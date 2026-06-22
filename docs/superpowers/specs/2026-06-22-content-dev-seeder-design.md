# 설계서 — 콘텐츠 dev seeder (빌드 B2 잔여, 2026-06-22)

> **상태**: 신규. 슬라이스 #4(콘텐츠 대량화) 빌드 B2에서 생성·검증된 150편 콘텐츠 seed 산출물을 메인 개발 DB에 적재하는 dev seeder가 부재한 잔여 항목을 정식 설계로 승격.
> **위치**: MD2 슬라이스 #4 빌드 B2 후속. 대상 레포 = `devpath-learning-svc` 단독. shared 스키마 변경 없음.
> **원칙**: 이미 검증된 seed SQL 산출물을 SSoT로 재사용한다. 기존 `QuestionBankSeeder` 패턴을 그대로 미러링한다. 기존 DB 데이터를 자동으로 파기하지 않는다(안전). 모든 변경은 실패 테스트 우선.

---

## 0. 배경

슬라이스 #4 빌드 B2(`devpath-learning-svc` PR #14)에서 5개 track × 30편 = 150편의 `PUBLISHED` 콘텐츠와 그 chunk embedding을 생성·검수해, 재현 가능한 seed 산출물(`db/seed/content_md2_seed.sql`)과 승인 JSON(`tools/content-gen/generated/approved/contents.jsonl` 150줄, `content_embeddings.jsonl`)을 만들었다.

그러나 이 seed SQL을 **메인 개발 DB(`devpath`)에 적재하는 dev seeder가 없다**. 슬라이스 #2에서 문항용 `QuestionBankSeeder`(`@Profile("dev")`)는 만들었지만 콘텐츠용 대응물은 누락됐다. 그 결과 메인 DB에는 콘텐츠가 **11개만** 존재하고(출처 불명, 슬라이스 #3 끝단간 수동 삽입 추정), 150편 승인 콘텐츠는 적재되지 않았다. 이 상태에서는 슬라이스 #3 경로 매칭·슬라이스 #4 뷰어를 실데이터로 끝단간 시연할 수 없다.

## 1. 목적과 완료 기준

### 1.1 목적
검증된 `content_md2_seed.sql`을 `dev` 프로파일 기동 시 메인 DB에 자동 적재하는 `ContentSeeder`를 `QuestionBankSeeder`와 동일한 패턴으로 추가한다.

### 1.2 완료 기준(DoD)
- `dev` 프로파일로 기동 시, `contents`가 비어 있으면 150편 콘텐츠 + 150 chunk embedding이 적재된다.
- `contents`가 이미 150편 이상이면 seeder는 **아무 것도 하지 않는다**(멱등 no-op, 재기동 안전).
- `contents`가 `0 < count < 150`인 부분 적재 상태면 seeder는 `IllegalStateException`으로 **기동을 멈춘다**(데이터 정합 보호, 자동 파기 금지).
- `test` 프로파일에는 seeder 빈이 생성되지 않아 기존 테스트에 영향이 없다.
- `ContentSeeder`의 count 분기(적재/부분시드 예외/no-op) 로직을 검증하는 테스트가 녹색.
- 기존 `ContentSeedSqlTest`(seed SQL 내용 150/150/track별 30) 회귀 통과.

### 1.3 범위 외
- shared 마이그레이션/스키마 변경. 콘텐츠 적재는 데이터 작업이지 스키마 작업이 아니다.
- 기존 메인 DB 11개 콘텐츠의 자동 마이그레이션·병합. **운영자가 수동 정리**(§6).
- prod/staging seeding. 본 seeder는 `@Profile("dev")` 한정. 배포 환경 시딩은 별도 운영 절차.
- Upsert(부족분 채움)·기동마다 재적재(사용자 결정으로 미채택).
- admin 콘텐츠 CRUD, 런타임 콘텐츠 생성.

## 2. 현재 상태 (실측)

