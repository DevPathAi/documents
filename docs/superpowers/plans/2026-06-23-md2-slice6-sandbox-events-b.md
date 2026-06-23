# 슬라이스 #6 빌드 B — sandbox-svc 발행 시점·읽기 API·SSE sessionId Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ai-svc 리뷰 워커가 **완료된** sandbox 실행(코드+stdout/exit)을 받을 수 있도록 sandbox-svc를 보강한다: (D-6) outbox 발행을 `createRunning`→`finish`로 이전, (D-7) 코드/결과 조회용 내부 읽기 엔드포인트, (D-8) run SSE가 `sessionId`를 노출.

**Architecture:** 세 변경 모두 sandbox-svc 단독. 발행 시점 이전은 `SandboxRunPersistenceService`의 outbox 호출을 `finish()`(터미널 상태) 안으로 옮긴다(트랜잭션 아웃박스 보장 유지). 읽기 엔드포인트는 게이트웨이를 거치지 않는 내부 경로(`/internal/**`, JWT 면제, 네트워크 신뢰)다. SSE는 실행 종료 시 `session` 이벤트로 id를 보낸다.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Spring MVC(SseEmitter) · Spring Security(oauth2 resource server) · Spring Data JPA · JUnit 5 · Mockito · MockMvc · AssertJ.

## Global Constraints

- 대상 레포: `devpath-sandbox-svc` 단독. 설계서 [2026-06-23-md2-slice6-ai-code-review-design](../specs/2026-06-23-md2-slice6-ai-code-review-design.md) D-6·D-7·D-8.
- **빌드 A(shared `ai_code_reviews`) main 릴리스 후 시작**(본 빌드는 shared 스키마를 직접 쓰진 않지만 슬라이스 순서 유지). 빌드 시작 시 `--refresh-dependencies`.
- 발행 이전은 **트랜잭션 아웃박스 보장 유지**: 발행은 결과 영속과 같은 `@Transactional`(`finish`) 안.
- 읽기 엔드포인트는 **내부 경로**(`/internal/sandbox/sessions/{id}`)로 `permitAll`. 게이트웨이는 `/internal/**`를 라우트하지 않는다(공개 노출 금지). 호출자(ai-svc)는 이벤트의 `userId`로 소유 정합을 자체 확인한다.
- Boot4: `@AutoConfigureMockMvc`=`org.springframework.boot.webmvc.test.autoconfigure`, `@MockitoBean`, 모든 `@SpringBootTest` `@ActiveProfiles("test")`.
- 신규 작업 브랜치는 `develop`에서 분기.

---

## File Structure

- Modify: `src/main/java/ai/devpath/sandbox/run/SandboxRunPersistenceService.java` — `publishSubmitted` 호출을 `createRunning`에서 `finish`로 이전.
- Create: `src/main/java/ai/devpath/sandbox/run/SandboxSessionView.java` — 내부 읽기 응답 record.
- Create: `src/main/java/ai/devpath/sandbox/run/InternalSessionController.java` — `GET /internal/sandbox/sessions/{id}`.
- Modify: `src/main/java/ai/devpath/sandbox/config/SecurityConfig.java` — `/internal/**` permitAll.
- Modify: `src/main/java/ai/devpath/sandbox/run/RunController.java` — SSE `session` 이벤트(sessionId) 추가.
- Modify(test): `src/test/java/ai/devpath/sandbox/run/SandboxRunServiceTest.java` — 백엔드 실패 시 미발행 단언.
- Create(test): `src/test/java/ai/devpath/sandbox/run/InternalSessionControllerTest.java`.
- Modify(test): `src/test/java/ai/devpath/sandbox/run/RunControllerTest.java` — SSE `session` 이벤트 단언.

---

## Task 0: 작업 브랜치

- [ ] **Step 1: 브랜치 분기 + 최신 shared**

```powershell
cd devpath-sandbox-svc
git switch develop
git pull
git switch -c feat/slice6-sandbox-review-hooks
.\gradlew.bat --refresh-dependencies test -Dgroups="!docker"
```

Expected: 기존 단위 테스트 PASS(docker IT 제외). 베이스라인 확보.

---

## Task 1: D-6 — 발행 시점을 `finish()`로 이전

**Files:**
- Modify: `src/main/java/ai/devpath/sandbox/run/SandboxRunPersistenceService.java`
- Test: `src/test/java/ai/devpath/sandbox/run/SandboxRunServiceTest.java`

**Interfaces:**
- Consumes: `SandboxRunEventPublisher.publishSubmitted(long sandboxSessionId, long userId, String language, Long contentId)`(기존), `OutboxRepository.count()`.
- Produces(거동): outbox 발행은 `finish()` 안에서만 일어난다 → 실행이 완료(터미널 상태)된 경우에만 이벤트가 발행된다. 백엔드가 throw하면(`run` 실패) 이벤트는 발행되지 않는다.

