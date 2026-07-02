# Design: 참여 촉진 배치 — 스트릭 · 주간 리포트 · 정체 탐지 · 선호시간대 알림 (learning-svc / notification-svc / ai-svc / community-svc)

> 2026-07-01 · 슬라이스 "평판 기초"(MD3 Tier-2)의 마지막 서브 항목("스트릭(TZ)·주간 리포트 배치·3일 미접속 AI 제안·선호 시간대 푸시", [17_스케줄 §2](../../../17_스케줄.md) 미체크 항목). 설계 출처 [07_요구사항_정의서 FR-PRO-001~005](../../../07_요구사항_정의서.md) · [06_화면_기능_정의서 SCR-W-DASH-001](../../../06_화면_기능_정의서.md) · [04_API_명세서](../../../04_API_명세서.md) · [02_ERD_문서](../../../02_ERD_문서.md).
> **스택**: Java 21 · Spring Boot 4 · Gradle · Kafka(outbox) · shared Flyway. 관련 서비스: `devpath-learning-svc`(신규 패키지 `ai.devpath.learning.progress`), 신규 `devpath-notification-svc`(`ai.devpath.notification`), `devpath-ai-svc`(신규 패키지 `ai.devpath.aigw.retention`), `devpath-community-svc`(기존 `badge` 모듈에 컨슈머만 추가), `devpath-gateway`(라우트 추가).

## 목표 / 범위

FR-PRO-004 "리텐션 트리거 3종"(일일 푸시 / 주간 리포트 / 정체 탐지) + FR-PRO-001(스트릭) + FR-PRO-005(알림 시간대 사용자 설정)를 구현한다.

- 스트릭 계산(TZ 인식 일일 롤오버, 학습 활동 완료 기준) — learning-svc
- 주간 리포트 집계(일요일 저녁) + 이메일 발송 + 대시보드 위젯 — learning-svc(집계) + notification-svc(발송)
- 3일 미접속 정체 탐지 + AI 재참여 제안 생성 — learning-svc(탐지) + ai-svc(생성) + notification-svc(발송)
- 선호 시간대 등록 + 해당 시간 일일 리마인더 푸시 — notification-svc(신규 서비스)
- FCM 디바이스 토큰 등록(모바일 `DeviceRegistrar` 수신처) — notification-svc
- 스트릭 30일 달성 시 community-svc의 COMMUNITY 배지(Bronze) 수여 트리거 — [17_스케줄](../../../17_스케줄.md)에 "프로필·편집·스트릭 기능 부재로 결선 대기"로 명시된 3종 중 하나를 이번 빌드로 해소

**범위 밖(후속)**: platform-svc의 `timezone` 필드 정식 편입(이번엔 notification-svc가 임시 소유, 아래 "설계 트레이드오프" 참조), 주간 리포트 웹 조회 화면(이력 테이블은 만들되 조회 API/화면은 후속), Silver/Gold 배지 연동, 레벨 게이트 500/1000.

## 현재 상태 (실측, 2026-07-01)

