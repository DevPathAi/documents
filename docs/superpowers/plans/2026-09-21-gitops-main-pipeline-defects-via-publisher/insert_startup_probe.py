#!/usr/bin/env python3
"""Insert the staging-proven startupProbe before readinessProbe in the eight Spring Deployments,
and declare the ghcr pull secret on the migration fence ServiceAccount. Exact, counted edits.

Usage: insert_startup_probe.py <devpath-gitops worktree>
"""

from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1])
SERVICES = (
    "devpath-ai-svc",
    "devpath-community-svc",
    "devpath-gateway",
    "devpath-lcs-svc",
    "devpath-learning-svc",
    "devpath-notification-svc",
    "devpath-platform-svc",
    "devpath-sandbox-svc",
)
ANCHOR = (
    "          readinessProbe:\n"
    "            httpGet:\n"
    "              path: /actuator/health/readiness\n"
)
PROBE = (
    "          startupProbe:\n"
    "            httpGet:\n"
    "              path: /actuator/health/liveness\n"
    "              port: 8080\n"
    "            periodSeconds: 5\n"
    "            timeoutSeconds: 3\n"
    "            failureThreshold: 60\n"
)
SA_OLD = (
    "kind: ServiceAccount\n"
    "metadata:\n"
    "  name: devpath-migration-fence\n"
    "automountServiceAccountToken: false\n"
)
SA_NEW = SA_OLD + "imagePullSecrets:\n  - name: ghcr-pull\n"


def edit(path: Path, old: str, new: str) -> None:
    # apps/** carries no eol attribute, so a Windows checkout (core.autocrlf=true) materialises
    # CRLF while the blob is LF. Edit the LF form and write back in the checkout's own style;
    # `git add` normalises to LF again and make_pipeline_defects_target.py asserts LF blobs.
    raw = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    assert "\r" not in text, path
    assert not crlf or raw.count("\r\n") == raw.count("\n"), (path, "mixed line endings")
    assert text.count(old) == 1, (path, text.count(old))
    assert "startupProbe" not in text and "imagePullSecrets" not in text, path
    edited = text.replace(old, new)
    path.write_bytes((edited.replace("\n", "\r\n") if crlf else edited).encode("utf-8"))


for service in SERVICES:
    edit(root / "apps" / service / "base" / "deployment.yaml", ANCHOR, PROBE + ANCHOR)
edit(root / "apps" / "devpath-migration" / "base" / "writer-fence-rbac.yaml", SA_OLD, SA_NEW)
print("edited", len(SERVICES) + 1, "files")
