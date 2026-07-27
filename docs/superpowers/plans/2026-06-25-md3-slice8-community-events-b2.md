# 빌드 B2 (community-svc 이벤트/유사질문) — Outbox 발행 · AI 시드 consume · pgvector 유사질문 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development. 태스크별 RED→GREEN→커밋. Steps use checkbox (`- [ ]`).

**Goal:** devpath-community-svc에 슬라이스 #8 이벤트 왕복(질문 게시 → `community.question.posted` Outbox 발행 / `community.seed.ready` 멱등 consume → AI 답변·메타·임베딩 영속)과 pgvector 유사질문 탐지를 TDD로 추가한다. 빌드 B1(Q&A 코어 CRUD)은 develop 머지 완료(PR #9, merge `e5f01aa`).

**Architecture:** 설계서 [2026-06-25-md3-slice8-community-qna-design](../specs/2026-06-25-md3-slice8-community-qna-design.md) §3(D-1·D-4·D-5·D-6)·§4·§5(community-svc B2). learning-svc `outbox/`(Outbox 트랜잭션 아웃박스) + `path/ContentEmbeddingMatcher`(pgvector JdbcTemplate) + ai-svc `review/ReviewConsumer`+`ReviewKafkaConfig`(멱등 `@KafkaListener` + EmbeddedKafka IT) 패턴을 community-svc에 미러한다.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Gradle KDSL · JPA(Hibernate) · spring-kafka · PostgreSQL+pgvector(shared 중앙 Flyway; 서비스는 validate) · JsonMapper(Jackson 3, Boot 자동구성) · JUnit 5 · EmbeddedKafka · Awaitility.

## Global Constraints

- **DB**: 마이그레이션은 shared 중앙(빌드 A 완료, `V202606251001__community_qna.sql` — `community_posts`·`community_questions`(`question_embedding VECTOR(768)`)·`community_answers`·`community_votes`·`community_tags`·`community_post_tags`·`community_ai_answers`(PK=question_id, UNIQUE 멱등) + outbox 테이블 `V202606171004`). community-svc는 `ddl-auto: validate`, prod `flyway.enabled: false`. **테스트 프로파일은 `flyway.enabled: true`로 fresh DB에 shared 마이그레이션 적용**(B1 교훈, `application-test.yml` 실측).
- **테스트 DB**: 로컬 docker `devpath-local-postgres-1`(5432). `DB_URL=jdbc:postgresql://localhost:5432/devpath_citest DB_USER=devpath DB_PASSWORD=localdev`. 모든 `@SpringBootTest`에 `@ActiveProfiles("test")`(B1 CI 교훈).
- **Kafka**: 실 kafka 불요. 모든 Kafka 테스트는 `@EmbeddedKafka`(in-process). `OutboxRelayScheduler`는 `@Profile("!test")`라 테스트에서 비활성 → 테스트는 `relay.relayOnce()` 직접 호출 또는 consumer만 검증.
- **교차서비스 FK 금지**: `author_id`는 논리참조. AI 답변은 `author_id=null`.
- **ai-svc는 호출만**: `/ai/embed`는 community-svc가 RestClient로 호출. **실제 호출은 테스트에서 mock**(MockWebServer 또는 빈 교체). ai-svc 코드는 절대 수정하지 않는다(빌드 C 소관).
- **JSON 직렬화**: ai-svc와 동일하게 `tools.jackson.databind.json.JsonMapper`(Jackson 3, Boot 4 자동구성 빈) 주입. payload는 이벤트 record를 JSON 문자열로 직렬화.
- **검증 명령**: `cd devpath-community-svc && DB_URL=jdbc:postgresql://localhost:5432/devpath_citest DB_USER=devpath DB_PASSWORD=localdev ./gradlew test`. 빌드: 같은 env로 `./gradlew build`.
- **브랜치**: `feat/slice8-community-events`(develop에서 분기 완료). develop으로 PR(2단계).

---

## File Structure (B2 신규/수정)

`devpath-community-svc/src/main/java/ai/devpath/community/`:
- **신규 `outbox/`**(learning 미러): `OutboxEntry.java`·`OutboxRepository.java`·`OutboxRelay.java`·`OutboxRelayScheduler.java`
- **신규 `config/KafkaConfig.java`** — 멱등 consumer ErrorHandler(poison skip) + (necessary 시) ConsumerFactory. ai-svc `ReviewKafkaConfig` 미러(축소).
- **신규 `seed/`**(AI 시드 consume + 유사질문):
  - `CommunitySeedConsumer.java` — `@KafkaListener("community.seed.ready")` 멱등 영속
  - `CommunitySeedService.java` — DONE/FAILED 분기 + `UNIQUE(question_id)` insert-if-absent + 임베딩 UPDATE(JdbcTemplate)
  - `CommunityAiAnswer.java` + `CommunityAiAnswerRepository.java` — `community_ai_answers` 엔티티(PK=questionId)
  - `EmbeddingClient.java` — ai-svc `/ai/embed` RestClient(text→List<Double> 768)
  - `SimilarQuestionMatcher.java` — pgvector JdbcTemplate(코사인거리, learning 패턴)
  - `dto/SimilarQuestionView.java` — `{questionId, title}`
- **수정** `post/QuestionService.java` — `create()` tx 안에서 `community.question.posted` OutboxEntry 저장
- **수정** `post/CommunityController.java` — `GET /community/questions/similar?q=` 추가
- **수정** `build.gradle.kts` — spring-kafka·spring-boot-kafka 활성 + test(spring-kafka-test·awaitility)
- **수정** `application.yml` — kafka(producer/consumer) + `devpath.ai-svc.base-url`
- **수정** `application-test.yml`(test) — kafka bootstrap placeholder(EmbeddedKafka가 주입) + ai-svc base-url

테스트 `src/test/java/ai/devpath/community/`:
- `outbox/OutboxRelayTest.java`(EmbeddedKafka, relayOnce 발행 단언) — learning 미러
- `seed/CommunitySeedConsumerIT.java`(EmbeddedKafka — seed.ready DONE consume→답변/메타/임베딩 영속, 멱등 중복 1건, FAILED 경로)
- `seed/SimilarQuestionMatcherTest.java`(실 DB pgvector, 768 검증·0.20 임계)
- `seed/SimilarQuestionApiTest.java`(MockMvc — EmbeddingClient mock→similar, embed 실패 시 빈배열)
- `post/QuestionOutboxTest.java`(MockMvc 또는 서비스 — 질문 작성 후 outbox 1건 적재 단언)

---

## Task B2-1: deps 활성화 + Kafka 설정 + 컨텍스트 기동

