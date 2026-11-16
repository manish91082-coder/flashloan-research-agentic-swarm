from __future__ import annotations

import hashlib
import json
import unittest

from scripts.run_r15d_reviewer_benchmark import (
    git_blob_sha,
    load_finish_reason,
    load_model_output,
)


class R15DReviewerBenchmarkHelpersTests(unittest.TestCase):
    def test_git_blob_sha_matches_git_object_hash(self):
        content = b"source-pinned benchmark fixture"
        expected = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        self.assertEqual(git_blob_sha(content), expected)

    def test_load_model_output_parses_openai_compatible_json_content(self):
        output = {
            "review_decision": "inconclusive",
            "findings": [],
            "unknowns": ["The callback caller check is not established by the supplied excerpt."],
        }
        envelope = {
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": json.dumps(output)},
            }]
        }
        exchange = {"response_raw": json.dumps(envelope)}
        self.assertEqual(load_model_output(exchange), output)
        self.assertEqual(load_finish_reason(exchange), "stop")

    def test_load_model_output_fails_closed_on_malformed_response(self):
        exchange = {"response_raw": "{not-json"}
        self.assertIsNone(load_model_output(exchange))
        self.assertIsNone(load_finish_reason(exchange))

    def test_load_model_output_accepts_structured_content_object(self):
        output = {"review_decision": "inconclusive", "findings": []}
        envelope = {"choices": [{"finish_reason": "stop", "message": {"content": output}}]}
        exchange = {"response_raw": json.dumps(envelope)}
        self.assertEqual(load_model_output(exchange), output)


if __name__ == "__main__":
    unittest.main()
