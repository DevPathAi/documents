# Tier-1 리펙토링 검토 보고서 (슬라이스 #1~6, 7개 레포)

> 2026-06-23. Tier-2 진입 전 코드 유지보수성 검토(버그가 아닌 **리펙토링 기회**). 7개 레포를 3개 검토자(R1 ai/sandbox-svc, R2 learning/platform-svc, R3 shared/gateway/frontend)가 read-only 분석. 본 문서는 종합·우선순위판이며, 검토는 **권고**이고 실제 리펙토링은 별도 작업이다.

## 0. 종합 건강도

전반적으로 **설계 의식이 높다**: 짧은 트랜잭션 분리(persistence service), 인젝션 방어 프롬프트, Outbox 패턴 정석 구현, Riverpod sealed-state, 비동기 경쟁조건 방어, 보안 격리(네트워크 차단·비특권·리소스 제한). 테스트 커버리지도 핵심 시나리오에 충실. **결함이 아니라 "코드베이스가 커지기 전에 정리할 중복·매직값"이 주된 부채**다.

| 레포 | 건강도 | 핵심 부채 |
|---|---|---|
| ai-svc | 양호 | OllamaClient↔OllamaAiReviewClient 중복(레코드·헬퍼·RestClient), Controller의 Repository 직접접근 |
| sandbox-svc | 양호 | `run()` 80행 단일메서드, DockerClient 이중생성·이중ping, dead `containerId` |
| learning-svc | 보통-양호 | 상태 String 산재, `complete()` 54행 단일책임 위반, Assessment/Guest 병렬진화 |
| platform-svc | 양호 | Kafka 소비자 구조중복 + 오류처리 불일치, Outbox 쓰기 중복 |
| shared | 양호 | FlywayMigrationTest 23× 반복, track/level 열거값이 SQL 리터럴에만 |
| gateway | 양호 | 테스트 헬퍼(jwt/assert) 복붙, application-test.yml 라우트 중복 |
| frontend | 양호 | admin AuthInterceptor 미연결, deprecated 메서드 잔존, String status 분기 |

## 1. 횡단 테마 (최우선 — 여러 레포에 걸침)

### T1. ⭐ Outbox 3클래스가 3개 레포에 바이트 수준 복제 (최고 위험)
`OutboxRelay`·`OutboxEntry`·`OutboxRelayScheduler`가 **learning-svc·platform-svc·sandbox-svc**에 거의 동일 복사본으로 존재. `relayOnce()`의 `findTop100`·`kafka.send().get(5s)`·실패 시 `break` 전략·컬럼 집합까지 동일. **버그 수정이 한 레포에만 반영될 위험이 가장 크다.** (L-H2/P-H1 + sandbox OutboxRelay)
- **권고**: 중기적으로 공통 라이브러리(`devpath-outbox-core` 또는 devpath-shared 모듈)로 추출. 단기적으로 각 파일에 `// SHARED: keep in sync` 주석 + 변경 연동 정책 문서화. **단, OutboxRelay.relayOnce()는 실패 예외를 무음 삼킴(`catch{break}`) → 추출 시 `log.warn` 동반(sandbox R1-Med, 운영 추적성).**

### T2. 도메인 열거값이 String으로 SQL·Java·Dart 3계층에 분산
- 상태: `PENDING/DONE/FAILED`(ai-svc), `IN_PROGRESS/COMPLETED/ACTIVE/ARCHIVED`(learning-svc), `UP/DOWN`(피드백) — Java 서비스·레포·JPQL·native SQL·Dart 모델에 매직 문자열.
- 트랙: `BACKEND_SPRING` 등 5개 마이그레이션 SQL + 이벤트 String 필드 + Dart 모델에 각자 하드코딩.
- 언어: `JAVA/NODE/PYTHON` — sandbox_sessions CHECK + RunController 정규식 + Runtime switch + 이벤트 String 필드.
- **위험**: 오타·신규 값 추가를 컴파일러가 못 잡고, 3계층이 drift. (L-H4/R1 상태/R3 track·language)
- **권고**: 계층별 enum 점진 도입 — Java(`@Enumerated(STRING)` 또는 Converter), shared 이벤트 필드 타입 격상(`Track`/`SandboxLanguage`/status), Dart 모델 enum. SQL CHECK는 리터럴 유지. **Tier-2 시작 전 enum 골격만 잡고 점진 이전 권장**(신규 코드부터 enum 사용).

### T3. `Long` vs `long` 비교 패턴 (잠재 결함 씨앗)
`session.userId() != userId`(ai-svc), `a.getUserId() != userId`(learning-svc), `s.pendingQuestionId() != req.questionId()`(GuestAssessmentService) — 현재는 언박싱으로 정상이나 시그니처가 `Long`으로 바뀌면 **참조 비교로 돌변**. 동일 기능을 AssessmentService는 `.equals()`, GuestAssessmentService는 `!=`로 **불일치**. (R1-Med/L-M4/L-M5)
- **권고**: `Objects.equals(a, b)`로 통일. (이건 리펙토링 겸 잠재버그 예방 — 2절 참조)

### T4. JSON 직렬화/역직렬화 헬퍼 중복
`try{jsonMapper.writeValueAsString}catch` 패턴이 learning-svc 4곳·ai-svc 등에 반복, 예외 타입도 클래스마다 다름(PathContractException vs IllegalStateException). (L-M7)
- **권고**: 레포별 `JsonSupport.toJson/fromJsonList` 유틸 추출.

