# 슬라이스 #7 빌드 B — sandbox-svc userId 기준 최근 N 세션 조회 내부 API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ai-svc 멘토 `MentorContextAssembler`가 `SandboxClient.recentByUser(userId, 5)`로 **현재 사용자의 최근 N개 Sandbox 실행**(코드+stdout/stderr/exit/status)을 받아 context_snapshot에 주입할 수 있도록, sandbox-svc에 userId 기준 최근 N 세션 조회 내부 API를 추가한다: `GET /internal/sandbox/sessions/recent?userId={long}&limit={int}` → `List<SandboxSessionView>`(정렬 `started_at DESC`).

**Architecture:** 변경은 sandbox-svc 단독. 기존 `InternalSessionController`(`@RequestMapping("/internal/sandbox/sessions")`, 단일 `GET /{id}`)에 `@GetMapping("/recent")` 메서드를 추가하고, 바레(bare) `SandboxSessionRepository`에 파생 쿼리 메서드 `findByUserIdOrderByStartedAtDesc(long, Pageable)`를 추가한다. 정렬은 **`started_at DESC`**(기존 인덱스 `idx_sandbox_user_started(user_id, started_at DESC)` 정합 — 설계서 M-3/§2.3/§5/m-3). `limit`은 파라미터화하되 상한 가드(1~20, 기본 5). 응답 `SandboxSessionView`(record 9필드)는 **기존 그대로 재사용**(변경 없음)이라 응답 JSON 필드명이 record 컴포넌트명과 일치 → 빌드 D(ai-svc `SandboxClient.recentByUser`)가 그대로 역직렬화한다. `/internal/**`는 `SecurityConfig`에서 이미 `permitAll`(실측) → **보안 설정 변경 없음**. 호출자(ai-svc)는 JWT subject의 `userId`로 소유 정합을 자체 보장한다(게이트웨이 미경유 내부 경로).

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Spring MVC · Spring Security(oauth2 resource server) · Spring Data JPA(파생 쿼리 + `Pageable`/`PageRequest`) · JUnit 5 · MockMvc · AssertJ/JUnit assertions.

## Global Constraints

