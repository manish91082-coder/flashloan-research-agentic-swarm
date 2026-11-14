# Candidate audit: 0xTona/liquidator-bot

- **Assessment:** C (provisional; independent review pending)
- **Purpose:** Aave V3 borrower scanner plus Balancer Vault flash-loan funded Aave liquidation and Uniswap V3 collateral-to-debt swap.
- **Repository identity:** GitHub repository ID `1223736441`; default branch `main`; not a fork; no license field reported by GitHub metadata.
- **Pinned source:** commit `6d964cb5f34276012f5a59281d861cd9aacb0b83`; tree `7a24b296c6c0947d95c2a6f54921a33fa4b5575f`; author date 2026-04-29.
- **Inspected blob pins:**
  - `contracts/Liquidator.sol`: `64d5ff727b7b5550a426b4057f9393bb5c302a79`
  - `src/scanner.js`: `479651cbd74e23ab3c96995b6725ac2398ce7d6c`
  - `src/liquidator.js`: `39e01ece314e9584ac2c3d1b82d661f612fa7e8f`
  - `src/config.js`: `33230675b2fafc45a3648ad6634481968d96ab45`
  - `src/bot.js`: `8e69efc6705a66487f7910ba7c9994be8181e500`
  - `README.md`: `a43059f13a6e37bcfb20746c35fdb4a1b22ab36d`
  - `package.json`: `29722dee32182163aedfb748ea83f088d7603a28`

## What the code actually does

The Solidity contract asks Balancer Vault for a flash loan of the debt asset, calls Aave `liquidationCall`, swaps seized collateral through Uniswap V3, repays Balancer and transfers residual debt-token balance to owner. The off-chain scanner discovers borrowers through Aave Borrow events, checks account health factor, chooses one collateral/debt pair, estimates swap output and submits a transaction. The README's high-level architecture broadly matches the code.

## Positive evidence

- The callback requires `msg.sender == balancerVault`.
- The external liquidation entry point is owner-restricted.
- A callback reentrancy lock is present.
- The swap accepts a caller-supplied minimum output.
- The contract handles the same-token collateral/debt case by skipping the swap.
- Off-chain execution first estimates gas and checks that the transaction can be estimated.

## Findings and limitations

1. **Net profitability is not enforced (high confidence, high economic impact).** `tryLiquidate` calculates gross `expectedAmountOut - debtToCover`; it obtains `gasEstimate` and `gasCost` but only prints gas cost. It does not convert gas cost into debt-token/USD units, subtract it from profit, or enforce the imported `MIN_PROFIT_BASE`. A positive gross spread can therefore be net-negative after gas.
2. **Candidate pair selection is heuristic (high confidence).** `analyzePosition` selects the largest collateral balance and largest debt balance independently, rather than evaluating all valid collateral/debt pairs and quoting each pair. It can miss profitable pairs or select a pair with poor/no liquidity. This is a recall/quality limitation, not proof that every chosen pair is invalid.
3. **Historical borrower coverage is intentionally narrow (high confidence).** The Base and Arbitrum configs set initial event lookback to only 2,000 and 5,000 blocks. Borrowers whose Borrow event predates this window are not seeded at startup. The live listener only catches future Borrow events, so the bot can omit existing positions.
4. **RPC scan failures can silently omit ranges (high confidence).** At the minimum 10-block chunk, a failed event query is logged and skipped; the scanner continues and reports an initial scan complete. The run does not persist a durable coverage-gap ledger for skipped block intervals.
5. **Token transfer return values are unchecked in the Solidity contract (high confidence).** `IERC20.approve` and `transfer` return booleans but the contract ignores them. Non-standard/false-returning ERC-20s can break assumptions. SafeERC20-style handling is absent.
6. **Profit calculation is balance-based, not isolated to this loan (high confidence).** After repaying the loan, all remaining debt-token balance is treated as profit and transferred to owner. Pre-existing debt tokens or accidental residual balances are included in reported profit.
7. **No runtime proof.** Repository metadata and source were inspected only. No candidate code, build, tests, deployment, wallet or transaction was executed by this research project.

## Tests, dependencies, maintenance

Package scripts expose Hardhat compile/test, but this review did not execute them. Dependencies include ethers 6.11.1, Hardhat 2.22.2, dotenv and Hardhat toolbox. Repository was created 2026-04-28 and last pushed 2026-04-29 in the pinned metadata. No GitHub license metadata was reported; package metadata alone does not establish an open-source license.

## Verdict

A recognizable Aave/Balancer/Uniswap liquidation prototype with meaningful contract-side controls, but not evidence of a production-ready or net-profitable system. The largest economic defect is that gas is measured but not deducted from the profit gate. Treat as research/reference code, not deployable software.

## Evidence links

- [Pinned contract](https://github.com/0xTona/liquidator-bot/blob/6d964cb5f34276012f5a59281d861cd9aacb0b83/contracts/Liquidator.sol)
- [Pinned scanner](https://github.com/0xTona/liquidator-bot/blob/6d964cb5f34276012f5a59281d861cd9aacb0b83/src/scanner.js)
- [Pinned liquidator](https://github.com/0xTona/liquidator-bot/blob/6d964cb5f34276012f5a59281d861cd9aacb0b83/src/liquidator.js)
- [Pinned config](https://github.com/0xTona/liquidator-bot/blob/6d964cb5f34276012f5a59281d861cd9aacb0b83/src/config.js)

**Review status:** source inspection completed; independent reviewer not yet run; no execution.
