#!/usr/bin/env python3
"""Render the staged dispatcher from the executed 2026-09-21 dispatcher by exact, counted substitution.

Usage: render_dispatcher.py <9/21 dispatcher workflow> <destination>
Source bytes: git show origin/chore/r2-unfence-publish-dispatcher-staged-20260921:.github/workflows/mission-spine-release-gate-dispatch.yml
The trigger is a push of the staged commit to automation/dispatch-pipeline-defects-main-publish - do not create
that branch before the operator transaction does.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

source, destination = Path(sys.argv[1]), Path(sys.argv[2])
text = io.open(source, encoding="utf-8", newline="").read()
assert "\r" not in text


def replace(old: str, new: str, count: int = 1) -> None:
    global text
    assert text.count(old) == count, (old[:60], text.count(old), count)
    text = text.replace(old, new)


replace("r2 writer fence removal main publisher", "pipeline defects main publisher", 2)
replace("automation/dispatch-r2-unfence-main-publish", "automation/dispatch-pipeline-defects-main-publish")
replace("chore/r2-writer-fence-removal-publish-20260921", "chore/pipeline-defects-publish-20260921")
for stale in ("r2", "unfence", "fence"):
    assert stale not in text, stale
io.open(destination, "w", encoding="utf-8", newline="\n").write(text)
print("rendered", destination.name, len(text.splitlines()), "lines")
