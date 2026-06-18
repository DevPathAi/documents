# 슬라이스 #2 빌드 B-2 — learning-svc 이벤트 발행 + guest Redis + claim Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** learning-svc에 outbox→Kafka 이벤트 발행(`AssessmentCompletedEvent`), 비회원(guest) Redis 진단 세션, 회원 귀속(claim), 진단 문항 시드를 추가한다. (B-1의 엔진·회원 API 위에 얹는다.)

**Architecture:** 슬라이스 #1 platform-svc 2b 패턴 그대로 — Transactional Outbox(도메인 tx 동일 커밋으로 이벤트 적재) + `OutboxRelay`(send-ack 후 published) + `@Profile("!test")` 스케줄러. guest는 회원과 동일 `AdaptiveEngine`/`NextQuestionSelector`를 쓰되 상태를 Redis(JSON, TTL 30분)에 둔다. claim은 Redis 세션을 DB로 이행하고 이벤트를 발행한다.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Spring Data Redis · Spring Kafka(+`spring-boot-kafka` autoconfig) · Jackson 3(`tools.jackson.databind.json.JsonMapper`) · JUnit 5 · EmbeddedKafka · Awaitility · `ai.devpath:devpath-shared`(빌드 A).

## Global Constraints

- 레포 절대조건: 추측 금지 · **테스트 우선** · 문제 시 코드 분석.
- 브랜치: develop 분기 → develop PR, CI 녹색 후 merge commit.
- **선행**: 빌드 B-1 develop 머지 완료(엔티티·엔진·회원 API 존재). 빌드 A shared main 릴리스로 `AssessmentCompletedEvent` 소비 가능.
- **Boot 4 = Jackson 3**: 이벤트 직렬화/역직렬화는 `tools.jackson.databind.json.JsonMapper`(Boot가 빈 자동등록). `org.springframework.boot:spring-boot-kafka` autoconfig 모듈 필요. 모든 `@SpringBootTest`에 `@ActiveProfiles("test")`.
- 이벤트: 클래스 `ai.devpath.shared.event.AssessmentCompletedEvent`, 토픽=`AssessmentCompletedEvent.EVENT_TYPE`(`learning.assessment.completed`). payload는 JsonMapper 직렬화 문자열.
- outbox 릴레이는 platform과 동일: `relayOnce()` send 후 `get(5s)` 성공 시에만 published, 실패 시 break(순서보장). 스케줄러 `@Profile("!test") @Scheduled(fixedDelay=2000)`.
- guest 세션: Redis 키 `assessment:guest:{guestId}`, **TTL 30분, 매 answer마다 갱신**. guestId=UUID. 만료/부재 시 404.
- claim 멱등: 이미 이행된 guestId 재요청은 기존 assessmentId 반환(중복 DB행·중복 이벤트 금지).

---

## File Structure

- Modify: `build.gradle.kts` — redis, kafka 의존성
- Modify: `src/main/resources/application.yml` — kafka producer, redis
- Modify: `src/test/resources/application-test.yml` — (kafka는 EmbeddedKafka가 오버라이드)
- Create: `.../outbox/OutboxEntry.java`, `OutboxRepository.java`, `OutboxRelay.java`, `OutboxRelayScheduler.java` (platform 2b 패턴 복사, 패키지만 learning)
- Create: `.../assessment/AssessmentEventPublisher.java` — 이벤트 outbox 적재
- Modify: `.../assessment/AssessmentService.java` — `complete()`에서 이벤트 적재 + concept 집계
- Create: `.../assessment/guest/GuestSession.java` — Redis 직렬화 모델(record)
- Create: `.../assessment/guest/GuestSessionStore.java` — Redis CRUD(TTL)
- Create: `.../assessment/guest/GuestAssessmentService.java` — guest 진단 유스케이스
- Create: `.../assessment/guest/GuestAssessmentController.java` — guest 엔드포인트
- Create: `.../assessment/claim/ClaimService.java`, `ClaimController.java`
- Create: `src/main/java/ai/devpath/learning/seed/QuestionBankSeeder.java` — dev 프로파일 시드
- Create: `src/test/resources/seed/question_bank_seed.sql` — 테스트/로컬 시드 SQL
- Tests: `OutboxRelayTest`, `AssessmentEventPropagationIT`, `GuestAssessmentControllerTest`, `ClaimControllerTest`

---

## Task 1: 의존성·설정 (Redis, Kafka)

**Files:** `build.gradle.kts`, `src/main/resources/application.yml`

- [ ] **Step 1: build.gradle.kts 의존성 추가**

```kotlin
	implementation("org.springframework.boot:spring-boot-starter-data-redis")
	implementation("org.springframework.kafka:spring-kafka")
	implementation("org.springframework.boot:spring-boot-kafka")
	testImplementation("org.springframework.kafka:spring-kafka-test")
	testImplementation("org.awaitility:awaitility")
```

- [ ] **Step 2: application.yml에 kafka·redis 추가**

`src/main/resources/application.yml`의 `spring:` 하위에 추가(platform 패턴):

```yaml
  kafka:
    bootstrap-servers: ${KAFKA_BOOTSTRAP:localhost:9092}
    consumer:
      group-id: devpath-learning
      auto-offset-reset: earliest
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.apache.kafka.common.serialization.StringSerializer
  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: ${REDIS_PORT:6379}
```

- [ ] **Step 3: 컴파일 확인 + 커밋**

```bash
./gradlew compileJava
git add build.gradle.kts src/main/resources/application.yml
git commit -m "chore(deps): learning-svc redis·kafka 의존성·설정"
```

---

## Task 2: Outbox 인프라 (platform 2b 패턴 복사)

> platform-svc `ai.devpath.platform.outbox` 4파일을 `ai.devpath.learning.outbox`로 패키지만 바꿔 복사. 동작·시그니처 동일.

