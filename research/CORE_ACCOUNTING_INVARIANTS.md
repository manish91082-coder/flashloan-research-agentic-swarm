# Flash-Loan Accounting Invariants

## On-chain debt-token invariant

Let:
- B0 = executor debt-token balance immediately before the flash loan.
- P = principal borrowed.
- F = actual flash premium supplied by the lender callback.
- M = configured minimum on-chain profit.
- Bcb = executor debt-token balance after strategy execution and immediately before the lender pulls repayment.

Require:

    Bcb >= B0 + P + F + M

After the lender pulls principal plus premium:

    Bafter >= B0 + M

The baseline B0 prevents pre-existing dust from being miscounted as profit. Use the callback-supplied premium, not a hardcoded fee. Keep the repayment check in the on-chain executor.

## Off-chain expected-net-profit gate

    ExpectedNetProfit = ExpectedGrossProfit
                      - FlashLoanFee
                      - DEXFees
                      - ExpectedGas
                      - Slippage
                      - RelayOrBuilderCost
                      - OtherExecutionCosts

Do not mark an opportunity executable when a required cost or conversion price is missing, stale or untrusted. A quote is not execution proof. A simulation is not realized profit. On-chain borrowed-token profit floor and off-chain operator net-profit floor are separate controls.

## Review checklist
- Snapshot balances before borrowing.
- Authenticate callback caller, initiator and active operation state.
- Consume callback state exactly once.
- Check principal plus actual premium repayment.
- Enforce a minimum profit above the pre-loan balance.
- Bound token approvals and router targets.
- Pin quote/simulation block state where possible.
- Account for gas, flash fees, pool fees, slippage and MEV/relay costs.
- Fail closed on missing data or stale quotes.
