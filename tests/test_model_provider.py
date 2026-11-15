from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from flashloan_research.model_provider import (
    LocalOpenAICompatibleProvider,
    ModelProviderError,
)


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

    def test_local_provider_sends_required_json_schema_and_returns_object(self):
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        result = provider.generate_json(
            "Classify the repository purpose using evidence only.",
            {"repository": "org/repo", "source_excerpt": "function liquidate()"},
            {"purpose", "confidence"},
        )
        self.assertEqual(result["purpose"], "liquidation bot")
        self.assertEqual(provider.identity.provider, "local_openai_compatible")
        response_format = Handler.body["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        self.assertEqual(
            response_format["json_schema"]["schema"]["required"],
            ["confidence", "purpose"],
        )
        self.assertIn("OUTPUT CONTRACT", Handler.body["messages"][0]["content"])
        self.assertIn('"purpose"', Handler.body["messages"][0]["content"])
        self.assertEqual(Handler.body["temperature"], 0)

    def test_full_specialist_schema_includes_evidence_and_reviewer_contracts(self):
        Handler.response_content = json.dumps({
            "summary": "Unknown until source evidence is sufficient.",
            "purpose": "unknown",
            "implementation_status": "unknown",
            "findings": [],
            "evidence": [],
            "unknowns": ["No evidence was selected."],
            "confidence": "low",
            "review_decision": "not_applicable",
            "review_disagreements": [],
        })
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        required = {
            "summary", "purpose", "implementation_status", "findings", "evidence",
            "unknowns", "confidence", "review_decision", "review_disagreements",
        }
        result = provider.generate_json(
            "Return evidence-grounded specialist output.",
            {"source_evidence_catalog": [], "role": "candidate_purpose"},
            required,
        )
        self.assertEqual(result["implementation_status"], "unknown")
        schema = Handler.body["response_format"]["json_schema"]["schema"]
        self.assertIn("review_decision", schema["properties"])
        self.assertIn("review_disagreements", schema["properties"])
        self.assertIn("evidence_refs", schema["properties"]["findings"]["items"]["properties"])
        system_prompt = Handler.body["messages"][0]["content"]
        self.assertIn("source_evidence_catalog", system_prompt)
        self.assertIn("Never invent IDs", system_prompt)

    def test_review_decision_schema_is_conditioned_on_task_role(self):
        required = {
            "summary", "purpose", "implementation_status", "findings", "evidence",
            "unknowns", "confidence", "review_decision", "review_disagreements",
        }
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        Handler.response_content = json.dumps({
            "summary": "Source-supported purpose classification.",
            "purpose": "liquidator",
            "implementation_status": "partial",
            "findings": [],
            "evidence": ["EV00001"],
            "unknowns": ["Runtime behavior not tested."],
            "confidence": "low",
            "review_decision": "not_applicable",
            "review_disagreements": [],
        })
        provider.generate_json(
            "Classify purpose.", {"role": "candidate_purpose", "source_evidence_catalog": []}, required,
        )
        specialist_enum = Handler.body["response_format"]["json_schema"]["schema"]["properties"]["review_decision"]["enum"]
        self.assertEqual(specialist_enum, ["not_applicable"])

        Handler.response_content = json.dumps({
            "summary": "Independent review of prior source reports.",
            "purpose": "liquidator",
            "implementation_status": "partial",
            "findings": [],
            "evidence": ["EV00001"],
            "unknowns": ["Runtime behavior not tested."],
            "confidence": "low",
            "review_decision": "accept_with_reservations",
            "review_disagreements": ["No proof of runtime profitability."],
        })
        provider.generate_json(
            "Review prior analysis.", {"role": "independent_reviewer", "source_evidence_catalog": []}, required,
        )
        reviewer_enum = Handler.body["response_format"]["json_schema"]["schema"]["properties"]["review_decision"]["enum"]
        self.assertEqual(reviewer_enum, ["accept", "accept_with_reservations", "reject", "inconclusive"])
        self.assertNotIn("not_applicable", reviewer_enum)

    def test_full_output_schema_requires_a_recognized_role(self):
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        required = {
            "summary", "purpose", "implementation_status", "findings", "evidence",
            "unknowns", "confidence", "review_decision", "review_disagreements",
        }
        with self.assertRaisesRegex(ModelProviderError, "recognized specialist role"):
            provider.generate_json("Classify.", {"repository": "org/repo"}, required)

    def test_rejects_non_loopback_model_hosts(self):
        with patch(
            "flashloan_research.model_provider.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("203.0.113.10", 80))],
        ):
            with self.assertRaises(ModelProviderError):
                LocalOpenAICompatibleProvider("http://model.example:11434", "model")

    def test_rejects_missing_required_keys(self):
        Handler.response_content = '{"purpose":"unknown"}'
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        with self.assertRaisesRegex(ModelProviderError, "missing required keys"):
            provider.generate_json(
                "Classify.",
                {"repo": "org/repo"},
                {"purpose", "confidence"},
            )

    def test_rejects_unexpected_top_level_keys(self):
        Handler.response_content = '{"purpose":"unknown","confidence":"low","extra":"not allowed"}'
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        with self.assertRaisesRegex(ModelProviderError, "unexpected top-level keys"):
            provider.generate_json(
                "Classify.",
                {"repo": "org/repo"},
                {"purpose", "confidence"},
            )

    def test_rejects_unsupported_schema_key_before_network_call(self):
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        with self.assertRaisesRegex(ModelProviderError, "no output schema"):
            provider.generate_json("Classify.", {"repo": "org/repo"}, {"unsupported"})
        self.assertIsNone(Handler.body)

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
