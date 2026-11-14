from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path(os.getenv("FLR_DATABASE", "data/research.sqlite3"))
    snapshot_dir: Path = Path(os.getenv("FLR_SNAPSHOT_DIR", "data/snapshots"))
    api_base: str = "https://api.github.com"
    user_agent: str = "flashloan-research-engine/0.1.0"
    request_timeout_seconds: int = 20
    max_retries: int = 4
    max_source_files: int = 80
    max_blob_bytes: int = 250_000
    github_token: str | None = os.getenv("GITHUB_TOKEN")


SETTINGS = Settings()
