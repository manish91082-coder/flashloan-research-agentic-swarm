from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research_runs/r15d_v2_semantic_case_design.json"
SOURCES = {
    "0xnavarro/Aave-Liquiditor": ROOT / "tests/fixtures/r15d_semantic_sources/nav_flash_liquidator.sol",
    "cobibean/aave-liquidator-bot": ROOT / "tests/fixtures/r15d_semantic_sources/cob_aave_liquidator_swap_router02.sol",
}
EXPECTED = {
    "0xnavarro/Aave-Liquiditor": ("9197ee3002d7d9b35e9c2da324128a38f7569038", "14de2312e96c369bcc52c9bae96215051aea22b4", "src/contracts/FlashLiquidator.sol", "32c5e42920517fa1b93540a94e5d4dd95de94e1a"),
    "cobibean/aave-liquidator-bot": ("3159c15f4dcfb0df215b4c3024f47753a1133b84", "1a9ee7218304b95654385fc11f255a7c5d532bc4", "contracts/AaveLiquidatorSwapRouter02.sol", "daa5716e80f203ff9ba34868e4693db382774ab8"),
}
FORBIDDEN_KEYS = {"expected_label", "gold_label", "reference_label", "ground_truth_label", "answer_key", "answer_labels", "label_key"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _check_no_answer_key(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden answer-key field at {path}.{key}")
            _check_no_answer_key(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_no_answer_key(child, f"{path}[{index}]")


def build(manifest_path: Path = MANIFEST, output_dir: Path | None = None) -> dict:
    if output_dir is None:
        raise ValueError("R15D v2 fixture build requires an explicit isolated output directory")
    out = output_dir.resolve()
    root = ROOT.resolve()
    if out == root or root in out.parents:
        raise ValueError("R15D v2 fixture output must be outside the public repository")

    raw_manifest = manifest_path.read_bytes()
    manifest = json.loads(raw_manifest.decode("utf-8"))
    _check_no_answer_key(manifest)
    if manifest.get("benchmark_id") != "r15d-semantic-source-facts-v2":
        raise ValueError("unexpected R15D v2 benchmark identity")
    if manifest.get("status") != "design_only_no_reference_labels":
        raise ValueError("v2 design manifest must remain design-only without reference labels")
    if manifest.get("blinding", {}).get("expected_labels_in_public_manifest") is not False:
        raise ValueError("v2 public design must explicitly declare that expected labels are absent")

    sources_by_repo = {source["repository"]: source for source in manifest.get("sources", [])}
    if set(sources_by_repo) != set(EXPECTED):
        raise ValueError("v2 source set differs from the two approved immutable repositories")
    for repo, source in sources_by_repo.items():
        commit, tree, path, blob = EXPECTED[repo]
        if (source.get("commit_sha"), source.get("tree_sha"), source.get("path"), source.get("git_blob_sha1")) != (commit, tree, path, blob):
            raise ValueError(f"v2 source identity mismatch: {repo}")
        source_bytes = SOURCES[repo].read_bytes()
        if git_blob_sha(source_bytes) != blob:
            raise ValueError(f"v2 source Git blob SHA-1 mismatch: {repo}")

    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != 6:
        raise ValueError("v2 fixture must contain exactly six design cases")
    case_ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(case_ids) != 6 or len(set(case_ids)) != 6:
        raise ValueError("v2 case IDs must be six unique strings")
    if not all(isinstance(case_id, str) for case_id in case_ids):
        raise ValueError("v2 case IDs must be strings")

    excerpts_dir = out / "excerpts"
    excerpts_dir.mkdir(parents=True, exist_ok=True)
    built_cases = []
    for case in cases:
        repo = case.get("repository")
        source = sources_by_repo.get(repo)
        if source is None or case.get("path") != source["path"]:
            raise ValueError(f"{case.get('id')}: case source path is not in the immutable source registry")
        start, end = case.get("line_start"), case.get("line_end")
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
            raise ValueError(f"{case.get('id')}: invalid inclusive line range")
        lines = SOURCES[repo].read_text(encoding="utf-8").splitlines(keepends=True)
        if end > len(lines):
            raise ValueError(f"{case.get('id')}: line range exceeds pinned source")
        excerpt = "".join(lines[start - 1:end]).encode("utf-8")
        filename = f"{case['id']}.sol.txt"
        (excerpts_dir / filename).write_bytes(excerpt)
        built_cases.append({
            "id": case["id"],
            "repository": repo,
            "commit_sha": source["commit_sha"],
            "tree_sha": source["tree_sha"],
            "path": source["path"],
            "git_blob_sha1": source["git_blob_sha1"],
            "line_start": start,
            "line_end": end,
            "proposition": case["proposition"],
            "boundary": case["boundary"],
            "excerpt_file": f"excerpts/{filename}",
            "excerpt_sha256": sha256(excerpt),
            "excerpt_bytes": len(excerpt),
        })

    result = {
        "schema_version": "1.0",
        "benchmark_id": manifest["benchmark_id"],
        "status": "built_pending_independent_adjudication",
        "source_design_manifest_sha256": sha256(raw_manifest),
        "sources": [
            {key: source[key] for key in ("repository", "commit_sha", "tree_sha", "path", "git_blob_sha1")}
            for source in manifest["sources"]
        ],
        "cases": built_cases,
        "safety": manifest["safety"],
        "adjudication_policy": manifest["adjudication_policy"],
        "answer_key_included": False,
    }
    _check_no_answer_key(result)
    (out / "fixture_manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build label-free R15D v2 source-pinned excerpts for blind review.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build(output_dir=args.output_dir)
    manifest_path = args.output_dir.resolve() / "fixture_manifest.json"
    print(json.dumps({
        "status": result["status"],
        "case_count": len(result["cases"]),
        "manifest_sha256": sha256(manifest_path.read_bytes()),
        "answer_key_included": False,
    }, indent=2))


if __name__ == "__main__":
    main()
