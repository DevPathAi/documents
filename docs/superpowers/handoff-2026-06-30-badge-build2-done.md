# 핸드오프 — 평판 기초 Build 2(Bronze 배지 엔진) 완료 / 다음 = Build 3(sockpuppet·자기투표금지) (2026-06-30)

> 다음 세션 이관용. **평판 기초 Build 2(Bronze 배지 엔진) 구현·develop 머지 완료**(community-svc PR #15 / shared 스키마·이벤트 PR #31 main publish). spec+플랜(documents PR #51)은 develop 머지됨. Build 1(평판 엔진) 위에 **같은 트랜잭션에서 배지를 멱등 수여하는 엔진**을 올렸다(신호 있는 6종 트리거 결선, 카탈로그 9종 시드, `community.badge.awarded` outbox). 직전 핸드오프 [[handoff-2026-06-30-reputation-build1-done]]의 "다음=Build 2"를 본 문서가 잇는다. 남은 = **Build 3(sockpuppet·자기 글 투표 금지)** + 배지 3종 dormant·Silver/Gold·게이트 500/1000·스트릭/배치. 환경 = **Windows + Git Bash, 메인 직접 진행.** 실행은 **Subagent-Driven Development**로 완주.

## 1. 종착점 — 배지 Build 2 ✅

승인 spec/플랜: [specs/2026-06-30-md3-badge-engine-design.md](specs/2026-06-30-md3-badge-engine-design.md) · [plans/2026-06-30-md3-badge-engine-build2.md](plans/2026-06-30-md3-badge-engine-build2.md)(7 Task, TDD). 권위 출처 [20_커뮤니티_기능_설계서.md](../../20_커뮤니티_기능_설계서.md) §3.3·§8.

| Task | 산출물 | 근거 |
|---|---|---|
| **1 — shared 스키마+이벤트** | `V202606301002__badges.sql`(badges·user_badges + 9종 시드) + `CommunityBadgeAwardedEvent`(DomainEvent, `community.badge.awarded`) | shared `bd50b84` / PR #31 → **main publish** |
| **2 — 배지 도메인** | `ai.devpath.community.badge`: `BadgeCode`(9)·`Badge`/`UserBadge`(+복합키) + 리포지토리 | community-svc `119587c` |
| **3 — BadgeService** | `award(userId, code, sourceType, sourceId)` 멱등(`user_badges` PK)+ outbox 발행(단일 타임스탬프) | `8bf8507`·`ff3b7ae` |
| **4 — 작성 배지** | QuestionService→FIRST_QUESTION, AnswerService.add→FIRST_ANSWER | `89b2c49` |
| **5 — 투표 배지** | VoteService: STUDENT(글 순점수 +1)·TEACHER(답변 순점수 +1)·CRITIC(downvote 행사) | `c1c5f53` |
| **6 — 평판 배지** | PHILANTHROPIST(평판 15) — accept(답변·질문 작성자 둘 다)+votePost+voteAnswer | `10a03cc` |
| **7 — 조회 API** | `GET /community/users/{userId}/badges` (BadgeView/QueryService/Controller) | `fed233a` |
| 폴리시 | 최종리뷰 반영(RepPoints import·자기투표 주석·TEACHER 음성단언) | `8d4a8dc` |

- 아키텍처: `BadgeService.award`는 호출자(Question/Answer/Vote Service)의 `@Transactional`에 합류(Build 1 `ReputationService` 패턴). 멱등은 `user_badges` PK(app `existsBy…` 선검사 + DB PK 이중). 수여 시 기존 outbox 패턴으로 `CommunityBadgeAwardedEvent` 적재.
- **6종 트리거 결선**: FIRST_QUESTION·FIRST_ANSWER·STUDENT·TEACHER·CRITIC·PHILANTHROPIST. **3종 시드만**: FIRST_STEP(프로필=platform-svc)·EDITOR(글 편집 기능 부재)·COMMUNITY(30일 스트릭 부재) — 상위 기능 도입 시 트리거 결선.

## 2. 검증 (2026-06-30)

- **shared**: 클린 DB 전체 마이그레이션 적용 — `FlywayMigrationTest` PASS. PR #31 CI `build` pass → main 머지 → **`Publish Package` 성공**. 받은 SNAPSHOT jar에 `V202606301002__badges.sql`·`CommunityBadgeAwardedEvent.class` 포함 직접 확인.
- **community-svc**: `./gradlew test` 클린 DB **전체 38/38 PASS**(18 suites, Build 1 회귀 + 신규 BadgeServiceTest 3·BadgeTriggerTest 6·BadgeApiMockMvcTest 1). 컨트롤러가 `--rerun-tasks`로 직접 재확인. PR #15 CI `build` pass(fresh postgres + 게시 jar 독립검증) → develop 머지(`0096cae`).
- **Subagent-Driven**: Task별 implementer(TDD RED→GREEN) + 컨트롤러 직접 검증(diff·테스트 재실행) + task-review(로직 Task는 평결 파일 기록). Task 3 리뷰 Important 2건(단일 타임스탬프·outbox 필드 단언) 반영. **최종 전체 브랜치 리뷰(opus) "Ready to merge: Yes"**(Critical/Important 0). scope-lock: 각 Task 커밋 범위 플랜과 일치, 이탈 0.

## 3. 남은 작업 — 후속 빌드

- **Build 3(다음 진입점) — sockpuppet 탐지 + 자기 글 투표 금지**: 현재 STUDENT/TEACHER/CRITIC은 **자기 글 투표로도 획득 가능**(VoteService에 `// 자기투표…Build 3에서 정합` 주석 표기). 자기투표 금지 + 다중계정 셀프추천 탐지. 착수 시 이 세 award 지점과 Build 1 투표 로직 재검토.
- **배지 3종 dormant 트리거**: FIRST_STEP(프로필 이벤트 소비 — platform-svc 연동)·EDITOR(글 편집 기능 신설)·COMMUNITY(스트릭 도입) — 카탈로그는 이미 시드됨.
- **Silver/Gold 배지**(설계문 §3.3), **게이트 500/1000**(상수는 정의됨, 강제 미연결), **board_type 점수 차등**, **스트릭/주간 리포트 배치**.
- **배지 알림**: `community.badge.awarded` 발행되나 소비자(notification 워커) 미구현.
- **코드 follow-up(최종리뷰 Minor, 비차단)**: 답변경로 CRITIC 테스트(rep-125 게이트), 질문작성자 PHILANTHROPIST 테스트, `BadgeQueryService.badgesOf` N+1(Bronze 카디널리티엔 무해).

## 4. 환경/도구/게이트 (필수)

- **환경**: Windows 11 + **Git Bash**(WSL 아님). 모든 도구 호출 Bash만(PowerShell 금지 — antml 프리픽스 버그). 메인 직접 호출 마찰 0건.
- **백엔드 스택**: Java 21 · Spring Boot 4.0.7 · Gradle(Kotlin DSL). Jackson 3(`tools.jackson.databind.json.JsonMapper` — `writeValueAsString` unchecked). 빌드/테스트 `./gradlew`.
- **로컬 인프라(테스트 필수)**: `cd devpath-shared && docker compose up -d postgres`(pgvector/pg17, 5432). community-svc 테스트 DB=`devpath_citest`, shared=`devpath`(동일 컨테이너). **로컬 DB가 Flyway 이력과 불일치(테이블만 남음)하면** migrate가 `relation already exists`로 실패 → `docker exec devpath-local-postgres-1 psql -U devpath -d <db> -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO devpath; GRANT ALL ON SCHEMA public TO public;"` 후 재적용(CI는 매 실행 fresh라 무관).
- **cross-repo 릴리스 게이트(필수)**: shared 버전 `0.0.1-SNAPSHOT`, **main push에서만 GitHub Packages publish**. shared엔 develop 없음 → `feat/*→main` 직접 PR 관례. community-svc는 publish 후 `./gradlew compileJava --refresh-dependencies`로 새 SNAPSHOT 수신 필요(인증 `gpr.user`/`gpr.token`, gradle.properties). **jar 검증은 mtime 필터 말고 내용 grep**(`unzip -l <jar> | grep V2026…`)으로 — 캐시에 옛 SNAPSHOT jar가 여럿 남아 mtime이 헷갈린다(이번 세션 실제 혼동).
- **Subagent-Driven 운영 메모**: 백그라운드 서브에이전트의 **최종 채팅 메시지가 컨트롤러에 안 닿는다**(알림 result가 일반 문구로 대체) → implementer는 리포트를, **리뷰어는 평결을 파일로 기록**하게 하고 컨트롤러가 Read. task-brief/review-package 스크립트는 `.claude/plugins/.../subagent-driven-development/scripts`.
- 브랜치 전략: 각 레포 `develop` 분기 → develop PR → 머지. main 직접 금지(shared 릴리스 PR 제외). 서브에이전트 Scope Lock + 컨트롤러 직접 검증.

## 5. 레포 위생 / 열린 항목

- **이 세션 산출 PR**: shared #31·community-svc #15(코드) 머지 완료. documents #51(spec+플랜) 머지 완료. 진행현황 [community-svc #16]·본 핸드오프 PR은 머지 대기/진행.
- **여전히 열린(이전 세션)**: frontend **PR #55**(랜딩 P7) — 배지와 무관, 미머지 유지.
- 검증용 로컬 postgres 컨테이너(`devpath-local-postgres-1`) 실행 중일 수 있음 — 불필요 시 `docker compose stop postgres`.

## 6. 다음 진입점

**평판 Build 3 — sockpuppet 탐지 + 자기 글 투표 금지**: Build 1 spec(20 §3.5 평판 남용 방지)·§3.3 배지와 연계. 자기투표 금지를 VoteService에 추가하고, STUDENT/TEACHER/CRITIC 자기투표 획득을 함께 차단·정합. sockpuppet은 IP/디바이스 기반(설계문 §3.5) — moderation 연계 여부 확인. Build 1/2와 동일 패턴(spec→플랜(TDD)→구현, cross-repo 릴리스 게이트).

> 대안 진입점: 배지 3종 dormant 트리거(프로필/편집/스트릭 상위 기능 필요) 또는 열린 frontend #55(랜딩) 마무리. 우선순위는 사용자 확인.

## 7. 관련 메모리

- [[devpath-next-reputation-build1]](Build 1+2 완료·다음 Build 3) · [[handoff-2026-06-30-reputation-build1-done]](직전 핸드오프) · [[devpath-handoffs-lag-verify-first]](문서 lag — 착수 전 git 검증)
- 대시보드: https://devpathai.github.io/workflow-dashboard/