- 대상 레포: `devpath-sandbox-svc` 단독. 설계서 [2026-06-24-md3-slice7-ai-mentor-design](../specs/2026-06-24-md3-slice7-ai-mentor-design.md) §5 sandbox-svc·§9 빌드 B·M-3·§2.3.
- **빌드 A(shared `ai_mentor_sessions`) main 릴리스 후 시작**(슬라이스 순서 유지). 본 빌드는 shared 스키마를 직접 쓰진 않지만 순서를 따른다. 빌드 시작 시 `--refresh-dependencies`.
- 읽기 엔드포인트는 **내부 경로**(`/internal/sandbox/sessions/recent`)로 `permitAll`(기존 정책). 게이트웨이는 `/internal/**`를 라우트하지 않는다(공개 노출 금지). 호출자(ai-svc)는 `userId`로 소유 정합을 자체 확인한다.
- **인터페이스 계약 고정(이름·타입 변경 금지)**: 엔드포인트 `GET /internal/sandbox/sessions/recent?userId={long}&limit={int}` → `List<SandboxSessionView>`. `SandboxSessionView`는 기존 record 그대로 재사용: `(Long id, Long userId, String language, Long contentId, String submittedCode, String stdout, String stderr, Integer exitCode, String status)`. 정렬 `started_at DESC`.
- **`SandboxSessionView`·`SecurityConfig`는 변경하지 않는다**(View는 그대로 재사용, `/internal/**`는 이미 permitAll — 실측 §2.1/§2.3 일치).
- Boot4: `@AutoConfigureMockMvc`=`org.springframework.boot.webmvc.test.autoconfigure`, 모든 `@SpringBootTest` `@ActiveProfiles("test")`. 기존 `InternalSessionControllerTest`와 동일 슬라이스 패턴 미러.
- DB가 필요한 `@SpringBootTest`는 fresh DB로 실행(`$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"`). 로컬 인프라가 CI를 가리지 않게 CI 서비스와 일치시킨다(슬라이스 #1~#6 교훈).
- 신규 작업 브랜치는 `develop`에서 분기.

---

## File Structure

- Modify: `src/main/java/ai/devpath/sandbox/run/SandboxSessionRepository.java` — `findByUserIdOrderByStartedAtDesc(long userId, Pageable pageable)` 파생 쿼리 추가.
- Modify: `src/main/java/ai/devpath/sandbox/run/InternalSessionController.java` — `GET /internal/sandbox/sessions/recent` 메서드 추가(limit 가드 1~20·기본 5, `started_at DESC`, `List<SandboxSessionView>`).
- Modify(test): `src/test/java/ai/devpath/sandbox/run/InternalSessionControllerTest.java` — 최근순(`started_at DESC`)·limit·빈 결과·limit 가드 케이스 추가.

> 변경 없음(확인용): `src/main/java/ai/devpath/sandbox/run/SandboxSessionView.java`(record 그대로 재사용), `src/main/java/ai/devpath/sandbox/config/SecurityConfig.java`(`/internal/**` 이미 permitAll).

---

## Task 0: 작업 브랜치

- [ ] **Step 1: 브랜치 분기 + 최신 shared**

```powershell
cd devpath-sandbox-svc
git switch develop
git pull
git switch -c feat/slice7-sandbox-recent-sessions
.\gradlew.bat --refresh-dependencies test -Dgroups="!docker"
```

Expected: 기존 단위/통합 테스트 PASS(docker IT 제외). 베이스라인 확보. (DB 필요 테스트 실패 시 `$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"` 설정 후 재실행.)

---

## Task 1: userId 기준 최근 N 세션 조회 내부 API

**Files:**
- Modify: `src/main/java/ai/devpath/sandbox/run/SandboxSessionRepository.java`
- Modify: `src/main/java/ai/devpath/sandbox/run/InternalSessionController.java`
- Test: `src/test/java/ai/devpath/sandbox/run/InternalSessionControllerTest.java`

**Interfaces:**
- Produces(ai-svc 빌드 D `SandboxClient.recentByUser(userId, 5)`가 의존): `GET /internal/sandbox/sessions/recent?userId={long}&limit={int}` → 200 `List<SandboxSessionView>`. 각 원소 `SandboxSessionView{Long id, Long userId, String language, Long contentId, String submittedCode, String stdout, String stderr, Integer exitCode, String status}`. 정렬 = `started_at DESC`(최신 먼저). `limit` 미지정 시 5, 가드 1~20(0 이하→1, 20 초과→20). 해당 userId 세션 없으면 빈 배열 `[]`.
- Consumes: `SandboxSessionRepository.findByUserIdOrderByStartedAtDesc(long userId, Pageable pageable)`(파생 쿼리, `PageRequest.of(0, limit)`로 limit 적용).

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/sandbox/run/InternalSessionControllerTest.java`의 import 블록을, 기존 정적/일반 import에 더해 `jsonPath` 배열 단언과 `MockMvcRequestBuilders.get`이 모두 들어오도록 둔다(기존 파일에 이미 `get`·`jsonPath`·`status`·`Instant`·`SpringBootTest`·`AutoConfigureMockMvc`·`ActiveProfiles`·`MockMvc`·`SandboxSessionRepository` autowire가 있음). 클래스 닫는 `}` 직전에 아래 4개 테스트를 추가한다.

```java
  @Test
  void recentReturnsSessionsForUserOrderedByStartedAtDesc() throws Exception {
    long userId = 7001L;
    // 의도적으로 삽입 순서와 started_at 순서를 어긋나게 해서 정렬을 실증한다.
    saveSession(userId, "older", Instant.parse("2026-06-24T10:00:00Z"));
    saveSession(userId, "newest", Instant.parse("2026-06-24T12:00:00Z"));
    saveSession(userId, "middle", Instant.parse("2026-06-24T11:00:00Z"));
    // 다른 사용자 세션은 결과에 섞이면 안 된다.
    saveSession(9999L, "other-user", Instant.parse("2026-06-24T13:00:00Z"));

    mvc.perform(get("/internal/sandbox/sessions/recent")
            .param("userId", String.valueOf(userId)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(3))
        .andExpect(jsonPath("$[0].userId").value((int) userId))
        .andExpect(jsonPath("$[0].submittedCode").value("newest"))
        .andExpect(jsonPath("$[1].submittedCode").value("middle"))
        .andExpect(jsonPath("$[2].submittedCode").value("older"));
  }

  @Test
  void recentRespectsLimitParameter() throws Exception {
    long userId = 7002L;
    saveSession(userId, "s1", Instant.parse("2026-06-24T10:00:00Z"));
    saveSession(userId, "s2", Instant.parse("2026-06-24T11:00:00Z"));
    saveSession(userId, "s3", Instant.parse("2026-06-24T12:00:00Z"));

    mvc.perform(get("/internal/sandbox/sessions/recent")
            .param("userId", String.valueOf(userId))
            .param("limit", "2"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(2))
        .andExpect(jsonPath("$[0].submittedCode").value("s3"))
        .andExpect(jsonPath("$[1].submittedCode").value("s2"));
  }

  @Test
  void recentReturnsEmptyArrayWhenNoSessions() throws Exception {
    mvc.perform(get("/internal/sandbox/sessions/recent")
            .param("userId", "70030001"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(0));
  }

  @Test
  void recentClampsLimitToUpperBound() throws Exception {
    long userId = 7004L;
    for (int i = 0; i < 22; i++) {
      saveSession(userId, "c" + i, Instant.parse("2026-06-24T10:00:00Z").plusSeconds(i));
    }

    mvc.perform(get("/internal/sandbox/sessions/recent")
            .param("userId", String.valueOf(userId))
            .param("limit", "999"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(20));
  }

  private void saveSession(long userId, String code, Instant startedAt) {
    SandboxSession s = new SandboxSession();
    s.setUserId(userId);
    s.setLanguage("PYTHON");
    s.setSubmittedCode(code);
    s.setStatus("COMPLETED");
    s.setExitCode(0);
    s.setStartedAt(startedAt);
    sessions.save(s);
  }
```

> 참고: 엔티티 `@PrePersist`는 `startedAt`이 `null`일 때만 현재시각을 채운다(실측) → 위처럼 명시값을 주면 정렬을 결정적으로 검증할 수 있다.

- [ ] **Step 2: 실패 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.run.InternalSessionControllerTest"
```

Expected: 컴파일 실패 — `recentReturnsSessionsForUserOrderedByStartedAtDesc` 등이 참조하는 `GET /recent` 핸들러 및 `findByUserIdOrderByStartedAtDesc` 미존재(엔드포인트 부재 → 404/매핑 없음, 신규 테스트 4종 FAIL). 기존 `returnsSessionViewWithoutAuth`·`missingSessionReturns404`는 영향 없음.

- [ ] **Step 3: 리포지토리 파생 쿼리 + 컨트롤러 핸들러 구현**

`src/main/java/ai/devpath/sandbox/run/SandboxSessionRepository.java` 전체를 아래로 교체(파생 쿼리 추가):

```java
package ai.devpath.sandbox.run;

import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SandboxSessionRepository extends JpaRepository<SandboxSession, Long> {

  /** 사용자별 최근 실행(started_at DESC). limit은 Pageable로 적용(인덱스 idx_sandbox_user_started 정합). */
  List<SandboxSession> findByUserIdOrderByStartedAtDesc(long userId, Pageable pageable);
}
```

`src/main/java/ai/devpath/sandbox/run/InternalSessionController.java` 전체를 아래로 교체(`/recent` 핸들러 + limit 가드 추가, 기존 `GET /{id}` 보존):

```java
package ai.devpath.sandbox.run;

import java.util.List;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/** 서비스 간 내부 조회(게이트웨이 미경유). ai-svc 워커가 코드+결과를 가져온다(슬라이스 #6 D-7, 슬라이스 #7 멘토 context). */
@RestController
@RequestMapping("/internal/sandbox/sessions")
public class InternalSessionController {

  private static final int DEFAULT_LIMIT = 5;
  private static final int MAX_LIMIT = 20;

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

  /** 사용자별 최근 실행(started_at DESC). 멘토 context_snapshot 주입용(슬라이스 #7 빌드 D 소비). */
  @GetMapping("/recent")
  public List<SandboxSessionView> recent(
      @RequestParam long userId,
      @RequestParam(defaultValue = "5") int limit) {
    int clamped = Math.min(Math.max(limit, 1), MAX_LIMIT);
    return sessions.findByUserIdOrderByStartedAtDesc(userId, PageRequest.of(0, clamped))
        .stream()
        .map(SandboxSessionView::from)
        .toList();
  }
}
```

> `DEFAULT_LIMIT`은 `@RequestParam(defaultValue = "5")`로 동일값을 강제(상수는 문서/가독성용). `SandboxSessionView`·`SecurityConfig`는 변경하지 않는다(`/internal/**` 이미 permitAll).

- [ ] **Step 4: 통과 확인(fresh DB)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.run.InternalSessionControllerTest"
```

Expected: 신규 4종(`recentReturnsSessionsForUserOrderedByStartedAtDesc`·`recentRespectsLimitParameter`·`recentReturnsEmptyArrayWhenNoSessions`·`recentClampsLimitToUpperBound`) + 기존 2종(`returnsSessionViewWithoutAuth`·`missingSessionReturns404`) 전부 PASS.

> 보안 주의: `/internal/**`는 JWT를 면제하므로 게이트웨이 라우트에 절대 포함하지 않는다(빌드 E는 `/ai-mentor/**`만 라우트). 클러스터 네트워크 경계가 1차 방어(설계 M-3/§2.4).

- [ ] **Step 5: 커밋**

```powershell
git add src/main/java/ai/devpath/sandbox/run/SandboxSessionRepository.java src/main/java/ai/devpath/sandbox/run/InternalSessionController.java src/test/java/ai/devpath/sandbox/run/InternalSessionControllerTest.java
git commit -m "feat(sandbox): internal recent-sessions-by-user endpoint for ai mentor context (slice7 B)"
```

---

## Task 2: 전체 회귀 + develop PR

- [ ] **Step 1: 전체 테스트(fresh DB, docker IT 제외)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat clean test -Dgroups="!docker"
```

Expected: 전 단위/통합 PASS, 회귀 없음. (docker IT는 CI에서 별도 실행 — 본 변경과 무관.)

- [ ] **Step 2: PR 생성(develop 대상)**

```powershell
git push -u origin feat/slice7-sandbox-recent-sessions
gh pr create --base develop --title "feat(sandbox): userId 최근 N 세션 조회 내부 API(started_at DESC) 슬라이스 #7 빌드 B" --body "GET /internal/sandbox/sessions/recent?userId={}&limit={}(permitAll·게이트웨이 미경유) → List<SandboxSessionView>, started_at DESC, limit 가드 1~20(기본 5). ai-svc 멘토 context_snapshot(SandboxClient.recentByUser) 소비. 설계서 docs/superpowers/specs/2026-06-24-md3-slice7-ai-mentor-design.md §9 빌드 B·M-3"
```

- [ ] **Step 3: CI 녹색 확인 → 머지**

```powershell
gh pr checks --watch
gh pr merge --merge
```

Expected: sandbox-svc CI(build + docker IT) 녹색. 앱/서비스라 main 릴리스는 슬라이스 마지막 통합 릴리스에서.

---

## Self-Review 메모(작성자)

- **Spec 커버리지**: 설계서 §5 sandbox-svc(`GET /internal/sandbox/sessions/recent` + `findBy…StartedAtDesc` + 테스트)·§9 빌드 B·M-3·§2.3을 Task1에 매핑. 정렬은 `started_at DESC`(인덱스 `idx_sandbox_user_started(user_id, started_at DESC)` 정합, m-3) — `created_at` 아님.
- **인터페이스 고정**: `SandboxSessionView`(record 9필드)를 **변경 없이 재사용** → 응답 JSON 필드명이 record 컴포넌트명과 일치 → 빌드 D ai-svc `SandboxClient.recentByUser(userId, 5)`가 그대로 역직렬화. 엔드포인트/쿼리파라미터(`userId`·`limit`) 이름·타입 고정.
- **placeholder 없음**: 모든 코드/테스트/명령 실제값. limit 가드는 `Math.min(Math.max(limit,1),20)`로 1~20 클램프, 기본 5(`@RequestParam(defaultValue="5")`). limit은 `PageRequest.of(0, clamped)`로 적용(파생 쿼리 `Pageable`).
- **테스트 결정성**: 엔티티 `@PrePersist`가 `startedAt==null`일 때만 채움을 실측 → 테스트가 명시 `startedAt`을 주입해 `started_at DESC` 정렬·limit·타 사용자 분리·상한 클램프를 결정적으로 단언. 기존 `InternalSessionControllerTest` 슬라이스 패턴(`@SpringBootTest`+`@AutoConfigureMockMvc`+`@ActiveProfiles("test")`, `@Autowired MockMvc`/`SandboxSessionRepository`) 미러.
- **변경 최소·범위 고정**: `SecurityConfig`(`/internal/**` 이미 permitAll, 실측 §2.1/§2.3) 및 `SandboxSessionView` 무변경. 신규 파일 없음(전부 기존 3파일 수정). 빌드 B 경계 내(다른 빌드 A/C/D/E/F·gateway·shared·frontend 미변경).
- **거동**: `userId` 세션 없으면 빈 배열, limit 미지정 5·하한 1·상한 20. 타 사용자 세션은 `findByUserId…`의 `user_id` 술어로 자연 분리.
