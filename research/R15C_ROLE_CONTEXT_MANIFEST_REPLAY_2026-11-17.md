# R15C Role-Context Manifest Replay — 2026-11-17

## Purpose and method

This is a deterministic, model-free replay of the role-aware source-family selector against the frozen R15C inspection manifests from GitHub Actions artifact `14229725407`.

Artifact provenance:
- Workflow run: `43868846531`
- Artifact ID: `14229725407`
- ZIP SHA-256: `98fdccc443072374a753ec6c3c045f859a8a0624ec901952ed4a4e7073a4cbe3`
- The ZIP's SQLite integrity check was previously recorded as `ok`.
- Candidate inspection commit/tree pins are copied from the frozen inspection JSON and are not rewritten.

The replay applied the current deterministic role-family ordering and the current per-role file limits: three files for ordinary specialist roles and five for the independent reviewer. It did not call a model, modify the frozen packet, or create new semantic claims.

**Scope limitation:** the frozen R15C artifact contains inspection manifests and reports, but not the content-addressed source-vault blobs. Therefore this replay verifies manifest-level path selection and family coverage, not byte-level excerpt reconstruction, blob re-hashing, or model output. Full `_verified_source_context` execution against source bytes remains a separate validation task.

## Frozen candidate identities

| Candidate | Commit | Tree | Captured files | Signal count |
|---|---|---|---:|---:|
| `0xnavarro/Aave-Liquiditor` | `9197ee3002d7d9b35e9c2da324128a38f7569038` | `14de2312e96c369bcc52c9bae96215051aea22b4` | 8 | 11 |
| `cobibean/aave-liquidator-bot` | `3159c15f4dcfb0df215b4c3024f47753a1133b84` | `1a9ee7218304b95654385fc11f255a7c5d532bc4` | 30 | 84 |

## Deterministic selected paths

### Aave candidate

| Role | Selected paths (in order) | Missing required families |
|---|---|---|
| Candidate purpose | `src/contracts/FlashLiquidator.sol`; `src/index.ts`; `src/monitor/graphql.ts` | None |
| Protocol | `src/contracts/FlashLiquidator.sol`; `src/index.ts`; `src/monitor/graphql.ts` | None |
| Solidity security | `src/contracts/FlashLiquidator.sol`; `hardhat.config.ts`; `src/index.ts` | None |
| Execution | `src/contracts/FlashLiquidator.sol`; `src/index.ts`; `src/monitor/graphql.ts` | None |
| Test verification | `hardhat.config.ts` | Test source, CI workflow |
| Economics | `src/contracts/FlashLiquidator.sol`; `src/index.ts`; `src/monitor/graphql.ts` | None |
| Dependency/license | `hardhat.config.ts` | Dependency manifest, license artifact |
| Independent reviewer | `src/contracts/FlashLiquidator.sol`; `src/index.ts`; `src/monitor/graphql.ts`; `src/monitor/positions.ts`; `src/types/graphql.ts` | None |

### COB candidate

| Role | Selected paths (in order) | Missing required families |
|---|---|---|
| Candidate purpose | `contracts/AaveLiquidatorSwapRouter02.sol`; `bot.js`; `monitor/public/app.js` | None |
| Protocol | `contracts/AaveLiquidatorSwapRouter02.sol`; `bot.js`; `monitor/src/chainMetadata.js` | None |
| Solidity security | `contracts/AaveLiquidatorSwapRouter02.sol`; `bot.js`; `monitor/src/chainMetadata.js` | None |
| Execution | `contracts/AaveLiquidatorSwapRouter02.sol`; `bot.js`; `monitor/src/chainMetadata.js` | None |
| Test verification | `monitor/test/apiLogs.test.js`; `monitor/test/logParser.test.js`; `monitor/test/redact.test.js` | CI workflow, test configuration |
| Economics | `contracts/AaveLiquidatorSwapRouter02.sol`; `bot.js`; `monitor/src/chainMetadata.js` | None |
| Dependency/license | No admissible files selected | Dependency manifest, compiler/build configuration, license artifact |
| Independent reviewer | `contracts/AaveLiquidatorSwapRouter02.sol`; `bot.js`; `monitor/src/chainMetadata.js`; `monitor/src/dataStore.js`; `monitor/src/dockerClient.js` | None |

## Findings

1. **Primary COB starvation mechanism is addressed at manifest-selection level.** The Solidity contract is selected first for candidate-purpose, protocol, security, execution, economics and independent-review roles. The high-signal `bot.js` is second, not first. The contract therefore no longer loses the first bounded context slots to global lexical-signal ordering.
2. **Dependency/license is correctly fail-closed for COB.** The frozen captured-file manifest contains no admissible dependency manifest, lockfile, compiler/build configuration or license artifact. The new policy selects no files and exposes explicit missing-family coverage. It must produce zero findings, empty evidence, unknown implementation status and low confidence.
3. **Test verification is role-isolated.** It selects actual captured monitor test files only. The absence of CI workflow and test configuration is explicit. These monitor tests must not be represented as tests of the Solidity liquidation contract.
4. **Protocol/security review excludes monitor-only tests.** The selector no longer promotes generic monitoring tests into protocol-security context merely because their path contains `test/`. The COB protocol contract and runtime source occupy the available slots instead.
5. **Aave test/dependency evidence is incomplete.** Aave's captured manifest includes `hardhat.config.ts`, but no captured test source, CI workflow, dependency manifest or license artifact. The configuration may support build/dependency context, but it does not prove dependency inventory or contract test coverage.

