# R15D v1 Blindness Leakage Audit

**Audit date:** 2026-11-17  
**Repository:** `manish91082-coder/flashloan-research-agentic-swarm`  
**Repository visibility:** public  
**Disposition:** R15D v1 is not eligible for blind human adjudication or blind model-quality evaluation.

## Executive finding

The six-case blind adjudication packet omits expected labels, but the public source manifest `research_runs/r15d_semantic_case_manifest.json` contains an `expected_label` for each case. The CI-generated fixture artifact `14307778314` also contains the six `expected_label` fields in `fixture_manifest.json`.

The artifact's manifest status is `built_pending_independent_adjudication`, but its labels are nevertheless present. This contradicts the blind protocol's intended separation and the packet's `expected_labels_omitted=true` invariant when the repository and associated artifacts are considered as a whole.

## Verified evidence

| Evidence | Verified value |
|---|---|
| Repository visibility | `public` |
| Public source manifest | `research_runs/r15d_semantic_case_manifest.json` |
| Source manifest Git blob | `34d15f0e7aa50b61ca127ae37aa3781c2a8c15d5` |
| Fixture artifact workflow run | `44038191152` |
| Fixture artifact ID | `14307778314` |
| Fixture artifact name | `r15d-semantic-fixtures-9e1ec0a9f42c0b8403b4166db0c5ab340f15f495` |
| Downloaded ZIP SHA-256 | `83f1665e69ede8a269b2c2d397f50bb6c1d46645fb441cf36edd7dc61e0f67b8` |
| Artifact fixture manifest SHA-256 | `2c0eb9ef589963ad48f430eeb838c416f90251a73b9ad876f201be20e6eda305` |
| Artifact-declared source manifest SHA-256 | `65aee61321efa3f759508158ac2fb803b32e798ab31488725bbeca756f4eae36` |
| Cases in artifact | 6 |
| Cases with an `expected_label` field | 6 |
| Canonical blind packet Git blob | `b9dac92fb354eea8abfddb04b68b1a2d7c9a604b` |

The downloaded ZIP was inspected directly. It contains six excerpt files and `fixture_manifest.json`; the manifest contains all six case records and an `expected_label` field on every record. The manifest's own SHA-256 matches the fixture identity already pinned in the adjudication validator.

## What this finding means

- The blind packet file itself remains unchanged and blank.
- The wider benchmark information boundary is compromised because reference labels exist in the public source manifest and the generated fixture artifact.
- No genuine primary or third-adjudicator submissions have been received in the canonical packet. Therefore actual reviewer contamination is **not observed or established**.
- It is not safe to claim the six cases are blind, to use them for blind reviewer scoring, to freeze them as independent blind ground truth, or to authorize model inference from them.
- Removing the current manifest field would not erase already published Git history or previously generated artifacts. Do not rewrite history or delete forensic evidence as a cosmetic fix.

## Immediate controls

1. Retain the original manifest, artifact and blank packet as forensic evidence.
2. Mark R15D v1 as `blinding_compromised_retired` for new blind adjudication.
3. Keep all six reviewer slots blank. Do not solicit new reviews against this v1 packet.
4. Keep production freeze disabled, model inference unauthorized and semantic audit increment at zero.
5. Create a new benchmark revision with new case propositions and a clean public/private separation:
   - public repository contains only source pins, propositions, boundaries, evidence rules and schemas;
   - expected labels are not stored in the public repository, public Git history, public CI artifacts, build logs or reviewer-facing files;
   - the reference-label key is held outside the public repository under custodian control;
   - build artifacts contain excerpts and hashes only, never expected labels;
   - reviewers receive isolated blind bundles through a private channel;
   - no model sees any case until the new ground truth is independently adjudicated, frozen and verified.
6. Add automated leakage checks that scan all reviewer-facing artifacts and CI outputs for label-bearing fields and known answer-key material.

## Safety and accounting

- Real reviewer submissions received: 0
- Custodian identity checks completed: 0
- Production adjudication merge: none
- Production ground-truth freeze: none
- Model inference authorized: false
- Semantic audit increment: 0
- Candidate code execution, wallet access, signing, deployment and live trading: false
- Paid inference and cloud inference: false

## Disposition

**R15D v1 remains a preserved engineering/forensic fixture only.** The next legitimate benchmark step is a new leakage-resistant revision, not a freeze of the current six-case packet.
