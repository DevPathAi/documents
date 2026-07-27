# 평판 기초 Build 2 — Bronze 배지 엔진 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 이미 동작하는 질문·답변·투표·평판 위에, 같은 트랜잭션에서 Bronze 배지를 멱등 수여하는 엔진을 community-svc에 구현한다(신호 있는 6종 결선, 카탈로그 9종 시드, 수여 시 outbox 발행).

**Architecture:** 신규 `BadgeService`(community-svc `badge` 패키지)를 기존 `QuestionService`/`AnswerService`/`VoteService`의 `@Transactional` 안에서 호출해 동기 수여한다(Build 1 `ReputationService` 패턴). 멱등은 `user_badges` PK. 스키마(`badges`·`user_badges`)와 이벤트(`CommunityBadgeAwardedEvent`)는 shared에 둔다.

**Tech Stack:** Java 21 · Spring Boot 4.0.7 · Spring Data JPA · PostgreSQL · Flyway(shared) · Jackson 3(`tools.jackson`) · JUnit 5 + Spring Boot Test(MockMvc). 빌드 `./gradlew`.

**승인 spec:** [2026-06-30-md3-badge-engine-design.md](../specs/2026-06-30-md3-badge-engine-design.md)

## Global Constraints

- 백엔드 스택: Java 21 · Spring Boot 4 · Gradle(Kotlin DSL). community-svc 패키지 루트 `ai.devpath.community`.
- 모든 서비스 테스트는 `@ActiveProfiles("test")` + shared jar `classpath:db/migration` Flyway 적용. 테스트 DB `devpath_citest`(localhost:5432, docker compose `postgres`). 로컬 DB가 Flyway 이력과 불일치하면 `DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO devpath; GRANT ALL ON SCHEMA public TO public;` 후 재적용.
- 브랜치 전략: 각 레포 `develop`에서 작업 브랜치 분기 → develop PR. main 직접 금지(shared 릴리스 PR 제외).
- **shared→서비스 소비 순서(릴리스 게이트)**: **Task 1(shared 마이그레이션 + 이벤트)은 shared `feat/*→main` PR 머지(publish) 후**에야 community-svc가 새 테이블·이벤트를 소비할 수 있다. Task 2부터는 그 publish 완료 + community-svc `./gradlew compileJava --refresh-dependencies` 후 진행한다. shared 버전 `0.0.1-SNAPSHOT`, main push에서만 publish. community-svc 인증은 `gpr.user`/`gpr.token`(gradle.properties).
- 배지 9종 code(안정키): `FIRST_QUESTION` `FIRST_ANSWER` `STUDENT` `TEACHER` `PHILANTHROPIST` `CRITIC` `FIRST_STEP` `EDITOR` `COMMUNITY`. 이번 빌드는 앞 6종만 트리거 결선, 뒤 3종은 시드만.
- 점수 임계: 평판 `PHILANTHROPIST` = 15(`RepPoints.LVL_UPVOTE_QUESTION`와 동일 상수값이나 의미는 배지 임계). 글/답변 순점수 ≥1 = (upvote − downvote) ≥ 1.
- 이벤트: `community.badge.awarded`(`CommunityBadgeAwardedEvent.EVENT_TYPE`). 소비자는 후속(미구현).

---

## File Structure

**shared 레포** (`devpath-shared`):
- Create: `src/main/resources/db/migration/V202606301002__badges.sql` — `badges`·`user_badges` + 9종 시드.
- Create: `src/main/java/ai/devpath/shared/event/CommunityBadgeAwardedEvent.java` — 이벤트 레코드.

**community-svc 레포** (`devpath-community-svc`), 신규 패키지 `ai.devpath.community.badge`:
- Create: `BadgeCode.java` — enum 9종.
- Create: `Badge.java` / `BadgeRepository.java` — 카탈로그 엔티티 + `findByCode`.
- Create: `UserBadge.java` / `UserBadgeId.java` / `UserBadgeRepository.java` — 보유 배지(복합 PK).
- Create: `BadgeService.java` — `award(userId, code, sourceType, sourceId)` 멱등 + outbox.
- Create: `BadgeView.java` / `BadgeQueryService.java` / `BadgeController.java` — 조회 API.
- Modify: `post/QuestionService.java` — FIRST_QUESTION.
- Modify: `post/AnswerService.java` — FIRST_ANSWER(add) + PHILANTHROPIST(accept).
- Modify: `post/VoteService.java` — STUDENT/TEACHER/CRITIC + PHILANTHROPIST.
- Test: `badge/BadgeServiceTest.java` · `badge/BadgeTriggerTest.java`(작성·투표·평판 통합) · `badge/BadgeApiMockMvcTest.java`(조회).

> `BadgeService`는 post 리포지토리를 주입받지 않고, 호출자가 이미 로드한 `authorId`·점수·평판을 인자로 전달한다 → 배지 로직이 post/reputation 내부구조에 비결합.

