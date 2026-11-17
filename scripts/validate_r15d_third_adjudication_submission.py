from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts.validate_r15d_adjudication import (
    CASE_FIELDS, CONSENSUS_FIELDS, EXPECTED_CASES, EXPECTED_PINS, EVIDENCE_RE,
    REVIEW_FIELDS, THIRD_FIELDS, _has_exact_keys, _has_pinned_evidence,
    _review_complete, _valid_timestamp,
)
from scripts.validate_r15d_review_submission import _unique_object

ROOT = Path(__file__).resolve().parents[1]
TOP_FIELDS = {"schema_version", "benchmark_id", "reviewer_id", "submitted_at", "attestations", "cases"}
ATTESTATION_FIELDS = {"independent_review", "model_outputs_not_seen", "primary_reviews_seen", "conflicts_disclosed", "conflict_statement"}
THIRD_CASE_FIELDS = {"case_id", "source_pin", "label", "rationale", "evidence_references", "confidence", "completed_at", "independence_attestation"}
PIN_FIELDS = {"repository", "commit_sha", "tree_sha", "path", "git_blob_sha1", "line_start", "line_end", "excerpt_sha256"}
ALLOWED = {"present", "absent", "not_applicable", "unknown"}
REVIEWER_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{3,128}$")


def _pin(case_id: str) -> dict:
    values = EXPECTED_PINS[case_id]
    return dict(zip(
        ("repository", "commit_sha", "tree_sha", "path", "git_blob_sha1", "line_start", "line_end", "excerpt_sha256"),
        values,
    ))


def _valid_refs(references: object, pin: dict) -> bool:
    if not isinstance(references, list) or not references:
        return False
    normalized = []
    for reference in references:
        if not isinstance(reference, str):
            return False
        match = EVIDENCE_RE.fullmatch(reference.strip())
        if not match or not (
            match.group("path") == pin["path"]
            and match.group("start") == str(pin["line_start"])
            and (match.group("end") or match.group("start")) == str(pin["line_end"])
            and match.group("sha") == pin["excerpt_sha256"]
        ):
            return False
        normalized.append(reference.strip())
    return len(normalized) == len(set(normalized))


def _validate_staged_packet(packet: object) -> tuple[list[str], list[str], set[str]]:
    errors = []
    disagreements = []
    primary_ids_by_slot = [set(), set()]
    if not isinstance(packet, dict):
        return ["staged packet must be a JSON object"], disagreements, set()
    if packet.get("schema_version") != "1.0" or packet.get("benchmark_id") != "r15d-semantic-source-facts-v1":
        errors.append("staged packet schema version or benchmark ID is invalid")
    if packet.get("packet_type") != "blind_ground_truth_adjudication" or packet.get("status") != "pending_independent_review":
        errors.append("staged packet must remain in pending independent-review state")
    if not _has_exact_keys(packet.get("freeze"), {"ground_truth_frozen", "frozen_at", "reviewer_output_visibility", "model_inference_authorized"}):
        errors.append("staged packet freeze object has an invalid shape")
    else:
        if packet["freeze"]["ground_truth_frozen"] is not False or packet["freeze"]["frozen_at"] is not None or packet["freeze"]["model_inference_authorized"] is not False:
            errors.append("staged packet must remain unfrozen with model inference unauthorized")
    cases = packet.get("cases")
    if not isinstance(cases, list) or len(cases) != 6:
        return errors + ["staged packet must contain exactly six cases"], disagreements, set()
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(ids) != 6 or not all(isinstance(x, str) for x in ids) or set(ids) != EXPECTED_CASES:
        errors.append("staged packet must contain each canonical case exactly once")
        return errors, disagreements, set()
    for case in cases:
        case_id = case["id"]
        if not _has_exact_keys(case, CASE_FIELDS):
            errors.append(f"{case_id}: case object has an invalid shape")
            continue
        if tuple(case.get(k) for k in ("repository", "commit_sha", "tree_sha", "path", "git_blob_sha1", "line_start", "line_end", "excerpt_sha256")) != EXPECTED_PINS[case_id]:
            errors.append(f"{case_id}: immutable source pin mismatch")
        reviewers = case.get("reviewers")
        if not isinstance(reviewers, list) or len(reviewers) != 2:
            errors.append(f"{case_id}: exactly two primary reviews are required")
            continue
        valid_reviews = []
        for index, review in enumerate(reviewers):
            if not _has_exact_keys(review, REVIEW_FIELDS) or not _review_complete(review) or not _has_pinned_evidence(case, review):
                errors.append(f"{case_id}: primary review {index + 1} is incomplete or has invalid pinned evidence")
                valid_reviews.append(False)
            else:
                valid_reviews.append(True)
                primary_ids_by_slot[index].add(review["reviewer_id"].strip())
        if not all(valid_reviews):
            continue
        if reviewers[0]["reviewer_id"].strip() == reviewers[1]["reviewer_id"].strip():
            errors.append(f"{case_id}: primary reviewer identities must be distinct")
        disagreement = reviewers[0]["label"] != reviewers[1]["label"]
        if disagreement:
            disagreements.append(case_id)
        third = case.get("third_adjudicator")
        if not _has_exact_keys(third, THIRD_FIELDS, optional={"independence_attestation"}):
            errors.append(f"{case_id}: third-adjudicator slot has an invalid shape")
        elif third.get("triggered") is not disagreement:
            errors.append(f"{case_id}: third-adjudicator trigger does not match primary-review disagreement")
        elif any(third.get(field) is not None for field in ("reviewer_id", "label", "rationale", "confidence", "completed_at", "independence_attestation")) or third.get("evidence_references") != []:
            errors.append(f"{case_id}: third-adjudicator slot must remain blank before third-review intake")
        consensus = case.get("consensus")
        if not _has_exact_keys(consensus, CONSENSUS_FIELDS) or consensus.get("status") != "pending" or consensus.get("label") is not None or consensus.get("rationale") is not None or consensus.get("disagreement") is not disagreement:
            errors.append(f"{case_id}: consensus must remain pending and reflect the primary disagreement state")
    for index, values in enumerate(primary_ids_by_slot):
        if len(values) != 1:
            errors.append(f"primary reviewer slot {index + 1} must retain one stable identity across all six cases")
    if primary_ids_by_slot[0] & primary_ids_by_slot[1]:
        errors.append("primary reviewer identities must be globally distinct")
    return errors, disagreements, primary_ids_by_slot[0] | primary_ids_by_slot[1]


