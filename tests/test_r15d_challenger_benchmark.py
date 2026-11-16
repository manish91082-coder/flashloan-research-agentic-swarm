from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_r15d_challenger_benchmark import ChallengerGateError, EXPECTED_INPUTS, EXPECTED_MODEL, verify


class ChallengerBenchmarkGateTests(unittest.TestCase):
    def fixture(self, decisions):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        outcomes = []
        for index, (repo, pin) in enumerate(EXPECTED_INPUTS.items()):
            response = json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"review_decision": decisions[index]})}}]})
            response_sha = hashlib.sha256(response.encode()).hexdigest()
            request = {"messages": [{"role": "system", "content": "system"}, {"role": "user", "content": f"frozen-{index}"}]}
            request_sha = hashlib.sha256(json.dumps(request).encode()).hexdigest()
            exchange = {"exchange": {"request": request, "request_sha256": request_sha, "response_raw": response, "response_sha256": response_sha}}
            name = f"exchange-{index}.json"
            (root / name).write_text(json.dumps(exchange), encoding="utf-8")
            outcomes.append({
                "repository": repo,
                "inspection_commit_sha": pin["commit"],
                "inspection_tree_sha": pin["tree"],
                "input_packet_sha256": pin["packet_sha256"],
                "packet_adequacy": {"status": "insufficient"},
                "model_output": {"review_decision": decisions[index]},
                "request_sha256": request_sha,
                "response_sha256": response_sha,
                "exchange_file": str(root / name),
                "exchange_file_sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
            })
        report = {
            "status": "completed",
            "model": {"tag": EXPECTED_MODEL["tag"], "digest": EXPECTED_MODEL["digest"], "quantization": EXPECTED_MODEL["quantization"]},
            "reviewer_outcomes": outcomes,
            "acceptance": {
                "reviewer_exchanges_captured": True,
                "both_packets_expected_insufficient": True,
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

    def test_accepts_two_inconclusive_reviews_on_exact_frozen_packets(self):
        tmp, path = self.fixture(["inconclusive", "inconclusive"])
        self.addCleanup(tmp.cleanup)
        self.assertEqual(verify(path)["status"], "accepted")

    def test_rejects_accept_on_inadequate_packet(self):
        tmp, path = self.fixture(["accept", "inconclusive"])
        self.addCleanup(tmp.cleanup)
        with self.assertRaisesRegex(ChallengerGateError, "requires model's own inconclusive"):
            verify(path)

    def test_rejects_changed_input_packet(self):
        tmp, path = self.fixture(["inconclusive", "inconclusive"])
        self.addCleanup(tmp.cleanup)
        report = json.loads(path.read_text())
        report["reviewer_outcomes"][0]["input_packet_sha256"] = "0" * 64
        path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ChallengerGateError, "differs from frozen baseline"):
            verify(path)


if ( __name__ == "__main__"):
    unittest.main()
