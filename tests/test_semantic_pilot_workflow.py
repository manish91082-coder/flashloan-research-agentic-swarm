from __future__ import annotations

import unittest
from pathlib import Path


class SemanticPilotWorkflowContractTests(unittest.TestCase):
    def test_artifact_upload_is_scoped_to_triggered_mission(self):
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "agentic-semantic-pilot.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("echo \"database=$DATABASE\" >> \"$GITHUB_OUTPUT\"", workflow)
        self.assertIn("echo \"artifact_root=$ARTIFACT_ROOT\" >> \"$GITHUB_OUTPUT\"", workflow)
        self.assertIn(
            "name: flashloan-agent-form-semantic-pilot-${{ steps.seed.outputs.mission_id }}",
            workflow,
        )
        self.assertIn("${{ steps.seed.outputs.database }}", workflow)
        self.assertIn("${{ steps.seed.outputs.artifact_root }}/", workflow)
        self.assertNotIn("data/agentic-mission-pilot-20261115-r4.sqlite3", workflow)
        self.assertNotIn("flashloan-agent-form-pilot-20261115-r4/", workflow)


if __name__ == "__main__":
    unittest.main()
