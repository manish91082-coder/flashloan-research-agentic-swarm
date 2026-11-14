# Agent Roles

These are specialist capabilities coordinated by the Research Director. They are not ten always-on processes and are not manually prompted one by one.

## Mission control
1. **Research Director / Orchestrator:** validates mission scope, builds task DAG, dispatches workers, manages retries/budgets, resolves dependencies and controls acceptance.
2. **Continuity & Documentation:** persists state, task checkpoints, decision log, run history, research changelog and handoff.

## Research specialists
3. **GitHub Discovery:** search, pagination, metadata enrichment and candidate normalization.
4. **Protocol Specialist:** identifies actual flash funding primitive, protocol version, callback interface, chain and liquidation/arbitrage scope.
5. **Solidity Security Auditor:** callback caller/initiator, state binding, reentrancy, approvals, token accounting and profit invariants.
6. **Execution Engineer:** scanner, routing, exact trade size, quote consistency, simulation and transaction architecture. Research only; never broadcast.
7. **Test & Verification:** tests, CI artifacts, deterministic reproduction and regression fixtures.
8. **Economics & Quant:** premium, DEX fees, gas, slippage, liquidity, MEV and expected net-profit model.
9. **Dependency & License:** dependency versions, provenance, license compatibility and supply-chain risks.
10. **Evidence Auditor:** exact commit/tree/blob SHA, path, line ranges, excerpt integrity, source provenance and claim status.
11. **Independent Reviewer:** adversarial review by a role that did not author the finding. Security conclusions are not decided by majority vote.

## Dispatch policy
- Select specialists from mission scope and detected repository features.
- Keep tasks bounded with explicit inputs, output schema, dependencies, time/iteration budgets and acceptance criteria.
- Agent output is an untrusted proposal until deterministic validation succeeds.
- Preserve disagreements and unresolved claims.
- No agent can change mission safety policy or grant itself tools/permissions.
- If free model inference is unavailable, mark LLM-dependent tasks blocked; do not silently use paid services.
