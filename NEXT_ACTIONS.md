# Next Actions

1. Verify the post-merge main CI run for commit 6a0a395699e0bc6479ad493b4c33d8ca06818a11.
2. Restore the remaining eight tests from the 26-test local baseline into remote CI. Do not call the remote suite 26/26 until all tests execute there.
3. Add a deterministic accounting-invariant module and fixture tests for Bcb >= B0 + P + F + M; explicitly test dust, principal, premium and minimum-profit edge cases. This must be a simulator/test harness in our repository, not execution of third-party candidate code.
4. Add deterministic off-chain net-profit calculation that fails closed on missing/stale flash fee, DEX fees, gas, price conversion, slippage and relay/builder costs.
5. Add fixture-backed GitHub search pagination that captures total_count, incomplete_results, page and query provenance.
6. Add recursive-tree truncation recovery and explicit source-file cap/oversize coverage accounting.
7. Revalidate the ten historical candidates against their current HEAD commits and inspect remaining candidates from the 38-item discovery snapshot.
8. Add AST-aware Solidity/Rust/Python analysis and protocol classification. Lexical patterns stay as leads only.
9. Add candidate test/CI metadata collection pinned to exact candidate commits. Never execute candidate code in the research pipeline.
10. Add claim grading, contradiction tracking and evidence acceptance/rejection review.
11. Only after deterministic state and evidence controls stabilize, add LangGraph specialist orchestration with bounded state transitions and schemas.
12. Observe the first scheduled GitHub discovery run (Mondays at 02:17 UTC / 07:47 IST) and verify its timestamped research_runs report commit.
13. Keep n8n optional for notifications/approval UX, not the evidence store or orchestration source of truth.
14. Do not assert profitability without trade-size-specific simulation and full costs, plus independent evidence of realized settlement.

## Current limitations

- Remote CI currently runs 18 tests (4 baseline + 14 extended). The original 26-test baseline passed locally only; 8 test cases still need remote restoration.
- The manual discovery baseline searched only page 1, up to 20 results per query; it is not exhaustive.
- The scheduled workflow's first run is pending. The connected GitHub action set has no workflow-dispatch action.
- Branch protection is not configured; the connected GitHub action set exposes no branch-protection mutation action.
- Candidate forensic findings are source-backed research assessments, not external audits or exploit reproductions.
