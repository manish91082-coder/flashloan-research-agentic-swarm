from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from scripts.merge_r15d_v2_primary_reviews import _fixture_manifest_bytes, _read_strict, build_staged_packet
from scripts.validate_r15d_v2_review_submission import load_fixture_bundle, validate_submission


def verify_primary_merge(
    fixture_path: Path,
    reviewer_a_path: Path,
    reviewer_b_path: Path,
    staged_packet_path: Path,
    custodian_id: str,
    identity_verification_complete: bool,
    expected_sha256: str | None = None,
) -> dict:
    if not identity_verification_complete:
        raise ValueError("custodian must attest out-of-band identity verification before staged-merge verification")
    if not isinstance(custodian_id, str) or len(custodian_id.strip()) < 3:
        raise ValueError("custodian_id must be a stable identifier")
    paths = [fixture_path.resolve(), reviewer_a_path.resolve(), reviewer_b_path.resolve(), staged_packet_path.resolve()]
    if len(set(paths)) != 4:
        raise ValueError("fixture, reviewer bundles and staged packet must be separate paths")

    fixture = load_fixture_bundle(fixture_path)
    fixture_hash = hashlib.sha256(_fixture_manifest_bytes(fixture_path)).hexdigest()
    bundle_a = _read_strict(reviewer_a_path, "reviewer A bundle")
    bundle_b = _read_strict(reviewer_b_path, "reviewer B bundle")
    result_a = validate_submission(bundle_a, fixture)
    result_b = validate_submission(bundle_b, fixture)
    if not result_a["valid"]:
        raise ValueError("reviewer A bundle failed validation: " + "; ".join(result_a["errors"]))
    if not result_b["valid"]:
        raise ValueError("reviewer B bundle failed validation: " + "; ".join(result_b["errors"]))
    if result_a["reviewer_id"] == result_b["reviewer_id"]:
        raise ValueError("primary reviewer identities must be distinct")

    expected = build_staged_packet(fixture, bundle_a, bundle_b, fixture_hash, custodian_id)
    expected_bytes = (json.dumps(expected, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        actual_bytes = staged_packet_path.read_bytes()
    except OSError as exc:
        raise ValueError(f"unable to read staged packet: {exc}") from exc
    if actual_bytes != expected_bytes:
        raise ValueError("staged packet does not exactly match the canonical v2 fixture plus both validated private reviewer bundles")
    digest = hashlib.sha256(actual_bytes).hexdigest()
    if expected_sha256 is not None:
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise ValueError("expected_sha256 must be a lowercase 64-character SHA-256 digest")
        if digest != expected_sha256:
            raise ValueError("staged packet SHA-256 does not match expected digest")
    disagreements = [case["id"] for case in expected["cases"] if case["disagreement"]]
    return {
        "valid": True,
        "staged_packet_sha256": digest,
        "fixture_manifest_sha256": fixture_hash,
        "case_count": 6,
        "disagreement_cases": disagreements,
        "ground_truth_frozen": False,
        "model_inference_authorized": False,
        "custodian_id": custodian_id.strip(),
        "identity_verification": "custodian_attested_out_of_band_not_cryptographically_proven",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Independently reconstruct and verify an R15D v2 staged primary-review merge.")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--reviewer-a", type=Path, required=True)
    parser.add_argument("--reviewer-b", type=Path, required=True)
    parser.add_argument("--staged-packet", type=Path, required=True)
    parser.add_argument("--custodian-id", required=True)
    parser.add_argument("--identity-verification-complete", action="store_true")
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    result = verify_primary_merge(
        args.fixture, args.reviewer_a, args.reviewer_b, args.staged_packet,
        args.custodian_id, args.identity_verification_complete, args.expected_sha256,
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
