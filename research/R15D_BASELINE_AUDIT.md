# R15D Frozen-Packet Baseline Audit

**Date:** 2026-11-16  
**Mission:** `flashloan-agent-form-pilot-20261116-r15c`  
**Baseline workflow run:** [43896051809](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43896051809)  
**Workflow conclusion:** `success`  
**Benchmark acceptance:** **FAILED**  
**Artifact:** `r15d-reviewer-baseline-43896051809` (ID `14239836369`)  
**Artifact SHA-256:** `dae45c06414deb8553bc2573e48c6aec2e5137fc5dbe63b52bc5a183746190b5`

## Executive finding

The workflow completed its infrastructure and inference steps, but the reviewer benchmark did **not** meet its acceptance contract. Both specialist packets were deterministically classified `insufficient`, while Qwen2.5 3B returned `review_decision=accept` for both. This is direct model instruction-following failure on the frozen adversarial fixture. The independent-review tasks remained failed, both candidate dossiers remained pending, and semantic audit increment remained zero.

Do not describe this as a successful reviewer benchmark. It is a successful reproducibility/inference run and a failed model-quality acceptance run.

## Frozen inputs and reproducibility

- Baseline model: `qwen2.5:3b`
- Digest: `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`
- Quantization: `Q4_K_M`
- Reported context: 32,768
- Configured request context: 16,384
- Maximum output tokens: 2,400
- Prompt template: `5.6.0-r15d-adequacy-and-exchange-capture`
- Inference endpoint: local loopback Ollama (`127.0.0.1`)
- Source-vault restore: `checkpoint_restored_and_verified`
- Restored source inventory: 7,901 items; 50,268 unique Git blobs verified; 64,449 Git blob references verified.
- Original R15C artifact and database were not modified. The reviewer replay used a separate copied database.

## Candidate outcomes

| Repository | Pinned commit | Packet adequacy | Raw model decision | Result |
|---|---|---|---|---|
| `0xnavarro/Aave-Liquiditor` | `9197ee3002d7d9b35e9c2da324128a38f7569038` | insufficient | accept | rejected by deterministic review gate |
| `cobibean/aave-liquidator-bot` | `3159c15f4dcfb0df215b4c3024f47753a1133b84` | insufficient | accept | rejected by deterministic review gate |

### Failure signatures

- `0xnavarro/Aave-Liquiditor`: the model returned six generic operational/documentation claims (fixed ETH price, edge cases, environment validation, deployment errors, tests and documentation) rather than the required source-grounded protocol challenge. It also returned low confidence and seven opaque disagreement IDs. The deterministic topic gate found no covered protocol-risk groups.
- `cobibean/aave-liquidator-bot`: the model repeated the same generic statement about a DeFi smart-contract snippet across six findings. The deterministic topic gate found no covered protocol-risk groups.

The packet-adequacy policy was included in the reviewer prompt. The model nevertheless emitted `accept` for both insufficient packets. The runtime then failed the tasks closed; it did not create dossiers or increment the semantic audit count.

## Exchange evidence

- `0xnavarro` exchange SHA-256: `9997c54d775d0848d023ca5caeb055596bfcfc1a97c4353a81c28595b0ef2f04`
  - Request SHA-256: `062b942f7f7d01d143e808fafecf78b2eb747c64b45d33980b0541d7db873383`
  - Response SHA-256: `0ec330a59a28730f3e7b91e48eba1be4e4156fd2c0a42033c497718d76968b40`
- `cobibean` exchange SHA-256: `0c4a3aed254f41b6f61d2d4a454d475d292dc8054363737418ec768c1be37998`
  - Request SHA-256: `b8bf978a506fb0cceeaba33d4cbd99a7f55c1146645775678e3de23bc17c6ef4`
  - Response SHA-256: preserved in the raw exchange JSON and benchmark report.

The ZIP contains the isolated SQLite database, both source inspection packets, both raw model exchanges, the benchmark report, source-restore verification, and the exact Ollama model manifest.

## Safety and accounting

- Candidate source code executed: **no**
- Wallet access / transaction signing: **no**
- Deployment / live trading: **no**
- Paid or cloud inference: **no**
- Dossiers: **pending**
- Semantic audit increment: **0**

## Engineering correction applied after the failed baseline

The first baseline workflow reported job-level success when the benchmark report itself had `both_model_decisions_inconclusive=false`. That status ambiguity is now closed by a separate fail-closed acceptance verifier:

- `scripts/verify_r15d_reviewer_benchmark.py`
- `tests/test_r15d_benchmark_acceptance_gate.py`
- The workflow now runs the verifier before its artifact-upload step. Artifact upload remains `if: always()`, so rejected benchmark evidence is retained.
- The verifier checks both inadequate-packet decisions, both raw exchange file hashes, raw request and response fingerprints, safety/accounting invariants, and zero semantic-audit increment.
- It does not rewrite or normalize a model's `accept` into `inconclusive`; the model's actual decision remains the benchmark result.

The verifier and workflow gate are committed. CI is running against the latest changes; do not mark the new gate verified until the matrix completes.

## Next sequence

1. Confirm the latest Python 3.11/3.12/3.13 CI matrix passes.
2. Run the acceptance verifier against the downloaded frozen artifact and confirm it rejects this baseline for the correct model-decision reason.
3. Preserve this Qwen2.5 3B result as the baseline failure fixture. Do not rerun identical inference just to change the workflow badge.
4. Only after the verifier and regression tests pass, evaluate a separately pinned CPU-feasible challenger against the identical two packets and scoring rubric.
5. Do not create candidate dossiers or increment semantic audit until a reviewer returns a valid, source-grounded decision and all acceptance gates pass.
