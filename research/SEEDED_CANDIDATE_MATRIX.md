# Seeded Candidate Matrix

Status: this matrix separates historical leads from newly revalidated pins. Every present-tense source conclusion is tied to the exact commit/tree/blob pins in the candidate forensic report. A README claim or lexical source match is not proof of runtime behavior, security, test execution or profitability.

## Earlier research leads (historical; revalidation still required)

| Repository | Prior inspected commit | Prior assessment | Revalidation target |
|---|---|---|---|
| manuelinfosec/flash-arb-bot | dd89d1ccfefb4a7ec34d993ec3ee7fa27ac865f5 | B; BLOCKED_CONFIG | Aave V3 flashLoanSimple and two DEX legs; scanner startup previously failed due missing ARBITRUM_RPC_URL; optional USD route made gas/net nullable. |
| babylonlabs-io/aave-v4-bots | 5a28358f9f5c123faff099bd502f688716383933 | A for tested custom integration, not external audit | Morpho/Aave/Uniswap V4 liquidation; inspect swapDatas arbitrary calldata + allowance trust boundary. |
| leex0x0/keeper-liquidator | db2033ae48ff5f313084c74e056923ecf2213e7e | B+ | Base Sepolia staged/fork liquidation; no mainnet realized-profit evidence; absolute balance accounting. |
| obchain/Charon | d805c9cabac16bf9d32a77fa935109de59c0760a | A-/B split | Rust scanner/executor; Venus BSC evidence stronger than Aave path. |
| BowTiedDevil/degenbot | 56471478668c70001d0065b59bce0bc8cdd7c100 | B framework; not a verified flash-loan executor | General MEV/simulation framework; CI failed at inspected snapshot. |
| arksenu/liquidation-bot | 33497e570ba63cbf9fc90f79b2472ad7474b0306 | C-/blocked executor | Shared nonReentrant guard conflicts with synchronous lender callback; stored minProfitThreshold not enforced in inspected callback. |
| danywayGit/OnChainArbitrage | 1e38b593d051b0851f81e0c26eae2b756643b8ab | C prototype | Profit estimator cost/flash-fee omissions and amountOutMinimum=0. |
| tsmluky/Morpho-Blue-Liquidator-Bot | 1bc416a0dab923c53d4e1086d9c7de7cfc446d96 | B-/C+ | Absolute balance floor/dust and limited test coverage. |
| cobibean/aave-liquidator-bot | 3159c15f4dcfb0df215b4c3024f47753a1133b84 | B- | Router/config mismatch; no CI evidence at inspected snapshot. |
| alexpetrache-dev/aave-liquidator-base | fda5ff2a68a8803e40e7c6ea1ec6d22889fc8f | C prototype | Uniswap V3 flash swap, not Aave flash loan; no tests/CI at inspected snapshot. |

## Newly revalidated candidates

| Repository | Exact HEAD | Classification | Current assessment |
|---|---|---|---|
| Aquafr198/liquidator | c0970909d4fa0cbbc36a2aed3dbb7857b809e29c | Multi-protocol liquidation; Morpho flash loans for Morpho/Aave mainnet/Euler/Silo, native Aave flashLoanSimple for L2 | B-/C+ research candidate; broad contract coverage, but no B0 accounting, non-WETH minProfit is off-chain-only, fork test fixture is a no-op, no GitHub Actions run history. |
| clubytech/cluby-liquidator | 46a7d56e061db6e46389f5b731783a4183d2cb53 | Morpho Blue flash-loan liquidation with Uniswap V3 | C+ focused reference; oracle-relative output floor and one successful CI run; no B0 accounting or strictly positive net-profit floor. |
| litmajor/argus-evm | fd1a1161a62b10a431079b60812d64ba10b820bd | Native Morpho liquidation callback, not flash loan | B+ callback-accounting reference; session-bound callback and B0/collateral baseline; README says runtime wiring incomplete and executor unsafe as wired. |
| MELD-labs/meld-flashloan-liquidation-bot-public | 74653447a0ff9014f2e022d6778b442182f9841a | Legacy Aave V3 flash-loan liquidation prototype | C/blocked; executeOperation lacks Pool/initiator authentication, absolute balance accounting and dimensionally inconsistent minimum-output formula. |

## Promotion requirements

A candidate cannot be promoted based on README claims or lexical matches. Revalidation must pin:
1. Current repository metadata, default branch, exact commit SHA and tree SHA.
2. Relevant source blob SHA and exact path/line ranges.
3. Funding source and callback caller/initiator authentication.
4. Balance-baseline and actual repayment/premium invariant.
5. On-chain and off-chain net-profit gates.
6. Test code and CI history at the exact inspected commit; distinguish real fork replay from placeholders.
7. Known limitations, missing proof, contradictory evidence and operational trust boundaries.

Grades describe strength of available evidence for the stated scope, not probability of profit or production readiness.
