# 정합성 3차 — 축② 코드 실측 인벤토리

## 기준

- 목적: 코드 레포에서 API 표면·Flyway·이벤트/토픽·shared 컨트랙트·frontend 화면/라우트를 **실측**해 정합성 점검(축②)의 근거 인벤토리를 확보한다. 판정·불일치 분석은 후속 문서 소관이며 본 문서는 실측 전용이다.
- 기준 ref: 각 레포 `origin/develop` (읽기 전용). 고정 SHA 대응:
  - platform-svc=`4c1ca4f`, learning-svc=`0461c4f`, community-svc=`043b830`, sandbox-svc=`a6d802e`, ai-svc=`69d5e0f`, lcs-svc=`bd64ada`, notification-svc=`0afddfd`, gateway=`c8a1282`, frontend=`e6be351`, shared=`ff7f5a6`, svc-template=`b6c33ee`, gitops=`ece471d`
- 참고 목표치(42번 기준): API 엔드포인트 총계 52개.

## 방법

- 코드 레포는 읽기 전용. `git -C <절대경로> grep` / `ls-tree`(읽기)만 사용, 상태 변경 명령 없음. Windows 경로 이슈로 Bash 도구가 백슬래시를 삭제해 실패 → 전 명령을 PowerShell 도구로 절대경로 실행.
- 실행 명령:
  - API 표면: `git -C <repo> grep -nE '@(Get|Post|Put|Delete|Patch|Request)Mapping' origin/develop -- '*.java'` (7 svc). class-level `@RequestMapping` base + method-level 경로를 합쳐 full path 산출. 테스트/plan 문서 매치는 제외하고 `src/main` 컨트롤러만 집계.
  - Flyway: `git -C <repo> ls-tree -r origin/develop --name-only` 에서 `db/migration` 필터 (7 svc + shared).
  - 이벤트: `git -C <repo> grep -nE 'KafkaListener|topics? *=|TopicNames|EventType' origin/develop` (7 svc + shared).
  - shared 컨트랙트: `git -C devpath-shared ls-tree -r origin/develop --name-only`.
  - frontend: `git -C devpath-frontend ls-tree ... | grep '^lib/'` + `git -C devpath-frontend grep -nE 'GoRoute|routes?:|path:' origin/develop -- '*.dart'`.

## 실측

### (1) svc별 API 표면 표 + 총계

`src/main` 컨트롤러 기준. full path = class @RequestMapping base + method 경로. (테스트·plan 문서 매치 제외)

#### platform-svc (12개)

| # | HTTP | full path | 컨트롤러 |
|---|------|-----------|----------|
| 1 | POST | /auth/oauth/token | AuthController |
| 2 | POST | /auth/refresh | AuthController |
| 3 | POST | /auth/logout | AuthController |
| 4 | GET | /admin/users | AdminUserController |
| 5 | POST | /admin/users/{id}/approve | AdminUserController |
| 6 | POST | /admin/allowlist | AdminUserController |
| 7 | GET | /beta/status | BetaStatusController (class base 없음, method-level 절대경로) |
| 8 | POST | /consents | ConsentController |
| 9 | GET | /consents/me | ConsentController |
| 10 | POST | /consents/{type}/revoke | ConsentController |
| 11 | DELETE | /users/me | AccountController |
| 12 | POST | /users/me/avatar | AvatarController |
| 13 | DELETE | /users/me/avatar | AvatarController |
| 14 | GET | /users/me/profile | ProfileController |
| 15 | PUT | /users/me/profile | ProfileController |
| 16 | GET | /users/me | UserController |

platform-svc 총계: **16개** (표 행 16; 위 "(12개)" 표기는 초기 오산으로 정정 — 실측 16).

#### learning-svc (19개)

