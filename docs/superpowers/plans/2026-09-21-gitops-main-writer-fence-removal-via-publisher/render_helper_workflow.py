#!/usr/bin/env python3
"""Render the fence-removal publisher from the executed 2026-09-20 publisher by exact, counted substitution."""

from __future__ import annotations

import io
import sys
from pathlib import Path

source, destination = Path(sys.argv[1]), Path(sys.argv[2])
text = io.open(source, encoding="utf-8").read()
assert "\r" not in text

TAB = chr(92) + "t"  # the two characters backslash + t, for bash $'M\t...' quoting
PLATFORM = "apps/devpath-platform-svc/base/kustomization.yaml"
SANDBOX = "apps/devpath-sandbox-svc/base/kustomization.yaml"
MIGRATION = "apps/devpath-migration/base/kustomization.yaml"


def replace(old: str, new: str, count: int = 1) -> None:
    global text
    assert text.count(old) == count, (old[:60], text.count(old), count)
    text = text.replace(old, new)


replace("name: S2a mobile-free release contract main publisher", "name: r2 writer fence removal main publisher")
replace(
    "description: Publish the exact tested S2a mobile-free release contract to main",
    "description: Publish the exact tested r2 writer fence removal to main",
)
replace("group: s2a-mobile-free-contract-main-publish", "group: r2-writer-fence-removal-main-publish")
replace(
    "chore/s2a-mobile-free-contract-publish-20260920", "chore/r2-writer-fence-removal-publish-20260921", 2
)
replace("fix/s2a-mobile-free-contract-main-20260920", "fix/r2-writer-fence-removal-main-20260921")
replace(
    "      MAIN_SHA: 4f3ed64b2a148394eb0b8b3f5311e327f0edd759\n"
    "      TARGET_SHA: 69e7bd15570f5ba0f271c83b5bd46955cb249c8e\n"
    "      TARGET_TREE: 7799cc07f3083a002d0e2064db5437e2cde46f84\n"
    "      HELPER_BASE_SHA: 4f3ed64b2a148394eb0b8b3f5311e327f0edd759\n",
    "      MAIN_SHA: c1d5e8cf197c7dbcb0d5f224011b82b73412e17a\n"
    "      FENCE_BASE_SHA: 69e7bd15570f5ba0f271c83b5bd46955cb249c8e\n"
    "      TARGET_SHA: fcf97cf686df8e8bad56597d4679f9a96fd597fc\n"
    "      TARGET_TREE: a1c43f95c1332611e0f32066b51aa25090e98b5a\n"
    "      HELPER_BASE_SHA: c1d5e8cf197c7dbcb0d5f224011b82b73412e17a\n",
)
replace("tests/release/test_s2a_main_publish.py", "tests/release/test_r2_unfence_main_publish.py")
replace("-p 'test_s2a_main_publish.py'", "-p 'test_r2_unfence_main_publish.py'")
replace(
    "      - name: Checkout the exact tested S2a target\n"
    "        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0\n"
    "        with:\n"
    "          ref: ${{ env.TARGET_SHA }}\n"
    "          fetch-depth: 2\n",
    "      - name: Checkout the exact tested fence-removal target\n"
    "        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0\n"
    "        with:\n"
    "          ref: ${{ env.TARGET_SHA }}\n"
    "          fetch-depth: 3\n",
)
replace("      - name: Test the exact S2a target\n", "      - name: Test the exact fence-removal target\n")
replace(
    '          test "$(git rev-list --parents -n 1 HEAD)" = "$TARGET_SHA $MAIN_SHA"\n',
    '          test "$(git rev-list --parents -n 1 HEAD)" = "$TARGET_SHA $MAIN_SHA"\n'
    '          test "$(git rev-list --parents -n 1 HEAD^)" = "$MAIN_SHA $FENCE_BASE_SHA"\n',
)
replace(
    "            'release: promote the mobile-free release contract and the pinned ET13 catalog to main'\n",
    "            'release: remove the abandoned ms-20260920-community-flat-pages-r2 writer fence from main'\n",
)
replace(
    '          target_listing="$(git diff-tree --no-commit-id --name-only -r HEAD)"\n'
    '          test -n "$target_listing"\n'
    '          mapfile -t target_paths <<<"$target_listing"\n'
    '          test "${#target_paths[@]}" -gt 0\n'
    '          for target_path in "${target_paths[@]}"; do\n'
    '            case "$target_path" in\n'
    "              release-manifests/*|scripts/release/*|tests/release/*) ;;\n"
    '              *) echo "unexpected target path: $target_path" >&2; exit 1 ;;\n'
    "            esac\n"
    "          done\n",
    '          target_listing="$(git diff-tree --no-commit-id --name-status -r HEAD)"\n'
    '          test -n "$target_listing"\n'
    '          mapfile -t target_rows <<<"$target_listing"\n'
    '          test "${#target_rows[@]}" -eq 2\n'
    f"          test \"${{target_rows[0]}}\" = $'M{TAB}{PLATFORM}'\n"
    f"          test \"${{target_rows[1]}}\" = $'M{TAB}{SANDBOX}'\n"
    f"          for writer_path in {PLATFORM} {SANDBOX}; do\n"
    '            target_blob="$(git rev-parse "HEAD:$writer_path")"\n'
    '            base_blob="$(git rev-parse "$FENCE_BASE_SHA:$writer_path")"\n'
    '            test -n "$target_blob"\n'
    '            test -n "$base_blob"\n'
    '            test "$target_blob" = "$base_blob"\n'
    "            if grep -q '^replicas' \"$writer_path\"; then\n"
    '              echo "writer fence is still present: $writer_path" >&2\n'
    "              exit 1\n"
    "            fi\n"
    "          done\n"
    f'          migration_target="$(git rev-parse "HEAD:{MIGRATION}")"\n'
    f'          migration_main="$(git rev-parse "$MAIN_SHA:{MIGRATION}")"\n'
    '          test -n "$migration_target"\n'
    '          test "$migration_target" = "$migration_main"\n',
)
replace(
    "      - name: Fast-forward protected main to the exact tested S2a target\n",
    "      - name: Fast-forward protected main to the exact tested fence-removal target\n",
)

for stale in ("S2a", "s2a", "4f3ed64b", "7799cc07", "publish-20260920", "main-20260920"):
    assert stale not in text, stale
io.open(destination, "w", encoding="utf-8", newline="\n").write(text)
print("rendered", destination.name, len(text.splitlines()), "lines")
