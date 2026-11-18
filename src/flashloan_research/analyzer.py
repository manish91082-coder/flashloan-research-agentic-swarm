from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Any

from .config import SETTINGS, Settings
from .github_api import GitHubClient
from .models import EvidenceRecord, RepositoryCandidate
from .storage import ContentAddressedVault, ResearchStore, git_blob_sha

SOURCE_EXTENSIONS = {".sol", ".rs", ".py", ".ts", ".js", ".vy", ".move"}
FLASH_PATTERNS: dict[str, str] = {
    "aave_flash_loan_simple": r"flashLoanSimple",
    "aave_execute_operation": r"executeOperation\s*\(",
    "aave_pool_provider_wiring": r"IPoolAddressesProvider\s*\(|IPool\s*\(",
    "erc3156_callback": r"onFlashLoan\s*\(",
    "uniswap_v2_flash_callback": r"uniswapV2Call\s*\(",
    "uniswap_v3_flash_callback": r"uniswapV3FlashCallback\s*\(",
    "generic_flash_loan_call": r"\.flashLoan\s*\(",
    "min_profit_guard": r"minProfit|min_profit|minProfitThreshold",
    "balance_delta_pattern": r"balanceOf\s*\(",
    "reentrancy_guard": r"nonReentrant|ReentrancyGuard",
}


@dataclass(frozen=True)
class CapturedFile:
    path: str
    blob_sha: str
    content: bytes


def is_source_file(path: str) -> bool:
    from pathlib import PurePosixPath
    p = PurePosixPath(path)
    return p.suffix.lower() in SOURCE_EXTENSIONS and not any(part in {"node_modules", "vendor", "lib", "out", "build", "target"} for part in p.parts)


RESEARCH_ARTIFACT_NAMES = {
    "package.json", "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock",
    "requirements.txt", "requirements.lock", "pyproject.toml", "poetry.lock", "pipfile", "pipfile.lock",
    "cargo.toml", "cargo.lock", "go.mod", "go.sum", "composer.json", "composer.lock",
    "foundry.toml", "pytest.ini", "tox.ini", "truffle-config.js", "truffle-config.ts",
    "tsconfig.json", "makefile", "dockerfile", "license", "license.md", "license.txt",
    "copying", "notice", "readme", "readme.md", "readme.rst",
}

NON_PROTOCOL_CAPTURE_SEGMENTS = {
    "monitor", "monitoring", "telemetry", "dashboard", "ui", "frontend",
    "observability", "web", "public",
}


def is_research_artifact(path: str) -> bool:
    """Include source plus small, high-value test/build/dependency/license evidence files."""
    from pathlib import PurePosixPath
    p = PurePosixPath(path)
    parts = {part.casefold() for part in p.parts}
    if parts.intersection({"node_modules", "vendor", "lib", "out", "build", "target"}):
        return False
    if parts.intersection(NON_PROTOCOL_CAPTURE_SEGMENTS):
        return False
    name = p.name.casefold()
    if is_source_file(path) or name in RESEARCH_ARTIFACT_NAMES:
        return True
    if ".github" in parts and "workflows" in parts and p.suffix.casefold() in {".yml", ".yaml"}:
        return True
    return False


def _capture_family(path: str) -> str | None:
    from pathlib import PurePosixPath
    p = PurePosixPath(path)
    name = p.name.casefold()
    parts = {part.casefold() for part in p.parts}
    if parts.intersection(NON_PROTOCOL_CAPTURE_SEGMENTS):
        return None
    if any(part in {"test", "tests", "spec", "specs"} for part in parts) or name.endswith((".test.js", ".test.ts", ".spec.js", ".spec.ts", ".t.sol")):
        return "test_source"
    if p.suffix.casefold() == ".sol" or any(term in name for term in ("liquidat", "flashloan", "flash_loan", "executor", "router")):
        return "protocol_contract"
    if name in {"package.json", "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock",
                "requirements.txt", "requirements.lock", "pyproject.toml", "poetry.lock", "pipfile", "pipfile.lock",
                "cargo.toml", "cargo.lock", "go.mod", "go.sum", "composer.json", "composer.lock"}:
        return "dependency_manifest"
    if name in {"license", "license.md", "license.txt", "copying", "notice"}:
        return "license_artifact"
    if ".github" in parts and "workflows" in parts:
        return "ci_workflow"
    if name in {"foundry.toml", "pytest.ini", "tox.ini", "truffle-config.js", "truffle-config.ts", "tsconfig.json", "makefile", "dockerfile"} or name.startswith("hardhat.config"):
        return "build_config"
    if p.suffix.casefold() in SOURCE_EXTENSIONS:
        return "runtime_entrypoint"
    if name.startswith("readme"):
        return "documentation"
    return None


