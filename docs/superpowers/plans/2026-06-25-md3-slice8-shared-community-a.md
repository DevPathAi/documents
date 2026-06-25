# 빌드 A (shared) — 커뮤니티 Q&A 스키마 + 이벤트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** devpath-shared에 커뮤니티 Q&A 데이터 모델(`V202606251001__community_qna.sql`)과 이벤트 2종(`CommunityQuestionPostedEvent`·`CommunitySeedReadyEvent`)을 추가하고, `FlywayMigrationTest`로 계약을 단언한 뒤 **main 릴리스(publish)** 한다.

**Architecture:** 설계서 [2026-06-25-md3-slice8-community-qna-design](../specs/2026-06-25-md3-slice8-community-qna-design.md) §4. 커뮤니티 도메인 7개 테이블(posts·questions·answers·votes·tags·post_tags·ai_answers). 교차서비스 FK 없음(author_id 논리참조), 도메인 내 FK 허용(questions→posts 등). AI 시드 이벤트 왕복(community→ai-svc→community)의 계약 이벤트 2종.

**Tech Stack:** Java 21 · Gradle (Kotlin DSL) · `java-library` · Flyway(중앙 `classpath:db/migration`) · pgvector · JUnit 5 · PostgreSQL 17.

## Global Constraints

- **마이그레이션 번호**: `V202606251001`(직전 최댓값 `V202606241001__ai_mentor_sessions` +1 — **작성 직전 `ls devpath-shared/src/main/resources/db/migration/`로 재실측**, 더 큰 번호 있으면 그 +1).
- **교차서비스 FK 금지**: `author_id`(platform users)·시드의 `content` 참조는 **논리참조(FK 없음)**. **도메인 내 FK는 허용**(questions→posts, answers→questions, post_tags→posts/tags).
- **이벤트 규약**(shared CLAUDE.md): `ai.devpath.shared.event`에 **record**로 정의, `DomainEvent` 구현, `eventType`은 `<도메인>.<엔티티>.<동작>` 소문자 점 표기, 새 필드는 nullable/기본값.
- **트리거 재사용**: `set_updated_at()` 함수는 `V202606150900__init_common`에 존재 → 재정의 금지, 트리거만 생성.
- **vector**: `CREATE EXTENSION IF NOT EXISTS vector`(이미 `V202606181006`에 있으나 멱등 안전). 타입 `VECTOR(768)`, 인덱스 `USING hnsw (… vector_cosine_ops)`.
- **브랜치 전략**(핸드오프 §4): **devpath-shared는 develop 부재 → `feat/*`→`main` 직접 PR**(다른 서비스의 develop 2단계와 다름). 머지 후 **publish**(GitHub Packages)로 `0.0.1-SNAPSHOT` 갱신 — 후속 빌드가 jar 의존.
- **테스트 DB**: `FlywayMigrationTest`는 실DB(로컬 `docker compose up -d` postgres 5432 `devpath`, CI는 service container). `DB_URL`/`DB_USER`/`DB_PASSWORD` 환경변수(기본 로컬). **멱등**(이미 적용된 DB도 통과하도록 "결과 상태" 단언).
- **검증 명령**: `cd devpath-shared && ./gradlew test`(전체) 또는 `./gradlew test --tests "ai.devpath.shared.*"`.

---

## File Structure

- `devpath-shared/src/main/java/ai/devpath/shared/event/CommunityQuestionPostedEvent.java` — 질문 게시 이벤트(community→ai-svc)
- `devpath-shared/src/main/java/ai/devpath/shared/event/CommunitySeedReadyEvent.java` — AI 시드 준비 이벤트(ai-svc→community)
- `devpath-shared/src/test/java/ai/devpath/shared/event/CommunityQuestionPostedEventTest.java`
- `devpath-shared/src/test/java/ai/devpath/shared/event/CommunitySeedReadyEventTest.java`
- `devpath-shared/src/main/resources/db/migration/V202606251001__community_qna.sql` — 7개 테이블 + 인덱스 + 트리거
- `devpath-shared/src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java:506` — 커뮤니티 단언 메서드 추가(기존 파일 끝에)

---

## Task A1: CommunityQuestionPostedEvent

