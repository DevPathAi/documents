# Design: 평판 기초 Build 1 — 평판 엔진 (community-svc)

> 2026-06-30 · 슬라이스 "평판 기초"(MD3 Tier-2)의 첫 빌드. 설계 출처 [20_커뮤니티_기능_설계서 §3](../../20_커뮤니티_기능_설계서.md) · 일정 [17_스케줄 §2](../../17_스케줄.md).
> **스택**: Java 21 · Spring Boot 4 · Gradle · shared Flyway. 패키지 `ai.devpath.community.reputation`.

## 목표 / 범위

이미 구현된 **투표(upvote/downvote)·답변 채택** 위에 **평판 가산 엔진**을 얹는다. 이 빌드(Build 1)의 범위:

- 투표/채택 → 평판 점수 동기 가산(같은 트랜잭션)
- 총점(`user_reputation`) + 태그별 평판(`user_tag_reputation`)
- 일일 +40 상한(upvote 획득만)
- 레벨 권한 게이트 — 15(질문 upvote)·125(답변 downvote)만 강제, 500/1000은 상수만 정의

**범위 밖(후속 빌드)**: Bronze 배지 9종, sockpuppet 탐지, 자기 글 투표 금지, 현상금(bounty), Silver/Gold 배지.

## 현재 상태 (실측, 2026-06-30)

- `community_votes` + `VoteService.votePost/voteAnswer`(upsert: value ±1, 0 없음 → 철회 없이 변경만) — 동작 중. **평판 미가산.**
- 답변 채택: `community_answers.is_accepted`·`community_questions.accepted_answer_id`·`AnswerService.accept(userId, answerId)`(질문 작성자만) — 동작 중. **평판 미가산 + 재호출 시 중복 채택 위험(가드 없음).**
- 평판/태그평판/이벤트 테이블 없음.

## 아키텍처

가산은 **동기·같은 트랜잭션**(분산 불필요 — community-svc 단일 도메인). 기존 서비스의 `@Transactional` 안에서 신규 `ReputationService`를 호출한다.

```
VoteService.votePost/voteAnswer ─┐
AnswerService.accept ────────────┼─▶ ReputationService (같은 tx)
                                 │     ├─ reputation_events 기록(append-only)
                                 │     ├─ user_reputation.total 갱신
                                 │     └─ user_tag_reputation.score 갱신
VoteService(게이트) ◀── ReputationQueryService.reputationOf(userId)
```

## 스키마 (shared 신규 Flyway: `V202606301001__reputation.sql` — 기존 최신 `V202606261001` 다음)

```sql
CREATE TABLE reputation_events (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL,                 -- 평판 귀속 대상(글/답변 작성자, 또는 downvote 행사자)
  delta       INT    NOT NULL,                 -- +5/+10/+15/+2/-2/-1
  reason      VARCHAR(32) NOT NULL,            -- UPVOTE_Q|UPVOTE_A|ACCEPTED|ACCEPT_BONUS|DOWNVOTE_RECEIVED|DOWNVOTE_CAST
  source_type VARCHAR(16) NOT NULL,            -- POST|ANSWER
  source_id   BIGINT NOT NULL,
  tag_id      BIGINT,                          -- 태그 평판 대상(없으면 NULL)
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_repevent_user_day ON reputation_events (user_id, created_at);  -- 일일상한 산출

CREATE TABLE user_reputation (
  user_id    BIGINT PRIMARY KEY,
  total      INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE user_tag_reputation (
  user_id BIGINT NOT NULL,
  tag_id  BIGINT NOT NULL,
  score   INT NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, tag_id)
);
```

> 공통 규약(`set_updated_at` 트리거 등)은 shared 기존 마이그레이션 패턴을 따른다. FK는 cross-table 정책(users는 다른 서비스 소유) — 기존 community 스키마처럼 **논리 참조**(물리 FK 미설정).

## 컴포넌트

- **`ReputationService`** (`@Transactional` 전제 — 호출자 tx 합류)
  - `applyVote(authorId, voterId, targetType, targetId, oldValue, newValue, List<tagId>)`
    - 델타 = (newValue 효과) − (oldValue 효과). 작성자 총점/태그점수에 적용 + 이벤트 기록.
    - downvote **행사 비용 −1**: voterId에게 별도 이벤트(행사가 새로 −1이 될 때만; 변경 역산 포함).
  - `applyAcceptance(answerAuthorId, questionAuthorId, List<tagId>)`
    - answerAuthorId +15(ACCEPTED), questionAuthorId +2(ACCEPT_BONUS). 상한 제외.
