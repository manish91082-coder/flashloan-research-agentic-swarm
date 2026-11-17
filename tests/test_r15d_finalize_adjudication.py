import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.finalize_r15d_adjudication import finalize_adjudication
from scripts.merge_r15d_primary_reviews import merge_primary_submissions
from scripts.validate_r15d_adjudication import DEFAULT_PACKET, validate


class R15DFinalizeAdjudicationTests(unittest.TestCase):
    def setUp(self):
        self.template = json.loads(DEFAULT_PACKET.read_text(encoding="utf-8"))

    def primary_bundle(self, reviewer_id, disagreement_case=None):
        cases = []
        for source in self.template["cases"]:
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
                "rationale": "Primary reviewer conclusion grounded in the pinned source excerpt.",
                "evidence_references": refs, "confidence": 0.8,
                "completed_at": "2026-11-17T00:00:00Z",
            })
        return {
            "schema_version": "1.0", "benchmark_id": "r15d-semantic-source-facts-v1",
            "reviewer_id": reviewer_id, "submitted_at": "2026-11-17T00:00:00Z",
            "attestations": {
                "independent_review": True, "model_outputs_not_seen": True,
                "other_reviews_not_seen": True, "conflicts_disclosed": True,
                "conflict_statement": "none",
            },
            "cases": cases,
        }

    def third_bundle(self, staged, reviewer_id="reviewer.gamma"):
        cases = []
        for source in staged["cases"]:
            if not source["consensus"]["disagreement"]:
                continue
            pin = {key: source[key] for key in (
                "repository", "commit_sha", "tree_sha", "path",
                "git_blob_sha1", "line_start", "line_end", "excerpt_sha256",
            )}
            refs = [f'{pin["path"]}:{pin["line_start"]}-{pin["line_end"]}#sha256:{pin["excerpt_sha256"]}']
            cases.append({
                "case_id": source["id"], "source_pin": pin, "label": "present",
                "rationale": "After reviewing both primary records, this label best matches the pinned evidence.",
                "evidence_references": refs, "confidence": 0.9,
                "completed_at": "2026-11-17T00:00:00Z", "independence_attestation": True,
            })
        return {
            "schema_version": "1.0", "benchmark_id": "r15d-semantic-source-facts-v1",
            "reviewer_id": reviewer_id, "submitted_at": "2026-11-17T00:00:00Z",
            "attestations": {
                "independent_review": True, "model_outputs_not_seen": True,
                "primary_reviews_seen": True, "conflicts_disclosed": True,
                "conflict_statement": "none",
            },
            "cases": cases,
        }

    def setup_sources(self, root, disagreement_case=None):
        a, b, staged = root / "a.json", root / "b.json", root / "staged.json"
        a.write_text(json.dumps(self.primary_bundle("reviewer.alpha")), encoding="utf-8")
        b.write_text(json.dumps(self.primary_bundle("reviewer.beta", disagreement_case)), encoding="utf-8")
        merge_result = merge_primary_submissions(a, b, staged, "custodian.1", True)
        return a, b, staged, merge_result

    def test_unanimous_primary_reviews_finalize_without_third_adjudicator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, staged, merge = self.setup_sources(root)
            output = root / "final.json"
            result = finalize_adjudication(a, b, staged, output, "custodian.1", True, expected_staged_sha256=merge["output_sha256"])
            packet = json.loads(output.read_text(encoding="utf-8"))
            validation = validate(packet, require_complete=True)
            self.assertTrue(result["valid_complete_adjudication"])
            self.assertTrue(validation["valid"])
            self.assertEqual(validation["completed_cases"], 6)
            self.assertEqual(result["third_adjudication_cases"], [])
            self.assertFalse(packet["freeze"]["ground_truth_frozen"])
            self.assertFalse(packet["freeze"]["model_inference_authorized"])
            self.assertTrue(all(c["consensus"]["status"] == "adjudicated" for c in packet["cases"]))
            self.assertEqual(result["output_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())

    def test_disagreement_requires_verified_third_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, staged, merge = self.setup_sources(root, "NAV-02")
            staged_packet = json.loads(staged.read_text(encoding="utf-8"))
            third = root / "third.json"
            third.write_text(json.dumps(self.third_bundle(staged_packet)), encoding="utf-8")
            output = root / "final.json"
            result = finalize_adjudication(
                a, b, staged, output, "custodian.1", True, third, True, merge["output_sha256"]
            )
            packet = json.loads(output.read_text(encoding="utf-8"))
            nav = next(c for c in packet["cases"] if c["id"] == "NAV-02")
            self.assertTrue(result["valid_complete_adjudication"])
            self.assertEqual(nav["third_adjudicator"]["reviewer_id"], "reviewer.gamma")
            self.assertEqual(nav["consensus"]["label"], "present")
            self.assertTrue(nav["consensus"]["disagreement"])
            self.assertFalse(packet["freeze"]["ground_truth_frozen"])

    def test_missing_third_submission_blocks_disagreement_finalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, staged, _ = self.setup_sources(root, "NAV-02")
            with self.assertRaisesRegex(ValueError, "third-adjudicator submission is required"):
                finalize_adjudication(a, b, staged, root / "final.json", "custodian.1", True)
            self.assertFalse((root / "final.json").exists())

    def test_unverified_third_identity_blocks_finalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, staged, _ = self.setup_sources(root, "NAV-02")
            staged_packet = json.loads(staged.read_text(encoding="utf-8"))
            third = root / "third.json"
            third.write_text(json.dumps(self.third_bundle(staged_packet)), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "verify the third adjudicator identity"):
                finalize_adjudication(a, b, staged, root / "final.json", "custodian.1", True, third, False)
            self.assertFalse((root / "final.json").exists())

    def test_third_submission_not_accepted_for_unanimous_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, staged, _ = self.setup_sources(root)
            third = root / "third.json"
            third.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not permitted when there are no"):
                finalize_adjudication(a, b, staged, root / "final.json", "custodian.1", True, third, True)

    def test_final_packet_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, staged, _ = self.setup_sources(root)
            output = root / "final.json"
            output.write_text("preserve-me", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                finalize_adjudication(a, b, staged, output, "custodian.1", True)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve-me")


if __name__ == "__main__":
    unittest.main()
