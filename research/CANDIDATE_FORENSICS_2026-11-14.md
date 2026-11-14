# Candidate Forensics: 2026-11-14

## Scope and evidence method

This pass revalidated four newly surfaced candidates against their exact current default-branch commits on 2026-11-14. Repository metadata, recursive tree, selected source blobs, selected test files and available GitHub Actions history were inspected. Candidate source was read as untrusted data and was **not executed**. No local build, test, deployment, transaction signing, or on-chain simulation of candidate code was performed.

Grades below describe evidence quality and suitability as a research/code reference. They are not security-audit certifications, profit estimates, or production-readiness approvals.

## Executive triage

| Candidate | Exact inspected HEAD | Classification | Current assessment |
|---|---|---|---|
| [Aquafr198/liquidator](https://github.com/Aquafr198/liquidator) | `c0970909d4fa0cbbc36a2aed3dbb7857b809e29c` | Multi-protocol liquidation with Morpho flash-loan funding; Aave L2 native Aave flashLoanSimple variant | **B-/C+ research candidate**. Broad architecture and meaningful unit-test code, but no repository Actions history, inert historical-fork fixture, no pre-loan balance baseline, and non-WETH on-chain min-profit floor absent. |
| [clubytech/cluby-liquidator](https://github.com/clubytech/cluby-liquidator) | `46a7d56e061db6e46389f5b731783a4183d2cb53` | Morpho Blue flash-loan liquidation, Uniswap V3 swap | **C+ focused reference**. Good oracle-relative output floor and one successful Foundry CI run, but no pre-loan balance baseline and zero-profit liquidation is allowed. Four unit tests only in the inspected test file. |
| [litmajor/argus-evm](https://github.com/litmajor/argus-evm) | `fd1a1161a62b10a431079b60812d64ba10b820bd` | Native Morpho liquidation callback, not a flash-loan bot | **B+ callback-accounting reference, not a flash-loan candidate**. Strong session, callback and balance-delta controls. README explicitly says it does not use a flash loan and that runtime wiring is incomplete/unsafe for the documented dry-run as wired. |
| [MELD-labs/meld-flashloan-liquidation-bot-public](https://github.com/MELD-labs/meld-flashloan-liquidation-bot-public) | `74653447a0ff9014f2e022d6778b442182f9841a` | Historical Aave V3 flash-loan liquidation prototype | **C / blocked historical reference**. Callback does not authenticate the LendingPool caller or initiator; profit accounting uses absolute balance; no tests or GitHub Actions evidence in the inspected tree. |

---

## 1. Aquafr198/liquidator

### Snapshot

- URL: https://github.com/Aquafr198/liquidator
- Default branch: `master`
- HEAD: `c0970909d4fa0cbbc36a2aed3dbb7857b809e29c`
- Tree SHA: `23574a8038440af780799565ba675419b44d13f4`
- Commit date: 2026-06-13T18:34:11Z
- Repository metadata: MIT, Python primary language, 0 stars, 0 forks at inspection.
- Recursive tree was not truncated.
- GitHub Actions API returned `total_count = 0`; the inspected tree had no `.github/workflows` directory.
- The README advertises 323 tests (258 pytest + 65 Foundry) and production operation across three chains. These are README claims, not independently verified runtime or deployment evidence.

### Actual funding and protocol flow

The codebase contains Morpho flash-loan callback contracts for:
- Morpho Blue liquidation
- Euler v2 liquidation
- Silo v2 liquidation
- Aave V3 mainnet liquidation, funded through a Morpho flash loan

A separate `AaveLiquidatorL2.sol` uses Aave V3 `flashLoanSimple` on L2. Its callback authenticates both the Pool caller and `initiator == address(this)`, validates the borrowed asset against the configured debt asset, and includes the actual callback-supplied premium in `repayTotal = amount + premium`.

This is more than a README-only claim: the pinned tree contains separate protocol contracts, deployment/operations code, Solidity unit-test files and Python test directories.

### Confirmed accounting gap: pre-existing balance is not excluded

In `contracts/src/Liquidator.sol` at the inspected blob SHA `99481fabca717e7f0a7e3b4a42887d6ce2c0c2b8`:
- Lines 142-145 initiate Morpho `flashLoan`.
- Lines 148-150 authenticate the callback caller as Morpho.
- Line 172 reads the executor's current loan-token balance after liquidation and swaps.
- Line 188 computes surplus as `loanBal - flashAmount`.
- Lines 196-202 enforce `minProfitWei` in the WETH-loan branch.
- The non-WETH branch (around lines 218-263) performs the WETH settlement/builder payment and transfers remaining loan-token balance above `flashAmount`, but does not apply the loan-token `minProfitWei` field.

There is no `loanBalBefore` snapshot before the flash loan in this contract. The same accounting shape appears in:
- `AaveLiquidator.sol`, blob `e97c7527daf3732f69847c8599570fa4e3c2b2aa`, balance/surplus/floor lines 207, 212 and 225.
- `EulerLiquidator.sol`, blob `39e3802bb588dd20715618bacea29e0484844110`, lines 189, 194 and 207.
- `SiloLiquidator.sol`, blob `24036a954a55e0c64fe398b2bf7b3e45fd90578d`, lines 204, 209 and 222.
- `AaveLiquidatorL2.sol`, blob `f971e03a18cb2dbb288640f16ec838ab3d897ffe`, lines 193-215. This contract correctly includes Aave's premium in `repayTotal`, but still reads the absolute balance rather than subtracting a pre-operation baseline.

**Implication:** a donated or residual debt-token balance can be included in the measured surplus. In the WETH path it can contribute toward the on-chain minimum-profit test; in non-WETH paths it can be transferred to the owner as apparent leftover profit. This is a correctness/accounting finding, not a demonstrated third-party theft exploit.

**Required correction:** take `B0` before the flash loan and enforce the lender-specific repayment plus profit invariant. For Morpho's fee-free path: before lender pull, `Bcb >= B0 + P + M`. For Aave: `Bcb >= B0 + P + premium + M`. The callback-supplied premium must be used, never a hardcoded value. Use equivalent checks for every protocol adapter.

### Non-WETH profit control is off-chain, not an on-chain loan-token floor

The Solidity comments explicitly say the `minProfitWei` field is enforced on-chain only for WETH-loan markets (for example, `Liquidator.sol` lines 68-73). The non-WETH path converts enough loan-token balance to WETH for builder payment and a gas reserve, then returns the remaining loan-token surplus. The Python atomic bundle flow contains an `eth_callBundle` simulation and a `coinbaseDiff` threshold gate in the Euler candidate path (blob `4392c5378edda7b1e465228672b1504885238db5`, approximately lines 1120-1200 and 1507-1522).

This is a deliberate architecture split, not proof that the bot is exploitable. It means the non-WETH minimum-profit safety property depends on the off-chain planner/simulation/relay path. The contract itself does not enforce the same minimum in loan-token units. Keep this distinction visible in any risk analysis and test the off-chain control for every adapter.

### Allowance hygiene is acknowledged but open

The README (blob `fb376f258078361aee989e16ee5356df34265b6c`, around line 268) explicitly lists persistent `_safeApprove(token, router, max)` allowances as an open item and recommends resetting them after swaps. Source inspection confirms maximum approvals to trusted protocol/router addresses in several adapters. This is an acknowledged hardening debt. The inspected code also restricts routers through immutable allowlists, so this should not be misreported as an unrestricted arbitrary-spender approval.

### Test and production evidence limitation

- The repository tree contains six Foundry `.t.sol` files with 65 named `test*` functions in total, consistent with the README's Foundry count.
- However, `contracts/test/Liquidator.fork.t.sol` (blob `2551522b68497b348b07332cc6beae3991881565`) is not currently a runnable mainnet-fork proof. Its fixture constants are commented placeholders; even when an RPC is configured, the test logs that Fixture 1 is not populated and returns before `vm.createSelectFork` or assertions.
- GitHub Actions API returned zero workflow runs at the inspected time and no workflow file was present in the tree.
- The README's production-service, cross-chain deployment and 323-passing-test statements therefore remain unverified claims for this audit. Unit-test source exists, but this pass did not execute candidate code.

### Assessment

Retain as the highest-priority multi-protocol architecture candidate for deeper research, not as an approved production implementation. Highest priority fixes: pre-operation balance baseline in all adapters, explicit non-WETH on-chain minimum-profit policy (or a documented and independently tested off-chain trust boundary), and allowance revocation. Require reproducible Foundry and fork evidence at the same commit before increasing confidence.

---

## 2. Clubytech/cluby-liquidator

### Snapshot

- URL: https://github.com/clubytech/cluby-liquidator
- HEAD: `46a7d56e061db6e46389f5b731783a4183d2cb53`
- Tree SHA: `c8c975a320403b92e79e487445387450bde45847`
- Contract: `src/periphery/FlashLiquidator.sol`, blob `e268c10d4f6e3c882f71c1e3b92caf293ad83937`
- Unit test: `test/unit/FlashLiquidator.t.sol`, blob `32fb71cff1d3295f30b3e75584ea2f5516f6446e`
- GitHub Actions run `34110570806` on this exact HEAD completed successfully. The job ran Foundry install, dependency install, build and test.
- The inspected test file contains four tests: capital-free happy path, below-oracle-floor revert, keeper authorization, and callback caller authorization.

### Strengths

- Uses Morpho Blue `flashLoan` and authenticates the callback caller as Morpho (source lines 107-125).
- Uses a Uniswap V3 router with an oracle-relative output floor (lines 127-149).
- Distinguishes the Morpho amount lent (`assets`) from the amount Morpho actually takes in liquidation (`repaid`); rejects `received < repaid` (lines 151-155).
- Has a concise unit suite and one successful CI workflow run on the pinned commit.

### Accounting gap and profitability limit

At line 160 the contract computes `profit = loanToken.balanceOf(address(this)) - assets`. It does not snapshot the loan-token balance before the flash loan, so pre-existing token dust is included in the reported `profit`. The pre-loan baseline is zero in the happy-path test (test lines 59-80); no test injects dust before execution.

The contract rejects a loss when `received < repaid`, but accepts equality (line 155). There is no explicit strictly-positive minimum-net-profit parameter or gas-cost gate in this contract. The oracle floor is a price-protection floor, not a proof that the liquidation is net-profitable after gas/relay costs.

### Assessment

Useful compact reference for Morpho callback flow and oracle-aware swap output protection. Not a sufficient reference for the project's profitability invariant without a pre-loan balance delta, positive net-profit floor and tests for dust/breakeven cases. The only observed CI run is the initial September 2026 run; no sustained CI history or mainnet realized-profit proof was found.

---

## 3. Litmajor/argus-evm

### Snapshot

- URL: https://github.com/litmajor/argus-evm
- HEAD: `fd1a1161a62b10a431079b60812d64ba10b820bd`
- Tree SHA: `8763e087efa0960b2a08a995d8f9299d9822a918`
- `contracts/src/VaultLiquidator.sol`, blob `64f83719b00155771f9fc52b43baedc496eaf7ae`
- README blob `27b124cd5ef770a610b69d38ef1cbf2dbce9a542`
- Repository created 2026-11-12 and last pushed 2026-11-13; GitHub Actions API returned zero runs at inspection.

### Category correction

This is **not a flash-loan implementation**. The contract header (VaultLiquidator.sol lines 4-18) explicitly describes Morpho Blue's native liquidation callback ordering: Morpho transfers seized collateral, then calls `onMorphoLiquidate`, and finally pulls repayment. README lines 17-18 separately says the contract does not use a flash loan.

### Valuable callback/accounting design

- The callback payload snapshots `loanBalBefore` and `collBalBefore` and carries a nonce (lines 99-110).
- `executeLiquidation` requires a nonzero minimum profit, validates the exclusive seized-assets/repaid-shares inputs, snapshots both token balances, and creates a session hash (lines 176-214).
- `onMorphoLiquidate` authenticates Morpho, requires an active session and exact payload hash, consumes the session once, then approves repayment (lines 221-238).
- `_swapAndGate` computes `base = loanBalBefore + owed`, swaps only collateral received during the current operation, calculates balance-delta profit, and enforces the minimum profit (lines 245-265).

This is a strong design reference for session-bound callbacks, pre-existing-balance exclusion and strict profit accounting. It is relevant to our flash-loan executor design, but it is not evidence of flash-loan integration.

### Operational maturity caveat

The README itself says the runtime currently passes no protocol addresses to Alloy WS ingest, runtime domain state is not configured with markets or positions, and the executor is unsafe for the documented dry-run as wired (README lines 13-18). The repository provides a local Anvil-fork smoke-test walkthrough, but current end-to-end readiness is not established by the README or Actions history.

### Assessment

Retain as a high-value architecture reference for callback state, replay prevention and balance-delta economics. Do not list it as a flash-loan bot or operational competitor.

---

## 4. MELD Labs legacy bot

### Snapshot

- URL: https://github.com/MELD-labs/meld-flashloan-liquidation-bot-public
- HEAD: `74653447a0ff9014f2e022d6778b442182f9841a`
- Tree SHA: `ddf5f95679d1a13fd7c45a775eaa4c56fca244a6`
- `contracts/LiquidateLoan.sol`, blob `ec704736adb1ce3547bbbe4809c14ab345b134fc`
- `contracts/FlashLoanReceiverBase.sol`, blob `bd38930b28085b88e0acd19541f225a57392ef95`
- Last pushed 2024-10-10; GitHub Actions API returned zero runs. No test directory or test files were present in the inspected tree.

### Source-level callback authentication defect

`executeOperation` is externally callable and its signature accepts the Aave callback's initiator argument, but the parameter is unnamed/ignored (LiquidateLoan.sol lines 130-136). The function does not check `msg.sender == lendingPoolAddr` or that the initiator is this receiver before continuing to approve the Pool and call `liquidationCall` (lines 143-156). This violates the expected flash-loan callback trust boundary. It is a confirmed source-level authorization defect; this research pass did not construct or execute an exploit.

### Additional accounting and amount-floor problems

- Profit is calculated from the absolute post-operation asset balance minus amount and premium (lines 163-166), without a pre-operation balance baseline.
- The requested swap minimum at lines 159-161 subtracts `currentBalance` of the collateral token from a threshold expressed in borrowed-asset terms. No conversion/scaling between those token units is performed in that expression; this is a dimensional accounting error unless a specific token-unit equivalence is assumed.
- The checked-in tree has no tests or GitHub Actions evidence.

### Assessment

Historical, blocked reference only. Do not use as a callback or accounting template.

---

## Portfolio conclusion

1. **Best multi-protocol source to continue studying:** Aquafr198/liquidator, conditional on fixing the accounting and test-evidence gaps.
2. **Best compact oracle-floor example:** clubytech/cluby-liquidator, after adding B0-based accounting and a true positive-profit floor.
3. **Best callback/session and balance-delta reference:** litmajor/argus-evm, explicitly not a flash-loan bot.
4. **Negative/legacy security reference:** MELD Labs, with unauthenticated flash-loan callback source.

No candidate has been shown in this pass to deliver repeatable realized net profit after flash fee, protocol/DEX fee, gas, slippage, relay/builder cost and other execution costs. No live transaction, wallet interaction, or candidate-code execution was performed.


## Supplemental source audits added after the initial four-candidate pass

### Lumetra-Labs/morpho-liquidation-bot — grade C

- Exact HEAD: `471c7adac62aaf58e5046a395ba96338dc82278a`; tree `20487e3b1e7621525f0521b4832c4a3dc75b4c3c`.
- Classification: Morpho Blue native liquidation callback plus 1inch swap; no flash-loan funding was identified in the reviewed primary path.
- Audit: [Lumetra-Labs__morpho-liquidation-bot.md](candidate-audits/Lumetra-Labs__morpho-liquidation-bot.md).
- Findings: shared global borrower cursor, stale-index fallback after scan failure, incentive-only theoretical P&L, ignored transaction outcome, and full selected-token balance transfer.
- Static source review only; no code, RPC, transaction or external audit.

### 0xnavarro/Aave-Liquiditor — grade D

- Exact HEAD: `9197ee3002d7d9b35e9c2da324128a38f7569038`; tree `14de2312e96c369bcc52c9bae96215051aea22b4`.
- Classification: Aave V3 flash-loan liquidation prototype.
- Audit: [0xnavarro__Aave-Liquiditor.md](candidate-audits/0xnavarro__Aave-Liquiditor.md).
- Findings: wrong PoolAddressesProvider/IPool pointer; missing callback caller/initiator authentication; missing collateral-to-debt swap; no B0 profit baseline; wrong collateral bitmap bit; principal-free profit formula; base-currency unit assumptions; capped tx-origin address discovery; env mismatch; monitor/executor disconnection; health-factor threshold mismatch.
- Official Aave interface references are included in the dossier. Static source review only; no candidate execution.
