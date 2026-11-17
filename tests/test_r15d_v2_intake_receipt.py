import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_r15d_v2_semantic_fixtures import build
from scripts.create_r15d_v2_intake_receipt import create_intake_receipt
from scripts.merge_r15d_v2_primary_reviews import merge_primary_reviews
from scripts.validate_r15d_v2_review_submission import load_fixture_bundle

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_SCHEMA = ROOT / "research/R15D_V2_INTAKE_RECEIPT.schema.json"


class R15DV2IntakeReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture_dir = self.root / "fixture"
        build(output_dir=self.fixture_dir)
        self.fixture = load_fixture_bundle(self.fixture_dir)

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
                "rationale": "Synthetic private review rationale.",
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
                "rationale": "Synthetic third adjudication rationale.",
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

    def test_primary_receipt_contains_only_metadata_and_hashes(self):
        submission = self.root / "reviewer-a.json"
        submission.write_text(json.dumps(self.primary_bundle("reviewer.alpha")), encoding="utf-8")
        raw = submission.read_bytes()
        output = self.root / "receipt.json"
        result = create_intake_receipt(
            self.fixture_dir, submission, output, "primary_a", "custodian.v2",
            "2026-11-17T00:00:00Z", "private_video_check", True,
        )
        receipt = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(result["valid_receipt"])
        self.assertEqual(receipt["submission_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertFalse(receipt["labels_included"])
        self.assertFalse(receipt["rationales_included"])
        self.assertFalse(receipt["payload_content_included"])
        self.assertTrue(receipt["public_repository_storage_prohibited"])
        self.assertNotIn("cases", receipt)
        self.assertNotIn('"label":', json.dumps(receipt).lower())
        self.assertNotIn('"rationale":', json.dumps(receipt).lower())

    def test_receipt_requires_custodian_identity_verification(self):
        submission = self.root / "reviewer-a.json"
        submission.write_text(json.dumps(self.primary_bundle("reviewer.alpha")), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "out-of-band identity verification"):
            create_intake_receipt(
                self.fixture_dir, submission, self.root / "receipt.json", "primary_a",
                "custodian.v2", "2026-11-17T00:00:00Z", "private_video_check", False,
            )

    def test_receipt_output_inside_public_repository_is_rejected(self):
        submission = self.root / "reviewer-a.json"
        submission.write_text(json.dumps(self.primary_bundle("reviewer.alpha")), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "outside the public repository"):
            create_intake_receipt(
                self.fixture_dir, submission, ROOT / "receipt-leak-test.json", "primary_a",
                "custodian.v2", "2026-11-17T00:00:00Z", "private_video_check", True,
            )

    def test_invalid_submission_cannot_receive_receipt(self):
        submission = self.root / "invalid.json"
        bundle = self.primary_bundle("reviewer.alpha")
        bundle["attestations"]["v1_answer_key_not_seen"] = False
        submission.write_text(json.dumps(bundle), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "failed validation"):
            create_intake_receipt(
                self.fixture_dir, submission, self.root / "receipt.json", "primary_a",
                "custodian.v2", "2026-11-17T00:00:00Z", "private_video_check", True,
            )

    def test_third_receipt_preserves_primary_visibility_attestation_without_payload(self):
        a, b, staged_path = self.root / "a.json", self.root / "b.json", self.root / "staged.json"
        receipt_a, receipt_b = self.root / "receipt-a.json", self.root / "receipt-b.json"
        a.write_text(json.dumps(self.primary_bundle("reviewer.alpha")), encoding="utf-8")
        b.write_text(json.dumps(self.primary_bundle("reviewer.beta", "NAV2-01")), encoding="utf-8")
        create_intake_receipt(self.fixture_dir, a, receipt_a, "primary_a", "custodian.v2", "2026-11-17T00:00:00Z", "private_video_check", True)
        create_intake_receipt(self.fixture_dir, b, receipt_b, "primary_b", "custodian.v2", "2026-11-17T00:00:00Z", "private_video_check", True)
        merge_primary_reviews(self.fixture_dir, a, b, receipt_a, receipt_b, staged_path, "custodian.v2", True)
        staged = json.loads(staged_path.read_text(encoding="utf-8"))
        third_path = self.root / "third.json"
        third_path.write_text(json.dumps(self.third_bundle(staged)), encoding="utf-8")
        output = self.root / "third-receipt.json"
        create_intake_receipt(
            self.fixture_dir, third_path, output, "third_adjudicator", "custodian.v2",
            "2026-11-17T00:00:00Z", "institutional_identity_check", True, staged_path,
        )
        receipt = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(receipt["attestation_summary"]["primary_reviews_seen"])
        self.assertFalse(receipt["attestation_summary"]["other_reviews_not_seen"])
        self.assertFalse(receipt["labels_included"])
        self.assertFalse(receipt["rationales_included"])

    def test_receipt_schema_is_strict_and_forbids_payload_content(self):
        schema = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertIs(schema["properties"]["labels_included"]["const"], False)
        self.assertIs(schema["properties"]["rationales_included"]["const"], False)
        self.assertIs(schema["properties"]["payload_content_included"]["const"], False)


if __name__ == "__main__":
    unittest.main()
