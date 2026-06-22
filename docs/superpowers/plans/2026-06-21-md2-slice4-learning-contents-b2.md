# MD2 슬라이스 #4 빌드 B2 — devpath-learning-svc 콘텐츠/임베딩 생성 + 150 seed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **✅ 구현 완료(2026-06-21):** 본 플랜은 `devpath-learning-svc`에서 실행 완료됐다 — PR #14(`feat/slice4-content-seed` → develop, merge `318fa46`), CI 녹색. 산출물이 본 플랜 File Structure와 정합: B1의 `tools/content-gen` 확장(content·embedding schema/prompt)·`ContentValidator`+`ContentValidatorTest`·`src/main/resources/db/seed/content_md2_seed.sql`·승인 `contents.jsonl` **150줄(5 track×30, 전부 PUBLISHED)**·`content_embeddings.jsonl`(768차원). origin/develop 실측 확인.

**Goal:** `devpath-learning-svc`에 콘텐츠 생성/검증/임베딩 seed 파이프라인을 추가하고, 5개 track x 30편 = 150개 `PUBLISHED` 콘텐츠와 `content_embeddings` seed를 적재 가능하게 만든다.

**Architecture:** B1의 `tools/content-gen` 구조를 확장한다. 콘텐츠 본문은 approved JSONL, DB 적재는 seed SQL, 임베딩은 실제 768차원 산출물 또는 JSONL+loader를 SSoT로 둔다. CI는 실제 Ollama/qwen/nomic 호출 없이 fixture embedding으로 chunking, validation, SQL/loader를 검증한다.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Gradle · Jackson(JsonMapper) · PostgreSQL 17 + pgvector · JUnit 5.

## Global Constraints

- 범위는 **B2 콘텐츠/임베딩 데이터**만이다. runtime API는 C, gateway는 D, frontend는 E다.
- CI에서 Ollama/qwen/nomic 실호출 금지.
- `contents`와 `content_embeddings`는 shared `V202606181006` 스키마를 사용한다. schema migration은 추가하지 않는다.
- 승인 콘텐츠만 seed에 들어간다. `DRAFT`는 approved JSONL에 넣지 않는다.
- raw HTML 금지, Markdown fenced code block만 허용한다.
- embedding은 `nomic-embed-text` 768차원만 허용하고 길이가 다르면 fail-fast한다.
- **검수 반영:** `content_embeddings`에는 `(content_id, chunk_hash)` **DB unique 제약이 없다**(`V202606181006` 확인: `chunk_hash VARCHAR(64)` nullable, unique 없음). 따라서 같은 content+chunk 중복 방지는 **validator/loader 레벨에서만** 강제한다(Task 2 Step 2). seed는 fresh/dev 기준으로 만들고 `ON CONFLICT`에 의존하지 않는다.
- `content_id`는 slug 조회 CTE로 채워 id 하드코딩을 피한다. `contents.concept_tags`는 **JSONB**, `content_embeddings.embedding`은 `VECTOR(768) NOT NULL`, `status`는 `ACTIVE`(CHECK `ACTIVE`/`INACTIVE`)로 넣는다.

---

## File Structure

- Modify: `tools/content-gen/README.md`
- Create: `tools/content-gen/schemas/content.schema.json`
- Create: `tools/content-gen/schemas/embedding.schema.json`
- Create: `tools/content-gen/prompts/content-system.md`
- Create: `tools/content-gen/generated/approved/contents.jsonl`
- Create: `tools/content-gen/generated/approved/content_embeddings.jsonl` 또는 generated seed SQL
- Create: `tools/content-gen/generated/seeds/content_seed.sql`
- Create: `src/main/resources/db/seed/content_md2_seed.sql`
- Create: `src/test/resources/seed/content_md2_seed.sql`
- Create: `src/contentGen/java/ai/devpath/learning/contentgen/content/**`
- Create: `src/test/java/ai/devpath/learning/contentgen/content/**`
- Create or Modify: `src/test/java/ai/devpath/learning/seed/ContentSeedSqlTest.java`

