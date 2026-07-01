# 평판 기초 Build 3 — 남용 방지(자기투표 금지 + 담합 탐지) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** community-svc에 (1) 자기 글 투표 하드 차단과 (2) `reputation_events` 기반 행동 담합 탐지(기록만)를 추가한다.

**Architecture:** Build 1·2와 동일하게 `VoteService`의 `@Transactional` 안에서 동기 처리. 자기투표 가드는 투표 진입부(레벨게이트 앞), 담합 탐지는 upvote 평판 가산 직후 신규 `CollusionDetector` 호출. suspicion 스키마·이벤트는 shared.

**Tech Stack:** Java 21 · Spring Boot 4.0.7 · Spring Data JPA · PostgreSQL · Flyway(shared) · Jackson 3(`tools.jackson`) · JUnit 5 + Spring Boot Test(MockMvc). 빌드 `./gradlew`.

**승인 spec:** [2026-07-01-md3-antiabuse-build3-design.md](../specs/2026-07-01-md3-antiabuse-build3-design.md)

## Global Constraints

- 백엔드 스택: Java 21 · Spring Boot 4 · Gradle(Kotlin DSL). community-svc 패키지 루트 `ai.devpath.community`.
- 모든 서비스 테스트는 `@ActiveProfiles("test")` + shared jar `classpath:db/migration` Flyway 적용. 테스트 DB `devpath_citest`(localhost:5432, docker compose `postgres`). 로컬 DB가 Flyway 이력과 불일치하면 `docker exec devpath-local-postgres-1 psql -U devpath -d devpath_citest -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO devpath; GRANT ALL ON SCHEMA public TO public;"` 후 재적용.
- 도구는 **Bash만**(PowerShell 금지). 로컬 postgres가 꺼져 있으면 `cd devpath-shared && docker compose up -d postgres`로 기동.
- 브랜치: 각 레포 `develop`에서 작업 브랜치 분기 → develop PR. main 직접 금지(shared 릴리스 PR 제외).
- **릴리스 게이트**: Task 1(shared 마이그레이션+이벤트)은 `feat/*→main` PR 머지(publish) 후에야 community-svc(Task 2~)가 소비. shared 버전 `0.0.1-SNAPSHOT`, main push에서만 publish. community-svc는 publish 후 `./gradlew compileJava --refresh-dependencies`. **jar 검증은 내용 grep**(`unzip -l <jar> | grep V202607011001`)으로.
- 담합 임계: `RepPoints.COLLUSION_UPVOTE_THRESHOLD = 5`. 사유 문자열 `"REPEAT_UPVOTE"`.
- **⚠️ 일일 상한 상호작용(테스트 설계 필수)**: Build 1 `ReputationService`는 작성자 하루 upvote 획득 +40 상한 초과분에 대해 **reputation_events를 아예 저장하지 않는다**(granted=0). 답변 upvote(+10)는 하루 4건까지만 이벤트가 남으므로 임계 5에 도달 못 한다. **담합 테스트는 질문(POST) upvote(+5, 하루 8건까지)로 5건**을 만들어 임계에 도달시킨다.
- 담합 카운트는 `reputation_events`에서 `reason IN ('UPVOTE_Q','UPVOTE_A') AND delta > 0`인 행의 **DISTINCT source_id**. `delta > 0`는 Build 1 투표변경 역산(음수 delta 동일 reason)을 배제하기 위함.
- 자기투표 가드는 upvote·downvote 모두 차단, **레벨게이트 앞**에 배치(평판 무관 검증).

---

## File Structure

**shared 레포** (`devpath-shared`):
- Create: `src/main/resources/db/migration/V202607011001__vote_abuse_suspicions.sql`
- Create: `src/main/java/ai/devpath/shared/event/CommunityReputationSuspectedEvent.java`

**community-svc 레포**, 신규 패키지 `ai.devpath.community.abuse`:
- Create: `VoteAbuseSuspicion.java` / `VoteAbuseSuspicionRepository.java`
- Create: `CollusionDetector.java`
- Modify: `reputation/RepPoints.java` — 임계 상수.
- Modify: `reputation/ReputationEventRepository.java` — 담합 카운트 쿼리.
- Modify: `post/VoteService.java` — 자기투표 가드 + upvote 후 CollusionDetector 호출 + 주석 갱신.
- Test: `abuse/CollusionDetectorTest.java` · `post/SelfVoteMockMvcTest.java` · `abuse/CollusionWiringTest.java`

