import copy
import json
import unittest
from pathlib import Path

from scripts.validate_r15d_adjudication import DEFAULT_PACKET, validate


class R15DAdjudicationValidatorTests(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads(DEFAULT_PACKET.read_text(encoding="utf-8"))

    def completed_review(self, reviewer_id, label="present"):
        return {
            "reviewer_id": reviewer_id,
            "label": label,
            "rationale": "The cited source lines directly support this bounded proposition.",
            "evidence_references": ["pinned-file.sol:10-12#sha256:example"],
            "confidence": 0.9,
            "completed_at": "2026-11-17T00:00:00Z",
            "independence_attestation": True,
        }

    def test_blank_packet_is_valid_but_not_complete(self):
        result = validate(self.packet)
        self.assertTrue(result["valid"])
        self.assertFalse(result["complete"])
        self.assertEqual(result["completed_cases"], 0)

    def test_duplicate_reviewer_identity_rejected(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [self.completed_review("reviewer-a"), self.completed_review("reviewer-a")]
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("distinct" in error for error in result["errors"]))

    def test_disagreement_requires_third_independent_adjudicator(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [self.completed_review("reviewer-a", "present"), self.completed_review("reviewer-b", "unknown")]
        case["consensus"] = {"status": "pending", "label": "present", "rationale": "reconciled", "disagreement": True}
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("third adjudication" in error for error in result["errors"]))

    def test_disagreement_rejects_reused_third_reviewer(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [self.completed_review("reviewer-a", "present"), self.completed_review("reviewer-b", "unknown")]
        case["third_adjudicator"] = self.completed_review("reviewer-a", "present")
        case["consensus"] = {"status": "adjudicated", "label": "present", "rationale": "Third reviewer resolved the disagreement.", "disagreement": True}
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("third adjudicator must be distinct" in error for error in result["errors"]))

    def test_agreement_still_requires_explicit_consensus(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [self.completed_review("reviewer-a"), self.completed_review("reviewer-b")]
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("consensus label and rationale" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