- `/dashboard/me`(learning-svc)만 실제 구현. `DashboardSummary.streakDays`는 **하드코딩 0**, `badges`도 **하드코딩 문자열**이며 community-svc의 실제 배지 API와 연동돼 있지 않다(devpath-learning-svc `dashboard/DashboardService.java:25,39`, 별도 저장소라 링크 대신 경로로 표기).
- `/progress/**`는 gateway(devpath-gateway `src/main/resources/application.yml`)에 라우트가 없다 → 백엔드 전체 미구현.
- **[2026-07-01 정정]** `/notifications/**`는 "백엔드 전체 미구현"이 아니다 — `devpath-platform-svc`의 CLAUDE.md는 `notification: 알림(리텐션 루프)`를 이미 자신의 도메인으로 선언하고 있고, `ai.devpath.platform.notification` 패키지에 `DeviceController`(`POST/DELETE /notifications/devices`, 멱등 upsert+IDOR 방지 완비)·`DeviceToken`/`Notification` 엔티티·`WelcomeNotificationConsumer`(Kafka 컨슈머)가 **이미 동작 중**이다. `device_tokens`/`notifications` 테이블도 devpath-shared에 이미 마이그레이션되어 있다(`V202606271001`, `V202606171005`). 실제 문제는 게이트웨이에 `/notifications/**` 라우트가 없어 이 기존 코드가 외부에서 도달 불가능하다는 것뿐이다. Build 1은 "신규 생성"이 아니라 이 기존 코드를 platform-svc에서 notification-svc로 **이관**하는 작업으로 조정됨 — 상세는 [2026-07-01-md3-retention-batch-build1.md](../plans/2026-07-01-md3-retention-batch-build1.md) 참조.
- API 명세서의 `user_learning_prefs`(ERD 초안)는 어떤 서비스의 Flyway 마이그레이션에도 없다 → DB 미생성. `timezone` 컬럼은 ERD에도 없다(신규 도입 필요). (스트릭/주간리포트/정체탐지/timezone-prefs 관련해서는 이 발견이 적용되지 않는다 — 재확인 결과 여전히 그린필드가 맞다.)
- 모바일은 `DeviceRegistrar` / `PushService`(FCM, Stub·Fcm 2종 구현)가 이미 구현되어 `POST /notifications/devices`를 호출하며, 이 요청을 받아줄 컨트롤러 자체는 platform-svc에 이미 있다(위 정정 참조) — 다만 게이트웨이 라우트가 없어 요청이 닿지 못한다.
- ai-svc는 Claude 연동 인터페이스 + Mock/Ollama/Claude 구현 패턴(`ClaudeAiReviewClient`, `ClaudeMentorClient`, `AiSeedClient`)이 이미 3개 도메인(review/mentor/community-seed)에 있으나, 재참여 제안 전용 클라이언트는 없다.
- 이메일 발송 인프라(JavaMailSender/SES 등)가 전체 미존재.
- 5개 서비스(learning/community/ai/sandbox/platform-svc) 전부에 Kafka 기반 outbox(`OutboxRelay` + `OutboxRelayScheduler`, `@Scheduled(fixedDelay=2000)`, 토픽=eventType, key=aggregateId) 패턴이 이미 확립되어 있다 — 이 설계는 그대로 재사용한다.
- `devpath-shared`의 기존 `CommunityBadgeAwardedEvent` 주석에 이미 "소비자(notification-worker)는 후속"이라는 메모가 있다 — 이번에 신설하는 notification-svc가 바로 그 자리를 채운다.
- [17_스케줄](../../../17_스케줄.md)의 최신 갱신(2026-07-01)에 따르면 Bronze 배지 중 COMMUNITY(FIRST_STEP·EDITOR와 함께 시드만 되어 있는 3종 중 하나)가 "스트릭 기능 부재"로 결선 대기 상태다.

## 아키텍처

```
learning-svc (집계 소유)
  ├─ progress/ [신규]
  │    ├─ user_streak 테이블: user_id, current_days, longest_days, last_active_date
  │    ├─ 시간대 윈도우 스캔 배치(매시간 정각): "지금이 로컬 자정인 TZ" 유저만 골라
  │    │     → 어제 학습 활동 유무 반영해 스트릭 갱신 + 3일 연속 미활동 여부 판정
  │    └─ 주간 배치(일요일 저녁, 서버 TZ 기준 KST 20:00 고정): 진척도+스트릭+배지 집계
  │         └─ (동기 REST) community-svc GET /community/users/{id}/badges 로 이번주 배지 enrich
  └─ dashboard/ [기존 수정] DashboardService의 하드코딩 streakDays=0 제거 → user_streak 실연동
       │ Kafka(outbox) 발행
       ├─ progress.streak.reached        {userId, days}                    ─┐
       ├─ progress.user.stagnated        {userId, lastActiveAt, daysInactive}┤
       └─ progress.report.generated      {userId, weekOf, streakDays,       ┤
                                           progressPercent, badges, nextTask}┤
                                                                              ▼
community-svc (기존, 컨슈머만 추가)              notification-svc [신규 서비스]
  └─ badge/ 구독: progress.streak.reached          ├─ device/   FCM 토큰 등록(모바일 DeviceRegistrar 수신처)
       (days==30 → COMMUNITY 배지 수여,             ├─ prefs/    timezone·preferred_time_slot·reminder_enabled
        기존 배지 수여 로직 재사용)                  ├─ 구독: progress.user.stagnated
                                                     │    → ai-svc POST /ai/re-engagement 동기 호출 → FCM 푸시
ai-svc (기존, 확장)                                 ├─ 구독: progress.report.generated
  └─ retention/ [신규]                              │    → weekly_report 테이블 저장 + SMTP 이메일 발송
       POST /ai/re-engagement                       │       + "리포트 도착" FCM 푸시
       ReEngagementSuggestionClient(interface)       └─ 자체 스케줄러(10~15분 주기): 선호시간대 도달 유저에게
        ├─ ClaudeReEngagementClient(현재 학습경로 컨텍스트 포함)   일일 리마인더 푸시(learning-svc 이벤트와 무관)
        ├─ OllamaReEngagementClient
        └─ MockReEngagementClient(테스트/로컬)

gateway: /notifications/** 라우트 신규 추가 → notification-svc
```

