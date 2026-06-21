# MD2 슬라이스 #4 빌드 E — devpath-frontend 콘텐츠 뷰어 진척 연동 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **✅ 구현 완료(2026-06-21):** 본 플랜은 `devpath-frontend`에서 실행 완료됐다 — 커밋 `90d26e1` "feat: MD2 slice4 content progress web flow" (PR #23 → develop 머지, merge commit `8345462`). 변경 17파일은 본 플랜 File Structure 범위 내(`dp_core` `LearningContent` 모델 + `apps/web` content feature + `path_plan_view` + 테스트), CI `analyze-test`(`melos run analyze`+`test`) 녹색, **무관 generated 노이즈 미포함**(Risk 경고 준수). 구현은 본 플랜과 정합 — `ContentProgress.completedAt: String?`, `ContentLoaded(LearningContent content)`, `path_plan_view`의 `task.contentSlug ?? task.contentId?.toString()` onTap 라우팅 확인. 따라서 아래 "Current source alignment"의 *실행 전* 기술(ContentController가 markdown만 읽음·PathPlanView onTap 없음)은 **이미 해소됨**.

**Goal:** web 앱에서 Path task 클릭 -> `/content/:idOrSlug` 진입 -> 콘텐츠 상세 로드 -> scroll/dwell progress POST -> 완료 시 Path/Dashboard refresh 흐름을 완성한다.

**Architecture:** `dp_core`에 `LearningContent`/`ContentProgress` 모델을 추가하고, web `ContentController`가 전체 API 응답을 파싱한다. `ContentPage`는 `ScrollController`와 dwell timer로 누적 progress를 계산하고 throttled POST를 보낸다. Path task는 `contentSlug ?? contentId`가 있으면 콘텐츠로 이동한다. 완료 응답을 받으면 path/dashboard controller를 재로딩한다.

**Tech Stack:** Flutter · Riverpod Notifier · go_router · dp_core Freezed/json_serializable · dp_design · flutter_test.

## Global Constraints

- 범위는 `apps/web` + 필요한 `packages/dp_core` 모델만이다. backend/gateway는 C/D 선행.
- 기존 `/content/:id` route는 유지하고 idOrSlug 모두 허용한다.
- 앱은 dio를 직접 만지지 않고 `ApiClient`만 사용한다.
- text overflow/레이아웃 이동 없이 모바일/데스크톱 모두 동작해야 한다.
- progress request는 누적값이다. delta가 아니다.
- 목 fixture는 실 API 계약과 동일한 camelCase를 사용한다.

---

## File Structure

- Create: `packages/dp_core/lib/src/models/learning_content.dart`
- Generated: `learning_content.freezed.dart`, `learning_content.g.dart`
- Modify: `packages/dp_core/lib/dp_core.dart`
- Create: `packages/dp_core/test/models/learning_content_test.dart`
- Modify: `apps/web/lib/src/features/content/state/content_state.dart`
- Modify: `apps/web/lib/src/features/content/application/content_controller.dart`
- Modify: `apps/web/lib/src/features/content/presentation/content_page.dart`
- Modify: `apps/web/lib/src/features/path/presentation/path_plan_view.dart`
- Modify: `apps/web/lib/src/data/web_mock_fixtures.dart`
- Modify: tests under `apps/web/test/features/content/**`, `path/**`, dashboard/path smoke if needed

---

## Task 0: 브랜치와 codegen 상태 확인

```powershell
cd devpath-frontend
git switch develop
git pull
git switch -c feat/slice4-content-progress-web
git status --short --branch
```

현재 generated `*.g.dart`/`*.freezed.dart` dirty가 있으면 사용자/타 세션 변경으로 간주하고, 본 빌드가 건드리는 generated 파일만 명확히 재생성한다.

---

## Task 1: dp_core LearningContent 모델

**Files:**
- Create: `packages/dp_core/lib/src/models/learning_content.dart`
- Modify: `packages/dp_core/lib/dp_core.dart`
- Create: `packages/dp_core/test/models/learning_content_test.dart`

- [ ] **Step 1: 실패 테스트**

JSON contract:

```json
{
  "id": 1,
  "slug": "backend-spring-transaction-boundary",
  "title": "스프링 트랜잭션 경계 잡기",
  "track": "BACKEND_SPRING",
  "markdown": "## ...",
  "estimatedMinutes": 8,
  "difficulty": 0.5,
  "bloomLevel": "APPLY",
  "conceptTags": ["spring-tx"],
  "progress": {
    "scrollPct": 0.42,
    "dwellSec": 73,
    "completed": false,
    "completedAt": null
  }
}
```

