#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/resume_source_capture.sh /path/to/flashloan-source-capture-pilot-43607072905.zip

Required:
  A copy of the 10-candidate pilot ZIP from GitHub Actions run 43607072905.
  GITHUB_TOKEN must contain read-only access to public repository metadata and Git objects.

Optional environment:
  SOURCE_CAPTURE_BATCH=12       Candidates claimed per cycle (1..12).
  SOURCE_CAPTURE_PARALLEL=2     Concurrent inspections (1..4).
  SOURCE_CAPTURE_POLL_SECONDS=30 Seconds between queue checks.

The script restores into dedicated paths and does not overwrite data/research.sqlite3.
EOF
}

if [[ $# -ne 1 ]]; then
  usage >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f pyproject.toml || ! -f research_runs/audit-batches/43600488013/manifest.json ]]; then
  echo "Run this script from a checkout of the canonical repository." >&2
  exit 2
fi

ZIP_PATH="$(realpath "$1")"
if [[ ! -f "$ZIP_PATH" ]]; then
  echo "Pilot artifact ZIP not found: $ZIP_PATH" >&2
  exit 2
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "GITHUB_TOKEN is required for the multi-thousand-repository run." >&2
  echo "Create a fine-grained token with read-only access to public repository contents, then export it in this WSL shell." >&2
  exit 2
fi

export FLR_DATABASE="$ROOT/data/source-capture-pilot.sqlite3"
export FLR_SNAPSHOT_DIR="$ROOT/data/source-capture-pilot-vault"

export PILOT_ZIP="$ZIP_PATH"
export PILOT_ROOT="$ROOT"

python3 - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

EXPECTED_ZIP_SHA256 = "092235cf3f11920d65ccbbe4e6412f5b325c2158c2d698f61da947767400c178"
EXPECTED_MANIFEST_SHA256 = "45014ead9e61098cef320704131752f63f2a4ebe392947bd8204fd1a34ad43fd"
RUN_ID = "43600488013"
EXPECTED_TOTAL = 7901
EXPECTED_CAPTURED = 10
root = Path(os.environ["PILOT_ROOT"]).resolve()
zip_path = Path(os.environ["PILOT_ZIP"]).resolve()
manifest_path = root / "research_runs/audit-batches/43600488013/manifest.json"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\\0" + content).hexdigest()

if sha256_file(zip_path) != EXPECTED_ZIP_SHA256:
    raise SystemExit("Pilot ZIP SHA-256 mismatch. Do not restore an unverified artifact.")
if sha256_file(manifest_path) != EXPECTED_MANIFEST_SHA256:
    raise SystemExit("Canonical manifest SHA-256 mismatch. Update the script only after verifying a new manifest.")

allowed_exact = {
    "data/research.sqlite3",
    "reports/pilot-run-summary.json",
    "reports/pilot-verification.json",
}
allowed_prefixes = ("data/snapshots/", "reports/source-capture/")
staging_parent = root / ".source-capture-restore"
staging_parent.mkdir(parents=True, exist_ok=True)