- [ ] **Step 1: 실패 테스트 작성**

`SandboxRunServiceTest.java`의 클래스 닫는 `}` 직전에 추가:

```java
  @Test
  void backendFailureDoesNotPublishEvent() {
    when(runnerBackend.run(any(), any()))
        .thenThrow(new SandboxUnavailableException("Docker 미가동"));

    long before = outboxRepo.count();
    assertThrows(SandboxUnavailableException.class, () ->
        service.execute(8L, new SandboxRunRequest("print(1)", "PYTHON", null, null), line -> {}));

    assertEquals(before, outboxRepo.count(),
        "실행이 완료되지 못하면(run throw) 리뷰 이벤트를 발행하지 않는다(발행은 finish에서)");
  }
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.sandbox.run.SandboxRunServiceTest"
```

Expected: `backendFailureDoesNotPublishEvent` FAIL — 현재 `createRunning`이 run 이전에 발행·커밋하므로 outbox에 1건 남아 `before+1 != before`.

- [ ] **Step 3: 발행 호출 이전**

`SandboxRunPersistenceService.java`. `createRunning`에서 `eventPublisher.publishSubmitted(...)` 줄을 **삭제**하고, `finish`에서 `sessions.save(session)` 결과로 발행한다.

`createRunning` (발행 줄 제거):

```java
  /** 세션 생성(ALLOCATING) + RUNNING 전이. 짧은 tx. (제출 이벤트는 finish에서 발행 — D-6) */
  @Transactional
  public SandboxSession createRunning(long userId, SandboxRunRequest req) {
    SandboxSession session = new SandboxSession();
    session.setUserId(userId);
    session.setLanguage(req.language());
    session.setSubmittedCode(req.code());
    session.setContentId(req.contentId());
    session.setCodeBlockId(req.codeBlockId());
    session.setStatus("ALLOCATING");
    session.setStartedAt(Instant.now());
    session = sessions.save(session);

    session.setStatus("RUNNING");
    return sessions.save(session);
  }
```

`finish` (발행 추가):

```java
  /** 실행 결과 반영 + 완료 이벤트 발행(outbox). 짧은 tx. */
  @Transactional
  public SandboxSession finish(SandboxSession session, RunResult result) {
    session.setFinishedAt(Instant.now());
    session.setExitCode(result.exitCode());
    session.setStdout(result.stdout());
    session.setStderr(result.stderr());
    session.setCpuMsUsed(result.cpuMsUsed());
    session.setMemoryMbPeak(result.memoryMbPeak());
    if (result.exitCode() == 0) {
      session.setStatus("COMPLETED");
    } else if (result.exitCode() == -1) {
      session.setStatus("KILLED");
    } else {
      session.setStatus("FAILED");
    }
    SandboxSession saved = sessions.save(session);
    eventPublisher.publishSubmitted(
        saved.getId(), saved.getUserId(), saved.getLanguage(), saved.getContentId());
    return saved;
  }
```

- [ ] **Step 4: 통과 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.sandbox.run.SandboxRunServiceTest"
```

Expected: 신규 + 기존(`successfulRunCompletesSessionAndPublishesEvent`·`outboxEntryIsCreatedForEachRun` 등) 전부 PASS. (성공 실행은 finish에서 발행되므로 `outboxEntryIsCreatedForEachRun`의 +1 단언 유지.) `SandboxRunEventPublisherTest`(발행자 단위)는 무영향.

- [ ] **Step 5: 커밋**

```powershell
git add src/main/java/ai/devpath/sandbox/run/SandboxRunPersistenceService.java src/test/java/ai/devpath/sandbox/run/SandboxRunServiceTest.java
git commit -m "refactor(sandbox): publish run event on finish, not submission (slice6 D-6)"
```

---

## Task 2: D-7 — 내부 세션 읽기 엔드포인트

**Files:**
- Create: `src/main/java/ai/devpath/sandbox/run/SandboxSessionView.java`
- Create: `src/main/java/ai/devpath/sandbox/run/InternalSessionController.java`
- Modify: `src/main/java/ai/devpath/sandbox/config/SecurityConfig.java`
- Test: `src/test/java/ai/devpath/sandbox/run/InternalSessionControllerTest.java`

**Interfaces:**
- Produces(ai-svc `SandboxClient`가 의존): `GET /internal/sandbox/sessions/{id}` → 200 `SandboxSessionView{Long id, Long userId, String language, Long contentId, String submittedCode, String stdout, String stderr, Integer exitCode, String status}` / 404.
- Consumes: `SandboxSessionRepository.findById(Long)`(JpaRepository).

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/sandbox/run/InternalSessionControllerTest.java`:

