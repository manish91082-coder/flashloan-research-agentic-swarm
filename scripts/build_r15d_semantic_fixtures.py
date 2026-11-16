from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research_runs/r15d_semantic_case_manifest.json"
SOURCES = {
    "0xnavarro/Aave-Liquiditor": ROOT / "tests/fixtures/r15d_semantic_sources/nav_flash_liquidator.sol",
    "cobibean/aave-liquidator-bot": ROOT / "tests/fixtures/r15d_semantic_sources/cob_aave_liquidator_swap_router02.sol",
}
EXPECTED = {
    "0xnavarro/Aave-Liquiditor": ("9197ee3002d7d9b35e9c2da324128a38f7569038", "14de2312e96c369bcc52c9bae96215051aea22b4", "src/contracts/FlashLiquidator.sol", "32c5e42920517fa1b93540a94e5d4dd95de94e1a"),
    "cobibean/aave-liquidator-bot": ("3159c15f4dcfb0df215b4c3024f47753a1133b84", "1a9ee7218304b95654385fc11f255a7c5d532bc4", "contracts/AaveLiquidatorSwapRouter02.sol", "daa5716e80f203ff9ba34868e4693db382774ab8"),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def verify_source(repo: str, data: bytes, identity: dict) -> None:
    if repo not in EXPECTED:
        raise ValueError(f"unapproved repository: {repo}")
    commit, tree, path, blob = EXPECTED[repo]
    if (identity.get("commit_sha"), identity.get("tree_sha")) != (commit, tree):
        raise ValueError(f"commit/tree pin mismatch: {repo}")
    if identity.get("path") != path or identity.get("git_blob_sha1") != blob:
        raise ValueError(f"path/blob pin mismatch: {repo}")
    if git_blob_sha(data) != blob:
        raise ValueError(f"source Git blob SHA-1 mismatch: {repo}")


def extract_excerpt(lines: list[str], start: int, end: int) -> bytes:
    if isinstance(start, bool) or isinstance(end, bool) or start < 1 or end < start or end > len(lines):
        raise ValueError("invalid or shifted inclusive line range")
    return "".join(lines[start - 1:end]).encode("utf-8")


def require_complete_function(excerpt: str, signature: str) -> None:
    if not excerpt.lstrip().startswith(signature):
        raise ValueError("absence case does not begin with the declared function signature")
    clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", excerpt, flags=re.S)
    clean = re.sub(r'"(?:\\.|[^"\\])*"', '""', clean)
    depth = 0
    opened = False
    for char in clean:
        if char == "{":
            depth += 1
            opened = True
        elif char == "}":
            depth -= 1
            if depth < 0:
                raise ValueError("function range closes before it opens")
    if not opened or depth != 0 or not clean.rstrip().endswith("}"):
        raise ValueError("absence case range is not a complete balanced function body")


def build(manifest_path: Path = MANIFEST, output_dir: Path | None = None) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("benchmark_id") != "r15d-semantic-source-facts-v1":
        raise ValueError("unexpected benchmark identity")
    if manifest.get("status") != "design_only_excerpt_hashes_and_adjudication_pending":
        raise ValueError("refusing to rebuild a frozen or adjudicated manifest")
    identities = {}
    for candidate in manifest["candidates"]:
        repo = candidate["repository"]
        if repo in identities or repo not in SOURCES:
            raise ValueError(f"duplicate or unapproved candidate: {repo}")
        identities[repo] = candidate
        verify_source(
            repo,
            SOURCES[repo].read_bytes(),
            {
                **candidate["files"][0],
                "commit_sha": candidate["commit_sha"],
                "tree_sha": candidate["tree_sha"],
            },
        )
    if set(identities) != set(EXPECTED):
        raise ValueError("candidate set differs from the two approved source pins")

    out = output_dir or ROOT / "research_runs/r15d_semantic_fixtures"
    excerpts_dir = out / "excerpts"
    excerpts_dir.mkdir(parents=True, exist_ok=True)
    built_cases = []
    for case in manifest["cases"]:
        repo = case["repository"]
        if repo not in identities:
            raise ValueError(f"case references unpinned repository: {repo}")
        source_lines = SOURCES[repo].read_text(encoding="utf-8").splitlines(keepends=True)
        excerpt = extract_excerpt(source_lines, case["line_start"], case["line_end"])
        if case["expected_label"] == "absent":
            if case["id"] != "NAV-02":
                raise ValueError("unreviewed absence proposition")
            require_complete_function(excerpt.decode("utf-8"), "function executeOperation(")
        elif case["expected_label"] not in {"present", "not_applicable", "unknown"}:
            raise ValueError(f"invalid applicability label: {case['expected_label']}")
        filename = f"{case['id']}.sol.txt"
        (excerpts_dir / filename).write_bytes(excerpt)
        built_cases.append({
            **case,
            "commit_sha": identities[repo]["commit_sha"],
            "tree_sha": identities[repo]["tree_sha"],
            "git_blob_sha1": identities[repo]["files"][0]["git_blob_sha1"],
            "excerpt_file": f"excerpts/{filename}",
            "excerpt_sha256": sha256(excerpt),
            "excerpt_bytes": len(excerpt),
        })
    result = {
        "schema_version": "1.0",
        "benchmark_id": manifest["benchmark_id"],
        "status": "built_pending_independent_adjudication",
        "source_manifest_sha256": sha256(manifest_path.read_bytes()),
        "cases": built_cases,
        "safety": manifest["safety"],
        "adjudication": manifest["adjudication"],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "fixture_manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build source-pinned R15D semantic fixtures; never executes candidate code.")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    result = build(output_dir=args.output_dir)
    target = args.output_dir or ROOT / "research_runs/r15d_semantic_fixtures"
    print(json.dumps({"status": result["status"], "cases": len(result["cases"]), "manifest_sha256": sha256((target / "fixture_manifest.json").read_bytes())}, indent=2))


if __name__ == "__main__":
    main()
