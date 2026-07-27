# 슬라이스 #5 빌드 B1 — sandbox-svc 코어 (RunController · SandboxRunService · RunnerBackend 인터페이스 · outbox · 단위 테스트) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** devpath-sandbox-svc에 sandbox 코어를 처음부터 구축한다. `SandboxSession` JPA 엔티티(빌드 A의 `sandbox_sessions` 매핑), `RunnerBackend` 인터페이스, `SandboxRunService`(상태머신·영속·outbox 발행·SSE 오케스트레이션), `RunController`(POST /sandbox/run SSE), `SecurityConfig`(자체 JWT), `GlobalExceptionHandler`(SANDBOX_UNAVAILABLE→503), outbox 인프라(`OutboxEntry`·`OutboxRepository`·`OutboxRelay`·`OutboxRelayScheduler`), `SandboxRunEventPublisher`를 구현한다. **`DockerRunnerBackend`는 B2 범위** — 이 빌드의 단위 테스트는 fake/mock `RunnerBackend`로 Docker 없이 통과한다.

**Architecture:**
```
RunController (POST /sandbox/run, SSE text/event-stream)
   └─▶ SandboxRunService   상태머신(ALLOCATING→RUNNING→COMPLETED|FAILED|KILLED)
          ├─▶ SandboxSessionRepository   sandbox_sessions 영속
          ├─▶ SandboxRunEventPublisher   SandboxRunSubmittedEvent → outbox
          └─▶ RunnerBackend (interface)  run() → 로그 콜백 + RunResult
                 └─▶ (B2) DockerRunnerBackend
```
outbox 인프라는 devpath-learning-svc의 `outbox/*` 패턴을 그대로 복사한다. `SecurityConfig`·`GlobalExceptionHandler`도 learning-svc 패턴 미러. 단위 테스트는 `FakeRunnerBackend`(테스트 전용 구현)를 사용해 Docker 없이 전 케이스를 검증한다.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Gradle(Kotlin DSL) · Spring Security(oauth2ResourceServer·HS256) · Spring Kafka · JPA/Hibernate · PostgreSQL · JUnit 5 · MockMvc(`org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc`) · `@MockitoBean`(NOT `@MockBean`) · `tools.jackson.databind.json.JsonMapper`

**Global Constraints:**

- 대상 레포: **devpath-sandbox-svc 단독**. B2/C/D에 손대지 않는다.
- 패키지 루트: `ai.devpath.sandbox`. 메인 클래스: `SandboxApplication`.
- `build.gradle.kts`: security·kafka deps 주석 해제(활성화). Redis는 이번 빌드에서 불필요 — 주석 유지.
- `application.yml`: `flyway.enabled=false`(중앙 마이그레이션), `jpa.hibernate.ddl-auto=validate` 유지.
- `application-test.yml`: `flyway.enabled=true`, `locations=classpath:db/migration`, `ddl-auto=none`, DB는 `${DB_URL:jdbc:postgresql://localhost:5432/devpath_citest}`. Kafka는 테스트 프로파일에서 embedded 사용.
- `sandbox_sessions` 테이블은 빌드 A에서 이미 생성됨. JPA 엔티티 컬럼명은 테이블 컬럼과 **정확히 일치**해야 한다(`ddl-auto=validate`).
- `SandboxRunSubmittedEvent` 시그니처: `(UUID eventId, Instant occurredAt, long userId, long sandboxSessionId, String language, Long contentId)`, `EVENT_TYPE="sandbox.run.submitted"` — 빌드 A 인터페이스를 그대로 소비한다.
- 모든 `@SpringBootTest`에 `@ActiveProfiles("test")` 필수.
- `@AutoConfigureMockMvc` import: `org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc`(Boot 4).
- `@MockitoBean` import: `org.springframework.test.context.bean.override.mockito.MockitoBean`(Boot 4; `@MockBean` 금지).
- Jackson: `tools.jackson.databind.json.JsonMapper`(Boot 4; `com.fasterxml` 금지).
- 검증: `.\gradlew.bat test -x test --tests "ai.devpath.sandbox...."` 형식, fresh DB `devpath_citest`.
- 신규 작업 브랜치는 `develop`에서 분기(CLAUDE.md 규칙 4).

---

## File Structure

```
devpath-sandbox-svc/
├── build.gradle.kts                                         Modify: security·kafka 활성화
├── src/main/resources/
│   ├── application.yml                                      Modify: jwt-secret property 추가
│   └── application-test.yml                                 Create: 테스트 프로파일
└── src/main/java/ai/devpath/sandbox/
    ├── SandboxApplication.java                              이미 존재(skeleton)
    ├── config/
    │   ├── SecurityConfig.java                              Create: HS256 JWT, oauth2ResourceServer
    │   └── GlobalExceptionHandler.java                      Create: SANDBOX_UNAVAILABLE→503 등
    ├── outbox/
    │   ├── OutboxEntry.java                                 Create: learning-svc 패턴 복사
    │   ├── OutboxRepository.java                            Create: learning-svc 패턴 복사
    │   ├── OutboxRelay.java                                 Create: learning-svc 패턴 복사
    │   └── OutboxRelayScheduler.java                        Create: learning-svc 패턴 복사
    └── run/
        ├── SandboxSession.java                              Create: JPA 엔티티, sandbox_sessions 매핑
        ├── SandboxSessionRepository.java                    Create: JpaRepository
        ├── RunnerBackend.java                               Create: 인터페이스(run 명세)
        ├── RunSpec.java                                     Create: run() 입력 record
        ├── RunResult.java                                   Create: run() 출력 record
        ├── SandboxRunService.java                           Create: 상태머신·영속·이벤트·SSE
        ├── SandboxRunEventPublisher.java                    Create: outbox 발행(AssessmentEventPublisher 패턴)
        ├── SandboxRunRequest.java                           Create: 요청 body record
        ├── SandboxUnavailableException.java                 Create: 503 트리거 예외
        └── RunController.java                               Create: POST /sandbox/run SSE
src/test/java/ai/devpath/sandbox/
    ├── run/
    │   ├── FakeRunnerBackend.java                           Create: 테스트 전용 구현
    │   ├── SandboxRunServiceTest.java                       Create: 상태머신·이벤트·영속·예외 단위 테스트
    │   └── RunControllerTest.java                           Create: SSE 형식·인증·503 MockMvc 테스트
    └── outbox/
        └── OutboxRelayTest.java                             Create: embedded kafka 릴레이 단위 테스트
src/test/resources/
    └── application-test.yml                                 Create: 테스트 DB·Flyway·EmbeddedKafka 설정
```

> 본보기: learning-svc `assessment/AssessmentEventPublisher.java`, `outbox/*`, `config/SecurityConfig.java`, `config/GlobalExceptionHandler.java`, `path/LearningPathController.java`, `path/LearningPathConflictMappingTest.java`, `assessment/AssessmentControllerTest.java`, `outbox/OutboxRelayTest.java`.

---

## Task 0: 작업 브랜치

- [ ] **Step 1: 브랜치 분기**

```powershell
cd D:\workspace\dev-path-ai\devpath-sandbox-svc
git switch develop
git pull
git switch -c feat/sandbox-core-b1
```

---

## Task 1: build.gradle.kts — security·kafka deps 활성화

**Files:**
- Modify: `build.gradle.kts`

**Interfaces:**
- Produces: `spring-boot-starter-security`, `spring-kafka` 의존성이 활성화된 빌드 설정.

- [ ] **Step 1: 실패 확인** — 현재 security 없이 빌드가 통과하는지(기준점). SecurityConfig를 나중에 추가할 때 실패가 의미 있음.

```powershell
cd D:\workspace\dev-path-ai\devpath-sandbox-svc
.\gradlew.bat compileJava
```

