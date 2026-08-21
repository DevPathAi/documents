# 커뮤니티 콘텐츠 변경 경로 동시성 제어 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `devpath-community-svc` 의 변경 경로에서 대상 행을 비관적으로 잠가, 실측된 경쟁 네 건
(R1 투표↔내리기 · R2 채택↔삭제 · R4 같은 사용자 동시 투표 · R5 두 사용자 동시 투표)을 닫는다.

**Architecture:** 리포지토리에 `@Lock(PESSIMISTIC_WRITE)` 조회를 답변·글 각각 하나씩 더하고,
여섯 개 변경 경로의 `findById` 를 그것으로 바꾼다. 뒤따르는 상태 판정과 응답 코드는 **그대로
둔다** — 락이 생김으로써 이미 있던 판정이 비로소 신뢰할 수 있게 된다. API 계약은 바뀌지 않는다.

**Tech Stack:** Java 21 · Spring Boot 4 (Data JPA) · PostgreSQL 17 · JUnit 5 · AssertJ ·
`TransactionTemplate`(이 레포에 선례 없음, 이 계획이 도입)

**Spec:** `docs/superpowers/specs/2026-08-21-community-concurrency-control-design.md`

## Global Constraints

모든 태스크의 요구사항에 아래가 암묵적으로 포함된다.

- **잠그는 곳은 여섯 개뿐**: `VoteService.votePost` · `VoteService.voteAnswer` ·
  `AnswerService.accept` · `AnswerService.delete` · `ContentAdminService.hidePost` ·
  `ContentAdminService.hideAnswer`.
- **잠그지 않는 곳**: 댓글 전 경로 · `PostService.deletePost` · 본문 수정 세 경로
  (`PostService.updatePost` · `AnswerService.update` · `CommentService.update`). 건드리지 말 것.
- **API 계약 변경 금지.** 상태 코드·응답 본문·엔드포인트를 바꾸지 않는다. 프론트엔드 변경 0.
- **`@Version` 도입 금지.** 격리 수준은 READ COMMITTED 유지(설정 파일을 건드리지 않는다).
- **교착 방지**: 명시적 락은 직접 대상 **한 행만**. 이어지는 갱신은 **답변 → 질문** 순서.
- **락 대기는 유한**해야 한다. 목표 3초.
- ★**테스트 클래스에 `@Transactional` 을 붙이지 않는다**★ — 워커 스레드가 커밋된 데이터를 봐야
  한다. 대신 `@BeforeEach` 로 직접 정리한다.
- **동시 커넥션은 2개까지**(`src/test/resources/application-test.yml` 의
  `hikari.maximum-pool-size: 4`). 워커 스레드는 하나만 쓴다.
- **완료 조건은 "green" 이 아니라 "락을 빼면 red"** 다. 각 경쟁 태스크는 되돌림 관측을 포함한다.
- **테스트 DB**: 원형 템플릿에서 새로 만들고 id 공간을 분리한다. `devpath` 재사용 금지.

  ```bash
  docker start devpath-pg devpath-es
  docker exec devpath-pg psql -U devpath -d postgres \
    -c "CREATE DATABASE devpath_run40 TEMPLATE devpath_tpl OWNER devpath"
  docker exec devpath-pg psql -U devpath -d devpath_run40 -tAc \
    "SELECT setval('community_posts_id_seq',40000000), setval('community_answers_id_seq',40000000), setval('community_comments_id_seq',40000000)"
  ```

- **테스트 실행 명령**(파이프의 `$?` 는 `tail` 것이므로 파이프 금지):

  ```bash
  cd /d/workspace/dpa/devpath-community-svc
  DB_URL=jdbc:postgresql://localhost:5432/devpath_run40 DB_USER=devpath DB_PASSWORD=localdev \
  GITHUB_ACTOR=$(gh api user --jq .login) GITHUB_TOKEN=$(gh auth token) \
    ./gradlew test --tests '<패턴>' > /tmp/t.log 2>&1; echo "GRADLE_EXIT=$?"
  ```

- **"BUILD SUCCESSFUL" 은 실행의 증거가 아니다.** 실행 증거는 XML 이다:

  ```bash
  grep -oE 'tests="[0-9]+" skipped="[0-9]+" failures="[0-9]+" errors="[0-9]+"' \
    build/test-results/test/TEST-<FQCN>.xml
  ```

- 브랜치: `devpath-community-svc` 는 `develop` 에서 `fix/content-mutation-concurrency` 를 뗀다.
  `documents` 는 `develop` 에서 `docs/concurrency-convention` 을 뗀다. `main` 직접 커밋 금지.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `src/main/java/ai/devpath/community/post/CommunityAnswerRepository.java` (수정) | `findByIdForUpdate` 하나 추가 |
| `src/main/java/ai/devpath/community/post/CommunityPostRepository.java` (수정) | `findByIdForUpdate` 하나 추가 |
| `src/main/java/ai/devpath/community/post/VoteService.java` (수정) | `votePost`·`voteAnswer` 가 잠금 조회를 쓴다 |
| `src/main/java/ai/devpath/community/post/AnswerService.java` (수정) | `accept`·`delete` 가 잠금 조회를 쓴다 |
| `src/main/java/ai/devpath/community/post/ContentAdminService.java` (수정) | `hidePost`·`hideAnswer` 가 잠금 조회를 쓴다 |
| `src/test/java/ai/devpath/community/post/LockTimeoutProbeTest.java` (신규) | 락 대기가 유한함을 증명 |
| `src/test/java/ai/devpath/community/post/ContentMutationRaceTest.java` (신규) | 경쟁 5건 + 공용 하네스 |
| `src/test/resources/application-test.yml` (수정, **조건부**) | Task 1 이 힌트 미작동으로 판정했을 때만 |
| `documents/48_동시성_제어_관례.md` (신규) | 조직 관례 |

**태스크 순서의 근거**: Task 2 가 답변 락을 넣으면 R4 가 **덤으로 닫힌다.** 그래서 Task 4 의
테스트는 처음부터 green 이다. ★green 인 테스트가 실제로 무언가를 지키는지는 락을 잠시 되돌려
red 를 관측해야만 알 수 있다★ — 그 단계를 빼면 "green 인데 아무것도 검증하지 않는 테스트" 가
된다(이 프로젝트에서 세 번 겪었다). R5 도 Task 5 의 글 락에 덤으로 닫히므로 같은 처리를 한다.

---

### Task 1: 락 대기를 유한하게 만들고, 유한함을 증명한다

