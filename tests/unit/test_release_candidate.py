import unittest

from simplicio_loop_quality.release_candidate import (
    REQUIRED_CHECKS,
    evaluate_release_candidate,
)


def candidate():
    return {
        "version": "0.1.0",
        "source_sha": "source",
        "artifacts": [{"name": "package.whl", "sha256": "digest", "size": 100}],
        "sbom": "sbom.json",
        "provenance": "provenance.json",
        "signature": "signature",
        "checks": {name: True for name in REQUIRED_CHECKS},
    }


class ReleaseCandidateTest(unittest.TestCase):
    def test_complete_candidate_passes(self):
        self.assertEqual(evaluate_release_candidate(candidate())["status"], "PASS")

    def test_tamper_check_fails_closed(self):
        value = candidate()
        value["checks"]["tamper_detection"] = False
        result = evaluate_release_candidate(value)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("TAMPER_DETECTION_FAILED", result["reason_codes"])

    def test_missing_clean_install_is_blocked(self):
        value = candidate()
        value["checks"]["clean_install"] = None
        result = evaluate_release_candidate(value)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("CLEAN_INSTALL_UNAVAILABLE", result["reason_codes"])

    def test_empty_version_or_source_sha(self):
        value = candidate()
        value["version"] = ""
        value["source_sha"] = "  "
        result = evaluate_release_candidate(value)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("VERSION_MISSING", result["reason_codes"])
        self.assertIn("SOURCE_SHA_MISSING", result["reason_codes"])

    def test_missing_or_invalid_artifacts(self):
        value = candidate()
        value["artifacts"] = None
        result = evaluate_release_candidate(value)
        self.assertIn("ARTIFACTS_MISSING", result["reason_codes"])

        value2 = candidate()
        value2["artifacts"] = [{"name": "", "sha256": "", "size": 0}]
        result2 = evaluate_release_candidate(value2)
        self.assertIn("ARTIFACT_DIGEST_MISSING", result2["reason_codes"])
        self.assertIn("ARTIFACT_SIZE_MISSING", result2["reason_codes"])

    def test_missing_sbom_provenance_signature(self):
        value = candidate()
        value["sbom"] = ""
        value["provenance"] = None
        value["signature"] = ""
        result = evaluate_release_candidate(value)
        self.assertIn("SBOM_MISSING", result["reason_codes"])
        self.assertIn("PROVENANCE_MISSING", result["reason_codes"])
        self.assertIn("SIGNATURE_MISSING", result["reason_codes"])

    def test_missing_checks_mapping(self):
        value = candidate()
        value["checks"] = "not-a-mapping"
        result = evaluate_release_candidate(value)
        self.assertIn("CHECKS_MISSING", result["reason_codes"])



if __name__ == "__main__":
    unittest.main()
