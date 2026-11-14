from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterator

from .models import RepositoryCandidate
from .storage import ResearchStore


class DiscoveryImportError(RuntimeError):
    pass


IMPORT_SCHEMA = """
CREATE TABLE IF NOT EXISTS discovery_import_runs (
 run_id TEXT PRIMARY KEY,
 report_path TEXT NOT NULL,
 report_sha256 TEXT NOT NULL,
 taxonomy_version TEXT NOT NULL,
 total_candidates INTEGER NOT NULL,
 last_candidate_index INTEGER NOT NULL DEFAULT -1,
 imported_candidate_count INTEGER NOT NULL DEFAULT 0,
 status TEXT NOT NULL CHECK(status IN ('running','paused','completed','failed')),
 error TEXT,
 updated_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS discovery_candidate_provenance (
 run_id TEXT NOT NULL,
 repository TEXT NOT NULL,
 repository_id INTEGER,
 metadata_json TEXT NOT NULL,
 matched_families_json TEXT NOT NULL,
 discovered_by_json TEXT NOT NULL,
 candidate_index INTEGER NOT NULL,
 PRIMARY KEY(run_id, repository),
 FOREIGN KEY(run_id) REFERENCES discovery_import_runs(run_id),
 FOREIGN KEY(repository) REFERENCES candidates(full_name)
);
CREATE INDEX IF NOT EXISTS idx_discovery_provenance_repository
 ON discovery_candidate_provenance(repository);
"""


def _report_metadata(path: Path) -> tuple[str, int]:
    taxonomy_version: str | None = None
    total_candidates: int | None = None
    found_array = False
    with path.open("r", encoding="utf-8") as handle:
        # Discovery reports are written with sort_keys=True, so "candidates"
        # sorts before "taxonomy_version" and "unique_candidate_count".
        # Scan the file line-by-line and keep memory bounded; do not stop at
        # the candidates key before the metadata keys have been observed.
        for line in handle:
            if line.startswith('  "taxonomy_version":'):
                value = line.split(":", 1)[1].strip().rstrip(",")
                taxonomy_version = json.loads(value)
            elif line.startswith('  "unique_candidate_count":'):
                value = line.split(":", 1)[1].strip().rstrip(",")
                total_candidates = json.loads(value)
            elif line.startswith('  "candidates":'):
                if "[" not in line:
                    raise DiscoveryImportError("candidates must be a JSON array on its key line")
                found_array = True
    if not found_array:
        raise DiscoveryImportError("report is missing the top-level candidates array")
    if not isinstance(taxonomy_version, str) or not taxonomy_version:
        raise DiscoveryImportError("report is missing taxonomy_version")
    if isinstance(total_candidates, bool) or not isinstance(total_candidates, int) or total_candidates < 0:
        raise DiscoveryImportError("report is missing a valid unique_candidate_count")
    return taxonomy_version, total_candidates