### 2.1 본보기 — `QuestionBankSeeder`
`src/main/java/ai/devpath/learning/seed/QuestionBankSeeder.java`:
- `@Component @Profile("dev")` `implements CommandLineRunner`.
- 생성자 주입: `QuestionBankRepository`, `DataSource`.
- `run()`: `questions.count()` → `>= 500L` 이면 return(no-op); `> 0` 이면 `IllegalStateException("partial seed data ...; expected 0 or >= 500")`; `== 0` 이면 `ResourceDatabasePopulator(new ClassPathResource("db/seed/question_bank_md2_seed.sql")).execute(dataSource)`.

### 2.2 콘텐츠 seed 산출물 (검증됨)
- `src/main/resources/db/seed/content_md2_seed.sql` — 3122줄. `INSERT INTO contents|content_embeddings` 라인 151개(contents multi-row 1 INSERT + content_embeddings 150 INSERT). slug 기반 INSERT, **고정 id 미지정**(`RESTART IDENTITY` 후 자동 증가 안전).
- 동일 파일이 `src/test/resources/seed/content_md2_seed.sql`에도 존재하며 **두 파일은 IDENTICAL**(diff 결과 동일, 3122줄).
- `src/test/java/ai/devpath/learning/seed/ContentSeedSqlTest.java`가 이미 검증: `contents`=150, `content_embeddings`=150, 비-PUBLISHED 0, 비-ACTIVE 0, 중복 slug 0, 임베딩 없는 콘텐츠 0, track별 정확히 30(BACKEND_SPRING/FRONTEND_REACT/MOBILE_FLUTTER/DEVOPS/FULLSTACK), `embedding <=> vector` 코사인 거리 계산 가능.
- 승인 JSON: `tools/content-gen/generated/approved/contents.jsonl`(150), `content_embeddings.jsonl`.

### 2.3 콘텐츠 seeder — 부재
- `ai.devpath.learning.seed` 패키지에 `QuestionBankSeeder`만 존재. **콘텐츠용 seeder 없음**(Glob/Grep 실측).

### 2.4 리포지토리·엔티티
- `ContentRepository extends JpaRepository<Content, Long>` (`path/ContentRepository.java`) → `count()` 상속 사용 가능.
- `contents`/`content_embeddings` 스키마는 shared `V202606181006`(VECTOR(768)+HNSW, status ACTIVE/INACTIVE).

### 2.5 프로파일·DataSource
- `src/main/resources/application.yml`: 프로파일 분리 블록 없음(단일). `spring.datasource.url=${DB_URL:jdbc:postgresql://localhost:5432/devpath}`, `ddl-auto: validate`, `spring.flyway.enabled: false`.
- `dev` 프로파일 활성화 = `--spring.profiles.active=dev` 또는 `SPRING_PROFILES_ACTIVE=dev`로 `bootRun`. `@Profile("dev")` 빈은 이때만 생성.

## 3. 설계 결정

### D-1. `QuestionBankSeeder` 패턴 미러 (채택)
`ContentSeeder`를 동일 구조로 만든다: `@Component @Profile("dev") CommandLineRunner`, 임계값 `CONTENT_SEED_COUNT = 150L`, `ResourceDatabasePopulator("db/seed/content_md2_seed.sql")`. 차이점은 count 소스(`ContentRepository.count()`)와 seed 파일명·임계값뿐. 일관성으로 학습·유지보수 비용 최소화.

### D-2. count 기준 = `contents` 행 수
seed SQL이 contents + content_embeddings를 한 파일에서 함께 INSERT하므로, 적재 판정은 `contents` 행 수 하나로 충분하다(임베딩은 contents와 1:1로 같은 트랜잭션에서 적재). count 임계 150은 contents 기준.

### D-3. 기존 11개 = 부분시드 예외 → 운영자 수동 정리 (채택)
`0 < count < 150`이면 `IllegalStateException`으로 기동을 멈춘다(QuestionBankSeeder와 동일). 즉 현재 11개 상태에서는 seeder가 **막힌다**. 이는 의도된 안전장치다: 데이터를 자동으로 지우지 않고, 운영자가 명시적으로 정리(§6)하게 강제한다. Upsert/자동 TRUNCATE는 미채택.

### D-4. 적재는 `ResourceDatabasePopulator` (DDL 아님)
seed는 데이터 INSERT일 뿐 스키마 변경이 아니다. Flyway(비활성)와 무관하게 `ddl-auto: validate` 환경에서 런타임 DataSource로 SQL을 실행한다.

