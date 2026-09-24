"""Round 2 of the service applied-revision fix: share SERVICE_BASE_PATHS and use it in the canary builder and the
promotion-evidence verifier too (both compare recorded applied revisions against a kustomization-only lookup).
Tests first, then implementation; run from anywhere."""
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


# ---------------------------------------------------------------- tests (RED) --------------------------------
patch("tests/release/test_service_promotion.py", [
    (
        '        self.assertEqual(\n'
        '            tuple(self.promoter.SERVICE_PATHS.values()),\n'
        '            tuple(f"apps/{name}/base/kustomization.yaml" for name in expected),\n'
        '        )\n',
        '        self.assertEqual(\n'
        '            tuple(self.promoter.SERVICE_PATHS.values()),\n'
        '            tuple(f"apps/{name}/base/kustomization.yaml" for name in expected),\n'
        '        )\n'
        '        # Argo syncs on any rendered change beneath the base directory; applied revisions follow it.\n'
        '        self.assertEqual(\n'
        '            tuple(self.promoter.SERVICE_BASE_PATHS.values()),\n'
        '            tuple(f"apps/{name}/base" for name in expected),\n'
        '        )\n',
    ),
])

patch("tests/release/test_promotion_evidence.py", [
    (
        '    def test_exact_full_chain_and_nine_service_payload_passes(self):\n',
        '    def test_service_applied_revision_is_derived_from_the_app_base(self):\n'
        '        calls = []\n'
        '\n'
        '        def recording_git(root, *args):\n'
        '            calls.append(args)\n'
        '            return self.commits["services_commit"]\n'
        '\n'
        '        state = {"phase": "mission-on", **self.commits}\n'
        '        raw = (json.dumps(self.payload, separators=(",", ":")) + "\\n").encode()\n'
        '        with mock.patch.object(module, "inspect_chain", return_value=state), mock.patch.object(\n'
        '            module, "_git", side_effect=recording_git\n'
        '        ):\n'
        '            module.validate_promotion_payload(\n'
        '                self.payload,\n'
        '                raw,\n'
        '                ROOT,\n'
        '                self.release_id,\n'
        '                self.candidate,\n'
        '                self.candidate_hash,\n'
        '                self.release_hash,\n'
        '                self.run,\n'
        '                "c" * 64,\n'
        '            )\n'
        '        lookups = [args for args in calls if len(args) >= 2 and args[-2] == "--"]\n'
        '        self.assertEqual(\n'
        '            sorted(args[-1] for args in lookups),\n'
        '            sorted(f"apps/{name}/base" for name in module.SERVICE_NAMES),\n'
        '        )\n'
        '        self.assertFalse(any(args[-1].endswith("kustomization.yaml") for args in lookups))\n'
        '\n'
        '    def test_exact_full_chain_and_nine_service_payload_passes(self):\n',
    ),
])

patch("tests/release/test_production_canary.py", [
    (
        '    def test_runtime_image_form_uses_canonical_oci_contract(self):\n',
        '    def test_service_applied_revision_lookup_uses_the_app_base(self):\n'
        '        # The runtime evidence records Argo\'s sync revision, which follows any rendered change beneath\n'
        '        # apps/<service>/base; the canary must derive its expectation from the same directory.\n'
        '        import inspect\n'
        '\n'
        '        source = inspect.getsource(self.canary.build_canary)\n'
        '        self.assertIn("SERVICE_BASE_PATHS[name]", source)\n'
        '        self.assertNotIn("SERVICE_PATHS[name]", source)\n'
        '        self.assertEqual(\n'
        '            tuple(self.canary.SERVICE_BASE_PATHS.values()),\n'
        '            tuple(f"apps/{name}/base" for name in self.canary.SERVICE_NAMES),\n'
        '        )\n'
        '\n'
        '    def test_runtime_image_form_uses_canonical_oci_contract(self):\n',
    ),
])

