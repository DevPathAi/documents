# 커뮤니티 콘텐츠 수정·삭제 구현 계획 — 1부: 백엔드

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 커뮤니티 글·질문·답변·댓글에 수정·삭제 API 를 만들고, 그 과정에서 드러난 읽기 경로 구멍 두 개를 닫는다.

**Architecture:** 소프트 삭제를 `status` 값으로 표현하되 **삭제 주체를 상태로 구분한다**(`DELETED`=작성자 · `HIDDEN`=관리자). 권한은 경로로 가른다 — `/community/**` 는 작성자, `/community/admin/**` 는 `SecurityConfig` 가 이미 `ROLE_ADMIN` 을 강제한다. 수정 이력은 `community_reports` 와 같은 다형 대상 패턴(`target_type`+`target_id`)의 단일 리비전 테이블에 쌓는다.

**Tech Stack:** Java 21 · Spring Boot(WebMVC · Data JPA · Security OAuth2 Resource Server) · PostgreSQL · Flyway(중앙 마이그레이션은 `devpath-shared` 소관) · JUnit 5 + MockMvc · Gradle Kotlin DSL

**Spec:** `documents/docs/superpowers/specs/2026-08-20-community-content-edit-delete-design.md`

## Global Constraints

- 상태 어휘는 정확히 이 네 값이다: `PUBLISHED` · `DELETED`(작성자 삭제) · `HIDDEN`(관리자 삭제) · `DRAFT`(미사용). 답변·댓글은 `DRAFT` 를 갖지 않는다.
- 마이그레이션 파일은 **`devpath-shared` 에만** 만든다. `community-svc` 에는 마이그레이션 디렉터리가 없다.
- 마이그레이션 명명은 `V<YYYYMMDDHHNN>__<snake_name>.sql`. 이 계획은 `V202608201001` 과 `V202608201002` 를 쓴다.
- 예외는 **새로 만들지 않는다.** 기존 `ai.devpath.community.post.ForbiddenException`(403) · `NotFoundException`(404) · `ai.devpath.community.report.ConflictException`(409) 을 재사용한다. 렌더링은 shared `ApiExceptionHandler`(스펙 §3.4 envelope)가 한다.
- 인증 주체는 `CommunityController.uid(Jwt)` = `Long.parseLong(jwt.getSubject())` 로 얻는다.
- 테스트는 `@SpringBootTest @AutoConfigureMockMvc @ActiveProfiles("test")` + `jwt().jwt(j -> j.subject("<id>"))` 패턴을 따른다.
- **테스트 실행 전제**: Postgres 와 Redis 컨테이너가 둘 다 떠 있어야 한다.
  ```bash
  docker run -d --name devpath-pg -e POSTGRES_DB=devpath -e POSTGRES_USER=devpath \
    -e POSTGRES_PASSWORD=localdev -p 5432:5432 pgvector/pgvector:pg16
  docker run -d --name devpath-redis -p 6379:6379 redis:7-alpine
  ```
  community-svc 테스트 DB 는 `devpath_citest` 다(`application-test.yml`). 없으면 만든다:
  `docker exec devpath-pg psql -U devpath -d devpath -c "CREATE DATABASE devpath_citest OWNER devpath"`
- **Gradle 은 `UP-TO-DATE` 로 테스트를 건너뛴다.** 통과를 확인할 때는 실행 건수를 근거로 삼는다 —
  `build/test-results/test/*.xml` 의 `tests=` 합계가 늘었는지 본다.
- ★**각 태스크의 가드는 임시로 지워 red 가 나는지 실제로 돌린다.**★ "테스트가 green" 은 "가드가 동작한다" 의 증거가 아니다. 각 태스크에 그 절차가 단계로 들어 있다.

---

## File Structure

### `devpath-shared`

| 경로 | 책임 |
|---|---|
| `src/main/resources/db/migration/V202608201001__community_content_soft_delete_and_revisions.sql` | (신규) 답변·댓글 `status` 컬럼 + `NOT VALID` CHECK + 리비전 테이블 |
| `src/main/resources/db/migration/V202608201002__validate_community_content_soft_delete.sql` | (신규) CHECK `VALIDATE` 2 건 |
| `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java` | (수정) 위 두 마이그레이션의 결과 상태를 검증하는 테스트 3 개 추가 |

### `devpath-community-svc`

| 경로 | 책임 |
|---|---|
| `build.gradle.kts` · `gradle.properties` | (수정·신규) shared 좌표를 프로퍼티로 뺀다 |
| `src/main/java/ai/devpath/community/post/ContentStatus.java` | (신규) 상태 문자열 상수 한 곳 |
| `src/main/java/ai/devpath/community/post/CommunityAnswer.java` | (수정) `status` 필드 |
| `src/main/java/ai/devpath/community/post/CommunityComment.java` | (수정) `status` 필드 |
| `src/main/java/ai/devpath/community/post/ContentRevision.java` | (신규) 리비전 엔티티 |
| `src/main/java/ai/devpath/community/post/ContentRevisionRepository.java` | (신규) 리비전 조회 |
| `src/main/java/ai/devpath/community/post/ContentRevisionRecorder.java` | (신규) "본문이 실제로 바뀔 때만 직전 본문을 남긴다" 한 곳 |
| `src/main/java/ai/devpath/community/post/PostService.java` | (수정) 상태 필터 · 수정 · 삭제 · 비석 매핑 |
| `src/main/java/ai/devpath/community/post/CommentService.java` | (수정) 부모 상태 확인 · 수정 · 삭제 · 비석 매핑 |
| `src/main/java/ai/devpath/community/post/AnswerService.java` | (수정) 수정 · 삭제 · 수용 답변 409 |
| `src/main/java/ai/devpath/community/post/QuestionService.java` | (수정) 상태 필터 · 답변 비석 매핑 |
| `src/main/java/ai/devpath/community/post/CommunityController.java` | (수정) `PUT`/`DELETE` 6 개 |
| `src/main/java/ai/devpath/community/post/dto/UpdatePostRequest.java` · `UpdateBodyRequest.java` | (신규) 요청 레코드 |
| `src/main/java/ai/devpath/community/post/dto/AnswerView.java` · `CommentView.java` | (수정) `deleted` 필드 |
| `src/main/java/ai/devpath/community/post/dto/RevisionView.java` | (신규) 리비전 응답 |
| `src/main/java/ai/devpath/community/report/ReportService.java` | (수정) 삭제된 대상 신고 차단 |
| `src/main/java/ai/devpath/community/reputation/ReputationEventRepository.java` | (수정) `netBySource` 쿼리 |
| `src/main/java/ai/devpath/community/reputation/ReputationService.java` | (수정) `revokeAllForSource` |
| `src/main/java/ai/devpath/community/post/ContentAdminController.java` | (신규) 관리자 삭제 3 개 + 리비전 조회 |
| `src/main/java/ai/devpath/community/post/ContentAdminService.java` | (신규) `HIDDEN` 전환 · 수용 해제 · 평판 회수 · 색인 갱신 |
| `src/main/java/ai/devpath/community/post/ActivityController.java` | (수정) 삭제된 것 제외 |

**왜 관리자 기능을 `report` 가 아니라 `post` 패키지에 두는가** — 대상이 신고가 아니라 콘텐츠이고, `PostService`·`AnswerService`·`ReputationService` 를 함께 쓴다. `AdminReportController` 는 `/community/admin/reports` 를, 새 `ContentAdminController` 는 `/community/admin/{posts|answers|comments}` 를 맡는다. 경로가 갈리므로 매핑 충돌이 없다.

---

## Task 1: shared 마이그레이션

**Files:**
- Create: `devpath-shared/src/main/resources/db/migration/V202608201001__community_content_soft_delete_and_revisions.sql`
- Create: `devpath-shared/src/main/resources/db/migration/V202608201002__validate_community_content_soft_delete.sql`
- Test: `devpath-shared/src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java` (수정)

**Interfaces:**
- Consumes: 없음(첫 태스크)
- Produces: 테이블 `community_content_revisions` · 컬럼 `community_answers.status` · `community_comments.status` · 제약 `chk_community_answers_status` · `chk_community_comments_status` · `chk_community_revisions_target`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`FlywayMigrationTest.java` 끝의 마지막 `}` 앞에 붙인다. 파일 상단 import 는 이미
`assertThrows`·`assertTrue` 를 갖고 있다.

```java
  /** 답변·댓글 소프트 삭제 상태 컬럼이 존재하고 기본값이 PUBLISHED 여야 한다. */
  @Test
  void communityAnswerAndCommentHaveSoftDeleteStatus() throws Exception {
    migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      try (var rs = st.executeQuery(
          "SELECT column_default, is_nullable FROM information_schema.columns "
              + "WHERE table_name='community_answers' AND column_name='status'")) {
        assertTrue(rs.next(), "community_answers.status 가 존재해야 한다");
        assertTrue(rs.getString(1).contains("PUBLISHED"), "기본값이 PUBLISHED 여야 한다");
        assertEquals("NO", rs.getString(2), "NOT NULL 이어야 한다");
      }
      try (var rs = st.executeQuery(
          "SELECT column_default, is_nullable FROM information_schema.columns "
              + "WHERE table_name='community_comments' AND column_name='status'")) {
        assertTrue(rs.next(), "community_comments.status 가 존재해야 한다");
        assertTrue(rs.getString(1).contains("PUBLISHED"), "기본값이 PUBLISHED 여야 한다");
        assertEquals("NO", rs.getString(2), "NOT NULL 이어야 한다");
      }
    }
  }

  /** 상태 CHECK 가 어휘 밖의 값을 막아야 한다. DRAFT 는 답변·댓글에 없다. */
  @Test
  void communityContentStatusCheckRejectsUnknownValues() throws Exception {
    migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      st.execute("INSERT INTO community_posts(author_id,board_type,title,body_md) "
          + "VALUES (900001,'QNA','상태검증','본문') RETURNING id");
      try (var rs = st.executeQuery(
          "SELECT id FROM community_posts WHERE author_id=900001 ORDER BY id DESC LIMIT 1")) {
        assertTrue(rs.next());
        long postId = rs.getLong(1);
        st.execute("INSERT INTO community_questions(post_id) VALUES (" + postId + ")");
        assertThrows(java.sql.SQLException.class, () -> st.execute(
            "INSERT INTO community_answers(question_id,author_id,body_md,status) "
                + "VALUES (" + postId + ",900002,'답변','DRAFT')"));
        assertThrows(java.sql.SQLException.class, () -> st.execute(
            "INSERT INTO community_comments(post_id,author_id,body_md,status) "
                + "VALUES (" + postId + ",900002,'댓글','GONE')"));
        st.execute("DELETE FROM community_questions WHERE post_id=" + postId);
        st.execute("DELETE FROM community_posts WHERE id=" + postId);
      }
    }
  }

  /** 리비전 테이블과 다형 대상 CHECK 가 있어야 한다. */
  @Test
  void communityContentRevisionsTableExistsWithTargetCheck() throws Exception {
    migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      try (var rs = st.executeQuery(
          "SELECT count(*) FROM information_schema.columns "
              + "WHERE table_name='community_content_revisions'")) {
        assertTrue(rs.next());
        assertEquals(8, rs.getInt(1), "리비전 테이블은 8개 컬럼이어야 한다");
      }
      assertThrows(java.sql.SQLException.class, () -> st.execute(
          "INSERT INTO community_content_revisions(target_type,target_id,body_md,edited_by) "
              + "VALUES ('QUESTION',1,'본문',1)"));
    }
  }
```

파일 상단 import 에 `assertEquals` 가 없다면 추가한다:

```java
import static org.junit.jupiter.api.Assertions.assertEquals;
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd /d/workspace/dpa/devpath-shared
./gradlew test --tests '*FlywayMigrationTest*' -i 2>&1 | tail -40
```

Expected: 3 개 실패. `community_answers.status 가 존재해야 한다` 등.

- [ ] **Step 3: 마이그레이션을 쓴다**

`V202608201001__community_content_soft_delete_and_revisions.sql`:

```sql
-- 답변·댓글에 소프트 삭제 상태를 더한다. community_posts 는 이미
-- chk_community_posts_status 로 DRAFT/PUBLISHED/HIDDEN/DELETED 를 갖고 있으므로
-- 어휘를 맞추되, 초안 개념이 없는 두 테이블에서는 DRAFT 를 뺀다.
--
-- 상태가 삭제 주체를 구분한다: DELETED=작성자가 지움(평판 유지) ·
-- HIDDEN=관리자가 내림(평판 회수). 그래서 "누가 지웠는가" 를 위한 별도 컬럼이 없다.
ALTER TABLE community_answers  ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'PUBLISHED';
ALTER TABLE community_comments ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'PUBLISHED';

-- NOT VALID 로 마이그레이션 락 아래 전체 스캔을 피한다(V202608161007 과 같은 방식).
-- 새 값은 즉시 거부되고, 기존 행 검증은 다음 마이그레이션이 맡는다.
ALTER TABLE community_answers  ADD CONSTRAINT chk_community_answers_status
  CHECK (status IN ('PUBLISHED','HIDDEN','DELETED')) NOT VALID;
ALTER TABLE community_comments ADD CONSTRAINT chk_community_comments_status
  CHECK (status IN ('PUBLISHED','HIDDEN','DELETED')) NOT VALID;

-- 수정 이력. community_reports 와 같은 다형 대상 패턴(target_type + target_id)이다.
-- 질문은 board_type='QNA' 인 게시글이므로 target_type 은 POST 다 —
-- ReportTargetType 과 같은 3값 어휘를 쓴다.
CREATE TABLE community_content_revisions (
  id          BIGSERIAL PRIMARY KEY,
  target_type VARCHAR(16) NOT NULL,
  target_id   BIGINT      NOT NULL,
  -- 글·질문만 제목이 있다(답변·댓글은 NULL). community_posts.title 과 같은 길이다.
  title       VARCHAR(120),
  body_md     TEXT        NOT NULL,
  body_html   TEXT,
  edited_by   BIGINT      NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_community_revisions_target CHECK (target_type IN ('POST','ANSWER','COMMENT'))
);
CREATE INDEX idx_community_revisions_target
  ON community_content_revisions(target_type, target_id, created_at DESC);
```

`V202608201002__validate_community_content_soft_delete.sql`:

```sql
-- 앞 마이그레이션이 NOT VALID 로 남긴 제약의 기존 행 검증을 분리해 끝낸다.
ALTER TABLE community_answers  VALIDATE CONSTRAINT chk_community_answers_status;
ALTER TABLE community_comments VALIDATE CONSTRAINT chk_community_comments_status;
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd /d/workspace/dpa/devpath-shared
./gradlew test --tests '*FlywayMigrationTest*' 2>&1 | tail -10
```

Expected: BUILD SUCCESSFUL. 실행 건수를 근거로 본다:

```bash
grep -o 'tests="[0-9]*"' build/test-results/test/TEST-ai.devpath.shared.db.FlywayMigrationTest.xml
```

