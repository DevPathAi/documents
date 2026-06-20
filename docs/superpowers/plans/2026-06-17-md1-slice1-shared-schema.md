# MD1 슬라이스 #1 — devpath-shared 스키마·이벤트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** OAuth/인증 게이트의 데이터 기반인 중앙 스키마(users 확장·user_oauth_identities·user_profiles·outbox)와 `UserRegisteredEvent`를 devpath-shared에 추가한다.

**Architecture:** devpath-shared가 중앙 Flyway 스키마(SSoT)와 공유 이벤트 record를 소유한다. 마이그레이션은 기존 `VYYYYMMDDHHMM__*.sql` 규약으로 W1 baseline(`V202606150900~0902`) 다음 번호에 추가하고, 기존 `FlywayMigrationTest`(PGSimpleDataSource + Flyway.migrate + JDBC 메타데이터 검증) 패턴을 그대로 확장한다. **Testcontainers는 쓰지 않는다** — 로컬 docker-compose PostgreSQL(또는 CI service container)에 연결한다.

**Tech Stack:** Java 21 · Gradle(Kotlin DSL) · `java-library` · Flyway 11.8.2 · PostgreSQL 17 · JUnit 5(junit-jupiter, junit-bom 6.0.1) · Jackson 2.20.1.

## Global Constraints

- Java 21 toolchain. 신규 의존성 추가 금지 — 기존 build.gradle.kts 의존성만 사용(Flyway·PGSimpleDataSource·JUnit·Jackson).
- 마이그레이션 파일명: `VYYYYMMDDHHMM__<설명>.sql`, `src/main/resources/db/migration/`. W1 다음 번호(`V20260617xxxx`). 기존 파일 수정 금지 — 신규 추가만(Flyway 불변성).
- 모든 테이블: snake_case, `created_at`/`updated_at TIMESTAMPTZ` audit 컬럼 + `set_updated_at` BEFORE UPDATE 트리거(공통 규약, `V202606150900__init_common.sql`이 함수 정의).
- 이벤트: `ai.devpath.shared.event` 패키지, `DomainEvent` 구현 record. `eventType`은 `<도메인>.<엔티티>.<동작>` 소문자 점 표기. 하위 호환을 깨는 필드 변경 금지(새 필드 nullable/기본값).
- ERD 권위: 02_ERD §1 — `users.role` ∈ {LEARNER, ADMIN}, `onboarding_status` ∈ {PENDING, IN_PROGRESS, DONE}, provider ∈ {GITHUB, GOOGLE, KAKAO}, `learning_goal` ∈ {JOB, CAREER_CHANGE, UPSKILL, SIDE_PROJECT}, `target_track` ∈ {BACKEND_SPRING, FRONTEND_REACT, MOBILE_FLUTTER, DEVOPS, FULLSTACK}.
- 비밀값 커밋 금지.
- 브랜치: devpath-shared `develop`에서 `feat/oauth-schema` 분기 → `develop` PR(2단계). main 직접 금지.

## Preconditions

- 작업 디렉터리: `D:\workspace\dev-path-ai\devpath-shared`.
- PostgreSQL 가동 필요(테스트가 실DB 연결): `docker compose up -d` (PostgreSQL 17 / `devpath` db / `devpath` user / `localdev` pw — `docker-compose.yml`·`build.gradle.kts` flyway 블록·기존 테스트 기본값 일치).
- 깨끗한 스키마에서 검증하려면(github_id 제거 등 ALTER 확인) 필요 시 DB 재생성: `docker compose down -v && docker compose up -d`.
- 브랜치 분기:
```bash
cd /d/workspace/dev-path-ai/devpath-shared
git checkout develop && git pull
git checkout -b feat/oauth-schema
```

---

### Task 1: users 골격 인증 확장 + github_id 이관

W1 `users`(id·github_id·status·*_at)에 인증/온보딩 컬럼을 추가하고, GitHub 신원을 `user_oauth_identities`로 이관하기 위해 `github_id`를 제거한다.

