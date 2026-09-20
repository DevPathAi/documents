#!/usr/bin/env python3
"""Operator transaction for the one-shot S2a main publisher.

Opens the helper branch on the protected environment, bot-dispatches the
publisher, restores the exact main-only branch policy no matter what happened,
and only after the restore is verified approves the pending deployment.
It never touches ``prevent_self_review``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

REPO = "DevPathAi/devpath-gitops"
ENVIRONMENT = "mission-spine-production-off"
REVIEWER = "VelkaressiaBlutkrone"
BOT = "github-actions[bot]"
MAIN_SHA = "4f3ed64b2a148394eb0b8b3f5311e327f0edd759"
TARGET_SHA = "69e7bd15570f5ba0f271c83b5bd46955cb249c8e"
TARGET_TREE = "7799cc07f3083a002d0e2064db5437e2cde46f84"
HELPER_BRANCH = "chore/s2a-mobile-free-contract-publish-20260920"
TARGET_BRANCH = "fix/s2a-mobile-free-contract-main-20260920"
STAGED_BRANCH = "chore/s2a-main-publish-dispatcher-staged-20260920"
DISPATCH_BRANCH = "automation/dispatch-s2a-main-publish"
WORKFLOW_FILE = "mission-spine-auth-smoke.yml"
RULESETS = {
    21194269: "mission-spine-main-integrity",
    21194270: "mission-spine-main-governance",
}
BUSY_STATUSES = ("in_progress", "queued", "waiting", "requested", "pending")
SITES = ("https://app.leva.ai.kr", "https://leva.ai.kr")
ENV_PATH = f"repos/{REPO}/environments/{ENVIRONMENT}"
POLICIES_PATH = f"{ENV_PATH}/deployment-branch-policies"
HELPER_RUNS_PATH = (
    f"repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/runs"
    f"?branch={HELPER_BRANCH}&event=workflow_dispatch&per_page=20"
)


class PublishError(RuntimeError):
    """The transaction stopped; main-only policy was restored and verified."""


class RestoreError(PublishError):
    """The main-only policy could NOT be verified. Nothing was approved."""


@dataclass
class Ops:
    api: Callable[[str, str, dict[str, Any] | None], Any]
    run: Callable[[list[str]], str]
    sleep: Callable[[float], None]
    clock: Callable[[], float]
    http_status: Callable[[str], int]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PublishError(message)


def _branch_sha(ops: Ops, branch: str) -> str:
    return ops.api("GET", f"repos/{REPO}/branches/{branch}", None)["commit"]["sha"]


def _policies(ops: Ops) -> list[tuple[int, str, str]]:
    payload = ops.api("GET", f"{POLICIES_PATH}?per_page=100", None)
    rows = [(row["id"], row["name"], row["type"]) for row in payload["branch_policies"]]
    _require(payload["total_count"] == len(rows), "branch policy listing is truncated")
    return sorted(rows)


def snapshot_environment(ops: Ops) -> dict[str, Any]:
    """Return the sealed shape of the environment, or refuse to continue."""
    environment = ops.api("GET", ENV_PATH, None)
    _require(environment["name"] == ENVIRONMENT, "environment identity mismatch")
    _require(environment["can_admins_bypass"] is False, "administrators may bypass")
    _require(
        environment["deployment_branch_policy"]
        == {"protected_branches": False, "custom_branch_policies": True},
        "environment does not use an exact custom branch policy",
    )
    reviewer_rules = [
        rule for rule in environment["protection_rules"] if rule["type"] == "required_reviewers"
    ]
    _require(len(reviewer_rules) == 1, "exactly one required-reviewers rule is required")
    rule = reviewer_rules[0]
    _require(rule["prevent_self_review"] is True, "prevent_self_review is not true")
    reviewers = [(entry["type"], entry["reviewer"]["login"]) for entry in rule["reviewers"]]
    _require(reviewers == [("User", REVIEWER)], "configured reviewer is not exact")
    policies = _policies(ops)
    _require(
        [(name, kind) for _, name, kind in policies] == [("main", "branch")],
        "environment branch policy is not exactly main",
    )
    return {"environment_id": environment["id"], "policies": policies}


def preflight(ops: Ops, repo_dir: str, staged_sha: str) -> dict[str, Any]:
    _require(ops.api("GET", "user", None)["login"] == REVIEWER, "gh is not the reviewer")
    _require(_branch_sha(ops, "main") == MAIN_SHA, "main moved away from MAIN_SHA")
    _require(_branch_sha(ops, TARGET_BRANCH) == TARGET_SHA, "target branch moved")
    _require(_branch_sha(ops, STAGED_BRANCH) == staged_sha, "staged dispatcher moved")
    helper = ops.api("GET", f"repos/{REPO}/branches/{HELPER_BRANCH}", None)["commit"]
    _require(
        [parent["sha"] for parent in helper["parents"]] == [MAIN_SHA],
        "helper is not exactly one commit on MAIN_SHA",
    )
    _require(
        ops.api("GET", f"repos/{REPO}/git/matching-refs/heads/{DISPATCH_BRANCH}", None) == [],
        "dispatcher branch already exists",
    )
    for status in BUSY_STATUSES:
        busy = ops.api("GET", f"repos/{REPO}/actions/runs?status={status}&per_page=1", None)
        _require(busy["total_count"] == 0, f"repository has {status} workflow runs")
    known_runs = {run["id"] for run in ops.api("GET", HELPER_RUNS_PATH, None)["workflow_runs"]}
    ops.run(["git", "-C", repo_dir, "fetch", "--no-tags", "origin", STAGED_BRANCH])
    ops.run(["git", "-C", repo_dir, "cat-file", "-e", f"{staged_sha}^{{commit}}"])
    return {
        "snapshot": snapshot_environment(ops),
        "helper_sha": helper["sha"],
        "known_runs": known_runs,
    }


def _waiting_run(ops: Ops, helper_sha: str, known_runs: set[int]) -> int | None:
    runs = [
        run
        for run in ops.api("GET", HELPER_RUNS_PATH, None)["workflow_runs"]
        if run["id"] not in known_runs
    ]
    _require(len(runs) <= 1, "more than one publisher run appeared")
    if not runs:
        return None
    run = runs[0]
    _require(run["head_sha"] == helper_sha, "publisher run is not on the helper commit")
    _require(run["actor"]["login"] == BOT, "publisher run was not bot-dispatched")
    _require(run["run_attempt"] == 1, "publisher run is not attempt one")
    _require(run["status"] != "completed", "publisher run finished without waiting")
    return run["id"] if run["status"] == "waiting" else None


def restore(ops: Ops, snapshot: dict[str, Any]) -> None:
    """Delete only the helper policy, then prove the sealed shape is back."""
    for policy_id, name, _ in _policies(ops):
        if name == HELPER_BRANCH:
            ops.api("DELETE", f"{POLICIES_PATH}/{policy_id}", None)
    if snapshot_environment(ops) != snapshot:
        raise PublishError("environment differs from the snapshot")


def open_dispatch_restore(
    ops: Ops,
    repo_dir: str,
    staged_sha: str,
    state: dict[str, Any],
    *,
    wait_seconds: float = 300.0,
    poll_seconds: float = 5.0,
) -> int:
    failure: BaseException | None = None
    run_id: int | None = None
    try:
        ops.api("POST", POLICIES_PATH, {"name": HELPER_BRANCH, "type": "branch"})
        ops.run(
            ["git", "-C", repo_dir, "push", "origin", f"{staged_sha}:refs/heads/{DISPATCH_BRANCH}"]
        )
        deadline = ops.clock() + wait_seconds
        while run_id is None:
            run_id = _waiting_run(ops, state["helper_sha"], state["known_runs"])
            if run_id is None:
                _require(ops.clock() < deadline, "publisher run never reached waiting")
                ops.sleep(poll_seconds)
    except BaseException as exc:  # noqa: BLE001 - the policy must be restored regardless
        failure = exc
    try:
        restore(ops, state["snapshot"])
    except Exception as exc:
        raise RestoreError(
            "main-only policy NOT verified - restore it by hand before anything else"
        ) from (failure or exc)
    if failure is not None:
        raise failure
    assert run_id is not None
    return run_id


def approve(ops: Ops, run_id: int, environment_id: int, comment: str) -> list[int]:
    path = f"repos/{REPO}/actions/runs/{run_id}/pending_deployments"
    pending = ops.api("GET", path, None)
    _require(len(pending) == 1, "exactly one pending deployment is required")
    _require(pending[0]["environment"]["id"] == environment_id, "pending environment mismatch")
    _require(pending[0]["environment"]["name"] == ENVIRONMENT, "pending environment mismatch")
    _require(pending[0]["current_user_can_approve"] is True, "current user cannot approve")
    approved = ops.api(
        "POST",
        path,
        {"environment_ids": [environment_id], "state": "approved", "comment": comment},
    )
    _require(len(approved) == 1, "approval response is not exact")
    return [item["id"] for item in approved]


def post_verify(ops: Ops, snapshot: dict[str, Any], *, ci_wait_seconds: float = 900.0) -> None:
    _require(_branch_sha(ops, "main") == TARGET_SHA, "main is not TARGET_SHA")
    commit = ops.api("GET", f"repos/{REPO}/git/commits/{TARGET_SHA}", None)
    _require(commit["tree"]["sha"] == TARGET_TREE, "published tree is not TARGET_TREE")
    rulesets = {
        row["id"]: (row["name"], row["enforcement"])
        for row in ops.api("GET", f"repos/{REPO}/rulesets", None)
    }
    _require(
        rulesets == {key: (name, "active") for key, name in RULESETS.items()},
        "rulesets changed",
    )
    protection = ops.api("GET", f"repos/{REPO}/branches/main/protection", None)
    _require(protection["enforce_admins"]["enabled"] is True, "enforce_admins is off")
    _require(snapshot_environment(ops) == snapshot, "environment differs from the snapshot")
    deadline = ops.clock() + ci_wait_seconds
    ci_path = f"repos/{REPO}/actions/workflows/ci.yml/runs?head_sha={TARGET_SHA}&event=push"
    while True:
        runs = ops.api("GET", ci_path, None)["workflow_runs"]
        if runs and runs[0]["status"] == "completed":
            _require(runs[0]["conclusion"] == "success", "main CI failed on TARGET_SHA")
            break
        _require(ops.clock() < deadline, "main CI did not finish in time")
        ops.sleep(15.0)
    for site in SITES:
        _require(ops.http_status(site) == 200, f"{site} is not 200")


def publish(ops: Ops, repo_dir: str, staged_sha: str, comment: str) -> dict[str, Any]:
    state = preflight(ops, repo_dir, staged_sha)
    run_id = open_dispatch_restore(ops, repo_dir, staged_sha, state)
    deployment_ids = approve(ops, run_id, state["snapshot"]["environment_id"], comment)
    ops.run(["gh", "run", "watch", str(run_id), "-R", REPO, "--interval", "15", "--exit-status"])
    post_verify(ops, state["snapshot"])
    return {"run_id": run_id, "deployment_ids": deployment_ids, "main": TARGET_SHA}


def _gh_api(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    command = ["gh", "api", "-H", "X-GitHub-Api-Version: 2026-03-10", "-X", method, path]
    if payload is not None:
        command += ["--input", "-"]
    done = subprocess.run(
        command,
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    if done.returncode != 0:
        raise PublishError(f"GitHub API {method} {path} failed: {done.stderr.strip()[:300]}")
    return json.loads(done.stdout) if done.stdout.strip() else None


def _run(command: list[str]) -> str:
    done = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
    if done.returncode != 0:
        raise PublishError(f"{' '.join(command[:4])} failed: {done.stderr.strip()[:300]}")
    return done.stdout


def _http_status(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=20) as response:  # noqa: S310 - fixed https URLs
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", required=True, help="absolute path of a devpath-gitops clone")
    parser.add_argument("--staged-sha", required=True, help="head of the staged dispatcher branch")
    parser.add_argument("--comment", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--post-verify-only", action="store_true")
    args = parser.parse_args()
    ops = Ops(api=_gh_api, run=_run, sleep=time.sleep, clock=time.monotonic, http_status=_http_status)
    if args.preflight_only:
        state = preflight(ops, args.repo_dir, args.staged_sha)
        print(json.dumps({"preflight": "ok", "helper_sha": state["helper_sha"]}))
        return 0
    if args.post_verify_only:
        post_verify(ops, snapshot_environment(ops))
        print(json.dumps({"post_verify": "ok", "main": TARGET_SHA}))
        return 0
    print(json.dumps(publish(ops, args.repo_dir, args.staged_sha, args.comment), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
