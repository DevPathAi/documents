# 슬라이스 #3 빌드 E — gateway 라우트 + Flutter frontend 학습경로 실API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `devpath-gateway`에 `/learning-paths/**` → learning-svc 라우트를 추가하고, `devpath-frontend` Flutter Web의 PATH 생성/결과 화면을 실계약(`stage` SSE + `milestones` 응답)으로 전환한다.

**Architecture:** 빌드 C learning-svc가 path API와 SSE를 소유한다. gateway는 bare path(`/learning-paths/**`)를 learning-svc로 프록시하고 JWT 엣지 검증을 유지한다. frontend는 기존 목 와이어(`step`, `fromStep`, `weeks`, "이어서 생성")를 제거하고, `PathSseEvent(stage/progress/message/pathId)`, 새 `LearningPath(pathId/track/totalWeeks/diagnosis/milestones/tasks)` 모델, 중단 시 "다시 생성" UX로 깨지는 마이그레이션을 수행한다.

**Tech Stack:** (gateway) Spring Boot 4.0.7 · Spring Cloud Gateway WebFlux · WebTestClient. (frontend) Flutter Web · Dart pub workspaces/melos 7 · dp_core(freezed/json_serializable) · flutter_riverpod · dio ApiClient/SSE · go_router · dp_design.

## Global Constraints

- 각 레포 절대조건: 추측 금지 · **테스트 우선** · 문제 시 코드 분석.
- 브랜치: 각 레포 `develop` 기준 작업 브랜치 → develop PR. `main` 직접 금지.
- **범위:** 빌드 E만 수행한다. learning-svc API 구현(C), platform DONE 소비(D)는 범위 밖이다.
- **상류 계약 재검증 게이트:** 구현 전 learning-svc 실소스의 `LearningPathController`, `LearningPathView`, `MilestoneView`, `WeeklyTaskView`, `ThisWeekView`, `PathProgressEvent`를 다시 읽고 본 플랜 계약과 비교한다. 불일치 시 플랜 후속 task를 실제 코드 기준으로 정정한다.
- **API prefix:** 슬라이스 #1/#2/#3 설계 확정대로 bare path 유지. frontend baseUrl은 gateway root를 가리키며 `/api/v1`를 붙이지 않는다.
- **SSE 계약:** learning-svc는 `event: progress`, `data: {"stage":"collecting|generating|matching|done|error","progress":0.0~1.0,"message":"...","pathId":...}`를 보낸다. frontend는 `event` 이름보다 data의 `stage`를 기준으로 처리한다.
- **재개 정책:** 서버측 partial resume 없음. `fromStep` 전송 금지. 중단/timeout 시 사용자는 "다시 생성"을 누르고 `POST /learning-paths/me/generate`를 처음부터 호출한다. 생성 완료 후 `GET /learning-paths/me`를 조회한다.
- **frontend 테스트:** 모델 변경은 실패 테스트 작성 → 구현 → `dart run build_runner build --delete-conflicting-outputs` → focused test → `melos run analyze`·`melos run test`.

---

## Current Contract Snapshot (2026-06-20 실소스 확인)

- learning-svc controller:
  - `POST /learning-paths/me/generate` produces `text/event-stream`
  - `POST /learning-paths/me/regenerate` returns `{ "pathId": long }`
  - `GET /learning-paths/me` returns `LearningPathView`
  - `GET /learning-paths/me/this-week` returns `ThisWeekView`
  - `GET /learning-paths/{id}/rationale` returns `RationaleView`
- `LearningPathView`: `pathId`, `track`, `totalWeeks`, `rationale`, `diagnosis`, `milestones`
- `DiagnosisView`: `diagnosedLevel`, `strengthConcepts`, `weaknessConcepts`
- `MilestoneView`: `weekNum`, `title`, `goalDescription`, `targetSkills`, `estimatedHours`, `whyThisOrder`, `expectedOutcome`, `locked`, `tasks`
- `WeeklyTaskView`: `orderNum`, `taskType`, `title`, `required`, `contentId`, `contentSlug`, `completed`
- `PathProgressEvent`: `stage`, `progress`, `message`, `pathId`
- gateway currently routes platform and `/onboarding/assessments/**`; `/learning-paths/**` is missing.
- frontend currently uses `step/fromStep/weeks` and partial "이어서 생성"; this is the main breaking migration.

---

## File Structure (gateway)

