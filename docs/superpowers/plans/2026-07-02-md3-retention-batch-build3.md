# 참여촉진배치 Build 3 (선호시간대 prefs API + 일일 리마인더 스케줄러) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** notification-svc에 사용자 대면 알림 설정 API(`GET/PUT /notifications/prefs/me`)와 선호시간대 일일 리마인더 스케줄러를 추가한다. 스케줄러는 각 유저의 timezone으로 현재 시각을 환산해 "오늘 선호시간대에 도달했고 아직 안 보낸" 유저에게 하루 1회 리마인더를 전달한다.

**Architecture:** Build 2가 이미 만든 `user_notification_prefs` 테이블(모든 컬럼 존재)과 `InternalPrefsController`(내부 timezone bulk 조회) 위에 **사용자 대면 API·스케줄러 콘텐츠만 얹는다**. 전달(delivery)은 스펙의 `EmailSender`(interface + Smtp + Mock) 패턴을 그대로 미러링한 `PushSender` 인터페이스로 추상화하고, 이번 빌드의 구체 구현은 Build 1이 이미 만든 `inbox`(Notification 테이블)에 행을 쓰는 `InboxPushSender`로 한다. 실제 FCM 발송(`FcmPushSender`)은 Firebase 서비스계정 인프라가 아직 없어 **후속으로 명시 연기**한다(스펙이 SMTP를 Build 5로 연기한 것과 동일한 이유·패턴). 당일 중복 발송 방지는 별도 스키마 추가 없이 inbox에 "오늘 생성된 `DAILY_REMINDER` 행이 있는가"로 판정한다.

**Tech Stack:** Java 21 · Spring Boot 4.0.7 · Gradle(Kotlin DSL) · Spring Data JPA · Spring Security(OAuth2 Resource Server, HS256) · Spring `@Scheduled`. **신규 의존성 없음.** devpath-shared(중앙 Flyway, GitHub Packages)는 이미 최신(Build 2에서 publish된 `user_notification_prefs`/`notifications` 스키마 사용).

**스펙:** [2026-07-01-md3-retention-batch-design.md](../specs/2026-07-01-md3-retention-batch-design.md) — §"컴포넌트별 설계 › notification-svc"의 `PrefsController`·`PreferredTimeReminderScheduler` 항목 + §"빌드 분해 › Build 3" + §"설계 트레이드오프 — timezone 소유권".

## Global Constraints

- **스키마 변경 없음.** `flyway.enabled: false`(main 프로파일, `ddl-auto: validate`) 유지. `user_notification_prefs`·`notifications`·`device_token` 테이블은 devpath-shared가 이미 소유·publish 완료(Build 1·2). 이번 빌드는 devpath-shared에 손대지 않는다.
- 신규 작업은 `devpath-notification-svc`의 `develop`에서 **단일 브랜치** `feat/retention-build3-reminders`를 분기해 진행한다(CLAUDE.md 절대조건 4). 공유 브랜치 직접 작업 금지.
- **TDD**(절대조건 2): 모든 기능은 실패하는 테스트를 먼저 작성하고 최소 구현으로 통과시킨다. 변경 후 반드시 테스트 실행으로 통과를 눈으로 확인한다.
- **추측 금지**(절대조건 1): 명세에 없는 코드를 임의 구현하지 않는다.
- 테스트 실행 전제: 로컬 Postgres(`localhost:5432/devpath`, `devpath`/`localdev`, docker `postgres`) 기동. `@SpringBootTest` 통합 테스트는 `application-test.yml`의 `flyway.enabled: true`가 devpath-shared jar의 `classpath:db/migration`을 적용해 스키마를 만든다. 순수 단위 테스트(Mockito)는 DB 불요.
- 서비스 간 인증: 사용자 대면 엔드포인트(`/notifications/prefs/me`)는 JWT 필요(`SecurityConfig`의 `anyRequest().authenticated()`). 유저 식별은 기존 관례대로 `Long.parseLong(jwt.getSubject())`(참고: `DeviceController`).
- 커밋은 Conventional Commits. 각 Task 끝에서 커밋하고, 머지는 하지 않는다(컨트롤러/사용자 몫). PR 생성까지만.

## File Structure

- `prefs/` (기존, Build 2): `UserNotificationPrefs`(setter 추가), `UserNotificationPrefsRepository`(쿼리 메서드 1개 추가), `UserTimezoneView`, `InternalPrefsController`(무변경). **신규**: `UserNotificationPrefsService`, `PrefsController`, `NotificationPrefsView`, `UpdateNotificationPrefsRequest`.
- `push/` (신규 패키지): `PushSender`(interface), `InboxPushSender`(구현).
- `reminder/` (신규 패키지): `DailyReminderService`, `PreferredTimeReminderScheduler`.
- `inbox/` (기존): `NotificationRepository`에 당일 중복판정 쿼리 메서드 1개 추가. `Notification`/`WelcomeNotificationConsumer` 무변경.
- `NotificationApplication`: `@EnableScheduling` 추가.
- `src/test/resources/application-test.yml`: 테스트 중 스케줄러 자동실행 비활성 프로퍼티 추가.
- `README.md` / `CLAUDE.md`: 도메인 표에 `prefs`·`reminder` 반영.

---

### Task 1: prefs 도메인 — 엔티티 setter 보강 + UserNotificationPrefsService

**Files:**
- Modify: `devpath-notification-svc/src/main/java/ai/devpath/notification/prefs/UserNotificationPrefs.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/prefs/UserNotificationPrefsService.java`
- Test: `devpath-notification-svc/src/test/java/ai/devpath/notification/prefs/UserNotificationPrefsServiceTest.java`

**Interfaces:**
- Consumes: 기존 `UserNotificationPrefsRepository extends JpaRepository<UserNotificationPrefs, Long>`(`findById`/`save`).
- Produces: `UserNotificationPrefsService`
  - `UserNotificationPrefs getOrDefault(long userId)` — 행이 있으면 반환, 없으면 `userId`만 세팅한 **미저장** 기본값 엔티티 반환(엔티티 필드 이니셜라이저가 timezone=`Asia/Seoul`, preferredTimeSlot=`19:00`, reminderEnabled=true, weeklyReportEmailEnabled=true 제공).
  - `UserNotificationPrefs upsert(long userId, String timezone, String preferredTimeSlot, boolean reminderEnabled, boolean weeklyReportEmailEnabled)` — 행 있으면 갱신·없으면 생성, `updatedAt=Instant.now()` 세팅 후 저장, 저장본 반환.
  - Task 2(`PrefsController`)가 이 두 메서드를 그대로 호출한다.