```java
package ai.devpath.sandbox.run;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class InternalSessionControllerTest {

  @Autowired MockMvc mvc;
  @Autowired SandboxSessionRepository sessions;

  @Test
  void returnsSessionViewWithoutAuth() throws Exception {
    SandboxSession s = new SandboxSession();
    s.setUserId(42L);
    s.setLanguage("PYTHON");
    s.setSubmittedCode("print(1)");
    s.setContentId(7L);
    s.setStatus("COMPLETED");
    s.setStdout("ok\n");
    s.setExitCode(0);
    s.setStartedAt(Instant.now());
    long id = sessions.save(s).getId();

    mvc.perform(get("/internal/sandbox/sessions/" + id))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.userId").value(42))
        .andExpect(jsonPath("$.language").value("PYTHON"))
        .andExpect(jsonPath("$.contentId").value(7))
        .andExpect(jsonPath("$.submittedCode").value("print(1)"))
        .andExpect(jsonPath("$.stdout").value("ok\n"))
        .andExpect(jsonPath("$.exitCode").value(0))
        .andExpect(jsonPath("$.status").value("COMPLETED"));
  }

  @Test
  void missingSessionReturns404() throws Exception {
    mvc.perform(get("/internal/sandbox/sessions/999999999"))
        .andExpect(status().isNotFound());
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.sandbox.run.InternalSessionControllerTest"
```

Expected: 컴파일 실패 또는 401(엔드포인트/permitAll 없음) → FAIL.

- [ ] **Step 3: View + Controller + SecurityConfig 구현**

`src/main/java/ai/devpath/sandbox/run/SandboxSessionView.java`:

```java
package ai.devpath.sandbox.run;

public record SandboxSessionView(
    Long id, Long userId, String language, Long contentId,
    String submittedCode, String stdout, String stderr, Integer exitCode, String status) {

  static SandboxSessionView from(SandboxSession s) {
    return new SandboxSessionView(
        s.getId(), s.getUserId(), s.getLanguage(), s.getContentId(),
        s.getSubmittedCode(), s.getStdout(), s.getStderr(), s.getExitCode(), s.getStatus());
  }
}
```

`src/main/java/ai/devpath/sandbox/run/InternalSessionController.java`:

```java
package ai.devpath.sandbox.run;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/** 서비스 간 내부 조회(게이트웨이 미경유). ai-svc 리뷰 워커가 코드+결과를 가져온다. */
@RestController
@RequestMapping("/internal/sandbox/sessions")
public class InternalSessionController {

  private final SandboxSessionRepository sessions;

  public InternalSessionController(SandboxSessionRepository sessions) {
    this.sessions = sessions;
  }

  @GetMapping("/{id}")
  public SandboxSessionView get(@PathVariable long id) {
    return sessions.findById(id)
        .map(SandboxSessionView::from)
        .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));
  }
}
```

`SecurityConfig.java` — `authorizeHttpRequests` 람다에 `/internal/**` permitAll을 `anyRequest()` 앞에 추가:

```java
        .authorizeHttpRequests(authorize -> authorize
            .requestMatchers("/actuator/health").permitAll()
            .requestMatchers("/internal/**").permitAll()
            .anyRequest().authenticated())
```

