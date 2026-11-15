from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable


MAX_ARCHIVE_BYTES = 250 * 1024 * 1024
MAX_EXTRACTED_BYTES = 1_000 * 1024 * 1024


class ArtifactDownloadError(RuntimeError):
    pass


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Do not forward the GitHub bearer token to a redirected blob-storage host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        source_host = urllib.parse.urlparse(req.full_url).hostname
        target_host = urllib.parse.urlparse(newurl).hostname
        if source_host != target_host:
            redirected.headers = {
                key: value for key, value in redirected.headers.items()
                if key.lower() != "authorization"
            }
            redirected.unredirected_hdrs = {
                key: value for key, value in redirected.unredirected_hdrs.items()
                if key.lower() != "authorization"
            }
        return redirected


def _build_opener():
    return urllib.request.build_opener(_SafeRedirectHandler())


def _rate_limit_delay(headers, body: str, attempt: int, now: float) -> float:
    retry_after = headers.get("Retry-After") if headers else None
    if retry_after:
        try:
            return max(1.0, min(3600.0, float(retry_after)))
        except (TypeError, ValueError):
            pass
    reset_at = headers.get("X-RateLimit-Reset") if headers else None
    if reset_at:
        try:
            return max(1.0, min(3600.0, float(reset_at) - now + 5.0))
        except (TypeError, ValueError):
            pass
    return float(min(300, 15 * (2 ** min(attempt - 1, 4))))


def _is_rate_limited(status: int, body: str) -> bool:
    lowered = body.lower()
    return status == 429 or (
        status == 403 and ("rate limit exceeded" in lowered or "secondary rate limit" in lowered)
    )


def _is_retryable_server_error(status: int) -> bool:
    return status in {500, 502, 503, 504}


def download_artifact(
    repository: str,
    artifact_id: int,
    destination: Path,
    token: str,
    *,
    max_wait_seconds: int = 7200,
    api_base_url: str = "https://api.github.com",
    opener=None,
    sleep_fn: Callable[[float], None] = time.sleep,
    clock_fn: Callable[[], float] = time.time,
) -> Path:
    if not token:
        raise ArtifactDownloadError("GH_TOKEN or GITHUB_TOKEN is required")
    if "/" not in repository or repository.count("/") != 1:
        raise ArtifactDownloadError("repository must be in owner/name form")
    if artifact_id <= 0 or max_wait_seconds < 0:
        raise ArtifactDownloadError("artifact_id must be positive and max_wait_seconds non-negative")

    api_url = (
        api_base_url.rstrip("/")
        + f"/repos/{repository}/actions/artifacts/{artifact_id}/zip"
    )
    request = urllib.request.Request(
        api_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "flashloan-research-artifact-restore/1.0",
        },
        method="GET",
    )
    client = opener or _build_opener()
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")
    deadline = clock_fn() + max_wait_seconds
    attempt = 0

    while True:
        attempt += 1
        try:
            with client.open(request, timeout=90) as response:
                total = 0
                with partial.open("wb") as output:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MAX_ARCHIVE_BYTES:
                            raise ArtifactDownloadError("artifact archive exceeds 250 MiB safety limit")
                        output.write(chunk)
            if total == 0 or not zipfile.is_zipfile(partial):
                raise ArtifactDownloadError("GitHub artifact response is empty or not a ZIP archive")
            with zipfile.ZipFile(partial) as archive:
                bad_member = archive.testzip()
                if bad_member is not None:
                    raise ArtifactDownloadError(f"artifact ZIP CRC verification failed: {bad_member}")
            partial.replace(target)
            return target
        except urllib.error.HTTPError as exc:
            body = exc.read(16_384).decode("utf-8", errors="replace")
            rate_limited = _is_rate_limited(exc.code, body)
            transient_server_error = _is_retryable_server_error(exc.code)
            if not rate_limited and not transient_server_error:
                raise ArtifactDownloadError(
                    f"GitHub artifact download failed with HTTP {exc.code}: {body[:1000]}"
                ) from exc
            remaining = deadline - clock_fn()
            if remaining <= 0:
                reason = "API rate limit" if rate_limited else "transient server error"
                raise ArtifactDownloadError(
                    f"artifact {reason} persisted after {max_wait_seconds} seconds: {body[:500]}"
                ) from exc
            if rate_limited:
                delay = min(_rate_limit_delay(exc.headers, body, attempt, clock_fn()), remaining)
                label = "GitHub artifact API rate-limited"
            else:
                delay = min(float(min(300, 5 * (2 ** min(attempt - 1, 5)))), remaining)
                label = f"GitHub artifact endpoint returned HTTP {exc.code}"
            print(
                f"{label} (attempt {attempt}); retrying in {int(delay)} seconds.",
                flush=True,
            )
            partial.unlink(missing_ok=True)
            sleep_fn(delay)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            remaining = deadline - clock_fn()
            if remaining <= 0:
                raise ArtifactDownloadError(
                    f"artifact download network retry window exhausted: {type(exc).__name__}: {exc}"
                ) from exc
            delay = min(float(min(120, 5 * (2 ** min(attempt - 1, 4)))), remaining)
            print(
                f"Artifact download network error (attempt {attempt}); retrying in {int(delay)} seconds.",
                flush=True,
            )
            partial.unlink(missing_ok=True)
            sleep_fn(delay)


def safe_extract(archive_path: Path, destination: Path) -> None:
    root = Path(destination).resolve()
    root.mkdir(parents=True, exist_ok=True)
    extracted_bytes = 0
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            relative = PurePosixPath(member.filename)
            if relative.is_absolute() or not relative.parts or any(
                part in {"", ".", ".."} for part in relative.parts
            ):
                raise ArtifactDownloadError(f"unsafe ZIP member path: {member.filename!r}")
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ArtifactDownloadError(f"symbolic links are not permitted in artifact: {member.filename}")
            target = (root / Path(*relative.parts)).resolve()
            if target != root and root not in target.parents:
                raise ArtifactDownloadError(f"ZIP member escapes extraction root: {member.filename!r}")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            extracted_bytes += member.file_size
            if extracted_bytes > MAX_EXTRACTED_BYTES:
                raise ArtifactDownloadError("artifact expands beyond 1 GiB safety limit")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download a GitHub Actions artifact by ID with rate-limit-aware retry."
    )
    parser.add_argument("--repository", required=True)
    parser.add_argument("--artifact-id", type=int, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--extract-to", type=Path, required=True)
    parser.add_argument("--max-wait-seconds", type=int, default=7200)
    args = parser.parse_args()
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    try:
        archive = download_artifact(
            args.repository,
            args.artifact_id,
            args.destination,
            token,
            max_wait_seconds=args.max_wait_seconds,
        )
        safe_extract(archive, args.extract_to)
        print(
            f"Downloaded and verified artifact {args.artifact_id}; "
            f"archive={archive}; extracted_to={args.extract_to}",
            flush=True,
        )
    except ArtifactDownloadError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
