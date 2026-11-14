# Candidate audit: 0xGusMcCrae/aave-liquidator-bot

- **Assessment:** D (provisional; obvious correctness and callback-safety defects; independent review pending)
- **Purpose:** Early-stage Aave/Arbitrum flash-loan liquidation prototype. README explicitly labels it a work in progress and says the author does not expect it to be competitive or safe on Arbitrum mainnet.
- **Repository identity:** GitHub repository ID `549892218`; default branch `main`; not a fork; GitHub metadata reports no license.
- **Pinned source:** merge commit `80bd056f37a7f0e3da4bd51a2ddb4bad979c11b2`; tree `68003fbb1e522ff814ec24bb0bfccd001f62d13b`; author date 2022-11-02.
- **Inspected blob pins:**
  - `contracts/flashloanHelper.sol`: `0ffba85c9cfd0d8b04150b0f02c39c12c9c96c78`
  - `contracts/liquidator.sol`: `5302ac76214244875cd35bad14690a8bb044dfe3`
  - `README.md`: `e7bb3fabb7a503ea8ab022b2a82a8f7b285ed655`

## What the code actually does

An Aave `flashLoanSimple` helper transfers borrowed debt tokens to a separate liquidator contract, calls a pre-encoded liquidation payload, and expects the liquidator to swap collateral back to debt token so Aave can pull repayment. The liquidator uses Aave L2 encoder/pool and Uniswap V3 exactInput.

## Findings and limitations

1. **Allowance expression is XOR, not exponentiation (critical correctness defect).** The expression `2^256 - 1` in Solidity uses bitwise XOR. It evaluates to 257, not `2^256 - 1`; constructor approvals therefore do not create the intended maximum allowance. This affects token approvals to Aave and Uniswap.
2. **Flash-loan callback is unauthenticated (critical security defect).** `executeOperation` is public and has no visible check that `msg.sender == address(pool)` or that `initiator == address(this)`. It transfers tokens to the configured liquidator and calls arbitrary encoded `params` supplied to the callback. A direct caller cannot mint the flash-loan amount, but can invoke the callback against any residual contract balance/allowances and trigger the downstream call path. Correct Aave receiver implementations must authenticate pool and initiator.
3. **Low-level liquidator call result ignored.** `liquidator.call(params)` discards the success flag and return data; the helper can continue even if liquidation call fails, relying only on later balance/repayment behavior.
4. **No return value from executeOperation.** The callback is declared `returns (bool)` in Aave receiver interface context but the implementation does not return `true`; depending on compiler/interface exactness this is a compile-time/interface compatibility issue or runtime ABI failure. The inspected source declares it without an explicit `returns (bool)` signature, which must be reconciled against the configured IPool interface before any build claim.
5. **No reentrancy guard or robust access restriction** on the helper's `getFlashLoan`; any caller can request a flash loan using the contract's configured liquidator and send residual debt-token balance to themselves. This is especially problematic if tokens become stuck in the helper.
6. **Profit/slippage assumptions are brittle.** The liquidator hardcodes a 0.3% pool fee and `amountOutMinimum = debtToCover * 403/400`, irrespective of token decimal normalization, actual liquidation bonus, premium, pool price or live quote. This may revert frequently or encode an unsafe/incorrect bound.
7. **No tests or safety evidence inspected.** README says work in progress and not expected safe/competitive on mainnet. No candidate code was executed by this research project.

## Verdict

Useful as a historical example of the Aave flashLoanSimple + external liquidator + Uniswap swap pattern, but not safe to deploy. The XOR allowance bug, unauthenticated callback, public flash-loan entry and unchecked external call are major defects. Provisional D.

## Evidence links

- [Pinned flash-loan helper](https://github.com/0xGusMcCrae/aave-liquidator-bot/blob/80bd056f37a7f0e3da4bd51a2ddb4bad979c11b2/contracts/flashloanHelper.sol)
- [Pinned liquidator](https://github.com/0xGusMcCrae/aave-liquidator-bot/blob/80bd056f37a7f0e3da4bd51a2ddb4bad979c11b2/contracts/liquidator.sol)
- [README](https://github.com/0xGusMcCrae/aave-liquidator-bot/blob/80bd056f37a7f0e3da4bd51a2ddb4bad979c11b2/README.md)

**Review status:** source inspection completed; independent reviewer not yet run; no execution.
