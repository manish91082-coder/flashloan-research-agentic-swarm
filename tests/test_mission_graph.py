from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from flashloan_research.mission_graph import build_mission_graph


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def prepare(self, mission_id):
        self.calls.append(("prepare", mission_id))
        return {"plan_task_count": 4}

    def discover(self, mission_id):
        self.calls.append(("discover", mission_id))
        return {"family_tasks_total": 11, "ready_for_merge": True}

    def merge_and_expand(self, mission_id):
        self.calls.append(("expand", mission_id))
        return {"unique_candidate_count": 38, "first_audit_batch_count": 38}

    def inspect_candidate_batch(self, mission_id):
        self.calls.append(("inspect", mission_id))
        return {"source_inspections_completed": 38}

    def finalize(self, mission_id):
        self.calls.append(("finalize", mission_id))
        return {"mission_status": "blocked", "pending_roles": ["independent_reviewer"]}


class MissionGraphTests(unittest.TestCase):
    def test_graph_runs_ordered_mission_stages_and_persists_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = FakeExecutor()
            checkpoint_path = Path(tmp) / "checkpoints.sqlite"
            with SqliteSaver.from_conn_string(str(checkpoint_path)) as checkpointer:
                graph = build_mission_graph(executor, checkpointer)
                config = {"configurable": {"thread_id": "mission-graph-test"}}
                result = graph.invoke({"mission_id": "mission-graph-test"}, config=config)
                snapshot = graph.get_state(config)
            self.assertEqual(
                [x[0] for x in executor.calls],
                ["prepare", "discover", "expand", "inspect", "finalize"],
            )
            self.assertEqual(result["final"]["mission_status"], "blocked")
            self.assertEqual(snapshot.values["final"]["pending_roles"], ["independent_reviewer"])
            self.assertTrue(checkpoint_path.exists())


if __name__ == "__main__":
    unittest.main()
