#!/usr/bin/env python3
"""Create the deterministic service-applied-revision target commit (no ref, no push) and print its SHA and tree.

Usage: make_service_applied_revision_target.py <devpath-gitops clone> <source commit> [expected target sha]

The target is the single child of the r3 additive-services commit on protected main. It takes exactly four paths
from the locally developed <source commit> (the services runtime waiter, the promotion chain grammar and their
tests) and nothing else. Fixed identity and timestamp make the SHA reproducible from any clone that has the blobs.
Structure: documents plans/2026-09-21-gitops-main-pipeline-defects-via-publisher/make_pipeline_defects_target.py.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

MAIN_SHA = "8b036dce5c410191c99b6334b288cccd104a0b34"  # release(services): promote ...-r3 additive-services
TARGET_ROWS = (
    ("M", "scripts/release/build_production_canary.py"),
    ("M", "scripts/release/promote_service_digests.py"),
    ("M", "scripts/release/verify_promotion_chain.py"),
    ("M", "scripts/release/verify_promotion_evidence.py"),
    ("M", "scripts/release/wait_release_rollouts.py"),
    ("M", "tests/release/test_kubernetes_release_runtime.py"),
    ("M", "tests/release/test_production_canary.py"),
    ("M", "tests/release/test_promotion_chain.py"),
    ("M", "tests/release/test_promotion_evidence.py"),
    ("M", "tests/release/test_service_promotion.py"),
)
BOT_NAME = "devpath-gitops-release[bot]"
BOT_EMAIL = "244265210+devpath-gitops-release[bot]@users.noreply.github.com"
FIXED_DATE = "1790215200 +0000"  # 2026-09-24T02:00:00Z - fixed so the SHA is reproducible

MESSAGE = "\n".join(
    [
        "fix(release): bind service applied revision to the app base",
        "",
        "Argo syncs an application on any rendered change beneath apps/<service>/base. The",
        "2026-09-23 publisher (5961922b) added a startupProbe to eight deployment.yaml files",
        "without touching kustomization.yaml, so Argo's last sync revision for the five",
        "services whose digests did not change afterwards is 5961922b while the services",
        "runtime verifier still derived the applied revision from kustomization.yaml alone",
        "(ec54b37 / 12fd3b9). The exact runtime gate of the additive-services phase can no",
        "longer pass on this base for any release (ms-20260923-home-functions-gateway-cors-r3",
        "promote runs 35941807967 and 35942936280).",
        "",
        "The applied revision now follows the base directory, which is what Argo actually",
        "syncs. The promotion chain grammar admits this fix once, directly after the services",
        "commit, with exactly these four paths.",
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
        raise SystemExit("the source commit does not change exactly the four pinned paths")

    with tempfile.TemporaryDirectory(prefix="service-applied-revision-index-") as scratch:
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
        raise SystemExit("target does not change exactly the four pinned paths")
    if git(repo, "rev-list", "--parents", "-n", "1", target) != f"{target} {MAIN_SHA}":
        raise SystemExit("target is not the single child of MAIN_SHA")
    git(repo, "diff", "--check", MAIN_SHA, target)
    if git(repo, "show", "-s", "--format=%s", target) != MESSAGE.splitlines()[0]:
        raise SystemExit("target subject drifted from the chain grammar subject")
    if expected and target != expected:
        raise SystemExit(f"target SHA {target} != pinned {expected} - stop")
    print(f"TARGET_SHA={target}")
    print(f"TARGET_TREE={tree}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
