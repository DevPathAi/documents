# MD1 슬라이스 #1 — devpath-platform-svc 이벤트 전파(2b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** outbox에 기록된 `UserRegisteredEvent`를 Kafka로 발행(릴레이)하고, 소비자가 환영 알림을 notifications 테이블에 생성하는 이벤트 전파 경로를 완성한다(설계서 D-5 소비처).

**Architecture:** Transactional Outbox 릴레이 = 스케줄러가 `outbox`의 미발행 행(`published_at IS NULL`)을 폴링해 `KafkaTemplate`로 토픽(=`event_type`)에 발행 후 `published_at` 갱신. 소비자 = `@KafkaListener`가 `user.user.registered` 토픽을 구독해 `notifications` 행을 INSERT(환영 알림). notifications 스키마는 devpath-shared가 소유(신규 마이그레이션). 테스트는 `spring-kafka-test`의 `@EmbeddedKafka`로 외부 Kafka 없이 검증.

**Tech Stack:** Java 21 · Spring Boot 4.0.7 · Spring for Apache Kafka · PostgreSQL 17 · JUnit5 · spring-kafka-test(EmbeddedKafka) · devpath-shared.

**선행:** platform 2a(`feat/oauth-auth-core`) develop 머지 완료 + 본 플랜 Task 1(shared notifications 마이그레이션) main 릴리스 완료.

## Global Constraints

- Java 21. 패키지 루트 `ai.devpath.platform`. `ddl-auto: validate` — 스키마는 shared 소유, 엔티티는 매핑만.
- 마이그레이션은 devpath-shared에만 추가(`VYYYYMMDDHHMM__*.sql`, 2a까지의 `V202606171004` 다음 번호). platform에 마이그레이션 금지.
- Kafka 토픽명 = `DomainEvent.eventType()`(예: `user.user.registered`). 토픽은 자동 생성 허용(dev/test) 또는 명시 생성.
- 이벤트 페이로드 = outbox.payload(JSON 문자열, 2a에서 Jackson 직렬화한 `UserRegisteredEvent`).
- 릴레이는 멱등: 발행 성공 행만 `published_at` 설정. 중복 발행 가능성(at-least-once) → 소비자는 멱등(동일 user 환영 알림 중복 방지).
- 비밀값 커밋 금지. 브랜치: 각 레포 develop에서 분기 → develop PR. main 직접 금지(shared 릴리스 PR 제외).

## Preconditions

- platform 2a 머지됨(outbox `OutboxEntry`/`OutboxRepository`, `UserRegisteredEvent` 사용 가능).
- PostgreSQL 가동(로컬 compose). Kafka는 테스트에 EmbeddedKafka 사용 → 외부 Kafka/CI service 불요.
- 브랜치(shared): `git checkout develop && git pull && git checkout -b feat/notifications-schema`. (platform): 2a 머지 후 `git checkout develop && git pull && git checkout -b feat/event-propagation`.

## File Structure

- (shared) `src/main/resources/db/migration/V202606171005__notifications.sql` — notifications 테이블.
- (platform) `config/KafkaConfig.java` — 토픽/직렬화 설정(필요 시).
- (platform) `outbox/OutboxRelay.java` — `@Scheduled` 폴링 → KafkaTemplate 발행 → published_at.
- (platform) `outbox/OutboxRepository.java` — 2a 것에 `findTop100ByPublishedAtIsNullOrderByCreatedAtAsc()` 추가.
- (platform) `notification/Notification.java`·`NotificationRepository.java` — notifications 엔티티/리포지토리.
- (platform) `notification/WelcomeNotificationConsumer.java` — `@KafkaListener`(user.user.registered) → 환영 알림.
- (platform) `src/main/resources/application.yml` — kafka bootstrap, consumer group, scheduling 활성.

---

### Task 1: (shared) notifications 마이그레이션 + main 릴리스

