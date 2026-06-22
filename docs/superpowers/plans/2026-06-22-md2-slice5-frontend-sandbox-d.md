# 슬라이스 #5 빌드 D — frontend `sandbox_run_source` 실API 전환 + `language` 추가 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `devpath-frontend`의 Sandbox 실API 요청 body에 `language` 파라미터를 추가하고(`{code}` → `{code, language}`), 언어 선택 드롭다운 UI를 `SandboxPage`에 삽입한다. `RunController.run`이 `language`를 받아 `SandboxRunConnect`에 전달하도록 시그니처를 확장한다. 기존 목 분기·SSE 로그 흐름·`RunUnavailable`(503) 회귀가 없음을 테스트로 보장한다.

**Architecture:**
- `SandboxRunConnect` typedef: `Function(String code)` → `Function(String code, String language)`
- `sandboxRunConnectProvider` 실API 분기: `client.sse('/sandbox/run', body: {'code': code, 'language': language})`
- `RunController.run(String code)` → `run(String code, String language)`
- `SandboxPage._SandboxPageState`: `_language` 상태(`String`) + `DropdownButton`(JAVA/NODE/PYTHON, 기본 JAVA) 추가, `run(_code, _language)` 전달
- 목 분기는 기존 유지(code·language 모두 무시, `_kMockRunLog` 그대로)
- 기존 테스트(`run_controller_test.dart`, `sandbox_page_test.dart`)의 override 람다 시그니처를 `(_, __) =>` 로 수정

**Tech Stack:** Flutter Web · Dart · flutter_riverpod · flutter_test · ProviderContainer · melos 7.

> ⚠️ **language 출처 결정**: 설계서 §5 D-3은 "프론트 소폭 수정"으로 언어 추가를 지정하나 UI 상세를 명시하지 않는다. 본 플랜은 **가장 단순한 드롭다운(JAVA/NODE/PYTHON, 기본값 JAVA)** 을 채택한다. 콘텐츠 메타나 라우트 파라미터 연동이 필요하면 컨트롤러가 이 플랜을 수정한 뒤 위임하라.

## Global Constraints

- 대상 레포: **devpath-frontend 단독**. 다른 레포 수정 금지.
- 신규 브랜치는 `develop`에서 분기(`feat/sandbox-language-param`).
- `main`·`develop` 직접 push 금지. 모든 변경은 PR 경유.
- **테스트 우선**: 실패 테스트 먼저 작성 → 구현 → `melos run test` 통과 눈으로 확인.
- **추측 금지**: 불명확한 부분은 멈추고 `NEEDS_CONTEXT`로 보고.
- 플랜에 없는 코드(예: 라우팅 변경, 다른 feature 파일) 임의 수정 금지.
- 위젯 테스트에서 `DpTheme.light()` 필요(`context.dpColors` 사용 위젯 포함), `tester.view.physicalSize`로 폭 고정.
- melos 명령은 **모노레포 루트**(`devpath-frontend/`)에서 실행.

---

## File Structure

**Modify (production):**
- `apps/web/lib/src/features/sandbox/data/sandbox_run_source.dart` — typedef에 `language` 추가, 실API body 확장
- `apps/web/lib/src/features/sandbox/application/run_controller.dart` — `run` 메서드 시그니처에 `language` 추가
- `apps/web/lib/src/features/sandbox/presentation/sandbox_page.dart` — `_language` 상태 + 언어 드롭다운 추가, `run` 호출에 `_language` 전달

**Modify (test):**
- `apps/web/test/features/sandbox/run_controller_test.dart` — override 람다 `(_) =>` → `(_, __) =>`, language 전달 테스트 추가
- `apps/web/test/features/sandbox/sandbox_page_test.dart` — override 람다 `(_) =>` → `(_, __) =>`

> 본보기: `run_controller_test.dart`의 `ProviderContainer` + `sandboxRunConnectProvider.overrideWithValue` 패턴 그대로 재사용. `sandbox_page_test.dart`의 `UncontrolledProviderScope` + `tester.view.physicalSize` 패턴 재사용.

