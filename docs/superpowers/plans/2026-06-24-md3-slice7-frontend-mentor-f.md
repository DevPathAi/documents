# 슬라이스 #7 빌드 F — frontend 멘토 SSE 실API 전환 + 참고자료 렌더 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** AI 멘토 프론트(`apps/web`)를 **mock SSE에서 실API SSE로 전환**한다: `POST /ai-mentor/sessions` 요청에 wire body `{message, contentId?}`를 보내고(빌드 D ai-svc 계약 M-2), `event:token`을 실시간 누적하며, **`event:references`(1회) data=JSON 배열을 파싱해 참고자료 패널로 렌더**한다. 정상 종료(스트림 close)·LLM 실패(`completeWithError`)·개시 전 거부(비-200 kill-switch/quota)는 **기존 onDone/onError/`ApiException` 경로를 그대로 재사용**한다.

**Architecture:** `flutter_riverpod` Notifier 패턴. `mentorSseConnectProvider`(typedef `MentorSseConnect`)가 `apiClient.sse('/ai-mentor/sessions', body: {message, contentId})`를 호출한다(`fromStep`은 wire에서 제거, typedef 파라미터는 재개 후속 자리로 미사용 보존). `MentorController.send()`의 `listen` 콜백이 **`e.event`로 분기** — `references`면 JSON 파싱→`state.references`, 그 외(token)면 기존 버블 append. mock 경로는 `references` 이벤트를 1회 방출(위젯 테스트 고정 데이터). `mentor_page`의 `_FollowUpSlot`(자리표시)을 `state.references` 칩 패널로 교체(빈 배열이면 미표시).

**Tech Stack:** Flutter · Dart · Riverpod 3 · `dp_core`(ApiClient.sse·SseEvent·ApiException·ApiErrorCode) · melos 7 · flutter_test.

## Global Constraints

- 대상 레포: `devpath-frontend` 단독(`apps/web`). 설계서 [2026-06-24-md3-slice7-ai-mentor-design](../specs/2026-06-24-md3-slice7-ai-mentor-design.md) §5(frontend)·§9 빌드 F·M-2(SSE 계약)·§2.2(현 mock)·C-1.
- **서버 계약(M-2, 빌드 D ai-svc 제공)을 정확히 consume**:
  - `POST /ai-mentor/sessions` body `{message, contentId?}`(JWT 엣지는 gateway).
  - **개시 전 선체크**: kill-switch=503·quota=429(비-200, 스트림 미개시) → dio가 `DioException`→`ApiException`으로 정규화 → 프론트 기존 `ApiException.isKillSwitch`/`isQuota`.
  - **200 스트림 개시 후**: `event:token`(반복, 누적) · `event:references` data=JSON `[{contentId, slug, title}]`(1회). 정상=스트림 close(`onDone`). LLM 런타임 실패=서버 `completeWithError`→dio stream error→`onError`.
  - **in-band `event:error`/`event:done` 없음**(C-1). 프론트 신규 처리는 `references` 분기 1종뿐.
- **상류 계약 실측 완료(추측 금지, 본 플랜 작성 시 실소스 확인)**:
  - `dp_core` `ApiClient.sse(String path, {Object? body}) => SseClient(dio).connect(...)`(JSON body, `text/event-stream`). `SseClient.connect`는 **비-200(DioException)일 때만 `ApiException` throw**(개시 전 거부 경로), 200 후에는 `event:`/`data:`를 파싱해 `SseEvent{event, data}`를 `onData`로 yield. → 컨트롤러가 `e.event`로 분기 가능(확인).
  - `SseEvent{String? event, required String data}`(dp_core, 변경 없음).
  - `ApiException`: `isKillSwitch`(`code==aiKillSwitchActive`)·`isQuota`(`code==quotaExceeded`) 게터 존재. `ApiErrorCode.fromWire`가 `AI_KILL_SWITCH_ACTIVE`/`QUOTA_EXCEEDED` 매핑(변경 없음).
  - `apiClientProvider`·`appConfigProvider`(`config.useMock`) 위치: **`apps/web/lib/src/providers/api_providers.dart`**(mentor에서 `../../../providers/api_providers.dart`로 import). ⚠️ 설계 §11/지시서의 `features/providers/` 표기는 오기 — 실경로는 `lib/src/providers/`.
  - 패키지명 **`devpath_web`**(테스트 import `package:devpath_web/...`).
