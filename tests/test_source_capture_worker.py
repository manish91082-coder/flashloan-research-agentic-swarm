from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from flashloan_research.source_capture_worker import (
    SourceCaptureError,
    SourceCaptureQueue,
    SourceCaptureWorker,
)


def candidate(index: int, name: str, repo_id: int, families: list[str]) -> dict:
    return {
        "audit_status": "pending_commit_pinned_source_capture",
        "candidate_index": index,
        "repository": name,
        "repository_id": repo_id,
        "matched_families": families,
        "discovered_by": [{"family_id": families[0], "query": "flash loan liquidation", "page": 1}],
        "metadata": {
            "full_name": name,
            "html_url": f"https://github.com/{name}",
            "default_branch": "main",
            "description": "flash loan liquidation research candidate",
            "pushed_at": "2026-11-14T00:00:00Z",
            "archived": False,
            "stars": 1,
            "forks": 0,
            "discovery_query": "flash loan liquidation",
        },
    }


def write_manifest(root: Path) -> Path:
    batch_dir = root / "research_runs" / "audit-batches" / "test-run"
    batch_dir.mkdir(parents=True)
    rows = [
        candidate(0, "sample-lab/adjacent-repo", 101, ["dex_and_liquidity"]),
        candidate(1, "sample-lab/direct-liquidator", 102, ["flash_loan_liquidation_combo"]),
        candidate(2, "sample-lab/provider-repo", 103, ["flash_loan_provider_apis"]),
    ]
    # Empty repositories can have a null discovery-time default branch. The worker
    # refetches live repository metadata before resolving the branch for inspection.
    rows[0]["metadata"]["default_branch"] = None
    batches = []
    for number, chunk in enumerate((rows[:2], rows[2:]), start=1):
        name = f"batch-{number:04d}.jsonl"
        path = batch_dir / name
        raw = "".join(json.dumps(row, sort_keys=True) + "\n" for row in chunk).encode()
        path.write_bytes(raw)
        batches.append({
            "batch_id": f"test-run-b{number:04d}",
            "candidate_count": len(chunk),
            "first_candidate_index": chunk[0]["candidate_index"],
            "last_candidate_index": chunk[-1]["candidate_index"],
            "path": str(path.relative_to(root)).replace("\\", "/"),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "status": "pending",
        })
    manifest = {
        "schema_version": "1.0",
        "record_type": "resumable_discovery_candidate_batch_manifest",
        "run_id": "test-run",
        "batch_count": len(batches),
        "batch_size": 2,
        "candidate_count": len(rows),
        "batches": batches,
        "status": "candidate_metadata_imported_audit_pending",
    }
    manifest_path = batch_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


class FakePipeline:
    def inspect(self, repository, store):
        return {
            "repository": repository,
            "commit_sha": "a" * 40,
            "tree_sha": "b" * 40,
            "source_files_captured": 1,
            "source_capture_complete_within_configured_scope": True,
            "signals": [{"signal": "executeOperation", "path": "src/Bot.sol", "line": 10}],
            "captured_files": [{"path": "src/Bot.sol", "blob_sha": "c" * 40}],
            "limitations": ["No candidate code was executed."],
        }


