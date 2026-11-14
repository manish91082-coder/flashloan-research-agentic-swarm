from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .analyzer import ResearchPipeline
from .config import SETTINGS
from .github_api import GitHubClient
from .storage import ResearchStore


QUEUE_SCHEMA = """
CREATE TABLE IF NOT EXISTS source_capture_runs (
    run_id TEXT PRIMARY KEY,
    manifest_path TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    total_candidates INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_capture_items (
    run_id TEXT NOT NULL,
    candidate_index INTEGER NOT NULL,
    repository TEXT NOT NULL,
    repository_id INTEGER NOT NULL,
    metadata_json TEXT NOT NULL,
    matched_families_json TEXT NOT NULL,
    discovered_by_json TEXT NOT NULL,
    priority INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','leased','captured','failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    lease_owner TEXT,
    lease_expires_at TEXT,
    commit_sha TEXT,
    tree_sha TEXT,
    report_path TEXT,
    capture_json TEXT,
    error TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    PRIMARY KEY(run_id, repository),
    UNIQUE(run_id, candidate_index)
);
CREATE INDEX IF NOT EXISTS idx_source_capture_ready
ON source_capture_items(run_id, status, priority, candidate_index);
"""


class SourceCaptureError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + f".{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _family_priority(families: list[str]) -> int:
    direct = {"flash_loan_core", "flash_loan_provider_apis", "defi_liquidation"}
    adjacent = {"arbitrage", "dex_and_liquidity", "mev_and_searchers", "lending_protocols"}
    if direct.intersection(families):
        return 0
    if adjacent.intersection(families):
        return 1
    return 2


