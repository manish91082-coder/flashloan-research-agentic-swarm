# Seeded Candidate Matrix

Status: historical research leads imported into this project baseline. Every row must be revalidated against the current default-branch commit before a present-tense conclusion is made. A source-pattern match is not proof of runtime behavior, security or profitability.

| Repository | Prior inspected commit | Prior assessment | Main finding / revalidation target |
|---|---|---|---|
| manuelinfosec/flash-arb-bot | dd89d1ccfefb4a7ec34d993ec3ee7fa27ac865f5 | B; BLOCKED_CONFIG | Aave V3 flashLoanSimple and two DEX legs; scanner runs failed at startup for missing ARBITRUM_RPC_URL. If USD route is absent, gas/net fields can be null and fallback can classify gross-positive opportunity as viable. Confirm same-block quote consistency and full-cost gate. |
| babylonlabs-io/aave-v4-bots | 5a28358f9f5c123faff099bd502f688716383933 | A for tested custom integration, not an external audit | Custom BTC vault liquidation using Morpho/Aave V3/Uniswap V4 routes; CI and fork tests passed at inspected commit. Review arbitrary router calldata and unlimited WBTC allowance through non-empty swapDatas; bot path previously used an empty list. |
| leex0x0/keeper-liquidator | db2033ae48ff5f313084c74e056923ecf2213e7e | B+ | Base Sepolia Aave V3 flash liquidation; four fork tests passed for staged/mock setup. No mainnet realized-profit evidence; absolute balance accounting and missing on-chain minimum-profit floor require review. |
| obchain/Charon | d805c9cabac16bf9d32a77fa935109de59c0760a | A-/B split | Rust scanner/executor plus liquidation contracts; Venus BSC validation scope stronger than Aave path. Check README/version drift and Aave callback accounting. |
| BowTiedDevil/degenbot | 56471478668c70001d0065b59bce0bc8cdd7c100 | B as MEV/simulation framework; not established as generic flash-loan bot | Rust MEV core, Python driver and DEX simulation coverage. CI at inspected commit failed overall with some Python/dependency checks failing. Do not classify as a flash-loan executor without new evidence. |
| arksenu/liquidation-bot | 33497e570ba63cbf9fc90f79b2472ad7474b0306 | C-/blocked executor | Entry function and synchronous Aave callback both use the same nonReentrant lock, creating a source/dependency-level callback conflict. Stored minProfitThreshold was not enforced in inspected callback. Verify if current source still matches. |
| danywayGit/OnChainArbitrage | 1e38b593d051b0851f81e0c26eae2b756643b8ab | C prototype | Profit estimator used fixed trade size/gas assumptions and did not subtract flash fee in inspected net calculation; swaps used amountOutMinimum=0; tests were smoke/TODO level. |
| tsmluky/Morpho-Blue-Liquidator-Bot | 1bc416a0dab923c53d4e1086d9c7de7cfc446d96 | B-/C+ | Morpho Blue liquidation design; inspect absolute balance profit floor/dust and CLI execution toggle before any deeper trust. |
| cobibean/aave-liquidator-bot | 3159c15f4dcfb0df215b4c3024f47753a1133b84 | B- | Gas-aware min-profit plumbing but router/config mismatch noted; no CI evidence at inspected snapshot. |
| alexpetrache-dev/aave-liquidator-base | fda5ff2a68a8803e40e7c6ea1ec6d22889fc8f | C prototype | Base Uniswap V3 flash-swap funding, not an Aave flash loan; absolute balance floor, no pre-operation snapshot, no tests/CI at inspected snapshot. |

## Promotion requirements

A candidate cannot be promoted based on README claims or lexical matches. Revalidation must pin:
1. Current repository metadata and default branch.
2. Full commit SHA and tree SHA.
3. Relevant source blob SHA and exact path/line ranges.
4. Protocol-specific callback and repayment behavior.
5. Tests/CI at the exact inspected commit.
6. Known limitations, missing proof and contradictory evidence.

Grades describe strength of available evidence for the stated scope, not probability of profit or production readiness.
