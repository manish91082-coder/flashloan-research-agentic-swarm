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
            {"path": "monitor/test/apiLogs.test.js", "blob_sha": "9" * 40},
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

    def test_protocol_review_roles_exclude_unrelated_monitor_tests(self):
        for role in ("solidity_security", "independent_reviewer"):
            ordered, coverage = order_role_source_manifest(role, self.manifest)
            paths = [item["path"] for item in ordered]
            self.assertIn("tests/test_liquidation.py", paths)
            self.assertNotIn("monitor/test/apiLogs.test.js", paths)

    def test_dependency_role_prioritizes_manifest_then_license(self):
        ordered, coverage = order_role_source_manifest("dependency_license", self.manifest)
        self.assertEqual(ordered[0]["path"], "package.json")
        self.assertIn("dependency_manifest", coverage["present_families"])
        self.assertIn("license_artifact", coverage["present_families"])

    def test_test_role_prioritizes_test_and_ci_sources(self):
        ordered, coverage = order_role_source_manifest("test_verification", self.manifest)
        paths = [item["path"] for item in ordered]
        self.assertLess(paths.index("tests/test_liquidation.py"),
                        paths.index(".github/workflows/ci.yml"))
        self.assertNotIn("bot.js", paths)
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

    def test_bounded_prefix_interleaves_source_families_instead_of_starving_them(self):
        manifest = [
            {"path": f"contracts/Contract{i:02d}.sol"} for i in range(12)
        ] + [
            {"path": "src/bot.js"},
            {"path": "tests/test_liquidation.py"},
            {"path": "foundry.toml"},
        ]
        ordered, coverage = order_role_source_manifest("execution_engineer", manifest)
        # The source-context loader takes a bounded prefix. A 4-file prefix
        # must include the first contract plus runtime, test and build config.
        prefix = ordered[:4]
        prefix_families = [
            next((family for family, _ in (
                ("execution_contract", ("contracts/", ".sol")),
                ("execution_runtime", ("src/", "bot.")),
                ("execution_test", ("test/", "tests/", "spec/")),
                ("execution_config", ("foundry.toml", "hardhat.config", "package.json")),
            ) if any(needle in item["path"].casefold() for needle in _)),
                 None)
            for item in prefix
        ]
        self.assertEqual(
            prefix_families,
            ["execution_contract", "execution_runtime", "execution_test", "execution_config"],
        )
        self.assertEqual(
            coverage["policy"],
            "round_robin_role_family_priority_then_deterministic_path_order",
        )
        self.assertEqual(coverage["family_file_counts"]["execution_contract"], 12)

    def test_round_robin_preserves_deterministic_order_within_each_family(self):
        manifest = [
            {"path": "contracts/Z.sol"},
            {"path": "contracts/A.sol"},
            {"path": "src/z_bot.py"},
            {"path": "src/a_bot.py"},
        ]
        ordered, _ = order_role_source_manifest("protocol_specialist", manifest)
        self.assertEqual(
            [item["path"] for item in ordered],
            ["contracts/A.sol", "src/a_bot.py", "contracts/Z.sol", "src/z_bot.py"],
        )


if __name__ == "__main__":
    unittest.main()