class SourceCaptureWorkerTests(unittest.TestCase):
    def test_import_capture_and_resume_are_idempotent_and_priority_ordered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = write_manifest(root)
            captured_order: list[str] = []

            class RecordingPipeline(FakePipeline):
                def inspect(self, repository, store):
                    captured_order.append(repository)
                    return super().inspect(repository, store)

            worker = SourceCaptureWorker(
                database_path=root / "state.sqlite3",
                snapshot_dir=root / "snapshots",
                output_dir=root / "reports",
                pipeline_factory=RecordingPipeline,
            )
            first = worker.run_once(manifest, root, max_candidates=1, parallel=1)
            self.assertEqual(first["attempted_this_cycle"], 1)
            self.assertEqual(first["queue"]["captured"], 1)
            self.assertEqual(captured_order, ["sample-lab/direct-liquidator"])

            second = worker.run_once(manifest, root, max_candidates=2, parallel=1)
            self.assertEqual(second["attempted_this_cycle"], 2)
            self.assertEqual(second["queue"]["captured"], 3)
            self.assertEqual(second["queue"]["pending"], 0)
            third = worker.run_once(manifest, root, max_candidates=2, parallel=1)
            self.assertEqual(third["attempted_this_cycle"], 0)
            self.assertEqual(third["queue"]["captured"], 3)
            self.assertEqual(len(captured_order), 3)

            queue = SourceCaptureQueue(root / "state.sqlite3")
            try:
                rows = queue.connection.execute(
                    "SELECT repository,status,commit_sha,tree_sha,report_path FROM source_capture_items ORDER BY candidate_index"
                ).fetchall()
                self.assertEqual(len(rows), 3)
                self.assertTrue(all(row["status"] == "captured" for row in rows))
                self.assertTrue(all(row["commit_sha"] == "a" * 40 for row in rows))
                self.assertTrue(all(Path(row["report_path"]).is_file() for row in rows))
            finally:
                queue.close()

    def test_capture_cycle_emits_batch_start_and_per_candidate_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = write_manifest(root)
            worker = SourceCaptureWorker(
                database_path=root / "state.sqlite3",
                snapshot_dir=root / "snapshots",
                output_dir=root / "reports",
                pipeline_factory=FakePipeline,
            )
            output = io.StringIO()
            with redirect_stdout(output):
                result = worker.run_once(manifest, root, max_candidates=2, parallel=2)
            events = [json.loads(line) for line in output.getvalue().splitlines() if line.strip()]
            self.assertEqual(events[0]["event"], "source_capture_batch_started")
            finished = [event for event in events if event["event"] == "source_capture_candidate_finished"]
            self.assertEqual(len(finished), 2)
            self.assertTrue(all(event["status"] == "captured" for event in finished))
            self.assertTrue(all(event["completed_in_batch"] >= 1 for event in finished))
            self.assertEqual(result["attempted_this_cycle"], 2)

    def test_transient_failure_is_retryable_and_then_captured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = write_manifest(root)
            attempts: dict[str, int] = {}

            class FlakyPipeline(FakePipeline):
                def inspect(self, repository, store):
                    attempts[repository] = attempts.get(repository, 0) + 1
                    if repository == "sample-lab/direct-liquidator" and attempts[repository] == 1:
                        raise RuntimeError("temporary API failure")
                    return super().inspect(repository, store)

            worker = SourceCaptureWorker(
                database_path=root / "state.sqlite3",
                snapshot_dir=root / "snapshots",
                output_dir=root / "reports",
                pipeline_factory=FlakyPipeline,
            )
            first = worker.run_once(manifest, root, max_candidates=1, parallel=1)
            self.assertEqual(first["results"][0]["status"], "pending")
            self.assertEqual(first["queue"]["pending"], 3)

            second = worker.run_once(manifest, root, max_candidates=1, parallel=1)
            self.assertEqual(second["results"][0]["status"], "captured")
            self.assertEqual(second["queue"]["captured"], 1)
            self.assertEqual(attempts["sample-lab/direct-liquidator"], 2)


    def test_expired_lease_is_reclaimed_after_worker_interruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = write_manifest(root)
            queue = SourceCaptureQueue(root / "state.sqlite3")
            try:
                queue.import_manifest(manifest, root)
                first = queue.claim_ready("test-run", "worker-that-crashed", 1, lease_seconds=60)
                self.assertEqual(len(first), 1)
                repository = first[0]["repository"]
                queue.connection.execute(
                    "UPDATE source_capture_items SET lease_expires_at='2000-01-01T00:00:00+00:00' WHERE run_id=? AND repository=?",
                    ("test-run", repository),
                )
                queue.connection.commit()

                resumed = queue.claim_ready("test-run", "replacement-worker", 1, lease_seconds=60)
                self.assertEqual(len(resumed), 1)
                self.assertEqual(resumed[0]["repository"], repository)
                self.assertEqual(resumed[0]["attempts"], 2)
                self.assertEqual(resumed[0]["lease_owner"], "replacement-worker")
            finally:
                queue.close()


    def test_empty_repository_failure_is_terminal_without_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = write_manifest(root)
            queue = SourceCaptureQueue(root / "state.sqlite3")
            try:
                queue.import_manifest(manifest, root)
                claimed = queue.claim_ready("test-run", "empty-repo-worker", 1, lease_seconds=60)
                self.assertEqual(len(claimed), 1)
                repository = claimed[0]["repository"]
                status = queue.fail(
                    "test-run", repository, "empty-repo-worker",
                    'GitHubAPIError: GitHub API HTTP 409: {"message":"Git Repository is empty."}',
                    retryable=False,
                )
                self.assertEqual(status, "failed")
                row = queue.connection.execute(
                    "SELECT attempts,status,error FROM source_capture_items WHERE run_id=? AND repository=?",
                    ("test-run", repository),
                ).fetchone()
                self.assertEqual(row["attempts"], 1)
                self.assertEqual(row["status"], "failed")
                self.assertIn("Git Repository is empty", row["error"])
            finally:
                queue.close()

    def test_batch_hash_mismatch_is_rejected_before_queue_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = write_manifest(root)
            batch = root / "research_runs" / "audit-batches" / "test-run" / "batch-0001.jsonl"
            batch.write_text(batch.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            worker = SourceCaptureWorker(
                database_path=root / "state.sqlite3",
                snapshot_dir=root / "snapshots",
                output_dir=root / "reports",
                pipeline_factory=FakePipeline,
            )
            with self.assertRaises(SourceCaptureError):
                worker.run_once(manifest, root, max_candidates=1, parallel=1)
            queue = SourceCaptureQueue(root / "state.sqlite3")
            try:
                self.assertEqual(
                    queue.connection.execute("SELECT COUNT(*) FROM source_capture_items").fetchone()[0],
                    0,
                )
            finally:
                queue.close()


if __name__ == "__main__":
    unittest.main()
