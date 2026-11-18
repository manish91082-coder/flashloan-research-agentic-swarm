from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flashloan_research.role_source_policy import (  # noqa: E402
    order_role_source_manifest,
    role_path_admissible,
)
from flashloan_research.specialist_runner import _verified_source_context  # noqa: E402


CANDIDATES = {
    "0xnavarro/Aave-Liquiditor",
    "cobibean/aave-liquidator-bot",
}
ROLES = (
    "candidate_purpose",
    "protocol_specialist",
    "solidity_security",
    "execution_engineer",
    "test_verification",
    "economics_quant",
    "dependency_license",
    "independent_reviewer",
)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def fetch_pinned_source(repository: str, commit_sha: str, path: str) -> bytes:
    encoded_path = urllib.parse.quote(path, safe="/")
    url = f"https://raw.githubusercontent.com/{repository}/{commit_sha}/{encoded_path}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "flashloan-r15c-context-replay/1.0"},
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"failed to fetch pinned source {repository}@{commit_sha}:{path}: {last_error}")


def load_inspections(input_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    found: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(input_dir.rglob("inspections/*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("repository") in CANDIDATES:
            found.append((path, data))
    repositories = {data.get("repository") for _, data in found}
    missing = CANDIDATES - repositories
    if missing:
        raise RuntimeError(f"frozen R15C artifact is missing candidate inspections: {sorted(missing)}")
    return found


def replay_candidate(
    inspection_path: Path,
    inspection: dict[str, Any],
    vault_root: Path,
) -> dict[str, Any]:
    repository = inspection["repository"]
    commit_sha = inspection["commit_sha"]
    tree_sha = inspection["tree_sha"]
    manifest = inspection.get("captured_files", [])
    if not isinstance(manifest, list) or not manifest:
        raise RuntimeError(f"{repository}: captured_files is empty or malformed")

    verified_sources = []
    for item in manifest:
        if not isinstance(item, dict):
            raise RuntimeError(f"{repository}: malformed captured file manifest entry")
        path = item.get("path")
        expected_blob = item.get("blob_sha")
        if not isinstance(path, str) or not isinstance(expected_blob, str):
            raise RuntimeError(f"{repository}: captured file lacks path/blob_sha")
        data = fetch_pinned_source(repository, commit_sha, path)
        actual_blob = git_blob_sha(data)
        if actual_blob != expected_blob:
            raise RuntimeError(
                f"{repository}:{path}: Git blob SHA mismatch; "
                f"expected={expected_blob}, actual={actual_blob}"
            )
        relative = Path(expected_blob[:2]) / expected_blob[2:]
        target = vault_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        verified_sources.append({
            "path": path,
            "blob_sha": actual_blob,
            "bytes": len(data),
            "vault_relative_path": relative.as_posix(),
        })

    role_results = {}
    for role in ROLES:
        max_files = 5 if role == "independent_reviewer" else 3
        max_chars = 12000 if role == "independent_reviewer" else 6000
        context_lines = 10 if role == "independent_reviewer" else 12
        ordered, coverage = order_role_source_manifest(role, manifest)
        expected_paths = [item["path"] for item in ordered[:max_files]]
        excerpts = _verified_source_context(
            inspection,
            snapshot_root=vault_root,
            max_files=max_files,
            max_chars=max_chars,
            context_lines=context_lines,
            role=role,
        )
        excerpt_paths = [item["path"] for item in excerpts]
        unique_excerpt_paths = list(dict.fromkeys(excerpt_paths))
        if unique_excerpt_paths != expected_paths:
            raise AssertionError(
                f"{repository}/{role}: emitted unique excerpt paths differ from deterministic shortlist; "
                f"expected={expected_paths}, actual={unique_excerpt_paths}"
            )
        if any(not role_path_admissible(role, path) for path in excerpt_paths):
            raise AssertionError(f"{repository}/{role}: inadmissible path entered context")
        manifest_by_path = {item["path"]: item for item in manifest}
        per_path_characters: dict[str, int] = {}
        for excerpt in excerpts:
            per_path_characters[excerpt["path"]] = (
                per_path_characters.get(excerpt["path"], 0) + len(excerpt["excerpt"]) + 1
            )
            source = manifest_by_path.get(excerpt["path"])
            if not source or source["blob_sha"] != excerpt["blob_sha"]:
                raise AssertionError(f"{repository}/{role}: excerpt source pin mismatch")
            expected_excerpt_sha = hashlib.sha256(
                excerpt["excerpt"].encode("utf-8")
            ).hexdigest()
            if expected_excerpt_sha != excerpt["excerpt_sha256"]:
                raise AssertionError(f"{repository}/{role}: excerpt hash mismatch")
            if excerpt["start_line"] < 1 or excerpt["end_line"] < excerpt["start_line"]:
                raise AssertionError(f"{repository}/{role}: invalid inclusive line range")
            if len(excerpt["excerpt"]) > max_chars // max_files:
                raise AssertionError(f"{repository}/{role}: per-file context budget exceeded")
        if any(value > max_chars // max_files for value in per_path_characters.values()):
            raise AssertionError(f"{repository}/{role}: aggregate per-file context budget exceeded")
        if sum(per_path_characters.values()) > max_chars:
            raise AssertionError(f"{repository}/{role}: total context budget exceeded")

        # The context builder may emit fewer files than the path shortlist if a
        # selected source has no renderable lines. It must never emit an
        # inadmissible file or exceed the configured file/context budgets.
        if len(set(excerpt_paths)) > max_files:
            raise AssertionError(f"{repository}/{role}: max_files exceeded")

        selected_manifest = [
            item for item in manifest if item.get("path") in set(expected_paths)
        ]
        _, selected_coverage = order_role_source_manifest(role, selected_manifest)
        # Manifest-level presence is not enough: record whether required families
        # actually survived the bounded max_files selection into specialist context.
        if coverage["coverage_status"] == "complete" and selected_coverage["coverage_status"] != "complete":
            raise AssertionError(
                f"{repository}/{role}: bounded shortlist starved a required source family; "
                f"missing={selected_coverage['missing_families']}"
            )

        role_results[role] = {
            "source_family_coverage": coverage,
            "selected_source_family_coverage": selected_coverage,
            "shortlisted_paths": expected_paths,
            "excerpt_paths": unique_excerpt_paths,
            "excerpt_count": len(excerpts),
            "excerpt_characters": sum(len(item["excerpt"]) for item in excerpts),
            "per_file_budget": max_chars // max_files,
            "total_budget": max_chars,
            "excerpts": [
                {
                    "path": item["path"],
                    "blob_sha": item["blob_sha"],
                    "start_line": item["start_line"],
                    "end_line": item["end_line"],
                    "excerpt_sha256": item["excerpt_sha256"],
                    "characters": len(item["excerpt"]),
                }
                for item in excerpts
            ],
        }

    # Candidate-specific invariants from the frozen R15C failure packet.
    if repository == "cobibean/aave-liquidator-bot":
        for role in (
            "candidate_purpose", "protocol_specialist", "solidity_security",
            "execution_engineer", "economics_quant", "independent_reviewer",
        ):
            paths = role_results[role]["excerpt_paths"]
            if not paths or paths[0] != "contracts/AaveLiquidatorSwapRouter02.sol":
                raise AssertionError(f"COB {role}: Solidity protocol contract is not first in context")
        dependency = role_results["dependency_license"]
        if dependency["excerpt_paths"]:
            raise AssertionError("COB dependency/license received source without admissible dependency/build/license family")
        test_paths = role_results["test_verification"]["excerpt_paths"]
        if any(not path.startswith(("monitor/test/", "test/", "tests/", "spec/")) for path in test_paths):
            raise AssertionError("COB test-verification received non-test source")
        review_paths = role_results["independent_reviewer"]["excerpt_paths"]
        if any(path.startswith("monitor/test/") for path in review_paths):
            raise AssertionError("COB independent reviewer received monitor-only tests")

    if repository == "0xnavarro/Aave-Liquiditor":
        test_paths = role_results["test_verification"]["excerpt_paths"]
        if any(path != "hardhat.config.ts" for path in test_paths):
            raise AssertionError("Aave test-verification received non-test/non-config source")
        if "test_source" not in role_results["test_verification"]["source_family_coverage"]["missing_families"]:
            raise AssertionError("Aave missing test-source family was not surfaced")

    return {
        "repository": repository,
        "commit_sha": commit_sha,
        "tree_sha": tree_sha,
        "inspection_path_in_artifact": str(inspection_path),
        "captured_file_count": len(manifest),
        "signal_count": len(inspection.get("signals", [])),
        "verified_source_count": len(verified_sources),
        "verified_source_bytes": sum(item["bytes"] for item in verified_sources),
        "verified_sources": verified_sources,
        "roles": role_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inspections = load_inspections(args.input_dir)
    with TemporaryDirectory(prefix="r15c-role-context-vault-") as temp:
        vault = Path(temp)
        candidates = [
            replay_candidate(path, data, vault)
            for path, data in inspections
        ]
    result = {
        "replay": "r15c_role_context_byte_level_replay",
        "status": "passed",
        "model_inference_used": False,
        "candidate_count": len(candidates),
        "source_blob_verification": "git_blob_sha1_exact_match",
        "candidates": candidates,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(json.dumps({
        "status": "passed",
        "candidate_count": len(candidates),
        "verified_source_files": sum(item["verified_source_count"] for item in candidates),
        "report": str(args.output),
        "report_sha256": digest,
        "model_inference_used": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