**Files:**
- Create: `devpath-shared/src/main/java/ai/devpath/shared/event/CommunityQuestionPostedEvent.java`
- Test: `devpath-shared/src/test/java/ai/devpath/shared/event/CommunityQuestionPostedEventTest.java`

**Interfaces:**
- Consumes: `DomainEvent`(eventId·occurredAt·eventType).
- Produces: `CommunityQuestionPostedEvent(UUID eventId, Instant occurredAt, long userId, long questionId, long postId, String title, String bodyMd)`, `EVENT_TYPE="community.question.posted"`. (빌드 B2가 발행, 빌드 C가 소비.)

- [ ] **Step 1: Write the failing test**

```java
package ai.devpath.shared.event;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class CommunityQuestionPostedEventTest {

  @Test
  void eventTypeIsStable() {
    var event = new CommunityQuestionPostedEvent(
        UUID.randomUUID(), Instant.now(), 1L, 10L, 10L, "JPA N+1?", "본문...");
    assertEquals("community.question.posted", event.eventType());
  }

  @Test
  void carriesQuestionBodyForSeedWorker() {
    var event = new CommunityQuestionPostedEvent(
        UUID.randomUUID(), Instant.now(), 7L, 42L, 42L, "제목", "마크다운 본문");
    assertEquals(42L, event.questionId());
    assertEquals("제목", event.title());
    assertEquals("마크다운 본문", event.bodyMd());
  }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.event.CommunityQuestionPostedEventTest"`
Expected: 컴파일 실패(`CommunityQuestionPostedEvent` 심볼 없음).

- [ ] **Step 3: Write the event record**

```java
package ai.devpath.shared.event;

import java.time.Instant;
import java.util.UUID;

/**
 * 커뮤니티 Q&A 질문 게시 이벤트.
 * community-svc가 Transactional Outbox로 발행하고, ai-svc(AI 시드 답변, 슬라이스 #8)가 구독한다.
 * 질문 본문(title·bodyMd)을 동봉해 ai-svc가 역조회 없이 시드 답변을 생성한다(설계 D-2).
 */
public record CommunityQuestionPostedEvent(
    UUID eventId,
    Instant occurredAt,
    long userId,
    long questionId,
    long postId,
    String title,
    String bodyMd
) implements DomainEvent {

  public static final String EVENT_TYPE = "community.question.posted";

  @Override
  public String eventType() {
    return EVENT_TYPE;
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.event.CommunityQuestionPostedEventTest"`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add devpath-shared/src/main/java/ai/devpath/shared/event/CommunityQuestionPostedEvent.java \
        devpath-shared/src/test/java/ai/devpath/shared/event/CommunityQuestionPostedEventTest.java
