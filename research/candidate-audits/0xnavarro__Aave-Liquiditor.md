# Candidate Audit: 0xnavarro Aave-Liquiditor

- Repository: https://github.com/0xnavarro/Aave-Liquiditor
- Default branch: `main`
- Inspected commit: `9197ee3002d7d9b35e9c2da324128a38f7569038`
- Tree SHA: `14de2312e96c369bcc52c9bae96215051aea22b4`
- Last commit observed: 2024-12-23
- Review type: read-only static source and configuration review; no repository code, tests, deployment, RPC calls, wallet, signer or transaction was executed
- Grade: **D (broken/incomplete prototype; not a verified executable liquidator)**

## 1. Purpose and scope classification

The README presents an Aave V3 liquidation bot for Arbitrum with two components: a risk-position monitor and a flash-loan liquidation executor. The source contains an Aave `FlashLoanSimpleReceiverBase` subclass and calls `flashLoanSimple` in its intended execution path, so this is a genuine **flash-loan liquidation candidate by declared implementation design**.

However, the inspected system has critical wiring and accounting defects. The monitor currently enumerates and prints positions; the executable monitor path does not call the liquidation contract. The Solidity executor passes a Pool Addresses Provider address to its locally declared `IPool pool` variable and then calls Pool methods on that variable. The candidate must therefore remain classified as an incomplete prototype until its execution path is corrected and independently verified.

## 2. Actual architecture observed

- `src/monitor/positions.ts`: queries recent Arbiscan transactions to seed an address set, fetches Aave account data, selects a collateral reserve, estimates gains, and sorts candidate positions.
- `src/index.ts`: constructs an RPC provider and wallet, then starts `PositionMonitor.startMonitoring(60000)`. The wallet is only used to print its address; the monitor does not receive the wallet or call the liquidation contract.
- `scripts/deploy.ts`: deploys `FlashLiquidator` with the Arbitrum Pool Addresses Provider address.
- `src/contracts/FlashLiquidator.sol`: intends to borrow the debt asset through Aave `flashLoanSimple`, call `liquidationCall`, and check that the debt-asset balance can cover principal plus premium.

Key source pins:
- `src/contracts/FlashLiquidator.sol`: blob `32c5e42920517fa1b93540a94e5d4dd95de94e1a`
- `src/monitor/positions.ts`: blob `677ae613db6f9ee8516da72bdb9759489978e009`
- `src/index.ts`: blob `3522cafd9bb708d5ae96184cb676bfadaefcbfe7`
- `scripts/deploy.ts`: blob `1a4c588e860bbbcbd8c7e781daf59e9ebdc0fd38`
- `readme.md`: blob `95b559797f21a5db443d69de5d59b64838d7a276`
- `.env.example`: blob `008af85a7f7a6cb4815fd414e18bb04c790aff75`
- `package-lock.json`: blob `0f84c18a39f0bc085246c312f9fd3d6b8f700d40`; resolved `@aave/core-v3` version `1.19.3`.

## 3. Findings

### AAVE-POOL-001: Pool Addresses Provider is cast directly to IPool and used for Pool calls

**Status:** Confirmed source-level contract-address wiring defect.  
**Severity:** Critical for the intended execution path.

The deployment script passes `AAVE_POOL_ADDRESSES_PROVIDER` to the constructor (deploy blob `1a4c588e860bbbcbd8c7e781daf59e9ebdc0fd38`, lines 6-10). The constructor correctly passes this value to the Aave base constructor as an `IPoolAddressesProvider`, but it also assigns the same provider address to a separate local `IPool public pool` variable (contract blob `32c5e42920517fa1b93540a94e5d4dd95de94e1a`, lines 55-60 and 71-74). The implementation then calls `pool.liquidationCall` (lines 91-101) and `pool.flashLoanSimple` (lines 131-138) through that local variable.

Aave's `FlashLoanSimpleReceiverBase` already exposes the correct immutable `POOL`, initialized as `IPool(provider.getPool())`. The separate lower-case `pool` field is not that base field. Aave documents the Pool Addresses Provider as a registry and says the Pool address should be obtained through `getPool()`.

