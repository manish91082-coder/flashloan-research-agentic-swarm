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
        self.assertIn('report.get("evidence_gate") != "pinned_evidence_semantic_quality_and_claim_linkage_pass"', workflow)
        self.assertIn('if decision != "accept":', workflow)
        self.assertIn('if disagreements:', workflow)
        self.assertIn("FLR_MODEL_MAX_PARALLEL_TASKS: '2'", workflow)
        self.assertIn("FLR_MODEL_CONTEXT_TOKENS: '16384'", workflow)
        self.assertIn("OLLAMA_NUM_PARALLEL: '2'", workflow)
        self.assertIn('Independent review did not accept', workflow)


if __name__ == "__main__":
    unittest.main()
