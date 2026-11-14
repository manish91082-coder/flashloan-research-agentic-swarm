from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from flashloan_research.mission_api import MissionHTTPServer, MissionRequestHandler
from flashloan_research.mission_queue import MissionQueue


def mission_payload():
    return {
        "mission_id": "api-mission-20261114111500",
        "title": "Flash loan research mission",
        "objective": "Deeply research flash-loan callback security and accounting invariants.",
        "domain": "flash_loan_arbitrage",
        "scope": {"chains": ["Ethereum"], "protocols": ["Aave V3"], "repository_limit": 25,
                  "include_archived": False, "include_older_references": True},
        "research_depth": "deep_forensic",
        "agent_policy": {"mode": "autonomous", "independent_review": True,
                         "max_parallel_agents": 4, "max_iterations": 3,
                         "specialists": ["research_director", "github_discovery", "independent_reviewer"]},
        "safety_policy": {"research_only": True, "execute_candidate_code": False,
                          "wallet_access": False, "sign_transactions": False,
                          "deploy_contracts": False, "live_trading": False, "paid_services": False,
                          "allow_free_model_inference": True},
        "deliverables": ["candidate_matrix", "security_findings", "evidence_register"],
        "acceptance_criteria": ["Commit-pinned evidence required."],
        "created_at_utc": "2026-11-14T11:15:00Z"
    }


class MissionAPITests(unittest.TestCase):
    def test_local_api_queues_valid_mission_and_reports_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = MissionQueue(Path(tmp) / "missions.sqlite3")
            server = MissionHTTPServer(("127.0.0.1", 0), MissionRequestHandler, queue)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                request = urllib.request.Request(
                    base + "/missions",
                    data=json.dumps(mission_payload()).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=3) as response:
                    self.assertEqual(response.status, 202)
                    result = json.loads(response.read())
                self.assertEqual(result["status"], "queued")
                with urllib.request.urlopen(base + "/missions/" + result["mission_id"], timeout=3) as response:
                    detail = json.loads(response.read())
                self.assertEqual(detail["status"], "queued")
                self.assertEqual(detail["payload"]["mission_id"], result["mission_id"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
                queue.close()

    def test_api_rejects_attempt_to_enable_live_trading(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = MissionQueue(Path(tmp) / "missions.sqlite3")
            server = MissionHTTPServer(("127.0.0.1", 0), MissionRequestHandler, queue)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            payload = mission_payload()
            payload["safety_policy"]["live_trading"] = True
            try:
                request = urllib.request.Request(
                    base + "/missions", data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=3)
                self.assertEqual(caught.exception.code, 422)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
                queue.close()


if __name__ == "__main__":
    unittest.main()