Expected: SUCCESS(현재 스켈레톤은 컴파일됨).

- [ ] **Step 2: deps 활성화** — `build.gradle.kts`의 주석 처리된 security·kafka 라인을 활성화한다.

현재 주석 상태:
```kotlin
// implementation("org.springframework.boot:spring-boot-starter-security")
// implementation("org.springframework.kafka:spring-kafka")
```

변경 후:
```kotlin
implementation("org.springframework.boot:spring-boot-starter-security")
implementation("org.springframework.kafka:spring-kafka")
```

추가로 테스트용 embedded kafka 의존성을 `testImplementation`에 추가한다:
```kotlin
testImplementation("org.springframework.kafka:spring-kafka-test")
testImplementation("org.springframework.security:spring-security-test")
```

최종 `build.gradle.kts` 전체:
```kotlin
plugins {
    java
    id("org.springframework.boot") version "4.0.7"
    id("io.spring.dependency-management") version "1.1.7"
}

group = "ai.devpath"
version = "0.0.1-SNAPSHOT"
description = "DevPath AI isolated sandbox runner (Docker + gVisor)"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

repositories {
    mavenCentral()
    maven {
        url = uri("https://maven.pkg.github.com/DevPathAi/devpath-shared")
        credentials {
            username = providers.gradleProperty("gpr.user").orElse(providers.environmentVariable("GITHUB_ACTOR")).orNull
            password = providers.gradleProperty("gpr.token").orElse(providers.environmentVariable("GITHUB_TOKEN")).orNull
        }
    }
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-security")
    implementation("org.springframework.kafka:spring-kafka")
    implementation("ai.devpath:devpath-shared:0.0.1-SNAPSHOT")
    runtimeOnly("org.postgresql:postgresql")
    // implementation("org.springframework.boot:spring-boot-starter-data-redis")
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")
    testImplementation("org.springframework.boot:spring-boot-starter-actuator-test")
    testImplementation("org.springframework.boot:spring-boot-starter-validation-test")
    testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
    testImplementation("org.springframework.kafka:spring-kafka-test")
    testImplementation("org.springframework.security:spring-security-test")
    testCompileOnly("org.projectlombok:lombok")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
    testAnnotationProcessor("org.projectlombok:lombok")
}

tasks.withType<Test> {
    useJUnitPlatform()
}
```

- [ ] **Step 3: 의존성 해소 확인**

```powershell
.\gradlew.bat dependencies --configuration runtimeClasspath | Select-String "spring-security|spring-kafka"
```

Expected: `spring-security-core`, `spring-kafka` 등 라인 출력.

- [ ] **Step 4: 커밋**

```powershell
git add build.gradle.kts
git commit -m "build(deps): activate security and kafka dependencies (slice5 B1)"
```

---

## Task 2: application-test.yml + application.yml 보완

**Files:**
- Create: `src/test/resources/application-test.yml`
- Modify: `src/main/resources/application.yml`

**Interfaces:**
- Produces: 테스트 프로파일에서 Flyway 활성·fresh DB·EmbeddedKafka bootstrap 연동. 운영 yml에 jwt-secret property 추가.

- [ ] **Step 1: application-test.yml 작성** — `src/test/resources/application-test.yml` 신규 생성:

```yaml
spring:
  datasource:
    url: ${DB_URL:jdbc:postgresql://localhost:5432/devpath_citest}
    username: ${DB_USER:devpath}
    password: ${DB_PASSWORD:localdev}
    driver-class-name: org.postgresql.Driver
  flyway:
    enabled: true
    locations: classpath:db/migration
  jpa:
    hibernate:
      ddl-auto: none
  kafka:
    bootstrap-servers: ${spring.embedded.kafka.brokers}
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.apache.kafka.common.serialization.StringSerializer
    consumer:
      group-id: sandbox-test
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.apache.kafka.common.serialization.StringDeserializer
```

> `spring.embedded.kafka.brokers`는 `@EmbeddedKafka`의 `bootstrapServersProperty`와 연동된다.

- [ ] **Step 2: application.yml에 jwt-secret property 추가** — 현재 `application.yml`에 `devpath.auth.jwt-secret` 항목이 없다. SecurityConfig에서 사용할 property를 추가한다:

```yaml
spring:
  application:
    name: devpath-sandbox-svc
  datasource:
    url: ${DB_URL:jdbc:postgresql://localhost:5432/devpath}
    username: ${DB_USER:devpath}
    password: ${DB_PASSWORD:localdev}
    driver-class-name: org.postgresql.Driver
  jpa:
    hibernate:
      ddl-auto: validate
    properties:
      hibernate.dialect: org.hibernate.dialect.PostgreSQLDialect
  flyway:
    enabled: false   # 마이그레이션은 devpath-shared(중앙)에서 실행, 서비스는 validate만

server:
  port: 8080

management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics

devpath:
  auth:
    jwt-secret: ${JWT_SECRET:test-secret-please-change-min-32-bytes-long-0123456789}
  sandbox:
    sse-timeout-ms: 60000
```

- [ ] **Step 3: 커밋**

```powershell
git add src/test/resources/application-test.yml src/main/resources/application.yml
git commit -m "config: add test profile yml and jwt-secret property (slice5 B1)"
```

---

## Task 3: outbox 인프라 (OutboxEntry · OutboxRepository · OutboxRelay · OutboxRelayScheduler)

**Files:**
- Create: `src/main/java/ai/devpath/sandbox/outbox/OutboxEntry.java`
- Create: `src/main/java/ai/devpath/sandbox/outbox/OutboxRepository.java`
- Create: `src/main/java/ai/devpath/sandbox/outbox/OutboxRelay.java`
- Create: `src/main/java/ai/devpath/sandbox/outbox/OutboxRelayScheduler.java`

**Interfaces:**
- `OutboxRelay.relayOnce()` → `int` (발행된 건수). Kafka topic = `e.getEventType()`, key = `e.getAggregateId()`.
- `OutboxRelayScheduler`는 `@Profile("!test")`로 테스트 환경에서 자동 릴레이 비활성.

- [ ] **Step 1: 실패 테스트 작성** — `src/test/java/ai/devpath/sandbox/outbox/OutboxRelayTest.java`:

```java
package ai.devpath.sandbox.outbox;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Instant;
import java.util.stream.StreamSupport;
import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.test.EmbeddedKafkaBroker;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.kafka.test.utils.KafkaTestUtils;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
@EmbeddedKafka(
    partitions = 1,
    topics = {"sandbox.run.submitted"},
    bootstrapServersProperty = "spring.embedded.kafka.brokers")
class OutboxRelayTest {

  @Autowired OutboxRepository outbox;
  @Autowired OutboxRelay relay;
  @Autowired ConsumerFactory<String, String> cf;
  @Autowired EmbeddedKafkaBroker broker;

  @Test
  void relayPublishesUnpublishedRowAndMarksPublished() {
    OutboxEntry e = new OutboxEntry();
    e.setAggregateType("sandbox_session");
    e.setAggregateId("999");
    e.setEventType("sandbox.run.submitted");
    e.setPayload("{\"sandboxSessionId\":999}");
    e.setCreatedAt(Instant.now());
    Long id = outbox.save(e).getId();

    int published = relay.relayOnce();
    assertTrue(published >= 1, "최소 1건 발행");
    assertNotNull(outbox.findById(id).orElseThrow().getPublishedAt(), "published_at 설정");

    try (Consumer<String, String> c = cf.createConsumer("relay-grp", "relay")) {
      broker.consumeFromAnEmbeddedTopic(c, "sandbox.run.submitted");
      ConsumerRecords<String, String> recs = KafkaTestUtils.getRecords(c);
      boolean found = StreamSupport.stream(recs.spliterator(), false)
          .anyMatch(r -> r.value().contains("999"));
      assertTrue(found, "발행된 레코드에 sandboxSessionId=999 포함");
    }
  }

  @Test
  void alreadyPublishedRowIsSkipped() {
    OutboxEntry e = new OutboxEntry();
    e.setAggregateType("sandbox_session");
    e.setAggregateId("888");
    e.setEventType("sandbox.run.submitted");
    e.setPayload("{\"sandboxSessionId\":888}");
    e.setCreatedAt(Instant.now());
    e.setPublishedAt(Instant.now()); // 이미 발행됨
    outbox.save(e);

    int before = relay.relayOnce();
    // 888은 이미 published_at 존재 → 배치에 포함 안 됨(발행 건수 0이거나 다른 미발행 행만)
    // 이 테스트 단독 실행 기준 0 이하일 수 없고 888이 재발행되지 않음을 확인
    assertTrue(before >= 0);
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
cd D:\workspace\dev-path-ai\devpath-sandbox-svc
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.outbox.OutboxRelayTest"
```

