# 슬라이스 #2 빌드 C — platform-svc 진단완료 소비 → onboarding_status 전이 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** platform-svc가 `AssessmentCompletedEvent`(Kafka `learning.assessment.completed`)를 소비해, 해당 사용자의 `users.onboarding_status`를 PENDING→IN_PROGRESS로 멱등 전이한다. (DONE은 슬라이스 #3 범위.)

**Architecture:** 슬라이스 #1 2b `WelcomeNotificationConsumer` 패턴 그대로 — `@KafkaListener`로 payload(String)를 `JsonMapper`(Jackson 3)로 역직렬화하고, 사용자 상태가 PENDING일 때만 IN_PROGRESS로 갱신(멱등). platform은 이미 shared·spring-kafka에 의존한다(추가 의존 없음).

**Tech Stack:** Spring Boot 4.0.7 · Spring Kafka · Jackson 3(`tools.jackson.databind.json.JsonMapper`) · JPA · JUnit 5 · EmbeddedKafka · Awaitility.

## Global Constraints

- 레포 절대조건: 추측 금지 · **테스트 우선** · 문제 시 코드 분석.
- 브랜치: develop 분기 → develop PR, CI 녹색 후 merge commit.
- **선행**: 빌드 A shared main 릴리스로 `AssessmentCompletedEvent`가 GitHub Packages에 publish됨(platform이 새 클래스 소비하려면 필요). 로컬은 shared 캐시 purge 후 `--refresh-dependencies`.
- 소비자 groupId는 기존 컨슈머(`devpath-platform`)와 동일 그룹 사용(application.yml `spring.kafka.consumer.group-id: devpath-platform`).
- 전이 규칙: **현재 PENDING일 때만** IN_PROGRESS로. 이미 IN_PROGRESS/DONE이면 무변동(멱등). 사용자 미존재면 무시(로그).
- Boot 4 = Jackson 3, mock 빈 `@MockitoBean`, 모든 `@SpringBootTest`에 `@ActiveProfiles("test")`.

---

## File Structure

- Create: `src/main/java/ai/devpath/platform/onboarding/AssessmentCompletedConsumer.java` — Kafka 소비 + 상태 전이
- Create: `src/test/java/ai/devpath/platform/onboarding/AssessmentStatusTransitionIT.java` — EmbeddedKafka 끝단간

> 기존 `WelcomeNotificationConsumer`(notification 패키지)와 책임 분리 위해 `onboarding` 패키지 신설.

---

## Task 1: AssessmentCompletedConsumer + 멱등 상태 전이

**Files:**
- Create: `src/main/java/ai/devpath/platform/onboarding/AssessmentCompletedConsumer.java`
- Create: `src/test/java/ai/devpath/platform/onboarding/AssessmentStatusTransitionIT.java`

**Interfaces:**
- Consumes: `UserRepository`(findById, save), `JsonMapper`, `AssessmentCompletedEvent`(shared: userId 등).
- Produces: `@KafkaListener(topics = AssessmentCompletedEvent.EVENT_TYPE, groupId = "devpath-platform")` 메서드. 부수효과: `users.onboarding_status` PENDING→IN_PROGRESS.

- [ ] **Step 1: 끝단간 전이 IT 작성(실패)**

`AssessmentStatusTransitionIT.java` — 실제 user(PENDING) 저장 → outbox 또는 직접 Kafka 발행 → 소비 후 IN_PROGRESS 대기(EventPropagationIT 패턴, KafkaTemplate 직접 발행):

```java
package ai.devpath.platform.onboarding;

import static org.awaitility.Awaitility.await;
import static org.junit.jupiter.api.Assertions.assertEquals;

import ai.devpath.platform.user.User;
import ai.devpath.platform.user.UserRepository;
import ai.devpath.shared.event.AssessmentCompletedEvent;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.test.context.ActiveProfiles;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest
@ActiveProfiles("test")
@EmbeddedKafka(partitions = 1, topics = {"learning.assessment.completed"}, bootstrapServersProperty = "spring.kafka.bootstrap-servers")
class AssessmentStatusTransitionIT {

  @Autowired UserRepository users;
  @Autowired KafkaTemplate<String, String> kafka;
  @Autowired JsonMapper jsonMapper;

  @Test
  void pendingUserBecomesInProgress() throws Exception {
    User u = new User();
    u.setEmail("assess-" + System.nanoTime() + "@example.com");
    u.setNickname("진단유저");
    u.setRole("LEARNER");
    u.setStatus("ACTIVE");
    u.setOnboardingStatus("PENDING");
    u = users.save(u);
    final Long userId = u.getId();

    var event = new AssessmentCompletedEvent(UUID.randomUUID(), Instant.now(),
        100L, userId, "BACKEND_SPRING", "MID", Map.of("spring", 0.7), Instant.now());
    kafka.send(AssessmentCompletedEvent.EVENT_TYPE, String.valueOf(userId), jsonMapper.writeValueAsString(event));

    await().atMost(Duration.ofSeconds(10)).pollInterval(Duration.ofMillis(200))
        .untilAsserted(() ->
            assertEquals("IN_PROGRESS", users.findById(userId).orElseThrow().getOnboardingStatus()));
  }
}
```

