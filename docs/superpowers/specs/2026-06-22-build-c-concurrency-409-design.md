# 설계서 — 학습경로 동시 생성 충돌 409 처리 (빌드 C 잔여, 2026-06-22)

> **상태**: 신규. 슬라이스 #3(학습경로) 빌드 C에서 "동시성 409"가 의도적으로 미포함된 잔여 항목을 정식 설계로 승격.
> **위치**: MD1 슬라이스 #3 빌드 C 후속. 대상 레포 = `devpath-learning-svc` 단독. shared 스키마 변경 없음.
> **원칙**: DB partial UNIQUE를 동시성 정합의 진실의 원천으로 삼는다(R-8). 추가 락/직렬화 도입 없이 제약 위반을 의미 있는 409로 변환한다. 모든 변경은 실패 테스트 우선.

---

## 0. 배경

슬라이스 #3 빌드 C(`devpath-learning-svc` PR #7, 커버리지 보강 PR #8)에서 학습경로 생성 엔진을 구현하며, 사용자별 ACTIVE 경로 유일성은 shared `V202606181006`의 partial UNIQUE 제약(`learning_paths(user_id) WHERE status='ACTIVE'`)으로 보장하도록 설계했다(R-8: AI 호출은 트랜잭션 밖, persist만 짧은 트랜잭션).

당시 정상 재생성(순차 archive→신규 생성)은 `regenerateArchivesPreviousActiveAndReturnsNewPathId` 테스트로 커버했으나, **동일 사용자의 동시 생성 요청이 제약을 위반할 때의 동작은 테스트도 변환 로직도 없는 상태**로 남겼다(메모리 SSoT: "동시성 409만 의도적 미포함").

실측 결과 이 갭은 단순 테스트 누락이 아니라 **런타임 동작 결함**이다: 현재 `GlobalExceptionHandler`에 `DataIntegrityViolationException` 핸들러가 없어, 동시 충돌 시 `regenerate`(동기)는 **HTTP 500**, `generate`(SSE)는 의미 없는 generic error 이벤트로 떨어진다. 클라이언트는 "충돌(이미 생성됨/생성 중)"과 "서버 오류"를 구분할 수 없다.

## 1. 목적과 완료 기준

### 1.1 목적
동일 사용자의 동시 학습경로 생성으로 partial UNIQUE 제약이 위반될 때, 이를 **명시적 409 CONFLICT**로 변환하고, 최종 DB 상태가 항상 "ACTIVE 경로 정확히 1개"로 수렴함을 자동화 테스트로 실증한다.

### 1.2 완료 기준(DoD)
- 동일 `userId`로 2개의 경로 생성이 동시에 진입했을 때, **하나는 성공, 다른 하나는 409**로 끝난다.
- 충돌 후 DB 상태: 해당 user의 `learning_paths` 중 `status='ACTIVE'`가 **정확히 1행**.
- `regenerate`(동기) 충돌 시 응답 = **HTTP 409**, body에 `errorCode: "PATH_GENERATION_CONFLICT"`.
- `generate`(SSE) 충돌 시 = **error 스테이지 이벤트에 `errorCode: "PATH_GENERATION_CONFLICT"` 포함**(현재는 메시지 문자열만).
- 위 시나리오를 검증하는 동시성 통합 테스트가 **fresh DB(`devpath_citest`) 또는 CI(postgres+redis 서비스)에서 녹색**.
- 기존 `LearningPathEngineTest` 전 케이스 회귀 통과.

### 1.3 범위 외
- 분산 환경(다중 인스턴스) 직렬화·분산락. 본 설계는 단일 DB 제약에 의존하며, 다중 인스턴스에서도 DB partial UNIQUE는 유효하므로 정합성은 보장된다(락 없이).
- 낙관적/비관적 락, advisory lock 도입(사용자 결정으로 미채택).
- 사용자 경험상의 "이미 생성 중" 진행 표시·폴링 UX(프론트 후속).
- 생성 멱등화(동일 요청 재시도 시 기존 경로 반환). 본 설계는 충돌을 성공으로 위장하지 않고 409로 노출한다.

## 2. 현재 상태 (실측)

### 2.1 생성·영속 흐름
- `LearningPathGenerationService.generate(userId, goal, progress)` — `path/LearningPathGenerationService.java:24`
  - `diagnoses.findLatestCompleted(userId)` → 없으면 `NoCompletedAssessmentException`.
  - `aiClient.generate(...)` + `aiClient.embed(...)` (트랜잭션 밖).
  - 마지막에 `persistence.persist(userId, ...)` 호출.
- `LearningPathPersistenceService.persist(long userId, GeneratedLearningPath generated)` — `path/LearningPathPersistenceService.java:28`
  - `@Transactional`.
  - `paths.archiveActiveByUserId(userId)` → 신규 `LearningPath`(status=`ACTIVE`) 구성 → **`paths.save(path)`** → `publishGenerated(saved)`(outbox INSERT).
