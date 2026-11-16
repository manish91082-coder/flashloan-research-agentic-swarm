from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify_r15d_challenger_benchmark import (
    ChallengerGateError, EXPECTED_INPUTS, EXPECTED_MODEL, verify,
)


class ChallengerBenchmarkGateTests(unittest.TestCase):
    def fixture(self, decisions):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        outcomes = []
        test_pins = {}
        (root / "model_exchanges").mkdir()
        (root / "inspections").mkdir()
        for index, (repo, original_pin) in enumerate(EXPECTED_INPUTS.items()):
            pin = dict(original_pin)
            user_content = f"frozen-{index}"
            pin["packet_sha256"] = hashlib.sha256(user_content.encode()).hexdigest()
            test_pins[repo] = pin
            response = json.dumps({
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": json.dumps({"review_decision": decisions[index]})},
                }]
            })
            response_sha = hashlib.sha256(response.encode()).hexdigest()
            request = {
                "messages": [
                    {"role": "system", "content": "system"},
                    {"role": "user", "content": user_content},
                ]
            }
            request_raw = json.dumps(request).replace(" ", "")
            request_sha = hashlib.sha256(request_raw.encode("utf-8")).hexdigest()
            exchange = {
                "exchange": {
                    "request": request,
                    "request_raw": json.dumps(request).replace(" ", ""),
                    "request_sha256": hashlib.sha256(json.dumps(request).replace(" ", "").encode("utf-8")).hexdigest(),
                    "response_raw": response,
                    "response_sha256": response_sha,
                }
            }
            name = f"candidate-{index}.json"
            raw_path = root / "model_exchanges" / name
            raw_path.write_text(json.dumps(exchange), encoding="utf-8")
            # Same basename in inspections must never shadow the raw exchange.
            (root / "inspections" / name).write_text("{\"normalized\": true}", encoding="utf-8")
            outcomes.append({
                "repository": repo,
                "inspection_commit_sha": pin["commit"],
                "inspection_tree_sha": pin["tree"],
                "input_packet_sha256": pin["packet_sha256"],
                "packet_adequacy": {"status": "insufficient"},
                "model_output": {"review_decision": decisions[index]},
                "request_sha256": request_sha,
                "response_sha256": response_sha,
                "exchange_file": f"/runner/path/model_exchanges/{name}",
                "exchange_file_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
            })
        report = {
            "status": "completed",
            "model": {
                "tag": EXPECTED_MODEL["tag"],
                "digest": EXPECTED_MODEL["digest"],
                "quantization": EXPECTED_MODEL["quantization"],
            },
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
        return temp, path, test_pins

    def test_accepts_two_inconclusive_reviews_on_exact_frozen_packets(self):
        tmp, path, pins = self.fixture(["inconclusive", "inconclusive"])
        self.addCleanup(tmp.cleanup)
        with patch.dict(EXPECTED_INPUTS, pins, clear=True):
            self.assertEqual(verify(path)["status"], "accepted")

    def test_rejects_accept_on_inadequate_packet(self):
        tmp, path, pins = self.fixture(["accept", "inconclusive"])
        self.addCleanup(tmp.cleanup)
        with patch.dict(EXPECTED_INPUTS, pins, clear=True):
            with self.assertRaisesRegex(ChallengerGateError, "requires model's own inconclusive"):
                verify(path)

    def test_rejects_changed_input_packet(self):
        tmp, path, pins = self.fixture(["inconclusive", "inconclusive"])
        self.addCleanup(tmp.cleanup)
        report = json.loads(path.read_text())
        report["reviewer_outcomes"][0]["input_packet_sha256"] = "0" * 64
        path.write_text(json.dumps(report))
        with patch.dict(EXPECTED_INPUTS, pins, clear=True):
            with self.assertRaisesRegex(ChallengerGateError, "differs from frozen baseline"):
                verify(path)


if __name__ == "__main__":
    unittest.main()
