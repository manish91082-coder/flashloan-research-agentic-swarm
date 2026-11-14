from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from flashloan_research.mission_executor import MissionExecutor
from flashloan_research.mission_runtime import MissionTask, MissionTaskStore, stable_task_id
from flashloan_research.mission_queue import MissionQueue
from flashloan_research.storage import git_blob_sha


class FakeLocalProvider:
    calls = []
    reviewer_prior_count = None
    identity = SimpleNamespace(
        provider="fake_loopback_test_provider",
        model="deterministic-fixture-model",
        base_url="http://127.0.0.1:11434",
        prompt_template_version="test-1",
    )

    def __init__(self):
        pass

    def generate_json(self, system_prompt, user_payload, required_keys):
        self.calls.append({"system_prompt": system_prompt, "payload": user_payload})
        self.assert_context(user_payload, system_prompt)
        signal = user_payload["source_signals"][0]
        if "Independently challenge" in system_prompt:
            self.__class__.reviewer_prior_count = len(user_payload["prior_specialist_outputs"])
        return {
            "summary": "Fixture analysis; all claims remain provisional.",
            "purpose": "flash-loan liquidation research implementation",
            "implementation_status": "partial",
            "findings": [],
            "evidence": [{
                "path": signal["path"],
                "line": signal["line"],
                "signal": signal["signal"],
                "excerpt": signal["excerpt"],
            }],
            "unknowns": ["No live execution or profitability proof."],
            "confidence": "low",
        }

    @staticmethod
    def assert_context(user_payload, system_prompt):
        excerpts = user_payload.get("verified_source_excerpts", [])
        assert excerpts, "verified source excerpts must reach every model task"
        assert "blob_sha" in excerpts[0] and "excerpt_sha256" in excerpts[0]
        if "Independently challenge" in system_prompt:
            assert user_payload.get("prior_specialist_outputs"), "reviewer must receive prior reports"


class SemanticPipelineEndToEndTests(unittest.TestCase):
    def test_purpose_specialists_evidence_gate_and_independent_review_run_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "research.sqlite3"
            artifacts = root / "artifacts"
            vault = root / "vault"
            mission_id = "semantic-e2e-test"
            repository = "research-lab/flashloan-liquidator"

            expansion_id = stable_task_id(mission_id, "expand_candidate_tasks")
            synthesis_id = stable_task_id(mission_id, "mission_synthesis")
            base_tasks = [
                MissionTask(mission_id, expansion_id, "expand_candidate_tasks",
                            "research_director", (), {}, priority=40),
                MissionTask(mission_id, synthesis_id, "mission_synthesis",
                            "continuity_documentation", (), {}, priority=90),
            ]
            store = MissionTaskStore(database)
            try:
                store.create_plan(base_tasks)
                claim = store.claim_ready(mission_id, "test-planner", task_types={"expand_candidate_tasks"})[0]
                store.complete_task(mission_id, expansion_id, "test-planner", {"test_fixture": True})
                store.expand_candidates(
                    mission_id, expansion_id, [repository],
                    selected_roles=[
                        "protocol_specialist", "solidity_security", "execution_engineer",
                        "test_verification", "economics_quant", "dependency_license",
                    ],
                )
            finally:
                store.close()

            source = (
                "contract Liquidator {\n"
                "    function executeOperation() external returns (bool) {\n"
                "        return true;\n"
                "    }\n"
                "}\n"
            ).encode()
            blob_sha = git_blob_sha(source)
            relative_blob = f"{blob_sha[:2]}/{blob_sha[2:]}"
            blob_path = vault / relative_blob
            blob_path.parent.mkdir(parents=True)
            blob_path.write_bytes(source)
            commit_sha = "a" * 40
            tree_sha = "b" * 40
            signal = {
                "signal": "aave_execute_operation",
                "path": "contracts/Liquidator.sol",
                "line": 2,
                "excerpt": "function executeOperation() external returns (bool)",
            }
            mission_dir = artifacts / mission_id
            inspection_dir = mission_dir / "inspections"
            inspection_dir.mkdir(parents=True)
            inspection = {
                "repository": repository,
                "commit_sha": commit_sha,
                "tree_sha": tree_sha,
                "captured_files": [{
                    "path": "contracts/Liquidator.sol",
                    "blob_sha": blob_sha,
                    "size_bytes": len(source),
                    "vault_relative_path": relative_blob,
                }],
                "signals": [signal],
            }
            (inspection_dir / "research-lab__flashloan-liquidator.json").write_text(
                json.dumps(inspection), encoding="utf-8"
            )

            FakeLocalProvider.calls = []
            FakeLocalProvider.reviewer_prior_count = None
            executor = MissionExecutor(database_path=database, artifact_root=artifacts)
            with patch.dict(os.environ, {
                "FLR_MODEL_BASE_URL": "http://127.0.0.1:11434",
                "FLR_MODEL_NAME": "deterministic-fixture-model",
                "FLR_SNAPSHOT_DIR": str(vault),
            }), patch(
                "flashloan_research.specialist_runner.LocalOpenAICompatibleProvider",
                FakeLocalProvider,
            ):
                result = executor.run_local_semantic_agents(mission_id)

            self.assertEqual(result["status"], "executed_with_evidence_gate")
            self.assertTrue(result["evidence_validation"]["completed"])
            self.assertEqual(len(FakeLocalProvider.calls), 8)
            self.assertEqual(FakeLocalProvider.reviewer_prior_count, 7)
            self.assertTrue(all(
                call["payload"].get("verified_source_excerpts")
                for call in FakeLocalProvider.calls
            ))
            store = MissionTaskStore(database)
            try:
                rows = store.list_tasks(mission_id)
                statuses = {row["task_type"]: row["status"] for row in rows}
                self.assertEqual(statuses["candidate_purpose"], "completed")
                self.assertEqual(statuses["protocol_forensics"], "completed")
                self.assertEqual(statuses["security_forensics"], "completed")
                self.assertEqual(statuses["execution_forensics"], "completed")
                self.assertEqual(statuses["test_forensics"], "completed")
                self.assertEqual(statuses["economic_forensics"], "completed")
                self.assertEqual(statuses["dependency_forensics"], "completed")
                self.assertEqual(statuses["evidence_validation"], "completed")
                self.assertEqual(statuses["independent_review"], "completed")
                self.assertEqual(statuses["candidate_dossier"], "pending")
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()