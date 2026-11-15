from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from flashloan_research.specialist_runner import (
    SpecialistTaskError, validate_specialist_output, _evidence_catalog,
    _verified_source_context, _prior_specialist_reports,
)
from flashloan_research.storage import git_blob_sha


def sample_inspection():
    return {
        "repository": "org/repo",
        "commit_sha": "a" * 40,
        "tree_sha": "b" * 40,
        "signals": [{
            "path": "contracts/Liquidator.sol",
            "line": 42,
            "signal": "executeOperation",
            "excerpt": "function executeOperation(...) external returns (bool)",
        }],
    }


def sample_output(**overrides):
    value = {
        "summary": "The supplied source shows an executeOperation callback entry point.",
        "purpose": "liquidation executor",
        "implementation_status": "partial",
        "findings": [{
            "finding_id": "F-1",
            "claim": "The repository defines an executeOperation callback.",
            "category": "protocol_flow",
            "severity": "informational",
            "claim_status": "source_observed",
            "confidence": "medium",
            "evidence_refs": ["EV00001"],
        }],
        "evidence": ["EV00001"],
        "unknowns": ["Runtime behavior has not been executed."],
        "confidence": "medium",
    }
    value.update(overrides)
    return value


class SpecialistEvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.inspection = sample_inspection()

    def test_evidence_catalog_has_stable_ids_and_exact_source_coordinates(self):
        catalog = _evidence_catalog(self.inspection)
        self.assertEqual(catalog[0]["evidence_id"], "EV00001")
        self.assertEqual(catalog[0]["path"], "contracts/Liquidator.sol")
        self.assertEqual(catalog[0]["line"], 42)

    def test_accepts_only_catalog_id_and_attaches_commit_provenance(self):
        result = validate_specialist_output(sample_output(), self.inspection, "protocol_specialist")
        self.assertEqual(len(result["evidence"]), 1)
        self.assertEqual(result["evidence"][0]["evidence_id"], "EV00001")
        self.assertEqual(result["evidence"][0]["commit_sha"], "a" * 40)
        self.assertEqual(result["review_decision"], "not_applicable")
        self.assertEqual(result["review_disagreements"], [])
        self.assertTrue(result["evidence_validation"]["all_findings_linked_to_accepted_evidence"])

    def test_rejects_any_model_evidence_id_not_in_the_pinned_catalog(self):
        output = sample_output(evidence=["EV00001", "EV99999"])
        with self.assertRaisesRegex(SpecialistTaskError, "not in the pinned catalog"):
            validate_specialist_output(output, self.inspection, "protocol_specialist")

    def test_rejects_finding_that_cites_unselected_or_fabricated_evidence_id(self):
        output = sample_output(evidence=["EV00001"], findings=[{
            "finding_id": "F-1", "claim": "unsupported", "category": "security",
            "severity": "high", "claim_status": "source_observed", "confidence": "high",
            "evidence_refs": ["EV99999"],
        }])
        with self.assertRaisesRegex(SpecialistTaskError, "not selected from the pinned catalog"):
            validate_specialist_output(output, self.inspection, "solidity_security")

    def test_rejects_finding_without_any_evidence_reference(self):
        output = sample_output(findings=[{
            "finding_id": "F-1", "claim": "unsupported", "category": "security",
            "severity": "high", "claim_status": "supported_inference", "confidence": "high",
            "evidence_refs": [],
        }])
        with self.assertRaisesRegex(SpecialistTaskError, "has no evidence_refs"):
            validate_specialist_output(output, self.inspection, "solidity_security")

    def test_zero_evidence_requires_unknown_status_low_confidence_and_no_findings(self):
        output = sample_output(
            evidence=[], findings=[], implementation_status="unknown", confidence="low",
        )
        result = validate_specialist_output(output, self.inspection, "economics_quant")
        self.assertEqual(result["evidence"], [])
        self.assertEqual(result["implementation_status"], "unknown")
        invalid = sample_output(evidence=[], findings=[], confidence="high")
        with self.assertRaisesRegex(SpecialistTaskError, "zero-evidence output"):
            validate_specialist_output(invalid, self.inspection, "economics_quant")

    def test_specialist_model_output_must_not_include_reviewer_only_fields(self):
        output = sample_output(review_decision="not_applicable", review_disagreements=[])
        with self.assertRaisesRegex(SpecialistTaskError, "must not contain reviewer-only fields"):
            validate_specialist_output(output, self.inspection, "protocol_specialist")

    def test_reviewer_must_return_explicit_decision(self):
        output = sample_output(review_decision="not_applicable", review_disagreements=[])
        with self.assertRaisesRegex(SpecialistTaskError, "explicit valid review_decision"):
            validate_specialist_output(output, self.inspection, "independent_reviewer")

    def test_verified_source_context_loads_hash_verified_bounded_excerpts(self):
        payload = (
            "contract Liquidator {\n"
            "    function executeOperation() external returns (bool) {\n"
            "        return true;\n"
            "    }\n"
            "}\n"
        ).encode()
        blob_sha = git_blob_sha(payload)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel = f"{blob_sha[:2]}/{blob_sha[2:]}"
            target = root / rel
            target.parent.mkdir(parents=True)
            target.write_bytes(payload)
            inspection = {
                "signals": [{"path": "contracts/Liquidator.sol", "line": 2}],
                "captured_files": [{"path": "contracts/Liquidator.sol",
                                    "blob_sha": blob_sha, "vault_relative_path": rel}],
            }
            result = _verified_source_context(inspection, snapshot_root=root, max_chars=4000)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["blob_sha"], blob_sha)
            self.assertIn("000002:     function executeOperation()", result[0]["excerpt"])

    def test_verified_source_context_rejects_tampered_blob(self):
        payload = b"contract X {}"
        blob_sha = git_blob_sha(payload)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel = f"{blob_sha[:2]}/{blob_sha[2:]}"
            target = root / rel
            target.parent.mkdir(parents=True)
            target.write_bytes(b"modified content")
            inspection = {"signals": [], "captured_files": [{
                "path": "contracts/X.sol", "blob_sha": blob_sha, "vault_relative_path": rel
            }]}
            with self.assertRaises(SpecialistTaskError):
                _verified_source_context(inspection, snapshot_root=root)

    def test_prior_reviewer_context_requires_seven_distinct_task_reports(self):
        roles = [
            ("candidate_purpose", "candidate_purpose"),
            ("protocol_forensics", "protocol_specialist"),
            ("security_forensics", "solidity_security"),
            ("execution_forensics", "execution_engineer"),
            ("test_forensics", "test_verification"),
            ("economic_forensics", "economics_quant"),
            ("dependency_forensics", "dependency_license"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            tasks = []
            for index, (task_type, role) in enumerate(roles):
                task_id = f"task-{index}"
                report = {
                    "summary": f"Report {index}", "purpose": "liquidation bot",
                    "implementation_status": "partial", "findings": [], "evidence": [],
                    "unknowns": ["runtime not verified"], "confidence": "low",
                    "task_metadata": {"task_id": task_id, "task_type": task_type, "role": role},
                    "agent_metadata": {"role": role},
                    "evidence_validation": {
                        "inspection_commit_sha": "a" * 40,
                        "inspection_tree_sha": "b" * 40,
                        "accepted_signal_references": 12,
                        "all_findings_linked_to_accepted_evidence": True,
                    },
                }
                path = Path(tmp) / f"{task_id}.json"
                path.write_text(json.dumps(report), encoding="utf-8")
                tasks.append({
                    "task_type": task_type, "role": role, "status": "completed",
                    "task_id": task_id, "payload": {"repository": "org/repo"},
                    "result": {"report": str(path)},
                })
            context = _prior_specialist_reports(tasks, "org/repo", self.inspection)
            self.assertEqual(len(context), 7)
            self.assertEqual(len({item["task_type"] for item in context}), 7)

    def test_prior_reviewer_context_deduplicates_source_excerpts_and_preserves_all_claims(self):
        roles = [
            ("candidate_purpose", "candidate_purpose"),
            ("protocol_forensics", "protocol_specialist"),
            ("security_forensics", "solidity_security"),
            ("execution_forensics", "execution_engineer"),
            ("test_forensics", "test_verification"),
            ("economic_forensics", "economics_quant"),
            ("dependency_forensics", "dependency_license"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            tasks = []
            for index, (task_type, role) in enumerate(roles):
                task_id = f"large-task-{index}"
                report = {
                    "summary": "A source-grounded report " + ("S" * 800),
                    "purpose": "A repository purpose " + ("P" * 600),
                    "implementation_status": "partial",
                    "findings": [{
                        "finding_id": f"F-{index}-{finding_index}",
                        "claim": f"Material claim {finding_index} from role {role}. " + ("C" * 240),
                        "category": "security",
                        "severity": "high",
                        "claim_status": "supported_inference",
                        "confidence": "medium",
                        "evidence_refs": ["EV00001"],
                    } for finding_index in range(3)],
                    "evidence": [{
                        "evidence_id": "EV00001",
                        "path": "contracts/Liquidator.sol",
                        "line": 42,
                        "signal": "executeOperation",
                        "excerpt": "LONG_SOURCE_EXCERPT_SHOULD_NOT_BE_DUPLICATED_" + ("X" * 2500),
                        "commit_sha": "a" * 40,
                    } for _ in range(12)],
                    "rejected_evidence": [],
                    "unknowns": ["Runtime behavior was not executed."],
                    "confidence": "medium",
                    "task_metadata": {"task_id": task_id, "task_type": task_type},
                    "agent_metadata": {"role": role},
                    "evidence_validation": {
                        "inspection_commit_sha": "a" * 40,
                        "inspection_tree_sha": "b" * 40,
                        "accepted_signal_references": 12,
                        "all_findings_linked_to_accepted_evidence": True,
                    },
                }
                path = Path(tmp) / f"{task_id}.json"
                path.write_text(json.dumps(report), encoding="utf-8")
                tasks.append({
                    "task_type": task_type, "role": role, "status": "completed",
                    "task_id": task_id, "payload": {"repository": "org/repo"},
                    "result": {"report": str(path)},
                })
            context = _prior_specialist_reports(tasks, "org/repo", self.inspection, max_chars=12000)
            rendered = json.dumps(context, ensure_ascii=False)
            self.assertEqual(len(context), 7)
            self.assertLess(len(rendered), 12000)
            self.assertNotIn("LONG_SOURCE_EXCERPT_SHOULD_NOT_BE_DUPLICATED", rendered)
            self.assertTrue(all(len(item["findings"]) == 3 for item in context))
            self.assertTrue(all(item["accepted_evidence_ids"] == ["EV00001"] for item in context))
            self.assertEqual(len({item["task_type"] for item in context}), 7)

    def test_prior_reviewer_context_rejects_report_task_id_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = {
                "summary": "x", "purpose": "unknown", "implementation_status": "unknown",
                "findings": [], "evidence": [], "unknowns": ["x"], "confidence": "low",
                "task_metadata": {"task_id": "wrong", "task_type": "candidate_purpose"},
                "agent_metadata": {"role": "candidate_purpose"},
                "evidence_validation": {
                    "inspection_commit_sha": "a" * 40,
                    "inspection_tree_sha": "b" * 40,
                    "all_findings_linked_to_accepted_evidence": True,
                },
            }
            path = Path(tmp) / "purpose.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            tasks = [{
                "task_type": "candidate_purpose", "role": "candidate_purpose",
                "status": "completed", "task_id": "expected",
                "payload": {"repository": "org/repo"}, "result": {"report": str(path)},
            }]
            with self.assertRaisesRegex(SpecialistTaskError, "task provenance mismatch"):
                _prior_specialist_reports(tasks, "org/repo", self.inspection)


if __name__ == "__main__":
    unittest.main()