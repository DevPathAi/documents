# 참여촉진배치 Build 2 (스트릭 계산 + 대시보드 실연동) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** learning-svc에 TZ 인식 스트릭 계산 배치를 추가하고, 대시보드의 `streakDays`/`badges` 하드코딩을 실연동으로 교체하며, 스트릭 30일 달성 시 community-svc가 COMMUNITY 배지를 자동 수여하게 한다.

**Architecture:** learning-svc가 신규 `progress` 모듈로 활동 신호(주간 과제 완료 + Sandbox 제출)를 집계해 매시간 TZ 윈도우 스캔으로 스트릭을 갱신하고, 마일스톤(7/14/30/60/100일) 도달 시 `StreakReachedEvent`를 Kafka로 발행한다. community-svc는 이를 구독해 `days==30`일 때 기존 `BadgeService`로 COMMUNITY 배지를 수여한다. TZ 개인화를 위해 notification-svc에 최소한의 timezone 저장/조회만 신규로 만든다(Build 3 범위인 사용자 대면 prefs API·리마인더는 손대지 않음). `path_weekly_tasks.completed_at`은 콘텐츠 연결 태스크는 이미 자동 완료 처리되므로, `content_id`가 없는 태스크만을 위한 명시적 완료 API를 추가한다.

**Tech Stack:** Java 21 · Spring Boot 4.0.7 · Gradle(Kotlin DSL) · Spring Data JPA · Kafka(`spring-kafka`) · devpath-shared(Flyway 중앙 마이그레이션, GitHub Packages).

**스펙:** [2026-07-01-md3-retention-batch-design.md](../specs/2026-07-01-md3-retention-batch-design.md) (Build 2 절 + 2026-07-02 착수 정정)

## Global Constraints

- 모든 신규 코드는 `flyway.enabled: false`를 유지한다 — 스키마는 `devpath-shared`가 중앙 소유, 각 서비스는 `ddl-auto: validate`만 한다.
- `devpath-shared` 변경(이벤트·마이그레이션)은 **가장 먼저** `main`에 병합해 GitHub Packages에 publish되어야 다른 서비스가 소비할 수 있다. `devpath-shared`에는 `develop` 브랜치가 없다 — `feat/*` 브랜치를 `main`에 직접 PR한다.
- `devpath-shared`를 새로 받는 서비스는 `./gradlew compileJava --refresh-dependencies`로 새 SNAPSHOT을 받는다(로컬 jar 캐시가 낡은 SNAPSHOT을 들고 있을 수 있음 — mtime이 아니라 **jar 내용 grep**으로 새 클래스가 들어왔는지 확인).
- 신규 작업은 각 레포 `develop`에서 새 브랜치(`feat/*`)를 분기한다. 공유 브랜치에서 직접 작업하지 않는다.
- Kafka payload는 항상 `String`(JSON), 컨슈머가 `JsonMapper#readValue`로 수동 역직렬화하고 실패 시 로그 후 스킵한다(poison-pill 무한재시도 방지) — 기존 `CommunitySeedConsumer`/`WelcomeNotificationConsumer` 패턴을 그대로 따른다.
- outbox 발행은 `OutboxEntry`(aggregateType/aggregateId/eventType/payload/createdAt) 저장까지만 하고, 실제 Kafka 전송은 기존 `OutboxRelay`(`@Scheduled(fixedDelay=2000)`)가 담당한다 — 신규 발행 코드에서 KafkaTemplate을 직접 쓰지 않는다.
- 테스트는 실 Postgres(`localhost:5432/devpath`, `devpath`/`localdev`) + `@EmbeddedKafka`를 쓴다. Testcontainers는 이 두 레포(learning-svc, community-svc, notification-svc) 어디에도 없다 — 새로 도입하지 않는다.
- 서비스 간 동기 호출은 게이트웨이를 경유하지 않고 `RestClient` 직접 호출을 쓴다(`devpath.<svc>.base-url` 프로퍼티 패턴, 기존 `RestAiPathClient` 참고).

---

### Task 1: devpath-shared — StreakReachedEvent + 마이그레이션 2건

**Files:**
- Create: `devpath-shared/src/main/java/ai/devpath/shared/event/StreakReachedEvent.java`
- Create: `devpath-shared/src/main/resources/db/migration/V202607021001__user_streak.sql`
- Create: `devpath-shared/src/main/resources/db/migration/V202607021002__user_notification_prefs.sql`
- Test: `devpath-shared/src/test/java/ai/devpath/shared/event/StreakReachedEventTest.java`

**Interfaces:**
- Consumes: 없음(devpath-shared는 최하위 레이어).
- Produces: `StreakReachedEvent` record(필드: `eventId: UUID`, `occurredAt: Instant`, `userId: long`, `days: int`, 정적 상수 `EVENT_TYPE = "progress.streak.reached"`) — Task 4(발행)와 Task 6(구독)이 이 정확한 필드명·타입을 그대로 참조한다. `user_streak` 테이블(컬럼: `user_id BIGINT PK`, `current_days INT`, `longest_days INT`, `last_active_date DATE`, `updated_at TIMESTAMPTZ`) — Task 4가 그대로 매핑한다. `user_notification_prefs` 테이블(컬럼: `user_id BIGINT PK`, `timezone VARCHAR(64)`, `preferred_time_slot VARCHAR(5)`, `reminder_enabled BOOLEAN`, `weekly_report_email_enabled BOOLEAN`, `updated_at TIMESTAMPTZ`) — Task 2가 그대로 매핑한다.

- [ ] **Step 1: StreakReachedEvent 실패 테스트 작성**

```java
package ai.devpath.shared.event;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class StreakReachedEventTest {

  @Test
  void eventTypeMatchesConstant() {
    StreakReachedEvent event = new StreakReachedEvent(UUID.randomUUID(), Instant.now(), 42L, 30);

    assertEquals("progress.streak.reached", event.eventType());
    assertEquals("progress.streak.reached", StreakReachedEvent.EVENT_TYPE);
    assertEquals(42L, event.userId());
    assertEquals(30, event.days());
  }
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.event.StreakReachedEventTest"`
Expected: FAIL — `StreakReachedEvent` 클래스가 없어 컴파일 실패.

- [ ] **Step 3: StreakReachedEvent 구현**

```java
package ai.devpath.shared.event;

import java.time.Instant;
import java.util.UUID;

/**
 * 스트릭 마일스톤(7/14/30/60/100일) 도달 이벤트.
 * learning-svc가 Transactional Outbox로 발행한다. 소비자: community-svc(days==30 → COMMUNITY 배지).
 */
public record StreakReachedEvent(
		UUID eventId,
		Instant occurredAt,
		long userId,
		int days
) implements DomainEvent {

	public static final String EVENT_TYPE = "progress.streak.reached";

	@Override
	public String eventType() {
		return EVENT_TYPE;
	}
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.event.StreakReachedEventTest"`
Expected: PASS

- [ ] **Step 5: user_streak 마이그레이션 작성**