def _manifest_candidates(manifest_path: Path, workspace_root: Path) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    manifest_path = Path(manifest_path).resolve()
    root = Path(workspace_root).resolve()
    if root not in manifest_path.parents:
        raise SourceCaptureError("manifest must be located inside workspace_root")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceCaptureError(f"cannot read manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("record_type") != "resumable_discovery_candidate_batch_manifest":
        raise SourceCaptureError("unsupported discovery batch manifest record_type")
    run_id = manifest.get("run_id")
    batches = manifest.get("batches")
    total_expected = manifest.get("candidate_count")
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", run_id):
        raise SourceCaptureError("manifest run_id must be a safe 1..100 character identifier")
    if isinstance(total_expected, bool) or not isinstance(total_expected, int) or total_expected < 0:
        raise SourceCaptureError("manifest candidate_count is invalid")
    if not isinstance(batches, list) or manifest.get("batch_count") != len(batches):
        raise SourceCaptureError("manifest batch_count does not match batches array")

    manifest_sha = sha256_file(manifest_path)
    candidates: list[dict[str, Any]] = []
    seen_repositories: set[str] = set()
    seen_ids: set[int] = set()
    next_index = 0
    for batch in batches:
        if not isinstance(batch, dict):
            raise SourceCaptureError("manifest batch entry must be an object")
        relative = batch.get("path")
        expected_sha = batch.get("sha256")
        expected_count = batch.get("candidate_count")
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise SourceCaptureError("batch path must be a safe workspace-relative path")
        batch_path = (root / relative).resolve()
        if root not in batch_path.parents or not batch_path.is_file():
            raise SourceCaptureError(f"batch file is missing or escapes workspace: {relative}")
        if not isinstance(expected_sha, str) or sha256_file(batch_path) != expected_sha:
            raise SourceCaptureError(f"batch SHA-256 mismatch: {relative}")
        first = batch.get("first_candidate_index")
        last = batch.get("last_candidate_index")
        if first != next_index or not isinstance(expected_count, int) or last != first + expected_count - 1:
            raise SourceCaptureError(f"batch index range is discontinuous: {relative}")

        count = 0
        with batch_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise SourceCaptureError(f"invalid JSONL in {relative}: {exc}") from exc
                if not isinstance(item, dict):
                    raise SourceCaptureError(f"candidate row must be an object in {relative}")
                index = item.get("candidate_index")
                repository = item.get("repository")
                repository_id = item.get("repository_id")
                metadata = item.get("metadata")
                families = item.get("matched_families", [])
                discovered_by = item.get("discovered_by", [])
                if index != next_index or not isinstance(repository, str) or repository.count("/") != 1:
                    raise SourceCaptureError(f"candidate identity/index invalid at global index {next_index}")
                if not isinstance(metadata, dict) or metadata.get("full_name") != repository:
                    raise SourceCaptureError(f"metadata identity mismatch for {repository}")
                if not isinstance(metadata.get("default_branch"), str) or not metadata["default_branch"]:
                    raise SourceCaptureError(f"default branch missing for {repository}")
                if isinstance(repository_id, bool) or not isinstance(repository_id, int) or repository_id <= 0:
                    raise SourceCaptureError(f"GitHub repository ID invalid for {repository}")
                if repository in seen_repositories or repository_id in seen_ids:
                    raise SourceCaptureError(f"duplicate repository identity in manifest: {repository}")
                if not isinstance(families, list) or any(not isinstance(x, str) for x in families):
                    raise SourceCaptureError(f"matched_families invalid for {repository}")
                if not isinstance(discovered_by, list) or any(not isinstance(x, dict) for x in discovered_by):
                    raise SourceCaptureError(f"discovered_by invalid for {repository}")
                if item.get("audit_status") != "pending_commit_pinned_source_capture":
                    raise SourceCaptureError(f"unexpected audit status for {repository}")
                candidates.append({
                    "candidate_index": index,
                    "repository": repository,
                    "repository_id": repository_id,
                    "metadata": metadata,
                    "matched_families": families,
                    "discovered_by": discovered_by,
                    "priority": _family_priority(families),
                })
                seen_repositories.add(repository)
                seen_ids.add(repository_id)
                next_index += 1
                count += 1
        if count != expected_count:
            raise SourceCaptureError(f"batch candidate count mismatch: {relative}")
        if count and next_index - 1 != last:
            raise SourceCaptureError(f"batch last index mismatch: {relative}")

    if len(candidates) != total_expected or next_index != total_expected:
        raise SourceCaptureError(
            f"manifest candidate total mismatch: parsed {len(candidates)}, expected {total_expected}"
        )
    return manifest, manifest_sha, candidates


class SourceCaptureQueue:
    """SQLite-backed, idempotent source-capture queue with expiring leases."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(
            self.database_path, timeout=30, check_same_thread=False
        )
        self.connection.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA busy_timeout=30000")
        self.connection.executescript(QUEUE_SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        with self.lock:
            self.connection.close()

    def import_manifest(self, manifest_path: Path, workspace_root: Path) -> dict[str, Any]:
        manifest, manifest_sha, candidates = _manifest_candidates(manifest_path, workspace_root)
        run_id = manifest["run_id"]
        now = utc_now()
        with self.lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                existing = self.connection.execute(
                    "SELECT * FROM source_capture_runs WHERE run_id=?", (run_id,)
                ).fetchone()
                if existing:
                    if existing["manifest_sha256"] != manifest_sha:
                        raise SourceCaptureError("run_id already exists for a different manifest SHA-256")
                    count = self.connection.execute(
                        "SELECT COUNT(*) FROM source_capture_items WHERE run_id=?", (run_id,)
                    ).fetchone()[0]
                    if count != len(candidates):
                        raise SourceCaptureError("stored queue count differs from verified manifest")
                    self.connection.commit()
                    return {
                        "run_id": run_id, "status": existing["status"],
                        "candidate_count": count, "already_imported": True,
                        "manifest_sha256": manifest_sha,
                    }
                self.connection.execute(
                    """INSERT INTO source_capture_runs
                    (run_id,manifest_path,manifest_sha256,total_candidates,status,created_at_utc,updated_at_utc)
                    VALUES(?,?,?,?,?,?,?)""",
                    (run_id, str(Path(manifest_path).resolve()), manifest_sha,
                     len(candidates), "queued", now, now),
                )
                for item in candidates:
                    self.connection.execute(
                        """INSERT INTO source_capture_items
                        (run_id,candidate_index,repository,repository_id,metadata_json,
                         matched_families_json,discovered_by_json,priority,status,
                         attempts,max_attempts,created_at_utc,updated_at_utc)
                        VALUES(?,?,?,?,?,?,?,?, 'pending',0,3,?,?)""",
                        (run_id, item["candidate_index"], item["repository"], item["repository_id"],
                         json.dumps(item["metadata"], ensure_ascii=False, sort_keys=True),
                         json.dumps(item["matched_families"], sort_keys=True),
                         json.dumps(item["discovered_by"], sort_keys=True), item["priority"], now, now),
                    )
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
        return {
            "run_id": run_id, "status": "queued",
            "candidate_count": len(candidates), "already_imported": False,
            "manifest_sha256": manifest_sha,
        }

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json"))
        item["matched_families"] = json.loads(item.pop("matched_families_json"))
        item["discovered_by"] = json.loads(item.pop("discovered_by_json"))
        item["capture"] = json.loads(item["capture_json"]) if item.get("capture_json") else None
        item.pop("capture_json", None)
        return item

    def claim_ready(self, run_id: str, worker_id: str, limit: int,
                    lease_seconds: int = 3600) -> list[dict[str, Any]]:
        if not worker_id or not 1 <= limit <= 12 or not 60 <= lease_seconds <= 3600:
            raise ValueError("worker_id, limit or lease_seconds is invalid")
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        expiry = (now_dt + timedelta(seconds=lease_seconds)).isoformat()
        claimed: list[dict[str, Any]] = []
        with self.lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                self.connection.execute(
                    """UPDATE source_capture_items
                    SET status=CASE WHEN attempts>=max_attempts THEN 'failed' ELSE 'pending' END,
                        lease_owner=NULL,lease_expires_at=NULL,
                        error=CASE WHEN attempts>=max_attempts THEN 'lease expired after retry budget' ELSE error END,
                        updated_at_utc=?
                    WHERE run_id=? AND status='leased' AND lease_expires_at < ?""",
                    (now, run_id, now),
                )
                rows = self.connection.execute(
                    """SELECT * FROM source_capture_items
                    WHERE run_id=? AND status='pending' AND attempts<max_attempts
                    ORDER BY priority,candidate_index LIMIT ?""",
                    (run_id, limit),
                ).fetchall()
                for row in rows:
                    cur = self.connection.execute(
                        """UPDATE source_capture_items SET status='leased',lease_owner=?,
                        lease_expires_at=?,attempts=attempts+1,updated_at_utc=?
                        WHERE run_id=? AND repository=? AND status='pending'""",
                        (worker_id, expiry, now, run_id, row["repository"]),
                    )
                    if cur.rowcount == 1:
                        fresh = self.connection.execute(
                            "SELECT * FROM source_capture_items WHERE run_id=? AND repository=?",
                            (run_id, row["repository"]),
                        ).fetchone()
                        claimed.append(self._decode(fresh))
                self.connection.execute(
                    "UPDATE source_capture_runs SET status='processing',updated_at_utc=? WHERE run_id=?",
                    (now, run_id),
                )
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
        return claimed

    def complete(self, run_id: str, repository: str, worker_id: str,
                 report_path: Path, capture: dict[str, Any]) -> None:
        now = utc_now()
        with self.lock:
            cur = self.connection.execute(
                """UPDATE source_capture_items SET status='captured',lease_owner=NULL,
                lease_expires_at=NULL,commit_sha=?,tree_sha=?,report_path=?,capture_json=?,
                error=NULL,updated_at_utc=?
                WHERE run_id=? AND repository=? AND status='leased' AND lease_owner=?""",
                (capture.get("commit_sha"), capture.get("tree_sha"), str(report_path),
                 json.dumps(capture, ensure_ascii=False, sort_keys=True), now,
                 run_id, repository, worker_id),
            )
            self.connection.commit()
        if cur.rowcount != 1:
            raise SourceCaptureError("source-capture lease was lost before completion")

    def fail(self, run_id: str, repository: str, worker_id: str, error: str) -> str:
        now = utc_now()
        with self.lock:
            row = self.connection.execute(
                """SELECT attempts,max_attempts FROM source_capture_items
                WHERE run_id=? AND repository=? AND status='leased' AND lease_owner=?""",
                (run_id, repository, worker_id),
            ).fetchone()
            if row is None:
                raise SourceCaptureError("source-capture lease was lost before failure update")
            status = "pending" if row["attempts"] < row["max_attempts"] else "failed"
            self.connection.execute(
                """UPDATE source_capture_items SET status=?,lease_owner=NULL,
                lease_expires_at=NULL,error=?,updated_at_utc=?
                WHERE run_id=? AND repository=?""",
                (status, error[:2000], now, run_id, repository),
            )
            self.connection.commit()
        return status

    def summary(self, run_id: str) -> dict[str, Any]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT status,capture_json FROM source_capture_items WHERE run_id=?", (run_id,)
            ).fetchall()
            run = self.connection.execute(
                "SELECT total_candidates FROM source_capture_runs WHERE run_id=?", (run_id,)
            ).fetchone()
            if run is None:
                raise SourceCaptureError(f"source-capture run not found: {run_id}")
            counts = {key: 0 for key in ("pending", "leased", "captured", "failed")}
            complete = limited = 0
            for row in rows:
                counts[row["status"]] += 1
                if row["capture_json"]:
                    capture = json.loads(row["capture_json"])
                    if capture.get("source_capture_complete_within_configured_scope") is True:
                        complete += 1
                    else:
                        limited += 1
            status = "processing" if counts["pending"] or counts["leased"] else (
                "completed" if not counts["failed"] else "completed_with_failures"
            )
            self.connection.execute(
                "UPDATE source_capture_runs SET status=?,updated_at_utc=? WHERE run_id=?",
                (status, utc_now(), run_id),
            )
            self.connection.commit()
        return {
            "run_id": run_id, "status": status, "total": int(run["total_candidates"]),
            **counts, "captured_complete_within_scope": complete,
            "captured_with_coverage_limits": limited,
        }


class SourceCaptureWorker:
    """Resumable first-pass source capture for immutable discovery audit batches."""

    def __init__(self, database_path: Path | None = None,
                 snapshot_dir: Path | None = None,
                 output_dir: Path = Path("reports/source-capture"),
                 max_source_files: int = 30,
                 max_blob_bytes: int = 250_000,
                 client_factory: Any = GitHubClient,
                 pipeline_factory: Any = None):
        self.database_path = Path(database_path or SETTINGS.database_path)
        self.snapshot_dir = Path(snapshot_dir or SETTINGS.snapshot_dir)
        self.output_dir = Path(output_dir)
        self.max_source_files = max_source_files
        self.max_blob_bytes = max_blob_bytes
        self.client_factory = client_factory
        self.pipeline_factory = pipeline_factory
        if not 1 <= max_source_files <= 80 or not 1 <= max_blob_bytes <= 1_000_000:
            raise ValueError("source capture limits are outside the supported bounds")

    def _pipeline(self) -> Any:
        if self.pipeline_factory is not None:
            return self.pipeline_factory()
        settings = replace(
            SETTINGS, database_path=self.database_path, snapshot_dir=self.snapshot_dir,
            max_source_files=self.max_source_files, max_blob_bytes=self.max_blob_bytes,
        )
        return ResearchPipeline(self.client_factory(settings), settings)

    def _capture_one(self, item: dict[str, Any], run_id: str, worker_id: str,
                     queue: SourceCaptureQueue) -> dict[str, Any]:
        repository = item["repository"]
        store = ResearchStore(self.database_path)
        try:
            result = self._pipeline().inspect(repository, store)
            filename = re.sub(r"[^A-Za-z0-9._-]+", "_", repository.replace("/", "__"))
            report_path = self.output_dir / run_id / f"{item['candidate_index']:05d}-{filename}.json"
            report = {
                "schema_version": "1.0",
                "record_type": "commit_pinned_source_capture",
                "run_id": run_id,
                "candidate_index": item["candidate_index"],
                "repository": repository,
                "repository_id": item["repository_id"],
                "matched_families": item["matched_families"],
                "discovered_by": item["discovered_by"],
                "capture_attempt": item["attempts"],
                "capture_method": "ResearchPipeline.inspect",
                "audit_status": "source_captured_pending_semantic_review",
                "candidate_code_executed": False,
                **result,
            }
            atomic_write_json(report_path, report)
            capture_summary = {
                "commit_sha": result["commit_sha"],
                "tree_sha": result["tree_sha"],
                "source_files_captured": result["source_files_captured"],
                "source_capture_complete_within_configured_scope":
                    result["source_capture_complete_within_configured_scope"],
                "signal_count": len(result.get("signals", [])),
                "report_path": str(report_path),
            }
            queue.complete(run_id, repository, worker_id, report_path, capture_summary)
            return {"repository": repository, "status": "captured", **capture_summary}
        except Exception as exc:
            status = queue.fail(run_id, repository, worker_id, f"{type(exc).__name__}: {exc}")
            return {"repository": repository, "status": status, "error": str(exc)[:500]}
        finally:
            store.close()

    def _capture_cycle(self, queue: SourceCaptureQueue, run_id: str,
                       max_candidates: int, parallel: int) -> dict[str, Any]:
        worker_id = f"source-capture-{uuid.uuid4().hex[:12]}"
        claimed = queue.claim_ready(run_id, worker_id, max_candidates, lease_seconds=3600)
        completed: list[dict[str, Any]] = []
        if claimed:
            with ThreadPoolExecutor(max_workers=min(parallel, len(claimed))) as pool:
                futures = [
                    pool.submit(self._capture_one, item, run_id, worker_id, queue)
                    for item in claimed
                ]
                for future in as_completed(futures):
                    completed.append(future.result())
        return {
            "attempted_this_cycle": len(claimed),
            "results": sorted(completed, key=lambda x: x["repository"]),
            "queue": queue.summary(run_id),
        }

    def run_once(self, manifest_path: Path, workspace_root: Path = Path.cwd(),
                 max_candidates: int = 4, parallel: int = 2) -> dict[str, Any]:
        if not 1 <= max_candidates <= 12 or not 1 <= parallel <= 4:
            raise ValueError("max_candidates must be 1..12 and parallel must be 1..4")
        queue = SourceCaptureQueue(self.database_path)
        try:
            imported = queue.import_manifest(manifest_path, workspace_root)
            result = self._capture_cycle(queue, imported["run_id"], max_candidates, parallel)
            result["manifest"] = imported
            return result
        finally:
            queue.close()

    def run_until_drained(self, manifest_path: Path, workspace_root: Path = Path.cwd(),
                          max_candidates: int = 4, parallel: int = 2,
                          poll_seconds: float = 10.0,
                          stop_event: threading.Event | None = None) -> dict[str, Any]:
        if not 1 <= max_candidates <= 12 or not 1 <= parallel <= 4 or poll_seconds < 1:
            raise ValueError("invalid batch, parallelism or poll interval")
        stop = stop_event or threading.Event()
        queue = SourceCaptureQueue(self.database_path)
        cycles = 0
        attempted = 0
        try:
            imported = queue.import_manifest(manifest_path, workspace_root)
            run_id = imported["run_id"]
            latest: dict[str, Any] = {}
            while not stop.is_set():
                latest = self._capture_cycle(queue, run_id, max_candidates, parallel)
                cycles += 1
                attempted += latest["attempted_this_cycle"]
                status = latest["queue"]
                if status["pending"] == 0 and status["leased"] == 0:
                    break
                if latest["attempted_this_cycle"] == 0:
                    stop.wait(poll_seconds)
            return {
                "manifest": imported, "cycles": cycles, "attempted_total": attempted,
                "stopped": stop.is_set(), "queue": queue.summary(run_id),
            }
        finally:
            queue.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resumable commit-pinned source capture for immutable GitHub audit batches"
    )
    parser.add_argument("--manifest", required=True, help="Workspace-relative manifest.json path")
    parser.add_argument("--workspace", default=str(Path.cwd()))
    parser.add_argument("--database", default=str(SETTINGS.database_path))
    parser.add_argument("--snapshots", default=str(SETTINGS.snapshot_dir))
    parser.add_argument("--output", default="reports/source-capture")
    parser.add_argument("--max-candidates", type=int, default=4, help="Candidates claimed per cycle (1..12)")
    parser.add_argument("--parallel", type=int, default=2, help="Concurrent read-only inspections (1..4)")
    parser.add_argument("--max-source-files", type=int, default=30)
    parser.add_argument("--max-blob-bytes", type=int, default=250_000)
    parser.add_argument("--continuous", action="store_true", help="Continue until every candidate is captured or exhausts retries")
    parser.add_argument("--poll-seconds", type=float, default=10.0)
    args = parser.parse_args()

    worker = SourceCaptureWorker(
        database_path=Path(args.database),
        snapshot_dir=Path(args.snapshots),
        output_dir=Path(args.output),
        max_source_files=args.max_source_files,
        max_blob_bytes=args.max_blob_bytes,
    )
    if args.continuous:
        result = worker.run_until_drained(
            Path(args.manifest), Path(args.workspace), args.max_candidates,
            args.parallel, args.poll_seconds,
        )
    else:
        result = worker.run_once(
            Path(args.manifest), Path(args.workspace), args.max_candidates, args.parallel,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