- [ ] **Step 2: 모델 구현**

`LearningContent`, `ContentProgress`, `ContentProgressUpdateResponse`를 추가한다. `completedAt`은 **`String?`로 둔다** — 현재 dp_core 모델은 타임스탬프를 `DateTime`으로 들지 않고 ISO 문자열 그대로 보관하는 관례다(`grep -r DateTime packages/dp_core/lib/src/models` 0건 확인). 표시 포맷이 필요하면 표시 시점에서 파싱한다. 나머지 필드 타입은 빌드 C 응답(§6.1)과 동일한 camelCase: `id:int, slug:String, title:String, track:String, markdown:String, estimatedMinutes:int?, difficulty:double?, bloomLevel:String?, conceptTags:List<String>, progress:ContentProgress`.

- [ ] **Step 3: codegen**

```powershell
dart run build_runner build --delete-conflicting-outputs
dart format packages/dp_core/lib/src/models/learning_content.dart packages/dp_core/test/models/learning_content_test.dart
```

---

## Task 2: ContentController가 전체 응답과 progress POST를 다룸

**Files:**
- Modify: `content_state.dart`
- Modify: `content_controller.dart`
- Modify: `content_controller_test.dart`

- [ ] **Step 1: 실패 테스트**

테스트:

- `load('future-async-await')` 후 `ContentLoaded.content.markdown` 렌더 가능.
- response의 title/progress도 state에 들어감.
- `reportProgress`가 `POST /contents/{id}/progress`로 body `{scrollPct,dwellSec}` 전송.
- 완료 응답이면 `completed=true`를 반영.
- API failure는 `ContentFailed`.

- [ ] **Step 2: state 변경**

`ContentLoaded`는 markdown string 대신 `LearningContent content`를 가진다.

- [ ] **Step 3: controller 구현**

메서드:

```dart
Future<void> load(String idOrSlug)
Future<ContentProgressUpdateResponse?> reportProgress({
  required String idOrSlug,
  required double scrollPct,
  required int dwellSec,
})
```

POST 성공 후 현재 loaded content의 progress를 monotonic하게 갱신한다.

---

## Task 3: progress tracking 순수 로직

**Files:**
- Create: `apps/web/lib/src/features/content/application/content_progress_tracker.dart`
- Create: `apps/web/test/features/content/content_progress_tracker_test.dart`

- [ ] **Step 1: tracker 테스트**

조건:

- 최초 렌더 후 5초 전에는 flush하지 않음.
- scrollPct가 마지막 전송 대비 0.1 이상 증가하면 flush.
- 완료 임계값(0.8 + 45s) 도달 시 flush.
- dispose 시 마지막 값 flush.
- 이미 completed면 추가 flush하지 않음.

- [ ] **Step 2: tracker 구현**

UI timer와 분리된 순수 클래스로 구현해 widget test 타이밍 민감도를 줄인다.

---

## Task 4: ContentPage UI/flush 연동

**Files:**
- Modify: `content_page.dart`
- Create or Modify: `content_page_test.dart`

- [ ] **Step 1: UI 테스트**

테스트:

- title, estimated minutes, progress 상태, markdown 렌더.
- scroll 후 progress controller가 호출됨.
- retry button reloads.
- "실습" button remains `/sandbox`.

- [ ] **Step 2: 구현**

`ScrollController`와 `Timer.periodic(Duration(seconds: 1))`로 dwellSec 누적. 실제 POST 조건은 `ContentProgressTracker`에 위임한다.

dispose에서 flush한다. 브라우저 visibility hidden은 Flutter web 테스트가 까다로우므로, E에서는 dispose flush와 threshold flush를 우선 구현하고 visibility hidden도 가능하면 `WidgetsBindingObserver.didChangeAppLifecycleState`로 처리한다.

- [ ] **Step 3: 완료 후 refresh**

progress POST 응답 `completed=true`면:

```dart
await ref.read(pathControllerProvider.notifier).loadOrStart();
await ref.read(dashboardControllerProvider.notifier).load();
```

현재 화면 state는 유지한다.

---

## Task 5: Path task 클릭 라우팅

**Files:**
- Modify: `path_plan_view.dart`
- Modify: `path_plan_view_test.dart`

- [ ] **Step 1: 실패 테스트**

