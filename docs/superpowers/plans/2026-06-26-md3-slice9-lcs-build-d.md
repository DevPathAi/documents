# 빌드플랜 — MD3 슬라이스 #9 LCS Build D (프론트 + 통합 릴리스) (2026-06-26)

> 상위 플랜 `2026-06-26-md3-slice9-lcs-build.md`의 Build D 상세화. 설계서 `specs/2026-06-26-md3-slice9-lcs-design.md` §4·§6·§7 기준.
> 원칙: Test-First · 추측금지 · 신규 브랜치 · 컨트롤러 직접검증(각 레포 CLAUDE.md 절대조건). WSL+Bash 메인 직접 진행.

## 검증된 전제 (코드 실측, 2026-06-26)
- gateway `/lcs/**` → `${LCS_SVC_URI:http://localhost:8087}` 라우트 **이미 적용**(Build C, develop).
- lcs-svc 엔드포인트: `POST /snapshots/draft`·`POST /snapshots/{draftId}/commit`·`GET /snapshots/{id}`·`GET/PUT /preferences`. **`by-question` 없음**.
- lcs-svc `main`: `ci.yml` 없음 + `gradlew` 권한 `100644`(실행비트 X). develop은 `ci.yml` 있음 + `gradlew` `100755`. → 릴리스 develop→main이 둘 다 main에 반영.
- lcs-svc develop `ci.yml`의 **deploy 잡**: `working-directory: gitops/apps/devpath-lcs-svc/base`에서 `kustomize edit set image` 실행 → **gitops main에 해당 디렉터리가 선행 존재해야 성공**.

## 통합 갭 (Build D가 푸는 문제)
B·C에서 community 무변경 → `CommunityQuestionDetail`에 `snapshotId` 노출 경로 없음. 프론트 상세는 `questionId`만 보유.
→ community 무변경 유지를 위해 lcs-svc에 `by-question` 역조회 추가. commit 흐름은 설계서 §7 정본: 프론트가 질문 게시(201, questionId) 후 `commit{attachedToId: questionId}` 호출.

---

## Phase 1 — lcs-svc: `GET /lcs/snapshots/by-question/{questionId}`
**브랜치**: `devpath-lcs-svc` `feat/slice9-lcs-by-question` (develop 분기)

**Test-First**:
1. `LcsServiceTest`(mock 단위, 기존 파일 미러):
   - `byQuestionReturnsSnapshotWhenCommitted` → SnapshotView(renderedFor="answerer")
   - `byQuestionMissingThrowsNotFound` → `NotFoundException`
   - `byQuestionPrivateNonOwnerForbidden` → `ForbiddenException`(기존 `canView` 재사용)
2. `LcsControllerTest`(`@WebMvcTest`, 기존 파일 미러):
   - `byQuestionReturns200` → `get("/lcs/snapshots/by-question/5")` 200, `$.renderedFor`="answerer"
   - `byQuestionMissingReturns404`

**구현(최소)**:
- `LearningContextSnapshotRepository.findFirstByAttachedToTypeAndAttachedToIdOrderByCreatedAtDesc(String, Long)` (불변·최신 1건; 인덱스 `(attached_to_type, attached_to_id)`).
- `LcsService.getSnapshotByQuestion(long userId, long questionId)`: type="question" 조회 → 없으면 NotFound → `canView`(없으면 403) → `SnapshotView`.
- `LcsController` `@GetMapping("/snapshots/by-question/{questionId}")` (세그먼트 수 달라 `{id}`와 충돌 없음).

**게이트**: `./gradlew test` 로컬 green(JDK 21, 필요시 shared `publishToMavenLocal -x test`) → PR → develop → CI green(PR은 build/test만, deploy `if main` skip).

---

## Phase 2 — 프론트(apps/web): 맥락 카드 + 답변자 패널
**브랜치**: `devpath-frontend` `feat/slice9-frontend-lcs` (develop 분기)

### 2-1. dp_core 모델 — `packages/dp_core/lib/src/models/lcs_snapshot.dart` (freezed, `community_post.dart` 미러)
- `LcsDraft{draftId, expiresAt, content, fieldsAvailable, fieldsUnavailable}`
- `LcsFieldUnavailable{field, reason}`
- `LcsSnapshotView{id, createdAt, content, renderedFor}`
- (preferences는 Build D MVP 밖 → 후속). export 배럴 추가 → `cd packages/dp_core && dart run build_runner build --delete-conflicting-outputs`(무관 `.freezed/.g` 줄바꿈은 `git checkout --`).

