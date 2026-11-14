from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from flashloan_research.mission_queue import validate_mission
from flashloan_research.storage import git_blob_sha


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "initialize_agentic_capture_mission.py"
SPEC = importlib.util.spec_from_file_location("agentic_capture_bridge", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AgenticCaptureBridgeTests(unittest.TestCase):
    def test_payload_matches_agent_form_validation_contract(self) -> None:
        payload = MODULE.form_payload(12)
        validated = validate_mission(payload)
        self.assertEqual(validated["mission_id"], "flashloan-research-43600488013")
        self.assertEqual(len(validated["scope"]["discovery_query_families"]), 11)
        self.assertFalse(validated["safety_policy"]["execute_candidate_code"])
        self.assertTrue(validated["agent_policy"]["independent_review"])

    def test_load_reports_requires_pinned_identity_and_verified_blobs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_dir = root / "reports"
            vault = root / "vault"
            report_dir.mkdir()
            vault.mkdir()
            blob = b"contract FlashLoan {}\n"
            blob_sha = git_blob_sha(blob)
            blob_path = vault / blob_sha[:2] / blob_sha[2:]
            blob_path.parent.mkdir()
            blob_path.write_bytes(blob)
            report = {
                "record_type": "commit_pinned_source_capture",
                "run_id": MODULE.DISCOVERY_RUN_ID,
                "candidate_code_executed": False,
                "candidate_index": 4,
                "repository": "example/flashloan",
                "commit_sha": "a" * 40,
                "tree_sha": "b" * 40,
                "captured_files": [{
                    "path": "FlashLoan.sol",
                    "blob_sha": blob_sha,
                    "vault_relative_path": blob_sha[:2] + "/" + blob_sha[2:],
                }],
            }
            (report_dir / "00004-example__flashloan.json").write_text(json.dumps(report))
            loaded = MODULE.load_reports(report_dir, vault, 12)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["repository"], "example/flashloan")

    def test_load_reports_rejects_tampered_blob(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_dir = root / "reports"
            vault = root / "vault"
            report_dir.mkdir()
            vault.mkdir()
            blob = b"contract FlashLoan {}\n"
            blob_sha = git_blob_sha(blob)
            blob_path = vault / blob_sha[:2] / blob_sha[2:]
            blob_path.parent.mkdir()
            blob_path.write_bytes(b"tampered")
            report = {
                "record_type": "commit_pinned_source_capture",
                "run_id": MODULE.DISCOVERY_RUN_ID,
                "candidate_code_executed": False,
                "candidate_index": 4,
                "repository": "example/flashloan",
                "commit_sha": "a" * 40,
                "tree_sha": "b" * 40,
                "captured_files": [{
                    "path": "FlashLoan.sol",
                    "blob_sha": blob_sha,
                    "vault_relative_path": blob_sha[:2] + "/" + blob_sha[2:],
                }],
            }
            (report_dir / "00004-example__flashloan.json").write_text(json.dumps(report))
            with self.assertRaises(SystemExit):
                MODULE.load_reports(report_dir, vault, 12)


if __name__ == "__main__":
    unittest.main()
