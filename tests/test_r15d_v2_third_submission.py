import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_r15d_v2_semantic_fixtures import build
from scripts.merge_r15d_v2_primary_reviews import merge_primary_reviews
from scripts.validate_r15d_v2_third_submission import validate_third_submission

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "research/R15D_V2_THIRD_ADJUDICATION_SUBMISSION.schema.json"


class R15DV2ThirdSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture_dir = self.root / "fixture"
        build(output_dir=self.fixture_dir)
        self.fixture = json.loads((self.fixture_dir / "fixture_manifest.json").read_text(encoding="utf-8"))

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
                "rationale": "Synthetic primary review grounded in the pinned excerpt.",
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

    def make_staged(self, disagreement_case="NAV2-02"):
        a, b, staged = self.root / "a.json", self.root / "b.json", self.root / "staged.json"
        a.write_text(json.dumps(self.primary_bundle("reviewer.alpha")), encoding="utf-8")
        b.write_text(json.dumps(self.primary_bundle("reviewer.beta", disagreement_case)), encoding="utf-8")
        merge_primary_reviews(self.fixture_dir, a, b, staged, "custodian.v2", True)
        return a, b, staged, json.loads(staged.read_text(encoding="utf-8"))

    def third_bundle(self, staged, reviewer_id="reviewer.gamma"):
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
                "rationale": "Synthetic third review after seeing both primary records, without model outputs.",
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

    def test_valid_third_bundle_matches_exact_disagreement_set(self):
        _, _, _, staged = self.make_staged()
        result = validate_third_submission(self.fixture, staged, self.third_bundle(staged))
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["disagreement_cases"], ["NAV2-02"])
        self.assertEqual(result["reviewer_id"], "reviewer.gamma")

    def test_third_reviewer_must_differ_from_both_primary_reviewers(self):
        _, _, _, staged = self.make_staged()
        result = validate_third_submission(self.fixture, staged, self.third_bundle(staged, "reviewer.alpha"))
        self.assertFalse(result["valid"])
        self.assertTrue(any("distinct from both primary" in e for e in result["errors"]))

    def test_third_bundle_must_cover_all_and_only_disagreements(self):
        _, _, _, staged = self.make_staged()
        bundle = self.third_bundle(staged)
        bundle["cases"] = []
        result = validate_third_submission(self.fixture, staged, bundle)
        self.assertFalse(result["valid"])
        self.assertTrue(any("exactly the staged disagreement cases" in e for e in result["errors"]))

    def test_third_bundle_rejected_when_no_disagreement_exists(self):
        _, _, _, staged = self.make_staged(None)
        result = validate_third_submission(self.fixture, staged, self.third_bundle(staged))
        self.assertFalse(result["valid"])
        self.assertTrue(any("no disagreement exists" in e for e in result["errors"]))

    def test_model_output_and_v1_answer_key_exposure_are_hard_failures(self):
        for field in ("model_outputs_not_seen", "v1_answer_key_not_seen", "v1_labels_not_consulted"):
            _, _, _, staged = self.make_staged()
            bundle = self.third_bundle(staged)
            bundle["attestations"][field] = False
            with self.subTest(field=field):
                result = validate_third_submission(self.fixture, staged, bundle)
                self.assertFalse(result["valid"])
                self.assertTrue(any(field in e for e in result["errors"]))

    def test_staged_fixture_digest_and_custody_tampering_are_rejected(self):
        _, _, _, staged = self.make_staged()
        staged["fixture_manifest_sha256"] = "0" * 64
        result = validate_third_submission(self.fixture, staged, self.third_bundle(staged))
        self.assertFalse(result["valid"])
        self.assertTrue(any("digest does not match" in e for e in result["errors"]))
        _, _, _, staged = self.make_staged()
        staged["custody"]["primary_reviewer_identities_verified_out_of_band"] = False
        result = validate_third_submission(self.fixture, staged, self.third_bundle(staged))
        self.assertFalse(result["valid"])
        self.assertTrue(any("custodian identity-verification" in e for e in result["errors"]))

    def test_third_source_pin_and_duplicate_evidence_rejected(self):
        _, _, _, staged = self.make_staged()
        bundle = self.third_bundle(staged)
        bundle["cases"][0]["source_pin"]["excerpt_sha256"] = "0" * 64
        bundle["cases"][0]["evidence_references"].append(bundle["cases"][0]["evidence_references"][0])
        result = validate_third_submission(self.fixture, staged, bundle)
        self.assertFalse(result["valid"])

    def test_schema_requires_primary_visibility_and_v1_non_exposure(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        props = schema["properties"]["attestations"]["properties"]
        self.assertIs(props["primary_reviews_seen"]["const"], True)
        self.assertIs(props["model_outputs_not_seen"]["const"], True)
        self.assertIs(props["v1_answer_key_not_seen"]["const"], True)
        self.assertIs(props["v1_labels_not_consulted"]["const"], True)


if __name__ == "__main__":
    unittest.main()