**Files:**
- Modify: `build.gradle.kts`(spring-kafka·spring-boot-kafka 활성 + test deps)
- Modify: `application.yml`(kafka + ai-svc base-url)
- Modify: `src/test/resources/application-test.yml`(kafka·ai-svc base-url)
- Create: `config/KafkaConfig.java`(consumer ErrorHandler — poison skip)
- Test: 기존 `CommunityContextTest`가 kafka 빈 포함 기동되는지(재실행)

**Interfaces:**
- Produces: `KafkaTemplate<String,String>`(Boot 자동구성, producer 설정), consumer 인프라. 이후 태스크가 사용.

- [ ] **Step 1: build.gradle.kts — kafka 활성 + test deps**

`dependencies`에서 주석 해제(37-39행 실측):
```kotlin
	implementation("org.springframework.kafka:spring-kafka")
	implementation("org.springframework.boot:spring-boot-kafka")
```
(redis 줄은 그대로 주석 유지 — B2 불필요.)

test 블록에 추가(ai-svc 미러):
```kotlin
	testImplementation("org.springframework.kafka:spring-kafka-test")
	testImplementation("org.awaitility:awaitility")
```

- [ ] **Step 2: application.yml — kafka + ai-svc base-url**

`spring:` 아래 추가(learning producer/consumer 미러):
```yaml
  kafka:
    bootstrap-servers: ${KAFKA_BOOTSTRAP:localhost:9092}
    consumer:
      group-id: devpath-community
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.apache.kafka.common.serialization.StringDeserializer
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.apache.kafka.common.serialization.StringSerializer
```
`devpath:` 아래 추가(learning `RestAiPathClient` base-url 규약 미러):
```yaml
  ai-svc:
    base-url: ${AI_SVC_URI:http://localhost:8081}
    timeout: ${AI_SVC_TIMEOUT:PT5S}
```
또한 `@EnableScheduling`이 필요(OutboxRelayScheduler `@Scheduled`). `CommunityApplication`에 `@EnableScheduling` 추가(B2-2에서 함께; 본 태스크는 설정만).

- [ ] **Step 3: application-test.yml — kafka placeholder + ai-svc base-url**

EmbeddedKafka가 `spring.kafka.bootstrap-servers`를 주입하므로 test yml에는 consumer group + ai-svc base-url만 둔다(부트스트랩은 EmbeddedKafka가 덮어씀):
```yaml
  kafka:
    consumer:
      group-id: devpath-community-test
      auto-offset-reset: earliest
devpath:
  ai-svc:
    base-url: http://localhost:9 # 테스트 기본(미사용; mock 교체). 실패 graceful 검증용으로 닿지 않는 포트
```
(이미 있는 datasource/flyway/jpa/jwt 블록은 유지. `devpath` 키 병합 주의 — 기존 `auth.jwt-secret` 아래에 `ai-svc` 추가.)

- [ ] **Step 4: config/KafkaConfig.java — poison-skip ErrorHandler**

ai-svc `ReviewKafkaConfig` 축소 미러(재시도 3회 후 로그만; community는 멱등 영속이라 recover에서 별도 영속 불요 — 단순 로깅):
```java
package ai.devpath.community.config;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.listener.DefaultErrorHandler;
import org.springframework.util.backoff.ExponentialBackOff;

/** 시드 컨슈머 에러 핸들러: 일시 오류 지수백오프 재시도(3회), 소진 시 로그(멱등 영속이라 별도 보상 불요). */
@Configuration
public class KafkaConfig {

  private static final Logger log = LoggerFactory.getLogger(KafkaConfig.class);

  @Bean
  public DefaultErrorHandler communityErrorHandler() {
    ExponentialBackOff backOff = new ExponentialBackOff(1000L, 2.0);
    backOff.setMaxAttempts(3L);
    return new DefaultErrorHandler(this::recover, backOff);
  }

  private void recover(ConsumerRecord<?, ?> record, Exception ex) {
    log.error("community seed consume 재시도 소진 — skip offset={} value={}",
        record.offset(), record.value(), ex);
  }
}
```

- [ ] **Step 5: Run context test → PASS**

Run: `DB_URL=jdbc:postgresql://localhost:5432/devpath_citest DB_USER=devpath DB_PASSWORD=localdev ./gradlew test --tests "ai.devpath.community.CommunityContextTest"`
Expected: PASS(kafka 빈 포함 컨텍스트 기동). 실패 시 의존성/yml 오타 점검.

- [ ] **Step 6: Commit**

```bash
git add devpath-community-svc/build.gradle.kts \
  devpath-community-svc/src/main/resources/application.yml \
  devpath-community-svc/src/test/resources/application-test.yml \
  devpath-community-svc/src/main/java/ai/devpath/community/config/KafkaConfig.java
git commit -m "feat(community): spring-kafka 활성 + Kafka 설정 + ai-svc base-url (B2-1)"
```

---

## Task B2-2: outbox 미러 + question.posted 발행

**Files:**
- Create: `outbox/OutboxEntry.java`·`OutboxRepository.java`·`OutboxRelay.java`·`OutboxRelayScheduler.java`(learning 복제)
- Modify: `CommunityApplication.java`(`@EnableScheduling`)
- Modify: `post/QuestionService.java`(create tx에서 OutboxEntry 저장)
- Test: `outbox/OutboxRelayTest.java`(EmbeddedKafka), `post/QuestionOutboxTest.java`(작성→outbox 적재)

**Interfaces:**
- Consumes: `KafkaTemplate`(B2-1), `JsonMapper`(Boot 자동구성), `CommunityQuestionPostedEvent`(shared).
- Produces: `OutboxRelay.relayOnce()`. `QuestionService.create()`가 `community.question.posted` payload 적재.

- [ ] **Step 1: Write failing OutboxRelayTest (EmbeddedKafka)**

