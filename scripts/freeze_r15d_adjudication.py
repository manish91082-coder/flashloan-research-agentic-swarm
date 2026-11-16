from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.validate_r15d_adjudication import validate

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET = ROOT / "research_runs/r15d_adjudication/blind_adjudication_packet.json"
DEFAULT_OUTPUT = ROOT / "research_runs/r15d_adjudication/frozen_ground_truth_manifest.json"


def freeze(packet_path: Path, output_path: Path, frozen_at: str) -> str:
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite frozen manifest: {output_path}")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    result = validate(packet, require_complete=True)
    if not result["valid"] or not result["complete"]:
        raise ValueError("adjudication packet failed fail-closed validation: " + "; ".join(result["errors"]))
    blinding = packet.get("blinding", {})
    if blinding.get("expected_labels_omitted") is not True or blinding.get("model_outputs_omitted") is not True:
        raise ValueError("blind packet integrity flags are not satisfied")
    safety = packet.get("safety", {})
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
        "input_packet_sha256": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
        "validator": "scripts/validate_r15d_adjudication.py",
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
