from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts.validate_r15d_adjudication import _valid_timestamp
from scripts.validate_r15d_review_submission import _unique_object
from scripts.validate_r15d_v2_review_submission import ALLOWED, _valid_evidence, load_fixture_bundle

REVIEW_FIELDS = {"reviewer_id", "label", "rationale", "evidence_references", "confidence", "completed_at", "independence_attestation"}
THIRD_FIELDS = {"reviewer_id", "label", "rationale", "evidence_references", "confidence", "completed_at", "triggered", "independence_attestation"}
CONSENSUS_FIELDS = {"status", "label", "rationale", "disagreement"}
FINAL_STATUS = "complete_adjudication_pending_freeze"
UNANIMOUS_RATIONALE = (
    "Both independent primary reviewers selected the same label; "
    "consensus follows their unanimous label. No third adjudication was required."
)


def validate_final_packet(fixture: dict, packet: object) -> dict:
    errors = []
    if not isinstance(packet, dict):
        return {"valid": False, "complete": False, "case_count": 0, "completed_cases": 0, "errors": ["final packet must be a JSON object"]}
    expected_top = {"schema_version", "benchmark_id", "status", "fixture_manifest_sha256", "cases", "primary_reviewer_attestations", "third_reviewer_attestations", "custody_receipts", "blinding", "custody", "safety", "freeze"}
    if set(packet) != expected_top:
        errors.append("final packet top-level fields are not canonical")
    if packet.get("schema_version") != "1.0" or packet.get("benchmark_id") != "r15d-semantic-source-facts-v2" or packet.get("status") != FINAL_STATUS:
        errors.append("final packet benchmark identity or status is invalid")
    if packet.get("fixture_manifest_sha256") != fixture.get("_artifact_manifest_sha256"):
        errors.append("final packet fixture digest does not match the verified label-free artifact")

    blinding = packet.get("blinding")
    blinding_fields = {"expected_labels_omitted", "model_outputs_omitted", "primary_reviews_completed_independently", "v1_answer_key_non_exposure_attested"}
    if not isinstance(blinding, dict) or set(blinding) != blinding_fields or any(blinding.get(k) is not True for k in blinding_fields):
        errors.append("final packet blinding invariants must all remain true")
    custody = packet.get("custody")
    custody_fields = {"custodian_id", "primary_reviewer_identities_verified_out_of_band", "third_adjudicator_identity_verified_out_of_band", "identity_verification_is_custodian_attestation_not_cryptographic_proof"}
    if not isinstance(custody, dict) or set(custody) != custody_fields or not isinstance(custody.get("custodian_id"), str) or len(custody.get("custodian_id", "").strip()) < 3 or custody.get("primary_reviewer_identities_verified_out_of_band") is not True or custody.get("identity_verification_is_custodian_attestation_not_cryptographic_proof") is not True:
        errors.append("final packet custodian identity attestation is invalid")
    safety = packet.get("safety")
    safety_fields = {"candidate_code_execution", "wallet_access", "transaction_signing", "deployment", "live_trading", "paid_inference", "cloud_inference"}
    if not isinstance(safety, dict) or set(safety) != safety_fields or any(value is not False for value in safety.values()):
        errors.append("final packet safety controls must all remain disabled")
    custody_receipts = packet.get("custody_receipts")
    receipt_fields = {"primary_a_receipt_sha256", "primary_b_receipt_sha256", "third_adjudicator_receipt_sha256"}
    if not isinstance(custody_receipts, dict) or set(custody_receipts) != receipt_fields or not all(isinstance(custody_receipts.get(k), str) and re.fullmatch(r"[0-9a-f]{64}", custody_receipts[k]) for k in ("primary_a_receipt_sha256", "primary_b_receipt_sha256")):
        errors.append("final packet must preserve two valid primary custody receipt digests")
    freeze = packet.get("freeze")
    if not isinstance(freeze, dict) or freeze != {"ground_truth_frozen": False, "frozen_at": None, "model_inference_authorized": False}:
        errors.append("final adjudication packet must remain unfrozen and model inference unauthorized")

    fixture_cases = {case["id"]: case for case in fixture["cases"]}
    cases = packet.get("cases")
    if not isinstance(cases, list) or len(cases) != 6:
        return {"valid": False, "complete": False, "case_count": len(cases) if isinstance(cases, list) else 0, "completed_cases": 0, "errors": errors + ["final packet must contain exactly six cases"]}
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(ids) != len(cases) or not all(isinstance(x, str) for x in ids) or set(ids) != set(fixture_cases):
        errors.append("final packet must contain each canonical v2 case exactly once")
        return {"valid": False, "complete": False, "case_count": len(cases), "completed_cases": 0, "errors": errors}

    primary_ids_by_slot = [set(), set()]
    third_reviewer_ids = set()
    completed = 0
    for case in cases:
        case_id = case["id"]
        source = fixture_cases[case_id]
        fields = {
            "id", "repository", "commit_sha", "tree_sha", "path", "git_blob_sha1",
            "line_start", "line_end", "excerpt_sha256", "proposition", "boundary",
            "reviewers", "disagreement", "third_adjudicator", "consensus",
        }
        if set(case) != fields:
            errors.append(f"{case_id}: final case fields are not canonical")
            continue
        for key in ("repository", "commit_sha", "tree_sha", "path", "git_blob_sha1", "line_start", "line_end", "excerpt_sha256", "proposition", "boundary"):
            if case.get(key) != source.get(key):
                errors.append(f"{case_id}: source pin or proposition differs from the verified fixture: {key}")
        pin = {key: source[key] for key in ("repository", "commit_sha", "tree_sha", "path", "git_blob_sha1", "line_start", "line_end", "excerpt_sha256")}
        reviewers = case.get("reviewers")
        if not isinstance(reviewers, list) or len(reviewers) != 2:
            errors.append(f"{case_id}: exactly two primary reviews are required")
            continue
        valid_reviews = True
        for index, review in enumerate(reviewers):
            if not isinstance(review, dict) or set(review) != REVIEW_FIELDS:
                errors.append(f"{case_id}: primary review {index + 1} shape is invalid")
                valid_reviews = False
                continue
            reviewer_id = review.get("reviewer_id")
            if not isinstance(reviewer_id, str) or not reviewer_id.strip():
                errors.append(f"{case_id}: primary reviewer ID is missing")
                valid_reviews = False
            else:
                primary_ids_by_slot[index].add(reviewer_id.strip())
            if not isinstance(review.get("label"), str) or review["label"] not in ALLOWED:
                errors.append(f"{case_id}: primary label is invalid")
                valid_reviews = False
            if not isinstance(review.get("rationale"), str) or not review["rationale"].strip():
                errors.append(f"{case_id}: primary rationale is missing")
                valid_reviews = False
            if not _valid_evidence(review.get("evidence_references"), pin):
                errors.append(f"{case_id}: primary evidence references do not match exact pinned excerpt")
                valid_reviews = False
            confidence = review.get("confidence")
            if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
                errors.append(f"{case_id}: primary confidence is invalid")
                valid_reviews = False
            if not _valid_timestamp(review.get("completed_at")) or review.get("independence_attestation") is not True:
                errors.append(f"{case_id}: primary timestamp or independence attestation is invalid")
                valid_reviews = False
        if not valid_reviews:
            continue
        if reviewers[0]["reviewer_id"].strip() == reviewers[1]["reviewer_id"].strip():
            errors.append(f"{case_id}: primary reviewer identities must differ")
        disagreement = reviewers[0]["label"] != reviewers[1]["label"]
        if case.get("disagreement") is not disagreement:
            errors.append(f"{case_id}: disagreement flag differs from primary labels")
        third = case.get("third_adjudicator")
        consensus = case.get("consensus")
        if not isinstance(consensus, dict) or set(consensus) != CONSENSUS_FIELDS or consensus.get("status") != "adjudicated" or consensus.get("disagreement") is not disagreement:
            errors.append(f"{case_id}: consensus status or disagreement flag is invalid")
            continue
        if disagreement:
            if not isinstance(third, dict) or set(third) != THIRD_FIELDS or third.get("triggered") is not True:
                errors.append(f"{case_id}: a complete third adjudicator is required for disagreement")
                continue
            if not isinstance(third.get("reviewer_id"), str) or third["reviewer_id"].strip() in {reviewers[0]["reviewer_id"].strip(), reviewers[1]["reviewer_id"].strip()}:
                errors.append(f"{case_id}: third reviewer identity must differ from both primary reviewers")
            elif isinstance(third.get("reviewer_id"), str):
                third_reviewer_ids.add(third["reviewer_id"].strip())
            if not isinstance(third.get("label"), str) or third["label"] not in ALLOWED or consensus.get("label") != third.get("label"):
                errors.append(f"{case_id}: consensus label must equal the third-adjudicator label")
            if not isinstance(third.get("rationale"), str) or not third["rationale"].strip() or consensus.get("rationale") != third.get("rationale"):
                errors.append(f"{case_id}: consensus rationale must equal the third-adjudicator rationale")
            if not _valid_evidence(third.get("evidence_references"), pin):
                errors.append(f"{case_id}: third-adjudicator evidence does not match exact pinned excerpt")
            confidence = third.get("confidence")
            if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
                errors.append(f"{case_id}: third-adjudicator confidence is invalid")
            if not _valid_timestamp(third.get("completed_at")) or third.get("independence_attestation") is not True:
                errors.append(f"{case_id}: third-adjudicator timestamp or independence attestation is invalid")
        else:
            expected_third = {
                "reviewer_id": None, "label": None, "rationale": None,
                "evidence_references": [], "confidence": None, "completed_at": None,
                "triggered": False, "independence_attestation": None,
            }
            if third != expected_third:
                errors.append(f"{case_id}: unanimous case must not contain a third-adjudicator record")
            if consensus.get("label") != reviewers[0]["label"] or reviewers[0]["label"] != reviewers[1]["label"]:
                errors.append(f"{case_id}: unanimous consensus must equal both matching primary labels")
            if consensus.get("rationale") != UNANIMOUS_RATIONALE:
                errors.append(f"{case_id}: unanimous consensus rationale is not the canonical procedural rationale")
        if not any(error.startswith(f"{case_id}:") for error in errors):
            completed += 1

    for index, identities in enumerate(primary_ids_by_slot):
        if len(identities) != 1:
            errors.append(f"primary reviewer slot {index + 1} must retain one stable identity across all six cases")
    if primary_ids_by_slot[0] & primary_ids_by_slot[1]:
        errors.append("primary reviewer identities must be globally distinct")

    primary_attestations = packet.get("primary_reviewer_attestations")
    attestation_fields = {"reviewer_id", "independent_review", "model_outputs_not_seen", "other_reviews_not_seen", "v1_answer_key_not_seen", "v1_labels_not_consulted", "conflicts_disclosed", "conflict_statement"}
    if not isinstance(primary_attestations, list) or len(primary_attestations) != 2:
        errors.append("final packet must preserve exactly two primary reviewer attestation records")
    else:
        for index, attestation in enumerate(primary_attestations):
            if not isinstance(attestation, dict) or set(attestation) != attestation_fields:
                errors.append(f"primary reviewer attestation {index + 1} has an invalid shape")
                continue
            if any(attestation.get(k) is not True for k in ("independent_review", "model_outputs_not_seen", "other_reviews_not_seen", "v1_answer_key_not_seen", "v1_labels_not_consulted", "conflicts_disclosed")) or not isinstance(attestation.get("conflict_statement"), str) or len(attestation["conflict_statement"].strip()) < 3:
                errors.append(f"primary reviewer attestation {index + 1} is incomplete")
            if index < 2 and len(primary_ids_by_slot[index]) == 1 and attestation.get("reviewer_id") not in primary_ids_by_slot[index]:
                errors.append(f"primary reviewer attestation {index + 1} does not match the case records")

    has_disagreements = any(case.get("disagreement") is True for case in cases)
    if isinstance(custody_receipts, dict):
        third_receipt_digest = custody_receipts.get("third_adjudicator_receipt_sha256")
        if has_disagreements and (not isinstance(third_receipt_digest, str) or not __import__("re").fullmatch(r"[0-9a-f]{64}", third_receipt_digest)):
            errors.append("disagreement packet must preserve a verified third-adjudicator receipt digest")
        if not has_disagreements and third_receipt_digest is not None:
            errors.append("unanimous packet must not contain a third-adjudicator receipt digest")
    third_attestations = packet.get("third_reviewer_attestations")
    if has_disagreements:
        if len(third_reviewer_ids) != 1:
            errors.append("all third-adjudicated cases must retain one stable third reviewer identity")
        third_fields = {"reviewer_id", "independent_review", "model_outputs_not_seen", "primary_reviews_seen", "v1_answer_key_not_seen", "v1_labels_not_consulted", "conflicts_disclosed", "conflict_statement"}
        if not isinstance(third_attestations, dict) or set(third_attestations) != third_fields:
            errors.append("final packet must preserve the third reviewer attestation record")
        else:
            if third_attestations.get("reviewer_id") not in third_reviewer_ids:
                errors.append("third reviewer attestation identity does not match case records")
            if any(third_attestations.get(k) is not True for k in ("independent_review", "model_outputs_not_seen", "primary_reviews_seen", "v1_answer_key_not_seen", "v1_labels_not_consulted", "conflicts_disclosed")) or not isinstance(third_attestations.get("conflict_statement"), str) or len(third_attestations["conflict_statement"].strip()) < 3:
                errors.append("third reviewer attestation record is incomplete")
    elif third_attestations is not None or third_reviewer_ids:
        errors.append("unanimous packet must not contain third-review identity or attestation")
    if isinstance(custody, dict) and custody.get("third_adjudicator_identity_verified_out_of_band") is not has_disagreements:
        errors.append("custody third-adjudicator identity state does not match disagreement resolution")

    valid = not errors and completed == 6
    return {
        "valid": valid,
        "complete": valid,
        "case_count": 6,
        "completed_cases": completed,
        "disagreement_cases": [case["id"] for case in cases if case.get("disagreement") is True],
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a complete R15D v2 adjudication packet before the separate freeze step.")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    args = parser.parse_args()
    try:
        fixture = load_fixture_bundle(args.fixture)
        packet = json.loads(args.packet.read_bytes().decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"valid": False, "complete": False, "errors": [str(exc)]}, indent=2))
        raise SystemExit(1)
    result = validate_final_packet(fixture, packet)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] and result["complete"] else 1)


if __name__ == "__main__":
    main()
