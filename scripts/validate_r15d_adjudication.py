from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET = ROOT / "research_runs/r15d_adjudication/blind_adjudication_packet.json"
ALLOWED = {"present", "absent", "not_applicable", "unknown"}
EXPECTED_CASES = {"NAV-01", "NAV-02", "NAV-03", "COB-01", "COB-02", "COB-03"}
EVIDENCE_RE = re.compile(r"^(?P<path>.+):(?P<start>[1-9][0-9]*)(?:-(?P<end>[1-9][0-9]*))?#sha256:(?P<sha>[0-9a-f]{64})$")
EXPECTED_ARTIFACT = {
    "artifact_id": 14262528859,
    "artifact_zip_sha256": "264e121033653d4c19566433c9a2f522176952adcb319fa3c7550967cc4bfb6a",
    "manifest_sha256": "2c0eb9ef589963ad48f430eeb838c416f90251a73b9ad876f201be20e6eda305",
}
EXPECTED_PINS = {
    "NAV-01": ("0xnavarro/Aave-Liquiditor", "9197ee3002d7d9b35e9c2da324128a38f7569038", "14de2312e96c369bcc52c9bae96215051aea22b4", "src/contracts/FlashLiquidator.sol", "32c5e42920517fa1b93540a94e5d4dd95de94e1a", 81, 111, "5f8ff797cf26a007c55f881f18525385f95d96abec21dabd4ebbdc5323ac1db2"),
    "NAV-02": ("0xnavarro/Aave-Liquiditor", "9197ee3002d7d9b35e9c2da324128a38f7569038", "14de2312e96c369bcc52c9bae96215051aea22b4", "src/contracts/FlashLiquidator.sol", "32c5e42920517fa1b93540a94e5d4dd95de94e1a", 81, 111, "5f8ff797cf26a007c55f881f18525385f95d96abec21dabd4ebbdc5323ac1db2"),
    "NAV-03": ("0xnavarro/Aave-Liquiditor", "9197ee3002d7d9b35e9c2da324128a38f7569038", "14de2312e96c369bcc52c9bae96215051aea22b4", "src/contracts/FlashLiquidator.sol", "32c5e42920517fa1b93540a94e5d4dd95de94e1a", 71, 74, "36a6f1bb80d8f530620294d0d490cd63aaf15688c85bb25454cf017049211ffb"),
    "COB-01": ("cobibean/aave-liquidator-bot", "3159c15f4dcfb0df215b4c3024f47753a1133b84", "1a9ee7218304b95654385fc11f255a7c5d532bc4", "contracts/AaveLiquidatorSwapRouter02.sol", "daa5716e80f203ff9ba34868e4693db382774ab8", 191, 204, "9d35f17a6f8f688a2549fc78fa6fd59550a5e11e675c341d47c05aaa007ec266"),
    "COB-02": ("cobibean/aave-liquidator-bot", "3159c15f4dcfb0df215b4c3024f47753a1133b84", "1a9ee7218304b95654385fc11f255a7c5d532bc4", "contracts/AaveLiquidatorSwapRouter02.sol", "daa5716e80f203ff9ba34868e4693db382774ab8", 206, 243, "fa52b7179aff62497e4ec4416443c9325094c17ea2e0499f8f371134d8ae26c3"),
    "COB-03": ("cobibean/aave-liquidator-bot", "3159c15f4dcfb0df215b4c3024f47753a1133b84", "1a9ee7218304b95654385fc11f255a7c5d532bc4", "contracts/AaveLiquidatorSwapRouter02.sol", "daa5716e80f203ff9ba34868e4693db382774ab8", 73, 73, "eb45789c4bb160055dcc0dc23ba204d5151ba0bbd05b61b62186ff050f55de1d"),
}


def _valid_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed)
    except ValueError:
        return False


def _review_complete(review: object) -> bool:
    if not isinstance(review, dict):
        return False
    confidence = review.get("confidence")
    return (
        isinstance(review.get("reviewer_id"), str)
        and bool(review["reviewer_id"].strip())
        and isinstance(review.get("label"), str)
        and review["label"] in ALLOWED
        and isinstance(review.get("rationale"), str)
        and bool(review["rationale"].strip())
        and isinstance(review.get("evidence_references"), list)
        and bool(review["evidence_references"])
        and isinstance(confidence, (int, float))
        and not isinstance(confidence, bool)
        and 0 <= confidence <= 1
        and _valid_timestamp(review.get("completed_at"))
        and review.get("independence_attestation") is True
    )


def _has_pinned_evidence(case: dict, review: dict) -> bool:
    references = review.get("evidence_references")
    if not isinstance(references, list) or not references:
        return False
    for reference in references:
        if not isinstance(reference, str):
            return False
        match = EVIDENCE_RE.fullmatch(reference.strip())
        if not match or not (
            match.group("path") == case.get("path")
            and match.group("start") == str(case.get("line_start"))
            and (match.group("end") or match.group("start")) == str(case.get("line_end"))
            and match.group("sha") == case.get("excerpt_sha256")
        ):
            return False
    return True


