# 슬라이스 #6 빌드 E — frontend AI리뷰 폴링 전환 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** AI 리뷰 프론트를 **동기 mock에서 비동기 폴링 실API**로 전환한다: sandbox 실행 SSE에서 `sessionId`를 받아(빌드 B D-8), 실행 완료 후 `GET /reviews?sandboxSessionId={id}`를 상태가 `DONE/FAILED`로 수렴할 때까지 폴링해 `ReviewPanel`에 표시한다.

**Architecture:** `flutter_riverpod` Notifier 패턴. `RunController`가 SSE `session` 이벤트로 `sandboxSessionId`를 `RunDone`에 싣고, `ReviewController.pollForSession(id)`가 `apiClient.get`을 인터벌 폴링한다. 목 프로토는 `sandboxRunConnect`가 `session` 이벤트를, 목 픽스처가 `GET /reviews`를 제공한다. `CodeReview.id/status`(이미 선확보)를 활용.

**Tech Stack:** Flutter · Dart · Riverpod 3 · `dp_core`(ApiClient·CodeReview·SseEvent) · melos · flutter_test.

## Global Constraints

- 대상 레포: `devpath-frontend` 단독. 설계서 [2026-06-23-md2-slice6-ai-code-review-design](../specs/2026-06-23-md2-slice6-ai-code-review-design.md) D-8·§5(frontend).
- **빌드 B(SSE `session` 이벤트)·C1(폴링 API)·D(라우트) 머지 후 끝단간 실연동 가능**. 단 본 빌드는 목 픽스처로 독립 테스트 가능(실서버 불요).
- 기존 계약 재사용: `CodeReview{confidence,strengths,improvements,security,id?,status?}`·`ReviewIssue`(dp_core, 변경 없음), `ReviewState`(idle/loading/loaded/killSwitch/quota/failed).
- ⚠️ **상류 계약 재검증 게이트**(P4~P5 교훈): `dp_core` `ApiClient`의 `get`/쿼리파라미터/`ApiException`(isKillSwitch·isQuota·isNotFound·retryAfterSeconds) 시그니처를 **실소스로 확인 후** 코드 확정(추측 금지). 본 플랜의 호출부는 그에 맞춘다.
- 테스트: `melos run analyze`·`melos run test`(flutter_test, 위젯/컨트롤러). 실패 테스트 우선.
- 신규 작업 브랜치는 `develop`에서 분기.

---

## File Structure

- Modify: `apps/web/lib/src/features/sandbox/state/run_state.dart` — `RunDone`에 `int? sandboxSessionId` 추가.
- Modify: `apps/web/lib/src/features/sandbox/application/run_controller.dart` — SSE `session` 이벤트 캡처 → `RunDone(sandboxSessionId)`.
- Modify: `apps/web/lib/src/features/sandbox/data/sandbox_run_source.dart` — 목 스트림이 `session` 이벤트도 방출.
- Modify: `apps/web/lib/src/features/review/application/review_controller.dart` — 동기 `request(code)` → `pollForSession(int sandboxSessionId)` 폴링.
- Modify: `apps/web/lib/src/features/review/presentation/review_panel.dart` — `RunDone(sandboxSessionId)` 감지 시 폴링 트리거(UI 배선).
- Modify: `apps/web/lib/src/data/web_mock_fixtures.dart` — `GET /reviews?sandboxSessionId=` 목 응답 + run `session` 이벤트.
- Modify(test): `apps/web/test/features/review/review_controller_test.dart`, `apps/web/test/features/sandbox/...`(run sessionId), `review_panel_test.dart`.

---

## Task 0: 작업 브랜치 + 상류 계약 재검증

- [ ] **Step 1: 브랜치**

```powershell
cd devpath-frontend
git switch develop
git pull
git switch -c feat/slice6-frontend-review-polling
```

- [ ] **Step 2: dp_core ApiClient 계약 확인(추측 금지)**

