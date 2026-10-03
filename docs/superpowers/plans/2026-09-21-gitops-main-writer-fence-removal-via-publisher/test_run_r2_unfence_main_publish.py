import unittest
from typing import Any
from unittest import mock

import run_r2_unfence_main_publish as runner
from run_r2_unfence_main_publish import Ops, PublishError, RestoreError

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
        self.delete_is_interrupted = False
        self.can_approve = True
        self.approval_body: Any = [{"id": 4242}]
        self.ci_conclusion = "success"
        self.site_status = 200
        self.ruleset_enforcement = "active"
        self.probed: list[str] = []

    # -- Ops ---------------------------------------------------------------
    def ops(self) -> Ops:
        return Ops(
            api=self.api, run=self.run, sleep=self.sleep, clock=lambda: self.now,
            http_status=self.http_status,
        )

    def http_status(self, url: str) -> int:
        self.probed.append(url)
        return self.site_status

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
            if self.delete_is_interrupted:
                raise KeyboardInterrupt
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
            return self.approval_body
        if path == f"{repo}/git/commits/{runner.TARGET_SHA}":
            return {"tree": {"sha": runner.TARGET_TREE}}
        if path == f"{repo}/rulesets":
            return [
                {"id": key, "name": name, "enforcement": self.ruleset_enforcement}
                for key, name in runner.RULESETS.items()
            ]
        if path == f"{repo}/branches/main/protection":
            return {"enforce_admins": {"enabled": True}}
        if path.startswith(f"{repo}/actions/workflows/ci.yml/runs"):
            # main CI only exists for the target once main has actually moved to it.
            if self.main != runner.TARGET_SHA:
                return {"workflow_runs": []}
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
        result = runner.publish(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA, "go")
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
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA, "go")
        self.assertFalse(github.policy_opened())
        self.assertFalse(github.approved())

    def test_preflight_walks_every_read_edge_of_the_post_verification(self) -> None:
        # 2026-09-20: --preflight-only never reached _http_status, and the live run died there.
        github = FakeGitHub()
        runner.preflight(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA)
        for edge in (
            f"GET repos/{runner.REPO}/rulesets",
            f"GET repos/{runner.REPO}/branches/main/protection",
            f"GET repos/{runner.REPO}/git/commits/{runner.TARGET_SHA}",
            f"GET repos/{runner.REPO}/actions/workflows/ci.yml/runs",
        ):
            self.assertIn(edge, github.calls)
        self.assertEqual(list(runner.SITES), github.probed)
        self.assertFalse(github.policy_opened())

    def test_preflight_refuses_a_site_that_is_down_before_any_write(self) -> None:
        github = FakeGitHub()
        github.site_status = 503
        with self.assertRaisesRegex(PublishError, "is not 200"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA, "go")
        self.assertFalse(github.policy_opened())
        self.assertFalse(github.approved())

    def test_preflight_refuses_a_weakened_ruleset_before_any_write(self) -> None:
        github = FakeGitHub()
        github.ruleset_enforcement = "evaluate"
        with self.assertRaisesRegex(PublishError, "rulesets changed"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA, "go")
        self.assertFalse(github.policy_opened())

    def test_preflight_refuses_a_target_that_was_already_published(self) -> None:
        github = FakeGitHub()
        github.main = runner.TARGET_SHA
        with self.assertRaisesRegex(PublishError, "main moved"):
            runner.preflight(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA)

    def test_preflight_refuses_a_helper_that_is_not_the_reviewed_commit(self) -> None:
        # The staged dispatcher was pinned but the helper was discovered: whatever sat on the
        # helper branch at run time - not what was reviewed - would have been dispatched.
        github = FakeGitHub()
        with self.assertRaisesRegex(PublishError, "helper branch moved"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "e" * 40, "go")
        self.assertFalse(github.policy_opened())
        self.assertFalse(github.approved())

    def test_preflight_refuses_a_busy_repository_before_any_write(self) -> None:
        github = FakeGitHub()
        github.busy = 1
        with self.assertRaisesRegex(PublishError, "workflow runs"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA, "go")
        self.assertFalse(github.policy_opened())

    def test_preflight_refuses_a_relaxed_self_review_rule(self) -> None:
        github = FakeGitHub()
        github.prevent_self_review = False
        with self.assertRaisesRegex(PublishError, "prevent_self_review"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA, "go")
        self.assertFalse(github.policy_opened())

    def test_a_run_that_never_waits_is_restored_and_not_approved(self) -> None:
        github = FakeGitHub()
        github.dispatch_appears = False
        with self.assertRaisesRegex(PublishError, "never reached waiting"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA, "go")
        self.assertEqual(["main"], [row["name"] for row in github.policies])
        self.assertFalse(github.approved())
        self.assertGreaterEqual(github.now, 300.0)

    def test_a_failed_dispatch_push_is_restored_and_not_approved(self) -> None:
        github = FakeGitHub()
        github.push_fails = True
        with self.assertRaisesRegex(PublishError, "push failed"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA, "go")
        self.assertEqual(["main"], [row["name"] for row in github.policies])
        self.assertFalse(github.approved())

    def test_an_unverified_restore_blocks_the_approval(self) -> None:
        github = FakeGitHub()
        github.delete_is_ignored = True
        with self.assertRaises(RestoreError):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA, "go")
        self.assertFalse(github.approved())

    def test_an_unapprovable_deployment_is_not_approved(self) -> None:
        github = FakeGitHub()
        github.can_approve = False
        with self.assertRaisesRegex(PublishError, "cannot approve"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA, "go")
        self.assertEqual(["main"], [row["name"] for row in github.policies])
        self.assertFalse(github.approved())

    def test_a_red_main_ci_fails_the_post_verification(self) -> None:
        github = FakeGitHub()
        github.ci_conclusion = "failure"
        with self.assertRaisesRegex(PublishError, "main CI failed"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA, "go")
        self.assertTrue(github.approved())

    def test_an_interrupt_during_the_restore_is_a_restore_error(self) -> None:
        github = FakeGitHub()
        github.delete_is_interrupted = True
        with self.assertRaises(RestoreError):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA, "go")
        self.assertFalse(github.approved())

    def test_an_empty_approval_response_is_a_publish_error(self) -> None:
        github = FakeGitHub()
        github.approval_body = None
        with self.assertRaisesRegex(PublishError, "approval response is not exact"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, HELPER_SHA, "go")
        self.assertEqual(["main"], [row["name"] for row in github.policies])

    def test_post_verify_without_a_snapshot_still_requires_the_sealed_shape(self) -> None:
        github = FakeGitHub()
        github.main = runner.TARGET_SHA
        runner.post_verify(github.ops(), None)
        github.prevent_self_review = False
        with self.assertRaisesRegex(PublishError, "prevent_self_review"):
            runner.post_verify(github.ops(), None)

    def test_site_probe_identifies_itself(self) -> None:
        # Cloudflare answers 403 to the default "Python-urllib" agent on leva.ai.kr (live, 2026-09-20).
        seen: list[Any] = []

        class _Response:
            status = 200

            def __enter__(self) -> "_Response":
                return self

            def __exit__(self, *exc: Any) -> None:
                return None

        def fake_urlopen(request: Any, timeout: float) -> _Response:
            seen.append(request)
            return _Response()

        with mock.patch.object(runner.urllib.request, "urlopen", fake_urlopen):
            self.assertEqual(200, runner._http_status("https://leva.ai.kr"))
        self.assertEqual("https://leva.ai.kr", seen[0].full_url)
        agent = seen[0].get_header("User-agent")
        self.assertTrue(agent and "urllib" not in agent.lower(), agent)


if __name__ == "__main__":
    unittest.main()