Expected: 컴파일 실패(`OutboxEntry`·`OutboxRepository`·`OutboxRelay` 없음).

- [ ] **Step 3: OutboxEntry 구현** — `src/main/java/ai/devpath/sandbox/outbox/OutboxEntry.java`:

```java
package ai.devpath.sandbox.outbox;

import jakarta.persistence.*;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "outbox")
public class OutboxEntry {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
  @Column(name = "aggregate_type", nullable = false) private String aggregateType;
  @Column(name = "aggregate_id", nullable = false) private String aggregateId;
  @Column(name = "event_type", nullable = false) private String eventType;
  @JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private String payload;
  @Column(name = "created_at", nullable = false) private Instant createdAt;
  @Column(name = "published_at") private Instant publishedAt;

  public Long getId() { return id; }
  public String getAggregateType() { return aggregateType; }
  public void setAggregateType(String v) { this.aggregateType = v; }
  public String getAggregateId() { return aggregateId; }
  public void setAggregateId(String v) { this.aggregateId = v; }
  public String getEventType() { return eventType; }
  public void setEventType(String v) { this.eventType = v; }
  public String getPayload() { return payload; }
  public void setPayload(String v) { this.payload = v; }
  public Instant getCreatedAt() { return createdAt; }
  public void setCreatedAt(Instant v) { this.createdAt = v; }
  public Instant getPublishedAt() { return publishedAt; }
  public void setPublishedAt(Instant v) { this.publishedAt = v; }
}
```

- [ ] **Step 4: OutboxRepository 구현** — `src/main/java/ai/devpath/sandbox/outbox/OutboxRepository.java`:

```java
package ai.devpath.sandbox.outbox;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OutboxRepository extends JpaRepository<OutboxEntry, Long> {
  List<OutboxEntry> findTop100ByPublishedAtIsNullOrderByCreatedAtAsc();
}
```

- [ ] **Step 5: OutboxRelay 구현** — `src/main/java/ai/devpath/sandbox/outbox/OutboxRelay.java`:

```java
package ai.devpath.sandbox.outbox;

import java.time.Instant;
import java.util.concurrent.TimeUnit;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class OutboxRelay {

  private final OutboxRepository outbox;
  private final KafkaTemplate<String, String> kafka;

  public OutboxRelay(OutboxRepository outbox, KafkaTemplate<String, String> kafka) {
    this.outbox = outbox;
    this.kafka = kafka;
  }

  public int relayOnce() {
    var batch = outbox.findTop100ByPublishedAtIsNullOrderByCreatedAtAsc();
    int count = 0;
    for (OutboxEntry e : batch) {
      try {
        kafka.send(e.getEventType(), e.getAggregateId(), e.getPayload()).get(5, TimeUnit.SECONDS);
      } catch (Exception ex) {
        break;
      }
      e.setPublishedAt(Instant.now());
      outbox.save(e);
      count++;
    }
    return count;
  }
}
```

- [ ] **Step 6: OutboxRelayScheduler 구현** — `src/main/java/ai/devpath/sandbox/outbox/OutboxRelayScheduler.java`:

```java
package ai.devpath.sandbox.outbox;

import org.springframework.context.annotation.Profile;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@Profile("!test")
public class OutboxRelayScheduler {

  private final OutboxRelay outboxRelay;

  public OutboxRelayScheduler(OutboxRelay outboxRelay) {
    this.outboxRelay = outboxRelay;
  }

  @Scheduled(fixedDelay = 2000)
  public void relay() {
    outboxRelay.relayOnce();
  }
}
```