### T5. 테스트 보일러플레이트·설정 중복
- gateway: `jwt()` 헬퍼 4개 클래스 복붙 + `assertGatewayMatchedRoute` 3개 복붙 → `GatewayTestSupport` 추출. (R3-H3/H4)
- gateway: `application-test.yml`이 라우트 블록 전체를 main yml에서 복사(동기화 부담) → 테스트 yml은 delta만. *(슬라이스 #6 빌드 D에서 동일 함정 경험)*
- shared: `FlywayMigrationTest`가 migrate()를 23개 메서드에 반복 → `@BeforeAll` 1회. (R3-H1)
- SecurityConfig: ai-svc↔sandbox-svc 거의 동일(중기 shared 스타터 후보, 현재 복제는 MSA 경계상 허용 — 명시 권고).

## 2. 리펙토링 너머 — 잠재 결함 플래그 (우선 처리 권장)

검토 중 **순수 리펙토링을 넘어 동작 위험**인 항목:

| 위험 | 위치 | 내용 | 권고 |
|---|---|---|---|
| 🔴 admin 인증 누락 | frontend `apps/admin/.../api_providers.dart:12-21` | admin `ApiClient`에 **AuthInterceptor 미연결**(web에는 있음). 실서버 모드에서 admin API 요청에 Authorization 헤더 미부착 → 실연동 시 401. mock이라 미발현. | web 패턴대로 AuthInterceptor 삽입(refresh 콜백만 tokenStore 기반) |
| 🟠 poison 무한재시도 | platform-svc `WelcomeNotificationConsumer.java:31-33` | 역직렬화 실패 시 **예외 throw**(다른 두 소비자는 log.warn+return skip). poison 메시지가 Kafka 무한 재시도 루프 유발 가능. | skip 전략으로 통일 또는 명시적 @RetryableTopic/DLT |
| 🟠 Long != long 불일치 | learning-svc `GuestAssessmentService.java:53` 등 | 위 T3. 현재 동작하나 시그니처 변경 시 즉시 버그. | `Objects.equals` |
| 🟡 outbox 실패 무음 | sandbox-svc `OutboxRelay.java:22-30` (3레포 공통) | 전송 실패를 조용히 삼켜 운영 추적 불가. | `log.warn` 추가 |

## 3. 레포별 High 항목 (요약)

- **ai-svc**: RestClient 생성패턴 3중복제 / OllamaChatResponse·OllamaMessage 레코드 중복 / `OllamaClient.validate()` 4단 중첩 / `ReviewController`가 Repository 직접접근(persistence service 우회).
- **sandbox-svc**: `DockerRunnerBackend.run()` 80행 단일메서드(start/await/cleanup 분리) / DockerClient 이중생성·이중ping(요청당 2회) / `createRunning()` ALLOCATING→RUNNING 동일tx 이중저장.
- **learning-svc**: `normalize()` 중복정의 / Outbox 복제(T1) / `complete()` 54행 5책임 / 상태 String 산재(T2).
- **platform-svc**: Outbox 복제(T1) / OutboxWriter 패턴 중복 / 두 Kafka 소비자 구조중복(제네릭 `KafkaEventConsumer<T>` 추출 후보).
- **shared**: FlywayMigrationTest 23×(T5) / track 열거값 SQL 리터럴(T2).
- **gateway**: 테스트 헬퍼 복붙(T5) / application-test.yml 라우트 중복(T5).
- **frontend**: admin AuthInterceptor 미연결(2절) / `ReviewController.request()` deprecated·unused 잔존(삭제) / String status 분기(enum, T2).

## 4. Dead code (즉시 제거 가능)

- sandbox-svc `SandboxSession.containerId` — 항상 null(아무도 set 안 함). 컬럼·필드·getter/setter 제거 또는 계획 TODO.
- learning-svc `Assessment.bloomDistribution` — grep 0건, 미사용 JSON 필드. 마이그레이션으로 컬럼 제거.
- frontend `ReviewController.request()` — deprecated+unused 메서드.

## 5. 권고 (우선순위)

1. **잠재 결함 플래그(2절) 우선 처리** — admin AuthInterceptor·WelcomeConsumer poison·Long비교·outbox 무음. 작은 변경이고 동작 위험. (별도 fix 사이클 또는 Tier-2 착수 시 동반)
2. **T1 Outbox**: 즉시 공통화는 부담 → 단기 `// SHARED: keep in sync` 주석 + 정책 문서화, 중기 `devpath-outbox-core` 추출.
3. **T2 enum 골격**: Tier-2 시작 전 status/track/language enum 골격을 잡고 **신규 코드부터 적용**, 기존은 점진 이전(빅뱅 금지).
4. **Dead code(4절) 즉시 제거** — 저비용 고명료.
5. 나머지(메서드 분해·헬퍼 추출·테스트 보일러플레이트)는 해당 파일을 손댈 때 기회적으로(boy-scout rule). 전면 리펙토링 사이클은 Tier-2 진척에 맞춰 선택.

> 전체 원시 검토: `.refactor-r1.md`(ai/sandbox-svc) · `.refactor-r2.md`(learning/platform-svc) · `.refactor-r3.md`(shared/gateway/frontend) — 워크스페이스 루트, 미커밋(참고용).
