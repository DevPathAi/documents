"""Add the RED tests for the service applied-revision fix (run from the gitops fix worktree)."""
import pathlib

ROOT = pathlib.Path("D:/workspace/dpa/.worktrees/gitops-fix-applied-revision-20260924")

# --- tests/release/test_kubernetes_release_runtime.py -------------------------------------------------
p = ROOT / "tests/release/test_kubernetes_release_runtime.py"
s = p.read_text(encoding="utf-8")
anchor = "    def setUp(self):\n        self.name = \"devpath-ai-svc\"\n"
assert s.count(anchor) == 1
new_test = '''    def test_service_applied_revision_tracks_any_base_manifest_change(self):
        # Argo syncs on any rendered change beneath apps/<service>/base (2026-09-23: startupProbe in
        # deployment.yaml), so the applied revision must follow the base directory, not kustomization.yaml.
        self.assertEqual(
            set(self.wait.SERVICE_BASE_PATHS), set(self.wait.SERVICE_NAMES)
        )
        self.assertEqual(
            self.wait.SERVICE_BASE_PATHS["devpath-ai-svc"], "apps/devpath-ai-svc/base"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "test"], cwd=root, check=True
            )
            for name in self.wait.SERVICE_NAMES:
                base = root / "apps" / name / "base"
                base.mkdir(parents=True)
                (base / "kustomization.yaml").write_text("resources: []\\n", encoding="utf-8")
                (base / "deployment.yaml").write_text("kind: Deployment\\n", encoding="utf-8")
            subprocess.run(["git", "add", "apps"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "services"], cwd=root, check=True)
            services_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
            ).stdout.strip()
            (root / "apps" / "devpath-ai-svc" / "base" / "deployment.yaml").write_text(
                "kind: Deployment\\nstartupProbe: true\\n", encoding="utf-8"
            )
            subprocess.run(["git", "add", "apps"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "startup budget"], cwd=root, check=True)
            observed_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
            ).stdout.strip()

            applied = self.wait._service_applied_revisions(root, observed_commit)
            self.assertEqual(set(applied), set(self.wait.SERVICE_NAMES))
            self.assertEqual(applied["devpath-ai-svc"], observed_commit)
            self.assertEqual(applied["devpath-gateway"], services_commit)
            self.assertEqual(
                self.wait._last_path_change(
                    root, observed_commit, self.wait.SERVICE_PATHS["devpath-ai-svc"]
                ),
                services_commit,
            )

'''
s = s.replace(anchor, new_test + anchor)
p.write_text(s, encoding="utf-8", newline="\n")
print("runtime test added")

# --- tests/release/test_promotion_chain.py ------------------------------------------------------------
p = ROOT / "tests/release/test_promotion_chain.py"
s = p.read_text(encoding="utf-8")
old = "            *self.chain.SERVICE_SOURCE_STATUS_FIX_PATHS,\n            *self.chain.CANARY_RUNTIME_FORM_FIX_PATHS,\n"
assert s.count(old) == 1
s = s.replace(old, "            *self.chain.SERVICE_SOURCE_STATUS_FIX_PATHS,\n            *self.chain.SERVICE_APPLIED_REVISION_FIX_PATHS,\n            *self.chain.CANARY_RUNTIME_FORM_FIX_PATHS,\n")
old = "    def commit_canary_runtime_form_fix(self, *, suffix: str = \"\") -> str:\n"
assert s.count(old) == 1
helper = '''    def commit_service_applied_revision_fix(self, *, suffix: str = "") -> str:
        paths = self.chain.SERVICE_APPLIED_REVISION_FIX_PATHS
        for relative in paths:
            path = self.root / relative
            path.write_text(
                path.read_text(encoding="utf-8")
                + f"\\n# service-applied-revision-fix{suffix}\\n",
                encoding="utf-8",
                newline="\\n",
            )
        git(self.root, "add", *paths)
        git(self.root, "commit", "-m", self.chain.SERVICE_APPLIED_REVISION_FIX_SUBJECT)
        return git(self.root, "rev-parse", "HEAD")

'''
s = s.replace(old, helper + old)
old = "    def test_exact_service_status_image_fix_is_phase_transparent_and_cannot_repeat(self):\n"
assert s.count(old) == 1
tests = '''    def test_exact_service_applied_revision_fix_is_phase_transparent_and_cannot_repeat(self):
        self.set_migration()
        migration = self.commit(
            f"deploy(devpath-migration): {self.candidate['release_id']} sealed {self.release_hash}"
        )
        self.set_services()
        services = self.commit(
            f"release(services): promote {self.candidate['release_id']} additive-services"
        )
        applied_fix = self.commit_service_applied_revision_fix()

        state = self.inspect(applied_fix)
        self.assertEqual("services", state["phase"])
        self.assertEqual("base", state["web_phase"])
        self.assertEqual(migration, state["migration_commit"])
        self.assertEqual(services, state["services_commit"])
        self.assertEqual(applied_fix, state["service_applied_revision_fix_commit"])
        self.assertEqual(applied_fix, state["current_commit"])

        repeated = self.commit_service_applied_revision_fix(suffix="-repeated")
        with self.assertRaisesRegex(ValueError, "directly follow services"):
            self.inspect(repeated)

    def test_service_applied_revision_fix_requires_services_and_exact_paths(self):
        self.set_migration()
        self.commit(
            f"deploy(devpath-migration): {self.candidate['release_id']} sealed {self.release_hash}"
        )
        early = self.commit_service_applied_revision_fix()
        with self.assertRaisesRegex(ValueError, "directly follow services"):
            self.inspect(early)

        git(self.root, "reset", "--hard", "HEAD^")
        self.set_services()
        self.commit(
            f"release(services): promote {self.candidate['release_id']} additive-services"
        )
        omitted = self.chain.SERVICE_APPLIED_REVISION_FIX_PATHS[-1]
        self.commit_service_applied_revision_fix()
        git(self.root, "checkout", "HEAD^", "--", omitted)
        git(self.root, "add", omitted)
        git(self.root, "commit", "--amend", "--no-edit")
        applied_fix = git(self.root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(ValueError, "path set is not exact"):
            self.inspect(applied_fix)

'''
s = s.replace(old, tests + old)
p.write_text(s, encoding="utf-8", newline="\n")
print("chain tests added")