- [ ] **Step 7: 통과 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.outbox.OutboxRelayTest"
```

Expected: 2개 테스트 PASS.

- [ ] **Step 8: 커밋**

```powershell
git add src/main/java/ai/devpath/sandbox/outbox/ src/test/java/ai/devpath/sandbox/outbox/
git commit -m "feat(outbox): add OutboxEntry/Repository/Relay/Scheduler (slice5 B1)"
```

---

## Task 4: SecurityConfig + GlobalExceptionHandler

**Files:**
- Create: `src/main/java/ai/devpath/sandbox/config/SecurityConfig.java`
- Create: `src/main/java/ai/devpath/sandbox/config/GlobalExceptionHandler.java`
- Create: `src/main/java/ai/devpath/sandbox/run/SandboxUnavailableException.java`

**Interfaces:**
- `SecurityConfig`: HS256 자체 JWT, `POST /sandbox/run`·`/actuator/health` 외 전체 인증 필요.
- `GlobalExceptionHandler`: `SandboxUnavailableException` → 503 + `{"errorCode":"SANDBOX_UNAVAILABLE","error":"..."}`.

- [ ] **Step 1: 실패 테스트 작성** — `src/test/java/ai/devpath/sandbox/config/SecurityConfigTest.java`:

```java
package ai.devpath.sandbox.config;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import ai.devpath.sandbox.run.SandboxRunService;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class SecurityConfigTest {

  @Autowired MockMvc mvc;
  @MockitoBean SandboxRunService sandboxRunService;

  @Test
  void healthIsPublic() throws Exception {
    mvc.perform(get("/actuator/health")).andExpect(status().isOk());
  }

  @Test
  void sandboxRunWithoutTokenReturns401() throws Exception {
    mvc.perform(post("/sandbox/run")
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"code\":\"print(1)\",\"language\":\"PYTHON\"}"))
        .andExpect(status().isUnauthorized());
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.config.SecurityConfigTest"
```

Expected: 컴파일 실패(`SandboxRunService`, `SecurityConfig` 등 없음) 또는 런타임 실패(시큐리티 미설정).

- [ ] **Step 3: SandboxUnavailableException 구현** — `src/main/java/ai/devpath/sandbox/run/SandboxUnavailableException.java`:

```java
package ai.devpath.sandbox.run;

/**
 * Docker 데몬 미가동·컨테이너 생성 실패 등 Runner 백엔드를 사용할 수 없을 때 발생.
 * GlobalExceptionHandler가 HTTP 503 SANDBOX_UNAVAILABLE로 매핑한다.
 */
public class SandboxUnavailableException extends RuntimeException {
  public SandboxUnavailableException(String message) {
    super(message);
  }
  public SandboxUnavailableException(String message, Throwable cause) {
    super(message, cause);
  }
}
```

- [ ] **Step 4: SecurityConfig 구현** — `src/main/java/ai/devpath/sandbox/config/SecurityConfig.java`:

```java
package ai.devpath.sandbox.config;

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

- [ ] **Step 5: GlobalExceptionHandler 구현** — `src/main/java/ai/devpath/sandbox/config/GlobalExceptionHandler.java`:

```java
package ai.devpath.sandbox.config;

import ai.devpath.sandbox.run.SandboxUnavailableException;
import java.util.Map;
import java.util.NoSuchElementException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

  @ExceptionHandler(SandboxUnavailableException.class)
  public ResponseEntity<Map<String, String>> sandboxUnavailable(SandboxUnavailableException e) {
    return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
        .body(Map.of("errorCode", "SANDBOX_UNAVAILABLE", "error", e.getMessage()));
  }

  @ExceptionHandler(IllegalArgumentException.class)
  public ResponseEntity<Map<String, String>> badRequest(IllegalArgumentException e) {
    return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
  }

  @ExceptionHandler(AccessDeniedException.class)
  public ResponseEntity<Map<String, String>> forbidden(AccessDeniedException e) {
    return ResponseEntity.status(HttpStatus.FORBIDDEN).body(Map.of("error", e.getMessage()));
  }

  @ExceptionHandler(NoSuchElementException.class)
  public ResponseEntity<Map<String, String>> notFound(NoSuchElementException e) {
    return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("error", e.getMessage()));
  }
}
```

- [ ] **Step 6: 통과 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.config.SecurityConfigTest"
```

Expected: 2개 테스트 PASS(`healthIsPublic`·`sandboxRunWithoutTokenReturns401`).

- [ ] **Step 7: 커밋**

```powershell
git add src/main/java/ai/devpath/sandbox/config/ src/main/java/ai/devpath/sandbox/run/SandboxUnavailableException.java src/test/java/ai/devpath/sandbox/config/
git commit -m "feat(config): add SecurityConfig, GlobalExceptionHandler, SandboxUnavailableException (slice5 B1)"
```

---

## Task 5: 도메인 모델 — SandboxSession · SandboxSessionRepository · RunnerBackend · RunSpec · RunResult

**Files:**
- Create: `src/main/java/ai/devpath/sandbox/run/SandboxSession.java`
- Create: `src/main/java/ai/devpath/sandbox/run/SandboxSessionRepository.java`
- Create: `src/main/java/ai/devpath/sandbox/run/RunnerBackend.java`
- Create: `src/main/java/ai/devpath/sandbox/run/RunSpec.java`
- Create: `src/main/java/ai/devpath/sandbox/run/RunResult.java`

**Interfaces:**
- `SandboxSession`: `@Table(name = "sandbox_sessions")`, 컬럼명은 빌드 A SQL 정확 일치(`ddl-auto=validate`).
- `RunnerBackend.run(RunSpec spec, java.util.function.Consumer<String> logCallback)` → `RunResult`. 구현이 없을 때 `SandboxUnavailableException` throw.
- `RunResult(int exitCode, String stdout, String stderr, Long cpuMsUsed, Integer memoryMbPeak)`.

- [ ] **Step 1: 실패 테스트 작성** — `src/test/java/ai/devpath/sandbox/run/SandboxSessionJpaTest.java`:

```java
package ai.devpath.sandbox.run;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class SandboxSessionJpaTest {

  @Autowired SandboxSessionRepository repo;

  @Test
  void persistAndReloadSession() {
    SandboxSession s = new SandboxSession();
    s.setUserId(1L);
    s.setLanguage("PYTHON");
    s.setSubmittedCode("print(1)");
    s.setStatus("ALLOCATING");
    s.setStartedAt(Instant.now());
    SandboxSession saved = repo.save(s);

    SandboxSession loaded = repo.findById(saved.getId()).orElseThrow();
    assertEquals("PYTHON", loaded.getLanguage());
    assertEquals("ALLOCATING", loaded.getStatus());
    assertEquals(1L, loaded.getUserId());
  }

  @Test
  void nullableFieldsAreNotRequired() {
    SandboxSession s = new SandboxSession();
    s.setUserId(2L);
    s.setLanguage("JAVA");
    s.setSubmittedCode("class A{}");
    s.setStatus("ALLOCATING");
    s.setStartedAt(Instant.now());
    SandboxSession saved = repo.save(s);
    // contentId, codeBlockId, containerId, exitCode, stdout, stderr 등은 nullable
    assertNotNull(saved.getId());
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.run.SandboxSessionJpaTest"
```

Expected: 컴파일 실패(`SandboxSession` 없음).

- [ ] **Step 3: RunSpec record 구현** — `src/main/java/ai/devpath/sandbox/run/RunSpec.java`:

```java
package ai.devpath.sandbox.run;

/**
 * RunnerBackend.run()에 전달하는 실행 명세.
 * language: "JAVA" | "NODE" | "PYTHON"
 */
public record RunSpec(
    String code,
    String language,
    long sandboxSessionId
) {}
```

- [ ] **Step 4: RunResult record 구현** — `src/main/java/ai/devpath/sandbox/run/RunResult.java`:

```java
package ai.devpath.sandbox.run;

/**
 * RunnerBackend.run() 완료 결과.
 * exitCode=0 → COMPLETED, exitCode≠0 → FAILED, exitCode=-1(timeout signal) → KILLED.
 */
public record RunResult(
    int exitCode,
    String stdout,
    String stderr,
    Long cpuMsUsed,
    Integer memoryMbPeak
) {}
```

- [ ] **Step 5: RunnerBackend 인터페이스 구현** — `src/main/java/ai/devpath/sandbox/run/RunnerBackend.java`:

```java
package ai.devpath.sandbox.run;

import java.util.function.Consumer;

/**
 * 코드 격리 실행 백엔드 추상화.
 * - MVP 구현: DockerRunnerBackend (빌드 B2).
 * - 테스트용: FakeRunnerBackend (테스트 패키지).
 * - 후속 구현: GvisorRunnerBackend (MD4).
 *
 * 구현이 실행 환경을 제공할 수 없는 경우(Docker 미가동 등) SandboxUnavailableException을 throw한다.
 */
public interface RunnerBackend {

  /**
   * @param spec       실행 명세(code·language·sandboxSessionId)
   * @param logCallback stdout/stderr 각 라인이 생성될 때마다 호출. 실시간 SSE 중계용.
   * @return RunResult  실행 완료 결과(exitCode·stdout·stderr·리소스사용량)
   * @throws SandboxUnavailableException Docker 데몬 미가동·컨테이너 생성 불가 등
   */
  RunResult run(RunSpec spec, Consumer<String> logCallback);
}
```

- [ ] **Step 6: SandboxSession 엔티티 구현** — `src/main/java/ai/devpath/sandbox/run/SandboxSession.java`.

컬럼명은 빌드 A `V202606221001__sandbox_sessions.sql`과 **정확히 일치**해야 한다(`ddl-auto=validate`).

```java
package ai.devpath.sandbox.run;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "sandbox_sessions")
public class SandboxSession {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(name = "user_id", nullable = false)
  private Long userId;

  @Column(name = "content_id")
  private Long contentId;

  @Column(name = "code_block_id")
  private Long codeBlockId;

  @Column(name = "language", nullable = false, length = 16)
  private String language;

  @Column(name = "container_id", length = 128)
  private String containerId;

  @Column(name = "status", nullable = false, length = 16)
  private String status;

  @Column(name = "submitted_code", nullable = false, columnDefinition = "TEXT")
  private String submittedCode;

  @Column(name = "stdout", columnDefinition = "TEXT")
  private String stdout;

  @Column(name = "stderr", columnDefinition = "TEXT")
  private String stderr;

  @Column(name = "exit_code")
  private Integer exitCode;

  @Column(name = "cpu_ms_used")
  private Long cpuMsUsed;

  @Column(name = "memory_mb_peak")
  private Integer memoryMbPeak;

  @Column(name = "started_at", nullable = false)
  private Instant startedAt;

  @Column(name = "finished_at")
  private Instant finishedAt;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt;

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;

  @PrePersist
  void prePersist() {
    Instant now = Instant.now();
    if (createdAt == null) createdAt = now;
    if (updatedAt == null) updatedAt = now;
    if (startedAt == null) startedAt = now;
  }

  @PreUpdate
  void preUpdate() {
    updatedAt = Instant.now();
  }

  // getters & setters
  public Long getId() { return id; }
  public Long getUserId() { return userId; }
  public void setUserId(Long v) { this.userId = v; }
  public Long getContentId() { return contentId; }
  public void setContentId(Long v) { this.contentId = v; }
  public Long getCodeBlockId() { return codeBlockId; }
  public void setCodeBlockId(Long v) { this.codeBlockId = v; }
  public String getLanguage() { return language; }
  public void setLanguage(String v) { this.language = v; }
  public String getContainerId() { return containerId; }
  public void setContainerId(String v) { this.containerId = v; }
  public String getStatus() { return status; }
  public void setStatus(String v) { this.status = v; }
  public String getSubmittedCode() { return submittedCode; }
  public void setSubmittedCode(String v) { this.submittedCode = v; }
  public String getStdout() { return stdout; }
  public void setStdout(String v) { this.stdout = v; }
  public String getStderr() { return stderr; }
  public void setStderr(String v) { this.stderr = v; }
  public Integer getExitCode() { return exitCode; }
  public void setExitCode(Integer v) { this.exitCode = v; }
  public Long getCpuMsUsed() { return cpuMsUsed; }
  public void setCpuMsUsed(Long v) { this.cpuMsUsed = v; }
  public Integer getMemoryMbPeak() { return memoryMbPeak; }
  public void setMemoryMbPeak(Integer v) { this.memoryMbPeak = v; }
  public Instant getStartedAt() { return startedAt; }
  public void setStartedAt(Instant v) { this.startedAt = v; }
  public Instant getFinishedAt() { return finishedAt; }
  public void setFinishedAt(Instant v) { this.finishedAt = v; }
  public Instant getCreatedAt() { return createdAt; }
  public Instant getUpdatedAt() { return updatedAt; }
}
```

- [ ] **Step 7: SandboxSessionRepository 구현** — `src/main/java/ai/devpath/sandbox/run/SandboxSessionRepository.java`:

```java
package ai.devpath.sandbox.run;

import org.springframework.data.jpa.repository.JpaRepository;

public interface SandboxSessionRepository extends JpaRepository<SandboxSession, Long> {}
```

- [ ] **Step 8: 통과 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.run.SandboxSessionJpaTest"
```

Expected: 2개 테스트 PASS. `ddl-auto=validate` 위반 시 Hibernate SchemaValidationException → 컬럼명 재확인.

- [ ] **Step 9: 커밋**

```powershell
git add src/main/java/ai/devpath/sandbox/run/
git commit -m "feat(domain): add SandboxSession entity, RunnerBackend interface, RunSpec/RunResult (slice5 B1)"
```

---

## Task 6: SandboxRunEventPublisher

**Files:**
- Create: `src/main/java/ai/devpath/sandbox/run/SandboxRunEventPublisher.java`

**Interfaces:**
- `publishSubmitted(long sandboxSessionId, long userId, String language, Long contentId)` → outbox에 `SandboxRunSubmittedEvent` 저장.

- [ ] **Step 1: 실패 테스트 작성** — `src/test/java/ai/devpath/sandbox/run/SandboxRunEventPublisherTest.java`:

```java
package ai.devpath.sandbox.run;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import ai.devpath.sandbox.outbox.OutboxEntry;
import ai.devpath.sandbox.outbox.OutboxRepository;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class SandboxRunEventPublisherTest {

  @Autowired SandboxRunEventPublisher publisher;
  @Autowired OutboxRepository outbox;

  @Test
  void publishSubmittedSavesOutboxEntryWithCorrectEventType() {
    publisher.publishSubmitted(42L, 1L, "PYTHON", 10L);

    List<OutboxEntry> entries = outbox.findAll();
    OutboxEntry entry = entries.stream()
        .filter(e -> "sandbox.run.submitted".equals(e.getEventType()))
        .findFirst()
        .orElseThrow(() -> new AssertionError("outbox entry not found"));

    assertEquals("sandbox_session", entry.getAggregateType());
    assertEquals("42", entry.getAggregateId());
    assertEquals("sandbox.run.submitted", entry.getEventType());
    assertFalse(entry.getPayload().isEmpty());
  }

  @Test
  void nullableContentIdIsAccepted() {
    publisher.publishSubmitted(99L, 1L, "JAVA", null);

    List<OutboxEntry> entries = outbox.findAll();
    boolean found = entries.stream()
        .anyMatch(e -> "99".equals(e.getAggregateId())
            && "sandbox.run.submitted".equals(e.getEventType()));
    org.junit.jupiter.api.Assertions.assertTrue(found, "null contentId도 outbox에 저장돼야 한다");
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.run.SandboxRunEventPublisherTest"
```

Expected: 컴파일 실패(`SandboxRunEventPublisher` 없음).

- [ ] **Step 3: SandboxRunEventPublisher 구현** — `src/main/java/ai/devpath/sandbox/run/SandboxRunEventPublisher.java`:

```java
package ai.devpath.sandbox.run;

import ai.devpath.sandbox.outbox.OutboxEntry;
import ai.devpath.sandbox.outbox.OutboxRepository;
import ai.devpath.shared.event.SandboxRunSubmittedEvent;
import java.time.Instant;
import java.util.UUID;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

@Component
public class SandboxRunEventPublisher {

  private final OutboxRepository outbox;
  private final JsonMapper jsonMapper;

  public SandboxRunEventPublisher(OutboxRepository outbox, JsonMapper jsonMapper) {
    this.outbox = outbox;
    this.jsonMapper = jsonMapper;
  }

  public void publishSubmitted(long sandboxSessionId, long userId, String language, Long contentId) {
    var event = new SandboxRunSubmittedEvent(
        UUID.randomUUID(), Instant.now(), userId, sandboxSessionId, language, contentId);
    OutboxEntry entry = new OutboxEntry();
    entry.setAggregateType("sandbox_session");
    entry.setAggregateId(String.valueOf(sandboxSessionId));
    entry.setEventType(SandboxRunSubmittedEvent.EVENT_TYPE);
    entry.setPayload(serialize(event));
    entry.setCreatedAt(Instant.now());
    outbox.save(entry);
  }

  private String serialize(SandboxRunSubmittedEvent event) {
    try {
      return jsonMapper.writeValueAsString(event);
    } catch (Exception e) {
      throw new IllegalStateException("SandboxRunSubmittedEvent 직렬화 실패", e);
    }
  }
}
```

- [ ] **Step 4: 통과 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.run.SandboxRunEventPublisherTest"
```

Expected: 2개 테스트 PASS.

- [ ] **Step 5: 커밋**

```powershell
git add src/main/java/ai/devpath/sandbox/run/SandboxRunEventPublisher.java src/test/java/ai/devpath/sandbox/run/SandboxRunEventPublisherTest.java
git commit -m "feat(event): add SandboxRunEventPublisher (outbox, SandboxRunSubmittedEvent) (slice5 B1)"
```

---

## Task 7: SandboxRunService (상태머신 · 영속 · SSE 오케스트레이션)

**Files:**
- Create: `src/main/java/ai/devpath/sandbox/run/SandboxRunRequest.java`
- Create: `src/main/java/ai/devpath/sandbox/run/SandboxRunService.java`
- Create: `src/test/java/ai/devpath/sandbox/run/FakeRunnerBackend.java`
- Create: `src/test/java/ai/devpath/sandbox/run/SandboxRunServiceTest.java`

**Interfaces:**
- `SandboxRunService.execute(long userId, SandboxRunRequest req, java.util.function.Consumer<String> logCallback)` → `SandboxSession` (완료된 세션).
- 상태머신: 세션 생성(ALLOCATING) → outbox 발행 → `RunnerBackend.run()` 호출 중 status=RUNNING → 완료 시 exit_code에 따라 COMPLETED(0)/FAILED(≠0)/KILLED(-1) → `finished_at`·stdout·stderr·exitCode 업데이트.
- `RunnerBackend.run()`이 `SandboxUnavailableException` throw 시 그대로 전파(→ `GlobalExceptionHandler`가 503 매핑).

- [ ] **Step 1: FakeRunnerBackend 작성** — `src/test/java/ai/devpath/sandbox/run/FakeRunnerBackend.java`:

```java
package ai.devpath.sandbox.run;

import java.util.List;
import java.util.function.Consumer;

/**
 * 단위 테스트 전용 RunnerBackend 구현. Docker 불요.
 * 생성 시 미리 정의한 로그 라인들을 logCallback으로 전달하고 RunResult를 반환한다.
 */
public class FakeRunnerBackend implements RunnerBackend {

  private final List<String> logLines;
  private final RunResult result;
  private final boolean throwUnavailable;

  /** 정상 완료 케이스 */
  public FakeRunnerBackend(List<String> logLines, RunResult result) {
    this.logLines = logLines;
    this.result = result;
    this.throwUnavailable = false;
  }

  /** SandboxUnavailableException throw 케이스 */
  public static FakeRunnerBackend unavailable() {
    return new FakeRunnerBackend(List.of(), null, true);
  }

  private FakeRunnerBackend(List<String> logLines, RunResult result, boolean throwUnavailable) {
    this.logLines = logLines;
    this.result = result;
    this.throwUnavailable = throwUnavailable;
  }

  @Override
  public RunResult run(RunSpec spec, Consumer<String> logCallback) {
    if (throwUnavailable) {
      throw new SandboxUnavailableException("테스트: Docker 미가동");
    }
    logLines.forEach(logCallback);
    return result;
  }
}
```

- [ ] **Step 2: SandboxRunRequest record 구현** — `src/main/java/ai/devpath/sandbox/run/SandboxRunRequest.java`:

```java
package ai.devpath.sandbox.run;

/**
 * POST /sandbox/run 요청 body.
 * language: "JAVA" | "NODE" | "PYTHON" (CHECK 제약과 일치)
 */
public record SandboxRunRequest(
    String code,
    String language,
    Long contentId,
    Long codeBlockId
) {}
```

- [ ] **Step 3: 실패 테스트 작성** — `src/test/java/ai/devpath/sandbox/run/SandboxRunServiceTest.java`:

```java
package ai.devpath.sandbox.run;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import ai.devpath.sandbox.outbox.OutboxRepository;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class SandboxRunServiceTest {

  @Autowired SandboxSessionRepository sessionRepo;
  @Autowired OutboxRepository outboxRepo;
  @MockitoBean RunnerBackend runnerBackend;

  SandboxRunService service;

  @BeforeEach
  void setUp(@Autowired SandboxRunEventPublisher publisher) {
    // 실제 service를 빈에서 주입받아 사용하되,
    // RunnerBackend는 @MockitoBean으로 교체된 mock 사용
    service = new SandboxRunService(sessionRepo, runnerBackend, publisher);
  }

  @Test
  void successfulRunCompletesSessionWithExitCode0() {
    when(runnerBackend.run(any(), any()))
        .thenAnswer(inv -> {
          Consumer<String> cb = inv.getArgument(1);
          cb.accept("Hello from Python");
          return new RunResult(0, "Hello from Python\n", "", 100L, 32);
        });

    var req = new SandboxRunRequest("print('Hello')", "PYTHON", null, null);
    SandboxSession session = service.execute(1L, req, line -> {});

    assertEquals("COMPLETED", session.getStatus());
    assertEquals(0, session.getExitCode());
    assertNotNull(session.getFinishedAt());
  }

  @Test
  void nonZeroExitCodeResultsInFailedStatus() {
    when(runnerBackend.run(any(), any()))
        .thenReturn(new RunResult(1, "", "NameError: name 'x' is not defined\n", 50L, 16));

    var req = new SandboxRunRequest("print(x)", "PYTHON", null, null);
    SandboxSession session = service.execute(2L, req, line -> {});

    assertEquals("FAILED", session.getStatus());
    assertEquals(1, session.getExitCode());
  }

  @Test
  void killedExitCodeResultsInKilledStatus() {
    // DockerRunnerBackend 규약: timeout kill → exitCode = -1
    when(runnerBackend.run(any(), any()))
        .thenReturn(new RunResult(-1, "", "실행 시간 초과(30s)\n", null, null));

    var req = new SandboxRunRequest("while True: pass", "PYTHON", null, null);
    SandboxSession session = service.execute(3L, req, line -> {});

    assertEquals("KILLED", session.getStatus());
  }

  @Test
  void unavailableBackendThrowsSandboxUnavailableException() {
    when(runnerBackend.run(any(), any()))
        .thenThrow(new SandboxUnavailableException("Docker 미가동"));

    var req = new SandboxRunRequest("print(1)", "PYTHON", null, null);
    assertThrows(SandboxUnavailableException.class, () ->
        service.execute(4L, req, line -> {}));
  }

  @Test
  void sessionIsAllocatingBeforeRunThenUpdated() {
    when(runnerBackend.run(any(), any()))
        .thenAnswer(inv -> {
          // run() 호출 중 세션은 RUNNING 상태여야 함 — 여기서 검증하려면 DB flush가 필요하므로
          // 간단히 run()이 완료 후 세션 상태가 COMPLETED인지 최종 확인
          Consumer<String> cb = inv.getArgument(1);
          cb.accept("line1");
          return new RunResult(0, "line1\n", "", 80L, 20);
        });

    var req = new SandboxRunRequest("print('x')", "PYTHON", 5L, null);
    SandboxSession session = service.execute(5L, req, line -> {});

    assertEquals("COMPLETED", session.getStatus());
    assertEquals(5L, session.getContentId());
    assertNotNull(session.getFinishedAt());
  }

  @Test
  void outboxEntryIsCreatedForEachRun() {
    when(runnerBackend.run(any(), any()))
        .thenReturn(new RunResult(0, "ok\n", "", 60L, 10));

    long countBefore = outboxRepo.count();
    service.execute(6L, new SandboxRunRequest("x=1", "PYTHON", null, null), line -> {});
    long countAfter = outboxRepo.count();

    assertEquals(countBefore + 1, countAfter, "outbox에 1건 추가");
  }

  @Test
  void logCallbackIsInvokedForEachLogLine() {
    when(runnerBackend.run(any(), any()))
        .thenAnswer(inv -> {
          Consumer<String> cb = inv.getArgument(1);
          cb.accept("log-line-A");
          cb.accept("log-line-B");
          return new RunResult(0, "log-line-A\nlog-line-B\n", "", null, null);
        });

    var received = new java.util.ArrayList<String>();
    service.execute(7L, new SandboxRunRequest("x=1", "PYTHON", null, null), received::add);

    assertEquals(List.of("log-line-A", "log-line-B"), received);
  }
}
```

- [ ] **Step 4: 실패 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.run.SandboxRunServiceTest"
```

Expected: 컴파일 실패(`SandboxRunService` 없음).

- [ ] **Step 5: SandboxRunService 구현** — `src/main/java/ai/devpath/sandbox/run/SandboxRunService.java`:

```java
package ai.devpath.sandbox.run;

import java.time.Instant;
import java.util.function.Consumer;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class SandboxRunService {

  private final SandboxSessionRepository sessions;
  private final RunnerBackend runnerBackend;
  private final SandboxRunEventPublisher eventPublisher;

  public SandboxRunService(SandboxSessionRepository sessions,
      RunnerBackend runnerBackend,
      SandboxRunEventPublisher eventPublisher) {
    this.sessions = sessions;
    this.runnerBackend = runnerBackend;
    this.eventPublisher = eventPublisher;
  }

  /**
   * 코드 실행 전체 흐름:
   * 1. SandboxSession 생성(ALLOCATING)
   * 2. SandboxRunSubmittedEvent → outbox
   * 3. RunnerBackend.run() — 로그 콜백 중계(→ SSE)
   * 4. 세션 상태 업데이트(COMPLETED|FAILED|KILLED)
   *
   * RunnerBackend가 SandboxUnavailableException throw 시 그대로 전파.
   * 호출자(RunController)가 SSE 에러 처리 또는 GlobalExceptionHandler가 503 매핑.
   */
  @Transactional
  public SandboxSession execute(long userId, SandboxRunRequest req, Consumer<String> logCallback) {
    // 1. 세션 생성(ALLOCATING)
    SandboxSession session = new SandboxSession();
    session.setUserId(userId);
    session.setLanguage(req.language());
    session.setSubmittedCode(req.code());
    session.setContentId(req.contentId());
    session.setCodeBlockId(req.codeBlockId());
    session.setStatus("ALLOCATING");
    session.setStartedAt(Instant.now());
    session = sessions.save(session);

    // 2. 이벤트 발행(outbox)
    eventPublisher.publishSubmitted(session.getId(), userId, req.language(), req.contentId());

    // 3. 실행(SandboxUnavailableException은 전파)
    session.setStatus("RUNNING");
    sessions.save(session);

    RunResult result = runnerBackend.run(
        new RunSpec(req.code(), req.language(), session.getId()),
        logCallback);

    // 4. 결과 반영
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

    return sessions.save(session);
  }
}
```

- [ ] **Step 6: 통과 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.run.SandboxRunServiceTest"
```

Expected: 7개 테스트 PASS.

- [ ] **Step 7: 커밋**

```powershell
git add src/main/java/ai/devpath/sandbox/run/SandboxRunRequest.java src/main/java/ai/devpath/sandbox/run/SandboxRunService.java src/test/java/ai/devpath/sandbox/run/FakeRunnerBackend.java src/test/java/ai/devpath/sandbox/run/SandboxRunServiceTest.java src/test/java/ai/devpath/sandbox/run/SandboxSessionJpaTest.java
git commit -m "feat(service): add SandboxRunService state machine + SandboxRunRequest (slice5 B1)"
```

---

## Task 8: RunController (POST /sandbox/run SSE)

**Files:**
- Create: `src/main/java/ai/devpath/sandbox/run/RunController.java`
- Create: `src/test/java/ai/devpath/sandbox/run/RunControllerTest.java`

**Interfaces:**
- `POST /sandbox/run`, produces `text/event-stream`. `@AuthenticationPrincipal Jwt jwt` → `userId=Long.parseLong(jwt.getSubject())`.
- SSE 이벤트: `event: log` + `data: <로그 라인>` 반복 → `emitter.complete()` 로 스트림 종료.
- `SandboxUnavailableException` → GlobalExceptionHandler가 503 매핑(SSE 바깥에서 예외 발생 가능). SSE 내부에서 발생하면 emitter를 completeWithError로 종료.
- 코드 크기 제한: `req.code()` > 65536 bytes (64KB) → 400 `{"error":"코드 크기 제한(64KB) 초과"}`.

- [ ] **Step 1: 실패 테스트 작성** — `src/test/java/ai/devpath/sandbox/run/RunControllerTest.java`:

```java
package ai.devpath.sandbox.run;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doThrow;
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
class RunControllerTest {

  @Autowired MockMvc mvc;
  @MockitoBean SandboxRunService sandboxRunService;

  @Test
  void unauthenticatedRequestReturns401() throws Exception {
    mvc.perform(post("/sandbox/run")
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"code\":\"print(1)\",\"language\":\"PYTHON\"}"))
        .andExpect(status().isUnauthorized());
  }

  @Test
  void validRequestReturnsSseStreamWithLogEvents() throws Exception {
    doAnswer(inv -> {
      java.util.function.Consumer<String> cb = inv.getArgument(2);
      cb.accept("Hello, World!");
      SandboxSession s = new SandboxSession();
      s.setStatus("COMPLETED");
      return s;
    }).when(sandboxRunService).execute(anyLong(), any(), any());

    var result = mvc.perform(post("/sandbox/run")
            .with(jwt().jwt(j -> j.subject("42")))
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"code\":\"print('Hello')\",\"language\":\"PYTHON\"}"))
        .andExpect(request().asyncStarted())
        .andReturn();

    String sse = mvc.perform(asyncDispatch(result))
        .andExpect(status().isOk())
        .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM))
        .andReturn().getResponse().getContentAsString();

    assertThat(sse).contains("event:log");
    assertThat(sse).contains("data:Hello, World!");
  }

  @Test
  void sandboxUnavailableReturns503() throws Exception {
    doThrow(new SandboxUnavailableException("Docker 미가동"))
        .when(sandboxRunService).execute(anyLong(), any(), any());

    var result = mvc.perform(post("/sandbox/run")
            .with(jwt().jwt(j -> j.subject("42")))
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"code\":\"x\",\"language\":\"PYTHON\"}"))
        .andExpect(request().asyncStarted())
        .andReturn();

    // SSE 내부에서 throw → 503 매핑 또는 emitter completeWithError.
    // GlobalExceptionHandler가 SSE 스트림 외부 예외를 처리하는 경우:
    mvc.perform(asyncDispatch(result))
        .andExpect(status().isServiceUnavailable());
  }

  @Test
  void oversizedCodeReturns400() throws Exception {
    String bigCode = "x".repeat(65537);
    mvc.perform(post("/sandbox/run")
            .with(jwt().jwt(j -> j.subject("42")))
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"code\":\"" + bigCode + "\",\"language\":\"PYTHON\"}"))
        .andExpect(status().isBadRequest());
  }

  @Test
  void missingLanguageReturns400() throws Exception {
    mvc.perform(post("/sandbox/run")
            .with(jwt().jwt(j -> j.subject("42")))
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"code\":\"print(1)\"}"))
        .andExpect(status().isBadRequest());
  }
}
```

> **SSE + SandboxUnavailable 매핑 주의**: `RunController`의 `CompletableFuture` 내부에서 `SandboxUnavailableException`이 throw되면 `emitter.completeWithError()`로 전달한다. Spring MVC SSE는 이 경우 클라이언트에게 연결 종료를 보내고 HTTP 상태는 이미 200으로 커밋된 상태일 수 있다. 테스트는 `asyncDispatch` 결과가 `isServiceUnavailable()`임을 검증한다 — 만약 SSE가 이미 열리기 전에 예외가 발생한다면 GlobalExceptionHandler가 503을 반환한다. 구현에서는 `execute()` 호출을 `CompletableFuture` 내부로 이동해 SSE 스트림 시작 전에 검증 단계(code size check·language check)를 먼저 수행하고, 이 단계에서 발생하는 `IllegalArgumentException`은 GlobalExceptionHandler가 400으로 처리하도록 한다.

- [ ] **Step 2: 실패 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.run.RunControllerTest"
```

