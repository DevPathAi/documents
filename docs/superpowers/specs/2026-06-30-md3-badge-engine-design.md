# 평판 기초 Build 2 — Bronze 배지 엔진 설계 (MD3)

> 평판 Build 1(평판 엔진, 구현 완료) 위에 **Bronze 배지 자동 수여 엔진**을 community-svc에 올린다. 권위 출처: [20_커뮤니티_기능_설계서.md](../../../20_커뮤니티_기능_설계서.md) §3.3 배지 시스템 · §8.1 ERD(Badge/UserBadge) · §8.2 이벤트(community.badge.awarded).

## 목표

질문·답변 작성, 투표로 점수 +1 도달, 평판 15 도달, downvote 행사 등 **이미 community-svc가 보유한 신호**에 반응해 Bronze 배지를 **같은 트랜잭션에서 동기 수여**한다. 멱등하게 1회만 수여하고, 수여 시 `community.badge.awarded`를 outbox로 발행한다. 배지 카탈로그 9종(Bronze)은 전부 시드하되, 신호가 있는 6종만 트리거를 결선한다.

## 비목표 (범위 밖)

- Silver/Gold 배지(설계문 §3.3) — 후속.
- 신호가 없는 Bronze 3종의 **트리거 결선**: FIRST_STEP(프로필 작성=platform-svc 소관)·EDITOR(글 편집 기능 미구현)·COMMUNITY(30일 연속 방문=스트릭 미구현). **카탈로그에는 시드**하되, 상위 기능 도입 시 트리거를 잇는다.
- 배지 수여 **알림**(notification 워커) — `community.badge.awarded` 소비자는 미구현. 이벤트는 발행만 한다.
- 스트릭(TZ)·주간 리포트 배치 — 스케줄 §평판 기초의 별도 항목.

## 배경 / 현 상태 (검증됨, 2026-06-30)

- community-svc에 `badge` 모듈 **없음**(신설). `reputation` 모듈(Build 1)·`outbox` 인프라(OutboxEntry/OutboxRelay) **있음**.
- community-svc는 **로컬 Flyway 마이그레이션이 없고** shared jar의 `classpath:db/migration`을 쓴다 → 배지 스키마는 **shared**에 둔다(Build 1 reputation과 동일). cross-repo 릴리스 게이트 동일 적용.
- 기존 이벤트 발행 패턴: shared의 이벤트 레코드(예 `CommunityQuestionPostedEvent`, `EVENT_TYPE` 상수)를 JSON 직렬화해 `OutboxEntry`(aggregate_type/aggregate_id/event_type/payload)로 적재. `community.badge.awarded`도 동일 패턴.
- 글 편집(update/PUT/PATCH) 엔드포인트 **없음**, 방문/스트릭 추적 **없음**, 프로필은 platform-svc 소관 → 3종 dormant 근거.

## 배지 9종 (Bronze) — §3.3 일치

| code | 배지명 | 조건 | Build 2 트리거 |
|---|---|---|---|
| FIRST_QUESTION | 첫 질문 | 질문 작성 | ✅ 결선 |
| FIRST_ANSWER | 첫 답변 | 답변 작성 | ✅ 결선 |
| STUDENT | 학생 | 질문 1개가 +1 이상 | ✅ 결선 |
| TEACHER | 선생 | 답변 1개가 +1 이상 | ✅ 결선 |
| PHILANTHROPIST | 자선가 | 평판 15 도달 | ✅ 결선 |
| CRITIC | 비평가 | downvote 1회 행사 | ✅ 결선 |
| FIRST_STEP | 첫 걸음 | 프로필 작성 완료 | ⏸️ 시드만(platform-svc 신호) |
| EDITOR | 편집자 | 글 편집 1회 | ⏸️ 시드만(편집 기능 미구현) |
| COMMUNITY | 커뮤니티 | 30일 연속 방문 | ⏸️ 시드만(스트릭 미구현) |

> code는 영문 안정키(컬럼 UNIQUE). 한글 배지명은 `name`. 조건 원문은 `criteria`에 보존.

## 아키텍처