git commit -m "feat(shared): CommunityQuestionPostedEvent (슬라이스 #8 AI 시드 이벤트 왕복 시작)"
```

---

## Task A2: CommunitySeedReadyEvent

**Files:**
- Create: `devpath-shared/src/main/java/ai/devpath/shared/event/CommunitySeedReadyEvent.java`
- Test: `devpath-shared/src/test/java/ai/devpath/shared/event/CommunitySeedReadyEventTest.java`

**Interfaces:**
- Consumes: `DomainEvent`.
- Produces: `CommunitySeedReadyEvent(UUID eventId, Instant occurredAt, long questionId, String status, String content, String provider, List<Double> questionEmbedding, String errorCode)`, `EVENT_TYPE="community.seed.ready"`. `status`∈{DONE,FAILED}. `content`/`provider`/`questionEmbedding`/`errorCode`는 nullable(FAILED·임베딩 실패 시). (빌드 C가 발행, 빌드 B2가 소비.)

- [ ] **Step 1: Write the failing test**

```java
package ai.devpath.shared.event;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class CommunitySeedReadyEventTest {

  @Test
  void eventTypeIsStable() {
    var event = new CommunitySeedReadyEvent(
        UUID.randomUUID(), Instant.now(), 10L, "DONE", "답변", "MOCK", List.of(0.1, 0.2), null);
    assertEquals("community.seed.ready", event.eventType());
  }

  @Test
  void failedSeedHasNullContentAndEmbedding() {
    var event = new CommunitySeedReadyEvent(
        UUID.randomUUID(), Instant.now(), 10L, "FAILED", null, "CLAUDE", null, "LLM_FAILED");
    assertEquals("FAILED", event.status());
    assertNull(event.content());
    assertNull(event.questionEmbedding());
    assertEquals("LLM_FAILED", event.errorCode());
  }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.event.CommunitySeedReadyEventTest"`
Expected: 컴파일 실패(`CommunitySeedReadyEvent` 심볼 없음).

- [ ] **Step 3: Write the event record**

```java
package ai.devpath.shared.event;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * 커뮤니티 AI 시드 답변 준비 이벤트.
 * ai-svc가 질문을 받아 시드 답변(+질문 임베딩)을 생성한 뒤 Transactional Outbox로 발행하고,
 * community-svc가 구독해 community_answers/community_ai_answers/question_embedding을 영속한다(설계 D-1).
 * status=FAILED면 content/questionEmbedding은 null일 수 있고 errorCode가 채워진다.
 */
public record CommunitySeedReadyEvent(
    UUID eventId,
    Instant occurredAt,
    long questionId,
    String status,
    String content,
    String provider,
    List<Double> questionEmbedding,
    String errorCode
) implements DomainEvent {

  public static final String EVENT_TYPE = "community.seed.ready";

  @Override
  public String eventType() {
    return EVENT_TYPE;
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.event.CommunitySeedReadyEventTest"`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add devpath-shared/src/main/java/ai/devpath/shared/event/CommunitySeedReadyEvent.java \
        devpath-shared/src/test/java/ai/devpath/shared/event/CommunitySeedReadyEventTest.java
git commit -m "feat(shared): CommunitySeedReadyEvent (AI 시드 답변+임베딩 반환 이벤트)"
```

---

## Task A3: 커뮤니티 Q&A 마이그레이션 + FlywayMigrationTest 단언

**Files:**
- Create: `devpath-shared/src/main/resources/db/migration/V202606251001__community_qna.sql`
- Modify: `devpath-shared/src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`(파일 끝 `}` 앞에 테스트 메서드 추가)

**Interfaces:**
- Produces(빌드 B1/B2/C가 JPA 매핑): 테이블 `community_posts`·`community_questions`·`community_answers`·`community_votes`·`community_tags`·`community_post_tags`·`community_ai_answers`. 컬럼·CHECK·UNIQUE·인덱스는 아래 SQL 그대로.

- [ ] **Step 1: 마이그레이션 번호 재실측**

Run: `ls devpath-shared/src/main/resources/db/migration/ | sort | tail -3`
Expected: 최댓값이 `V202606241001__ai_mentor_sessions.sql`임을 확인. 더 큰 번호가 있으면 파일명을 그 +1로 조정(아래는 `V202606251001` 가정).

- [ ] **Step 2: Write the failing test (FlywayMigrationTest에 커뮤니티 단언 추가)**

`FlywayMigrationTest.java`의 **마지막 `}` 바로 앞**에 아래 4개 메서드를 추가한다(기존 `columns(String)` 헬퍼·import 재사용):

```java
  @Test
  void communityPostsTableContract() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      var cols = columns("community_posts");
      for (String col : new String[] {"id", "author_id", "board_type", "title", "body_md",
          "body_html", "status", "view_count", "upvote_count", "downvote_count",
          "created_at", "updated_at"}) {
        assertTrue(cols.contains(col), "community_posts." + col + " 컬럼 필요");
      }
      // board_type CHECK
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO community_posts(author_id,board_type,title,body_md) "
              + "VALUES (1,'BOGUS','t','b')"));
      // status CHECK
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO community_posts(author_id,board_type,title,body_md,status) "
              + "VALUES (1,'QNA','t','b','NOPE')"));
      try (var rs = st.executeQuery(
          "SELECT 1 FROM pg_indexes WHERE schemaname='public' "
              + "AND tablename='community_posts' "
              + "AND indexname='idx_community_posts_board_status_created'")) {
        assertTrue(rs.next(), "게시판별 최신글 인덱스 필요");
      }
    }
  }

  @Test
  void communityQnaTablesAndVotesContract() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      for (String t : new String[] {"community_questions", "community_answers",
          "community_votes", "community_tags", "community_post_tags", "community_ai_answers"}) {
        try (var rs = c.getMetaData().getTables(null, "public", t, new String[] {"TABLE"})) {
          assertTrue(rs.next(), t + " 테이블 필요");
        }
      }
      // votes: value CHECK + target CHECK + UNIQUE(user_id,target_type,target_id)
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO community_votes(user_id,target_type,target_id,value) "
              + "VALUES (1,'POST',1,2)"));
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO community_votes(user_id,target_type,target_id,value) "
              + "VALUES (1,'BOGUS',1,1)"));
      long uid = System.nanoTime();
      st.execute("INSERT INTO community_votes(user_id,target_type,target_id,value) "
          + "VALUES (" + uid + ",'POST',1,1)");
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO community_votes(user_id,target_type,target_id,value) "
              + "VALUES (" + uid + ",'POST',1,-1)"));
      st.execute("DELETE FROM community_votes WHERE user_id=" + uid);
    }
  }

  @Test
  void communityQuestionEmbeddingVectorAndAiAnswerIdempotency() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      // question_embedding은 VECTOR(768)
      try (var rs = st.executeQuery(
          "SELECT format_type(a.atttypid, a.atttypmod) FROM pg_attribute a "
              + "JOIN pg_class cl ON cl.oid = a.attrelid "
              + "JOIN pg_namespace n ON n.oid = cl.relnamespace "
              + "WHERE n.nspname='public' AND cl.relname='community_questions' "
              + "AND a.attname='question_embedding' AND NOT a.attisdropped")) {
        assertTrue(rs.next(), "question_embedding 컬럼 필요");
        assertTrue("vector(768)".equalsIgnoreCase(rs.getString(1)), "question_embedding은 VECTOR(768)");
      }
      // community_ai_answers: status CHECK + PK(question_id) 멱등(중복 INSERT 거부)
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO community_ai_answers(question_id,status) VALUES (1,'PENDING')"));
      long qid = System.nanoTime();
      // questions row 선행(FK)
      long pid;
      try (var rs = st.executeQuery("INSERT INTO community_posts(author_id,board_type,title,body_md) "
          + "VALUES (1,'QNA','t','b') RETURNING id")) {
        assertTrue(rs.next()); pid = rs.getLong(1);
      }
      st.execute("INSERT INTO community_questions(post_id) VALUES (" + pid + ")");
      st.execute("INSERT INTO community_ai_answers(question_id,status) VALUES (" + pid + ",'DONE')");
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO community_ai_answers(question_id,status) VALUES (" + pid + ",'DONE')"));
      st.execute("DELETE FROM community_posts WHERE id=" + pid); // cascade
    }
  }

  @Test
  void communityNoAuthorFkAndUpdatedAtTrigger() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      long authorId = 999_999_000L + (System.nanoTime() % 100_000L);
      long pid;
      // author_id는 platform users 논리 참조다. FK가 없어야 존재하지 않는 id로도 INSERT가 통과한다.
      try (var rs = st.executeQuery("INSERT INTO community_posts(author_id,board_type,title,body_md) "
          + "VALUES (" + authorId + ",'QNA','t','b') RETURNING id")) {
        assertTrue(rs.next()); pid = rs.getLong(1);
      }
      st.execute("UPDATE community_posts SET updated_at = TIMESTAMPTZ '2000-01-01 00:00:00+00', "
          + "view_count = 1 WHERE id = " + pid);
      try (var rs = st.executeQuery(
          "SELECT updated_at > TIMESTAMPTZ '2020-01-01 00:00:00+00' "
              + "FROM community_posts WHERE id = " + pid)) {
        assertTrue(rs.next());
        assertTrue(rs.getBoolean(1), "updated_at trigger가 now()로 갱신되어야 한다");
      }
      st.execute("DELETE FROM community_posts WHERE id = " + pid);
    }
  }
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd devpath-shared && docker compose up -d && ./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest"`
Expected: 신규 4개 메서드 FAIL(테이블/컬럼 없음). 기존 테스트는 PASS.