> `abuse` 패키지로 남용 방지 로직을 post/reputation과 분리. `CollusionDetector`는 post 리포지토리를 주입받지 않고 호출자가 넘긴 `voterId`·`authorId`로만 동작.

---

## Task 1: shared 담합 스키마 + 이벤트 (Flyway + DomainEvent)

**레포:** `devpath-shared` · 작업 브랜치 `feat/vote-abuse-schema`(main 분기 — shared는 develop 없음).

**Files:**
- Create: `src/main/resources/db/migration/V202607011001__vote_abuse_suspicions.sql`
- Create: `src/main/java/ai/devpath/shared/event/CommunityReputationSuspectedEvent.java`
- Test: 기존 `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`(전체 마이그레이션 적용 검증 — 신규 작성 불필요).

**Interfaces:**
- Produces: 테이블 `vote_abuse_suspicions`(id·actor_id·target_user_id·reason·evidence_count·detected_at, UNIQUE(actor_id,target_user_id,reason)). 이벤트 `CommunityReputationSuspectedEvent(eventId, occurredAt, actorId, targetUserId, reason, evidenceCount)` + `EVENT_TYPE="community.reputation.suspected"`.

- [ ] **Step 1: 마이그레이션 작성**

Create `src/main/resources/db/migration/V202607011001__vote_abuse_suspicions.sql`:
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

- [ ] **Step 2: 이벤트 레코드 작성**

Create `src/main/java/ai/devpath/shared/event/CommunityReputationSuspectedEvent.java`:
```java
package ai.devpath.shared.event;

import java.time.Instant;
import java.util.UUID;

/**
 * 평판 조작(담합/sockpuppet) 의심 이벤트.
 * community-svc가 Transactional Outbox로 발행한다. 소비자(moderation)는 후속.
 */
public record CommunityReputationSuspectedEvent(
		UUID eventId,
		Instant occurredAt,
		long actorId,
		long targetUserId,
		String reason,
		int evidenceCount
) implements DomainEvent {

	public static final String EVENT_TYPE = "community.reputation.suspected";

	@Override
	public String eventType() {
		return EVENT_TYPE;
	}
}
```

- [ ] **Step 3: 마이그레이션 적용 테스트(클린 DB)**

Run(필요 시 DB 초기화 후):
```bash
docker exec devpath-local-postgres-1 psql -U devpath -d devpath -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO devpath; GRANT ALL ON SCHEMA public TO public;"
./gradlew test --tests "*FlywayMigrationTest*"
```
Expected: PASS(전체 마이그레이션 + vote_abuse_suspicions 적용). 실패 시 SQL 문법/순서 점검.

- [ ] **Step 4: 컴파일 + 커밋**

Run: `./gradlew compileJava`
Expected: BUILD SUCCESSFUL.
```bash
git add src/main/resources/db/migration/V202607011001__vote_abuse_suspicions.sql \
        src/main/java/ai/devpath/shared/event/CommunityReputationSuspectedEvent.java
git commit -m "feat(schema): vote_abuse_suspicions 테이블 + CommunityReputationSuspectedEvent"
```

- [ ] **Step 5: 릴리스 게이트(필수)**

`feat/vote-abuse-schema` → `main` PR → CI `build` 녹색 확인 → 머지로 publish 트리거(`Publish Package` 성공 확인). 이후 community-svc:
```bash
cd ../devpath-community-svc && ./gradlew compileJava --refresh-dependencies
JAR=$(find ~/.gradle/caches -path "*devpath-shared*" -name "*.jar" | while read j; do unzip -l "$j" 2>/dev/null | grep -q V202607011001 && echo "$j"; done | head -1)
echo "jar with migration: $JAR"; unzip -l "$JAR" | grep -E "V202607011001|CommunityReputationSuspectedEvent"
```
Expected: 최신 jar에 `V202607011001__vote_abuse_suspicions.sql`·`CommunityReputationSuspectedEvent.class` 포함.

---

## Task 2: community-svc 담합 도메인 + 리포지토리 쿼리 + 상수

**레포:** `devpath-community-svc` · 작업 브랜치 `feat/anti-abuse`(develop 분기). 선행: Task 1 publish 완료.

