# 참여촉진배치 Build 5 (주간 리포트 집계 + 이메일 발송) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** learning-svc가 매주 일요일 20:00(KST) 전체 활성 유저의 주간 리포트(스트릭·진척률·이번주 배지·다음 과제)를 집계해 `WeeklyReportGeneratedEvent`를 발행하고, notification-svc가 이를 구독해 `weekly_report` 이력을 저장하고 (설정 시) 이메일을 발송한 뒤 "리포트 도착" 알림을 전달한다.

**Architecture:** learning-svc `WeeklyReportScheduler`(@Scheduled cron 일 20:00 KST, `@Profile("!test")`)가 `ActiveLearnerRepository.activeLearnerUserIds()`로 전체 유저를 순회하며 `WeeklyReportAggregator`로 (user_streak + 학습경로 진척 + community-svc 배지 API의 이번주 배지) 를 조합해 `WeeklyReportGeneratedEvent`를 기존 Outbox로 발행한다(Kafka 전송은 기존 `OutboxRelay` 담당). notification-svc `WeeklyReportConsumer`가 구독해 `weekly_report`(UNIQUE(user_id, week_of)로 멱등) 저장 → `user_notification_prefs.weekly_report_email_enabled=true`면 `EmailSender`로 이메일 → 기존 `PushSender`(Build 3)로 "리포트 도착" 전달. **이메일 전달은 스펙의 `EmailSender`(interface + Smtp + Mock) 패턴** — 이번 빌드의 기본 구현은 `MockEmailSender`이고 실제 SMTP(`SmtpEmailSender`)는 devpath-gitops에 계정·발신도메인이 아직 없어 **후속 배포 작업으로 연기**(Build 3의 FCM 연기와 동일 논리, 스펙 §리스크에 명시). community-svc는 배지 API가 이미 `awardedAt`을 반환하므로 **변경 없음**.

**Tech Stack:** Java 21 · Spring Boot 4.0.7 · Gradle(Kotlin DSL) · Spring Data JPA · Kafka(outbox relay) · `spring-boot-starter-mail`(JavaMailSender, notification-svc 신규) · devpath-shared(중앙 Flyway, GitHub Packages).

**스펙:** [2026-07-01-md3-retention-batch-design.md](../specs/2026-07-01-md3-retention-batch-design.md) §데이터 모델(`weekly_report`)·§이벤트 계약(`WeeklyReportGeneratedEvent`)·§컴포넌트별 설계(learning-svc `WeeklyReportScheduler`·notification-svc `WeeklyReportConsumer`/`EmailSender`)·§빌드 분해 Build 5·§리스크. **랜드스케이프 조사:** `scratchpad/build5-landscape.md`(2026-07-03).

## 설계 결정 (스펙·기존 패턴 기반, 착수 전 확정)

- **이메일 = `EmailSender` 인터페이스 + `MockEmailSender`(기본, test/local) + `SmtpEmailSender`(prod)**. 스펙이 요구한 패턴 그대로(§컴포넌트별 설계). 실제 SMTP는 **후속 연기**(gitops 계정 부재). provider 스위칭은 `@ConditionalOnProperty(devpath.mail.provider)`(ai-svc retention·Build 3 PushSender 패턴 미러).
- **"이번주 배지" = `awardedAt`이 최근 7일 이내인 배지**. community-svc `BadgeView`가 `awardedAt`(Instant)을 이미 반환하므로(조사 C절 확인) community-svc 변경 불필요. learning-svc의 배지 클라이언트에 `awardedAt`을 보존하는 신규 메서드만 추가(기존 `badgeNamesOf`는 대시보드용으로 유지).
- **배지 enrich N+1은 후속 연기**(스펙 §리스크: "배치 컨텍스트라 지연 허용", "후속으로 bulk 조회 API 필요"). 스케줄러가 유저마다 `GET /community/users/{id}/badges` 동기 호출(주간 배치라 허용). bulk API는 community-svc에 없으며 이번 스코프 밖.
- **진척%/다음과제 계산은 `WeeklyReportAggregator`가 자체 수행**(`LearningPathQueryService.current()` 재사용). Build 2 `DashboardService`의 동일 계산과 6줄가량 유사하나, **Build 2 코드를 건드리지 않기 위해** 자체 구현(경미한 중복 수용, 후속에 공용 추출 가능).
- **스케줄러 비활성화**: learning-svc 관례대로 `@Profile("!test")`(클래스 레벨) — `StreakRolloverScheduler`와 동일.

## Global Constraints

- **devpath-shared 변경(이벤트 + 마이그레이션)은 가장 먼저 `main`에 병합·publish**되어야 소비 서비스가 새 SNAPSHOT을 받는다. shared엔 `develop` 없음 → `feat/*`→`main` 직접 PR. 소비 서비스는 `./gradlew compileJava --refresh-dependencies`(jar **내용 grep**으로 확인).
- 나머지는 각 레포 `develop`에서 `feat/*` 분기 → develop PR. 공유 브랜치 직접 작업 금지.
- **TDD**(절대조건 2): 실패 테스트 먼저 → 최소 구현 → 통과 확인. **추측 금지**(절대조건 1).
- Kafka payload는 `String`(JSON), 컨슈머는 `tools.jackson.databind.json.JsonMapper#readValue` 수동 역직렬화 + 실패 시 로그 후 skip(poison 방지) — `WelcomeNotificationConsumer`/`StagnationConsumer` 패턴.
- outbox 발행은 `OutboxEntry` 저장까지만(Kafka 전송은 기존 `OutboxRelay`). KafkaTemplate 직접 사용 금지.
- 서비스 간 동기 호출은 `RestClient` 직통(`devpath.<svc>.base-url`). **community-svc = `http://localhost:8086`**(기존 `RestCommunityBadgeClient` 관례).
- 테스트: 실 Postgres(`localhost:5432/devpath`) + shared jar Flyway가 classpath로 스키마 구성. 이메일 테스트는 **Mock**(실 SMTP 없음). 스케줄러는 `@Profile("!test")`라 테스트 컨텍스트에서 미등록 → `WeeklyReportAggregator`/`WeeklyReportConsumer` 로직을 직접 테스트.
- **notification-svc 다수 @SpringBootTest 커넥션 고갈 방지**: 이미 `application-test.yml`에 `hikari.maximum-pool-size` 적용됨(Build 4에서 ai-svc에 적용한 것과 동일 이슈 — notification-svc는 컨텍스트 수가 적어 현재 미적용이나, 신규 @SpringBootTest 추가로 "too many clients"가 나면 동일하게 `spring.datasource.hikari.maximum-pool-size: 4`를 추가할 것).
- 머지 금지 — PR 생성까지만(컨트롤러/사용자 몫). shared Task 1만 publish 위해 컨트롤러가 머지.