- [ ] **Step 2: 실패 확인**

```bash
docker compose up -d
./gradlew test --tests ai.devpath.platform.onboarding.AssessmentStatusTransitionIT
```
Expected: FAIL(소비자 미존재 → 상태 PENDING 유지로 타임아웃).

- [ ] **Step 3: AssessmentCompletedConsumer 구현**

`AssessmentCompletedConsumer.java`:

```java
package ai.devpath.platform.onboarding;

import ai.devpath.platform.user.User;
import ai.devpath.platform.user.UserRepository;
import ai.devpath.shared.event.AssessmentCompletedEvent;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.json.JsonMapper;

@Component
public class AssessmentCompletedConsumer {

  private final UserRepository users;
  private final JsonMapper jsonMapper;

  public AssessmentCompletedConsumer(UserRepository users, JsonMapper jsonMapper) {
    this.users = users;
    this.jsonMapper = jsonMapper;
  }

  @KafkaListener(topics = AssessmentCompletedEvent.EVENT_TYPE, groupId = "devpath-platform")
  @Transactional
  public void onAssessmentCompleted(String payload) {
    AssessmentCompletedEvent event;
    try {
      event = jsonMapper.readValue(payload, AssessmentCompletedEvent.class);
    } catch (Exception e) {
      throw new IllegalStateException("AssessmentCompletedEvent 역직렬화 실패", e);
    }
    User user = users.findById(event.userId()).orElse(null);
    if (user == null) return; // 사용자 미존재 무시
    if ("PENDING".equals(user.getOnboardingStatus())) { // 멱등: PENDING일 때만 전이
      user.setOnboardingStatus("IN_PROGRESS");
      users.save(user);
    }
  }
}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
docker compose up -d
./gradlew test --tests ai.devpath.platform.onboarding.AssessmentStatusTransitionIT
```
Expected: PASS.

- [ ] **Step 5: 멱등 회귀 테스트 추가**

`AssessmentStatusTransitionIT.java`에 이미 DONE인 사용자가 무변동임을 검증하는 테스트 추가:

```java
  @Test
  void doneUserStaysUnchanged() throws Exception {
    User u = new User();
    u.setEmail("done-" + System.nanoTime() + "@example.com");
    u.setNickname("완료유저");
    u.setRole("LEARNER");
    u.setStatus("ACTIVE");
    u.setOnboardingStatus("DONE");
    u = users.save(u);
    final Long userId = u.getId();

    var event = new AssessmentCompletedEvent(UUID.randomUUID(), Instant.now(),
        101L, userId, "BACKEND_SPRING", "SENIOR", Map.of(), Instant.now());
    kafka.send(AssessmentCompletedEvent.EVENT_TYPE, String.valueOf(userId), jsonMapper.writeValueAsString(event));

    // 잠시 소비 시간 후에도 DONE 유지
    Thread.sleep(2000);
    assertEquals("DONE", users.findById(userId).orElseThrow().getOnboardingStatus());
  }
```

```bash
./gradlew test --tests ai.devpath.platform.onboarding.AssessmentStatusTransitionIT
```
Expected: PASS(2 tests).

- [ ] **Step 6: 커밋**

```bash
git add src/main/java/ai/devpath/platform/onboarding/AssessmentCompletedConsumer.java \
        src/test/java/ai/devpath/platform/onboarding/AssessmentStatusTransitionIT.java
git commit -m "feat(onboarding): 진단완료 소비 → onboarding_status PENDING→IN_PROGRESS(멱등)"
```

---

## Task 2: 전체 빌드 + develop PR

- [ ] **Step 1: shared 의존 갱신 확인 + 전체 빌드**

```bash
docker compose up -d
./gradlew clean build --refresh-dependencies
```
Expected: BUILD SUCCESSFUL(새 shared의 AssessmentCompletedEvent 해석), 전 테스트 PASS.

- [ ] **Step 2: develop PR → CI 녹색 → merge**

작업 브랜치(`feat/slice2-platform-status`, develop 분기) → `gh pr create --base develop` → 머지.

> 다음: 빌드 D(gateway 라우트 + frontend 실API).

---

## 검토 반영 보완 (2026-06-18 리뷰 P1 — 구현 시 우선 적용)

### R-C1 (P1-5): read-save 대신 **조건부 update**로 DONE 되돌림 방지
read→check→save는 다른 트랜잭션이 그 사이 사용자를 DONE으로 바꾸면 오래된 PENDING 엔티티를 저장해 IN_PROGRESS로 되돌릴 수 있다. → `UserRepository`에 조건부 update 추가하고 컨슈머는 그것만 호출한다.