---

## Task 1: shared 배지 스키마 + 이벤트 (Flyway + DomainEvent)

**레포:** `devpath-shared` · 작업 브랜치 `feat/badge-schema`(main 분기 — shared는 develop 없음, feat→main 관례).

**Files:**
- Create: `src/main/resources/db/migration/V202606301002__badges.sql`
- Create: `src/main/java/ai/devpath/shared/event/CommunityBadgeAwardedEvent.java`
- Test: 기존 `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`(전체 마이그레이션 적용 검증 — 신규 작성 불필요).

**Interfaces:**
- Produces: 테이블 `badges`(id·code·name·tier·criteria·created_at)·`user_badges`(user_id·badge_id·awarded_at). 이벤트 `CommunityBadgeAwardedEvent(eventId, occurredAt, userId, badgeCode, badgeId, sourceType, sourceId)` + `EVENT_TYPE="community.badge.awarded"`.

- [ ] **Step 1: 마이그레이션 작성**

Create `src/main/resources/db/migration/V202606301002__badges.sql`:
```sql
-- 배지 카탈로그(참조 데이터). code가 코드의 안정키.
CREATE TABLE badges (
  id          BIGSERIAL PRIMARY KEY,
  code        VARCHAR(32)  NOT NULL UNIQUE,   -- FIRST_QUESTION 등
  name        VARCHAR(64)  NOT NULL,          -- 한글 배지명
  tier        VARCHAR(8)   NOT NULL,          -- BRONZE|SILVER|GOLD
  criteria    VARCHAR(255) NOT NULL,          -- 조건 원문
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
  CONSTRAINT chk_badge_tier CHECK (tier IN ('BRONZE','SILVER','GOLD'))
);

-- 사용자 보유 배지(멱등 수여 — PK가 중복 방지).
CREATE TABLE user_badges (
  user_id    BIGINT      NOT NULL,            -- platform users 논리 참조(FK 없음)
  badge_id   BIGINT      NOT NULL REFERENCES badges(id),
  awarded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, badge_id)
);
CREATE INDEX idx_user_badges_user ON user_badges (user_id, awarded_at DESC);

-- Bronze 9종 시드(설계문 20 §3.3).
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

- [ ] **Step 2: 이벤트 레코드 작성**

Create `src/main/java/ai/devpath/shared/event/CommunityBadgeAwardedEvent.java`:
```java
package ai.devpath.shared.event;

import java.time.Instant;
import java.util.UUID;

/**
 * 커뮤니티 배지 수여 이벤트.
 * community-svc가 Transactional Outbox로 발행한다. 소비자(notification-worker)는 후속.
 */