**Files:**
- Modify: `src/main/java/ai/devpath/community/post/CommunityAnswerRepository.java`
- Create: `src/test/java/ai/devpath/community/post/LockTimeoutProbeTest.java`
- Modify (조건부): `src/test/resources/application-test.yml`

**Interfaces:**
- Produces: `CommunityAnswerRepository.findByIdForUpdate(long) : Optional<CommunityAnswer>` —
  Task 2·3·4 가 쓴다.

★**이 태스크는 미확인 전제를 재는 것이 목적이다.** `jakarta.persistence.lock.timeout` 힌트가
PostgreSQL 에서 먹는지 확인되지 않았다(Postgres 는 역사적으로 `NOWAIT`/`SKIP LOCKED` 만 지원).
관측 결과에 따라 Step 5 로 갈지 Step 6 으로 갈지가 갈린다. **추측으로 넘어가지 말 것.**★

- [ ] **Step 1: 잠금 조회를 리포지토리에 추가**

`CommunityAnswerRepository.java` 전체를 아래로 바꾼다:

```java
package ai.devpath.community.post;

import jakarta.persistence.LockModeType;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.jpa.repository.QueryHints;
import org.springframework.data.repository.query.Param;

public interface CommunityAnswerRepository extends JpaRepository<CommunityAnswer, Long> {
  java.util.List<CommunityAnswer> findByQuestionIdOrderByCreatedAtAsc(Long questionId);
  int countByQuestionId(Long questionId);
  long countByAuthorIdAndAiGeneratedFalse(Long authorId);
  long countByAuthorIdAndAiGeneratedFalseAndStatus(Long authorId, String status);

  /**
   * 변경 경로 전용 조회. 행을 잠가 같은 답변에 대한 다른 변경과 직렬화한다.
   *
   * <p>READ COMMITTED 에서 {@code FOR UPDATE} 는 락을 얻은 뒤 행을 <b>다시 읽는다</b>(측정함).
   * 그래서 이 조회 뒤의 status 판정이 비로소 신뢰할 수 있게 된다.
   */
  @Lock(LockModeType.PESSIMISTIC_WRITE)
  @QueryHints(@jakarta.persistence.QueryHint(
      name = "jakarta.persistence.lock.timeout", value = "3000"))
  @Query("select a from CommunityAnswer a where a.id = :id")
  Optional<CommunityAnswer> findByIdForUpdate(@Param("id") long id);
}
```

- [ ] **Step 2: 대기가 유한한지 재는 테스트를 쓴다**

`src/test/java/ai/devpath/community/post/LockTimeoutProbeTest.java`:

```java
package ai.devpath.community.post;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import ai.devpath.community.post.dto.CreateAnswerRequest;
import ai.devpath.community.post.dto.CreateQuestionRequest;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * ★락 대기는 반드시 유한해야 한다★ — 무한 대기는 커넥션을 쌓아 서비스를 죽인다.
 *
 * <p>이 테스트는 "어떤 수단으로" 유한한지는 묻지 않는다. 힌트가 먹든 커넥션 옵션이 먹든
 * 결과만 본다. 그래서 Task 1 의 두 분기 어디로 가든 같은 테스트가 계약을 지킨다.
 */
@SpringBootTest
@ActiveProfiles("test")
class LockTimeoutProbeTest {

  @Autowired PlatformTransactionManager txm;
  @Autowired CommunityAnswerRepository answers;
  @Autowired QuestionService questionService;
  @Autowired AnswerService answerService;

  @Test
  void lockWaitIsBounded() {
    TransactionTemplate tx = new TransactionTemplate(txm);
    ExecutorService pool = Executors.newSingleThreadExecutor();
    try {
      long answerId = tx.execute(st -> {
        var q = questionService.create(9601L, new CreateQuestionRequest("t", "b", List.of()));
        return answerService.add(9602L, q.id(), new CreateAnswerRequest("ans")).id();
      });

      Future<?>[] waiter = new Future<?>[1];
      tx.executeWithoutResult(st -> {
        answers.findByIdForUpdate(answerId).orElseThrow();   // 락을 쥐고 놓지 않는다
        waiter[0] = pool.submit(() ->
            tx.execute(inner -> answers.findByIdForUpdate(answerId).orElseThrow()));
        // 8초는 목표 3초의 두 배 이상이다. 유한하면 그 전에 "예외로" 끝난다.
        // 무한이면 여기서 TimeoutException 이 나고, 그것이 곧 실패다.
        assertThatThrownBy(() -> waiter[0].get(8, TimeUnit.SECONDS))
            .as("대기가 유한하면 ExecutionException, 무한하면 TimeoutException 이다")
            .isInstanceOf(ExecutionException.class);
      });
      assertThat(waiter[0].isDone()).isTrue();
    } finally {
      pool.shutdownNow();
    }
  }
}
```

- [ ] **Step 3: 실행해서 어느 분기인지 관측한다**

```bash
DB_URL=jdbc:postgresql://localhost:5432/devpath_run40 DB_USER=devpath DB_PASSWORD=localdev \
GITHUB_ACTOR=$(gh api user --jq .login) GITHUB_TOKEN=$(gh auth token) \
  ./gradlew test --tests '*LockTimeoutProbeTest*' > /tmp/t.log 2>&1; echo "GRADLE_EXIT=$?"
grep -oE 'message="[^"]{0,200}' \
  build/test-results/test/TEST-ai.devpath.community.post.LockTimeoutProbeTest.xml
```

두 결과 중 하나를 **기록한다**:
- **PASS** → 힌트가 먹는다. Step 5 를 건너뛰고 Step 6 으로.
- **FAIL, 사유가 `TimeoutException`** → 힌트가 안 먹는다(대기가 무한). Step 5 로.
- 그 밖의 사유로 실패 → 테스트 자체의 결함이다. 고치고 Step 3 을 다시 한다.

- [ ] **Step 4: 관측 결과를 커밋 메시지에 남길 문장으로 적어 둔다**

한 줄이면 된다. 예: `lock.timeout 힌트: PostgreSQL 17 에서 먹지 않음(8초 무한 대기 관측)`.
이 문장이 Step 6 커밋에 들어가야 다음 사람이 같은 실험을 반복하지 않는다.

- [ ] **Step 5: (Step 3 이 FAIL 이었을 때만) 커넥션 옵션으로 전환한다**

힌트 애노테이션(`@QueryHints(...)` 줄 두 줄)을 `CommunityAnswerRepository` 에서 **지우고**,
`src/test/resources/application-test.yml` 의 `spring.datasource.hikari` 아래에 더한다:

```yaml
      data-source-properties:
        options: "-c lock_timeout=3000"
```

