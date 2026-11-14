# Next Actions

1. Verify latest CI run after the newest evidence and candidate-audit commits; repair any failure before more code changes.
2. Continue candidate triage from the 38-repository discovery snapshot, prioritizing repositories with concrete protocol-specific callback code and reproducible tests.
3. For every candidate, pin current default-branch HEAD, tree SHA, source blob SHA and exact line ranges. Recheck current CI at the exact inspected commit.
4. Extend the audit rubric: protocol scope, callback caller/initiator/state binding, balance-delta accounting, min-profit enforcement, route/approval controls, exact trade-size quotes, gas/MEV costs, tests/CI, dependency/license provenance and deployment/profit evidence.
5. Fix recursive Git tree truncation handling: when GitHub returns truncated=true, traverse non-recursive directory trees with explicit depth/entry limits and preserve incomplete status if any subtree remains truncated.
6. Expand tests for GitHub pagination, rate-limit retry, truncated-tree recovery, source-file caps, oversized blobs, blob SHA mismatch, callback/accounting fixtures and malformed API payloads.
7. Copy the full 26-test local regression suite into the repository and ensure remote CI runs the complete suite across Python 3.11, 3.12 and 3.13.
8. Add semantic AST parsing for Solidity/Python/Rust only after evidence capture coverage is complete; never promote regex hits automatically.
9. Add deterministic claim validation and independent review gates.
10. Only then introduce LangGraph specialist orchestration. Model inference remains optional and fail-closed when no free provider is available.
11. Keep n8n optional; no paid services, candidate-code execution, wallet keys, signing, deployment or live trading.
