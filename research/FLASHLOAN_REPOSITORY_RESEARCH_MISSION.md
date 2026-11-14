# Flash Loan & DeFi Public Repository Research Mission

## North-star mission

Discover the broadest reproducible set of **public GitHub repositories** that implement, support, monitor, simulate, test, document or discuss flash loans and closely related DeFi systems. The mission explicitly includes **flash-loan liquidation and liquidation bots**, flash-loan arbitrage, lending/borrowing protocols, DEX liquidity routes, MEV/searcher infrastructure, callback standards, protocol integrations and supporting tooling.

For every candidate, determine from pinned source and tests what the repository is actually for, what it really implements, what is missing or only claimed, whether important logic is correct, what security weaknesses or economic assumptions exist, and whether the project is useful as a reference.

This is not merely a repository-name search and not a scanner-only project. It is a form-driven autonomous research swarm that discovers, investigates, cross-checks, records evidence, independently reviews findings and continues the research queue.

## Discovery query families

The canonical, versioned query taxonomy is `research/keyword-taxonomy.json`. It contains:
- Flash-loan terms and spelling variants: flash loan, flashloan, flash-loan.
- Provider standards and callbacks: Aave `flashLoan` / `flashLoanSimple` / `executeOperation`; Balancer `receiveFlashLoan`; ERC-3156 `onFlashLoan`; Morpho and Uniswap flash callbacks.
- Liquidation: Aave `liquidationCall`, Compound `liquidateBorrow`, Comet `absorb`, Morpho liquidator, collateral seizure, health factor, close factor and bad debt.
- Flash-loan-powered liquidation combinations.
- DEX, cross-DEX and triangular arbitrage.
- MEV, Flashbots, bundles, private mempool, backrun, builder and relay systems.
- Lending/borrowing protocols and DEX/liquidity ecosystems.
- Callback authentication, repayment, premium, balance-delta, approvals, slippage and profit invariants.
- Cross-chain, chain-specific, language/tooling and tutorial/research variants.

Search each query independently, paginate to the documented limit, preserve total_count/page counts, deduplicate by stable repository identity, and record rate-limit, indexing, permission, 1,000-result search cap, and pagination gaps. A single search page is never considered complete coverage. Search results are candidates, not proof that a repository implements the feature.

## Repository classification

Every candidate must receive one purpose label:
- Complete flash-loan implementation
- Flash-loan provider/SDK
- Flash-loan arbitrage bot
- Flash-loan liquidation bot
- Liquidation bot without flash loans
- Protocol/core contracts
- Monitoring/searcher
- Simulation/test harness
- Tutorial/example
- Research prototype
- Incomplete/placeholder
- Fork/mirror
- Unrelated false positive
- Purpose unverified

The dossier explains the actual entrypoints, call flow, assets, chain, protocol/version, transaction path, operational dependencies and claimed versus implemented capabilities. Forks and mirrors are linked to likely upstreams and not counted as independent implementations unless material changes are established.

## Per-repository audit

1. Pin repository metadata, default branch, commit SHA and tree SHA.
2. Inventory source files and record capture limits.
3. Read README, docs, manifests, source, tests, workflows and release/activity metadata.
4. Trace actual entrypoints and callback/repayment/liquidation/arbitrage paths.
5. Check callback caller and initiator authentication; token/asset/amount binding; replay/state/reentrancy risks.
6. Verify repayment principal + premium and protection against pre-existing token balances satisfying a profit check.
7. Inspect liquidation eligibility, health factor, close factor, debt/collateral denomination, seize/bonus arithmetic and oracle assumptions.
8. Inspect swaps, route selection, quote freshness, amountOutMin/slippage, approvals, gas, MEV, builder/relay and failed transaction costs.
9. Recompute expected net profit only where source data and assumptions support it. Never treat a README claim or test stub as realized profit.
10. Review test quality, CI, fork tests, fuzzing, dependency versions, license, maintenance and provenance.
11. Record positive, negative and unresolved evidence. An absence claim requires a documented complete search of the relevant source scope.

## Research judgement

Avoid a simplistic “good/bad” score. Separate:
- implementation completeness;
- functional correctness supported by tests/source;
- security posture;
- economic viability;
- operational readiness;
- research/reference value;
- evidence confidence.

Use explicit statuses such as promising reference, correct with limitations, partially implemented, incorrect/broken, security-critical risk, economically unproven, abandoned, not relevant and insufficient evidence. Findings require exact file path, line range, commit/blob provenance, impact, preconditions and independent review. Preserve disagreements.

## Autonomous swarm workflow

Mission Form -> Research Director -> query-family DAG -> paginated GitHub discovery -> identity deduplication -> metadata/purpose triage -> commit-pinned repository inspection -> conditional Security / Protocol / Liquidation / Execution / Economics / Testing / Dependency specialists -> deterministic evidence validator -> independent reviewer -> dossier + candidate matrix + evidence register -> automatically queued next batch.

Agents work in bounded tasks with explicit dependencies, retry budgets and resumable checkpoints. Agent/model outputs are untrusted until schema and source-evidence validation. No repeated user prompting of individual agents is part of the normal workflow.

## Acceptance criteria

- Search coverage manifest records every query, page, result count, completion state and limitations.
- Each unique repository is assigned a purpose/status or explicitly marked unresolved.
- Every substantive claim is linked to commit-pinned source evidence.
- Each candidate gets a purpose dossier before any “good/bad” conclusion.
- Security and economic claims are reviewed independently.
- Candidate code is never executed.
- Missing source, tests, quotes, costs or evidence remains explicitly unknown.
- Discovery continues until all planned query families are paginated or blocked by a recorded external limit; remaining coverage debt is visible.

## Fixed safety boundary

Public-source research only. No wallet/private-key/signer access, candidate code execution, transaction signing, deployment, transaction broadcast, live trading, or paid service/model fallback.