**Files:**
- Create: `src/main/java/ai/devpath/community/abuse/VoteAbuseSuspicion.java`
- Create: `src/main/java/ai/devpath/community/abuse/VoteAbuseSuspicionRepository.java`
- Modify: `src/main/java/ai/devpath/community/reputation/RepPoints.java`
- Modify: `src/main/java/ai/devpath/community/reputation/ReputationEventRepository.java`

**Interfaces:**
- Produces: `VoteAbuseSuspicion`(엔티티, 대리키 id), `VoteAbuseSuspicionRepository.existsByActorIdAndTargetUserIdAndReason`, `RepPoints.COLLUSION_UPVOTE_THRESHOLD`(=5), `ReputationEventRepository.countDistinctUpvotedSourcesByActorToUser(Long,Long) -> long`. Task 3가 소비.

- [ ] **Step 1: VoteAbuseSuspicion 엔티티**

Create `VoteAbuseSuspicion.java`:
```java
package ai.devpath.community.abuse;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "vote_abuse_suspicions")
public class VoteAbuseSuspicion {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
  @Column(name = "actor_id", nullable = false) private Long actorId;
  @Column(name = "target_user_id", nullable = false) private Long targetUserId;
  @Column(nullable = false, length = 32) private String reason;
  @Column(name = "evidence_count", nullable = false) private int evidenceCount;
  @Column(name = "detected_at", insertable = false, updatable = false) private Instant detectedAt;

  public VoteAbuseSuspicion() {}
  public VoteAbuseSuspicion(Long actorId, Long targetUserId, String reason, int evidenceCount) {
    this.actorId = actorId; this.targetUserId = targetUserId;
    this.reason = reason; this.evidenceCount = evidenceCount;
  }
  public Long getId() { return id; }
  public Long getActorId() { return actorId; }
  public Long getTargetUserId() { return targetUserId; }
  public String getReason() { return reason; }
  public int getEvidenceCount() { return evidenceCount; }
  public Instant getDetectedAt() { return detectedAt; }
}
```

- [ ] **Step 2: VoteAbuseSuspicionRepository**

Create `VoteAbuseSuspicionRepository.java`:
```java
package ai.devpath.community.abuse;

import org.springframework.data.jpa.repository.JpaRepository;

public interface VoteAbuseSuspicionRepository extends JpaRepository<VoteAbuseSuspicion, Long> {
  boolean existsByActorIdAndTargetUserIdAndReason(Long actorId, Long targetUserId, String reason);
}
```

- [ ] **Step 3: RepPoints 상수 추가**

Modify `reputation/RepPoints.java` — `DAILY_UPVOTE_CAP` 아래에 추가:
```java
  /** 담합 의심 임계: 한 투표자가 같은 작성자의 서로 다른 글을 이만큼 upvote하면 의심 기록. */
  public static final int COLLUSION_UPVOTE_THRESHOLD = 5;
```

- [ ] **Step 4: ReputationEventRepository 담합 카운트 쿼리 추가**

Modify `reputation/ReputationEventRepository.java` — 인터페이스에 메서드 추가:
```java
  /** 투표자(actor)가 작성자(user)의 서로 다른 글을 upvote한 개수(실가산분만, 역산 제외). 담합 탐지용. */
  @Query("""
      select count(distinct e.sourceId) from ReputationEvent e
      where e.actorId = :actorId and e.userId = :userId
        and e.reason in ('UPVOTE_Q','UPVOTE_A') and e.delta > 0
      """)
  long countDistinctUpvotedSourcesByActorToUser(@Param("actorId") Long actorId, @Param("userId") Long userId);
```
> `@Query`·`@Param`은 이 파일에 이미 import되어 있다(sumUpvoteGainSince에서 사용). 없으면 `import org.springframework.data.jpa.repository.Query;` `import org.springframework.data.repository.query.Param;` 추가.

- [ ] **Step 5: 컴파일 확인**

Run: `./gradlew compileJava`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 6: 커밋**
```bash
git add src/main/java/ai/devpath/community/abuse/ \
        src/main/java/ai/devpath/community/reputation/RepPoints.java \
        src/main/java/ai/devpath/community/reputation/ReputationEventRepository.java
git commit -m "feat(abuse): 담합 suspicion 엔티티·리포지토리 + 카운트 쿼리 + 임계 상수"
```

---

## Task 3: CollusionDetector — 담합 탐지(기록만 + outbox)