---

## Task 0: 작업 브랜치

- [ ] **Step 1: 브랜치 분기**

```powershell
cd D:\workspace\dev-path-ai\devpath-frontend
git switch develop
git pull
git switch -c feat/sandbox-language-param
```

---

## Task 1: `SandboxRunConnect` typedef + `sandboxRunConnectProvider` 실API 전환

**Files:**
- Modify: `apps/web/lib/src/features/sandbox/data/sandbox_run_source.dart`

**Interfaces:**
- `SandboxRunConnect`: `typedef SandboxRunConnect = Stream<SseEvent> Function(String code, String language);`
- 실API body: `{'code': code, 'language': language}`
- 목 분기: 파라미터 추가만, 동작 변경 없음(기존 `_kMockRunLog` 유지)

- [ ] **Step 1: 실패 테스트 먼저** — `run_controller_test.dart`에서 `language`가 요청에 실리는지 확인하는 테스트를 추가한다. 이 테스트는 아직 typedef가 변경되지 않아 **컴파일 실패**해야 한다.

`apps/web/test/features/sandbox/run_controller_test.dart` 파일 맨 위 `main()` 블록 **끝(마지막 `}`  앞)** 에 다음 테스트를 추가한다:

```dart
  test('language가 connect 호출에 전달된다', () async {
    String? capturedLanguage;
    final c = ProviderContainer(
      overrides: [
        sandboxRunConnectProvider.overrideWithValue(
          (String code, String language) {
            capturedLanguage = language;
            return _logs(['ok']);
          },
        ),
      ],
    );
    addTearDown(c.dispose);

    await c.read(runControllerProvider.notifier).run('print(1);', 'NODE');

    expect(capturedLanguage, 'NODE');
  });
```

- [ ] **Step 2: 실패 확인**

```powershell
cd D:\workspace\dev-path-ai\devpath-frontend
melos run test -- --name "language가 connect 호출에 전달된다"
```

Expected: 컴파일 실패(typedef 불일치 또는 `run` 시그니처 불일치).

- [ ] **Step 3: `sandbox_run_source.dart` 수정** — 아래와 같이 파일 전체를 교체한다:

```dart
import 'package:dp_core/dp_core.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../providers/api_providers.dart';

/// 실행 로그 SSE 스트림 생성기.
/// D-3 반영: language 파라미터 추가(JAVA/NODE/PYTHON). 목 분기는 무시.
/// 테스트 override는 `(code, language) => stream` 형태.
typedef SandboxRunConnect = Stream<SseEvent> Function(String code, String language);

const List<String> _kMockRunLog = [
  '> dart run main.dart',
  '컴파일 중…',
  '테스트 1/2 통과',
  '테스트 2/2 통과',
  '완료 (0.8s)',
];

final sandboxRunConnectProvider = Provider<SandboxRunConnect>((ref) {
  final config = ref.watch(appConfigProvider);
  if (config.useMock) {
    return (String code, String language) async* {
      for (final line in _kMockRunLog) {
        await Future<void>.delayed(const Duration(milliseconds: 200));
        yield SseEvent(event: 'log', data: line);
      }
    };
  }
  // 실API: body에 code + language 포함(설계서 §5 D-3).
  final client = ref.watch(apiClientProvider);
  return (String code, String language) =>
      client.sse('/sandbox/run', body: {'code': code, 'language': language});
});
```

- [ ] **Step 4: 기존 테스트 override 람다 수정** — `run_controller_test.dart`의 기존 `(_) =>` 람다 3개를 `(_, __) =>` 로 수정한다.

`apps/web/test/features/sandbox/run_controller_test.dart` 에서:

