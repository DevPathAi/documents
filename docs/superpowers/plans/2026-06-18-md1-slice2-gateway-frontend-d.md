# 슬라이스 #2 빌드 D — gateway 라우트 + frontend 진단 실API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gateway에 `/onboarding/assessments/**` → learning-svc 라우트를 추가하고(guest 경로 공개), frontend web 온보딩 진단을 목→실API로 전환한다(비회원 guest 진단 → 가입 게이트 → claim → 결과, 회원 진단).

**Architecture:** ⚠️ **상류 계약 재검증 게이트** — 빌드 B(learning-svc) 실제 엔드포인트/DTO를 소스로 교차검증 후 진행. gateway는 Spring Cloud Gateway(WebFlux) 라우트 1개 추가 + guest permitAll. frontend는 dp_core에 진단 모델·API 클라이언트를 추가하고, riverpod Notifier로 진단 흐름을, 기존 목 프로토(`onboarding`)를 실API 화면으로 전환한다. 목 모드(`USE_MOCK=true`)는 실계약과 정합한 픽스처로 유지.

**Tech Stack:** (gateway) Spring Boot 4.0.7 · Spring Cloud Gateway WebFlux. (frontend) Flutter Web · dp_core(freezed/json_serializable) · flutter_riverpod · dio(ApiClient) · go_router · dp_design.

## Global Constraints

