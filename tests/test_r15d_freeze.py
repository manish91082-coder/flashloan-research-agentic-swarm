import json
import tempfile
import unittest
from pathlib import Path

from scripts.freeze_r15d_adjudication import freeze
from scripts.validate_r15d_adjudication import DEFAULT_PACKET


class R15DFreezeTests(unittest.TestCase):
    def completed_review(self, case, reviewer_id, label):
        return {
            "reviewer_id": reviewer_id,
            "label": label,
            "rationale": "Bounded proposition checked against the pinned source excerpt.",
            "evidence_references": [f'{case["path"]}:{case["line_start"]}-{case["line_end"]}#sha256:{case["excerpt_sha256"]}'],
            "confidence": 0.9,
            "completed_at": "2026-11-17T00:00:00Z",
            "independence_attestation": True,
        }

    def complete_packet(self):
        packet = json.loads(DEFAULT_PACKET.read_text(encoding="utf-8"))
        for case in packet["cases"]:
            case["reviewers"] = [
                self.completed_review(case, case["id"] + "-reviewer-a", "present"),
                self.completed_review(case, case["id"] + "-reviewer-b", "present"),
            ]
            case["consensus"] = {
                "status": "adjudicated",
                "label": "present",
                "rationale": "Both independent reviewers agree on the bounded source fact.",
                "disagreement": False,
            }
        return packet

    def test_freeze_writes_separate_manifest_and_preserves_input(self):
        packet = self.complete_packet()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "blind.json"
            output = root / "frozen.json"
            source.write_text(json.dumps(packet), encoding="utf-8")
            original = source.read_bytes()
            digest = freeze(source, output, "2026-11-17T00:00:00Z")
            frozen = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(frozen["status"], "frozen_ground_truth")
            self.assertTrue(frozen["freeze"]["ground_truth_frozen"])
            self.assertFalse(frozen["freeze"]["model_inference_authorized"])
            self.assertEqual(len(digest), 64)

    def test_incomplete_packet_cannot_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "frozen.json"
            with self.assertRaises(ValueError):
                freeze(DEFAULT_PACKET, output, "2026-11-17T00:00:00Z")
            self.assertFalse(output.exists())

    def test_invalid_or_non_utc_freeze_timestamp_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "blind.json"
            output = Path(tmp) / "frozen.json"
            source.write_text(json.dumps(self.complete_packet()), encoding="utf-8")
            for timestamp in ("yesterday", "2026-11-17T05:30:00+05:30"):
                with self.subTest(timestamp=timestamp):
                    with self.assertRaises(ValueError):
                        freeze(source, output, timestamp)
                    self.assertFalse(output.exists())

    def test_noncanonical_packet_state_cannot_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "blind.json"
            output = root / "frozen.json"
            for field, value in (("status", "frozen_ground_truth"), ("packet_type", "ordinary_report")):
                packet = self.complete_packet()
                packet[field] = value
                source.write_text(json.dumps(packet), encoding="utf-8")
                with self.subTest(field=field):
                    with self.assertRaises(ValueError):
                        freeze(source, output, "2026-11-17T00:00:00Z")
                    self.assertFalse(output.exists())

    def test_existing_frozen_manifest_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "blind.json"
            output = Path(tmp) / "frozen.json"
            source.write_text(json.dumps(self.complete_packet()), encoding="utf-8")
            output.write_text("immutable", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                freeze(source, output, "2026-11-17T00:00:00Z")
            self.assertEqual(output.read_text(encoding="utf-8"), "immutable")

    def test_malformed_top_level_json_values_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "blind.json"
            output = root / "frozen.json"
            for value in ([], "not-an-object", 7, None):
                source.write_text(json.dumps(value), encoding="utf-8")
                with self.subTest(value=value):
                    with self.assertRaisesRegex(ValueError, "JSON object"):
                        freeze(source, output, "2026-11-17T00:00:00Z")
                    self.assertFalse(output.exists())

    def test_malformed_nested_gate_objects_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "blind.json"
            output = root / "frozen.json"
            for field, value in (("freeze", []), ("blinding", "invalid"), ("safety", None)):
                packet = self.complete_packet()
                packet[field] = value
                source.write_text(json.dumps(packet), encoding="utf-8")
                with self.subTest(field=field):
                    with self.assertRaises(ValueError):
                        freeze(source, output, "2026-11-17T00:00:00Z")
                    self.assertFalse(output.exists())

    def test_invalid_json_fails_with_controlled_validation_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "blind.json"
            output = Path(tmp) / "frozen.json"
            source.write_text("{not valid json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "valid adjudication JSON"):
                freeze(source, output, "2026-11-17T00:00:00Z")
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
