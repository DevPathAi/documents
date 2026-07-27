# 평판 기초 Build 1 — 평판 엔진 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 이미 동작하는 투표·답변 채택 위에, 같은 트랜잭션에서 평판을 가산하는 엔진을 community-svc에 구현한다(총점·태그평판·일일 +40 상한·레벨 게이트).

**Architecture:** 신규 `ReputationService`(community-svc `reputation` 패키지)를 기존 `VoteService`/`AnswerService`의 `@Transactional` 안에서 호출해 동기 가산한다. 스키마는 shared Flyway에 추가하고, 평판은 `user_reputation`(총점)·`user_tag_reputation`(태그별)에 비정규화하며 `reputation_events`(append-only)를 감사·일일상한 산출·역산 근거로 쓴다.

**Tech Stack:** Java 21 · Spring Boot 4.0.7 · Spring Data JPA · PostgreSQL · Flyway(shared) · JUnit 5 + Spring Boot Test(MockMvc). 빌드 `./gradlew`.

**승인 spec:** [2026-06-30-md3-reputation-engine-design.md](../specs/2026-06-30-md3-reputation-engine-design.md)

## Global Constraints

- 백엔드 스택: Java 21 · Spring Boot 4 · Gradle(Kotlin DSL). community-svc 패키지 루트 `ai.devpath.community`.
- 모든 서비스 테스트는 `@ActiveProfiles("test")` + shared jar `classpath:db/migration` Flyway 적용(main은 flyway 비활성). mock 빈은 `@MockitoBean`.
- 브랜치 전략: 각 레포 `develop`에서 작업 브랜치 분기 → develop PR. main 직접 금지(shared 릴리스 PR 제외).
- **shared→서비스 소비 순서(D-6)**: community-svc 테스트는 shared jar의 `db/migration`을 쓴다. 따라서 **Task 1(shared 마이그레이션)은 shared develop→main 릴리스(publish) 후**에야 community-svc가 새 테이블을 소비할 수 있다. Task 2부터는 그 publish 완료 + community-svc `--refresh-dependencies` 후 진행한다.
- 점수 상수(문서 20 §3.1): 질문(POST) upvote **+5**, 답변(ANSWER) upvote **+10**, 답변 채택됨 **+15**, 채택 보너스 **+2**, downvote 받음 **−2**, downvote 행사 **−1**.
- 레벨 임계(문서 20 §3.2): 15 / 125 / 500 / 1000. 이번 빌드는 **15(질문 upvote)·125(답변 downvote)만 강제**.
- 일일 상한: 작성자가 하루(서버 TZ)에 **upvote(+5/+10)로 얻는 합 ≤ +40**(초과분 미지급). 채택·보너스·downvote 패널티는 상한 무관.
- 자기 글 투표 금지·배지·sockpuppet은 **범위 밖**(후속 빌드).

---

## File Structure

**shared 레포** (`devpath-shared`):
- Create: `src/main/resources/db/migration/V202606301001__reputation.sql` — 3개 테이블.

**community-svc 레포** (`devpath-community-svc`), 신규 패키지 `ai.devpath.community.reputation`:
- Create: `ReputationReason.java` — enum(가산 사유).
- Create: `RepPoints.java` — 점수·레벨·상한 상수.
- Create: `ReputationEvent.java` / `ReputationEventRepository.java` — 원장 + 일일합 쿼리.
- Create: `UserReputation.java` / `UserReputationRepository.java` — 총점.
- Create: `UserTagReputation.java` / `UserTagReputationId.java` / `UserTagReputationRepository.java` — 태그별.
- Create: `ReputationService.java` — applyVote/applyAcceptance(가산·역산·상한).
- Create: `ReputationQueryService.java` — reputationOf(레벨 게이트용).
- Modify: `post/VoteService.java` — old value 포착 + 레벨 게이트 + applyVote 호출.
- Modify: `post/AnswerService.java` — 채택 중복 가드 + applyAcceptance 호출.
- Test: `reputation/ReputationServiceTest.java`(서비스 통합) · `reputation/VoteGateMockMvcTest.java`(레벨 게이트) · `post/AcceptReputationTest.java`(채택).

> `reputation` 패키지로 분리해 post 도메인과 평판 도메인의 경계를 둔다. `ReputationService`는 post 엔티티 리포지토리(작성자·태그 조회)를 주입받지 않고, 호출자(VoteService/AnswerService)가 이미 로드한 값(authorId·tagIds)을 **인자로 전달**한다 → 평판 로직이 post 내부구조에 결합되지 않음.

---

## Task 1: shared 평판 스키마 (Flyway)

**레포:** `devpath-shared` · 작업 브랜치 `feat/reputation-schema`(develop 분기).

**Files:**
- Create: `src/main/resources/db/migration/V202606301001__reputation.sql`
- Test: 기존 `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`(신규 작성 불필요 — 전체 마이그레이션 적용 검증).

**Interfaces:**
- Produces: 테이블 `reputation_events`·`user_reputation`·`user_tag_reputation`(아래 컬럼). community-svc 엔티티가 이 스키마에 매핑.

