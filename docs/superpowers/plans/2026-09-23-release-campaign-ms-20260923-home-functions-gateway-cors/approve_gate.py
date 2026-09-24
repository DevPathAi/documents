"""Approve exactly one pending deployment of one run, only if it is the expected environment."""
import json
import subprocess
import sys

repo, run_id, expected_env, comment = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]


def api(method: str, path: str, payload: dict | None = None):
    command = ["gh", "api", "-X", method, path]
    if payload is not None:
        command += ["--input", "-"]
    done = subprocess.run(command, input=json.dumps(payload) if payload else None,
                          capture_output=True, text=True, encoding="utf-8")
    if done.returncode != 0:
        raise SystemExit(f"{method} {path} failed: {done.stderr.strip()[:300]}")
    return json.loads(done.stdout) if done.stdout.strip() else None


path = f"repos/{repo}/actions/runs/{run_id}/pending_deployments"
run = api("GET", f"repos/{repo}/actions/runs/{run_id}")
assert run["actor"]["login"] == "github-actions[bot]" and run["run_attempt"] == 1, run["actor"]
pending = api("GET", path)
assert len(pending) == 1, [p["environment"]["name"] for p in pending]
entry = pending[0]
assert entry["environment"]["name"] == expected_env, entry["environment"]["name"]
assert entry["current_user_can_approve"] is True
approved = api("POST", path, {"environment_ids": [entry["environment"]["id"]], "state": "approved", "comment": comment})
assert isinstance(approved, list) and len(approved) == 1, approved
print(f"approved {expected_env} on {repo} run {run_id} (deployment {approved[0]['id']})")
