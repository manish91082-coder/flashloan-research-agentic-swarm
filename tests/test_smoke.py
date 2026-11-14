from __future__ import annotations

import hashlib
import unittest

from flashloan_research.analyzer import extract_signals, is_source_file
from flashloan_research.models import EvidenceRecord
from flashloan_research.storage import git_blob_sha


class SmokeTests(unittest.TestCase):
    def test_git_blob_hash_uses_git_object_framing(self):
        payload = b"flash-loan"
        framed = b"blob " + str(len(payload)).encode() + b"\0" + payload
        self.assertEqual(git_blob_sha(payload), hashlib.sha1(framed).hexdigest())

    def test_source_filter_excludes_vendor_and_docs(self):
        self.assertTrue(is_source_file("contracts/Executor.sol"))
        self.assertFalse(is_source_file("vendor/Executor.sol"))
        self.assertFalse(is_source_file("README.md"))

    def test_callback_signal_is_line_aware(self):
        source = b"contract X {\n function executeOperation() external {}\n}"
        matches = extract_signals("Executor.sol", source)
        callback = [item for item in matches if item["signal"] == "aave_execute_operation"]
        self.assertEqual(len(callback), 1)
        self.assertEqual(callback[0]["line"], 2)

    def test_evidence_rejects_short_commit_sha(self):
        record = EvidenceRecord(
            "owner/repo", "abc", "src/A.sol", "b" * 40,
            "observed_fact", "claim", "excerpt"
        )
        with self.assertRaises(ValueError):
            record.validate()


if __name__ == "__main__":
    unittest.main()
