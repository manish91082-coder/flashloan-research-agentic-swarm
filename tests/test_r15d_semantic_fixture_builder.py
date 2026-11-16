import hashlib
import unittest

from scripts.build_r15d_semantic_fixtures import (
    EXPECTED, extract_excerpt, git_blob_sha, require_complete_function, verify_source,
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

    def test_git_blob_hash_is_git_object_hash(self):
        self.assertEqual(git_blob_sha(b"abc"), hashlib.sha1(b"blob 3\0abc").hexdigest())


if __name__ == "__main__":
    unittest.main()