`packages/dp_core/lib/src/...`에서 `ApiClient`의 `get`(메서드 유무·쿼리파라미터 전달법·반환), `ApiException`(`isKillSwitch`/`isQuota`/`retryAfterSeconds`/not-found 판별)을 **읽어 확인**한다. 본 플랜의 `apiClient.get(...)`/`ApiException` 호출부를 실제 시그니처에 맞춰 정정한다. (없으면 dp_core에 `get` 추가는 별도 범위 — 멈추고 보고.)

```powershell
.\... # melos bootstrap 후 baseline
dart pub global run melos run analyze
```

Expected: 분석 통과(베이스라인).

---

## Task 1: RunState/RunController — sessionId 캡처

**Files:**
- Modify: `sandbox/state/run_state.dart`
- Modify: `sandbox/application/run_controller.dart`
- Modify: `sandbox/data/sandbox_run_source.dart`(목 `session` 이벤트)
- Test: `apps/web/test/features/sandbox/run_controller_session_test.dart`

**Interfaces:**
- Produces: `RunDone({List<String> logs, int? sandboxSessionId})`. SSE `event:'session'`이면 sessionId 파싱·보존, 완료 시 `RunDone(sandboxSessionId)`.

- [ ] **Step 1: 실패 테스트 작성**

`apps/web/test/features/sandbox/run_controller_session_test.dart`:

```dart
import 'package:dp_core/dp_core.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:web/src/features/sandbox/application/run_controller.dart';
import 'package:web/src/features/sandbox/data/sandbox_run_source.dart';
import 'package:web/src/features/sandbox/state/run_state.dart';

void main() {
  test('captures sandboxSessionId from session SSE event', () async {
    final container = ProviderContainer(overrides: [
      sandboxRunConnectProvider.overrideWithValue((code, language) async* {
        yield const SseEvent(event: 'log', data: 'compiling');
        yield const SseEvent(event: 'session', data: '99');
      }),
    ]);
    addTearDown(container.dispose);

    await container.read(runControllerProvider.notifier).run('x', 'PYTHON');

    final s = container.read(runControllerProvider);
    expect(s, isA<RunDone>());
    expect((s as RunDone).sandboxSessionId, 99);
    expect(s.logs, contains('compiling'));
  });
}
```

- [ ] **Step 2: 실패 확인**

```powershell
cd apps/web && flutter test test/features/sandbox/run_controller_session_test.dart
```

Expected: 컴파일 실패(`RunDone.sandboxSessionId` 없음) → FAIL.

- [ ] **Step 3: RunState 확장**

`sandbox/state/run_state.dart`의 `RunDone`을 수정(로그 + sessionId):

```dart
class RunDone extends RunState {
  const RunDone({this.logs = const [], this.sandboxSessionId});
  final List<String> logs;
  final int? sandboxSessionId;
}
```

- [ ] **Step 4: RunController — session 이벤트 캡처**

`sandbox/application/run_controller.dart`. `int? _sessionId` 필드 추가, listen의 onNext에서 `session` 이벤트 분기, onDone에서 `RunDone(logs, sandboxSessionId)`:

```dart
  int? _sessionId;

  Future<void> run(String code, String language) {
    if (_inFlight != null && !_inFlight!.isCompleted) return _inFlight!.future;
    _sub?.cancel();
    _sessionId = null;
    final done = Completer<void>();
    _inFlight = done;
    state = const RunRunning();

    _sub = ref.read(sandboxRunConnectProvider)(code, language).listen(
      (e) {
        if (e.event == 'session') {
          _sessionId = int.tryParse(e.data);
          return;
        }
        final s = state;
        if (s is RunRunning) state = s.appended(e.data);
      },
      onError: (Object err) {
        if (err is ApiException && err.code == ApiErrorCode.sandboxUnavailable) {
          state = const RunUnavailable();
        } else {
          final msg = err is ApiException ? err.message : err.toString();
          state = RunDone(logs: [..._logsOf(state), '실행 오류: $msg'], sandboxSessionId: _sessionId);
        }
        if (!done.isCompleted) done.complete();
      },
      onDone: () {
        final s = state;
        if (s is RunRunning) state = RunDone(logs: s.logs, sandboxSessionId: _sessionId);
        if (!done.isCompleted) done.complete();
      },
      cancelOnError: true,
    );
    return done.future;
  }
```

