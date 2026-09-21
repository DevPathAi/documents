#!/usr/bin/env python3
"""Create the deterministic pipeline-defects target commit (no ref, no push) and print its SHA and tree.

Usage: make_pipeline_defects_target.py <devpath-gitops clone> <source commit> [expected target sha]

The target is a single child of the completed r3 mission-on commit. It takes exactly twelve paths from the
locally developed <source commit> (startup budget for the eight Spring Deployments, the migration fence pull
secret, the landing API smoke and their tests) and nothing else. Fixed identity and timestamp make the SHA
reproducible from any clone that has the source blobs.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

MAIN_SHA = "30c0e9f717efaad9bd46d47721a61495f4093e96"  # release(web): promote ...-r3 mission-on
TARGET_ROWS = (
    ("M", "apps/devpath-ai-svc/base/deployment.yaml"),
    ("M", "apps/devpath-community-svc/base/deployment.yaml"),
    ("M", "apps/devpath-gateway/base/deployment.yaml"),
    ("M", "apps/devpath-lcs-svc/base/deployment.yaml"),
    ("M", "apps/devpath-learning-svc/base/deployment.yaml"),
    ("M", "apps/devpath-migration/base/writer-fence-rbac.yaml"),
    ("M", "apps/devpath-notification-svc/base/deployment.yaml"),
    ("M", "apps/devpath-platform-svc/base/deployment.yaml"),
    ("M", "apps/devpath-sandbox-svc/base/deployment.yaml"),
    ("M", "scripts/release/cloudflare_pages.py"),
    ("M", "tests/release/test_cloudflare_api.py"),
    ("A", "tests/release/test_production_startup_budget.py"),
)
BOT_NAME = "devpath-gitops-release[bot]"
BOT_EMAIL = "244265210+devpath-gitops-release[bot]@users.noreply.github.com"
FIXED_DATE = "1789995600 +0000"  # 2026-09-21T13:00:00Z - fixed so the SHA is reproducible

MESSAGE = "\n".join(
    [
        "release: add the production startup budget, the fence pull secret, and the landing API smoke to main",
        "",
        "Three control-plane defects that the 2026-09-21 campaign exposed:",
        "",
        "- The eight Spring Deployments had no startupProbe, so liveness (20s delay + 3 x 10s) killed",
        "  every JVM that needed more than about 50 seconds to start. When additive-services rolled",
        "  five rebuilt services at once on the single 4-CPU node, all of them were killed in a loop",
        "  (12m40s outage). They now get the startup budget the staging stack already uses:",
        "  /actuator/health/liveness every 5s, up to 300s. Readiness and liveness are unchanged.",
        "- The migration fence ServiceAccount pulled its private ghcr.io image only through a manual",
        "  cluster patch. The pull secret is now declared.",
        "- Landing verification probed / and the dist marker only, so a dist-only deploy that lost the",
        "  Pages Functions passed while /api/* returned 404 (2m30s). It now also requires",
        "  GET /api/invite-rounds to answer 200 with JSON.",
        "",
        "The pod templates of eight Deployments change. The operator pauses their rollouts before this",
        "commit is published and resumes them one at a time.",
        "",
        "Published by the one-shot publisher, not merged: protected main only moves through the",
        "release App.",
        "",
        "Spec: documents docs/superpowers/specs/2026-09-20-gitops-main-promotion-via-publisher-design.md (appendix 12)",
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
        raise SystemExit("the source commit does not change exactly the twelve pinned paths")

    with tempfile.TemporaryDirectory(prefix="pipeline-defects-index-") as scratch:
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
        raise SystemExit("target does not change exactly the twelve pinned paths")
    if git(repo, "rev-list", "--parents", "-n", "1", target) != f"{target} {MAIN_SHA}":
        raise SystemExit("target is not the single child of MAIN_SHA")
    git(repo, "diff", "--check", MAIN_SHA, target)
    if expected and target != expected:
        raise SystemExit(f"target SHA {target} != pinned {expected} - stop")
    print(f"TARGET_SHA={target}")
    print(f"TARGET_TREE={tree}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
