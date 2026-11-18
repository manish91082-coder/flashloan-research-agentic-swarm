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
from flashloan_research.storage import git_blob_sha
from flashloan_research.role_source_policy import role_path_admissible


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
        role = user_payload["role"]
        evidence_catalog = user_payload.get("source_evidence_catalog", [])
        evidence = evidence_catalog[0]["evidence_id"] if evidence_catalog else None
        role_sources_missing = (
            role in {"dependency_license", "test_verification"}
            and not user_payload.get("role_source_coverage", {}).get("present_families")
        )
        if role == "independent_reviewer":
            self.__class__.reviewer_prior_count = len(user_payload["prior_specialist_outputs"])
            decision = "inconclusive"
            disagreements = ["The supplied callback declaration does not establish Pool caller authentication, initiator binding, or repayment and premium handling."]
        else:
            decision = "not_applicable"
            disagreements = []
        category_by_role = {
            "candidate_purpose": "purpose",
            "protocol_specialist": "protocol_flow",
            "solidity_security": "security",
            "execution_engineer": "execution",
            "test_verification": "testing",
            "economics_quant": "economics",
            "dependency_license": "dependency_license",
            "independent_reviewer": "review_challenge",
        }
        if role == "independent_reviewer":
            assert {"review_decision", "review_disagreements"}.issubset(required_keys)
        else:
            assert not ({"review_decision", "review_disagreements"} & required_keys)
        result = {
            "summary": "Fixture analysis; all material claims are linked to a pinned source signal.",
            "purpose": "Flash-loan liquidation research implementation.",
            "purpose_category": "flash_loan_liquidation_bot",
            "implementation_status": "unknown" if role == "independent_reviewer" or role_sources_missing else "partial",
            "findings": [] if role == "independent_reviewer" or role_sources_missing else [{
                "finding_id": f"F-{role}",
                "claim": "The pinned source excerpt contains the executeOperation callback declaration.",
                "category": category_by_role[role],
                "severity": "high" if role == "solidity_security" else "not_applicable",
                "claim_status": "source_observed",
                "confidence": "low",
                "evidence_refs": [evidence],
            }],
            "evidence": [evidence] if evidence else [],
            "unknowns": (
                ["No role-admissible test, CI or test-configuration source was captured for this candidate."]
                if role_sources_missing and role == "test_verification" else
                ["No package manifest, lockfile, compiler/build configuration or license artifact was captured for this candidate."]
                if role_sources_missing and role == "dependency_license" else
                ["Pool caller authentication, initiator binding and repayment behavior are not established by the supplied callback declaration."]
                if role == "independent_reviewer" else
                ["No live execution or profitability proof."]
            ),
            "confidence": "low",
            "review_decision": decision,
            "review_disagreements": disagreements,
        }
        return {key: result[key] for key in required_keys}

    @staticmethod
    def assert_context(user_payload, system_prompt):
        excerpts = user_payload.get("verified_source_excerpts", [])
        catalog = user_payload.get("source_evidence_catalog", [])
        role = user_payload.get("role")
        missing_role_sources = (
            role in {"dependency_license", "test_verification"}
            and not user_payload.get("role_source_coverage", {}).get("present_families")
        )
        captured = user_payload.get("source_files_captured", [])
        if missing_role_sources:
            assert not excerpts and not catalog and not captured, "roles with no admissible source families must receive no source context"
        else:
            assert excerpts, "verified source excerpts must reach every eligible model task"
            assert "blob_sha" in excerpts[0] and "excerpt_sha256" in excerpts[0]
            assert catalog, "pinned evidence catalog must reach every eligible model task"
            assert all(role_path_admissible(role, item["path"]) for item in captured), (
                "captured source inventory must be filtered to role-admissible paths"
            )
        assert "task_type" in user_payload and "role" in user_payload
        if user_payload["role"] == "independent_reviewer":
            assert len(user_payload.get("prior_specialist_outputs", [])) == 7, (
                "reviewer must receive all seven unique purpose/specialist reports"
            )


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
                store.claim_ready(mission_id, "test-planner", task_types={"expand_candidate_tasks"})
                store.complete_task(mission_id, expansion_id, "test-planner", {"test_fixture": True})
                store.expand_candidates(
                    mission_id, expansion_id, [repository],
                    selected_roles=[
                        "protocol_specialist", "solidity_security", "execution_engineer",
                        "test_verification", "economics_quant", "dependency_license",
                    ],
                )
                source_capture = store.claim_ready(
                    mission_id, "test-capture", task_types={"candidate_source_capture"}
                )[0]
                store.complete_task(
                    mission_id, source_capture["task_id"], "test-capture", {"captured": True}
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
                "FLR_MODEL_TIMEOUT_SECONDS": "1200",
            }), patch(
                "flashloan_research.specialist_runner.LocalOpenAICompatibleProvider",
                FakeLocalProvider,
            ), patch(
                "flashloan_research.specialist_runner.SETTINGS",
                SimpleNamespace(snapshot_dir=vault, max_blob_bytes=250000),
            ):
                result = executor.run_local_semantic_agents(mission_id)

            self.assertEqual(result["status"], "executed_with_evidence_gate", json.dumps(result, indent=2, default=str))
            self.assertTrue(result["evidence_validation"]["completed"])
            # An inadequate specialist packet is dispositioned deterministically; the local model is not asked to fabricate a review.
            self.assertEqual(len(FakeLocalProvider.calls), 7)
            self.assertIsNone(FakeLocalProvider.reviewer_prior_count)
            self.assertTrue(all(
                call["payload"].get("verified_source_excerpts")
                for call in FakeLocalProvider.calls
                if not (
                    call["payload"]["role"] in {"dependency_license", "test_verification"}
                    and not call["payload"].get("role_source_coverage", {}).get("present_families")
                )
            ))
            gate = json.loads(Path(result["evidence_validation"]["completed"][0]["report"]).read_text())
            self.assertEqual(gate["evidence_gate"], "pinned_evidence_semantic_quality_and_claim_linkage_pass")
            self.assertTrue(gate["semantic_quality_pass"])
            self.assertTrue(gate["role_category_pass"])
            self.assertTrue(gate["confidence_calibration_pass"])
            self.assertTrue(gate["purpose_consensus_pass"])
            self.assertGreater(gate["accepted_evidence_total"], 0)
            self.assertGreater(gate["candidate_purpose_evidence_count"], 0)
            self.assertEqual(len(result["independent_review"]["completed"]), 1)
            self.assertEqual(result["independent_review"]["failures"], [])
            reviewer = result["independent_review"]["completed"][0]
            reviewer_report = json.loads(Path(reviewer["report"]).read_text())
            self.assertEqual(reviewer_report["review_decision"], "inconclusive")
            self.assertTrue(reviewer_report["review_disagreements"])
            self.assertEqual(reviewer_report["findings"], [])
            self.assertEqual(reviewer_report["implementation_status"], "unknown")

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
                report_paths = [
                    row["result"]["report"] for row in rows
                    if row["task_type"] in {"candidate_purpose", "protocol_forensics"}
                ]
                self.assertEqual(len(set(report_paths)), 2)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