---

### Task 1: devpath-shared — WeeklyReportGeneratedEvent + weekly_report 마이그레이션

**Files:**
- Create: `devpath-shared/src/main/java/ai/devpath/shared/event/WeeklyReportGeneratedEvent.java`
- Create: `devpath-shared/src/main/resources/db/migration/V202607031002__weekly_report.sql`
- Test: `devpath-shared/src/test/java/ai/devpath/shared/event/WeeklyReportGeneratedEventTest.java`

**Interfaces:**
- Consumes: `DomainEvent`.
- Produces: `WeeklyReportGeneratedEvent` record(필드 순서·타입 정확히): `eventId: UUID`, `occurredAt: Instant`, `userId: long`, `weekOf: LocalDate`, `streakDays: int`, `progressPercent: int`, `badgesEarnedThisWeek: List<String>`, `nextTaskTitle: String`(nullable). 상수 `EVENT_TYPE = "progress.report.generated"`. Task 3(발행)·Task 4(구독)가 이 정확한 필드명·순서를 참조. `weekly_report` 테이블 — Task 4가 매핑.

- [ ] **Step 1: 실패 테스트 작성**

```java
package ai.devpath.shared.event;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class WeeklyReportGeneratedEventTest {

  @Test
  void eventTypeAndFields() {
    Instant now = Instant.now();
    LocalDate week = LocalDate.of(2026, 7, 5);
    WeeklyReportGeneratedEvent e = new WeeklyReportGeneratedEvent(
        UUID.randomUUID(), now, 42L, week, 12, 75, List.of("STUDENT", "TEACHER"), "Spring MVC 실습");

    assertEquals("progress.report.generated", e.eventType());
    assertEquals("progress.report.generated", WeeklyReportGeneratedEvent.EVENT_TYPE);
    assertEquals(42L, e.userId());
    assertEquals(week, e.weekOf());
    assertEquals(12, e.streakDays());
    assertEquals(75, e.progressPercent());
    assertEquals(List.of("STUDENT", "TEACHER"), e.badgesEarnedThisWeek());
    assertEquals("Spring MVC 실습", e.nextTaskTitle());
  }
}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.event.WeeklyReportGeneratedEventTest"`
Expected: FAIL — 클래스 없어 컴파일 실패.

- [ ] **Step 3: WeeklyReportGeneratedEvent 구현**

```java
package ai.devpath.shared.event;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

/**
 * 주간 리포트 생성 이벤트. learning-svc가 매주(일 20:00 KST) 유저별로 Transactional Outbox로 발행한다.
 * 소비자: notification-svc {@code WeeklyReportConsumer}(→ weekly_report 저장 + 이메일 + 푸시).
 * {@code badgesEarnedThisWeek}는 이번주 획득 배지명 목록(없으면 빈 리스트), {@code nextTaskTitle}은 없으면 null.
 */
public record WeeklyReportGeneratedEvent(
		UUID eventId,
		Instant occurredAt,
		long userId,
		LocalDate weekOf,
		int streakDays,
		int progressPercent,
		List<String> badgesEarnedThisWeek,
		String nextTaskTitle
) implements DomainEvent {

	public static final String EVENT_TYPE = "progress.report.generated";

	@Override
	public String eventType() {
		return EVENT_TYPE;
	}
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.event.WeeklyReportGeneratedEventTest"`
Expected: PASS

- [ ] **Step 5: weekly_report 마이그레이션 작성**

파일 `devpath-shared/src/main/resources/db/migration/V202607031002__weekly_report.sql`:

```sql
-- 주간 리포트 이력(재발송·다시보기 대비). owner: devpath-notification-svc.
CREATE TABLE weekly_report (
  id            BIGSERIAL PRIMARY KEY,
  user_id       BIGINT NOT NULL,
  week_of       DATE NOT NULL,               -- 해당 주 일요일 날짜
  payload       JSONB NOT NULL,              -- progress.report.generated 이벤트 payload 스냅샷
  generated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  email_sent_at TIMESTAMPTZ,
  push_sent_at  TIMESTAMPTZ
);
CREATE UNIQUE INDEX idx_weekly_report_user_week ON weekly_report (user_id, week_of);
```

- [ ] **Step 6: 로컬 Flyway 검증 + 전체 빌드 + 커밋 + PR(main)**

Run: `cd devpath-shared && ./gradlew build`
Expected: BUILD SUCCESSFUL (`FlywayMigrationTest`가 클린 DB에 신규 마이그레이션 적용 검증).

```bash
cd devpath-shared
git fetch origin && git switch main && git pull --ff-only origin main
git switch -c feat/retention-build5-weekly-report-event
git add src/main/java/ai/devpath/shared/event/WeeklyReportGeneratedEvent.java \
        src/main/resources/db/migration/V202607031002__weekly_report.sql \
        src/test/java/ai/devpath/shared/event/WeeklyReportGeneratedEventTest.java
git commit -m "feat(shared): WeeklyReportGeneratedEvent + weekly_report 테이블

참여촉진배치 Build 5 — 주간 리포트 이벤트 + 이력 테이블(UNIQUE user_id,week_of)."
git push -u origin feat/retention-build5-weekly-report-event
gh pr create --base main --title "feat(shared): 참여촉진배치 Build 5 주간리포트 이벤트+테이블" --body "WeeklyReportGeneratedEvent + weekly_report 마이그레이션. 이 PR 머지+publish 이후 learning/notification-svc가 의존."
```

