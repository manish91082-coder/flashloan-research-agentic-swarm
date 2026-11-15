# Flash Loan Research Agentic Swarm

Evidence-first, research-only GitHub intelligence for flash-loan arbitrage and liquidation systems. The project deliberately builds deterministic acquisition and provenance controls before enabling LLM agents.

## Safety boundary

- Public GitHub research only. No wallet access, transaction signing, deployment, live trading or transaction execution.
- Candidate repositories are treated as untrusted data. Their source, README files, workflows and issue text are never executed or treated as agent instructions.
- Lexical matches are discovery leads, not proof of runtime behavior, security defects or profitability.
- Captured source is pinned to a full commit SHA and Git blob SHA. A mismatch fails closed.
- No paid API or third-party Python runtime package is required for Phase A. GitHub API rate limits still apply.

## Requirements and local setup

- Python 3.11+
- Standard-library runtime for Phase A

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux / WSL: source .venv/bin/activate
pip install -e .
python -m compileall -q src tests
PYTHONPATH=src python -m unittest discover -s tests -v
```

## CLI

```bash
# Search public GitHub repositories and save a portable JSON record
python -m flashloan_research.cli discover --query "flash loan arbitrage" --per-page 30 --page 1 --output research_runs/manual-discovery.json

# Pin a repository's default-branch commit/tree and inspect bounded source files
python -m flashloan_research.cli inspect manuelinfosec/flash-arb-bot