**Files:**
- Create: `src/main/java/ai/devpath/community/abuse/CollusionDetector.java`
- Test: `src/test/java/ai/devpath/community/abuse/CollusionDetectorTest.java`

**Interfaces:**
- Consumes: `ReputationEventRepository.countDistinctUpvotedSourcesByActorToUser`, `VoteAbuseSuspicionRepository`, `OutboxRepository`(`ai.devpath.community.outbox`), `CommunityReputationSuspectedEvent`(shared), `tools.jackson.databind.json.JsonMapper`, `RepPoints`.
- Produces: `void checkOnUpvote(long voterId, long authorId, String sourceType, long sourceId)`.

- [ ] **Step 1: 실패 테스트 작성(임계 도달/미만/멱등)**

Create `CollusionDetectorTest.java`:
```java
package ai.devpath.community.abuse;

import static org.assertj.core.api.Assertions.assertThat;

import ai.devpath.community.outbox.OutboxRepository;
import ai.devpath.community.reputation.ReputationService;
import ai.devpath.shared.event.CommunityReputationSuspectedEvent;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class CollusionDetectorTest {
  @Autowired CollusionDetector detector;
  @Autowired ReputationService reputation;
  @Autowired VoteAbuseSuspicionRepository suspicions;
  @Autowired OutboxRepository outbox;

  /** POST upvote(+5)로 5건 생성 — 답변 upvote(+10)는 일일 +40 상한에 4건에서 막힌다. */
  private void upvotePosts(long voter, long author, int count) {
    for (int i = 0; i < count; i++) {
      reputation.applyVote(author, voter, "POST", 90_000 + i, 0, 1, List.of());
    }
  }

  @Test
  void recordsSuspicionAtThreshold() {
    long voter = 80001, author = 80002;
    upvotePosts(voter, author, 5); // 5 distinct POST upvotes V->A
    long before = outbox.count();

    detector.checkOnUpvote(voter, author, "POST", 90_004);

    assertThat(suspicions.existsByActorIdAndTargetUserIdAndReason(voter, author, "REPEAT_UPVOTE")).isTrue();
    assertThat(outbox.count()).isEqualTo(before + 1);
    assertThat(outbox.findAll().stream().anyMatch(e ->
        CommunityReputationSuspectedEvent.EVENT_TYPE.equals(e.getEventType())
            && e.getPayload().contains("\"reason\":\"REPEAT_UPVOTE\""))).isTrue();
  }

  @Test
  void noSuspicionBelowThreshold() {
    long voter = 80003, author = 80004;
    upvotePosts(voter, author, 4); // 4 < 5
    detector.checkOnUpvote(voter, author, "POST", 90_003);
    assertThat(suspicions.existsByActorIdAndTargetUserIdAndReason(voter, author, "REPEAT_UPVOTE")).isFalse();
  }

  @Test
  void idempotentOnRepeatedDetection() {
    long voter = 80005, author = 80006;
    upvotePosts(voter, author, 6);
    detector.checkOnUpvote(voter, author, "POST", 90_005);
    long afterFirst = outbox.count();
    detector.checkOnUpvote(voter, author, "POST", 90_005); // 재탐지 → no-op
    assertThat(suspicions.count()).isEqualTo(1);
    assertThat(outbox.count()).isEqualTo(afterFirst);
  }
}
```

- [ ] **Step 2: 실패 확인**

Run: `./gradlew test --tests "*CollusionDetectorTest*"`
Expected: FAIL(`CollusionDetector` 미존재 → 컴파일 실패).

- [ ] **Step 3: CollusionDetector 구현**

