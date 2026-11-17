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
- NAV2-01: the `onlyOwner` modifier's sender-to-owner equality guard.
- NAV2-02: the receiver, asset and amount arguments supplied to `flashLoanSimple`.
- NAV2-03: the native-asset balance transfer performed by `withdrawETH`.
- COB2-01: the constructor's zero-address guard for `_aavePool`.
- COB2-02: the ternary selection of the larger stored/per-call minimum-profit floor.
- COB2-03: the direct-pair fee-tier branch in `_resolveSwapPath`.

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

## V2 atomic proposition fixture and leakage scan — CI verified

- Builder: `scripts/build_r15d_v2_semantic_fixtures.py`
- Scanner: `scripts/scan_r15d_v2_artifact_leakage.py`
- CI run: [44039885278](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/44039885278)
- Artifact ID: `14308727443`
- Artifact name: `r15d-v2-label-free-fixtures-b8e01f699fae9a8d13dd0af361c795e89261bc8d`
- Downloaded ZIP SHA-256: `ab510711134b10a8a51dd366c1a4cf4e2329629d5c4651a42475b8765cb32f23`
- Fixture manifest SHA-256: `8c7e461c9d08f9e328f34195d431b59031f2f235e44cb5a3e2527739ffaf94b8`
- Source design manifest SHA-256: `51c8cc5ecaa1b97164654d7bb6bf5b367a59936de6da5405c32aee48be034f07`
- CI matrix: **289 tests passed** on Python 3.11, 3.12 and 3.13.
- Python 3.11 built the fixture, passed the leakage scanner, then uploaded it. Python 3.12 and 3.13 skipped build/upload by design.
- Direct ZIP inspection confirmed exactly six atomic case IDs (`NAV2-01` through `COB2-03`), six excerpt files, six excerpt SHA-256 values, and zero forbidden answer-key JSON keys. `answer_key_included=false`.
- The earlier v2 artifact `14308717210` is superseded because its propositions were broader; the current artifact uses the narrowed atomic propositions.
- This artifact is a source-pinned reviewer fixture, not a reference-label or ground-truth record. No reviewer submissions, consensus, freeze or model inference have occurred.

