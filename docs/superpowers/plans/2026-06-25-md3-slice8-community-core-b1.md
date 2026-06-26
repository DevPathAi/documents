# 빌드 B1 (community-svc 코어) — Q&A CRUD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** devpath-community-svc에 Q&A 코어(질문 CRUD·답변·채택·투표·태그 자동완성)를 TDD로 구현한다. 이벤트/유사질문(Outbox·AI 시드 consume·pgvector)은 빌드 B2.

**Architecture:** 설계서 [2026-06-25-md3-slice8-community-qna-design](../specs/2026-06-25-md3-slice8-community-qna-design.md) §5(community-svc B1). learning-svc `content`/`config` 패턴 미러. 패키지 `ai.devpath.community.post`(도메인) + `ai.devpath.community.config`(Security·예외). 서비스 자체 JWT 검증(HS256, gateway 엣지 동일 시크릿), `userId=jwt.getSubject()`, 채택은 OWNER.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Gradle KDSL · JPA(Hibernate) · PostgreSQL(shared 중앙 Flyway, 서비스는 validate) · JUnit 5 · MockMvc.

## Global Constraints

- **DB**: 마이그레이션은 shared 중앙(빌드 A 완료). community-svc는 `ddl-auto: validate`, `flyway.enabled: false`(application.yml 실측). 테이블은 `community_posts`·`community_questions`·`community_answers`·`community_votes`·`community_tags`·`community_post_tags`(빌드 A `V202606251001`).
- **테스트 DB**: 로컬 `docker compose`(postgres 5432). **기본 `devpath` DB는 구버전 → `DB_URL=jdbc:postgresql://localhost:5432/devpath_citest`로 실행**(빌드 A 교훈). `@SpringBootTest`/`@DataJpaTest`는 `@ActiveProfiles("test")`. fresh DB·CI 서비스 일치.
- **교차서비스 FK 금지**: `author_id`는 논리참조(platform). 엔티티에 users 연관 매핑 없음.
- **JWT**: `userId = Long.parseLong(jwt.getSubject())`. SecurityConfig는 learning-svc 미러(HS256 `devpath.auth.jwt-secret`).
- **브랜치**: community-svc는 develop 보유 → `feat/slice8-community-core`를 **develop에서 분기**, develop으로 PR(2단계). (shared와 다름.)
- **검증 명령**: `cd devpath-community-svc && ./gradlew test`(로컬은 위 DB_URL 필요). 빌드: `./gradlew build`.
- **도구 주의(이 세션)**: 도구 호출은 앞 텍스트 0으로 발행. PowerShell 분류기 불안정 시 Bash 사용.

---

## File Structure

`devpath-community-svc/src/main/java/ai/devpath/community/`:
- `config/SecurityConfig.java` — JWT 자원서버(learning 미러)
- `config/GlobalExceptionHandler.java` — 404/403/400 매핑
- `post/CommunityPost.java`·`CommunityQuestion.java`·`CommunityAnswer.java`·`CommunityVote.java`·`CommunityTag.java`·`CommunityPostTag.java`·`CommunityPostTagId.java` — 엔티티
- `post/*Repository.java` — JpaRepository 6종
- `post/QuestionService.java`·`AnswerService.java`·`VoteService.java`·`TagService.java` — 서비스
- `post/CommunityController.java` — REST
- `post/dto/` — `CreateQuestionRequest`·`QuestionDetailView`·`PostSummaryView`·`AnswerView`·`CreateAnswerRequest`·`VoteRequest`·`TagView`
- `post/NotFoundException.java`·`ForbiddenException.java` — 도메인 예외
- `application.yml` 보강(jwt secret), `build.gradle.kts`(security·oauth2 활성)

테스트 `src/test/java/ai/devpath/community/`: `CommunityContextTest`(기동), `post/CommunityRepositoryTest`(@DataJpaTest), `post/QnaMockMvcTest`(IT, 작성·목록·상세·답변·채택·투표·태그).

---

## Task B1-1: deps 활성화 + SecurityConfig + 컨텍스트 기동

**Files:**
- Modify: `devpath-community-svc/build.gradle.kts`(security·oauth2-resource-server 활성 + test deps)
- Modify: `devpath-community-svc/src/main/resources/application.yml`(jwt secret 추가)
- Create: `src/main/java/ai/devpath/community/config/SecurityConfig.java`
- Test: `src/test/java/ai/devpath/community/CommunityContextTest.java`, `src/test/resources/application-test.yml`

**Interfaces:**
- Produces: `SecurityConfig`(jwtDecoder HS256). 이후 모든 컨트롤러가 JWT 인증.

- [ ] **Step 1: build.gradle.kts — security/oauth2 활성 + test deps**

`dependencies` 블록에서 주석 해제/추가(learning-svc 미러, kafka·redis는 B2까지 미포함):

```kotlin
	implementation("org.springframework.boot:spring-boot-starter-security")
	implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
```

test deps 추가(기존 test 블록에):

```kotlin
	testImplementation("org.springframework.boot:spring-boot-starter-security-test")
	testImplementation("org.springframework.boot:spring-boot-starter-data-jpa-test")
	testImplementation("org.springframework.boot:spring-boot-flyway")
	testImplementation("org.flywaydb:flyway-core")
	testImplementation("org.flywaydb:flyway-database-postgresql")
```

- [ ] **Step 2: application.yml — jwt secret + test 프로파일**

`application.yml`에 추가(기존 spring/server/management 유지):

```yaml
devpath:
  auth:
    jwt-secret: ${DEVPATH_AUTH_JWT_SECRET:test-secret-please-change-min-32-bytes-long-0123456789}
```

Create `src/test/resources/application-test.yml`:

```yaml
spring:
  datasource:
    url: ${DB_URL:jdbc:postgresql://localhost:5432/devpath_citest}
    username: ${DB_USER:devpath}
    password: ${DB_PASSWORD:localdev}
  jpa:
    hibernate:
      ddl-auto: validate
devpath:
  auth:
    jwt-secret: test-secret-please-change-min-32-bytes-long-0123456789
```

- [ ] **Step 3: Write failing context test**

Create `CommunityContextTest.java`:

```java
package ai.devpath.community;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class CommunityContextTest {
  @Test
  void contextLoads() {}
}
```

Run: `cd devpath-community-svc && ./gradlew test --tests "ai.devpath.community.CommunityContextTest"` (DB_URL=devpath_citest)
Expected: FAIL — `SecurityConfig` 빈 없음/jwtDecoder 없음으로 컨텍스트 기동 실패(또는 보안 자동구성 누락).

- [ ] **Step 4: Write SecurityConfig (learning 미러)**

Create `config/SecurityConfig.java` — learning-svc `SecurityConfig` 구조 그대로, 단 permitAll은 `/actuator/health`만(커뮤니티는 게스트/internal 경로 B1 없음):

```java
package ai.devpath.community.config;

import java.nio.charset.StandardCharsets;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

  @Bean
  public SecretKey jwtSecretKey(
      @Value("${devpath.auth.jwt-secret:test-secret-please-change-min-32-bytes-long-0123456789}") String secret) {
    byte[] bytes = secret.getBytes(StandardCharsets.UTF_8);
    if (bytes.length < 32) {
      throw new IllegalStateException("JWT_SECRET must be >= 32 bytes (HS256), got " + bytes.length);
    }
    return new SecretKeySpec(bytes, "HmacSHA256");
  }

  @Bean
  public JwtDecoder jwtDecoder(SecretKey key) {
    return NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
  }

  @Bean
  public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
    http
        .csrf(csrf -> csrf.disable())
        .authorizeHttpRequests(authorize -> authorize
            .requestMatchers("/actuator/health").permitAll()
            .anyRequest().authenticated())
        .oauth2ResourceServer(rs -> rs.jwt(Customizer.withDefaults()));
    return http.build();
  }
}
```

- [ ] **Step 5: Run test → PASS**

Run: `./gradlew test --tests "ai.devpath.community.CommunityContextTest"` (DB_URL=devpath_citest)
Expected: PASS(컨텍스트 기동).

- [ ] **Step 6: Commit**

```bash
git add devpath-community-svc/build.gradle.kts devpath-community-svc/src/main/resources/application.yml \
  devpath-community-svc/src/main/java/ai/devpath/community/config/SecurityConfig.java \
  devpath-community-svc/src/test/java/ai/devpath/community/CommunityContextTest.java \
  devpath-community-svc/src/test/resources/application-test.yml
git commit -m "feat(community): deps(security/oauth2) 활성 + SecurityConfig + 컨텍스트 기동 (B1-1)"
```

---

## Task B1-2: 엔티티 6종 + 리포지토리 + JPA 매핑 검증

**Files:**
- Create: `post/CommunityPost.java`·`CommunityQuestion.java`·`CommunityAnswer.java`·`CommunityVote.java`·`CommunityTag.java`·`CommunityPostTag.java`·`CommunityPostTagId.java`
- Create: `post/CommunityPostRepository.java`·`CommunityQuestionRepository.java`·`CommunityAnswerRepository.java`·`CommunityVoteRepository.java`·`CommunityTagRepository.java`·`CommunityPostTagRepository.java`
- Test: `post/CommunityRepositoryTest.java`(@DataJpaTest)

**Interfaces:**
- Produces (B1-3~6·B2가 사용):
  - `CommunityPost`(id·authorId·boardType·title·bodyMd·bodyHtml·status·viewCount·upvoteCount·downvoteCount), getter/setter
  - `CommunityQuestion`(postId@Id·isSolved·acceptedAnswerId·learningContext). **`question_embedding`은 매핑 제외**(B2 JdbcTemplate UPDATE; validate는 미매핑 컬럼 허용).
  - `CommunityAnswer`(id·questionId·authorId·bodyMd·bodyHtml·isAiGenerated·isAccepted·upvoteCount)
  - `CommunityVote`(id·userId·targetType·targetId·value)
  - `CommunityTag`(id·name·postCount), `CommunityPostTag`(@IdClass postId·tagId)
  - Repos: `CommunityPostRepository extends JpaRepository<CommunityPost,Long>` 등. 쿼리 메서드는 B1-3~6에서 추가.

- [ ] **Step 1: Write failing @DataJpaTest**

Create `CommunityRepositoryTest.java`(엔티티 매핑·기본 저장 검증):

```java
package ai.devpath.community.post;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase.Replace;
import org.springframework.test.context.ActiveProfiles;

@DataJpaTest
@AutoConfigureTestDatabase(replace = Replace.NONE)
@ActiveProfiles("test")
class CommunityRepositoryTest {

  @Autowired CommunityPostRepository posts;
  @Autowired CommunityQuestionRepository questions;
  @Autowired CommunityAnswerRepository answers;
  @Autowired CommunityVoteRepository votes;
  @Autowired CommunityTagRepository tags;

  @Test
  void savesQuestionPostAnswerVoteTag() {
    CommunityPost p = new CommunityPost();
    p.setAuthorId(1L); p.setBoardType("QNA"); p.setTitle("t"); p.setBodyMd("b"); p.setStatus("PUBLISHED");
    p = posts.save(p);
    assertNotNull(p.getId());
    assertEquals(0, p.getUpvoteCount());

    CommunityQuestion q = new CommunityQuestion();
    q.setPostId(p.getId());
    questions.save(q);
    assertTrue(questions.findById(p.getId()).isPresent());

    CommunityAnswer a = new CommunityAnswer();
    a.setQuestionId(p.getId()); a.setAuthorId(2L); a.setBodyMd("ans");
    a = answers.save(a);
    assertNotNull(a.getId());

    CommunityVote v = new CommunityVote();
    v.setUserId(3L); v.setTargetType("POST"); v.setTargetId(p.getId()); v.setValue((short) 1);
    votes.save(v);

    CommunityTag tag = new CommunityTag();
    tag.setName("jpa-" + System.nanoTime());
    tag = tags.save(tag);
    assertNotNull(tag.getId());
  }
}
```

Run: `./gradlew test --tests "ai.devpath.community.post.CommunityRepositoryTest"` (DB_URL=devpath_citest)
Expected: FAIL(엔티티/리포 없음, 컴파일 실패).

- [ ] **Step 2: Write entities**