- [ ] **Step 4: 통과 확인(fresh DB)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.run.InternalSessionControllerTest"
```

Expected: 두 케이스 PASS.

> 보안 주의: `/internal/**`는 JWT를 면제하므로 게이트웨이 라우트에 절대 포함하지 않는다(빌드 D는 `/reviews/**`만 라우트). 클러스터 네트워크 경계가 1차 방어(설계 D-7).

- [ ] **Step 5: 커밋**

```powershell
git add src/main/java/ai/devpath/sandbox/run/SandboxSessionView.java src/main/java/ai/devpath/sandbox/run/InternalSessionController.java src/main/java/ai/devpath/sandbox/config/SecurityConfig.java src/test/java/ai/devpath/sandbox/run/InternalSessionControllerTest.java
git commit -m "feat(sandbox): internal session read endpoint for ai review worker (slice6 D-7)"
```

---

## Task 3: D-8 — run SSE가 sessionId 노출

**Files:**
- Modify: `src/main/java/ai/devpath/sandbox/run/RunController.java`
- Test: `src/test/java/ai/devpath/sandbox/run/RunControllerTest.java`

**Interfaces:**
- Produces(프론트 빌드 E가 의존): `POST /sandbox/run` SSE가 `log` 이벤트 외에 종료 직전 `session` 이벤트(`event:session\ndata:<sessionId>`)를 1회 보낸다.

- [ ] **Step 1: 실패 테스트 작성**

`RunControllerTest.java`의 클래스 닫는 `}` 직전에 추가:

```java
  @Test
  void sseEmitsSessionIdEvent() throws Exception {
    doReturn(true).when(sandboxRunService).isRunnerAvailable();
    SandboxSession s = org.mockito.Mockito.mock(SandboxSession.class);
    org.mockito.Mockito.when(s.getId()).thenReturn(99L);
    doReturn(s).when(sandboxRunService).execute(anyLong(), any(), any());

    var result = mvc.perform(post("/sandbox/run")
            .with(jwt().jwt(j -> j.subject("42")))
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"code\":\"print(1)\",\"language\":\"PYTHON\"}"))
        .andExpect(request().asyncStarted())
        .andReturn();

    String sse = mvc.perform(asyncDispatch(result))
        .andExpect(status().isOk())
        .andReturn().getResponse().getContentAsString();

    assertThat(sse).contains("event:session");
    assertThat(sse).contains("data:99");
  }
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.sandbox.run.RunControllerTest"
```

Expected: `sseEmitsSessionIdEvent` FAIL(현재 `session` 이벤트 미전송).

- [ ] **Step 3: RunController에 session 이벤트 추가**

`RunController.java`. `CompletableFuture.runAsync` 블록에서 execute 반환 세션을 잡아 `session` 이벤트를 보낸다:

```java
    CompletableFuture.runAsync(() -> {
      try {
        SandboxSession session = runService.execute(userId, req, line -> sendLog(emitter, line));
        sendSession(emitter, session.getId());
        emitter.complete();
      } catch (Exception e) {
        emitter.completeWithError(e);
      }
    });
```

그리고 `sendLog` 옆에 헬퍼 추가:

```java
  private void sendSession(SseEmitter emitter, Long sessionId) {
    try {
      emitter.send(SseEmitter.event().name("session").data(String.valueOf(sessionId)));
    } catch (IOException e) {
      throw new IllegalStateException("SSE send failed", e);
    }
  }
```

- [ ] **Step 4: 통과 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.sandbox.run.RunControllerTest"
```

Expected: 신규 + 기존(`validRequestReturnsSseStreamWithLogEvents` 등) 전부 PASS. (기존 테스트는 `session` 이벤트 부재를 단언하지 않으므로 무영향.)

- [ ] **Step 5: 커밋**

```powershell
git add src/main/java/ai/devpath/sandbox/run/RunController.java src/test/java/ai/devpath/sandbox/run/RunControllerTest.java
git commit -m "feat(sandbox): expose sessionId via run SSE for review polling (slice6 D-8)"
```

---

## Task 4: 전체 회귀 + develop PR

- [ ] **Step 1: 전체 테스트(fresh DB, docker IT 제외)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat clean test -Dgroups="!docker"
```

Expected: 전 단위/통합 PASS, 회귀 없음. (docker IT는 CI에서 별도 실행 — 본 변경과 무관.)

- [ ] **Step 2: PR 생성(develop 대상)**

```powershell
git push -u origin feat/slice6-sandbox-review-hooks
gh pr create --base develop --title "feat(sandbox): 리뷰 연동 훅(발행 finish 이전·내부 읽기 API·SSE sessionId) 슬라이스 #6 빌드 B" --body "D-6 발행을 finish로 이전(완료 후 발행), D-7 GET /internal/sandbox/sessions/{id}(permitAll·게이트웨이 미경유), D-8 run SSE session 이벤트. 설계서 docs/superpowers/specs/2026-06-23-md2-slice6-ai-code-review-design.md"
```

- [ ] **Step 3: CI 녹색 확인 → 머지**

```powershell
gh pr checks --watch
gh pr merge --merge
```

Expected: sandbox-svc CI(build + docker IT) 녹색. 앱/서비스라 main 릴리스는 슬라이스 마지막 통합 릴리스에서.

---

## Self-Review 메모(작성자)

- **Spec 커버리지**: D-6(발행 이전)=Task1, D-7(내부 읽기 API)=Task2, D-8(SSE sessionId)=Task3. 전부 매핑.
- **placeholder 없음**: 모든 코드/테스트/명령 실제값. SSE 테스트는 `mock(SandboxSession.class)`로 `getId()` 제어(엔티티에 setId 없음).
- **타입 일관성**: `SandboxSessionView`(record 9필드)·`GET /internal/sandbox/sessions/{id}`·`session` SSE 이벤트가 본문·테스트·ai-svc(빌드 C `SandboxClient`)·frontend(빌드 E) 참조와 일치. `publishSubmitted` 시그니처 불변(호출 위치만 이동).
- **거동 변화 명시**: 발행이 finish로 이동 → run이 throw하면 이벤트 미발행(Task1 테스트로 실증). 성공/실패(non-zero exit)/killed 실행은 finish 도달 → 발행됨(리뷰 대상).
