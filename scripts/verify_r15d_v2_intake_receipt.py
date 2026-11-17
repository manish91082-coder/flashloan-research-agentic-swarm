from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from scripts.validate_r15d_adjudication import _valid_timestamp
from scripts.validate_r15d_review_submission import _unique_object
from scripts.validate_r15d_v2_review_submission import load_fixture_bundle, validate_submission
from scripts.validate_r15d_v2_third_submission import validate_third_submission

ROOT = Path(__file__).resolve().parents[1]


def verify_intake_receipt(
    fixture_path: Path,
    submission_path: Path,
    receipt_path: Path,
    reviewer_slot: str,
    custodian_id: str,
    staged_packet_path: Path | None = None,
    expected_receipt_sha256: str | None = None,
) -> dict:
    if reviewer_slot not in {"primary_a", "primary_b", "third_adjudicator"}:
        raise ValueError("reviewer_slot must be primary_a, primary_b or third_adjudicator")
    if not isinstance(custodian_id, str) or len(custodian_id.strip()) < 3:
        raise ValueError("custodian_id must be a stable pseudonymous identifier")
    paths = [fixture_path.resolve(), submission_path.resolve(), receipt_path.resolve()]
    if staged_packet_path is not None:
        paths.append(staged_packet_path.resolve())
    if len(set(paths)) != len(paths):
        raise ValueError("fixture, submission, receipt and staged packet must be separate paths")
    for path in paths[1:]:
        if path == ROOT.resolve() or ROOT.resolve() in path.parents:
            raise ValueError("private submission, receipt and staged packet must remain outside the public repository")

    fixture = load_fixture_bundle(fixture_path)
    raw = submission_path.read_bytes()
    submission = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    if reviewer_slot == "third_adjudicator":
        if staged_packet_path is None:
            raise ValueError("third-adjudicator receipt verification requires the staged packet")
        staged = json.loads(staged_packet_path.read_bytes().decode("utf-8"), object_pairs_hook=_unique_object)
        validation = validate_third_submission(fixture, staged, submission)
        if not validation["valid"]:
            raise ValueError("third-adjudicator submission failed validation: " + "; ".join(validation["errors"]))
    else:
        if staged_packet_path is not None:
            raise ValueError("primary receipt verification must not include a staged packet")
        validation = validate_submission(submission, fixture)
        if not validation["valid"]:
            raise ValueError("primary reviewer submission failed validation: " + "; ".join(validation["errors"]))

    try:
        receipt_bytes = receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes.decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"receipt must be duplicate-free UTF-8 JSON: {exc}") from exc
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be a JSON object")
    if receipt.get("identity_verification", {}).get("status") != "verified_out_of_band":
        raise ValueError("receipt does not contain verified_out_of_band identity status")
    identity_method = receipt.get("identity_verification", {}).get("method")
    if identity_method not in {"private_video_check", "institutional_identity_check", "in_person_check", "other_private_method"}:
        raise ValueError("receipt identity verification method is invalid")
    if receipt.get("identity_verification", {}).get("cryptographic_proof") is not False:
        raise ValueError("receipt must not overstate identity verification as cryptographic proof")
    custodian_verified_at = receipt.get("custodian_verified_at")
    if not _valid_timestamp(custodian_verified_at):
        raise ValueError("receipt custodian verification timestamp is invalid")

    attestation = submission["attestations"]
    expected = {
        "schema_version": "1.0",
        "benchmark_id": "r15d-semantic-source-facts-v2",
        "reviewer_slot": reviewer_slot,
        "reviewer_id": validation["reviewer_id"],
        "submission_sha256": hashlib.sha256(raw).hexdigest(),
        "fixture_manifest_sha256": fixture["_artifact_manifest_sha256"],
        "submitted_at": submission["submitted_at"],
        "custodian_id": custodian_id.strip(),
        "custodian_verified_at": custodian_verified_at,
        "identity_verification": {
            "status": "verified_out_of_band",
            "method": identity_method,
            "cryptographic_proof": False,
        },
        "attestation_summary": {
            "independent_review": attestation["independent_review"],
            "model_outputs_not_seen": attestation["model_outputs_not_seen"],
            "other_reviews_not_seen": attestation.get("other_reviews_not_seen", False),
            "primary_reviews_seen": attestation.get("primary_reviews_seen", False),
            "v1_answer_key_not_seen": attestation["v1_answer_key_not_seen"],
            "v1_labels_not_consulted": attestation["v1_labels_not_consulted"],
            "conflicts_disclosed": attestation["conflicts_disclosed"],
        },
        "payload_content_included": False,
        "labels_included": False,
        "rationales_included": False,
        "public_repository_storage_prohibited": True,
    }
    if receipt != expected:
        raise ValueError("custody receipt does not exactly match the submitted bundle, fixture, reviewer slot and custodian")
    digest = hashlib.sha256(receipt_bytes).hexdigest()
    if expected_receipt_sha256 is not None:
        if not re.fullmatch(r"[0-9a-f]{64}", expected_receipt_sha256) or digest != expected_receipt_sha256:
            raise ValueError("receipt SHA-256 does not match expected digest")
    return {
        "valid": True,
        "receipt_sha256": digest,
        "submission_sha256": expected["submission_sha256"],
        "fixture_manifest_sha256": expected["fixture_manifest_sha256"],
        "reviewer_slot": reviewer_slot,
        "reviewer_id": expected["reviewer_id"],
        "custodian_id": custodian_id.strip(),
        "labels_or_rationales_included": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a metadata-only R15D v2 intake receipt against exact submission bytes.")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--reviewer-slot", choices=["primary_a", "primary_b", "third_adjudicator"], required=True)
    parser.add_argument("--custodian-id", required=True)
    parser.add_argument("--staged-packet", type=Path)
    parser.add_argument("--expected-receipt-sha256")
    args = parser.parse_args()
    result = verify_intake_receipt(
        args.fixture, args.submission, args.receipt, args.reviewer_slot,
        args.custodian_id, args.staged_packet, args.expected_receipt_sha256,
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
