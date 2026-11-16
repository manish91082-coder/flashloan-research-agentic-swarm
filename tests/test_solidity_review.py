from __future__ import annotations

import unittest

from flashloan_research.solidity_review import deterministic_protocol_review


class DeterministicSolidityReviewTests(unittest.TestCase):
    def test_aave_complete_callback_reports_observed_guards_and_repayment(self):
        source = """
        constructor(address provider) {
            ADDRESSES_PROVIDER = IPoolAddressesProvider(provider);
            POOL = IPool(provider);
        }
        function executeOperation(address asset,uint256 amount,uint256 premium,address initiator,bytes calldata params) external returns (bool) {
            require(msg.sender == address(POOL), "pool");
            require(initiator == address(this), "initiator");
            uint256 owed = amount + premium;
            IERC20(asset).approve(address(POOL), owed);
            return true;
        }
        """
        result = deterministic_protocol_review("org/aave-liquidator", [{"excerpt": source, "evidence_ids": ["EV00001"]}])
        topics = result["topics"]
        self.assertEqual(topics["callback_authentication"]["status"], "source_observed")
        self.assertIn("trusted-caller comparison visible", topics["callback_authentication"]["detail"])
        self.assertIn("initiator/address(this) binding visible", topics["callback_authentication"]["detail"])
        self.assertIn("amount + premium arithmetic visible", topics["repayment_premium"]["detail"])
        self.assertEqual(topics["pool_provider_wiring"]["status"], "source_observed")
        self.assertEqual(topics["callback_authentication"]["evidence_ids"], ["EV00001"])
        self.assertFalse(result["exploitability_assessed"])

    def test_aave_partial_excerpt_fails_closed(self):
        result = deterministic_protocol_review("org/aave-liquidator", [{"excerpt": "function executeOperation(...) external {"}])
        self.assertEqual(result["topics"]["callback_authentication"]["status"], "unknown")
        self.assertEqual(result["topics"]["repayment_premium"]["status"], "unknown")

    def test_aave_does_not_invent_evidence_ids(self):
        result = deterministic_protocol_review("org/aave-liquidator", [{"excerpt": "function executeOperation() {}", "evidence_ids": ["EV99999", "fabricated"]}])
        self.assertEqual(result["topics"]["callback_authentication"]["evidence_ids"], [])

    def test_uniswap_placeholder_and_pair_auth_pattern(self):
        source = """
        function uniswapV2Call(address sender,uint amount0,uint amount1,bytes calldata data) external {
            require(msg.sender == pair, "pair");
            // TODO repay
            IERC20(token0).transfer(msg.sender, amount0);
        }
        address token0;
        address token1;
        function reserves() external view { pair.getReserves(); }
        """
        result = deterministic_protocol_review("org/uniswap-flashswap", [{"excerpt": source}])
        topics = result["topics"]
        self.assertIn("placeholder", topics["callback_implementation"]["detail"])
        self.assertIn("guard pattern", topics["pair_authentication"]["detail"])
        self.assertEqual(topics["token_order_reserves"]["status"], "source_observed")
        self.assertIn("transfer call", topics["repayment"]["detail"])

    def test_unknown_protocol_and_no_source(self):
        result = deterministic_protocol_review("org/other", [])
        self.assertEqual(result["status"], "unsupported_protocol")
        aave = deterministic_protocol_review("org/aave", [])
        self.assertEqual(aave["topics"]["callback_authentication"]["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
