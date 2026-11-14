# Research Changelog

## 2026-11-14 (autonomous hosted continuation)

- Replaced the WSL-only primary continuation dependency with a GitHub-hosted self-chaining source-capture workflow: `.github/workflows/autonomous-source-capture.yml`.
- Added a deterministic cross-run checkpoint restore verifier: `scripts/restore_source_capture_checkpoint.py`. It validates the immutable discovery manifest, SQLite integrity and queue accounting, report/candidate identity, commit/tree pins, execution-safety flags and captured Git blob SHA-1 references before restoring the state into dedicated DB/vault paths.
- Added regression tests for canonical Git blob hashing and artifact path traversal. CI initially caught a double-escaped null-byte literal; the helper was corrected to use Git's exact `blob <length>\\0<content>` framing. Latest CI run 43613456152 passed on Python 3.11/3.12/3.13 with 70 tests.
- Added an autonomous workflow-dispatch chain using repository-scoped `GITHUB_TOKEN` with `actions:write`. Each hosted run restores the preceding artifact, performs 12 bounded read-only captures at concurrency 2, writes a checkpoint, uploads SQLite/source-vault/reports and dispatches the next run while pending work remains.
- Started the first hosted continuation from the existing 10-candidate pilot through marker commit `975dd04e80878a7ee36c83a079027eaa1a4914a8`. Workflow run [43613572504](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43613572504) passed checkout, runtime installation and prior-checkpoint download/restore; source capture was still running at the time this entry was written.
- The automation is not yet declared complete or fully proven: first-batch queue counts, artifact upload and successor workflow dispatch must be verified from live Actions outputs. The last fully verified queue remains 10 captured / 7,891 pending / 0 leased / 0 failed.
- The 7,901-candidate semantic classification, security/economics specialist analysis, evidence auditor and independent reviewer remain separate gates. Source capture is not an audit. Candidate code execution, wallets, keys, signing, deployment and live transactions remain prohibited.
- User-side WSL commands, artifact download and personal GitHub token are no longer required for the hosted deterministic source-capture path.

## 2026-11-14
- Created the dedicated repository and verified GitHub connector admin/push access.
- Phase A deterministic Python engine, SQLite evidence store, GitHub acquisition, commit/tree pinning, bounded source capture, Git blob verification and lexical signal extraction are merged to main.
- CI workflow is read-only; discovery workflow has contents: write only to persist its own generated report. External Actions are pinned by full commit SHA.
- Local Phase A validation previously recorded: compileall PASS; 26/26 local tests PASS; workflow YAML parsed; CLI help/status PASS. Remote CI matrix passed on Python 3.11, 3.12 and 3.13 on prior main commits.
- Saved first manual read-only GitHub discovery snapshot at research_runs/manual/2026-11-14-discovery-1052Z.json. Four queries returned 39 raw results and 38 unique repositories. This was performed through the connected GitHub search action and persisted directly; it was not a scheduled Actions execution.
- Search metadata exposed by the connector did not include descriptions, pushed_at, stars, language or license; the snapshot leaves those fields unasserted.
- Pinned MELD Labs candidate at commit 74653447a0ff9014f2e022d6778b442182f9841a. Added source audit at research/candidate-audits/MELD-labs__meld-flashloan-liquidation-bot-public.md.
- Recorded two source-level findings: MELD-CALLBACK-AUTH-001 (callback caller/initiator not authenticated) and MELD-ACCOUNTING-002 (minimum-output expression mixes collateral-token and debt-token raw units).
- Added both findings to SECURITY_FINDINGS.json and EVIDENCE_REGISTER.csv with exact source blob SHA and line ranges.
- Findings are not claims of a reproduced live exploit. No candidate code was executed; no wallet, signer, deployment or live trading used.
- Latest evidence-register commit CI run 43587464686 was queued at the last checkpoint; verify before declaring the latest main state green.

- Added a second candidate audit: Power-Howdy/flashloan-bot-ArbitrageAndLiquidation at commit 025eb602ddd96c3cc8479fb0fbd00cde13e198b6. Grade D: callback integration absent, zero-address placeholders, amountOutMin=0 and no profit invariant.
- Added a third candidate audit: tundefund0-gif/morpho-liquidator at commit 7cbfa8abc8f0c75b38f75ac4b0878ffe883645e9. Grade C reference only; source contains private-key signing, raw transaction broadcast and automatic deployment paths, so it was not executed. Flash callback does not enforce balance-delta profit above pre-loan balance and failed quote falls back to minOut=1.
- Added all three candidate audits and seven total candidate findings/evidence rows to the matrix, SECURITY_FINDINGS.json and EVIDENCE_REGISTER.csv.
- Candidate execution was deliberately not performed. The research project did not supply keys, deploy contracts, broadcast transactions or interact with wallets.