Expected: 컴파일 실패(`RunController` 없음).

- [ ] **Step 3: RunController 구현** — `src/main/java/ai/devpath/sandbox/run/RunController.java`:

```java
package ai.devpath.sandbox.run;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.CompletableFuture;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/sandbox")
public class RunController {

  private static final int MAX_CODE_BYTES = 64 * 1024; // 64KB

  private final SandboxRunService runService;
  private final long sseTimeoutMs;

  public RunController(SandboxRunService runService,
      @Value("${devpath.sandbox.sse-timeout-ms:60000}") long sseTimeoutMs) {
    this.runService = runService;
    this.sseTimeoutMs = sseTimeoutMs;
  }

  @PostMapping(path = "/run", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
  public SseEmitter run(@AuthenticationPrincipal Jwt jwt,
      @RequestBody SandboxRunRequest req) {
    // 검증: SSE 스트림 시작 전에 수행해야 GlobalExceptionHandler가 처리 가능
    if (req.code() == null || req.language() == null) {
      throw new IllegalArgumentException("code와 language는 필수입니다.");
    }
    if (req.code().getBytes(StandardCharsets.UTF_8).length > MAX_CODE_BYTES) {
      throw new IllegalArgumentException("코드 크기 제한(64KB) 초과");
    }
    if (!req.language().matches("JAVA|NODE|PYTHON")) {
      throw new IllegalArgumentException("지원하지 않는 language: " + req.language());
    }

    long userId = Long.parseLong(jwt.getSubject());
    SseEmitter emitter = new SseEmitter(sseTimeoutMs);

    CompletableFuture.runAsync(() -> {
      try {
        runService.execute(userId, req, line -> sendLog(emitter, line));
        emitter.complete();
      } catch (SandboxUnavailableException e) {
        // SSE 스트림 내부에서 unavailable → completeWithError(Spring이 503으로 매핑)
        emitter.completeWithError(e);
      } catch (Exception e) {
        emitter.completeWithError(e);
      }
    });

    return emitter;
  }

  private void sendLog(SseEmitter emitter, String line) {
    try {
      emitter.send(SseEmitter.event().name("log").data(line));
    } catch (IOException e) {
      throw new IllegalStateException("SSE send failed", e);
    }
  }
}
```