def select_research_artifacts(items: list[dict[str, Any]], max_files: int) -> list[dict[str, Any]]:
    """Deterministically round-robin evidence families before applying the capture cap."""
    if max_files < 1:
        raise ValueError("max_files must be positive")
    family_order = ("protocol_contract", "runtime_entrypoint", "test_source", "dependency_manifest",
                    "build_config", "license_artifact", "ci_workflow", "documentation")
    buckets: dict[str, list[dict[str, Any]]] = {family: [] for family in family_order}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            continue
        family = _capture_family(item["path"])
        if family in buckets:
            buckets[family].append(item)
    for bucket in buckets.values():
        bucket.sort(key=lambda item: item["path"].casefold())
    selected: list[dict[str, Any]] = []
    depth = 0
    while len(selected) < max_files:
        added = False
        for family in family_order:
            bucket = buckets[family]
            if depth < len(bucket) and len(selected) < max_files:
                selected.append(bucket[depth])
                added = True
        if not added:
            break
        depth += 1
    return selected


def decode_blob(raw: dict[str, Any]) -> bytes:
    if raw.get("encoding") != "base64" or not isinstance(raw.get("content"), str):
        raise ValueError("GitHub blob response must contain base64 content")
    return base64.b64decode("".join(raw["content"].split()), validate=True)


def extract_signals(path: str, content: bytes) -> list[dict[str, Any]]:
    text = content.decode("utf-8", errors="replace")
    signals: list[dict[str, Any]] = []
    for signal, pattern in FLASH_PATTERNS.items():
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            line = text.count("\n", 0, match.start()) + 1
            excerpt = text[max(0, match.start() - 120):min(len(text), match.end() + 180)].replace("\n", " ").strip()
            signals.append({"signal": signal, "path": path, "line": line, "excerpt": excerpt[:400]})
    return signals


