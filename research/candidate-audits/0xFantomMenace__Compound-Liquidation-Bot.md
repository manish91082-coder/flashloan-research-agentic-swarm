# Candidate audit: 0xFantomMenace/Compound-Liquidation-Bot

- **Assessment:** D (provisional; critical implementation defects; independent review pending)
- **Purpose:** Compound V3/Comet liquidation and collateral-purchase bot. The contract calls `Comet.absorb`, then uses a Uniswap V3 flash loan to buy protocol-held collateral and swaps it back to base token.
- **Repository identity:** GitHub repository ID `1113845890`; default branch `main`; not a fork; GitHub metadata reports no license.
- **Pinned source:** commit `62695b315a7c3ea4b9cb4daa8587119d33abae1c`; tree `67da1bdba755f7a2e3701b91b36eea205dfd3a39`; author date 2025-12-10.
- **Inspected blob pins:**
  - `src/Liquidator.sol`: `a6ddf6faaa01f81c21fa5a08a51b74d8c54ac0f4`
  - `bot/scripts/executeLiquidation.ts`: `11c081e1818116b1952204712266f4a50b7f1b54`
  - `bot/scripts/getLiquidatable.ts`: `4b0abe6e62bbab132546eb6376cccb08f384f287`
  - `bot/helpers/constants.ts`: `91fcdf95857a213c92567cb56d938891960f2f95`
  - `test/Liquidator.t.sol`: `409146d4c0f3aca24872569138717e3fa1dfab33`
  - `README.md`: `e39e25911f7b726f8cfb8b931de57ee54a2ad85a`

## What the code actually does

The Solidity contract absorbs an array of underwater accounts through Compound Comet. If collateral purchases are not paused and Comet base reserves are below target, it estimates costs for each configured collateral reserve, borrows base token through a Uniswap V3 pool flash callback, buys collateral from Comet, swaps collateral through WETH to base token, repays the pool and sends remaining base-token balance to owner. The TypeScript bot discovers users, batches eligibility checks and sends batches to the contract.

This is not a classic Aave-style flash loan used to repay the user's debt. It is a Compound V3 absorb plus flash-funded collateral-purchase/arb design.

## Findings and limitations

1. **Critical array construction bug (high confidence, execution-blocking).** `purchasableCount` sizes `purchasableCollaterals`, but the following loop writes using the original reserve index `k` instead of a compact output index. If any earlier reserve has zero collateral reserves and a later reserve is purchasable, `purchasableCollaterals[k]` can exceed the new array length and revert; if zero entries precede valid entries, the array also has uninitialized zero addresses. The code needs a separate write cursor and consistent cost-array mapping.
2. **Flash-loan asset selection relies on token-address ordering (high confidence, high impact).** The call chooses token0 vs token1 amount using `flashLoanPool.token0() > flashLoanPool.token1()`, but does not check that the pool pair actually contains `baseToken`. A wrong pool configuration borrows the wrong asset while callback logic assumes the borrowed amount is base token.
3. **Swap paths are not validated (high confidence).** `paths[collateral]` can be empty; callback indexes `poolPath[0]` and `poolPath[poolPath.length - 1]`. Missing configuration causes reverts. Path pools/tokens are not validated against the collateral/WETH/base-token route before use.
4. **Zero minimum swap output (high confidence, high economic impact).** Both Uniswap swaps set `amountOutMinimum: 0`; the later check only ensures the final output for each collateral is at least its computed purchase cost. This omits explicit price-impact/slippage bounds and does not by itself protect total flash-loan repayment costs.
5. **Test file provides no executable assertions (high confidence).** `test/Liquidator.t.sol` contains only commented-out sample test code. README describes Foundry testing, but the inspected test source has no active test contract.
6. **Unused or incomplete accounting signals.** `totalAmountOut` is accumulated but not used for final profitability; the final debt-vs-balance check protects principal plus fee, but no minimum profit margin or gas-cost threshold is enforced in this contract.
7. **Potential reserve/cost index mismatch.** The same un-compacted array indexing bug can desynchronize `collaterals` and `collateralCosts`; even before an out-of-bounds revert, zero-address slots can cause incorrect token operations.
8. **No runtime proof.** No candidate code, tests, build, deployment, wallet or transaction was executed by this research project.

## Tests, dependencies, maintenance

The checked-in Foundry test is commented out. TypeScript bot uses ethers v6, JSON environment configuration and RPC/WebSocket endpoints. README marks the software UNLICENSED/private internal use. Repository creation and latest push in GitHub metadata are both 2025-12-10.

## Verdict

The repository's purpose is real and its high-level flow is identifiable, but the contract has a deterministic array-indexing defect that can revert on ordinary mixed-reserve states, relies on unvalidated flash-pool configuration, and lacks meaningful swap slippage bounds and active tests. Do not treat as production-ready. Provisional grade D.

## Evidence links

- [Pinned Liquidator.sol](https://github.com/0xFantomMenace/Compound-Liquidation-Bot/blob/62695b315a7c3ea4b9cb4daa8587119d33abae1c/src/Liquidator.sol)
- [Pinned liquidation batch executor](https://github.com/0xFantomMenace/Compound-Liquidation-Bot/blob/62695b315a7c3ea4b9cb4daa8587119d33abae1c/bot/scripts/executeLiquidation.ts)
- [Pinned eligibility batcher](https://github.com/0xFantomMenace/Compound-Liquidation-Bot/blob/62695b315a7c3ea4b9cb4daa8587119d33abae1c/bot/scripts/getLiquidatable.ts)
- [Pinned test file](https://github.com/0xFantomMenace/Compound-Liquidation-Bot/blob/62695b315a7c3ea4b9cb4daa8587119d33abae1c/test/Liquidator.t.sol)

**Review status:** source inspection completed; independent reviewer not yet run; no execution.
