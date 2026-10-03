# Independent review (subagent critic, 2026-09-24 02:45Z)

**VERDICT: ACCEPT-WITH-RESERVATIONS**

**Overall Assessment**: The fix is semantically correct for the immediate blocking issue. The grammar slot follows established precedent patterns with one deliberate design variation (flexible parent via `current_commit`). The publisher workflow and contract test are structurally identical to the executed precedent, differing only in the expected constants. Two downstream files (`build_production_canary.py` and `verify_promotion_evidence.py`) retain the kustomization-only lookup, creating a latent inconsistency that does not block the current chain but could recur.

**Pre-commitment Predictions**: (1) Applied-revision lookup might not match ArgoCD behavior in edge cases involving non-rendered changes -- partially confirmed. (2) Grammar slot might be more permissive than precedents -- confirmed, deliberate. (3) Other files might still use the old lookup pattern -- confirmed, two files found. (4) Publisher/contract-test differences might go beyond constants -- confirmed, one non-cosmetic difference in the chain-absent guard. (5) Tests might not cover the specific failure scenario -- not confirmed, tests are well-designed.

---

**A. Semantic Correctness** -- Rating: **Info** (correct, one theoretical edge case)

The fix is semantically correct. `git log -1 --format=%H <observed> -- apps/<svc>/base` returns the last commit that changed ANY file under the base directory. ArgoCD's `spec.source.path` for each service is `apps/<service>/base` (`verify_kubernetes_release_runtime.py:349`: `f"apps/{service_name}/base"`). When any rendered manifest under that path changes, ArgoCD syncs and records the commit as `operationState.syncResult.revision`. The base-directory lookup matches this behavior.

The old code at `wait_release_rollouts.py:260-262` (pre-fix) used `SERVICE_PATHS[name]` which resolves to `apps/<svc>/base/kustomization.yaml`. The `5961922b` publisher commit changed `deployment.yaml` (startupProbe) without touching `kustomization.yaml`, causing ArgoCD to sync at `5961922b` while the kustomization-only lookup returned an earlier commit. The fix at `wait_release_rollouts.py:41` defines `SERVICE_BASE_PATHS = {name: f"apps/{name}/base" for name in SERVICE_NAMES}` and at line 131-135 introduces `_service_applied_revisions()` using these base paths. Line 262 now calls `_service_applied_revisions(root, observed_commit)` instead of the inline dict comprehension.

Realistic divergence case: A commit that changes a file under `apps/<svc>/base/` in a way that does NOT change the rendered Kustomize output (e.g., a YAML comment Kustomize strips). `git log` would return that commit, but ArgoCD would NOT re-sync, and `syncResult.revision` would remain at the earlier commit. This is theoretical -- the chain's strict `_require_delta` paths (`verify_promotion_chain.py:237-261`) prevent arbitrary file additions under base directories, and the release tooling never modifies YAML comments.

**B. Grammar Slot Security** -- Rating: **Info** (sound, one design-choice observation)

The slot does NOT weaken the chain. Evidence from `verify_promotion_chain.py:979-998`:

```python
if subject == SERVICE_APPLIED_REVISION_FIX_SUBJECT:
    _require_write_actor(root, commit)
    if (
        prior["phase"] != "services"
        or not prior["services_commit"]
        or parent != prior["current_commit"]
        or prior["service_applied_revision_fix_commit"]
    ):
```

Conditions enforced:
- `_require_write_actor` (line 981): author/committer = `devpath-gitops-release[bot]` -- requires the GitHub App's private key. Same as ALL other slots.
- Phase = `services`, `services_commit` non-empty (lines 983-984) -- structural constraint.
- Parent = `current_commit` (line 985) -- linear ancestry within the services phase.
- One-shot: `prior["service_applied_revision_fix_commit"]` (line 986) blocks repeats.
- `_require_delta` (line 989): exactly the 4 listed paths modified, all status `M`.
- `_require_migration`, `_require_services`, `_require_web` (lines 990-993): full manifest integrity checks unchanged.