# Show local SQLite counts or export pending/accepted evidence records
python -m flashloan_research.cli status
python -m flashloan_research.cli export-evidence
```

Set `GITHUB_TOKEN` only as an environment variable when a higher authenticated API limit is needed. A fine-grained read-only token is sufficient for local collection. Never paste tokens into chat or commit them. The scheduled workflow uses its built-in token and has write permission only to persist its own generated discovery report.

## Phase A implementation

- Read-only GitHub REST acquisition with bounded retries/backoff.
- Repository candidate normalization and SQLite persistence.
- Default-branch commit SHA and Git tree SHA pinning.
- Bounded source selection, with excluded vendor/build folders and explicit file-size/file-count limits.
- Git blob object SHA-1 verification using `blob <length>\0<bytes>` framing.
- Content-addressed source vault under `data/snapshots/`, keyed by verified Git blob SHA.
- Lexical indicators for flash-loan primitives, callbacks, min-profit variables, balance reads and reentrancy guards.
- Evidence records are low-confidence and `pending` by default.
- Recursive tree truncation triggers bounded non-recursive directory recovery (50,000 entries / 10,000 directories); incomplete recovery, oversized source files and source-file caps remain explicit coverage limitations.
- Weekly GitHub Actions discovery writes timestamped JSON records to `research_runs/`; no third-party repository code is executed.

## Locked research mission and keyword taxonomy

The full mission scope is documented in [Flash Loan & DeFi Public Repository Research Mission](research/FLASHLOAN_REPOSITORY_RESEARCH_MISSION.md). The single source of search terms, provider callback names, liquidation/arbitrage/MEV terms, purpose labels and audit dimensions is [keyword-taxonomy.json](research/keyword-taxonomy.json) v1.0.0. The mission explicitly includes flash-loan-powered liquidation and liquidation bots, not only arbitrage.

The Mission Form records selected taxonomy families and pagination limits. Search coverage must be measured query-by-query, with API/indexing/search-cap limitations recorded as coverage debt. A first-page discovery snapshot is not exhaustive.

## Form-driven autonomous agentic system

- [Research Mission Form prototype](ui/research-mission-form.html): configure a research mission and generate JSON.
- [Mission schema](schemas/research-mission.schema.json): machine-readable intake contract.
- [Project Constitution](PROJECT_CONSTITUTION.md): locked goal, safety boundaries and definition of done.
- [Autonomous research lifecycle](docs/AUTONOMOUS_AGENTIC_RESEARCH.md): mission-to-agents-to-evidence-to-continuation architecture.

**Verified capability at current main:** the form connects to a local-only API and durable SQLite queue. LangGraph runs checkpointed deterministic discovery/source capture and invokes a loopback-only semantic specialist/evidence/reviewer stage. Specialists receive bounded line-numbered excerpts from the content-addressed vault after Git blob SHA-1 verification; independent review receives actual prior reports. The model output contract uses stable IDs for exact commit-pinned source signals, requires each material finding to link to selected evidence, rejects out-of-catalog IDs and fails closed on zero-evidence claims. Reviewer-only fields are absent from specialist JSON Schemas. The fake-provider end-to-end fixture covers candidate purpose, six specialists, evidence validation and independent review.

**Current live execution checkpoint (15 Nov 2026):** discovery has 7,901 candidates (28/38 query templates complete). Latest durable source checkpoint is 942/7,901 captured, 6,947 pending, 0 leased and 12 empty-repository failures; source capture is not semantic audit. Source-capture workflows now emit per-candidate progress and structured GitHub API retry telemetry (PR #15, merge commit `a54019a4f6e95cd657e94b79cc3a0712be2bc976`). Agent Form r2 pilot [43683037797](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43683037797) has successfully restored its immutable seed, installed local Ollama qwen2.5:3b and bootstrapped a fresh mission; serialized specialist/evidence/reviewer execution remains in progress and has **not** been accepted. No semantic audit count has been incremented. Main CI [43684603884](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43684603884) passed on Python 3.11/3.12/3.13.
 
**Latest quality-gate checkpoint (15 Nov 2026):** PR [#13](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/13) and PR [#14](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/14) are merged. Specialist model schemas now exclude reviewer-only fields; only the independent reviewer receives an explicit review decision and disagreement array. The fresh r1 live pilot [43681829089](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681829089) correctly failed closed when the model returned reviewer-only values from a specialist task. No semantic audit count was increased. The isolated r2 pilot [43683037797](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43683037797) is the current attempt, using a fresh mission/database and the preserved immutable seed. It has restored the immutable seed, installed the local model and bootstrapped its fresh DAG; serialized specialist/evidence/reviewer execution is in progress. It must pass both candidate-purpose tasks, 12 specialist reports, two positive source-linked evidence gates and two independent reviews before dossier generation proceeds.

**Latest autonomous source-capture checkpoint:** [Run 43681894031](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681894031), artifact 14148553489: 942/7,901 captured, 6,947 pending, 0 leased, 12 empty-repository HTTP 409 failures; 687 complete within configured scope and 255 coverage-limited. [Run 43681954178](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681954178) resumed from that exact artifact and is processing the next batch. Source capture is not semantic audit.


**Live discovery:** GitHub Actions run [43600488013](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43600488013) executed all 11 taxonomy families and 38 query templates: 7,901 unique candidates, 28 complete and 10 incomplete queries. Overall coverage is incomplete. The report is saved at `research_runs/mission/2026-11-14/discovery-43600488013-1.json`.

**Candidate dossiers:** ten manually source-inspected, commit-pinned candidate records are tracked in `research/candidate-audits/`; these are a separate manual sample, not completion of the automated 7,901-row queue. Some findings remain provisional pending independent review. Examples: [Lumetra Labs Morpho liquidation](research/candidate-audits/Lumetra-Labs__morpho-liquidation-bot.md), grade C and not flash-loan funded in the reviewed primary path; [0xnavarro Aave Liquiditor](research/candidate-audits/0xnavarro__Aave-Liquiditor.md), grade D with critical wiring and accounting gaps.

**Candidate queue preparation:** the 7,901 live-discovery candidates have been stream-imported and persisted as 80 hash-verified JSONL batches (up to 100 each) under `research_runs/audit-batches/43600488013/`. The preparation workflow verified 7,901 unique names, 7,901 unique GitHub repository IDs, contiguous candidate indexes and all batch SHA-256 hashes. Each row remains `pending_commit_pinned_source_capture`; import is not an audit.

**Automated source-capture queue worker:** `flashloan-source-capture-worker` consumes the immutable manifest and all 80 JSONL batches. It verifies every batch SHA-256 and candidate index before queue import, uses SQLite leases and retry counters, pins each repository's current default-branch commit/tree and verified Git blob IDs, and writes one atomic inspection report per candidate. The default first-pass cap is 30 source files per repository; any tree/file cap is explicitly recorded as a coverage limitation. Raw verified blobs remain in the local content-addressed vault, not in Git history.

Run it from the repository root (keep the SQLite database and snapshot vault on persistent storage):

```bash
pip install -e .
flashloan-source-capture-worker \
  --manifest research_runs/audit-batches/43600488013/manifest.json \
  --database data/research.sqlite3 \
  --snapshots data/snapshots \
  --output reports/source-capture \
  --max-candidates 4 \
  --parallel 2 \
  --continuous
