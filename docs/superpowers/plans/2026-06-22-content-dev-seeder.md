# 콘텐츠 dev seeder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 검증된 `db/seed/content_md2_seed.sql`(콘텐츠 150 + 임베딩 150)을 `dev` 프로파일 기동 시 메인 개발 DB에 자동 적재하는 `ContentSeeder`를 `QuestionBankSeeder`와 동일한 패턴으로 추가한다.

**Architecture:** `@Component @Profile("dev")` `CommandLineRunner`로, `ContentRepository.count()`가 0이면 `ResourceDatabasePopulator`로 seed SQL을 실행하고, `0<count<150`이면 부분시드 예외로 멈추며, `>=150`이면 no-op. 기존 데이터를 자동으로 파기하지 않는다(운영자가 수동 정리).

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Spring JDBC(`ResourceDatabasePopulator`) · Spring Data JPA · PostgreSQL 17 · JUnit 5 · Mockito · AssertJ.

## Global Constraints

- 대상 레포: `devpath-learning-svc` 단독. shared 스키마·seed SQL 변경 없음(기존 산출물 재사용).
- seed 파일: `src/main/resources/db/seed/content_md2_seed.sql`(3122줄, contents 150 + content_embeddings 150). `src/test/resources/seed/content_md2_seed.sql`와 IDENTICAL.
- 임계값 `CONTENT_SEED_COUNT = 150L`. count 소스 = `ContentRepository.count()`(contents 행 수).
- `0<count<150`이면 `IllegalStateException`(자동 파기 금지, 운영자 수동 정리). Upsert/기동마다 재적재 미채택(사용자 결정).
- `@Profile("dev")` 한정 — `test`/기본 프로파일에는 빈이 생성되지 않아 기존 테스트에 영향 없음.
- 모든 변경은 실패 테스트 우선(레포 CLAUDE.md 절대조건 2). 적재 검증은 fresh/격리 DB로(슬라이스 교훈).
- 신규 작업 브랜치는 `develop`에서 분기(레포 CLAUDE.md 규칙 4).

---

## File Structure

- Create: `src/main/java/ai/devpath/learning/seed/ContentSeeder.java` — `QuestionBankSeeder` 미러(count 소스·임계값·seed 파일명만 다름).
- Create(test): `src/test/java/ai/devpath/learning/seed/ContentSeederTest.java` — 분기 단위(mock) + 적재 통합(@Sql TRUNCATE) 검증.
- 변경 없음: `db/seed/content_md2_seed.sql`(재사용), `application.yml`(프로파일 추가 불요 — `@Profile("dev")`는 `--spring.profiles.active=dev`로 활성화).

> 참고 본보기: `src/main/java/ai/devpath/learning/seed/QuestionBankSeeder.java`, `src/test/java/ai/devpath/learning/seed/ContentSeedSqlTest.java`(@Sql TRUNCATE 패턴).

---

## Task 0: 작업 브랜치

- [ ] **Step 1: 브랜치 분기**

```powershell
cd devpath-learning-svc
git switch develop
git pull
git switch -c feat/content-dev-seeder
```

- [ ] **Step 2: 기존 seed 검증 베이스라인 확인**

```powershell
.\gradlew.bat --refresh-dependencies test --tests "ai.devpath.learning.seed.ContentSeedSqlTest"
```

Expected: PASS(seed SQL이 150/150/track별 30을 적재함을 이미 검증). 이 테스트가 통과해야 seeder가 같은 SQL을 재사용해도 안전하다.

---

## Task 1: ContentSeeder + 분기/적재 테스트

**Files:**
- Create: `src/main/java/ai/devpath/learning/seed/ContentSeeder.java`
- Test: `src/test/java/ai/devpath/learning/seed/ContentSeederTest.java`

**Interfaces:**
- Produces: `ContentSeeder(ContentRepository contents, DataSource dataSource)` `implements CommandLineRunner`, `void run(String... args)`.
- Consumes: `ai.devpath.learning.path.ContentRepository.count()`(JpaRepository 상속), `org.springframework.jdbc.datasource.init.ResourceDatabasePopulator`, `org.springframework.core.io.ClassPathResource`.

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/learning/seed/ContentSeederTest.java`:

```java
package ai.devpath.learning.seed;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import ai.devpath.learning.path.ContentRepository;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;

