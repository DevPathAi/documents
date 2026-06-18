# 슬라이스 #2 계획 문서 검토 리포트

작성일: 2026-06-18  
검토 범위: 아래 5개 Implementation Plan 및 일부 실제 소스 교차 확인  
원칙: 원본 문서와 서비스 코드는 수정하지 않고, 보완 의견만 별도 문서로 기록

## 검토 대상

- `2026-06-18-md1-slice2-shared-schema.md`
- `2026-06-18-md1-slice2-learning-engine-b1.md`
- `2026-06-18-md1-slice2-learning-events-b2.md`
- `2026-06-18-md1-slice2-platform-status-c.md`
- `2026-06-18-md1-slice2-gateway-frontend-d.md`

교차 확인한 실제 소스:

- `devpath-frontend/packages/dp_core/lib/src/api/api_client.dart`
- `devpath-frontend/packages/dp_core/lib/src/mock/mock_http_adapter.dart`
- `devpath-frontend/apps/web/lib/src/features/auth/application/auth_controller.dart`
- `devpath-frontend/apps/web/lib/src/app/router.dart`
- `devpath-gateway/src/main/java/ai/devpath/gateway/config/GatewaySecurityConfig.java`
- `devpath-shared/src/main/resources/db/migration/V202606171004__outbox.sql`

## 총평

전체 흐름은 A(shared schema/event) -> B-1(member assessment engine/API) -> B-2(event/guest/claim/seed) -> C(platform status consumer) -> D(gateway/frontend) 순서로 잘 분리되어 있습니다. 테스트 우선, shared main publish 게이트, Boot 4/Jackson 3 주의, 실소스 재검증 게이트를 명시한 점도 좋습니다.

다만 D 문서는 실제 web/gateway 소스와 맞지 않는 부분이 몇 군데 있고, B-1/B-2/C에는 구현자가 문서 그대로 옮겼을 때 상태 전이, guest claim, 재시도/멱등성에서 깨질 수 있는 지점이 있습니다. 아래 P0/P1 항목은 구현 전에 문서 보완을 권장합니다.

## 핵심 수정 필요 사항

| 우선순위 | 영역 | 요약 | 권장 조치 |
| --- | --- | --- | --- |
| P0 | D frontend + B-1/B-2 contract | guest claim 후 `complete()` 재호출 흐름이 B-1의 `ownedInProgress()`와 충돌 | `AssessmentApi.result()`를 추가하고 claim 후 `GET /{id}/result` 사용 또는 claim 응답에 result 포함 |
| P0 | D frontend router | 실제 web gate는 미인증 사용자를 `/login`으로 보내므로 guest 진단 화면 접근 불가 | `/diagnostic` 또는 `/onboarding` guest 진입을 gate 예외로 명시 |
| P1 | D frontend tests/API | `MockHttpAdapter` fixture 형식이 실제 타입과 다름 | `(status, body)` 튜플 형태로 테스트/목 픽스처 예시 수정 |
| P1 | D frontend auth | 문서의 `loginWithGitHub()`는 실제 `AuthController`에 없음 | `login()`으로 수정하고 `AuthAuthenticated` import 명시 |
| P1 | B-1/B-2 next/answer | member와 guest의 next 호출 의미가 다르고 중복 next/임의 answer 방지가 약함 | outstanding question 모델 또는 pending question 저장 방식 추가 |
| P1 | B-2 claim | Redis claim 멱등 키 저장과 DB 이행이 원자적이지 않음 | Redis lock/SETNX + 트랜잭션 후 보상, 또는 DB claim mapping 테이블 고려 |
| P1 | C platform consumer | read-save 방식은 동시 상태 변경 시 DONE을 IN_PROGRESS로 되돌릴 수 있음 | 조건부 update 쿼리 `WHERE onboarding_status='PENDING'` 사용 |

## 상세 검토 결과

### P0-1. D의 `claimAfterLogin()`이 완료된 assessment에 다시 `complete()`를 호출함

근거:

- D 문서 `claimAfterLogin()` 예시는 claim 후 `_api.complete(assessmentId: _assessmentId)`를 호출합니다.
- B-2 `ClaimService`는 claim 시 assessment를 `COMPLETED`로 만들고 `AssessmentResult`를 저장합니다.
- B-1 `AssessmentService.complete()`는 `ownedInProgress()`를 호출하므로 이미 `COMPLETED`인 assessment에서는 실패합니다.

영향:

- guest 진단 완료 -> 로그인 -> claim -> 결과 표시 흐름이 런타임에서 실패할 가능성이 큽니다.

권장 보완:

