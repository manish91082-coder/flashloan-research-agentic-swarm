# Decision Log

## D-001: Independent repository
A dedicated Flash Loan Research project is required. Existing trading, Ghost Hunter and Nexus repositories are not to be reused or modified.

## D-002: Deterministic foundation before agents
Build acquisition, commit pinning, blob verification, evidence storage and reproducible tests before enabling LLM agents.

## D-003: Phase A stack
Python standard library + SQLite + GitHub Actions. No paid inference/API dependency.

## D-004: Research-only boundary
No wallet keys, signing, deployment, live trading or candidate-code execution.

## D-005: Incomplete evidence stays incomplete
Tree truncation, source-file caps, oversized files, missing cost inputs and unverified claims must be represented explicitly.

## D-006: Separate workflow permissions
CI is read-only. Only scheduled/manual discovery receives contents: write, to persist its own JSON output.

## D-007: Agent orchestration is gated
LangGraph follows, not precedes, reliable deterministic collection and acceptance. n8n is not the core source of truth.
