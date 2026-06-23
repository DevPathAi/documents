# 슬라이스 #6 빌드 A — shared `ai_code_reviews` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI 코드리뷰 결과를 영속할 `ai_code_reviews` 테이블을 중앙 shared Flyway에 추가하고, develop→main 릴리스(publish)로 다운스트림(ai-svc)이 의존할 수 있게 한다.

**Architecture:** shared `db/migration`에 신규 마이그레이션 1개를 추가한다(코드 변경 없음, DDL만). 검증은 `FlywayMigrationTest`에 계약 테스트를 추가해 테이블·컬럼·CHECK·UNIQUE·인덱스·트리거·교차서비스 no-FK를 단언한다. 다른 빌드(B~E)가 이 테이블 jar/스키마에 의존하므로 **A는 develop→main 릴리스(publish)를 선행**한다.

**Tech Stack:** PostgreSQL 17(pgvector) · Flyway · JUnit 5 · `PGSimpleDataSource` · Gradle(java-library).

## Global Constraints

- 대상 레포: `devpath-shared` 단독. 설계서 [2026-06-23-md2-slice6-ai-code-review-design](../specs/2026-06-23-md2-slice6-ai-code-review-design.md) §4·§9 빌드 A.
- 마이그레이션 번호 = 직전 최댓값 `V202606221001`(sandbox_sessions) **+1 → `V202606231001`**. 파일명 `V202606231001__ai_code_reviews.sql`.
- **교차서비스 FK 금지**(서비스 경계, 슬라이스 #2 교훈): `sandbox_session_id`·`user_id`·`content_id`는 논리 참조만, **FK 없음**.
- 공통 규약 `set_updated_at()` 트리거 함수는 `V202606150900__init_common.sql`에 이미 존재 — 재사용한다.
- 검증은 **fresh DB(`devpath_citest`)** 또는 CI(postgres pgvector)로 한다. 메인 `devpath` DB는 이미 다른 마이그레이션이 적용돼 있어 가짜통과 위험(슬라이스 #2/#3 교훈).
- 하위호환: 신규 테이블 추가만(기존 스키마 무변경).
- 신규 작업 브랜치는 `develop`에서 분기.

---

## File Structure

- Create: `src/main/resources/db/migration/V202606231001__ai_code_reviews.sql` — `ai_code_reviews` 테이블 DDL(컬럼·CHECK·UNIQUE·인덱스·트리거).
- Modify: `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java` — `aiCodeReviewsTableContract()`·`aiCodeReviewsNoUserFkAndUpdatedAtTrigger()` 두 계약 테스트 추가(기존 `sandboxSessionsTableContract`/`...HasNoUserFkAndUpdatedAtTrigger` 패턴 미러).

---

## Task 0: 작업 브랜치

- [ ] **Step 1: 브랜치 분기**

```powershell
cd devpath-shared
git switch develop
git pull
git switch -c feat/slice6-ai-code-reviews-schema
```

- [ ] **Step 2: 베이스라인 확인(기존 마이그레이션 녹색)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.shared.db.FlywayMigrationTest"
```

Expected: 기존 케이스 전부 PASS(fresh DB에 1006/1001 등 적용). 실패 시 이 작업과 무관한 환경 문제부터 규명(추측 금지).

---

## Task 1: `ai_code_reviews` 마이그레이션 + 계약 테스트

**Files:**
- Create: `src/main/resources/db/migration/V202606231001__ai_code_reviews.sql`
- Modify: `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`

**Interfaces:**
- Produces(다운스트림 B~E가 의존하는 스키마):
  - 테이블 `ai_code_reviews(id BIGSERIAL PK, sandbox_session_id BIGINT NOT NULL, user_id BIGINT NOT NULL, content_id BIGINT, status VARCHAR(16) NOT NULL DEFAULT 'PENDING', provider VARCHAR(16), confidence INT, strengths JSONB NOT NULL DEFAULT '[]', improvements JSONB NOT NULL DEFAULT '[]', security JSONB NOT NULL DEFAULT '[]', feedback VARCHAR(8), error_code VARCHAR(32), created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)`.
  - 제약: `UNIQUE(sandbox_session_id)`=`uq_ai_code_reviews_session`, `status ∈ {PENDING,DONE,FAILED}`, `feedback ∈ {UP,DOWN} 또는 NULL`, `confidence NULL 또는 0~100`.
  - 인덱스 `idx_ai_reviews_user_created(user_id, created_at DESC)`, 트리거 `ai_code_reviews_set_updated_at`.

- [ ] **Step 1: 실패 테스트 작성**

`FlywayMigrationTest.java`의 클래스 닫는 중괄호 `}` **직전**에 아래 두 메서드를 추가한다(기존 `sandboxSessions*` 테스트와 동일 스타일):

```java
  @Test
  void aiCodeReviewsTableContract() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      try (var rs = c.getMetaData().getTables(null, "public", "ai_code_reviews",
          new String[] {"TABLE"})) {
        assertTrue(rs.next(), "ai_code_reviews 테이블 필요");
      }
      var cols = columns("ai_code_reviews");
      for (String col : new String[] {"id", "sandbox_session_id", "user_id", "content_id",
          "status", "provider", "confidence", "strengths", "improvements", "security",
          "feedback", "error_code", "created_at", "updated_at"}) {
        assertTrue(cols.contains(col), "ai_code_reviews." + col + " 컬럼 필요");
      }

      // status CHECK
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO ai_code_reviews(sandbox_session_id,user_id,status) "
              + "VALUES (1,1,'BOGUS')"));
      // feedback CHECK
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO ai_code_reviews(sandbox_session_id,user_id,feedback) "
              + "VALUES (1,1,'MAYBE')"));
      // confidence 범위 CHECK
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO ai_code_reviews(sandbox_session_id,user_id,confidence) "
              + "VALUES (1,1,200)"));

      // UNIQUE(sandbox_session_id)
      long sid = System.nanoTime();
      st.execute("INSERT INTO ai_code_reviews(sandbox_session_id,user_id) VALUES ("
          + sid + ",1)");
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO ai_code_reviews(sandbox_session_id,user_id) VALUES ("
              + sid + ",2)"));
      st.execute("DELETE FROM ai_code_reviews WHERE sandbox_session_id = " + sid);

      try (var rs = st.executeQuery(
          "SELECT 1 FROM pg_indexes WHERE schemaname = 'public' "
              + "AND tablename = 'ai_code_reviews' "
              + "AND indexname = 'idx_ai_reviews_user_created'")) {
        assertTrue(rs.next(), "user 최신 리뷰 조회 인덱스 필요");
      }
    }
  }

  @Test
  void aiCodeReviewsNoUserFkAndUpdatedAtTrigger() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      long userId = 999_999_000L + (System.nanoTime() % 100_000L);
      long reviewId;
      // user_id/sandbox_session_id는 논리 참조다. FK가 없어야 존재하지 않는 id로도 INSERT가 통과한다.
      try (var rs = st.executeQuery(
          "INSERT INTO ai_code_reviews(sandbox_session_id,user_id,status) "
              + "VALUES (" + userId + "," + userId + ",'PENDING') RETURNING id")) {
        assertTrue(rs.next(), "ai_code_reviews id 필요");
        reviewId = rs.getLong(1);
      }
      st.execute("UPDATE ai_code_reviews "
          + "SET updated_at = TIMESTAMPTZ '2000-01-01 00:00:00+00', status = 'DONE' "
          + "WHERE id = " + reviewId);
      try (var rs = st.executeQuery(
          "SELECT updated_at > TIMESTAMPTZ '2020-01-01 00:00:00+00' "
              + "FROM ai_code_reviews WHERE id = " + reviewId)) {
        assertTrue(rs.next(), "updated_at 결과 필요");
        assertTrue(rs.getBoolean(1), "updated_at trigger가 now()로 갱신되어야 한다");
      }
      st.execute("DELETE FROM ai_code_reviews WHERE id = " + reviewId);
    }
  }
