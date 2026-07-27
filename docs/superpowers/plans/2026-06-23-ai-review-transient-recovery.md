# AI 코드리뷰 일시 장애 복구(재시도 + DB 종료) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** LLM(Ollama/Claude)의 일시 장애(타임아웃·5xx·429)가 영구 FAILED로 고착되고 이벤트가 소실되는 갭을, 일시/영구 오류 구분 + Kafka 백오프 재시도 + 소진 시 DB 종료(LLM_EXHAUSTED) + error_code 세분화로 해소한다.

**Architecture:** 멱등 skip을 행 존재가 아니라 **상태(status)** 기준으로 전환(DONE/FAILED skip, PENDING 재시도). 일시 LLM 오류는 PENDING을 남긴 채 `TransientReviewException`을 재던져 Kafka `DefaultErrorHandler`가 지수 백오프 재시도하고, 소진 시 recoverer가 `FAILED(LLM_EXHAUSTED)`로 종료한다. 영구/터미널(파싱·ownership·sandbox)은 즉시 `finishFailed`.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Spring Kafka(DefaultErrorHandler·ExponentialBackOffWithMaxRetries) · RestClient(Ollama) · anthropic-java 2.34.0(Claude) · JUnit 5 · EmbeddedKafka · MockWebServer · Mockito.

## Global Constraints

- 대상 레포: `devpath-ai-svc` 단독. **마이그레이션 변경 없음**(`ai_code_reviews.error_code`는 VARCHAR(32) 자유문자열, CHECK 없음 — 기존 컬럼 재사용).
- **이 환경은 로컬에 GitHub Packages 인증이 없어 ai-svc를 로컬 빌드/테스트할 수 없다. 각 Task는 테스트+구현을 작성만 하고 `.\gradlew.bat`을 실행하지 말라. 검증은 push 후 CI(GITHUB_TOKEN)가 수행한다.** ("실패/통과 확인" 스텝은 CI로 대체.)
- 신규 작업 브랜치는 `develop`에서 분기, `develop`으로 PR. 비밀값(ANTHROPIC_API_KEY) 커밋 금지.
- error_code 집합: `LLM_TIMEOUT·LLM_5XX·LLM_RATELIMIT·PARSE_FAILED·OWNERSHIP_MISMATCH·SANDBOX_UNAVAILABLE·LLM_EXHAUSTED·LLM_FAILED`(예상밖 폴백).
- 백오프: `ExponentialBackOffWithMaxRetries(3)` + initialInterval 1000ms + multiplier 2.0(1s·2s·4s).
- 패키지 루트 `ai.devpath.aigw`, 리뷰 모듈 `ai.devpath.aigw.review`. 모든 `@SpringBootTest`는 `@ActiveProfiles("test")`.
- 멱등 불변식: 동일 sandbox_session_id에 리뷰 1행(UNIQUE) 유지. `duplicateEventIsIdempotent`(기존) 회귀 금지.

## File Structure

- Create: `review/TransientReviewException.java` — 재시도 대상 예외(errorCode 보유).
- Create: `review/PermanentReviewException.java` — 즉시 종료 예외(errorCode 보유).
- Create: `review/ReviewKafkaConfig.java` — DefaultErrorHandler 빈 + recoverer.
- Modify: `review/ReviewPersistenceService.java` — `createPendingIfAbsent`→`findOrCreatePending`, `markExhausted` 추가.
- Modify: `review/ReviewService.java` — 상태기준 멱등 + 분류 catch.
- Modify: `review/OllamaAiReviewClient.java` — RestClient 오류 → Transient/Permanent 매핑(내부 retry 제거).
- Modify: `review/ClaudeAiReviewClient.java` — SDK 오류 → Transient/Permanent 매핑.
- Modify(test): `review/ReviewPersistenceServiceTest.java`, `review/ReviewServiceTest.java`, `review/OllamaAiReviewClientTest.java`, `review/ClaudeAiReviewClientTest.java`.
- Create(test): `review/ReviewRetryIT.java` — 재시도 소진→LLM_EXHAUSTED(EmbeddedKafka).

