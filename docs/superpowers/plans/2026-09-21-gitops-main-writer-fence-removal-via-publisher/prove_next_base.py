#!/usr/bin/env python3
"""Prove with the real gate code that the fence-removal target is an acceptable sealed base for the next release.

Usage: prove_next_base.py <gitops repo> <gitops main scripts dir> <shared main scripts dir> <candidate spec> <target sha>
Runs the same base checks the promotion chain applies at `base`, and the same renders the shared migration
gate applies to the base. As controls it runs them on M (must be refused: fence present).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

repo, gitops_scripts, shared_scripts, spec_path, target = sys.argv[1:6]
M = "c1d5e8cf197c7dbcb0d5f224011b82b73412e17a"
NEXT_MANIFEST_SHA = "f" * 64  # any release manifest hash other than r2's


def load(name: str, path: Path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def blob(commit: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", repo, "show", f"{commit}:{path}"], capture_output=True, check=True).stdout


chain = load("verify_promotion_chain", Path(gitops_scripts) / "verify_promotion_chain.py")
gate = load("migration_release_gate", Path(shared_scripts) / "migration_release_gate.py")
candidate = json.loads(Path(spec_path).read_text(encoding="utf-8"))
root = Path(repo)
results = []


def check(label: str, commit: str, fn, expect_ok: bool) -> None:
    try:
        fn(commit)
        ok, detail = True, "accepted"
    except Exception as exc:  # the gates raise ValueError / GateError
        ok, detail = False, f"refused: {exc}"
    verdict = "PASS" if ok == expect_ok else "FAIL"
    results.append(verdict)
    print(f"[{verdict}] {label} @ {commit[:8]} -> {detail}")


def chain_base(commit: str) -> None:
    chain._require_inert_migration_base(root, commit)
    chain._require_migration_base_selector(root, commit)
    chain._require_service_base_selectors(root, commit, candidate)


def gate_fence(commit: str) -> None:
    for service, path in (
        ("devpath-platform-svc", "apps/devpath-platform-svc/base/kustomization.yaml"),
        ("devpath-sandbox-svc", "apps/devpath-sandbox-svc/base/kustomization.yaml"),
    ):
        gate.render_writer_fence_kustomization(blob(commit, path), service)


def gate_migration(commit: str) -> None:
    digest = candidate["shared_migration"]["image_digest"]
    gate.render_migration_kustomization(
        blob(commit, "apps/devpath-migration/base/kustomization.yaml"), digest, NEXT_MANIFEST_SHA
    )


check("chain base conditions", target, chain_base, True)
check("shared gate: writer fence render", target, gate_fence, True)
check("shared gate: next migration render", target, gate_migration, True)
print("-- controls: the fenced M must be refused as a base")
check("chain base conditions", M, chain_base, False)
check("shared gate: writer fence render", M, gate_fence, False)
raise SystemExit(0 if all(v == "PASS" for v in results) else 1)