- [ ] **Step 1: UserNotificationPrefs에 setter가 없어 실패하는 서비스 테스트 작성**

`devpath-notification-svc/src/test/java/ai/devpath/notification/prefs/UserNotificationPrefsServiceTest.java`:

```java
package ai.devpath.notification.prefs;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/** 순수 단위테스트(Spring 컨텍스트·DB 불요). prefs 조회 기본값 + upsert 로직. */
class UserNotificationPrefsServiceTest {

  private UserNotificationPrefsRepository repo;
  private UserNotificationPrefsService service;

  @BeforeEach
  void setUp() {
    repo = mock(UserNotificationPrefsRepository.class);
    service = new UserNotificationPrefsService(repo);
  }

  @Test
  void getOrDefaultReturnsDefaultsWhenNoRow() {
    when(repo.findById(42L)).thenReturn(Optional.empty());

    UserNotificationPrefs p = service.getOrDefault(42L);

    assertThat(p.getUserId()).isEqualTo(42L);
    assertThat(p.getTimezone()).isEqualTo("Asia/Seoul");
    assertThat(p.getPreferredTimeSlot()).isEqualTo("19:00");
    assertThat(p.getReminderEnabled()).isTrue();
    assertThat(p.getWeeklyReportEmailEnabled()).isTrue();
  }

  @Test
  void getOrDefaultReturnsStoredRowWhenPresent() {
    UserNotificationPrefs existing = new UserNotificationPrefs();
    existing.setUserId(42L);
    existing.setTimezone("America/New_York");
    when(repo.findById(42L)).thenReturn(Optional.of(existing));

    assertThat(service.getOrDefault(42L).getTimezone()).isEqualTo("America/New_York");
  }

  @Test
  void upsertCreatesRowWithAllFieldsAndUpdatedAt() {
    when(repo.findById(42L)).thenReturn(Optional.empty());
    when(repo.save(any(UserNotificationPrefs.class))).thenAnswer(inv -> inv.getArgument(0));

    service.upsert(42L, "Europe/Paris", "08:30", false, false);

    ArgumentCaptor<UserNotificationPrefs> cap = ArgumentCaptor.forClass(UserNotificationPrefs.class);
    verify(repo).save(cap.capture());
    UserNotificationPrefs saved = cap.getValue();
    assertThat(saved.getUserId()).isEqualTo(42L);
    assertThat(saved.getTimezone()).isEqualTo("Europe/Paris");
    assertThat(saved.getPreferredTimeSlot()).isEqualTo("08:30");
    assertThat(saved.getReminderEnabled()).isFalse();
    assertThat(saved.getWeeklyReportEmailEnabled()).isFalse();
    assertThat(saved.getUpdatedAt()).isNotNull();
  }

  @Test
  void upsertUpdatesExistingRowInPlace() {
    UserNotificationPrefs existing = new UserNotificationPrefs();
    existing.setUserId(42L);
    existing.setTimezone("Asia/Seoul");
    when(repo.findById(42L)).thenReturn(Optional.of(existing));
    when(repo.save(any(UserNotificationPrefs.class))).thenAnswer(inv -> inv.getArgument(0));

    service.upsert(42L, "America/New_York", "21:00", true, false);

    verify(repo).save(existing); // 같은 행 재사용
    assertThat(existing.getTimezone()).isEqualTo("America/New_York");
    assertThat(existing.getPreferredTimeSlot()).isEqualTo("21:00");
  }
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd devpath-notification-svc && ./gradlew test --tests "ai.devpath.notification.prefs.UserNotificationPrefsServiceTest"`
Expected: FAIL — `UserNotificationPrefsService` 클래스가 없고, `setPreferredTimeSlot`/`setReminderEnabled`/`setWeeklyReportEmailEnabled` setter가 없어 컴파일 실패.

- [ ] **Step 3: UserNotificationPrefs에 누락 setter 3개 추가**

`UserNotificationPrefs.java`에서 기존 getter/setter 블록 중, `getPreferredTimeSlot`/`getReminderEnabled`/`getWeeklyReportEmailEnabled`에 대응하는 setter가 없다. 다음 3개를 추가한다(기존 `setTimezone` 아래, `getPreferredTimeSlot` 등과 짝을 맞춰).

old_string:
```java
	public String getTimezone() { return timezone; }
	public void setTimezone(String v) { this.timezone = v; }
	public String getPreferredTimeSlot() { return preferredTimeSlot; }
	public Boolean getReminderEnabled() { return reminderEnabled; }
	public Boolean getWeeklyReportEmailEnabled() { return weeklyReportEmailEnabled; }
```

new_string:
```java
	public String getTimezone() { return timezone; }
	public void setTimezone(String v) { this.timezone = v; }
	public String getPreferredTimeSlot() { return preferredTimeSlot; }
	public void setPreferredTimeSlot(String v) { this.preferredTimeSlot = v; }
	public Boolean getReminderEnabled() { return reminderEnabled; }
	public void setReminderEnabled(Boolean v) { this.reminderEnabled = v; }
	public Boolean getWeeklyReportEmailEnabled() { return weeklyReportEmailEnabled; }
	public void setWeeklyReportEmailEnabled(Boolean v) { this.weeklyReportEmailEnabled = v; }
```

- [ ] **Step 4: UserNotificationPrefsService 구현**

`devpath-notification-svc/src/main/java/ai/devpath/notification/prefs/UserNotificationPrefsService.java`:

```java
package ai.devpath.notification.prefs;

import java.time.Instant;
import org.springframework.stereotype.Service;

/** 사용자 알림 설정 조회(기본값 포함)·upsert. PrefsController 및 리마인더 흐름의 진입점. */
@Service
public class UserNotificationPrefsService {

	private final UserNotificationPrefsRepository repo;

	public UserNotificationPrefsService(UserNotificationPrefsRepository repo) {
		this.repo = repo;
	}

	/** 저장된 설정이 있으면 반환, 없으면 userId만 세팅한 미저장 기본값 엔티티 반환. */
	public UserNotificationPrefs getOrDefault(long userId) {
		return repo.findById(userId).orElseGet(() -> {
			UserNotificationPrefs p = new UserNotificationPrefs();
			p.setUserId(userId);
			return p; // 나머지 필드는 엔티티 이니셜라이저 기본값
		});
	}

	/** 전체 필드 교체 upsert. */
	public UserNotificationPrefs upsert(long userId, String timezone, String preferredTimeSlot,
			boolean reminderEnabled, boolean weeklyReportEmailEnabled) {
		UserNotificationPrefs p = repo.findById(userId).orElseGet(UserNotificationPrefs::new);
		p.setUserId(userId);
		p.setTimezone(timezone);
		p.setPreferredTimeSlot(preferredTimeSlot);
		p.setReminderEnabled(reminderEnabled);
		p.setWeeklyReportEmailEnabled(weeklyReportEmailEnabled);
		p.setUpdatedAt(Instant.now());
		return repo.save(p);
	}
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd devpath-notification-svc && ./gradlew test --tests "ai.devpath.notification.prefs.UserNotificationPrefsServiceTest"`
Expected: PASS (4 tests)