---

## Task 0: 브랜치

- [ ] **Step 1: 브랜치**

```powershell
cd devpath-ai-svc
git switch develop; git pull
git switch -c fix/ai-review-transient-recovery
```

---

## Task 1: 오류 분류 예외

**Files:** Create `review/TransientReviewException.java`, `review/PermanentReviewException.java`

**Interfaces:**
- Produces: `TransientReviewException(String errorCode, String message, Throwable cause)` + `String errorCode()`; 동형 `PermanentReviewException`.

- [ ] **Step 1: TransientReviewException 작성**

```java
package ai.devpath.aigw.review;

/** 재시도 가능한 일시 리뷰 오류(LLM 타임아웃/5xx/429). 리스너 밖으로 전파되어 Kafka가 재시도. */
public class TransientReviewException extends RuntimeException {
  private final String errorCode;

  public TransientReviewException(String errorCode, String message, Throwable cause) {
    super(message, cause);
    this.errorCode = errorCode;
  }

  public String errorCode() {
    return errorCode;
  }
}
```

- [ ] **Step 2: PermanentReviewException 작성**

```java
package ai.devpath.aigw.review;

/** 재시도 무의미한 영구 리뷰 오류(LLM 응답 파싱 실패 등). 즉시 finishFailed로 종료. */
public class PermanentReviewException extends RuntimeException {
  private final String errorCode;

  public PermanentReviewException(String errorCode, String message, Throwable cause) {
    super(message, cause);
    this.errorCode = errorCode;
  }

  public String errorCode() {
    return errorCode;
  }
}
```

- [ ] **Step 3: 커밋**

```powershell
git add src/main/java/ai/devpath/aigw/review/TransientReviewException.java src/main/java/ai/devpath/aigw/review/PermanentReviewException.java
git commit -m "feat(ai-svc): transient/permanent review exception taxonomy (review recovery)"
```

---

## Task 2: 영속 — findOrCreatePending + markExhausted

**Files:** Modify `review/ReviewPersistenceService.java`; Test `review/ReviewPersistenceServiceTest.java`

**Interfaces:**
- Produces: `AiCodeReview findOrCreatePending(long sandboxSessionId, long userId, Long contentId)`(기존 행 또는 신규 PENDING, never null); `void markExhausted(long sandboxSessionId)`(PENDING→FAILED(LLM_EXHAUSTED)).
- Consumes: `AiCodeReviewRepository.findBySandboxSessionId(long)`, `saveAndFlush`.

- [ ] **Step 1: 실패 테스트 추가** (`ReviewPersistenceServiceTest.java`에 메서드 추가 — 기존 클램프 테스트 옆)

```java
  @Test
  void findOrCreatePendingReturnsExistingOnSecondCall() {
    long sid = System.nanoTime();
    AiCodeReview first = persistence.findOrCreatePending(sid, 5L, null);
    AiCodeReview second = persistence.findOrCreatePending(sid, 5L, null);

    assertThat(second.getId()).isEqualTo(first.getId());
    assertThat(reviews.findAll().stream().filter(x -> x.getSandboxSessionId() == sid).count()).isEqualTo(1L);
    reviews.deleteById(first.getId());
  }

  @Test
  void markExhaustedSetsFailedLlmExhaustedOnPending() {
    long sid = System.nanoTime();
    AiCodeReview pending = persistence.findOrCreatePending(sid, 5L, null);

    persistence.markExhausted(sid);

    AiCodeReview after = reviews.findById(pending.getId()).orElseThrow();
    assertThat(after.getStatus()).isEqualTo("FAILED");
    assertThat(after.getErrorCode()).isEqualTo("LLM_EXHAUSTED");
    reviews.deleteById(pending.getId());
  }

  @Test
  void markExhaustedDoesNotOverwriteTerminal() {
    long sid = System.nanoTime();
    AiCodeReview pending = persistence.findOrCreatePending(sid, 5L, null);
    persistence.finishDone(pending.getId(),
        new ReviewResult(90, List.of("ok"), List.of(), List.of()), "MOCK");

    persistence.markExhausted(sid); // 이미 DONE → 무변경

    AiCodeReview after = reviews.findById(pending.getId()).orElseThrow();
    assertThat(after.getStatus()).isEqualTo("DONE");
    reviews.deleteById(pending.getId());
  }
```