learning `OutboxRelayTest` 미러(토픽만 community.question.posted):
```java
package ai.devpath.community.outbox;

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
@EmbeddedKafka(partitions = 1, topics = {"community.question.posted"}, bootstrapServersProperty = "spring.kafka.bootstrap-servers")
class OutboxRelayTest {

  @Autowired OutboxRepository outbox;
  @Autowired OutboxRelay relay;
  @Autowired ConsumerFactory<String, String> cf;
  @Autowired EmbeddedKafkaBroker broker;

  @Test
  void relayPublishesUnpublishedRowAndMarksPublished() {
    OutboxEntry e = new OutboxEntry();
    e.setAggregateType("community_question");
    e.setAggregateId("555");
    e.setEventType("community.question.posted");
    e.setPayload("{\"questionId\":555}");
    e.setCreatedAt(Instant.now());
    Long id = outbox.save(e).getId();

    int published = relay.relayOnce();
    assertTrue(published >= 1);
    assertTrue(outbox.findById(id).orElseThrow().getPublishedAt() != null, "published_at 설정");

    try (Consumer<String, String> c = cf.createConsumer("t-grp", "t")) {
      broker.consumeFromAnEmbeddedTopic(c, "community.question.posted");
      ConsumerRecords<String, String> recs = KafkaTestUtils.getRecords(c);
      boolean found = StreamSupport.stream(recs.spliterator(), false)
          .anyMatch(r -> r.value().contains("555"));
      assertTrue(found, "발행 레코드에 questionId=555 포함");
    }
  }
}
```
Run: `./gradlew test --tests "ai.devpath.community.outbox.OutboxRelayTest"` → FAIL(outbox 클래스 없음).

- [ ] **Step 2: outbox/ 4종 복제 (learning 미러, 패키지만 변경)**

`OutboxEntry.java`(learning `outbox/OutboxEntry.java` 그대로, 패키지 `ai.devpath.community.outbox`):
```java
package ai.devpath.community.outbox;

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
`OutboxRepository.java`:
```java
package ai.devpath.community.outbox;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OutboxRepository extends JpaRepository<OutboxEntry, Long> {
  List<OutboxEntry> findTop100ByPublishedAtIsNullOrderByCreatedAtAsc();
}
```
`OutboxRelay.java`(learning 그대로):
```java
package ai.devpath.community.outbox;

