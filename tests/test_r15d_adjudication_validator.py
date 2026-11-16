import copy
import json
import unittest

from scripts.validate_r15d_adjudication import DEFAULT_PACKET, validate


class R15DAdjudicationValidatorTests(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads(DEFAULT_PACKET.read_text(encoding="utf-8"))

    def evidence(self, case):
        return [f'{case["path"]}:{case["line_start"]}-{case["line_end"]}#sha256:{case["excerpt_sha256"]}']

    def completed_review(self, case, reviewer_id, label="present"):
        return {
            "reviewer_id": reviewer_id,
            "label": label,
            "rationale": "The cited source lines directly support this bounded proposition.",
            "evidence_references": self.evidence(case),
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
        case["reviewers"] = [self.completed_review(case, "reviewer-a"), self.completed_review(case, "reviewer-a")]
        case["consensus"] = {"status": "adjudicated", "label": "present", "rationale": "same", "disagreement": False}
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("distinct" in error for error in result["errors"]))

    def test_disagreement_requires_third_independent_adjudicator(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [self.completed_review(case, "reviewer-a", "present"), self.completed_review(case, "reviewer-b", "unknown")]
        case["consensus"] = {"status": "pending", "label": "present", "rationale": "reconciled", "disagreement": True}
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("third adjudication" in error for error in result["errors"]))

    def test_disagreement_rejects_reused_third_reviewer(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [self.completed_review(case, "reviewer-a", "present"), self.completed_review(case, "reviewer-b", "unknown")]
        case["third_adjudicator"] = self.completed_review(case, "reviewer-a", "present")
        case["consensus"] = {"status": "adjudicated", "label": "present", "rationale": "Third reviewer resolved it.", "disagreement": True}
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("third adjudicator must be distinct" in error for error in result["errors"]))

    def test_unanimous_consensus_must_match_reviewers(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [self.completed_review(case, "reviewer-a", "present"), self.completed_review(case, "reviewer-b", "present")]
        case["consensus"] = {"status": "adjudicated", "label": "absent", "rationale": "incorrect", "disagreement": False}
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("unanimous reviewer labels" in error for error in result["errors"]))

    def test_non_utc_or_invalid_timestamp_rejected(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [self.completed_review(case, "reviewer-a"), self.completed_review(case, "reviewer-b")]
        case["reviewers"][0]["completed_at"] = "yesterday"
        case["consensus"] = {"status": "adjudicated", "label": "present", "rationale": "agreement", "disagreement": False}
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("pending" in error for error in result["errors"]))

    def test_source_pin_tampering_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["cases"][0]["commit_sha"] = "0" * 40
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("immutable source pin" in error for error in result["errors"]))

    def test_evidence_must_match_exact_case_pin(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [self.completed_review(case, "reviewer-a"), self.completed_review(case, "reviewer-b")]
        case["reviewers"][0]["evidence_references"] = ["pinned-file.sol:10-12#sha256:" + "0" * 64]
        case["consensus"] = {"status": "adjudicated", "label": "present", "rationale": "agreement", "disagreement": False}
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("exact pinned" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