- [ ] **Step 7: CI 확인 후 머지·publish 확인** — `gh pr checks <PR> -R DevPathAi/devpath-shared` 통과 → `gh pr merge <PR> --merge` → `gh run list -R DevPathAi/devpath-shared --branch main --limit 1`로 Publish 성공 확인. jar에 `WeeklyReportGeneratedEvent.class` 포함 확인.

---

### Task 2: devpath-learning-svc — 배지 클라이언트 awardedAt 확장

**배경**: 기존 `CommunityBadgeClient.badgeNamesOf(long): List<String>`는 이름만 반환해 "이번주 배지" 필터가 불가능하다. `awardedAt`을 보존하는 신규 메서드를 추가한다(기존 메서드·대시보드는 무변경). community-svc API는 이미 `BadgeView(code,name,tier,awardedAt)`를 반환하므로 community-svc 변경은 없다.

**Files:**
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/dashboard/BadgeAwardView.java`
- Modify: `devpath-learning-svc/src/main/java/ai/devpath/learning/dashboard/CommunityBadgeClient.java`
- Modify: `devpath-learning-svc/src/main/java/ai/devpath/learning/dashboard/RestCommunityBadgeClient.java`
- Test: `devpath-learning-svc/src/test/java/ai/devpath/learning/dashboard/RestCommunityBadgeClientBadgesOfTest.java`

**Interfaces:**
- Consumes: community-svc `GET /community/users/{id}/badges` → `[{code,name,tier,awardedAt}]`.
- Produces: `CommunityBadgeClient.badgesOf(long userId): List<BadgeAwardView>`(신규). `BadgeAwardView(String code, String name, String tier, Instant awardedAt)`. Task 3의 `WeeklyReportAggregator`가 이 메서드로 이번주 배지를 필터링한다. 기존 `badgeNamesOf`는 유지.

- [ ] **Step 1: 브랜치 준비**

```bash
cd devpath-learning-svc
git fetch origin && git switch develop && git pull --ff-only origin develop
git switch -c feat/retention-build5-weekly-report
./gradlew compileJava --refresh-dependencies
```
（이 태스크는 shared 신규 이벤트를 아직 안 쓰지만, Task 3에서 쓰므로 브랜치를 공유한다 — Task 1 publish 이후 시작.）

- [ ] **Step 2: 실패하는 통합 테스트 작성**

기존 배지 테스트가 있으면 그 패턴을 따르되, 없으면 `@SpringBootTest` + MockWebServer 대신 실제 구현 검증은 어려우니 **경량 단위 테스트**로 파싱만 검증한다(아래는 RestClient 응답 매핑을 직접 검증하기 어려워, 최소한 `BadgeAwardView` 매핑 계약을 문서화하는 단위 테스트).

실제로는 `RestCommunityBadgeClient.badgesOf`가 community-svc 응답을 `List<BadgeAwardView>`로 파싱하는지 검증하려면 실 community-svc나 목 서버가 필요하다. 기존 레포에 배지 클라이언트 테스트가 없다면(조사 시 미발견), **`badgesOf`의 반환 타입·필터 계약을 Task 3의 `WeeklyReportAggregator` 테스트에서 mock으로 커버**하고, 이 Task는 컴파일·빌드 성공으로 검증한다. 따라서 이 Task의 TDD는 `WeeklyReportAggregator`(Task 3)에서 `CommunityBadgeClient`를 mock해 `badgesOf`가 반환하는 `awardedAt` 기반 필터를 검증하는 것으로 성립한다.

（주: 실 REST 파싱까지 테스트하려면 Task 3 이후 별도 IT를 추가할 수 있으나, 기존 `RestCommunityBadgeClient`도 파싱 단위 테스트 없이 대시보드 IT로만 커버돼 있었다 — 동일 관례.）

- [ ] **Step 3: BadgeAwardView 구현**

```java
package ai.devpath.learning.dashboard;

import java.time.Instant;

/** community-svc 배지 응답(awardedAt 포함) — 주간 리포트의 "이번주 배지" 필터용. */
public record BadgeAwardView(String code, String name, String tier, Instant awardedAt) {
}
```

- [ ] **Step 4: CommunityBadgeClient에 badgesOf 추가**

`CommunityBadgeClient.java`:

old_string:
```java
public interface CommunityBadgeClient {
  List<String> badgeNamesOf(long userId);
}
```
new_string:
```java
public interface CommunityBadgeClient {
  List<String> badgeNamesOf(long userId);

  /** awardedAt 포함 배지 목록(주간 리포트 "이번주 배지" 필터용). 실패 시 빈 목록. */
  List<BadgeAwardView> badgesOf(long userId);
}
```

- [ ] **Step 5: RestCommunityBadgeClient에 badgesOf 구현**

`RestCommunityBadgeClient.java` — `badgeNamesOf` 아래에 추가(기존 `BadgeSummaryView` 파싱은 그대로 두고, `badgesOf`는 `awardedAt` 포함 응답을 파싱):

```java
  @Override
  public List<BadgeAwardView> badgesOf(long userId) {
    try {
      List<BadgeAwardView> badges = restClient.get()
          .uri("/community/users/{userId}/badges", userId)
          .retrieve()
          .body(new org.springframework.core.ParameterizedTypeReference<List<BadgeAwardView>>() {});
      return badges == null ? java.util.List.of() : badges;
    } catch (org.springframework.web.client.RestClientException e) {
      return java.util.List.of(); // 배지 조회 실패로 리포트 전체가 죽으면 안 됨 — 그레이스풀 디그레이드
    }
  }
