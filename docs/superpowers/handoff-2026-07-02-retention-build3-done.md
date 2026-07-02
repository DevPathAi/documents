# 핸드오프 — 참여촉진배치 Build 3(선호시간대 prefs API + 일일 리마인더) 완료 / 다음 = Build 4(정체 탐지 + AI 재참여) (2026-07-02)

> 다음 세션 이관용. **참여촉진배치 Build 3 구현·검증 완료, PR 오픈**(devpath-notification-svc **PR #6** → develop, CI green). 계획서 documents **PR #61**. Build 1(device/inbox 이관)·Build 2(스트릭 계산+대시보드+prefs 스키마·내부 timezone API) 위에 **사용자 대면 알림 설정 API**와 **선호시간대 일일 리마인더 스케줄러**를 올렸다. 직전 핸드오프 [[handoff-2026-07-01-antiabuse-build3-done]]가 지목한 "다음=스트릭·배치" 중 스트릭(Build 2)·선호시간대 리마인더(Build 3)까지 진행됨. **notification-svc 단일 레포, shared/gateway 변경 없음**(Build 2 스키마 재사용, `/notifications/**` 라우트는 Build 1에 이미 존재). 실행 = **Subagent-Driven Development**(태스크별 implementer + 컨트롤러 직접 검증 + 최종 opus 전체 리뷰). 환경 = **Windows + Bash 도구, 메인 직접 진행 + 서브에이전트 파일 리포트.**

## 1. 종착점 — Build 3 ✅

승인 계획: [plans/2026-07-02-md3-retention-batch-build3.md](plans/2026-07-02-md3-retention-batch-build3.md)(5 Task, TDD) · 스펙 [specs/2026-07-01-md3-retention-batch-design.md](specs/2026-07-01-md3-retention-batch-design.md) §Build 3. 권위 출처 [17_스케줄](../../17_스케줄.md) §평판 기초 "선호 시간대 푸시" · [07_요구사항_정의서](../../07_요구사항_정의서.md) FR-PRO-004/005.

| Task | 산출물 | 커밋 |
|---|---|---|
| **1 — prefs 도메인** | `UserNotificationPrefs` setter 보강 + `UserNotificationPrefsService`(`getOrDefault`/`upsert`) | `be45035` |
| **2 — 사용자 대면 API** | `GET/PUT /notifications/prefs/me` + `NotificationPrefsView`/`UpdateNotificationPrefsRequest`. IANA(`ZoneId.of`)·`HH:mm`(`LocalTime.parse`) 검증, JWT subject=userId, 미인증 401 | `75aefc2` |
| **3 — 전달 추상화** | `PushSender` 인터페이스 + `InboxPushSender`(inbox Notification 행 생성) | `688990a` |
| **4 — 리마인더** | `DailyReminderService`(TZ 윈도우 스캔 + inbox 기반 당일 1회 중복방지) + `PreferredTimeReminderScheduler`(`@Scheduled` 10분, `@ConditionalOnProperty`) + `@EnableScheduling` + repo 쿼리 2개 | `65085c7` |
| **5 — 문서** | README·CLAUDE.md 도메인 표(prefs·push·reminder) | `a366166`, `67e864a` |

- **핵심 설계 결정(veto 가능, 계획 Self-Review §2·PR #6 본문 명시):** 리마인더 "푸시" = **인앱 inbox 행**(`InboxPushSender`), 실제 **FCM 발송은 후속 연기**(Firebase 서비스계정 인프라 부재 — 스펙이 SMTP를 Build 5로 미룬 것과 동일 논리). `PushSender` 추상화로 국소화(스펙 `EmailSender` 패턴 미러링) → 후속 `FcmPushSender` drop-in.
- **스키마 변경 없음**: Build 2가 publish한 `user_notification_prefs`(전 컬럼) + `notifications` 재사용. shared·gateway 무변경.
- **리마인더 판정**: 유저 로컬 현재시각 ≥ 오늘 `preferred_time_slot` **AND** 오늘(유저 로컬 자정 기준) `DAILY_REMINDER` inbox 행 없음 → 전송. 스케줄러 실행 간격이 정렬 안 돼도 하루 정확히 1회, 선호시간 이후 최초 스캔에서 발송.

## 2. 검증 (2026-07-02)

- **로컬**: `./gradlew build` **28/28 GREEN**(0 failures). 실 Postgres(`devpath-local-postgres-1`, pgvector pg17, 5432) 기반 통합 테스트 포함 — `PrefsControllerIT`(5, GET 기본값/PUT 왕복/검증 400/미인증 401), `InternalPrefsControllerIT`(2), `WelcomeNotificationConsumerIT`(1) 전부 green. 신규 단위: `UserNotificationPrefsServiceTest`(4)·`InboxPushSenderTest`(1)·`DailyReminderServiceTest`(5, TZ 환산·미도달·당일중복·유저별tz·잘못된tz skip).
- **원격 CI**: PR #6 `build` **pass**(1m57s), `image` 잡은 PR에서 정상 skip.
- **`@EnableScheduling` 회귀 안전**: 스케줄러는 `@ConditionalOnProperty(devpath.reminder.scheduler-enabled, matchIfMissing=true)`, 테스트 프로파일에서 `false`로 미등록 → 기존 IT 회귀 0.
- **Subagent-Driven**: Task별 implementer(TDD, 파일 리포트) + 컨트롤러가 매 태스크 git diff/파일/커밋 범위 직접 검증 + 인접 레포 낯선 브랜치 스팟체크. **최종 전체 브랜치 리뷰(opus) "READY TO MERGE: YES"** — Critical 0·Important 0·Minor 5(전부 의도된 설계/스펙 범위 밖, 아래 §3).

## 3. 남은 작업 — 후속

- **Build 4(다음 진입점)**: 정체 탐지 + AI 재참여 제안. learning-svc `progress`에 `UserStagnatedEvent`(미활동 정확히 3일째 1회만, 재발행 방지) + ai-svc `retention` 모듈(`POST /ai/re-engagement`, Claude/Ollama/Mock 3중, 기존 review/mentor 패턴 재사용) + notification-svc `StagnationConsumer`(구독 → ai 동기 호출·실패 시 폴백 문구 → 푸시).
- **Build 5**: 주간 리포트(learning-svc 집계 `WeeklyReportGeneratedEvent` + community-svc 배지 enrich) + notification-svc `WeeklyReportConsumer`(→ `weekly_report` 저장 + SMTP 이메일 + 푸시). **SMTP 계정·발신 도메인은 devpath-gitops에 미존재 — 배포 전 별도 작업 필요.**
- **FCM 실발송(`FcmPushSender`)**: Firebase 서비스계정 인프라 필요. 추가 시 리마인더 당일-중복방지를 inbox 결합에서 분리(별도 `reminder_log` 또는 `user_notification_prefs.last_reminded_on`) 필요 — 계획 리스크 절에 문서화.
- **최종 리뷰 Minor(전부 non-blocking, 액션 불필요):** M1 DST spring-forward 갭 슬롯 스큐(연 1회·1시간 미만, 한국 DST 없음 → 스펙 Korea-first 범위 밖), M2 늦은 발화(선호시간 이후 최초 스캔=의도된 계약), M3 `weekly_report_email_enabled` 1빌드 선반영(기존 컬럼·full-replace PUT), M4 full-replace PUT(누락 필드 400), M5 `getOrDefault` 미저장 기본값(GET이 행 생성 안 함=의도).
- `findByReminderEnabledTrue` 전량 스캔은 유저 급증 시 TZ 버킷팅 최적화 후속 필요.

## 4. 환경/도구/게이트 (필수)

- **환경**: Windows 11 + Bash 도구. 백엔드 Java 21 · Spring Boot 4.0.7 · Gradle(Kotlin DSL). Jackson 3(`tools.jackson.databind.json.JsonMapper`). MockMvc autoconfigure는 Boot 4 경로 `org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc`.
- **로컬 인프라(테스트 필수)**: Postgres `localhost:5432/devpath`(`devpath`/`localdev`, docker `devpath-local-postgres-1`). 테스트는 `application-test.yml`의 `flyway.enabled: true`가 devpath-shared jar의 `classpath:db/migration`으로 스키마 생성 → notification-svc는 스키마 로컬 미소유.
- **Subagent-Driven(이 세션 확정 패턴)**: implementer/reviewer 모두 **결과를 지정 파일에 기록**하고 최종 응답은 상태 4줄만. **브랜치는 컨트롤러가 선생성**(서브에이전트에 브랜치 생성/전환 시키지 않음 — cwd 리셋 사고 예방), **모든 git/gradle에 `-C <절대경로>`**, **push·PR·머지는 컨트롤러만**(서브에이전트에 원격/머지 권한 주지 않음). 매 태스크 후 컨트롤러가 git/테스트 직접 재검증 + 인접 레포(특히 documents) 낯선 브랜치 스팟체크. 관련 [[devpath-windows-subagent-flakiness]]·[[devpath-subagent-merge-attempt-incident]].
- 브랜치 전략: 각 레포 `develop` 분기 → develop PR → 머지. main 직접 금지(release develop→main만). 서브에이전트 Scope Lock + 컨트롤러 직접 검증.

## 5. 레포 위생 / 열린 항목

- **이 세션 산출(머지 상태는 본 핸드오프 세션에서 갱신)**: notification-svc **PR #6**(코드+진행문서, develop, CI green) / documents **PR #61**(계획) / 본 핸드오프 PR. 정리 과정에서 Build 2 잔여 feature 브랜치들을 통합 브랜치(develop/main)로 원복.
- **여전히 열린(무관, 이전 세션 소관)**: `devpath-sandbox-svc #18`(CLAUDE.md 도메인 표 정합), `.github #6`(조직 프로필 정정) — 둘 다 OPEN, 이 세션에서 손대지 않음.

## 6. 다음 진입점

**Build 4 — 정체 탐지 + AI 재참여 제안**(스펙 §빌드 분해). 스펙의 핵심 아키텍처는 이미 승인됨 → 재브레인스토밍 없이 바로 writing-plans. 3개 레포(learning-svc 탐지·ai-svc 생성·notification-svc 발송)에 걸치므로, shared 이벤트(`UserStagnatedEvent`) → ai-svc → notification-svc 순서 의존성과 "정확히 3일째 1회만 발행" 재발행 방지(플래그/정확일치)를 계획 단계에서 확정할 것. Build 3의 `PushSender`를 `StagnationConsumer`도 재사용.

착수 전 [[devpath-handoffs-lag-verify-first]]대로 각 레포 git 재검증 + PR #6/#61/본 핸드오프 머지 여부부터 확인.

## 7. 관련 메모리

- [[devpath-retention-batch-design]](참여촉진배치 Build 1·2 머지·Build 3 PR — 설계 결정·후속 목록) · [[handoff-2026-07-01-antiabuse-build3-done]](직전 핸드오프) · [[devpath-handoffs-lag-verify-first]](문서 lag — 착수 전 git 검증) · [[devpath-windows-subagent-flakiness]] · [[devpath-subagent-merge-attempt-incident]]
- 대시보드: https://devpathai.github.io/workflow-dashboard/
