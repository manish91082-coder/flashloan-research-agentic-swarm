from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from flashloan_research.discovery_import import DiscoveryImportError, import_discovery_report
from flashloan_research.storage import ResearchStore


def candidate(name: str, repo_id: int, family: str) -> dict:
    return {
        "repository": name,
        "repository_id": repo_id,
        "metadata": {
            "full_name": name,
            "html_url": f"https://github.com/{name}",
            "description": "flash-loan liquidation research candidate",
            "default_branch": "main",
            "pushed_at": "2026-11-14T00:00:00Z",
            "archived": False,
            "stars": 10,
            "forks": 2,
            "discovery_query": f"{family} | flash loan liquidation",
        },
        "discovered_by": [{"family_id": family, "query": "flash loan liquidation", "page": 1}],
        "matched_families": [family],
    }


class DiscoveryImportTests(unittest.TestCase):
    def test_import_pauses_and_resumes_without_duplicate_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "discovery.json"
            report = {
                "schema_version": "1.0",
                "taxonomy_version": "1.0.0",
                "unique_candidate_count": 3,
                "candidates": [
                    candidate("org/one", 1, "flash_loan_core"),
                    candidate("org/two", 2, "defi_liquidation"),
                    candidate("org/three", 3, "arbitrage"),
                ],
            }
            report["candidates"][0]["metadata"]["description"] = 'quoted "text" and path C:\\research\\repo'
            report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
            store = ResearchStore(root / "research.sqlite3")
            try:
                first = import_discovery_report(report_path, "run-001", store, batch_size=2, max_batches=1)
                self.assertEqual(first["status"], "paused")
                self.assertEqual(first["imported_candidates"], 2)
                second = import_discovery_report(report_path, "run-001", store, batch_size=2)
                self.assertEqual(second["status"], "completed")
                self.assertEqual(second["imported_candidates"], 3)
                self.assertEqual(store.counts()["candidates"], 3)
                stored_description = store.connection.execute(
                    "SELECT description FROM candidates WHERE full_name='org/one'"
                ).fetchone()[0]
                self.assertEqual(stored_description, 'quoted "text" and path C:\\research\\repo')
                provenance = store.connection.execute(
                    "SELECT COUNT(*) FROM discovery_candidate_provenance WHERE run_id='run-001'"
                ).fetchone()[0]
                self.assertEqual(provenance, 3)
                third = import_discovery_report(report_path, "run-001", store, batch_size=2)
                self.assertEqual(third["status"], "completed")
                self.assertEqual(store.counts()["candidates"], 3)
            finally:
                store.close()

    def test_import_rejects_reusing_run_id_for_different_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "discovery.json"
            store = ResearchStore(root / "research.sqlite3")
            try:
                report = {"taxonomy_version":"1.0.0","unique_candidate_count":1,
                          "candidates":[candidate("org/one",1,"flash_loan_core")] }
                path.write_text(json.dumps(report,indent=2),encoding="utf-8")
                import_discovery_report(path,"run-002",store,batch_size=1)
                report["candidates"][0]["metadata"]["description"]="changed source report"
                path.write_text(json.dumps(report,indent=2),encoding="utf-8")
                with self.assertRaises(DiscoveryImportError):
                    import_discovery_report(path,"run-002",store,batch_size=1)
            finally:
                store.close()

    def test_import_rejects_invalid_candidate_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path=root/"discovery.json"
            row=candidate("org/one",1,"flash_loan_core")
            row["metadata"]["full_name"]="org/other"
            path.write_text(json.dumps({"taxonomy_version":"1.0.0","unique_candidate_count":1,"candidates":[row]},indent=2,sort_keys=True),encoding="utf-8")
            store=ResearchStore(root/"research.sqlite3")
            try:
                with self.assertRaises(DiscoveryImportError):
                    import_discovery_report(path,"run-003",store,batch_size=1)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()