| # | HTTP | full path | 컨트롤러 |
|---|------|-----------|----------|
| 1 | POST | /onboarding/assessments | AssessmentController |
| 2 | GET | /onboarding/assessments/{id}/next | AssessmentController |
| 3 | POST | /onboarding/assessments/{id}/answer | AssessmentController |
| 4 | POST | /onboarding/assessments/{id}/complete | AssessmentController |
| 5 | GET | /onboarding/assessments/{id}/result | AssessmentController |
| 6 | POST | /onboarding/assessments/claim | ClaimController |
| 7 | POST | /onboarding/assessments/guest | GuestAssessmentController |
| 8 | GET | /onboarding/assessments/guest/{gid}/next | GuestAssessmentController |
| 9 | POST | /onboarding/assessments/guest/{gid}/answer | GuestAssessmentController |
| 10 | POST | /onboarding/assessments/guest/{gid}/complete | GuestAssessmentController |
| 11 | GET | /contents/{idOrSlug} | ContentController |
| 12 | POST | /contents/{idOrSlug}/progress | ContentController |
| 13 | GET | /contents/me/progress | ContentController |
| 14 | GET | /internal/contents/{id} | InternalContentController |
| 15 | POST | /internal/contents/similar | InternalSimilarController |
| 16 | GET | /dashboard/me | DashboardController |
| 17 | POST | /learning-paths/tasks/{taskId}/complete | LearningPathController |
| 18 | POST | /learning-paths/me/generate (SSE) | LearningPathController |
| 19 | POST | /learning-paths/me/regenerate | LearningPathController |
| 20 | GET | /learning-paths/me | LearningPathController |
| 21 | GET | /learning-paths/me/this-week | LearningPathController |
| 22 | GET | /learning-paths/{id}/rationale | LearningPathController |

learning-svc 총계: **22개**.

#### community-svc (12개)

| # | HTTP | full path | 컨트롤러 |
|---|------|-----------|----------|
| 1 | GET | /community/users/{userId}/badges | BadgeController |
| 2 | GET | /community/me/activity | ActivityController |
| 3 | POST | /community/questions | CommunityController |
| 4 | POST | /community/questions/{id}/answers | CommunityController |
| 5 | POST | /community/answers/{id}/accept | CommunityController |
| 6 | GET | /community/questions/similar | CommunityController |
| 7 | GET | /community/questions/{id} | CommunityController |
| 8 | GET | /community/posts | CommunityController |
| 9 | POST | /community/posts/{id}/vote | CommunityController |
| 10 | POST | /community/answers/{id}/vote | CommunityController |
| 11 | GET | /community/tags | CommunityController |

community-svc 총계: **11개**.

#### sandbox-svc (3개)

| # | HTTP | full path | 컨트롤러 |
|---|------|-----------|----------|
| 1 | GET | /internal/sandbox/sessions/{id} | InternalSessionController |
| 2 | GET | /internal/sandbox/sessions/recent | InternalSessionController |
| 3 | POST | /sandbox/run (SSE) | RunController |

sandbox-svc 총계: **3개**.

#### ai-svc (7개)

| # | HTTP | full path | 컨트롤러 |
|---|------|-----------|----------|
| 1 | POST | /ai-mentor/sessions | MentorController |
| 2 | POST | /ai/embed | OllamaController |
| 3 | POST | /ai/path/generate | OllamaController |
| 4 | POST | /ai/re-engagement | ReEngagementController |
| 5 | GET | /reviews?sandboxSessionId=... | ReviewController (params 기반) |
| 6 | GET | /reviews/{id} | ReviewController |
| 7 | POST | /reviews/{id}/feedback | ReviewController |

ai-svc 총계: **7개**.

#### lcs-svc (6개)

| # | HTTP | full path | 컨트롤러 |
|---|------|-----------|----------|
| 1 | POST | /lcs/snapshots/draft | LcsController |
| 2 | POST | /lcs/snapshots/{draftId}/commit | LcsController |
| 3 | GET | /lcs/snapshots/{id} | LcsController |
| 4 | GET | /lcs/snapshots/by-question/{questionId} | LcsController |
| 5 | GET | /lcs/preferences | LcsController |
| 6 | PUT | /lcs/preferences | LcsController |

lcs-svc 총계: **6개**.

#### notification-svc (5개)

