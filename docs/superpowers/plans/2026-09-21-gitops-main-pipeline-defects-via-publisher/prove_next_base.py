#!/usr/bin/env python3
"""Prove with the real gate code that the pipeline-defects target is an acceptable sealed base for the next release.

Usage: prove_next_base.py <gitops repo> <target checkout> <shared main scripts dir> <candidate spec> <target sha>

Runs the base checks the promotion chain applies at `base` (with the target's own verifier), the renders the
shared migration gate applies to a base, and - because this target adds `imagePullSecrets` to the fence
ServiceAccount that is rendered next to the migration Job - the exact render path of shared's
mission-spine-migration-release.yml: rewrite the migration kustomization with `set-migration-release`, build the
base with kustomize, then `validate-migration-render`. (That workflow pins kustomize v5.4.3; this proof uses the
kustomize embedded in the local kubectl.) Controls: the fenced r2 commit M must be refused as a base, and a
tampered render must be refused by the render validation.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

repo, target_checkout, shared_scripts, spec_path, target = sys.argv[1:6]
M = "c1d5e8cf197c7dbcb0d5f224011b82b73412e17a"  # abandoned r2 migration commit: writers fenced to replicas 0
NEXT_MANIFEST_SHA = "f" * 64  # any release manifest hash other than the completed release's


def load(name: str, path: Path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def blob(commit: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", repo, "show", f"{commit}:{path}"], capture_output=True, check=True).stdout


checkout = Path(target_checkout)
head = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"], capture_output=True, check=True)
assert head.stdout.decode().strip() == target, "the target checkout is not at the target commit"
chain = load("verify_promotion_chain", checkout / "scripts" / "release" / "verify_promotion_chain.py")
gate = load("migration_release_gate", Path(shared_scripts) / "migration_release_gate.py")
candidate = json.loads(Path(spec_path).read_text(encoding="utf-8"))
root = Path(repo)
results = []


def check(label: str, subject: str, fn, expect_ok: bool) -> None:
    try:
        fn(subject)
        ok, detail = True, "accepted"
    except Exception as exc:  # the gates raise ValueError / GateError
        ok, detail = False, f"refused: {exc}"
    verdict = "PASS" if ok == expect_ok else "FAIL"
    results.append(verdict)
    print(f"[{verdict}] {label} @ {subject[:8]} -> {detail}")


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


MAIN_SHA = "30c0e9f717efaad9bd46d47721a61495f4093e96"
JOB_PATH = "apps/devpath-migration/base/job.yaml"
assert blob(target, JOB_PATH) == blob(MAIN_SHA, JOB_PATH), "the base migration Job must stay byte-identical"
DIGEST = candidate["shared_migration"]["image_digest"]


def next_release_render() -> bytes:
    with tempfile.TemporaryDirectory(prefix="next-base-render-") as scratch:
        base = Path(scratch) / "base"
        shutil.copytree(checkout / "apps" / "devpath-migration" / "base", base)
        rewritten = gate.render_migration_kustomization(
            blob(target, "apps/devpath-migration/base/kustomization.yaml"), DIGEST, NEXT_MANIFEST_SHA
        )
        (base / "kustomization.yaml").write_bytes(rewritten)
        done = subprocess.run(["kubectl", "kustomize", str(base)], capture_output=True, check=True)
    return done.stdout.replace(b"\r\n", b"\n")


RENDER = next_release_render()
assert b"imagePullSecrets:\n- name: ghcr-pull\n" in RENDER, "the render does not carry the declared pull secret"


def gate_next_render(_: str) -> None:
    gate.validate_migration_render(RENDER, DIGEST, NEXT_MANIFEST_SHA)


def gate_tampered_render(_: str) -> None:
    gate.validate_migration_render(RENDER.replace(b"suspend: false", b"suspend: true"), DIGEST, NEXT_MANIFEST_SHA)


check("chain base conditions", target, chain_base, True)
check("shared gate: writer fence render", target, gate_fence, True)
check("shared gate: next migration render", target, gate_migration, True)
check("shared gate: built next-release render incl. the fence ServiceAccount", target, gate_next_render, True)
print("-- controls: the fenced M must be refused as a base; a still-suspended release Job must be refused")
check("chain base conditions", M, chain_base, False)
check("shared gate: writer fence render", M, gate_fence, False)
check("shared gate: tampered next-release render", target, gate_tampered_render, False)
raise SystemExit(0 if all(v == "PASS" for v in results) else 1)
