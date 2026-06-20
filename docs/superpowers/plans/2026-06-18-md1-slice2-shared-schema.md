# 슬라이스 #2 빌드 A — devpath-shared 진단 스키마 + 이벤트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** devpath-shared에 진단(diagnostic) 4테이블 Flyway 마이그레이션과 `AssessmentCompletedEvent`를 추가하고, develop→main 릴리스(publish)로 다운스트림 서비스가 소비할 수 있게 한다.

**Architecture:** 슬라이스 #1 shared 빌드(V202606171001~1005 + UserRegisteredEvent) 패턴을 그대로 따른다. enum은 VARCHAR + CHECK 제약, PK는 BIGSERIAL, FK는 BIGINT, 타임스탬프는 TIMESTAMPTZ + `set_updated_at()` 트리거(이미 존재), JSON은 JSONB, FLOAT은 DOUBLE PRECISION. 이벤트는 `record` + `DomainEvent` 구현 + `EVENT_TYPE` 상수.

**Tech Stack:** Java 21 · Gradle (Kotlin DSL, `java-library`) · Flyway 11.8.2 · PostgreSQL 17 · JUnit 5 · `maven-publish`(GitHub Packages).

## Global Constraints

- 레포 절대조건: 추측 금지 · **테스트 우선(실패 테스트 먼저)** · 문제 시 코드 분석. (devpath-shared/CLAUDE.md)
- 브랜치 전략: `develop`에서 작업 브랜치 분기 → `develop` PR. main 직접 금지(릴리스 PR만). 머지 전 CI 녹색. merge commit.
- 이벤트 규칙(CLAUDE.md): `ai.devpath.shared.event`에 `record`로 정의, `DomainEvent` 구현. `eventType`은 `<도메인>.<엔티티>.<동작>` 소문자 점표기. 하위호환 깨는 필드 변경 금지(새 필드는 nullable/기본값). **스키마 변경 시 직렬화/계약 테스트 먼저 작성.**
- 마이그레이션 파일명: `V<YYYYMMDD><4자리seq>__<설명>.sql`. 슬라이스 #2는 `V20260618xxxx`. **기존 V202606171005까지 적용된 DB에 추가**되므로 번호는 그보다 뒤(권장 `V202606181001`~`1004`).
- enum 컬럼은 네이티브 ENUM 금지, **VARCHAR(20) + CHECK 제약**(슬라이스 #1 규약). difficulty/score는 **DOUBLE PRECISION**, JSON은 **JSONB**.
- track enum 값(설계서 §11): `BACKEND_SPRING, FRONTEND_REACT, MOBILE_FLUTTER, DEVOPS, FULLSTACK` (user_profiles.target_track 재사용).
- 이벤트 토픽/타입: **`learning.assessment.completed`** (설계서 §7, 문서26 정합).
- 테스트용 Postgres: 로컬은 `docker compose up -d`(devpath-shared/CLAUDE.md), CI는 postgres service container. `FlywayMigrationTest`는 `DB_URL/DB_USER/DB_PASSWORD`(기본 `jdbc:postgresql://localhost:5432/devpath`/`devpath`/`localdev`)로 연결.

---

## File Structure

- Create: `src/main/resources/db/migration/V202606181001__question_bank.sql` — 진단 문항 뱅크
- Create: `src/main/resources/db/migration/V202606181002__assessments.sql` — 진단 세션
- Create: `src/main/resources/db/migration/V202606181003__assessment_items.sql` — 출제·응답 항목
- Create: `src/main/resources/db/migration/V202606181004__assessment_results.sql` — 진단 결과
- Modify: `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java` — 4테이블 존재 검증 추가
- Create: `src/main/java/ai/devpath/shared/event/AssessmentCompletedEvent.java` — 진단 완료 이벤트
- Create: `src/test/java/ai/devpath/shared/event/AssessmentCompletedEventTest.java` — 이벤트 계약 테스트

> ERD §3에 없으나 본 빌드가 추가하는 컬럼(레포 감사 컨벤션 정합): `question_bank.created_at/updated_at`, `assessment_results.created_at`. assessments는 ERD대로 started_at/completed_at만(updated_at 없음 → 트리거 없음).

---

## Task 1: 진단 부모 테이블 마이그레이션 (question_bank, assessments)

**Files:**
- Create: `src/main/resources/db/migration/V202606181001__question_bank.sql`
- Create: `src/main/resources/db/migration/V202606181002__assessments.sql`
- Modify: `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java` (테스트 메서드 추가)

**Interfaces:**
- Consumes: 기존 `users(id BIGINT)` 테이블, `set_updated_at()` 함수(V202606150900 init_common).
- Produces: 테이블 `question_bank(id BIGSERIAL PK)`, `assessments(id BIGSERIAL PK, user_id BIGINT NULL FK→users)`. Task 3·5가 FK/소비.

- [ ] **Step 1: question_bank 존재 검증 실패 테스트 추가**

`FlywayMigrationTest.java`의 마지막 테스트(`notificationsTableExists`) 뒤, 클래스 닫는 `}` 앞에 추가:

```java
  @Test
  void questionBankTableExists() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection();
        var rs = c.getMetaData().getTables(null, "public", "question_bank", new String[] {"TABLE"})) {
      assertTrue(rs.next(), "question_bank 테이블 필요");
    }
  }

  @Test
  void assessmentsTableExists() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection();
        var rs = c.getMetaData().getTables(null, "public", "assessments", new String[] {"TABLE"})) {
      assertTrue(rs.next(), "assessments 테이블 필요");
    }
  }
```

- [ ] **Step 2: 테스트 실패 확인 (Postgres 필요)**

```bash
docker compose up -d        # 로컬 postgres(5432) 기동 (이미 떠 있으면 생략)
./gradlew test --tests ai.devpath.shared.db.FlywayMigrationTest
```
Expected: `questionBankTableExists`·`assessmentsTableExists` FAIL (해당 테이블 없음).

- [ ] **Step 3: question_bank 마이그레이션 작성**

`V202606181001__question_bank.sql`:

```sql
-- 슬라이스 #2: 진단 문항 뱅크 (02_ERD §3). Bloom 태깅·난이도·개념 태그.
CREATE TABLE question_bank (
  id            BIGSERIAL PRIMARY KEY,
  track         VARCHAR(20) NOT NULL,
  question_type VARCHAR(20) NOT NULL,
  content       TEXT NOT NULL,
  options       JSONB,
  answer_key    JSONB NOT NULL,
  bloom_level   VARCHAR(20) NOT NULL,
  difficulty    DOUBLE PRECISION NOT NULL,
  concept_tags  JSONB,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_qb_track CHECK (
    track IN ('BACKEND_SPRING', 'FRONTEND_REACT', 'MOBILE_FLUTTER', 'DEVOPS', 'FULLSTACK')),
  CONSTRAINT chk_qb_question_type CHECK (
    question_type IN ('MCQ', 'CODE_READING', 'SHORT_ANSWER')),
  CONSTRAINT chk_qb_bloom_level CHECK (
    bloom_level IN ('REMEMBER', 'UNDERSTAND', 'APPLY', 'ANALYZE', 'EVALUATE', 'CREATE')),
  CONSTRAINT chk_qb_difficulty CHECK (difficulty >= 0.0 AND difficulty <= 1.0)
);
CREATE INDEX idx_question_bank_track_difficulty ON question_bank(track, difficulty);
CREATE TRIGGER question_bank_set_updated_at BEFORE UPDATE ON question_bank
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

- [ ] **Step 4: assessments 마이그레이션 작성**

`V202606181002__assessments.sql`:

```sql
-- 슬라이스 #2: 진단 세션 (02_ERD §3). 비회원은 user_id NULL, claim 시 결합. 시작 난이도 0.3(설계서 §4).
CREATE TABLE assessments (
  id                 BIGSERIAL PRIMARY KEY,
  user_id            BIGINT REFERENCES users(id) ON DELETE CASCADE,
  track              VARCHAR(20) NOT NULL,
  status             VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS',
  current_difficulty DOUBLE PRECISION NOT NULL DEFAULT 0.3,
  bloom_distribution JSONB,
  started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at       TIMESTAMPTZ,
  CONSTRAINT chk_assessments_track CHECK (
    track IN ('BACKEND_SPRING', 'FRONTEND_REACT', 'MOBILE_FLUTTER', 'DEVOPS', 'FULLSTACK')),
  CONSTRAINT chk_assessments_status CHECK (
    status IN ('IN_PROGRESS', 'COMPLETED', 'ABANDONED')),
  CONSTRAINT chk_assessments_difficulty CHECK (
    current_difficulty >= 0.0 AND current_difficulty <= 1.0)
);
CREATE INDEX idx_assessments_user_id ON assessments(user_id);
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
./gradlew test --tests ai.devpath.shared.db.FlywayMigrationTest
```
Expected: `questionBankTableExists`·`assessmentsTableExists` PASS (기존 테스트도 멱등 통과).

- [ ] **Step 6: 커밋**

```bash
git add src/main/resources/db/migration/V202606181001__question_bank.sql \
        src/main/resources/db/migration/V202606181002__assessments.sql \
        src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(db): 진단 부모 테이블 question_bank·assessments 마이그레이션"
```

---

## Task 2: 진단 자식 테이블 마이그레이션 (assessment_items, assessment_results)

**Files:**
- Create: `src/main/resources/db/migration/V202606181003__assessment_items.sql`
- Create: `src/main/resources/db/migration/V202606181004__assessment_results.sql`
- Modify: `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`

**Interfaces:**
- Consumes: Task 1의 `assessments(id)`, `question_bank(id)`.
- Produces: `assessment_items`(FK→assessments, question_bank), `assessment_results`(PK=assessment_id, 1:1).

- [ ] **Step 1: 존재 검증 실패 테스트 추가**

`FlywayMigrationTest.java`에 Task 1 메서드 뒤로 추가:

```java
  @Test
  void assessmentItemsTableExists() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection();
        var rs = c.getMetaData().getTables(null, "public", "assessment_items", new String[] {"TABLE"})) {
      assertTrue(rs.next(), "assessment_items 테이블 필요");
    }
  }

  @Test
  void assessmentResultsTableExists() throws Exception {
    Flyway.configure().dataSource(dataSource())
        .locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection();
        var rs = c.getMetaData().getTables(null, "public", "assessment_results", new String[] {"TABLE"})) {
      assertTrue(rs.next(), "assessment_results 테이블 필요");
    }
  }
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
./gradlew test --tests ai.devpath.shared.db.FlywayMigrationTest
```
Expected: `assessmentItemsTableExists`·`assessmentResultsTableExists` FAIL.

- [ ] **Step 3: assessment_items 마이그레이션 작성**

`V202606181003__assessment_items.sql`:

```sql
-- 슬라이스 #2: 진단 출제·응답 항목 (02_ERD §3). skipped='잘 모르겠어요'(설계서 §4).
CREATE TABLE assessment_items (
  id               BIGSERIAL PRIMARY KEY,
  assessment_id    BIGINT NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
  question_bank_id BIGINT NOT NULL REFERENCES question_bank(id),
  order_num        INT NOT NULL,
  presented_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  answered_at      TIMESTAMPTZ,
  answer           JSONB,
  is_correct       BOOLEAN,
  skipped          BOOLEAN NOT NULL DEFAULT FALSE,
  time_spent_sec   INT,
  CONSTRAINT uq_assessment_items_order UNIQUE (assessment_id, order_num)
);
CREATE INDEX idx_assessment_items_assessment ON assessment_items(assessment_id);
```

- [ ] **Step 4: assessment_results 마이그레이션 작성**

`V202606181004__assessment_results.sql`:

```sql
-- 슬라이스 #2: 진단 결과 (02_ERD §3). assessment와 1:1. diagnosed_level=JUNIOR/MID/SENIOR.
CREATE TABLE assessment_results (
  assessment_id     BIGINT PRIMARY KEY REFERENCES assessments(id) ON DELETE CASCADE,
  diagnosed_level   VARCHAR(20) NOT NULL,
  concept_scores    JSONB,
  strength_concepts JSONB,
  weakness_concepts JSONB,
  confidence_weight DOUBLE PRECISION,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_assessment_results_level CHECK (
    diagnosed_level IN ('JUNIOR', 'MID', 'SENIOR'))
);
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
./gradlew test --tests ai.devpath.shared.db.FlywayMigrationTest
```
Expected: 추가 2테스트 PASS, 전체 FlywayMigrationTest 녹색.

- [ ] **Step 6: 커밋**

```bash
git add src/main/resources/db/migration/V202606181003__assessment_items.sql \
        src/main/resources/db/migration/V202606181004__assessment_results.sql \
        src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(db): 진단 자식 테이블 assessment_items·assessment_results 마이그레이션"
