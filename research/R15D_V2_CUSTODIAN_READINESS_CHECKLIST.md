# R15D v2 Custodian Operational Readiness Checklist

**Disposition:** preparation checklist only. It does not authorize real reviewer intake.

## 1. Governance and authorization
- [ ] Name one accountable custodian and one independent backup custodian.
- [ ] Record the approved benchmark ID: r15d-semantic-source-facts-v2.
- [ ] Confirm v1 is retired and no v1 labels, answer-key material or contaminated review artifacts are used.
- [ ] Obtain explicit written authorization for the private intake window, reviewer count, deadlines and incident escalation owner.
- [ ] Keep production reviewer intake disabled until every required item below is signed off.

## 2. Reviewer eligibility and identity
- [ ] Verify primary reviewer A's real identity out of band and record the evidence privately.
- [ ] Verify primary reviewer B's real identity out of band and record the evidence privately.
- [ ] Confirm A and B are different people, have no disqualifying conflicts, and have not seen or consulted v1 answer-key material.
- [ ] Assign stable pseudonymous IDs. Do not put real names or identity documents in the repository or receipt.
- [ ] Verify the third adjudicator only if a primary disagreement occurs; they must be distinct from A and B.
- [ ] Record identity verification method and UTC time in the private custodian record, not in public CI logs.

## 3. Encrypted delivery and key custody
- [ ] Select a reviewed public-key encryption workflow (for example, age recipient keys or GnuPG public-key encryption). Do not send a symmetric passphrase through the same channel as the ciphertext.
- [ ] Verify each recipient's encryption public key through a separate trusted channel before sending any fixture or receiving any bundle.
- [ ] Keep private decryption keys on a separate custodian-controlled device or protected secret store; never place keys in the repository, CI variables, logs or shared folder.
- [ ] Test encryption and decryption with synthetic data before real intake. Verify exact SHA-256 equality after decryption.
- [ ] Use a dedicated encrypted volume or encrypted storage location outside the public repository and automatically synchronized folders.
- [ ] Apply least privilege: directory mode equivalent to 0700, file mode equivalent to 0600, restrictive umask, and no broad group/world access.
- [ ] Preserve the original encrypted submission as received. Validate and merge only working copies.
- [ ] Verify ciphertext delivery and plaintext hash over a separate authenticated channel. Do not infer delivery integrity from transport success alone.

## 4. Reviewer isolation and evidence handling
- [ ] Send the same immutable label-free fixture artifact to both primary reviewers separately.
- [ ] Confirm artifact SHA-256 and fixture-manifest SHA-256 before distribution.
- [ ] Ensure primary reviewers cannot see each other's identities, submissions, labels, rationales or evidence notes.
- [ ] Ensure no reviewer sees model predictions, model rationales or model-generated labels.
- [ ] For third adjudication, reveal both primary records only for the disagreement cases and keep model outputs hidden.
- [ ] Keep all raw submissions, decrypted copies, receipts, staged packets and final packets outside the public repository and CI artifacts.
- [ ] Disable shell tracing and avoid commands that echo private payloads or passphrases.

## 5. Receipt-bound processing
- [ ] Validate each primary bundle against the current v2 fixture before creating a receipt.
- [ ] Create separate primary_a and primary_b metadata-only receipts using the same custodian identity.
- [ ] Independently verify each receipt against exact submission bytes, fixture digest, reviewer slot and custodian ID.
- [ ] Run the v2 merge and independent staged-merge verifier.
- [ ] If disagreements exist, validate the exact disagreement-only third bundle, create a third receipt bound to the staged packet, and verify it.
- [ ] Run final consensus assembly, complete packet validation, freeze writer and independent frozen-manifest verifier.
- [ ] Preserve all receipt digests and original encrypted submissions in the private evidence store.

## 6. Stop conditions and incident response
Stop intake and quarantine affected material if:
- any reviewer identity is uncertain or duplicated;
- any reviewer has seen v1 labels, another primary review or model outputs;
- a bundle, label, rationale, receipt or key is exposed in public repository/CI/logs;
- ciphertext or decrypted SHA-256 does not match the received-byte record;
- a receipt is missing, swapped, stale, tampered or bound to the wrong reviewer slot/custodian;
- source pins, fixture manifest, evidence references or consensus validation fail;
- filesystem permissions, key custody or private-channel controls cannot be verified.

Preserve incident evidence privately. Do not repair blindness by deleting only the latest exposed copy. Replace compromised reviewers only after a fresh independent eligibility screen.

## 7. Independent approvals
- [ ] Custodian signs the identity, eligibility, encryption and access-control checklist.
- [ ] Independent security reviewer signs the key-management and storage review.
- [ ] Research lead confirms fixture digest and benchmark scope.
- [ ] A separate explicit decision authorizes genuine human intake.
- [ ] A later, separate decision authorizes model inference only after a frozen manifest is independently verified.

## Current verified boundary
The synthetic CI tabletop demonstrates the software path and OpenPGP public-key encryption/decryption round trips for three synthetic submissions. A temporary recipient fingerprint is generated; the sender imports only the public key in a separate GnuPG home; the private-key home is separate from sender/receiver working directories; decrypted bytes are checked exactly; POSIX 0700/0600 modes and temporary workspace cleanup are verified. It does not demonstrate real recipient fingerprint verification over an independent channel, separate physical-device or hardware-backed key custody, real external transport/storage, real identity proof, real reviewer independence, or operational authorization.

**Current decision:** production reviewer intake remains unauthorized; no real reviewer submissions, identity checks, receipts, merges, freeze or model inference exist.