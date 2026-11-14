from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from flashloan_research.mission_executor import MissionExecutor
from flashloan_research.mission_queue import MissionQueue
from flashloan_research.mission_runtime import MissionTaskStore


class FakeGitHubClient:
    def get(self, path, params=None):
        if path != "/search/repositories":
            raise AssertionError(f"unexpected API path: {path}")
        return {
            "total_count": 1,
            "incomplete_results": False,
            "items": [{
                "id": 4242,
                "full_name": "research-lab/flashloan-liquidator",
                "html_url": "https://github.com/research-lab/flashloan-liquidator",
                "description": "Flash loan powered DeFi liquidation research bot",
                "default_branch": "main",
                "pushed_at": "2026-11-01T00:00:00Z",
                "archived": False,
                "fork": False,
                "stargazers_count": 25,
                "forks_count": 4,
            }],
        }


class FakeInspectionPipeline:
    def inspect(self, repository, store):
        return {
            "repository": repository,
            "commit_sha": "a" * 40,
            "tree_sha": "b" * 40,
            "tree_truncated": False,
            "source_capture_complete_within_configured_scope": True,
            "source_files_captured": 1,
            "captured_files": [{
                "path": "src/Liquidator.sol",
                "blob_sha": "c" * 40,
                "size": 128,
            }],
            "signals": [{
                "signal": "executeOperation",
                "path": "src/Liquidator.sol",
                "line": 42,
                "excerpt": "function executeOperation(...) external returns (bool)",
            }],
            "limitations": [],
        }


def mission_payload():
    return {
        "mission_id": "flashloan-executor-test",
        "title": "Flash loan liquidation repository research",
        "objective": (
            "Discover and deeply audit public GitHub repositories implementing "
            "flash loans, flash-loan-powered liquidation and related DeFi systems."
        ),
        "domain": "defi_liquidation",
        "scope": {
            "chains": ["Ethereum"],
            "protocols": ["Aave V3"],
            "repository_limit": 10,
            "include_archived": False,
            "include_older_references": True,
            "keyword_taxonomy_version": "test-1",
            "discovery_query_families": ["flash_loan_core"],
            "search_per_page": 100,
            "max_pages_per_query": 2,
            "include_forked": True,
        },
        "research_depth": "deep_forensic",
        "agent_policy": {
            "mode": "autonomous",
            "independent_review": True,
            "max_parallel_agents": 2,
            "max_iterations": 3,
            "specialists": [
                "research_director", "github_discovery", "solidity_security",
                "independent_reviewer",
            ],
        },
        "safety_policy": {
            "research_only": True,
            "execute_candidate_code": False,
            "wallet_access": False,
            "sign_transactions": False,
            "deploy_contracts": False,
            "live_trading": False,
            "paid_services": False,
            "allow_free_model_inference": True,
        },
        "deliverables": ["candidate_matrix", "source_audits", "evidence_register"],
        "acceptance_criteria": ["All substantive claims require commit-pinned source evidence."],
    }


class MissionExecutorTests(unittest.TestCase):
    def test_form_mission_runs_discovery_and_source_capture_then_blocks_ai_review_honestly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "research.sqlite3"
            taxonomy = root / "taxonomy.json"
            taxonomy.write_text(json.dumps({
                "taxonomy_version": "test-1",
                "families": [{"id": "flash_loan_core", "label": "Flash loan core"}],
                "family_queries": {"flash_loan_core": ["flash loan"]},
            }), encoding="utf-8")
            queue = MissionQueue(db)
            queue.enqueue(mission_payload())
            queue.close()

            executor = MissionExecutor(
                database_path=db,
                taxonomy_path=taxonomy,
                artifact_root=root / "artifacts",
                client_factory=FakeGitHubClient,
                pipeline_factory=FakeInspectionPipeline,
            )
            result = executor.run_mission("flashloan-executor-test")

            self.assertEqual(result["discovery"]["family_tasks_completed_this_run"], 1)
            self.assertEqual(result["candidate_expansion"]["unique_candidate_count"], 1)
            self.assertEqual(result["source_inspection"]["source_inspections_completed"], 1)
            self.assertEqual(result["final"]["mission_status"], "blocked")
            self.assertEqual(
                result["final"]["model_runtime_status"],
                "blocked_no_approved_free_local_model_endpoint",
            )
            self.assertFalse(result["final"]["candidate_code_executed"])
            tasks = MissionTaskStore(db)
            try:
                rows = tasks.list_tasks("flashloan-executor-test")
                inspection = next(x for x in rows if x["task_type"] == "candidate_source_capture")
                purpose = next(x for x in rows if x["task_type"] == "candidate_purpose")
                security = next(x for x in rows if x["task_type"] == "security_forensics")
                review = next(x for x in rows if x["task_type"] == "independent_review")
                self.assertEqual(inspection["status"], "completed")
                self.assertEqual(purpose["status"], "pending")
                self.assertEqual(security["status"], "pending")
                self.assertEqual(review["status"], "pending")
            finally:
                tasks.close()


if __name__ == "__main__":
    unittest.main()
