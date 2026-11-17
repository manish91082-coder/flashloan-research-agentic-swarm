from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

FORBIDDEN_KEYS = {
    "expected_label", "gold_label", "reference_label", "ground_truth_label",
    "answer_key", "answer_labels", "label_key", "correct_label", "target_label",
}
FORBIDDEN_TEXT = (
    b'"expected_label"', b'"gold_label"', b'"reference_label"',
    b'"ground_truth_label"', b'"answer_key"', b'"answer_labels"',
    b'"label_key"', b'"correct_label"', b'"target_label"',
)
MANIFEST_NAME = "fixture_manifest.json"


def _scan_json(value: object, location: str, findings: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and key.lower() in FORBIDDEN_KEYS:
                findings.append(f"{location}: forbidden answer-key field {key}")
            _scan_json(child, f"{location}.{key}", findings)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_json(child, f"{location}[{index}]", findings)


def scan_artifact(path: Path) -> dict:
    findings: list[str] = []
    entries: dict[str, bytes] = {}
    if path.is_dir():
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file():
                relative = file_path.relative_to(path).as_posix()
                entries[relative] = file_path.read_bytes()
    elif path.is_file() and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.endswith("/") or name.startswith("/") or ".." in Path(name).parts:
                    findings.append(f"unsafe archive entry path: {name}")
                    continue
                entries[name] = archive.read(name)
    else:
        raise ValueError("artifact path must be a directory or ZIP archive")

    manifests = [(name, raw) for name, raw in entries.items() if Path(name).name == MANIFEST_NAME]
    if len(manifests) != 1:
        findings.append(f"artifact must contain exactly one {MANIFEST_NAME}")
    for name, raw in entries.items():
        lowered = name.lower()
        if any(token in lowered for token in ("answer-key", "answer_key", "reference-labels", "ground-truth-labels")):
            findings.append(f"answer-key-like filename is forbidden: {name}")
        for token in FORBIDDEN_TEXT:
            if token in raw:
                findings.append(f"{name}: forbidden answer-key field token {token.decode('ascii')}")
        if name.lower().endswith(".json"):
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                findings.append(f"{name}: invalid UTF-8 JSON: {exc}")
            else:
                _scan_json(parsed, name, findings)

    if len(manifests) == 1:
        name, raw = manifests[0]
        try:
            manifest = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            findings.append(f"{name}: invalid fixture manifest JSON: {exc}")
            manifest = None
        if isinstance(manifest, dict):
            if manifest.get("benchmark_id") != "r15d-semantic-source-facts-v2":
                findings.append("fixture manifest benchmark ID is not R15D v2")
            if manifest.get("status") != "built_pending_independent_adjudication":
                findings.append("fixture manifest status is not pending independent adjudication")
            if manifest.get("answer_key_included") is not False:
                findings.append("fixture manifest must explicitly assert answer_key_included=false")
            cases = manifest.get("cases")
            if not isinstance(cases, list) or len(cases) != 6:
                findings.append("fixture manifest must contain exactly six cases")
            elif len({case.get("id") for case in cases if isinstance(case, dict)}) != 6 or any(not isinstance(case, dict) for case in cases):
                findings.append("fixture manifest case IDs must be six unique objects")
            if any(isinstance(case, dict) and "label" in case for case in (cases if isinstance(cases, list) else [])):
                findings.append("fixture manifest must not contain adjudication label fields")

    return {
        "valid": not findings,
        "file_count": len(entries),
        "manifest_count": len(manifests),
        "findings": findings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail closed if an R15D v2 reviewer-facing artifact contains answer-key material.")
    parser.add_argument("--path", type=Path, required=True)
    args = parser.parse_args()
    result = scan_artifact(args.path)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
