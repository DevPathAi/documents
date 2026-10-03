"""Production stage for the sealed release (runs ONLY after the user confirms — every step past `preflight` changes production).

Steps (each idempotent-guarded, run in order):
  preflight          read-only: seal on the candidate branch, artifact expiry, nine-image pre-verification, promotion chain phase
  migration          shared: push automation/dispatch-<id> (main-based) -> approve `mission-spine-migration-release` -> success
  promote-off        gitops: switch the dispatcher to mission-spine-promote.yml -> approve `mission-spine-production-off` -> run result
  promote-on         gitops: empty nonce commit re-dispatches promote -> approve `mission-spine-staging` + `mission-spine-production-on`
  landing            gitops: switch the dispatcher to mission-spine-landing-last.yml -> approve `mission-spine-production-landing` -> live /api checks

Cluster-side helpers (release_ops.py, over SSH):
  preflight also checks the static sandbox-runner TLS secrets (>= 30 days left) and that no stale migration gate exists,
  and prints the live gate measurement. promote-off places the `sandbox-migration-gate` ConfigMap from a fresh measurement
  (+25% headroom) before dispatching and recalls it after success; promote-off/resume/on run a main watcher that forces an
  Argo refresh of every Application whenever gitops main moves (Argo polls every 3 minutes; the runtime verifier does not
  wait that long). Standalone: tls-check | gate-measure | gate-place | gate-recall | argo-refresh.

Usage: promote_r2.py <coords.json> <step>
"""
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

GITOPS_REPO = "DevPathAi/devpath-gitops"
GITOPS = "D:/workspace/dpa/devpath-gitops"
SHARED_REPO = "DevPathAi/devpath-shared"
SHARED = "D:/workspace/dpa/devpath-shared"
SHARED_MAIN = "9793b8f92f92cca1ef57e28d2db6fb7d911741a3"
BOT_NAME = "devpath-gitops-release[bot]"
BOT_EMAIL = "244265210+devpath-gitops-release[bot]@users.noreply.github.com"
coords_path = pathlib.Path(sys.argv[1])
coords = json.loads(coords_path.read_text(encoding="utf-8"))
step = sys.argv[2]
OUT = pathlib.Path(coords["out_dir"])
RID = coords["release_id"]
TAG = RID.rsplit("-", 1)[1]
BASE = coords["gitops_base_sha"]
BRANCH = f"automation/dispatch-{RID}"
CAND = f"release/candidate-{RID}"
GIT_WT = pathlib.Path(f"D:/workspace/dpa/.worktrees/gitops-dispatch-{TAG}-20260924")       # gitops automation branch (validate dispatcher)
CAND_WT = pathlib.Path(f"D:/workspace/dpa/.worktrees/gitops-candidate-20260923-{TAG}")       # candidate branch (spec + seal)
MAIN_WT = pathlib.Path("D:/workspace/dpa/.worktrees/gitops-main-20260924")                    # detached at gitops main (control root)
SHARED_WT = pathlib.Path(f"D:/workspace/dpa/.worktrees/shared-dispatch-{TAG}-20260924")
WF = ".github/workflows/mission-spine-release-gate-dispatch.yml"
ENV = {**os.environ, "MSYS_NO_PATHCONV": "1", "PYTHONUTF8": "1"}
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_ops as ops  # noqa: E402  (cluster-side helpers: TLS expiry, migration gate, Argo refresh)


def run(cmd, cwd=None, env=None, capture=True, check=True, inp=None):
    done = subprocess.run(cmd, cwd=cwd, env=env or ENV, text=True, capture_output=capture, encoding="utf-8", input=inp)
    if check and done.returncode != 0:
        raise SystemExit(f"command failed ({done.returncode}): {' '.join(map(str, cmd))[:160]}\n{(done.stdout or '')[-400:]}\n{(done.stderr or '')[-800:]}")
    return done


def git(*args, cwd=GITOPS):
    return run(["git", "-C", str(cwd), *args]).stdout.strip()


def gh_json(*args):
    out = run(["gh", *args]).stdout
    return json.loads(out) if out.strip() else None


