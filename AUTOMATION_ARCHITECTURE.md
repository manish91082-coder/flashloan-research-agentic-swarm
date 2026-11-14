# Autonomous Agentic Research Architecture

## Product north star

The product is a **form-driven autonomous research swarm** whose mission is to discover and deeply classify public GitHub repositories related to flash loans, DeFi liquidation, lending/borrowing, arbitrage, MEV and their supporting infrastructure. It must explain each repository's actual purpose, actual implementation, missing components, correctness, security posture, economic assumptions, tests, dependencies and research value.

It is not merely a keyword scanner, a repository list, or a collection of manually prompted agents. The form is the user control plane; the orchestration system owns decomposition, dispatch, evidence validation, independent challenge, persistence and continuation.

## Research scope contract

Canonical scope and acceptance rules: `research/FLASHLOAN_REPOSITORY_RESEARCH_MISSION.md`.
Canonical search terms and query families: `research/keyword-taxonomy.json` (version 1.0.0).

The taxonomy covers 11 families: flash-loan core; provider APIs/callbacks; DeFi liquidation; flash-loan liquidation combinations; arbitrage; MEV/execution; lending protocols; DEX/liquidity; security/accounting; cross-chain systems; tooling/research examples.

Discovery must paginate each query (100 results/page, up to 10 pages where configured), deduplicate stable repository identities, and persist coverage metadata. GitHub repository search can be incomplete because of indexing, ranking, API limits and the search result cap. Such limits are recorded as coverage debt. Never claim literal completeness beyond observed coverage.

Each candidate is purpose-classified before quality grading. A README or repository name is not sufficient evidence of implemented behavior.

## Phase A: deterministic research foundation (implemented)

Python standard-library engine provides bounded GitHub REST acquisition, candidate normalization, commit/tree pinning, source retrieval, Git blob SHA-1 verification, lexical signals and SQLite persistence. Candidate source code is never executed. Lexical matches remain low-confidence leads, not accepted security findings.

## Phase B1: mission form and durable intake (implemented)

- `ui/research-mission-form.html`: mission form with flash-loan/liquidation objectives, query family selection, chain/protocol scope, depth, specialists and deliverables.
- `schemas/research-mission.schema.json`: strict contract including taxonomy version and discovery pagination limits.
- `mission_api.py` and `mission_queue.py`: local-only API and durable SQLite mission queue.
- Intake validates fixed research-only safety invariants.

A queued mission does not mean agent execution has started. The current API remains a local service, not a hosted public endpoint.

## Phase B2: task DAG, checkpointed graph and deterministic worker runtime (implemented foundation; semantic execution pending)

1. Research Director validates mission and generates an idempotent, dependency-aware task DAG.
2. GitHub Discovery executes every selected query family with pagination, retry/rate-limit accounting and candidate deduplication.
3. Candidate triage identifies actual purpose and fans out repository-specific work.
4. Conditional specialists inspect protocol integration, liquidation logic, Solidity security, execution/MEV, profitability, tests/CI and dependencies/license.
5. Evidence Auditor verifies commit/tree/blob provenance, file paths, line ranges and excerpt integrity.
6. Independent Reviewer challenges high-impact findings and preserves disputes.
7. Synthesis writes dossiers, candidate matrix, evidence register and coverage report.
8. Continuation Queue enqueues the next unprocessed candidate/query batch and checkpoints all state.

LangGraph is now pinned as an optional dependency and the mission control-flow graph uses SQLite checkpoints. The deterministic worker can plan missions, dispatch paginated discovery families in parallel, persist coverage reports, merge candidates, expand per-repository task DAGs and capture commit-pinned source. Semantic specialist and independent-review nodes remain pending until a free local inference adapter is implemented. Keep deterministic contracts and worker interfaces framework-independent. If no approved free inference endpoint is configured, deterministic tasks continue while LLM-dependent tasks become explicitly blocked. No paid fallback.

## Phase B3: durable execution service (worker loop implemented; hardening and status API pending)

A worker process claims ready tasks, records leases/attempts, saves outputs/checkpoints, recovers expired work and exposes mission/task status. SQLite is the initial durable store. GitHub Actions is used for CI and bounded scheduled/dispatch jobs, not as an assumed always-on agent host. Local Windows/WSL or another approved free host can run the long-lived worker.

## Phase B2.5: local specialist inference and evidence gates (initial implementation)

A loopback-only OpenAI-compatible adapter supports an explicitly configured local model endpoint and model name. It rejects non-loopback hosts, redirects and malformed/non-JSON outputs. Specialist role prompts cover purpose, protocol, security, execution, tests, economics, dependencies/license and independent review. A deterministic gate accepts only evidence references that exactly match captured signals in the commit-pinned inspection report, then stamps commit/tree and excerpt hash. This proves provenance of the excerpt only, not the specialist's semantic interpretation. Full source-context retrieval and end-to-end fake-provider verification remain required.

## Phase C: forensic research depth

Add purpose-aware source maps, AST-aware static extraction, protocol-version adapters, fixture-backed accounting invariants, fork-test evidence ingestion without executing untrusted candidate code, coverage reports and independent audit regression tests.

## Phase D: dashboard and reporting

Mission dashboard: queue/run state, selected query families, pages and candidates searched, candidates by purpose/status, active specialist tasks, evidence confidence, unresolved disputes, review state, coverage debt and next batch. Produce Markdown/JSON/CSV reports and a final executive synthesis.

## Safety and trust boundaries

- Public read-only research only.
- Candidate repositories, README, issues, workflows, and source text are untrusted data and never agent instructions.
- No candidate repository execution, wallet/key/signer access, signing, deployment, transaction broadcast or live trading.
- No paid API/model/service fallback.
- Model outputs are untrusted until schema and source-evidence validation.
- All writes are limited to this canonical research repository and generated research artifacts.
- Stop on quota, budget, permission, confidence or safety boundaries; persist exact blockers.