---

## Task 0: 선행 조건 확인

- [ ] **Step 1: B1 도구 존재 확인**

```powershell
Test-Path tools/content-gen
rg -n "validateQuestions|makeQuestionSeedSql|contentGen" build.gradle.kts tools src
```

Expected: B1의 content-gen source set과 검증 task가 있다.

- [ ] **Step 2: 작업 브랜치**

```powershell
git switch develop
git pull
git switch -c feat/slice4-content-seed
```

---

## Task 1: 콘텐츠 validator와 실패 테스트

**Files:**
- Create: `ContentValidatorTest.java`
- Create: `ContentValidator.java`, `ApprovedContent.java`, `ContentJsonlReader.java`
- Create: `tools/content-gen/schemas/content.schema.json`

- [ ] **Step 1: 실패 테스트**

테스트 케이스:

- track별 30편이 아니면 실패.
- slug 중복 실패.
- slug가 lowercase kebab-case가 아니면 실패.
- `status != PUBLISHED` 실패.
- `markdown`에 raw HTML이 있으면 실패.
- fenced code block이 닫히지 않으면 실패.
- difficulty가 0.0~1.0 범위 밖이면 실패.
- 입문 8, 중급 14, 심화 8 quota가 아니면 실패.
- track당 코드블록 포함 콘텐츠가 10개 미만이면 실패.

- [ ] **Step 2: validator 구현**

> **검수 반영(Jackson 3):** JSONL 파싱은 `tools.jackson.databind.json.JsonMapper`(Boot 4 = Jackson 3, 기존 learning-svc 서비스 전부 사용)를 쓴다 — `com.fasterxml.jackson...ObjectMapper`가 아니다. `ContentJsonlReader`는 줄 단위로 `jsonMapper.readValue(line, ApprovedContent.class)`로 읽는다.

`conceptTags`는 B1 question taxonomy와 최대한 같은 kebab-case를 사용한다. validator는 한글 tag/공백 tag를 실패로 처리한다.

