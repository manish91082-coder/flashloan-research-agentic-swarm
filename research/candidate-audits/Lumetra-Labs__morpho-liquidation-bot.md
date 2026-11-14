# Candidate Audit: Lumetra-Labs Morpho Liquidation Bot

- Repository: https://github.com/Lumetra-Labs/morpho-liquidation-bot
- Default branch: `main`
- Inspected commit: `471c7adac62aaf58e5046a395ba96338dc82278a`
- Tree SHA: `20487e3b1e7621525f0521b4832c4a3dc75b4c3c`
- Review type: read-only static source review; no repository code, tests, deployment script, RPC call, wallet, signer or transaction was executed
- Snapshot date: 2026-11-14
- Grade: **C (educational Morpho liquidation reference; economics and operational correctness unproven)**

## 1. Purpose and scope classification

The repository describes itself as an educational liquidation bot for unhealthy DeFi borrowers. The inspected primary execution path is a **Morpho Blue native liquidation callback plus 1inch swap**, not a flash-loan-funded liquidation implementation.

Evidence:
- `contracts/Liquidator.sol` imports `IMorphoLiquidateCallback` and implements `onMorphoLiquidate`; the public entrypoint calls `IMorpho(MORPHO_BLUE).liquidate(...)` (blob `9d69d1fdd4037668bf462ff2d8b6e40501e9fde3`, lines 4-6, 10, 33-40, 52-63).
- The TypeScript executor connects to the deployed Liquidator and submits `liquidate(...)` transactions (blob `3f304afc04f86c91cdde66d2bea32b63727afd8a`, lines 110-149).
- No flash-loan lender call or flash-loan receiver callback appears in this inspected primary contract/execution path. This classification is limited to the reviewed files, not a claim that every repository file was exhaustively searched.

**Taxonomy label:** `liquidation_bot_without_flash_loan` / `educational_liquidation_reference`.

## 2. Actual implementation path

1. `src/main.ts` obtains a provider, reads market IDs from `WHITELISTED_MARKET_IDS`, checks the latest block, and calls `liquidateUsers`.
2. `borrowerFetcher.ts` scans Morpho Blue `Borrow` logs in 1,000-block ranges and persists borrower addresses to `src/data/borrowersPerMarket.json`.
3. `fetch.ts` retrieves market state, accrues interest using a configured IRM, reads the oracle price, queries borrower positions, and derives a health factor.
4. `liquidate.ts` estimates collateral to seize, requests a 1inch swap transaction, constructs a liquidation candidate, and signs/submits a call to the Liquidator contract using `PRIVATE_KEY`.
5. Morpho Blue invokes `onMorphoLiquidate`; the contract approves the router and Morpho, calls the immutable 1inch Aggregation Router, and requires the router-reported output to cover `repaidAssets`.
6. After a successful Morpho liquidation, the public `liquidate` entrypoint transfers remaining balances of the decoded source and destination tokens to the caller.

Relevant pins:
- `src/main.ts`: blob `2d09451924ac832797bce291a8d16e3701a0383e`
- `src/fetcher/fetch.ts`: blob `1acecba8565c1a0b2c3e7aa12c143aa544aa4c09`
- `src/liquidate/borrowerFetcher.ts`: blob `79cfb84d7e6a238c507d207a98324afb58a7c98f`
- `src/liquidate/liquidate.ts`: blob `3f304afc04f86c91cdde66d2bea32b63727afd8a`
- `src/oneInch/oneInch.ts`: blob `d9dae32869691450e6e35a8ce1576d2c7c9565a3`
- `contracts/Liquidator.sol`: blob `9d69d1fdd4037668bf462ff2d8b6e40501e9fde3`

## 3. Findings

### MORPHO-INDEX-001: one global borrower scan cursor is shared across all markets

**Status:** Confirmed source-level candidate-discovery completeness defect.  
**Severity:** High for coverage correctness when the market whitelist changes.

The persisted shape stores a top-level `lastBlock` alongside a map of per-market borrower lists. Every market in the current whitelist starts scanning from `previousData.lastBlock + 1`, regardless of whether that market was present in the earlier snapshot (blob `79cfb84d7e6a238c507d207a98324afb58a7c98f`, lines 13-21, 54-60, 74-85). After one run advances the global cursor, adding a new market later scans only blocks after that cursor and omits historical borrowers from that market. The checked-in data snapshot contains one market and `lastBlock: 19888760` (blob `c8a514c7e413409a7218b16a8c96f355d6879139`), so the gap is directly relevant to expansion beyond that seeded market.