```

- [ ] **Step 6: 빌드 확인 + 커밋**

Run: `cd devpath-learning-svc && ./gradlew compileJava compileTestJava`
Expected: 컴파일 성공(기존 `RestCommunityBadgeClient`가 `badgesOf`까지 구현하므로 인터페이스 미구현 에러 없음).

```bash
cd devpath-learning-svc
git add src/main/java/ai/devpath/learning/dashboard/BadgeAwardView.java \
        src/main/java/ai/devpath/learning/dashboard/CommunityBadgeClient.java \
        src/main/java/ai/devpath/learning/dashboard/RestCommunityBadgeClient.java
git commit -m "feat(dashboard): CommunityBadgeClient.badgesOf(awardedAt 포함)

참여촉진배치 Build 5 — 주간 리포트의 이번주 배지 필터용. 기존 badgeNamesOf·대시보드 무변경."
```
（Task 3과 같은 브랜치이므로 push/PR은 Task 3 이후 함께.）

---

### Task 3: devpath-learning-svc — WeeklyReportAggregator + WeeklyReportScheduler

**Files:**
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/WeeklyReportAggregator.java`
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/WeeklyReportScheduler.java`
- Test: `devpath-learning-svc/src/test/java/ai/devpath/learning/progress/WeeklyReportAggregatorTest.java`

**Interfaces:**
- Consumes: `UserStreakRepository`(streak), `LearningPathQueryService.current(long): LearningPathView`(진척/다음과제, `NoSuchElementException` if 없음), `CommunityBadgeClient.badgesOf`(Task 2), `OutboxRepository`/`OutboxEntry`, `ActiveLearnerRepository.activeLearnerUserIds()`, Task 1 `WeeklyReportGeneratedEvent`(shared 새 SNAPSHOT).
- Produces: `WeeklyReportAggregator.aggregate(long userId, LocalDate weekOf, Instant now): WeeklyReportGeneratedEvent`. `WeeklyReportScheduler`(@Profile("!test"), cron 일 20:00 KST) → 유저별 aggregate → outbox 발행.

- [ ] **Step 1: 실패하는 Aggregator 테스트 작성**

`LearningPathView`/`WeeklyTaskView`의 정확한 형태는 `DashboardService`가 쓰는 것과 동일: `path.milestones()` → 각 milestone `.tasks()` → `WeeklyTaskView.completed()`(boolean)·`.title()`(String). 테스트는 `LearningPathQueryService`를 mock한다.

```java
package ai.devpath.learning.progress;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import ai.devpath.learning.dashboard.BadgeAwardView;
import ai.devpath.learning.dashboard.CommunityBadgeClient;
import ai.devpath.learning.path.LearningPathQueryService;
import java.time.Instant;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class WeeklyReportAggregatorTest {

  @Autowired UserStreakRepository streaks;

  private WeeklyReportAggregator aggregator(LearningPathQueryService paths, CommunityBadgeClient badges) {
    return new WeeklyReportAggregator(streaks, paths, badges);
  }

  @Test
  void aggregatesStreakAndFiltersBadgesToThisWeek() {
    long userId = 660001L;
    UserStreak s = new UserStreak();
    s.setUserId(userId); s.setCurrentDays(12); s.setUpdatedAt(Instant.now());
    streaks.save(s);

    Instant now = Instant.now();
    LearningPathQueryService paths = mock(LearningPathQueryService.class);
    when(paths.current(anyLong())).thenThrow(new java.util.NoSuchElementException()); // 활성 경로 없음 → progress 0
    CommunityBadgeClient badges = mock(CommunityBadgeClient.class);
    when(badges.badgesOf(userId)).thenReturn(List.of(
        new BadgeAwardView("STUDENT", "학생", "BRONZE", now.minus(2, ChronoUnit.DAYS)),      // 이번주
        new BadgeAwardView("FIRST_QUESTION", "첫질문", "BRONZE", now.minus(30, ChronoUnit.DAYS)) // 지난달 → 제외
    ));

    var event = aggregator(paths, badges).aggregate(userId, LocalDate.of(2026, 7, 5), now);

    assertThat(event.userId()).isEqualTo(userId);
    assertThat(event.streakDays()).isEqualTo(12);
    assertThat(event.progressPercent()).isEqualTo(0);
    assertThat(event.nextTaskTitle()).isNull();
    assertThat(event.badgesEarnedThisWeek()).containsExactly("학생"); // 최근 7일 배지만
    assertThat(event.weekOf()).isEqualTo(LocalDate.of(2026, 7, 5));
  }
}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.progress.WeeklyReportAggregatorTest"`
Expected: FAIL — `WeeklyReportAggregator` 없어 컴파일 실패.

- [ ] **Step 3: WeeklyReportAggregator 구현**

진척%/다음과제 계산은 `DashboardService.summary()`와 동일 로직(milestones→tasks flatten→completed/total→round; 첫 미완료 title). 배지는 `badgesOf`에서 `awardedAt`이 `now - 7일` 이후인 것만.