- [ ] **Step 6: 브랜치 생성 + 커밋**

```bash
cd devpath-notification-svc
git fetch origin
git switch develop
git pull --ff-only origin develop
git switch -c feat/retention-build3-reminders
git add src/main/java/ai/devpath/notification/prefs/UserNotificationPrefs.java \
        src/main/java/ai/devpath/notification/prefs/UserNotificationPrefsService.java \
        src/test/java/ai/devpath/notification/prefs/UserNotificationPrefsServiceTest.java
git commit -m "feat(prefs): 알림 설정 조회(기본값)·upsert 서비스 + 엔티티 setter 보강

참여촉진배치 Build 3 — 사용자 대면 prefs API의 도메인 계층."
```

---

### Task 2: 사용자 대면 PrefsController (`GET/PUT /notifications/prefs/me`)

**Files:**
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/prefs/NotificationPrefsView.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/prefs/UpdateNotificationPrefsRequest.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/prefs/PrefsController.java`
- Test: `devpath-notification-svc/src/test/java/ai/devpath/notification/prefs/PrefsControllerIT.java`

**Interfaces:**
- Consumes: `UserNotificationPrefsService`(Task 1).
- Produces:
  - `GET /notifications/prefs/me` → 200 `NotificationPrefsView(String timezone, String preferredTimeSlot, boolean reminderEnabled, boolean weeklyReportEmailEnabled)`. 행 없으면 기본값 반환.
  - `PUT /notifications/prefs/me` — body `UpdateNotificationPrefsRequest(String timezone, String preferredTimeSlot, Boolean reminderEnabled, Boolean weeklyReportEmailEnabled)`. 4개 필드 모두 필수(전체 교체). 검증: `timezone`은 유효 IANA(`ZoneId.of`), `preferredTimeSlot`은 `HH:mm`(`LocalTime.parse`). 검증 실패·필드 누락 → 400. 성공 → 200 갱신된 `NotificationPrefsView`. 인증 없으면 401.
- SecurityConfig 변경 없음 — `/notifications/prefs/me`는 `/notifications/internal/**`(permitAll)에 해당하지 않으므로 `anyRequest().authenticated()`로 자동 보호된다.

- [ ] **Step 1: 실패하는 통합 테스트 작성**

`devpath-notification-svc/src/test/java/ai/devpath/notification/prefs/PrefsControllerIT.java`:

```java
package ai.devpath.notification.prefs;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class PrefsControllerIT {

  @Autowired MockMvc mvc;

  private static Jwt jwtFor(long userId) {
    return Jwt.withTokenValue("t").header("alg", "none").subject(String.valueOf(userId)).build();
  }

  @Test
  void getReturnsDefaultsWhenNoRow() throws Exception {
    mvc.perform(get("/notifications/prefs/me").with(jwt().jwt(jwtFor(990101L))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.timezone").value("Asia/Seoul"))
        .andExpect(jsonPath("$.preferredTimeSlot").value("19:00"))
        .andExpect(jsonPath("$.reminderEnabled").value(true))
        .andExpect(jsonPath("$.weeklyReportEmailEnabled").value(true));
  }

  @Test
  void putThenGetReturnsUpdatedValues() throws Exception {
    mvc.perform(put("/notifications/prefs/me").with(jwt().jwt(jwtFor(990102L)))
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"timezone\":\"America/New_York\",\"preferredTimeSlot\":\"08:30\",\"reminderEnabled\":false,\"weeklyReportEmailEnabled\":false}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.timezone").value("America/New_York"))
        .andExpect(jsonPath("$.preferredTimeSlot").value("08:30"))
        .andExpect(jsonPath("$.reminderEnabled").value(false));

    mvc.perform(get("/notifications/prefs/me").with(jwt().jwt(jwtFor(990102L))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.timezone").value("America/New_York"))
        .andExpect(jsonPath("$.preferredTimeSlot").value("08:30"));
  }

  @Test
  void putRejectsInvalidTimezone() throws Exception {
    mvc.perform(put("/notifications/prefs/me").with(jwt().jwt(jwtFor(990103L)))
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"timezone\":\"Mars/Olympus\",\"preferredTimeSlot\":\"19:00\",\"reminderEnabled\":true,\"weeklyReportEmailEnabled\":true}"))
        .andExpect(status().isBadRequest());
  }

  @Test
  void putRejectsInvalidTimeSlot() throws Exception {
    mvc.perform(put("/notifications/prefs/me").with(jwt().jwt(jwtFor(990104L)))
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"timezone\":\"Asia/Seoul\",\"preferredTimeSlot\":\"25:99\",\"reminderEnabled\":true,\"weeklyReportEmailEnabled\":true}"))
        .andExpect(status().isBadRequest());
  }

  @Test
  void getWithoutJwtIsUnauthorized() throws Exception {
    mvc.perform(get("/notifications/prefs/me"))
        .andExpect(status().isUnauthorized());
  }
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd devpath-notification-svc && ./gradlew test --tests "ai.devpath.notification.prefs.PrefsControllerIT"`
Expected: FAIL — `NotificationPrefsView`/`UpdateNotificationPrefsRequest`/`PrefsController`가 없어 컴파일 실패.

- [ ] **Step 3: NotificationPrefsView + UpdateNotificationPrefsRequest 구현**

`NotificationPrefsView.java`:

```java
package ai.devpath.notification.prefs;

public record NotificationPrefsView(
		String timezone,
		String preferredTimeSlot,
		boolean reminderEnabled,
		boolean weeklyReportEmailEnabled) {

	static NotificationPrefsView from(UserNotificationPrefs p) {
		return new NotificationPrefsView(
				p.getTimezone(), p.getPreferredTimeSlot(),
				Boolean.TRUE.equals(p.getReminderEnabled()),
				Boolean.TRUE.equals(p.getWeeklyReportEmailEnabled()));
	}
}
```

`UpdateNotificationPrefsRequest.java`:

```java
package ai.devpath.notification.prefs;

public record UpdateNotificationPrefsRequest(
		String timezone,
		String preferredTimeSlot,
		Boolean reminderEnabled,
		Boolean weeklyReportEmailEnabled) {
}
```

- [ ] **Step 4: PrefsController 구현**

`PrefsController.java`:

```java
package ai.devpath.notification.prefs;

import java.time.LocalTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 사용자 대면 알림 설정 API. 게이트웨이 /notifications/** 라우트로 노출된다(라우트는 Build 1에서 추가됨). */
@RestController
@RequestMapping("/notifications/prefs")
public class PrefsController {