운영에도 같은 값이 필요하므로 `src/main/resources/application.yml` 의
`spring.datasource.hikari` 아래에도 같은 두 줄을 더한다.

그다음 **옵션이 실제로 세션에 도달했는지 직접 잰다.** `LockTimeoutProbeTest` 에 추가:

```java
  @Autowired org.springframework.jdbc.core.JdbcTemplate jdbc;

  @Test
  void lockTimeoutSettingReachesTheSession() {
    String actual = jdbc.queryForObject("SELECT current_setting('lock_timeout')", String.class);
    assertThat(actual).as("0 은 무한을 뜻한다").isNotEqualTo("0");
    assertThat(actual).isEqualTo("3s");
  }
```

- [ ] **Step 6: 다시 실행해 green 확인 후 커밋**

```bash
DB_URL=jdbc:postgresql://localhost:5432/devpath_run40 DB_USER=devpath DB_PASSWORD=localdev \
GITHUB_ACTOR=$(gh api user --jq .login) GITHUB_TOKEN=$(gh auth token) \
  ./gradlew test --tests '*LockTimeoutProbeTest*' > /tmp/t.log 2>&1; echo "GRADLE_EXIT=$?"
grep -oE 'tests="[0-9]+" skipped="[0-9]+" failures="[0-9]+" errors="[0-9]+"' \
  build/test-results/test/TEST-ai.devpath.community.post.LockTimeoutProbeTest.xml
git add -A && git commit -m "feat(community): 답변 잠금 조회와 유한한 락 대기

<Step 4 에 적어 둔 관측 문장을 여기에 넣는다>"
```

---

### Task 2: R1-답변 — 내려간 답변에 이미 날아온 투표가 착지하지 못한다

**Files:**
- Create: `src/test/java/ai/devpath/community/post/ContentMutationRaceTest.java`
- Modify: `src/main/java/ai/devpath/community/post/VoteService.java`
- Modify: `src/main/java/ai/devpath/community/post/ContentAdminService.java`

**Interfaces:**
- Consumes: `CommunityAnswerRepository.findByIdForUpdate` (Task 1)
- Produces: `ContentMutationRaceTest` 의 공용 하네스(`LO`/`HI` id 공간, `isolate()`, `tx`, `pool`,
  `repOf`) — Task 3·4·5·6 이 같은 파일에 테스트를 더한다.