**Required remediation:** Remove the duplicate local `pool` field and use the inherited `POOL` consistently, or explicitly set `pool = IPool(IPoolAddressesProvider(_addressProvider).getPool())`. Add a deployment-time assertion that the configured address supports the expected Pool interface.

Official reference:
- https://github.com/aave/aave-v3-core/blob/master/contracts/flashloan/base/FlashLoanSimpleReceiverBase.sol
- https://www.aave.com/docs/aave-v3/smart-contracts/pool-addresses-provider

### AAVE-CALLBACK-002: executeOperation does not authenticate the callback caller or initiator

**Status:** Confirmed missing source-level trust-boundary checks.  
**Severity:** High; exploitability is not established in the currently miswired deployment path.

The callback decodes arbitrary supplied `params`, approves the locally stored `pool`, and invokes `liquidationCall`, but it does not check `msg.sender == address(POOL)` or `initiator == address(this)` (contract blob `32c5e42920517fa1b93540a94e5d4dd95de94e1a`, lines 81-110). Aave flash-loan receivers should bind callback entry to the Pool and to the expected initiator. The present wrong Pool pointer already prevents the intended path from being considered operational; this missing check remains a mandatory fix even after the address wiring is corrected.

**Required remediation:** Require both the actual Aave Pool caller and the expected initiator, validate the borrowed asset/amount against the stored request, and clear request state after successful execution.

### AAVE-FLOW-003: collateral is received but no collateral-to-debt swap is implemented

**Status:** Confirmed missing step in the inspected contract.  
**Severity:** Critical for ordinary cross-asset liquidations.

The contract's callback approves the debt asset to the Pool, calls `liquidationCall`, and then checks whether the debt-asset balance is at least `amount + premium` (blob `32c5e42920517fa1b93540a94e5d4dd95de94e1a`, lines 91-108). The inspected contract has no DEX/router integration or collateral-to-debt swap function. For a normal liquidation where collateral asset differs from debt asset, Aave transfers seized collateral but the contract does not convert it into the borrowed debt asset needed for repayment. Unless the contract already holds sufficient debt tokens or the two assets coincide, the repayment check will fail.

**Required remediation:** Add a bounded swap route for the seized collateral, enforce an actual output minimum in debt-token units, and verify post-swap balance delta before repayment. Do not treat pre-funded balances as liquidation proceeds.

### AAVE-CALLBACK-004: repayment check can be satisfied by pre-existing debt-token balance and has no positive-profit floor

**Status:** Confirmed accounting weakness.  
**Severity:** High.

The callback checks only `balanceOf(address(this)) >= amount + premium` (blob `32c5e42920517fa1b93540a94e5d4dd95de94e1a`, lines 103-108). It does not snapshot the pre-loan balance or require post-repayment surplus above that baseline. Pre-existing debt-token dust or owner-supplied funds could therefore mask a strategy loss. There is no configurable `minProfit` condition in the callback. The owner-only `withdrawToken` function (lines 141-143) does not supply that missing invariant.

**Required remediation:** Snapshot `B0` before the flash loan and require debt-token balance before repayment to be at least `B0 + principal + actual premium + minProfit`. Measure net profit after repayment and execution costs.

### AAVE-MONITOR-005: collateral bitmap reads the borrowing bit, not the collateral bit

**Status:** Confirmed source-level monitor defect.  
**Severity:** High for candidate correctness.

`getUserCollateral` tests `(config >> (i * 2)) & 1` and labels it `isUsedAsCollateral` (monitor blob `677ae613db6f9ee8516da72bdb9759489978e009`, lines 120-131). Aave's two-bit-per-reserve user bitmap uses bit `2*i` for borrowing and bit `2*i+1` for collateral. The monitor is therefore checking the borrowing bit when it needs the collateral bit; it can return a borrowed reserve as collateral or fail to find the pledged collateral.

**Required remediation:** Check `(config >> (BigInt(i) * 2n + 1n)) & 1n` and iterate every collateral-enabled reserve, not merely the first. Add fixtures for borrowing-only, collateral-only, both, and neither states.

Official reference:
- https://aave.com/docs/aave-v3/smart-contracts/pool?language=en
- https://github.com/aave/aave-v3-core/blob/master/contracts/protocol/libraries/configuration/UserConfiguration.sol

