# 슬라이스 #6 빌드 C1 — ai-svc 비동기 리뷰 파이프라인 + API (Mock provider) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **직접 작업 권장**(콘텐츠필터 전례). 본 C1은 인젝션 방어 프롬프트가 없는 파이프라인/API라 위험 낮음. 실제 LLM 프롬프트는 C2에서.

**Goal:** ai-svc에 `SandboxRunSubmittedEvent`를 소비해 `ai_code_reviews`에 리뷰를 비동기 생성하는 파이프라인과 폴링/피드백 API를 추가한다. LLM은 `AiReviewClient` 인터페이스 + **Mock 구현**으로 두어 외부 의존 없이 CI 녹색·끝단간 통합(빌드 D/E)이 가능하게 한다. 실제 Ollama/Claude 공급자는 빌드 C2.

**Architecture:** ai-svc(무상태 Ollama 게이트웨이)에 JPA+Kafka+Security를 활성화한다. `ReviewConsumer`(@KafkaListener) → `ReviewService`(오케스트레이션) → `ReviewPersistenceService`(짧은 @Transactional: PENDING 선삽입·DONE/FAILED) + `SandboxClient`(코드/결과 조회) + `AiReviewClient`(Mock). 폴링/피드백은 `ReviewController`. LLM 호출은 트랜잭션 밖(슬라이스 #3/#5 패턴).

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Spring Data JPA · Spring Kafka · Spring Security(oauth2 resource server, HS256) · RestClient · PostgreSQL 17 · JUnit 5 · EmbeddedKafka · MockMvc · Mockito · MockWebServer.

## Global Constraints

- 대상 레포: `devpath-ai-svc` 단독. 설계서 [2026-06-23-md2-slice6-ai-code-review-design](../specs/2026-06-23-md2-slice6-ai-code-review-design.md) D-1·D-5·D-7·D-8·D-9 + §5(ai-svc)·§7.
- **빌드 A(`ai_code_reviews`) main 릴리스 후 시작**. 빌드 시작 시 `--refresh-dependencies`(슬라이스 #3 교훈: 로컬 gradle 캐시가 옛 shared에 고정).
- 패키지 루트 `ai.devpath.aigw`. 신규 리뷰 모듈은 `ai.devpath.aigw.review`. 기존 `ai.devpath.aigw.ollama`(게이트웨이)는 무변경.
- **Mock이 기본 provider**: `@ConditionalOnProperty("devpath.review.provider", havingValue="mock", matchIfMissing=true)`. CI/test/미설정 dev는 Mock. (실 공급자는 C2.)
- Boot4 모듈: Kafka=`spring-boot-kafka`, Flyway(test)=`spring-boot-flyway`. `@AutoConfigureMockMvc`=`org.springframework.boot.webmvc.test.autoconfigure`. `@MockitoBean`. 모든 `@SpringBootTest` `@ActiveProfiles("test")`. JsonMapper(Jackson3, `tools.jackson.databind.json.JsonMapper`).
- 교차서비스 FK 없음(빌드 A). 멱등: `UNIQUE(sandbox_session_id)` + insert-if-absent.
- **CI는 외부 LLM 실호출 금지**(Mock provider). fresh DB(`devpath_citest`) + EmbeddedKafka로 검증.
- LLM 호출은 `@Transactional` **밖**(persistence 분리, 자기호출 프록시 우회 회피).
- 신규 작업 브랜치는 `develop`에서 분기. 운영 비밀값(Anthropic 키 등) 커밋 금지.

---

## File Structure

- Modify: `build.gradle.kts` — data-jpa·postgresql·security·oauth2-resource-server·spring-kafka·spring-boot-kafka 활성화 + test deps.
- Modify: `src/main/resources/application.yml` — datasource·jpa(validate)·flyway off·kafka·jwt·sandbox base-url·review.provider.
- Create: `src/main/java/ai/devpath/aigw/config/SecurityConfig.java`, `config/GlobalExceptionHandler.java`(learning-svc 미러).
- Create(review 모듈, `src/main/java/ai/devpath/aigw/review/`):
  - `CodeReview.java`·`ReviewIssue.java`(API DTO) · `ReviewResult.java`·`ReviewInput.java`(client I/O) · `AiReviewClient.java`(interface) · `MockAiReviewClient.java`.
  - `AiCodeReview.java`(엔티티) · `AiCodeReviewRepository.java`.
  - `SandboxClient.java` · `SandboxSessionView.java`(조회 DTO).
  - `ReviewPersistenceService.java`(짧은 tx) · `ReviewService.java`(오케스트레이션) · `ReviewConsumer.java`(@KafkaListener).
  - `ReviewController.java`(폴링/피드백) · `ReviewNotFoundException.java`.
- Create(test, `src/test/java/ai/devpath/aigw/review/`): 각 Task 참조.

---

## Task 0: 브랜치 + 의존성/설정 활성화

**Files:** Modify `build.gradle.kts`, `src/main/resources/application.yml`

- [ ] **Step 1: 브랜치 + 최신 shared**

```powershell
cd devpath-ai-svc
git switch develop
git pull
git switch -c feat/slice6-ai-review-pipeline
```

- [ ] **Step 2: build.gradle deps 활성화**

`dependencies { }`에서 주석 3줄을 활성화하고 누락 deps를 추가한다(learning-svc 미러):

```kotlin
	implementation("org.springframework.boot:spring-boot-starter-actuator")
	implementation("org.springframework.boot:spring-boot-starter-validation")
	implementation("org.springframework.boot:spring-boot-starter-webmvc")
	implementation("org.springframework.boot:spring-boot-starter-data-jpa")
	implementation("org.springframework.boot:spring-boot-starter-security")
	implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
	implementation("org.springframework.kafka:spring-kafka")
	implementation("org.springframework.boot:spring-boot-kafka")
	implementation("ai.devpath:devpath-shared:0.0.1-SNAPSHOT")
	runtimeOnly("org.postgresql:postgresql")
	compileOnly("org.projectlombok:lombok")
	annotationProcessor("org.projectlombok:lombok")
	testImplementation("org.springframework.boot:spring-boot-starter-actuator-test")
	testImplementation("org.springframework.boot:spring-boot-starter-validation-test")
	testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
	testImplementation("org.springframework.boot:spring-boot-starter-security-test")
	testImplementation("org.springframework.boot:spring-boot-starter-data-jpa-test")
	testImplementation("org.springframework.kafka:spring-kafka-test")
	testImplementation("org.awaitility:awaitility")
	testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
	testImplementation("org.springframework.boot:spring-boot-flyway")
	testImplementation("org.flywaydb:flyway-core")
	testImplementation("org.flywaydb:flyway-database-postgresql")
	testCompileOnly("org.projectlombok:lombok")
	testRuntimeOnly("org.junit.platform:junit-platform-launcher")
	testAnnotationProcessor("org.projectlombok:lombok")
```

- [ ] **Step 3: application.yml에 datasource·kafka·jwt·review 블록 추가**

> learning-svc `application.yml`을 본보기로 확인 후 작성(추측 금지). 표준 패턴:

```yaml
spring:
  application:
    name: devpath-ai-svc
  datasource:
    url: ${DB_URL:jdbc:postgresql://localhost:5432/devpath}
    username: ${DB_USER:devpath}
    password: ${DB_PASSWORD:localdev}
  jpa:
    hibernate:
      ddl-auto: validate
    open-in-view: false
  flyway:
    enabled: false
  kafka:
    bootstrap-servers: ${KAFKA_BOOTSTRAP:localhost:9092}
    consumer:
      group-id: devpath-ai-review
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.apache.kafka.common.serialization.StringDeserializer

server:
  port: 8080

devpath:
  auth:
    jwt-secret: ${JWT_SECRET:test-secret-please-change-min-32-bytes-long-0123456789}
  sandbox:
    base-url: ${SANDBOX_URI:http://localhost:8085}
    timeout: ${SANDBOX_TIMEOUT:PT5S}
  review:
    provider: ${REVIEW_PROVIDER:mock}
  ollama:
    base-url: ${OLLAMA_BASE_URL:http://localhost:11434}
    gen-model: ${OLLAMA_GEN_MODEL:qwen2.5:7b}
    embed-model: ${OLLAMA_EMBED_MODEL:nomic-embed-text}
    timeout: ${OLLAMA_TIMEOUT:PT8S}

management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics
```

`src/test/resources/application-test.yml`(없으면 생성)에 test datasource + `spring.flyway.enabled: true`(shared jar classpath:db/migration 적용)·`devpath.review.provider: mock`을 둔다(learning-svc test yml 미러).

- [ ] **Step 4: 컴파일 베이스라인**

```powershell
.\gradlew.bat --refresh-dependencies compileJava
```

Expected: 컴파일 성공(기존 Ollama 게이트웨이 무변경). 신규 deps 해석.

- [ ] **Step 5: 커밋**

```powershell
git add build.gradle.kts src/main/resources/application.yml src/test/resources/application-test.yml
git commit -m "chore(ai-svc): enable jpa/kafka/security for review pipeline (slice6 C1)"
```

---

## Task 1: 엔티티 + 리포지토리 + API DTO

**Files:** Create `review/AiCodeReview.java`, `review/AiCodeReviewRepository.java`, `review/CodeReview.java`, `review/ReviewIssue.java`; Test `review/AiCodeReviewJpaTest.java`

**Interfaces:**
- Produces: `AiCodeReview`(JPA, `ai_code_reviews`), `AiCodeReviewRepository extends JpaRepository<AiCodeReview, Long>` + `Optional<AiCodeReview> findBySandboxSessionId(long)` + `boolean existsBySandboxSessionId(long)`.
- Produces(API): `record CodeReview(String id, String status, int confidence, List<String> strengths, List<ReviewIssue> improvements, List<ReviewIssue> security)`, `record ReviewIssue(String message, Integer line, String severity)`.

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/aigw/review/AiCodeReviewJpaTest.java`:

```java
package ai.devpath.aigw.review;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class AiCodeReviewJpaTest {

  @Autowired AiCodeReviewRepository reviews;

  @Test
  void persistsAndQueriesBySandboxSession() {
    long sid = System.nanoTime();
    AiCodeReview r = new AiCodeReview();
    r.setSandboxSessionId(sid);
    r.setUserId(42L);
    r.setStatus("PENDING");
    AiCodeReview saved = reviews.save(r);

    assertThat(saved.getId()).isNotNull();
    assertThat(saved.getCreatedAt()).isNotNull();
    assertThat(saved.getStrengths()).isEqualTo("[]"); // JSONB 기본값
    assertThat(reviews.existsBySandboxSessionId(sid)).isTrue();
    assertThat(reviews.findBySandboxSessionId(sid)).get()
        .extracting(AiCodeReview::getUserId).isEqualTo(42L);

    reviews.delete(saved);
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.aigw.review.AiCodeReviewJpaTest"
```

Expected: 컴파일 실패(클래스 없음) → FAIL.

- [ ] **Step 3: DTO 작성**

`review/ReviewIssue.java`:

```java
package ai.devpath.aigw.review;

public record ReviewIssue(String message, Integer line, String severity) {}
```

`review/CodeReview.java`:

```java
package ai.devpath.aigw.review;

import java.util.List;

public record CodeReview(
    String id,
    String status,
    int confidence,
    List<String> strengths,
    List<ReviewIssue> improvements,
    List<ReviewIssue> security) {}
```

- [ ] **Step 4: 엔티티 + 리포지토리 작성**

`review/AiCodeReview.java`:

```java
package ai.devpath.aigw.review;

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
@Table(name = "ai_code_reviews")
public class AiCodeReview {

  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
  @Column(name = "sandbox_session_id", nullable = false) private Long sandboxSessionId;
  @Column(name = "user_id", nullable = false) private Long userId;
  @Column(name = "content_id") private Long contentId;
  @Column(nullable = false) private String status = "PENDING";
  private String provider;
  private Integer confidence;
  @JdbcTypeCode(SqlTypes.JSON) private String strengths = "[]";
  @JdbcTypeCode(SqlTypes.JSON) private String improvements = "[]";
  @JdbcTypeCode(SqlTypes.JSON) private String security = "[]";
  private String feedback;
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
  public Long getSandboxSessionId() { return sandboxSessionId; }
  public void setSandboxSessionId(Long v) { this.sandboxSessionId = v; }
  public Long getUserId() { return userId; }
  public void setUserId(Long v) { this.userId = v; }
  public Long getContentId() { return contentId; }
  public void setContentId(Long v) { this.contentId = v; }
  public String getStatus() { return status; }
  public void setStatus(String v) { this.status = v; }
  public String getProvider() { return provider; }
  public void setProvider(String v) { this.provider = v; }
  public Integer getConfidence() { return confidence; }
  public void setConfidence(Integer v) { this.confidence = v; }
  public String getStrengths() { return strengths; }
  public void setStrengths(String v) { this.strengths = v; }
  public String getImprovements() { return improvements; }
  public void setImprovements(String v) { this.improvements = v; }
  public String getSecurity() { return security; }
  public void setSecurity(String v) { this.security = v; }
  public String getFeedback() { return feedback; }
  public void setFeedback(String v) { this.feedback = v; }
  public String getErrorCode() { return errorCode; }
  public void setErrorCode(String v) { this.errorCode = v; }
  public Instant getCreatedAt() { return createdAt; }
  public Instant getUpdatedAt() { return updatedAt; }
}
```

`review/AiCodeReviewRepository.java`:

```java
package ai.devpath.aigw.review;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AiCodeReviewRepository extends JpaRepository<AiCodeReview, Long> {
  Optional<AiCodeReview> findBySandboxSessionId(long sandboxSessionId);
  boolean existsBySandboxSessionId(long sandboxSessionId);
}
```

- [ ] **Step 5: 통과 확인 + 커밋**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.aigw.review.AiCodeReviewJpaTest"
git add src/main/java/ai/devpath/aigw/review/AiCodeReview.java src/main/java/ai/devpath/aigw/review/AiCodeReviewRepository.java src/main/java/ai/devpath/aigw/review/CodeReview.java src/main/java/ai/devpath/aigw/review/ReviewIssue.java src/test/java/ai/devpath/aigw/review/AiCodeReviewJpaTest.java
git commit -m "feat(ai-svc): ai_code_reviews entity, repository, CodeReview DTO (slice6 C1)"
```

Expected: PASS(엔티티·JSONB 기본값·파생쿼리).

---

## Task 2: SecurityConfig + GlobalExceptionHandler (learning-svc 미러)

**Files:** Create `config/SecurityConfig.java`, `config/GlobalExceptionHandler.java`; Test `review/ReviewSecurityTest.java`

**Interfaces:**
- Produces: HS256 JWT 리소스서버. `/actuator/health` permitAll, 그 외 authenticated. `AccessDeniedException`→403, `IllegalArgumentException`→400, `ResponseStatusException`은 Spring 기본 처리.

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/aigw/review/ReviewSecurityTest.java`:

```java
package ai.devpath.aigw.review;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class ReviewSecurityTest {

  @Autowired MockMvc mvc;

  @Test
  void reviewsRequireAuth() throws Exception {
    mvc.perform(get("/reviews?sandboxSessionId=1")).andExpect(status().isUnauthorized());
  }

  @Test
  void actuatorHealthIsPublic() throws Exception {
    mvc.perform(get("/actuator/health")).andExpect(status().isOk());
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.review.ReviewSecurityTest"
```

Expected: SecurityConfig 없으면 Spring Boot 기본 보안이 떠 401이 날 수도 있으나, `/reviews` 컨트롤러(Task7) 부재로 우선 컴파일/컨텍스트 단계에서 진행 — 이 단계 통과 기준은 Task7 후 최종. (보안 빈을 먼저 둬 컨텍스트가 명시 구성으로 뜨게 한다.) `actuatorHealthIsPublic` FAIL 가능(기본 보안).

- [ ] **Step 3: SecurityConfig 작성** (learning-svc `config/SecurityConfig.java`와 동일, permitAll은 actuator만)

```java
package ai.devpath.aigw.config;

import java.nio.charset.StandardCharsets;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

  @Bean
  public SecretKey jwtSecretKey(
      @Value("${devpath.auth.jwt-secret:test-secret-please-change-min-32-bytes-long-0123456789}") String secret) {
    byte[] bytes = secret.getBytes(StandardCharsets.UTF_8);
    if (bytes.length < 32) {
      throw new IllegalStateException("JWT_SECRET must be >= 32 bytes (HS256), got " + bytes.length);
    }
    return new SecretKeySpec(bytes, "HmacSHA256");
  }

  @Bean
  public JwtDecoder jwtDecoder(SecretKey key) {
    return NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
  }

  @Bean
  public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
    http
        .csrf(csrf -> csrf.disable())
        .authorizeHttpRequests(authorize -> authorize
            .requestMatchers("/actuator/health").permitAll()
            .anyRequest().authenticated())
        .oauth2ResourceServer(rs -> rs.jwt(Customizer.withDefaults()));
    return http.build();
  }
}
```

- [ ] **Step 4: GlobalExceptionHandler 작성** (learning-svc 미러, 본 모듈이 쓰는 예외만)

```java
package ai.devpath.aigw.config;

import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

  @ExceptionHandler(IllegalArgumentException.class)
  public ResponseEntity<Map<String, String>> badRequest(IllegalArgumentException e) {
    return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
  }

  @ExceptionHandler(AccessDeniedException.class)
  public ResponseEntity<Map<String, String>> forbidden(AccessDeniedException e) {
    return ResponseEntity.status(HttpStatus.FORBIDDEN).body(Map.of("error", e.getMessage()));
  }
}
```

> `ReviewNotFoundException`은 Task7에서 `@ResponseStatus(NOT_FOUND)`로 두어 핸들러 불요. 기존 `ollama.OllamaExceptionHandler`(@RestControllerAdvice)와 충돌하지 않도록 본 핸들러는 review 모듈 예외만 다룬다(서로 다른 예외 타입이므로 공존 가능).

- [ ] **Step 5: 통과 확인 + 커밋** (actuator 공개 확인; `/reviews` 401은 Task7 후 최종)

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.review.ReviewSecurityTest"
git add src/main/java/ai/devpath/aigw/config/SecurityConfig.java src/main/java/ai/devpath/aigw/config/GlobalExceptionHandler.java src/test/java/ai/devpath/aigw/review/ReviewSecurityTest.java
git commit -m "feat(ai-svc): JWT resource-server security + exception handler (slice6 C1)"
```

---

## Task 3: SandboxClient (코드/결과 조회)

**Files:** Create `review/SandboxSessionView.java`, `review/SandboxClient.java`; Test `review/SandboxClientTest.java`

**Interfaces:**
- Produces: `record SandboxSessionView(Long id, Long userId, String language, Long contentId, String submittedCode, String stdout, String stderr, Integer exitCode, String status)`; `SandboxClient.getSession(long id)` → `SandboxSessionView`(GET `/internal/sandbox/sessions/{id}`, 빌드 B D-7 계약). 실패 시 `SandboxUnavailableException`.
- Consumes: `RestClient`(RestAiPathClient 패턴).

- [ ] **Step 1: 실패 테스트(MockWebServer)**

`src/test/java/ai/devpath/aigw/review/SandboxClientTest.java`:

```java
package ai.devpath.aigw.review;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Duration;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class SandboxClientTest {

  private MockWebServer server;

  @BeforeEach
  void setUp() throws Exception { server = new MockWebServer(); server.start(); }

  @AfterEach
  void tearDown() throws Exception { server.shutdown(); }

  @Test
  void fetchesSessionView() {
    server.enqueue(new MockResponse()
        .setHeader("Content-Type", "application/json")
        .setBody("{\"id\":7,\"userId\":42,\"language\":\"PYTHON\",\"contentId\":3,"
            + "\"submittedCode\":\"print(1)\",\"stdout\":\"1\\n\",\"stderr\":\"\","
            + "\"exitCode\":0,\"status\":\"COMPLETED\"}"));
    var client = new SandboxClient(server.url("/").toString(), Duration.ofSeconds(5));

    SandboxSessionView v = client.getSession(7);

    assertThat(v.userId()).isEqualTo(42L);
    assertThat(v.submittedCode()).isEqualTo("print(1)");
    assertThat(v.exitCode()).isEqualTo(0);
  }

  @Test
  void serverErrorThrowsUnavailable() {
    server.enqueue(new MockResponse().setResponseCode(500));
    var client = new SandboxClient(server.url("/").toString(), Duration.ofSeconds(5));

    assertThatThrownBy(() -> client.getSession(7))
        .isInstanceOf(SandboxUnavailableException.class);
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.review.SandboxClientTest"
```

Expected: 컴파일 실패 → FAIL.

- [ ] **Step 3: View + Client 구현**

`review/SandboxSessionView.java`:

```java
package ai.devpath.aigw.review;

public record SandboxSessionView(
    Long id, Long userId, String language, Long contentId,
    String submittedCode, String stdout, String stderr, Integer exitCode, String status) {}
```

`review/SandboxUnavailableException.java`:

```java
package ai.devpath.aigw.review;

public class SandboxUnavailableException extends RuntimeException {
  public SandboxUnavailableException(String message, Throwable cause) { super(message, cause); }
}
```

`review/SandboxClient.java` (RestAiPathClient 패턴):

```java
package ai.devpath.aigw.review;

import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class SandboxClient {

  private final RestClient restClient;

  public SandboxClient(
      @Value("${devpath.sandbox.base-url:http://localhost:8085}") String baseUrl,
      @Value("${devpath.sandbox.timeout:PT5S}") Duration timeout) {
    var requestFactory = new SimpleClientHttpRequestFactory();
    requestFactory.setConnectTimeout(timeout);
    requestFactory.setReadTimeout(timeout);
    this.restClient = RestClient.builder().baseUrl(baseUrl).requestFactory(requestFactory).build();
  }

  public SandboxSessionView getSession(long sandboxSessionId) {
    try {
      SandboxSessionView view = restClient.get()
          .uri("/internal/sandbox/sessions/{id}", sandboxSessionId)
          .retrieve()
          .body(SandboxSessionView.class);
      if (view == null || view.submittedCode() == null) {
        throw new SandboxUnavailableException(
            "sandbox session response is incomplete: " + sandboxSessionId, null);
      }
      return view;
    } catch (RestClientException e) {
      throw new SandboxUnavailableException("sandbox session fetch failed: " + sandboxSessionId, e);
    }
  }
}
```

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.review.SandboxClientTest"
git add src/main/java/ai/devpath/aigw/review/SandboxSessionView.java src/main/java/ai/devpath/aigw/review/SandboxUnavailableException.java src/main/java/ai/devpath/aigw/review/SandboxClient.java src/test/java/ai/devpath/aigw/review/SandboxClientTest.java
git commit -m "feat(ai-svc): SandboxClient to fetch run code+result (slice6 C1 D-7)"
```

---

## Task 4: AiReviewClient 인터페이스 + Mock 구현

**Files:** Create `review/ReviewInput.java`, `review/ReviewResult.java`, `review/AiReviewClient.java`, `review/MockAiReviewClient.java`; Test `review/MockAiReviewClientTest.java`

**Interfaces:**
- Produces: `record ReviewInput(String language, String code, String stdout, String stderr, Integer exitCode)`; `record ReviewResult(int confidence, List<String> strengths, List<ReviewIssue> improvements, List<ReviewIssue> security)`; `interface AiReviewClient { ReviewResult review(ReviewInput input); String providerName(); }`; `MockAiReviewClient`(기본 provider, 실행결과 기반 결정적 출력).

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/aigw/review/MockAiReviewClientTest.java`:

```java
package ai.devpath.aigw.review;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class MockAiReviewClientTest {

  private final MockAiReviewClient client = new MockAiReviewClient();

  @Test
  void successfulRunGetsHighConfidenceNoIssues() {
    ReviewResult r = client.review(new ReviewInput("PYTHON", "print(1)", "1\n", "", 0));
    assertThat(client.providerName()).isEqualTo("MOCK");
    assertThat(r.confidence()).isGreaterThanOrEqualTo(70);
    assertThat(r.improvements()).isEmpty();
  }

  @Test
  void failedRunIsGroundedInExitCode() {
    ReviewResult r = client.review(new ReviewInput("PYTHON", "boom", "", "Traceback\n", 1));
    assertThat(r.confidence()).isLessThan(70);
    assertThat(r.improvements()).isNotEmpty();
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.review.MockAiReviewClientTest"
```

Expected: 컴파일 실패 → FAIL.

- [ ] **Step 3: 타입 + Mock 구현**

`review/ReviewInput.java`:

```java
package ai.devpath.aigw.review;

public record ReviewInput(String language, String code, String stdout, String stderr, Integer exitCode) {}
```

`review/ReviewResult.java`:

```java
package ai.devpath.aigw.review;

import java.util.List;

public record ReviewResult(
    int confidence, List<String> strengths, List<ReviewIssue> improvements, List<ReviewIssue> security) {}
```

`review/AiReviewClient.java`:

```java
package ai.devpath.aigw.review;

/** 코드리뷰 LLM 추상화. 구현: Mock(C1), Ollama·Claude(C2). 동일 출력 스키마. */
public interface AiReviewClient {
  ReviewResult review(ReviewInput input);
  String providerName();
}
```

`review/MockAiReviewClient.java`:

```java
package ai.devpath.aigw.review;

import java.util.List;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/** 외부 LLM 없는 결정적 리뷰(CI/test/미설정 dev 기본). 실행결과(exitCode)에 그라운딩. */
@Component
@ConditionalOnProperty(name = "devpath.review.provider", havingValue = "mock", matchIfMissing = true)
public class MockAiReviewClient implements AiReviewClient {

  @Override
  public ReviewResult review(ReviewInput input) {
    boolean failed = input.exitCode() != null && input.exitCode() != 0;
    if (failed) {
      return new ReviewResult(
          40,
          List.of("코드를 수신했습니다 (" + input.language() + ")"),
          List.of(new ReviewIssue("실행이 비정상 종료되었습니다(exit=" + input.exitCode() + ")", null, "warning")),
          List.of());
    }
    return new ReviewResult(
        85,
        List.of("정상 실행되었습니다 (" + input.language() + ")"),
        List.of(),
        List.of());
  }

  @Override
  public String providerName() { return "MOCK"; }
}
```

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
.\gradlew.bat test --tests "ai.devpath.aigw.review.MockAiReviewClientTest"
git add src/main/java/ai/devpath/aigw/review/ReviewInput.java src/main/java/ai/devpath/aigw/review/ReviewResult.java src/main/java/ai/devpath/aigw/review/AiReviewClient.java src/main/java/ai/devpath/aigw/review/MockAiReviewClient.java src/test/java/ai/devpath/aigw/review/MockAiReviewClientTest.java
git commit -m "feat(ai-svc): AiReviewClient interface + Mock provider (slice6 C1)"
```

---

## Task 5: ReviewPersistenceService + ReviewService (오케스트레이션)

**Files:** Create `review/ReviewPersistenceService.java`, `review/ReviewService.java`; Test `review/ReviewServiceTest.java`

**Interfaces:**
- Produces: `ReviewService.reviewRun(long sandboxSessionId, long userId, Long contentId)`(이벤트 진입점, 멱등). `ReviewPersistenceService`(짧은 tx): `Optional<AiCodeReview> createPendingIfAbsent(long, long, Long)`, `void finishDone(long reviewId, ReviewResult, String provider)`, `void finishFailed(long reviewId, String errorCode)`.
- Consumes: `AiCodeReviewRepository`, `SandboxClient`(Task3), `AiReviewClient`(Task4), `JsonMapper`.

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/aigw/review/ReviewServiceTest.java`:

```java
package ai.devpath.aigw.review;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

@SpringBootTest
@ActiveProfiles("test")
class ReviewServiceTest {

  @Autowired ReviewService service;
  @Autowired AiCodeReviewRepository reviews;
  @MockitoBean SandboxClient sandboxClient;

  @Test
  void createsDoneReviewFromCompletedSession() {
    long sid = System.nanoTime();
    when(sandboxClient.getSession(anyLong())).thenReturn(new SandboxSessionView(
        sid, 42L, "PYTHON", 3L, "print(1)", "1\n", "", 0, "COMPLETED"));

    service.reviewRun(sid, 42L, 3L);

    AiCodeReview r = reviews.findBySandboxSessionId(sid).orElseThrow();
    assertThat(r.getStatus()).isEqualTo("DONE");
    assertThat(r.getProvider()).isEqualTo("MOCK");
    assertThat(r.getConfidence()).isGreaterThanOrEqualTo(70);
    reviews.delete(r);
  }

  @Test
  void duplicateEventIsIdempotent() {
    long sid = System.nanoTime();
    when(sandboxClient.getSession(anyLong())).thenReturn(new SandboxSessionView(
        sid, 7L, "PYTHON", null, "x", "", "", 0, "COMPLETED"));

    service.reviewRun(sid, 7L, null);
    service.reviewRun(sid, 7L, null); // 재전달

    assertThat(reviews.findBySandboxSessionId(sid)).isPresent();
    assertThat(reviews.findAll().stream()
        .filter(x -> x.getSandboxSessionId() == sid).count()).isEqualTo(1L);
    reviews.findBySandboxSessionId(sid).ifPresent(reviews::delete);
  }

  @Test
  void ownershipMismatchFails() {
    long sid = System.nanoTime();
    when(sandboxClient.getSession(anyLong())).thenReturn(new SandboxSessionView(
        sid, 999L, "PYTHON", null, "x", "", "", 0, "COMPLETED")); // 세션 user != 이벤트 user

    service.reviewRun(sid, 7L, null);

    AiCodeReview r = reviews.findBySandboxSessionId(sid).orElseThrow();
    assertThat(r.getStatus()).isEqualTo("FAILED");
    assertThat(r.getErrorCode()).isEqualTo("OWNERSHIP_MISMATCH");
    reviews.delete(r);
  }

  @Test
  void sandboxFailureMarksFailed() {
    long sid = System.nanoTime();
    when(sandboxClient.getSession(anyLong()))
        .thenThrow(new SandboxUnavailableException("down", null));

    service.reviewRun(sid, 7L, null);

    AiCodeReview r = reviews.findBySandboxSessionId(sid).orElseThrow();
    assertThat(r.getStatus()).isEqualTo("FAILED");
    assertThat(r.getErrorCode()).isEqualTo("LLM_FAILED");
    reviews.delete(r);
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.aigw.review.ReviewServiceTest"
```

Expected: 컴파일 실패 → FAIL.

- [ ] **Step 3: Persistence(짧은 tx) 구현**

`review/ReviewPersistenceService.java`:

```java
package ai.devpath.aigw.review;

import java.util.List;
import java.util.Optional;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.json.JsonMapper;

/** 리뷰 영속을 짧은 @Transactional로 분리(LLM 호출은 ReviewService에서 tx 밖). */
@Service
public class ReviewPersistenceService {

  private final AiCodeReviewRepository reviews;
  private final JsonMapper jsonMapper;

  public ReviewPersistenceService(AiCodeReviewRepository reviews, JsonMapper jsonMapper) {
    this.reviews = reviews;
    this.jsonMapper = jsonMapper;
  }

  /** 멱등: 이미 있으면 empty. UNIQUE(sandbox_session_id) 경합도 empty로 흡수. */
  @Transactional
  public Optional<AiCodeReview> createPendingIfAbsent(long sandboxSessionId, long userId, Long contentId) {
    if (reviews.existsBySandboxSessionId(sandboxSessionId)) {
      return Optional.empty();
    }
    AiCodeReview r = new AiCodeReview();
    r.setSandboxSessionId(sandboxSessionId);
    r.setUserId(userId);
    r.setContentId(contentId);
    r.setStatus("PENDING");
    try {
      return Optional.of(reviews.saveAndFlush(r));
    } catch (DataIntegrityViolationException dup) {
      return Optional.empty();
    }
  }

  @Transactional
  public void finishDone(long reviewId, ReviewResult result, String provider) {
    AiCodeReview r = reviews.findById(reviewId).orElseThrow();
    r.setStatus("DONE");
    r.setProvider(provider);
    r.setConfidence(result.confidence());
    r.setStrengths(toJson(result.strengths()));
    r.setImprovements(toJson(result.improvements()));
    r.setSecurity(toJson(result.security()));
    reviews.save(r);
  }

  @Transactional
  public void finishFailed(long reviewId, String errorCode) {
    AiCodeReview r = reviews.findById(reviewId).orElseThrow();
    r.setStatus("FAILED");
    r.setErrorCode(errorCode);
    reviews.save(r);
  }

  private String toJson(List<?> value) {
    try {
      return jsonMapper.writeValueAsString(value);
    } catch (Exception e) {
      throw new IllegalStateException("리뷰 결과 직렬화 실패", e);
    }
  }
}
```

- [ ] **Step 4: ReviewService(오케스트레이션) 구현**

`review/ReviewService.java`:

```java
package ai.devpath.aigw.review;

import java.util.Optional;
import org.springframework.stereotype.Service;

/**
 * 리뷰 오케스트레이션. PENDING 선삽입(짧은 tx) → 세션 조회 + LLM(트랜잭션 밖) → DONE/FAILED(짧은 tx).
 * 자기호출 프록시 우회를 피하려 tx 메서드는 ReviewPersistenceService에 둔다(슬라이스 #3/#5 패턴).
 */
@Service
public class ReviewService {

  private final ReviewPersistenceService persistence;
  private final SandboxClient sandboxClient;
  private final AiReviewClient aiReviewClient;

  public ReviewService(ReviewPersistenceService persistence, SandboxClient sandboxClient,
      AiReviewClient aiReviewClient) {
    this.persistence = persistence;
    this.sandboxClient = sandboxClient;
    this.aiReviewClient = aiReviewClient;
  }

  public void reviewRun(long sandboxSessionId, long userId, Long contentId) {
    Optional<AiCodeReview> created = persistence.createPendingIfAbsent(sandboxSessionId, userId, contentId);
    if (created.isEmpty()) {
      return; // 멱등: 이미 리뷰 존재
    }
    long reviewId = created.get().getId();
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
    } catch (RuntimeException e) {
      persistence.finishFailed(reviewId, "LLM_FAILED");
    }
  }
}
```

- [ ] **Step 5: 통과 확인 + 커밋**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.aigw.review.ReviewServiceTest"
git add src/main/java/ai/devpath/aigw/review/ReviewPersistenceService.java src/main/java/ai/devpath/aigw/review/ReviewService.java src/test/java/ai/devpath/aigw/review/ReviewServiceTest.java
git commit -m "feat(ai-svc): review orchestration + idempotent persistence (slice6 C1 D-9)"
```

Expected: 4 케이스 PASS(DONE 생성·멱등·소유불일치 FAILED·sandbox 실패 FAILED).

---

## Task 6: ReviewConsumer (@KafkaListener)

**Files:** Create `review/ReviewConsumer.java`; Test `review/ReviewConsumerIT.java`

**Interfaces:**
- Consumes: `SandboxRunSubmittedEvent.EVENT_TYPE`("sandbox.run.submitted") 토픽, `ReviewService.reviewRun`, `JsonMapper`.

- [ ] **Step 1: 실패 테스트(EmbeddedKafka)**

`src/test/java/ai/devpath/aigw/review/ReviewConsumerIT.java`:

```java
package ai.devpath.aigw.review;

import static org.awaitility.Awaitility.await;

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
import org.springframework.beans.factory.annotation.Value;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.when;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest
@ActiveProfiles("test")
@EmbeddedKafka(topics = "sandbox.run.submitted", partitions = 1)
class ReviewConsumerIT {

  @Autowired KafkaTemplate<String, String> kafka;
  @Autowired JsonMapper jsonMapper;
  @Autowired AiCodeReviewRepository reviews;
  @MockitoBean SandboxClient sandboxClient;

  @Test
  void consumesEventAndPersistsReview() throws Exception {
    long sid = System.nanoTime();
    when(sandboxClient.getSession(anyLong())).thenReturn(new SandboxSessionView(
        sid, 42L, "PYTHON", null, "print(1)", "1\n", "", 0, "COMPLETED"));
    var event = new SandboxRunSubmittedEvent(UUID.randomUUID(), Instant.now(), 42L, sid, "PYTHON", null);

    kafka.send("sandbox.run.submitted", jsonMapper.writeValueAsString(event));

    await().atMost(Duration.ofSeconds(20)).untilAsserted(() ->
        org.assertj.core.api.Assertions.assertThat(reviews.findBySandboxSessionId(sid)).isPresent());
    reviews.findBySandboxSessionId(sid).ifPresent(reviews::delete);
  }
}
```

> EmbeddedKafka가 `spring.kafka.bootstrap-servers`를 오버라이드하도록 test 설정에 `@EmbeddedKafka` 표준 배선을 따른다(슬라이스 #2 `WelcomeNotificationConsumer` IT 패턴 참조). `KafkaTemplate<String,String>` 빈은 spring-kafka autoconfig가 제공.

- [ ] **Step 2: 실패 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.aigw.review.ReviewConsumerIT"
```

Expected: 컴파일 실패(`ReviewConsumer` 없음) → FAIL.

- [ ] **Step 3: ReviewConsumer 구현** (AssessmentCompletedConsumer 미러: poison skip)

```java
package ai.devpath.aigw.review;

import ai.devpath.shared.event.SandboxRunSubmittedEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

@Component
public class ReviewConsumer {

  private static final Logger log = LoggerFactory.getLogger(ReviewConsumer.class);

  private final ReviewService reviewService;
  private final JsonMapper jsonMapper;

  public ReviewConsumer(ReviewService reviewService, JsonMapper jsonMapper) {
    this.reviewService = reviewService;
    this.jsonMapper = jsonMapper;
  }

  @KafkaListener(topics = SandboxRunSubmittedEvent.EVENT_TYPE, groupId = "devpath-ai-review")
  public void onSandboxRun(String payload) {
    SandboxRunSubmittedEvent event;
    try {
      event = jsonMapper.readValue(payload, SandboxRunSubmittedEvent.class);
    } catch (Exception e) {
      log.warn("SandboxRunSubmittedEvent 역직렬화 실패 — skip: {}", payload, e);
      return; // poison 무한재시도 방지
    }
    reviewService.reviewRun(event.sandboxSessionId(), event.userId(), event.contentId());
  }
}
```

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.aigw.review.ReviewConsumerIT"
git add src/main/java/ai/devpath/aigw/review/ReviewConsumer.java src/test/java/ai/devpath/aigw/review/ReviewConsumerIT.java
git commit -m "feat(ai-svc): Kafka consumer for sandbox.run.submitted (slice6 C1)"
```

---

## Task 7: ReviewController (폴링 + 피드백)

**Files:** Create `review/ReviewController.java`, `review/ReviewNotFoundException.java`; Test `review/ReviewControllerTest.java`

**Interfaces:**
- Produces(프론트 빌드 E가 의존): `GET /reviews?sandboxSessionId={id}` → `CodeReview`(OWNER) / 404. `GET /reviews/{id}` → `CodeReview` / 404. `POST /reviews/{id}/feedback {value:UP|DOWN}` → `CodeReview`. 비소유자 403.

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/aigw/review/ReviewControllerTest.java`:

```java
package ai.devpath.aigw.review;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class ReviewControllerTest {

  @Autowired MockMvc mvc;
  @Autowired AiCodeReviewRepository reviews;

  private long seed(long userId, String status) {
    AiCodeReview r = new AiCodeReview();
    r.setSandboxSessionId(System.nanoTime());
    r.setUserId(userId);
    r.setStatus(status);
    r.setConfidence(80);
    r.setStrengths("[\"good\"]");
    return reviews.save(r).getId();
  }

  @Test
  void getByIdReturnsReviewForOwner() throws Exception {
    long id = seed(42L, "DONE");
    mvc.perform(get("/reviews/" + id).with(jwt().jwt(j -> j.subject("42"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("DONE"))
        .andExpect(jsonPath("$.confidence").value(80))
        .andExpect(jsonPath("$.strengths[0]").value("good"));
    reviews.deleteById(id);
  }

  @Test
  void getByIdForbiddenForNonOwner() throws Exception {
    long id = seed(42L, "DONE");
    mvc.perform(get("/reviews/" + id).with(jwt().jwt(j -> j.subject("999"))))
        .andExpect(status().isForbidden());
    reviews.deleteById(id);
  }

  @Test
  void bySandboxSessionReturnsPendingStatus() throws Exception {
    AiCodeReview r = new AiCodeReview();
    long sid = System.nanoTime();
    r.setSandboxSessionId(sid); r.setUserId(42L); r.setStatus("PENDING");
    reviews.save(r);

    mvc.perform(get("/reviews").param("sandboxSessionId", String.valueOf(sid))
            .with(jwt().jwt(j -> j.subject("42"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("PENDING"));
    reviews.deleteById(r.getId());
  }

  @Test
  void feedbackPersistsUpDown() throws Exception {
    long id = seed(42L, "DONE");
    mvc.perform(post("/reviews/" + id + "/feedback")
            .with(jwt().jwt(j -> j.subject("42")))
            .contentType(MediaType.APPLICATION_JSON).content("{\"value\":\"UP\"}"))
        .andExpect(status().isOk());
    org.assertj.core.api.Assertions.assertThat(reviews.findById(id).orElseThrow().getFeedback())
        .isEqualTo("UP");
    reviews.deleteById(id);
  }

  @Test
  void missingReviewReturns404() throws Exception {
    mvc.perform(get("/reviews/999999999").with(jwt().jwt(j -> j.subject("42"))))
        .andExpect(status().isNotFound());
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.aigw.review.ReviewControllerTest"
```

Expected: 컴파일 실패 → FAIL.

- [ ] **Step 3: NotFound 예외 + Controller 구현**

`review/ReviewNotFoundException.java`:

```java
package ai.devpath.aigw.review;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.NOT_FOUND)
public class ReviewNotFoundException extends RuntimeException {
  public ReviewNotFoundException(String message) { super(message); }
}
```

`review/ReviewController.java`:

```java
package ai.devpath.aigw.review;

import java.util.List;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.json.JsonMapper;

@RestController
@RequestMapping("/reviews")
public class ReviewController {

  private final AiCodeReviewRepository reviews;
  private final JsonMapper jsonMapper;

  public ReviewController(AiCodeReviewRepository reviews, JsonMapper jsonMapper) {
    this.reviews = reviews;
    this.jsonMapper = jsonMapper;
  }

  @GetMapping(params = "sandboxSessionId")
  public CodeReview bySandboxSession(@AuthenticationPrincipal Jwt jwt,
      @RequestParam long sandboxSessionId) {
    long userId = Long.parseLong(jwt.getSubject());
    AiCodeReview r = reviews.findBySandboxSessionId(sandboxSessionId)
        .orElseThrow(() -> new ReviewNotFoundException("review not found for session " + sandboxSessionId));
    requireOwner(r, userId);
    return toDto(r);
  }

  @GetMapping("/{id}")
  public CodeReview byId(@AuthenticationPrincipal Jwt jwt, @PathVariable long id) {
    long userId = Long.parseLong(jwt.getSubject());
    AiCodeReview r = reviews.findById(id)
        .orElseThrow(() -> new ReviewNotFoundException("review not found: " + id));
    requireOwner(r, userId);
    return toDto(r);
  }

  @PostMapping("/{id}/feedback")
  public CodeReview feedback(@AuthenticationPrincipal Jwt jwt, @PathVariable long id,
      @RequestBody FeedbackRequest req) {
    long userId = Long.parseLong(jwt.getSubject());
    AiCodeReview r = reviews.findById(id)
        .orElseThrow(() -> new ReviewNotFoundException("review not found: " + id));
    requireOwner(r, userId);
    if (req == null || (!"UP".equals(req.value()) && !"DOWN".equals(req.value()))) {
      throw new IllegalArgumentException("feedback value must be UP or DOWN");
    }
    r.setFeedback(req.value());
    reviews.save(r);
    return toDto(r);
  }

  private static void requireOwner(AiCodeReview r, long userId) {
    if (r.getUserId() == null || r.getUserId() != userId) {
      throw new AccessDeniedException("not the review owner");
    }
  }

  private CodeReview toDto(AiCodeReview r) {
    return new CodeReview(
        String.valueOf(r.getId()),
        r.getStatus(),
        r.getConfidence() == null ? 0 : r.getConfidence(),
        readList(r.getStrengths(), String.class),
        readList(r.getImprovements(), ReviewIssue.class),
        readList(r.getSecurity(), ReviewIssue.class));
  }

  private <T> List<T> readList(String json, Class<T> type) {
    if (json == null || json.isBlank()) {
      return List.of();
    }
    try {
      return jsonMapper.readValue(json,
          jsonMapper.getTypeFactory().constructCollectionType(List.class, type));
    } catch (Exception e) {
      return List.of();
    }
  }

  public record FeedbackRequest(String value) {}
}
```

- [ ] **Step 4: 통과 확인 + 커밋**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.aigw.review.ReviewControllerTest"
git add src/main/java/ai/devpath/aigw/review/ReviewController.java src/main/java/ai/devpath/aigw/review/ReviewNotFoundException.java src/test/java/ai/devpath/aigw/review/ReviewControllerTest.java
git commit -m "feat(ai-svc): review polling + feedback API (slice6 C1)"
```

Expected: 5 케이스 PASS(소유자 조회·비소유자 403·세션 폴링 PENDING·피드백·404).

---

## Task 8: 전체 회귀 + develop PR

- [ ] **Step 1: 전체 테스트(fresh DB + EmbeddedKafka)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat clean test
```

Expected: 신규 review 테스트 + 기존 `OllamaControllerTest`(MockWebServer)·`AiApplicationTests` 전부 PASS. (기존 Ollama 게이트웨이 무영향.) ⚠️ `AiApplicationTests`가 컨텍스트 로드 시 datasource/kafka를 요구하면 test 프로파일에 fresh DB + EmbeddedKafka 또는 `spring.kafka.bootstrap-servers` 기본값이 필요 — 컨텍스트 로드 실패 시 test yml 보강(추측 금지, 로그 확인).

- [ ] **Step 2: PR 생성(develop 대상)**

```powershell
git push -u origin feat/slice6-ai-review-pipeline
gh pr create --base develop --title "feat(ai-svc): 비동기 코드리뷰 파이프라인+API (Mock provider) 슬라이스 #6 빌드 C1" --body "ReviewConsumer(sandbox.run.submitted)→ReviewService→ai_code_reviews(PENDING/DONE/FAILED, 멱등)+SandboxClient(D-7)+AiReviewClient Mock+폴링/피드백 API. 실 Ollama/Claude는 C2. CI는 Mock(외부 LLM 없음). 설계서 docs/superpowers/specs/2026-06-23-md2-slice6-ai-code-review-design.md"
```

- [ ] **Step 3: CI 녹색 확인 → 머지**

```powershell
gh pr checks --watch
gh pr merge --merge
```

Expected: ai-svc CI(postgres + EmbeddedKafka, Mock provider) 녹색. ⚠️ ai-svc `ci.yml`이 현재 무상태라 postgres service가 없을 수 있음 → 필요 시 ci.yml에 postgres(pgvector) service 추가(learning/sandbox ci.yml 미러). 이 경우 본 PR에 포함.

---

## Self-Review 메모(작성자)

- **Spec 커버리지**: D-1(비동기)=Task6 컨슈머. D-5(ai-svc 일원화)=Task0 deps+모듈. D-7(코드 조회)=Task3 SandboxClient. D-9(멱등)=Task5 createPendingIfAbsent. §5 폴링/피드백 API=Task7. §7 에러(FAILED+error_code)=Task5. **실 LLM 프롬프트·인젝션 방어·골든50=C2**(본 C1 범위 외, Mock으로 파이프라인 검증).
- **placeholder 없음**: 모든 코드/테스트/명령 실제값.
- **타입 일관성**: `CodeReview`(id,status,confidence,strengths,improvements,security)·`ReviewIssue`(message,line,severity)·`ReviewResult`·`ReviewInput`·`AiReviewClient.review/providerName`·`SandboxSessionView`(빌드 B 계약 일치)·`AiCodeReviewRepository.findBySandboxSessionId/existsBySandboxSessionId`가 전 Task·프론트(E)·빌드 B와 일치.
- **자기호출 tx 회피**: tx 메서드는 `ReviewPersistenceService`에 분리, `ReviewService`는 tx 밖에서 LLM 호출(슬라이스 #3/#5 패턴).
- **CI 외부호출 없음**: Mock provider(`matchIfMissing=true`) 기본 → CI 녹색. Ollama/Claude는 C2에서 `devpath.review.provider`로 활성.
- **확인 필요(구현 시)**: ① ai-svc test 프로파일 datasource/kafka 배선(`AiApplicationTests` 컨텍스트) ② ai-svc ci.yml postgres service 추가 여부 — 둘 다 learning-svc 미러로 확인(추측 금지).
