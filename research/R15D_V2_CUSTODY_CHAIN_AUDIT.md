## Synthetic custody tabletop and encrypted-delivery verification — CI passed (2026-11-17)

- The end-to-end synthetic tabletop now runs in CI and exercises fixture build, primary A/B receipt creation and verification, receipt-bound merge, independent merge reconstruction, disagreement-only third review and receipt, final consensus assembly, freeze, and independent frozen-manifest verification.
- The tabletop uses a temporary workspace outside the public repository. It verifies directory modes 0700, file modes 0600, and now checks that the temporary workspace is actually removed after the test.
- Three synthetic reviewer bundles (two primary, one third adjudicator) are passed through GnuPG AES-256 symmetric encryption/decryption. The sender plaintext is removed after encryption; the receiver copy is checked byte-for-byte against the original payload.
- CI run [44045502636](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/44045502636) passed 346 tests on Python 3.11, 3.12 and 3.13. The dedicated Python 3.11 job also completed the GnuPG tabletop and label-free fixture build/scan/upload.
- The current fixture artifact from that run is artifact ID 14311191843. ZIP SHA-256: 103dd9bc104e69b113d6120c548506d4cbe80b23806f51ac6090e68725253649. Direct ZIP inspection found six pinned excerpt files, answer_key_included=false, and zero forbidden answer-key JSON keys.
- The standalone tabletop command's repository-root import path was fixed for CI. An earlier failure was traced to the workflow setting PYTHONPATH=src while invoking a root-level scripts module; the workflow now supplies the repository root. A later GnuPG integration failure was caused by GnuPG not being installed; CI installs gnupg only in the dedicated Python 3.11 job, while other matrix jobs skip the optional GnuPG integration test.
- This synthetic pass proves software-path behavior, symmetric encryption/decryption round-trip, restrictive POSIX permissions and cleanup under the CI runner. It does not prove public-key recipient verification, real external transport, real identity, real reviewer independence, separate-device key custody or real-world storage controls.

**Operational decision:** the synthetic tabletop is complete, but production reviewer intake remains unauthorized pending a human custodian's signed readiness review. Use research/R15D_V2_CUSTODIAN_READINESS_CHECKLIST.md. No genuine reviewer submissions, identity checks, receipts, production merge/freeze or model inference exist.

---

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