- 기존 계약 보존(회귀 금지): `MentorController.send()`의 취소 경쟁(`targetIndex` 클로저 캡처)·hang 방지(`_inFlight` Completer)·빈/부분 버블 prune(`_pruneEmptyMentorBubble`)·`retry()`(resend)·onError 분기(killSwitch/failed/partial)·onDone(idle). **이 로직들은 그대로 유지**하고 `e.event` 분기 + references 상태만 추가한다.
- `MentorReference` 타입 위치 결정(설계 §3 "mentor feature 내 또는 dp_core — 기존 패턴 확인 후 결정"): **mentor feature 내 `state/mentor_state.dart`에 plain Dart class로 정의**한다. 근거 — 멘토 feature는 freezed/codegen을 쓰지 않고 상태 타입(`ChatMessage`/`MentorState`)을 `state/`에 co-locate한다. dp_core 모델(`code_review.dart` 등)은 모두 freezed+build_runner 기반이라 거기 추가하면 패턴 불일치 + 코드젠 필요 → mentor-local plain class가 `ChatMessage`와 동형(추측 아님, 실측 기반 결정).
- 테스트: `melos run analyze` · `melos run test`(flutter_test, 위젯/컨트롤러) · `melos run format`(CI 게이트, `dart format --set-exit-if-changed`). 실패 테스트 우선(절대 조건 2). 위젯 테스트에 `theme: DpTheme.light()` 제공(레포 CLAUDE.md). 단일 앱 테스트는 `cd apps/web && flutter test <path>`.
- 신규 작업 브랜치는 `develop`에서 분기. `main`·`develop` 직접 작업·push 금지. develop으로 PR.
- 본 빌드는 **mock fixture로 독립 테스트 가능**(실서버 불요). 빌드 D(ai-svc)·E(gateway) 머지 후 끝단간 실연동.

---

## File Structure

- Modify: `apps/web/lib/src/features/mentor/state/mentor_state.dart` — `MentorReference{int contentId, String slug, String title}` 타입 추가(+`fromJson`) · `MentorState`에 `List<MentorReference> references`(기본 `const []`) 필드 추가.
- Modify: `apps/web/lib/src/features/mentor/data/mentor_sse_source.dart` — `MentorSseConnect` typedef에 `String? contentId` 파라미터 추가(`fromStep`은 미사용 보존) · 실 경로 wire body `{message, contentId}`로 교체(`fromStep` 제거) · mock 경로가 `event:references`를 1회 방출(고정 데이터).
- Modify: `apps/web/lib/src/features/mentor/application/mentor_controller.dart` — `send({String? contentId})` 시그니처 · `listen` 콜백에서 `e.event=='references'` 분기(JSON 파싱→`state.references`) + 그 외 token 기존 append · onDone/onError/prune 기존 유지 · `MentorState` 재생성 시 `references` 보존.
- Modify: `apps/web/lib/src/features/mentor/presentation/mentor_page.dart` — `_FollowUpSlot`(자리표시) 제거 → `_ReferencePanel`(state.references 칩, 빈 배열이면 미표시)로 교체.
- Modify(test): `apps/web/test/features/mentor/mentor_controller_test.dart`(references 수신→state·token 회귀·기존 onError/onDone/killSwitch/partial/prune 유지) · `apps/web/test/features/mentor/mentor_page_test.dart`(참고자료 패널 렌더) · `apps/web/test/features/mentor/mentor_sse_source_test.dart`(mock이 token+references 방출, wire body 형태).

> mentor mock SSE는 **fixture가 아니라 `mentorSseConnectProvider`의 `useMock` 분기에서 인라인 생성**된다(실측: `web_mock_fixtures.dart`는 비-SSE REST 목 전용). 따라서 references 목은 그 분기에 추가한다(빌드 E 패턴과 위치 다름 — 멘토는 SSE 소스 자체가 mock).

---

## Task 0: 작업 브랜치 + 베이스라인

- [ ] **Step 1: 브랜치**

```powershell
cd devpath-frontend
git switch develop
git pull
git switch -c feat/slice7-frontend-mentor-sse
```

- [ ] **Step 2: 베이스라인 분석(현 상태 녹색 확인)**

```powershell
dart pub global run melos run analyze
```

Expected: 분석 0 이슈(베이스라인). (melos PATH 설정 시 `melos run analyze`도 가능.)

---

## Task 1: MentorState — references 필드 + MentorReference 타입

**Files:**
- Modify: `apps/web/lib/src/features/mentor/state/mentor_state.dart`
- Test: `apps/web/test/features/mentor/mentor_state_test.dart`(신규)

**Interfaces:**
- Produces: `MentorReference{int contentId, String slug, String title}` + `MentorReference.fromJson(Map<String,dynamic>)`. `MentorState{messages, status, error, references}`(`references` 기본 `const []`).

- [ ] **Step 1: 실패 테스트 작성**

`apps/web/test/features/mentor/mentor_state_test.dart`:

```dart
import 'package:devpath_web/src/features/mentor/state/mentor_state.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('MentorReference.fromJson 파싱', () {
    final r = MentorReference.fromJson(
      const {'contentId': 7, 'slug': 'async-await', 'title': '비동기 기초'},
    );
    expect(r.contentId, 7);
    expect(r.slug, 'async-await');
    expect(r.title, '비동기 기초');
  });

  test('MentorState references 기본값은 빈 리스트', () {
    const s = MentorState();
    expect(s.references, isEmpty);
    expect(s.status, MentorStatus.idle);
    expect(s.messages, isEmpty);
  });
}
```

- [ ] **Step 2: 실패 확인**

```powershell
cd apps/web
flutter test test/features/mentor/mentor_state_test.dart
```

Expected: 컴파일 실패(`MentorReference` 미정의, `MentorState.references` 없음) → FAIL.

- [ ] **Step 3: 상태 타입 구현**

