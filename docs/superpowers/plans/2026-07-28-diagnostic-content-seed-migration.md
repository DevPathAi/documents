# 진단·콘텐츠 시드 마이그레이션 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 운영 DB에 진단 문항(`question_bank` 500)·학습 콘텐츠(`contents` 150) 시드를 devpath-shared 중앙 Flyway 마이그레이션으로 적재해, `@Profile("dev")` 시더가 운영에서 안 돌아 비어버린 두 테이블을 채우고 실력진단 퍼널을 복구한다.

**Architecture:** devpath-shared에 versioned Flyway 마이그레이션 2개를 추가한다. 시드 데이터는 learning-svc의 기존 MD2 승인 시드 SQL(`question_bank_md2_seed.sql`·`content_md2_seed.sql`)에서 그대로 이식하되, **빈 테이블일 때만 적재하는 멱등 가드(DO 블록)**로 감싼다. 검증은 기존 `FlywayMigrationTest`에 count 단언을 추가한다(TDD). 운영 적용은 gitops `apps/devpath-migration` 잡이 담당(이 플랜 범위 밖, 배포 시).

**Tech Stack:** Flyway, PostgreSQL 17 (+pgvector), JUnit 5, Gradle (Kotlin DSL), Docker Compose(로컬 Postgres).

## Global Constraints

- 마이그레이션 네이밍: `V<YYYYMMDDHHMM>__<name>.sql`. 현재 최신 = `V202607221003__ad_daily_stats.sql`. 신규는 그 이후 타임스탬프: `V202607281001`, `V202607281002`.
- 마이그레이션 위치: `devpath-shared/src/main/resources/db/migration/`.
- 시드 SQL 컬럼은 기존 CREATE 스키마와 **정확히 일치**해야 한다(실측):
  - `question_bank`: `(track, question_type, content, options, answer_key, bloom_level, difficulty, concept_tags)` — `V202606181001__question_bank.sql`
  - `contents`: `(slug, title, track, content_md, estimated_minutes, difficulty, bloom_level, concept_tags, status)` — `V202606181006__learning_path_schema.sql`
- 멱등: 마이그레이션은 **빈 테이블일 때만** 적재(DO 블록 count 가드). 기존 dev 시더(`@Profile("dev")`, "비어있을 때만 전체 적재")와 동일 의미 → 이미 시드된 로컬 dev DB엔 무영향.
- 테스트는 로컬/CI Postgres 필요: devpath-shared에서 `docker compose up -d`(PostgreSQL 17 + pgvector). `FlywayMigrationTest`는 `DB_URL`(기본 `jdbc:postgresql://localhost:5432/devpath`, user `devpath`, pw `localdev`)에 연결.
- TDD: 실패 테스트 우선. 브랜치→develop PR. **main 직접 금지.** Conventional Commits.
- 이 플랜은 **devpath-shared만** 변경. 운영 적용(배포)은 EC2 재시작 후 gitops `apps/devpath-migration` 잡이 devpath-shared 릴리스본을 적용(이 플랜 밖).

---

### Task 1: question_bank 시드 마이그레이션 (500문항)

**Files:**
- Create: `devpath-shared/src/main/resources/db/migration/V202607281001__seed_question_bank.sql`
- Modify(test): `devpath-shared/src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`
- Source(복사 원본): `devpath-learning-svc/src/main/resources/db/seed/question_bank_md2_seed.sql`

**Interfaces:**
- Consumes: 기존 `question_bank` 테이블(V202606181001), `FlywayMigrationTest.dataSource()` 하네스(기존 테스트와 동일 패턴).
- Produces: 마이그레이션 적용 후 `SELECT count(*) FROM question_bank >= 500`. (Task 2와 독립)

- [ ] **Step 1: 로컬 Postgres 기동 (깨끗한 상태)**

Run: `cd devpath-shared && docker compose down -v && docker compose up -d`
Expected: postgres(5432) 컨테이너가 up. `-v`로 기존 볼륨을 지워 빈 DB에서 시작(실패 테스트를 정확히 관찰하기 위함).

- [ ] **Step 2: 실패 테스트 작성**

`FlywayMigrationTest.java`에 아래 메서드를 클래스 끝(마지막 `}` 직전)에 추가:

```java
  @Test
  void questionBankSeeded() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement();
        var rs = st.executeQuery("SELECT count(*) FROM question_bank")) {
      assertTrue(rs.next(), "count 결과 필요");
      assertTrue(rs.getLong(1) >= 500, "question_bank는 500문항 이상 시드되어야 한다");
    }
  }
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.questionBankSeeded"`
Expected: FAIL — `question_bank는 500문항 이상 시드되어야 한다` (현재 마이그레이션엔 시드가 없어 count=0).

