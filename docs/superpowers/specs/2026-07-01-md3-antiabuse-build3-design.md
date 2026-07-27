# 평판 기초 Build 3 — 남용 방지(자기 글 투표 금지 + 담합 탐지) 설계 (MD3)

> 평판 Build 1(엔진)·Build 2(Bronze 배지) 위에 **평판 남용 방지**를 community-svc에 추가한다. 권위 출처: [20_커뮤니티_기능_설계서.md](../../20_커뮤니티_기능_설계서.md) §3.5 평판 남용 방지.

## 목표

두 축을 구현한다. (1) **자기 글 투표 금지**: 사용자가 자신의 글/답변에 투표하지 못하게 하드 차단. (2) **행동 기반 담합(sockpuppet) 탐지**: 이미 있는 `reputation_events` 원장으로 "한 계정이 특정 계정에게 반복 upvote" 패턴을 탐지해 **기록만 한다**(suspicion 영속 + 이벤트 발행). 평판 회수·투표 차단은 하지 않는다(false positive 무해, 실제 제재는 후속 moderation).

## 비목표 (범위 밖)

- **IP·디바이스 기반 sockpuppet 탐지**(설계문 §3.5): community-svc에 IP/디바이스 신호가 없다(컨트롤러 IP 미캡처, `community_votes`에 컬럼 없음). 요청 IP 캡처 + 스키마 컬럼 + 파이프라인은 후속.
- **신계정 첫 7일 투표 불가**(§3.5): 계정 생성일은 platform-svc 소관(community는 `author_id`/`userId` 논리 참조). cross-service 신호 — 후속.
- **자동 감사/제재(Moderation Service)**: moderation 모듈 미존재. 이번엔 suspicion **기록 + 이벤트**까지. 소비·제재는 후속.
- 상호(reciprocal) boosting 고도화·가중 스코어링, 레벨 게이트 500/1000.

## 배경 / 현 상태 (검증됨, 2026-07-01)

- **VoteService에 자기투표 체크 없음** — `votePost`/`voteAnswer`가 투표자 `userId`와 작성자 `authorId`를 비교하지 않는다. 자기투표가 가능하고, 이로 인해 Build 2의 STUDENT/TEACHER/CRITIC이 자기투표로 획득 가능(코드에 "Build 3에서 정합" 주석 존재).
- **moderation 모듈 미존재.** `reputation`·`badge`·`post`·`outbox` 모듈은 존재.
- **`reputation_events` 원장**(Build 1)에 `actor_id`(유발자=투표자)·`user_id`(수혜자)·`reason`·`created_at`이 있어 IP/디바이스 없이 **행동 기반 담합 탐지**가 community-svc 내에서 가능. `ReputationEventRepository`(findByActorIdAndSourceTypeAndSourceId·sumUpvoteGainSince) 존재.
- community-svc는 **로컬 Flyway 마이그레이션이 없고** shared jar `classpath:db/migration`을 쓴다 → suspicion 스키마는 **shared**(Build 1·2와 동일 cross-repo 릴리스 게이트).
- 기존 outbox 발행 패턴: shared 이벤트 레코드(`EVENT_TYPE` 상수) JSON 직렬화 → `OutboxEntry` 적재(예 `CommunityBadgeAwardedEvent`).

## 아키텍처

Build 1·2와 동일하게 **`VoteService`의 `@Transactional` 안에서 동기 처리**. 신규 `CollusionDetector`(community-svc)를 upvote 평판 가산 직후 호출한다. 자기투표 가드는 VoteService 진입부.

### 자기 글 투표 금지

`votePost(userId, postId, value)`·`voteAnswer(userId, answerId, value)`의 **검증/레벨게이트 직후, 투표 반영 전**에:
- votePost: `p.getAuthorId()`가 `userId`와 같으면 `ForbiddenException("자기 글에는 투표할 수 없습니다")`.
- voteAnswer: `a.getAuthorId()`가 `userId`와 같으면 동일 예외.
- upvote·downvote **모두** 금지(StackOverflow 모델).

