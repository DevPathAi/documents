# 빌드플랜 — MD3 슬라이스 #9 LCS (2026-06-26)

> 설계서 `specs/2026-06-26-md3-slice9-lcs-design.md` 기준. 전용 `devpath-lcs-svc`(포트 8087, `ai.devpath.lcs`). TDD·추측금지·CI 1급 검증·develop 2단계 PR·슬라이스 끝 통합 릴리스.

## Build A — shared 마이그레이션
- `devpath-shared/src/main/resources/db/migration/V20260626xxxx__lcs_snapshots.sql`(직전 max `V202606251001`+1, 작성 시 재실측): `learning_context_snapshots` + `user_context_preferences`(설계서 §3, BIGINT 논리참조·교차서비스 FK 없음).
- shared 호환 테스트(있으면) + `flyway` 로컬 적용 검증 + `publishToMavenLocal`.
- **shared는 develop 부재 → feature→main PR**. 릴리스 후 재publish.

## Build B — lcs-svc 코어 (신규 레포)
- 스캐폴딩(community-svc 미러): svc-template 파생 → `devpath-lcs-svc`(settings/build.gradle.kts: shared+GitHub Packages·JPA·postgres·security/oauth2-resource-server·**redis**) + `application.yml`(port 8080, kafka group `devpath-lcs`, `devpath.learning.base-url`·`devpath.sandbox.base-url`) + `LcsApplication` + config(Security·GlobalExceptionHandler).
- 엔티티/리포지토리: `LearningContextSnapshot`·`UserContextPreference`(JPA, ddl `validate`).
- `SnapshotAssembler`: current_content 풀(learning-svc `/internal/contents/{id}` 재사용; 현재콘텐츠 판별 = 프론트 contentId 동봉 vs learning-svc 내부 진척조회 — **Build B에서 실측 후 택1**) + graceful degradation(멘토 패턴). active_tags/tag_reputation/recent_errors = MVP 생략.
- `DraftStore`(Redis): `lcs:draft:{token}` TTL 10분.
- `LcsController`: `POST /lcs/snapshots/draft`·`POST /lcs/snapshots/{id}/commit`·`GET /lcs/snapshots/{id}`(인가)·`GET/PUT /lcs/preferences`.
- 테스트: 조립(소스 mock)·draft/commit·인가·preferences. CI = postgres(pgvector pg17) **+ redis 서비스 컨테이너 추가** green.
- develop 2단계 PR(신규 레포 → develop).

## Build C — gateway + 연계
- gateway `application.yml`·`application-test.yml`: `id: lcs`, `uri: ${LCS_SVC_URI:http://localhost:8087}`, `Path=/lcs/**`. `LcsRouteTest`(미인증 401 + 인증 라우트) 미러(슬라이스 #8 community 라우트). Test-First.
- commit 흐름: **프론트가 질문 게시(201, questionId) 후 `POST /lcs/snapshots/{draftId}/commit {attachedToId: questionId}`** → community-svc 무변경(순환 회피). `community_questions.learning_context`에 snapshotId 저장 필요 여부는 Build C 실측(상세 응답에 snapshotId 노출 경로 확정).
- gitops `apps/devpath-lcs-svc/base/{deployment,service,kustomization}.yaml`(ApplicationSet 자동발견).

## Build D — frontend (apps/web)
- 맥락 카드(작성 폼): opt-in 토글 → draft 호출 → 필드 칩 토글·미리보기·노출범위 → 게시 후 commit.
- 답변자 맥락 패널(질문 상세): 스냅샷 있으면 `GET /lcs/snapshots/{id}` 렌더.
- dp_core 모델 + provider(목 픽스처) + 위젯/컨트롤러 테스트. `melos run analyze/test/format` 녹색.

## 통합 릴리스
- shared(이미 main) → lcs-svc·gateway·frontend(+필요시 learning-svc) develop→main + 신규 gitops app + image/deploy(ArgoCD). documents develop PR(설계서·플랜·보고서).

## 검증 게이트(슬라이스 끝)
- lcs-svc CI green(postgres+redis) · gateway CI green · frontend melos green · gitops 배포 커밋 · main HEAD == 배포 SHA.
