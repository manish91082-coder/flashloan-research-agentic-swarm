from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from scripts.finalize_r15d_v2_adjudication import finalize_adjudication
from scripts.validate_r15d_adjudication import _valid_timestamp
from scripts.validate_r15d_review_submission import _unique_object
from scripts.validate_r15d_v2_adjudication import validate_final_packet
from scripts.validate_r15d_v2_review_submission import load_fixture_bundle

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate_r15d_v2_adjudication.py"
SCANNER_PATH = ROOT / "scripts/scan_r15d_v2_artifact_leakage.py"
BUILDER_PATH = ROOT / "scripts/build_r15d_v2_semantic_fixtures.py"


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
            raise OSError("frozen v2 manifest differs from validated payload")
    finally:
        temporary.unlink(missing_ok=True)


def freeze_adjudication(
    packet_path: Path,
    fixture_path: Path,
    output_path: Path,
    frozen_at: str,
    reviewer_a_path: Path,
    reviewer_b_path: Path,
    receipt_a_path: Path,
    receipt_b_path: Path,
    staged_packet_path: Path,
    custodian_id: str,
    primary_identity_verified: bool,
    third_submission_path: Path | None = None,
    third_receipt_path: Path | None = None,
    third_identity_verified: bool = False,
    expected_staged_sha256: str | None = None,
) -> dict:
    if not _valid_timestamp(frozen_at):
        raise ValueError("frozen_at must be a timezone-aware UTC ISO-8601 timestamp")
    input_paths = {
        packet_path.resolve(), fixture_path.resolve(), reviewer_a_path.resolve(),
        reviewer_b_path.resolve(), receipt_a_path.resolve(), receipt_b_path.resolve(),
        staged_packet_path.resolve(),
    }
    if third_submission_path is not None:
        input_paths.add(third_submission_path.resolve())
    if third_receipt_path is not None:
        input_paths.add(third_receipt_path.resolve())
    if output_path.resolve() in input_paths or len(input_paths) != (9 if third_submission_path is not None else 7):
        raise ValueError("frozen manifest, final packet, fixture, reviewer bundles, receipts and staged packet must all be separate paths")

    try:
        packet_bytes = packet_path.read_bytes()
        packet = json.loads(packet_bytes.decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"unable to read duplicate-free final adjudication packet: {exc}") from exc

    # Reconstruct the entire final packet from the verified fixture, primary bundles,
    # mandatory custody receipts, staged merge and disagreement-only third bundle.
    with tempfile.TemporaryDirectory(prefix="r15d-v2-freeze-reconstruction-") as temporary:
        reconstructed_path = Path(temporary) / "reconstructed-final-packet.json"
        finalize_adjudication(
            fixture_path, reviewer_a_path, reviewer_b_path, receipt_a_path, receipt_b_path,
            staged_packet_path, reconstructed_path, custodian_id, primary_identity_verified,
            third_submission_path, third_receipt_path, third_identity_verified,
            expected_staged_sha256,
        )
        reconstructed_bytes = reconstructed_path.read_bytes()
    if packet_bytes != reconstructed_bytes:
        raise ValueError("final adjudication packet does not exactly match receipt-verified primary/third review reconstruction")

    fixture = load_fixture_bundle(fixture_path)
    validation = validate_final_packet(fixture, packet)
    if not validation["valid"] or not validation["complete"]:
        raise ValueError("final v2 adjudication packet is not eligible for freeze: " + "; ".join(validation["errors"]))
    if packet["freeze"] != {"ground_truth_frozen": False, "frozen_at": None, "model_inference_authorized": False}:
        raise ValueError("input packet must be unfrozen and model inference unauthorized")

    frozen = json.loads(json.dumps(packet))
    frozen["status"] = "frozen_ground_truth"
    frozen["freeze"] = {
        "ground_truth_frozen": True,
        "frozen_at": frozen_at,
        "reviewer_output_visibility": "released_after_freeze",
        "model_inference_authorized": False,
    }
    frozen["freeze_provenance"] = {
        "input_packet_sha256": hashlib.sha256(packet_bytes).hexdigest(),
        "fixture_manifest_sha256": fixture["_artifact_manifest_sha256"],
        "custody_receipt_digests": packet["custody_receipts"],
        "validator": "scripts/validate_r15d_v2_adjudication.py",
        "validator_sha256": hashlib.sha256(VALIDATOR_PATH.read_bytes()).hexdigest(),
        "fixture_scanner": "scripts/scan_r15d_v2_artifact_leakage.py",
        "fixture_scanner_sha256": hashlib.sha256(SCANNER_PATH.read_bytes()).hexdigest(),
        "fixture_builder": "scripts/build_r15d_v2_semantic_fixtures.py",
        "fixture_builder_sha256": hashlib.sha256(BUILDER_PATH.read_bytes()).hexdigest(),
        "validation": validation,
        "receipt_verified_reconstruction": True,
        "output_is_separate_from_input": True,
    }
    payload = (json.dumps(frozen, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _atomic_create(output_path, payload)
    return {
        "valid_frozen_manifest": True,
        "output_path": str(output_path),
        "output_sha256": hashlib.sha256(payload).hexdigest(),
        "input_packet_sha256": hashlib.sha256(packet_bytes).hexdigest(),
        "fixture_manifest_sha256": fixture["_artifact_manifest_sha256"],
        "custody_receipt_digests": packet["custody_receipts"],
        "completed_cases": validation["completed_cases"],
        "model_inference_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze R15D v2 only after receipt-verified reconstruction of the complete human adjudication packet.")
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen-at", required=True)
    parser.add_argument("--reviewer-a", type=Path, required=True)
    parser.add_argument("--reviewer-b", type=Path, required=True)
    parser.add_argument("--receipt-a", type=Path, required=True)
    parser.add_argument("--receipt-b", type=Path, required=True)
    parser.add_argument("--staged-packet", type=Path, required=True)
    parser.add_argument("--custodian-id", required=True)
    parser.add_argument("--primary-identity-verification-complete", action="store_true")
    parser.add_argument("--third-submission", type=Path)
    parser.add_argument("--third-receipt", type=Path)
    parser.add_argument("--third-identity-verification-complete", action="store_true")
    parser.add_argument("--expected-staged-sha256")
    args = parser.parse_args()
    result = freeze_adjudication(
        args.packet, args.fixture, args.output, args.frozen_at,
        args.reviewer_a, args.reviewer_b, args.receipt_a, args.receipt_b,
        args.staged_packet, args.custodian_id, args.primary_identity_verification_complete,
        args.third_submission, args.third_receipt, args.third_identity_verification_complete,
        args.expected_staged_sha256,
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
