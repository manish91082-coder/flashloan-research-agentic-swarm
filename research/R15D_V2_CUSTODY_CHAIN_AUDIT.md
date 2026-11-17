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

## Receipt-to-merge binding remediation — implemented and CI verified

The original gap is closed in the current code path:

- Added `scripts/verify_r15d_v2_intake_receipt.py`. It revalidates the exact private submission bytes, fixture digest, reviewer slot, custodian ID, attestation summary and receipt digest.
- `scripts/merge_r15d_v2_primary_reviews.py` now requires separate primary-A and primary-B receipts. It rejects missing, swapped, wrong-custodian, stale or tampered receipts before writing the staged packet.
- `scripts/verify_r15d_v2_primary_merge.py` independently verifies both receipts and reconstructs the staged packet byte-for-byte.
- `scripts/finalize_r15d_v2_adjudication.py` requires a third receipt whenever a disagreement exists, verifies it against the exact third submission and staged packet, and preserves its digest.
- Staged and final packets preserve the two primary receipt SHA-256 digests and the optional third receipt digest. Validators enforce their shape and disagreement-dependent presence.
- `scripts/freeze_r15d_v2_adjudication.py` now requires all primary bundles, receipts, staged packet and (when needed) third bundle/receipt. Before freezing, it reconstructs the complete final packet by rerunning the receipt-verified finalizer and requires byte-for-byte equality.
- `scripts/verify_r15d_v2_frozen_manifest.py` performs the same receipt-verified reconstruction before checking the frozen manifest, toolchain hashes and expected output digest.
- Negative tests cover missing, swapped, wrong-custodian and tampered receipts, plus missing/tampered third receipts and freeze-time reconstruction.

## Remaining operational trust controls

- Out-of-band identity verification is still a custodian operation, not a cryptographic identity proof. The receipt records that attestation; it cannot independently prove the human's identity.
- File encryption, private-channel transfer, actual filesystem permissions, key custody and reviewer separation are documented operational controls. CI cannot prove that a real custodian executed them.
- No genuine reviewers, identity checks or production receipts exist. Synthetic tests prove software behavior only.

**Disposition:** the code-level receipt-to-merge gap is closed. Production reviewer intake remains unauthorized until a custodian completes a synthetic tabletop of the private transfer/identity workflow, confirms encrypted storage and access controls, and explicitly authorizes genuine human intake. No model inference or semantic audit increment is permitted before a real v2 freeze and independent verification.

## Current state

- Genuine primary submissions: 0
- Genuine third submissions: 0
- Actual identity checks: 0
- Custody receipts created: 0
- Production merge/finalization/freeze: none
- Model inference: unauthorized
- Semantic audit increment: 0

**Decision:** Do not solicit or accept production v2 reviewer submissions until receipt-to-merge binding is implemented and passes CI. The existing receipt generator, merge/finalization tools and freeze pipeline remain engineering components under test, not an authorized operational intake system.
