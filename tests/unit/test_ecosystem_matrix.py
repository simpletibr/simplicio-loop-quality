import unittest

from simplicio_loop_quality.ecosystem_matrix import (
    build_integration_matrix,
    evaluate_matrix_results,
)


class EcosystemMatrixTest(unittest.TestCase):
    def test_matrix_covers_isolated_and_combined_components(self):
        matrix = build_integration_matrix(optional_components=("runtime", "mapper"))
        self.assertIn("loop+quality", matrix["cases"])
        self.assertIn("loop+quality+mapper+runtime", matrix["cases"])
        self.assertEqual(len(matrix["cases"]), 4)

    def test_complete_bound_results_pass(self):
        cases = tuple(build_integration_matrix(optional_components=())["cases"])
        results = [
            {
                "case": case,
                "status": "PASS",
                "source_sha": "source",
                "policy_hash": "policy",
                "evidence_refs": [f"evidence/{case}"],
            }
            for case in cases
        ]
        verdict = evaluate_matrix_results(
            results,
            expected_cases=cases,
            source_sha="source",
            policy_hash="policy",
        )
        self.assertEqual(verdict["status"], "PASS")

    def test_missing_case_blocks(self):
        verdict = evaluate_matrix_results(
            [],
            expected_cases=("loop+quality",),
            source_sha="source",
            policy_hash="policy",
        )
        self.assertEqual(verdict["status"], "FAIL")
        self.assertIn("MATRIX_CASE_MISSING", verdict["reason_codes"])

    def test_mismatches_and_edge_cases(self):
        results = [
            {
                "case": "loop+quality",
                "status": "FAIL",
                "source_sha": "wrong-sha",
                "policy_hash": "wrong-policy",
                "evidence_refs": [],
            },
            {
                "case": "loop+quality",
                "status": "PASS",
                "source_sha": "source",
                "policy_hash": "policy",
                "evidence_refs": ["ref"],
            },
            {
                "case": "unexpected_case",
                "status": "PASS",
                "source_sha": "source",
                "policy_hash": "policy",
                "evidence_refs": ["ref"],
            },
        ]
        verdict = evaluate_matrix_results(
            results,
            expected_cases=("loop+quality",),
            source_sha="source",
            policy_hash="policy",
        )
        self.assertEqual(verdict["status"], "BLOCKED")
        self.assertIn("DUPLICATE_CASE", verdict["reason_codes"])
        self.assertIn("SOURCE_BINDING_MISMATCH", verdict["reason_codes"])
        self.assertIn("POLICY_BINDING_MISMATCH", verdict["reason_codes"])
        self.assertIn("EVIDENCE_MISSING", verdict["reason_codes"])
        self.assertIn("CASE_NOT_PASS", verdict["reason_codes"])
        self.assertIn("MATRIX_CASE_UNEXPECTED", verdict["reason_codes"])



if __name__ == "__main__":
    unittest.main()
