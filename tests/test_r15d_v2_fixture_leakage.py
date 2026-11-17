import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_r15d_v2_semantic_fixtures import MANIFEST, build
from scripts.scan_r15d_v2_artifact_leakage import scan_artifact


class R15DV2FixtureLeakageTests(unittest.TestCase):
    def test_v2_build_contains_six_pinned_excerpts_and_no_reference_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "fixture"
            result = build(output_dir=output)
            self.assertEqual(result["benchmark_id"], "r15d-semantic-source-facts-v2")
            self.assertEqual(result["status"], "built_pending_independent_adjudication")
            self.assertEqual(len(result["cases"]), 6)
            self.assertFalse(result["answer_key_included"])
            self.assertTrue(all(len(case["excerpt_sha256"]) == 64 for case in result["cases"]))
            self.assertTrue(all("expected_label" not in case and "label" not in case for case in result["cases"]))
            scan = scan_artifact(output)
            self.assertTrue(scan["valid"], scan["findings"])

    def test_builder_refuses_public_repository_output(self):
        root = Path(__file__).resolve().parents[1]
        with self.assertRaisesRegex(ValueError, "outside the public repository"):
            build(output_dir=root / "research_runs" / "r15d-v2-public-test")

    def test_builder_rejects_answer_key_fields_in_design_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            manifest["cases"][0]["expected_label"] = "present"
            path = Path(tmp) / "leaky-design.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "forbidden answer-key field"):
                build(manifest_path=path, output_dir=Path(tmp) / "output")

    def test_scanner_rejects_answer_key_field_in_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "excerpts").mkdir()
            manifest = {
                "benchmark_id": "r15d-semantic-source-facts-v2",
                "status": "built_pending_independent_adjudication",
                "answer_key_included": False,
                "cases": [{"id": f"CASE-{i}", "expected_label": "present"} for i in range(6)],
            }
            (root / "fixture_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            result = scan_artifact(root)
            self.assertFalse(result["valid"])
            self.assertTrue(any("expected_label" in finding for finding in result["findings"]))

    def test_scanner_rejects_answer_key_in_secondary_json_or_text_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = {
                "benchmark_id": "r15d-semantic-source-facts-v2",
                "status": "built_pending_independent_adjudication",
                "answer_key_included": False,
                "cases": [{"id": f"CASE-{i}"} for i in range(6)],
            }
            (root / "fixture_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (root / "debug.json").write_text('{"gold_label":"absent"}', encoding="utf-8")
            result = scan_artifact(root)
            self.assertFalse(result["valid"])
            self.assertTrue(any("gold_label" in finding for finding in result["findings"]))

    def test_scanner_rejects_duplicate_case_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = {
                "benchmark_id": "r15d-semantic-source-facts-v2",
                "status": "built_pending_independent_adjudication",
                "answer_key_included": False,
                "cases": [{"id": "DUP"} for _ in range(6)],
            }
            (root / "fixture_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            result = scan_artifact(root)
            self.assertFalse(result["valid"])
            self.assertTrue(any("unique objects" in finding for finding in result["findings"]))


if __name__ == "__main__":
    unittest.main()
