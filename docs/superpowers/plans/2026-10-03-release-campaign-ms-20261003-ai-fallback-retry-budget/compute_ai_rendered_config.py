#!/usr/bin/env python3
"""Compute a candidate's ai_release_eval_config.rendered_config_sha256 exactly the way the release verifier checks it.

Usage: compute_ai_rendered_config.py <gitops clone> <verifier checkout> <gitops base sha> <kustomize v5.4.3 binary> [expected]

The verifier (scripts/release/verify_release_artifacts.py verify_ai_rendered_config) materializes the AI kustomize
base of the candidate's gitops.base_sha with _materialize_git_tree, renders it with the pinned kustomize v5.4.3
(`kustomize build apps/devpath-ai-svc/base`) and requires validate_ai_rendered_config_bytes(stdout, spec value):
canonical LF UTF-8, sha256 equal, and validate_ai_rendered_runtime (the frozen MENTOR_* routing).

This script imports those very functions from <verifier checkout>/scripts/release, so the only difference from
CI is the kustomize build for the local OS (the verifier pins the linux_amd64 binary bytes; locally use the same
release for this OS, checksum-verified). Prove the method first: the base of a completed release must reproduce
that release's spec value (e.g. eb413814 -> bfa0126d... for ms-20261002-ai-provider-fallback-gpu7b) - only then
trust the value for a new base.

Why this exists (review M3, 2026-10-03): the 2026-10-02 candidate builder copied this field from the previous spec.
It only matched because the AI base had not changed. Once gitops main moved the ai-svc image digest and env, the
copied value would fail closed late (ai-release-eval / promote / landing) and burn the release id.
"""
from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    repo, verifier_checkout, base_sha, kustomize = sys.argv[1:5]
    expected = sys.argv[5] if len(sys.argv) > 5 else ""
    scripts = Path(verifier_checkout) / "scripts" / "release"
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("verify_release_artifacts", scripts / "verify_release_artifacts.py")
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)

    version = subprocess.run([kustomize, "version"], capture_output=True, check=False, timeout=30)
    if version.returncode != 0 or version.stdout.strip() != verifier.KUSTOMIZE_VERSION.encode():
        raise SystemExit(f"kustomize must be {verifier.KUSTOMIZE_VERSION}, got {version.stdout!r}")
    full_sha = subprocess.run(
        ["git", "-C", repo, "rev-parse", f"{base_sha}^{{commit}}"], capture_output=True, check=True, text=True
    ).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="ai-render-") as scratch:
        source = Path(scratch) / "source"
        verifier._materialize_git_tree(Path(repo), full_sha, source)
        rendered = subprocess.run(
            [kustomize, "build", verifier.AI_RENDER_PATH], cwd=source, capture_output=True, check=False, timeout=60
        )
    if rendered.returncode != 0:
        raise SystemExit(f"kustomize build failed: {rendered.stderr.decode(errors='replace')[:400]}")
    raw = rendered.stdout
    digest = hashlib.sha256(raw).hexdigest()
    # The verifier's own byte contract: canonical LF UTF-8 + the frozen runtime routing.
    verifier.validate_ai_rendered_config_bytes(raw, digest)
    print(f"base={full_sha}")
    print(f"rendered_bytes={len(raw)}")
    print(f"rendered_config_sha256={digest}")
    if expected and digest != expected:
        raise SystemExit(f"MISMATCH: expected {expected}")
    if expected:
        print("matches expected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
