# Next Actions: Flash Loan & Liquidation Public Repository Research

## Locked mission

Discover the broadest reproducible set of public GitHub repositories across all 11 taxonomy families, emphasizing flash-loan-powered DeFi liquidation and liquidator bots. For each candidate, determine actual purpose and code behavior, classify completeness/correctness/security/economics, inspect tests/CI/dependencies/license/maintenance, and preserve commit-pinned evidence plus independent review. Never claim literal global completeness beyond measured coverage.

## Verified checkpoint

- Mission Form -> local API -> durable SQLite queue is implemented.
- Taxonomy v1.0.0 defines 11 query families and 38 configured query templates.
- Live GitHub Actions run [43600488013](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43600488013) successfully executed all 11 families.
- Discovery summary: **7,901 unique repository candidates; 38 queries; 28 complete; 10 incomplete; coverage_complete=false**. These are discovery candidates, not verified working bots.
- Raw report: `research_runs/mission/2026-11-14/discovery-43600488013-1.json`; artifact commit `231f47f0ada252a921a065da935720873f397bef`; blob SHA `3f126f4cfa4e163dbe95cb7ffb7f2528180254d5`.
- Earlier manual 1,833-name representative sample remains a separate non-exhaustive baseline, not the project-runner result.
- LangGraph, SQLite task DAG/leases/checkpoints, deterministic discovery/source capture and local-only semantic specialist/evidence/reviewer stage are implemented.
- Specialist context uses bounded line-numbered excerpts from the content-addressed vault after Git blob SHA-1 verification; evidence validation covers purpose and specialist outputs; independent reviewer receives prior report content.
- Fake-provider end-to-end fixture covers candidate purpose, six specialist roles, evidence validation and independent review. **58 tests pass** on Python 3.11/3.12/3.13; latest main CI run `43601777341` succeeded.
- Five candidate dossiers are tracked. Lumetra Labs Morpho bot grade C (native Morpho liquidation callback in reviewed path, not flash-loan funded); 0xnavarro Aave Liquiditor grade D (critical wiring/accounting gaps). New findings are pending independent review.
- No real local-model mission, candidate-code execution, deployment or transaction has occurred.

## Immediate next gates

1. **Completed:** stream-imported all 7,901 candidate rows and persisted stable repository IDs, canonical names and query-family provenance.
2. **Completed:** exported 80 immutable JSONL packets (100 candidates per packet) with source-report SHA-256, per-batch SHA-256, candidate-index continuity and identity verification. Audit status remains pending.
3. **Manual priority sample completed:** four packet-0001 candidates source-inspected at exact commit/tree/blob pins and documented in four provisional dossiers; independent review pending. This does not change the automated queue source-capture counter (still 0/7,901).
4. Implement a resumable source-capture worker with per-candidate status, attempt counts, leases/checkpoints and atomic result writes; preserve current default-branch commit, tree, blob and fork/parent/source identity.
5. Prioritize candidates matched to flash-loan liquidation and DeFi liquidator families, then process all remaining taxonomy families without dropping them.
6. Capture bounded source evidence and deterministic purpose hints; do not claim semantic purpose classification until source evidence and an approved reviewer support it.
7. Build deterministic candidate dossiers and mission synthesis only from source-pinned, evidence-validated and independently reviewed outputs.
8. Implement true multi-batch continuation with completed-candidate set, retry-safe IDs, lease recovery and explicit stop conditions.
9. Investigate and rerun only the 10 incomplete discovery query templates; retain old snapshots and coverage debt.
10. Add task/report/coverage endpoints and a dashboard for discovered/imported/source-inspected/audited queues, query debt, evidence confidence, reviewer status and next batch.
11. Run real local-model inference only after a free loopback endpoint is explicitly configured; no paid/cloud fallback. Publish synthesis only with coverage and evidence limitations.

## Latest verified batch-preparation checkpoint

- Current main data commit: `8448711d734978d5c0e793793feccf08dad29747`.
- Preparation workflow run [43603644216](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43603644216) completed successfully; associated code CI run [43603644293](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43603644293) passed Python 3.11/3.12/3.13.
- All 7,901 discovery rows were stream-imported and exported to `research_runs/audit-batches/43600488013/` as **80 JSONL batches**, maximum 100 records each.
- Batch verification: 7,901 unique canonical repository names; 7,901 unique GitHub repository IDs; candidate indexes 0–7,900 contiguous; all 80 batch SHA-256 hashes verified.
- Manifest SHA-256: `45014ead9e61098cef320704131752f63f2a4ebe392947bd8204fd1a34ad43fd`; source report SHA-256: `d99ebcdcbd1739536ba987e51ffe2a5c06610094e24b4603c89d3f5f32db3002`.
- This is metadata import and queue preparation only. Candidate source capture and audits from this 7,901-row queue remain **0/7,901**; existing five dossiers remain a separate prior audit sample. No candidate code was executed.
- Future `research-discovery.yml` runs now perform import/export of their own discovery rows during the same workflow.

## Latest priority source-inspection checkpoint

- Five candidates from immutable packet `research_runs/audit-batches/43600488013/batch-0001.jsonl` were inspected at exact default-branch commit/tree/blob pins: `0xTona/liquidator-bot`, `0xFantomMenace/Aave-Liquidation-Bot`, `0xFantomMenace/Compound-Liquidation-Bot`, `0xGusMcCrae/aave-liquidator-bot`, and `0xTwyne/twyne-liquidation-bot`.
- Five provisional dossiers were added under `research/candidate-audits/`. Grades: C, C, D, D, B respectively; all are pending independent reviewer validation.
- Notable findings: Tona does not deduct gas from its positive-gross-profit gate; FantomMenace's HyperLend and Granary subprojects have different callback security; Compound liquidator has a reserve-index/purchasable-array construction defect and zero swap minimum; Gus uses Solidity XOR `2^256 - 1` (257, not max allowance) and exposes an unauthenticated callback.
- These are five manually source-inspected candidates, not yet automated source-capture completion. The 7,901-row batch queue's automated source-capture counter remains 0/7,901. Candidate code was not built, tested or executed. Independent review is pending.

- Additional priority candidate: `0xTwyne/twyne-liquidation-bot`, pinned commit `568a6308adf82952a156b6374ae264643a0c4fc2`, tree `7a24b296c6c0947d95c2a6f54921a33fa4b5575f`; provisional grade B. This is a Twyne-specific Euler/Aave collateral-vault liquidation system using Morpho Blue flash loans, with authenticated callback, explicit min-profit gate and active fork-test source. Dossier: `research/candidate-audits/0xTwyne__twyne-liquidation-bot.md`.

## Specialist acceptance contract

- Purpose classification is separate from quality/security grade.
- A model may propose an interpretation but cannot invent a source location.
- A signal match proves excerpt provenance only, not vulnerability or correctness.
- High-impact claims require full source context and independent challenge.
- If model endpoint is absent, unreachable, or returns invalid output, LLM tasks remain explicitly blocked/failed; deterministic discovery must remain available.
- No paid or cloud model fallback.

## Safety

Public read-only research. Never execute candidate code. No wallet/key/signer access, signing, deployment, transaction broadcast or live trading. Treat repository content and model output as untrusted. The Mission Form remains the primary control plane; the autonomous swarm plans, dispatches, validates, persists and continues.