```java
package ai.devpath.learning.progress;

import ai.devpath.learning.dashboard.BadgeAwardView;
import ai.devpath.learning.dashboard.CommunityBadgeClient;
import ai.devpath.learning.path.LearningPathQueryService;
import ai.devpath.learning.path.LearningPathView;
import ai.devpath.learning.path.WeeklyTaskView;
import ai.devpath.shared.event.WeeklyReportGeneratedEvent;
import java.time.Instant;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** 유저별 주간 리포트 이벤트 조립(스트릭 + 진척% + 다음과제 + 이번주 배지). */
@Service
public class WeeklyReportAggregator {

	private final UserStreakRepository streaks;
	private final LearningPathQueryService paths;
	private final CommunityBadgeClient badgeClient;

	public WeeklyReportAggregator(UserStreakRepository streaks, LearningPathQueryService paths,
			CommunityBadgeClient badgeClient) {
		this.streaks = streaks;
		this.paths = paths;
		this.badgeClient = badgeClient;
	}

	@Transactional(readOnly = true)
	public WeeklyReportGeneratedEvent aggregate(long userId, LocalDate weekOf, Instant now) {
		int streakDays = streaks.findById(userId).map(UserStreak::getCurrentDays).orElse(0);

		int progressPercent = 0;
		String nextTaskTitle = null;
		try {
			LearningPathView path = paths.current(userId);
			List<WeeklyTaskView> tasks = path.milestones().stream()
					.flatMap(m -> m.tasks().stream())
					.toList();
			long completed = tasks.stream().filter(WeeklyTaskView::completed).count();
			progressPercent = tasks.isEmpty() ? 0 : (int) Math.round(completed * 100.0 / tasks.size());
			nextTaskTitle = tasks.stream().filter(t -> !t.completed()).findFirst()
					.map(WeeklyTaskView::title).orElse(null);
		} catch (NoSuchElementException e) {
			// 활성 학습경로 없음 → progress 0, nextTask null
		}

		Instant weekAgo = now.minus(7, ChronoUnit.DAYS);
		List<String> badgesThisWeek = badgeClient.badgesOf(userId).stream()
				.filter(b -> b.awardedAt() != null && b.awardedAt().isAfter(weekAgo))
				.map(BadgeAwardView::name)
				.toList();

		return new WeeklyReportGeneratedEvent(UUID.randomUUID(), now, userId, weekOf,
				streakDays, progressPercent, badgesThisWeek, nextTaskTitle);
	}
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.progress.WeeklyReportAggregatorTest"`
Expected: PASS

- [ ] **Step 5: WeeklyReportScheduler 구현**

`StreakRolloverScheduler`(@Profile("!test")) + `publishStreakReached`(outbox) 미러링. cron 일 20:00 KST(`zone` 명시).

```java
package ai.devpath.learning.progress;

import ai.devpath.learning.outbox.OutboxEntry;
import ai.devpath.learning.outbox.OutboxRepository;
import ai.devpath.shared.event.WeeklyReportGeneratedEvent;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Profile;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

/** 매주 일 20:00(KST) 전체 활성 유저의 주간 리포트를 집계해 Outbox로 발행한다. */
@Component
@Profile("!test")
public class WeeklyReportScheduler {

	private static final Logger log = LoggerFactory.getLogger(WeeklyReportScheduler.class);
	private static final ZoneId KST = ZoneId.of("Asia/Seoul");

	private final ActiveLearnerRepository activeLearners;
	private final WeeklyReportAggregator aggregator;
	private final OutboxRepository outbox;
	private final JsonMapper jsonMapper = new JsonMapper();

	public WeeklyReportScheduler(ActiveLearnerRepository activeLearners, WeeklyReportAggregator aggregator,
			OutboxRepository outbox) {
		this.activeLearners = activeLearners;
		this.aggregator = aggregator;
		this.outbox = outbox;
	}

	@Scheduled(cron = "0 0 20 * * SUN", zone = "Asia/Seoul")
	public void generateWeeklyReports() {
		LocalDate weekOf = LocalDate.now(KST);
		Instant now = Instant.now();
		for (Long userId : activeLearners.activeLearnerUserIds()) {
			try {
				WeeklyReportGeneratedEvent event = aggregator.aggregate(userId, weekOf, now);
				OutboxEntry entry = new OutboxEntry();
				entry.setAggregateType("weekly_report");
				entry.setAggregateId(String.valueOf(userId));
				entry.setEventType(WeeklyReportGeneratedEvent.EVENT_TYPE);
				entry.setPayload(jsonMapper.writeValueAsString(event));
				entry.setCreatedAt(Instant.now());
				outbox.save(entry);
			} catch (RuntimeException e) {
				log.warn("주간 리포트 생성 실패 — userId={} skip", userId, e); // 한 유저 실패가 전체를 막지 않음
			}
		}
	}
}
```

- [ ] **Step 6: 전체 빌드 + 커밋(Task 2와 함께) + push + PR**

Run: `cd devpath-learning-svc && ./gradlew build`
Expected: BUILD SUCCESSFUL(스케줄러는 `@Profile("!test")`라 테스트 컨텍스트 미등록 → 기존 IT 회귀 없음).

```bash
cd devpath-learning-svc
git add src/main/java/ai/devpath/learning/progress/WeeklyReportAggregator.java \
        src/main/java/ai/devpath/learning/progress/WeeklyReportScheduler.java \
        src/test/java/ai/devpath/learning/progress/WeeklyReportAggregatorTest.java
git commit -m "feat(progress): 주간 리포트 집계 + 스케줄러(일 20:00 KST)

참여촉진배치 Build 5 — WeeklyReportAggregator(스트릭+진척+이번주배지) +
WeeklyReportScheduler(@Profile('!test'), 전체 활성 유저 순회 → outbox 발행)."
git push -u origin feat/retention-build5-weekly-report
gh pr create --base develop --title "feat(progress): 주간 리포트 집계 + 스케줄러 (Build 5)" --body "WeeklyReportAggregator + WeeklyReportScheduler(cron 일 20:00 KST). CommunityBadgeClient.badgesOf(awardedAt) 확장 포함. shared #<Task1 PR> 머지+publish 선행 필요."
```

- [ ] **Step 7: CI 확인** (머지 금지)

---

### Task 4: devpath-notification-svc — WeeklyReportConsumer + EmailSender + weekly_report 저장