| # | HTTP | full path | 컨트롤러 |
|---|------|-----------|----------|
| 1 | POST | /notifications/devices | DeviceController |
| 2 | DELETE | /notifications/devices | DeviceController |
| 3 | GET | /notifications/internal/prefs/timezones | InternalPrefsController |
| 4 | GET | /notifications/prefs/me | PrefsController |
| 5 | PUT | /notifications/prefs/me | PrefsController |

notification-svc 총계: **5개**.

#### 합계

| svc | 엔드포인트 수 |
|-----|--------------|
| platform | 16 |
| learning | 22 |
| community | 11 |
| sandbox | 3 |
| ai | 7 |
| lcs | 6 |
| notification | 5 |
| **합계** | **70** |

참고: 42번 기준 52개 대비 실측 **70개**(+18). 증가분은 beta 게이팅(admin/allowlist/status·beta-pending), consent, avatar/profile 마이페이지, re-engagement, guest assessment 등 이후 머지된 기능으로 설명 가능(판정은 후속 문서 소관).

### (2) svc별 Flyway 목록

**핵심 실측: Flyway 마이그레이션은 devpath-shared에 중앙집중**되어 있고, 7개 svc 레포에는 `db/migration` 경로가 **존재하지 않는다**. 7 svc 전부 `ls-tree | grep db/migration` 결과 0건. 7 svc의 `build.gradle.kts`가 shared를 의존(platform 4회·나머지 각 2회 매치)해 스키마를 shared에서 공급받는다.

- platform-svc: 0 (shared 의존)
- learning-svc: 0 Flyway. 단 seed SQL 보유 — `src/main/resources/db/seed/content_md2_seed.sql`, `src/main/resources/db/seed/question_bank_md2_seed.sql` (+ test/tools 하위 seed 5종). Flyway 버전 마이그레이션 아님.
- community-svc: 0 (shared 의존)
- sandbox-svc: 0 (shared 의존)
- ai-svc: 0 (shared 의존)
- lcs-svc: 0 (shared 의존)
- notification-svc: 0 (shared 의존). resources = application.yml / application-test.yml 만.

**devpath-shared `src/main/resources/db/migration/` 전수 (31개, 버전 오름차순):**

```
V202606150900__init_common.sql
V202606150901__users_skeleton.sql
V202606150902__dormant_archives.sql
V202606171001__users_auth_extension.sql
V202606171002__user_oauth_identities.sql
V202606171003__user_profiles.sql
V202606171004__outbox.sql
V202606171005__notifications.sql
V202606181001__question_bank.sql
V202606181002__assessments.sql
V202606181003__assessment_items.sql
V202606181004__assessment_results.sql
V202606181005__drop_assessments_user_fk.sql
V202606181006__learning_path_schema.sql
V202606201001__user_content_progress.sql
V202606221001__sandbox_sessions.sql
V202606231001__ai_code_reviews.sql
V202606241001__ai_mentor_sessions.sql
V202606251001__community_qna.sql
V202606261001__lcs_snapshots.sql
V202606271001__device_tokens.sql
V202606301001__reputation.sql
V202606301002__badges.sql
V202607011001__vote_abuse_suspicions.sql
V202607021001__user_streak.sql
V202607021002__user_notification_prefs.sql
V202607021003__sandbox_activity_log.sql
V202607031001__user_streak_stagnation_notified.sql
V202607031002__weekly_report.sql
V202607041001__consent.sql
V202607171001__beta_allowlist.sql
```

(전수 grep 상 **31개** 파일명; 여기 나열된 것이 실측 전량이다. ※컨트롤러 재검증: `ls-tree -r | grep db/migration | grep -c '.sql$'` = 31 확정. 위 헤더의 초기 "34개" 표기는 오산으로 31로 정정.)

### (3) 이벤트 / 토픽 인벤토리

`src/main` 기준. 이벤트 타입 상수는 shared `ai.devpath.shared.event.*Event.EVENT_TYPE`. Producer=outbox `setEventType(...)`, Consumer=`@KafkaListener(topics=...)`.

