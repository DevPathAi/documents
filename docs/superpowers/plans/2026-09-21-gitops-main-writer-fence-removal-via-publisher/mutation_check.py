#!/usr/bin/env python3
"""Mutation check for the publisher's target-test step: each mutant must die at the assertion meant to catch it.

Mutants share the real subject/author/parent, so every earlier assertion passes and the traced last command
identifies the assertion that refused it. Commits are loose objects only (no refs, nothing pushed).
Usage: mutation_check.py <gitops repo> <workflow.yml> <scratch checkout dir>
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import yaml

repo, workflow, checkout = sys.argv[1:4]
BASH = os.environ["DRYRUN_BASH"]
M = "c1d5e8cf197c7dbcb0d5f224011b82b73412e17a"
BASE = "69e7bd15570f5ba0f271c83b5bd46955cb249c8e"
PLATFORM = "apps/devpath-platform-svc/base/kustomization.yaml"
SANDBOX = "apps/devpath-sandbox-svc/base/kustomization.yaml"
MIGRATION = "apps/devpath-migration/base/kustomization.yaml"
BOT = "devpath-gitops-release[bot]"
MAIL = "244265210+devpath-gitops-release[bot]@users.noreply.github.com"

document = yaml.safe_load(open(workflow, encoding="utf-8"))
job = document["jobs"]["publish"]
step = next(s for s in job["steps"] if s.get("name") == "Test the exact fence-removal target")
script = step["run"][: step["run"].index("python -m pip install")] + 'echo "STEP-ASSERTIONS-PASSED"\n'
subject = "release: remove the abandoned ms-20260920-community-flat-pages-r2 writer fence from main"


def git(*args: str, stdin: bytes | None = None, env: dict | None = None, cwd: str | None = None) -> str:
    done = subprocess.run(["git", "-C", cwd or repo, *args], input=stdin, capture_output=True, env=env)
    if done.returncode != 0:
        raise SystemExit(f"git {args[:3]} failed: {done.stderr.decode(errors='replace')}")
    return done.stdout.decode().strip()


def blob_of(commit: str, path: str) -> str:
    return git("rev-parse", f"{commit}:{path}")


def commit_with(changes: dict[str, str]) -> tuple[str, str]:
    with tempfile.TemporaryDirectory(prefix="mutant-index-") as scratch:
        env = {**os.environ, "GIT_INDEX_FILE": os.path.join(scratch, "index")}
        git("read-tree", M, env=env)
        for path, blob in changes.items():
            git("update-index", "--cacheinfo", f"100644,{blob},{path}", env=env)
        tree = git("write-tree", env=env)
    env = {**os.environ, "GIT_AUTHOR_NAME": BOT, "GIT_AUTHOR_EMAIL": MAIL, "GIT_AUTHOR_DATE": "1789963200 +0000",
           "GIT_COMMITTER_NAME": BOT, "GIT_COMMITTER_EMAIL": MAIL, "GIT_COMMITTER_DATE": "1789963200 +0000"}
    return git("commit-tree", tree, "-p", M, "-m", subject, env=env), tree


def run(label: str, commit: str, tree: str, expected_fragment: str | None) -> bool:
    git("checkout", "--quiet", "--detach", commit, cwd=checkout)
    env = {**os.environ, **{k: str(v) for k, v in job["env"].items()}, "TARGET_SHA": commit, "TARGET_TREE": tree}
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False, encoding="utf-8", newline="\n") as handle:
        handle.write(script)
        path = handle.name
    done = subprocess.run([BASH, "-ex", path.replace(chr(92), "/")], cwd=checkout, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    os.unlink(path)
    trace = [line for line in (done.stderr or "").splitlines() if line.startswith("+")]
    last = trace[-1] if trace else ""
    if expected_fragment is None:
        ok = done.returncode == 0 and "STEP-ASSERTIONS-PASSED" in (done.stdout or "")
    else:
        ok = done.returncode != 0 and expected_fragment in last
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: rc={done.returncode} died at: {last[:150]}")
    return ok


fenced_one = git("hash-object", "-w", "--stdin",
                 stdin=subprocess.run(["git", "-C", repo, "cat-file", "-p", blob_of(BASE, SANDBOX)],
                                      capture_output=True, check=True).stdout
                 + b"replicas:\n- name: devpath-sandbox-svc\n  count: 1\n")

results = []
real, real_tree = commit_with({PLATFORM: blob_of(BASE, PLATFORM), SANDBOX: blob_of(BASE, SANDBOX)})
results.append(run("real shape (must pass)", real, real_tree, None))
a, a_tree = commit_with({PLATFORM: blob_of(BASE, PLATFORM)})
results.append(run("mutant A: only platform restored", a, a_tree, "-eq 2"))
b, b_tree = commit_with({PLATFORM: blob_of(BASE, PLATFORM), SANDBOX: fenced_one})
results.append(run("mutant B: sandbox keeps a replica override (count 1)", b, b_tree, "test"))
c, c_tree = commit_with({PLATFORM: blob_of(BASE, PLATFORM), SANDBOX: blob_of(BASE, SANDBOX),
                         MIGRATION: blob_of(BASE, MIGRATION)})
results.append(run("mutant C: migration kustomization also reverted", c, c_tree, "-eq 2"))
print("real-shape commit equals the pinned target:", real == job["env"]["TARGET_SHA"], "(different message, so False is expected)")
raise SystemExit(0 if all(results) else 1)