`apps/web/lib/src/features/mentor/state/mentor_state.dart` 전체를 아래로 교체:

```dart
/// 멘토 스트리밍 상태. ENG-REVIEW D1: P2 `SseStage`
/// (connecting/streaming/partial/reconnecting/complete/failed)를 단일 출처로 두고
/// 멘토가 **구독·매핑**한다 — 여기 enum은 그 평행정의를 최소화한 멘토 뷰 모델이며,
/// `partial`은 P4b `PathPhase.partial`과 동일 의미(끊김 시 부분답변 보존 + 재전송 가능).
enum MentorStatus { idle, streaming, partial, killSwitch, failed }

class ChatMessage {
  const ChatMessage({required this.fromUser, required this.text});
  final bool fromUser;
  final String text;
  ChatMessage append(String s) =>
      ChatMessage(fromUser: fromUser, text: text + s);
}

/// 참고자료 링크(슬라이스 #7 M-2 `event:references`). ai-svc가 질문 임베딩 →
/// learning 유사검색으로 내려주는 top-K 콘텐츠. mentor feature 내 plain 모델
/// (state 타입과 co-locate; dp_core 모델은 freezed 기반이라 패턴 분리).
class MentorReference {
  const MentorReference({
    required this.contentId,
    required this.slug,
    required this.title,
  });

  final int contentId;
  final String slug;
  final String title;

  factory MentorReference.fromJson(Map<String, dynamic> json) =>
      MentorReference(
        contentId: (json['contentId'] as num).toInt(),
        slug: json['slug'] as String,
        title: json['title'] as String,
      );
}

class MentorState {
  const MentorState({
    this.messages = const [],
    this.status = MentorStatus.idle,
    this.error,
    this.references = const [],
  });
  final List<ChatMessage> messages;
  final MentorStatus status;
  final String? error;

  /// `event:references`(1회) 결과. 도착 전/없으면 빈 리스트.
  final List<MentorReference> references;
}
```

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
flutter test test/features/mentor/mentor_state_test.dart
cd ../.. && git add apps/web/lib/src/features/mentor/state/mentor_state.dart apps/web/test/features/mentor/mentor_state_test.dart
git commit -m "feat(web): add MentorReference + MentorState.references for mentor SSE (slice7 F)"
```

Expected: 테스트 PASS.

---

## Task 2: mentor_sse_source — wire body 교체 + contentId 파라미터 + mock references

**Files:**
- Modify: `apps/web/lib/src/features/mentor/data/mentor_sse_source.dart`
- Test: `apps/web/test/features/mentor/mentor_sse_source_test.dart`(갱신)

**Interfaces:**
- Produces: `typedef MentorSseConnect = Stream<SseEvent> Function(String question, {String? contentId, int fromStep})`. 실 경로 wire body `{'message': question, 'contentId': contentId}`(`fromStep` 제거). mock 경로는 `token*` 후 `event:references`(고정 1개) 방출.

- [ ] **Step 1: 실패 테스트 작성**(mock이 token + references를 방출)

`apps/web/test/features/mentor/mentor_sse_source_test.dart` 전체 교체:

```dart
import 'dart:convert';

import 'package:devpath_web/src/features/mentor/data/mentor_sse_source.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('목 소스는 답변 토큰을 emit한다', () async {
    final c = ProviderContainer();
    addTearDown(c.dispose);
    final connect = c.read(mentorSseConnectProvider);
    final events = await connect('비동기란?').toList();
    final tokens = events
        .where((e) => e.event == 'token')
        .map((e) => e.data)
        .toList();
    expect(tokens, isNotEmpty);
    expect(tokens.join(), contains('async'));
  });

  test('목 소스는 references 이벤트를 1회 방출한다(JSON 배열)', () async {
    final c = ProviderContainer();
    addTearDown(c.dispose);
    final connect = c.read(mentorSseConnectProvider);
    final refs = await connect(
      '비동기란?',
    ).where((e) => e.event == 'references').toList();
    expect(refs, hasLength(1));
    final decoded = jsonDecode(refs.single.data) as List<dynamic>;
    expect(decoded, isNotEmpty);
    final first = decoded.first as Map<String, dynamic>;
    expect(first['contentId'], isA<int>());
    expect(first['slug'], isA<String>());
    expect(first['title'], isA<String>());
  });
}
```

- [ ] **Step 2: 실패 확인**

```powershell
cd apps/web
flutter test test/features/mentor/mentor_sse_source_test.dart
```

Expected: 두 번째 테스트 FAIL(현 mock은 token만 방출, references 없음).

- [ ] **Step 3: SSE 소스 구현**

`apps/web/lib/src/features/mentor/data/mentor_sse_source.dart` 전체 교체:

```dart
import 'dart:convert';

import 'package:dp_core/dp_core.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../providers/api_providers.dart';