> 부수효과: 자기투표가 원천 차단되므로 STUDENT/TEACHER/CRITIC 자기 수여가 자동 방지된다. VoteService의 "자기투표…Build 3에서 정합" 주석을 "자기투표 금지됨(Build 3)"로 갱신.

### 담합 탐지 (행동 기반, 기록만)

upvote 평판 가산(`reputation.applyVote`) 직후, upvote일 때만:
1. `events.countDistinctUpvotedSourcesByActorToUser(voterId, authorId)` — `reputation_events`에서 `actor_id=voterId AND user_id=authorId AND reason IN ('UPVOTE_Q','UPVOTE_A') AND delta > 0`인 행의 **DISTINCT source_id 수**(= V가 A의 서로 다른 글/답변을 upvote한 개수).
   > **`delta > 0` 필수**: Build 1의 투표변경 역산은 같은 reason(UPVOTE_A 등)의 **음수 delta** 보상 이벤트를 원장에 남긴다. `delta > 0`으로 실제 가산분만 세어 역산 이벤트로 인한 오탐을 배제한다. DISTINCT source_id로 같은 글 재투표(변경→재upvote) 중복도 제거한다.
2. 카운트 ≥ `RepPoints.COLLUSION_UPVOTE_THRESHOLD`(=**5**) 이면 담합 의심:
   - `vote_abuse_suspicions`에 `(actor_id=voterId, target_user_id=authorId, reason='REPEAT_UPVOTE', evidence_count=카운트)` **멱등 저장**: UNIQUE(actor_id, target_user_id, reason)로 (투표자,수혜자,사유)당 1회만 기록. `existsBy…`가 true면 **no-op**(이미 의심 기록됨 — 이벤트도 1회만 발행, evidence_count 갱신 안 함).
   - 신규 기록 시에만 `community.reputation.suspected` outbox 발행(`CommunityReputationSuspectedEvent`).
3. 평판/투표는 **그대로 유지**(회수·차단 없음).

> 임계 T=5(서로 다른 글 5개 이상 반복 upvote)는 보수적 기본값. 상수로 두어 조정 가능. 상호 boosting(A↔B 양방향)은 후속 강화로 남긴다.

### 컴포넌트

**shared 레포** (`devpath-shared`):
- `db/migration/V202607011001__vote_abuse_suspicions.sql` — `vote_abuse_suspicions` 테이블.
- `ai.devpath.shared.event.CommunityReputationSuspectedEvent` — 이벤트 레코드(`EVENT_TYPE = "community.reputation.suspected"`).

**community-svc 레포**, 신규 패키지 `ai.devpath.community.abuse`:
- `VoteAbuseSuspicion` / `VoteAbuseSuspicionId` / `VoteAbuseSuspicionRepository` — suspicion 엔티티(복합/대리키) + `existsByActorIdAndTargetUserIdAndReason`.
- `CollusionDetector` — `@Service`, `checkOnUpvote(long voterId, long authorId, String sourceType, long sourceId)`: 카운트→임계→suspicion 멱등 저장 + outbox 발행.
- `reputation/RepPoints.java`(수정): `COLLUSION_UPVOTE_THRESHOLD = 5` 추가.
- `reputation/ReputationEventRepository.java`(수정): 담합 카운트 쿼리 추가.
- `post/VoteService.java`(수정): 자기투표 가드(votePost·voteAnswer) + upvote 후 `collusionDetector.checkOnUpvote(...)` 호출 + 주석 갱신.

### 스키마 (shared Flyway)

