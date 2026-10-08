import unittest

from simplicio_loop_quality.fast_conformance import (
    build_conformance_matrix,
    evaluate_conformance,
)


def result(case):
    engine, mode, lane, slots = case
    return {
        "engine": engine,
        "mode": mode,
        "lane": lane,
        "slots": slots,
        "status": "PASS",
        "source_sha": "source",
        "policy_hash": "policy",
        "evidence_refs": ["receipt"],
        "rollback_exercised": True,
    }


class FastConformanceTest(unittest.TestCase):
    def test_matrix_has_both_engines_and_modes(self):
        matrix = build_conformance_matrix()
        self.assertIn(("python", "full", "conformance", 1), matrix["cases"])
        self.assertIn(("rust", "loop-standalone", "conformance", 100), matrix["cases"])

    def test_complete_bound_results_pass(self):
        cases = tuple(build_conformance_matrix()["cases"])
        verdict = evaluate_conformance(
            [result(case) for case in cases],
            expected_cases=cases,
            source_sha="source",
            policy_hash="policy",
        )
        self.assertEqual(verdict["status"], "PASS")

    def test_rust_fallback_is_rejected(self):
        case = ("rust", "full", "conformance", 1)
        value = result(case)
        value["fallback_used"] = True
        verdict = evaluate_conformance(
            [value], expected_cases=(case,), source_sha="source", policy_hash="policy"
        )
        self.assertEqual(verdict["status"], "FAIL")
        self.assertIn("RUST_FALLBACK_USED", verdict["reason_codes"])

    def test_conformance_edge_cases(self):
        case = ("rust", "full", "conformance", 1)
        v1 = result(case)
        v1["python_loaded"] = True
        v1["shadow_duplicates"] = 2
        v1["rollback_exercised"] = False
        v1["status"] = "FAIL"
        v1["source_sha"] = "wrong-sha"
        v1["policy_hash"] = "wrong-policy"
        v1["evidence_refs"] = []

        v2 = result(case)  # Duplicate case
        verdict = evaluate_conformance(
            [v1, v2],
            expected_cases=(case, ("off", "full", "conformance", 1)),
            source_sha="source",
            policy_hash="policy",
        )
        self.assertEqual(verdict["status"], "BLOCKED")
        self.assertIn("DUPLICATE_CASE", verdict["reason_codes"])
        self.assertIn("SOURCE_BINDING_MISMATCH", verdict["reason_codes"])
        self.assertIn("POLICY_BINDING_MISMATCH", verdict["reason_codes"])
        self.assertIn("EVIDENCE_MISSING", verdict["reason_codes"])
        self.assertIn("RUST_LOADED_PYTHON", verdict["reason_codes"])
        self.assertIn("SHADOW_DUPLICATE_EFFECT", verdict["reason_codes"])
        self.assertIn("ROLLBACK_NOT_EXERCISED", verdict["reason_codes"])
        self.assertIn("CASE_NOT_PASS", verdict["reason_codes"])
        self.assertIn("CONFORMANCE_CASE_MISSING", verdict["reason_codes"])



if __name__ == "__main__":
    unittest.main()