/// 질문을 보내 SSE 이벤트를 흘리는 함수(슬라이스 #7 M-2 계약).
///
/// 와이어 body는 `{message, contentId?}`(빌드 D ai-svc). [contentId]는 옵셔널 —
/// 현재 콘텐츠 식별자가 있으면 전달, 없으면 null(독립 멘토 페이지는 null).
///
/// [fromStep](끊김 후 재개 시 이미 받은 토큰 수)은 **wire에서 제거**되었으나,
/// 시그니처 자리는 보존한다(I-3) — 백엔드가 `Last-Event-ID`/토큰 재개를 합의하면
/// 여기로 흘려보낸다(추측 금지, 자리만 둠; 현재 재개는 resend).
typedef MentorSseConnect =
    Stream<SseEvent> Function(
      String question, {
      String? contentId,
      int fromStep,
    });

const List<String> _kMockAnswer = [
  '비동기는 ',
  '`Future`와 ',
  '`async`/`await`로 ',
  '다룹니다. ',
  '스트림은 `Stream`을 구독하세요.',
];

/// 위젯/단위 테스트용 고정 참고자료(M-2 `event:references` 형태).
const List<Map<String, dynamic>> _kMockReferences = [
  {'contentId': 101, 'slug': 'async-await-basics', 'title': '비동기 기초: async/await'},
  {'contentId': 102, 'slug': 'dart-streams', 'title': 'Dart Stream 다루기'},
];

final mentorSseConnectProvider = Provider<MentorSseConnect>((ref) {
  final config = ref.watch(appConfigProvider);
  if (config.useMock) {
    return (question, {String? contentId, int fromStep = 0}) async* {
      for (final t in _kMockAnswer.sublist(
        fromStep.clamp(0, _kMockAnswer.length),
      )) {
        await Future<void>.delayed(const Duration(milliseconds: 120));
        yield SseEvent(event: 'token', data: t);
      }
      // 토큰 후 참고자료 1회(실서버 event:references 미러).
      yield SseEvent(event: 'references', data: jsonEncode(_kMockReferences));
    };
  }
  // ENG-REVIEW D1: `client.dio`를 직접 만지지 않는다 — `SseClient(client.dio)` 직접
  // 인스턴스화 금지. P2 `apiClient.sse(path, {body})` 헬퍼만 경유한다.
  final apiClient = ref.watch(apiClientProvider);
  return (question, {String? contentId, int fromStep = 0}) => apiClient.sse(
    '/ai-mentor/sessions',
    body: {'message': question, 'contentId': contentId},
  );
});
```

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
flutter test test/features/mentor/mentor_sse_source_test.dart
cd ../.. && git add apps/web/lib/src/features/mentor/data/mentor_sse_source.dart apps/web/test/features/mentor/mentor_sse_source_test.dart
git commit -m "feat(web): mentor SSE wire body {message,contentId} + mock references event (slice7 F)"
```

Expected: 두 테스트 PASS.

---

## Task 3: MentorController — e.event 분기 + references 상태 반영

**Files:**
- Modify: `apps/web/lib/src/features/mentor/application/mentor_controller.dart`
- Test: `apps/web/test/features/mentor/mentor_controller_test.dart`(references 케이스 추가 + 기존 회귀 유지)

**Interfaces:**
- Produces: `MentorController.send(String question, {String? contentId})`. `listen` 콜백: `e.event == 'references'`면 `e.data`를 JSON 디코드(`List`)해 `MentorReference.fromJson` 매핑 → `state.references` 갱신(버블 미변경). 그 외(token)는 기존대로 `targetIndex` 버블 append. onError(killSwitch/failed/partial)·onDone(idle)·prune 기존 유지. 모든 `MentorState` 재생성에서 **`references`를 보존**해 전달.

- [ ] **Step 1: 실패 테스트 작성**(references 이벤트 → state.references; token 회귀)

`apps/web/test/features/mentor/mentor_controller_test.dart`에 아래 테스트 2개를 **추가**(기존 테스트는 그대로 두되, Step 3 구현 후 전부 PASS 확인). 파일 상단 import에 `dart:convert` 추가:

```dart
import 'dart:convert';
```

기존 `void main() {` 블록 안(마지막 테스트 뒤)에 추가:

```dart
  test('references 이벤트 → state.references 반영(버블 미오염)', () async {
    Stream<SseEvent> withRefs(String q, {String? contentId, int fromStep = 0}) async* {
      yield SseEvent(event: 'token', data: '답변');
      yield SseEvent(
        event: 'references',
        data: jsonEncode(const [
          {'contentId': 7, 'slug': 'async', 'title': '비동기'},
        ]),
      );
    }

    final c = ProviderContainer(
      overrides: [mentorSseConnectProvider.overrideWithValue(withRefs)],
    );
    addTearDown(c.dispose);

    await c.read(mentorControllerProvider.notifier).send('질문');
    final s = c.read(mentorControllerProvider);

    expect(s.status, MentorStatus.idle);
    // 토큰만 버블에 — references는 버블에 append되지 않는다.
    expect(s.messages.last.text, '답변');
    expect(s.references, hasLength(1));
    expect(s.references.single.contentId, 7);
    expect(s.references.single.slug, 'async');
    expect(s.references.single.title, '비동기');
  });

  test('references 없이 토큰만 와도 정상(references 빈 리스트 유지)', () async {
    final c = ProviderContainer(
      overrides: [
        mentorSseConnectProvider.overrideWithValue(
          (q, {String? contentId, int fromStep = 0}) => _tokens(['토큰']),
        ),
      ],
    );
    addTearDown(c.dispose);

    await c.read(mentorControllerProvider.notifier).send('질문');
    final s = c.read(mentorControllerProvider);
    expect(s.status, MentorStatus.idle);
    expect(s.messages.last.text, '토큰');
    expect(s.references, isEmpty);
  });
```