엔티티는 learning `Content.java` 패턴(`@Entity`·`@Table`·`@Id @GeneratedValue(IDENTITY)`·`@Column(name=...)`·JSONB는 `@JdbcTypeCode(SqlTypes.JSON) String`). 카운트/불리언 기본값은 필드 초기화. 전부 getter/setter 작성.

`CommunityPost.java`:
```java
package ai.devpath.community.post;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "community_posts")
public class CommunityPost {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
  @Column(name = "author_id", nullable = false) private Long authorId;
  @Column(name = "board_type", nullable = false) private String boardType;
  @Column(nullable = false) private String title;
  @Column(name = "body_md", nullable = false) private String bodyMd;
  @Column(name = "body_html") private String bodyHtml;
  @Column(nullable = false) private String status = "PUBLISHED";
  @Column(name = "view_count", nullable = false) private int viewCount = 0;
  @Column(name = "upvote_count", nullable = false) private int upvoteCount = 0;
  @Column(name = "downvote_count", nullable = false) private int downvoteCount = 0;
  @Column(name = "created_at", insertable = false, updatable = false) private Instant createdAt;
  @Column(name = "updated_at", insertable = false, updatable = false) private Instant updatedAt;
  // getters/setters for all fields (id getter only; createdAt/updatedAt getter only)
}
```

`CommunityQuestion.java`(post 1:1, post_id가 PK; embedding 미매핑):
```java
package ai.devpath.community.post;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "community_questions")
public class CommunityQuestion {
  @Id @Column(name = "post_id") private Long postId;
  @Column(name = "is_solved", nullable = false) private boolean solved = false;
  @Column(name = "accepted_answer_id") private Long acceptedAnswerId;
  @JdbcTypeCode(SqlTypes.JSON) @Column(name = "learning_context", nullable = false) private String learningContext = "{}";
  // getters/setters (postId, solved, acceptedAnswerId, learningContext)
}
```

`CommunityAnswer.java`:
```java
package ai.devpath.community.post;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "community_answers")
public class CommunityAnswer {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
  @Column(name = "question_id", nullable = false) private Long questionId;
  @Column(name = "author_id") private Long authorId;
  @Column(name = "body_md", nullable = false) private String bodyMd;
  @Column(name = "body_html") private String bodyHtml;
  @Column(name = "is_ai_generated", nullable = false) private boolean aiGenerated = false;
  @Column(name = "is_accepted", nullable = false) private boolean accepted = false;
  @Column(name = "upvote_count", nullable = false) private int upvoteCount = 0;
  @Column(name = "created_at", insertable = false, updatable = false) private Instant createdAt;
  @Column(name = "updated_at", insertable = false, updatable = false) private Instant updatedAt;
  // getters/setters
}
```

`CommunityVote.java`:
```java
package ai.devpath.community.post;

import jakarta.persistence.*;

@Entity
@Table(name = "community_votes")
public class CommunityVote {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
  @Column(name = "user_id", nullable = false) private Long userId;
  @Column(name = "target_type", nullable = false) private String targetType;
  @Column(name = "target_id", nullable = false) private Long targetId;
  @Column(nullable = false) private short value;
  // getters/setters
}
```

`CommunityTag.java`:
```java
package ai.devpath.community.post;

import jakarta.persistence.*;

@Entity
@Table(name = "community_tags")
public class CommunityTag {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
  @Column(nullable = false, unique = true) private String name;
  @Column(name = "post_count", nullable = false) private int postCount = 0;
  // getters/setters
}
```

`CommunityPostTagId.java`(복합키) + `CommunityPostTag.java`:
```java
package ai.devpath.community.post;

import java.io.Serializable;
import java.util.Objects;

public class CommunityPostTagId implements Serializable {
  private Long postId;
  private Long tagId;
  public CommunityPostTagId() {}
  public CommunityPostTagId(Long postId, Long tagId) { this.postId = postId; this.tagId = tagId; }
  @Override public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof CommunityPostTagId that)) return false;
    return Objects.equals(postId, that.postId) && Objects.equals(tagId, that.tagId);
  }
  @Override public int hashCode() { return Objects.hash(postId, tagId); }
}
```
```java
package ai.devpath.community.post;

import jakarta.persistence.*;

@Entity
@Table(name = "community_post_tags")
@IdClass(CommunityPostTagId.class)
public class CommunityPostTag {
  @Id @Column(name = "post_id") private Long postId;
  @Id @Column(name = "tag_id") private Long tagId;
  public CommunityPostTag() {}
  public CommunityPostTag(Long postId, Long tagId) { this.postId = postId; this.tagId = tagId; }
  public Long getPostId() { return postId; }
  public Long getTagId() { return tagId; }
}
```

- [ ] **Step 3: Write repositories**

각 `JpaRepository`(쿼리 메서드는 후속 태스크에서 추가). 예:
```java
package ai.devpath.community.post;
import org.springframework.data.jpa.repository.JpaRepository;
public interface CommunityPostRepository extends JpaRepository<CommunityPost, Long> {}
```
동일 패턴으로 `CommunityQuestionRepository extends JpaRepository<CommunityQuestion, Long>`, `CommunityAnswerRepository extends JpaRepository<CommunityAnswer, Long>`, `CommunityVoteRepository extends JpaRepository<CommunityVote, Long>`, `CommunityTagRepository extends JpaRepository<CommunityTag, Long>`, `CommunityPostTagRepository extends JpaRepository<CommunityPostTag, CommunityPostTagId>`.

- [ ] **Step 4: Run test → PASS**

Run: `./gradlew test --tests "ai.devpath.community.post.CommunityRepositoryTest"` (DB_URL=devpath_citest)
Expected: PASS. validate가 통과(엔티티 컬럼이 빌드 A 스키마와 일치). 실패 시 컬럼명/타입 불일치 — 마이그레이션과 대조.

- [ ] **Step 5: Commit**

```bash
git add devpath-community-svc/src/main/java/ai/devpath/community/post/ \
  devpath-community-svc/src/test/java/ai/devpath/community/post/CommunityRepositoryTest.java
git commit -m "feat(community): Q&A 엔티티 6종 + 리포지토리 + JPA 매핑 검증 (B1-2)"
```

