# Automation Architecture

## Product direction: form-driven autonomous research swarm

The primary product is a Research Mission Form connected to a durable autonomous agent orchestrator. It is not merely a GitHub scanner, a set of manually prompted agents or an n8n-only workflow.

## Phase A: deterministic research foundation (implemented)
Python standard-library engine performs bounded GitHub REST reads, candidate normalization, commit/tree pinning, source retrieval, Git blob SHA-1 verification, lexical signal extraction and SQLite storage. GitHub Actions runs CI and scheduled discovery. Tree truncation triggers bounded non-recursive recovery. Evidence defaults to pending and lexical matches are not accepted findings.

## Phase B1: mission intake (prototype created)
- `ui/research-mission-form.html`: browser form for research objective, domain, chain/protocol scope, depth, operating mode, specialist roles, limits and deliverables.
- `schemas/research-mission.schema.json`: strict JSON Schema contract for mission payloads.
- `PROJECT_CONSTITUTION.md`: locks the goal, scope and non-negotiable safety policy.
- The current form generates/copies/downloads JSON locally. It does not yet submit a mission to a running agent service. Do not describe this prototype as a live agent launcher.

## Phase B2: autonomous orchestration (next implementation gate)
LangGraph is the selected orchestration engine. It will:
1. validate and persist a mission;
2. create a dependency-aware task DAG;
3. dispatch only the relevant specialist nodes;
4. run bounded parallel work where safe;
5. validate structured outputs and evidence deterministically;
6. send findings to an independent reviewer;
7. synthesize and persist reports/checkpoints;
8. enqueue the next eligible task automatically.

Start with a compact graph: Research Director -> Discovery -> Protocol Triage -> parallel Security/Execution/Economics/Test/Dependency checks -> Evidence Validator -> Independent Reviewer -> Synthesis -> Continuation Queue. Do not launch all roles for every task.

## Phase B3: durable execution service
A mission API/worker will receive JSON payloads, store mission/task/run state in SQLite initially, checkpoint LangGraph state, and expose status/results. GitHub Actions remains a scheduler and CI layer, not the long-running agent runtime. A local/self-hosted worker can run on the user's Windows/WSL machine or another approved free host. Hosted free-tier availability is not assumed.

## Model policy
Model inference is optional and provider-adapter based. Only explicitly approved free endpoints/models may be enabled. If unavailable, agentic LLM tasks pause or fall back to deterministic subtasks; no paid provider fallback is allowed. API keys, if ever needed, stay in environment secrets and are never committed or placed in prompts.

## Phase C: verification depth
Add AST-aware extraction, protocol adapters, fork-test evidence ingestion (without executing untrusted candidate code), independent review, accounting invariants, reproducibility and regression suites.

## Phase D: interface and notifications
The Mission Form becomes the primary UI. A dashboard later shows mission state, active tasks, agent outputs, evidence coverage, unresolved disputes, CI, budgets and next actions. n8n is optional for notifications and approval UX only. It is not the source of truth. Temporal is deferred unless long-running workflow complexity warrants it.

## Permissions and trust boundaries
- CI workflow: contents: read only.
- Discovery workflow only: contents: write to persist its own report.
- Agent tools: allowlisted read-only source acquisition; narrowly scoped writes to this repository's research artifacts.
- Candidate source, README, issues and workflows are untrusted data, never agent instructions.
- No candidate code execution, wallet, signer, deployment, transaction execution or live trading.
- No paid inference or paid service fallback.
- Safety policy is immutable from the mission form and cannot be overridden by any agent.