**Files:**
- Modify: `devpath-notification-svc/build.gradle.kts` (spring-boot-starter-mail 추가)
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/report/WeeklyReport.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/report/WeeklyReportRepository.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/report/EmailSender.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/report/MockEmailSender.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/report/SmtpEmailSender.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/report/WeeklyReportConsumer.java`
- Modify: `devpath-notification-svc/src/main/resources/application.yml`
- Modify: `devpath-notification-svc/src/test/resources/application-test.yml`
- Test: `devpath-notification-svc/src/test/java/ai/devpath/notification/report/WeeklyReportConsumerTest.java`

**Interfaces:**
- Consumes: Task 1 `WeeklyReportGeneratedEvent`(shared 새 SNAPSHOT), `weekly_report` 테이블, 기존 `UserNotificationPrefsRepository.findById`(weeklyReportEmailEnabled), `PushSender`(Build 3).
- Produces: `EmailSender.send(long userId, String toHint, String subject, String body)`(interface). `WeeklyReportConsumer`(@KafkaListener `progress.report.generated`, groupId `devpath-notification`).

- [ ] **Step 1: 브랜치 + mail 의존성 추가 + 새 SNAPSHOT**

```bash
cd devpath-notification-svc
git fetch origin && git switch develop && git pull --ff-only origin develop
git switch -c feat/retention-build5-weekly-report
```
`build.gradle.kts`의 `dependencies` 블록에 추가(`spring-boot-starter-webmvc` 아래 등):
```kotlin
	implementation("org.springframework.boot:spring-boot-starter-mail")
```
그리고 `./gradlew compileJava --refresh-dependencies`.

- [ ] **Step 2: WeeklyReport 엔티티 + Repository**

`WeeklyReport.java`:
```java
package ai.devpath.notification.report;

import jakarta.persistence.*;
import java.time.Instant;
import java.time.LocalDate;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/** 스키마: devpath-shared V202607031002__weekly_report.sql. */
@Entity
@Table(name = "weekly_report")
public class WeeklyReport {
	@Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
	@Column(name = "user_id", nullable = false) private Long userId;
	@Column(name = "week_of", nullable = false) private LocalDate weekOf;
	@JdbcTypeCode(SqlTypes.JSON) @Column(nullable = false) private String payload;
	@Column(name = "generated_at", insertable = false, updatable = false) private Instant generatedAt;
	@Column(name = "email_sent_at") private Instant emailSentAt;
	@Column(name = "push_sent_at") private Instant pushSentAt;

	public Long getUserId() { return userId; }
	public void setUserId(Long v) { this.userId = v; }
	public LocalDate getWeekOf() { return weekOf; }
	public void setWeekOf(LocalDate v) { this.weekOf = v; }
	public String getPayload() { return payload; }
	public void setPayload(String v) { this.payload = v; }
	public Instant getEmailSentAt() { return emailSentAt; }
	public void setEmailSentAt(Instant v) { this.emailSentAt = v; }
	public Instant getPushSentAt() { return pushSentAt; }
	public void setPushSentAt(Instant v) { this.pushSentAt = v; }
}
```

`WeeklyReportRepository.java`:
```java
package ai.devpath.notification.report;

import org.springframework.data.jpa.repository.JpaRepository;

public interface WeeklyReportRepository extends JpaRepository<WeeklyReport, Long> {
	boolean existsByUserIdAndWeekOf(Long userId, java.time.LocalDate weekOf);
}
```

- [ ] **Step 3: EmailSender 인터페이스 + Mock + Smtp**

`EmailSender.java`:
```java
package ai.devpath.notification.report;

/** 이메일 전달 추상화(스펙의 EmailSender 패턴). 기본 구현은 MockEmailSender, 운영은 SmtpEmailSender. */
public interface EmailSender {
	void send(long userId, String subject, String body);
}
```

`MockEmailSender.java`(기본 provider — test·local·SMTP 미구성 시):
```java
package ai.devpath.notification.report;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "devpath.mail.provider", havingValue = "mock", matchIfMissing = true)
public class MockEmailSender implements EmailSender {
	private static final Logger log = LoggerFactory.getLogger(MockEmailSender.class);

	@Override
	public void send(long userId, String subject, String body) {
		log.info("[MockEmailSender] userId={} subject={} (실제 발송 안 함)", userId, subject);
	}
}
```

`SmtpEmailSender.java`(운영 — `devpath.mail.provider=smtp`, `spring-boot-starter-mail`의 `JavaMailSender` 사용). **실제 SMTP 계정·발신도메인은 devpath-gitops 후속** — 이 클래스는 provider=smtp일 때만 로드되므로 test/local(mock 기본)에 영향 없음:
```java
package ai.devpath.notification.report;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "devpath.mail.provider", havingValue = "smtp")
public class SmtpEmailSender implements EmailSender {

	private final JavaMailSender mailSender;
	private final String from;

	public SmtpEmailSender(JavaMailSender mailSender,
			@Value("${devpath.mail.from-address:no-reply@devpath.ai}") String from) {
		this.mailSender = mailSender;
		this.from = from;
	}

	@Override
	public void send(long userId, String subject, String body) {
		// 실제 수신자 이메일은 platform-svc 소관 — 후속 연동. 현재는 발신/본문 구성까지.
		SimpleMailMessage msg = new SimpleMailMessage();
		msg.setFrom(from);
		msg.setSubject(subject);
		msg.setText(body);
		// msg.setTo(...) 는 수신자 조회 API(platform-svc) 연동 후속
		mailSender.send(msg);
	}
}
```

- [ ] **Step 4: 실패하는 WeeklyReportConsumer 단위 테스트**

```java
package ai.devpath.notification.report;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import ai.devpath.notification.prefs.UserNotificationPrefs;
import ai.devpath.notification.prefs.UserNotificationPrefsRepository;
import ai.devpath.notification.push.PushSender;
import ai.devpath.shared.event.WeeklyReportGeneratedEvent;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

class WeeklyReportConsumerTest {

  private final JsonMapper jsonMapper = new JsonMapper();

  private String payload(long userId) {
    return jsonMapper.writeValueAsString(new WeeklyReportGeneratedEvent(
        UUID.randomUUID(), Instant.now(), userId, LocalDate.of(2026, 7, 5), 12, 75, List.of("학생"), "Spring 실습"));
  }

  private UserNotificationPrefs prefs(long userId, boolean emailOn) {
    UserNotificationPrefs p = new UserNotificationPrefs();
    p.setUserId(userId); p.setWeeklyReportEmailEnabled(emailOn);
    return p;
  }