- [ ] **Step 5: 목 스트림에 session 이벤트 추가**

`sandbox/data/sandbox_run_source.dart`의 목 분기 끝에 `session` 이벤트 방출(목 sessionId 고정):

```dart
    return (String code, String language) async* {
      for (final line in _kMockRunLog) {
        await Future<void>.delayed(const Duration(milliseconds: 200));
        yield SseEvent(event: 'log', data: line);
      }
      yield const SseEvent(event: 'session', data: '1');
    };
```

- [ ] **Step 6: 통과 확인 + 커밋**

```powershell
flutter test test/features/sandbox/run_controller_session_test.dart
cd ../.. && git add apps/web/lib/src/features/sandbox/ apps/web/test/features/sandbox/run_controller_session_test.dart
git commit -m "feat(web): capture sandbox sessionId from run SSE for review polling (slice6 E)"
```

---

## Task 2: ReviewController — 폴링 전환

**Files:**
- Modify: `review/application/review_controller.dart`
- Test: `apps/web/test/features/review/review_controller_test.dart`

**Interfaces:**
- Produces: `ReviewController.pollForSession(int sandboxSessionId, {Duration interval, int maxAttempts})` — `GET /reviews?sandboxSessionId={id}` 인터벌 폴링. status PENDING→재시도(ReviewLoading 유지), DONE→`ReviewLoaded`, FAILED→`ReviewFailed`. ApiException isKillSwitch→`ReviewKillSwitch`, isQuota→`ReviewQuota`, not-found→재시도, 그 외→`ReviewFailed`. 타임아웃→`ReviewFailed`.

> ⚠️ `apiClient.get`/쿼리·`ApiException` 판별은 Task0에서 확인한 실 시그니처에 맞춘다. 아래는 표준 형태(정정 필요 시 정정).

- [ ] **Step 1: 실패 테스트 작성**(목 ApiClient: PENDING→DONE 전이)

`apps/web/test/features/review/review_controller_test.dart`(기존 동기 테스트를 폴링으로 교체):

```dart
import 'package:dp_core/dp_core.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:web/src/features/review/application/review_controller.dart';
import 'package:web/src/features/review/state/review_state.dart';
import 'package:web/src/providers/api_providers.dart';

class _FakeApiClient implements ApiClient {
  _FakeApiClient(this._responses);
  final List<Map<String, dynamic>> _responses;
  int _i = 0;
  @override
  Future<T> get<T>(String path, {Map<String, String>? query}) async {
    final r = _responses[_i.clamp(0, _responses.length - 1)];
    _i++;
    return r as T;
  }
  // 그 외 ApiClient 멤버는 noSuchMethod 또는 UnimplementedError로 스텁(실 인터페이스에 맞춤).
  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

void main() {
  test('polls until DONE then ReviewLoaded', () async {
    final fake = _FakeApiClient([
      {'status': 'PENDING', 'confidence': 0, 'strengths': [], 'improvements': [], 'security': []},
      {'status': 'DONE', 'confidence': 88, 'strengths': ['clear'], 'improvements': [], 'security': []},
    ]);
    final container = ProviderContainer(overrides: [
      apiClientProvider.overrideWithValue(fake),
    ]);
    addTearDown(container.dispose);

    await container.read(reviewControllerProvider.notifier)
        .pollForSession(99, interval: const Duration(milliseconds: 1), maxAttempts: 5);

    final s = container.read(reviewControllerProvider);
    expect(s, isA<ReviewLoaded>());
    expect((s as ReviewLoaded).review.confidence, 88);
  });
}
```