import java.time.Instant;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class OutboxRelay {

  private static final Logger log = LoggerFactory.getLogger(OutboxRelay.class);
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
        log.warn("outbox relay 발행 실패(eventType={}, aggregateId={}) — 미발행 유지, 다음 주기 재시도",
            e.getEventType(), e.getAggregateId(), ex);
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
`OutboxRelayScheduler.java`(learning 그대로 — `@Profile("!test")`):
```java
package ai.devpath.community.outbox;

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

- [ ] **Step 3: CommunityApplication @EnableScheduling**

```java
// CommunityApplication.java 클래스 위 어노테이션 추가
import org.springframework.scheduling.annotation.EnableScheduling;
@EnableScheduling
```
(기존 `@SpringBootApplication`과 함께. `@Profile("!test")` 스케줄러가 prod에서만 동작.)

- [ ] **Step 4: Run OutboxRelayTest → PASS**

Run: `./gradlew test --tests "ai.devpath.community.outbox.OutboxRelayTest"` → PASS.

- [ ] **Step 5: Write failing QuestionOutboxTest (작성→outbox 적재)**

```java
package ai.devpath.community.post;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.devpath.community.outbox.OutboxEntry;
import ai.devpath.community.outbox.OutboxRepository;
import ai.devpath.community.post.dto.CreateQuestionRequest;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import tools.jackson.databind.json.JsonMapper;
import ai.devpath.shared.event.CommunityQuestionPostedEvent;

@SpringBootTest
@ActiveProfiles("test")
class QuestionOutboxTest {

  @Autowired QuestionService questions;
  @Autowired OutboxRepository outbox;
  @Autowired JsonMapper jsonMapper;

  @Test
  void createPersistsQuestionPostedOutboxEntry() throws Exception {
    long before = outbox.count();
    var view = questions.create(4242L,
        new CreateQuestionRequest("아웃박스질문", "본문내용", List.of("kafka")));
    assertTrue(outbox.count() > before, "outbox 1건 이상 적재");

    OutboxEntry entry = outbox.findAll().stream()
        .filter(e -> "community.question.posted".equals(e.getEventType()))
        .filter(e -> e.getAggregateId().equals(String.valueOf(view.id())))
        .findFirst().orElseThrow();
    assertEquals("community_question", entry.getAggregateType());
    CommunityQuestionPostedEvent ev =
        jsonMapper.readValue(entry.getPayload(), CommunityQuestionPostedEvent.class);
    assertEquals(view.id(), ev.questionId());
    assertEquals(4242L, ev.userId());
    assertEquals("아웃박스질문", ev.title());
    assertEquals("본문내용", ev.bodyMd());
  }
}
```
Run: `./gradlew test --tests "ai.devpath.community.post.QuestionOutboxTest"` → FAIL(create가 outbox 미적재).

- [ ] **Step 6: QuestionService.create() — OutboxEntry 발행 (같은 tx)**

`QuestionService`에 `OutboxRepository`·`JsonMapper` 주입 추가(생성자 파라미터 확장, 기존 필드 유지). `create()`의 `return detail(...)` **직전**에 outbox 적재:
```java
// 필드
private final ai.devpath.community.outbox.OutboxRepository outbox;
private final tools.jackson.databind.json.JsonMapper jsonMapper;
// 생성자에 OutboxRepository outbox, JsonMapper jsonMapper 추가 후 this.outbox=outbox; this.jsonMapper=jsonMapper;

// create() 내부, postTags 저장 루프 뒤 / return 전:
ai.devpath.shared.event.CommunityQuestionPostedEvent event =
    new ai.devpath.shared.event.CommunityQuestionPostedEvent(
        java.util.UUID.randomUUID(), java.time.Instant.now(),
        userId, p.getId(), p.getId(), req.title(), req.bodyMd());
ai.devpath.community.outbox.OutboxEntry entry = new ai.devpath.community.outbox.OutboxEntry();
entry.setAggregateType("community_question");
entry.setAggregateId(String.valueOf(p.getId()));
entry.setEventType(ai.devpath.shared.event.CommunityQuestionPostedEvent.EVENT_TYPE);
entry.setPayload(jsonMapper.writeValueAsString(event));
entry.setCreatedAt(java.time.Instant.now());
outbox.save(entry);
```
> 주의: `questionId`와 `postId`는 같은 값(question PK = post id, B1 실측 `CommunityQuestion.postId = post.id`). 설계 §4 이벤트는 둘 다 동봉 → 둘 다 `p.getId()`.
> `jsonMapper.writeValueAsString`은 Jackson 3(tools.jackson)에서 checked 예외 미발생(unchecked) — try/catch 불요. (B1 ai-svc `ReviewPersistenceService` 실측 패턴과 동일; 컴파일 에러 시 메서드 시그니처 확인.)

- [ ] **Step 7: Run QuestionOutboxTest + 기존 B1 테스트 → PASS**

Run: `./gradlew test --tests "ai.devpath.community.post.QuestionOutboxTest" --tests "ai.devpath.community.post.QnaMockMvcTest"`
Expected: 둘 다 PASS(B1 create 테스트가 outbox 추가로 깨지지 않음 — create 반환 계약 불변).

- [ ] **Step 8: Commit**

```bash
git add devpath-community-svc/src/main/java/ai/devpath/community/outbox/ \
  devpath-community-svc/src/main/java/ai/devpath/community/CommunityApplication.java \
  devpath-community-svc/src/main/java/ai/devpath/community/post/QuestionService.java \
  devpath-community-svc/src/test/java/ai/devpath/community/outbox/OutboxRelayTest.java \
  devpath-community-svc/src/test/java/ai/devpath/community/post/QuestionOutboxTest.java
git commit -m "feat(community): outbox 미러 + question.posted 발행 (B2-2)"
```

---

## Task B2-3: community_ai_answers 엔티티 + CommunitySeedConsumer (멱등 영속)

**Files:**
- Create: `seed/CommunityAiAnswer.java`·`CommunityAiAnswerRepository.java`
- Create: `seed/CommunitySeedService.java`·`CommunitySeedConsumer.java`
- Test: `seed/CommunitySeedConsumerIT.java`(EmbeddedKafka — DONE/멱등/FAILED)

**Interfaces:**
- Consumes: `CommunitySeedReadyEvent`(shared), B1 `CommunityAnswerRepository`·`CommunityQuestionRepository`, `JdbcTemplate`(임베딩 UPDATE), `JsonMapper`.
- Produces: `community.seed.ready` 소비 → `community_answers`(is_ai_generated=true)·`community_ai_answers`(PK=question_id)·`community_questions.question_embedding` 영속. 멱등(UNIQUE question_id).

- [ ] **Step 1: Write failing CommunitySeedConsumerIT**

3 시나리오: DONE(영속), 멱등(중복 이벤트 → ai_answers 1건), FAILED(content 없음·status=FAILED). 사전 질문은 `QuestionService.create`로 생성(존재하는 question_id 필요 — FK).
```java
package ai.devpath.community.seed;

import static org.awaitility.Awaitility.await;
import static org.assertj.core.api.Assertions.assertThat;

import ai.devpath.community.post.QuestionService;
import ai.devpath.community.post.dto.CreateQuestionRequest;
import ai.devpath.community.post.CommunityAnswerRepository;
import ai.devpath.shared.event.CommunitySeedReadyEvent;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.test.context.ActiveProfiles;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest
@ActiveProfiles("test")
@EmbeddedKafka(partitions = 1, topics = {"community.seed.ready"}, bootstrapServersProperty = "spring.kafka.bootstrap-servers")
class CommunitySeedConsumerIT {

  @Autowired KafkaTemplate<String, String> kafka;
  @Autowired JsonMapper jsonMapper;
  @Autowired QuestionService questions;
  @Autowired CommunityAnswerRepository answers;
  @Autowired CommunityAiAnswerRepository aiAnswers;
  @Autowired JdbcTemplate jdbc;

  private long newQuestion() {
    return questions.create(70L, new CreateQuestionRequest("seed q", "body", List.of())).id();
  }

  private static List<Double> emb768() {
    return java.util.stream.DoubleStream.generate(() -> 0.01).limit(768).boxed().toList();
  }

  @Test
  void consumesDoneAndPersistsAnswerMetaEmbedding() throws Exception {
    long qid = newQuestion();
    var ev = new CommunitySeedReadyEvent(UUID.randomUUID(), Instant.now(), qid,
        "DONE", "AI 초안 답변", "mock", emb768(), null);
    kafka.send("community.seed.ready", String.valueOf(qid), jsonMapper.writeValueAsString(ev));

    await().atMost(Duration.ofSeconds(20)).untilAsserted(() ->
        assertThat(aiAnswers.findById(qid)).isPresent());

    var ai = aiAnswers.findById(qid).orElseThrow();
    assertThat(ai.getStatus()).isEqualTo("DONE");
    assertThat(ai.getContent()).isEqualTo("AI 초안 답변");
    assertThat(ai.getAnswerId()).isNotNull();
    // community_answers에 is_ai_generated 답변 1건
    assertThat(answers.findByQuestionIdOrderByCreatedAtAsc(qid).stream()
        .anyMatch(a -> a.isAiGenerated() && "AI 초안 답변".equals(a.getBodyMd()))).isTrue();
    // 임베딩 UPDATE 됐는지(네이티브)
    Integer cnt = jdbc.queryForObject(
        "select count(*) from community_questions where post_id = ? and question_embedding is not null",
        Integer.class, qid);
    assertThat(cnt).isEqualTo(1);
  }

  @Test
  void duplicateEventIsIdempotent() throws Exception {
    long qid = newQuestion();
    var ev = new CommunitySeedReadyEvent(UUID.randomUUID(), Instant.now(), qid,
        "DONE", "중복답변", "mock", emb768(), null);
    String payload = jsonMapper.writeValueAsString(ev);
    kafka.send("community.seed.ready", String.valueOf(qid), payload);
    await().atMost(Duration.ofSeconds(20)).untilAsserted(() ->
        assertThat(aiAnswers.findById(qid)).isPresent());
    // 같은 questionId로 재전달(다른 eventId)
    var ev2 = new CommunitySeedReadyEvent(UUID.randomUUID(), Instant.now(), qid,
        "DONE", "중복답변2", "mock", emb768(), null);
    kafka.send("community.seed.ready", String.valueOf(qid), jsonMapper.writeValueAsString(ev2));
    Thread.sleep(2000); // 두 번째 처리 시도 시간
    // ai_answers는 여전히 1건, community_answers AI 답변도 1건(중복 no-op)
    assertThat(answers.findByQuestionIdOrderByCreatedAtAsc(qid).stream()
        .filter(a -> a.isAiGenerated()).count()).isEqualTo(1L);
    assertThat(aiAnswers.findById(qid).orElseThrow().getContent()).isEqualTo("중복답변");
  }

  @Test
  void failedStatusRecordedWithoutAnswer() throws Exception {
    long qid = newQuestion();
    var ev = new CommunitySeedReadyEvent(UUID.randomUUID(), Instant.now(), qid,
        "FAILED", null, "mock", null, "LLM_FAILED");
    kafka.send("community.seed.ready", String.valueOf(qid), jsonMapper.writeValueAsString(ev));
    await().atMost(Duration.ofSeconds(20)).untilAsserted(() ->
        assertThat(aiAnswers.findById(qid)).isPresent());
    var ai = aiAnswers.findById(qid).orElseThrow();
    assertThat(ai.getStatus()).isEqualTo("FAILED");
    assertThat(ai.getErrorCode()).isEqualTo("LLM_FAILED");
    assertThat(answers.findByQuestionIdOrderByCreatedAtAsc(qid).stream()
        .anyMatch(a -> a.isAiGenerated())).isFalse();
  }
}
```
Run: `./gradlew test --tests "ai.devpath.community.seed.CommunitySeedConsumerIT"` → FAIL.

- [ ] **Step 2: CommunityAiAnswer 엔티티 + Repository**

`community_ai_answers`(PK=question_id, B1 마이그레이션 실측: question_id·answer_id·model_used·prompt_version·content·reference_links JSONB·status·error_code·generated_at):
```java
package ai.devpath.community.seed;

import jakarta.persistence.*;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "community_ai_answers")
public class CommunityAiAnswer {
  @Id @Column(name = "question_id") private Long questionId;
  @Column(name = "answer_id") private Long answerId;
  @Column(name = "model_used") private String modelUsed;
  @Column(name = "prompt_version") private String promptVersion;
  @Column private String content;
  @JdbcTypeCode(SqlTypes.JSON) @Column(name = "reference_links", nullable = false)
  private String referenceLinks = "[]";
  @Column(nullable = false) private String status;
  @Column(name = "error_code") private String errorCode;
  @Column(name = "generated_at", insertable = false, updatable = false) private Instant generatedAt;

