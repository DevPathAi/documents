#!/usr/bin/env python3
"""Render the pipeline-defects publisher from the executed 2026-09-21 fence-removal publisher by exact, counted substitution.

Usage: render_helper_workflow.py <9/21 helper workflow> <destination>
Source bytes: git show origin/chore/r2-writer-fence-removal-publish-20260921:.github/workflows/mission-spine-auth-smoke.yml
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

source, destination = Path(sys.argv[1]), Path(sys.argv[2])
text = io.open(source, encoding="utf-8", newline="").read()
assert "\r" not in text

TAB = chr(92) + "t"  # the two characters backslash + t, for bash $'M\t...' quoting
CONT = " " + chr(92)  # a shell line continuation
TARGET_ROWS = (
    ("M", "apps/devpath-ai-svc/base/deployment.yaml"),
    ("M", "apps/devpath-community-svc/base/deployment.yaml"),
    ("M", "apps/devpath-gateway/base/deployment.yaml"),
    ("M", "apps/devpath-lcs-svc/base/deployment.yaml"),
    ("M", "apps/devpath-learning-svc/base/deployment.yaml"),
    ("M", "apps/devpath-migration/base/writer-fence-rbac.yaml"),
    ("M", "apps/devpath-notification-svc/base/deployment.yaml"),
    ("M", "apps/devpath-platform-svc/base/deployment.yaml"),
    ("M", "apps/devpath-sandbox-svc/base/deployment.yaml"),
    ("M", "scripts/release/cloudflare_pages.py"),
    ("M", "tests/release/test_cloudflare_api.py"),
    ("A", "tests/release/test_production_startup_budget.py"),
)
SUBJECT = "release: add the production startup budget, the fence pull secret, and the landing API smoke to main"


def replace(old: str, new: str, count: int = 1) -> None:
    global text
    assert text.count(old) == count, (old[:60], text.count(old), count)
    text = text.replace(old, new)


replace("name: r2 writer fence removal main publisher", "name: pipeline defects main publisher")
replace(
    "description: Publish the exact tested r2 writer fence removal to main",
    "description: Publish the exact tested pipeline defect fixes to main",
)
replace("group: r2-writer-fence-removal-main-publish", "group: pipeline-defects-main-publish")
replace("chore/r2-writer-fence-removal-publish-20260921", "chore/pipeline-defects-publish-20260921", 2)
replace("fix/r2-writer-fence-removal-main-20260921", "fix/pipeline-defects-main-20260921")
replace(
    "      MAIN_SHA: c1d5e8cf197c7dbcb0d5f224011b82b73412e17a\n"
    "      FENCE_BASE_SHA: 69e7bd15570f5ba0f271c83b5bd46955cb249c8e\n"
    "      TARGET_SHA: fcf97cf686df8e8bad56597d4679f9a96fd597fc\n"
    "      TARGET_TREE: a1c43f95c1332611e0f32066b51aa25090e98b5a\n"
    "      HELPER_BASE_SHA: c1d5e8cf197c7dbcb0d5f224011b82b73412e17a\n",
    "      MAIN_SHA: 30c0e9f717efaad9bd46d47721a61495f4093e96\n"
    "      TARGET_SHA: 5961922b9a309055a75bc7302e5c852c5c51d59c\n"
    "      TARGET_TREE: 85d71a7f6734d781df3ea0f287ae8569a1b801e4\n"
    "      HELPER_BASE_SHA: 30c0e9f717efaad9bd46d47721a61495f4093e96\n",
)
replace("tests/release/test_r2_unfence_main_publish.py", "tests/release/test_pipeline_defects_main_publish.py")
replace("-p 'test_r2_unfence_main_publish.py'", "-p 'test_pipeline_defects_main_publish.py'")
replace(
    "      - name: Checkout the exact tested fence-removal target\n"
    "        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0\n"
    "        with:\n"
    "          ref: ${{ env.TARGET_SHA }}\n"
    "          fetch-depth: 3\n",
    "      - name: Checkout the exact tested pipeline-defects target\n"
    "        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0\n"
    "        with:\n"
    "          ref: ${{ env.TARGET_SHA }}\n"
    "          fetch-depth: 2\n",
)
replace("      - name: Test the exact fence-removal target\n", "      - name: Test the exact pipeline-defects target\n")
replace(
    '          test "$(git rev-list --parents -n 1 HEAD)" = "$TARGET_SHA $MAIN_SHA"\n'
    '          test "$(git rev-list --parents -n 1 HEAD^)" = "$MAIN_SHA $FENCE_BASE_SHA"\n',
    '          test "$(git rev-list --parents -n 1 HEAD)" = "$TARGET_SHA $MAIN_SHA"\n',
)
replace(
    "            'release: remove the abandoned ms-20260920-community-flat-pages-r2 writer fence from main'\n",
    f"            '{SUBJECT}'\n",
)

listing_rows = "".join(
    f"            $'{status}{TAB}{path}'" + (CONT if index < len(TARGET_ROWS) - 1 else ')"') + "\n"
    for index, (status, path) in enumerate(TARGET_ROWS)
)
old_start = '          target_listing="$(git diff-tree --no-commit-id --name-status -r HEAD)"\n'
old_end = '          test "$migration_target" = "$migration_main"\n'
assert text.count(old_start) == 1 and text.count(old_end) == 1
begin, finish = text.index(old_start), text.index(old_end) + len(old_end)
assert begin < finish and text[begin:finish].count("\n") == 21, text[begin:finish].count("\n")
text = (
    text[:begin]
    + old_start
    + '          test -n "$target_listing"\n'
    + "          expected_listing=\"$(printf '%s" + chr(92) + "n'" + CONT + "\n"
    + listing_rows
    + '          test -n "$expected_listing"\n'
    + '          test "$target_listing" = "$expected_listing"\n'
    + '          mapfile -t target_rows <<<"$target_listing"\n'
    + f'          test "${{#target_rows[@]}}" -eq {len(TARGET_ROWS)}\n'
    + text[finish:]
)
replace(
    "      - name: Fast-forward protected main to the exact tested fence-removal target\n",
    "      - name: Fast-forward protected main to the exact tested pipeline-defects target\n",
)

for stale in ("r2", "unfence", "fence-removal", "FENCE_BASE", "writer_path", "c1d5e8cf", "69e7bd15", "fcf97cf6", "a1c43f95"):
    assert stale not in text, stale
io.open(destination, "w", encoding="utf-8", newline="\n").write(text)
print("rendered", destination.name, len(text.splitlines()), "lines")