- [ ] **Step 1: 마이그레이션 작성**

Create `src/main/resources/db/migration/V202606301001__reputation.sql`:
```sql
-- 평판 원장(append-only): 감사 + 일일상한 산출 + 투표변경 역산 근거.
CREATE TABLE reputation_events (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT      NOT NULL,            -- 평판 귀속 대상(수혜자)
  actor_id    BIGINT,                          -- 유발자(투표자/채택자) — 역산 매칭용, 시스템이면 NULL
  delta       INT         NOT NULL,            -- 실제 반영된 값(상한 적용 후)
  reason      VARCHAR(32) NOT NULL,            -- UPVOTE_Q|UPVOTE_A|ACCEPTED|ACCEPT_BONUS|DOWNVOTE_RECEIVED|DOWNVOTE_CAST
  source_type VARCHAR(16) NOT NULL,            -- POST|ANSWER
  source_id   BIGINT      NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_repevent_user_day ON reputation_events (user_id, reason, created_at);
CREATE INDEX idx_repevent_actor_src ON reputation_events (actor_id, source_type, source_id);

-- 총점(비정규화, 빠른 읽기/레벨 게이트).
CREATE TABLE user_reputation (
  user_id    BIGINT PRIMARY KEY,
  total      INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 태그별 평판.
CREATE TABLE user_tag_reputation (
  user_id BIGINT NOT NULL,
  tag_id  BIGINT NOT NULL,
  score   INT NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, tag_id)
);
```
> `actor_id`는 spec 스키마의 구현 보강 — 투표 변경 시 (투표자, 대상)별 이전 효과를 정확히 찾아 역산하기 위함. `tag_id`는 events에 두지 않고 `user_tag_reputation`만 갱신(원장은 총점 사유 기록, 태그는 집계 테이블이 SoT).

- [ ] **Step 2: 마이그레이션 적용 테스트 실행(실패→통과 확인)**

Run: `./gradlew test --tests "*FlywayMigrationTest*"`
Expected: PASS (3개 테이블이 깨끗한 DB에 적용됨). 실패 시 SQL 문법/순서 점검.

- [ ] **Step 3: 커밋**
```bash
git add src/main/resources/db/migration/V202606301001__reputation.sql
git commit -m "feat(schema): reputation 테이블(events/user_reputation/user_tag_reputation)"
```

- [ ] **Step 4: 릴리스 게이트(필수)**

`feat/reputation-schema` → `develop` PR 머지 후, **`develop` → `main` 릴리스 PR 머지**로 GitHub Packages publish를 트리거한다(shared는 main push에서만 publish). community-svc는 이후 캐시 purge + `--refresh-dependencies`로 새 jar를 받아야 Task 2~를 진행할 수 있다.

---

## Task 2: community-svc 평판 도메인(상수·enum·엔티티·리포지토리)

**레포:** `devpath-community-svc` · 작업 브랜치 `feat/reputation-engine`(develop 분기). 선행: Task 1 publish 완료.

**Files:**
- Create: `src/main/java/ai/devpath/community/reputation/ReputationReason.java`
- Create: `src/main/java/ai/devpath/community/reputation/RepPoints.java`
- Create: `src/main/java/ai/devpath/community/reputation/ReputationEvent.java`
- Create: `src/main/java/ai/devpath/community/reputation/ReputationEventRepository.java`
- Create: `src/main/java/ai/devpath/community/reputation/UserReputation.java`
- Create: `src/main/java/ai/devpath/community/reputation/UserReputationRepository.java`
- Create: `src/main/java/ai/devpath/community/reputation/UserTagReputation.java`
- Create: `src/main/java/ai/devpath/community/reputation/UserTagReputationId.java`
- Create: `src/main/java/ai/devpath/community/reputation/UserTagReputationRepository.java`

**Interfaces:**
- Produces: `RepPoints`(상수), `ReputationReason`(enum), 3개 엔티티 + 리포지토리. Task 3~5가 소비.

- [ ] **Step 1: enum + 상수**

Create `ReputationReason.java`:
```java
package ai.devpath.community.reputation;

public enum ReputationReason {
  UPVOTE_Q, UPVOTE_A, ACCEPTED, ACCEPT_BONUS, DOWNVOTE_RECEIVED, DOWNVOTE_CAST
}
```

Create `RepPoints.java`:
```java
package ai.devpath.community.reputation;

/** 평판 점수·레벨·일일상한 상수(문서 20 §3). */
public final class RepPoints {
  private RepPoints() {}

  public static final int UPVOTE_QUESTION = 5;
  public static final int UPVOTE_ANSWER = 10;
  public static final int ACCEPTED = 15;
  public static final int ACCEPT_BONUS = 2;
  public static final int DOWNVOTE_RECEIVED = -2;
  public static final int DOWNVOTE_CAST = -1;

  /** 하루 upvote 획득 상한(초과분 미지급). */
  public static final int DAILY_UPVOTE_CAP = 40;

  // 레벨 임계(이번 빌드는 15·125만 게이트 강제).
  public static final int LVL_UPVOTE_QUESTION = 15;
  public static final int LVL_DOWNVOTE_ANSWER = 125;
  public static final int LVL_EDIT_SUGGEST = 500;
  public static final int LVL_MODERATION = 1000;
}
```

