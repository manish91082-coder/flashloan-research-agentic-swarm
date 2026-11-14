# Next Actions

1. Expand tests for GitHub search pagination and retry/rate-limit behavior, malformed payloads, source-file caps, oversized blobs and blob SHA mismatch.
2. Add complete metadata enrichment for discovered candidates (description, pushed_at, stars, language, license and topics) with explicit missing-field tracking.
3. Continue commit-pinned audits of remaining 35 candidates, prioritizing current maintained protocol-specific implementations and reproducible tests.
4. Improve source coverage with path-specific prioritization and explicit omitted-file manifests; keep file-size and source-count caps fail-visible.
5. Copy and reconcile the previously validated 26-test local regression suite if it remains available; the repository currently runs 7 tests remotely.
6. Add Solidity AST/Slither-compatible static analysis only in isolated, pinned tooling; do not execute candidate project scripts or dependency install hooks.
7. Add deterministic claim validation, severity rubric, evidence provenance and independent review gates.
8. Build a read-only workflow report that can inspect pinned candidates and persist JSON snapshots, keeping least-privilege permissions.
9. Only after these controls stabilize, introduce LangGraph specialist orchestration with bounded state, structured outputs and deterministic acceptance.
10. Keep n8n optional for notifications/approval UI. No paid services, wallet keys, transaction signing, deployment or live trading.
