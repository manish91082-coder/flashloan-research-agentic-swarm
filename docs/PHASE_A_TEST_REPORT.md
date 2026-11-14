# Phase A Verification Report

## Local pre-publish check

- Runtime: Python 3.13.5 in the isolated work container.
- `python -m unittest discover -s tests -v`: 26/26 passed after the hardening patch.
- `python -m compileall -q src tests`: passed after the hardening patch.
- Workflow YAML was reviewed for full-SHA action pins, least-privilege permissions and quoted workflow-dispatch input.

## Changes in the current hardening pass

- GitHub blob Base64 decoding strips transport whitespace and validates the alphabet and padding strictly.
- Captured blob length is rechecked against the configured maximum after download.
- Inspection reports disclose tree truncation, source-file cap hits and oversized/invalid source files.
- Evidence validation checks confidence values and repository identity shape.
- Discovery CLI can export portable timestamped JSON.
- Scheduled workflow stores discovery output under `research_runs/` instead of losing results when the hosted runner is discarded.
- CI remains read-only; only the discovery workflow receives `contents: write` to save its own report.
- Actions are pinned to verified full commit SHAs for official upstream `actions/checkout` v7 and `actions/setup-python` v7.0.0.

## Final local result

- `python -m compileall -q src tests`: PASS.
- `PYTHONPATH=src python -m unittest discover -s tests -v`: 26/26 PASS.
- Both workflow YAML files parsed: PASS.
- CLI help and isolated temporary-SQLite status smoke test: PASS.
- Editable install: PASS using local setuptools 82.0.1 with `--no-build-isolation --no-deps`. A standard isolated build first attempted to download build dependencies and failed because this container has no outbound network.

## Verification boundary

Local compile and all 26 tests passed after this patch. The original 26-test suite was verified locally. The repository CI initially had four smoke tests; this branch adds fourteen focused regression tests in `tests/test_extended.py`. Remote GitHub Actions results on this branch will be the authoritative remote check. Local tests do not prove external audit quality, exhaustive repository coverage, profitability or mainnet execution. No candidate source code is executed.