```sql
-- 학습 스트릭(연속 활동 일수). owner: devpath-learning-svc.
CREATE TABLE user_streak (
  user_id          BIGINT PRIMARY KEY,          -- platform users 논리 참조(FK 없음)
  current_days     INT NOT NULL DEFAULT 0,
  longest_days     INT NOT NULL DEFAULT 0,
  last_active_date DATE,
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

파일: `devpath-shared/src/main/resources/db/migration/V202607021001__user_streak.sql`

- [ ] **Step 6: user_notification_prefs 마이그레이션 작성**

```sql
-- 알림 수신 설정(timezone은 Build 2에서 사용, 나머지 컬럼은 Build 3에서 사용). owner: devpath-notification-svc.
CREATE TABLE user_notification_prefs (
  user_id                     BIGINT PRIMARY KEY,
  timezone                    VARCHAR(64) NOT NULL DEFAULT 'Asia/Seoul',
  preferred_time_slot         VARCHAR(5)  NOT NULL DEFAULT '19:00',
  reminder_enabled            BOOLEAN NOT NULL DEFAULT true,
  weekly_report_email_enabled BOOLEAN NOT NULL DEFAULT true,
  updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

파일: `devpath-shared/src/main/resources/db/migration/V202607021002__user_notification_prefs.sql`

- [ ] **Step 7: 로컬 Flyway로 마이그레이션 검증**

Run: `cd devpath-shared && ./gradlew flywayMigrate`
Expected: `Successfully applied 2 migrations` (또는 이미 최신이면 `Schema is up to date`가 아니라 신규 2건이 적용됐다는 로그) — 실패 시 `./gradlew flywayInfo`로 현재 스키마 버전 확인 후 원인 규명.

- [ ] **Step 8: 전체 테스트 + 커밋**

Run: `cd devpath-shared && ./gradlew build`
Expected: BUILD SUCCESSFUL

```bash
cd devpath-shared
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feat/retention-build2-streak-event
git add src/main/java/ai/devpath/shared/event/StreakReachedEvent.java \
        src/main/resources/db/migration/V202607021001__user_streak.sql \
        src/main/resources/db/migration/V202607021002__user_notification_prefs.sql \
        src/test/java/ai/devpath/shared/event/StreakReachedEventTest.java
git commit -m "feat(shared): StreakReachedEvent + user_streak/user_notification_prefs 마이그레이션

참여촉진배치 Build 2 — 스트릭 계산·TZ 저장 스키마 추가."
git push -u origin feat/retention-build2-streak-event
gh pr create --base main --title "feat(shared): 참여촉진배치 Build 2 스키마+이벤트" --body "user_streak, user_notification_prefs 마이그레이션 + StreakReachedEvent 추가. 다른 서비스(learning/notification/community-svc)가 이 PR 머지+publish 이후에 의존 가능."
```

- [ ] **Step 9: CI 확인 후 머지, publish 확인**

Run: `gh pr checks <PR번호> -R DevPathAi/devpath-shared` — 통과 확인 후:
```bash
gh pr merge <PR번호> -R DevPathAi/devpath-shared --merge
gh pr view <PR번호> -R DevPathAi/devpath-shared --json state,mergedAt
```
Expected: `state: MERGED`. main push 시 GitHub Actions가 GitHub Packages에 새 SNAPSHOT을 publish한다 — `gh run list -R DevPathAi/devpath-shared --branch main --limit 1`로 publish 워크플로 성공 확인.

---

### Task 2: devpath-notification-svc — user_notification_prefs 저장/내부 조회 API

**Files:**
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/prefs/UserNotificationPrefs.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/prefs/UserNotificationPrefsRepository.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/prefs/UserTimezoneView.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/prefs/InternalPrefsController.java`
- Modify: `devpath-notification-svc/src/main/java/ai/devpath/notification/config/SecurityConfig.java`
- Test: `devpath-notification-svc/src/test/java/ai/devpath/notification/prefs/InternalPrefsControllerIT.java`

**Interfaces:**
- Consumes: `user_notification_prefs` 테이블(Task 1). devpath-shared 새 SNAPSHOT을 받아야 한다(`build.gradle.kts`의 `implementation("ai.devpath:devpath-shared:0.0.1-SNAPSHOT")`는 이미 있으므로 버전 변경 불필요, `--refresh-dependencies`만 필요).
- Produces: `GET /notifications/internal/prefs/timezones?userIds=1,2,3` → `List<UserTimezoneView>`(레코드: `userId: long`, `timezone: String`) — Task 4의 `StreakRolloverScheduler`가 이 정확한 경로·응답 타입을 그대로 호출한다.

- [ ] **Step 1: 브랜치 준비 (devpath-shared 새 SNAPSHOT 수신)**

```bash
cd devpath-notification-svc
git fetch origin
git switch develop
git pull --ff-only origin develop
git switch -c feat/retention-build2-prefs
./gradlew compileJava --refresh-dependencies
```
Expected: BUILD SUCCESSFUL, 새 `StreakReachedEvent`가 classpath에 없어도(이 Task는 이벤트를 쓰지 않음) 빌드는 통과해야 한다.

- [ ] **Step 2: 실패하는 통합 테스트 작성**

```java
package ai.devpath.notification.prefs;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class InternalPrefsControllerIT {

  @Autowired MockMvc mvc;
  @Autowired UserNotificationPrefsRepository prefs;

  @Test
  void returnsDefaultTimezoneWhenNoRowExists() throws Exception {
    mvc.perform(get("/notifications/internal/prefs/timezones").param("userIds", "999001"))
        .andExpect(status().isOk())
        .andExpect(content().json("[{\"userId\":999001,\"timezone\":\"Asia/Seoul\"}]"));
  }

  @Test
  void returnsStoredTimezoneWhenRowExists() throws Exception {
    UserNotificationPrefs row = new UserNotificationPrefs();
    row.setUserId(999002L);
    row.setTimezone("America/New_York");
    prefs.save(row);

    mvc.perform(get("/notifications/internal/prefs/timezones").param("userIds", "999002"))
        .andExpect(status().isOk())
        .andExpect(content().json("[{\"userId\":999002,\"timezone\":\"America/New_York\"}]"));
  }
}
```

（테스트 클래스 실행 전 이 레포에 `spring-boot-starter-test`/`MockMvc` 의존성이 있는지 `build.gradle.kts`를 확인하고 없으면 `testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")`를 추가하라 — 이 레포는 이번 조사에서 MockMvc 사용 이력이 없었으므로 신규 추가가 필요할 수 있다.）

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `cd devpath-notification-svc && ./gradlew test --tests "ai.devpath.notification.prefs.InternalPrefsControllerIT"`
Expected: FAIL — `UserNotificationPrefs`/`UserNotificationPrefsRepository`/`InternalPrefsController` 클래스가 없어 컴파일 실패.

- [ ] **Step 4: UserNotificationPrefs 엔티티 구현**

```java
package ai.devpath.notification.prefs;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

/**
 * 알림 수신 설정. Build 2는 timezone만 사용한다(스트릭 롤오버 스케줄러용).
 * 스키마: devpath-shared {@code V202607021002__user_notification_prefs.sql}.
 */
@Entity
@Table(name = "user_notification_prefs")
public class UserNotificationPrefs {

	@Id
	@Column(name = "user_id")
	private Long userId;

	@Column(nullable = false)
	private String timezone = "Asia/Seoul";

	@Column(name = "preferred_time_slot", nullable = false)
	private String preferredTimeSlot = "19:00";

	@Column(name = "reminder_enabled", nullable = false)
	private Boolean reminderEnabled = true;

	@Column(name = "weekly_report_email_enabled", nullable = false)
	private Boolean weeklyReportEmailEnabled = true;

	@Column(name = "updated_at")
	private Instant updatedAt;

	public Long getUserId() { return userId; }
	public void setUserId(Long v) { this.userId = v; }
	public String getTimezone() { return timezone; }
	public void setTimezone(String v) { this.timezone = v; }
	public String getPreferredTimeSlot() { return preferredTimeSlot; }
	public Boolean getReminderEnabled() { return reminderEnabled; }
	public Boolean getWeeklyReportEmailEnabled() { return weeklyReportEmailEnabled; }
	public Instant getUpdatedAt() { return updatedAt; }
	public void setUpdatedAt(Instant v) { this.updatedAt = v; }
}
```

- [ ] **Step 5: Repository 구현**

```java
package ai.devpath.notification.prefs;

import org.springframework.data.jpa.repository.JpaRepository;

public interface UserNotificationPrefsRepository extends JpaRepository<UserNotificationPrefs, Long> {
}
```

- [ ] **Step 6: UserTimezoneView 구현**

```java
package ai.devpath.notification.prefs;

public record UserTimezoneView(long userId, String timezone) {
}
```

- [ ] **Step 7: InternalPrefsController 구현**

기본값(`Asia/Seoul`)은 행이 없는 userId에도 반환해야 한다(스펙: `timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Seoul'` — 행이 아예 없으면 DB 기본값이 적용되지 않으므로 애플리케이션 레벨에서 기본값을 채운다).

```java
package ai.devpath.notification.prefs;

import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** 서비스 간 내부 조회(게이트웨이 미경유). learning-svc의 스트릭 롤오버 스케줄러가 timezone bulk 조회에 쓴다. */
@RestController
@RequestMapping("/notifications/internal/prefs")
public class InternalPrefsController {

	private static final String DEFAULT_TIMEZONE = "Asia/Seoul";

	private final UserNotificationPrefsRepository prefs;

	public InternalPrefsController(UserNotificationPrefsRepository prefs) {
		this.prefs = prefs;
	}

	@GetMapping("/timezones")
	public List<UserTimezoneView> timezones(@RequestParam String userIds) {
		List<Long> ids = Arrays.stream(userIds.split(","))
				.map(String::trim)
				.filter(s -> !s.isEmpty())
				.map(Long::parseLong)
				.toList();
		Map<Long, String> found = prefs.findAllById(ids).stream()
				.collect(Collectors.toMap(UserNotificationPrefs::getUserId, UserNotificationPrefs::getTimezone));
		return ids.stream()
				.map(id -> new UserTimezoneView(id, found.getOrDefault(id, DEFAULT_TIMEZONE)))
				.toList();
	}
}
```

- [ ] **Step 8: SecurityConfig에 internal 경로 permitAll 추가**

`devpath-notification-svc/src/main/java/ai/devpath/notification/config/SecurityConfig.java`의 `securityFilterChain` 메서드에서:

old_string:
```java
        .authorizeHttpRequests(authorize -> authorize
            .requestMatchers("/actuator/health").permitAll()
            .anyRequest().authenticated())
```

new_string:
```java
        .authorizeHttpRequests(authorize -> authorize
            .requestMatchers("/actuator/health").permitAll()
            .requestMatchers("/notifications/internal/**").permitAll()
            .anyRequest().authenticated())
```

- [ ] **Step 9: 테스트 통과 확인**

Run: `cd devpath-notification-svc && ./gradlew test --tests "ai.devpath.notification.prefs.InternalPrefsControllerIT"`
Expected: PASS (2 tests)

- [ ] **Step 10: 전체 빌드 + 커밋 + PR**

Run: `cd devpath-notification-svc && ./gradlew build`
Expected: BUILD SUCCESSFUL

```bash
cd devpath-notification-svc
git add src/main/java/ai/devpath/notification/prefs/ \
        src/main/java/ai/devpath/notification/config/SecurityConfig.java \
        src/test/java/ai/devpath/notification/prefs/ \
        build.gradle.kts
git commit -m "feat(prefs): user_notification_prefs 저장 + timezone 내부 bulk 조회 API

참여촉진배치 Build 2 선당김분 — learning-svc 스트릭 롤오버 스케줄러가 사용.
사용자 대면 prefs API·리마인더 스케줄러는 Build 3에서 구현."
git push -u origin feat/retention-build2-prefs
gh pr create --base develop --title "feat(prefs): timezone 저장/내부 조회 API (Build 2 선당김)" --body "참여촉진배치 Build 2 스펙의 순서 의존성 정정에 따라 notification-svc의 timezone 저장/bulk조회만 선구현. 근거: documents/docs/superpowers/specs/2026-07-01-md3-retention-batch-design.md"
```

- [ ] **Step 11: CI 확인 후 머지**

Run: `gh pr checks <PR번호> -R DevPathAi/devpath-notification-svc` → 통과 확인 후 `gh pr merge <PR번호> -R DevPathAi/devpath-notification-svc --merge` → `gh pr view <PR번호> -R DevPathAi/devpath-notification-svc --json state,mergedAt`로 MERGED 직접 재확인.

---

### Task 3: devpath-learning-svc — PathWeeklyTask 명시적 완료 API

**배경**: `content_id`가 있는 태스크는 `ContentProgressRepository.completeActivePathTasks()`로 이미 자동 완료 처리된다(콘텐츠 진척 100% 시). `content_id`가 없는 태스크(AI 경로 생성 시 벡터 매칭이 안 된 경우)는 완료 처리 경로가 전혀 없다 — 이 Task가 그 공백만 메운다.

**Files:**
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/path/PathWeeklyTaskRepository.java`
- Modify: `devpath-learning-svc/src/main/java/ai/devpath/learning/path/LearningPathController.java`
- Test: `devpath-learning-svc/src/test/java/ai/devpath/learning/path/PathWeeklyTaskRepositoryTest.java`
- Test: `devpath-learning-svc/src/test/java/ai/devpath/learning/path/LearningPathControllerCompleteTaskTest.java`

**Interfaces:**
- Consumes: 기존 `path_weekly_tasks`/`path_milestones`/`learning_paths` 테이블(변경 없음).
- Produces: `PathWeeklyTaskRepository.completeTaskIfOwned(long userId, long taskId): int`(영향받은 행 수, 0 또는 1) — 이 Task 안에서만 쓰이지만, Task 4의 `StreakRolloverService`가 활동 판정에 쓰는 `PathWeeklyTaskRepository.hasCompletedTaskOnDate(long userId, LocalDate date): boolean` 메서드도 이 Task에서 함께 만든다(같은 Repository 클래스, 스트릭 판정과 완료 API가 같은 테이블을 보는 자연스러운 응집). `POST /learning-paths/tasks/{taskId}/complete` — 202/204 응답, 소유자 아니거나 존재하지 않으면 404.

- [ ] **Step 1: 브랜치 준비**

```bash
cd devpath-learning-svc
git fetch origin
git switch develop
git pull --ff-only origin develop
git switch -c feat/retention-build2-task-complete
./gradlew compileJava --refresh-dependencies
```

- [ ] **Step 2: PathWeeklyTaskRepository 실패 테스트 작성**

```java
package ai.devpath.learning.path;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class PathWeeklyTaskRepositoryTest {

  @Autowired PathWeeklyTaskRepository tasks;
  @Autowired JdbcTemplate jdbc;

  private long newTaskWithoutContent(long userId) {
    Long pathId = jdbc.queryForObject("""
        INSERT INTO learning_paths(user_id, generated_at, track, total_weeks, status)
        VALUES (?, now(), 'BACKEND_SPRING', 12, 'ACTIVE') RETURNING id
        """, Long.class, userId);
    Long milestoneId = jdbc.queryForObject("""
        INSERT INTO path_milestones(path_id, week_num, title) VALUES (?, 1, 'w1') RETURNING id
        """, Long.class, pathId);
    return jdbc.queryForObject("""
        INSERT INTO path_weekly_tasks(milestone_id, order_num, task_type, title, required)
        VALUES (?, 1, 'PRACTICE', 'task without content', true) RETURNING id
        """, Long.class, milestoneId);
  }

  @Test
  void completeTaskIfOwnedSetsCompletedAtForOwner() {
    long userId = 888001L;
    long taskId = newTaskWithoutContent(userId);

    int updated = tasks.completeTaskIfOwned(userId, taskId);

    assertThat(updated).isEqualTo(1);
    Instant completedAt = jdbc.queryForObject(
        "select completed_at from path_weekly_tasks where id = ?", Instant.class, taskId);
    assertThat(completedAt).isNotNull();
  }

  @Test
  void completeTaskIfOwnedReturnsZeroForNonOwner() {
    long ownerUserId = 888002L;
    long otherUserId = 888003L;
    long taskId = newTaskWithoutContent(ownerUserId);

    int updated = tasks.completeTaskIfOwned(otherUserId, taskId);

    assertThat(updated).isEqualTo(0);
  }

  @Test
  void hasCompletedTaskOnDateTrueWhenCompletedThatDay() {
    long userId = 888004L;
    long taskId = newTaskWithoutContent(userId);
    tasks.completeTaskIfOwned(userId, taskId);
    LocalDate today = Instant.now().atZone(ZoneOffset.UTC).toLocalDate();

    assertThat(tasks.hasCompletedTaskOnDate(userId, today)).isTrue();
  }

  @Test
  void hasCompletedTaskOnDateFalseWhenNoActivity() {
    long userId = 888005L;
    LocalDate today = Instant.now().atZone(ZoneOffset.UTC).toLocalDate();

    assertThat(tasks.hasCompletedTaskOnDate(userId, today)).isFalse();
  }
}
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.path.PathWeeklyTaskRepositoryTest"`
Expected: FAIL — `PathWeeklyTaskRepository` 클래스가 없어 컴파일 실패.

- [ ] **Step 4: PathWeeklyTaskRepository 구현**

`ContentProgressRepository`(JDBC 직접 쿼리, `NamedParameterJdbcTemplate`)와 동일한 스타일을 따른다.

```java
package ai.devpath.learning.path;

import java.time.LocalDate;
import java.util.Map;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class PathWeeklyTaskRepository {
  private final NamedParameterJdbcTemplate jdbc;

  public PathWeeklyTaskRepository(NamedParameterJdbcTemplate jdbc) {
    this.jdbc = jdbc;
  }

  /** content_id가 없는 태스크의 명시적 완료 처리. 본인 소유(ACTIVE 경로)의 태스크만 갱신, 이미 완료면 no-op. 반환값: 갱신된 행 수(0 또는 1). */
  public int completeTaskIfOwned(long userId, long taskId) {
    var sql = """
        UPDATE path_weekly_tasks t
        SET completed_at = COALESCE(t.completed_at, now())
        FROM path_milestones m
        JOIN learning_paths p ON p.id = m.path_id
        WHERE t.milestone_id = m.id
          AND t.id = :taskId
          AND p.user_id = :userId
          AND p.status = 'ACTIVE'
        """;
    return jdbc.update(sql, Map.of("taskId", taskId, "userId", userId));
  }

  /** 스트릭 활동 판정용: 해당 유저가 주어진 UTC 날짜에 완료한 주간 과제가 하나라도 있는지. */
  public boolean hasCompletedTaskOnDate(long userId, LocalDate date) {
    var sql = """
        SELECT EXISTS (
          SELECT 1 FROM path_weekly_tasks t
          JOIN path_milestones m ON t.milestone_id = m.id
          JOIN learning_paths p ON p.id = m.path_id
          WHERE p.user_id = :userId
            AND t.completed_at >= :dayStart
            AND t.completed_at < :dayEnd
        )
        """;
    return Boolean.TRUE.equals(jdbc.queryForObject(sql, Map.of(
        "userId", userId,
        "dayStart", date.atStartOfDay(java.time.ZoneOffset.UTC).toInstant(),
        "dayEnd", date.plusDays(1).atStartOfDay(java.time.ZoneOffset.UTC).toInstant())
        , Boolean.class));
  }
}
```

- [ ] **Step 5: PathWeeklyTaskRepositoryTest 통과 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.path.PathWeeklyTaskRepositoryTest"`
Expected: PASS (4 tests)

- [ ] **Step 6: 컨트롤러 실패 테스트 작성**

```java
package ai.devpath.learning.path;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class LearningPathControllerCompleteTaskTest {

  @Autowired MockMvc mvc;
  @Autowired JdbcTemplate jdbc;

  private long newTaskWithoutContent(long userId) {
    Long pathId = jdbc.queryForObject("""
        INSERT INTO learning_paths(user_id, generated_at, track, total_weeks, status)
        VALUES (?, now(), 'BACKEND_SPRING', 12, 'ACTIVE') RETURNING id
        """, Long.class, userId);
    Long milestoneId = jdbc.queryForObject("""
        INSERT INTO path_milestones(path_id, week_num, title) VALUES (?, 1, 'w1') RETURNING id
        """, Long.class, pathId);
    return jdbc.queryForObject("""
        INSERT INTO path_weekly_tasks(milestone_id, order_num, task_type, title, required)
        VALUES (?, 1, 'PRACTICE', 'task without content', true) RETURNING id
        """, Long.class, milestoneId);
  }

  @Test
  void completeTaskReturns204ForOwner() throws Exception {
    long userId = 888101L;
    long taskId = newTaskWithoutContent(userId);
    Jwt jwt = Jwt.withTokenValue("t").header("alg", "none").subject(String.valueOf(userId)).build();

    mvc.perform(post("/learning-paths/tasks/{taskId}/complete", taskId)
            .with(SecurityMockMvcRequestPostProcessors.jwt().jwt(jwt)))
        .andExpect(status().isNoContent());
  }

  @Test
  void completeTaskReturns404ForNonOwnerOrMissing() throws Exception {
    long ownerUserId = 888102L;
    long otherUserId = 888103L;
    long taskId = newTaskWithoutContent(ownerUserId);
    Jwt jwt = Jwt.withTokenValue("t").header("alg", "none").subject(String.valueOf(otherUserId)).build();

    mvc.perform(post("/learning-paths/tasks/{taskId}/complete", taskId)
            .with(SecurityMockMvcRequestPostProcessors.jwt().jwt(jwt)))
        .andExpect(status().isNotFound());
  }
}
```

（`spring-security-test`가 이미 `build.gradle.kts`의 `testImplementation("org.springframework.boot:spring-boot-starter-security-test")`로 존재하므로 `SecurityMockMvcRequestPostProcessors`는 바로 사용 가능하다.）

- [ ] **Step 7: 테스트가 실패하는지 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.path.LearningPathControllerCompleteTaskTest"`
Expected: FAIL — `POST /learning-paths/tasks/{taskId}/complete` 엔드포인트가 없어 404 대신 다른 결과(둘째 테스트는 우연히 통과할 수 있으나 첫째 테스트는 반드시 실패).

- [ ] **Step 8: LearningPathController에 완료 엔드포인트 추가**

`devpath-learning-svc/src/main/java/ai/devpath/learning/path/LearningPathController.java`에서:

old_string:
```java
  public LearningPathController(LearningPathGenerationService generation, LearningPathQueryService queries,
      @Value("${devpath.path.sse-timeout-ms:180000}") long sseTimeoutMs) {
    this.generation = generation;
    this.queries = queries;
    this.sseTimeoutMs = sseTimeoutMs;
  }
```

new_string:
```java
  private final PathWeeklyTaskRepository weeklyTasks;

  public LearningPathController(LearningPathGenerationService generation, LearningPathQueryService queries,
      PathWeeklyTaskRepository weeklyTasks,
      @Value("${devpath.path.sse-timeout-ms:180000}") long sseTimeoutMs) {
    this.generation = generation;
    this.queries = queries;
    this.weeklyTasks = weeklyTasks;
    this.sseTimeoutMs = sseTimeoutMs;
  }

  /** content_id가 없어 콘텐츠 진척 완료로 자동 처리되지 않는 주간 과제의 명시적 완료 처리. */
  @PostMapping("/tasks/{taskId}/complete")
  public ResponseEntity<Void> completeTask(@AuthenticationPrincipal Jwt jwt, @PathVariable long taskId) {
    int updated = weeklyTasks.completeTaskIfOwned(uid(jwt), taskId);
    return updated == 1 ? ResponseEntity.noContent().build() : ResponseEntity.notFound().build();
  }
```

- [ ] **Step 9: 테스트 통과 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.path.LearningPathControllerCompleteTaskTest"`
Expected: PASS (2 tests)

- [ ] **Step 10: 전체 빌드 + 커밋**

Run: `cd devpath-learning-svc && ./gradlew build`
Expected: BUILD SUCCESSFUL

```bash
cd devpath-learning-svc
git add src/main/java/ai/devpath/learning/path/PathWeeklyTaskRepository.java \
        src/main/java/ai/devpath/learning/path/LearningPathController.java \
        src/test/java/ai/devpath/learning/path/PathWeeklyTaskRepositoryTest.java \
        src/test/java/ai/devpath/learning/path/LearningPathControllerCompleteTaskTest.java
git commit -m "feat(path): content_id 없는 주간 과제용 명시적 완료 API

POST /learning-paths/tasks/{taskId}/complete. content_id 있는 태스크는
ContentProgressRepository.completeActivePathTasks()로 이미 자동 처리됨 —
이 API는 그 공백(content 미연결 태스크)만 메운다."
```

（이 Task는 Task 4와 같은 레포·같은 develop 브랜치 기반이므로, Task 4 완료 후 함께 push+PR한다 — Step 11은 Task 5 이후로 넘긴다.）

---

### Task 4: devpath-learning-svc — progress 모듈(스트릭 계산 + 활동 판정 + 이벤트 발행)

**Files:**
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/UserStreak.java`
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/UserStreakRepository.java`
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/UserTimezoneView.java`
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/NotificationPrefsClient.java`
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/RestNotificationPrefsClient.java`
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/StreakRolloverService.java`
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/StreakRolloverScheduler.java`
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/SandboxRunConsumer.java`
- Modify: `devpath-learning-svc/src/main/resources/application.yml`
- Test: `devpath-learning-svc/src/test/java/ai/devpath/learning/progress/StreakRolloverServiceTest.java`
- Test: `devpath-learning-svc/src/test/java/ai/devpath/learning/progress/SandboxRunConsumerIT.java`

**Interfaces:**
- Consumes: Task 1의 `StreakReachedEvent`(devpath-shared), `user_streak` 테이블. Task 2의 `GET /notifications/internal/prefs/timezones?userIds=...` → `[{userId, timezone}]`. Task 3의 `PathWeeklyTaskRepository.hasCompletedTaskOnDate(long, LocalDate): boolean`(같은 레포, 이미 만들어짐). 기존 `OutboxRepository`/`OutboxEntry`(이벤트 발행).
- Produces: `StreakRolloverService.rollover(long userId, LocalDate localDate): void` — Task 5(dashboard)가 직접 호출하진 않지만, 이 서비스가 갱신하는 `user_streak` 테이블을 Task 5의 `UserStreakRepository`가 조회한다. `SandboxRunConsumer`는 `SandboxRunSubmittedEvent`(devpath-shared 기존)를 구독해 활동을 기록하되, 이번 태스크에서는 "오늘 활동 있었다"는 사실만 필요하므로 별도 저장 없이 즉시 `StreakRolloverService`의 당일 롤오버를 트리거하지 않는다(스케줄러가 시간대 윈도우에서 알아서 반영) — 대신 Sandbox 활동도 `hasCompletedTaskOnDate`와 동일한 방식의 "당일 활동 존재" 판정에 포함되도록 별도 `learning_activity_log` 없이 **sandbox 이벤트 수신 시각을 그대로 활동 신호**로 쓴다(아래 Step 7 참고, 최소 테이블 하나 추가).

- [ ] **Step 1: UserStreak 엔티티 실패 테스트 작성**

```java
package ai.devpath.learning.progress;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class UserStreakRepositoryTest {

  @Autowired UserStreakRepository streaks;

  @Test
  void savesAndFindsByUserId() {
    UserStreak s = new UserStreak();
    s.setUserId(777001L);
    s.setCurrentDays(3);
    s.setLongestDays(5);
    streaks.save(s);

    UserStreak found = streaks.findById(777001L).orElseThrow();
    assertThat(found.getCurrentDays()).isEqualTo(3);
    assertThat(found.getLongestDays()).isEqualTo(5);
  }

  @Test
  void findByIdReturnsEmptyWhenNoRow() {
    assertThat(streaks.findById(777999L)).isEmpty();
  }
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.progress.UserStreakRepositoryTest"`
Expected: FAIL — `UserStreak`/`UserStreakRepository` 클래스가 없어 컴파일 실패.

- [ ] **Step 3: UserStreak 엔티티 + Repository 구현**

```java
package ai.devpath.learning.progress;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.time.LocalDate;

/** 스키마: devpath-shared {@code V202607021001__user_streak.sql}. */
@Entity
@Table(name = "user_streak")
public class UserStreak {

	@Id
	@Column(name = "user_id")
	private Long userId;

	@Column(name = "current_days", nullable = false)
	private Integer currentDays = 0;

	@Column(name = "longest_days", nullable = false)
	private Integer longestDays = 0;

	@Column(name = "last_active_date")
	private LocalDate lastActiveDate;

	@Column(name = "updated_at")
	private Instant updatedAt;

	public Long getUserId() { return userId; }
	public void setUserId(Long v) { this.userId = v; }
	public Integer getCurrentDays() { return currentDays; }
	public void setCurrentDays(Integer v) { this.currentDays = v; }
	public Integer getLongestDays() { return longestDays; }
	public void setLongestDays(Integer v) { this.longestDays = v; }
	public LocalDate getLastActiveDate() { return lastActiveDate; }
	public void setLastActiveDate(LocalDate v) { this.lastActiveDate = v; }
	public Instant getUpdatedAt() { return updatedAt; }
	public void setUpdatedAt(Instant v) { this.updatedAt = v; }
}
```

```java
package ai.devpath.learning.progress;

import org.springframework.data.jpa.repository.JpaRepository;

public interface UserStreakRepository extends JpaRepository<UserStreak, Long> {
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.progress.UserStreakRepositoryTest"`
Expected: PASS (2 tests)

- [ ] **Step 5: NotificationPrefsClient 인터페이스 + REST 구현체**

`RestAiPathClient` 패턴(생성자 주입 `@Value` base-url/timeout, `RestClient`, 실패 시 전용 예외)을 그대로 따른다.

```java
package ai.devpath.learning.progress;

import java.util.List;

public interface NotificationPrefsClient {
  List<UserTimezoneView> timezonesOf(List<Long> userIds);
}
```

```java
package ai.devpath.learning.progress;

public record UserTimezoneView(long userId, String timezone) {
}
```

```java
package ai.devpath.learning.progress;

import java.time.Duration;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ParameterizedTypeReference;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class RestNotificationPrefsClient implements NotificationPrefsClient {
  private final RestClient restClient;

  public RestNotificationPrefsClient(
      @Value("${devpath.notification-svc.base-url:http://localhost:8088}") String baseUrl,
      @Value("${devpath.notification-svc.timeout:PT5S}") Duration timeout) {
    var requestFactory = new SimpleClientHttpRequestFactory();
    requestFactory.setConnectTimeout(timeout);
    requestFactory.setReadTimeout(timeout);
    this.restClient = RestClient.builder().baseUrl(baseUrl).requestFactory(requestFactory).build();
  }

  @Override
  public List<UserTimezoneView> timezonesOf(List<Long> userIds) {
    if (userIds.isEmpty()) return List.of();
    String csv = userIds.stream().map(String::valueOf).reduce((a, b) -> a + "," + b).orElse("");
    try {
      List<UserTimezoneView> result = restClient.get()
          .uri("/notifications/internal/prefs/timezones?userIds={ids}", csv)
          .retrieve()
          .body(new ParameterizedTypeReference<List<UserTimezoneView>>() {});
      return result == null ? List.of() : result;
    } catch (RestClientException e) {
      throw new NotificationPrefsUnavailableException("notification-svc timezone 조회 실패", e);
    }
  }
}
```

```java
package ai.devpath.learning.progress;

public class NotificationPrefsUnavailableException extends RuntimeException {
  public NotificationPrefsUnavailableException(String message, Throwable cause) {
    super(message, cause);
  }
}
```

- [ ] **Step 6: 활동 로그 테이블 대신 sandbox 활동을 위한 별도 테이블 없이 진행하는 대신, Sandbox 활동 판정을 위한 최소 테이블 추가 — StreakRolloverService 실패 테스트 작성**

스트릭 판정 로직: 어제 활동 있음(`PathWeeklyTaskRepository.hasCompletedTaskOnDate` 또는 `sandbox_activity_log`에 어제 행 존재) → `current_days += 1`, 마일스톤 도달 시 이벤트 발행. 없음 → `current_days = 0`.

```java
package ai.devpath.learning.progress;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import ai.devpath.learning.outbox.OutboxRepository;
import ai.devpath.learning.path.PathWeeklyTaskRepository;
import java.time.LocalDate;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class StreakRolloverServiceTest {

  @Autowired UserStreakRepository streaks;
  @Autowired OutboxRepository outbox;
  @Autowired SandboxActivityLogRepository sandboxActivity;

  private StreakRolloverService serviceWithTaskActivity(boolean hadActivity) {
    PathWeeklyTaskRepository tasks = mock(PathWeeklyTaskRepository.class);
    when(tasks.hasCompletedTaskOnDate(any(Long.class), any(LocalDate.class))).thenReturn(hadActivity);
    return new StreakRolloverService(streaks, tasks, sandboxActivity, outbox);
  }

  @Test
  void incrementsCurrentDaysWhenActivityYesterday() {
    long userId = 777101L;
    UserStreak existing = new UserStreak();
    existing.setUserId(userId);
    existing.setCurrentDays(2);
    existing.setLongestDays(2);
    existing.setLastActiveDate(LocalDate.now().minusDays(1));
    streaks.save(existing);

    serviceWithTaskActivity(true).rollover(userId, LocalDate.now());

    UserStreak after = streaks.findById(userId).orElseThrow();
    assertThat(after.getCurrentDays()).isEqualTo(3);
    assertThat(after.getLongestDays()).isEqualTo(3);
  }

  @Test
  void resetsCurrentDaysToZeroWhenNoActivity() {
    long userId = 777102L;
    UserStreak existing = new UserStreak();
    existing.setUserId(userId);
    existing.setCurrentDays(5);
    existing.setLongestDays(5);
    streaks.save(existing);

    serviceWithTaskActivity(false).rollover(userId, LocalDate.now());

    UserStreak after = streaks.findById(userId).orElseThrow();
    assertThat(after.getCurrentDays()).isEqualTo(0);
    assertThat(after.getLongestDays()).isEqualTo(5);
  }

  @Test
  void publishesStreakReachedEventOnlyAtMilestone() {
    long userId = 777103L;
    UserStreak existing = new UserStreak();
    existing.setUserId(userId);
    existing.setCurrentDays(6);
    existing.setLongestDays(6);
    streaks.save(existing);

    long before = outbox.count();
    serviceWithTaskActivity(true).rollover(userId, LocalDate.now());
    assertThat(outbox.count()).isEqualTo(before + 1);

    // 8일째(비마일스톤)는 이벤트 미발행
    long afterFirst = outbox.count();
    serviceWithTaskActivity(true).rollover(userId, LocalDate.now().plusDays(1));
    assertThat(outbox.count()).isEqualTo(afterFirst);
  }
}
```

- [ ] **Step 7: 테스트가 실패하는지 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.progress.StreakRolloverServiceTest"`
Expected: FAIL — `StreakRolloverService`/`SandboxActivityLogRepository` 클래스가 없어 컴파일 실패.

- [ ] **Step 8: SandboxActivityLog 최소 테이블 마이그레이션 추가 (devpath-shared, 이 Task 안에서 함께 처리)**

Sandbox 활동을 "당일 활동 있었는지" 판정하려면 발생 시각을 저장할 최소 테이블이 필요하다(스펙은 별도 활동 로그 테이블을 만들지 않는다고 했으나 그건 "완료 신호 자체"를 재사용한다는 뜻이지 Sandbox 이벤트 수신 시각 자체를 어딘가엔 남겨야 판정 가능 — PathWeeklyTask처럼 완료 타임스탬프가 이미 있는 테이블이 없으므로 최소 로그 테이블 1개 추가).

**Files 추가:**
- Create: `devpath-shared/src/main/resources/db/migration/V202607021003__sandbox_activity_log.sql`
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/SandboxActivityLogRepository.java`

devpath-shared에 아래 마이그레이션을 추가하고, Task 1과 동일한 브랜치(`feat/retention-build2-streak-event`)에 커밋 추가 후 재-push한다(이미 머지됐다면 새 `feat/retention-build2-sandbox-activity` 브랜치로 별도 PR):

```sql
-- Sandbox 제출을 스트릭 활동 신호로 쓰기 위한 최소 로그. owner: devpath-learning-svc.
CREATE TABLE sandbox_activity_log (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX idx_sandbox_activity_user_date ON sandbox_activity_log (user_id, occurred_at);
```

devpath-learning-svc 쪽 Repository:

```java
package ai.devpath.learning.progress;

import java.time.LocalDate;
import java.util.Map;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class SandboxActivityLogRepository {
  private final NamedParameterJdbcTemplate jdbc;

  public SandboxActivityLogRepository(NamedParameterJdbcTemplate jdbc) {
    this.jdbc = jdbc;
  }

  public void record(long userId, java.time.Instant occurredAt) {
    jdbc.update("INSERT INTO sandbox_activity_log(user_id, occurred_at) VALUES (:userId, :occurredAt)",
        Map.of("userId", userId, "occurredAt", occurredAt));
  }

  public boolean hasActivityOnDate(long userId, LocalDate date) {
    var sql = """
        SELECT EXISTS (
          SELECT 1 FROM sandbox_activity_log
          WHERE user_id = :userId AND occurred_at >= :dayStart AND occurred_at < :dayEnd
        )
        """;
    return Boolean.TRUE.equals(jdbc.queryForObject(sql, Map.of(
        "userId", userId,
        "dayStart", date.atStartOfDay(java.time.ZoneOffset.UTC).toInstant(),
        "dayEnd", date.plusDays(1).atStartOfDay(java.time.ZoneOffset.UTC).toInstant())
        , Boolean.class));
  }
}
```

（devpath-shared를 다시 publish해야 하므로, 이 Step 완료 후 `cd devpath-shared && ./gradlew flywayMigrate && ./gradlew build`로 검증 후 기존 PR에 커밋 추가 또는 신규 PR·머지·publish, 그 다음 learning-svc에서 `--refresh-dependencies`.）

- [ ] **Step 9: StreakRolloverService 구현**

마일스톤 상수는 스펙 그대로(7/14/30/60/100). `LearningPathPersistenceService.publishGenerated()`와 동일한 outbox 저장 패턴을 따른다.

```java
package ai.devpath.learning.progress;

import ai.devpath.learning.outbox.OutboxEntry;
import ai.devpath.learning.outbox.OutboxRepository;
import ai.devpath.learning.path.PathWeeklyTaskRepository;
import ai.devpath.shared.event.StreakReachedEvent;
import java.time.Instant;
import java.time.LocalDate;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.json.JsonMapper;

@Service
public class StreakRolloverService {
  private static final Set<Integer> MILESTONES = Set.of(7, 14, 30, 60, 100);

  private final UserStreakRepository streaks;
  private final PathWeeklyTaskRepository weeklyTasks;
  private final SandboxActivityLogRepository sandboxActivity;
  private final OutboxRepository outbox;
  private final JsonMapper jsonMapper = new JsonMapper();

  public StreakRolloverService(UserStreakRepository streaks, PathWeeklyTaskRepository weeklyTasks,
      SandboxActivityLogRepository sandboxActivity, OutboxRepository outbox) {
    this.streaks = streaks;
    this.weeklyTasks = weeklyTasks;
    this.sandboxActivity = sandboxActivity;
    this.outbox = outbox;
  }

  /** localDate는 유저의 로컬 자정이 막 지난 "오늘" — 판정 대상은 그 전날(localDate.minusDays(1))의 활동. */
  @Transactional
  public void rollover(long userId, LocalDate localDate) {
    LocalDate yesterday = localDate.minusDays(1);
    boolean hadActivity = weeklyTasks.hasCompletedTaskOnDate(userId, yesterday)
        || sandboxActivity.hasActivityOnDate(userId, yesterday);

    UserStreak streak = streaks.findById(userId).orElseGet(() -> {
      UserStreak s = new UserStreak();
      s.setUserId(userId);
      return s;
    });

    if (hadActivity) {
      int newCurrent = streak.getCurrentDays() + 1;
      streak.setCurrentDays(newCurrent);
      streak.setLongestDays(Math.max(streak.getLongestDays(), newCurrent));
      streak.setLastActiveDate(yesterday);
      streak.setUpdatedAt(Instant.now());
      streaks.save(streak);
      if (MILESTONES.contains(newCurrent)) {
        publishStreakReached(userId, newCurrent);
      }
    } else {
      streak.setCurrentDays(0);
      streak.setUpdatedAt(Instant.now());
      streaks.save(streak);
    }
  }

  private void publishStreakReached(long userId, int days) {
    var event = new StreakReachedEvent(UUID.randomUUID(), Instant.now(), userId, days);
    OutboxEntry entry = new OutboxEntry();
    entry.setAggregateType("user_streak");
    entry.setAggregateId(String.valueOf(userId));
    entry.setEventType(StreakReachedEvent.EVENT_TYPE);
    entry.setPayload(jsonMapper.writeValueAsString(event));
    entry.setCreatedAt(Instant.now());
    outbox.save(entry);
  }
}
```

- [ ] **Step 10: 테스트 통과 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.progress.StreakRolloverServiceTest"`
Expected: PASS (3 tests)

- [ ] **Step 11: StreakRolloverScheduler 구현 (시간대 윈도우 스캔)**

TZ 윈도우 스캔: 현재 UTC 시각 기준 각 timezone의 "로컬 자정 근접(00:00~00:59)" 여부를 판정해 대상 유저만 롤오버한다. 대상 유저 목록은 `user_streak`에 이미 행이 있는 유저 전원 + 신규 유저는 최초 활동 시 자동 생성되므로, 이 스케줄러는 **활성 학습 경로가 있는 전체 유저**를 대상으로 한다(간단화를 위해 `UserStreakRepository.findAll()`이 아니라 활성 경로 유저 목록이 필요 — `LearningPathRepository`에 없으므로 최소 쿼리 추가).

```java
package ai.devpath.learning.progress;

import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Profile;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@Profile("!test")
public class StreakRolloverScheduler {
  private static final Logger log = LoggerFactory.getLogger(StreakRolloverScheduler.class);

  private final ActiveLearnerRepository activeLearners;
  private final NotificationPrefsClient prefsClient;
  private final StreakRolloverService rolloverService;

  public StreakRolloverScheduler(ActiveLearnerRepository activeLearners,
      NotificationPrefsClient prefsClient, StreakRolloverService rolloverService) {
    this.activeLearners = activeLearners;
    this.prefsClient = prefsClient;
    this.rolloverService = rolloverService;
  }

  @Scheduled(cron = "0 0 * * * *")
  public void rolloverDueTimezones() {
    List<Long> userIds = activeLearners.activeLearnerUserIds();
    if (userIds.isEmpty()) return;

    List<UserTimezoneView> prefs;
    try {
      prefs = prefsClient.timezonesOf(userIds);
    } catch (NotificationPrefsUnavailableException e) {
      log.warn("notification-svc timezone 조회 실패 — 이번 주기 스킵, 다음 주기 재시도", e);
      return;
    }

    for (UserTimezoneView pref : prefs) {
      ZonedDateTime nowInTz = ZonedDateTime.now(ZoneId.of(pref.timezone()));
      if (nowInTz.toLocalTime().isBefore(LocalTime.of(1, 0))) {
        rolloverService.rollover(pref.userId(), nowInTz.toLocalDate());
      }
    }
  }
}
```

**Files 추가:**
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/ActiveLearnerRepository.java`
- Test: `devpath-learning-svc/src/test/java/ai/devpath/learning/progress/ActiveLearnerRepositoryTest.java`

```java
package ai.devpath.learning.progress;

import java.util.List;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class ActiveLearnerRepository {
  private final NamedParameterJdbcTemplate jdbc;

  public ActiveLearnerRepository(NamedParameterJdbcTemplate jdbc) {
    this.jdbc = jdbc;
  }

  /** 활성(ACTIVE) 학습 경로를 보유한 전체 유저 ID — 스트릭 롤오버 스캔 대상. */
  public List<Long> activeLearnerUserIds() {
    return jdbc.queryForList(
        "SELECT DISTINCT user_id FROM learning_paths WHERE status = 'ACTIVE'", Map.of(), Long.class);
  }
}
```

```java
package ai.devpath.learning.progress;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class ActiveLearnerRepositoryTest {

  @Autowired ActiveLearnerRepository repo;
  @Autowired JdbcTemplate jdbc;

  @Test
  void returnsOnlyActivePathUsers() {
    long activeUserId = 777201L;
    long archivedUserId = 777202L;
    jdbc.update("INSERT INTO learning_paths(user_id, generated_at, track, total_weeks, status) VALUES (?, now(), 'BACKEND_SPRING', 12, 'ACTIVE')", activeUserId);
    jdbc.update("INSERT INTO learning_paths(user_id, generated_at, track, total_weeks, status) VALUES (?, now(), 'BACKEND_SPRING', 12, 'ARCHIVED')", archivedUserId);

    assertThat(repo.activeLearnerUserIds()).contains(activeUserId).doesNotContain(archivedUserId);
  }
}
```

- [ ] **Step 12: ActiveLearnerRepositoryTest 통과 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.progress.ActiveLearnerRepositoryTest"`
Expected: PASS

- [ ] **Step 13: SandboxRunConsumer 실패 테스트 작성 (Kafka 통합)**

`OutboxRelayTest`/`WelcomeNotificationConsumerIT`와 동일한 `@EmbeddedKafka` 패턴.

```java
package ai.devpath.learning.progress;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

import ai.devpath.shared.event.SandboxRunSubmittedEvent;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
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
@EmbeddedKafka(partitions = 1, topics = {SandboxRunSubmittedEvent.EVENT_TYPE},
    bootstrapServersProperty = "spring.kafka.bootstrap-servers")
class SandboxRunConsumerIT {

  @Autowired KafkaTemplate<String, String> kafka;
  @Autowired JsonMapper jsonMapper;
  @Autowired SandboxActivityLogRepository sandboxActivity;

  @Test
  void consumingEventRecordsActivityForToday() throws Exception {
    long userId = 777301L;
    var event = new SandboxRunSubmittedEvent(UUID.randomUUID(), Instant.now(), userId, 1L, "java21", null);
    kafka.send(SandboxRunSubmittedEvent.EVENT_TYPE, String.valueOf(userId), jsonMapper.writeValueAsString(event));

    await().atMost(Duration.ofSeconds(20)).untilAsserted(() ->
        assertThat(sandboxActivity.hasActivityOnDate(userId, LocalDate.now())).isTrue());
  }
}
```

- [ ] **Step 14: 테스트가 실패하는지 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.progress.SandboxRunConsumerIT"`
Expected: FAIL — `SandboxRunConsumer` 클래스가 없어 이벤트를 소비하는 컴포넌트 자체가 없음(컴파일은 되나 activity가 기록되지 않아 awaitility 타임아웃으로 실패).

- [ ] **Step 15: SandboxRunConsumer 구현**

`CommunitySeedConsumer` 패턴(단일 `@Component`, `@KafkaListener`, try/catch 역직렬화 실패 시 로그+스킵)을 그대로 따른다. groupId는 이 레포의 기존 `spring.kafka.consumer.group-id: devpath-learning`을 재사용.

```java
package ai.devpath.learning.progress;

import ai.devpath.shared.event.SandboxRunSubmittedEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

@Component
public class SandboxRunConsumer {

  private static final Logger log = LoggerFactory.getLogger(SandboxRunConsumer.class);

  private final SandboxActivityLogRepository sandboxActivity;
  private final JsonMapper jsonMapper;

  public SandboxRunConsumer(SandboxActivityLogRepository sandboxActivity, JsonMapper jsonMapper) {
    this.sandboxActivity = sandboxActivity;
    this.jsonMapper = jsonMapper;
  }

  @KafkaListener(topics = SandboxRunSubmittedEvent.EVENT_TYPE, groupId = "devpath-learning")
  public void onSandboxRunSubmitted(String payload) {
    SandboxRunSubmittedEvent event;
    try {
      event = jsonMapper.readValue(payload, SandboxRunSubmittedEvent.class);
    } catch (Exception e) {
      log.warn("SandboxRunSubmittedEvent 역직렬화 실패 — skip: {}", payload, e);
      return;
    }
    sandboxActivity.record(event.userId(), event.occurredAt());
  }
}
```

- [ ] **Step 16: application.yml에 notification-svc 호출 설정 + Kafka consumer deserializer 추가**

`devpath-learning-svc/src/main/resources/application.yml`에서:

old_string:
```yaml
  ai-svc:
    base-url: ${AI_SVC_BASE_URL:http://localhost:8081}
    timeout: ${AI_SVC_TIMEOUT:PT8S}
```

new_string:
```yaml
  ai-svc:
    base-url: ${AI_SVC_BASE_URL:http://localhost:8081}
    timeout: ${AI_SVC_TIMEOUT:PT8S}
  notification-svc:
    base-url: ${NOTIFICATION_SVC_BASE_URL:http://localhost:8088}
    timeout: ${NOTIFICATION_SVC_TIMEOUT:PT5S}
```

old_string:
```yaml
  kafka:
    bootstrap-servers: ${KAFKA_BOOTSTRAP:localhost:9092}
    consumer:
      group-id: devpath-learning
      auto-offset-reset: earliest
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.apache.kafka.common.serialization.StringSerializer
```

new_string:
```yaml
  kafka:
    bootstrap-servers: ${KAFKA_BOOTSTRAP:localhost:9092}
    consumer:
      group-id: devpath-learning
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.apache.kafka.common.serialization.StringDeserializer
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.apache.kafka.common.serialization.StringSerializer
```

（이 레포는 지금까지 Kafka consumer가 전혀 없었으므로 deserializer 설정도 없었다 — notification-svc/community-svc는 이미 명시하고 있으므로 동일하게 맞춘다.）

- [ ] **Step 17: 테스트 통과 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.progress.SandboxRunConsumerIT"`
Expected: PASS

- [ ] **Step 18: 전체 빌드 + Task 3과 함께 커밋 + PR**

Run: `cd devpath-learning-svc && ./gradlew build`
Expected: BUILD SUCCESSFUL

```bash
cd devpath-learning-svc
git add src/main/java/ai/devpath/learning/progress/ \
        src/main/resources/application.yml \
        src/test/java/ai/devpath/learning/progress/
git commit -m "feat(progress): 스트릭 계산(TZ 윈도우 스캔) + Sandbox 활동 신호 + 마일스톤 이벤트 발행

user_streak 갱신, PathWeeklyTask 완료/SandboxRunSubmittedEvent를 활동 신호로 판정,
7/14/30/60/100일 마일스톤 도달 시 StreakReachedEvent 발행."
git push -u origin feat/retention-build2-task-complete
gh pr create --base develop --title "feat(learning): 참여촉진배치 Build 2 — 스트릭 계산 + 과제 완료 API" --body "스펙: documents/docs/superpowers/specs/2026-07-01-md3-retention-batch-design.md (Build 2)

- content_id 없는 주간 과제용 명시적 완료 API
- progress 모듈: user_streak, TZ 윈도우 스캔 스케줄러, PathWeeklyTask/SandboxRunSubmittedEvent 활동 판정, StreakReachedEvent 발행(마일스톤 7/14/30/60/100일)

devpath-shared PR(StreakReachedEvent, user_streak, user_notification_prefs, sandbox_activity_log 마이그레이션)과 devpath-notification-svc PR(timezone 내부 API)이 먼저 머지+publish되어야 함."
```

- [ ] **Step 19: CI 확인 후 머지**

Run: `gh pr checks <PR번호> -R DevPathAi/devpath-learning-svc` → 통과 확인 후 `gh pr merge <PR번호> -R DevPathAi/devpath-learning-svc --merge` → `gh pr view <PR번호> -R DevPathAi/devpath-learning-svc --json state,mergedAt`로 MERGED 직접 재확인.

---

### Task 5: devpath-learning-svc — Dashboard 실연동 (하드코딩 제거)

**Files:**
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/dashboard/CommunityBadgeClient.java`
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/dashboard/RestCommunityBadgeClient.java`
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/dashboard/BadgeSummaryView.java`
- Modify: `devpath-learning-svc/src/main/java/ai/devpath/learning/dashboard/DashboardService.java`
- Modify: `devpath-learning-svc/src/main/resources/application.yml`
- Test: `devpath-learning-svc/src/test/java/ai/devpath/learning/dashboard/DashboardServiceTest.java`

**Interfaces:**
- Consumes: Task 4의 `UserStreakRepository`(같은 레포). community-svc의 기존 `GET /community/users/{userId}/badges` → `List<BadgeView>`(record: `code`, `name`, `tier`, `awardedAt` — 응답 JSON 구조 그대로 매핑, 이 Task에서는 `name` 필드만 사용).
- Produces: `DashboardService.summary(long userId): DashboardSummary`가 이제 실제 `streakDays`와 `badges`(배지 이름 목록)를 반환한다 — 이 레코드 구조(`streakDays: int`, `progressPercent: int`, `nextTaskTitle: String`, `badges: List<String>`) 자체는 변경하지 않는다.

- [ ] **Step 1: 브랜치 준비**

이 Task는 Task 4와 같은 브랜치(`feat/retention-build2-task-complete`)에서 이어서 작업한다(같은 레포, Task 4가 아직 머지 전이면 로컬에서 계속). 이미 Task 4에서 PR이 올라갔다면 새 브랜치를 develop에서 분기한다:

```bash
cd devpath-learning-svc
git status -sb
# Task 4가 아직 이 브랜치(feat/retention-build2-task-complete)에 머물러 있다면 그대로 이어서 작업.
# 이미 머지됐다면:
git fetch origin && git switch develop && git pull --ff-only origin develop
git switch -c feat/retention-build2-dashboard
```

- [ ] **Step 2: DashboardServiceTest 실패 테스트 작성 (기존 파일이 있다면 확장, 없다면 신규)**

먼저 기존 테스트 파일 존재 여부 확인: `git -C devpath-learning-svc ls-tree -r --name-only origin/develop -- src/test/java/ai/devpath/learning/dashboard`. 없으면 아래 전체를 신규 작성한다.

```java
package ai.devpath.learning.dashboard;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import ai.devpath.learning.path.LearningPathQueryService;
import ai.devpath.learning.progress.UserStreak;
import ai.devpath.learning.progress.UserStreakRepository;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class DashboardServiceTest {

  @Test
  void returnsZeroStreakWhenNoStreakRow() {
    LearningPathQueryService paths = mock(LearningPathQueryService.class);
    when(paths.current(42L)).thenThrow(new NoSuchElementException());
    UserStreakRepository streaks = mock(UserStreakRepository.class);
    when(streaks.findById(42L)).thenReturn(Optional.empty());
    CommunityBadgeClient badges = mock(CommunityBadgeClient.class);
    when(badges.badgeNamesOf(42L)).thenReturn(List.of());

    DashboardService service = new DashboardService(paths, streaks, badges);
    DashboardSummary summary = service.summary(42L);

    assertThat(summary.streakDays()).isEqualTo(0);
    assertThat(summary.badges()).isEmpty();
  }

  @Test
  void returnsActualStreakDaysWhenRowExists() {
    LearningPathQueryService paths = mock(LearningPathQueryService.class);
    when(paths.current(43L)).thenThrow(new NoSuchElementException());
    UserStreakRepository streaks = mock(UserStreakRepository.class);
    UserStreak streak = new UserStreak();
    streak.setUserId(43L);
    streak.setCurrentDays(12);
    when(streaks.findById(43L)).thenReturn(Optional.of(streak));
    CommunityBadgeClient badges = mock(CommunityBadgeClient.class);
    when(badges.badgeNamesOf(43L)).thenReturn(List.of("첫 질문", "학생"));

    DashboardService service = new DashboardService(paths, streaks, badges);
    DashboardSummary summary = service.summary(43L);

    assertThat(summary.streakDays()).isEqualTo(12);
    assertThat(summary.badges()).containsExactly("첫 질문", "학생");
  }
}
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.dashboard.DashboardServiceTest"`
Expected: FAIL — `DashboardService` 생성자 시그니처가 다르고 `CommunityBadgeClient` 클래스가 없어 컴파일 실패.

- [ ] **Step 4: BadgeSummaryView + CommunityBadgeClient 인터페이스 + REST 구현체**

```java
package ai.devpath.learning.dashboard;

public record BadgeSummaryView(String code, String name, String tier) {
}
```

```java
package ai.devpath.learning.dashboard;

import java.util.List;

public interface CommunityBadgeClient {
  List<String> badgeNamesOf(long userId);
}
```

```java
package ai.devpath.learning.dashboard;

import java.time.Duration;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ParameterizedTypeReference;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class RestCommunityBadgeClient implements CommunityBadgeClient {
  private final RestClient restClient;

  public RestCommunityBadgeClient(
      @Value("${devpath.community-svc.base-url:http://localhost:8086}") String baseUrl,
      @Value("${devpath.community-svc.timeout:PT3S}") Duration timeout) {
    var requestFactory = new SimpleClientHttpRequestFactory();
    requestFactory.setConnectTimeout(timeout);
    requestFactory.setReadTimeout(timeout);
    this.restClient = RestClient.builder().baseUrl(baseUrl).requestFactory(requestFactory).build();
  }

  @Override
  public List<String> badgeNamesOf(long userId) {
    try {
      List<BadgeSummaryView> badges = restClient.get()
          .uri("/community/users/{userId}/badges", userId)
          .retrieve()
          .body(new ParameterizedTypeReference<List<BadgeSummaryView>>() {});
      return badges == null ? List.of() : badges.stream().map(BadgeSummaryView::name).toList();
    } catch (RestClientException e) {
      // 대시보드는 배지 조회 실패로 전체가 죽으면 안 됨 — 빈 목록으로 그레이스풀 디그레이드.
      return List.of();
    }
  }
}
```

- [ ] **Step 5: DashboardService 수정**

`devpath-learning-svc/src/main/java/ai/devpath/learning/dashboard/DashboardService.java`에서:

old_string:
```java
package ai.devpath.learning.dashboard;

import ai.devpath.learning.path.LearningPathQueryService;
import ai.devpath.learning.path.LearningPathView;
import ai.devpath.learning.path.WeeklyTaskView;
import java.util.List;
import java.util.NoSuchElementException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DashboardService {
  private final LearningPathQueryService paths;

  public DashboardService(LearningPathQueryService paths) {
    this.paths = paths;
  }

  @Transactional(readOnly = true)
  public DashboardSummary summary(long userId) {
    LearningPathView path;
    try {
      path = paths.current(userId);
    } catch (NoSuchElementException e) {
      return new DashboardSummary(0, 0, null, List.of());
    }

    List<WeeklyTaskView> tasks = path.milestones().stream()
        .flatMap(m -> m.tasks().stream())
        .toList();
    long completed = tasks.stream().filter(WeeklyTaskView::completed).count();
    int progress = tasks.isEmpty() ? 0 : (int) Math.round(completed * 100.0 / tasks.size());
    String nextTask = tasks.stream()
        .filter(t -> !t.completed())
        .findFirst()
        .map(WeeklyTaskView::title)
        .orElse(null);

    return new DashboardSummary(0, progress, nextTask, List.of("첫 학습 경로 생성"));
  }
}
```

new_string:
```java
package ai.devpath.learning.dashboard;

import ai.devpath.learning.path.LearningPathQueryService;
import ai.devpath.learning.path.LearningPathView;
import ai.devpath.learning.path.WeeklyTaskView;
import ai.devpath.learning.progress.UserStreakRepository;
import java.util.List;
import java.util.NoSuchElementException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DashboardService {
  private final LearningPathQueryService paths;
  private final UserStreakRepository streaks;
  private final CommunityBadgeClient badgeClient;

  public DashboardService(LearningPathQueryService paths, UserStreakRepository streaks,
      CommunityBadgeClient badgeClient) {
    this.paths = paths;
    this.streaks = streaks;
    this.badgeClient = badgeClient;
  }

  @Transactional(readOnly = true)
  public DashboardSummary summary(long userId) {
    int streakDays = streaks.findById(userId).map(s -> s.getCurrentDays()).orElse(0);
    List<String> badges = badgeClient.badgeNamesOf(userId);

    LearningPathView path;
    try {
      path = paths.current(userId);
    } catch (NoSuchElementException e) {
      return new DashboardSummary(streakDays, 0, null, badges);
    }

    List<WeeklyTaskView> tasks = path.milestones().stream()
        .flatMap(m -> m.tasks().stream())
        .toList();
    long completed = tasks.stream().filter(WeeklyTaskView::completed).count();
    int progress = tasks.isEmpty() ? 0 : (int) Math.round(completed * 100.0 / tasks.size());
    String nextTask = tasks.stream()
        .filter(t -> !t.completed())
        .findFirst()
        .map(WeeklyTaskView::title)
        .orElse(null);

    return new DashboardSummary(streakDays, progress, nextTask, badges);
  }
}
```

- [ ] **Step 6: application.yml에 community-svc 호출 설정 추가**

old_string:
```yaml
  notification-svc:
    base-url: ${NOTIFICATION_SVC_BASE_URL:http://localhost:8088}
    timeout: ${NOTIFICATION_SVC_TIMEOUT:PT5S}
```

new_string:
```yaml
  notification-svc:
    base-url: ${NOTIFICATION_SVC_BASE_URL:http://localhost:8088}
    timeout: ${NOTIFICATION_SVC_TIMEOUT:PT5S}
  community-svc:
    base-url: ${COMMUNITY_SVC_BASE_URL:http://localhost:8086}
    timeout: ${COMMUNITY_SVC_TIMEOUT:PT3S}
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.dashboard.DashboardServiceTest"`
Expected: PASS (2 tests)

- [ ] **Step 8: DashboardController가 새 생성자 시그니처와 호환되는지 컴파일 확인**

`DashboardController`는 `DashboardService`를 주입받아 쓰기만 하므로 생성자 변경의 영향을 받지 않지만, 전체 컴파일로 확인한다.

Run: `cd devpath-learning-svc && ./gradlew build`
Expected: BUILD SUCCESSFUL — 실패 시 `DashboardController.java`를 열어 `DashboardService` 사용부가 새 생성자와 무관하게 동작하는지(Spring이 자동 주입하므로 보통 문제 없음) 확인.

- [ ] **Step 9: 커밋 + Task 3·4와 함께 푸시**

```bash
cd devpath-learning-svc
git add src/main/java/ai/devpath/learning/dashboard/ \
        src/main/resources/application.yml \
        src/test/java/ai/devpath/learning/dashboard/
git commit -m "feat(dashboard): streakDays·badges 하드코딩 제거, 실연동

user_streak·community-svc 배지 API 실제 조회. 배지 조회 실패는
그레이스풀 디그레이드(빈 목록)로 대시보드 전체 장애 방지."
git push -u origin feat/retention-build2-task-complete
```

（이미 Task 4에서 같은 브랜치로 PR을 올렸다면 `git push`만으로 기존 PR에 커밋이 추가된다. Task 4에서 이미 머지됐고 이 Task가 별도 브랜치라면 Step 1에서 만든 새 브랜치로 별도 PR을 올린다: `gh pr create --base develop --title "feat(learning): 대시보드 스트릭·배지 실연동" --body "Task 4(스트릭 계산) 후속. 하드코딩 제거."`）

- [ ] **Step 10: CI 확인 후 머지**

Run: `gh pr checks <PR번호> -R DevPathAi/devpath-learning-svc` → 통과 확인 후 머지 → `gh pr view <PR번호> -R DevPathAi/devpath-learning-svc --json state,mergedAt`로 MERGED 직접 재확인.

---

### Task 6: devpath-community-svc — StreakReachedConsumer (COMMUNITY 배지 트리거)

**Files:**
- Create: `devpath-community-svc/src/main/java/ai/devpath/community/badge/StreakReachedConsumer.java`
- Modify: `devpath-community-svc/build.gradle.kts`(devpath-shared 버전 갱신 불필요, `--refresh-dependencies`만)
- Test: `devpath-community-svc/src/test/java/ai/devpath/community/badge/StreakReachedConsumerIT.java`

**Interfaces:**
- Consumes: Task 1의 `StreakReachedEvent`(devpath-shared, 새 SNAPSHOT 필요). 기존 `BadgeService.award(long userId, BadgeCode code, String sourceType, long sourceId): boolean`(변경 없음, 그대로 호출).
- Produces: 없음(이 Task가 Build 2의 마지막 소비자).

- [ ] **Step 1: 브랜치 준비 (devpath-shared 새 SNAPSHOT 수신)**

```bash
cd devpath-community-svc
git fetch origin
git switch develop
git pull --ff-only origin develop
git switch -c feat/retention-build2-streak-badge
./gradlew compileJava --refresh-dependencies
```
Expected: BUILD SUCCESSFUL. 새 `StreakReachedEvent`가 classpath에 있는지 확인: `find ~/.gradle/caches -name "devpath-shared-0.0.1-SNAPSHOT.jar" -newer build.gradle.kts | xargs -I{} unzip -l {} | grep StreakReachedEvent`(경로는 환경에 따라 다를 수 있음 — Windows는 `%USERPROFILE%\.gradle\caches`) 또는 단순히 Step 2의 테스트가 컴파일되는지로 판별.

- [ ] **Step 2: 실패하는 통합 테스트 작성**

`CommunitySeedConsumerIT` 패턴(`@SpringBootTest` + `@ActiveProfiles("test")` + `@EmbeddedKafka`)을 그대로 따른다.

```java
package ai.devpath.community.badge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

import ai.devpath.shared.event.StreakReachedEvent;
import java.time.Duration;
import java.time.Instant;
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
@EmbeddedKafka(partitions = 1, topics = {StreakReachedEvent.EVENT_TYPE},
    bootstrapServersProperty = "spring.kafka.bootstrap-servers")
class StreakReachedConsumerIT {

  @Autowired KafkaTemplate<String, String> kafka;
  @Autowired JsonMapper jsonMapper;
  @Autowired UserBadgeRepository userBadges;
  @Autowired BadgeRepository badges;

  @Test
  void awardsCommunityBadgeAtDay30() throws Exception {
    long userId = 666001L;
    var event = new StreakReachedEvent(UUID.randomUUID(), Instant.now(), userId, 30);
    kafka.send(StreakReachedEvent.EVENT_TYPE, String.valueOf(userId), jsonMapper.writeValueAsString(event));

    await().atMost(Duration.ofSeconds(20)).untilAsserted(() -> {
      long communityBadgeId = badges.findByCode("COMMUNITY").orElseThrow().getId();
      assertThat(userBadges.existsByUserIdAndBadgeId(userId, communityBadgeId)).isTrue();
    });
  }

  @Test
  void doesNotAwardBadgeForNonMilestoneDay() throws Exception {
    long userId = 666002L;
    var event = new StreakReachedEvent(UUID.randomUUID(), Instant.now(), userId, 14);
    kafka.send(StreakReachedEvent.EVENT_TYPE, String.valueOf(userId), jsonMapper.writeValueAsString(event));

    // 14일째는 COMMUNITY 배지 대상이 아니므로, 짧게 대기 후 미수여 확인(고정 대기 — Build 1 WelcomeNotificationConsumerIT 패턴과 동일하게 처리하지 않고, 여기서는 음성 케이스라 await 대신 Thread.sleep 사용).
    Thread.sleep(3000);
    long communityBadgeId = badges.findByCode("COMMUNITY").orElseThrow().getId();
    assertThat(userBadges.existsByUserIdAndBadgeId(userId, communityBadgeId)).isFalse();
  }

  @Test
  void duplicateEventForSameUserIsIdempotent() throws Exception {
    long userId = 666003L;
    var event1 = new StreakReachedEvent(UUID.randomUUID(), Instant.now(), userId, 30);
    kafka.send(StreakReachedEvent.EVENT_TYPE, String.valueOf(userId), jsonMapper.writeValueAsString(event1));

    await().atMost(Duration.ofSeconds(20)).untilAsserted(() -> {
      long communityBadgeId = badges.findByCode("COMMUNITY").orElseThrow().getId();
      assertThat(userBadges.existsByUserIdAndBadgeId(userId, communityBadgeId)).isTrue();
    });

    var event2 = new StreakReachedEvent(UUID.randomUUID(), Instant.now(), userId, 60);
    kafka.send(StreakReachedEvent.EVENT_TYPE, String.valueOf(userId), jsonMapper.writeValueAsString(event2));
    Thread.sleep(3000);

    long communityBadgeId = badges.findByCode("COMMUNITY").orElseThrow().getId();
    long count = userBadges.findAll().stream()
        .filter(ub -> ub.getUserId() == userId && ub.getBadgeId() == communityBadgeId)
        .count();
    assertThat(count).isEqualTo(1); // BadgeService.award()의 기존 멱등성(PK 중복 방지)으로 중복 수여 안 됨
  }
}
```

（`badges.findByCode`가 `BadgeRepository`에 이미 존재함 — Item 1 조사에서 확인됨. `userBadges.existsByUserIdAndBadgeId`도 `BadgeService.award()`가 이미 쓰는 메서드이므로 존재. 시드 데이터(`badges` 테이블의 COMMUNITY 행)는 devpath-shared 마이그레이션(`V202606301002__badges.sql`)에 이미 있으므로 테스트에서 별도로 만들 필요 없다 — 단, 테스트 DB에 해당 마이그레이션이 이미 적용돼 있어야 하며, 기존 badge 테스트들(`BadgeServiceTest`, `BadgeTriggerTest`)이 이미 동일 전제로 동작 중이므로 문제없다.）

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `cd devpath-community-svc && ./gradlew test --tests "ai.devpath.community.badge.StreakReachedConsumerIT"`
Expected: FAIL — `StreakReachedConsumer` 클래스가 없어 이벤트가 소비되지 않고 awaitility 타임아웃.

- [ ] **Step 4: StreakReachedConsumer 구현**

`CommunitySeedConsumer` 패턴을 정확히 따른다(단일 `@Component`, `@KafkaListener(topics=EVENT_TYPE, groupId="devpath-community")`, try/catch 역직렬화, days==30 검사 후 기존 `BadgeService.award` 호출).

```java
package ai.devpath.community.badge;

import ai.devpath.shared.event.StreakReachedEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

@Component
public class StreakReachedConsumer {

  private static final int COMMUNITY_BADGE_MILESTONE_DAYS = 30;

  private static final Logger log = LoggerFactory.getLogger(StreakReachedConsumer.class);

  private final BadgeService badgeService;
  private final JsonMapper jsonMapper;

  public StreakReachedConsumer(BadgeService badgeService, JsonMapper jsonMapper) {
    this.badgeService = badgeService;
    this.jsonMapper = jsonMapper;
  }

  @KafkaListener(topics = StreakReachedEvent.EVENT_TYPE, groupId = "devpath-community")
  public void onStreakReached(String payload) {
    StreakReachedEvent event;
    try {
      event = jsonMapper.readValue(payload, StreakReachedEvent.class);
    } catch (Exception e) {
      log.warn("StreakReachedEvent 역직렬화 실패 — skip: {}", payload, e);
      return; // poison 무한재시도 방지
    }
    if (event.days() != COMMUNITY_BADGE_MILESTONE_DAYS) {
      return; // 30일 마일스톤만 COMMUNITY 배지 대상
    }
    badgeService.award(event.userId(), BadgeCode.COMMUNITY, "streak", event.userId());
  }
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd devpath-community-svc && ./gradlew test --tests "ai.devpath.community.badge.StreakReachedConsumerIT"`
Expected: PASS (3 tests)

- [ ] **Step 6: 기존 badge 패키지 테스트 회귀 확인**

Run: `cd devpath-community-svc && ./gradlew test --tests "ai.devpath.community.badge.*"`
Expected: PASS 전체(기존 `BadgeServiceTest`, `BadgeTriggerTest`, `BadgeApiMockMvcTest` 포함, 신규 컨슈머 추가로 인한 회귀 없어야 함).

- [ ] **Step 7: 전체 빌드 + 커밋 + PR**

Run: `cd devpath-community-svc && ./gradlew build`
Expected: BUILD SUCCESSFUL

```bash
cd devpath-community-svc
git add src/main/java/ai/devpath/community/badge/StreakReachedConsumer.java \
        src/test/java/ai/devpath/community/badge/StreakReachedConsumerIT.java
git commit -m "feat(badge): StreakReachedEvent 구독 — 30일 스트릭 시 COMMUNITY 배지 자동 수여

참여촉진배치 Build 2 마지막 소비자. 신규 배지 로직 없음, 기존
BadgeService.award() 트리거만 추가(CommunitySeedConsumer 패턴 재사용)."
git push -u origin feat/retention-build2-streak-badge
gh pr create --base develop --title "feat(badge): 스트릭 30일 COMMUNITY 배지 자동 수여" --body "참여촉진배치 Build 2 마지막 단계. devpath-shared의 StreakReachedEvent(Task 1)와 devpath-learning-svc의 StreakRolloverService(Task 4)가 먼저 머지+publish되어야 함.

스펙: documents/docs/superpowers/specs/2026-07-01-md3-retention-batch-design.md"
```

- [ ] **Step 8: CI 확인 후 머지**

Run: `gh pr checks <PR번호> -R DevPathAi/devpath-community-svc` → 통과 확인 후 `gh pr merge <PR번호> -R DevPathAi/devpath-community-svc --merge` → `gh pr view <PR번호> -R DevPathAi/devpath-community-svc --json state,mergedAt`로 MERGED 직접 재확인.

---

### Task 7: 끝단간 수동 검증 (선택, 로컬 인프라 필요)

**목적**: Build 1(notification-svc device API)처럼 실제 서비스를 띄워 스트릭 계산 → 이벤트 발행 → 배지 수여 전체 플로우가 실제로 연결되는지 확인한다. CI의 서비스별 단위/통합 테스트는 각 Task에서 이미 확인했으므로, 이 Task는 **여러 서비스에 걸친 이벤트 흐름**만 별도로 확인한다.

**Files:** 없음(코드 변경 없음, 수동 검증 절차만).

- [ ] **Step 1: 로컬 인프라 기동**

```bash
cd devpath-shared
docker compose up -d postgres redis kafka
```

- [ ] **Step 2: 4개 서비스 로컬 기동 (각각 별도 터미널)**

```bash
cd devpath-notification-svc && ./gradlew bootRun
cd devpath-learning-svc && ./gradlew bootRun
cd devpath-community-svc && ./gradlew bootRun
```

- [ ] **Step 3: user_streak을 마일스톤 직전(29일)으로 수동 세팅**

```bash
psql -h localhost -U devpath -d devpath -c \
  "INSERT INTO user_streak(user_id, current_days, longest_days, last_active_date) VALUES (999999, 29, 29, CURRENT_DATE - INTERVAL '1 day') ON CONFLICT (user_id) DO UPDATE SET current_days=29, longest_days=29, last_active_date=CURRENT_DATE - INTERVAL '1 day';"
psql -h localhost -U devpath -d devpath -c \
  "INSERT INTO learning_paths(user_id, generated_at, track, total_weeks, status) VALUES (999999, now(), 'BACKEND_SPRING', 12, 'ACTIVE');"
```

- [ ] **Step 4: 어제 활동을 시뮬레이션(주간 과제 완료 API 직접 호출 또는 DB 직접 삽입)**

```bash
psql -h localhost -U devpath -d devpath -c \
  "INSERT INTO path_milestones(path_id, week_num, title) SELECT id, 1, 'w1' FROM learning_paths WHERE user_id=999999 RETURNING id;"
# 위 반환된 milestone id를 다음 쿼리에 대입
psql -h localhost -U devpath -d devpath -c \
  "INSERT INTO path_weekly_tasks(milestone_id, order_num, task_type, title, required, completed_at) VALUES (<milestone_id>, 1, 'PRACTICE', 'manual test task', true, CURRENT_DATE - INTERVAL '1 day');"
```

- [ ] **Step 5: 스케줄러를 기다리지 않고 직접 트리거(테스트 프로필이 아닌 상태에서 액추에이터로 확인 어려우므로, 아래 대안)**

`StreakRolloverScheduler`는 매시간 정각에만 돈다 — 수동 검증 시에는 이 서비스 내부에 임시 REST 엔드포인트를 추가하지 않고, 대신 `@Scheduled` 크론을 로컬 한정 `application-local.yml`에서 `fixedDelay=10000`(10초)로 임시 오버라이드해 빠르게 관찰한다. 이 오버라이드 파일은 **커밋하지 않는다**.

- [ ] **Step 6: 결과 확인**

```bash
# user_streak이 30으로 증가했는지
psql -h localhost -U devpath -d devpath -c "SELECT * FROM user_streak WHERE user_id=999999;"
# COMMUNITY 배지가 수여됐는지
psql -h localhost -U devpath -d devpath -c "SELECT ub.* FROM user_badges ub JOIN badges b ON b.id=ub.badge_id WHERE ub.user_id=999999 AND b.code='COMMUNITY';"
```
Expected: `user_streak.current_days = 30`, `user_badges`에 `user_id=999999, badge_id=<COMMUNITY의 id>` 행 존재.

- [ ] **Step 7: 테스트 데이터 정리**

```bash
psql -h localhost -U devpath -d devpath -c "DELETE FROM user_badges WHERE user_id=999999; DELETE FROM path_weekly_tasks WHERE milestone_id IN (SELECT id FROM path_milestones WHERE path_id IN (SELECT id FROM learning_paths WHERE user_id=999999)); DELETE FROM path_milestones WHERE path_id IN (SELECT id FROM learning_paths WHERE user_id=999999); DELETE FROM learning_paths WHERE user_id=999999; DELETE FROM user_streak WHERE user_id=999999;"
```

---

## Self-Review 기록

**1. 스펙 커버리지**: Build 2 정의(스트릭 계산 TZ 롤오버, 대시보드 하드코딩 제거, StreakReachedEvent 발행, community-svc 컨슈머) 전부 Task 1·4·5·6에 매핑됨. 2026-07-02 정정 절(timezone 선당김)은 Task 2에 매핑됨. 브레인스토밍 중 발견한 추가 요구사항(PathWeeklyTask 완료 처리 공백)은 Task 3에 매핑됨.

**2. Placeholder 스캔**: "TBD", "TODO", "add appropriate" 패턴 없음. 모든 Step에 완전한 코드 또는 정확한 명령이 포함됨.

**3. 타입 일관성 검증**: `UserStreakRepository`(Task 4에서 정의) → Task 5의 `DashboardService`가 동일 타입·메서드(`findById(Long): Optional<UserStreak>`, JpaRepository 기본 제공)로 참조. `PathWeeklyTaskRepository.hasCompletedTaskOnDate`(Task 3에서 정의) → Task 4의 `StreakRolloverServiceTest`가 mock으로 동일 시그니처 사용. `StreakReachedEvent`(Task 1) → Task 4(발행)·Task 6(구독) 필드명(`userId`, `days`, `EVENT_TYPE`) 일치. `NotificationPrefsClient.timezonesOf`(Task 4) ↔ `InternalPrefsController`(Task 2) 응답 스키마(`{userId, timezone}[]`) 일치.

**4. 순서 의존성**: Task 1(shared) → Task 2·3(병렬 가능, 서로 무관) → Task 4(Task 2·3 산출물 소비) → Task 5(Task 4 산출물 소비) → Task 6(Task 1·4 산출물 소비). Task 3과 Task 5는 같은 레포·같은 브랜치를 공유하도록 안내했다(둘 다 devpath-learning-svc이므로 서로 다른 브랜치로 나누면 머지 충돌 위험 — Task 4가 그 사이에 낀 것은 논리적 순서이지 브랜치 분리를 의미하지 않는다. 즉 devpath-learning-svc 관련 Task 3·4·5는 **하나의 기능 브랜치**로 묶어 진행해도 되고, PR 리뷰 단위로는 Task별 커밋으로 분리했다).
