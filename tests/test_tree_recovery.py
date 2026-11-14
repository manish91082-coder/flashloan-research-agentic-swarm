from __future__ import annotations

import unittest

from flashloan_research.analyzer import collect_repository_tree
from flashloan_research.config import Settings


ROOT = "a" * 40
SRC = "b" * 40


class FakeTreeClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def tree(self, full_name, tree_sha, recursive=True):
        self.calls.append((full_name, tree_sha, recursive))
        return self.pages[(tree_sha, recursive)]


class TreeRecoveryTests(unittest.TestCase):
    def test_truncated_recursive_tree_is_recovered_by_directory_walk(self):
        client = FakeTreeClient({
            (ROOT, True): {"truncated": True, "tree": [{"path": "partial.sol", "type": "blob", "sha": "c" * 40}]},
            (ROOT, False): {"truncated": False, "tree": [
                {"path": "src", "type": "tree", "sha": SRC},
                {"path": "README.md", "type": "blob", "sha": "d" * 40},
            ]},
            (SRC, False): {"truncated": False, "tree": [
                {"path": "Executor.sol", "type": "blob", "sha": "e" * 40},
            ]},
        })
        items, status = collect_repository_tree(client, "owner/repo", ROOT, Settings())
        paths = {item["path"] for item in items}
        self.assertEqual(paths, {"README.md", "src/Executor.sol"})
        self.assertTrue(status["recursive_tree_truncated"])
        self.assertTrue(status["tree_recovery_attempted"])
        self.assertTrue(status["tree_recovery_complete"])
        self.assertEqual(status["tree_directories_visited"], 2)

    def test_directory_limit_keeps_coverage_incomplete(self):
        client = FakeTreeClient({
            (ROOT, True): {"truncated": True, "tree": []},
            (ROOT, False): {"truncated": False, "tree": [
                {"path": "src", "type": "tree", "sha": SRC},
                {"path": "README.md", "type": "blob", "sha": "d" * 40},
            ]},
        })
        items, status = collect_repository_tree(
            client, "owner/repo", ROOT, Settings(max_tree_directories=1)
        )
        self.assertEqual([item["path"] for item in items], ["README.md"])
        self.assertFalse(status["tree_recovery_complete"])
        self.assertEqual(status["tree_directories_visited"], 1)

    def test_truncated_subtree_is_not_reported_complete(self):
        client = FakeTreeClient({
            (ROOT, True): {"truncated": True, "tree": []},
            (ROOT, False): {"truncated": False, "tree": [
                {"path": "src", "type": "tree", "sha": SRC},
            ]},
            (SRC, False): {"truncated": True, "tree": [
                {"path": "Executor.sol", "type": "blob", "sha": "e" * 40},
            ]},
        })
        items, status = collect_repository_tree(client, "owner/repo", ROOT, Settings())
        self.assertEqual([item["path"] for item in items], ["src/Executor.sol"])
        self.assertFalse(status["tree_recovery_complete"])


if __name__ == "__main__":
    unittest.main()