def validate_third_submission(staged_packet: object, submission: object) -> dict:
    errors, disagreements, primary_ids = _validate_staged_packet(staged_packet)
    if errors:
        return {"valid": False, "disagreement_cases": disagreements, "errors": ["staged primary packet: " + error for error in errors]}
    if not disagreements:
        return {"valid": False, "disagreement_cases": [], "errors": ["no primary-review disagreement exists; third adjudication is not permitted or needed"]}
    if not _has_exact_keys(submission, TOP_FIELDS):
        return {"valid": False, "disagreement_cases": disagreements, "errors": ["third submission must contain exactly the schema-defined top-level fields"]}
    if submission.get("schema_version") != "1.0" or submission.get("benchmark_id") != "r15d-semantic-source-facts-v1":
        errors.append("third submission schema version or benchmark ID is invalid")
    reviewer_id = submission.get("reviewer_id")
    if not isinstance(reviewer_id, str) or not REVIEWER_ID_RE.fullmatch(reviewer_id) or reviewer_id != reviewer_id.strip():
        errors.append("third-adjudicator reviewer_id must be a normalized stable identifier")
    elif reviewer_id in primary_ids:
        errors.append("third adjudicator must be distinct from both primary reviewers")
    if not _valid_timestamp(submission.get("submitted_at")):
        errors.append("submitted_at must be a timezone-aware UTC ISO-8601 timestamp")
    attestations = submission.get("attestations")
    if not _has_exact_keys(attestations, ATTESTATION_FIELDS):
        errors.append("third-adjudicator attestations have an invalid shape")
    else:
        for field in ("independent_review", "model_outputs_not_seen", "primary_reviews_seen", "conflicts_disclosed"):
            if attestations.get(field) is not True:
                errors.append(f"required third-adjudicator attestation must be true: {field}")
        if not isinstance(attestations.get("conflict_statement"), str) or len(attestations["conflict_statement"].strip()) < 3:
            errors.append("conflict_statement must say none or describe the disclosed conflict")
    cases = submission.get("cases")
    if not isinstance(cases, list) or len(cases) != len(disagreements):
        errors.append("third submission must contain exactly the staged packet's disagreement cases")
        cases = cases if isinstance(cases, list) else []
    case_ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    if len(case_ids) != len(cases) or not all(isinstance(x, str) for x in case_ids) or set(case_ids) != set(disagreements) or len(set(case_ids)) != len(disagreements):
        errors.append("third submission case IDs must match every disagreement exactly once and no other cases")
    staged_by_id = {case["id"]: case for case in staged_packet["cases"]}
    for case in cases:
        case_id = case.get("case_id", "<invalid>") if isinstance(case, dict) else "<invalid>"
        if not _has_exact_keys(case, THIRD_CASE_FIELDS):
            errors.append(f"{case_id}: third-adjudication case has an invalid shape")
            continue
        if case_id not in disagreements:
            errors.append(f"{case_id}: third adjudication is only allowed for a primary disagreement")
            continue
        pin = _pin(case_id)
        if not _has_exact_keys(case.get("source_pin"), PIN_FIELDS) or case["source_pin"] != pin:
            errors.append(f"{case_id}: third-adjudication source pin mismatch")
        if not isinstance(case.get("label"), str) or case["label"] not in ALLOWED:
            errors.append(f"{case_id}: third-adjudication label is invalid")
        if not isinstance(case.get("rationale"), str) or not case["rationale"].strip():
            errors.append(f"{case_id}: third-adjudication rationale is required")
        if not _valid_refs(case.get("evidence_references"), pin):
            errors.append(f"{case_id}: third-adjudication evidence must match the exact pinned excerpt and be unique")
        confidence = case.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            errors.append(f"{case_id}: confidence must be a number between 0 and 1")
        if not _valid_timestamp(case.get("completed_at")):
            errors.append(f"{case_id}: completed_at must be a timezone-aware UTC ISO-8601 timestamp")
        if case.get("independence_attestation") is not True:
            errors.append(f"{case_id}: case-level independence attestation must be true")
    return {
        "valid": not errors,
        "reviewer_id": reviewer_id if isinstance(reviewer_id, str) else None,
        "case_count": len(cases),
        "disagreement_cases": disagreements,
        "errors": errors,
        "identity_verification": "not_performed_by_validator",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a private third-adjudicator bundle against the exact disagreements in a staged R15D primary packet.")
    parser.add_argument("--staged-packet", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    args = parser.parse_args()
    try:
        packet = _read_json(args.staged_packet, "staged packet")
        submission = _read_json(args.submission, "third-adjudicator submission")
    except ValueError as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2))
        raise SystemExit(1)
    result = validate_third_submission(packet, submission)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
