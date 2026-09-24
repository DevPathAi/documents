#!/usr/bin/env python3
"""Create the deterministic gateway-edge-CORS target commit (no ref, no push) and print its SHA and tree.

Usage: make_gateway_edge_cors_target.py <devpath-gitops clone> <source commit> [expected target sha]

The target is the single child of the completed r3 mission-on commit on protected main (the same shape as the
2026-09-21 publisher 5961922b: a `release:` commit on top of a landed release becomes the next sealed base). It
takes exactly the pinned paths from the locally developed <source commit> - the gateway Deployment env and its
test - and nothing else. Fixed identity and timestamp make the SHA reproducible from any clone with the blobs.
Structure: make_service_applied_revision_target.py (2026-09-24) / make_pipeline_defects_target.py (2026-09-21).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

MAIN_SHA = "eae5c42ef33b1a633a632766410e63d655b409fb"  # release(web): promote ...-r3 mission-on (landed)
TARGET_ROWS = (
    ("M", "apps/devpath-gateway/base/deployment.yaml"),
    ("A", "tests/release/test_gateway_edge_cors.py"),
)
BOT_NAME = "devpath-gitops-release[bot]"
BOT_EMAIL = "244265210+devpath-gitops-release[bot]@users.noreply.github.com"
FIXED_DATE = "1790224200 +0000"  # 2026-09-24T04:30:00Z - fixed so the SHA is reproducible

MESSAGE = "\n".join(
    [
        "release: restore the gateway edge CORS dedupe in the production default-filters",
        "",
        "devpath-gateway 391d984 (ms-20260923-home-functions-gateway-cors) dedupes the public CORS",
        "headers with `default-filters: [DedupeResponseHeader=Access-Control-Allow-Origin",
        "Access-Control-Allow-Credentials Vary, RETAIN_UNIQUE]` in its application.yml, and the image",
        "8cf6af8d has been serving production since the r3 additive-services phase (2026-09-24 01:21Z).",
        "The response still carried two Access-Control-Allow-Origin values and six Vary values on",
        "GET /mentor-access/invite-rounds with Origin https://leva.ai.kr, because the production",
        "Deployment pins SPRING_CLOUD_GATEWAY_SERVER_WEBFLUX_DEFAULT_FILTERS_0=PreserveHostHeader:",
        "Spring Boot binds a list from the highest-precedence source as a whole, so that single env",
        "entry replaced the image's default-filters list and silently dropped the dedupe. The",
        "staging stack already carries the dedupe as default-filters[1] next to the same env.",
        "",
        "The production env now carries both entries: PreserveHostHeader at index 0 (unchanged) and",
        "the image's exact DedupeResponseHeader definition at index 1. Only the gateway pod template",
        "changes; the image digest and every other application are untouched. A test pins the pair.",
        "",
        "Published by the one-shot publisher, not merged: protected main only moves through the",
        "release App.",
        "",
        "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>",
        "",
    ]
)


def git(repo: str, *args: str, stdin: bytes | None = None, env: dict[str, str] | None = None) -> str:
    done = subprocess.run(
        ["git", "-C", repo, *args], input=stdin, capture_output=True, env=env, check=False
    )
    if done.returncode != 0:
        raise SystemExit(f"git {' '.join(args[:3])} failed: {done.stderr.decode(errors='replace')}")
    return done.stdout.decode().strip()


def main() -> int:
    repo, source = sys.argv[1], sys.argv[2]
    expected = sys.argv[3] if len(sys.argv) > 3 else ""
    if git(repo, "rev-parse", "origin/main") != MAIN_SHA:
        raise SystemExit("origin/main moved away from MAIN_SHA - stop and re-plan")
    source = git(repo, "rev-parse", f"{source}^{{commit}}")
    rows = [f"{status}\t{path}" for status, path in TARGET_ROWS]
    if git(repo, "diff", "--name-status", MAIN_SHA, source).splitlines() != rows:
        raise SystemExit("the source commit does not change exactly the pinned paths")

    with tempfile.TemporaryDirectory(prefix="gateway-edge-cors-index-") as scratch:
        index_env = {**os.environ, "GIT_INDEX_FILE": os.path.join(scratch, "index")}
        git(repo, "read-tree", MAIN_SHA, env=index_env)
        for _, path in TARGET_ROWS:
            mode, kind, blob = git(repo, "ls-tree", source, "--", path).split()[:3]
            if (mode, kind) != ("100644", "blob"):
                raise SystemExit(f"{path} is not a regular blob at the source commit")
            content = subprocess.run(
                ["git", "-C", repo, "cat-file", "-p", blob], capture_output=True, check=True
            ).stdout
            if b"\r" in content:
                raise SystemExit(f"{path} carries a carriage return in its blob")
            git(repo, "update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=index_env)
        tree = git(repo, "write-tree", env=index_env)

    if tree != git(repo, "rev-parse", f"{source}^{{tree}}"):
        raise SystemExit("the target tree differs from the source tree - the source carries other changes")

    commit_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": BOT_NAME,
        "GIT_AUTHOR_EMAIL": BOT_EMAIL,
        "GIT_AUTHOR_DATE": FIXED_DATE,
        "GIT_COMMITTER_NAME": BOT_NAME,
        "GIT_COMMITTER_EMAIL": BOT_EMAIL,
        "GIT_COMMITTER_DATE": FIXED_DATE,
    }
    target = git(repo, "commit-tree", tree, "-p", MAIN_SHA, "-F", "-", stdin=MESSAGE.encode("utf-8"), env=commit_env)

    if git(repo, "diff", "--name-status", MAIN_SHA, target).splitlines() != rows:
        raise SystemExit("target does not change exactly the pinned paths")
    if git(repo, "rev-list", "--parents", "-n", "1", target) != f"{target} {MAIN_SHA}":
        raise SystemExit("target is not the single child of MAIN_SHA")
    git(repo, "diff", "--check", MAIN_SHA, target)
    if git(repo, "show", "-s", "--format=%s", target) != MESSAGE.splitlines()[0]:
        raise SystemExit("target subject drifted")
    if expected and target != expected:
        raise SystemExit(f"target SHA {target} != pinned {expected} - stop")
    print(f"TARGET_SHA={target}")
    print(f"TARGET_TREE={tree}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
