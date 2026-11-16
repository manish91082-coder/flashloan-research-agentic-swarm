from __future__ import annotations

import unittest

from flashloan_research.specialist_runner import _deterministic_review_with_catalog


class DeterministicReviewEvidenceResolutionTests(unittest.TestCase):
    def setUp(self):
        self.inspection = {
            "repository": "example/aave-liquidator",
            "commit_sha": "a" * 40,
            "tree_sha": "b" * 40,
            "signals": [
                {"path": "contracts/Liquidator.sol", "line": 12, "signal": "aave_execute_operation",
                 "excerpt": "function executeOperation()"},
                {"path": "contracts/Liquidator.sol", "line": 20, "signal": "aave_flash_loan_simple",
                 "excerpt": "IPool(provider)"},
            ],
        }
        self.source = [{
            "path": "contracts/Liquidator.sol", "start_line": 10, "end_line": 22,
            "blob_sha": "c" * 40,
            "excerpt": "001010: constructor(address provider) {\n001012: POOL = IPool(provider);\n"
                       "001020: function executeOperation() external {\n001022: }",
        }]

    def test_only_exact_path_and_overlapping_lines_resolve(self):
        result = _deterministic_review_with_catalog(self.inspection, self.source)
        ids = {e for topic in result["topics"].values() for e in topic["evidence_ids"]}
        self.assertEqual(ids, {"EV00001", "EV00002"})
        self.assertEqual(result["inspection_commit_sha"], "a" * 40)
        self.assertEqual(result["evidence_resolution"], "exact_path_line_overlap_and_topic_signal_allowlist")


    def test_aave_topics_receive_only_their_own_signal_ids(self):
        result = _deterministic_review_with_catalog(self.inspection, self.source)
        topics = result["topics"]
        self.assertEqual(topics["pool_provider_wiring"]["evidence_ids"], ["EV00002"])
        self.assertEqual(topics["callback_authentication"]["evidence_ids"], ["EV00001"])
        self.assertEqual(topics["repayment_premium"]["evidence_ids"], ["EV00001"])

    def test_unrelated_signal_in_same_excerpt_is_not_assigned_to_topic(self):
        inspection = {
            **self.inspection,
            "signals": self.inspection["signals"] + [
                {"path": "contracts/Liquidator.sol", "line": 15,
                 "signal": "min_profit_guard", "excerpt": "minProfit"}
            ],
        }
        result = _deterministic_review_with_catalog(inspection, self.source)
        all_ids = {e for topic in result["topics"].values() for e in topic["evidence_ids"]}
        self.assertNotIn("EV00003", all_ids)

    def test_wrong_path_does_not_resolve_catalog_ids(self):
        excerpts = [{**self.source[0], "path": "other.sol"}]
        result = _deterministic_review_with_catalog(self.inspection, excerpts)
        self.assertTrue(all(not topic["evidence_ids"] for topic in result["topics"].values()))

    def test_non_overlapping_lines_do_not_resolve_catalog_ids(self):
        excerpts = [{**self.source[0], "start_line": 30, "end_line": 40}]
        result = _deterministic_review_with_catalog(self.inspection, excerpts)
        self.assertTrue(all(not topic["evidence_ids"] for topic in result["topics"].values()))


if __name__ == "__main__":
    unittest.main()
