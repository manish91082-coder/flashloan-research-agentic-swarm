from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .analyzer import ResearchPipeline
from .config import SETTINGS
from .storage import ResearchStore, export_evidence_csv, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flashloan-research", description="Evidence-first GitHub Flash Loan research pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    discover = sub.add_parser("discover", help="Search GitHub repositories and store candidates")
    discover.add_argument("--query", required=True)
    discover.add_argument("--per-page", type=int, default=30)
    discover.add_argument("--page", type=int, default=1)
    discover.add_argument("--output", default=None, help="Optional path for a portable JSON discovery record")
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