  public Long getQuestionId() { return questionId; }
  public void setQuestionId(Long v) { this.questionId = v; }
  public Long getAnswerId() { return answerId; }
  public void setAnswerId(Long v) { this.answerId = v; }
  public String getModelUsed() { return modelUsed; }
  public void setModelUsed(String v) { this.modelUsed = v; }
  public String getPromptVersion() { return promptVersion; }
  public void setPromptVersion(String v) { this.promptVersion = v; }
  public String getContent() { return content; }
  public void setContent(String v) { this.content = v; }
  public String getReferenceLinks() { return referenceLinks; }
  public void setReferenceLinks(String v) { this.referenceLinks = v; }
  public String getStatus() { return status; }
  public void setStatus(String v) { this.status = v; }
  public String getErrorCode() { return errorCode; }
  public void setErrorCode(String v) { this.errorCode = v; }
  public Instant getGeneratedAt() { return generatedAt; }
}
```
> `generated_at`은 DB default `now()` → `insertable=false`. (B1 엔티티 `created_at` 패턴 동일.)
```java
package ai.devpath.community.seed;

import org.springframework.data.jpa.repository.JpaRepository;

public interface CommunityAiAnswerRepository extends JpaRepository<CommunityAiAnswer, Long> {
}
```

- [ ] **Step 3: CommunitySeedService (멱등 영속 + 임베딩 UPDATE)**

멱등 = `community_ai_answers.findById(questionId).isPresent()`면 no-op(이미 처리). DONE면 `CommunityAnswer`(is_ai_generated=true, author_id=null) 저장 후 `community_ai_answers`(answer_id=저장된 answer.id, status=DONE). 임베딩 있으면 JdbcTemplate 네이티브 `update community_questions set question_embedding = cast(? as vector)`. FAILED면 답변 미생성·`community_ai_answers`(status=FAILED·error_code·content=null).
```java
package ai.devpath.community.seed;

import ai.devpath.community.post.CommunityAnswer;
import ai.devpath.community.post.CommunityAnswerRepository;
import ai.devpath.shared.event.CommunitySeedReadyEvent;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CommunitySeedService {

  private static final Logger log = LoggerFactory.getLogger(CommunitySeedService.class);

  private final CommunityAnswerRepository answers;
  private final CommunityAiAnswerRepository aiAnswers;
  private final JdbcTemplate jdbc;

  public CommunitySeedService(CommunityAnswerRepository answers,
      CommunityAiAnswerRepository aiAnswers, JdbcTemplate jdbc) {
    this.answers = answers;
    this.aiAnswers = aiAnswers;
    this.jdbc = jdbc;
  }

  @Transactional
  public void apply(CommunitySeedReadyEvent event) {
    long qid = event.questionId();
    // 멱등: 이미 처리된 질문이면 no-op
    if (aiAnswers.existsById(qid)) {
      log.info("community.seed.ready 중복 — no-op questionId={}", qid);
      return;
    }
    CommunityAiAnswer meta = new CommunityAiAnswer();
    meta.setQuestionId(qid);
    meta.setModelUsed(event.provider());
    meta.setStatus(event.status());

    if ("DONE".equals(event.status()) && event.content() != null) {
      CommunityAnswer answer = new CommunityAnswer();
      answer.setQuestionId(qid);
      answer.setAuthorId(null); // AI
      answer.setBodyMd(event.content());
      answer.setAiGenerated(true);
      answer = answers.save(answer);
      meta.setAnswerId(answer.getId());
      meta.setContent(event.content());
      updateEmbedding(qid, event.questionEmbedding());
    } else {
      meta.setErrorCode(event.errorCode());
      // DONE이지만 best-effort 임베딩이 있을 수 있음(D-4)
      updateEmbedding(qid, event.questionEmbedding());
    }
    aiAnswers.save(meta);
  }

  private void updateEmbedding(long questionId, List<Double> embedding) {
    if (embedding == null) return;
    if (embedding.size() != 768) {
      log.warn("질문 임베딩 차원 불일치({}) — 스킵 questionId={}", embedding.size(), questionId);
      return;
    }
    String literal = toVectorLiteral(embedding);
    jdbc.update("update community_questions set question_embedding = cast(? as vector) where post_id = ?",
        literal, questionId);
  }

  private String toVectorLiteral(List<Double> embedding) {
    StringBuilder sb = new StringBuilder("[");
    for (int i = 0; i < embedding.size(); i++) {
      if (i > 0) sb.append(',');
      Double v = embedding.get(i);
      if (v == null || v.isNaN() || v.isInfinite()) {
        throw new IllegalArgumentException("embedding contains invalid value");
      }
      sb.append(v);
    }
    return sb.append(']').toString();
  }
}
```
> 멱등 키 = `community_ai_answers` PK(question_id) 존재 여부. `existsById` 선체크 + (동시 중복은) PK 충돌 시 예외→ErrorHandler 재시도에서 다시 existsById=true로 no-op 수렴. (설계 D-6 "insert-if-absent".)

- [ ] **Step 4: CommunitySeedConsumer (@KafkaListener)**

ai-svc `ReviewConsumer` 미러(역직렬화 실패 skip):
```java
package ai.devpath.community.seed;

import ai.devpath.shared.event.CommunitySeedReadyEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

@Component
public class CommunitySeedConsumer {

