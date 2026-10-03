#!/usr/bin/env python3
"""Negative controls for the AI-fallback-probe publisher contract test.

Usage: negative_controls.py <helper checkout>

Copies only the helper workflow and the contract test into a scratch tree, then runs the contract test against the
unmodified helper (must pass) and against tampered helpers (each must fail). Every tamper finds exactly one line
and asserts that the replacement really happened - a tamper that silently did nothing would look "caught".
Mirrors the 2026-09-24 controls: listing row deletion, row count, force push, TARGET_TREE, target suite omission.
Plus the five tampers the 2026-10-03 review (L1) found the unstrengthened contract accepting: `if: false` on the
target test, `continue-on-error` on two gates, a top-level `defaults.run.shell`, `persist-credentials: true` on
the target checkout. Run before strengthen_contract_l1.py those five are accepted (the gap); after, refused.
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
NL = "\n"


def one_line(text: str, needle: str) -> str:
    lines = [line for line in text.split(NL) if needle in line]
    assert len(lines) == 1, (needle, len(lines))
    return lines[0]


def drop_row(text: str) -> str:
    line = one_line(text, "$'M\\tapps/devpath-ollama-gpu/base/deployment.yaml'")
    return text.replace(line + NL, "", 1)


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


def insert_after(text: str, needle: str, added: str) -> str:
    anchor = one_line(text, needle)
    return text.replace(anchor + NL, anchor + NL + added + NL, 1)


def step_if_false(text: str) -> str:
    return insert_after(text, "- name: Test the exact ai-fallback-probe target", "        if: false")


def gate_continue_on_error(text: str) -> str:
    return insert_after(
        text, "- name: Authenticate the live protected environment and this approval", "        continue-on-error: true"
    )


def context_continue_on_error(text: str) -> str:
    return insert_after(text, "- name: Prove the exact one-shot helper context", "        continue-on-error: true")


def top_level_defaults(text: str) -> str:
    assert one_line(text, "concurrency:") == "concurrency:"
    old = NL + "concurrency:" + NL
    assert text.count(old) == 1
    return text.replace(old, NL + "defaults:" + NL + "  run:" + NL + "    shell: bash" + NL + NL + "concurrency:" + NL, 1)


def target_checkout_credentials(text: str) -> str:
    start = text.index(one_line(text, "- name: Checkout the exact tested ai-fallback-probe target"))
    at = text.index("persist-credentials: false", start)
    assert at < text.index("- name: ", start + 10), "the checkout step has no persist-credentials line"
    return text[:at] + "persist-credentials: true" + text[at + len("persist-credentials: false"):]


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
                     ("target suite narrowed", skip_suite),
                     ("L1 if: false on the target test", step_if_false),
                     ("L1 continue-on-error on the live approval gate", gate_continue_on_error),
                     ("L1 continue-on-error on the helper context gate", context_continue_on_error),
                     ("L1 top-level defaults.run.shell", top_level_defaults),
                     ("L1 persist-credentials: true on the target checkout", target_checkout_credentials)):
    mutated = tamper(original)
    assert mutated != original, name
    rc = run(mutated)
    results.append(rc != 0)
    print(f"[{'PASS' if rc != 0 else 'FAIL'}] {name} refused (rc={rc})")
raise SystemExit(0 if all(results) else 1)