```

---

## Task 3: AssessmentCompletedEvent

**Files:**
- Create: `src/main/java/ai/devpath/shared/event/AssessmentCompletedEvent.java`
- Create: `src/test/java/ai/devpath/shared/event/AssessmentCompletedEventTest.java`

**Interfaces:**
- Consumes: `DomainEvent`(eventId, occurredAt, eventType).
- Produces: `record AssessmentCompletedEvent(UUID eventId, Instant occurredAt, long assessmentId, long userId, String track, String diagnosedLevel, Map<String,Double> conceptScores, Instant completedAt)` + `public static final String EVENT_TYPE = "learning.assessment.completed"`. learning-svc(빌드 B)가 발행, platform(빌드 C)이 소비.

- [ ] **Step 1: 이벤트 계약 실패 테스트 작성**

`AssessmentCompletedEventTest.java`:

```java
package ai.devpath.shared.event;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class AssessmentCompletedEventTest {

  @Test
  void eventTypeIsStable() {
    var event = new AssessmentCompletedEvent(
        UUID.randomUUID(), Instant.now(), 10L, 1L, "BACKEND_SPRING", "MID",
        Map.of("jpa", 0.8, "spring-security", 0.4), Instant.now());
    assertEquals("learning.assessment.completed", event.eventType());
  }

  @Test
  void conceptScoresMayBeNull() {
    var event = new AssessmentCompletedEvent(
        UUID.randomUUID(), Instant.now(), 10L, 1L, "BACKEND_SPRING", "JUNIOR", null, Instant.now());
    assertNull(event.conceptScores());
    assertEquals("learning.assessment.completed", event.eventType());
  }
}
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
./gradlew test --tests ai.devpath.shared.event.AssessmentCompletedEventTest
```
Expected: FAIL — `AssessmentCompletedEvent` 심볼 없음(컴파일 실패).

- [ ] **Step 3: 이벤트 클래스 작성**

`AssessmentCompletedEvent.java`:

```java
package ai.devpath.shared.event;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/**
 * 진단(온보딩 적응형 평가) 완료 이벤트.
 * learning-svc가 발행하고 platform-svc(온보딩 상태 전이)·learning-svc(경로 생성)가 구독한다.
 * conceptScores는 강·약점 집계로, 하위호환 위해 nullable이다.
 */