- [ ] **Step 3: focused tests**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.contentgen.content.*"
```

---

## Task 2: chunking과 embedding validator

**Files:**
- Create: `ContentChunker.java`
- Create: `EmbeddingRecord.java`
- Create: `EmbeddingValidator.java`
- Create tests: `ContentChunkerTest.java`, `EmbeddingValidatorTest.java`

- [ ] **Step 1: chunking 규칙 테스트**

규칙:

- H2 섹션 우선 분할.
- 너무 긴 섹션은 800~1200자 단위로 분할.
- overlap은 120자 내외 허용.
- `chunk_index`는 content별 0부터 증가.
- `chunk_hash`는 normalized chunk text SHA-256 hex.

- [ ] **Step 2: embedding 검증 테스트**

테스트:

- embedding length 768 PASS.
- 767/769 FAIL.
- 같은 content + chunk hash 중복 FAIL.
- status는 `ACTIVE`만 허용.

---

## Task 3: local embedding client boundary

**Files:**
- Create: `EmbeddingClient.java`
- Create: `OllamaEmbeddingClient.java`
- Create tests with fake client

- [ ] **Step 1: client interface**

```java
List<Double> embed(String text);
```

`OllamaEmbeddingClient`는 로컬 수동 실행에서만 `nomic-embed-text`를 호출한다. CI test는 fake client로 고정 768차원 vector만 사용한다.

- [ ] **Step 2: README 수동 절차**

```powershell
.\gradlew.bat generateContentsLocal -Pollama.model=qwen2.5:7b
.\gradlew.bat validateContents
.\gradlew.bat embedContentsLocal -Pollama.embedModel=nomic-embed-text
.\gradlew.bat makeContentSeedSql
```

---

## Task 4: content seed SQL 생성

**Files:**
- Create: `ContentSeedSqlWriter.java`
- Create: `ContentEmbeddingSeedWriter.java`
- Create tests for deterministic output

> **검수 반영(결정성 정렬):** B1과 같이 byte-for-byte 재현을 위해 정렬 순서를 고정한다 — contents는 `(track enum 순서, slug asc)`, content_embeddings는 `(content slug asc, chunk_index asc)`. 같은 approved JSONL → 같은 seed SQL을 단언한다.

- [ ] **Step 1: contents INSERT**

`contents` 컬럼:

```sql
slug, title, track, content_md, estimated_minutes, difficulty, bloom_level, concept_tags, status
```

`status`는 항상 `PUBLISHED`.

- [ ] **Step 2: content_embeddings INSERT**

`content_embeddings` 컬럼:

```sql
content_id, chunk_index, chunk_text, embedding, chunk_hash, status
```

`content_id`는 slug로 조회하는 CTE를 사용해 id에 의존하지 않게 한다.

```sql
INSERT INTO content_embeddings(content_id, chunk_index, chunk_text, embedding, chunk_hash, status)
SELECT c.id, 0, '...', '[...]'::vector, 'sha256...', 'ACTIVE'
FROM contents c WHERE c.slug = 'backend-spring-...';
```

- [ ] **Step 3: 파일 크기 기준**

`content_seed.sql`이 지나치게 커지면 아래로 전환한다.

- `src/main/resources/db/seed/content_md2_seed.sql`: contents만.
- `tools/content-gen/generated/approved/content_embeddings.jsonl`: embeddings SSoT.
- `EmbeddingSeedLoader`: dev/demo load command.

전환 기준은 PR에서 파일 크기와 CI 시간을 보고 결정하되, CI fixture는 항상 Ollama 없이 통과해야 한다.

---

## Task 5: 승인 콘텐츠 150편과 seed 검증

**Files:**
- Create: `tools/content-gen/generated/approved/contents.jsonl`
- Create: `tools/content-gen/generated/approved/content_embeddings.jsonl`
- Create: `src/main/resources/db/seed/content_md2_seed.sql`
- Create: `src/test/resources/seed/content_md2_seed.sql`
- Create: `ContentSeedSqlTest.java`

- [ ] **Step 1: approved contents 추가**

track별 30편:

- `BACKEND_SPRING`: 30
- `FRONTEND_REACT`: 30
- `MOBILE_FLUTTER`: 30
- `DEVOPS`: 30
- `FULLSTACK`: 30

- [ ] **Step 2: seed DB 검증 테스트**

`@Sql("/seed/content_md2_seed.sql")` 후 검증:

- `contents` 총 150.
- track별 30.
- all `PUBLISHED`.
- content별 ACTIVE embedding 1개 이상.
- embedding `format_type`은 `vector(768)` 또는 `<=>` smoke query 통과.
- slug 중복 없음.

구현 메모(검수 반영):
- **카운트 수단**: `ContentRepository`는 bare `JpaRepository`라 `findByTrack`이 **없다**(`QuestionBankRepository`에만 있음, 확인). 집계 단언은 autowired `JdbcTemplate`로 한다 — track별: `SELECT track, count(*) FROM contents GROUP BY track`(각 30); PUBLISHED 외: `SELECT count(*) FROM contents WHERE status <> 'PUBLISHED'`(=0); ACTIVE 임베딩 누락: `SELECT count(*) FROM contents c WHERE NOT EXISTS (SELECT 1 FROM content_embeddings e WHERE e.content_id=c.id AND e.status='ACTIVE')`(=0). 차원은 `FlywayMigrationTest`의 `format_type(...) = 'vector(768)'` 쿼리를 재사용.
- **slug 중복**: `contents.slug`는 shared 스키마에서 `NOT NULL UNIQUE`라 중복 seed는 `@Sql` 적재 단계에서 실패한다(스키마=1차 방어, validator=2차). `count(*) = count(DISTINCT slug)` 보강 단언도 가능.
- **임베딩 pivot 대응**: Task 4 Step 3에서 임베딩을 JSONL+loader로 분리하면 `content_md2_seed.sql`엔 contents만 남는다 → 이 테스트는 `@Sql`(contents) + loader 실행(embeddings) 후 검증으로 맞춘다. 임베딩을 seed SQL에 포함하는 경로면 `@Sql` 하나로 충분하다.

```powershell
.\gradlew.bat test --tests ai.devpath.learning.seed.ContentSeedSqlTest
```

---

## Task 6: path matcher 실제 seed smoke

**Files:**
- Modify or Create: `src/test/java/ai/devpath/learning/path/ContentEmbeddingMatcherSeedTest.java`

- [ ] **Step 1: 실제 seed 기반 matcher 테스트**

fixture 768 query vector로 `ContentEmbeddingMatcher.match(track, vector, limit)`를 호출해 해당 track의 PUBLISHED 콘텐츠만 반환하는지 검증한다.

- [ ] **Step 2: matching miss는 기존 C 테스트 보존**

기존 `LearningPathEngineTest.matchingMissKeepsTaskContentIdNull`이 계속 통과해야 한다.

---

## Task 7: 검증과 PR

- [ ] **Step 1: focused tests**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.contentgen.content.*"
.\gradlew.bat test --tests "ai.devpath.learning.seed.*Content*"
.\gradlew.bat test --tests "ai.devpath.learning.path.*Matcher*"
```

