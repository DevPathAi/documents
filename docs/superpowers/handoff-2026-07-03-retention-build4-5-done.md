# 핸드오프 — 참여촉진배치 Build 4(정체탐지+AI재참여)·Build 5(주간리포트+이메일) 완료 / 참여촉진배치 전 5빌드 완결 (2026-07-03)

> 다음 세션 이관용. **참여촉진배치 Build 4·5 구현·develop 머지 완료 → Build 1~5 전부 완결.** 직전 핸드오프 [[handoff-2026-07-02-retention-build3-done]]가 지목한 "다음=Build 4"부터 마지막 Build 5까지 한 세션에서 완주. 스케줄 [17_스케줄](../../17_스케줄.md) §"평판 기초"의 **스트릭·주간 리포트 배치·3일 미접속 AI 제안·선호 시간대 푸시** 항목이 이로써 전부 완결됐다(스트릭=B2, 선호시간대=B3, 3일미접속=B4, 주간리포트=B5). 실행 = **Subagent-Driven Development**(태스크별 implementer + 컨트롤러 직접 검증 + 최종 opus 크로스레포 리뷰). 환경 = **Windows + Bash 도구, 서브에이전트 파일 리포트.** 관련 메모리 [[devpath-retention-batch-design]].

## 1. 종착점 — Build 4 ✅ (정체 탐지 + AI 재참여 제안 + 발송)

계획: [plans/2026-07-03-md3-retention-batch-build4.md](plans/2026-07-03-md3-retention-batch-build4.md). 스펙 [specs/2026-07-01-md3-retention-batch-design.md](specs/2026-07-01-md3-retention-batch-design.md) §Build 4.

| Task | 레포·PR | 산출물 |
|---|---|---|
| 1 | shared **#35**(main+publish, `61efe5c`) | `UserStagnatedEvent`(+`currentLearningPathSummary`) + `user_streak.stagnation_notified_at`(`V202607031001`) |
| 2 | ai-svc **#27**(`6150a1a`) | `retention` 모듈 `POST /ai/re-engagement`(review 패턴 미러, Mock/Claude) + **test Hikari cap=4** |
| 3 | learning-svc **#28**(`d116988`) | `StreakRolloverService` else 분기에 정체 판정 추가(`ActivePathSummaryReader` 경로요약 조립) |
| 4 | notification-svc **#7**(`e670d43`) | `StagnationConsumer` → ai-svc(`:8084`) RestClient(실패 시 폴백) → `PushSender` |

**흐름:** learning-svc 3일 미활동 감지 → `UserStagnatedEvent`(경로요약 포함) outbox 발행 → notification-svc `StagnationConsumer` 구독 → ai-svc `/ai/re-engagement` 호출(실패 시 폴백 문구) → 기존 `PushSender`(Build 3, inbox) 전달.

**착수 전 확정한 설계 결정 2건(사용자):** ① 재발행 방지 = `stagnation_notified_at` 컬럼(발행 시 세팅·재활성 시 리셋). ② `currentLearningPathSummary` = `UserStagnatedEvent` payload에 포함(스펙 이벤트↔ai요청 shape 모순 해소). **리뷰 IMPORTANT-1 반영(사용자 승인): 정체 판정 `== 3` → `>= 3`으로 완화**(마커가 중복 방지 → 롤오버 틱 놓쳐도 알림 누락 없음, day-4 첫관측 발화 테스트 추가). **스코프 축소(veto 가능):** Ollama provider·실제 FCM 멀티디바이스 발송 후속 연기.

## 2. 종착점 — Build 5 ✅ (주간 리포트 집계 + 이메일 발송)

계획: [plans/2026-07-03-md3-retention-batch-build5.md](plans/2026-07-03-md3-retention-batch-build5.md). 스펙 §Build 5.

| Task | 레포·PR | 산출물 |
|---|---|---|
| 1 | shared **#37**(main+publish, `58ce3f1`) | `WeeklyReportGeneratedEvent`(8필드) + `weekly_report` 테이블(`V202607031002`, UNIQUE user_id,week_of) |
| 2·3 | learning-svc **#29**(`aaf65a4`) | `CommunityBadgeClient.badgesOf`(awardedAt) + `WeeklyReportAggregator` + `WeeklyReportScheduler`(cron 일 20:00 KST, `@Profile("!test")`) |
| 4 | notification-svc **#8**(`ebccc9b`) | `spring-boot-starter-mail` + `WeeklyReport` 저장 + `EmailSender`(Mock/Smtp) + `WeeklyReportConsumer` |