  private static final Logger log = LoggerFactory.getLogger(CommunitySeedConsumer.class);

  private final CommunitySeedService seedService;
  private final JsonMapper jsonMapper;

  public CommunitySeedConsumer(CommunitySeedService seedService, JsonMapper jsonMapper) {
    this.seedService = seedService;
    this.jsonMapper = jsonMapper;
  }

  @KafkaListener(topics = CommunitySeedReadyEvent.EVENT_TYPE, groupId = "devpath-community")
  public void onSeedReady(String payload) {
    CommunitySeedReadyEvent event;
    try {
      event = jsonMapper.readValue(payload, CommunitySeedReadyEvent.class);
    } catch (Exception e) {
      log.warn("CommunitySeedReadyEvent 역직렬화 실패 — skip: {}", payload, e);
      return; // poison 무한재시도 방지
    }
    seedService.apply(event);
  }
}
```

- [ ] **Step 5: Run CommunitySeedConsumerIT → PASS**

Run: `./gradlew test --tests "ai.devpath.community.seed.CommunitySeedConsumerIT"`
Expected: 3 tests PASS. 멱등 테스트 실패 시 `existsById` 선체크/PK 확인. 임베딩 실패 시 vector 캐스팅/차원 확인.

- [ ] **Step 6: Commit**

```bash
git add devpath-community-svc/src/main/java/ai/devpath/community/seed/ \
  devpath-community-svc/src/test/java/ai/devpath/community/seed/CommunitySeedConsumerIT.java
git commit -m "feat(community): CommunitySeedConsumer 멱등 영속(답변/메타/임베딩) (B2-3)"
```

---

## Task B2-4: EmbeddingClient + SimilarQuestionMatcher + GET /community/questions/similar

**Files:**
- Create: `seed/EmbeddingClient.java`(ai-svc /ai/embed RestClient)
- Create: `seed/SimilarQuestionMatcher.java`(pgvector JdbcTemplate)
- Create: `seed/dto/SimilarQuestionView.java`
- Modify: `post/CommunityController.java`(similar 엔드포인트)
- Test: `seed/SimilarQuestionMatcherTest.java`(실 DB), `seed/SimilarQuestionApiTest.java`(MockMvc, embed mock)

**Interfaces:**
- Produces: `GET /community/questions/similar?q={text}` → `List<SimilarQuestionView{long questionId, String title}>`. EmbeddingClient.embed(text)→768 → matcher top-K(거리<0.20). embed 실패 시 빈 배열(graceful).

- [ ] **Step 1: Write failing SimilarQuestionMatcherTest (실 DB pgvector)**

질문 2건 생성 후 임베딩 직접 UPDATE(하나는 쿼리와 가깝게, 하나는 멀게) → match가 가까운 것만 반환:
```java
package ai.devpath.community.seed;

import static org.assertj.core.api.Assertions.assertThat;

import ai.devpath.community.post.QuestionService;
import ai.devpath.community.post.dto.CreateQuestionRequest;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class SimilarQuestionMatcherTest {

  @Autowired QuestionService questions;
  @Autowired SimilarQuestionMatcher matcher;
  @Autowired JdbcTemplate jdbc;

  private void setEmbedding(long qid, List<Double> emb) {
    StringBuilder sb = new StringBuilder("[");
    for (int i = 0; i < emb.size(); i++) { if (i>0) sb.append(','); sb.append(emb.get(i)); }
    sb.append(']');
    jdbc.update("update community_questions set question_embedding = cast(? as vector) where post_id = ?",
        sb.toString(), qid);
  }
  private static List<Double> vec(double base) {
    List<Double> v = new ArrayList<>(); for (int i=0;i<768;i++) v.add(base); return v;
  }

  @Test
  void returnsOnlyCloseQuestions() {
    long near = questions.create(80L, new CreateQuestionRequest("가까운질문 "+System.nanoTime(), "b", List.of())).id();
    long far = questions.create(80L, new CreateQuestionRequest("먼질문 "+System.nanoTime(), "b", List.of())).id();
    setEmbedding(near, vec(0.05));
    setEmbedding(far, vec(0.9));
    List<Double> query = vec(0.05); // near와 동일 방향(거리≈0)

    var results = matcher.match(query, 10);
    assertThat(results.stream().map(SimilarQuestionView::questionId)).contains(near);
    assertThat(results.stream().map(SimilarQuestionView::questionId)).doesNotContain(far);
  }

  @Test
  void rejectsWrongDimension() {
    try {
      matcher.match(List.of(0.1, 0.2), 10);
      org.junit.jupiter.api.Assertions.fail("768 차원 검증 기대");
    } catch (IllegalArgumentException expected) { /* ok */ }
  }
}
```
> 거리 임계 0.20: vec(0.05) 두 벡터는 동일 방향이라 코사인거리≈0(<0.20) → near 포함. vec(0.9) vs vec(0.05)는 동일 방향(모두 양수 상수배)이라 코사인거리도 0에 가까움 — **주의**: 상수 벡터는 방향이 같아 코사인거리가 0. 따라서 `far`도 거리≈0이 됨. **테스트 보정**: far는 방향이 다른 벡터로 설정(예: 일부 음수). `vec`를 방향이 다르게: near=모두 +0.05, far=교대 부호(+0.05,-0.05,...)로 직교에 가깝게 → 코사인거리≈1.0(>0.20)로 제외. (구현 시 far 벡터를 직교/반대 방향으로 생성.)

수정 `vec`/far 생성(코사인 거리 검증이 성립하도록):
```java
  private static List<Double> alt() { // 교대 부호 → near와 직교에 가까움(코사인거리 ~1)
    List<Double> v = new ArrayList<>();
    for (int i=0;i<768;i++) v.add(i % 2 == 0 ? 0.05 : -0.05);
    return v;
  }
  // far: setEmbedding(far, alt());  query: vec(0.05)
```

Run: `./gradlew test --tests "ai.devpath.community.seed.SimilarQuestionMatcherTest"` → FAIL(matcher 없음).

- [ ] **Step 2: SimilarQuestionView + SimilarQuestionMatcher**

```java
package ai.devpath.community.seed.dto;
public record SimilarQuestionView(long questionId, String title) {}
```
learning `ContentEmbeddingMatcher` 패턴(768 검증·`<=> cast(? as vector)`·거리<0.20). `community_questions` join `community_posts`로 title:
```java
package ai.devpath.community.seed;