- D의 `AssessmentApi`에 `Future<AssessmentResult> result(int assessmentId)` 추가.
- `claimAfterLogin()`은 `claim()` 후 `complete()`가 아니라 `result()` 호출.
- 대안으로 B-2 claim 응답을 `{assessmentId, result}`로 확장하고 D가 그 응답을 사용.
- 테스트에 `guest complete -> login/auth state 변경 -> claim -> result 표시` 시나리오 추가.

### P0-2. 실제 web router gate가 guest 진단 진입을 막음

근거:

- D 문서는 비회원 guest 진단을 목표로 하지만, 실제 `gateRedirect()`는 `AuthAuthenticated`가 아니면 `/login`만 허용합니다.
- D Task 5는 `/diagnostic` 또는 기존 `/onboarding`에 페이지 등록만 언급하고, gate 예외 처리는 명시하지 않습니다.

영향:

- `/diagnostic` 또는 `/onboarding`에 guest 진단 페이지를 추가해도 미인증 사용자는 즉시 `/login`으로 redirect됩니다.

권장 보완:

- `gateRedirect()`에 guest 진단 허용 경로를 명시합니다. 예: `location == '/diagnostic'`는 미인증 허용.
- 기존 `/onboarding`을 guest 진단으로 재사용할 경우, 인증 사용자 온보딩 게이트와 비회원 guest flow를 분리하는 규칙을 문서화합니다.
- OAuth callback 이후 `claimAfterLogin()`으로 복귀할 route state/query/local state 전략을 명시합니다.

### P1-1. D의 `MockHttpAdapter` 테스트 예시가 실제 fixture 타입과 불일치

근거:

- 실제 `MockHttpAdapter`는 `Map<String, MockFixture>`를 받고, `MockFixture`는 `(int status, Object body)` record입니다.
- D Task 3 테스트 예시는 `Map<String, dynamic>`에 raw JSON map을 넣습니다.

영향:

- 문서 예시 그대로 작성하면 Dart 타입 에러가 나거나, 목 응답이 동작하지 않습니다.

권장 보완:

```dart
ApiClient mockClient(Map<String, MockFixture> fixtures) {
  final c = ApiClient.create(const ApiConfig(baseUrl: 'http://t', useMock: true));
  c.dio.httpClientAdapter = MockHttpAdapter(fixtures);
  return c;
}

final api = AssessmentApi(mockClient({
  'POST /onboarding/assessments/guest': (200, {'guestAssessmentId': 'g-123'}),
}));
```

### P1-2. D의 auth 호출명이 실제 소스와 불일치

근거:

- 실제 `AuthController`에는 `login()`이 있고, 문서 D의 `DiagnosticPage` 예시는 `loginWithGitHub()`를 호출합니다.
- `DiagnosticController` 예시는 `AuthAuthenticated` 타입을 사용하지만 `auth_controller.dart`만 import합니다. Dart import는 transitive export가 아니므로 `auth_state.dart` import가 필요합니다.

영향:

- 프론트 구현 단계에서 컴파일 실패 가능성이 높습니다.

권장 보완:

- `ref.read(authControllerProvider.notifier).login()`으로 수정.
- `import '../../auth/state/auth_state.dart';` 또는 실제 상대 경로 import를 문서에 추가.

### P1-3. next/answer의 상태 모델이 member와 guest에서 일관되지 않음

근거:

- B-1 member flow는 `next()` 호출 시 `AssessmentItem`을 즉시 생성합니다.
- B-2 guest flow는 `next()`에서 Redis session을 변경하지 않고, `answer()`에서 `Presented`를 추가합니다.
- guest `answer()`는 해당 question이 실제로 직전에 출제되었는지 확인하지 않고 `questions.findById(req.questionId())`를 기준으로 채점합니다.

영향:

- member는 사용자가 `GET /next`를 반복 호출하면 응답하지 않은 문항이 누적될 수 있습니다.
- guest는 클라이언트가 임의 questionId를 제출하거나 같은 questionId를 반복 제출해도 흐름이 진행될 수 있습니다.
- 두 flow의 "presented count" 의미가 달라 claim/분석 결과가 달라질 수 있습니다.

권장 보완:

- 공통 규칙을 문서에 추가합니다: "unanswered outstanding question이 있으면 `next()`는 새 문항을 만들지 않고 기존 문항을 반환".
- guest `GuestSession`에 `pendingQuestionId` 또는 `Presented(answered=false)` 모델을 추가합니다.
- `answer()`는 pending/outstanding question과 일치할 때만 수락합니다.
- 반복 `next`, 임의 `answer`, 중복 `answer` 회귀 테스트를 B-1/B-2에 추가합니다.

### P1-4. B-2 claim 멱등성이 Redis 저장 시점에 의존해 원자성이 약함

근거:

- B-2 `ClaimService`는 먼저 Redis claim mapping을 조회하고, DB assessment/result/outbox 저장 후 마지막에 `assessment:claim:{guestId}`를 저장하고 guest session을 삭제합니다.

