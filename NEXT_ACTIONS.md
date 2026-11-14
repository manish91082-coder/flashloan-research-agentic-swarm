# Next Actions: Flash Loan & Liquidation Repository Research

## Locked mission

Discover the broadest reproducible set of public GitHub repositories across all 11 families in `research/keyword-taxonomy.json`, with explicit emphasis on flash-loan-powered DeFi liquidation and related liquidator bots. For every candidate, explain actual purpose, implementation completeness, correctness, security, economics, tests, dependencies, license and research usefulness from commit-pinned evidence.

## Completed checkpoint

- Public canonical repository and main branch verified.
- Mission Form, local API and SQLite queue exist.
- Mission objective and taxonomy v1.0.0 are now explicit in the form and repository.
- Intake schema accepts selected keyword families, taxonomy version, page size and page limit.
- Fresh CI is required for the taxonomy and intake changes.

## Priority 0: make taxonomy drive discovery

1. Load `research/keyword-taxonomy.json` as the single source of query-family identifiers, terms and repository-search query templates.
2. Implement an orchestrated query runner: 100 results/page, 10 pages/query by default, bounded retries, rate-limit reset handling and per-query completion metadata.
3. Persist the coverage ledger: query, family, page, total_count, returned count, duplicate count, API status, truncation/cap and incomplete reason.
4. Deduplicate by stable repository ID and canonical full name; distinguish forks/mirrors from independent implementations.
5. Add tests for pagination, duplicate merging, API caps, rate limits, malformed payloads and resumability.

## Priority 1: autonomous DAG and task persistence

6. Build idempotent mission task DAG: director -> query-family discovery -> dedup -> candidate purpose triage -> candidate-specific specialist tasks -> evidence validation -> independent review -> synthesis -> continuation.
7. Persist task status, dependency links, attempts, lease expiry, budgets, outputs, provenance and checkpoints in SQLite.
8. Implement worker claiming, safe retries, crash recovery and automatic next-batch continuation.
9. Add status/report endpoints and a mission progress dashboard.

## Priority 2: specialist repository forensics

10. Purpose classification for every candidate before quality grade.
11. Protocol/callback audit, liquidation mechanics, repayment/premium accounting and balance-delta invariant.
12. Execution/MEV and net economics: gas, DEX fees, slippage, liquidity, relay/builder costs and quote freshness.
13. Tests, CI, dependency/license, provenance and maintenance assessment.
14. Independent reviewer gate and evidence completeness validator.

## Priority 3: coverage completion and synthesis

15. Process all discovered repositories in bounded batches until planned search families are exhausted or external limits are explicitly recorded.
16. Produce candidate matrix, individual dossiers, security findings, evidence register, protocol architecture map, test/CI report, economic assumptions report and next research queue.
17. Mark repository purpose/quality as unknown where evidence is insufficient; never infer correctness from names, stars or README claims.

## Non-negotiable constraints

- Mission Form remains the primary intake; no manual per-agent prompting as normal operation.
- Agentic orchestration is the product; scanners are tools within the swarm.
- Public read-only research; no candidate code execution, wallets, keys, signing, deployment, broadcast or live trading.
- No paid services or paid inference fallback.
- Claims require commit-pinned source evidence and independent review where security-critical.
