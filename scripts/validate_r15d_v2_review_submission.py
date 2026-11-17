from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

from scripts.build_r15d_v2_semantic_fixtures import EXPECTED, FORBIDDEN_KEYS, MANIFEST, _check_no_answer_key, git_blob_sha
from scripts.scan_r15d_v2_artifact_leakage import scan_artifact
from scripts.validate_r15d_adjudication import EVIDENCE_RE, _valid_timestamp
from scripts.validate_r15d_review_submission import _unique_object

ROOT = Path(__file__).resolve().parents[1]
TOP_FIELDS = {"schema_version", "benchmark_id", "reviewer_id", "submitted_at", "attestations", "cases"}
ATTESTATION_FIELDS = {"independent_review", "model_outputs_not_seen", "other_reviews_not_seen", "conflicts_disclosed", "conflict_statement"}
CASE_FIELDS = {"case_id", "source_pin", "label", "rationale", "evidence_references", "confidence", "completed_at", "independence_attestation"}
PIN_FIELDS = {"repository", "commit_sha", "tree_sha", "path", "git_blob_sha1", "line_start", "line_end", "excerpt_sha256"}
ALLOWED = {"present", "absent", "not_applicable", "unknown"}
REVIEWER_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{3,128}$")


def load_fixture_bundle(path: Path) -> dict:
    scan_target = path if path.is_dir() or (path.is_file() and zipfile.is_zipfile(path)) else path.parent
    scan = scan_artifact(scan_target)
    if not scan["valid"]:
        raise ValueError("fixture artifact failed answer-key leakage scan: " + "; ".join(scan["findings"]))

    if path.is_dir():
        manifest_bytes = (path / "fixture_manifest.json").read_bytes()
        read_entry = lambda name: (path / name).read_bytes()
    elif path.is_file() and zipfile.is_zipfile(path):
        archive = zipfile.ZipFile(path)
        names = set(archive.namelist())
        manifest_names = [name for name in names if Path(name).name == "fixture_manifest.json"]
        if len(manifest_names) != 1:
            archive.close()
            raise ValueError("fixture ZIP must contain exactly one fixture_manifest.json")
        manifest_name = manifest_names[0]
        manifest_bytes = archive.read(manifest_name)
        base = str(Path(manifest_name).parent)
        read_entry = lambda name: archive.read(f"{base}/{name}") if base != "." else archive.read(name)
    else:
        manifest_bytes = path.read_bytes()
        read_entry = lambda name: (path.parent / name).read_bytes()

    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"fixture manifest is not duplicate-free UTF-8 JSON: {exc}") from exc
    _check_no_answer_key(manifest)
    if manifest.get("benchmark_id") != "r15d-semantic-source-facts-v2" or manifest.get("status") != "built_pending_independent_adjudication":
        raise ValueError("fixture manifest is not an active R15D v2 label-free fixture")
    if manifest.get("answer_key_included") is not False:
        raise ValueError("fixture manifest does not assert answer_key_included=false")

    design_bytes = MANIFEST.read_bytes()
    design = json.loads(design_bytes.decode("utf-8"), object_pairs_hook=_unique_object)
    _check_no_answer_key(design)
    if hashlib.sha256(design_bytes).hexdigest() != manifest.get("source_design_manifest_sha256"):
        raise ValueError("fixture source-design manifest digest does not match the current pinned v2 design")

    design_cases = {case["id"]: case for case in design["cases"]}
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != 6:
        raise ValueError("fixture manifest must contain exactly six cases")
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(ids) != 6 or len(ids) != len(cases) or not all(isinstance(x, str) for x in ids) or set(ids) != set(design_cases):
        raise ValueError("fixture case IDs do not match the six canonical v2 design cases")

    for case in cases:
        case_id = case["id"]
        design_case = design_cases[case_id]
        expected_keys = {
            "id", "repository", "commit_sha", "tree_sha", "path", "git_blob_sha1",
            "line_start", "line_end", "proposition", "boundary", "excerpt_file",
            "excerpt_sha256", "excerpt_bytes",
        }
        if set(case) != expected_keys:
            raise ValueError(f"{case_id}: fixture case fields are not canonical")
        for key in ("repository", "path", "line_start", "line_end", "proposition", "boundary"):
            if case[key] != design_case[key]:
                raise ValueError(f"{case_id}: fixture case differs from the public v2 design for {key}")
        source = EXPECTED.get(case["repository"])
        if source is None or (case["commit_sha"], case["tree_sha"], case["path"], case["git_blob_sha1"]) != source:
            raise ValueError(f"{case_id}: source commit/tree/path/blob pin is not approved")
        excerpt_name = case["excerpt_file"]
        if not isinstance(excerpt_name, str) or excerpt_name.startswith("/") or ".." in Path(excerpt_name).parts:
            raise ValueError(f"{case_id}: unsafe excerpt file path")
        try:
            excerpt = read_entry(excerpt_name)
        except (OSError, KeyError) as exc:
            raise ValueError(f"{case_id}: excerpt file is missing: {exc}") from exc
        if len(excerpt) != case["excerpt_bytes"] or hashlib.sha256(excerpt).hexdigest() != case["excerpt_sha256"]:
            raise ValueError(f"{case_id}: excerpt bytes or SHA-256 do not match fixture manifest")

    if 'archive' in locals():
        archive.close()
    return manifest