**서비스 책임 분리 근거**: learning-svc는 "집계"만 하고 알림 발송 방식을 몰라도 된다(이벤트만 던짐). notification-svc는 "발송"만 하고 무엇을 왜 보내는지 몰라도 된다(이벤트 payload로 다 받음) — 이벤트를 발행하지 않는 최종 소비자이므로 자체 outbox는 두지 않는다. "정체 탐지"와 "스트릭 롤오버"는 둘 다 "어제 활동 유무" 판정이 필요해 같은 시간대 스캔 배치에서 함께 처리한다.

## 데이터 모델

**learning-svc (신규 테이블 1개, shared Flyway)**

```sql
CREATE TABLE user_streak (
  user_id         BIGINT PRIMARY KEY,
  current_days    INT NOT NULL DEFAULT 0,
  longest_days    INT NOT NULL DEFAULT 0,
  last_active_date DATE,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```
스트릭 "활동" 판정은 별도 활동 로그 테이블을 새로 만들지 않고 다음 두 신호의 OR로 정의한다: (1) 기존 `path` 모듈의 `PathWeeklyTask` 완료 타임스탬프, (2) `SandboxRunSubmittedEvent`(devpath-shared, sandbox-svc가 이미 발행 중이며 ai-svc의 코드리뷰 컨슈머가 이미 구독하고 있는 것과 동일한 토픽 — learning-svc가 두 번째 구독자로 추가되기만 하면 됨, 신규 발행 작업 불필요). **콘텐츠 열람은 이번 빌드의 활동 신호에서 제외한다** — `content` 모듈을 확인한 결과 `LearningContentView`/`InternalContentView`는 콘텐츠 자체의 조회용 read-model DTO일 뿐 "언제 열람했는지" 타임스탬프를 남기는 이벤트나 테이블이 존재하지 않기 때문이다(추측 금지 원칙에 따라 실제 확인). 열람 기반 스트릭을 원하면 `content` 모듈에 열람 이벤트 발행을 먼저 추가하는 별도 후속 작업이 필요하다 — 아래 "리스크/후속" 참조.

**notification-svc (신규 서비스, 신규 테이블 3개)**

