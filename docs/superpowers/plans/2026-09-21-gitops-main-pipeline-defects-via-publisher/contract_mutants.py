#!/usr/bin/env python3
"""Run the publisher contract test against workflow mutants; every mutant must be KILLED (test run fails).

Usage: contract_mutants.py <helper dir containing .github/ and tests/>
The helper dir itself is never modified: each mutant lives in a temporary copy.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

helper = Path(sys.argv[1])
WORKFLOW = Path(".github/workflows/mission-spine-auth-smoke.yml")
TEST = "test_pipeline_defects_main_publish.py"
ATTACKER = "d" * 40
TAB = chr(92) + "t"
CONT = " " + chr(92) + "\n"
PUSH_STEP = "      - name: Fast-forward protected main to the exact tested pipeline-defects target\n        env:\n"
REAUTH_STEP = "      - name: Re-authenticate the published main\n        run: |\n"
TARGET_STEP = "      - name: Test the exact pipeline-defects target\n        working-directory: target\n        run: |\n          set -euo pipefail\n"
SANDBOX_ROW = f"            $'M{TAB}apps/devpath-sandbox-svc/base/deployment.yaml'" + CONT
NONEMPTY = '          test -n "$expected_listing"\n'
COMPARE = '          test "$target_listing" = "$expected_listing"\n'


def run_tests(root: Path) -> bool:
    done = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests/release", "-p", TEST],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return done.returncode == 0


def mutant(label: str, old: str, new: str) -> bool:
    with tempfile.TemporaryDirectory(prefix="contract-mutant-") as scratch:
        root = Path(scratch) / "helper"
        shutil.copytree(helper, root, ignore=shutil.ignore_patterns("__pycache__"))
        path = root / WORKFLOW
        text = path.read_bytes().decode("utf-8")
        assert text.count(old) == 1, (label, text.count(old))
        path.write_bytes(text.replace(old, new).encode("utf-8"))
        survived = run_tests(root)
    print(f"[{'SURVIVED' if survived else 'killed'}] {label}")
    return not survived


assert run_tests(helper), "the unmutated helper must pass its own contract test"
print("[ok] unmutated helper passes")
killed = [
    mutant("step env shadows TARGET_SHA on the push step", PUSH_STEP, PUSH_STEP + f"          TARGET_SHA: {ATTACKER}\n"),
    mutant(
        "step env shadows TARGET_SHA and TARGET_TREE on the re-authentication step",
        REAUTH_STEP,
        REAUTH_STEP.replace("        run: |\n", f"        env:\n          TARGET_SHA: {ATTACKER}\n          TARGET_TREE: {ATTACKER}\n        run: |\n"),
    ),
    mutant("strict mode removed from the target test step", TARGET_STEP, TARGET_STEP.replace("          set -euo pipefail\n", "")),
    mutant("strict mode weakened to `set +e` in the target test step", TARGET_STEP, TARGET_STEP.replace("set -euo pipefail", "set +e")),
    mutant("one expected row dropped from the pinned listing", SANDBOX_ROW, ""),
    mutant("the expected listing may be empty", NONEMPTY, ""),
    mutant("the whole-listing comparison removed", COMPARE, ""),
    mutant("the expected listing is reassigned from the target listing before the comparison",
           COMPARE, '          expected_listing="$target_listing"\n' + COMPARE),
    mutant("the comparison is weakened to a prefix match",
           COMPARE, '          [[ "$target_listing" == "$expected_listing"* ]]\n'),
]
raise SystemExit(0 if all(killed) else 1)
