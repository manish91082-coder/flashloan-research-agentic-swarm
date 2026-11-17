from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts.validate_r15d_adjudication import ALLOWED, EVIDENCE_RE, EXPECTED_CASES, EXPECTED_PINS, _valid_timestamp

ROOT = Path(__file__).resolve().parents[1]
REVIEWER_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{3,128}$")
TOP_LEVEL_FIELDS = {"schema_version", "benchmark_id", "reviewer_id", "submitted_at", "attestations", "cases"}
ATTESTATION_FIELDS = {"independent_review", "model_outputs_not_seen", "other_reviews_not_seen", "conflicts_disclosed", "conflict_statement"}
CASE_FIELDS = {"case_id", "source_pin", "label", "rationale", "evidence_references", "confidence", "completed_at"}
PIN_FIELDS = {"repository", "commit_sha", "tree_sha", "path", "git_blob_sha1", "line_start", "line_end", "excerpt_sha256"}


def _exact_keys(value: object, expected: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == expected


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _expected_pin(case_id: str) -> dict:
    values = EXPECTED_PINS[case_id]
    return {
        "repository": values[0],
        "commit_sha": values[1],
        "tree_sha": values[2],
        "path": values[3],
        "git_blob_sha1": values[4],
        "line_start": values[5],
        "line_end": values[6],
        "excerpt_sha256": values[7],
    }


def _valid_evidence_references(references: object, pin: dict) -> bool:
    if not isinstance(references, list) or not references:
        return False
    normalized = []
    for reference in references:
        if not isinstance(reference, str):
            return False
        value = reference.strip()
        match = EVIDENCE_RE.fullmatch(value)
        if not match:
            return False
        if not (
            match.group("path") == pin["path"]
            and match.group("start") == str(pin["line_start"])
            and (match.group("end") or match.group("start")) == str(pin["line_end"])
            and match.group("sha") == pin["excerpt_sha256"]
        ):
            return False
        normalized.append(value)
    return len(normalized) == len(set(normalized))


def validate_submission(submission: object) -> dict:
    errors: list[str] = []
    if not _exact_keys(submission, TOP_LEVEL_FIELDS):
        return {"valid": False, "reviewer_id": None, "case_count": 0, "errors": ["submission must be an object with exactly the schema-defined top-level fields"]}

    if submission.get("schema_version") != "1.0":
        errors.append("schema_version must equal 1.0")
    if submission.get("benchmark_id") != "r15d-semantic-source-facts-v1":
        errors.append("unexpected benchmark_id")

    reviewer_id = submission.get("reviewer_id")
    if not isinstance(reviewer_id, str) or not REVIEWER_ID_RE.fullmatch(reviewer_id) or reviewer_id != reviewer_id.strip():
        errors.append("reviewer_id must be a stable 3-128 character identifier without whitespace")

    if not _valid_timestamp(submission.get("submitted_at")):
        errors.append("submitted_at must be a timezone-aware UTC ISO-8601 timestamp")

    attestations = submission.get("attestations")
    if not _exact_keys(attestations, ATTESTATION_FIELDS):
        errors.append("attestations must contain exactly the schema-defined fields")
    else:
        for field in ("independent_review", "model_outputs_not_seen", "other_reviews_not_seen", "conflicts_disclosed"):
            if attestations.get(field) is not True:
                errors.append(f"required reviewer attestation must be true: {field}")
        if not isinstance(attestations.get("conflict_statement"), str) or len(attestations["conflict_statement"].strip()) < 3:
            errors.append("conflict_statement must explicitly state none or describe the disclosed conflict")

    cases = submission.get("cases")
    if not isinstance(cases, list) or len(cases) != len(EXPECTED_CASES):
        errors.append("submission must contain exactly six cases")
        cases = cases if isinstance(cases, list) else []

    case_ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    if (
        len(case_ids) != len(cases)
        or not all(isinstance(case_id, str) for case_id in case_ids)
        or set(case_ids) != EXPECTED_CASES
        or len(set(case_ids)) != len(EXPECTED_CASES)
    ):
        errors.append("case IDs must contain each of the six canonical IDs exactly once")

    for index, case in enumerate(cases):
        label = case.get("case_id", f"<slot-{index + 1}>") if isinstance(case, dict) else f"<slot-{index + 1}>"
        if not _exact_keys(case, CASE_FIELDS):
            errors.append(f"{label}: case must contain exactly the schema-defined fields")
            continue
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or case_id not in EXPECTED_CASES:
            errors.append(f"{label}: unknown case ID")
            continue
        pin = _expected_pin(case_id)
        if not _exact_keys(case.get("source_pin"), PIN_FIELDS) or case.get("source_pin") != pin:
            errors.append(f"{case_id}: source pin does not match immutable R15D baseline")
        if case.get("label") not in ALLOWED:
            errors.append(f"{case_id}: label is not in the allowed applicability taxonomy")
        if not isinstance(case.get("rationale"), str) or not case["rationale"].strip():
            errors.append(f"{case_id}: rationale must be non-empty")
        if not _valid_evidence_references(case.get("evidence_references"), pin):
            errors.append(f"{case_id}: evidence references must be unique and match exact pinned path/range/excerpt SHA-256")
        confidence = case.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            errors.append(f"{case_id}: confidence must be a number between 0 and 1")
        if not _valid_timestamp(case.get("completed_at")):
            errors.append(f"{case_id}: completed_at must be a timezone-aware UTC ISO-8601 timestamp")

    return {
        "valid": not errors,
        "reviewer_id": reviewer_id if isinstance(reviewer_id, str) else None,
        "case_count": len(cases),
        "errors": errors,
        "identity_verification": "not_performed_by_validator",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate one private R15D six-case reviewer bundle; does not verify human identity.")
    parser.add_argument("--submission", type=Path, required=True)
    args = parser.parse_args()
    try:
        raw = args.submission.read_bytes()
        submission = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"valid": False, "errors": [f"unable to read duplicate-free UTF-8 JSON submission: {exc}"]}, indent=2))
        raise SystemExit(1)
    result = validate_submission(submission)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