```

- [ ] **Step 2: 실패 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.shared.db.FlywayMigrationTest"
```

Expected: 신규 두 케이스 FAIL(`ai_code_reviews` 테이블 없음 → `assertTrue(rs.next())` 실패).

- [ ] **Step 3: 마이그레이션 작성**

`src/main/resources/db/migration/V202606231001__ai_code_reviews.sql`:

```sql
-- MD2 Slice #6: AI code review results (async, one per sandbox run).
-- sandbox_session_id(sandbox-svc) / user_id(platform) / content_id(learning) are
-- cross-service logical references only - NO FK (service boundary; slice #2 lesson).
CREATE TABLE ai_code_reviews (
  id                  BIGSERIAL PRIMARY KEY,
  sandbox_session_id  BIGINT NOT NULL,
  user_id             BIGINT NOT NULL,
  content_id          BIGINT,
  status              VARCHAR(16) NOT NULL DEFAULT 'PENDING',
  provider            VARCHAR(16),
  confidence          INT,
  strengths           JSONB NOT NULL DEFAULT '[]',
  improvements        JSONB NOT NULL DEFAULT '[]',
  security            JSONB NOT NULL DEFAULT '[]',
  feedback            VARCHAR(8),
  error_code          VARCHAR(32),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_ai_code_reviews_session UNIQUE (sandbox_session_id),
  CONSTRAINT chk_ai_review_status CHECK (status IN ('PENDING','DONE','FAILED')),
  CONSTRAINT chk_ai_review_feedback CHECK (feedback IS NULL OR feedback IN ('UP','DOWN')),
  CONSTRAINT chk_ai_review_confidence CHECK (confidence IS NULL OR (confidence BETWEEN 0 AND 100))
);

CREATE INDEX idx_ai_reviews_user_created ON ai_code_reviews(user_id, created_at DESC);

CREATE TRIGGER ai_code_reviews_set_updated_at BEFORE UPDATE ON ai_code_reviews
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

- [ ] **Step 4: 통과 확인(fresh DB)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.shared.db.FlywayMigrationTest"
```