- Implemented bounded recovery for GitHub recursive tree truncation. The engine now falls back to non-recursive directory traversal, bounded by 50,000 tree entries and 10,000 directories; it preserves an incomplete status if any subtree is truncated or a cap is reached.
- Added tree-recovery metadata to inspection results and explicit coverage limitations.
- Added tests for successful recovery, directory limit and truncated subtree handling.
- GitHub Actions run 43587812556 passed on Python 3.11, 3.12 and 3.13. All 7 repository tests and compileall passed.

- Added a form-driven Research Mission interface, JSON Schema, product constitution and autonomous research lifecycle contract. The form is now the primary mission intake, not a secondary utility.
- Implemented local-only mission intake API and durable SQLite queue. `POST /missions` validates and stores missions; the form can submit to the local service. The API binds to 127.0.0.1:8765.
- Mission validation rejects attempts to enable candidate-code execution, wallet access, transaction signing, deployment, live trading or paid services. Independent review is mandatory.
- First API integration CI run exposed SQLite thread-affinity failure. Fixed by using a thread-safe connection with a lock around database operations.
- Final GitHub Actions run 43588460762 passed on Python 3.11, 3.12 and 3.13: 29/29 tests passed and compileall passed.
- Explicit status: form + validated durable queue are implemented; live LangGraph agent execution is not yet connected. Next gate is dependency-aware mission DAG, checkpointed worker runtime, specialist nodes, independent review and automatic continuation.


## 2026-11-14 — autonomous graph and source-aware evidence hardening
- Fixed the LangGraph control-flow graph so the worker invokes the configured local semantic specialist/evidence/reviewer stage after source capture. Added a graph regression test asserting ordered execution and persisted semantic-stage output.
- Added bounded source-aware specialist context: source files are loaded from the content-addressed local vault, Git blob SHA-1 is recomputed before use, line-numbered excerpts are bounded, and excerpt SHA-256 is recorded.
- Extended evidence validation to include the candidate-purpose report; it no longer skips purpose classification provenance.
- Changed independent review context to include actual completed candidate-purpose/specialist report contents rather than only result paths. Report role and inspected commit provenance are checked.
- CI run 43598988641 passed on Python 3.11, 3.12 and 3.13 at commit f0fab8beafe01c1a8ce18c542c70a8372647052e.
- Still not claimed: full fake-provider mission lifecycle, live local-model run, complete 11-family live discovery, dossier/synthesis execution or multi-batch autonomous continuation.


## 2026-11-14 — live 11-family discovery and candidate audits
- GitHub Actions run 43600488013 completed successfully with all 11 taxonomy families and 38 configured query templates.
- Discovery summary: 7,901 unique candidates; 28 queries complete; 10 incomplete; `coverage_complete=false`. No global completeness claim is made.
- Report: `research_runs/mission/2026-11-14/discovery-43600488013-1.json`; artifact commit `231f47f0ada252a921a065da935720873f397bef`; blob SHA `3f126f4cfa4e163dbe95cb7ffb7f2528180254d5`.
- Merged source-pinned audit of `Lumetra-Labs/morpho-liquidation-bot` at `471c7adac62aaf58e5046a395ba96338dc82278a` (tree `20487e3b1e7621525f0521b4832c4a3dc75b4c3c`), grade C. Reviewed primary path is Morpho native liquidation callback plus 1inch swap, not flash-loan-funded. Source findings cover shared borrower cursor, stale-index fallback, theoretical P&L, ignored transaction result and full selected-token balance transfer. No candidate execution.
- Merged source-pinned audit of `0xnavarro/Aave-Liquiditor` at `9197ee3002d7d9b35e9c2da324128a38f7569038` (tree `14de2312e96c369bcc52c9bae96215051aea22b4`), grade D. Findings cover wrong Pool/Provider pointer, missing callback authentication, missing collateral-to-debt swap, missing B0 profit floor, wrong collateral bitmap bit, faulty profit arithmetic/base-unit assumptions, capped tx-origin scanning, environment mismatch and absent monitor-to-executor wiring. Official Aave references are linked in the dossier. No candidate execution.
- Candidate dossier count is now five. New source findings are pending independent review; they have not been promoted to the accepted findings set.
- Main CI run 43601777341 passed on Python 3.11, 3.12 and 3.13 after the Aave dossier merge.
- Remaining: stream-import the 7,901 candidates into bounded durable batches; perform source capture, purpose classification, review and synthesis; run real local inference only through an explicitly configured free loopback endpoint.


