from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
from pathlib import Path, PurePosixPath


RUN_ID = "43600488013"
MANIFEST_SHA256 = "45014ead9e61098cef320704131752f63f2a4ebe392947bd8204fd1a34ad43fd"
TOTAL_CANDIDATES = 7901


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\\0" + content).hexdigest()


def safe_child(root: Path, relative: str) -> Path:
    rel = PurePosixPath(relative)
    if rel.is_absolute() or not rel.parts or any(part in {"", ".", ".."} for part in rel.parts):
        raise ValueError(f"unsafe artifact-relative path: {relative}")
    candidate = (root / Path(*rel.parts)).resolve()
    if root.resolve() not in candidate.parents:
        raise ValueError(f"artifact path escapes root: {relative}")
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and restore a source-capture checkpoint artifact.")
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()

    artifact = args.artifact_root.resolve()
    workspace = args.workspace.resolve()
    manifest_path = workspace / "research_runs/audit-batches/43600488013/manifest.json"
    if not manifest_path.is_file() or sha256_file(manifest_path) != MANIFEST_SHA256:
        raise SystemExit("Canonical discovery manifest is missing or its SHA-256 changed.")

    # The first checkpoint is the verified pilot artifact; later checkpoints use
    # the dedicated persistent paths produced by this workflow.
    pilot_db = artifact / "data/research.sqlite3"
    if pilot_db.is_file():
        source_db = pilot_db
        source_vault = artifact / "data/snapshots"
    else:
        source_db = artifact / "data/source-capture-pilot.sqlite3"
        source_vault = artifact / "data/source-capture-pilot-vault"
    source_reports = artifact / "reports/source-capture" / RUN_ID
    if not source_db.is_file() or not source_vault.is_dir() or not source_reports.is_dir():
        raise SystemExit("Checkpoint artifact is missing the database, source vault or report directory.")

    connection = sqlite3.connect(source_db)
    connection.row_factory = sqlite3.Row
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise SystemExit(f"SQLite integrity_check failed: {integrity}")
        run = connection.execute(
            "SELECT manifest_sha256,total_candidates FROM source_capture_runs WHERE run_id=?", (RUN_ID,)
        ).fetchone()
        if run is None or run["manifest_sha256"] != MANIFEST_SHA256 or run["total_candidates"] != TOTAL_CANDIDATES:
            raise SystemExit("SQLite queue does not match the immutable 7,901-candidate manifest.")
        rows = connection.execute(
            "SELECT candidate_index,repository,status,commit_sha,tree_sha FROM source_capture_items "
            "WHERE run_id=? ORDER BY candidate_index", (RUN_ID,)
        ).fetchall()
        counts = {row["status"]: row["n"] for row in connection.execute(
            "SELECT status,COUNT(*) AS n FROM source_capture_items WHERE run_id=? GROUP BY status", (RUN_ID,)
        )}
    finally:
        connection.close()

    if len(rows) != TOTAL_CANDIDATES or sum(counts.values()) != TOTAL_CANDIDATES:
        raise SystemExit(f"Queue row count mismatch: rows={len(rows)}, states={counts}")

    checked_reports = 0
    checked_blob_references = 0
    checked_unique_blobs: set[str] = set()
    for row in rows:
        if row["status"] != "captured":
            continue
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", row["repository"].replace("/", "__"))
        report_path = source_reports / f"{row['candidate_index']:05d}-{safe_name}.json"
        if not report_path.is_file():
            raise SystemExit(f"Captured repository report missing: {row['repository']}")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if (report.get("repository") != row["repository"]
                or report.get("candidate_index") != row["candidate_index"]
                or report.get("run_id") != RUN_ID
                or report.get("commit_sha") != row["commit_sha"]
                or report.get("tree_sha") != row["tree_sha"]):
            raise SystemExit(f"Commit/tree/report identity mismatch: {row['repository']}")
        if report.get("candidate_code_executed") is not False or report.get("tree_recovery_complete") is not True:
            raise SystemExit(f"Safety or tree-recovery invariant failed: {row['repository']}")
        for item in report.get("captured_files", []):
            blob_sha = item.get("blob_sha")
            relative = item.get("vault_relative_path")
            if not isinstance(blob_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", blob_sha):
                raise SystemExit(f"Invalid Git blob SHA: {row['repository']}")
            if not isinstance(relative, str):
                raise SystemExit(f"Missing vault path: {row['repository']}")
            blob_path = safe_child(source_vault, relative)
            if not blob_path.is_file() or blob_path.is_symlink():
                raise SystemExit(f"Missing or unsafe source blob: {row['repository']}:{item.get('path')}")
            if git_blob_sha(blob_path.read_bytes()) != blob_sha:
                raise SystemExit(f"Git blob SHA-1 mismatch: {row['repository']}:{item.get('path')}")
            checked_blob_references += 1
            checked_unique_blobs.add(blob_sha)
        checked_reports += 1

    target_db = workspace / "data/source-capture-pilot.sqlite3"
    target_vault = workspace / "data/source-capture-pilot-vault"
    target_reports = workspace / "reports/source-capture" / RUN_ID
    if target_db.exists():
        raise SystemExit("Refusing to overwrite an existing source-capture database in the runner workspace.")
    if target_vault.exists() and any(target_vault.rglob("*")):
        raise SystemExit("Refusing to merge into a non-empty source-capture vault.")
    target_db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_db, target_db)
    shutil.copytree(source_vault, target_vault, dirs_exist_ok=True)
    target_reports.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_reports, target_reports, dirs_exist_ok=True)

    result = {
        "status": "checkpoint_restored_and_verified",
        "run_id": RUN_ID,
        "manifest_sha256": MANIFEST_SHA256,
        "total": TOTAL_CANDIDATES,
        "queue": {key: counts.get(key, 0) for key in ("pending", "leased", "captured", "failed")},
        "reports_verified": checked_reports,
        "git_blob_references_verified": checked_blob_references,
        "unique_git_blobs_verified": len(checked_unique_blobs),
        "candidate_code_executed": False,
    }
    output = workspace / "reports/source-capture-restore-verification.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