**Files:**
- Create: `.../outbox/OutboxEntry.java`, `OutboxRepository.java`, `OutboxRelay.java`, `OutboxRelayScheduler.java`
- Create: `src/test/java/ai/devpath/learning/outbox/OutboxRelayTest.java`

**Interfaces:**
- Produces: `OutboxEntry`(aggregateType/aggregateId/eventType/payload/createdAt/publishedAt), `OutboxRepository.findTop100ByPublishedAtIsNullOrderByCreatedAtAsc()`, `OutboxRelay.relayOnce():int`.

- [ ] **Step 1: OutboxRelay 발행 실패 테스트 작성**

`OutboxRelayTest.java` (platform OutboxRelayTest와 동일, 토픽만 진단 이벤트):

```java
package ai.devpath.learning.outbox;

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
@EmbeddedKafka(partitions = 1, topics = {"learning.assessment.completed"}, bootstrapServersProperty = "spring.kafka.bootstrap-servers")
class OutboxRelayTest {

  @Autowired OutboxRepository outbox;
  @Autowired OutboxRelay relay;
  @Autowired ConsumerFactory<String, String> cf;
  @Autowired EmbeddedKafkaBroker broker;

  @Test
  void relayPublishesUnpublishedRowAndMarksPublished() {
    OutboxEntry e = new OutboxEntry();
    e.setAggregateType("assessment");
    e.setAggregateId("777");
    e.setEventType("learning.assessment.completed");
    e.setPayload("{\"assessmentId\":777}");
    e.setCreatedAt(Instant.now());
    Long id = outbox.save(e).getId();

    int published = relay.relayOnce();
    assertTrue(published >= 1);
    assertTrue(outbox.findById(id).orElseThrow().getPublishedAt() != null, "published_at 설정");

    try (Consumer<String, String> c = cf.createConsumer("t-grp", "t")) {
      broker.consumeFromAnEmbeddedTopic(c, "learning.assessment.completed");
      ConsumerRecords<String, String> recs = KafkaTestUtils.getRecords(c);
      boolean found = StreamSupport.stream(recs.spliterator(), false)
          .anyMatch(r -> r.value().contains("777"));
      assertTrue(found, "발행된 레코드에 assessmentId=777 포함");
    }
  }
}
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
docker compose up -d
./gradlew test --tests ai.devpath.learning.outbox.OutboxRelayTest
```
Expected: FAIL(outbox 클래스 미존재).

- [ ] **Step 3: OutboxEntry 작성**

`OutboxEntry.java`:

```java
package ai.devpath.learning.outbox;

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

- [ ] **Step 4: OutboxRepository·OutboxRelay·OutboxRelayScheduler 작성**

`OutboxRepository.java`:

```java
package ai.devpath.learning.outbox;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OutboxRepository extends JpaRepository<OutboxEntry, Long> {
  List<OutboxEntry> findTop100ByPublishedAtIsNullOrderByCreatedAtAsc();
}
```

`OutboxRelay.java`:

```java
package ai.devpath.learning.outbox;

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

`OutboxRelayScheduler.java`:

```java
package ai.devpath.learning.outbox;

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

- [ ] **Step 5: @EnableScheduling 확인**

`LearningApplication.java`에 `@org.springframework.scheduling.annotation.EnableScheduling` 추가(클래스 어노테이션).

- [ ] **Step 6: 테스트 통과 확인 + 커밋**

```bash
./gradlew test --tests ai.devpath.learning.outbox.OutboxRelayTest
git add src/main/java/ai/devpath/learning/outbox/ \
        src/main/java/ai/devpath/learning/LearningApplication.java \
        src/test/java/ai/devpath/learning/outbox/OutboxRelayTest.java
git commit -m "feat(outbox): learning-svc outbox 릴레이(Kafka send-ack 후 published)"
```

---

## Task 3: 진단 완료 이벤트 발행 + concept 집계

**Files:**
- Create: `.../assessment/AssessmentEventPublisher.java`
- Modify: `.../assessment/AssessmentService.java` (`complete()`에 이벤트 적재 + concept_scores 집계)
- Create: `src/test/java/ai/devpath/learning/assessment/AssessmentEventPropagationIT.java`

**Interfaces:**
- Consumes: `OutboxRepository`, `JsonMapper`(Boot 자동), `AssessmentCompletedEvent`(shared).
- Produces: `AssessmentEventPublisher.publishCompleted(long assessmentId, long userId, String track, String diagnosedLevel, Map<String,Double> conceptScores)` — outbox 1행 적재(`@Transactional` 호출자 tx에 합류).

- [ ] **Step 1: 이벤트 전파 IT 작성(실패)**

`AssessmentEventPropagationIT.java` — outbox 적재 → relayOnce → Kafka 레코드에 이벤트 타입·assessmentId 확인(EventPropagationIT 패턴):

```java
package ai.devpath.learning.assessment;

import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.devpath.learning.outbox.OutboxRelay;
import java.util.Map;
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
@EmbeddedKafka(partitions = 1, topics = {"learning.assessment.completed"}, bootstrapServersProperty = "spring.kafka.bootstrap-servers")
class AssessmentEventPropagationIT {

  @Autowired AssessmentEventPublisher publisher;
  @Autowired OutboxRelay relay;
  @Autowired ConsumerFactory<String, String> cf;
  @Autowired EmbeddedKafkaBroker broker;