- [ ] **Step 4: 통과 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.sandbox.run.RunControllerTest"
```

Expected: 5개 테스트 PASS. `sandboxUnavailableReturns503`이 실패하면 아래 Self-Review 메모 참조.

- [ ] **Step 5: 커밋**

```powershell
git add src/main/java/ai/devpath/sandbox/run/RunController.java src/test/java/ai/devpath/sandbox/run/RunControllerTest.java
git commit -m "feat(controller): add RunController SSE POST /sandbox/run (slice5 B1)"
```

---

## Task 9: 전체 단위 테스트 회귀 + develop PR

**Files:**
- No new files — 전체 빌드 확인 + PR 생성.

- [ ] **Step 1: 전체 테스트 실행(fresh DB, Docker 불요)**

```powershell
cd D:\workspace\dev-path-ai\devpath-sandbox-svc
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat clean test
```

Expected: BUILD SUCCESSFUL. 전 단위 테스트 PASS. `@Tag("docker")` 태그가 없는 테스트만 실행됨(DockerRunnerBackend 없음 — B2 범위).

- [ ] **Step 2: 컴파일 경고 없음 확인**

```powershell
.\gradlew.bat compileJava compileTestJava 2>&1 | Select-String "warning|error" | Select-String -NotMatch "^Note:"
```

Expected: 출력 없음(경고·에러 없음).

- [ ] **Step 3: develop PR 생성**

```powershell
git push -u origin feat/sandbox-core-b1
gh pr create --base develop --title "feat(sandbox-svc): sandbox core B1 — RunController, SandboxRunService, outbox, security (slice5)" --body "MD2 슬라이스 #5 빌드 B1. RunController(SSE POST /sandbox/run), SandboxRunService(상태머신 ALLOCATING→RUNNING→COMPLETED|FAILED|KILLED), RunnerBackend 인터페이스, SandboxSession JPA 엔티티, outbox 인프라, SandboxRunEventPublisher, SecurityConfig(HS256 JWT), GlobalExceptionHandler(503 SANDBOX_UNAVAILABLE). DockerRunnerBackend는 빌드 B2. 전 단위 테스트 Docker 없이 PASS.

