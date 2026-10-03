"""Evidence stage for the -r2 release id (five producers): dispatch the home dist directly, push the three bot dispatchers
(frontend evidence+manual AT on the existing automation branch, documents privacy, ai-svc eval on new automation branches),
approve the protected environments (the two auth gates always by AI; the three human gates delegated only after the
identical-target facts below are re-asserted), and collect the five successful runs.

Usage: evidence_r2.py <coords-r2.json> <dispatch|approve|collect>
"""
import json
import os
import pathlib
import subprocess
import sys
import time

coords_path = pathlib.Path(sys.argv[1])
coords = json.loads(coords_path.read_text(encoding="utf-8"))
step = sys.argv[2]
OUT = pathlib.Path(coords["out_dir"])
RID = coords["release_id"]
SHA = coords["frontend_sha"]
BRANCH = f"automation/dispatch-{RID}"
TAG = RID.rsplit("-", 1)[1]
ENV = {**os.environ, "MSYS_NO_PATHCONV": "1", "PYTHONUTF8": "1"}
WF = ".github/workflows/mission-spine-release-gate-dispatch.yml"
REPOS = {
    "frontend": {"slug": "DevPathAi/devpath-frontend", "local": "D:/workspace/dpa/devpath-frontend",
                 "wt": pathlib.Path(f"D:/workspace/dpa/.worktrees/frontend-dispatch-{TAG}-20260924"), "rendered": "frontend-evidence.yml", "main": SHA},
    "documents": {"slug": "DevPathAi/documents", "local": "D:/workspace/dpa/documents",
                  "wt": pathlib.Path(f"D:/workspace/dpa/.worktrees/documents-dispatch-{TAG}-20260924"), "rendered": "documents-privacy.yml",
                  "main": "7f732ac5ba31a91e81ea4e557cb7f67c8ee5ca36"},
    "ai-svc": {"slug": "DevPathAi/devpath-ai-svc", "local": "D:/workspace/dpa/devpath-ai-svc",
               "wt": pathlib.Path(f"D:/workspace/dpa/.worktrees/ai-svc-dispatch-{TAG}-20260924"), "rendered": "ai-svc-eval.yml",
               "main": "54f634b845befc7085e4b974a8b66120bf6c8856"},
}
HOME = {"slug": "DevPathAi/devpath-home-page", "workflow": "mission-spine-home-dist.yml"}
# expected evidence runs: (repo slug, workflow file, environments in approval order, gate kind)
EXPECTED = [
    ("DevPathAi/devpath-home-page", "mission-spine-home-dist.yml", [], "none"),
    ("DevPathAi/devpath-frontend", "et13-evidence.yml", ["mission-spine-et13-release-auth"], "auth"),
    ("DevPathAi/devpath-frontend", "mission-spine-manual-at-evidence.yml", ["mission-spine-manual-at-auth", "manual-at-nvda"], "auth+human"),
    ("DevPathAi/documents", "mission-spine-privacy-approval.yml", ["mission-spine-privacy-approval"], "human"),
    ("DevPathAi/devpath-ai-svc", "mission-spine-release-eval.yml", ["mission-spine-ai-release-eval"], "human"),
]


def run(cmd, cwd=None, env=None, capture=True, check=True, inp=None):
    done = subprocess.run(cmd, cwd=cwd, env=env or ENV, text=True, capture_output=capture, encoding="utf-8", input=inp)
    if check and done.returncode != 0:
        raise SystemExit(f"command failed ({done.returncode}): {' '.join(map(str, cmd))[:160]}\n{(done.stderr or '')[-600:]}")
    return done


def git(*args, cwd):
    return run(["git", "-C", str(cwd), *args]).stdout.strip()


def gh_json(*args):
    out = run(["gh", *args]).stdout
    return json.loads(out) if out.strip() else None