with tempfile.TemporaryDirectory(prefix="pilot-", dir=staging_parent) as temp_name:
    staging = Path(temp_name)
    with zipfile.ZipFile(zip_path, "r") as archive:
        infos = archive.infolist()
        names = set()
        for info in infos:
            name = info.filename
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                raise SystemExit(f"Unsafe ZIP member path: {name}")
            if not (name in allowed_exact or name.startswith(allowed_prefixes)):
                # Directory entries are allowed only beneath approved directories.
                if info.is_dir() and (name.startswith("data/") or name.startswith("reports/")):
                    continue
                raise SystemExit(f"Unexpected ZIP member: {name}")
            if info.is_dir():
                continue
            if name in names:
                raise SystemExit(f"Duplicate ZIP member: {name}")
            names.add(name)
            if info.external_attr >> 16 & 0o170000 == 0o120000:
                raise SystemExit(f"Symbolic links are not accepted in pilot ZIP: {name}")
            destination = staging.joinpath(*path.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as src, destination.open("wb") as dst:
                shutil.copyfileobj(src, dst)

    required = allowed_exact | {
        "data/snapshots/",
        "reports/source-capture/",
    }
    for name in allowed_exact:
        if not (staging / name).is_file():
            raise SystemExit(f"Pilot ZIP is missing {name}")
    if not any((staging / "data/snapshots").rglob("*")):
        raise SystemExit("Pilot source vault is empty.")
    if len(list((staging / "reports/source-capture" / RUN_ID).glob("*.json"))) != EXPECTED_CAPTURED:
        raise SystemExit("Pilot ZIP does not contain exactly 10 inspection reports.")

    verification = json.loads((staging / "reports/pilot-verification.json").read_text(encoding="utf-8"))
    if verification.get("status") != "bounded_real_source_capture_pilot_completed":
        raise SystemExit("Pilot verification status is not successful.")
    if verification.get("captured") != EXPECTED_CAPTURED:
        raise SystemExit("Pilot verification captured count is not 10.")
    if verification.get("candidate_code_executed") is not False:
        raise SystemExit("Unexpected candidate-code-execution flag in pilot evidence.")

    staged_db = staging / "data/research.sqlite3"
    connection = sqlite3.connect(staged_db)
    connection.row_factory = sqlite3.Row
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise SystemExit(f"Pilot SQLite integrity check failed: {integrity}")
        run = connection.execute(
            "SELECT * FROM source_capture_runs WHERE run_id=?", (RUN_ID,)
        ).fetchone()
        if run is None or run["manifest_sha256"] != EXPECTED_MANIFEST_SHA256 or run["total_candidates"] != EXPECTED_TOTAL:
            raise SystemExit("Pilot SQLite queue does not match the canonical manifest.")
        counts = {
            row["status"]: row["n"]
            for row in connection.execute(
                "SELECT status, COUNT(*) AS n FROM source_capture_items WHERE run_id=? GROUP BY status",
                (RUN_ID,),
            )
        }
        if counts != {"captured": 10, "pending": 7891}:
            raise SystemExit(f"Unexpected pilot queue states: {counts}")
        rows = connection.execute(
            "SELECT candidate_index,repository,commit_sha,tree_sha,report_path,capture_json "
            "FROM source_capture_items WHERE run_id=? AND status='captured' ORDER BY candidate_index",
            (RUN_ID,),
        ).fetchall()
    finally:
        connection.close()

    report_root = staging / "reports"
    vault_root = staging / "data/snapshots"
    reference_count = 0
    unique_blob_ids = set()
    for row in rows:
        report_path = staging / row["report_path"]
        if not report_path.is_file():
            raise SystemExit(f"Missing capture report: {row['report_path']}")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if (
            report.get("repository") != row["repository"]
            or report.get("candidate_index") != row["candidate_index"]
            or report.get("commit_sha") != row["commit_sha"]
            or report.get("tree_sha") != row["tree_sha"]
            or report.get("run_id") != RUN_ID
        ):
            raise SystemExit(f"Commit/tree/report identity mismatch for {row['repository']}")
        if report.get("candidate_code_executed") is not False:
            raise SystemExit(f"Unsafe execution flag in report for {row['repository']}")
        if report.get("tree_recovery_complete") is not True:
            raise SystemExit(f"Tree inventory was incomplete for {row['repository']}")
        for item in report.get("captured_files", []):
            relative = item.get("vault_relative_path")
            blob_sha = item.get("blob_sha")
            if not isinstance(relative, str) or not isinstance(blob_sha, str):
                raise SystemExit(f"Malformed source blob reference in {row['repository']}")
            rel = PurePosixPath(relative)
            if rel.is_absolute() or ".." in rel.parts or "\\" in relative:
                raise SystemExit(f"Unsafe source vault path: {relative}")
            blob_path = vault_root.joinpath(*rel.parts)
            if not blob_path.is_file():
                raise SystemExit(f"Missing source blob in pilot archive: {relative}")
            content = blob_path.read_bytes()
            if git_blob_sha(content) != blob_sha:
                raise SystemExit(f"Git blob SHA-1 mismatch: {row['repository']}:{item.get('path')}")
            reference_count += 1
            unique_blob_ids.add(blob_sha)

    if reference_count != 182 or len(unique_blob_ids) != 173:
        raise SystemExit(
            f"Unexpected source evidence counts: references={reference_count}, unique_blobs={len(unique_blob_ids)}"
        )

    target_db = root / "data/source-capture-pilot.sqlite3"
    target_vault = root / "data/source-capture-pilot-vault"
    target_reports = root / "reports/source-capture" / RUN_ID
    target_verification = root / "reports/source-capture-pilot-verification.json"

    if target_db.exists():
        existing = sqlite3.connect(target_db)
        try:
            existing_run = existing.execute(
                "SELECT manifest_sha256,total_candidates FROM source_capture_runs WHERE run_id=?",
                (RUN_ID,),
            ).fetchone()
        except sqlite3.Error as exc:
            raise SystemExit(f"Existing target DB is not a compatible source-capture DB: {exc}")
        finally:
            existing.close()
        if existing_run != (EXPECTED_MANIFEST_SHA256, EXPECTED_TOTAL):
            raise SystemExit(
                "A different source-capture database already exists at data/source-capture-pilot.sqlite3; "
                "move it aside manually before restoring this pilot."
            )
    else:
        target_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged_db, target_db)

    # Merge the verified pilot blobs into an isolated vault; never overwrite a
    # different blob already present in a resumed local vault.
    target_vault.mkdir(parents=True, exist_ok=True)
    for blob_sha in unique_blob_ids:
        relative = PurePosixPath(blob_sha[:2]) / blob_sha[2:]
        source = vault_root / relative
        destination = target_vault / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != source.read_bytes():
                raise SystemExit(f"Existing local vault blob differs: {blob_sha}")
        else:
            shutil.copy2(source, destination)

    target_reports.mkdir(parents=True, exist_ok=True)
    for source in (staging / "reports/source-capture" / RUN_ID).glob("*.json"):
        destination = target_reports / source.name
        if destination.exists():
            if destination.read_bytes() != source.read_bytes():
                raise SystemExit(f"Existing local report differs: {destination}")
        else:
            shutil.copy2(source, destination)

    verification_copy = staging / "reports/pilot-verification.json"
    target_verification.parent.mkdir(parents=True, exist_ok=True)
    if target_verification.exists() and target_verification.read_bytes() != verification_copy.read_bytes():
        raise SystemExit(f"Existing verification file differs: {target_verification}")
    if not target_verification.exists():
        shutil.copy2(verification_copy, target_verification)

