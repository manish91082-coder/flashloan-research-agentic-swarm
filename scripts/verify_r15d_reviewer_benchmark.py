from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


class BenchmarkGateError(RuntimeError):
    pass


def verify_report(report_path: Path, expected_reviewers: int = 2) -> dict:
    report_path = report_path.resolve()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    outcomes = report.get("reviewer_outcomes")
    if not isinstance(outcomes, list) or len(outcomes) != expected_reviewers:
        raise BenchmarkGateError(
            f"expected {expected_reviewers} reviewer outcomes; got "
            f"{len(outcomes) if isinstance(outcomes, list) else 'invalid'}"
        )

    checked = []
    for outcome in outcomes:
        repository = outcome.get("repository")
        if not repository:
            raise BenchmarkGateError("reviewer outcome is missing repository identity")
        adequacy = outcome.get("packet_adequacy") or {}
        if adequacy.get("status") != "insufficient":
            raise BenchmarkGateError(
                f"{repository}: frozen specialist packet was expected to be insufficient"
            )
        model_output = outcome.get("model_output") or {}
        decision = model_output.get("review_decision")
        if decision != "inconclusive":
            raise BenchmarkGateError(
                f"{repository}: model returned {decision!r}; inadequate packet requires "
                "the model itself to return 'inconclusive'"
            )

        exchange_name = Path(outcome.get("exchange_file", "")).name
        if not exchange_name:
            raise BenchmarkGateError(f"{repository}: raw exchange path is missing")
        matches = list(report_path.parent.rglob(exchange_name))
        if len(matches) != 1:
            raise BenchmarkGateError(
                f"{repository}: expected one captured raw exchange {exchange_name!r}; "
                f"found {len(matches)}"
            )
        exchange_path = matches[0]
        exchange_sha = hashlib.sha256(exchange_path.read_bytes()).hexdigest()
        if exchange_sha != outcome.get("exchange_file_sha256"):
            raise BenchmarkGateError(f"{repository}: raw exchange SHA-256 mismatch")

        exchange = json.loads(exchange_path.read_text(encoding="utf-8"))
        envelope = exchange.get("exchange") or {}
        raw_response = envelope.get("response_raw")
        if not isinstance(raw_response, str):
            raise BenchmarkGateError(f"{repository}: raw model response was not preserved")
        response_sha = hashlib.sha256(raw_response.encode("utf-8")).hexdigest()
        if response_sha != envelope.get("response_sha256"):
            raise BenchmarkGateError(f"{repository}: raw response SHA-256 mismatch")
        if envelope.get("request_sha256") != outcome.get("request_sha256"):
            raise BenchmarkGateError(f"{repository}: request fingerprint mismatch")
        if envelope.get("response_sha256") != outcome.get("response_sha256"):
            raise BenchmarkGateError(f"{repository}: response fingerprint mismatch")
        checked.append({
            "repository": repository,
            "decision": decision,
            "exchange_sha256": exchange_sha,
            "response_sha256": response_sha,
        })

    acceptance = report.get("acceptance") or {}
    required_true = (
        "reviewer_exchanges_captured",
        "both_packets_expected_insufficient",
        "both_model_decisions_inconclusive",
        "dossiers_remain_pending",
        "candidate_code_executed",
        "wallet_access",
        "transaction_signing",
        "deployment",
        "live_trading",
        "paid_inference",
        "cloud_inference",
    )
    for key in required_true:
        expected = key not in {
            "candidate_code_executed", "wallet_access", "transaction_signing",
            "deployment", "live_trading", "paid_inference", "cloud_inference",
        }
        if acceptance.get(key) is not expected:
            raise BenchmarkGateError(
                f"acceptance.{key} expected {expected!r}; got {acceptance.get(key)!r}"
            )
    if acceptance.get("semantic_audit_increment") != 0:
        raise BenchmarkGateError("semantic audit increment must remain exactly zero")

    return {
        "status": "accepted",
        "reviewers_verified": len(checked),
        "reviewers": checked,
        "semantic_audit_increment": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed R15D reviewer benchmark acceptance gate.")
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--expected-reviewers", type=int, default=2)
    args = parser.parse_args()
    try:
        result = verify_report(args.report, args.expected_reviewers)
    except (OSError, json.JSONDecodeError, BenchmarkGateError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