Create `CollusionDetector.java`:
```java
package ai.devpath.community.abuse;

import ai.devpath.community.outbox.OutboxEntry;
import ai.devpath.community.outbox.OutboxRepository;
import ai.devpath.community.reputation.RepPoints;
import ai.devpath.community.reputation.ReputationEventRepository;
import ai.devpath.shared.event.CommunityReputationSuspectedEvent;
import java.time.Instant;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.json.JsonMapper;

/** 행동 기반 담합(sockpuppet) 탐지 — 기록만. 호출자(VoteService)의 트랜잭션에 합류한다. */
@Service
public class CollusionDetector {
  public static final String REASON_REPEAT_UPVOTE = "REPEAT_UPVOTE";

  private final ReputationEventRepository events;
  private final VoteAbuseSuspicionRepository suspicions;
  private final OutboxRepository outbox;
  private final JsonMapper jsonMapper;

  public CollusionDetector(ReputationEventRepository events, VoteAbuseSuspicionRepository suspicions,
      OutboxRepository outbox, JsonMapper jsonMapper) {
    this.events = events; this.suspicions = suspicions;
    this.outbox = outbox; this.jsonMapper = jsonMapper;
  }

  /** upvote 직후 호출. voter가 author의 서로 다른 글을 임계 이상 upvote했으면 의심 1회 기록 + 이벤트. */
  @Transactional
  public void checkOnUpvote(long voterId, long authorId, String sourceType, long sourceId) {
    long distinct = events.countDistinctUpvotedSourcesByActorToUser(voterId, authorId);
    if (distinct < RepPoints.COLLUSION_UPVOTE_THRESHOLD) return;
    if (suspicions.existsByActorIdAndTargetUserIdAndReason(voterId, authorId, REASON_REPEAT_UPVOTE)) return;
    suspicions.save(new VoteAbuseSuspicion(voterId, authorId, REASON_REPEAT_UPVOTE, (int) distinct));
    CommunityReputationSuspectedEvent event = new CommunityReputationSuspectedEvent(
        UUID.randomUUID(), Instant.now(), voterId, authorId, REASON_REPEAT_UPVOTE, (int) distinct);
    OutboxEntry entry = new OutboxEntry();
    entry.setAggregateType("community_reputation");
    entry.setAggregateId(voterId + ":" + authorId + ":" + REASON_REPEAT_UPVOTE);
    entry.setEventType(CommunityReputationSuspectedEvent.EVENT_TYPE);
    entry.setPayload(jsonMapper.writeValueAsString(event));
    entry.setCreatedAt(Instant.now());
    outbox.save(entry);
  }
}
```

- [ ] **Step 4: 통과 확인 + 커밋**

Run: `./gradlew test --tests "*CollusionDetectorTest*"`
Expected: PASS(3 테스트).
```bash
git add src/main/java/ai/devpath/community/abuse/CollusionDetector.java \
        src/test/java/ai/devpath/community/abuse/CollusionDetectorTest.java
git commit -m "feat(abuse): CollusionDetector 담합 탐지(기록만) + outbox 발행"
```

---

## Task 4: 자기 글 투표 금지 (VoteService 가드)

**Files:**
- Modify: `src/main/java/ai/devpath/community/post/VoteService.java`
- Test: `src/test/java/ai/devpath/community/post/SelfVoteMockMvcTest.java`

**Interfaces:**
- Consumes: 기존 `VoteService.votePost/voteAnswer`, `ForbiddenException`.

- [ ] **Step 1: 실패 테스트(자기투표 403 / 타인 정상)**

Create `SelfVoteMockMvcTest.java`:
```java
package ai.devpath.community.post;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import ai.devpath.community.post.dto.CreateAnswerRequest;
import ai.devpath.community.post.dto.CreateQuestionRequest;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class SelfVoteMockMvcTest {
  @Autowired MockMvc mvc;
  @Autowired QuestionService questionService;
  @Autowired AnswerService answerService;

  @Test
  void cannotVoteOwnPost() throws Exception {
    long author = 88001;
    var q = questionService.create(author, new CreateQuestionRequest("t", "b", List.of()));
    // 작성자가 자기 글 downvote(게이트 없음) → 자기투표 가드 403
    mvc.perform(post("/community/posts/" + q.id() + "/vote").with(jwt().jwt(j -> j.subject("88001")))
        .contentType("application/json").content("{\"value\":-1}"))
        .andExpect(status().isForbidden());
  }

  @Test
  void cannotVoteOwnAnswer() throws Exception {
    long author = 88002;
    var q = questionService.create(author, new CreateQuestionRequest("t", "b", List.of()));
    var a = answerService.add(author, q.id(), new CreateAnswerRequest("ans"));
    // 작성자가 자기 답변 upvote(게이트 없음) → 자기투표 가드 403
    mvc.perform(post("/community/answers/" + a.id() + "/vote").with(jwt().jwt(j -> j.subject("88002")))
        .contentType("application/json").content("{\"value\":1}"))
        .andExpect(status().isForbidden());
  }

  @Test
  void canVoteOthersPost() throws Exception {
    long author = 88003, voter = 88004;
    var q = questionService.create(author, new CreateQuestionRequest("t", "b", List.of()));
    // 타인이 downvote(게이트 없음) → 정상 200
    mvc.perform(post("/community/posts/" + q.id() + "/vote").with(jwt().jwt(j -> j.subject("88004")))
        .contentType("application/json").content("{\"value\":-1}"))
        .andExpect(status().isOk());
  }
}
```