print(json.dumps({
    "restore_status": "verified_and_restored",
    "database": str(root / "data/source-capture-pilot.sqlite3"),
    "vault": str(root / "data/source-capture-pilot-vault"),
    "reports": str(root / "reports/source-capture" / RUN_ID),
    "manifest_sha256": EXPECTED_MANIFEST_SHA256,
    "captured": 10,
    "pending": 7891,
    "source_file_references": 182,
    "unique_git_blobs": 173,
    "git_blob_sha1_verified": 182,
    "missing_or_mismatched_blobs": 0,
}, ensure_ascii=False, indent=2))
PY

python3 -m pip install -e .

export SOURCE_CAPTURE_BATCH="${SOURCE_CAPTURE_BATCH:-12}"
export SOURCE_CAPTURE_PARALLEL="${SOURCE_CAPTURE_PARALLEL:-2}"
export SOURCE_CAPTURE_POLL_SECONDS="${SOURCE_CAPTURE_POLL_SECONDS:-30}"

flashloan-source-capture-worker \
  --manifest research_runs/audit-batches/43600488013/manifest.json \
  --workspace "$ROOT" \
  --database "$FLR_DATABASE" \
  --snapshots "$FLR_SNAPSHOT_DIR" \
  --output reports/source-capture \
  --max-candidates "$SOURCE_CAPTURE_BATCH" \
  --parallel "$SOURCE_CAPTURE_PARALLEL" \
  --continuous \
  --poll-seconds "$SOURCE_CAPTURE_POLL_SECONDS"

python3 - <<'PY'
import json
import os
import sqlite3
from pathlib import Path

db = Path(os.environ["FLR_DATABASE"])
connection = sqlite3.connect(db)
try:
    rows = connection.execute(
        "SELECT status,COUNT(*) FROM source_capture_items WHERE run_id='43600488013' GROUP BY status"
    ).fetchall()
    counts = dict(rows)
finally:
    connection.close()

summary = {
    "run_id": "43600488013",
    "counts": counts,
    "total": sum(counts.values()),
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
if counts.get("pending", 0) or counts.get("leased", 0) or counts.get("failed", 0):
    raise SystemExit("Queue is not fully captured. Review failed rows; do not mark this run complete.")
PY