- [ ] **Step 4: 시드 마이그레이션 파일 생성**

`V202607281001__seed_question_bank.sql` 생성. 아래 골격의 DO 블록 안에, **원본 시드 파일(`question_bank_md2_seed.sql`)의 `VALUES` 이후 모든 행을 그대로 이식**한다(원본 첫 줄 `INSERT INTO question_bank (...) VALUES`는 아래 INSERT 헤더로 대체, 원본의 `(...)` 값 행들만 붙여넣고 마지막 `;`는 DO 블록 안에서 유지):

```sql
-- 진단 문항 뱅크 시드 (MD2 승인 500문항). @Profile("dev") 시더가 운영 미적용인 갭 복구.
-- 멱등: 뱅크가 비어있을 때만 적재(기존 dev 시더와 동일 의미). 이미 시드된 DB엔 무영향.
DO $$
BEGIN
  IF (SELECT count(*) FROM question_bank) = 0 THEN
    INSERT INTO question_bank (track, question_type, content, options, answer_key, bloom_level, difficulty, concept_tags) VALUES
    ('BACKEND_SPRING','MCQ','BACKEND_SPRING 009: Which option best applies concurrency in a DevPath diagnostic scenario?','["Apply the primary concept deliberately","Ignore the signal and continue","Disable validation around the flow","Move responsibility to an unrelated layer"]','{"correct":0}','REMEMBER',0.1,'["backend-spring-concurrency"]')
    -- ↑ 예시 1행. 원본 question_bank_md2_seed.sql의 전체 VALUES 행(500행)을 콤마로 이어 붙인다. 마지막 행 뒤에 세미콜론.
    ;
  END IF;
END $$;
```

주의:
- 컬럼 순서는 Global Constraints의 `question_bank` 목록과 일치(원본 시드도 동일 순서 — 실측 확인됨).
- 원본 값 안의 작은따옴표·JSON은 원본 그대로 유지(원본은 이미 유효 SQL).

- [ ] **Step 5: 테스트 통과 확인 (빈 DB)**

Run: `cd devpath-shared && docker compose down -v && docker compose up -d && ./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.questionBankSeeded"`
Expected: PASS — count >= 500.

- [ ] **Step 6: 멱등 재적용 확인 (이미 시드된 DB)**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.questionBankSeeded"` (Step 5의 DB를 지우지 않고 재실행)
Expected: PASS — count 여전히 500대(중복 적재 없음). Flyway가 적용된 버전을 건너뛰고, 설령 재실행돼도 DO 가드가 non-empty를 감지해 INSERT 0.

- [ ] **Step 7: 전체 마이그레이션 회귀**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest"`
Expected: 전체 PASS(기존 테이블 계약 테스트 + 신규 시드 테스트).

- [ ] **Step 8: 커밋**

```bash
git add devpath-shared/src/main/resources/db/migration/V202607281001__seed_question_bank.sql \
        devpath-shared/src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(migration): 진단 문항 뱅크 500문항 운영 시드 (dev 전용 시더 갭 복구)"
```

---

### Task 2: contents 시드 마이그레이션 (150콘텐츠)

**Files:**
- Create: `devpath-shared/src/main/resources/db/migration/V202607281002__seed_contents.sql`
- Modify(test): `devpath-shared/src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`
- Source(복사 원본): `devpath-learning-svc/src/main/resources/db/seed/content_md2_seed.sql`

**Interfaces:**
- Consumes: 기존 `contents` 테이블(V202606181006), `FlywayMigrationTest.dataSource()` 하네스.
- Produces: 마이그레이션 적용 후 `SELECT count(*) FROM contents >= 150`. (Task 1과 독립 — 순서 무관)

- [ ] **Step 1: 실패 테스트 작성**

`FlywayMigrationTest.java`에 추가:

```java
  @Test
  void contentsSeeded() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement();
        var rs = st.executeQuery("SELECT count(*) FROM contents")) {
      assertTrue(rs.next(), "count 결과 필요");
      assertTrue(rs.getLong(1) >= 150, "contents는 150개 이상 시드되어야 한다");
    }
  }
```

- [ ] **Step 2: 테스트 실패 확인 (빈 DB)**

Run: `cd devpath-shared && docker compose down -v && docker compose up -d && ./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.contentsSeeded"`
Expected: FAIL — `contents는 150개 이상 시드되어야 한다` (count=0).