```dart
// 변경 전 (3곳)
sandboxRunConnectProvider.overrideWithValue(
  (_) => _logs(['컴파일 중…', '테스트 통과']),
),
// ...
sandboxRunConnectProvider.overrideWithValue(
  (_) => Stream<SseEvent>.error(
    const ApiException(
      code: ApiErrorCode.sandboxUnavailable,
      message: '점검',
    ),
  ),
),
// ...
sandboxRunConnectProvider.overrideWithValue((_) {
  connects++;
  return _logs(['1회차']);
}),
```

```dart
// 변경 후 (3곳)
sandboxRunConnectProvider.overrideWithValue(
  (_, __) => _logs(['컴파일 중…', '테스트 통과']),
),
// ...
sandboxRunConnectProvider.overrideWithValue(
  (_, __) => Stream<SseEvent>.error(
    const ApiException(
      code: ApiErrorCode.sandboxUnavailable,
      message: '점검',
    ),
  ),
),
// ...
sandboxRunConnectProvider.overrideWithValue((_, __) {
  connects++;
  return _logs(['1회차']);
}),
```

- [ ] **Step 5: 통과 확인(단위 — run_controller_test만)**

```powershell
cd D:\workspace\dev-path-ai\devpath-frontend
melos run test -- --name "language가 connect 호출에 전달된다"
```

Expected: 신규 테스트 PASS. 단, `run_controller.dart`가 아직 업데이트 안 됐으면 컴파일 오류 — Task 2에서 해결.

> 이 단계 이후 `run_controller.dart` 수정 전까지는 전체 테스트가 컴파일 실패할 수 있음. Task 2 완료 후 전체 확인.

- [ ] **Step 6: 커밋(아직 전체 빌드 안 됨 — Task 2 후 함께 커밋해도 무방)**

단계별 작업 추적을 위해 커밋해도 되고, Task 2 완료 후 함께 커밋해도 된다.

---

## Task 2: `RunController.run` 시그니처 확장

**Files:**
- Modify: `apps/web/lib/src/features/sandbox/application/run_controller.dart`

**Interfaces:**
- `run(String code, String language)` — language를 `sandboxRunConnectProvider` 호출에 전달
- 재진입 가드·SSE 구독·에러 처리·`RunUnavailable` 분기는 변경 없음

- [ ] **Step 1: `run_controller.dart` 수정**

`run(String code)` 를 `run(String code, String language)` 로 변경하고, `ref.read(sandboxRunConnectProvider)(code)` 를 `ref.read(sandboxRunConnectProvider)(code, language)` 로 수정한다.

`apps/web/lib/src/features/sandbox/application/run_controller.dart` 전체:

```dart
import 'dart:async';

import 'package:dp_core/dp_core.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/sandbox_run_source.dart';
import '../state/run_state.dart';

class RunController extends Notifier<RunState> {
  StreamSubscription<SseEvent>? _sub;

  @override
  RunState build() {
    ref.onDispose(() => _sub?.cancel());
    return const RunIdle();
  }

  Completer<void>? _inFlight; // F5/D1: 재진입 가드

  Future<void> run(String code, String language) {
    // F5/D1 반영: 진행 중이면 무시 — 연속 호출로 이전 Completer가 미완료 hang되는 것을 방지.
    if (_inFlight != null && !_inFlight!.isCompleted) return _inFlight!.future;

    _sub?.cancel();
    final done = Completer<void>();
    _inFlight = done;
    state = const RunRunning();

    _sub = ref
        .read(sandboxRunConnectProvider)(code, language)
        .listen(
          (e) {
            final s = state;
            if (s is RunRunning) state = s.appended(e.data);
          },
          onError: (Object err) {
            if (err is ApiException &&
                err.code == ApiErrorCode.sandboxUnavailable) {
              state = const RunUnavailable();
            } else {
              final msg = err is ApiException ? err.message : err.toString();
              state = RunDone(logs: [..._logsOf(state), '실행 오류: $msg']);
            }
            if (!done.isCompleted) done.complete();
          },
          onDone: () {
            final s = state;
            if (s is RunRunning) state = RunDone(logs: s.logs);
            if (!done.isCompleted) done.complete();
          },
          cancelOnError: true,
        );

    return done.future;
  }

  List<String> _logsOf(RunState s) =>
      s is RunRunning ? [...s.logs] : (s is RunDone ? [...s.logs] : <String>[]);
}

final runControllerProvider = NotifierProvider<RunController, RunState>(
  RunController.new,
);
```