## 4. 변경 대상 (파일)

- Create: `src/main/java/ai/devpath/learning/seed/ContentSeeder.java` — `QuestionBankSeeder` 미러.
- Create(test): `src/test/java/ai/devpath/learning/seed/ContentSeederTest.java` — count 분기 로직 단위 테스트.
- (문서) 운영 절차는 본 설계 §6 및 plan에 기록. 코드 외 산출물 변경 없음(seed SQL은 그대로 재사용).

## 5. 테스트 설계

### 5.1 seed SQL 내용
기존 `ContentSeedSqlTest`가 이미 충분히 커버(150/150/track별 30/중복 0/임베딩 정합). 추가 작성 불필요, 회귀만 확인.

### 5.2 `ContentSeeder` 분기 로직 (신규)
- `@Profile("dev")`라 `test` 프로파일 `@SpringBootTest`에서는 빈이 안 뜬다 → **seeder를 직접 인스턴스화**해 분기를 단위 검증(QuestionBankSeeder와 동일한 검증 전략).
- 케이스:
  - `count() == 0` → `ResourceDatabasePopulator` 실행 경로 진입(모의 `ContentRepository` count=0; populator 실행은 실 DataSource로 검증하거나 적재 후 150 단언하는 통합형 1건).
  - `0 < count() < 150`(예: 11) → `IllegalStateException`.
  - `count() >= 150` → no-op(아무 동작 없음).
- 적재 실증(선택, 통합형): `test` 프로파일에서 `ContentSeeder`를 직접 생성하고 빈 contents 상태에서 `run()` 호출 → `select count(*) from contents` == 150. (단, test 스키마 프로비저닝·격리는 `@Sql` TRUNCATE로 관리, `ContentSeedSqlTest` 패턴 참조.)

## 6. 운영 절차 (기존 11개 정리 후 적재)

dev DB에 150편을 적재하려면(seeder가 부분시드 11개에서 멈추므로):

```powershell
# 1) 기존 콘텐츠/임베딩 확인 (정체 파악)
#    psql devpath -c "select id, slug, track, status from contents order by id;"
# 2) 정리 (개발 DB 한정, 운영자 판단)
#    psql devpath -c "TRUNCATE content_embeddings, contents RESTART IDENTITY CASCADE;"
# 3) dev 프로파일로 기동 → ContentSeeder가 150편 적재
cd devpath-learning-svc
.\gradlew.bat bootRun --args='--spring.profiles.active=dev'
# 4) 검증
#    psql devpath -c "select count(*) from contents;"   -- 150
#    psql devpath -c "select count(*) from content_embeddings;"  -- 150
```

> 주의: TRUNCATE는 개발 DB에서만. learning_paths의 task가 기존 11개 contentId를 참조 중이면 CASCADE/제약을 먼저 확인한다(`contents` FK 관계 실측 후 진행, 추측 금지).

## 7. 리스크와 대응

| 리스크 | 대응 |
|---|---|
| 기존 11개와 신규 150 slug 충돌 | seeder는 0건일 때만 적재하므로 충돌 없음. 정리는 운영자가 TRUNCATE로 선행(§6). |
| 11개 contentId를 참조하는 path task | TRUNCATE 전 FK/참조 실측. 필요 시 관련 path도 정리하거나 dev DB 초기화(추측 금지). |
| `@Profile("dev")` 테스트 불가 | seeder 직접 인스턴스화로 분기 단위 테스트(QuestionBankSeeder 동일 전략). |
| seed SQL과 test 사본 드리프트 | 두 파일 IDENTICAL 현황 유지. 향후 변경 시 동기화(또는 단일 소스화는 별도 과제). |

## 8. 참고
- 본보기: `src/main/java/ai/devpath/learning/seed/QuestionBankSeeder.java`, `src/test/java/ai/devpath/learning/seed/SeedSqlTest.java`, `ContentSeedSqlTest.java`.
- 슬라이스 #4 빌드 B2 플랜: `plans/2026-06-21-md2-slice4-learning-contents-b2.md`.
- 구현 플랜: `plans/2026-06-22-content-dev-seeder.md`.