- [ ] **Step 2: ReputationEvent 엔티티 + 리포지토리**

Create `ReputationEvent.java`:
```java
package ai.devpath.community.reputation;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "reputation_events")
public class ReputationEvent {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
  @Column(name = "user_id", nullable = false) private Long userId;
  @Column(name = "actor_id") private Long actorId;
  @Column(nullable = false) private int delta;
  @Column(nullable = false, length = 32) private String reason;
  @Column(name = "source_type", nullable = false, length = 16) private String sourceType;
  @Column(name = "source_id", nullable = false) private Long sourceId;
  @Column(name = "created_at", insertable = false, updatable = false) private Instant createdAt;

  public ReputationEvent() {}
  public ReputationEvent(Long userId, Long actorId, int delta, ReputationReason reason,
      String sourceType, Long sourceId) {
    this.userId = userId; this.actorId = actorId; this.delta = delta;
    this.reason = reason.name(); this.sourceType = sourceType; this.sourceId = sourceId;
  }
  public Long getId() { return id; }
  public Long getUserId() { return userId; }
  public Long getActorId() { return actorId; }
  public int getDelta() { return delta; }
  public String getReason() { return reason; }
  public String getSourceType() { return sourceType; }
  public Long getSourceId() { return sourceId; }
  public Instant getCreatedAt() { return createdAt; }
}
```

Create `ReputationEventRepository.java`:
```java
package ai.devpath.community.reputation;

import java.time.Instant;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ReputationEventRepository extends JpaRepository<ReputationEvent, Long> {

  /** (투표자, 대상)에 대한 이 사용자의 기존 이벤트 — 투표 변경 역산용. */
  List<ReputationEvent> findByActorIdAndSourceTypeAndSourceId(Long actorId, String sourceType, Long sourceId);

  /** 오늘(>=since) 작성자가 upvote로 얻은 합 — 일일상한 산출. */
  @Query("""
      select coalesce(sum(e.delta), 0) from ReputationEvent e
      where e.userId = :userId and e.reason in ('UPVOTE_Q','UPVOTE_A') and e.createdAt >= :since
      """)
  int sumUpvoteGainSince(@Param("userId") Long userId, @Param("since") Instant since);
}
```

- [ ] **Step 3: UserReputation 엔티티 + 리포지토리**

Create `UserReputation.java`:
```java
package ai.devpath.community.reputation;

import jakarta.persistence.*;

@Entity
@Table(name = "user_reputation")
public class UserReputation {
  @Id @Column(name = "user_id") private Long userId;
  @Column(nullable = false) private int total = 0;

  public UserReputation() {}
  public UserReputation(Long userId) { this.userId = userId; }
  public Long getUserId() { return userId; }
  public int getTotal() { return total; }
  public void setTotal(int total) { this.total = total; }
  public void add(int delta) { this.total += delta; }
}
```

Create `UserReputationRepository.java`:
```java
package ai.devpath.community.reputation;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserReputationRepository extends JpaRepository<UserReputation, Long> {
  Optional<UserReputation> findByUserId(Long userId);
}
```

- [ ] **Step 4: UserTagReputation 엔티티(복합키) + 리포지토리**

Create `UserTagReputationId.java`:
```java
package ai.devpath.community.reputation;

import java.io.Serializable;
import java.util.Objects;

public class UserTagReputationId implements Serializable {
  private Long userId;
  private Long tagId;
  public UserTagReputationId() {}
  public UserTagReputationId(Long userId, Long tagId) { this.userId = userId; this.tagId = tagId; }
  @Override public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof UserTagReputationId that)) return false;
    return Objects.equals(userId, that.userId) && Objects.equals(tagId, that.tagId);
  }
  @Override public int hashCode() { return Objects.hash(userId, tagId); }
}
```

Create `UserTagReputation.java`:
```java
package ai.devpath.community.reputation;

import jakarta.persistence.*;

@Entity
@Table(name = "user_tag_reputation")
@IdClass(UserTagReputationId.class)
public class UserTagReputation {
  @Id @Column(name = "user_id") private Long userId;
  @Id @Column(name = "tag_id") private Long tagId;
  @Column(nullable = false) private int score = 0;

  public UserTagReputation() {}
  public UserTagReputation(Long userId, Long tagId) { this.userId = userId; this.tagId = tagId; }
  public Long getUserId() { return userId; }
  public Long getTagId() { return tagId; }
  public int getScore() { return score; }
  public void add(int delta) { this.score += delta; }
}
```

Create `UserTagReputationRepository.java`:
```java
package ai.devpath.community.reputation;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserTagReputationRepository extends JpaRepository<UserTagReputation, UserTagReputationId> {
  Optional<UserTagReputation> findByUserIdAndTagId(Long userId, Long tagId);
}
```

