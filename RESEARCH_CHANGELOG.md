# Research Changelog

## 2026-11-14

- Created the dedicated public repository and verified GitHub connector push/admin access.
- Added Python standard-library research engine, GitHub REST client, SQLite persistence, commit/tree pinning, bounded source retrieval, Git object SHA-1 verification and lexical signal extraction.
- Added read-only CI and separately permissioned scheduled/manual public GitHub discovery workflow.
- Pinned external GitHub Actions by full commit SHA.
- Added governance docs, ten logical research roles, decision log, project state, accounting invariants and evidence schemas.
- Saved a bounded manual GitHub search snapshot: 38 deduplicated leads across four queries; page 1 only, explicitly non-exhaustive.
- PR #1 merged Phase A foundation into main: f42f93623e970a24beb0d3a5f395e03051f3893b.
- PR #2 merged regression expansion and schemas into main: a1621f16f29debe99feec14d41cbd3d3b3acd314.
- PR #3 merged four pinned candidate forensic reviews, candidate registry updates, seven source-based research findings and nine evidence records into main: 6a0a395699e0bc6479ad493b4c33d8ca06818a11.
- PR #3 CI run 43584553897 passed on Python 3.11, 3.12 and 3.13. Post-merge main push run 43584589907 was queued at the last checkpoint and still requires confirmation.
- Remote CI has 18 tests (4 baseline smoke + 14 extended) plus compileall. Original 26-test baseline passed locally; eight test cases remain to restore to remote CI.
- Four newly pinned candidates: Aquafr (multi-protocol liquidation; B0/dust accounting issue and non-WETH floor boundary), Cluby (Morpho liquidation with oracle floor but no B0 baseline/net profit floor), Argus (native Morpho callback, not flash loan; strong B0/session design but incomplete runtime), MELD (legacy Aave flashloan callback lacks caller/initiator authentication).
- Candidate source is read as untrusted data and was never executed. No wallet, signer, deployment, live trading or transaction execution.
- First scheduled discovery report remains pending. Schedule: Mondays at 02:17 UTC.
