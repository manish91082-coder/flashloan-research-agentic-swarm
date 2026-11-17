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
