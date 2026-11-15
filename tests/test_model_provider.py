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
    finish_reason = "stop"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        Handler.body = json.loads(self.rfile.read(length))
        payload = {
            "choices": [{
                "message": {"content": Handler.response_content},
                "finish_reason": Handler.finish_reason,
            }],
            "usage": {"completion_tokens": 12},
        }
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
        Handler.finish_reason = "stop"

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

    def test_full_specialist_schema_excludes_reviewer_only_fields(self):
        Handler.response_content = json.dumps({
            "summary": "Unknown until source evidence is sufficient.",
            "purpose": "unknown",
            "implementation_status": "unknown",
            "findings": [],
            "evidence": [],
            "unknowns": ["No evidence was selected."],
            "confidence": "low",
        })
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        required = {
            "summary", "purpose", "implementation_status", "findings", "evidence",
            "unknowns", "confidence",
        }
        result = provider.generate_json(
            "Return evidence-grounded specialist output.",
            {"source_evidence_catalog": [], "role": "candidate_purpose"},
            required,
        )
        self.assertEqual(result["implementation_status"], "unknown")
        schema = Handler.body["response_format"]["json_schema"]["schema"]
        self.assertNotIn("review_decision", schema["properties"])
        self.assertNotIn("review_disagreements", schema["properties"])
        self.assertIn("evidence_refs", schema["properties"]["findings"]["items"]["properties"])
        self.assertIn("source_evidence_catalog", Handler.body["messages"][0]["content"])

    def test_reviewer_schema_requires_explicit_review_fields_and_excludes_not_applicable(self):
        required = {
            "summary", "purpose", "implementation_status", "findings", "evidence",
            "unknowns", "confidence", "review_decision", "review_disagreements",
        }
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
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        provider.generate_json(
            "Review prior analysis.",
            {"role": "independent_reviewer", "source_evidence_catalog": [{"evidence_id": "EV00001"}]},
            required,
        )
        properties = Handler.body["response_format"]["json_schema"]["schema"]["properties"]
        self.assertEqual(
            properties["review_decision"]["enum"],
            ["accept", "accept_with_reservations", "reject", "inconclusive"],
        )

    def test_evidence_schema_items_are_enum_limited_to_current_pinned_catalog(self):
        Handler.response_content = json.dumps({
            "summary": "Purpose observed in pinned source.",
            "purpose": "flash loan liquidation prototype",
            "implementation_status": "partial",
            "findings": [{
                "finding_id": "F-1",
                "claim": "A callback function is declared.",
                "category": "protocol_flow",
                "severity": "informational",
                "claim_status": "source_observed",
                "confidence": "low",
                "evidence_refs": ["EV00002"],
            }],
            "evidence": ["EV00002"],
            "unknowns": ["Runtime behavior not tested."],
            "confidence": "low",
        })
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        required = {
            "summary", "purpose", "implementation_status", "findings",
            "evidence", "unknowns", "confidence",
        }
        catalog = [
            {"evidence_id": "EV00001", "path": "A.sol", "line": 3},
            {"evidence_id": "EV00002", "path": "B.sol", "line": 9},
        ]
        provider.generate_json(
            "Return only evidence IDs.", {"role": "candidate_purpose",
                                           "source_evidence_catalog": catalog}, required,
        )
        schema = Handler.body["response_format"]["json_schema"]["schema"]
        self.assertEqual(schema["properties"]["evidence"]["items"]["enum"], ["EV00001", "EV00002"])
        self.assertEqual(
            schema["properties"]["findings"]["items"]["properties"]["evidence_refs"]["items"]["enum"],
            ["EV00001", "EV00002"],
        )
        self.assertEqual(Handler.body["max_tokens"], 1200)

    def test_empty_catalog_forces_empty_evidence_and_findings(self):
        Handler.response_content = json.dumps({
            "summary": "No source evidence supplied.",
            "purpose": "unknown",
            "implementation_status": "unknown",
            "findings": [],
            "evidence": [],
            "unknowns": ["No source evidence catalog exists."],
            "confidence": "low",
        })
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        required = {
            "summary", "purpose", "implementation_status", "findings",
            "evidence", "unknowns", "confidence",
        }
        provider.generate_json(
            "Return unknown when there is no evidence.",
            {"role": "candidate_purpose", "source_evidence_catalog": []},
            required,
        )
        schema = Handler.body["response_format"]["json_schema"]["schema"]
        self.assertEqual(schema["properties"]["evidence"]["maxItems"], 0)
        self.assertEqual(schema["properties"]["findings"]["maxItems"], 0)

    def test_duplicate_or_malformed_catalog_evidence_ids_are_rejected(self):
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        required = {"summary", "purpose", "implementation_status", "findings", "evidence", "unknowns", "confidence"}
        with self.assertRaisesRegex(ModelProviderError, "unique stable EV evidence IDs"):
            provider.generate_json(
                "Classify.",
                {"role": "candidate_purpose", "source_evidence_catalog": [
                    {"evidence_id": "EV00001"}, {"evidence_id": "EV00001"}
                ]},
                required,
            )
        self.assertIsNone(Handler.body)

    def test_reviewer_only_schema_requires_independent_reviewer_role(self):
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        required = {
            "summary", "purpose", "implementation_status", "findings", "evidence",
            "unknowns", "confidence", "review_decision", "review_disagreements",
        }
        with self.assertRaisesRegex(ModelProviderError, "reviewer-only output fields"):
            provider.generate_json("Review.", {"repository": "org/repo"}, required)
    def test_accepts_fenced_json_model_content(self):
        Handler.response_content = ' ```json\n{"purpose":"liquidation bot","confidence":"low"}\n``` '
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        result = provider.generate_json(
            "Classify.", {"repo": "org/repo"}, {"purpose", "confidence"},
        )
        self.assertEqual(result["purpose"], "liquidation bot")

    def test_accepts_preparsed_json_content_object(self):
        Handler.response_content = {"purpose": "liquidation bot", "confidence": "low"}
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        result = provider.generate_json(
            "Classify.", {"repo": "org/repo"}, {"purpose", "confidence"},
        )
        self.assertEqual(result["confidence"], "low")

    def test_malformed_json_error_includes_finish_reason_and_content_preview(self):
        Handler.response_content = '{"purpose":'
        Handler.finish_reason = "length"
        provider = LocalOpenAICompatibleProvider(self.url, "test-model")
        with self.assertRaisesRegex(ModelProviderError, "finish_reason.*length") as caught:
            provider.generate_json(
                "Classify.", {"repo": "org/repo"}, {"purpose", "confidence"},
            )
        self.assertIn("content_preview", str(caught.exception))
        self.assertIn("content_chars", str(caught.exception))

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
