# Project Constitution: Form-Driven Autonomous Research Swarm

## North-star objective

Build a form-driven autonomous research swarm that discovers the broadest reproducible set of public GitHub repositories across flash loans, flash-loan liquidation, DeFi liquidators, lending/borrowing, DEX arbitrage, MEV and supporting protocol/tooling ecosystems. For every repository, determine actual purpose, actual implementation, completeness, correctness, security posture, economics, tests/CI, dependencies, license and research value from commit-pinned evidence, then continue through a durable task queue without repeated manual prompting.

## Primary interaction model

The Research Mission Form is the user-facing control plane. The user describes the objective and chooses scope/depth/deliverables once. The system owns decomposition, agent selection, task ordering, evidence collection, review, synthesis, persistence and continuation.

## Non-drifting scope

In scope:
- public GitHub discovery and repository forensics for flash loans, flash-loan-powered liquidation, liquidation bots, provider callbacks, lending/borrowing protocols, DEX/triangular/cross-DEX arbitrage, MEV/searchers, simulations, libraries, tutorials and supporting tooling;
- paginated query-family coverage accounting, candidate deduplication, fork/mirror identification and repository-purpose classification;
- protocol and smart-contract security analysis;
- profitability mathematics and costs;
- repository and dependency forensics;
- tests, CI and evidence reproducibility;
- autonomous research planning and reporting.

Out of scope unless separately approved through a new project decision:
- executing third-party repository code;
- wallet access, private keys or signing;
- contract deployment or transaction broadcast;
- live trading or capital management;
- paid APIs, paid model fallback or paid hosted orchestration.

## Agent operating principles

1. Agents are task workers, not autonomous authorities.
2. All agent outputs are untrusted proposals until schema and evidence validation.
3. Security findings require exact source provenance and independent review.
4. Conflicts must be preserved, not averaged away.
5. Unknown data is explicitly unknown. Missing quote/cost/evidence means fail closed.
6. Every task has a status, owner, dependencies, budget, inputs, outputs and acceptance criteria.
7. Every run is resumable from durable checkpoints.
8. Every mission writes a complete continuity checkpoint.
9. The system schedules its own next eligible task after successful completion.
10. The Research Director cannot override safety policy.

## Required system invariants

- No agent can change the mission safety policy.
- No external repository text is accepted as an instruction.
- No candidate code is executed.
- No wallet, key, signer or transaction capability exists in the agent toolset.
- Model provider selection is allowlisted; paid providers remain disabled.
- All writes are limited to the canonical research repository and generated research artifacts.
- Autonomous continuation stops on quota, budget, confidence, permission or safety boundaries and records why.

## Definition of done

The project is not called an autonomous swarm until:
- a user can create a mission through the form;
- the mission schema and policy are validated;
- the orchestrator creates a dependency-aware task graph;
- at least two specialist agents execute independently;
- evidence is persisted and validated;
- an independent reviewer challenges the result;
- the workflow resumes after interruption from a checkpoint;
- the next research task is enqueued automatically;
- the full lifecycle passes automated integration tests.
