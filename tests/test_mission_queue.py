from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from flashloan_research.mission_queue import MissionQueue, MissionValidationError, validate_mission


def valid_mission():
    return {
        "mission_id": "test-mission-001",
        "title": "Flash loan research mission",
        "objective": "Deeply research flash-loan callback security and accounting invariants.",
        "domain": "flash_loan_arbitrage",
        "scope": {"chains": ["Ethereum"], "protocols": ["Aave V3"], "repository_limit": 25},
        "research_depth": "deep_forensic",
        "agent_policy": {
            "mode": "autonomous", "independent_review": True,
            "max_parallel_agents": 4, "max_iterations": 3,
            "specialists": ["research_director", "github_discovery", "independent_reviewer"]
        },
        "safety_policy": {
            "research_only": True, "execute_candidate_code": False,
            "wallet_access": False, "sign_transactions": False,
            "deploy_contracts": False, "live_trading": False, "paid_services": False
        },
        "deliverables": ["candidate_matrix", "security_findings", "evidence_register"]
    }


class MissionQueueTests(unittest.TestCase):
    def test_accepts_valid_research_mission(self):
        self.assertEqual(validate_mission(valid_mission())["mission_id"], "test-mission-001")

    def test_rejects_wallet_access_even_if_form_requests_it(self):
        mission = valid_mission()
        mission["safety_policy"]["wallet_access"] = True
        with self.assertRaises(MissionValidationError):
            validate_mission(mission)

    def test_rejects_candidate_code_execution(self):
        mission = valid_mission()
        mission["safety_policy"]["execute_candidate_code"] = True
        with self.assertRaises(MissionValidationError):
            validate_mission(mission)

    def test_rejects_missing_independent_reviewer(self):
        mission = valid_mission()
        mission["agent_policy"]["specialists"].remove("independent_reviewer")
        with self.assertRaises(MissionValidationError):
            validate_mission(mission)

    def test_queue_persists_and_rejects_duplicate_mission_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = MissionQueue(Path(tmp) / "missions.sqlite3")
            try:
                result = queue.enqueue(valid_mission())
                self.assertEqual(result["status"], "queued")
                self.assertEqual(queue.get("test-mission-001")["status"], "queued")
                with self.assertRaises(MissionValidationError):
                    queue.enqueue(valid_mission())
            finally:
                queue.close()


if __name__ == "__main__":
    unittest.main()