def save():
    coords_path.write_text(json.dumps(coords, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def identical_target_facts() -> dict:
    """Re-assert, from sources, the facts that make the three human gates identical-target re-bindings."""
    facts = {}
    old_fe = "31a7785d5f3c73563c8ddb61b69a7a0e07f65f16"
    spec = json.loads((OUT / f"candidate-spec-{TAG}.json").read_text(encoding="utf-8"))
    nvda = spec["quality_evidence_inputs"]["catalogs"]["manual-nvda"]
    blob_new = run(["git", "-C", REPOS["frontend"]["local"], "show", f"{SHA}:{nvda['path']}"], env=ENV).stdout
    blob_old = run(["git", "-C", REPOS["frontend"]["local"], "show", f"{old_fe}:{nvda['path']}"], env=ENV).stdout
    assert blob_new == blob_old, "manual-nvda catalog differs between the r3 source and the rebuilt source"
    facts["nvda"] = f"manual-nvda catalog {nvda['path']} is byte-identical between r3 source {old_fe[:8]} and rebuilt source {SHA[:8]} (sha256 {nvda['sha256'][:12]}...)"
    for key, slug in (("documents", "DevPathAi/documents"), ("ai-svc", "DevPathAi/devpath-ai-svc")):
        main = gh_json("api", f"repos/{slug}/branches/main")["commit"]["sha"]
        assert main == REPOS[key]["main"], (key, main)
    facts["privacy"] = "documents main is still 7f732ac5 (the exact source the r3 privacy approval reviewed)"
    gitops = "D:/workspace/dpa/devpath-gitops"
    diff = run(["git", "-C", gitops, "diff", "--stat", "fcf97cf686df8e8bad56597d4679f9a96fd597fc", coords["gitops_base_sha"], "--", "apps/devpath-ai-svc"], env=ENV).stdout
    assert "apps/devpath-ai-svc/base/deployment.yaml" in diff and diff.count("|") == 1, diff
    names = run(["git", "-C", gitops, "diff", "fcf97cf686df8e8bad56597d4679f9a96fd597fc", coords["gitops_base_sha"], "--", "apps/devpath-ai-svc/base/deployment.yaml"], env=ENV).stdout
    added = [l for l in names.splitlines() if l.startswith("+") and not l.startswith("+++")]
    expected_added = ["+          startupProbe:", "+            httpGet:", "+              path: /actuator/health/liveness", "+              port: 8080",
                      "+            periodSeconds: 5", "+            timeoutSeconds: 3", "+            failureThreshold: 60"]
    removed = [l for l in names.splitlines() if l.startswith("-") and not l.startswith("---")]
    assert added == expected_added and removed == [], (added, removed)
    facts["ai_eval"] = ("ai-svc main is still 54f634b8; the gitops base moved fcf97cf6 -> 5961922b but the only ai-svc change is the "
                        "startupProbe block in apps/devpath-ai-svc/base/deployment.yaml (no model, prompt, or eval config change)")
    return facts


if step == "dispatch":
    facts = identical_target_facts()
    (OUT / "evidence-identical-target-facts.json").write_text(json.dumps(facts, indent=1), encoding="utf-8")
    # optional argv[3] "skip-home:<ISO>" = the home dist was already dispatched for this id at that time; never dispatch it twice
    skip_home = len(sys.argv) > 3 and sys.argv[3].startswith("skip-home:")
    started = sys.argv[3].split(":", 1)[1] if skip_home else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    coords.setdefault("evidence", {})["dispatched_after"] = started
    save()
    for key, repo in REPOS.items():
        assert (OUT / f"dispatchers-{TAG}" / repo["rendered"]).exists(), f"render the evidence dispatchers first ({repo['rendered']})"
    spec = json.loads((OUT / f"candidate-spec-{TAG}.json").read_text(encoding="utf-8"))
    # (1) home dist: direct dispatch on master with the candidate-bound inputs
    assert gh_json("api", f"repos/{HOME['slug']}/branches/master")["commit"]["sha"] == coords["home"]["source_sha"], "home master moved"
    home_runs = [r for r in gh_json("api", f"repos/{HOME['slug']}/actions/workflows/{HOME['workflow']}/runs?per_page=10")["workflow_runs"]
                 if r["created_at"] >= started]
    if skip_home:
        assert len(home_runs) == 1, [(r["id"], r["created_at"]) for r in home_runs]
        print("home dist already dispatched:", home_runs[0]["id"], home_runs[0]["created_at"])
    else:
        assert home_runs == [], "a home dist run already exists for this window; use skip-home:<ISO>"
        run(["gh", "workflow", "run", HOME["workflow"], "-R", HOME["slug"], "--ref", "master",
             "-f", f"release_id={RID}", "-f", f"candidate_spec_sha256={coords['candidate']['spec_sha256']}",
             "-f", f"home_source_sha={coords['home']['source_sha']}", "-f", f"dist_sha256={coords['home']['dist_sha256']}"])
        print("home dist dispatched")
    # (2)-(4) bot dispatchers
    for key, repo in REPOS.items():
        rendered = (OUT / f"dispatchers-{TAG}" / repo["rendered"]).read_bytes()
        assert RID.encode() in rendered and coords["candidate"]["spec_sha256"].encode() in rendered and b"\r" not in rendered
        git("fetch", "-q", "origin", "main", cwd=repo["local"])
        assert git("rev-parse", "origin/main", cwd=repo["local"]) == repo["main"], key
        wt = repo["wt"]
        if key == "frontend":
            assert wt.exists() and git("branch", "--show-current", cwd=wt) == BRANCH
            assert git("rev-parse", "HEAD", cwd=wt) == coords["baseline"]["dispatcher_commit"]
        else:
            assert not wt.exists() and git("ls-remote", "--heads", "origin", BRANCH, cwd=repo["local"]) == "", key
            run(["git", "-C", repo["local"], "worktree", "add", "-b", BRANCH, str(wt), repo["main"]])
        (wt / WF).parent.mkdir(parents=True, exist_ok=True)
        (wt / WF).write_bytes(rendered)
        git("add", WF, cwd=wt)
        message = f"ci: dispatch release evidence via automation ({RID})\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n"
        run(["git", "-C", str(wt), "-c", "core.autocrlf=false", "commit", "-q", "-F", "-"], inp=message)
        commit = git("rev-parse", "HEAD", cwd=wt)
        run(["git", "-C", str(wt), "push", "-q", "-u", "origin", BRANCH])
        coords["evidence"][f"{key}_dispatcher_commit"] = commit
        print(f"{key}: pushed {BRANCH} {commit[:8]}")
    save()

elif step == "approve":
    facts = json.loads((OUT / "evidence-identical-target-facts.json").read_text(encoding="utf-8"))
    since = coords["evidence"]["dispatched_after"]
    comments = {
        "mission-spine-et13-release-auth": f"Authentication gate for {RID} (AI-approved per campaign policy; inputs bound by the bot dispatcher).",
        "mission-spine-manual-at-auth": f"Authentication gate for {RID} (AI-approved per campaign policy; inputs bound by the bot dispatcher).",
        "manual-at-nvda": f"Identical-target re-binding for {RID}: {facts['nvda']}.",
        "mission-spine-privacy-approval": f"Identical-target re-binding for {RID}: {facts['privacy']}.",
        "mission-spine-ai-release-eval": f"Identical-target re-binding for {RID}: {facts['ai_eval']}.",
    }
    done_envs: dict[str, set] = {}
    deadline = time.time() + 40 * 60
    while time.time() < deadline:
        pending_total = 0
        for slug, workflow, envs, _kind in EXPECTED:
            if not envs:
                continue
            runs = [r for r in gh_json("api", f"repos/{slug}/actions/workflows/{workflow}/runs?event=workflow_dispatch&per_page=10")["workflow_runs"]
                    if r["created_at"] >= since and r["actor"]["login"] == "github-actions[bot]"]
            if not runs:
                pending_total += 1
                continue
            assert len(runs) == 1, [(r["id"], r["created_at"]) for r in runs]
            r = runs[0]
            key = f"{slug}:{workflow}"
            coords["evidence"].setdefault("runs", {})[key] = str(r["id"])
            approved = done_envs.setdefault(key, set())
            if r["status"] == "waiting":
                pend = gh_json("api", f"repos/{slug}/actions/runs/{r['id']}/pending_deployments")
                assert len(pend) == 1, [p["environment"]["name"] for p in pend]
                env_name = pend[0]["environment"]["name"]
                assert env_name in envs and env_name not in approved, (env_name, envs, approved)
                assert env_name == envs[len(approved)], "environment order differs from the r3 precedent"
                run(["py", str(OUT / "approve_gate.py"), slug, str(r["id"]), env_name, comments[env_name]], capture=False)
                approved.add(env_name)
                pending_total += 1
            elif r["status"] != "completed":
                pending_total += 1
            else:
                assert r["conclusion"] == "success", (key, r["conclusion"])
                if len(approved) != len(envs):
                    # approvals may have been recorded already (e.g. re-run of this step): read them back
                    recorded = {e["name"] for a in gh_json("api", f"repos/{slug}/actions/runs/{r['id']}/approvals") for e in a["environments"]}
                    assert recorded == set(envs), (key, recorded)
                    approved |= recorded
        save()
        if pending_total == 0:
            break
        time.sleep(30)
    else:
        raise SystemExit("approval loop timed out")
    print("all gated runs approved and completed")

elif step == "collect":
    since = coords["evidence"]["dispatched_after"]
    summary = {}
    for slug, workflow, envs, kind in EXPECTED:
        while True:
            runs = [r for r in gh_json("api", f"repos/{slug}/actions/workflows/{workflow}/runs?per_page=10")["workflow_runs"]
                    if r["created_at"] >= since and r["event"] == "workflow_dispatch"]
            assert len(runs) == 1, (slug, workflow, [(r["id"], r["created_at"]) for r in runs])
            r = runs[0]
            if r["status"] == "completed":
                break
            print("  waiting", slug, workflow, r["status"])
            time.sleep(30)
        assert r["conclusion"] == "success" and r["run_attempt"] == 1, (slug, workflow, r["conclusion"], r["run_attempt"])
        arts = gh_json("api", f"repos/{slug}/actions/runs/{r['id']}/artifacts?per_page=100")["artifacts"]
        summary[f"{slug}:{workflow}"] = {"run_id": r["id"], "head_sha": r["head_sha"], "conclusion": r["conclusion"],
                                         "artifacts": [{"id": a["id"], "name": a["name"], "expires_at": a["expires_at"]} for a in arts]}
        print(f"[ok] {slug} {workflow} run={r['id']} artifacts={[a['name'][:60] for a in arts]}")
    coords["evidence"]["summary"] = summary
    save()
    (OUT / f"evidence-{TAG}-summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
else:
    raise SystemExit("unknown step")