	private static final DateTimeFormatter HH_MM = DateTimeFormatter.ofPattern("HH:mm");

	private final UserNotificationPrefsService service;

	public PrefsController(UserNotificationPrefsService service) {
		this.service = service;
	}

	@GetMapping("/me")
	public NotificationPrefsView getMine(@AuthenticationPrincipal Jwt jwt) {
		return NotificationPrefsView.from(service.getOrDefault(uid(jwt)));
	}

	@PutMapping("/me")
	public ResponseEntity<NotificationPrefsView> updateMine(@AuthenticationPrincipal Jwt jwt,
			@RequestBody(required = false) UpdateNotificationPrefsRequest body) {
		if (body == null || body.timezone() == null || body.preferredTimeSlot() == null
				|| body.reminderEnabled() == null || body.weeklyReportEmailEnabled() == null
				|| !isValidZone(body.timezone()) || !isValidTimeSlot(body.preferredTimeSlot())) {
			return ResponseEntity.badRequest().build();
		}
		UserNotificationPrefs saved = service.upsert(uid(jwt), body.timezone(), body.preferredTimeSlot(),
				body.reminderEnabled(), body.weeklyReportEmailEnabled());
		return ResponseEntity.ok(NotificationPrefsView.from(saved));
	}

	private static long uid(Jwt jwt) {
		return Long.parseLong(jwt.getSubject());
	}

	private static boolean isValidZone(String tz) {
		try {
			ZoneId.of(tz);
			return true;
		} catch (RuntimeException e) {
			return false;
		}
	}

