from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET = ROOT / "research_runs/r15d_adjudication/blind_adjudication_packet.json"
ALLOWED = {"present", "absent", "not_applicable", "unknown"}
EXPECTED_CASES = {"NAV-01", "NAV-02", "NAV-03", "COB-01", "COB-02", "COB-03"}


def _review_complete(review: dict) -> bool:
    return (
        isinstance(review.get("reviewer_id"), str)
        and bool(review["reviewer_id"].strip())
        and review.get("label") in ALLOWED
        and isinstance(review.get("rationale"), str)
        and bool(review["rationale"].strip())
        and isinstance(review.get("evidence_references"), list)
        and bool(review["evidence_references"])
        and isinstance(review.get("confidence"), (int, float))
        and not isinstance(review.get("confidence"), bool)
        and 0 <= review["confidence"] <= 1
        and isinstance(review.get("completed_at"), str)
        and bool(review["completed_at"].strip())
        and review.get("independence_attestation") is True
    )


def validate(packet: dict, require_complete: bool = False) -> dict:
    errors: list[str] = []
    cases = packet.get("cases")
    if packet.get("benchmark_id") != "r15d-semantic-source-facts-v1":
        errors.append("unexpected benchmark_id")
    if not isinstance(cases, list) or {c.get("id") for c in cases if isinstance(c, dict)} != EXPECTED_CASES:
        errors.append("case set must contain exactly the six frozen R15D case IDs")
        cases = cases if isinstance(cases, list) else []

    complete_count = 0
    for case in cases:
        cid = case.get("id", "<missing>") if isinstance(case, dict) else "<invalid>"
        if not isinstance(case, dict):
            errors.append(f"{cid}: case must be an object")
            continue
        reviews = case.get("reviewers")
        if not isinstance(reviews, list) or len(reviews) != 2:
            errors.append(f"{cid}: exactly two independent reviewer slots required")
            continue
        complete = [_review_complete(r) if isinstance(r, dict) else False for r in reviews]
        ids = [r.get("reviewer_id") for r in reviews if isinstance(r, dict)]
        if all(complete) and len(set(ids)) != 2:
            errors.append(f"{cid}: reviewer IDs must be distinct")
        if any(complete) and not all(complete):
            errors.append(f"{cid}: partial reviewer submission; both reviews must be complete")
        consensus = case.get("consensus", {})
        if all(complete):
            labels = [r["label"] for r in reviews]
            disagreement = labels[0] != labels[1]
            third = case.get("third_adjudicator", {})
            if disagreement:
                if not isinstance(third, dict) or not _review_complete(third):
                    errors.append(f"{cid}: disagreement requires a complete independent third adjudication")
                elif third.get("reviewer_id") in ids:
                    errors.append(f"{cid}: third adjudicator must be distinct from both reviewers")
            if not isinstance(consensus, dict) or consensus.get("label") not in ALLOWED or not isinstance(consensus.get("rationale"), str) or not consensus["rationale"].strip():
                errors.append(f"{cid}: consensus label and rationale required")
            elif consensus.get("disagreement") is not disagreement:
                errors.append(f"{cid}: consensus disagreement flag does not match reviewer labels")
            else:
                complete_count += 1
        elif require_complete:
            errors.append(f"{cid}: independent reviews are pending")
    complete = complete_count == len(EXPECTED_CASES) and not errors
    if require_complete and not complete:
        errors.append("ground truth is not eligible for freeze")
    return {"valid": not errors, "complete": complete, "completed_cases": complete_count, "case_count": len(EXPECTED_CASES), "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate R15D independent adjudication records; never creates labels.")
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = validate(json.loads(args.packet.read_text(encoding="utf-8")), args.require_complete)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