- `LearningPathRepository.archiveActiveByUserId` — `path/LearningPathRepository.java:11`
  - `@Modifying @Query("update LearningPath p set p.status = 'ARCHIVED' where p.userId = :userId and p.status = 'ACTIVE'")`.

### 2.2 컨트롤러 2경로
- `LearningPathController.generate` — `path/LearningPathController.java:28`
  - `produces = TEXT_EVENT_STREAM_VALUE`, `CompletableFuture.runAsync`로 비동기 실행.
  - 예외 발생 시 `send(emitter, PathProgressEvent.error(e.getMessage()))` 후 `emitter.complete()` → **HTTP는 항상 200, error는 SSE 이벤트로만 전달**.
- `LearningPathController.regenerate` — `path/LearningPathController.java:50`
  - 동기 `ResponseEntity<Map<String,Long>>`. `generation.generate(...)` 직접 호출 → 예외는 `GlobalExceptionHandler`로.

### 2.3 예외 → HTTP 매핑 현황
`config/GlobalExceptionHandler.java`:
- `IllegalStateException` → 409 CONFLICT (`:25`)
- `NoCompletedAssessmentException` → 409 (`errorCode: NO_COMPLETED_ASSESSMENT`, `:30`)
- `PathContractException` → 502, `AiServiceUnavailableException` → 503, `AccessDeniedException` → 403 등.
- **`DataIntegrityViolationException` 핸들러 없음** → 동시 충돌은 매핑되지 않아 500으로 떨어짐.

### 2.4 DB 제약
- shared `V202606181006`: `learning_paths(user_id)` partial UNIQUE `WHERE status='ACTIVE'`(메모리 SSoT). learning-svc는 `spring.flyway.enabled: false`(application.yml:26), 마이그레이션은 shared 중앙 관리, 서비스는 `ddl-auto: validate`.

### 2.5 테스트 인프라
- `path/LearningPathEngineTest.java`: `@SpringBootTest @AutoConfigureMockMvc @ActiveProfiles("test")`. `JdbcTemplate` seed 헬퍼(`seedUser`/`seedAssessment`/`seedContent`), `@MockitoBean AiPathClient`, `jwt().jwt(j -> j.subject(...))`로 인증.
  - 기존 케이스: 최신완료진단 join, 벡터매칭, generate SSE 영속, 무진단 409, **순차 regenerate archive**, 매칭 miss null, 비소유자 403, AI 503, task<3 error.
  - `uniqueId()` = `System.nanoTime() % 1e9`로 테스트 간 user 격리.