Expected: 신규 두 케이스 포함 전부 PASS.

- [ ] **Step 5: 커밋**

```powershell
git add src/main/resources/db/migration/V202606231001__ai_code_reviews.sql src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(schema): add ai_code_reviews table for slice 6 code review"
```

---

## Task 2: 전체 회귀 + develop PR

- [ ] **Step 1: 전체 테스트(fresh DB)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat clean test
```

Expected: 전 마이그레이션 테스트 PASS, 회귀 없음.

- [ ] **Step 2: PR 생성(develop 대상)**

```powershell
git push -u origin feat/slice6-ai-code-reviews-schema
gh pr create --base develop --title "feat(schema): ai_code_reviews 테이블(슬라이스 #6 빌드 A)" --body "AI 코드리뷰 결과 영속 테이블 추가(교차서비스 FK 없음, status/feedback/confidence CHECK, UNIQUE(sandbox_session_id), updated_at 트리거). 설계서 docs/superpowers/specs/2026-06-23-md2-slice6-ai-code-review-design.md"
```

- [ ] **Step 3: CI 녹색 확인**

```powershell
gh pr checks --watch
```

Expected: shared CI(postgres pgvector) build 녹색. 녹색 확인 후에만 머지(컨트롤러 직접 검증).

- [ ] **Step 4: develop 머지**

```powershell
gh pr merge --merge
```

---

## Task 3: develop→main 릴리스 (publish) — **B~E 선행**

> shared는 main이 GitHub Packages publish 소스다. ai-svc(빌드 C) 등이 `ai.devpath:devpath-shared` jar로 신규 스키마/이벤트에 의존하므로, **B 시작 전 main 릴리스가 완료**돼야 한다(슬라이스 #2~#5 빌드 A 동일 패턴).

- [ ] **Step 1: 릴리스 PR(develop→main)**

```powershell
gh pr create --base main --head develop --title "release: ai_code_reviews 스키마(슬라이스 #6 빌드 A)" --body "슬라이스 #6 빌드 A develop→main 릴리스. main push로 publish.yml(Packages 배포) 트리거."
```

- [ ] **Step 2: CI 녹색 → 머지 → publish 확인**

```powershell
gh pr checks --watch
gh pr merge --merge
# main push 후 publish 워크플로 성공 확인
gh run list --branch main --limit 3
```

Expected: main build + `publish`(./gradlew publish) 성공. `ai.devpath:devpath-shared:0.0.1-SNAPSHOT`에 `ai_code_reviews` 스키마 반영. **이후 빌드 B~E는 `--refresh-dependencies`로 최신 shared 수신**(슬라이스 #3 교훈: 로컬 gradle 캐시가 옛 shared에 고정될 수 있음).

---

## Self-Review 메모(작성자)

- **Spec 커버리지**: §4 데이터 모델(컬럼·CHECK·UNIQUE·인덱스·트리거)=Task1 DDL+테스트. §9 빌드 A "develop→main 릴리스 선행"=Task3. 전부 매핑.
- **placeholder 없음**: 모든 SQL·테스트·명령은 실제값. 마이그레이션 번호 `V202606231001` 확정(직전 `V202606221001`+1).
- **타입 일관성**: 컬럼명·제약명(`uq_ai_code_reviews_session`·`chk_ai_review_status`·`chk_ai_review_feedback`·`chk_ai_review_confidence`·`idx_ai_reviews_user_created`·트리거 `ai_code_reviews_set_updated_at`)이 DDL·테스트·다운스트림(B~E) 참조와 일치.
- **교차서비스 FK 없음**: `aiCodeReviewsNoUserFkAndUpdatedAtTrigger`가 존재하지 않는 id INSERT 통과로 실증(슬라이스 #2 교훈).
