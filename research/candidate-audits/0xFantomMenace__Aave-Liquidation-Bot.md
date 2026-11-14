# Candidate audit: 0xFantomMenace/Aave-Liquidation-Bot

- **Assessment:** C (provisional; independent review pending)
- **Purpose:** Multi-project liquidation-bot repository. Reviewed subprojects include HyperLend (Aave V3-like) and Granary on Optimism (Aave V2 fork); do not treat the repository as one single implementation.
- **Repository identity:** GitHub repository ID `1113846676`; default branch `main`; not a fork; GitHub metadata reports no license.
- **Pinned source:** commit `83a0cdece4ba3721c527345624e05648ebd079f5`; tree `fbe231154632b2c0bf2bb5fa9bf6f4a6306deaed`; author date 2025-12-10.
- **Inspected blob pins:**
  - `Hyperlend/Deployer/contracts/Liquidator.sol`: `bd9e64460c697ee041eb51bde41f08606ddbb6fd`
  - `Hyperlend/Deployer/test/test.ts`: `f83c726af90ed4ea87a538c9f723beea916707d6`
  - `Hyperlend/Deployer/package.json`: `21b2722e6eb06b682a630576af9d805b02000d4a`
  - `Hyperlend/Liquidation Bot/src/app.ts`: `ffbd5448fcdb0b47b1d48215d10e7b0f2f684ed4`
  - `Granary Optimism/Deployer/contracts/Liquidator.sol`: `878767d0b0d049f486c2bbbcf679ba2e32ada414`
  - `Granary Optimism/Deployer/contracts/FlashLoanReceiverBase.sol`: `94d52a1149d467b5528c19853eb05136edb5b771`
  - `Granary Optimism/Liquidation Bot/src/app.ts`: `fd1e52b0216915d949f91564b2a15e2510996b11`

## What the code actually does

### HyperLend subproject

The Solidity liquidator requests a single-asset Aave V3-style flash loan, optionally updates Pyth price feeds inside the callback, calls `liquidationCall`, receives underlying collateral, swaps it through a Uniswap V3-style router, checks repayment sufficiency and returns success so the pool can pull principal plus premium. The callback checks both pool caller and `initiator == address(this)`. The TypeScript bot monitors borrower state, Pyth updates and estimated profitability, and calls the contract.

### Granary Optimism subproject

The Solidity contract inherits an Aave V2-style flash-loan receiver base, liquidates via Granary's lending pool, swaps collateral to debt token and converts residual profit to the gas token. Its `executeOperation` callback does not visibly authenticate `msg.sender` against `LENDING_POOL` or validate `initiator`; `jIUTh` is owner-gated. The swap uses low-level calls whose success result is not checked and sets `amountOutMinimum: 1`.

## Positive evidence

- HyperLend constructor rejects zero Pyth/pool/router addresses.
- HyperLend liquidation entry is owner-only and non-reentrant.
- HyperLend callback validates the pool caller and flash-loan initiator.
- HyperLend enforces minimum collateral, minimum swap output and sufficient debt balance for principal plus premium.
- HyperLend emits a structured liquidation event.
- Granary implementation clearly expresses the older Aave V2 flash-loan callback and liquidation/swap flow.

## Findings and limitations

1. **Granary callback authentication gap (high confidence, high impact).** The reviewed `Granary Optimism/Deployer/contracts/Liquidator.sol::executeOperation` has no visible `msg.sender == address(LENDING_POOL)` or initiator check, unlike the HyperLend callback. This is an externally callable flash-loan callback surface and must be restricted to the configured pool and expected initiator before any token approvals/liquidation/swap logic.
2. **Granary swap call results are ignored (high confidence).** The contract uses low-level `address(SWAP_ROUTER).call(...)` and discards the returned success flag. It can continue into later accounting after a failed router call; downstream checks may revert, but the call itself is not safely handled.
3. **Granary swap minimum output is effectively non-protective (high confidence).** `amountOutMinimum: 1` does not encode a meaningful price/slippage bound. A transaction may accept severe execution loss if the remaining debt/profit arithmetic still passes.
4. **HyperLend test coverage is not established by the inspected test.** The Deployer test imports a mock Uniswap V2 router and exercises the older lending-pool test helper flow; it does not prove the HyperLend/Pyth/Uniswap V3 callback and price-update path end-to-end. The package exposes Hardhat tests, but test execution was not performed.
5. **HyperLend Pyth update economics need explicit accounting.** The external entry point checks `msg.value >= getUpdateFee`, then the callback forwards exactly the update fee to Pyth. Excess ETH remains in the contract until owner withdrawal; not a direct exploit, but should be documented/refunded.
6. **HyperLend strategy depends on accurate off-chain opportunity calculations and live protocol configuration.** Source code alone does not prove that configured oracle feed IDs, asset addresses, pool/router deployments, liquidation parameters or Pyth updates are correct for a live chain.
7. **No runtime proof.** No candidate code or contracts were compiled, tested, deployed or executed by this research project.

## Tests, dependencies, maintenance

HyperLend Deployer package is marked `UNLICENSED`, uses Hardhat and OpenZeppelin Contracts 4.9.6. A test file exists, but the inspected test is not evidence for the HyperLend-specific path. Repository creation and latest push in GitHub metadata are both 2025-12-10. No GitHub license metadata was reported.

## Verdict

A multi-implementation research repository with a comparatively better-guarded HyperLend flash-loan callback and a materially weaker Granary callback. The repository must be audited per subproject, not assigned a single blanket implementation quality. Provisional C reflects mixed code paths and incomplete test evidence.

## Evidence links

- [Pinned HyperLend contract](https://github.com/0xFantomMenace/Aave-Liquidation-Bot/blob/83a0cdece4ba3721c527345624e05648ebd079f5/Hyperlend/Deployer/contracts/Liquidator.sol)
- [Pinned HyperLend test](https://github.com/0xFantomMenace/Aave-Liquidation-Bot/blob/83a0cdece4ba3721c527345624e05648ebd079f5/Hyperlend/Deployer/test/test.ts)
- [Pinned HyperLend bot](https://github.com/0xFantomMenace/Aave-Liquidation-Bot/blob/83a0cdece4ba3721c527345624e05648ebd079f5/Hyperlend/Liquidation%20Bot/src/app.ts)
- [Pinned Granary contract](https://github.com/0xFantomMenace/Aave-Liquidation-Bot/blob/83a0cdece4ba3721c527345624e05648ebd079f5/Granary%20Optimism/Deployer/contracts/Liquidator.sol)
- [Pinned Granary receiver base](https://github.com/0xFantomMenace/Aave-Liquidation-Bot/blob/83a0cdece4ba3721c527345624e05648ebd079f5/Granary%20Optimism/Deployer/contracts/FlashLoanReceiverBase.sol)

**Review status:** source inspection completed; independent reviewer not yet run; no execution.
