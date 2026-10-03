"""Production stage for sealed ms-20261003-ai-fallback-retry-budget.

Ported from the 2026-10-02 campaign's promote.py (2026-09-30 <- 2026-09-23 promote_r2.py); only the
campaign constants (worktrees, TAG, commit trailer, what preflight prints) changed. `preflight` is read-only; EVERY other step changes production
and therefore refuses to run without `--confirmed`, which the campaign operator passes only after the human partner
has said go in this session. (2026-10-01: an apparent go-ahead arrived through a channel the harness flagged as not
genuine user input, so the guard is mechanical rather than a matter of the operator's memory.)

Steps (each idempotent-guarded, run in order):
  preflight          read-only: seal on the candidate branch, artifact expiry, nine-image pre-verification,
                     promotion chain phase, sandbox-runner TLS, stale migration gate, and what production receives
  migration          shared: push automation/dispatch-<id> (main-based) -> approve `mission-spine-migration-release`
                     ★REQUIRED even though this release adds no SQL: promote-off's verify_migration_result.py demands
                      exactly one non-expired artifact named mission-spine-migration-result-<release id>-<run>-attempt-1★
  promote-off        gitops: switch the dispatcher to mission-spine-promote.yml -> approve `mission-spine-production-off`
  promote-on         gitops: empty nonce commit re-dispatches promote -> approve `mission-spine-staging` +
                     `mission-spine-production-on` (mission-ON -> canary 900s -> staging rebaseline)
  landing            gitops: switch the dispatcher to mission-spine-landing-last.yml ->
                     approve `mission-spine-production-landing` -> live /api checks

Cluster-side helpers (release_ops.py, over SSH) — read-only ones run inside preflight:
  tls-check | gate-measure | gate-place | gate-recall | argo-refresh

Usage: promote.py <coords.json> <step> [--confirmed] [extra]
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
BOT_NAME = "devpath-gitops-release[bot]"
BOT_EMAIL = "244265210+devpath-gitops-release[bot]@users.noreply.github.com"

argv = [a for a in sys.argv[1:] if a != "--confirmed"]
CONFIRMED = "--confirmed" in sys.argv
coords_path = pathlib.Path(argv[0])
coords = json.loads(coords_path.read_text(encoding="utf-8"))
step = argv[1]

OUT = pathlib.Path(coords["out_dir"])
RID = coords["release_id"]
TAG = RID.rsplit("-", 1)[1]                      # "budget"
BASE = coords["gitops_base_sha"]
SHARED_MAIN = coords["shared"]["main"]
BRANCH = f"automation/dispatch-{RID}"
CAND = f"release/candidate-{RID}"
GIT_WT = pathlib.Path("D:/workspace/dpa/.worktrees/gitops-dispatch-1003")      # gitops automation branch
CAND_WT = pathlib.Path("D:/workspace/dpa/.worktrees/gitops-candidate-1003")    # candidate branch (spec + seal)
MAIN_WT = pathlib.Path("D:/workspace/dpa/.worktrees/gitops-main-1003")         # detached at gitops main
SHARED_WT = pathlib.Path("D:/workspace/dpa/.worktrees/shared-dispatch-1003")
WF = ".github/workflows/mission-spine-release-gate-dispatch.yml"
ENV = {**os.environ, "MSYS_NO_PATHCONV": "1", "PYTHONUTF8": "1"}
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_ops as ops  # noqa: E402  (cluster-side helpers: TLS expiry, migration gate, Argo refresh)

PRODUCTION_STEPS = {"migration", "promote-off", "promote-resume", "promote-on", "promote-on-continue", "landing-resume",
                    "landing", "gate-place", "gate-recall", "argo-refresh"}
if step in PRODUCTION_STEPS and not CONFIRMED:
    raise SystemExit(
        f"refusing `{step}`: it changes production. Re-run with --confirmed only after the human partner\n"
        f"has explicitly approved the promotion in this session. `preflight` needs no confirmation."
    )


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
    """Wait for the bot-dispatched run created after `since`; approve the listed environments as they pend."""
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


def gitops_dispatcher_commit(rendered: bytes | None, message: str, key: str) -> str:
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
    coords.setdefault("production", {})[key] = {"commit": commit, "at": since, "message": message}
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
        print(out_file.read_text(encoding="utf-8").strip().splitlines()[0:5])
    assert done.returncode == 0, "promotion chain verifier refused the current main as this release's base"
    # the shared migration producer promote-off will demand (required even with no new SQL)
    assert git("rev-parse", "origin/main", cwd=SHARED) == SHARED_MAIN, "shared main moved from the spec's source_sha"
    print("shared main =", SHARED_MAIN, "(matches spec shared_migration.source_sha)")
    print("shared dispatcher branch exists:", bool(git("ls-remote", "--heads", "origin", BRANCH, cwd=SHARED)))
    # static TLS secrets the sandbox runner depends on
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
    print("  ai-svc          :", spec["services"]["devpath-ai-svc"]["image_digest"], "source", spec["services"]["devpath-ai-svc"]["source_sha"][:8])
    print("  gateway         :", spec["services"]["devpath-gateway"]["image_digest"], "source", spec["services"]["devpath-gateway"]["source_sha"][:8])
    print("  shared migration:", spec["shared_migration"]["flyway_target"], spec["shared_migration"]["required_migration"])
    print("  home landing    :", spec["home"]["source_sha"][:8], "dist", spec["home"]["dist_sha256"][:12], "prior deployment", spec["home"]["prior_production_deployment_id"])
    print("  canary          :", spec["rollout"]["canary_seconds"], "s · order", " -> ".join(spec["rollout"]["production_order"]))

elif step == "migration":
    run(["py", str(OUT / "render_dispatchers.py"), str(coords_path), "migration"])
    rendered = (OUT / "dispatchers" / "shared-migration.yml").read_bytes()
    assert coords["validate"]["sealed_sha"].encode() in rendered and SHARED_MAIN.encode() in rendered and b"\r" not in rendered
    git("fetch", "-q", "origin", "main", cwd=SHARED)
    assert git("rev-parse", "origin/main", cwd=SHARED) == SHARED_MAIN, "shared main moved"
    assert git("ls-remote", "--heads", "origin", BRANCH, cwd=SHARED) == "" and not SHARED_WT.exists()
    run(["git", "-C", SHARED, "worktree", "add", "-b", BRANCH, str(SHARED_WT), SHARED_MAIN])
    (SHARED_WT / WF).parent.mkdir(parents=True, exist_ok=True)
    (SHARED_WT / WF).write_bytes(rendered)
    run(["git", "-C", str(SHARED_WT), "add", WF])
    run(["git", "-C", str(SHARED_WT), "-c", "core.autocrlf=false", "commit", "-q", "-F", "-"],
        inp=f"ci: dispatch protected migration release ({RID})\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n")
    since = stamp()
    run(["git", "-C", str(SHARED_WT), "push", "-q", "-u", "origin", BRANCH])
    coords.setdefault("production", {})["migration_dispatched_after"] = since
    save()
    r = wait_bot_run(SHARED_REPO, "mission-spine-migration-release.yml", since, ["mission-spine-migration-release"], "shared migration-release")
    coords["production"]["migration_run"] = {"id": r["id"], "conclusion": r["conclusion"]}
    save()
    assert r["conclusion"] == "success", "migration-release failed — stop and inspect before promoting"

elif step == "promote-off":
    run(["py", str(OUT / "render_dispatchers.py"), str(coords_path), "promote"])
    rendered = (OUT / "dispatchers" / "gitops-promote.yml").read_bytes()
    ensure_gate()  # the migration Job's init container refuses without it (2026-09-24: ~6 min of fence downtime)
    since = gitops_dispatcher_commit(rendered, f"ci: dispatch {RID} production promotion", "promote_off_dispatch")
    r = watched(lambda: wait_bot_run(GITOPS_REPO, "mission-spine-promote.yml", since, ["mission-spine-production-off"], "promote (migration -> services -> mission-OFF)"))
    coords["production"]["promote_off_run"] = {"id": r["id"], "conclusion": r["conclusion"]}
    save()
    if r["conclusion"] == "success":
        recall_gate()
    assert r["conclusion"] == "success", "promote OFF run failed — inspect; the gate stays in place for `promote-resume`"

elif step == "promote-resume":
    # r3 precedent: promote resolves its own phase, so after fixing the cause an empty nonce commit resumes the OFF job
    reason = argv[2] if len(argv) > 2 else "after all nine services converged"
    ensure_gate()
    since = gitops_dispatcher_commit(None, f"ci: resume {RID} promotion {reason}", f"promote_resume_{stamp()}")
    r = watched(lambda: wait_bot_run(GITOPS_REPO, "mission-spine-promote.yml", since, ["mission-spine-production-off"], "promote resume (services -> mission-OFF)"))
    coords["production"].setdefault("promote_off_runs", []).append({"id": r["id"], "conclusion": r["conclusion"]})
    save()
    if r["conclusion"] == "success":
        recall_gate()
    assert r["conclusion"] == "success", "resumed promote OFF run failed — inspect before resuming again"

elif step == "promote-on":
    since = gitops_dispatcher_commit(None, f"ci: promote {RID} mission ON and canary", "promote_on_dispatch")
    r = watched(lambda: wait_bot_run(GITOPS_REPO, "mission-spine-promote.yml", since, ["mission-spine-staging", "mission-spine-production-on"], "promote (mission-ON + canary + staging rebaseline)"))
    coords["production"]["promote_on_run"] = {"id": r["id"], "conclusion": r["conclusion"]}
    save()
    assert r["conclusion"] == "success", "promote ON run failed — inspect before landing"

elif step == "promote-on-continue":
    # the ON run was already dispatched (nonce pushed); resume approving its gates in any order and wait
    since = coords["production"]["promote_on_dispatch"]["at"]
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
    run(["py", str(OUT / "render_dispatchers.py"), str(coords_path), "landing"])
    rendered = (OUT / "dispatchers" / "gitops-landing.yml").read_bytes()
    since = gitops_dispatcher_commit(rendered, f"ci: dispatch {RID} landing-last gate", "landing_dispatch")
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

elif step == "landing-resume":
    # 2026-10-01: the first landing run deployed successfully but `capture-new-production` probed the public dist
    # marker 1.17s after "Deployment complete!" and got a 404 — HTTPError is an OSError, so the gate reported
    # "public dist marker probe failed" with no retry/backoff. Production already serves the sealed dist, so a
    # fresh run takes preflight's reuse branch (current production != prior) and must NOT deploy again.
    # The dispatcher bytes are unchanged, so resume with an empty nonce commit.
    reason = argv[2] if len(argv) > 2 else "after the marker propagated"
    since = gitops_dispatcher_commit(None, f"ci: resume {RID} landing-last {reason}", f"landing_resume_{stamp()}")
    r = wait_bot_run(GITOPS_REPO, "mission-spine-landing-last.yml", since, ["mission-spine-production-landing"], "landing-last resume (reuse the deployed dist)")
    coords.setdefault("production", {}).setdefault("landing_runs", []).append({"id": r["id"], "conclusion": r["conclusion"]})
    save()
    for path in ("/api/invite-rounds", "/api/stats", "/updates", "/"):
        try:
            with urllib.request.urlopen(urllib.request.Request("https://leva.ai.kr" + path, headers={"User-Agent": "release-check"}), timeout=20) as resp:
                print(f"  GET {path}: {resp.status} {resp.headers.get('content-type','')} {resp.read(200)[:60]!r}")
        except Exception as exc:  # noqa: BLE001
            print(f"  GET {path}: ERROR {exc}")
    assert r["conclusion"] == "success"

else:
    raise SystemExit("unknown step")