### AAVE-MONITOR-006: profit formula does not subtract returned principal

**Status:** Confirmed arithmetic defect in the monitor estimate.  
**Severity:** High for opportunity ranking and minimum-profit filtering.

The reserve-config decoder converts the raw liquidation-bonus field to percentage points and then the monitor converts it to a multiplier (monitor blob `677ae613db6f9ee8516da72bdb9759489978e009`, lines 136-151 and 181-188). For a 105% liquidation bonus, the multiplier is 1.05. The current formula is:

`estimatedProfit = maxLiquidation * 1.05 - maxLiquidation * 0.001`

This subtracts only a 0.1% flash fee and fails to subtract the original debt principal. The theoretical incentive before costs should begin with approximately `maxLiquidation * (bonusMultiplier - 1)`, then deduct actual flash premium, swap, gas and other costs. The current expression therefore overstates the gross incentive by roughly the principal amount for the stated 105% example.

**Required remediation:** Derive gross collateral value from actual liquidation parameters, subtract the repaid principal, use the actual Aave flash-loan premium, and use executable quotes/simulation plus gas/priority-fee estimates before applying `MIN_PROFIT_USD`.

### AAVE-MONITOR-007: base-currency values are formatted as 18-decimal ETH and multiplied by a hard-coded ETH price

**Status:** Confirmed unit-assumption defect; exact Arbitrum oracle unit must be read at runtime.  
**Severity:** High for the displayed position values and estimated USD profit.

Aave's `getUserAccountData` returns collateral and debt totals in the market price oracle's base currency, not inherently in ETH. The monitor formats `totalCollateralBase` and `totalDebtBase` with 18 decimals, names them ETH, and multiplies its estimate by a fixed `ethPriceUSD = 2200` (monitor blob `677ae613db6f9ee8516da72bdb9759489978e009`, lines 164-192). Aave's oracle interface defines `BASE_CURRENCY_UNIT`; USD-base markets use 1e8, while ETH-base markets use 1e18. The implementation does not query either `BASE_CURRENCY` or `BASE_CURRENCY_UNIT`, so the displayed values and estimated USD profit are not robust to the configured market's actual base currency.

**Required remediation:** Read the Pool's Price Oracle base currency and unit, convert to a normalized decimal representation, and derive prices from live oracle/reserve data rather than a constant.

Official references:
- https://aave.com/docs/aave-v3/smart-contracts/pool?language=en
- https://www.aave.com/docs/aave-v3/smart-contracts/oracles
- https://github.com/aave/aave-v3-core/blob/master/contracts/interfaces/IPriceOracleGetter.sol

### AAVE-MONITOR-008: address discovery is only the latest 10,000 Pool transactions and uses tx.from as the user

**Status:** Confirmed discovery-coverage limitation.  
**Severity:** High for recall/completeness.

The monitor requests `txlist` for the Pool with `page: 1`, `offset: 10000`, `sort: desc`, then records only each transaction's `from` field (monitor blob `677ae613db6f9ee8516da72bdb9759489978e009`, lines 63-110). There is no pagination or borrower-event/user extraction. Transaction origin is not necessarily the Aave position owner, especially when a smart account, router, automation contract or relayer submits a call. The source also contains a GraphQL query module, but the inspected `PositionMonitor` path does not use it.

**Required remediation:** Build the borrower universe from Aave protocol events/indexer entities with pagination and stable cursors; identify the actual account owner/beneficiary for each event. Preserve coverage debt and avoid declaring the returned set exhaustive.

### AAVE-MONITOR-009: configured Pool address environment variable does not match the code

**Status:** Confirmed configuration mismatch.  
**Severity:** High for startup.

The monitor constructs its ethers Contract from `process.env.AAVE_LENDING_POOL` (monitor blob `677ae613db6f9ee8516da72bdb9759489978e009`, lines 49-55), but the checked-in `.env.example` defines `AAVE_POOL_ADDRESS` instead (env blob `008af85a7f7a6cb4815fd414e18bb04c790aff75`). With the supplied example file and no extra undocumented alias, the monitor receives an empty address string.

**Required remediation:** Use one canonical variable name and validate all required address/RPC inputs at process start with a clear error before creating the contract object.

