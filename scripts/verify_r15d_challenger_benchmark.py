from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_INPUTS = {
    "0xnavarro/Aave-Liquiditor": {
        "commit": "9197ee3002d7d9b35e9c2da324128a38f7569038",
        "tree": "14de2312e96c369bcc52c9bae96215051aea22b4",
        "packet_sha256": "f6468df676243cbcdc5bc603683d65d2980086b1345a3696a9cf63a36c2fa2d4",
    },
    "cobibean/aave-liquidator-bot": {
        "commit": "3159c15f4dcfb0df215b4c3024f47753a1133b84",
        "tree": "1a9ee7218304b95654385fc11f255a7c5d532bc4",
        "packet_sha256": "b8bf978a506fb0cceeaba33d4cbd99a7f55c1146645775678e3de23bc17c6ef4",
    },
}
EXPECTED_MODEL = {
    "tag": "qwen3.5:4b",
    "digest": "d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04",
    "quantization": "Q4_K_M",
}


class ChallengerGateError(RuntimeError):
    pass


def verify(report_path: Path) -> dict:
    root = report_path.resolve().parent
    report = json.loads(report_path.read_text(encoding="utf-8"))
    model = report.get("model", {})
    for key, expected in EXPECTED_MODEL.items():
        actual = model.get("tag" if key == "tag" else "digest" if key == "digest" else "quantization")
        if actual != expected:
            raise ChallengerGateError(f"challenger model {key} mismatch: {actual!r}")
    if report.get("status") != "completed":
        raise ChallengerGateError("challenger did not complete both frozen reviewer tasks")

    outcomes = report.get("reviewer_outcomes")
    if not isinstance(outcomes, list) or len(outcomes) != 2:
        raise ChallengerGateError("expected exactly two reviewer outcomes")
    seen = set()
    checked = []
    for item in outcomes:
        repo = item.get("repository")
        if repo not in EXPECTED_INPUTS or repo in seen:
            raise ChallengerGateError(f"unexpected or duplicate candidate: {repo!r}")
        seen.add(repo)
        pin = EXPECTED_INPUTS[repo]
        if item.get("inspection_commit_sha") != pin["commit"] or item.get("inspection_tree_sha") != pin["tree"]:
            raise ChallengerGateError(f"{repo}: inspection source pin mismatch")
        if item.get("input_packet_sha256") != pin["packet_sha256"]:
            raise ChallengerGateError(f"{repo}: reviewer input differs from frozen baseline packet")
        if (item.get("packet_adequacy") or {}).get("status") != "insufficient":
            raise ChallengerGateError(f"{repo}: frozen packet adequacy changed")
        output = item.get("model_output") or {}
        decision = output.get("review_decision")
        if decision != "inconclusive":
            raise ChallengerGateError(
                f"{repo}: inadequate packet requires model's own inconclusive verdict; got {decision!r}"
            )
        exchange_path = root / Path(item.get("exchange_file", "")).name
        if not exchange_path.is_file():
            exchange_path = next(root.rglob(Path(item.get("exchange_file", "")).name), None)
        if exchange_path is None or not exchange_path.is_file():
            raise ChallengerGateError(f"{repo}: raw exchange file is missing")
        raw_bytes = exchange_path.read_bytes()
        if hashlib.sha256(raw_bytes).hexdigest() != item.get("exchange_file_sha256"):
            raise ChallengerGateError(f"{repo}: raw exchange file hash mismatch")
        captured = json.loads(raw_bytes)
        exchange = captured.get("exchange") or {}
        request = exchange.get("request")
        if not isinstance(request, dict):
            raise ChallengerGateError(f"{repo}: raw request body missing")
        request_hash = hashlib.sha256(json.dumps(request).encode("utf-8")).hexdigest()
        response_raw = exchange.get("response_raw")
        if not isinstance(response_raw, str):
            raise ChallengerGateError(f"{repo}: raw response missing")
        response_hash = hashlib.sha256(response_raw.encode("utf-8")).hexdigest()
        if request_hash != exchange.get("request_sha256") or request_hash != item.get("request_sha256"):
            raise ChallengerGateError(f"{repo}: request fingerprint mismatch")
        if response_hash != exchange.get("response_sha256") or response_hash != item.get("response_sha256"):
            raise ChallengerGateError(f"{repo}: response fingerprint mismatch")
        checked.append({"repository": repo, "decision": decision, "exchange_sha256": item["exchange_file_sha256"]})

    acceptance = report.get("acceptance", {})
    if acceptance.get("semantic_audit_increment") != 0:
        raise ChallengerGateError("semantic audit increment must remain zero")
    for key in ("dossiers_remain_pending", "reviewer_exchanges_captured", "both_packets_expected_insufficient"):
        if acceptance.get(key) is not True:
            raise ChallengerGateError(f"acceptance invariant failed: {key}")
    for key in ("candidate_code_executed", "wallet_access", "transaction_signing", "deployment", "live_trading", "paid_inference", "cloud_inference"):
        if acceptance.get(key) is not False:
            raise ChallengerGateError(f"safety invariant failed: {key}")
    return {"status": "accepted", "model": EXPECTED_MODEL, "reviewers": checked, "semantic_audit_increment": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.report)
    except (OSError, json.JSONDecodeError, ChallengerGateError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