  @Test
  void completedEventReachesKafka() {
    publisher.publishCompleted(55L, 42L, "BACKEND_SPRING", "MID", Map.of("spring", 0.7));
    int published = relay.relayOnce();
    assertTrue(published >= 1);
    try (Consumer<String, String> c = cf.createConsumer("t-grp", "t")) {
      broker.consumeFromAnEmbeddedTopic(c, "learning.assessment.completed");
      ConsumerRecords<String, String> recs = KafkaTestUtils.getRecords(c);
      boolean found = StreamSupport.stream(recs.spliterator(), false)
          .anyMatch(r -> r.value().contains("\"assessmentId\":55") && r.value().contains("MID"));
      assertTrue(found, "이벤트 레코드에 assessmentId=55·MID 포함");
    }
  }
}
```

- [ ] **Step 2: 실패 확인**

```bash
./gradlew test --tests ai.devpath.learning.assessment.AssessmentEventPropagationIT
```
Expected: FAIL(`AssessmentEventPublisher` 미존재).

- [ ] **Step 3: AssessmentEventPublisher 구현**

`AssessmentEventPublisher.java`:

```java
package ai.devpath.learning.assessment;

import ai.devpath.learning.outbox.OutboxEntry;
import ai.devpath.learning.outbox.OutboxRepository;
import ai.devpath.shared.event.AssessmentCompletedEvent;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

@Component
public class AssessmentEventPublisher {

  private final OutboxRepository outbox;
  private final JsonMapper jsonMapper;

  public AssessmentEventPublisher(OutboxRepository outbox, JsonMapper jsonMapper) {
    this.outbox = outbox;
    this.jsonMapper = jsonMapper;
  }

  public void publishCompleted(long assessmentId, long userId, String track,
      String diagnosedLevel, Map<String, Double> conceptScores) {
    var event = new AssessmentCompletedEvent(UUID.randomUUID(), Instant.now(),
        assessmentId, userId, track, diagnosedLevel, conceptScores, Instant.now());
    OutboxEntry entry = new OutboxEntry();
    entry.setAggregateType("assessment");
    entry.setAggregateId(String.valueOf(assessmentId));
    entry.setEventType(AssessmentCompletedEvent.EVENT_TYPE);
    entry.setPayload(serialize(event));
    entry.setCreatedAt(Instant.now());
    outbox.save(entry);
  }

  private String serialize(AssessmentCompletedEvent event) {
    try {
      return jsonMapper.writeValueAsString(event);
    } catch (Exception e) {
      throw new IllegalStateException("AssessmentCompletedEvent 직렬화 실패", e);
    }
  }
}
```

- [ ] **Step 4: AssessmentService.complete()에 이벤트 적재 + concept 집계 결선**

`AssessmentService`에 `AssessmentEventPublisher publisher`를 생성자 주입하고, `complete()`에서 결과 저장 직후 concept_scores를 집계해 저장·발행하도록 수정. `complete()`의 결과 계산 블록을 아래로 교체:

```java
    // concept_tags별 정답률 집계 (skip 제외)
    Map<String, double[]> agg = new java.util.HashMap<>(); // tag -> [correct, total]
    for (AssessmentItem i : all) {
      if (i.isSkipped()) continue;
      QuestionBank q = byId.get(i.getQuestionBankId());
      java.util.List<String> tags = parseTags(q.getConceptTags());
      for (String tag : tags) {
        double[] cw = agg.computeIfAbsent(tag, k -> new double[2]);
        if (Boolean.TRUE.equals(i.getIsCorrect())) cw[0] += 1;
        cw[1] += 1;
      }
    }
    Map<String, Double> conceptScores = new java.util.HashMap<>();
    agg.forEach((tag, cw) -> conceptScores.put(tag, cw[1] == 0 ? 0.0 : cw[0] / cw[1]));
    java.util.List<String> strengths = conceptScores.entrySet().stream()
        .filter(e -> e.getValue() >= 0.7).map(Map.Entry::getKey).sorted().toList();
    java.util.List<String> weaknesses = conceptScores.entrySet().stream()
        .filter(e -> e.getValue() < 0.4).map(Map.Entry::getKey).sorted().toList();

    a.setStatus("COMPLETED");
    a.setCompletedAt(Instant.now());
    assessments.save(a);

    AssessmentResult r = new AssessmentResult();
    r.setAssessmentId(assessmentId);
    r.setDiagnosedLevel(level);
    r.setConfidenceWeight(confidence);
    r.setConceptScores(writeJson(conceptScores));
    r.setStrengthConcepts(writeJson(strengths));
    r.setWeaknessConcepts(writeJson(weaknesses));
    results.save(r);

    publisher.publishCompleted(assessmentId, a.getUserId(), a.getTrack(), level, conceptScores);
    return new AssessmentResultView(level, r.getConceptScores(), r.getStrengthConcepts(),
        r.getWeaknessConcepts(), confidence);
```

그리고 `AssessmentService`에 헬퍼 추가(생성자에 `JsonMapper jsonMapper` 주입):

```java
  private java.util.List<String> parseTags(String json) {
    if (json == null || json.isBlank()) return java.util.List.of();
    try { return jsonMapper.readValue(json, new tools.jackson.core.type.TypeReference<java.util.List<String>>() {}); }
    catch (Exception e) { return java.util.List.of(); }
  }
  private String writeJson(Object o) {
    try { return jsonMapper.writeValueAsString(o); } catch (Exception e) { throw new IllegalStateException(e); }
  }
```

- [ ] **Step 5: 테스트 통과 확인 + 커밋**

```bash
docker compose up -d
./gradlew test --tests ai.devpath.learning.assessment.AssessmentEventPropagationIT --tests ai.devpath.learning.assessment.AssessmentControllerTest
git add src/main/java/ai/devpath/learning/assessment/AssessmentEventPublisher.java \
        src/main/java/ai/devpath/learning/assessment/AssessmentService.java \
        src/test/java/ai/devpath/learning/assessment/AssessmentEventPropagationIT.java