- Modify: `devpath-gateway/src/main/resources/application.yml`
- Create: `devpath-gateway/src/test/java/ai/devpath/gateway/LearningPathRouteTest.java`
- Optional modify: `devpath-gateway/src/main/java/ai/devpath/gateway/config/GatewaySecurityConfig.java` only if tests reveal path-specific security behavior is needed. Default is authenticated by `anyExchange()`.

## File Structure (frontend)

- Modify: `devpath-frontend/packages/dp_core/lib/src/models/learning_path.dart`
- Modify generated: `learning_path.freezed.dart`, `learning_path.g.dart`
- Create: `devpath-frontend/packages/dp_core/lib/src/models/path_sse_event.dart`
- Modify: `devpath-frontend/packages/dp_core/lib/dp_core.dart`
- Modify or Create tests:
  - `packages/dp_core/test/models/learning_path_test.dart`
  - `packages/dp_core/test/models/path_sse_event_test.dart`
  - `packages/dp_core/test/mock/mock_test.dart`
  - `apps/web/test/features/path/path_sse_source_test.dart`
  - `apps/web/test/features/path/path_controller_test.dart`
  - `apps/web/test/features/path/path_page_test.dart`
  - `apps/web/test/features/path/path_plan_view_test.dart`
  - `apps/web/test/golden_path_onboarding_test.dart`
- Modify:
  - `packages/dp_core/lib/src/mock/mock_sse_source.dart`
  - `apps/web/lib/src/data/web_mock_fixtures.dart`
  - `apps/web/lib/src/features/path/data/path_sse_source.dart`
  - `apps/web/lib/src/features/path/application/path_controller.dart`
  - `apps/web/lib/src/features/path/presentation/path_page.dart`
  - `apps/web/lib/src/features/path/presentation/path_plan_view.dart`

---

## Task 0: 상류 계약 재검증 (코드 변경 없음)

- [ ] **Step 1: learning-svc 계약 파일 재확인**

Read:
- `devpath-learning-svc/src/main/java/ai/devpath/learning/path/LearningPathController.java`
- `LearningPathView.java`
- `MilestoneView.java`
- `WeeklyTaskView.java`
- `ThisWeekView.java`
- `PathProgressEvent.java`

Expected: Current Contract Snapshot과 일치. 불일치 시 본 플랜의 DTO/test fixture를 실소스 기준으로 수정 후 진행.

- [ ] **Step 2: frontend 현재 결합 지점 확인**

Read:
- `packages/dp_core/lib/src/models/learning_path.dart`
- `packages/dp_core/lib/src/mock/mock_sse_source.dart`
- `apps/web/lib/src/features/path/data/path_sse_source.dart`
- `apps/web/lib/src/features/path/application/path_controller.dart`
- `apps/web/lib/src/features/path/presentation/path_plan_view.dart`
- `apps/web/lib/src/features/path/presentation/path_page.dart`

Expected: `weeks`, `step`, `fromStep`, `resume`, "이어서 생성" 제거 대상 목록 확정.

---

## Task 1: gateway — `/learning-paths/**` 라우트와 인증

**Files:**
- Create: `src/test/java/ai/devpath/gateway/LearningPathRouteTest.java`
- Modify: `src/main/resources/application.yml`

**Interfaces:**
- Produces route id `learning-paths` or extends existing `learning` route.
- `Path=/learning-paths/**` → `${LEARNING_URI:http://localhost:8082}`.
- All `/learning-paths/**` paths require JWT at gateway edge.
- SSE response must not be blocked by security/CORS; route should preserve `text/event-stream`.

- [ ] **Step 1: failing route/security tests 작성**

`LearningPathRouteTest.java`:
- unauthenticated `GET /learning-paths/me` → 401
- unauthenticated `POST /learning-paths/me/generate` → 401
- authenticated `GET /learning-paths/me` is not 401/403 even if upstream is unavailable

Implementation hint: use `@SpringBootTest(webEnvironment = RANDOM_PORT)` + WebTestClient. Authenticated case can use a locally signed HS256 JWT matching test `JWT_SECRET`, or `SecurityMockServerConfigurers.mockJwt()` if gateway test stack already supports it.

- [ ] **Step 2: 실패 확인**

```powershell
cd devpath-gateway
.\gradlew.bat test --tests ai.devpath.gateway.LearningPathRouteTest
```

Expected: authenticated route test fails because route is missing, while unauthenticated checks remain 401.

- [ ] **Step 3: route 추가**

`src/main/resources/application.yml`:

```yaml
            - id: learning-paths
              uri: ${LEARNING_URI:http://localhost:8082}
              predicates:
                - Path=/learning-paths/**
```

