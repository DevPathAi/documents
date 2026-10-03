"""Compute the release-mode ET13 input provenance for both lanes for the -r2 release id (rebuilt frontend).

Usage: run_provenance_r2.py <coords-r2.json>
coords-r2.json: {"release_id", "frontend_sha", "raw_build_marker" (path), "baseline": {"run_id", "artifact_id",
  "artifact_name", "archive_sha256", "workflow_sha256", "dir"}}
Requires: frontend worktree at frontend_sha (clean), Flutter 3.44.1 builds under build/et13/build/{web,admin}
matching the raw review artifact's build marker, and the approved baseline extracted under build/et13/external/baseline.
"""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

coords = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
RELEASE_ID = coords["release_id"]
SOURCE_SHA = coords["frontend_sha"]
BASE = coords["baseline"]
WORKTREE = pathlib.Path(coords["worktree"])
OUT = pathlib.Path(coords["out_dir"]) / "candidate-provenance"
DART = "D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin/dart.bat"
BS = chr(92)


def win(*parts: str) -> str:
    return BS.join(parts)


head = subprocess.run(["git", "-C", str(WORKTREE), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
assert head == SOURCE_SHA, head
marker_src = pathlib.Path(coords["raw_build_marker"])
marker = json.loads(marker_src.read_text(encoding="utf-8"))
assert marker["source_sha"] == SOURCE_SHA, marker["source_sha"]
for dist in marker["distributions"]:
    built = WORKTREE / "build" / "et13" / "build" / dist["id"] / "main.dart.js"
    actual = hashlib.sha256(built.read_bytes()).hexdigest()
    assert actual == dist["main_dart_js_sha256"], (dist["id"], actual, dist["main_dart_js_sha256"])
print("build marker matches both distributions")
target_marker = WORKTREE / "build" / "et13" / "build-marker.v1.json"
target_marker.write_bytes(marker_src.read_bytes())

baseline_dir = WORKTREE / "build" / "et13" / "external" / "baseline"
if baseline_dir.exists():
    shutil.rmtree(baseline_dir)
shutil.copytree(BASE["dir"], baseline_dir)
approval = json.loads((baseline_dir / "baseline-approval.v1.json").read_text(encoding="utf-8"))
assert approval["source_sha"] == SOURCE_SHA and approval["approval_run_id"] == int(BASE["run_id"]), approval
archive = pathlib.Path(BASE["archive"])
assert hashlib.sha256(archive.read_bytes()).hexdigest() == BASE["archive_sha256"]

stray = WORKTREE / "build" / "et13" / "producer$lane"
if stray.exists():
    shutil.rmtree(stray)
OUT.mkdir(parents=True, exist_ok=True)
results = {}
for lane in ("visual", "a11y"):
    output = WORKTREE / "build" / "et13" / "producer" / lane / "provenance.v1.json"
    if output.exists():
        output.unlink()
    command = [
        DART, "run", "tools/et13_evidence.dart", "provenance",
        f"--kind={lane}",
        f"--source-sha={SOURCE_SHA}",
        "--build-marker=" + win("build", "et13", "build-marker.v1.json"),
        "--output=" + win("build", "et13", "producer", lane, "provenance.v1.json"),
        "--mode=release_ready",
        f"--release-id={RELEASE_ID}",
        "--baseline-root=" + win("build", "et13", "external", "baseline"),
        "--baseline-approval=" + win("build", "et13", "external", "baseline", "baseline-approval.v1.json"),
        f"--baseline-run-id={BASE['run_id']}",
        "--baseline-run-attempt=1",
        f"--baseline-artifact-id={BASE['artifact_id']}",
        f"--baseline-artifact-name={BASE['artifact_name']}",
        f"--baseline-artifact-archive-sha256={BASE['archive_sha256']}",
        f"--baseline-workflow-sha256={BASE['workflow_sha256']}",
    ]
    done = subprocess.run(command, cwd=WORKTREE, capture_output=True, text=True)
    print(f"[{lane}] rc={done.returncode} | {done.stdout.strip() or done.stderr.strip()[-300:]}")
    if done.returncode != 0:
        sys.exit(1)
    raw = output.read_bytes()
    (OUT / f"{lane}-provenance.v1.json").write_bytes(raw)
    document = json.loads(raw)
    unsigned = {k: v for k, v in document.items() if k != "input_provenance_sha256"}
    canonical = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    assert canonical == document["input_provenance_sha256"], lane
    assert document["baseline_authentication"]["release_id"] == RELEASE_ID
    results[lane] = {
        "input_provenance_sha256": document["input_provenance_sha256"],
        "input_provenance_file_sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw), "cr_bytes": raw.count(b"\r"), "source_sha": document["source_sha"],
        "baseline_run_id": document["baseline_authentication"]["run_id"],
    }
(OUT / "summary.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
print(json.dumps(results, indent=1))