- [ ] **Step 1: 하네스와 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/community/post/ContentMutationRaceTest.java`:

```java
package ai.devpath.community.post;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import ai.devpath.community.post.dto.CreateAnswerRequest;
import ai.devpath.community.post.dto.CreateQuestionRequest;
import ai.devpath.community.reputation.UserReputationRepository;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * 변경 경로의 동시성 계약. 각 테스트는 <b>테스트가 첫 트랜잭션을 쥔 채</b> 두 번째 요청을
 * 워커 스레드로 던져, 확률적인 경쟁을 결정적으로 만든다.
 *
 * <p>★단언 두 개가 서로 다른 일을 한다★
 * <ul>
 *   <li>{@code get(500ms)} 가 타임아웃한다 = <b>인터리빙이 실제로 일어났다는 증거</b>.
 *       없으면 두 번째 요청이 커밋 이후에 통째로 실행돼도 테스트가 통과한다.
 *   <li>커밋 뒤의 결과(404 · 평판 0) = <b>락이 있어야만 성립하는 것</b>.
 * </ul>
 * "막혔다" 는 락이 없어도 참이다(두 번째 요청도 자기 UPDATE 에서 막힌다). 그래서 그것만으로는
 * 판별력이 0 이다.
 *
 * <p>★{@code @Transactional} 을 붙이지 않는다★ — 붙이면 워커 스레드가 커밋된 데이터를 못 본다.
 * 그래서 정리를 {@link #isolate()} 가 직접 한다.
 */
@SpringBootTest
@ActiveProfiles("test")
class ContentMutationRaceTest {

  /** 이 테스트가 독점하는 사용자 id 공간. 정리도 정확히 이 범위로만 한다. */
  private static final long LO = 9500L;
  private static final long HI = 9599L;

  @Autowired PlatformTransactionManager txm;
  @Autowired JdbcTemplate jdbc;
  @Autowired QuestionService questionService;
  @Autowired AnswerService answerService;
  @Autowired PostService postService;
  @Autowired VoteService voteService;
  @Autowired ContentAdminService contentAdmin;
  @Autowired UserReputationRepository reputations;

  TransactionTemplate tx;
  ExecutorService pool;

  @BeforeEach
  void isolate() {
    tx = new TransactionTemplate(txm);
    pool = Executors.newSingleThreadExecutor();
    jdbc.update("DELETE FROM community_votes WHERE user_id BETWEEN ? AND ?", LO, HI);
    jdbc.update("DELETE FROM reputation_events WHERE user_id BETWEEN ? AND ?"
        + " OR actor_id BETWEEN ? AND ?", LO, HI, LO, HI);
    jdbc.update("DELETE FROM user_tag_reputation WHERE user_id BETWEEN ? AND ?", LO, HI);
    jdbc.update("DELETE FROM user_reputation WHERE user_id BETWEEN ? AND ?", LO, HI);
    jdbc.update("DELETE FROM user_badges WHERE user_id BETWEEN ? AND ?", LO, HI);
    jdbc.update("DELETE FROM community_comments WHERE author_id BETWEEN ? AND ?"
        + " OR post_id IN (SELECT id FROM community_posts WHERE author_id BETWEEN ? AND ?)",
        LO, HI, LO, HI);
    jdbc.update("DELETE FROM community_answers WHERE author_id BETWEEN ? AND ?"
        + " OR question_id IN (SELECT id FROM community_posts WHERE author_id BETWEEN ? AND ?)",
        LO, HI, LO, HI);
    jdbc.update("DELETE FROM community_post_tags WHERE post_id IN"
        + " (SELECT id FROM community_posts WHERE author_id BETWEEN ? AND ?)", LO, HI);
    jdbc.update("DELETE FROM community_questions WHERE post_id IN"
        + " (SELECT id FROM community_posts WHERE author_id BETWEEN ? AND ?)", LO, HI);
    jdbc.update("DELETE FROM community_posts WHERE author_id BETWEEN ? AND ?", LO, HI);
  }

  @AfterEach
  void stopPool() {
    pool.shutdownNow();
  }

  int repOf(long userId) {
    return reputations.findByUserId(userId).map(r -> r.getTotal()).orElse(0);
  }

  /** 워커 스레드에서 자기 트랜잭션으로 실행한다. */
  Future<?> inAnotherTransaction(Runnable body) {
    return pool.submit(() -> tx.execute(st -> {
      body.run();
      return null;
    }));
  }

  /** 아직 진행 중이어야 한다 = 인터리빙이 실제로 일어났다는 증거. */
  void assertStillInFlight(Future<?> f) {
    assertThatThrownBy(() -> f.get(500, TimeUnit.MILLISECONDS))
        .as("인터리빙 증거: 두 번째 요청이 아직 진행 중이어야 한다")
        .isInstanceOf(TimeoutException.class);
  }

  @Test
  void inFlightUpvoteCannotLandOnAnAnswerThatWasJustHidden() {
    long asker = 9501, answerer = 9502, firstVoter = 9503, raceVoter = 9504;
    long answerId = tx.execute(st -> {
      var q = questionService.create(asker, new CreateQuestionRequest("t", "b", List.of()));
      return answerService.add(answerer, q.id(), new CreateAnswerRequest("ans")).id();
    });

    // 대조군: 내려가기 전 upvote 는 실제로 평판을 올린다. 이게 없으면 아래 "0 유지" 가
    // 락 때문인지 애초에 평판이 안 붙은 것인지 구분할 수 없다.
    tx.executeWithoutResult(st -> voteService.voteAnswer(firstVoter, answerId, 1));
    assertThat(repOf(answerer)).isEqualTo(10);

    Future<?>[] vote = new Future<?>[1];
    tx.executeWithoutResult(st -> {
      contentAdmin.hideAnswer(answerId);        // 락 획득 + 평판 회수, 아직 커밋 전
      vote[0] = inAnotherTransaction(() -> voteService.voteAnswer(raceVoter, answerId, 1));
      assertStillInFlight(vote[0]);
    });                                          // 커밋 → 해제

    assertThatThrownBy(() -> vote[0].get(10, TimeUnit.SECONDS))
        .isInstanceOf(ExecutionException.class)
        .hasCauseInstanceOf(NotFoundException.class);
    assertThat(repOf(answerer)).as("락이 없으면 여기가 10 이 된다").isZero();
  }
}
```

- [ ] **Step 2: 실행해 red 를 확인하고, 사유가 맞는지 본다**

```bash
DB_URL=jdbc:postgresql://localhost:5432/devpath_run40 DB_USER=devpath DB_PASSWORD=localdev \
GITHUB_ACTOR=$(gh api user --jq .login) GITHUB_TOKEN=$(gh auth token) \
  ./gradlew test --tests '*ContentMutationRaceTest*' > /tmp/t.log 2>&1; echo "GRADLE_EXIT=$?"
grep -oE 'message="[^"]{0,200}' \
  build/test-results/test/TEST-ai.devpath.community.post.ContentMutationRaceTest.xml
```

기대: `expected: 0 but was: 10` 또는 그에 준하는 평판 단언 실패.
★`TimeoutException`(인터리빙 단언 실패)이 나오면 red 의 이유가 다르다★ — 워커가 아예 안 떴거나
락 없이도 안 막히는 것이므로, 그 원인을 먼저 규명한다.

- [ ] **Step 3: 두 경로를 잠금 조회로 바꾼다**

`VoteService.voteAnswer` 의 답변 조회를:

```java
    CommunityAnswer a = answers.findByIdForUpdate(answerId)
        .filter(found -> ContentStatus.PUBLISHED.equals(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("answer " + answerId));
```

`ContentAdminService.hideAnswer` 의 답변 조회를:

```java
    CommunityAnswer a = answers.findByIdForUpdate(answerId)
        .filter(found -> takedownable(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("answer " + answerId));
```

두 곳 모두 `.filter(...)` 이후는 **한 글자도 바꾸지 않는다.**

- [ ] **Step 4: green 확인**

```bash
DB_URL=jdbc:postgresql://localhost:5432/devpath_run40 DB_USER=devpath DB_PASSWORD=localdev \
GITHUB_ACTOR=$(gh api user --jq .login) GITHUB_TOKEN=$(gh auth token) \
  ./gradlew test --tests '*ContentMutationRaceTest*' > /tmp/t.log 2>&1; echo "GRADLE_EXIT=$?"
grep -oE 'tests="[0-9]+" skipped="[0-9]+" failures="[0-9]+" errors="[0-9]+"' \
  build/test-results/test/TEST-ai.devpath.community.post.ContentMutationRaceTest.xml
```

기대: `tests="1" ... failures="0" errors="0"`

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/community/post/VoteService.java \
        src/main/java/ai/devpath/community/post/ContentAdminService.java \
        src/test/java/ai/devpath/community/post/ContentMutationRaceTest.java
git commit -m "fix(community): 내려간 답변에 이미 날아온 투표가 착지하지 못하게 한다

투표와 내리기가 각자 status 를 PUBLISHED 로 읽은 뒤 커밋하는 창이 있었다. 투표의
UPDATE 는 상태 조건 없이 덮어쓰므로 회수한 평판이 10 으로 복원됐다.

두 경로가 같은 행을 잠가 직렬화된다. READ COMMITTED 에서 FOR UPDATE 는 락을 얻은 뒤
행을 다시 읽으므로(측정함), 뒤따르는 status 판정이 비로소 신뢰할 수 있게 된다.
응답 코드는 바뀌지 않는다 - 진 쪽은 지금과 같은 404 를 받는다."
```

---

### Task 3: R2 — 삭제 중인 답변을 채택할 수 없다

**Files:**
- Modify: `src/test/java/ai/devpath/community/post/ContentMutationRaceTest.java`
- Modify: `src/main/java/ai/devpath/community/post/AnswerService.java`

**Interfaces:**
- Consumes: Task 2 의 하네스, Task 1 의 `findByIdForUpdate`

- [ ] **Step 1: 실패하는 테스트를 더한다**

`ContentMutationRaceTest` 에 추가:

```java
  @Test
  void acceptCannotLandOnAnAnswerThatIsBeingDeleted() {
    long asker = 9511, answerer = 9512;
    long[] ids = tx.execute(st -> {
      var q = questionService.create(asker, new CreateQuestionRequest("t", "b", List.of()));
      var a = answerService.add(answerer, q.id(), new CreateAnswerRequest("ans"));
      return new long[] {q.id(), a.id()};
    });
    long questionId = ids[0];
    long answerId = ids[1];

    Future<?>[] accept = new Future<?>[1];
    tx.executeWithoutResult(st -> {
      answerService.delete(answerer, answerId);   // 락 획득 + DELETED, 아직 커밋 전
      accept[0] = inAnotherTransaction(() -> answerService.accept(asker, answerId));
      assertStillInFlight(accept[0]);
    });                                            // 커밋 → 해제

    assertThatThrownBy(() -> accept[0].get(10, TimeUnit.SECONDS))
        .isInstanceOf(ExecutionException.class)
        .hasCauseInstanceOf(NotFoundException.class);
    assertThat(questionService.detail(questionId).solved())
        .as("락이 없으면 solved 가 삭제된 답변을 가리킨다").isFalse();
    assertThat(repOf(answerer)).as("락이 없으면 채택 보상 +15 가 나간다").isZero();
  }
```

- [ ] **Step 2: 실행해 red 확인**

Task 2 Step 2 와 같은 명령. 기대 사유: `solved` 또는 평판 단언 실패
(`expected: false but was: true` 또는 `expected: 0 but was: 15`).

- [ ] **Step 3: `accept` 와 `delete` 를 잠금 조회로 바꾼다**

`AnswerService.accept` 의 답변 조회:

```java
    CommunityAnswer a = answers.findByIdForUpdate(answerId)
        .filter(found -> ContentStatus.PUBLISHED.equals(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("answer " + answerId));
```

`AnswerService.delete` 의 답변 조회:

```java
    CommunityAnswer a = answers.findByIdForUpdate(answerId)
        .filter(found -> ContentStatus.PUBLISHED.equals(found.getStatus()))
        .orElseThrow(() -> new NotFoundException("answer " + answerId));
```

`accept` 의 부모 글 조회(`posts.findById(q.getPostId())`)는 **그대로 둔다** — 교착 방지 규칙상
명시적 락은 직접 대상 한 행만 잡는다.

- [ ] **Step 4: green 확인** (기대: `tests="2" ... failures="0"`)

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/community/post/AnswerService.java \
        src/test/java/ai/devpath/community/post/ContentMutationRaceTest.java
git commit -m "fix(community): 삭제 중인 답변을 채택할 수 없게 한다

채택과 작성자 삭제가 각자 status 를 읽은 뒤 커밋하는 창이 있었다. 채택이 이기면
solved 가 사라진 답변을 가리킨 채 +15/+2 가 나갔다.

두 경로가 답변 행을 잠가 직렬화된다. 부모 글 조회는 잠그지 않는다 - 교착 방지 규칙상
명시적 락은 직접 대상 한 행만 잡는다."
```

---

### Task 4: R4 — 같은 사용자의 더블클릭이 500 을 내지 않는다 (되돌림 증명)

**Files:**
- Modify: `src/test/java/ai/devpath/community/post/ContentMutationRaceTest.java`

★**이 테스트는 처음부터 green 이다**★ — Task 2 의 답변 락이 R4 를 덤으로 닫았다. 그러므로
**Step 3 의 되돌림 관측이 이 태스크의 본체**다. 그것 없이는 이 테스트가 무엇이든 지킨다고
말할 수 없다.

- [ ] **Step 1: 테스트를 더한다**

```java
  @Test
  void sameUserVotingTwiceConcurrentlyDoesNotViolateTheVoteUniqueConstraint() {
    long asker = 9521, answerer = 9522, voter = 9523;
    long answerId = tx.execute(st -> {
      var q = questionService.create(asker, new CreateQuestionRequest("t", "b", List.of()));
      return answerService.add(answerer, q.id(), new CreateAnswerRequest("ans")).id();
    });

    Future<?>[] second = new Future<?>[1];
    tx.executeWithoutResult(st -> {
      voteService.voteAnswer(voter, answerId, 1);   // 표를 넣고 아직 커밋 전
      second[0] = inAnotherTransaction(() -> voteService.voteAnswer(voter, answerId, 1));
      assertStillInFlight(second[0]);
    });                                              // 커밋 → 해제

    // 예외 없이 끝나야 한다. 락이 없으면 유니크 위반이 rollback-only 를 만들어 여기서 터진다.
    awaitSuccess(second[0]);

    Integer votes = jdbc.queryForObject(
        "SELECT count(*) FROM community_votes WHERE user_id = ? AND target_type = 'ANSWER'"
            + " AND target_id = ?", Integer.class, voter, answerId);
    assertThat(votes).as("표는 한 행이어야 한다").isEqualTo(1);
    assertThat(repOf(answerer)).as("평판은 한 번만 붙는다").isEqualTo(10);
  }
```

하네스에 헬퍼를 더한다:

```java
  /** 워커가 예외 없이 끝났음을 단언하고 결과를 돌려준다. */
  Object awaitSuccess(Future<?> f) {
    try {
      return f.get(10, TimeUnit.SECONDS);
    } catch (Exception e) {
      throw new AssertionError("워커가 정상 종료해야 한다", e);
    }
  }
```

- [ ] **Step 2: 실행해 green 확인** (기대: `tests="3" ... failures="0"`)

- [ ] **Step 3: ★되돌림 관측 — 이 태스크의 본체★**

`VoteService.voteAnswer` 의 `answers.findByIdForUpdate(answerId)` 를 `answers.findById(answerId)`
로 **잠시** 되돌린 뒤 이 테스트만 실행한다:

```bash
DB_URL=jdbc:postgresql://localhost:5432/devpath_run40 DB_USER=devpath DB_PASSWORD=localdev \
GITHUB_ACTOR=$(gh api user --jq .login) GITHUB_TOKEN=$(gh auth token) \
  ./gradlew test --tests '*ContentMutationRaceTest.sameUserVotingTwice*' > /tmp/t.log 2>&1
echo "GRADLE_EXIT=$?"
grep -oE 'message="[^"]{0,300}' \
  build/test-results/test/TEST-ai.devpath.community.post.ContentMutationRaceTest.xml
```

**기대**: red. 사유에 `DataIntegrityViolation` · `duplicate key` · `uq_community_votes` ·
`rollback-only` 중 하나 이상이 보여야 한다.

red 가 **안 나오면** 이 테스트는 아무것도 지키지 않는 것이다. 그때는 시나리오를 고친다
(예: 두 번째 요청이 첫 표를 정말로 못 보는지 `currentValue` 결과를 로그로 확인).

관측한 사유 문자열을 커밋 메시지에 넣는다. 그다음 `findByIdForUpdate` 로 **되돌려 놓는다.**

- [ ] **Step 4: 되돌린 뒤 green 재확인**

- [ ] **Step 5: 커밋**

```bash
git add src/test/java/ai/devpath/community/post/ContentMutationRaceTest.java
git commit -m "test(community): 같은 사용자 더블클릭이 유니크 위반을 내지 않음을 지킨다

Task 2 의 답변 락이 이 경쟁을 덤으로 닫았으므로 이 테스트는 처음부터 green 이다.
그래서 락을 findById 로 되돌려 red 를 실제로 관측했다: <Step 3 에서 본 사유>

되돌림 관측이 없으면 green 인데 아무것도 검증하지 않는 테스트가 된다."
```

---

### Task 5: R1-글 — 내려간 글에 이미 날아온 투표가 착지하지 못한다

**Files:**
- Modify: `src/main/java/ai/devpath/community/post/CommunityPostRepository.java`
- Modify: `src/main/java/ai/devpath/community/post/VoteService.java`
- Modify: `src/main/java/ai/devpath/community/post/ContentAdminService.java`
- Modify: `src/test/java/ai/devpath/community/post/ContentMutationRaceTest.java`

**Interfaces:**
- Produces: `CommunityPostRepository.findByIdForUpdate(long) : Optional<CommunityPost>` — Task 6 이 쓴다.

- [ ] **Step 1: 실패하는 테스트를 더한다**

```java
  @Test
  void inFlightVoteCannotLandOnAPostThatWasJustHidden() {
    long author = 9531, firstVoter = 9532, raceVoter = 9533;
    long postId = tx.execute(st ->
        questionService.create(author, new CreateQuestionRequest("t", "b", List.of())).id());

    // 대조군: 내려가기 전 downvote 는 실제로 평판을 내린다(글 downvote 는 평판 게이트가 없다).
    tx.executeWithoutResult(st -> voteService.votePost(firstVoter, postId, -1));
    assertThat(repOf(author)).isEqualTo(-2);

    Future<?>[] vote = new Future<?>[1];
    tx.executeWithoutResult(st -> {
      contentAdmin.hidePost(postId);            // 락 획득 + 평판 회수, 아직 커밋 전
      vote[0] = inAnotherTransaction(() -> voteService.votePost(raceVoter, postId, -1));
      assertStillInFlight(vote[0]);
    });                                          // 커밋 → 해제

    assertThatThrownBy(() -> vote[0].get(10, TimeUnit.SECONDS))
        .isInstanceOf(ExecutionException.class)
        .hasCauseInstanceOf(NotFoundException.class);
    assertThat(repOf(author)).as("락이 없으면 -2 가 다시 붙는다").isZero();
  }
```

- [ ] **Step 2: 실행해 red 확인** (기대 사유: `expected: 0 but was: -2`)

- [ ] **Step 3: 글 잠금 조회를 더한다**

`CommunityPostRepository` 에 추가(Task 1 의 답변 쪽과 같은 모양. **Task 1 Step 5 로 갔다면
`@QueryHints` 줄은 넣지 않는다** — 그때는 커넥션 옵션이 전역으로 적용된다):

```java
  @Lock(LockModeType.PESSIMISTIC_WRITE)
  @Query("select p from CommunityPost p where p.id = :id")
  Optional<CommunityPost> findByIdForUpdate(@Param("id") long id);
```

필요한 import: `jakarta.persistence.LockModeType` · `java.util.Optional` ·
`org.springframework.data.jpa.repository.Lock` · `org.springframework.data.jpa.repository.Query` ·
`org.springframework.data.repository.query.Param`.

- [ ] **Step 4: 두 경로를 바꾼다**

`VoteService.publishedPost(long postId)` 안의 조회를 `posts.findByIdForUpdate(postId)` 로 바꾼다
(이 private 헬퍼를 `votePost` 와 `voteAnswer` 가 함께 쓴다 — `voteAnswer` 의 부모 확인도 같이
잠기게 되는데, 이는 교착 규칙을 어기지 않는다. 답변 락을 이미 쥔 뒤 글을 잠그므로 순서가
**답변 → 글** 로 고정되고, 반대 순서로 잠그는 경로가 없다).

`ContentAdminService.hidePost` 의 조회를 `posts.findByIdForUpdate(postId)` 로 바꾼다.

- [ ] **Step 5: green 확인** (기대: `tests="4" ... failures="0"`)

- [ ] **Step 6: 전체 스위트로 회귀 확인**

```bash
docker exec devpath-pg psql -U devpath -d postgres \
  -c "CREATE DATABASE devpath_run41 TEMPLATE devpath_tpl OWNER devpath"
docker exec devpath-pg psql -U devpath -d devpath_run41 -tAc \
  "SELECT setval('community_posts_id_seq',41000000), setval('community_answers_id_seq',41000000), setval('community_comments_id_seq',41000000)"
DB_URL=jdbc:postgresql://localhost:5432/devpath_run41 DB_USER=devpath DB_PASSWORD=localdev \
GITHUB_ACTOR=$(gh api user --jq .login) GITHUB_TOKEN=$(gh auth token) \
  ./gradlew test > /tmp/t.log 2>&1; echo "GRADLE_EXIT=$?"
grep -h -oE 'tests="[0-9]+"|failures="[0-9]+"|errors="[0-9]+"' build/test-results/test/*.xml \
  | awk -F'"' '{s[$1]+=$2} END{for(k in s) print k, s[k]}'
```

기대: `failures= 0`, `errors= 0`, `tests=` **187** — 기존 182 + `LockTimeoutProbeTest` 1 +
`ContentMutationRaceTest` 4(이 시점 기준). ★Task 1 이 대체 경로(Step 5)로 갔다면 프로브가 2 건
이므로 **188**★. `RevokeDurationProbeTest` 는 Task 7 에서 생기므로 아직 없다.
★교착이 생겼다면 여기서 드러난다★ — 특정 테스트가 락 타임아웃으로 실패하면 Step 4 의 순서
설명을 다시 검토한다.

- [ ] **Step 7: 커밋**

```bash
git add src/main/java/ai/devpath/community/post/CommunityPostRepository.java \
        src/main/java/ai/devpath/community/post/VoteService.java \
        src/main/java/ai/devpath/community/post/ContentAdminService.java \
        src/test/java/ai/devpath/community/post/ContentMutationRaceTest.java
git commit -m "fix(community): 내려간 글에 이미 날아온 투표가 착지하지 못하게 한다

답변과 같은 창이 글에도 있었다. 글 잠금 조회를 더하고 votePost 와 hidePost 가 쓴다.

voteAnswer 의 부모 글 확인도 같은 헬퍼를 통해 잠기는데, 답변을 먼저 잠근 뒤 글을
잠그므로 순서가 답변 -> 글 로 고정된다. 반대 순서로 잠그는 경로는 없다."
```

---

### Task 6: R5 — 동시 투표에서 집계가 유실되지 않는다 (되돌림 증명)

**Files:**
- Modify: `src/test/java/ai/devpath/community/post/ContentMutationRaceTest.java`

★Task 5 의 글 락이 이미 닫았으므로 처음부터 green 이다. **Step 3 의 되돌림 관측이 본체.**★

- [ ] **Step 1: 테스트를 더한다**

```java
  @Test
  void concurrentVotesFromTwoUsersDoNotLoseTheAggregate() {
    long author = 9541, voterA = 9542, voterB = 9543;
    long postId = tx.execute(st ->
        questionService.create(author, new CreateQuestionRequest("t", "b", List.of())).id());

    Future<?>[] b = new Future<?>[1];
    tx.executeWithoutResult(st -> {
      voteService.votePost(voterA, postId, -1);   // A 의 표, 아직 커밋 전
      b[0] = inAnotherTransaction(() -> voteService.votePost(voterB, postId, -1));
      assertStillInFlight(b[0]);
    });                                            // 커밋 → 해제
    awaitSuccess(b[0]);

    Integer stored = jdbc.queryForObject(
        "SELECT downvote_count FROM community_posts WHERE id = ?", Integer.class, postId);
    assertThat(stored).as("락이 없으면 B 가 A 를 못 세어 1 이 저장된다").isEqualTo(2);
  }
```

- [ ] **Step 2: 실행해 green 확인** (기대: `tests="5" ... failures="0"`)

- [ ] **Step 3: ★되돌림 관측★**

`VoteService.publishedPost` 의 `posts.findByIdForUpdate(postId)` 를 `posts.findById(postId)` 로
**잠시** 되돌린 뒤 이 테스트만 실행한다.

**기대**: red, 사유 `expected: 2 but was: 1`.

red 가 안 나오면 이 테스트는 아무것도 지키지 않는다. 관측한 사유를 커밋 메시지에 넣고
`findByIdForUpdate` 로 **되돌려 놓는다.**

- [ ] **Step 4: 되돌린 뒤 green 재확인**

- [ ] **Step 5: 커밋**

```bash
git add src/test/java/ai/devpath/community/post/ContentMutationRaceTest.java
git commit -m "test(community): 동시 투표에서 집계가 유실되지 않음을 지킨다

refreshPostCounts 는 COUNT 후 set 이라 두 투표가 겹치면 나중 것이 옛 수를 덮어썼다.
자가 치유되지만 그 사이 answerNet >= 1 판정으로 배지가 잘못 나간다.

Task 5 의 글 락이 덤으로 닫았으므로 락을 findById 로 되돌려 red 를 관측했다:
<Step 3 에서 본 사유>"
```

---

### Task 7: 회수 소요를 재고, 락 유지 시간이 타임아웃 안에 있음을 확인한다

**Files:**
- Create: `src/test/java/ai/devpath/community/post/RevokeDurationProbeTest.java`

스펙 §7 이 알린 위험이다 — `revokeAllForSource` 는 회수 대상 **이벤트 수에 비례**한다. 락을 쥔
채 도는 코드이므로, 이벤트가 아주 많으면 다른 요청이 3초 타임아웃에 걸린다.

- [ ] **Step 1: 재는 테스트를 쓴다**

```java
package ai.devpath.community.post;

import static org.assertj.core.api.Assertions.assertThat;

import ai.devpath.community.post.dto.CreateAnswerRequest;
import ai.devpath.community.post.dto.CreateQuestionRequest;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * ★락을 쥐고 도는 시간이 락 타임아웃 안에 있어야 한다★
 *
 * <p>{@code revokeAllForSource} 만 회수 대상 이벤트 수에 비례한다. 나머지 잠금 경로는
 * 단일 행 갱신이라 상수 시간이다.
 */
@SpringBootTest
@ActiveProfiles("test")
class RevokeDurationProbeTest {

  private static final long LO = 9700L;
  private static final long HI = 9999L;

  @Autowired PlatformTransactionManager txm;
  @Autowired org.springframework.jdbc.core.JdbcTemplate jdbc;
  @Autowired QuestionService questionService;
  @Autowired AnswerService answerService;
  @Autowired VoteService voteService;
  @Autowired ContentAdminService contentAdmin;

  /**
   * ★재실행 안전성이 이 테스트에서는 측정 유효성의 문제다★ — 정리하지 않으면 작성자
   * 9702 의 <b>오늘자 upvote 획득합</b>이 남아 일일 상한(40)에 걸린다. 상한을 넘으면
   * {@code capDailyUpvote} 가 0 을 돌려주고 {@code if (granted != 0)} 때문에
   * <b>이벤트가 아예 안 쌓인다</b>. 그러면 회수는 순식간에 끝나고 테스트는 green 인데
   * 아무것도 재지 않은 것이 된다.
   */
  @org.junit.jupiter.api.BeforeEach
  void isolate() {
    jdbc.update("DELETE FROM community_votes WHERE user_id BETWEEN ? AND ?", LO, HI);
    jdbc.update("DELETE FROM reputation_events WHERE user_id BETWEEN ? AND ?"
        + " OR actor_id BETWEEN ? AND ?", LO, HI, LO, HI);
    jdbc.update("DELETE FROM user_tag_reputation WHERE user_id BETWEEN ? AND ?", LO, HI);
    jdbc.update("DELETE FROM user_reputation WHERE user_id BETWEEN ? AND ?", LO, HI);
    jdbc.update("DELETE FROM user_badges WHERE user_id BETWEEN ? AND ?", LO, HI);
    jdbc.update("DELETE FROM community_answers WHERE author_id BETWEEN ? AND ?"
        + " OR question_id IN (SELECT id FROM community_posts WHERE author_id BETWEEN ? AND ?)",
        LO, HI, LO, HI);
    jdbc.update("DELETE FROM community_questions WHERE post_id IN"
        + " (SELECT id FROM community_posts WHERE author_id BETWEEN ? AND ?)", LO, HI);
    jdbc.update("DELETE FROM community_posts WHERE author_id BETWEEN ? AND ?", LO, HI);
  }

  @Test
  void takedownOfAHeavilyVotedAnswerStaysWellUnderTheLockTimeout() {
    TransactionTemplate tx = new TransactionTemplate(txm);
    long answerId = tx.execute(st -> {
      var q = questionService.create(9701L, new CreateQuestionRequest("t", "b", List.of()));
      return answerService.add(9702L, q.id(), new CreateAnswerRequest("ans")).id();
    });
    // 서로 다른 투표자 200 명.
    for (long v = 9800L; v < 10000L; v++) {
      final long voter = v;
      tx.executeWithoutResult(st -> voteService.voteAnswer(voter, answerId, 1));
    }

    // ★측정법 유효성을 먼저 세운다★ — 회수가 훑는 것은 이벤트 행 수다. 일일 상한이나
    // 정리 실패로 이벤트가 적으면 아래 소요 측정은 아무것도 재지 않는다.
    Integer targets = jdbc.queryForObject(
        "SELECT count(*) FROM reputation_events WHERE source_type = 'ANSWER' AND source_id = ?",
        Integer.class, answerId);
    assertThat(targets)
        .as("회수 대상 이벤트가 충분해야 소요 측정이 의미를 갖는다. 실측: %d 건", targets)
        .isGreaterThan(3);

    long startedAt = System.nanoTime();
    tx.executeWithoutResult(st -> contentAdmin.hideAnswer(answerId));
    long elapsedMs = (System.nanoTime() - startedAt) / 1_000_000L;

    assertThat(elapsedMs)
        .as("락 타임아웃 3000ms 의 1/3 안에 끝나야 여유가 있다. 실측: %d ms (이벤트 %d 건)",
            elapsedMs, targets)
        .isLessThan(1000L);
  }
}
```

- [ ] **Step 2: 실행하고 실측치를 기록한다**

```bash
DB_URL=jdbc:postgresql://localhost:5432/devpath_run41 DB_USER=devpath DB_PASSWORD=localdev \
GITHUB_ACTOR=$(gh api user --jq .login) GITHUB_TOKEN=$(gh auth token) \
  ./gradlew test --tests '*RevokeDurationProbeTest*' > /tmp/t.log 2>&1; echo "GRADLE_EXIT=$?"
grep -oE 'message="[^"]{0,200}' \
  build/test-results/test/TEST-ai.devpath.community.post.RevokeDurationProbeTest.xml
```

green 이면 실측치를 커밋 메시지에 적는다. red 면 **가정이 틀린 것이다** — 그때는 회수를 락
밖으로 빼는 설계 변경이 필요하므로 **멈추고 보고한다.** 임의로 타임아웃을 늘리지 않는다.

- [ ] **Step 3: 커밋**

```bash
git add src/test/java/ai/devpath/community/post/RevokeDurationProbeTest.java
git commit -m "test(community): 회수가 락 타임아웃 안에 끝남을 지킨다

revokeAllForSource 만 이벤트 수에 비례한다. 투표자 200 명이 붙은 답변을 내리는 데
<실측치> ms 가 걸렸다(타임아웃 3000ms)."
```

---

### Task 8: 동시성 관례를 조직 문서로 남긴다

**Files:**
- Create: `documents/48_동시성_제어_관례.md`

레포: `documents`, 브랜치 `docs/concurrency-convention` (`develop` 에서 분기).

- [ ] **Step 1: 문서를 쓴다**

`documents/48_동시성_제어_관례.md` 에 아래를 담는다. 각 항목은 **측정 결과이거나 이 프로젝트가
실제로 겪은 사고**이며, 근거 없는 일반론을 넣지 않는다.

1. **집의 방식은 "DB 가 심판"** — 앱 레벨 락(`@Version`·`@Lock`)이 9 개 레포에 **0 건**이었고,
   6 개 서비스가 유니크 제약 + `DataIntegrityViolationException` 으로 간다.
2. ★**`@Transactional` 안에서 `DataIntegrityViolationException` 을 잡지 말 것**★ — rollback-only
   로 마킹돼 커밋 시점에 다시 터진다. 이 프로젝트가 광고 기능에서 겪었고
   `ReportService` 주석에 남아 있다. **트랜잭션 안에서는 예외를 던지지 않는 수단만 쓴다.**
3. **언제 무엇을**
   - 중복 삽입을 막는다 → 유니크 제약. 단 포착은 트랜잭션 **밖**에서.
   - read-modify-write 를 직렬화한다 → `SELECT ... FOR UPDATE`.
   - 단일 문장으로 표현된다 → 조건부 UPDATE + 영향 행 수 판정.
4. **락 순서 규칙** — 명시적 락은 직접 대상 한 행만. 이어지는 갱신 순서를 문서에 고정한다.
   community-svc 는 **답변 → 질문**, 그리고 답변 락을 쥔 뒤에만 글을 잠근다.
5. **`lock_timeout` 은 반드시 유한**하고, 유한함을 테스트로 증명한다. 락을 쥔 채 도는 코드의
   소요도 함께 잰다.
6. ★**동시성 주장은 대조군을 세워 측정한다**★ — 예: `FOR UPDATE` 가 재읽기하는지 확인할 때
   plain `SELECT` 를 대조군으로 두어야 "락이 결과를 바꿨다" 고 말할 수 있다.
7. ★**"막혔다" 는 락의 증거가 아니다**★ — 락이 없어도 두 번째 요청은 자기 UPDATE 에서 막힌다.
   판별하는 것은 커밋 이후의 **결과**다. "막혔다" 는 인터리빙이 일어났다는 별개의 증거로 쓴다.
8. **덤으로 닫힌 경쟁의 테스트는 되돌림으로 증명한다** — 가드를 잠시 빼서 red 를 관측하지
   않으면 green 인데 아무것도 검증하지 않는 테스트가 된다.

문서 끝에 근거 링크를 단다:
`docs/superpowers/specs/2026-08-21-community-concurrency-control-design.md`

- [ ] **Step 2: 커밋**

```bash
cd /d/workspace/dpa/documents
git add 48_동시성_제어_관례.md
git commit -m "docs: 동시성 제어 관례를 조직 표준으로 남긴다

community-svc 의 경쟁 네 건을 닫으며 정한 방식이다. 근거는 전부 측정이거나 이
프로젝트가 실제로 겪은 사고이며, 일반론은 넣지 않았다."
```

---

## 완료 기준 (스펙 §9)

- [ ] 경쟁 테스트 **5 건**이 green
- [ ] Task 4·6 의 **되돌림 관측**이 실제로 red 를 냈고 그 사유가 커밋 메시지에 남았다
- [ ] community-svc 전체 스위트 **189 건**, failures 0 · errors 0
      (기존 182 + 프로브 1 + 경쟁 5 + 회수 소요 1. ★Task 1 이 대체 경로로 갔다면 **190**★)
- [ ] `lock_timeout` 이 유한하다는 **실측 증거**가 있다 (Task 1)
- [ ] 락을 쥐고 도는 최장 경로의 **실측 소요**가 타임아웃 안에 있다 (Task 7)
- [ ] `documents/48_동시성_제어_관례.md` 가 존재한다
- [ ] 프론트엔드 레포에 **변경 0** (API 계약이 안 바뀌었다는 증거)
