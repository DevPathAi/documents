# 슬라이스 #7 빌드 D1 — ai-svc 멘토 파이프라인(SSE·컨텍스트·참고자료·영속, Mock provider) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.
> ⚠️ **직접 작업 권장**(빌드 D는 인터페이스 허브 + SSE 신규 + 후속 D2에 인젝션/탈옥 표현). 위임 시 콘텐츠필터·계약 불일치 위험(#5 B2·#6 C 교훈).

**Goal:** ai-svc에 AI 멘토 동기 SSE 스트리밍 파이프라인을 **Mock provider로 끝단간** 구축한다: `POST /ai-mentor/sessions {message, contentId?}` → kill-switch 선체크 → 전용 스레드에서 context_snapshot 조립(sandbox 최근5 + 현재 콘텐츠) → `event:references`(임베딩 유사검색) → `event:token` 스트림(Mock) → 완료 후 `ai_mentor_sessions` 1행 영속. 실 provider(Claude/Ollama)·인젝션 방어 프롬프트·골든 eval은 **빌드 D2**.

**Architecture:** webmvc `SseEmitter`(webflux 전환 없음). 컨트롤러는 kill-switch 선체크 후 emitter를 만들어 **전용 `TaskExecutor`**에 오케스트레이션을 제출하고 즉시 반환한다. `MentorService`가 별도 스레드에서 context 조립→references 방출→`AiMentorClient.stream()`(토큰 sink)→완료 영속→`emitter.complete()`, 실패 시 FAILED 영속→`emitter.completeWithError()`. 교차서비스 조회는 단방향 `SandboxClient.recentByUser`(빌드 B)·`LearningClient.getContent/searchSimilar`(빌드 C). Kafka 미사용(동기). `AiMentorClient`는 인터페이스 + D1의 `MockMentorClient`만(실 provider는 D2).

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Spring MVC `SseEmitter` · `ThreadPoolTaskExecutor` · Spring Data JPA(`@JdbcTypeCode(SqlTypes.JSON)`) · Spring Security(oauth2 resource server) · RestClient(내부 호출) · JUnit 5 · MockMvc(async) · JsonMapper(Jackson3).

## Global Constraints

- 대상 레포: `devpath-ai-svc` 단독. 설계서 [2026-06-24-md3-slice7-ai-mentor-design](../specs/2026-06-24-md3-slice7-ai-mentor-design.md) §3(M-1·M-2·M-3·M-6·M-7·M-9)·§4·§5 ai-svc·§6·§7·§9 빌드 D.
- **빌드 A(shared `ai_mentor_sessions`) main 릴리스 후 시작**(엔티티가 스키마 의존). 시작 시 `.\gradlew.bat --refresh-dependencies`.
- **빌드 B/C와 인터페이스 계약 고정(consume, 이름·타입 변경 금지)**:
  - sandbox-svc(빌드 B): `GET {SANDBOX_URI}/internal/sandbox/sessions/recent?userId={long}&limit={int}` → `SandboxSessionView[]`{`id,userId,language,contentId,submittedCode,stdout,stderr,exitCode,status`}.
  - learning-svc(빌드 C): `GET {LEARNING_URI}/internal/contents/{id}` → `{id,slug,title,track,body}`; `POST {LEARNING_URI}/internal/contents/similar` body `{embedding:double[768], limit:int, track:String?}` → `[{contentId,slug,title}]`.
- **deps는 이미 충족**(실측): `webmvc`·`data-jpa`·`security`·`oauth2-resource-server`·`anthropic-java:2.34.0`·`devpath-shared`·`postgresql`. **build.gradle 변경 없음**(D2도 deps 추가 없음 — anthropic-java 기존재). `application.yml`에 `devpath.mentor`·`devpath.learning` 블록만 추가.
- **provider 기본 = mock**(`devpath.mentor.provider:mock`). CI/test는 Mock(외부 LLM 0). 실 provider는 D2.
- **SecurityConfig 변경 없음**(I-6): `/ai-mentor/**`는 기존 `anyRequest().authenticated()`로 인증 강제(실측 §2.1).
- **SSE 에러 계약(M-2, C-1)**: kill-switch는 **스트림 개시 전 503**(비-200) → 프론트 기존 `isKillSwitch`. 스트림 개시 후 LLM/내부 실패는 `emitter.completeWithError()`. **in-band `event:error`/`event:done` 없음**. (quota는 본 슬라이스 미강제 — MD4, 표면만 프론트가 보유.)
- 영속(M-6): 스트림 **정상 완료 시에만** DONE 1행 insert(PENDING 선삽입 없음). 실패 시 FAILED 1행. 짧은 `@Transactional`(ReviewPersistenceService 패턴).
- 모든 `@SpringBootTest` `@ActiveProfiles("test")`. CI postgres(pgvector). Kafka 불요(멘토 미사용) — 단 기존 #6 Kafka 자동설정이 컨텍스트 기동에 영향 없는지 IT에서 확인.
- 신규 작업 브랜치는 `develop`에서 분기.

---

## File Structure (D1)

- Modify: `src/main/resources/application.yml` — `devpath.mentor`(provider·timeout·executor)·`devpath.learning.base-url` 추가.
- Create: `src/main/java/ai/devpath/aigw/mentor/AiMentorSession.java` — `ai_mentor_sessions` 엔티티(JSONB context_snapshot·reference_links).
- Create: `src/main/java/ai/devpath/aigw/mentor/AiMentorSessionRepository.java`.
- Create: `src/main/java/ai/devpath/aigw/mentor/MentorPersistenceService.java` — DONE/FAILED 1행 영속(짧은 tx).
- Create: `src/main/java/ai/devpath/aigw/mentor/LearningClient.java` + `InternalContentView.java` + `SimilarQuery.java` + `SimilarContent.java` + `LearningUnavailableException.java`.
- Modify: `src/main/java/ai/devpath/aigw/review/SandboxClient.java` — `recentByUser(long, int)` 추가(기존 `getSession` 보존).
- Create: `src/main/java/ai/devpath/aigw/mentor/MentorContext.java` + `MentorContextAssembler.java`.
- Create: `src/main/java/ai/devpath/aigw/mentor/AiMentorClient.java`(인터페이스) + `MentorInput.java` + `MockMentorClient.java`.
- Create: `src/main/java/ai/devpath/aigw/mentor/MentorReferenceService.java`.
- Create: `src/main/java/ai/devpath/aigw/mentor/MentorService.java` — 오케스트레이션(전용 스레드).
- Create: `src/main/java/ai/devpath/aigw/mentor/MentorExecutorConfig.java` — 전용 `ThreadPoolTaskExecutor`.
- Create: `src/main/java/ai/devpath/aigw/mentor/MentorController.java` + `MentorRequest.java` + `MentorKillSwitchException.java`.
- Modify: `src/main/java/ai/devpath/aigw/config/GlobalExceptionHandler.java` — `MentorKillSwitchException` → 503.
- Create(test): 단위(`MentorContextAssemblerTest`·`MockMentorClientTest`·`MentorReferenceServiceTest`·`MentorPersistenceServiceTest`) + IT(`MentorSseIntegrationTest`).

---

## Task 0: 브랜치 + 설정

**Files:** Modify `src/main/resources/application.yml`

- [ ] **Step 1: 브랜치 + 최신 shared**

```powershell
cd devpath-ai-svc
git switch develop
git pull
git switch -c feat/slice7-mentor-pipeline
.\gradlew.bat --refresh-dependencies compileJava
```

Expected: 최신 shared(빌드 A `ai_mentor_sessions` 포함) 수신, 컴파일 성공.

- [ ] **Step 2: application.yml에 mentor/learning 블록 추가**

`devpath:` 아래(기존 `review:` 블록 다음)에 추가:

```yaml
  mentor:
    provider: ${MENTOR_PROVIDER:mock}
    claude-model: ${MENTOR_CLAUDE_MODEL:claude-sonnet-4-6}
    ollama-model: ${MENTOR_OLLAMA_MODEL:qwen2.5:7b}
    enabled: ${MENTOR_ENABLED:true}
    timeout: ${MENTOR_TIMEOUT:PT60S}
  learning:
    base-url: ${LEARNING_URI:http://localhost:8081}
    timeout: ${LEARNING_TIMEOUT:PT5S}
```

> `learning.base-url` 포트는 실측 — learning-svc 컨테이너 포트(기본 8080, 로컬 매핑은 환경별). 게이트웨이 미경유 내부 호출이라 직접 URI. gitops/compose의 실제 매핑을 확인해 기본값 조정(추측 금지, 미확인 시 `LEARNING_URI` env로 주입 전제).

- [ ] **Step 3: 컴파일 + 커밋**

```powershell
.\gradlew.bat compileJava
git add src/main/resources/application.yml
git commit -m "chore(ai-svc): add devpath.mentor/learning config (slice7 D1)"
```

---

## Task 1: AiMentorSession 엔티티 + Repository

**Files:** Create `mentor/AiMentorSession.java`, `mentor/AiMentorSessionRepository.java`

**Interfaces:**
- Produces: `AiMentorSession`(`@Table("ai_mentor_sessions")`, JSONB `contextSnapshot`/`referenceLinks` as String). `AiMentorSessionRepository extends JpaRepository<AiMentorSession, Long>`.

- [ ] **Step 1: 엔티티 작성**(AiCodeReview JSONB/@PrePersist 패턴 미러)

`src/main/java/ai/devpath/aigw/mentor/AiMentorSession.java`:

```java
package ai.devpath.aigw.mentor;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "ai_mentor_sessions")
public class AiMentorSession {

  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
  @Column(name = "user_id", nullable = false) private Long userId;
  @Column(name = "content_id") private Long contentId;
  @Column(nullable = false) private String question;
  @Column(nullable = false) private String answer = "";
  @JdbcTypeCode(SqlTypes.JSON)
  @Column(name = "context_snapshot", nullable = false) private String contextSnapshot = "{}";
  @JdbcTypeCode(SqlTypes.JSON)
  @Column(name = "reference_links", nullable = false) private String referenceLinks = "[]";
  private String provider;
  @Column(nullable = false) private String status;
  @Column(name = "error_code") private String errorCode;
  @Column(name = "created_at", nullable = false) private Instant createdAt;
  @Column(name = "updated_at", nullable = false) private Instant updatedAt;

  @PrePersist
  void prePersist() {
    Instant now = Instant.now();
    if (createdAt == null) createdAt = now;
    if (updatedAt == null) updatedAt = now;
  }

  @PreUpdate
  void preUpdate() { updatedAt = Instant.now(); }

  public Long getId() { return id; }
  public Long getUserId() { return userId; }
  public void setUserId(Long v) { this.userId = v; }
  public Long getContentId() { return contentId; }
  public void setContentId(Long v) { this.contentId = v; }
  public String getQuestion() { return question; }
  public void setQuestion(String v) { this.question = v; }
  public String getAnswer() { return answer; }
  public void setAnswer(String v) { this.answer = v; }
  public String getContextSnapshot() { return contextSnapshot; }
  public void setContextSnapshot(String v) { this.contextSnapshot = v; }
  public String getReferenceLinks() { return referenceLinks; }
  public void setReferenceLinks(String v) { this.referenceLinks = v; }
  public String getProvider() { return provider; }
  public void setProvider(String v) { this.provider = v; }
  public String getStatus() { return status; }
  public void setStatus(String v) { this.status = v; }
  public String getErrorCode() { return errorCode; }
  public void setErrorCode(String v) { this.errorCode = v; }
  public Instant getCreatedAt() { return createdAt; }
  public Instant getUpdatedAt() { return updatedAt; }
}
```

`src/main/java/ai/devpath/aigw/mentor/AiMentorSessionRepository.java`:

```java
package ai.devpath.aigw.mentor;

import org.springframework.data.jpa.repository.JpaRepository;

public interface AiMentorSessionRepository extends JpaRepository<AiMentorSession, Long> {
}
```

- [ ] **Step 2: 컴파일 확인 + 커밋**

```powershell
.\gradlew.bat compileJava
git add src/main/java/ai/devpath/aigw/mentor/AiMentorSession.java src/main/java/ai/devpath/aigw/mentor/AiMentorSessionRepository.java
git commit -m "feat(ai-svc): AiMentorSession entity + repository (slice7 D1)"
```

> 엔티티 단독 단위테스트는 생략(JSONB 매핑·영속은 Task 2 `MentorPersistenceServiceTest`가 fresh DB로 실증). `ddl-auto: validate`라 스키마(빌드 A)와 매핑 불일치 시 컨텍스트 기동 실패로 드러남.

---

## Task 2: MentorPersistenceService (DONE/FAILED 1행 영속)

**Files:** Create `mentor/MentorPersistenceService.java`; Test `mentor/MentorPersistenceServiceTest.java`

**Interfaces:**
- Produces: `long saveDone(long userId, String question, Long contentId, String answer, String contextSnapshotJson, String referenceLinksJson, String provider)` → 저장된 id. `long saveFailed(long userId, String question, Long contentId, String contextSnapshotJson, String errorCode)` → id. 둘 다 `@Transactional`(짧은 tx).

- [ ] **Step 1: 실패 테스트(fresh DB)**

`src/test/java/ai/devpath/aigw/mentor/MentorPersistenceServiceTest.java`:

```java
package ai.devpath.aigw.mentor;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class MentorPersistenceServiceTest {

  @Autowired MentorPersistenceService persistence;
  @Autowired AiMentorSessionRepository repo;

  @Test
  void saveDonePersistsAnswerContextAndReferences() {
    long id = persistence.saveDone(42L, "비동기란?", 7L, "비동기는 Future로 다룹니다.",
        "{\"track\":\"BACKEND_SPRING\"}", "[{\"contentId\":1,\"slug\":\"a\",\"title\":\"t\"}]", "MOCK");

    AiMentorSession s = repo.findById(id).orElseThrow();
    assertThat(s.getStatus()).isEqualTo("DONE");
    assertThat(s.getUserId()).isEqualTo(42L);
    assertThat(s.getContentId()).isEqualTo(7L);
    assertThat(s.getQuestion()).isEqualTo("비동기란?");
    assertThat(s.getAnswer()).isEqualTo("비동기는 Future로 다룹니다.");
    assertThat(s.getProvider()).isEqualTo("MOCK");
    assertThat(s.getContextSnapshot()).contains("BACKEND_SPRING");
    assertThat(s.getReferenceLinks()).contains("slug");
  }

  @Test
  void saveFailedPersistsErrorCodeAndEmptyAnswer() {
    long id = persistence.saveFailed(42L, "q", null, "{}", "LLM_FAILED");

    AiMentorSession s = repo.findById(id).orElseThrow();
    assertThat(s.getStatus()).isEqualTo("FAILED");
    assertThat(s.getErrorCode()).isEqualTo("LLM_FAILED");
    assertThat(s.getAnswer()).isEmpty();
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.aigw.mentor.MentorPersistenceServiceTest"
```

Expected: 컴파일 실패(`MentorPersistenceService` 없음) → FAIL.

- [ ] **Step 3: 구현**

`src/main/java/ai/devpath/aigw/mentor/MentorPersistenceService.java`:

```java
package ai.devpath.aigw.mentor;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** 멘토 세션 영속을 짧은 @Transactional로 분리(LLM 스트림은 MentorService에서 tx 밖). M-6: 완료 후 1행. */
@Service
public class MentorPersistenceService {

  private final AiMentorSessionRepository repo;

  public MentorPersistenceService(AiMentorSessionRepository repo) {
    this.repo = repo;
  }

  @Transactional
  public long saveDone(long userId, String question, Long contentId, String answer,
      String contextSnapshotJson, String referenceLinksJson, String provider) {
    AiMentorSession s = new AiMentorSession();
    s.setUserId(userId);
    s.setQuestion(question);
    s.setContentId(contentId);
    s.setAnswer(answer == null ? "" : answer);
    s.setContextSnapshot(contextSnapshotJson == null ? "{}" : contextSnapshotJson);
    s.setReferenceLinks(referenceLinksJson == null ? "[]" : referenceLinksJson);
    s.setProvider(provider);
    s.setStatus("DONE");
    return repo.save(s).getId();
  }

  @Transactional
  public long saveFailed(long userId, String question, Long contentId,
      String contextSnapshotJson, String errorCode) {
    AiMentorSession s = new AiMentorSession();
    s.setUserId(userId);
    s.setQuestion(question);
    s.setContentId(contentId);
    s.setContextSnapshot(contextSnapshotJson == null ? "{}" : contextSnapshotJson);
    s.setStatus("FAILED");
    s.setErrorCode(errorCode);
    return repo.save(s).getId();
  }
}
```

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.aigw.mentor.MentorPersistenceServiceTest"
git add src/main/java/ai/devpath/aigw/mentor/MentorPersistenceService.java src/test/java/ai/devpath/aigw/mentor/MentorPersistenceServiceTest.java
git commit -m "feat(ai-svc): MentorPersistenceService done/failed single-row persist (slice7 D1)"
```

---

## Task 3: LearningClient (내부 콘텐츠 조회 + 유사검색)

**Files:** Create `mentor/LearningClient.java`, `mentor/InternalContentView.java`, `mentor/SimilarQuery.java`, `mentor/SimilarContent.java`, `mentor/LearningUnavailableException.java`; Test `mentor/LearningClientTest.java`(MockWebServer)

**Interfaces:**
- Produces: `LearningClient.getContent(long id)` → `Optional<InternalContentView>`(404→empty). `searchSimilar(List<Double> embedding, int limit, String track)` → `List<SimilarContent>`(실패→빈 리스트, 토큰 스트림 무관 진행). `InternalContentView(long id, String slug, String title, String track, String body)`, `SimilarContent(long contentId, String slug, String title)`, `SimilarQuery(List<Double> embedding, Integer limit, String track)`.
- Consumes(빌드 C): `GET /internal/contents/{id}`, `POST /internal/contents/similar`.

- [ ] **Step 1: 실패 테스트(MockWebServer)**

`src/test/java/ai/devpath/aigw/mentor/LearningClientTest.java`:

```java
package ai.devpath.aigw.mentor;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Duration;
import java.util.Collections;
import java.util.List;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

class LearningClientTest {

  private MockWebServer server;
  private LearningClient client;

  @BeforeEach
  void setUp() throws Exception {
    server = new MockWebServer();
    server.start();
    client = new LearningClient(server.url("/").toString(), Duration.ofSeconds(5),
        JsonMapper.builder().build());
  }

  @AfterEach
  void tearDown() throws Exception { server.shutdown(); }

  @Test
  void getContentParsesView() {
    server.enqueue(new MockResponse().setHeader("Content-Type", "application/json")
        .setBody("{\"id\":7,\"slug\":\"async\",\"title\":\"비동기\",\"track\":\"BACKEND_SPRING\",\"body\":\"본문\"}"));

    InternalContentView v = client.getContent(7).orElseThrow();

    assertThat(v.id()).isEqualTo(7);
    assertThat(v.track()).isEqualTo("BACKEND_SPRING");
    assertThat(v.body()).isEqualTo("본문");
  }

  @Test
  void getContentReturnsEmptyOn404() {
    server.enqueue(new MockResponse().setResponseCode(404));
    assertThat(client.getContent(999)).isEmpty();
  }

  @Test
  void searchSimilarParsesList() {
    server.enqueue(new MockResponse().setHeader("Content-Type", "application/json")
        .setBody("[{\"contentId\":1,\"slug\":\"a\",\"title\":\"t1\"},"
            + "{\"contentId\":2,\"slug\":\"b\",\"title\":\"t2\"}]"));

    List<SimilarContent> refs = client.searchSimilar(Collections.nCopies(768, 0.1), 3, "BACKEND_SPRING");

    assertThat(refs).hasSize(2);
    assertThat(refs.get(0).slug()).isEqualTo("a");
  }

  @Test
  void searchSimilarReturnsEmptyOnError() {
    server.enqueue(new MockResponse().setResponseCode(500));
    assertThat(client.searchSimilar(Collections.nCopies(768, 0.1), 3, null)).isEmpty();
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.mentor.LearningClientTest"
```

Expected: 컴파일 실패 → FAIL.

- [ ] **Step 3: 구현**(records + client; SandboxClient의 RestClient 패턴 미러)

`InternalContentView.java`:
```java
package ai.devpath.aigw.mentor;

public record InternalContentView(long id, String slug, String title, String track, String body) {}
```

`SimilarContent.java`:
```java
package ai.devpath.aigw.mentor;

public record SimilarContent(long contentId, String slug, String title) {}
```

`SimilarQuery.java`:
```java
package ai.devpath.aigw.mentor;

import java.util.List;

public record SimilarQuery(List<Double> embedding, Integer limit, String track) {}
```

`LearningUnavailableException.java`:
```java
package ai.devpath.aigw.mentor;

public class LearningUnavailableException extends RuntimeException {
  public LearningUnavailableException(String message, Throwable cause) { super(message, cause); }
}
```

`LearningClient.java`:
```java
package ai.devpath.aigw.mentor;

import java.time.Duration;
import java.util.List;
import java.util.Optional;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import tools.jackson.databind.json.JsonMapper;

/** learning-svc 내부 조회(게이트웨이 미경유, 빌드 C). 콘텐츠 본문 + 임베딩 유사검색. */
@Component
public class LearningClient {

  private final RestClient restClient;
  private final JsonMapper jsonMapper;

  public LearningClient(
      @Value("${devpath.learning.base-url:http://localhost:8081}") String baseUrl,
      @Value("${devpath.learning.timeout:PT5S}") Duration timeout,
      JsonMapper jsonMapper) {
    var factory = new SimpleClientHttpRequestFactory();
    factory.setConnectTimeout(timeout);
    factory.setReadTimeout(timeout);
    this.restClient = RestClient.builder().baseUrl(baseUrl).requestFactory(factory).build();
    this.jsonMapper = jsonMapper;
  }

  /** 현재 콘텐츠 조회. 미존재(404)면 empty(맥락 결손 허용). 그 외 오류는 empty로 폴백(답변은 계속). */
  public Optional<InternalContentView> getContent(long id) {
    try {
      InternalContentView view = restClient.get()
          .uri("/internal/contents/{id}", id)
          .retrieve()
          .onStatus(HttpStatusCode::isError, (req, res) -> { /* swallow → null */ })
          .body(InternalContentView.class);
      return Optional.ofNullable(view);
    } catch (RestClientException e) {
      return Optional.empty();
    }
  }

  /** 질문 임베딩으로 유사 콘텐츠 top-K. 실패는 빈 리스트(references 생략, 토큰 스트림 무관). */
  public List<SimilarContent> searchSimilar(List<Double> embedding, int limit, String track) {
    try {
      SimilarContent[] arr = restClient.post()
          .uri("/internal/contents/similar")
          .contentType(MediaType.APPLICATION_JSON)
          .body(new SimilarQuery(embedding, limit, track))
          .retrieve()
          .body(SimilarContent[].class);
      return arr == null ? List.of() : List.of(arr);
    } catch (RestClientException e) {
      return List.of();
    }
  }
}
```

> ⚠️ 구현 시 `RestClient`의 `onStatus` 스왈로 패턴이 Boot 4.0.7에서 null 바디를 주는지 실측. 미흡하면 `try/catch(RestClientResponseException)`로 404→empty 분기(추측 금지). `jsonMapper`는 향후 커스텀 파싱 대비 주입(현재 `body(Class)`가 내부 변환).

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.mentor.LearningClientTest"
git add src/main/java/ai/devpath/aigw/mentor/LearningClient.java src/main/java/ai/devpath/aigw/mentor/InternalContentView.java src/main/java/ai/devpath/aigw/mentor/SimilarContent.java src/main/java/ai/devpath/aigw/mentor/SimilarQuery.java src/main/java/ai/devpath/aigw/mentor/LearningUnavailableException.java src/test/java/ai/devpath/aigw/mentor/LearningClientTest.java
git commit -m "feat(ai-svc): LearningClient internal content/similar for mentor context (slice7 D1)"
```

---

## Task 4: SandboxClient.recentByUser (기존 클라이언트 확장)

**Files:** Modify `review/SandboxClient.java`; Test `review/SandboxClientRecentTest.java`

**Interfaces:**
- Produces: `List<SandboxSessionView> SandboxClient.recentByUser(long userId, int limit)` — `GET /internal/sandbox/sessions/recent?userId&limit` → 배열. 실패는 빈 리스트(맥락 결손 허용).
- Consumes(빌드 B): `SandboxSessionView`(기존 record `review/SandboxSessionView.java` 재사용).

- [ ] **Step 1: 실패 테스트(MockWebServer)**

`src/test/java/ai/devpath/aigw/review/SandboxClientRecentTest.java`:

```java
package ai.devpath.aigw.review;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Duration;
import java.util.List;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class SandboxClientRecentTest {

  private MockWebServer server;
  private SandboxClient client;

  @BeforeEach
  void setUp() throws Exception {
    server = new MockWebServer();
    server.start();
    client = new SandboxClient(server.url("/").toString(), Duration.ofSeconds(5));
  }

  @AfterEach
  void tearDown() throws Exception { server.shutdown(); }

  @Test
  void recentByUserParsesSessionList() {
    server.enqueue(new MockResponse().setHeader("Content-Type", "application/json")
        .setBody("[{\"id\":2,\"userId\":42,\"language\":\"PYTHON\",\"contentId\":null,"
            + "\"submittedCode\":\"print(2)\",\"stdout\":\"2\",\"stderr\":\"\",\"exitCode\":0,"
            + "\"status\":\"COMPLETED\"}]"));

    List<SandboxSessionView> recent = client.recentByUser(42L, 5);

    assertThat(recent).hasSize(1);
    assertThat(recent.get(0).submittedCode()).isEqualTo("print(2)");
  }

  @Test
  void recentByUserReturnsEmptyOnError() {
    server.enqueue(new MockResponse().setResponseCode(500));
    assertThat(client.recentByUser(42L, 5)).isEmpty();
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.review.SandboxClientRecentTest"
```

Expected: 컴파일 실패(`recentByUser` 없음) → FAIL.

- [ ] **Step 3: SandboxClient에 메서드 추가**(기존 `getSession` 보존, import 추가)

`review/SandboxClient.java`에 import `java.util.List`·`org.springframework.web.client.RestClientException`(기존)·`java.util.Collections` 보강 후, `getSession` 메서드 **아래**에 추가:

```java
  /** 사용자별 최근 N개 실행(빌드 B). 멘토 context_snapshot용. 실패는 빈 리스트(맥락 결손 허용). */
  public java.util.List<SandboxSessionView> recentByUser(long userId, int limit) {
    try {
      SandboxSessionView[] arr = restClient.get()
          .uri(uriBuilder -> uriBuilder.path("/internal/sandbox/sessions/recent")
              .queryParam("userId", userId)
              .queryParam("limit", limit)
              .build())
          .retrieve()
          .body(SandboxSessionView[].class);
      return arr == null ? java.util.List.of() : java.util.List.of(arr);
    } catch (RestClientException e) {
      return java.util.List.of();
    }
  }
```

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.review.SandboxClientRecentTest"
git add src/main/java/ai/devpath/aigw/review/SandboxClient.java src/test/java/ai/devpath/aigw/review/SandboxClientRecentTest.java
git commit -m "feat(ai-svc): SandboxClient.recentByUser for mentor context (slice7 D1)"
```

---

## Task 5: MentorContextAssembler (context_snapshot 조립)

**Files:** Create `mentor/MentorContext.java`, `mentor/MentorContextAssembler.java`; Test `mentor/MentorContextAssemblerTest.java`

**Interfaces:**
- Produces: `MentorContext{String promptText, String snapshotJson, String track}` — `promptText`=LLM 프롬프트용 맥락 텍스트(콘텐츠+sandbox), `snapshotJson`=영속용 요약 JSON, `track`=현재 콘텐츠 track(참고자료 검색용, 없으면 null). `MentorContextAssembler.assemble(long userId, Long contentId)`.
- Consumes: `SandboxClient.recentByUser`(Task4), `LearningClient.getContent`(Task3), `JsonMapper`.

- [ ] **Step 1: 실패 테스트**

`src/test/java/ai/devpath/aigw/mentor/MentorContextAssemblerTest.java`:

```java
package ai.devpath.aigw.mentor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import ai.devpath.aigw.review.SandboxClient;
import ai.devpath.aigw.review.SandboxSessionView;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import tools.jackson.databind.json.JsonMapper;

@ExtendWith(MockitoExtension.class)
class MentorContextAssemblerTest {

  @Mock SandboxClient sandboxClient;
  @Mock LearningClient learningClient;

  private MentorContextAssembler assembler() {
    return new MentorContextAssembler(sandboxClient, learningClient, JsonMapper.builder().build());
  }

  @Test
  void assemblesContentAndSandboxIntoContext() {
    when(learningClient.getContent(7L)).thenReturn(Optional.of(
        new InternalContentView(7, "async", "비동기 기초", "BACKEND_SPRING", "콘텐츠 본문")));
    when(sandboxClient.recentByUser(42L, 5)).thenReturn(List.of(
        new SandboxSessionView(2L, 42L, "PYTHON", 7L, "print(2)", "2", "", 0, "COMPLETED")));

    MentorContext ctx = assembler().assemble(42L, 7L);

    assertThat(ctx.track()).isEqualTo("BACKEND_SPRING");
    assertThat(ctx.promptText()).contains("비동기 기초").contains("print(2)");
    assertThat(ctx.snapshotJson()).contains("BACKEND_SPRING");
  }

  @Test
  void worksWithoutContentId() {
    when(sandboxClient.recentByUser(42L, 5)).thenReturn(List.of());

    MentorContext ctx = assembler().assemble(42L, null);

    assertThat(ctx.track()).isNull();
    assertThat(ctx.promptText()).isNotNull();
    // contentId 없으면 learningClient.getContent 미호출
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.mentor.MentorContextAssemblerTest"
```

Expected: 컴파일 실패 → FAIL.

- [ ] **Step 3: 구현**

`MentorContext.java`:
```java
package ai.devpath.aigw.mentor;

/** 멘토 맥락: promptText=LLM 주입용, snapshotJson=영속용 요약, track=참고자료 검색용(없으면 null). */
public record MentorContext(String promptText, String snapshotJson, String track) {}
```

`MentorContextAssembler.java`:
```java
package ai.devpath.aigw.mentor;

import ai.devpath.aigw.review.SandboxClient;
import ai.devpath.aigw.review.SandboxSessionView;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

/** context_snapshot 조립(M-3): 현재 콘텐츠(옵셔널) + 최근 5 Sandbox. 결손 허용(클라이언트가 빈값 폴백). */
@Component
public class MentorContextAssembler {

  private static final int RECENT_LIMIT = 5;
  private static final int MAX_CODE_CHARS = 1500;
  private static final int MAX_BODY_CHARS = 2000;

  private final SandboxClient sandboxClient;
  private final LearningClient learningClient;
  private final JsonMapper jsonMapper;

  public MentorContextAssembler(SandboxClient sandboxClient, LearningClient learningClient,
      JsonMapper jsonMapper) {
    this.sandboxClient = sandboxClient;
    this.learningClient = learningClient;
    this.jsonMapper = jsonMapper;
  }

  public MentorContext assemble(long userId, Long contentId) {
    Optional<InternalContentView> content = contentId == null
        ? Optional.empty()
        : learningClient.getContent(contentId);
    List<SandboxSessionView> recent = sandboxClient.recentByUser(userId, RECENT_LIMIT);

    StringBuilder prompt = new StringBuilder();
    Map<String, Object> snapshot = new LinkedHashMap<>();

    content.ifPresent(c -> {
      prompt.append("현재 학습 콘텐츠: ").append(c.title())
          .append(" (track: ").append(c.track()).append(")\n")
          .append(truncate(c.body(), MAX_BODY_CHARS)).append("\n\n");
      snapshot.put("track", c.track());
      snapshot.put("contentTitle", c.title());
      snapshot.put("contentId", c.id());
    });

    if (!recent.isEmpty()) {
      prompt.append("최근 코드 실행:\n");
      for (SandboxSessionView s : recent) {
        prompt.append("- [").append(s.language()).append(", ").append(s.status()).append("] ")
            .append(truncate(s.submittedCode(), MAX_CODE_CHARS))
            .append(" => exit ").append(s.exitCode()).append("\n");
      }
      snapshot.put("recentRuns", recent.size());
    }

    return new MentorContext(
        prompt.toString(),
        toJson(snapshot),
        content.map(InternalContentView::track).orElse(null));
  }

  private String truncate(String s, int max) {
    if (s == null) return "";
    return s.length() <= max ? s : s.substring(0, max) + "…";
  }

  private String toJson(Map<String, Object> snapshot) {
    try {
      return jsonMapper.writeValueAsString(snapshot);
    } catch (Exception e) {
      return "{}";
    }
  }
}
```

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.mentor.MentorContextAssemblerTest"
git add src/main/java/ai/devpath/aigw/mentor/MentorContext.java src/main/java/ai/devpath/aigw/mentor/MentorContextAssembler.java src/test/java/ai/devpath/aigw/mentor/MentorContextAssemblerTest.java
git commit -m "feat(ai-svc): MentorContextAssembler builds context_snapshot from content+sandbox (slice7 D1)"
```

---

## Task 6: AiMentorClient 인터페이스 + MockMentorClient + MentorInput

**Files:** Create `mentor/AiMentorClient.java`, `mentor/MentorInput.java`, `mentor/MockMentorClient.java`; Test `mentor/MockMentorClientTest.java`

**Interfaces:**
- Produces: `interface AiMentorClient { void stream(MentorInput input, java.util.function.Consumer<String> tokenSink); String providerName(); }`. `MentorInput(String question, String contextText)`. `MockMentorClient implements AiMentorClient`, `@ConditionalOnProperty(devpath.mentor.provider=mock, matchIfMissing=true)`, `providerName()`="MOCK". 실 provider(Claude/Ollama)는 D2.

- [ ] **Step 1: 실패 테스트**

`src/test/java/ai/devpath/aigw/mentor/MockMentorClientTest.java`:

```java
package ai.devpath.aigw.mentor;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class MockMentorClientTest {

  @Test
  void streamsTokensAndReportsProvider() {
    MockMentorClient client = new MockMentorClient();
    List<String> tokens = new ArrayList<>();

    client.stream(new MentorInput("비동기란?", "ctx"), tokens::add);

    assertThat(client.providerName()).isEqualTo("MOCK");
    assertThat(tokens).isNotEmpty();
    assertThat(String.join("", tokens)).isNotBlank();
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.mentor.MockMentorClientTest"
```

Expected: 컴파일 실패 → FAIL.

- [ ] **Step 3: 구현**

`AiMentorClient.java`:
```java
package ai.devpath.aigw.mentor;

import java.util.function.Consumer;

/** 멘토 LLM 스트리밍 추상화. 토큰을 tokenSink로 push, 완료 시 반환, 실패 시 RuntimeException. */
public interface AiMentorClient {
  void stream(MentorInput input, Consumer<String> tokenSink);
  String providerName();
}
```

`MentorInput.java`:
```java
package ai.devpath.aigw.mentor;

public record MentorInput(String question, String contextText) {}
```

`MockMentorClient.java`:
```java
package ai.devpath.aigw.mentor;

import java.util.List;
import java.util.function.Consumer;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/** CI/dev 기본 멘토(외부 LLM 없음). 고정 답변을 토큰 분할 방출. */
@Component
@ConditionalOnProperty(name = "devpath.mentor.provider", havingValue = "mock", matchIfMissing = true)
public class MockMentorClient implements AiMentorClient {

  private static final List<String> TOKENS = List.of(
      "그 질문", "에 답하면, ", "비동기는 ", "Future/async/await", "로 다룹니다.");

  @Override
  public void stream(MentorInput input, Consumer<String> tokenSink) {
    for (String t : TOKENS) {
      tokenSink.accept(t);
    }
  }

  @Override
  public String providerName() { return "MOCK"; }
}
```

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.mentor.MockMentorClientTest"
git add src/main/java/ai/devpath/aigw/mentor/AiMentorClient.java src/main/java/ai/devpath/aigw/mentor/MentorInput.java src/main/java/ai/devpath/aigw/mentor/MockMentorClient.java src/test/java/ai/devpath/aigw/mentor/MockMentorClientTest.java
git commit -m "feat(ai-svc): AiMentorClient interface + MockMentorClient streaming (slice7 D1)"
```

---

## Task 7: MentorReferenceService (질문 임베딩 → 유사검색)

**Files:** Create `mentor/MentorReferenceService.java`; Test `mentor/MentorReferenceServiceTest.java`

**Interfaces:**
- Produces: `List<SimilarContent> MentorReferenceService.find(String question, String track)` — `OllamaClient.embed([question])` → 768 → `LearningClient.searchSimilar(vec, 3, track)`. 임베딩/검색 실패는 빈 리스트(references 생략, M-2 독립).
- Consumes: `OllamaClient`(기존 `ollama/`), `LearningClient`(Task3).

- [ ] **Step 1: 실패 테스트**

`src/test/java/ai/devpath/aigw/mentor/MentorReferenceServiceTest.java`:

```java
package ai.devpath.aigw.mentor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

import ai.devpath.aigw.ollama.OllamaClient;
import ai.devpath.aigw.ollama.dto.EmbedResponse;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class MentorReferenceServiceTest {

  @Mock OllamaClient ollamaClient;
  @Mock LearningClient learningClient;

  @Test
  void embedsQuestionAndSearchesSimilar() {
    when(ollamaClient.embed(List.of("비동기란?")))
        .thenReturn(new EmbedResponse(List.of(Collections.nCopies(768, 0.1))));
    when(learningClient.searchSimilar(any(), eq(3), eq("BACKEND_SPRING")))
        .thenReturn(List.of(new SimilarContent(1, "a", "t")));

    var svc = new MentorReferenceService(ollamaClient, learningClient);
    List<SimilarContent> refs = svc.find("비동기란?", "BACKEND_SPRING");

    assertThat(refs).hasSize(1);
    assertThat(refs.get(0).slug()).isEqualTo("a");
  }

  @Test
  void returnsEmptyWhenEmbedFails() {
    when(ollamaClient.embed(any())).thenThrow(new RuntimeException("ollama down"));

    var svc = new MentorReferenceService(ollamaClient, learningClient);
    assertThat(svc.find("q", null)).isEmpty();
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.mentor.MentorReferenceServiceTest"
```

Expected: 컴파일 실패 → FAIL.

- [ ] **Step 3: 구현**

`MentorReferenceService.java`:
```java
package ai.devpath.aigw.mentor;

import ai.devpath.aigw.ollama.OllamaClient;
import java.util.List;
import org.springframework.stereotype.Service;

/** 참고자료(M-4): 질문 임베딩(ai-svc 자체 Ollama embed) → learning 유사검색. 실패는 빈 리스트(M-2 독립). */
@Service
public class MentorReferenceService {

  private static final int TOP_K = 3;

  private final OllamaClient ollamaClient;
  private final LearningClient learningClient;

  public MentorReferenceService(OllamaClient ollamaClient, LearningClient learningClient) {
    this.ollamaClient = ollamaClient;
    this.learningClient = learningClient;
  }

  public List<SimilarContent> find(String question, String track) {
    try {
      List<Double> embedding = ollamaClient.embed(List.of(question)).embeddings().get(0);
      return learningClient.searchSimilar(embedding, TOP_K, track);
    } catch (RuntimeException e) {
      return List.of(); // 임베딩/검색 실패 → references 생략, 토큰 스트림은 무관 진행
    }
  }
}
```

> `OllamaClient.embed(List<String>)`→`EmbedResponse(List<List<Double>> embeddings)`는 실측(768 검증 내장). `embeddings().get(0)`이 질문 1건의 벡터.

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.mentor.MentorReferenceServiceTest"
git add src/main/java/ai/devpath/aigw/mentor/MentorReferenceService.java src/test/java/ai/devpath/aigw/mentor/MentorReferenceServiceTest.java
git commit -m "feat(ai-svc): MentorReferenceService question-embed + similar search (slice7 D1)"
```

---

## Task 8: MentorService 오케스트레이션 + 전용 Executor

**Files:** Create `mentor/MentorService.java`, `mentor/MentorExecutorConfig.java`; Test `mentor/MentorServiceTest.java`

**Interfaces:**
- Produces: `MentorService.streamAnswer(long userId, String question, Long contentId, org.springframework.web.servlet.mvc.method.annotation.SseEmitter emitter)` — 전용 스레드에서: context 조립 → `event:references` 방출 → `AiMentorClient.stream`(각 토큰 `event:token`) → 완료 시 DONE 영속 + `emitter.complete()`, 실패 시 FAILED 영속 + `emitter.completeWithError()`. `IOException`(클라이언트 끊김)도 FAILED 처리.
- Consumes: `MentorContextAssembler`·`MentorReferenceService`·`AiMentorClient`·`MentorPersistenceService`·`JsonMapper`.

- [ ] **Step 1: 실패 테스트**(Mockito로 토큰/references 방출·영속 검증)

`src/test/java/ai/devpath/aigw/mentor/MentorServiceTest.java`:

```java
package ai.devpath.aigw.mentor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.function.Consumer;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import tools.jackson.databind.json.JsonMapper;

@ExtendWith(MockitoExtension.class)
class MentorServiceTest {

  @Mock MentorContextAssembler contextAssembler;
  @Mock MentorReferenceService referenceService;
  @Mock AiMentorClient mentorClient;
  @Mock MentorPersistenceService persistence;

  private MentorService service() {
    return new MentorService(contextAssembler, referenceService, mentorClient, persistence,
        JsonMapper.builder().build());
  }

  @Test
  void streamsReferencesThenTokensThenPersistsDone() throws Exception {
    when(contextAssembler.assemble(42L, 7L))
        .thenReturn(new MentorContext("ctx", "{\"track\":\"BACKEND_SPRING\"}", "BACKEND_SPRING"));
    when(referenceService.find("비동기란?", "BACKEND_SPRING"))
        .thenReturn(List.of(new SimilarContent(1, "a", "t")));
    when(mentorClient.providerName()).thenReturn("MOCK");
    doAnswer(inv -> {
      Consumer<String> sink = inv.getArgument(1);
      sink.accept("비동기는 ");
      sink.accept("Future입니다.");
      return null;
    }).when(mentorClient).stream(any(), any());

    RecordingEmitter emitter = new RecordingEmitter();
    service().streamAnswer(42L, "비동기란?", 7L, emitter);

    assertThat(emitter.events).anyMatch(e -> e.contains("references"));
    assertThat(emitter.events).anyMatch(e -> e.contains("token"));
    verify(persistence).saveDone(eq(42L), eq("비동기란?"), eq(7L),
        eq("비동기는 Future입니다."), anyString(), anyString(), eq("MOCK"));
    assertThat(emitter.completed).isTrue();
  }

  @Test
  void persistsFailedAndCompletesWithErrorOnLlmFailure() throws Exception {
    when(contextAssembler.assemble(42L, null))
        .thenReturn(new MentorContext("ctx", "{}", null));
    when(referenceService.find(anyString(), isNull())).thenReturn(List.of());
    doAnswer(inv -> { throw new RuntimeException("llm down"); })
        .when(mentorClient).stream(any(), any());

    RecordingEmitter emitter = new RecordingEmitter();
    service().streamAnswer(42L, "q", null, emitter);

    verify(persistence).saveFailed(eq(42L), eq("q"), isNull(), anyString(), anyString());
    assertThat(emitter.error).isNotNull();
  }

  /** SseEmitter 더블: send된 이벤트 문자열과 complete/error를 기록. */
  static final class RecordingEmitter extends SseEmitter {
    final java.util.List<String> events = new java.util.ArrayList<>();
    boolean completed;
    Throwable error;
    @Override public void send(SseEventBuilder builder) {
      builder.build().forEach(d -> events.add(String.valueOf(d.getData())));
    }
    @Override public void complete() { completed = true; }
    @Override public void completeWithError(Throwable ex) { error = ex; }
  }
}
```

> ⚠️ 구현 시 `SseEmitter.SseEventBuilder.build()`의 반환 타입(Set<ResponseBodyEmitter.DataWithMediaType>)과 `getData()` 시그니처를 Boot 4.0.7로 실측해 `RecordingEmitter`를 맞춘다(추측 금지). 더블이 어려우면 Mockito `mock(SseEmitter.class)` + `ArgumentCaptor<SseEventBuilder>`로 대체.

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.mentor.MentorServiceTest"
```

Expected: 컴파일 실패 → FAIL.

- [ ] **Step 3: 구현**

`MentorExecutorConfig.java`:
```java
package ai.devpath.aigw.mentor;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.task.AsyncTaskExecutor;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

/** 멘토 SSE 스트림 전용 풀(공용 풀 오염 방지, M-1). 동시 세션 백프레셔. */
@Configuration
public class MentorExecutorConfig {

  @Bean(name = "mentorExecutor")
  public AsyncTaskExecutor mentorExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(4);
    executor.setMaxPoolSize(16);
    executor.setQueueCapacity(32);
    executor.setThreadNamePrefix("mentor-sse-");
    executor.initialize();
    return executor;
  }
}
```

`MentorService.java`:
```java
package ai.devpath.aigw.mentor;

import java.io.IOException;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import tools.jackson.databind.json.JsonMapper;

/** 멘토 오케스트레이션(전용 스레드, M-1/M-2): context → references → token 스트림 → 완료 영속. */
@Service
public class MentorService {

  private final MentorContextAssembler contextAssembler;
  private final MentorReferenceService referenceService;
  private final AiMentorClient mentorClient;
  private final MentorPersistenceService persistence;
  private final JsonMapper jsonMapper;

  public MentorService(MentorContextAssembler contextAssembler, MentorReferenceService referenceService,
      AiMentorClient mentorClient, MentorPersistenceService persistence, JsonMapper jsonMapper) {
    this.contextAssembler = contextAssembler;
    this.referenceService = referenceService;
    this.mentorClient = mentorClient;
    this.persistence = persistence;
    this.jsonMapper = jsonMapper;
  }

  /** 전용 executor 스레드에서 호출. 예외를 던지지 않고 emitter로 종결한다. */
  public void streamAnswer(long userId, String question, Long contentId, SseEmitter emitter) {
    MentorContext ctx = contextAssembler.assemble(userId, contentId);
    StringBuilder answer = new StringBuilder();
    try {
      List<SimilarContent> refs = referenceService.find(question, ctx.track());
      if (!refs.isEmpty()) {
        emitter.send(SseEmitter.event().name("references").data(jsonMapper.writeValueAsString(refs)));
      }
      mentorClient.stream(new MentorInput(question, ctx.promptText()), token -> {
        answer.append(token);
        try {
          emitter.send(SseEmitter.event().name("token").data(token));
        } catch (IOException io) {
          throw new MentorStreamAbortedException(io); // 클라이언트 끊김 → 스트림 중단
        }
      });
      persistence.saveDone(userId, question, contentId, answer.toString(),
          ctx.snapshotJson(), jsonMapper.writeValueAsString(refs), mentorClient.providerName());
      emitter.complete();
    } catch (MentorStreamAbortedException abort) {
      persistence.saveFailed(userId, question, contentId, ctx.snapshotJson(), "CLIENT_ABORTED");
      emitter.completeWithError(abort.getCause());
    } catch (Exception e) {
      persistence.saveFailed(userId, question, contentId, ctx.snapshotJson(), "LLM_FAILED");
      emitter.completeWithError(e);
    }
  }

  private static final class MentorStreamAbortedException extends RuntimeException {
    MentorStreamAbortedException(Throwable cause) { super(cause); }
  }
}
```

> ⚠️ 구현 시 `SseEmitter.event().name(...).data(...)`(SseEventBuilder) API를 Boot 4.0.7로 실측. `emitter.send(SseEventBuilder)`가 `IOException` 던짐을 확인(클라이언트 끊김 처리). study-documents Spring Boot 4 SSE 샘플 1급 참조.

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.mentor.MentorServiceTest"
git add src/main/java/ai/devpath/aigw/mentor/MentorService.java src/main/java/ai/devpath/aigw/mentor/MentorExecutorConfig.java src/test/java/ai/devpath/aigw/mentor/MentorServiceTest.java
git commit -m "feat(ai-svc): MentorService SSE orchestration (references+tokens+persist) (slice7 D1)"
```

---

## Task 9: MentorController (SseEmitter + kill-switch 선체크) + GlobalExceptionHandler

**Files:** Create `mentor/MentorController.java`, `mentor/MentorRequest.java`, `mentor/MentorKillSwitchException.java`; Modify `config/GlobalExceptionHandler.java`; Test `mentor/MentorControllerTest.java`

**Interfaces:**
- Produces: `POST /ai-mentor/sessions` body `MentorRequest(String message, Long contentId)` → `SseEmitter`(JWT subject userId). kill-switch(`devpath.mentor.enabled=false`) 시 `MentorKillSwitchException`→503(개시 전, M-2). 빈 message → 400.
- Consumes: `MentorService`(Task8), `mentorExecutor`(Task8).

- [ ] **Step 1: 실패 테스트**(MockMvc async, mock provider)

`src/test/java/ai/devpath/aigw/mentor/MentorControllerTest.java`:

```java
package ai.devpath.aigw.mentor;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.request;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class MentorControllerTest {

  @Autowired MockMvc mvc;

  @Test
  void streamsSseForAuthenticatedUser() throws Exception {
    MvcResult mvcResult = mvc.perform(post("/ai-mentor/sessions")
            .with(jwt().jwt(j -> j.subject("42")))
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"message\":\"비동기란?\"}"))
        .andExpect(request().asyncStarted())
        .andReturn();

    mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
            .asyncDispatch(mvcResult))
        .andExpect(status().isOk())
        .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers
            .content().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM));
  }

  @Test
  void rejectsEmptyMessage() throws Exception {
    mvc.perform(post("/ai-mentor/sessions")
            .with(jwt().jwt(j -> j.subject("42")))
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"message\":\"  \"}"))
        .andExpect(status().isBadRequest());
  }

  @Test
  void requiresAuthentication() throws Exception {
    mvc.perform(post("/ai-mentor/sessions")
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"message\":\"q\"}"))
        .andExpect(status().isUnauthorized());
  }
}
```

> kill-switch(503) 테스트는 `@TestPropertySource(properties="devpath.mentor.enabled=false")` 별도 클래스 또는 `MentorControllerKillSwitchTest`로 분리(프로퍼티 토글이 클래스 단위라). D1에서 1케이스 추가.

- [ ] **Step 2: 실패 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.aigw.mentor.MentorControllerTest"
```

Expected: 컴파일 실패 → FAIL.

- [ ] **Step 3: 구현**

`MentorRequest.java`:
```java
package ai.devpath.aigw.mentor;

public record MentorRequest(String message, Long contentId) {}
```

`MentorKillSwitchException.java`:
```java
package ai.devpath.aigw.mentor;

public class MentorKillSwitchException extends RuntimeException {
  public MentorKillSwitchException(String message) { super(message); }
}
```

`MentorController.java`:
```java
package ai.devpath.aigw.mentor;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.task.AsyncTaskExecutor;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/** AI 멘토 SSE(M-1/M-2). kill-switch 선체크(개시 전 비-200) → 전용 스레드에서 스트림. */
@RestController
@RequestMapping("/ai-mentor")
public class MentorController {

  private final MentorService mentorService;
  private final AsyncTaskExecutor mentorExecutor;
  private final boolean enabled;
  private final long timeoutMs;

  public MentorController(MentorService mentorService,
      @org.springframework.beans.factory.annotation.Qualifier("mentorExecutor") AsyncTaskExecutor mentorExecutor,
      @Value("${devpath.mentor.enabled:true}") boolean enabled,
      @Value("${devpath.mentor.timeout:PT60S}") java.time.Duration timeout) {
    this.mentorService = mentorService;
    this.mentorExecutor = mentorExecutor;
    this.enabled = enabled;
    this.timeoutMs = timeout.toMillis();
  }

  @PostMapping("/sessions")
  public SseEmitter sessions(@AuthenticationPrincipal Jwt jwt, @RequestBody MentorRequest req) {
    if (!enabled) {
      throw new MentorKillSwitchException("AI mentor is disabled"); // 개시 전 503(M-2)
    }
    if (req == null || req.message() == null || req.message().isBlank()) {
      throw new IllegalArgumentException("message must not be blank");
    }
    long userId = Long.parseLong(jwt.getSubject());
    SseEmitter emitter = new SseEmitter(timeoutMs);
    emitter.onTimeout(emitter::complete);
    mentorExecutor.execute(() ->
        mentorService.streamAnswer(userId, req.message(), req.contentId(), emitter));
    return emitter;
  }
}
```

`config/GlobalExceptionHandler.java`에 핸들러 추가(기존 핸들러 패턴 미러 — 실측 후 `@ExceptionHandler` 메서드 추가):
```java
  @org.springframework.web.bind.annotation.ExceptionHandler(MentorKillSwitchException.class)
  public org.springframework.http.ResponseEntity<?> killSwitch(MentorKillSwitchException e) {
    return org.springframework.http.ResponseEntity
        .status(org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE)
        .body(java.util.Map.of("errorCode", "AI_KILL_SWITCH_ACTIVE", "message", e.getMessage()));
  }
```

> ⚠️ `GlobalExceptionHandler`의 기존 에러 바디 형식(`errorCode` 키 등)을 실측해 일치시킨다. 프론트 `ApiErrorCode.fromWire`가 `AI_KILL_SWITCH_ACTIVE`를 `isKillSwitch`로 매핑(빌드 F 계약). `IllegalArgumentException`→400 핸들러가 이미 있으면 재사용, 없으면 추가.

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.aigw.mentor.MentorControllerTest"
git add src/main/java/ai/devpath/aigw/mentor/MentorController.java src/main/java/ai/devpath/aigw/mentor/MentorRequest.java src/main/java/ai/devpath/aigw/mentor/MentorKillSwitchException.java src/main/java/ai/devpath/aigw/config/GlobalExceptionHandler.java src/test/java/ai/devpath/aigw/mentor/MentorControllerTest.java
git commit -m "feat(ai-svc): MentorController SSE endpoint + kill-switch pre-check 503 (slice7 D1)"
```

---

## Task 10: 끝단간 IT(Mock) + kill-switch + 전체 회귀 + develop PR

**Files:** Create `mentor/MentorSseIntegrationTest.java`, `mentor/MentorKillSwitchTest.java`

- [ ] **Step 1: 끝단간 IT(Mock provider, SandboxClient/LearningClient mock)**

`src/test/java/ai/devpath/aigw/mentor/MentorSseIntegrationTest.java`: `@SpringBootTest @AutoConfigureMockMvc @ActiveProfiles("test")`로 `SandboxClient`·`LearningClient`·`OllamaClient`를 `@MockitoBean`으로 주입(외부 호출 0). `POST /ai-mentor/sessions` async dispatch 결과 본문에 `event:token`이 포함되고 `ai_mentor_sessions`에 DONE 1행이 영속되는지 단언. (구현 시 `MentorServiceTest`/`MentorControllerTest`의 패턴 결합 — async dispatch 본문 문자열에 "token"·"references" 포함, repo.count() 증가.)

```java
package ai.devpath.aigw.mentor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.request;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import ai.devpath.aigw.ollama.OllamaClient;
import ai.devpath.aigw.ollama.dto.EmbedResponse;
import ai.devpath.aigw.review.SandboxClient;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class MentorSseIntegrationTest {

  @Autowired MockMvc mvc;
  @Autowired AiMentorSessionRepository repo;
  @MockitoBean SandboxClient sandboxClient;
  @MockitoBean LearningClient learningClient;
  @MockitoBean OllamaClient ollamaClient;

  @Test
  void endToEndMockStreamsTokensAndPersistsDone() throws Exception {
    when(sandboxClient.recentByUser(42L, 5)).thenReturn(List.of());
    when(ollamaClient.embed(List.of("비동기란?")))
        .thenReturn(new EmbedResponse(List.of(Collections.nCopies(768, 0.1))));
    when(learningClient.searchSimilar(org.mockito.ArgumentMatchers.any(),
        org.mockito.ArgumentMatchers.anyInt(), org.mockito.ArgumentMatchers.any()))
        .thenReturn(List.of(new SimilarContent(1, "a", "t")));

    long before = repo.count();
    MvcResult started = mvc.perform(post("/ai-mentor/sessions")
            .with(jwt().jwt(j -> j.subject("42")))
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"message\":\"비동기란?\"}"))
        .andExpect(request().asyncStarted())
        .andReturn();

    String body = mvc.perform(asyncDispatch(started))
        .andExpect(status().isOk())
        .andReturn().getResponse().getContentAsString();

    assertThat(body).contains("token");
    assertThat(body).contains("references");
    assertThat(repo.count()).isEqualTo(before + 1);
  }
}
```

- [ ] **Step 2: kill-switch 503 테스트(프로퍼티 토글)**

`src/test/java/ai/devpath/aigw/mentor/MentorKillSwitchTest.java`:

```java
package ai.devpath.aigw.mentor;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@TestPropertySource(properties = "devpath.mentor.enabled=false")
class MentorKillSwitchTest {

  @Autowired MockMvc mvc;

  @Test
  void killSwitchReturns503BeforeStream() throws Exception {
    mvc.perform(post("/ai-mentor/sessions")
            .with(jwt().jwt(j -> j.subject("42")))
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"message\":\"q\"}"))
        .andExpect(status().isServiceUnavailable());
  }
}
```

- [ ] **Step 3: 전체 회귀(mock provider, fresh DB)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat clean test
```

Expected: 멘토 단위/IT + 기존 #6 리뷰 테스트 전부 PASS(회귀 없음). mock provider 고정(외부 LLM 0). 기존 Kafka(#6) 자동설정이 멘토 컨텍스트 기동에 무영향 확인.

- [ ] **Step 4: PR 생성(develop 대상)**

```powershell
git push -u origin feat/slice7-mentor-pipeline
gh pr create --base develop --title "feat(ai-svc): 멘토 SSE 파이프라인(Mock, context+references+persist) 슬라이스 #7 빌드 D1" --body "POST /ai-mentor/sessions SSE: kill-switch 선체크(503) → context_snapshot(sandbox recent5 + content) → event:references(임베딩 유사검색) → event:token(Mock 스트림) → DONE 영속. AiMentorClient 추상화(Mock만, 실 provider=D2). SandboxClient.recentByUser·LearningClient 내부 호출. SecurityConfig 무변경. 설계서 docs/superpowers/specs/2026-06-24-md3-slice7-ai-mentor-design.md §5·§9 빌드 D·M-1·M-2·M-6"
gh pr checks --watch
gh pr merge --merge
```

Expected: ai-svc CI(mock provider, postgres pgvector) 녹색. 빌드 D2(실 provider+인젝션+골든)는 후속 PR.

---

## Self-Review 메모(작성자)

- **Spec 커버리지(D1 범위)**: M-1(SseEmitter+전용 executor+타임아웃+IOException 취소)=Task8/9. M-2(token/references, kill-switch 개시전 503, in-band error/done 없음)=Task8/9. M-3(context: sandbox recent5 + content, 결손 허용)=Task3/4/5. M-6(완료 후 1행 영속)=Task2/8. M-7(context_snapshot JSONB)=Task1/5. M-9(SecurityConfig 무변경)=Global Constraints. 참고자료 임베딩(M-4)=Task7(질문 임베딩→learning searchSimilar). **실 provider/인젝션 방어/골든=빌드 D2(범위 외, 명시)**.
- **인터페이스 정합(빌드 B/C consume)**: `SandboxClient.recentByUser`→`GET /internal/sandbox/sessions/recent?userId&limit`(빌드 B 시그니처 일치). `LearningClient.getContent`→`GET /internal/contents/{id}`·`searchSimilar`→`POST /internal/contents/similar`(빌드 C `SimilarQuery{embedding,limit,track}`·`SimilarContent{contentId,slug,title}`·`InternalContentView{id,slug,title,track,body}` 1:1 일치). 프론트(빌드 F) consume: `POST /ai-mentor/sessions {message, contentId}`·`event:token`/`event:references`·kill-switch 503(`AI_KILL_SWITCH_ACTIVE`)·완료 close.
- **placeholder 없음**: 모든 코드/테스트/명령 실값. 단 ⚠️ **구현 시 실측 4곳 명시**(추측 금지): ① `SseEmitter.event()/send(IOException)` Boot4 API + study-documents SSE 샘플 ② `RestClient.onStatus` 404→empty 거동 ③ `GlobalExceptionHandler` 에러 바디 형식 ④ `learning.base-url` 실 포트. `RecordingEmitter` 더블의 `SseEventBuilder.build()` 시그니처도 실측.
- **타입 일관성**: `AiMentorSession`(JSONB String, AiCodeReview 패턴)·`MentorContext`·`MentorInput`·`AiMentorClient`(D2 provider가 구현)·`MentorPersistenceService.saveDone/saveFailed`가 Task 간 일치. provider 기본 mock(`matchIfMissing=true`).
- **#6 패턴 승계**: 짧은 tx 영속(ReviewPersistenceService), RestClient 내부 호출(SandboxClient), MockWebServer 단위, `@MockitoBean` IT, mock provider CI, fresh DB. 멘토 고유=SSE 스트리밍(전용 executor)·동기(Kafka 없음).
- **범위 경계(D1)**: ai-svc `mentor/` 패키지 + SandboxClient 1메서드 + application.yml/GlobalExceptionHandler. 빌드 A(shared)·B(sandbox)·C(learning)·E(gateway)·F(frontend)·D2(provider/인젝션/골든)는 별도. SecurityConfig·build.gradle 무변경.
