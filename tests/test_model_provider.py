from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from flashloan_research.model_provider import LocalOpenAICompatibleProvider, ModelProviderError


class Handler(BaseHTTPRequestHandler):
    body = None
    response_content = '{"purpose":"liquidation bot","confidence":"low"}'
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        Handler.body = json.loads(self.rfile.read(length))
        payload = {"choices": [{"message": {"content": Handler.response_content}}]}
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def log_message(self, *_):
        pass


class LocalModelProviderTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        Handler.body = None
        Handler.response_content = '{"purpose":"liquidation bot","confidence":"low"}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_local_provider_sends_json_mode_and_returns_structured_object(self):
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        result = provider.generate_json(
            "Classify the repository purpose using evidence only.",
            {"repository": "org/repo", "source_excerpt": "function liquidate()"},
            {"purpose", "confidence"},
        )
        self.assertEqual(result["purpose"], "liquidation bot")
        self.assertEqual(provider.identity.provider, "local_openai_compatible")
        self.assertEqual(Handler.body["response_format"], {"type": "json_object"})
        self.assertEqual(Handler.body["temperature"], 0)

    def test_rejects_non_loopback_model_hosts(self):
        with patch("flashloan_research.model_provider.socket.getaddrinfo",
                   return_value=[(2, 1, 6, "", ("203.0.113.10", 80))]):
            with self.assertRaises(ModelProviderError):
                LocalOpenAICompatibleProvider("http://model.example:11434", "model")

    def test_rejects_missing_required_keys(self):
        Handler.response_content = '{"purpose":"unknown"}'
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        with self.assertRaises(ModelProviderError):
            provider.generate_json("Classify.", {"repo": "org/repo"}, {"purpose", "confidence"})

    def test_rejects_non_json_model_content(self):
        Handler.response_content = "not json"
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        with self.assertRaises(ModelProviderError):
            provider.generate_json("Classify.", {"repo": "org/repo"}, {"purpose"})

    def test_requires_explicit_model_name(self):
        with self.assertRaises(ModelProviderError):
            LocalOpenAICompatibleProvider(self.url, "")


if __name__ == "__main__":
    unittest.main()
