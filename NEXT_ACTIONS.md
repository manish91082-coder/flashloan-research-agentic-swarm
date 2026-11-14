# Next Actions

## Priority 0: autonomous agent runtime
1. Implement mission task-DAG planner from queued mission payloads, with typed task records, dependencies, budgets, retries and idempotency.
2. Add LangGraph as a pinned optional dependency and build checkpointed graph state with deterministic nodes first.
3. Implement Research Director, GitHub Discovery and Protocol Triage nodes, then conditional parallel specialist nodes for Security, Execution, Economics, Testing and Dependency/License.
4. Add deterministic evidence validator and independent reviewer gate; no security finding is accepted on model assertion alone.
5. Implement worker loop that claims queued missions, advances tasks, persists checkpoints and automatically enqueues the next eligible research task.
6. Add status/report endpoints and UI mission progress view; distinguish queued, running, blocked, needs_approval, completed and failed.
7. Add integration tests for mission submission -> plan -> multi-node execution -> evidence validation -> independent review -> persistence -> crash/resume -> continuation.

## Priority 1: free model integration
8. Add provider adapter interface and a deterministic no-model mode. Enable only explicitly configured free model endpoints; if unavailable, mark model tasks blocked and continue deterministic tasks. Never fallback to paid inference.
9. Record provider/model identity, prompt/template version, token usage where available, outputs and validation results. Treat model outputs as untrusted.

## Priority 2: research quality
10. Expand metadata enrichment, pagination, retry/rate-limit and malformed payload tests.
11. Continue commit-pinned audits of remaining discovered repositories.
12. Add Solidity/Python/Rust AST-aware analysis in isolated, pinned tooling without executing candidate repositories.
13. Add protocol-specific accounting and profitability invariants with fixture-backed tests.

## Locked constraints
- Mission Form remains primary user interface; no manual per-agent prompting as normal workflow.
- Agents plan, dispatch, research, verify, persist and continue autonomously within bounded policy.
- No candidate code execution, wallet, key, signing, deployment, transaction broadcast or live trading.
- No paid model/service fallback.