- [ ] **Step 2: (CI 검증) 컴파일 실패 예상** — `findOrCreatePending`/`markExhausted` 미정의. 로컬 gradle 실행 금지.

- [ ] **Step 3: 구현** — `ReviewPersistenceService.java`의 `createPendingIfAbsent`를 아래 두 메서드로 대체(기존 `createPendingIfAbsent` 메서드 삭제, import 유지: `DataIntegrityViolationException`, `Optional`)

```java
  /** 기존 행이 있으면 그대로 반환, 없으면 PENDING 신규 생성. never null. UNIQUE 경합은 재조회로 흡수. */
  @Transactional
  public AiCodeReview findOrCreatePending(long sandboxSessionId, long userId, Long contentId) {
    Optional<AiCodeReview> existing = reviews.findBySandboxSessionId(sandboxSessionId);
    if (existing.isPresent()) {
      return existing.get();
    }
    AiCodeReview r = new AiCodeReview();
    r.setSandboxSessionId(sandboxSessionId);
    r.setUserId(userId);
    r.setContentId(contentId);
    r.setStatus("PENDING");
    try {
      return reviews.saveAndFlush(r);
    } catch (DataIntegrityViolationException dup) {
      return reviews.findBySandboxSessionId(sandboxSessionId).orElseThrow();
    }
  }

  /** 재시도 소진 시 PENDING 행을 FAILED(LLM_EXHAUSTED)로 종료. 이미 터미널이면 무변경(멱등). */
  @Transactional
  public void markExhausted(long sandboxSessionId) {
    reviews.findBySandboxSessionId(sandboxSessionId).ifPresent(r -> {
      if ("PENDING".equals(r.getStatus())) {
        r.setStatus("FAILED");
        r.setErrorCode("LLM_EXHAUSTED");
        reviews.save(r);
      }
    });
  }
```

- [ ] **Step 4: 커밋**

```powershell
git add src/main/java/ai/devpath/aigw/review/ReviewPersistenceService.java src/test/java/ai/devpath/aigw/review/ReviewPersistenceServiceTest.java
git commit -m "feat(ai-svc): findOrCreatePending + markExhausted for retry recovery (review recovery)"
```

---

## Task 3: ReviewService — 상태기준 멱등 + 분류 catch

**Files:** Modify `review/ReviewService.java`; Test `review/ReviewServiceTest.java`

**Interfaces:**
- Consumes: `ReviewPersistenceService.findOrCreatePending`(Task2), `TransientReviewException`/`PermanentReviewException`(Task1), `SandboxUnavailableException`(기존).

- [ ] **Step 1: 테스트 갱신/추가** (`ReviewServiceTest.java`)

기존 `sandboxFailureMarksFailed`의 error_code 단언을 변경:
```java
    assertThat(r.getErrorCode()).isEqualTo("SANDBOX_UNAVAILABLE"); // 기존 "LLM_FAILED"에서 변경
```

신규 테스트 추가(클래스에 메서드 추가):
```java
  @Test
  void transientLlmFailureRethrowsAndKeepsPending() {
    long sid = System.nanoTime();
    when(sandboxClient.getSession(anyLong())).thenReturn(new SandboxSessionView(
        sid, 7L, "PYTHON", null, "x", "", "", 0, "COMPLETED"));
    when(aiReviewClient.review(org.mockito.ArgumentMatchers.any()))
        .thenThrow(new TransientReviewException("LLM_5XX", "boom", null));

    org.junit.jupiter.api.Assertions.assertThrows(TransientReviewException.class,
        () -> service.reviewRun(sid, 7L, null));

    AiCodeReview r = reviews.findBySandboxSessionId(sid).orElseThrow();
    assertThat(r.getStatus()).isEqualTo("PENDING"); // 재시도 위해 PENDING 유지
    reviews.delete(r);
  }

  @Test
  void permanentLlmFailureMarksParseFailed() {
    long sid = System.nanoTime();
    when(sandboxClient.getSession(anyLong())).thenReturn(new SandboxSessionView(
        sid, 7L, "PYTHON", null, "x", "", "", 0, "COMPLETED"));
    when(aiReviewClient.review(org.mockito.ArgumentMatchers.any()))
        .thenThrow(new PermanentReviewException("PARSE_FAILED", "bad json", null));

    service.reviewRun(sid, 7L, null);

    AiCodeReview r = reviews.findBySandboxSessionId(sid).orElseThrow();
    assertThat(r.getStatus()).isEqualTo("FAILED");
    assertThat(r.getErrorCode()).isEqualTo("PARSE_FAILED");
    reviews.delete(r);
  }
```

