# Autonomous Agentic Research: Mission Form and Execution Contract

## Product direction (locked)

The product is a form-driven autonomous research system, not merely a repository scanner and not a collection of manually prompted chat agents.

The Research Mission Form is the single mission-intake surface. A user submits one mission definition. The orchestrator converts it into a dependency-aware task graph, dispatches the relevant specialist agents, collects evidence, runs deterministic validators, requests independent review, persists all state and creates the next research queue.

## Mission lifecycle

1. **Intake:** validate the mission against `schemas/research-mission.schema.json`; reject unsafe or unsupported requests.
2. **Plan:** Research Director creates a task graph, assigns owners, dependencies, budgets and acceptance criteria.
3. **Discover:** GitHub Discovery searches and normalizes public repositories, protocol documentation and source references.
4. **Triage:** Protocol Specialist classifies the primitive and implementation scope.
5. **Parallel audit:** Security, Execution, Economics, Test and Dependency agents each work on bounded evidence packets.
6. **Evidence gate:** Evidence Auditor checks commit SHA, tree SHA, blob SHA, path, line range, excerpt integrity and source provenance.
7. **Independent review:** reviewer did not author the finding; disagreements are recorded and unresolved claims remain pending.
8. **Synthesis:** Research Director produces the dossier, ranked candidates, gaps and next queue.
9. **Persistence:** mission state, task graph, agent outputs, findings, evidence, run logs and checkpoint are committed to the canonical repository.
10. **Autonomous continuation:** next eligible tasks start automatically until the mission is complete, a safety boundary is reached, a quota is exhausted or human approval is required.

## Agent topology

- Research Director: plans, dispatches, resolves task dependencies and controls acceptance.
- GitHub Discovery: source discovery and metadata.
- Protocol Specialist: lending/DEX/flash primitive classification.
- Solidity Security: callback, authorization, reentrancy, approvals and accounting.
- Execution Engineer: exact route, simulation, scanner and transaction architecture, analysis only.
- Test & Verification: tests, CI and reproducibility.
- Economics & Quant: fee, gas, slippage, liquidity and net-profit calculations.
- Dependency & License: dependency provenance and license.
- Evidence Auditor: evidence integrity and provenance.
- Independent Reviewer: adversarial review, not majority vote.
- Continuity & Documentation: state, logs, changelog and handoff.

Specialists are activated conditionally. Do not spawn all roles for every task. The initial runtime should use a small bounded graph with fan-out only where useful.

## Autonomous does not mean unbounded

Autonomy is constrained by:
- fixed research-only policy;
- no candidate-code execution;
- no wallet, key, signer, transaction, deployment or live-trading access;
- no paid inference or service fallback;
- per-mission iteration, parallelism, token and time budgets;
- allowlisted read-only tools for acquisition;
- write access only to the canonical research repository;
- deterministic evidence and schema validators;
- human approval for scope changes, new permissions or policy changes.

Free model inference is optional. If no approved free model endpoint is configured or available, the workflow must continue deterministic work where possible and mark AI-dependent tasks as blocked. It must not silently switch to a paid model.

## Current implementation status

- Phase A deterministic GitHub acquisition, commit/tree/blob pinning, SQLite and evidence capture: implemented.
- Bounded tree truncation recovery: implemented and covered by tests.
- Research Mission Form HTML prototype: created as an intake/payload composer. It exports JSON but does not yet submit to a live agent runtime.
- Mission schema and lifecycle contract: defined.
- LangGraph runtime, SQLite task DAG/leases and checkpointed worker are implemented; the graph executes deterministic discovery/source capture and invokes a local-only semantic specialist/evidence/reviewer stage.
- The local model adapter rejects non-loopback/cloud endpoints and paid fallback. Specialists receive hash-verified bounded source excerpts; the evidence gate checks purpose and specialist outputs; the independent reviewer receives prior report contents.
- Full fake-provider end-to-end lifecycle, actual local-model mission, dossier/synthesis execution, 11-family live coverage and multi-batch continuation remain unverified or incomplete.
- Therefore the current project is an advancing, checkpointed research runtime, but it must not yet be described as a fully autonomous, end-to-end completed research swarm.

## Acceptance gate before calling it autonomous

A mission must be submitted from the form, validated, planned, executed by at least two specialist nodes, independently reviewed, persisted with provenance, resumed from a checkpoint after interruption and produce a verified completion report without manually prompting each agent. Tests must prove that safety policy cannot be overridden by form values.