D-8 최소 notifications 테이블을 shared에 추가하고 main 릴리스로 Packages 배포(platform이 매핑·소비).

**Files:**
- (devpath-shared) Create: `src/main/resources/db/migration/V202606171005__notifications.sql`
- (devpath-shared) Modify(test): `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`

**Interfaces:**
- Produces: `notifications(id BIGSERIAL PK, user_id BIGINT FK→users(id) ON DELETE CASCADE, type VARCHAR(40) NOT NULL, title VARCHAR(255) NOT NULL, body TEXT, read_at TIMESTAMPTZ NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())`, index `(user_id, created_at)`.

- [ ] **Step 1: 실패 테스트** — `FlywayMigrationTest.java`에 추가:
```java
  @Test
  void notificationsTableExists() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection();
        var rs = c.getMetaData().getTables(null, "public", "notifications", new String[] {"TABLE"})) {
      assertTrue(rs.next(), "notifications 테이블 필요");
    }
  }
```
- [ ] **Step 2: 실패 확인** — `docker compose down -v && docker compose up -d` 후 `./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.notificationsTableExists"` → FAIL.
- [ ] **Step 3: 마이그레이션** — `V202606171005__notifications.sql`:
```sql
-- 슬라이스 #1 D-8: 최소 알림 테이블(환영 알림 소비자 산출처). 04_API §9 알림 목록 기반.
CREATE TABLE notifications (
  id         BIGSERIAL PRIMARY KEY,
  user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type       VARCHAR(40) NOT NULL,
  title      VARCHAR(255) NOT NULL,
  body       TEXT,
  read_at    TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notifications_user_created ON notifications(user_id, created_at);
-- P1-4: WELCOME 알림은 사용자당 1개(소비 레이스/중복 발행 시 DB가 멱등 보장).
CREATE UNIQUE INDEX uq_notifications_welcome_user ON notifications(user_id) WHERE type = 'WELCOME';
```
> 이 부분 UNIQUE 인덱스로 동시 소비 레이스에서도 두 번째 INSERT는 제약 위반으로 실패한다. 소비자는 `existsByUserIdAndType`(베스트에포트) + INSERT 시 `DataIntegrityViolationException`을 잡아 무시(이미 생성됨)하는 이중 방어를 둔다.
- [ ] **Step 4: 통과 확인** — `./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.notificationsTableExists"` → PASS.
- [ ] **Step 5: 커밋 + develop PR + 머지 + main 릴리스**
```bash
git add src/main/resources/db/migration/V202606171005__notifications.sql src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(schema): notifications 테이블(환영 알림)"
git push -u origin feat/notifications-schema
gh pr create --base develop --head feat/notifications-schema --title "feat: notifications 테이블" --body "D-8 최소 알림 테이블. platform 2b 환영 알림 소비자 산출처."
# CI green 후: gh pr merge --merge
# 이어서 develop→main 릴리스 PR(설계서 D-6) → publish.yml로 Packages 배포
```
- [ ] **Step 6: main 릴리스 + publish 확인** — `gh pr create --base main --head develop ...` 머지 → `gh run list --workflow publish.yml --branch main --limit 1` success 확인.

---

### Task 2: (platform) Kafka 설정 + OutboxRelay

미발행 outbox 행을 Kafka로 발행하고 published_at을 설정한다.

**Files:**
- Modify: `build.gradle.kts`(spring-kafka + spring-kafka-test 추가)
- Modify: `src/main/resources/application.yml`(kafka)
- Modify: `outbox/OutboxRepository.java`(쿼리 추가)
- Create: `outbox/OutboxRelay.java`
- Create(test): `src/test/java/ai/devpath/platform/outbox/OutboxRelayTest.java`

**Interfaces:**
- Consumes: `OutboxRepository`, `KafkaTemplate<String,String>`.
- Produces:
  - `OutboxRepository.findTop100ByPublishedAtIsNullOrderByCreatedAtAsc(): List<OutboxEntry>`.
  - `OutboxRelay.relayOnce(): int` — 미발행 행을 토픽(=eventType)에 key=aggregateId, value=payload로 발행 후 publishedAt=now 저장, 발행 건수 반환. `@Scheduled(fixedDelay=2000)` `relay()` 래퍼.