```sql
CREATE TABLE device_token (
  id            BIGSERIAL PRIMARY KEY,
  user_id       BIGINT NOT NULL,
  token         VARCHAR(255) NOT NULL,
  platform      VARCHAR(16) NOT NULL,        -- ANDROID|IOS
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_device_token_user_token ON device_token (user_id, token);

CREATE TABLE user_notification_prefs (
  user_id                    BIGINT PRIMARY KEY,
  timezone                   VARCHAR(64) NOT NULL DEFAULT 'Asia/Seoul',  -- IANA tz (예: Asia/Seoul)
  preferred_time_slot        VARCHAR(5)  NOT NULL DEFAULT '19:00',       -- HH:mm, 클라이언트 로컬시각 기준 입력
  reminder_enabled           BOOLEAN NOT NULL DEFAULT true,
  weekly_report_email_enabled BOOLEAN NOT NULL DEFAULT true,
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

**설계 트레이드오프 — timezone 소유권**: `timezone`은 원칙적으로 사용자 프로필 속성이라 platform-svc(신원 서비스)가 소유하는 편이 DDD 상 맞다. 하지만 이번 스코프에서 처음 도입되는 필드이고 오직 알림 스케줄링에만 쓰이므로, platform-svc까지 건드리는 대신 **notification-svc가 소유**하기로 결정했다(범위를 5개 서비스로 넓히지 않기 위한 의도적 타협). learning-svc는 시간대 스캔 배치 때 `GET /notifications/internal/users/{id}/prefs`(bulk 조회 지원) 내부 API로 timezone을 조회한다. 사용자가 timezone을 바꿀 곳이 마땅치 않다는 문제가 남는데, 클라이언트가 선호시간대를 설정할 때 기기 로컬 IANA tz(`Intl.DateTimeFormat` / Flutter 등가 API)를 함께 전송해 자동 갱신하는 방식으로 별도 UI 없이 해결한다.

## 이벤트 계약 (devpath-shared, `ai.devpath.shared.event`)

기존 규칙(`eventType`은 `<도메인>.<엔티티>.<동작>` 소문자 점 표기, `DomainEvent` 구현, `eventId`/`occurredAt` 공통 필드) 그대로 따른다.

```java
public record StreakReachedEvent(
    UUID eventId, Instant occurredAt, long userId, int days
) implements DomainEvent {
  public static final String EVENT_TYPE = "progress.streak.reached";
}

public record UserStagnatedEvent(
    UUID eventId, Instant occurredAt, long userId, Instant lastActiveAt, int daysInactive
) implements DomainEvent {
  public static final String EVENT_TYPE = "progress.user.stagnated";
}

