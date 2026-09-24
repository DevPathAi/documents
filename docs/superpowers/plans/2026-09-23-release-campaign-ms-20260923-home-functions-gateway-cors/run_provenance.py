"""Compute the release-mode ET13 input provenance for both lanes for ms-20260923-home-functions-gateway-cors.

Derived from r3's run_provenance_r3.py: same frontend source 31a7785d, same build marker, new release id and the
new approved baseline (run 35862514213, artifact 10750996942). Requires the ET13 builds (Flutter 3.44.1 = CI pin)
under build/et13/build/{web,admin} whose main.dart.js hashes equal the build marker.
"""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

WORKTREE = pathlib.Path("D:/workspace/dpa/.worktrees/frontend-et13-prov")
OUT = pathlib.Path("D:/workspace/dpa/.release-artifacts/ms-20260923-home-functions-gateway-cors/candidate-provenance")
SOURCE_SHA = "31a7785d5f3c73563c8ddb61b69a7a0e07f65f16"
RELEASE_ID = "ms-20260923-home-functions-gateway-cors"
BASELINE_RUN = "35862514213"
BASELINE_ARTIFACT = "10750996942"
BASELINE_NAME = f"{RELEASE_ID}-frontend-visual-approved-baseline-run-{BASELINE_RUN}-attempt-1"
BASELINE_ARCHIVE_SHA256 = "863331870949032bf4f53373e18cb8455c98087e61602ed51e6ff7b83ac2243d"
BASELINE_WORKFLOW_SHA256 = "24e959a7b34a02ca7f65e2a8f0af5d0a901a12d89deddc6f29ed564f868ef833"
DART = "D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin/dart.bat"  # explicit .bat: no shell needed
BS = chr(92)


def win(*parts: str) -> str:
    """A Windows-native relative path: the tool compares path strings, so separators must be backslashes."""
    return BS.join(parts)


marker = json.loads((WORKTREE / "build" / "et13" / "build-marker.v1.json").read_text(encoding="utf-8"))
for dist in marker["distributions"]:
    built = WORKTREE / "build" / "et13" / "build" / dist["id"] / "main.dart.js"
    actual = hashlib.sha256(built.read_bytes()).hexdigest()
    assert actual == dist["main_dart_js_sha256"], (dist["id"], actual)
print("build marker matches both distributions")

archive = pathlib.Path("D:/workspace/dpa/.release-artifacts/ms-20260923-home-functions-gateway-cors/baseline-artifact.zip")
assert hashlib.sha256(archive.read_bytes()).hexdigest() == BASELINE_ARCHIVE_SHA256

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
        f"--baseline-run-id={BASELINE_RUN}",
        "--baseline-run-attempt=1",
        f"--baseline-artifact-id={BASELINE_ARTIFACT}",
        f"--baseline-artifact-name={BASELINE_NAME}",
        f"--baseline-artifact-archive-sha256={BASELINE_ARCHIVE_SHA256}",
        f"--baseline-workflow-sha256={BASELINE_WORKFLOW_SHA256}",
    ]
    done = subprocess.run(command, cwd=WORKTREE, capture_output=True, text=True)
    print(f"[{lane}] rc={done.returncode} | {done.stdout.strip() or done.stderr.strip()[-300:]}")
    if done.returncode != 0:
        sys.exit(1)
    raw = output.read_bytes()
    (OUT / f"{lane}-provenance.v1.json").write_bytes(raw)
    document = json.loads(raw)
    unsigned = {k: v for k, v in document.items() if k != "input_provenance_sha256"}
    canonical = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert canonical == document["input_provenance_sha256"], lane
    results[lane] = {
        "input_provenance_sha256": document["input_provenance_sha256"],
        "input_provenance_file_sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "cr_bytes": raw.count(b"\r"),
        "kind": document.get("kind"),
        "source_sha": document.get("source_sha"),
        "release_id": document.get("release_id"),
        "baseline_run_id": (document.get("baseline_authentication") or {}).get("run_id"),
    }
(OUT / "summary.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
print(json.dumps(results, indent=1))