- [ ] **Step 1: build.gradle.kts** — dependencies에 추가:
```kotlin
	implementation("org.springframework.kafka:spring-kafka")
	testImplementation("org.springframework.kafka:spring-kafka-test")
```
`PlatformApplication`에 `@EnableScheduling` 추가.
- [ ] **Step 2: application.yml** — `spring:` 하위 추가:
```yaml
  kafka:
    bootstrap-servers: ${KAFKA_BOOTSTRAP:localhost:9092}
    consumer:
      group-id: devpath-platform
      auto-offset-reset: earliest
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.apache.kafka.common.serialization.StringSerializer
```
- [ ] **Step 3: 실패 테스트** — `outbox/OutboxRelayTest.java`(EmbeddedKafka + 실DB):
```java
package ai.devpath.platform.outbox;

import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Instant;
import java.util.Map;
import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerRecord;
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
@EmbeddedKafka(partitions = 1, topics = {"user.user.registered"}, bootstrapServersProperty = "spring.kafka.bootstrap-servers")
class OutboxRelayTest {

	@Autowired OutboxRepository outbox;
	@Autowired OutboxRelay relay;
	@Autowired ConsumerFactory<String, String> cf;
	@Autowired EmbeddedKafkaBroker broker;

	@Test
	void relayPublishesUnpublishedRowAndMarksPublished() {
		OutboxEntry e = new OutboxEntry();
		e.setAggregateType("user");
		e.setAggregateId("777");
		e.setEventType("user.user.registered");
		e.setPayload("{\"userId\":777}");
		e.setCreatedAt(Instant.now());
		Long id = outbox.save(e).getId();

		int published = relay.relayOnce();
		assertTrue(published >= 1);
		assertTrue(outbox.findById(id).orElseThrow().getPublishedAt() != null, "published_at 설정");

		try (Consumer<String, String> c = cf.createConsumer("t-grp", "t")) {
			broker.consumeFromAnEmbeddedTopic(c, "user.user.registered");
			ConsumerRecord<String, String> rec = KafkaTestUtils.getSingleRecord(c, "user.user.registered");
			assertTrue(rec.value().contains("777"));
		}
	}
}
```
> 주의: EmbeddedKafka API(`bootstrapServersProperty`·`KafkaTestUtils`)는 spring-kafka-test 기준. 컴파일되는 형태로 확정. consumer 검증이 까다로우면 published_at 설정 + 발행 카운트 검증으로 축소 가능(단, 발행 사실은 반드시 검증).
- [ ] **Step 4: 구현** — `OutboxRepository`에 추가:
```java
	java.util.List<OutboxEntry> findTop100ByPublishedAtIsNullOrderByCreatedAtAsc();
```
`outbox/OutboxRelay.java`:
```java
package ai.devpath.platform.outbox;

import java.time.Instant;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class OutboxRelay {

	private final OutboxRepository outbox;
	private final KafkaTemplate<String, String> kafka;

	public OutboxRelay(OutboxRepository outbox, KafkaTemplate<String, String> kafka) {
		this.outbox = outbox;
		this.kafka = kafka;
	}

	@Scheduled(fixedDelay = 2000)
	public void relay() { relayOnce(); }

	// P0-3: Kafka send는 비동기다. future 성공을 확인한 뒤에만 published_at을 설정한다.
	// 발행 실패 시 해당 행은 미발행 유지(다음 폴링 재시도) + 순서 보장 위해 중단. @Transactional 미사용
	// (각 save 자동 커밋 → 실패 전 성공분은 published로 확정, Kafka를 DB 트랜잭션에 묶지 않음).
	public int relayOnce() {
		var batch = outbox.findTop100ByPublishedAtIsNullOrderByCreatedAtAsc();
		int count = 0;
		for (OutboxEntry e : batch) {
			try {
				kafka.send(e.getEventType(), e.getAggregateId(), e.getPayload())
						.get(5, java.util.concurrent.TimeUnit.SECONDS); // 발행 성공 대기
			} catch (Exception ex) {
				break; // 발행 실패 → published_at 미설정, 이후 행은 다음 주기로
			}
			e.setPublishedAt(Instant.now());
			outbox.save(e);
			count++;
		}
		return count;
	}
}
```
> `KafkaTemplate.send(...)`는 `CompletableFuture<SendResult<K,V>>`(Spring Kafka 4)를 반환한다 — `.get(timeout)`로 broker ack를 확인한다. 반환 타입이 다르면 실제 API에 맞춰 future 완료 확인으로 확정(자체 구현 회피).
- [ ] **Step 4b: 실패 경로 테스트(P0-3)** — Kafka 발행 실패 시 `published_at`이 null로 유지됨을 검증한다. mock `KafkaTemplate`(또는 실패하는 broker 주소)으로 `send(...).get()`이 예외를 던지게 하고, `relayOnce()` 후 해당 outbox 행의 `getPublishedAt()`이 여전히 null임을 단언. (별도 `@SpringBootTest`에서 `@MockitoBean KafkaTemplate` 사용 권장 — EmbeddedKafka 없이 실패 주입.)
- [ ] **Step 5: 통과 확인** — `./gradlew test --tests "ai.devpath.platform.outbox.OutboxRelayTest"` → PASS(발행 성공 + 실패 시 미발행 유지).
- [ ] **Step 6: 커밋** — `git commit -m "feat(outbox): Kafka 릴레이(미발행 행 발행 + published_at)"`.