---

## Task B1-3: 질문 작성·목록·상세

**Files:**
- Create: `post/dto/CreateQuestionRequest.java`·`QuestionDetailView.java`·`PostSummaryView.java`·`AnswerView.java`
- Create: `post/QuestionService.java`, `post/CommunityController.java`(작성/목록/상세만; 답변·투표·태그는 후속 태스크에서 같은 파일에 추가)
- Modify: `CommunityPostRepository`(목록 쿼리), `CommunityAnswerRepository`(상세용)
- Create: `config/GlobalExceptionHandler.java`, `post/NotFoundException.java`
- Test: `post/QnaMockMvcTest.java`(작성→상세, 목록 필터)

**Interfaces:**
- Consumes: 엔티티/리포(B1-2).
- Produces:
  - `POST /community/questions` body `CreateQuestionRequest(String title, String bodyMd, List<String> tags)` → 201 `QuestionDetailView`
  - `GET /community/posts?board=QNA&tag=&sort=newest|unanswered` → `List<PostSummaryView>`
  - `GET /community/questions/{id}` → `QuestionDetailView(long id, String title, String bodyMd, boolean solved, Long acceptedAnswerId, int upvoteCount, int downvoteCount, List<String> tags, List<AnswerView> answers)`
  - `AnswerView(long id, Long authorId, String bodyMd, boolean aiGenerated, boolean accepted, int upvoteCount)`
  - `PostSummaryView(long id, String title, Long authorId, boolean solved, int upvoteCount, int answerCount)`
  - `QuestionService.create(long userId, CreateQuestionRequest)`·`detail(long postId)`·`list(String board, String tag, String sort)`

- [ ] **Step 1: Write failing MockMvc test**

Create `QnaMockMvcTest.java`(작성→상세 라운드트립 + 목록). JWT는 `jwt()` 포스트프로세서로 subject 주입:

```java
package ai.devpath.community.post;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class QnaMockMvcTest {

  @Autowired MockMvc mvc;

  @Test
  void createThenGetQuestion() throws Exception {
    String body = mvc.perform(post("/community/questions")
            .with(jwt().jwt(j -> j.subject("100")))
            .contentType("application/json")
            .content("{\"title\":\"JPA N+1\",\"bodyMd\":\"본문\",\"tags\":[\"jpa\",\"spring\"]}"))
        .andExpect(status().isCreated())
        .andExpect(jsonPath("$.title").value("JPA N+1"))
        .andExpect(jsonPath("$.solved").value(false))
        .andExpect(jsonPath("$.tags.length()").value(2))
        .andReturn().getResponse().getContentAsString();
    long id = com.jayway.jsonpath.JsonPath.parse(body).read("$.id", Long.class);

    mvc.perform(get("/community/questions/" + id).with(jwt().jwt(j -> j.subject("100"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.bodyMd").value("본문"))
        .andExpect(jsonPath("$.answers.length()").value(0));
  }

  @Test
  void listQuestionsByBoard() throws Exception {
    mvc.perform(post("/community/questions").with(jwt().jwt(j -> j.subject("101")))
        .contentType("application/json").content("{\"title\":\"목록테스트\",\"bodyMd\":\"b\",\"tags\":[]}"))
        .andExpect(status().isCreated());
    mvc.perform(get("/community/posts?board=QNA&sort=newest").with(jwt().jwt(j -> j.subject("101"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.length()").isNumber());
  }

  @Test
  void unauthenticatedRejected() throws Exception {
    mvc.perform(get("/community/posts?board=QNA")).andExpect(status().isUnauthorized());
  }
}
```

Run: `./gradlew test --tests "ai.devpath.community.post.QnaMockMvcTest"` (DB_URL=devpath_citest)
Expected: FAIL(컨트롤러/서비스 없음).

- [ ] **Step 2: Write DTOs (records)**

```java
package ai.devpath.community.post.dto;
import java.util.List;
public record CreateQuestionRequest(String title, String bodyMd, List<String> tags) {}
```
```java
package ai.devpath.community.post.dto;
import java.util.List;
public record AnswerView(long id, Long authorId, String bodyMd, boolean aiGenerated,
    boolean accepted, int upvoteCount) {}
```
```java
package ai.devpath.community.post.dto;
import java.util.List;
public record QuestionDetailView(long id, String title, String bodyMd, boolean solved,
    Long acceptedAnswerId, int upvoteCount, int downvoteCount, List<String> tags,
    List<AnswerView> answers) {}
```
```java
package ai.devpath.community.post.dto;
public record PostSummaryView(long id, String title, Long authorId, boolean solved,
    int upvoteCount, int answerCount) {}
```

- [ ] **Step 3: Repository 쿼리 추가**

`CommunityAnswerRepository`에:
```java
  java.util.List<CommunityAnswer> findByQuestionIdOrderByCreatedAtAsc(Long questionId);
  int countByQuestionId(Long questionId);
```
`CommunityPostRepository`에(목록; 미답변=questions.is_solved=false). 단순화: 게시판/정렬은 JPQL:
```java
  @org.springframework.data.jpa.repository.Query(
    "select p from CommunityPost p where p.boardType = :board and p.status = 'PUBLISHED' "
    + "order by p.id desc")
  java.util.List<CommunityPost> findBoardNewest(String board);
```
(tag 필터·unanswered는 B1-3 최소 구현에서 newest만; tag/unanswered는 Step 4 서비스에서 처리하거나 후속. 본 태스크 테스트는 board+newest만 단언.)

- [ ] **Step 4: Write QuestionService + tags 연결**