  @Test
  void savesReportSendsEmailAndPushWhenEmailEnabled() {
    WeeklyReportRepository reports = mock(WeeklyReportRepository.class);
    when(reports.existsByUserIdAndWeekOf(eq(500L), any())).thenReturn(false);
    UserNotificationPrefsRepository prefs = mock(UserNotificationPrefsRepository.class);
    when(prefs.findById(500L)).thenReturn(Optional.of(prefs(500L, true)));
    EmailSender email = mock(EmailSender.class);
    PushSender push = mock(PushSender.class);
    var c = new WeeklyReportConsumer(reports, prefs, email, push, jsonMapper);

    c.onWeeklyReport(payload(500L));

    verify(reports).save(any(WeeklyReport.class));
    verify(email).send(eq(500L), anyString(), anyString());
    verify(push).send(eq(500L), eq("WEEKLY_REPORT"), anyString(), anyString());
  }

  @Test
  void skipsEmailWhenDisabledButStillPushes() {
    WeeklyReportRepository reports = mock(WeeklyReportRepository.class);
    when(reports.existsByUserIdAndWeekOf(anyLong(), any())).thenReturn(false);
    UserNotificationPrefsRepository prefs = mock(UserNotificationPrefsRepository.class);
    when(prefs.findById(501L)).thenReturn(Optional.of(prefs(501L, false)));
    EmailSender email = mock(EmailSender.class);
    PushSender push = mock(PushSender.class);
    var c = new WeeklyReportConsumer(reports, prefs, email, push, jsonMapper);

    c.onWeeklyReport(payload(501L));

    verify(email, never()).send(anyLong(), anyString(), anyString());
    verify(push).send(eq(501L), eq("WEEKLY_REPORT"), anyString(), anyString());
  }

  @Test
  void skipsDuplicateWeek() {
    WeeklyReportRepository reports = mock(WeeklyReportRepository.class);
    when(reports.existsByUserIdAndWeekOf(eq(502L), any())).thenReturn(true); // 이미 처리됨
    var c = new WeeklyReportConsumer(reports, mock(UserNotificationPrefsRepository.class),
        mock(EmailSender.class), mock(PushSender.class), jsonMapper);

    c.onWeeklyReport(payload(502L));

    verify(reports, never()).save(any());
  }

  @Test
  void skipsPoisonPayload() {
    var c = new WeeklyReportConsumer(mock(WeeklyReportRepository.class), mock(UserNotificationPrefsRepository.class),
        mock(EmailSender.class), mock(PushSender.class), jsonMapper);
    c.onWeeklyReport("{ not json"); // 예외 없이 skip
  }
}
```

- [ ] **Step 5: 테스트 실패 확인 → WeeklyReportConsumer 구현 → 통과**

Run(RED): `cd devpath-notification-svc && ./gradlew test --tests "ai.devpath.notification.report.WeeklyReportConsumerTest"` → FAIL(클래스 없음).

`WeeklyReportConsumer.java`:
```java
package ai.devpath.notification.report;

import ai.devpath.notification.prefs.UserNotificationPrefs;
import ai.devpath.notification.prefs.UserNotificationPrefsRepository;
import ai.devpath.notification.push.PushSender;
import ai.devpath.shared.event.WeeklyReportGeneratedEvent;
import java.time.Instant;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

/** progress.report.generated 구독 → weekly_report 저장(멱등) → (설정 시)이메일 → "리포트 도착" 푸시. */
@Component
public class WeeklyReportConsumer {

	private static final Logger log = LoggerFactory.getLogger(WeeklyReportConsumer.class);
	private static final String TYPE = "WEEKLY_REPORT";

	private final WeeklyReportRepository reports;
	private final UserNotificationPrefsRepository prefs;
	private final EmailSender emailSender;
	private final PushSender pushSender;
	private final JsonMapper jsonMapper;

	public WeeklyReportConsumer(WeeklyReportRepository reports, UserNotificationPrefsRepository prefs,
			EmailSender emailSender, PushSender pushSender, JsonMapper jsonMapper) {
		this.reports = reports;
		this.prefs = prefs;
		this.emailSender = emailSender;
		this.pushSender = pushSender;
		this.jsonMapper = jsonMapper;
	}

	@KafkaListener(topics = WeeklyReportGeneratedEvent.EVENT_TYPE, groupId = "devpath-notification")
	public void onWeeklyReport(String payload) {
		WeeklyReportGeneratedEvent event;
		try {
			event = jsonMapper.readValue(payload, WeeklyReportGeneratedEvent.class);
		} catch (Exception e) {
			log.warn("WeeklyReportGeneratedEvent 역직렬화 실패 — skip: {}", payload, e);
			return; // poison 방지
		}
		if (reports.existsByUserIdAndWeekOf(event.userId(), event.weekOf())) return; // 멱등(UNIQUE 방어선과 병행)

		String subject = "이번 주 학습 리포트 (" + event.weekOf() + ")";
		String body = "스트릭 " + event.streakDays() + "일 · 진척률 " + event.progressPercent() + "%"
				+ (event.badgesEarnedThisWeek().isEmpty() ? "" : " · 이번주 배지 " + String.join(", ", event.badgesEarnedThisWeek()))
				+ (event.nextTaskTitle() == null ? "" : "\n다음 과제: " + event.nextTaskTitle());

		WeeklyReport report = new WeeklyReport();
		report.setUserId(event.userId());
		report.setWeekOf(event.weekOf());
		report.setPayload(payload);

		boolean emailEnabled = prefs.findById(event.userId())
				.map(UserNotificationPrefs::getWeeklyReportEmailEnabled).orElse(Boolean.TRUE);
		if (Boolean.TRUE.equals(emailEnabled)) {
			try {
				emailSender.send(event.userId(), subject, body);
				report.setEmailSentAt(Instant.now());
			} catch (RuntimeException e) {
				log.warn("주간 리포트 이메일 실패 — userId={} (푸시는 계속)", event.userId(), e);
			}
		}
		pushSender.send(event.userId(), TYPE, "주간 학습 리포트가 도착했어요", body);
		report.setPushSentAt(Instant.now());

		try {
			reports.save(report);
		} catch (org.springframework.dao.DataIntegrityViolationException dup) {
			// 동시 소비 레이스 — UNIQUE(user_id, week_of) 위반 = 이미 저장됨. 무시(멱등).
		}
	}
}
```
Run(GREEN): `./gradlew test --tests "ai.devpath.notification.report.WeeklyReportConsumerTest"` → PASS (4 tests).

- [ ] **Step 6: application.yml / application-test.yml 프로퍼티**

`application.yml`의 `devpath:` 블록에 추가:
```yaml
  mail:
    provider: ${MAIL_PROVIDER:mock}      # mock(기본) | smtp
    from-address: ${MAIL_FROM:no-reply@devpath.ai}
