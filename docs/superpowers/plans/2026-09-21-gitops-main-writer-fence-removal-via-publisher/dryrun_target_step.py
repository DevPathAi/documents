#!/usr/bin/env python3
"""Run the publisher's target-test step body (without pip/unittest) in a standalone bash, against real checkouts.

Usage: dryrun_target_step.py <workflow.yml> <checkout dir> <label> [ENV=VALUE ...]
Env overrides let a control run point the same script at a different commit.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import yaml

workflow, checkout, label = sys.argv[1:4]
overrides = dict(item.split("=", 1) for item in sys.argv[4:])
document = yaml.safe_load(open(workflow, encoding="utf-8"))
job = document["jobs"]["publish"]
step = next(s for s in job["steps"] if s.get("name") == "Test the exact fence-removal target")
body = step["run"]
cut = body.index("python -m pip install")
script = body[:cut] + 'echo "STEP-ASSERTIONS-PASSED"\n'
env = {**os.environ, **{k: str(v) for k, v in job["env"].items()}, **overrides}
with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False, encoding="utf-8", newline="\n") as handle:
    handle.write(script)
    path = handle.name
bash = os.environ["DRYRUN_BASH"]  # an explicit Git Bash; a bare `bash` on Windows may resolve to WSL
done = subprocess.run([bash, "-e", path.replace(chr(92), "/")], cwd=checkout, env=env, capture_output=True,
                      text=True, encoding="utf-8", errors="replace")
os.unlink(path)
tail = ((done.stdout or "").strip().splitlines() or [""])[-1]
print(f"[{label}] rc={done.returncode} last_stdout={tail!r} stderr={(done.stderr or "").strip()[-200:]!r}")