- [ ] **Step 5: 컴파일 확인**

Run: `./gradlew compileJava`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 6: 커밋**
```bash
git add src/main/java/ai/devpath/community/reputation/
git commit -m "feat(reputation): 평판 도메인 엔티티·리포지토리·상수"
```

---

## Task 3: ReputationService — applyVote(가산·역산·일일상한)

**Files:**
- Create: `src/main/java/ai/devpath/community/reputation/ReputationService.java`
- Test: `src/test/java/ai/devpath/community/reputation/ReputationServiceTest.java`

**Interfaces:**
- Consumes: Task 2 리포지토리·`RepPoints`·`ReputationReason`.
- Produces:
  - `void applyVote(long authorId, long voterId, String sourceType, long sourceId, int oldValue, int newValue, List<Long> tagIds)`
  - `void applyAcceptance(long answerAuthorId, long questionAuthorId, String sourceType, long sourceId, List<Long> tagIds)` (Task 4에서 사용)
  - `int reputationOf(long userId)`(편의 — Task 5 Query 서비스가 위임 가능)

- [ ] **Step 1: 실패 테스트 작성(upvote 가산 + 태그)**

Create `ReputationServiceTest.java`:
```java
package ai.devpath.community.reputation;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class ReputationServiceTest {
  @Autowired ReputationService svc;
  @Autowired UserReputationRepository reputations;
  @Autowired UserTagReputationRepository tagReputations;

  @Test
  void answerUpvoteGrantsTenToAuthorAndTags() {
    long author = 1001, voter = 1002, answerId = 5001;
    svc.applyVote(author, voter, "ANSWER", answerId, 0, 1, List.of(7L, 8L));

    assertThat(reputations.findByUserId(author).orElseThrow().getTotal()).isEqualTo(10);
    assertThat(tagReputations.findByUserIdAndTagId(author, 7L).orElseThrow().getScore()).isEqualTo(10);
    assertThat(tagReputations.findByUserIdAndTagId(author, 8L).orElseThrow().getScore()).isEqualTo(10);
  }

  @Test
  void questionUpvoteGrantsFive() {
    svc.applyVote(2001, 2002, "POST", 6001, 0, 1, List.of());
    assertThat(reputations.findByUserId(2001L).orElseThrow().getTotal()).isEqualTo(5);
  }
}
```

- [ ] **Step 2: 실패 확인**

Run: `./gradlew test --tests "*ReputationServiceTest*"`
Expected: FAIL (`ReputationService` 미존재 → 컴파일 실패).

- [ ] **Step 3: ReputationService 구현**

