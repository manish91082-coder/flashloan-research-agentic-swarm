import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_r15d_adjudication import DEFAULT_PACKET
from scripts.merge_r15d_primary_reviews import merge_primary_submissions
from scripts.validate_r15d_third_adjudication_submission import validate_third_submission


class R15DThirdAdjudicationSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.template = json.loads(DEFAULT_PACKET.read_text(encoding="utf-8"))

    def make_primary_bundle(self, reviewer_id, disagreement_case="NAV-02"):
        cases = []
        for source in self.template["cases"]:
            pin = {key: source[key] for key in (
                "repository", "commit_sha", "tree_sha", "path",
                "git_blob_sha1", "line_start", "line_end", "excerpt_sha256",
            )}
            evidence = [f'{pin["path"]}:{pin["line_start"]}-{pin["line_end"]}#sha256:{pin["excerpt_sha256"]}']
            label = "unknown"
            if reviewer_id == "reviewer.beta" and source["id"] == disagreement_case:
                label = "present"
            cases.append({
                "case_id": source["id"], "source_pin": pin, "label": label,
                "rationale": "Primary review rationale grounded in the pinned excerpt.",
                "evidence_references": evidence, "confidence": 0.8,
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

    def staged_packet(self, root, disagreement_case="NAV-02"):
        a, b, out = root / "a.json", root / "b.json", root / "staged.json"
        a.write_text(json.dumps(self.make_primary_bundle("reviewer.alpha")), encoding="utf-8")
        b.write_text(json.dumps(self.make_primary_bundle("reviewer.beta", disagreement_case)), encoding="utf-8")
        merge_primary_submissions(a, b, out, "custodian.1", True)
        return json.loads(out.read_text(encoding="utf-8"))

    def make_third_bundle(self, staged, reviewer_id="reviewer.gamma"):
        cases = []
        for source in staged["cases"]:
            if not source["consensus"]["disagreement"]:
                continue
            pin = {key: source[key] for key in (
                "repository", "commit_sha", "tree_sha", "path",
                "git_blob_sha1", "line_start", "line_end", "excerpt_sha256",
            )}
            evidence = [f'{pin["path"]}:{pin["line_start"]}-{pin["line_end"]}#sha256:{pin["excerpt_sha256"]}']
            cases.append({
                "case_id": source["id"], "source_pin": pin, "label": "present",
                "rationale": "After reviewing both independent primary records, this adjudicated label best matches the pinned source.",
                "evidence_references": evidence, "confidence": 0.9,
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

    def test_valid_third_submission_covers_exact_disagreement_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = self.staged_packet(Path(tmp))
            bundle = self.make_third_bundle(staged)
            result = validate_third_submission(staged, bundle)
            self.assertTrue(result["valid"])
            self.assertEqual(result["disagreement_cases"], ["NAV-02"])
            self.assertEqual(result["reviewer_id"], "reviewer.gamma")

    def test_third_reviewer_must_be_distinct_from_both_primary_reviewers(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = self.staged_packet(Path(tmp))
            bundle = self.make_third_bundle(staged, "reviewer.alpha")
            result = validate_third_submission(staged, bundle)
            self.assertFalse(result["valid"])
            self.assertTrue(any("distinct from both primary" in error for error in result["errors"]))

    def test_third_submission_must_cover_all_and_only_disagreements(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = self.staged_packet(Path(tmp))
            bundle = self.make_third_bundle(staged)
            bundle["cases"] = []
            result = validate_third_submission(staged, bundle)
            self.assertFalse(result["valid"])
            self.assertTrue(any("exactly the staged packet's disagreement cases" in error for error in result["errors"]))

    def test_third_submission_is_rejected_when_no_disagreement_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = self.staged_packet(Path(tmp), disagreement_case=None)
            bundle = self.make_third_bundle(staged)
            result = validate_third_submission(staged, bundle)
            self.assertFalse(result["valid"])
            self.assertTrue(any("no primary-review disagreement" in error for error in result["errors"]))

    def test_model_output_exposure_is_a_hard_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = self.staged_packet(Path(tmp))
            bundle = self.make_third_bundle(staged)
            bundle["attestations"]["model_outputs_not_seen"] = False
            result = validate_third_submission(staged, bundle)
            self.assertFalse(result["valid"])
            self.assertTrue(any("model_outputs_not_seen" in error for error in result["errors"]))

    def test_third_adjudicator_must_attest_primary_reviews_were_seen(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = self.staged_packet(Path(tmp))
            bundle = self.make_third_bundle(staged)
            bundle["attestations"]["primary_reviews_seen"] = False
            result = validate_third_submission(staged, bundle)
            self.assertFalse(result["valid"])
            self.assertTrue(any("primary_reviews_seen" in error for error in result["errors"]))

    def test_wrong_source_pin_and_duplicate_evidence_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = self.staged_packet(Path(tmp))
            bundle = self.make_third_bundle(staged)
            bundle["cases"][0]["source_pin"]["excerpt_sha256"] = "0" * 64
            bundle["cases"][0]["evidence_references"].append(bundle["cases"][0]["evidence_references"][0])
            result = validate_third_submission(staged, bundle)
            self.assertFalse(result["valid"])
            self.assertTrue(any("source pin mismatch" in error for error in result["errors"]))
            self.assertTrue(any("evidence must match" in error for error in result["errors"]))

    def test_boolean_confidence_and_unattested_case_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = self.staged_packet(Path(tmp))
            bundle = self.make_third_bundle(staged)
            bundle["cases"][0]["confidence"] = True
            bundle["cases"][0]["independence_attestation"] = False
            result = validate_third_submission(staged, bundle)
            self.assertFalse(result["valid"])
            self.assertTrue(any("confidence must be a number" in error for error in result["errors"]))
            self.assertTrue(any("case-level independence" in error for error in result["errors"]))

    def test_unstable_primary_identity_in_staged_packet_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = self.staged_packet(Path(tmp))
            staged["cases"][3]["reviewers"][0]["reviewer_id"] = "substitute"
            result = validate_third_submission(staged, self.make_third_bundle(staged))
            self.assertFalse(result["valid"])
            self.assertTrue(any("stable identity" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