**Design-choice observation** (Minor): The parent constraint uses `prior["current_commit"]` rather than `prior["services_commit"]`. Compare with `SERVICE_STATUS_IMAGE_FIX` at line 945 (`parent != prior["services_commit"]`) and `SERVICE_SOURCE_STATUS_FIX` at line 963 (`parent != prior["service_status_image_fix_commit"]`). The `current_commit` form accepts the fix after ANY service-phase commit, not only directly after the services commit. This is intentionally more permissive and correct for the current chain -- the fix can follow the services commit or any prior service-phase fix. The one-shot guard and `_require_write_actor` prevent abuse.

A commit with this exact subject would need: (1) possession of the release App's signing identity, (2) exact subject string match, (3) exactly the 4 listed paths changed and no others, (4) all service/migration/web kustomizations unchanged from the release candidate, (5) linear ancestry in the services phase, (6) slot not already filled. This is sufficiently constrained.

**C. Remaining Kustomization-only Lookups** -- Rating: **Minor**

Two files retain the old `SERVICE_PATHS[name]` (kustomization.yaml only) pattern for computing applied revisions:

`build_production_canary.py:145-156`:
```python
applied_revisions = {
    name: _git(chain_root, "log", "-1", "--format=%H", on_commit, "--", SERVICE_PATHS[name])
    for name in SERVICE_NAMES
}
```

`verify_promotion_evidence.py:201-212`:
```python
applied_revisions = {
    name: _git(root, "log", "-1", "--format=%H", top["on_commit"], "--", SERVICE_PATHS[name])
    for name in SERVICE_NAMES
}
```

Both run at the mission-ON phase. In the current chain, no commit between the services commit and mission-ON changes a non-kustomization file under any service base directory. The fix commit itself changes only `scripts/` and `tests/`, not `apps/`. The mission-OFF and mission-ON commits change only `apps/devpath-web/base/kustomization.yaml`. So the kustomization-only lookup and the base-directory lookup agree at every point from the services commit onward.

- Confidence: HIGH
- Why this matters: The fix solves the services-phase failure but does not close the identical pattern in later phases. A future chain that includes a mid-chain deployment.yaml change (between services and mission-ON) would trip the same bug again.
- Fix: Extract `_service_applied_revisions` (or its equivalent using `SERVICE_BASE_PATHS`) into a shared module and use it in `build_production_canary.py:145` and `verify_promotion_evidence.py:201`. This is not blocking the current publish.

No other promote/rollback flow uses `SERVICE_PATHS` for applied-revision lookup. The web rollout (`wait_web_rollout.py`) has its own `WEB_APPLIED_REVISION_FIX` already applied. The migration uses `MIGRATION_PATH` and `MIGRATION_APPLICATION_PATH` which are correct for their use case.

**D. Non-cosmetic Differences** -- Rating: **Info** (all differences are justified)

**Run script** (`run_service_applied_revision_main_publish.py` vs `run_pipeline_defects_main_publish.py`): ONLY constants and docstring differ. Every function, class, control path, and error message is byte-identical outside the constant definitions (MAIN_SHA, TARGET_SHA, TARGET_TREE, HELPER_BRANCH, TARGET_BRANCH, STAGED_BRANCH, DISPATCH_BRANCH). No non-cosmetic difference.

**Workflow YAML**: Differences limited to: `name:`, `description:`, `concurrency.group`, `if:` branch name, `env` block SHAs/branch names, step names containing `service-applied-revision` vs `pipeline-defects`, commit subject in test step, target listing rows (4 rows all `M` vs 12 rows with 11 `M` + 1 `A`), row count assertion (4 vs 12). Structure, step order, action pins, secret references, permissions, and the token-bearing steps block are identical.

**Contract test -- one non-cosmetic difference in `test_the_promotion_chain_is_deliberately_absent`**:

Precedent (`contract_test.py:452-461`):
```python
def test_the_promotion_chain_is_deliberately_absent(self) -> None:
    for forbidden in ("verify_promotion_chain", ...):
        self.assertNotIn(forbidden, self.text)
```

