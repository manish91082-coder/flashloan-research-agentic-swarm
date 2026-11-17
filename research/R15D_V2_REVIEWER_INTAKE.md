# R15D v2 Private Reviewer Intake Protocol

**Status:** schema and validator are being prepared; no genuine v2 reviewer submissions have been received.

## Eligibility and v1 contamination control

R15D v1 is retired because its expected labels were exposed in the public repository and a CI artifact. V2 uses six new propositions and a label-free fixture artifact. Reviewers must:
- be real individuals whose identities are verified out of band by the custodian;
- have no prior exposure to the R15D v1 answer key or v1 reference labels;
- attest that they have not consulted the v1 label-bearing source manifest or fixture artifact;
- work independently and not see model outputs or another primary review;
- disclose conflicts of interest.

A reviewer who has seen or consulted the v1 answer key is not eligible for this v2 blind panel. These attestations are not cryptographic proof; the custodian must assess reviewer eligibility and identity privately.

## Public fixture artifact

The current label-free fixture is published as a GitHub Actions artifact only after the CI leakage scanner passes:
- CI run: [44039885278](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/44039885278)
- Artifact ID: `14308727443`
- Benchmark: `r15d-semantic-source-facts-v2`

The artifact contains six pinned source excerpts, propositions, boundaries and SHA-256 digests. It contains no reference labels. Verify the artifact with the current `scripts/scan_r15d_v2_artifact_leakage.py` before distributing it.

## Private submission contract

One primary reviewer supplies one JSON bundle containing exactly six cases. Each case must include:
- the exact source pin and excerpt SHA-256 from the v2 fixture artifact;
- one label from `present`, `absent`, `not_applicable`, or `unknown`;
- a non-empty rationale;
- unique evidence references to the exact pinned excerpt;
- confidence from 0 to 1, excluding booleans;
- a timezone-aware UTC completion timestamp;
- case-level independence attestation.

The bundle-level attestations must confirm independent work, no model-output exposure, no other-review exposure, no v1 answer-key exposure, no consultation of v1 labels and conflict disclosure.

## Validation

Extract the artifact ZIP into a private working directory, then run:

```sh
python scripts/validate_r15d_v2_review_submission.py \
  --fixture <extracted-label-free-fixture-directory> \
  --submission <private-reviewer-bundle.json>
```

The validator re-runs the artifact leakage scanner, verifies the v2 design-manifest digest, checks all six source pins and excerpt byte/hash values, then validates the reviewer bundle. It does not verify real-world identity or prove independence.

## Custody and merge

- Receive reviewer A and reviewer B bundles through separate private channels.
- Verify both identities and v1 non-exposure independently.
- Keep both submissions private until both are complete.
- Do not commit submissions, identities, rationales or reviewer IDs to the public repository or CI logs.
- V2-specific staged merge, third-adjudication and finalization tooling must be completed and tested before production intake begins.
- No ground-truth freeze or model inference is allowed until independent reviews and all disagreement adjudications are complete, followed by a separate freeze and digest verification.

## Safety

No candidate-code execution, wallet access, transaction signing, deployment, live trading, paid inference or cloud inference is authorized by this intake protocol.