## 2026-11-14 — discovery queue import and hashed audit batches
- Added `.github/workflows/candidate-batch-preparation.yml` for a bounded, retry-safe import/export job. It validates the source snapshot, runs the test suite, stream-imports the discovery report into SQLite, exports JSONL batches and verifies batch SHA-256, canonical identities, unique repository IDs and candidate-index continuity before committing the output.
- Updated `research-discovery.yml` so future live discovery runs generate their own SQLite import and hashed audit batches within the same run.
- Preparation workflow run 43603644216 completed successfully; CI run 43603644293 passed on Python 3.11, 3.12 and 3.13 at code commit d596ae0d69bc625ad952e2f164ea8eb43e94044d.
- Pinned live report 43600488013 was imported: 7,901 candidates, 7,901 unique canonical names and IDs, and 80 JSONL packets of up to 100 candidates, persisted under `research_runs/audit-batches/43600488013/` in data commit 8448711d734978d5c0e793793feccf08dad29747.
- All 80 batch SHA-256 hashes and indexes 0–7,900 were verified. Manifest SHA-256 `45014ead9e61098cef320704131752f63f2a4ebe392947bd8204fd1a34ad43fd`; source report SHA-256 `d99ebcdcbd1739536ba987e51ffe2a5c06610094e24b4603c89d3f5f32db3002`.
- Import is not audit: all 7,901 rows remain pending commit-pinned source capture. Existing five source dossiers remain a separate prior sample. No candidate code was executed.


## 2026-11-14 — four priority packet candidates source-inspected
- Pinned exact repository commits, trees and inspected file blobs for four candidates in immutable packet 0001.
- Added four provisional dossiers: `0xTona/liquidator-bot` (C), `0xFantomMenace/Aave-Liquidation-Bot` (C, separately assesses HyperLend and Granary subprojects), `0xFantomMenace/Compound-Liquidation-Bot` (D), and `0xGusMcCrae/aave-liquidator-bot` (D).
- Findings include gross-only profit gating and narrow borrower history in Tona; Granary callback authentication/unchecked router call versus better HyperLend callback checks; Compound array indexing/pool configuration/zero minimum output and inactive test file; Gus XOR allowance expression (257, not max), unauthenticated callback and unchecked low-level call.
- All four dossiers are provisional and await independent review. Manual source inspection is separate from the automated 7,901-candidate queue, whose source-capture counter remains 0/7,901. No candidate code was executed.


## 2026-11-14 — Twyne Morpho flash-loan liquidator inspected
- Added a provisional B-grade dossier for `0xTwyne/twyne-liquidation-bot`, pinned to commit `568a6308adf82952a156b6374ae264643a0c4fc2` and tree `7a24b296c6c0947d95c2a6f54921a33fa4b5575f`.
- Reviewed both Euler/Twyne and Aave-vault liquidators, Morpho callback authentication, explicit realized minimum-profit gate, approval reset, router-call error propagation and fork-based Foundry test sources.
- Diligence notes cover public trigger/owner-directed proceeds, caller-provided router calldata under owner-configured router allowance, temporary max approvals and zero-debt branch semantics.
- Five manual candidates now have source-pinned dossiers, all awaiting independent review. Automated 7,901-candidate queue source-capture counter remains 0/7,901. No candidate code executed.


## 2026-11-14 — resumable manifest-driven source-capture worker merged