Create `ReputationService.java`:
```java
package ai.devpath.community.reputation;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** 평판 가산 엔진. 호출자(VoteService/AnswerService)의 트랜잭션에 합류한다. */
@Service
public class ReputationService {
  private final ReputationEventRepository events;
  private final UserReputationRepository reputations;
  private final UserTagReputationRepository tagReputations;

  public ReputationService(ReputationEventRepository events, UserReputationRepository reputations,
      UserTagReputationRepository tagReputations) {
    this.events = events; this.reputations = reputations; this.tagReputations = tagReputations;
  }

  /** 투표 1건(생성/변경)의 평판 효과를 반영한다. oldValue/newValue ∈ {-1,0,1}. */
  @Transactional
  public void applyVote(long authorId, long voterId, String sourceType, long sourceId,
      int oldValue, int newValue, List<Long> tagIds) {
    if (oldValue == newValue) return;
    reverseVote(voterId, sourceType, sourceId, tagIds);   // 이전 효과 역산
    applyNewVote(authorId, voterId, sourceType, sourceId, newValue, tagIds);
  }

  private void reverseVote(long voterId, String sourceType, long sourceId, List<Long> tagIds) {
    List<ReputationEvent> prior =
        events.findByActorIdAndSourceTypeAndSourceId(voterId, sourceType, sourceId);
    for (ReputationEvent e : prior) {
      // 보상(역) 이벤트로 총점/태그 환원. 같은 사유로 -delta.
      int back = -e.getDelta();
      addTotal(e.getUserId(), back);
      // 작성자(수혜자) 이벤트면 태그도 환원(행사자 비용 DOWNVOTE_CAST는 태그 무관).
      if (!ReputationReason.DOWNVOTE_CAST.name().equals(e.getReason())) {
        for (Long tagId : tagIds) addTag(e.getUserId(), tagId, back);
      }
      events.save(new ReputationEvent(e.getUserId(), voterId, back,
          ReputationReason.valueOf(e.getReason()), sourceType, sourceId));
    }
  }

  private void applyNewVote(long authorId, long voterId, String sourceType, long sourceId,
      int newValue, List<Long> tagIds) {
    if (newValue == 1) {
      ReputationReason reason = "ANSWER".equals(sourceType)
          ? ReputationReason.UPVOTE_A : ReputationReason.UPVOTE_Q;
      int nominal = "ANSWER".equals(sourceType) ? RepPoints.UPVOTE_ANSWER : RepPoints.UPVOTE_QUESTION;
      int granted = capDailyUpvote(authorId, nominal);
      if (granted != 0) {
        addTotal(authorId, granted);
        for (Long tagId : tagIds) addTag(authorId, tagId, granted);
        events.save(new ReputationEvent(authorId, voterId, granted, reason, sourceType, sourceId));
      }
    } else if (newValue == -1) {
      // 작성자: downvote 받음 -2
      addTotal(authorId, RepPoints.DOWNVOTE_RECEIVED);
      for (Long tagId : tagIds) addTag(authorId, tagId, RepPoints.DOWNVOTE_RECEIVED);
      events.save(new ReputationEvent(authorId, voterId, RepPoints.DOWNVOTE_RECEIVED,
          ReputationReason.DOWNVOTE_RECEIVED, sourceType, sourceId));
      // 행사자: downvote 비용 -1 (태그 무관)
      addTotal(voterId, RepPoints.DOWNVOTE_CAST);
      events.save(new ReputationEvent(voterId, voterId, RepPoints.DOWNVOTE_CAST,
          ReputationReason.DOWNVOTE_CAST, sourceType, sourceId));
    }
  }

  /** upvote 명목치를, 작성자의 오늘자 upvote 획득합이 40을 넘지 않도록 클램프. */
  private int capDailyUpvote(long authorId, int nominal) {
    Instant since = LocalDate.now(ZoneId.systemDefault()).atStartOfDay(ZoneId.systemDefault()).toInstant();
    int todays = events.sumUpvoteGainSince(authorId, since);
    int room = RepPoints.DAILY_UPVOTE_CAP - todays;
    if (room <= 0) return 0;
    return Math.min(nominal, room);
  }

  @Transactional
  public void applyAcceptance(long answerAuthorId, long questionAuthorId, String sourceType,
      long sourceId, List<Long> tagIds) {
    addTotal(answerAuthorId, RepPoints.ACCEPTED);
    for (Long tagId : tagIds) addTag(answerAuthorId, tagId, RepPoints.ACCEPTED);
    events.save(new ReputationEvent(answerAuthorId, questionAuthorId, RepPoints.ACCEPTED,
        ReputationReason.ACCEPTED, sourceType, sourceId));

    addTotal(questionAuthorId, RepPoints.ACCEPT_BONUS);
    for (Long tagId : tagIds) addTag(questionAuthorId, tagId, RepPoints.ACCEPT_BONUS);
    events.save(new ReputationEvent(questionAuthorId, questionAuthorId, RepPoints.ACCEPT_BONUS,
        ReputationReason.ACCEPT_BONUS, sourceType, sourceId));
  }

  public int reputationOf(long userId) {
    return reputations.findByUserId(userId).map(UserReputation::getTotal).orElse(0);
  }

  private void addTotal(long userId, int delta) {
    UserReputation r = reputations.findByUserId(userId).orElseGet(() -> new UserReputation(userId));
    r.add(delta);
    reputations.save(r);
  }

  private void addTag(long userId, long tagId, int delta) {
    UserTagReputation t = tagReputations.findByUserIdAndTagId(userId, tagId)
        .orElseGet(() -> new UserTagReputation(userId, tagId));
    t.add(delta);
    tagReputations.save(t);
  }
}
```

- [ ] **Step 4: 통과 확인**

Run: `./gradlew test --tests "*ReputationServiceTest*"`
Expected: PASS (2 테스트).

- [ ] **Step 5: 역산·상한·downvote 테스트 추가**

Append to `ReputationServiceTest.java`(메서드 추가):
```java
  @Test
  void changingUpvoteToDownvoteReversesAndAppliesPenalty() {
    long author = 3001, voter = 3002, answerId = 7001;
    svc.applyVote(author, voter, "ANSWER", answerId, 0, 1, List.of(9L));   // +10
    svc.applyVote(author, voter, "ANSWER", answerId, 1, -1, List.of(9L));  // -10 역산, -2 받음
    assertThat(reputations.findByUserId(author).orElseThrow().getTotal()).isEqualTo(-2);
    assertThat(tagReputations.findByUserIdAndTagId(author, 9L).orElseThrow().getScore()).isEqualTo(-2);
    assertThat(reputations.findByUserId(voter).orElseThrow().getTotal()).isEqualTo(-1); // 행사 비용
  }

  @Test
  void dailyUpvoteGainCappedAtForty() {
    long author = 4001;
    // 답변 upvote +10 × 5 = 50 → 40으로 클램프(서로 다른 답변/투표자).
    for (int i = 0; i < 5; i++) {
      svc.applyVote(author, 5000 + i, "ANSWER", 8000 + i, 0, 1, List.of());
    }
    assertThat(reputations.findByUserId(author).orElseThrow().getTotal()).isEqualTo(40);
  }

  @Test
  void acceptanceExemptFromDailyCap() {
    long author = 4101;
    for (int i = 0; i < 5; i++) svc.applyVote(author, 5100 + i, "ANSWER", 8100 + i, 0, 1, List.of()); // 40
    svc.applyAcceptance(author, 4102, "ANSWER", 8200, List.of()); // +15 (상한 무관)
    assertThat(reputations.findByUserId(author).orElseThrow().getTotal()).isEqualTo(55);
  }
```