> 주의: 위 신규 테스트는 `aiReviewClient`를 stub해야 한다. 기존 `ReviewServiceTest`는 `aiReviewClient`(MockAiReviewClient 실빈)를 mock하지 않으므로, **클래스에 `@MockitoBean AiReviewClient aiReviewClient;` 필드를 추가**한다. 그러면 기존 `createsDoneReviewFromCompletedSession`(provider "MOCK"·confidence≥70 단언)은 깨진다 → 그 테스트의 stub을 추가하거나, **신규 두 테스트를 별도 클래스 `ReviewServiceErrorTest`(@SpringBootTest·@ActiveProfiles("test")·@MockitoBean SandboxClient·@MockitoBean AiReviewClient)로 분리**한다(권장 — 기존 클래스 불변). 분리 시 위 두 메서드를 `ReviewServiceErrorTest`에 넣고, `sandboxFailureMarksFailed` error_code 변경만 기존 클래스에 적용.

- [ ] **Step 2: (CI 검증) 실패 예상** — 미구현. 로컬 gradle 금지.

- [ ] **Step 3: 구현** — `ReviewService.reviewRun` 전체 교체

```java
  public void reviewRun(long sandboxSessionId, long userId, Long contentId) {
    AiCodeReview review = persistence.findOrCreatePending(sandboxSessionId, userId, contentId);
    if ("DONE".equals(review.getStatus()) || "FAILED".equals(review.getStatus())) {
      return; // 터미널 → 멱등 skip
    }
    long reviewId = review.getId();
    try {
      SandboxSessionView session = sandboxClient.getSession(sandboxSessionId);
      if (session.userId() == null || session.userId() != userId) {
        persistence.finishFailed(reviewId, "OWNERSHIP_MISMATCH");
        return;
      }
      ReviewResult result = aiReviewClient.review(new ReviewInput(
          session.language(), session.submittedCode(),
          session.stdout(), session.stderr(), session.exitCode()));
      persistence.finishDone(reviewId, result, aiReviewClient.providerName());
    } catch (TransientReviewException e) {
      throw e; // PENDING 유지 → Kafka 재시도
    } catch (PermanentReviewException e) {
      persistence.finishFailed(reviewId, e.errorCode());
    } catch (SandboxUnavailableException e) {
      persistence.finishFailed(reviewId, "SANDBOX_UNAVAILABLE");
    } catch (RuntimeException e) {
      persistence.finishFailed(reviewId, "LLM_FAILED"); // 예상밖 → 터미널(재시도 안 함)
    }
  }
```

> `import java.util.Optional;`는 더 이상 불필요하면 제거. `created.get()` 등 기존 Optional 사용부는 위 코드로 사라진다.

- [ ] **Step 4: 커밋**

```powershell
git add src/main/java/ai/devpath/aigw/review/ReviewService.java src/test/java/ai/devpath/aigw/review/ReviewServiceTest.java src/test/java/ai/devpath/aigw/review/ReviewServiceErrorTest.java
git commit -m "feat(ai-svc): status-based idempotency + transient/permanent dispatch in reviewRun (review recovery)"
```

---

## Task 4: OllamaAiReviewClient — 오류 매핑

**Files:** Modify `review/OllamaAiReviewClient.java`; Test `review/OllamaAiReviewClientTest.java`