Expected: 이전보다 3 증가.

- [ ] **Step 5: 판별력을 실측한다**

`V202608201001` 에서 `CHECK (status IN ('PUBLISHED','HIDDEN','DELETED')) NOT VALID` 두 줄을 잠시 지우고 DB 를 새로 만들어 돌린다.

```bash
docker exec devpath-pg psql -U devpath -d postgres -c "DROP DATABASE IF EXISTS devpath"
docker exec devpath-pg psql -U devpath -d postgres -c "CREATE DATABASE devpath OWNER devpath"
cd /d/workspace/dpa/devpath-shared && ./gradlew test --tests '*FlywayMigrationTest*' 2>&1 | tail -20
```

Expected: `communityContentStatusCheckRejectsUnknownValues` **만** 실패한다.
확인 후 지운 두 줄을 복구하고 DB 를 다시 만들어 green 을 재확인한다.

- [ ] **Step 6: 커밋**

```bash
cd /d/workspace/dpa/devpath-shared
git checkout -b feat/community-content-soft-delete develop
git add src/main/resources/db/migration/V202608201001__community_content_soft_delete_and_revisions.sql \
        src/main/resources/db/migration/V202608201002__validate_community_content_soft_delete.sql \
        src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java
git commit -m "feat(db): 커뮤니티 콘텐츠 소프트 삭제 상태와 수정 이력 테이블을 더한다

답변·댓글에는 status 컬럼이 없었다. community_posts 는 이미
chk_community_posts_status 로 DELETED 를 허용하고 있어 어휘를 맞추되, 초안 개념이
없는 두 테이블에서는 DRAFT 를 뺀다. 상태가 삭제 주체를 구분한다 —
DELETED=작성자(평판 유지) · HIDDEN=관리자(평판 회수).

리비전 테이블은 community_reports 와 같은 다형 대상 패턴을 쓴다. 질문은
board_type='QNA' 인 게시글이므로 target_type 어휘는 POST/ANSWER/COMMENT 3값이다.

판별력 실측: CHECK 두 줄을 지우면 상태 검증 테스트만 red 가 된다."
```

---

## Task 2: 개발용 shared 좌표 발행과 community-svc 핀

★**이 태스크가 없으면 이후 모든 태스크의 테스트가 「column status does not exist」로 죽는다.**★
`community-svc` 의 테스트 스키마는 전적으로 shared jar 의 `classpath:db/migration` 에서 온다
(`flyway.enabled: true` · `ddl-auto: none`).

**왜 SNAPSHOT 을 덮어쓰지 않는가** — `0.0.1-SNAPSHOT` 은 8 개 서비스가 모두 참조한다. 덮어쓰면
그들의 의존성이 한꺼번에 바뀌어 지금 green 인 CI 가 깨질 수 있다. 별도 좌표를 발행하고
community-svc 브랜치만 그것을 가리키면 다른 서비스는 무영향이다.

**Files:**
- Modify(임시, 커밋하지 않음): `devpath-shared/build.gradle.kts:8`
- Create: `devpath-community-svc/gradle.properties`
- Modify: `devpath-community-svc/build.gradle.kts:34`

**Interfaces:**
- Consumes: Task 1 의 마이그레이션
- Produces: Maven 좌표 `ai.devpath:devpath-shared:0.0.1-dev.20260820` · Gradle 프로퍼티 `devpathSharedVersion`

- [ ] **Step 1: shared 를 개발용 좌표로 발행한다**

```bash
cd /d/workspace/dpa/devpath-shared
# version 만 임시로 바꾼다(커밋하지 않는다).
py -c "
import pathlib
p = pathlib.Path('build.gradle.kts')
t = p.read_text(encoding='utf-8', newline='')
assert 'version = \"0.0.1-et9.20260816\"' in t
with open(p,'w',encoding='utf-8',newline='') as f:
    f.write(t.replace('version = \"0.0.1-et9.20260816\"','version = \"0.0.1-dev.20260820\"',1))
print('version 임시 변경')
"
GITHUB_ACTOR=$(gh api user --jq .login) GITHUB_TOKEN=$(gh auth token) \
  ./gradlew publishMavenPublicationToGitHubPackagesRepository 2>&1 | tail -8
```

Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 2: 발행을 확인하고 임시 변경을 되돌린다**

```bash
cd /d/workspace/dpa/devpath-shared
MSYS_NO_PATHCONV=1 gh api orgs/DevPathAi/packages/maven/ai.devpath.devpath-shared/versions \
  --jq '.[].name'
git checkout -- build.gradle.kts
git status --porcelain
```

Expected: 버전 목록에 `0.0.1-dev.20260820` 이 보이고, `git status` 가 비어 있다
(임시 변경이 남지 않았다).

- [ ] **Step 3: community-svc 가 좌표를 프로퍼티로 읽게 한다**

`devpath-community-svc/gradle.properties` (신규):

```properties
# shared 좌표. 기본값은 공용 SNAPSHOT 이고, 아직 SNAPSHOT 에 실리지 않은 마이그레이션을
# 쓰는 동안에만 개발용 좌표를 가리킨다.
#
# 되돌릴 시점: Mission Spine 릴리스가 끝나 shared 가 0.0.1-et9.20260816 으로 게시되면
# 이 값을 그 좌표로 바꾼다(feat/mission-spine-immutable-image 브랜치가 이미 그렇게 한다).
devpathSharedVersion=0.0.1-dev.20260820
```

`devpath-community-svc/build.gradle.kts` — 34 행 근처를 바꾼다.

바꾸기 전:
```kotlin
	implementation("ai.devpath:devpath-shared:0.0.1-SNAPSHOT")
```

바꾼 뒤 (파일 상단 `repositories` 블록 위, `plugins`/`group` 선언 뒤에 값 선언을 둔다):
```kotlin
val devpathSharedVersion =
	providers.gradleProperty("devpathSharedVersion").orElse("0.0.1-SNAPSHOT").get()
```
```kotlin
	implementation("ai.devpath:devpath-shared:$devpathSharedVersion")
```

- [ ] **Step 4: 새 스키마가 실제로 도달했는지 확인한다**

```bash
cd /d/workspace/dpa/devpath-community-svc
docker exec devpath-pg psql -U devpath -d postgres -c "DROP DATABASE IF EXISTS devpath_citest"
docker exec devpath-pg psql -U devpath -d postgres -c "CREATE DATABASE devpath_citest OWNER devpath"
./gradlew test --tests '*CommunityContextTest*' --refresh-dependencies 2>&1 | tail -8
docker exec devpath-pg psql -U devpath -d devpath_citest -c "\d community_answers" | grep status
```

Expected: 테스트 통과, 그리고 마지막 명령이 `status | character varying(16) | not null` 을 낸다.

★`--refresh-dependencies` 를 빼면 Gradle 이 옛 메타데이터를 24 시간 캐시해 새 좌표를 못 본다.★

- [ ] **Step 5: 커밋**

```bash
cd /d/workspace/dpa/devpath-community-svc
git checkout -b feat/content-edit-delete develop
git add gradle.properties build.gradle.kts
git commit -m "build: shared 좌표를 프로퍼티로 빼고 개발용 좌표를 가리킨다

community-svc 테스트 스키마는 전적으로 shared jar 의 classpath:db/migration 에서
온다(ddl-auto: none). 소프트 삭제 마이그레이션이 아직 공용 SNAPSHOT 에 실리지 않아
그대로는 테스트가 「column status does not exist」로 죽는다.

SNAPSHOT 을 덮어쓰지 않는 이유는 8개 서비스가 모두 그것을 참조하기 때문이다. 별도
좌표를 발행하고 이 브랜치만 가리키면 다른 서비스는 영향을 받지 않는다.

되돌릴 시점을 gradle.properties 주석에 적어 둔다."
```

---

## Task 3: 상태 상수와 답변·댓글 엔티티

**Files:**
- Create: `src/main/java/ai/devpath/community/post/ContentStatus.java`
- Modify: `src/main/java/ai/devpath/community/post/CommunityAnswer.java`
- Modify: `src/main/java/ai/devpath/community/post/CommunityComment.java`
- Test: `src/test/java/ai/devpath/community/post/ContentStatusPersistenceTest.java`

**Interfaces:**
- Consumes: Task 2 의 `devpathSharedVersion` 핀
- Produces: `ContentStatus.PUBLISHED` · `.DELETED` · `.HIDDEN`(모두 `String` 상수) · `CommunityAnswer.getStatus()/setStatus(String)` · `CommunityComment.getStatus()/setStatus(String)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/community/post/ContentStatusPersistenceTest.java`:

```java
package ai.devpath.community.post;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class ContentStatusPersistenceTest {

  @Autowired CommunityPostRepository posts;
  @Autowired CommunityQuestionRepository questions;
  @Autowired CommunityAnswerRepository answers;
  @Autowired CommunityCommentRepository comments;

  @Test
  void answerAndCommentPersistStatusAndDefaultToPublished() {
    CommunityPost p = new CommunityPost();
    p.setAuthorId(910001L); p.setBoardType("QNA");
    p.setTitle("상태 저장"); p.setBodyMd("본문"); p.setStatus(ContentStatus.PUBLISHED);
    p = posts.save(p);
    CommunityQuestion q = new CommunityQuestion();
    q.setPostId(p.getId());
    questions.save(q);

    CommunityAnswer a = new CommunityAnswer();
    a.setQuestionId(p.getId()); a.setAuthorId(910002L); a.setBodyMd("답변");
    a = answers.save(a);
    assertThat(a.getStatus()).isEqualTo(ContentStatus.PUBLISHED);

    a.setStatus(ContentStatus.DELETED);
    answers.save(a);
    assertThat(answers.findById(a.getId()).orElseThrow().getStatus())
        .isEqualTo(ContentStatus.DELETED);

    CommunityComment c = new CommunityComment();
    c.setPostId(p.getId()); c.setAuthorId(910002L); c.setBodyMd("댓글");
    c = comments.save(c);
    assertThat(c.getStatus()).isEqualTo(ContentStatus.PUBLISHED);

    c.setStatus(ContentStatus.HIDDEN);
    comments.save(c);
    assertThat(comments.findById(c.getId()).orElseThrow().getStatus())
        .isEqualTo(ContentStatus.HIDDEN);
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd /d/workspace/dpa/devpath-community-svc
./gradlew test --tests '*ContentStatusPersistenceTest*' 2>&1 | tail -20
```

Expected: 컴파일 실패 — `ContentStatus` 심볼을 찾을 수 없고 `getStatus()` 가 없다.

- [ ] **Step 3: 구현한다**

`ContentStatus.java`:

```java
package ai.devpath.community.post;

/**
 * 커뮤니티 콘텐츠 상태. DB CHECK 제약과 값이 일치해야 한다
 * (chk_community_posts_status · chk_community_answers_status · chk_community_comments_status).
 *
 * <p>★상태가 삭제 주체를 구분한다★ — {@link #DELETED} 는 작성자가 지운 것이고 평판을 그대로 둔다.
 * {@link #HIDDEN} 은 관리자가 내린 것이고 그 콘텐츠로 얻은 평판을 회수한다. 그래서 "누가
 * 지웠는가" 를 담는 별도 컬럼이 없다.
 *
 * <p>{@code DRAFT} 는 community_posts CHECK 에만 있고 코드에서 쓰이지 않아 여기 두지 않는다.
 */
public final class ContentStatus {
  public static final String PUBLISHED = "PUBLISHED";
  public static final String DELETED = "DELETED";
  public static final String HIDDEN = "HIDDEN";

  private ContentStatus() {}
}
```

`CommunityAnswer.java` — `updatedAt` 필드 선언 바로 위에 넣는다:

```java
  @Column(nullable = false) private String status = ContentStatus.PUBLISHED;
```

그리고 클래스 끝의 getter/setter 묶음에 넣는다:

```java
  public String getStatus() { return status; }
  public void setStatus(String status) { this.status = status; }
```

`CommunityComment.java` — 같은 방식으로 `updatedAt` 선언 위에 넣는다:

```java
  @Column(nullable = false) private String status = ContentStatus.PUBLISHED;
```

그리고:

```java
  public String getStatus() { return status; }
  public void setStatus(String status) { this.status = status; }
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd /d/workspace/dpa/devpath-community-svc
./gradlew test --tests '*ContentStatusPersistenceTest*' 2>&1 | tail -8
```

Expected: BUILD SUCCESSFUL.

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/community/post/ContentStatus.java \
        src/main/java/ai/devpath/community/post/CommunityAnswer.java \
        src/main/java/ai/devpath/community/post/CommunityComment.java \
        src/test/java/ai/devpath/community/post/ContentStatusPersistenceTest.java
git commit -m "feat(content): 답변·댓글에 상태를 싣고 상태 어휘를 한 곳에 모은다

기존 코드는 \"PUBLISHED\" 문자열 리터럴을 10곳에서 쓴다. 상태값이 셋으로 늘어나므로
ContentStatus 상수로 모은다 — 기존 리터럴을 일괄 치환하지는 않고 새 코드부터 쓴다.

DELETED 와 HIDDEN 이 삭제 주체를 구분한다는 것을 상수 주석에 남긴다."
```

---

## Task 4: 읽기 경로의 구멍 셋을 닫는다

★**이 태스크의 첫 테스트는 지금 코드에서 반드시 red 다.**★ `postDetail` 이 `findById` 만 쓰기
때문에 **삭제된 글도 ID 로 직접 열면 200 을 낸다.** 삭제 API 를 붙이기 전에 이 구멍을 먼저 닫는다.

**Files:**
- Modify: `src/main/java/ai/devpath/community/post/PostService.java`
- Modify: `src/main/java/ai/devpath/community/post/QuestionService.java`
- Modify: `src/main/java/ai/devpath/community/post/CommentService.java`
- Modify: `src/main/java/ai/devpath/community/report/ReportService.java`
- Test: `src/test/java/ai/devpath/community/post/DeletedContentReadPathTest.java`

**Interfaces:**
- Consumes: `ContentStatus`(Task 3)
- Produces: `PostService.postDetail` · `QuestionService.detail` · `CommentService.listComments` 가 비공개 콘텐츠에 `NotFoundException` 을 던진다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/community/post/DeletedContentReadPathTest.java`:

```java
package ai.devpath.community.post;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class DeletedContentReadPathTest {

  @Autowired MockMvc mvc;
  @Autowired CommunityPostRepository posts;

  private long createFreePost(String subject) throws Exception {
    String body = mvc.perform(post("/community/posts")
            .with(jwt().jwt(j -> j.subject(subject)))
            .contentType("application/json")
            .content("{\"boardType\":\"FREE\",\"title\":\"읽기경로\",\"bodyMd\":\"본문\",\"tags\":[]}"))
        .andExpect(status().isCreated())
        .andReturn().getResponse().getContentAsString();
    return com.jayway.jsonpath.JsonPath.parse(body).read("$.id", Long.class);
  }

  private void markDeleted(long postId) {
    CommunityPost p = posts.findById(postId).orElseThrow();
    p.setStatus(ContentStatus.DELETED);
    posts.save(p);
  }

  @Test
  void deletedPostIsNotReadableById() throws Exception {
    long id = createFreePost("920001");
    mvc.perform(get("/community/posts/" + id).with(jwt().jwt(j -> j.subject("920001"))))
        .andExpect(status().isOk());

    markDeleted(id);

    mvc.perform(get("/community/posts/" + id).with(jwt().jwt(j -> j.subject("920001"))))
        .andExpect(status().isNotFound());
  }

  @Test
  void commentsOfDeletedPostAreNotReachable() throws Exception {
    long id = createFreePost("920002");
    mvc.perform(post("/community/posts/" + id + "/comments")
            .with(jwt().jwt(j -> j.subject("920003")))
            .contentType("application/json").content("{\"bodyMd\":\"댓글\"}"))
        .andExpect(status().isCreated());

    markDeleted(id);

    mvc.perform(get("/community/posts/" + id + "/comments")
            .with(jwt().jwt(j -> j.subject("920003"))))
        .andExpect(status().isNotFound());
  }

  @Test
  void deletedPostCannotBeReported() throws Exception {
    long id = createFreePost("920004");
    markDeleted(id);

    mvc.perform(post("/community/reports")
            .with(jwt().jwt(j -> j.subject("920005")))
            .contentType("application/json")
            .content("{\"targetType\":\"POST\",\"targetId\":" + id + ",\"category\":\"SPAM\"}"))
        .andExpect(status().isNotFound());
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd /d/workspace/dpa/devpath-community-svc
./gradlew test --tests '*DeletedContentReadPathTest*' 2>&1 | tail -30
```

Expected: 3 개 모두 실패. `deletedPostIsNotReadableById` 는 `Status expected:<404> but was:<200>` —
**이것이 지금 있는 구멍의 증거다.**

- [ ] **Step 3: 구현한다**

`PostService.java` — `postDetail` 의 첫 줄을 바꾼다.

바꾸기 전:
```java
    CommunityPost p = posts.findById(postId)
        .orElseThrow(() -> new NotFoundException("post " + postId));
```

바꾼 뒤:
```java
    CommunityPost p = posts.findById(postId)
        .filter(found -> ContentStatus.PUBLISHED.equals(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("post " + postId));
```

`QuestionService.java` — `detail` 의 첫 조회도 같은 방식으로 바꾼다.

바꾸기 전:
```java
    CommunityPost p = posts.findById(postId)
        .orElseThrow(() -> new NotFoundException("question " + postId));
```

바꾼 뒤:
```java
    CommunityPost p = posts.findById(postId)
        .filter(found -> ContentStatus.PUBLISHED.equals(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("question " + postId));
```

`CommentService.java` — `listComments` 앞에 부모 확인을 넣는다.

바꾸기 전:
```java
  @Transactional(readOnly = true)
  public List<CommentView> listComments(long postId) {
    return comments.findByPostIdOrderByCreatedAtAsc(postId).stream()
```

바꾼 뒤:
```java
  @Transactional(readOnly = true)
  public List<CommentView> listComments(long postId) {
    // 부모가 비공개면 자식으로 우회 조회할 수 없어야 한다.
    posts.findById(postId)
        .filter(p -> ContentStatus.PUBLISHED.equals(p.getStatus()))
        .orElseThrow(() -> new NotFoundException("post " + postId));
    return comments.findByPostIdOrderByCreatedAtAsc(postId).stream()
```

`ReportService.java` — `targetAuthorId` 의 세 갈래에 상태 필터를 넣는다.

바꾸기 전:
```java
      case POST -> posts.findById(targetId)
          .orElseThrow(() -> new NotFoundException("신고 대상 글을 찾을 수 없습니다."))
          .getAuthorId();
      case ANSWER -> answers.findById(targetId)
          .orElseThrow(() -> new NotFoundException("신고 대상 답변을 찾을 수 없습니다."))
          .getAuthorId();
      case COMMENT -> comments.findById(targetId)
          .orElseThrow(() -> new NotFoundException("신고 대상 댓글을 찾을 수 없습니다."))
          .getAuthorId();
```

바꾼 뒤:
```java
      case POST -> posts.findById(targetId)
          .filter(p -> ai.devpath.community.post.ContentStatus.PUBLISHED.equals(p.getStatus()))
          .orElseThrow(() -> new NotFoundException("신고 대상 글을 찾을 수 없습니다."))
          .getAuthorId();
      case ANSWER -> answers.findById(targetId)
          .filter(a -> ai.devpath.community.post.ContentStatus.PUBLISHED.equals(a.getStatus()))
          .orElseThrow(() -> new NotFoundException("신고 대상 답변을 찾을 수 없습니다."))
          .getAuthorId();
      case COMMENT -> comments.findById(targetId)
          .filter(c -> ai.devpath.community.post.ContentStatus.PUBLISHED.equals(c.getStatus()))
          .orElseThrow(() -> new NotFoundException("신고 대상 댓글을 찾을 수 없습니다."))
          .getAuthorId();
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd /d/workspace/dpa/devpath-community-svc
./gradlew test --tests '*DeletedContentReadPathTest*' 2>&1 | tail -8
```

Expected: BUILD SUCCESSFUL, 3 개 통과.

- [ ] **Step 5: 회귀가 없는지 전체를 돌린다**

```bash
./gradlew test 2>&1 | tail -15
```

Expected: BUILD SUCCESSFUL. 기존 테스트가 삭제되지 않은 글만 다루므로 영향이 없어야 한다.

- [ ] **Step 6: 커밋**

```bash
git add src/main/java/ai/devpath/community/post/PostService.java \
        src/main/java/ai/devpath/community/post/QuestionService.java \
        src/main/java/ai/devpath/community/post/CommentService.java \
        src/main/java/ai/devpath/community/report/ReportService.java \
        src/test/java/ai/devpath/community/post/DeletedContentReadPathTest.java
git commit -m "fix(content): 비공개 콘텐츠의 읽기·신고 우회 경로를 막는다

목록 쿼리 3종은 status='PUBLISHED' 를 걸었는데 postDetail 과 questionDetail 은
findById 만 써서 ID 로 직접 열면 그대로 읽혔다. 신고도 대상 상태를 보지 않았다.
삭제 API 를 붙이는 순간 이것들이 결함이 되므로 먼저 닫는다.

자식 댓글 목록도 부모 상태를 확인한다 — 부모가 404 인데 자식으로 우회해 내용을
읽을 수 있으면 삭제가 삭제가 아니다.

구현 전 실측: deletedPostIsNotReadableById 가 200 을 반환해 red 였다."
```

---

## Task 5: 리비전 인프라

**Files:**
- Create: `src/main/java/ai/devpath/community/post/ContentRevision.java`
- Create: `src/main/java/ai/devpath/community/post/ContentRevisionRepository.java`
- Create: `src/main/java/ai/devpath/community/post/ContentRevisionRecorder.java`
- Test: `src/test/java/ai/devpath/community/post/ContentRevisionRecorderTest.java`

**Interfaces:**
- Consumes: Task 1 의 `community_content_revisions` 테이블
- Produces: `ContentRevisionRecorder.record(String targetType, long targetId, String title, String bodyMd, String bodyHtml, long editedBy)` → `boolean`(기록했으면 true) · `ContentRevisionRepository.findByTargetTypeAndTargetIdOrderByCreatedAtDesc(String, Long)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/community/post/ContentRevisionRecorderTest.java`:

```java
package ai.devpath.community.post;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class ContentRevisionRecorderTest {

  @Autowired ContentRevisionRecorder recorder;
  @Autowired ContentRevisionRepository revisions;

  @Test
  void recordsPreviousBodyOnlyWhenContentActuallyChanges() {
    long targetId = 930001L;

    assertThat(recorder.record("POST", targetId, "제목1", "본문1", "<p>본문1</p>", 1L)).isTrue();
    assertThat(recorder.record("POST", targetId, "제목2", "본문2", "<p>본문2</p>", 1L)).isTrue();

    assertThat(revisions.findByTargetTypeAndTargetIdOrderByCreatedAtDesc("POST", targetId))
        .hasSize(2);
  }

  @Test
  void doesNotRecordWhenNothingChanged() {
    long targetId = 930002L;

    assertThat(recorder.record("POST", targetId, "같은제목", "같은본문", null, 1L)).isTrue();
    // 직전에 기록한 것과 제목·본문이 같으면 기록하지 않는다.
    assertThat(recorder.record("POST", targetId, "같은제목", "같은본문", null, 1L)).isFalse();

    assertThat(revisions.findByTargetTypeAndTargetIdOrderByCreatedAtDesc("POST", targetId))
        .hasSize(1);
  }

  @Test
  void answerAndCommentRevisionsHaveNoTitle() {
    assertThat(recorder.record("ANSWER", 930003L, null, "답변본문", null, 2L)).isTrue();
    assertThat(revisions.findByTargetTypeAndTargetIdOrderByCreatedAtDesc("ANSWER", 930003L))
        .singleElement()
        .satisfies(r -> {
          assertThat(r.getTitle()).isNull();
          assertThat(r.getBodyMd()).isEqualTo("답변본문");
          assertThat(r.getEditedBy()).isEqualTo(2L);
        });
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd /d/workspace/dpa/devpath-community-svc
./gradlew test --tests '*ContentRevisionRecorderTest*' 2>&1 | tail -20
```

Expected: 컴파일 실패 — `ContentRevisionRecorder` 를 찾을 수 없다.

- [ ] **Step 3: 구현한다**

`ContentRevision.java`:

```java
package ai.devpath.community.post;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

/**
 * 콘텐츠 수정 이력. 현재 행이 최신 본문을 들고 이 테이블이 과거를 쌓는다.
 * 최초 작성분은 여기 없고, N 번 수정하면 N 개가 생긴다.
 *
 * <p>community_reports 와 같은 다형 대상 패턴이다 — target_type 은 POST/ANSWER/COMMENT 이고
 * 질문은 board_type='QNA' 인 게시글이므로 POST 로 기록된다.
 */
@Entity
@Table(name = "community_content_revisions")
public class ContentRevision {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
  @Column(name = "target_type", nullable = false) private String targetType;
  @Column(name = "target_id", nullable = false) private Long targetId;
  private String title;
  @Column(name = "body_md", nullable = false) private String bodyMd;
  @Column(name = "body_html") private String bodyHtml;
  @Column(name = "edited_by", nullable = false) private Long editedBy;
  @Column(name = "created_at", insertable = false, updatable = false) private Instant createdAt;

  public Long getId() { return id; }
  public String getTargetType() { return targetType; }
  public void setTargetType(String targetType) { this.targetType = targetType; }
  public Long getTargetId() { return targetId; }
  public void setTargetId(Long targetId) { this.targetId = targetId; }
  public String getTitle() { return title; }
  public void setTitle(String title) { this.title = title; }
  public String getBodyMd() { return bodyMd; }
  public void setBodyMd(String bodyMd) { this.bodyMd = bodyMd; }
  public String getBodyHtml() { return bodyHtml; }
  public void setBodyHtml(String bodyHtml) { this.bodyHtml = bodyHtml; }
  public Long getEditedBy() { return editedBy; }
  public void setEditedBy(Long editedBy) { this.editedBy = editedBy; }
  public Instant getCreatedAt() { return createdAt; }
}
```

`ContentRevisionRepository.java`:

```java
package ai.devpath.community.post;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ContentRevisionRepository extends JpaRepository<ContentRevision, Long> {
  List<ContentRevision> findByTargetTypeAndTargetIdOrderByCreatedAtDesc(
      String targetType, Long targetId);
}
```

`ContentRevisionRecorder.java`:

```java
package ai.devpath.community.post;

import java.util.List;
import java.util.Objects;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 수정 직전 본문을 이력에 남긴다.
 *
 * <p>★같은 내용으로 저장을 눌러도 이력이 늘지 않는다★ — 직전 리비전과 제목·본문이 모두 같으면
 * 기록하지 않는다. 그러지 않으면 "저장" 을 반복하는 것만으로 이력이 부풀어 신고 처리 때
 * 실제 변경을 찾기 어려워진다.
 *
 * <p>{@code PostIndexEventPublisher} 와 같이 자체 {@code @Transactional} 로 호출자의 트랜잭션에
 * 합류한다(REQUIRED 전파).
 */
@Component
public class ContentRevisionRecorder {

  private final ContentRevisionRepository revisions;

  public ContentRevisionRecorder(ContentRevisionRepository revisions) {
    this.revisions = revisions;
  }

  /** @return 실제로 기록했으면 true, 직전과 같아 건너뛰었으면 false. */
  @Transactional
  public boolean record(String targetType, long targetId, String title, String bodyMd,
      String bodyHtml, long editedBy) {
    List<ContentRevision> prior =
        revisions.findByTargetTypeAndTargetIdOrderByCreatedAtDesc(targetType, targetId);
    if (!prior.isEmpty()) {
      ContentRevision last = prior.get(0);
      if (Objects.equals(last.getTitle(), title) && Objects.equals(last.getBodyMd(), bodyMd)) {
        return false;
      }
    }
    ContentRevision r = new ContentRevision();
    r.setTargetType(targetType);
    r.setTargetId(targetId);
    r.setTitle(title);
    r.setBodyMd(bodyMd);
    r.setBodyHtml(bodyHtml);
    r.setEditedBy(editedBy);
    revisions.save(r);
    return true;
  }
}
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd /d/workspace/dpa/devpath-community-svc
./gradlew test --tests '*ContentRevisionRecorderTest*' 2>&1 | tail -8
```

Expected: BUILD SUCCESSFUL, 3 개 통과.

- [ ] **Step 5: 판별력을 실측한다**

`ContentRevisionRecorder.record` 의 중복 검사 블록(`if (!prior.isEmpty()) { ... }`)을 잠시 지우고 돌린다.

```bash
./gradlew test --tests '*ContentRevisionRecorderTest*' 2>&1 | tail -20
```

Expected: `doesNotRecordWhenNothingChanged` **만** 실패한다(`expected true but was false` 또는
`hasSize(1)` 불일치). 확인 후 복구한다.

- [ ] **Step 6: 커밋**

```bash
git add src/main/java/ai/devpath/community/post/ContentRevision.java \
        src/main/java/ai/devpath/community/post/ContentRevisionRepository.java \
        src/main/java/ai/devpath/community/post/ContentRevisionRecorder.java \
        src/test/java/ai/devpath/community/post/ContentRevisionRecorderTest.java
git commit -m "feat(content): 수정 이력 기록기를 더한다

수정 직전 본문을 다형 대상 테이블에 남긴다. 같은 내용으로 저장을 반복해도 이력이
늘지 않도록 직전 리비전과 제목·본문을 비교해 건너뛴다.

판별력 실측: 중복 검사 블록을 지우면 doesNotRecordWhenNothingChanged 만 red 가 된다."
```