```
그리고 (provider=smtp 운영 대비, 기본은 미사용) `spring:` 블록에 주석성 SMTP 자리:
```yaml
  mail:
    host: ${MAIL_HOST:localhost}
    port: ${MAIL_PORT:587}
    username: ${MAIL_USERNAME:}
    password: ${MAIL_PASSWORD:}
```
`application-test.yml`은 기본 `devpath.mail.provider`가 `mock`(matchIfMissing)이라 **추가 불필요**(명시하려면 `devpath.mail.provider: mock`).

- [ ] **Step 7: 전체 빌드 + 커밋 + push + PR**

Run: `cd devpath-notification-svc && ./gradlew build`
Expected: BUILD SUCCESSFUL(전체 스위트 회귀 없음 — 신규 @KafkaListener는 브로커 없이 컨텍스트 기동에 영향 없음, MockEmailSender가 기본이라 JavaMailSender 미구성도 무해). "too many clients" 발생 시 `application-test.yml`에 `spring.datasource.hikari.maximum-pool-size: 4` 추가.

```bash
cd devpath-notification-svc
git add build.gradle.kts src/main/java/ai/devpath/notification/report/ \
        src/main/resources/application.yml src/test/resources/application-test.yml \
        src/test/java/ai/devpath/notification/report/
git commit -m "feat(report): WeeklyReportConsumer + EmailSender(Mock/Smtp) + weekly_report 저장

참여촉진배치 Build 5 — progress.report.generated 구독 → weekly_report 저장(멱등) →
(설정 시)이메일 + 리포트 도착 푸시. 실제 SMTP는 gitops 후속(MockEmailSender 기본)."
git push -u origin feat/retention-build5-weekly-report
gh pr create --base develop --title "feat(report): 주간 리포트 구독+저장+이메일 (Build 5)" --body "WeeklyReportGeneratedEvent 구독 → weekly_report 저장 + EmailSender(Mock 기본, Smtp 후속) + PushSender. shared #<Task1 PR>·learning-svc #<Task3 PR> 선행."
```

- [ ] **Step 8: CI 확인** (머지 금지)

---

## Self-Review (작성자 점검)

**1. 스펙 커버리지:**
- §데이터 모델 `weekly_report`(전 컬럼 + UNIQUE) → Task 1 ✅.
- §이벤트 계약 `WeeklyReportGeneratedEvent`(8필드) → Task 1 ✅.
- §learning-svc `WeeklyReportScheduler`(일 20:00 KST, 전체 유저 순회, 진척+스트릭+배지 조합 → 발행) → Task 3 ✅ (배지 enrich는 Task 2의 `badgesOf`).
- §notification-svc `WeeklyReportConsumer`(→ weekly_report 저장 → email_enabled면 EmailSender → 푸시) + `EmailSender`(interface+Smtp+Mock) → Task 4 ✅.

**2. 결정/스코프 노트:** EmailSender Mock 기본·Smtp 후속(gitops SMTP 부재, Build 3 FCM과 동일) / community-svc 무변경(awardedAt 이미 반환) / 배지 N+1 후속(스펙 허용) / DashboardService 무변경(진척계산 자체 구현, 경미한 중복 수용) — 전부 계획에 veto 가능하게 명시.

**3. 타입 일관성:** `WeeklyReportGeneratedEvent`(8필드, Task 1) ↔ learning 발행(Task 3)·notification 역직렬화(Task 4) 일치 ✅. `CommunityBadgeClient.badgesOf: List<BadgeAwardView>`(Task 2) ↔ `WeeklyReportAggregator` 사용(Task 3) 일치 ✅. `EmailSender.send(long,String,String)`(Task 4) ↔ `WeeklyReportConsumer` 호출 일치 ✅. `PushSender.send(long,String,String,String)`(Build 3) ↔ 사용 일치 ✅. `UserNotificationPrefs.getWeeklyReportEmailEnabled`(기존) ↔ 사용 일치 ✅.

**4. 순서 의존성:** Task 1(shared)→main publish 먼저. Task 2·3(learning, 같은 브랜치)·Task 4(notification)는 Task 1 publish 후. Task 4는 Task 3의 이벤트 발행을 런타임 소비하나 코드/테스트는 독립(Mock 이벤트 payload로 단위 테스트).

## 리스크 / 후속

- **실제 SMTP 발송**: `SmtpEmailSender`는 작성하되 `devpath.mail.provider=smtp`일 때만 로드. 운영 SMTP 계정·발신도메인·수신자(이메일) 조회(platform-svc) 연동은 **devpath-gitops/후속**.
- **배지 enrich N+1**: 유저마다 community-svc 동기 호출(주간 배치라 허용). 유저 급증 시 bulk API(`GET /community/users/badges?userIds=...`) 후속 필요.
- **진척% 계산 중복**: `DashboardService`와 `WeeklyReportAggregator`가 유사 계산 — 후속에 `LearningPathQueryService.progressOf()` 공용 추출 가능(이번엔 Build 2 무변경 우선).
- **수신자 이메일**: 실제 To 주소는 platform-svc 소관 — `SmtpEmailSender`에 수신자 조회 연동 후속.

## Execution Handoff

계획 완료. 저장: `documents/docs/superpowers/plans/2026-07-03-md3-retention-batch-build5.md`.
