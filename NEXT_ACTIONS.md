# Next Actions: Flash Loan & Liquidation Public Repository Research

## Locked mission

Discover the broadest reproducible set of public GitHub repositories across all 11 taxonomy families, emphasizing flash-loan-powered DeFi liquidation and liquidator bots. For each candidate, determine actual purpose and code behavior, classify completeness/correctness/security/economics, inspect tests/CI/dependencies/license/maintenance, and preserve commit-pinned evidence plus independent review. Never claim literal global completeness beyond measured coverage.

## Implemented checkpoint

- Mission Form -> local API -> durable SQLite queue.
- Taxonomy v1.0.0 with 11 query families and family-specific search templates.
- Paginated GitHub discovery, candidate deduplication, query provenance and coverage-debt manifest.
- Idempotent dependency-aware mission DAG, SQLite task persistence, leases, retries and checkpoint recovery.
- LangGraph control-flow graph with SQLite checkpoint saver and mission worker.
- Parallel discovery and commit-pinned repository source capture.
- Loopback-only OpenAI-compatible model adapter; cloud endpoints, redirects and paid fallback rejected.
- Specialist role prompts, strict JSON contract, exact signal-to-source evidence matching and deterministic evidence provenance gate.
- Independent reviewer task remains downstream of evidence validation.
- Latest candidate commit: `278031dd0a88106bb7a38dff7425161ed1faa94a`; CI run `43593929471` queued at checkpoint. Previous runtime/provider commits passed on Python 3.11/3.12/3.13.
- No live 11-family mission execution is claimed yet. Current semantic specialist path still needs end-to-end fake-provider tests and a bounded live mission.

## Immediate next gates

1. Verify CI for latest main and fix any failures before proceeding.
2. Add fake local-model integration tests covering candidate-purpose classification -> specialist roles -> deterministic evidence validation -> independent reviewer.
3. Harden provider failure handling, lease recovery and mission resume; distinguish retryable provider outages from permanent schema/evidence rejection.
4. Make specialist context source-aware: retrieve bounded full source excerpts by exact path/line from pinned blobs, not just lexical signals. Keep excerpt size limits and hashes.
5. Add deterministic liquidation/protocol accounting extractors and structured purpose taxonomy.
6. Add mission task/report/coverage endpoints and dashboard progress view.
7. Implement multi-batch candidate continuation with persisted cursor and dedup/fork reconciliation.
8. Run a bounded live discovery mission across all 11 families; persist raw query coverage, candidate inventory and commit-pinned inspection reports.
9. Expand candidate processing until inventory exhausted or coverage limits explicitly recorded.
10. Produce repository-purpose dossiers, audit matrix, evidence register, security/economic findings, test/CI/license reports and synthesis.

## Specialist acceptance contract

- Purpose classification is separate from quality/security grade.
- A model may propose an interpretation but cannot invent a source location.
- A signal match proves excerpt provenance only, not vulnerability or correctness.
- High-impact claims require full source context and independent challenge.
- If model endpoint is absent, unreachable, or returns invalid output, LLM tasks remain explicitly blocked/failed; deterministic discovery must remain available.
- No paid or cloud model fallback.

## Safety

Public read-only research. Never execute candidate code. No wallet/key/signer access, signing, deployment, transaction broadcast or live trading. Treat repository content and model output as untrusted. The Mission Form remains the primary control plane; the autonomous swarm plans, dispatches, validates, persists and continues.
