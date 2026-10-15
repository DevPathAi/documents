"""8단계 — validate 런(봇 디스패치)을 찾아 mission-spine-staging 승인(AI, 10/02 방침)을 대기마다 한 번씩 처리하고 완료까지 기다린다."""
import json, subprocess, sys, time
REPO = "DevPathAi/devpath-gitops"; SINCE = sys.argv[1]; RID = "ms-20261003-ai-fallback-retry-budget"
def gh(*a):
    out = subprocess.run(["gh", *a], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return json.loads(out) if out.strip() else None
approved = []
deadline = time.time() + 110 * 60
while time.time() < deadline:
    runs = [r for r in gh("api", f"repos/{REPO}/actions/workflows/mission-spine-validate.yml/runs?event=workflow_dispatch&per_page=10")["workflow_runs"]
            if r["created_at"] >= SINCE and r["actor"]["login"] == "github-actions[bot]"]
    if not runs:
        time.sleep(15); continue
    assert len(runs) == 1, [r["id"] for r in runs]
    r = runs[0]
    if r["status"] == "waiting":
        pend = gh("api", f"repos/{REPO}/actions/runs/{r['id']}/pending_deployments")
        names = [p["environment"]["name"] for p in pend]
        assert names == ["mission-spine-staging"], names
        n = len(approved) + 1
        assert n <= 2, "more than two staging approvals requested"
        done = subprocess.run(["py", "approve_gate.py", REPO, str(r["id"]), "mission-spine-staging",
            f"{RID}: GitOps validate/seal staging gate {n}/2 — AI 승인(2026-10-03 사용자 결정 10/02 방침). candidate c23f3b8e · evidence 5/5 success(사람 관문 3건 사용자 직접 승인)."],
            capture_output=True, text=True, encoding="utf-8")
        print(done.stdout.strip(), done.stderr.strip()[-300:], flush=True)
        assert done.returncode == 0
        approved.append(n)
    elif r["status"] == "completed":
        print(f"validate run {r['id']} {r['conclusion']} attempt={r['run_attempt']} approvals={len(approved)}", flush=True)
        sys.exit(0 if r["conclusion"] == "success" else 1)
    else:
        print(time.strftime("%H:%M:%S"), r["id"], r["status"], flush=True)
    time.sleep(30)
sys.exit("timeout")