### 2-2. 데이터 소스 — `apps/web/lib/src/features/community/data/community_source.dart`(또는 신규 `lcs_source.dart`)
- `lcsDraftProvider` → `POST /lcs/snapshots/draft`
- `lcsCommitProvider` → `POST /lcs/snapshots/{draftId}/commit`
- `lcsByQuestionProvider` → `GET /lcs/snapshots/by-question/{questionId}`(404→null 정규화)

### 2-3. 맥락 카드 — `question_create_page.dart`(`_QuestionCreatePageState`)
설계서 §6: opt-in 토글 → on이면 draft 호출 → 필드 칩 토글 + 미리보기 + 노출범위 선택. 게시 성공(detail.id) 직후 토글 on이면 `lcsCommitProvider(draftId, attachedToId: detail.id, visibility)` → 상세 이동. community 계약 무변경.

### 2-4. 답변자 패널 — `qna_detail_page.dart`(`_Loaded`)
상세 로드 시 `lcsByQuestionProvider(detail.id)` → 200이면 제목/본문 사이 맥락 패널 렌더, 404면 미표시.

### 2-5. 목 픽스처 — `apps/web/lib/src/data/web_mock_fixtures.dart`
`POST /lcs/snapshots/draft`(200)·`POST /lcs/snapshots/{draftId}/commit`(201)·`GET /lcs/snapshots/by-question/1`(200) + 미표시 검증용 404 케이스.

### 2-6. 테스트 — `apps/web/test/features/community/`(`ProviderContainer overrides` 미러)
작성: 토글 on→칩 렌더 / 게시 시 commit이 questionId·visibility로 호출. 상세: 200→패널, 404→미표시. 소스/컨트롤러 단위.

**게이트**: `melos run analyze`·`test`·`format`(CI 게이트, info 린트도 비-green) 전부 녹색 → PR → develop → CI green.

---

## Phase 3 — gitops 앱 등록 (⚠️ 릴리스 전 main 필수)
**브랜치**: `devpath-gitops` `feat/slice9-lcs-app` (develop 분기)
- `apps/devpath-lcs-svc/base/{deployment,service,kustomization}.yaml`(community 미러): image `ghcr.io/devpathai/devpath-lcs-svc:main`, containerPort 8080, readiness/liveness `/actuator/health/*`, service 8080→8080, kustomization `images:` 항목.
- ApplicationSet `apps/*` 자동발견 → 디렉터리만 추가하면 됨.
- ⚠️ **gitops `main`으로 머지**(배포 소스). lcs-svc 릴리스 전 선행 조건.

---

## Phase 4 — 통합 릴리스 + 문서 (배포는 사용자 확인 후)
**순서 엄수**:
1. gitops Phase 3 → **main**(선행).
2. lcs-svc `develop→main` 릴리스 PR(=gradlew 실행비트·ci.yml main 반영 → build→publish→deploy 잡 발동).
3. gateway `develop→main`, frontend `develop→main`.
4. documents Build D 보고서 `reports/2026-06-26-slice9-d-build-report.md` + 다음 핸드오프 → develop PR.
- **ArgoCD 프로덕션 동기화 검증은 사용자 확인 후**.

**최종 게이트**: lcs-svc CI green(postgres+redis)·gateway CI green·frontend melos green·gitops 배포 커밋·각 레포 main HEAD == 배포 SHA.

---

## 리스크/주의
- build_runner 무관 `.freezed/.g` 줄바꿈 변경 → `git checkout --`로 되돌림.
- lcs-svc 로컬 빌드 전 shared `publishToMavenLocal`(GitHub Packages 401 우회).
- gitops/lcs-svc `.github/workflows` 푸시는 `workflow` 스코프 필요 가능 → 사용자 `! gh auth refresh -h github.com -s workflow` 1회.
- 프론트 UX는 설계서 §6(opt-in 토글→draft→칩/미리보기/노출범위→commit)이 정본.