- [ ] **Step 1: 테스트 추가** (`OllamaAiReviewClientTest.java`에 메서드 추가 — 기존 `parsesStructuredReviewFromOllama` 유지)

```java
  @Test
  void serverErrorMapsToTransient5xx() {
    server.enqueue(new MockResponse().setResponseCode(503));
    var client = new OllamaAiReviewClient(server.url("/").toString(), "qwen2.5-coder:7b",
        java.time.Duration.ofSeconds(5), new ReviewPromptBuilder(), JsonMapper.builder().build());

    TransientReviewException ex = org.junit.jupiter.api.Assertions.assertThrows(
        TransientReviewException.class,
        () -> client.review(new ReviewInput("PYTHON", "x", "", "", 0)));
    assertThat(ex.errorCode()).isEqualTo("LLM_5XX");
  }

  @Test
  void rateLimitMapsToTransientRateLimit() {
    server.enqueue(new MockResponse().setResponseCode(429));
    var client = new OllamaAiReviewClient(server.url("/").toString(), "qwen2.5-coder:7b",
        java.time.Duration.ofSeconds(5), new ReviewPromptBuilder(), JsonMapper.builder().build());

    TransientReviewException ex = org.junit.jupiter.api.Assertions.assertThrows(
        TransientReviewException.class,
        () -> client.review(new ReviewInput("PYTHON", "x", "", "", 0)));
    assertThat(ex.errorCode()).isEqualTo("LLM_RATELIMIT");
  }

  @Test
  void malformedJsonMapsToPermanentParseFailed() {
    server.enqueue(new MockResponse().setHeader("Content-Type", "application/json")
        .setBody("{\"message\":{\"content\":\"not-json\"}}"));
    var client = new OllamaAiReviewClient(server.url("/").toString(), "qwen2.5-coder:7b",
        java.time.Duration.ofSeconds(5), new ReviewPromptBuilder(), JsonMapper.builder().build());

    PermanentReviewException ex = org.junit.jupiter.api.Assertions.assertThrows(
        PermanentReviewException.class,
        () -> client.review(new ReviewInput("PYTHON", "x", "", "", 0)));
    assertThat(ex.errorCode()).isEqualTo("PARSE_FAILED");
  }
```

- [ ] **Step 2: (CI 검증) 실패 예상.**

- [ ] **Step 3: 구현** — `OllamaAiReviewClient.java`의 `review`/`callAndParse`/`ContractException` 교체. import 추가: `org.springframework.web.client.RestClientResponseException`, `org.springframework.web.client.ResourceAccessException`. `RestClientException` import 유지.

`review` 메서드(내부 retry 제거):
```java
  @Override
  public ReviewResult review(ReviewInput input) {
    return callAndParse(input);
  }
```

`callAndParse` 교체(기존 try/catch 블록 전체 + `private static final class ContractException` 삭제):
```java
  private ReviewResult callAndParse(ReviewInput input) {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("model", model);
    body.put("messages", List.of(
        Map.of("role", "system", "content", prompts.systemPrompt()),
        Map.of("role", "user", "content", prompts.userContent(input))));
    body.put("stream", false);
    body.put("format", prompts.reviewJsonSchema());
    body.put("options", Map.of("temperature", 0.2));

    OllamaChatResponse response;
    try {
      response = restClient.post().uri("/api/chat").body(body)
          .retrieve().body(OllamaChatResponse.class);
    } catch (RestClientResponseException e) { // HTTP 4xx/5xx 응답
      int status = e.getStatusCode().value();
      if (status == 429) {
        throw new TransientReviewException("LLM_RATELIMIT", "Ollama 429", e);
      }
      if (status >= 500) {
        throw new TransientReviewException("LLM_5XX", "Ollama " + status, e);
      }
      throw new PermanentReviewException("PARSE_FAILED", "Ollama " + status, e);
    } catch (ResourceAccessException e) { // I/O 타임아웃/커넥션
      throw new TransientReviewException("LLM_TIMEOUT", "Ollama timeout", e);
    } catch (RestClientException e) { // 그 외 호출 실패
      throw new TransientReviewException("LLM_TIMEOUT", "Ollama call failed", e);
    }
    if (response == null || response.message() == null
        || response.message().content() == null || response.message().content().isBlank()) {
      throw new PermanentReviewException("PARSE_FAILED", "Ollama empty content", null);
    }
    try {
      return jsonMapper.readValue(response.message().content(), ReviewResult.class);
    } catch (Exception e) {
      throw new PermanentReviewException("PARSE_FAILED", "Ollama JSON parse failed", e);
    }
  }
```