- [ ] **Step 6: 통과 확인 + 커밋**

Run: `./gradlew test --tests "*ReputationServiceTest*"`
Expected: PASS (5 테스트).
```bash
git add src/main/java/ai/devpath/community/reputation/ReputationService.java \
        src/test/java/ai/devpath/community/reputation/ReputationServiceTest.java
git commit -m "feat(reputation): applyVote/applyAcceptance 가산·역산·일일상한"
```

---

## Task 4: 채택 평판 연결 + 중복 가드 (AnswerService)

**Files:**
- Modify: `src/main/java/ai/devpath/community/post/AnswerService.java`
- Test: `src/test/java/ai/devpath/community/post/AcceptReputationTest.java`

**Interfaces:**
- Consumes: `ReputationService.applyAcceptance(...)`, `CommunityPostTagRepository.findByPostId(Long)`.

- [ ] **Step 1: 실패 테스트(채택 +15/+2, 재채택 no-op)**

Create `AcceptReputationTest.java`:
```java
package ai.devpath.community.post;

import static org.assertj.core.api.Assertions.assertThat;

import ai.devpath.community.post.dto.CreateAnswerRequest;
import ai.devpath.community.post.dto.CreateQuestionRequest;
import ai.devpath.community.reputation.UserReputationRepository;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class AcceptReputationTest {
  @Autowired QuestionService questionService;
  @Autowired AnswerService answerService;
  @Autowired UserReputationRepository reputations;

  @Test
  void acceptGrantsFifteenToAnswererAndTwoToAsker() {
    long asker = 9001, answerer = 9002;
    var q = questionService.create(asker, new CreateQuestionRequest("t", "b", List.of()));
    var a = answerService.add(answerer, q.id(), new CreateAnswerRequest("ans"));

    answerService.accept(asker, a.id());
    assertThat(reputations.findByUserId(answerer).orElseThrow().getTotal()).isEqualTo(15);
    assertThat(reputations.findByUserId(asker).orElseThrow().getTotal()).isEqualTo(2);

    // 재채택 호출 → no-op(중복 가산 없음)
    answerService.accept(asker, a.id());
    assertThat(reputations.findByUserId(answerer).orElseThrow().getTotal()).isEqualTo(15);
  }
}
```
> 시그니처 검증됨(plan 작성 시 실제 dto 확인): `CreateQuestionRequest(String title, String bodyMd, List<String> tags)` · `CreateAnswerRequest(String bodyMd)` · `QuestionDetailView`/`AnswerView`는 record로 `.id()` 접근자 보유.

- [ ] **Step 2: 실패 확인**

Run: `./gradlew test --tests "*AcceptReputationTest*"`
Expected: FAIL (현재 accept는 평판 미부여).

- [ ] **Step 3: AnswerService 수정(가드 + 가산)**

Modify `AnswerService.java`:
- 생성자에 `ReputationService` + `CommunityPostTagRepository` 주입.
- `accept(...)`를 아래로 교체:
```java
  @Transactional
  public void accept(long userId, long answerId) {
    CommunityAnswer a = answers.findById(answerId)
        .orElseThrow(() -> new NotFoundException("answer " + answerId));
    if (a.isAccepted()) return;   // 중복 채택 가드(중복 가산 방지)
    CommunityQuestion q = questions.findById(a.getQuestionId())
        .orElseThrow(() -> new NotFoundException("question " + a.getQuestionId()));
    CommunityPost p = posts.findById(q.getPostId())
        .orElseThrow(() -> new NotFoundException("post " + q.getPostId()));
    if (p.getAuthorId() == null || p.getAuthorId() != userId) {
      throw new ForbiddenException("only question author can accept");
    }
    a.setAccepted(true);
    answers.save(a);
    q.setSolved(true);
    q.setAcceptedAnswerId(answerId);
    questions.save(q);

    List<Long> tagIds = postTags.findByPostId(q.getPostId()).stream()
        .map(CommunityPostTag::getTagId).toList();
    reputation.applyAcceptance(a.getAuthorId(), p.getAuthorId(), "ANSWER", answerId, tagIds);
  }
```
> 필드 추가: `private final ReputationService reputation;` `private final CommunityPostTagRepository postTags;` + 생성자 파라미터/대입 + `import ai.devpath.community.reputation.ReputationService;` `import java.util.List;`.

- [ ] **Step 4: 통과 확인 + 커밋**

Run: `./gradlew test --tests "*AcceptReputationTest*"`
Expected: PASS.
```bash
git add src/main/java/ai/devpath/community/post/AnswerService.java \
        src/test/java/ai/devpath/community/post/AcceptReputationTest.java
git commit -m "feat(reputation): 채택 시 +15/+2 가산 + 중복 채택 가드"
```

