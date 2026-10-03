#!/usr/bin/env python3
"""Render the operator transaction and its unit tests from the executed 2026-09-21 ones by counted substitution.

Usage: render_run_script.py <documents clone> <revision> <destination dir>
The precedent is read as committed bytes (`git show`), never from a checkout: a Windows checkout materialises CRLF.
Only the pinned coordinates, branch names, the docstring headline and the module name change.
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

documents, revision, destination = sys.argv[1], sys.argv[2], Path(sys.argv[3])
PRECEDENT = "docs/superpowers/plans/2026-09-21-gitops-main-writer-fence-removal-via-publisher"


def render(source: str, target: Path, substitutions: list[tuple[str, str, int]], stale: tuple[str, ...]) -> None:
    shown = subprocess.run(
        ["git", "-C", documents, "show", f"{revision}:{PRECEDENT}/{source}"], capture_output=True, check=True
    )
    text = shown.stdout.decode("utf-8")
    assert "\r" not in text, source
    for old, new, count in substitutions:
        assert text.count(old) == count, (source, old[:60], text.count(old), count)
        text = text.replace(old, new)
    for fragment in stale:
        assert fragment not in text, (source, fragment)
    compile(text, str(target), "exec")
    io.open(target, "w", encoding="utf-8", newline="\n").write(text)
    print("rendered", target.name, len(text.splitlines()), "lines")


STALE = ("r2", "unfence", "fence", "c1d5e8cf", "69e7bd15", "fcf97cf6", "a1c43f95")
render(
    "run_r2_unfence_main_publish.py",
    destination / "run_pipeline_defects_main_publish.py",
    [
        (
            "Operator transaction for the one-shot r2 writer-fence-removal main publisher.",
            "Operator transaction for the one-shot pipeline-defects main publisher.",
            1,
        ),
        ('MAIN_SHA = "c1d5e8cf197c7dbcb0d5f224011b82b73412e17a"', 'MAIN_SHA = "30c0e9f717efaad9bd46d47721a61495f4093e96"', 1),
        ('TARGET_SHA = "fcf97cf686df8e8bad56597d4679f9a96fd597fc"', 'TARGET_SHA = "5961922b9a309055a75bc7302e5c852c5c51d59c"', 1),
        ('TARGET_TREE = "a1c43f95c1332611e0f32066b51aa25090e98b5a"', 'TARGET_TREE = "85d71a7f6734d781df3ea0f287ae8569a1b801e4"', 1),
        ('HELPER_BRANCH = "chore/r2-writer-fence-removal-publish-20260921"', 'HELPER_BRANCH = "chore/pipeline-defects-publish-20260921"', 1),
        ('TARGET_BRANCH = "fix/r2-writer-fence-removal-main-20260921"', 'TARGET_BRANCH = "fix/pipeline-defects-main-20260921"', 1),
        (
            'STAGED_BRANCH = "chore/r2-unfence-publish-dispatcher-staged-20260921"',
            'STAGED_BRANCH = "chore/pipeline-defects-publish-dispatcher-staged-20260921"',
            1,
        ),
        (
            'DISPATCH_BRANCH = "automation/dispatch-r2-unfence-main-publish"',
            'DISPATCH_BRANCH = "automation/dispatch-pipeline-defects-main-publish"',
            1,
        ),
    ],
    STALE,
)
render(
    "test_run_r2_unfence_main_publish.py",
    destination / "test_run_pipeline_defects_main_publish.py",
    [("run_r2_unfence_main_publish", "run_pipeline_defects_main_publish", 2)],
    STALE,
)
