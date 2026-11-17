import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_r15d_v2_semantic_fixtures import build
from scripts.finalize_r15d_v2_adjudication import finalize_adjudication
from scripts.merge_r15d_v2_primary_reviews import merge_primary_reviews
from scripts.validate_r15d_v2_adjudication import validate_final_packet
from scripts.validate_r15d_v2_review_submission import load_fixture_bundle


class R15DV2FinalizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture_dir = self.root / "fixture"
        build(output_dir=self.fixture_dir)
        self.fixture = load_fixture_bundle(self.fixture_dir)
        self.stage_counter = 0

    def primary_bundle(self, reviewer_id, disagreement_case=None):
        cases = []
        for source in self.fixture["cases"]:
            pin = {key: source[key] for key in (
                "repository", "commit_sha", "tree_sha", "path",
                "git_blob_sha1", "line_start", "line_end", "excerpt_sha256",
            )}
            refs = [f'{pin["path"]}:{pin["line_start"]}-{pin["line_end"]}#sha256:{pin["excerpt_sha256"]}']
            label = "unknown"
            if reviewer_id == "reviewer.beta" and source["id"] == disagreement_case:
                label = "present"
            cases.append({
                "case_id": source["id"], "source_pin": pin, "label": label,
                "rationale": "Synthetic primary reviewer rationale for finalization testing.",
                "evidence_references": refs, "confidence": 0.8,
                "completed_at": "2026-11-17T00:00:00Z", "independence_attestation": True,
            })
        return {
            "schema_version": "1.0", "benchmark_id": "r15d-semantic-source-facts-v2",
            "reviewer_id": reviewer_id, "submitted_at": "2026-11-17T00:00:00Z",
            "attestations": {
                "independent_review": True, "model_outputs_not_seen": True,
                "other_reviews_not_seen": True, "v1_answer_key_not_seen": True,
                "v1_labels_not_consulted": True, "conflicts_disclosed": True,
                "conflict_statement": "synthetic test fixture only",
            },
            "cases": cases,
        }

    def make_third_bundle(self, staged, reviewer_id="reviewer.gamma"):
        cases = []
        for source in staged["cases"]:
            if not source["disagreement"]:
                continue
            pin = {key: source[key] for key in (
                "repository", "commit_sha", "tree_sha", "path",
                "git_blob_sha1", "line_start", "line_end", "excerpt_sha256",
            )}
            refs = [f'{pin["path"]}:{pin["line_start"]}-{pin["line_end"]}#sha256:{pin["excerpt_sha256"]}']
            cases.append({
                "case_id": source["id"], "source_pin": pin, "label": "present",
                "rationale": "Synthetic third-adjudicator rationale after reviewing both primary records.",
                "evidence_references": refs, "confidence": 0.9,
                "completed_at": "2026-11-17T00:00:00Z", "independence_attestation": True,
            })
        return {
            "schema_version": "1.0", "benchmark_id": "r15d-semantic-source-facts-v2",
            "reviewer_id": reviewer_id, "submitted_at": "2026-11-17T00:00:00Z",
            "attestations": {
                "independent_review": True, "model_outputs_not_seen": True,
                "primary_reviews_seen": True, "v1_answer_key_not_seen": True,
                "v1_labels_not_consulted": True, "conflicts_disclosed": True,
                "conflict_statement": "synthetic test fixture only",
            },
            "cases": cases,
        }

    def setup_inputs(self, disagreement_case=None):
        self.stage_counter += 1
        a, b, staged = self.root / "a.json", self.root / "b.json", self.root / f"staged-{self.stage_counter}.json"
        a.write_text(json.dumps(self.primary_bundle("reviewer.alpha")), encoding="utf-8")
        b.write_text(json.dumps(self.primary_bundle("reviewer.beta", disagreement_case)), encoding="utf-8")
        merge = merge_primary_reviews(self.fixture_dir, a, b, staged, "custodian.v2", True)
        return a, b, staged, merge

    def test_unanimous_primary_reviews_finalize_to_complete_pending_freeze_packet(self):
        a, b, staged, merge = self.setup_inputs()
        output = self.root / "final-unanimous.json"
        result = finalize_adjudication(
            self.fixture_dir, a, b, staged, output, "custodian.v2", True,
            expected_staged_sha256=merge["output_sha256"],
        )
        packet = json.loads(output.read_text(encoding="utf-8"))
        validation = validate_final_packet(self.fixture, packet)
        self.assertTrue(result["valid_complete_adjudication"])
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(validation["completed_cases"], 6)
        self.assertIsNone(packet["third_reviewer_attestations"])
        self.assertFalse(packet["custody"]["third_adjudicator_identity_verified_out_of_band"])
        self.assertFalse(packet["freeze"]["ground_truth_frozen"])
        self.assertFalse(packet["freeze"]["model_inference_authorized"])
        self.assertEqual(len(packet["primary_reviewer_attestations"]), 2)

    def test_disagreement_path_requires_and_preserves_third_review_attestations(self):
        a, b, staged_path, merge = self.setup_inputs("NAV2-02")
        staged = json.loads(staged_path.read_text(encoding="utf-8"))
        third_path = self.root / "third.json"
        third_path.write_text(json.dumps(self.make_third_bundle(staged)), encoding="utf-8")
        output = self.root / "final-disagreement.json"
        result = finalize_adjudication(
            self.fixture_dir, a, b, staged_path, output, "custodian.v2", True,
            third_path, True, merge["output_sha256"],
        )
        packet = json.loads(output.read_text(encoding="utf-8"))
        validation = validate_final_packet(self.fixture, packet)
        nav = next(c for c in packet["cases"] if c["id"] == "NAV2-02")
        self.assertTrue(result["valid_complete_adjudication"])
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(nav["third_adjudicator"]["reviewer_id"], "reviewer.gamma")
        self.assertEqual(nav["consensus"]["label"], "present")
        self.assertEqual(packet["third_reviewer_attestations"]["reviewer_id"], "reviewer.gamma")
        self.assertTrue(packet["custody"]["third_adjudicator_identity_verified_out_of_band"])
        self.assertFalse(packet["freeze"]["ground_truth_frozen"])

    def test_disagreement_without_third_bundle_is_blocked(self):
        a, b, staged, _ = self.setup_inputs("COB2-02")
        with self.assertRaisesRegex(ValueError, "third-adjudicator bundle is required"):
            finalize_adjudication(self.fixture_dir, a, b, staged, self.root / "blocked.json", "custodian.v2", True)
        self.assertFalse((self.root / "blocked.json").exists())

    def test_unverified_third_identity_is_blocked(self):
        a, b, staged_path, _ = self.setup_inputs("COB2-03")
        staged = json.loads(staged_path.read_text(encoding="utf-8"))
        third = self.root / "third-unverified.json"
        third.write_text(json.dumps(self.make_third_bundle(staged)), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "verify third-adjudicator identity"):
            finalize_adjudication(self.fixture_dir, a, b, staged_path, self.root / "blocked.json", "custodian.v2", True, third, False)
        self.assertFalse((self.root / "blocked.json").exists())

    def test_third_reviewer_identity_collision_is_blocked(self):
        a, b, staged_path, _ = self.setup_inputs("NAV2-01")
        staged = json.loads(staged_path.read_text(encoding="utf-8"))
        third_bundle = self.make_third_bundle(staged, "reviewer.alpha")
        third = self.root / "third-collision.json"
        third.write_text(json.dumps(third_bundle), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "third-adjudicator bundle failed validation"):
            finalize_adjudication(self.fixture_dir, a, b, staged_path, self.root / "blocked.json", "custodian.v2", True, third, True)
        self.assertFalse((self.root / "blocked.json").exists())

    def test_third_bundle_is_rejected_for_unanimous_packet(self):
        a, b, staged, _ = self.setup_inputs()
        third = self.root / "third-not-needed.json"
        third.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "not permitted when no primary disagreement"):
            finalize_adjudication(self.fixture_dir, a, b, staged, self.root / "blocked.json", "custodian.v2", True, third, True)

    def test_output_collision_is_not_overwritten(self):
        a, b, staged, _ = self.setup_inputs()
        output = self.root / "existing-final.json"
        output.write_text("preserve-me", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            finalize_adjudication(self.fixture_dir, a, b, staged, output, "custodian.v2", True)
        self.assertEqual(output.read_text(encoding="utf-8"), "preserve-me")

    def test_final_validator_detects_consensus_label_tampering(self):
        a, b, staged, _ = self.setup_inputs()
        output = self.root / "tamper-final.json"
        finalize_adjudication(self.fixture_dir, a, b, staged, output, "custodian.v2", True)
        packet = json.loads(output.read_text(encoding="utf-8"))
        packet["cases"][0]["consensus"]["label"] = "absent"
        result = validate_final_packet(self.fixture, packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("unanimous consensus" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
