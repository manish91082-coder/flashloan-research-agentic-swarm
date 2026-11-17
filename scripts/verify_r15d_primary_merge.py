from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from scripts.merge_r15d_primary_reviews import _read_json
from scripts.validate_r15d_adjudication import DEFAULT_PACKET, EXPECTED_CASES, validate
from scripts.validate_r15d_review_submission import validate_submission


def verify_primary_merge(
    reviewer_a_path: Path,
    reviewer_b_path: Path,
    merged_packet_path: Path,
    custodian_id: str,
    identity_verification_complete: bool,
    template_path: Path = DEFAULT_PACKET,
    expected_sha256: str | None = None,
) -> dict:
    if not identity_verification_complete:
        raise ValueError("custodian must attest that both reviewer identities were verified out of band")
    if not isinstance(custodian_id, str) or len(custodian_id.strip()) < 3:
        raise ValueError("custodian_id must be a stable non-empty identifier")
    resolved = [reviewer_a_path.resolve(), reviewer_b_path.resolve(), merged_packet_path.resolve(), template_path.resolve()]
    if resolved[0] == resolved[1] or resolved[2] in resolved[:2] or resolved[2] == resolved[3]:
        raise ValueError("reviewer inputs, template and staged packet must be separate files")

    template = _read_json(template_path, "canonical blank packet")
    template_result = validate(template, require_complete=False)
    if not template_result["valid"] or template_result["completed_cases"] != 0:
        raise ValueError("canonical template is not the unchanged valid blank R15D packet")
    bundle_a = _read_json(reviewer_a_path, "reviewer A submission")
    bundle_b = _read_json(reviewer_b_path, "reviewer B submission")
    result_a = validate_submission(bundle_a)
    result_b = validate_submission(bundle_b)
    if not result_a["valid"]:
        raise ValueError("reviewer A submission failed validation: " + "; ".join(result_a["errors"]))
    if not result_b["valid"]:
        raise ValueError("reviewer B submission failed validation: " + "; ".join(result_b["errors"]))
    if result_a["reviewer_id"] == result_b["reviewer_id"]:
        raise ValueError("primary reviewer identities must be globally distinct")

    by_id_a = {case["case_id"]: case for case in bundle_a["cases"]}
    by_id_b = {case["case_id"]: case for case in bundle_b["cases"]}
    if set(by_id_a) != EXPECTED_CASES or set(by_id_b) != EXPECTED_CASES:
        raise ValueError("both private submissions must contain exactly the six canonical cases")

    expected = json.loads(json.dumps(template))
    disagreements = []
    for case in expected["cases"]:
        case_id = case["id"]
        records = []
        for bundle, source_case in ((bundle_a, by_id_a[case_id]), (bundle_b, by_id_b[case_id])):
            records.append({
                "reviewer_id": bundle["reviewer_id"],
                "label": source_case["label"],
                "rationale": source_case["rationale"],
                "evidence_references": list(source_case["evidence_references"]),
                "confidence": source_case["confidence"],
                "completed_at": source_case["completed_at"],
                "independence_attestation": True,
            })
        case["reviewers"] = records
        disagreement = records[0]["label"] != records[1]["label"]
        case["consensus"] = {"status": "pending", "label": None, "rationale": None, "disagreement": disagreement}
        case["third_adjudicator"]["triggered"] = disagreement
        if disagreement:
            disagreements.append(case_id)

    expected_bytes = (json.dumps(expected, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        actual_bytes = merged_packet_path.read_bytes()
    except OSError as exc:
        raise ValueError(f"unable to read staged primary-review packet: {exc}") from exc
    if actual_bytes != expected_bytes:
        raise ValueError("staged packet does not exactly match the canonical blank template plus the two validated primary submissions")
    digest = hashlib.sha256(actual_bytes).hexdigest()
    if expected_sha256 is not None:
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise ValueError("expected_sha256 must be a lowercase 64-character SHA-256 digest")
        if digest != expected_sha256:
            raise ValueError("staged packet SHA-256 does not match expected digest")
    return {
        "valid": True,
        "staged_packet_sha256": digest,
        "case_count": len(expected["cases"]),
        "disagreement_cases": disagreements,
        "third_adjudication_required": disagreements,
        "ground_truth_frozen": False,
        "model_inference_authorized": False,
        "custodian_id": custodian_id.strip(),
        "identity_verification": "custodian_attested_out_of_band_not_cryptographically_proven_by_this_script",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Independently verify an R15D staged primary-review merge against its two private source bundles.")
    parser.add_argument("--reviewer-a", type=Path, required=True)
    parser.add_argument("--reviewer-b", type=Path, required=True)
    parser.add_argument("--merged-packet", type=Path, required=True)
    parser.add_argument("--custodian-id", required=True)
    parser.add_argument("--identity-verification-complete", action="store_true")
    parser.add_argument("--template", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    result = verify_primary_merge(
        args.reviewer_a, args.reviewer_b, args.merged_packet, args.custodian_id,
        args.identity_verification_complete, args.template, args.expected_sha256,
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
