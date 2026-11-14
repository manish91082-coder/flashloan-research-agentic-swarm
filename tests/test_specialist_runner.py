from __future__ import annotations

import unittest

from flashloan_research.specialist_runner import SpecialistTaskError, validate_specialist_output


class SpecialistEvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.inspection = {
            "repository": "org/repo",
            "commit_sha": "a" * 40,
            "tree_sha": "b" * 40,
            "signals": [{
                "path": "contracts/Liquidator.sol",
                "line": 42,
                "signal": "executeOperation",
                "excerpt": "function executeOperation(...) external returns (bool)",
            }],
        }

    def test_accepts_only_exact_pinned_signal_reference(self):
        output = {
            "summary": "Callback implementation requires manual source review.",
            "purpose": "liquidation executor",
            "implementation_status": "partial",
            "findings": [],
            "evidence": [{
                "path": "contracts/Liquidator.sol",
                "line": 42,
                "signal": "executeOperation",
                "excerpt": "function executeOperation(...) external returns (bool)",
            }],
            "unknowns": ["Callback caller authentication not proven by this excerpt."],
            "confidence": "low",
        }
        result = validate_specialist_output(output, self.inspection)
        self.assertEqual(len(result["evidence"]), 1)
        self.assertEqual(result["evidence"][0]["commit_sha"], "a" * 40)
        self.assertEqual(len(result["rejected_evidence"]), 0)

    def test_rejects_fabricated_source_location(self):
        output = {
            "summary": "Potential issue needs full review.",
            "purpose": "liquidation executor",
            "implementation_status": "unknown",
            "findings": [],
            "evidence": [{
                "path": "contracts/Imaginary.sol",
                "line": 999,
                "signal": "onlyOwner",
                "excerpt": "function onlyOwner()",
            }],
            "unknowns": [],
            "confidence": "low",
        }
        result = validate_specialist_output(output, self.inspection)
        self.assertEqual(result["evidence"], [])
        self.assertEqual(result["rejected_evidence"][0]["reason"],
                         "not_present_in_pinned_inspection_signals")

    def test_rejects_invalid_status_or_confidence(self):
        output = {
            "summary": "x", "purpose": "x", "implementation_status": "safe",
            "findings": [], "evidence": [], "unknowns": [], "confidence": "certain",
        }
        with self.assertRaises(SpecialistTaskError):
            validate_specialist_output(output, self.inspection)


if __name__ == "__main__":
    unittest.main()
