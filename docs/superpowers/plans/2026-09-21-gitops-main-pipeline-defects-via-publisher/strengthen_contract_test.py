#!/usr/bin/env python3
"""Strengthen the rendered contract test with findings F1 and F2 of the 2026-09-23 independent review.

Usage: strengthen_contract_test.py <rendered contract test> <reviewed helper workflow> <destination>

F1  The token-bearing steps (mint onward) were pinned only by fragments, so a reassignment of TARGET_SHA in the
    push step, a spliced `pu""sh`, an API PATCH with a split literal, or an extra `uses:` step that receives the
    App token all survived the test. From the mint onward every step is now compared whole against the reviewed
    step documents; the action set, the step-name sequence, the runner, and the number of App-token references
    are exact.
F2  Gate assertions were matched as substrings, so ` || :` and `true || ` kept the fragment intact while
    disabling the gate. Every gate step body is now compared line for line, and the `set -e` escapes that keep
    a fragment intact are forbidden spellings.

The literals are taken from the reviewed workflow bytes, so for a given (rendered test, workflow) pair this
script is deterministic: the strengthened test pins exactly the bytes that were reviewed.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import yaml

rendered, workflow, destination = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
text = io.open(rendered, encoding="utf-8", newline="").read()
wf_text = io.open(workflow, encoding="utf-8", newline="").read()
assert "\r" not in text and "\r" not in wf_text

document = yaml.safe_load(wf_text)
job = document["jobs"]["publish"]
steps = job["steps"]
names = [step.get("name") for step in steps]
LINE_CONTINUATION = re.compile(r"\\\n[ \t]*")

STEP_MINT = "Mint the production-scoped release App token"
GATES = (
    "Prove the exact one-shot helper context",
    "Run the publisher contract test on the exact helper bytes",
    "Authenticate the live protected environment and this approval",
    "Test the exact pipeline-defects target",
)
mint = names.index(STEP_MINT)


def replace(old: str, new: str, count: int = 1) -> None:
    global text
    assert text.count(old) == count, (old[:60], text.count(old), count)
    text = text.replace(old, new)


def normalized_lines(run: str) -> list[str]:
    return [" ".join(line.split()) for line in LINE_CONTINUATION.sub(" ", run).splitlines()]


# --- literals taken from the reviewed workflow ---------------------------------------------------------------
gate_bodies = {}
for name in GATES:
    (step,) = [step for step in steps if step.get("name") == name]
    gate_bodies[name] = normalized_lines(step["run"])
    assert gate_bodies[name][0] == "set -euo pipefail", name
    assert all(gate_bodies[name]), name  # no blank lines inside a gate body

marker = "      - name: " + STEP_MINT + "\n"
assert wf_text.count(marker) == 1
tail = wf_text[wf_text.index(marker):]
assert all(line.startswith("      ") or not line.strip() for line in tail.splitlines()), "steps are indented by six"
token_bearing = "\n".join(line[6:] if line.strip() else "" for line in tail.splitlines()) + "\n"
assert '"""' not in token_bearing and not token_bearing.endswith("\\\n")
assert yaml.safe_load(token_bearing) == steps[mint:], "the embedded literal must parse to the reviewed steps"

actions = sorted({step["uses"] for step in steps if "uses" in step})
assert len(actions) == 4, actions
# One checkout token + (token, app-slug, installation-id) on each of the two authority steps.
app_token_references = wf_text.count("steps.app_token")
assert app_token_references == 7, app_token_references
assert job["runs-on"] == "ubuntu-24.04" and job["timeout-minutes"] == 25


def py_list(items: list[str], indent: str) -> str:
    return "".join(f"{indent}{item!r},\n" for item in items)


gate_literal = "GATE_BODIES = {\n"
for name, lines in gate_bodies.items():
    gate_literal += f"    {name!r}: [\n" + py_list(lines, "        ") + "    ],\n"
gate_literal += "}\n"

