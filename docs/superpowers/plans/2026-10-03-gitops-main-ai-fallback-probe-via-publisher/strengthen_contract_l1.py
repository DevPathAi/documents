#!/usr/bin/env python3
"""Close review finding L1: pin the pre-token steps and the document shape of the publisher helper.

Usage: strengthen_contract_l1.py <rendered dir>

The rendered contract test compares the steps from the App-token mint onward as whole documents
(TOKEN_BEARING_STEPS) but the earlier gate steps only by their `run` text (GATE_BODIES). The 2026-10-03 review
accepted five tampers that way: `if: false` on the target test, `continue-on-error: true` on two gates, a
top-level `defaults.run.shell`, and `persist-credentials: true` on the target checkout. This script, run after
render_ai_fallback_probe_publisher.py, edits rendered/test_ai_fallback_probe_main_publish.py in place:

- PRE_TOKEN_STEPS: the verbatim YAML of every step before the mint, cut from the reviewed rendered/helper.yml
  bytes (asserted to parse to exactly those steps), compared whole like TOKEN_BEARING_STEPS;
- TOP_LEVEL_KEYS / JOB_KEYS: the exact key sets of the workflow and the job (no `defaults`, no extra `env`);
- no step may carry `if`, `continue-on-error`, `timeout-minutes` or `shell`;
- the stale method name `..._twelve_pinned_paths` (review L4) becomes `..._five_pinned_paths`.

Every edit finds exactly one anchor and is asserted to have happened. Structure: 2026-09-23
strengthen_contract_test.py (literals extracted from the reviewed workflow bytes, never hand-typed).
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import yaml

OUT = Path(sys.argv[1])
HELPER = OUT / "helper.yml"
CONTRACT = OUT / "test_ai_fallback_probe_main_publish.py"
MINT_LINE = "      - name: Mint the production-scoped release App token\n"
STEPS_LINE = "    steps:\n"

helper_text = io.open(HELPER, encoding="utf-8", newline="").read()
assert "\r" not in helper_text
document = yaml.safe_load(helper_text)
job = document["jobs"]["publish"]
steps = job["steps"]
mint = [step.get("name") for step in steps].index("Mint the production-scoped release App token")

assert helper_text.count(STEPS_LINE) == 1 and helper_text.count(MINT_LINE) == 1
pre_block = helper_text[helper_text.index(STEPS_LINE) + len(STEPS_LINE):helper_text.index(MINT_LINE)]
pre_lines = pre_block.split("\n")
assert all(line == "" or line.startswith("      ") for line in pre_lines)
pre_yaml = "\n".join(line[6:] for line in pre_lines).rstrip("\n") + "\n"
assert yaml.safe_load(pre_yaml) == steps[:mint], "the cut text does not parse to exactly the pre-token steps"
assert '"""' not in pre_yaml and not pre_yaml.rstrip("\n").endswith("\\")
for step in steps:
    for forbidden in ("if", "continue-on-error", "timeout-minutes", "shell"):
        assert forbidden not in step, (step.get("name"), forbidden)
top_keys = [key for key in document]
assert top_keys == ["name", True, "permissions", "concurrency", "jobs"], top_keys
job_keys = list(job)
assert job_keys == ["if", "runs-on", "timeout-minutes", "environment", "permissions", "env", "steps"], job_keys

text = io.open(CONTRACT, encoding="utf-8", newline="").read()
assert "\r" not in text


def replace_once(old: str, new: str) -> None:
    global text
    assert text.count(old) == 1, (old[:60], text.count(old))
    text = text.replace(old, new)


replace_once(
    'TOKEN_BEARING_STEPS = r"""\n',
    "# L1 (2026-10-03 review): every step before the mint, verbatim from the reviewed helper bytes.\n"
    'PRE_TOKEN_STEPS = r"""\n' + pre_yaml + '"""\n'
    "TOP_LEVEL_KEYS = ['name', True, 'permissions', 'concurrency', 'jobs']\n"
    "JOB_KEYS = ['if', 'runs-on', 'timeout-minutes', 'environment', 'permissions', 'env', 'steps']\n"
    "STEP_ESCAPES = ('if', 'continue-on-error', 'timeout-minutes', 'shell')\n\n"
    'TOKEN_BEARING_STEPS = r"""\n',
)
replace_once(
    "    def test_target_changes_exactly_the_twelve_pinned_paths(self) -> None:\n",
    "    def test_target_changes_exactly_the_five_pinned_paths(self) -> None:\n",
)
replace_once(
    '\n\nif __name__ == "__main__":\n',
    "\n\n"
    "    def test_pre_token_steps_are_the_reviewed_documents(self) -> None:\n"
    "        # L1: the gates before the mint are compared whole as well - not only their `run` text - so an\n"
    "        # `if: false`, a `continue-on-error`, or a changed `with:` cannot slip past GATE_BODIES.\n"
    "        mint = self.names.index(STEP_MINT)\n"
    "        self.assertEqual(yaml.safe_load(PRE_TOKEN_STEPS), self.steps[:mint])\n"
    "\n"
    "    def test_document_and_job_shape_is_exact(self) -> None:\n"
    "        # L1: no `defaults` (a workflow- or job-level shell would bypass the strict-mode check of every\n"
    "        # run block) and no step-level escape hatch anywhere, including the token-bearing steps.\n"
    "        self.assertEqual(TOP_LEVEL_KEYS, list(self.document))\n"
    "        self.assertEqual(JOB_KEYS, list(self.job))\n"
    "        for step in self.steps:\n"
    "            for escape in STEP_ESCAPES:\n"
    "                self.assertNotIn(escape, step, step.get(\"name\"))\n"
    '\n\nif __name__ == "__main__":\n',
)
compile(text, "contract", "exec")
io.open(CONTRACT, "w", encoding="utf-8", newline="\n").write(text)
print(f"strengthened {CONTRACT.name}: {len(text.splitlines())} lines, pre-token steps {mint}")