- [ ] **Step 2: run_controller 단위 테스트 전체 통과 확인**

```powershell
cd D:\workspace\dev-path-ai\devpath-frontend
melos run test -- --name "run_controller"
```

Expected: `run_controller_test.dart`의 4개 테스트 모두 PASS(기존 3개 + 신규 `language가 connect 호출에 전달된다`).

> 아직 `sandbox_page.dart`가 `run(_code)` (1인자) 를 호출하므로 전체 컴파일은 실패할 수 있음. Task 3에서 해결.

- [ ] **Step 3: 커밋**

```powershell
git add apps/web/lib/src/features/sandbox/data/sandbox_run_source.dart
git add apps/web/lib/src/features/sandbox/application/run_controller.dart
git add apps/web/test/features/sandbox/run_controller_test.dart
git commit -m "feat(sandbox): add language param to SandboxRunConnect and RunController (MD2 slice5 build D)"
```

---

## Task 3: `SandboxPage` 언어 선택 드롭다운 + `run` 호출 수정

**Files:**
- Modify: `apps/web/lib/src/features/sandbox/presentation/sandbox_page.dart`
- Modify: `apps/web/test/features/sandbox/sandbox_page_test.dart`

**Interfaces:**
- `_SandboxPageState`에 `String _language = 'JAVA'` 상태 추가
- `AppBar.actions`에 언어 드롭다운 삽입: `DropdownButton<String>` (JAVA/NODE/PYTHON)
- `run(_code)` → `run(_code, _language)`
- `sandbox_page_test.dart`: override 람다 `(_) =>` → `(_, __) =>`

- [ ] **Step 1: `sandbox_page_test.dart` 수정(실패 먼저)**

`apps/web/test/features/sandbox/sandbox_page_test.dart` 의 `(_) => _logs(...)` 를 `(_, __) => _logs(...)` 로 수정한다:

```dart
// 변경 전
sandboxRunConnectProvider.overrideWithValue(
  (_) => _logs(['실행 결과: OK']),
),

// 변경 후
sandboxRunConnectProvider.overrideWithValue(
  (_, __) => _logs(['실행 결과: OK']),
),
```

- [ ] **Step 2: 언어 선택 테스트 추가**

`apps/web/test/features/sandbox/sandbox_page_test.dart` 의 `main()` 블록 끝(마지막 `}` 앞)에 다음 테스트를 추가한다:

```dart
  testWidgets('언어 드롭다운에서 NODE 선택 시 run에 NODE가 전달된다', (tester) async {
    tester.view.physicalSize = const Size(1400, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    String? capturedLanguage;
    final c = ProviderContainer(
      overrides: [
        sandboxRunConnectProvider.overrideWithValue(
          (String code, String language) {
            capturedLanguage = language;
            return const Stream<SseEvent>.empty();
          },
        ),
      ],
    );
    addTearDown(c.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: c,
        child: MaterialApp(theme: DpTheme.light(), home: const SandboxPage()),
      ),
    );
    await tester.pumpAndSettle();

    // 드롭다운에서 NODE 선택
    await tester.tap(find.byKey(const Key('sandbox_language_dropdown')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('NODE').last);
    await tester.pumpAndSettle();

    // 실행 버튼 탭
    await tester.tap(find.text('실행'));
    await tester.pumpAndSettle();

    expect(capturedLanguage, 'NODE');
  });
```

> `const Key('sandbox_language_dropdown')`은 Step 3에서 드롭다운에 지정할 key와 일치해야 한다.

- [ ] **Step 3: 실패 확인**

