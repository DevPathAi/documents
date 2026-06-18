# 슬라이스 #3 빌드 A — devpath-shared 학습경로 스키마 + pgvector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** devpath-shared에 학습경로·콘텐츠·임베딩 스키마(pgvector VECTOR(768)+HNSW)를 추가하고, 메인 DB·CI를 pgvector 이미지로 전환해 다운스트림(ai-svc 제외)이 소비하게 한다.

**Architecture:** 슬라이스 #2 빌드 A 패턴(VARCHAR+CHECK enum·BIGSERIAL·TIMESTAMPTZ·set_updated_at·JSONB)에 pgvector를 더한다. 메인 devpath DB(5432) 이미지를 `pgvector/pgvector:pg17`로 전환하고 단일 Flyway 마이그레이션에 `CREATE EXTENSION vector` + 5테이블 + HNSW를 담는다. learning 도메인 내부 FK만(user_id는 FK 없음 — 슬라이스 #2 서비스 경계 교훈).

**Tech Stack:** Java 21 · Gradle(Kotlin DSL, java-library) · Flyway 11.8.2 · PostgreSQL 17 + **pgvector** · JUnit 5 · maven-publish.

## Global Constraints

- 레포 절대조건: 추측 금지 · **테스트 우선** · 문제 시 코드 분석.
- 브랜치: develop 분기 → develop PR, CI 녹색 후 merge commit. main 직접 금지(릴리스 PR만).
- 마이그레이션 파일명 `V<YYYYMMDD><4자리>__<설명>.sql`. **기존 V202606181005까지 적용된 DB에 추가** → 다음 번호 `V202606181006`.
- enum=VARCHAR+CHECK, JSON=JSONB, PK=BIGSERIAL, 타임스탬프=TIMESTAMPTZ+`set_updated_at()` 트리거(기존 함수), FLOAT=DOUBLE PRECISION, 벡터=**VECTOR(768)**.
- **교차서비스 FK 금지**(슬라이스 #2 교훈): `learning_paths.user_id`는 FK 없음. learning 도메인 내부 FK만(learning_paths↔milestones↔tasks↔contents↔embeddings).
- track enum: `BACKEND_SPRING, FRONTEND_REACT, MOBILE_FLUTTER, DEVOPS, FULLSTACK`. content_embeddings.status=`ACTIVE/INACTIVE`(ERD 정합). task_type=`READ/PRACTICE/QUIZ`. path status=`ACTIVE/ARCHIVED`.
- **R-8 동시성**: `learning_paths(user_id) WHERE status='ACTIVE'` partial UNIQUE로 사용자당 ACTIVE 1개 DB 보장.
- **R-3 pgvector 전환**: 메인 DB·CI postgres 이미지 `pgvector/pgvector:pg17`(postgres 상위호환). 로컬은 fresh DB 권장(`docker compose down -v` 후 up).
- 임베딩 VECTOR(768)는 nomic-embed-text 차원(설계 §2). HNSW cosine(`vector_cosine_ops`).

---

## File Structure

- Modify: `docker-compose.yml` — 5432 postgres 이미지 → pgvector/pgvector:pg17
- Modify: `.github/workflows/ci.yml` — postgres 서비스 이미지 → pgvector/pgvector:pg17
- Create: `src/main/resources/db/migration/V202606181006__learning_path_schema.sql` — extension + 5테이블 + HNSW
- Modify: `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java` — extension·테이블·VECTOR·HNSW·`<=>` smoke 검증

---

## Task 1: pgvector 인프라 전환 (docker-compose + CI)

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: 메인 devpath DB(5432)·CI postgres가 pgvector 확장을 지원 → Task 2 마이그레이션의 `CREATE EXTENSION vector`가 성공.

- [ ] **Step 1: docker-compose 메인 postgres 이미지 교체**

`docker-compose.yml`의 `postgres:` 서비스(현재 `image: postgres:17-alpine`)를 교체:

```yaml
  postgres:
    image: pgvector/pgvector:pg17
    environment:
      POSTGRES_USER: devpath
      POSTGRES_PASSWORD: localdev
      POSTGRES_DB: devpath
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "devpath"]
      interval: 10s
      retries: 5
```
(나머지 서비스·`postgres-vector`(5433)는 그대로 둔다 — 5433은 별도 devpath_vector DB로 무해.)

- [ ] **Step 2: CI postgres 서비스 이미지 교체**

`.github/workflows/ci.yml`의 `services.postgres.image`를 `postgres:17-alpine` → `pgvector/pgvector:pg17`로 변경(나머지 env/ports/options 유지).

- [ ] **Step 3: 로컬 fresh DB 적용**

```bash
docker compose down -v
docker compose up -d postgres redis kafka
```
> ⚠️ `down -v`는 로컬 DB 볼륨을 삭제한다(스키마 재적용). 보존할 로컬 데이터가 있으면 백업 후 진행.

- [ ] **Step 4: 커밋**

```bash
git add docker-compose.yml .github/workflows/ci.yml
git commit -m "chore(infra): 메인 postgres를 pgvector/pgvector:pg17로 전환(슬라이스 #3 임베딩)"
```

---

## Task 2: 학습경로·콘텐츠·임베딩 마이그레이션

**Files:**
- Create: `src/main/resources/db/migration/V202606181006__learning_path_schema.sql`
- Modify: `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`

**Interfaces:**
- Consumes: 기존 `users`(BIGINT id) — 단 FK 없이 user_id 논리참조. `set_updated_at()` 함수.
- Produces: 테이블 `learning_paths`·`path_milestones`·`path_weekly_tasks`·`contents`·`content_embeddings`(VECTOR(768)). 슬라이스 #3 빌드 C가 JPA/native로 소비.

- [ ] **Step 1: 테이블/extension 존재 검증 실패 테스트 추가**

`FlywayMigrationTest.java`의 마지막 테스트(`assessmentsHasNoUserFk`) 뒤, 클래스 닫는 `}` 앞에 추가(기존 import·`assertThrows`·`dataSource()` 사용):

```java
  @Test
  void vectorExtensionAndPathTablesExist() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      try (var rs = st.executeQuery("SELECT 1 FROM pg_extension WHERE extname = 'vector'")) {
        assertTrue(rs.next(), "vector 확장 필요");
      }
      for (String t : new String[] {"learning_paths", "path_milestones",
          "path_weekly_tasks", "contents", "content_embeddings"}) {
        try (var rs = c.getMetaData().getTables(null, "public", t, new String[] {"TABLE"})) {
          assertTrue(rs.next(), t + " 테이블 필요");
        }
      }
    }
  }

  @Test
  void contentEmbeddingsCosineSmoke() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      // 콘텐츠 + 768차원 임베딩 2건 삽입 후 코사인 거리(<=>) 쿼리가 동작해야 한다.
      st.execute("INSERT INTO contents(slug,title,track,content_md) "
          + "VALUES ('smoke-" + System.nanoTime() + "','t','BACKEND_SPRING','m') RETURNING id");
      try (var rs = st.executeQuery("SELECT id FROM contents ORDER BY id DESC LIMIT 1")) {
        rs.next();
        long cid = rs.getLong(1);
        st.execute("INSERT INTO content_embeddings(content_id,chunk_index,chunk_text,embedding) "
            + "VALUES (" + cid + ",0,'c', array_fill(0.1::float8, ARRAY[768])::vector)");
        try (var rs2 = st.executeQuery(
            "SELECT embedding <=> array_fill(0.2::float8, ARRAY[768])::vector AS dist "
            + "FROM content_embeddings WHERE content_id=" + cid)) {
          assertTrue(rs2.next(), "코사인 거리 쿼리 결과 필요");
        }
        st.execute("DELETE FROM content_embeddings WHERE content_id=" + cid);
        st.execute("DELETE FROM contents WHERE id=" + cid);
      }
    }
  }

  @Test
  void learningPathsActiveUserUniqueEnforced() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      long uid = System.nanoTime();
      st.execute("INSERT INTO learning_paths(user_id,track,status) VALUES (" + uid + ",'BACKEND_SPRING','ACTIVE')");
      // 같은 user의 두 번째 ACTIVE는 partial unique 위반
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO learning_paths(user_id,track,status) VALUES (" + uid + ",'BACKEND_SPRING','ACTIVE')"));
      st.execute("DELETE FROM learning_paths WHERE user_id=" + uid);
    }
  }
```

- [ ] **Step 2: 테스트 실패 확인 (pgvector DB 필요)**

```bash
docker compose up -d postgres
./gradlew test --tests ai.devpath.shared.db.FlywayMigrationTest
```
Expected: 신규 3테스트 FAIL(테이블/extension 없음).

- [ ] **Step 3: 마이그레이션 작성**

`V202606181006__learning_path_schema.sql`:

```sql
-- 슬라이스 #3: 학습경로·콘텐츠·임베딩 스키마 (02_ERD §학습경로·콘텐츠). pgvector 768차원.
-- user_id는 platform users로의 논리참조(교차서비스 FK 없음, 슬라이스 #2 경계 원칙).
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE learning_paths (
  id                       BIGSERIAL PRIMARY KEY,
  user_id                  BIGINT NOT NULL,
  generated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  track                    VARCHAR(20) NOT NULL,
  total_weeks              INT NOT NULL DEFAULT 12,
  gen_prompt_version       VARCHAR(20),
  source_embedding_version VARCHAR(40),
  status                   VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
  ai_rationale             TEXT,
  CONSTRAINT chk_lp_track CHECK (track IN ('BACKEND_SPRING','FRONTEND_REACT','MOBILE_FLUTTER','DEVOPS','FULLSTACK')),
  CONSTRAINT chk_lp_status CHECK (status IN ('ACTIVE','ARCHIVED'))
);
-- R-8: 사용자당 ACTIVE 경로 1개 보장(동시 generate 레이스 차단)
CREATE UNIQUE INDEX uq_learning_paths_active_user ON learning_paths(user_id) WHERE status = 'ACTIVE';
CREATE INDEX idx_learning_paths_user ON learning_paths(user_id);

CREATE TABLE contents (
  id                BIGSERIAL PRIMARY KEY,
  slug              VARCHAR(120) NOT NULL UNIQUE,
  title             VARCHAR(300) NOT NULL,
  track             VARCHAR(20) NOT NULL,
  content_md        TEXT NOT NULL,
  estimated_minutes INT,
  difficulty        DOUBLE PRECISION,
  bloom_level       VARCHAR(20),
  concept_tags      JSONB,
  status            VARCHAR(20) NOT NULL DEFAULT 'PUBLISHED',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_contents_track CHECK (track IN ('BACKEND_SPRING','FRONTEND_REACT','MOBILE_FLUTTER','DEVOPS','FULLSTACK')),
  CONSTRAINT chk_contents_status CHECK (status IN ('DRAFT','PUBLISHED'))
);
CREATE INDEX idx_contents_track_status_diff ON contents(track, status, difficulty);
CREATE TRIGGER contents_set_updated_at BEFORE UPDATE ON contents
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE path_milestones (
  id               BIGSERIAL PRIMARY KEY,
  path_id          BIGINT NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
  week_num         INT NOT NULL,
  title            VARCHAR(200) NOT NULL,
  goal_description TEXT,
  target_skills    JSONB,
  estimated_hours  INT,
  why_this_order   TEXT,
  expected_outcome TEXT,
  CONSTRAINT uq_path_milestones_week UNIQUE (path_id, week_num),
  CONSTRAINT chk_pm_week CHECK (week_num > 0)
);

CREATE TABLE path_weekly_tasks (
  id           BIGSERIAL PRIMARY KEY,
  milestone_id BIGINT NOT NULL REFERENCES path_milestones(id) ON DELETE CASCADE,
  order_num    INT NOT NULL,
  content_id   BIGINT REFERENCES contents(id),
  task_type    VARCHAR(20) NOT NULL,
  title        VARCHAR(300) NOT NULL,
  required     BOOLEAN NOT NULL DEFAULT TRUE,
  completed_at TIMESTAMPTZ,
  CONSTRAINT uq_path_weekly_tasks_order UNIQUE (milestone_id, order_num),
  CONSTRAINT chk_pwt_order CHECK (order_num > 0),
  CONSTRAINT chk_pwt_task_type CHECK (task_type IN ('READ','PRACTICE','QUIZ'))
);
CREATE INDEX idx_path_weekly_tasks_milestone ON path_weekly_tasks(milestone_id);

CREATE TABLE content_embeddings (
  id          BIGSERIAL PRIMARY KEY,
  content_id  BIGINT NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  chunk_text  TEXT NOT NULL,
  embedding   VECTOR(768) NOT NULL,
  chunk_hash  VARCHAR(64),
  status      VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
  CONSTRAINT chk_ce_status CHECK (status IN ('ACTIVE','INACTIVE'))
);
-- HNSW(cosine) 부분 인덱스: ACTIVE 임베딩만
CREATE INDEX idx_content_embeddings_hnsw ON content_embeddings
  USING hnsw (embedding vector_cosine_ops) WHERE status = 'ACTIVE';
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
./gradlew test --tests ai.devpath.shared.db.FlywayMigrationTest
```
Expected: 신규 3테스트 + 기존 전부 PASS.

- [ ] **Step 5: 커밋**

```bash
git add src/main/resources/db/migration/V202606181006__learning_path_schema.sql \
        src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(db): 학습경로·콘텐츠·임베딩 스키마(pgvector VECTOR(768)+HNSW)"
```

---

## Task 3: 전체 빌드 + develop PR

- [ ] **Step 1: clean build (pgvector DB)**

```bash
docker compose up -d postgres
./gradlew clean build
```
Expected: BUILD SUCCESSFUL, 전 FlywayMigrationTest PASS.

- [ ] **Step 2: develop PR → CI 녹색 → merge**

작업 브랜치(`feat/slice3-learning-path-schema`, develop 분기) push → `gh pr create --base develop` → **CI(pgvector 이미지로 마이그레이션 테스트 통과)** 확인 후 merge commit.
> ⚠️ 이 PR이 머지되면 다운스트림(learning/platform) CI도 pgvector 이미지여야 한다 — 그 변경은 각 빌드(C/D)에서 해당 레포 ci.yml에 적용한다. shared develop 머지 자체는 다운스트림 빌드 전이므로 영향 없음.

---

## Task 4: develop→main 릴리스(publish) — 다운스트림 선행 필수

> 빌드 B(ai-svc)·C(learning-svc)가 새 마이그레이션을 test 프로파일로 소비하려면 shared가 **main에서 publish**되어야 한다(슬라이스 #2 D-6 패턴).

- [ ] **Step 1: develop→main 릴리스 PR**

```bash
gh pr create --base main --head develop --title "release: 슬라이스 #3 학습경로 스키마 + pgvector publish" --body "<요약>"
```

- [ ] **Step 2: 머지 후 publish 확인**

main 머지 → `publish.yml`이 GitHub Packages에 새 jar publish. Actions 녹색 확인.

---

## Self-Review (작성자 점검 결과)

- **Spec coverage**: 설계서 §3 데이터모델(5테이블·VECTOR768·HNSW), §9 빌드A, R-3(pgvector 메인/CI 전환), R-8(partial unique), content_embeddings status ACTIVE/INACTIVE, task_type READ/PRACTICE/QUIZ, expected_outcome 필드 — 전부 Task로 커버. user_id FK 없음(슬라이스 #2 교훈) 반영.
- **Placeholder scan**: SQL·Java·명령 전량 기재. Task 3/4 `<요약>`은 PR 본문 자유서술.
- **Type consistency**: 마이그레이션 번호 V202606181006(기존 1005 다음), FK 의존 순서(learning_paths·contents 먼저 → milestones·tasks·embeddings), task_type/status/track enum 값이 CHECK·spec 일치. content_id FK는 contents 생성 후 정의(테이블 순서로 해결).
- **주의**: pgvector 테스트는 pgvector 이미지 DB 필요(로컬 fresh DB·CI 이미지 교체). HNSW partial index는 pgvector 0.5+ 지원. `array_fill(...)::vector` 리터럴로 768차원 smoke. ai-svc는 DB 제거(빌드 B)라 pgvector CI 교체 대상 아님.
