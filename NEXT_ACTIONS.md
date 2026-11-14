# Next Actions

1. Complete source-level forensic review of the pinned candidate shortlist, starting with Aquafr198/liquidator, litmajor/argus-evm, and clubytech/cluby-liquidator.
2. Commit candidate evidence with exact current commit SHA, tree SHA, source blob SHA, path/line range, excerpt, claim type, confidence, limitations and review status.
3. Restore the remaining original local regression cases into remote tests. Current remote CI runs 18 tests (4 baseline smoke + 14 extended); the full original 26-test suite has passed locally only.
4. Add fixture-backed GitHub search pagination, total_count/incomplete_results capture and recursive-tree truncation recovery.
5. Add deterministic protocol classification and AST-aware Solidity/Rust/Python analysis; lexical signals remain discovery leads.
6. Add test/CI metadata collection pinned to candidate commit SHA, including exact workflows and test commands. Never execute candidate repo code in this research pipeline.
7. Revalidate all carried-forward historical candidates at current HEAD before presenting current assessments.
8. Add claim grading, contradiction tracking and evidence acceptance/rejection review.
9. Only after these controls stabilize, add LangGraph specialist orchestration with bounded state transitions and schemas.
10. Keep n8n optional for notifications and approval UX, not the evidence store or orchestration source of truth.
11. Observe the first scheduled GitHub discovery run (Mondays at 02:17 UTC / 07:47 IST) and verify its timestamped report commit.
12. Do not assert profitability without trade-size-specific simulation and full fees, gas, slippage, builder/relay costs, and independently evidenced realized settlement.

## Operational limitation

The connected GitHub action set supports reading workflow runs/jobs and repository writes, but it does not expose a workflow-dispatch or branch-protection mutation action. The scheduled workflow is enabled; first automatic run is pending. Branch protection is not configured.
