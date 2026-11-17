import shutil
import unittest

from scripts.run_r15d_v2_custody_tabletop import run_tabletop


class R15DV2CustodyTabletopTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("gpg"), "GnuPG is installed only in the dedicated Python 3.11 custody tabletop job")
    def test_synthetic_receipt_bound_pipeline_and_private_permissions(self):
        result = run_tabletop()
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["synthetic_only"])
        self.assertEqual(result["primary_receipts_verified"], 2)
        self.assertEqual(result["third_receipts_verified"], 1)
        self.assertEqual(result["encrypted_submissions_verified"], 3)
        self.assertEqual(result["encryption_tool"], "GnuPG OpenPGP RSA-2048 public-key encrypted-delivery round trip")
        self.assertTrue(result["recipient_fingerprint_established"])
        self.assertTrue(result["private_key_separate_from_sender_receiver"])
        self.assertFalse(result["production_key_identity_verified_out_of_band"])
        self.assertTrue(result["primary_merge_verified"])
        self.assertTrue(result["final_adjudication_complete"])
        self.assertTrue(result["frozen_manifest_verified"])
        self.assertEqual(result["workspace_directory_mode"], "0700")
        self.assertEqual(result["private_file_mode"], "0600")
        self.assertTrue(result["workspace_removed_after_test"])
        self.assertFalse(result["model_inference_authorized"])
        self.assertFalse(result["production_reviewer_intake_authorized"])


if __name__ == "__main__":
    unittest.main()