## Acceptance status

- Manifest-level role ordering: **PASS** for the two frozen R15C candidates.
- COB Solidity contract selected before `bot.js` in protocol-critical roles: **PASS**.
- Dependency/license role receives no inadmissible COB files: **PASS** at manifest-selection level.
- Test-verification role receives test-family files only: **PASS** at manifest-selection level.
- Protocol/security reviewer excludes monitor-only tests: **PASS** at manifest-selection level.
- Exact blob re-hash and excerpt reconstruction: **NOT VERIFIED** in this replay because the frozen artifact does not contain source-vault blobs.
- New model pilot and semantic adequacy: **NOT RUN**.
- R15C historical reports: remain immutable; the prior 14/14 insufficient assessment is not changed by path-selection replay.

## Next actions

1. Add a testable source-vault replay harness that mounts or fetches the exact commit-pinned source bytes, verifies every Git blob SHA, then invokes the actual `_verified_source_context` function for each role.
2. Assert the emitted excerpt paths, line ranges, per-file character limits, total context budget, excerpt hashes and missing-family metadata.
3. Keep R15C outputs immutable; run a new isolated pilot only after this byte-level replay passes.
4. Compare new specialist claims to their cited excerpt, then run independent reviewer adequacy checks. No report is promoted merely because its provenance is valid.


## Byte-level replay result — verified 2026-11-17

**Workflow:** [R15C Role Context Byte Replay run 44074313870](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/44074313870)  
**Implementation commit:** `a4504cc6ac56950c2fe68f28b96ea8aeb3a66f28`  
**Replay artifact ID:** `14324256232` (`r15c-role-context-byte-replay`)  
**Replay report SHA-256:** `dba554a73769895be4dbef79cced4ab8539a6b4cb0c3f4eab88a79886eb11e8d`  
**Replay result:** PASS; model inference used: false.

The harness fetched all source files from the exact frozen candidate commits, verified Git blob SHA-1 for every file, reconstructed the content-addressed vault, and invoked the actual `_verified_source_context` for all eight roles on both candidates.

| Candidate | Source files fetched and blob-verified | Total bytes |
|---|---:|---:|
| Aave | 8 | 23,167 |
| COB | 30 | 297,202 |
| **Total** | **38** | **320,369** |

### Byte-level assertions passed

- Every fetched source file matched its frozen Git blob SHA-1.
- Actual excerpt paths matched the deterministic role shortlist.
- Every excerpt's blob pin and SHA-256 matched the verified source/actual excerpt.
- Inclusive line ranges were valid.
- Unique source-file counts respected role `max_files`.
- Aggregate per-file character budgets and total context budgets were respected.
- Role admissibility held for every emitted excerpt.
- COB Solidity protocol contract was first for candidate-purpose, protocol, security, execution, economics and independent-review roles.
- COB dependency/license emitted zero excerpts and reported all three required source families missing.
- COB test verification emitted only monitor test files and explicitly reported missing CI/test configuration.
- COB independent reviewer emitted no monitor-only tests.
- Aave test verification emitted only the captured Hardhat config and explicitly reported missing test source and CI workflow.

The output artifact was downloaded and inspected independently. It records two candidates, 38 verified source files, exact excerpt paths/ranges/hashes and role-family coverage.

## Latest Research Engine CI

[Run 44074385730](https://github.com/manish91082-coder/flashloan-research-agentic-swarm/actions/runs/44074385730) passed on Python 3.11, 3.12 and 3.13. The standard-library suite reports 355 tests passed. The Python 3.11 synthetic R15D v2 custody tabletop passed.

## Revised acceptance status

- Manifest-level role ordering: **PASS**.
- Exact commit-pinned source fetch and Git blob SHA-1 verification: **PASS, 38/38 files**.
- Actual `_verified_source_context` byte-level replay across 16 candidate/role combinations: **PASS**.
- Excerpt line ranges, hashes and per-file/total budgets: **PASS**.
- Model inference during replay: **NOT USED**.
- Fresh model pilot after repair: **NOT RUN**.
- Historical R15C specialist report adequacy: unchanged; the previous 14/14 insufficient assessment remains the baseline.
- Full mission lifecycle, autonomous continuation/restart and 72-hour soak: **NOT PROVEN**.
- 24x7 production acceptance: **NOT GRANTED**.

## Next action

Proceed to a fresh isolated model pilot only after checking the repository's current pilot runner and model-provider availability. Use a new mission ID, SQLite database and artifact root. Keep the frozen R15C packet read-only. Compare the new seven specialist outputs per candidate to the actual excerpt evidence, role-specific adequacy, reviewer challenge and persisted decision lifecycle. No R15D v2 adjudication or benchmark inference is authorized by this replay.