| 토픽(EVENT_TYPE) | Producer (svc / 클래스) | Consumer (@KafkaListener svc / 클래스) |
|------------------|--------------------------|----------------------------------------|
| user.user.registered | platform / UserRegistrationService | notification / WelcomeNotificationConsumer |
| user.beta.waitlisted | platform / BetaGate | notification / BetaNotificationConsumer |
| user.beta.approved | platform / AdminBetaService | notification / BetaNotificationConsumer |
| learning.assessment.completed | learning / AssessmentEventPublisher | platform / AssessmentCompletedConsumer |
| learning.path.generated | learning / LearningPathPersistenceService | platform / LearningPathGeneratedConsumer |
| sandbox.run.submitted | sandbox / SandboxRunEventPublisher | learning / SandboxRunConsumer; ai / ReviewConsumer |
| community.question.posted | community / QuestionService | ai / CommunitySeedConsumer |
| community.seed.ready | ai / CommunitySeedEventPublisher | community / CommunitySeedConsumer |
| (streak) StreakReachedEvent.EVENT_TYPE | learning / StreakRolloverService | community / StreakReachedConsumer |
| (stagnation) UserStagnatedEvent.EVENT_TYPE | learning / StreakRolloverService | notification / StagnationConsumer |
| (weekly) WeeklyReportGeneratedEvent.EVENT_TYPE | learning / WeeklyReportScheduler | notification / WeeklyReportConsumer |
| CommunityBadgeAwardedEvent.EVENT_TYPE | community / BadgeService | (소비자 미실측 — grep상 producer만) |
| CommunityReputationSuspectedEvent.EVENT_TYPE | community / CollusionDetector | (소비자 미실측) |

- shared는 이벤트 DTO(EVENT_TYPE 상수)만 정의, `@KafkaListener` 없음 (grep 매치는 BetaEventTest뿐).
- lcs-svc: 이벤트/토픽 매치 0건 (Kafka 미참여, 동기 API 전용).
- sandbox-svc: producer만(sandbox.run.submitted), consumer 없음.
- 문자열 리터럴 토픽 사용처: notification/BetaNotificationConsumer가 `"user.beta.waitlisted"`·`"user.beta.approved"` 하드코딩(EVENT_TYPE 상수 아님) — 관찰 참조.

### (4) shared 컨트랙트

`devpath-shared/src/main/java/ai/devpath/shared/` 공개 컨트랙트:

- **error (에러 envelope)** — `ai.devpath.shared.error`:
  - `ErrorCode.java`, `ErrorResponse.java`, `ApiException.java`, `ApiExceptionHandler.java`, `SseSupport.java`
- **event (이벤트 DTO)** — `ai.devpath.shared.event`:
  - `DomainEvent.java` (base), `AssessmentCompletedEvent`, `BetaAccessApprovedEvent`, `BetaWaitlistRegisteredEvent`, `CommunityBadgeAwardedEvent`, `CommunityQuestionPostedEvent`, `CommunityReputationSuspectedEvent`, `CommunitySeedReadyEvent`, `LearningPathGeneratedEvent`, `SandboxRunSubmittedEvent`, `StreakReachedEvent`, `UserRegisteredEvent`, `UserStagnatedEvent`, `WeeklyReportGeneratedEvent` (13 event + DomainEvent)