If keeping one learning route is cleaner, use:

```yaml
            - id: learning
              uri: ${LEARNING_URI:http://localhost:8082}
              predicates:
                - Path=/onboarding/assessments/**,/learning-paths/**
```

- [ ] **Step 4: focused tests 통과**

```powershell
cd devpath-gateway
.\gradlew.bat test --tests ai.devpath.gateway.LearningPathRouteTest
```

- [ ] **Step 5: full gateway test**

```powershell
cd devpath-gateway
.\gradlew.bat test
```

---

## Task 2: dp_core — `PathSseEvent` DTO 추가

**Files:**
- Create: `packages/dp_core/lib/src/models/path_sse_event.dart`
- Modify: `packages/dp_core/lib/dp_core.dart`
- Create: `packages/dp_core/test/models/path_sse_event_test.dart`

**Interfaces:**

```dart
@freezed
abstract class PathSseEvent with _$PathSseEvent {
  const factory PathSseEvent({
    required String stage,
    required double progress,
    required String message,
    int? pathId,
  }) = _PathSseEvent;
}
```

- [ ] **Step 1: failing DTO tests 작성**

Test JSON parsing:
- collecting without `pathId`
- done with `pathId`
- error stage with message

- [ ] **Step 2: DTO 구현 + barrel export**

Add `part` files and export from `dp_core.dart`.

- [ ] **Step 3: codegen**

```powershell
cd devpath-frontend
dart run build_runner build --delete-conflicting-outputs
```

- [ ] **Step 4: focused test**

```powershell
cd devpath-frontend\packages\dp_core
dart test test/models/path_sse_event_test.dart
```

---

## Task 3: dp_core — `LearningPath` 모델을 `milestones` 계약으로 재생성

**Files:**
- Modify: `packages/dp_core/lib/src/models/learning_path.dart`
- Modify generated: `learning_path.freezed.dart`, `learning_path.g.dart`
- Modify: `packages/dp_core/test/models/learning_path_test.dart`

**Interfaces:**
- `LearningPath(pathId, track, totalWeeks, rationale, diagnosis?, milestones)`
- `PathDiagnosis(diagnosedLevel, strengthConcepts, weaknessConcepts)`
- `PathMilestone(weekNum, title, goalDescription, targetSkills, estimatedHours, whyThisOrder, expectedOutcome, locked, tasks)`
- `WeeklyTask(orderNum, taskType, title, required, contentId?, contentSlug?, completed)`

- [ ] **Step 1: failing model test 작성**

Use a fixture matching learning-svc `GET /learning-paths/me`, including:
- `pathId`
- `diagnosis.strengthConcepts`
- first milestone `expectedOutcome`
- first milestone exactly 3 tasks
- nullable `contentId/contentSlug`

Also update the old `weeks` test so it no longer expects `weeks`.

- [ ] **Step 2: model 구현**

Replace `PathWeek` with milestone/diagnosis structures. Keep class name `WeeklyTask` if convenient, but update fields to the server contract.

- [ ] **Step 3: codegen**

```powershell
cd devpath-frontend
dart run build_runner build --delete-conflicting-outputs
```

- [ ] **Step 4: focused test**

```powershell
cd devpath-frontend\packages\dp_core
dart test test/models/learning_path_test.dart
```

---

## Task 4: dp_core mock SSE — remove `fromStep`, emit `stage`

**Files:**
- Modify: `packages/dp_core/lib/src/mock/mock_sse_source.dart`
- Modify: `packages/dp_core/test/mock/mock_test.dart`

**Interfaces:**
- mock emits JSON data shaped like `PathSseEvent`.
- no `fromStep` constructor argument.
- stages should use server names: `collecting`, `generating`, `matching`, `done`.

- [ ] **Step 1: failing tests 정리**

Replace old "fromStep으로 이어한다" test with:
- emits all stages in order from the beginning
- `failAfter` injects network failure
- done event includes `pathId`

- [ ] **Step 2: implementation**

`MockSseSource.stream()` should yield:

```dart
SseEvent(
  event: 'progress',
  data: '{"stage":"collecting","progress":0.15,"message":"진단 결과를 분석하고 있어요.","pathId":null}',
)
```

Use `jsonEncode` instead of manual interpolation.

- [ ] **Step 3: focused test**

```powershell
cd devpath-frontend\packages\dp_core
dart test test/mock/mock_test.dart
```

---

## Task 5: web path SSE source — remove request body `fromStep`

**Files:**
- Modify: `apps/web/lib/src/features/path/data/path_sse_source.dart`
- Modify: `apps/web/test/features/path/path_sse_source_test.dart`

