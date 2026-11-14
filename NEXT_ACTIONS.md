# Next Actions

1. Observe the first scheduled public GitHub discovery run. The current schedule is every Monday at 02:17 UTC (07:47 India Standard Time).
2. Verify the run writes a timestamped JSON snapshot under research_runs/ and that the report includes limitations and query provenance.
3. Copy the full 26-test local regression suite into the repository; remote CI currently runs four focused smoke tests plus compileall.
4. Add fixture-backed pagination and recovery for truncated recursive trees.
5. Revalidate every seeded candidate at its current exact commit SHA before treating historical findings as current.
6. Add AST-aware Solidity/Rust/Python analysis and a protocol classifier.
7. Add deterministic claim grading and evidence acceptance/rejection review.
8. Only after those controls stabilize, add LangGraph specialist orchestration with bounded state transitions and schemas.
9. Keep n8n optional for notifications and approval UX, not the evidence store or orchestration source of truth.
10. Do not assert profitability without trade-size-specific simulation and full fees, gas, slippage, builder/relay costs, and independently evidenced realized settlement.

## Operational limitation
The connected GitHub action set supports reading workflow runs/jobs and repository writes, but it does not expose a workflow-dispatch or branch-protection mutation action. The schedule is therefore enabled and will perform the first automated run without a manual dispatch from this connector.
