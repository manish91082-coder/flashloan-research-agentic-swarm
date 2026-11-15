from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from flashloan_research.reviewer_recovery import (
    EXPECTED_FAILURE, ReviewerRecoveryError, requeue_failed_reviewers,
)


ROLE_BY_TYPE = {
    "candidate_purpose": "candidate_purpose",
    "protocol_forensics": "protocol_specialist",
    "security_forensics": "solidity_security",
    "execution_forensics": "execution_engineer",
    "test_forensics": "test_verification",
    "economic_forensics": "economics_quant",
    "dependency_forensics": "dependency_license",
}


class ReviewerRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        self.database = self.workspace / "mission.sqlite3"
        self.mission_id = "r4-recovery-test"
        self.repository = "org/repo"
        self.connection = sqlite3.connect(self.database)
        self.connection.executescript("""
            CREATE TABLE research_missions (
                mission_id TEXT PRIMARY KEY
            );
            CREATE TABLE mission_tasks (
                mission_id TEXT, task_id TEXT PRIMARY KEY, task_type TEXT, role TEXT,
                status TEXT, depends_on_json TEXT, payload_json TEXT, priority INTEGER,
                attempts INTEGER, max_attempts INTEGER, budget_units INTEGER,
                lease_owner TEXT, lease_expires_at TEXT, result_json TEXT, error TEXT,
                created_at_utc TEXT, updated_at_utc TEXT
            );
        """)
        self.connection.execute(
            "INSERT INTO research_missions VALUES (?)", (self.mission_id,)
        )
        self._write("reports/inspection.json", {
            "repository": self.repository,
            "commit_sha": "a" * 40,
            "tree_sha": "b" * 40,
        })
        self._write("reports/evidence.json", {
            "repository": self.repository,
            "inspection_commit_sha": "a" * 40,
            "inspection_tree_sha": "b" * 40,
            "evidence_gate": "pinned_evidence_and_claim_linkage_pass",
            "accepted_evidence_total": 3,
            "provenance_pass": True,
            "claim_linkage_pass": True,
        })
        self._insert_task(
            "source-task", "candidate_source_capture", "github_discovery", "completed",
            {"repository": self.repository},
            {"inspection_report": "reports/inspection.json"},
        )
        self.prior_task_ids = []
        for task_type, role in ROLE_BY_TYPE.items():
            task_id = f"prior-{task_type}"
            self.prior_task_ids.append(task_id)
            report_path = f"reports/{task_type}.json"
            self._write(report_path, {
                "task_metadata": {"task_id": task_id, "task_type": task_type},
                "agent_metadata": {"role": role},
                "evidence_validation": {
                    "inspection_commit_sha": "a" * 40,
                    "inspection_tree_sha": "b" * 40,
                    "all_findings_linked_to_accepted_evidence": True,
                },
            })
            self._insert_task(
                task_id, task_type, role, "completed",
                {"repository": self.repository}, {"report": report_path},
            )
        self._insert_task(
            "evidence-task", "evidence_validation", "evidence_auditor", "completed",
            {"repository": self.repository}, {"report": "reports/evidence.json"},
        )
        self._insert_task(
            "review-task", "independent_review", "independent_reviewer", "failed",
            {"repository": self.repository}, None,
            depends_on=["evidence-task"], attempts=1, max_attempts=3,
            error=EXPECTED_FAILURE,
        )
        self.connection.commit()

    def tearDown(self):
        self.connection.close()
        self.tmp.cleanup()

    def _write(self, relative: str, data: dict):
        path = self.workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def _insert_task(self, task_id, task_type, role, status, payload, result,
                     depends_on=None, attempts=1, max_attempts=3, error=None):
        self.connection.execute(
            """INSERT INTO mission_tasks
            (mission_id,task_id,task_type,role,status,depends_on_json,payload_json,
             priority,attempts,max_attempts,budget_units,lease_owner,lease_expires_at,
             result_json,error,created_at_utc,updated_at_utc)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                self.mission_id, task_id, task_type, role, status,
                json.dumps(depends_on or []), json.dumps(payload), 1, attempts,
                max_attempts, 1, "old-worker" if status == "failed" else None,
                "2026-11-15T00:00:00Z" if status == "failed" else None,
                json.dumps(result) if result is not None else None,
                error, "2026-11-15T00:00:00Z", "2026-11-15T00:00:00Z",
            ),
        )

    def test_requeues_only_known_reviewer_failures_after_verifying_all_upstream_reports(self):
        result = requeue_failed_reviewers(
            self.database, self.mission_id, expected_count=1, workspace=self.workspace,
        )
        row = self.connection.execute(
            "SELECT status,attempts,max_attempts,error,lease_owner,lease_expires_at FROM mission_tasks WHERE task_id='review-task'"
        ).fetchone()
        self.assertEqual(result["reviewers_requeued"], 1)
        self.assertEqual(result["tasks"][0]["prior_reports_verified"], 7)
        self.assertEqual(row, ("pending", 1, 3, None, None, None))
        for task_id in self.prior_task_ids + ["source-task", "evidence-task"]:
            status = self.connection.execute(
                "SELECT status FROM mission_tasks WHERE task_id=?", (task_id,)
            ).fetchone()[0]
            self.assertEqual(status, "completed")

    def test_refuses_to_reset_any_other_failure_reason(self):
        self.connection.execute(
            "UPDATE mission_tasks SET error='different failure' WHERE task_id='review-task'"
        )
        self.connection.commit()
        with self.assertRaisesRegex(ReviewerRecoveryError, "exact known context-cap failure"):
            requeue_failed_reviewers(
                self.database, self.mission_id, expected_count=1, workspace=self.workspace,
            )
        status = self.connection.execute(
            "SELECT status,error FROM mission_tasks WHERE task_id='review-task'"
        ).fetchone()
        self.assertEqual(status, ("failed", "different failure"))

    def test_refuses_recovery_when_prior_report_is_missing_or_unpinned(self):
        path = self.workspace / "reports/protocol_forensics.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        report["evidence_validation"]["inspection_commit_sha"] = "c" * 40
        path.write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(ReviewerRecoveryError, "commit/tree pin mismatch"):
            requeue_failed_reviewers(
                self.database, self.mission_id, expected_count=1, workspace=self.workspace,
            )
        status = self.connection.execute(
            "SELECT status FROM mission_tasks WHERE task_id='review-task'"
        ).fetchone()[0]
        self.assertEqual(status, "failed")


if __name__ == "__main__":
    unittest.main()
