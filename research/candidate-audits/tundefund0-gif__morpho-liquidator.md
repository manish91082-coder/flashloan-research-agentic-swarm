# Candidate Audit: tundefund0-gif Morpho Liquidator

- Repository: https://github.com/tundefund0-gif/morpho-liquidator
- Default branch: master
- Inspected commit: 7cbfa8abc8f0c75b38f75ac4b0878ffe883645e9
- Tree: recursive tree was not truncated; one main source file, bot_v4.py
- Source blob SHA: 8d36ed6cecdf421ef0dcd67bdcee56d8ee509fb9
- Review type: static review of source and embedded Solidity; no script, bytecode, RPC transaction or deployment executed

## Scope classification

This is an active-style Morpho Blue liquidation bot with capital-backed and Balancer flash-loan paths for Ethereum and Base. It is not a passive research-only scanner. The Python program reads a private key from LIQUIDATOR_PK (lines 12-14), constructs and signs EIP-1559 transactions (lines 100-114), and sends raw transactions through eth_sendRawTransaction (RPC method at lines 145-146).

## Finding MORPHO-EXEC-001: startup can deploy a contract and the bot can broadcast transactions

**Status:** Confirmed source-level operational behavior; not executed.

The file embeds a non-empty FL_BYTECODE value and check_fl_contract constructs a deployment transaction and broadcasts it (lines 220-245). The main loop calls check_fl_contract when the Balancer vault exists and bytecode is present (lines 449-459). The main loop then scans positions and enters an execution loop (lines 463-490). The transaction helper signs and sends raw transactions (lines 100-114 and 145-146). This is a material operational boundary: running the script with a valid LIQUIDATOR_PK and funded wallet can deploy contracts and execute on-chain actions. It must never be run as part of this research pipeline.

## Finding MORPHO-ACCOUNTING-002: flash callback repayment check can consume pre-existing dust

**Status:** Confirmed source-level accounting weakness in embedded contract.

The embedded MorphoFL.receiveFlashLoan callback snapshots balBefore at the loan-token balance (embedded Solidity around bot_v4.py lines 190-194), but does not use that value. It checks only balAfter >= amounts[0] + fees[0] before transferring repayment to the Balancer vault. It does not require post-repayment balance to remain at least the pre-loan balance plus a minimum profit. Pre-existing loan-token dust can therefore mask a strategy loss or insufficient swap output. The owner-only withdraw can later remove remaining balances, but it does not repair the missing invariant.

**Required remediation:** snapshot the loan-token balance before the flash loan; after liquidation and swap, require balance >= pre-loan balance + principal + actual fee + configured minimum profit before repayment. Also verify that the amount borrowed, debt shares repaid and collateral seized are consistent.

## Finding MORPHO-QUOTE-003: failed quote falls back to amountOutMin = 1

**Status:** Confirmed fail-open behavior in off-chain strategy construction.

In liq_fl (around lines 390-405), quote failure is caught broadly and min_out is set to 1. The transaction is then still constructed and may be broadcast. This defeats the intended fail-closed requirement when the quote is unavailable or malformed. A one-unit minimum is not a meaningful slippage or profitability bound.

**Required remediation:** abort opportunity construction on any quote failure; bind quote to a recent block; simulate the exact transaction; calculate full flash fee, DEX fee, gas and relay costs; enforce a positive net-profit threshold before any signing path.

## Other observations

- The embedded flash-loan callback checks msg.sender == Balancer Vault and execute/withdraw are owner-only. These are positive controls, but they do not replace balance-delta profit accounting.
- The embedded contract calculates balBefore but never uses it.
- The bot uses public RPC endpoints and performs its own transaction signing; no credentials or wallet values were accessed in this research.
- The bot uses broad exception handling in RPC/quote paths, which can obscure the reason for failures.
- No automated tests or CI were found in the inspected repository tree.
- The precompiled bytecode is embedded in the source. It was not executed or independently matched to the Solidity source in this review.

## Verdict

**Grade: C as a research reference; unsafe to run without substantial remediation and independent verification.** It contains a real Morpho/Balancer liquidation design and useful integration concepts, but it is an active transaction sender/deployer, its flash-loan balance check can count pre-existing dust as profit, and quote failure falls back to a near-zero minimum. No live execution, deployed bytecode verification, fork test, external audit or realized-profit evidence was established.
