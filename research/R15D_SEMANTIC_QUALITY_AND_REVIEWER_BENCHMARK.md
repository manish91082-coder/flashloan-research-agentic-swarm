# R15D — Semantic Quality Gate and Reviewer Benchmark

**Status:** initial reviewer and specialist-adequacy gates implemented; frozen evaluation packet and model benchmark pending  
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

## 8. Implementation checkpoint — 2026-11-16 15:08 UTC

The first R15D code tranche is committed on `main`:

- `cab14d8927cbaf49decf5e56e7612e87adbdcf7e`: permit evidence-bounded inconclusive review when protocol topic coverage is insufficient; remove forced relevance retries; only exact `accept` completes the reviewer task.
- `ea91a24e40c92baaf591ac1a6b507fefbb06c2b8`: remove mandatory Aave reviewer finding slots and make protocol topic labels optional.
- `3aeb2f48f3ebcd10a9d7a17c31c24806770a3b1a`: align the end-to-end fixture with fail-closed inconclusive review behavior.
- `f0781bfb32237af72ed3ea034e711ec77fce8f15`: add deterministic specialist report and packet adequacy triage before independent review.
- `d952769e7ae456200fda8e3dcd5dfa762f0cdaf6`: extract and enforce the packet-level reviewer decision policy.
- `3a6e836b45165a81b3fddff2f2013534c7295806`: require role-specific technical anchors to overlap the exact cited source excerpt.
- `d302a901db0b47e3624a01f27d83fbb541aa2aa1`: add regression coverage for cited-excerpt anchor mismatch.

### Implemented behavior

1. Each of the seven task-pinned purpose/specialist reports is assessed for generic boilerplate, minimum claim substance, role-relevant technical language, accepted evidence-reference linkage, and overlap between a role-specific technical anchor and the exact cited evidence excerpt.
2. A packet-level status is computed. If any report is insufficient, the independent reviewer receives the explicit packet status and must return `inconclusive`. A non-inconclusive verdict is rejected before task completion.
3. Reviewer protocol-topic coverage is no longer forced by a fixed finding count. Low coverage is valid only with an explicit `inconclusive` decision.
4. Only exact `accept` can complete an independent-review task. `accept_with_reservations`, `reject`, and `inconclusive` remain non-accepted outcomes.
5. Regression tests cover boilerplate rejection, role-topic mismatch, missing cited-excerpt anchor, packet-level fail-closed behavior, mandatory inconclusive verdict, and the end-to-end blocked-review path.

### Verification

- Adequacy gate CI run: [43893065834](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43893065834)
- Commit: `d302a901db0b47e3624a01f27d83fbb541aa2aa1`
- Python 3.11: **153 tests passed**
- Python 3.12: **153 tests passed**
- Python 3.13: **153 tests passed**
- All three matrix jobs succeeded.
- Reviewer raw-exchange capture and fingerprint tests passed in CI run [43894208083](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/43894208083).
- Frozen artifact manifest: `research/R15C_EVALUATION_PACKET_MANIFEST.json`; artifact SHA-256 `98fdccc443072374a753ec6c3c045f859a8a0624ec901952ed4a4e7073a4cbe3`.
- Baseline model manifest pinned from R15C: `qwen2.5:3b`, digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`, Q4_K_M, 3.1B parameters, reported context 32,768.

### Frozen R15C adequacy replay

The normalized R15D deterministic adequacy logic was replayed against all 14 immutable R15C specialist reports:

- **14/14 insufficient**, 0/14 adequate for adversarial challenge.
- Both seven-report candidate packets are insufficient.
- Reason counts: 29 findings lack a role-relevant technical mechanism; 6 findings lack a shared role-specific anchor in the exact cited excerpt.
- CamelCase normalization is included, so identifiers such as `healthFactor` can match prose such as “health factor”.
- This does not mean every underlying source finding is false. It means the specialist reports and their cited excerpts do not meet the deterministic pre-review adequacy contract. R15C remains unchanged and is not retroactively relabelled.

### Reproducible reviewer exchange capture

The local provider now retains the exact request body, request SHA-256, raw OpenAI-compatible response envelope and response SHA-256. The independent-review worker writes this exchange to the mission artifact root before semantic validation, including task ID, repository, pinned commit/tree, model identity, prompt-template version and specialist-packet adequacy state. Thus a rejected reviewer response is preserved for audit rather than reduced to a log preview. This capture is restricted to the local loopback model provider; no cloud inference path is introduced.

### Limitation — do not overstate this gate

The specialist adequacy gate is deterministic lexical/evidence-reference triage, not a semantic theorem prover. Shared role-specific tokens in a claim and excerpt do not prove that the claim is true. The independent reviewer still has to inspect full pinned source context, and the frozen evaluation packet still needs independent adjudication. The gate is designed to detect obvious boilerplate, off-topic claims and citation mismatch early, and to force uncertainty rather than false approval when specialist input is inadequate.

### Exact next sequence

1. Build the frozen R15C evaluation packet from artifact 14229725407; verify the artifact SHA-256, SQLite integrity, task ledger, report hashes and exact source pins.
2. Add the two R15C failure classes as immutable regression fixtures and score the new deterministic gates against them.
3. Verify model manifests and runner limits before any challenger inference; keep Qwen2.5 3B as baseline and use one model loaded at a time.
4. Run baseline reviewer benchmark on the same frozen packet; retain raw outputs, normalized reports, packet fingerprints, model manifests and validator outcomes.
5. Only add a challenger if its exact model digest/quantization/context and CPU-only runner feasibility are verifiable.
6. Publish separate provenance, claim-support, protocol-coverage, false-critical-claim, unknown-handling, confidence and runtime scores.
7. Do not launch a fresh semantic pilot or increment audit counts until the benchmark and independent adjudication gates pass.

## 9. R15D exit condition

R15D is complete only when the evaluation packet is reproducible, regression tests pass on all supported Python versions, both observed R15C failure modes are caught by tests, reviewer insufficiency is handled without fabricated findings, and the baseline/challenger scorecard is backed by pinned artifacts. Until then, semantic processing remains blocked at the review gate.
