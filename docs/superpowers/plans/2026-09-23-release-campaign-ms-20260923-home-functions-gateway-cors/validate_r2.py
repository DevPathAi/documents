"""Validate/seal stage for the -r2 release id: push the gitops automation dispatcher (bot author, branched from main), let it
dispatch mission-spine-validate.yml, approve the two `mission-spine-staging` gates as they appear, wait for success, and
record the seal commit that lands on the candidate branch plus the sealed manifest.

Usage: validate_r2.py <coords-r2.json> <dispatch|approve|collect>
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

GITOPS_REPO = "DevPathAi/devpath-gitops"
GITOPS = "D:/workspace/dpa/devpath-gitops"
BOT_NAME = "devpath-gitops-release[bot]"
BOT_EMAIL = "244265210+devpath-gitops-release[bot]@users.noreply.github.com"
coords_path = pathlib.Path(sys.argv[1])
coords = json.loads(coords_path.read_text(encoding="utf-8"))
step = sys.argv[2]
OUT = pathlib.Path(coords["out_dir"])
RID = coords["release_id"]
BASE = coords["gitops_base_sha"]
BRANCH = f"automation/dispatch-{RID}"
CAND = f"release/candidate-{RID}"
TAG = RID.rsplit("-", 1)[1]
WT = pathlib.Path(f"D:/workspace/dpa/.worktrees/gitops-dispatch-{TAG}-20260924")
WF = ".github/workflows/mission-spine-release-gate-dispatch.yml"
ENV = {**os.environ, "MSYS_NO_PATHCONV": "1", "PYTHONUTF8": "1"}


def run(cmd, cwd=None, env=None, capture=True, check=True, inp=None):
    done = subprocess.run(cmd, cwd=cwd, env=env or ENV, text=True, capture_output=capture, encoding="utf-8", input=inp)
    if check and done.returncode != 0:
        raise SystemExit(f"command failed ({done.returncode}): {' '.join(map(str, cmd))[:160]}\n{(done.stderr or '')[-600:]}")
    return done


def git(*args, cwd=GITOPS):
    return run(["git", "-C", str(cwd), *args]).stdout.strip()


def gh_json(*args):
    out = run(["gh", *args]).stdout
    return json.loads(out) if out.strip() else None


def save():
    coords_path.write_text(json.dumps(coords, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if step == "dispatch":
    assert coords["evidence"].get("summary"), "collect the evidence first"
    for key, entry in coords["evidence"]["summary"].items():
        assert entry["conclusion"] == "success", key
    run(["py", str(OUT / "render_dispatchers_r2.py"), str(coords_path), "validate"])
    rendered = (OUT / f"dispatchers-{TAG}" / "gitops-validate.yml").read_bytes()
    assert RID.encode() in rendered and b"mission-spine-validate.yml" in rendered and b"\r" not in rendered
    git("fetch", "-q", "origin", "main")
    assert git("rev-parse", "origin/main") == BASE, "gitops main moved"
    assert git("ls-remote", "--heads", "origin", BRANCH) == "" and not WT.exists(), "dispatcher branch/worktree exists"
    assert git("branch", "--list", BRANCH) == ""
    run(["git", "-C", GITOPS, "-c", "core.autocrlf=false", "worktree", "add", "-b", BRANCH, str(WT), BASE])
    (WT / WF).write_bytes(rendered)
    run(["git", "-C", str(WT), "add", WF])
    run(["git", "-C", str(WT), "-c", "core.autocrlf=false", "-c", f"user.name={BOT_NAME}", "-c", f"user.email={BOT_EMAIL}",
         "commit", "-q", "-m", f"ci: dispatch {RID} validation as GitHub Actions automation"])
    commit = git("rev-parse", "HEAD", cwd=WT)
    assert git("show", "-s", "--format=%an|%cn", "HEAD", cwd=WT) == f"{BOT_NAME}|{BOT_NAME}"
    coords.setdefault("validate", {})["dispatched_after"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    run(["git", "-C", str(WT), "push", "-q", "-u", "origin", BRANCH])
    coords["validate"]["dispatcher_commit"] = commit
    save()
    print("pushed", BRANCH, commit)

elif step == "redispatch":
    # a fresh validate run (attempt 1) after a failed one: the dispatcher re-fires on an empty nonce commit
    assert WT.exists() and git("branch", "--show-current", cwd=WT) == BRANCH
    run(["git", "-C", str(WT), "pull", "-q", "--ff-only", "origin", BRANCH])
    reason = sys.argv[3] if len(sys.argv) > 3 else "re-dispatch"
    run(["git", "-C", str(WT), "-c", "core.autocrlf=false", "-c", f"user.name={BOT_NAME}", "-c", f"user.email={BOT_EMAIL}",
         "commit", "-q", "--allow-empty", "-m", f"ci: re-dispatch {RID} validation ({reason})"])
    commit = git("rev-parse", "HEAD", cwd=WT)
    coords["validate"].setdefault("failed_runs", []).append(coords["validate"].get("run_id"))
    coords["validate"]["dispatched_after"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    coords["validate"].pop("run_id", None)
    run(["git", "-C", str(WT), "push", "-q", "origin", BRANCH])
    coords["validate"]["dispatcher_commit"] = commit
    save()
    print("re-dispatched", BRANCH, commit)

elif step == "approve":
    since = coords["validate"]["dispatched_after"]
    approved = 0
    deadline = time.time() + 60 * 60
    run_id = None
    while time.time() < deadline:
        runs = [r for r in gh_json("api", f"repos/{GITOPS_REPO}/actions/workflows/mission-spine-validate.yml/runs?event=workflow_dispatch&per_page=10")["workflow_runs"]
                if r["created_at"] >= since and r["actor"]["login"] == "github-actions[bot]"]
        if not runs:
            time.sleep(20)
            continue
        assert len(runs) == 1, [(r["id"], r["created_at"]) for r in runs]
        r = runs[0]
        run_id = r["id"]
        coords["validate"]["run_id"] = str(run_id)
        save()
        if r["status"] == "waiting":
            pend = gh_json("api", f"repos/{GITOPS_REPO}/actions/runs/{run_id}/pending_deployments")
            assert len(pend) == 1 and pend[0]["environment"]["name"] == "mission-spine-staging", [p["environment"]["name"] for p in pend]
            phase = "candidate journeys" if approved == 0 else "seal and staging"
            run(["py", str(OUT / "approve_gate.py"), GITOPS_REPO, str(run_id), "mission-spine-staging",
                 f"{RID}: {phase} on staging (AI-approved; five evidence producers succeeded, candidate {coords['candidate']['commit'][:8]})"], capture=False)
            approved += 1
            assert approved <= 2
        elif r["status"] == "completed":
            assert r["conclusion"] == "success", r["conclusion"]
            print("validate run", run_id, "success; approvals", approved)
            break
        time.sleep(30)
    else:
        raise SystemExit("validate did not finish in time")

elif step == "collect":
    run_id = int(coords["validate"]["run_id"])
    r = gh_json("api", f"repos/{GITOPS_REPO}/actions/runs/{run_id}")
    assert r["status"] == "completed" and r["conclusion"] == "success" and r["run_attempt"] == 1
    git("fetch", "-q", "origin", f"{CAND}:refs/remotes/origin/{CAND}")
    head = git("rev-parse", f"origin/{CAND}")
    assert git("rev-parse", f"origin/{CAND}^") == coords["candidate"]["commit"], "seal commit is not on top of the candidate commit"
    author = git("show", "-s", "--format=%an|%s", f"origin/{CAND}")
    assert author.startswith("devpath-release-bot|release(manifest): seal"), author
    files = git("show", "--name-status", "--format=", f"origin/{CAND}").splitlines()
    print("seal commit", head, "|", author, "|", files)
    release_path = f"release-manifests/releases/{RID}.json"
    manifest = run(["git", "-C", GITOPS, "show", f"origin/{CAND}:{release_path}"], env=ENV).stdout
    (OUT / f"sealed-release-manifest-{TAG}.json").write_text(manifest, encoding="utf-8", newline="\n")
    arts = gh_json("api", f"repos/{GITOPS_REPO}/actions/runs/{run_id}/artifacts?per_page=100")["artifacts"]
    coords["validate"].update({"sealed_sha": head, "sealed_manifest_sha256": hashlib.sha256(manifest.encode("utf-8")).hexdigest(),
                               "artifacts": [{"id": a["id"], "name": a["name"], "expires_at": a["expires_at"]} for a in arts]})
    save()
    print(json.dumps({k: coords["validate"][k] for k in ("run_id", "sealed_sha", "sealed_manifest_sha256")}, indent=1))
    print("artifacts:", [a["name"][:70] for a in arts])
else:
    raise SystemExit("unknown step")
