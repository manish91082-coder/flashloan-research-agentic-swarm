# Candidate Audit: MELD Labs Flashloan Liquidation Bot

- Repository: https://github.com/MELD-labs/meld-flashloan-liquidation-bot-public
- Default branch: main
- Inspected commit: 74653447a0ff9014f2e022d6778b442182f9841a
- Contract file: contracts/LiquidateLoan.sol
- Contract blob SHA: ec704736adb1ce3547bbbe4809c14ab345b134fc
- Callback interface blob SHA: 0a3a73501154db79b081085ef70533dbd8de70a8
- README blob SHA: a131cf26a3219bc33343ab0e79157fc1a4435361
- Package manifest blob SHA: aa1c31fa73fffe00423a565e4091369e87686efa
- Review type: bounded static source review; no candidate code executed

## Scope classification

The repository is an example MELD lending-protocol liquidation bot, not a generic multi-protocol DEX arbitrage engine. The README describes it as reference material and warns users not to trust it blindly (README lines 3-9). The described flow is flash-borrow debt asset, liquidate a position, swap collateral back to debt asset, send benefit to treasury and repay (README lines 41-48).

## Finding MELD-CALLBACK-AUTH-001: flash-loan callback lacks caller and initiator authentication

**Status:** Confirmed source-level security finding; runtime exploitability and deployment exposure not tested.

The external callback is declared at LiquidateLoan.sol lines 130-136. The initiator argument is unnamed/unused (line 134). The function does not check that msg.sender equals lendingPoolAddr or that the initiator equals address(this). It decodes params at lines 137-141, approves the configured lending pool at line 148, invokes liquidationCall using decoded collateral/user at lines 150-156, and performs swap/profit/repayment logic at lines 159-172.

The intended callback is documented as automatically invoked by the lending protocol (lines 126-129), and the interface defines an initiator parameter (IFlashLoanReceiver.sol lines 14-28). The source does not enforce that trust boundary. A direct external call can enter callback logic with caller-supplied arrays and params; whether that causes loss depends on balances, approvals, lending-pool state and router behavior at deployment. This is not claimed as a proven live exploit.

**Required remediation:** require callback caller to equal the currently configured lending pool, require initiator to equal address(this), validate array lengths and active operation state, bind callback params to the operation started by the entrypoint, and consume operation state exactly once. Test direct unauthorized calls, wrong initiator, replay and valid lender callback.

## Finding MELD-ACCOUNTING-002: minAmountOut subtracts balances in different token units

**Status:** Confirmed arithmetic/design defect in source; exact transaction impact depends on token decimals and asset pair.

At lines 159-161, currentBalance is the collateral-token balance, while amount and premium are denominated in the borrowed debt asset. The expression is:

    minAmountOut = (myMinBenefit * amount) / 10000 + premium - currentBalance

The subtraction mixes raw units of collateral token with raw units of debt token. If collateral and debt are different assets, these quantities are not dimensionally comparable. The subtraction can underflow and revert, or produce a meaningless minimum output. The value is passed as amountOutMin to the router (lines 181-201).

The default myMinBenefit is 10500 at line 49, with a comment describing 5% profit. The final check at lines 163-166 only requires profit > 0; it does not independently enforce a 5% net-profit floor.

**Required remediation:** compute minimum debt-token output entirely in debt-token units, without subtracting collateral-token balances. Derive it from principal, actual premium and a clearly defined profit floor. Separately snapshot the executor's pre-operation debt-token balance and enforce after >= before + principal + premium + minimumProfit before repayment. Add tests with differing token decimals and collateral/debt assets.

## Other observations

- liquidateUserWithFlashLoan is intentionally public/permissionless (lines 93-123); permissionless initiation is not itself a defect if callback authentication and operation binding are correct.
- swapToBorrowedAsset is public (lines 181-201); it operates on the contract's entire collateral-token balance using the configured router. Review whether this should be internal or operation-scoped.
- The bot reads BOT_OPERATING_WALLET_PRIVATE_KEY from environment and signs transactions in offchain-bot/main.py. This research project did not run that signing path.
- The inspected repository tree had no tests directory and no GitHub Actions workflow directory. This is an observation of the inspected tree, not proof that no external testing exists.
- Package manifest pins OpenZeppelin contracts 4.9.2 but uses caret ranges for many other dependencies; supply-chain reproducibility requires lockfile and dependency review.
- README calls the repository reference/example code and explicitly warns users to review it themselves.

## Verdict

**Grade: C+ as a reusable implementation reference; not production-ready on current evidence.** The architecture is useful for understanding a protocol-specific liquidation flow, but the callback trust boundary and cross-token-unit minimum-output calculation are material blockers. No on-chain deployment, fork reproduction, external audit or realized-profit evidence was established in this review.