---

## Task 6: 글·질문 수정

**Files:**
- Create: `src/main/java/ai/devpath/community/post/dto/UpdatePostRequest.java`
- Modify: `src/main/java/ai/devpath/community/post/PostService.java`
- Modify: `src/main/java/ai/devpath/community/post/CommunityController.java`
- Test: `src/test/java/ai/devpath/community/post/PostUpdateMockMvcTest.java`

**Interfaces:**
- Consumes: `ContentStatus`(Task 3) · `ContentRevisionRecorder`(Task 5)
- Produces: `PostService.updatePost(long userId, long postId, UpdatePostRequest req)` → `PostDetailView` · `PUT /community/posts/{id}`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/community/post/PostUpdateMockMvcTest.java`:

```java
package ai.devpath.community.post;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class PostUpdateMockMvcTest {

  @Autowired MockMvc mvc;
  @Autowired ContentRevisionRepository revisions;
  @Autowired CommunityPostRepository posts;

  private long createFreePost(String subject) throws Exception {
    String body = mvc.perform(post("/community/posts")
            .with(jwt().jwt(j -> j.subject(subject)))
            .contentType("application/json")
            .content("{\"boardType\":\"FREE\",\"title\":\"원제목\",\"bodyMd\":\"원본문\",\"tags\":[]}"))
        .andExpect(status().isCreated())
        .andReturn().getResponse().getContentAsString();
    return com.jayway.jsonpath.JsonPath.parse(body).read("$.id", Long.class);
  }

  @Test
  void authorCanUpdateAndPreviousBodyIsKept() throws Exception {
    long id = createFreePost("940001");

    mvc.perform(put("/community/posts/" + id)
            .with(jwt().jwt(j -> j.subject("940001")))
            .contentType("application/json")
            .content("{\"title\":\"새제목\",\"bodyMd\":\"새본문\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.title").value("새제목"))
        .andExpect(jsonPath("$.bodyMd").value("새본문"));

    mvc.perform(get("/community/posts/" + id).with(jwt().jwt(j -> j.subject("940001"))))
        .andExpect(jsonPath("$.title").value("새제목"));

    assertThat(revisions.findByTargetTypeAndTargetIdOrderByCreatedAtDesc("POST", id))
        .singleElement()
        .satisfies(r -> {
          assertThat(r.getTitle()).isEqualTo("원제목");
          assertThat(r.getBodyMd()).isEqualTo("원본문");
          assertThat(r.getEditedBy()).isEqualTo(940001L);
        });
  }

  @Test
  void otherUserCannotUpdate() throws Exception {
    long id = createFreePost("940002");

    mvc.perform(put("/community/posts/" + id)
            .with(jwt().jwt(j -> j.subject("940003")))
            .contentType("application/json")
            .content("{\"title\":\"침입\",\"bodyMd\":\"침입\"}"))
        .andExpect(status().isForbidden());
  }

  @Test
  void deletedPostCannotBeUpdated() throws Exception {
    long id = createFreePost("940004");
    CommunityPost p = posts.findById(id).orElseThrow();
    p.setStatus(ContentStatus.DELETED);
    posts.save(p);

    mvc.perform(put("/community/posts/" + id)
            .with(jwt().jwt(j -> j.subject("940004")))
            .contentType("application/json")
            .content("{\"title\":\"부활\",\"bodyMd\":\"부활\"}"))
        .andExpect(status().isNotFound());
  }

  @Test
  void emptyBodyIsRejected() throws Exception {
    long id = createFreePost("940005");

    mvc.perform(put("/community/posts/" + id)
            .with(jwt().jwt(j -> j.subject("940005")))
            .contentType("application/json")
            .content("{\"title\":\"제목\",\"bodyMd\":\"   \"}"))
        .andExpect(status().isBadRequest());
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd /d/workspace/dpa/devpath-community-svc
./gradlew test --tests '*PostUpdateMockMvcTest*' 2>&1 | tail -25
```

Expected: 4 개 모두 실패(`PUT` 매핑이 없어 405 또는 404).

- [ ] **Step 3: 구현한다**

`dto/UpdatePostRequest.java`:

```java
package ai.devpath.community.post.dto;

/** 글·질문 수정. 태그는 바꾸지 않는다 — 평판이 투표 시점 태그로 귀속되어 소급 변경이 어긋난다. */
public record UpdatePostRequest(String title, String bodyMd) {}
```

`PostService.java` — import 에 `UpdatePostRequest` 를 더하고, 필드·생성자에 `ContentRevisionRecorder` 를 더한 뒤 메서드를 추가한다.

import 추가:
```java
import ai.devpath.community.post.dto.UpdatePostRequest;
```

필드 추가(마지막 필드 뒤):
```java
  private final ContentRevisionRecorder revisions;
```

생성자 시그니처와 본문을 바꾼다.

바꾸기 전:
```java
  public PostService(CommunityPostRepository posts, CommunityTagRepository tags,
      CommunityPostTagRepository postTags, CommunityCommentRepository comments,
      PostIndexEventPublisher postIndexEvents) {
    this.posts = posts; this.tags = tags; this.postTags = postTags; this.comments = comments;
    this.postIndexEvents = postIndexEvents;
  }
```

바꾼 뒤:
```java
  public PostService(CommunityPostRepository posts, CommunityTagRepository tags,
      CommunityPostTagRepository postTags, CommunityCommentRepository comments,
      PostIndexEventPublisher postIndexEvents, ContentRevisionRecorder revisions) {
    this.posts = posts; this.tags = tags; this.postTags = postTags; this.comments = comments;
    this.postIndexEvents = postIndexEvents; this.revisions = revisions;
  }
```

`postDetail` 뒤에 메서드를 추가한다:

```java
  /**
   * 글·질문 본문 수정. 질문(QNA)도 같은 community_posts 행이므로 여기서 함께 처리한다.
   *
   * <p>시간 제한을 두지 않는다 — "N분 안에만" 은 이력이 없을 때 왜곡을 막는 방어책이고,
   * 우리는 리비전을 남기므로 그 방어가 다른 방식으로 성립한다.
   */
  @Transactional
  public PostDetailView updatePost(long userId, long postId, UpdatePostRequest req) {
    if (req.bodyMd() == null || req.bodyMd().isBlank()) {
      throw new IllegalArgumentException("bodyMd must not be blank");
    }
    if (req.title() == null || req.title().isBlank()) {
      throw new IllegalArgumentException("title must not be blank");
    }
    CommunityPost p = posts.findById(postId)
        .filter(found -> ContentStatus.PUBLISHED.equals(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("post " + postId));
    if (p.getAuthorId() == null || p.getAuthorId() != userId) {
      throw new ForbiddenException("작성자만 수정할 수 있습니다");
    }
    revisions.record("POST", postId, p.getTitle(), p.getBodyMd(), p.getBodyHtml(), userId);
    p.setTitle(req.title());
    p.setBodyMd(req.bodyMd());
    posts.save(p);
    postIndexEvents.publish(postId, false);
    return postDetail(postId);
  }
```

`CommunityController.java` — import 에 `UpdatePostRequest` 와 `PutMapping` 을 더하고 매핑을 추가한다.

import 추가:
```java
import ai.devpath.community.post.dto.UpdatePostRequest;
import org.springframework.web.bind.annotation.PutMapping;
```

`@GetMapping("/posts/{id}")` 아래에 추가:
```java
  @PutMapping("/posts/{id}")
  public ResponseEntity<PostDetailView> updatePost(
      @AuthenticationPrincipal Jwt jwt, @PathVariable long id, @RequestBody UpdatePostRequest req) {
    return ResponseEntity.ok(postService.updatePost(uid(jwt), id, req));
  }
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd /d/workspace/dpa/devpath-community-svc
./gradlew test --tests '*PostUpdateMockMvcTest*' 2>&1 | tail -10
```

Expected: BUILD SUCCESSFUL, 4 개 통과.

- [ ] **Step 5: 판별력을 실측한다**

`updatePost` 의 작성자 검사(`if (p.getAuthorId() == null || ...) throw new ForbiddenException(...)`)를 잠시 지우고 돌린다.

Expected: `otherUserCannotUpdate` **만** 실패한다. 확인 후 복구한다.

- [ ] **Step 6: 커밋**

```bash
git add src/main/java/ai/devpath/community/post/dto/UpdatePostRequest.java \
        src/main/java/ai/devpath/community/post/PostService.java \
        src/main/java/ai/devpath/community/post/CommunityController.java \
        src/test/java/ai/devpath/community/post/PostUpdateMockMvcTest.java
git commit -m "feat(content): 글·질문 수정 API 를 더한다

질문은 board_type='QNA' 인 같은 community_posts 행이므로 /posts/{id} 하나가 둘 다
처리한다. 태그는 수정 대상이 아니다 — 평판이 투표 시점 태그로 귀속되어 소급 변경이
어긋난다.

수정 시각 제한을 두지 않는 대신 직전 본문을 리비전에 남긴다. 색인은 제목·본문이
문서에 실리므로 갱신한다.

판별력 실측: 작성자 검사를 지우면 otherUserCannotUpdate 만 red 가 된다."
```

---

## Task 7: 글·질문 삭제

**Files:**
- Modify: `src/main/java/ai/devpath/community/post/PostService.java`
- Modify: `src/main/java/ai/devpath/community/post/CommunityController.java`
- Test: `src/test/java/ai/devpath/community/post/PostDeleteMockMvcTest.java`

**Interfaces:**
- Consumes: Task 6 의 `PostService` 생성자
- Produces: `PostService.deletePost(long userId, long postId)` → `void` · `DELETE /community/posts/{id}`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/community/post/PostDeleteMockMvcTest.java`:

```java
package ai.devpath.community.post;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class PostDeleteMockMvcTest {

  @Autowired MockMvc mvc;
  @Autowired CommunityPostRepository posts;

  private long createFreePost(String subject) throws Exception {
    String body = mvc.perform(post("/community/posts")
            .with(jwt().jwt(j -> j.subject(subject)))
            .contentType("application/json")
            .content("{\"boardType\":\"FREE\",\"title\":\"삭제대상\",\"bodyMd\":\"본문\",\"tags\":[]}"))
        .andExpect(status().isCreated())
        .andReturn().getResponse().getContentAsString();
    return com.jayway.jsonpath.JsonPath.parse(body).read("$.id", Long.class);
  }

  @Test
  void authorDeleteMarksDeletedAndHidesFromReads() throws Exception {
    long id = createFreePost("950001");

    mvc.perform(delete("/community/posts/" + id).with(jwt().jwt(j -> j.subject("950001"))))
        .andExpect(status().isNoContent());

    assertThat(posts.findById(id).orElseThrow().getStatus()).isEqualTo(ContentStatus.DELETED);

    mvc.perform(get("/community/posts/" + id).with(jwt().jwt(j -> j.subject("950001"))))
        .andExpect(status().isNotFound());
  }

  @Test
  void otherUserCannotDelete() throws Exception {
    long id = createFreePost("950002");

    mvc.perform(delete("/community/posts/" + id).with(jwt().jwt(j -> j.subject("950003"))))
        .andExpect(status().isForbidden());
  }

  @Test
  void deletingTwiceIsNotFound() throws Exception {
    long id = createFreePost("950004");

    mvc.perform(delete("/community/posts/" + id).with(jwt().jwt(j -> j.subject("950004"))))
        .andExpect(status().isNoContent());
    mvc.perform(delete("/community/posts/" + id).with(jwt().jwt(j -> j.subject("950004"))))
        .andExpect(status().isNotFound());
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd /d/workspace/dpa/devpath-community-svc
./gradlew test --tests '*PostDeleteMockMvcTest*' 2>&1 | tail -20
```

Expected: 3 개 모두 실패(`DELETE` 매핑 없음).

- [ ] **Step 3: 구현한다**

`PostService.java` — `updatePost` 뒤에 추가:

```java
  /**
   * 작성자 삭제. 상태만 바꾸고 자식(댓글)은 건드리지 않는다.
   *
   * <p>자식 상태를 전파하지 않는 이유는 되돌릴 수 있어야 하기 때문이다 — 전파하면 복구할 때
   * 자식이 스스로 삭제된 것인지 부모 때문인지 구분이 사라진다. 도달 경로는 이미 막혀 있다
   * (부모가 404 이고 자식 목록도 부모 상태를 확인한다).
   *
   * <p>이미 삭제된 것을 다시 지우면 404 다. 프론트가 resourceNotFound 를
   * "이미 삭제된 콘텐츠예요" 로 렌더하므로 그 UI 와 맞물린다.
   */
  @Transactional
  public void deletePost(long userId, long postId) {
    CommunityPost p = posts.findById(postId)
        .filter(found -> ContentStatus.PUBLISHED.equals(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("post " + postId));
    if (p.getAuthorId() == null || p.getAuthorId() != userId) {
      throw new ForbiddenException("작성자만 삭제할 수 있습니다");
    }
    p.setStatus(ContentStatus.DELETED);
    posts.save(p);
    postIndexEvents.publish(postId, true);
  }
```

`CommunityController.java` — import 에 `DeleteMapping` 을 더하고 매핑을 추가한다.

import 추가:
```java
import org.springframework.web.bind.annotation.DeleteMapping;
```

`@PutMapping("/posts/{id}")` 아래에 추가:
```java
  @DeleteMapping("/posts/{id}")
  public ResponseEntity<Void> deletePost(@AuthenticationPrincipal Jwt jwt, @PathVariable long id) {
    postService.deletePost(uid(jwt), id);
    return ResponseEntity.noContent().build();
  }
```

- [ ] **Step 4: 통과를 확인한다**

```bash
./gradlew test --tests '*PostDeleteMockMvcTest*' 2>&1 | tail -8
```

Expected: BUILD SUCCESSFUL, 3 개 통과.

- [ ] **Step 5: 색인 삭제 이벤트가 실제로 나가는지 확인한다**

```bash
docker exec devpath-pg psql -U devpath -d devpath_citest -c \
  "SELECT event_type, payload FROM outbox WHERE aggregate_type='community_post' \
   AND payload LIKE '%\"deleted\":true%' ORDER BY id DESC LIMIT 3"
```

Expected: `community.post.changed` 행이 `"deleted":true` 로 최소 1 건. ★코드베이스에서 `true` 가
처음 쓰이는 지점이다.★

- [ ] **Step 6: 커밋**

```bash
git add src/main/java/ai/devpath/community/post/PostService.java \
        src/main/java/ai/devpath/community/post/CommunityController.java \
        src/test/java/ai/devpath/community/post/PostDeleteMockMvcTest.java
git commit -m "feat(content): 글·질문 작성자 삭제 API 를 더한다

상태를 DELETED 로 바꾸고 색인 삭제 이벤트를 낸다 — publish(postId, true) 가
코드베이스에서 처음 쓰인다(소비자와 색인기는 이미 이 경로를 구현해 두고 있었다).

자식 댓글의 상태는 전파하지 않는다. 되돌릴 때 자식의 원래 상태를 잃지 않기 위해서이고,
도달 경로는 부모 404 와 자식 목록의 부모 확인으로 이미 막혀 있다.

재삭제는 404 다 — 프론트가 resourceNotFound 를 「이미 삭제된 콘텐츠예요」로 렌더한다."
```

---

## Task 8: 답변 수정·삭제와 비석

**Files:**
- Create: `src/main/java/ai/devpath/community/post/dto/UpdateBodyRequest.java`
- Modify: `src/main/java/ai/devpath/community/post/dto/AnswerView.java`
- Modify: `src/main/java/ai/devpath/community/post/AnswerService.java`
- Modify: `src/main/java/ai/devpath/community/post/QuestionService.java`
- Modify: `src/main/java/ai/devpath/community/post/CommunityController.java`
- Test: `src/test/java/ai/devpath/community/post/AnswerEditDeleteMockMvcTest.java`

**Interfaces:**
- Consumes: `ContentStatus` · `ContentRevisionRecorder` · `ConflictException`(기존 `ai.devpath.community.report.ConflictException`)
- Produces: `AnswerService.update(long userId, long answerId, UpdateBodyRequest req)` → `AnswerView` · `AnswerService.delete(long userId, long answerId)` → `void` · `AnswerView` 에 `boolean deleted` 추가

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/community/post/AnswerEditDeleteMockMvcTest.java`:

```java
package ai.devpath.community.post;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class AnswerEditDeleteMockMvcTest {

  @Autowired MockMvc mvc;

  private long createQuestion(String subject) throws Exception {
    String body = mvc.perform(post("/community/questions")
            .with(jwt().jwt(j -> j.subject(subject)))
            .contentType("application/json")
            .content("{\"title\":\"질문\",\"bodyMd\":\"질문본문\",\"tags\":[]}"))
        .andExpect(status().isCreated())
        .andReturn().getResponse().getContentAsString();
    return com.jayway.jsonpath.JsonPath.parse(body).read("$.id", Long.class);
  }

  private long addAnswer(long questionId, String subject) throws Exception {
    String body = mvc.perform(post("/community/questions/" + questionId + "/answers")
            .with(jwt().jwt(j -> j.subject(subject)))
            .contentType("application/json").content("{\"bodyMd\":\"답변본문\"}"))
        .andExpect(status().isCreated())
        .andReturn().getResponse().getContentAsString();
    return com.jayway.jsonpath.JsonPath.parse(body).read("$.id", Long.class);
  }

  @Test
  void authorCanUpdateAnswer() throws Exception {
    long qid = createQuestion("960001");
    long aid = addAnswer(qid, "960002");

    mvc.perform(put("/community/answers/" + aid)
            .with(jwt().jwt(j -> j.subject("960002")))
            .contentType("application/json").content("{\"bodyMd\":\"고친답변\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.bodyMd").value("고친답변"));
  }

  @Test
  void otherUserCannotUpdateAnswer() throws Exception {
    long qid = createQuestion("960003");
    long aid = addAnswer(qid, "960004");

    mvc.perform(put("/community/answers/" + aid)
            .with(jwt().jwt(j -> j.subject("960005")))
            .contentType("application/json").content("{\"bodyMd\":\"침입\"}"))
        .andExpect(status().isForbidden());
  }

  @Test
  void deletedAnswerBecomesTombstoneInQuestionDetail() throws Exception {
    long qid = createQuestion("960006");
    long aid = addAnswer(qid, "960007");

    mvc.perform(delete("/community/answers/" + aid).with(jwt().jwt(j -> j.subject("960007"))))
        .andExpect(status().isNoContent());

    mvc.perform(get("/community/questions/" + qid).with(jwt().jwt(j -> j.subject("960006"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.answers.length()").value(1))
        .andExpect(jsonPath("$.answers[0].deleted").value(true))
        .andExpect(jsonPath("$.answers[0].bodyMd").doesNotExist())
        .andExpect(jsonPath("$.answers[0].authorId").doesNotExist());
  }

  @Test
  void acceptedAnswerCannotBeDeletedByAuthor() throws Exception {
    long qid = createQuestion("960008");
    long aid = addAnswer(qid, "960009");

    mvc.perform(post("/community/answers/" + aid + "/accept")
            .with(jwt().jwt(j -> j.subject("960008"))))
        .andExpect(status().isOk());

    mvc.perform(delete("/community/answers/" + aid).with(jwt().jwt(j -> j.subject("960009"))))
        .andExpect(status().isConflict());
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
./gradlew test --tests '*AnswerEditDeleteMockMvcTest*' 2>&1 | tail -25
```

Expected: 4 개 모두 실패.

- [ ] **Step 3: 구현한다**

`dto/UpdateBodyRequest.java`:

```java
package ai.devpath.community.post.dto;

/** 답변·댓글 수정. 제목이 없다. */
public record UpdateBodyRequest(String bodyMd) {}
```

`dto/AnswerView.java` 를 통째로 바꾼다:

```java
package ai.devpath.community.post.dto;

/**
 * 답변 표현. {@code deleted=true} 면 비석이다 — 본문과 작성자를 비운다.
 *
 * <p>비석의 목적은 스레드 맥락 보존이지 "누가 썼다 지웠다" 의 기록이 아니므로 작성자도 감춘다.
 * 집계(upvoteCount)는 남긴다 — 작성자 삭제는 평판을 유지하기로 했으므로 일관된다.
 */
public record AnswerView(long id, Long authorId, String bodyMd, boolean aiGenerated,
    boolean accepted, int upvoteCount, boolean deleted) {

  public static AnswerView tombstone(long id, int upvoteCount) {
    return new AnswerView(id, null, null, false, false, upvoteCount, true);
  }
}
```

`AnswerService.java` — import 와 필드를 더하고 메서드를 추가한다.

import 추가:
```java
import ai.devpath.community.post.dto.UpdateBodyRequest;
import ai.devpath.community.report.ConflictException;
```

필드 추가:
```java
  private final ContentRevisionRecorder revisions;
```

생성자를 바꾼다.

바꾸기 전:
```java
  public AnswerService(CommunityPostRepository posts, CommunityQuestionRepository questions,
      CommunityAnswerRepository answers, ReputationService reputation,
      CommunityPostTagRepository postTags, BadgeService badgeService) {
    this.posts = posts; this.questions = questions; this.answers = answers;
    this.reputation = reputation; this.postTags = postTags;
    this.badgeService = badgeService;
  }
```

바꾼 뒤:
```java
  public AnswerService(CommunityPostRepository posts, CommunityQuestionRepository questions,
      CommunityAnswerRepository answers, ReputationService reputation,
      CommunityPostTagRepository postTags, BadgeService badgeService,
      ContentRevisionRecorder revisions) {
    this.posts = posts; this.questions = questions; this.answers = answers;
    this.reputation = reputation; this.postTags = postTags;
    this.badgeService = badgeService; this.revisions = revisions;
  }
```

`add` 메서드의 반환문을 새 레코드 시그니처에 맞춘다.

바꾸기 전:
```java
    return new AnswerView(a.getId(), a.getAuthorId(), a.getBodyMd(),
        a.isAiGenerated(), a.isAccepted(), a.getUpvoteCount());
```

바꾼 뒤:
```java
    return new AnswerView(a.getId(), a.getAuthorId(), a.getBodyMd(),
        a.isAiGenerated(), a.isAccepted(), a.getUpvoteCount(), false);
```

클래스 끝(`awardPhilanthropistIfReached` 앞)에 두 메서드를 추가한다:

```java
  @Transactional
  public AnswerView update(long userId, long answerId, UpdateBodyRequest req) {
    if (req.bodyMd() == null || req.bodyMd().isBlank()) {
      throw new IllegalArgumentException("bodyMd must not be blank");
    }
    CommunityAnswer a = answers.findById(answerId)
        .filter(found -> ContentStatus.PUBLISHED.equals(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("answer " + answerId));
    if (a.getAuthorId() == null || a.getAuthorId() != userId) {
      throw new ForbiddenException("작성자만 수정할 수 있습니다");
    }
    revisions.record("ANSWER", answerId, null, a.getBodyMd(), a.getBodyHtml(), userId);
    a.setBodyMd(req.bodyMd());
    answers.save(a);
    return new AnswerView(a.getId(), a.getAuthorId(), a.getBodyMd(),
        a.isAiGenerated(), a.isAccepted(), a.getUpvoteCount(), false);
  }

  /**
   * 작성자 삭제.
   *
   * <p>★수용된 답변은 지울 수 없다★ — 질문자가 "이게 정답" 이라고 공식화한 것이라 작성자가
   * 마음대로 지우면 질문이 깨진다. 409 로 돌려보내 먼저 수용을 해제하게 한다.
   * (관리자 삭제는 이 제한을 받지 않는다 — 규정 위반 답변이 하필 수용된 상태일 수 있다.)
   */
  @Transactional
  public void delete(long userId, long answerId) {
    CommunityAnswer a = answers.findById(answerId)
        .filter(found -> ContentStatus.PUBLISHED.equals(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("answer " + answerId));
    if (a.getAuthorId() == null || a.getAuthorId() != userId) {
      throw new ForbiddenException("작성자만 삭제할 수 있습니다");
    }
    if (a.isAccepted()) {
      throw new ConflictException("채택된 답변입니다. 채택을 먼저 해제해 주세요.");
    }
    a.setStatus(ContentStatus.DELETED);
    answers.save(a);
  }
```

`QuestionService.java` — `detail` 의 답변 매핑을 비석 처리로 바꾼다.

바꾸기 전:
```java
    List<AnswerView> ans = answers.findByQuestionIdOrderByCreatedAtAsc(postId).stream()
        .map(a -> new AnswerView(a.getId(), a.getAuthorId(), a.getBodyMd(),
            a.isAiGenerated(), a.isAccepted(), a.getUpvoteCount()))
        .collect(Collectors.toList());
```

바꾼 뒤:
```java
    List<AnswerView> ans = answers.findByQuestionIdOrderByCreatedAtAsc(postId).stream()
        .map(a -> ContentStatus.PUBLISHED.equals(a.getStatus())
            ? new AnswerView(a.getId(), a.getAuthorId(), a.getBodyMd(),
                a.isAiGenerated(), a.isAccepted(), a.getUpvoteCount(), false)
            : AnswerView.tombstone(a.getId(), a.getUpvoteCount()))
        .collect(Collectors.toList());
```

`CommunityController.java` — 매핑 두 개를 추가한다.

import 추가:
```java
import ai.devpath.community.post.dto.UpdateBodyRequest;
```

`@PostMapping("/answers/{id}/vote")` 아래에 추가:
```java
  @PutMapping("/answers/{id}")
  public ResponseEntity<AnswerView> updateAnswer(
      @AuthenticationPrincipal Jwt jwt, @PathVariable long id, @RequestBody UpdateBodyRequest req) {
    return ResponseEntity.ok(answerService.update(uid(jwt), id, req));
  }

  @DeleteMapping("/answers/{id}")
  public ResponseEntity<Void> deleteAnswer(
      @AuthenticationPrincipal Jwt jwt, @PathVariable long id) {
    answerService.delete(uid(jwt), id);
    return ResponseEntity.noContent().build();
  }
```

`AnswerView` 가 import 되어 있지 않다면 더한다:
```java
import ai.devpath.community.post.dto.AnswerView;
```

- [ ] **Step 4: 통과를 확인한다**

```bash
./gradlew test --tests '*AnswerEditDeleteMockMvcTest*' 2>&1 | tail -10
```

Expected: BUILD SUCCESSFUL, 4 개 통과.

- [ ] **Step 5: 기존 테스트 회귀를 확인한다**

`AnswerView` 시그니처가 바뀌었으므로 이를 쓰는 다른 테스트가 깨질 수 있다.

```bash
./gradlew test 2>&1 | tail -20
```

Expected: BUILD SUCCESSFUL. 실패하면 `new AnswerView(...)` 호출부에 `, false` 를 더한다.

- [ ] **Step 6: 판별력을 실측한다**

`delete` 의 `if (a.isAccepted()) throw new ConflictException(...)` 을 잠시 지우고 돌린다.

Expected: `acceptedAnswerCannotBeDeletedByAuthor` **만** 실패한다. 확인 후 복구한다.

- [ ] **Step 7: 커밋**

```bash
git add src/main/java/ai/devpath/community/post/dto/UpdateBodyRequest.java \
        src/main/java/ai/devpath/community/post/dto/AnswerView.java \
        src/main/java/ai/devpath/community/post/AnswerService.java \
        src/main/java/ai/devpath/community/post/QuestionService.java \
        src/main/java/ai/devpath/community/post/CommunityController.java \
        src/test/java/ai/devpath/community/post/AnswerEditDeleteMockMvcTest.java
git commit -m "feat(content): 답변 수정·삭제와 비석 표현을 더한다

답변은 완전히 사라지지 않고 비석으로 남는다 — 스레드 맥락(「위 답변처럼」 같은 참조)이
끊기지 않게 하기 위해서다. 비석은 본문과 작성자를 비우되 집계는 남긴다.

채택된 답변은 작성자가 지울 수 없다(409). 질문자가 공식화한 것이라 마음대로 사라지면
질문이 깨진다.

판별력 실측: 채택 가드를 지우면 acceptedAnswerCannotBeDeletedByAuthor 만 red 가 된다."
```

---

## Task 9: 댓글 수정·삭제와 비석

**Files:**
- Modify: `src/main/java/ai/devpath/community/post/dto/CommentView.java`
- Modify: `src/main/java/ai/devpath/community/post/CommentService.java`
- Modify: `src/main/java/ai/devpath/community/post/PostService.java`
- Modify: `src/main/java/ai/devpath/community/post/CommunityController.java`
- Test: `src/test/java/ai/devpath/community/post/CommentEditDeleteMockMvcTest.java`

**Interfaces:**
- Consumes: `UpdateBodyRequest`(Task 8) · `ContentRevisionRecorder`
- Produces: `CommentService.update(long userId, long commentId, UpdateBodyRequest req)` → `CommentView` · `CommentService.delete(long userId, long commentId)` → `void` · `CommentView` 에 `boolean deleted` 추가

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/community/post/CommentEditDeleteMockMvcTest.java`:

```java
package ai.devpath.community.post;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class CommentEditDeleteMockMvcTest {

  @Autowired MockMvc mvc;

  private long createFreePost(String subject) throws Exception {
    String body = mvc.perform(post("/community/posts")
            .with(jwt().jwt(j -> j.subject(subject)))
            .contentType("application/json")
            .content("{\"boardType\":\"FREE\",\"title\":\"댓글모글\",\"bodyMd\":\"본문\",\"tags\":[]}"))
        .andExpect(status().isCreated())
        .andReturn().getResponse().getContentAsString();
    return com.jayway.jsonpath.JsonPath.parse(body).read("$.id", Long.class);
  }

  private long addComment(long postId, String subject) throws Exception {
    String body = mvc.perform(post("/community/posts/" + postId + "/comments")
            .with(jwt().jwt(j -> j.subject(subject)))
            .contentType("application/json").content("{\"bodyMd\":\"댓글본문\"}"))
        .andExpect(status().isCreated())
        .andReturn().getResponse().getContentAsString();
    return com.jayway.jsonpath.JsonPath.parse(body).read("$.id", Long.class);
  }

  @Test
  void authorCanUpdateComment() throws Exception {
    long pid = createFreePost("970001");
    long cid = addComment(pid, "970002");

    mvc.perform(put("/community/comments/" + cid)
            .with(jwt().jwt(j -> j.subject("970002")))
            .contentType("application/json").content("{\"bodyMd\":\"고친댓글\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.bodyMd").value("고친댓글"));
  }

  @Test
  void otherUserCannotDeleteComment() throws Exception {
    long pid = createFreePost("970003");
    long cid = addComment(pid, "970004");

    mvc.perform(delete("/community/comments/" + cid).with(jwt().jwt(j -> j.subject("970005"))))
        .andExpect(status().isForbidden());
  }

  @Test
  void deletedCommentIsTombstoneInBothReadPaths() throws Exception {
    long pid = createFreePost("970006");
    long cid = addComment(pid, "970007");

    mvc.perform(delete("/community/comments/" + cid).with(jwt().jwt(j -> j.subject("970007"))))
        .andExpect(status().isNoContent());

    // 목록 경로
    mvc.perform(get("/community/posts/" + pid + "/comments")
            .with(jwt().jwt(j -> j.subject("970006"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(1))
        .andExpect(jsonPath("$[0].deleted").value(true))
        .andExpect(jsonPath("$[0].bodyMd").doesNotExist())
        .andExpect(jsonPath("$[0].authorId").doesNotExist());

    // 상세 안에 박힌 경로 — 같은 매핑이 두 곳에 있어 한쪽만 고치면 어긋난다.
    mvc.perform(get("/community/posts/" + pid).with(jwt().jwt(j -> j.subject("970006"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.comments.length()").value(1))
        .andExpect(jsonPath("$.comments[0].deleted").value(true))
        .andExpect(jsonPath("$.comments[0].bodyMd").doesNotExist());
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
./gradlew test --tests '*CommentEditDeleteMockMvcTest*' 2>&1 | tail -25
```

Expected: 3 개 모두 실패.

- [ ] **Step 3: 구현한다**

`dto/CommentView.java` 를 통째로 바꾼다:

```java
package ai.devpath.community.post.dto;

import java.time.Instant;

/**
 * 댓글 표현. {@code deleted=true} 면 비석이다 — 본문과 작성자를 비운다.
 *
 * <p>작성 시각은 남긴다. 스레드 순서가 보이지 않으면 비석의 의미가 없다.
 */
public record CommentView(long id, Long authorId, String bodyMd, int upvoteCount,
    Instant createdAt, boolean deleted) {

  public static CommentView tombstone(long id, int upvoteCount, Instant createdAt) {
    return new CommentView(id, null, null, upvoteCount, createdAt, true);
  }
}
```

`CommentService.java` — 필드·생성자에 `ContentRevisionRecorder` 를 더하고 매핑을 비석 처리로 바꾼 뒤 두 메서드를 추가한다.

import 추가:
```java
import ai.devpath.community.post.dto.UpdateBodyRequest;
```

바꾸기 전:
```java
  public CommentService(CommunityPostRepository posts, CommunityCommentRepository comments) {
    this.posts = posts; this.comments = comments;
  }
```

바꾼 뒤:
```java
  private final ContentRevisionRecorder revisions;

  public CommentService(CommunityPostRepository posts, CommunityCommentRepository comments,
      ContentRevisionRecorder revisions) {
    this.posts = posts; this.comments = comments; this.revisions = revisions;
  }

  /** 비석 여부를 한 곳에서 판단한다 — 목록과 상세 두 경로가 같은 규칙을 쓰게 하기 위해서다. */
  static CommentView toView(CommunityComment c) {
    return ContentStatus.PUBLISHED.equals(c.getStatus())
        ? new CommentView(c.getId(), c.getAuthorId(), c.getBodyMd(), c.getUpvoteCount(),
            c.getCreatedAt(), false)
        : CommentView.tombstone(c.getId(), c.getUpvoteCount(), c.getCreatedAt());
  }
```

`addComment` 의 반환문을 바꾼다.

바꾸기 전:
```java
    return new CommentView(c.getId(), c.getAuthorId(), c.getBodyMd(), c.getUpvoteCount(),
        c.getCreatedAt());
```

바꾼 뒤:
```java
    return toView(c);
```

`listComments` 의 매핑을 바꾼다.

바꾸기 전:
```java
    return comments.findByPostIdOrderByCreatedAtAsc(postId).stream()
        .map(c -> new CommentView(c.getId(), c.getAuthorId(), c.getBodyMd(), c.getUpvoteCount(),
            c.getCreatedAt()))
        .collect(Collectors.toList());
```

바꾼 뒤:
```java
    return comments.findByPostIdOrderByCreatedAtAsc(postId).stream()
        .map(CommentService::toView)
        .collect(Collectors.toList());
```

클래스 끝에 두 메서드를 추가한다:

```java
  @Transactional
  public CommentView update(long userId, long commentId, UpdateBodyRequest req) {
    if (req.bodyMd() == null || req.bodyMd().isBlank()) {
      throw new IllegalArgumentException("bodyMd must not be blank");
    }
    CommunityComment c = comments.findById(commentId)
        .filter(found -> ContentStatus.PUBLISHED.equals(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("comment " + commentId));
    if (c.getAuthorId() == null || c.getAuthorId() != userId) {
      throw new ForbiddenException("작성자만 수정할 수 있습니다");
    }
    revisions.record("COMMENT", commentId, null, c.getBodyMd(), c.getBodyHtml(), userId);
    c.setBodyMd(req.bodyMd());
    comments.save(c);
    return toView(c);
  }

  @Transactional
  public void delete(long userId, long commentId) {
    CommunityComment c = comments.findById(commentId)
        .filter(found -> ContentStatus.PUBLISHED.equals(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("comment " + commentId));
    if (c.getAuthorId() == null || c.getAuthorId() != userId) {
      throw new ForbiddenException("작성자만 삭제할 수 있습니다");
    }
    c.setStatus(ContentStatus.DELETED);
    comments.save(c);
  }
```

`PostService.java` — `postDetail` 의 댓글 매핑을 공용 헬퍼로 바꾼다.

바꾸기 전:
```java
    List<CommentView> commentViews = comments.findByPostIdOrderByCreatedAtAsc(postId).stream()
        .map(c -> new CommentView(c.getId(), c.getAuthorId(), c.getBodyMd(),
            c.getUpvoteCount(), c.getCreatedAt()))
        .collect(Collectors.toList());
```

바꾼 뒤:
```java
    List<CommentView> commentViews = comments.findByPostIdOrderByCreatedAtAsc(postId).stream()
        .map(CommentService::toView)
        .collect(Collectors.toList());
```

`CommunityController.java` — 매핑 두 개를 추가한다. `@GetMapping("/posts/{id}/comments")` 아래:

```java
  @PutMapping("/comments/{id}")
  public ResponseEntity<CommentView> updateComment(
      @AuthenticationPrincipal Jwt jwt, @PathVariable long id, @RequestBody UpdateBodyRequest req) {
    return ResponseEntity.ok(commentService.update(uid(jwt), id, req));
  }

  @DeleteMapping("/comments/{id}")
  public ResponseEntity<Void> deleteComment(
      @AuthenticationPrincipal Jwt jwt, @PathVariable long id) {
    commentService.delete(uid(jwt), id);
    return ResponseEntity.noContent().build();
  }
```

- [ ] **Step 4: 통과를 확인한다**

```bash
./gradlew test --tests '*CommentEditDeleteMockMvcTest*' 2>&1 | tail -10
```

Expected: BUILD SUCCESSFUL, 3 개 통과.

- [ ] **Step 5: 전체 회귀를 확인한다**

`CommentView` 시그니처가 바뀌었으므로 호출부가 깨질 수 있다.

```bash
./gradlew test 2>&1 | tail -20
```

Expected: BUILD SUCCESSFUL.

- [ ] **Step 6: 판별력을 실측한다**

★두 읽기 경로가 같은 규칙을 쓰는지가 이 태스크의 핵심이다.★ `PostService.postDetail` 의
`.map(CommentService::toView)` 를 예전 매핑(`new CommentView(...)` 직접 생성, `deleted` 자리에
`false`)으로 되돌리고 돌린다.

Expected: `deletedCommentIsTombstoneInBothReadPaths` **만** 실패하고, 실패 지점이 `$.comments[0]`
쪽이다(목록 경로 단언은 통과). 확인 후 복구한다.

- [ ] **Step 7: 커밋**

```bash
git add src/main/java/ai/devpath/community/post/dto/CommentView.java \
        src/main/java/ai/devpath/community/post/CommentService.java \
        src/main/java/ai/devpath/community/post/PostService.java \
        src/main/java/ai/devpath/community/post/CommunityController.java \
        src/test/java/ai/devpath/community/post/CommentEditDeleteMockMvcTest.java
git commit -m "feat(content): 댓글 수정·삭제와 비석 표현을 더한다

댓글 매핑이 CommentService.listComments 와 PostService.postDetail 두 곳에 복제돼
있었다. 비석 규칙이 한쪽에만 들어가면 「목록에서는 가려지는데 상세에서는 보이는」
어긋남이 생기므로 toView 헬퍼로 모은다.

판별력 실측: postDetail 매핑만 예전으로 되돌리면 상세 경로 단언만 red 가 된다."
```

---

## Task 10: 평판 순합 회수

★**이 태스크가 이 계획의 핵심 회귀 가드다.**★ 순진한 구현("그 소스의 모든 이벤트를 하나씩
`-delta` 로 뒤집는다")은 **이미 취소된 투표가 있을 때 아무것도 회수하지 못한다** — 원본(`+10`)과
그 역산(`-10`)이 둘 다 저장돼 있어 각각 뒤집으면 순효과가 0 이 된다.

**Files:**
- Modify: `src/main/java/ai/devpath/community/reputation/ReputationEventRepository.java`
- Modify: `src/main/java/ai/devpath/community/reputation/ReputationService.java`
- Test: `src/test/java/ai/devpath/community/reputation/ReputationRevokeAllTest.java`

**Interfaces:**
- Consumes: 기존 `ReputationEvent` · `UserReputationRepository` · `UserTagReputationRepository`
- Produces: `ReputationService.revokeAllForSource(String sourceType, long sourceId, List<Long> tagIds)` → `void`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/community/reputation/ReputationRevokeAllTest.java`:

```java
package ai.devpath.community.reputation;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class ReputationRevokeAllTest {

  @Autowired ReputationService reputation;

  /**
   * ★순진한 「이벤트별 역산」 구현이면 이 테스트만 red 가 된다★
   *
   * <p>투표 → 취소 → 재투표로 이벤트가 여러 겹 쌓인 상태를 만든다. 이때 각 이벤트를 하나씩
   * 뒤집으면 원본과 역산이 서로를 상쇄해 순효과가 0 이 되고, 평판이 하나도 회수되지 않는다.
   * 올바른 구현은 (userId, reason) 순합을 구해 그 합만큼만 되돌린다.
   */
  @Test
  void revokeAllRemovesNetReputationEvenAfterVoteChurn() {
    long author = 980001L;
    long voter = 980002L;
    long sourceId = 980100L;
    List<Long> tagIds = List.of();

    reputation.applyVote(author, voter, "ANSWER", sourceId, 0, 1, tagIds);   // upvote
    reputation.applyVote(author, voter, "ANSWER", sourceId, 1, 0, tagIds);   // 취소
    reputation.applyVote(author, voter, "ANSWER", sourceId, 0, 1, tagIds);   // 재투표

    int before = reputation.reputationOf(author);
    assertThat(before).isGreaterThan(0);

    reputation.revokeAllForSource("ANSWER", sourceId, tagIds);

    assertThat(reputation.reputationOf(author)).isZero();
  }

  /** 회수는 멱등하다 — 순합이 0 이 된 뒤 다시 돌려도 아무 일이 없어야 한다. */
  @Test
  void revokeAllIsIdempotent() {
    long author = 980003L;
    long voter = 980004L;
    long sourceId = 980101L;
    List<Long> tagIds = List.of();

    reputation.applyVote(author, voter, "ANSWER", sourceId, 0, 1, tagIds);
    reputation.revokeAllForSource("ANSWER", sourceId, tagIds);
    int afterFirst = reputation.reputationOf(author);

    reputation.revokeAllForSource("ANSWER", sourceId, tagIds);

    assertThat(reputation.reputationOf(author)).isEqualTo(afterFirst).isZero();
  }

  /** 수용 보너스도 같은 (sourceType, sourceId) 에 쌓이므로 순합에 자연히 들어온다. */
  @Test
  void revokeAllAlsoRemovesAcceptanceBonus() {
    long answerAuthor = 980005L;
    long questionAuthor = 980006L;
    long sourceId = 980102L;
    List<Long> tagIds = List.of();

    reputation.applyAcceptance(answerAuthor, questionAuthor, "ANSWER", sourceId, tagIds);
    assertThat(reputation.reputationOf(answerAuthor)).isGreaterThan(0);
    assertThat(reputation.reputationOf(questionAuthor)).isGreaterThan(0);

    reputation.revokeAllForSource("ANSWER", sourceId, tagIds);

    assertThat(reputation.reputationOf(answerAuthor)).isZero();
    assertThat(reputation.reputationOf(questionAuthor)).isZero();
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
./gradlew test --tests '*ReputationRevokeAllTest*' 2>&1 | tail -20
```

Expected: 컴파일 실패 — `revokeAllForSource` 가 없다.

- [ ] **Step 3: 구현한다**

`ReputationEventRepository.java` — 인터페이스 끝에 쿼리를 추가한다:

```java
  /**
   * (userId, reason) 별 델타 순합. 관리자 삭제 시 평판을 되돌리는 데 쓴다.
   *
   * <p>★이벤트를 하나씩 뒤집으면 안 된다★ — 취소된 투표는 원본(+10)과 역산(-10)이 둘 다
   * 저장돼 있어 각각 뒤집으면 순효과가 0 이 된다. 순합이 0 이 아닌 것만 되돌려야 한다.
   */
  @Query("""
      select e.userId, e.reason, coalesce(sum(e.delta), 0) from ReputationEvent e
      where e.sourceType = :sourceType and e.sourceId = :sourceId
      group by e.userId, e.reason having coalesce(sum(e.delta), 0) <> 0
      """)
  List<Object[]> netBySource(@Param("sourceType") String sourceType,
      @Param("sourceId") Long sourceId);
```

`ReputationService.java` — `applyAcceptance` 뒤에 메서드를 추가한다:

```java
  /**
   * 그 콘텐츠로 얻은 평판을 전부 되돌린다. 관리자 삭제(HIDDEN)에서만 쓴다 —
   * 작성자 삭제(DELETED)는 이미 받은 평가를 무효로 만들지 않는다.
   *
   * <p>{@link #reverseVote} 를 재사용할 수 없다. 그것은 한 투표자의 이벤트만 되돌리고,
   * 여기서는 모든 투표자와 수용 보너스까지 되돌려야 한다. 그리고 ★이벤트별 역산은 틀린다★ —
   * 취소된 투표의 원본과 역산이 서로를 상쇄해 아무것도 회수되지 않는다. 순합을 되돌린다.
   *
   * <p>회수 후 순합이 0 이 되므로 다시 호출해도 아무 일이 없다(멱등).
   */
  @Transactional
  public void revokeAllForSource(String sourceType, long sourceId, List<Long> tagIds) {
    for (Object[] row : events.netBySource(sourceType, sourceId)) {
      long userId = ((Number) row[0]).longValue();
      String reason = (String) row[1];
      int net = ((Number) row[2]).intValue();
      int back = -net;
      addTotal(userId, back);
      // 행사자 비용(DOWNVOTE_CAST)은 태그 무관이다 — reverseVote 와 같은 예외 처리.
      if (!ReputationReason.DOWNVOTE_CAST.name().equals(reason)) {
        for (Long tagId : tagIds) addTag(userId, tagId, back);
      }
      events.save(new ReputationEvent(userId, null, back,
          ReputationReason.valueOf(reason), sourceType, sourceId));
    }
  }
```

- [ ] **Step 4: 통과를 확인한다**

```bash
./gradlew test --tests '*ReputationRevokeAllTest*' 2>&1 | tail -10
```

Expected: BUILD SUCCESSFUL, 3 개 통과.

- [ ] **Step 5: ★순진한 구현이 실제로 red 가 되는지 실측한다★**

`revokeAllForSource` 를 잠시 "이벤트별 역산" 으로 바꿔 돌린다:

```java
  @Transactional
  public void revokeAllForSource(String sourceType, long sourceId, List<Long> tagIds) {
    for (ReputationEvent e : events.findAll()) {
      if (!sourceType.equals(e.getSourceType()) || !Long.valueOf(sourceId).equals(e.getSourceId())) {
        continue;
      }
      int back = -e.getDelta();
      addTotal(e.getUserId(), back);
      if (!ReputationReason.DOWNVOTE_CAST.name().equals(e.getReason())) {
        for (Long tagId : tagIds) addTag(e.getUserId(), tagId, back);
      }
      events.save(new ReputationEvent(e.getUserId(), null, back,
          ReputationReason.valueOf(e.getReason()), sourceType, sourceId));
    }
  }
```

Expected: `revokeAllRemovesNetReputationEvenAfterVoteChurn` 이 **실패**한다
(`expected: 0 but was: <양수>`). ★이것이 이 태스크의 존재 이유다 — 이벤트가 한 겹뿐인 단순
시나리오였다면 두 구현이 똑같이 green 이라 구분되지 않는다.★

확인 후 올바른 구현으로 복구하고 green 을 재확인한다.

- [ ] **Step 6: 커밋**

```bash
git add src/main/java/ai/devpath/community/reputation/ReputationEventRepository.java \
        src/main/java/ai/devpath/community/reputation/ReputationService.java \
        src/test/java/ai/devpath/community/reputation/ReputationRevokeAllTest.java
git commit -m "feat(reputation): 콘텐츠 단위 평판 순합 회수를 더한다

관리자 삭제는 그 콘텐츠로 얻은 평판을 되돌린다. reverseVote 는 한 투표자의 이벤트만
다루므로 재사용할 수 없다.

★이벤트별 역산은 틀린다★ — 취소된 투표는 원본(+10)과 역산(-10)이 둘 다 저장돼 있어
각각 뒤집으면 순효과가 0 이 되고 아무것도 회수되지 않는다. (userId, reason) 순합이
0 이 아닌 것만 되돌린다.

판별력 실측: 순진한 이벤트별 역산으로 바꾸면 투표 churn 테스트만 red 가 된다.
이벤트가 한 겹뿐인 시나리오에서는 두 구현이 똑같이 green 이라 구분되지 않는다."
```

---

## Task 11: 관리자 삭제

**Files:**
- Create: `src/main/java/ai/devpath/community/post/ContentAdminService.java`
- Create: `src/main/java/ai/devpath/community/post/ContentAdminController.java`
- Test: `src/test/java/ai/devpath/community/post/ContentAdminMockMvcTest.java`

**Interfaces:**
- Consumes: `ContentStatus` · `ReputationService.revokeAllForSource`(Task 10) · `PostIndexEventPublisher`
- Produces: `DELETE /community/admin/posts/{id}` · `/answers/{id}` · `/comments/{id}`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/community/post/ContentAdminMockMvcTest.java`:

```java
package ai.devpath.community.post;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import ai.devpath.community.reputation.ReputationService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class ContentAdminMockMvcTest {

  @Autowired MockMvc mvc;
  @Autowired CommunityAnswerRepository answers;
  @Autowired CommunityQuestionRepository questions;
  @Autowired ReputationService reputation;

  private static org.springframework.test.web.servlet.request.RequestPostProcessor admin(String id) {
    return jwt().jwt(j -> j.subject(id).claim("role", "ADMIN"));
  }

  private long createQuestion(String subject) throws Exception {
    String body = mvc.perform(post("/community/questions")
            .with(jwt().jwt(j -> j.subject(subject)))
            .contentType("application/json")
            .content("{\"title\":\"관리자대상\",\"bodyMd\":\"본문\",\"tags\":[]}"))
        .andExpect(status().isCreated())
        .andReturn().getResponse().getContentAsString();
    return com.jayway.jsonpath.JsonPath.parse(body).read("$.id", Long.class);
  }

  private long addAnswer(long questionId, String subject) throws Exception {
    String body = mvc.perform(post("/community/questions/" + questionId + "/answers")
            .with(jwt().jwt(j -> j.subject(subject)))
            .contentType("application/json").content("{\"bodyMd\":\"답변\"}"))
        .andExpect(status().isCreated())
        .andReturn().getResponse().getContentAsString();
    return com.jayway.jsonpath.JsonPath.parse(body).read("$.id", Long.class);
  }

  @Test
  void nonAdminIsRejected() throws Exception {
    long qid = createQuestion("990001");

    mvc.perform(delete("/community/admin/posts/" + qid)
            .with(jwt().jwt(j -> j.subject("990002"))))
        .andExpect(status().isForbidden());
  }

  @Test
  void adminDeleteMarksHiddenAndRevokesReputation() throws Exception {
    long qid = createQuestion("990003");
    long aid = addAnswer(qid, "990004");

    mvc.perform(post("/community/answers/" + aid + "/vote")
            .with(jwt().jwt(j -> j.subject("990005")))
            .contentType("application/json").content("{\"value\":1}"))
        .andExpect(status().isOk());
    assertThat(reputation.reputationOf(990004L)).isGreaterThan(0);

    mvc.perform(delete("/community/admin/answers/" + aid).with(admin("990009")))
        .andExpect(status().isNoContent());

    assertThat(answers.findById(aid).orElseThrow().getStatus()).isEqualTo(ContentStatus.HIDDEN);
    assertThat(reputation.reputationOf(990004L)).isZero();
  }

  /**
   * ★수용된 답변을 내리면 질문의 연결을 풀어야 한다★
   * 그러지 않으면 질문이 "해결됨" 인데 답이 없는 상태가 되고, 그 값이 검색 문서에도 실린다.
   */
  @Test
  void adminDeleteOfAcceptedAnswerUnsolvesQuestion() throws Exception {
    long qid = createQuestion("990006");
    long aid = addAnswer(qid, "990007");

    mvc.perform(post("/community/answers/" + aid + "/accept")
            .with(jwt().jwt(j -> j.subject("990006"))))
        .andExpect(status().isOk());
    assertThat(questions.findById(qid).orElseThrow().isSolved()).isTrue();

    mvc.perform(delete("/community/admin/answers/" + aid).with(admin("990009")))
        .andExpect(status().isNoContent());

    CommunityQuestion q = questions.findById(qid).orElseThrow();
    assertThat(q.isSolved()).isFalse();
    assertThat(q.getAcceptedAnswerId()).isNull();

    mvc.perform(get("/community/questions/" + qid).with(jwt().jwt(j -> j.subject("990006"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.solved").value(false));
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
./gradlew test --tests '*ContentAdminMockMvcTest*' 2>&1 | tail -25
```

Expected: 3 개 모두 실패(매핑 없음 → 404).

- [ ] **Step 3: 구현한다**

`ContentAdminService.java`:

```java
package ai.devpath.community.post;

import ai.devpath.community.reputation.ReputationService;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 관리자 콘텐츠 내리기.
 *
 * <p>작성자 삭제({@code DELETED})와 달리 {@code HIDDEN} 은 규정 위반 판단이므로 그 콘텐츠로
 * 얻은 평판을 회수한다. 그리고 ★작성자에게 걸던 "채택된 답변은 못 지운다"(409) 제한을 받지
 * 않는다★ — 규정 위반 답변이 하필 채택된 상태일 수 있고, 그때 내리지 못하면 모더레이션이
 * 무력해진다. 대신 질문의 채택 연결을 풀어 준다.
 */
@Service
public class ContentAdminService {

  private final CommunityPostRepository posts;
  private final CommunityAnswerRepository answers;
  private final CommunityCommentRepository comments;
  private final CommunityQuestionRepository questions;
  private final CommunityPostTagRepository postTags;
  private final ReputationService reputation;
  private final PostIndexEventPublisher postIndexEvents;

  public ContentAdminService(CommunityPostRepository posts, CommunityAnswerRepository answers,
      CommunityCommentRepository comments, CommunityQuestionRepository questions,
      CommunityPostTagRepository postTags, ReputationService reputation,
      PostIndexEventPublisher postIndexEvents) {
    this.posts = posts; this.answers = answers; this.comments = comments;
    this.questions = questions; this.postTags = postTags; this.reputation = reputation;
    this.postIndexEvents = postIndexEvents;
  }

  @Transactional
  public void hidePost(long postId) {
    CommunityPost p = posts.findById(postId)
        .filter(found -> ContentStatus.PUBLISHED.equals(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("post " + postId));
    p.setStatus(ContentStatus.HIDDEN);
    posts.save(p);
    reputation.revokeAllForSource("POST", postId, tagIdsOfPost(postId));
    postIndexEvents.publish(postId, true);
  }

  @Transactional
  public void hideAnswer(long answerId) {
    CommunityAnswer a = answers.findById(answerId)
        .filter(found -> ContentStatus.PUBLISHED.equals(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("answer " + answerId));
    a.setStatus(ContentStatus.HIDDEN);
    if (a.isAccepted()) {
      a.setAccepted(false);
    }
    answers.save(a);

    long questionPostId = a.getQuestionId();
    reputation.revokeAllForSource("ANSWER", answerId, tagIdsOfPost(questionPostId));

    CommunityQuestion q = questions.findById(questionPostId).orElse(null);
    if (q != null && Long.valueOf(answerId).equals(q.getAcceptedAnswerId())) {
      q.setAcceptedAnswerId(null);
      q.setSolved(false);
      questions.save(q);
      // 검색 문서에 isSolved 가 실려 있다. 갱신하지 않으면 "해결됨" 인데 답이 없는 상태가 된다.
      postIndexEvents.publish(questionPostId, false);
    }
  }

  @Transactional
  public void hideComment(long commentId) {
    CommunityComment c = comments.findById(commentId)
        .filter(found -> ContentStatus.PUBLISHED.equals(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("comment " + commentId));
    c.setStatus(ContentStatus.HIDDEN);
    comments.save(c);
    // 댓글에는 투표 엔드포인트가 없어 회수할 평판이 없다. 색인 문서에도 댓글은 없다.
  }

  private List<Long> tagIdsOfPost(long postId) {
    return postTags.findByPostId(postId).stream().map(CommunityPostTag::getTagId).toList();
  }
}
```

`ContentAdminController.java`:

```java
package ai.devpath.community.post;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 관리자 콘텐츠 내리기. 권한은 경로가 가른다 —
 * SecurityConfig 가 {@code /community/admin/**} 에 hasRole("ADMIN") 을 이미 걸어 두었으므로
 * 메서드 안에서 role 을 파싱하지 않는다.
 *
 * <p>{@code AdminReportController} 는 {@code /community/admin/reports} 를 맡는다. 경로가 갈리므로
 * 매핑 충돌이 없다.
 */
@RestController
@RequestMapping("/community/admin")
public class ContentAdminController {

  private final ContentAdminService service;

  public ContentAdminController(ContentAdminService service) {
    this.service = service;
  }

  @DeleteMapping("/posts/{id}")
  public ResponseEntity<Void> hidePost(@PathVariable long id) {
    service.hidePost(id);
    return ResponseEntity.noContent().build();
  }

  @DeleteMapping("/answers/{id}")
  public ResponseEntity<Void> hideAnswer(@PathVariable long id) {
    service.hideAnswer(id);
    return ResponseEntity.noContent().build();
  }

  @DeleteMapping("/comments/{id}")
  public ResponseEntity<Void> hideComment(@PathVariable long id) {
    service.hideComment(id);
    return ResponseEntity.noContent().build();
  }
}
```

- [ ] **Step 4: 통과를 확인한다**

```bash
./gradlew test --tests '*ContentAdminMockMvcTest*' 2>&1 | tail -10
```

Expected: BUILD SUCCESSFUL, 3 개 통과.

- [ ] **Step 5: 색인 갱신 판별력을 실측한다**

`hideAnswer` 의 `postIndexEvents.publish(questionPostId, false);` 한 줄을 잠시 지우고 아웃박스를
확인한다.

```bash
./gradlew test --tests '*ContentAdminMockMvcTest*'
docker exec devpath-pg psql -U devpath -d devpath_citest -c \
  "SELECT count(*) FROM outbox WHERE aggregate_type='community_post' \
   AND payload LIKE '%\"deleted\":false%'"
```

Expected: 그 줄이 있을 때보다 건수가 줄어든다. ★MockMvc 테스트만으로는 이 한 줄을 잃어도
green 이므로 아웃박스를 직접 세어 확인한다.★ 확인 후 복구한다.

- [ ] **Step 6: 커밋**

```bash
git add src/main/java/ai/devpath/community/post/ContentAdminService.java \
        src/main/java/ai/devpath/community/post/ContentAdminController.java \
        src/test/java/ai/devpath/community/post/ContentAdminMockMvcTest.java
git commit -m "feat(content): 관리자 콘텐츠 내리기를 더한다

신고를 받아도 콘텐츠를 내릴 수단이 없었다 — resolve 는 RESOLVE|REJECT 뿐이고 상태를
바꾸지 않는다. HIDDEN 으로 내리고 그 콘텐츠로 얻은 평판을 회수한다.

관리자는 작성자에게 걸던 채택 제한(409)을 받지 않는다. 규정 위반 답변이 하필 채택된
상태일 수 있고 그때 못 내리면 모더레이션이 무력해진다. 대신 질문의 채택 연결을 풀고
색인을 갱신한다 — isSolved 가 검색 문서에 실려 있어 갱신하지 않으면 「해결됨인데 답이
없는」 검색 결과가 남는다.

권한은 경로가 가른다. SecurityConfig 가 /community/admin/** 에 ADMIN 을 이미 강제한다."
```

---

## Task 12: 관리자 리비전 조회와 활동 목록 정리

**Files:**
- Create: `src/main/java/ai/devpath/community/post/dto/RevisionView.java`
- Modify: `src/main/java/ai/devpath/community/post/ContentAdminService.java`
- Modify: `src/main/java/ai/devpath/community/post/ContentAdminController.java`
- Modify: `src/main/java/ai/devpath/community/post/ActivityController.java`
- Modify: `src/main/java/ai/devpath/community/post/CommunityPostRepository.java`
- Modify: `src/main/java/ai/devpath/community/post/CommunityAnswerRepository.java`
- Test: `src/test/java/ai/devpath/community/post/RevisionAndActivityMockMvcTest.java`

**Interfaces:**
- Consumes: `ContentRevisionRepository`(Task 5) · `ContentAdminService`(Task 11)
- Produces: `GET /community/admin/revisions?targetType=&targetId=` → `List<RevisionView>`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/community/post/RevisionAndActivityMockMvcTest.java`:

```java
package ai.devpath.community.post;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class RevisionAndActivityMockMvcTest {

  @Autowired MockMvc mvc;

  private static org.springframework.test.web.servlet.request.RequestPostProcessor admin(String id) {
    return jwt().jwt(j -> j.subject(id).claim("role", "ADMIN"));
  }

  private long createFreePost(String subject, String title) throws Exception {
    String body = mvc.perform(post("/community/posts")
            .with(jwt().jwt(j -> j.subject(subject)))
            .contentType("application/json")
            .content("{\"boardType\":\"FREE\",\"title\":\"" + title
                + "\",\"bodyMd\":\"본문\",\"tags\":[]}"))
        .andExpect(status().isCreated())
        .andReturn().getResponse().getContentAsString();
    return com.jayway.jsonpath.JsonPath.parse(body).read("$.id", Long.class);
  }

  @Test
  void adminCanReadRevisionsNewestFirst() throws Exception {
    long id = createFreePost("991001", "원제목");

    mvc.perform(put("/community/posts/" + id).with(jwt().jwt(j -> j.subject("991001")))
            .contentType("application/json")
            .content("{\"title\":\"두번째\",\"bodyMd\":\"두번째본문\"}"))
        .andExpect(status().isOk());
    mvc.perform(put("/community/posts/" + id).with(jwt().jwt(j -> j.subject("991001")))
            .contentType("application/json")
            .content("{\"title\":\"세번째\",\"bodyMd\":\"세번째본문\"}"))
        .andExpect(status().isOk());

    mvc.perform(get("/community/admin/revisions")
            .param("targetType", "POST").param("targetId", String.valueOf(id))
            .with(admin("991009")))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(2))
        .andExpect(jsonPath("$[0].title").value("두번째"))
        .andExpect(jsonPath("$[1].title").value("원제목"));
  }

  @Test
  void nonAdminCannotReadRevisions() throws Exception {
    long id = createFreePost("991002", "제목");

    mvc.perform(get("/community/admin/revisions")
            .param("targetType", "POST").param("targetId", String.valueOf(id))
            .with(jwt().jwt(j -> j.subject("991003"))))
        .andExpect(status().isForbidden());
  }

  /**
   * ActivityController 는 제목이 아니라 개수를 낸다
   * ({@code ActivityView(long questionCount, long answerCount)}, 경로 {@code /community/me/activity}).
   * 삭제한 글이 개수에 남아 있으면 "지워지지 않았다" 고 읽힌다.
   */
  @Test
  void deletedPostDisappearsFromMyActivityCount() throws Exception {
    long id = createFreePost("991004", "활동에서사라질글");

    mvc.perform(get("/community/me/activity").with(jwt().jwt(j -> j.subject("991004"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.questionCount").value(1));

    mvc.perform(delete("/community/posts/" + id).with(jwt().jwt(j -> j.subject("991004"))))
        .andExpect(status().isNoContent());

    mvc.perform(get("/community/me/activity").with(jwt().jwt(j -> j.subject("991004"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.questionCount").value(0));
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
./gradlew test --tests '*RevisionAndActivityMockMvcTest*' 2>&1 | tail -25
```

Expected: 3 개 모두 실패.

- [ ] **Step 3: 구현한다**

`dto/RevisionView.java`:

```java
package ai.devpath.community.post.dto;

import java.time.Instant;

/**
 * 수정 이력 한 건. 최신순으로 낸다.
 *
 * <p>페이지네이션을 두지 않는다 — 한 콘텐츠의 수정 횟수는 실무상 작다.
 */
public record RevisionView(String targetType, long targetId, String title, String bodyMd,
    long editedBy, Instant createdAt) {}
```

`ContentAdminService.java` — 필드에 리포지토리를 더하고 조회 메서드를 추가한다.

생성자 파라미터와 필드에 다음을 더한다:
```java
  private final ContentRevisionRepository revisions;
```

생성자 시그니처 끝에 `ContentRevisionRepository revisions` 를 더하고 본문에
`this.revisions = revisions;` 를 더한다.

메서드를 추가한다:
```java
  @Transactional(readOnly = true)
  public List<RevisionView> revisionsOf(String targetType, long targetId) {
    return revisions.findByTargetTypeAndTargetIdOrderByCreatedAtDesc(targetType, targetId).stream()
        .map(r -> new RevisionView(r.getTargetType(), r.getTargetId(), r.getTitle(),
            r.getBodyMd(), r.getEditedBy(), r.getCreatedAt()))
        .toList();
  }
```

import 를 더한다:
```java
import ai.devpath.community.post.dto.RevisionView;
```

`ContentAdminController.java` — 매핑을 추가한다.

import 추가:
```java
import ai.devpath.community.post.dto.RevisionView;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
```

메서드 추가:
```java
  @GetMapping("/revisions")
  public ResponseEntity<List<RevisionView>> revisions(
      @RequestParam String targetType, @RequestParam long targetId) {
    return ResponseEntity.ok(service.revisionsOf(targetType, targetId));
  }
```

`ActivityController` 는 목록이 아니라 **개수**를 낸다. 따라서 스트림 필터가 아니라 **상태를 포함한
카운트 쿼리**로 바꾼다.

`CommunityPostRepository.java` — 인터페이스에 메서드를 더한다:

```java
  long countByAuthorIdAndStatus(Long authorId, String status);
```

`CommunityAnswerRepository.java` — 인터페이스에 메서드를 더한다:

```java
  long countByAuthorIdAndAiGeneratedFalseAndStatus(Long authorId, String status);
```

`ActivityController.java` — `get` 의 반환문을 바꾼다.

바꾸기 전:
```java
    return new ActivityView(
        posts.countByAuthorId(uid), answers.countByAuthorIdAndAiGeneratedFalse(uid));
```

바꾼 뒤:
```java
    // 지운 글·답변은 내 활동에서도 빠진다. 남아 있으면 "지워지지 않았다" 고 읽힌다.
    return new ActivityView(
        posts.countByAuthorIdAndStatus(uid, ContentStatus.PUBLISHED),
        answers.countByAuthorIdAndAiGeneratedFalseAndStatus(uid, ContentStatus.PUBLISHED));
```


- [ ] **Step 4: 통과를 확인한다**

```bash
./gradlew test --tests '*RevisionAndActivityMockMvcTest*' 2>&1 | tail -10
```

Expected: BUILD SUCCESSFUL, 3 개 통과.

- [ ] **Step 5: 전체 스위트를 돌린다**

```bash
./gradlew test 2>&1 | tail -20
grep -ho 'tests="[0-9]*"' build/test-results/test/*.xml \
  | grep -o '[0-9]*' | paste -sd+ | bc
```

Expected: BUILD SUCCESSFUL. 총 실행 건수가 착수 전보다 크게 늘어 있어야 한다
(`bc` 가 없으면 `awk '{s+=$1} END {print s}'` 로 대체한다).

- [ ] **Step 6: 커밋**

```bash
git add src/main/java/ai/devpath/community/post/dto/RevisionView.java \
        src/main/java/ai/devpath/community/post/ContentAdminService.java \
        src/main/java/ai/devpath/community/post/ContentAdminController.java \
        src/main/java/ai/devpath/community/post/ActivityController.java \
        src/main/java/ai/devpath/community/post/CommunityPostRepository.java \
        src/main/java/ai/devpath/community/post/CommunityAnswerRepository.java \
        src/test/java/ai/devpath/community/post/RevisionAndActivityMockMvcTest.java
git commit -m "feat(content): 관리자 리비전 조회와 활동 목록 정리를 더한다

이력을 쌓아만 두면 쓸 데가 없다. 신고 처리 시 「답변 받고 질문을 통째로 바꿨는가」를
확인할 근거가 되도록 관리자에게만 연다.

내 활동 목록에서 삭제한 글·답변을 뺀다 — 지운 것이 남아 있으면 「지워지지 않았다」고
읽힌다."
```

---

## Self-Review

### 1. 스펙 커버리지

| 스펙 절 | 태스크 |
|---|---|
| §3 스키마(컬럼·CHECK·리비전 테이블) | Task 1 |
| §4 작성자 엔드포인트 6 개 | Task 6(글 수정) · 7(글 삭제) · 8(답변) · 9(댓글) |
| §4 관리자 엔드포인트 4 개 | Task 11(삭제 3) · 12(리비전 조회) |
| §4 읽기 경로 수정 4 곳 | Task 4(3 곳) · 8·9(비석 매핑) |
| §4 비석 표현 | Task 8(답변) · 9(댓글) |
| §5 수정 규칙(작성자·삭제된 것 불가·시간 제한 없음·no-op 비기록) | Task 5(no-op) · 6 · 8 · 9 |
| §5 삭제 규칙(재삭제 404 · 수용 답변 409) | Task 7 · 8 |
| §5 자식 미전파 + 우회 차단 | Task 4 · 7 |
| §5 관리자는 수용 제한 면제 + 연결 정리 | Task 11 |
| §5 신고 상호작용(삭제 대상 404 · 신고 자동 종결 안 함) | Task 4(404). **자동 종결하지 않는다는 것은 코드를 더하지 않는 결정이므로 별도 태스크가 없다.** |
| §5 활동 목록 | Task 12 |
| §6 색인 호출 4 종 | Task 6(수정) · 7(삭제 true) · 11(수용 답변 갱신). **답변·댓글은 호출 없음이 정답이므로 코드가 없다.** |
| §6 평판 순합 회수 | Task 10 |
| §6 댓글 평판 없음 | Task 11(`hideComment` 주석) |
| §6 트랜잭션 경계 | 전 태스크의 `@Transactional` |
| §9 릴리스 제약 | Task 2(개발용 좌표 + 되돌릴 시점 주석) |

**갭 없음.** §7 프론트엔드와 §8 의 프론트 항목은 **2 부 계획**으로 분리했다.

### 2. 자리표시자 스캔

`TBD`·`TODO`·"적절히"·"비슷하게" 없음. 모든 코드 단계에 실제 코드가 있다.

★**자체 검토가 실제 결함 하나를 잡았다.**★ 초판 Task 12 에는 "`ActivityController` 를 읽고 맞춰라"
는 조사 단계가 있었다. 계획을 다 쓰고 실제로 읽어 보니 그 컨트롤러는 **목록이 아니라 개수를 내고**
(`ActivityView(long questionCount, long answerCount)`) **경로도 `/community/me/activity`** 였다.
초판의 테스트는 `/community/activity` 에서 `$..title` 을 단언하고 있었으니 **경로와 응답 형태가 둘 다
틀렸다.** 조사 단계를 없애고 카운트 쿼리(`countByAuthorIdAndStatus` ·
`countByAuthorIdAndAiGeneratedFalseAndStatus`) 기반의 실제 코드로 교체했다.

**그 밖에 실측으로 확인한 가정들** — `ConflictException`→409 · `ForbiddenException`→403 ·
`NotFoundException`→404 · `IllegalArgumentException`→`VALIDATION_FAILED`(400, shared
`ApiExceptionHandler` 39 행) · `getBodyHtml()` 이 세 엔티티에 모두 존재 ·
`CommunityQuestion.setPostId` 존재. 전부 계획이 쓴 대로였다.


### 3. 타입 정합성

- `ContentStatus.PUBLISHED/DELETED/HIDDEN` — Task 3 에서 정의, Task 4·6·7·8·9·11·12 에서 사용. 일치.
- `ContentRevisionRecorder.record(String, long, String, String, String, long) → boolean` — Task 5 정의, Task 6·8·9 사용. 인자 순서 일치.
- `ContentRevisionRepository.findByTargetTypeAndTargetIdOrderByCreatedAtDesc(String, Long)` — Task 5 정의, Task 5·6 테스트와 Task 12 사용. 일치.
- `AnswerView`(7 필드, `deleted` 마지막) — Task 8 에서 변경, `QuestionService`·`AnswerService` 양쪽 갱신. `AnswerView.tombstone(long, int)` 일치.
- `CommentView`(6 필드, `deleted` 마지막) — Task 9 에서 변경, `CommentService.toView` 하나로 모아 두 경로가 같은 규칙을 쓴다. `CommentView.tombstone(long, int, Instant)` 일치.
- `ReputationService.revokeAllForSource(String, long, List<Long>)` — Task 10 정의, Task 11 사용. 일치.
- `ReputationEventRepository.netBySource(String, Long)` — Task 10 정의·사용. `@Param` 이름 일치.
- 예외: `ForbiddenException`·`NotFoundException` 은 `post` 패키지, `ConflictException` 은 `report` 패키지 — Task 8 에서 import 를 명시했다.

---

## 이 계획이 끝나면

- `community-svc` 브랜치 `feat/content-edit-delete` 에 커밋 11 개(Task 2~12)
- `devpath-shared` 브랜치 `feat/community-content-soft-delete` 에 커밋 1 개(Task 1)
- **두 브랜치 모두 아직 PR 을 열지 않는다.** shared `develop` 은 릴리스 PR #67 의 head 라, 머지
  시점을 사용자와 정한 뒤에 연다.
- 2 부(프론트엔드) 계획은 이 계획이 만든 실제 API 표면 위에서 작성한다.
