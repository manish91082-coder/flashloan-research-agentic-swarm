from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from flashloan_research.mission_runtime import (
    MissionPlanError,
    MissionTaskStore,
    build_candidate_tasks,
    build_mission_plan,
    stable_task_id,
    validate_acyclic,
)


def mission():
    return {
        "mission_id": "flashloan-test-01",
        "title": "Flash loan and liquidation repository research",
        "objective": "Discover and audit public flash-loan liquidation repositories.",
        "scope": {
            "discovery_query_families": ["flash_loan_core", "defi_liquidation"],
            "search_per_page": 100,
            "max_pages_per_query": 10,
            "include_archived": False,
            "include_forked": True,
        },
        "deliverables": ["candidate_matrix", "source_audits"],
        "agent_policy": {"max_parallel_agents": 4},
    }


def taxonomy():
    return {
        "taxonomy_version": "test-1",
        "family_queries": {
            "flash_loan_core": ["flash loan", "flashloan"],
            "defi_liquidation": ["liquidator", "liquidation bot"],
        },
    }


class MissionRuntimeTests(unittest.TestCase):
    def test_plan_builds_dependency_aware_family_dag(self):
        tasks = build_mission_plan(mission(), taxonomy())
        self.assertEqual(len(tasks), 8)
        by_type = {task.task_type: task for task in tasks}
        self.assertEqual(by_type["discover_family"].depends_on[0],
                         by_type["mission_plan"].task_id)
        merge = by_type["merge_candidates"]
        self.assertEqual(len(merge.depends_on), 2)
        self.assertEqual(by_type["mission_synthesis"].depends_on,
                         (by_type["expand_candidate_tasks"].task_id,))
        self.assertEqual(stable_task_id("m", "t", "k"), stable_task_id("m", "t", "k"))

    def test_cycle_detection_rejects_invalid_dag(self):
        tasks = build_mission_plan(mission(), taxonomy())
        cycle = list(tasks)
        first = cycle[0]
        cycle[0] = type(first)(
            mission_id=first.mission_id, task_id=first.task_id,
            task_type=first.task_type, role=first.role,
            depends_on=(cycle[-1].task_id,), payload=first.payload,
        )
        with self.assertRaises(MissionPlanError):
            validate_acyclic(cycle)

    def test_plan_persistence_is_idempotent_and_tasks_release_by_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MissionTaskStore(Path(tmp) / "missions.sqlite3")
            try:
                tasks = build_mission_plan(mission(), taxonomy())
                self.assertEqual(store.create_plan(tasks), {"inserted": 8, "existing": 0})
                self.assertEqual(store.create_plan(tasks), {"inserted": 0, "existing": 8})
                first = store.claim_ready("flashloan-test-01", "worker-a", limit=5)
                self.assertEqual(len(first), 1)
                self.assertEqual(first[0]["task_type"], "mission_plan")
                self.assertEqual(first[0]["attempts"], 1)
                store.complete_task("flashloan-test-01", first[0]["task_id"], "worker-a", {"ok": True})
                second = store.claim_ready("flashloan-test-01", "worker-a", limit=5)
                self.assertEqual(len(second), 2)
                self.assertTrue(all(x["task_type"] == "discover_family" for x in second))
            finally:
                store.close()

    def test_lease_owner_is_enforced_and_failure_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MissionTaskStore(Path(tmp) / "missions.sqlite3")
            try:
                tasks = build_mission_plan(mission(), taxonomy())
                store.create_plan(tasks)
                task = store.claim_ready("flashloan-test-01", "worker-a", limit=1)[0]
                with self.assertRaises(MissionPlanError):
                    store.complete_task("flashloan-test-01", task["task_id"], "worker-b", {})
                self.assertEqual(store.fail_task("flashloan-test-01", task["task_id"], "worker-a",
                                                 "temporary network error"), "pending")
                retried = store.claim_ready("flashloan-test-01", "worker-a", limit=1)[0]
                self.assertEqual(retried["attempts"], 2)
            finally:
                store.close()

    def test_candidate_expansion_adds_independent_specialist_and_review_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MissionTaskStore(Path(tmp) / "missions.sqlite3")
            try:
                base = build_mission_plan(mission(), taxonomy())
                store.create_plan(base)
                expansion = next(x for x in base if x.task_type == "expand_candidate_tasks")
                result = store.expand_candidates(
                    "flashloan-test-01", expansion.task_id,
                    ["org/repo-one", "org/repo-two"],
                    selected_roles=["solidity_security", "economics_quant"],
                )
                self.assertEqual(result["candidate_count"], 2)
                self.assertEqual(result["synthesis_dependencies"], 2)
                rows = store.list_tasks("flashloan-test-01")
                dossiers = [x for x in rows if x["task_type"] == "candidate_dossier"]
                self.assertEqual(len(dossiers), 2)
                reviewers = [x for x in rows if x["task_type"] == "independent_review"]
                self.assertEqual(len(reviewers), 2)
                synthesis = next(x for x in rows if x["task_type"] == "mission_synthesis")
                self.assertEqual(len(synthesis["depends_on"]), 3)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