- [ ] **Step 2: 실패 확인**

Run: `./gradlew test --tests "*SelfVoteMockMvcTest*"`
Expected: FAIL(자기투표가 현재 200으로 통과 → 첫 두 테스트 실패).

- [ ] **Step 3: VoteService 자기투표 가드 추가**

Modify `post/VoteService.java`:
- `votePost`의 `CommunityPost p = posts.findById(...)` 다음 줄(레벨게이트 `if (value == 1 && ...)` **앞**)에 추가:
```java
    if (p.getAuthorId() != null && p.getAuthorId() == userId) {
      throw new ForbiddenException("자기 글에는 투표할 수 없습니다");
    }
```
- `voteAnswer`의 `CommunityAnswer a = answers.findById(...)...orElseThrow(...)` 다음 줄(downvote 게이트 `if (value == -1 && ...)` **앞**)에 추가:
```java
    if (a.getAuthorId() != null && a.getAuthorId() == userId) {
      throw new ForbiddenException("자기 답변에는 투표할 수 없습니다");
    }
```
> `getAuthorId()`는 `Long`. null 가드 후 `== userId`(long)로 언박싱 비교. `ForbiddenException`은 같은 패키지에 존재(추가 import 불필요).

- [ ] **Step 4: 통과 확인 + 커밋**

Run: `./gradlew test --tests "*SelfVoteMockMvcTest*"`
Expected: PASS(3 테스트).
```bash
git add src/main/java/ai/devpath/community/post/VoteService.java \
        src/test/java/ai/devpath/community/post/SelfVoteMockMvcTest.java
git commit -m "feat(abuse): 자기 글 투표 금지(votePost/voteAnswer 403)"
```

---

## Task 5: 담합 탐지 연결 (VoteService) + 전체 회귀

**Files:**
- Modify: `src/main/java/ai/devpath/community/post/VoteService.java`
- Test: `src/test/java/ai/devpath/community/abuse/CollusionWiringTest.java`

**Interfaces:**
- Consumes: `CollusionDetector.checkOnUpvote`, `VoteService.votePost`.

- [ ] **Step 1: 실패 테스트(투표 경로로 담합 탐지)**

Create `CollusionWiringTest.java`:
```java
package ai.devpath.community.abuse;

import static org.assertj.core.api.Assertions.assertThat;

import ai.devpath.community.post.QuestionService;
import ai.devpath.community.post.VoteService;
import ai.devpath.community.post.dto.CreateQuestionRequest;
import ai.devpath.community.reputation.ReputationService;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class CollusionWiringTest {
  @Autowired QuestionService questionService;
  @Autowired VoteService voteService;
  @Autowired ReputationService reputation;
  @Autowired VoteAbuseSuspicionRepository suspicions;

  @Test
  void repeatedUpvotesThroughVoteServiceRecordSuspicion() {
    long author = 81001, voter = 81002;
    reputation.applyAcceptance(voter, 99990L, "ANSWER", 1L, List.of()); // voter 평판 15(질문 upvote 게이트 통과)
    // author의 서로 다른 질문 5개를 voter가 upvote(+5씩, 일일 상한 40 내) → 담합 임계 5 도달
    for (int i = 0; i < 5; i++) {
      var q = questionService.create(author, new CreateQuestionRequest("t" + i, "b", List.of()));
      voteService.votePost(voter, q.id(), 1);
    }
    assertThat(suspicions.existsByActorIdAndTargetUserIdAndReason(voter, author, "REPEAT_UPVOTE")).isTrue();
  }
}
```
> 질문 upvote(+5) 5건 = +25 ≤ 40(일일 상한). 답변 upvote(+10)로는 4건에서 상한에 막혀 임계 5에 도달 못 하므로 질문 경로로 검증한다. voter≠author라 자기투표 가드 통과.

- [ ] **Step 2: 실패 확인**

