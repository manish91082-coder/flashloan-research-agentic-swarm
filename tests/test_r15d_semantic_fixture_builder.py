import hashlib
import unittest
import tempfile
from pathlib import Path

from scripts.build_r15d_semantic_fixtures import (
    EXPECTED, build, extract_excerpt, git_blob_sha, require_complete_function, verify_source,
)


class SemanticFixtureBuilderTests(unittest.TestCase):
    def test_pinned_fixture_sources_match_git_blob(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        paths = {
            "0xnavarro/Aave-Liquiditor": root / "tests/fixtures/r15d_semantic_sources/nav_flash_liquidator.sol",
            "cobibean/aave-liquidator-bot": root / "tests/fixtures/r15d_semantic_sources/cob_aave_liquidator_swap_router02.sol",
        }
        for repo, path in paths.items():
            commit, tree, source_path, blob = EXPECTED[repo]
            verify_source(repo=repo, data=path.read_bytes(), identity={
                "commit_sha": commit, "tree_sha": tree, "path": source_path, "git_blob_sha1": blob,
            })

    def test_tampered_source_rejected(self):
        repo = "0xnavarro/Aave-Liquiditor"
        commit, tree, path, blob = EXPECTED[repo]
        with self.assertRaisesRegex(ValueError, "Git blob"):
            verify_source(repo, b"tampered", {
                "commit_sha": commit, "tree_sha": tree, "path": path, "git_blob_sha1": blob,
            })

    def test_wrong_commit_tree_and_path_rejected(self):
        repo = "cobibean/aave-liquidator-bot"
        commit, tree, path, blob = EXPECTED[repo]
        for identity in (
            {"commit_sha": "0" * 40, "tree_sha": tree, "path": path, "git_blob_sha1": blob},
            {"commit_sha": commit, "tree_sha": "0" * 40, "path": path, "git_blob_sha1": blob},
            {"commit_sha": commit, "tree_sha": tree, "path": "wrong.sol", "git_blob_sha1": blob},
        ):
            with self.assertRaises(ValueError):
                verify_source(repo, b"x", identity)

    def test_shifted_or_out_of_bounds_line_range_rejected(self):
        for start, end in ((0, 1), (2, 1), (1, 3)):
            with self.assertRaises(ValueError):
                extract_excerpt(["a\n", "b\n"], start, end)

    def test_complete_function_required_for_absence(self):
        require_complete_function("function executeOperation() external { return true; }", "function executeOperation(")
        for bad in (
            "function executeOperation() external { return true;",
            "function unrelated() external { return true; }",
            "prefix function executeOperation() external { return true; }",
        ):
            with self.assertRaises(ValueError):
                require_complete_function(bad, "function executeOperation(")

    def test_full_build_emits_six_hashed_source_pinned_cases(self):
        with tempfile.TemporaryDirectory() as temp:
            result = build(output_dir=Path(temp))
            self.assertEqual(result["status"], "retired_forensic_fixture_not_for_blind_adjudication")
            self.assertEqual(len(result["cases"]), 6)
            self.assertTrue(all(len(case["excerpt_sha256"]) == 64 for case in result["cases"]))
            self.assertTrue(all("expected_label" not in case for case in result["cases"]))
            self.assertEqual(result["cases"][1]["id"], "NAV-02")

    def test_default_repository_output_is_refused_for_retired_v1(self):
        with self.assertRaisesRegex(ValueError, "explicit isolated forensic output directory"):
            build()

    def test_public_repository_output_path_is_refused(self):
        repository_root = Path(__file__).resolve().parents[1]
        with self.assertRaisesRegex(ValueError, "outside the public repository"):
            build(output_dir=repository_root / "research_runs" / "forensic-r15d-v1")

    def test_git_blob_hash_is_git_object_hash(self):
        self.assertEqual(git_blob_sha(b"abc"), hashlib.sha1(b"blob 3\0abc").hexdigest())


if __name__ == "__main__":
    unittest.main()
