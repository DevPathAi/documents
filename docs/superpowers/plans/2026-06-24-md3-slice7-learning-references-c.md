# 슬라이스 #7 빌드 C — learning-svc 내부 콘텐츠 조회 + 임베딩 유사검색 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ai-svc 멘토(빌드 D)가 사용자 JWT 없이 학습 맥락·참고자료를 가져올 수 있도록 learning-svc에 **무인증 내부 경로**를 보강한다: (1) `GET /internal/contents/{id}`(콘텐츠 본문 요약 조회), (2) `POST /internal/contents/similar`(768벡터 임베딩 유사검색), (3) `ContentEmbeddingMatcher.matchAny`(track 술어 제거 변형), (4) `SecurityConfig`에 `/internal/**` permitAll.

**Architecture:** 네 변경 모두 learning-svc 단독. 기존 `GET /contents/{idOrSlug}`는 `@AuthenticationPrincipal Jwt` 필수라 ai-svc 내부 호출 불가 → 게이트웨이를 거치지 않는 내부 경로(`/internal/**`, JWT 면제, 네트워크 신뢰 경계)를 신규로 연다. 유사검색은 `ContentEmbeddingMatcher`(JdbcTemplate + pgvector `<=>` 코사인 거리)를 확장하되 기존 `match(track,…)`는 불변으로 두고 track 술어만 제거한 `matchAny`를 추가한다. 본문(body)은 멘토 context용이라 길이 상한으로 truncate한다.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Spring MVC(`@RestController`) · Spring Security(oauth2 resource server, HS256) · Spring Data JPA(`ContentRepository`) · JdbcTemplate + pgvector(768) · JUnit 5 · MockMvc · AssertJ.

## Global Constraints

- 대상 레포: `devpath-learning-svc` 단독. 설계서 [2026-06-24-md3-slice7-ai-mentor-design](../specs/2026-06-24-md3-slice7-ai-mentor-design.md) §5 learning-svc · §9 빌드 C · M-3 · M-4 · §2.3.
- **이 인터페이스를 정확히 produce(이름·타입 변경 금지). 소비자는 빌드 D(ai-svc `LearningClient`)다.** 시그니처를 임의 변경하지 않는다.
  - `GET /internal/contents/{id}` → `InternalContentView(long id, String slug, String title, String track, String body)`.
  - `POST /internal/contents/similar` body `SimilarQuery(List<Double> embedding, Integer limit, String track)`(`track` nullable) → `List<SimilarContent(long contentId, String slug, String title)>`.
  - `ContentEmbeddingMatcher.matchAny(List<Double> queryEmbedding, int limit)`.
- **기존 `ContentEmbeddingMatcher.match(String track, …)`는 변경 금지**(track 있을 때 사용). `matchAny`는 `match`에서 `c.track = ?` WHERE 술어만 제거한 변형(`ce.status='ACTIVE'`·`c.status='PUBLISHED'`·`order by ce.embedding <=> cast(? as vector), c.id desc` 동일).
- **본문 truncate 정책**: `InternalContentView.body`는 콘텐츠 `content_md`를 **최대 4000자**로 자른다(초과 시 앞 4000자 + `…`). 멘토 context 토큰 폭증 방지(설계 M-8·§5 "본문 body는 멘토 context용 — 길면 truncate").
- **유사검색 limit 클램프**: `SimilarQuery.limit`이 null이거나 1 미만이면 기본 3, 상한 10으로 클램프.
- **내부 경로는 게이트웨이가 라우트하지 않는다**(공개 노출 금지). 호출자(ai-svc)는 JWT subject의 userId로 소유 정합을 자체 확인한다. learning은 인가만 면제.
- Boot4: `@AutoConfigureMockMvc`=`org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc`, 모든 `@SpringBootTest` `@ActiveProfiles("test")`.
- 빌드/테스트: `./gradlew test`(fresh DB, pgvector 필요). Windows는 `.\gradlew.bat`. 테스트 DB는 `application-test.yml`의 `DB_URL`(기본 `jdbc:postgresql://localhost:5432/devpath`) — fresh DB는 `$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"`로 지정.
- 신규 작업 브랜치는 `develop`에서 분기. 빌드 A(shared `ai_mentor_sessions`)는 본 빌드와 스키마 의존이 없으나 슬라이스 순서상 A 머지 후 시작 권장.