public record AssessmentCompletedEvent(
		UUID eventId,
		Instant occurredAt,
		long assessmentId,
		long userId,
		String track,
		String diagnosedLevel,
		Map<String, Double> conceptScores,
		Instant completedAt
) implements DomainEvent {

	public static final String EVENT_TYPE = "learning.assessment.completed";

	@Override
	public String eventType() {
		return EVENT_TYPE;
	}
}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
./gradlew test --tests ai.devpath.shared.event.AssessmentCompletedEventTest
```
Expected: PASS (2 tests).

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/shared/event/AssessmentCompletedEvent.java \
        src/test/java/ai/devpath/shared/event/AssessmentCompletedEventTest.java
git commit -m "feat(event): AssessmentCompletedEvent (learning.assessment.completed)"
```

---

## Task 4: 전체 빌드 검증 + develop PR

**Files:** (없음 — 검증·통합)

- [ ] **Step 1: 전체 빌드·테스트 녹색 확인**

```bash
docker compose up -d
./gradlew clean build
```
Expected: BUILD SUCCESSFUL, FlywayMigrationTest(기존+신규)·이벤트 테스트 전부 PASS.

- [ ] **Step 2: develop으로 PR**

작업 브랜치(`feat/slice2-shared-diagnostic-schema` 등, develop에서 분기)를 push 후:

