"""Candidate stage for the -r2 release id: derive the spec in a fresh gitops worktree on release/candidate-<id>, pass every
local gate (gitops validator, web base lineage, home journey harness mirror, promote's image pre-verification), commit it as
the gitops release bot exactly as the candidate workflow demands (one commit, one added file, parent = main), push, dispatch
mission-spine-candidate.yml on that branch, and record the candidate run/artifact.

Usage: candidate_r2.py <coords-r2.json> <prepare|push|dispatch>
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
HOME_WT = pathlib.Path("D:/workspace/dpa/.worktrees/home-candidate-20260923")  # detached at home master ffaf4b33
BOT_NAME = "devpath-gitops-release[bot]"
BOT_EMAIL = "244265210+devpath-gitops-release[bot]@users.noreply.github.com"
coords_path = pathlib.Path(sys.argv[1])
coords = json.loads(coords_path.read_text(encoding="utf-8"))
step = sys.argv[2]
OUT = pathlib.Path(coords["out_dir"])
RID = coords["release_id"]
BASE = coords["gitops_base_sha"]
BRANCH = f"release/candidate-{RID}"
TAG = RID.rsplit("-", 1)[1]
WT = pathlib.Path(f"D:/workspace/dpa/.worktrees/gitops-candidate-20260923-{TAG}")
SPEC_REL = f"release-manifests/candidates/{RID}.candidate-spec.json"
ENV = {**os.environ, "MSYS_NO_PATHCONV": "1", "PYTHONUTF8": "1"}


def run(cmd, cwd=None, env=None, check=True, capture=False):
    done = subprocess.run(cmd, cwd=cwd, env=env or ENV, text=True, capture_output=capture, encoding="utf-8" if capture else None)
    if check and done.returncode != 0:
        raise SystemExit(f"command failed ({done.returncode}): {' '.join(map(str, cmd))[:160]}\n{(done.stderr or '')[-800:] if capture else ''}")
    return done


def git(*args, cwd=GITOPS):
    return run(["git", "-C", str(cwd), *args], capture=True).stdout.strip()


def gh_json(*args):
    return json.loads(run(["gh", *args], capture=True).stdout or "null")


def save():
    coords_path.write_text(json.dumps(coords, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if step == "prepare":
    for key in ("frontend_sha", "web_off_digest", "web_on_digest", "admin_digest"):
        assert coords[key], key
    for key in ("run_id", "artifact_id", "dir"):
        assert coords["baseline"][key], f"baseline.{key}"
    assert (OUT / "candidate-provenance" / "summary.json").exists(), "run run_provenance_r2.py first"
    git("fetch", "-q", "origin", "main")
    assert git("rev-parse", "origin/main") == BASE, "gitops main moved; the base_sha coordinate is stale"
    assert git("ls-remote", "--heads", "origin", BRANCH) == "", "remote candidate branch already exists"
    if not WT.exists():
        assert git("branch", "--list", BRANCH) == "", "local branch exists without worktree"
        run(["git", "-C", GITOPS, "-c", "core.autocrlf=false", "worktree", "add", "-b", BRANCH, str(WT), BASE])
    assert git("rev-parse", "HEAD", cwd=WT) == BASE and git("branch", "--show-current", cwd=WT) == BRANCH
    spec_path = WT / SPEC_REL
    if spec_path.exists():
        spec_path.unlink()
    run(["py", str(OUT / "build_candidate_spec_r2.py"), str(coords_path), str(WT)])
    assert spec_path.exists()
    spec_sha = sha256_file(spec_path)
    assert b"\r" not in spec_path.read_bytes()
    print("spec sha256 =", spec_sha)
    # gate 1: the gitops validator at the exact base commit (the candidate workflow runs this same command)
    run(["py", "scripts/release/validate_release_manifest.py", "--root", str(WT), "--candidate-id", RID, "--expected-sha256", spec_sha], cwd=WT)
    print("gate 1 validator: ok")
    # gate 2: prior lineage vs the exact web base
    run(["py", "scripts/release/verify_candidate_web_base.py", "--root", str(WT), "--release-id", RID], cwd=WT)
    print("gate 2 web base: ok")
    # gate 3: the home release-journey harness mirror of the contract, at the pinned home source
    assert git("rev-parse", "HEAD", cwd=HOME_WT) == coords["home"]["source_sha"], "home worktree is not at home.source_sha"
    evidence_dir = OUT / "home-harness-check"
    evidence_dir.mkdir(exist_ok=True)
    harness_env = {**ENV, "MISSION_CANDIDATE_SPEC_PATH": str(spec_path), "MISSION_CANDIDATE_SPEC_SHA256": spec_sha,
                   "MISSION_RELEASE_EVIDENCE_DIR": str(evidence_dir), "MISSION_RELEASE_CONTROL_TOKEN": "local-gate-dummy-token"}
    js = ("import('./e2e/release/support/release-context.js').then(m=>{m.loadReleaseContext();console.log('home harness accepted the spec')})"
          ".catch(e=>{console.error('HARNESS FAIL:',e.message);process.exit(1)})")
    run(["node", "-e", js], cwd=HOME_WT, env=harness_env)
    print("gate 3 home harness: ok")
    # gate 4: promote's nine-image pre-verification (expiry + GHCR + current protected main per service)
    run(["py", str(pathlib.Path("D:/workspace/dpa/.release-artifacts/ms-20260920-community-flat-pages/r3/preverify_service_images.py")),
         str(WT / "scripts" / "release"), str(spec_path)])
    print("gate 4 service images: ok")
    (OUT / f"candidate-spec-{TAG}.json").write_bytes(spec_path.read_bytes())
    coords["candidate"]["spec_sha256"] = spec_sha
    coords["candidate"]["branch"] = BRANCH
    save()

elif step == "push":
    spec_path = WT / SPEC_REL
    spec_sha = sha256_file(spec_path)
    assert spec_sha == coords["candidate"]["spec_sha256"], "spec changed since prepare"
    assert git("rev-parse", "HEAD", cwd=WT) == BASE
    status = git("status", "--porcelain=v1", "--untracked-files=all", cwd=WT)
    assert status == f"?? {SPEC_REL}", status
    run(["git", "-C", str(WT), "add", SPEC_REL])
    run(["git", "-C", str(WT), "-c", "core.autocrlf=false", "-c", f"user.name={BOT_NAME}", "-c", f"user.email={BOT_EMAIL}",
         "commit", "-q", "-m", f"release: add {RID} candidate"])
    head = git("rev-parse", "HEAD", cwd=WT)
    assert git("rev-parse", "HEAD^", cwd=WT) == BASE
    assert git("show", "-s", "--format=%an|%ae|%cn|%ce", "HEAD", cwd=WT) == f"{BOT_NAME}|{BOT_EMAIL}|{BOT_NAME}|{BOT_EMAIL}"
    assert git("diff", "--name-status", f"{BASE}...HEAD", cwd=WT) == f"A\t{SPEC_REL}"
    blob = run(["git", "-C", str(WT), "show", f"HEAD:{SPEC_REL}"], capture=True).stdout
    assert "\r" not in blob and hashlib.sha256(blob.encode("utf-8")).hexdigest() == spec_sha, "committed blob differs (line endings?)"
    run(["git", "-C", str(WT), "push", "-q", "-u", "origin", BRANCH])
    coords["candidate"]["commit"] = head
    save()
    print("pushed", BRANCH, head)

elif step == "dispatch":
    head = coords["candidate"]["commit"]
    assert gh_json("api", f"repos/{GITOPS_REPO}/branches/{BRANCH}")["commit"]["sha"] == head
    before = {r["id"] for r in gh_json("api", f"repos/{GITOPS_REPO}/actions/workflows/mission-spine-candidate.yml/runs?branch={BRANCH.replace('/', '%2F')}&per_page=20")["workflow_runs"]}
    run(["gh", "workflow", "run", "mission-spine-candidate.yml", "-R", GITOPS_REPO, "--ref", BRANCH, "-f", f"release_id={RID}"])
    run_obj = None
    for _ in range(40):
        time.sleep(10)
        runs = [r for r in gh_json("api", f"repos/{GITOPS_REPO}/actions/workflows/mission-spine-candidate.yml/runs?branch={BRANCH.replace('/', '%2F')}&per_page=20")["workflow_runs"]
                if r["id"] not in before]
        if runs:
            assert len(runs) == 1, [r["id"] for r in runs]
            run_obj = runs[0]
            break
    assert run_obj, "candidate run did not appear"
    while run_obj["status"] != "completed":
        time.sleep(20)
        run_obj = gh_json("api", f"repos/{GITOPS_REPO}/actions/runs/{run_obj['id']}")
        print("  candidate run", run_obj["id"], run_obj["status"], run_obj["conclusion"])
    assert run_obj["conclusion"] == "success" and run_obj["run_attempt"] == 1 and run_obj["head_sha"] == head
    name = f"{RID}-candidate-spec-run-{run_obj['id']}-attempt-1"
    arts = [a for a in gh_json("api", f"repos/{GITOPS_REPO}/actions/runs/{run_obj['id']}/artifacts?per_page=100")["artifacts"] if a["name"] == name]
    assert len(arts) == 1, [a["name"] for a in arts]
    coords["candidate"].update({"run_id": str(run_obj["id"]), "artifact_id": str(arts[0]["id"]), "artifact_name": name,
                                "artifact_digest": arts[0]["digest"], "expires_at": arts[0]["expires_at"]})
    save()
    print(json.dumps(coords["candidate"], indent=1))
else:
    raise SystemExit("unknown step")
