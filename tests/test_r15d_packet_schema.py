import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "research/R15D_BLIND_ADJUDICATION_PACKET.schema.json"
PACKET_PATH = ROOT / "research_runs/r15d_adjudication/blind_adjudication_packet.json"


class R15DSchemaContractTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))

    def test_schema_is_draft_2020_12_and_rejects_unknown_top_level_fields(self):
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(self.schema["additionalProperties"])
        self.assertEqual(set(self.schema["required"]), set(self.packet))

    def test_schema_requires_exact_blinding_and_safety_invariants(self):
        properties = self.schema["properties"]
        for name in ("expected_labels_omitted", "model_outputs_omitted",
                     "reviewers_must_not_consult_model_outputs", "reviewers_must_work_independently"):
            self.assertIs(properties["blinding"]["properties"][name]["const"], True)
        for name, rule in properties["safety"]["properties"].items():
            self.assertIs(rule["const"], False)

    def test_schema_bounds_case_and_reviewer_cardinality(self):
        cases = self.schema["properties"]["cases"]
        self.assertEqual((cases["minItems"], cases["maxItems"]), (6, 6))
        case = cases["items"]["properties"]
        self.assertEqual((case["reviewers"]["minItems"], case["reviewers"]["maxItems"]), (2, 2))
        self.assertIn("$defs/review", case["reviewers"]["items"]["$ref"])

    def test_schema_keeps_model_inference_unauthorized(self):
        freeze = self.schema["properties"]["freeze"]["properties"]
        self.assertIs(freeze["model_inference_authorized"]["const"], False)


if __name__ == "__main__":
    unittest.main()
