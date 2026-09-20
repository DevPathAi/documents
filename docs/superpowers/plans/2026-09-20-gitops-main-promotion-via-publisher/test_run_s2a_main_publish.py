import unittest
from typing import Any

import run_s2a_main_publish as runner
from run_s2a_main_publish import Ops, PublishError, RestoreError

HELPER_SHA = "a" * 40
STAGED_SHA = "b" * 40
ENV_ID = 9001
MAIN_POLICY_ID = 57524487
HELPER_POLICY_ID = 60000001
RUN_ID = 777


class FakeGitHub:
    """A scripted GitHub that records every call in order."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.main = runner.MAIN_SHA
        self.policies = [{"id": MAIN_POLICY_ID, "name": "main", "type": "branch"}]
        self.prevent_self_review = True
        self.runs: list[dict[str, Any]] = []
        self.busy = 0
        self.now = 0.0
        self.dispatch_appears = True
        self.push_fails = False
        self.delete_is_ignored = False
        self.can_approve = True
        self.ci_conclusion = "success"

    # -- Ops ---------------------------------------------------------------
    def ops(self) -> Ops:
        return Ops(
            api=self.api, run=self.run, sleep=self.sleep, clock=lambda: self.now,
            http_status=lambda url: 200,
        )

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def run(self, command: list[str]) -> str:
        self.calls.append("RUN " + " ".join(command[:5]))
        if command[3:4] == ["push"]:
            if self.push_fails:
                raise PublishError("push failed")
            allowed = any(policy["name"] == runner.HELPER_BRANCH for policy in self.policies)
            if self.dispatch_appears:
                self.runs.append(
                    {
                        "id": RUN_ID,
                        "head_sha": HELPER_SHA,
                        "actor": {"login": runner.BOT},
                        "run_attempt": 1,
                        "status": "waiting" if allowed else "completed",
                    }
                )
        if command[:3] == ["gh", "run", "watch"]:
            self.main = runner.TARGET_SHA
        return ""

    def api(self, method: str, path: str, payload: dict[str, Any] | None) -> Any:
        self.calls.append(f"{method} {path.split('?')[0]}")
        repo = f"repos/{runner.REPO}"
        if path == "user":
            return {"login": runner.REVIEWER}
        if path == f"{repo}/branches/main":
            return {"commit": {"sha": self.main}}
        if path == f"{repo}/branches/{runner.TARGET_BRANCH}":
            return {"commit": {"sha": runner.TARGET_SHA}}
        if path == f"{repo}/branches/{runner.STAGED_BRANCH}":
            return {"commit": {"sha": STAGED_SHA}}
        if path == f"{repo}/branches/{runner.HELPER_BRANCH}":
            return {"commit": {"sha": HELPER_SHA, "parents": [{"sha": runner.MAIN_SHA}]}}
        if path.startswith(f"{repo}/git/matching-refs/"):
            return []
        if path.startswith(f"{repo}/actions/runs?status="):
            return {"total_count": self.busy}
        if path == runner.HELPER_RUNS_PATH:
            return {"workflow_runs": list(self.runs)}
        if path == runner.ENV_PATH:
            return {
                "id": ENV_ID,
                "name": runner.ENVIRONMENT,
                "can_admins_bypass": False,
                "deployment_branch_policy": {
                    "protected_branches": False,
                    "custom_branch_policies": True,
                },
                "protection_rules": [
                    {
                        "type": "required_reviewers",
                        "prevent_self_review": self.prevent_self_review,
                        "reviewers": [{"type": "User", "reviewer": {"login": runner.REVIEWER}}],
                    },
                    {"type": "branch_policy"},
                ],
            }
        if path == f"{runner.POLICIES_PATH}?per_page=100":
            return {"total_count": len(self.policies), "branch_policies": list(self.policies)}
        if method == "POST" and path == runner.POLICIES_PATH:
            assert payload == {"name": runner.HELPER_BRANCH, "type": "branch"}
            self.policies.append({"id": HELPER_POLICY_ID, **payload})
            return {"id": HELPER_POLICY_ID, **payload}
        if method == "DELETE" and path.startswith(runner.POLICIES_PATH + "/"):
            policy_id = int(path.rsplit("/", 1)[1])
            assert policy_id != MAIN_POLICY_ID, "the main policy must never be deleted"
            if not self.delete_is_ignored:
                self.policies = [row for row in self.policies if row["id"] != policy_id]
            return None
        if path == f"{repo}/actions/runs/{RUN_ID}/pending_deployments":
            if method == "GET":
                return [
                    {
                        "environment": {"id": ENV_ID, "name": runner.ENVIRONMENT},
                        "current_user_can_approve": self.can_approve,
                    }
                ]
            assert payload == {
                "environment_ids": [ENV_ID],
                "state": "approved",
                "comment": "go",
            }
            return [{"id": 4242}]
        if path == f"{repo}/git/commits/{runner.TARGET_SHA}":
            return {"tree": {"sha": runner.TARGET_TREE}}
        if path == f"{repo}/rulesets":
            return [
                {"id": key, "name": name, "enforcement": "active"}
                for key, name in runner.RULESETS.items()
            ]
        if path == f"{repo}/branches/main/protection":
            return {"enforce_admins": {"enabled": True}}
        if path.startswith(f"{repo}/actions/workflows/ci.yml/runs"):
            return {"workflow_runs": [{"status": "completed", "conclusion": self.ci_conclusion}]}
        raise AssertionError(f"unscripted call: {method} {path}")

    # -- helpers -----------------------------------------------------------
    def index(self, needle: str) -> int:
        return next(i for i, call in enumerate(self.calls) if needle in call)

    def approved(self) -> bool:
        return any(call.startswith("POST") and "pending_deployments" in call for call in self.calls)

    def policy_opened(self) -> bool:
        return f"POST {runner.POLICIES_PATH}" in self.calls


class PublishTransactionTest(unittest.TestCase):
    def test_happy_path_restores_before_it_approves(self) -> None:
        github = FakeGitHub()
        result = runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertEqual(
            {"run_id": RUN_ID, "deployment_ids": [4242], "main": runner.TARGET_SHA}, result
        )
        opened = github.index(f"POST {runner.POLICIES_PATH}")
        pushed = github.index("RUN git -C D:/repo push origin")
        deleted = github.index(f"DELETE {runner.POLICIES_PATH}/{HELPER_POLICY_ID}")
        approved = github.index(f"POST repos/{runner.REPO}/actions/runs/{RUN_ID}/pending")
        self.assertLess(opened, pushed)
        self.assertLess(pushed, deleted)
        self.assertLess(deleted, approved)
        self.assertEqual([{"id": MAIN_POLICY_ID, "name": "main", "type": "branch"}], github.policies)

    def test_preflight_refuses_a_moved_main_before_any_write(self) -> None:
        github = FakeGitHub()
        github.main = "c" * 40
        with self.assertRaisesRegex(PublishError, "main moved"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertFalse(github.policy_opened())
        self.assertFalse(github.approved())

    def test_preflight_refuses_a_busy_repository_before_any_write(self) -> None:
        github = FakeGitHub()
        github.busy = 1
        with self.assertRaisesRegex(PublishError, "workflow runs"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertFalse(github.policy_opened())

    def test_preflight_refuses_a_relaxed_self_review_rule(self) -> None:
        github = FakeGitHub()
        github.prevent_self_review = False
        with self.assertRaisesRegex(PublishError, "prevent_self_review"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertFalse(github.policy_opened())

    def test_a_run_that_never_waits_is_restored_and_not_approved(self) -> None:
        github = FakeGitHub()
        github.dispatch_appears = False
        with self.assertRaisesRegex(PublishError, "never reached waiting"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertEqual(["main"], [row["name"] for row in github.policies])
        self.assertFalse(github.approved())
        self.assertGreaterEqual(github.now, 300.0)

    def test_a_failed_dispatch_push_is_restored_and_not_approved(self) -> None:
        github = FakeGitHub()
        github.push_fails = True
        with self.assertRaisesRegex(PublishError, "push failed"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertEqual(["main"], [row["name"] for row in github.policies])
        self.assertFalse(github.approved())

    def test_an_unverified_restore_blocks_the_approval(self) -> None:
        github = FakeGitHub()
        github.delete_is_ignored = True
        with self.assertRaises(RestoreError):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertFalse(github.approved())

    def test_an_unapprovable_deployment_is_not_approved(self) -> None:
        github = FakeGitHub()
        github.can_approve = False
        with self.assertRaisesRegex(PublishError, "cannot approve"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertEqual(["main"], [row["name"] for row in github.policies])
        self.assertFalse(github.approved())

    def test_a_red_main_ci_fails_the_post_verification(self) -> None:
        github = FakeGitHub()
        github.ci_conclusion = "failure"
        with self.assertRaisesRegex(PublishError, "main CI failed"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertTrue(github.approved())


if __name__ == "__main__":
    unittest.main()
