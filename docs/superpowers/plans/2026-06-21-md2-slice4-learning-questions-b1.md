# MD2 슬라이스 #4 빌드 B1 — devpath-learning-svc 문항 생성/검증 + 500 seed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `devpath-learning-svc`에 오프라인 문항 생성/검증 파이프라인을 추가하고, 5개 track x 100개 = 500개 승인 진단 문항을 `question_bank` seed로 적재 가능하게 만든다.

**Architecture:** 생성은 런타임 기능이 아니다. `tools/content-gen`과 Gradle task는 로컬 Ollama 초안 생성, 자동 검증, seed SQL 생성을 담당한다. CI는 Ollama를 호출하지 않고 fixture와 승인 JSON/SQL만 검증한다. 기존 `QuestionBankSeeder`의 BACKEND_SPRING 17개 하드코딩은 MD2 seed SQL 로더로 대체한다.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Gradle · Jackson(JsonMapper) · JUnit 5 · PostgreSQL 17 + pgvector.

## Global Constraints

- 레포 절대조건: 추측 금지 · 테스트 우선 · 문제 시 코드 분석. (`devpath-learning-svc/CLAUDE.md`)
- 신규 작업은 `develop`에서 새 브랜치로 분기한다. 현재 working tree에 타 세션 변경이 있으면 건드리지 않는다.
- 범위는 **B1 문항 데이터**만이다. 콘텐츠/임베딩은 B2, 콘텐츠 API는 C다.
- CI에서 Ollama 실호출 금지. 생성 client는 fixture/mock으로 테스트한다.
- MD2 seed에는 `MCQ` 70%, `CODE_READING` 30%, `SHORT_ANSWER` 0%만 허용한다.
- Bloom `CREATE`는 MD2 seed에서 금지한다.
- **설계서 §4.4 분포(검수 결정):** track당 난이도 밴드(0.1–0.2:10·0.3–0.4:25·0.5–0.6:30·0.7–0.8:25·0.9:10)와 Bloom 분포(REMEMBER:10·UNDERSTAND:25·APPLY:30·ANALYZE:25·EVALUATE:10·CREATE:0)는 **생성/수검수 목표치**다. validator는 (1) 타입 비율 `MCQ70/CODE_READING30`, (2) `SHORT_ANSWER`·`CREATE` 금지, (3) `difficulty 0.0–1.0`, (4) track당 100개를 **강제**한다. 난이도 밴드/Bloom 세부 분포는 **비차단 경고 리포트**로 출력해 편향만 드러낸다(정확 강제는 오프라인 생성 반복 비용이 큼). 강제 승격 여부는 PR에서 결정한다. 이 결정으로 §4.4가 "암묵 누락"이 아니라 명시적으로 다뤄진다.
- 승인 JSONL + seed SQL이 SSoT다. raw Ollama output은 검수 참고물이며 운영 seed로 직접 쓰지 않는다. `question_bank`의 `options`/`answer_key`/`concept_tags`는 **JSONB**이므로 seed SQL은 유효한 JSON 리터럴을 넣는다(예: `'["a","b","c","d"]'`, `'{"correct":2}'`).

---

## File Structure

- Modify: `build.gradle.kts` — `contentGen` source set 또는 JavaExec task 추가.
- Create: `tools/content-gen/README.md`
- Create: `tools/content-gen/schemas/question.schema.json`
- Create: `tools/content-gen/prompts/question-system.md`
- Create: `tools/content-gen/prompts/tracks/{backend-spring,frontend-react,mobile-flutter,devops,fullstack}.md`
- Create: `tools/content-gen/generated/approved/questions.jsonl`
- Create: `tools/content-gen/generated/seeds/question_bank_seed.sql`
- Create: `src/main/resources/db/seed/question_bank_md2_seed.sql`
- (선택) `src/test/resources/seed/question_bank_md2_seed.sql` — 단 `SeedSqlTest`가 main 리소스 `/db/seed/question_bank_md2_seed.sql`를 직접 `@Sql` 로드하면 중복 사본이 불필요(Task 5 Step 3)
- Modify: `src/main/java/ai/devpath/learning/seed/QuestionBankSeeder.java`
- Create: `src/contentGen/java/ai/devpath/learning/contentgen/question/**`
- Create: `src/test/java/ai/devpath/learning/contentgen/question/**`
- Modify: `src/test/java/ai/devpath/learning/seed/SeedSqlTest.java`