git commit -m "feat(assessment): 진단 완료 AssessmentCompletedEvent 발행 + concept 집계"
```
Expected: PASS(회원 흐름·이벤트 전파 모두).

---

## Task 4: 진단 문항 시드 (테스트/로컬)

**Files:**
- Create: `src/test/resources/seed/question_bank_seed.sql`
- Create: `src/main/java/ai/devpath/learning/seed/QuestionBankSeeder.java`
- Create: `src/test/java/ai/devpath/learning/seed/SeedSqlTest.java`

**Interfaces:**
- Produces: dev 프로파일에서 비어있을 때 소량 문항 적재하는 `QuestionBankSeeder`(CommandLineRunner). 테스트는 `@Sql("/seed/question_bank_seed.sql")`로 적재.

- [ ] **Step 1: 시드 SQL 작성**

`src/test/resources/seed/question_bank_seed.sql` — track BACKEND_SPRING에 난이도/Bloom/concept 분포 커버 15+문항:

```sql
INSERT INTO question_bank (track, question_type, content, options, answer_key, bloom_level, difficulty, concept_tags) VALUES
('BACKEND_SPRING','MCQ','스프링 빈 스코프 기본값은?','["singleton","prototype"]','{"correct":0}','REMEMBER',0.1,'["spring-core"]'),
('BACKEND_SPRING','MCQ','@Transactional 전파 기본값은?','["REQUIRED","REQUIRES_NEW"]','{"correct":0}','UNDERSTAND',0.3,'["spring-tx"]'),
('BACKEND_SPRING','CODE_READING','이 JPA 코드의 N+1 문제는?','["지연로딩","즉시로딩"]','{"correct":0}','ANALYZE',0.6,'["jpa"]'),
('BACKEND_SPRING','MCQ','HTTP 멱등 메서드가 아닌 것은?','["GET","POST"]','{"correct":1}','UNDERSTAND',0.4,'["http"]'),
('BACKEND_SPRING','MCQ','인덱스가 가장 효과적인 경우는?','["고선택도","저선택도"]','{"correct":0}','APPLY',0.5,'["db-index"]'),
('BACKEND_SPRING','MCQ','스프링 시큐리티 필터체인 순서를 결정하는 것은?','["@Order","임의"]','{"correct":0}','APPLY',0.7,'["spring-security"]'),
('BACKEND_SPRING','MCQ','Kafka 컨슈머 그룹의 역할은?','["분산소비","중복소비"]','{"correct":0}','UNDERSTAND',0.5,'["kafka"]'),
('BACKEND_SPRING','MCQ','REST에서 201의 의미는?','["생성됨","수정됨"]','{"correct":0}','REMEMBER',0.2,'["http"]'),
('BACKEND_SPRING','CODE_READING','이 코드의 동시성 버그는?','["경쟁상태","없음"]','{"correct":0}','EVALUATE',0.8,'["concurrency"]'),
('BACKEND_SPRING','MCQ','커넥션 풀 고갈 원인으로 옳은 것은?','["미반환","과반환"]','{"correct":0}','ANALYZE',0.6,'["db-pool"]'),
('BACKEND_SPRING','MCQ','캐시 무효화 전략이 아닌 것은?','["TTL","무한보관"]','{"correct":1}','UNDERSTAND',0.4,'["cache"]'),
('BACKEND_SPRING','MCQ','idempotency-key의 목적은?','["중복방지","속도"]','{"correct":0}','APPLY',0.6,'["api-design"]'),
('BACKEND_SPRING','MCQ','트랜잭션 격리수준 중 팬텀리드를 막는 것은?','["SERIALIZABLE","READ_COMMITTED"]','{"correct":0}','ANALYZE',0.7,'["spring-tx"]'),
('BACKEND_SPRING','MCQ','스프링 프로파일의 용도는?','["환경분리","로깅"]','{"correct":0}','REMEMBER',0.2,'["spring-core"]'),
('BACKEND_SPRING','MCQ','OAuth2 authorization code 흐름의 첫 단계는?','["인가요청","토큰교환"]','{"correct":0}','UNDERSTAND',0.5,'["oauth2"]'),
('BACKEND_SPRING','CODE_READING','이 SQL의 풀스캔 원인은?','["함수인덱스미사용","조인"]','{"correct":0}','EVALUATE',0.9,'["db-index"]'),
('BACKEND_SPRING','MCQ','멱등 컨슈머 구현 방법은?','["처리이력저장","재시도"]','{"correct":0}','APPLY',0.6,'["kafka"]');
```

- [ ] **Step 2: 시드 SQL 적재 테스트 작성·실행**

`SeedSqlTest.java`:

```java
package ai.devpath.learning.seed;

import static org.assertj.core.api.Assertions.assertThat;

import ai.devpath.learning.assessment.QuestionBankRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;

@SpringBootTest
@ActiveProfiles("test")
@Sql("/seed/question_bank_seed.sql")
class SeedSqlTest {

  @Autowired QuestionBankRepository questions;

  @Test
  void seedLoadsBackendQuestions() {
    assertThat(questions.findByTrack("BACKEND_SPRING").size()).isGreaterThanOrEqualTo(15);
  }
}
```

```bash
docker compose up -d
./gradlew test --tests ai.devpath.learning.seed.SeedSqlTest
```
Expected: PASS.

- [ ] **Step 3: dev 시더 작성 + 커밋**

`QuestionBankSeeder.java`:

```java
package ai.devpath.learning.seed;

import ai.devpath.learning.assessment.QuestionBank;
import ai.devpath.learning.assessment.QuestionBankRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

/** 로컬(dev) 끝단간용 최소 문항 시드. 비어있을 때만 적재. */
@Component
@Profile("dev")
public class QuestionBankSeeder implements CommandLineRunner {

  private final QuestionBankRepository questions;

  public QuestionBankSeeder(QuestionBankRepository questions) { this.questions = questions; }