- [ ] **Step 3: 시드 마이그레이션 파일 생성**

`V202607281002__seed_contents.sql` 생성. Task 1과 동일 패턴의 DO 가드 안에, **원본 `content_md2_seed.sql`의 `VALUES` 이후 전체 행을 그대로 이식**:

```sql
-- 학습 콘텐츠 시드 (MD2 승인 150개). @Profile("dev") 시더가 운영 미적용인 갭 복구.
-- 멱등: contents가 비어있을 때만 적재.
-- content_md는 여러 줄 텍스트(줄바꿈 포함) — 원본의 작은따옴표 이스케이프를 그대로 유지하면 안전.
DO $$
BEGIN
  IF (SELECT count(*) FROM contents) = 0 THEN
    INSERT INTO contents (slug, title, track, content_md, estimated_minutes, difficulty, bloom_level, concept_tags, status) VALUES
    -- ↓ 원본 content_md2_seed.sql의 전체 VALUES 행(150행)을 콤마로 이어 붙인다. 마지막 행 뒤 세미콜론.
    ;
  END IF;
END $$;
```

주의: 원본 `content_md2_seed.sql`은 `contents` INSERT 외에 `content_embeddings` 등 다른 INSERT나 `SELECT ... FROM contents` 파생 구문이 섞여 있을 수 있다. **`contents` 테이블 INSERT 블록만** 이식하고, 임베딩·파생 구문은 이식하지 않는다(임베딩은 Ollama 배포 후 백필 — 트랙2/후속). 이식 전 원본을 열어 `INSERT INTO contents` 구간을 정확히 식별할 것.

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd devpath-shared && docker compose down -v && docker compose up -d && ./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.contentsSeeded"`
Expected: PASS — count >= 150.

- [ ] **Step 5: 전체 마이그레이션 회귀**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest"`
Expected: 전체 PASS.

- [ ] **Step 6: 커밋**

```bash
git add devpath-shared/src/main/resources/db/migration/V202607281002__seed_contents.sql \
        devpath-shared/src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(migration): 학습 콘텐츠 150개 운영 시드 (dev 전용 시더 갭 복구)"
```

---

### Task 3: 브랜치 마무리 + PR

- [ ] **Step 1: 전체 빌드·테스트**

Run: `cd devpath-shared && ./gradlew build`
Expected: BUILD SUCCESSFUL (전체 테스트 그린).

- [ ] **Step 2: 푸시 + develop PR**

```bash
git push -u origin feat/diagnostic-content-seed
gh pr create --base develop --title "feat: 진단·콘텐츠 시드 운영 적재 (dev 전용 시더 갭 복구)" \
  --body "question_bank(500)·contents(150) 시드를 중앙 Flyway 마이그레이션으로 승격. @Profile(\"dev\") 시더가 운영 미적용이라 비었던 두 테이블을 채워 실력진단 퍼널 복구. 멱등(빈 테이블만 적재)."
```
Expected: PR 생성. CI 그린 확인 후 머지(merge commit).

- [ ] **Step 3: 배포 메모(플랜 밖, 실행 시점 기록)**

운영 반영은 **EC2 재시작 후**: devpath-shared develop→main 릴리스 → gitops `apps/devpath-migration` 잡 재실행 → 운영 DB에 시드 적용 → `psql`로 `question_bank>=500`·`contents>=150` 실측. (본 플랜의 테스트 범위 밖)

---

## Self-Review

**1. Spec coverage:** 스펙 트랙1(진단·콘텐츠 시드를 중앙 마이그레이션으로 승격) 전부 커버. 트랙2(Ollama 배포)는 별도 플랜 예정. ✅

**2. Placeholder scan:** "500행/150행 이식"은 실재하는 원본 파일(`question_bank_md2_seed.sql`·`content_md2_seed.sql`)에서 **복사**하라는 구체 지시이며, 예시 1행과 정확한 컬럼 목록·가드 골격을 제공했다 — placeholder 아님. 그 외 TBD/TODO 없음. ✅

**3. Type/스키마 일관성:** 두 마이그레이션의 INSERT 컬럼이 Global Constraints의 실측 스키마(question_bank 8컬럼·contents 9컬럼)와 일치. 테스트 메서드명(`questionBankSeeded`·`contentsSeeded`)·단언 임계(500·150)가 Goal·Interfaces와 일치. ✅

**4. 멱등/리스크:** DO 가드로 재적용·기존 로컬 DB 중복 방지. content 시드 이식 시 `contents` INSERT 구간만 취하도록 명시(임베딩 파생 구문 제외). ✅