---

## Task 5: 투표 평판 연결 + 레벨 게이트 (VoteService)

**Files:**
- Modify: `src/main/java/ai/devpath/community/post/VoteService.java`
- Test: `src/test/java/ai/devpath/community/post/VoteGateMockMvcTest.java`

**Interfaces:**
- Consumes: `ReputationService.applyVote/reputationOf`, `CommunityPostTagRepository`, `CommunityAnswerRepository`, `CommunityQuestionRepository`, `CommunityPostRepository`, `RepPoints`.

- [ ] **Step 1: 실패 테스트(레벨 게이트 경계)**

Create `VoteGateMockMvcTest.java`:
```java
package ai.devpath.community.post;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import ai.devpath.community.reputation.ReputationService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class VoteGateMockMvcTest {
  @Autowired MockMvc mvc;
  @Autowired ReputationService reputation;

  private long createQuestion(String subject) throws Exception {
    String body = mvc.perform(post("/community/questions").with(jwt().jwt(j -> j.subject(subject)))
        .contentType("application/json").content("{\"title\":\"g\",\"bodyMd\":\"b\",\"tags\":[]}"))
        .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
    return com.jayway.jsonpath.JsonPath.parse(body).read("$.id", Long.class);
  }

  @Test
  void upvoteQuestionRequiresReputation15() throws Exception {
    long qid = createQuestion("8001");
    // 평판 0인 사용자(8002)가 질문 upvote → 거부(403)
    mvc.perform(post("/community/posts/" + qid + "/vote").with(jwt().jwt(j -> j.subject("8002")))
        .contentType("application/json").content("{\"value\":1}"))
        .andExpect(status().isForbidden());
    // 평판 15 부여 후 → 허용(200)
    reputation.applyAcceptance(8002L, 9999L, "ANSWER", 1L, java.util.List.of()); // +15
    mvc.perform(post("/community/posts/" + qid + "/vote").with(jwt().jwt(j -> j.subject("8002")))
        .contentType("application/json").content("{\"value\":1}"))
        .andExpect(status().isOk());
  }
}
```

- [ ] **Step 2: 실패 확인**

Run: `./gradlew test --tests "*VoteGateMockMvcTest*"`
Expected: FAIL (게이트 미구현 → 첫 호출이 200).

- [ ] **Step 3: VoteService 수정(게이트 + old value 포착 + applyVote)**

Modify `VoteService.java` — 전체를 아래로 교체:
```java
package ai.devpath.community.post;

import ai.devpath.community.reputation.RepPoints;
import ai.devpath.community.reputation.ReputationService;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class VoteService {
  private final CommunityVoteRepository votes;
  private final CommunityPostRepository posts;
  private final CommunityAnswerRepository answers;
  private final CommunityQuestionRepository questions;
  private final CommunityPostTagRepository postTags;
  private final ReputationService reputation;

  public VoteService(CommunityVoteRepository votes, CommunityPostRepository posts,
      CommunityAnswerRepository answers, CommunityQuestionRepository questions,
      CommunityPostTagRepository postTags, ReputationService reputation) {
    this.votes = votes; this.posts = posts; this.answers = answers;
    this.questions = questions; this.postTags = postTags; this.reputation = reputation;
  }

  @Transactional
  public void votePost(long userId, long postId, int value) {
    validate(value);
    CommunityPost p = posts.findById(postId).orElseThrow(() -> new NotFoundException("post " + postId));
    // 게이트: 질문 upvote는 평판 15 이상
    if (value == 1 && reputation.reputationOf(userId) < RepPoints.LVL_UPVOTE_QUESTION) {
      throw new ForbiddenException("질문 upvote는 평판 " + RepPoints.LVL_UPVOTE_QUESTION + " 이상 필요");
    }
    int oldValue = currentValue(userId, "POST", postId);
    upsert(userId, "POST", postId, (short) value);
    refreshPostCounts(p, postId);
    List<Long> tagIds = postTags.findByPostId(postId).stream().map(CommunityPostTag::getTagId).toList();
    reputation.applyVote(p.getAuthorId(), userId, "POST", postId, oldValue, value, tagIds);
  }

  @Transactional
  public void voteAnswer(long userId, long answerId, int value) {
    validate(value);
    CommunityAnswer a = answers.findById(answerId)
        .orElseThrow(() -> new NotFoundException("answer " + answerId));
    // 게이트: 답변 downvote는 평판 125 이상
    if (value == -1 && reputation.reputationOf(userId) < RepPoints.LVL_DOWNVOTE_ANSWER) {
      throw new ForbiddenException("답변 downvote는 평판 " + RepPoints.LVL_DOWNVOTE_ANSWER + " 이상 필요");
    }
    int oldValue = currentValue(userId, "ANSWER", answerId);
    upsert(userId, "ANSWER", answerId, (short) value);
    a.setUpvoteCount(votes.countByTargetTypeAndTargetIdAndValue("ANSWER", answerId, (short) 1));
    answers.save(a);
    CommunityQuestion q = questions.findById(a.getQuestionId())
        .orElseThrow(() -> new NotFoundException("question " + a.getQuestionId()));
    List<Long> tagIds = postTags.findByPostId(q.getPostId()).stream()
        .map(CommunityPostTag::getTagId).toList();
    reputation.applyVote(a.getAuthorId(), userId, "ANSWER", answerId, oldValue, value, tagIds);
  }

  private int currentValue(long userId, String type, long targetId) {
    return votes.findByUserIdAndTargetTypeAndTargetId(userId, type, targetId)
        .map(v -> (int) v.getValue()).orElse(0);
  }

  private void refreshPostCounts(CommunityPost p, long postId) {
    p.setUpvoteCount(votes.countByTargetTypeAndTargetIdAndValue("POST", postId, (short) 1));
    p.setDownvoteCount(votes.countByTargetTypeAndTargetIdAndValue("POST", postId, (short) -1));
    posts.save(p);
  }

  private void upsert(long userId, String type, long targetId, short value) {
    CommunityVote v = votes.findByUserIdAndTargetTypeAndTargetId(userId, type, targetId)
        .orElseGet(() -> {
          CommunityVote nv = new CommunityVote();
          nv.setUserId(userId); nv.setTargetType(type); nv.setTargetId(targetId);
          return nv;
        });
    v.setValue(value);
    votes.save(v);
  }

  private void validate(int value) {
    if (value != 1 && value != -1) throw new InvalidVoteException("value must be 1 or -1");
  }
}
```
> `currentValue`는 upsert **전에** 호출해 old value를 포착(upsert가 덮어쓰므로 순서 중요). 기존 `VoteMockMvcTest`(upvoteCount 누적·멱등·잘못된 값 400)는 회귀로 유지된다 — 단 게이트 추가로 평판 0인 투표자가 질문 upvote 시 403이 되므로, 그 테스트가 평판 없는 subject로 upvote하면 깨질 수 있다. **Step 5에서 회귀 확인 후 필요한 경우 기존 테스트의 투표자에게 평판을 부여하도록 보정**한다(테스트 의도 보존).

