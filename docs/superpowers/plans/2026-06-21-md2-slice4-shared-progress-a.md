# MD2 슬라이스 #4 빌드 A — devpath-shared user_content_progress 스키마 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `devpath-shared`에 콘텐츠 읽기 진척 저장용 `user_content_progress` Flyway 마이그레이션을 추가하고, 다운스트림 `devpath-learning-svc`가 콘텐츠 뷰어/진척 API를 구현할 수 있게 develop -> main 릴리스(publish)까지 완료한다.

**Architecture:** 슬라이스 #3에서 이미 `contents` 테이블이 shared 스키마에 들어갔다. 빌드 A는 그 `contents(id)`를 참조하는 learning 도메인 내부 progress 테이블만 추가한다. `user_id`는 platform users의 논리 참조이므로 교차서비스 FK를 두지 않고, `content_id`는 learning 도메인 내부 FK로 `ON DELETE CASCADE`를 둔다. progress 값은 서버에서 monotonic upsert할 수 있도록 `(user_id, content_id)` unique와 `scroll_pct`/`dwell_sec` CHECK 제약으로 방어한다.

**Tech Stack:** Java 21 · Gradle(Kotlin DSL, java-library) · Flyway 11.8.2 · PostgreSQL 17 + pgvector 이미지 유지 · JUnit 5 · maven-publish.

## Global Constraints

- 레포 절대조건: 추측 금지 · **테스트 우선** · 문제 시 코드 분석. (`devpath-shared/CLAUDE.md`)
- 신규 작업은 반드시 `develop`에서 작업 브랜치 분기. `develop`/`main` 직접 작업 금지.
- 범위는 **빌드 A(shared schema)만**이다. learning-svc API, gateway route, frontend progress tracking은 빌드 C/D/E 범위다.
- 마이그레이션은 **schema only**. 대량 콘텐츠/문항 seed, approved JSON, embedding seed는 빌드 B1/B2 범위다.
- 마이그레이션 파일명은 `V<YYYYMMDD><4자리>__<설명>.sql`. 현재 최신은 `V202606181006__learning_path_schema.sql`이므로 본 계획은 `V202606211001__user_content_progress.sql`을 사용한다. 날짜 부분은 **구현 당일 기준**이며(본 계획 작성일 2026-06-21), 어떤 경우든 최신 `V202606181006`보다 큰 버전이어야 한다. 구현 시 이미 같은 날짜의 신규 마이그레이션이 있으면 다음 sequence로 올리고 파일명/테스트/커밋 메시지를 함께 맞춘다.
- `user_id`는 BIGINT NOT NULL이지만 FK 없음(서비스 경계). `content_id`는 `contents(id)` FK + `ON DELETE CASCADE`.
- progress 완료 판정(`scrollPct >= 0.8 AND dwellSec >= 45`)과 ACTIVE path task 자동완료는 learning-svc 빌드 C에서 구현한다. shared는 저장 가능한 데이터 구조와 제약만 제공한다.

---

## File Structure

- Create: `devpath-shared/src/main/resources/db/migration/V202606211001__user_content_progress.sql`
- Modify: `devpath-shared/src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`

---

## Task 0: 작업 브랜치 준비

- [ ] **Step 1: develop 최신화**

```powershell
cd devpath-shared
git switch develop
git pull
```

- [ ] **Step 2: 신규 작업 브랜치 생성**

```powershell
git switch -c feat/slice4-user-content-progress
```

- [ ] **Step 3: 현재 마이그레이션 번호 확인**

```powershell
Get-ChildItem src/main/resources/db/migration | Sort-Object Name | Select-Object Name
```

Expected: 최신이 `V202606181006__learning_path_schema.sql`이면 본 계획대로 `V202606211001__user_content_progress.sql` 사용.

---

## Task 1: user_content_progress 계약 테스트 먼저 추가

**Files:**
- Modify: `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`

**Interfaces:**
- Consumes: 기존 `contents(id)` from `V202606181006__learning_path_schema.sql`, `set_updated_at()` from common migration.
- Produces: 실패 테스트. 아직 마이그레이션이 없으므로 테이블/제약 검증이 FAIL해야 한다.

- [ ] **Step 1: 테이블/제약/트리거 테스트 추가**

`FlywayMigrationTest.java`의 마지막 테스트 뒤, 클래스 닫는 `}` 앞에 아래 메서드를 추가한다. 새 import 없이 현재 `assertTrue`/`assertThrows`만 사용한다.

