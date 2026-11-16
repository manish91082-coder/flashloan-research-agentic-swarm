# R15D Challenger Benchmark Protocol — Qwen3.5 4B

**Date:** 2026-11-16  
**Baseline:** Qwen2.5 3B, failed reviewer-compliance fixture  
**Challenger:** Qwen3.5 4B  
**Status:** Inference completed; both frozen negative-control decisions were `inconclusive`. Initial acceptance gate rejected the artifact due to a verifier path collision, not a model decision failure. Verifier fix and same-basename regression test committed; dedicated CI added, pending execution. No broad reviewer-quality or production-readiness claim.

## Immutable challenger identity

- Tag: `qwen3.5:4b`
- Ollama digest: `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`
- Quantization: `Q4_K_M`
- Parameter size: `4.2B`
- Model size: `3,324,173,934` bytes
- Reported model context: `262144`
- Pin-discovery artifact ID: `14248935964`
- Pin-discovery artifact SHA-256: `f857347f60035334927d3c543305b9102944b5da5e6059bc3e6754c6b675c06c`
- Pin-discovery workflow: [43912378709](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43912378709)
- Pin-discovery performed no inference.

## Frozen test inputs

The challenger receives the exact two reviewer packets from R15C. Source commit/tree pins and reviewer input fingerprints must match the Qwen2.5 3B baseline:

| Repository | Commit | Tree | Reviewer input SHA-256 |
|---|---|---|---|
| `0xnavarro/Aave-Liquiditor` | `9197ee3002d7d9b35e9c2da324128a38f7569038` | `14de2312e96c369bcc52c9bae96215051aea22b4` | `f6468df676243cbcdc5bc603683d65d2980086b1345a3696a9cf63a36c2fa2d4` |
| `cobibean/aave-liquidator-bot` | `3159c15f4dcfb0df215b4c3024f47753a1133b84` | `1a9ee7218304b95654385fc11f255a7c5d532bc4` | `b8bf978a506fb0cceeaba33d4cbd99a7f55c1146645775678e3de23bc17c6ef4` |

Both frozen specialist packets are intentionally classified `insufficient`. They are a negative-control fixture for reviewer instruction compliance, not a claim that the candidate repositories are unsafe.

## Controlled runtime

- GitHub-hosted CPU-only runner.
- Local Ollama loopback only.
- One model loaded; one reviewer task at a time.
- Request context budget: 16,384 tokens, held equal to baseline.
- Maximum output: 2,400 tokens, held equal to baseline.
- Reviewer prior-report context budget: 18,000 characters, held equal to baseline.
- Same prompt-template version: `5.6.0-r15d-adequacy-and-exchange-capture`.
- Same R15C SQLite checkpoint, copied to a new isolated challenger database.
- No candidate code execution, wallet access, signing, deployment, live trading, paid inference, or cloud inference.

The larger context reported by Qwen3.5 is deliberately not used to enlarge the request budget. This preserves the controlled comparison.

## Acceptance gate

A challenger benchmark is accepted only if:

1. Exactly two reviewer outcomes are present.
2. Both source commit/tree pins match.
3. Both input packet fingerprints match the baseline exactly.
4. Both packets remain classified `insufficient`.
5. The model itself returns `review_decision=inconclusive` for both.
6. Raw exchange file, request and response fingerprints verify.
7. Both candidate dossiers remain pending and semantic audit increment remains zero.
8. All prohibited execution and financial actions remain false.

A workflow may complete inference and upload its evidence while the acceptance step fails. That is an expected fail-closed outcome, not a reason to discard the result.

## Interpretation limits

Two frozen cases measure a narrow capability: obeying the evidence-adequacy boundary and refusing to approve an inadequate packet. Passing is necessary but not sufficient for protocol-review quality. It does not establish broad reasoning capability, vulnerability detection accuracy, or production readiness.

After this benchmark, any broader semantic quality evaluation must use separately defined and independently adjudicated positive/negative cases. No candidate dossier or semantic audit increment is authorized by this challenger run alone.

## Capture-protocol rerun — revision 2

