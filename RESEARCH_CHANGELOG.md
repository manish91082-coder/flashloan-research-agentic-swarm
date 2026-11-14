# Research Changelog

## 2026-11-14
- Created the dedicated repository and verified GitHub connector push/admin access.
- Added Python standard-library research engine, GitHub REST client, SQLite persistence, commit/tree pinning, bounded source retrieval, Git object SHA-1 verification and lexical signal extraction.
- Added read-only CI and separately permissioned scheduled/manual public GitHub discovery workflow.
- Pinned external GitHub Actions by full commit SHA.
- Added governance docs, ten logical research roles, decision log, project state, accounting invariants and historical candidate revalidation queue.
- Saved and verified a bounded manual GitHub search snapshot: 38 deduplicated leads across four queries; page 1 only, explicitly non-exhaustive.
- PR #1 squash-merged Phase A foundation into main: f42f93623e970a24beb0d3a5f395e03051f3893b.
- PR #2 squash-merged regression expansion and schemas into main: a1621f16f29debe99feec14d41cbd3d3b3acd314.
- Added 14 extended regression tests and two JSON Schemas. Latest main CI run 43583006127 passed on Python 3.11, 3.12 and 3.13.
- Remote test count is 18 (4 baseline smoke + 14 extended), plus compileall. Original full 26-test suite passed locally; it is not yet fully restored to remote CI.
- Added Phase A local verification report at docs/PHASE_A_TEST_REPORT.md.
- Candidate forensic review underway using exact current repository commit/tree/blob pins. No current candidate finding has yet been accepted into the evidence register.
- Candidate source code was not executed. No wallet access, signer, deployment, live trading or transaction execution.
- Scheduled discovery is configured for Mondays at 02:17 UTC. First actual scheduled run and report commit remain pending.