---

### Task 3: (platform) Notification 엔티티 + 리포지토리

notifications 테이블 매핑 + 멱등 조회.

**Files:**
- Create: `notification/Notification.java`, `notification/NotificationRepository.java`
- Create(test): `src/test/java/ai/devpath/platform/notification/NotificationRepositoryTest.java`

**Interfaces:**
- Produces:
  - `Notification(id Long, userId Long, type String, title String, body String, readAt Instant, createdAt Instant)` — table `notifications`.
  - `NotificationRepository.existsByUserIdAndType(Long userId, String type): boolean`(멱등 가드), `countByUserId(Long): long`.

- [ ] **Step 1: 실패 테스트(P1-5: FK 만족 — `@SpringBootTest`+`UserRepository`로 user 저장 후 그 id 사용)** — `NotificationRepositoryTest.java`:
```java
package ai.devpath.platform.notification;

import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.devpath.platform.user.User;
import ai.devpath.platform.user.UserRepository;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class NotificationRepositoryTest {

	@Autowired NotificationRepository repo;
	@Autowired UserRepository users;

	@Test
	void savesAndChecksExistenceByType() {
		User u = new User();
		u.setEmail("n" + System.nanoTime() + "@example.com");
		u.setNickname("지수"); u.setRole("LEARNER"); u.setStatus("ACTIVE"); u.setOnboardingStatus("PENDING");
		u = users.save(u); // FK 만족용 실제 user

		Notification n = new Notification();
		n.setUserId(u.getId());
		n.setType("WELCOME");
		n.setTitle("환영합니다");
		n.setCreatedAt(Instant.now());
		repo.save(n);

		assertTrue(repo.existsByUserIdAndType(u.getId(), "WELCOME"));
	}
}
```
- [ ] **Step 2~5**: 실패 확인 → 엔티티/리포지토리 작성 → 통과 → 커밋.

