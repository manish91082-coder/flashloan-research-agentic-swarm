# Next Actions: Flash Loan & Liquidation Public Repository Research

## Locked mission

Discover the broadest reproducible set of public GitHub repositories across all 11 families in `research/keyword-taxonomy.json`, emphasizing flash-loan-powered DeFi liquidation and liquidator bots. For every candidate, determine actual purpose and what its code does, classify completeness/correctness/security/economics, inspect tests/CI/dependencies/license/maintenance, and preserve commit-pinned evidence plus independent review. Never claim literal global completeness beyond observed coverage.

## Verified implementation checkpoint

- Mission Form -> local API -> durable SQLite mission queue.
- Canonical keyword taxonomy v1.0.0 with 11 query families and family-specific GitHub search query templates.
- Paginated discovery runner with deduplication, query provenance and coverage-debt reporting.
- Mission DAG planner with stable task IDs, dependency validation, idempotent persistence, leases, retries and crash recovery.
- LangGraph control-flow graph with SQLite checkpoints.
- Deterministic discovery and commit-pinned source-capture stages.
- Mission worker polls queued/running missions.
- Latest main CI: `7e3853f4a95cf9ce2a8722de557b3dcee48dc502`, run `43592109714`, green on Python 3.11/3.12/3.13.
- Semantic AI specialists and independent reviewer are not yet active. The current executor truthfully blocks those tasks until a free local inference adapter is implemented and configured.
- No full 11-family live discovery run is claimed in this checkpoint.

## Next build gates, in order

### B2.1 Free local inference adapter
1. Define provider-neutral adapter contract and structured request/response schemas.
2. Support local OpenAI-compatible endpoints (e.g. Ollama-compatible local server) only when explicitly configured by the operator.
3. No cloud model default, no paid fallback, no API key requirement.
4. Add deterministic task budgets, timeout/retry ceilings, model identity, prompt-template version and output provenance.
5. Validate every output against strict JSON schemas; model output is untrusted.
6. If endpoint is absent/unavailable, mark only LLM-dependent tasks blocked; deterministic discovery and evidence work continue.

### B2.2 Specialist execution and review gates
7. Implement purpose classification using commit-pinned source maps, not repository name/README alone.
8. Run conditional specialist tasks: protocol/callback, Solidity security, liquidation math, execution/MEV, net economics, tests/CI, dependencies/license.
9. Deterministic evidence auditor checks commit SHA, tree SHA, blob SHA, path, line ranges and excerpt hashes.
10. Independent reviewer must challenge high-impact security/economic claims; disputed findings remain disputed.
11. No finding is accepted from a model assertion without evidence.

### B2.3 Task/report API and UI
12. Add mission task list, progress summary, report manifest and coverage-debt endpoints.
13. Show query family/page progress, unique candidates, audit queue, source-capture state, evidence/review confidence, blockers and next batch in the form dashboard.

### B2.4 Multi-batch autonomous continuation
14. Process candidate inventory in bounded batches until exhausted or a clearly recorded external limit is reached.
15. Persist cursor, batch ID, processed repository identities, retry state and next-batch task.
16. Reconcile forks/mirrors and canonical repository renames without losing provenance.
17. Automatically enqueue the next eligible batch; avoid reprocessing completed candidate tasks.

### Phase C forensic depth
18. Purpose-aware source maps and static AST extraction for Solidity/Python/TypeScript.
19. Protocol-specific liquidation eligibility, health-factor, close-factor, collateral seizure, debt/collateral decimals and oracle assumptions.
20. Flash-loan invariant: callback pre-existing debt-token balance must not subsidize repayment/profit. Check `Bcb >= B0 + P + F + M`.
21. Net economics includes flash premium, swap fees, gas, slippage, relay/builder costs and quote freshness.
22. Candidate code remains unexecuted. Ingest existing test/CI evidence only; never run untrusted candidate workflows.

### Phase D synthesis
23. Candidate matrix, per-repository purpose dossier, security findings, evidence register, protocol architecture map, test/CI and dependency/license report, coverage report and unresolved questions.
24. Rank by research relevance and evidence quality, not stars alone.

## Safety and trust invariants

- Public read-only research only.
- No candidate repository execution, wallet/key/signer access, signing, deployment, transaction broadcast or live trading.
- No paid API/model/service fallback.
- Repository content and model output are untrusted data.
- Mission Form remains the primary control plane; swarm owns planning, dispatch, verification, persistence and continuation.
