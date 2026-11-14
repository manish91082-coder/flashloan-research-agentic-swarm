# Next Actions

## Priority 0: connect the form to a real autonomous runtime
1. Build a mission intake API that validates `schemas/research-mission.schema.json` and rejects safety-policy overrides.
2. Add durable mission/task/run tables to SQLite with idempotency keys, status transitions, budgets and checkpoint references.
3. Implement the LangGraph Research Director graph with discovery and at least two specialist nodes; specialist outputs must be typed JSON.
4. Add deterministic evidence acceptance and an independent reviewer node before synthesis.
5. Persist every task result, tool call metadata, evidence reference, disagreement and next action in the canonical repository or durable store.
6. Add a continuation scheduler that enqueues the next eligible task automatically, with stop conditions for quotas, policy, missing evidence and human approval.

## Priority 1: form and runtime integration
7. Replace the local JSON-only form action with a submit-to-API workflow once the service endpoint is implemented; add mission status and report views.
8. Add integration tests proving form -> mission validation -> DAG -> multi-agent execution -> evidence gate -> independent review -> persistence -> resume -> next task.
9. Add tests proving form values and agent outputs cannot enable candidate-code execution, wallet access, signing, deployment, live trading or paid providers.

## Priority 2: research quality expansion
10. Expand metadata enrichment, search pagination, API retry, malformed payload, source cap, oversized blob and blob SHA mismatch tests.
11. Continue commit-pinned audits of the remaining discovered repositories and maintain a ranked queue.
12. Add Solidity/Python/Rust AST-aware analysis in isolated, pinned tooling without executing candidate repositories.
13. Improve profitability models and protocol-specific accounting invariant checks.

## Locked constraints
- Research-only; no candidate code execution.
- No wallet, private key, signing, deployment, transaction broadcast or live trading.
- No paid service/model fallback.
- GitHub remains canonical research history; n8n optional notifications only.
