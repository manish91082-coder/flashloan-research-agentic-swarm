# Next Actions

1. Verify CI run 43587464686 for latest main commit 5140c93011b4baf55104c9ec91016f4a9c9ecfb3; repair any failure before more code changes.
2. Revalidate and audit the next high-signal candidates from the 38-repository discovery snapshot, starting with Power-Howdy/flashloan-bot-ArbitrageAndLiquidation, tundefund0-gif/morpho-liquidator and CryptoWizardsNet/flash-loan-arbitrage-triangular. Pin current HEAD, tree SHA, source blob SHA and exact line ranges.
3. Extend the candidate audit rubric: protocol scope, callback authentication, initiator/state binding, balance-delta accounting, min-profit enforcement, route/approval controls, exact trade-size quotes, gas/MEV costs, tests/CI, dependency/license provenance and deployment/profit evidence.
4. Fix recursive Git tree truncation handling: when GitHub returns truncated=true, traverse non-recursive directory trees with explicit depth/entry limits and preserve incomplete status if any subtree remains truncated.
5. Expand tests for GitHub pagination, rate-limit retry, truncated-tree recovery, source-file caps, oversized blobs, blob SHA mismatch, callback/accounting signal fixtures and malformed API payloads.
6. Copy the full local 26-test suite into the repository and ensure remote CI runs the complete suite across Python 3.11, 3.12 and 3.13.
7. Add semantic AST parsing for Solidity/Python/Rust only after evidence capture coverage is complete; do not promote regex hits into accepted findings automatically.
8. Add deterministic claim validation and independent review gates.
9. Only then introduce LangGraph specialist orchestration. Model inference remains optional and fail-closed when no free inference provider is available.
10. Keep n8n optional; no paid services, candidate-code execution, wallet keys, signing, deployment or live trading.
