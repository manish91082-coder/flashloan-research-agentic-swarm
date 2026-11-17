# R15D v2 Leakage-Resistant Benchmark Design

**Status:** design-only; no reference labels exist in this public design file and no reviewer submissions have been requested.

## Why v2 exists

R15D v1 is retired after the public repository source manifest and CI fixture artifact were found to contain expected labels. The v1 packet and artifacts remain forensic evidence. V2 uses a new proposition set and must not inherit or expose the v1 answer key.

## Public design boundary

The public design contains only:
- immutable source repository/commit/tree/blob pins;
- bounded propositions, line ranges and interpretation boundaries;
- allowed label taxonomy and adjudication procedure;
- safety constraints and provenance requirements.

It contains no expected labels, reference labels, model outputs, reviewer identities, reviewer rationales or private answer-key material.

## New six-case proposition set

The six new propositions are recorded in `research_runs/r15d_v2_semantic_case_design.json`:
- NAV2-01: `onlyOwner` modifier behavior.
- NAV2-02: `executeLiquidation` parameter encoding and flash-loan call construction.
- NAV2-03: owner-only token and native-asset withdrawal behavior.
- COB2-01: constructor zero-address checks, reference assignments and fee-tier initialization.
- COB2-02: per-call minimum-profit floor selection and forwarding.
- COB2-03: direct and intermediate Uniswap V3 path-selection behavior.

These propositions are not the six v1 propositions. They are design statements, not adjudicated facts. Reviewers must determine the applicable labels from the pinned source excerpts.

## Answer-key custody

- Do not create an `expected_label` field in any public v2 file.
- Do not store a reference-label JSON, CSV, spreadsheet or manifest in the public repository, public Git history, CI artifact, workflow log or public release.
- The custodian must hold the answer-key record outside the public repository, with access restricted to the custodian until independent reviews are complete.
- Public CI artifacts may contain source excerpts, source pins, hashes and case propositions only.
- Reviewer bundles and rationales must be received privately and kept isolated from other reviewers until both primary submissions are complete.
- No model inference is permitted until independent ground truth has been completed, frozen and digest-verified.

## Build and leakage gates

Before reviewer intake:
1. Verify all six source line ranges and source blob pins.
2. Build excerpt-only artifacts with no label-bearing keys.
3. Run the leakage scanner against every generated artifact and CI output.
4. Confirm no answer-key file or label-bearing material exists in the public v2 manifest or artifacts.
5. Verify the public source manifest SHA-256 and every excerpt SHA-256.
6. Keep the v1 forensic answer key separate and do not reuse it as v2 ground truth.

## Safety

Candidate code execution, wallet access, transaction signing, deployment, live trading, paid inference and cloud inference remain disabled. V2 is a source-fact adjudication benchmark, not a vulnerability verdict or profitability certification.

## V2 fixture build and leakage scan — first CI artifact verified

- Builder: `scripts/build_r15d_v2_semantic_fixtures.py`
- Scanner: `scripts/scan_r15d_v2_artifact_leakage.py`
- CI run: [44039591500](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/44039591500)
- Artifact ID: `14308717210`
- Artifact name: `r15d-v2-label-free-fixtures-4bcf8413b4190db34105eec74aa65f50aad49322`
- Downloaded ZIP SHA-256: `d1aa9a8f3512e83c7e93a7166c46e01f5e49ed8c3bf8b6b3ca326878364894f6`
- Fixture manifest SHA-256: `52ed5fda1e28795a721b6840f8bc6655fd9255465024c84094c2881a328618e5`
- Source design manifest SHA-256: `237ca66fd71a0a3d678a97007b2414c3476e214c199f989c47fb073d2accef5b`
- CI matrix: **289 tests passed** on Python 3.11, 3.12 and 3.13.
- Python 3.11 job built the fixture, ran the leakage scanner successfully, then uploaded the artifact. Python 3.12 and 3.13 skipped artifact build/upload by design.
- Direct ZIP inspection confirmed six new case IDs, six source excerpt files, no reference-label fields, and `answer_key_included=false`. The exact forbidden-key scan found no answer-key keys.
- This is a label-free design artifact, not a ground-truth record. No reviewer submissions, consensus, freeze or model inference have occurred.