```java
  @Test
  void userContentProgressTableContract() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      try (var rs = c.getMetaData().getTables(null, "public", "user_content_progress",
          new String[] {"TABLE"})) {
        assertTrue(rs.next(), "user_content_progress 테이블 필요");
      }

      var cols = columns("user_content_progress");
      for (String col : new String[] {"id", "user_id", "content_id", "scroll_pct",
          "dwell_sec", "completed_at", "created_at", "updated_at"}) {
        assertTrue(cols.contains(col), "user_content_progress." + col + " 컬럼 필요");
      }

      try (var rs = st.executeQuery(
          "SELECT 1 FROM pg_constraint WHERE conname = 'uq_ucp_user_content'")) {
        assertTrue(rs.next(), "user_id + content_id unique constraint 필요");
      }
      try (var rs = st.executeQuery(
          "SELECT 1 FROM pg_constraint WHERE conname = 'chk_ucp_scroll'")) {
        assertTrue(rs.next(), "scroll_pct 범위 CHECK 필요");
      }
      try (var rs = st.executeQuery(
          "SELECT 1 FROM pg_constraint WHERE conname = 'chk_ucp_dwell'")) {
        assertTrue(rs.next(), "dwell_sec 비음수 CHECK 필요");
      }
      try (var rs = st.executeQuery(
          "SELECT 1 FROM pg_indexes WHERE schemaname = 'public' "
              + "AND tablename = 'user_content_progress' "
              + "AND indexname = 'idx_ucp_user_updated'")) {
        assertTrue(rs.next(), "user 최신 progress 조회 인덱스 필요");
      }
      try (var rs = st.executeQuery(
          "SELECT 1 FROM pg_indexes WHERE schemaname = 'public' "
              + "AND tablename = 'user_content_progress' "
              + "AND indexname = 'idx_ucp_content'")) {
        assertTrue(rs.next(), "content_id 인덱스 필요");
      }
    }
  }

  @Test
  void userContentProgressConstraintsAndCascadeWork() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      long userId = System.nanoTime();
      long contentId;
      try (var rs = st.executeQuery("INSERT INTO contents(slug,title,track,content_md) "
          + "VALUES ('ucp-" + userId + "','t','BACKEND_SPRING','m') RETURNING id")) {
        assertTrue(rs.next(), "content id 필요");
        contentId = rs.getLong(1);
      }

      st.execute("INSERT INTO user_content_progress(user_id,content_id,scroll_pct,dwell_sec) "
          + "VALUES (" + userId + "," + contentId + ",0.4,10)");

      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO user_content_progress(user_id,content_id,scroll_pct,dwell_sec) "
              + "VALUES (" + userId + "," + contentId + ",0.5,11)"));
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO user_content_progress(user_id,content_id,scroll_pct,dwell_sec) "
              + "VALUES (" + (userId + 1) + "," + contentId + ",-0.1,10)"));
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO user_content_progress(user_id,content_id,scroll_pct,dwell_sec) "
              + "VALUES (" + (userId + 2) + "," + contentId + ",1.1,10)"));
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO user_content_progress(user_id,content_id,scroll_pct,dwell_sec) "
              + "VALUES (" + (userId + 3) + "," + contentId + ",0.2,-1)"));

      st.execute("DELETE FROM contents WHERE id = " + contentId);
      try (var rs = st.executeQuery(
          "SELECT count(*) FROM user_content_progress WHERE user_id = " + userId)) {
        assertTrue(rs.next(), "count 결과 필요");
        assertTrue(rs.getLong(1) == 0L, "content 삭제 시 progress도 cascade 삭제되어야 한다");
      }
    }
  }

  @Test
  void userContentProgressHasNoUserForeignKeyAndUpdatedAtTrigger() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      long userId = 999_999_000L + (System.nanoTime() % 100_000L);
      long contentId;
      long progressId;
      try (var rs = st.executeQuery("INSERT INTO contents(slug,title,track,content_md) "
          + "VALUES ('ucp-trigger-" + userId + "','t','BACKEND_SPRING','m') RETURNING id")) {
        assertTrue(rs.next(), "content id 필요");
        contentId = rs.getLong(1);
      }

      // user_id는 platform users 논리 참조다. users FK가 없어야 이 INSERT가 통과한다.
      try (var rs = st.executeQuery(
          "INSERT INTO user_content_progress(user_id,content_id) VALUES ("
              + userId + "," + contentId + ") RETURNING id")) {
        assertTrue(rs.next(), "progress id 필요");
        progressId = rs.getLong(1);
      }

      st.execute("UPDATE user_content_progress "
          + "SET updated_at = TIMESTAMPTZ '2000-01-01 00:00:00+00', dwell_sec = 1 "
          + "WHERE id = " + progressId);
      try (var rs = st.executeQuery(
          "SELECT updated_at > TIMESTAMPTZ '2020-01-01 00:00:00+00' "
              + "FROM user_content_progress WHERE id = " + progressId)) {
        assertTrue(rs.next(), "updated_at 결과 필요");
        assertTrue(rs.getBoolean(1), "updated_at trigger가 now()로 갱신되어야 한다");
      }

      st.execute("DELETE FROM contents WHERE id = " + contentId);
    }
  }
```

