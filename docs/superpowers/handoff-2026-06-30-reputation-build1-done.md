# 핸드오프 — 평판 기초 Build 1(평판 엔진) 완료 / 다음 = Build 2(배지) (2026-06-30)

> 다음 세션 이관용. **평판 기초 Build 1(평판 엔진) 구현·develop 머지 완료**(community-svc PR #13 / shared 스키마 PR #30 main publish). spec+플랜(documents PR #49)은 develop 머지됨. 이미 동작하던 투표·채택 위에 **같은 트랜잭션에서 평판을 가산하는 엔진**(총점·태그평판·일일 +40 상한·레벨 게이트 15/125)을 올렸다. 남은 = **Bronze 배지 9종(Build 2)·sockpuppet+자기글투표금지(Build 3)·게이트 500/1000·스트릭/배치.** 환경 = **Windows + Git Bash, 메인 직접 진행.**

## 1. 종착점 — 평판 Build 1 ✅

승인 spec/플랜: [specs/2026-06-30-md3-reputation-engine-design.md](specs/2026-06-30-md3-reputation-engine-design.md) · [plans/2026-06-30-md3-reputation-engine-build1.md](plans/2026-06-30-md3-reputation-engine-build1.md)(5 Task, TDD).

| Task | 산출물 | 근거 |
|---|---|---|
| **1 — shared 스키마** | `V202606301001__reputation.sql`(reputation_events·user_reputation·user_tag_reputation + 인덱스 2종) | shared `3f35fba` / PR #30 → **main publish** |
| **2 — 평판 도메인** | `ai.devpath.community.reputation`: RepPoints·ReputationReason·ReputationEvent(원장)·UserReputation(총점)·UserTagReputation(태그) + 리포지토리 | community-svc `9a7c7c1` |
| **3 — ReputationService** | `applyVote`(upvote +5/+10·downvote −2 받음/−1 행사·투표변경 역산)·`applyAcceptance`(+15/+2)·`reputationOf` + 일일 +40 상한(채택 제외) | `71221cd` |
| **4 — 채택 연결** | `AnswerService.accept`: 채택 +15/+2 가산 + **중복 채택 가드**(재채택 no-op) | `bda46b6` |
| **5 — 투표 연결 + 게이트** | `VoteService` 전면 교체: 평판 가산 연결 + **레벨 게이트**(질문 upvote≥15·답변 downvote≥125) + old value 포착 역산 | `f80c9ae` |

- 아키텍처: `ReputationService`는 post 리포지토리를 주입받지 않고, 호출자(VoteService/AnswerService)가 이미 로드한 `authorId`·`tagIds`를 **인자로 전달** → 평판 로직이 post 내부구조에 비결합.
- 점수 상수(문서 20 §3.1): 질문 upvote +5 / 답변 upvote +10 / 채택 +15 / 채택 보너스 +2 / downvote 받음 −2 / downvote 행사 −1. 일일 upvote 획득 ≤ +40(채택·패널티 무관).

## 2. 검증 (2026-06-30)

- **shared**: 클린 DB 전체 마이그레이션 적용 — `FlywayMigrationTest` 29 PASS. PR #30 CI `build` pass → main 머지 → **`Publish Package` 성공**(`./gradlew publish`). 받은 SNAPSHOT jar에 `db/migration/V202606301001__reputation.sql` 포함 직접 확인(릴리스 게이트 통과).
- **community-svc**: `./gradlew test` **전체 28 PASS / 0 fail**(15 suites). 신규 = ReputationServiceTest(5: 가산·태그·역산·일일상한·채택상한제외)·AcceptReputationTest(1)·VoteGateMockMvcTest(1). PR #13 CI `build` pass(fresh postgres + 게시 jar 독립검증) → develop 머지(`cd268c3`).
- 회귀: 게이트 추가로 기존 `VoteMockMvcTest`(질문 upvote 투표자 301/302)가 403이 되므로 사전 평판 부여로 보정(테스트 의도=누적·멱등 보존).
- scope-lock 자체검증: develop 대비 16파일 변경 = 플랜 File Structure 정확히 일치, 범위 이탈 0.

## 3. 남은 작업 (평판) — 후속 빌드

- **Build 2 — Bronze 배지 9종**(다음 진입점): 평판/이벤트 트리거 자동 수여. `badge` 모듈(community-svc CLAUDE.md 도메인 표) 신설. `reputation_events` 원장이 트리거 근거로 이미 존재.
- **Build 3 — sockpuppet 탐지 + 자기 글 투표 금지**: 현재 자기 글 투표 금지 **미적용**(범위 밖이었음). sockpuppet(다중계정 셀프 추천) 탐지 로직.
- **게이트 500/1000**: 이번 빌드는 15(질문 upvote)·125(답변 downvote)만 강제. `RepPoints.LVL_EDIT_SUGGEST=500`·`LVL_MODERATION=1000` 상수는 정의됨, 강제 미연결.
- **board_type 미구분**: 모든 POST upvote를 +5로 처리(자유게시판 무평판·인기글 +20은 문서 20이나 후속).
- **스트릭/배치**(스케줄 §평판 기초): 스트릭(TZ)·주간 리포트 배치·3일 미접속 AI 제안·선호 시간대 푸시 — 미착수.
- **태그 변경 잔차**(리스크): 투표 후 글 태그가 바뀌면 역산이 현재 태그 기준이라 태그 점수 잔차 가능(통상 태그 고정이라 Build 1 범위 밖). 후속에서 events에 tag 기록 고려.

## 4. 환경/도구 (필수)

- **환경**: Windows 11 + **Git Bash**(WSL 아님). 모든 도구 호출은 Bash만 사용(PowerShell 금지 — antml 프리픽스 버그). 이번 세션 메인 직접 호출 마찰 0건.
- **백엔드 스택**: Java 21 · Spring Boot 4.0.7 · Gradle(Kotlin DSL). community-svc 패키지 루트 `ai.devpath.community`. 빌드/테스트 `./gradlew`.
- **로컬 인프라(테스트 필수)**: `cd devpath-shared && docker compose up -d postgres`(pgvector/pg17, 5432). community-svc 테스트 DB = **`devpath_citest`**(application-test.yml), shared 테스트 DB = `devpath`. 둘 다 동일 컨테이너.
- **⚠️ 로컬 DB 오염 주의**: `postgres-data` 볼륨이 Flyway 이력과 불일치(테이블만 남음)하면 migrate가 `relation already exists`로 실패한다(이번 세션 실제 발생). 해결: `docker exec devpath-local-postgres-1 psql -U devpath -d <devpath|devpath_citest> -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO devpath; GRANT ALL ON SCHEMA public TO public;"` 후 재적용(CI는 매 실행 fresh라 무관).
- **cross-repo 릴리스 게이트(필수)**: shared는 버전 `0.0.1-SNAPSHOT`, **main push에서만 GitHub Packages publish**. community-svc는 `gpr.user`/`gpr.token`(gradle.properties)로 인증, 새 스키마 소비 전 `./gradlew compileJava --refresh-dependencies`로 SNAPSHOT 갱신 필요. shared엔 **develop 브랜치 없음** → `feat/*→main` 직접 PR 관례.
- 브랜치 전략: 각 레포 `develop` 분기 → develop PR → 머지. main 직접 금지(shared 릴리스 PR 제외). 서브에이전트 Scope Lock + 컨트롤러 직접 검증.

## 5. 레포 위생 / 열린 항목 (착수 전 확인)

- **열린 PR(이 세션 외)**: documents **PR #48**(slice10-D 핸드오프 — 그 "다음=#11 랜딩" 포인터는 본 문서가 대체)·frontend **PR #55**(랜딩 P7, 슬라이스 #11) 모두 **OPEN**. 랜딩은 구현됐으나 develop 미머지 상태.
- 서비스 레포 일부가 이미 머지된 feature 브랜치에 체크아웃만 남아있을 수 있음 — 재개 전 각 레포 `develop` 전환 + `git pull`(community-svc·shared는 이 세션에서 정리됨).
- 검증용 로컬 postgres 컨테이너(`devpath-local-postgres-1`) 실행 중일 수 있음 — 불필요 시 `docker compose stop postgres`.

## 6. 다음 진입점

**평판 Build 2 — Bronze 배지 9종**: `reputation_events` 트리거 기반 자동 수여 + `badge` 모듈. 스케줄 `17_스케줄.md` §2 MD3 평판 기초 · §3 Tier-3(#12 평판 고도화)의 기초 파트. 착수 전 평판 spec(20_커뮤니티_기능_설계서 §3, 배지 9종 정의) 확인.

> 대안 진입점: Build 3(sockpuppet·자기글투표금지) 또는 열린 frontend PR #55(랜딩) 마무리. 우선순위는 사용자 확인.

## 7. 관련 메모리

- [[devpath-next-reputation-build1]](평판 Build 1 완료·다음 Build 2/3) · [[devpath-handoffs-lag-verify-first]](문서 lag — 착수 전 git 검증)
- 대시보드: https://devpathai.github.io/workflow-dashboard/
