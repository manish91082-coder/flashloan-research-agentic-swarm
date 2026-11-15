from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_FAILURE = (
    "SpecialistTaskError: independent reviewer context would omit a required prior report"
)
REQUIRED_PRIOR_TYPES = {
    "candidate_purpose", "protocol_forensics", "security_forensics",
    "execution_forensics", "test_forensics", "economic_forensics",
    "dependency_forensics",
}


class ReviewerRecoveryError(RuntimeError):
    pass


def _object(value: str | None, field: str) -> dict[str, Any]:
    try:
        result = json.loads(value or "{}")
    except json.JSONDecodeError as exc:
        raise ReviewerRecoveryError(f"invalid JSON in SQLite field {field}") from exc
    if not isinstance(result, dict):
        raise ReviewerRecoveryError(f"SQLite field {field} must be an object")
    return result


def _verified_report(task: sqlite3.Row, workspace: Path,
                     commit_sha: str, tree_sha: str) -> Path:
    result = _object(task["result_json"], "result_json")
    relative = result.get("report")
    if not isinstance(relative, str) or not relative:
        raise ReviewerRecoveryError(f"completed task {task['task_id']} has no report path")
    path = (workspace / relative).resolve()
    if workspace not in path.parents or not path.is_file():
        raise ReviewerRecoveryError(f"task report missing or outside workspace: {relative}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewerRecoveryError(f"cannot read task report: {relative}") from exc
    metadata = data.get("task_metadata", {})
    agent = data.get("agent_metadata", {})
    evidence = data.get("evidence_validation", {})
    if metadata.get("task_id") != task["task_id"] or metadata.get("task_type") != task["task_type"]:
        raise ReviewerRecoveryError(f"task report provenance mismatch: {relative}")
    if agent.get("role") != task["role"]:
        raise ReviewerRecoveryError(f"task report role mismatch: {relative}")
    if evidence.get("inspection_commit_sha") != commit_sha or evidence.get("inspection_tree_sha") != tree_sha:
        raise ReviewerRecoveryError(f"task report commit/tree pin mismatch: {relative}")
    if evidence.get("all_findings_linked_to_accepted_evidence") is not True:
        raise ReviewerRecoveryError(f"task report lacks claim-to-evidence validation: {relative}")
    return path


def requeue_failed_reviewers(database: Path, mission_id: str, expected_count: int,
                             workspace: Path) -> dict[str, Any]:
    if not database.is_file():
        raise ReviewerRecoveryError(f"mission database not found: {database}")
    con = sqlite3.connect(database, timeout=30)
    con.row_factory = sqlite3.Row
    requeued = []
    try:
        con.execute("BEGIN IMMEDIATE")
        if not con.execute(
            "SELECT 1 FROM research_missions WHERE mission_id=?", (mission_id,)
        ).fetchone():
            raise ReviewerRecoveryError(f"mission not found: {mission_id}")
        tasks = con.execute(
            "SELECT * FROM mission_tasks WHERE mission_id=?", (mission_id,)
        ).fetchall()
        reviewers = [x for x in tasks if x["task_type"] == "independent_review"]
        if len(reviewers) != expected_count:
            raise ReviewerRecoveryError(
                f"expected {expected_count} independent-review tasks, found {len(reviewers)}"
            )
        now = datetime.now(timezone.utc).isoformat()
        for reviewer in reviewers:
            if reviewer["status"] != "failed" or reviewer["error"] != EXPECTED_FAILURE:
                raise ReviewerRecoveryError(
                    f"refusing to reset reviewer {reviewer['task_id']}: not the exact known context-cap failure"
                )
            attempts, max_attempts = int(reviewer["attempts"]), int(reviewer["max_attempts"])
            if attempts >= max_attempts:
                raise ReviewerRecoveryError(f"reviewer retry budget exhausted: {reviewer['task_id']}")
            repository = _object(reviewer["payload_json"], "payload_json").get("repository")
            if not isinstance(repository, str) or not repository:
                raise ReviewerRecoveryError("reviewer task has no repository identity")

            prior = [
                x for x in tasks
                if _object(x["payload_json"], "payload_json").get("repository") == repository
                and (x["task_type"] == "candidate_purpose" or x["task_type"].endswith("_forensics"))
            ]
            if len(prior) != 7 or {x["task_type"] for x in prior} != REQUIRED_PRIOR_TYPES:
                raise ReviewerRecoveryError(f"{repository}: seven distinct purpose/specialist reports are required")
            if len({x["role"] for x in prior}) != 7:
                raise ReviewerRecoveryError(f"{repository}: specialist roles are not distinct")

            inspection_task = next(
                (x for x in tasks if x["task_type"] == "candidate_source_capture"
                 and _object(x["payload_json"], "payload_json").get("repository") == repository),
                None,
            )
            if inspection_task is None or inspection_task["status"] != "completed":
                raise ReviewerRecoveryError(f"{repository}: source inspection is incomplete")
            inspection_result = _object(inspection_task["result_json"], "result_json")
            inspection_rel = inspection_result.get("inspection_report")
            if not isinstance(inspection_rel, str):
                raise ReviewerRecoveryError(f"{repository}: inspection report path is missing")
            inspection_path = (workspace / inspection_rel).resolve()
            if workspace not in inspection_path.parents or not inspection_path.is_file():
                raise ReviewerRecoveryError(f"{repository}: inspection report is missing")
            inspection = json.loads(inspection_path.read_text(encoding="utf-8"))
            commit_sha, tree_sha = inspection.get("commit_sha"), inspection.get("tree_sha")
            if not isinstance(commit_sha, str) or not isinstance(tree_sha, str):
                raise ReviewerRecoveryError(f"{repository}: source commit/tree pins are missing")

            for task in prior:
                if task["status"] != "completed":
                    raise ReviewerRecoveryError(f"{repository}: prior task {task['task_type']} is incomplete")
                _verified_report(task, workspace, commit_sha, tree_sha)

            gate_task = next(
                (x for x in tasks if x["task_type"] == "evidence_validation"
                 and _object(x["payload_json"], "payload_json").get("repository") == repository),
                None,
            )
            if gate_task is None or gate_task["status"] != "completed":
                raise ReviewerRecoveryError(f"{repository}: evidence gate is incomplete")
            gate_result = _object(gate_task["result_json"], "result_json")
            gate_rel = gate_result.get("report")
            if not isinstance(gate_rel, str):
                raise ReviewerRecoveryError(f"{repository}: evidence gate report path is missing")
            gate_path = (workspace / gate_rel).resolve()
            if workspace not in gate_path.parents or not gate_path.is_file():
                raise ReviewerRecoveryError(f"{repository}: evidence gate report is missing")
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            if (gate.get("evidence_gate") != "pinned_evidence_and_claim_linkage_pass"
                    or gate.get("accepted_evidence_total", 0) <= 0
                    or gate.get("provenance_pass") is not True
                    or gate.get("claim_linkage_pass") is not True):
                raise ReviewerRecoveryError(f"{repository}: evidence gate is not accepted")
            dependencies = json.loads(reviewer["depends_on_json"] or "[]")
            if gate_task["task_id"] not in dependencies:
                raise ReviewerRecoveryError(f"{repository}: reviewer does not depend on its evidence gate")

            cursor = con.execute(
                """UPDATE mission_tasks
                   SET status='pending', error=NULL, lease_owner=NULL, lease_expires_at=NULL,
                       updated_at_utc=?
                   WHERE mission_id=? AND task_id=? AND status='failed' AND error=?""",
                (now, mission_id, reviewer["task_id"], EXPECTED_FAILURE),
            )
            if cursor.rowcount != 1:
                raise ReviewerRecoveryError(f"reviewer state changed: {reviewer['task_id']}")
            requeued.append({
                "task_id": reviewer["task_id"],
                "repository": repository,
                "attempts_preserved": attempts,
                "attempts_remaining": max_attempts - attempts,
                "prior_reports_verified": 7,
                "evidence_gate_verified": True,
            })
        con.commit()
        return {
            "mission_id": mission_id,
            "reviewers_expected": expected_count,
            "reviewers_requeued": len(requeued),
            "tasks": requeued,
            "reset_scope": "only independent_review tasks failed with the exact known reviewer-context cap error",
            "specialist_outputs_recomputed": False,
            "evidence_gates_recomputed": False,
            "candidate_code_executed": False,
        }
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Requeue only the r4 independent-review tasks blocked by the known context-cap error."
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--mission-id", required=True)
    parser.add_argument("--expected-count", type=int, default=2)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()
    if not 1 <= args.expected_count <= 10:
        raise SystemExit("--expected-count must be between 1 and 10")
    try:
        result = requeue_failed_reviewers(
            args.database, args.mission_id, args.expected_count, args.workspace.resolve()
        )
    except ReviewerRecoveryError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
