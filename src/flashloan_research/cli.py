from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .analyzer import ResearchPipeline
from .config import SETTINGS
from .mission_discovery import run_taxonomy_discovery
from .storage import ResearchStore, export_evidence_csv, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flashloan-research", description="Evidence-first GitHub Flash Loan research pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    discover = sub.add_parser("discover", help="Search GitHub repositories and store candidates")
    discover.add_argument("--query", required=True)
    discover.add_argument("--per-page", type=int, default=30)
    discover.add_argument("--page", type=int, default=1)
    discover.add_argument("--output", default=None, help="Optional path for a portable JSON discovery record")
    mission_discover = sub.add_parser("discover-mission", help="Run all selected flash-loan taxonomy searches with pagination and coverage ledger")
    mission_discover.add_argument("--taxonomy", default="research/keyword-taxonomy.json")
    mission_discover.add_argument("--families", default=None, help="Comma-separated taxonomy family IDs; defaults to all families")
    mission_discover.add_argument("--per-page", type=int, default=100)
    mission_discover.add_argument("--max-pages", type=int, default=10)
    mission_discover.add_argument("--include-archived", action="store_true")
    mission_discover.add_argument("--exclude-forks", action="store_true")
    mission_discover.add_argument("--output", default=None)
    run_mission = sub.add_parser("run-mission", help="Execute a form-submitted mission using the checkpointed agentic workflow")
    run_mission.add_argument("--mission-id", required=True)
    run_mission.add_argument("--database", default=str(SETTINGS.database_path))
    run_mission.add_argument("--taxonomy", default="research/keyword-taxonomy.json")
    run_mission.add_argument("--artifacts", default="research_runs/mission")
    run_mission.add_argument("--checkpoints", default=None)
    import_discovery = sub.add_parser("import-discovery", help="Resumeably import a persisted discovery report into SQLite in bounded batches")
    import_discovery.add_argument("--input", required=True, help="Path to a persisted taxonomy discovery JSON report")
    import_discovery.add_argument("--run-id", required=True, help="Stable discovery run identifier")
    import_discovery.add_argument("--batch-size", type=int, default=200)
    import_discovery.add_argument("--max-batches", type=int, default=None, help="Optional bounded invocation; rerun with same run-id to resume")
    export_batches = sub.add_parser("export-discovery-batches", help="Export a completed discovery import as hashed JSONL batches")
    export_batches.add_argument("--run-id", required=True)
    export_batches.add_argument("--output-dir", required=True)
    export_batches.add_argument("--batch-size", type=int, default=100)
    export_batches.add_argument("--source-report", default=None)
    inspect = sub.add_parser("inspect", help="Pin default-branch commit and capture bounded source evidence")
    inspect.add_argument("repository", help="owner/name")
    status = sub.add_parser("status", help="Show local database counts")
    export = sub.add_parser("export-evidence", help="Export evidence register as CSV")
    export.add_argument("--output", default="reports/EVIDENCE_REGISTER.csv")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    store = ResearchStore(SETTINGS.database_path)
    try:
        if args.command == "discover":
            pipeline = ResearchPipeline()
            candidates = pipeline.discover(args.query, store, args.per_page, args.page)
            payload = {
                "schema_version": "1.0",
                "record_type": "github_repository_discovery",
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                "query": args.query,
                "page": args.page,
                "per_page": args.per_page,
                "candidate_count": len(candidates),
                "candidates": [candidate.to_dict() for candidate in candidates],
                "limitations": [
                    "A search result is a discovery lead, not evidence of flash-loan functionality.",
                    "Candidates require commit-pinned source inspection and independent verification.",
                    "GitHub search ranking and API limits can omit relevant repositories.",
                ],
            }
            if args.output:
                write_json(Path(args.output), payload)
            print(json.dumps({"discovered": len(candidates), "output": args.output, "repositories": [c.full_name for c in candidates]}, indent=2))
        elif args.command == "discover-mission":
            selected = [x.strip() for x in args.families.split(",") if x.strip()] if args.families else None
            pipeline = ResearchPipeline()
            report = run_taxonomy_discovery(
                pipeline.client, store, Path(args.taxonomy), selected,
                args.per_page, args.max_pages, args.include_archived, not args.exclude_forks,
            )
            output = Path(args.output) if args.output else Path("research_runs") / (
                "mission-discovery-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json"
            )
            write_json(output, report)
            print(json.dumps({
                "report": str(output),
                "unique_candidates": report["unique_candidate_count"],
                "queries": report["query_count"],
                "complete_queries": report["complete_query_count"],
                "incomplete_queries": report["incomplete_query_count"],
                "coverage_complete": report["coverage_complete"],
            }, indent=2))
        elif args.command == "run-mission":
            from .mission_graph import run_mission_graph
            result = run_mission_graph(
                args.mission_id,
                Path(args.database),
                Path(args.taxonomy),
                Path(args.artifacts),
                Path(args.checkpoints) if args.checkpoints else None,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "import-discovery":
            from .discovery_import import import_discovery_report
            report = import_discovery_report(
                Path(args.input), args.run_id, store,
                batch_size=args.batch_size, max_batches=args.max_batches,
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif args.command == "export-discovery-batches":
            from .discovery_import import export_discovery_batches
            report = export_discovery_batches(
                store, args.run_id, Path(args.output_dir),
                batch_size=args.batch_size, source_report_path=args.source_report,
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif args.command == "inspect":
            pipeline = ResearchPipeline()
            result = pipeline.inspect(args.repository, store)
            out = Path("reports") / (args.repository.replace("/", "__") + "__inspection.json")
            write_json(out, result)
            print(json.dumps({"report": str(out), **{k: result[k] for k in ("repository", "commit_sha", "source_files_captured", "tree_truncated")}}, indent=2))
        elif args.command == "status":
            print(json.dumps(store.counts(), indent=2))
        elif args.command == "export-evidence":
            export_evidence_csv(store, Path(args.output))
            print(f"Exported evidence register: {args.output}")
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
