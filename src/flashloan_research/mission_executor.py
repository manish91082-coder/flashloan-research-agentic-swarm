from __future__ import annotations

import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .analyzer import ResearchPipeline
from .config import SETTINGS
from .github_api import GitHubClient
from .mission_discovery import run_taxonomy_discovery
from .mission_queue import MissionQueue
from .mission_runtime import MissionTaskStore, build_mission_plan
from .storage import ResearchStore, write_json


class MissionExecutionError(RuntimeError):
    pass


class MissionExecutor:
    """Checkpoint-friendly deterministic mission stages.

    This controller performs public GitHub discovery and commit-pinned source
    capture. Semantic specialist/reviewer tasks remain pending until a free,
    explicitly configured local inference provider is available.
    """

    def __init__(self, database_path: Path | None = None,
                 taxonomy_path: Path = Path("research/keyword-taxonomy.json"),
                 artifact_root: Path = Path("research_runs/mission"),
                 client_factory: Any = GitHubClient,
                 pipeline_factory: Any = ResearchPipeline):
        self.database_path = Path(database_path or SETTINGS.database_path)
        self.taxonomy_path = Path(taxonomy_path)
        self.artifact_root = Path(artifact_root)
        self.client_factory = client_factory
        self.pipeline_factory = pipeline_factory

    def _worker_id(self, mission_id: str) -> str:
        return f"mission-{mission_id}-{uuid.uuid4().hex[:8]}"

    def _load_mission(self, mission_id: str) -> dict[str, Any]:
        queue = MissionQueue(self.database_path)
        try:
            record = queue.get(mission_id)
        finally:
            queue.close()
        if record is None:
            raise MissionExecutionError(f"mission not found: {mission_id}")
        return record["payload"]

    def _set_mission_status(self, mission_id: str, status: str, reason: str | None = None) -> None:
        queue = MissionQueue(self.database_path)
        try:
            queue.set_status(mission_id, status, reason)
        finally:
            queue.close()

    def prepare(self, mission_id: str) -> dict[str, Any]:
        mission = self._load_mission(mission_id)
        taxonomy = json.loads(self.taxonomy_path.read_text(encoding="utf-8"))
        tasks = build_mission_plan(mission, taxonomy)
        store = MissionTaskStore(self.database_path)
        try:
            persisted = store.create_plan(tasks)
            director = next(x for x in tasks if x.task_type == "mission_plan")
            existing = store.get_task(mission_id, director.task_id)
            if existing and existing["status"] == "pending":
                worker_id = self._worker_id(mission_id)
                claimed = store.claim_ready(
                    mission_id, worker_id, limit=1, task_types={"mission_plan"}
                )
                if claimed:
                    store.complete_task(mission_id, director.task_id, worker_id, {
                        "status": "plan_validated",
                        "task_count": len(tasks),
                        "taxonomy_version": taxonomy.get("taxonomy_version", "unknown"),
                        "selected_families": mission.get("scope", {}).get("discovery_query_families", []),
                    })
            elif existing and existing["status"] not in {"completed"}:
                raise MissionExecutionError(
                    f"mission director task is {existing['status']}; resume after its lease or resolve blocker"
                )
        finally:
            store.close()
        self._set_mission_status(mission_id, "running")
        return {
            "mission_id": mission_id,
            "plan_task_count": len(tasks),
            "plan_inserted": persisted["inserted"],
            "plan_existing": persisted["existing"],
            "taxonomy_version": taxonomy.get("taxonomy_version", "unknown"),
        }

    def discover(self, mission_id: str) -> dict[str, Any]:
        mission = self._load_mission(mission_id)
        policy = mission.get("agent_policy", {})
        parallel = int(policy.get("max_parallel_agents", 4))
        worker_id = self._worker_id(mission_id)
        task_store = MissionTaskStore(self.database_path)
        taxonomy_path = self.taxonomy_path
        mission_dir = self.artifact_root / mission_id
        mission_dir.mkdir(parents=True, exist_ok=True)
        completed: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []

        def execute(task: dict[str, Any]) -> dict[str, Any]:
            family_id = task["payload"]["family_id"]
            family_store = ResearchStore(self.database_path)
            try:
                report = run_taxonomy_discovery(
                    self.client_factory(), family_store, taxonomy_path,
                    selected_families=[family_id],
                    per_page=task["payload"]["per_page"],
                    max_pages=task["payload"]["max_pages_per_query"],
                    include_archived=task["payload"]["include_archived"],
                    include_forked=task["payload"]["include_forked"],
                )
                output = mission_dir / f"discovery-{family_id}.json"
                write_json(output, report)
                summary = {
                    "family_id": family_id,
                    "unique_candidate_count": report["unique_candidate_count"],
                    "query_count": report["query_count"],
                    "complete_query_count": report["complete_query_count"],
                    "incomplete_query_count": report["incomplete_query_count"],
                    "coverage_complete": report["coverage_complete"],
                    "report": str(output),
                }
                task_store.complete_task(mission_id, task["task_id"], worker_id, summary)
                return summary
            except Exception as exc:
                state = task_store.fail_task(
                    mission_id, task["task_id"], worker_id,
                    f"{type(exc).__name__}: {str(exc)}", retryable=True,
                )
                return {"family_id": family_id, "status": state, "error": str(exc)[:500]}
            finally:
                family_store.close()

        try:
            while True:
                claimed = task_store.claim_ready(
                    mission_id, worker_id, limit=parallel, lease_seconds=900,
                    task_types={"discover_family"},
                )
                if not claimed:
                    break
                with ThreadPoolExecutor(max_workers=min(parallel, len(claimed))) as pool:
                    futures = [pool.submit(execute, task) for task in claimed]
                    for future in as_completed(futures):
                        result = future.result()
                        if result.get("status") in {"pending", "failed"} or "error" in result:
                            failures.append(result)
                        else:
                            completed.append(result)
            rows = task_store.list_tasks(mission_id)
            family_rows = [x for x in rows if x["task_type"] == "discover_family"]
            unresolved = [x for x in family_rows if x["status"] != "completed"]
            return {
                "mission_id": mission_id,
                "family_tasks_total": len(family_rows),
                "family_tasks_completed_this_run": len(completed),
                "family_tasks_unresolved": len(unresolved),
                "query_count": sum(x.get("query_count", 0) for x in completed),
                "candidate_count_per_family_sum_not_deduplicated": sum(
                    x.get("unique_candidate_count", 0) for x in completed
                ),
                "coverage_incomplete_family_count": sum(
                    1 for x in completed if not x.get("coverage_complete", False)
                ),
                "reports": completed,
                "failures": failures,
                "ready_for_merge": not unresolved,
            }
        finally:
            task_store.close()

    def merge_and_expand(self, mission_id: str) -> dict[str, Any]:
        mission = self._load_mission(mission_id)
        worker_id = self._worker_id(mission_id)
        task_store = MissionTaskStore(self.database_path)
        research_store = ResearchStore(self.database_path)
        try:
            merge_claim = task_store.claim_ready(
                mission_id, worker_id, task_types={"merge_candidates"}
            )
            if merge_claim:
                candidates = research_store.list_candidates(limit=50000)
                task_store.complete_task(mission_id, merge_claim[0]["task_id"], worker_id, {
                    "unique_repository_count": len(candidates),
                    "source": "deduplicated_research_store",
                    "candidate_purpose_verified": False,
                })
            else:
                merge_task = next((x for x in task_store.list_tasks(mission_id)
                                   if x["task_type"] == "merge_candidates"), None)
                if not merge_task or merge_task["status"] != "completed":
                    raise MissionExecutionError("merge task is not ready; some discovery families may be blocked")

            candidates = research_store.list_candidates(limit=50000)
            triage_claim = task_store.claim_ready(
                mission_id, worker_id, task_types={"purpose_triage"}
            )
            if triage_claim:
                task_store.complete_task(mission_id, triage_claim[0]["task_id"], worker_id, {
                    "candidate_count": len(candidates),
                    "purpose_status": "purpose_unverified_until_commit_pinned_source_review",
                    "triage_basis": "search-family provenance and GitHub repository metadata only",
                })
            else:
                triage_task = next((x for x in task_store.list_tasks(mission_id)
                                    if x["task_type"] == "purpose_triage"), None)
                if not triage_task or triage_task["status"] != "completed":
                    raise MissionExecutionError("purpose-triage task is not ready")

            expansion_task = next(x for x in task_store.list_tasks(mission_id)
                                  if x["task_type"] == "expand_candidate_tasks")
            if expansion_task["status"] == "pending":
                expansion_claim = task_store.claim_ready(
                    mission_id, worker_id, task_types={"expand_candidate_tasks"}
                )
                if not expansion_claim:
                    raise MissionExecutionError("candidate expansion task is not ready")
                batch_limit = int(mission.get("scope", {}).get("repository_limit", 100))
                batch = candidates[:batch_limit]
                repositories = [x["full_name"] for x in batch]
                roles = mission.get("agent_policy", {}).get("specialists", [])
                expanded = task_store.expand_candidates(
                    mission_id, expansion_task["task_id"], repositories, roles
                )
                task_store.complete_task(mission_id, expansion_task["task_id"], worker_id, {
                    **expanded,
                    "batch_limit": batch_limit,
                    "candidate_inventory_count": len(candidates),
                    "candidates_remaining_unplanned": max(0, len(candidates) - len(batch)),
                    "repository_batch": repositories,
                })
            else:
                expanded = {"candidate_count": 0, "tasks_inserted": 0, "synthesis_dependencies": 0}
                batch_limit = int(mission.get("scope", {}).get("repository_limit", 100))
                batch = candidates[:batch_limit]

            mission_dir = self.artifact_root / mission_id
            mission_dir.mkdir(parents=True, exist_ok=True)
            inventory_path = mission_dir / "candidate-inventory.json"
            write_json(inventory_path, {
                "mission_id": mission_id,
                "candidate_count": len(candidates),
                "candidate_purpose_status": "purpose_unverified",
                "candidates": candidates,
                "candidate_batch_limit": batch_limit,
                "first_batch_repositories": [x["full_name"] for x in batch],
                "remaining_repositories": [x["full_name"] for x in candidates[batch_limit:]],
            })
            return {
                "mission_id": mission_id,
                "unique_candidate_count": len(candidates),
                "first_audit_batch_count": min(len(candidates), batch_limit),
                "remaining_unplanned_count": max(0, len(candidates) - batch_limit),
                "candidate_inventory": str(inventory_path),
                "candidate_task_expansion": expanded,
            }
        finally:
            research_store.close()
            task_store.close()

    def inspect_candidate_batch(self, mission_id: str) -> dict[str, Any]:
        mission = self._load_mission(mission_id)
        worker_id = self._worker_id(mission_id)
        parallel = int(mission.get("agent_policy", {}).get("max_parallel_agents", 4))
        task_store = MissionTaskStore(self.database_path)
        mission_dir = self.artifact_root / mission_id
        inspection_dir = mission_dir / "inspections"
        inspection_dir.mkdir(parents=True, exist_ok=True)

        def inspect(task: dict[str, Any]) -> dict[str, Any]:
            repository = task["payload"]["repository"]
            store = ResearchStore(self.database_path)
            try:
                pipeline = self.pipeline_factory()
                result = pipeline.inspect(repository, store)
                path = inspection_dir / (repository.replace("/", "__") + ".json")
                write_json(path, result)
                summary = {
                    "repository": repository,
                    "commit_sha": result["commit_sha"],
                    "tree_sha": result["tree_sha"],
                    "source_files_captured": result["source_files_captured"],
                    "source_capture_complete_within_configured_scope": result[
                        "source_capture_complete_within_configured_scope"
                    ],
                    "signal_count": len(result["signals"]),
                    "inspection_report": str(path),
                    "purpose_classification": "purpose_unverified_pending_semantic_forensic_review",
                }
                task_store.complete_task(mission_id, task["task_id"], worker_id, summary)
                return summary
            except Exception as exc:
                status = task_store.fail_task(
                    mission_id, task["task_id"], worker_id,
                    f"{type(exc).__name__}: {str(exc)}", retryable=True,
                )
                return {"repository": repository, "status": status, "error": str(exc)[:500]}
            finally:
                store.close()

        completed: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        try:
            while True:
                claimed = task_store.claim_ready(
                    mission_id, worker_id, limit=parallel, lease_seconds=900,
                    task_types={"candidate_source_capture"},
                )
                if not claimed:
                    break
                with ThreadPoolExecutor(max_workers=min(parallel, len(claimed))) as pool:
                    futures = [pool.submit(inspect, task) for task in claimed]
                    for future in as_completed(futures):
                        result = future.result()
                        if result.get("status") in {"pending", "failed"} or "error" in result:
                            failures.append(result)
                        else:
                            completed.append(result)
            remaining = [
                x for x in task_store.list_tasks(mission_id)
                if x["task_type"] == "candidate_source_capture" and x["status"] != "completed"
            ]
            return {
                "mission_id": mission_id,
                "source_inspections_completed": len(completed),
                "source_inspections_unresolved": len(remaining),
                "reports": completed,
                "failures": failures,
                "semantic_purpose_classification": "not_asserted_by_static_signals",
            }
        finally:
            task_store.close()

    def finalize(self, mission_id: str) -> dict[str, Any]:
        store = MissionTaskStore(self.database_path)
        try:
            tasks = store.list_tasks(mission_id)
            counts: dict[str, int] = {}
            for task in tasks:
                counts[task["status"]] = counts.get(task["status"], 0) + 1
            pending_roles = sorted({
                task["role"] for task in tasks
                if task["status"] in {"pending", "leased"} and task["role"] not in {"research_director"}
            })
        finally:
            store.close()
        endpoint = os.getenv("FLR_MODEL_BASE_URL", "").strip()
        if endpoint:
            model_status = "blocked_provider_adapter_not_implemented"
            blocker_text = (
                "A model endpoint is configured, but the approved free-provider adapter and "
                "semantic specialist execution gate are not implemented yet."
            )
        else:
            model_status = "blocked_no_approved_free_local_model_endpoint"
            blocker_text = (
                "No approved free local inference endpoint is configured. Semantic specialist and "
                "independent-review tasks remain pending."
            )
        reason = None if not pending_roles else (
            "Deterministic discovery and commit-pinned source capture ran. " + blocker_text
        )
        final_status = "blocked" if pending_roles else "completed"
        self._set_mission_status(mission_id, final_status, reason)
        return {
            "mission_id": mission_id,
            "mission_status": final_status,
            "task_status_counts": counts,
            "pending_roles": pending_roles,
            "model_runtime_status": model_status,
            "blocker": reason,
            "research_only": True,
            "candidate_code_executed": False,
        }

    def run_mission(self, mission_id: str) -> dict[str, Any]:
        prepared = self.prepare(mission_id)
        discovery = self.discover(mission_id)
        if not discovery["ready_for_merge"]:
            task_store = MissionTaskStore(self.database_path)
            try:
                family_rows = [x for x in task_store.list_tasks(mission_id) if x["task_type"] == "discover_family"]
                all_leased = bool(family_rows) and all(x["status"] == "leased" for x in family_rows if x["status"] != "completed")
            finally:
                task_store.close()
            if all_leased:
                self._set_mission_status(mission_id, "running", "Discovery tasks are leased by a prior worker and will resume after lease expiry.")
                return {"prepare": prepared, "discovery": discovery, "status": "waiting_for_lease_recovery"}
            self._set_mission_status(mission_id, "blocked", "One or more discovery-family tasks remain incomplete.")
            return {"prepare": prepared, "discovery": discovery, "status": "blocked"}
        expansion = self.merge_and_expand(mission_id)
        inspections = self.inspect_candidate_batch(mission_id)
        final = self.finalize(mission_id)
        return {
            "prepare": prepared,
            "discovery": discovery,
            "candidate_expansion": expansion,
            "source_inspection": inspections,
            "final": final,
        }
