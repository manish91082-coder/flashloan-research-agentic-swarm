# R15D — Semantic Quality Gate and Reviewer Benchmark

**Status:** planned / implementation pending  
**Checkpoint:** R15C run 43868846531, artifact 14229725407  
**Canonical branch:** main  
**Immutable source seed:** run 43799361897, artifact 14196365507, SHA-256 0c28a6ead92ed6d8150cfec42f2be9c38f7742d802a580cd25c692010bb2fdad  
**Mission mode:** public-source research only

## 1. Why R15C is not accepted

R15C restored and verified the immutable source checkpoint, bootstrapped a fresh isolated mission, completed 2 candidate-purpose tasks, 12 specialist tasks and both candidate-specific evidence-validation tasks. The independent-review stage failed for both candidates. No dossier was produced and the semantic audit count did not increment.

Run 43868846531 uploaded artifact 14229725407 (SHA-256 98fdccc443072374a753ec6c3c045f859a8a0624ec901952ed4a4e7073a4cbe3). The workflow log and report identify these reviewer failures:

- `cobibean/aave-liquidator-bot`: six repetitive generic claims ("code snippet is part of a smart contract"); zero required protocol-risk topics covered.
- `0xnavarro/Aave-Liquiditor`: unrelated fixed-ETH-price and frozen-account claims; zero required protocol-risk topics covered.
- Both reviewer tasks failed semantic relevance validation. Specialist tasks and evidence-validation tasks completed without task-level failures, but that does not establish semantic correctness.

The specialist artifact itself contains warning signs: the `0xnavarro/Aave-Liquiditor` protocol specialist mostly reports generic project-description claims, while the security specialist for `cobibean/aave-liquidator-bot` emits a speculative "dead zone" exploit claim from limited excerpts. Therefore the failure is not safely attributable to reviewer model size alone. R15D must test upstream report quality and reviewer behavior separately.

## 2. Locked R15D objective

Establish a reproducible, source-pinned benchmark that can distinguish:

1. source provenance correctness;
2. specialist semantic adequacy;
3. reviewer protocol-risk coverage and factual grounding;
4. reviewer verdict calibration;
5. model/runtime constraints.

Do not increase the semantic audit count, generate candidate dossiers, or resume broad semantic processing until the benchmark's deterministic checks and independent adjudication gates pass.

## 3. Required benchmark design

### A. Freeze an immutable evaluation packet

Use the R15C artifact and its exact pinned inspection commits as evaluation inputs. Record for every fixture:
- repository full name;
- full commit SHA and tree SHA;
- exact source path and line range;
- excerpt SHA-256 and Git blob identity where available;
- source-capture artifact ID and SHA-256;
- specialist report and evidence-validation report hashes.

Never fetch a moving default branch as a substitute for the pinned source. Do not execute candidate repository code.

### B. Separate upstream specialist quality from reviewer quality

Before invoking an independent reviewer, run a deterministic pre-review adequacy gate over the specialist packet.

The gate must reject or mark insufficient:
- generic claims that do not state a protocol mechanism;
- claims without exact evidence references;
- claims whose cited excerpt does not contain the claimed mechanism;
- security claims inferred only from lexical matches or truncated excerpts;
- high confidence when material unknowns or incomplete implementation remain;
- repeated boilerplate or duplicate findings;
- candidate-purpose summaries presented as security findings.

A reviewer must receive an explicit insufficiency state when the specialist packet is inadequate. It must be allowed to return the schema-supported `inconclusive` verdict; it must not invent risks to satisfy a minimum finding count.

### C. Protocol-specific review contract

For Aave flash-loan candidates, ask the reviewer to inspect only source-supported dimensions relevant to the exact candidate, including as applicable:
- Pool / IPool / address-provider identity and wiring;
- callback entry point and caller authentication;
- initiator authentication and parameter binding;
- asset, amount and premium consistency;
- repayment balance and allowance behavior;
- liquidation execution and token-flow accounting;
- TODOs, missing implementations and reachable failure paths.