```powershell
cd D:\workspace\dev-path-ai\devpath-frontend
melos run test -- --name "언어 드롭다운"
```

Expected: 컴파일 실패 또는 `sandbox_language_dropdown` key를 찾지 못해 실패.

- [ ] **Step 4: `sandbox_page.dart` 수정**

`apps/web/lib/src/features/sandbox/presentation/sandbox_page.dart` 전체를 아래와 같이 수정한다:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../review/application/review_controller.dart';
import '../../review/presentation/review_panel.dart';
import '../application/run_controller.dart';
import '../state/run_state.dart';
import 'monaco_editor_view.dart';
import 'sandbox_layout.dart';

const _kInitialCode = 'void main() {\n  print(\'hello devpath\');\n}\n';

/// 지원 언어 목록(설계서 §2 D-3).
const _kLanguages = ['JAVA', 'NODE', 'PYTHON'];

class SandboxPage extends ConsumerStatefulWidget {
  const SandboxPage({super.key});

  @override
  ConsumerState<SandboxPage> createState() => _SandboxPageState();
}

class _SandboxPageState extends ConsumerState<SandboxPage> {
  String _code = _kInitialCode;
  String _language = 'JAVA'; // D-3 기본값

  // F5-b: 에디터 가시화 시 Monaco 재레이아웃 트리거용 핸들.
  final GlobalKey<MonacoEditorViewState> _editorKey =
      GlobalKey<MonacoEditorViewState>();

  @override
  Widget build(BuildContext context) {
    final run = ref.watch(runControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Sandbox'),
        actions: [
          // D-3: 언어 선택 드롭다운(JAVA/NODE/PYTHON, 기본 JAVA).
          DropdownButton<String>(
            key: const Key('sandbox_language_dropdown'),
            value: _language,
            items: _kLanguages
                .map((l) => DropdownMenuItem(value: l, child: Text(l)))
                .toList(),
            onChanged: (v) {
              if (v != null) setState(() => _language = v);
            },
          ),
          const SizedBox(width: DpSpacing.sm),
          FilledButton(
            onPressed: run is RunRunning
                ? null
                : () => ref
                    .read(runControllerProvider.notifier)
                    .run(_code, _language),
            child: const Text('실행'),
          ),
          const SizedBox(width: DpSpacing.md),
        ],
      ),
      body: SandboxLayout(
        // F5-b: <1024 세그먼트 탭에서 에디터 재가시화 시 layout() 보정.
        onEditorVisible: () => _editorKey.currentState?.layout(),
        editor: MonacoEditorView(
          key: _editorKey,
          initialCode: _kInitialCode,
          onChanged: (v) => _code = v,
        ),
        log: _LogPane(run: run),
        review: ReviewPanel(
          onRequest: () =>
              ref.read(reviewControllerProvider.notifier).request(_code),
        ),
      ),
    );
  }
}

/// 실행 로그(codeLogBg). SANDBOX_UNAVAILABLE이면 전용 안내(편집은 유지).
class _LogPane extends StatelessWidget {
  const _LogPane({required this.run});
  final RunState run;

