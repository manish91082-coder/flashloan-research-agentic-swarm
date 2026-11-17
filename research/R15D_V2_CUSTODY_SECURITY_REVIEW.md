# R15D v2 Reviewer Custody and Security Review

**Status:** operating procedure drafted; no real submissions or identity checks have occurred.

## Trust boundaries

- Public repository and CI artifacts may contain v2 source excerpts, immutable source pins, propositions, evidence rules, schemas and scanner output only.
- Primary reviewer bundles contain labels, rationales, confidence and evidence references. They are private records and must never enter public commits, pull requests, issues, workflow logs, public artifacts or public releases.
- Third-adjudicator bundles are private and include only disputed cases. The third reviewer may see both primary reviews for those cases, but not model outputs or v1 answer-key material.
- Real-world identity records are held separately by the custodian. The repository stores only pseudonymous reviewer IDs and a custodian attestation that an out-of-band identity check occurred.

## Required intake procedure

1. Verify reviewer identity privately and independently. Assign a stable pseudonymous reviewer ID. Reject anyone who has seen or consulted R15D v1 answer-key material.
2. Give each primary reviewer the same v2 label-free fixture artifact through separate private channels. Do not reveal another reviewer's identity, work or labels.
3. Require the signed/attested v2 bundle and receive it through an encrypted private channel.
4. Compute SHA-256 immediately on receipt. Preserve the original encrypted submission as read-only evidence; validate a working copy.
5. Generate a metadata-only intake receipt with `scripts/create_r15d_v2_intake_receipt.py`. The receipt contains hashes, pseudonymous IDs, timestamps and attestation booleans only. It must not contain labels, rationales or evidence text.
6. Store raw submissions, staged packets, receipts and identity records outside the public repository in an encrypted, access-controlled location. Use separate access controls for the custodian and the reviewers.
7. Do not merge until both primary bundles have arrived and passed validation. Preserve original bundle hashes and verify the staged merge independently.
8. Obtain a third review only for the exact disagreement set. The third reviewer must be distinct from both primary reviewers.
9. Keep all model inference disabled until a complete packet is frozen and independently verified. A freeze is not itself authorization to infer.

## Local file handling

- Use a dedicated directory outside the repository and outside automatically synchronized public/shared folders.
- On POSIX systems, use a directory mode equivalent to `0700` and file modes equivalent to `0600`; verify actual permissions after creation.
- Encrypt submissions at rest and in transit using an established open-source tool such as age or GnuPG. Keep decryption keys separate from the encrypted files.
- Do not paste raw reviewer submissions into public issues, code review, shared chat rooms or CI logs.
- Keep identity documents and real names out of the repository and out of intake receipts.
- Preserve originals; perform validation and merging on copies. Never edit a received bundle to make it pass.

## Custody receipt constraints

The metadata-only receipt must include:
- benchmark ID and fixture manifest digest;
- reviewer slot and pseudonymous reviewer ID;
- SHA-256 of the exact received submission bytes;
- submitted and custodian-verified timestamps;
- custodian ID and out-of-band identity verification status;
- v1 non-exposure, model-blindness and independence attestation booleans;
- explicit booleans that payload content, labels and rationales are not included.

The receipt is not a cryptographic identity certificate. The custodian's identity verification remains an operational control.

## Incident response

If a reviewer saw v1 answer-key material, another primary review, or model output:
- quarantine the submission;
- do not merge or use its labels;
- record a private incident receipt without exposing content;
- replace the reviewer with a newly screened independent person;
- preserve the incident evidence privately.

If any private bundle or label appears in a public repository or CI artifact, stop the benchmark, preserve the evidence, mark the affected revision compromised, and do not attempt to restore blindness by deleting only the latest copy.

## Current status

No genuine reviewer bundles, identity checks, custody receipts, staged merges, adjudication or production freeze exist. This procedure is a control design, not evidence that the controls have been exercised.

## Receipt generation

After the bundle passes the appropriate validator and the custodian has verified the reviewer's identity, create a metadata-only receipt:

```sh
python scripts/create_r15d_v2_intake_receipt.py \
  --fixture <label-free-fixture-directory-or-zip> \
  --submission <private-reviewer-bundle.json> \
  --output <private-receipt.json> \
  --reviewer-slot primary_a \
  --custodian-id <custodian-pseudonym> \
  --custodian-verified-at <UTC-ISO8601-timestamp> \
  --identity-method private_video_check \
  --identity-verification-complete
```

For a third adjudicator, use `--reviewer-slot third_adjudicator` and add `--staged-packet <private-staged-packet.json>`. The receipt generator revalidates the submission and writes only metadata and hashes. It refuses submission, staged-packet or receipt paths inside the public repository and never writes labels or rationales into the receipt.

Verify the receipt before any merge:

```sh
python scripts/verify_r15d_v2_intake_receipt.py \
  --fixture <label-free-fixture-directory-or-zip> \
  --submission <private-reviewer-bundle.json> \
  --receipt <private-receipt.json> \
  --reviewer-slot primary_a \
  --custodian-id <custodian-pseudonym>
```

For the third reviewer, use `--reviewer-slot third_adjudicator` and supply `--staged-packet`. Primary merge, staged-merge verification, finalization, freeze and frozen-manifest verification all re-check the receipt chain. A receipt is a metadata integrity record and custodian attestation, not cryptographic proof of a person's identity.

## Synthetic custody tabletop result

- CI run: [44045502636](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/44045502636)
- Script: `scripts/run_r15d_v2_custody_tabletop.py`
- The synthetic scenario completed GnuPG AES-256 symmetric encryption/decryption round trips for both primary bundles and the third bundle, primary receipt creation/verification, primary merge, independent staged-merge verification, disagreement-only third receipt, finalization, freeze and independent frozen-manifest verification. Plaintext sender-side submission copies were removed after encryption; receiver-side decrypted copies were validated.
- Temporary private workspace permissions were verified as directories `0700` and files `0600`; the workspace was removed after the run.
- The tabletop used synthetic reviewer IDs and synthetic labels only. It verifies a local encrypted-delivery round trip, not real external transfer, real human identity, independent key custody, actual custodian operations or production readiness.
- CI passed **346 tests** on Python 3.11, 3.12 and 3.13. GnuPG is installed only in the dedicated Python 3.11 job; the additional encrypted-delivery tabletop ran there. The tabletop's symmetric passphrase is held in a separate directory inside the same temporary test workspace, so this does not prove real external key custody or independent-channel security.

**Operational gate remains closed:** a successful synthetic tabletop validates software and POSIX permission behavior, not a real human review operation. The custodian must still validate encrypted transfer, identity checks, key custody and private storage before inviting genuine reviewers.