```java
package ai.devpath.community.post;

import ai.devpath.community.post.dto.*;
import java.util.*;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class QuestionService {
  private final CommunityPostRepository posts;
  private final CommunityQuestionRepository questions;
  private final CommunityAnswerRepository answers;
  private final CommunityTagRepository tags;
  private final CommunityPostTagRepository postTags;

  public QuestionService(CommunityPostRepository posts, CommunityQuestionRepository questions,
      CommunityAnswerRepository answers, CommunityTagRepository tags,
      CommunityPostTagRepository postTags) {
    this.posts = posts; this.questions = questions; this.answers = answers;
    this.tags = tags; this.postTags = postTags;
  }

  @Transactional
  public QuestionDetailView create(long userId, CreateQuestionRequest req) {
    CommunityPost p = new CommunityPost();
    p.setAuthorId(userId); p.setBoardType("QNA");
    p.setTitle(req.title()); p.setBodyMd(req.bodyMd()); p.setStatus("PUBLISHED");
    p = posts.save(p);
    CommunityQuestion q = new CommunityQuestion();
    q.setPostId(p.getId());
    questions.save(q);
    List<String> tagNames = req.tags() == null ? List.of() : req.tags();
    for (String name : tagNames) {
      CommunityTag tag = tags.findByName(name).orElseGet(() -> {
        CommunityTag t = new CommunityTag(); t.setName(name); return tags.save(t);
      });
      postTags.save(new CommunityPostTag(p.getId(), tag.getId()));
    }
    return detail(p.getId());
  }

  @Transactional(readOnly = true)
  public QuestionDetailView detail(long postId) {
    CommunityPost p = posts.findById(postId)
        .orElseThrow(() -> new NotFoundException("question " + postId));
    CommunityQuestion q = questions.findById(postId)
        .orElseThrow(() -> new NotFoundException("question " + postId));
    List<AnswerView> ans = answers.findByQuestionIdOrderByCreatedAtAsc(postId).stream()
        .map(a -> new AnswerView(a.getId(), a.getAuthorId(), a.getBodyMd(),
            a.isAiGenerated(), a.isAccepted(), a.getUpvoteCount()))
        .collect(Collectors.toList());
    List<String> tagNames = tagNamesFor(postId);
    return new QuestionDetailView(p.getId(), p.getTitle(), p.getBodyMd(), q.isSolved(),
        q.getAcceptedAnswerId(), p.getUpvoteCount(), p.getDownvoteCount(), tagNames, ans);
  }

  @Transactional(readOnly = true)
  public List<PostSummaryView> list(String board, String tag, String sort) {
    String b = (board == null || board.isBlank()) ? "QNA" : board;
    return posts.findBoardNewest(b).stream()
        .map(p -> new PostSummaryView(p.getId(), p.getTitle(), p.getAuthorId(),
            questions.findById(p.getId()).map(CommunityQuestion::isSolved).orElse(false),
            p.getUpvoteCount(), answers.countByQuestionId(p.getId())))
        .collect(Collectors.toList());
  }

  private List<String> tagNamesFor(long postId) {
    List<Long> ids = postTags.findByPostId(postId).stream()
        .map(CommunityPostTag::getTagId).collect(Collectors.toList());
    if (ids.isEmpty()) return List.of();
    return tags.findAllById(ids).stream().map(CommunityTag::getName).collect(Collectors.toList());
  }
}
```

추가 리포 메서드: `CommunityTagRepository.findByName(String)` → `Optional<CommunityTag>`; `CommunityPostTagRepository.findByPostId(Long)` → `List<CommunityPostTag>`. `CommunityQuestion`에 `isSolved()` getter, `CommunityTag.getName()` 등 B1-2 getter 사용.

- [ ] **Step 5: Write NotFoundException + GlobalExceptionHandler + Controller**

```java
package ai.devpath.community.post;
public class NotFoundException extends RuntimeException {
  public NotFoundException(String msg) { super(msg); }
}
```
```java
package ai.devpath.community.config;

import ai.devpath.community.post.NotFoundException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {
  @ExceptionHandler(NotFoundException.class)
  public ResponseEntity<String> notFound(NotFoundException e) {
    return ResponseEntity.status(HttpStatus.NOT_FOUND).body(e.getMessage());
  }
}
```
```java
package ai.devpath.community.post;

import ai.devpath.community.post.dto.*;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/community")
public class CommunityController {
  private final QuestionService questionService;

  public CommunityController(QuestionService questionService) {
    this.questionService = questionService;
  }

  @PostMapping("/questions")
  public ResponseEntity<QuestionDetailView> create(
      @AuthenticationPrincipal Jwt jwt, @RequestBody CreateQuestionRequest req) {
    return ResponseEntity.status(HttpStatus.CREATED).body(questionService.create(uid(jwt), req));
  }

  @GetMapping("/questions/{id}")
  public ResponseEntity<QuestionDetailView> detail(@PathVariable long id) {
    return ResponseEntity.ok(questionService.detail(id));
  }

  @GetMapping("/posts")
  public ResponseEntity<List<PostSummaryView>> list(
      @RequestParam(required = false) String board,
      @RequestParam(required = false) String tag,
      @RequestParam(required = false) String sort) {
    return ResponseEntity.ok(questionService.list(board, tag, sort));
  }

  static long uid(Jwt jwt) { return Long.parseLong(jwt.getSubject()); }
}
```

- [ ] **Step 6: Run test → PASS**

Run: `./gradlew test --tests "ai.devpath.community.post.QnaMockMvcTest"` (DB_URL=devpath_citest)
Expected: PASS(3 tests).

- [ ] **Step 7: Commit**

```bash
git add devpath-community-svc/src/main/java/ai/devpath/community/post/ \
  devpath-community-svc/src/main/java/ai/devpath/community/config/GlobalExceptionHandler.java \
  devpath-community-svc/src/test/java/ai/devpath/community/post/QnaMockMvcTest.java
git commit -m "feat(community): 질문 작성·목록·상세 + 태그 연결 (B1-3)"
```

---

## Task B1-4: 답변 작성 + 채택(OWNER)

**Files:**
- Create: `post/AnswerService.java`, `post/dto/CreateAnswerRequest.java`, `post/ForbiddenException.java`
- Modify: `post/CommunityController.java`(답변·채택 엔드포인트 추가), `config/GlobalExceptionHandler.java`(403)
- Test: `post/QnaMockMvcTest.java`(답변→채택, 비OWNER 403)

**Interfaces:**
- Produces:
  - `POST /community/questions/{id}/answers` body `CreateAnswerRequest(String bodyMd)` → 201 `AnswerView`
  - `POST /community/answers/{id}/accept` → 200(질문자 OWNER만; 아니면 403). 채택 시 `answer.is_accepted=true`·`question.is_solved=true`·`question.accepted_answer_id=answerId`.
  - `AnswerService.add(long userId, long questionId, CreateAnswerRequest)`·`accept(long userId, long answerId)`