	private static boolean isValidTimeSlot(String slot) {
		try {
			LocalTime.parse(slot, HH_MM);
			return true;
		} catch (RuntimeException e) {
			return false;
		}
	}
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd devpath-notification-svc && ./gradlew test --tests "ai.devpath.notification.prefs.PrefsControllerIT"`
Expected: PASS (5 tests)

- [ ] **Step 6: 커밋**

```bash
cd devpath-notification-svc
git add src/main/java/ai/devpath/notification/prefs/NotificationPrefsView.java \
        src/main/java/ai/devpath/notification/prefs/UpdateNotificationPrefsRequest.java \
        src/main/java/ai/devpath/notification/prefs/PrefsController.java \
        src/test/java/ai/devpath/notification/prefs/PrefsControllerIT.java
git commit -m "feat(prefs): 사용자 대면 GET/PUT /notifications/prefs/me

참여촉진배치 Build 3 — timezone/선호시간대/리마인더 on-off 조회·수정.
timezone(IANA)·preferredTimeSlot(HH:mm) 검증, 유저별 upsert."
```

---

### Task 3: PushSender 추상화 + InboxPushSender

**Files:**
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/push/PushSender.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/push/InboxPushSender.java`
- Test: `devpath-notification-svc/src/test/java/ai/devpath/notification/push/InboxPushSenderTest.java`

**Interfaces:**
- Consumes: 기존 `ai.devpath.notification.inbox.NotificationRepository`(`save`) + `Notification` 엔티티.
- Produces: `PushSender` 인터페이스 — `void send(long userId, String type, String title, String body)`. Task 4(`DailyReminderService`)가 이 시그니처로 호출한다. `InboxPushSender`가 유일 구현(@Component) — Notification 행(userId/type/title/body/createdAt=now)을 저장한다.
- 설계 노트: 실제 FCM 발송은 이번 빌드 범위 밖(Firebase 서비스계정 인프라 부재). `FcmPushSender implements PushSender`를 후속에 추가하고, 그때 리마인더 당일-중복 판정(Task 4)이 여전히 inbox 행 존재로 이뤄지므로 FCM 구현도 inbox 행을 함께 남기거나 별도 reminder_log를 도입해야 한다(아래 "리스크/후속" 참조).

- [ ] **Step 1: 실패하는 단위 테스트 작성**

`devpath-notification-svc/src/test/java/ai/devpath/notification/push/InboxPushSenderTest.java`:

```java
package ai.devpath.notification.push;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import ai.devpath.notification.inbox.Notification;
import ai.devpath.notification.inbox.NotificationRepository;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/** 순수 단위테스트(DB 불요). 푸시=inbox Notification 행 생성인지 검증. */
class InboxPushSenderTest {

  @Test
  void sendPersistsInboxNotificationRow() {
    NotificationRepository repo = mock(NotificationRepository.class);
    InboxPushSender sender = new InboxPushSender(repo);

    sender.send(555L, "DAILY_REMINDER", "제목", "본문");

    ArgumentCaptor<Notification> cap = ArgumentCaptor.forClass(Notification.class);
    verify(repo).save(cap.capture());
    Notification n = cap.getValue();
    assertThat(n.getUserId()).isEqualTo(555L);
    assertThat(n.getType()).isEqualTo("DAILY_REMINDER");
    assertThat(n.getTitle()).isEqualTo("제목");
    assertThat(n.getBody()).isEqualTo("본문");
    assertThat(n.getCreatedAt()).isNotNull();
  }
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd devpath-notification-svc && ./gradlew test --tests "ai.devpath.notification.push.InboxPushSenderTest"`
Expected: FAIL — `PushSender`/`InboxPushSender`가 없어 컴파일 실패.

- [ ] **Step 3: PushSender 인터페이스 구현**

`PushSender.java`:

```java
package ai.devpath.notification.push;

/**
 * 사용자에게 알림을 "전달"하는 채널 추상화(스펙의 EmailSender 패턴과 동일 철학).
 * 이번 빌드의 구현은 인앱 inbox 저장({@link InboxPushSender}). 실제 FCM 발송은 후속.
 */
public interface PushSender {
	void send(long userId, String type, String title, String body);
}
```

- [ ] **Step 4: InboxPushSender 구현**

`InboxPushSender.java`:

```java
package ai.devpath.notification.push;

import ai.devpath.notification.inbox.Notification;
import ai.devpath.notification.inbox.NotificationRepository;
import java.time.Instant;
import org.springframework.stereotype.Component;

/** 푸시를 인앱 알림(inbox Notification 행)으로 전달한다. Build 1 inbox 인프라 재사용. */
@Component
public class InboxPushSender implements PushSender {

	private final NotificationRepository notifications;

	public InboxPushSender(NotificationRepository notifications) {
		this.notifications = notifications;
	}

	@Override
	public void send(long userId, String type, String title, String body) {
		Notification n = new Notification();
		n.setUserId(userId);
		n.setType(type);
		n.setTitle(title);
		n.setBody(body);
		n.setCreatedAt(Instant.now());
		notifications.save(n);
	}
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd devpath-notification-svc && ./gradlew test --tests "ai.devpath.notification.push.InboxPushSenderTest"`
Expected: PASS (1 test)

- [ ] **Step 6: 커밋**

```bash
cd devpath-notification-svc
git add src/main/java/ai/devpath/notification/push/ \
        src/test/java/ai/devpath/notification/push/
git commit -m "feat(push): PushSender 추상화 + InboxPushSender(인앱 전달)

참여촉진배치 Build 3 — 전달 채널 추상화(EmailSender 패턴 미러링).
실제 FCM 발송은 Firebase 인프라 부재로 후속."
```

---

### Task 4: 일일 리마인더 — 스캔 서비스 + 스케줄러 + @EnableScheduling

**배경**: 스펙 §"스케줄러 설계"의 핵심 원칙 — "전체 유저 일괄 롤오버는 틀린 설계"이므로 각 유저 timezone으로 현재 시각을 환산해 판정한다. 리마인더는 하루 1회만 보내야 하며(중복 방지), 별도 스키마를 추가하지 않기 위해 inbox에 "오늘(유저 로컬 기준) 생성된 `DAILY_REMINDER` 행이 있는지"로 판정한다.

**판정 규칙(각 `reminder_enabled=true` 유저)**: 유저 로컬 현재시각이 오늘의 `preferred_time_slot` 이상이고(도달·경과), 오늘(유저 로컬 자정 기준) 아직 리마인더 inbox 행이 없으면 → 전송. 이로써 스케줄러 실행 간격이 정확히 정렬되지 않아도 하루 정확히 1회, 선호시간 이후 최초 스캔에서 전송된다.

**Files:**
- Modify: `devpath-notification-svc/src/main/java/ai/devpath/notification/inbox/NotificationRepository.java`
- Modify: `devpath-notification-svc/src/main/java/ai/devpath/notification/prefs/UserNotificationPrefsRepository.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/reminder/DailyReminderService.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/reminder/PreferredTimeReminderScheduler.java`
- Modify: `devpath-notification-svc/src/main/java/ai/devpath/notification/NotificationApplication.java`
- Modify: `devpath-notification-svc/src/test/resources/application-test.yml`
- Test: `devpath-notification-svc/src/test/java/ai/devpath/notification/reminder/DailyReminderServiceTest.java`

**Interfaces:**
- Consumes: `UserNotificationPrefsRepository.findByReminderEnabledTrue(): List<UserNotificationPrefs>`(신규), `NotificationRepository.existsByUserIdAndTypeAndCreatedAtGreaterThanEqual(Long userId, String type, Instant since): boolean`(신규), `PushSender`(Task 3).
- Produces: `DailyReminderService.sendDueReminders(Instant now): void` — 스케줄러가 `Instant.now()`로 호출. `PreferredTimeReminderScheduler`는 `@Scheduled(fixedDelayString="${devpath.reminder.fixed-delay-ms:600000}")` 얇은 래퍼이며 `devpath.reminder.scheduler-enabled`(기본 true) 프로퍼티로 on/off.

- [ ] **Step 1: Repository 쿼리 메서드 2개 추가**

`inbox/NotificationRepository.java`:

old_string:
```java
public interface NotificationRepository extends JpaRepository<Notification, Long> {
	boolean existsByUserIdAndType(Long userId, String type);
	long countByUserId(Long userId);
}
```

new_string:
```java
public interface NotificationRepository extends JpaRepository<Notification, Long> {
	boolean existsByUserIdAndType(Long userId, String type);
	long countByUserId(Long userId);
	boolean existsByUserIdAndTypeAndCreatedAtGreaterThanEqual(Long userId, String type, java.time.Instant since);
}
```

`prefs/UserNotificationPrefsRepository.java`:

old_string:
```java
package ai.devpath.notification.prefs;

import org.springframework.data.jpa.repository.JpaRepository;

public interface UserNotificationPrefsRepository extends JpaRepository<UserNotificationPrefs, Long> {
}
```

new_string:
```java
package ai.devpath.notification.prefs;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserNotificationPrefsRepository extends JpaRepository<UserNotificationPrefs, Long> {
	List<UserNotificationPrefs> findByReminderEnabledTrue();
}
```

- [ ] **Step 2: 실패하는 DailyReminderService 단위 테스트 작성**

`devpath-notification-svc/src/test/java/ai/devpath/notification/reminder/DailyReminderServiceTest.java`:

```java
package ai.devpath.notification.reminder;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import ai.devpath.notification.inbox.NotificationRepository;
import ai.devpath.notification.prefs.UserNotificationPrefs;
import ai.devpath.notification.prefs.UserNotificationPrefsRepository;
import ai.devpath.notification.push.PushSender;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** 순수 단위테스트(DB·Spring 불요). TZ 환산·당일 중복방지 판정 로직. */
class DailyReminderServiceTest {

  private UserNotificationPrefsRepository prefs;
  private NotificationRepository inbox;
  private PushSender pushSender;
  private DailyReminderService service;

  @BeforeEach
  void setUp() {
    prefs = mock(UserNotificationPrefsRepository.class);
    inbox = mock(NotificationRepository.class);
    pushSender = mock(PushSender.class);
    service = new DailyReminderService(prefs, inbox, pushSender);
  }

  private UserNotificationPrefs prefsRow(long userId, String tz, String slot) {
    UserNotificationPrefs p = new UserNotificationPrefs();
    p.setUserId(userId);
    p.setTimezone(tz);
    p.setPreferredTimeSlot(slot);
    p.setReminderEnabled(true);
    return p;
  }

  /** 주어진 zone에서 로컬 시각이 hh:mm이 되도록 하는 Instant. */
  private Instant instantAtLocal(String tz, int hour, int minute) {
    ZoneId zone = ZoneId.of(tz);
    ZonedDateTime local = LocalDate.of(2026, 7, 2).atTime(LocalTime.of(hour, minute)).atZone(zone);
    return local.toInstant();
  }

  @Test
  void sendsWhenLocalTimeReachedAndNotYetSent() {
    when(prefs.findByReminderEnabledTrue()).thenReturn(List.of(prefsRow(1L, "Asia/Seoul", "19:00")));
    when(inbox.existsByUserIdAndTypeAndCreatedAtGreaterThanEqual(eq(1L), eq("DAILY_REMINDER"), any()))
        .thenReturn(false);

    service.sendDueReminders(instantAtLocal("Asia/Seoul", 19, 5)); // 로컬 19:05

    verify(pushSender).send(eq(1L), eq("DAILY_REMINDER"), anyString(), anyString());
  }

  @Test
  void doesNotSendBeforePreferredTime() {
    when(prefs.findByReminderEnabledTrue()).thenReturn(List.of(prefsRow(1L, "Asia/Seoul", "19:00")));
    when(inbox.existsByUserIdAndTypeAndCreatedAtGreaterThanEqual(anyLong(), anyString(), any()))
        .thenReturn(false);

    service.sendDueReminders(instantAtLocal("Asia/Seoul", 18, 55)); // 로컬 18:55

    verify(pushSender, never()).send(anyLong(), anyString(), anyString(), anyString());
  }

  @Test
  void doesNotSendTwiceSameDay() {
    when(prefs.findByReminderEnabledTrue()).thenReturn(List.of(prefsRow(1L, "Asia/Seoul", "19:00")));
    when(inbox.existsByUserIdAndTypeAndCreatedAtGreaterThanEqual(eq(1L), eq("DAILY_REMINDER"), any()))
        .thenReturn(true); // 오늘 이미 보냄

    service.sendDueReminders(instantAtLocal("Asia/Seoul", 19, 5));

    verify(pushSender, never()).send(anyLong(), anyString(), anyString(), anyString());
  }

  @Test
  void respectsPerUserTimezone() {
    // 같은 Instant라도 뉴욕 로컬은 아직 선호시간 전, 서울 로컬은 도달
    when(prefs.findByReminderEnabledTrue()).thenReturn(List.of(
        prefsRow(1L, "Asia/Seoul", "19:00"),
        prefsRow(2L, "America/New_York", "19:00")));
    when(inbox.existsByUserIdAndTypeAndCreatedAtGreaterThanEqual(anyLong(), anyString(), any()))
        .thenReturn(false);

    service.sendDueReminders(instantAtLocal("Asia/Seoul", 19, 5)); // 서울 19:05 = 뉴욕 06:05

    verify(pushSender).send(eq(1L), anyString(), anyString(), anyString());
    verify(pushSender, never()).send(eq(2L), anyString(), anyString(), anyString());
  }

  @Test
  void skipsRowWithInvalidTimezoneWithoutFailingBatch() {
    when(prefs.findByReminderEnabledTrue()).thenReturn(List.of(
        prefsRow(1L, "Mars/Olympus", "19:00"), // 잘못된 tz — skip
        prefsRow(2L, "Asia/Seoul", "19:00")));
    when(inbox.existsByUserIdAndTypeAndCreatedAtGreaterThanEqual(anyLong(), anyString(), any()))
        .thenReturn(false);

    service.sendDueReminders(instantAtLocal("Asia/Seoul", 19, 5));

    verify(pushSender).send(eq(2L), anyString(), anyString(), anyString());
    verify(pushSender, never()).send(eq(1L), anyString(), anyString(), anyString());
  }
}
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `cd devpath-notification-svc && ./gradlew test --tests "ai.devpath.notification.reminder.DailyReminderServiceTest"`
Expected: FAIL — `DailyReminderService`가 없어 컴파일 실패.

- [ ] **Step 4: DailyReminderService 구현**

`devpath-notification-svc/src/main/java/ai/devpath/notification/reminder/DailyReminderService.java`:

```java
package ai.devpath.notification.reminder;

import ai.devpath.notification.inbox.NotificationRepository;
import ai.devpath.notification.prefs.UserNotificationPrefs;
import ai.devpath.notification.prefs.UserNotificationPrefsRepository;
import ai.devpath.notification.push.PushSender;
import java.time.Instant;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/** 선호시간대 도달 유저에게 하루 1회 고정 문구 리마인더를 전달한다(TZ 인식, inbox 기반 당일 중복방지). */
@Service
public class DailyReminderService {

