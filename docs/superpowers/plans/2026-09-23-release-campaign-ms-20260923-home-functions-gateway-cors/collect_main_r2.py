"""After the frontend release PR merges: wait for the main-push CI and ET13 raw review at the new main SHA,
download the immutable registry evidence (web off/on, admin) and the raw review build marker, and fill coords-r2.json.

Usage: collect_main_r2.py <coords-r2.json> [<expected main sha>]
"""
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import time
import zipfile

REPO = "DevPathAi/devpath-frontend"
coords_path = pathlib.Path(sys.argv[1])
coords = json.loads(coords_path.read_text(encoding="utf-8"))
OUT = pathlib.Path(coords["out_dir"])


def gh(*args: str, raw: bool = False):
    done = subprocess.run(["gh", *args], capture_output=True, text=not raw, encoding=None if raw else "utf-8", timeout=300)
    if done.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)[:120]} failed: {(done.stderr if raw else done.stderr).strip()[:300] if not raw else done.stderr[:300]}")
    return done.stdout if raw else (json.loads(done.stdout) if done.stdout.strip() else None)


main_sha = gh("api", f"repos/{REPO}/branches/main")["commit"]["sha"]
if len(sys.argv) > 2:
    assert main_sha == sys.argv[2], (main_sha, sys.argv[2])
assert main_sha != "31a7785d5f3c73563c8ddb61b69a7a0e07f65f16", "main has not moved"
print("main =", main_sha)


def find_run(workflow: str, event: str):
    runs = gh("api", f"repos/{REPO}/actions/workflows/{workflow}/runs?branch=main&event={event}&head_sha={main_sha}&per_page=10")["workflow_runs"]
    assert len(runs) == 1, [(r["id"], r["status"], r["conclusion"]) for r in runs]
    return runs[0]


def wait_success(workflow: str, event: str, budget_s: int = 3600):
    deadline = time.time() + budget_s
    while True:
        run = find_run(workflow, event)
        print(f"  {workflow}: run={run['id']} attempt={run['run_attempt']} status={run['status']} conclusion={run['conclusion']}")
        if run["status"] == "completed":
            assert run["conclusion"] == "success", (workflow, run["conclusion"])
            assert run["run_attempt"] == 1, run["run_attempt"]
            return run
        if time.time() > deadline:
            raise SystemExit(f"{workflow} did not finish in time")
        time.sleep(60)


ci = wait_success("ci.yml", "push")
raw = wait_success("et13-evidence.yml", "push")


def artifacts(run_id: int):
    return gh("api", f"repos/{REPO}/actions/runs/{run_id}/artifacts?per_page=100")["artifacts"]


def download(artifact_id: int) -> bytes:
    return gh("api", f"repos/{REPO}/actions/artifacts/{artifact_id}/zip", raw=True)


def one(items, name):
    hits = [a for a in items if a["name"] == name]
    assert len(hits) == 1, (name, [a["name"] for a in items])
    assert hits[0]["expired"] is False
    return hits[0]


ci_arts = artifacts(ci["id"])
digests = {}
evidence = {}
for key, name in (
    ("web_off_digest", f"leva-web-{main_sha}-mission-off-registry-evidence-run-{ci['id']}-attempt-1"),
    ("web_on_digest", f"leva-web-{main_sha}-mission-on-registry-evidence-run-{ci['id']}-attempt-1"),
    ("admin_digest", f"leva-admin-{main_sha}-registry-evidence-run-{ci['id']}-attempt-1"),
):
    art = one(ci_arts, name)
    blob = download(art["id"])
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = zf.namelist()
        assert len(names) == 1 and names[0].endswith(".registry.json"), names
        doc = json.loads(zf.read(names[0]))
    assert doc["source_sha"] == main_sha, doc
    assert doc["image_digest"].startswith("sha256:") and len(doc["image_digest"]) == 71
    if key.startswith("web"):
        assert doc["image_tag"] == f"{main_sha}-mission-{'off' if 'off' in key else 'on'}", doc["image_tag"]
        assert doc["compiled_config"]["mission_spine_enabled"] is ("on" in key.split("_")[1])
    digests[key] = doc["image_digest"]
    evidence[key] = {"artifact_id": art["id"], "artifact_name": name, "expires_at": art["expires_at"], "run_id": ci["id"], "document": doc}
    print(f"  {key} = {doc['image_digest']} (artifact {art['id']}, expires {art['expires_at']})")
assert len(set(digests.values()) | {"sha256:a6466f5de1714e12b7fcd01766e0fc0e4f61cf4dab4e6155ea0948ee3fb1c4e1"}) == 4, "digests must be distinct from each other and production"
(OUT / "image-evidence" / "frontend-r2.json").write_text(json.dumps(evidence, indent=1), encoding="utf-8")

raw_name = f"et13-unsealed-raw-review-run-{raw['id']}-attempt-1"
raw_art = one(artifacts(raw["id"]), raw_name)
raw_blob = download(raw_art["id"])
raw_dir = OUT / "raw-review-r2"
raw_dir.mkdir(exist_ok=True)
(OUT / "raw-review-r2-artifact.zip").write_bytes(raw_blob)
with zipfile.ZipFile(io.BytesIO(raw_blob)) as zf:
    assert "build-marker.v1.json" in zf.namelist(), zf.namelist()[:10]
    zf.extractall(raw_dir)
marker = json.loads((raw_dir / "build-marker.v1.json").read_text(encoding="utf-8"))
assert marker["source_sha"] == main_sha
assert [d["id"] for d in marker["distributions"]] == ["web", "admin"]
wf_sha = hashlib.sha256(subprocess.run(["git", "-C", "D:/workspace/dpa/devpath-frontend", "show", f"{main_sha}:.github/workflows/et13-evidence.yml"],
                                       capture_output=True, check=True, env={**__import__("os").environ, "MSYS_NO_PATHCONV": "1", "PYTHONUTF8": "1"}).stdout).hexdigest()
print(f"  raw review: run={raw['id']} artifact={raw_art['id']} digest={raw_art['digest']} expires={raw_art['expires_at']} workflow_sha256={wf_sha}")

coords["frontend_sha"] = main_sha
coords.update(digests)
coords["raw_review"] = {"run_id": str(raw["id"]), "run_attempt": "1", "artifact_id": str(raw_art["id"]), "artifact_digest": raw_art["digest"],
                        "artifact_name": raw_name, "expires_at": raw_art["expires_at"], "workflow_sha256": wf_sha,
                        "web_main_dart_js_sha256": marker["distributions"][0]["main_dart_js_sha256"],
                        "admin_main_dart_js_sha256": marker["distributions"][1]["main_dart_js_sha256"]}
coords["baseline"]["workflow_sha256"] = hashlib.sha256(subprocess.run(["git", "-C", "D:/workspace/dpa/devpath-frontend", "show", f"{main_sha}:.github/workflows/et13-baseline-approval.yml"],
                                                                      capture_output=True, check=True, env={**__import__("os").environ, "MSYS_NO_PATHCONV": "1", "PYTHONUTF8": "1"}).stdout).hexdigest()
coords["ci_run_id"] = str(ci["id"])
coords_path.write_text(json.dumps(coords, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("coords-r2.json updated")