```bash
gh pr create --base develop --title "feat: 슬라이스 #2 진단 스키마 + AssessmentCompletedEvent" --body "<요약>"
```
CI 녹색 확인 후 merge commit으로 머지.

---

## Task 5: develop→main 릴리스 (publish) — ⚠️ 다운스트림 선행 필수

> 빌드 B(learning-svc)가 `AssessmentCompletedEvent`와 새 마이그레이션을 소비하려면 shared가 **main에서 GitHub Packages로 publish**되어야 한다(슬라이스 #1 D-6 교훈: publish.yml은 main push에서만 동작).

- [ ] **Step 1: develop→main 릴리스 PR**

```bash
gh pr create --base main --head develop --title "release: 슬라이스 #2 진단 스키마 + AssessmentCompletedEvent" --body "<요약>"
```

- [ ] **Step 2: 머지 후 publish 확인**

main 머지 → `publish.yml`(GitHub Actions)이 GitHub Packages에 새 jar publish. Actions 녹색 + 패키지 버전 확인.

- [ ] **Step 3: 다운스트림 캐시 갱신 안내**

learning-svc 로컬 빌드 시 shared 캐시 purge 후 `--refresh-dependencies` 필요(슬라이스 #1 교훈).

---

## 검토 반영 보완 (2026-06-18 리뷰 — 구현 시 우선 적용)

### R-A1: 데이터 품질 CHECK 제약 추가
- `assessment_results`: `CONSTRAINT chk_ar_confidence CHECK (confidence_weight IS NULL OR (confidence_weight >= 0.0 AND confidence_weight <= 1.0))`
- `assessment_items`: `CONSTRAINT chk_ai_order CHECK (order_num > 0)`, `CONSTRAINT chk_ai_time CHECK (time_spent_sec IS NULL OR time_spent_sec >= 0)`

Task 2 두 마이그레이션 SQL의 닫는 `)` 앞에 위 CHECK를 각각 추가.

### R-A2: 마이그레이션 테스트 강화(테이블 존재 → 계약 검증)
`getTables`로 존재만 보는 대신, 핵심 제약을 INSERT 시도로 검증한다(실 PG). 예: 잘못된 enum/범위 INSERT가 거부되는지, 1:1 result PK·`uq_assessment_items_order` UNIQUE가 작동하는지, FK가 막는지. `FlywayMigrationTest`(또는 신규 `DiagnosticSchemaTest`)에 추가:

```java
  @Test
  void questionBankRejectsBadEnumAndRange() throws Exception {
    Flyway.configure().dataSource(dataSource()).locations("classpath:db/migration").load().migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      // 잘못된 bloom_level → CHECK 위반
      org.junit.jupiter.api.Assertions.assertThrows(java.sql.SQLException.class, () ->
        st.execute("INSERT INTO question_bank(track,question_type,content,answer_key,bloom_level,difficulty) "
          + "VALUES ('BACKEND_SPRING','MCQ','q','{}','NOPE',0.3)"));
      // difficulty 범위 밖 → CHECK 위반
      org.junit.jupiter.api.Assertions.assertThrows(java.sql.SQLException.class, () ->
        st.execute("INSERT INTO question_bank(track,question_type,content,answer_key,bloom_level,difficulty) "
          + "VALUES ('BACKEND_SPRING','MCQ','q','{}','APPLY',9.9)"));
    }
  }
```
(테스트는 멱등·정리 위해 BAD INSERT만 시도하므로 행을 남기지 않는다. 정상 INSERT/UNIQUE/FK 검증은 별도 메서드로 추가 권장.)

### R-A3: 이벤트 직렬화 계약 테스트
`AssessmentCompletedEventTest`의 `eventType` 검증만으로는 필드명·nullable 호환을 보장하지 못한다. shared 테스트 classpath에 Jackson(JsonMapper)이 있으면 직렬화→역직렬화 라운드트립 + JSON 키명(assessmentId/userId/diagnosedLevel/conceptScores/completedAt) 검증을 추가한다. **shared에 Jackson 의존이 없으면**(현 `UserRegisteredEventTest`가 직렬화 미검증인 점으로 보아 가능) 이 계약은 **B-2 `AssessmentEventPropagationIT`**(JsonMapper로 직렬화→Kafka→소비)와 **C 소비자 IT**(역직렬화)가 실효 검증하므로, A에는 "직렬화 계약은 B-2/C IT가 보증"을 명시하고 별도 의존 추가는 하지 않는다(YAGNI).

### R-A4(선택): guest_claims 멱등 테이블 (B-2 R-B2-4 견고화 채택 시)
B-2 claim 멱등을 DB 테이블로 견고화하려면 빌드 A에 `V202606181005__guest_claims.sql` 추가:

```sql
-- 슬라이스 #2: guest→회원 claim 멱등 매핑(중복 이행 방지).
CREATE TABLE guest_claims (
  guest_id      VARCHAR(64) PRIMARY KEY,
  assessment_id BIGINT NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
  claimed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```
채택 여부는 B-2 R-B2-4 결정에 따른다(Redis SETNX 최소안이면 불요).

---

## Self-Review (작성자 점검 결과)

- **Spec coverage**: 설계서 §2 빌드A(스키마+이벤트), §3 데이터모델 4테이블, §7 이벤트(`learning.assessment.completed`)·main 릴리스 — 전부 Task 1~5로 커버. §3 `skipped` 추가 컬럼 반영(Task 2). track enum(§11) CHECK 제약에 반영.
- **Placeholder scan**: 모든 SQL·Java·테스트 코드 완전 기재(TBD/TODO 없음). Task 4·5의 `<요약>`은 PR 본문 자유 서술 항목(코드 아님).
- **Type consistency**: `AssessmentCompletedEvent` 필드/`EVENT_TYPE`이 Task 3 정의와 Interfaces 블록 일치. 마이그레이션 번호 V202606181001~1004 연속, FK 의존 순서(부모 Task1 → 자식 Task2) 정합.
- **주의**: 마이그레이션 테스트는 실 Postgres 필요(로컬 `docker compose up -d`/CI service container). Windows 로컬에서 compose 미가동 시 테스트 실패는 환경 문제이지 코드 문제 아님 — CI 녹색을 최종 기준으로 한다.
