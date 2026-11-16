# R15D Semantic Benchmark — Source-Pinned Case Design

**Status:** case design drafted; excerpt-hash generation and independent adjudication pending  
**Purpose:** evaluate source-grounded code understanding after the narrow R15D negative-control compliance gate passed  
**Safety:** static source inspection only; candidate code must never be executed

## 1. Scope and interpretation

The benchmark uses two already-frozen repositories and their exact R15C commit/tree pins. The six initial cases below are **code-fact questions**, not vulnerability verdicts. A model must distinguish:
- a behavior explicitly present in a source range;
- a behavior absent from a complete, bounded function body;
- an implementation detail whose correctness cannot be inferred without dependency/API semantics.

No claim that either repository is exploitable, profitable, deployable, or safe follows from these fixtures. Security conclusions require separate source-complete protocol adjudication.

## 2. Frozen source identities

| Candidate | Commit | Tree | Source file | Git blob |
|---|---|---|---|---|
| 0xnavarro/Aave-Liquiditor | 9197ee3002d7d9b35e9c2da324128a38f7569038 | 14de2312e96c369bcc52c9bae96215051aea22b4 | src/contracts/FlashLiquidator.sol | 32c5e42920517fa1b93540a94e5d4dd95de94e1a |
| cobibean/aave-liquidator-bot | 3159c15f4dcfb0df215b4c3024f47753a1133b84 | 1a9ee7218304b95654385fc11f255a7c5d532bc4 | contracts/AaveLiquidatorSwapRouter02.sol | daa5716e80f203ff9ba34868e4693db382774ab8 |

The Git blob identifiers are from the immutable source-capture manifest. Before a fixture is admitted, the builder must re-fetch or restore the exact blob, verify its Git blob SHA-1, and calculate SHA-256 for each exact excerpt. No moving branch is permitted.

## 3. Initial six code-fact cases

| ID | Candidate / exact range | Grounded proposition to test | Expected label | Important boundary |
|---|---|---|---|---|
| NAV-01 | FlashLiquidator.sol:81-110 | The callback function accepts asset, amount, premium, initiator and encoded params; it decodes liquidation parameters, approves the pool, calls liquidationCall, checks repayment balance and returns true. | present | Does not establish that the flash-loan callback is correctly authenticated. |
| NAV-02 | FlashLiquidator.sol:81-110 | The callback body contains no explicit require/check binding msg.sender to the configured pool or initiator to address(this). | absent | Absence is scoped to this complete function body only; do not claim absence elsewhere in inherited code. |
| NAV-03 | FlashLiquidator.sol:71-74 | The constructor initializes the base receiver with IPoolAddressesProvider(_addressProvider), then assigns pool = IPool(_addressProvider). | present | This is an assignment fact. Whether the cast/address is semantically correct requires provider/API context and separate adjudication. |
| COB-01 | AaveLiquidatorSwapRouter02.sol:191-204 | executeOperation explicitly requires msg.sender == address(aavePool) and initiator == address(this) before decoding params and calling liquidationCall. | present | Do not generalize to all external entry points. |
| COB-02 | AaveLiquidatorSwapRouter02.sol:206-243 | The callback computes amountOwed = debtAmount + premium, requiredBalance = amountOwed + floor, and reverts if debtBalance is below requiredBalance before approving repayment. | present | This proves the coded balance condition, not economic profitability after all off-chain costs. |
| COB-03 | AaveLiquidatorSwapRouter02.sol:73 | The stored `minProfit` state variable is initialized to zero. | present | This is only the declared default value; it does not establish the floor applied by every entry point. |

## 4. Required fixture structure

Each case must store:
- case ID and candidate identity;
- exact commit SHA, tree SHA, path, inclusive start/end line;
- Git blob SHA-1 and exact excerpt SHA-256;
- neutral question and expected structured answer;
- expected applicability label: present / absent / not_applicable / unknown;
- evidence rationale limited to the excerpt and explicitly identified dependencies;
- adjudicator identity class (independent human or separately governed adjudication process), adjudication timestamp and disagreement resolution;
- confidence ceiling and unknowns;
- fixture split: development or held-out test.

The exact excerpt hash is intentionally not guessed in this design note. The deterministic fixture builder must compute it from the restored pinned blob, emit the line-preserving excerpt, and freeze the resulting manifest before model inference.

## 5. Adjudication protocol

1. Two independent reviewers inspect each exact pinned source range and relevant dependency/API declarations.
2. Reviewers answer independently before seeing model output.
3. Disagreements are resolved by a third adjudicator with written source-linked rationale.
4. A claim that cannot be decided from the available pinned source is labelled unknown, not forced into present/absent.
5. Absence claims require complete function or complete declared scope, never a short lexical excerpt.
6. No adjudicator may use a model's own output as ground truth.
7. Keep held-out cases out of prompt and rubric tuning.

## 6. Scoring (separate metrics)

- exact source provenance and excerpt integrity;
- proposition classification accuracy;
- evidence-to-claim entailment;
- false-positive rate on absent propositions;
- false-negative rate on present propositions;
- unknown calibration and abstention quality;
- confidence calibration;
- protocol interpretation error rate;
- raw response/schema validity and runtime.

Do not collapse these into one score. No candidate dossier approval or semantic audit increment is authorized by this small initial suite.

## 7. Next engineering steps

1. Implement a deterministic builder that restores the frozen source-vault blobs and verifies commit/tree/blob identities.
2. Compute and freeze exact excerpt SHA-256 values, line-preserving excerpts and a manifest hash.
3. Add tests for altered source, shifted line ranges, excerpt hash mismatch, incomplete function ranges and invalid absence labels.
4. Commission independent adjudication and preserve reviewer rationales before model inference.
5. Add held-out positive/negative/unknown cases from additional pinned repositories only after this first fixture set is adjudicated.
6. Run the model only after fixture and adjudication manifests are immutable.