For Uniswap V2 flash-swap candidates, use a separate rubric:
- pair identity / factory validation;
- callback entry point and caller authentication;
- token ordering and amount semantics;
- repayment invariant and fee calculation;
- swap path / reserve assumptions;
- missing callback or incomplete implementation.

Do not require every dimension to be present in every repository. Mark dimensions `present`, `absent`, `not_applicable`, or `unknown` with evidence references. Absence claims require inspection coverage sufficient to support absence.

### D. Model comparison only after the evaluation harness is valid

Retain Qwen2.5 3B as the baseline. A challenger model may be added only after:
- its exact Ollama model tag and manifest are recorded;
- its model digest, parameter size, quantization and context metadata are captured;
- it can run CPU-only on the GitHub runner within the existing bounded resource/time budget;
- the same frozen packet, prompt, schema, decoding settings and validator are used for both models.

Do not assume a model is superior from its family name or published claims. Select the winner only from benchmark results. Run one model at a time with one loaded model to avoid memory contention; preserve bounded task concurrency only where safe.

## 4. Scoring and fail-closed acceptance

Report separate scores, never one blended score:

| Dimension | Measurement | Acceptance |
|---|---|---|
| Provenance | Exact commit/tree/path/line/excerpt checks | 100% |
| Claim support | Every material claim supported by cited source | 100% |
| Protocol coverage | Applicable rubric dimensions correctly assessed | All required dimensions |
| Unsupported critical claims | Adjudicated false critical claims | 0 |
| Generic / duplicate claims | Boilerplate and duplicate findings | 0 accepted |
| Unknown handling | Missing evidence explicitly marked unknown | 100% |
| Confidence calibration | Confidence consistent with evidence and unknowns | No unjustified high |
| Verdict contract | Valid structured decision and disagreement fields | 100% schema-valid |
| Runtime | Wall time, peak memory if measurable, token/context use | Within configured limits |

A reviewer may legitimately return no vulnerability findings. A clean review is not a failure when it is evidence-backed. Do not optimize for finding count.

For benchmark adjudication, preserve:
- model raw output;
- normalized output;
- deterministic validator result;
- exact input packet fingerprint;
- adjudicator rationale and evidence;
- runtime/model manifest.

No model may adjudicate its own output. Any manual adjudication must be clearly labelled as such and source-pinned.

## 5. Execution sequence

1. Download and independently verify R15C artifact 14229725407 and its SHA-256.
2. Inspect SQLite task ledger, specialist reports, evidence reports and pinned inspection excerpts.
3. Build a compact, deterministic evaluation packet from the two R15C candidates; preserve all source identities.
4. Add regression fixtures for the two observed failure classes: generic repeated reviewer claims and unrelated off-topic reviewer claims.
5. Add specialist-adequacy tests so weak specialist reports cannot be passed to reviewers as semantically complete.
6. Add reviewer rubric/schema tests, including the valid `insufficient_evidence` / `inconclusive` path.
7. Run existing CI on Python 3.11, 3.12 and 3.13.
8. Run baseline inference, then a manifest-pinned challenger only if the runner can support it without paid/cloud inference.
9. Publish a model-by-model scorecard and choose the next model/prompt correction from measured failure categories.
10. Only after benchmark acceptance, launch a fresh isolated semantic pilot with a fresh database and artifact root.

## 6. Non-negotiable safety and accounting

- Public GitHub research only.
- Candidate source code is never executed.
- No wallet, private key, signer, transaction, deployment or live-trading access.
- No paid API, paid model fallback or cloud inference.
- Model output remains untrusted until deterministic schema, provenance and semantic checks pass.
- Source capture is not semantic audit.
- Specialist completion is not semantic acceptance.
- Reviewer task completion is not correctness.
- Dossier creation and semantic audit increments occur only after all acceptance gates pass.
- Failed attempts remain immutable evidence; do not overwrite or relabel R15C as successful.

## 7. R15D exit condition

R15D is complete only when the evaluation packet is reproducible, regression tests pass on all supported Python versions, both observed R15C failure modes are caught by tests, reviewer insufficiency is handled without fabricated findings, and the baseline/challenger scorecard is backed by pinned artifacts. Until then, semantic processing remains blocked at the review gate.