- [ ] **Step 2: 실패 확인**

```powershell
cd apps/web && flutter test test/features/review/review_controller_test.dart
```

Expected: 컴파일 실패(`pollForSession` 없음) → FAIL.

- [ ] **Step 3: 폴링 구현**

`review/application/review_controller.dart`:

```dart
import 'package:dp_core/dp_core.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../providers/api_providers.dart';
import '../state/review_state.dart';

class ReviewController extends Notifier<ReviewState> {
  @override
  ReviewState build() => const ReviewIdle();

  /// 실행 완료 후 sandboxSessionId로 리뷰가 DONE/FAILED로 수렴할 때까지 폴링.
  Future<void> pollForSession(
    int sandboxSessionId, {
    Duration interval = const Duration(seconds: 2),
    int maxAttempts = 30,
  }) async {
    state = const ReviewLoading();
    for (var attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        final json = await ref.read(apiClientProvider).get<Map<String, dynamic>>(
              '/reviews',
              query: {'sandboxSessionId': '$sandboxSessionId'},
            );
        final review = CodeReview.fromJson(json);
        switch (review.status) {
          case 'DONE':
            state = ReviewLoaded(review);
            return;
          case 'FAILED':
            state = const ReviewFailed('AI 리뷰 생성에 실패했습니다');
            return;
          default: // PENDING — 계속 폴링
            break;
        }
      } on ApiException catch (e) {
        if (e.isKillSwitch) {
          state = const ReviewKillSwitch();
          return;
        }
        if (e.isQuota) {
          state = ReviewQuota(e.retryAfterSeconds);
          return;
        }
        // 아직 리뷰 미생성(404 등)이면 계속 폴링; 그 외 오류는 실패.
        if (!_isNotFound(e)) {
          state = ReviewFailed(e.message);
          return;
        }
      }
      await Future<void>.delayed(interval);
    }
    state = const ReviewFailed('AI 리뷰 시간이 초과되었습니다');
  }

  bool _isNotFound(ApiException e) =>
      e.code == ApiErrorCode.notFound; // ⚠️ dp_core ApiErrorCode 실값으로 확인·정정
}

final reviewControllerProvider =
    NotifierProvider<ReviewController, ReviewState>(ReviewController.new);
```

> ⚠️ `apiClient.get`의 `query` 파라미터명·`ApiErrorCode.notFound`·`ApiException.isKillSwitch/isQuota/retryAfterSeconds`는 Task0에서 확인한 dp_core 실값에 맞춰 정정한다. 기존 동기 `request(code)`는 제거(또는 deprecated 주석).

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
flutter test test/features/review/review_controller_test.dart
cd ../.. && git add apps/web/lib/src/features/review/application/review_controller.dart apps/web/test/features/review/review_controller_test.dart
git commit -m "feat(web): poll GET /reviews by sandboxSessionId (slice6 E D-8)"
```

---

## Task 3: ReviewPanel 폴링 트리거 + 목 픽스처

**Files:**
- Modify: `review/presentation/review_panel.dart`(run 완료 감지 → 폴링)
- Modify: `apps/web/lib/src/data/web_mock_fixtures.dart`(`GET /reviews` 목)
- Test: `apps/web/test/features/review/review_panel_test.dart`(상태별 렌더)

**Interfaces:**
- Consumes: `runControllerProvider`(RunDone.sandboxSessionId), `reviewControllerProvider.pollForSession`. 목 픽스처가 `GET /reviews?sandboxSessionId=`에 `{status:'DONE',...}` 반환.

- [ ] **Step 1: ReviewPanel 트리거 배선**

`review_panel.dart`에서 `RunState`를 `ref.listen`해 `RunDone && sandboxSessionId != null`이면 1회 `pollForSession(id)` 호출(중복 트리거 가드). 기존 "AI 리뷰" 버튼이 있으면 "최신 실행 리뷰 보기"로 의미 전환(폴링 재시도) — 기존 위젯 구조 확인 후 최소 수정. 상태별 렌더(loading/loaded/killSwitch/quota/failed)는 기존 유지.

- [ ] **Step 2: 목 픽스처**

`web_mock_fixtures.dart`에 `GET /reviews`(쿼리 sandboxSessionId) → `{status:'DONE', confidence:82, strengths:['목 리뷰'], improvements:[], security:[]}` 추가(기존 `POST /reviews` 목은 제거 또는 폴링용으로 대체).

- [ ] **Step 3: 위젯 테스트 갱신**

`review_panel_test.dart`: ReviewLoaded/Failed/KillSwitch/Quota 상태에서 패널 렌더 단언(기존 테스트를 폴링 흐름·새 상태에 맞게 갱신). `theme: DpTheme.light()` 제공(레포 CLAUDE.md 위젯테스트 규칙).

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
cd apps/web && flutter test test/features/review/
cd ../.. && git add apps/web/lib/src/features/review/presentation/review_panel.dart apps/web/lib/src/data/web_mock_fixtures.dart apps/web/test/features/review/review_panel_test.dart
git commit -m "feat(web): wire review polling on run done + mock fixtures (slice6 E)"
```