- [ ] **Step 1: Write failing test (append to QnaMockMvcTest)**

```java
  @Test
  void answerThenAcceptByOwner() throws Exception {
    String qBody = mvc.perform(post("/community/questions").with(jwt().jwt(j -> j.subject("200")))
        .contentType("application/json").content("{\"title\":\"q\",\"bodyMd\":\"b\",\"tags\":[]}"))
        .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
    long qid = com.jayway.jsonpath.JsonPath.parse(qBody).read("$.id", Long.class);

    String aBody = mvc.perform(post("/community/questions/" + qid + "/answers")
            .with(jwt().jwt(j -> j.subject("201")))
            .contentType("application/json").content("{\"bodyMd\":\"답변내용\"}"))
        .andExpect(status().isCreated())
        .andExpect(jsonPath("$.bodyMd").value("답변내용"))
        .andReturn().getResponse().getContentAsString();
    long aid = com.jayway.jsonpath.JsonPath.parse(aBody).read("$.id", Long.class);

    // 비OWNER(작성자 200 아님) 채택 시도 → 403
    mvc.perform(post("/community/answers/" + aid + "/accept").with(jwt().jwt(j -> j.subject("999"))))
        .andExpect(status().isForbidden());

    // OWNER(200) 채택 → 200, 이후 상세에서 solved=true
    mvc.perform(post("/community/answers/" + aid + "/accept").with(jwt().jwt(j -> j.subject("200"))))
        .andExpect(status().isOk());
    mvc.perform(get("/community/questions/" + qid).with(jwt().jwt(j -> j.subject("200"))))
        .andExpect(jsonPath("$.solved").value(true))
        .andExpect(jsonPath("$.acceptedAnswerId").value(aid));
  }
```

Run: `./gradlew test --tests "ai.devpath.community.post.QnaMockMvcTest"` Expected: 새 테스트 FAIL.

- [ ] **Step 2: DTO + 예외**

```java
package ai.devpath.community.post.dto;
public record CreateAnswerRequest(String bodyMd) {}
```
```java
package ai.devpath.community.post;
public class ForbiddenException extends RuntimeException {
  public ForbiddenException(String msg) { super(msg); }
}
```

- [ ] **Step 3: AnswerService**

```java
package ai.devpath.community.post;

import ai.devpath.community.post.dto.AnswerView;
import ai.devpath.community.post.dto.CreateAnswerRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AnswerService {
  private final CommunityPostRepository posts;
  private final CommunityQuestionRepository questions;
  private final CommunityAnswerRepository answers;

  public AnswerService(CommunityPostRepository posts, CommunityQuestionRepository questions,
      CommunityAnswerRepository answers) {
    this.posts = posts; this.questions = questions; this.answers = answers;
  }

  @Transactional
  public AnswerView add(long userId, long questionId, CreateAnswerRequest req) {
    questions.findById(questionId).orElseThrow(() -> new NotFoundException("question " + questionId));
    CommunityAnswer a = new CommunityAnswer();
    a.setQuestionId(questionId); a.setAuthorId(userId); a.setBodyMd(req.bodyMd());
    a = answers.save(a);
    return new AnswerView(a.getId(), a.getAuthorId(), a.getBodyMd(),
        a.isAiGenerated(), a.isAccepted(), a.getUpvoteCount());
  }

  @Transactional
  public void accept(long userId, long answerId) {
    CommunityAnswer a = answers.findById(answerId)
        .orElseThrow(() -> new NotFoundException("answer " + answerId));
    CommunityQuestion q = questions.findById(a.getQuestionId())
        .orElseThrow(() -> new NotFoundException("question " + a.getQuestionId()));
    CommunityPost p = posts.findById(q.getPostId())
        .orElseThrow(() -> new NotFoundException("post " + q.getPostId()));
    if (p.getAuthorId() == null || p.getAuthorId() != userId) {
      throw new ForbiddenException("only question author can accept");
    }
    a.setAccepted(true);
    answers.save(a);
    q.setSolved(true);
    q.setAcceptedAnswerId(answerId);
    questions.save(q);
  }
}
```

- [ ] **Step 4: Controller 엔드포인트 + GlobalExceptionHandler 403**

`CommunityController`에 `AnswerService` 주입 + 추가(생성자에 AnswerService 파라미터 추가):
```java
  @PostMapping("/questions/{id}/answers")
  public ResponseEntity<AnswerView> answer(
      @AuthenticationPrincipal Jwt jwt, @PathVariable long id,
      @RequestBody CreateAnswerRequest req) {
    return ResponseEntity.status(HttpStatus.CREATED).body(answerService.add(uid(jwt), id, req));
  }

  @PostMapping("/answers/{id}/accept")
  public ResponseEntity<Void> accept(@AuthenticationPrincipal Jwt jwt, @PathVariable long id) {
    answerService.accept(uid(jwt), id);
    return ResponseEntity.ok().build();
  }
```
`GlobalExceptionHandler`에:
```java
  @ExceptionHandler(ForbiddenException.class)
  public ResponseEntity<String> forbidden(ForbiddenException e) {
    return ResponseEntity.status(HttpStatus.FORBIDDEN).body(e.getMessage());
  }
```

- [ ] **Step 5: Run test → PASS**

Run: `./gradlew test --tests "ai.devpath.community.post.QnaMockMvcTest"` Expected: PASS(전체).

- [ ] **Step 6: Commit**

```bash
git add devpath-community-svc/src/main/java/ai/devpath/community/
git commit -m "feat(community): 답변 작성 + 채택(OWNER 검사) (B1-4)"
```

---

## Task B1-5: 투표(UPSERT + 카운트 집계)

**Files:**
- Create: `post/VoteService.java`, `post/dto/VoteRequest.java`
- Modify: `post/CommunityController.java`(투표 엔드포인트), `CommunityVoteRepository`(조회), `CommunityAnswerRepository`(upvote 집계)
- Test: `post/VoteMockMvcTest.java`

