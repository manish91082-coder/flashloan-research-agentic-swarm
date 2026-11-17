import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_r15d_v2_semantic_fixtures import build
from scripts.create_r15d_v2_intake_receipt import create_intake_receipt
from scripts.merge_r15d_v2_primary_reviews import merge_primary_reviews
from scripts.verify_r15d_v2_primary_merge import verify_primary_merge


class R15DV2PrimaryMergeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture_dir = self.root / "fixture"
        build(output_dir=self.fixture_dir)
        self.fixture = json.loads((self.fixture_dir / "fixture_manifest.json").read_text(encoding="utf-8"))

    def make_bundle(self, reviewer_id, disagreement_case=None):
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
                "rationale": "Synthetic test-only reviewer rationale based on the pinned excerpt.",
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

    def write_bundle(self, path, bundle):
        path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    def setup_inputs(self, disagreement_case=None, reviewer_b_id="reviewer.beta"):
        a, b = self.root / "a.json", self.root / "b.json"
        receipt_a, receipt_b, output = self.root / "receipt-a.json", self.root / "receipt-b.json", self.root / "staged.json"
        self.write_bundle(a, self.make_bundle("reviewer.alpha"))
        self.write_bundle(b, self.make_bundle(reviewer_b_id, disagreement_case))
        create_intake_receipt(self.fixture_dir, a, receipt_a, "primary_a", "custodian.v2", "2026-11-17T00:00:00Z", "private_video_check", True)
        create_intake_receipt(self.fixture_dir, b, receipt_b, "primary_b", "custodian.v2", "2026-11-17T00:00:00Z", "private_video_check", True)
        return a, b, receipt_a, receipt_b, output

    def test_valid_bundles_merge_and_independently_verify(self):
        a, b, receipt_a, receipt_b, output = self.setup_inputs("NAV2-02")
        created = merge_primary_reviews(self.fixture_dir, a, b, receipt_a, receipt_b, output, "custodian.v2", True)
        verified = verify_primary_merge(self.fixture_dir, a, b, receipt_a, receipt_b, output, "custodian.v2", True, created["output_sha256"])
        packet = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(created["valid_staged_merge"])
        self.assertTrue(verified["valid"])
        self.assertEqual(verified["disagreement_cases"], ["NAV2-02"])
        self.assertTrue(packet["cases"][1]["third_adjudicator"]["triggered"])
        self.assertEqual(packet["cases"][1]["consensus"]["status"], "pending")
        self.assertFalse(packet["freeze"]["ground_truth_frozen"])
        self.assertFalse(packet["freeze"]["model_inference_authorized"])

    def test_unanimous_reviews_have_no_third_adjudication_trigger(self):
        a, b, receipt_a, receipt_b, output = self.setup_inputs()
        result = merge_primary_reviews(self.fixture_dir, a, b, receipt_a, receipt_b, output, "custodian.v2", True)
        packet = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["disagreement_cases"], [])
        self.assertTrue(all(not c["third_adjudicator"]["triggered"] for c in packet["cases"]))

    def test_custodian_identity_attestation_is_required(self):
        a, b, receipt_a, receipt_b, output = self.setup_inputs()
        with self.assertRaisesRegex(ValueError, "verify both reviewer identities out of band"):
            merge_primary_reviews(self.fixture_dir, a, b, receipt_a, receipt_b, output, "custodian.v2", False)
        self.assertFalse(output.exists())

    def test_same_reviewer_cannot_fill_both_slots(self):
        a, b, receipt_a, receipt_b, output = self.setup_inputs(reviewer_b_id="reviewer.alpha")
        with self.assertRaisesRegex(ValueError, "identities must be distinct"):
            merge_primary_reviews(self.fixture_dir, a, b, receipt_a, receipt_b, output, "custodian.v2", True)
        self.assertFalse(output.exists())

    def test_output_collision_is_never_overwritten(self):
        a, b, receipt_a, receipt_b, output = self.setup_inputs()
        output.write_text("preserve-me", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            merge_primary_reviews(self.fixture_dir, a, b, receipt_a, receipt_b, output, "custodian.v2", True)
        self.assertEqual(output.read_text(encoding="utf-8"), "preserve-me")

    def test_independent_verifier_detects_reviewer_bundle_tampering(self):
        a, b, receipt_a, receipt_b, output = self.setup_inputs()
        created = merge_primary_reviews(self.fixture_dir, a, b, receipt_a, receipt_b, output, "custodian.v2", True)
        bundle = json.loads(a.read_text(encoding="utf-8"))
        bundle["cases"][0]["rationale"] = "tampered after merge"
        a.write_text(json.dumps(bundle), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not exactly match"):
            verify_primary_merge(self.fixture_dir, a, b, receipt_a, receipt_b, output, "custodian.v2", True, created["output_sha256"])

    def test_independent_verifier_detects_staged_packet_tampering(self):
        a, b, receipt_a, receipt_b, output = self.setup_inputs()
        merge_primary_reviews(self.fixture_dir, a, b, receipt_a, receipt_b, output, "custodian.v2", True)
        packet = json.loads(output.read_text(encoding="utf-8"))
        packet["cases"][0]["consensus"]["label"] = "present"
        output.write_text(json.dumps(packet, indent=2), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not exactly match"):
            verify_primary_merge(self.fixture_dir, a, b, receipt_a, receipt_b, output, "custodian.v2", True)

    def test_fixture_artifact_tampering_blocks_merge(self):
        a, b, receipt_a, receipt_b, output = self.setup_inputs()
        excerpt = self.fixture_dir / self.fixture["cases"][0]["excerpt_file"]
        excerpt.write_bytes(excerpt.read_bytes() + b"tamper")
        with self.assertRaisesRegex(ValueError, "excerpt bytes or SHA-256"):
            merge_primary_reviews(self.fixture_dir, a, b, receipt_a, receipt_b, output, "custodian.v2", True)
        self.assertFalse(output.exists())



    def test_missing_primary_receipt_blocks_merge(self):
        a, b, receipt_a, receipt_b, output = self.setup_inputs()
        receipt_b.unlink()
        with self.assertRaisesRegex(ValueError, "receipt"):
            merge_primary_reviews(self.fixture_dir, a, b, receipt_a, receipt_b, output, "custodian.v2", True)
        self.assertFalse(output.exists())

    def test_swapped_primary_receipts_are_rejected(self):
        a, b, receipt_a, receipt_b, output = self.setup_inputs()
        with self.assertRaisesRegex(ValueError, "reviewer slot and custodian"):
            merge_primary_reviews(self.fixture_dir, a, b, receipt_b, receipt_a, output, "custodian.v2", True)
        self.assertFalse(output.exists())

    def test_wrong_custodian_receipt_is_rejected(self):
        a, b, receipt_a, receipt_b, output = self.setup_inputs()
        with self.assertRaisesRegex(ValueError, "custodian"):
            merge_primary_reviews(self.fixture_dir, a, b, receipt_a, receipt_b, output, "custodian.other", True)
        self.assertFalse(output.exists())

    def test_tampered_receipt_is_rejected(self):
        a, b, receipt_a, receipt_b, output = self.setup_inputs()
        receipt = json.loads(receipt_a.read_text(encoding="utf-8"))
        receipt["submission_sha256"] = "0" * 64
        receipt_a.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not exactly match"):
            merge_primary_reviews(self.fixture_dir, a, b, receipt_a, receipt_b, output, "custodian.v2", True)
        self.assertFalse(output.exists())

if __name__ == "__main__":
    unittest.main()
