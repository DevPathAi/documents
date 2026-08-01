# Handoff — 계약확장 이월 A·B·C 완결(머지) · D(서식 에디터) spec 단계 (2026-07-31)

> 이번 세션은 [handoff-2026-07-31-uiux-roadmap-complete-next-contract-expansion](handoff-2026-07-31-uiux-roadmap-complete-next-contract-expansion.md)가 이월한 **4건(A·B·C·D)** 을 사용자 지시대로 **A→B→C→D 순차**로 진행했다. **A·B·C는 brainstorm→spec→plan→인라인 TDD 구현→PR→CI green→사용자 승인→develop 머지까지 전부 완결**. **D는 brainstorming으로 접근(진짜 WYSIWYG) 확정 + spec 작성·커밋까지 진행**(구현 전, 다음 세션 이관).

## 요약 표

| 작업 | 상태 | 백엔드 PR | 프론트 PR |
|---|---|---|---|
| A 대시보드 시계열 | ✅ 머지 완결 | learning-svc **#42**(merge `7e374be`) | frontend **#94**(merge `37e23d2`) |
| B 커뮤니티 excerpt 미리보기 | ✅ 머지 완결 | community-svc **#30**(merge `69ba67e`) | frontend **#95**(merge `aac3199`) |
| C admin 벌크 액션 | ✅ 머지 완결 | platform-svc **#43**(merge `8caf083`) | frontend **#96**(merge `2c325ae`) |
| D 서식 텍스트 에디터 | 🟡 **spec 단계**(구현 전) | — | frontend 브랜치 `feat/rich-text-editor`(spec 커밋 `9fc696a`, **push됨**) |

- frontend develop 최신 = **`2c325ae`**(A·B·C 반영). 각 작업 spec/plan = `devpath-frontend/docs/superpowers/{specs,plans}/2026-07-31-{dashboard-timeseries,community-excerpt-preview,admin-bulk-actions,rich-text-editor}*`.
- **공통 패턴**: 각 작업 = 개별 brainstorm→spec→writing-plans→inline executing-plans(서브에이전트 미사용). 계약확장(A·B·C)은 전부 **서비스 로컬 record/DTO → `shared` 발행 불필요**, 백엔드+프론트 2 PR, **백엔드 먼저 머지**.

## A. 대시보드 시계열 차트 (완결)
- **주간 학습량 바차트(7일)** + **진행률 추이 라인차트(14일 누적%)**. 기존 타임스탬프(`user_content_progress.completed_at`·`path_weekly_tasks.completed_at`, 둘 다 TIMESTAMPTZ)의 **SQL 집계 프로젝션** → 신규 이벤트 수집 불필요.
- **★핸드오프 정정**: 이월 문서의 "DpKpiCard에 trend 슬롯 이미 존재"는 **오류**(실제 `progress` 진행바만) → 범위를 신규 카드 2개(Option 2)로 확정.
- **★설계 편차: 백엔드 DTO `date`=`String`(ISO) not `LocalDate`**. 이유: jackson-datatype-jsr310가 learning-svc **테스트 컴파일 classpath에 미해결** → LocalDate 직렬화 취약(@JsonTest도 이 프로젝트선 ObjectMapper 빈 생성 실패). JSON 와이어(`"2026-07-31"`)는 동일, 헬퍼가 DTO 경계서 `toString()`. **교훈: 소형 서비스 wire DTO 날짜는 String ISO가 안전**.
- 파일: learning-svc `DashboardSummary`+`DailyActivity`/`ProgressPoint`·`DashboardTimeseries`(순수 헬퍼 7일 갭필·14일 누적율)·`ContentProgressRepository`(집계 쿼리 KST 버킷). frontend dp_core 모델·`apps/web` `WeeklyActivityCard`/`ProgressTrendCard`(fl_chart, 앱 레벨)·Bento 통합·목.

## B. 커뮤니티 제목 미리보기(excerpt) (완결)
- 제목 hover 시 본문 요약 미리보기(웹 전용). `QuestionService.list()`가 이미 전체 엔티티 로드 → `Excerpts.from(body_md, 140)` 파생, **추가 쿼리 없음**. `Excerpts` 순수 헬퍼(마크다운 마커 제거·140자 말줄임).
- frontend: dp_core `CommunityPostSummary.excerpt`(`@Default('')`, mobile 컴파일 안전). **`DpListRow`에 `preview` 슬롯 신설** = `MouseRegion`+`OverlayPortal`+`CompositedTransformFollower` hover 카드(웹 전용). web `_postRow` 배선·목.
- **★교훈: community-svc 테스트 DB명 = `devpath_citest`**(learning-svc의 `devpath`와 다름).