**Interfaces:**
- Produces:
  - `POST /community/posts/{id}/vote` body `VoteRequest(int value)`(value∈{-1,1}) → 200. 같은 사용자 재투표는 값 갱신(같은 값 재전송도 멱등 유지). `community_posts.upvote_count/downvote_count`를 votes 집계로 재계산.
  - `POST /community/answers/{id}/vote` → 200. `community_answers.upvote_count` 갱신.
  - `VoteService.votePost(long userId, long postId, int value)`·`voteAnswer(long userId, long answerId, int value)`

- [ ] **Step 1: Write failing test**

```java
package ai.devpath.community.post;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class VoteMockMvcTest {
  @Autowired MockMvc mvc;

  @Test
  void upvotePostAccumulatesAndIsIdempotentPerUser() throws Exception {
    String qBody = mvc.perform(post("/community/questions").with(jwt().jwt(j -> j.subject("300")))
        .contentType("application/json").content("{\"title\":\"vote\",\"bodyMd\":\"b\",\"tags\":[]}"))
        .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
    long qid = com.jayway.jsonpath.JsonPath.parse(qBody).read("$.id", Long.class);

    mvc.perform(post("/community/posts/" + qid + "/vote").with(jwt().jwt(j -> j.subject("301")))
        .contentType("application/json").content("{\"value\":1}")).andExpect(status().isOk());
    // 같은 사용자 재투표(멱등) → 여전히 upvote 1
    mvc.perform(post("/community/posts/" + qid + "/vote").with(jwt().jwt(j -> j.subject("301")))
        .contentType("application/json").content("{\"value\":1}")).andExpect(status().isOk());
    // 다른 사용자 upvote → 2
    mvc.perform(post("/community/posts/" + qid + "/vote").with(jwt().jwt(j -> j.subject("302")))
        .contentType("application/json").content("{\"value\":1}")).andExpect(status().isOk());

    mvc.perform(get("/community/questions/" + qid).with(jwt().jwt(j -> j.subject("300"))))
        .andExpect(jsonPath("$.upvoteCount").value(2));
  }

  @Test
  void invalidVoteValueRejected() throws Exception {
    String qBody = mvc.perform(post("/community/questions").with(jwt().jwt(j -> j.subject("303")))
        .contentType("application/json").content("{\"title\":\"v2\",\"bodyMd\":\"b\",\"tags\":[]}"))
        .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
    long qid = com.jayway.jsonpath.JsonPath.parse(qBody).read("$.id", Long.class);
    mvc.perform(post("/community/posts/" + qid + "/vote").with(jwt().jwt(j -> j.subject("304")))
        .contentType("application/json").content("{\"value\":5}")).andExpect(status().isBadRequest());
  }
}
```

Run: `./gradlew test --tests "ai.devpath.community.post.VoteMockMvcTest"` Expected: FAIL.

- [ ] **Step 2: DTO + repo 메서드**

```java
package ai.devpath.community.post.dto;
public record VoteRequest(int value) {}
```
`CommunityVoteRepository`에:
```java
  java.util.Optional<CommunityVote> findByUserIdAndTargetTypeAndTargetId(Long userId, String targetType, Long targetId);
  int countByTargetTypeAndTargetIdAndValue(String targetType, Long targetId, short value);
```

- [ ] **Step 3: VoteService (UPSERT + 카운트 재집계)**

```java
package ai.devpath.community.post;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class VoteService {
  private final CommunityVoteRepository votes;
  private final CommunityPostRepository posts;
  private final CommunityAnswerRepository answers;

  public VoteService(CommunityVoteRepository votes, CommunityPostRepository posts,
      CommunityAnswerRepository answers) {
    this.votes = votes; this.posts = posts; this.answers = answers;
  }

  @Transactional
  public void votePost(long userId, long postId, int value) {
    validate(value);
    posts.findById(postId).orElseThrow(() -> new NotFoundException("post " + postId));
    upsert(userId, "POST", postId, (short) value);
    CommunityPost p = posts.findById(postId).orElseThrow();
    p.setUpvoteCount(votes.countByTargetTypeAndTargetIdAndValue("POST", postId, (short) 1));
    p.setDownvoteCount(votes.countByTargetTypeAndTargetIdAndValue("POST", postId, (short) -1));
    posts.save(p);
  }

  @Transactional
  public void voteAnswer(long userId, long answerId, int value) {
    validate(value);
    CommunityAnswer a = answers.findById(answerId)
        .orElseThrow(() -> new NotFoundException("answer " + answerId));
    upsert(userId, "ANSWER", answerId, (short) value);
    a.setUpvoteCount(votes.countByTargetTypeAndTargetIdAndValue("ANSWER", answerId, (short) 1));
    answers.save(a);
  }

  private void upsert(long userId, String type, long targetId, short value) {
    CommunityVote v = votes.findByUserIdAndTargetTypeAndTargetId(userId, type, targetId)
        .orElseGet(() -> {
          CommunityVote nv = new CommunityVote();
          nv.setUserId(userId); nv.setTargetType(type); nv.setTargetId(targetId);
          return nv;
        });
    v.setValue(value);
    votes.save(v);
  }

  private void validate(int value) {
    if (value != 1 && value != -1) throw new InvalidVoteException("value must be 1 or -1");
  }
}
```
`InvalidVoteException`:
```java
package ai.devpath.community.post;
public class InvalidVoteException extends RuntimeException {
  public InvalidVoteException(String msg) { super(msg); }
}
```

- [ ] **Step 4: Controller + 400 매핑**

`CommunityController`에 `VoteService` 주입 + :
```java
  @PostMapping("/posts/{id}/vote")
  public ResponseEntity<Void> votePost(@AuthenticationPrincipal Jwt jwt, @PathVariable long id,
      @RequestBody VoteRequest req) {
    voteService.votePost(uid(jwt), id, req.value());
    return ResponseEntity.ok().build();
  }

  @PostMapping("/answers/{id}/vote")
  public ResponseEntity<Void> voteAnswer(@AuthenticationPrincipal Jwt jwt, @PathVariable long id,
      @RequestBody VoteRequest req) {
    voteService.voteAnswer(uid(jwt), id, req.value());
    return ResponseEntity.ok().build();
  }
```
`GlobalExceptionHandler`에:
```java
  @ExceptionHandler(InvalidVoteException.class)
  public ResponseEntity<String> badVote(InvalidVoteException e) {
    return ResponseEntity.badRequest().body(e.getMessage());
  }
```

