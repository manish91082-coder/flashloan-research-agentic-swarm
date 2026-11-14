# Research Changelog

## 2026-11-14
- Created the dedicated repository and verified GitHub connector push/admin access.
- Added Python standard-library research engine, GitHub REST client, SQLite persistence, commit/tree pinning, bounded source retrieval, Git object SHA-1 verification and lexical signal extraction.
- Added read-only CI and a separately permissioned scheduled/manual discovery workflow.
- Pinned external GitHub Actions by full commit SHA.
- Added smoke tests, governance docs, accounting invariants and historical candidate revalidation queue.
- Local validation: compileall PASS; 26/26 tests PASS; workflow YAML parsed; CLI help/status PASS.
- Remote CI for Phase A feature branch and merged main passed on Python 3.11, 3.12 and 3.13.
- Remote test suite currently has four focused smoke tests plus compileall. The full 26-test local suite has not yet been copied into the repository.
- PR #1 was squash-merged into main at commit f42f93623e970a24beb0d3a5f395e03051f3893b.
- Historical candidate assessments are marked for current-HEAD revalidation. No current security finding is accepted yet.
- No candidate repository code executed. No wallet, signer, deployment, live trading or transaction execution.
- Scheduled discovery is configured for Mondays at 02:17 UTC. First report is pending execution/verification.