영향:

- DB 저장 성공 후 Redis 저장 전에 장애가 나면 재요청 시 중복 assessment/result/event가 생성될 수 있습니다.
- 동시 claim 요청이 들어오면 두 요청이 모두 기존 mapping 없음으로 판단할 수 있습니다.

권장 보완:

- 최소 보완: `SETNX assessment:claim-lock:{guestId}` + 짧은 TTL로 동시 진입 방지.
- 더 견고한 보완: `guest_claims(guest_id unique, assessment_id)` 같은 DB 멱등 테이블 추가.
- claim 테스트에 동시 요청 또는 동일 guestId 빠른 재요청 시 outbox 중복 없음 검증 추가.

### P1-5. C platform 상태 전이는 조건부 update가 더 안전함

근거:

- C 문서 구현은 `users.findById()`, 상태 확인, `setOnboardingStatus("IN_PROGRESS")`, `save()` 순서입니다.

영향:

- 다른 트랜잭션이 같은 사용자를 `DONE`으로 바꾸는 사이에 consumer가 오래된 PENDING 엔티티를 저장하면 상태가 IN_PROGRESS로 되돌아갈 수 있습니다.

권장 보완:

- `UserRepository`에 조건부 update 추가:

```java
@Modifying
@Query("update User u set u.onboardingStatus = 'IN_PROGRESS' " +
       "where u.id = :userId and u.onboardingStatus = 'PENDING'")
int markAssessmentStartedIfPending(@Param("userId") Long userId);
```

- consumer는 위 메서드만 호출하고, 결과 row count로 로그를 남깁니다.
- DONE/IN_PROGRESS 무변동 테스트는 repository update 기반으로 검증합니다.

### P1-6. D의 UI는 실API 전환 목표에 비해 답안 선택이 지나치게 하드코딩됨

근거:

- D `DiagnosticPage` 예시는 options를 파싱하지 않고 `{"correct":0}`을 고정 제출합니다.

영향:

- "목 -> 실API 전환" 작업 결과물이 실제 진단 UX로 사용되기 어렵고, 모든 문항에 같은 답을 제출합니다.

권장 보완:

- 최소 구현 범위를 "문항 options JSON 파싱, 선택 상태, submit 활성화, skip"까지 올립니다.
- options가 없거나 code/short answer 타입인 경우의 UI fallback을 명시합니다.
- widget test에 옵션 선택 -> 선택한 index가 answer JSON으로 전송되는지 검증 추가.

## 문서별 보완 제안

### A. shared schema/event

좋은 점:

- migration 순서와 FK 의존성이 명확합니다.
- shared main publish 필요성을 명시해 다운스트림 의존성 문제를 줄였습니다.
- `AssessmentCompletedEvent.EVENT_TYPE = learning.assessment.completed`가 B/C/D와 일관됩니다.

보완 제안:

- migration test가 테이블 존재만 검증합니다. enum CHECK, difficulty 범위, FK, trigger, 1:1 result PK, unique order를 검증하는 테스트를 추가하세요.
- `assessment_results.confidence_weight`에 `0.0 <= confidence_weight <= 1.0` CHECK를 추가하는 것이 좋습니다.
- `assessment_items.order_num > 0`, `time_spent_sec >= 0` CHECK를 추가하면 데이터 품질이 좋아집니다.
- `AssessmentCompletedEventTest`에 JsonMapper 직렬화/역직렬화 계약 테스트를 추가하세요. 필드명과 nullable field 호환성은 eventType 테스트만으로는 부족합니다.

### B-1. learning engine/member API

좋은 점:

- 엔진을 순수 도메인 객체로 분리한 점이 좋습니다.
- Boot 4 test autoconfigure 모듈, test profile Flyway, JWT 자체 검증을 명시한 점이 구현 안정성에 도움이 됩니다.

보완 제안:

- `next()` 반복 호출 시 unanswered item이 계속 누적되지 않도록 outstanding question 규칙을 추가하세요.
- `answer()`는 "가장 최근 미응답 문항" 또는 "현재 outstanding 문항"만 수락하도록 제한하세요.
- `complete()`는 15문항 미만 또는 미응답 문항 존재 시 허용할지 정책이 필요합니다. 현재 문서상으로는 조기 complete 가능성이 있습니다.
- JSON answer 비교가 공백 제거 문자열 비교입니다. B-2에서 시드가 들어간 뒤 `JsonMapper`로 구조적 비교하는 보완을 권장합니다.
- 테스트 seed 데이터는 테스트 간 중복/잔존 데이터 영향을 줄이기 위해 고유 track 또는 cleanup 전략을 명시하세요.

### B-2. learning events/guest/claim

좋은 점:

- shared 기존 `outbox` 테이블을 재사용하는 방향은 실제 migration과 맞습니다.
- guest TTL과 answer 시 TTL 갱신을 명시한 점이 좋습니다.
- member complete에서 concept score 집계를 B-1 위에 결선하는 방향이 자연스럽습니다.

보완 제안:

- claim 멱등성을 Redis mapping만으로 끝내지 말고 동시성/장애 케이스를 보완하세요.
- guest session에 answer payload와 timeSpentSec를 보관하지 않아 claim 시 DB `assessment_items.answer/time_spent_sec`가 유실됩니다. Redis session 모델에 포함하는 편이 좋습니다.
- guest claim 후 conceptScores가 `Map.of()`로 비어 있습니다. 슬라이스 #3에서 경로 생성 입력으로 concept score가 필요하면 B-2에서 guest concept 집계까지 포함해야 합니다.
- OutboxRelay는 platform의 failure test도 함께 복사하세요. 성공 테스트만 있으면 send 실패 시 published_at null 유지 계약이 약합니다.
- `QuestionBankSeeder`가 BACKEND_SPRING만 시드합니다. API가 모든 track을 받는다면 다른 track 요청 시 문항 없음 정책을 명시하거나 최소 fixture를 확장하세요.

### C. platform status consumer

좋은 점:

- event topic/groupId와 상태 전이 범위가 명확합니다.
- DONE은 슬라이스 #3 범위로 남긴 점이 좋습니다.

보완 제안:

- 상태 전이는 read-save 대신 조건부 update로 바꾸는 것이 안전합니다.
- DONE 무변동 테스트의 `Thread.sleep(2000)`은 부정 검증이라 불안정합니다. 직접 consumer 메서드를 호출하는 단위 테스트와 EmbeddedKafka E2E를 분리하거나, 짧은 관찰 구간 동안 상태가 변하지 않음을 Awaitility로 표현하세요.
- 역직렬화 실패 payload 처리 전략이 없습니다. 계속 retry되는 poison message를 막기 위해 error handler/DLQ/로그 후 skip 중 하나를 문서화하세요.

### D. gateway/frontend

좋은 점:

- Task 0으로 상류 계약 재검증 게이트를 둔 점은 매우 좋습니다.
- gateway route와 guest permitAll 범위가 명확합니다.
- dp_core model/API/controller/page로 층을 나눈 점이 좋습니다.

보완 제안:

- 실제 web router gate를 반영해 guest diagnostic route 예외를 명시하세요.
- `MockHttpAdapter` fixture tuple 형식, `AuthController.login()` 호출명, `AuthAuthenticated` import를 실제 소스 기준으로 수정하세요.
- claim 후 결과 조회는 `complete()`가 아니라 `result()`가 되어야 합니다.
- `AssessmentApi._base()`는 `assessmentId`와 `guestId` 중 정확히 하나만 허용하도록 검증하세요.
- `AssessmentResult` 모델은 B-1/B-2 응답의 `conceptScores`, `strengthConcepts`, `weaknessConcepts`를 받을지 의도적으로 제외할지 결정해야 합니다.
- 라우터 결선과 OAuth callback 후 `claimAfterLogin()` 호출 시점을 구체화하세요. 현재는 "실소스 확인"만 있어 구현자마다 달라질 수 있습니다.

## 권장 보완 순서

1. D의 guest claim/result contract부터 정리합니다. B-2 claim 응답을 확장할지, D에 `GET /result`를 추가할지 먼저 결정해야 합니다.
2. web router gate에서 guest 진단 경로 허용 정책을 확정합니다.
3. B-1/B-2의 next/answer 상태 모델을 outstanding question 기준으로 통일합니다.
4. B-2 claim 멱등성 원자화 방식을 정합니다.
5. C 상태 전이를 조건부 update로 바꿉니다.
6. A schema/event 계약 테스트를 강화합니다.
7. D frontend 테스트 예시와 실제 소스명/fixture 타입을 맞춥니다.

## 최종 체크리스트

- [ ] guest complete -> login -> claim -> result 표시가 한 번의 E2E 테스트로 검증된다.
- [ ] 미인증 사용자가 guest 진단 페이지에 접근할 수 있다.
- [ ] claim 재시도/동시 요청에서 assessment/result/outbox 중복이 없다.
- [ ] member/guest 모두 반복 `next()`와 임의 `answer()`가 안전하다.
- [ ] platform consumer가 DONE을 IN_PROGRESS로 되돌리지 않는다.
- [ ] migration test가 주요 CHECK/FK/unique/trigger 계약을 검증한다.
- [ ] frontend 목 테스트가 실제 `MockHttpAdapter` fixture 타입과 일치한다.
- [ ] 문서 D의 auth 메서드명과 import가 실제 web 소스와 일치한다.

