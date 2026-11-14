from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path

from .config import SETTINGS
from .mission_graph import run_mission_graph
from .mission_queue import MissionQueue


def run_pending_once(database_path: Path | None = None) -> int:
    db_path = Path(database_path or SETTINGS.database_path)
    queue = MissionQueue(db_path)
    try:
        pending = queue.list_by_status("queued", limit=10)
        resumable = queue.list_by_status("running", limit=10)
    finally:
        queue.close()
    missions = {x["mission_id"]: x for x in (pending + resumable)}
    processed = 0
    for mission_id in missions:
        try:
            run_mission_graph(mission_id, database_path=db_path)
        except Exception as exc:
            queue = MissionQueue(db_path)
            try:
                record = queue.get(mission_id)
                if record and record["status"] not in {"completed", "blocked"}:
                    queue.set_status(
                        mission_id, "blocked",
                        f"Mission runtime stopped: {type(exc).__name__}: {str(exc)[:1500]}",
                    )
            finally:
                queue.close()
        processed += 1
    return processed


def worker_loop(database_path: Path | None = None, poll_seconds: float = 3.0,
                stop_event: threading.Event | None = None) -> None:
    stop = stop_event or threading.Event()
    while not stop.is_set():
        run_pending_once(database_path)
        stop.wait(poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Durable form-driven research mission worker")
    parser.add_argument("--database", default=str(SETTINGS.database_path))
    parser.add_argument("--once", action="store_true", help="Process queued/resumable missions once and exit")
    parser.add_argument("--poll-seconds", type=float, default=3.0)
    args = parser.parse_args()
    db_path = Path(args.database)
    if args.once:
        print(f"Processed missions: {run_pending_once(db_path)}")
        return
    print(f"Mission worker active. Database: {db_path}")
    print("Public-source research only. Candidate code execution and live transactions are disabled.")
    try:
        worker_loop(db_path, max(1.0, args.poll_seconds))
    except KeyboardInterrupt:
        print("Mission worker stopped. Persisted task leases/checkpoints can be resumed.")


if __name__ == "__main__":
    main()