public record WeeklyReportGeneratedEvent(
    UUID eventId, Instant occurredAt, long userId, LocalDate weekOf,
    int streakDays, int progressPercent, List<String> badgesEarnedThisWeek, String nextTaskTitle
) implements DomainEvent {
  public static final String EVENT_TYPE = "progress.report.generated";
}
```

`StreakReachedEvent`는 매일 발행하지 않고 **마일스톤 도달 시에만**(7/14/30/60/100일 등 상수 목록) 발행한다 — community-svc는 `days == 30`일 때만 반응해 COMMUNITY 배지를 수여한다.

## 컴포넌트별 설계

**learning-svc — `progress` 모듈(신규)**
- `StreakRolloverScheduler`(`@Scheduled(cron="0 0 * * * *")`, 매시간 정각): notification-svc의 `timezone` bulk 조회 → 현재 UTC 시각이 로컬 자정(00:00~00:59)에 해당하는 유저만 대상으로 `StreakRolloverService.rollover(userId, localDate)` 호출.
  - 어제 활동 있음 → `current_days += 1`, `longest_days = max(longest_days, current_days)`, `last_active_date = 어제`. 마일스톤 도달 시 `StreakReachedEvent` 발행.
  - 어제 활동 없음 → `current_days = 0`. `last_active_date` 기준 미활동 일수가 정확히 3일째 되는 시점에 `UserStagnatedEvent` 발행(하루 지연 없이 정확히 1회만 — 재발행 방지 플래그 필요, 아래 리스크 참조).
- `WeeklyReportScheduler`(`@Scheduled(cron="0 0 20 * * SUN")`, 매주 일 20:00 KST): 전체 유저 순회 → 이번주 진척도(`LearningPathQueryService`) + `user_streak` + community-svc 배지 API(동기 REST, 배치 컨텍스트라 지연 허용) 조합해 `WeeklyReportGeneratedEvent` 발행.
- `DashboardService` 수정: `streakDays` 하드코딩 0 제거 → `user_streak` 조회로 교체. `badges` 하드코딩 문자열 제거 → community-svc 배지 API 연동(이번 빌드에서 함께 해소).

**notification-svc(신규 서비스, `devpath-svc-template` 기반 스캐폴딩)**
- `DeviceController`: `POST /notifications/devices`(등록, AUTHENTICATED), `DELETE /notifications/devices/{deviceId}`(삭제, OWNER) — API 명세서 그대로.
- `PrefsController`: `GET/PUT /notifications/prefs/me`(선호시간대·timezone·리마인더 on/off), 내부용 `GET /notifications/internal/users/{id}/prefs`(bulk, learning-svc 전용, 서비스 간 인증은 기존 서비스 간 호출 관례 재사용).
- `StagnationConsumer`(Kafka `progress.user.stagnated` 구독) → ai-svc `POST /ai/re-engagement` 동기 호출(실패 시 폴백 문구) → 대상 유저 전체 `device_token`에 FCM 푸시.
- `WeeklyReportConsumer`(Kafka `progress.report.generated` 구독) → `weekly_report` 저장 → `weekly_report_email_enabled=true`면 `EmailSender`로 이메일 발송 → FCM으로 "리포트 도착" 푸시.
- `PreferredTimeReminderScheduler`(`@Scheduled(fixedDelay=600000)`, 10분 주기): `user_notification_prefs`에서 현재 UTC 시각을 각 유저 timezone으로 환산했을 때 `preferred_time_slot`이 포함된 유저만 골라 일일 리마인더 푸시(고정 문구, AI 아님).
- `EmailSender`(interface) — `SmtpEmailSender implements EmailSender`(`spring-boot-starter-mail`, `JavaMailSender`, SMTP 호스트/계정은 환경변수) / `MockEmailSender`(test·local 프로파일).

**ai-svc — `retention` 모듈(신규)**
- `ReEngagementController`: `POST /ai/re-engagement` — request `{userId, lastActiveAt, daysInactive, currentLearningPathSummary}`, response `{message: String}`.
- `ReEngagementSuggestionClient`(interface) — `ClaudeReEngagementClient`(기존 `ClaudeAiReviewClient`/`ClaudeMentorClient`와 동일하게 `AnthropicClient` 사용, 모델 기본값 `claude-sonnet-4-6`, 학습경로 컨텍스트를 프롬프트에 포함) / `OllamaReEngagementClient` / `MockReEngagementClient`(고정 문구 반환, 테스트·로컬 및 Claude 호출 실패 시 폴백 공용).

**community-svc — 기존 `badge` 모듈에 컨슈머만 추가**
- `StreakReachedConsumer`(Kafka `progress.streak.reached` 구독) → `days == 30`이면 기존 `BadgeService`(Build 2에서 구현됨)로 COMMUNITY 배지 수여. 신규 배지 로직 없음, 트리거만 추가.

**gateway**
- `application.yml`에 라우트 추가: `Path=/notifications/**` → `NOTIFICATION_URI:http://localhost:8088`(포트는 기존 8081~8087 다음 순번).

## 스케줄러 설계 (TZ 인식이 핵심 난제)

"매일 자정 전체 유저 일괄 롤오버"는 틀린 설계다 — 유저마다 로컬 자정 시각이 다르므로 서버가 한 번에 처리하면 어떤 유저는 실제 로컬 자정보다 몇 시간 빠르거나 늦게 스트릭이 갱신된다. 대신 **시간대 윈도우 스캔** 패턴을 사용한다: learning-svc는 매시간 정각에 "지금이 로컬 자정인 timezone대"에 속한 유저만 골라 롤오버하고, notification-svc는 10분 주기로 "지금이 선호시간대에 도달한" 유저만 골라 리마인더를 보낸다. 두 스케줄러 모두 기존 `OutboxRelayScheduler`(`@Scheduled(fixedDelay=...)`) 스타일을 그대로 재사용한다. Kafka 이벤트 컨슈머(정체탐지/마일스톤/주간리포트) 3종은 스케줄러가 아니라 즉시 반응형이다.

## 에러 처리

- Kafka 컨슈머 처리 실패 → Spring Kafka 기본 재시도(지수 백오프) 후 최종 실패 시 DLQ 토픽 이동 + 로그.
- ai-svc 호출 실패(재참여 문구 생성 실패) → 전체 알림이 막히면 안 되므로 **고정 폴백 문구로 그레이스풀 디그레이드**(예: "오랜만이에요! 다시 학습을 시작해볼까요?") 후 정상 발송 계속.
- 이메일(SMTP) 발송 실패 → 재시도 큐 처리, 반복 실패 시 다음 주기로 넘김(기존 outbox relay의 "실패 시 skip, 다음 주기 재시도" 철학과 동일).
- FCM 토큰 만료/무효 → 발송 실패 응답 코드 확인 후 해당 `device_token` 삭제(다음 발송에서 제외).

## 테스트 전략 (TDD, 각 서비스 CLAUDE.md 절대조건 2 적용)

- 단위: 스트릭 TZ 경계값(자정 근처 활동, DST 없는 한국 기준이나 해외 유저 대비 일반 TZ 로직 검증), 정체탐지 판정 로직(정확히 3일째에만 1회 발행 — 재발행 방지).
- 통합: Kafka 발행-소비(기존 outbox 임베디드 카프카 테스트 패턴 재사용), ai-svc 신규 엔드포인트는 `MockReEngagementClient` 기반 계약 테스트, notification-svc는 `MockEmailSender`로 발송 로직 검증.
- 경계값: 일일 배치가 "정확히 30일째"에만 `StreakReachedEvent`를 발행하는지(29일·31일에는 미발행), 주간 리포트가 정확히 일요일 20:00에만 트리거되는지.

## 빌드 분해 (제안)

- **Build 1**: notification-svc 신규 서비스 스캐폴딩 + `device_token` 등록/삭제 API + gateway 라우트. (모바일이 이미 기다리고 있는 것부터 살림 — 즉시 가치)
- **Build 2**: learning-svc 스트릭 계산(TZ 롤오버) + 대시보드 하드코딩 제거 + `StreakReachedEvent` 발행 + community-svc 컨슈머(COMMUNITY 배지).
- **Build 3**: notification-svc 선호시간대 prefs API + 일일 리마인더 스케줄러(Build 1 인프라 위에서 콘텐츠만 추가).
- **Build 4**: 정체 탐지(learning-svc) + ai-svc `/ai/re-engagement` + notification-svc 구독·푸시.
- **Build 5**: 주간 리포트(learning-svc 집계 + community-svc 배지 enrich) + notification-svc 이메일 발송 + 이력 테이블.

## 리스크 / 후속

- 정체 탐지 "정확히 3일째 1회만 발행" 조건은 배치가 시간 단위로 도는 특성상 중복 발행 위험이 있다 — `user_stagnation_notified_at` 같은 플래그 또는 `daysInactive == 3` 정확 일치 체크로 방지(구현 계획 단계에서 확정).
- timezone을 notification-svc가 임시 소유하는 것은 후속 platform-svc 통합 시 데이터 이관이 필요하다.
- 주간 리포트 이메일은 SMTP 계정/발신 도메인이 아직 운영 인프라에 없다 — devpath-gitops에 신규 secret/설정 추가가 실제 배포 전 필요(이번 스펙은 애플리케이션 코드 설계까지만, 운영 배포 설정은 후속).
- community-svc 배지 enrich를 위한 학습-svc→community-svc 동기 REST 호출은 배치 컨텍스트라 허용했지만, 유저 수가 많아지면 N+1 호출 문제 — 후속으로 bulk 조회 API 필요.
- 콘텐츠 열람은 이번 빌드의 스트릭 신호에서 제외했다(위 데이터 모델 절 참조) — `content` 모듈에 열람 이벤트(예: `ContentViewedEvent` 또는 최소한 열람 타임스탬프 테이블)를 먼저 추가해야 포함 가능. 단순 태스크 완료·샌드박스 제출이 없는 "읽기만 하는" 학습 패턴의 유저는 이번 빌드에서 스트릭이 끊길 수 있음.