def _iter_candidate_objects(path: Path) -> Iterator[dict[str, Any]]:
    """Stream the pretty-printed top-level candidates array one object at a time.
 
    The report writer uses JSON indentation. This parser tracks object depth and
    quoted-string escapes, keeping memory bounded to one candidate object.
    """
    with path.open("r", encoding="utf-8") as handle:
        found = False
        for line in handle:
            stripped = line.lstrip()
            if stripped.startswith('"candidates"'):
                bracket = line.find("[")
                if bracket < 0:
                    raise DiscoveryImportError("candidates array opening bracket is missing")
                initial = line[bracket + 1:]
                found = True
                break
        if not found:
            raise DiscoveryImportError("report is missing candidates array")

        depth = 0
        in_string = False
        escaped = False
        object_chars: list[str] = []
        chunk = initial
        while True:
            for char in chunk:
                if depth == 0:
                    if char.isspace() or char == ",":
                        continue
                    if char == "]":
                        return
                    if char != "{":
                        raise DiscoveryImportError(f"unexpected character in candidates array: {char!r}")
                    depth = 1
                    object_chars = [char]
                    in_string = False
                    escaped = False
                    continue

                object_chars.append(char)
                if in_string:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == '"':
                        in_string = False
                else:
                    if char == '"':
                        in_string = True
                    elif char == "{":
                        depth += 1
                    elif char == "}":
                        depth -= 1
                        if depth == 0:
                            try:
                                item = json.loads("".join(object_chars))
                            except json.JSONDecodeError as exc:
                                raise DiscoveryImportError(f"invalid candidate object: {exc}") from exc
                            if not isinstance(item, dict):
                                raise DiscoveryImportError("candidate array entry must be an object")
                            yield item
                            object_chars = []
            chunk = handle.read(65536)
            if not chunk:
                if depth != 0:
                    raise DiscoveryImportError("unexpected end of file inside candidate object")
                raise DiscoveryImportError("candidate array ended without a closing bracket")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _candidate_from_report(item: dict[str, Any]) -> tuple[RepositoryCandidate, int | None, list[str], list[dict[str, Any]]]:
    metadata = item.get("metadata")
    repository = item.get("repository")
    if not isinstance(metadata, dict) or not isinstance(repository, str) or repository.count("/") != 1:
        raise DiscoveryImportError("candidate entry is missing canonical repository or metadata")
    if metadata.get("full_name") != repository:
        raise DiscoveryImportError(f"candidate identity mismatch for {repository}")
    query = metadata.get("discovery_query", "")
    candidate = RepositoryCandidate.from_api(metadata, query if isinstance(query, str) else "")
    repo_id = item.get("repository_id")
    if isinstance(repo_id, bool) or (repo_id is not None and not isinstance(repo_id, int)):
        raise DiscoveryImportError(f"invalid repository_id for {repository}")
    families = item.get("matched_families", [])
    discovered_by = item.get("discovered_by", [])
    if not isinstance(families, list) or any(not isinstance(x, str) for x in families):
        raise DiscoveryImportError(f"invalid matched_families for {repository}")
    if not isinstance(discovered_by, list) or any(not isinstance(x, dict) for x in discovered_by):
        raise DiscoveryImportError(f"invalid discovered_by provenance for {repository}")
    return candidate, repo_id, families, discovered_by


def _ensure_schema(store: ResearchStore) -> None:
    store.connection.executescript(IMPORT_SCHEMA)
    columns = {row[1] for row in store.connection.execute("PRAGMA table_info(discovery_candidate_provenance)")}
    if "metadata_json" not in columns:
        store.connection.execute("ALTER TABLE discovery_candidate_provenance ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'")
    store.connection.commit()


