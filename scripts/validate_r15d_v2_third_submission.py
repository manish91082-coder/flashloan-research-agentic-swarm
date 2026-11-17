from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts.validate_r15d_adjudication import _valid_timestamp
from scripts.validate_r15d_review_submission import _unique_object
from scripts.validate_r15d_v2_review_submission import (
    ALLOWED, CASE_FIELDS as UNUSED_CASE_FIELDS, PIN_FIELDS, _valid_evidence,
    load_fixture_bundle,
)

TOP_FIELDS = {"schema_version", "benchmark_id", "reviewer_id", "submitted_at", "attestations", "cases"}
ATTESTATION_FIELDS = {"independent_review", "model_outputs_not_seen", "primary_reviews_seen", "v1_answer_key_not_seen", "v1_labels_not_consulted", "conflicts_disclosed", "conflict_statement"}
THIRD_CASE_FIELDS = {"case_id", "source_pin", "label", "rationale", "evidence_references", "confidence", "completed_at", "independence_attestation"}
REVIEW_FIELDS = {"reviewer_id", "label", "rationale", "evidence_references", "confidence", "completed_at", "independence_attestation"}
REVIEWER_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{3,128}$")


def _validate_staged_packet(staged: object, fixture: dict) -> tuple[list[str], list[str], set[str]]:
    errors = []
    disagreements = []
    reviewer_ids_by_slot = [set(), set()]
    if not isinstance(staged, dict):
        return ["staged packet must be a JSON object"], disagreements, set()
    required_top = {"schema_version", "benchmark_id", "status", "fixture_manifest_sha256", "cases", "blinding", "custody", "safety", "freeze"}
    if set(staged) != required_top:
        errors.append("staged packet top-level fields are not canonical")
    if staged.get("schema_version") != "1.0" or staged.get("benchmark_id") != "r15d-semantic-source-facts-v2":
        errors.append("staged packet benchmark identity is invalid")
    if staged.get("status") != "primary_reviews_received_pending_consensus":
        errors.append("staged packet must remain pending consensus")
    if staged.get("fixture_manifest_sha256") != fixture.get("_artifact_manifest_sha256"):
        errors.append("staged packet fixture manifest digest does not match the verified artifact")
    blinding = staged.get("blinding")
    blinding_fields = {"expected_labels_omitted", "model_outputs_omitted", "primary_reviews_completed_independently", "v1_answer_key_non_exposure_attested"}
    if not isinstance(blinding, dict) or set(blinding) != blinding_fields or any(blinding.get(k) is not True for k in blinding_fields):
        errors.append("staged packet blinding invariants must all remain true")
    custody = staged.get("custody")
    custody_fields = {"custodian_id", "primary_reviewer_identities_verified_out_of_band", "identity_verification_is_custodian_attestation_not_cryptographic_proof"}
    if not isinstance(custody, dict) or set(custody) != custody_fields or not isinstance(custody.get("custodian_id"), str) or len(custody.get("custodian_id", "").strip()) < 3 or custody.get("primary_reviewer_identities_verified_out_of_band") is not True or custody.get("identity_verification_is_custodian_attestation_not_cryptographic_proof") is not True:
        errors.append("staged packet must carry the exact custodian identity-verification attestation")
    safety = staged.get("safety")
    if not isinstance(safety, dict) or set(safety) != {"candidate_code_execution", "wallet_access", "transaction_signing", "deployment", "live_trading", "paid_inference", "cloud_inference"} or any(value is not False for value in safety.values()):
        errors.append("staged packet safety controls must all remain disabled")
    freeze = staged.get("freeze")
    if not isinstance(freeze, dict) or freeze != {"ground_truth_frozen": False, "frozen_at": None, "model_inference_authorized": False}:
        errors.append("staged packet must remain unfrozen and model inference unauthorized")

    fixture_hash = staged.get("fixture_manifest_sha256")
    cases = staged.get("cases")
    if not isinstance(cases, list) or len(cases) != 6:
        return errors + ["staged packet must contain exactly six cases"], disagreements, set()
    fixture_cases = {case["id"]: case for case in fixture["cases"]}
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(ids) != 6 or len(ids) != len(cases) or not all(isinstance(x, str) for x in ids) or set(ids) != set(fixture_cases):
        errors.append("staged packet case IDs must match all six canonical v2 cases exactly once")
        return errors, disagreements, set()

    for case in cases:
        case_id = case["id"]
        source = fixture_cases[case_id]
        case_fields = {
            "id", "repository", "commit_sha", "tree_sha", "path", "git_blob_sha1",
            "line_start", "line_end", "excerpt_sha256", "proposition", "boundary",
            "reviewers", "disagreement", "third_adjudicator", "consensus",
        }
        if set(case) != case_fields:
            errors.append(f"{case_id}: staged case fields are not canonical")
            continue
        for key in ("repository", "commit_sha", "tree_sha", "path", "git_blob_sha1", "line_start", "line_end", "excerpt_sha256", "proposition", "boundary"):
            if case.get(key) != source.get(key):
                errors.append(f"{case_id}: staged source field differs from verified fixture: {key}")
        reviewers = case.get("reviewers")
        if not isinstance(reviewers, list) or len(reviewers) != 2:
            errors.append(f"{case_id}: exactly two primary reviews are required")
            continue
        valid = []
        pin = {key: source[key] for key in ("repository", "commit_sha", "tree_sha", "path", "git_blob_sha1", "line_start", "line_end", "excerpt_sha256")}
        for index, review in enumerate(reviewers):
            if not isinstance(review, dict) or set(review) != REVIEW_FIELDS:
                errors.append(f"{case_id}: primary review {index + 1} shape is invalid")
                valid.append(False)
                continue
            if not isinstance(review.get("reviewer_id"), str) or not review["reviewer_id"].strip():
                errors.append(f"{case_id}: primary reviewer ID is missing")
                valid.append(False)
                continue
            if not isinstance(review.get("label"), str) or review["label"] not in ALLOWED:
                errors.append(f"{case_id}: primary review label is invalid")
                valid.append(False)
            if not isinstance(review.get("rationale"), str) or not review["rationale"].strip():
                errors.append(f"{case_id}: primary review rationale is missing")
                valid.append(False)
            if not _valid_evidence(review.get("evidence_references"), pin):
                errors.append(f"{case_id}: primary evidence references do not match the exact pinned excerpt")
                valid.append(False)
            confidence = review.get("confidence")
            if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
                errors.append(f"{case_id}: primary confidence is invalid")
                valid.append(False)
            if not _valid_timestamp(review.get("completed_at")) or review.get("independence_attestation") is not True:
                errors.append(f"{case_id}: primary timestamp or independence attestation is invalid")
                valid.append(False)
            else:
                valid.append(True)
            reviewer_ids_by_slot[index].add(review["reviewer_id"].strip())
        if not all(valid):
            continue
        if reviewers[0]["reviewer_id"].strip() == reviewers[1]["reviewer_id"].strip():
            errors.append(f"{case_id}: primary reviewer IDs must differ")
        disagreement = reviewers[0]["label"] != reviewers[1]["label"]
        if case.get("disagreement") is not disagreement:
            errors.append(f"{case_id}: disagreement flag does not match primary labels")
        if disagreement:
            disagreements.append(case_id)
        third = case.get("third_adjudicator")
        expected_third = {
            "reviewer_id": None, "label": None, "rationale": None,
            "evidence_references": [], "confidence": None, "completed_at": None,
            "triggered": disagreement, "independence_attestation": None,
        }
        if third != expected_third:
            errors.append(f"{case_id}: third-adjudicator slot must remain blank with a correct trigger")
        consensus = case.get("consensus")
        if consensus != {"status": "pending", "label": None, "rationale": None, "disagreement": disagreement}:
            errors.append(f"{case_id}: consensus must remain pending and reflect disagreement")

    for index, identities in enumerate(reviewer_ids_by_slot):
        if len(identities) != 1:
            errors.append(f"primary reviewer slot {index + 1} must retain one stable identity across all six cases")
    if reviewer_ids_by_slot[0] & reviewer_ids_by_slot[1]:
        errors.append("primary reviewer identities must be globally distinct")
    return errors, disagreements, reviewer_ids_by_slot[0] | reviewer_ids_by_slot[1]


