from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from flashloan_research.specialist_runner import (
    SpecialistTaskError, REQUIRED_KEYS, validate_specialist_output, _generate_validated_output, _source_supported_purpose_category, _evidence_catalog, _is_retryable_specialist_error,
    _verified_source_context, _prior_specialist_reports, _validate_report_evidence_provenance,
    ROLE_PROMPTS, _canonical_purpose_category,
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
        "purpose": "Flash-loan liquidation executor.",
        "purpose_category": "flash_loan_liquidation_bot",
        "implementation_status": "partial",
        "findings": [{
            "finding_id": "F-1",
            "claim": "The repository defines an executeOperation callback.",
            "category": "protocol_flow",
            "severity": "not_applicable",
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


class DuplicateClaimRetryTests(unittest.TestCase):
    def test_duplicate_claim_failure_is_retried_at_task_level_with_bounded_attempts(self):
        self.assertTrue(_is_retryable_specialist_error(SpecialistTaskError("duplicate finding claim")))
        self.assertTrue(_is_retryable_specialist_error(TimeoutError("model timeout")))
        self.assertFalse(_is_retryable_specialist_error(SpecialistTaskError("invalid evidence ID")))

    def test_duplicate_claim_gets_one_corrective_retry_and_remains_strict(self):
        class Provider:
            def __init__(self):
                self.calls = []
            def generate_json(self, prompt, context, required_keys):
                self.calls.append((prompt, context))
                if len(self.calls) == 1:
                    duplicate = sample_output(findings=[
                        {"finding_id": "F-1", "claim": "Same claim.", "category": "protocol_flow",
                         "severity": "not_applicable", "claim_status": "source_observed",
                         "confidence": "low", "evidence_refs": ["EV00001"]},
                        {"finding_id": "F-2", "claim": "Same claim.", "category": "protocol_flow",
                         "severity": "not_applicable", "claim_status": "source_observed",
                         "confidence": "low", "evidence_refs": ["EV00001"]},
                    ])
                    return {k: v for k, v in duplicate.items() if k in required_keys}
                corrected = sample_output(findings=[
                    {"finding_id": "F-1", "claim": "One distinct source claim.", "category": "protocol_flow",
                     "severity": "not_applicable", "claim_status": "source_observed",
                     "confidence": "low", "evidence_refs": ["EV00001"]},
                ])
                return {k: v for k, v in corrected.items() if k in required_keys}

        provider = Provider()
        context = {"repository": "org/repo"}
        result = _generate_validated_output(
            provider, "prompt", context, REQUIRED_KEYS, sample_inspection(), "protocol_specialist",
            canonical_purpose_category="flash_loan_liquidation_bot",
        )
        self.assertEqual(len(provider.calls), 2)
        self.assertIn("VALIDATION RETRY", provider.calls[1][0])
        self.assertIn("previous_rejected_output", provider.calls[1][1])
        self.assertEqual(len(result["findings"]), 1)
        self.assertTrue(result["evidence_validation"]["all_findings_linked_to_accepted_evidence"])

    def test_source_pinned_aave_liquidation_signal_rejects_security_tooling_and_retries(self):
        inspection = sample_inspection()
        inspection["repository"] = "0xnavarro/Aave-Liquiditor"
        inspection["captured_files"] = [{"path": "src/contracts/FlashLiquidator.sol"}]
        inspection["signals"] = [{
            "path": "src/contracts/FlashLiquidator.sol",
            "line": 131,
            "signal": "aave_flash_loan_simple",
            "excerpt": "pool.flashLoanSimple(asset, amount, params, 0)",
        }]
        self.assertEqual(
            _source_supported_purpose_category(inspection), "flash_loan_liquidation_bot"
        )
        class Provider:
            def __init__(self): self.calls = []
            def generate_json(self, prompt, context, required_keys):
                self.calls.append((prompt, context))
                category = "security_tooling" if len(self.calls) == 1 else "flash_loan_liquidation_bot"
                result = sample_output(purpose_category=category)
                return {k: v for k, v in result.items() if k in required_keys}
        provider = Provider()
        result = _generate_validated_output(
            provider, "purpose prompt", {}, REQUIRED_KEYS, inspection, "candidate_purpose"
        )
        self.assertEqual(len(provider.calls), 2)
        self.assertIn("only permitted purpose_category", provider.calls[1][1]["validation_feedback"])
        self.assertEqual(result["purpose_category"], "flash_loan_liquidation_bot")

    def test_source_pinned_uniswap_liquidation_signal_maps_to_flash_swap_liquidation(self):
        inspection = sample_inspection()
        inspection["repository"] = "AlbertSu123/UniswapFlashSwap"
        inspection["captured_files"] = [{"path": "contracts/LiquidationOperator.sol"}]
        inspection["signals"] = [{"signal": "uniswap_v2_flash_callback"}]
        self.assertEqual(
            _source_supported_purpose_category(inspection), "flash_swap_liquidation_bot"
        )

    def test_non_duplicate_validation_errors_are_not_retried(self):
        class Provider:
            def __init__(self): self.calls = 0
            def generate_json(self, prompt, context, required_keys):
                self.calls += 1
                return {k: v for k, v in sample_output(evidence=["EV99999"]).items() if k in required_keys}
        provider = Provider()
        with self.assertRaisesRegex(SpecialistTaskError, "not in the pinned catalog"):
            _generate_validated_output(
                provider, "prompt", {}, REQUIRED_KEYS, sample_inspection(), "protocol_specialist",
                canonical_purpose_category="flash_loan_liquidation_bot",
            )
        self.assertEqual(provider.calls, 1)


class SpecialistEvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.inspection = sample_inspection()

    def test_independent_reviewer_prompt_checks_callback_auth_and_placeholder_logic(self):
        prompt = ROLE_PROMPTS["independent_reviewer"]
        self.assertIn("callback caller", prompt)
        self.assertIn("initiator", prompt)
        self.assertIn("repayment and premium", prompt)
        self.assertIn("TODO or placeholder", prompt)
        self.assertIn("configured lending Pool/provider address", prompt)

    def test_rejects_role_inappropriate_finding_category(self):
        output = sample_output(findings=[{
            "finding_id": "F-1", "claim": "A security flaw exists.",
            "category": "security", "severity": "high",
            "claim_status": "supported_inference", "confidence": "medium",
            "evidence_refs": ["EV00001"],
        }])
        with self.assertRaisesRegex(SpecialistTaskError, "category is not permitted"):
            validate_specialist_output(output, self.inspection, "candidate_purpose")

    def test_rejects_security_severity_on_non_security_role(self):
        output = sample_output(findings=[{
            "finding_id": "F-1", "claim": "A liquidation callback is declared.",
            "category": "protocol_flow", "severity": "high",
            "claim_status": "source_observed", "confidence": "medium",
            "evidence_refs": ["EV00001"],
        }])
        with self.assertRaisesRegex(SpecialistTaskError, "severity must be not_applicable"):
            validate_specialist_output(output, self.inspection, "candidate_purpose")

    def test_rejects_high_confidence_when_unknowns_remain_or_status_is_partial(self):
        output = sample_output(confidence="high")
        with self.assertRaisesRegex(SpecialistTaskError, "high confidence requires implemented status"):
            validate_specialist_output(output, self.inspection, "candidate_purpose")

    def test_candidate_purpose_prompt_distinguishes_security_tooling_from_review_topic(self):
        prompt = ROLE_PROMPTS["candidate_purpose"]
        self.assertIn("NOT a liquidation contract", prompt)
        self.assertIn("flash_swap_liquidation_bot", prompt)
        self.assertIn("Classify intended primary function even when implementation is partial", prompt)

    def test_specialist_output_must_inherit_canonical_candidate_purpose(self):
        output = sample_output(purpose_category="security_tooling")
        with self.assertRaisesRegex(SpecialistTaskError, "differs from the completed candidate-purpose"):
            validate_specialist_output(
                output, self.inspection, "protocol_specialist",
                canonical_purpose_category="flash_loan_liquidation_bot",
            )
        accepted = validate_specialist_output(
            sample_output(), self.inspection, "protocol_specialist",
            canonical_purpose_category="flash_loan_liquidation_bot",
        )
        self.assertEqual(accepted["purpose_category"], "flash_loan_liquidation_bot")

    def test_canonical_purpose_loader_requires_exact_completed_task_and_source_pins(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_id = "purpose-task-1"
            report = validate_specialist_output(
                sample_output(), self.inspection, "candidate_purpose",
            )
            report["task_metadata"] = {
                "task_id": task_id, "task_type": "candidate_purpose",
            }
            report["agent_metadata"] = {"role": "candidate_purpose"}
            path = Path(tmp) / "purpose.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            task = {
                "task_type": "candidate_purpose", "status": "completed",
                "task_id": task_id, "payload": {"repository": "org/repo"},
                "result": {"report": str(path)},
            }
            self.assertEqual(
                _canonical_purpose_category([task], "org/repo", self.inspection),
                "flash_loan_liquidation_bot",
            )
            wrong_pin = json.loads(json.dumps(report))
            wrong_pin["evidence_validation"]["inspection_tree_sha"] = "c" * 40
            path.write_text(json.dumps(wrong_pin), encoding="utf-8")
            with self.assertRaisesRegex(SpecialistTaskError, "lacks exact source provenance"):
                _canonical_purpose_category([task], "org/repo", self.inspection)

    def test_rejects_invalid_purpose_category(self):
        output = sample_output(purpose_category="security")
        with self.assertRaisesRegex(SpecialistTaskError, "invalid or missing purpose_category"):
            validate_specialist_output(output, self.inspection, "candidate_purpose")

    def test_rejects_finding_with_more_than_four_evidence_references(self):
        inspection = {
            "repository": "org/repo", "commit_sha": "a" * 40, "tree_sha": "b" * 40,
            "signals": [{"path": f"contracts/C{i}.sol", "line": i + 1,
                         "signal": f"signal_{i}", "excerpt": f"source {i}"}
                        for i in range(5)],
        }
        output = sample_output(
            evidence=[f"EV{i:05d}" for i in range(1, 6)],
            findings=[{
                "finding_id": "F-1", "claim": "A bounded source claim.",
                "category": "protocol_flow", "severity": "not_applicable",
                "claim_status": "source_observed", "confidence": "medium",
                "evidence_refs": [f"EV{i:05d}" for i in range(1, 6)],
            }],
        )
        with self.assertRaisesRegex(SpecialistTaskError, "at most 4 narrowly relevant IDs"):
            validate_specialist_output(output, inspection, "candidate_purpose")

    def test_report_evidence_provenance_rechecks_exact_signal_and_commit_tree_pins(self):
        report = validate_specialist_output(sample_output(), self.inspection, "protocol_specialist")
        _validate_report_evidence_provenance(report, self.inspection)
        tampered = json.loads(json.dumps(report))
        tampered["evidence"][0]["excerpt"] = "invented excerpt"
        with self.assertRaisesRegex(SpecialistTaskError, "exact pinned source signal metadata"):
            _validate_report_evidence_provenance(tampered, self.inspection)
        wrong_pin = json.loads(json.dumps(report))
        wrong_pin["evidence"][0]["commit_sha"] = "c" * 40
        with self.assertRaisesRegex(SpecialistTaskError, "exact pinned source signal metadata"):
            _validate_report_evidence_provenance(wrong_pin, self.inspection)

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

    def test_rejects_duplicate_report_evidence_ids(self):
        output = sample_output(evidence=["EV00001", "EV00001"])
        with self.assertRaisesRegex(SpecialistTaskError, "evidence IDs must be unique"):
            validate_specialist_output(output, self.inspection, "candidate_purpose")

    def test_rejects_report_evidence_over_eight_ids(self):
        inspection = {
            "repository": "org/repo", "commit_sha": "a" * 40, "tree_sha": "b" * 40,
            "signals": [{"path": f"contracts/C{i}.sol", "line": i + 1,
                         "signal": f"signal_{i}", "excerpt": f"source {i}"}
                        for i in range(9)],
        }
        output = sample_output(evidence=[f"EV{i:05d}" for i in range(1, 10)], findings=[])
        with self.assertRaisesRegex(SpecialistTaskError, "at most 8 distinct IDs"):
            validate_specialist_output(output, inspection, "candidate_purpose")

    def test_rejects_finding_that_cites_unselected_or_fabricated_evidence_id(self):
        output = sample_output(evidence=["EV00001"], findings=[{
            "finding_id": "F-1", "claim": "unsupported", "category": "security",
            "severity": "high", "claim_status": "source_observed", "confidence": "medium",
            "evidence_refs": ["EV99999"],
        }])
        with self.assertRaisesRegex(SpecialistTaskError, "not selected from the pinned catalog"):
            validate_specialist_output(output, self.inspection, "solidity_security")

    def test_rejects_finding_without_any_evidence_reference(self):
        output = sample_output(findings=[{
            "finding_id": "F-1", "claim": "unsupported", "category": "security",
            "severity": "high", "claim_status": "supported_inference", "confidence": "medium",
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
        output = sample_output(findings=[], review_decision="not_applicable", review_disagreements=[])
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
                    "summary": "A source-grounded report with bounded material context.",
                    "purpose": "A repository purpose with bounded material context.",
                    "implementation_status": "partial",
                    "findings": [{
                        "finding_id": f"F-{index}-{finding_index}",
                        "claim": f"Material claim {finding_index} from role {role}, supported by the pinned source.",
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
            context = _prior_specialist_reports(tasks, "org/repo", self.inspection, max_chars=18000)
            rendered = json.dumps(context, ensure_ascii=False)
            self.assertEqual(len(context), 7)
            self.assertLess(len(rendered), 18000)
            self.assertNotIn("LONG_SOURCE_EXCERPT_SHOULD_NOT_BE_DUPLICATED", rendered)
            self.assertTrue(all(len(item["findings"]) == 3 for item in context))
            self.assertTrue(all(item["accepted_evidence_ids"] == ["EV00001"] for item in context))
            self.assertEqual(len({item["task_type"] for item in context}), 7)

    def test_prior_reviewer_context_fails_closed_instead_of_truncating_findings(self):
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
                task_id = f"overflow-task-{index}"
                report = {
                    "summary": "summary",
                    "purpose": "purpose",
                    "implementation_status": "partial",
                    "findings": [{
                        "finding_id": f"F-{i}", "claim": "claim", "category": "security",
                        "severity": "medium", "claim_status": "supported_inference",
                        "confidence": "low", "evidence_refs": ["EV00001"],
                    } for i in range(31 if index == 0 else 1)],
                    "evidence": [{"evidence_id": "EV00001"}],
                    "unknowns": [],
                    "confidence": "low",
                    "task_metadata": {"task_id": task_id, "task_type": task_type},
                    "agent_metadata": {"role": role},
                    "evidence_validation": {
                        "inspection_commit_sha": "a" * 40,
                        "inspection_tree_sha": "b" * 40,
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
            with self.assertRaisesRegex(SpecialistTaskError, "lossless reviewer-context item limits"):
                _prior_specialist_reports(tasks, "org/repo", self.inspection)

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