### AAVE-WIRING-010: monitor never submits candidates to the flash-liquidation contract

**Status:** Confirmed missing integration in the inspected run path.  
**Severity:** Critical for the claimed end-to-end bot behavior.

`src/index.ts` creates a provider and wallet, logs the wallet address, constructs `PositionMonitor`, and starts a one-minute monitoring loop (index blob `3522cafd9bb708d5ae96184cb676bfadaefcbfe7`, lines 8-21). `PositionMonitor.startMonitoring` only finds positions and prints them (monitor blob, lines 223-250). The inspected monitor does not connect to `FlashLiquidator` or call `executeLiquidation`. The deployment script only deploys the contract (deploy blob `1a4c588e860bbbcbd8c7e781daf59e9ebdc0fd38`, lines 3-17).

**Required remediation:** Implement a separately tested, approval-gated executor adapter that validates the candidate, passes the exact liquidation parameters and swap route, verifies receipt status and emits auditable transaction outcomes. Do not equate monitoring with execution.

### AAVE-CONFIG-011: health-factor threshold defaults and example are inconsistent with liquidatability

**Status:** Confirmed configuration semantics; impact depends on operator settings.  
**Severity:** Medium.

The monitor accepts positions with `healthFactor < MIN_HEALTH_FACTOR` (monitor blob, lines 170-173). Its code default is 1.1 (line 56), which includes positions above Aave's liquidation boundary of 1.0; the checked-in `.env.example` sets 0.95, which excludes positions from 0.95 up to 1.0 despite those positions being below the protocol's 1.0 health-factor boundary. The README defines health factor below 1 as liquidatable (README blob `95b559797f21a5db443d69de5d59b64838d7a276`, lines 51-60).

**Required remediation:** Separate an early-warning threshold from the protocol liquidation eligibility predicate. Use the exact `healthFactor < 1e18` check for liquidatability and separately configure a buffer for monitoring.

## 4. Positive controls and design notes

- The on-chain `executeLiquidation` and token withdrawal functions are `onlyOwner` (contract blob, lines 113-143).
- The constructor uses the Aave `FlashLoanSimpleReceiverBase`, which stores both the provider and the actual Pool obtained through `provider.getPool()`. The project creates a second variable that bypasses this correctly initialized `POOL`.
- The `.env.example` contains placeholders, not a real private key. No credentials were accessed.
- The README itself lists “Implement real liquidations” among next steps (README blob, lines 173-177), which is consistent with an incomplete prototype rather than a production-ready bot.

## 5. Tests, CI, dependencies and maturity

- The repository root has no `test/` directory in the inspected tree, despite `package.json` defining `"test": "npx hardhat test"`.
- GitHub Actions API returned zero workflow runs at inspection; no test/CI workflow was present in the root tree.
- `@aave/core-v3` resolves to version `1.19.3` in the committed `package-lock.json`. The lockfile is present, but no dependency installation or candidate code execution was performed.
- The latest commit in the inspected history is 2024-12-23; no current maintenance or production deployment evidence was established.
- The repository root contains MIT license files; the Solidity contract also carries `SPDX-License-Identifier: MIT`.

## 6. Evidence limitations

- The Aave Pool address pointer, callback guard, swap absence and monitoring logic are static source observations.
- The exact Pool oracle `BASE_CURRENCY` and `BASE_CURRENCY_UNIT` were not queried on Arbitrum; the report flags the hard-coded decimal assumption rather than claiming a chain-state measurement.
- No Solidity compilation, Hardhat test, RPC call, fork, deployment, wallet, signature or transaction was performed.
- No realized liquidation, deployed bytecode match, external security audit or realized net-profit evidence exists in this review.

## Verdict

**Grade: D.** This is a directly relevant Aave V3 flash-loan-liquidation prototype, but it is not a verified or operational liquidator. The Pool/Provider pointer is wrong in the local execution path, the callback is missing caller/initiator authentication, no collateral-to-debt swap is implemented, and the monitor is disconnected from execution. The monitor additionally misreads Aave's collateral bitmap, uses a broken gross-profit formula, relies on a capped transaction-origin address list, and has environment-key and health-factor threshold mismatches. Retain as a negative/learning reference and do not promote it as a working implementation or profitability reference.