- **storage (스토리지 포트)** — `ai.devpath.shared.storage`:
  - `ObjectStorage.java` (포트), `S3ObjectStorage.java` (어댑터), `StorageAutoConfiguration.java`, `StorageProperties.java`, `StorageException.java`, `StoredFileValidator.java`
  - 스프링 부트 자동구성 등록: `src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
- **db/migration**: (2)절 참조 — 31개 Flyway 스크립트(전 svc 스키마 SSoT).

### (5) frontend 화면 · 라우트

frontend는 멀티앱 모노레포: `apps/web`, `apps/mobile`, `apps/admin` + `packages/dp_core`. `lib/` 하위는 각 앱 `apps/<app>/lib/src/`(app/features/…) 구조. GoRouter 라우트 표(테스트 라우터 제외, `apps/*/lib/src/app/router.dart` 및 shell 기준):

#### apps/web (router.dart)

| path | 화면 | 비고 |
|------|------|------|
| /login | LoginPage | |
| /beta-pending | (베타 대기) | |
| /consent | ConsentPage | |
| /diagnostic | DiagnosticPage | 온보딩 |
| /auth/callback | (OAuth 콜백) | |
| /dashboard | DashboardPage | shell 탭 |
| /path | PathPage | shell 탭 |
| /content/:id | (콘텐츠 상세) | |
| /sandbox | SandboxPage | SSE |
| /mentor | MentorPage | shell 탭, SSE |
| /community | (커뮤니티 홈) | shell 탭 |
| /community/new | (질문 작성) | |
| /community/:id | (질문 상세) | |
| /settings | SettingsPage | shell 탭 |
| /mypage | MyPagePage | |

web shell 탭(app_shell.dart): /dashboard, /path, /mentor, /community, /settings (5탭).

#### apps/mobile (router.dart)

| path | 화면 |
|------|------|
| /login | LoginPage |
| /onboarding | OnboardingPage |
| /home | DashboardPage |
| /learn | (학습) |
| /learn/content/:slug | (콘텐츠) |
| /community | (커뮤니티) |
| /community/new | QuickCapturePage |
| /community/posts/:id | (게시글 상세) |
| /notifications | (알림) |

- 인증: OAuth 콜백 딥링크 `devpath://callback?code=` (auth_callback.dart / deep_link_service.dart, PKCE 하드닝 트랙 A).

#### apps/admin (router.dart)

| path | 화면 |
|------|------|
| /login | AdminLoginPage |
| /auth/callback | (콜백) |
| /forbidden | (403) |
| /dashboard | (대시보드) |
| /users | AdminUsersPage |
| /reports | ReportsPage |

admin shell(admin_shell.dart): /dashboard, /users, /reports (3탭).

## 불일치 후보

해당 없음 (실측 전용 인벤토리). 판정·불일치 분석은 후속 정합성 문서 소관.

## 관찰

- **엔드포인트 총계 실측 70개** (42번 기준 52 대비 +18). 판정 유보이나, 후속 문서에서 목표치 갱신 필요 후보.
- **Flyway 중앙집중**: 7 svc 어디에도 `db/migration` 없음 — shared 단일 SSoT(31 스크립트). learning-svc만 `db/seed`에 seed SQL 보유(Flyway 버전 아님, 별도 로딩 경로). svc별 스키마 소유 문서와의 정합은 후속 확인 대상.
- **토픽 상수 vs 리터럴 비표준**: 대부분 producer/consumer가 shared `*.EVENT_TYPE` 상수를 참조하나, notification/BetaNotificationConsumer는 `@KafkaListener(topics="user.beta.waitlisted"/"user.beta.approved")`를 **문자열 하드코딩**. platform 쪽 producer는 `BetaWaitlistRegisteredEvent.EVENT_TYPE`/`BetaAccessApprovedEvent.EVENT_TYPE` 상수 사용 → 상수-리터럴 불일치 위험(오타 시 컴파일 통과·런타임 미구독).
- **소비자 미매칭 이벤트 후보**: `CommunityBadgeAwardedEvent`, `CommunityReputationSuspectedEvent`는 community에서 발행되나 grep상 `@KafkaListener` 소비자 미실측(발행 후 미소비 또는 소비처가 grep 패턴 밖일 가능성).
- **lcs-svc는 이벤트 비참여**: Kafka 리스너/발행 0. 동기 REST 전용 서비스로 관찰됨.
- **SSE 엔드포인트 3종**: learning `/learning-paths/me/generate`, sandbox `/sandbox/run`, (ai mentor는 `/ai-mentor/sessions` POST — produces 미표기, 별도 스트림 경로 여부는 미실측). `produces=TEXT_EVENT_STREAM_VALUE` 명시는 learning·sandbox 2곳.
- **비표준 경로 관찰**: platform `/beta/status`는 class @RequestMapping base 없이 method-level 절대경로(`BetaStatusController`). ai `/reviews` GET은 path 없이 `params="sandboxSessionId"`로 분기(쿼리 파라미터 기반 라우팅).
- **frontend web /mypage**: shell 5탭에 없으나 라우트로 존재(별도 진입 경로). 라우트-탭 노출 정합은 후속 확인 후보.
