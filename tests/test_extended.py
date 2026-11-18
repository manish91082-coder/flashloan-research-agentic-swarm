from __future__ import annotations

import base64
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from dataclasses import replace
from email.message import Message
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

from flashloan_research.analyzer import decode_blob, extract_signals, is_source_file, is_research_artifact, select_research_artifacts
from flashloan_research.config import SETTINGS
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

    def test_research_artifact_filter_includes_manifests_tests_ci_and_license(self):
        self.assertTrue(is_research_artifact("contracts/Liquidator.sol"))
        self.assertTrue(is_research_artifact("package-lock.json"))
        self.assertTrue(is_research_artifact("tests/test_liquidation.py"))
        self.assertTrue(is_research_artifact(".github/workflows/ci.yml"))
        self.assertTrue(is_research_artifact("LICENSE"))
        self.assertFalse(is_research_artifact("monitor/test/dashboard.test.js"))
        self.assertFalse(is_research_artifact("node_modules/pkg/index.js"))

    def test_capture_selector_round_robins_research_families_before_cap(self):
        items = ([{"path": f"contracts/Liquidator{i:02d}.sol", "sha": str(i)} for i in range(20)]
                 + [{"path": "bot.js", "sha": "runtime"},
                    {"path": "tests/test_liquidation.py", "sha": "test"},
                    {"path": "package.json", "sha": "deps"},
                    {"path": "hardhat.config.ts", "sha": "build"},
                    {"path": "LICENSE", "sha": "license"},
                    {"path": ".github/workflows/ci.yml", "sha": "ci"},
                    {"path": "monitor/test/apiLogs.test.js", "sha": "monitor"}])
        selected = select_research_artifacts(items, 6)
        paths = [item["path"] for item in selected]
        self.assertEqual(paths, ["contracts/Liquidator00.sol", "bot.js", "tests/test_liquidation.py",
                                 "package.json", "hardhat.config.ts", "LICENSE"])
        self.assertNotIn("monitor/test/apiLogs.test.js", paths)


    def test_dependency_lockfiles_receive_a_separate_bounded_size_cap(self):
        from flashloan_research.config import SETTINGS
        self.assertGreater(max_research_artifact_bytes("package-lock.json"), SETTINGS.max_blob_bytes)
        self.assertEqual(max_research_artifact_bytes("contracts/Liquidator.sol"), SETTINGS.max_blob_bytes)

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


    def test_github_client_waits_until_primary_rate_limit_reset(self):
        calls = 0
        sleeps = []

        def opener(request, timeout):
            nonlocal calls
            calls += 1
            if calls == 1:
                headers = Message()
                headers["X-RateLimit-Remaining"] = "0"
                headers["X-RateLimit-Reset"] = "2000"
                raise HTTPError(
                    request.full_url, 403, "API rate limit exceeded",
                    headers, BytesIO(b"rate limited")
                )
            return BytesIO(b'{"ok": true}')

        settings = replace(SETTINGS, max_retries=1)
        client = GitHubClient(
            settings=settings, opener=opener, sleep=sleeps.append,
            clock=lambda: 1000.0,
        )
        output = io.StringIO()
        with redirect_stderr(output):
            self.assertEqual(client.get("/rate-limit"), {"ok": True})
        self.assertEqual(calls, 2)
        self.assertEqual(sleeps, [1001])
        telemetry = json.loads(output.getvalue().strip())
        self.assertEqual(telemetry["event"], "github_api_retry")
        self.assertTrue(telemetry["rate_limited"])
        self.assertEqual(telemetry["sleep_seconds"], 1001)

    def test_github_client_respects_retry_after_above_sixty_seconds(self):
        calls = 0
        sleeps = []

        def opener(request, timeout):
            nonlocal calls
            calls += 1
            if calls == 1:
                headers = Message()
                headers["Retry-After"] = "120"
                raise HTTPError(
                    request.full_url, 429, "secondary rate limit",
                    headers, BytesIO(b"try later")
                )
            return BytesIO(b'{"ok": true}')

        settings = replace(SETTINGS, max_retries=1)
        client = GitHubClient(settings=settings, opener=opener, sleep=sleeps.append)
        self.assertEqual(client.get("/secondary-limit"), {"ok": True})
        self.assertEqual(calls, 2)
        self.assertEqual(sleeps, [120])

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