```sql
-- 담합(sockpuppet) 의심 감사 로그. 기록만 — 실제 제재는 후속 moderation.
CREATE TABLE vote_abuse_suspicions (
  id             BIGSERIAL PRIMARY KEY,
  actor_id       BIGINT      NOT NULL,          -- 의심 투표자
  target_user_id BIGINT      NOT NULL,          -- 반복 수혜자
  reason         VARCHAR(32) NOT NULL,          -- REPEAT_UPVOTE (향후 확장)
  evidence_count INT         NOT NULL,          -- 탐지 시점 누적 근거 수
  detected_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_vote_abuse UNIQUE (actor_id, target_user_id, reason)
);
CREATE INDEX idx_vote_abuse_target ON vote_abuse_suspicions (target_user_id, detected_at DESC);
```

> `actor_id`·`target_user_id`는 platform users 논리 참조(FK 없음, 기존 community/reputation 테이블과 동일). UNIQUE로 (투표자,수혜자,사유)별 1회 기록 멱등. `idx_vote_abuse_target`으로 피해자 기준 조회.

## 데이터 흐름

1. 사용자 V가 A의 답변에 upvote → `VoteService.voteAnswer` tx: 자기투표 가드(V≠A 통과) → 투표 반영 → `reputation.applyVote(A, V, ...)` → 배지(Build 2) → `collusionDetector.checkOnUpvote(V, A, "ANSWER", answerId)`.
2. Detector가 V→A upvote 수를 세어 ≥5이면 `vote_abuse_suspicions` 멱등 저장 + `community.reputation.suspected` outbox 적재. 미만이면 no-op.
3. OutboxRelay(기존 스케줄러)가 이벤트를 Kafka로 발행(소비자=후속 moderation).
4. 자기투표(V=A)면 2단계 이전에 403으로 거부 — 투표·평판·배지·탐지 모두 발생 안 함.

## 멱등성 / 정합성

- suspicion 멱등: `vote_abuse_suspicions` UNIQUE(actor_id, target_user_id, reason) + `existsBy…` 선검사. 임계 재도달·초과해도 이미 기록됐으면 **no-op**(새 행 미생성, evidence_count 미갱신, 이벤트 미발행). 최초 임계 도달 1회만 기록·발행.
- 자기투표 가드는 투표 반영 전이라, 차단 시 부작용(평판·배지·탐지) 전무.
- Detector는 호출자 tx 합류(동기) — suspicion·outbox가 투표와 원자적.

## 에러 처리

- 자기투표 → `ForbiddenException`(기존 예외 재사용, 컨트롤러가 403 매핑 — 기존 레벨게이트와 동일).
- Detector의 카운트 쿼리/저장 실패는 호출자 tx 롤백(투표 실패). 단순 count+insert라 실패 요인 적음.

## 테스트 전략 (TDD)

- **자기투표 금지**(MockMvc/서비스): 자기 글 upvote → 403, 자기 답변 downvote → 403, 타인 글 투표는 정상.
- **담합 탐지**(서비스 통합): 동일 V→A upvote를 임계까지 반복 시 `vote_abuse_suspicions` 1건 + `community.reputation.suspected` outbox 1건; 임계 미만이면 미기록; 임계 초과 반복은 멱등(행 1개 유지).
- **회귀**: 기존 평판/배지/투표 테스트 유지. 자기투표로 배지/점수를 얻던 테스트가 있으면 타인 투표자로 보정(테스트 의도 보존).

## 릴리스 게이트 (Build 1·2와 동일)

shared(마이그레이션 + 이벤트 레코드)는 `feat/*→main` 직접 PR 머지에서만 GitHub Packages publish. community-svc는 publish 후 `--refresh-dependencies`로 새 jar 수신 → 이후 Task 진행.

## 리스크 / 후속

- **담합 오탐**: 정당한 반복 upvote(진짜 좋은 답변자)를 의심할 수 있음 — 기록만 하므로 무해, moderation이 사람 검토. 임계·상호성으로 정밀화는 후속.
- **IP/디바이스·신계정 제한·자동 제재**: 신호/모듈 필요 — 후속.
- **자기투표 금지의 기존 테스트 영향**: Build 1/2 테스트 중 동일 subject가 자기 글에 투표하는 케이스가 있으면 보정 필요(플랜에서 회귀로 확인).