- [ ] **Step 2: 테스트 실패 확인**

Postgres는 슬라이스 #3 이후 pgvector 이미지여야 한다.

```powershell
docker compose up -d postgres
.\gradlew.bat test --tests ai.devpath.shared.db.FlywayMigrationTest
```

Expected: 신규 `userContentProgress*` 테스트들이 FAIL. 실패 이유는 `user_content_progress` 테이블/제약/인덱스가 없기 때문이다.

---

## Task 2: user_content_progress 마이그레이션 작성

**Files:**
- Create: `src/main/resources/db/migration/V202606211001__user_content_progress.sql`

**Interfaces:**
- Consumes: `contents(id)` table.
- Produces: `user_content_progress` table for learning-svc Build C progress upsert.

- [ ] **Step 1: 마이그레이션 작성**

`V202606211001__user_content_progress.sql`:

```sql
-- MD2 Slice #4: user content reading progress.
-- user_id is a logical platform users reference only; no cross-service FK.
CREATE TABLE user_content_progress (
  id           BIGSERIAL PRIMARY KEY,
  user_id      BIGINT NOT NULL,
  content_id   BIGINT NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
  scroll_pct   DOUBLE PRECISION NOT NULL DEFAULT 0,
  dwell_sec    INT NOT NULL DEFAULT 0,
  completed_at TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_ucp_user_content UNIQUE (user_id, content_id),
  CONSTRAINT chk_ucp_scroll CHECK (scroll_pct >= 0 AND scroll_pct <= 1),
  CONSTRAINT chk_ucp_dwell CHECK (dwell_sec >= 0)
);

CREATE INDEX idx_ucp_user_updated ON user_content_progress(user_id, updated_at DESC);
CREATE INDEX idx_ucp_content ON user_content_progress(content_id);

CREATE TRIGGER user_content_progress_set_updated_at BEFORE UPDATE ON user_content_progress
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

- [ ] **Step 2: focused test 통과 확인**

```powershell
.\gradlew.bat test --tests ai.devpath.shared.db.FlywayMigrationTest
```

Expected: 기존 Flyway 테스트 + 신규 progress 테스트 전부 PASS.

- [ ] **Step 3: 커밋**

```powershell
git add src/main/resources/db/migration/V202606211001__user_content_progress.sql `
        src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(db): add user content progress schema"
```

---

## Task 3: 전체 검증

- [ ] **Step 1: 전체 테스트**

```powershell
.\gradlew.bat test
```

Expected: BUILD SUCCESSFUL, 모든 JUnit 테스트 PASS.

- [ ] **Step 2: 전체 빌드**

```powershell
.\gradlew.bat clean build
```

Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: schema scan**

```powershell
rg -n "user_content_progress|uq_ucp_user_content|chk_ucp_scroll|idx_ucp_user_updated" src/main src/test
```

Expected: 마이그레이션 SQL과 FlywayMigrationTest에서만 매칭.

---

## Task 4: develop PR

- [ ] **Step 1: 브랜치 push**

```powershell
git push -u origin feat/slice4-user-content-progress
```

- [ ] **Step 2: develop PR 생성**

```powershell
gh pr create --base develop --head feat/slice4-user-content-progress `
  --title "feat: MD2 slice4 user content progress schema" `
  --body "Adds user_content_progress schema and Flyway contract tests for content reading progress."
```

- [ ] **Step 3: CI 녹색 확인 후 merge commit**

CI에서 pgvector DB 이미지가 유지되어야 한다. 본 빌드는 pgvector 자체를 새로 쓰지는 않지만 기존 `V202606181006` 때문에 plain postgres에서는 Flyway가 실패한다.

---

## Task 5: develop -> main 릴리스(publish)

> 빌드 C(`devpath-learning-svc`)가 새 테이블을 test/dev DB에서 소비하려면 shared가 main에서 publish되어야 한다. 슬라이스 #2/#3와 동일한 선행 조건이다.

