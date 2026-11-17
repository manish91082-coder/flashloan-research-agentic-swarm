# R15D v2 Custody Chain Audit

**Audit date:** 2026-11-17  
**Disposition:** engineering pipeline implemented; production reviewer intake remains blocked pending receipt-enforced merge.

## Verified controls

- Public v2 fixture artifact is label-free and scanned before upload.
- Reviewer bundles are validated against the exact artifact, design-manifest digest, source pins and excerpt SHA-256 values.
- Primary reviewers require v1 answer-key non-exposure attestations.
- Third-review bundles are restricted to the exact disagreement set and require a distinct reviewer identity.
- Staged merge has an independent byte-for-byte reconstruction verifier.
- Final consensus assembly preserves primary and third-review attestations.
- Complete packet validator checks stable identities, evidence, consensus, safety and unfrozen state.
- Separate freeze writer and independent manifest verifier bind exact input bytes, fixture digest and toolchain source hashes.
- Metadata-only custody receipt schema and generator exist. Receipts omit labels, rationales, evidence text and raw reviewer payload.
- All current CI and end-to-end tests use synthetic data only.

## Residual finding: receipt-to-merge binding is not yet enforced

The receipt generator can create a metadata-only receipt after custodian identity attestation. However:
- `merge_r15d_v2_primary_reviews.py` currently accepts a boolean identity-verification flag and does not require primary receipt files.
- `verify_r15d_v2_primary_merge.py` reconstructs from the two bundles and fixture but does not verify their custody receipts.
- `finalize_r15d_v2_adjudication.py` accepts a third-review identity-verification flag but does not require a third receipt file.
- The staged/final packet does not yet preserve receipt hashes as a verified custody chain.

Therefore, a valid submission bundle can currently be merged by a caller who supplies the identity-verification flag without first producing or verifying the corresponding receipt. The receipt generator is useful, but it is not yet an enforced merge gate.

## Required remediation before production intake

1. Add `verify_r15d_v2_intake_receipt.py` to reconstruct and verify a receipt against the exact private submission bytes, fixture digest, reviewer slot, custodian ID, timestamp and attestation summary.
2. Require primary A and primary B receipt paths in `merge_r15d_v2_primary_reviews.py`; reject missing, mismatched, wrong-slot, wrong-custodian or stale receipts.
3. Require independent verification of both receipts in `verify_r15d_v2_primary_merge.py`.
4. Require a third-adjudicator receipt whenever a disagreement exists; verify it against the exact third bundle and staged packet before finalization.
5. Preserve receipt SHA-256 digests and receipt-slot identities in the staged and final packets; validate them before freeze.
6. Add negative tests for missing receipts, mismatched submission hashes, swapped slots, wrong custodian, tampered receipts, duplicate reviewer identity and third receipt supplied for a unanimous packet.
7. Keep identity verification explicitly documented as an out-of-band custodian control, not a cryptographic proof. If stronger proof is needed, add a separately managed digital signature over the receipt digest.

## Current state

- Genuine primary submissions: 0
- Genuine third submissions: 0
- Actual identity checks: 0
- Custody receipts created: 0
- Production merge/finalization/freeze: none
- Model inference: unauthorized
- Semantic audit increment: 0

**Decision:** Do not solicit or accept production v2 reviewer submissions until receipt-to-merge binding is implemented and passes CI. The existing receipt generator, merge/finalization tools and freeze pipeline remain engineering components under test, not an authorized operational intake system.
