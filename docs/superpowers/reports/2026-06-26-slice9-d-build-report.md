# 빌드 보고서 — MD3 슬라이스 #9 LCS Build D + 통합 릴리스 (2026-06-26)

> 플랜 `plans/2026-06-26-md3-slice9-lcs-build-d.md` 기준. **슬라이스 #9(LCS) 완료·프로덕션 배포 검증.** WSL+Bash 메인 직접 진행.

## 1. 결과 요약
슬라이스 #9 LCS(학습 맥락 자동 첨부) **Build D(프론트) + 통합 릴리스 완료**. lcs-svc 신규 서비스 + gateway 라우트가 ArgoCD로 프로덕션 배포됨(deploy 잡→gitops 커밋→main HEAD == 배포 SHA 검증). community-svc 무변경 유지.

## 2. 구현 (Test-First · red→green, 각 레포 절대조건 준수)

### D-1. lcs-svc `GET /lcs/snapshots/by-question/{questionId}` (PR #2 → develop, #3 → main)
- 통합 갭 해결: community가 `snapshotId`를 노출하지 않아, 답변자 패널이 `questionId`로 역조회.
- `findFirstByAttachedToTypeAndAttachedToIdOrderByCreatedAtDesc`(불변·최신 1건) + `getSnapshotByQuestion`(없으면 404, private 비소유자 403 — `canView` 재사용) + 컨트롤러 매핑.
- 검증: 서비스 14 + 컨트롤러 8 + JPA 3 + 조립 6 = **31 green**. 파생쿼리는 임시 clean DB(전체 shared 마이그레이션=CI 동일)에서 실 postgres 검증.

### D-2. 프론트 맥락 카드 + 답변자 패널 (PR #37 → develop, #38 → main)
- dp_core: `LcsDraft`·`LcsSnapshotView`·`LcsFieldUnavailable`(freezed).
- data `lcs_source`: draft/commit/by-question + **404→null 정규화** + `questionSnapshotProvider`(family).
- 작성 `LcsContextCard`: opt-in 토글 → `draft` 미리보기(필드 칩, 키→한글 라벨) + 노출범위(answerers_only/public/private) → 게시 응답 questionId로 `commit`(best-effort, 첨부 실패가 게시를 막지 않음).
- 상세 `LcsAnswererPanel`: `by-question` 200 → 패널, 없으면(404→null) 미표시.
- 목 픽스처(`/lcs/**`) + 위젯/소스 테스트. **web 147 + dp_core 48 green**, analyze 0, format clean.
- 스코프: 필드 개별 토글은 더 많은 필드가 라이브될 때(Phase 2) 후속 — 현재 백엔드는 `recent_activity`/`current_content`만 included(나머지 Phase 2 연기).

### D-3. gitops 앱 등록 (PR #11 → develop, #12 → main)
- `apps/devpath-lcs-svc/base/{deployment,service,kustomization}.yaml`(community 미러). ApplicationSet 자동발견.
- CI `kustomize`(kubectl kustomize 렌더) pass.

## 3. 통합 릴리스 (develop→main, 사용자 GO 후, 순서 엄수)
1. **gitops #12 → main** (앱 등록 선행). ⚠️ **main 기준 분기**로 신규 3파일만 머지 — 아래 §4 참조.
2. **lcs-svc #3 → main**: main CI build→publish(ghcr `:main`/`:sha`)→deploy. 배포 SHA `2bc7398…`.
3. **gateway #22 → main**: 배포 SHA `86bf756…`.
4. **frontend #38 → main**: 릴리스만(deploy 잡 없음). main HEAD `8b732dd…`.
- **검증**: gitops main에 `deploy(devpath-lcs-svc): 2bc7398…`·`deploy(devpath-gateway): 86bf756…` 커밋. lcs-svc/gateway **main HEAD == gitops kustomization newTag** 일치 확인. ArgoCD auto-sync(prune+selfHeal)로 클러스터 반영.

## 4. ⚠️ 발견 — gitops develop→main 머지는 위험(롤백 유발)
- gitops **기본 브랜치 = main**, **deploy 봇이 이미지 SHA를 main에 직접 커밋** → `develop`이 다른 앱들의 태그에서 뒤처짐(예: community develop `87be03f` vs main `3332b09`).
- 따라서 gitops를 **develop→main 머지하면 7개 서비스가 구 이미지로 롤백**된다. → 신규 앱 등록은 **main에서 분기해 앱 파일만** 담아 main에 PR해야 안전(이번에 그렇게 처리).
- 후속: gitops `develop`을 main에서 재동기화하거나, 앱 구조 변경 PR은 항상 main 기준으로.

## 5. 환경
- WSL: JDK 21(`~/jdks`) + shared mavenLocal(GitHub Packages 401 우회), Flutter 3.44.4(`~/flutter`) + melos. antml 마찰 0건(메모리 [[wsl-build-environment]]·[[antml-prefix-windows-only]]).
- lcs JPA 테스트: 로컬 `devpath` DB는 dirty → clean DB/CI에서 검증(이번엔 임시 DB 생성으로 로컬 실검증).

## 6. 참고
- 플랜: `plans/2026-06-26-md3-slice9-lcs-build-d.md`(PR #44). 설계서: `specs/2026-06-26-md3-slice9-lcs-design.md`.
- 직전 핸드오프: `handoff-2026-06-26-slice9-abc-done-d-next.md`.