## C. admin 벌크 액션 (완결)
- **소관 = platform-svc**(users=`beta/AdminUserController`, ads=`ads/AdminAdController`). `POST /admin/users/bulk-approve`·`POST /admin/ads/bulk-delete`, `{ids:[number]}`→**204**(요청 바디는 기존 `/admin/allowlist`처럼 `@RequestBody Map<String,List<Long>>`). 서비스 `bulkApprove`(존재 id만 approveUser 반복·멱등)·`bulkDelete`(존재 id만 deleteById).
- frontend: `DpDataTable`에 `showCheckboxColumn`·`onSelectAll` 패스스루(기존 소비처 불변). admin 공용 `BulkActionBar`(`apps/admin/lib/src/widgets/`, AnimatedSwitcher). users(`Set<String>`)·ads(`Set<int>`) 컨트롤러 selectedIds+벌크 메서드, 페이지 `DataRow2(selected:,onSelectChanged:)`+벌크바(key `users-bulk-bar`·`ads-bulk-bar`).
- **★발견: sanction 백엔드 부재** — 프론트 `users_controller.sanction()`이 `POST /admin/users/{id}/sanction` 호출하나 **전 레포에 엔드포인트 없음**(실서버 404, 목 전용) → **벌크 sanction 제외**, bulk-approve+bulk-delete로 한정. (후속: sanction 백엔드 구현은 별개 기능.)
- **★교훈(중요): platform-svc 메인 워킹트리에 다른 세션의 미커밋 작업**(`feat/refresh-reuse-detection`의 `.gitignore` 변경)이 있어, **`git worktree add .wt-platform-bulk`로 완전 격리**해 무손상 진행 → 작업 후 `git worktree remove`. platform-svc 테스트 DB명 = **`devpath`**.

## D. 서식 텍스트 에디터 (🟡 spec 단계 — 다음 세션 구현)
- **brainstorming 완료**: 사용자가 **Approach B(진짜 WYSIWYG, flutter_quill+markdown_quill)** 선택(Approach A=마크다운 툴바+프리뷰는 폴백). 저장은 **Delta→마크다운 변환**으로 **기존 `bodyMd` 계약·`DpMarkdown` 렌더 불변**(백엔드/dp_core/shared 무변경).
- **spec 작성·커밋 완료**: `devpath-frontend/docs/superpowers/specs/2026-07-31-rich-text-editor-design.md`(브랜치 `feat/rich-text-editor`, 커밋 `9fc696a`, **origin push됨**). **사용자 spec 검토 대기 중이었음 → 다음 세션은 검토 확인 후 writing-plans→구현**.
- **패키지 API(Context7 확인)**: flutter_quill `QuillController.basic()`·`QuillSimpleToolbar(config: QuillSimpleToolbarConfig())`·`QuillEditor.basic(config: QuillEditorConfig())`·`controller.document.toDelta()`. markdown_quill `DeltaToMarkdown().convert(delta)`(저장)·`MarkdownToDelta(markdownDocument: md.Document(encodeHtml:false))`(편집 로드, 범위 외). `markdown` 패키지 필요.
- **⚠️ 최대 리스크 = 웹 한글 IME**: flutter_quill CanvasKit에서 한글 IME/전각 입력은 **브라우저 스모크(`flutter run -d chrome`)로 실측이 필수 AC**. **실패 시 폴백 = Approach A(마크다운 툴바+프리뷰)** — bodyMd 계약 동일이라 저비용 회귀.
- **⚠️ 버전 호환**: markdown_quill이 flutter_quill 최신을 못 따라갈 수 있음 → `flutter pub add` pub 해석 우선, 충돌 시 flutter_quill 핀.
- **위치**: `DpRichEditor`는 **apps/web**(flutter_quill 격리, admin/mobile 무부담). dp_design은 `DpMarkdown` 렌더만 유지.
- **작업 대상**: `apps/web/.../community/presentation/{post_create_page,question_create_page}.dart`의 body `TextField`(`_bodyCtrl`) → `QuillController`+`DpRichEditor` 교체. `_submit`이 `quillToMarkdown(controller)`로 md 산출. **기존 `post_create_page_test`·`question_create_page_test`가 "본문 (Markdown)" TextField 의존 → QuillEditor 기반으로 갱신 필요**. 툴바는 마크다운 표현 범위만(색/폰트 비활성 → 무손실).

