import json
import tempfile
import unittest
from pathlib import Path

from scripts.finalize_r15d_adjudication import finalize_adjudication
from scripts.freeze_r15d_adjudication import freeze
from scripts.merge_r15d_primary_reviews import merge_primary_submissions
from scripts.validate_r15d_adjudication import DEFAULT_PACKET
from scripts.verify_r15d_frozen_manifest import verify_frozen_manifest


class R15DEndToEndFreezePipelineTests(unittest.TestCase):
    def setUp(self):
        self.template_bytes = DEFAULT_PACKET.read_bytes()
        self.template = json.loads(self.template_bytes.decode("utf-8"))

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
                "rationale": "Synthetic test-only primary review based on the exact pinned excerpt.",
                "evidence_references": refs, "confidence": 0.8,
                "completed_at": "2026-11-17T00:00:00Z",
            })
        return {
            "schema_version": "1.0", "benchmark_id": "r15d-semantic-source-facts-v1",
            "reviewer_id": reviewer_id, "submitted_at": "2026-11-17T00:00:00Z",
            "attestations": {
                "independent_review": True, "model_outputs_not_seen": True,
                "other_reviews_not_seen": True, "conflicts_disclosed": True,
                "conflict_statement": "synthetic test fixture only",
            },
            "cases": cases,
        }

    def third_bundle(self, staged):
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
                "rationale": "Synthetic test-only third adjudication for pipeline verification.",
                "evidence_references": refs, "confidence": 0.9,
                "completed_at": "2026-11-17T00:00:00Z", "independence_attestation": True,
            })
        return {
            "schema_version": "1.0", "benchmark_id": "r15d-semantic-source-facts-v1",
            "reviewer_id": "reviewer.gamma", "submitted_at": "2026-11-17T00:00:00Z",
            "attestations": {
                "independent_review": True, "model_outputs_not_seen": True,
                "primary_reviews_seen": True, "conflicts_disclosed": True,
                "conflict_statement": "synthetic test fixture only",
            },
            "cases": cases,
        }

    def run_pipeline(self, root, disagreement_case=None):
        a, b = root / "reviewer-a.json", root / "reviewer-b.json"
        staged_path, final_path = root / "staged.json", root / "final.json"
        manifest_path = root / "frozen-manifest.json"
        a.write_text(json.dumps(self.primary_bundle("reviewer.alpha")), encoding="utf-8")
        b.write_text(json.dumps(self.primary_bundle("reviewer.beta", disagreement_case)), encoding="utf-8")
        merge = merge_primary_submissions(a, b, staged_path, "custodian.synthetic", True)
        staged = json.loads(staged_path.read_text(encoding="utf-8"))
        third_path = None
        if disagreement_case:
            third_path = root / "third.json"
            third_path.write_text(json.dumps(self.third_bundle(staged)), encoding="utf-8")
        final = finalize_adjudication(
            a, b, staged_path, final_path, "custodian.synthetic", True,
            third_path, bool(third_path), merge["output_sha256"],
        )
        digest = freeze(final_path, manifest_path, "2026-11-17T00:00:00Z")
        verified = verify_frozen_manifest(final_path, manifest_path, digest)
        return final, digest, verified, final_path, manifest_path

    def test_unanimous_path_runs_from_private_bundles_to_verified_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            final, digest, verified, final_path, manifest_path = self.run_pipeline(Path(tmp))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(final["valid_complete_adjudication"])
            self.assertTrue(verified["valid"])
            self.assertEqual(verified["frozen_manifest_sha256"], digest)
            self.assertEqual(verified["completed_cases"], 6)
            self.assertTrue(manifest["freeze"]["ground_truth_frozen"])
            self.assertFalse(manifest["freeze"]["model_inference_authorized"])
            self.assertEqual(DEFAULT_PACKET.read_bytes(), self.template_bytes)

    def test_disagreement_path_runs_through_third_review_and_verified_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            final, digest, verified, final_path, manifest_path = self.run_pipeline(Path(tmp), "NAV-02")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            nav = next(c for c in manifest["cases"] if c["id"] == "NAV-02")
            self.assertTrue(verified["valid"])
            self.assertEqual(verified["frozen_manifest_sha256"], digest)
            self.assertEqual(nav["third_adjudicator"]["reviewer_id"], "reviewer.gamma")
            self.assertEqual(nav["consensus"]["label"], "present")
            self.assertTrue(manifest["freeze"]["ground_truth_frozen"])
            self.assertFalse(manifest["freeze"]["model_inference_authorized"])
            self.assertEqual(DEFAULT_PACKET.read_bytes(), self.template_bytes)

    def test_frozen_manifest_verifier_detects_post_freeze_input_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, digest, _, final_path, manifest_path = self.run_pipeline(Path(tmp))
            final_path.write_bytes(final_path.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "provenance"):
                verify_frozen_manifest(final_path, manifest_path, digest)



    def test_primary_bundle_tampering_after_merge_blocks_finalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, staged = root / "a.json", root / "b.json", root / "staged.json"
            a.write_text(json.dumps(self.primary_bundle("reviewer.alpha")), encoding="utf-8")
            b.write_text(json.dumps(self.primary_bundle("reviewer.beta")), encoding="utf-8")
            merge_primary_submissions(a, b, staged, "custodian.synthetic", True)
            changed = json.loads(a.read_text(encoding="utf-8"))
            changed["cases"][0]["rationale"] = "tampered after staged merge"
            a.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not exactly match"):
                finalize_adjudication(a, b, staged, root / "final.json", "custodian.synthetic", True)
            self.assertFalse((root / "final.json").exists())

    def test_staged_packet_tampering_blocks_finalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.json"
            b = root / "b.json"
            staged = root / "staged.json"
            a.write_text(json.dumps(self.primary_bundle("reviewer.alpha")), encoding="utf-8")
            b.write_text(json.dumps(self.primary_bundle("reviewer.beta")), encoding="utf-8")
            merge_primary_submissions(a, b, staged, "custodian.synthetic", True)
            changed = json.loads(staged.read_text(encoding="utf-8"))
            changed["cases"][0]["reviewers"][0]["label"] = "absent"
            staged.write_text(json.dumps(changed, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not exactly match"):
                finalize_adjudication(a, b, staged, root / "final.json", "custodian.synthetic", True)
            self.assertFalse((root / "final.json").exists())

    def test_third_identity_collision_blocks_disagreement_finalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, staged = root / "a.json", root / "b.json", root / "staged.json"
            a.write_text(json.dumps(self.primary_bundle("reviewer.alpha")), encoding="utf-8")
            b.write_text(json.dumps(self.primary_bundle("reviewer.beta", "NAV-02")), encoding="utf-8")
            merge_primary_submissions(a, b, staged, "custodian.synthetic", True)
            staged_packet = json.loads(staged.read_text(encoding="utf-8"))
            third = self.third_bundle(staged_packet)
            third["reviewer_id"] = "reviewer.alpha"
            third_path = root / "third.json"
            third_path.write_text(json.dumps(third), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "third-adjudicator submission failed validation"):
                finalize_adjudication(a, b, staged, root / "final.json", "custodian.synthetic", True, third_path, True)
            self.assertFalse((root / "final.json").exists())

    def test_disagreement_without_third_bundle_blocks_end_to_end_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, staged = root / "a.json", root / "b.json", root / "staged.json"
            a.write_text(json.dumps(self.primary_bundle("reviewer.alpha")), encoding="utf-8")
            b.write_text(json.dumps(self.primary_bundle("reviewer.beta", "NAV-03")), encoding="utf-8")
            merge_primary_submissions(a, b, staged, "custodian.synthetic", True)
            with self.assertRaisesRegex(ValueError, "third-adjudicator submission is required"):
                finalize_adjudication(a, b, staged, root / "final.json", "custodian.synthetic", True)
            self.assertFalse((root / "final.json").exists())

    def test_frozen_manifest_tampering_is_rejected_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, digest, _, final_path, manifest_path = self.run_pipeline(Path(tmp), "COB-01")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["freeze_provenance"]["validator_sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "provenance"):
                verify_frozen_manifest(final_path, manifest_path, digest)


if __name__ == "__main__":
    unittest.main()