	private static final Logger log = LoggerFactory.getLogger(DailyReminderService.class);
	private static final DateTimeFormatter HH_MM = DateTimeFormatter.ofPattern("HH:mm");
	static final String TYPE = "DAILY_REMINDER";
	static final String TITLE = "오늘의 학습 리마인더";
	static final String BODY = "설정하신 시간이 되었어요. 오늘의 학습을 이어가 볼까요?";

	private final UserNotificationPrefsRepository prefs;
	private final NotificationRepository inbox;
	private final PushSender pushSender;

	public DailyReminderService(UserNotificationPrefsRepository prefs, NotificationRepository inbox,
			PushSender pushSender) {
		this.prefs = prefs;
		this.inbox = inbox;
		this.pushSender = pushSender;
	}

	public void sendDueReminders(Instant now) {
		for (UserNotificationPrefs p : prefs.findByReminderEnabledTrue()) {
			try {
				if (isDue(p, now)) {
					pushSender.send(p.getUserId(), TYPE, TITLE, BODY);
				}
			} catch (RuntimeException e) {
				// 잘못된 tz/slot 등 한 유저의 오류가 전체 배치를 막지 않도록 skip + 로그.
				log.warn("리마인더 판정 실패 — userId={} skip", p.getUserId(), e);
			}
		}
	}