- [ ] **Step 4: Write the migration SQL**

Create `V202606251001__community_qna.sql`:

```sql
-- MD3 Slice #8: community Q&A (posts, questions, answers, votes, tags, ai seed answers).
-- author_id = platform users logical reference only; NO cross-service FK.
-- Intra-domain FK allowed (questions->posts, answers->questions, post_tags->posts/tags).
-- vector extension created in V202606181006 (IF NOT EXISTS is idempotent-safe).
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE community_posts (
  id              BIGSERIAL PRIMARY KEY,
  author_id       BIGINT NOT NULL,
  board_type      VARCHAR(16) NOT NULL,
  title           VARCHAR(120) NOT NULL,
  body_md         TEXT NOT NULL,
  body_html       TEXT,
  status          VARCHAR(16) NOT NULL DEFAULT 'PUBLISHED',
  view_count      INT NOT NULL DEFAULT 0,
  upvote_count    INT NOT NULL DEFAULT 0,
  downvote_count  INT NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_community_posts_board CHECK (board_type IN ('QNA','FREE','PROJECT','STUDY','ALUMNI')),
  CONSTRAINT chk_community_posts_status CHECK (status IN ('DRAFT','PUBLISHED','HIDDEN','DELETED'))
);
CREATE INDEX idx_community_posts_board_status_created ON community_posts(board_type, status, created_at DESC);
CREATE INDEX idx_community_posts_author_created ON community_posts(author_id, created_at DESC);
CREATE TRIGGER community_posts_set_updated_at BEFORE UPDATE ON community_posts
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE community_questions (
  post_id            BIGINT PRIMARY KEY REFERENCES community_posts(id) ON DELETE CASCADE,
  is_solved          BOOLEAN NOT NULL DEFAULT FALSE,
  accepted_answer_id BIGINT,
  question_embedding VECTOR(768),
  learning_context   JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_community_questions_solved ON community_questions(is_solved, post_id DESC);

CREATE TABLE community_answers (
  id              BIGSERIAL PRIMARY KEY,
  question_id     BIGINT NOT NULL REFERENCES community_questions(post_id) ON DELETE CASCADE,
  author_id       BIGINT,
  body_md         TEXT NOT NULL,
  body_html       TEXT,
  is_ai_generated BOOLEAN NOT NULL DEFAULT FALSE,
  is_accepted     BOOLEAN NOT NULL DEFAULT FALSE,
  upvote_count    INT NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_community_answers_question ON community_answers(question_id);
CREATE TRIGGER community_answers_set_updated_at BEFORE UPDATE ON community_answers
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- accepted_answer_id FK는 community_answers 생성 후 추가(순환 정의 회피).
ALTER TABLE community_questions
  ADD CONSTRAINT fk_cq_accepted_answer FOREIGN KEY (accepted_answer_id)
  REFERENCES community_answers(id) ON DELETE SET NULL;

CREATE TABLE community_votes (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL,
  target_type VARCHAR(8) NOT NULL,
  target_id   BIGINT NOT NULL,
  value       SMALLINT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_community_votes_target CHECK (target_type IN ('POST','ANSWER')),
  CONSTRAINT chk_community_votes_value CHECK (value IN (-1, 1)),
  CONSTRAINT uq_community_votes UNIQUE (user_id, target_type, target_id)
);
CREATE INDEX idx_community_votes_target ON community_votes(target_type, target_id);

CREATE TABLE community_tags (
  id         BIGSERIAL PRIMARY KEY,
  name       VARCHAR(50) NOT NULL UNIQUE,
  post_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_community_tags_name_prefix ON community_tags(name text_pattern_ops);

CREATE TABLE community_post_tags (
  post_id BIGINT NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
  tag_id  BIGINT NOT NULL REFERENCES community_tags(id) ON DELETE CASCADE,
  PRIMARY KEY (post_id, tag_id)
);
CREATE INDEX idx_community_post_tags_tag ON community_post_tags(tag_id);

CREATE TABLE community_ai_answers (
  question_id     BIGINT PRIMARY KEY REFERENCES community_questions(post_id) ON DELETE CASCADE,
  answer_id       BIGINT REFERENCES community_answers(id) ON DELETE SET NULL,
  model_used      VARCHAR(64),
  prompt_version  VARCHAR(32),
  content         TEXT,
  reference_links JSONB NOT NULL DEFAULT '[]',
  status          VARCHAR(16) NOT NULL,
  error_code      VARCHAR(32),
  generated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_community_ai_answers_status CHECK (status IN ('DONE','FAILED'))
);
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest"`
Expected: 전체 PASS(신규 4개 포함). 실패 시 `docker compose` postgres 가동·`DB_URL` 확인.

