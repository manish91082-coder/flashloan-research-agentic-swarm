# Specialist Context Engine Repair — 2026-11-17

## Scope and baseline

This repair follows the frozen R15C source-context forensic checkpoint. The observed failure pattern was that a high-signal, large off-chain bot file could dominate the globally signal-ranked source list, leaving protocol-specific Solidity files outside the bounded specialist context. A dependency/license specialist also emitted execution-oriented claims, showing that prompt-only role restrictions were insufficient.

The R15C packet remains immutable. This repair does not change its findings, does not authorize R15D v2 inference, and does not authorize execution of candidate code, wallet access, signing, deployment or trading.

## Implemented changes

1. Added `src/flashloan_research/role_source_policy.py`.
   - Defines deterministic, role-specific source families for candidate purpose, protocol, Solidity security, execution, test verification, economics, dependency/license and independent review.
   - Returns a coverage record listing required, present and missing source families.
   - Orders source manifests by role family priority and deterministic path order.
   - Exposes role-to-source admissibility for evidence citations.

2. Integrated role-aware ordering in `specialist_runner._verified_source_context`.
   - The task role is now passed into context construction.
   - Existing content-addressed blob SHA verification is preserved.
   - A per-file character budget prevents the first selected file from consuming the entire shared context budget.
   - The role source coverage record is supplied to the model as explicit context.

3. Added deterministic cross-role evidence restrictions.
   - Dependency/license findings cannot cite bot execution or protocol contract paths.
   - Test-verification findings must cite test, CI or test-configuration/runtime source families.
   - Existing exact evidence ID, commit/tree and excerpt hash checks remain in place.

4. Added regression tests for:
   - Solidity contract priority over a high-signal bot file.
   - Dependency manifest and license priority.
   - Test and CI source priority.
   - Explicit missing-family reporting.
   - Unknown role fail-closed behavior.
   - Rejection of dependency/test findings citing inadmissible paths.

## CI status and known correction

The first CI attempt exposed a test expectation defect: the execution specialist uses the role-family name `execution_contract`, not the generic `protocol_contract`. The implementation ordering itself selected the Solidity contract first. The assertion was corrected to check the role-specific family name.

The latest CI run for the corrected test commit must be read from GitHub Actions before this repair can be called green. A push-triggered CI run is not considered passed until all Python 3.11, 3.12 and 3.13 jobs complete successfully.

## Remaining validation

- Confirm the corrected full CI matrix passes.
- Add end-to-end role-specific source-context tests using a fixture with an oversized `bot.js`, Solidity contract, manifests, tests and license file.
- Run the frozen R15C candidates through the new deterministic context selector without model inference; compare selected paths and per-role coverage against the previous context.
- Only then run a fresh isolated model pilot with a new mission/database/artifact root.
- Re-run adequacy and claim-to-excerpt checks; do not treat provenance as semantic correctness.
- Update the operational readiness audit with the exact code HEAD and latest CI evidence.

## Acceptance boundary

This is a code-level repair batch, not operational acceptance. It does not prove that all 14 prior specialist reports are now adequate, that a full mission completes, that autonomous continuation/restart works, or that the system is 24x7 production-operational. R15D v2 human adjudication remains independently gated.


## Follow-up refinement and latest CI result

- Tightened source-family selection so unmatched paths are excluded from role context rather than appended as a fallback.
- Removed generic runtime sources from the test-verification role's admissible families. Test verification now receives only test sources, CI workflows and test configuration.
- Filtered the evidence catalog and captured-file inventory by role admissibility before model invocation. Post-generation validation remains in place as a second independent barrier.
- Updated the deterministic semantic-pipeline fixture: when a candidate has no dependency manifests/build/license files or test/CI files, the corresponding role receives no excerpts, no evidence catalog and no captured-file inventory. Its correct result is zero findings, empty evidence, unknown implementation status and low confidence.
- Added assertions that source-starved roles receive no inadmissible content, and updated the corrective-retry fixture to cite a test path for the test-verification role.

**Latest verified CI:** run [44073293999](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/44073293999), HEAD `e7ef78ae6e58a9b8764965b3dc9cff0056c77212`. Python 3.11, 3.12 and 3.13 all passed; the standard-library suite reports 353 tests passed. The Python 3.11 R15D v2 synthetic custody tabletop also completed successfully as part of the workflow.

**Important:** the 353-test result and synthetic custody tabletop validate the software and fixture path only. They do not establish specialist semantic adequacy, a complete autonomous mission, genuine human reviewer identity, R15D v2 production intake, or 24x7 operational acceptance.
