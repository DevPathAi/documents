# gitops 검증기 applied-revision 결함 fix publisher — 실행 기록 (2026-09-24)

> 실행 완료. 이 문서는 요약이고 디렉터리 `2026-09-24-gitops-main-service-applied-revision-via-publisher/` 가 스크립트·렌더 산출물·리뷰다. 선례: `2026-09-21-gitops-main-pipeline-defects-via-publisher.md`(틀), 체인 슬롯 선례 `f9b717e`(web applied revision lineage).

**Goal:** 릴리스 r3 의 promote(services 관문)가 `Argo Application revision is not exact` 로 두 번 실패한 원인 — `wait_release_rollouts.py` 가 applied revision 을 `apps/<svc>/base/kustomization.yaml` 의 마지막 커밋으로 계산하는 결함 — 을 봇 target 커밋으로 고쳐 one-shot publisher 로 gitops `main` 에 올리고 nonce 로 promote 를 재개한다.

**결함:** 9/23 publisher `5961922b` 가 8개 JVM `deployment.yaml`(startupProbe)만 바꿔 Argo 는 그 커밋으로 sync 했고, 그 뒤 kustomization 이 안 바뀐 ai·community·lcs·learning·notification 5개의 `operationState.syncResult.revision`(`5961922b`)이 검증기 기대값(r3 `ec54b37`/ai `12fd3b9`)과 영구 불일치. `build_production_canary.py`·`verify_promotion_evidence.py` 도 같은 kustomization 기준 lookup 을 Argo 기록과 대조하므로 promote ON·landing 에서 재발할 것이었다(1차 리뷰가 '경미'로 분류 → 직접 대조 후 범위 확장).

**수정(target `8b01c02dd1d1e1a3d400a2536e7b7f23227bd264`, 트리 `b38a6ebf…`, 부모 `8b036dc`, 봇 신원, 고정 시각 2026-09-24T02:00:00Z, subject = 체인 슬롯 `fix(release): bind service applied revision to the app base`, 10경로 M):**
- `promote_service_digests.py` `SERVICE_BASE_PATHS = {name: f"apps/{name}/base"}` 공유
- `wait_release_rollouts.py` `_service_applied_revisions(root, observed)` = 디렉터리 기준 `_last_path_change`
- `build_production_canary.py`·`verify_promotion_evidence.py` 가 `SERVICE_BASE_PATHS[name]` 사용
- `verify_promotion_chain.py` 슬롯 상수·경로 집합·state key `service_applied_revision_fix_commit`·walk(phase services, parent == current, 1회, `_require_delta/_require_migration/_require_services/_require_web(...,"base")`)
- 테스트: `test_kubernetes_release_runtime.py`(디렉터리 기준 증명) · `test_promotion_chain.py`(수용·반복 거부·경로 집합) · `test_service_promotion.py` · `test_promotion_evidence.py` · `test_production_canary.py`

**Tasks (전부 완료):**
- [x] Task 1 TDD — `patch_tests_r3fix.py`(RED) → `patch_impl_r3fix.py`(GREEN) → 2라운드 `patch_round2_r3fix.py`(canary·evidence·공유 상수) — dev `dev/service-applied-revision-20260924` `fa3383b`, 스위트 **359 OK**
- [x] Task 2 결정적 target — `make_service_applied_revision_target.py <clone> <source> [expected]` → `target.txt`; 체인 검증기가 r3 체인 위 fix 를 수용(phase services)하고 디렉터리 기준 applied revision 9/9 가 라이브 Argo syncResult 와 일치
- [x] Task 3 publisher 렌더 — `render_r3fix_publisher.py`(9/21 선례 `prec-0921-live` 에서 counted substitution; 계약 가드 `test_the_promotion_chain_is_deliberately_absent` 는 target 이 `verify_promotion_chain.py` 자체를 고치므로 listing 행을 제외한 텍스트로 완화 + `assertNotIn("verify_promotion_chain.py --")`) → `rendered/`
- [x] Task 4 검증 — 헬퍼 `d5a4694c`(`chore/service-applied-revision-publish-20260924`) 계약 18/18 · staged `1d960111` · run 스크립트 단위 18 · preflight ok · 음성 대조 거부 · 독립 리뷰 `REVIEW.md`(ACCEPT-WITH-RESERVATIONS → 유보 2건 실제 대조로 해소)
- [x] Task 5 실행 — 사용자 결정 "publisher 로 검증기 수정 게시 후 재개" → `run_service_applied_revision_main_publish.py`(환경 `mission-spine-production-off`, 방아쇠 `automation/dispatch-service-applied-revision-main-publish`) → 런 `35949979763` success(03:04~03:07Z, 2분 15초, deployment 6629254999) → **main `8b01c02d`** → Argo refresh → 9 서비스 Synced/Healthy · syncResult = 디렉터리 기준 기대값
- [x] Task 6 재개 — nonce `11920e22` → promote OFF `35950184028` success → mission-off `1d45b63` → promote ON `35950519691` success → mission-on `eae5c42`

**함정:** Bash 도구가 `\` 한 겹을 먹어 인라인 파이썬 패치가 두 번 깨짐(긴 패치는 파일로) · 첫 헬퍼 커밋이 계약 테스트 실패 상태로 push 됨(`&&`+`tail` 이 rc 를 가림 → amend·force-push, 일회용 브랜치) · Codex CLI 리뷰 20분 무출력 → 서브에이전트 리뷰로 대체.
