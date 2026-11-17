# R15D Reviewer Submission Intake Contract

**Status:** RETIRED FOR R15D v1. The intake implementation is preserved as engineering evidence, but this six-case answer key is exposed in the public repository and CI artifact. Do not use it to solicit genuine blind reviews. See `research/R15D_V1_BLINDNESS_LEAKAGE_AUDIT.md` and `research_runs/r15d_adjudication/r15d_state_report.json`.

## Purpose

Accept one independently completed six-case review bundle from one reviewer. Keep the original public blind packet immutable. The bundle is a private intake object, not a public repository artifact and not a ground-truth manifest.

## Confidentiality and blind separation

- The repository is public. Do not commit plaintext reviewer bundles, reviewer identities, email addresses, or reviewer rationales before both primary submissions are complete.
- Each reviewer receives only the six source-pinned propositions and the blank review instructions. They must not see model outputs, the other reviewer's work, or previous labels.
- Deliver the completed bundle to the designated custodian through a private channel. The custodian verifies the reviewer's real-world/platform identity out of band and assigns a stable, distinct `reviewer_id`.
- The validator checks the bundle's structure, pins, timestamps, evidence references and attestations. It does **not** cryptographically prove the reviewer's identity or independence; the custodian's out-of-band identity check remains a separate required control.
- If a private channel and identity check are unavailable, do not accept plaintext submissions through public issues, pull requests, commits or workflow logs.

## Bundle contract

One bundle contains exactly six cases, one for each canonical case ID. Every case must include:
- the exact immutable source pin from the blind packet;
- one allowed label: `present`, `absent`, `not_applicable`, or `unknown`;
- a non-empty bounded rationale;
- one or more unique evidence references matching the exact pinned path, inclusive line range and excerpt SHA-256;
- confidence from 0 to 1, excluding booleans;
- a timezone-aware UTC completion timestamp.

The bundle-level attestations must confirm independent work, no model-output exposure, no access to another review, and conflict disclosure. The conflict statement must say `none` or describe the disclosed conflict.

## Intake and merge sequence

1. Give reviewer A and reviewer B the same immutable blind source packet, independently.
2. Receive each six-case bundle privately. Verify identity outside the repository, then run `python scripts/validate_r15d_review_submission.py --submission <private-file>`.
3. Keep both bundles private until both are complete. Do not publish one review while the other reviewer is still working.
4. Only after both are received and the custodian has completed out-of-band identity checks, run `python scripts/merge_r15d_primary_reviews.py --reviewer-a <private-a.json> --reviewer-b <private-b.json> --output <new-private-working-packet.json> --custodian-id <custodian-id> --identity-verification-complete`. The explicit flag is a custodian attestation, not cryptographic identity proof. The tool validates both bundles, requires distinct stable reviewer IDs, preserves the blank template byte-for-byte, writes a new staged packet atomically without overwriting an existing output, and leaves consensus pending. Keep the output private.
5. Independently verify the staged packet using `python scripts/verify_r15d_primary_merge.py --reviewer-a <private-a.json> --reviewer-b <private-b.json> --merged-packet <new-private-working-packet.json> --custodian-id <custodian-id> --identity-verification-complete --expected-sha256 <merge-digest>`. This reconstructs the exact expected merge from the blank template and both private bundles and rejects any byte-level mismatch. Review the staged packet's disagreement list. Where labels disagree, obtain a third independent review privately and record it only after identity verification. Do not mark consensus adjudicated until unanimous primary labels or a valid third adjudication establish it. The final packet validator enforces the distinct third adjudicator and consensus consistency.
6. Run `python scripts/validate_r15d_adjudication.py --packet <working-packet> --require-complete`.
7. Freeze to a separate output, then run `python scripts/verify_r15d_frozen_manifest.py --packet <working-packet> --manifest <frozen-manifest> --expected-sha256 <published-digest>`.
8. Publish the frozen manifest and digest only after independent verification. Only then may the next model benchmark be considered.

## Hard stop conditions

- Any source pin or excerpt digest mismatch.
- Any duplicate/missing case, duplicate evidence reference, invalid timestamp, missing attestation or malformed record.
- Any identity uncertainty, conflict that compromises independence, or evidence that one reviewer saw another review or model output.
- Any disagreement without a distinct third adjudicator.
- Any attempt to mutate the original blank packet or run model inference before the frozen manifest is verified.

A valid bundle is not itself a consensus result. Two valid bundles create only a staged primary-review packet. They are not frozen ground truth until consensus is completed, every disagreement has a distinct third adjudicator, the final packet validator passes, the freeze is written separately and the manifest is independently verified.

## Third-adjudication handoff

When the independently verified staged merge contains disagreements, follow `research/R15D_THIRD_ADJUDICATION_INTAKE.md`. The third adjudicator sees both primary reviews for disputed cases but must not see model outputs. The third submission must cover exactly the disagreement set and must use an identity distinct from both primary reviewers. Validate it with `python scripts/validate_r15d_third_adjudication_submission.py --staged-packet <private-staged-packet.json> --submission <private-third-adjudicator.json>`. No third review is accepted for unanimous cases.

## Final assembly and freeze boundary

After all disagreement-only third submissions pass validation, use `scripts/finalize_r15d_adjudication.py` as documented in `research/R15D_THIRD_ADJUDICATION_INTAKE.md`. It creates a separate complete adjudication packet and runs the full validator, but it does not freeze ground truth or authorize inference. Keep the freeze writer unused until the resulting packet passes `python scripts/validate_r15d_adjudication.py --packet <private-final-adjudication.json> --require-complete` and the custodian authorizes the separate freeze/verification step.