import ai.devpath.community.seed.dto.SimilarQuestionView;
import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class SimilarQuestionMatcher {

  private static final double MAX_DISTANCE = 0.20; // 코사인 유사도 >= 0.80

  private final JdbcTemplate jdbc;

  public SimilarQuestionMatcher(JdbcTemplate jdbc) {
    this.jdbc = jdbc;
  }

  public List<SimilarQuestionView> match(List<Double> queryEmbedding, int limit) {
    String vector = toVectorLiteral(queryEmbedding);
    String sql = """
        select q.post_id as question_id, p.title as title,
               q.question_embedding <=> cast(? as vector) as distance
        from community_questions q
        join community_posts p on p.id = q.post_id
        where q.question_embedding is not null
          and p.status = 'PUBLISHED'
          and (q.question_embedding <=> cast(? as vector)) < ?
        order by q.question_embedding <=> cast(? as vector), q.post_id desc
        limit ?
        """;
    return jdbc.query(sql,
        (rs, rowNum) -> new SimilarQuestionView(rs.getLong("question_id"), rs.getString("title")),
        vector, vector, MAX_DISTANCE, vector, limit);
  }

  private String toVectorLiteral(List<Double> embedding) {
    if (embedding == null || embedding.size() != 768) {
      throw new IllegalArgumentException("embedding must be 768 dimensions");
    }
    StringBuilder sb = new StringBuilder("[");
    for (int i = 0; i < embedding.size(); i++) {
      if (i > 0) sb.append(',');
      Double v = embedding.get(i);
      if (v == null || v.isNaN() || v.isInfinite()) {
        throw new IllegalArgumentException("embedding contains invalid value");
      }
      sb.append(v);
    }
    return sb.append(']').toString();
  }
}
```

- [ ] **Step 3: Run SimilarQuestionMatcherTest → PASS**

Run: `./gradlew test --tests "ai.devpath.community.seed.SimilarQuestionMatcherTest"` → PASS(2 tests).

- [ ] **Step 4: EmbeddingClient (ai-svc /ai/embed)**

learning `RestAiPathClient.embed` 패턴 — 단, 단일 text → List<Double> 768. ai-svc 계약은 `{texts:[...]}` → `{embeddings:[[...]]}` (실측 `EmbedRequest`/`EmbedResponse`):
```java
package ai.devpath.community.seed;