def collect_repository_tree(client: Any, full_name: str, root_tree_sha: str, settings: Settings) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Recover a truncated recursive Git tree using bounded non-recursive traversal."""
    recursive_tree = client.tree(full_name, root_tree_sha, recursive=True)
    recursive_items = recursive_tree.get("tree", [])
    if not isinstance(recursive_items, list):
        raise ValueError("Git recursive tree response missing tree array")
    if not recursive_tree.get("truncated", False):
        return recursive_items, {
            "recursive_tree_truncated": False,
            "tree_recovery_attempted": False,
            "tree_recovery_complete": True,
            "tree_directories_visited": 0,
            "tree_entries_seen": len(recursive_items),
        }

    recovered: list[dict[str, Any]] = []
    pending: list[tuple[str, str]] = [("", root_tree_sha)]
    visited: set[str] = set()
    entries_seen = 0
    complete = True

    while pending:
        prefix, tree_sha = pending.pop()
        if tree_sha in visited:
            continue
        if len(visited) >= settings.max_tree_directories:
            complete = False
            break
        visited.add(tree_sha)
        page = client.tree(full_name, tree_sha, recursive=False)
        entries = page.get("tree", [])
        if not isinstance(entries, list) or page.get("truncated", False):
            complete = False
        if not isinstance(entries, list):
            continue
        for entry in entries:
            entries_seen += 1
            if entries_seen > settings.max_tree_entries:
                complete = False
                break
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                complete = False
                continue
            full_path = f"{prefix}{entry['path']}"
            normalized = {**entry, "path": full_path}
            if entry.get("type") == "tree":
                child_sha = entry.get("sha")
                if not isinstance(child_sha, str) or len(child_sha) != 40:
                    complete = False
                else:
                    pending.append((full_path.rstrip("/") + "/", child_sha))
            else:
                recovered.append(normalized)
        if not complete:
            break

    if pending:
        complete = False
    return recovered, {
        "recursive_tree_truncated": True,
        "tree_recovery_attempted": True,
        "tree_recovery_complete": complete,
        "tree_directories_visited": len(visited),
        "tree_entries_seen": entries_seen,
    }


class ResearchPipeline:
    def __init__(self, client: GitHubClient | None = None, settings: Settings = SETTINGS):
        self.settings = settings
        self.client = client or GitHubClient(settings)

    def discover(self, query: str, store: ResearchStore, per_page: int = 30, page: int = 1) -> list[RepositoryCandidate]:
        raw_items = self.client.search_repositories(query, per_page=per_page, page=page)
        candidates = [RepositoryCandidate.from_api(raw, query) for raw in raw_items]
        for candidate in candidates:
            store.upsert_candidate(candidate)
        return candidates

    def inspect(self, full_name: str, store: ResearchStore) -> dict[str, Any]:
        repo = self.client.repository(full_name)
        candidate = RepositoryCandidate.from_api(repo, "manual-inspect")
        store.upsert_candidate(candidate)
        commit = self.client.commit(full_name, candidate.default_branch)
        commit_sha = commit.get("sha")
        tree_sha = commit.get("commit", {}).get("tree", {}).get("sha")
        if not isinstance(commit_sha, str) or len(commit_sha) != 40 or not isinstance(tree_sha, str):
            raise ValueError("GitHub commit response missing full commit SHA or tree SHA")
        tree_items, tree_status = collect_repository_tree(self.client, full_name, tree_sha, self.settings)
        tree_truncated = not tree_status["tree_recovery_complete"]
        store.save_snapshot(full_name, commit_sha, tree_sha, tree_truncated)
        research_items_all = [
            item for item in tree_items
            if isinstance(item, dict)
            and item.get("type") == "blob"
            and isinstance(item.get("path"), str)
            and isinstance(item.get("sha"), str)
            and is_research_artifact(item["path"])
        ]
        source_items_all = [item for item in research_items_all if is_source_file(item["path"])]
        oversized_source_count = sum(
            1 for item in research_items_all
            if not isinstance(item.get("size"), int) or item["size"] < 0 or item["size"] > self.settings.max_blob_bytes
        )
        eligible_research_items = [
            item for item in research_items_all
            if isinstance(item.get("size"), int) and 0 <= item["size"] <= self.settings.max_blob_bytes
        ]
        source_items = select_research_artifacts(eligible_research_items, self.settings.max_source_files)
        source_cap_hit = len(eligible_research_items) > len(source_items)
        eligible_source_items = [item for item in source_items_all if isinstance(item.get("size"), int) and 0 <= item["size"] <= self.settings.max_blob_bytes]
        captured_source_count = sum(1 for item in source_items if is_source_file(item["path"]))
        captured: list[CapturedFile] = []
        captured_manifest: list[dict[str, Any]] = []
        all_signals: list[dict[str, Any]] = []
        vault = ContentAddressedVault(self.settings.snapshot_dir)
        for item in source_items:
            raw_blob = self.client.blob(full_name, item["sha"])
            content = decode_blob(raw_blob)
            if len(content) > self.settings.max_blob_bytes:
                raise ValueError(f"GitHub blob exceeded configured size cap for {item['path']}")
            actual_sha = git_blob_sha(content)
            if actual_sha != item["sha"]:
                raise ValueError(f"Git blob SHA mismatch for {item['path']}: expected {item['sha']}, got {actual_sha}")
            captured.append(CapturedFile(item["path"], actual_sha, content))
            vault_path = vault.put(actual_sha, content)
            captured_manifest.append({"path": item["path"], "blob_sha": actual_sha, "size_bytes": len(content), "vault_relative_path": str(vault_path.relative_to(vault.root))})
            file_signals = extract_signals(item["path"], content)
            all_signals.extend(file_signals)
            for signal in file_signals:
                from .models import EvidenceRecord
                store.save_evidence(EvidenceRecord(
                    repository=full_name, commit_sha=commit_sha, path=item["path"], blob_sha=actual_sha,
                    claim_type="observed_fact",
                    claim=f"Lexical pattern {signal['signal']} appears at line {signal['line']}; this is not proof of runtime behavior.",
                    evidence_excerpt=signal["excerpt"], confidence="low", acceptance_status="pending"
                ))
        source_capture_complete = not tree_truncated and not source_cap_hit and oversized_source_count == 0
        limitations = [
            "Static lexical signals are leads, not proof of runtime behavior or a vulnerability.",
            "No candidate repository code was executed.",
            "The scan covers only configured source extensions and excludes common vendor/build directories.",
        ]
        if tree_status["recursive_tree_truncated"] and tree_status["tree_recovery_complete"]:
            limitations.append("GitHub's recursive tree response was truncated; bounded non-recursive traversal recovered the tree inventory.")
        elif tree_truncated:
            limitations.append("GitHub returned a truncated recursive tree and bounded recovery did not complete; repository coverage is incomplete.")
        if source_cap_hit:
            limitations.append("The configured source-file cap was reached; additional eligible source files were not captured.")
        if oversized_source_count:
            limitations.append("One or more source files were omitted because size metadata was missing/invalid or exceeded the blob-size cap.")
        return {
            "repository": full_name,
            "commit_sha": commit_sha,
            "tree_sha": tree_sha,
            "tree_truncated": tree_truncated,
            **tree_status,
            "source_files_available_in_tree": len(source_items_all),
            "source_files_eligible_by_size": len(eligible_source_items),
            "source_files_selected": captured_source_count,
            "source_files_captured": captured_source_count,
            "research_artifacts_available_in_tree": len(research_items_all),
            "research_artifacts_eligible_by_size": len(eligible_research_items),
            "research_artifacts_selected": len(source_items),
            "research_artifacts_captured": len(captured),
            "source_cap_hit": source_cap_hit,
            "oversized_or_invalid_source_count": oversized_source_count,
            "source_capture_complete_within_configured_scope": source_capture_complete,
            "blobs_persisted": len(captured),
            "captured_files": captured_manifest,
            "source_file_cap": self.settings.max_source_files,
            "blob_size_cap_bytes": self.settings.max_blob_bytes,
            "signals": all_signals,
            "limitations": limitations,
        }
