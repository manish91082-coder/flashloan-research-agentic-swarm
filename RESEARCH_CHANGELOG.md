# Research Changelog

## 2026-11-14
- Created the dedicated repository and verified GitHub connector push/admin access.
- Added Python standard-library research engine, GitHub REST client, SQLite persistence, commit/tree pinning, bounded source retrieval, Git object SHA-1 verification and lexical signal extraction.
- Added read-only CI and a separately permissioned scheduled/manual discovery workflow.
- Pinned external GitHub Actions by full commit SHA.
- Added Phase A smoke tests, role/architecture/decision docs, project state and candidate revalidation queue.
- Local validation: compileall PASS; 26/26 tests PASS; workflow YAML parsed; CLI help/status PASS.
- Remote push CI: Python 3.11, 3.12 and 3.13 jobs succeeded. PR CI test steps also succeeded at last inspection; final runner cleanup was completing.
- Remote test suite currently has four focused smoke tests. The full 26-test local suite has not yet been copied into the repository.
- Historical candidate assessments are explicitly marked for current-HEAD revalidation. No current security finding is yet accepted.
- No candidate repository code executed. No wallet, signer, deployment, live trading or transaction execution.