## 이번 세션 기술 교훈 (재사용)
- **핸드오프는 실제 코드보다 뒤처질 수 있음** → 착수 전 반드시 실측(A의 DpKpiCard trend 슬롯 오류).
- **로컬 백엔드 테스트 레시피**: postgres 미기동 → `docker run -d --name dpa-test-pg -e POSTGRES_USER=devpath -e POSTGRES_PASSWORD=localdev -e POSTGRES_DB=devpath -p 5432:5432 pgvector/pgvector:pg16`(마이그레이션이 `CREATE EXTENSION vector` 요구 → 바 postgres 불가). **서비스별 테스트 DB명 상이**: learning-svc=`devpath`·community-svc=`devpath_citest`(별도 `createdb` 필요)·platform-svc=`devpath`. `@SpringBootTest`는 Kafka/Redis 미기동에도 컨텍스트 기동(연결 tolerant). learning-svc 전체 스위트 3건(`ClaimControllerTest`·`GuestAssessmentControllerTest`·`SecurityConfigTest`=health503·guest409)은 **base 커밋서도 동일 실패**하는 로컬 Redis/Kafka 부재 환경 이슈(회귀 아님, CI green). 회귀 판별 = base detached checkout 후 동일 클래스 실행.
- **다른 세션 미커밋 작업 회피 = git worktree**(platform-svc). 인접 레포 스팟체크(다른 세션 워킹트리 무손상 확인)를 매 작업 종료 시 수행.
- **Edit 도구 결과 "updated successfully"가 권위 신호**. 인라인 실행 중 PostToolUse hook이 "Edit operation failed"로 **오발화하는 사례 다수** → 무시하고 **테스트 컴파일/통과로 검증**(실제 전부 정상 적용됨).
- **melos `format`은 `--set-exit-if-changed`** → 미포맷 시 FAILED(정상). 매 커밋 전 확인. 생성파일(freezed/.g)은 tracked → 커밋 대상.
- **도구 호출 간 cwd 리셋** 발생 → gradle/flutter는 `cd <경로> &&` 프리픽스, git은 `git -C <절대경로>`.

## 레포/브랜치 상태 (세션 종료 시점)
- **frontend**: `develop`=`2c325ae`(A·B·C). D 브랜치 `feat/rich-text-editor`(spec `9fc696a`) origin push됨.
- **learning-svc**: `develop`=`7e374be`(A). 메인 워킹트리 develop(untracked `.jqwik-database`·`.omc/` 잔재 — 무관).
- **community-svc**: `develop`=`69ba67e`(B).
- **platform-svc**: `develop`에 `8caf083`(C, 머지). **메인 워킹트리는 다른 세션 `feat/refresh-reuse-detection`(미커밋 `.gitignore`·`.omc/`) — 건드리지 말 것**. C용 worktree는 제거 완료.
- **documents**: 이 핸드오프 브랜치. (이전 세션 `docs/handoff-2026-07-31-contract-expansion`은 별개 — 미머지일 수 있음.)

## 다음 세션 착수 (D 이어가기)
1. `git -C devpath-frontend fetch && git checkout feat/rich-text-editor`(spec `9fc696a` 보유).
2. 사용자에게 spec 검토 확인 → **writing-plans**로 구현 플랜 작성 → **executing-plans(인라인)**.
3. **패키지 도입 먼저**(`cd apps/web && flutter pub add flutter_quill markdown_quill markdown` → 버전 실측·리포트) → `quillToMarkdown` 헬퍼+단위테스트 → `DpRichEditor`(제약 툴바) → post/question 작성화면 통합+테스트 갱신 → **브라우저 한글 IME 스모크(필수 AC)**.
4. IME 실패 시 **폴백 A**(마크다운 툴바+프리뷰)로 전환(spec §6 Fork 3).
- 참조: 로드맵 메모리 [[devpath-uiux-elevation-roadmap]](A·B·C 머지·D spec 기록), spec `2026-07-31-rich-text-editor-design.md`.