---

## Task 0: 브랜치와 현재 상태 확인

- [ ] **Step 1: 브랜치 준비**

```powershell
cd devpath-learning-svc
git switch develop
git pull
git switch -c feat/slice4-question-bank-seed
```

- [ ] **Step 2: 기존 dirty 상태 확인**

```powershell
git status --short --branch
```

Expected: unrelated 변경이 있으면 건드리지 않고, 본 빌드 파일만 수정한다.

---

## Task 1: content-gen 문항 도구 골격과 검증 실패 테스트

**Files:**
- Modify: `build.gradle.kts`
- Create: `src/contentGen/java/ai/devpath/learning/contentgen/question/*`
- Create: `src/test/java/ai/devpath/learning/contentgen/question/QuestionValidatorTest.java`

- [ ] **Step 1: Gradle source set 결정**

기존 repo가 Java/Gradle 중심이므로 Node 패키지를 새로 만들지 않는다. `build.gradle.kts`에 `contentGen` source set과 JavaExec task를 둔다.

```kotlin
sourceSets {
  create("contentGen") {
    java.srcDir("src/contentGen/java")
    resources.srcDir("tools/content-gen")
    compileClasspath += sourceSets["main"].runtimeClasspath
    runtimeClasspath += output + compileClasspath
  }
}
```

