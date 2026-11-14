from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class ModelProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelIdentity:
    provider: str
    model: str
    base_url: str
    prompt_template_version: str


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ModelProviderError("model endpoint redirects are disabled")


class LocalOpenAICompatibleProvider:
    """Strict local-only OpenAI-compatible chat-completions adapter.

    The adapter intentionally rejects non-loopback hosts. No cloud inference,
    API keys, or paid fallback are supported by this implementation.
    """

    def __init__(self, base_url: str | None = None, model: str | None = None,
                 timeout_seconds: int = 120, prompt_template_version: str = "1.0.0"):
        self.base_url = (base_url or os.getenv("FLR_MODEL_BASE_URL", "")).strip().rstrip("/")
        self.model = (model or os.getenv("FLR_MODEL_NAME", "")).strip()
        self.timeout_seconds = timeout_seconds
        self.prompt_template_version = prompt_template_version
        if not self.base_url:
            raise ModelProviderError("FLR_MODEL_BASE_URL is not configured")
        parsed = urllib.parse.urlparse(self.base_url)
        if parsed.scheme != "http" or not parsed.hostname:
            raise ModelProviderError("local model endpoint must use http:// and include a host")
        try:
            addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 80, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise ModelProviderError(f"cannot resolve local model endpoint: {exc}") from exc
        if not addresses or any(not address[4][0].startswith(("127.", "::1")) for address in addresses):
            raise ModelProviderError("only loopback model endpoints are permitted; cloud endpoints are disabled")
        if not self.model:
            raise ModelProviderError("FLR_MODEL_NAME is required for local inference")
        if not 1 <= timeout_seconds <= 600:
            raise ModelProviderError("timeout_seconds must be between 1 and 600")

    @property
    def identity(self) -> ModelIdentity:
        return ModelIdentity(
            provider="local_openai_compatible",
            model=self.model,
            base_url=self.base_url,
            prompt_template_version=self.prompt_template_version,
        )

    def generate_json(self, system_prompt: str, user_payload: dict[str, Any],
                      required_keys: set[str], max_output_chars: int = 30000) -> dict[str, Any]:
        if not system_prompt.strip():
            raise ModelProviderError("system_prompt cannot be empty")
        if not isinstance(user_payload, dict):
            raise ModelProviderError("user_payload must be a JSON object")
        endpoint = self.base_url + "/v1/chat/completions"
        body = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
            ],
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            opener = urllib.request.build_opener(_NoRedirect())
            with opener.open(request, timeout=self.timeout_seconds) as response:
                raw = response.read(2_000_001)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ModelProviderError(f"local model request failed: {type(exc).__name__}: {exc}") from exc
        if len(raw) > 2_000_000:
            raise ModelProviderError("local model response exceeded 2 MB")
        try:
            envelope = json.loads(raw.decode("utf-8"))
            content = envelope["choices"][0]["message"]["content"]
            result = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise ModelProviderError("model returned malformed OpenAI-compatible JSON response") from exc
        if not isinstance(result, dict):
            raise ModelProviderError("model output must be a JSON object")
        missing = sorted(required_keys - set(result))
        if missing:
            raise ModelProviderError(f"model output missing required keys: {missing}")
        if len(json.dumps(result, ensure_ascii=False)) > max_output_chars:
            raise ModelProviderError("model output exceeded configured character budget")
        return result


def provider_from_environment() -> LocalOpenAICompatibleProvider:
    return LocalOpenAICompatibleProvider()