	private boolean isDue(UserNotificationPrefs p, Instant now) {
		ZoneId zone = ZoneId.of(p.getTimezone());
		ZonedDateTime localNow = now.atZone(zone);
		LocalTime slot = LocalTime.parse(p.getPreferredTimeSlot(), HH_MM);
		ZonedDateTime slotToday = localNow.toLocalDate().atTime(slot).atZone(zone);
		if (localNow.isBefore(slotToday)) {
			return false; // 오늘 선호시간 아직 미도달
		}
		Instant startOfLocalDay = localNow.toLocalDate().atStartOfDay(zone).toInstant();
		return !inbox.existsByUserIdAndTypeAndCreatedAtGreaterThanEqual(p.getUserId(), TYPE, startOfLocalDay);
	}
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd devpath-notification-svc && ./gradlew test --tests "ai.devpath.notification.reminder.DailyReminderServiceTest"`
Expected: PASS (5 tests)

- [ ] **Step 6: PreferredTimeReminderScheduler + @EnableScheduling + 테스트 프로파일 비활성**

`devpath-notification-svc/src/main/java/ai/devpath/notification/reminder/PreferredTimeReminderScheduler.java`:

```java
package ai.devpath.notification.reminder;

import java.time.Instant;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 10분 주기로 선호시간대 도달 유저에게 리마인더를 보낸다(시간대 윈도우 스캔).
 * 테스트에서는 devpath.reminder.scheduler-enabled=false로 비활성(로직은 DailyReminderService를 직접 테스트).
 */
@Component
@ConditionalOnProperty(name = "devpath.reminder.scheduler-enabled", havingValue = "true", matchIfMissing = true)
public class PreferredTimeReminderScheduler {

	private final DailyReminderService service;

	public PreferredTimeReminderScheduler(DailyReminderService service) {
		this.service = service;
	}

