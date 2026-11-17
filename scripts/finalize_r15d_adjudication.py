from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from scripts.merge_r15d_primary_reviews import _read_json
from scripts.validate_r15d_adjudication import validate
from scripts.validate_r15d_third_adjudication_submission import validate_third_submission
from scripts.verify_r15d_primary_merge import verify_primary_merge


def _atomic_create_no_overwrite(output_path: Path, payload: bytes) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent)
    temporary_path = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary_path, output_path)
        try:
            directory_fd = os.open(output_path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
        if output_path.read_bytes() != payload:
            raise OSError("final adjudication packet differs from validated payload")
    finally:
        temporary_path.unlink(missing_ok=True)


def finalize_adjudication(
    reviewer_a_path: Path,
    reviewer_b_path: Path,
    staged_packet_path: Path,
    output_path: Path,
    custodian_id: str,
    primary_identity_verified: bool,
    third_submission_path: Path | None = None,
    third_identity_verified: bool = False,
    expected_staged_sha256: str | None = None,
) -> dict:
    if output_path.resolve() in {reviewer_a_path.resolve(), reviewer_b_path.resolve(), staged_packet_path.resolve()}:
        raise ValueError("final adjudication output must be a new file separate from all source inputs")
    primary_verification = verify_primary_merge(
        reviewer_a_path, reviewer_b_path, staged_packet_path, custodian_id,
        primary_identity_verified, expected_sha256=expected_staged_sha256,
    )
    staged = _read_json(staged_packet_path, "staged primary packet")
    disagreements = primary_verification["disagreement_cases"]
    third_by_id = {}

    if disagreements:
        if third_submission_path is None:
            raise ValueError("a private third-adjudicator submission is required for every disagreement")
        if not third_identity_verified:
            raise ValueError("custodian must verify the third adjudicator identity out of band")
        third_submission = _read_json(third_submission_path, "third-adjudicator submission")
        third_result = validate_third_submission(staged, third_submission)
        if not third_result["valid"]:
            raise ValueError("third-adjudicator submission failed validation: " + "; ".join(third_result["errors"]))
        third_by_id = {case["case_id"]: case for case in third_submission["cases"]}
    elif third_submission_path is not None:
        raise ValueError("third-adjudicator submission is not permitted when there are no primary-review disagreements")

    finalized = json.loads(json.dumps(staged))
    for case in finalized["cases"]:
        case_id = case["id"]
        primary_a, primary_b = case["reviewers"]
        disagreement = primary_a["label"] != primary_b["label"]
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
                "label": primary_a["label"],
                "rationale": (
                    "Both independent primary reviewers selected the same label; "
                    "consensus follows their unanimous label. No third adjudication was required."
                ),
                "disagreement": False,
            }

    validation = validate(finalized, require_complete=True)
    if not validation["valid"] or not validation["complete"]:
        raise ValueError("final adjudication packet failed complete validation: " + "; ".join(validation["errors"]))
    if finalized["freeze"]["ground_truth_frozen"] is not False or finalized["freeze"]["model_inference_authorized"] is not False:
        raise ValueError("final adjudication packet must remain unfrozen and model inference unauthorized")
    payload = (json.dumps(finalized, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _atomic_create_no_overwrite(output_path, payload)
    import hashlib
    return {
        "valid_complete_adjudication": True,
        "output_path": str(output_path),
        "output_sha256": hashlib.sha256(payload).hexdigest(),
        "case_count": validation["case_count"],
        "completed_cases": validation["completed_cases"],
        "third_adjudication_cases": disagreements,
        "ground_truth_frozen": False,
        "model_inference_authorized": False,
        "custodian_id": custodian_id.strip(),
        "identity_verification": "custodian_attested_out_of_band_not_cryptographically_proven_by_this_script",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble complete R15D adjudication from verified private primary and disagreement-only third reviews. Does not freeze or authorize inference.")
    parser.add_argument("--reviewer-a", type=Path, required=True)
    parser.add_argument("--reviewer-b", type=Path, required=True)
    parser.add_argument("--staged-packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--custodian-id", required=True)
    parser.add_argument("--primary-identity-verification-complete", action="store_true")
    parser.add_argument("--third-submission", type=Path)
    parser.add_argument("--third-identity-verification-complete", action="store_true")
    parser.add_argument("--expected-staged-sha256")
    args = parser.parse_args()
    result = finalize_adjudication(
        args.reviewer_a, args.reviewer_b, args.staged_packet, args.output,
        args.custodian_id, args.primary_identity_verification_complete,
        args.third_submission, args.third_identity_verification_complete,
        args.expected_staged_sha256,
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