def validate(packet: object, require_complete: bool = False) -> dict:
    errors: list[str] = []
    if not isinstance(packet, dict):
        return {"valid": False, "complete": False, "completed_cases": 0, "case_count": len(EXPECTED_CASES), "errors": ["packet must be a JSON object"]}
    if packet.get("packet_type") != "blind_ground_truth_adjudication":
        errors.append("packet_type must identify the blind ground-truth adjudication packet")
    if packet.get("status") != "pending_independent_review":
        errors.append("packet status must remain pending_independent_review before freeze")
    if packet.get("benchmark_id") != "r15d-semantic-source-facts-v1":
        errors.append("unexpected benchmark_id")
    if packet.get("created_from_fixture_artifact") != EXPECTED_ARTIFACT:
        errors.append("fixture artifact identity or digest does not match frozen baseline")
    blinding = packet.get("blinding")
    if not isinstance(blinding, dict):
        errors.append("blinding must be an object")
        blinding = {}
    for flag in ("expected_labels_omitted", "model_outputs_omitted", "reviewers_must_not_consult_model_outputs", "reviewers_must_work_independently"):
        if blinding.get(flag) is not True:
            errors.append(f"blinding invariant must remain true: {flag}")
    freeze_state = packet.get("freeze")
    if not isinstance(freeze_state, dict):
        errors.append("freeze must be an object")
        freeze_state = {}
    if freeze_state.get("ground_truth_frozen") is not False:
        errors.append("ground_truth_frozen must remain false before adjudication freeze")
    if freeze_state.get("reviewer_output_visibility") != "hidden_until_freeze":
        errors.append("reviewer outputs must remain hidden until freeze")
    if freeze_state.get("model_inference_authorized") is not False:
        errors.append("model inference must remain unauthorized")
    cases = packet.get("cases")
    if not isinstance(cases, list) or {c.get("id") for c in cases if isinstance(c, dict)} != EXPECTED_CASES or len(cases) != len(EXPECTED_CASES):
        errors.append("case set must contain exactly the six frozen R15D case IDs")
        cases = cases if isinstance(cases, list) else []

    complete_count = 0
    for case in cases:
        cid = case.get("id", "<missing>") if isinstance(case, dict) else "<invalid>"
        if not isinstance(case, dict):
            errors.append(f"{cid}: case must be an object")
            continue
        expected = EXPECTED_PINS.get(cid)
        actual = (case.get("repository"), case.get("commit_sha"), case.get("tree_sha"), case.get("path"), case.get("git_blob_sha1"), case.get("line_start"), case.get("line_end"), case.get("excerpt_sha256"))
        if expected is None or actual != expected:
            errors.append(f"{cid}: immutable source pin does not match frozen R15D fixture baseline")
        reviews = case.get("reviewers")
        if not isinstance(reviews, list) or len(reviews) != 2:
            errors.append(f"{cid}: exactly two independent reviewer slots required")
            continue
        for index, review in enumerate(reviews):
            if not isinstance(review, dict):
                errors.append(f"{cid}: reviewer slot {index + 1} must be an object")
        complete = [_review_complete(review) for review in reviews]
        ids = [review.get("reviewer_id").strip() for review in reviews if isinstance(review, dict) and isinstance(review.get("reviewer_id"), str)]
        if all(complete) and len(set(ids)) != 2:
            errors.append(f"{cid}: reviewer IDs must be distinct")
        for index, review in enumerate(reviews):
            if isinstance(review, dict) and review.get("reviewer_id") and not complete[index]:
                errors.append(f"{cid}: reviewer {index + 1} submission is pending or invalid; verify required fields and UTC completion timestamp")
            if complete[index] and not _has_pinned_evidence(case, review):
                errors.append(f"{cid}: reviewer {index + 1} evidence references must all match exact pinned path/range/excerpt SHA-256")
        if any(complete) and not all(complete):
            errors.append(f"{cid}: partial reviewer submission; both reviews must be complete")
        if all(complete):
            labels = [review["label"] for review in reviews]
            disagreement = labels[0] != labels[1]
            third = case.get("third_adjudicator")
            if disagreement:
                if not _review_complete(third):
                    errors.append(f"{cid}: disagreement requires a complete independent third adjudication")
                else:
                    if third["reviewer_id"].strip() in ids:
                        errors.append(f"{cid}: third adjudicator must be distinct from both reviewers")
                    if not _has_pinned_evidence(case, third):
                        errors.append(f"{cid}: third adjudicator evidence references must all match exact pinned path/range/excerpt SHA-256")
            consensus = case.get("consensus")
            if not isinstance(consensus, dict) or consensus.get("status") != "adjudicated" or not isinstance(consensus.get("label"), str) or consensus.get("label") not in ALLOWED or not isinstance(consensus.get("rationale"), str) or not consensus["rationale"].strip():
                errors.append(f"{cid}: consensus must be adjudicated with an allowed label and written rationale")
            elif consensus.get("disagreement") is not disagreement:
                errors.append(f"{cid}: consensus disagreement flag does not match reviewer labels")
            elif not disagreement and consensus.get("label") != labels[0]:
                errors.append(f"{cid}: consensus label must match unanimous reviewer labels")
            elif disagreement and _review_complete(third) and consensus.get("label") != third.get("label"):
                errors.append(f"{cid}: consensus label must match third adjudicator label")
            else:
                complete_count += 1
        elif require_complete:
            errors.append(f"{cid}: independent reviews are pending")
    safety = packet.get("safety")
    if not isinstance(safety, dict):
        errors.append("safety must be an object")
        safety = {}
    for key in ("candidate_code_execution", "wallet_access", "transaction_signing", "deployment", "live_trading", "paid_inference", "cloud_inference"):
        if safety.get(key) is not False:
            errors.append(f"safety invariant must remain false: {key}")
    complete = complete_count == len(EXPECTED_CASES) and not errors
    if require_complete and not complete:
        errors.append("ground truth is not eligible for freeze")
    return {"valid": not errors, "complete": complete, "completed_cases": complete_count, "case_count": len(EXPECTED_CASES), "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate R15D independent adjudication records; never creates labels.")
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = validate(json.loads(args.packet.read_text(encoding="utf-8")), args.require_complete)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
