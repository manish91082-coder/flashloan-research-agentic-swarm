from __future__ import annotations

import argparse
import json
from pathlib import Path

from flashloan_research.reviewer_recovery import ReviewerRecoveryError, requeue_failed_reviewers


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Requeue only r4 independent-review tasks blocked by the known reviewer-context cap."
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--mission-id", required=True)
    parser.add_argument("--expected-count", type=int, default=2)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()
    if not 1 <= args.expected_count <= 10:
        raise SystemExit("--expected-count must be between 1 and 10")
    try:
        result = requeue_failed_reviewers(
            args.database, args.mission_id, args.expected_count, args.workspace.resolve()
        )
    except ReviewerRecoveryError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