constants = (
    "\n"
    "# 2026-09-23 independent review, F1/F2: the literals below are the reviewed workflow bytes.\n"
    "STEP_NAMES = [\n" + py_list([name if name is not None else None for name in names], "    ").replace("None,", "None,") +
    "]\n"
    "PINNED_ACTIONS = [\n" + py_list(actions, "    ") + "]\n"
    f"APP_TOKEN_REFERENCES = {app_token_references}\n"
    "SHELL_ESCAPE = re.compile(\n"
    "    r\"(eval|source|\\.|export|read|printf -v|declare|typeset|local|unset|trap|exec|alias|function)(\\s|$)\"\n"
    "    r\"|(export\\s+)?(MAIN_SHA|TARGET_SHA|TARGET_TREE|HELPER_BASE_SHA|HELPER_BRANCH|TARGET_BRANCH\"\n"
    "    r\"|PROTECTED_ENVIRONMENT|APPROVER_LOGIN|GITHUB_[A-Z_]+)=\"\n"
    ")\n"
    + gate_literal
    + 'TOKEN_BEARING_STEPS = r"""\n' + token_bearing + '"""\n'
)

# --- edits to the rendered test --------------------------------------------------------------------------------
replace(
    'STEP_REAUTH = "Re-authenticate the published main"\n',
    'STEP_REAUTH = "Re-authenticate the published main"\n' + constants,
)
replace(
    '            for weakening in ("set +e", "set +u", "set +o pipefail", "|| true"):\n'
    '                self.assertNotIn(weakening, step["run"], step.get("name"))\n',
    '            for weakening in (\n'
    '                "set +e", "set +u", "set +o pipefail", "|| true", "|| :", "||:", "true ||", ":||"\n'
    '            ):\n'
    '                self.assertNotIn(weakening, step["run"], step.get("name"))\n'
    '            # F2: no builtin that rewrites variables or sources code, no pin reassigned mid-step.\n'
    '            for line in step["run"].splitlines():\n'
    '                self.assertIsNone(SHELL_ESCAPE.match(line.strip()), (step.get("name"), line))\n',
)
replace(
    "        for reference in used:\n"
    "            self.assertIsNotNone(PINNED_ACTION.fullmatch(reference), reference)\n",
    "        for reference in used:\n"
    "            self.assertIsNotNone(PINNED_ACTION.fullmatch(reference), reference)\n"
    "        # F1: the action set is exact - no other action may receive the App token.\n"
    "        self.assertEqual(PINNED_ACTIONS, sorted(set(used)))\n"
    "        self.assertEqual(STEP_NAMES, self.names)\n",
)
new_tests = (
    "    def test_gate_step_bodies_are_exact(self) -> None:\n"
    "        # F2: a substring survives ` || :` and `true || `; each gate body is compared line for line\n"
    "        # (continuations folded, whitespace normalized) against the reviewed bytes.\n"
    "        for name, expected in GATE_BODIES.items():\n"
    "            run = LINE_CONTINUATION.sub(\" \", self._run(name))\n"
    "            self.assertEqual(expected, [\" \".join(line.split()) for line in run.splitlines()], name)\n"
    "\n"
    "    def test_token_bearing_steps_are_the_reviewed_documents(self) -> None:\n"
    "        # F1: from the mint onward nothing may differ from the reviewed step documents - not a\n"
    "        # reassignment before the push, not a spliced `pu\"\"sh`, not an API call, not an extra step.\n"
    "        mint = self.names.index(STEP_MINT)\n"
    "        self.assertEqual(yaml.safe_load(TOKEN_BEARING_STEPS), self.steps[mint:])\n"
    "        self.assertEqual(\"ubuntu-24.04\", self.job[\"runs-on\"])\n"
    "        self.assertEqual(25, self.job[\"timeout-minutes\"])\n"
    "        self.assertEqual(APP_TOKEN_REFERENCES, self.text.count(\"steps.app_token\"))\n"
    "\n"
)
replace('\n\nif __name__ == "__main__":\n', "\n" + new_tests + '\nif __name__ == "__main__":\n')

compile(text, str(destination), "exec")
io.open(destination, "w", encoding="utf-8", newline="\n").write(text)
print("strengthened", destination.name, len(text.splitlines()), "lines")
