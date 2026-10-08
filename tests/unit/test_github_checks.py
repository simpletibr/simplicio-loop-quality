import unittest

from simplicio_loop_quality.github_checks import project_check


class GitHubChecksTest(unittest.TestCase):
    def test_pass_projects_success_and_close_action(self):
        result = project_check({"status": "PASS", "findings": []})
        self.assertEqual(result.conclusion, "success")
        self.assertEqual(result.issue_action, "close")

    def test_blocked_projects_neutral_and_keeps_issue_open(self):
        result = project_check({"status": "BLOCKED", "reason_codes": ["EVIDENCE_MISSING"]})
        self.assertEqual(result.conclusion, "neutral")
        self.assertEqual(result.issue_action, "keep-open")
        self.assertEqual(result.annotations[0]["level"], "warning")

    def test_to_dict_and_projector(self):
        from simplicio_loop_quality.github_checks import GitHubChecksProjector
        proj = GitHubChecksProjector()
        result = proj.project({"status": "PASS"})
        d = result.to_dict()
        self.assertEqual(d["schema"], "simplicio.quality-github-checks/v1")
        self.assertEqual(d["conclusion"], "success")



if __name__ == "__main__":
    unittest.main()
