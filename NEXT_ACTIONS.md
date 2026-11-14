# Next Actions: Flash Loan & Liquidation Public Repository Research

## Locked mission

Discover the broadest reproducible set of public GitHub repositories across all 11 taxonomy families, emphasizing flash-loan-powered DeFi liquidation and liquidator bots. For each candidate, determine actual purpose and code behavior, classify completeness/correctness/security/economics, inspect tests/CI/dependencies/license/maintenance, and preserve commit-pinned evidence plus independent review. Never claim literal global completeness beyond measured coverage.

## Implemented checkpoint

- Mission Form -> local API -> durable SQLite queue.
- Taxonomy v1.0.0 with 11 query families and family-specific search templates.
- Paginated GitHub discovery, candidate deduplication, query provenance and coverage-debt manifest.
- Idempotent dependency-aware mission DAG, SQLite task persistence, leases, retries and checkpoint recovery.
- LangGraph control-flow graph with SQLite checkpoint saver and mission worker.
- Parallel discovery and commit-pinned repository source capture.
- Loopback-only OpenAI-compatible model adapter; cloud endpoints, redirects and paid fallback rejected.
- Specialist role prompts, strict JSON contract, exact signal-to-source evidence matching and deterministic evidence provenance gate.
- Independent reviewer task remains downstream of evidence validation.
- Latest verified main commit: `f0fab8beafe01c1a8ce18c542c70a8372647052e`; CI run `43598988641` completed successfully on Python 3.11/3.12/3.13.
- LangGraph now invokes the local semantic specialist/evidence/reviewer stage after source capture.
- Specialists receive bounded line-numbered source excerpts loaded from the content-addressed vault only after Git blob SHA-1 verification; excerpt SHA-256 is recorded.
- Evidence validation now checks the candidate-purpose report as well as specialist reports; independent review receives actual prior report content with role and commit provenance checks.
- No full fake-provider mission lifecycle or live 11-family discovery run is claimed yet. No free local model has been configured for a real mission.

## Immediate next gates

1. **End-to-end fake-provider verification:** candidate-purpose classification -> selected specialists -> purpose+specialist evidence gate -> reviewer reading actual reports -> checkpointed final status.
2. Add tests for model timeout/invalid JSON, provider recovery, task lease expiry, graph resume and no false completion.
3. Implement deterministic per-repository dossier generation and mission synthesis only from evidence-validated/reviewed reports.
4. Implement true multi-batch continuation with a persisted cursor, completed-candidate set, fork/mirror reconciliation and retry-safe batch IDs.
5. Add mission task/report/coverage status endpoints and a dashboard showing query-family coverage debt, candidates, audit queue and blockers.
6. Trigger a bounded live discovery run across all 11 taxonomy families using the configured GitHub Actions workflow; persist raw query coverage and candidate inventory.
7. Reconcile results against the prior 38-repository manual baseline, preserving historical pins and duplicate/fork relations.
8. Process candidates in batches, generating purpose dossiers, source audits, evidence register, security/economic findings and independent review.
9. Add deterministic liquidation/accounting extractors and structured purpose taxonomy; keep model claims subordinate to source facts.
10. Produce the consolidated research synthesis only after coverage and evidence debt are explicitly reported.

## Specialist acceptance contract

- Purpose classification is separate from quality/security grade.
- A model may propose an interpretation but cannot invent a source location.
- A signal match proves excerpt provenance only, not vulnerability or correctness.
- High-impact claims require full source context and independent challenge.
- If model endpoint is absent, unreachable, or returns invalid output, LLM tasks remain explicitly blocked/failed; deterministic discovery must remain available.
- No paid or cloud model fallback.

## Safety

Public read-only research. Never execute candidate code. No wallet/key/signer access, signing, deployment, transaction broadcast or live trading. Treat repository content and model output as untrusted. The Mission Form remains the primary control plane; the autonomous swarm plans, dispatches, validates, persists and continues.