신규 `ai.devpath.community.badge` 모듈. `BadgeService`가 **호출자(QuestionService/AnswerService/VoteService)의 @Transactional에 합류**해 동기 수여한다(Build 1 `ReputationService` 패턴 재사용 — 호출자가 이미 로드한 값을 인자로 전달, badge 로직이 post/reputation 내부구조에 비결합).

### 컴포넌트

**shared 레포** (`devpath-shared`):
- `db/migration/V202606301002__badges.sql` — `badges`·`user_badges` 테이블 + 9종 Bronze 시드(reputation `V202606301001` 다음 시퀀스).
- `ai.devpath.shared.event.CommunityBadgeAwardedEvent` — 이벤트 레코드(`EVENT_TYPE = "community.badge.awarded"`).

**community-svc 레포** 신규 패키지 `ai.devpath.community.badge`:
- `BadgeCode` — enum 9종(위 code).
- `Badge` / `BadgeRepository` — 카탈로그 엔티티 + `findByCode`.
- `UserBadge` / `UserBadgeId` / `UserBadgeRepository` — 보유 배지(복합 PK) + `existsByUserIdAndBadgeId`·`findByUserId`.
- `BadgeService` — `award(long userId, BadgeCode code, String sourceType, long sourceId)`: 멱등 체크 → UserBadge 저장 → outbox 발행. 트리거별 편의 메서드(아래).
- 조회: `BadgeQueryService` 또는 컨트롤러 메서드.

**배선 수정**:
- `QuestionService.create` → `badgeService.onQuestionCreated(authorId, postId)` (FIRST_QUESTION).
- `AnswerService.add` → `badgeService.onAnswerCreated(authorId, answerId)` (FIRST_ANSWER).
- `VoteService.votePost` → 글 순점수 ≥1이면 `STUDENT`(글 작성자), value=−1이면 `CRITIC`(투표자).
- `VoteService.voteAnswer` → 답변 순점수 ≥1이면 `TEACHER`(답변 작성자), value=−1이면 `CRITIC`(투표자).
- `VoteService`/`AnswerService`의 `reputation.applyVote/applyAcceptance` 직후 **평판이 증가한 작성자**에 대해 `reputationOf(authorId) ≥ 15`이면 `PHILANTHROPIST`. applyVote → 글/답변 작성자. applyAcceptance → 답변 작성자(+15)·질문 작성자(+2) 둘 다 평가.

> **STUDENT board_type 무구분**: votePost는 모든 POST에 적용된다. Build 1 평판이 모든 POST upvote를 board_type 구분 없이 처리한 것과 동일하게, STUDENT도 순점수 ≥1 도달한 POST 작성자에게 수여한다(자유게시판 등 board_type별 차등은 평판과 함께 후속). "질문"으로의 한정은 board_type 도입 시 정합.

**조회 API**: `GET /community/users/{userId}/badges` → `[{code, name, tier, awardedAt}, ...]`(awarded_at 내림차순).

### 스키마 (shared Flyway)

```sql
CREATE TABLE badges (
  id          BIGSERIAL PRIMARY KEY,
  code        VARCHAR(32)  NOT NULL UNIQUE,   -- 안정키(FIRST_QUESTION 등) — 코드가 참조
  name        VARCHAR(64)  NOT NULL,          -- 한글 배지명
  tier        VARCHAR(8)   NOT NULL,          -- BRONZE|SILVER|GOLD
  criteria    VARCHAR(255) NOT NULL,          -- 조건 원문(감사/표시용)
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
  CONSTRAINT chk_badge_tier CHECK (tier IN ('BRONZE','SILVER','GOLD'))
);

CREATE TABLE user_badges (
  user_id    BIGINT      NOT NULL,            -- platform users 논리 참조(서비스 경계 — FK 없음)
  badge_id   BIGINT      NOT NULL REFERENCES badges(id),
  awarded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, badge_id)
);
CREATE INDEX idx_user_badges_user ON user_badges (user_id, awarded_at DESC);

-- 9종 Bronze 시드(트리거 결선 여부와 무관하게 카탈로그 완비).
INSERT INTO badges (code, name, tier, criteria) VALUES
  ('FIRST_QUESTION','첫 질문','BRONZE','질문 작성'),
  ('FIRST_ANSWER','첫 답변','BRONZE','답변 작성'),
  ('STUDENT','학생','BRONZE','질문 1개가 +1 이상'),
  ('TEACHER','선생','BRONZE','답변 1개가 +1 이상'),
  ('PHILANTHROPIST','자선가','BRONZE','평판 15 도달'),
  ('CRITIC','비평가','BRONZE','downvote 1회 행사'),
  ('FIRST_STEP','첫 걸음','BRONZE','프로필 작성 완료'),
  ('EDITOR','편집자','BRONZE','글 편집 1회'),
  ('COMMUNITY','커뮤니티','BRONZE','30일 연속 방문');
```

