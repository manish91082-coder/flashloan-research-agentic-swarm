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