def _pin(case: dict) -> dict:
    return {key: case[key] for key in ("repository", "commit_sha", "tree_sha", "path", "git_blob_sha1", "line_start", "line_end", "excerpt_sha256")}


def _valid_evidence(references: object, pin: dict) -> bool:
    if not isinstance(references, list) or not references:
        return False
    normalized = []
    for reference in references:
        if not isinstance(reference, str):
            return False
        match = EVIDENCE_RE.fullmatch(reference.strip())
        if not match or not (
            match.group("path") == pin["path"]
            and match.group("start") == str(pin["line_start"])
            and (match.group("end") or match.group("start")) == str(pin["line_end"])
            and match.group("sha") == pin["excerpt_sha256"]
        ):
            return False
        normalized.append(reference.strip())
    return len(normalized) == len(set(normalized))


def validate_submission(submission: object, fixture_manifest: dict) -> dict:
    errors = []
    if not isinstance(submission, dict) or set(submission) != TOP_FIELDS:
        return {"valid": False, "reviewer_id": None, "case_count": 0, "errors": ["submission must contain exactly the schema-defined top-level fields"]}
    if submission.get("schema_version") != "1.0" or submission.get("benchmark_id") != "r15d-semantic-source-facts-v2":
        errors.append("schema version or benchmark ID is invalid")
    reviewer_id = submission.get("reviewer_id")
    if not isinstance(reviewer_id, str) or not REVIEWER_ID_RE.fullmatch(reviewer_id) or reviewer_id != reviewer_id.strip():
        errors.append("reviewer_id must be a normalized 3-128 character stable identifier")
    if not _valid_timestamp(submission.get("submitted_at")):
        errors.append("submitted_at must be a timezone-aware UTC ISO-8601 timestamp")

    attestations = submission.get("attestations")
    if not isinstance(attestations, dict) or set(attestations) != ATTESTATION_FIELDS:
        errors.append("reviewer attestations must contain exactly the schema-defined fields")
    else:
        for field in ("independent_review", "model_outputs_not_seen", "other_reviews_not_seen", "conflicts_disclosed"):
            if attestations.get(field) is not True:
                errors.append(f"required reviewer attestation must be true: {field}")
        if not isinstance(attestations.get("conflict_statement"), str) or len(attestations["conflict_statement"].strip()) < 3:
            errors.append("conflict_statement must say none or describe the disclosed conflict")

    fixture_cases = {case["id"]: case for case in fixture_manifest["cases"]}
    cases = submission.get("cases")
    if not isinstance(cases, list) or len(cases) != 6:
        errors.append("submission must contain exactly six v2 cases")
        cases = cases if isinstance(cases, list) else []
    ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    if len(ids) != len(cases) or not all(isinstance(x, str) for x in ids) or set(ids) != set(fixture_cases) or len(set(ids)) != 6:
        errors.append("case IDs must contain each of the six canonical v2 cases exactly once")

    for case in cases:
        case_id = case.get("case_id", "<invalid>") if isinstance(case, dict) else "<invalid>"
        if not isinstance(case, dict) or set(case) != CASE_FIELDS:
            errors.append(f"{case_id}: reviewer case fields are not canonical")
            continue
        expected = fixture_cases.get(case_id)
        if expected is None:
            errors.append(f"{case_id}: case ID is not part of R15D v2")
            continue
        pin = _pin(expected)
        if not isinstance(case.get("source_pin"), dict) or case["source_pin"] != pin:
            errors.append(f"{case_id}: source pin differs from the verified label-free fixture")
        if not isinstance(case.get("label"), str) or case["label"] not in ALLOWED:
            errors.append(f"{case_id}: label is outside the allowed applicability taxonomy")
        if not isinstance(case.get("rationale"), str) or not case["rationale"].strip():
            errors.append(f"{case_id}: rationale must be non-empty")
        if not _valid_evidence(case.get("evidence_references"), pin):
            errors.append(f"{case_id}: evidence references must be unique and match exact pinned excerpt")
        confidence = case.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            errors.append(f"{case_id}: confidence must be a number between 0 and 1")
        if not _valid_timestamp(case.get("completed_at")):
            errors.append(f"{case_id}: completed_at must be a timezone-aware UTC ISO-8601 timestamp")
        if case.get("independence_attestation") is not True:
            errors.append(f"{case_id}: case-level independence attestation must be true")

    return {
        "valid": not errors,
        "reviewer_id": reviewer_id if isinstance(reviewer_id, str) else None,
        "case_count": len(cases),
        "errors": errors,
        "identity_verification": "not_performed_by_validator",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate one private R15D v2 six-case reviewer bundle against a scanned label-free fixture artifact.")
    parser.add_argument("--fixture", type=Path, required=True, help="Extracted fixture directory, ZIP artifact, or fixture_manifest.json path.")
    parser.add_argument("--submission", type=Path, required=True)
    args = parser.parse_args()
    try:
        fixture = load_fixture_bundle(args.fixture)
        submission = json.loads(args.submission.read_bytes().decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2))
        raise SystemExit(1)
    result = validate_submission(submission, fixture)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
