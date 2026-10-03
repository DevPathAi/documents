"""Implement the service applied-revision fix in the gitops fix worktree (GREEN)."""
import pathlib

ROOT = pathlib.Path("D:/workspace/dpa/.worktrees/gitops-fix-applied-revision-20260924")


def patch(rel, pairs):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert s.count(old) == 1, (rel, old[:70], s.count(old))
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8", newline="\n")
    print("patched", rel)


# --- scripts/release/wait_release_rollouts.py -----------------------------------------------------------
patch("scripts/release/wait_release_rollouts.py", [
    (
        'MIGRATION_APPLICATION_PATH = "apps/devpath-migration/base"\n',
        'MIGRATION_APPLICATION_PATH = "apps/devpath-migration/base"\n'
        '# Argo syncs an application on any rendered change beneath its base directory (2026-09-23: a\n'
        '# startupProbe landed in deployment.yaml without touching kustomization.yaml), so the service\n'
        '# applied revision must follow the base directory rather than the digest file alone.\n'
        'SERVICE_BASE_PATHS = {name: f"apps/{name}/base" for name in SERVICE_NAMES}\n',
    ),
    (
        "        MIGRATION_PATH,\n        MIGRATION_APPLICATION_PATH,\n        *SERVICE_PATHS.values(),\n    }:",
        "        MIGRATION_PATH,\n        MIGRATION_APPLICATION_PATH,\n        *SERVICE_PATHS.values(),\n        *SERVICE_BASE_PATHS.values(),\n    }:",
    ),
    (
        "def _registry() -> RegistryClient:\n",
        "def _service_applied_revisions(root: Path, observed_commit: str) -> dict[str, str]:\n"
        "    return {\n"
        "        name: _last_path_change(root, observed_commit, SERVICE_BASE_PATHS[name])\n"
        "        for name in SERVICE_NAMES\n"
        "    }\n"
        "\n"
        "\n"
        "def _registry() -> RegistryClient:\n",
    ),
    (
        "    applied_revisions = {\n"
        "        name: _last_path_change(root, observed_commit, SERVICE_PATHS[name])\n"
        "        for name in SERVICE_NAMES\n"
        "    }\n",
        "    applied_revisions = _service_applied_revisions(root, observed_commit)\n",
    ),
])

# --- scripts/release/verify_promotion_chain.py ----------------------------------------------------------
patch("scripts/release/verify_promotion_chain.py", [
    (
        'SERVICE_SOURCE_STATUS_FIX_PATHS = MIGRATION_RUNTIME_ADMISSION_FIX_PATHS\n',
        'SERVICE_SOURCE_STATUS_FIX_PATHS = MIGRATION_RUNTIME_ADMISSION_FIX_PATHS\n'
        'SERVICE_APPLIED_REVISION_FIX_SUBJECT = (\n'
        '    "fix(release): bind service applied revision to the app base"\n'
        ')\n'
        'SERVICE_APPLIED_REVISION_FIX_PATHS = (\n'
        '    "scripts/release/verify_promotion_chain.py",\n'
        '    "scripts/release/wait_release_rollouts.py",\n'
        '    "tests/release/test_kubernetes_release_runtime.py",\n'
        '    "tests/release/test_promotion_chain.py",\n'
        ')\n',
    ),
    (
        '                "service_source_status_fix_commit": "",\n                "canary_runtime_form_fix_commit": "",\n',
        '                "service_source_status_fix_commit": "",\n                "service_applied_revision_fix_commit": "",\n                "canary_runtime_form_fix_commit": "",\n',
    ),
    (
        '            return {\n'
        '                **prior,\n'
        '                "current_commit": commit,\n'
        '                "service_source_status_fix_commit": commit,\n'
        '            }\n'
        '        if subject == CANARY_RUNTIME_FORM_FIX_SUBJECT:\n',
        '            return {\n'
        '                **prior,\n'
        '                "current_commit": commit,\n'
        '                "service_source_status_fix_commit": commit,\n'
        '            }\n'
        '        if subject == SERVICE_APPLIED_REVISION_FIX_SUBJECT:\n'
        '            _require_write_actor(root, commit)\n'
        '            if (\n'
        '                prior["phase"] != "services"\n'
        '                or not prior["services_commit"]\n'
        '                or parent != prior["current_commit"]\n'
        '                or prior["service_applied_revision_fix_commit"]\n'
        '            ):\n'
        '                raise ValueError(\n'
        '                    "service applied revision fix must directly follow services"\n'
        '                )\n'
        '            _require_delta(root, commit, SERVICE_APPLIED_REVISION_FIX_PATHS)\n'
        '            _require_migration(root, commit, candidate, release_manifest_sha256)\n'
        '            _require_services(root, commit, candidate)\n'
        '            _require_web(root, commit, candidate, candidate_spec_sha256, "base")\n'
        '            return {\n'
        '                **prior,\n'
        '                "current_commit": commit,\n'
        '                "service_applied_revision_fix_commit": commit,\n'
        '            }\n'
        '        if subject == CANARY_RUNTIME_FORM_FIX_SUBJECT:\n',
    ),
])
print("implementation applied")
