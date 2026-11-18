from __future__ import annotations

from pathlib import PurePosixPath
from typing import Iterable

ROLE_FAMILY_PATTERNS = {
    "candidate_purpose": (
        ("protocol_contract", ("contracts/", "contract/", ".sol")),
        ("runtime_entrypoint", ("src/", "bot.", "main.", "index.", "app.")),
        ("build_manifest", ("package.json", "pyproject.toml", "foundry.toml", "hardhat.config", "truffle-config")),
        ("documentation", ("readme",)),
    ),
    "protocol_specialist": (
        ("protocol_contract", ("contracts/", "contract/", ".sol")),
        ("protocol_runtime", ("src/", "bot.", "main.", "index.")),
        ("build_manifest", ("foundry.toml", "hardhat.config", "truffle-config")),
    ),
    "solidity_security": (
        ("protocol_contract", ("contracts/", "contract/", ".sol")),
        ("security_test", ("test/", "tests/", "spec/", ".t.sol")),
        ("security_config", ("foundry.toml", "hardhat.config", "slither", "mythril")),
        ("runtime_entrypoint", ("src/", "bot.", "main.", "index.")),
    ),
    "execution_engineer": (
        ("execution_contract", ("contracts/", "contract/", ".sol")),
        ("execution_runtime", ("src/", "bot.", "main.", "index.", "executor", "router")),
        ("execution_test", ("test/", "tests/", "spec/")),
        ("execution_config", ("foundry.toml", "hardhat.config", "package.json")),
    ),
    "test_verification": (
        ("test_source", ("test/", "tests/", "spec/", ".t.sol", ".test.", ".spec.")),
        ("ci_workflow", (".github/workflows/",)),
        ("test_config", ("foundry.toml", "hardhat.config", "pytest.ini", "tox.ini", "pyproject.toml")),
    ),
    "economics_quant": (
        ("economic_contract", ("contracts/", "contract/", ".sol")),
        ("economic_runtime", ("src/", "bot.", "main.", "index.", "strategy", "profit", "quote")),
        ("economic_test", ("test/", "tests/", "spec/")),
        ("economic_config", ("foundry.toml", "hardhat.config", "package.json")),
    ),
    "dependency_license": (
        ("dependency_manifest", ("package.json", "package-lock.json", "npm-shrinkwrap.json",
                                 "pnpm-lock.yaml", "yarn.lock", "requirements.txt",
                                 "requirements.lock", "pyproject.toml", "poetry.lock",
                                 "pipfile", "pipfile.lock", "cargo.toml", "cargo.lock",
                                 "go.mod", "go.sum", "composer.json", "composer.lock")),
        ("compiler_build_config", ("foundry.toml", "hardhat.config", "truffle-config",
                                   "tsconfig.json", "webpack.config", "vite.config",
                                   "makefile", "dockerfile")),
        ("license_artifact", ("license", "copying", "notice")),
    ),
    "independent_reviewer": (
        ("protocol_contract", ("contracts/", "contract/", ".sol")),
        ("protocol_test", ("test/", "tests/", "spec/", ".t.sol")),
        ("protocol_runtime", ("src/", "bot.", "main.", "index.")),
        ("build_manifest", ("foundry.toml", "hardhat.config", "package.json")),
    ),
}

REQUIRED_FAMILIES = {
    "candidate_purpose": ("protocol_contract", "runtime_entrypoint"),
    "protocol_specialist": ("protocol_contract",),
    "solidity_security": ("protocol_contract",),
    "execution_engineer": ("execution_contract",),
    "test_verification": ("test_source", "ci_workflow", "test_config"),
    "economics_quant": ("economic_contract", "economic_runtime"),
    "dependency_license": ("dependency_manifest", "compiler_build_config", "license_artifact"),
    "independent_reviewer": ("protocol_contract",),
}


def _family_for_path(role: str, path: str) -> tuple[int, str | None]:
    normalized = PurePosixPath(path).as_posix().casefold()
    patterns = ROLE_FAMILY_PATTERNS.get(role, ROLE_FAMILY_PATTERNS["candidate_purpose"])
    for rank, (family, needles) in enumerate(patterns):
        if not any(needle in normalized for needle in needles):
            continue
        # Test verification admits genuine test suites broadly, but excludes
        # observability/UI-only tests that do not verify candidate behavior.
        if role == "test_verification" and family == "test_source":
            excluded_segments = {"monitor", "monitoring", "telemetry", "dashboard", "ui", "frontend"}
            if excluded_segments.intersection(PurePosixPath(normalized).parts):
                continue
        # Protocol/security reviewers must not consume unrelated monitoring tests.
        if role in {"solidity_security", "independent_reviewer"} and family in {
            "security_test", "protocol_test"
        }:
            protocol_markers = (
                "liquidat", "flashloan", "flash_loan", "flash-loan", "aave",
                "uniswap", "callback", "protocol", "security", "contract",
            )
            if not normalized.endswith(".t.sol") and not any(
                marker in normalized for marker in protocol_markers
            ):
                continue
        return rank, family
    return len(patterns), None


def order_role_source_manifest(role: str, manifest: Iterable[dict]) -> tuple[list[dict], dict]:
    """Interleave role-admissible source families to avoid bounded-context starvation."""
    patterns = ROLE_FAMILY_PATTERNS.get(role)
    if patterns is None:
        raise ValueError(f"unknown specialist source role: {role}")
    rows = [item for item in manifest if isinstance(item, dict) and isinstance(item.get("path"), str)]
    buckets: dict[str, list[tuple[str, dict]]] = {}
    present = set()
    for item in rows:
        _, family = _family_for_path(role, item["path"])
        if family:
            present.add(family)
            buckets.setdefault(family, []).append((item["path"].casefold(), item))
    for family in buckets:
        buckets[family].sort(key=lambda pair: pair[0])

    family_order = [family for family, _ in patterns if family in buckets]
    ordered: list[dict] = []
    depth = 0
    while True:
        added = False
        for family in family_order:
            bucket = buckets[family]
            if depth < len(bucket):
                ordered.append(bucket[depth][1])
                added = True
        if not added:
            break
        depth += 1

    required = REQUIRED_FAMILIES.get(role, ())
    missing = [family for family in required if family not in present]
    coverage = {
        "role": role,
        "required_families": list(required),
        "present_families": sorted(present),
        "missing_families": missing,
        "coverage_status": "complete" if not missing else "incomplete",
        "policy": "round_robin_role_family_priority_then_deterministic_path_order",
        "family_file_counts": {family: len(buckets[family]) for family in family_order},
        "ordered_family_prefix": [_family_for_path(role, item["path"])[1] for item in ordered],
    }
    return ordered, coverage


def role_path_admissible(role: str, path: str) -> bool:
    """Whether a finding from this role may cite this source family."""
    _, family = _family_for_path(role, path)
    if family is None:
        return False
    if role == "dependency_license":
        return family in {"dependency_manifest", "compiler_build_config", "license_artifact"}
    if role == "test_verification":
        return family in {"test_source", "ci_workflow", "test_config"}
    return True