**Interfaces:**
- `typedef PathSseConnect = Stream<SseEvent> Function();`
- mock uses new `MockSseSource(stages: kPathStages, ...)`.
- real call: `apiClient.sse('/learning-paths/me/generate')` with no `body` unless `goal` is later introduced.

- [ ] **Step 1: failing test 작성**

Assert:
- provider returns stream with `stage` data
- no test references `fromStep`

If ApiClient can be faked, assert real source does not send `{'fromStep': ...}`.

- [ ] **Step 2: implementation**

Replace:

```dart
typedef PathSseConnect = Stream<SseEvent> Function({int fromStep});
```

with:

```dart
typedef PathSseConnect = Stream<SseEvent> Function();
```

Replace `kSseSteps` with:

```dart
const kPathStages = ['collecting', 'generating', 'matching', 'done'];
const kPathStageLabels = ['진단 분석', '경로 생성', '콘텐츠 매칭'];
```

- [ ] **Step 3: focused test**

```powershell
cd devpath-frontend\apps\web
flutter test test/features/path/path_sse_source_test.dart
```

---

## Task 6: PathController — parse `stage`, remove resume, regenerate from start

**Files:**
- Modify: `apps/web/lib/src/features/path/application/path_controller.dart`
- Modify: `apps/web/test/features/path/path_controller_test.dart`

**Interfaces:**
- `start()` starts from scratch.
- `restart()` or `regenerate()` starts from scratch after partial/error. It does not pass a cursor.
- `resume()` removed.
- Parses `PathSseEvent.fromJson(jsonDecode(event.data))`.
- `done` loads `GET /learning-paths/me`.
- `error` stage transitions to failed with server message.
- timeout/network during stream transitions to partial with CTA "다시 생성".

- [ ] **Step 1: failing controller tests 작성**

Cases:
- normal `collecting -> generating -> matching -> done` loads `LearningPath` with `milestones`.
- stream error after `generating` sets `partial`, preserves completed labels, and second `start()` replays from the beginning.
- server `stage:error` sets `failed`.
- old `step` event is ignored or fails safely without completing.

- [ ] **Step 2: implementation**

Remove `fromStep` parameters and `resume()`. Add a private parser:

```dart
PathSseEvent? _eventOf(String data) { ... }
```

Stage mapping:
- `collecting` → completed first label, current second
- `generating` → completed first two labels, current third
- `matching` → completed all three labels, current null
- `done` → load result
- `error` → failed

- [ ] **Step 3: focused test**

```powershell
cd devpath-frontend\apps\web
flutter test test/features/path/path_controller_test.dart
```

---

## Task 7: PathPage — partial CTA becomes "다시 생성"

**Files:**
- Modify: `apps/web/lib/src/features/path/presentation/path_page.dart`
- Modify: `apps/web/test/features/path/path_page_test.dart`

**Interfaces:**
- Partial state button calls `notifier.start` (or `restart`) from scratch.
- Button text: `다시 생성`.
- No "이어서 생성" remains in path feature tests/source.

- [ ] **Step 1: failing widget test 작성**

Update partial test:
- expects `다시 생성`
- taps it and verifies provider connect starts a fresh stream
- does not reference `resume`

- [ ] **Step 2: implementation**

Rename `_Progress.onResume` to `_Progress.onRestart` and button copy to `다시 생성`.

- [ ] **Step 3: focused test**

```powershell
cd devpath-frontend\apps\web
flutter test test/features/path/path_page_test.dart
```

---

## Task 8: PathPlanView — render O05 from `milestones`

**Files:**
- Modify: `apps/web/lib/src/features/path/presentation/path_plan_view.dart`
- Create or Modify: `apps/web/test/features/path/path_plan_view_test.dart`

**Interfaces:**
- Shows rationale.
- Shows diagnosis strengths/weaknesses if present.
- Shows first unlocked milestone as "이번 주 과제" with 3 tasks.
- Shows task type/required/completed status.
- Shows 12-week roadmap from `milestones`.
- Shows `expectedOutcome` and `whyThisOrder` without inventing copy.
- Locked milestones are visually distinguishable but still readable.

- [ ] **Step 1: failing widget test 작성**

Fixture should assert visible text:
- `diagnosedLevel`
- one strength and one weakness
- first milestone `expectedOutcome`
- 3 task titles
- locked week title

- [ ] **Step 2: implementation**

Replace all `plan.weeks` usage with `plan.milestones`.

