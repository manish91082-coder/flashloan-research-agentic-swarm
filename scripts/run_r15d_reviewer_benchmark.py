from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MISSION_ID = "flashloan-agent-form-pilot-20261116-r15c"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    ).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_model_output(exchange: dict[str, Any]) -> dict[str, Any] | None:
    raw = exchange.get("response_raw")
    if not isinstance(raw, str):
        return None
    try:
        envelope = json.loads(raw)
        content = envelope["choices"][0]["message"]["content"]
        if isinstance(content, dict):
            return content
        if isinstance(content, str):
            return json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None
    return None


def verify_frozen_packet(workspace: Path, eval_root: Path, manifest: dict[str, Any],
                         source_vault: Path) -> tuple[Path, Path]:
    mission_root = eval_root / "research_runs" / "mission-pilots" / MISSION_ID / MISSION_ID
    db_source = eval_root / "data" / "agentic-mission-pilot-20261116-r15c.sqlite3"
    if not db_source.is_file() or not mission_root.is_dir():
        raise SystemExit("Frozen R15C evaluation artifact is missing its database or mission reports.")
    if sha256_file(db_source) != manifest["mission"]["sqlite_sha256"]:
        raise SystemExit("R15C SQLite SHA-256 does not match the frozen manifest.")

    for item in manifest["inspections"]:
        name = item["repo"].replace("/", "__") + ".json"
        path = mission_root / "inspections" / name
        if not path.is_file() or sha256_file(path) != item["inspection_sha256"]:
            raise SystemExit(f"Inspection report fingerprint mismatch: {item['repo']}")
        inspection = json.loads(path.read_text(encoding="utf-8"))
        if inspection.get("commit_sha") != item["commit"] or inspection.get("tree_sha") != item["tree"]:
            raise SystemExit(f"Source pin mismatch: {item['repo']}")
        for captured in inspection.get("captured_files", []):
            blob_sha = captured.get("blob_sha")
            relative = captured.get("vault_relative_path")
            if not isinstance(blob_sha, str) or not isinstance(relative, str):
                raise SystemExit(f"Malformed source blob reference: {item['repo']}")
            blob = (source_vault / relative).resolve()
            if source_vault.resolve() not in blob.parents or not blob.is_file() or blob.is_symlink():
                raise SystemExit(f"Missing/unsafe pinned source blob: {item['repo']}:{captured.get('path')}")
            if git_blob_sha(blob.read_bytes()) != blob_sha:
                raise SystemExit(f"Git blob mismatch: {item['repo']}:{captured.get('path')}")

    for item in manifest["specialist_reports"]:
        repo_slug = item["repo"].replace("/", "__")
        path = mission_root / "specialists" / f"{repo_slug}__{item['task']}.json"
        if not path.is_file() or sha256_file(path) != item["sha256"]:
            raise SystemExit(f"Specialist report fingerprint mismatch: {item['repo']}:{item['task']}")

    for item in manifest["evidence_reports"]:
        repo_slug = item["repo"].replace("/", "__")
        path = mission_root / "evidence-validation" / f"{repo_slug}.json"
        if not path.is_file() or sha256_file(path) != item["sha256"]:
            raise SystemExit(f"Evidence report fingerprint mismatch: {item['repo']}")

    return mission_root, db_source


def create_isolated_benchmark_state(db_source: Path, db_target: Path, mission_root: Path,
                                    artifact_root: Path) -> None:
    if db_target.exists() or artifact_root.exists():
        raise SystemExit("Refusing to overwrite an existing R15D benchmark database or artifact root.")
    db_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_source, db_target)
    target_mission = artifact_root / MISSION_ID
    target_mission.mkdir(parents=True, exist_ok=False)
    shutil.copytree(mission_root / "inspections", target_mission / "inspections")

    connection = sqlite3.connect(db_target)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise SystemExit(f"Copied benchmark database integrity check failed: {integrity}")
        rows = connection.execute(
            "SELECT task_id,status,payload_json,depends_on_json FROM mission_tasks "
            "WHERE mission_id=? AND task_type='independent_review' ORDER BY task_id",
            (MISSION_ID,),
        ).fetchall()
        if len(rows) != 2 or any(row[1] != "failed" for row in rows):
            raise SystemExit(f"Expected exactly two immutable failed R15C reviewer tasks; found {rows!r}")
        now = datetime.now(timezone.utc).isoformat()
        connection.execute(
            "UPDATE mission_tasks SET status='pending',attempts=0,lease_owner=NULL,"
            "lease_expires_at=NULL,result_json=NULL,error=NULL,updated_at_utc=? "
            "WHERE mission_id=? AND task_type='independent_review'",
            (now, MISSION_ID),
        )
        connection.commit()
        pending = connection.execute(
            "SELECT COUNT(*) FROM mission_tasks WHERE mission_id=? AND task_type='independent_review' AND status='pending'",
            (MISSION_ID,),
        ).fetchone()[0]
        if pending != 2:
            raise SystemExit("Failed to reset exactly two reviewer tasks in the isolated database.")
    finally:
        connection.close()


