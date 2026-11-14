from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from flashloan_research.mission_discovery import run_taxonomy_discovery
from flashloan_research.storage import ResearchStore


def repository(repo_id: int, full_name: str) -> dict:
    return {
        "id": repo_id,
        "full_name": full_name,
        "html_url": f"https://github.com/{full_name}",
        "description": "public DeFi research candidate",
        "default_branch": "main",
        "pushed_at": "2026-11-01T00:00:00Z",
        "archived": False,
        "fork": False,
        "stargazers_count": 10,
        "forks_count": 2,
    }


class FakeClient:
    def __init__(self, responses=None, fail_queries=None):
        self.responses = responses or {}
        self.fail_queries = set(fail_queries or [])
        self.calls = []

    def get(self, path, params):
        self.calls.append((path, dict(params)))
        query, page = params["q"], int(params["page"])
        if query in self.fail_queries:
            raise RuntimeError("simulated rate limit")
        return self.responses[(query, page)]


class MissionDiscoveryTests(unittest.TestCase):
    def write_taxonomy(self, root: Path) -> Path:
        path = root / "taxonomy.json"
        path.write_text(json.dumps({
            "taxonomy_version": "test-1",
            "families": [
                {"id": "flash_loan_core", "label": "Flash loan core"},
                {"id": "defi_liquidation", "label": "DeFi liquidation"}
            ],
            "family_queries": {
                "flash_loan_core": ["q-flash", "q-provider"],
                "defi_liquidation": ["q-liquidation"]
            }
        }), encoding="utf-8")
        return path

    def test_paginates_deduplicates_and_preserves_query_provenance(self):
        responses = {
            ("q-flash", 1): {"total_count": 3, "incomplete_results": False,
                             "items": [repository(1, "org/one"), repository(2, "org/two")]},
            ("q-flash", 2): {"total_count": 3, "incomplete_results": False,
                             "items": [repository(2, "org/two")]},
            ("q-provider", 1): {"total_count": 2, "incomplete_results": False,
                                "items": [repository(1, "org/one"), repository(3, "org/three")]},
            ("q-provider", 2): {"total_count": 2, "incomplete_results": False, "items": []},
            ("q-liquidation", 1): {"total_count": 1, "incomplete_results": False,
                                   "items": [repository(4, "org/four")]},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ResearchStore(root / "research.sqlite3")
            try:
                report = run_taxonomy_discovery(
                    FakeClient(responses), store, self.write_taxonomy(root),
                    selected_families=["flash_loan_core"], per_page=2, max_pages=3
                )
                self.assertEqual(report["unique_candidate_count"], 3)
                self.assertTrue(report["coverage_complete"])
                one = next(x for x in report["candidates"] if x["repository"] == "org/one")
                self.assertEqual(len(one["discovered_by"]), 2)
                self.assertEqual(store.counts()["candidates"], 3)
                self.assertEqual(report["query_count"], 2)
                self.assertEqual(report["complete_query_count"], 2)
            finally:
                store.close()

    def test_search_result_cap_is_reported_as_coverage_debt(self):
        item = repository(1, "org/one")
        responses = {("q-flash", page): {
            "total_count": 1200, "incomplete_results": False, "items": [item] * 2
        } for page in range(1, 11)}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ResearchStore(root / "research.sqlite3")
            try:
                report = run_taxonomy_discovery(
                    FakeClient(responses), store, self.write_taxonomy(root),
                    selected_families=["flash_loan_core"], per_page=2, max_pages=10
                )
                self.assertFalse(report["coverage_complete"])
                self.assertEqual(report["coverage_debt"][0]["status"], "capped")
                self.assertTrue(report["coverage_debt"][0]["search_cap_hit"])
            finally:
                store.close()

    def test_api_failure_is_persisted_as_incomplete_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ResearchStore(root / "research.sqlite3")
            try:
                report = run_taxonomy_discovery(
                    FakeClient(fail_queries=["q-flash"]), store, self.write_taxonomy(root),
                    selected_families=["flash_loan_core"], per_page=2, max_pages=2
                )
                self.assertFalse(report["coverage_complete"])
                self.assertEqual(report["incomplete_query_count"], 1)
                self.assertIn("simulated rate limit", report["coverage_debt"][0]["error"])
            finally:
                store.close()

    def test_rejects_unknown_selected_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ResearchStore(root / "research.sqlite3")
            try:
                with self.assertRaises(ValueError):
                    run_taxonomy_discovery(FakeClient(), store, self.write_taxonomy(root),
                                           selected_families=["not-a-family"])
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