또한 **기존 테스트의 override 람다 시그니처를 갱신**한다(typedef에 `contentId` 추가됨): 기존 `(q, {int fromStep = 0}) => ...` 4곳을 `(q, {String? contentId, int fromStep = 0}) => ...`로 수정. (`_tokens`/`partial` 헬퍼 시그니처도 `{String? contentId, int fromStep = 0}`로.)

- [ ] **Step 2: 실패 확인**

```powershell
cd apps/web
flutter test test/features/mentor/mentor_controller_test.dart
```

Expected: 컴파일 실패(override 람다가 새 typedef와 불일치) 또는 새 references 테스트 FAIL(`state.references` 미반영). → FAIL.

- [ ] **Step 3: 컨트롤러 구현**

`apps/web/lib/src/features/mentor/application/mentor_controller.dart` 전체 교체:

```dart
import 'dart:async';
import 'dart:convert';

import 'package:dp_core/dp_core.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/mentor_sse_source.dart';
import '../state/mentor_state.dart';

class MentorController extends Notifier<MentorState> {
  StreamSubscription<SseEvent>? _sub;

  @override
  MentorState build() {
    ref.onDispose(() => _sub?.cancel());
    return const MentorState();
  }

  /// 마지막으로 보낸 질문/콘텐츠 — partial 끊김 후 "다시 시도"(재전송)용.
  String? _lastQuestion;
  String? _lastContentId;

  /// 진행 중 send의 future. 새 send가 이전 구독을 취소할 때, 취소된 구독은
  /// onDone/onError가 호출되지 않아 이전 Completer가 영원히 미완료(hang)된다 →
  /// 새 send 시작 시 이전 in-flight를 완료해 대기 중인 future가 풀리게 한다.
  Completer<void>? _inFlight;

  /// 질문 전송. [contentId]는 현재 콘텐츠 식별자(옵셔널) — wire body로 전달된다.
  Future<void> send(String question, {String? contentId}) {
    if (question.trim().isEmpty) return Future.value();
    _sub?.cancel();
    // 취소된 이전 구독의 Completer를 완료(hang 방지).
    if (_inFlight != null && !_inFlight!.isCompleted) _inFlight!.complete();
    _lastQuestion = question;
    _lastContentId = contentId;
    final done = Completer<void>();
    _inFlight = done;

    final msgs = [
      ...state.messages,
      ChatMessage(fromUser: true, text: question),
      const ChatMessage(fromUser: false, text: ''),
    ];
    // 새 질문 시작 시 이전 참고자료는 비운다(이번 답변의 references만 표시).
    state = MentorState(messages: msgs, status: MentorStatus.streaming);

    // ENG-REVIEW(취소 경쟁조건): 토큰 대상 인덱스를 send 시점에 클로저로 캡처한다.
    // 연속 send 시 이전 스트림의 잔여 콜백이 새 멘토 버블(state.messages.last)에
    // 오append되는 것을 막는다 — append 대상은 항상 이 send가 만든 버블(targetIndex).
    final targetIndex = msgs.length - 1;

    _sub = ref
        .read(mentorSseConnectProvider)(question, contentId: contentId)
        .listen(
          (e) {
            // M-2: references 이벤트(1회)는 버블이 아니라 state.references로.
            if (e.event == 'references') {
              state = MentorState(
                messages: state.messages,
                status: state.status,
                error: state.error,
                references: _parseReferences(e.data),
              );
              return;
            }
            // token: 이 send가 만든 버블이 아직 마지막일 때만 갱신(취소된 잔여 콜백 무시).
            if (state.messages.length <= targetIndex) return;
            final m = [...state.messages];
            m[targetIndex] = m[targetIndex].append(e.data);
            state = MentorState(
              messages: m,
              status: MentorStatus.streaming,
              references: state.references,
            );
          },
          onError: (Object err) {
            final isKill = err is ApiException && err.isKillSwitch;
            // ENG-REVIEW D2: 부분답변은 보존하고 재전송 가능한 partial로 둔다.
            // KILL_SWITCH만 점검 분기 — 나머지 끊김은 partial(다시 시도) / API 에러는 failed.
            // M-2: kill-switch/quota는 개시 전 비-200 → 여기 ApiException으로 도달.
            final MentorStatus status;
            if (isKill) {
              status = MentorStatus.killSwitch;
            } else if (err is ApiException) {
              status = MentorStatus.failed;
            } else {
              status = MentorStatus.partial; // 네트워크 끊김 — 부분답변 보존
            }
            state = MentorState(
              messages: _pruneEmptyMentorBubble(state.messages, targetIndex),
              status: status,
              error: err is ApiException ? err.message : '연결이 끊겼어요',
              references: state.references,
            );
            if (!done.isCompleted) done.complete();
          },
          onDone: () {
            // ENG-REVIEW(빈/부분 버블 잔류): 토큰 0개로 끝나면 빈 멘토 버블을 제거한다.
            state = MentorState(
              messages: _pruneEmptyMentorBubble(state.messages, targetIndex),
              status: MentorStatus.idle,
              references: state.references,
            );
            if (!done.isCompleted) done.complete();
          },
          cancelOnError: true,
        );

    return done.future;
  }

  /// `event:references` data(JSON 배열) → `MentorReference` 목록.
  /// 파싱 실패(형식 오류)는 빈 리스트로 폴백(토큰 스트림은 무관하게 진행).
  List<MentorReference> _parseReferences(String data) {
    try {
      final decoded = jsonDecode(data);
      if (decoded is! List) return const [];
      return decoded
          .whereType<Map<String, dynamic>>()
          .map(MentorReference.fromJson)
          .toList();
    } catch (_) {
      return const [];
    }
  }

  /// 끊김/완료 시 [targetIndex]의 멘토 버블이 비어 있으면 제거(빈 버블 잔류 방지).
  List<ChatMessage> _pruneEmptyMentorBubble(
    List<ChatMessage> msgs,
    int targetIndex,
  ) {
    if (targetIndex < msgs.length &&
        !msgs[targetIndex].fromUser &&
        msgs[targetIndex].text.isEmpty) {
      return [...msgs]..removeAt(targetIndex);
    }
    return msgs;
  }

  /// partial 끊김 후 "다시 시도" — 마지막 질문을 재전송(resend).
  /// ENG-REVIEW D2: 토큰 단위 재개(Last-Event-ID)는 백엔드 합의 후속. 현재는 resend.
  Future<void> retry() {
    final q = _lastQuestion;
    if (q == null) return Future.value();
    return send(q, contentId: _lastContentId);
  }
}

final mentorControllerProvider =
    NotifierProvider<MentorController, MentorState>(MentorController.new);
```

