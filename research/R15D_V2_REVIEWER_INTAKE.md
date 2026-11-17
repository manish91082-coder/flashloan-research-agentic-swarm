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
- CI run: [44041990335](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/44041990335)
- Artifact ID: `14310026292`
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

## Staged primary merge and independent verification

After both genuine primary bundles pass validation and the custodian has independently verified both identities, run:

```sh
python scripts/merge_r15d_v2_primary_reviews.py \
  --fixture <label-free-fixture-directory-or-zip> \
  --reviewer-a <private-a.json> \
  --reviewer-b <private-b.json> \
  --receipt-a <private-a-receipt.json> \
  --receipt-b <private-b-receipt.json> \
  --output <new-private-staged-packet.json> \
  --custodian-id <custodian-id> \
  --identity-verification-complete
```

The merge requires distinct reviewer IDs, preserves the fixture digest and source pins, keeps consensus pending, records disagreements, leaves the third-adjudicator slots blank except for their trigger flags, and keeps ground truth unfrozen.

Independently reconstruct and verify the staged packet:

```sh
python scripts/verify_r15d_v2_primary_merge.py \
  --fixture <label-free-fixture-directory-or-zip> \
  --reviewer-a <private-a.json> \
  --reviewer-b <private-b.json> \
  --receipt-a <private-a-receipt.json> \
  --receipt-b <private-b-receipt.json> \
  --staged-packet <private-staged-packet.json> \
  --custodian-id <custodian-id> \
  --identity-verification-complete \
  --expected-sha256 <staged-packet-digest>
```

Both commands create or verify private adjudication material. Do not commit the output packet, reviewer identities, labels or rationales to the public repository.

## Third-adjudication handoff

Only cases with different primary labels are sent to a third adjudicator. The third reviewer sees both primary records for those cases, but must not see model outputs or v1 answer-key material. The v2 schema and validator are `research/R15D_V2_THIRD_ADJUDICATION_SUBMISSION.schema.json` and `scripts/validate_r15d_v2_third_submission.py`.

```sh
python scripts/validate_r15d_v2_third_submission.py \
  --fixture <label-free-fixture-directory-or-zip> \
  --staged-packet <private-staged-packet.json> \
  --submission <private-third-review.json>
```

After custodian identity verification, create the third review receipt with `scripts/create_r15d_v2_intake_receipt.py`, using `--reviewer-slot third_adjudicator` and `--staged-packet <private-staged-packet.json>`. Verify the receipt with `scripts/verify_r15d_v2_intake_receipt.py` before finalization.

## Final consensus assembly

For a disagreement packet, the finalizer requires the third submission and its verified receipt. For a unanimous packet, omit both. The primary receipts are always required.

```sh
python scripts/finalize_r15d_v2_adjudication.py \
  --fixture <label-free-fixture-directory-or-zip> \
  --reviewer-a <private-a.json> \
  --reviewer-b <private-b.json> \
  --receipt-a <private-a-receipt.json> \
  --receipt-b <private-b-receipt.json> \
  --staged-packet <private-staged-packet.json> \
  --output <private-complete-adjudication.json> \
  --custodian-id <custodian-id> \
  --primary-identity-verification-complete \
  --third-submission <private-third-review.json> \
  --third-receipt <private-third-receipt.json> \
  --third-identity-verification-complete \
  --expected-staged-sha256 <staged-packet-digest>
```

The finalizer independently reconstructs the staged merge from both primary bundles and receipts, verifies the third receipt when required, preserves all attestation records and receipt digests, then validates consensus. It writes an unfrozen packet with model inference unauthorized.

## Separate freeze and independent verification

Freeze and verification require the original primary bundles, their receipts, the staged packet, custodian ID and (for disagreement cases) the third bundle and receipt. This prevents a caller from bypassing the receipt chain by presenting only a syntactically valid final packet.

```sh
python scripts/validate_r15d_v2_adjudication.py \
  --fixture <label-free-fixture-directory-or-zip> \
  --packet <private-complete-adjudication.json>

python scripts/freeze_r15d_v2_adjudication.py \
  --packet <private-complete-adjudication.json> \
  --fixture <label-free-fixture-directory-or-zip> \
  --output <new-private-frozen-manifest.json> \
  --frozen-at <UTC-ISO8601-timestamp> \
  --reviewer-a <private-a.json> \
  --reviewer-b <private-b.json> \
  --receipt-a <private-a-receipt.json> \
  --receipt-b <private-b-receipt.json> \
  --staged-packet <private-staged-packet.json> \
  --custodian-id <custodian-id> \
  --primary-identity-verification-complete \
  --expected-staged-sha256 <staged-packet-digest>

python scripts/verify_r15d_v2_frozen_manifest.py \
  --packet <private-complete-adjudication.json> \
  --fixture <label-free-fixture-directory-or-zip> \
  --manifest <private-frozen-manifest.json> \
  --expected-sha256 <frozen-manifest-digest> \
  --reviewer-a <private-a.json> \
  --reviewer-b <private-b.json> \
  --receipt-a <private-a-receipt.json> \
  --receipt-b <private-b-receipt.json> \
  --staged-packet <private-staged-packet.json> \
  --custodian-id <custodian-id> \
  --primary-identity-verification-complete \
  --expected-staged-sha256 <staged-packet-digest>
```

For disagreement cases, add `--third-submission`, `--third-receipt` and `--third-identity-verification-complete` to both freeze and verify commands. The freeze manifest binds exact complete-packet bytes, fixture digest, custody receipt digests, validator source, leakage scanner source and fixture builder source. The verifier reconstructs the final packet from the receipt-verified human submissions before checking the frozen transformation and expected digest. Even a verified freeze does not itself authorize model inference.

## Metadata-only custody receipt

After validation and out-of-band identity verification, create a private receipt with `scripts/create_r15d_v2_intake_receipt.py`. It records the exact submission SHA-256, fixture digest, pseudonymous reviewer ID, reviewer slot, custodian ID, timestamps and attestation summary. It deliberately excludes labels, rationales, evidence text and raw payload. Keep the receipt outside the public repository with the encrypted original bundle.