```

The worker resumes from SQLite after interruption and retries failed candidates up to three attempts. Set `GITHUB_TOKEN` as an environment variable when higher authenticated GitHub API limits are needed. This stage performs source acquisition only: a captured candidate is **not** semantically classified, independently reviewed, or security-audited until the model/evidence/reviewer stages run. It never executes candidate code.

**Latest verified automated source-capture checkpoint:** workflow [43630157644](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43630157644), artifact **14127627316**: **920/7,901 captured; 6,971 pending; 0 leased; 10 failed**. Of captured repositories, 673 are complete within the configured source scope and 247 have explicit coverage limitations. All 10 terminal failures are empty Git repositories returning HTTP 409, not security findings. The next source-capture run [43681829011](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681829011) restored this exact immutable artifact and began its next 12-repository batch. The primary path is GitHub-hosted and self-chaining; no WSL/local worker is required.

**Agent Form quality gate:** pilot [43627944086](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43627944086) installed Ollama qwen2.5:3b and completed 12 specialist outputs, but timed out on two roles; only one candidate reached evidence validation/review. Reports inspected had zero accepted pinned-source evidence, so the pilot was rejected and no semantic audit count increased. PR [#13](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/13) is now merged. It assigns stable IDs to pinned source signals, requires every finding to cite selected evidence IDs, rejects any fabricated ID, enforces unique task/report/commit provenance, makes zero-evidence gates fail closed, serializes CPU inference with bounded task leases, and uses a fresh mission DB for the next pilot. Three-version CI passed before merge in run [43681735442](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681735442).

**Fresh isolated pilot:** workflow [43681829089](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681829089) uses mission ID `flashloan-agent-form-pilot-20261115`, a new SQLite database, the preserved 268-candidate seed artifact, and loopback-only qwen2.5:3b with 1,200-second request timeout and bounded source context. At the last check it was installing Ollama; no pass is claimed until both candidate-purpose chains, all twelve specialists, both positive evidence gates and both independent-r4 completed two candidate-purpose tasks, twelve specialist reports and two positive evidence gates, but both independent reviewers hit the reviewer-context cap. PR #22 added a lossless compact reviewer context and a guarded reviewer-only recovery workflow. Recovery run 43693473127 is active; semantic audit count remains unchanged until the reviewer artifact is independently audited.

Start the local form and queue:

```bash
pip install -e .
flashloan-mission-api
# Open http://127.0.0.1:8765/ in your browser
```

The service binds to `127.0.0.1` only. Missions are persisted in the configured SQLite database (`FLR_DATABASE`, default `data/research.sqlite3`).


## Optional local checkpoint restore (not required for the primary workflow)

The primary source-capture continuation is GitHub-hosted and self-chaining. It restores the latest verified checkpoint, captures a bounded priority batch, validates SQLite/WAL state and source evidence, uploads a durable replacement artifact, retires only the safely superseded checkpoint, and dispatches the next batch. It does not depend on the user's laptop, WSL, a self-hosted runner or a manual command.

Latest inspected checkpoint: workflow [43630157644](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43630157644), artifact 14127627316. Queue: 920 captured / 6,971 pending / 0 leased / 10 empty-repository failures; 673 complete within configured source scope and 247 coverage-limited. The 12-repository cycle captured 12/12 successfully. The current continuation [43681829011](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43681829011) restored this exact artifact and entered the next capture batch.

The optional local restore helper `scripts/resume_source_capture.sh` remains a recovery path only. It verifies the artifact digest, SQLite integrity, manifest, report identities, commit/tree pins and Git blob SHA-1 references before restoring into a dedicated database and vault. It does not overwrite the default research database or source vault. No user-side action is needed for the primary GitHub-hosted workflow.

## Automation architecture

**Phase A:** Python deterministic engine + SQLite + GitHub Actions.

**Phase B:** LangGraph coordinates bounded specialist roles after deterministic source capture. The current local-only inference adapter accepts only loopback OpenAI-compatible endpoints; no cloud or paid fallback exists. Specialist claims remain provisional until evidence validation and independent review. No agent receives arbitrary shell, secrets, wallet, signing or deployment tools.

**Optional:** n8n may later provide visual triggers, notifications and approval UX. It is not the source of truth and is not required for correctness. n8n Community uses a Sustainable Use License, so commercial embedding/use must be reviewed separately.

## Current verification

See [`docs/PHASE_A_TEST_REPORT.md`](docs/PHASE_A_TEST_REPORT.md) and the current GitHub Actions checks. A passing unit suite verifies code behavior under fixtures; it is not an external security audit, a full semantic audit of candidate projects, or evidence of realized on-chain profit.


## Latest autonomous checkpoint (2026-11-15)

Source capture run [43691891924](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43691891924), artifact 14152633179, is independently verified at **1,112/7,901 captured**, 6,771 pending, 0 leased and 18 empty-repository HTTP 409 failures. Of captured snapshots, 802 are complete within configured scope and 310 carry coverage limits. Successor [43691988547](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43691988547) is running separately.

The r4 semantic artifact [14152481228](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43688699311) passed 2 purpose tasks, 12 specialist reports and 2 evidence gates, but both reviewers were blocked by context size. PR #22 merged the compact, lossless reviewer recovery. [Recovery run 43693473127](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43693473127) is active. No semantic audit is accepted or counted yet.


## Authoritative ground-verification checkpoint (2026-11-15 08:43 UTC)

- Locked mission unchanged: evidence-backed research over 7,901 discovered public GitHub candidates. Discovery coverage remains 28/38 query templates complete; 10 remain incomplete.
- **Latest independently downloaded source checkpoint:** run [43695633862](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43695633862), artifact 14153204517, SHA-256 `f53377a62eae4a8f758c8b67989d018a3ecc1232416eb5d1636ff143aea5e492`. SQLite integrity is `ok`; checkpoint JSON and SQLite agree: **1,171 captured / 6,711 pending / 0 leased / 19 failed**, with 845 complete within configured scope and 326 coverage-limited. The latest 12-candidate cycle captured 11 and had one empty Git repository HTTP 409. All 13,639 vault files independently match their Git blob SHA-1 paths (0 mismatches).
- Source child [43695703370](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43695703370) restored the exact parent artifact and is capturing the next 12 candidates. Source capture is demonstrably self-chaining: completed runs 43695380555, 43695481083, 43695549399 and 43695633862 each completed checkpoint upload, retired the consumed parent only after replacement, and dispatched the next child. Intermediate artifacts may disappear after their successor safely replaces them; use the newest retained artifact.
- **r4 is not accepted.** Reviewer recovery [43693473127](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43693473127) completed and uploaded artifact 14154370687 (SHA-256 `cb609e08d2e7d08e1133045a19a4dda87262f374c744c147453f790ad6d5a947`). Both reviewer decisions were `inconclusive`. Manual artifact audit: the Aave reviewer missed the wrong Pool pointer and missing callback authentication, repeated a false direct-liquidation claim and returned high confidence despite partial status/unknowns; the Uniswap reviewer correctly noticed the unimplemented `uniswapV2Call` TODO but also returned high confidence despite partial status/unknowns. Reviewer task completion is not semantic correctness. No dossier and no semantic audit count increment.
- PR [#23](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/pull/23) merged at `5bff54b556cf45d482391cefbf16de746df3f2f4`. New r5 controls: strict primary-purpose taxonomy; role-specific finding categories; non-security severity suppression; maximum four narrowly relevant evidence IDs per finding; high confidence only for implemented reports with no unknowns; seven-report purpose consensus; exact evidence excerpt/path/line/commit/tree/hash revalidation. CI [43695283729](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43695283729) and merge CI [43695350412](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43695350412) passed Python 3.11/3.12/3.13.
- Fresh r5 pilot [43695437370](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43695437370) uses new mission/database/artifact paths, qwen2.5:3b CPU-only loopback inference and immutable seed artifact 14121666814 with exact SHA-256 verification. Restore, runtime installation and fresh DAG bootstrap passed; serialized specialist/evidence/reviewer execution is in progress. No artifact or r5 acceptance is yet claimed.
- **Next gate:** inspect r5 artifact and every report. Specifically challenge Aave Pool pointer/callback authentication and Uniswap TODO/placeholder behavior. If any gate fails, repair and rerun fresh isolated pilot; do not generate dossiers or increment semantic audit count. Only after full semantic and reviewer acceptance implement dossier generation and reviewer-disagreement reconciliation, then enqueue the next persistent DAG batch.
- Safety unchanged: no candidate code execution, wallets, signing, deployment, live trading, cloud inference or paid inference.