	@Scheduled(fixedDelayString = "${devpath.reminder.fixed-delay-ms:600000}")
	public void run() {
		service.sendDueReminders(Instant.now());
	}
}
```

`NotificationApplication.java`에 `@EnableScheduling` 추가:

old_string:
```java
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class NotificationApplication {
```

new_string:
```java
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class NotificationApplication {
```

`src/test/resources/application-test.yml`에 스케줄러 비활성 프로퍼티 추가(테스트 컨텍스트가 실 DB에 리마인더를 자동 삽입하지 않도록):

old_string:
```yaml
devpath:
  auth:
    jwt-secret: test-secret-please-change-min-32-bytes-long-0123456789
```

new_string:
```yaml
devpath:
  auth:
    jwt-secret: test-secret-please-change-min-32-bytes-long-0123456789
  reminder:
    scheduler-enabled: false
```

- [ ] **Step 7: 전체 테스트 통과 확인(스케줄러 빈이 컨텍스트를 깨지 않는지 포함)**

Run: `cd devpath-notification-svc && ./gradlew test`
Expected: BUILD SUCCESSFUL — 기존 테스트 전부 + 신규 테스트 통과. `@EnableScheduling`/스케줄러 추가로 기존 `@SpringBootTest`(InternalPrefsControllerIT·PrefsControllerIT·WelcomeNotificationConsumerIT 등) 컨텍스트가 정상 기동해야 한다(스케줄러는 test 프로파일에서 `scheduler-enabled=false`로 미등록).

- [ ] **Step 8: 커밋**

```bash
cd devpath-notification-svc
git add src/main/java/ai/devpath/notification/inbox/NotificationRepository.java \
        src/main/java/ai/devpath/notification/prefs/UserNotificationPrefsRepository.java \
        src/main/java/ai/devpath/notification/reminder/ \
        src/main/java/ai/devpath/notification/NotificationApplication.java \
        src/test/resources/application-test.yml \
        src/test/java/ai/devpath/notification/reminder/
git commit -m "feat(reminder): 선호시간대 일일 리마인더 스케줄러(TZ 인식, 당일 1회)

참여촉진배치 Build 3 — 10분 주기 윈도우 스캔으로 유저 로컬 선호시간 도달 시
고정 문구 리마인더를 InboxPushSender로 전달. inbox 기반 당일 중복방지.
@EnableScheduling 추가, 테스트 프로파일은 스케줄러 비활성."
```

---

### Task 5: 문서 갱신(README·CLAUDE.md 도메인 표) + 전체 빌드 + PR

**배경**: 이 레포 CLAUDE.md/README.md의 도메인 표는 현재 `device`/`inbox`만 있다. Build 2에서 이미 `prefs`가 들어왔으나 표에 누락됐고, Build 3의 `prefs`(사용자 대면)·`reminder`가 추가된다. README와 CLAUDE.md 두 파일을 함께 갱신한다(한쪽만 고치지 않는다 — 정합성).

**Files:**
- Modify: `devpath-notification-svc/CLAUDE.md`
- Modify: `devpath-notification-svc/README.md`

- [ ] **Step 1: 실제 파일 내용 확인**

Run: `cd devpath-notification-svc && sed -n '1,80p' README.md` — README의 도메인/모듈 표 위치와 표기 형식을 확인한다. CLAUDE.md는 `## 도메인` 표에 `device`/`inbox` 2행이 있다(확인됨).

- [ ] **Step 2: CLAUDE.md 도메인 표에 prefs·reminder 추가**

`CLAUDE.md`의 도메인 표:

old_string:
```
| 모듈 | 역할 |
|------|------|
| device | FCM 디바이스 토큰 등록/해제 |
| inbox | 인앱 알림(웰컴 등) 저장·조회, `UserRegisteredEvent` 등 구독 |
```

new_string:
```
| 모듈 | 역할 |
|------|------|
| device | FCM 디바이스 토큰 등록/해제 |
| inbox | 인앱 알림(웰컴·리마인더 등) 저장·조회, `UserRegisteredEvent` 등 구독 |
| prefs | 알림 설정(timezone·선호시간대·리마인더/이메일 on-off): 사용자 대면 `GET/PUT /notifications/prefs/me` + 내부 timezone bulk 조회 |
| push | 전달 채널 추상화(`PushSender`) — 현재 구현은 인앱 inbox 저장, FCM 발송은 후속 |
| reminder | 선호시간대 일일 리마인더 스케줄러(TZ 윈도우 스캔, 하루 1회) |
```

- [ ] **Step 3: README.md 도메인/기능 표에 동일 반영**

README의 모듈/도메인 표(Step 1에서 확인한 형식)에 `prefs`·`push`·`reminder` 항목을, `inbox` 설명에 "리마인더"를 CLAUDE.md와 동일 취지로 추가한다. (표 형식이 CLAUDE.md와 다르면 README의 기존 형식을 따르되 내용은 동일하게.)

- [ ] **Step 4: 전체 빌드 확인**

Run: `cd devpath-notification-svc && ./gradlew build`
Expected: BUILD SUCCESSFUL

- [ ] **Step 5: 커밋 + push + PR**

```bash
cd devpath-notification-svc
git add CLAUDE.md README.md
git commit -m "docs: 도메인 표에 prefs·push·reminder 반영 (Build 3)"
git push -u origin feat/retention-build3-reminders
gh pr create --base develop \
  --title "feat(notification): 참여촉진배치 Build 3 — 선호시간대 prefs API + 일일 리마인더 스케줄러" \
  --body "## 참여촉진배치 Build 3

스펙: docs/superpowers/specs/2026-07-01-md3-retention-batch-design.md (§Build 3)
계획: docs/superpowers/plans/2026-07-02-md3-retention-batch-build3.md

### 변경
- 사용자 대면 \`GET/PUT /notifications/prefs/me\`(timezone·선호시간대·리마인더/이메일 on-off, IANA·HH:mm 검증)
- \`PushSender\` 추상화 + \`InboxPushSender\`(인앱 전달; 실제 FCM은 Firebase 인프라 부재로 후속)
- \`PreferredTimeReminderScheduler\`(10분 주기, TZ 윈도우 스캔) + \`DailyReminderService\`(inbox 기반 당일 1회 중복방지) + \`@EnableScheduling\`

### 스키마
- 변경 없음. Build 2가 publish한 \`user_notification_prefs\`(전 컬럼)·\`notifications\` 재사용.

### 테스트
- 단위: prefs 서비스 upsert/기본값, InboxPushSender, DailyReminderService(TZ 환산·당일 중복방지·유저별 tz·잘못된 tz skip)
- 통합: PrefsControllerIT(MockMvc+JWT, GET 기본값/PUT 왕복/검증 400/미인증 401)

머지하지 마세요 — 컨트롤러/사용자 검토 후 진행."
gh pr view --json number,url -R DevPathAi/devpath-notification-svc
```

- [ ] **Step 6: CI 확인**

Run: `gh pr checks <PR번호> -R DevPathAi/devpath-notification-svc` — 통과 확인. 실패 시 로그 확인 후 수정 커밋(추측 금지, 원인 규명). **머지는 하지 않는다.**

---

## Self-Review (작성자 점검)

**1. 스펙 커버리지:**
- 스펙 §"notification-svc › PrefsController: GET/PUT /notifications/prefs/me(선호시간대·timezone·리마인더 on/off)" → Task 2 ✅. (내부 `GET /notifications/internal/users/{id}/prefs`는 Build 2가 이미 `GET /notifications/internal/prefs/timezones`로 learning-svc 수요를 충족했으므로 **미구현(YAGNI)** — 새 내부 엔드포인트 불필요.)
- 스펙 §"PreferredTimeReminderScheduler(@Scheduled(fixedDelay=600000), 10분 주기): 현재 UTC를 유저 timezone 환산 후 preferred_time_slot 매칭 유저에게 고정 문구 일일 리마인더 푸시(AI 아님)" → Task 4 ✅. "푸시"의 구체 채널은 inbox(아래 결정).
- 스펙 §"빌드 분해 › Build 3: Build 1 인프라 위에서 콘텐츠만 추가" → 신규 스키마·의존성 0, 기존 inbox/prefs 재사용 ✅.
- 범위 밖(정체 탐지=Build 4, 주간 리포트/이메일=Build 5, FCM 실발송=후속)은 태스크에 포함하지 않음 ✅.

**2. 결정: "푸시"의 구체 채널 = inbox(FCM 후속 연기)** — 스펙 아키텍처 서술은 "FCM 푸시"지만 (a) notification-svc에 FCM 발송 인프라·의존성이 전무하고, (b) Build 3는 "Build 1 인프라 위 콘텐츠만 추가"로 정의됐으며, (c) 스펙이 SMTP를 Build 5로 연기한 것과 동일 논리. 따라서 스펙의 `EmailSender`(interface+Smtp+Mock) 패턴을 미러링한 `PushSender` 추상화로 이 결정을 국소화하고, 구체 전달은 Build 1의 inbox 재사용으로 한다. 이는 되돌리기 쉬운 선택(후속에 `FcmPushSender` drop-in). **이 결정이 스펙 문언과 달라 계획 검토 시 사용자 veto 가능하도록 명시함.**

**3. 타입 일관성:** `PushSender.send(long,String,String,String)`(Task 3) ↔ `DailyReminderService`의 호출(Task 4) 일치 ✅. `UserNotificationPrefsService.getOrDefault/upsert`(Task 1) ↔ `PrefsController` 호출(Task 2) 일치 ✅. `existsByUserIdAndTypeAndCreatedAtGreaterThanEqual`(Task 4 Step 1 정의) ↔ `DailyReminderService`(Task 4 Step 4 사용) 일치 ✅. `findByReminderEnabledTrue`(정의/사용) 일치 ✅.

**4. Placeholder 스캔:** 각 코드 스텝에 실제 코드 포함, "TODO/TBD" 없음 ✅. Task 5 Step 3만 README 기존 형식에 맞춰 조정 여지를 남겼으나 반영할 내용(prefs·push·reminder)은 명시했고 Step 1에서 실제 형식을 먼저 확인하도록 함.

## 리스크 / 후속

- **당일 중복방지가 inbox 행 존재에 의존** → 후속에 `FcmPushSender`를 추가할 때 (a) FCM 구현도 inbox 행을 함께 남기거나 (b) 별도 `reminder_log` 테이블/`user_notification_prefs.last_reminded_on` 컬럼(shared 마이그레이션)을 도입해 전달 채널과 독립적으로 만들 것. 이번 빌드는 inbox가 유일 전달이므로 문제없음.
- **전체 유저 매 10분 풀스캔**(`findByReminderEnabledTrue`) — 유저 급증 시 timezone 인덱싱/버킷팅 최적화 후속 필요(스펙 "리스크" 절의 N+1 우려와 동류).
- 스펙의 timezone 자동갱신(클라이언트가 기기 로컬 IANA tz를 PUT으로 전송) UI 연동은 프론트엔드 후속. 이 빌드는 PUT 계약만 제공.

## Execution Handoff

계획 완료. 저장 위치: `documents/docs/superpowers/plans/2026-07-02-md3-retention-batch-build3.md`.