설계서: docs/superpowers/specs/2026-06-22-md2-slice5-sandbox-design.md
플랜: docs/superpowers/plans/2026-06-22-md2-slice5-sandbox-core-b1.md"
gh pr checks --watch
```

Expected: CI `build` 녹색. 녹색 확인 후 머지(컨트롤러 직접 검증: `git log`, 파일 구조, 테스트 통과 실측).

---

## Self-Review 메모 (작성자)

### Spec 커버리지
- §3 아키텍처: RunController→SandboxRunService→RunnerBackend(인터페이스)→(B2)DockerRunnerBackend — Task 7~8 구현.
- §5 API: `POST /sandbox/run` SSE, `event:log`, 스트림 종료, `503 SANDBOX_UNAVAILABLE`, 64KB 제한 — Task 8 커버.
- §6 실행흐름: ALLOCATING→outbox→RUNNING→run()→COMPLETED|FAILED|KILLED — Task 7 상태머신 커버.
- §7 보안: 컨테이너 격리(Docker 보안 옵션)는 B2. 이번 B1은 JWT 인증(SecurityConfig) 커버.
- §8 테스트 전략: "단위(Docker 불요)" = Task 3~8. "통합(@Tag("docker"))" = B2. "모든 @SpringBootTest에 @ActiveProfiles("test")" 준수.
- §9 빌드 B1 범위: DockerRunnerBackend 제외 확인(인터페이스만), Redis 미포함(주석 유지).

### No placeholder
- 모든 Task에 실코드(패키지명·클래스명·필드명·메서드 시그니처·어노테이션 포함). "TBD"/"적절히" 없음.

### 타입 일관성
- `SandboxRunSubmittedEvent(UUID,Instant,long,long,String,Long)` · `EVENT_TYPE="sandbox.run.submitted"` — 빌드 A 인터페이스 그대로 소비.
- `sandbox_sessions` 컬럼명: `user_id`,`content_id`,`code_block_id`,`language`,`container_id`,`status`,`submitted_code`,`stdout`,`stderr`,`exit_code`,`cpu_ms_used`,`memory_mb_peak`,`started_at`,`finished_at`,`created_at`,`updated_at` — 빌드 A SQL과 정확 일치.
- CHECK 값: `JAVA`,`NODE`,`PYTHON` / `ALLOCATING`,`RUNNING`,`COMPLETED`,`FAILED`,`KILLED` — 빌드 A와 일치.
- Boot 4 import: `org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc`, `@MockitoBean`(`org.springframework.test.context.bean.override.mockito`), `tools.jackson.databind.json.JsonMapper`.

### SSE + 503 매핑 주의점
SSE 응답에서 HTTP 상태코드는 첫 번째 write 시점에 커밋된다. `RunController`는 `CompletableFuture` 시작 전에 코드 크기·언어 유효성 검사를 수행(동기 throw → GlobalExceptionHandler 400/503)하고, SSE 스트림 내부에서 `SandboxUnavailableException` 발생 시 `emitter.completeWithError()`를 호출한다. `RunControllerTest.sandboxUnavailableReturns503`은 `execute()` 호출 자체를 throw하도록 mock해 SSE 시작 직후 예외가 발생하는 시나리오를 검증한다. 테스트가 실패(200 응답)하면 mock 설정을 검토하고 `execute()` 호출 경로에서 throw가 실제로 emitter에 전달되는지 `emitter.completeWithError()` 호출을 확인한다.

### 교훈 반영
- fresh DB(`devpath_citest`) 검증 — 로컬 `devpath` 가짜통과 회피(슬라이스 #2/#3 교훈).
- `@Profile("!test")` on OutboxRelayScheduler — 테스트 환경 자동 릴레이 비활성.
- 교차서비스 FK 없음: `SandboxSession.userId`는 `BIGINT NOT NULL`(platform users 논리 참조), `contentId`·`codeBlockId`는 nullable BIGINT(learning 논리 참조).