def import_discovery_report(path: Path, run_id: str, store: ResearchStore,
                            batch_size: int = 200, max_batches: int | None = None) -> dict[str, Any]:
    """Idempotently import candidate metadata/provenance with durable batch checkpoints."""
    path = Path(path).resolve()
    if not path.is_file():
        raise DiscoveryImportError(f"discovery report does not exist: {path}")
    if not isinstance(run_id, str) or not run_id.strip() or len(run_id) > 200:
        raise DiscoveryImportError("run_id must be a non-empty stable identifier")
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or not 1 <= batch_size <= 2000:
        raise DiscoveryImportError("batch_size must be between 1 and 2000")
    if max_batches is not None and (isinstance(max_batches, bool) or not isinstance(max_batches, int) or max_batches < 1):
        raise DiscoveryImportError("max_batches must be a positive integer when supplied")

    taxonomy_version, expected_count = _report_metadata(path)
    report_sha = _sha256_file(path)
    connection = store.connection
    _ensure_schema(store)
    existing = connection.execute("SELECT * FROM discovery_import_runs WHERE run_id=?", (run_id,)).fetchone()
    if existing:
        if existing["report_sha256"] != report_sha:
            raise DiscoveryImportError("run_id already exists for a different report SHA-256; choose a new run_id")
        if existing["taxonomy_version"] != taxonomy_version or existing["total_candidates"] != expected_count:
            raise DiscoveryImportError("report metadata differs from the saved import checkpoint")
        last_index = int(existing["last_candidate_index"])
    else:
        connection.execute(
            "INSERT INTO discovery_import_runs(run_id,report_path,report_sha256,taxonomy_version,total_candidates,status) VALUES(?,?,?,?,?,'running')",
            (run_id, str(path), report_sha, taxonomy_version, expected_count),
        )
        connection.commit()
        last_index = -1
    connection.execute("UPDATE discovery_import_runs SET status='running',error=NULL,updated_at_utc=CURRENT_TIMESTAMP WHERE run_id=?", (run_id,))
    connection.commit()

    batch: list[tuple[int, dict[str, Any]]] = []
    parsed = 0
    processed_batches = 0
    highest_index = last_index

    def persist_batch(entries: list[tuple[int, dict[str, Any]]]) -> None:
        if not entries:
            return
        normalized = []
        for candidate_index, item in entries:
            candidate, repo_id, families, discovered_by = _candidate_from_report(item)
            value = candidate.to_dict()
            normalized.append((candidate_index, value, repo_id, families, discovered_by))
        connection.execute("BEGIN IMMEDIATE")
        try:
            for candidate_index, value, repo_id, families, discovered_by in normalized:
                connection.execute("""
                    INSERT INTO candidates
                    (full_name,html_url,description,default_branch,pushed_at,archived,stars,forks,discovery_query)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(full_name) DO UPDATE SET
                      html_url=excluded.html_url,description=excluded.description,
                      default_branch=excluded.default_branch,pushed_at=excluded.pushed_at,
                      archived=excluded.archived,stars=excluded.stars,forks=excluded.forks,
                      discovery_query=excluded.discovery_query,last_seen_at=CURRENT_TIMESTAMP
                """, (value["full_name"],value["html_url"],value["description"],value["default_branch"],
                      value["pushed_at"],int(value["archived"]),value["stars"],value["forks"],value["discovery_query"]))
                connection.execute("""
                    INSERT INTO discovery_candidate_provenance
                    (run_id,repository,repository_id,metadata_json,matched_families_json,discovered_by_json,candidate_index)
                    VALUES (?,?,?,?,?,?,?)
                    ON CONFLICT(run_id,repository) DO UPDATE SET
                      repository_id=excluded.repository_id,
                      metadata_json=excluded.metadata_json,
                      matched_families_json=excluded.matched_families_json,
                      discovered_by_json=excluded.discovered_by_json,
                      candidate_index=excluded.candidate_index
                """, (run_id,value["full_name"],repo_id,json.dumps(value,ensure_ascii=False,sort_keys=True),
                      json.dumps(families,sort_keys=True),json.dumps(discovered_by,sort_keys=True),candidate_index))
            last = entries[-1][0]
            count = connection.execute("SELECT COUNT(*) FROM discovery_candidate_provenance WHERE run_id=?", (run_id,)).fetchone()[0]
            connection.execute("UPDATE discovery_import_runs SET last_candidate_index=?,imported_candidate_count=?,status='running',updated_at_utc=CURRENT_TIMESTAMP WHERE run_id=?",
                               (last,count,run_id))
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    try:
        for index, item in enumerate(_iter_candidate_objects(path)):
            parsed = index + 1
            if index <= last_index:
                continue
            batch.append((index,item))
            if len(batch) >= batch_size:
                persist_batch(batch)
                highest_index = batch[-1][0]
                batch.clear()
                processed_batches += 1
                if max_batches is not None and processed_batches >= max_batches:
                    connection.execute("UPDATE discovery_import_runs SET status='paused',updated_at_utc=CURRENT_TIMESTAMP WHERE run_id=?", (run_id,))
                    connection.commit()
                    count = connection.execute("SELECT imported_candidate_count FROM discovery_import_runs WHERE run_id=?",(run_id,)).fetchone()[0]
                    return {"run_id":run_id,"status":"paused","report_sha256":report_sha,"taxonomy_version":taxonomy_version,
                            "expected_candidates":expected_count,"imported_candidates":count,"last_candidate_index":highest_index,
                            "batch_size":batch_size,"batches_this_invocation":processed_batches,"resume_with_same_run_id":True}
        if batch:
            persist_batch(batch)
            highest_index = batch[-1][0]
            processed_batches += 1
        if parsed != expected_count:
            raise DiscoveryImportError(f"report candidate count mismatch: parsed {parsed}, metadata says {expected_count}")
        count = int(connection.execute("SELECT COUNT(*) FROM discovery_candidate_provenance WHERE run_id=?",(run_id,)).fetchone()[0])
        if count != expected_count:
            raise DiscoveryImportError(f"imported provenance count mismatch: imported {count}, expected {expected_count}")
        connection.execute("UPDATE discovery_import_runs SET status='completed',last_candidate_index=?,imported_candidate_count=?,error=NULL,updated_at_utc=CURRENT_TIMESTAMP WHERE run_id=?",
                           (expected_count-1,count,run_id))
        connection.commit()
        return {"run_id":run_id,"status":"completed","report_sha256":report_sha,"taxonomy_version":taxonomy_version,
                "expected_candidates":expected_count,"imported_candidates":count,"last_candidate_index":expected_count-1,
                "batch_size":batch_size,"batches_this_invocation":processed_batches,"resumed_from_index":last_index+1}
    except Exception as exc:
        connection.execute("UPDATE discovery_import_runs SET status='failed',error=?,updated_at_utc=CURRENT_TIMESTAMP WHERE run_id=?",
                           (f"{type(exc).__name__}: {str(exc)}"[:2000],run_id))
        connection.commit()
        raise