> `user_id`는 Build 1 reputation·기존 community 테이블과 동일하게 **users FK 없음**(교차서비스 경계). `badge_id`는 동일 서비스 참조데이터라 FK 유지. `idx_user_badges_user`로 사용자별 보유 배지 조회.

## 데이터 흐름

1. 사용자가 질문 작성 → `QuestionService.create` tx 안에서 글 저장·이벤트 적재 후 `badgeService.onQuestionCreated(authorId, postId)`.
2. `BadgeService.award(authorId, FIRST_QUESTION, "POST", postId)`: `user_badges`에 (authorId, FIRST_QUESTION.id) 없으면 INSERT + outbox에 `CommunityBadgeAwardedEvent` 적재. 이미 있으면 **no-op**.
3. OutboxRelay(기존 스케줄러)가 `community.badge.awarded`를 Kafka로 발행(소비자는 후속).
4. 투표/평판도 동일 — VoteService가 순점수·평판 total을 평가해 해당 배지 award 호출.

## 멱등성 / 동시성

- 멱등은 `user_badges` PK(user_id, badge_id). `award`는 `existsByUserIdAndBadgeId`로 선검사 후 INSERT(경쟁 시 PK 유니크 위반은 동일 tx 드묾 — 같은 사용자 동시 동일 트리거는 사실상 없음, 발생해도 무결성은 PK가 보장).
- 같은 tx 합류라 글/투표/평판 변경과 배지 수여가 원자적. 롤백 시 함께 취소.

## 에러 처리

- 배지 award 실패가 핵심 도메인(질문/투표) tx를 깨뜨리지 않아야 하는가? → **같은 tx**이므로 award의 제약 위반은 전체 롤백. 단 award는 단순 INSERT라 실패 요인이 적다. 미시드 code 참조 시 `findByCode` empty → 프로그래밍 오류로 즉시 실패(시드 누락 방지).
- `criteria`/`name`은 시드 기준(한글), 표시는 카탈로그 조회.

## 테스트 전략 (TDD)

- `BadgeServiceTest`(@SpringBootTest, devpath_citest): 6 트리거 각 정확한 배지 수여 + **멱등**(재트리거 무중복) + **outbox 1건 적재**(event_type=community.badge.awarded) 검증.
- 트리거 통합: 질문작성→FIRST_QUESTION, 답변작성→FIRST_ANSWER, 글 +1 투표→STUDENT, 답변 +1 투표→TEACHER, downvote→CRITIC, 평판 15 도달→PHILANTHROPIST.
- 조회 MockMvc: `GET /community/users/{id}/badges` 보유 목록·정렬.
- 회귀: 기존 평판/투표 테스트(레벨 게이트 등) 무변 유지.

## 릴리스 게이트 (Build 1과 동일)

shared(마이그레이션 + 이벤트 레코드)는 `feat/*→main` 직접 PR 머지에서만 GitHub Packages publish. community-svc는 publish 후 `--refresh-dependencies`로 새 jar 수신 → Task 2~ 진행.

## 리스크 / 후속

- **자기 투표로 학생/선생 획득**: Build 1에 자기 글 투표 금지 미적용 → 자기 글에 +1로 STUDENT/TEACHER 가능. 자기 투표 금지는 Build 3 범위. 배지도 그때 정합.
- **순점수 정의**: STUDENT/TEACHER의 "+1 이상"은 (upvote − downvote) ≥ 1. VoteService가 이미 집계하는 카운트로 산출.
- **3종 dormant**: 상위 기능(프로필 이벤트 소비·글 편집·스트릭) 도입 시 트리거 결선. 카탈로그는 이미 완비.
- **이벤트 소비자 부재**: `community.badge.awarded`는 발행되나 현재 소비자 없음 — notification 워커는 후속.