@SpringBootTest
@ActiveProfiles("test")
class ContentSeederTest {

  @Autowired ContentRepository contentRepository;
  @Autowired DataSource dataSource;
  @Autowired JdbcTemplate jdbc;

  @Test
  void partialSeedThrowsAndDoesNotTouchDataSource() {
    ContentRepository repo = mock(ContentRepository.class);
    DataSource ds = mock(DataSource.class);
    when(repo.count()).thenReturn(11L);
    var seeder = new ContentSeeder(repo, ds);

    assertThatThrownBy(seeder::run)
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("partial seed");
    verifyNoInteractions(ds);
  }

  @Test
  void alreadySeededIsNoOp() {
    ContentRepository repo = mock(ContentRepository.class);
    DataSource ds = mock(DataSource.class);
    when(repo.count()).thenReturn(150L);
    var seeder = new ContentSeeder(repo, ds);

    seeder.run();

    verifyNoInteractions(ds);
  }

  @Test
  @Sql(statements = "TRUNCATE content_embeddings, contents RESTART IDENTITY CASCADE",
      executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
  @Sql(statements = "TRUNCATE content_embeddings, contents RESTART IDENTITY CASCADE",
      executionPhase = Sql.ExecutionPhase.AFTER_TEST_METHOD)
  void emptyDbLoadsOneHundredFifty() {
    new ContentSeeder(contentRepository, dataSource).run();

    assertThat(contentRepository.count()).isEqualTo(150L);
    Integer embeddings = jdbc.queryForObject(
        "select count(*) from content_embeddings", Integer.class);
    assertThat(embeddings).isEqualTo(150);
  }
}
```

> `run`은 `CommandLineRunner.run(String... args)`라 인자 없이 `seeder::run`(빈 varargs)으로 호출된다. 분기 단위 테스트는 mock으로 `count()`만 제어하고 `verifyNoInteractions(ds)`로 populator 미실행을 확인한다. 적재 테스트는 실 `DataSource`/`ContentRepository`로 빈 DB에서 seeder를 직접 실행하고 150/150을 단언한다(`@Profile("dev")`라 빈 자동생성이 없으므로 `new`로 생성). `@Sql` TRUNCATE는 `ContentSeedSqlTest`와 동일 격리 패턴.

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.seed.ContentSeederTest"
```

Expected: 컴파일 실패(`ContentSeeder` 없음) → FAIL.

- [ ] **Step 3: ContentSeeder 구현**

`src/main/java/ai/devpath/learning/seed/ContentSeeder.java`:

```java
package ai.devpath.learning.seed;

import ai.devpath.learning.path.ContentRepository;
import javax.sql.DataSource;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

/** 로컬(dev) 끝단간용 MD2 승인 콘텐츠 시드. 비어있을 때만 전체 적재. */
@Component
@Profile("dev")
public class ContentSeeder implements CommandLineRunner {

  private static final long MD2_SEED_COUNT = 150L;

  private final ContentRepository contents;
  private final DataSource dataSource;

  public ContentSeeder(ContentRepository contents, DataSource dataSource) {
    this.contents = contents;
    this.dataSource = dataSource;
  }

  @Override
  public void run(String... args) {
    long count = contents.count();
    if (count >= MD2_SEED_COUNT) {
      return;
    }
    if (count > 0) {
      throw new IllegalStateException(
          "contents has partial seed data (" + count + " rows); expected 0 or >= 150");
    }
    var populator = new ResourceDatabasePopulator(
        new ClassPathResource("db/seed/content_md2_seed.sql"));
    populator.execute(dataSource);
  }
}
```

> `QuestionBankSeeder`와 구조 동일. 차이: 주입 타입 `ContentRepository`, 임계값 150, seed 파일 `content_md2_seed.sql`, 예외 메시지("partial seed"). 메시지의 `partial seed`는 단위 테스트의 `hasMessageContaining("partial seed")`와 일치.

- [ ] **Step 4: 통과 확인(fresh/격리 DB)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.learning.seed.ContentSeederTest"
```

Expected: 3개 케이스 PASS. (적재 테스트는 빈 DB에서 150/150 적재 확인.)

- [ ] **Step 5: 커밋**

```powershell
git add src/main/java/ai/devpath/learning/seed/ContentSeeder.java src/test/java/ai/devpath/learning/seed/ContentSeederTest.java
git commit -m "feat(seed): add dev ContentSeeder for 150 MD2 contents"
```

---

## Task 2: 전체 회귀 + PR

- [ ] **Step 1: 전체 테스트(fresh DB)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat clean test
```

Expected: 기존 seed 테스트(`ContentSeedSqlTest`/`SeedSqlTest`) + 신규 `ContentSeederTest` 전부 PASS. 회귀 없음.

- [ ] **Step 2: PR 생성(develop 대상)**

```powershell
git push -u origin feat/content-dev-seeder
gh pr create --base develop --title "feat(seed): 콘텐츠 dev seeder(150편) 추가" --body "QuestionBankSeeder 미러. dev 프로파일 기동 시 contents 비어있으면 150편+임베딩 적재, 0<count<150이면 부분시드 예외, >=150 no-op. 설계서 docs/superpowers/specs/2026-06-22-content-dev-seeder-design.md"
```

- [ ] **Step 3: CI 녹색 확인**

```powershell
gh pr checks --watch
```

Expected: learning-svc CI 녹색. 녹색 확인 후에만 머지(컨트롤러 직접 검증).

---

## Task 3: (운영, 코드 외) 메인 dev DB에 150편 적재

> 코드 머지와 별개로, 메인 개발 DB(`devpath`)에 150편을 실제로 채우는 운영 절차. seeder는 기존 11개(부분시드)에서 멈추므로 수동 정리가 선행되어야 한다.

- [ ] **Step 1: 기존 콘텐츠 확인(정체 파악)**

```powershell
psql "postgresql://devpath:localdev@localhost:5432/devpath" -c "select id, slug, track, status from contents order by id;"
```

- [ ] **Step 2: 참조 무결성 확인** — 기존 11개 contentId를 참조하는 `path_weekly_tasks`가 있는지 확인(추측 금지).

```powershell
psql "postgresql://devpath:localdev@localhost:5432/devpath" -c "select count(*) from path_weekly_tasks where content_id is not null;"
```

참조가 있으면 해당 path까지 정리할지(또는 dev DB 전체 초기화) 판단한다. dev 한정 작업이다.

- [ ] **Step 3: 정리 후 dev 기동으로 적재**

```powershell
psql "postgresql://devpath:localdev@localhost:5432/devpath" -c "TRUNCATE content_embeddings, contents RESTART IDENTITY CASCADE;"
cd devpath-learning-svc
.\gradlew.bat bootRun --args='--spring.profiles.active=dev'
```

- [ ] **Step 4: 적재 검증**

```powershell
psql "postgresql://devpath:localdev@localhost:5432/devpath" -c "select count(*) from contents;"            # 150
psql "postgresql://devpath:localdev@localhost:5432/devpath" -c "select count(*) from content_embeddings;"  # 150
psql "postgresql://devpath:localdev@localhost:5432/devpath" -c "select track, count(*) from contents group by track;"  # 각 30
```

Expected: contents 150, content_embeddings 150, track별 30. (이후 dev 재기동 시 `count>=150`이라 seeder는 no-op.)

---

## Self-Review 메모(작성자)

- **Spec 커버리지**: DoD ①비었으면 150 적재(Task1 적재 테스트) ②>=150 no-op(Task1 단위) ③0<count<150 예외(Task1 단위) ④test 프로파일 무영향(`@Profile("dev")` + 단위는 mock·적재는 직접 new) ⑤분기 테스트 녹색(Task1) ⑥기존 ContentSeedSqlTest 회귀(Task0/2) — 전부 매핑. 운영 적재(§6)는 Task3.
- **placeholder 없음**: 모든 코드/명령은 실제값. seed SQL 재사용이라 신규 데이터 없음.
- **타입 일관성**: `ContentSeeder(ContentRepository, DataSource)`, `MD2_SEED_COUNT=150L`, 예외 메시지 "partial seed", seed 경로 `db/seed/content_md2_seed.sql`가 본문·테스트·QuestionBankSeeder 패턴과 일관.
- **YAGNI**: Upsert·기동마다 재적재·prod 시딩은 범위 외(미채택). 단일 seeder + 운영 절차로 최소 구현.