**흐름:** learning-svc `WeeklyReportScheduler` 매주 일 20:00 KST 전체 활성 유저 순회 → `WeeklyReportAggregator`(스트릭+진척%+이번주 배지=최근 7일+다음과제) → `WeeklyReportGeneratedEvent` outbox → notification-svc `WeeklyReportConsumer` → `weekly_report` 저장(멱등 UNIQUE) → `weekly_report_email_enabled`면 `EmailSender` → `PushSender` "리포트 도착".

**결정(스펙·패턴 준수):** community-svc **무변경**(배지 API가 `awardedAt` 이미 반환 — learning-svc 클라이언트에 `badgesOf` 신규 메서드만, `badgeNamesOf`·`DashboardService` 무변경) / `EmailSender`=`MockEmailSender`(기본)+`SmtpEmailSender`(prod, `devpath.mail.provider=smtp`) — **실제 SMTP는 gitops 후속** / 배지 enrich N+1 후속(배치 컨텍스트 허용).

## 3. 검증 (2026-07-03)

- **Build 4**: shared FlywayMigrationTest 29/29·publish OK / ai-svc 전체 GREEN(CI, Hikari cap 적용 후 안정) / learning-svc 신규 3/3+회귀 3/3(CI, 재실행 1회 — 아래 §5 flaky) / notification-svc 단위 3/3+전체 31/31. 최종 opus 크로스레포 리뷰 **READY, Critical 0·Important 1(>=3 반영 완료)·Minor 4**.
- **Build 5**: shared event 1/1+FlywayMigrationTest 29/29·publish OK / learning-svc aggregator 1/1+전체 121/121 / notification-svc 단위 4/4+전체 35/35. 최종 opus 크로스레포 리뷰 **READY, Critical 0·Important 0·Minor 3**(M1·M2=save-before-side-effect 중복 푸시/이메일 희귀 엣지·기존 컨슈머와 일관·배치 허용, M3=SmtpEmailSender setTo 미설정·gitops 후속).
- 크로스레포 계약(이벤트 필드↔발행↔역직렬화↔ai요청/응답, outbox 토픽, 마이그레이션↔엔티티) 전부 소스 대조 일치. 각 PR CI green 후 머지.

## 4. 남은 작업 — 후속 (전부 비블로킹, 계획·메모리에 문서화)

- **실제 발송 인프라(gitops 필요)**: FCM 멀티디바이스 발송(현재 인앱 inbox 전달, `PushSender` 추상화로 `FcmPushSender` drop-in 대기) · SMTP 실발송(계정·발신도메인 + 수신자 이메일 platform-svc 연동, `SmtpEmailSender` 스텁 준비됨).
- **N+1 최적화**: 배지/timezone bulk 조회 API(현재 유저별 동기 REST, 배치 컨텍스트라 허용).
- **소비자 멱등 강화**: Kafka 재전달 시 중복 푸시/이메일 방지 — `WeeklyReportConsumer`/`StagnationConsumer`를 save-first 순서로(현재 side-effect-then-save, 기존 컨슈머와 일관). 전 컨슈머 일괄 적용 권장.
- **AI**: ai-svc retention `OllamaReEngagementClient`(현재 Mock+Claude) · kill-switch 500→503 코스메틱.
- **learning-svc 로컬 flaky**: `LearningPathEngineTest`(async-SSE `ConcurrentModificationException`)·`SandboxRunConsumerIT`(embedded-Kafka 타이밍)가 로컬/CI 비결정 실패(Build 4·5와 무관, 커넥션 이슈 아님). CI 재실행으로 통과 — 별도 하드닝감.

## 5. 환경/도구/게이트 (필수)