> **검수 반영(컴파일 블로커):** 위 설정만으로는 `src/test`의 `QuestionValidatorTest`가 `src/contentGen`의 `QuestionValidator`를 **볼 수 없다**(별도 source set이라 test 컴파일 클래스패스에 contentGen 산출물이 없음). 아래 둘 중 하나로 해결하고, Task 전체에서 **일관되게** 적용한다.
> - **(권장, 배선 위험 최소)** 검증기·DTO·`*SeedSqlWriter` 같은 순수 도구 클래스를 별도 source set 대신 `src/test/java/ai/devpath/learning/contentgen/**`에 두고, 로컬 Ollama 호출 진입점(`main`)만 `JavaExec` task로 노출한다. production 아티팩트에 도구가 섞이지 않고 test가 바로 참조한다. 이 경우 위 `sourceSets` 블록은 생략한다.
> - **(source set 유지 시)** `sourceSets["test"]`의 compile/runtime 클래스패스에 `sourceSets["contentGen"].output`을 더하고, `contentGenImplementation`이 `implementation`을 상속하도록 구성한다. 추가 후 `.\gradlew.bat compileTestJava`로 **실제 컴파일을 먼저 확인**한다(절대조건 2·5). 검증 전엔 "된다"고 단정하지 않는다.
>
> 참고: `mockwebserver:4.12.0`는 `build.gradle.kts:50`에 **이미 있다**(슬라이스 #3에서 추가). Task 3에서 추가 의존성 없이 바로 쓴다.

필요 task:

- `validateQuestions`
- `makeQuestionSeedSql`
- `generateQuestionsLocal` (로컬 Ollama 전용, CI 호출 금지)

- [ ] **Step 2: 실패 테스트 작성**

`QuestionValidatorTest` 케이스:

- `SHORT_ANSWER`가 있으면 실패.
- Bloom `CREATE`가 있으면 실패.
- `answerKey.correct`가 options 범위 밖이면 실패.
- track별 100개가 아니면 실패.
- track별 `MCQ=70`, `CODE_READING=30`이 아니면 실패.
- difficulty가 0.0~1.0 범위 밖이면 실패.
- `conceptTags`가 비어 있거나 kebab-case가 아니면 실패.
- (비차단 경고) track별 난이도 밴드/Bloom 분포가 §4.4 목표에서 벗어나면 리포트에 표시(테스트 실패 아님). 경고 카운트를 반환하는 메서드를 두고, 강제 전환 시 이 카운트를 assert로 올린다.

Expected: validator 구현 전 컴파일 실패 또는 테스트 실패.

---

## Task 2: question schema, DTO, validator 구현

**Files:**
- Create: `tools/content-gen/schemas/question.schema.json`
- Create: `src/contentGen/java/ai/devpath/learning/contentgen/question/ApprovedQuestion.java`
- Create: `QuestionValidator.java`, `QuestionQuota.java`, `QuestionJsonlReader.java`

- [ ] **Step 1: schema 작성**

필수 필드:

```json
{
  "track": "BACKEND_SPRING",
  "questionType": "MCQ",
  "content": "문항 본문",
  "options": ["A", "B", "C", "D"],
  "answerKey": {"correct": 0},
  "bloomLevel": "APPLY",
  "difficulty": 0.5,
  "conceptTags": ["spring-tx"],
  "explanation": "검수용 해설"
}
```

- [ ] **Step 2: validator 구현**

> **검수 반영(Jackson 3):** 이 레포는 Spring Boot 4 = **Jackson 3**이다. JSONL 파싱은 `tools.jackson.databind.json.JsonMapper`(필요 시 `tools.jackson.core.type.TypeReference`)를 쓴다 — `com.fasterxml.jackson...ObjectMapper`가 **아니다**(기존 `AssessmentService`·`LearningPathQueryService`·`AssessmentEventPublisher`·`GuestSessionStore` 전부 `JsonMapper` 주입, 실코드 확인). JSONL은 줄 단위로 `jsonMapper.readValue(line, ApprovedQuestion.class)`로 읽는다.

Jackson(`JsonMapper`)으로 JSONL을 파싱하고 schema와 quota를 명시 검증한다. generic schema validator dependency를 추가할 경우 의존성 다운로드 실패 가능성을 먼저 확인한다. 실패하면 explicit validator를 SSoT로 두고 schema 파일은 계약 문서로 유지한다.

- [ ] **Step 3: focused tests**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.contentgen.question.*"
```

Expected: validator 테스트 PASS.

---

## Task 3: Ollama client는 mockable boundary로만 추가

**Files:**
- Create: `QuestionDraftClient.java`
- Create: `OllamaQuestionDraftClient.java`
- Create: `GenerateQuestionsCommand.java`
- Create tests with fixture/mock server

- [ ] **Step 1: client boundary**

`QuestionDraftClient.generate(track, count, prompt)`는 JSONL 문자열 또는 `List<ApprovedQuestion>` 초안을 반환한다.

`OllamaQuestionDraftClient`는 로컬 수동 실행에서만 `OLLAMA_BASE_URL` 기본 `http://localhost:11434`로 `/api/chat`을 호출한다.

- [ ] **Step 2: CI safety test**

테스트는 MockWebServer 또는 fake client만 사용한다. 실제 `localhost:11434` 호출이 테스트에 있으면 실패로 본다.

- [ ] **Step 3: manual command 문서화**

`tools/content-gen/README.md`에만 수동 명령을 적는다.

```powershell
.\gradlew.bat generateQuestionsLocal -Pollama.model=qwen2.5:7b
.\gradlew.bat validateQuestions
.\gradlew.bat makeQuestionSeedSql
```

---

## Task 4: seed SQL 생성 결정성

**Files:**
- Create: `QuestionSeedSqlWriter.java`
- Create test: `QuestionSeedSqlWriterTest.java`
- Create: `tools/content-gen/generated/approved/questions.fixture.jsonl`

- [ ] **Step 1: 결정성 테스트**

같은 approved JSONL을 두 번 seed SQL로 만들면 byte-for-byte 동일해야 한다.

- [ ] **Step 2: SQL 규칙**

`question_bank` 컬럼:

```sql
track, question_type, content, options, answer_key, bloom_level, difficulty, concept_tags
```

정렬 순서:

1. track enum 순서
2. questionType `MCQ` then `CODE_READING`
3. difficulty asc
4. normalized content hash asc

중복 재적재를 피하려면 B1에서는 fresh/dev seed를 기준으로 하고, 운영 idempotent insert가 필요하면 후속으로 `content` hash key 도입을 검토한다. 현재 shared schema에 natural unique가 없으므로 `ON CONFLICT`를 억지로 쓰지 않는다.

---

## Task 5: 승인 문항 500개와 seed 적용 테스트

**Files:**
- Create: `tools/content-gen/generated/approved/questions.jsonl`
- Create: `tools/content-gen/generated/seeds/question_bank_seed.sql`
- Create: `src/main/resources/db/seed/question_bank_md2_seed.sql`
- Create or Modify: `src/test/resources/seed/question_bank_md2_seed.sql`
- Modify: `SeedSqlTest.java`

- [ ] **Step 1: approved JSONL 추가**

track별 100개:

- `BACKEND_SPRING`: 70 MCQ + 30 CODE_READING
- `FRONTEND_REACT`: 70 MCQ + 30 CODE_READING
- `MOBILE_FLUTTER`: 70 MCQ + 30 CODE_READING
- `DEVOPS`: 70 MCQ + 30 CODE_READING
- `FULLSTACK`: 70 MCQ + 30 CODE_READING

- [ ] **Step 2: seed SQL 생성**

```powershell
.\gradlew.bat validateQuestions
.\gradlew.bat makeQuestionSeedSql
```

생성된 SQL을 `src/main/resources/db/seed/question_bank_md2_seed.sql`로 복사하거나 task가 직접 쓰게 한다.

- [ ] **Step 3: SeedSqlTest 강화**

테스트:

- 총 500개 이상 적재.
- track별 100개.
- track별 `SHORT_ANSWER` 0개.
- track별 `MCQ=70`, `CODE_READING=30`.
- Bloom `CREATE` 0개.
- `answer_key->correct`가 options 범위 안.

구현 메모(검수 반영):
- **@Sql 재지정**: 현재 `SeedSqlTest`는 `@Sql("/seed/question_bank_seed.sql")`(17개)을 로드한다. 클래스 `@Sql`을 MD2 seed로 바꾼다. **중복 파일을 피하려면 test-resource 사본 대신 main 리소스를 직접 로드**한다: `@Sql("/db/seed/question_bank_md2_seed.sql")` (main 리소스도 test 클래스패스에 포함). 기존 `seedLoadsBackendQuestions`(BACKEND_SPRING≥15)는 그대로 통과(100≥15)하거나 100 단언으로 갱신한다.
- **카운트 수단**: `QuestionBankRepository`는 `findByTrack(String)`+`count()`만 있다(확인). track×type/Bloom 카운트는 `findByTrack(t).stream().filter(q -> q.getQuestionType().equals("MCQ")).count()`처럼 엔티티 getter로 센다. `answer_key->correct` 범위 위반은 SQL이 가장 단순하다 — `JdbcTemplate`으로 `SELECT count(*) FROM question_bank WHERE (answer_key->>'correct')::int < 0 OR (answer_key->>'correct')::int >= jsonb_array_length(options)` = 0 을 단언한다(`options`/`answer_key`는 JSONB).

```powershell
.\gradlew.bat test --tests ai.devpath.learning.seed.SeedSqlTest
```

---

## Task 6: dev profile seeder 교체

**Files:**
- Modify: `src/main/java/ai/devpath/learning/seed/QuestionBankSeeder.java`

- [ ] **Step 1: 하드코딩 17개 제거**

기존 BACKEND_SPRING 17개 루프를 제거하고, classpath `db/seed/question_bank_md2_seed.sql`을 읽어 실행한다.

정책:

- `question_bank` 총 count가 500 이상이면 no-op.
- count가 0이면 전체 seed 실행.
- 0보다 크고 500보다 작으면 warn 후 no-op 또는 fail-fast 중 하나를 택한다. 권장: fail-fast로 부분 seed를 드러낸다.

구현 메모(검수 반영): 현재 `QuestionBankSeeder`는 `@Profile("dev")` `CommandLineRunner`로 `QuestionBankRepository.save()`(JPA)를 쓰고, no-op 조건이 `findByTrack("BACKEND_SPRING").isEmpty()`(단일 track)다. MD2 전환 시 — (1) 17개 루프와 단일 track 조건을 제거하고, (2) count는 `questions.count()`(JpaRepository 제공)로 판정하며, (3) SQL 파일 적재는 JPA save가 아니라 `DataSource` 기반으로 실행한다: `new ResourceDatabasePopulator(new ClassPathResource("db/seed/question_bank_md2_seed.sql")).execute(dataSource)` 또는 `JdbcTemplate`. seeder는 `DataSource`(또는 `JdbcTemplate`)를 주입받도록 생성자를 바꾼다.

- [ ] **Step 2: seeder 테스트**

dev profile runner를 직접 unit test하기 어렵다면 `SeedSqlTest`로 SQL 자체를 보증하고, seeder는 resource 존재 여부만 lightweight test한다.

---

## Task 7: 전체 검증과 PR

- [ ] **Step 1: focused tests**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.contentgen.question.*"
.\gradlew.bat test --tests ai.devpath.learning.seed.SeedSqlTest
```

- [ ] **Step 2: full test/build**

```powershell
.\gradlew.bat test
.\gradlew.bat clean build
```

- [ ] **Step 3: no real Ollama scan**

```powershell
rg -n "localhost:11434|/api/chat|generateQuestionsLocal" src tools build.gradle.kts
```

Expected: real Ollama call exists only in local command/client, not in tests or CI workflow.

- [ ] **Step 4: develop PR**

```powershell
git push -u origin feat/slice4-question-bank-seed
gh pr create --base develop --title "feat: MD2 slice4 approved diagnostic question seed" --body "Adds content-gen question validation and 500 approved question_bank seed."
```

---

## Acceptance Checklist

- [ ] `tools/content-gen` 문항 validator가 있다.
- [ ] 승인 문항 JSONL 500개가 있다.
- [ ] seed SQL이 결정적으로 생성된다.
- [ ] `question_bank` seed는 5 track x 100개다.
- [ ] MD2 seed에 `SHORT_ANSWER`와 Bloom `CREATE`가 없다.
- [ ] CI/test는 Ollama를 호출하지 않는다.
- [ ] dev `QuestionBankSeeder`가 17개 하드코딩 대신 MD2 seed를 사용한다.
- [ ] `.\gradlew.bat test`와 `.\gradlew.bat clean build`가 통과한다.

## Self-Review

- **Spec coverage:** 설계서 §4.1~§4.4, §4.8~§4.9, §9 Build B1, §11.2 batch 테스트를 커버한다.
- **Current source alignment:** 현재 `QuestionBankSeeder`와 `src/test/resources/seed/question_bank_seed.sql`는 BACKEND_SPRING 17개 중심이다. 본 빌드는 그 임시 seed를 MD2 seed로 대체한다.
- **검수 정정(실코드 대조):** `QuestionBank` 엔티티는 `options`/`answer_key`/`concept_tags`를 `@JdbcTypeCode(JSON) String`으로, `difficulty`를 `double`로 매핑한다. 기존 test seed의 JSON 리터럴 포맷(`'["a","b"]'`,`'{"correct":0}'`)을 MD2 seed도 그대로 따른다(2~4지선다 허용, 최소 2개). 파싱은 Jackson 3 `JsonMapper`. `QuestionBankRepository`=`findByTrack`+`count()`(확인).
- **B1↔B2 결합:** B1이 `tools/content-gen` 스캐폴드 + `build.gradle.kts`의 contentGen 배선/task를 **최초로 만든다**. B2는 이를 확장(content schema/prompt/seed)한다. 따라서 `tools/content-gen`·`build.gradle.kts`·README는 B1/B2 동시 수정 시 충돌하므로 **B2는 B1 머지 후 rebase**가 안전하다(설계서의 "B1/B2 병렬"은 데이터 생성 작업 기준).
- **Boundary safety:** B1은 question data only다. contents와 embeddings는 B2로 남긴다.
