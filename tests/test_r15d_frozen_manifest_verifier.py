import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.freeze_r15d_adjudication import freeze
from scripts.verify_r15d_frozen_manifest import verify_frozen_manifest
from scripts.validate_r15d_adjudication import DEFAULT_PACKET


class R15DFrozenManifestVerifierTests(unittest.TestCase):
    def completed_review(self, case, reviewer_id):
        return {
            "reviewer_id": reviewer_id,
            "label": "present",
            "rationale": "The pinned excerpt supports this bounded proposition.",
            "evidence_references": [
                f'{case["path"]}:{case["line_start"]}-{case["line_end"]}#sha256:{case["excerpt_sha256"]}'
            ],
            "confidence": 0.9,
            "completed_at": "2026-11-17T00:00:00Z",
            "independence_attestation": True,
        }

    def complete_packet(self):
        packet = json.loads(DEFAULT_PACKET.read_text(encoding="utf-8"))
        for case in packet["cases"]:
            case["reviewers"] = [
                self.completed_review(case, "reviewer-a"),
                self.completed_review(case, "reviewer-b"),
            ]
            case["consensus"] = {
                "status": "adjudicated",
                "label": "present",
                "rationale": "Both independent reviewers agree.",
                "disagreement": False,
            }
        return packet

    def write_frozen_pair(self, root):
        packet_path = root / "blind.json"
        manifest_path = root / "frozen.json"
        packet_path.write_text(json.dumps(self.complete_packet(), indent=2) + "\n", encoding="utf-8")
        digest = freeze(packet_path, manifest_path, "2026-11-17T00:00:00Z")
        return packet_path, manifest_path, digest

    def test_valid_manifest_reverifies_exact_input_and_output_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_path, manifest_path, digest = self.write_frozen_pair(Path(tmp))
            result = verify_frozen_manifest(packet_path, manifest_path, digest)
            self.assertTrue(result["valid"])
            self.assertEqual(result["completed_cases"], 6)
            self.assertEqual(result["case_count"], 6)
            self.assertEqual(result["frozen_manifest_sha256"], digest)
            self.assertFalse(result["model_inference_authorized"])

    def test_input_byte_change_invalidates_manifest_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_path, manifest_path, _ = self.write_frozen_pair(Path(tmp))
            packet_path.write_bytes(packet_path.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "provenance"):
                verify_frozen_manifest(packet_path, manifest_path)

    def test_manifest_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_path, manifest_path, _ = self.write_frozen_pair(Path(tmp))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["freeze_provenance"]["input_packet_sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "provenance"):
                verify_frozen_manifest(packet_path, manifest_path)

    def test_expected_manifest_digest_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_path, manifest_path, _ = self.write_frozen_pair(Path(tmp))
            with self.assertRaisesRegex(ValueError, "expected digest"):
                verify_frozen_manifest(packet_path, manifest_path, "0" * 64)

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_path, manifest_path, _ = self.write_frozen_pair(Path(tmp))
            manifest_path.write_text('{"status":"frozen_ground_truth","status":"tampered"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate-free"):
                verify_frozen_manifest(packet_path, manifest_path)

    def test_input_and_manifest_must_be_separate_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_path, _, _ = self.write_frozen_pair(Path(tmp))
            with self.assertRaisesRegex(ValueError, "separate files"):
                verify_frozen_manifest(packet_path, packet_path)


if __name__ == "__main__":
    unittest.main()
