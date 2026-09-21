#!/usr/bin/env python3
"""Render the pipeline-defects publisher contract test from the executed 2026-09-21 contract test by counted substitution.

Usage: render_contract_test.py <9/21 contract test> <destination>
Source bytes: git show origin/chore/r2-writer-fence-removal-publish-20260921:tests/release/test_r2_unfence_main_publish.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

source, destination = Path(sys.argv[1]), Path(sys.argv[2])
text = io.open(source, encoding="utf-8", newline="").read()
assert "\r" not in text

BS = chr(92)


def replace(old: str, new: str, count: int = 1) -> None:
    global text
    assert text.count(old) == count, (old[:60], text.count(old), count)
    text = text.replace(old, new)


def replace_span(start: str, end: str, new: str) -> None:
    global text
    assert text.count(start) == 1 and text.count(end) == 1, (start[:40], end[:40])
    begin, finish = text.index(start), text.index(end)
    assert begin < finish
    text = text[:begin] + new + text[finish:]


replace(
    'MAIN_SHA = "c1d5e8cf197c7dbcb0d5f224011b82b73412e17a"\n'
    'FENCE_BASE_SHA = "69e7bd15570f5ba0f271c83b5bd46955cb249c8e"\n'
    'TARGET_SHA = "fcf97cf686df8e8bad56597d4679f9a96fd597fc"\n'
    'TARGET_TREE = "a1c43f95c1332611e0f32066b51aa25090e98b5a"\n'
    'HELPER_BRANCH = "chore/r2-writer-fence-removal-publish-20260921"\n'
    'TARGET_BRANCH = "fix/r2-writer-fence-removal-main-20260921"\n',
    'MAIN_SHA = "30c0e9f717efaad9bd46d47721a61495f4093e96"\n'
    'TARGET_SHA = "5961922b9a309055a75bc7302e5c852c5c51d59c"\n'
    'TARGET_TREE = "85d71a7f6734d781df3ea0f287ae8569a1b801e4"\n'
    'HELPER_BRANCH = "chore/pipeline-defects-publish-20260921"\n'
    'TARGET_BRANCH = "fix/pipeline-defects-main-20260921"\n',
)
replace('CONTRACT_TEST = "test_r2_unfence_main_publish.py"\n', 'CONTRACT_TEST = "test_pipeline_defects_main_publish.py"\n')
replace(
    'PLATFORM_PATH = "apps/devpath-platform-svc/base/kustomization.yaml"\n'
    'SANDBOX_PATH = "apps/devpath-sandbox-svc/base/kustomization.yaml"\n'
    'MIGRATION_PATH = "apps/devpath-migration/base/kustomization.yaml"\n'
    'SUBJECT = "release: remove the abandoned ms-20260920-community-flat-pages-r2 writer fence from main"\n',
    "TARGET_ROWS = (\n"
    '    ("M", "apps/devpath-ai-svc/base/deployment.yaml"),\n'
    '    ("M", "apps/devpath-community-svc/base/deployment.yaml"),\n'
    '    ("M", "apps/devpath-gateway/base/deployment.yaml"),\n'
    '    ("M", "apps/devpath-lcs-svc/base/deployment.yaml"),\n'
    '    ("M", "apps/devpath-learning-svc/base/deployment.yaml"),\n'
    '    ("M", "apps/devpath-migration/base/writer-fence-rbac.yaml"),\n'
    '    ("M", "apps/devpath-notification-svc/base/deployment.yaml"),\n'
    '    ("M", "apps/devpath-platform-svc/base/deployment.yaml"),\n'
    '    ("M", "apps/devpath-sandbox-svc/base/deployment.yaml"),\n'
    '    ("M", "scripts/release/cloudflare_pages.py"),\n'
    '    ("M", "tests/release/test_cloudflare_api.py"),\n'
    '    ("A", "tests/release/test_production_startup_budget.py"),\n'
    ")\n"
    "SUBJECT = (\n"
    '    "release: add the production startup budget, the fence pull secret, "\n'
    '    "and the landing API smoke to main"\n'
    ")\n",
)
replace('STEP_TARGET_CHECKOUT = "Checkout the exact tested fence-removal target"', 'STEP_TARGET_CHECKOUT = "Checkout the exact tested pipeline-defects target"')
replace('STEP_TARGET_TEST = "Test the exact fence-removal target"', 'STEP_TARGET_TEST = "Test the exact pipeline-defects target"')
replace(
    'STEP_PUSH = "Fast-forward protected main to the exact tested fence-removal target"',
    'STEP_PUSH = "Fast-forward protected main to the exact tested pipeline-defects target"',
)
replace("class R2UnfenceMainPublishTest(unittest.TestCase):", "class PipelineDefectsMainPublishTest(unittest.TestCase):")
replace('{"group": "r2-writer-fence-removal-main-publish", "cancel-in-progress": False}', '{"group": "pipeline-defects-main-publish", "cancel-in-progress": False}')
replace('        self.assertEqual(FENCE_BASE_SHA, env["FENCE_BASE_SHA"])\n', "")
replace(
    "        self.assertEqual(3, len({MAIN_SHA, FENCE_BASE_SHA, TARGET_SHA}))\n",
    '        self.assertEqual(2, len({MAIN_SHA, TARGET_SHA}))\n        self.assertNotIn("FENCE_BASE_SHA", env)\n',
)
replace(
    '        self.assertTrue({"MAIN_SHA", "TARGET_SHA", "TARGET_TREE", "FENCE_BASE_SHA"} <= pins)\n',
    '        self.assertTrue({"MAIN_SHA", "TARGET_SHA", "TARGET_TREE", "HELPER_BASE_SHA"} <= pins)\n',
)

new_target_tests = (
    "    def test_target_changes_exactly_the_twelve_pinned_paths(self) -> None:\n"
    "        # Only the parent is needed: the target is the single child of the completed release.\n"
    '        self.assertEqual(2, self._step(STEP_TARGET_CHECKOUT)["with"]["fetch-depth"])\n'
    "        run = self._run(STEP_TARGET_TEST)\n"
    "        for fragment in (\n"
    "            'test \"$(git rev-parse HEAD)\" = \"$TARGET_SHA\"',\n"
    "            'test \"$(git rev-list --parents -n 1 HEAD)\" = \"$TARGET_SHA $MAIN_SHA\"',\n"
    "            \"test \\\"$(git rev-parse 'HEAD^{tree}')\\\" = \\\"$TARGET_TREE\\\"\",\n"
    "            SUBJECT,\n"
    "            \"test \\\"$(git show -s --format=%an HEAD)\\\" = 'devpath-gitops-release[bot]'\",\n"
    "            \"test \\\"$(git show -s --format=%cn HEAD)\\\" = 'devpath-gitops-release[bot]'\",\n"
    "            'git diff --check \"$MAIN_SHA\" \"$TARGET_SHA\"',\n"
    "            \"python -m unittest discover -s tests/release -p 'test_*.py'\",\n"
    "        ):\n"
    "            self.assertIn(fragment, run)\n"
    "        self.assertEqual(\n"
    '            2, run.count("244265210+devpath-gitops-release[bot]@users.noreply.github.com")\n'
    "        )\n"
    "\n"
    "    def test_target_listing_is_compared_whole_and_cannot_compare_empty(self) -> None:\n"
    "        run = LINE_CONTINUATION.sub(\" \", self._run(STEP_TARGET_TEST))\n"
    "        rows = \" \".join(f\"$'{status}\\\\t{path}'\" for status, path in TARGET_ROWS)\n"
    "        self.assertEqual(12, len(TARGET_ROWS))\n"
    "        self.assertEqual(sorted(path for _, path in TARGET_ROWS), [path for _, path in TARGET_ROWS])\n"
    "        expected = [\n"
    "            'target_listing=\"$(git diff-tree --no-commit-id --name-status -r HEAD)\"',\n"
    "            'test -n \"$target_listing\"',\n"
    "            f\"expected_listing=\\\"$(printf '%s\\\\n' {rows})\\\"\",\n"
    "            'test -n \"$expected_listing\"',\n"
    "            'test \"$target_listing\" = \"$expected_listing\"',\n"
    "            'mapfile -t target_rows <<<\"$target_listing\"',\n"
    "            'test \"${#target_rows[@]}\" -eq 12',\n"
    "        ]\n"
    "        # Folding a continuation leaves two spaces; the rows hold a literal backslash-t, never a tab.\n"
    "        lines = [\" \".join(line.split()) for line in run.splitlines()]\n"
    "        start = lines.index(expected[0])\n"
    "        # The seven statements are consecutive: nothing may reassign a listing between them.\n"
    "        self.assertEqual(expected, lines[start : start + len(expected)])\n"
    "        for name in (\"target_listing=\", \"expected_listing=\"):\n"
    "            self.assertEqual(1, sum(line.startswith(name) for line in lines), name)\n"
    "        # The full unit suite runs only after the listing gate.\n"
    "        self.assertLess(start + len(expected) - 1, lines.index(\"git diff --check \\\"$MAIN_SHA\\\" \\\"$TARGET_SHA\\\"\"))\n"
    "\n"
)
replace_span(
    "    def test_target_changes_exactly_the_two_writer_kustomizations(self) -> None:\n",
    "    def test_live_environment_and_approval_are_authenticated(self) -> None:\n",
    new_target_tests,
)
replace(
    "        # The r2 chain is abandoned on purpose; its verifiers would refuse this unregistered subject.\n",
    "        # This commit sits outside every release chain; the chain verifiers would refuse its unregistered subject.\n",
)

for stale in ("r2", "R2", "unfence", "Unfence", "fence-removal", "FENCE_BASE_SHA, ", "PLATFORM_PATH", "c1d5e8cf", "69e7bd15", "fcf97cf6", "a1c43f95"):
    assert stale not in text, stale
compile(text, str(destination), "exec")
io.open(destination, "w", encoding="utf-8", newline="\n").write(text)
print("rendered", destination.name, len(text.splitlines()), "lines")