- Added a standalone `flashloan-source-capture-worker` backed by a durable SQLite queue for the immutable discovery manifest and 80 JSONL batches.
- The importer verifies the manifest type/run ID, every batch SHA-256, contiguous candidate indexes, canonical repository identity, unique GitHub repository IDs and batch counts before writing queue records.
- The queue persists per-candidate pending/leased/captured/failed states, bounded three-attempt retries, 60-minute expiring leases and crash/lease recovery. Existing runs are idempotent and must match the same manifest SHA-256.
- Worker processes direct flash-loan/provider/liquidation candidates first, then adjacent DeFi families, then remaining taxonomy families. It uses bounded concurrency and the existing read-only `ResearchPipeline.inspect` to pin current default-branch commit/tree and verify Git blob SHAs.
- Per-candidate capture reports are written atomically; raw verified source blobs are stored in the local content-addressed vault. Default first-pass capture limit is 30 source files per repository with configured blob-size and tree traversal limits disclosed as coverage constraints.
- Added regression tests for manifest hash tampering, priority order, idempotent continuation, transient retry and expired-lease recovery.
- PR [#7](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/7) merged to main at `089e215bac99a60ba2b2e2c7b33c8f9e370a21b3`.
- CI run [43606380880](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43606380880) passed compile and test jobs on Python 3.11, 3.12 and 3.13.
- **Execution distinction:** the worker implementation is merged, but it has not yet been run against the live 7,901-candidate manifest. Automated source capture remains **0/7,901** until a real persistent local/WSL run records captures. The five manual source-inspected dossiers remain a separate sample awaiting independent review.
- No candidate repository code was executed; no wallet, transaction signing, deployment or live trading was used.


## 2026-11-14 — 10-repository real source-capture pilot verified

- Added bounded Actions workflow `.github/workflows/source-capture-pilot.yml` with a hard cap of 10 candidates, parallelism <=2 and `contents: read` permissions. Marker-triggered run [43607072905](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43607072905) completed successfully.
- **Real queue result:** 10 attempted, 10 captured, zero failed; 7,891 pending and zero leased out of the original 7,901.
- Ten repositories were pinned to current default-branch commit and tree SHAs, with full tree inventory and one atomic inspection report per candidate. 182 source-file references were captured across nine repositories; 173 unique Git blobs were persisted in the content-addressed vault and all 182 blob SHA-1 references independently verified, with zero missing or mismatched blobs.
- Scope limitations: four repositories hit the 30-source-file cap; one repository had zero eligible source files under the source-extension allowlist. Six report flags say complete within configured scope, but only five of those six contain source files. Signal counts are lexical leads, not semantic findings.
- Artifact [14118419543](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43607072905/artifacts/14118419543), 1,509,274 bytes, SHA-256 `092235cf3f11920d65ccbbe4e6412f5b325c2158c2d698f61da947767400c178`, contains the pilot SQLite state, 10 reports and verified source vault.
- Persisted sanitized verification: `research_runs/source-capture-pilots/43607072905/verification.json`; commit `0cc64139f0476bb372f4446fc45fc301cc9522e0`.
- Updated `PROJECT_STATE.json` to 10 automated source captures, 7,891 pending. Semantic audit remains 0/7,901. The five manually inspected candidates remain separate.

## 2026-11-14 — source-capture priority and API quota hardening

- PR [#8](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/8) merged: exact taxonomy family `flash_loan_liquidation_combo` now receives highest priority; taxonomy ID mapping covers all eleven configured families; empty repositories with null discovery-time default branch metadata are not rejected before live metadata refetch.
- PR [#9](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/9) merged: primary GitHub API quota handling waits through `X-RateLimit-Reset`; secondary limits respect `Retry-After` up to one hour. Fake-opener regression tests cover 1,001-second primary reset and 120-second secondary wait.
- Both PRs passed CI on Python 3.11/3.12/3.13. These fixes protect the multi-hour/multi-day read-only source-capture run from repeatedly exhausting per-candidate retries before API quota reset.

## 2026-11-14 — persistent WSL restore/resume path merged

- PR [#10](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/10) merged with `scripts/resume_source_capture.sh`, README instructions and JSON progress output after every worker cycle.
- Restore helper verifies exact pilot ZIP SHA-256, SQLite integrity, canonical manifest SHA-256, ten report identity/commit/tree pins and each of 182 Git blob SHA-1 references before restore.
- Pilot state restores to dedicated `data/source-capture-pilot.sqlite3` and `data/source-capture-pilot-vault/`; it never overwrites existing `data/research.sqlite3` or `data/snapshots/`. It resumes the same run ID with 10 completed and 7,891 pending.
- GitHub CI validates the Bash helper syntax, compiles source and runs tests on Python 3.11/3.12/3.13. The long queue has **not** yet been resumed locally; no claim is made that 7,891 candidates have completed.
- Required WSL operation: download artifact 14118419543 and run `bash scripts/resume_source_capture.sh <pilot-zip-path>` from the repository root with a read-only GitHub token exported in the shell.
- No candidate code was executed. Semantic specialist analysis, evidence acceptance, independent review and dossier synthesis remain pending.