def run_benchmark(workspace: Path, db_path: Path, artifact_root: Path,
                  manifest: dict[str, Any], model_manifest_path: Path) -> dict[str, Any]:
    model_manifest = json.loads(model_manifest_path.read_text(encoding="utf-8"))
    models = model_manifest.get("models", [])
    expected = manifest["model"]
    matching = [item for item in models if item.get("name") == expected["tag"]]
    if len(matching) != 1 or matching[0].get("digest") != expected["digest"]:
        raise SystemExit("Installed Ollama model digest does not match the immutable R15C baseline model.")
    if matching[0].get("details", {}).get("quantization_level") != expected["quantization"]:
        raise SystemExit("Installed Ollama quantization does not match the R15C baseline.")

    os.environ["FLR_DATABASE"] = str(db_path)
    os.environ["FLR_SNAPSHOT_DIR"] = str(workspace / "data" / "source-capture-pilot-vault")
    os.environ.setdefault("FLR_MODEL_BASE_URL", "http://127.0.0.1:11434")
    os.environ.setdefault("FLR_MODEL_NAME", expected["tag"])
    os.environ.setdefault("FLR_MODEL_CONTEXT_TOKENS", "16384")
    os.environ.setdefault("FLR_MODEL_MAX_OUTPUT_TOKENS", "2400")
    os.environ.setdefault("FLR_MODEL_TIMEOUT_SECONDS", "1800")
    os.environ.setdefault("FLR_MODEL_MAX_REVIEWER_CONTEXT_CHARS", "18000")
    os.environ.setdefault("FLR_MODEL_MAX_PARALLEL_TASKS", "1")

    from flashloan_research.specialist_runner import run_specialist_batch

    started = time.monotonic()
    batches: list[dict[str, Any]] = []
    for _ in range(2):
        result = run_specialist_batch(MISSION_ID, db_path, artifact_root, limit=1)
        batches.append(result)
        if result.get("claimed_tasks", 0) == 0:
            break
    elapsed = time.monotonic() - started

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        task_rows = [dict(row) for row in connection.execute(
            "SELECT task_id,task_type,role,status,error,result_json,payload_json "
            "FROM mission_tasks WHERE mission_id=? AND task_type IN "
            "('independent_review','candidate_dossier') ORDER BY task_type,task_id",
            (MISSION_ID,),
        )]
    finally:
        connection.close()

    outcomes = []
    exchange_dir = artifact_root / MISSION_ID / "model_exchanges"
    for path in sorted(exchange_dir.glob("*__independent_review.json")):
        captured = json.loads(path.read_text(encoding="utf-8"))
        exchange = captured.get("exchange", {})
        request = exchange.get("request", {})
        user_content = None
        messages = request.get("messages", [])
        if len(messages) > 1 and isinstance(messages[1].get("content"), str):
            user_content = messages[1]["content"]
        packet_fingerprint = (
            hashlib.sha256(user_content.encode("utf-8")).hexdigest()
            if isinstance(user_content, str) else None
        )
        output = load_model_output(exchange)
        repository = captured.get("repository")
        slug = str(repository).replace("/", "__")
        report_path = artifact_root / MISSION_ID / "specialists" / f"{slug}__independent_review.json"
        validated_report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
        outcomes.append({
            "repository": repository,
            "task_id": captured.get("task_id"),
            "inspection_commit_sha": captured.get("inspection_commit_sha"),
            "inspection_tree_sha": captured.get("inspection_tree_sha"),
            "packet_adequacy": captured.get("specialist_packet_adequacy"),
            "request_sha256": exchange.get("request_sha256"),
            "response_sha256": exchange.get("response_sha256"),
            "input_packet_sha256": packet_fingerprint,
            "finish_reason": (
                json.loads(exchange["response_raw"]).get("choices", [{}])[0].get("finish_reason")
                if isinstance(exchange.get("response_raw"), str) else None
            ),
            "model_output": output,
            "validated_report": validated_report,
            "exchange_file": str(path),
            "exchange_file_sha256": sha256_file(path),
        })

    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report = {
        "benchmark_id": "r15d-reviewer-baseline-qwen25-3b-r15c-frozen-packet",
        "status": "completed" if len(outcomes) == 2 else "incomplete",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mission_id": MISSION_ID,
        "source_artifact": manifest["artifact"],
        "source_database_sha256": manifest["mission"]["sqlite_sha256"],
        "model": {
            "tag": expected["tag"],
            "digest": expected["digest"],
            "quantization": expected["quantization"],
            "context_length_reported_by_model": expected["context"],
            "request_context_tokens": int(os.environ["FLR_MODEL_CONTEXT_TOKENS"]),
            "max_output_tokens": int(os.environ["FLR_MODEL_MAX_OUTPUT_TOKENS"]),
            "prompt_template_version": "5.6.0-r15d-adequacy-and-exchange-capture",
            "ollama_manifest_sha256": sha256_file(model_manifest_path),
        },
        "runtime": {
            "elapsed_seconds": round(elapsed, 3),
            "process_peak_rss_kb": peak_rss,
            "execution_mode": "GitHub-hosted CPU-only runner; one model loaded; one reviewer task at a time",
        },
        "reviewer_outcomes": outcomes,
        "task_ledger": task_rows,
        "batch_results": batches,
        "acceptance": {
            "reviewer_exchanges_captured": len(outcomes) == 2,
            "both_packets_expected_insufficient": all(
                item.get("packet_adequacy", {}).get("status") == "insufficient" for item in outcomes
            ),
            "both_model_decisions_inconclusive": all(
                (item.get("model_output") or {}).get("review_decision") == "inconclusive" for item in outcomes
            ),
            "dossiers_remain_pending": all(
                row["status"] == "pending" for row in task_rows if row["task_type"] == "candidate_dossier"
            ),
            "semantic_audit_increment": 0,
            "candidate_code_executed": False,
            "wallet_access": False,
            "transaction_signing": False,
            "deployment": False,
            "live_trading": False,
            "paid_inference": False,
            "cloud_inference": False,
        },
    }
    report_path = artifact_root / MISSION_ID / "r15d-reviewer-baseline-report.json"
    write_json(report_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay only the two R15C reviewer tasks on a fresh isolated DB.")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path, required=True)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    eval_root = args.eval_root.resolve()
    artifact_root = args.artifact_root.resolve()
    manifest_path = workspace / "research" / "R15C_EVALUATION_PACKET_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "frozen_failed_regression_fixture_not_semantic_acceptance":
        raise SystemExit("R15C manifest status is not the expected immutable failed-fixture state.")
    source_vault = workspace / "data" / "source-capture-pilot-vault"
    mission_root, db_source = verify_frozen_packet(workspace, eval_root, manifest, source_vault)
    create_isolated_benchmark_state(db_source, args.database.resolve(), mission_root, artifact_root)
    report = run_benchmark(workspace, args.database.resolve(), artifact_root, manifest, args.model_manifest.resolve())
    report_path = artifact_root / MISSION_ID / "r15d-reviewer-baseline-report.json"
    print(json.dumps({
        "status": report["status"],
        "report": str(report_path),
        "reviewer_exchanges": len(report["reviewer_outcomes"]),
        "acceptance": report["acceptance"],
    }, indent=2))
    if report["status"] != "completed":
        raise SystemExit("R15D baseline did not capture both candidate reviewer exchanges.")


if __name__ == "__main__":
    main()
