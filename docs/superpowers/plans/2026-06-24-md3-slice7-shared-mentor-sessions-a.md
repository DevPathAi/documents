# 슬라이스 #7 빌드 A — shared `ai_mentor_sessions` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI 멘토 단발 Q&A를 영속할 `ai_mentor_sessions` 테이블을 중앙 shared Flyway에 추가하고, develop→main 릴리스(publish)로 다운스트림(ai-svc 빌드 D)이 의존할 수 있게 한다.

**Architecture:** shared `db/migration`에 신규 마이그레이션 1개를 추가한다(코드 변경 없음, DDL만). 검증은 `FlywayMigrationTest`에 계약 테스트를 추가해 테이블·컬럼·CHECK·인덱스·트리거·교차서비스 no-FK를 단언한다. 멘토는 Kafka 미사용이라 **shared 이벤트 변경은 없다**(테이블 DDL만). 빌드 D(ai-svc)가 이 테이블 jar/스키마에 의존하므로 **A는 develop→main 릴리스(publish)를 선행**한다.

**Tech Stack:** PostgreSQL 17(pgvector) · Flyway · JUnit 5 · `PGSimpleDataSource` · Gradle(java-library).

## Global Constraints

- 대상 레포: `devpath-shared` 단독. 설계서 [2026-06-24-md3-slice7-ai-mentor-design](../specs/2026-06-24-md3-slice7-ai-mentor-design.md) §4·§9 빌드 A.
- 마이그레이션 번호 = 직전 최댓값 `V202606231001`(ai_code_reviews) **+1 → `V202606241001`**. 파일명 `V202606241001__ai_mentor_sessions.sql`. (착수 시 `db/migration` 최댓값을 재실측해 충돌 없으면 확정.)
- **교차서비스 FK 금지**(서비스 경계, 슬라이스 #2 교훈): `user_id`·`content_id`는 논리 참조만, **FK 없음**.
- 공통 규약 `set_updated_at()` 트리거 함수는 `V202606150900__init_common.sql`에 이미 존재 — 재사용한다.
- 검증은 **fresh DB(`devpath_citest`)** 또는 CI(postgres pgvector)로 한다. 메인 `devpath` DB는 이미 다른 마이그레이션이 적용돼 가짜통과 위험(슬라이스 #2/#3 교훈).
- 하위호환: 신규 테이블 추가만(기존 스키마 무변경). 멘토는 단발·동기라 **UNIQUE 제약 없음**(멱등 키 불요, ai_code_reviews와 차이).
- `status` CHECK ∈ {DONE, FAILED}만(PENDING 없음 — 스트림 완료 후에만 영속, 설계 M-6). `reference_links`는 SQL 예약어 `references` 회피용 컬럼명(설계 §4).
- 신규 작업 브랜치는 `develop`에서 분기.

---

## File Structure

- Create: `src/main/resources/db/migration/V202606241001__ai_mentor_sessions.sql` — `ai_mentor_sessions` 테이블 DDL(컬럼·CHECK·인덱스·트리거).
- Modify: `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java` — `aiMentorSessionsTableContract()`·`aiMentorSessionsNoUserFkAndUpdatedAtTrigger()` 두 계약 테스트 추가(기존 `aiCodeReviews*` 패턴 미러).

---

## Task 0: 작업 브랜치

- [ ] **Step 1: 브랜치 분기 + 마이그레이션 최댓값 재실측**

```powershell
cd devpath-shared
git switch develop
git pull
git switch -c feat/slice7-ai-mentor-sessions-schema
# db/migration 최댓값 확인 — V202606231001가 최신이면 신규는 V202606241001
ls src/main/resources/db/migration
```

Expected: 최신 마이그레이션 `V202606231001__ai_code_reviews.sql`. 신규 번호 `V202606241001` 확정(더 큰 번호가 있으면 그 +1로 조정 — 추측 금지, 실측).

- [ ] **Step 2: 베이스라인 확인(기존 마이그레이션 녹색)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.shared.db.FlywayMigrationTest"
```

Expected: 기존 케이스 전부 PASS(fresh DB에 1006/2210/2310 등 적용). 실패 시 이 작업과 무관한 환경 문제부터 규명(추측 금지).

---

## Task 1: `ai_mentor_sessions` 마이그레이션 + 계약 테스트

**Files:**
- Create: `src/main/resources/db/migration/V202606241001__ai_mentor_sessions.sql`
- Modify: `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`

**Interfaces:**
- Produces(빌드 D ai-svc `AiMentorSession` 엔티티가 의존하는 스키마):
  - 테이블 `ai_mentor_sessions(id BIGSERIAL PK, user_id BIGINT NOT NULL, content_id BIGINT, question TEXT NOT NULL, answer TEXT NOT NULL DEFAULT '', context_snapshot JSONB NOT NULL DEFAULT '{}', reference_links JSONB NOT NULL DEFAULT '[]', provider VARCHAR(16), status VARCHAR(16) NOT NULL, error_code VARCHAR(32), created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)`.
  - 제약: `status ∈ {DONE,FAILED}`=`chk_ai_mentor_status`. **UNIQUE 없음**(단발 동기).
  - 인덱스 `idx_ai_mentor_user_created(user_id, created_at DESC)`, 트리거 `ai_mentor_sessions_set_updated_at`.

- [ ] **Step 1: 실패 테스트 작성**

`FlywayMigrationTest.java`의 클래스 닫는 중괄호 `}` **직전**에 아래 두 메서드를 추가한다(기존 `aiCodeReviews*` 테스트와 동일 스타일— 같은 파일에서 `columns(...)`·`dataSource()` 헬퍼 시그니처를 실측해 맞춘다):

```java
  @Test
  void aiMentorSessionsTableContract() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      try (var rs = c.getMetaData().getTables(null, "public", "ai_mentor_sessions",
          new String[] {"TABLE"})) {
        assertTrue(rs.next(), "ai_mentor_sessions 테이블 필요");
      }
      var cols = columns("ai_mentor_sessions");
      for (String col : new String[] {"id", "user_id", "content_id", "question", "answer",
          "context_snapshot", "reference_links", "provider", "status", "error_code",
          "created_at", "updated_at"}) {
        assertTrue(cols.contains(col), "ai_mentor_sessions." + col + " 컬럼 필요");
      }

      // status CHECK (DONE/FAILED만)
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO ai_mentor_sessions(user_id,question,status) "
              + "VALUES (1,'q','PENDING')"));
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO ai_mentor_sessions(user_id,question,status) "
              + "VALUES (1,'q','BOGUS')"));

      // JSONB 기본값 + 단발(UNIQUE 없음): 같은 user로 2건 INSERT 통과
      long uid = System.nanoTime();
      st.execute("INSERT INTO ai_mentor_sessions(user_id,question,status) VALUES ("
          + uid + ",'q1','DONE')");
      st.execute("INSERT INTO ai_mentor_sessions(user_id,question,status) VALUES ("
          + uid + ",'q2','DONE')");
      try (var rs = st.executeQuery(
          "SELECT count(*) FROM ai_mentor_sessions WHERE user_id = " + uid)) {
        assertTrue(rs.next());
        assertTrue(rs.getInt(1) == 2, "단발이라 동일 user 다건 허용(UNIQUE 없음)");
      }
      st.execute("DELETE FROM ai_mentor_sessions WHERE user_id = " + uid);

      try (var rs = st.executeQuery(
          "SELECT 1 FROM pg_indexes WHERE schemaname = 'public' "
              + "AND tablename = 'ai_mentor_sessions' "
              + "AND indexname = 'idx_ai_mentor_user_created'")) {
        assertTrue(rs.next(), "user 최신 멘토 이력 조회 인덱스 필요");
      }
    }
  }

  @Test
  void aiMentorSessionsNoUserFkAndUpdatedAtTrigger() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      long userId = 999_999_000L + (System.nanoTime() % 100_000L);
      long sessionId;
      // user_id/content_id는 논리 참조다. FK가 없어야 존재하지 않는 id로도 INSERT가 통과한다.
      try (var rs = st.executeQuery(
          "INSERT INTO ai_mentor_sessions(user_id,content_id,question,status) "
              + "VALUES (" + userId + "," + userId + ",'q','DONE') RETURNING id")) {
        assertTrue(rs.next(), "ai_mentor_sessions id 필요");
        sessionId = rs.getLong(1);
      }
      st.execute("UPDATE ai_mentor_sessions "
          + "SET updated_at = TIMESTAMPTZ '2000-01-01 00:00:00+00', answer = 'a' "
          + "WHERE id = " + sessionId);
      try (var rs = st.executeQuery(
          "SELECT updated_at > TIMESTAMPTZ '2020-01-01 00:00:00+00' "
              + "FROM ai_mentor_sessions WHERE id = " + sessionId)) {
        assertTrue(rs.next(), "updated_at 결과 필요");
        assertTrue(rs.getBoolean(1), "updated_at trigger가 now()로 갱신되어야 한다");
      }
      st.execute("DELETE FROM ai_mentor_sessions WHERE id = " + sessionId);
    }
  }