`UserRepository`에 추가:

```java
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface UserRepository extends JpaRepository<User, Long> {
  @Modifying
  @Query("update User u set u.onboardingStatus = 'IN_PROGRESS' "
       + "where u.id = :userId and u.onboardingStatus = 'PENDING'")
  int markAssessmentStartedIfPending(@Param("userId") Long userId);
}
```

`AssessmentCompletedConsumer.onAssessmentCompleted`의 read-check-save 블록을 교체:

```java
    int updated = users.markAssessmentStartedIfPending(event.userId());
    // updated==0: 사용자 미존재 또는 이미 IN_PROGRESS/DONE(멱등 무변동). 로그만.
```
(`@Transactional` 유지 — `@Modifying` 실행에 트랜잭션 필요.)

### R-C2 (P1 C): DONE 무변동 테스트의 `Thread.sleep` 제거
부정 검증은 sleep 기반이라 불안정. **컨슈머 메서드 직접 호출 단위 테스트**로 분리해 결정적으로 검증한다(EmbeddedKafka E2E는 PENDING→IN_PROGRESS 긍정 검증만 유지).

```java
@SpringBootTest
@ActiveProfiles("test")
class AssessmentStatusConsumerUnitTest {
  @Autowired AssessmentCompletedConsumer consumer;
  @Autowired UserRepository users;
  @Autowired tools.jackson.databind.json.JsonMapper jsonMapper;

  @Test
  void doneUserStaysDone() throws Exception {
    User u = new User();
    u.setEmail("done-" + System.nanoTime() + "@example.com");
    u.setNickname("완료"); u.setRole("LEARNER"); u.setStatus("ACTIVE");
    u.setOnboardingStatus("DONE");
    u = users.save(u);
    var event = new ai.devpath.shared.event.AssessmentCompletedEvent(
        java.util.UUID.randomUUID(), java.time.Instant.now(), 1L, u.getId(),
        "BACKEND_SPRING", "SENIOR", java.util.Map.of(), java.time.Instant.now());
    consumer.onAssessmentCompleted(jsonMapper.writeValueAsString(event)); // 직접 호출
    assertEquals("DONE", users.findById(u.getId()).orElseThrow().getOnboardingStatus());
  }
}
```
(기존 IT의 `doneUserStaysUnchanged`는 삭제하고 이 단위 테스트로 대체.)

### R-C3 (P1 C): poison message(역직렬화 실패) 처리 전략 명시
역직렬화 실패 시 예외를 던지면 동일 메시지가 무한 재시도된다. → `DefaultErrorHandler`로 **고정 횟수 재시도 후 로그 후 skip**(또는 DLQ)을 구성한다(슬라이스 #1 2b 후속과 동일 방향). 최소 구현: 컨슈머에서 역직렬화 실패는 로그 후 정상 종료(메시지 커밋)로 바꿔 poison 무한루프를 막는다.

```java
  @KafkaListener(topics = AssessmentCompletedEvent.EVENT_TYPE, groupId = "devpath-platform")
  @Transactional
  public void onAssessmentCompleted(String payload) {
    AssessmentCompletedEvent event;
    try {
      event = jsonMapper.readValue(payload, AssessmentCompletedEvent.class);
    } catch (Exception e) {
      log.warn("AssessmentCompletedEvent 역직렬화 실패 — 메시지 skip: {}", payload, e);
      return; // poison 무한재시도 방지(커밋 후 진행). DLQ는 하드닝 후속.
    }
    int updated = users.markAssessmentStartedIfPending(event.userId());
    ...
  }
```
(클래스에 SLF4J `Logger log` 추가.)

---

## Self-Review (작성자 점검 결과)

- **Spec coverage**: 설계서 §2 빌드C, §7 소비(`AssessmentCompletedEvent`→onboarding_status PENDING→IN_PROGRESS 멱등) — 커버. DONE 전이는 범위 외(슬라이스 #3) 준수.
- **Placeholder scan**: 코드 완전 기재. 사용자 미존재 무시·DONE 무변동 명시.
- **Type consistency**: `AssessmentCompletedEvent.userId()`(빌드 A 정의) 사용 일치. `User.getOnboardingStatus()/setOnboardingStatus()`(실제 엔티티) 일치. groupId `devpath-platform`(application.yml) 일치. 토픽 `AssessmentCompletedEvent.EVENT_TYPE`=`learning.assessment.completed` 일치.
- **주의**: 소비는 비동기 → IT는 Awaitility 대기. DONE 무변동 테스트는 짧은 sleep 후 단언(부정 검증이라 결정적 대기 불가 — 2초면 동일 그룹 소비 충분). 실패 시 시간 늘림. 정확-한-번 소비는 슬라이스 #1과 동일하게 베스트에포트(at-least-once + 멱등 전이로 안전).