def validate_third_submission(fixture: dict, staged: object, submission: object) -> dict:
    errors, disagreements, primary_ids = _validate_staged_packet(staged, fixture)
    if errors:
        return {"valid": False, "disagreement_cases": disagreements, "errors": ["staged packet: " + error for error in errors]}
    if not disagreements:
        return {"valid": False, "disagreement_cases": [], "errors": ["no disagreement exists; third adjudication is not permitted or needed"]}
    if not isinstance(submission, dict) or set(submission) != TOP_FIELDS:
        return {"valid": False, "disagreement_cases": disagreements, "errors": ["third submission must contain exactly the schema-defined top-level fields"]}
    if submission.get("schema_version") != "1.0" or submission.get("benchmark_id") != "r15d-semantic-source-facts-v2":
        errors.append("third submission schema version or benchmark ID is invalid")
    reviewer_id = submission.get("reviewer_id")
    if not isinstance(reviewer_id, str) or not REVIEWER_ID_RE.fullmatch(reviewer_id) or reviewer_id != reviewer_id.strip():
        errors.append("third reviewer ID must be normalized and stable")
    elif reviewer_id in primary_ids:
        errors.append("third adjudicator must be distinct from both primary reviewers")
    if not _valid_timestamp(submission.get("submitted_at")):
        errors.append("third submitted_at timestamp is invalid")
    attestations = submission.get("attestations")
    if not isinstance(attestations, dict) or set(attestations) != ATTESTATION_FIELDS:
        errors.append("third-adjudicator attestations have an invalid shape")
    else:
        for field in ("independent_review", "model_outputs_not_seen", "primary_reviews_seen", "v1_answer_key_not_seen", "v1_labels_not_consulted", "conflicts_disclosed"):
            if attestations.get(field) is not True:
                errors.append(f"required third-adjudicator attestation must be true: {field}")
        if not isinstance(attestations.get("conflict_statement"), str) or len(attestations["conflict_statement"].strip()) < 3:
            errors.append("third-adjudicator conflict_statement must disclose none or describe the conflict")
    cases = submission.get("cases")
    if not isinstance(cases, list) or len(cases) != len(disagreements):
        errors.append("third submission must contain exactly the staged disagreement cases")
        cases = cases if isinstance(cases, list) else []
    ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    if len(ids) != len(cases) or not all(isinstance(x, str) for x in ids) or set(ids) != set(disagreements) or len(set(ids)) != len(disagreements):
        errors.append("third submission case IDs must match every disagreement exactly once")
    fixture_cases = {case["id"]: case for case in fixture["cases"]}
    for case in cases:
        case_id = case.get("case_id", "<invalid>") if isinstance(case, dict) else "<invalid>"
        if not isinstance(case, dict) or set(case) != THIRD_CASE_FIELDS:
            errors.append(f"{case_id}: third case shape is invalid")
            continue
        if case_id not in disagreements:
            errors.append(f"{case_id}: third review is only permitted for a disagreement")
            continue
        source = fixture_cases[case_id]
        pin = {key: source[key] for key in ("repository", "commit_sha", "tree_sha", "path", "git_blob_sha1", "line_start", "line_end", "excerpt_sha256")}
        if case.get("source_pin") != pin:
            errors.append(f"{case_id}: third source pin differs from the v2 fixture")
        if not isinstance(case.get("label"), str) or case["label"] not in ALLOWED:
            errors.append(f"{case_id}: third label is invalid")
        if not isinstance(case.get("rationale"), str) or not case["rationale"].strip():
            errors.append(f"{case_id}: third rationale is required")
        if not _valid_evidence(case.get("evidence_references"), pin):
            errors.append(f"{case_id}: third evidence references do not match exact pinned excerpt")
        confidence = case.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            errors.append(f"{case_id}: third confidence is invalid")
        if not _valid_timestamp(case.get("completed_at")) or case.get("independence_attestation") is not True:
            errors.append(f"{case_id}: third timestamp or independence attestation is invalid")
    return {
        "valid": not errors,
        "reviewer_id": reviewer_id if isinstance(reviewer_id, str) else None,
        "case_count": len(cases),
        "disagreement_cases": disagreements,
        "errors": errors,
        "identity_verification": "not_performed_by_validator",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a private R15D v2 third-adjudicator bundle against staged disagreements.")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--staged-packet", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    args = parser.parse_args()
    try:
        fixture = load_fixture_bundle(args.fixture)
        staged = json.loads(args.staged_packet.read_bytes().decode("utf-8"), object_pairs_hook=_unique_object)
        submission = json.loads(args.submission.read_bytes().decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2))
        raise SystemExit(1)
    result = validate_third_submission(fixture, staged, submission)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
