# Flash Loan Research Agentic Swarm

Evidence-first, research-only GitHub intelligence for flash-loan arbitrage and liquidation systems. The project deliberately builds deterministic acquisition and provenance controls before enabling LLM agents.

## Safety boundary

- Public GitHub research only. No wallet access, transaction signing, deployment, live trading or transaction execution.
- Candidate repositories are treated as untrusted data. Their source, README files, workflows and issue text are never executed or treated as agent instructions.
- Lexical matches are discovery leads, not proof of runtime behavior, security defects or profitability.
- Captured source is pinned to a full commit SHA and Git blob SHA. A mismatch fails closed.
- No paid API or third-party Python runtime package is required for Phase A. GitHub API rate limits still apply.

## Requirements and local setup

- Python 3.11+
- Standard-library runtime for Phase A

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux / WSL: source .venv/bin/activate
pip install -e .
python -m compileall -q src tests
PYTHONPATH=src python -m unittest discover -s tests -v
```

## CLI

```bash
# Search public GitHub repositories and save a portable JSON record
python -m flashloan_research.cli discover --query "flash loan arbitrage" --per-page 30 --page 1 --output research_runs/manual-discovery.json

# Pin a repository's default-branch commit/tree and inspect bounded source files
python -m flashloan_research.cli inspect manuelinfosec/flash-arb-bot

# Show local SQLite counts or export pending/accepted evidence records
python -m flashloan_research.cli status
python -m flashloan_research.cli export-evidence
```

Set `GITHUB_TOKEN` only as an environment variable when a higher authenticated API limit is needed. A fine-grained read-only token is sufficient for local collection. Never paste tokens into chat or commit them. The scheduled workflow uses its built-in token and has write permission only to persist its own generated discovery report.

## Phase A implementation

- Read-only GitHub REST acquisition with bounded retries/backoff.
- Repository candidate normalization and SQLite persistence.
- Default-branch commit SHA and Git tree SHA pinning.
- Bounded source selection, with excluded vendor/build folders and explicit file-size/file-count limits.
- Git blob object SHA-1 verification using `blob <length>\0<bytes>` framing.
- Content-addressed source vault under `data/snapshots/`, keyed by verified Git blob SHA.
- Lexical indicators for flash-loan primitives, callbacks, min-profit variables, balance reads and reentrancy guards.
- Evidence records are low-confidence and `pending` by default.
- Tree truncation, oversized source files and source-file caps are surfaced as coverage limitations, not treated as complete scans.
- Weekly GitHub Actions discovery writes timestamped JSON records to `research_runs/`; no third-party repository code is executed.

## Automation architecture

**Phase A:** Python deterministic engine + SQLite + GitHub Actions.

**Phase B (gated):** LangGraph as one orchestrator coordinating bounded specialist roles after evidence schemas and deterministic acceptance gates stabilize. No agent receives arbitrary shell, secrets, write or signing tools.

**Optional:** n8n may later provide visual triggers, notifications and approval UX. It is not the source of truth and is not required for correctness. n8n Community uses a Sustainable Use License, so commercial embedding/use must be reviewed separately.

## Current verification

See [`docs/PHASE_A_TEST_REPORT.md`](docs/PHASE_A_TEST_REPORT.md) and the current GitHub Actions checks. A passing unit suite verifies code behavior under fixtures; it is not an external security audit, a full semantic audit of candidate projects, or evidence of realized on-chain profit.