New (`test_service_applied_revision_main_publish.py:439-456`):
```python
def test_the_promotion_chain_is_deliberately_absent(self) -> None:
    guarded = "\n".join(
        line for line in self.text.splitlines()
        if not line.lstrip().startswith("$'M\\t")
        and not line.lstrip().startswith("$'A\\t")
    )
    self.assertNotIn("verify_promotion_chain.py --", self.text)
    for forbidden in ("verify_promotion_chain", ...):
        self.assertNotIn(forbidden, guarded)
```

This is NECESSARY because the target listing includes `scripts/release/verify_promotion_chain.py` as one of the 4 changed files (it's in the printf argument `$'M\tscripts/release/verify_promotion_chain.py'`). The guarded filter excludes literal listing data rows from the executable-code check. The additional `assertNotIn("verify_promotion_chain.py --", self.text)` guard ensures no command-line invocation of the chain verifier exists in the raw text. The precedent's target listing did not include `verify_promotion_chain.py`, so the raw check was sufficient there.

All other contract test differences are constants/names: SHA values, branch names, CONTRACT_TEST filename, TARGET_ROWS (4 entries vs 12), SUBJECT string, step names, GATE_BODIES entries (contract test name, target listing, subject, row count), TOKEN_BEARING_STEPS step names, concurrency group, class name.

**E. Tests Red/Green** -- Rating: **Info** (all three correctly discriminate)

1. `test_service_applied_revision_tracks_any_base_manifest_change` (`test_kubernetes_release_runtime.py:113-162`): On old code, `SERVICE_BASE_PATHS` and `_service_applied_revisions` do not exist -- `AttributeError`. On new code, both exist and the test exercises the exact scenario: creates a temp repo, commits `kustomization.yaml` + `deployment.yaml` for all services, then modifies only `deployment.yaml` for `devpath-ai-svc`. Verifies the base-directory lookup returns the second commit while the kustomization-only lookup returns the first. **Red on old, green on new.**

2. `test_exact_service_applied_revision_fix_is_phase_transparent_and_cannot_repeat` (`test_promotion_chain.py:1062-1083`): On old code, the chain walker does not recognize `SERVICE_APPLIED_REVISION_FIX_SUBJECT` and raises `"current main contains an unrelated promotion commit"` instead of succeeding. The test expects a successful inspect (phase = services, fix commit recorded) followed by a repeat failure (`"directly follow services"`). **Red on old, green on new.**

3. `test_service_applied_revision_fix_requires_services_and_exact_paths` (`test_promotion_chain.py:1085-1109`): On old code, same -- unrecognized subject triggers the wrong error. The test expects `"directly follow services"` when applied before services phase, and `"path set is not exact"` when an expected path is omitted from the commit. Both assertions would fail on old code. **Red on old, green on new.**

---

**What's Missing**:
- The `build_production_canary.py` and `verify_promotion_evidence.py` base-directory migration (see C above). Not blocking for this publish.
- No test validates the interaction between `service_applied_revision_fix` and other service-phase fixes (e.g., the combination of `service_status_image_fix` + `service_applied_revision_fix` in the same chain). The `current_commit` parent constraint makes this safe but untested.

**Verdict Justification**: Review operated in THOROUGH mode throughout. No CRITICAL or MAJOR findings. The fix is narrowly scoped, semantically correct, structurally consistent with executed precedent, and testable. The single reservation is the latent kustomization-only pattern in `build_production_canary.py:145` and `verify_promotion_evidence.py:201`, which should be addressed in a future release cycle but does not block this publish.

---

**5-line summary**:

VERDICT: ACCEPT-WITH-RESERVATIONS. 0 Critical, 0 Major, 2 Minor (one latent consistency, one design-choice observation).
The fix is semantically correct -- base-directory lookup matches ArgoCD's sync-revision model.
The grammar slot is sound: write-actor, phase, one-shot, delta, and manifest integrity checks are all enforced.
The single reservation: `build_production_canary.py:145` and `verify_promotion_evidence.py:201` retain the old kustomization-only lookup, safe for this chain but should be migrated later.
Most important finding: the fix correctly unblocks the services-phase runtime verifier and the publisher is a faithful instantiation of the executed precedent.