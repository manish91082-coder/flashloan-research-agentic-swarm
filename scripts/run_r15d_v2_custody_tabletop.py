from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_r15d_v2_semantic_fixtures import build
from scripts.create_r15d_v2_intake_receipt import create_intake_receipt
from scripts.finalize_r15d_v2_adjudication import finalize_adjudication
from scripts.freeze_r15d_v2_adjudication import freeze_adjudication
from scripts.merge_r15d_v2_primary_reviews import merge_primary_reviews
from scripts.validate_r15d_v2_review_submission import load_fixture_bundle
from scripts.verify_r15d_v2_frozen_manifest import verify_frozen_manifest
from scripts.verify_r15d_v2_primary_merge import verify_primary_merge


def _write_private(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    if os.name == "posix":
        path.chmod(0o600)


def _primary_bundle(fixture: dict, reviewer_id: str, disagreement_case: str | None = None) -> dict:
    cases = []
    for source in fixture["cases"]:
        pin = {key: source[key] for key in (
            "repository", "commit_sha", "tree_sha", "path",
            "git_blob_sha1", "line_start", "line_end", "excerpt_sha256",
        )}
        evidence = [f'{pin["path"]}:{pin["line_start"]}-{pin["line_end"]}#sha256:{pin["excerpt_sha256"]}']
        label = "unknown"
        if reviewer_id == "tabletop.reviewer.b" and source["id"] == disagreement_case:
            label = "present"
        cases.append({
            "case_id": source["id"], "source_pin": pin, "label": label,
            "rationale": "Synthetic tabletop-only reviewer rationale.",
            "evidence_references": evidence, "confidence": 0.8,
            "completed_at": "2026-11-17T00:00:00Z", "independence_attestation": True,
        })
    return {
        "schema_version": "1.0",
        "benchmark_id": "r15d-semantic-source-facts-v2",
        "reviewer_id": reviewer_id,
        "submitted_at": "2026-11-17T00:00:00Z",
        "attestations": {
            "independent_review": True,
            "model_outputs_not_seen": True,
            "other_reviews_not_seen": True,
            "v1_answer_key_not_seen": True,
            "v1_labels_not_consulted": True,
            "conflicts_disclosed": True,
            "conflict_statement": "synthetic tabletop only",
        },
        "cases": cases,
    }


def _third_bundle(staged: dict) -> dict:
    cases = []
    for source in staged["cases"]:
        if not source["disagreement"]:
            continue
        pin = {key: source[key] for key in (
            "repository", "commit_sha", "tree_sha", "path",
            "git_blob_sha1", "line_start", "line_end", "excerpt_sha256",
        )}
        evidence = [f'{pin["path"]}:{pin["line_start"]}-{pin["line_end"]}#sha256:{pin["excerpt_sha256"]}']
        cases.append({
            "case_id": source["id"], "source_pin": pin, "label": "present",
            "rationale": "Synthetic tabletop-only third-review rationale.",
            "evidence_references": evidence, "confidence": 0.9,
            "completed_at": "2026-11-17T00:00:00Z", "independence_attestation": True,
        })
    return {
        "schema_version": "1.0",
        "benchmark_id": "r15d-semantic-source-facts-v2",
        "reviewer_id": "tabletop.reviewer.gamma",
        "submitted_at": "2026-11-17T00:00:00Z",
        "attestations": {
            "independent_review": True,
            "model_outputs_not_seen": True,
            "primary_reviews_seen": True,
            "v1_answer_key_not_seen": True,
            "v1_labels_not_consulted": True,
            "conflicts_disclosed": True,
            "conflict_statement": "synthetic tabletop only",
        },
        "cases": cases,
    }


def _encrypted_delivery(root: Path, name: str, value: dict) -> Path:
    gpg = shutil.which("gpg")
    if gpg is None:
        raise RuntimeError("GnuPG is required for the synthetic encrypted-delivery tabletop")
    sender = root / "sender"
    receiver = root / "receiver"
    key_custody = root / "key-custody"
    gnupg_home = root / "gnupg-home"
    for directory in (sender, receiver, key_custody, gnupg_home):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory.chmod(0o700)
    passphrase_file = key_custody / "tabletop.passphrase"
    if not passphrase_file.exists():
        passphrase_file.write_text(secrets.token_urlsafe(32) + "\n", encoding="utf-8")
        passphrase_file.chmod(0o600)
    env = os.environ.copy()
    env["GNUPGHOME"] = str(gnupg_home)
    plaintext = sender / f"{name}.json"
    ciphertext = sender / f"{name}.json.gpg"
    decrypted = receiver / f"{name}.json"
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    plaintext.write_bytes(payload)
    plaintext.chmod(0o600)
    subprocess.run([gpg, "--batch", "--yes", "--pinentry-mode", "loopback", "--passphrase-file", str(passphrase_file), "--symmetric", "--cipher-algo", "AES256", "--output", str(ciphertext), str(plaintext)], check=True, capture_output=True, env=env)
    ciphertext.chmod(0o600)
    encrypted_bytes = ciphertext.read_bytes()
    if not encrypted_bytes or payload in encrypted_bytes:
        raise RuntimeError("GnuPG encryption did not produce opaque ciphertext")
    plaintext.unlink()
    subprocess.run([gpg, "--batch", "--yes", "--pinentry-mode", "loopback", "--passphrase-file", str(passphrase_file), "--output", str(decrypted), "--decrypt", str(ciphertext)], check=True, capture_output=True, env=env)
    decrypted.chmod(0o600)
    if decrypted.read_bytes() != payload:
        raise RuntimeError("GnuPG encrypted-delivery round trip changed the private submission bytes")
    return decrypted

def run_tabletop() -> dict:
    if os.name != "posix":
        raise RuntimeError("custody permission tabletop requires POSIX file-mode semantics")
    workspace_path = None
    result = None
    with tempfile.TemporaryDirectory(prefix="r15d-v2-custody-tabletop-") as temporary:
        root = Path(temporary).resolve()
        workspace_path = root
        repository_root = Path(__file__).resolve().parents[1]
        if root == repository_root or repository_root in root.parents:
            raise RuntimeError("tabletop workspace must be outside the public repository")
        root.chmod(0o700)
        fixture_dir = root / "fixture"
        build(output_dir=fixture_dir)
        fixture = load_fixture_bundle(fixture_dir)

        a, b = root / "reviewer-a.json", root / "reviewer-b.json"
        receipt_a, receipt_b = root / "receipt-a.json", root / "receipt-b.json"
        staged_path = root / "staged-packet.json"
        third_path, third_receipt = root / "third-review.json", root / "third-receipt.json"
        final_path, frozen_path = root / "final-packet.json", root / "frozen-manifest.json"

        a = _encrypted_delivery(root, "primary-a", _primary_bundle(fixture, "tabletop.reviewer.a"))
        b = _encrypted_delivery(root, "primary-b", _primary_bundle(fixture, "tabletop.reviewer.b", "NAV2-02"))
        create_intake_receipt(fixture_dir, a, receipt_a, "primary_a", "tabletop.custodian", "2026-11-17T00:00:00Z", "private_video_check", True)
        create_intake_receipt(fixture_dir, b, receipt_b, "primary_b", "tabletop.custodian", "2026-11-17T00:00:00Z", "private_video_check", True)

        merged = merge_primary_reviews(fixture_dir, a, b, receipt_a, receipt_b, staged_path, "tabletop.custodian", True)
        verified_merge = verify_primary_merge(fixture_dir, a, b, receipt_a, receipt_b, staged_path, "tabletop.custodian", True, merged["output_sha256"])
        staged = json.loads(staged_path.read_text(encoding="utf-8"))
        third_path = _encrypted_delivery(root, "third-adjudicator", _third_bundle(staged))
        create_intake_receipt(fixture_dir, third_path, third_receipt, "third_adjudicator", "tabletop.custodian", "2026-11-17T00:00:00Z", "private_video_check", True, staged_path)

        finalized = finalize_adjudication(
            fixture_dir, a, b, receipt_a, receipt_b, staged_path, final_path,
            "tabletop.custodian", True, third_path, third_receipt, True, merged["output_sha256"],
        )
        frozen = freeze_adjudication(
            final_path, fixture_dir, frozen_path, "2026-11-17T00:00:00Z",
            a, b, receipt_a, receipt_b, staged_path, "tabletop.custodian", True,
            third_path, third_receipt, True, merged["output_sha256"],
        )
        verified_frozen = verify_frozen_manifest(
            final_path, fixture_dir, frozen_path, frozen["output_sha256"],
            a, b, receipt_a, receipt_b, staged_path, "tabletop.custodian", True,
            third_path, third_receipt, True, merged["output_sha256"],
        )

        for path in root.rglob("*"):
            if path.is_dir():
                path.chmod(0o700)
            elif path.is_file():
                path.chmod(0o600)
        root.chmod(0o700)
        directory_modes = {stat.S_IMODE(path.stat().st_mode) for path in [root, *[p for p in root.rglob("*") if p.is_dir()]]}
        file_modes = {stat.S_IMODE(path.stat().st_mode) for path in root.rglob("*") if path.is_file()}
        if directory_modes != {0o700} or file_modes != {0o600}:
            raise RuntimeError("private workspace permission audit failed")

        result = {
            "status": "passed",
            "synthetic_only": True,
            "primary_receipts_verified": 2,
            "third_receipts_verified": 1,
            "encrypted_submissions_verified": 3,
            "encryption_tool": "GnuPG AES-256 symmetric encrypted-delivery round trip",
            "primary_merge_verified": verified_merge["valid"],
            "final_adjudication_complete": finalized["valid_complete_adjudication"],
            "frozen_manifest_verified": verified_frozen["valid"],
            "case_count": verified_frozen["completed_cases"],
            "workspace_directory_mode": "0700",
            "private_file_mode": "0600",
            "workspace_removed_after_test": True,
            "model_inference_authorized": False,
            "production_reviewer_intake_authorized": False,
        }
    if workspace_path is None or workspace_path.exists():
        raise RuntimeError("synthetic private workspace was not removed after tabletop")
    if result is None:
        raise RuntimeError("synthetic custody tabletop produced no result")
    result["workspace_removed_after_test"] = True
    return result


def main() -> None:
    print(json.dumps(run_tabletop(), indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
