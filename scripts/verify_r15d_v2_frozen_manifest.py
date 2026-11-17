from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
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


def verify_frozen_manifest(
    packet_path: Path,
    fixture_path: Path,
    manifest_path: Path,
    expected_sha256: str | None = None,
    reviewer_a_path: Path | None = None,
    reviewer_b_path: Path | None = None,
    receipt_a_path: Path | None = None,
    receipt_b_path: Path | None = None,
    staged_packet_path: Path | None = None,
    custodian_id: str | None = None,
    primary_identity_verified: bool = False,
    third_submission_path: Path | None = None,
    third_receipt_path: Path | None = None,
    third_identity_verified: bool = False,
    expected_staged_sha256: str | None = None,
) -> dict:
    required = [reviewer_a_path, reviewer_b_path, receipt_a_path, receipt_b_path, staged_packet_path, custodian_id]
    if any(value is None for value in required):
        raise ValueError("independent frozen-manifest verification requires both primary bundles, both receipts, staged packet and custodian ID")
    inputs = {
        packet_path.resolve(), fixture_path.resolve(), manifest_path.resolve(),
        reviewer_a_path.resolve(), reviewer_b_path.resolve(), receipt_a_path.resolve(),
        receipt_b_path.resolve(), staged_packet_path.resolve(),
    }
    if third_submission_path is not None:
        inputs.add(third_submission_path.resolve())
    if third_receipt_path is not None:
        inputs.add(third_receipt_path.resolve())
    if manifest_path.resolve() in inputs - {manifest_path.resolve()} or len(inputs) != (10 if third_submission_path is not None else 8):
        raise ValueError("frozen manifest, packet, fixture, reviewer bundles, receipts and staged packet must all be separate paths")
    try:
        packet_bytes = packet_path.read_bytes()
        manifest_bytes = manifest_path.read_bytes()
        packet = json.loads(packet_bytes.decode("utf-8"), object_pairs_hook=_unique_object)
        manifest = json.loads(manifest_bytes.decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"unable to read duplicate-free v2 packet/manifest JSON: {exc}") from exc
    if not isinstance(packet, dict) or not isinstance(manifest, dict):
        raise ValueError("packet and frozen manifest must be JSON objects")

    # Rebuild the expected complete packet from exact reviewer submissions and receipts.
    with tempfile.TemporaryDirectory(prefix="r15d-v2-verify-reconstruction-") as temporary:
        reconstructed_path = Path(temporary) / "reconstructed-final-packet.json"
        finalize_adjudication(
            fixture_path, reviewer_a_path, reviewer_b_path, receipt_a_path, receipt_b_path,
            staged_packet_path, reconstructed_path, custodian_id, primary_identity_verified,
            third_submission_path, third_receipt_path, third_identity_verified,
            expected_staged_sha256,
        )
        reconstructed_bytes = reconstructed_path.read_bytes()
    if packet_bytes != reconstructed_bytes:
        raise ValueError("source adjudication packet does not exactly match receipt-verified primary/third review reconstruction")

    fixture = load_fixture_bundle(fixture_path)
    validation = validate_final_packet(fixture, packet)
    if not validation["valid"] or not validation["complete"]:
        raise ValueError("source adjudication packet is not complete and valid: " + "; ".join(validation["errors"]))

    frozen_at = manifest.get("freeze", {}).get("frozen_at") if isinstance(manifest.get("freeze"), dict) else None
    if not _valid_timestamp(frozen_at):
        raise ValueError("frozen manifest timestamp must be timezone-aware UTC ISO-8601")
    expected = copy.deepcopy(packet)
    expected["status"] = "frozen_ground_truth"
    expected["freeze"] = {
        "ground_truth_frozen": True,
        "frozen_at": frozen_at,
        "reviewer_output_visibility": "released_after_freeze",
        "model_inference_authorized": False,
    }
    expected["freeze_provenance"] = {
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
    if manifest != expected:
        raise ValueError("frozen manifest content or provenance does not match the exact receipt-verified v2 packet and current toolchain")
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    if expected_sha256 is not None:
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or digest != expected_sha256:
            raise ValueError("frozen manifest SHA-256 does not match expected digest")
    return {
        "valid": True,
        "input_packet_sha256": hashlib.sha256(packet_bytes).hexdigest(),
        "fixture_manifest_sha256": fixture["_artifact_manifest_sha256"],
        "custody_receipt_digests": packet["custody_receipts"],
        "frozen_manifest_sha256": digest,
        "completed_cases": validation["completed_cases"],
        "model_inference_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Independently verify R15D v2 frozen manifest from receipt-verified human review inputs.")
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-sha256")
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
    result = verify_frozen_manifest(
        args.packet, args.fixture, args.manifest, args.expected_sha256,
        args.reviewer_a, args.reviewer_b, args.receipt_a, args.receipt_b,
        args.staged_packet, args.custodian_id, args.primary_identity_verification_complete,
        args.third_submission, args.third_receipt, args.third_identity_verification_complete,
        args.expected_staged_sha256,
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