**Required remediation:** Persist `lastScannedBlock` per market. For a market without prior state, start from the Morpho deployment block or a verified market-creation block. Record partial scans and only advance each market cursor after successful completion.

### MORPHO-INDEX-002: borrower-scan failure is logged, then execution continues with the previous data file

**Status:** Confirmed source-level stale-data path.  
**Severity:** Medium to high for operational completeness.

`liquidateUsers` calls `compileBorrowersPerMarket(...).catch(console.error)` and then immediately reads borrower data through `fetchAllLiquidatableUsersPositions` (blob `3f304afc04f86c91cdde66d2bea32b63727afd8a`, lines 161-171). If the scan fails, the error is swallowed and an existing `borrowersPerMarket.json` can still be used. This can silently omit newly discovered positions or use an outdated candidate universe.

**Required remediation:** Fail closed on borrower-index update failure, or explicitly mark the run as stale/incomplete and prevent liquidation submission until the index is refreshed or approved.

### MORPHO-ECON-003: reported gains are theoretical liquidation incentive, not quoted or realized net profit

**Status:** Confirmed source-level economic measurement gap.  
**Severity:** High for any profitability claim.

The TypeScript flow obtains a 1inch response containing `dstAmount`, but the gain estimate is calculated as `incentivizedRepaidAssets - repaidAssets` and converted using a token USD price (blob `3f304afc04f86c91cdde66d2bea32b63727afd8a`, lines 200-210, 215-242). The calculation does not use the actual 1inch `dstAmount` as the output amount in the displayed gain formula, and it does not deduct gas, priority fees, swap/aggregator charges, price movement, or other transaction costs. The checked-in test explicitly names the scenario “gas costs not considered” (blob `c2ba25cc5112656b9dff17bf77bdec05fb276070`, line 43).

The on-chain callback checks only that the router-reported output covers `repaidAssets` (contract blob `9d69d1fdd4037668bf462ff2d8b6e40501e9fde3`, lines 52-63). It does not enforce a strictly positive configured net-profit floor.

**Required remediation:** Recompute expected repayment from exact Morpho liquidation semantics, use the returned swap quote/output, subtract all execution costs, bind estimates to a block, simulate the exact call, and require a positive configurable net-profit margin. Keep estimated, simulated, and realized P&L as separate fields.

### MORPHO-EXEC-004: transaction result is ignored by the candidate loop

**Status:** Confirmed source-level reporting defect.  
**Severity:** Medium.

`_atomicLiquidation` waits for the transaction receipt and catches failures by returning `null` (blob `3f304afc04f86c91cdde66d2bea32b63727afd8a`, lines 110-149). The caller loop awaits `atomicLiquidation` but discards its return value, then logs liquidation details and eventually returns the entire `results` array (same blob, lines 250-270). Thus the returned array represents prepared candidates, not successfully mined liquidations. The test asserts that the returned array has length one; it does not assert a successful receipt or transaction status (test blob `c2ba25cc5112656b9dff17bf77bdec05fb276070`, lines 72-76).

**Required remediation:** Store each transaction hash, receipt status, block number, gas used and revert/error reason. Separate `candidate`, `submitted`, `confirmed`, and `failed` states. Never label a candidate “liquidated” merely because a quote and candidate record exist.

### MORPHO-CUSTODY-005: public entrypoint transfers the full selected-token balances to its caller

**Status:** Confirmed source-level asset-custody behavior; exploitability/value not reproduced.  
**Severity:** Medium; requires a balance-delta design review.

The `liquidate` function is externally callable and, after a successful call, transfers the entire current balances of the decoded `srcToken` and `dstToken` to `msg.sender` (contract blob `9d69d1fdd4037668bf462ff2d8b6e40501e9fde3`, lines 33-49). It does not snapshot balances before the liquidation and transfer only the delta produced by that call. Any pre-existing dust of those two token types held by the contract is therefore included in the transfer to the current caller if the liquidation succeeds.

The normal path intends to leave no residual balances, but this does not guarantee that no tokens can be donated, left behind through another path, or stranded from a prior execution.

**Required remediation:** Snapshot source and destination balances before the external Morpho call and transfer only the attributable balance delta. Add tests with preloaded token balances and a different caller.