> 주의: token append 시 `references: state.references`를 함께 전달해 references 도착 순서(토큰 전/후 무관)와 관계없이 보존한다(M-2: references는 토큰 스트림과 독립, 순서 보장 불필요).

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
flutter test test/features/mentor/mentor_controller_test.dart
cd ../.. && git add apps/web/lib/src/features/mentor/application/mentor_controller.dart apps/web/test/features/mentor/mentor_controller_test.dart
git commit -m "feat(web): branch SSE event=references into MentorState.references, keep token/onError/onDone (slice7 F)"
```

Expected: 신규 references 2종 + 기존 회귀(idle/killSwitch/partial/prune/취소경쟁) 전부 PASS.

---

## Task 4: MentorPage — 참고자료 패널(_FollowUpSlot 교체)

**Files:**
- Modify: `apps/web/lib/src/features/mentor/presentation/mentor_page.dart`
- Test: `apps/web/test/features/mentor/mentor_page_test.dart`(참고자료 렌더 테스트 추가)

**Interfaces:**
- Consumes: `MentorState.references`. 비어 있으면 미표시, 있으면 칩 리스트로 제목 렌더. 기존 버블/partial/failed/killSwitch/composer 구조 유지.

- [ ] **Step 1: 실패 테스트 작성**(references 도착 시 패널 칩 렌더)

`apps/web/test/features/mentor/mentor_page_test.dart`의 `void main() {` 안에 아래 테스트를 **추가**. 파일 상단 import에 `dart:convert` 추가:

```dart
import 'dart:convert';
```

추가 테스트:

```dart
  testWidgets('참고자료 references 도착 시 칩으로 렌더', (tester) async {
    Stream<SseEvent> withRefs(String q, {String? contentId, int fromStep = 0}) async* {
      yield SseEvent(event: 'token', data: '답변본문');
      yield SseEvent(
        event: 'references',
        data: jsonEncode(const [
          {'contentId': 9, 'slug': 'streams', 'title': 'Stream 가이드'},
        ]),
      );
    }

    final c = ProviderContainer(
      overrides: [mentorSseConnectProvider.overrideWithValue(withRefs)],
    );
    addTearDown(c.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: c,
        child: MaterialApp(theme: DpTheme.light(), home: const MentorPage()),
      ),
    );

    await tester.enterText(find.byType(TextField), '비동기란?');
    await tester.tap(find.byTooltip('전송'));
    await tester.pumpAndSettle();

    expect(find.text('답변본문'), findsOneWidget); // 답변 누적
    expect(find.text('참고자료'), findsOneWidget); // 패널 헤더
    expect(find.text('Stream 가이드'), findsOneWidget); // 참고자료 칩(제목)
  });
