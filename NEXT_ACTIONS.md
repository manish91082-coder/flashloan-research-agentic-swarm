# Next Actions: Flash Loan & Liquidation Public Repository Research

## Locked mission

Discover the broadest reproducible set of public GitHub repositories across all 11 taxonomy families, emphasizing flash-loan-powered DeFi liquidation and liquidator bots. For each candidate, determine actual purpose and code behavior, classify completeness/correctness/security/economics, inspect tests/CI/dependencies/license/maintenance, and preserve commit-pinned evidence plus independent review. Never claim literal global completeness beyond measured coverage.

## Verified checkpoint

- Mission Form -> local API -> durable SQLite queue is implemented.
- Taxonomy v1.0.0 defines 11 query families and 38 configured query templates.
- Live GitHub Actions run [43600488013](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43600488013) successfully executed all 11 families.
- Discovery summary: **7,901 unique repository candidates; 38 queries; 28 complete; 10 incomplete; coverage_complete=false**. These are discovery candidates, not verified working bots.
- Raw report: `research_runs/mission/2026-11-14/discovery-43600488013-1.json`; artifact commit `231f47f0ada252a921a065da935720873f397bef`; blob SHA `3f126f4cfa4e163dbe95cb7ffb7f2528180254d5`.
- Earlier manual 1,833-name representative sample remains a separate non-exhaustive baseline, not the project-runner result.
- LangGraph, SQLite task DAG/leases/checkpoints, deterministic discovery/source capture and local-only semantic specialist/evidence/reviewer stage are implemented.
- Specialist context uses bounded line-numbered excerpts from the content-addressed vault after Git blob SHA-1 verification; evidence validation covers purpose and specialist outputs; independent reviewer receives prior report content.
- Fake-provider end-to-end fixture covers candidate purpose, six specialist roles, evidence validation and independent review. **58 tests pass** on Python 3.11/3.12/3.13; latest main CI run `43601777341` succeeded.
- Five candidate dossiers are tracked. Lumetra Labs Morpho bot grade C (native Morpho liquidation callback in reviewed path, not flash-loan funded); 0xnavarro Aave Liquiditor grade D (critical wiring/accounting gaps). New findings are pending independent review.
- No real local-model mission, candidate-code execution, deployment or transaction has occurred.

## Immediate next gates

1. Stream-import the 7,901 report rows into the durable candidate store without loading the entire artifact into unbounded memory.
2. Persist stable repository IDs, canonical names, query-family provenance, fork/mirror links and a retry-safe batch cursor.
3. Execute bounded commit-pinned source capture and purpose classification in candidate batches; discovery is not an audit.
4. Build deterministic dossier and mission synthesis from evidence-validated and independently reviewed outputs.
5. Implement true multi-batch continuation with completed-candidate set, retry-safe IDs, lease recovery and explicit stop conditions.
6. Investigate and rerun only the 10 incomplete discovery query templates; retain old snapshots and coverage debt.
7. Add task/report/coverage endpoints and a dashboard for discovered/audited queues, query debt, evidence confidence, reviewer status and next batch.
8. Add timeout/invalid-JSON, provider recovery, lease-expiry, checkpoint-resume and no-false-completion tests.
9. Run real local-model inference only after a free loopback endpoint is explicitly configured; no paid/cloud fallback.
10. Publish synthesis only after coverage, review and evidence limitations are reported.

## Specialist acceptance contract

- Purpose classification is separate from quality/security grade.
- A model may propose an interpretation but cannot invent a source location.
- A signal match proves excerpt provenance only, not vulnerability or correctness.
- High-impact claims require full source context and independent challenge.
- If model endpoint is absent, unreachable, or returns invalid output, LLM tasks remain explicitly blocked/failed; deterministic discovery must remain available.
- No paid or cloud model fallback.

## Safety

Public read-only research. Never execute candidate code. No wallet/key/signer access, signing, deployment, transaction broadcast or live trading. Treat repository content and model output as untrusted. The Mission Form remains the primary control plane; the autonomous swarm plans, dispatches, validates, persists and continues.
