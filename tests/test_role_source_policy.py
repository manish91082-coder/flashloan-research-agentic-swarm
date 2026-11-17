from __future__ import annotations

import unittest

from flashloan_research.role_source_policy import order_role_source_manifest, role_path_admissible


class RoleSourcePolicyTests(unittest.TestCase):
    def setUp(self):
        self.manifest = [
            {"path": "bot.js", "blob_sha": "a" * 40},
            {"path": "contracts/AaveLiquidator.sol", "blob_sha": "b" * 40},
            {"path": "package.json", "blob_sha": "c" * 40},
            {"path": "tests/test_liquidation.py", "blob_sha": "d" * 40},
            {"path": "LICENSE", "blob_sha": "e" * 40},
            {"path": ".github/workflows/ci.yml", "blob_sha": "f" * 40},
        ]

    def test_protocol_roles_prioritize_contract_over_large_bot_path(self):
        expected_families = {
            "candidate_purpose": "protocol_contract",
            "protocol_specialist": "protocol_contract",
            "solidity_security": "protocol_contract",
            "execution_engineer": "execution_contract",
            "independent_reviewer": "protocol_contract",
        }
        for role, expected_family in expected_families.items():
            ordered, coverage = order_role_source_manifest(role, self.manifest)
            self.assertEqual(ordered[0]["path"], "contracts/AaveLiquidator.sol")
            self.assertIn(expected_family, coverage["present_families"])

    def test_dependency_role_prioritizes_manifest_then_license(self):
        ordered, coverage = order_role_source_manifest("dependency_license", self.manifest)
        self.assertEqual(ordered[0]["path"], "package.json")
        self.assertIn("dependency_manifest", coverage["present_families"])
        self.assertIn("license_artifact", coverage["present_families"])

    def test_test_role_prioritizes_test_and_ci_sources(self):
        ordered, coverage = order_role_source_manifest("test_verification", self.manifest)
        paths = [item["path"] for item in ordered]
        self.assertLess(paths.index("tests/test_liquidation.py"),
                        paths.index("bot.js"))
        self.assertLess(paths.index(".github/workflows/ci.yml"),
                        paths.index("bot.js"))
        self.assertIn("test_source", coverage["present_families"])

    def test_missing_required_family_is_explicit(self):
        ordered, coverage = order_role_source_manifest(
            "dependency_license", [{"path": "bot.js"}]
        )
        self.assertEqual(coverage["coverage_status"], "incomplete")
        self.assertEqual(ordered, [], "dependency role must not receive unrelated execution source")
        self.assertEqual(set(coverage["missing_families"]),
                         {"dependency_manifest", "compiler_build_config", "license_artifact"})

    def test_unknown_role_fails_closed(self):
        with self.assertRaises(ValueError):
            order_role_source_manifest("unregistered_role", self.manifest)

    def test_dependency_findings_cannot_cite_bot_or_contract_execution_paths(self):
        self.assertTrue(role_path_admissible("dependency_license", "package.json"))
        self.assertTrue(role_path_admissible("dependency_license", "LICENSE"))
        self.assertFalse(role_path_admissible("dependency_license", "bot.js"))
        self.assertFalse(role_path_admissible("dependency_license", "contracts/Liquidator.sol"))

    def test_test_findings_require_test_ci_or_test_configuration_sources(self):
        self.assertTrue(role_path_admissible("test_verification", "tests/test_bot.py"))
        self.assertTrue(role_path_admissible("test_verification", ".github/workflows/ci.yml"))
        self.assertFalse(role_path_admissible("test_verification", "bot.js"))


if __name__ == "__main__":
    unittest.main()
