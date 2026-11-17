# R15D Blind Ground-Truth Adjudication Protocol

**Status:** RETIRED FOR BLIND ADJUDICATION. R15D v1 has a verified answer-key leakage path through the public source manifest and CI fixture artifact. Preserve this protocol and packet as forensic evidence only. Do not solicit reviews, freeze ground truth, or run model evaluation against this six-case v1 set. See `research/R15D_V1_BLINDNESS_LEAKAGE_AUDIT.md` and `research_runs/r15d_adjudication/r15d_state_report.json`.

## Objective

Create source-grounded reference labels for the six R15D code-fact cases before any model sees the cases. This process evaluates bounded propositions, not exploitability, contract safety, or economic profitability.

## Blinding and independence

1. The blind packet at `research_runs/r15d_adjudication/blind_adjudication_packet.json` intentionally omits expected labels and all model outputs.
2. Two reviewers independently inspect the same immutable source commit/tree/blob and excerpt fingerprint. They must not see each other's labels or rationales before both submissions are complete.
3. Each reviewer records a distinct reviewer ID, label, written rationale, source evidence references, confidence (0–1), completion timestamp and an independence attestation.
4. Reviewers must disclose conflicts and must not use model output, previous candidate grades, or another reviewer's rationale as ground truth.
5. Labels are restricted to `present`, `absent`, `not_applicable`, and `unknown`. Use `unknown` whenever the bounded source and explicitly permitted dependencies do not decide the proposition.
6. If labels differ, a third independent adjudicator is mandatory. The adjudicator records a source-linked rationale and final label. If labels agree, the consensus record still requires an explicit reconciliation rationale.
7. The ground-truth record is frozen only after all six cases have two valid independent reviews, all disagreements have a valid third adjudication, and provenance checks pass.
8. Model outputs remain hidden until the frozen ground-truth manifest and its digest are published. Any later correction creates a new version and preserves the prior frozen record.

## Evidence and scope rules

- A reviewer must cite the exact pinned file, line range and relevant excerpt. The excerpt SHA-256 in the packet is a required identity check.
- NAV-02 is an absence proposition scoped only to the complete `executeOperation` body at lines 81–111. It must not be generalized to inherited code or other entry points.
- NAV-03 asks only what the constructor assigns. Whether the provider/pool address wiring is correct requires a separate dependency/API review and must not be smuggled into this code-fact label.
- COB-02 establishes only a code-level balance floor. It does not prove realized net profit after gas, fees, slippage, MEV or off-chain costs.
- A code fact is not a vulnerability verdict. Do not infer exploitability, deployment safety or profitability from this benchmark.

## Freeze acceptance checklist

- [ ] Source commit, tree, path and Git blob identities verified.
- [ ] Exact excerpt SHA-256 values match the immutable fixture artifact.
- [ ] Two distinct reviewer IDs per case with independence attestations.
- [ ] Two complete rationales and evidence references per case.
- [ ] Third adjudicator completed for every disagreement.
- [ ] Consensus label and rationale recorded for every case.
- [ ] No model output exposed before freeze.
- [ ] Frozen manifest hash recorded and immutable copy retained.

## Current state

The committed packet is deliberately blank. It is a workflow contract, not evidence that human adjudication occurred. No reviewer identities, labels, timestamps or rationales have been fabricated. Until the checklist is complete, do not run semantic inference, change dossier states, or increment semantic audit counters.
