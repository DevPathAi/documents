# 핸드오프 — 평판 기초 Build 3(자기 글 투표 금지 + 담합 탐지) 완료 / 다음 = 스트릭·배치 또는 후속 고도화 (2026-07-01)

> 다음 세션 이관용. **평판 기초 Build 3(남용 방지) 구현·develop 머지 완료**(community-svc PR #17 / shared 스키마·이벤트 PR #32 main publish). spec+플랜(documents PR #53)은 develop 머지됨. Build 1(평판 엔진)·Build 2(Bronze 배지) 위에 **자기 글 투표 하드 차단**과 **행동 기반 담합(sockpuppet) 탐지(기록만)**를 올렸다. 직전 핸드오프 [[handoff-2026-06-30-badge-build2-done]]의 "다음=Build 3"를 본 문서가 잇는다. **평판 기초 핵심 구현은 이것으로 완료** — 남은 것은 스트릭/배치(같은 스케줄 항목의 별도 서브)와 다수 후속 고도화(하단 §3). 실행은 **Subagent-Driven Development**. 환경 = **Windows + Git Bash, 메인 직접 진행.**

## 1. 종착점 — Build 3 ✅

승인 spec/플랜: [specs/2026-07-01-md3-antiabuse-build3-design.md](specs/2026-07-01-md3-antiabuse-build3-design.md) · [plans/2026-07-01-md3-antiabuse-build3.md](plans/2026-07-01-md3-antiabuse-build3.md)(5 Task, TDD). 권위 출처 [20_커뮤니티_기능_설계서.md](../../20_커뮤니티_기능_설계서.md) §3.5 평판 남용 방지.

| Task | 산출물 | 근거 |
|---|---|---|
| **1 — shared 스키마+이벤트** | `V202607011001__vote_abuse_suspicions.sql`(actor_id·target_user_id·reason·evidence_count, UNIQUE(actor_id,target_user_id,reason)) + `CommunityReputationSuspectedEvent`(`community.reputation.suspected`) | shared `c2fc3ec` / PR #32 → **main publish** |
| **2 — 담합 도메인+쿼리** | `ai.devpath.community.abuse`: `VoteAbuseSuspicion`+Repo, `RepPoints.COLLUSION_UPVOTE_THRESHOLD=5`, `ReputationEventRepository.countDistinctUpvotedSourcesByActorToUser`(delta>0 필터) | community-svc `9c26dfd` |
| **3 — CollusionDetector** | `checkOnUpvote(voterId, authorId, sourceType, sourceId)` — 임계 도달 시 멱등 기록 + outbox 발행(기록만, 회수·차단 없음) | `4df1a26` |
| **4 — 자기 글 투표 금지** | `VoteService.votePost`/`voteAnswer` **레벨게이트 앞**에서 투표자==작성자 시 403(upvote·downvote 모두) | `87ed06d` |
| **5 — 담합 연결 + 회귀** | `VoteService`에 `CollusionDetector` 주입, PHILANTHROPIST 블록 뒤 `value==1`일 때 호출 + 배지 주석 갱신 | `098c9ca` |

- 자기투표 가드는 **모든 mutation(투표 반영·평판 가산·배지 수여·담합 탐지) 이전**에 hard throw라, 자기투표는 어떤 부작용도 남기지 않는다(Build 2에서 남은 "자기투표로 배지 획득" 문제도 이걸로 자동 해소).
- 담합 탐지: `reputation_events`의 투표자→작성자 **DISTINCT source(delta>0) upvote 수 ≥5**면 의심 1회 기록. `delta>0` 필터로 Build 1 투표변경 역산(동일 reason 음수 delta) 오탐을 배제(최종리뷰가 `ReputationService.reverseVote`와 대조 검증).

## 2. 검증 (2026-07-01)

- **shared**: 클린 DB 전체 마이그레이션 — `FlywayMigrationTest` PASS. PR #32 CI `build` pass → main 머지 → **`Publish Package` 성공**. jar에 마이그레이션+이벤트 클래스 포함 직접 확인(`unzip -l | grep` 내용 검증, mtime 아님).
- **community-svc**: `./gradlew test` 클린 DB **전체 45/45 PASS**(21 suites, Build 1·2 회귀 + 신규 CollusionDetectorTest 3·CollusionWiringTest 1·SelfVoteMockMvcTest 3). 컨트롤러가 `--rerun-tasks`로 직접 재확인. 자기투표 금지로 깨진 기존 테스트 없음(전부 별도 투표자/작성자 조합 확인). PR #17 CI `build` pass(fresh postgres + 게시 jar 독립검증) → develop 머지(`e27e544`).
- **Subagent-Driven**: Task별 implementer(TDD) + 컨트롤러 직접 검증(diff·테스트 재실행) + task-review(평결 파일 기록). **최종 전체 브랜치 리뷰(opus) "Ready to merge: Yes"**(Critical/Important 0, Minor 3건 전부 "액션 불필요"로 명시 — 이벤트 계약을 실제 게시 jar `javap`로 대조, 역산 필터를 `ReputationService.reverseVote` 소스와 대조, 자기투표 부작용 완전차단을 diff 전수 검증).

## 3. 남은 작업 — 후속

- **스트릭(TZ)·주간 리포트 배치·3일 미접속 AI 제안·선호 시간대 푸시**(다음 진입점 후보, 스케줄 §평판 기초의 별도 서브항목, 미착수).
- **레벨 게이트 500/1000**: `RepPoints.LVL_EDIT_SUGGEST=500`·`LVL_MODERATION=1000` 상수는 정의됨, 강제 미연결.
- **배지 3종 dormant**: FIRST_STEP(프로필=platform-svc 신호)·EDITOR(글 편집 기능 미구현)·COMMUNITY(스트릭 도입 시 결선 — 위 스트릭 작업과 연계 가능).
- **Silver/Gold 배지**(설계문 §3.3), **board_type 점수 차등**.
- **IP·디바이스 기반 sockpuppet 탐지**(설계문 §3.5 원문): community-svc에 IP/디바이스 신호 없음(컨트롤러 IP 미캡처, votes 컬럼 없음) — 요청 IP 캡처 파이프라인 신설 필요.
- **신계정 첫 7일 투표 불가**: 계정 생성일=platform-svc 소관, cross-service 신호 필요.
- **moderation 자동 제재/소비**: `community.reputation.suspected`·`community.badge.awarded` 둘 다 발행되나 소비자(moderation-worker) 미구현 — moderation 모듈 자체가 아직 없음(community-svc CLAUDE.md 도메인표에 "moderation" 항목만 존재).
- **코드 follow-up(전부 non-blocking, 최종리뷰/이전 task-review Minor)**: `CollusionDetector`의 이벤트/outbox 이중 `Instant.now()`(코스메틱), `BadgeQueryService.badgesOf` N+1(Bronze 카디널리티엔 무해), 답변경로 CRITIC·질문작성자 PHILANTHROPIST 테스트 커버리지.

## 4. 환경/도구/게이트 (필수)

- **환경**: Windows 11 + **Git Bash**(WSL 아님). 모든 도구 호출 Bash만(PowerShell 금지 — antml 프리픽스 버그).
- **백엔드 스택**: Java 21 · Spring Boot 4.0.7 · Gradle(Kotlin DSL). Jackson 3(`tools.jackson.databind.json.JsonMapper` unchecked). 빌드/테스트 `./gradlew`.
- **로컬 인프라(테스트 필수)**: `cd devpath-shared && docker compose up -d postgres`(pgvector/pg17, 5432). community-svc 테스트 DB=`devpath_citest`, shared=`devpath`. 로컬 DB가 Flyway 이력과 불일치하면 `docker exec devpath-local-postgres-1 psql -U devpath -d <db> -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO devpath; GRANT ALL ON SCHEMA public TO public;"` 후 재적용. **작업 종료 시 컨테이너 정지**(`docker compose stop postgres`) — 이번 세션에서 정지 완료.
- **cross-repo 릴리스 게이트**: shared 버전 `0.0.1-SNAPSHOT`, **main push에서만 GitHub Packages publish**. shared엔 develop 없음 → `feat/*→main` 직접 PR 관례. community-svc는 publish 후 `./gradlew compileJava --refresh-dependencies`. **jar 검증은 반드시 내용 grep**(`unzip -l <jar> | grep <파일명>`) — SNAPSHOT 캐시에 여러 해시가 누적되므로 mtime으로는 최신 jar를 특정할 수 없다(이번 세션 실제 혼동 후 정정).
- **⚠️ Subagent-Driven 동시성 함정**: 서브에이전트가 아직 실행 중인 상태에서 컨트롤러가 같은 `devpath_citest`에 직접 테스트를 실행하면 **간헐적 실패**가 난다(DB 경합, 코드 결함 아님 — Build 3 Task 3에서 실제 발생·오진단 위험 확인). **에이전트가 완전히 종료된 뒤에만** 컨트롤러 검증을 수행할 것.
- **⚠️ 서브에이전트 보고 신뢰 금지 강화**: 백그라운드 서브에이전트의 최종 채팅 메시지가 컨트롤러에 안 닿거나("Standing by" 등 공백 응답) 지연될 수 있다. implementer는 리포트 파일을, **리뷰어는 평결을 파일로 기록**하게 하고 컨트롤러가 항상 git log/diff/테스트 재실행으로 직접 확인한다.
- 브랜치 전략: 각 레포 `develop` 분기 → develop PR → 머지. main 직접 금지(shared 릴리스 PR 제외). 서브에이전트 Scope Lock + 컨트롤러 직접 검증.

## 5. 레포 위생 / 열린 항목

- **이 세션 산출**: shared #32·community-svc #17(코드) 머지 완료. documents #53(spec+플랜) 머지 완료. 진행현황 [community-svc #18]·스케줄 갱신 [documents #54]·본 핸드오프 PR은 머지 대기/진행.
- **여전히 열린(무관, 이전 세션)**: frontend **PR #55**(랜딩 P7) — CI `analyze-test` **실패** 확인됨(landing 잡은 pass). 별도 프론트엔드 수정 필요, 이번 세션 손대지 않음.

## 6. 다음 진입점

**후보 A — 스트릭(TZ)·주간 리포트 배치**: 같은 스케줄 "평판 기초" 항목의 마지막 서브(3일 미접속 AI 제안·선호 시간대 푸시 포함). 완료 시 배지 COMMUNITY(30일 연속방문)도 결선 가능해짐.

**후보 B — 후속 고도화 중 택1**: moderation 모듈 신설(suspicion/badge 이벤트 소비 + 자동 제재), 또는 레벨 게이트 500/1000, 또는 IP/디바이스 sockpuppet(요청 IP 캡처 인프라 선행 필요).

우선순위는 사용자 확인 필요 — 본 핸드오프 세션에서 다음 작업 계획을 함께 논의함(§7 참고).

## 7. 관련 메모리

- [[devpath-next-reputation-build1]](Build 1+2+3 완료·후속 목록) · [[handoff-2026-06-30-badge-build2-done]](직전 핸드오프) · [[devpath-handoffs-lag-verify-first]](문서 lag — 착수 전 git 검증)
- 대시보드: https://devpathai.github.io/workflow-dashboard/