public record CommunityBadgeAwardedEvent(
		UUID eventId,
		Instant occurredAt,
		long userId,
		String badgeCode,
		long badgeId,
		String sourceType,
		long sourceId
) implements DomainEvent {

	public static final String EVENT_TYPE = "community.badge.awarded";

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
Expected: PASS(전체 마이그레이션 + badges/user_badges 적용). 실패 시 SQL 문법/순서 점검.

- [ ] **Step 4: 컴파일 + 커밋**

Run: `./gradlew compileJava`
Expected: BUILD SUCCESSFUL(이벤트 레코드 컴파일).
```bash
git add src/main/resources/db/migration/V202606301002__badges.sql \
        src/main/java/ai/devpath/shared/event/CommunityBadgeAwardedEvent.java
git commit -m "feat(schema): 배지 테이블(badges/user_badges) + CommunityBadgeAwardedEvent"
```

- [ ] **Step 5: 릴리스 게이트(필수)**

`feat/badge-schema` → `main` PR 생성 → CI `build` 녹색 확인 → 머지로 GitHub Packages publish 트리거(`Publish Package` 성공 확인). 이후 community-svc에서 캐시 갱신:
```bash
cd ../devpath-community-svc && ./gradlew compileJava --refresh-dependencies
# 받은 jar에 badges 마이그레이션 + 이벤트 포함 확인:
JAR=$(find ~/.gradle/caches -path "*devpath-shared*" -name "*.jar" | head -1)
unzip -l "$JAR" | grep -E "V202606301002|CommunityBadgeAwardedEvent"
```
Expected: jar에 `V202606301002__badges.sql`·`CommunityBadgeAwardedEvent.class` 포함. 미포함 시 publish 완료 재확인.

---

## Task 2: community-svc 배지 도메인(enum·엔티티·리포지토리)

**레포:** `devpath-community-svc` · 작업 브랜치 `feat/badge-engine`(develop 분기). 선행: Task 1 publish 완료.

**Files:**
- Create: `src/main/java/ai/devpath/community/badge/BadgeCode.java`
- Create: `src/main/java/ai/devpath/community/badge/Badge.java`
- Create: `src/main/java/ai/devpath/community/badge/BadgeRepository.java`
- Create: `src/main/java/ai/devpath/community/badge/UserBadge.java`
- Create: `src/main/java/ai/devpath/community/badge/UserBadgeId.java`
- Create: `src/main/java/ai/devpath/community/badge/UserBadgeRepository.java`

**Interfaces:**
- Produces: `BadgeCode`(enum), `Badge`+`BadgeRepository.findByCode`, `UserBadge`+`UserBadgeRepository.existsByUserIdAndBadgeId`/`findByUserIdOrderByAwardedAtDesc`. Task 3~가 소비.

- [ ] **Step 1: BadgeCode enum**

Create `BadgeCode.java`:
```java
package ai.devpath.community.badge;

public enum BadgeCode {
  FIRST_QUESTION, FIRST_ANSWER, STUDENT, TEACHER, PHILANTHROPIST, CRITIC,
  FIRST_STEP, EDITOR, COMMUNITY
}
```

- [ ] **Step 2: Badge 엔티티 + 리포지토리**

Create `Badge.java`:
```java
package ai.devpath.community.badge;

import jakarta.persistence.*;

@Entity
@Table(name = "badges")
public class Badge {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
  @Column(nullable = false, unique = true, length = 32) private String code;
  @Column(nullable = false, length = 64) private String name;
  @Column(nullable = false, length = 8) private String tier;
  @Column(nullable = false, length = 255) private String criteria;

  public Badge() {}
  public Long getId() { return id; }
  public String getCode() { return code; }
  public String getName() { return name; }
  public String getTier() { return tier; }
  public String getCriteria() { return criteria; }
}
```

Create `BadgeRepository.java`:
```java
package ai.devpath.community.badge;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BadgeRepository extends JpaRepository<Badge, Long> {
  Optional<Badge> findByCode(String code);
}
```

- [ ] **Step 3: UserBadge 엔티티(복합키) + 리포지토리**

Create `UserBadgeId.java`:
```java
package ai.devpath.community.badge;

import java.io.Serializable;
import java.util.Objects;

public class UserBadgeId implements Serializable {
  private Long userId;
  private Long badgeId;
  public UserBadgeId() {}
  public UserBadgeId(Long userId, Long badgeId) { this.userId = userId; this.badgeId = badgeId; }
  @Override public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof UserBadgeId that)) return false;
    return Objects.equals(userId, that.userId) && Objects.equals(badgeId, that.badgeId);
  }
  @Override public int hashCode() { return Objects.hash(userId, badgeId); }
}
```

Create `UserBadge.java`:
```java
package ai.devpath.community.badge;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "user_badges")
@IdClass(UserBadgeId.class)
public class UserBadge {
  @Id @Column(name = "user_id") private Long userId;
  @Id @Column(name = "badge_id") private Long badgeId;
  @Column(name = "awarded_at", insertable = false, updatable = false) private Instant awardedAt;

  public UserBadge() {}
  public UserBadge(Long userId, Long badgeId) { this.userId = userId; this.badgeId = badgeId; }
  public Long getUserId() { return userId; }
  public Long getBadgeId() { return badgeId; }
  public Instant getAwardedAt() { return awardedAt; }
}
```

Create `UserBadgeRepository.java`:
```java
package ai.devpath.community.badge;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserBadgeRepository extends JpaRepository<UserBadge, UserBadgeId> {
  boolean existsByUserIdAndBadgeId(Long userId, Long badgeId);
  List<UserBadge> findByUserIdOrderByAwardedAtDesc(Long userId);
}
```

- [ ] **Step 4: 컴파일 확인**

Run: `./gradlew compileJava`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 5: 커밋**
```bash
git add src/main/java/ai/devpath/community/badge/
git commit -m "feat(badge): 배지 도메인 enum·엔티티·리포지토리"
```

---

## Task 3: BadgeService — award(멱등 수여 + outbox)

**Files:**
- Create: `src/main/java/ai/devpath/community/badge/BadgeService.java`
- Test: `src/test/java/ai/devpath/community/badge/BadgeServiceTest.java`

**Interfaces:**
- Consumes: Task 2 리포지토리, `OutboxRepository`(`ai.devpath.community.outbox`), `CommunityBadgeAwardedEvent`(shared), `tools.jackson.databind.json.JsonMapper`.
- Produces: `boolean award(long userId, BadgeCode code, String sourceType, long sourceId)` — 신규 수여 시 true + outbox 발행, 보유 시 false.

- [ ] **Step 1: 실패 테스트 작성(수여 + 멱등 + outbox)**

Create `BadgeServiceTest.java`:
```java
package ai.devpath.community.badge;

import static org.assertj.core.api.Assertions.assertThat;

import ai.devpath.community.outbox.OutboxRepository;
import ai.devpath.shared.event.CommunityBadgeAwardedEvent;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class BadgeServiceTest {
  @Autowired BadgeService svc;
  @Autowired UserBadgeRepository userBadges;
  @Autowired BadgeRepository badges;
  @Autowired OutboxRepository outbox;

  @Test
  void awardsBadgeOnceAndIsIdempotent() {
    long user = 70001;
    long badgeId = badges.findByCode("FIRST_QUESTION").orElseThrow().getId();

    boolean first = svc.award(user, BadgeCode.FIRST_QUESTION, "POST", 5001);
    assertThat(first).isTrue();
    assertThat(userBadges.existsByUserIdAndBadgeId(user, badgeId)).isTrue();

    boolean second = svc.award(user, BadgeCode.FIRST_QUESTION, "POST", 5001);
    assertThat(second).isFalse(); // 멱등 — 재수여 안 함
    assertThat(userBadges.findByUserIdOrderByAwardedAtDesc(user)).hasSize(1);
  }

  @Test
  void awardEmitsBadgeAwardedOutbox() {
    long user = 70002;
    long before = outbox.count();
    svc.award(user, BadgeCode.CRITIC, "ANSWER", 6001);
    assertThat(outbox.count()).isEqualTo(before + 1);
    assertThat(outbox.findAll().stream()
        .anyMatch(e -> CommunityBadgeAwardedEvent.EVENT_TYPE.equals(e.getEventType())
            && e.getPayload().contains("\"badgeCode\":\"CRITIC\""))).isTrue();
  }

  @Test
  void seedCatalogHasNineBronze() {
    assertThat(badges.count()).isGreaterThanOrEqualTo(9);
    assertThat(badges.findByCode("PHILANTHROPIST")).isPresent();
  }
}
```

- [ ] **Step 2: 실패 확인**

Run: `./gradlew test --tests "*BadgeServiceTest*"`
Expected: FAIL(`BadgeService` 미존재 → 컴파일 실패).

- [ ] **Step 3: BadgeService 구현**

Create `BadgeService.java`:
```java
package ai.devpath.community.badge;

import ai.devpath.community.outbox.OutboxEntry;
import ai.devpath.community.outbox.OutboxRepository;
import ai.devpath.shared.event.CommunityBadgeAwardedEvent;
import java.time.Instant;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.json.JsonMapper;

/** Bronze 배지 자동 수여 엔진. 호출자(post/reputation)의 트랜잭션에 합류한다. */
@Service
public class BadgeService {
  private final BadgeRepository badges;
  private final UserBadgeRepository userBadges;
  private final OutboxRepository outbox;
  private final JsonMapper jsonMapper;

  public BadgeService(BadgeRepository badges, UserBadgeRepository userBadges,
      OutboxRepository outbox, JsonMapper jsonMapper) {
    this.badges = badges; this.userBadges = userBadges;
    this.outbox = outbox; this.jsonMapper = jsonMapper;
  }

  /** code 배지를 userId에게 멱등 수여. 신규 수여 시 true + outbox 발행, 보유 시 false. */
  @Transactional
  public boolean award(long userId, BadgeCode code, String sourceType, long sourceId) {
    Badge badge = badges.findByCode(code.name())
        .orElseThrow(() -> new IllegalStateException("badge not seeded: " + code));
    if (userBadges.existsByUserIdAndBadgeId(userId, badge.getId())) return false;
    userBadges.save(new UserBadge(userId, badge.getId()));
    CommunityBadgeAwardedEvent event = new CommunityBadgeAwardedEvent(
        UUID.randomUUID(), Instant.now(), userId, code.name(), badge.getId(), sourceType, sourceId);
    OutboxEntry entry = new OutboxEntry();
    entry.setAggregateType("community_badge");
    entry.setAggregateId(userId + ":" + code.name());
    entry.setEventType(CommunityBadgeAwardedEvent.EVENT_TYPE);
    entry.setPayload(jsonMapper.writeValueAsString(event));
    entry.setCreatedAt(Instant.now());
    outbox.save(entry);
    return true;
  }
}
```

- [ ] **Step 4: 통과 확인 + 커밋**

Run: `./gradlew test --tests "*BadgeServiceTest*"`
Expected: PASS(3 테스트).
```bash
git add src/main/java/ai/devpath/community/badge/BadgeService.java \
        src/test/java/ai/devpath/community/badge/BadgeServiceTest.java
git commit -m "feat(badge): BadgeService 멱등 수여 + outbox 발행"
```

---

## Task 4: 작성 배지 연결 (FIRST_QUESTION · FIRST_ANSWER)

**Files:**
- Modify: `src/main/java/ai/devpath/community/post/QuestionService.java`
- Modify: `src/main/java/ai/devpath/community/post/AnswerService.java`
- Test: `src/test/java/ai/devpath/community/badge/BadgeTriggerTest.java`

**Interfaces:**
- Consumes: `BadgeService.award`, `QuestionService.create`, `AnswerService.add`.

- [ ] **Step 1: 실패 테스트(작성 시 배지)**

Create `BadgeTriggerTest.java`:
```java
package ai.devpath.community.badge;

import static org.assertj.core.api.Assertions.assertThat;

import ai.devpath.community.post.AnswerService;
import ai.devpath.community.post.QuestionService;
import ai.devpath.community.post.dto.CreateAnswerRequest;
import ai.devpath.community.post.dto.CreateQuestionRequest;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class BadgeTriggerTest {
  @Autowired QuestionService questionService;
  @Autowired AnswerService answerService;
  @Autowired UserBadgeRepository userBadges;
  @Autowired BadgeRepository badges;

  private boolean has(long userId, String code) {
    long badgeId = badges.findByCode(code).orElseThrow().getId();
    return userBadges.existsByUserIdAndBadgeId(userId, badgeId);
  }

  @Test
  void firstQuestionAwardsBadge() {
    long asker = 71001;
    questionService.create(asker, new CreateQuestionRequest("t", "b", List.of()));
    assertThat(has(asker, "FIRST_QUESTION")).isTrue();
  }

  @Test
  void firstAnswerAwardsBadge() {
    long asker = 71002, answerer = 71003;
    var q = questionService.create(asker, new CreateQuestionRequest("t", "b", List.of()));
    answerService.add(answerer, q.id(), new CreateAnswerRequest("ans"));
    assertThat(has(answerer, "FIRST_ANSWER")).isTrue();
  }
}
```

- [ ] **Step 2: 실패 확인**

Run: `./gradlew test --tests "*BadgeTriggerTest*"`
Expected: FAIL(작성 시 배지 미수여).

- [ ] **Step 3: QuestionService 수정(FIRST_QUESTION)**

Modify `QuestionService.java`:
- 생성자에 `BadgeService badgeService` 주입(필드 + 파라미터 + 대입).
- import 추가: `import ai.devpath.community.badge.BadgeCode;` `import ai.devpath.community.badge.BadgeService;`.
- `create(...)`의 `publishQuestionPosted(userId, p.getId(), req);` 다음 줄에 수여 호출 추가:
```java
    publishQuestionPosted(userId, p.getId(), req);
    badgeService.award(userId, BadgeCode.FIRST_QUESTION, "POST", p.getId());
    return detail(p.getId());
```
> 필드 `private final BadgeService badgeService;`, 생성자 끝 파라미터 `BadgeService badgeService` 추가 + `this.badgeService = badgeService;`.

- [ ] **Step 4: AnswerService 수정(FIRST_ANSWER)**

Modify `AnswerService.java`:
- import 추가: `import ai.devpath.community.badge.BadgeCode;` `import ai.devpath.community.badge.BadgeService;`.
- 생성자에 `BadgeService badgeService` 주입(필드 + 파라미터 + 대입).
- `add(...)`의 `a = answers.save(a);` 다음에 수여 호출 추가:
```java
    a = answers.save(a);
    badgeService.award(userId, BadgeCode.FIRST_ANSWER, "ANSWER", a.getId());
    return new AnswerView(a.getId(), a.getAuthorId(), a.getBodyMd(),
        a.isAiGenerated(), a.isAccepted(), a.getUpvoteCount());
```

- [ ] **Step 5: 통과 확인 + 커밋**

Run: `./gradlew test --tests "*BadgeTriggerTest*"`
Expected: PASS(2 테스트).
```bash
git add src/main/java/ai/devpath/community/post/QuestionService.java \
        src/main/java/ai/devpath/community/post/AnswerService.java \
        src/test/java/ai/devpath/community/badge/BadgeTriggerTest.java
git commit -m "feat(badge): 질문/답변 작성 시 FIRST_QUESTION/FIRST_ANSWER 수여"
```

---

## Task 5: 투표 배지 연결 (STUDENT · TEACHER · CRITIC)

**Files:**
- Modify: `src/main/java/ai/devpath/community/post/VoteService.java`
- Test: `src/test/java/ai/devpath/community/badge/BadgeTriggerTest.java`(메서드 추가)

**Interfaces:**
- Consumes: `BadgeService.award`, `VoteService.votePost`/`voteAnswer`, `CommunityVoteRepository.countByTargetTypeAndTargetIdAndValue`.

- [ ] **Step 1: 실패 테스트 추가(투표 배지)**

Append to `BadgeTriggerTest.java`(메서드 + 필요한 import/필드):
- 상단 import 추가: `import ai.devpath.community.post.VoteService;` `import ai.devpath.community.reputation.ReputationService;`.
- 필드 추가: `@Autowired VoteService voteService;` `@Autowired ReputationService reputation;`.
- 메서드 추가:
```java
  @Test
  void postReachingPlusOneAwardsStudentToAuthor() {
    long asker = 72001, voter = 72002;
    var q = questionService.create(asker, new CreateQuestionRequest("t", "b", List.of()));
    reputation.applyAcceptance(voter, 99990L, "ANSWER", 1L, List.of()); // voter 평판 15(게이트 통과)
    voteService.votePost(voter, q.id(), 1);
    assertThat(has(asker, "STUDENT")).isTrue();
  }

  @Test
  void answerReachingPlusOneAwardsTeacherToAuthor() {
    long asker = 72003, answerer = 72004, voter = 72005;
    var q = questionService.create(asker, new CreateQuestionRequest("t", "b", List.of()));
    var a = answerService.add(answerer, q.id(), new CreateAnswerRequest("ans"));
    voteService.voteAnswer(voter, a.id(), 1); // 답변 upvote는 게이트 없음
    assertThat(has(answerer, "TEACHER")).isTrue();
  }

  @Test
  void castingDownvoteAwardsCriticToVoter() {
    long asker = 72006, voter = 72008;
    var q = questionService.create(asker, new CreateQuestionRequest("t", "b", List.of()));
    voteService.votePost(voter, q.id(), -1); // 질문 downvote는 레벨 게이트 없음 → CRITIC
    assertThat(has(voter, "CRITIC")).isTrue();
  }
```
> CRITIC은 질문 downvote(`votePost(voter, qid, -1)`)로 검증한다 — Build 1에서 질문 downvote는 레벨 게이트가 없어 투표자 평판 사전부여가 불필요하다(답변 downvote만 평판 125 게이트). STUDENT 테스트의 upvote(value=1)는 질문 upvote 게이트 15가 있어 voter에게 `applyAcceptance`로 평판 15를 사전 부여한다.

- [ ] **Step 2: 실패 확인**

Run: `./gradlew test --tests "*BadgeTriggerTest*"`
Expected: FAIL(투표 배지 미수여).

- [ ] **Step 3: VoteService 수정(STUDENT/TEACHER/CRITIC)**

Modify `VoteService.java`:
- import 추가: `import ai.devpath.community.badge.BadgeCode;` `import ai.devpath.community.badge.BadgeService;`.
- 생성자에 `BadgeService badgeService` 주입(필드 + 파라미터 + 대입).
- `votePost(...)`의 `reputation.applyVote(...)` 다음에 배지 수여 추가:
```java
    reputation.applyVote(p.getAuthorId(), userId, "POST", postId, oldValue, value, tagIds);
    // 배지: 순점수 +1 도달 → 글 작성자 STUDENT, downvote 행사 → 투표자 CRITIC
    if (p.getUpvoteCount() - p.getDownvoteCount() >= 1) {
      badgeService.award(p.getAuthorId(), BadgeCode.STUDENT, "POST", postId);
    }
    if (value == -1) {
      badgeService.award(userId, BadgeCode.CRITIC, "POST", postId);
    }
```
- `voteAnswer(...)`의 `reputation.applyVote(...)` 다음에 추가:
```java
    reputation.applyVote(a.getAuthorId(), userId, "ANSWER", answerId, oldValue, value, tagIds);
    // 배지: 답변 순점수 +1 도달 → 답변 작성자 TEACHER, downvote 행사 → 투표자 CRITIC
    int answerNet = a.getUpvoteCount()
        - votes.countByTargetTypeAndTargetIdAndValue("ANSWER", answerId, (short) -1);
    if (answerNet >= 1) {
      badgeService.award(a.getAuthorId(), BadgeCode.TEACHER, "ANSWER", answerId);
    }
    if (value == -1) {
      badgeService.award(userId, BadgeCode.CRITIC, "ANSWER", answerId);
    }
```
> `a.getUpvoteCount()`은 같은 메서드에서 `a.setUpvoteCount(votes.count(...,1))`로 갱신된 값. downvote 수는 votes 카운트로 산출(answer는 downvote 컬럼 없음). `votePost`의 `p`는 `refreshPostCounts` 후 최신 카운트 보유.

- [ ] **Step 4: 통과 확인 + 커밋**

Run: `./gradlew test --tests "*BadgeTriggerTest*"`
Expected: PASS(작성 2 + 투표 3 = 5 테스트).
```bash
git add src/main/java/ai/devpath/community/post/VoteService.java \
        src/test/java/ai/devpath/community/badge/BadgeTriggerTest.java
git commit -m "feat(badge): 투표 시 STUDENT/TEACHER/CRITIC 수여"
```

---

## Task 6: 평판 배지 연결 (PHILANTHROPIST — 평판 15)

**Files:**
- Modify: `src/main/java/ai/devpath/community/post/VoteService.java`
- Modify: `src/main/java/ai/devpath/community/post/AnswerService.java`
- Test: `src/test/java/ai/devpath/community/badge/BadgeTriggerTest.java`(메서드 추가)

**Interfaces:**
- Consumes: `BadgeService.award`, `ReputationService.reputationOf`.

- [ ] **Step 1: 실패 테스트 추가(평판 15 → PHILANTHROPIST)**

Append to `BadgeTriggerTest.java`:
```java
  @Test
  void reachingReputation15AwardsPhilanthropist() {
    long answerer = 73001, asker = 73002;
    var q = questionService.create(asker, new CreateQuestionRequest("t", "b", List.of()));
    var a = answerService.add(answerer, q.id(), new CreateAnswerRequest("ans"));
    answerService.accept(asker, a.id()); // 답변 채택 → answerer +15
    assertThat(has(answerer, "PHILANTHROPIST")).isTrue();
  }
```

- [ ] **Step 2: 실패 확인**

Run: `./gradlew test --tests "*BadgeTriggerTest*"`
Expected: FAIL(평판 15 도달했으나 PHILANTHROPIST 미수여).

- [ ] **Step 3: AnswerService.accept 수정(PHILANTHROPIST)**

Modify `AnswerService.java` `accept(...)`의 `reputation.applyAcceptance(...)` 다음에 추가:
```java
    reputation.applyAcceptance(a.getAuthorId(), p.getAuthorId(), "ANSWER", answerId, tagIds);
    // 배지: 평판 15 도달 → PHILANTHROPIST(답변 작성자·질문 작성자 둘 다 평가)
    awardPhilanthropistIfReached(a.getAuthorId(), "ANSWER", answerId);
    awardPhilanthropistIfReached(p.getAuthorId(), "POST", q.getPostId());
```
- `AnswerService`에 private 헬퍼 + import 추가:
```java
  private void awardPhilanthropistIfReached(long userId, String sourceType, long sourceId) {
    if (reputation.reputationOf(userId) >= ai.devpath.community.reputation.RepPoints.LVL_UPVOTE_QUESTION) {
      badgeService.award(userId, BadgeCode.PHILANTHROPIST, sourceType, sourceId);
    }
  }
```
> `RepPoints.LVL_UPVOTE_QUESTION` == 15. `reputation`은 Build 1에서 이미 주입됨(`ReputationService`).

- [ ] **Step 4: VoteService 수정(PHILANTHROPIST)**

Modify `VoteService.java` — `votePost`/`voteAnswer`의 배지 블록에 평판 체크 추가:
- `votePost` STUDENT 블록 다음:
```java
    if (reputation.reputationOf(p.getAuthorId()) >= RepPoints.LVL_UPVOTE_QUESTION) {
      badgeService.award(p.getAuthorId(), BadgeCode.PHILANTHROPIST, "POST", postId);
    }
```
- `voteAnswer` TEACHER 블록 다음:
```java
    if (reputation.reputationOf(a.getAuthorId()) >= RepPoints.LVL_UPVOTE_QUESTION) {
      badgeService.award(a.getAuthorId(), BadgeCode.PHILANTHROPIST, "ANSWER", answerId);
    }
```
- import 추가: `import ai.devpath.community.reputation.RepPoints;`(미존재 시).

- [ ] **Step 5: 통과 확인 + 커밋**

Run: `./gradlew test --tests "*BadgeTriggerTest*"`
Expected: PASS(작성 2 + 투표 3 + 평판 1 = 6 테스트).
```bash
git add src/main/java/ai/devpath/community/post/AnswerService.java \
        src/main/java/ai/devpath/community/post/VoteService.java \
        src/test/java/ai/devpath/community/badge/BadgeTriggerTest.java
git commit -m "feat(badge): 평판 15 도달 시 PHILANTHROPIST 수여"
```

---

## Task 7: 조회 API + 전체 회귀 (GET /community/users/{id}/badges)

**Files:**
- Create: `src/main/java/ai/devpath/community/badge/BadgeView.java`
- Create: `src/main/java/ai/devpath/community/badge/BadgeQueryService.java`
- Create: `src/main/java/ai/devpath/community/badge/BadgeController.java`
- Test: `src/test/java/ai/devpath/community/badge/BadgeApiMockMvcTest.java`

**Interfaces:**
- Consumes: `UserBadgeRepository.findByUserIdOrderByAwardedAtDesc`, `BadgeRepository.findById`, `QuestionService.create`.
- Produces: `GET /community/users/{userId}/badges` → `[{code, name, tier, awardedAt}, ...]`.

- [ ] **Step 1: 실패 테스트(조회 API)**

Create `BadgeApiMockMvcTest.java`:
```java
package ai.devpath.community.badge;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import ai.devpath.community.post.QuestionService;
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
class BadgeApiMockMvcTest {
  @Autowired MockMvc mvc;
  @Autowired QuestionService questionService;

  @Test
  void listsUserBadges() throws Exception {
    long user = 74001;
    questionService.create(user, new CreateQuestionRequest("t", "b", List.of())); // FIRST_QUESTION 수여
    mvc.perform(get("/community/users/" + user + "/badges").with(jwt().jwt(j -> j.subject("999"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$[?(@.code=='FIRST_QUESTION')]").exists())
        .andExpect(jsonPath("$[0].name").exists())
        .andExpect(jsonPath("$[0].tier").value("BRONZE"));
  }
}
```

- [ ] **Step 2: 실패 확인**

Run: `./gradlew test --tests "*BadgeApiMockMvcTest*"`
Expected: FAIL(엔드포인트 미존재 → 404 또는 컴파일 실패).

- [ ] **Step 3: BadgeView + BadgeQueryService + BadgeController 구현**

Create `BadgeView.java`:
```java
package ai.devpath.community.badge;

import java.time.Instant;

public record BadgeView(String code, String name, String tier, Instant awardedAt) {}
```

Create `BadgeQueryService.java`:
```java
package ai.devpath.community.badge;

import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class BadgeQueryService {
  private final UserBadgeRepository userBadges;
  private final BadgeRepository badges;

  public BadgeQueryService(UserBadgeRepository userBadges, BadgeRepository badges) {
    this.userBadges = userBadges; this.badges = badges;
  }

  @Transactional(readOnly = true)
  public List<BadgeView> badgesOf(long userId) {
    return userBadges.findByUserIdOrderByAwardedAtDesc(userId).stream()
        .map(ub -> {
          Badge b = badges.findById(ub.getBadgeId()).orElseThrow();
          return new BadgeView(b.getCode(), b.getName(), b.getTier(), ub.getAwardedAt());
        })
        .toList();
  }
}
```

Create `BadgeController.java`:
```java
package ai.devpath.community.badge;

import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/community/users")
public class BadgeController {
  private final BadgeQueryService badgeQuery;
  public BadgeController(BadgeQueryService badgeQuery) { this.badgeQuery = badgeQuery; }

  @GetMapping("/{userId}/badges")
  public List<BadgeView> badges(@PathVariable long userId) {
    return badgeQuery.badgesOf(userId);
  }
}
```

- [ ] **Step 4: 통과 확인**

Run: `./gradlew test --tests "*BadgeApiMockMvcTest*"`
Expected: PASS.

- [ ] **Step 5: 전체 회귀**

Run(필요 시 citest 초기화 후): `./gradlew test`
Expected: BUILD SUCCESSFUL. 기존 평판/투표/Q&A 테스트 + 신규 배지 테스트 전부 PASS. 회귀 실패 시 원인 분석(추측 금지).

- [ ] **Step 6: 커밋**
```bash
git add src/main/java/ai/devpath/community/badge/BadgeView.java \
        src/main/java/ai/devpath/community/badge/BadgeQueryService.java \
        src/main/java/ai/devpath/community/badge/BadgeController.java \
        src/test/java/ai/devpath/community/badge/BadgeApiMockMvcTest.java
git commit -m "feat(badge): 보유 배지 조회 API(GET /community/users/{id}/badges)"
```

---

## 검증 기준 (Definition of Done)

- [ ] shared `V202606301002__badges.sql` 적용 — `FlywayMigrationTest` PASS, feat→main publish 완료, jar에 마이그레이션 + `CommunityBadgeAwardedEvent` 포함.
- [ ] community-svc `./gradlew test` 전체 PASS(신규 BadgeServiceTest·BadgeTriggerTest·BadgeApiMockMvcTest + 기존 회귀).
- [ ] 6종 결선 수여 검증: FIRST_QUESTION(질문 작성)·FIRST_ANSWER(답변 작성)·STUDENT(글 +1)·TEACHER(답변 +1)·CRITIC(downvote 행사)·PHILANTHROPIST(평판 15). 멱등(재트리거 무중복)·outbox 발행(`community.badge.awarded`) 검증.
- [ ] 9종 카탈로그 시드 확인. 3종(FIRST_STEP·EDITOR·COMMUNITY)은 시드만(트리거 미결선).
- [ ] 조회 API `GET /community/users/{id}/badges` 동작.

## 리스크 / 후속

- **자기 투표로 STUDENT/TEACHER**: Build 1에 자기 글 투표 금지 미적용 → 자기 글 +1로 획득 가능. 자기 투표 금지(Build 3)와 함께 정합.
- **board_type 무구분**: STUDENT를 모든 POST에 적용(Build 1 평판과 일관). 자유게시판 등 board_type별 차등은 후속.
- **이벤트 소비자 부재**: `community.badge.awarded` 발행되나 notification 워커 후속.
- **3종 dormant**: FIRST_STEP(프로필 이벤트 소비)·EDITOR(글 편집 기능)·COMMUNITY(스트릭) — 상위 기능 도입 시 트리거 결선. 카탈로그는 완비.
- **Silver/Gold 배지**: 후속 빌드.