**Files:**
- Create: `src/main/resources/db/migration/V202606171001__users_auth_extension.sql`
- Modify(test): `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`

**Interfaces:**
- Consumes: `set_updated_at()` 함수(`V202606150900`), `users` 테이블(`V202606150901`).
- Produces: `users(id, status, created_at, updated_at, last_active_at, email, nickname, role, onboarding_status)` — `github_id` 없음. `email` UNIQUE(nullable).

- [ ] **Step 1: 실패하는 테스트 작성** — `FlywayMigrationTest.java`에 컬럼 헬퍼와 테스트 메서드를 추가한다. 파일 상단 import에 `import static org.junit.jupiter.api.Assertions.assertFalse;`를 추가하고, 클래스 안에 아래를 추가:

```java
  private static java.util.Set<String> columns(String table) throws Exception {
    try (var c = dataSource().getConnection();
        var rs = c.getMetaData().getColumns(null, "public", table, "%")) {
      var cols = new java.util.HashSet<String>();
      while (rs.next()) cols.add(rs.getString("COLUMN_NAME"));
      return cols;
    }
  }

  @Test
  void usersHasAuthColumnsAndDropsGithubId() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    var cols = columns("users");
    assertTrue(cols.contains("email"), "users.email 필요");
    assertTrue(cols.contains("nickname"), "users.nickname 필요");
    assertTrue(cols.contains("role"), "users.role 필요");
    assertTrue(cols.contains("onboarding_status"), "users.onboarding_status 필요");
    assertFalse(cols.contains("github_id"), "users.github_id 제거(신원 이관)");
  }
```

- [ ] **Step 2: 테스트 실패 확인**

먼저 깨끗한 DB로 재생성(이전 마이그레이션이 적용된 상태와 무관하게 신규 마이그레이션 검증):
Run: `docker compose down -v && docker compose up -d`
그다음: `./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.usersHasAuthColumnsAndDropsGithubId"`
Expected: FAIL — `users.email 필요` (아직 컬럼 없음). github_id는 아직 존재해 assertFalse도 실패.

- [ ] **Step 3: 마이그레이션 작성** — `V202606171001__users_auth_extension.sql`:

```sql
-- 슬라이스 #1: W1 users 골격을 인증/온보딩 도메인으로 확장한다 (02_ERD §1).
-- GitHub 신원은 user_oauth_identities로 이관하므로 users.github_id는 제거한다.
ALTER TABLE users
  ADD COLUMN email             VARCHAR(255),
  ADD COLUMN nickname          VARCHAR(100),
  ADD COLUMN role              VARCHAR(20) NOT NULL DEFAULT 'LEARNER',
  ADD COLUMN onboarding_status VARCHAR(20) NOT NULL DEFAULT 'PENDING';

ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email);
ALTER TABLE users ADD CONSTRAINT chk_users_role
  CHECK (role IN ('LEARNER', 'ADMIN'));
ALTER TABLE users ADD CONSTRAINT chk_users_onboarding_status
  CHECK (onboarding_status IN ('PENDING', 'IN_PROGRESS', 'DONE'));

ALTER TABLE users DROP COLUMN github_id;

CREATE INDEX idx_users_onboarding_status ON users(onboarding_status);
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.usersHasAuthColumnsAndDropsGithubId"`
Expected: PASS. (`email`은 nullable이므로 PostgreSQL UNIQUE가 다중 NULL 허용 — R4.)

- [ ] **Step 5: 커밋**

```bash
git add src/main/resources/db/migration/V202606171001__users_auth_extension.sql src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(schema): users 인증 컬럼 확장 + github_id 이관"
```

---

### Task 2: user_oauth_identities 테이블

OAuth provider 신원·암호화 토큰을 저장한다. `(provider, provider_user_id)` UNIQUE로 로그인 조회(02_ERD §인덱스).

**Files:**
- Create: `src/main/resources/db/migration/V202606171002__user_oauth_identities.sql`
- Modify(test): `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`

