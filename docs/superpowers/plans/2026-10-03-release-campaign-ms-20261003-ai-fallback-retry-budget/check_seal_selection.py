"""validate 재디스패치 전 확인 — main 의 seal 코드(select_frontend_evidence_run)가 지금 frontend producer 런을 하나로 고르는지 실제 API 로 재현한다.

Usage: (cd <gitops worktree at main>/scripts/release && GH_TOKEN=$(gh auth token) PYTHONUTF8=1 py <this file>)
2026-10-03 11:10Z seal 이 「exactly one frontend producer run is required」로 실패했지만 같은 코드가 11:2xZ 에는 37117660640 을 골랐다.
"""
import os, sys
sys.path.insert(0, os.getcwd())
import seal_release_manifest as s
env = dict(os.environ)
repo, head, rid = "DevPathAi/devpath-frontend", "b69e99909bd028682a9c0a3ca11489ac87f90fb9", "ms-20261003-ai-fallback-retry-budget"
runs = s.list_frontend_evidence_runs(env, repo, head)
print([(r["id"], r["path"].rsplit("/", 1)[-1]) for r in runs])
print("SELECTED", s.select_frontend_evidence_run(runs, head, env=env, repository=repo, release_id=rid)["id"])