---

## File Structure

- Create: `src/main/java/ai/devpath/learning/content/InternalContentView.java` — 내부 콘텐츠 조회 응답 record.
- Create: `src/main/java/ai/devpath/learning/content/InternalContentController.java` — `GET /internal/contents/{id}`.
- Create: `src/main/java/ai/devpath/learning/content/InternalContentService.java` — id 조회 + body truncate.
- Create: `src/main/java/ai/devpath/learning/content/SimilarQuery.java` — 유사검색 요청 record.
- Create: `src/main/java/ai/devpath/learning/content/SimilarContent.java` — 유사검색 응답 record.
- Create: `src/main/java/ai/devpath/learning/content/InternalSimilarController.java` — `POST /internal/contents/similar`.
- Create: `src/main/java/ai/devpath/learning/content/InternalSimilarService.java` — limit 클램프 + matcher 호출 + 매핑.
- Modify: `src/main/java/ai/devpath/learning/path/ContentEmbeddingMatcher.java` — `matchAny(queryEmbedding, limit)` 추가(기존 `match` 불변).
- Modify: `src/main/java/ai/devpath/learning/config/SecurityConfig.java` — `/internal/**` permitAll.
- Create(test): `src/test/java/ai/devpath/learning/content/InternalContentControllerTest.java`.
- Create(test): `src/test/java/ai/devpath/learning/content/InternalSimilarControllerTest.java`.
- Create(test): `src/test/java/ai/devpath/learning/path/ContentEmbeddingMatcherMatchAnyTest.java`.
- Modify(test): `src/test/java/ai/devpath/learning/config/SecurityConfigTest.java` — `/internal/**` 무인증 접근 단언.

---

## Task 0: 작업 브랜치

- [ ] **Step 1: 브랜치 분기 + 최신 shared**

```powershell
cd devpath-learning-svc
git switch develop
git pull
git switch -c feat/slice7-learning-internal-references
.\gradlew.bat --refresh-dependencies test --tests "ai.devpath.learning.config.SecurityConfigTest"
```

Expected: 기존 `SecurityConfigTest` 2케이스 PASS. 베이스라인·DB 접속 확인.

> fresh DB가 필요하면 먼저 `$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"`를 설정한다. 이하 모든 테스트 명령에 동일 적용.

---

## Task 1: `ContentEmbeddingMatcher.matchAny` (track 술어 제거 변형)

**Files:**
- Modify: `src/main/java/ai/devpath/learning/path/ContentEmbeddingMatcher.java`
- Test: `src/test/java/ai/devpath/learning/path/ContentEmbeddingMatcherMatchAnyTest.java`

**Interfaces:**
- Produces(빌드 D·`InternalSimilarService`가 의존): `List<MatchedContent> matchAny(List<Double> queryEmbedding, int limit)` — `content_embeddings ce join contents c`(`ce.status='ACTIVE'`·`c.status='PUBLISHED'`, **track 무관**) `order by ce.embedding <=> cast(? as vector), c.id desc limit ?`.
- Consumes: `JdbcTemplate`(기존), `toVectorLiteral`(기존 private, 768 검증 재사용), `MatchedContent`(기존 record).
- **불변**: 기존 `match(String track, …)`는 1바이트도 바꾸지 않는다.

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/learning/path/ContentEmbeddingMatcherMatchAnyTest.java`:

```java
package ai.devpath.learning.path;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;