- [ ] **Step 4: 게이트 테스트 통과 확인**

Run: `./gradlew test --tests "*VoteGateMockMvcTest*"`
Expected: PASS.

- [ ] **Step 5: 전체 회귀 확인 + (필요시) 기존 VoteMockMvcTest 보정**

Run: `./gradlew test`
Expected: BUILD SUCCESSFUL. 만약 `VoteMockMvcTest.upvotePostAccumulates...`가 게이트(403)로 실패하면, 해당 테스트의 upvote 투표자(subject 301/302)에게 사전 평판 15를 부여하도록 보정한다(예: 테스트에 `@Autowired ReputationService` 주입 후 `reputation.applyAcceptance(301L, 9999L, "ANSWER", 1L, List.of())`). 평판 가산이 upvoteCount 집계에 영향 없음을 함께 확인(집계는 votes count 기반).

- [ ] **Step 6: 커밋**
```bash
git add src/main/java/ai/devpath/community/post/VoteService.java \
        src/test/java/ai/devpath/community/post/VoteGateMockMvcTest.java \
        src/test/java/ai/devpath/community/post/VoteMockMvcTest.java
git commit -m "feat(reputation): 투표 평판 가산 연결 + 레벨 게이트(15/125)"
```

---

## 검증 기준 (Definition of Done)

- [ ] shared `V202606301001__reputation.sql` 적용 — `FlywayMigrationTest` PASS, develop→main 릴리스 publish 완료.
- [ ] community-svc `./gradlew test` 전체 PASS(신규 ReputationServiceTest·AcceptReputationTest·VoteGateMockMvcTest + 기존 회귀).
- [ ] upvote 가산(+5/+10)·태그 점수·투표 변경 역산·일일 +40 상한(채택 제외)·채택 +15/+2·재채택 no-op·downvote(−2/−1)·레벨 게이트(15/125 경계) 검증됨.
- [ ] 배지·sockpuppet·자기 글 투표 금지 **미포함**(후속 빌드).

## 리스크 / 후속

- **일일상한 정확도**: events 합산 기반 — 투표 변경 역산이 같은 날 합을 줄이므로 재가산 시 일관. 상한은 명목치 클램프(이미 today≥40이면 0 지급).
- **태그 변경**: 투표 후 글 태그가 바뀌면 역산 시 현재 태그 기준으로 환원되어 태그 점수 잔차 가능 — Build 1 범위 밖(태그는 통상 고정). 후속에서 events에 tag 기록 고려.
- **board_type 미구분**: 모든 POST upvote를 +5로 처리(자유게시판 무평판·인기글 +20은 문서 20이나 후속 빌드).
- **Build 2**: Bronze 배지 9종 자동 수여(평판/이벤트 트리거). **Build 3**: sockpuppet 탐지 + 자기 글 투표 금지.