- CI: postgres(pgvector/pgvector:pg17) + redis 서비스. 로컬 인프라가 빈 DB CI 실패를 가린 전례 → **fresh DB 또는 CI로 검증**(슬라이스 #2/#3 교훈).

## 3. 설계 결정

### D-1. 예외 → 409 변환 (채택)
DB partial UNIQUE를 진실의 원천으로 두고, 위반 시 발생하는 `DataIntegrityViolationException`을 도메인 예외 `ActivePathConflictException`으로 변환, `GlobalExceptionHandler`에서 409로 매핑한다. 락/직렬화를 추가하지 않으므로 다중 인스턴스에서도 동일하게 동작한다.

### D-2. `save` → `saveAndFlush` (핵심)
현재 `paths.save(path)`는 트랜잭션 **커밋 시점(즉 `persist()` 메서드 반환 이후)** 에 flush된다. 그 시점에 제약 위반이 터지면 `persist()`의 try/catch로 잡을 수 없다(예외가 트랜잭션 인프라 레이어에서 발생). 따라서 **`saveAndFlush(path)`로 flush를 트랜잭션·메서드 경계 안으로 끌어와** `DataIntegrityViolationException`을 포착하고 `ActivePathConflictException`으로 재던진다.

> 트랜잭션이 롤백 표시(rollback-only)된 뒤에도 메서드 밖에서 커밋이 시도되면 `UnexpectedRollbackException`이 날 수 있다. 변환 예외는 `RuntimeException`이므로 트랜잭션은 정상 롤백되고, flush 시점에 잡으므로 추가 DB 작업은 없다. 이 거동은 동시성 IT로 실증한다(추측 금지).

### D-3. errorCode 표준화 (SSE는 메시지 채널 재사용 — 실측 확정)
- `errorCode: "PATH_GENERATION_CONFLICT"`. `NO_COMPLETED_ASSESSMENT` 패턴(GlobalExceptionHandler 기존)과 일관.
- **`PathProgressEvent`/`LearningPathController` 수정 불필요**(실측 확정): `PathProgressEvent`는 `record (String stage, double progress, String message, Long pathId)`이고 `error(message)`는 message를 그대로 싣는다. `LearningPathController.generate`는 예외 시 `PathProgressEvent.error(e.getMessage())`로 SSE에 전달하며, `NoCompletedAssessmentException`도 메시지(`"NO_COMPLETED_ASSESSMENT: userId=..."`)로 코드를 노출한다(기존 `generateWithoutCompletedAssessmentReturns409BeforeAiCall`가 이 문자열을 검사). 따라서 `ActivePathConflictException` 메시지에 `PATH_GENERATION_CONFLICT`를 담으면 동일 경로로 노출되어 추가 수정이 없다.

### D-4. 충돌 판정 지점
충돌은 `persist()`의 `saveAndFlush` 또는 그 직전 동작에서 발생한다. `archiveActiveByUserId`는 bulk update라 충돌 원인이 아니며(자기 자신의 기존 ACTIVE만 ARCHIVED 처리), 충돌은 **두 트랜잭션이 각자 신규 ACTIVE를 INSERT**하면서 partial UNIQUE를 위반할 때 발생한다. 따라서 변환은 `saveAndFlush` 호출을 감싼 좁은 try/catch로 한정한다.

## 4. 변경 대상 (파일)

- Create: `src/main/java/ai/devpath/learning/path/ActivePathConflictException.java` — `RuntimeException`.
- Modify: `src/main/java/ai/devpath/learning/path/LearningPathPersistenceService.java` — `save`→`saveAndFlush`, `DataIntegrityViolationException` catch→`ActivePathConflictException`.
- Modify: `src/main/java/ai/devpath/learning/config/GlobalExceptionHandler.java` — `ActivePathConflictException`→409 + `errorCode: PATH_GENERATION_CONFLICT`.
- **수정 불필요(실측 확정)**: `PathProgressEvent.java`, `LearningPathController.java`. `ActivePathConflictException` 메시지에 코드 문자열을 담아 기존 `error(message)` 채널로 SSE 노출(D-3).
- Create(test): `LearningPathPersistenceServiceTest`(변환 단위) · `LearningPathConflictMappingTest`(409 매핑+SSE errorCode, 컨트롤러 MockMvc) · `LearningPathConcurrencyIT`(동시 생성 ACTIVE=1 불변). 상세는 구현 플랜 참조.

## 5. 테스트 설계

### 5.1 동시성 통합 테스트 (핵심)
- 클래스는 **`@Transactional`을 붙이지 않는다**(테스트 트랜잭션 롤백이 두 스레드의 독립 트랜잭션을 가린다). 정리(cleanup)는 `@AfterEach`에서 해당 user 행 수동 삭제 또는 `uniqueId()`로 격리.
- 준비: `seedUser` + `seedAssessment(COMPLETED)` + 매칭용 `seedContent` 3건. `@MockitoBean AiPathClient`로 generate/embed 고정 응답.
- 실행: `ExecutorService`(2 스레드) + `CountDownLatch(1)`로 동시 시작 → 같은 userId로 `regenerate`(동기 경로가 예외를 직접 노출하므로 검증 용이) 또는 서비스 `generate`를 동시 호출.
- 단언:
  - 두 결과 중 **정확히 1개 성공, 1개 `ActivePathConflictException`/409**.
  - `select count(*) from learning_paths where user_id=? and status='ACTIVE'` == **1**.
  - (선택) ARCHIVED 개수로 archive 거동 확인.
- 비결정성 대비: 충돌이 매번 재현되도록 동시 시작 배리어를 명확히 두고, 충돌이 한 번도 안 나면 테스트 실패로 간주(루프 N회 또는 배리어 강화).

### 5.2 단위/슬라이스 테스트
- `DataIntegrityViolationException`을 던지는 상황을 모사해 `persist()`가 `ActivePathConflictException`으로 변환하는지(또는 GlobalExceptionHandler가 409+errorCode 반환하는지).
- SSE error 이벤트에 `PATH_GENERATION_CONFLICT`가 포함되는지(MockMvc async).

## 6. 리스크와 대응

| 리스크 | 대응 |
|---|---|
| flush 타이밍·롤백 거동 추측 | `saveAndFlush` 거동을 IT로 실증(D-2). 추측으로 구현하지 않음. |
| 동시성 테스트 flaky | 동시 시작 배리어(`CountDownLatch`) + 충돌 미발생 시 실패 처리. fresh DB로 격리. |
| 로컬 DB가 CI 실패를 가림 | fresh DB(`devpath_citest`) 또는 CI(postgres+redis)로 최종 검증(슬라이스 교훈). |
| SSE errorCode 노출 방식 회귀 | 기존 SSE 문자열 검사 패턴(`NO_COMPLETED_ASSESSMENT`)과 동일 방식 채택. |

## 7. 참고
- study-documents: `Sample Codes/🐤 Spring_Boot_4_*`의 분산락·SSE 샘플(분산락은 본 설계 미채택, SSE 패턴 참조). CLAUDE.md "study-documents 연계" 절.
- 슬라이스 #3 빌드 C 플랜: `plans/2026-06-20-md1-slice3-learning-engine-c.md`.
- 구현 플랜: `plans/2026-06-22-build-c-concurrency-409.md`.
