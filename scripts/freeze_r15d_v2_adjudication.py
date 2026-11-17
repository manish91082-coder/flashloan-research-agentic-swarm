from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

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


def freeze_adjudication(packet_path: Path, fixture_path: Path, output_path: Path, frozen_at: str) -> dict:
    if packet_path.resolve() == output_path.resolve() or fixture_path.resolve() == output_path.resolve():
        raise ValueError("frozen manifest output must be separate from the adjudication packet and fixture")
    if not _valid_timestamp(frozen_at):
        raise ValueError("frozen_at must be a timezone-aware UTC ISO-8601 timestamp")
    try:
        packet_bytes = packet_path.read_bytes()
        packet = json.loads(packet_bytes.decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"unable to read duplicate-free final adjudication packet: {exc}") from exc
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
        "validator": "scripts/validate_r15d_v2_adjudication.py",
        "validator_sha256": hashlib.sha256(VALIDATOR_PATH.read_bytes()).hexdigest(),
        "fixture_scanner": "scripts/scan_r15d_v2_artifact_leakage.py",
        "fixture_scanner_sha256": hashlib.sha256(SCANNER_PATH.read_bytes()).hexdigest(),
        "fixture_builder": "scripts/build_r15d_v2_semantic_fixtures.py",
        "fixture_builder_sha256": hashlib.sha256(BUILDER_PATH.read_bytes()).hexdigest(),
        "validation": validation,
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
        "completed_cases": validation["completed_cases"],
        "model_inference_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze a complete R15D v2 adjudication packet into a separate immutable manifest. Does not authorize model inference.")
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen-at", required=True)
    args = parser.parse_args()
    result = freeze_adjudication(args.packet, args.fixture, args.output, args.frozen_at)
    print(json.dumps(result, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
