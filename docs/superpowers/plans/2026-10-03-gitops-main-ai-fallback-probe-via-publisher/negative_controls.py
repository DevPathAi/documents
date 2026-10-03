#!/usr/bin/env python3
"""Negative controls for the AI-fallback-probe publisher contract test.

Usage: negative_controls.py <helper checkout>

Copies only the helper workflow and the contract test into a scratch tree, then runs the contract test against the
unmodified helper (must pass) and against five tampered helpers (each must fail). Every tamper finds exactly one
line and asserts that the replacement really happened - a tamper that silently did nothing would look "caught".
Mirrors the 2026-09-24 controls: listing row deletion, row count, force push, TARGET_TREE, target suite omission.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HELPER = Path(sys.argv[1])
WORKFLOW = ".github/workflows/mission-spine-auth-smoke.yml"
CONTRACT = "tests/release/test_ai_fallback_probe_main_publish.py"
TREE = "fa3bcc60b2e9bb018ae0362c16f28696a028e470"


def one_line(text: str, needle: str) -> str:
    lines = [line for line in text.split("\n") if needle in line]
    assert len(lines) == 1, (needle, len(lines))
    return lines[0]


def drop_row(text: str) -> str:
    line = one_line(text, "$'M\\tapps/devpath-ollama-gpu/base/deployment.yaml'")
    return text.replace(line + "\n", "", 1)


def row_count(text: str) -> str:
    line = one_line(text, 'test "${#target_rows[@]}" -eq 5')
    return text.replace(line, line.replace("-eq 5", "-eq 4"), 1)


def force_push(text: str) -> str:
    line = one_line(text, 'git -C gitops-main push origin "$TARGET_SHA:refs/heads/main"')
    return text.replace(line, line.replace("push origin", "push --force origin"), 1)


def target_tree(text: str) -> str:
    line = one_line(text, f"TARGET_TREE: {TREE}")
    return text.replace(line, line.replace(TREE, "0" * 40), 1)


def skip_suite(text: str) -> str:
    line = one_line(text, "python -m unittest discover -s tests/release -p 'test_*.py'")
    return text.replace(line, line.replace("'test_*.py'", "'test_cloudflare_api.py'"), 1)


def run(text: str) -> int:
    with tempfile.TemporaryDirectory(prefix="aifb-contract-") as scratch:
        root = Path(scratch)
        for rel in (WORKFLOW, CONTRACT):
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / WORKFLOW).write_bytes(text.encode("utf-8"))
        shutil.copyfile(HELPER / CONTRACT, root / CONTRACT)
        done = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests/release", "-p", Path(CONTRACT).name],
            cwd=root, capture_output=True, text=True,
        )
        return done.returncode


original = (HELPER / WORKFLOW).read_bytes().decode("utf-8")
assert "\r" not in original
results = []
rc = run(original)
results.append(rc == 0)
print(f"[{'PASS' if rc == 0 else 'FAIL'}] original helper accepted (rc={rc})")
for name, tamper in (("listing row deleted", drop_row), ("row count 5 -> 4", row_count),
                     ("push --force", force_push), ("TARGET_TREE tampered", target_tree),
                     ("target suite narrowed", skip_suite)):
    mutated = tamper(original)
    assert mutated != original, name
    rc = run(mutated)
    results.append(rc != 0)
    print(f"[{'PASS' if rc != 0 else 'FAIL'}] {name} refused (rc={rc})")
raise SystemExit(0 if all(results) else 1)