import java.time.Duration;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class EmbeddingClient {

  private final RestClient restClient;

  public EmbeddingClient(
      @Value("${devpath.ai-svc.base-url:http://localhost:8081}") String baseUrl,
      @Value("${devpath.ai-svc.timeout:PT5S}") Duration timeout) {
    var rf = new SimpleClientHttpRequestFactory();
    rf.setConnectTimeout(timeout);
    rf.setReadTimeout(timeout);
    this.restClient = RestClient.builder().baseUrl(baseUrl).requestFactory(rf).build();
  }

  /** ai-svc /ai/embed 호출. 실패 시 EmbeddingUnavailableException(상위가 graceful 처리). */
  public List<Double> embed(String text) {
    try {
      EmbedResponse res = restClient.post()
          .uri("/ai/embed")
          .body(new EmbedRequest(List.of(text)))
          .retrieve()
          .body(EmbedResponse.class);
      if (res == null || res.embeddings() == null || res.embeddings().isEmpty()
          || res.embeddings().get(0) == null || res.embeddings().get(0).size() != 768) {
        throw new EmbeddingUnavailableException("ai-svc embed response invalid");
      }
      return res.embeddings().get(0);
    } catch (RestClientException e) {
      throw new EmbeddingUnavailableException("ai-svc embed failed", e);
    }
  }

  record EmbedRequest(List<String> texts) {}
  record EmbedResponse(List<List<Double>> embeddings) {}
}
```
`EmbeddingUnavailableException`:
```java
package ai.devpath.community.seed;
public class EmbeddingUnavailableException extends RuntimeException {
  public EmbeddingUnavailableException(String msg) { super(msg); }
  public EmbeddingUnavailableException(String msg, Throwable cause) { super(msg, cause); }
}
```

- [ ] **Step 5: Write failing SimilarQuestionApiTest (MockMvc, embed mock)**

`EmbeddingClient`를 `@MockitoBean`으로 교체 → similar API가 matcher 거쳐 결과/그레이스풀 반환:
```java
package ai.devpath.community.seed;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import ai.devpath.community.post.QuestionService;
import ai.devpath.community.post.dto.CreateQuestionRequest;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class SimilarQuestionApiTest {

  @Autowired MockMvc mvc;
  @Autowired QuestionService questions;
  @Autowired JdbcTemplate jdbc;
  @MockitoBean EmbeddingClient embeddingClient;

  private static List<Double> vec(double b){List<Double> v=new ArrayList<>();for(int i=0;i<768;i++)v.add(b);return v;}

  @Test
  void similarReturnsMatchesWhenEmbedSucceeds() throws Exception {
    String title = "유사질문대상 " + System.nanoTime();
    long qid = questions.create(90L, new CreateQuestionRequest(title, "b", List.of())).id();
    StringBuilder sb=new StringBuilder("[");for(int i=0;i<768;i++){if(i>0)sb.append(',');sb.append(0.05);}sb.append(']');
    jdbc.update("update community_questions set question_embedding = cast(? as vector) where post_id = ?", sb.toString(), qid);
    when(embeddingClient.embed(anyString())).thenReturn(vec(0.05));

    mvc.perform(get("/community/questions/similar?q=" + title).with(jwt().jwt(j -> j.subject("90"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$[?(@.questionId==" + qid + ")]").exists());
  }

  @Test
  void similarReturnsEmptyWhenEmbedFails() throws Exception {
    when(embeddingClient.embed(anyString()))
        .thenThrow(new EmbeddingUnavailableException("down"));
    mvc.perform(get("/community/questions/similar?q=anything").with(jwt().jwt(j -> j.subject("90"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(0));
  }

  @Test
  void blankQueryReturnsEmpty() throws Exception {
    mvc.perform(get("/community/questions/similar?q=").with(jwt().jwt(j -> j.subject("90"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(0));
  }
}
```
Run: `./gradlew test --tests "ai.devpath.community.seed.SimilarQuestionApiTest"` → FAIL(엔드포인트 없음).

- [ ] **Step 6: Controller similar 엔드포인트 (graceful)**

`CommunityController`에 `EmbeddingClient`·`SimilarQuestionMatcher` 주입(생성자 확장, 기존 유지) + :
```java
  @GetMapping("/questions/similar")
  public ResponseEntity<List<SimilarQuestionView>> similar(@RequestParam(required = false) String q) {
    if (q == null || q.isBlank()) return ResponseEntity.ok(List.of());
    try {
      List<Double> embedding = embeddingClient.embed(q);
      return ResponseEntity.ok(similarQuestionMatcher.match(embedding, 5));
    } catch (EmbeddingUnavailableException e) {
      log.warn("유사질문 임베딩 실패 — 빈 결과 반환: {}", e.getMessage());
      return ResponseEntity.ok(List.of());
    }
  }
```
필요한 import: `ai.devpath.community.seed.EmbeddingClient`·`EmbeddingUnavailableException`·`SimilarQuestionMatcher`·`ai.devpath.community.seed.dto.SimilarQuestionView` + slf4j Logger 필드. **주의**: `/questions/similar`가 `/questions/{id}`(B1, `@PathVariable long id`)보다 먼저/구체 매핑되어야 함 — Spring은 구체 경로(`/similar`)를 변수 경로보다 우선하나, `{id}`가 `long`이라 "similar"는 바인딩 실패→similar 매핑으로 감. 안전을 위해 similar 매핑을 명시(별도 메서드로 충분).

- [ ] **Step 7: Run SimilarQuestionApiTest → PASS**

Run: `./gradlew test --tests "ai.devpath.community.seed.SimilarQuestionApiTest"` → PASS(3 tests).

- [ ] **Step 8: Commit**

```bash
git add devpath-community-svc/src/main/java/ai/devpath/community/seed/ \
  devpath-community-svc/src/main/java/ai/devpath/community/post/CommunityController.java \
  devpath-community-svc/src/test/java/ai/devpath/community/seed/SimilarQuestionMatcherTest.java \
  devpath-community-svc/src/test/java/ai/devpath/community/seed/SimilarQuestionApiTest.java
git commit -m "feat(community): EmbeddingClient + SimilarQuestionMatcher + similar 엔드포인트 (B2-4)"
```

---

## Task B2-5: 전체 검증 + 빌드

- [ ] **Step 1: Full suite**

Run: `DB_URL=jdbc:postgresql://localhost:5432/devpath_citest DB_USER=devpath DB_PASSWORD=localdev ./gradlew test`
Expected: 전체 PASS — B1(Context·Repository·Qna·Vote·Tag) + B2(OutboxRelay·QuestionOutbox·CommunitySeedConsumerIT·SimilarQuestionMatcher·SimilarQuestionApi).

- [ ] **Step 2: Full build (CI 동등)**

Run: `DB_URL=jdbc:postgresql://localhost:5432/devpath_citest DB_USER=devpath DB_PASSWORD=localdev ./gradlew build`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: (필요 시) 잔여 커밋**

플랜 외 보정이 있으면 의미 단위로 커밋.

---

## PR + 머지

```bash
git push -u origin feat/slice8-community-events
gh pr create --repo DevPathAi/devpath-community-svc --base develop \
  --title "feat(community): 슬라이스 #8 B2 — 이벤트 왕복 + 유사질문" \
  --body "B2: outbox 미러 + community.question.posted 발행 + CommunitySeedConsumer(멱등 영속) + EmbeddingClient + SimilarQuestionMatcher + GET /community/questions/similar. EmbeddedKafka IT. ai-svc 호출은 테스트 mock. 설계 §3(D-1·D-4·D-5·D-6)·§5(community-svc B2)."
# CI 대기
gh pr checks <n> --watch --interval 15
# 녹색 시 머지
gh pr merge <n> --merge --delete-branch
```
CI 실패 시 `gh run view <id> --log-failed`로 원인 분석(B1 교훈: postgres image pgvector·flyway 활성·@ActiveProfiles("test")) 후 수정·재푸시.

---

## Self-Review (스킬 체크리스트)

**1. Spec coverage**(설계서 §1.2 DoD·§5 community-svc B2 대비):
- outbox 미러 → B2-2 ✅ · question.posted 발행(같은 tx) → B2-2 ✅ · CommunitySeedConsumer(seed.ready 멱등 UNIQUE) → B2-3 ✅ · 임베딩 UPDATE(JdbcTemplate 네이티브) → B2-3 ✅ · EmbeddingClient(/ai/embed) → B2-4 ✅ · SimilarQuestionMatcher(pgvector 0.20) → B2-4 ✅ · GET /questions/similar(graceful) → B2-4 ✅
- ai-svc 시드 워커(seed.ready 발행 측) → **빌드 C**(범위 외) ✅ · gateway → D · frontend → E

**2. Placeholder scan**: 각 스텝 실제 코드/명령. outbox 4종은 learning 그대로 복제(패키지만). getter/setter 명시.

**3. Type consistency**: `CommunitySeedReadyEvent`(questionId long·status·content·provider·questionEmbedding List<Double>·errorCode) ↔ 서비스 분기. EmbeddingClient는 ai-svc `EmbedRequest{texts}`/`EmbedResponse{embeddings}` 계약 일치(embeddings[0]). `JsonMapper`=tools.jackson(Jackson3, Boot 자동구성, ai-svc 실측). 임베딩 768 일관(matcher·seed UPDATE 둘 다 검증).

> ⚠️ 구현 주의:
> ① **JsonMapper 패키지**는 `tools.jackson.databind.json.JsonMapper`(Jackson 3, Boot 4 자동구성). `com.fasterxml`가 아님(ai-svc 실측).
> ② **멱등**은 `community_ai_answers` PK(question_id) `existsById` 선체크. 동시 중복 시 PK 충돌→ErrorHandler 재시도→existsById=true 수렴.
> ③ **OutboxRelayScheduler `@Profile("!test")`** — 테스트는 스케줄러 비활성. IT는 consumer(@KafkaListener)만 검증(seed.ready) 또는 relayOnce 직접.
> ④ **EmbeddedKafka** `bootstrapServersProperty = "spring.kafka.bootstrap-servers"`로 부트스트랩 주입(learning/ai-svc 실측).
> ⑤ **similar 경로 우선순위**: `/questions/{id}`(long)와 `/questions/similar` 공존 — "similar"는 long 바인딩 실패라 similar 매핑으로 라우팅(안전).
> ⑥ **author_id=null**(AI 답변) — B1 `CommunityAnswer.authorId`는 nullable(마이그레이션 `author_id BIGINT`(NULL 허용) 실측).
> ⑦ **B1 create 테스트 회귀** — create에 outbox 추가해도 반환 DTO(QuestionDetailView) 불변이라 QnaMockMvcTest 안 깨짐. 반드시 재실행 확인.
> ⑧ **코사인거리 테스트 벡터** — 상수 벡터끼리는 방향 동일(거리≈0). far는 교대 부호 등 직교 벡터로 설정해야 0.20 임계 검증 성립.