## 4. Positive controls and design notes

- The callback has an explicit `onlyMorpho` check against the immutable `MORPHO_BLUE` address (contract blob, lines 71-74). This is a positive callback-caller control.
- The aggregation router and Morpho contract addresses are immutable constructor parameters (contract blob, lines 25-30).
- The Morpho callback is atomic with the liquidation transaction. If Morpho cannot pull the repayment token, the transaction should revert; this is not equivalent to a net-profit guarantee.
- The router calldata is supplied by the transaction caller and decoded for token/amount fields; the reviewed contract does not visibly bind decoded source and destination token addresses to the market's collateral and loan token in its own pre-call checks. Add explicit binding and receiver checks as a hardening requirement. This review did not prove an exploitable route.
- The callback has no visible reentrancy guard and no explicit post-operation allowance revocation. These remain review items; this static pass did not establish an exploitable reentrancy or allowance attack.
- `fetchAllUserData` maps every borrower into a Promise and awaits the entire set at once (fetch blob, lines 181-230), with no explicit concurrency cap. Large borrower lists may cause RPC provider throttling or memory pressure.
- The health-factor filter converts a large integer to JavaScript `Number` with `parseFloat` before comparing it to WAD (fetch blob, around lines 270-290). Integer comparison against `WAD` should be preferred to preserve exact boundary behavior.

## 5. Tests, CI, dependencies and license

- The repository contains a Hardhat fork-oriented test file and mocks a 1inch API response (test blob `c2ba25cc5112656b9dff17bf77bdec05fb276070`; mock blob `50d9587a5ac94197ac14794aa4c21b60978a22fb`).
- The test config pins a Hardhat mainnet fork block at 19,888,759 (config blob `c9cb539d50176e674d83d5e0cd92eac2b4ee3099`); the test expects block 19,888,760 after setup/deployment (test blob, lines 31-40).
- GitHub Actions API returned zero workflow runs at inspection. The only workflow file in `.github/workflows` is a Telegram PR notification workflow, not a test/CI workflow.
- No root `LICENSE` file was present in the inspected repository tree. `package.json` declares MIT, README says MIT but references an “incoming” LICENSE file, and the Solidity source uses `SPDX-License-Identifier: UNLICENSED` (package blob `4a8f6950f3e9818443d9f33e0d28d8d969cc0fd3`; README blob `21248134be5ccdca776b6d7726288ebce8186383`; contract blob, line 1). Treat licensing as unresolved pending owner clarification and file-level resolution.
- `package.json` includes an `fs@^0.0.1-security` dependency entry alongside Node's built-in `fs`; dependency provenance and necessity should be reviewed. No dependency installation or candidate code execution was performed.
- The README and `.env.example` show a well-known default Hardhat development private key example (README blob, lines 41-57; env-example blob `55f48c70d11f08108016c7ef1e02bcc313d79b57`). It is a local development key, not a secret discovered in this audit, but it must never be reused on a real network.
- The borrower snapshot currently contains one market, 107 borrower addresses and `lastBlock=19888760` (data blob `c8a514c7e413409a7218b16a8c96f355d6879139`). This matches the documented educational fork fixture, not broad production-market coverage.

## 6. Evidence limitations

- No candidate code, Hardhat test, fork, deployment, RPC transaction, wallet, private key, or 1inch API call was executed.
- No live liquidation, mainnet deployment state, external audit, reproducible CI run or realized profit was verified.
- Submodule source revisions and transitive dependency provenance have not yet been independently audited.
- Static source findings are not a proof of exploitability. The token-balance transfer and missing market-token binding need a targeted, isolated test before being elevated to confirmed exploit claims.

## Verdict

**Grade: C.** Retain as a useful educational Morpho Blue liquidation/callback reference, not as a verified flash-loan liquidator or profitable production bot. Its strongest reusable concept is the Morpho native liquidation callback plus atomic collateral-to-debt-token swap. Do not promote its economic claims: the gain estimate is theoretical, explicit gas costs are excluded, and the on-chain invariant checks repayment coverage rather than positive net profit. The global borrower cursor and ignored transaction receipt are concrete correctness/reporting defects. Require per-market scan cursors, fail-closed indexing, delta-based balance accounting, exact transaction outcome tracking, and cost-complete simulation before considering it a reliable reference.