- [ ] **Step 1: develop -> main 릴리스 PR**

```powershell
gh pr create --base main --head develop `
  --title "release: MD2 slice4 user content progress schema" `
  --body "Publishes shared schema for user_content_progress so learning-svc content progress APIs can consume it."
```

- [ ] **Step 2: main merge 후 publish 확인**

main 머지 후 `publish.yml` GitHub Actions가 새 shared artifact를 publish하는지 확인한다.

- [ ] **Step 3: 다운스트림 안내**

learning-svc 빌드 C 착수 전 로컬/CI에서 shared 최신 artifact를 보도록 한다.

```powershell
.\gradlew.bat --refresh-dependencies test
```

---

## Acceptance Checklist

- [ ] `V202606211001__user_content_progress.sql`가 추가되어 있다.
- [ ] `user_content_progress`는 `id`, `user_id`, `content_id`, `scroll_pct`, `dwell_sec`, `completed_at`, `created_at`, `updated_at` 컬럼을 가진다.
- [ ] `(user_id, content_id)` unique가 있다.
- [ ] `scroll_pct`는 0.0~1.0 범위 밖 값을 거부한다.
- [ ] `dwell_sec`는 음수를 거부한다.
- [ ] `content_id`는 `contents(id) ON DELETE CASCADE` FK다.
- [ ] `user_id`는 users FK가 아니며, 존재하지 않는 user id로도 progress insert가 가능하다.
- [ ] `updated_at` trigger가 update 시 갱신된다.
- [ ] `idx_ucp_user_updated`, `idx_ucp_content` 인덱스가 있다.
- [ ] `.\gradlew.bat test`와 `.\gradlew.bat clean build`가 통과한다.
- [ ] develop PR이 CI 녹색으로 머지되고, main 릴리스 publish가 완료된다.

---

## Self-Review

- **Spec coverage:** 슬라이스 #4 설계서 §5.2 신규 `user_content_progress`, §9 Build A, §11.1 shared 테스트 전략(unique/check/trigger/cascade)을 커버한다.
- **Current source alignment:** 현재 shared 최신 마이그레이션은 `V202606181006__learning_path_schema.sql`이며 `contents`와 `set_updated_at()`이 이미 존재한다. 본 빌드는 그 위에 progress 테이블만 추가한다.
- **검수 확인(실코드 대조 완료):** `FlywayMigrationTest.java`에 `dataSource()`(L20)와 `private static java.util.Set<String> columns(String)`(L52) 헬퍼가 이미 있고 `assertTrue/assertThrows/assertFalse`+`org.flywaydb.core.Flyway`가 import돼 있어, Task 1의 신규 테스트는 **새 import 없이 그대로 작성 가능**하다. 테스트의 `INSERT INTO contents(slug,title,track,content_md)`는 나머지 컬럼이 nullable/DEFAULT라 성공하고, `track` CHECK가 `BACKEND_SPRING`을 허용한다(`V202606181006:35`). 테스트는 Testcontainers가 아니라 **실 DB**(`DB_URL` 기본 `localhost:5432`)에 붙으므로 Task 1 Step 2의 `docker compose up -d postgres`가 정확하다. `set_updated_at()`은 `V202606150900__init_common.sql`에 정의되어 있고 본문이 `NEW.updated_at = now()`로 **무조건** 갱신함을 확인했다(컬럼을 명시 SET해도 BEFORE UPDATE 트리거가 덮어씀) — Task 1의 트리거 테스트(`updated_at`을 2000-01-01로 SET 후 now() 갱신 기대)가 이에 근거해 유효하다. `assertThrows`+동일 `Statement` 재사용은 autocommit(기본값) 하에서 기존 `questionBankRejectsBadEnumAndRange`가 같은 패턴으로 이미 검증한다.
- **Boundary safety:** `user_id` 교차서비스 FK 금지를 테스트로 검증한다. learning-svc task 자동완료 쿼리와 progress upsert 로직은 빌드 C로 남겨 범위를 넘지 않는다.
- **CI safety:** 새 외부 서비스나 Ollama 호출 없음. 기존 pgvector 마이그레이션 때문에 테스트 DB는 계속 pgvector 지원 Postgres여야 한다.
- **Risk:** 구현 시 다른 세션이 `V20260621xxxx` 마이그레이션을 먼저 추가했다면 sequence 충돌만 조정하면 된다. 스키마 자체는 독립적이다.