`notification/Notification.java`:
```java
package ai.devpath.platform.notification;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "notifications")
public class Notification {
	@Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
	@Column(name = "user_id", nullable = false) private Long userId;
	@Column(nullable = false) private String type;
	@Column(nullable = false) private String title;
	private String body;
	@Column(name = "read_at") private Instant readAt;
	@Column(name = "created_at", nullable = false) private Instant createdAt;

	public Long getId() { return id; }
	public Long getUserId() { return userId; }
	public void setUserId(Long v) { this.userId = v; }
	public String getType() { return type; }
	public void setType(String v) { this.type = v; }
	public String getTitle() { return title; }
	public void setTitle(String v) { this.title = v; }
	public String getBody() { return body; }
	public void setBody(String v) { this.body = v; }
	public Instant getReadAt() { return readAt; }
	public void setReadAt(Instant v) { this.readAt = v; }
	public Instant getCreatedAt() { return createdAt; }
	public void setCreatedAt(Instant v) { this.createdAt = v; }
}
```
`notification/NotificationRepository.java`:
```java
package ai.devpath.platform.notification;
import org.springframework.data.jpa.repository.JpaRepository;
public interface NotificationRepository extends JpaRepository<Notification, Long> {
	boolean existsByUserIdAndType(Long userId, String type);
	long countByUserId(Long userId);
}
```
커밋: `git commit -m "feat(notification): notifications 엔티티 + 리포지토리"`.

---

### Task 4: (platform) WelcomeNotificationConsumer (@KafkaListener)

`user.user.registered`를 구독해 환영 알림을 멱등 생성한다.

**Files:**
- Create: `notification/WelcomeNotificationConsumer.java`
- Create(test): `src/test/java/ai/devpath/platform/notification/WelcomeNotificationConsumerTest.java`

**Interfaces:**
- Consumes: `NotificationRepository`, `ObjectMapper`, `UserRegisteredEvent`(payload 역직렬화).
- Produces: `@KafkaListener(topics = UserRegisteredEvent.EVENT_TYPE)` `onUserRegistered(String payload)` — `UserRegisteredEvent` 역직렬화 → `existsByUserIdAndType(userId,"WELCOME")` 아니면 Notification(type=WELCOME, title="환영합니다") 저장(멱등).

- [ ] **Step 1: 실패 테스트** — `WelcomeNotificationConsumerTest.java`(소비자 핸들러 직접 호출 단위, 또는 EmbeddedKafka 통합). 단위 권장:
```java
package ai.devpath.platform.notification;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.fasterxml.jackson.databind.ObjectMapper;
import ai.devpath.shared.event.UserRegisteredEvent;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import ai.devpath.platform.user.User;
import ai.devpath.platform.user.UserRepository;

@SpringBootTest
@ActiveProfiles("test")
class WelcomeNotificationConsumerTest {

	@Autowired WelcomeNotificationConsumer consumer;
	@Autowired NotificationRepository notifications;
	@Autowired UserRepository users;
	@Autowired ObjectMapper om;

	@Test
	void createsWelcomeNotificationOnceIdempotently() throws Exception {
		User u = new User();
		u.setEmail("w" + System.nanoTime() + "@example.com");
		u.setNickname("지수"); u.setRole("LEARNER"); u.setStatus("ACTIVE"); u.setOnboardingStatus("PENDING");
		u = users.save(u);
		String payload = om.writeValueAsString(
				new UserRegisteredEvent(UUID.randomUUID(), Instant.now(), u.getId(), "GITHUB", u.getEmail()));

		consumer.onUserRegistered(payload);
		consumer.onUserRegistered(payload); // 중복

		assertEquals(1, notifications.findAll().stream()
				.filter(n -> n.getUserId().equals(u.getId()) && n.getType().equals("WELCOME")).count());
	}
}
```
- [ ] **Step 2~5**: 실패 → 구현 → 통과 → 커밋.

