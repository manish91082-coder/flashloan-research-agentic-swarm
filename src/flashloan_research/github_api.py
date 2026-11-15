from __future__ import annotations

import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .config import SETTINGS, Settings


class GitHubAPIError(RuntimeError):
    pass


class GitHubClient:
    """Small read-only GitHub REST client with bounded retries and backoff."""

    def __init__(self, settings: Settings = SETTINGS, opener: Any = urllib.request.urlopen,
                 sleep: Any = time.sleep, clock: Any = time.time):
        self.settings = settings
        self.opener = opener
        self.sleep = sleep
        self.clock = clock

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": self.settings.user_agent,
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        return headers

    def get(self, path: str, params: dict[str, str] | None = None) -> Any:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("API path must be a relative absolute-path under the configured host")
        query = urllib.parse.urlencode(params or {})
        url = f"{self.settings.api_base}{path}" + (f"?{query}" if query else "")
        request = urllib.request.Request(url, headers=self._headers(), method="GET")
        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                with self.opener(request, timeout=self.settings.request_timeout_seconds) as response:
                    payload = response.read()
                    return json.loads(payload.decode("utf-8"))
            except urllib.error.HTTPError as exc:
                last_error = exc
                retry_after = exc.headers.get("Retry-After")
                remaining = exc.headers.get("X-RateLimit-Remaining")
                reset = exc.headers.get("X-RateLimit-Reset")
                retryable = exc.code in (403, 429, 500, 502, 503, 504)
                rate_limited = exc.code in (403, 429) and (remaining == "0" or retry_after is not None)
                if not retryable or attempt >= self.settings.max_retries:
                    body = exc.read(500).decode("utf-8", errors="replace")
                    raise GitHubAPIError(f"GitHub API HTTP {exc.code}: {body}") from exc
                if rate_limited and reset and remaining == "0":
                    # Primary API quotas reset on an absolute epoch timestamp.
                    # Waiting only 60 seconds causes repeated failures for the
                    # remainder of the hour and burns the candidate retry budget.
                    reset_at = int(reset)
                    now = int(self.clock())
                    delay = max(1, min(3600, reset_at - now + 1))
                elif retry_after:
                    # Respect GitHub's Retry-After window for secondary limits.
                    delay = max(1, min(3600, int(retry_after)))
                else:
                    delay = min(30, (2 ** attempt) + random.random())
                print(json.dumps({
                    "event": "github_api_retry",
                    "path": path,
                    "http_status": exc.code,
                    "attempt": attempt + 1,
                    "max_attempts": self.settings.max_retries + 1,
                    "rate_limited": rate_limited,
                    "rate_limit_remaining": remaining,
                    "rate_limit_reset": reset,
                    "retry_after": retry_after,
                    "sleep_seconds": delay,
                }, sort_keys=True), file=sys.stderr, flush=True)
                self.sleep(delay)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt >= self.settings.max_retries:
                    raise GitHubAPIError(f"GitHub API request failed after retries: {exc}") from exc
                delay = min(30, (2 ** attempt) + random.random())
                print(json.dumps({
                    "event": "github_api_retry",
                    "path": path,
                    "error_type": type(exc).__name__,
                    "attempt": attempt + 1,
                    "max_attempts": self.settings.max_retries + 1,
                    "sleep_seconds": round(delay, 2),
                }, sort_keys=True), file=sys.stderr, flush=True)
                self.sleep(delay)
        raise GitHubAPIError(f"GitHub API request failed: {last_error}")

    def search_repositories(self, query: str, per_page: int = 30, page: int = 1) -> list[dict[str, Any]]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if not 1 <= per_page <= 100 or page < 1:
            raise ValueError("per_page must be 1..100 and page must be >= 1")
        result = self.get("/search/repositories", {"q": query, "per_page": str(per_page), "page": str(page), "sort": "updated", "order": "desc"})
        items = result.get("items")
        if not isinstance(items, list):
            raise GitHubAPIError("GitHub repository search response has no items array")
        return items

    def repository(self, full_name: str) -> dict[str, Any]:
        owner, sep, repo = full_name.partition("/")
        if not sep or not owner or not repo or "/" in repo:
            raise ValueError("repository must be owner/name")
        return self.get(f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}")

    def commit(self, full_name: str, ref: str) -> dict[str, Any]:
        owner, repo = full_name.split("/", 1)
        return self.get(f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/commits/{urllib.parse.quote(ref)}")

    def tree(self, full_name: str, tree_sha: str, recursive: bool = True) -> dict[str, Any]:
        owner, repo = full_name.split("/", 1)
        params = {"recursive": "1"} if recursive else None
        return self.get(f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/git/trees/{tree_sha}", params)

    def blob(self, full_name: str, blob_sha: str) -> dict[str, Any]:
        owner, repo = full_name.split("/", 1)
        return self.get(f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/git/blobs/{blob_sha}")