- **`ReputationQueryService.reputationOf(userId) -> int`** — `user_reputation.total`(없으면 0). 레벨 게이트용.
- **`ReputationLevel`** 상수: `UPVOTE_QUESTION=15, DOWNVOTE_ANSWER=125, EDIT_SUGGEST=500, MODERATION=1000`. 게이트는 앞 둘만 사용.
- **점수 상수**: `UPVOTE_Q=+5, UPVOTE_A=+10, ACCEPTED=+15, ACCEPT_BONUS=+2, DOWNVOTE_RECEIVED=-2, DOWNVOTE_CAST=-1`.

## 가산 규칙 (문서 20 §3)

| 트리거 | 귀속 | 델타 | 상한 |
|---|---|---|---|
| 질문(POST) upvote | 글 작성자 | +5 | O |
| 답변(ANSWER) upvote | 답변 작성자 | +10 | O |
| 답변 채택됨 | 답변 작성자 | +15 | X |
| 답변 채택 행위 | 질문 작성자 | +2 | X |
| 글/답변 downvote 받음 | 작성자 | −2 | X |
| downvote 행사 | 행사자 | −1 | X |

**투표 변경 역산**: upsert가 value를 덮어쓰므로, 가산 전 **old value를 포착**해 `(new효과 − old효과)`만 적용. 예: +1→−1 이면 작성자 −2(received)−(+이전 효과 회수), 행사자 −1(cast) 신규. 태그 점수도 동일 델타.

## 일일 +40 상한 (upvote 획득만)

대상 작성자가 **하루(서버 TZ) UPVOTE_Q/UPVOTE_A로 얻는 합**을 +40으로 클램프. 초과분은 **미지급**(SO식). 산출: `reputation_events`에서 `user_id=작성자 AND reason IN (UPVOTE_Q,UPVOTE_A) AND created_at::date = today` 합. 채택(+15)·보너스(+2)·downvote 패널티는 상한과 무관. 역산(투표 변경으로 인한 음의 upvote 델타)은 당일 합을 줄인다.

## 레벨 게이트 (VoteService 강제)

- 질문 upvote(POST, value=+1): 행사자 `reputationOf ≥ 15` 아니면 `ForbiddenException`.
- 답변 downvote(ANSWER, value=−1): 행사자 `reputationOf ≥ 125` 아니면 `ForbiddenException`.
- 그 외 투표(질문 downvote·답변 upvote)는 게이트 없음(문서 20 §3.2 기준). 500/1000은 대응 기능 부재로 미배선.

## 채택 중복 가드 (정확성 보강)

`AnswerService.accept`는 현재 이미 채택된 답변 재호출 시 +15 중복 위험 → **`if (a.isAccepted()) return;` 가드 추가** 후 평판 부여. (un-accept/재채택은 범위 밖.)

## 에러 처리

- 레벨 미달 → `ForbiddenException`(기존 `GlobalExceptionHandler` 재사용).
- 대상/작성자 없음 → 기존 `NotFoundException` 흐름 유지.
- 자기 글 투표 금지: 문서 명세 없음 → **이번 빌드 미적용**(기존 동작 유지, 후속 결정).

## 테스트 (TDD, `@ActiveProfiles("test")` + shared Flyway)

1. upvote 가산: 질문 +5 / 답변 +10 작성자 총점·태그점수.
2. 투표 변경 역산: +1→−1 시 작성자/행사자 점수 정확 반영.
3. 일일 +40 상한: upvote 합 40 클램프, 채택 +15는 상한 무관.
4. 채택: 답변자 +15 · 질문자 +2 · **재채택 호출 no-op**.
5. downvote: 받음 −2 · 행사 −1.
6. 레벨 게이트: 평판 14→질문 upvote 거부, 15→허용 / 124→답변 downvote 거부, 125→허용(경계값).
7. 태그 평판: 글의 각 태그에 동일 델타.

## 빌드 분해 (이 슬라이스 전체)

- **Build 1(본 spec)**: 평판 엔진 + 태그평판 + 일일상한 + 레벨 게이트.
- Build 2(후속): Bronze 배지 9종 자동 수여.
- Build 3(후속): sockpuppet 탐지 + 자기 글 투표 금지.

## 리스크 / 후속

- 일일상한을 events 합산으로 매 투표 계산 → 인덱스(`idx_repevent_user_day`)로 완화. 트래픽 증가 시 `reputation_daily` 집계 테이블 후속.
- 태그 해석: 답변 투표의 태그는 **질문 글의 `community_post_tags`**에서 도출(답변 자체엔 태그 없음).
- users 논리 참조 — 탈퇴 사용자 평판 정리는 운영 단계 후속.
