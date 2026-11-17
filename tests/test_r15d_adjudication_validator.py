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

    def test_reviewer_identity_whitespace_cannot_bypass_distinctness(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [self.completed_review(case, "reviewer-a"), self.completed_review(case, " reviewer-a ")]
        case["consensus"] = {"status": "adjudicated", "label": "present", "rationale": "same identity", "disagreement": False}
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("reviewer IDs must be distinct" in error for error in result["errors"]))

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

    def test_pending_consensus_cannot_be_treated_as_adjudicated(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [self.completed_review(case, "reviewer-a"), self.completed_review(case, "reviewer-b")]
        case["consensus"] = {"status": "pending", "label": "present", "rationale": "not finalized", "disagreement": False}
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("consensus must be adjudicated" in error for error in result["errors"]))

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


    def test_non_object_packet_returns_validation_error_not_exception(self):
        for packet in (None, [], "not-a-packet", 7):
            with self.subTest(packet=packet):
                result = validate(packet)
                self.assertFalse(result["valid"])
                self.assertTrue(any("JSON object" in error for error in result["errors"]))

    def test_malformed_nested_control_objects_fail_closed(self):
        for field, value in (("blinding", []), ("safety", "false"), ("freeze", None)):
            packet = copy.deepcopy(self.packet)
            packet[field] = value
            with self.subTest(field=field):
                result = validate(packet)
                self.assertFalse(result["valid"])
                self.assertTrue(result["errors"])

    def test_wrong_pre_freeze_packet_state_rejected_by_validator(self):
        for field, value in (("packet_type", "ordinary_report"), ("status", "frozen_ground_truth")):
            packet = copy.deepcopy(self.packet)
            packet[field] = value
            with self.subTest(field=field):
                result = validate(packet)
                self.assertFalse(result["valid"])

    def test_non_pinned_extra_evidence_reference_rejected(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        packet["cases"][0]["reviewers"] = [
            self.completed_review(case, "reviewer-a"),
            self.completed_review(case, "reviewer-b"),
        ]
        packet["cases"][0]["reviewers"][0]["evidence_references"].append(
            "unrelated.sol:1-2#sha256:" + "a" * 64
        )
        packet["cases"][0]["consensus"] = {
            "status": "adjudicated", "label": "present",
            "rationale": "Agreement based on pinned excerpt.", "disagreement": False
        }
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("all match exact pinned" in error for error in result["errors"]))

    def test_non_object_reviewer_is_rejected_without_exception(self):
        packet = copy.deepcopy(self.packet)
        packet["cases"][0]["reviewers"][0] = ["malformed"]
        result = validate(packet)
        self.assertFalse(result["valid"])

    def test_third_adjudicator_must_be_triggered_for_disagreement(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [
            self.completed_review(case, "reviewer-a", "present"),
            self.completed_review(case, "reviewer-b", "unknown"),
        ]
        third = self.completed_review(case, "reviewer-c", "present")
        third["triggered"] = False
        case["third_adjudicator"] = third
        case["consensus"] = {
            "status": "adjudicated", "label": "present",
            "rationale": "Third reviewer resolves disagreement.",
            "disagreement": True,
        }
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("explicitly marked triggered" in error for error in result["errors"]))

    def test_unused_third_adjudicator_must_remain_blank_on_unanimity(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [
            self.completed_review(case, "reviewer-a", "present"),
            self.completed_review(case, "reviewer-b", "present"),
        ]
        case["third_adjudicator"]["reviewer_id"] = "unexpected-reviewer"
        case["consensus"] = {
            "status": "adjudicated", "label": "present",
            "rationale": "Both independent reviewers agree.",
            "disagreement": False,
        }
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("unused third-adjudicator record must remain blank" in error for error in result["errors"]))

    def test_malformed_third_adjudicator_rejected_without_exception(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [
            self.completed_review(case, "reviewer-a", "present"),
            self.completed_review(case, "reviewer-b", "present"),
        ]
        case["third_adjudicator"] = []
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("third_adjudicator must be an object" in error for error in result["errors"]))


    def test_unhashable_case_ids_are_rejected_without_exception(self):
        for bad_id in ([], {}, ["NAV-01"]):
            packet = copy.deepcopy(self.packet)
            packet["cases"][0]["id"] = bad_id
            with self.subTest(bad_id=bad_id):
                result = validate(packet)
                self.assertFalse(result["valid"])
                self.assertTrue(any("case set" in error for error in result["errors"]))

    def test_duplicate_and_extra_case_ids_are_rejected(self):
        for replacement in ("NAV-02", "UNEXPECTED-CASE"):
            packet = copy.deepcopy(self.packet)
            packet["cases"][0]["id"] = replacement
            with self.subTest(replacement=replacement):
                result = validate(packet)
                self.assertFalse(result["valid"])
                self.assertTrue(any("no duplicates or extras" in error for error in result["errors"]))

    def test_malformed_third_adjudicator_on_disagreement_is_rejected_without_exception(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [
            self.completed_review(case, "reviewer-a", "present"),
            self.completed_review(case, "reviewer-b", "unknown"),
        ]
        case["third_adjudicator"] = []
        case["consensus"] = {
            "status": "adjudicated", "label": "present",
            "rationale": "must not bypass third adjudication",
            "disagreement": True,
        }
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("third_adjudicator" in error for error in result["errors"]))

    def test_malformed_consensus_object_is_rejected_without_exception(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        case["reviewers"] = [
            self.completed_review(case, "reviewer-a"),
            self.completed_review(case, "reviewer-b"),
        ]
        case["consensus"] = ["adjudicated", "present"]
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("consensus" in error for error in result["errors"]))

    def test_duplicate_reviewer_evidence_references_are_rejected(self):
        packet = copy.deepcopy(self.packet)
        case = packet["cases"][0]
        evidence = self.evidence(case)
        first = self.completed_review(case, "reviewer-a")
        second = self.completed_review(case, "reviewer-b")
        first["evidence_references"] = evidence + evidence
        case["reviewers"] = [first, second]
        case["consensus"] = {
            "status": "adjudicated", "label": "present",
            "rationale": "duplicate evidence must not be accepted",
            "disagreement": False,
        }
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("exact pinned" in error for error in result["errors"]))

    def test_pre_freeze_timestamp_must_remain_null(self):
        packet = copy.deepcopy(self.packet)
        packet["freeze"]["frozen_at"] = "2026-11-17T00:00:00Z"
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("frozen_at must remain null" in error for error in result["errors"]))

    def test_unknown_nested_fields_are_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["cases"][0]["consensus"]["unexpected"] = "extra"
        result = validate(packet)
        self.assertFalse(result["valid"])
        self.assertTrue(any("consensus must contain exactly" in error for error in result["errors"]))

    def test_schema_version_and_allowed_labels_are_enforced(self):
        for field, value in (("schema_version", "2.0"), ("allowed_labels", ["present"])):
            packet = copy.deepcopy(self.packet)
            packet[field] = value
            with self.subTest(field=field):
                result = validate(packet)
                self.assertFalse(result["valid"])


    def test_primary_reviewer_identity_must_be_stable_across_all_six_cases(self):
        packet = copy.deepcopy(self.packet)
        for case in packet["cases"]:
            case["reviewers"] = [
                self.completed_review(case, "reviewer-a"),
                self.completed_review(case, "reviewer-b"),
            ]
            case["consensus"] = {
                "status": "adjudicated", "label": "present",
                "rationale": "Both primary reviewers independently agree.",
                "disagreement": False,
            }
        packet["cases"][3]["reviewers"][0]["reviewer_id"] = "substitute-reviewer"
        result = validate(packet, require_complete=True)
        self.assertFalse(result["valid"])
        self.assertTrue(any("stable reviewer identity" in error for error in result["errors"]))

    def test_primary_reviewer_slots_must_remain_globally_distinct(self):
        packet = copy.deepcopy(self.packet)
        for case in packet["cases"]:
            case["reviewers"] = [
                self.completed_review(case, "reviewer-a"),
                self.completed_review(case, "reviewer-b"),
            ]
            case["consensus"] = {
                "status": "adjudicated", "label": "present",
                "rationale": "Both primary reviewers independently agree.",
                "disagreement": False,
            }
        packet["cases"][4]["reviewers"][1]["reviewer_id"] = "reviewer-a"
        result = validate(packet, require_complete=True)
        self.assertFalse(result["valid"])
        self.assertTrue(any("globally distinct" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
