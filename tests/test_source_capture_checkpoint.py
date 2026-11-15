from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "restore_source_capture_checkpoint.py"
SPEC = importlib.util.spec_from_file_location("source_capture_checkpoint", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SourceCaptureCheckpointHelpersTests(unittest.TestCase):
    def test_coverage_limited_truncated_tree_is_restorable_when_disclosed(self) -> None:
        report = {
            "candidate_code_executed": False,
            "recursive_tree_truncated": True,
            "tree_recovery_attempted": True,
            "tree_recovery_complete": False,
            "source_capture_complete_within_configured_scope": False,
            "limitations": [
                "GitHub returned a truncated recursive tree and bounded recovery did not complete; repository coverage is incomplete."
            ],
        }
        MODULE.validate_report_invariants(report, "PrimeNumbersLabs/primefi-liquidator")

    def test_incomplete_tree_recovery_cannot_claim_complete_source_scope(self) -> None:
        report = {
            "candidate_code_executed": False,
            "recursive_tree_truncated": True,
            "tree_recovery_attempted": True,
            "tree_recovery_complete": False,
            "source_capture_complete_within_configured_scope": True,
            "limitations": [
                "GitHub returned a truncated recursive tree and bounded recovery did not complete; repository coverage is incomplete."
            ],
        }
        with self.assertRaisesRegex(ValueError, "cannot claim complete configured scope"):
            MODULE.validate_report_invariants(report, "org/repo")

    def test_incomplete_tree_recovery_must_be_explicitly_disclosed(self) -> None:
        report = {
            "candidate_code_executed": False,
            "recursive_tree_truncated": True,
            "tree_recovery_attempted": True,
            "tree_recovery_complete": False,
            "source_capture_complete_within_configured_scope": False,
            "limitations": ["Source scope incomplete."],
        }
        with self.assertRaisesRegex(ValueError, "not disclosed"):
            MODULE.validate_report_invariants(report, "org/repo")

    def test_candidate_code_execution_still_fails_restore_invariant(self) -> None:
        report = {
            "candidate_code_executed": True,
            "recursive_tree_truncated": False,
            "tree_recovery_attempted": False,
            "tree_recovery_complete": True,
            "source_capture_complete_within_configured_scope": True,
        }
        with self.assertRaisesRegex(ValueError, "candidate-code execution safety invariant"):
            MODULE.validate_report_invariants(report, "org/repo")

    def test_recovery_flags_must_be_boolean_and_consistent(self) -> None:
        report = {
            "candidate_code_executed": False,
            "recursive_tree_truncated": False,
            "tree_recovery_attempted": False,
            "tree_recovery_complete": None,
            "source_capture_complete_within_configured_scope": True,
        }
        with self.assertRaisesRegex(ValueError, "missing or not boolean"):
            MODULE.validate_report_invariants(report, "org/repo")
    def test_git_blob_sha_uses_git_object_framing(self) -> None:
        self.assertEqual(
            MODULE.git_blob_sha(b""),
            "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
        )

    def test_safe_child_accepts_relative_vault_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "ab" / "blob"
            self.assertEqual(MODULE.safe_child(root, "ab/blob"), expected.resolve())

    def test_safe_child_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                MODULE.safe_child(Path(directory), "../outside")


if __name__ == "__main__":
    unittest.main()
