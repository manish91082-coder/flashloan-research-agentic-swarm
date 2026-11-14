# Candidate Audit: Power-Howdy Flash USDT Bot

- Repository: https://github.com/Power-Howdy/flashloan-bot-ArbitrageAndLiquidation
- Default branch: main
- Inspected commit: 025eb602ddd96c3cc8479fb0fbd00cde13e198b6
- Tree: recursive tree was not truncated
- FlashLoan.sol blob SHA: 6afc0efd259c24a71cec3354cc324a12c7cabb49
- Arbitrage.sol blob SHA: 64791930ad7949bae327d498a391169553fc34b8
- Liquidation.sol blob SHA: 95af527ec5737cf84173e6ff1138200472c17fa8
- README blob SHA: e361422df364f152eb067a81c344f04c1d16cd7e
- package.json blob SHA: d5ad4b036281d9f36cd67966d274b626eb6ddb70
- Review type: bounded static source review; no code executed

## Scope classification

README describes a Flash USDT Bot for arbitrage and liquidation, but inspected contracts contain placeholders and incomplete interfaces. This is a prototype/example, not a functioning verified flash-loan implementation.

## Finding POWER-FLASH-CALLBACK-001: receiver callback flow is absent from the borrower contract

**Status:** Confirmed source-level architecture gap; exact behavior depends on the unspecified provider implementation.

FlashLoan.sol defines only a generic provider interface with flashLoan(borrower, token, amount, data) at lines 8-10. executeFlashLoan calls that function at lines 27-29, then attempts to perform arbitrage/liquidation after the provider call returns (lines 31-37), and approves only principal at line 41. The contract contains no lender callback entrypoint, no callback caller/initiator validation and no active-operation state. Under standard atomic flash-loan designs, the lender calls a borrower callback during the flashLoan call and expects repayment before the lender call completes. This repository does not implement that receiver flow.

## Finding POWER-ARBITRAGE-002: route and profit controls are placeholders

Arbitrage.sol uses address(0) as the target token in both swap legs (lines 44-60), passes amountOutMin=0 to both routers (lines 49-55 and 62-68), and contains no net-profit or repayment invariant. The comments at lines 40-42 and 70-73 explicitly leave flash-loan and repayment integration as assumptions/comments.

## Finding POWER-LIQUIDATION-003: borrower and protocol integration are placeholders

FlashLoan.sol hardcodes borrower = address(0) in the liquidation branch (lines 31-35). Liquidation.sol exposes a generic ILendingProtocol interface rather than a verified protocol adapter; executeLiquidation calls getDebtAmount and liquidate but does not validate protocol-specific eligibility, collateral/debt token relationships or post-liquidation repayment economics (lines 6-9 and 22-32).

## Additional observations

- owner is assigned in FlashLoan.sol and stored in the Arbitrage/Liquidation contracts but no access-control modifier uses it in the inspected functions.
- README asks the user to provide a real USDT address and describes the deployment flow, but that does not close the code placeholders.
- package.json has a small Hardhat dependency set; no tests directory or GitHub Actions workflows were present in the inspected tree.
- No live deployment, fork test, independent audit or realized-profit evidence was established.

## Verdict

**Grade: D / non-functional prototype for the stated flash-loan use case.** It is useful only as a list of intended components. It should not be used as a base implementation without a complete lender-specific callback, real token/router/protocol addresses, authorization, operation-state controls, token-unit-safe accounting, slippage limits, profit checks and tests.
