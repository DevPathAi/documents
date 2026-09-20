#!/usr/bin/env python3
"""Create the deterministic S2a target commit (no ref, no push) and print its SHA."""

from __future__ import annotations

import os
import subprocess
import sys

MAIN_SHA = "4f3ed64b2a148394eb0b8b3f5311e327f0edd759"
TARGET_TREE = "7799cc07f3083a002d0e2064db5437e2cde46f84"
PR162_HEAD = "4f0ba697c7a9994e1ba263e04cc4bd7e6db8aefe"
EXPECTED_TARGET_SHA = "69e7bd15570f5ba0f271c83b5bd46955cb249c8e"
BOT_NAME = "devpath-gitops-release[bot]"
BOT_EMAIL = "244265210+devpath-gitops-release[bot]@users.noreply.github.com"
FIXED_DATE = "1789873200 +0000"  # 2026-09-20T03:00:00Z - fixed so the SHA is reproducible

MESSAGE = "\n".join(
    [
        "release: promote the mobile-free release contract and the pinned ET13 catalog to main",
        "",
        "Squash promotion of S2a (1) #160 and (2) #161 from develop:",
        "- drop the candidate-prebound signed Android build and the manual TalkBack lane",
        "  (quality evidence 6 -> 5 labels; schema_version stays 1, in-place)",
        "- rebind the ET13 contract to the 13-fixture frontend catalog at frontend main",
        "  31a7785d5f3c73563c8ddb61b69a7a0e07f65f16 and derive the fixture list, projection matrix,",
        "  counts and surfaces from eight byte-pinned producer files",
        "",
        "main and develop had already diverged in nine files, so this applies the develop diff",
        "(988661b..9204c33) as a patch on top of main instead of copying files.",
        "",
        "Tree 7799cc07f3083a002d0e2064db5437e2cde46f84 is byte-identical to PR #162 head",
        "4f0ba697c7a9994e1ba263e04cc4bd7e6db8aefe, whose CI passed the full release suite on main.",
        "Published by the one-shot publisher, not merged: main PRs may not change the control plane.",
        "",
        "Spec: documents docs/superpowers/specs/2026-09-20-gitops-main-promotion-via-publisher-design.md",
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
    if git(repo, "rev-parse", "origin/main") != MAIN_SHA:
        raise SystemExit("origin/main moved away from MAIN_SHA - stop and re-plan")
    if git(repo, "rev-parse", f"{PR162_HEAD}^{{tree}}") != TARGET_TREE:
        raise SystemExit("PR #162 head tree is not TARGET_TREE")
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": BOT_NAME,
        "GIT_AUTHOR_EMAIL": BOT_EMAIL,
        "GIT_AUTHOR_DATE": FIXED_DATE,
        "GIT_COMMITTER_NAME": BOT_NAME,
        "GIT_COMMITTER_EMAIL": BOT_EMAIL,
        "GIT_COMMITTER_DATE": FIXED_DATE,
    }
    target = git(
        repo, "commit-tree", TARGET_TREE, "-p", MAIN_SHA, "-F", "-",
        stdin=MESSAGE.encode("utf-8"), env=env,
    )
    if target != EXPECTED_TARGET_SHA:
        raise SystemExit(f"target SHA {target} != pinned {EXPECTED_TARGET_SHA} - stop")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
