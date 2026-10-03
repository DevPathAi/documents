#!/usr/bin/env python3
"""Prove with the real gate code that the AI-fallback-probe target is an acceptable sealed base for the next release.

Usage: prove_next_base.py <gitops repo> <target checkout> <candidate spec> <target sha>

The chain's `base` branch (verify_promotion_chain.py inspect_chain walk, `commit == base`) applies FOUR checks:
_require_inert_migration_base, _require_migration_base_selector, _require_service_base_selectors and
_require_web(..., "base"). This proof runs the first three (with the target's own verifier) against the target,
the current main (control: the landed mission-on commit must also pass) and the abandoned fenced r2 migration
commit M (control: must be refused - only the service-selector check refuses it, so it proves the writer-fence
branch). _require_web(base) is NOT run: it binds the web kustomization to the NEXT candidate's base_web_digest,
which does not exist yet (with this release's spec it would refuse the promoted 902f1ae1 by design). It is safe to
omit because the web kustomization is asserted byte-identical to main below. The target touches no migration,
fence or kustomization path, so the shared migration renders of the 2026-09-21 proof are not needed either.
Not covered here (review M3): the next candidate's ai_release_eval_config.rendered_config_sha256 renders
apps/devpath-ai-svc/base, which this target changes - the candidate builder must recompute it.
Structure: 2026-09-21 prove_next_base.py, reduced the way the 2026-09-24 gateway-edge-CORS proof was.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

repo, target_checkout, spec_path, target = sys.argv[1:5]
MAIN_SHA = "cea3610ab29567b5bf46a2ba2a56bc5a58cac594"
M = "c1d5e8cf197c7dbcb0d5f224011b82b73412e17a"  # abandoned r2 migration commit: writers fenced to replicas 0
UNCHANGED = (
    "apps/devpath-migration/base/job.yaml",
    "apps/devpath-migration/base/kustomization.yaml",
    "apps/devpath-migration/base/writer-fence-rbac.yaml",
    "apps/devpath-ai-svc/base/kustomization.yaml",
    "apps/devpath-admin/base/kustomization.yaml",
    "apps/devpath-web/base/kustomization.yaml",
    "apps/devpath-ollama-gpu/base/kustomization.yaml",
)


def blob(commit: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", repo, "show", f"{commit}:{path}"], capture_output=True, check=True).stdout


checkout = Path(target_checkout)
head = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"], capture_output=True, check=True)
assert head.stdout.decode().strip() == target, "the target checkout is not at the target commit"
for path in UNCHANGED:
    assert blob(target, path) == blob(MAIN_SHA, path), f"{path} must stay byte-identical to main"

sys.path.insert(0, str(checkout / "scripts" / "release"))
module_spec = importlib.util.spec_from_file_location(
    "verify_promotion_chain", checkout / "scripts" / "release" / "verify_promotion_chain.py"
)
chain = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(chain)
candidate = json.loads(Path(spec_path).read_text(encoding="utf-8"))
root = Path(repo)
results = []


def check(label: str, subject: str, expect_ok: bool) -> None:
    try:
        chain._require_inert_migration_base(root, subject)
        chain._require_migration_base_selector(root, subject)
        chain._require_service_base_selectors(root, subject, candidate)
        ok, detail = True, "accepted"
    except Exception as exc:  # the gates raise ValueError
        ok, detail = False, f"refused: {exc}"
    verdict = "PASS" if ok == expect_ok else "FAIL"
    results.append(verdict)
    print(f"[{verdict}] {label} @ {subject[:8]} -> {detail}")


check("chain base conditions (target)", target, True)
print("-- controls: the landed mission-on main must pass; the fenced r2 commit M must be refused")
check("chain base conditions (current main)", MAIN_SHA, True)
check("chain base conditions (fenced M)", M, False)
raise SystemExit(0 if all(v == "PASS" for v in results) else 1)