- [ ] **Step 4: 커밋**

```powershell
git add src/main/java/ai/devpath/aigw/review/OllamaAiReviewClient.java src/test/java/ai/devpath/aigw/review/OllamaAiReviewClientTest.java
git commit -m "feat(ai-svc): map Ollama HTTP errors to transient/permanent (review recovery)"
```

---

## Task 5: ClaudeAiReviewClient — 오류 매핑

**Files:** Modify `review/ClaudeAiReviewClient.java`; Test `review/ClaudeAiReviewClientTest.java`

> **⚠️ SDK 예외 타입 실측 필수(추측 금지)**: 구현 전 anthropic-java 2.34.0의 `com.anthropic.errors` 패키지 예외 계층을 확인하라(claude-api 스킬 Java 문서, 또는 `~/.gradle/caches`의 anthropic-java-core jar를 `javap`/소스로). 기대 타입: `RateLimitException`(429), `InternalServerException`/5xx 계열, 커넥션/타임아웃 계열(`AnthropicIoException` 등), 공통 상위 `AnthropicServiceException`/`AnthropicException`. 아래 코드의 catch 타입을 실측 타입으로 교정하라.

- [ ] **Step 1: 테스트(구성 단위, 실호출 없음)** — `ClaudeAiReviewClientTest.java`에 추가. 실 SDK 예외를 만들기 어려우므로 providerName 유지 + (가능하면) 매핑 헬퍼를 분리해 단위 검증. 최소: 기존 `providerNameIsClaude` 유지. SDK 예외→분류 매핑은 CI 컴파일 + 운영 eval에서 확인.

```java
  // 기존 providerNameIsClaude 유지. (실 SDK 예외 인스턴스화는 환경 의존 — 단위는 providerName/구성만.)
```

- [ ] **Step 2: 구현** — `ClaudeAiReviewClient.review`의 SDK 호출을 try/catch로 감싸 매핑. **catch 타입은 Step 위 ⚠️대로 실측 교정.** 골격:

```java
  @Override
  public ReviewResult review(ReviewInput input) {
    StructuredMessageCreateParams<ReviewResult> params = MessageCreateParams.builder()
        .model(model)
        .maxTokens(2000L)
        .system(prompts.systemPrompt())
        .addUserMessage(prompts.userContent(input))
        .outputConfig(ReviewResult.class)
        .build();
    try {
      return client.messages().create(params).content().stream()
          .flatMap(cb -> cb.text().stream())
          .map(typed -> typed.text())
          .findFirst()
          .orElseThrow(() -> new PermanentReviewException("PARSE_FAILED", "Claude 응답이 비어 있습니다", null));
    } catch (com.anthropic.errors.RateLimitException e) {       // 실측 타입으로 교정
      throw new TransientReviewException("LLM_RATELIMIT", "Claude 429", e);
    } catch (com.anthropic.errors.InternalServerException e) {  // 5xx, 실측 타입으로 교정
      throw new TransientReviewException("LLM_5XX", "Claude 5xx", e);
    } catch (com.anthropic.errors.AnthropicIoException e) {     // 타임아웃/커넥션, 실측 타입으로 교정
      throw new TransientReviewException("LLM_TIMEOUT", "Claude io", e);
    } catch (com.anthropic.errors.AnthropicException e) {       // 그 외 SDK 오류(4xx 등) → 영구
      throw new PermanentReviewException("PARSE_FAILED", "Claude error", e);
    }
  }
```

> import는 위 catch가 정리되면 `com.anthropic.errors.*` 필요한 것만 추가. `PermanentReviewException`/`TransientReviewException` 동일 패키지라 import 불필요.

