from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


TASK_STATUSES = {"pending", "leased", "completed", "failed", "blocked"}
SPECIALIST_ROLES = {
    "protocol_specialist", "solidity_security", "execution_engineer",
    "test_verification", "economics_quant", "dependency_license",
}
ROLE_TASK_TYPES = {
    "protocol_specialist": "protocol_forensics",
    "solidity_security": "security_forensics",
    "execution_engineer": "execution_forensics",
    "test_verification": "test_forensics",
    "economics_quant": "economic_forensics",
    "dependency_license": "dependency_forensics",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_task_id(mission_id: str, task_type: str, key: str = "") -> str:
    digest = hashlib.sha256(f"{mission_id}|{task_type}|{key}".encode("utf-8")).hexdigest()[:24]
    return f"tsk-{digest}"


@dataclass(frozen=True)
class MissionTask:
    mission_id: str
    task_id: str
    task_type: str
    role: str
    depends_on: tuple[str, ...]
    payload: dict[str, Any]
    priority: int = 100
    max_attempts: int = 3
    budget_units: int = 1

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["depends_on"] = list(self.depends_on)
        return value


class MissionPlanError(ValueError):
    pass


def _task(mission_id: str, task_type: str, role: str, key: str = "",
          depends_on: tuple[str, ...] = (), payload: dict[str, Any] | None = None,
          priority: int = 100, max_attempts: int = 3, budget_units: int = 1) -> MissionTask:
    return MissionTask(
        mission_id=mission_id,
        task_id=stable_task_id(mission_id, task_type, key),
        task_type=task_type,
        role=role,
        depends_on=depends_on,
        payload=payload or {},
        priority=priority,
        max_attempts=max_attempts,
        budget_units=budget_units,
    )


def validate_acyclic(tasks: list[MissionTask]) -> None:
    by_id = {task.task_id: task for task in tasks}
    if len(by_id) != len(tasks):
        raise MissionPlanError("duplicate task IDs in plan")
    for task in tasks:
        missing = sorted(set(task.depends_on) - set(by_id))
        if missing:
            raise MissionPlanError(f"task {task.task_id} has unknown dependencies: {missing}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise MissionPlanError("mission task plan contains a dependency cycle")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in by_id[task_id].depends_on:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in by_id:
        visit(task_id)


def build_mission_plan(mission: dict[str, Any], taxonomy: dict[str, Any]) -> list[MissionTask]:
    mission_id = mission.get("mission_id")
    if not isinstance(mission_id, str) or not mission_id:
        raise MissionPlanError("mission_id is required")
    scope = mission.get("scope")
    if not isinstance(scope, dict):
        raise MissionPlanError("mission scope is required")
    family_queries = taxonomy.get("family_queries")
    if not isinstance(family_queries, dict):
        raise MissionPlanError("taxonomy family_queries is required")
    selected = scope.get("discovery_query_families") or list(family_queries)
    unknown = sorted(set(selected) - set(family_queries))
    if unknown:
        raise MissionPlanError(f"unknown taxonomy families: {unknown}")

    tasks: list[MissionTask] = []
    director = _task(
        mission_id, "mission_plan", "research_director", payload={
            "title": mission.get("title"),
            "objective": mission.get("objective"),
            "taxonomy_version": taxonomy.get("taxonomy_version", "unknown"),
            "selected_families": selected,
        }, priority=0, budget_units=1,
    )
    tasks.append(director)
    family_tasks: list[MissionTask] = []
    for family_id in selected:
        queries = family_queries[family_id]
        task = _task(
            mission_id, "discover_family", "github_discovery", key=family_id,
            depends_on=(director.task_id,),
            payload={"family_id": family_id, "queries": queries,
                     "per_page": scope.get("search_per_page", 100),
                     "max_pages_per_query": scope.get("max_pages_per_query", 10),
                     "include_archived": scope.get("include_archived", False),
                     "include_forked": scope.get("include_forked", True)},
            priority=10, max_attempts=4, budget_units=max(1, len(queries)),
        )
        family_tasks.append(task)
        tasks.append(task)
    merge = _task(
        mission_id, "merge_candidates", "github_discovery", depends_on=tuple(x.task_id for x in family_tasks),
        payload={"deduplicate_by": ["repository_id", "canonical_full_name"]},
        priority=20, budget_units=2,
    )
    triage = _task(
        mission_id, "purpose_triage", "protocol_specialist", depends_on=(merge.task_id,),
        payload={"classify_purpose_before_quality": True},
        priority=30, budget_units=2,
    )
    expansion = _task(
        mission_id, "expand_candidate_tasks", "research_director", depends_on=(triage.task_id,),
        payload={"conditional_specialists": sorted(SPECIALIST_ROLES)},
        priority=40, budget_units=1,
    )
    synthesis = _task(
        mission_id, "mission_synthesis", "continuity_documentation",
        depends_on=(expansion.task_id,),
        payload={"required_deliverables": mission.get("deliverables", [])},
        priority=90, budget_units=3,
    )
    continuation = _task(
        mission_id, "continuation_queue", "research_director",
        depends_on=(synthesis.task_id,),
        payload={"enqueue_next_unprocessed_batch": True},
        priority=100, budget_units=1,
    )
    tasks.extend([merge, triage, expansion, synthesis, continuation])
    validate_acyclic(tasks)
    return tasks


def build_candidate_tasks(mission_id: str, repository: str, expansion_task_id: str,
                          selected_roles: list[str] | None = None) -> list[MissionTask]:
    roles = sorted(set(selected_roles or SPECIALIST_ROLES) & SPECIALIST_ROLES)
    purpose = _task(
        mission_id, "candidate_purpose", "protocol_specialist", key=repository,
        depends_on=(expansion_task_id,), payload={"repository": repository},
        priority=45, budget_units=2,
    )
    tasks = [purpose]
    specialist_tasks: list[MissionTask] = []
    for role in roles:
        item = _task(
            mission_id, ROLE_TASK_TYPES[role], role, key=repository,
            depends_on=(purpose.task_id,),
            payload={"repository": repository, "candidate_scope": "commit_pinned_source_only"},
            priority=50, max_attempts=3, budget_units=3,
        )
        specialist_tasks.append(item)
        tasks.append(item)
    evidence = _task(
        mission_id, "evidence_validation", "evidence_auditor", key=repository,
        depends_on=tuple(x.task_id for x in specialist_tasks) or (purpose.task_id,),
        payload={"repository": repository, "require_path_line_commit_blob": True},
        priority=70, budget_units=2,
    )
    reviewer = _task(
        mission_id, "independent_review", "independent_reviewer", key=repository,
        depends_on=(evidence.task_id,),
        payload={"repository": repository, "challenge_security_and_economic_claims": True},
        priority=80, budget_units=2,
    )
    dossier = _task(
        mission_id, "candidate_dossier", "continuity_documentation", key=repository,
        depends_on=(reviewer.task_id,),
        payload={"repository": repository},
        priority=85, budget_units=2,
    )
    tasks.extend([evidence, reviewer, dossier])
    validate_acyclic(tasks)
    return tasks


class MissionTaskStore:
    """Durable idempotent task DAG, lease claiming and crash recovery on SQLite."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path, timeout=15, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA busy_timeout=15000")
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS mission_tasks (
            mission_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending','leased','completed','failed','blocked')),
            depends_on_json TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            priority INTEGER NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL,
            budget_units INTEGER NOT NULL,
            lease_owner TEXT,
            lease_expires_at TEXT,
            result_json TEXT,
            error TEXT,
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL,
            PRIMARY KEY (mission_id, task_id)
        );
        CREATE INDEX IF NOT EXISTS idx_mission_tasks_ready
            ON mission_tasks(mission_id, status, priority, created_at_utc);
        """)
        self.connection.commit()

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def create_plan(self, tasks: list[MissionTask]) -> dict[str, int]:
        if not tasks:
            raise MissionPlanError("cannot persist an empty task plan")
        validate_acyclic(tasks)
        now = utc_now()
        inserted = 0
        with self._lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                for task in tasks:
                    cur = self.connection.execute("""
                        INSERT OR IGNORE INTO mission_tasks
                        (mission_id,task_id,task_type,role,status,depends_on_json,payload_json,
                         priority,attempts,max_attempts,budget_units,created_at_utc,updated_at_utc)
                        VALUES (?,?,?,?,?,?,?,?,0,?,?,?,?)
                    """, (
                        task.mission_id, task.task_id, task.task_type, task.role, "pending",
                        json.dumps(list(task.depends_on), sort_keys=True),
                        json.dumps(task.payload, sort_keys=True),
                        task.priority, task.max_attempts, task.budget_units, now, now,
                    ))
                    inserted += cur.rowcount
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
        return {"inserted": inserted, "existing": len(tasks) - inserted}

    def get_task(self, mission_id: str, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM mission_tasks WHERE mission_id=? AND task_id=?",
                (mission_id, task_id),
            ).fetchone()
        return self._decode_row(row) if row else None

    def list_tasks(self, mission_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute(
                "SELECT * FROM mission_tasks WHERE mission_id=? ORDER BY priority,created_at_utc,task_id",
                (mission_id,),
            ).fetchall()
        return [self._decode_row(row) for row in rows]

    @staticmethod
    def _decode_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["depends_on"] = json.loads(item.pop("depends_on_json"))
        item["payload"] = json.loads(item.pop("payload_json"))
        item["result"] = json.loads(item.pop("result_json")) if item.get("result_json") else None
        item.pop("result_json", None)
        return item

    def claim_ready(self, mission_id: str, worker_id: str, limit: int = 1,
                    lease_seconds: int = 300) -> list[dict[str, Any]]:
        if not worker_id or not 1 <= limit <= 12 or not 10 <= lease_seconds <= 3600:
            raise ValueError("invalid worker_id, limit or lease_seconds")
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        expiry = (now_dt + timedelta(seconds=lease_seconds)).isoformat()
        claimed: list[dict[str, Any]] = []
        with self._lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                expired = self.connection.execute("""
                    SELECT mission_id,task_id,attempts,max_attempts FROM mission_tasks
                    WHERE mission_id=? AND status='leased' AND lease_expires_at < ?
                """, (mission_id, now)).fetchall()
                for row in expired:
                    next_status = "failed" if row["attempts"] >= row["max_attempts"] else "pending"
                    self.connection.execute("""
                        UPDATE mission_tasks SET status=?,lease_owner=NULL,lease_expires_at=NULL,
                        error=CASE WHEN ?='failed' THEN 'lease expired after retry budget' ELSE error END,
                        updated_at_utc=? WHERE mission_id=? AND task_id=?
                    """, (next_status, next_status, now, mission_id, row["task_id"]))
                pending = self.connection.execute("""
                    SELECT * FROM mission_tasks WHERE mission_id=? AND status='pending'
                    ORDER BY priority,created_at_utc,task_id
                """, (mission_id,)).fetchall()
                for row in pending:
                    deps = json.loads(row["depends_on_json"])
                    if deps:
                        placeholders = ",".join("?" for _ in deps)
                        states = self.connection.execute(
                            f"SELECT task_id,status FROM mission_tasks WHERE mission_id=? AND task_id IN ({placeholders})",
                            (mission_id, *deps),
                        ).fetchall()
                        status_by_id = {x["task_id"]: x["status"] for x in states}
                        if any(status_by_id.get(dep) in {"failed", "blocked"} for dep in deps):
                            self.connection.execute("""
                                UPDATE mission_tasks SET status='blocked',error='dependency failed or blocked',
                                updated_at_utc=? WHERE mission_id=? AND task_id=?
                            """, (now, mission_id, row["task_id"]))
                            continue
                        if any(status_by_id.get(dep) != "completed" for dep in deps):
                            continue
                    updated = self.connection.execute("""
                        UPDATE mission_tasks SET status='leased',lease_owner=?,lease_expires_at=?,
                        attempts=attempts+1,updated_at_utc=?
                        WHERE mission_id=? AND task_id=? AND status='pending'
                    """, (worker_id, expiry, now, mission_id, row["task_id"]))
                    if updated.rowcount == 1:
                        fresh = self.connection.execute(
                            "SELECT * FROM mission_tasks WHERE mission_id=? AND task_id=?",
                            (mission_id, row["task_id"]),
                        ).fetchone()
                        claimed.append(self._decode_row(fresh))
                    if len(claimed) >= limit:
                        break
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
        return claimed

    def complete_task(self, mission_id: str, task_id: str, worker_id: str,
                      result: dict[str, Any]) -> None:
        now = utc_now()
        encoded = json.dumps(result, ensure_ascii=False, sort_keys=True)
        with self._lock:
            cur = self.connection.execute("""
                UPDATE mission_tasks SET status='completed',result_json=?,error=NULL,
                lease_owner=NULL,lease_expires_at=NULL,updated_at_utc=?
                WHERE mission_id=? AND task_id=? AND status='leased' AND lease_owner=?
            """, (encoded, now, mission_id, task_id, worker_id))
            self.connection.commit()
        if cur.rowcount != 1:
            raise MissionPlanError("task lease not owned by worker or task is not leased")

    def fail_task(self, mission_id: str, task_id: str, worker_id: str,
                  error: str, retryable: bool = True) -> str:
        now = utc_now()
        with self._lock:
            row = self.connection.execute("""
                SELECT attempts,max_attempts FROM mission_tasks
                WHERE mission_id=? AND task_id=? AND status='leased' AND lease_owner=?
            """, (mission_id, task_id, worker_id)).fetchone()
            if row is None:
                raise MissionPlanError("task lease not owned by worker or task is not leased")
            status = "pending" if retryable and row["attempts"] < row["max_attempts"] else "failed"
            self.connection.execute("""
                UPDATE mission_tasks SET status=?,error=?,lease_owner=NULL,lease_expires_at=NULL,
                updated_at_utc=? WHERE mission_id=? AND task_id=?
            """, (status, str(error)[:2000], now, mission_id, task_id))
            self.connection.commit()
        return status

    def expand_candidates(self, mission_id: str, expansion_task_id: str,
                          repositories: list[str], selected_roles: list[str] | None = None) -> dict[str, int]:
        all_tasks: list[MissionTask] = []
        dossier_ids: list[str] = []
        for repository in sorted(set(repositories)):
            if not isinstance(repository, str) or repository.count("/") != 1:
                raise MissionPlanError("candidate repository must be owner/name")
            tasks = build_candidate_tasks(mission_id, repository, expansion_task_id, selected_roles)
            all_tasks.extend(tasks)
            dossier_ids.append(next(x.task_id for x in tasks if x.task_type == "candidate_dossier"))
        if all_tasks:
            self.create_plan(all_tasks)
        synthesis_id = stable_task_id(mission_id, "mission_synthesis")
        with self._lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                row = self.connection.execute(
                    "SELECT depends_on_json FROM mission_tasks WHERE mission_id=? AND task_id=?",
                    (mission_id, synthesis_id),
                ).fetchone()
                if row is None:
                    raise MissionPlanError("mission synthesis task does not exist")
                deps = json.loads(row["depends_on_json"])
                deps = list(dict.fromkeys(deps + dossier_ids))
                self.connection.execute("""
                    UPDATE mission_tasks SET depends_on_json=?,updated_at_utc=?
                    WHERE mission_id=? AND task_id=?
                """, (json.dumps(deps), utc_now(), mission_id, synthesis_id))
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
        return {"candidate_count": len(set(repositories)), "tasks_inserted": len(all_tasks),
                "synthesis_dependencies": len(dossier_ids)}
