# Research Changelog

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
