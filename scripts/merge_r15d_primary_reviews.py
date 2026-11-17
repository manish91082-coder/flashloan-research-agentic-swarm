from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path

from scripts.validate_r15d_adjudication import DEFAULT_PACKET, EXPECTED_CASES, validate
from scripts.validate_r15d_review_submission import validate_submission, _unique_object

ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path, label: str):
    try:
        return json.loads(path.read_bytes().decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"{label} must be readable duplicate-free UTF-8 JSON: {exc}") from exc


def _atomic_create_no_overwrite(output_path: Path, payload: bytes) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent)
    temp_path = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp_path, output_path)
        try:
            directory_fd = os.open(output_path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
        if output_path.read_bytes() != payload:
            raise OSError("published primary-review merge differs from validated payload")
    finally:
        temp_path.unlink(missing_ok=True)


def merge_primary_submissions(
    reviewer_a_path: Path,
    reviewer_b_path: Path,
    output_path: Path,
    custodian_id: str,
    identity_verification_complete: bool,
    template_path: Path = DEFAULT_PACKET,
) -> dict:
    if not identity_verification_complete:
        raise ValueError("custodian must complete out-of-band identity verification before merge")
    if not isinstance(custodian_id, str) or len(custodian_id.strip()) < 3:
        raise ValueError("custodian_id must be a stable non-empty identifier")
    paths = [reviewer_a_path.resolve(), reviewer_b_path.resolve(), output_path.resolve(), template_path.resolve()]
    if paths[0] == paths[1] or paths[2] in paths[:2] or paths[2] == paths[3]:
        raise ValueError("reviewer inputs, blank template and output must be separate files")

    packet = _read_json(template_path, "canonical blank packet")
    baseline = validate(packet, require_complete=False)
    if not baseline["valid"] or baseline["completed_cases"] != 0:
        raise ValueError("canonical template must be the unchanged, valid, fully blank R15D packet")
    if packet.get("freeze", {}).get("ground_truth_frozen") is not False or packet.get("freeze", {}).get("model_inference_authorized") is not False:
        raise ValueError("canonical template must remain unfrozen with model inference unauthorized")

    bundle_a = _read_json(reviewer_a_path, "reviewer A submission")
    bundle_b = _read_json(reviewer_b_path, "reviewer B submission")
    result_a = validate_submission(bundle_a)
    result_b = validate_submission(bundle_b)
    if not result_a["valid"]:
        raise ValueError("reviewer A submission failed validation: " + "; ".join(result_a["errors"]))
    if not result_b["valid"]:
        raise ValueError("reviewer B submission failed validation: " + "; ".join(result_b["errors"]))
    if result_a["reviewer_id"] == result_b["reviewer_id"]:
        raise ValueError("the two primary reviewer identities must be distinct")

    by_id_a = {case["case_id"]: case for case in bundle_a["cases"]}
    by_id_b = {case["case_id"]: case for case in bundle_b["cases"]}
    if set(by_id_a) != EXPECTED_CASES or set(by_id_b) != EXPECTED_CASES:
        raise ValueError("both submissions must contain exactly the canonical six case IDs")

    merged = copy.deepcopy(packet)
    disagreements = []
    for case in merged["cases"]:
        case_id = case["id"]
        primary_records = []
        for bundle, review_case in ((bundle_a, by_id_a[case_id]), (bundle_b, by_id_b[case_id])):
            record = {
                "reviewer_id": bundle["reviewer_id"],
                "label": review_case["label"],
                "rationale": review_case["rationale"],
                "evidence_references": list(review_case["evidence_references"]),
                "confidence": review_case["confidence"],
                "completed_at": review_case["completed_at"],
                "independence_attestation": True,
            }
            primary_records.append(record)
        case["reviewers"] = primary_records
        disagreement = primary_records[0]["label"] != primary_records[1]["label"]
        case["consensus"] = {
            "status": "pending",
            "label": None,
            "rationale": None,
            "disagreement": disagreement,
        }
        case["third_adjudicator"]["triggered"] = disagreement
        if disagreement:
            disagreements.append(case_id)

    # This is intentionally a staged merge, not adjudicated ground truth.
    if merged["status"] != "pending_independent_review":
        raise ValueError("staged packet status must remain pending_independent_review")
    if merged["freeze"]["ground_truth_frozen"] is not False or merged["freeze"]["model_inference_authorized"] is not False:
        raise ValueError("staged packet must remain unfrozen and model inference unauthorized")
    for case in merged["cases"]:
        if len(case["reviewers"]) != 2 or any(not record["independence_attestation"] for record in case["reviewers"]):
            raise ValueError(f"{case['id']}: both primary reviewer records must be present")
        if case["third_adjudicator"]["reviewer_id"] is not None:
            raise ValueError(f"{case['id']}: third-adjudicator slot must remain blank pending independent adjudication")
    payload = (json.dumps(merged, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _atomic_create_no_overwrite(output_path, payload)
    return {
        "valid_staged_merge": True,
        "output_path": str(output_path),
        "output_sha256": hashlib.sha256(payload).hexdigest(),
        "reviewer_a_id": result_a["reviewer_id"],
        "reviewer_b_id": result_b["reviewer_id"],
        "case_count": len(merged["cases"]),
        "disagreement_cases": disagreements,
        "third_adjudication_required": disagreements,
        "ground_truth_frozen": False,
        "model_inference_authorized": False,
        "custodian_id": custodian_id.strip(),
        "identity_verification": "custodian_attested_out_of_band_not_cryptographically_proven_by_this_script",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge two privately verified R15D primary review bundles into a new staged packet. Does not adjudicate or freeze.")
    parser.add_argument("--reviewer-a", type=Path, required=True)
    parser.add_argument("--reviewer-b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--custodian-id", required=True)
    parser.add_argument("--identity-verification-complete", action="store_true", help="Custodian attestation that both reviewer identities were verified out of band.")
    parser.add_argument("--template", type=Path, default=DEFAULT_PACKET)
    args = parser.parse_args()
    result = merge_primary_submissions(
        args.reviewer_a, args.reviewer_b, args.output, args.custodian_id,
        args.identity_verification_complete, args.template,
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