@SpringBootTest
@ActiveProfiles("test")
@Sql(statements = "TRUNCATE content_embeddings, contents RESTART IDENTITY CASCADE",
    executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
@Sql(value = "/seed/content_md2_seed.sql", executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
@Sql(statements = "TRUNCATE content_embeddings, contents RESTART IDENTITY CASCADE",
    executionPhase = Sql.ExecutionPhase.AFTER_TEST_METHOD)
class ContentEmbeddingMatcherMatchAnyTest {

  @Autowired ContentEmbeddingMatcher matcher;
  @Autowired JdbcTemplate jdbc;

  @Test
  void matchAnyReturnsPublishedContentAcrossTracks() {
    List<MatchedContent> result = matcher.matchAny(Collections.nCopies(768, 0.08), 5);

    assertThat(result).hasSize(5);
    assertThat(result).allSatisfy(match -> {
      String status = jdbc.queryForObject(
          "select status from contents where id = ?", String.class, match.contentId());
      assertThat(status).isEqualTo("PUBLISHED");
    });
  }

  @Test
  void matchAnyIsNotRestrictedToASingleTrack() {
    List<MatchedContent> result = matcher.matchAny(Collections.nCopies(768, 0.08), 50);

    long distinctTracks = result.stream()
        .map(match -> jdbc.queryForObject(
            "select track from contents where id = ?", String.class, match.contentId()))
        .distinct()
        .count();
    assertThat(distinctTracks).isGreaterThan(1);
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.path.ContentEmbeddingMatcherMatchAnyTest"
```

Expected: 컴파일 실패(`matchAny` 메서드 없음) → FAIL.

- [ ] **Step 3: `matchAny` 구현**

`src/main/java/ai/devpath/learning/path/ContentEmbeddingMatcher.java`. 기존 `match` 메서드 **바로 아래**, `toVectorLiteral` **위**에 추가:

```java
  public List<MatchedContent> matchAny(List<Double> queryEmbedding, int limit) {
    String vector = toVectorLiteral(queryEmbedding);
    String sql = """
        select c.id, c.slug, c.title, ce.embedding <=> cast(? as vector) as distance
        from content_embeddings ce
        join contents c on c.id = ce.content_id
        where ce.status = 'ACTIVE'
          and c.status = 'PUBLISHED'
        order by ce.embedding <=> cast(? as vector), c.id desc
        limit ?
        """;
    return jdbc.query(sql, (rs, rowNum) -> new MatchedContent(
        rs.getLong("id"),
        rs.getString("slug"),
        rs.getString("title"),
        rs.getDouble("distance")), vector, vector, limit);
  }
```

> `match`와 차이는 `and c.track = ?` 한 줄 제거 + 바인딩에서 `track` 인자 제거(`vector, vector, limit`). 나머지(코사인 거리·정렬·tie-break `c.id desc`·`MatchedContent` 매핑)는 동일.

- [ ] **Step 4: 통과 확인(fresh DB)**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.path.ContentEmbeddingMatcherMatchAnyTest"
```

Expected: 두 케이스 PASS. 기존 `ContentEmbeddingMatcherSeedTest`(track 필터)도 무영향(같은 클래스 변경 없음).

- [ ] **Step 5: 커밋**

```powershell
git add src/main/java/ai/devpath/learning/path/ContentEmbeddingMatcher.java src/test/java/ai/devpath/learning/path/ContentEmbeddingMatcherMatchAnyTest.java
git commit -m "feat(learning): ContentEmbeddingMatcher.matchAny for track-agnostic similarity (slice7 C)"
```

---

## Task 2: `GET /internal/contents/{id}` — 내부 콘텐츠 본문 조회 + SecurityConfig

**Files:**
- Create: `src/main/java/ai/devpath/learning/content/InternalContentView.java`
- Create: `src/main/java/ai/devpath/learning/content/InternalContentService.java`
- Create: `src/main/java/ai/devpath/learning/content/InternalContentController.java`
- Modify: `src/main/java/ai/devpath/learning/config/SecurityConfig.java`
- Test: `src/test/java/ai/devpath/learning/content/InternalContentControllerTest.java`
- Test: `src/test/java/ai/devpath/learning/config/SecurityConfigTest.java`

**Interfaces:**
- Produces(빌드 D·ai-svc `LearningClient`가 의존): `GET /internal/contents/{id}` → 200 `InternalContentView(long id, String slug, String title, String track, String body)`(PUBLISHED만) / 404(미존재·DRAFT). **무인증**.
- Consumes: `ContentRepository.findByIdAndStatus(Long, "PUBLISHED")`(기존), `Content.getContentMd()`(body 원본).
- body는 최대 4000자 truncate.

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/learning/content/InternalContentControllerTest.java`:

```java
package ai.devpath.learning.content;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class InternalContentControllerTest {

  @Autowired MockMvc mvc;
  @Autowired JdbcTemplate jdbc;

  @BeforeEach
  void reset() {
    jdbc.execute("""
        TRUNCATE user_content_progress, path_weekly_tasks, path_milestones,
          learning_paths, content_embeddings, contents
        RESTART IDENTITY CASCADE
        """);
  }

  @Test
  void returnsPublishedContentBodyWithoutAuth() throws Exception {
    long id = seedContent("spring-tx-boundary", "BACKEND_SPRING", "PUBLISHED",
        "## Transaction Boundary\nRead this body.");

    mvc.perform(get("/internal/contents/" + id))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.id").value(id))
        .andExpect(jsonPath("$.slug").value("spring-tx-boundary"))
        .andExpect(jsonPath("$.title").value("spring-tx-boundary"))
        .andExpect(jsonPath("$.track").value("BACKEND_SPRING"))
        .andExpect(jsonPath("$.body").value("## Transaction Boundary\nRead this body."));
  }

  @Test
  void truncatesLongBodyTo4000Chars() throws Exception {
    String longBody = "x".repeat(5000);
    long id = seedContent("long-body", "BACKEND_SPRING", "PUBLISHED", longBody);

    mvc.perform(get("/internal/contents/" + id))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.body").value(("x".repeat(4000)) + "…"));
  }

  @Test
  void missingContentReturns404() throws Exception {
    mvc.perform(get("/internal/contents/999999999"))
        .andExpect(status().isNotFound());
  }

  @Test
  void draftContentReturns404() throws Exception {
    long id = seedContent("draft-content", "BACKEND_SPRING", "DRAFT", "## Draft");

    mvc.perform(get("/internal/contents/" + id))
        .andExpect(status().isNotFound());
  }

  private long seedContent(String slug, String track, String status, String markdown) {
    return jdbc.queryForObject("""
        insert into contents(slug, title, track, content_md, estimated_minutes, difficulty,
          bloom_level, concept_tags, status)
        values (?, ?, ?, ?, 10, 0.4, 'APPLY', cast('[\"tag\"]' as jsonb), ?)
        returning id
        """, Long.class, slug, slug, track, markdown, status);
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.content.InternalContentControllerTest"
```

Expected: 컴파일 실패(타입 없음) 또는 401(엔드포인트/permitAll 없음) → FAIL.

- [ ] **Step 3: View + Service + Controller + SecurityConfig 구현**

`src/main/java/ai/devpath/learning/content/InternalContentView.java`:

```java
package ai.devpath.learning.content;

public record InternalContentView(long id, String slug, String title, String track, String body) {
}
```

`src/main/java/ai/devpath/learning/content/InternalContentService.java`:

```java
package ai.devpath.learning.content;

import ai.devpath.learning.path.Content;
import ai.devpath.learning.path.ContentRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** ai-svc 멘토가 사용자 JWT 없이 콘텐츠 본문을 가져오는 내부 조회(게이트웨이 미경유). */
@Service
public class InternalContentService {
  private static final String PUBLISHED = "PUBLISHED";
  static final int MAX_BODY_CHARS = 4000;

  private final ContentRepository contents;

  public InternalContentService(ContentRepository contents) {
    this.contents = contents;
  }

  @Transactional(readOnly = true)
  public InternalContentView get(long id) {
    Content content = contents.findByIdAndStatus(id, PUBLISHED)
        .orElseThrow(() -> new ContentNotFoundException(String.valueOf(id)));
    return new InternalContentView(
        content.getId(),
        content.getSlug(),
        content.getTitle(),
        content.getTrack(),
        truncate(content.getContentMd()));
  }

  private String truncate(String body) {
    if (body == null) return "";
    if (body.length() <= MAX_BODY_CHARS) return body;
    return body.substring(0, MAX_BODY_CHARS) + "…";
  }
}
```

`src/main/java/ai/devpath/learning/content/InternalContentController.java`:

```java
package ai.devpath.learning.content;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 서비스 간 내부 조회(게이트웨이 미경유). ai-svc 멘토가 콘텐츠 본문을 context로 가져온다. */
@RestController
@RequestMapping("/internal/contents")
public class InternalContentController {
  private final InternalContentService service;

  public InternalContentController(InternalContentService service) {
    this.service = service;
  }

  @GetMapping("/{id}")
  public InternalContentView get(@PathVariable long id) {
    return service.get(id);
  }
}
```

`SecurityConfig.java` — `authorizeHttpRequests` 람다의 `permitAll` 매처에 `/internal/**`을 추가(`anyRequest()` 앞):

```java
        .authorizeHttpRequests(authorize -> authorize
            .requestMatchers("/onboarding/assessments/guest/**", "/actuator/health").permitAll()
            .requestMatchers("/internal/**").permitAll()
            .anyRequest().authenticated())
```

> `ContentNotFoundException`은 기존 `GlobalExceptionHandler`가 404(`errorCode:CONTENT_NOT_FOUND`)로 매핑한다 — 추가 핸들러 불필요. 내부 조회는 errorCode 본문을 검증하지 않고 상태코드(404)만 단언.

- [ ] **Step 4: 통과 확인(fresh DB)**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.content.InternalContentControllerTest"
```

Expected: 4케이스 PASS.

- [ ] **Step 5: SecurityConfigTest에 내부 경로 무인증 단언 추가**

`src/test/java/ai/devpath/learning/config/SecurityConfigTest.java`의 클래스 닫는 `}` 직전에 추가:

```java
  @Test
  void internalPathIsPublic() throws Exception {
    // /internal/** is permitAll; missing content resolves to 404 (not 401)
    mvc.perform(get("/internal/contents/999999999")).andExpect(status().isNotFound());
  }
```

- [ ] **Step 6: 통과 확인 + 커밋**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.config.SecurityConfigTest"
git add src/main/java/ai/devpath/learning/content/InternalContentView.java src/main/java/ai/devpath/learning/content/InternalContentService.java src/main/java/ai/devpath/learning/content/InternalContentController.java src/main/java/ai/devpath/learning/config/SecurityConfig.java src/test/java/ai/devpath/learning/content/InternalContentControllerTest.java src/test/java/ai/devpath/learning/config/SecurityConfigTest.java
git commit -m "feat(learning): GET /internal/contents/{id} unauthenticated body read for mentor context (slice7 C)"
```

Expected: `SecurityConfigTest` 3케이스(`healthIsPublic`·`protectedAssessmentRequiresAuth`·`internalPathIsPublic`) PASS.

---

## Task 3: `POST /internal/contents/similar` — 임베딩 유사검색

**Files:**
- Create: `src/main/java/ai/devpath/learning/content/SimilarQuery.java`
- Create: `src/main/java/ai/devpath/learning/content/SimilarContent.java`
- Create: `src/main/java/ai/devpath/learning/content/InternalSimilarService.java`
- Create: `src/main/java/ai/devpath/learning/content/InternalSimilarController.java`
- Test: `src/test/java/ai/devpath/learning/content/InternalSimilarControllerTest.java`

**Interfaces:**
- Produces(빌드 D·ai-svc `LearningClient`가 의존): `POST /internal/contents/similar` body `SimilarQuery(List<Double> embedding, Integer limit, String track)` → 200 `List<SimilarContent(long contentId, String slug, String title)>`. **무인증**(Task 2의 `/internal/**` permitAll 적용).
- 동작: `track` 비어있지 않으면 `ContentEmbeddingMatcher.match(track, embedding, limit)`(track 필터), null/blank이면 `matchAny(embedding, limit)`(전체 PUBLISHED·ACTIVE). limit은 null/<1 → 3, 상한 10.
- Consumes: `ContentEmbeddingMatcher.match`/`matchAny`(Task 1), `MatchedContent`(기존). 벡터 768 검증은 matcher의 `toVectorLiteral`이 수행(`PathContractException` → 기존 핸들러 502).

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/learning/content/InternalSimilarControllerTest.java`:

```java
package ai.devpath.learning.content;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class InternalSimilarControllerTest {

  @Autowired MockMvc mvc;
  @Autowired JdbcTemplate jdbc;
  @Autowired JsonMapper jsonMapper;

  @BeforeEach
  void reset() {
    jdbc.execute("TRUNCATE content_embeddings, contents RESTART IDENTITY CASCADE");
  }

  @Test
  void similarWithoutTrackReturnsAcrossTracks() throws Exception {
    long backend = seedContentWithEmbedding("backend-one", "BACKEND_SPRING", 0.10);
    long frontend = seedContentWithEmbedding("frontend-one", "FRONTEND_REACT", 0.11);

    String body = jsonMapper.writeValueAsString(
        new SimilarQuery(Collections.nCopies(768, 0.10), 5, null));

    mvc.perform(post("/internal/contents/similar")
            .contentType(MediaType.APPLICATION_JSON)
            .content(body))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(2))
        .andExpect(jsonPath("$[*].contentId",
            org.hamcrest.Matchers.containsInAnyOrder((int) backend, (int) frontend)));
  }

  @Test
  void similarWithTrackFiltersToThatTrack() throws Exception {
    seedContentWithEmbedding("backend-one", "BACKEND_SPRING", 0.10);
    long frontend = seedContentWithEmbedding("frontend-one", "FRONTEND_REACT", 0.11);

    String body = jsonMapper.writeValueAsString(
        new SimilarQuery(Collections.nCopies(768, 0.11), 5, "FRONTEND_REACT"));

    mvc.perform(post("/internal/contents/similar")
            .contentType(MediaType.APPLICATION_JSON)
            .content(body))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(1))
        .andExpect(jsonPath("$[0].contentId").value((int) frontend))
        .andExpect(jsonPath("$[0].slug").value("frontend-one"));
  }

  @Test
  void nullLimitDefaultsAndClampsToTen() throws Exception {
    for (int i = 0; i < 15; i++) {
      seedContentWithEmbedding("bulk-" + i, "BACKEND_SPRING", 0.10 + i * 0.0001);
    }

    String nullLimitBody = jsonMapper.writeValueAsString(
        new SimilarQuery(Collections.nCopies(768, 0.10), null, null));
    mvc.perform(post("/internal/contents/similar")
            .contentType(MediaType.APPLICATION_JSON)
            .content(nullLimitBody))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(3));

    String bigLimitBody = jsonMapper.writeValueAsString(
        new SimilarQuery(Collections.nCopies(768, 0.10), 100, null));
    mvc.perform(post("/internal/contents/similar")
            .contentType(MediaType.APPLICATION_JSON)
            .content(bigLimitBody))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").value(10));
  }

  /** Seeds one PUBLISHED content + one ACTIVE 768-dim embedding (constant vector). */
  private long seedContentWithEmbedding(String slug, String track, double value) {
    long id = jdbc.queryForObject("""
        insert into contents(slug, title, track, content_md, estimated_minutes, difficulty,
          bloom_level, concept_tags, status)
        values (?, ?, ?, '## Body', 10, 0.4, 'APPLY', cast('[\"tag\"]' as jsonb), 'PUBLISHED')
        returning id
        """, Long.class, slug, slug, track);
    String vector = "[" + String.join(",", Collections.nCopies(768, Double.toString(value))) + "]";
    jdbc.update("""
        insert into content_embeddings(content_id, chunk_index, chunk_text, embedding, chunk_hash, status)
        values (?, 0, 'chunk', cast(? as vector), 'hash-' || ?, 'ACTIVE')
        """, id, vector, slug);
    return id;
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.content.InternalSimilarControllerTest"
```

Expected: 컴파일 실패(`SimilarQuery`/`SimilarContent` 없음) → FAIL.

- [ ] **Step 3: records + Service + Controller 구현**

`src/main/java/ai/devpath/learning/content/SimilarQuery.java`:

```java
package ai.devpath.learning.content;

import java.util.List;

public record SimilarQuery(List<Double> embedding, Integer limit, String track) {
}
```

`src/main/java/ai/devpath/learning/content/SimilarContent.java`:

```java
package ai.devpath.learning.content;

public record SimilarContent(long contentId, String slug, String title) {
}
```

`src/main/java/ai/devpath/learning/content/InternalSimilarService.java`:

```java
package ai.devpath.learning.content;

import ai.devpath.learning.path.ContentEmbeddingMatcher;
import ai.devpath.learning.path.MatchedContent;
import java.util.List;
import org.springframework.stereotype.Service;

/** 멘토 참고자료: 질문 임베딩(768)으로 유사 콘텐츠를 찾는 내부 검색(ai-svc가 벡터를 전달). */
@Service
public class InternalSimilarService {
  private static final int DEFAULT_LIMIT = 3;
  private static final int MAX_LIMIT = 10;

  private final ContentEmbeddingMatcher matcher;

  public InternalSimilarService(ContentEmbeddingMatcher matcher) {
    this.matcher = matcher;
  }

  public List<SimilarContent> search(SimilarQuery query) {
    int limit = clampLimit(query.limit());
    List<MatchedContent> matched = hasTrack(query.track())
        ? matcher.match(query.track(), query.embedding(), limit)
        : matcher.matchAny(query.embedding(), limit);
    return matched.stream()
        .map(m -> new SimilarContent(m.contentId(), m.slug(), m.title()))
        .toList();
  }

  private boolean hasTrack(String track) {
    return track != null && !track.isBlank();
  }

  private int clampLimit(Integer limit) {
    if (limit == null || limit < 1) return DEFAULT_LIMIT;
    return Math.min(limit, MAX_LIMIT);
  }
}
```

`src/main/java/ai/devpath/learning/content/InternalSimilarController.java`:

```java
package ai.devpath.learning.content;

import java.util.List;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 서비스 간 내부 유사검색(게이트웨이 미경유). body가 768벡터라 GET 아님 POST. */
@RestController
@RequestMapping("/internal/contents")
public class InternalSimilarController {
  private final InternalSimilarService service;

  public InternalSimilarController(InternalSimilarService service) {
    this.service = service;
  }

  @PostMapping("/similar")
  public List<SimilarContent> similar(@RequestBody SimilarQuery query) {
    return service.search(query);
  }
}
```

- [ ] **Step 4: 통과 확인(fresh DB)**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.content.InternalSimilarControllerTest"
```

Expected: 3케이스 PASS. (`/internal/**` permitAll은 Task 2에서 이미 추가됨 → 무인증 접근 200.)

- [ ] **Step 5: 커밋**

```powershell
git add src/main/java/ai/devpath/learning/content/SimilarQuery.java src/main/java/ai/devpath/learning/content/SimilarContent.java src/main/java/ai/devpath/learning/content/InternalSimilarService.java src/main/java/ai/devpath/learning/content/InternalSimilarController.java src/test/java/ai/devpath/learning/content/InternalSimilarControllerTest.java
git commit -m "feat(learning): POST /internal/contents/similar embedding search for mentor references (slice7 C)"
```

---

## Task 4: 전체 회귀 + develop PR

- [ ] **Step 1: 전체 테스트(fresh DB)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat clean test
```

Expected: 전 단위/통합 PASS, 회귀 없음. 특히 기존 `ContentControllerTest`·`ContentEmbeddingMatcherSeedTest`·`SecurityConfigTest`가 그대로 통과(기존 `match`·`/contents/**` 인증 경로 불변).

- [ ] **Step 2: PR 생성(develop 대상)**

```powershell
git push -u origin feat/slice7-learning-internal-references
gh pr create --base develop --title "feat(learning): 멘토 내부 콘텐츠 조회·임베딩 유사검색(슬라이스 #7 빌드 C)" --body "GET /internal/contents/{id}(무인증 본문 4000자 truncate), POST /internal/contents/similar(768벡터, track 2-경로), ContentEmbeddingMatcher.matchAny(track 술어 제거), SecurityConfig /internal/** permitAll. 소비자=빌드 D ai-svc LearningClient. 설계서 docs/superpowers/specs/2026-06-24-md3-slice7-ai-mentor-design.md §5·§9·M-3·M-4"
```

- [ ] **Step 3: CI 녹색 확인 → 머지**

```powershell
gh pr checks --watch
gh pr merge --merge
```

Expected: learning-svc CI(build + test, pgvector 포함) 녹색. 앱/서비스라 main 릴리스는 슬라이스 마지막 통합 릴리스에서.

---

## Self-Review 메모(작성자)

- **Spec 커버리지**: 명세 4항목 = Task1(`matchAny`)·Task2(`GET /internal/contents/{id}` + SecurityConfig `/internal/**`)·Task3(`POST /internal/contents/similar` + `SimilarQuery`/`SimilarContent`). 설계 §5 learning-svc 4불릿·§9 빌드 C·M-3(내부 콘텐츠 조회 필수)·M-4(track 2-경로)·§2.3 전부 매핑.
- **인터페이스 정합(빌드 D 소비자)**: `InternalContentView(long id, String slug, String title, String track, String body)`·`SimilarQuery(List<Double> embedding, Integer limit, String track)`·`SimilarContent(long contentId, String slug, String title)`·`matchAny(List<Double>, int)` — 지시문 명세와 이름·타입 1:1 일치. record `long` primitive(명세대로) 사용.
- **기존 코드 불변 검증**: `match(String track,…)`는 미변경(Task1은 아래에 `matchAny` 추가만). `/contents/**`(JWT 필수) 경로·`ContentController`·`ContentService`·`GlobalExceptionHandler`는 손대지 않음. `SecurityConfig`는 `permitAll` 매처 1줄 추가만(기존 guest·health 매처 보존).
- **placeholder 없음**: 모든 코드/테스트/명령 실제값. truncate 4000·limit 클램프(3/10)·벡터 리터럴 조립은 실측 패턴(`ContentEmbeddingMatcher.toVectorLiteral`·`ContentService.clampLimit`) 미러.
- **truncate 정책 명시**: body 4000자 초과 시 앞 4000 + `…`(테스트 `truncatesLongBodyTo4000Chars`로 실증). 설계 "길면 truncate 정책 명시" 요구 충족.
- **track 2-경로 실증**: `similarWithoutTrackReturnsAcrossTracks`(matchAny)·`similarWithTrackFiltersToThatTrack`(match). null/blank track → matchAny.
- **테스트 패턴 미러**: `@SpringBootTest @AutoConfigureMockMvc @ActiveProfiles("test")` + Boot4 `webmvc.test.autoconfigure` import(`ContentControllerTest` 동일). matcher 테스트는 `ContentEmbeddingMatcherSeedTest`의 `@Sql` 시드 패턴 재사용, 유사검색 컨트롤러 테스트는 자체 768 상수벡터 시드(대형 픽스처 비의존). JSON 직렬화는 프로젝트가 쓰는 `tools.jackson.databind.json.JsonMapper`(Jackson 3, `ContentService` import 확인).
- **무인증 검증**: `InternalContentControllerTest`/`InternalSimilarControllerTest`는 `jwt()` 없이 호출 → permitAll 실증. `SecurityConfigTest.internalPathIsPublic`은 401이 아닌 404를 단언(permitAll이 적용돼 인가는 통과, 미존재라 404).
- **DB 의존**: pgvector 필요(`<=>` 코사인). 모든 테스트 fresh DB 명령에 `DB_URL` 지정 안내. `content_embeddings.embedding VECTOR(768)`·`status ACTIVE`/`contents.status PUBLISHED`(V202606181006 실측)와 정합.
- **에러 처리 위임**: `ContentNotFoundException`→404·`PathContractException`(벡터 차원 위반)→502는 기존 `GlobalExceptionHandler` 재사용(신규 핸들러 불요). 빌드 D가 벡터 차원을 항상 768로 보내므로 502는 비정상 경로 방어.
- **범위 경계**: 빌드 C(learning-svc)만. ai-svc `LearningClient`·gateway·frontend·shared는 다른 빌드. 코드 구현·다른 빌드·PR 머지 실행은 본 플랜 실행자(서브에이전트)의 몫이며, 본 문서는 작성만.