```

`mentorSseConnectProvider`/`SseEvent` import가 이미 있는지 확인(기존 파일은 `mentor_sse_source.dart`·`dp_core` import 보유 → 추가 import 불요, `dart:convert`만 추가).

- [ ] **Step 2: 실패 확인**

```powershell
cd apps/web
flutter test test/features/mentor/mentor_page_test.dart
```

Expected: 새 테스트 FAIL(`참고자료` 헤더/칩 미존재 — 현재 `_FollowUpSlot`만 있음).

- [ ] **Step 3: 페이지 구현**

`apps/web/lib/src/features/mentor/presentation/mentor_page.dart`에서 두 곳을 수정한다.

(a) `build` 메서드 안의 `_FollowUpSlot` 사용부를 참고자료 패널로 교체. 기존:

```dart
          // ENG-REVIEW(P3): 응답 완료(idle) 시 후속질문 슬롯 — 자리표시만.
          // 후속질문 *추천*(서버 payload 기반)은 후속(리스크 절 참조).
          if (s.status == MentorStatus.idle && s.messages.isNotEmpty)
            const _FollowUpSlot(),
```

를 아래로 교체:

```dart
          // 슬라이스 #7 M-2: 참고자료(event:references) — 있으면 칩으로 렌더, 없으면 미표시.
          if (s.references.isNotEmpty) _ReferencePanel(references: s.references),