- [ ] **Step 5: Run test → PASS**

Run: `./gradlew test --tests "ai.devpath.community.post.VoteMockMvcTest"` Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add devpath-community-svc/src/main/java/ai/devpath/community/
git commit -m "feat(community): 투표 UPSERT + 카운트 집계 (B1-5)"
```

---

## Task B1-6: 태그 자동완성 + 전체 검증

**Files:**
- Create: `post/TagService.java`, `post/dto/TagView.java`
- Modify: `post/CommunityController.java`(태그 엔드포인트), `CommunityTagRepository`(prefix 쿼리)
- Test: `post/TagMockMvcTest.java`

**Interfaces:**
- Produces: `GET /community/tags?q={prefix}` → `List<TagView>`(prefix 매칭, 최대 10, postCount desc). `TagView(long id, String name, int postCount)`. `TagService.autocomplete(String q)`.

- [ ] **Step 1: Write failing test**

```java
package ai.devpath.community.post;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class TagMockMvcTest {
  @Autowired MockMvc mvc;

  @Test
  void autocompleteByPrefix() throws Exception {
    // 질문 작성으로 태그 생성(고유 prefix)
    String pre = "spr" + (System.nanoTime() % 100000);
    mvc.perform(post("/community/questions").with(jwt().jwt(j -> j.subject("400")))
        .contentType("application/json")
        .content("{\"title\":\"t\",\"bodyMd\":\"b\",\"tags\":[\"" + pre + "boot\"]}"))
        .andExpect(status().isCreated());
    mvc.perform(get("/community/tags?q=" + pre).with(jwt().jwt(j -> j.subject("400"))))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$[0].name").value(pre + "boot"));
  }
}
```

Run: `./gradlew test --tests "ai.devpath.community.post.TagMockMvcTest"` Expected: FAIL.

- [ ] **Step 2: repo 쿼리 + DTO**

`CommunityTagRepository`에:
```java
  java.util.List<CommunityTag> findTop10ByNameStartingWithOrderByPostCountDesc(String prefix);
```
```java
package ai.devpath.community.post.dto;
public record TagView(long id, String name, int postCount) {}
```

- [ ] **Step 3: TagService + Controller**

```java
package ai.devpath.community.post;

import ai.devpath.community.post.dto.TagView;
import java.util.List;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

@Service
public class TagService {
  private final CommunityTagRepository tags;
  public TagService(CommunityTagRepository tags) { this.tags = tags; }

  public List<TagView> autocomplete(String q) {
    if (q == null || q.isBlank()) return List.of();
    return tags.findTop10ByNameStartingWithOrderByPostCountDesc(q).stream()
        .map(t -> new TagView(t.getId(), t.getName(), t.getPostCount()))
        .collect(Collectors.toList());
  }
}
```
`CommunityController`에 `TagService` 주입 + :
```java
  @GetMapping("/tags")
  public ResponseEntity<List<TagView>> tags(@RequestParam(required = false) String q) {
    return ResponseEntity.ok(tagService.autocomplete(q));
  }
```

- [ ] **Step 4: Run test → PASS**

Run: `./gradlew test --tests "ai.devpath.community.post.TagMockMvcTest"` Expected: PASS.

- [ ] **Step 5: Full suite + commit**

Run: `./gradlew test` (DB_URL=devpath_citest)
Expected: 전체 PASS(Context·Repository·Qna·Vote·Tag).

```bash
git add devpath-community-svc/src/main/java/ai/devpath/community/ \
  devpath-community-svc/src/test/java/ai/devpath/community/post/TagMockMvcTest.java
git commit -m "feat(community): 태그 자동완성 + B1 코어 전체 검증 (B1-6)"
```

---

## Self-Review (스킬 체크리스트)

**1. Spec coverage**(설계서 §1.2 DoD·§5 community-svc B1 대비):
- 질문 작성/목록/상세 → B1-3 ✅ · 답변/채택(OWNER) → B1-4 ✅ · 투표 집계(UPSERT) → B1-5 ✅ · 태그 자동완성 → B1-6 ✅ · SecurityConfig(JWT) → B1-1 ✅ · 엔티티/리포 → B1-2 ✅
- 이벤트 발행(question.posted)·유사질문·AI 시드 consume → **B2**(범위 외, 명시) ✅
- `learning_context`·`question_embedding` → 컬럼만(B1 미사용; embedding 엔티티 미매핑) ✅

**2. Placeholder scan**: 각 스텝에 실제 코드/명령. getter/setter는 "learning Content.java 패턴 + @Column(name)"으로 명시(보일러플레이트, 반복 생략은 의도적이며 패턴 참조 제공) — 엔지니어가 채울 모호함 없음.

**3. Type consistency**: `uid(jwt)`·`QuestionDetailView`(B1-3 정의)·`AnswerView`(B1-3, B1-4 재사용)·`CommunityController` 생성자에 서비스 누적 주입(B1-3 QuestionService → B1-4 +AnswerService → B1-5 +VoteService → B1-6 +TagService). **주의: 컨트롤러 생성자는 태스크마다 파라미터가 늘어난다 — 각 태스크에서 기존 필드 유지하며 추가.** 투표 value는 엔티티 `short`, DTO/검증은 `int`(±1만 허용)로 일관.

> ⚠️ 구현 주의: ① `created_at/updated_at`은 DB default/trigger 소관 → 엔티티 `insertable=false, updatable=false`(위 코드 반영). ② `@DataJpaTest`는 실 PostgreSQL 필요 → `@AutoConfigureTestDatabase(replace=NONE)` + `devpath_citest`. ③ MockMvc 테스트는 `jwt().jwt(j -> j.subject("..."))`로 userId 주입(SecurityConfig HS256 디코더는 실토큰 불요). ④ 컨트롤러 생성자 누적 주입은 B1-4/5/6에서 빠뜨리지 말 것.
