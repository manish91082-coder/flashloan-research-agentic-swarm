from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from scripts.merge_r15d_v2_primary_reviews import _read_strict
from scripts.validate_r15d_v2_adjudication import validate_final_packet
from scripts.validate_r15d_v2_review_submission import load_fixture_bundle
from scripts.validate_r15d_v2_third_submission import validate_third_submission
from scripts.verify_r15d_v2_intake_receipt import verify_intake_receipt
from scripts.verify_r15d_v2_primary_merge import verify_primary_merge


def _atomic_create(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
        if path.read_bytes() != payload:
            raise OSError("final v2 adjudication bytes differ from validated payload")
    finally:
        temporary.unlink(missing_ok=True)


def finalize_adjudication(
    fixture_path: Path,
    reviewer_a_path: Path,
    reviewer_b_path: Path,
    receipt_a_path: Path,
    receipt_b_path: Path,
    staged_packet_path: Path,
    output_path: Path,
    custodian_id: str,
    primary_identity_verified: bool,
    third_submission_path: Path | None = None,
    third_receipt_path: Path | None = None,
    third_identity_verified: bool = False,
    expected_staged_sha256: str | None = None,
) -> dict:
    inputs = {fixture_path.resolve(), reviewer_a_path.resolve(), reviewer_b_path.resolve(), receipt_a_path.resolve(), receipt_b_path.resolve(), staged_packet_path.resolve()}
    if output_path.resolve() in inputs:
        raise ValueError("final adjudication output must be separate from every source input")
    primary_verification = verify_primary_merge(
        fixture_path, reviewer_a_path, reviewer_b_path, receipt_a_path, receipt_b_path, staged_packet_path,
        custodian_id, primary_identity_verified, expected_sha256=expected_staged_sha256,
    )
    fixture = load_fixture_bundle(fixture_path)
    staged = _read_strict(staged_packet_path, "staged primary packet")
    disagreements = primary_verification["disagreement_cases"]
    third_by_id = {}
    third_attestations = None

    if disagreements:
        if third_submission_path is None:
            raise ValueError("a private third-adjudicator bundle is required for every disagreement")
        if third_receipt_path is None:
            raise ValueError("a verified third-adjudicator custody receipt is required for every disagreement")
        if not third_identity_verified:
            raise ValueError("custodian must verify third-adjudicator identity out of band")
        third_submission = _read_strict(third_submission_path, "third-adjudicator bundle")
        third_result = validate_third_submission(fixture, staged, third_submission)
        if not third_result["valid"]:
            raise ValueError("third-adjudicator bundle failed validation: " + "; ".join(third_result["errors"]))
        third_receipt = verify_intake_receipt(fixture_path, third_submission_path, third_receipt_path, "third_adjudicator", custodian_id, staged_packet_path)
        third_by_id = {case["case_id"]: case for case in third_submission["cases"]}
        third_attestations = {
            "reviewer_id": third_submission["reviewer_id"],
            **{key: third_submission["attestations"][key] for key in (
                "independent_review", "model_outputs_not_seen", "primary_reviews_seen",
                "v1_answer_key_not_seen", "v1_labels_not_consulted", "conflicts_disclosed", "conflict_statement",
            )},
        }
    elif third_submission_path is not None or third_receipt_path is not None:
        raise ValueError("third-adjudicator submission or receipt is not permitted when no primary disagreement exists")

    final_packet = json.loads(json.dumps(staged))
    final_packet["status"] = "complete_adjudication_pending_freeze"
    final_packet["third_reviewer_attestations"] = third_attestations
    final_packet["custody"]["third_adjudicator_identity_verified_out_of_band"] = bool(third_submission_path)
    final_packet["custody_receipts"]["third_adjudicator_receipt_sha256"] = third_receipt["receipt_sha256"] if third_submission_path else None
    for case in final_packet["cases"]:
        case_id = case["id"]
        reviewer_a, reviewer_b = case["reviewers"]
        disagreement = reviewer_a["label"] != reviewer_b["label"]
        if disagreement:
            record = third_by_id[case_id]
            case["third_adjudicator"] = {
                "reviewer_id": third_submission["reviewer_id"],
                "label": record["label"],
                "rationale": record["rationale"],
                "evidence_references": list(record["evidence_references"]),
                "confidence": record["confidence"],
                "completed_at": record["completed_at"],
                "triggered": True,
                "independence_attestation": True,
            }
            case["consensus"] = {
                "status": "adjudicated",
                "label": record["label"],
                "rationale": record["rationale"],
                "disagreement": True,
            }
        else:
            case["consensus"] = {
                "status": "adjudicated",
                "label": reviewer_a["label"],
                "rationale": (
                    "Both independent primary reviewers selected the same label; "
                    "consensus follows their unanimous label. No third adjudication was required."
                ),
                "disagreement": False,
            }

    validation = validate_final_packet(fixture, final_packet)
    if not validation["valid"] or not validation["complete"]:
        raise ValueError("final v2 adjudication packet failed complete validation: " + "; ".join(validation["errors"]))
    if final_packet["freeze"] != {"ground_truth_frozen": False, "frozen_at": None, "model_inference_authorized": False}:
        raise ValueError("final v2 adjudication must remain unfrozen and model inference unauthorized")
    payload = (json.dumps(final_packet, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _atomic_create(output_path, payload)
    return {
        "valid_complete_adjudication": True,
        "output_path": str(output_path),
        "output_sha256": hashlib.sha256(payload).hexdigest(),
        "case_count": validation["case_count"],
        "completed_cases": validation["completed_cases"],
        "disagreement_cases": disagreements,
        "ground_truth_frozen": False,
        "model_inference_authorized": False,
        "custodian_id": custodian_id.strip(),
        "identity_verification": "custodian_attested_out_of_band_not_cryptographically_proven",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize complete R15D v2 consensus from verified primary and disagreement-only third reviews. Does not freeze.")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--reviewer-a", type=Path, required=True)
    parser.add_argument("--reviewer-b", type=Path, required=True)
    parser.add_argument("--receipt-a", type=Path, required=True)
    parser.add_argument("--receipt-b", type=Path, required=True)
    parser.add_argument("--staged-packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--custodian-id", required=True)
    parser.add_argument("--primary-identity-verification-complete", action="store_true")
    parser.add_argument("--third-submission", type=Path)
    parser.add_argument("--third-receipt", type=Path)
    parser.add_argument("--third-identity-verification-complete", action="store_true")
    parser.add_argument("--expected-staged-sha256")
    args = parser.parse_args()
    result = finalize_adjudication(
        args.fixture, args.reviewer_a, args.reviewer_b, args.receipt_a, args.receipt_b, args.staged_packet,
        args.output, args.custodian_id, args.primary_identity_verification_complete,
        args.third_submission, args.third_receipt, args.third_identity_verification_complete,
        args.expected_staged_sha256,
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