`notification/WelcomeNotificationConsumer.java`:
```java
package ai.devpath.platform.notification;

import ai.devpath.shared.event.UserRegisteredEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class WelcomeNotificationConsumer {

	private static final String TYPE = "WELCOME";
	private final NotificationRepository notifications;
	private final ObjectMapper objectMapper;

	public WelcomeNotificationConsumer(NotificationRepository notifications, ObjectMapper objectMapper) {
		this.notifications = notifications;
		this.objectMapper = objectMapper;
	}

	@KafkaListener(topics = UserRegisteredEvent.EVENT_TYPE, groupId = "devpath-platform")
	public void onUserRegistered(String payload) {
		UserRegisteredEvent event;
		try {
			event = objectMapper.readValue(payload, UserRegisteredEvent.class);
		} catch (Exception e) {
			throw new IllegalStateException("UserRegisteredEvent 역직렬화 실패", e);
		}
		if (notifications.existsByUserIdAndType(event.userId(), TYPE)) return; // 베스트에포트 멱등
		Notification n = new Notification();
		n.setUserId(event.userId());
		n.setType(TYPE);
		n.setTitle("환영합니다!");
		n.setBody("DevPath AI에 가입하신 것을 환영합니다. 진단을 시작해 보세요.");
		n.setCreatedAt(Instant.now());
		try {
			notifications.save(n);
		} catch (org.springframework.dao.DataIntegrityViolationException dup) {
			// P1-4: 동시 소비 레이스 — uq_notifications_welcome_user 위반 = 이미 생성됨. 무시(멱등).
		}
	}
}
```
커밋: `git commit -m "feat(notification): UserRegisteredEvent 환영 알림 소비자(멱등)"`.

---

### Task 5: 끝단간 통합(릴레이→Kafka→소비자→알림) + 전체 빌드 + PR

**Files:** Create(test): `src/test/java/ai/devpath/platform/EventPropagationIT.java`

- [ ] **Step 1: 통합 테스트** — `@SpringBootTest @EmbeddedKafka`: outbox에 UserRegisteredEvent 1행 저장 → `relay.relayOnce()` → 소비자가 알림 생성될 때까지 awaitility/폴링 → notifications에 WELCOME 1행 검증. (Kafka 비동기 → `org.awaitility:awaitility` testImplementation 추가 또는 KafkaTestUtils 대기.)
- [ ] **Step 2: 전체 빌드** — PG 가동 + `./gradlew clean build` → BUILD SUCCESSFUL.
- [ ] **Step 3: develop PR + CI green + 머지**
```bash
git push -u origin feat/event-propagation
gh pr create --base develop --head feat/event-propagation --title "feat: platform-svc 이벤트 전파(2b) — outbox 릴레이 + 환영 알림 소비자" --body "outbox→Kafka 릴레이 + UserRegisteredEvent 소비→notifications. EmbeddedKafka 테스트. 설계서 D-5/D-8."
```
> CI: EmbeddedKafka는 외부 Kafka 불요. notifications 테이블은 Task 1 main 릴리스로 Packages·CI DB(마이그레이션)에 존재해야 함.

---

## Self-Review

**1. Spec coverage:** outbox 릴레이→Kafka 발행(D-5 producer 전파) Task 2 ✓; notifications 테이블(D-8) Task 1 ✓; 환영 알림 소비자(D-5 소비처) Task 4 ✓; 끝단간 Task 5 ✓. provider 토큰 캡처(2a에서 유보)는 본 2b 범위 아님 — 별도 명시 필요 시 후속.
**2. Placeholder scan:** 코드·테스트·명령 포함. EmbeddedKafka/FK 주의는 구현 확정 지시(추상 지시 아님).
**3. Type consistency:** `OutboxEntry`(2a)·`UserRegisteredEvent.EVENT_TYPE`·`Notification` 필드 일관. 토픽=eventType 일관.

**주의(상류 의존):** 본 플랜은 2a 머지 후 실행. Task 1(shared notifications)은 또 한 번의 shared main 릴리스를 요구(D-6 재적용).

## Execution Handoff
Plan complete and saved to `documents/docs/superpowers/plans/2026-06-17-md1-slice1-platform-events-2b.md`.
