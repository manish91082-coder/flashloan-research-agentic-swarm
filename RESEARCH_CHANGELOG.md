# Research Changelog

## 2026-11-15 (PR #15 source telemetry; corrected 942 checkpoint accounting)

- PR [#15](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/15) merged at `a54019a4f6e95cd657e94b79cc3a0712be2bc976`. Source capture now emits structured batch-start and per-candidate completion events and logs GitHub API 403/429/5xx/network retry attempts, retry headers and wait durations. No authorization values or tokens are logged.
- PR #15 pre-merge tests and main CI [43684603884](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43684603884) passed on Python 3.11/3.12/3.13, including source capture, GitHub API telemetry, compileall and WSL resume-helper syntax.
- Reopened and queried the exact durable source artifact [14148553489](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681894031): its `source-capture-cycle.json` contains 12 result records, **11 captured and 1 failed**, while SQLite and checkpoint counters agree at 942 captured / 6,947 pending / 0 leased / 12 failed. An earlier prose summary incorrectly described the batch as 10 captured / 2 failed; this is corrected here and in the canonical project state.
- Source continuation [43681954178](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681954178) restored the 942 checkpoint and remains in the next capture step. No successor artifact or new queue total is available at this checkpoint. It predates PR #15, so new progress events will become visible on future source-capture runs.
- Fresh isolated Agent Form r2 pilot [43683037797](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43683037797) remains in serialized specialist/evidence/reviewer execution after successful restore, runtime/model installation and fresh DAG bootstrap. The chosen seed candidates have 11 and 7 pinned lexical source signals respectively; output reports and review decisions are not yet artifact-verified. Semantic audit count remains unchanged.


## 2026-11-15 (PR #14 role-exclusive model schema; source checkpoint 942; Agent Form r2)

- Durable source-capture checkpoint [43681894031](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681894031), artifact **14148553489**, SHA-256 `dfb9b9a57c60e7ea708d5d85d93df416f251c889343ec508a8f2be27cef2e1a`: **942/7,901 captured; 6,947 pending; 0 leased; 12 failed**. Within configured source scope, 687 captures are complete and 255 have coverage limits. The last 12-item batch captured 11 and recorded 1 empty-repository HTTP 409 failure.
- Source continuation [43681954178](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681954178) restored the immutable run/artifact pair and was processing the next bounded 12-item batch at the checkpoint. The chain uses direct artifact-ID restore, bounded API rate-limit/5xx retry, durable upload and dispatch of the successor artifact ID.
- Fresh isolated Agent Form r1 pilot [43681829089](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681829089) restored the source checkpoint, installed the Agent Form runtime and Ollama qwen2.5:3b, and initialized a fresh SQLite mission. Both candidate-purpose tasks then failed closed because the shared output schema exposed reviewer-only values to non-reviewer model tasks. Downstream evidence and reviewer stages were blocked; no semantic audit count was incremented.
- PR [#14](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/14) merged at `08b9f6d1f129298f7faf42b50529cbc6e14f27b0`. Specialist model schemas now contain only seven common fields. Reviewer-only decision/disagreement fields are not sent to specialist tasks and are injected deterministically after successful validation. Only independent reviewer tasks receive explicit decision/disagreement fields; `not_applicable` is excluded from reviewer decisions.
- PR #14 CI [43682983408](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43682983408) passed on Python 3.11/3.12/3.13. Main merge CI [43683037814](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43683037814) also passed on all three versions.
- Fresh isolated r2 pilot [43683037797](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43683037797) was triggered automatically by the merge. It uses mission `flashloan-agent-form-pilot-20261115-r2`, a fresh SQLite database and artifact root, and the preserved seed 43615137961 / artifact 14121666814. At the last check, immutable restore, Agent Form runtime, Ollama qwen2.5:3b and the fresh DAG bootstrap had succeeded; serialized specialist/evidence/reviewer execution was in progress.
- No r2 quality pass is claimed until both purpose reports, 12 specialist reports, both positive evidence gates, both independent-review decisions and the complete task/artifact ledger are inspected. Candidate dossier generation and reviewer-disagreement reconciliation remain gated on this acceptance.
- No candidate code execution, wallet access, signing, deployment, live trading, cloud inference or paid inference.

## 2026-11-15 (PR #13 quality gates merged; source checkpoint 920; fresh isolated pilot started)

- Latest inspected source checkpoint: workflow [43630157644](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43630157644), artifact **14127627316**, SHA-256 `31797dc0cd3f80813cd34534f0ca696e73b321e237f407e2a9866afb0f207b75`. The SQLite queue and checkpoint record agree: **920/7,901 captured, 6,971 pending, 0 leased, 10 terminal failures**; 673 complete within configured source scope and 247 coverage-limited. The last bounded cycle captured 12/12. The 10 failures are empty Git repositories (HTTP 409), not security findings.
- Follow-up source run [43630236847](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43630236847) failed before candidate capture when the artifact endpoint returned HTTP 502 for artifact 14127627316. No candidate source-inspection failure was recorded by that run.
- PR [#13](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/13) merged at `778f82b95d382249e600eee933841a71697cf9b0`. It adds exact signal evidence IDs, finding-to-evidence linkage, rejection of every out-of-catalog evidence ID, zero-evidence rejection, unique purpose/protocol report identities, strict task/report provenance for all seven specialist reports, serialized CPU inference and bounded retryable timeouts. It also makes source continuation use immutable run/artifact IDs and retry transient 5xx plus rate limits.
- PR #13 CI [43681735442](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681735442) passed on Python 3.11/3.12/3.13. Main merge CI [43681828999](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681828999) was running at the latest status check.
- Autonomous source-capture continuation [43681829011](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681829011) restored run 43630157644 / artifact 14127627316 and began the next 12-repository batch.
- The prior semantic pilot [43627944086](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43627944086) was rejected: two specialist tasks timed out, only one candidate completed the downstream gates, and reviewed reports contained zero accepted pinned-source evidence. No semantic audit counter was incremented.
- Fresh isolated Agent Form pilot [43681829089](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681829089) started on merge. It uses fresh mission ID `flashloan-agent-form-pilot-20261115`, a separate SQLite database, immutable seed run 43615137961 / artifact 14121666814, local loopback qwen2.5:3b, 1,200-second request timeout and reduced source context. Last observed at local Ollama runtime installation; no pass has yet been asserted.
- Candidate source capture, specialist inference, evidence validation, independent review and candidate dossier acceptance remain distinct metrics. No source-capture count is an audit count. No candidate code is executed; wallet access, signing, deployment, live trading, cloud inference and paid inference remain disabled.
- README.md, NEXT_ACTIONS.md and PROJECT_STATE.json were synchronized to the 920-source checkpoint and the PR #13 / fresh-pilot state.


## 2026-11-14 (Agent Form structured-output repair, artifact restore hardening and 896-source checkpoint)

- PR [#11](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/11) merged the strict specialist JSON Schema contract. The local provider now transmits the exact required schema and prompt contract, rejects missing or unexpected top-level keys, and retains the loopback-only/no-cloud policy. Its regression matrix passed Python 3.11/3.12/3.13 (CI run 43626544380; merge commit cc22f5e408927353d6f31991d34827efa8f476d0).
- The next pilot attempt [43626720183](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43626720183) did not reach inference: `gh run download` hit GitHub installation API rate limit HTTP 403 while listing the preserved seed checkpoint artifact.
- PR [#12](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/12) merged direct retrieval by immutable artifact ID, bounded retry honoring Retry-After/X-RateLimit-Reset, ZIP CRC checking, safe extraction and cross-host Authorization stripping. CI passed Python 3.11/3.12/3.13 (run 43627789274; merge commit 84dc4e423d5884cb170500aec3961e22345d749f).
- Third bounded pilot [43627944086](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43627944086) was triggered from preserved seed run 43615137961 / artifact 14121666814. At the last check it remained in the checkpoint-download step; model installation and semantic inference had not yet started. No semantic audit count is added from this attempt until final artifacts are inspected.
- Latest inspected source capture [43626548828](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43626548828), artifact 14126596143: 896/7,901 captured; 6,995 pending; 0 leased; 10 terminal empty-Git-repository HTTP 409 failures. Of captured repositories, 656 are complete within configured source scope and 240 have explicit coverage limitations. Latest 12-repository cycle captured 12/12.
- Source capture, semantic specialist reports, structural evidence validation, independent reviewer acceptance and final candidate dossier remain separate state dimensions. The 10 empty-repository failures are source-availability records, not security findings. Candidate code execution, wallet access, signing, deployment, live trading, paid inference and cloud inference remain disabled.
- README.md and NEXT_ACTIONS.md were synchronized to this checkpoint. The primary source-capture path remains GitHub-hosted and self-chaining; WSL/local restore is fallback only.


## 2026-11-14 (Agent Form pilot failure audit and structured-output repair)

- Inspected the complete evidence artifact for semantic-pilot run [43615341905](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43615341905), including the task ledger and pinned source inspection reports for both pilot candidates.
- The run completed checkpoint restore, Agent Form runtime installation, Ollama installation/model pull and mission-DAG bootstrap. The semantic job failed: both `candidate_purpose` tasks rejected the model reply because the seven required report keys were absent. Evidence validation claimed 0 tasks; independent review claimed 0 tasks; both remain uncompleted.
- Root cause in the local provider contract: it requested JSON mode but did not transmit the required field schema or explain the required key contract to the model. The failure is a structured-output contract failure, not a source-capture failure.
- Repair branch `fix/agent-form-json-output-contract` adds a strict JSON Schema response format, places the same schema and mandatory field rules in the system prompt, rejects unexpected top-level keys, and adds regression tests. The repair remains unaccepted until CI and a fresh live local-model pilot pass.
- No semantic audit count has been incremented. Source capture, semantic specialist output, evidence validation, independent review and dossier completion remain separate counters.
- No candidate code execution, wallet access, signing, deployment, live trading, cloud inference or paid model use.

## 2026-11-14 (source checkpoint 316; semantic pilot result pending audit)

- Verified source-capture workflow [43615449485](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43615449485), artifact 14122085911. Queue: 7,901 total / 316 captured / 7,583 pending / 0 leased / 2 failed. Coverage: 236 complete within configured source scope; 80 with limitations.
- Source-capture chain continues to self-dispatch; empty Git repository failures remain explicitly separated from security findings.
- Agent Form local-model pilot [43615341905](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43615341905) completed checkpoint restoration, Agent Form runtime installation, Ollama model installation and mission DAG bootstrap. Specialist/evidence/reviewer execution was later found to have failed; see the audit entry above.
- The pilot remains restricted to two candidates using qwen2.5:3b via loopback-only Ollama. No semantic audit count is incremented until outputs and independent-review results are inspected.
- No candidate code execution, wallet access, signing, deployment, live trading, cloud inference or paid model use.


## 2026-11-14 (source checkpoint 316; semantic pilot still executing)

- Verified source-capture workflow [43615449485](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43615449485), artifact 14122085911. Queue: 7,901 total / 316 captured / 7,583 pending / 0 leased / 2 failed. Coverage: 236 complete within configured source scope; 80 with limitations.
- Source-capture chain continues to self-dispatch; empty Git repository failures remain explicitly separated from security findings.
- Agent Form local-model pilot [43615341905](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43615341905) completed checkpoint restoration, Agent Form runtime installation, Ollama model installation and mission DAG bootstrap. Specialist/evidence/reviewer inference remained in progress at this checkpoint.
- The pilot remains restricted to two candidates using qwen2.5:3b via loopback-only Ollama. No semantic audit count is incremented until outputs and independent-review results are inspected.
- No candidate code execution, wallet access, signing, deployment, live trading, cloud inference or paid model use.

## 2026-11-14 (source checkpoint 304; Agent Form pilot executing)

- Verified source-capture workflow [43615383358](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43615383358), artifact 14122475274 (8,510,984 bytes). Queue: 7,901 total / 304 captured / 7,595 pending / 0 leased / 2 failed. Source coverage: 226 complete within configured scope; 78 with limitations.
- The source-capture chain remains active and self-dispatching. The two failures remain empty repositories (HTTP 409), not security findings.
- Agent Form semantic pilot [43615341905](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43615341905) passed source checkpoint restore, Agent Form runtime installation, Ollama installation/model pull and task-DAG bootstrap. Specialist, evidence and independent-review execution was in progress at this checkpoint.
- The pilot uses the preserved checkpoint 43615137961 / artifact 14121666814, model qwen2.5:3b, CPU-only local inference served on 127.0.0.1:11434, context limit five files / 18,000 characters and 600-second model timeout.
- The pilot scope is exactly two high-priority candidates and requires two purpose tasks, six specialist roles per candidate, two evidence gates and two independent reviews. No candidate is counted semantically audited until its final artifact is inspected.
- The source queue and semantic pilot run concurrently. Latest source checkpoint is 304 captured; no semantic audit count has been incremented.
- No candidate code execution, wallet access, signing, deployment, live trading, cloud inference or paid model use.

## 2026-11-14 (Agent Form semantic pilot launched)

- Latest inspected source-capture checkpoint: [43615137961](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43615137961), artifact 14121666814. Queue: 7,901 total / 268 captured / 7,631 pending / 0 leased / 2 failed. Coverage: 203 complete within configured source scope; 65 with limitations.
- Two failed rows are empty repositories returning GitHub HTTP 409: ADMac/flashloan and Alejo1156/FLASHLOAN. They are unavailable-source records, not security findings.
- Added `.github/workflows/agentic-semantic-pilot.yml`. It downloads a preserved verified source-capture artifact, restores and validates it, installs the Agent Form/LangGraph runtime, then installs Ollama and pulls qwen2.5:3b for CPU inference served only on loopback 127.0.0.1:11434.
- Added a one-time pilot seed marker for run 43615137961 and updated checkpoint-retirement logic so the source-capture chain preserves this designated artifact until the semantic pilot consumes it.
- Triggered Agent Form pilot workflow [43615341905](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43615341905). At checkpoint time, restore succeeded and Agent Form runtime installation was in progress; no semantic output had yet been verified.
- Pilot batch size: 2 repositories, selected by direct flash-loan/liquidation taxonomy priority. The workflow requires two purpose tasks, six specialist roles per repository, two evidence-validation tasks and two independent reviews. It records model manifest, task ledger and elapsed time. The pilot fails closed on task failures or missing gates.
- Model context is bounded to five files and 18,000 characters per task, with 600-second request timeout. This is a controlled quality/throughput experiment; full-scale semantic automation remains gated on the resulting evidence.
- A fake-provider test seam initially failed when timeout configuration was injected as a constructor argument. The implementation now applies timeout after provider construction, preserving the existing injectable provider contract. Latest CI [43615235086](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43615235086) passed on Python 3.11/3.12/3.13.
- No semantic audit count is increased until the pilot reports are inspected. Candidate code execution, wallet access, transaction signing, deployment, live trading, cloud inference and paid model use remain disabled.

## 2026-11-14 (Agent Form bridge and 196-candidate source checkpoint)

- Latest inspected source checkpoint: workflow [43614692895](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43614692895), artifact 14121229184. The artifact's queue reports 196 captured / 7,703 pending / 0 leased / 2 failed out of 7,901.
- Captured coverage: 148 complete within configured source scope; 48 have source-scope limitations. The 2 failed rows are empty Git repositories (HTTP 409): ADMac/flashloan and Alejo1156/FLASHLOAN. They are source availability gaps, not code findings.
- Added `scripts/initialize_agentic_capture_mission.py`, which maps verified source-capture reports into the Agent Form schema, mission queue and task DAG. It verifies commit/tree identities and all source Git blob hashes before creating inspection inputs. It does not re-run discovery or treat lexical signals as audit findings.
- Candidate selection for the bounded Agent Form pilot prioritizes direct flash-loan/liquidation intersections, then flash-loan core, liquidation, provider APIs, lending and security/accounting families. Lexical signal counts are scheduling hints only.
- Added tests for mission payload schema compatibility, blob verification, tamper rejection and priority ordering. CI passed on Python 3.11/3.12/3.13 (runs 43614561997 and 43614586467).
- Added terminal handling for GitHub 409 empty repositories to avoid three futile retries. Regression test and CI run 43614709576 passed across Python 3.11/3.12/3.13.
- The Agent Form DAG bridge is implemented, but hosted local-model inference has not yet run. The loopback-only provider rejects cloud endpoints. Next gate: run a bounded open-weight model pilot inside a GitHub-hosted runner using a loopback endpoint, validate outputs against pinned evidence, and only then scale specialist/reviewer processing.
- Source capture, semantic specialist analysis, evidence validation and independent review remain distinct counters. No candidate code execution, wallet access, signing, deployment or live transactions.

## 2026-11-14 (verified continuation checkpoint: 118 source captures)

- Verified that the GitHub-hosted source-capture chain self-dispatches successfully across successive workflow runs; latest completed run at this checkpoint: [43614195040](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43614195040).
- Downloaded and inspected artifact 14121562264 (3,965,756 bytes). Its restore-verification record confirms 106 prior report identities and 1,343 Git blob references (1,261 unique blobs) were revalidated before continuation.
- Its cycle captured 12 additional candidates. Queue counters now read 7,901 total / 118 captured / 7,783 pending / 0 leased / 0 failed. Source-scope coverage: 86 complete within configured limits; 32 with coverage limitations.
- Successor run [43614274364](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43614274364) was observed in progress. Its output must be checked before the next counter increment.
- Updated PROJECT_STATE.json and NEXT_ACTIONS.md to remove WSL/manual commands from the primary path and to record the actual Agent Form integration gate.
- Agent Form is not yet the active semantic runtime for the captured queue: HTML intake + local SQLite API + LangGraph task DAG + local-only model adapter exist, but the adapter explicitly rejects cloud inference. Next implementation is a deterministic bridge from verified capture reports to the form-defined task DAG, followed by a bounded open-weight model inference pilot served on loopback inside GitHub-hosted runners.
- No semantic audits or independent reviews are inferred from source capture. Existing manually reviewed dossiers remain a separate sample. Candidate code execution remains zero.

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


## 2026-11-15 — source telemetry stream contract preserved

- PR [#16](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/16) merged at `e9ae3d67a3b8d0222d44e940f9a54c77f10d1ed7`.
- Forensic integration review identified that PR #15's new progress events shared stdout with the CLI summary, while the Actions workflow parses `reports/source-capture-cycle.json` as one JSON document. This would have broken the future checkpoint step after candidate capture.
- Moved source batch-start, per-candidate completion, and GitHub API retry/backoff events to stderr. The final CLI summary remains the sole JSON document on stdout.
- Regression tests verify the source worker emits progress only on stderr and that GitHub retry telemetry is captured from stderr.
- PR CI passed Python 3.11/3.12/3.13. Main merge CI [43685837776](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43685837776) is in progress.
- Active source run 43681954178 and Agent Form r2 pilot 43683037797 predate this merge and remain separately in progress at the latest check. The last durable source checkpoint remains 942/7,901; no semantic audit has been accepted or counted.


## 2026-11-15 — source checkpoint 1,055 and Agent Form r4 launch

- Independently downloaded and inspected source artifact 14151925155 from run 43688683947. Its checkpoint JSON and SQLite queue agree: 1,055 captured, 6,831 pending, 0 leased, 15 failed; coverage split is 762 complete within configured scope and 293 coverage-limited.
- The 12-item cycle in that artifact contained 10 successful captures and two HTTP 404 Git-tree lookups left pending/retryable. Existing 15 failed records remain empty-Git-repository HTTP 409 source-availability cases.
- Successor workflow 43688785565 restored the exact parent checkpoint and was in its next 12-candidate capture step at the latest verification. No successor artifact/count is claimed until its checkpoint upload is inspected.
- r3 semantic pilot 43687345074 was not accepted: qwen2.5:1.5b returned malformed OpenAI-compatible JSON for both candidate-purpose requests. Its artifact 14150952579 confirms that no specialist, evidence or reviewer gate passed.
- PR #21 merged at 4d5d403121ec48c541f0fe646d76f7e90910bc36. It returns inference to qwen2.5:3b, adds bounded malformed-output diagnostics and fenced/pre-parsed JSON handling, and retries malformed/truncated JSON/timeouts only within the existing attempt budget. CI 43688699274 passed on Python 3.11/3.12/3.13.
- Fresh r4 Agent Form pilot 43688699311 was launched with a new database and mission ID, the immutable 268-candidate seed, qwen2.5:3b, reduced source context and a 1,200-token output cap. Restore/runtime/bootstrap passed; the semantic specialist/evidence/reviewer step was still running at the latest verification. No r4 quality pass or audit count is claimed.
- Research scope and safety invariants remain unchanged: no candidate code execution, wallet access, signing, deployment, live trading, paid inference or cloud inference.


## 2026-11-15 — r4 reviewer recovery and source checkpoint 1,112

- Independently downloaded source artifact 14152633179 from run 43691891924 and verified checkpoint JSON against SQLite: 1,112 captured, 6,771 pending, 0 leased, 18 failed; 802 complete within configured scope and 310 coverage-limited. The 12-item cycle captured 12/12. All 18 failed records are empty-Git-repository HTTP 409 source-availability failures.
- Source successor 43691988547 restored the exact parent artifact and is still in its next capture batch; no successor checkpoint is claimed yet.
- Independently audited r4 artifact 14152481228 from run 43688699311. Both candidate-purpose tasks and all 12 specialist reports completed; both evidence gates passed with 77 accepted evidence references for 0xnavarro/Aave-Liquiditor and 23 for AlbertSu123/UniswapFlashSwap. Both reviewer tasks failed before inference because the seven prior reports plus duplicated source excerpts exceeded the reviewer context cap. No dossiers were generated and no semantic audit count changed.
- PR #22 merged at ddeb3470f61fb61f389d5604508cb7a7dc7e1203. It adds lossless reviewer context compaction, stronger adversarial reviewer criteria, fail-closed overflow checks, and a provenance-verified reviewer-only recovery workflow. CI 43693371140 and main CI 43693473120 passed Python 3.11/3.12/3.13.
- Reviewer recovery run 43693473127 is in progress at immutable r4 artifact download/verification. It must revalidate all seven prior reports, task/role/commit/tree provenance and the positive evidence gate, then run only the two independent reviewers. r4 remains not accepted pending artifact audit.
- Mission and safety boundary unchanged. Source captures are not semantic audits; no candidate code executed; no wallet/signing/deployment/live trading; no cloud or paid inference.


## Authoritative ground-verification checkpoint (2026-11-15 08:43 UTC)

- Locked mission unchanged: evidence-backed research over 7,901 discovered public GitHub candidates. Discovery coverage remains 28/38 query templates complete; 10 remain incomplete.
- **Latest independently downloaded source checkpoint:** run [43695633862](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43695633862), artifact 14153204517, SHA-256 `f53377a62eae4a8f758c8b67989d018a3ecc1232416eb5d1636ff143aea5e492`. SQLite integrity is `ok`; checkpoint JSON and SQLite agree: **1,171 captured / 6,711 pending / 0 leased / 19 failed**, with 845 complete within configured scope and 326 coverage-limited. The latest 12-candidate cycle captured 11 and had one empty Git repository HTTP 409. All 13,639 vault files independently match their Git blob SHA-1 paths (0 mismatches).
- Source child [43695703370](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43695703370) restored the exact parent artifact and is capturing the next 12 candidates. Source capture is demonstrably self-chaining: completed runs 43695380555, 43695481083, 43695549399 and 43695633862 each completed checkpoint upload, retired the consumed parent only after replacement, and dispatched the next child. Intermediate artifacts may disappear after their successor safely replaces them; use the newest retained artifact.
- **r4 is not accepted.** Reviewer recovery [43693473127](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43693473127) completed and uploaded artifact 14154370687 (SHA-256 `cb609e08d2e7d08e1133045a19a4dda87262f374c744c147453f790ad6d5a947`). Both reviewer decisions were `inconclusive`. Manual artifact audit: the Aave reviewer missed the wrong Pool pointer and missing callback authentication, repeated a false direct-liquidation claim and returned high confidence despite partial status/unknowns; the Uniswap reviewer correctly noticed the unimplemented `uniswapV2Call` TODO but also returned high confidence despite partial status/unknowns. Reviewer task completion is not semantic correctness. No dossier and no semantic audit count increment.
- PR [#23](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/23) merged at `5bff54b556cf45d482391cefbf16de746df3f2f4`. New r5 controls: strict primary-purpose taxonomy; role-specific finding categories; non-security severity suppression; maximum four narrowly relevant evidence IDs per finding; high confidence only for implemented reports with no unknowns; seven-report purpose consensus; exact evidence excerpt/path/line/commit/tree/hash revalidation. CI [43695283729](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43695283729) and merge CI [43695350412](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43695350412) passed Python 3.11/3.12/3.13.
- Fresh r5 pilot [43695437370](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43695437370) uses new mission/database/artifact paths, qwen2.5:3b CPU-only loopback inference and immutable seed artifact 14121666814 with exact SHA-256 verification. Restore, runtime installation and fresh DAG bootstrap passed; serialized specialist/evidence/reviewer execution is in progress. No artifact or r5 acceptance is yet claimed.
- **Next gate:** inspect r5 artifact and every report. Specifically challenge Aave Pool pointer/callback authentication and Uniswap TODO/placeholder behavior. If any gate fails, repair and rerun fresh isolated pilot; do not generate dossiers or increment semantic audit count. Only after full semantic and reviewer acceptance implement dossier generation and reviewer-disagreement reconciliation, then enqueue the next persistent DAG batch.
- Safety unchanged: no candidate code execution, wallets, signing, deployment, live trading, cloud inference or paid inference.