```

(b) 파일 하단의 `_FollowUpSlot` 클래스 전체를 아래 `_ReferencePanel`로 교체:

```dart
/// 참고자료 패널(슬라이스 #7 M-2). `event:references`로 받은 콘텐츠 링크를
/// 칩으로 렌더한다. 비어 있으면 호출부에서 미표시.
class _ReferencePanel extends StatelessWidget {
  const _ReferencePanel({required this.references});
  final List<MentorReference> references;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: DpSpacing.lg,
        vertical: DpSpacing.sm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '참고자료',
            style: Theme.of(
              context,
            ).textTheme.labelMedium?.copyWith(color: c.textSecondary),
          ),
          const SizedBox(height: DpSpacing.xs),
          Wrap(
            spacing: DpSpacing.sm,
            runSpacing: DpSpacing.xs,
            children: [
              for (final r in references)
                ActionChip(
                  key: ValueKey('ref-${r.contentId}'),
                  avatar: const Icon(DpIcons.content, size: 16),
                  label: Text(r.title),
                  onPressed: () => context.go('/content/${r.slug}'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
```

> ⚠️ **칩 탭 라우팅 확인**: `context.go('/content/${r.slug}')`는 콘텐츠 상세 라우트로의 이동이다. **라우트 경로(`/content/:slug` 형태)와 `context.go`(go_router) 사용 가능 여부를 `apps/web/lib/src/app/router.dart`에서 확인 후 정정한다**(추측 금지). 콘텐츠 상세 라우트가 slug가 아니라 id 기반이거나 경로가 다르면 그에 맞춘다. 만약 콘텐츠 상세 라우트가 미존재면 `onPressed: null`(비활성 칩, 제목 표시만)로 두고 라우팅은 후속으로 명시한다. `import 'package:go_router/go_router.dart';`가 필요하면 추가(`context.go` 확장 제공). `DpIcons.content` 심볼 존재도 `dp_design`에서 확인(없으면 `DpIcons.path` 등 실재 아이콘으로 대체).

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
flutter test test/features/mentor/
cd ../.. && git add apps/web/lib/src/features/mentor/presentation/mentor_page.dart apps/web/test/features/mentor/mentor_page_test.dart
git commit -m "feat(web): render mentor references panel (replace _FollowUpSlot) (slice7 F)"
```

Expected: mentor 위젯/컨트롤러 테스트 전부 PASS.

---

## Task 5: documents — learning-svc/CLAUDE.md 도메인표 정정(M-9)

> 설계 §5(documents)·M-9: `learning-svc/CLAUDE.md` 도메인표의 `mentor` 행은 1st Aha 초기 계획 잔재(stale) → 멘토는 ai-svc 소관임을 명기. **이 변경은 `devpath-frontend`가 아니라 `devpath-learning`(learning-svc) 레포 또는 documents 레포에 위치**할 수 있음 — 실제 파일 위치를 먼저 확인하고, 위치에 맞는 레포의 develop 브랜치에서 별도 처리한다.

- [ ] **Step 1: 대상 파일 위치 확인(추측 금지)**

`learning-svc/CLAUDE.md`의 실제 경로를 확인한다(별도 레포 `devpath-learning`의 루트 `CLAUDE.md`일 가능성). frontend 레포 밖이면 **본 빌드 F의 frontend PR과 분리**하여 해당 레포에서 처리한다.

```powershell
# 예: learning 레포가 형제 디렉터리에 있으면
#   ls ../devpath-learning/CLAUDE.md
# documents 레포 내 사본이면 grep으로 mentor 행 위치 확인.
```

- [ ] **Step 2: 도메인표 `mentor` 행 정정**

해당 `CLAUDE.md` 도메인표에서 `mentor`를 learning-svc 소관으로 둔 행을 **"멘토는 ai-svc(`ai-mentor/**`) 소관 — 본 행은 1st Aha 잔재"** 로 정정(표 형식 보존, 한 줄 주석/이관 명기). 코드 변경 없음(문서 정합성).

> ⚠️ 이 Task는 frontend 빌드와 **독립**이다. 파일이 frontend 레포 밖이면 Task 4까지 frontend PR을 먼저 완료하고, 이 정정은 해당 레포 별도 PR(`docs/*`)로 처리한다. frontend 레포에 사본이 없으면 본 Task는 **NEEDS_CONTEXT로 보고**(위치 미확정 시 추측 금지).

---

## Task 6: 전체 회귀 + format + develop PR

- [ ] **Step 1: melos format + analyze + test(전 패키지)**

```powershell
dart pub global run melos run format
dart pub global run melos run analyze
dart pub global run melos run test
```

Expected: format 변경 없음(CI 게이트 `--set-exit-if-changed` 통과), 분석 0 이슈, web 테스트(mentor 신규 references/state/source + 기존 token/killSwitch/partial/prune/취소경쟁 회귀) 전부 PASS, dp_core 무변경 회귀 없음. (골든 제외 CI 동등.)

- [ ] **Step 2: PR 생성·CI·머지**

```powershell
git push -u origin feat/slice7-frontend-mentor-sse
gh pr create --base develop --title "feat(web): AI 멘토 SSE 실API 전환 + 참고자료 렌더(슬라이스 #7 빌드 F)" --body "mentor mock→실API: wire body {message,contentId?}(M-2), event:token 누적 + event:references(1회) 파싱→참고자료 패널. 개시 전 비-200(kill-switch 503/quota 429)→기존 ApiException.isKillSwitch/isQuota, LLM 실패 completeWithError→기존 onError, 정상 close→onDone. in-band error/done 없음(C-1). 취소경쟁/hang/prune/retry 기존 로직 유지. 설계서 docs/superpowers/specs/2026-06-24-md3-slice7-ai-mentor-design.md §5·§9 F·M-2"
gh pr checks --watch
gh pr merge --merge
```

Expected: frontend CI(`analyze-test`, `format`) 녹색. 앱이라 main 릴리스는 슬라이스 통합 릴리스에서.

---

## Self-Review 메모(작성자)

- **Spec 커버리지(§5 frontend·§9 빌드 F·M-2·C-1)**: 변경 4건 전부 매핑 —
  - C-1 ① `mentor_sse_source` wire body `{message, contentId}` 교체(`fromStep` wire 제거, typedef 자리 보존) = Task 2.
  - C-1 ② 컨트롤러 `e.event=='references'` 분기(JSON→state.references), token/onDone/onError(killSwitch/failed/partial) 기존 유지, in-band error/done 없음 = Task 3.
  - C-1 ③ `MentorState.references` + `MentorReference{contentId,slug,title}` = Task 1.
  - C-1 ④ `_FollowUpSlot`→참고자료 패널(빈 배열 미표시) = Task 4.
  - mock references 1회 방출 = Task 2(`mentorSseConnectProvider` useMock 분기).
  - M-9 documents 정정 = Task 5(위치 확인 후, 필요 시 분리/NEEDS_CONTEXT).
- **placeholder 없음**: 상태/소스/컨트롤러/패널 전량 실제 Dart. 모든 테스트 구체 단언.
- **실측 기반(추측 금지)**: ① `apiClient.sse`/`SseClient.connect` 시그니처·비-200 throw·200 후 `SseEvent{event,data}` yield(실소스 확인 → `e.event` 분기 가능) ② `ApiException.isKillSwitch/isQuota`·`ApiErrorCode` 매핑(변경 없음) ③ `api_providers.dart` 실경로 `lib/src/providers/`(지시서 `features/providers/`는 오기 — 정정 명시) ④ 패키지명 `devpath_web` ⑤ mentor mock은 fixture 아닌 provider 인라인(실측) ⑥ `MentorPage`는 contentId 없는 독립 라우트(`router.dart` 확인) → send의 contentId는 null 전달(없는 콘텐츠 컨텍스트를 발명하지 않음).
- **타입/계약 일관성**: `MentorReference.fromJson`(num→int)·wire `{message,contentId}`(빌드 D M-2)·`event:references` data=JSON 배열·`MentorStatus` 5종 재사용·`references` 모든 state 재생성에서 보존(순서 독립, M-2). kill-switch/quota는 **개시 전 비-200**이라 기존 stream-error→ApiException 경로 그대로(빌드 E gateway/D ai-svc가 비-200 반환 책임 — 프론트는 소비만).
- **확인 필요 지점 2곳(구현 시 실소스 확정, 추측 금지 명시)**: ① 참고자료 칩 탭 라우트(`/content/:slug` vs id, `context.go`/go_router import, 라우트 미존재 시 비활성 칩) — `router.dart` 확인 후 정정. ② `DpIcons.content` 심볼 존재 — `dp_design` 확인 후 없으면 실재 아이콘 대체. 두 지점 모두 Task 4 Step 3에 경고로 명시.
- **회귀 보호**: 기존 mentor 컨트롤러/페이지 테스트의 override 람다 시그니처를 새 typedef(`{String? contentId, int fromStep}`)로 갱신(Task 3 Step 1 명시). 기존 token-only·killSwitch·partial·prune·취소경쟁 테스트는 의미 보존.
- **Scope Lock**: 빌드 F(frontend 4파일 + 테스트 3 + documents 1)만. 빌드 A~E(shared/sandbox/learning/ai-svc/gateway) 미포함. Task 5는 frontend 레포 밖이면 분리/NEEDS_CONTEXT.