  @Override
  public void run(String... args) {
    if (!questions.findByTrack("BACKEND_SPRING").isEmpty()) return;
    for (int i = 0; i < 17; i++) {
      QuestionBank q = new QuestionBank();
      q.setTrack("BACKEND_SPRING");
      q.setQuestionType("MCQ");
      q.setContent("샘플 진단 문항 " + (i + 1));
      q.setOptions("[\"a\",\"b\"]");
      q.setAnswerKey("{\"correct\":0}");
      q.setBloomLevel(new String[]{"REMEMBER","UNDERSTAND","APPLY","ANALYZE","EVALUATE"}[i % 5]);
      q.setDifficulty(0.1 + (i % 9) * 0.1);
      q.setConceptTags("[\"concept-" + (i % 4) + "\"]");
      questions.save(q);
    }
  }
}
```

```bash
git add src/test/resources/seed/question_bank_seed.sql \
        src/main/java/ai/devpath/learning/seed/QuestionBankSeeder.java \
        src/test/java/ai/devpath/learning/seed/SeedSqlTest.java
git commit -m "feat(seed): 진단 문항 시드(test SQL + dev 시더)"
```

---

## Task 5: 비회원(guest) Redis 진단 세션

**Files:**
- Create: `.../assessment/guest/GuestSession.java`, `GuestSessionStore.java`, `GuestAssessmentService.java`, `GuestAssessmentController.java`
- Create: `src/test/java/ai/devpath/learning/assessment/guest/GuestAssessmentControllerTest.java`

**Interfaces:**
- Consumes: `AdaptiveEngine`, `NextQuestionSelector`, `QuestionBankRepository`, `StringRedisTemplate`, `JsonMapper`.
- Produces:
  - `GuestSession(String guestId, String track, double currentDifficulty, List<Presented> presented, boolean completed, String diagnosedLevel)` + nested `record Presented(long questionId, double difficulty, Boolean correct, boolean skipped)`.
  - `GuestSessionStore.save(GuestSession)`, `Optional<GuestSession> find(String guestId)`, `delete(String)` — Redis 키 `assessment:guest:{guestId}`, TTL 30분.
  - 엔드포인트(PUBLIC): `POST /onboarding/assessments/guest`(body track)→{guestAssessmentId}, `GET /guest/{gid}/next`, `POST /guest/{gid}/answer`, `POST /guest/{gid}/complete`→result.

- [ ] **Step 1: guest 끝단간 컨트롤러 테스트 작성(실패)**

`GuestAssessmentControllerTest.java`:

```java
package ai.devpath.learning.assessment.guest;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Sql("/seed/question_bank_seed.sql")
class GuestAssessmentControllerTest {

  @Autowired MockMvc mvc;

  @Test
  void guestFlowStartToResultNoAuth() throws Exception {
    String start = mvc.perform(post("/onboarding/assessments/guest")
            .contentType(MediaType.APPLICATION_JSON).content("{\"track\":\"BACKEND_SPRING\"}"))
        .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
    String gid = com.jayway.jsonpath.JsonPath.parse(start).read("$.guestAssessmentId");

    for (int i = 0; i < 15; i++) {
      String next = mvc.perform(get("/onboarding/assessments/guest/" + gid + "/next"))
          .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
      long qid = com.jayway.jsonpath.JsonPath.parse(next).read("$.question.id", Long.class);
      mvc.perform(post("/onboarding/assessments/guest/" + gid + "/answer")
              .contentType(MediaType.APPLICATION_JSON)
              .content("{\"questionId\":" + qid + ",\"answer\":\"{\\\"correct\\\":0}\",\"skipped\":false,\"timeSpentSec\":3}"))
          .andExpect(status().isOk());
    }
    mvc.perform(post("/onboarding/assessments/guest/" + gid + "/complete"))
        .andExpect(status().isOk()).andExpect(jsonPath("$.diagnosedLevel").exists());
  }
}
```

- [ ] **Step 2: 실패 확인**

```bash
./gradlew test --tests ai.devpath.learning.assessment.guest.GuestAssessmentControllerTest
```
Expected: FAIL(guest 클래스/엔드포인트 미존재).

- [ ] **Step 3: GuestSession 작성**

`GuestSession.java`:

```java
package ai.devpath.learning.assessment.guest;

import java.util.List;

public record GuestSession(
    String guestId,
    String track,
    double currentDifficulty,
    List<Presented> presented,
    boolean completed,
    String diagnosedLevel) {

  public record Presented(long questionId, double difficulty, Boolean correct, boolean skipped) {}
}
```

- [ ] **Step 4: GuestSessionStore 작성**

`GuestSessionStore.java`:

```java
package ai.devpath.learning.assessment.guest;

import java.time.Duration;
import java.util.Optional;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

@Component
public class GuestSessionStore {

  private static final String PREFIX = "assessment:guest:";
  private static final Duration TTL = Duration.ofMinutes(30);

  private final StringRedisTemplate redis;
  private final JsonMapper jsonMapper;

  public GuestSessionStore(StringRedisTemplate redis, JsonMapper jsonMapper) {
    this.redis = redis;
    this.jsonMapper = jsonMapper;
  }

  public void save(GuestSession session) {
    try {
      redis.opsForValue().set(PREFIX + session.guestId(), jsonMapper.writeValueAsString(session), TTL);
    } catch (Exception e) {
      throw new IllegalStateException("guest 세션 직렬화 실패", e);
    }
  }

  public Optional<GuestSession> find(String guestId) {
    String json = redis.opsForValue().get(PREFIX + guestId);
    if (json == null) return Optional.empty();
    try {
      return Optional.of(jsonMapper.readValue(json, GuestSession.class));
    } catch (Exception e) {
      throw new IllegalStateException("guest 세션 역직렬화 실패", e);
    }
  }

