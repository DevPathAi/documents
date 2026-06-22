# 학습경로 동시 생성 충돌 409 처리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 동일 사용자의 동시 학습경로 생성이 `learning_paths` partial UNIQUE를 위반할 때, 이를 명시적 409 CONFLICT(`PATH_GENERATION_CONFLICT`)로 변환하고 최종 ACTIVE 경로가 항상 1개로 수렴함을 테스트로 보장한다.

**Architecture:** `LearningPathPersistenceService.persist()`에서 `save`를 `saveAndFlush`로 바꿔 제약 위반을 `@Transactional` 경계 안에서 포착하고, `DataIntegrityViolationException`을 도메인 예외 `ActivePathConflictException`으로 변환한다. `GlobalExceptionHandler`가 이를 409로 매핑한다. SSE(`generate`)는 기존 `error(message)` 채널을 그대로 쓰되 예외 메시지에 코드 문자열을 담아 노출한다(`NoCompletedAssessmentException` 패턴 재사용). 추가 락/직렬화는 도입하지 않는다.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Spring Data JPA · PostgreSQL 17(pgvector) · JUnit 5 · Mockito · MockMvc · AssertJ.

## Global Constraints

- 대상 레포: `devpath-learning-svc` 단독. shared 스키마 변경 없음(partial UNIQUE는 이미 `V202606181006`).
- DB partial UNIQUE(`learning_paths(user_id) WHERE status='ACTIVE'`)가 동시성 정합의 진실의 원천. 락/직렬화 추가 금지(사용자 결정).
- 모든 변경은 실패 테스트 우선(레포 CLAUDE.md 절대조건 2). 검증은 fresh DB 또는 CI(postgres+redis)로 확인(로컬 인프라가 빈 DB 실패를 가린 전례 — 슬라이스 #2/#3 교훈).
- 모든 `@SpringBootTest`는 `@ActiveProfiles("test")`. Boot4 모듈: `@AutoConfigureMockMvc`=`org.springframework.boot.webmvc.test.autoconfigure`.
- `errorCode` 명칭: `PATH_GENERATION_CONFLICT`(기존 `NO_COMPLETED_ASSESSMENT` 패턴과 일관).
- JsonMapper는 Boot4 Jackson3(`tools.jackson.databind.json.JsonMapper`).
- 신규 작업 브랜치는 `develop`에서 분기(레포 CLAUDE.md 규칙 4).

---

## File Structure

- Create: `src/main/java/ai/devpath/learning/path/ActivePathConflictException.java` — `RuntimeException(message, cause)`. 메시지에 `PATH_GENERATION_CONFLICT` 포함.
- Modify: `src/main/java/ai/devpath/learning/path/LearningPathPersistenceService.java:65` — `paths.save(path)` → `saveAndFlush` + `DataIntegrityViolationException` catch → `ActivePathConflictException`.
- Modify: `src/main/java/ai/devpath/learning/config/GlobalExceptionHandler.java` — `ActivePathConflictException` → 409 + `errorCode: PATH_GENERATION_CONFLICT`.
- Create(test): `src/test/java/ai/devpath/learning/path/LearningPathPersistenceServiceTest.java` — 변환 단위 테스트.
- Create(test): `src/test/java/ai/devpath/learning/path/LearningPathConflictMappingTest.java` — 컨트롤러 MockMvc(409 + SSE errorCode).
- Create(test): `src/test/java/ai/devpath/learning/path/LearningPathConcurrencyIT.java` — 동시 생성 ACTIVE=1 불변.
- **수정 불필요(실측 확정)**: `PathProgressEvent.java`, `LearningPathController.java`. 이유: `LearningPathController.generate`는 예외 시 `PathProgressEvent.error(e.getMessage())`로 메시지를 SSE에 그대로 싣고, `NoCompletedAssessmentException`도 메시지("NO_COMPLETED_ASSESSMENT: ...")로 코드를 노출한다. `ActivePathConflictException` 메시지에 코드 문자열을 담으면 동일 경로로 노출된다.

---

## Task 0: 작업 브랜치

- [ ] **Step 1: 브랜치 분기**

```powershell
cd devpath-learning-svc
git switch develop
git pull
git switch -c fix/learning-path-concurrency-409
```

- [ ] **Step 2: 최신 shared 반영 확인(빌드 grün 베이스라인)**

```powershell
.\gradlew.bat --refresh-dependencies test --tests "ai.devpath.learning.path.LearningPathEngineTest"
```

Expected: 기존 9개 케이스 PASS(베이스라인). 실패하면 먼저 원인 규명(이 작업과 무관한 환경 문제 배제).

---

## Task 1: 예외 변환 (`save`→`saveAndFlush` + `ActivePathConflictException`)

**Files:**
- Create: `src/main/java/ai/devpath/learning/path/ActivePathConflictException.java`
- Modify: `src/main/java/ai/devpath/learning/path/LearningPathPersistenceService.java`
- Test: `src/test/java/ai/devpath/learning/path/LearningPathPersistenceServiceTest.java`

**Interfaces:**
- Produces: `ActivePathConflictException(String message, Throwable cause) extends RuntimeException`.
- Consumes: `LearningPathRepository.saveAndFlush(LearningPath)`(JpaRepository 상속), `org.springframework.dao.DataIntegrityViolationException`.

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/learning/path/LearningPathPersistenceServiceTest.java`:

```java
package ai.devpath.learning.path;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import ai.devpath.learning.outbox.OutboxRepository;
import ai.devpath.learning.path.ai.PathGenerateResult;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;
import tools.jackson.databind.json.JsonMapper;

class LearningPathPersistenceServiceTest {

  @Test
  void persistTranslatesUniqueViolationToActivePathConflict() {
    LearningPathRepository paths = mock(LearningPathRepository.class);
    OutboxRepository outbox = mock(OutboxRepository.class);
    JsonMapper jsonMapper = JsonMapper.builder().build();
    when(paths.saveAndFlush(any(LearningPath.class)))
        .thenThrow(new DataIntegrityViolationException("uq learning_paths active user"));
    var service = new LearningPathPersistenceService(paths, outbox, jsonMapper);

    var diagnosis = new LatestDiagnosis(1L, "BACKEND_SPRING", "JUNIOR",
        List.of(), List.of(), 0.9);
    var aiResult = new PathGenerateResult("rationale", List.of());
    var generated = new GeneratedLearningPath(diagnosis, aiResult, List.of());

    assertThatThrownBy(() -> service.persist(42L, generated))
        .isInstanceOf(ActivePathConflictException.class)
        .hasMessageContaining("PATH_GENERATION_CONFLICT");
  }
}
```

> 빈 `milestones`라 persist의 milestone 루프는 돌지 않고, `archiveActiveByUserId`(mock 기본 0 반환) 직후 `saveAndFlush`에서 예외가 발생한다. `publishGenerated`(JsonMapper 사용)는 예외로 도달하지 않으므로 jsonMapper는 빈 인스턴스로 충분하다.

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.path.LearningPathPersistenceServiceTest"
```

Expected: 컴파일 실패(`ActivePathConflictException` 없음) 또는 `saveAndFlush` 미사용으로 변환 안 됨 → FAIL.

- [ ] **Step 3: 예외 클래스 생성**

`src/main/java/ai/devpath/learning/path/ActivePathConflictException.java`:

```java
package ai.devpath.learning.path;

public class ActivePathConflictException extends RuntimeException {
  public ActivePathConflictException(String message, Throwable cause) {
    super(message, cause);
  }
}
```

- [ ] **Step 4: persist 변환 구현**

`LearningPathPersistenceService.java`. import 추가:

```java
import org.springframework.dao.DataIntegrityViolationException;
```

`paths.save(path)` 줄(현재 `:65`)을 아래로 교체:

```java
    LearningPath saved;
    try {
      saved = paths.saveAndFlush(path);
    } catch (DataIntegrityViolationException e) {
      throw new ActivePathConflictException(
          "PATH_GENERATION_CONFLICT: an active learning path already exists for user " + userId, e);
    }
    publishGenerated(saved);
    return saved;
```

- [ ] **Step 5: 통과 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.path.LearningPathPersistenceServiceTest"
```

Expected: PASS.

- [ ] **Step 6: 커밋**

```powershell
git add src/main/java/ai/devpath/learning/path/ActivePathConflictException.java src/main/java/ai/devpath/learning/path/LearningPathPersistenceService.java src/test/java/ai/devpath/learning/path/LearningPathPersistenceServiceTest.java
git commit -m "fix(path): translate active-path unique violation to ActivePathConflictException"
```

---

## Task 2: 409 매핑 + SSE errorCode 노출

**Files:**
- Modify: `src/main/java/ai/devpath/learning/config/GlobalExceptionHandler.java`
- Test: `src/test/java/ai/devpath/learning/path/LearningPathConflictMappingTest.java`

**Interfaces:**
- Consumes: `ActivePathConflictException`(Task 1), `LearningPathGenerationService.generate(long, String, Consumer<PathProgressEvent>)`.
- regenerate 엔드포인트: `POST /learning-paths/me/regenerate` → 동기 `ResponseEntity`. generate 엔드포인트: `POST /learning-paths/me/generate` → SSE.

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/learning/path/LearningPathConflictMappingTest.java`:

```java
package ai.devpath.learning.path;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class LearningPathConflictMappingTest {
  @Autowired MockMvc mvc;
  @MockitoBean LearningPathGenerationService generation;

  @Test
  void regenerateReturns409WithErrorCodeOnConflict() throws Exception {
    when(generation.generate(anyLong(), any(), any()))
        .thenThrow(new ActivePathConflictException("PATH_GENERATION_CONFLICT: dup", null));

    mvc.perform(post("/learning-paths/me/regenerate")
            .with(jwt().jwt(j -> j.subject("42")))
            .contentType(MediaType.APPLICATION_JSON).content("{\"goal\":\"g\"}"))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.errorCode").value("PATH_GENERATION_CONFLICT"));
  }

  @Test
  void generateSseEmitsErrorStageWithConflictCode() throws Exception {
    when(generation.generate(anyLong(), any(), any()))
        .thenThrow(new ActivePathConflictException("PATH_GENERATION_CONFLICT: dup", null));

    var result = mvc.perform(post("/learning-paths/me/generate")
            .with(jwt().jwt(j -> j.subject("42"))))
        .andExpect(request().asyncStarted()).andReturn();
    String sse = mvc.perform(asyncDispatch(result)).andExpect(status().isOk())
        .andReturn().getResponse().getContentAsString();

    org.assertj.core.api.Assertions.assertThat(sse).contains("\"stage\":\"error\"");
    org.assertj.core.api.Assertions.assertThat(sse).contains("PATH_GENERATION_CONFLICT");
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.path.LearningPathConflictMappingTest"
```

Expected: `regenerateReturns409...`는 500(핸들러 없음)으로 FAIL. SSE 테스트는 `generate`가 mock이라 progress 콜백을 호출하지 않으므로 error 이벤트만 나오고 코드 문자열은 메시지 경유로 포함 — 핸들러 추가 전에는 regenerate가 핵심 FAIL.

- [ ] **Step 3: GlobalExceptionHandler에 핸들러 추가**

`GlobalExceptionHandler.java`. import 추가:

```java
import ai.devpath.learning.path.ActivePathConflictException;
```

`NoCompletedAssessmentException` 핸들러 아래에 추가:

```java
  @ExceptionHandler(ActivePathConflictException.class)
  public ResponseEntity<Map<String, String>> activePathConflict(ActivePathConflictException e) {
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(Map.of("errorCode", "PATH_GENERATION_CONFLICT", "error", e.getMessage()));
  }
```

- [ ] **Step 4: 통과 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.path.LearningPathConflictMappingTest"
```

Expected: 두 케이스 PASS. (SSE 테스트가 메시지 문자열 `PATH_GENERATION_CONFLICT` 포함을 확인 — `ActivePathConflictException` 메시지가 `PathProgressEvent.error(e.getMessage())`로 전달됨.)

- [ ] **Step 5: 커밋**

```powershell
git add src/main/java/ai/devpath/learning/config/GlobalExceptionHandler.java src/test/java/ai/devpath/learning/path/LearningPathConflictMappingTest.java
git commit -m "fix(path): map ActivePathConflictException to 409 with PATH_GENERATION_CONFLICT code"
```

---

## Task 3: 동시 생성 통합 테스트 (ACTIVE=1 불변)

**Files:**
- Test: `src/test/java/ai/devpath/learning/path/LearningPathConcurrencyIT.java`

**Interfaces:**
- Consumes: `LearningPathGenerationService.generate`, `ActivePathConflictException`(Task 1), `LearningPathEngineTest`의 seed/aiResult 헬퍼 패턴.

- [ ] **Step 1: 실패(또는 보호) 테스트 작성**

`src/test/java/ai/devpath/learning/path/LearningPathConcurrencyIT.java`. seed 헬퍼는 `LearningPathEngineTest.java`의 `seedUser`/`seedContent`/`aiResult`/`vector`/`vectorLiteral`/`uniqueId`와 동일 구현을 복사하고, 완료 진단 seed는 아래 `seedCompletedAssessment`를 사용한다:

```java
package ai.devpath.learning.path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import ai.devpath.learning.path.ai.AiPathClient;
import ai.devpath.learning.path.ai.PathGenerateResult;
import java.time.Instant;
import java.util.List;
import java.util.concurrent.*;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

@SpringBootTest
@ActiveProfiles("test")
class LearningPathConcurrencyIT {
  @Autowired LearningPathGenerationService generation;
  @Autowired JdbcTemplate jdbc;
  @MockitoBean AiPathClient aiClient;

  @Test
  void concurrentGenerateKeepsExactlyOneActivePathAndConflictsAre409() throws Exception {
    long userId = uniqueId();
    seedUser(userId);
    seedCompletedAssessment(userId);
    seedContent("c1-" + userId, "BACKEND_SPRING", "PUBLISHED", 0.10);
    seedContent("c2-" + userId, "BACKEND_SPRING", "PUBLISHED", 0.11);
    seedContent("c3-" + userId, "BACKEND_SPRING", "PUBLISHED", 0.12);
    when(aiClient.generate(any())).thenReturn(aiResult());
    when(aiClient.embed(any())).thenReturn(List.of(vector(0.10)));

    ExecutorService pool = Executors.newFixedThreadPool(2);
    CountDownLatch start = new CountDownLatch(1);
    Callable<Object> call = () -> {
      start.await();
      try {
        return generation.generate(userId, "goal", e -> {});
      } catch (Throwable t) {
        return t;
      }
    };
    Future<Object> f1 = pool.submit(call);
    Future<Object> f2 = pool.submit(call);
    start.countDown();
    Object r1 = f1.get(30, TimeUnit.SECONDS);
    Object r2 = f2.get(30, TimeUnit.SECONDS);
    pool.shutdown();

    List<Object> results = List.of(r1, r2);
    long success = results.stream().filter(r -> r instanceof LearningPath).count();

    Integer active = jdbc.queryForObject(
        "select count(*) from learning_paths where user_id = ? and status = 'ACTIVE'",
        Integer.class, userId);
    assertThat(active).isEqualTo(1);          // 핵심 불변식: ACTIVE는 항상 정확히 1
    assertThat(success).isGreaterThanOrEqualTo(1);
    // 충돌이 발생했다면 반드시 ActivePathConflictException(500/기타 예외 금지)
    results.stream().filter(r -> r instanceof Throwable)
        .forEach(r -> assertThat(r).isInstanceOf(ActivePathConflictException.class));
  }

  private void seedCompletedAssessment(long userId) {
    Long assessmentId = jdbc.queryForObject("""
        insert into assessments(user_id, track, status, current_difficulty, started_at, completed_at)
        values (?, 'BACKEND_SPRING', 'COMPLETED', 0.3, now(), now()) returning id
        """, Long.class, userId);
    jdbc.update("""
        insert into assessment_results(assessment_id, diagnosed_level, concept_scores,
          strength_concepts, weakness_concepts, confidence_weight)
        values (?, 'JUNIOR', cast('{}' as jsonb), cast('[\"Java syntax\"]' as jsonb),
          cast('[\"Spring MVC\"]' as jsonb), 0.9)
        """, assessmentId);
  }

  // --- 아래 헬퍼는 LearningPathEngineTest.java에서 동일 구현 복사 ---
  // private void seedUser(long userId) { ... on conflict (id) do nothing ... }
  // private long seedContent(String slug, String track, String status, double value) { ... }
  // private PathGenerateResult aiResult() { ... }
  // private List<Double> vector(double value) { return java.util.Collections.nCopies(768, value); }
  // private String vectorLiteral(double value) { ... }
  // private long uniqueId() { return System.nanoTime() % 1_000_000_000L; }
}
```

> **테스트 설계 노트:** 이 클래스에는 `@Transactional`을 **붙이지 않는다**. 붙이면 테스트가 단일 트랜잭션으로 묶여 두 스레드의 독립 트랜잭션 동시성을 재현할 수 없다. user 격리는 `uniqueId()`(nanoTime)로 보장하므로 별도 cleanup 없이 다른 테스트와 충돌하지 않는다.
>
> **비결정성 처리:** 두 트랜잭션이 순차로 실행되면(두 번째가 첫 번째 ACTIVE를 archive 후 신규 생성) `success==2`가 될 수 있고, 동시면 한쪽이 충돌해 `success==1`이 된다. 어느 경우든 **최종 ACTIVE는 정확히 1**이라는 불변식과 "충돌이 나면 반드시 `ActivePathConflictException`"이라는 성질은 항상 성립한다. 변환 자체의 결정적 검증은 Task 1(단위)·Task 2(매핑)가 담당하므로, 본 IT는 동시성 안전성(불변식)에 집중한다.

- [ ] **Step 2: fresh DB로 실행**

```powershell
# 빈 DB(devpath_citest)로 CI 동등 검증 — 메인 devpath DB는 기존 데이터가 가릴 수 있음
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.learning.path.LearningPathConcurrencyIT"
```

Expected: PASS(ACTIVE=1). 만약 충돌 경로에서 `ActivePathConflictException`이 아닌 다른 예외(예: 변환 누락 시 `DataIntegrityViolationException`/`UnexpectedRollbackException`)가 나오면 FAIL → Task 1 변환 재점검.

- [ ] **Step 3: 커밋**

```powershell
git add src/test/java/ai/devpath/learning/path/LearningPathConcurrencyIT.java
git commit -m "test(path): concurrent generate keeps exactly one active path"
```

---

## Task 4: 전체 회귀 + CI 검증

- [ ] **Step 1: 전체 테스트(fresh DB)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat clean test
```

Expected: 기존 `LearningPathEngineTest` 9개 + 신규 3개 클래스 전부 PASS. 회귀 없음.

- [ ] **Step 2: PR 생성(develop 대상)**

```powershell
git push -u origin fix/learning-path-concurrency-409
gh pr create --base develop --title "fix(path): 학습경로 동시 생성 충돌 409 처리" --body "동시 생성 시 partial UNIQUE 위반을 ActivePathConflictException→409(PATH_GENERATION_CONFLICT)로 변환. 동시성 IT로 ACTIVE=1 불변 검증. 설계서 docs/superpowers/specs/2026-06-22-build-c-concurrency-409-design.md"
```

- [ ] **Step 3: CI 녹색 확인**

```powershell
gh pr checks --watch
```

Expected: learning-svc CI(postgres pgvector + redis) build 녹색. 녹색 확인 후에만 머지 가능(컨트롤러가 직접 검증).

---

## Self-Review 메모(작성자)

- **Spec 커버리지**: DoD의 ①동시 1성공/1충돌(Task 3 best-effort + Task 1/2 결정적) ②ACTIVE=1(Task 3) ③regenerate 409+errorCode(Task 2) ④SSE errorCode(Task 2) ⑤fresh DB/CI(Task 3/4) ⑥기존 회귀(Task 4) — 전부 매핑됨.
- **placeholder 없음**: 모든 코드 블록은 실제 코드. seed 헬퍼만 기존 `LearningPathEngineTest`에서 복사 지시(중복 코드 방지 + 기존 검증된 구현 재사용).
- **타입 일관성**: `ActivePathConflictException(String, Throwable)`, `saveAndFlush`, `errorCode=PATH_GENERATION_CONFLICT`가 전 Task 일관.
- **정정**: spec §4의 "PathProgressEvent/Controller 필요 시 수정"은 실측 결과 **수정 불필요**로 확정(메시지 채널 재사용). spec에도 반영.