- [ ] **Step 6: Run full shared test suite**

Run: `cd devpath-shared && ./gradlew test`
Expected: 전체 PASS(이벤트 2종 + Flyway + 기존).

- [ ] **Step 7: Commit**

```bash
git add devpath-shared/src/main/resources/db/migration/V202606251001__community_qna.sql \
        devpath-shared/src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(shared): community Q&A 스키마 V202606251001 (posts/questions/answers/votes/tags/ai_answers)"
```

---

## Task A4: main 릴리스 + publish

**Files:** (변경 없음 — 릴리스 작업)

- [ ] **Step 1: feature 브랜치 푸시 + main PR**

devpath-shared는 develop 부재 → `feat/*`→`main` 직접(Global Constraints).

```bash
cd devpath-shared
git checkout -b feat/slice8-community-schema   # 작업을 main에서 분기했다면
git push -u origin feat/slice8-community-schema
gh pr create --base main --title "feat(shared): 슬라이스 #8 커뮤니티 Q&A 스키마 + 이벤트 2종" \
  --body "community_qna 마이그레이션(V202606251001) + CommunityQuestionPostedEvent/CommunitySeedReadyEvent. FlywayMigrationTest 단언. 슬라이스 #8 빌드 A."
```

- [ ] **Step 2: CI 녹색 확인 후 머지**