**Interfaces:**
- Consumes: `users(id)`, `set_updated_at()`.
- Produces: `user_oauth_identities(id, user_id, provider, provider_user_id, access_token_encrypted, refresh_token_encrypted, scope, linked_at, created_at, updated_at)`, UNIQUE `(provider, provider_user_id)`.

- [ ] **Step 1: 실패하는 테스트 작성** — `FlywayMigrationTest.java`에 추가:

```java
  @Test
  void oauthIdentitiesTableExists() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection();
        var rs = c.getMetaData().getTables(null, "public", "user_oauth_identities", new String[] {"TABLE"})) {
      assertTrue(rs.next(), "user_oauth_identities 테이블 필요");
    }
  }
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.oauthIdentitiesTableExists"`
Expected: FAIL — `user_oauth_identities 테이블 필요`.

- [ ] **Step 3: 마이그레이션 작성** — `V202606171002__user_oauth_identities.sql`:

```sql
-- OAuth provider 신원 + 암호화된 provider 토큰. 로그인 조회는 (provider, provider_user_id).
CREATE TABLE user_oauth_identities (
  id                      BIGSERIAL PRIMARY KEY,
  user_id                 BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider                VARCHAR(20) NOT NULL,
  provider_user_id        VARCHAR(255) NOT NULL,
  access_token_encrypted  TEXT,
  refresh_token_encrypted TEXT,
  scope                   VARCHAR(255),
  linked_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_oauth_provider CHECK (provider IN ('GITHUB', 'GOOGLE', 'KAKAO'))
);
CREATE UNIQUE INDEX uq_oauth_provider_user ON user_oauth_identities(provider, provider_user_id);
CREATE INDEX idx_oauth_user ON user_oauth_identities(user_id);
CREATE TRIGGER user_oauth_identities_set_updated_at BEFORE UPDATE ON user_oauth_identities
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.oauthIdentitiesTableExists"`
Expected: PASS.

- [ ] **Step 5: 커밋**

```bash
git add src/main/resources/db/migration/V202606171002__user_oauth_identities.sql src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(schema): user_oauth_identities 테이블"
```

---

### Task 3: user_profiles 테이블

프로필(아바타·bio·학습목표·트랙·경력). `learning_goal`/`target_track`은 온보딩 #2에서 채우므로 nullable.

**Files:**
- Create: `src/main/resources/db/migration/V202606171003__user_profiles.sql`
- Modify(test): `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`

**Interfaces:**
- Consumes: `users(id)`, `set_updated_at()`.
- Produces: `user_profiles(user_id PK, avatar, bio, learning_goal, target_track, experience_years, created_at, updated_at)`.

- [ ] **Step 1: 실패하는 테스트 작성** — `FlywayMigrationTest.java`에 추가:

```java
  @Test
  void userProfilesTableExists() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection();
        var rs = c.getMetaData().getTables(null, "public", "user_profiles", new String[] {"TABLE"})) {
      assertTrue(rs.next(), "user_profiles 테이블 필요");
    }
  }
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.userProfilesTableExists"`
Expected: FAIL — `user_profiles 테이블 필요`.

- [ ] **Step 3: 마이그레이션 작성** — `V202606171003__user_profiles.sql`:

```sql
-- 사용자 프로필. learning_goal/target_track은 온보딩(#2)에서 채우므로 nullable.
CREATE TABLE user_profiles (
  user_id          BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  avatar           VARCHAR(512),
  bio              TEXT,
  learning_goal    VARCHAR(20),
  target_track     VARCHAR(20),
  experience_years INT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_learning_goal CHECK (
    learning_goal IS NULL OR learning_goal IN ('JOB', 'CAREER_CHANGE', 'UPSKILL', 'SIDE_PROJECT')),
  CONSTRAINT chk_target_track CHECK (
    target_track IS NULL OR target_track IN ('BACKEND_SPRING', 'FRONTEND_REACT', 'MOBILE_FLUTTER', 'DEVOPS', 'FULLSTACK'))
);
CREATE TRIGGER user_profiles_set_updated_at BEFORE UPDATE ON user_profiles
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.userProfilesTableExists"`
Expected: PASS.

- [ ] **Step 5: 커밋**