def export_discovery_batches(store: ResearchStore, run_id: str, output_dir: Path,
                             batch_size: int = 100, source_report_path: str | None = None) -> dict[str, Any]:
    """Export immutable per-run candidate metadata into hashed, bounded JSONL batches."""
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or not 1 <= batch_size <= 1000:
        raise DiscoveryImportError("batch_size must be between 1 and 1000")
    _ensure_schema(store)
    connection = store.connection
    run = connection.execute("SELECT * FROM discovery_import_runs WHERE run_id=?", (run_id,)).fetchone()
    if run is None:
        raise DiscoveryImportError(f"unknown discovery import run: {run_id}")
    if run["status"] != "completed":
        raise DiscoveryImportError(f"discovery import must be completed before export; status={run['status']}")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cursor = connection.execute("""
        SELECT repository,repository_id,metadata_json,matched_families_json,discovered_by_json,candidate_index
        FROM discovery_candidate_provenance WHERE run_id=? ORDER BY candidate_index
    """, (run_id,))
    batches: list[dict[str, Any]] = []
    total = 0
    batch_number = 0
    while True:
        records = cursor.fetchmany(batch_size)
        if not records:
            break
        batch_number += 1
        filename = f"batch-{batch_number:04d}.jsonl"
        target = output_dir / filename
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            for row in records:
                metadata = json.loads(row["metadata_json"])
                if metadata.get("full_name") != row["repository"]:
                    raise DiscoveryImportError(f"stored candidate metadata identity mismatch: {row['repository']}")
                record = {
                    "candidate_index": row["candidate_index"],
                    "repository": row["repository"],
                    "repository_id": row["repository_id"],
                    "metadata": metadata,
                    "matched_families": json.loads(row["matched_families_json"]),
                    "discovered_by": json.loads(row["discovered_by_json"]),
                    "audit_status": "pending_commit_pinned_source_capture",
                }
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                total += 1
        batch_sha = _sha256_file(target)
        batches.append({
            "batch_id": f"{run_id}-b{batch_number:04d}",
            "path": str(target.as_posix()),
            "sha256": batch_sha,
            "candidate_count": len(records),
            "first_candidate_index": records[0]["candidate_index"],
            "last_candidate_index": records[-1]["candidate_index"],
            "status": "pending",
        })
    if total != int(run["total_candidates"]) or total != int(run["imported_candidate_count"]):
        raise DiscoveryImportError(
            f"exported candidate count mismatch: exported={total}, report={run['total_candidates']}, imported={run['imported_candidate_count']}"
        )
    manifest = {
        "schema_version": "1.0",
        "record_type": "resumable_discovery_candidate_batch_manifest",
        "run_id": run_id,
        "source_report_path": source_report_path or run["report_path"],
        "source_report_sha256": run["report_sha256"],
        "taxonomy_version": run["taxonomy_version"],
        "candidate_count": total,
        "batch_size": batch_size,
        "batch_count": len(batches),
        "status": "candidate_metadata_imported_audit_pending",
        "safety": {
            "candidate_code_executed": False,
            "wallet_or_transaction_access": False,
            "source_audit_completed": False,
        },
        "batches": batches,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {
        "run_id": run_id,
        "status": manifest["status"],
        "candidate_count": total,
        "batch_count": batch_number,
        "batch_size": batch_size,
        "manifest": str(manifest_path.as_posix()),
    }