- [ ] **Step 3: 커밋**

```powershell
git add src/main/java/ai/devpath/aigw/review/ClaudeAiReviewClient.java src/test/java/ai/devpath/aigw/review/ClaudeAiReviewClientTest.java
git commit -m "feat(ai-svc): map Claude SDK errors to transient/permanent (review recovery)"
```

---

## Task 6: ReviewKafkaConfig — 에러핸들러 + recoverer + IT

**Files:** Create `review/ReviewKafkaConfig.java`; Test `review/ReviewRetryIT.java`

**Interfaces:**
- Consumes: `ReviewPersistenceService.markExhausted`(Task2), `SandboxRunSubmittedEvent`(shared), `JsonMapper`.
- Produces: `@Bean DefaultErrorHandler`(Spring Boot가 기본 컨테이너 팩토리에 자동 주입).

- [ ] **Step 1: 재시도 소진 IT 작성** — `review/ReviewRetryIT.java`

```java
package ai.devpath.aigw.review;

import static org.awaitility.Awaitility.await;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.when;

import ai.devpath.shared.event.SandboxRunSubmittedEvent;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest
@ActiveProfiles("test")
@EmbeddedKafka(topics = "sandbox.run.submitted", partitions = 1)
class ReviewRetryIT {

  @Autowired KafkaTemplate<String, String> kafka;
  @Autowired JsonMapper jsonMapper;
  @Autowired AiCodeReviewRepository reviews;
  @MockitoBean SandboxClient sandboxClient;
  @MockitoBean AiReviewClient aiReviewClient;

  @Test
  void exhaustedRetriesMarkLlmExhausted() throws Exception {
    long sid = System.nanoTime();
    when(sandboxClient.getSession(anyLong())).thenReturn(new SandboxSessionView(
        sid, 42L, "PYTHON", null, "print(1)", "1\n", "", 0, "COMPLETED"));
    when(aiReviewClient.review(any()))
        .thenThrow(new TransientReviewException("LLM_5XX", "always 5xx", null));
    when(aiReviewClient.providerName()).thenReturn("MOCK");
    var event = new SandboxRunSubmittedEvent(UUID.randomUUID(), Instant.now(), 42L, sid, "PYTHON", null);

    kafka.send("sandbox.run.submitted", jsonMapper.writeValueAsString(event));

    await().atMost(Duration.ofSeconds(40)).untilAsserted(() -> {
      var r = reviews.findBySandboxSessionId(sid);
      org.assertj.core.api.Assertions.assertThat(r).isPresent();
      org.assertj.core.api.Assertions.assertThat(r.get().getStatus()).isEqualTo("FAILED");
      org.assertj.core.api.Assertions.assertThat(r.get().getErrorCode()).isEqualTo("LLM_EXHAUSTED");
    });
    reviews.findBySandboxSessionId(sid).ifPresent(reviews::delete);
  }
}
```

- [ ] **Step 2: (CI 검증) 실패 예상** — DefaultErrorHandler 미구성이면 재시도/recoverer 없음.

- [ ] **Step 3: 구현** — `review/ReviewKafkaConfig.java`

