from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

from scripts.validate_r15d_adjudication import _valid_timestamp, validate

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET = ROOT / "research_runs/r15d_adjudication/blind_adjudication_packet.json"
DEFAULT_MANIFEST = ROOT / "research_runs/r15d_adjudication/frozen_ground_truth_manifest.json"
VALIDATOR_PATH = ROOT / "scripts/validate_r15d_adjudication.py"


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _load_strict_json(raw: bytes, label: str):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"{label} is not valid duplicate-free UTF-8 JSON: {exc}") from exc


def verify_frozen_manifest(packet_path: Path, manifest_path: Path, expected_sha256: str | None = None) -> dict:
    if packet_path.resolve() == manifest_path.resolve():
        raise ValueError("blind input packet and frozen manifest must be separate files")
    try:
        packet_bytes = packet_path.read_bytes()
        manifest_bytes = manifest_path.read_bytes()
    except OSError as exc:
        raise ValueError(f"unable to read packet or frozen manifest: {exc}") from exc

    packet = _load_strict_json(packet_bytes, "blind input packet")
    manifest = _load_strict_json(manifest_bytes, "frozen manifest")
    if not isinstance(packet, dict) or not isinstance(manifest, dict):
        raise ValueError("packet and frozen manifest must both be JSON objects")

    validation = validate(packet, require_complete=True)
    if not validation["valid"] or not validation["complete"]:
        raise ValueError("original blind packet is not eligible for freeze: " + "; ".join(validation["errors"]))

    validator_bytes = VALIDATOR_PATH.read_bytes()
    validator_sha256 = hashlib.sha256(validator_bytes).hexdigest()
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
        "validator": "scripts/validate_r15d_adjudication.py",
        "validator_sha256": validator_sha256,
        "validation": validation,
        "output_is_separate_from_blind_input": True,
    }
    if manifest != expected:
        raise ValueError("frozen manifest content or provenance does not match the exact validated input packet and current validator")
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if expected_sha256 is not None:
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise ValueError("expected_sha256 must be a lowercase 64-character SHA-256 digest")
        if manifest_sha256 != expected_sha256:
            raise ValueError("frozen manifest SHA-256 does not match the supplied expected digest")
    return {
        "valid": True,
        "input_packet_sha256": hashlib.sha256(packet_bytes).hexdigest(),
        "validator_sha256": validator_sha256,
        "frozen_manifest_sha256": manifest_sha256,
        "completed_cases": validation["completed_cases"],
        "case_count": validation["case_count"],
        "model_inference_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Independently verify an R15D frozen ground-truth manifest against its exact blind input.")
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    result = verify_frozen_manifest(args.packet, args.manifest, args.expected_sha256)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
