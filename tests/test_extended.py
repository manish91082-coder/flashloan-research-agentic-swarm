from __future__ import annotations

import base64
import hashlib
import tempfile
import unittest
from pathlib import Path

from flashloan_research.analyzer import decode_blob, extract_signals, is_source_file
from flashloan_research.github_api import GitHubClient
from flashloan_research.models import EvidenceRecord, RepositoryCandidate
from flashloan_research.storage import ContentAddressedVault, ResearchStore, git_blob_sha


class ExtendedRegressionTests(unittest.TestCase):
    def test_git_blob_sha_uses_git_object_header(self):
        data = b"contract Test {}"
        expected = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        self.assertEqual(git_blob_sha(data), expected)

    def test_decode_blob_accepts_base64_content(self):
        payload = b"flash loan callback"
        self.assertEqual(
            decode_blob({"encoding": "base64", "content": base64.b64encode(payload).decode()}),
            payload,
        )

    def test_decode_blob_rejects_non_base64_transport(self):
        with self.assertRaises(ValueError):
            decode_blob({"encoding": "utf-8", "content": "not-base64"})

    def test_decode_blob_rejects_corrupt_base64(self):
        with self.assertRaises(ValueError):
            decode_blob({"encoding": "base64", "content": "%%invalid%%"})

    def test_source_filter_excludes_vendor_and_docs(self):
        self.assertTrue(is_source_file("contracts/Executor.sol"))
        self.assertFalse(is_source_file("vendor/Executor.sol"))
        self.assertFalse(is_source_file("README.md"))

    def test_signal_extraction_is_line_aware(self):
        source = b"contract X {\n function executeOperation() external {}\n}"
        signals = extract_signals("Executor.sol", source)
        found = [x for x in signals if x["signal"] == "aave_execute_operation"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["line"], 2)

    def test_generic_flashloan_call_not_promoted_to_aave_specific_signal(self):
        source = b"vault.flashLoan(receiver, tokens, amounts, data);"
        names = {x["signal"] for x in extract_signals("Generic.sol", source)}
        self.assertIn("generic_flash_loan_call", names)
        self.assertNotIn("aave_flash_loan_simple", names)

    def test_candidate_identity_is_mandatory(self):
        with self.assertRaises(ValueError):
            RepositoryCandidate.from_api({"full_name": "owner/name"}, "flash loan")

    def test_evidence_rejects_short_commit_sha(self):
        item = EvidenceRecord(
            "owner/repo", "abc", "src/Executor.sol", "b" * 40,
            "observed_fact", "callback is present", "executeOperation"
        )
        with self.assertRaises(ValueError):
            item.validate()

    def test_evidence_rejects_unsupported_confidence(self):
        item = EvidenceRecord(
            "owner/repo", "a" * 40, "src/Executor.sol", "b" * 40,
            "observed_fact", "callback is present", "executeOperation",
            confidence="certain"
        )
        with self.assertRaises(ValueError):
            item.validate()

    def test_evidence_rejects_uncontrolled_acceptance_status(self):
        item = EvidenceRecord(
            "owner/repo", "a" * 40, "src/Executor.sol", "b" * 40,
            "observed_fact", "callback is present", "executeOperation",
            acceptance_status="auto_approved"
        )
        with self.assertRaises(ValueError):
            item.validate()

    def test_github_client_rejects_external_absolute_path(self):
        client = GitHubClient()
        with self.assertRaises(ValueError):
            client.get("//evil.example/path")

    def test_github_search_validates_query_and_page_bounds(self):
        client = GitHubClient()
        with self.assertRaises(ValueError):
            client.search_repositories(" ")
        with self.assertRaises(ValueError):
            client.search_repositories("flash loan", per_page=101)

    def test_sqlite_candidate_upsert_and_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(Path(tmp) / "research.sqlite3")
            candidate = RepositoryCandidate(
                "owner/repo", "https://github.com/owner/repo", None, "main",
                None, False, 0, 0, "flash loan"
            )
            store.upsert_candidate(candidate)
            store.upsert_candidate(candidate)
            self.assertEqual(store.counts()["candidates"], 1)
            store.close()

    def test_content_addressed_vault_is_idempotent_and_verifies_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = b"immutable evidence"
            sha = git_blob_sha(payload)
            vault = ContentAddressedVault(Path(tmp))
            first = vault.put(sha, payload)
            second = vault.put(sha, payload)
            self.assertEqual(first, second)
            self.assertEqual(first.read_bytes(), payload)
            with self.assertRaises(ValueError):
                vault.put("0" * 40, payload)


if __name__ == "__main__":
    unittest.main()
