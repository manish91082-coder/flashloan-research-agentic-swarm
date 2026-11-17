from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from scripts.validate_r15d_adjudication import _valid_timestamp
from scripts.validate_r15d_review_submission import _unique_object
from scripts.validate_r15d_v2_review_submission import load_fixture_bundle, validate_submission
from scripts.validate_r15d_v2_third_submission import validate_third_submission

ROOT = Path(__file__).resolve().parents[1]
IDENTITY_METHODS = {"private_video_check", "institutional_identity_check", "in_person_check", "other_private_method"}


def _read_submission(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    if not isinstance(value, dict):
        raise ValueError("reviewer submission must be a JSON object")
    return value, raw


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
            raise OSError("published custody receipt differs from validated bytes")
    finally:
        temporary.unlink(missing_ok=True)


def create_intake_receipt(
    fixture_path: Path,
    submission_path: Path,
    output_path: Path,
    reviewer_slot: str,
    custodian_id: str,
    custodian_verified_at: str,
    identity_method: str,
    identity_verification_complete: bool,
    staged_packet_path: Path | None = None,
) -> dict:
    if not identity_verification_complete:
        raise ValueError("custodian must complete out-of-band identity verification before issuing a receipt")
    if reviewer_slot not in {"primary_a", "primary_b", "third_adjudicator"}:
        raise ValueError("reviewer_slot must be primary_a, primary_b or third_adjudicator")
    if not isinstance(custodian_id, str) or len(custodian_id.strip()) < 3:
        raise ValueError("custodian_id must be a stable pseudonymous identifier")
    if not _valid_timestamp(custodian_verified_at):
        raise ValueError("custodian_verified_at must be a timezone-aware UTC ISO-8601 timestamp")
    if identity_method not in IDENTITY_METHODS:
        raise ValueError("identity_method is not an approved private verification method")

    paths = [submission_path.resolve(), output_path.resolve()]
    if fixture_path.exists():
        paths.append(fixture_path.resolve())
    if staged_packet_path is not None:
        paths.append(staged_packet_path.resolve())
    repository_root = ROOT.resolve()
    for path in paths:
        if path == repository_root or repository_root in path.parents:
            raise ValueError("private submissions, staged packets and custody receipts must remain outside the public repository")
    if len(set(paths)) != len(paths):
        raise ValueError("fixture, private submission, staged packet and receipt output must be separate paths")

    fixture = load_fixture_bundle(fixture_path)
    submission, raw = _read_submission(submission_path)
    if reviewer_slot == "third_adjudicator":
        if staged_packet_path is None:
            raise ValueError("third-adjudicator receipt requires the staged primary packet")
        staged = json.loads(staged_packet_path.read_bytes().decode("utf-8"), object_pairs_hook=_unique_object)
        validation = validate_third_submission(fixture, staged, submission)
        if not validation["valid"]:
            raise ValueError("third-adjudicator submission failed validation: " + "; ".join(validation["errors"]))
        attestation = submission["attestations"]
    else:
        if staged_packet_path is not None:
            raise ValueError("primary reviewer receipt must not include a staged packet")
        validation = validate_submission(submission, fixture)
        if not validation["valid"]:
            raise ValueError("primary reviewer submission failed validation: " + "; ".join(validation["errors"]))
        attestation = submission["attestations"]

    receipt = {
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
            "v1_answer_key_not_seen": attestation["v1_answer_key_not_seen"],
            "v1_labels_not_consulted": attestation["v1_labels_not_consulted"],
            "conflicts_disclosed": attestation["conflicts_disclosed"],
        },
        "payload_content_included": False,
        "labels_included": False,
        "rationales_included": False,
        "public_repository_storage_prohibited": True,
    }
    payload = (json.dumps(receipt, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _atomic_create(output_path, payload)
    return {
        "valid_receipt": True,
        "receipt_path": str(output_path),
        "receipt_sha256": hashlib.sha256(payload).hexdigest(),
        "submission_sha256": receipt["submission_sha256"],
        "reviewer_slot": reviewer_slot,
        "reviewer_id": receipt["reviewer_id"],
        "labels_or_rationales_included": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a private metadata-only receipt for a validated R15D v2 reviewer submission.")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviewer-slot", choices=["primary_a", "primary_b", "third_adjudicator"], required=True)
    parser.add_argument("--custodian-id", required=True)
    parser.add_argument("--custodian-verified-at", required=True)
    parser.add_argument("--identity-method", choices=sorted(IDENTITY_METHODS), required=True)
    parser.add_argument("--identity-verification-complete", action="store_true")
    parser.add_argument("--staged-packet", type=Path)
    args = parser.parse_args()
    result = create_intake_receipt(
        args.fixture, args.submission, args.output, args.reviewer_slot,
        args.custodian_id, args.custodian_verified_at, args.identity_method,
        args.identity_verification_complete, args.staged_packet,
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