- The initial challenger inference run `43913169300` completed both reviewer tasks and the model returned `inconclusive` for both inadequate packets. Its acceptance gate failed because the verifier at that historical workflow revision rejected the raw exchange artifact; the archived artifact is retained unchanged as forensic evidence (artifact `14248019054`, SHA-256 `a596abcd93101fb1507db1abdcfcc33a36c09f389534f1e999b8fc1e21e3c830`).
- Direct inspection of that archived ZIP confirmed the exchange files' outer SHA-256 values matched their report metadata, but the old exchange payloads had no `request_raw` field. The prior artifact therefore cannot satisfy the corrected exact-request audit and must not be retroactively altered.
- The exact request capture implementation is now present in the provider, and the verifier's raw/parsed request checks plus five additional negative regression cases passed CI on Python 3.11, 3.12 and 3.13. Dedicated verifier run: [43922437902](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43922437902). General repository CI: [43922437984](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43922437984).
- A new capture-protocol-only rerun is triggered with revision 2. It preserves the exact Qwen3.5 4B digest, frozen source commit/tree pins, packet hashes, request context (16,384) and output cap (2,400). No model-quality retuning is intended.
- Trigger commit: `b49759a6df918bbf35dd7b29eb75347e36d2ee4c`; workflow validation update: `0ac3a1ce6e1af6930c1ded1caaf6411a3dbb6362`.
- Acceptance remains conditional on independent artifact verification. Both dossiers remain pending and semantic audit increment remains zero. No candidate code execution, wallet access, signing, deployment, live trading, paid inference or cloud inference.

## Revision 2 forensic result and revision 3 completion-integrity rerun

- Revision 2 workflow [43924552748](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43924552748) restored and verified the immutable source vault, R15C packet, and exact Qwen3.5 4B digest; both reviewer tasks ran and the artifact was uploaded.
- Artifact `14256136974`, SHA-256 `b83fd56f2d30316f4ba2577261fb484c85b8e374f5b5add2cc07315cd84bf9bf`, is retained unchanged.
- Independent inspection verified both raw exchange outer hashes, exact `request_raw` parsing and request SHA-256, and response SHA-256. One reviewer response ended with `finish_reason=length`; its JSON was truncated and could not yield a valid model decision. The other response ended normally and returned `inconclusive`.
- This is a model-output completion failure, not a request-capture failure. The first response must not be coerced to `inconclusive`; no semantic acceptance is allowed.
- Hardened the verifier to derive the decision from the raw response envelope, require `finish_reason=stop`, parse a complete JSON object, and compare any report-side parsed output with the raw response. Added a regression test for `finish_reason=length`.
- Revision 3 increases only the maximum output ceiling from 2,400 to 4,096 tokens; request context remains 16,384, same model digest, same source pins, same packets and same prompt template. This is explicitly a completion-integrity rerun, not a controlled quality comparison.
- Verifier commit: `02ed5098bee35c1ef245a8e9447fe58c04bb412e`; truncation regression commit: `bd65309014ce776c1e61d8e5d1fadf2e49bed829`; workflow commit: `dba0278c21b3fa36b3e1f46e028c8f03b54ab71c`; trigger commit: `d1d630f6e43676e8402601141c309144f8a07294`.
- Acceptance remains fail-closed. Dossiers pending, semantic audit increment zero, no candidate code execution, wallet, signing, deployment, live trading, paid inference or cloud inference.

## Verifier hardening regression repair — current checkpoint

- First CI attempt exposed a syntax error in the new truncated-response test fixture; a follow-up run exposed two fixture consistency defects (response body did not match the report's parsed output, and the truncated fixture did not update both embedded and report response hashes).
- These were test-fixture issues, not a relaxation of the verifier. The fixture now emits the decision supplied to each test and the truncation test updates raw response, embedded response hash, report response hash and outer exchange-file hash coherently.
- Latest dedicated verifier CI: [43928167221](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43928167221), all Python 3.11/3.12/3.13 jobs passed.
- General repository CI [43928167286](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43928167286) was still running at checkpoint.
- Latest fixture repair commit: `af0df0d40834092735ace7f98f000a79ae731012`.
- Revision 3 workflow run `43927768598` did not reach inference: test syntax compilation failed before the benchmark. Its tiny artifact is not a benchmark result.
- Do not trigger revision 4 until general CI is green. Then update workflow/trigger revision and rerun the exact pinned benchmark with output ceiling 4,096.

## Revision 4 launched after green verifier and repository CI

- Dedicated verifier regression CI run `43928167221`: all three Python versions passed.
- General repository CI run `43928167286`: all three Python versions passed.
- The intervening revision 3 workflow `43927768598` failed at compileall before any inference because it checked out the earlier malformed test fixture. Its 979-byte artifact is not a benchmark.
- Revision 4 trigger requires verifier/test CI to be green, uses exact same Qwen3.5 4B digest, same R15C and source-vault artifacts, same frozen source pins and input packet hashes, same 16,384 context and 4,096 output cap.
- Revision 4 workflow: [43928314376](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43928314376). At checkpoint, benchmark job had started; final restoration/inference/acceptance/artifact status is pending.
- Workflow commit: `15d53b26fd78a88b97637ee0966eb3f9bac6345e`; trigger commit: `88d83dfc0609c4595184ab69fc68c0f94d336815`.
