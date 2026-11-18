from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

# Configure the same loopback-only source vault contract used by the Agent Form
# before importing modules that freeze Settings from environment variables.
os.environ.setdefault("FLR_DATABASE", "data/agentic-mission.sqlite3")
os.environ.setdefault("FLR_SNAPSHOT_DIR", "data/source-capture-pilot-vault")

from flashloan_research.mission_queue import MissionQueue
from flashloan_research.mission_runtime import MissionTaskStore, build_mission_plan
from flashloan_research.storage import git_blob_sha, write_json


MISSION_ID = "flashloan-research-43600488013"
DISCOVERY_RUN_ID = "43600488013"


def load_reports(report_dir: Path, vault: Path, limit: int, source_run_id: str = DISCOVERY_RUN_ID, normalize_inspection_reports: bool = False) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in sorted(report_dir.glob("*.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("record_type") != "commit_pinned_source_capture":
            if not normalize_inspection_reports or not report.get("commit_sha") or not report.get("tree_sha") or not isinstance(report.get("captured_files"), list):
                continue
            report = {
                **report,
                "record_type": "commit_pinned_source_capture",
                "run_id": source_run_id,
                "candidate_index": len(reports),
                "matched_families": [],
                "discovered_by": [],
                "candidate_code_executed": False,
                "audit_status": "source_captured_pending_semantic_review",
            }
        if report.get("run_id") != source_run_id or report.get("candidate_code_executed") is not False:
            raise SystemExit(f"Report identity/safety mismatch: {path}")
        if not report.get("commit_sha") or not report.get("tree_sha"):
            raise SystemExit(f"Missing commit/tree pin: {path}")
        for item in report.get("captured_files", []):
            rel = item.get("vault_relative_path")
            blob_sha = item.get("blob_sha")
            if not isinstance(rel, str) or not isinstance(blob_sha, str):
                raise SystemExit(f"Malformed captured-file record: {path}")
            candidate = (vault / rel).resolve()
            if vault.resolve() not in candidate.parents or not candidate.is_file() or candidate.is_symlink():
                raise SystemExit(f"Source blob missing or unsafe: {path}:{rel}")
            if git_blob_sha(candidate.read_bytes()) != blob_sha:
                raise SystemExit(f"Git blob SHA mismatch: {path}:{rel}")
        reports.append(report)
    if not reports:
        raise SystemExit("No verified source-capture reports found.")

    # Prioritize direct flash-loan/liquidation intersections first. Family and
    # lexical-signal counts are scheduling hints only, never audit conclusions.
    def priority(report: dict[str, Any]) -> tuple[int, ...]:
        families = set(report.get("matched_families", []))
        return (
            int("flash_loan_liquidation_combo" in families),
            int("flash_loan_core" in families),
            int("defi_liquidation" in families),
            int("flash_loan_provider_apis" in families),
            int("lending_protocols" in families),
            int("security_accounting" in families),
            min(len(report.get("signals", [])), 100),
            -int(report["candidate_index"]),
        )

    reports.sort(key=priority, reverse=True)
    return reports[:limit]


def form_payload(repository_limit: int, mission_id: str = MISSION_ID, source_run_id: str = DISCOVERY_RUN_ID, candidate_inventory_count: int = 7901) -> dict[str, Any]:
    taxonomy = json.loads(Path("research/keyword-taxonomy.json").read_text(encoding="utf-8"))
    return {
        "mission_id": mission_id,
        "title": "Flash Loan & DeFi Autonomous Public Repository Research",
        "objective": (
            f"Research the {candidate_inventory_count}-repository frozen public GitHub candidate inventory from source run {source_run_id}, discovered by the locked "
            "11-family flash-loan taxonomy. Establish actual repository purpose and implemented "
            "call flow from commit-pinned source; classify implementation completeness; inspect "
            "flash-loan callbacks, initiator/asset binding, repayment and premium accounting, "
            "liquidation eligibility, collateral/debt math, oracle assumptions, DEX routing, "
            "slippage, gas/MEV economics, tests, dependencies, license and maintenance. "
            "Preserve source-level evidence and independent review. Never execute candidate code."
        ),
        "domain": "cross_protocol_research",
        "scope": {
            "chains": ["Ethereum", "Polygon", "Arbitrum", "Base", "Optimism", "BNB Chain"],
            "protocols": ["Aave V3", "Morpho Blue", "Balancer", "Uniswap V2/V3/V4", "Compound V2/V3", "Euler"],
            "repository_limit": repository_limit,
            "include_archived": False,
            "include_older_references": True,
            "include_forked": True,
            "keyword_taxonomy_version": taxonomy.get("taxonomy_version", "1.0.0"),
            "discovery_query_families": list(taxonomy["family_queries"].keys()),
            "search_per_page": 100,
            "max_pages_per_query": 10,
        },
        "research_depth": "deep_forensic",
        "agent_policy": {
            "mode": "autonomous",
            "independent_review": True,
            "max_parallel_agents": 4,
            "max_iterations": 5,
            "specialists": [
                "research_director", "github_discovery", "protocol_specialist",
                "solidity_security", "execution_engineer", "test_verification",
                "economics_quant", "dependency_license", "evidence_auditor",
                "independent_reviewer", "continuity_documentation",
            ],
        },
        "safety_policy": {
            "research_only": True,
            "execute_candidate_code": False,
            "wallet_access": False,
            "sign_transactions": False,
            "deploy_contracts": False,
            "live_trading": False,
            "paid_services": False,
            "allow_free_model_inference": True,
        },
        "deliverables": [
            "candidate_matrix", "protocol_architecture", "source_audits",
            "security_findings", "test_and_ci_evidence", "profitability_model",
            "dependency_license_report", "evidence_register",
            "executive_summary", "next_research_queue",
        ],
        "acceptance_criteria": [
            "Every material claim has commit-pinned source evidence.",
            "Source blob SHA and line range are recorded.",
            "Static signals are not promoted to findings without validation.",
            "Independent review is required for security-critical findings.",
            "Unknown costs, missing quotes and incomplete scans fail closed.",
        ],
        "created_at_utc": "2026-11-14T00:00:00Z",
    }


def complete_ready(store: MissionTaskStore, mission_id: str, task_type: str,
                   result_factory, worker_id: str) -> int:
    count = 0
    while True:
        claims = store.claim_ready(mission_id, worker_id, limit=12,
                                   lease_seconds=300, task_types={task_type})
        if not claims:
            return count
        for task in claims:
            store.complete_task(mission_id, task["task_id"], worker_id,
                                result_factory(task))
            count += 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize the Agent Form mission DAG from verified source-capture reports."
    )
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--mission-db", type=Path, default=Path("data/agentic-mission.sqlite3"))
    parser.add_argument("--artifact-root", type=Path, default=Path("research_runs/mission"))
    parser.add_argument("--batch-limit", type=int, default=12)
    parser.add_argument("--mission-id", default=MISSION_ID)
    parser.add_argument("--source-run-id", default=DISCOVERY_RUN_ID)
    parser.add_argument("--candidate-inventory-count", type=int, default=7901)
    parser.add_argument("--normalize-inspection-reports", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.batch_limit <= 100:
        raise SystemExit("--batch-limit must be between 1 and 100")
    if not args.mission_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in args.mission_id):
        raise SystemExit("--mission-id must contain only letters, digits, hyphens and underscores")

    os.environ["FLR_DATABASE"] = str(args.mission_db)
    os.environ["FLR_SNAPSHOT_DIR"] = str(args.vault)
    if args.candidate_inventory_count < args.batch_limit:
        raise SystemExit("candidate inventory count cannot be smaller than batch limit")
    reports = load_reports(args.report_dir, args.vault, args.batch_limit, args.source_run_id,
                           normalize_inspection_reports=args.normalize_inspection_reports)
    payload = form_payload(args.batch_limit, args.mission_id, args.source_run_id,
                           args.candidate_inventory_count)
    taxonomy = json.loads(Path("research/keyword-taxonomy.json").read_text(encoding="utf-8"))
    queue = MissionQueue(args.mission_db)
    tasks = MissionTaskStore(args.mission_db)
    try:
        try:
            queued = queue.enqueue(payload)
        except Exception as exc:
            existing = queue.get(args.mission_id)
            if not existing:
                raise
            if existing["payload"] != payload:
                raise SystemExit("Existing mission ID has a different form payload; refusing overwrite.") from exc
            queued = {"mission_id": args.mission_id, "status": existing["status"], "reused": True}

        plan = build_mission_plan(payload, taxonomy)
        plan_result = tasks.create_plan(plan)
        worker = "agent-form-bootstrap"
        complete_ready(tasks, args.mission_id, "mission_plan",
                       lambda task: {"status": "plan_validated", "source": "Agent Form payload"},
                       worker)
        complete_ready(tasks, args.mission_id, "discover_family",
                       lambda task: {"status": "discovery_imported_from_verified_inventory",
                                     "family_id": task["payload"]["family_id"],
                                     "source_run_id": args.source_run_id,
                                     "live_discovery_repeated": False},
                       worker)
        complete_ready(tasks, args.mission_id, "merge_candidates",
                       lambda task: {"unique_repository_count": args.candidate_inventory_count,
                                     "source": "immutable_11_family_discovery_manifest",
                                     "candidate_purpose_verified": False},
                       worker)
        complete_ready(tasks, args.mission_id, "purpose_triage",
                       lambda task: {"candidate_count": args.candidate_inventory_count,
                                     "purpose_status": "purpose_unverified_until_semantic_review",
                                     "triage_basis": "discovery provenance only"},
                       worker)

        expansion_claims = tasks.claim_ready(args.mission_id, worker, limit=1,
                                             lease_seconds=300,
                                             task_types={"expand_candidate_tasks"})
        if expansion_claims:
            expansion = expansion_claims[0]
            repositories = [x["repository"] for x in reports]
            expanded = tasks.expand_candidates(
                args.mission_id, expansion["task_id"], repositories,
                selected_roles=payload["agent_policy"]["specialists"],
            )
            tasks.complete_task(args.mission_id, expansion["task_id"], worker, {
                **expanded,
                "batch_limit": args.batch_limit,
                "candidate_inventory_count": args.candidate_inventory_count,
                "candidates_remaining_unplanned": args.candidate_inventory_count - len(repositories),
                "repository_batch": repositories,
                "source": "verified_source_capture_checkpoint",
            })
        else:
            expanded = {"candidate_count": len(reports), "tasks_inserted": 0,
                        "status": "existing_expansion"}

        mission_dir = args.artifact_root / args.mission_id
        inspection_dir = mission_dir / "inspections"
        inspection_dir.mkdir(parents=True, exist_ok=True)
        report_paths: dict[str, str] = {}
        for report in reports:
            repository = report["repository"]
            destination = inspection_dir / (repository.replace("/", "__") + ".json")
            write_json(destination, report)
            report_paths[repository] = str(destination)

        completed_sources = complete_ready(
            tasks, args.mission_id, "candidate_source_capture",
            lambda task: {
                "repository": task["payload"]["repository"],
                "inspection_report": report_paths[task["payload"]["repository"]],
                "commit_sha": next(x["commit_sha"] for x in reports if x["repository"] == task["payload"]["repository"]),
                "tree_sha": next(x["tree_sha"] for x in reports if x["repository"] == task["payload"]["repository"]),
                "source_status": "restored_and_blob_verified",
            },
            worker,
        )
        queue.set_status(args.mission_id, "running")
        output = {
            "status": "agent_form_mission_initialized_from_verified_capture",
            "mission_id": args.mission_id,
            "source_run_id": args.source_run_id,
            "candidate_inventory_count": args.candidate_inventory_count,
            "form_payload_accepted": True,
            "mission_queue": queued,
            "plan_tasks": len(plan),
            "plan_inserted": plan_result["inserted"],
            "candidate_batch": len(reports),
            "candidate_task_expansion": expanded,
            "source_capture_tasks_completed": completed_sources,
            "candidate_purpose_tasks_ready": sum(
                1 for x in tasks.list_tasks(args.mission_id)
                if x["task_type"] == "candidate_purpose" and x["status"] == "pending"
            ),
            "semantic_specialists_executed": False,
            "independent_review_completed": False,
            "candidate_code_executed": False,
            "next_gate": "run loopback-only open-weight inference pilot; do not count audits before evidence and reviewer gates",
        }
        out = mission_dir / "agent-form-bootstrap.json"
        write_json(out, output)
        print(json.dumps(output, indent=2, sort_keys=True))
    finally:
        tasks.close()
        queue.close()


if __name__ == "__main__":
    main()