```

> ⚠️ 구현 시 `FlywayMigrationTest`의 기존 `aiCodeReviews*` 메서드를 열어 `columns(String)`·`dataSource()` 헬퍼의 정확한 시그니처/임포트(`assertTrue`·`assertThrows`·`Flyway`)를 실측해 위 코드를 맞춘다(추측 금지). 기존 패턴과 1:1 동형이면 그대로 통과한다.

- [ ] **Step 2: 실패 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.shared.db.FlywayMigrationTest"
```

Expected: 신규 두 케이스 FAIL(`ai_mentor_sessions` 테이블 없음 → `assertTrue(rs.next())` 실패).

- [ ] **Step 3: 마이그레이션 작성**

`src/main/resources/db/migration/V202606241001__ai_mentor_sessions.sql`:

```sql
-- MD3 Slice #7: AI mentor Q&A sessions (single-turn, one row per question-answer).
-- user_id(platform) / content_id(learning) are cross-service logical references only
-- - NO FK (service boundary; slice #2 lesson). No Kafka/event (synchronous SSE).
CREATE TABLE ai_mentor_sessions (
  id                BIGSERIAL PRIMARY KEY,
  user_id           BIGINT NOT NULL,
  content_id        BIGINT,
  question          TEXT NOT NULL,
  answer            TEXT NOT NULL DEFAULT '',
  context_snapshot  JSONB NOT NULL DEFAULT '{}',
  reference_links   JSONB NOT NULL DEFAULT '[]',
  provider          VARCHAR(16),
  status            VARCHAR(16) NOT NULL,
  error_code        VARCHAR(32),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_ai_mentor_status CHECK (status IN ('DONE','FAILED'))
);

-- 사용자별 멘토 이력 최신순(단발 Q&A, UNIQUE 불요).
CREATE INDEX idx_ai_mentor_user_created ON ai_mentor_sessions(user_id, created_at DESC);

CREATE TRIGGER ai_mentor_sessions_set_updated_at BEFORE UPDATE ON ai_mentor_sessions
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
git add src/main/resources/db/migration/V202606241001__ai_mentor_sessions.sql src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(schema): add ai_mentor_sessions table for slice 7 AI mentor"
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
git push -u origin feat/slice7-ai-mentor-sessions-schema
gh pr create --base develop --title "feat(schema): ai_mentor_sessions 테이블(슬라이스 #7 빌드 A)" --body "AI 멘토 단발 Q&A 영속 테이블 추가(교차서비스 FK 없음, status DONE/FAILED CHECK, context_snapshot/reference_links JSONB, idx_ai_mentor_user_created, updated_at 트리거, UNIQUE 없음). 설계서 docs/superpowers/specs/2026-06-24-md3-slice7-ai-mentor-design.md §4"
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

## Task 3: develop→main 릴리스 (publish) — **D 선행**

> shared는 main이 GitHub Packages publish 소스다. ai-svc(빌드 D)가 `ai.devpath:devpath-shared` jar로 `ai_mentor_sessions` 스키마에 의존하므로, **D 시작 전 main 릴리스가 완료**돼야 한다(슬라이스 #2~#6 빌드 A 동일 패턴). 빌드 B(sandbox)·C(learning)는 이 테이블에 의존하지 않지만(별도 스키마) 슬라이스 순서상 A 머지 후 진행.

- [ ] **Step 1: 릴리스 PR(develop→main)**

```powershell
gh pr create --base main --head develop --title "release: ai_mentor_sessions 스키마(슬라이스 #7 빌드 A)" --body "슬라이스 #7 빌드 A develop→main 릴리스. main push로 publish.yml(Packages 배포) 트리거. (이번 릴리스에 Tier-1 종결 fix 4건·문서 등 미릴리스 develop 분이 함께 포함될 수 있으니 diff 확인.)"
```

> ⚠️ 핸드오프 §2: develop에 미릴리스분(잠재결함 4건 fix·문서)이 있을 수 있다. 이 릴리스 PR diff를 확인해 의도한 범위(스키마 + 누적분)가 맞는지 검토 후 머지(추측 금지).

- [ ] **Step 2: CI 녹색 → 머지 → publish 확인**

```powershell
gh pr checks --watch
gh pr merge --merge
# main push 후 publish 워크플로 성공 확인
gh run list --branch main --limit 3
```

Expected: main build + `publish`(./gradlew publish) 성공. `ai.devpath:devpath-shared:0.0.1-SNAPSHOT`에 `ai_mentor_sessions` 스키마 반영. **이후 빌드 D는 `--refresh-dependencies`로 최신 shared 수신**(슬라이스 #3 교훈: 로컬 gradle 캐시가 옛 shared에 고정될 수 있음).

---

## Self-Review 메모(작성자)

- **Spec 커버리지**: §4 데이터 모델(컬럼·CHECK·인덱스·트리거·UNIQUE 없음·reference_links 컬럼명)=Task1 DDL+테스트. §9 빌드 A "develop→main 릴리스 선행"=Task3. 전부 매핑.
- **placeholder 없음**: 모든 SQL·테스트·명령은 실제값. 마이그레이션 번호 `V202606241001`(직전 `V202606231001`+1, 착수 시 재실측 지시).
- **타입 일관성**: 컬럼명·제약명(`chk_ai_mentor_status`·`idx_ai_mentor_user_created`·트리거 `ai_mentor_sessions_set_updated_at`)이 DDL·테스트·빌드 D(`AiMentorSession` 엔티티) 참조와 일치. `status VARCHAR(16)`·`provider VARCHAR(16)`·`error_code VARCHAR(32)`(ai_code_reviews 규약 동형).
- **#6과 차이(의도적)**: UNIQUE 제약 없음(단발 동기, 멱등 키 불요), status는 DONE/FAILED만(PENDING 없음 — 완료 후 영속, M-6), `context_snapshot`·`reference_links` JSONB(코드리뷰의 strengths/improvements/security와 다른 멘토 고유 컬럼). 테스트가 "동일 user 다건 INSERT 통과"로 UNIQUE 부재를 실증.
- **교차서비스 FK 없음**: `aiMentorSessionsNoUserFkAndUpdatedAtTrigger`가 존재하지 않는 id INSERT 통과로 실증(슬라이스 #2 교훈).
