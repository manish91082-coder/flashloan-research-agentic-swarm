import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_r15d_v2_semantic_fixtures import build
from scripts.create_r15d_v2_intake_receipt import create_intake_receipt
from scripts.finalize_r15d_v2_adjudication import finalize_adjudication
from scripts.freeze_r15d_v2_adjudication import freeze_adjudication
from scripts.merge_r15d_v2_primary_reviews import merge_primary_reviews
from scripts.validate_r15d_v2_review_submission import load_fixture_bundle
from scripts.verify_r15d_v2_frozen_manifest import verify_frozen_manifest


class R15DV2EndToEndFreezeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture_dir = self.root / "fixture"
        build(output_dir=self.fixture_dir)
        self.fixture = load_fixture_bundle(self.fixture_dir)
        self.counter = 0

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
                "rationale": "Synthetic primary review for isolated v2 end-to-end tests.",
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

    def third_bundle(self, staged):
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
                "rationale": "Synthetic third review for isolated v2 freeze-pipeline testing.",
                "evidence_references": refs, "confidence": 0.9,
                "completed_at": "2026-11-17T00:00:00Z", "independence_attestation": True,
            })
        return {
            "schema_version": "1.0", "benchmark_id": "r15d-semantic-source-facts-v2",
            "reviewer_id": "reviewer.gamma", "submitted_at": "2026-11-17T00:00:00Z",
            "attestations": {
                "independent_review": True, "model_outputs_not_seen": True,
                "primary_reviews_seen": True, "v1_answer_key_not_seen": True,
                "v1_labels_not_consulted": True, "conflicts_disclosed": True,
                "conflict_statement": "synthetic test fixture only",
            },
            "cases": cases,
        }

    def run_pipeline(self, disagreement_case=None):
        self.counter += 1
        n = self.counter
        a, b = self.root / f"a-{n}.json", self.root / f"b-{n}.json"
        receipt_a, receipt_b = self.root / f"receipt-a-{n}.json", self.root / f"receipt-b-{n}.json"
        staged_path = self.root / f"staged-{n}.json"
        final_path = self.root / f"final-{n}.json"
        third_path, third_receipt = self.root / f"third-{n}.json", self.root / f"third-receipt-{n}.json"
        manifest_path = self.root / f"frozen-{n}.json"

        a.write_text(json.dumps(self.primary_bundle("reviewer.alpha")), encoding="utf-8")
        b.write_text(json.dumps(self.primary_bundle("reviewer.beta", disagreement_case)), encoding="utf-8")
        create_intake_receipt(self.fixture_dir, a, receipt_a, "primary_a", "custodian.v2", "2026-11-17T00:00:00Z", "private_video_check", True)
        create_intake_receipt(self.fixture_dir, b, receipt_b, "primary_b", "custodian.v2", "2026-11-17T00:00:00Z", "private_video_check", True)
        merge = merge_primary_reviews(self.fixture_dir, a, b, receipt_a, receipt_b, staged_path, "custodian.v2", True)
        staged = json.loads(staged_path.read_text(encoding="utf-8"))

        third_submission = None
        third_receipt_path = None
        if disagreement_case:
            third_path.write_text(json.dumps(self.third_bundle(staged)), encoding="utf-8")
            create_intake_receipt(self.fixture_dir, third_path, third_receipt, "third_adjudicator", "custodian.v2", "2026-11-17T00:00:00Z", "private_video_check", True, staged_path)
            third_submission, third_receipt_path = third_path, third_receipt

        final = finalize_adjudication(
            self.fixture_dir, a, b, receipt_a, receipt_b, staged_path, final_path,
            "custodian.v2", True, third_submission, third_receipt_path,
            bool(third_submission), merge["output_sha256"],
        )
        freeze = freeze_adjudication(
            final_path, self.fixture_dir, manifest_path, "2026-11-17T00:00:00Z",
            a, b, receipt_a, receipt_b, staged_path, "custodian.v2", True,
            third_submission, third_receipt_path, bool(third_submission), merge["output_sha256"],
        )
        verified = verify_frozen_manifest(
            final_path, self.fixture_dir, manifest_path, freeze["output_sha256"],
            a, b, receipt_a, receipt_b, staged_path, "custodian.v2", True,
            third_submission, third_receipt_path, bool(third_submission), merge["output_sha256"],
        )
        return {
            "final": final, "freeze": freeze, "verified": verified,
            "final_path": final_path, "manifest_path": manifest_path,
            "reviewer_a": a, "reviewer_b": b, "receipt_a": receipt_a, "receipt_b": receipt_b,
            "staged": staged_path, "third_submission": third_submission,
            "third_receipt": third_receipt_path, "staged_sha256": merge["output_sha256"],
        }

    def test_unanimous_path_freezes_and_verifies_with_inference_disabled(self):
        result = self.run_pipeline()
        manifest = json.loads(result["manifest_path"].read_text(encoding="utf-8"))
        self.assertTrue(result["final"]["valid_complete_adjudication"])
        self.assertTrue(result["freeze"]["valid_frozen_manifest"])
        self.assertTrue(result["verified"]["valid"])
        self.assertEqual(result["verified"]["completed_cases"], 6)
        self.assertTrue(manifest["freeze"]["ground_truth_frozen"])
        self.assertFalse(manifest["freeze"]["model_inference_authorized"])
        self.assertIsNone(manifest["custody_receipts"]["third_adjudicator_receipt_sha256"])

    def test_disagreement_path_freezes_after_receipt_verified_third_adjudication(self):
        result = self.run_pipeline("NAV2-02")
        manifest = json.loads(result["manifest_path"].read_text(encoding="utf-8"))
        case = next(c for c in manifest["cases"] if c["id"] == "NAV2-02")
        self.assertTrue(result["final"]["valid_complete_adjudication"])
        self.assertTrue(result["freeze"]["valid_frozen_manifest"])
        self.assertTrue(result["verified"]["valid"])
        self.assertEqual(case["third_adjudicator"]["reviewer_id"], "reviewer.gamma")
        self.assertIsNotNone(manifest["custody_receipts"]["third_adjudicator_receipt_sha256"])
        self.assertTrue(manifest["freeze"]["ground_truth_frozen"])
        self.assertFalse(manifest["freeze"]["model_inference_authorized"])

    def test_incomplete_staged_packet_cannot_be_frozen(self):
        a, b, staged = self.root / "incomplete-a.json", self.root / "incomplete-b.json", self.root / "incomplete-staged.json"
        ra, rb = self.root / "incomplete-ra.json", self.root / "incomplete-rb.json"
        a.write_text(json.dumps(self.primary_bundle("reviewer.alpha")), encoding="utf-8")
        b.write_text(json.dumps(self.primary_bundle("reviewer.beta", "COB2-01")), encoding="utf-8")
        create_intake_receipt(self.fixture_dir, a, ra, "primary_a", "custodian.v2", "2026-11-17T00:00:00Z", "private_video_check", True)
        create_intake_receipt(self.fixture_dir, b, rb, "primary_b", "custodian.v2", "2026-11-17T00:00:00Z", "private_video_check", True)
        merge_primary_reviews(self.fixture_dir, a, b, ra, rb, staged, "custodian.v2", True)
        with self.assertRaisesRegex(ValueError, "must all be separate paths"):
            freeze_adjudication(staged, self.fixture_dir, self.root / "invalid-frozen.json", "2026-11-17T00:00:00Z", a, b, ra, rb, staged, "custodian.v2", True)

    def test_manifest_provenance_tampering_is_rejected(self):
        result = self.run_pipeline()
        manifest = json.loads(result["manifest_path"].read_text(encoding="utf-8"))
        manifest["freeze_provenance"]["fixture_scanner_sha256"] = "0" * 64
        result["manifest_path"].write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "content or provenance"):
            verify_frozen_manifest(
                result["final_path"], self.fixture_dir, result["manifest_path"], result["freeze"]["output_sha256"],
                result["reviewer_a"], result["reviewer_b"], result["receipt_a"], result["receipt_b"],
                result["staged"], "custodian.v2", True, expected_staged_sha256=result["staged_sha256"],
            )

    def test_input_packet_tampering_after_freeze_is_rejected(self):
        result = self.run_pipeline("COB2-03")
        result["final_path"].write_bytes(result["final_path"].read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "does not exactly match receipt-verified"):
            verify_frozen_manifest(
                result["final_path"], self.fixture_dir, result["manifest_path"], result["freeze"]["output_sha256"],
                result["reviewer_a"], result["reviewer_b"], result["receipt_a"], result["receipt_b"],
                result["staged"], "custodian.v2", True, result["third_submission"], result["third_receipt"],
                True, result["staged_sha256"],
            )

    def test_expected_manifest_digest_mismatch_is_rejected(self):
        result = self.run_pipeline()
        with self.assertRaisesRegex(ValueError, "expected digest"):
            verify_frozen_manifest(
                result["final_path"], self.fixture_dir, result["manifest_path"], "0" * 64,
                result["reviewer_a"], result["reviewer_b"], result["receipt_a"], result["receipt_b"],
                result["staged"], "custodian.v2", True, expected_staged_sha256=result["staged_sha256"],
            )

    def test_freeze_output_collision_is_not_overwritten(self):
        result = self.run_pipeline()
        output = self.root / "existing-manifest.json"
        output.write_text("preserve-me", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            freeze_adjudication(
                result["final_path"], self.fixture_dir, output, "2026-11-17T00:00:00Z",
                result["reviewer_a"], result["reviewer_b"], result["receipt_a"], result["receipt_b"],
                result["staged"], "custodian.v2", True, expected_staged_sha256=result["staged_sha256"],
            )
        self.assertEqual(output.read_text(encoding="utf-8"), "preserve-me")


if __name__ == "__main__":
    unittest.main()