Run: `./gradlew test --tests "*CollusionWiringTest*"`
Expected: FAIL(VoteService가 아직 CollusionDetector 미호출 → suspicion 미기록).

- [ ] **Step 3: VoteService에 CollusionDetector 연결**

Modify `post/VoteService.java`:
- import 추가: `import ai.devpath.community.abuse.CollusionDetector;`.
- 생성자에 `CollusionDetector collusionDetector` 주입(필드 + 파라미터 + 대입).
- `votePost`의 PHILANTHROPIST 블록 다음(메서드 끝부분)에 추가하고, 기존 "자기투표…Build 3에서 정합" 주석을 갱신:
```java
    // 담합 탐지: upvote 시 동일 (투표자→작성자) 반복 패턴 검사(기록만).
    if (value == 1) {
      collusionDetector.checkOnUpvote(userId, p.getAuthorId(), "POST", postId);
    }
```
- `voteAnswer`의 PHILANTHROPIST 블록 다음에 추가:
```java
    // 담합 탐지: upvote 시 동일 (투표자→작성자) 반복 패턴 검사(기록만).
    if (value == 1) {
      collusionDetector.checkOnUpvote(userId, a.getAuthorId(), "ANSWER", answerId);
    }
```
- 두 메서드의 기존 배지 주석 `// 자기 글 투표로도 획득 가능 — 자기투표/sockpuppet 게이팅은 Build 3에서 정합.`를 `// 자기투표는 Build 3에서 금지됨(위 가드) — 담합은 아래 CollusionDetector가 기록.`로 교체.

- [ ] **Step 4: 배선 테스트 통과 확인**

Run: `./gradlew test --tests "*CollusionWiringTest*"`
Expected: PASS.

- [ ] **Step 5: 전체 회귀**

Run(citest 초기화 후): 
```bash
docker exec devpath-local-postgres-1 psql -U devpath -d devpath_citest -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO devpath; GRANT ALL ON SCHEMA public TO public;"
./gradlew test
```
Expected: BUILD SUCCESSFUL, 전체 PASS(기존 평판/배지/투표/Q&A + 신규 CollusionDetectorTest·SelfVoteMockMvcTest·CollusionWiringTest). 자기투표 금지로 깨지는 기존 테스트가 있으면(동일 subject가 자기 글에 투표) 타인 투표자로 보정한다 — 원인 분석 후 수정(추측 금지).

- [ ] **Step 6: 커밋**
```bash
git add src/main/java/ai/devpath/community/post/VoteService.java \
        src/test/java/ai/devpath/community/abuse/CollusionWiringTest.java
git commit -m "feat(abuse): 투표 시 담합 탐지 연결(VoteService) + 주석 갱신"
```

---

## 검증 기준 (Definition of Done)

- [ ] shared `V202607011001__vote_abuse_suspicions.sql` 적용 — `FlywayMigrationTest` PASS, feat→main publish 완료, jar에 마이그레이션 + `CommunityReputationSuspectedEvent` 포함.
- [ ] community-svc `./gradlew test` 전체 PASS(신규 CollusionDetectorTest·SelfVoteMockMvcTest·CollusionWiringTest + 기존 회귀).
- [ ] 자기 글 upvote/downvote → 403(post·answer), 타인 투표 정상.
- [ ] 담합: 동일 투표자→작성자 DISTINCT upvote(delta>0) 5건 도달 시 `vote_abuse_suspicions` 1건 + `community.reputation.suspected` outbox 1건, 미만 미기록, 재도달 멱등(no-op).
- [ ] 평판 회수·투표 차단 없음(담합은 기록만).

## 리스크 / 후속

- **일일 상한 상호작용**: 답변 upvote(+10)는 하루 4건에서 상한에 막혀 이벤트가 안 남으므로 담합 임계 5는 답변만으로는 하루 내 도달 불가(며칠 누적 시 도달). 테스트는 질문 upvote(+5)로 구성. 실서비스에선 담합이 상한(+40/일)으로 이미 제한되며, 탐지는 누적 패턴을 잡는다.
- **오탐**: 정당한 반복 upvote도 의심될 수 있으나 기록만 하므로 무해(사람 검토). 상호성·시간창 정밀화는 후속.
- **범위 밖**: IP/디바이스 탐지, 신계정 7일 제한(platform-svc), moderation 자동 제재·소비, 게이트 500/1000.
