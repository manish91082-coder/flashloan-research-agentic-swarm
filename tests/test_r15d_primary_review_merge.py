import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_r15d_adjudication import DEFAULT_PACKET
from scripts.merge_r15d_primary_reviews import merge_primary_submissions


class R15DPrimaryReviewMergeTests(unittest.TestCase):
    def setUp(self):
        self.template_bytes = DEFAULT_PACKET.read_bytes()
        self.template = json.loads(self.template_bytes.decode("utf-8"))

    def make_bundle(self, reviewer_id, disagreement_case=None):
        cases = []
        for source in self.template["cases"]:
            pin = {
                key: source[key]
                for key in (
                    "repository", "commit_sha", "tree_sha", "path",
                    "git_blob_sha1", "line_start", "line_end", "excerpt_sha256",
                )
            }
            evidence = [
                f'{pin["path"]}:{pin["line_start"]}-{pin["line_end"]}#sha256:{pin["excerpt_sha256"]}'
            ]
            label = "unknown"
            if disagreement_case == source["id"] and reviewer_id == "reviewer.beta":
                label = "present"
            cases.append({
                "case_id": source["id"],
                "source_pin": pin,
                "label": label,
                "rationale": "This bounded label is based on the exact pinned source excerpt.",
                "evidence_references": evidence,
                "confidence": 0.8,
                "completed_at": "2026-11-17T00:00:00Z",
            })
        return {
            "schema_version": "1.0",
            "benchmark_id": "r15d-semantic-source-facts-v1",
            "reviewer_id": reviewer_id,
            "submitted_at": "2026-11-17T00:00:00Z",
            "attestations": {
                "independent_review": True,
                "model_outputs_not_seen": True,
                "other_reviews_not_seen": True,
                "conflicts_disclosed": True,
                "conflict_statement": "none",
            },
            "cases": cases,
        }

    def write_bundle(self, path, bundle):
        path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    def test_valid_bundles_create_new_staged_packet_without_mutating_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, output = root / "a.json", root / "b.json", root / "merged.json"
            self.write_bundle(a, self.make_bundle("reviewer.alpha", "NAV-02"))
            self.write_bundle(b, self.make_bundle("reviewer.beta", "NAV-02"))
            result = merge_primary_submissions(a, b, output, "custodian.1", True)
            merged = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(result["valid_staged_merge"])
            self.assertEqual(result["case_count"], 6)
            self.assertEqual(result["disagreement_cases"], ["NAV-02"])
            self.assertEqual(merged["cases"][1]["third_adjudicator"]["triggered"], True)
            self.assertIsNone(merged["cases"][1]["third_adjudicator"]["reviewer_id"])
            self.assertEqual(merged["cases"][1]["consensus"]["status"], "pending")
            self.assertFalse(merged["freeze"]["ground_truth_frozen"])
            self.assertFalse(merged["freeze"]["model_inference_authorized"])
            self.assertEqual(DEFAULT_PACKET.read_bytes(), self.template_bytes)
            self.assertEqual(result["output_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())

    def test_identity_verification_attestation_is_mandatory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, output = root / "a.json", root / "b.json", root / "merged.json"
            self.write_bundle(a, self.make_bundle("reviewer.alpha"))
            self.write_bundle(b, self.make_bundle("reviewer.beta"))
            with self.assertRaisesRegex(ValueError, "out-of-band identity verification"):
                merge_primary_submissions(a, b, output, "custodian.1", False)
            self.assertFalse(output.exists())

    def test_same_reviewer_cannot_fill_both_primary_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, output = root / "a.json", root / "b.json", root / "merged.json"
            self.write_bundle(a, self.make_bundle("reviewer.alpha"))
            self.write_bundle(b, self.make_bundle("reviewer.alpha"))
            with self.assertRaisesRegex(ValueError, "identities must be distinct"):
                merge_primary_submissions(a, b, output, "custodian.1", True)
            self.assertFalse(output.exists())

    def test_bad_source_pin_rejected_before_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, output = root / "a.json", root / "b.json", root / "merged.json"
            bundle = self.make_bundle("reviewer.alpha")
            bundle["cases"][0]["source_pin"]["excerpt_sha256"] = "0" * 64
            self.write_bundle(a, bundle)
            self.write_bundle(b, self.make_bundle("reviewer.beta"))
            with self.assertRaisesRegex(ValueError, "reviewer A submission failed validation"):
                merge_primary_submissions(a, b, output, "custodian.1", True)
            self.assertFalse(output.exists())

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, output = root / "a.json", root / "b.json", root / "merged.json"
            self.write_bundle(a, self.make_bundle("reviewer.alpha"))
            self.write_bundle(b, self.make_bundle("reviewer.beta"))
            output.write_text("preserve-me", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                merge_primary_submissions(a, b, output, "custodian.1", True)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve-me")

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, output = root / "a.json", root / "b.json", root / "merged.json"
            a.write_text('{"reviewer_id":"a","reviewer_id":"b"}', encoding="utf-8")
            self.write_bundle(b, self.make_bundle("reviewer.beta"))
            with self.assertRaisesRegex(ValueError, "duplicate-free"):
                merge_primary_submissions(a, b, output, "custodian.1", True)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