# ---------------------------------------------------------------- implementation ------------------------------
patch("scripts/release/promote_service_digests.py", [
    (
        'SERVICE_PATHS = {\n    name: f"apps/{name}/base/kustomization.yaml" for name in SERVICE_NAMES\n}\n',
        'SERVICE_PATHS = {\n    name: f"apps/{name}/base/kustomization.yaml" for name in SERVICE_NAMES\n}\n'
        '# Argo syncs an application on any rendered change beneath its base directory (2026-09-23: a\n'
        '# startupProbe landed in deployment.yaml without touching kustomization.yaml), so every applied-\n'
        '# revision expectation must follow the base directory rather than the digest file alone.\n'
        'SERVICE_BASE_PATHS = {name: f"apps/{name}/base" for name in SERVICE_NAMES}\n',
    ),
])

patch("scripts/release/wait_release_rollouts.py", [
    (
        'from promote_service_digests import SERVICE_NAMES, SERVICE_PATHS\n',
        'from promote_service_digests import SERVICE_BASE_PATHS, SERVICE_NAMES, SERVICE_PATHS\n',
    ),
    (
        'MIGRATION_APPLICATION_PATH = "apps/devpath-migration/base"\n'
        '# Argo syncs an application on any rendered change beneath its base directory (2026-09-23: a\n'
        '# startupProbe landed in deployment.yaml without touching kustomization.yaml), so the service\n'
        '# applied revision must follow the base directory rather than the digest file alone.\n'
        'SERVICE_BASE_PATHS = {name: f"apps/{name}/base" for name in SERVICE_NAMES}\n',
        'MIGRATION_APPLICATION_PATH = "apps/devpath-migration/base"\n',
    ),
])

patch("scripts/release/build_production_canary.py", [
    (
        'from promote_service_digests import SERVICE_NAMES, SERVICE_PATHS\n',
        'from promote_service_digests import SERVICE_BASE_PATHS, SERVICE_NAMES\n',
    ),
    (
        '            on_commit,\n            "--",\n            SERVICE_PATHS[name],\n        )\n        for name in SERVICE_NAMES\n    }\n    if any(SHA40.fullmatch(value) is None for value in applied_revisions.values()):\n        raise ValueError("production canary service applied revision is invalid")\n',
        '            on_commit,\n            "--",\n            SERVICE_BASE_PATHS[name],\n        )\n        for name in SERVICE_NAMES\n    }\n    if any(SHA40.fullmatch(value) is None for value in applied_revisions.values()):\n        raise ValueError("production canary service applied revision is invalid")\n',
    ),
])

patch("scripts/release/verify_promotion_evidence.py", [
    (
        'from promote_service_digests import SERVICE_NAMES, SERVICE_PATHS\n',
        'from promote_service_digests import SERVICE_BASE_PATHS, SERVICE_NAMES\n',
    ),
    (
        '            top["on_commit"],\n            "--",\n            SERVICE_PATHS[name],\n        )\n        for name in SERVICE_NAMES\n    }\n',
        '            top["on_commit"],\n            "--",\n            SERVICE_BASE_PATHS[name],\n        )\n        for name in SERVICE_NAMES\n    }\n',
    ),
])

patch("scripts/release/verify_promotion_chain.py", [
    (
        'SERVICE_APPLIED_REVISION_FIX_PATHS = (\n'
        '    "scripts/release/verify_promotion_chain.py",\n'
        '    "scripts/release/wait_release_rollouts.py",\n'
        '    "tests/release/test_kubernetes_release_runtime.py",\n'
        '    "tests/release/test_promotion_chain.py",\n'
        ')\n',
        'SERVICE_APPLIED_REVISION_FIX_PATHS = (\n'
        '    "scripts/release/build_production_canary.py",\n'
        '    "scripts/release/promote_service_digests.py",\n'
        '    "scripts/release/verify_promotion_chain.py",\n'
        '    "scripts/release/verify_promotion_evidence.py",\n'
        '    "scripts/release/wait_release_rollouts.py",\n'
        '    "tests/release/test_kubernetes_release_runtime.py",\n'
        '    "tests/release/test_production_canary.py",\n'
        '    "tests/release/test_promotion_chain.py",\n'
        '    "tests/release/test_promotion_evidence.py",\n'
        '    "tests/release/test_service_promotion.py",\n'
        ')\n',
    ),
])
print("round 2 applied")
