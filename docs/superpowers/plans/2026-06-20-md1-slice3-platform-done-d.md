# 슬라이스 #3 빌드 D — devpath-platform-svc LearningPathGeneratedEvent DONE 전이 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `devpath-platform-svc`가 `LearningPathGeneratedEvent`(`learning.path.generated`)를 소비해 `users.onboarding_status`를 `PENDING` 또는 `IN_PROGRESS`에서 `DONE`으로 전이한다. 슬라이스 #2 C의 `AssessmentCompletedEvent → IN_PROGRESS` 소비자 패턴을 그대로 따른다.

**Architecture:** Kafka consumer가 payload를 `LearningPathGeneratedEvent`로 역직렬화하고, JPA bulk update로 조건부 전이한다. read-modify-save를 쓰지 않는다. poison payload는 로그 후 skip해 무한 재시도를 막는다. 멱등성은 `where onboarding_status in ('PENDING','IN_PROGRESS')` 조건이 보장한다.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Spring Kafka · JPA bulk update · PostgreSQL · JUnit 5 · EmbeddedKafka · Awaitility.

## Global Constraints

- 레포 절대조건: 추측 금지 · 테스트 우선 · 문제 시 코드 분석.
- 범위: 빌드 D만 수행한다. learning-svc producer, gateway/frontend는 범위 밖이다.
- DB schema 변경 없음. shared `users.onboarding_status` 기존 enum(`PENDING/IN_PROGRESS/DONE`)만 사용한다.
- shared event는 현재 5필드 `LearningPathGeneratedEvent(eventId, occurredAt, userId, learningPathId, targetTrack)`를 그대로 소비한다.
- 상태 전이는 **조건부 bulk update**만 사용한다.
- `DONE` 사용자는 절대 `IN_PROGRESS`나 다른 상태로 되돌리지 않는다.
- 없는 user, 이미 `DONE`, poison payload는 오류를 밖으로 던지지 않고 skip/log 처리한다.

---

## File Structure

- Modify: `src/main/java/ai/devpath/platform/user/UserRepository.java`
- Create: `src/main/java/ai/devpath/platform/onboarding/LearningPathGeneratedConsumer.java`
- Create: `src/test/java/ai/devpath/platform/onboarding/LearningPathGeneratedConsumerUnitTest.java`
- Create or Modify: `src/test/java/ai/devpath/platform/onboarding/LearningPathDoneTransitionIT.java`

---

## Task 1: repository 조건부 update

**Files:**
- Modify: `UserRepository.java`

- [ ] **Step 1: 메서드 추가**

```java
@Modifying
@Query("update User u set u.onboardingStatus = 'DONE' "
     + "where u.id = :userId and u.onboardingStatus in ('PENDING', 'IN_PROGRESS')")
int markOnboardingDoneIfPathGenerated(@Param("userId") Long userId);
```

- [ ] **Step 2: 단위 테스트에서 상태별 결과 검증**

테스트 케이스:
- PENDING → DONE
- IN_PROGRESS → DONE
- DONE → DONE 유지, update count 0
- missing user → update count 0

---

## Task 2: LearningPathGeneratedEvent consumer

**Files:**
- Create: `LearningPathGeneratedConsumer.java`

- [ ] **Step 1: consumer 작성**

```java
@KafkaListener(topics = LearningPathGeneratedEvent.EVENT_TYPE, groupId = "devpath-platform")
@Transactional
public void onLearningPathGenerated(String payload) { ... }
```

역직렬화 실패 시:

```java
log.warn("LearningPathGeneratedEvent 역직렬화 실패 — 메시지 skip: {}", payload, e);
return;
```

- [ ] **Step 2: 무변동 debug log**

update count 0이면 user 미존재 또는 이미 DONE으로 보고 debug log만 남긴다.

---

## Task 3: direct unit test

**Files:**
- Create: `LearningPathGeneratedConsumerUnitTest.java`

- [ ] **Step 1: direct consumer tests**

`JsonMapper`로 실제 event를 직렬화해 consumer method를 직접 호출한다.

검증:
- PENDING user → DONE
- IN_PROGRESS user → DONE
- DONE user → DONE 유지
- malformed JSON 호출 후 예외 없음

---

## Task 4: EmbeddedKafka integration

**Files:**
- Create: `LearningPathDoneTransitionIT.java`

- [ ] **Step 1: Kafka topic test**

`@EmbeddedKafka(topics = {"learning.path.generated"})`에서 event를 publish하고 Awaitility로 user status가 DONE이 되는지 확인한다.

테스트 케이스:
- `IN_PROGRESS` user receives `learning.path.generated` → DONE

- [ ] **Step 2: 기존 AssessmentStatusTransitionIT와 충돌 확인**

기존 `learning.assessment.completed` consumer는 계속 PENDING → IN_PROGRESS만 수행해야 한다.

---

## Task 5: verification

- [ ] **Step 1: focused tests**

```powershell
cd devpath-platform-svc
.\gradlew.bat test --tests "ai.devpath.platform.onboarding.*LearningPath*"
```

- [ ] **Step 2: existing onboarding consumer tests**

```powershell
.\gradlew.bat test --tests "ai.devpath.platform.onboarding.*"
```

- [ ] **Step 3: full build**

```powershell
.\gradlew.bat clean build
```

---

## Acceptance Checklist

- [ ] Consumer listens to `learning.path.generated`.
- [ ] Valid `LearningPathGeneratedEvent` transitions PENDING → DONE.
- [ ] Valid `LearningPathGeneratedEvent` transitions IN_PROGRESS → DONE.
- [ ] DONE remains DONE and is not downgraded.
- [ ] Missing user is a no-op.
- [ ] Malformed payload is logged and skipped.
- [ ] Existing `AssessmentCompletedEvent` PENDING → IN_PROGRESS behavior remains intact.
- [ ] No schema changes required.

---

## Self-Review

- **Spec coverage:** 설계서 §6/§9 Build D, R-8/R-세부정정의 `where onboarding_status in ('PENDING','IN_PROGRESS')`와 poison skip을 커버한다.
- **Pattern alignment:** 슬라이스 #2 C `AssessmentCompletedConsumer`와 같은 KafkaListener + JsonMapper + conditional repository update 패턴이다.
- **Risk:** shared package가 아직 `LearningPathGeneratedEvent`를 publish하지 않은 환경이면 compile이 실패한다. 그 경우 Build A/shared release가 선행 조건이다.
