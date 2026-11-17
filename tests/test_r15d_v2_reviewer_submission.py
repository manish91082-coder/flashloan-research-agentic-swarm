import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_r15d_v2_semantic_fixtures import build
from scripts.validate_r15d_v2_review_submission import load_fixture_bundle, validate_submission

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "research/R15D_V2_REVIEWER_SUBMISSION.schema.json"


class R15DV2ReviewerSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture_dir = self.root / "fixture"
        build(output_dir=self.fixture_dir)
        self.fixture = load_fixture_bundle(self.fixture_dir)

    def make_bundle(self):
        cases = []
        for source in self.fixture["cases"]:
            pin = {key: source[key] for key in (
                "repository", "commit_sha", "tree_sha", "path",
                "git_blob_sha1", "line_start", "line_end", "excerpt_sha256",
            )}
            refs = [f'{pin["path"]}:{pin["line_start"]}-{pin["line_end"]}#sha256:{pin["excerpt_sha256"]}']
            cases.append({
                "case_id": source["id"],
                "source_pin": pin,
                "label": "unknown",
                "rationale": "The proposition is evaluated only against the supplied pinned source excerpt.",
                "evidence_references": refs,
                "confidence": 0.75,
                "completed_at": "2026-11-17T00:00:00Z",
                "independence_attestation": True,
            })
        return {
            "schema_version": "1.0",
            "benchmark_id": "r15d-semantic-source-facts-v2",
            "reviewer_id": "reviewer.v2.alpha",
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

    def test_valid_bundle_passes_against_verified_label_free_fixture(self):
        result = validate_submission(self.make_bundle(), self.fixture)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["case_count"], 6)
        self.assertEqual(result["identity_verification"], "not_performed_by_validator")

    def test_schema_is_strict_and_contains_exact_v2_case_ids(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["properties"]["cases"]["items"]["properties"]["case_id"]["enum"]), {c["id"] for c in self.fixture["cases"]})
        self.assertTrue(schema["properties"]["cases"]["items"]["properties"]["evidence_references"]["uniqueItems"])

    def test_missing_duplicate_and_unknown_cases_rejected(self):
        for mode in ("missing", "duplicate", "unknown"):
            bundle = self.make_bundle()
            if mode == "missing":
                bundle["cases"].pop()
            elif mode == "duplicate":
                bundle["cases"][0]["case_id"] = bundle["cases"][1]["case_id"]
            else:
                bundle["cases"][0]["case_id"] = "NAV-01"
            with self.subTest(mode=mode):
                self.assertFalse(validate_submission(bundle, self.fixture)["valid"])

    def test_wrong_source_pin_and_evidence_are_rejected(self):
        for mode in ("pin", "wrong_evidence", "duplicate_evidence"):
            bundle = self.make_bundle()
            if mode == "pin":
                bundle["cases"][0]["source_pin"]["excerpt_sha256"] = "0" * 64
            elif mode == "wrong_evidence":
                bundle["cases"][0]["evidence_references"][0] = "other.sol:1-2#sha256:" + "0" * 64
            else:
                bundle["cases"][0]["evidence_references"].append(bundle["cases"][0]["evidence_references"][0])
            with self.subTest(mode=mode):
                result = validate_submission(bundle, self.fixture)
                self.assertFalse(result["valid"])

    def test_bad_attestations_and_boolean_confidence_are_rejected(self):
        bundle = self.make_bundle()
        bundle["attestations"]["model_outputs_not_seen"] = False
        bundle["cases"][0]["confidence"] = True
        result = validate_submission(bundle, self.fixture)
        self.assertFalse(result["valid"])
        self.assertTrue(any("model_outputs_not_seen" in error for error in result["errors"]))
        self.assertTrue(any("confidence must be a number" in error for error in result["errors"]))

    def test_non_utc_timestamps_and_unattested_case_rejected(self):
        bundle = self.make_bundle()
        bundle["cases"][0]["completed_at"] = "2026-11-17T05:30:00+05:30"
        bundle["cases"][1]["independence_attestation"] = False
        result = validate_submission(bundle, self.fixture)
        self.assertFalse(result["valid"])

    def test_fixture_excerpt_tampering_is_rejected_before_submission(self):
        excerpt = self.fixture_dir / self.fixture["cases"][0]["excerpt_file"]
        excerpt.write_bytes(excerpt.read_bytes() + b"tamper")
        with self.assertRaisesRegex(ValueError, "excerpt bytes or SHA-256"):
            load_fixture_bundle(self.fixture_dir)

    def test_fixture_manifest_answer_key_injection_is_rejected(self):
        manifest_path = self.fixture_dir / "fixture_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["cases"][0]["expected_label"] = "present"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "leakage scan"):
            load_fixture_bundle(self.fixture_dir)

    def test_zip_fixture_is_supported_and_verified(self):
        archive_path = self.root / "fixture.zip"
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in self.fixture_dir.rglob("*"):
                if file.is_file():
                    archive.write(file, file.relative_to(self.fixture_dir).as_posix())
        loaded = load_fixture_bundle(archive_path)
        self.assertEqual(len(loaded["cases"]), 6)
        self.assertFalse(loaded["answer_key_included"])

    def test_duplicate_json_keys_rejected_in_reviewer_bundle_cli_input_shape(self):
        from scripts.validate_r15d_review_submission import _unique_object
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            json.loads('{"reviewer_id":"a","reviewer_id":"b"}', object_pairs_hook=_unique_object)


if __name__ == "__main__":
    unittest.main()