  @override
  Widget build(BuildContext context) {
    if (run is RunUnavailable) return const DpSandboxUnavailable();
    final logs = switch (run) {
      RunRunning(:final logs) => logs,
      RunDone(:final logs) => logs,
      _ => const <String>[],
    };
    return Container(
      color: context.dpColors.codeLogBg,
      padding: const EdgeInsets.all(DpSpacing.md),
      child: logs.isEmpty
          ? Text(
              '실행 결과가 여기에 표시됩니다.',
              style: DpTypography.code.copyWith(
                color: context.dpColors.codeText,
              ),
            )
          : SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final l in logs)
                    Text(
                      l,
                      style: DpTypography.code.copyWith(
                        color: context.dpColors.codeText,
                      ),
                    ),
                ],
              ),
            ),
    );
  }
}
```

- [ ] **Step 5: 전체 sandbox 테스트 통과 확인**

```powershell
cd D:\workspace\dev-path-ai\devpath-frontend
melos run test -- --name "sandbox"
```

Expected: `run_controller_test.dart` 4개 + `sandbox_page_test.dart` 2개 전부 PASS.

- [ ] **Step 6: 정적 분석**

```powershell
cd D:\workspace\dev-path-ai\devpath-frontend
melos run analyze
```

Expected: 0 errors, 0 warnings (info 허용).

- [ ] **Step 7: 커밋**

```powershell
git add apps/web/lib/src/features/sandbox/presentation/sandbox_page.dart
git add apps/web/test/features/sandbox/sandbox_page_test.dart
git commit -m "feat(sandbox): add language dropdown to SandboxPage and wire to run (MD2 slice5 build D)"
```

---

## Task 4: 전체 회귀 + develop PR

- [ ] **Step 1: 전체 테스트(모노레포)**

```powershell
cd D:\workspace\dev-path-ai\devpath-frontend
melos run test
```

Expected: 전체 PASS. 기존 `sandbox_page_test.dart` · `run_controller_test.dart` · `sandbox_layout_test.dart` · `run_state_test.dart` · `monaco_editor_view_test.dart` · `sandbox_review_smoke_test.dart` 회귀 없음.

- [ ] **Step 2: 정적 분석(전체)**

```powershell
cd D:\workspace\dev-path-ai\devpath-frontend
melos run analyze
```

Expected: 0 errors.

- [ ] **Step 3: develop PR 생성 · CI 녹색 · 머지**

```powershell
cd D:\workspace\dev-path-ai\devpath-frontend
git push -u origin feat/sandbox-language-param
gh pr create --base develop --title "feat(sandbox): add language param to run request (MD2 slice5 build D)" --body "MD2 슬라이스 #5 빌드 D. SandboxRunConnect typedef에 language 파라미터 추가, 실API body {code,language}, RunController.run(code, language), SandboxPage 언어 드롭다운(JAVA/NODE/PYTHON 기본JAVA). 목 분기 유지, 기존 SSE 로그/RunUnavailable 회귀 없음. 설계서 docs/superpowers/specs/2026-06-22-md2-slice5-sandbox-design.md §5 D-3."
gh pr checks --watch
```

Expected: CI `melos run analyze` · `melos run test` 녹색 → 확인 후 머지(컨트롤러 직접 검증).

---

## Self-Review 메모 (작성자)

- **Spec 커버리지**: 설계서 §5 D-3 "language 추가(프론트 소폭 수정)" → Task 1~3 전량 커버. 계약 최소(SSE log) 유지 — exit_code 등 별도 파싱 없음(일치).
- **No placeholder**: `sandbox_run_source.dart` · `run_controller.dart` · `sandbox_page.dart` 전량 실코드. melos 명령 전부 구체적.
- **언어값 일치**: `'JAVA'` / `'NODE'` / `'PYTHON'` — 설계서 §4 CHECK(JAVA/NODE/PYTHON) · §5 body 계약 · 드롭다운 · 테스트 `capturedLanguage` 검증이 동일 문자열로 통일.
- **기존 테스트 회귀**: 람다 `(_) =>` → `(_, __) =>` 수정을 Task 1·3에 명시(2파일 3곳). 누락 시 컴파일 실패로 즉시 발견 가능.
- **재진입 가드**: `run_controller.dart` 수정 시 `_inFlight` 가드 원형 보존(코드에 명시).
- **language 출처 결정**: 드롭다운 기본안 채택, 플랜 상단 `⚠️` 에 근거·위임 명시. 컨텐츠 메타 연동은 후속(범위 외).
- **교훈 반영**: 실패 테스트 우선(CLAUDE.md 절대조건 2), 추측 금지(조건 1), develop 브랜치 분기(조건 4), melos 루트 실행(CLAUDE.md 빌드·테스트 절).
