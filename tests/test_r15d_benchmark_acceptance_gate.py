from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_r15d_reviewer_benchmark import BenchmarkGateError, verify_report


class R15DBenchmarkAcceptanceGateTests(unittest.TestCase):
    def _fixture(self, decisions):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        outcomes = []
        for index, decision in enumerate(decisions):
            repository = f"org/repo-{index}"
            response = json.dumps({"choices": [{"message": {"content": json.dumps({"review_decision": decision})}}]})
            response_sha = hashlib.sha256(response.encode()).hexdigest()
            request_sha = hashlib.sha256(f"request-{index}".encode()).hexdigest()
            exchange = {
                "exchange": {
                    "request": {"messages": []},
                    "request_sha256": request_sha,
                    "response_raw": response,
                    "response_sha256": response_sha,
                }
            }
            name = f"review-{index}.json"
            (root / name).write_text(json.dumps(exchange), encoding="utf-8")
            exchange_sha = hashlib.sha256((root / name).read_bytes()).hexdigest()
            outcomes.append({
                "repository": repository,
                "packet_adequacy": {"status": "insufficient"},
                "model_output": {"review_decision": decision},
                "exchange_file": str(root / name),
                "exchange_file_sha256": exchange_sha,
                "request_sha256": request_sha,
                "response_sha256": response_sha,
            })
        report = {
            "reviewer_outcomes": outcomes,
            "acceptance": {
                "reviewer_exchanges_captured": True,
                "both_packets_expected_insufficient": True,
                "both_model_decisions_inconclusive": True,
                "dossiers_remain_pending": True,
                "semantic_audit_increment": 0,
                "candidate_code_executed": False,
                "wallet_access": False,
                "transaction_signing": False,
                "deployment": False,
                "live_trading": False,
                "paid_inference": False,
                "cloud_inference": False,
            },
        }
        path = root / "report.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        return temp, path

    def test_accepts_two_inconclusive_decisions_with_verified_exchanges(self):
        temp, path = self._fixture(["inconclusive", "inconclusive"])
        self.addCleanup(temp.cleanup)
        self.assertEqual(verify_report(path)["status"], "accepted")

    def test_rejects_model_accept_on_inadequate_packet(self):
        temp, path = self._fixture(["accept", "inconclusive"])
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(BenchmarkGateError, "requires the model itself"):
            verify_report(path)

    def test_rejects_exchange_hash_mismatch(self):
        temp, path = self._fixture(["inconclusive", "inconclusive"])
        self.addCleanup(temp.cleanup)
        report = json.loads(path.read_text())
        report["reviewer_outcomes"][0]["exchange_file_sha256"] = "0" * 64
        path.write_text(json.dumps(report))
        with self.assertRaisesRegex(BenchmarkGateError, "exchange SHA-256 mismatch"):
            verify_report(path)


if __name__ == "__main__":
    unittest.main()
