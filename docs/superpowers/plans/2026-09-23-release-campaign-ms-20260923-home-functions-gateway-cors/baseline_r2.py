"""Dispatch the protected ET13 baseline approval for the -r2 release id via the automation branch, approve it (only after
verify_identical_target_r2.py passed), and pull the approved baseline artifact.

Usage: baseline_r2.py <coords-r2.json> <dispatch|approve|collect>
"""
import hashlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import zipfile

REPO = "DevPathAi/devpath-frontend"
FRONTEND = "D:/workspace/dpa/devpath-frontend"
APPROVED_SET = "2db5d5723b522fde49496d8a18ae28964c4eb2f6b749557de1c6ace391198476"
coords_path = pathlib.Path(sys.argv[1])
coords = json.loads(coords_path.read_text(encoding="utf-8"))
step = sys.argv[2]
OUT = pathlib.Path(coords["out_dir"])
RID = coords["release_id"]
SHA = coords["frontend_sha"]
BRANCH = f"automation/dispatch-{RID}"
TAG = RID.rsplit("-", 1)[1]
WT = pathlib.Path(f"D:/workspace/dpa/.worktrees/frontend-dispatch-{TAG}-20260924")
ENV = {**os.environ, "MSYS_NO_PATHCONV": "1", "PYTHONUTF8": "1"}


def gh_json(*args):
    done = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", timeout=300)
    if done.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)[:100]} failed: {done.stderr[:300]}")
    return json.loads(done.stdout) if done.stdout.strip() else None


def gh_bytes(*args) -> bytes:
    done = subprocess.run(["gh", *args], capture_output=True, timeout=600)
    if done.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)[:100]} failed: {done.stderr[:300]!r}")
    return done.stdout


def git(*args, cwd=FRONTEND):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True, env=ENV).stdout.strip()


def save():
    coords_path.write_text(json.dumps(coords, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if step == "dispatch":
    ok = OUT / "IDENTICAL_TARGET_OK"
    assert ok.exists() and ok.read_text().split()[0] == SHA, "run verify_identical_target_r2.py first"
    subprocess.run(["py", str(OUT / "render_dispatchers_r2.py"), str(coords_path), "baseline"], check=True)
    rendered = (OUT / f"dispatchers-{TAG}" / "frontend-baseline.yml").read_bytes()
    assert RID.encode() in rendered and coords["raw_review"]["run_id"].encode() in rendered
    assert b"\r" not in rendered
    git("fetch", "-q", "origin", "main")
    assert git("rev-parse", "origin/main") == SHA, "frontend main moved"
    assert git("branch", "--list", BRANCH) == "", "local branch exists"
    assert git("ls-remote", "--heads", "origin", BRANCH) == "", "remote branch exists"
    if WT.exists():
        raise SystemExit(f"{WT} exists")
    git("worktree", "add", "-b", BRANCH, str(WT), SHA)
    target = WT / ".github" / "workflows" / "mission-spine-release-gate-dispatch.yml"
    target.write_bytes(rendered)
    git("add", ".github/workflows/mission-spine-release-gate-dispatch.yml", cwd=WT)
    message = f"ci: dispatch the ET13 baseline approval for {RID}\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n"
    subprocess.run(["git", "-C", str(WT), "-c", "core.autocrlf=false", "commit", "-q", "-F", "-"],
                   input=message, text=True, check=True, env=ENV)
    commit = git("rev-parse", "HEAD", cwd=WT)
    coords["baseline"]["dispatched_after"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    git("push", "-q", "-u", "origin", BRANCH, cwd=WT)
    coords["baseline"]["dispatcher_branch"] = BRANCH
    coords["baseline"]["dispatcher_commit"] = commit
    save()
    print("pushed", BRANCH, commit)

elif step == "approve":
    runs = []
    for _ in range(40):
        runs = gh_json("api", f"repos/{REPO}/actions/workflows/et13-baseline-approval.yml/runs?event=workflow_dispatch&per_page=10")["workflow_runs"]
        runs = [r for r in runs if r["head_sha"] == SHA and r["actor"]["login"] == "github-actions[bot]"
                and r["created_at"] >= coords["baseline"]["dispatched_after"]]
        if runs:
            break
        time.sleep(15)
    assert len(runs) == 1, [(r["id"], r["status"], r["created_at"]) for r in runs]
    run = runs[0]
    print("approval run", run["id"], run["status"], run["created_at"], "|", run["display_title"])
    while True:
        run = gh_json("api", f"repos/{REPO}/actions/runs/{run['id']}")
        if run["status"] in ("waiting", "completed"):
            break
        time.sleep(15)
    assert run["status"] == "waiting", run["status"]
    ok = OUT / "IDENTICAL_TARGET_OK"
    assert ok.exists() and ok.read_text().split()[0] == SHA
    comment = (f"Identical-target re-binding for {RID}: rebuilt raw review run {coords['raw_review']['run_id']} "
               f"reproduces the r3-approved visual set {APPROVED_SET[:8]}... byte for byte (verified locally, 104/104 PNGs).")
    subprocess.run(["py", str(OUT / "approve_gate.py"), REPO, str(run["id"]), "et13-baseline-approval", comment], check=True)
    coords["baseline"]["run_id"] = str(run["id"])
    save()

elif step == "collect":
    run_id = int(coords["baseline"]["run_id"])
    while True:
        run = gh_json("api", f"repos/{REPO}/actions/runs/{run_id}")
        print("  status", run["status"], run["conclusion"])
        if run["status"] == "completed":
            break
        time.sleep(30)
    assert run["conclusion"] == "success" and run["run_attempt"] == 1, (run["conclusion"], run["run_attempt"])
    name = f"{RID}-frontend-visual-approved-baseline-run-{run_id}-attempt-1"
    arts = [a for a in gh_json("api", f"repos/{REPO}/actions/runs/{run_id}/artifacts?per_page=100")["artifacts"] if a["name"] == name]
    assert len(arts) == 1, [a["name"] for a in arts]
    art = arts[0]
    blob = gh_bytes("api", f"repos/{REPO}/actions/artifacts/{art['id']}/zip")
    archive = pathlib.Path(coords["baseline"]["archive"])
    archive.write_bytes(blob)
    bdir = pathlib.Path(coords["baseline"]["dir"])
    if bdir.exists():
        shutil.rmtree(bdir)
    bdir.mkdir()
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        zf.extractall(bdir)
    approval = json.loads((bdir / "baseline-approval.v1.json").read_text(encoding="utf-8"))
    assert approval["source_sha"] == SHA and approval["approval_run_id"] == run_id and approval["status"] == "approved"
    assert approval["candidate_set_sha256"] == APPROVED_SET, approval["candidate_set_sha256"]
    assert approval["raw_review_run_id"] == int(coords["raw_review"]["run_id"])
    assert approval["raw_review_artifact_id"] == int(coords["raw_review"]["artifact_id"])
    assert approval["approval_workflow_sha256"] == coords["baseline"]["workflow_sha256"]
    coords["baseline"].update({
        "artifact_id": str(art["id"]), "artifact_name": name, "archive_sha256": hashlib.sha256(blob).hexdigest(),
        "artifact_digest": art["digest"], "expires_at": art["expires_at"], "approved_by": approval["approved_by"],
    })
    save()
    print(json.dumps({k: coords["baseline"][k] for k in ("run_id", "artifact_id", "archive_sha256", "expires_at")}, indent=1))
else:
    raise SystemExit("unknown step")