`WeeklyTask(contentSlug: 'future', contentId: 1)`를 tap하면 `/content/future`로 이동한다.

`contentSlug == null && contentId == 3`이면 `/content/3`.

둘 다 없으면 disabled/no navigation.

- [ ] **Step 2: 구현**

`ListTile.onTap`:

```dart
final target = t.contentSlug ?? t.contentId?.toString();
if (target != null) context.go('/content/$target');
```

필요하면 `go_router` import 추가.

---

## Task 6: mock fixtures 실계약 정합

**Files:**
- Modify: `web_mock_fixtures.dart`

- [ ] **Step 1: content fixture 확장**

기존 `GET /contents/c1` markdown-only fixture를 실 API 형태로 교체하고, path mock의 slug와 맞춘다.

필수:

- `GET /contents/future-async-await`
- `GET /contents/stream-subscription`
- `POST /contents/future-async-await/progress`

응답은 C API와 동일한 camelCase.

- [ ] **Step 2: smoke 유지**

기존 content controller test가 새 fixture로 통과해야 한다. mock path task slug와 content fixture slug가 어긋나면 E2E smoke가 깨진다.

---

## Task 7: 통합 smoke

**Files:**
- Create or Modify: `apps/web/test/content_progress_smoke_test.dart`

- [ ] **Step 1: path -> content -> progress 흐름**

ProviderScope + router에서:

1. `/path` 로드.
2. 첫 task tap.
3. `/content/future-async-await` 진입.
4. markdown 렌더.
5. progress threshold를 controller/test hook으로 충족.
6. path/dashboard reload가 호출되거나 최소 POST fixture가 소비됨을 검증.

- [ ] **Step 2: error path**

`GET /contents/missing` mock 404를 넣고 retry UI가 보이는지 확인한다.

---

## Task 8: 검증

- [ ] **Step 1: codegen/format**

```powershell
dart run build_runner build --delete-conflicting-outputs
dart format packages/dp_core apps/web
```

- [ ] **Step 2: focused tests (단일 패키지)**

> **검수 반영:** 이 레포의 melos 7 스크립트는 루트 `pubspec.yaml`의 `melos.scripts`에 `analyze`/`test`/`format`/`fix`로 정의돼 있고 **`melos run <script>`**로 실행한다(`melos test`/`melos analyze`라는 명령은 없음). `test` 스크립트는 이미 `flutter test --exclude-tags golden`라 `--run-skipped`/`--scope`는 쓰지 않는다. 특정 패키지만 돌리려면 `melos exec --scope`를 쓴다. 웹 앱 패키지명은 `devpath_web`(`apps/web/pubspec.yaml`).

```powershell
# dp_core(순수 Dart)만
dart pub global run melos exec --scope="dp_core" -- dart test
# web(Flutter)만
dart pub global run melos exec --scope="devpath_web" -- flutter test --exclude-tags golden
```

- [ ] **Step 3: full analyze/test (전 패키지, CI 게이트와 동일)**

```powershell
dart pub global run melos run analyze
dart pub global run melos run test
```

melos가 PATH에 있으면 `melos run analyze` / `melos run test`로 바로 호출한다. 위젯/로직 테스트는 golden 태그 없이 작성한다(`melos run test`가 golden을 제외하므로).

- [ ] **Step 4: build web**

```powershell
cd apps/web
flutter build web
```

---

## Task 9: develop PR

```powershell
git push -u origin feat/slice4-content-progress-web
gh pr create --base develop --title "feat: MD2 slice4 content progress web flow" --body "Adds content API model, progress tracking, task navigation, and mock fixtures."
```

## Acceptance Checklist

- [ ] `LearningContent`/`ContentProgress` dp_core model exists and is exported.
- [ ] ContentController parses full API response.
- [ ] ContentPage shows title/meta/progress + markdown.
- [ ] progress POST sends cumulative `scrollPct`/`dwellSec`.
- [ ] completed progress refreshes Path/Dashboard.
- [ ] Path task click routes to contentSlug or contentId.
- [ ] mock fixtures match backend C contract.
- [ ] `melos analyze`, `melos test`, and `flutter build web` pass.

## Self-Review

- **Spec coverage:** 설계서 §10.3 frontend and §11.5 tests를 커버한다.
- **Current source alignment:** current ContentController only reads `markdown`; current PathPlanView has no onTap. This plan targets those exact gaps.
- **Risk:** generated dp_core files are already dirty in the workspace. Implementation must avoid overwriting unrelated generated changes without checking diff.
