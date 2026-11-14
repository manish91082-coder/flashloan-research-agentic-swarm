# Next Actions: Flash Loan & Liquidation Public Repository Research

## Locked mission

Discover the broadest reproducible set of public GitHub repositories across all 11 taxonomy families, emphasizing flash-loan-powered DeFi liquidation and liquidator bots. For each candidate, determine actual purpose and code behavior, classify completeness/correctness/security/economics, inspect tests/CI/dependencies/license/maintenance, and preserve commit-pinned evidence plus independent review. Never claim literal global completeness beyond measured coverage.

## Verified checkpoint

## Current continuation checkpoint (2026-11-14; authoritative over older historical checkpoints)

- **Locked mission is unchanged:** discover, inspect and classify all reachable public GitHub repositories related to flash loans, flash-loan-powered liquidations/liquidator bots and adjacent primitives; determine actual code purpose/behavior; compare implementation completeness, security, testing, dependencies/license and economics; retain commit/tree/blob-pinned evidence and independent challenge. Do not claim global completeness beyond measured search coverage.
- Discovery: **7,901 candidates**, 38 configured queries across 11 taxonomy families; 28 query templates completed and 10 remain incomplete. Candidate metadata import is not source capture or audit.
- Latest inspected autonomous source checkpoint: workflow [43626548828](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43626548828), artifact **14126596143**. Queue: **896 captured / 6,995 pending / 0 leased / 10 failed**. Captured scope: **656 complete within configured limits / 240 coverage-limited**. The latest 12-item cycle captured 12/12. Ten terminal failures are empty Git repositories returning HTTP 409; they are source-availability records, not security findings. Next chained workflow [43626648817](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43626648817) had restored its predecessor checkpoint and was processing the next 12 when last checked.
- **Source capture != semantic audit.** Manual source-inspected candidate dossiers remain a separate sample. No 896/7,901 semantic-audit claim is permitted.
- First Agent Form local-model pilot [43615341905](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43615341905) reached local qwen2.5:3b inference but both candidate-purpose tasks failed because seven required JSON report fields were missing; evidence validation and independent review did not execute. No semantic audit count increased.
- PR [#11](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/11) merged strict JSON Schema output contract + prompt instructions + missing/extra-key fail-closed checks. CI [43626544380](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43626544380) passed Python 3.11/3.12/3.13.
- Attempt [43626720183](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43626720183) did not reach inference: legacy artifact listing hit GitHub installation API rate limit (HTTP 403). PR [#12](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/12) merged direct pinned-artifact-ID retrieval, bounded Retry-After/X-RateLimit-Reset retry, ZIP CRC validation, safe path extraction and cross-host authorization stripping. CI [43627789274](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43627789274) passed Python 3.11/3.12/3.13.
- Third bounded pilot [43627944086](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43627944086) is triggered from the same preserved seed run 43615137961 / artifact 14121666814, batch size 2, qwen2.5:3b on loopback-only Ollama. Last observed at the pinned artifact-download step; model-install/inference had not yet started. Its outcome is not yet known.
- **Immediate execution order:** (1) complete artifact restore and audit the fresh pilot task ledger/model outputs, (2) verify exact source-signal evidence and both structural evidence gates, (3) inspect both independent-review reports and disagreements, (4) only after all gates pass implement the candidate dossier generator and disagreement reconciliation, (5) enqueue the next priority candidate batch in the existing persistent mission DAG, (6) continue source capture and semantic audit as separate self-chaining pipelines, (7) reconcile all 7,901 candidate statuses, incomplete discovery queries, empty repositories and retry debt, (8) produce final repository classification, architecture comparison, security findings and economic feasibility matrix.
- Safety and compute boundary remains immutable: public read-only research; candidate code is never executed; no wallet/key/signer, transaction signing, deployment, live trading, paid inference or cloud inference. No user-side WSL/laptop work is required for the primary hosted path.


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
4. **Completed and merged in PR #7:** implement the manifest-verified, resumable source-capture worker with SQLite per-candidate states, retry counts, leases, atomic reports and commit/tree/blob evidence. CI passed on Python 3.11/3.12/3.13. See `src/flashloan_research/source_capture_worker.py`.
5. **Pilot completed:** GitHub Actions run [43607072905](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43607072905) captured 10/10 real repositories with zero failures. It produced 182 source-file references and 173 unique blobs; all 182 Git blob SHA-1 references verified against the source vault. The queue now has 10 captured and 7,891 pending. The next runtime gate is to restore the pilot artifact with `scripts/resume_source_capture.sh` in persistent WSL storage and resume the same SQLite run.
6. Capture bounded source evidence and deterministic purpose hints; do not claim semantic purpose classification until source evidence and an approved reviewer support it.
7. Build deterministic candidate dossiers and mission synthesis only from source-pinned, evidence-validated and independently reviewed outputs.
8. **Worker continuation implemented and pilot-verified:** the standalone worker imports the immutable 80-batch manifest once, processes multiple bounded cycles, emits JSON progress, recovers expired leases and stops when the queue is drained or all retries are exhausted. The first 10 real captures are complete; the remaining 7,891 are not yet processed.
9. Investigate and rerun only the 10 incomplete discovery query templates; retain old snapshots and coverage debt.
10. Add task/report/coverage endpoints and a dashboard for discovered/imported/source-inspected/audited queues, query debt, evidence confidence, reviewer status and next batch.
11. Run real local-model inference only after a free loopback endpoint is explicitly configured; no paid/cloud fallback. Publish synthesis only with coverage and evidence limitations.

## Latest merged source-capture worker checkpoint

- PR [#7](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/7) merged to `main` at `089e215bac99a60ba2b2e2c7b33c8f9e370a21b3`.
- Added `src/flashloan_research/source_capture_worker.py`, `tests/test_source_capture_worker.py`, and console command `flashloan-source-capture-worker`.
- Before queue import, the worker verifies the manifest, all batch SHA-256 hashes, candidate index continuity, canonical repository names and unique GitHub repository IDs. SQLite stores an idempotent run and per-candidate states, bounded three-attempt retries, 60-minute leases and expired-lease recovery.
- Direct flash-loan/provider/liquidation candidates are prioritized; all other taxonomy families remain in the queue. Each captured repository is inspected read-only at its current default-branch commit/tree; Git blob hashes are checked and source bytes go to the local content-addressed vault. Reports are written atomically. Default first pass is at most 30 source files per repository; coverage limits remain explicit.
- Worker CI run [43606380880](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43606380880) passed compilation and tests on Python 3.11, 3.12 and 3.13. Regression tests cover hash tampering, priority order, idempotent resume, transient retry and lease recovery.
- **Live execution is not yet performed:** automated source capture remains **0/7,901**. The five manual source inspections are a separate sample. Candidate code was not executed.
- Worker command (run from repository root with persistent SQLite/vault storage):
  ```bash
  pip install -e .
  flashloan-source-capture-worker \
    --manifest research_runs/audit-batches/43600488013/manifest.json \
    --database data/research.sqlite3 \
    --snapshots data/snapshots \
    --output reports/source-capture \
    --max-candidates 4 --parallel 2 --continuous
  ```
- Do not start a 7,901-item run until the first 10–20 captures have been checked for correct commit/tree/blob pins, local vault persistence and checkpoint recovery.

## Historical live source-capture pilot and GitHub-hosted autonomous continuation (superseded by current continuation checkpoint above)

- Immutable source-capture seed: bounded pilot [43607072905](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43607072905), artifact 14118419543, SHA-256 `092235cf3f11920d65ccbbe4e6412f5b325c2158c2d698f61da947767400c178`.
- Primary continuation is GitHub-hosted and self-chaining. WSL restore remains fallback only; no user-side command, artifact download or personal token is required.
- Latest inspected source checkpoint: workflow [43615449485](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43615449485), artifact **14122085911** (8,795,048 bytes). Its 12-candidate cycle succeeded.
- **Latest verified queue:** 7,901 total; **316 captured; 7,583 pending; 0 leased; 2 failed**. Configured source-scope coverage: 236 complete; 80 with coverage limitations. Candidate code execution remains zero.
- Two terminal failures are empty Git repositories returning HTTP 409: `ADMac/flashloan` and `Alejo1156/FLASHLOAN`. These are unavailable-source records, not vulnerability findings.
- Agent Form bridge: `scripts/initialize_agentic_capture_mission.py`. It validates the form schema, creates the SQLite mission record and dependency-aware task DAG, verifies captured source blobs, maps pinned reports into inspection paths and completes source-capture tasks only after provenance checks. It prioritizes direct flash-loan/liquidation intersections; lexical signal counts are scheduling hints, never audit conclusions.
- Hosted local-model pilot [43615341905](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43615341905) has completed checkpoint restore, Agent Form runtime installation, Ollama installation/model pull and mission DAG bootstrap. Its specialist/evidence/reviewer execution stage remained in progress at this checkpoint.
- Pilot uses preserved checkpoint 43615137961 / artifact 14121666814 and open-weight `qwen2.5:3b` served by Ollama at `127.0.0.1:11434`. It is limited to two priority candidates, six specialist roles per candidate, two evidence-validation tasks and two independent reviews.
- Model context is bounded to five files and 18,000 characters per task, with 600-second timeout. This is a quality/throughput experiment, not an approved full-scale setting.
- CI for the Agent Form bridge and model-timeout injection passed Python 3.11/3.12/3.13 in run [43615235086](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43615235086). A previous fake-provider compatibility failure was corrected before the current pilot.
- **Do not scale semantic processing** until the pilot artifact is inspected for structured-output validity, accepted/rejected evidence, specialist disagreement, reviewer challenges, unknowns, elapsed time and runner resource use. A green workflow alone is not proof of research quality.
- **Audit counters remain separate:** 316 source-captured does not mean 316 semantically audited. No new semantic audit is counted until the model reports, evidence-gate outputs and independent reviews are inspected. Existing manual dossiers remain a separate sample.

## Latest verified batch-preparation checkpoint

- Original discovery batch-data commit: `8448711d734978d5c0e793793feccf08dad29747`; worker implementation merge: `089e215bac99a60ba2b2e2c7b33c8f9e370a21b3`.
- Preparation workflow run [43603644216](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43603644216) completed successfully; associated code CI run [43603644293](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43603644293) passed Python 3.11/3.12/3.13.
- All 7,901 discovery rows were stream-imported and exported to `research_runs/audit-batches/43600488013/` as **80 JSONL batches**, maximum 100 records each.
- Batch verification: 7,901 unique canonical repository names; 7,901 unique GitHub repository IDs; candidate indexes 0–7,900 contiguous; all 80 batch SHA-256 hashes verified.
- Manifest SHA-256: `45014ead9e61098cef320704131752f63f2a4ebe392947bd8204fd1a34ad43fd`; source report SHA-256: `d99ebcdcbd1739536ba987e51ffe2a5c06610094e24b4603c89d3f5f32db3002`.
- This is metadata import and queue preparation only. The later bounded pilot source-captured **10/7,901** candidates; **7,891 remain pending**. Semantic audit and independent review of this 7,901-row queue remain **0/7,901**. Existing five manual dossiers remain a separate sample. No candidate code was executed.
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
