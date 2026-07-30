# Handoff — 커뮤니티 하위 B(자유/피드백 웹) Task2~9 구현·검증·PR 2건 머지 완료 (2026-07-30)

> 앞선 [handoff-2026-07-29-community-subB-planned-task1-done.md](handoff-2026-07-29-community-subB-planned-task1-done.md)를 잇는다. 이전 세션이 하위 B의 spec/plan + Task1(백엔드) 구현까지 하고 Task2~9를 이관했다. **이번 세션은 Task2~9를 전부 구현·검증하고 PR-A·PR-B를 만들어 CI green 확인 후 사용자 지시로 둘 다 develop에 머지**했다.

## 이 세션 결과 (요약)

### 커뮤니티 하위 B — 완결 (Task 1~9 전부 develop 통합)
- **executing-plans로 Task2~9 전부 inline 실행**(서브에이전트 미사용 — 이전 세션 교훈: Windows 서브에이전트 return 신뢰 불가, [[devpath-windows-subagent-flakiness]]). 각 Task TDD(실패 테스트→구현→통과)·커밋.
- **PR-A = community-svc #29** (`feat/community-feed-summary`, base develop): `PostSummaryView` boardType+replyCount·전-보드 피드·`FeedMockMvcTest`. **CI build PASS(1m40s) → 머지**(develop `7d3b1b0`).
- **PR-B = frontend #89** (`feat/community-free-feedback-web`, base develop): 아래 Task2~9. **CI analyze-test PASS(2m44s) → 머지**(develop `6b9d13d`).
- 머지 순서 = PR-A(백엔드 계약) 선행 → PR-B. 로컬 develop 둘 다 ff 동기화·머지된 feature 브랜치 로컬 삭제 완료.

### PR-B 커밋 구성 (frontend, 10커밋)
- `docs(spec/plan)` 2 (이전 세션, rebase로 보존)
- **Task2** `feat(dp_core)`: `CommunityPostSummary`에 `boardType`+`replyCount`(`answerCount` 제거), 신규 `CommunityPostDetail`·`CommunityComment`, freezed 재생성
- **Task3** `feat(community)`: `postCreateProvider`·`postDetailFetchProvider`·`commentCreateProvider`
- **Task4** `feat(community)`: `CommunityBoard` enum(all/qna/free/feedback)·`CommunityState.board`·`selectBoard`
- **Task5** `feat(community)`: `PostDetailController`(family)·`PostDetailState`(댓글/추천)
- **Task6** `feat(community)`: 통합 피드 화면 — 필터칩·보드 뱃지·보드별 라우팅·FAB 스피드다이얼(질문/자유글/피드백)·목 픽스처 3보드 혼합
- **Task7** `feat(community)`: 일반 게시글 상세 화면 + 라우트 `/community/post/:id`
- **Task8** `feat(community)`: 일반 게시글 작성 화면 + 라우트 `/community/new/post?board=`
- **Task9** `style`: dart format 정합 + `.gitignore`에 `.gstack/` 추가

### 검증 (근거)
- **PR-B**: `melos analyze` 5패키지 0 issues · `melos format` clean(0 changed) · `melos test` **5패키지 전부 "All tests passed"(FAILED 0)** — 로컬 + GitHub CI 이중 확인.
- **PR-A**: 로컬 postgres 미기동(AWS 정지)으로 로컬 `./gradlew build` 불가 → **CI(postgres 서비스)에서 build PASS**로 검증. 초기 로컬 FeedMockMvcTest 실패는 순수 **DB 부재(ConnectException)** 였고 CI green으로 코드 정상 확증.

## ⚠️ 계획에서 벗어나 대응한 부분 (전부 검증 완료, 다음 세션 인지)

1. **riverpod 3.3.2엔 `FamilyNotifier`가 없다** — plan Task5는 `FamilyNotifier<State,Arg>`+`build(arg)`를 가정했으나 이 API는 riverpod 3.x에서 제거됨(컴파일 실패). 정답: class-based family notifier는 **`Notifier<State>`를 확장 + family 인자를 생성자로 받고**(`PostDetailController(this.postId)`) `build()`는 무인자, provider는 `NotifierProvider.family<Ctrl, State, int>(Ctrl.new)`. 근거=riverpod 3.3.2 `test/src/matrix/notifier_mixin.dart`의 `SyncFamily(this.arg)` 예제. → [[devpath-riverpod3-family-notifier]] 참조.
2. **공유 `dp_core` 모델 변경의 mobile 파급** — `CommunityPostSummary.answerCount`→`replyCount`가 web뿐 아니라 **mobile 앱**(`community_page.dart` + mock/test 픽스처)까지 컴파일 파급. plan은 web 참조만 명시했으나 `melos analyze`(전 패키지)가 mobile·dp_core dashboard_community_test까지 잡아냄 → 전 참조 갱신(값 보존 mechanical 리네임). **교훈: 공유 패키지 모델 필드 변경은 반드시 `melos analyze`(전 패키지)로 파급 전수 확인.**
3. **PR-B 브랜치 stale** — `feat/community-free-feedback-web`가 UI/UX Phase0/1 머지 **이전**에 분기돼 origin/develop 대비 17커밋 뒤처짐(spec/plan 2 doc커밋만 보유). origin/develop 위로 **rebase**(doc-only라 충돌 없이 replay). 이후 Task 구현.
4. **`.gstack/` 오커밋** — 이 브랜치엔 `.gstack/` gitignore가 없어 `git add -A`가 로컬 gstack 도구 파일을 포함시킴 → 커밋 amend로 제거 + `.gitignore`에 `.gstack/` 등록. **다음 세션: frontend 다른 브랜치에서도 `git add -A` 주의**(develop엔 이제 반영됨).

