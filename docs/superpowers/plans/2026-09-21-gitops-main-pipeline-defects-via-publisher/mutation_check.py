#!/usr/bin/env python3
"""Mutation check for the publisher's target-test step: each mutant must die at the assertion meant to catch it.

Mutants share the real subject/author/parent, so every earlier assertion passes and the traced last command
identifies the assertion that refused it. Commits are loose objects only (no refs, nothing pushed).
Usage: mutation_check.py <gitops repo> <workflow.yml> <scratch checkout dir (a detached worktree)>
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import yaml

repo, workflow, checkout = sys.argv[1:4]
BASH = os.environ["DRYRUN_BASH"]  # an explicit Git Bash; a bare `bash` on Windows may resolve to WSL
BOT = "devpath-gitops-release[bot]"
MAIL = "244265210+devpath-gitops-release[bot]@users.noreply.github.com"
DATE = "1789995600 +0000"
SANDBOX = "apps/devpath-sandbox-svc/base/deployment.yaml"
WEB = "apps/devpath-web/base/deployment.yaml"
PLATFORM = "apps/devpath-platform-svc/base/deployment.yaml"

document = yaml.safe_load(open(workflow, encoding="utf-8"))
job = document["jobs"]["publish"]
MAIN = job["env"]["MAIN_SHA"]
TARGET = job["env"]["TARGET_SHA"]
step = next(s for s in job["steps"] if s.get("name") == "Test the exact pipeline-defects target")
script = step["run"][: step["run"].index("python -m pip install")] + 'echo "STEP-ASSERTIONS-PASSED"\n'


def git(*args: str, stdin: bytes | None = None, env: dict | None = None, cwd: str | None = None) -> str:
    done = subprocess.run(["git", "-C", cwd or repo, *args], input=stdin, capture_output=True, env=env)
    if done.returncode != 0:
        raise SystemExit(f"git {args[:3]} failed: {done.stderr.decode(errors='replace')}")
    return done.stdout.decode().strip()


SUBJECT = git("show", "-s", "--format=%s", TARGET)
TARGET_PATHS = git("diff", "--name-only", MAIN, TARGET).splitlines()
assert len(TARGET_PATHS) == 12, TARGET_PATHS


def blob_of(commit: str, path: str) -> str:
    return git("rev-parse", f"{commit}:{path}")


def content(commit: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", repo, "show", f"{commit}:{path}"], capture_output=True, check=True).stdout


def commit_with(changes: dict[str, str]) -> tuple[str, str]:
    with tempfile.TemporaryDirectory(prefix="mutant-index-") as scratch:
        env = {**os.environ, "GIT_INDEX_FILE": os.path.join(scratch, "index")}
        git("read-tree", MAIN, env=env)
        for path, blob in changes.items():
            git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
        tree = git("write-tree", env=env)
    env = {**os.environ, "GIT_AUTHOR_NAME": BOT, "GIT_AUTHOR_EMAIL": MAIL, "GIT_AUTHOR_DATE": DATE,
           "GIT_COMMITTER_NAME": BOT, "GIT_COMMITTER_EMAIL": MAIL, "GIT_COMMITTER_DATE": DATE}
    return git("commit-tree", tree, "-p", MAIN, "-m", SUBJECT, env=env), tree


def run(label: str, commit: str, overrides: dict[str, str], expected_fragment: str | None) -> bool:
    git("checkout", "--quiet", "--detach", commit, cwd=checkout)
    env = {**os.environ, **{k: str(v) for k, v in job["env"].items()}, **overrides}
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
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: rc={done.returncode} died at: {last[:160]}")
    return ok


real_shape = {path: blob_of(TARGET, path) for path in TARGET_PATHS}
weak_probe = git("hash-object", "-w", "--stdin",
                 stdin=content(TARGET, PLATFORM).replace(b"failureThreshold: 60", b"failureThreshold: 6"))
touched_web = git("hash-object", "-w", "--stdin", stdin=content(MAIN, WEB) + b"# thirteenth path\n")

# xtrace prints the multi-line `test "$target_listing" = "$expected_listing"` starting with its first row; the rows
# hold a real tab once bash has expanded $'M<backslash>t...'. `test -n` would be traced as `+ test -n`, so this is the comparison.
LISTING_COMPARISON = "+ test 'M" + chr(9) + "apps/devpath-ai-svc/base/deployment.yaml"

results = [run("the pinned target itself (must pass)", TARGET, {}, None)]

a, a_tree = commit_with({path: blob for path, blob in real_shape.items() if path != SANDBOX})
results.append(run("mutant A: sandbox-svc left without a startup budget (11 paths)", a,
                   {"TARGET_SHA": a, "TARGET_TREE": a_tree}, LISTING_COMPARISON))
b, b_tree = commit_with({**real_shape, WEB: touched_web})
results.append(run("mutant B: a thirteenth path rides along", b,
                   {"TARGET_SHA": b, "TARGET_TREE": b_tree}, LISTING_COMPARISON))
c, _ = commit_with({**real_shape, PLATFORM: weak_probe})
results.append(run("mutant C: same twelve paths, platform budget cut to 30s (tree pin must refuse)", c,
                   {"TARGET_SHA": c}, "= 85d71a7f6734d781df3ea0f287ae8569a1b801e4"))
git("checkout", "--quiet", "--detach", TARGET, cwd=checkout)
raise SystemExit(0 if all(results) else 1)