  public void delete(String guestId) {
    redis.delete(PREFIX + guestId);
  }
}
```

- [ ] **Step 5: GuestAssessmentService 작성**

`GuestAssessmentService.java` (회원과 동일 엔진, 상태만 Redis):

```java
package ai.devpath.learning.assessment.guest;

import ai.devpath.learning.assessment.NextQuestionSelector;
import ai.devpath.learning.assessment.QuestionBank;
import ai.devpath.learning.assessment.QuestionBankRepository;
import ai.devpath.learning.assessment.dto.*;
import ai.devpath.learning.assessment.engine.AdaptiveEngine;
import java.util.*;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

@Service
public class GuestAssessmentService {

  private final GuestSessionStore store;
  private final QuestionBankRepository questions;
  private final AdaptiveEngine engine;
  private final NextQuestionSelector selector;

  public GuestAssessmentService(GuestSessionStore store, QuestionBankRepository questions,
      AdaptiveEngine engine, NextQuestionSelector selector) {
    this.store = store;
    this.questions = questions;
    this.engine = engine;
    this.selector = selector;
  }

  public String start(String track) {
    String guestId = UUID.randomUUID().toString();
    store.save(new GuestSession(guestId, track, AdaptiveEngine.START_DIFFICULTY,
        new ArrayList<>(), false, null));
    return guestId;
  }

  public Optional<NextQuestionResponse> next(String guestId) {
    GuestSession s = require(guestId);
    if (engine.isComplete(s.presented().size())) return Optional.empty();
    Set<Long> excluded = s.presented().stream()
        .map(GuestSession.Presented::questionId).collect(Collectors.toSet());
    QuestionBank q = selector.select(s.track(), s.currentDifficulty(), excluded, questions.findByTrack(s.track()));
    if (q == null) return Optional.empty();
    var view = new QuestionView(q.getId(), q.getQuestionType(), q.getContent(), q.getOptions(),
        q.getBloomLevel(), q.getDifficulty());
    return Optional.of(new NextQuestionResponse(view, s.presented().size() + 1, AdaptiveEngine.TOTAL_QUESTIONS));
  }

  public void answer(String guestId, AnswerRequest req) {
    GuestSession s = require(guestId);
    QuestionBank q = questions.findById(req.questionId()).orElseThrow();
    AdaptiveEngine.AnswerOutcome outcome;
    Boolean correct;
    if (req.skipped()) {
      outcome = AdaptiveEngine.AnswerOutcome.SKIP;
      correct = null;
    } else {
      boolean ok = Objects.equals(normalize(req.answer()), normalize(q.getAnswerKey()));
      correct = ok;
      outcome = ok ? AdaptiveEngine.AnswerOutcome.CORRECT : AdaptiveEngine.AnswerOutcome.WRONG;
    }
    var presented = new ArrayList<>(s.presented());
    presented.add(new GuestSession.Presented(q.getId(), q.getDifficulty(), correct, req.skipped()));
    double nextDiff = engine.nextDifficulty(s.currentDifficulty(), outcome);
    store.save(new GuestSession(s.guestId(), s.track(), nextDiff, presented, false, null));
  }

  public AssessmentResultView complete(String guestId) {
    GuestSession s = require(guestId);
    List<Double> correctDiffs = s.presented().stream()
        .filter(p -> Boolean.TRUE.equals(p.correct())).map(GuestSession.Presented::difficulty).toList();
    String level = engine.diagnoseLevel(correctDiffs);
    long scored = s.presented().stream().filter(p -> !p.skipped()).count();
    double confidence = s.presented().isEmpty() ? 0.0 : (double) scored / s.presented().size();
    store.save(new GuestSession(s.guestId(), s.track(), s.currentDifficulty(), s.presented(), true, level));
    return new AssessmentResultView(level, null, null, null, confidence);
  }

  private GuestSession require(String guestId) {
    return store.find(guestId)
        .orElseThrow(() -> new java.util.NoSuchElementException("guest 세션 없음/만료"));
  }

  private static String normalize(String json) {
    return json == null ? null : json.replaceAll("\\s+", "");
  }
}
```

- [ ] **Step 6: GuestAssessmentController 작성**

`GuestAssessmentController.java`:

```java
package ai.devpath.learning.assessment.guest;

import ai.devpath.learning.assessment.dto.*;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/onboarding/assessments/guest")
public class GuestAssessmentController {

  private final GuestAssessmentService service;

  public GuestAssessmentController(GuestAssessmentService service) { this.service = service; }

  @PostMapping
  public ResponseEntity<Map<String, String>> start(@RequestBody StartAssessmentRequest req) {
    return ResponseEntity.ok(Map.of("guestAssessmentId", service.start(req.track())));
  }

  @GetMapping("/{gid}/next")
  public ResponseEntity<NextQuestionResponse> next(@PathVariable String gid) {
    return service.next(gid).map(ResponseEntity::ok).orElseGet(() -> ResponseEntity.noContent().build());
  }

  @PostMapping("/{gid}/answer")
  public ResponseEntity<Void> answer(@PathVariable String gid, @RequestBody AnswerRequest req) {
    service.answer(gid, req);
    return ResponseEntity.ok().build();
  }

  @PostMapping("/{gid}/complete")
  public ResponseEntity<AssessmentResultView> complete(@PathVariable String gid) {
    return ResponseEntity.ok(service.complete(gid));
  }
}
```

- [ ] **Step 7: 테스트 통과 확인 + 커밋**

```bash
docker compose up -d
./gradlew test --tests ai.devpath.learning.assessment.guest.GuestAssessmentControllerTest
git add src/main/java/ai/devpath/learning/assessment/guest/ \
        src/test/java/ai/devpath/learning/assessment/guest/GuestAssessmentControllerTest.java
