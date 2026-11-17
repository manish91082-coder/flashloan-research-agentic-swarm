from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.validate_r15d_adjudication import _valid_timestamp, validate

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET = ROOT / "research_runs/r15d_adjudication/blind_adjudication_packet.json"
DEFAULT_OUTPUT = ROOT / "research_runs/r15d_adjudication/frozen_ground_truth_manifest.json"


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def freeze(packet_path: Path, output_path: Path, frozen_at: str) -> str:
    if not _valid_timestamp(frozen_at):
        raise ValueError("frozen_at must be a timezone-aware UTC ISO-8601 timestamp")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite frozen manifest: {output_path}")
    try:
        packet_bytes = packet_path.read_bytes()
        packet = json.loads(packet_bytes.decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"unable to read a valid adjudication JSON packet: {exc}") from exc
    if not isinstance(packet, dict):
        raise ValueError("input packet must be a JSON object")
    if packet.get("packet_type") != "blind_ground_truth_adjudication":
        raise ValueError("input must be the designated blind ground-truth adjudication packet")
    if packet.get("status") != "pending_independent_review":
        raise ValueError("input packet must remain in pending_independent_review state until freeze")
    freeze_state = packet.get("freeze")
    if not isinstance(freeze_state, dict):
        raise ValueError("input packet freeze state must be an object")
    if (
        freeze_state.get("ground_truth_frozen") is not False
        or freeze_state.get("reviewer_output_visibility") != "hidden_until_freeze"
        or freeze_state.get("model_inference_authorized") is not False
    ):
        raise ValueError("input packet freeze/blinding state is not the expected pre-freeze state")
    result = validate(packet, require_complete=True)
    if not result["valid"] or not result["complete"]:
        raise ValueError("adjudication packet failed fail-closed validation: " + "; ".join(result["errors"]))
    blinding = packet.get("blinding")
    if not isinstance(blinding, dict):
        raise ValueError("blind packet integrity flags must be an object")
    if blinding.get("expected_labels_omitted") is not True or blinding.get("model_outputs_omitted") is not True:
        raise ValueError("blind packet integrity flags are not satisfied")
    safety = packet.get("safety")
    if not isinstance(safety, dict):
        raise ValueError("safety invariants must be an object")
    required_false = ("candidate_code_execution", "wallet_access", "transaction_signing", "deployment", "live_trading", "paid_inference", "cloud_inference")
    if any(safety.get(key) is not False for key in required_false):
        raise ValueError("safety invariant missing or enabled")
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
        "validator": "scripts/validate_r15d_adjudication.py",
        "validator_sha256": hashlib.sha256(Path(__file__).with_name("validate_r15d_adjudication.py").read_bytes()).hexdigest(),
        "validation": result,
        "output_is_separate_from_blind_input": True,
    }
    payload = (json.dumps(frozen, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("xb") as handle:
        handle.write(payload)
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze independently adjudicated R15D ground truth into a new immutable file.")
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--frozen-at", required=True, help="Explicit ISO-8601 UTC timestamp from the adjudication record.")
    args = parser.parse_args()
    digest = freeze(args.packet, args.output, args.frozen_at)
    print(json.dumps({"frozen_manifest": str(args.output), "sha256": digest}, indent=2))


if __name__ == "__main__":
    main()