Design constraints:
- Avoid nested cards. Existing `Container` rationale block is acceptable as a single framed content block, but do not wrap every section in heavy cards.
- Keep dense, scannable layout for repeated learning tasks.
- Text must fit mobile widths; long concept tags should wrap.

- [ ] **Step 3: focused test**

```powershell
cd devpath-frontend\apps\web
flutter test test/features/path/path_plan_view_test.dart
```

---

## Task 9: Mock fixtures and golden path onboarding tests

**Files:**
- Modify: `apps/web/lib/src/data/web_mock_fixtures.dart`
- Modify: `apps/web/test/golden_path_onboarding_test.dart`

**Interfaces:**
- `GET /learning-paths/me` mock returns the new `LearningPathView` contract.
- normal path golden uses `stage` SSE.
- interrupted path golden expects "다시 생성" and full restart, not resume.

- [ ] **Step 1: fixture update**

Replace:

```dart
'weeks': [...]
```

with:

```dart
'pathId': 101,
'track': 'BACKEND',
'totalWeeks': 12,
'diagnosis': {
  'diagnosedLevel': 'MID',
  'strengthConcepts': ['HTTP', '테스트'],
  'weaknessConcepts': ['비동기', '트랜잭션'],
},
'milestones': [...]
```

Ensure week 1 has exactly 3 tasks and an `expectedOutcome`.

- [ ] **Step 2: golden path tests update**

Rename old D2 from "이어서 생성" to "중단 후 다시 생성".

- [ ] **Step 3: focused tests**

```powershell
cd devpath-frontend\apps\web
flutter test test/golden_path_onboarding_test.dart
```

---

## Task 10: frontend regression sweep

- [ ] **Step 1: no stale path contract references**

```powershell
cd devpath-frontend
rg -n "fromStep|이어서 생성|\\bstep\\b|weeks|PathWeek" packages apps
```

Expected:
- no path feature references to `fromStep`, "이어서 생성", old `weeks`, or `PathWeek`.
- mentor feature may still use its own `fromStep`; do not change mentor in this build.

- [ ] **Step 2: focused path tests**

```powershell
cd devpath-frontend
flutter test apps/web/test/features/path
dart test packages/dp_core/test/models/learning_path_test.dart
dart test packages/dp_core/test/models/path_sse_event_test.dart
```

- [ ] **Step 3: full frontend checks**

```powershell
cd devpath-frontend
melos run analyze
melos run test
```

---

## Task 11: optional local end-to-end smoke

Run only after builds C and D are locally available and gateway route is implemented.

- [ ] **Step 1: start services**

Start platform, learning, gateway with matching `JWT_SECRET`, `LEARNING_URI`, and frontend `API_BASE_URL=http://localhost:8080`.

- [ ] **Step 2: browser smoke**

In Flutter web:
- complete diagnostic or seed a completed assessment
- enter `/path`
- observe SSE progress labels
- result loads from `GET /learning-paths/me`
- O05 sections show diagnosis, rationale, first week 3 tasks, roadmap

Record any manual verification notes in PR description.

---

## Acceptance Checklist

- [ ] gateway routes `/learning-paths/**` to learning-svc.
- [ ] gateway keeps `/learning-paths/**` authenticated.
- [ ] gateway tests cover unauthenticated 401 and authenticated route matching.
- [ ] frontend no longer sends `fromStep` for path generation.
- [ ] frontend parses `PathSseEvent.stage`.
- [ ] frontend handles `collecting/generating/matching/done/error`.
- [ ] partial/interrupted path UX says "다시 생성", not "이어서 생성".
- [ ] `LearningPath` dp_core model matches `GET /learning-paths/me`.
- [ ] `PathPlanView` renders `milestones`, diagnosis strengths/weaknesses, `expectedOutcome`, and first week 3 tasks.
- [ ] mock fixtures match the real learning-svc contract.
- [ ] focused tests and full repo checks pass.

---

## Self-Review

- **Spec coverage:** 설계서 §7/§8, §11-bis R-2/R-4/R-5, 빌드 분해 E를 커버한다.
- **Frontend stack fit:** Flutter Web + Dart workspaces + freezed/json_serializable + Riverpod controller 패턴을 유지한다.
- **Risk:** learning-svc SSE uses Spring MVC `SseEmitter` with `event: progress`. The existing `SseClient` must preserve named events and raw data; keep/extend `api_client_sse_test` if parsing differences appear.
- **Scope guard:** mentor SSE still has `fromStep`; this build only removes `fromStep` from path generation. Do not refactor mentor.