## 구현 세부 (다음 세션 참고)

- **통합 피드 라우팅**: QNA 항목 탭 → `/community/:id`(기존 QnaDetailPage), FREE/FEEDBACK → `/community/post/:id`(신규 PostDetailPage). router에서 `/community/post/:id`·`/community/new/post`를 `/community/:id`보다 **먼저** 선언.
- **FAB 스피드다이얼**: 기존 코드베이스에 showModalBottomSheet/MenuAnchor 선례 없어 `showModalBottomSheet` 채택(3항목 ListTile).
- **보드 뱃지**: `DpColors`에 `surfaceVariant` 없음 → `c.border` 배경 + `c.textSecondary` 텍스트로 대체.
- **소스 provider 테스트**: `test/support/fake_api_client.dart` 없음 → 기존 `lcs_source_test.dart` 패턴(`ApiClient.create`+`MockHttpAdapter(fixtures)`+`apiClientProvider` override) 승계. MockHttpAdapter는 요청 바디 미캡처 → 반환값+경로해석으로 검증.
- **PostDetailState**: qna의 sealed(QnaLoading/Loaded/Failed)와 달리 plain class(phase enum). 컨트롤러는 성공 액션 후 상세 재조회(qna 패턴 승계).

## ⏭ 다음 세션 착수 — ③ UI/UX Phase 2 (남은 유일 대형 워크스트림)

4이슈(①콘텐츠 ②멘토+커뮤니티 ③UI/UX) 중 **①②는 완결**, ③만 남음. 하위 B로 커뮤니티 기능이 완성됐으니 이후는 UI/UX 고도화.

- **로드맵**: [[devpath-uiux-elevation-roadmap]]. Phase 0(dp_design 토큰/인터랙션)·Phase 1(DpAppShell 4-클래스 반응형 셸 + DpCommandPalette Ctrl/Cmd+K·web/admin 이관) **이미 develop 머지 완료**(PR#86·#87·#88).
- **다음 = Phase 2(학습자 대시보드/홈)**: `DpKpiCard`+`fl_chart`·`flutter_staggered_grid_view`·`skeletonizer` 도입. spec/plan은 로드맵 §3 검증절차 따라 신규 작성.
- spec/plan(로드맵): `devpath-frontend/docs/superpowers/{specs,plans}/2026-07-30-*uiux*`.

## 로컬 환경 메모 (다음 세션 재현)

- **AWS 여전히 정지**(EC2 `i-09e252854566cc123`·RDS `devpath-pg` stopped, GPU 쿼터 증설 PENDING). 로컬 진행 유지.
- **로컬 postgres 미기동**(5432 리스닝 없음·docker 없음) — community-svc 백엔드 테스트는 로컬에서 `ConnectException`. 백엔드 검증은 **CI(postgres 서비스)에 의존**하거나, 필요 시 로컬 postgres/docker 기동 후 `devpath_citest` 생성.
- frontend 검증: 레포 루트에서 `dart pub global run melos run analyze`·`melos run test`·`melos run format`. 단일: `cd apps/web && flutter test test/<path>`.
- **cwd 리셋 주의**: Bash 도구는 호출 간 cwd가 리셋될 수 있음(직전 `cd`가 남지 않는 경우 관측) → git/파일 명령은 절대경로 또는 `-C <repo>`, flutter test는 명령 앞에 `cd <apps/web> &&`.
- 도구 호출 Bash만(PowerShell 금지, antml 프리픽스 버그 회피). `python`=Store 스텁 → `py`.

## 교훈 (이 세션)

- **plan의 API 가정은 실제 설치 버전으로 검증**(riverpod FamilyNotifier 부재) — plan Self-Review가 리스크로 짚었고, 실행자가 pub cache 소스를 읽어 정답 확정. 추측 금지 원칙의 실전.
- **공유 패키지 모델 변경은 전 소비 앱 파급** — `melos analyze`(전 패키지)를 컴파일 게이트로 삼아 web/mobile/dp_core 전수 확인.
- **stale feature 브랜치는 rebase 후 착수** — Phase0/1 이후 분기 안 된 브랜치는 최신 develop 위로 rebase(doc-only면 무충돌).
- **inline executing-plans가 Windows에선 SDD보다 단순·안정** — 컨트롤러가 어차피 전부 직접 검증하므로 서브에이전트 return 불확실성 제거.
