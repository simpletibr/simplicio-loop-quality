import unittest

from simplicio_loop_quality.evo_benchmark import (
    REQUIRED_METRICS,
    evaluate_benchmark_run,
    validate_dataset,
)


def task(index):
    return {
        "task_id": f"task-{index}",
        "repository": f"repo-{index % 3}",
        "class": f"class-{index % 3}",
        "base_sha": "a" * 40,
        "spec_ref": f"spec/{index}",
        "test_ref": f"test/{index}",
    }


def run():
    metrics = {name: 1 for name in REQUIRED_METRICS}
    metrics["retries"] = 0
    return {
        "scenario": "S3_FULL_STACK",
        "repetitions": 10,
        "raw_samples": [{"total_seconds": 1}],
        "source_sha": "a" * 40,
        "receipt_refs": ["receipt"],
        "metrics": metrics,
    }


class EvoBenchmarkTest(unittest.TestCase):
    def test_dataset_requires_long_horizon_corpus(self):
        self.assertEqual(validate_dataset([task(index) for index in range(12)])["status"], "PASS")

    def test_complete_run_passes(self):
        self.assertEqual(evaluate_benchmark_run(run())["status"], "PASS")

    def test_missing_metric_reason_blocks(self):
        value = run()
        value["metrics"].pop("tokens")
        result = evaluate_benchmark_run(value)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("TOKENS_UNAVAILABLE_REASON_MISSING", result["reason_codes"])

    def test_invalid_dataset(self):
        result = validate_dataset([])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("TASK_COUNT_BELOW_12", result["reason_codes"])
        self.assertIn("REPOSITORY_COUNT_BELOW_3", result["reason_codes"])
        self.assertIn("TASK_CLASS_COUNT_BELOW_3", result["reason_codes"])

        bad_tasks = [{"task_id": ""} for _ in range(12)]
        result2 = validate_dataset(bad_tasks)
        self.assertIn("TASK_TASK_ID_MISSING", result2["reason_codes"])

    def test_benchmark_run_edge_cases(self):
        bad_run = {
            "scenario": "INVALID_SCENARIO",
            "repetitions": 5,
            "raw_samples": [],
            "source_sha": "",
            "receipt_refs": [],
            "metrics": "not-a-map",
        }
        res = evaluate_benchmark_run(bad_run)
        self.assertEqual(res["status"], "BLOCKED")
        self.assertIn("SCENARIO_INVALID", res["reason_codes"])
        self.assertIn("REPETITIONS_BELOW_10", res["reason_codes"])
        self.assertIn("RAW_SAMPLES_MISSING", res["reason_codes"])
        self.assertIn("SOURCE_SHA_MISSING", res["reason_codes"])
        self.assertIn("RECEIPTS_MISSING", res["reason_codes"])
        self.assertIn("METRICS_MISSING", res["reason_codes"])

        r2 = run()
        r2["metrics"]["tokens"] = -5
        res2 = evaluate_benchmark_run(r2)
        self.assertIn("TOKENS_INVALID", res2["reason_codes"])



if __name__ == "__main__":
    unittest.main()