- 각 레포 절대조건: 추측 금지 · **테스트 우선** · 문제 시 코드 분석.
- 브랜치: 각 레포 develop 분기 → develop PR, CI 녹색 후 merge commit.
- **선행**: 빌드 B-1·B-2 develop 머지(learning 엔드포인트 존재), 빌드 C 머지(상태 전이). gateway/frontend는 **learning 실소스로 계약 재검증** 후 구현.
- 인증/쿠키(슬라이스 #1): gateway JWT 엣지 검증 + Authorization 헤더 전달, CORS allow-credentials. web `withCredentials:true`(쿠키 왕복). guest 경로는 JWT 불요.
- 엔드포인트 계약(빌드 B 확정): 회원 `POST /onboarding/assessments`{track}→{assessmentId}, `GET /{id}/next`→{question,index,total}, `POST /{id}/answer`{questionId,answer,skipped,timeSpentSec}, `POST /{id}/complete`→result, `GET /{id}/result`. guest `POST /onboarding/assessments/guest`{track}→{guestAssessmentId}, `GET /guest/{gid}/next`, `POST /guest/{gid}/answer`, `POST /guest/{gid}/complete`→result. `POST /onboarding/assessments/claim`{guest_assessment_id}→{assessmentId}.
- 총 15문항 고정, "잘 모르겠어요"=skip(감점 없음). answer_key는 응답에 미노출.
- frontend 빌드/테스트: 루트에서 `melos run analyze`·`melos run test`. 모델 변경 시 `dart run build_runner build --delete-conflicting-outputs`(dp_core).

---

## File Structure (gateway)

- Modify: `src/main/resources/application.yml` — learning 라우트
- Modify: `src/main/java/ai/devpath/gateway/config/GatewaySecurityConfig.java` — guest permitAll
- Modify/Create: gateway 라우팅 테스트

## File Structure (frontend)

- Create: `packages/dp_core/lib/src/models/assessment.dart` (+regen) — Question/AssessmentResult/NextQuestion 모델
- Modify: `packages/dp_core/lib/dp_core.dart` (barrel) — export
- Create: `packages/dp_core/lib/src/api/assessment_api.dart` — 진단 API 클라이언트
- Create: `apps/web/lib/src/features/diagnostic/...` — 진단 controller/state/page
- Modify: `apps/web/lib/src/data/web_mock_fixtures.dart` — 진단 목 픽스처(실계약 정합)
- Modify: 라우터(진단 경로) — 기존 `/onboarding` 흐름에 결선

---

## Task 0: 상류 계약 재검증 (⚠️ 게이트, 코드 변경 없음)

- [ ] **Step 1: learning-svc 실소스로 엔드포인트·DTO 교차검증**

devpath-learning-svc의 `AssessmentController`·`GuestAssessmentController`·`ClaimController`·`dto/*`를 읽고, 본 플랜 "Global Constraints의 엔드포인트 계약"과 **경로·메서드·요청/응답 필드명**이 일치하는지 확인한다. 불일치 시 이 플랜의 후속 Task 코드를 실제 계약으로 정정 후 진행(추측 금지).

Expected: 계약 일치 확인 또는 정정 목록 도출.

---

## Task 1: gateway — learning 라우트 + guest 공개경로

**Files:**
- Modify: `src/main/resources/application.yml`
- Modify: `src/main/java/ai/devpath/gateway/config/GatewaySecurityConfig.java`
- Create: `src/test/java/ai/devpath/gateway/AssessmentRouteTest.java`

**Interfaces:**
- Produces: 라우트 `learning`(Path=`/onboarding/assessments/**` → `${LEARNING_URI}`). 공개경로에 `/onboarding/assessments/guest/**` 추가(JWT 불요). 그 외 진단 경로는 authenticated(엣지).

- [ ] **Step 1: 공개/보호 경로 라우팅 테스트 작성(실패)**

`AssessmentRouteTest.java` — WebTestClient로 guest 경로는 인증 없이 통과(상류 미가동이라 5xx/연결오류여도 401이 아님), 보호 경로는 401:

```java
package ai.devpath.gateway;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.reactive.server.WebTestClient;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class AssessmentRouteTest {

  @LocalServerPort int port;

  @Test
  void guestPathIsPublic_notUnauthorized() {
    WebTestClient client = WebTestClient.bindToServer()
        .baseUrl("http://localhost:" + port).build();
    client.post().uri("/onboarding/assessments/guest").exchange()
        .expectStatus().value(s -> org.assertj.core.api.Assertions.assertThat(s)
            .isNotEqualTo(HttpStatus.UNAUTHORIZED.value()));
  }

  @Test
  void protectedAssessmentPathIsUnauthorizedWithoutJwt() {
    WebTestClient client = WebTestClient.bindToServer()
        .baseUrl("http://localhost:" + port).build();
    client.get().uri("/onboarding/assessments/1/next").exchange()
        .expectStatus().isUnauthorized();
  }
}
```

- [ ] **Step 2: 실패 확인**

```bash
./gradlew test --tests ai.devpath.gateway.AssessmentRouteTest
```
Expected: FAIL(guest 경로가 보호되어 401, 또는 라우트 없음).

- [ ] **Step 3: application.yml에 learning 라우트 추가**

`src/main/resources/application.yml`의 `routes:` 목록에 추가(기존 platform-auth 라우트 아래):

```yaml
            - id: learning
              uri: ${LEARNING_URI:http://localhost:8082}
              predicates:
                - Path=/onboarding/assessments/**
```

- [ ] **Step 4: GatewaySecurityConfig에 guest 공개경로 추가**

`securityWebFilterChain`의 `pathMatchers(...permitAll)`에 `/onboarding/assessments/guest/**`를 추가:

```java
				.pathMatchers("/oauth2/**", "/login/**", "/auth/refresh", "/auth/logout",
						"/onboarding/assessments/guest/**", "/actuator/health").permitAll()
```

- [ ] **Step 5: 테스트 통과 확인 + 커밋**

```bash
./gradlew test --tests ai.devpath.gateway.AssessmentRouteTest
git add src/main/resources/application.yml \
        src/main/java/ai/devpath/gateway/config/GatewaySecurityConfig.java \
        src/test/java/ai/devpath/gateway/AssessmentRouteTest.java
git commit -m "feat(route): learning 진단 라우트 + guest 공개경로"
```
Expected: PASS. develop PR → CI 녹색 → 머지.

> 배포 env: `LEARNING_URI`(배포 `http://devpath-learning-svc:8080`), 로컬 learning 포트(예 8082)로 동시구동. CORS_ALLOWED_ORIGINS·JWT_SECRET은 슬라이스 #1과 동일.

---

## Task 2: dp_core — 진단 모델

**Files:**
- Create: `packages/dp_core/lib/src/models/assessment.dart`
- Modify: `packages/dp_core/lib/dp_core.dart`
- Create: `packages/dp_core/test/models/assessment_test.dart`

**Interfaces:**
- Produces:
  - `AssessmentQuestion(int id, String type, String content, String? options, String bloomLevel, double difficulty)`.
  - `NextQuestion(AssessmentQuestion question, int index, int total)`.
  - `AssessmentResult(String diagnosedLevel, double? confidenceWeight)`(강·약점은 후속).
  - 모두 `fromJson` 지원(freezed/json_serializable).

- [ ] **Step 1: 모델 역직렬화 실패 테스트 작성**

`assessment_test.dart`:

```dart
import 'package:dp_core/src/models/assessment.dart';
import 'package:test/test.dart';

void main() {
  test('NextQuestion 역직렬화', () {
    final n = NextQuestion.fromJson({
      'question': {
        'id': 7,
        'type': 'MCQ',
        'content': '스프링 빈 스코프?',
        'options': '["singleton","prototype"]',
        'bloomLevel': 'UNDERSTAND',
        'difficulty': 0.3,
      },
      'index': 3,
      'total': 15,
    });
    expect(n.question.id, 7);
    expect(n.total, 15);
    expect(n.question.bloomLevel, 'UNDERSTAND');
  });

  test('AssessmentResult 역직렬화', () {
    final r = AssessmentResult.fromJson({'diagnosedLevel': 'MID', 'confidenceWeight': 0.8});
    expect(r.diagnosedLevel, 'MID');
    expect(r.confidenceWeight, 0.8);
  });
}
```

- [ ] **Step 2: 실패 확인**

```bash
cd packages/dp_core && dart test test/models/assessment_test.dart
```
Expected: FAIL(`assessment.dart` 미존재).

- [ ] **Step 3: assessment.dart 작성**

`packages/dp_core/lib/src/models/assessment.dart`:

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'assessment.freezed.dart';
part 'assessment.g.dart';

/// 진단 문항 뷰(정답 키 미포함).
@freezed
abstract class AssessmentQuestion with _$AssessmentQuestion {
  const factory AssessmentQuestion({
    required int id,
    required String type,
    required String content,
    String? options,
    required String bloomLevel,
    required double difficulty,
  }) = _AssessmentQuestion;

  factory AssessmentQuestion.fromJson(Map<String, dynamic> json) =>
      _$AssessmentQuestionFromJson(json);
}

/// 적응형 다음 문항 + 진행률.
@freezed
abstract class NextQuestion with _$NextQuestion {
  const factory NextQuestion({
    required AssessmentQuestion question,
    required int index,
    required int total,
  }) = _NextQuestion;

  factory NextQuestion.fromJson(Map<String, dynamic> json) =>
      _$NextQuestionFromJson(json);
}

/// 진단 결과(강·약점은 후속 확장).
@freezed
abstract class AssessmentResult with _$AssessmentResult {
  const factory AssessmentResult({
    required String diagnosedLevel,
    double? confidenceWeight,
  }) = _AssessmentResult;

  factory AssessmentResult.fromJson(Map<String, dynamic> json) =>
      _$AssessmentResultFromJson(json);
}
```

- [ ] **Step 4: barrel export 추가**

`packages/dp_core/lib/dp_core.dart`에 다른 model export 옆에 추가:

```dart
export 'src/models/assessment.dart';
```

- [ ] **Step 5: 코드 생성 + 테스트 통과 + 커밋**

```bash
cd packages/dp_core
dart run build_runner build --delete-conflicting-outputs
dart test test/models/assessment_test.dart
```
Expected: PASS.

```bash
git add packages/dp_core/lib/src/models/assessment.dart \
        packages/dp_core/lib/src/models/assessment.g.dart \
        packages/dp_core/lib/src/models/assessment.freezed.dart \
        packages/dp_core/lib/dp_core.dart \
        packages/dp_core/test/models/assessment_test.dart
git commit -m "feat(dp_core): 진단 모델(AssessmentQuestion/NextQuestion/AssessmentResult)"
```

---

## Task 3: dp_core — 진단 API 클라이언트

**Files:**
- Create: `packages/dp_core/lib/src/api/assessment_api.dart`
- Modify: `packages/dp_core/lib/dp_core.dart`
- Create: `packages/dp_core/test/api/assessment_api_test.dart`

**Interfaces:**
- Consumes: `ApiClient`(post/get).
- Produces: `AssessmentApi(ApiClient client)` 메서드:
  - `Future<String> startGuest(String track)` → guestAssessmentId
  - `Future<int> startMember(String track)` → assessmentId
  - `Future<NextQuestion?> next({int? assessmentId, String? guestId})` (204→null)
  - `Future<void> answer({int? assessmentId, String? guestId, required int questionId, String? answer, required bool skipped, int? timeSpentSec})`
  - `Future<AssessmentResult> complete({int? assessmentId, String? guestId})`
  - `Future<int> claim(String guestAssessmentId)` → assessmentId

- [ ] **Step 1: API 클라이언트 테스트 작성(MockHttpAdapter)**

`assessment_api_test.dart` — dp_core 기존 `MockHttpAdapter`/`ApiClient` 테스트 패턴을 따라 start/next/answer/complete 경로·응답 매핑 검증. (기존 `test/api/api_client_test.dart`·`test/mock/*` 패턴 참조.)

```dart
import 'package:dp_core/dp_core.dart';
import 'package:test/test.dart';

void main() {
  ApiClient mockClient(Map<String, dynamic> fixtures) {
    final c = ApiClient.create(const ApiConfig(baseUrl: 'http://t', useMock: true));
    c.dio.httpClientAdapter = MockHttpAdapter(fixtures);
    return c;
  }

  test('startGuest는 guestAssessmentId를 반환', () async {
    final api = AssessmentApi(mockClient({
      'POST /onboarding/assessments/guest': {'guestAssessmentId': 'g-123'},
    }));
    expect(await api.startGuest('BACKEND_SPRING'), 'g-123');
  });

  test('next는 NextQuestion 매핑', () async {
    final api = AssessmentApi(mockClient({
      'GET /onboarding/assessments/guest/g-123/next': {
        'question': {'id': 1, 'type': 'MCQ', 'content': 'Q', 'options': null,
            'bloomLevel': 'REMEMBER', 'difficulty': 0.3},
        'index': 1, 'total': 15,
      },
    }));
    final n = await api.next(guestId: 'g-123');
    expect(n!.question.id, 1);
  });
}
```

> 주: `MockHttpAdapter`의 픽스처 키 형식은 dp_core 기존 테스트(`test/mock/mock_test.dart`)를 확인해 정확히 맞춘다(예: `"METHOD path"`). 불일치 시 그 형식으로 정정.

- [ ] **Step 2: 실패 확인**

```bash
cd packages/dp_core && dart test test/api/assessment_api_test.dart
```
Expected: FAIL(`AssessmentApi` 미존재).

- [ ] **Step 3: AssessmentApi 구현**

`packages/dp_core/lib/src/api/assessment_api.dart`:

```dart
import '../models/assessment.dart';
import 'api_client.dart';

/// 진단 API 클라이언트. 회원(assessmentId)·비회원(guestId) 동일 인터페이스.
class AssessmentApi {
  AssessmentApi(this.client);

  final ApiClient client;

  String _base({int? assessmentId, String? guestId}) {
    if (guestId != null) return '/onboarding/assessments/guest/$guestId';
    return '/onboarding/assessments/$assessmentId';
  }

  Future<String> startGuest(String track) async {
    final data = await client.post<Map<String, dynamic>>(
      '/onboarding/assessments/guest', body: {'track': track});
    return data['guestAssessmentId'] as String;
  }

  Future<int> startMember(String track) async {
    final data = await client.post<Map<String, dynamic>>(
      '/onboarding/assessments', body: {'track': track});
    return data['assessmentId'] as int;
  }

  Future<NextQuestion?> next({int? assessmentId, String? guestId}) async {
    final data = await client.get<Map<String, dynamic>?>(
      '${_base(assessmentId: assessmentId, guestId: guestId)}/next');
    if (data == null) return null; // 204 No Content = 종료
    return NextQuestion.fromJson(data);
  }

  Future<void> answer({
    int? assessmentId, String? guestId,
    required int questionId, String? answer,
    required bool skipped, int? timeSpentSec,
  }) async {
    await client.post<void>(
      '${_base(assessmentId: assessmentId, guestId: guestId)}/answer',
      body: {
        'questionId': questionId,
        'answer': answer,
        'skipped': skipped,
        'timeSpentSec': timeSpentSec,
      });
  }

  Future<AssessmentResult> complete({int? assessmentId, String? guestId}) async {
    final data = await client.post<Map<String, dynamic>>(
      '${_base(assessmentId: assessmentId, guestId: guestId)}/complete');
    return AssessmentResult.fromJson(data);
  }

  Future<int> claim(String guestAssessmentId) async {
    final data = await client.post<Map<String, dynamic>>(
      '/onboarding/assessments/claim',
      body: {'guest_assessment_id': guestAssessmentId});
    return data['assessmentId'] as int;
  }
}
```

> 주: `ApiClient`의 `get`/`post` 시그니처(제네릭·204 처리)는 dp_core 기존 `api_client.dart`를 확인해 정확히 맞춘다(특히 204→null 반환 가능 여부). 다르면 정정.

- [ ] **Step 4: barrel export + 테스트 통과 + 커밋**

`dp_core.dart`에 `export 'src/api/assessment_api.dart';` 추가.

```bash
cd packages/dp_core && dart test test/api/assessment_api_test.dart
git add packages/dp_core/lib/src/api/assessment_api.dart packages/dp_core/lib/dp_core.dart \
        packages/dp_core/test/api/assessment_api_test.dart
git commit -m "feat(dp_core): 진단 API 클라이언트(회원/비회원/claim)"
```

---

## Task 4: web — 진단 컨트롤러 + 상태

**Files:**
- Create: `apps/web/lib/src/features/diagnostic/state/diagnostic_state.dart`
- Create: `apps/web/lib/src/features/diagnostic/application/diagnostic_controller.dart`
- Create: `apps/web/test/features/diagnostic/diagnostic_controller_test.dart`

**Interfaces:**
- Consumes: `AssessmentApi`(provider), `authControllerProvider`(로그인 여부).
- Produces: `DiagnosticController extends Notifier<DiagnosticState>` — `startAsGuest(track)`·`startAsMember(track)`·`submitAnswer(...)`·`skip()`·`complete()`·`claimAfterLogin()`. 상태: Idle/Loading/Question(NextQuestion)/GateSignup(guest 완료, 로그인 유도)/Result(AssessmentResult)/Error.

- [ ] **Step 1: 컨트롤러 흐름 테스트 작성(목 API 주입)**

`diagnostic_controller_test.dart` — `assessmentApiProvider`를 Fake로 override해 guest start→question→answer→complete→GateSignup 전이를 검증(`ProviderContainer`). (web 기존 `auth_controller` 테스트의 override 패턴 참조.)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// import 경로는 실제 패키지명에 맞춘다(devpath_web).

void main() {
  test('guest 진단: 시작→문항→완료→가입게이트', () async {
    // Fake AssessmentApi를 assessmentApiProvider로 override.
    // start→ guestId, next→ 15회 후 null, complete→ GateSignup.
    // (구현 후 상세 단언 채움 — 상태 전이 Idle→Question→...→GateSignup)
  });
}
```

> 주: 이 테스트는 구현(Step 3)과 함께 구체화한다. Fake API는 15문항 후 `next`가 null을 반환하도록 하고, 컨트롤러가 `complete()`를 호출해 guest는 GateSignup으로 전이하는지 단언한다.

- [ ] **Step 2: DiagnosticState 작성**

`diagnostic_state.dart`:

```dart
import 'package:dp_core/dp_core.dart';

sealed class DiagnosticState {
  const DiagnosticState();
}

class DiagnosticIdle extends DiagnosticState { const DiagnosticIdle(); }
class DiagnosticLoading extends DiagnosticState { const DiagnosticLoading(); }

class DiagnosticQuestion extends DiagnosticState {
  const DiagnosticQuestion(this.next);
  final NextQuestion next;
}

/// 비회원 진단 완료 → 결과 직전 가입 게이트.
class DiagnosticGateSignup extends DiagnosticState { const DiagnosticGateSignup(); }

class DiagnosticResultState extends DiagnosticState {
  const DiagnosticResultState(this.result);
  final AssessmentResult result;
}

class DiagnosticError extends DiagnosticState {
  const DiagnosticError(this.message);
  final String message;
}
```

- [ ] **Step 3: DiagnosticController 작성**

`diagnostic_controller.dart`:

```dart
import 'package:dp_core/dp_core.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../providers/api_providers.dart';
import '../../auth/application/auth_controller.dart';
import '../state/diagnostic_state.dart';

final assessmentApiProvider = Provider<AssessmentApi>(
  (ref) => AssessmentApi(ref.read(apiClientProvider)),
);

class DiagnosticController extends Notifier<DiagnosticState> {
  @override
  DiagnosticState build() => const DiagnosticIdle();

  int? _assessmentId;
  String? _guestId;

  AssessmentApi get _api => ref.read(assessmentApiProvider);

  Future<void> startAsMember(String track) async {
    state = const DiagnosticLoading();
    try {
      _assessmentId = await _api.startMember(track);
      _guestId = null;
      await _advance();
    } on ApiException catch (e) {
      state = DiagnosticError(e.message);
    }
  }

  Future<void> startAsGuest(String track) async {
    state = const DiagnosticLoading();
    try {
      _guestId = await _api.startGuest(track);
      _assessmentId = null;
      await _advance();
    } on ApiException catch (e) {
      state = DiagnosticError(e.message);
    }
  }

  Future<void> submitAnswer(int questionId, String answer, {int? timeSpentSec}) =>
      _answer(questionId, answer, false, timeSpentSec);

  Future<void> skip(int questionId) => _answer(questionId, null, true, null);

  Future<void> _answer(int questionId, String? answer, bool skipped, int? timeSpentSec) async {
    try {
      await _api.answer(
        assessmentId: _assessmentId, guestId: _guestId,
        questionId: questionId, answer: answer, skipped: skipped, timeSpentSec: timeSpentSec);
      await _advance();
    } on ApiException catch (e) {
      state = DiagnosticError(e.message);
    }
  }

  Future<void> _advance() async {
    final next = await _api.next(assessmentId: _assessmentId, guestId: _guestId);
    if (next != null) {
      state = DiagnosticQuestion(next);
      return;
    }
    // 종료 → complete
    final result = await _api.complete(assessmentId: _assessmentId, guestId: _guestId);
    final loggedIn = ref.read(authControllerProvider) is AuthAuthenticated;
    if (_guestId != null && !loggedIn) {
      state = const DiagnosticGateSignup(); // 결과 직전 가입 게이트
    } else {
      state = DiagnosticResultState(result);
    }
  }

  /// 가입/로그인 완료 후 호출: guest 결과를 회원에 귀속하고 결과 표시.
  Future<void> claimAfterLogin() async {
    if (_guestId == null) return;
    state = const DiagnosticLoading();
    try {
      _assessmentId = await _api.claim(_guestId!);
      final result = await _api.complete(assessmentId: _assessmentId);
      _guestId = null;
      state = DiagnosticResultState(result);
    } on ApiException catch (e) {
      state = DiagnosticError(e.message);
    }
  }
}

final diagnosticControllerProvider =
    NotifierProvider<DiagnosticController, DiagnosticState>(DiagnosticController.new);
```

> 주: `claimAfterLogin` 후 `complete` 재호출은 guest가 이미 완료 상태이므로 회원 결과 조회 대용이다. 빌드 B `claim` 응답이 결과를 직접 주면 그 값을 쓰도록 정정(계약 재검증 Task 0 반영). `AuthAuthenticated`/`authControllerProvider` 실제 타입명은 web `auth` 소스로 확인해 맞춘다.

- [ ] **Step 4: 테스트 구체화·통과 + 커밋**

Step 1 테스트를 Fake API로 완성(15문항 후 GateSignup 단언)하고:

```bash
cd ../../ && melos run test --no-select   # 또는 cd apps/web && flutter test
```
Expected: PASS.

```bash
git add apps/web/lib/src/features/diagnostic/ apps/web/test/features/diagnostic/
git commit -m "feat(diagnostic): 진단 컨트롤러(회원/비회원/가입게이트/claim)"
```

---

## Task 5: web — 진단 퀴즈 화면 + 목 픽스처 + 라우팅

**Files:**
- Create: `apps/web/lib/src/features/diagnostic/presentation/diagnostic_page.dart`
- Modify: `apps/web/lib/src/data/web_mock_fixtures.dart`
- Modify: 라우터(`/diagnostic` 경로 등록, 기존 온보딩 흐름 결선)
- Create: `apps/web/test/features/diagnostic/diagnostic_page_test.dart`

**Interfaces:**
- Consumes: `diagnosticControllerProvider`, `DiagnosticState`.
- Produces: `DiagnosticPage`(ConsumerStatefulWidget) — Question 상태에서 진행률 `index/15`·문항·옵션·"잘 모르겠어요" 렌더, 응답 시 controller 호출. GateSignup→로그인 유도(슬라이스 #1 OAuth), Result→경로(#3 자리)로 이동.

- [ ] **Step 1: 위젯 테스트 작성(실패)**

`diagnostic_page_test.dart` — `diagnosticControllerProvider`를 Question 상태로 override하고 진행률·"잘 모르겠어요" 노출, skip 탭 시 controller.skip 호출을 검증(web 기존 위젯 테스트 패턴, `theme: DpTheme.light()`).

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dp_design/dp_design.dart';
// import 경로는 devpath_web 패키지명에 맞춘다.

void main() {
  testWidgets('Question 상태에서 진행률과 "잘 모르겠어요" 노출', (tester) async {
    // diagnosticControllerProvider override → DiagnosticQuestion(NextQuestion(index:3,total:15,...))
    // MaterialApp(theme: DpTheme.light(), home: DiagnosticPage())
    // expect(find.textContaining('3'), findsWidgets); expect(find.text('잘 모르겠어요'), findsOneWidget);
  });
}
```

- [ ] **Step 2: DiagnosticPage 구현**

`diagnostic_page.dart`(onboarding_page.dart 위젯 스타일 — dp_design `DpSpacing`/`context.dpColors`, go_router):

```dart
import 'package:dp_design/dp_design.dart';
import 'package:dp_core/dp_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../application/diagnostic_controller.dart';
import '../state/diagnostic_state.dart';

class DiagnosticPage extends ConsumerWidget {
  const DiagnosticPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(diagnosticControllerProvider);
    final notifier = ref.read(diagnosticControllerProvider.notifier);

    ref.listen(diagnosticControllerProvider, (_, next) {
      if (next is DiagnosticResultState) context.go('/path');
    });

    return Scaffold(
      appBar: AppBar(title: const Text('실력 진단')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Padding(
            padding: const EdgeInsets.all(DpSpacing.xl),
            child: switch (state) {
              DiagnosticIdle() => FilledButton(
                  onPressed: () => notifier.startAsGuest('BACKEND_SPRING'),
                  child: const Text('진단 시작하기')),
              DiagnosticLoading() => const Center(child: CircularProgressIndicator()),
              DiagnosticQuestion(:final next) => _QuestionView(next: next, notifier: notifier),
              DiagnosticGateSignup() => Column(mainAxisSize: MainAxisSize.min, children: [
                  const Text('결과를 보려면 로그인하세요'),
                  const SizedBox(height: DpSpacing.lg),
                  FilledButton(
                    onPressed: () => ref.read(authControllerProvider.notifier).loginWithGitHub(),
                    child: const Text('GitHub로 로그인')),
                ]),
              DiagnosticResultState(:final result) =>
                  Text('진단 레벨: ${result.diagnosedLevel}'),
              DiagnosticError(:final message) => Text(message,
                  style: TextStyle(color: context.dpColors.danger)),
            },
          ),
        ),
      ),
    );
  }
}

class _QuestionView extends StatelessWidget {
  const _QuestionView({required this.next, required this.notifier});
  final NextQuestion next;
  final DiagnosticController notifier;

  @override
  Widget build(BuildContext context) {
    final q = next.question;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('${next.index} / ${next.total} · 진단',
            style: Theme.of(context).textTheme.labelMedium),
        const SizedBox(height: DpSpacing.md),
        Text(q.content, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: DpSpacing.lg),
        // 옵션: 단순화 — 첫 옵션 정답 제출(실제 옵션 파싱/선택 UI는 dp_design Option Card로 확장)
        FilledButton(
          onPressed: () => notifier.submitAnswer(q.id, '{"correct":0}', timeSpentSec: 5),
          child: const Text('답안 제출')),
        const SizedBox(height: DpSpacing.md),
        const Divider(),
        TextButton(
          onPressed: () => notifier.skip(q.id),
          child: const Text('잘 모르겠어요')),
      ],
    );
  }
}
```

> 주: 옵션 선택 UI(4지선다 Option Card·코드블록·난이도 별점)는 와이어프레임 O03(`19 §3.5`)·dp_design 컴포넌트로 확장한다. 본 Task는 진행률·문항·skip·제출 흐름의 실API 결선을 책임진다(슬롯형 UI 정교화는 후속 디자인 Task).

- [ ] **Step 3: 목 픽스처 추가(실계약 정합)**

`web_mock_fixtures.dart`에 진단 엔드포인트 픽스처 추가(guest start/next/answer/complete). 기존 픽스처 형식·키 규약을 그대로 따른다(`USE_MOCK=true`에서 진단 흐름 동작 보장). next는 호출 횟수와 무관히 동일 문항을 반환해도 무방(목은 흐름 시연용)하되, complete가 결과를 주도록 구성.

- [ ] **Step 4: 라우터 결선**

진단 경로(`/diagnostic` 또는 기존 `/onboarding`)에 `DiagnosticPage`를 등록하고, 가입 게이트→OAuth 로그인→`claimAfterLogin()`→결과 흐름을 라우팅과 연결(슬라이스 #1 `auth` 콜백 후 진단 복귀). 실제 라우터 파일·경로는 web `app/router` 소스로 확인해 맞춘다.

- [ ] **Step 5: 전체 analyze/test 통과 + 커밋**

```bash
cd <repo root>
melos run analyze
melos run test
```
Expected: 전 패키지 SUCCESS(web 위젯/컨트롤러 포함).

```bash
git add apps/web/lib/src/features/diagnostic/presentation/diagnostic_page.dart \
        apps/web/lib/src/data/web_mock_fixtures.dart \
        apps/web/test/features/diagnostic/diagnostic_page_test.dart
# + 라우터 변경 파일
git commit -m "feat(diagnostic): 진단 퀴즈 화면 실API + 목 픽스처 + 라우팅"
```
develop PR → CI(analyze·test) 녹색 → merge.

---

## Self-Review (작성자 점검 결과)

- **Spec coverage**: 설계서 §2 빌드D(gateway 라우트+frontend 실API), §5 엔드포인트, §6 guest→가입게이트→claim, §8 프론트(진행률·skip·결과). gateway 라우팅·공개경로, dp_core 모델·API, 진단 컨트롤러·화면 커버. Task 0(상류 계약 재검증 게이트) 명시.
- **Placeholder scan**: gateway·dp_core·컨트롤러는 완전 코드. **UI 정교화(Option Card·코드블록·별점)와 일부 테스트 본문·라우터 결선은 "후속/실소스 확인"으로 명시** — 이는 상류 계약 재검증(Task 0) 의존 + 디자인 컴포넌트 확장 항목으로, 추측 회피를 위한 의도적 위임(설계서 §8 정합). 구현자는 Task 0 결과·web 실소스(api_client·router·auth 타입)로 정정 후 채운다.
- **Type consistency**: dp_core 모델(`AssessmentQuestion`,`NextQuestion`,`AssessmentResult`)이 API 클라이언트·컨트롤러·화면에서 일관. API 메서드 시그니처(start/next/answer/complete/claim)가 컨트롤러 호출과 일치. gateway 라우트 Path·공개경로가 빌드 B 경로와 일치.
- **⚠️ 주의(상류 의존 최대)**: `ApiClient.get/post` 제네릭·204 처리, `authControllerProvider`/`AuthAuthenticated` 타입, 라우터 구조, `MockHttpAdapter` 픽스처 키 형식, claim 응답 형태는 **실소스로 확인 후 코드 정정**(추측 금지). Task 0에서 learning 계약, 각 Task에서 web 실소스 교차검증.
