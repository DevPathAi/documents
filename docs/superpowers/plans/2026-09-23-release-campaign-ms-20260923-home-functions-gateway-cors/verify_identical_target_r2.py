"""Before delegating the ET13 baseline approval: prove the rebuilt raw review renders the byte-identical PNG set that the
r3 baseline approved (candidate_set_sha256 2db5d572...), computed exactly as et13-baseline-approval.yml does
(lines "<artifact_path> <sha256>" in visual-cases order, then sha256 of that file).

Usage: verify_identical_target_r2.py <coords-r2.json>
Writes <out_dir>/IDENTICAL_TARGET_OK on success (baseline_r2.py dispatch requires it).
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys

coords = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
OUT = pathlib.Path(coords["out_dir"])
SHA = coords["frontend_sha"]
APPROVED_SET = "2db5d5723b522fde49496d8a18ae28964c4eb2f6b749557de1c6ace391198476"  # r3 / first-id approved baseline set
raw = OUT / "raw-review-r2"
env = {**os.environ, "MSYS_NO_PATHCONV": "1", "PYTHONUTF8": "1"}
cases = json.loads(subprocess.run(
    ["git", "-C", "D:/workspace/dpa/devpath-frontend", "show", f"{SHA}:evidence/et13/generated/visual-cases.v1.json"],
    capture_output=True, check=True, env=env).stdout)
paths = [c["artifact_path"] for c in cases["cases"]]
assert len(paths) == len(cases["cases"]) == 104, len(paths)
lines = []
first_id_dir = OUT / "baseline"
identical_to_first_id = 0
for path in paths:
    blob = (raw / "capture" / path).read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    lines.append(f"{path} {digest}\n")
    prior = first_id_dir / path
    if prior.exists() and prior.read_bytes() == blob:
        identical_to_first_id += 1
set_sha = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
print("candidate_set_sha256 =", set_sha)
print("byte-identical PNGs vs first-id approved baseline:", identical_to_first_id, "/", len(paths))
rc = json.loads((raw / "producer" / "visual" / "review-candidate.v1.json").read_text(encoding="utf-8"))
assert rc["source_sha"] == SHA, rc["source_sha"]
assert rc["producer_run_id"] == int(coords["raw_review"]["run_id"]), rc["producer_run_id"]
assert rc["case_count"] == 104 and rc["baseline_status"] == "pending_external_review", rc
marker = OUT / "IDENTICAL_TARGET_OK"
if set_sha != APPROVED_SET or identical_to_first_id != len(paths):
    if marker.exists():
        marker.unlink()
    print("NOT IDENTICAL - a human must review the baseline; do not delegate the approval")
    sys.exit(2)
marker.write_text(f"{SHA} {set_sha}\n", encoding="utf-8")
print("IDENTICAL TARGET: the rebuilt raw review reproduces the approved r3 baseline byte for byte -> delegation allowed (r3 policy)")