- **환경**: Windows 11 + Bash 도구. Java 21 · Spring Boot 4.0.7 · Gradle(Kotlin DSL). Jackson 3(`tools.jackson.databind.json.JsonMapper`).
- **로컬 인프라(테스트)**: Postgres `localhost:5432/devpath`(docker `devpath-local-postgres-1`). 테스트는 shared jar Flyway가 classpath로 스키마 구성(서비스는 `ddl-auto: validate`).
- **테스트 커넥션 고갈 방지**: 다수 @SpringBootTest 컨텍스트×Hikari 풀이 Postgres `max_connections` 초과 → "too many clients"(53300). 해결: 각 레포 `application-test.yml`에 `spring.datasource.hikari.maximum-pool-size` 하향(ai-svc=4 적용). 로컬 여유분으로 devpath-shared docker-compose `postgres`에 `max_connections=200`(PR #36) 적용. 상세 [[devpath-svc-test-context-connection-flake]].
- **cross-repo 릴리스 게이트**: shared는 develop 없음 → `feat/*`→`main` 직접 PR, **main push에서만 GitHub Packages publish**. 소비 서비스는 `./gradlew compileJava --refresh-dependencies`(jar **내용 grep**으로 새 클래스 확인).
- **Subagent-Driven(확정 패턴)**: implementer/reviewer 모두 **결과를 지정 파일에 기록**(반환 텍스트에 긴 본문 기대 금지 — 이번 세션에도 여러 서브에이전트가 최종 메시지 유실, 파일 리포트로 보존). **브랜치는 컨트롤러가 선생성**, 모든 git/gradle에 `-C <절대경로>`, **push·PR·머지·publish는 컨트롤러만**. 매 태스크 후 git/파일/테스트 직접 재검증 + 인접 레포 스팟체크. [[devpath-windows-subagent-flakiness]]·[[devpath-subagent-merge-attempt-incident]].
- 브랜치 전략: 각 레포 `develop` 분기 → develop PR → 머지. main 직접 금지(shared 릴리스 PR 제외).

## 6. 레포 위생 / 열린 항목

- **이 세션 산출(전부 머지)**: shared #35·#36·#37(main+publish) / ai-svc #27 / learning-svc #28·#29 / notification-svc #7·#8(develop) / documents #63·#64(계획)·본 핸드오프(develop). 머지 브랜치 정리 완료, 전 레포 develop/main 클린.
- **여전히 열린(이전 세션 소관, 미변경)**: `devpath-sandbox-svc #18`(CLAUDE.md 도메인 표 정합), `.github #6`(조직 프로필 정정) — 둘 다 OPEN.

## 7. 다음 진입점

**참여촉진배치는 완결.** 다음은 스케줄 **Tier-2(MD3)의 나머지** — 백엔드는 대부분 구현됐고 남은 건 **프론트 실API 전환**이 주력이다([17_스케줄](../../17_스케줄.md) §2·§0.1):
- #7 멘토·#8 커뮤니티·#9 LCS: 백엔드 구현됨 → 프론트 실API 전환(기본 `USE_MOCK=true` 해제) + moderation·검색·LCS sanitize 등 후속(TARGET).
- #10 모바일: 목데이터 8종 → 실API 전환 + 홈 대시보드(스트릭·진척률) + FCM.
- #11 랜딩: 검증 페이지 가동 → 장기 Jaspr 랜딩(`feat/p7-landing-jaspr`).
- **MD3 완료 기준**: 풀 골든패스 web 실동작 + 모바일 앱 + 랜딩 배포 + 3R 권역 IR.
- 리텐션 실발송(FCM/SMTP)·평판 고도화(Silver/Gold·레벨게이트 강제)는 각각 gitops/Tier-3(MD4).

착수 전 [[devpath-handoffs-lag-verify-first]]대로 각 레포 git 재검증(스케줄 §2 체크박스는 백엔드 완료 미반영으로 뒤처짐 — §0.1 스냅샷·[42_전체_정합성_점검_2차](../../42_전체_정합성_점검_2차.md)가 최신).

## 8. 관련 메모리

- [[devpath-retention-batch-design]](Build 1~5 완결·설계결정·후속) · [[handoff-2026-07-02-retention-build3-done]](직전) · [[devpath-svc-test-context-connection-flake]](테스트 커넥션 고갈) · [[devpath-handoffs-lag-verify-first]] · [[devpath-windows-subagent-flakiness]]
- 대시보드: https://devpathai.github.io/workflow-dashboard/
