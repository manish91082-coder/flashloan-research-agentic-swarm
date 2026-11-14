# Candidate audit: 0xTwyne/twyne-liquidation-bot

- **Assessment:** B (provisional; independent reviewer pending)
- **Purpose:** Twyne protocol liquidation bot for Euler-based collateral vaults and Aave V3 collateral-vault integrations. The on-chain liquidators use Morpho Blue flash loans to obtain the target debt asset, execute Twyne/EVC liquidation flows, swap seized underlying collateral back to the flash-loaned asset through a configured router (README identifies 1inch), repay Morpho and enforce a caller-specified minimum profit.
- **Repository identity:** GitHub repository ID `1162466457`; default branch `main`; MIT license reported by GitHub; not a fork in current repository metadata. README states it was forked from Euler's liquidation-bot-v2 main-base branch.
- **Pinned source:** commit `568a6308adf82952a156b6374ae264643a0c4fc2`; tree `7a24b296c6c0947d95c2a6f54921a33fa4b5575f`; latest commit metadata retrieved from GitHub; repository was pushed 2026-09-15.
- **Inspected blob pins:**
  - `contracts/TwyneLiquidator.sol`: `f343a3c841d3c1dc9dc089252ec223ddf8fe7d8c`
  - `contracts/TwyneAaveLiquidator.sol`: `e7e802b0000d72b8335c09a31ad62f6827b2c79e`
  - `contracts/HealthStatViewer.sol`: `f1bc7f71bba3d0f1c196f763f3b397ef2914c6cb`
  - `test/LiquidatorTest.t.sol`: `c751d48df2813cec90c6c23404145a91a605caa1`
  - `test/AaveLiquidatorTest.t.sol`: `824815c0c989dae35327cd25ebbe9988b99c7dcd`
  - `README.md`: `33c32ab26570ca368c9cdde6cfebbae7c33bcdb3`
  - `pyproject.toml`: `64d01ee3fe3753faec61f10a0acf14da500acfde`

## What the code actually does

This is not a generic Aave liquidation bot. It liquidates Twyne collateral vaults, including Twyne's own Euler-based collateral vault path and a separate Aave V3 collateral-vault integration. Both Solidity liquidators call the fixed Morpho Blue flash-loan contract, use EVC batches to liquidate/repay/withdraw collateral, swap underlying collateral through an owner-configured router using caller-provided calldata, and rely on Morpho to pull repayment after the callback. The outer function measures the target-asset balance delta and requires it to meet `minProfit`.

## Positive evidence

1. **Callback authentication:** `onMorphoFlashLoan` requires `msg.sender == address(MORPHO)` in both liquidator contracts.
2. **Minimum realized profit:** Both internal liquidation paths calculate `postBalance - initBalance` after the flash-loan callback and require `profit >= minProfit`. This is stronger than merely checking gross swap output before gas.
3. **Approval lifecycle:** The normal debt-bearing paths set the necessary approvals and reset them to zero after the flash-loan operation.
4. **Router-call failure propagation:** The callback checks the low-level router call's success flag and bubbles revert data or throws a custom error.
5. **Vault identity and eligibility checks:** Internal liquidation validates the collateral vault against the configured factory and checks `canLiquidate()`; external liquidation checks factory membership and external-liquidation status.
6. **Substantial test artifacts:** Foundry tests cover internal liquidation, external liquidation with/without debt, minimum-profit reverts, owner-only sweeps, router changes and allowance reset. A separate Aave liquidator test file covers Aave-vault paths. These are source-presence observations, not test results from this research run.

## Findings and limitations

1. **Permissionless trigger, owner-directed proceeds (design/incentive concern).** The main liquidation entry points are external and not owner-only, while profit remains in the contract and `sweep` is owner-only. A third party can pay gas to trigger a profitable liquidation whose proceeds are controlled by the configured owner. This may be intentional keeper architecture, but the incentive and access model should be explicit.
2. **Caller-supplied router calldata requires strict trust/configuration review.** The contract approves the configured router for the underlying collateral and executes caller-provided `dexData`. The router is owner-configurable and approval is reset after the normal debt-bearing path. The router address, calldata semantics, recipient, token route and allowance scope must be validated by the off-chain bot and deployment configuration. The current contract source alone does not prove arbitrary calldata is safe.
3. **Router allowance is temporarily set to max.** Although reset after successful execution, the allowance is `type(uint256).max` during the transaction. Atomicity reduces persistence, but a trusted-router assumption remains central.
4. **Zero-debt external-liquidation branch has no profit gate.** The `liquidateExtLiquidatedCollateralVaultZeroDebt` path performs EVC batch operations and emits an event without the same `minProfit` check used by debt-bearing flash-loan paths. This may be appropriate because there is no flash loan/swap in that branch, but returned profit semantics and caller incentives need separate validation.
5. **No generic cross-protocol scope.** The inspected contracts target Twyne collateral vault interfaces and a fixed Morpho Blue flash-loan address; they should not be classified as generic Aave/Compound liquidators.
6. **Test execution not performed.** The repository includes active Foundry tests that require a mainnet fork and manufactured live-protocol state; this audit only inspected the test source and configuration. No build, test, fork, deployment, wallet, or transaction was run.
7. **Operational dependencies.** README describes Python bot operation, 1inch swap API, secrets via 1Password/AWS options, Docker/systemd, and monitoring. The project is therefore more operationally mature than the small prototypes, but it is not zero-dependency/zero-cost.

## Verdict

A substantive protocol-specific liquidation system with Morpho flash-loan integration, separate Euler/Twyne and Aave-vault implementations, explicit minimum-profit gates, callback authentication, allowance reset and meaningful fork-based tests. Its principal diligence focus is the trust boundary around caller-provided router calldata and the owner-directed profit model. Provisional grade B; independent reviewer and actual test execution remain pending.

## Evidence links

- [Pinned Euler/Twyne liquidator](https://github.com/0xTwyne/twyne-liquidation-bot/blob/568a6308adf82952a156b6374ae264643a0c4fc2/contracts/TwyneLiquidator.sol)
- [Pinned Aave liquidator](https://github.com/0xTwyne/twyne-liquidation-bot/blob/568a6308adf82952a156b6374ae264643a0c4fc2/contracts/TwyneAaveLiquidator.sol)
- [Pinned Euler/Twyne tests](https://github.com/0xTwyne/twyne-liquidation-bot/blob/568a6308adf82952a156b6374ae264643a0c4fc2/test/LiquidatorTest.t.sol)
- [Pinned Aave tests](https://github.com/0xTwyne/twyne-liquidation-bot/blob/568a6308adf82952a156b6374ae264643a0c4fc2/test/AaveLiquidatorTest.t.sol)
- [Pinned README](https://github.com/0xTwyne/twyne-liquidation-bot/blob/568a6308adf82952a156b6374ae264643a0c4fc2/README.md)

**Review status:** source inspection completed; independent reviewer pending; no execution.
