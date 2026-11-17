import copy
import json
import unittest
from pathlib import Path

from scripts.validate_r15d_adjudication import DEFAULT_PACKET
from scripts.validate_r15d_review_submission import validate_submission

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION_SCHEMA = ROOT / "research/R15D_REVIEWER_SUBMISSION.schema.json"


class R15DReviewSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads(DEFAULT_PACKET.read_text(encoding="utf-8"))

    def make_bundle(self):
        cases = []
        for source_case in self.packet["cases"]:
            pin = {
                key: source_case[key]
                for key in (
                    "repository", "commit_sha", "tree_sha", "path",
                    "git_blob_sha1", "line_start", "line_end", "excerpt_sha256",
                )
            }
            evidence = [
                f'{pin["path"]}:{pin["line_start"]}-{pin["line_end"]}#sha256:{pin["excerpt_sha256"]}'
            ]
            cases.append({
                "case_id": source_case["id"],
                "source_pin": pin,
                "label": "unknown",
                "rationale": "The bounded proposition is not fully established by the supplied source excerpt.",
                "evidence_references": evidence,
                "confidence": 0.7,
                "completed_at": "2026-11-17T00:00:00Z",
            })
        return {
            "schema_version": "1.0",
            "benchmark_id": "r15d-semantic-source-facts-v1",
            "reviewer_id": "reviewer.alpha",
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

    def test_valid_six_case_bundle_passes_format_and_pin_validation(self):
        result = validate_submission(self.make_bundle())
        self.assertTrue(result["valid"])
        self.assertEqual(result["case_count"], 6)
        self.assertEqual(result["identity_verification"], "not_performed_by_validator")

    def test_missing_duplicate_and_extra_case_ids_rejected(self):
        for mutate in ("missing", "duplicate", "extra"):
            bundle = self.make_bundle()
            if mutate == "missing":
                bundle["cases"].pop()
            elif mutate == "duplicate":
                bundle["cases"][0]["case_id"] = bundle["cases"][1]["case_id"]
            else:
                bundle["cases"][0]["case_id"] = "UNKNOWN"
            with self.subTest(mutate=mutate):
                self.assertFalse(validate_submission(bundle)["valid"])

    def test_unhashable_case_id_rejected_without_exception(self):
        bundle = self.make_bundle()
        bundle["cases"][0]["case_id"] = []
        result = validate_submission(bundle)
        self.assertFalse(result["valid"])
        self.assertTrue(any("case IDs" in error for error in result["errors"]))

    def test_source_pin_tampering_rejected(self):
        bundle = self.make_bundle()
        bundle["cases"][0]["source_pin"]["commit_sha"] = "0" * 40
        result = validate_submission(bundle)
        self.assertFalse(result["valid"])
        self.assertTrue(any("source pin" in error for error in result["errors"]))

    def test_wrong_and_duplicate_evidence_references_rejected(self):
        for mode in ("wrong", "duplicate"):
            bundle = self.make_bundle()
            refs = bundle["cases"][0]["evidence_references"]
            if mode == "wrong":
                refs[0] = "other.sol:1-2#sha256:" + "0" * 64
            else:
                refs.append(refs[0])
            with self.subTest(mode=mode):
                result = validate_submission(bundle)
                self.assertFalse(result["valid"])
                self.assertTrue(any("evidence references" in error for error in result["errors"]))

    def test_malformed_label_and_boolean_confidence_rejected_without_exception(self):
        for field, value in (("label", []), ("confidence", True)):
            bundle = self.make_bundle()
            bundle["cases"][0][field] = value
            with self.subTest(field=field):
                result = validate_submission(bundle)
                self.assertFalse(result["valid"])

    def test_missing_blinding_attestation_rejected(self):
        bundle = self.make_bundle()
        bundle["attestations"]["model_outputs_not_seen"] = False
        result = validate_submission(bundle)
        self.assertFalse(result["valid"])
        self.assertTrue(any("model_outputs_not_seen" in error for error in result["errors"]))

    def test_invalid_and_non_utc_timestamps_rejected(self):
        for field, value in (("submitted_at", "yesterday"), ("completed_at", "2026-11-17T05:30:00+05:30")):
            bundle = self.make_bundle()
            if field == "submitted_at":
                bundle[field] = value
            else:
                bundle["cases"][0][field] = value
            with self.subTest(field=field):
                self.assertFalse(validate_submission(bundle)["valid"])

    def test_unknown_fields_rejected_at_all_levels(self):
        bundle = self.make_bundle()
        bundle["unexpected"] = "extra"
        self.assertFalse(validate_submission(bundle)["valid"])
        bundle = self.make_bundle()
        bundle["cases"][0]["unexpected"] = "extra"
        self.assertFalse(validate_submission(bundle)["valid"])
        bundle = self.make_bundle()
        bundle["attestations"]["unexpected"] = True
        self.assertFalse(validate_submission(bundle)["valid"])

    def test_reviewer_id_must_be_normalized_and_nonblank(self):
        for reviewer_id in (" reviewer.alpha ", "x", ""):
            bundle = self.make_bundle()
            bundle["reviewer_id"] = reviewer_id
            with self.subTest(reviewer_id=reviewer_id):
                self.assertFalse(validate_submission(bundle)["valid"])


    def test_submission_schema_is_strict_draft_2020_12(self):
        schema = json.loads(SUBMISSION_SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), {"schema_version", "benchmark_id", "reviewer_id", "submitted_at", "attestations", "cases"})

    def test_submission_schema_pins_six_cases_and_unique_evidence(self):
        schema = json.loads(SUBMISSION_SCHEMA.read_text(encoding="utf-8"))
        cases = schema["properties"]["cases"]
        self.assertEqual((cases["minItems"], cases["maxItems"]), (6, 6))
        props = cases["items"]["properties"]
        self.assertTrue(props["evidence_references"]["uniqueItems"])
        self.assertEqual(set(props["case_id"]["enum"]), {"NAV-01", "NAV-02", "NAV-03", "COB-01", "COB-02", "COB-03"})

    def test_submission_schema_requires_blindness_attestations(self):
        schema = json.loads(SUBMISSION_SCHEMA.read_text(encoding="utf-8"))
        attestations = schema["properties"]["attestations"]
        for field in ("independent_review", "model_outputs_not_seen", "other_reviews_not_seen", "conflicts_disclosed"):
            self.assertIs(attestations["properties"][field]["const"], True)


if __name__ == "__main__":
    unittest.main()
