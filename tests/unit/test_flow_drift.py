"""Test suite for simplicio-loop-quality declarative flow and drift prevention.

Enforces criteria of issue #165 (Langflow + Mermaid/imagem contract simplicio.flow/v1):
- Drift test: validates that flow.json references only existing files, lines, and symbols.
- Completeness: verifies that flow.json, .mmd, .svg/.png and .langflow.json exist.
- Determinism: verifies identical byte output across multiple generator runs.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.generate_flow import (
    FLOW_JSON_PATH,
    FLOW_SCHEMA,
    LANGFLOW_JSON_PATH,
    MMD_PATH,
    PNG_PATH,
    REPO_ROOT,
    SVG_PATH,
    build_langflow_json,
    build_mermaid,
    validate_drift,
)


class TestFlowDrift(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(FLOW_JSON_PATH.exists(), f"Missing {FLOW_JSON_PATH}")
        with open(FLOW_JSON_PATH, "r", encoding="utf-8") as f:
            self.flow_data = json.load(f)

    def test_schema_conformance(self) -> None:
        self.assertEqual(self.flow_data.get("schema"), FLOW_SCHEMA)
        self.assertIn("inputs", self.flow_data)
        self.assertIn("nodes", self.flow_data)
        self.assertIn("edges", self.flow_data)
        self.assertIn("outputs", self.flow_data)
        self.assertGreater(len(self.flow_data["inputs"]), 0)
        self.assertGreater(len(self.flow_data["nodes"]), 0)
        self.assertGreater(len(self.flow_data["edges"]), 0)
        self.assertGreater(len(self.flow_data["outputs"]), 0)

    def test_no_code_drift(self) -> None:
        errors = validate_drift(self.flow_data)
        self.assertEqual(errors, [], "Code drift detected:\n" + "\n".join(errors))

    def test_deterministic_mermaid_generation(self) -> None:
        mmd_first = build_mermaid(self.flow_data)
        mmd_second = build_mermaid(self.flow_data)
        self.assertEqual(mmd_first, mmd_second)
        self.assertIn("flowchart TD", mmd_first)
        self.assertIn("subgraph Inputs", mmd_first)
        self.assertIn("subgraph Steps", mmd_first)
        self.assertIn("subgraph Outputs", mmd_first)

    def test_deterministic_langflow_generation(self) -> None:
        lf_first = build_langflow_json(self.flow_data)
        lf_second = build_langflow_json(self.flow_data)
        self.assertEqual(
            json.dumps(lf_first, sort_keys=True),
            json.dumps(lf_second, sort_keys=True),
        )
        self.assertEqual(lf_first["name"], "simplicio-loop-quality")
        self.assertIn("nodes", lf_first["data"])
        self.assertIn("edges", lf_first["data"])

    def test_artifacts_exist_and_non_empty(self) -> None:
        self.assertTrue(FLOW_JSON_PATH.exists() and FLOW_JSON_PATH.stat().st_size > 0)
        self.assertTrue(MMD_PATH.exists() and MMD_PATH.stat().st_size > 0)
        self.assertTrue(SVG_PATH.exists() and SVG_PATH.stat().st_size > 0)
        self.assertTrue(PNG_PATH.exists() and PNG_PATH.stat().st_size > 0)
        self.assertTrue(LANGFLOW_JSON_PATH.exists() and LANGFLOW_JSON_PATH.stat().st_size > 0)


if __name__ == "__main__":
    unittest.main()
