#!/usr/bin/env python3
"""Create the deterministic writer-fence-removal target commit (no ref, no push) and print its SHA and tree.

The target is a single child of the abandoned r2 migration commit M. It restores exactly the two writer
kustomizations to their bytes at the sealed base, and changes nothing else - in particular the migration
kustomization keeps the r2 Job name, whose Job already completed, so Argo CD does not re-run a migration.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

MAIN_SHA = "c1d5e8cf197c7dbcb0d5f224011b82b73412e17a"  # M: deploy(devpath-migration): ...-r2 sealed 0328f124...
SEALED_BASE_SHA = "69e7bd15570f5ba0f271c83b5bd46955cb249c8e"  # parent of M
WRITER_PATHS = (
    "apps/devpath-platform-svc/base/kustomization.yaml",
    "apps/devpath-sandbox-svc/base/kustomization.yaml",
)
MIGRATION_PATH = "apps/devpath-migration/base/kustomization.yaml"
BOT_NAME = "devpath-gitops-release[bot]"
BOT_EMAIL = "244265210+devpath-gitops-release[bot]@users.noreply.github.com"
FIXED_DATE = "1789963200 +0000"  # 2026-09-21T04:00:00Z - fixed so the SHA is reproducible

MESSAGE = "\n".join(
    [
        "release: remove the abandoned ms-20260920-community-flat-pages-r2 writer fence from main",
        "",
        "The r2 migration commit c1d5e8cf197c7dbcb0d5f224011b82b73412e17a fenced platform-svc and",
        "sandbox-svc (replicas 0). Its migration Job completed, but promotion can never add the",
        "additive-services commit that lifts the fence: the immutable-image evidence of",
        "community-svc and notification-svc expired on 2026-09-21 and cannot be reproduced at the",
        "same source SHA. A new release cannot start either, because the migration gate refuses a",
        "sealed base that already contains a replica override.",
        "",
        "This restores exactly the two writer kustomizations to their bytes at the sealed base",
        "69e7bd15570f5ba0f271c83b5bd46955cb249c8e. The migration kustomization keeps the r2 Job",
        "name: that Job already completed, so nothing is re-run. r2 is abandoned; its sealed branch",
        "stays as evidence.",
        "",
        "Published by the one-shot publisher, not merged: protected main only moves through the",
        "release App.",
        "",
        "Spec: documents docs/superpowers/specs/2026-09-20-gitops-main-promotion-via-publisher-design.md (appendix 11)",
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
    repo = sys.argv[1]
    expected = sys.argv[2] if len(sys.argv) > 2 else ""
    if git(repo, "rev-parse", "origin/main") != MAIN_SHA:
        raise SystemExit("origin/main moved away from MAIN_SHA - stop and re-plan")
    if git(repo, "rev-parse", f"{MAIN_SHA}^") != SEALED_BASE_SHA:
        raise SystemExit("MAIN_SHA is not the sole child of SEALED_BASE_SHA")
    changed = git(repo, "diff", "--name-only", SEALED_BASE_SHA, MAIN_SHA).splitlines()
    if changed != sorted([MIGRATION_PATH, *WRITER_PATHS]):
        raise SystemExit(f"M changed unexpected paths: {changed}")

    with tempfile.TemporaryDirectory(prefix="unfence-index-") as scratch:
        index_env = {**os.environ, "GIT_INDEX_FILE": os.path.join(scratch, "index")}
        git(repo, "read-tree", MAIN_SHA, env=index_env)
        for path in WRITER_PATHS:
            mode, kind, blob = git(repo, "ls-tree", SEALED_BASE_SHA, "--", path).split()[:3]
            if (mode, kind) != ("100644", "blob"):
                raise SystemExit(f"{path} is not a regular blob at the sealed base")
            if b"replicas" in subprocess.run(
                ["git", "-C", repo, "cat-file", "-p", blob], capture_output=True, check=True
            ).stdout:
                raise SystemExit(f"{path} already carries a replica override at the sealed base")
            git(repo, "update-index", "--cacheinfo", f"100644,{blob},{path}", env=index_env)
        tree = git(repo, "write-tree", env=index_env)

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

    if git(repo, "diff", "--name-status", MAIN_SHA, target).splitlines() != [f"M\t{p}" for p in WRITER_PATHS]:
        raise SystemExit("target does not change exactly the two writer kustomizations")
    for path in WRITER_PATHS:
        if git(repo, "rev-parse", f"{target}:{path}") != git(repo, "rev-parse", f"{SEALED_BASE_SHA}:{path}"):
            raise SystemExit(f"{path} is not byte-identical to the sealed base")
    if git(repo, "rev-parse", f"{target}:{MIGRATION_PATH}") != git(repo, "rev-parse", f"{MAIN_SHA}:{MIGRATION_PATH}"):
        raise SystemExit("the migration kustomization must stay at M")
    git(repo, "diff", "--check", MAIN_SHA, target)
    if expected and target != expected:
        raise SystemExit(f"target SHA {target} != pinned {expected} - stop")
    print(f"TARGET_SHA={target}")
    print(f"TARGET_TREE={tree}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