```bash
git add src/main/resources/db/migration/V202606171003__user_profiles.sql src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(schema): user_profiles 테이블"
```

---

### Task 4: outbox 테이블 (Transactional Outbox)

도메인 트랜잭션과 동일 커밋으로 이벤트를 기록하고 릴레이가 Kafka로 발행한다(릴레이/소비자 코드는 platform-svc 플랜).

**Files:**
- Create: `src/main/resources/db/migration/V202606171004__outbox.sql`
- Modify(test): `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`

**Interfaces:**
- Consumes: 없음(독립 테이블).
- Produces: `outbox(id, aggregate_type, aggregate_id, event_type, payload jsonb, created_at, published_at nullable)`, 미발행 부분 인덱스 `WHERE published_at IS NULL`.

- [ ] **Step 1: 실패하는 테스트 작성** — `FlywayMigrationTest.java`에 추가:

```java
  @Test
  void outboxTableExists() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection();
        var rs = c.getMetaData().getTables(null, "public", "outbox", new String[] {"TABLE"})) {
      assertTrue(rs.next(), "outbox 테이블 필요");
    }
  }
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.outboxTableExists"`
Expected: FAIL — `outbox 테이블 필요`.

- [ ] **Step 3: 마이그레이션 작성** — `V202606171004__outbox.sql`:

```sql
-- Transactional Outbox: 도메인 트랜잭션과 동일 커밋으로 이벤트 기록 → 릴레이가 Kafka로 발행.
CREATE TABLE outbox (
  id             BIGSERIAL PRIMARY KEY,
  aggregate_type VARCHAR(100) NOT NULL,
  aggregate_id   VARCHAR(100) NOT NULL,
  event_type     VARCHAR(100) NOT NULL,
  payload        JSONB NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  published_at   TIMESTAMPTZ
);
CREATE INDEX idx_outbox_unpublished ON outbox(created_at) WHERE published_at IS NULL;
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `./gradlew test --tests "ai.devpath.shared.db.FlywayMigrationTest.outboxTableExists"`
Expected: PASS.

- [ ] **Step 5: 커밋**

```bash
git add src/main/resources/db/migration/V202606171004__outbox.sql src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(schema): transactional outbox 테이블"
```

---

### Task 5: UserRegisteredEvent record

가입(최초 OAuth 연동) 완료 이벤트. platform-svc가 발행하고 notification이 구독한다. 기존 `LearningPathGeneratedEvent` 패턴을 따른다.

**Files:**
- Create: `src/main/java/ai/devpath/shared/event/UserRegisteredEvent.java`
- Create(test): `src/test/java/ai/devpath/shared/event/UserRegisteredEventTest.java`

**Interfaces:**
- Consumes: `DomainEvent`(eventId/occurredAt/eventType).
- Produces: `UserRegisteredEvent(UUID eventId, Instant occurredAt, long userId, String provider, String email)`, 상수 `EVENT_TYPE = "user.user.registered"`. (platform-svc가 이 record를 직렬화해 outbox.payload에 기록·발행.)

- [ ] **Step 1: 실패하는 테스트 작성** — `UserRegisteredEventTest.java`:

```java
package ai.devpath.shared.event;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class UserRegisteredEventTest {

	@Test
	void eventTypeIsStable() {
		var event = new UserRegisteredEvent(UUID.randomUUID(), Instant.now(), 1L, "GITHUB", "u@example.com");
		assertEquals("user.user.registered", event.eventType());
	}

	@Test
	void emailMayBeNull() {
		var event = new UserRegisteredEvent(UUID.randomUUID(), Instant.now(), 1L, "GITHUB", null);
		assertEquals("user.user.registered", event.eventType());
	}
}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `./gradlew test --tests "ai.devpath.shared.event.UserRegisteredEventTest"`
Expected: FAIL — 컴파일 에러(`UserRegisteredEvent` 클래스 없음).

- [ ] **Step 3: record 작성** — `UserRegisteredEvent.java`:

```java
package ai.devpath.shared.event;

import java.time.Instant;
import java.util.UUID;

/**
 * 사용자 가입(최초 OAuth 연동) 완료 이벤트.
 * platform-svc가 발행하고 notification 등이 구독한다.
 * email은 provider가 미반환할 수 있어 nullable이다 (설계서 R4).
 */
public record UserRegisteredEvent(
		UUID eventId,
		Instant occurredAt,
		long userId,
		String provider,
		String email
) implements DomainEvent {

	public static final String EVENT_TYPE = "user.user.registered";

	@Override
	public String eventType() {
		return EVENT_TYPE;
	}
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `./gradlew test --tests "ai.devpath.shared.event.UserRegisteredEventTest"`
Expected: PASS.

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/shared/event/UserRegisteredEvent.java src/test/java/ai/devpath/shared/event/UserRegisteredEventTest.java
git commit -m "feat(event): UserRegisteredEvent 추가"
```

---

### Task 6: 전체 검증 + develop PR

**Files:** 없음(검증·통합).

- [ ] **Step 1: 전체 빌드·테스트** — 깨끗한 DB에서 전체 마이그레이션·테스트 통과 확인.

Run: `docker compose down -v && docker compose up -d`
그다음: `./gradlew clean build`
Expected: PASS — `FlywayMigrationTest`(set_updated_at·users·dormant + 신규 users 컬럼·oauth·profiles·outbox), `LearningPathGeneratedEventTest`, `UserRegisteredEventTest` 모두 통과.

- [ ] **Step 2: 푸시 + PR(작업 브랜치 → develop)**

```bash
git push -u origin feat/oauth-schema
gh pr create --base develop --head feat/oauth-schema \
  --title "feat: MD1 슬라이스 #1 인증 스키마 + UserRegisteredEvent" \
  --body "users 확장(github_id 이관)·user_oauth_identities·user_profiles·outbox + UserRegisteredEvent. 설계서: documents/docs/superpowers/specs/2026-06-17-md1-slice1-oauth-design.md"
```

- [ ] **Step 3: CI 녹색 확인 후 머지(merge commit)**

Run: `gh pr checks --watch`
Expected: 모든 체크 통과. 통과 시 머지: `gh pr merge --merge`. (실패 시 머지 금지 — 로그 분석 후 수정.)

- [ ] **Step 4: 후속 의존성 메모** — develop 머지 후 shared가 GitHub Packages로 재배포되어야 platform-svc가 `UserRegisteredEvent`를 소비할 수 있다(이미지 파이프라인/CI). platform-svc 플랜은 이 머지·배포 이후 작성·실행한다.

---

## Self-Review

**1. Spec coverage (설계서 §3.1 대조):**
- users 확장(email UK·nickname·role·onboarding_status) + github_id 제거 → Task 1 ✓
- user_oauth_identities(provider enum·provider_user_id·*_encrypted·scope, `(provider,provider_user_id)` UNIQUE) → Task 2 ✓
- user_profiles(avatar·bio·learning_goal·target_track·experience_years, nullable) → Task 3 ✓
- outbox 테이블(payload jsonb·published_at 부분 인덱스) → Task 4 ✓
- UserRegisteredEvent(`user.user.registered`, DomainEvent 규약) → Task 5 ✓
- user_learning_prefs 연기(범위 외) → 미포함 ✓(설계서 §6)
- Flyway 마이그레이션 테스트 → 기존 패턴 확장(Testcontainers 아님, 설계서 §3.1 정정) ✓

**2. Placeholder scan:** TBD/TODO/"적절히 처리" 없음. 모든 SQL·Java·테스트 코드 전문 포함. ✓

**3. Type consistency:** `UserRegisteredEvent(UUID, Instant, long, String, String)` — Task 5 정의와 Interfaces 블록 일치. `set_updated_at` 함수명·`columns()` 헬퍼명 일관. provider/role/track enum 값 Global Constraints와 SQL CHECK 일치. ✓

## Execution Handoff

Plan complete and saved to `documents/docs/superpowers/plans/2026-06-17-md1-slice1-shared-schema.md`.