---

## Task 4: 전체 회귀 + develop PR

- [ ] **Step 1: melos analyze + test(전 패키지)**

```powershell
dart pub global run melos run analyze
dart pub global run melos run test
```

Expected: 분석 0 이슈, web 테스트(신규 폴링/sessionId + 기존) 전부 PASS, dp_core 무변경 회귀 없음. (골든 제외 CI 동등.)

- [ ] **Step 2: PR 생성·CI·머지**

```powershell
git push -u origin feat/slice6-frontend-review-polling
gh pr create --base develop --title "feat(web): AI 리뷰 폴링 전환(sessionId 수신 + GET /reviews 폴링) 슬라이스 #6 빌드 E" --body "run SSE session 이벤트로 sandboxSessionId 수신(D-8) → 실행 완료 후 GET /reviews?sandboxSessionId 폴링(PENDING→DONE/FAILED) → ReviewPanel. mock→실API. CodeReview.id/status 활용. 설계서 docs/superpowers/specs/2026-06-23-md2-slice6-ai-code-review-design.md"
gh pr checks --watch
gh pr merge --merge
```

Expected: frontend CI(`analyze-test`) 녹색. 앱이라 main 릴리스는 슬라이스 통합 릴리스에서.

---

## Self-Review 메모(작성자)

- **Spec 커버리지**: D-8(sessionId 수신=Task1, 폴링=Task2, 트리거=Task3). §5 frontend(mock→실API, ReviewPanel)=Task3. 전부 매핑.
- **placeholder 없음**: 상태/컨트롤러/목 코드 실값. ⚠️ **상류 계약 재검증 지시 2곳**: `dp_core` `ApiClient.get`/쿼리·`ApiException`(killSwitch/quota/notFound/retryAfter) 실 시그니처(Task0 확인 후 정정), ReviewPanel 기존 위젯 구조(최소 수정). 추측 금지 명시(P4~P5 교훈).
- **타입 일관성**: `RunDone.sandboxSessionId`(int?)·SSE `session` 이벤트·`pollForSession(int)`·`CodeReview.status`('PENDING'/'DONE'/'FAILED', 빌드 C1 ReviewController 반환과 일치)·`GET /reviews?sandboxSessionId`(빌드 C1 API·빌드 D 라우트와 일치). `ReviewState` 6종 재사용.
- **kill-switch/quota 매핑 주의**: 비동기 모델에서 kill-switch/quota는 C1이 FAILED+error_code로 저장. 프론트의 `isKillSwitch`/`isQuota`는 ApiException 기반이므로, 폴링 GET이 그 경우 **HTTP 503/429를 반환**하도록 C1 ReviewController와 정합 필요(또는 CodeReview에 errorCode 노출). 구현 시 C1과 교차 확정(설계 §7).
