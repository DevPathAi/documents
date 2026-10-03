#!/usr/bin/env python3
"""Create the deterministic AI-fallback-probe target commit (no ref, no push) and print its SHA and tree.

Usage: make_ai_fallback_probe_target.py <devpath-gitops clone> <source commit> [expected target sha]

The target is the single child of the completed ms-20261002-ai-provider-fallback-gpu7b mission-on commit on
protected main (the shape of the 2026-09-21 publisher 5961922b and the 2026-09-24 publisher 5427fe1e: a `release:`
commit on top of a landed release becomes the next sealed base). It takes exactly the pinned paths from <source
commit> - the five develop blobs reviewed in gitops PRs #165/#166/#167 - and nothing else. The release-managed
kustomizations (web, ai-svc, migration) are deliberately absent: develop still carries the r3 digests there, and
taking them would silently roll production back. Fixed identity and timestamp make the SHA reproducible.
Structure: make_gateway_edge_cors_target.py (2026-09-24).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

MAIN_SHA = "cea3610ab29567b5bf46a2ba2a56bc5a58cac594"  # release(web): promote ms-20261002-...-gpu7b mission-on (landed)
TARGET_ROWS = (
    ("M", "apps/devpath-ai-svc/base/deployment.yaml"),
    ("M", "apps/devpath-ollama-gpu/base/deployment.yaml"),
    ("M", "docs/runbook-k3s-bootstrap.md"),
    ("M", "scripts/release/cloudflare_pages.py"),
    ("M", "tests/release/test_cloudflare_api.py"),
)
BOT_NAME = "devpath-gitops-release[bot]"
BOT_EMAIL = "244265210+devpath-gitops-release[bot]@users.noreply.github.com"
FIXED_DATE = "1790996400 +0000"  # 2026-10-03T03:00:00Z - fixed so the SHA is reproducible

MESSAGE = "\n".join(
    [
        "release: enable the GPU Ollama Claude fallback and retry the Landing probes",
        "",
        "ms-20261002-ai-provider-fallback-gpu7b put devpath-ai-svc 107fd20a (#83 fallback core, #84",
        "per-feature Ollama endpoints) into production, but the env that turns the fallback on lives in",
        "the gitops Deployment and could not ride the release: the main PR policy refuses apps/ and",
        "scripts/release/, and promote only writes kustomization.yaml. Without that env the fallback stays",
        "off, so production behaves exactly as before the release.",
        "",
        "- devpath-ai-svc: retention, community-seed and review fall back to qwen2.5:7b on the GPU",
        "  Ollama (ollama-gpu.devpath.svc) when Claude fails. Embedding and mentor stay on the CPU",
        "  Ollama. Measured on the L4 node 2026-10-02: every feature answers inside its timeout.",
        "- ollama-gpu: strategy Recreate (one nvidia.com/gpu per node deadlocks RollingUpdate) and the",
        "  7b model pulled next to the 3b path-generation model (two models fit the 8Gi limit).",
        "- scripts/release/cloudflare_pages.py: the Landing probes retry through Pages propagation and",
        "  tell a 404 from a connection failure (2026-10-01: a marker probe 1.17s after the deploy).",
        "- docs/runbook-k3s-bootstrap.md: GPU spot reclaim recovery and the detection gap.",
        "",
        "The blobs are byte-identical to gitops develop e6730ed. Only the ai-svc and ollama-gpu pod",
        "templates change in production; no image digest or release-managed kustomization moves.",
        "",
        "Published by the one-shot publisher, not merged: protected main only moves through the",
        "release App.",
        "",
        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>",
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

    with tempfile.TemporaryDirectory(prefix="ai-fallback-probe-index-") as scratch:
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