def save():
    coords_path.write_text(json.dumps(coords, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def stamp():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def wait_bot_run(repo: str, workflow: str, since: str, approvals: list[str], label: str) -> dict:
    """Wait for the bot-dispatched run created after `since`; approve the listed environments in order as they pend."""
    approved: list[str] = []
    deadline = time.time() + 90 * 60
    while time.time() < deadline:
        runs = [r for r in gh_json("api", f"repos/{repo}/actions/workflows/{workflow}/runs?event=workflow_dispatch&per_page=10")["workflow_runs"]
                if r["created_at"] >= since and r["actor"]["login"] == "github-actions[bot]"]
        if not runs:
            time.sleep(20)
            continue
        assert len(runs) == 1, [(r["id"], r["created_at"]) for r in runs]
        r = runs[0]
        if r["status"] == "waiting":
            pend = gh_json("api", f"repos/{repo}/actions/runs/{r['id']}/pending_deployments")
            assert len(pend) == 1, [p["environment"]["name"] for p in pend]
            env_name = pend[0]["environment"]["name"]
            assert env_name in approvals and env_name not in approved, (env_name, approvals, approved)
            run(["py", str(OUT / "approve_gate.py"), repo, str(r["id"]), env_name,
                 f"{RID}: {label} — user-confirmed production change; gate approved by the campaign operator (AI) per the r3 policy."], capture=False)
            approved.append(env_name)
        elif r["status"] == "completed":
            print(f"{label}: run {r['id']} {r['conclusion']} (approved {approved})")
            return r
        time.sleep(30)
    raise SystemExit(f"{label}: run did not finish in time")


def gitops_dispatcher_commit(rendered: bytes | None, message: str) -> str:
    """Commit the rendered dispatcher (or an empty nonce when rendered is None) on the gitops automation branch as the bot."""
    assert GIT_WT.exists() and git("branch", "--show-current", cwd=GIT_WT) == BRANCH
    run(["git", "-C", str(GIT_WT), "pull", "-q", "--ff-only", "origin", BRANCH])
    if rendered is not None:
        (GIT_WT / WF).write_bytes(rendered)
        run(["git", "-C", str(GIT_WT), "add", WF])
        extra = []
    else:
        extra = ["--allow-empty"]
    run(["git", "-C", str(GIT_WT), "-c", "core.autocrlf=false", "-c", f"user.name={BOT_NAME}", "-c", f"user.email={BOT_EMAIL}",
         "commit", "-q", *extra, "-m", message])
    commit = git("rev-parse", "HEAD", cwd=GIT_WT)
    since = stamp()
    run(["git", "-C", str(GIT_WT), "push", "-q", "origin", BRANCH])
    coords.setdefault("production", {})[f"{message[:20]}"] = {"commit": commit, "at": since}
    save()
    print("pushed", commit[:8], "|", message)
    return since


def ensure_gate() -> None:
    """Place the migration maintenance gate from a fresh measurement unless it is already there (resume case)."""
    if ops.gate_exists():
        print(f"{ops.GATE_NAME} already present (resume) — leaving it in place")
        return
    measured = ops.measure_gate()
    bounds = ops.gate_bounds(measured)
    print(f"placing {ops.GATE_NAME}: measured {measured} -> bounds {bounds}")
    print(" ", ops.gate_place(bounds))
    coords.setdefault("production", {})["migration_gate"] = {"measured": measured, "bounds": bounds, "placed_at": stamp()}
    save()


def recall_gate() -> None:
    if not ops.gate_exists():
        print(f"{ops.GATE_NAME} not present — nothing to recall")
        return
    print(f"recalling {ops.GATE_NAME}:", ops.gate_recall())
    coords.setdefault("production", {}).setdefault("migration_gate", {})["recalled_at"] = stamp()
    save()


def watched(fn):
    """Run fn() while a watcher forces an Argo refresh on every new gitops main head."""
    watcher = ops.MainWatcher(GITOPS)
    watcher.start()
    try:
        return fn()
    finally:
        watcher.stop()
        print("argo refreshed for main heads:", [h[:8] for h in watcher.refreshed])


if step == "preflight":
    v = coords["validate"]
    assert v.get("sealed_sha") and v.get("sealed_manifest_sha256"), "validate/seal not collected"
    git("fetch", "-q", "origin", "main", f"{CAND}:refs/remotes/origin/{CAND}")
    main = git("rev-parse", "origin/main")
    print("gitops main =", main, "(base_sha)" if main == BASE else "(!! moved from base_sha)")
    assert git("rev-parse", f"origin/{CAND}") == v["sealed_sha"], "candidate branch head is not the sealed sha"
    # bring the candidate worktree to the sealed commit; make a detached main worktree as the control root
    run(["git", "-C", str(CAND_WT), "pull", "-q", "--ff-only", "origin", CAND])
    assert git("rev-parse", "HEAD", cwd=CAND_WT) == v["sealed_sha"]
    if not MAIN_WT.exists():
        run(["git", "-C", GITOPS, "-c", "core.autocrlf=false", "worktree", "add", "--detach", str(MAIN_WT), main])
    else:
        run(["git", "-C", str(MAIN_WT), "checkout", "-q", "--detach", main])
    # artifact expiry of everything the seal referenced
    manifest = json.loads((OUT / f"sealed-release-manifest-{TAG}.json").read_text(encoding="utf-8"))
    soonest = None
    def walk(o):
        global soonest
        if isinstance(o, dict):
            for k, val in o.items():
                if "expire" in k and isinstance(val, str) and val.endswith("Z"):
                    soonest = val if soonest is None or val < soonest else soonest
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(manifest)
    print("sealed manifest soonest artifact expiry:", soonest)
    # nine images (promote's first gate after the fence) — the real gitops selection code
    run(["py", str(pathlib.Path("D:/workspace/dpa/.release-artifacts/ms-20260920-community-flat-pages/r3/preverify_service_images.py")),
         str(MAIN_WT / "scripts" / "release"), str(OUT / f"candidate-spec-{TAG}.json")], capture=False)
    # promotion chain phase exactly as promote.yml's `resolve` job computes it
    out_file = OUT / f"chain-preflight-{TAG}.txt"
    out_file.write_text("", encoding="utf-8")  # the verifier requires an existing regular file
    done = run(["py", "scripts/release/verify_promotion_chain.py", "--root", str(MAIN_WT), "--release-root", str(CAND_WT),
                "--release-id", RID, "--current", main, "--github-output", str(out_file)], cwd=MAIN_WT, check=False)
    print("chain verifier rc =", done.returncode, "|", (done.stdout or "").strip()[-300:], (done.stderr or "").strip()[-300:])
    if out_file.exists():
        print(out_file.read_text(encoding="utf-8").strip())
    assert done.returncode == 0, "promotion chain verifier refused the current main as this release's base"
    # static TLS secrets the sandbox runner depends on (2026-09-23: a 30-day staging certificate expired mid-campaign)
    tls_ok, tls_failures, tls_rows = ops.tls_check(min_days=30)
    for row in tls_rows:
        print(f"  tls {row.label:55s} {'absent' if row.days_left is None else str(row.days_left) + 'd'}")
    assert tls_ok, f"sandbox-runner TLS secrets absent or expiring within 30 days: {tls_failures}"
    # migration maintenance gate: must not linger from an earlier release; show what promote-off will place
    assert not ops.gate_exists(), f"stale {ops.GATE_NAME} ConfigMap present — run `gate-recall` before promoting"
    measured = ops.measure_gate()
    print("  migration gate measurement:", measured, "-> bounds", ops.gate_bounds(measured))
    # what production will receive
    spec = json.loads((OUT / f"candidate-spec-{TAG}.json").read_text(encoding="utf-8"))
    print("PRODUCTION CHANGES:")
    print("  web mission-off :", spec["frontend"]["mission_off"]["image_digest"])
    print("  web mission-on  :", spec["frontend"]["mission_on"]["image_digest"], "(replaces", spec["gitops"]["base_web_digest"][:19], ")")
    print("  admin           :", spec["services"]["devpath-admin"]["image_digest"])
    print("  gateway         :", spec["services"]["devpath-gateway"]["image_digest"], "source", spec["services"]["devpath-gateway"]["source_sha"][:8])
    print("  shared migration:", spec["shared_migration"])
    print("  home landing    :", spec["home"]["source_sha"][:8], "dist", spec["home"]["dist_sha256"][:12], "prior deployment", spec["home"]["prior_production_deployment_id"])

elif step == "migration":
    run(["py", str(OUT / "render_dispatchers_r2.py"), str(coords_path), "migration"])
    rendered = (OUT / f"dispatchers-{TAG}" / "shared-migration.yml").read_bytes()
    assert coords["validate"]["sealed_sha"].encode() in rendered and SHARED_MAIN.encode() in rendered and b"\r" not in rendered
    git("fetch", "-q", "origin", "main", cwd=SHARED)
    assert git("rev-parse", "origin/main", cwd=SHARED) == SHARED_MAIN, "shared main moved"
    assert git("ls-remote", "--heads", "origin", BRANCH, cwd=SHARED) == "" and not SHARED_WT.exists()
    run(["git", "-C", SHARED, "worktree", "add", "-b", BRANCH, str(SHARED_WT), SHARED_MAIN])
    (SHARED_WT / WF).parent.mkdir(parents=True, exist_ok=True)
    (SHARED_WT / WF).write_bytes(rendered)
    run(["git", "-C", str(SHARED_WT), "add", WF])
    run(["git", "-C", str(SHARED_WT), "-c", "core.autocrlf=false", "commit", "-q", "-F", "-"],
        inp=f"ci: dispatch protected migration release ({RID})\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n")
    since = stamp()
    run(["git", "-C", str(SHARED_WT), "push", "-q", "-u", "origin", BRANCH])
    coords.setdefault("production", {})["migration_dispatched_after"] = since
    save()
    r = wait_bot_run(SHARED_REPO, "mission-spine-migration-release.yml", since, ["mission-spine-migration-release"], "shared migration-release")
    coords["production"]["migration_run"] = {"id": r["id"], "conclusion": r["conclusion"]}
    save()
    assert r["conclusion"] == "success", "migration-release failed — stop and inspect before promoting"

elif step == "promote-off":
    run(["py", str(OUT / "render_dispatchers_r2.py"), str(coords_path), "promote"])
    rendered = (OUT / f"dispatchers-{TAG}" / "gitops-promote.yml").read_bytes()
    ensure_gate()  # the migration Job's init container refuses without it (2026-09-24: ~6 min of fence downtime)
    since = gitops_dispatcher_commit(rendered, f"ci: dispatch {RID} production promotion")
    r = watched(lambda: wait_bot_run(GITOPS_REPO, "mission-spine-promote.yml", since, ["mission-spine-production-off"], "promote (migration -> services -> mission-OFF)"))
    coords["production"]["promote_off_run"] = {"id": r["id"], "conclusion": r["conclusion"]}
    save()
    if r["conclusion"] == "success":
        recall_gate()
    assert r["conclusion"] == "success", "promote OFF run failed — inspect; the gate stays in place for `promote-resume`"

elif step == "promote-resume":
    # r3 precedent: promote resolves its own phase, so after fixing the cause an empty nonce commit resumes the OFF job
    reason = sys.argv[3] if len(sys.argv) > 3 else "after all nine services converged"
    ensure_gate()
    since = gitops_dispatcher_commit(None, f"ci: resume {RID} promotion {reason}")
    r = watched(lambda: wait_bot_run(GITOPS_REPO, "mission-spine-promote.yml", since, ["mission-spine-production-off"], "promote resume (services -> mission-OFF)"))
    coords["production"].setdefault("promote_off_runs", []).append({"id": r["id"], "conclusion": r["conclusion"]})
    save()
    if r["conclusion"] == "success":
        recall_gate()
    assert r["conclusion"] == "success", "resumed promote OFF run failed — inspect before resuming again"

elif step == "promote-on":
    since = gitops_dispatcher_commit(None, f"ci: promote {RID} mission ON and canary")
    r = watched(lambda: wait_bot_run(GITOPS_REPO, "mission-spine-promote.yml", since, ["mission-spine-staging", "mission-spine-production-on"], "promote (mission-ON + canary + staging rebaseline)"))
    coords["production"]["promote_on_run"] = {"id": r["id"], "conclusion": r["conclusion"]}
    save()
    assert r["conclusion"] == "success", "promote ON run failed — inspect before landing"

elif step == "promote-on-continue":
    # the ON run was already dispatched (nonce pushed); resume approving its gates in any order and wait
    since = coords["production"]["ci: promote ms-20260"]["at"]
    r = watched(lambda: wait_bot_run(GITOPS_REPO, "mission-spine-promote.yml", since, ["mission-spine-production-on", "mission-spine-staging"], "promote (mission-ON + canary + staging rebaseline)"))
    coords["production"]["promote_on_run"] = {"id": r["id"], "conclusion": r["conclusion"]}
    save()
    assert r["conclusion"] == "success", "promote ON run failed — inspect before landing"

elif step == "tls-check":
    tls_ok, tls_failures, tls_rows = ops.tls_check(min_days=30)
    for row in tls_rows:
        print(f"  {row.label:55s} {'absent' if row.days_left is None else str(row.days_left) + 'd'}")
    print("ok:", tls_ok, "failures:", tls_failures)
    assert tls_ok

elif step == "gate-measure":
    measured = ops.measure_gate()
    print("measured:", measured)
    print("bounds  :", ops.gate_bounds(measured))
    print("present :", ops.gate_exists())

elif step == "gate-place":
    ensure_gate()

elif step == "gate-recall":
    recall_gate()

elif step == "argo-refresh":
    print(ops.argo_refresh_all())

elif step == "landing":
    run(["py", str(OUT / "render_dispatchers_r2.py"), str(coords_path), "landing"])
    rendered = (OUT / f"dispatchers-{TAG}" / "gitops-landing.yml").read_bytes()
    since = gitops_dispatcher_commit(rendered, f"ci: dispatch {RID} landing-last gate")
    r = wait_bot_run(GITOPS_REPO, "mission-spine-landing-last.yml", since, ["mission-spine-production-landing"], "landing-last (home dist to production Pages)")
    coords["production"]["landing_run"] = {"id": r["id"], "conclusion": r["conclusion"]}
    save()
    for path in ("/api/invite-rounds", "/api/stats", "/updates", "/"):
        try:
            with urllib.request.urlopen(urllib.request.Request("https://leva.ai.kr" + path, headers={"User-Agent": "release-check"}), timeout=20) as resp:
                body = resp.read(200)
                print(f"  GET {path}: {resp.status} {resp.headers.get('content-type','')} {body[:60]!r}")
        except Exception as exc:  # noqa: BLE001
            print(f"  GET {path}: ERROR {exc}")
    assert r["conclusion"] == "success"
else:
    raise SystemExit("unknown step")
