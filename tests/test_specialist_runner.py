from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from flashloan_research.specialist_runner import (
    SpecialistTaskError, validate_specialist_output,
    _verified_source_context, _prior_specialist_reports,
)
from flashloan_research.storage import git_blob_sha


class SpecialistEvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.inspection = {
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

    def test_accepts_only_exact_pinned_signal_reference(self):
        output = {
            "summary": "Callback implementation requires manual source review.",
            "purpose": "liquidation executor",
            "implementation_status": "partial",
            "findings": [],
            "evidence": [{
                "path": "contracts/Liquidator.sol",
                "line": 42,
                "signal": "executeOperation",
                "excerpt": "function executeOperation(...) external returns (bool)",
            }],
            "unknowns": ["Callback caller authentication not proven by this excerpt."],
            "confidence": "low",
        }
        result = validate_specialist_output(output, self.inspection)
        self.assertEqual(len(result["evidence"]), 1)
        self.assertEqual(result["evidence"][0]["commit_sha"], "a" * 40)
        self.assertEqual(len(result["rejected_evidence"]), 0)

    def test_rejects_fabricated_source_location(self):
        output = {
            "summary": "Potential issue needs full review.",
            "purpose": "liquidation executor",
            "implementation_status": "unknown",
            "findings": [],
            "evidence": [{
                "path": "contracts/Imaginary.sol",
                "line": 999,
                "signal": "onlyOwner",
                "excerpt": "function onlyOwner()",
            }],
            "unknowns": [],
            "confidence": "low",
        }
        result = validate_specialist_output(output, self.inspection)
        self.assertEqual(result["evidence"], [])
        self.assertEqual(result["rejected_evidence"][0]["reason"],
                         "not_present_in_pinned_inspection_signals")

    def test_rejects_invalid_status_or_confidence(self):
        output = {
            "summary": "x", "purpose": "x", "implementation_status": "safe",
            "findings": [], "evidence": [], "unknowns": [], "confidence": "certain",
        }
        with self.assertRaises(SpecialistTaskError):
            validate_specialist_output(output, self.inspection)

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
            self.assertEqual(len(result[0]["excerpt_sha256"]), 64)

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

    def test_prior_reviewer_context_contains_real_candidate_purpose_report(self):
        report_data = {
            "summary": "Morpho liquidation callback implementation.",
            "purpose": "liquidation bot", "implementation_status": "partial",
            "findings": [{"id": "F-1", "claim": "callback authentication"}],
            "evidence": [], "unknowns": ["No live execution proof"], "confidence": "low",
            "agent_metadata": {"role": "protocol_specialist"},
            "evidence_validation": {"inspection_commit_sha": "a" * 40},
        }
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "purpose.json"
            report_path.write_text(json.dumps(report_data), encoding="utf-8")
            tasks = [{
                "task_type": "candidate_purpose", "role": "protocol_specialist",
                "status": "completed", "task_id": "purpose-1",
                "payload": {"repository": "org/repo"},
                "result": {"report": str(report_path)},
            }]
            context = _prior_specialist_reports(tasks, "org/repo", {"commit_sha": "a" * 40})
            self.assertEqual(context[0]["purpose"], "liquidation bot")
            self.assertEqual(context[0]["findings"][0]["id"], "F-1")

    def test_prior_reviewer_context_rejects_source_commit_mismatch(self):
        report_data = {
            "summary": "x", "purpose": "unknown", "implementation_status": "unknown",
            "findings": [], "evidence": [], "unknowns": [], "confidence": "low",
            "agent_metadata": {"role": "protocol_specialist"},
            "evidence_validation": {"inspection_commit_sha": "b" * 40},
        }
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "purpose.json"
            report_path.write_text(json.dumps(report_data), encoding="utf-8")
            tasks = [{
                "task_type": "candidate_purpose", "role": "protocol_specialist",
                "status": "completed", "task_id": "purpose-1",
                "payload": {"repository": "org/repo"},
                "result": {"report": str(report_path)},
            }]
            with self.assertRaises(SpecialistTaskError):
                _prior_specialist_reports(tasks, "org/repo", {"commit_sha": "a" * 40})

if __name__ == "__main__":
    unittest.main()
