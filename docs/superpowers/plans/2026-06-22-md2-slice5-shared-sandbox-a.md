# 슬라이스 #5 빌드 A — shared `sandbox_sessions` 스키마 + `SandboxRunSubmittedEvent` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** sandbox-svc가 의존할 `sandbox_sessions` 테이블(중앙 Flyway)과 `SandboxRunSubmittedEvent` 도메인 이벤트를 devpath-shared에 추가하고 develop→main 릴리스(GitHub Packages publish)한다.

**Architecture:** 슬라이스 #2~#4의 shared 빌드 A 패턴 그대로. 마이그레이션 SQL 1개 + `FlywayMigrationTest` 계약 테스트 추가 + `DomainEvent` 구현 record 1개 + 이벤트 테스트. main 릴리스로 jar publish해 다운스트림(sandbox-svc)이 의존.

**Tech Stack:** Java 21 · Gradle(Kotlin DSL) · `java-library` · Flyway · PostgreSQL 17 · JUnit 5.

## Global Constraints

- 대상 레포: **devpath-shared 단독**.
- 마이그레이션 번호 = **`V202606221001`**(기존 최신 `V202606201001` 다음, 오늘 날짜 06-22). 파일명 `V202606221001__sandbox_sessions.sql`.
- **교차서비스 FK 금지**(슬라이스 #2 교훈): `sandbox_sessions`의 `user_id`(platform)·`content_id`/`code_block_id`(learning)는 **다른 서비스 소유 → FK 없는 논리 참조 BIGINT**. `code_blocks` 테이블은 존재하지 않음(확인됨).
- 공통 함수 `set_updated_at`은 이미 `V202606150900__init_common.sql`에 존재 — 재사용(트리거만 생성).
- 이벤트: `ai.devpath.shared.event` record, `DomainEvent` 구현, `eventType` = `sandbox.run.submitted`(`<도메인>.<엔티티>.<동작>`).
- 모든 변경은 실패 테스트 우선(레포 CLAUDE.md 절대조건 2). 검증은 **fresh DB(devpath_citest) 또는 CI**로(로컬 devpath DB는 이미 적용분 가짜통과 위험 — 슬라이스 #2/#3 교훈).
- 신규 작업 브랜치는 `develop`에서 분기(레포 CLAUDE.md 규칙 4).

---

## File Structure

- Create: `src/main/resources/db/migration/V202606221001__sandbox_sessions.sql` — sandbox_sessions 테이블.
- Create: `src/main/java/ai/devpath/shared/event/SandboxRunSubmittedEvent.java` — 도메인 이벤트 record.
- Create(test): `src/test/java/ai/devpath/shared/event/SandboxRunSubmittedEventTest.java` — eventType 안정성.
- Modify: `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java` — sandbox_sessions 계약 테스트 2개 추가(파일 끝 `}` 앞에 메서드 삽입).

> 본보기: `V202606201001__user_content_progress.sql`(마이그레이션), `LearningPathGeneratedEvent.java`/`LearningPathGeneratedEventTest.java`(이벤트), `FlywayMigrationTest.userContentProgressTableContract`(테스트).

---

## Task 0: 작업 브랜치

- [ ] **Step 1: 브랜치 분기**

```powershell
cd devpath-shared
git switch develop
git pull
git switch -c feat/sandbox-sessions-schema
```

---

## Task 1: sandbox_sessions 마이그레이션 + 계약 테스트

**Files:**
- Create: `src/main/resources/db/migration/V202606221001__sandbox_sessions.sql`
- Modify(test): `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`

**Interfaces:**
- Produces: `sandbox_sessions` 테이블(컬럼·CHECK·인덱스·트리거). 빌드 B(sandbox-svc)가 JPA 엔티티로 매핑.

- [ ] **Step 1: 실패 테스트 작성** — `FlywayMigrationTest.java` 파일 끝의 마지막 `}` **앞에** 다음 두 메서드를 추가한다.

```java
  @Test
  void sandboxSessionsTableContract() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      try (var rs = c.getMetaData().getTables(null, "public", "sandbox_sessions",
          new String[] {"TABLE"})) {
        assertTrue(rs.next(), "sandbox_sessions 테이블 필요");
      }
      var cols = columns("sandbox_sessions");
      for (String col : new String[] {"id", "user_id", "content_id", "code_block_id",
          "language", "container_id", "status", "submitted_code", "stdout", "stderr",
          "exit_code", "cpu_ms_used", "memory_mb_peak", "started_at", "finished_at",
          "created_at", "updated_at"}) {
        assertTrue(cols.contains(col), "sandbox_sessions." + col + " 컬럼 필요");
      }
      // language CHECK 위반 거부
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO sandbox_sessions(user_id,language,submitted_code) "
              + "VALUES (1,'RUBY','x')"));
      // status CHECK 위반 거부
      assertThrows(java.sql.SQLException.class, () ->
          st.execute("INSERT INTO sandbox_sessions(user_id,language,status,submitted_code) "
              + "VALUES (1,'PYTHON','BOGUS','x')"));
      // 실습 이력 인덱스
      try (var rs = st.executeQuery(
          "SELECT 1 FROM pg_indexes WHERE schemaname = 'public' "
              + "AND tablename = 'sandbox_sessions' "
              + "AND indexname = 'idx_sandbox_user_started'")) {
        assertTrue(rs.next(), "user 실습이력 인덱스 필요");
      }
    }
  }

  @Test
  void sandboxSessionsHasNoUserFkAndUpdatedAtTrigger() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      long userId = 999_999_000L + (System.nanoTime() % 100_000L);
      long sid;
      // user_id는 platform users 논리 참조다. users FK가 없어야 이 INSERT가 통과한다.
      try (var rs = st.executeQuery(
          "INSERT INTO sandbox_sessions(user_id,language,submitted_code) "
              + "VALUES (" + userId + ",'PYTHON','print(1)') RETURNING id")) {
        assertTrue(rs.next(), "sandbox_session id 필요");
        sid = rs.getLong(1);
      }
      st.execute("UPDATE sandbox_sessions "
          + "SET updated_at = TIMESTAMPTZ '2000-01-01 00:00:00+00', status = 'RUNNING' "
          + "WHERE id = " + sid);
      try (var rs = st.executeQuery(
          "SELECT updated_at > TIMESTAMPTZ '2020-01-01 00:00:00+00' "
              + "FROM sandbox_sessions WHERE id = " + sid)) {
        assertTrue(rs.next(), "updated_at 결과 필요");
        assertTrue(rs.getBoolean(1), "updated_at trigger가 now()로 갱신되어야 한다");
      }
      st.execute("DELETE FROM sandbox_sessions WHERE id = " + sid);
    }
  }
```

> `columns(String)`·`dataSource()`·`assertThrows`·`assertTrue`는 이 테스트 파일에 이미 존재(import 추가 불필요).

- [ ] **Step 2: 실패 확인(fresh DB)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.shared.db.FlywayMigrationTest"
```

Expected: 신규 2개 케이스 FAIL(sandbox_sessions 테이블 없음).

- [ ] **Step 3: 마이그레이션 작성** — `src/main/resources/db/migration/V202606221001__sandbox_sessions.sql`:

```sql
-- MD2 Slice #5: sandbox code execution sessions.
-- user_id(platform) / content_id, code_block_id(learning) are cross-service logical
-- references only — NO FK (service boundary; 슬라이스 #2 교훈). code_blocks 테이블 부재.
CREATE TABLE sandbox_sessions (
  id              BIGSERIAL PRIMARY KEY,
  user_id         BIGINT NOT NULL,
  content_id      BIGINT,
  code_block_id   BIGINT,
  language        VARCHAR(16) NOT NULL,
  container_id    VARCHAR(128),
  status          VARCHAR(16) NOT NULL DEFAULT 'ALLOCATING',
  submitted_code  TEXT NOT NULL,
  stdout          TEXT,
  stderr          TEXT,
  exit_code       INT,
  cpu_ms_used     BIGINT,
  memory_mb_peak  INT,
  started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_sandbox_language CHECK (language IN ('JAVA','NODE','PYTHON')),
  CONSTRAINT chk_sandbox_status CHECK (status IN ('ALLOCATING','RUNNING','COMPLETED','FAILED','KILLED'))
);

CREATE INDEX idx_sandbox_user_started ON sandbox_sessions(user_id, started_at DESC);

CREATE TRIGGER sandbox_sessions_set_updated_at BEFORE UPDATE ON sandbox_sessions
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

- [ ] **Step 4: 통과 확인(fresh DB)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test --tests "ai.devpath.shared.db.FlywayMigrationTest"
```

Expected: 전체 PASS(신규 2개 포함). 기존 마이그레이션 테스트 회귀 없음.

- [ ] **Step 5: 커밋**

```powershell
git add src/main/resources/db/migration/V202606221001__sandbox_sessions.sql src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(schema): add sandbox_sessions table (MD2 slice5 build A)"
```

---

## Task 2: SandboxRunSubmittedEvent + 테스트

**Files:**
- Create: `src/main/java/ai/devpath/shared/event/SandboxRunSubmittedEvent.java`
- Create(test): `src/test/java/ai/devpath/shared/event/SandboxRunSubmittedEventTest.java`

**Interfaces:**
- Produces: `SandboxRunSubmittedEvent(UUID eventId, Instant occurredAt, long userId, long sandboxSessionId, String language, Long contentId)` · `EVENT_TYPE = "sandbox.run.submitted"`. 빌드 B(sandbox-svc)가 outbox로 발행, #6(ai-svc)이 구독.

- [ ] **Step 1: 실패 테스트 작성** — `src/test/java/ai/devpath/shared/event/SandboxRunSubmittedEventTest.java`:

```java
package ai.devpath.shared.event;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class SandboxRunSubmittedEventTest {

	@Test
	void eventTypeIsStable() {
		var event = new SandboxRunSubmittedEvent(
				UUID.randomUUID(), Instant.now(), 1L, 10L, "PYTHON", 5L);
		assertEquals("sandbox.run.submitted", event.eventType());
	}

	@Test
	void contentIdIsNullable() {
		var event = new SandboxRunSubmittedEvent(
				UUID.randomUUID(), Instant.now(), 1L, 10L, "JAVA", null);
		assertEquals(null, event.contentId());
	}
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.shared.event.SandboxRunSubmittedEventTest"
```

Expected: 컴파일 실패(`SandboxRunSubmittedEvent` 없음).

- [ ] **Step 3: 이벤트 구현** — `src/main/java/ai/devpath/shared/event/SandboxRunSubmittedEvent.java`:

```java
package ai.devpath.shared.event;

import java.time.Instant;
import java.util.UUID;

/**
 * 샌드박스 코드 실행 제출 이벤트.
 * sandbox-svc가 Transactional Outbox로 발행하고, ai-svc(코드 리뷰, 슬라이스 #6)가 구독한다.
 * contentId는 실습 콘텐츠 연결로 nullable이다.
 */
public record SandboxRunSubmittedEvent(
		UUID eventId,
		Instant occurredAt,
		long userId,
		long sandboxSessionId,
		String language,
		Long contentId
) implements DomainEvent {

	public static final String EVENT_TYPE = "sandbox.run.submitted";

	@Override
	public String eventType() {
		return EVENT_TYPE;
	}
}
```

- [ ] **Step 4: 통과 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.shared.event.SandboxRunSubmittedEventTest"
```

Expected: 2개 케이스 PASS.

- [ ] **Step 5: 커밋**

```powershell
git add src/main/java/ai/devpath/shared/event/SandboxRunSubmittedEvent.java src/test/java/ai/devpath/shared/event/SandboxRunSubmittedEventTest.java
git commit -m "feat(event): add SandboxRunSubmittedEvent (MD2 slice5 build A)"
```

---

## Task 3: 전체 회귀 + develop PR + main 릴리스(publish)

- [ ] **Step 1: 전체 빌드(fresh DB)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat clean build
```

Expected: BUILD SUCCESSFUL. 전 마이그레이션 테스트 + 이벤트 테스트 PASS.

- [ ] **Step 2: develop PR 생성·CI 녹색·머지**

```powershell
git push -u origin feat/sandbox-sessions-schema
gh pr create --base develop --title "feat(schema): sandbox_sessions + SandboxRunSubmittedEvent (slice5 A)" --body "MD2 슬라이스 #5 빌드 A. sandbox_sessions 테이블(교차서비스 FK 없음·language/status CHECK·실습이력 인덱스·set_updated_at 트리거) + SandboxRunSubmittedEvent. 설계서 docs/superpowers/specs/2026-06-22-md2-slice5-sandbox-design.md"
gh pr checks --watch
```

Expected: CI `build` 녹색. 녹색 확인 후에만 머지(컨트롤러 직접 검증).

- [ ] **Step 3: develop→main 릴리스(publish)**

```powershell
gh pr create --base main --head develop --title "release(shared): sandbox_sessions + SandboxRunSubmittedEvent → main" --body "슬라이스 #5 빌드 A develop→main 릴리스. publish.yml로 GitHub Packages 배포(다운스트림 sandbox-svc 의존)."
gh pr checks --watch
```

Expected: CI 녹색 → 머지 → `publish.yml`(`./gradlew publish`)로 jar 배포. 빌드 B(sandbox-svc)는 이 jar에 의존하므로 **릴리스 선행 필수**.

---

## Self-Review 메모(작성자)

- **Spec 커버리지**: 설계서 §4 데이터모델(sandbox_sessions + language·status CHECK·인덱스·트리거·FK 없음) → Task1. `SandboxRunSubmittedEvent`(§2 D-6) → Task2. 릴리스 선행(§9 빌드 A) → Task3. quota·test_results는 §10 제외(미생성) — 플랜에서도 미포함(일치).
- **No placeholder**: 마이그레이션 SQL·이벤트 record·테스트 전량 실코드. 마이그레이션 번호 `V202606221001` 확정.
- **타입 일관성**: `SandboxRunSubmittedEvent(UUID,Instant,long,long,String,Long)`·`EVENT_TYPE="sandbox.run.submitted"`·테이블 `sandbox_sessions`·CHECK 값(JAVA/NODE/PYTHON, ALLOCATING/RUNNING/COMPLETED/FAILED/KILLED)이 본문·테스트·설계서와 일관.
- **교훈**: fresh DB(devpath_citest) 검증(로컬 devpath 가짜통과 회피), 교차서비스 FK 없음, 이벤트 record+DomainEvent 패턴.