- [ ] **Step 2: full build**

```powershell
.\gradlew.bat test
.\gradlew.bat clean build
```

- [ ] **Step 3: no real Ollama scan**

```powershell
rg -n "localhost:11434|nomic-embed-text|qwen2.5" src tools build.gradle.kts
```

Expected: real model names only in README/local clients/tasks, not CI tests.

- [ ] **Step 4: develop PR**

```powershell
git push -u origin feat/slice4-content-seed
gh pr create --base develop --title "feat: MD2 slice4 approved content and embedding seed" --body "Adds validated 150 content seed and embedding seed pipeline."
```

## Acceptance Checklist

- [ ] approved contents JSONL 150편이 있다.
- [ ] track별 30편, all PUBLISHED다.
- [ ] raw HTML과 깨진 code fence가 없다.
- [ ] content별 ACTIVE embedding이 1개 이상 있다.
- [ ] embedding은 768차원만 허용된다.
- [ ] seed SQL 또는 JSONL+loader가 결정적으로 생성된다.
- [ ] CI/test는 Ollama/qwen/nomic을 호출하지 않는다.
- [ ] `.\gradlew.bat clean build`가 통과한다.

## Self-Review

- **Spec coverage:** 설계서 §4.5~§4.8, §9 Build B2, §11.2 embedding/seed 테스트를 커버한다.
- **Current source alignment:** `ContentEmbeddingMatcher.match(String, List<Double>, int)`(확인)와 `contents`/`content_embeddings` 스키마가 이미 있으므로 B2는 data와 batch 검증에 집중한다. `ContentRepository`는 bare라 seed 테스트 집계는 `JdbcTemplate`, JSONL 파싱은 Jackson 3 `JsonMapper`로 한다.
- **B1↔B2 결합:** B2 Task 0이 B1의 `tools/content-gen`+contentGen 배선 존재를 확인한다. B2는 그 스캐폴드를 확장(content schema/prompt·embedding writer)하므로 `tools/content-gen`·`build.gradle.kts`·README를 공유한다 → 동시 수정 충돌. **B1 머지 후 진행/rebase가 안전**하다(설계서의 "B1/B2 병렬"은 데이터 생성 작업 기준).
- **Risk:** 실제 embedding seed 파일이 커질 수 있다. 이 경우 설계서가 허용한 JSONL+loader 방식으로 전환하고(Task 4 Step 3), seed 테스트도 loader 경로로 맞춘다(Task 5 Step 2).
