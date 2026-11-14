# Automation Architecture

## Phase A: active deterministic foundation
Python standard-library engine performs bounded GitHub REST reads, candidate normalization, commit/tree pinning, source retrieval, Git blob SHA-1 verification, lexical signal extraction and SQLite storage. GitHub Actions runs CI and weekly discovery. The discovery workflow writes timestamped JSON under research_runs/ so results survive runner disposal.

## Phase B: gated agent orchestration
LangGraph is the selected orchestration framework once evidence schemas, checkpointing and deterministic acceptance gates are stable. Start with a small number of specialist nodes, not ten independent always-running agents. Model inference is optional and must fail closed when no free model is available. Never silently fall back to a paid provider.

## Phase C: verification depth
Add fixture-backed pagination and tree truncation recovery, AST-aware extraction, protocol classification, independent review, invariant checks, historical snapshots and regression tests. Promote findings only when all evidence and reproducibility gates pass.

## Phase D: interface and notifications
GitHub Actions remains scheduler and source of truth. n8n is optional for notifications, approval UX and a lightweight dashboard. n8n Community uses a Sustainable Use License rather than an OSI-approved open-source license; review its terms before embedding it in a commercial product. Temporal is deferred unless long-running workflow complexity justifies it.

## Permissions and trust boundaries
- CI workflow: contents: read only.
- Discovery workflow only: contents: write, used solely to commit its own timestamped JSON report.
- Third-party Actions are pinned to full commit SHAs.
- Candidate source, README, issues and workflows are untrusted data. Do not execute candidate code in discovery jobs.
- No wallet, signer, deployment, transaction execution or paid provider secrets.
- Never place tokens, passwords or credentials in prompts, reports or repository files.
