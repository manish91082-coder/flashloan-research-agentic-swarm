from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import EvidenceRecord, RepositoryCandidate

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS candidates (
 full_name TEXT PRIMARY KEY, html_url TEXT NOT NULL, description TEXT,
 default_branch TEXT NOT NULL, pushed_at TEXT, archived INTEGER NOT NULL,
 stars INTEGER NOT NULL, forks INTEGER NOT NULL, discovery_query TEXT NOT NULL,
 first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS snapshots (
 repository TEXT NOT NULL, commit_sha TEXT NOT NULL, tree_sha TEXT,
 captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, tree_truncated INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(repository, commit_sha), FOREIGN KEY(repository) REFERENCES candidates(full_name)
);
CREATE TABLE IF NOT EXISTS evidence (
 id INTEGER PRIMARY KEY AUTOINCREMENT, repository TEXT NOT NULL, commit_sha TEXT NOT NULL,
 path TEXT NOT NULL, blob_sha TEXT NOT NULL, claim_type TEXT NOT NULL, claim TEXT NOT NULL,
 evidence_excerpt TEXT NOT NULL, confidence TEXT NOT NULL, acceptance_status TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(repository, commit_sha, path, blob_sha, claim)
);
CREATE TABLE IF NOT EXISTS runs (
 run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 finished_at TEXT, status TEXT NOT NULL, summary_json TEXT NOT NULL
);
"""


class ResearchStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path, timeout=15, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA busy_timeout=15000")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def upsert_candidate(self, candidate: RepositoryCandidate) -> None:
        d = candidate.to_dict()
        self.connection.execute("""INSERT INTO candidates
        (full_name,html_url,description,default_branch,pushed_at,archived,stars,forks,discovery_query)
        VALUES (:full_name,:html_url,:description,:default_branch,:pushed_at,:archived,:stars,:forks,:discovery_query)
        ON CONFLICT(full_name) DO UPDATE SET html_url=excluded.html_url, description=excluded.description,
        default_branch=excluded.default_branch, pushed_at=excluded.pushed_at, archived=excluded.archived,
        stars=excluded.stars, forks=excluded.forks, discovery_query=excluded.discovery_query,
        last_seen_at=CURRENT_TIMESTAMP""", {**d, "archived": int(d["archived"])})
        self.connection.commit()

    def save_snapshot(self, repository: str, commit_sha: str, tree_sha: str | None, truncated: bool) -> None:
        self.connection.execute("""INSERT OR REPLACE INTO snapshots(repository,commit_sha,tree_sha,tree_truncated)
        VALUES (?,?,?,?)""", (repository, commit_sha, tree_sha, int(truncated)))
        self.connection.commit()

    def save_evidence(self, record: EvidenceRecord) -> None:
        record.validate()
        self.connection.execute("""INSERT OR IGNORE INTO evidence
        (repository,commit_sha,path,blob_sha,claim_type,claim,evidence_excerpt,confidence,acceptance_status)
        VALUES (?,?,?,?,?,?,?,?,?)""", (record.repository, record.commit_sha, record.path, record.blob_sha,
        record.claim_type, record.claim, record.evidence_excerpt, record.confidence, record.acceptance_status))
        self.connection.commit()

    def list_candidates(self, limit: int = 10000) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not 1 <= limit <= 50000:
            raise ValueError("limit must be between 1 and 50000")
        rows = self.connection.execute(
            """SELECT full_name,html_url,description,default_branch,pushed_at,archived,
                      stars,forks,discovery_query,first_seen_at,last_seen_at
               FROM candidates ORDER BY stars DESC,full_name LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def counts(self) -> dict[str, int]:
        return {table: int(self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in ("candidates", "snapshots", "evidence", "runs")}


def git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def export_evidence_csv(store: ResearchStore, path: Path) -> None:
    rows = store.connection.execute("SELECT repository,commit_sha,path,blob_sha,claim_type,claim,evidence_excerpt,confidence,acceptance_status,created_at FROM evidence ORDER BY repository,commit_sha,path").fetchall()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["repository", "commit_sha", "path", "blob_sha", "claim_type", "claim", "evidence_excerpt", "confidence", "acceptance_status", "created_at"])
        writer.writerows([tuple(row) for row in rows])


class ContentAddressedVault:
    """Persist immutable source blobs under their verified Git object SHA."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, blob_sha: str, content: bytes) -> Path:
        if len(blob_sha) != 40 or any(c not in "0123456789abcdef" for c in blob_sha.lower()):
            raise ValueError("blob_sha must be a 40-character hexadecimal Git object SHA")
        actual = git_blob_sha(content)
        if actual != blob_sha:
            raise ValueError(f"blob SHA mismatch: expected {blob_sha}, got {actual}")
        target = (self.root / blob_sha[:2] / blob_sha[2:]).resolve()
        if self.root not in target.parents:
            raise ValueError("resolved blob path escaped vault root")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != content:
                raise RuntimeError("content-address collision or corrupted vault entry")
            return target
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(content)
        temporary.replace(target)
        return target