```java
package ai.devpath.aigw.review;

import ai.devpath.shared.event.SandboxRunSubmittedEvent;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.listener.DefaultErrorHandler;
import org.springframework.util.backoff.ExponentialBackOffWithMaxRetries;
import tools.jackson.databind.json.JsonMapper;

/** 리뷰 컨슈머 에러 핸들러: 일시 오류 지수백오프 재시도(3회), 소진 시 FAILED(LLM_EXHAUSTED). */
@Configuration
public class ReviewKafkaConfig {

  private static final Logger log = LoggerFactory.getLogger(ReviewKafkaConfig.class);

  private final ReviewPersistenceService persistence;
  private final JsonMapper jsonMapper;

  public ReviewKafkaConfig(ReviewPersistenceService persistence, JsonMapper jsonMapper) {
    this.persistence = persistence;
    this.jsonMapper = jsonMapper;
  }

  @Bean
  public DefaultErrorHandler reviewErrorHandler() {
    ExponentialBackOffWithMaxRetries backOff = new ExponentialBackOffWithMaxRetries(3);
    backOff.setInitialInterval(1000L);
    backOff.setMultiplier(2.0);
    return new DefaultErrorHandler(this::recover, backOff);
  }

  /** 재시도 소진 시: payload에서 sandboxSessionId 추출 → FAILED(LLM_EXHAUSTED). */
  private void recover(ConsumerRecord<?, ?> record, Exception ex) {
    Object value = record.value();
    try {
      SandboxRunSubmittedEvent event =
          jsonMapper.readValue(String.valueOf(value), SandboxRunSubmittedEvent.class);
      persistence.markExhausted(event.sandboxSessionId());
      log.warn("리뷰 재시도 소진 → FAILED(LLM_EXHAUSTED) session={}", event.sandboxSessionId(), ex);
    } catch (Exception e) {
      log.error("recoverer payload 처리 실패: {}", value, e);
    }
  }
}
```

> Spring Boot `KafkaAutoConfiguration`은 단일 `CommonErrorHandler`(여기선 `DefaultErrorHandler`) 빈을 기본 `ConcurrentKafkaListenerContainerFactory`에 자동 적용한다. 별도 팩토리 배선 불필요. `ReviewConsumer`의 역직렬화 poison-skip(try/catch→return)은 그대로 유지(역직렬화 실패는 재시도 대상 아님).

- [ ] **Step 4: 커밋**

```powershell
git add src/main/java/ai/devpath/aigw/review/ReviewKafkaConfig.java src/test/java/ai/devpath/aigw/review/ReviewRetryIT.java
git commit -m "feat(ai-svc): kafka retry error handler + exhausted recoverer (review recovery)"
```

---

## Task 7: 전체 push + CI 검증

- [ ] **Step 1: push + PR(develop)**

```powershell
git push -u origin fix/ai-review-transient-recovery
gh pr create --base develop --title "fix(ai-svc): 리뷰 일시 LLM 장애 재시도+DB 종료 (슬라이스 #6 Important #1)" --body "일시(타임아웃/5xx/429)/영구 오류 구분, 상태기준 멱등(PENDING 재시도), Kafka 지수백오프(3회)+소진 시 FAILED(LLM_EXHAUSTED), error_code 세분화. 설계서 docs/superpowers/specs/2026-06-23-ai-review-transient-recovery-design.md"
```

- [ ] **Step 2: CI 녹색 확인 → 머지** (mock provider·eval 제외, Postgres+EmbeddedKafka). 실패 시 로그 근본원인 분석 후 수정.

---

## Self-Review 메모(작성자)

- **Spec 커버리지**: ① 예외=Task1 · ② 클라이언트 매핑=Task4(Ollama)/Task5(Claude) · ③ reviewRun=Task3 · ④ 영속=Task2 · ⑤ 에러핸들러=Task6 · ⑥ error_code=전반 · 테스트=각 Task + Task6 IT. 매트릭스 전 행 매핑.
- **No placeholder**: 코드 실값. 단 Task5는 **SDK 예외 타입 실측 교정 지시**(추측 금지 원칙, anthropic-java 2.34.0). Task3은 기존 테스트 충돌 회피 위해 `ReviewServiceErrorTest` 분리 지시.
- **타입 일관성**: `findOrCreatePending`(AiCodeReview 반환)·`markExhausted(long)`·`TransientReviewException(code,msg,cause)+errorCode()`·`PermanentReviewException` 동형. `ReviewService`가 `created.get()` 등 Optional 제거. error_code 문자열이 매트릭스·테스트·구현 일치.
- **환경**: ai-svc 로컬 빌드 불가 → 전 Task 작성만, CI 검증(Global Constraints). 마이그레이션 무변경.
- **회귀 방지**: `duplicateEventIsIdempotent`(DONE skip)·`ownershipMismatchFails` 유지, `sandboxFailureMarksFailed`는 error_code만 SANDBOX_UNAVAILABLE로 갱신.