git commit -m "feat(guest): 비회원 Redis 진단 세션(start/next/answer/complete)"
```
Expected: PASS.

---

## Task 6: 회원 귀속(claim) — Redis→DB 이행 + 이벤트

**Files:**
- Create: `.../assessment/claim/ClaimService.java`, `ClaimController.java`
- Create: `.../assessment/claim/dto/ClaimRequest.java`
- Create: `src/test/java/ai/devpath/learning/assessment/claim/ClaimControllerTest.java`

**Interfaces:**
- Consumes: `GuestSessionStore`, `AssessmentRepository`, `AssessmentItemRepository`, `AssessmentResultRepository`, `QuestionBankRepository`, `AssessmentEventPublisher`, `AdaptiveEngine`.
- Produces:
  - `ClaimRequest(String guest_assessment_id)`.
  - 엔드포인트 `POST /onboarding/assessments/claim`(AUTHENTICATED)→{assessmentId}. completed guest 세션을 DB로 이행(user_id 결합, status COMPLETED), `AssessmentCompletedEvent` 발행. 멱등(guestId→assessmentId 매핑 Redis로 중복 방지).

- [ ] **Step 1: claim 테스트 작성(실패)**

`ClaimControllerTest.java` — guest 완료 세션을 만든 뒤 JWT로 claim → DB assessment·result 생성 검증:

```java
package ai.devpath.learning.assessment.claim;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import ai.devpath.learning.assessment.AssessmentRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Sql("/seed/question_bank_seed.sql")
class ClaimControllerTest {

  @Autowired MockMvc mvc;
  @Autowired AssessmentRepository assessments;

  @Test
  void claimMigratesGuestToMember() throws Exception {
    // 1. guest 진단 1바퀴 완료
    String start = mvc.perform(post("/onboarding/assessments/guest")
            .contentType(MediaType.APPLICATION_JSON).content("{\"track\":\"BACKEND_SPRING\"}"))
        .andReturn().getResponse().getContentAsString();
    String gid = com.jayway.jsonpath.JsonPath.parse(start).read("$.guestAssessmentId");
    for (int i = 0; i < 15; i++) {
      String next = mvc.perform(get("/onboarding/assessments/guest/" + gid + "/next"))
          .andReturn().getResponse().getContentAsString();
      long qid = com.jayway.jsonpath.JsonPath.parse(next).read("$.question.id", Long.class);
      mvc.perform(post("/onboarding/assessments/guest/" + gid + "/answer")
          .contentType(MediaType.APPLICATION_JSON)
          .content("{\"questionId\":" + qid + ",\"answer\":\"{\\\"correct\\\":0}\",\"skipped\":false,\"timeSpentSec\":3}"));
    }
    mvc.perform(post("/onboarding/assessments/guest/" + gid + "/complete"));

    // 2. 로그인 사용자가 claim
    long before = assessments.count();
    var auth = jwt().jwt(j -> j.subject("99"));
    mvc.perform(post("/onboarding/assessments/claim").with(auth)
            .contentType(MediaType.APPLICATION_JSON).content("{\"guest_assessment_id\":\"" + gid + "\"}"))
        .andExpect(status().isOk()).andExpect(jsonPath("$.assessmentId").exists());
    org.assertj.core.api.Assertions.assertThat(assessments.count()).isEqualTo(before + 1);

    // 3. 멱등: 재요청은 동일 결과, 추가 행 없음
    mvc.perform(post("/onboarding/assessments/claim").with(auth)
        .contentType(MediaType.APPLICATION_JSON).content("{\"guest_assessment_id\":\"" + gid + "\"}"))
        .andExpect(status().isOk());
    org.assertj.core.api.Assertions.assertThat(assessments.count()).isEqualTo(before + 1);
  }
}
```

- [ ] **Step 2: 실패 확인**

```bash
./gradlew test --tests ai.devpath.learning.assessment.claim.ClaimControllerTest
```
Expected: FAIL(claim 미존재).

- [ ] **Step 3: ClaimRequest 작성**

`dto/ClaimRequest.java`:

```java
package ai.devpath.learning.assessment.claim.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record ClaimRequest(@JsonProperty("guest_assessment_id") String guestAssessmentId) {}
```

> 주: 요청 JSON 키는 API 명세(`04 §2.1`)대로 snake_case `guest_assessment_id`. `@JsonProperty`로 매핑(Boot4 Jackson3도 `com.fasterxml.jackson.annotation.JsonProperty` 어노테이션 인식).

- [ ] **Step 4: ClaimService 작성**

`ClaimService.java`:

```java
package ai.devpath.learning.assessment.claim;