Run: `gh pr checks --watch`
Expected: 전 체크 녹색. 녹색 확인 후 `gh pr merge --merge`.

- [ ] **Step 3: publish 확인**

main 머지 시 publish 워크플로가 GitHub Packages `0.0.1-SNAPSHOT`을 갱신하는지 확인(슬라이스 #7 A와 동일 경로). publish 워크플로가 수동이면 트리거.

Run: `gh run list --branch main --limit 3`
Expected: publish(또는 release) 워크플로 success. 이후 빌드 B1~C가 갱신된 jar 의존.

- [ ] **Step 4: 다음 빌드 진입 신호**

빌드 A 완료(스키마·이벤트 main 릴리스·publish)를 핸드오프/메모리에 기록. 빌드 B1(community-svc 코어) 플랜 작성으로 진행.

---

## Self-Review (스킬 체크리스트)

**1. Spec coverage**(설계서 §4 대비):
- 7개 테이블(posts·questions·answers·votes·tags·post_tags·ai_answers) → A3 SQL ✅
- 이벤트 2종(question.posted·seed.ready) → A1·A2 ✅
- 교차서비스 FK 없음 + 도메인 내 FK → SQL(author_id FK 없음, questions→posts FK 有) + `communityNoAuthorFkAndUpdatedAtTrigger` ✅
- vector(768)·UNIQUE 투표·멱등 ai_answers PK → `communityQuestionEmbeddingVectorAndAiAnswerIdempotency`·`communityQnaTablesAndVotesContract` ✅
- main 릴리스 선행 → A4 ✅
- 인덱스(board/status/created, votes target, tags prefix) → SQL + 단언 ✅

**2. Placeholder scan**: 모든 스텝에 실제 SQL/Java/명령 포함. TBD 없음 ✅

**3. Type consistency**: 이벤트 필드(questionId·postId·title·bodyMd / questionId·status·content·provider·questionEmbedding·errorCode)는 설계서 §4와 일치. 테이블/컬럼명은 A3 SQL과 FlywayMigrationTest 단언이 일치(community_posts·community_questions.post_id·community_ai_answers.question_id PK) ✅

> ⚠️ 주의: `community_questions.accepted_answer_id` FK는 `community_answers` 생성 후 `ALTER TABLE`로 추가(순환 정의 회피). `community_ai_answers.question_id`는 PK이자 멱등 키(별도 UNIQUE 불요).
