from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path

from scripts.validate_r15d_review_submission import _unique_object
from scripts.validate_r15d_v2_review_submission import load_fixture_bundle, validate_submission
from scripts.verify_r15d_v2_intake_receipt import verify_intake_receipt


def _read_strict(path: Path, label: str):
    try:
        return json.loads(path.read_bytes().decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"{label} must be duplicate-free UTF-8 JSON: {exc}") from exc


def _fixture_manifest_bytes(fixture_path: Path) -> bytes:
    if fixture_path.is_dir():
        return (fixture_path / "fixture_manifest.json").read_bytes()
    if fixture_path.is_file() and zipfile.is_zipfile(fixture_path):
        with zipfile.ZipFile(fixture_path) as archive:
            names = [name for name in archive.namelist() if Path(name).name == "fixture_manifest.json"]
            if len(names) != 1:
                raise ValueError("fixture ZIP must contain exactly one fixture_manifest.json")
            return archive.read(names[0])
    if fixture_path.is_file():
        return fixture_path.read_bytes()
    raise ValueError("fixture path does not exist")


def _atomic_create(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
        if path.read_bytes() != payload:
            raise OSError("published staged packet differs from validated bytes")
    finally:
        temporary.unlink(missing_ok=True)


def build_staged_packet(fixture: dict, bundle_a: dict, bundle_b: dict, fixture_sha256: str, custodian_id: str) -> dict:
    by_a = {case["case_id"]: case for case in bundle_a["cases"]}
    by_b = {case["case_id"]: case for case in bundle_b["cases"]}
    if set(by_a) != set(by_b) or len(by_a) != 6:
        raise ValueError("both primary bundles must cover the exact six v2 cases")
    cases = []
    for source in fixture["cases"]:
        case_id = source["id"]
        reviews = []
        for bundle, review_case in ((bundle_a, by_a[case_id]), (bundle_b, by_b[case_id])):
            reviews.append({
                "reviewer_id": bundle["reviewer_id"],
                "label": review_case["label"],
                "rationale": review_case["rationale"],
                "evidence_references": list(review_case["evidence_references"]),
                "confidence": review_case["confidence"],
                "completed_at": review_case["completed_at"],
                "independence_attestation": True,
            })
        disagreement = reviews[0]["label"] != reviews[1]["label"]
        cases.append({
            "id": case_id,
            "repository": source["repository"],
            "commit_sha": source["commit_sha"],
            "tree_sha": source["tree_sha"],
            "path": source["path"],
            "git_blob_sha1": source["git_blob_sha1"],
            "line_start": source["line_start"],
            "line_end": source["line_end"],
            "excerpt_sha256": source["excerpt_sha256"],
            "proposition": source["proposition"],
            "boundary": source["boundary"],
            "reviewers": reviews,
            "disagreement": disagreement,
            "third_adjudicator": {
                "reviewer_id": None, "label": None, "rationale": None,
                "evidence_references": [], "confidence": None,
                "completed_at": None, "triggered": disagreement,
                "independence_attestation": None,
            },
            "consensus": {
                "status": "pending", "label": None, "rationale": None,
                "disagreement": disagreement,
            },
        })
    return {
        "schema_version": "1.0",
        "benchmark_id": "r15d-semantic-source-facts-v2",
        "status": "primary_reviews_received_pending_consensus",
        "fixture_manifest_sha256": fixture_sha256,
        "cases": cases,
        "primary_reviewer_attestations": [
            {
                "reviewer_id": bundle["reviewer_id"],
                **{key: bundle["attestations"][key] for key in ("independent_review", "model_outputs_not_seen", "other_reviews_not_seen", "v1_answer_key_not_seen", "v1_labels_not_consulted", "conflicts_disclosed", "conflict_statement")},
            }
            for bundle in (bundle_a, bundle_b)
        ],
        "third_reviewer_attestations": None,
        "custody_receipts": {
            "primary_a_receipt_sha256": None,
            "primary_b_receipt_sha256": None,
            "third_adjudicator_receipt_sha256": None,
        },
        "blinding": {
            "expected_labels_omitted": True,
            "model_outputs_omitted": True,
            "primary_reviews_completed_independently": True,
            "v1_answer_key_non_exposure_attested": True,
        },
        "custody": {
            "custodian_id": custodian_id.strip(),
            "primary_reviewer_identities_verified_out_of_band": True,
            "third_adjudicator_identity_verified_out_of_band": False,
            "identity_verification_is_custodian_attestation_not_cryptographic_proof": True,
        },
        "safety": {
            "candidate_code_execution": False,
            "wallet_access": False,
            "transaction_signing": False,
            "deployment": False,
            "live_trading": False,
            "paid_inference": False,
            "cloud_inference": False,
        },
        "freeze": {
            "ground_truth_frozen": False,
            "frozen_at": None,
            "model_inference_authorized": False,
        },
    }


def merge_primary_reviews(
    fixture_path: Path,
    reviewer_a_path: Path,
    reviewer_b_path: Path,
    receipt_a_path: Path,
    receipt_b_path: Path,
    output_path: Path,
    custodian_id: str,
    identity_verification_complete: bool,
) -> dict:
    if not identity_verification_complete:
        raise ValueError("custodian must verify both reviewer identities out of band before merge")
    if not isinstance(custodian_id, str) or len(custodian_id.strip()) < 3:
        raise ValueError("custodian_id must be a stable identifier")
    resolved = [fixture_path.resolve(), reviewer_a_path.resolve(), reviewer_b_path.resolve(), receipt_a_path.resolve(), receipt_b_path.resolve(), output_path.resolve()]
    if len(set(resolved)) != 6:
        raise ValueError("fixture, both reviewer submissions, both receipts and output must be separate paths")

    receipt_a = verify_intake_receipt(fixture_path, reviewer_a_path, receipt_a_path, "primary_a", custodian_id)
    receipt_b = verify_intake_receipt(fixture_path, reviewer_b_path, receipt_b_path, "primary_b", custodian_id)
    fixture = load_fixture_bundle(fixture_path)
    fixture_hash = hashlib.sha256(_fixture_manifest_bytes(fixture_path)).hexdigest()
    bundle_a = _read_strict(reviewer_a_path, "reviewer A bundle")
    bundle_b = _read_strict(reviewer_b_path, "reviewer B bundle")
    result_a = validate_submission(bundle_a, fixture)
    result_b = validate_submission(bundle_b, fixture)
    if not result_a["valid"]:
        raise ValueError("reviewer A bundle failed validation: " + "; ".join(result_a["errors"]))
    if not result_b["valid"]:
        raise ValueError("reviewer B bundle failed validation: " + "; ".join(result_b["errors"]))
    if result_a["reviewer_id"] == result_b["reviewer_id"]:
        raise ValueError("primary reviewer identities must be distinct")
    packet = build_staged_packet(fixture, bundle_a, bundle_b, fixture_hash, custodian_id)
    packet["custody_receipts"] = {
        "primary_a_receipt_sha256": receipt_a["receipt_sha256"],
        "primary_b_receipt_sha256": receipt_b["receipt_sha256"],
        "third_adjudicator_receipt_sha256": None,
    }
    payload = (json.dumps(packet, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _atomic_create(output_path, payload)
    disagreements = [case["id"] for case in packet["cases"] if case["disagreement"]]
    return {
        "valid_staged_merge": True,
        "output_path": str(output_path),
        "output_sha256": hashlib.sha256(payload).hexdigest(),
        "fixture_manifest_sha256": fixture_hash,
        "case_count": 6,
        "disagreement_cases": disagreements,
        "ground_truth_frozen": False,
        "model_inference_authorized": False,
        "custodian_id": custodian_id.strip(),
        "identity_verification": "custodian_attested_out_of_band_not_cryptographically_proven",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge two private R15D v2 primary reviews into a new staged packet. Does not adjudicate or freeze.")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--reviewer-a", type=Path, required=True)
    parser.add_argument("--reviewer-b", type=Path, required=True)
    parser.add_argument("--receipt-a", type=Path, required=True)
    parser.add_argument("--receipt-b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--custodian-id", required=True)
    parser.add_argument("--identity-verification-complete", action="store_true")
    args = parser.parse_args()
    result = merge_primary_reviews(args.fixture, args.reviewer_a, args.reviewer_b, args.receipt_a, args.receipt_b, args.output, args.custodian_id, args.identity_verification_complete)
    print(json.dumps(result, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