import ai.devpath.learning.assessment.*;
import ai.devpath.learning.assessment.engine.AdaptiveEngine;
import ai.devpath.learning.assessment.guest.GuestSession;
import ai.devpath.learning.assessment.guest.GuestSessionStore;
import java.time.Instant;
import java.util.*;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ClaimService {

  private static final String CLAIM_PREFIX = "assessment:claim:"; // guestId -> assessmentId (멱등)

  private final GuestSessionStore guestStore;
  private final AssessmentRepository assessments;
  private final AssessmentItemRepository items;
  private final AssessmentResultRepository results;
  private final QuestionBankRepository questions;
  private final AssessmentEventPublisher publisher;
  private final AdaptiveEngine engine;
  private final StringRedisTemplate redis;

  public ClaimService(GuestSessionStore guestStore, AssessmentRepository assessments,
      AssessmentItemRepository items, AssessmentResultRepository results,
      QuestionBankRepository questions, AssessmentEventPublisher publisher,
      AdaptiveEngine engine, StringRedisTemplate redis) {
    this.guestStore = guestStore;
    this.assessments = assessments;
    this.items = items;
    this.results = results;
    this.questions = questions;
    this.publisher = publisher;
    this.engine = engine;
    this.redis = redis;
  }

  @Transactional
  public long claim(long userId, String guestId) {
    String existing = redis.opsForValue().get(CLAIM_PREFIX + guestId);
    if (existing != null) return Long.parseLong(existing); // 멱등

    GuestSession s = guestStore.find(guestId)
        .orElseThrow(() -> new NoSuchElementException("guest 세션 없음/만료"));
    if (!s.completed()) throw new IllegalStateException("완료되지 않은 guest 진단");

    Assessment a = new Assessment();
    a.setUserId(userId);
    a.setTrack(s.track());
    a.setStatus("COMPLETED");
    a.setCurrentDifficulty(s.currentDifficulty());
    a.setStartedAt(Instant.now());
    a.setCompletedAt(Instant.now());
    long assessmentId = assessments.save(a).getId();

    int order = 1;
    List<Double> correctDiffs = new ArrayList<>();
    for (GuestSession.Presented p : s.presented()) {
      AssessmentItem item = new AssessmentItem();
      item.setAssessmentId(assessmentId);
      item.setQuestionBankId(p.questionId());
      item.setOrderNum(order++);
      item.setPresentedAt(Instant.now());
      item.setAnsweredAt(Instant.now());
      item.setSkipped(p.skipped());
      item.setIsCorrect(p.correct());
      items.save(item);
      if (Boolean.TRUE.equals(p.correct())) correctDiffs.add(p.difficulty());
    }

    String level = s.diagnosedLevel() != null ? s.diagnosedLevel() : engine.diagnoseLevel(correctDiffs);
    AssessmentResult r = new AssessmentResult();
    r.setAssessmentId(assessmentId);
    r.setDiagnosedLevel(level);
    long scored = s.presented().stream().filter(p -> !p.skipped()).count();
    r.setConfidenceWeight(s.presented().isEmpty() ? 0.0 : (double) scored / s.presented().size());
    results.save(r);

    publisher.publishCompleted(assessmentId, userId, s.track(), level, Map.of());

    redis.opsForValue().set(CLAIM_PREFIX + guestId, String.valueOf(assessmentId));
    guestStore.delete(guestId);
    return assessmentId;
  }
}
```

- [ ] **Step 5: ClaimController 작성**

`ClaimController.java`:

```java
package ai.devpath.learning.assessment.claim;

import ai.devpath.learning.assessment.claim.dto.ClaimRequest;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/onboarding/assessments/claim")
public class ClaimController {

  private final ClaimService service;

  public ClaimController(ClaimService service) { this.service = service; }

  @PostMapping
  public ResponseEntity<Map<String, Long>> claim(@AuthenticationPrincipal Jwt jwt,
      @RequestBody ClaimRequest req) {
    long userId = Long.parseLong(jwt.getSubject());
    long assessmentId = service.claim(userId, req.guestAssessmentId());
    return ResponseEntity.ok(Map.of("assessmentId", assessmentId));
  }
}
```

> 보안 주의: `/onboarding/assessments/claim`은 `/guest/**` permitAll 패턴에 걸리지 않는다(별도 경로). B-1 SecurityConfig의 `anyRequest().authenticated()`로 보호됨 — 확인.

- [ ] **Step 6: 테스트 통과 확인 + 커밋**

```bash
docker compose up -d
./gradlew test --tests ai.devpath.learning.assessment.claim.ClaimControllerTest
git add src/main/java/ai/devpath/learning/assessment/claim/ \
        src/test/java/ai/devpath/learning/assessment/claim/ClaimControllerTest.java
git commit -m "feat(claim): 비회원→회원 진단 귀속(Redis→DB 이행·이벤트·멱등)"
```
Expected: PASS.

---

## Task 7: 전체 빌드 + develop PR

- [ ] **Step 1: 전체 빌드·테스트**

```bash
docker compose up -d
./gradlew clean build
```
Expected: BUILD SUCCESSFUL, 전 테스트 PASS.

- [ ] **Step 2: develop PR → CI 녹색 → merge**

작업 브랜치(`feat/slice2-learning-events`, develop 분기) → `gh pr create --base develop` → 머지.

> 다음: 빌드 C(platform 소비자) → 빌드 D(gateway 라우트 + frontend).

---

## Self-Review (작성자 점검 결과)

- **Spec coverage**: 설계서 §2 빌드B(이벤트·guest·claim·시드), §4(guest 동일 엔진), §6(guest Redis 30분·claim 멱등), §7(이벤트 outbox→Kafka·`learning.assessment.completed`), §9(EmbeddedKafka·guest·claim IT), §11.3(concept 집계 보강)·§11.6(시드) — 커버.
- **Placeholder scan**: 모든 코드 완전 기재. claim 이벤트의 conceptScores는 `Map.of()`(guest는 concept 미집계 — guest 세션에 concept 미보관, 설계 결정. 회원 complete는 집계). TODO 없음.
- **Type consistency**: `AssessmentCompletedEvent` 8필드(빌드A) = `publishCompleted` 인자 매핑 일치. `GuestSession.Presented(questionId,difficulty,correct,skipped)`가 guest 서비스·claim 사용과 일치. DTO(`AnswerRequest`,`NextQuestionResponse`,`AssessmentResultView`)는 B-1과 공유(동일 패키지 `dto`). `AdaptiveEngine.AnswerOutcome`·`diagnoseLevel`·`START_DIFFICULTY` 일치.
- **주의**: claim 멱등은 `assessment:claim:{guestId}` Redis 매핑 + guest 세션 delete로 구현(완전 원자성은 하드닝 후속). guest concept_scores 미집계는 회원 claim 후에도 빈 값 — 슬라이스 #3 입력에 concept 필요 시 후속 보강(설계서 §11.4와 연계).
