# AI provider 폴백 — 가용성을 보는 체인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 세 기능(review · community-seed · retention)에서 Ollama 폴백을 쓸 수 없을 때 Claude 의 성공률과 지연이 폴백을 끈 상태와 같아지게 한다.

**Architecture:** 요청마다 `ProviderAttemptPlan` 이 래치 상태로 시도 목록을 만들고, 뒤에 쓸 수 있는 provider 가 없는 시도에는 SDK 기본 재시도를 가진 「마지막 수단」 Claude 클라이언트(`AnthropicClient.withOptions` 로 파생)를 쓴다. 폴백 자리의 Ollama 는 30초마다 생존 탐색(`/api/tags` + 모델 존재)을 받아 죽으면 래치가 즉시 열린다. Ollama 연결 타임아웃은 3초로 분리하고, Ollama 404 는 가용성 실패로 분류한다.

**Tech Stack:** Java 21 · Spring Boot 4.0.7(Spring Framework 7.0.8) · `com.anthropic:anthropic-java:2.34.0` · JUnit 5 · `okhttp3.mockwebserver` 4.12.0 · Gradle 9.5.1(Kotlin DSL)

**Spec:** `documents/docs/superpowers/specs/2026-10-03-ai-fallback-availability-aware-retries-design.md`

## Global Constraints

- 대상 레포 `D:/workspace/dpa/devpath-ai-svc`. 작업 브랜치 `feat/ai-fallback-availability-aware-retries` 를 `origin/develop` 에서 분기하고 PR 은 `develop` 으로만 한다. `main` 에 직접 커밋·푸시하지 않는다.
- 모든 git 명령은 `git -C <절대경로>` 로 쓴다. `cd` 후 상대경로 명령을 이어 쓰지 않는다.
- TDD: 각 Task 는 실패하는 테스트를 먼저 쓰고 실패를 눈으로 본 뒤 구현한다.
- 테스트 실행은 Git Bash 에서 래퍼를 **절대경로로** 부른다: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests '<FQCN>'`(작업 디렉터리에 의존하지 않는다). ★`BUILD SUCCESSFUL` 은 테스트가 실행됐다는 증거가 아니다 — `D:/workspace/dpa/.worktrees/ai-svc-aifb/build/test-results/test/TEST-<FQCN>.xml` 의 `tests=`·`failures=`·`errors=` 를 확인한다★
- 들여쓰기는 파일마다 기존 것을 따른다: `provider`·`review`·`community` 패키지는 **공백 2칸**, `retention` 패키지는 **탭**.
- 멘토(`ai.devpath.aigw.mentor`)는 바꾸지 않는다. `ProviderFailures`·`ProviderLatch` 는 멘토가 쓰지 않는다(실측).
- 설정 키와 기본값(스펙 §4 그대로): `devpath.provider.liveness-interval` = `PT30S` · `devpath.review.ollama-connect-timeout` = `PT3S` · `devpath.community-seed.ollama-connect-timeout` = `PT3S` · `devpath.retention.ollama-connect-timeout` = `PT3S`. 생존 탐색의 읽기 타임아웃 = 5초(고정 상수).
- 기존 빈 이름(`anthropicClient` · `communitySeedAnthropicClient` · `retentionAnthropicClient`)과 그 재시도 규칙(`ClaudeClients.maxRetriesFor`)은 바꾸지 않는다. 「마지막 수단」 클라이언트는 **빈이 아니다** — 기능별 ClientConfig 안에서 `ClaudeClients.lastResort(...)` 로 파생한다(`ClaudeBeanConditionTest` 의 빈 3개 단언 유지).
- fallback 이 비어 있는 환경(체인 길이 1)에서는 동작·트래픽 변화가 0 이어야 한다 — 래퍼가 끼지 않고, Ollama 탐색 빈이 생기지 않는다.

## Review Focus

1. **fallback CSV 의 공백·중복**(`" ollama , "`) — 탐색 빈 조건과 체인 순서가 같은 규칙(`ProviderChain.requestedNames`: trim·중복 제거)을 써야 한다. → Task 12 `isFallbackTrimsAndDeduplicates`.
2. **비슷하지만 다른 모델 태그**(`qwen2.5:7b-instruct` 만 있고 `qwen2.5:7b` 는 없음) — 정확히 같은 이름만 「있음」이다. → Task 10 `aSimilarTagDoesNotCountAsTheConfiguredModel`.
3. **느린 Ollama**(응답이 읽기 타임아웃을 넘김) — 생존 탐색이 스케줄러를 붙들지 않고 TRANSIENT 로 래치를 연다. → Task 10 `aSlowTagsResponseFailsWithinTheReadTimeout` · Task 11 `livenessFailureOpensTheLatchImmediately`.
4. **요청 도중 래치가 바뀜** — 한 요청의 계획은 provider 마다 래치를 한 번만 읽는다(스냅샷). → Task 1 `consultsTheLatchOncePerProvider`.
5. **기록되는 provider 이름** — 「마지막 수단」 구현체로 응답해도 저장·발행되는 이름은 `CLAUDE` 다. → Task 7·8·9 `reportsClaudeWhenTheLastResortVariantServed`.

---

### Task 0: 작업 트리와 기준선

**Files:** 없음(환경)

- [ ] **Step 1: 워크트리 생성**

```bash
git -C D:/workspace/dpa/devpath-ai-svc fetch origin
git -C D:/workspace/dpa/devpath-ai-svc worktree add -b feat/ai-fallback-availability-aware-retries D:/workspace/dpa/.worktrees/ai-svc-aifb origin/develop
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb log --oneline -1
```

- [ ] **Step 2: 기준선 스위트**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test`
Expected: BUILD SUCCESSFUL. 그리고 `build/test-results/test/*.xml` 의 `tests=` 합계와 `failures=0 errors=0` 을 기록한다(2026-10-01 기준 359). 이후 Task 13 에서 같은 방법으로 대조한다.

---

### Task 1: `ProviderAttemptPlan` — 요청별 시도 계획(순수 함수)

**Files:**
- Create: `src/main/java/ai/devpath/aigw/provider/ProviderAttemptPlan.java`
- Test: `src/test/java/ai/devpath/aigw/provider/ProviderAttemptPlanTest.java`

**Interfaces:**
- Produces:
  - `ProviderAttemptPlan.Mode` = `enum { FAST, LAST_RESORT }`
  - `ProviderAttemptPlan.Attempt` = `record Attempt(String name, Mode mode)`
  - `static List<Attempt> ProviderAttemptPlan.plan(List<String> chain, Predicate<String> isOpen)` — `chain` 이 비면 `IllegalArgumentException`

- [ ] **Step 1: Write the failing test**

```java
package ai.devpath.aigw.provider;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import ai.devpath.aigw.provider.ProviderAttemptPlan.Attempt;
import ai.devpath.aigw.provider.ProviderAttemptPlan.Mode;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Predicate;
import org.junit.jupiter.api.Test;

class ProviderAttemptPlanTest {

  private static Predicate<String> open(String... names) {
    Set<String> set = Set.of(names);
    return set::contains;
  }

  @Test
  void bothUsableClaudeFailsFastToOllama() {
    assertEquals(
        List.of(new Attempt("claude", Mode.FAST), new Attempt("ollama", Mode.LAST_RESORT)),
        ProviderAttemptPlan.plan(List.of("claude", "ollama"), open()));
  }

  @Test
  void deadFallbackGivesClaudeTheLastResortBudget() {
    assertEquals(
        List.of(new Attempt("claude", Mode.LAST_RESORT)),
        ProviderAttemptPlan.plan(List.of("claude", "ollama"), open("ollama")));
  }

  @Test
  void blockedPrimaryLeavesOnlyTheFallback() {
    assertEquals(
        List.of(new Attempt("ollama", Mode.LAST_RESORT)),
        ProviderAttemptPlan.plan(List.of("claude", "ollama"), open("claude")));
  }

  @Test
  void everythingBlockedCallsThePrimaryOnceAnyway() {
    // 폴백을 끈 상태(체인 길이 1)에는 래치가 없어 매번 1순위를 부른다 — 그것과 같아야 한다.
    assertEquals(
        List.of(new Attempt("claude", Mode.LAST_RESORT)),
        ProviderAttemptPlan.plan(List.of("claude", "ollama"), open("claude", "ollama")));
  }

  @Test
  void aSingleProviderIsAlwaysTheLastResort() {
    assertEquals(
        List.of(new Attempt("claude", Mode.LAST_RESORT)),
        ProviderAttemptPlan.plan(List.of("claude"), open()));
  }

  @Test
  void onlyTheLastUsableProviderIsTheLastResort() {
    assertEquals(
        List.of(new Attempt("claude", Mode.FAST), new Attempt("third", Mode.LAST_RESORT)),
        ProviderAttemptPlan.plan(List.of("claude", "ollama", "third"), open("ollama")));
  }

  @Test
  void rejectsAnEmptyChain() {
    assertThrows(IllegalArgumentException.class,
        () -> ProviderAttemptPlan.plan(List.of(), open()));
  }

  @Test
  void consultsTheLatchOncePerProvider() {
    // Review Focus 4: 요청 도중 래치가 바뀌어도 한 요청의 계획은 한 번 읽은 상태로 일관된다.
    Map<String, Integer> reads = new HashMap<>();
    Predicate<String> counting = name -> {
      reads.merge(name, 1, Integer::sum);
      return false;
    };

    ProviderAttemptPlan.plan(List.of("claude", "ollama"), counting);

    assertEquals(Map.of("claude", 1, "ollama", 1), reads);
  }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.provider.ProviderAttemptPlanTest'`
Expected: FAIL — 컴파일 오류 `cannot find symbol: class ProviderAttemptPlan`

- [ ] **Step 3: Write minimal implementation**

```java
package ai.devpath.aigw.provider;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Predicate;

/**
 * 한 요청의 provider 시도 계획. 체인 순서와 래치 상태만으로 정한다(스펙 2026-10-03 §3.1-1).
 *
 * <ul>
 *   <li>래치가 열린 provider 는 건너뛴다.</li>
 *   <li>뒤에 래치가 닫힌 provider 가 남아 있는 시도는 {@link Mode#FAST} — 실패를 바로 넘긴다
 *       (#83 보정 ②: SDK 재시도가 429 를 삼켜 래치 판정을 왜곡하지 않게).</li>
 *   <li>뒤에 쓸 수 있는 provider 가 없는 시도는 {@link Mode#LAST_RESORT} — 폴백을 끈 상태와 같은
 *       재시도 예산을 쓴다.</li>
 *   <li>전부 막혔으면 1순위를 {@link Mode#LAST_RESORT} 로 한 번 시도한다(래치 무시). 폴백을 끈
 *       상태에는 래치가 없어 매번 1순위를 부르기 때문이다.</li>
 * </ul>
 *
 * <p>래치는 provider 마다 <b>한 번만</b> 읽는다 — 요청 도중 상태가 바뀌어도 계획이 일관된다.
 */
public final class ProviderAttemptPlan {

  public enum Mode { FAST, LAST_RESORT }

  public record Attempt(String name, Mode mode) {}

  private ProviderAttemptPlan() {}

  public static List<Attempt> plan(List<String> chain, Predicate<String> isOpen) {
    if (chain == null || chain.isEmpty()) {
      throw new IllegalArgumentException("chain must not be empty");
    }
    List<String> usable = new ArrayList<>();
    for (String name : chain) {
      if (!isOpen.test(name)) usable.add(name);
    }
    if (usable.isEmpty()) {
      return List.of(new Attempt(chain.get(0), Mode.LAST_RESORT));
    }
    List<Attempt> attempts = new ArrayList<>(usable.size());
    for (int i = 0; i < usable.size(); i++) {
      Mode mode = i < usable.size() - 1 ? Mode.FAST : Mode.LAST_RESORT;
      attempts.add(new Attempt(usable.get(i), mode));
    }
    return List.copyOf(attempts);
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: 같은 명령
Expected: PASS — `TEST-ai.devpath.aigw.provider.ProviderAttemptPlanTest.xml` 에 `tests="8" failures="0" errors="0"`

- [ ] **Step 5: Commit**

```bash
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb add src/main/java/ai/devpath/aigw/provider/ProviderAttemptPlan.java src/test/java/ai/devpath/aigw/provider/ProviderAttemptPlanTest.java
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb commit -m "feat(provider): plan each request's attempts from the latch state"
```

---

### Task 2: `ClaudeClients.lastResort` — 재시도만 SDK 기본으로 되돌린 사본

**Files:**
- Modify: `src/main/java/ai/devpath/aigw/provider/ClaudeClients.java`
- Test: `src/test/java/ai/devpath/aigw/provider/ClaudeRetryBudgetTest.java`

**Interfaces:**
- Consumes: `AnthropicClient.withOptions(Consumer<ClientOptions.Builder>)` — anthropic-java-core 2.34.0 에 존재(javap 실측)
- Produces: `static AnthropicClient ClaudeClients.lastResort(AnthropicClient fast)` — 원본은 바꾸지 않는다

- [ ] **Step 1: Write the failing test** — `ClaudeRetryBudgetTest` 클래스 끝(마지막 `}` 앞)에 추가

```java
  @Test
  void theLastResortCopyRestoresTheSdkRetryBudgetWithoutTouchingTheFastClient() {
    for (int i = 0; i < 4; i++) server.enqueue(new MockResponse().setResponseCode(500));
    AnthropicClient fast = client("claude", "ollama");

    assertThrows(RuntimeException.class, () -> ping(ClaudeClients.lastResort(fast)));
    // SDK 기본 maxRetries = 2 → 총 3회.
    assertEquals(3, server.getRequestCount());

    assertThrows(RuntimeException.class, () -> ping(fast));
    // 원본(체인용, 재시도 0)은 그대로다 — 1회만 더.
    assertEquals(4, server.getRequestCount());
  }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.provider.ClaudeRetryBudgetTest'`
Expected: FAIL — `cannot find symbol: method lastResort(AnthropicClient)`

- [ ] **Step 3: Write minimal implementation** — `ClaudeClients` 의 `maxRetriesFor` 메서드 **위**에 추가

```java
  /**
   * 「마지막 수단」 클라이언트: 같은 키·주소·타임아웃에 재시도만 SDK 기본(2)으로 되돌린 사본.
   * 뒤에 쓸 수 있는 provider 가 없을 때 래퍼가 쓴다(스펙 2026-10-03 §3.1-2) — 그때는 래치 판정을
   * 지킬 이유(넘겨받을 폴백)가 없으므로 폴백을 끈 상태와 같은 재시도를 준다. 원본은 바꾸지 않는다.
   */
  public static AnthropicClient lastResort(AnthropicClient fast) {
    return fast.withOptions(options -> options.maxRetries(SDK_DEFAULT_MAX_RETRIES));
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: 같은 명령
Expected: PASS — `ClaudeRetryBudgetTest` `tests="4" failures="0" errors="0"`(기존 3 + 신규 1)

- [ ] **Step 5: Commit**

```bash
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb add src/main/java/ai/devpath/aigw/provider/ClaudeClients.java src/test/java/ai/devpath/aigw/provider/ClaudeRetryBudgetTest.java
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb commit -m "feat(provider): derive a last-resort Claude client with the SDK retry budget"
```

---

### Task 3: Ollama 404·모델 부재를 가용성 실패로 분류

**Files:**
- Create: `src/main/java/ai/devpath/aigw/provider/OllamaModelUnavailableException.java`
- Modify: `src/main/java/ai/devpath/aigw/provider/ProviderFailures.java:43-58`(`classifyOne`)
- Test: `src/test/java/ai/devpath/aigw/provider/ProviderFailuresTest.java`

**Interfaces:**
- Produces: `class OllamaModelUnavailableException extends RuntimeException` (생성자 `(String message)`) — Task 10 이 던진다
- 동작: `RestClientResponseException` 404 → `TRANSIENT` · `OllamaModelUnavailableException` → `TRANSIENT` · SDK `NotFoundException`(Claude 404) → `OUTPUT_INVALID` **유지**

- [ ] **Step 1: Write the failing test** — `ProviderFailuresTest` 클래스 끝에 추가(필요한 import: `org.springframework.http.HttpHeaders`, `org.springframework.web.client.RestClientResponseException` 이 이미 없으면 추가)

```java
  @Test
  void treatsAnOllama404AsAnAvailabilityFailure() {
    // 스펙 2026-10-03 §3.1-7: Ollama 의 404 는 모델(또는 경로)이 없다는 뜻 — 그 Ollama 를 지금 쓸 수 없다.
    RestClientResponseException notFound = new RestClientResponseException(
        "Not Found", 404, "Not Found", new HttpHeaders(), null, null);
    assertEquals(FailureKind.TRANSIENT, ProviderFailures.classify(notFound).kind());
  }

  @Test
  void treatsAMissingOllamaModelAsAnAvailabilityFailure() {
    assertEquals(FailureKind.TRANSIENT, ProviderFailures.classify(
        new OllamaModelUnavailableException("qwen2.5:7b is not loaded")).kind());
  }

  @Test
  void findsTheOllama404BehindAFeatureException() {
    // review 는 Ollama 실패를 자기 예외로 감싼다 — 원인 체인을 따라가 404 를 찾아야 한다.
    RestClientResponseException notFound = new RestClientResponseException(
        "Not Found", 404, "Not Found", new HttpHeaders(), null, null);
    assertEquals(FailureKind.TRANSIENT, ProviderFailures.classify(
        new RuntimeException("wrapped", notFound)).kind());
  }
```

기존 `treatsAnUnmappedSdkStatusAsOutputInvalidSoItNeverOpensTheLatch`(Claude 404 → `OUTPUT_INVALID`)는 **그대로 둔다** — 바뀌면 안 되는 대조군이다.

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.provider.ProviderFailuresTest'`
Expected: FAIL — 컴파일 오류 `cannot find symbol: class OllamaModelUnavailableException`

- [ ] **Step 3: Write minimal implementation**

`OllamaModelUnavailableException.java`:

```java
package ai.devpath.aigw.provider;

/**
 * Ollama 는 응답하지만 설정한 모델이 없다(스팟 회수 뒤 PVC 유실, 다운로드 중 등). 내용 실패가 아니라
 * 그 Ollama 를 지금 쓸 수 없다는 <b>가용성 실패</b>다 — {@link ProviderFailures} 가 TRANSIENT 로 분류한다.
 */
public class OllamaModelUnavailableException extends RuntimeException {

  public OllamaModelUnavailableException(String message) {
    super(message);
  }
}
```

`ProviderFailures.classifyOne` 의 첫 분기를 바꾸고, 그 아래에 새 분기를 더한다:

```java
  private static Classified classifyOne(Throwable t) {
    if (t instanceof RestClientResponseException http) {
      int status = http.getStatusCode().value();
      // 이 체인에서 RestClient 를 쓰는 provider 는 Ollama 뿐이다(Claude 는 SDK 예외로 온다).
      // Ollama 404 = 모델(또는 경로)이 없다 = 그 Ollama 를 지금 쓸 수 없다(스펙 2026-10-03 §3.1-7).
      if (status == 404) return new Classified(FailureKind.TRANSIENT, null);
      return fromStatus(status, retryAfter(http.getResponseHeaders()));
    }
    if (t instanceof OllamaModelUnavailableException) {
      return new Classified(FailureKind.TRANSIENT, null);
    }
    if (t instanceof AnthropicServiceException sdk) {
```

(`if (t instanceof AnthropicServiceException sdk) {` 부터 아래는 그대로.)

- [ ] **Step 4: Run test to verify it passes**

Run: 같은 명령
Expected: PASS — `failures="0" errors="0"`, 기존 SDK 404 테스트 포함

- [ ] **Step 5: Commit**

```bash
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb add src/main/java/ai/devpath/aigw/provider/OllamaModelUnavailableException.java src/main/java/ai/devpath/aigw/provider/ProviderFailures.java src/test/java/ai/devpath/aigw/provider/ProviderFailuresTest.java
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb commit -m "fix(provider): classify an Ollama 404 or missing model as an availability failure"
```

---

### Task 4: `OllamaHttp` — 연결·읽기 타임아웃을 분리한 요청 팩토리

**Files:**
- Create: `src/main/java/ai/devpath/aigw/provider/OllamaHttp.java`
- Test: `src/test/java/ai/devpath/aigw/provider/OllamaHttpTest.java`

**Interfaces:**
- Produces: `static SimpleClientHttpRequestFactory OllamaHttp.requestFactory(Duration connectTimeout, Duration readTimeout)` — Task 5·10 이 쓴다

- [ ] **Step 1: Write the failing test**

```java
package ai.devpath.aigw.provider;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.test.util.ReflectionTestUtils;

class OllamaHttpTest {

  @Test
  void keepsTheConnectAndReadTimeoutsApart() {
    // Spring 7.0.8 SimpleClientHttpRequestFactory 는 두 값을 private int(ms)로 든다(javap 실측).
    SimpleClientHttpRequestFactory factory =
        OllamaHttp.requestFactory(Duration.ofSeconds(3), Duration.ofSeconds(60));

    assertEquals(3_000, ReflectionTestUtils.getField(factory, "connectTimeout"));
    assertEquals(60_000, ReflectionTestUtils.getField(factory, "readTimeout"));
  }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.provider.OllamaHttpTest'`
Expected: FAIL — `cannot find symbol: class OllamaHttp`

- [ ] **Step 3: Write minimal implementation**

```java
package ai.devpath.aigw.provider;

import java.time.Duration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;

/**
 * Ollama 호출용 요청 팩토리. 연결과 읽기 타임아웃을 <b>따로</b> 둔다(스펙 2026-10-03 §3.1-6).
 *
 * <p>둘을 같은 값(60초)으로 두면, GPU 노드가 갑자기 사라져 엔드포인트가 아직 남아 있는 동안 요청마다
 * 연결에서 60초를 기다린다. 생성은 분 단위라 읽기는 길어야 하지만 연결은 짧아도 된다.
 */
public final class OllamaHttp {

  private OllamaHttp() {}

  public static SimpleClientHttpRequestFactory requestFactory(
      Duration connectTimeout, Duration readTimeout) {
    var factory = new SimpleClientHttpRequestFactory();
    factory.setConnectTimeout(connectTimeout);
    factory.setReadTimeout(readTimeout);
    return factory;
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: 같은 명령
Expected: PASS — `tests="1" failures="0" errors="0"`

- [ ] **Step 5: Commit**

```bash
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb add src/main/java/ai/devpath/aigw/provider/OllamaHttp.java src/test/java/ai/devpath/aigw/provider/OllamaHttpTest.java
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb commit -m "feat(provider): build Ollama request factories with separate connect and read timeouts"
```

---

### Task 5: 세 기능의 Ollama 연결 타임아웃 분리(기본 3초)

**Files:**
- Modify: `src/main/java/ai/devpath/aigw/review/OllamaAiReviewClient.java:26-38`(생성자)
- Modify: `src/main/java/ai/devpath/aigw/community/OllamaSeedClient.java:22-33`(생성자)
- Modify: `src/main/java/ai/devpath/aigw/retention/OllamaReEngagementClient.java:23-31`(생성자)
- Modify: `src/main/java/ai/devpath/aigw/review/ReviewClientConfig.java` · `community/CommunitySeedClientConfig.java` · `retention/ReEngagementClientConfig.java`
- Modify: `src/main/resources/application.yml`(세 기능 절)
- Test: `src/test/java/ai/devpath/aigw/provider/OllamaConnectTimeoutWiringTest.java`

**Interfaces:**
- Consumes: `OllamaHttp.requestFactory(Duration, Duration)`(Task 4)
- Produces(새 생성자, 기존 생성자는 연결=읽기로 위임해 유지):
  - `OllamaAiReviewClient(String baseUrl, String model, Duration connectTimeout, Duration readTimeout, ReviewPromptBuilder prompts, JsonMapper jsonMapper)`
  - `OllamaSeedClient(String baseUrl, String model, Duration connectTimeout, Duration readTimeout, SeedPromptBuilder prompts, tools.jackson.databind.json.JsonMapper jsonMapper)`
  - `OllamaReEngagementClient(String baseUrl, String model, Duration connectTimeout, Duration readTimeout, ReEngagementPromptBuilder prompts)`

- [ ] **Step 1: Write the failing test**

```java
package ai.devpath.aigw.provider;

import static org.junit.jupiter.api.Assertions.assertEquals;

import ai.devpath.aigw.community.AiSeedClient;
import ai.devpath.aigw.community.CommunitySeedClientConfig;
import ai.devpath.aigw.community.SeedPromptBuilder;
import ai.devpath.aigw.retention.ReEngagementClientConfig;
import ai.devpath.aigw.retention.ReEngagementPromptBuilder;
import ai.devpath.aigw.retention.ReEngagementSuggestionClient;
import ai.devpath.aigw.review.AiReviewClient;
import ai.devpath.aigw.review.ReviewClientConfig;
import ai.devpath.aigw.review.ReviewPromptBuilder;
import java.time.Clock;
import org.junit.jupiter.api.Test;
import org.springframework.boot.convert.ApplicationConversionService;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.test.util.ReflectionTestUtils;
import tools.jackson.databind.json.JsonMapper;

/** 세 기능의 Ollama 클라이언트가 연결 타임아웃을 읽기와 따로 받는지(스펙 2026-10-03 §3.1-6). */
class OllamaConnectTimeoutWiringTest {

  private ApplicationContextRunner runner() {
    return new ApplicationContextRunner()
        .withInitializer(context -> context.getBeanFactory()
            .setConversionService(ApplicationConversionService.getSharedInstance()))
        .withBean(Clock.class, Clock::systemUTC)
        .withBean(ProviderLatch.class, () -> new ProviderLatch(Clock.systemUTC()))
        .withBean(JsonMapper.class, JsonMapper::new)
        .withBean(ReviewPromptBuilder.class, ReviewPromptBuilder::new)
        .withBean(SeedPromptBuilder.class, SeedPromptBuilder::new)
        .withBean(ReEngagementPromptBuilder.class, ReEngagementPromptBuilder::new)
        .withUserConfiguration(
            ReviewClientConfig.class, CommunitySeedClientConfig.class,
            ReEngagementClientConfig.class)
        .withPropertyValues(
            "devpath.review.provider=ollama",
            "devpath.community-seed.provider=ollama",
            "devpath.retention.provider=ollama");
  }

  /** DefaultRestClient(Spring 7.0.8)는 팩토리를 clientRequestFactory 필드에 든다(javap 실측). */
  private static int timeout(Object ollamaClient, String field) {
    Object restClient = ReflectionTestUtils.getField(ollamaClient, "restClient");
    Object factory = ReflectionTestUtils.getField(restClient, "clientRequestFactory");
    return (int) ReflectionTestUtils.getField(factory, field);
  }

  @Test
  void connectsWithinThreeSecondsByDefaultWhileReadingForSixty() {
    runner().run(context -> {
      for (Object client : new Object[] {
          context.getBean(AiReviewClient.class),
          context.getBean(AiSeedClient.class),
          context.getBean(ReEngagementSuggestionClient.class)}) {
        assertEquals(3_000, timeout(client, "connectTimeout"), client.getClass().getSimpleName());
        assertEquals(60_000, timeout(client, "readTimeout"), client.getClass().getSimpleName());
      }
    });
  }

  @Test
  void eachFeatureCanOverrideItsConnectTimeout() {
    runner()
        .withPropertyValues(
            "devpath.review.ollama-connect-timeout=PT1S",
            "devpath.community-seed.ollama-connect-timeout=PT2S",
            "devpath.retention.ollama-connect-timeout=PT4S")
        .run(context -> {
          assertEquals(1_000, timeout(context.getBean(AiReviewClient.class), "connectTimeout"));
          assertEquals(2_000, timeout(context.getBean(AiSeedClient.class), "connectTimeout"));
          assertEquals(4_000,
              timeout(context.getBean(ReEngagementSuggestionClient.class), "connectTimeout"));
        });
  }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.provider.OllamaConnectTimeoutWiringTest'`
Expected: FAIL — `expected: <3000> but was: <60000>`(지금은 연결도 60초)

- [ ] **Step 3: Write minimal implementation**

`OllamaAiReviewClient` — 생성자 하나를 아래 둘로 바꾸고, `import org.springframework.http.client.SimpleClientHttpRequestFactory;` 를 지우고 `import ai.devpath.aigw.provider.OllamaHttp;` 를 더한다:

```java
  public OllamaAiReviewClient(
      @Value("${devpath.ollama.base-url:http://localhost:11434}") String baseUrl,
      @Value("${devpath.review.ollama-model:qwen2.5-coder:7b}") String model,
      @Value("${devpath.review.ollama-timeout:PT60S}") Duration timeout,
      ReviewPromptBuilder prompts, JsonMapper jsonMapper) {
    this(baseUrl, model, timeout, timeout, prompts, jsonMapper);
  }

  /** 연결과 읽기 타임아웃을 따로 받는다(스펙 2026-10-03 §3.1-6). 운영 조립은 이 생성자를 쓴다. */
  public OllamaAiReviewClient(
      String baseUrl, String model, Duration connectTimeout, Duration readTimeout,
      ReviewPromptBuilder prompts, JsonMapper jsonMapper) {
    this.restClient = RestClient.builder().baseUrl(baseUrl)
        .requestFactory(OllamaHttp.requestFactory(connectTimeout, readTimeout)).build();
    this.model = model;
    this.prompts = prompts;
    this.jsonMapper = jsonMapper;
  }
```

`OllamaSeedClient` — 같은 방식(import 동일하게 교체):

```java
  public OllamaSeedClient(
      @Value("${devpath.ollama.base-url:http://localhost:11434}") String baseUrl,
      @Value("${devpath.community-seed.ollama-model:qwen2.5:7b}") String model,
      @Value("${devpath.community-seed.ollama-timeout:PT60S}") Duration timeout,
      SeedPromptBuilder prompts, tools.jackson.databind.json.JsonMapper jsonMapper) {
    this(baseUrl, model, timeout, timeout, prompts, jsonMapper);
  }

  /** 연결과 읽기 타임아웃을 따로 받는다(스펙 2026-10-03 §3.1-6). 운영 조립은 이 생성자를 쓴다. */
  public OllamaSeedClient(
      String baseUrl, String model, Duration connectTimeout, Duration readTimeout,
      SeedPromptBuilder prompts, tools.jackson.databind.json.JsonMapper jsonMapper) {
    this.restClient = RestClient.builder().baseUrl(baseUrl)
        .requestFactory(OllamaHttp.requestFactory(connectTimeout, readTimeout)).build();
    this.model = model;
    this.prompts = prompts;
  }
```

`OllamaReEngagementClient` — **탭 들여쓰기**(import 동일하게 교체):

```java
	public OllamaReEngagementClient(
			String baseUrl, String model, Duration timeout, ReEngagementPromptBuilder prompts) {
		this(baseUrl, model, timeout, timeout, prompts);
	}

	/** 연결과 읽기 타임아웃을 따로 받는다(스펙 2026-10-03 §3.1-6). 운영 조립은 이 생성자를 쓴다. */
	public OllamaReEngagementClient(
			String baseUrl, String model, Duration connectTimeout, Duration readTimeout,
			ReEngagementPromptBuilder prompts) {
		this.restClient = RestClient.builder().baseUrl(baseUrl)
				.requestFactory(OllamaHttp.requestFactory(connectTimeout, readTimeout)).build();
		this.model = model;
		this.prompts = prompts;
	}
```

`ReviewClientConfig.reviewClient` — `ollamaTimeout` 파라미터 바로 아래에 추가하고 생성 줄을 바꾼다:

```java
      @Value("${devpath.review.ollama-timeout:PT60S}") Duration ollamaTimeout,
      @Value("${devpath.review.ollama-connect-timeout:PT3S}") Duration ollamaConnectTimeout,
```

```java
    available.put("ollama", new OllamaAiReviewClient(
        ollamaBaseUrl, ollamaModel, ollamaConnectTimeout, ollamaTimeout, prompts, jsonMapper));
```

`CommunitySeedClientConfig.seedClient` — 같은 자리:

```java
      @Value("${devpath.community-seed.ollama-timeout:PT60S}") Duration ollamaTimeout,
      @Value("${devpath.community-seed.ollama-connect-timeout:PT3S}") Duration ollamaConnectTimeout,
```

```java
    available.put("ollama", new OllamaSeedClient(
        ollamaBaseUrl, ollamaModel, ollamaConnectTimeout, ollamaTimeout, prompts, jsonMapper));
```

`ReEngagementClientConfig.reEngagementClient` — **탭**:

```java
			@Value("${devpath.retention.ollama-timeout:PT60S}") Duration ollamaTimeout,
			@Value("${devpath.retention.ollama-connect-timeout:PT3S}") Duration ollamaConnectTimeout,
```

```java
		available.put("ollama", new OllamaReEngagementClient(
				ollamaBaseUrl, ollamaModel, ollamaConnectTimeout, ollamaTimeout, prompts));
```

`application.yml` — 세 기능 절의 `ollama-base-url:` 줄 바로 아래에 각각 추가:

```yaml
    # 연결만 짧게 끊는다 — GPU 노드가 갑자기 사라졌을 때 요청마다 60초를 기다리지 않게(스펙 2026-10-03 §3.1-6).
    ollama-connect-timeout: ${REVIEW_OLLAMA_CONNECT_TIMEOUT:PT3S}
```

(community-seed 는 `COMMUNITY_SEED_OLLAMA_CONNECT_TIMEOUT`, retention 은 `RETENTION_OLLAMA_CONNECT_TIMEOUT`.)

- [ ] **Step 4: Run test to verify it passes**

Run: 같은 명령, 그리고 기존 Ollama 클라이언트 테스트도 함께:
`D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.provider.OllamaConnectTimeoutWiringTest' --tests 'ai.devpath.aigw.review.OllamaAiReviewClientTest' --tests 'ai.devpath.aigw.community.OllamaSeedClientTest' --tests 'ai.devpath.aigw.retention.OllamaReEngagementClientTest' --tests 'ai.devpath.aigw.provider.FeatureScopedOllamaBaseUrlTest'`
Expected: PASS — 다섯 XML 모두 `failures="0" errors="0"`

- [ ] **Step 5: Commit**

```bash
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb add src/main/java/ai/devpath/aigw/review/OllamaAiReviewClient.java src/main/java/ai/devpath/aigw/community/OllamaSeedClient.java src/main/java/ai/devpath/aigw/retention/OllamaReEngagementClient.java src/main/java/ai/devpath/aigw/review/ReviewClientConfig.java src/main/java/ai/devpath/aigw/community/CommunitySeedClientConfig.java src/main/java/ai/devpath/aigw/retention/ReEngagementClientConfig.java src/main/resources/application.yml src/test/java/ai/devpath/aigw/provider/OllamaConnectTimeoutWiringTest.java
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb commit -m "feat(ollama): cap the connect timeout of the three fallback clients at three seconds"
```

---

### Task 6: review — Ollama 404 를 일시 실패로(Kafka 재시도 유지)

**Files:**
- Modify: `src/main/java/ai/devpath/aigw/review/OllamaAiReviewClient.java`(`callAndParse` 의 `RestClientResponseException` catch)
- Test: `src/test/java/ai/devpath/aigw/review/OllamaAiReviewClientTest.java`

**Interfaces:**
- 동작: Ollama HTTP 404 → `TransientReviewException("LLM_MODEL_UNAVAILABLE", "Ollama 404", e)` · 400 등 다른 4xx(429 제외) → `PermanentReviewException("PARSE_FAILED", ...)` **유지**

- [ ] **Step 1: Write the failing test** — `OllamaAiReviewClientTest` 클래스 끝에 추가

```java
  @Test
  void aMissingModelIsTransientSoKafkaRetriesTheReview() {
    // 스펙 2026-10-03 §1: 404(모델 없음)가 PARSE_FAILED 영구 실패가 되면 원래 Kafka 가 다시 시도하던 리뷰를 잃는다.
    server.enqueue(new MockResponse().setResponseCode(404)
        .setBody("{\"error\":\"model \\\"qwen2.5-coder:7b\\\" not found\"}"));
    var client = new OllamaAiReviewClient(server.url("/").toString(), "qwen2.5-coder:7b",
        Duration.ofSeconds(5), new ReviewPromptBuilder(), JsonMapper.builder().build());

    TransientReviewException ex = org.junit.jupiter.api.Assertions.assertThrows(
        TransientReviewException.class,
        () -> client.review(new ReviewInput("PYTHON", "x", "", "", 0)));
    assertThat(ex.errorCode()).isEqualTo("LLM_MODEL_UNAVAILABLE");
  }

  @Test
  void aBadRequestStaysPermanent() {
    server.enqueue(new MockResponse().setResponseCode(400));
    var client = new OllamaAiReviewClient(server.url("/").toString(), "qwen2.5-coder:7b",
        Duration.ofSeconds(5), new ReviewPromptBuilder(), JsonMapper.builder().build());

    PermanentReviewException ex = org.junit.jupiter.api.Assertions.assertThrows(
        PermanentReviewException.class,
        () -> client.review(new ReviewInput("PYTHON", "x", "", "", 0)));
    assertThat(ex.errorCode()).isEqualTo("PARSE_FAILED");
  }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.review.OllamaAiReviewClientTest'`
Expected: FAIL — `aMissingModelIsTransientSoKafkaRetriesTheReview`: `Expected TransientReviewException but PermanentReviewException was thrown`(`aBadRequestStaysPermanent` 는 이미 통과 — 대조군)

- [ ] **Step 3: Write minimal implementation** — `callAndParse` 의 catch 블록에서 `if (status >= 500) {...}` 뒤, `throw new PermanentReviewException(...)` 앞에 추가

```java
      if (status == 404) {
        // 모델(또는 경로)이 없다 = 이 Ollama 를 지금 쓸 수 없다(스펙 2026-10-03 §3.1-7).
        // 영구 실패로 끝내면 원래 Kafka 가 다시 시도하던 리뷰를 잃는다.
        throw new TransientReviewException("LLM_MODEL_UNAVAILABLE", "Ollama 404", e);
      }
```

- [ ] **Step 4: Run test to verify it passes**

Run: 같은 명령
Expected: PASS — `failures="0" errors="0"`

- [ ] **Step 5: Commit**

```bash
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb add src/main/java/ai/devpath/aigw/review/OllamaAiReviewClient.java src/test/java/ai/devpath/aigw/review/OllamaAiReviewClientTest.java
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb commit -m "fix(review): keep the Kafka retry when the Ollama model is missing"
```

---

### Task 7: review 래퍼 — 시도 계획과 「마지막 수단」 Claude

**Files:**
- Modify: `src/main/java/ai/devpath/aigw/review/FallbackAiReviewClient.java`(전체 교체)
- Modify: `src/main/java/ai/devpath/aigw/review/ReviewClientConfig.java`(반환부)
- Test: `src/test/java/ai/devpath/aigw/review/FallbackAiReviewClientTest.java`

**Interfaces:**
- Consumes: `ProviderAttemptPlan.plan`(Task 1) · `ClaudeClients.lastResort`(Task 2)
- Produces: `FallbackAiReviewClient(LinkedHashMap<String, AiReviewClient> delegates, Map<String, AiReviewClient> lastResort, ProviderLatch latch)` · 기존 2-인자 생성자는 빈 `lastResort` 로 위임해 유지

- [ ] **Step 1: Write the failing test**

`FallbackAiReviewClientTest` 에서 `throwsTheExistingReviewExceptionWhenEveryProviderIsBlocked` 메서드를 **지우고**(스펙 §3.1-1 규칙 ③이 이 동작을 의도적으로 바꾼다), `import java.util.Map;` 을 더한 뒤 아래를 추가한다:

```java
  private FallbackAiReviewClient chain(
      ProviderLatch latch, Map<String, AiReviewClient> lastResort, Stub... stubs) {
    LinkedHashMap<String, AiReviewClient> delegates = new LinkedHashMap<>();
    for (Stub s : stubs) delegates.put(s.providerName().toLowerCase(Locale.ROOT), s);
    return new FallbackAiReviewClient(delegates, lastResort, latch);
  }

  @Test
  void usesTheFastClaudeWhileAUsableFallbackFollows() {
    ProviderLatch latch = latch();
    Stub fast = new Stub("CLAUDE", status(503, "Service Unavailable"), null);
    Stub patient = new Stub("CLAUDE", null, result(9));
    Stub ollama = new Stub("OLLAMA", null, result(4));

    assertEquals(4, chain(latch, Map.of("claude", patient), fast, ollama).review(INPUT).confidence());
    assertEquals(1, fast.calls);
    assertEquals(0, patient.calls);
  }

  @Test
  void usesTheLastResortClaudeWhenTheFallbackIsBlocked() {
    ProviderLatch latch = latch();
    latch.recordFailure("review", "ollama", FailureKind.AUTH, null);
    Stub fast = new Stub("CLAUDE", null, result(1));
    Stub patient = new Stub("CLAUDE", null, result(5));
    Stub ollama = new Stub("OLLAMA", null, result(2));

    assertEquals(5, chain(latch, Map.of("claude", patient), fast, ollama).review(INPUT).confidence());
    assertEquals(0, fast.calls);
    assertEquals(1, patient.calls);
    assertEquals(0, ollama.calls);
  }

  @Test
  void callsThePrimaryLastResortOnceWhenEveryProviderIsBlocked() {
    // 스펙 §3.1-1 규칙 ③: 폴백을 끈 상태처럼 1순위를 부른다(예전에는 LLM_ALL_PROVIDERS_BLOCKED 로 실패).
    ProviderLatch latch = latch();
    latch.recordFailure("review", "claude", FailureKind.RATE_LIMIT, null);
    latch.recordFailure("review", "ollama", FailureKind.AUTH, null);
    Stub fast = new Stub("CLAUDE", null, result(1));
    Stub patient = new Stub("CLAUDE", null, result(8));
    Stub ollama = new Stub("OLLAMA", null, result(2));

    assertEquals(8, chain(latch, Map.of("claude", patient), fast, ollama).review(INPUT).confidence());
    assertEquals(1, patient.calls);
    assertEquals(0, fast.calls);
    assertEquals(0, ollama.calls);
  }

  @Test
  void surfacesTheLastResortFailureWhenEveryProviderIsBlocked() {
    ProviderLatch latch = latch();
    latch.recordFailure("review", "claude", FailureKind.RATE_LIMIT, null);
    latch.recordFailure("review", "ollama", FailureKind.AUTH, null);
    TransientReviewException failure = new TransientReviewException("LLM_RATELIMIT", "Claude 429", null);
    Stub patient = new Stub("CLAUDE", failure, null);

    RuntimeException thrown = assertThrows(RuntimeException.class,
        () -> chain(latch, Map.of("claude", patient),
            new Stub("CLAUDE", null, result(1)), new Stub("OLLAMA", null, result(2))).review(INPUT));
    assertSame(failure, thrown);
  }

  @Test
  void fallsBackToTheFastDelegateWhenNoLastResortVariantIsGiven() {
    ProviderLatch latch = latch();
    latch.recordFailure("review", "ollama", FailureKind.AUTH, null);
    Stub claude = new Stub("CLAUDE", null, result(6));

    assertEquals(6, chain(latch, claude, new Stub("OLLAMA", null, result(2))).review(INPUT).confidence());
    assertEquals(1, claude.calls);
  }

  @Test
  void reportsClaudeWhenTheLastResortVariantServed() {
    // Review Focus 5: 저장·발행되는 이름은 구현체가 말하는 이름이다.
    ProviderLatch latch = latch();
    latch.recordFailure("review", "ollama", FailureKind.AUTH, null);
    FallbackAiReviewClient client = chain(latch,
        Map.of("claude", new Stub("CLAUDE", null, result(5))),
        new Stub("CLAUDE", null, result(1)), new Stub("OLLAMA", null, result(2)));

    client.review(INPUT);

    assertEquals("CLAUDE", client.providerName());
  }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.review.FallbackAiReviewClientTest'`
Expected: FAIL — 컴파일 오류 `no suitable constructor found for FallbackAiReviewClient(LinkedHashMap,Map,ProviderLatch)`

- [ ] **Step 3: Write minimal implementation**

`FallbackAiReviewClient.java` 전체:

```java
package ai.devpath.aigw.review;

import ai.devpath.aigw.provider.ProviderAttemptPlan;
import ai.devpath.aigw.provider.ProviderFailures;
import ai.devpath.aigw.provider.ProviderFeatures;
import ai.devpath.aigw.provider.ProviderLatch;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 순서형 폴백 코드리뷰 클라이언트. 래치가 열린 provider 는 <b>호출하지 않고</b> 건너뛴다.
 *
 * <p>리뷰는 요청/응답이라 멘토의 「토큰 방출 뒤 전환 불가」 제약이 없다 — 실패하면 항상 다음으로 간다.
 *
 * <p>시도 순서와 각 시도의 재시도 예산은 {@link ProviderAttemptPlan} 이 정한다(스펙 2026-10-03 §3.1):
 * 뒤에 쓸 수 있는 provider 가 남아 있으면 빠른 구현체(재시도 0)로 실패를 바로 넘기고, 남아 있지 않으면
 * {@code lastResort} 구현체(SDK 기본 재시도)를 쓴다. 전부 막혔으면 1순위를 래치와 무관하게 한 번 부른다 —
 * 폴백을 끈 상태(체인 길이 1)가 매번 Claude 를 부르는 것과 같아진다.
 */
public class FallbackAiReviewClient implements AiReviewClient {

  private static final String FEATURE = ProviderFeatures.REVIEW;

  private final LinkedHashMap<String, AiReviewClient> delegates;
  private final Map<String, AiReviewClient> lastResort;
  private final ProviderLatch latch;
  private final ThreadLocal<String> served = new ThreadLocal<>();

  public FallbackAiReviewClient(
      LinkedHashMap<String, AiReviewClient> delegates, ProviderLatch latch) {
    this(delegates, Map.of(), latch);
  }

  public FallbackAiReviewClient(
      LinkedHashMap<String, AiReviewClient> delegates,
      Map<String, AiReviewClient> lastResort,
      ProviderLatch latch) {
    if (delegates == null || delegates.isEmpty()) {
      throw new IllegalArgumentException("delegates must not be empty");
    }
    this.delegates = new LinkedHashMap<>(delegates);
    this.lastResort = Map.copyOf(lastResort);
    this.latch = latch;
  }

  @Override
  public ReviewResult review(ReviewInput input) {
    // 들어올 때 비운다 — 풀 워커 스레드에 직전 요청의 값이 남아 있으면 이번 요청의
    // 기록이 그 값을 제 것으로 발행한다(FallbackMentorClient 와 같은 수명 관리).
    served.remove();
    List<ProviderAttemptPlan.Attempt> plan = ProviderAttemptPlan.plan(
        List.copyOf(delegates.keySet()), name -> latch.isOpen(FEATURE, name));
    RuntimeException last = null;
    for (ProviderAttemptPlan.Attempt attempt : plan) {
      String name = attempt.name();
      AiReviewClient delegate = attempt.mode() == ProviderAttemptPlan.Mode.LAST_RESORT
          ? lastResort.getOrDefault(name, delegates.get(name))
          : delegates.get(name);
      // 체인 키(소문자)가 아니라 구현체가 스스로 말하는 이름(대문자)을 기록한다 —
      // 이 값이 그대로 저장·발행되고, 그 자리엔 이미 대문자가 들어 있다.
      // 호출 **전에** 기록하므로 전부 실패해도 마지막으로 시도한 provider 가 남는다.
      served.set(delegate.providerName());
      try {
        ReviewResult result = delegate.review(input);
        latch.recordSuccess(FEATURE, name);
        return result;
      } catch (RuntimeException ex) {
        ProviderFailures.Classified c = ProviderFailures.classify(ex);
        latch.recordFailure(FEATURE, name, c.kind(), c.retryAfter());
        last = ex;
      }
    }
    // 계획은 비지 않는다(전부 막혔어도 1순위 1회) — 여기 왔다면 모든 시도가 실패했다.
    throw last;
  }

  @Override
  public String providerName() {
    String s = served.get();
    // 한 번 읽으면 비운다 — 호출 측이 읽지 않고 끝난 요청의 값이 스레드에 남아
    // 다음 요청의 기록을 오염시키는 것을 막는다(FallbackMentorClient 와 같은 규약).
    served.remove();
    return s != null ? s : delegates.values().iterator().next().providerName();
  }
}
```

`ReviewClientConfig.reviewClient` 의 끝(`return chain.size() == 1 ...` 부분)을 아래로 바꾸고, `import ai.devpath.aigw.provider.ClaudeClients;` 와 `import java.util.Map;` 을 더한다:

```java
    if (chain.size() == 1) {
      return chain.values().iterator().next();
    }
    // 체인이 있을 때만 「마지막 수단」 Claude 를 만든다 — 같은 클라이언트에서 재시도만 SDK 기본으로
    // 되돌린 사본이다(빈이 아니다). 뒤에 쓸 수 있는 폴백이 없을 때 래퍼가 쓴다(스펙 2026-10-03 §3.1-2).
    Map<String, AiReviewClient> lastResort = new LinkedHashMap<>();
    if (anthropic != null && chain.containsKey("claude")) {
      lastResort.put("claude",
          new ClaudeAiReviewClient(ClaudeClients.lastResort(anthropic), claudeModel, prompts));
    }
    return new FallbackAiReviewClient(chain, lastResort, latch);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.review.FallbackAiReviewClientTest' --tests 'ai.devpath.aigw.review.ReviewServiceProviderRecordingTest'`
Expected: PASS — 두 XML `failures="0" errors="0"`

- [ ] **Step 5: Commit**

```bash
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb add src/main/java/ai/devpath/aigw/review/FallbackAiReviewClient.java src/main/java/ai/devpath/aigw/review/ReviewClientConfig.java src/test/java/ai/devpath/aigw/review/FallbackAiReviewClientTest.java
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb commit -m "feat(review): give Claude its retry budget when no fallback can take over"
```

---

### Task 8: community-seed 래퍼 — 시도 계획과 「마지막 수단」 Claude

**Files:**
- Modify: `src/main/java/ai/devpath/aigw/community/FallbackAiSeedClient.java`(전체 교체)
- Modify: `src/main/java/ai/devpath/aigw/community/CommunitySeedClientConfig.java`(반환부)
- Test: `src/test/java/ai/devpath/aigw/community/FallbackAiSeedClientTest.java`

**Interfaces:**
- Consumes: `ProviderAttemptPlan.plan`(Task 1) · `ClaudeClients.lastResort`(Task 2)
- Produces: `FallbackAiSeedClient(LinkedHashMap<String, AiSeedClient> delegates, Map<String, AiSeedClient> lastResort, ProviderLatch latch)` · 기존 2-인자 생성자 유지

- [ ] **Step 1: Write the failing test**

`FallbackAiSeedClientTest` 에서 `throwsTheExistingSeedExceptionWhenEveryProviderIsBlocked` 를 **지우고**, `import java.util.Map;` 과 `import static org.junit.jupiter.api.Assertions.assertSame;` 을 더한 뒤 추가:

```java
  private FallbackAiSeedClient chain(
      ProviderLatch latch, Map<String, AiSeedClient> lastResort, Stub... stubs) {
    LinkedHashMap<String, AiSeedClient> delegates = new LinkedHashMap<>();
    for (Stub s : stubs) delegates.put(s.providerName().toLowerCase(Locale.ROOT), s);
    return new FallbackAiSeedClient(delegates, lastResort, latch);
  }

  @Test
  void usesTheFastClaudeWhileAUsableFallbackFollows() {
    ProviderLatch latch = latch();
    Stub fast = new Stub("CLAUDE", status(503, "Service Unavailable"), null);
    Stub patient = new Stub("CLAUDE", null, "patient");
    Stub ollama = new Stub("OLLAMA", null, "ollama");

    assertEquals("ollama",
        chain(latch, Map.of("claude", patient), fast, ollama).generate(INPUT).content());
    assertEquals(1, fast.calls);
    assertEquals(0, patient.calls);
  }

  @Test
  void usesTheLastResortClaudeWhenTheFallbackIsBlocked() {
    ProviderLatch latch = latch();
    latch.recordFailure("community-seed", "ollama", FailureKind.AUTH, null);
    Stub fast = new Stub("CLAUDE", null, "fast");
    Stub patient = new Stub("CLAUDE", null, "patient");

    assertEquals("patient", chain(latch, Map.of("claude", patient), fast,
        new Stub("OLLAMA", null, "ollama")).generate(INPUT).content());
    assertEquals(0, fast.calls);
    assertEquals(1, patient.calls);
  }

  @Test
  void callsThePrimaryLastResortOnceWhenEveryProviderIsBlocked() {
    // 스펙 §3.1-1 규칙 ③(예전에는 LLM_ALL_PROVIDERS_BLOCKED 로 실패).
    ProviderLatch latch = latch();
    latch.recordFailure("community-seed", "claude", FailureKind.RATE_LIMIT, null);
    latch.recordFailure("community-seed", "ollama", FailureKind.AUTH, null);
    Stub patient = new Stub("CLAUDE", null, "patient");

    assertEquals("patient", chain(latch, Map.of("claude", patient),
        new Stub("CLAUDE", null, "fast"), new Stub("OLLAMA", null, "ollama"))
        .generate(INPUT).content());
    assertEquals(1, patient.calls);
  }

  @Test
  void surfacesTheLastResortFailureWhenEveryProviderIsBlocked() {
    ProviderLatch latch = latch();
    latch.recordFailure("community-seed", "claude", FailureKind.RATE_LIMIT, null);
    latch.recordFailure("community-seed", "ollama", FailureKind.AUTH, null);
    SeedGenerationException failure =
        new SeedGenerationException("LLM_FAILED", "Claude seed 호출 실패", null);

    RuntimeException thrown = assertThrows(RuntimeException.class,
        () -> chain(latch, Map.of("claude", new Stub("CLAUDE", failure, null)),
            new Stub("CLAUDE", null, "fast"), new Stub("OLLAMA", null, "ollama")).generate(INPUT));
    assertSame(failure, thrown);
  }

  @Test
  void reportsClaudeWhenTheLastResortVariantServed() {
    ProviderLatch latch = latch();
    latch.recordFailure("community-seed", "ollama", FailureKind.AUTH, null);
    FallbackAiSeedClient client = chain(latch,
        Map.of("claude", new Stub("CLAUDE", null, "patient")),
        new Stub("CLAUDE", null, "fast"), new Stub("OLLAMA", null, "ollama"));

    client.generate(INPUT);

    assertEquals("CLAUDE", client.providerName());
  }
```

(`SeedAnswer` 는 `record SeedAnswer(String content)` 다 — 접근자 `content()`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.community.FallbackAiSeedClientTest'`
Expected: FAIL — `no suitable constructor found for FallbackAiSeedClient(LinkedHashMap,Map,ProviderLatch)`

- [ ] **Step 3: Write minimal implementation**

`FallbackAiSeedClient.java` 전체:

```java
package ai.devpath.aigw.community;

import ai.devpath.aigw.provider.ProviderAttemptPlan;
import ai.devpath.aigw.provider.ProviderFailures;
import ai.devpath.aigw.provider.ProviderFeatures;
import ai.devpath.aigw.provider.ProviderLatch;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 순서형 폴백 커뮤니티 시드 클라이언트. 래치가 열린 provider 는 호출하지 않고 건너뛴다.
 *
 * <p>시드 답변은 저장되고 공개되므로 어느 provider 가 만들었는지 {@link #providerName()} 으로
 * 기록된다. mock 으로는 떨어지지 않는다(스펙 §4.1).
 *
 * <p>시도 순서와 재시도 예산은 {@link ProviderAttemptPlan} 이 정한다(스펙 2026-10-03 §3.1) — 시드는
 * Kafka 재시도가 없어 한 번의 503 이 그 질문의 답변을 영구히 잃으므로, 넘겨받을 폴백이 없을 때 Claude 에
 * SDK 기본 재시도를 주는 것이 특히 중요하다.
 */
public class FallbackAiSeedClient implements AiSeedClient {

  private static final String FEATURE = ProviderFeatures.COMMUNITY_SEED;

  private final LinkedHashMap<String, AiSeedClient> delegates;
  private final Map<String, AiSeedClient> lastResort;
  private final ProviderLatch latch;
  private final ThreadLocal<String> served = new ThreadLocal<>();

  public FallbackAiSeedClient(
      LinkedHashMap<String, AiSeedClient> delegates, ProviderLatch latch) {
    this(delegates, Map.of(), latch);
  }

  public FallbackAiSeedClient(
      LinkedHashMap<String, AiSeedClient> delegates,
      Map<String, AiSeedClient> lastResort,
      ProviderLatch latch) {
    if (delegates == null || delegates.isEmpty()) {
      throw new IllegalArgumentException("delegates must not be empty");
    }
    this.delegates = new LinkedHashMap<>(delegates);
    this.lastResort = Map.copyOf(lastResort);
    this.latch = latch;
  }

  @Override
  public SeedAnswer generate(SeedInput input) {
    // 들어올 때 비운다 — 풀 워커 스레드에 직전 요청의 값이 남아 있으면 이번 요청의
    // 기록이 그 값을 제 것으로 발행한다(FallbackMentorClient 와 같은 수명 관리).
    served.remove();
    List<ProviderAttemptPlan.Attempt> plan = ProviderAttemptPlan.plan(
        List.copyOf(delegates.keySet()), name -> latch.isOpen(FEATURE, name));
    RuntimeException last = null;
    for (ProviderAttemptPlan.Attempt attempt : plan) {
      String name = attempt.name();
      AiSeedClient delegate = attempt.mode() == ProviderAttemptPlan.Mode.LAST_RESORT
          ? lastResort.getOrDefault(name, delegates.get(name))
          : delegates.get(name);
      // 체인 키(소문자)가 아니라 구현체가 스스로 말하는 이름(대문자)을 기록한다 —
      // 이 값이 그대로 저장·발행되고, 그 자리엔 이미 대문자가 들어 있다.
      // 호출 **전에** 기록하므로 전부 실패해도 마지막으로 시도한 provider 가 남는다.
      served.set(delegate.providerName());
      try {
        SeedAnswer answer = delegate.generate(input);
        latch.recordSuccess(FEATURE, name);
        return answer;
      } catch (RuntimeException ex) {
        ProviderFailures.Classified c = ProviderFailures.classify(ex);
        latch.recordFailure(FEATURE, name, c.kind(), c.retryAfter());
        last = ex;
      }
    }
    // 계획은 비지 않는다(전부 막혔어도 1순위 1회) — 여기 왔다면 모든 시도가 실패했다.
    throw last;
  }

  @Override
  public String providerName() {
    String s = served.get();
    // 한 번 읽으면 비운다 — 호출 측이 읽지 않고 끝난 요청의 값이 스레드에 남아
    // 다음 요청의 기록을 오염시키는 것을 막는다(FallbackMentorClient 와 같은 규약).
    served.remove();
    return s != null ? s : delegates.values().iterator().next().providerName();
  }
}
```

`CommunitySeedClientConfig.seedClient` 의 끝을 바꾸고 `import ai.devpath.aigw.provider.ClaudeClients;`·`import java.util.Map;` 을 더한다:

```java
    if (chain.size() == 1) {
      return chain.values().iterator().next();
    }
    // 체인이 있을 때만 「마지막 수단」 Claude 를 만든다(빈이 아니다, 스펙 2026-10-03 §3.1-2).
    Map<String, AiSeedClient> lastResort = new LinkedHashMap<>();
    if (anthropic != null && chain.containsKey("claude")) {
      lastResort.put("claude",
          new ClaudeSeedClient(ClaudeClients.lastResort(anthropic), claudeModel, prompts));
    }
    return new FallbackAiSeedClient(chain, lastResort, latch);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.community.FallbackAiSeedClientTest' --tests 'ai.devpath.aigw.community.CommunitySeedServiceProviderRecordingTest'`
Expected: PASS — 두 XML `failures="0" errors="0"`

- [ ] **Step 5: Commit**

```bash
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb add src/main/java/ai/devpath/aigw/community/FallbackAiSeedClient.java src/main/java/ai/devpath/aigw/community/CommunitySeedClientConfig.java src/test/java/ai/devpath/aigw/community/FallbackAiSeedClientTest.java
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb commit -m "feat(community): give Claude its retry budget when no fallback can take over"
```

---

### Task 9: retention 래퍼 — 시도 계획과 「마지막 수단」 Claude (탭 들여쓰기)

**Files:**
- Modify: `src/main/java/ai/devpath/aigw/retention/FallbackReEngagementClient.java`(전체 교체)
- Modify: `src/main/java/ai/devpath/aigw/retention/ReEngagementClientConfig.java`(반환부)
- Test: `src/test/java/ai/devpath/aigw/retention/FallbackReEngagementClientTest.java`

**Interfaces:**
- Consumes: `ProviderAttemptPlan.plan`(Task 1) · `ClaudeClients.lastResort`(Task 2)
- Produces: `FallbackReEngagementClient(LinkedHashMap<String, ReEngagementSuggestionClient> delegates, Map<String, ReEngagementSuggestionClient> lastResort, ProviderLatch latch)` · 기존 2-인자 생성자 유지

- [ ] **Step 1: Write the failing test**

`FallbackReEngagementClientTest` 에서 `throwsTheExistingRetentionExceptionWhenEveryProviderIsBlocked` 를 **지우고**, `import java.util.Map;` 과 `import static org.junit.jupiter.api.Assertions.assertSame;` 을 더한 뒤 추가(**탭**):

```java
	private FallbackReEngagementClient chain(
			ProviderLatch latch, Map<String, ReEngagementSuggestionClient> lastResort, Stub... stubs) {
		LinkedHashMap<String, ReEngagementSuggestionClient> delegates = new LinkedHashMap<>();
		for (Stub s : stubs) delegates.put(s.providerName().toLowerCase(Locale.ROOT), s);
		return new FallbackReEngagementClient(delegates, lastResort, latch);
	}

	@Test
	void usesTheFastClaudeWhileAUsableFallbackFollows() {
		ProviderLatch latch = latch();
		Stub fast = new Stub("CLAUDE", status(503, "Service Unavailable"), null);
		Stub patient = new Stub("CLAUDE", null, "patient");

		assertEquals("ollama", chain(latch, Map.of("claude", patient), fast,
				new Stub("OLLAMA", null, "ollama")).suggest(INPUT));
		assertEquals(1, fast.calls);
		assertEquals(0, patient.calls);
	}

	@Test
	void usesTheLastResortClaudeWhenTheFallbackIsBlocked() {
		ProviderLatch latch = latch();
		latch.recordFailure("retention", "ollama", FailureKind.AUTH, null);
		Stub fast = new Stub("CLAUDE", null, "fast");
		Stub patient = new Stub("CLAUDE", null, "patient");

		assertEquals("patient", chain(latch, Map.of("claude", patient), fast,
				new Stub("OLLAMA", null, "ollama")).suggest(INPUT));
		assertEquals(0, fast.calls);
		assertEquals(1, patient.calls);
	}

	@Test
	void callsThePrimaryLastResortOnceWhenEveryProviderIsBlocked() {
		// 스펙 §3.1-1 규칙 ③(예전에는 ReEngagementGenerationException 으로 실패).
		ProviderLatch latch = latch();
		latch.recordFailure("retention", "claude", FailureKind.RATE_LIMIT, null);
		latch.recordFailure("retention", "ollama", FailureKind.AUTH, null);
		Stub patient = new Stub("CLAUDE", null, "patient");

		assertEquals("patient", chain(latch, Map.of("claude", patient),
				new Stub("CLAUDE", null, "fast"), new Stub("OLLAMA", null, "ollama")).suggest(INPUT));
		assertEquals(1, patient.calls);
	}

	@Test
	void surfacesTheLastResortFailureWhenEveryProviderIsBlocked() {
		ProviderLatch latch = latch();
		latch.recordFailure("retention", "claude", FailureKind.RATE_LIMIT, null);
		latch.recordFailure("retention", "ollama", FailureKind.AUTH, null);
		ReEngagementGenerationException failure =
				new ReEngagementGenerationException("Claude 재참여 문구 생성 실패", null);

		RuntimeException thrown = assertThrows(RuntimeException.class,
				() -> chain(latch, Map.of("claude", new Stub("CLAUDE", failure, null)),
						new Stub("CLAUDE", null, "fast"), new Stub("OLLAMA", null, "ollama")).suggest(INPUT));
		assertSame(failure, thrown);
	}

	@Test
	void reportsClaudeWhenTheLastResortVariantServed() {
		ProviderLatch latch = latch();
		latch.recordFailure("retention", "ollama", FailureKind.AUTH, null);
		FallbackReEngagementClient client = chain(latch,
				Map.of("claude", new Stub("CLAUDE", null, "patient")),
				new Stub("CLAUDE", null, "fast"), new Stub("OLLAMA", null, "ollama"));

		client.suggest(INPUT);

		assertEquals("CLAUDE", client.providerName());
	}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.retention.FallbackReEngagementClientTest'`
Expected: FAIL — `no suitable constructor found for FallbackReEngagementClient(LinkedHashMap,Map,ProviderLatch)`

- [ ] **Step 3: Write minimal implementation**

`FallbackReEngagementClient.java` 전체(**탭**):

```java
package ai.devpath.aigw.retention;

import ai.devpath.aigw.provider.ProviderAttemptPlan;
import ai.devpath.aigw.provider.ProviderFailures;
import ai.devpath.aigw.provider.ProviderFeatures;
import ai.devpath.aigw.provider.ProviderLatch;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 순서형 폴백 재참여 문구 클라이언트. 래치가 열린 provider 는 호출하지 않고 건너뛴다.
 *
 * <p>문구는 일회성이라 즉시 이어받는다. mock 으로는 떨어지지 않는다(스펙 §4.1 — 가짜 문구가 알림으로
 * 발송되는 것은 실패보다 나쁘다).
 *
 * <p>시도 순서와 재시도 예산은 {@link ProviderAttemptPlan} 이 정한다(스펙 2026-10-03 §3.1) — retention 은
 * 동기 HTTP 라 재시도가 아예 없으므로, 넘겨받을 폴백이 없을 때 Claude 에 SDK 기본 재시도를 준다.
 */
public class FallbackReEngagementClient implements ReEngagementSuggestionClient {

	private static final String FEATURE = ProviderFeatures.RETENTION;

	private final LinkedHashMap<String, ReEngagementSuggestionClient> delegates;
	private final Map<String, ReEngagementSuggestionClient> lastResort;
	private final ProviderLatch latch;
	private final ThreadLocal<String> served = new ThreadLocal<>();

	public FallbackReEngagementClient(
			LinkedHashMap<String, ReEngagementSuggestionClient> delegates, ProviderLatch latch) {
		this(delegates, Map.of(), latch);
	}

	public FallbackReEngagementClient(
			LinkedHashMap<String, ReEngagementSuggestionClient> delegates,
			Map<String, ReEngagementSuggestionClient> lastResort,
			ProviderLatch latch) {
		if (delegates == null || delegates.isEmpty()) {
			throw new IllegalArgumentException("delegates must not be empty");
		}
		this.delegates = new LinkedHashMap<>(delegates);
		this.lastResort = Map.copyOf(lastResort);
		this.latch = latch;
	}

	@Override
	public String suggest(ReEngagementInput input) {
		// 들어올 때 비운다 — 풀 워커 스레드에 직전 요청의 값이 남아 있으면 이번 요청의
		// 기록이 그 값을 제 것으로 발행한다(FallbackMentorClient 와 같은 수명 관리).
		served.remove();
		List<ProviderAttemptPlan.Attempt> plan = ProviderAttemptPlan.plan(
				List.copyOf(delegates.keySet()), name -> latch.isOpen(FEATURE, name));
		RuntimeException last = null;
		for (ProviderAttemptPlan.Attempt attempt : plan) {
			String name = attempt.name();
			ReEngagementSuggestionClient delegate = attempt.mode() == ProviderAttemptPlan.Mode.LAST_RESORT
					? lastResort.getOrDefault(name, delegates.get(name))
					: delegates.get(name);
			// 체인 키(소문자)가 아니라 구현체가 스스로 말하는 이름(대문자)을 기록한다 —
			// 이 값이 그대로 저장·발행되고, 그 자리엔 이미 대문자가 들어 있다.
			// 호출 **전에** 기록하므로 전부 실패해도 마지막으로 시도한 provider 가 남는다.
			served.set(delegate.providerName());
			try {
				String text = delegate.suggest(input);
				latch.recordSuccess(FEATURE, name);
				return text;
			} catch (RuntimeException ex) {
				ProviderFailures.Classified c = ProviderFailures.classify(ex);
				latch.recordFailure(FEATURE, name, c.kind(), c.retryAfter());
				last = ex;
			}
		}
		// 계획은 비지 않는다(전부 막혔어도 1순위 1회) — 여기 왔다면 모든 시도가 실패했다.
		throw last;
	}

	@Override
	public String providerName() {
		String s = served.get();
		// 한 번 읽으면 비운다 — 호출 측이 읽지 않고 끝난 요청의 값이 스레드에 남아
		// 다음 요청의 기록을 오염시키는 것을 막는다(FallbackMentorClient 와 같은 규약).
		served.remove();
		return s != null ? s : delegates.values().iterator().next().providerName();
	}
}
```

`ReEngagementClientConfig.reEngagementClient` 의 끝을 바꾸고(**탭**) `import ai.devpath.aigw.provider.ClaudeClients;`·`import java.util.Map;` 을 더한다:

```java
		if (chain.size() == 1) {
			return chain.values().iterator().next();
		}
		// 체인이 있을 때만 「마지막 수단」 Claude 를 만든다(빈이 아니다, 스펙 2026-10-03 §3.1-2).
		Map<String, ReEngagementSuggestionClient> lastResort = new LinkedHashMap<>();
		if (anthropic != null && chain.containsKey("claude")) {
			lastResort.put("claude",
					new ClaudeReEngagementClient(ClaudeClients.lastResort(anthropic), claudeModel, prompts));
		}
		return new FallbackReEngagementClient(chain, lastResort, latch);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.retention.FallbackReEngagementClientTest' --tests 'ai.devpath.aigw.retention.ReEngagementProviderRecordingTest'`
Expected: PASS — 두 XML `failures="0" errors="0"`

- [ ] **Step 5: Commit**

```bash
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb add src/main/java/ai/devpath/aigw/retention/FallbackReEngagementClient.java src/main/java/ai/devpath/aigw/retention/ReEngagementClientConfig.java src/test/java/ai/devpath/aigw/retention/FallbackReEngagementClientTest.java
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb commit -m "feat(retention): give Claude its retry budget when no fallback can take over"
```

---

### Task 10: `OllamaProviderProbe` — 생존 탐색기

**Files:**
- Modify: `src/main/java/ai/devpath/aigw/provider/ProviderProbe.java`(기본 메서드 추가)
- Create: `src/main/java/ai/devpath/aigw/provider/OllamaProviderProbe.java`
- Test: `src/test/java/ai/devpath/aigw/provider/OllamaProviderProbeTest.java`

**Interfaces:**
- Consumes: `OllamaHttp.requestFactory`(Task 4) · `OllamaModelUnavailableException`(Task 3)
- Produces:
  - `ProviderProbe.livenessTarget()` = `default boolean` → `false`
  - `OllamaProviderProbe(String feature, String baseUrl, String model)`(연결 3초·읽기 5초) · 패키지 전용 `OllamaProviderProbe(String feature, String baseUrl, String model, Duration connectTimeout, Duration readTimeout)` · `provider()` = `"ollama"` · `livenessTarget()` = `true`

- [ ] **Step 1: Write the failing test**

```java
package ai.devpath.aigw.provider;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Duration;
import java.util.concurrent.TimeUnit;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import okhttp3.mockwebserver.RecordedRequest;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class OllamaProviderProbeTest {

  private MockWebServer server;

  @BeforeEach
  void start() throws Exception {
    server = new MockWebServer();
    server.start();
  }

  @AfterEach
  void stop() throws Exception {
    server.shutdown();
  }

  private static MockResponse tags(String... names) {
    StringBuilder models = new StringBuilder();
    for (String n : names) {
      if (models.length() > 0) models.append(',');
      models.append("{\"name\":\"").append(n).append("\",\"model\":\"").append(n)
          .append("\",\"size\":4683087332}");
    }
    return new MockResponse().setHeader("Content-Type", "application/json")
        .setBody("{\"models\":[" + models + "]}");
  }

  private OllamaProviderProbe probe(String model) {
    return new OllamaProviderProbe("review", server.url("/").toString(), model);
  }

  @Test
  void isALivenessTargetForOllama() {
    OllamaProviderProbe p = probe("qwen2.5:7b");
    assertEquals("review", p.feature());
    assertEquals("ollama", p.provider());
    assertTrue(p.livenessTarget());
  }

  @Test
  void passesWhenTheConfiguredModelIsLoaded() throws Exception {
    server.enqueue(tags("qwen2.5:3b", "qwen2.5:7b"));

    assertDoesNotThrow(() -> probe("qwen2.5:7b").ping());
    RecordedRequest request = server.takeRequest(1, TimeUnit.SECONDS);
    assertEquals("GET", request.getMethod());
    assertEquals("/api/tags", request.getPath());
  }

  @Test
  void failsAsAnAvailabilityFailureWhenTheModelIsMissing() {
    server.enqueue(tags("qwen2.5:3b"));

    RuntimeException e = assertThrows(RuntimeException.class, () -> probe("qwen2.5:7b").ping());
    assertEquals(FailureKind.TRANSIENT, ProviderFailures.classify(e).kind());
  }

  @Test
  void aSimilarTagDoesNotCountAsTheConfiguredModel() {
    // Review Focus 2: 정확히 같은 이름만 「있음」이다.
    server.enqueue(tags("qwen2.5:7b-instruct", "qwen2.5-coder:7b"));

    assertThrows(OllamaModelUnavailableException.class, () -> probe("qwen2.5:7b").ping());
  }

  @Test
  void aServerErrorIsTransient() {
    server.enqueue(new MockResponse().setResponseCode(503));

    RuntimeException e = assertThrows(RuntimeException.class, () -> probe("qwen2.5:7b").ping());
    assertEquals(FailureKind.TRANSIENT, ProviderFailures.classify(e).kind());
  }

  @Test
  void aRefusedConnectionIsTransient() throws Exception {
    // 공용 server 는 @AfterEach 가 닫으므로 따로 띄워 닫은 포트를 쓴다(연결 거부 = 회수된 GPU 노드).
    MockWebServer gone = new MockWebServer();
    gone.start();
    String dead = gone.url("/").toString();
    gone.shutdown();

    RuntimeException e = assertThrows(RuntimeException.class,
        () -> new OllamaProviderProbe("review", dead, "qwen2.5:7b").ping());
    assertEquals(FailureKind.TRANSIENT, ProviderFailures.classify(e).kind());
  }

  @Test
  void aSlowTagsResponseFailsWithinTheReadTimeout() {
    // Review Focus 3: 느린 Ollama 가 탐색 스케줄러를 붙들지 않는다.
    server.enqueue(tags("qwen2.5:7b").setBodyDelay(3, TimeUnit.SECONDS));
    OllamaProviderProbe p = new OllamaProviderProbe(
        "review", server.url("/").toString(), "qwen2.5:7b",
        Duration.ofSeconds(1), Duration.ofMillis(500));

    long started = System.nanoTime();
    RuntimeException e = assertThrows(RuntimeException.class, p::ping);
    long elapsedMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - started);

    assertEquals(FailureKind.TRANSIENT, ProviderFailures.classify(e).kind());
    assertTrue(elapsedMs < 2_500, "probe took " + elapsedMs + " ms");
  }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.provider.OllamaProviderProbeTest'`
Expected: FAIL — `cannot find symbol: class OllamaProviderProbe`

- [ ] **Step 3: Write minimal implementation**

`ProviderProbe` 인터페이스 끝(`void ping();` 아래)에 추가:

```java
  /**
   * 래치가 <b>닫혀 있어도</b> 주기적으로 핑할 대상인가(스펙 2026-10-03 §3.1-5). 폴백 자리의 Ollama 처럼
   * 죽은 것을 미리 알아야 하는 provider 만 {@code true} 다. 기본은 열린 래치를 닫는 용도로만 쓴다.
   */
  default boolean livenessTarget() {
    return false;
  }
```

`OllamaProviderProbe.java`:

```java
package ai.devpath.aigw.provider;

import java.time.Duration;
import java.util.List;
import org.springframework.web.client.RestClient;

/**
 * 폴백 자리 Ollama 의 생존 탐색기(스펙 2026-10-03 §3.1-4). {@code GET /api/tags} 로 응답하는지,
 * 설정한 모델이 <b>정확히 같은 이름으로</b> 올라와 있는지 본다.
 *
 * <p>생존 탐색({@link ProviderProbeScheduler#runLivenessProbes})과 열린 래치의 복구 탐색
 * ({@link ProviderProbeScheduler#runDueProbes}) 양쪽에 쓰인다. 예외를 감싸지 않는다 —
 * {@link ProviderFailures} 가 상태코드·연결 실패·{@link OllamaModelUnavailableException} 을 분류한다.
 * 연결 3초·읽기 5초 상한으로 단일 스케줄러 스레드를 오래 붙들지 않는다.
 */
public class OllamaProviderProbe implements ProviderProbe {

  private static final Duration CONNECT_TIMEOUT = Duration.ofSeconds(3);
  private static final Duration READ_TIMEOUT = Duration.ofSeconds(5);

  private final String feature;
  private final String model;
  private final RestClient restClient;

  public OllamaProviderProbe(String feature, String baseUrl, String model) {
    this(feature, baseUrl, model, CONNECT_TIMEOUT, READ_TIMEOUT);
  }

  OllamaProviderProbe(
      String feature, String baseUrl, String model, Duration connectTimeout, Duration readTimeout) {
    this.feature = feature;
    this.model = model;
    this.restClient = RestClient.builder().baseUrl(baseUrl)
        .requestFactory(OllamaHttp.requestFactory(connectTimeout, readTimeout)).build();
  }

  @Override
  public String feature() { return feature; }

  @Override
  public String provider() { return "ollama"; }

  @Override
  public boolean livenessTarget() { return true; }

  @Override
  public void ping() {
    Tags tags = restClient.get().uri("/api/tags").retrieve().body(Tags.class);
    boolean loaded = tags != null && tags.models() != null
        && tags.models().stream().anyMatch(m -> model.equals(m.name()));
    if (!loaded) {
      throw new OllamaModelUnavailableException("Ollama model is not loaded: " + model);
    }
  }

  private record Tags(List<Model> models) {}

  private record Model(String name) {}
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: 같은 명령, 그리고 기존 탐색 테스트도:
`D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.provider.OllamaProviderProbeTest' --tests 'ai.devpath.aigw.provider.ClaudeProviderProbeTest' --tests 'ai.devpath.aigw.provider.ProviderProbeSchedulerTest'`
Expected: PASS — 세 XML `failures="0" errors="0"`(`OllamaProviderProbeTest` `tests="7"`)

- [ ] **Step 5: Commit**

```bash
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb add src/main/java/ai/devpath/aigw/provider/ProviderProbe.java src/main/java/ai/devpath/aigw/provider/OllamaProviderProbe.java src/test/java/ai/devpath/aigw/provider/OllamaProviderProbeTest.java
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb commit -m "feat(provider): probe the fallback Ollama for liveness and its configured model"
```

---

### Task 11: 생존 탐색 루프

**Files:**
- Modify: `src/main/java/ai/devpath/aigw/provider/ProviderProbeScheduler.java`(메서드 추가)
- Modify: `src/main/resources/application.yml`(`devpath.provider` 절)
- Test: `src/test/java/ai/devpath/aigw/provider/ProviderProbeSchedulerTest.java`

**Interfaces:**
- Consumes: `ProviderProbe.livenessTarget()`(Task 10) · `ProviderLatch.recordProbeFailure`(기존)
- Produces: `public void ProviderProbeScheduler.runLivenessProbes()` — `@Scheduled(fixedDelayString = "${devpath.provider.liveness-interval:PT30S}")`

- [ ] **Step 1: Write the failing test** — `ProviderProbeSchedulerTest` 에 `LivenessProbe` 스텁과 테스트를 추가

```java
  private static final class LivenessProbe implements ProviderProbe {
    private final String feature;
    private final String provider;
    private final RuntimeException failure;
    int pings;

    LivenessProbe(String feature, String provider, RuntimeException failure) {
      this.feature = feature;
      this.provider = provider;
      this.failure = failure;
    }

    @Override public String feature() { return feature; }
    @Override public String provider() { return provider; }
    @Override public boolean livenessTarget() { return true; }
    @Override public void ping() {
      pings++;
      if (failure != null) throw failure;
    }
  }

  private static RestClientResponseException unavailable() {
    return new RestClientResponseException(
        "Service Unavailable", 503, "Service Unavailable", new HttpHeaders(), null, null);
  }

  @Test
  void livenessFailureOpensTheLatchImmediately() {
    // 사용자 요청의 「3연속」 게이트를 쓰지 않는다 — 죽은 폴백을 다음 요청 전에 막아야 한다.
    ProviderLatch latch = new ProviderLatch(new MovableClock());
    LivenessProbe ollama = new LivenessProbe("review", "ollama", unavailable());

    new ProviderProbeScheduler(latch, List.of(ollama)).runLivenessProbes();

    assertEquals(1, ollama.pings);
    assertTrue(latch.isOpen("review", "ollama"));
  }

  @Test
  void livenessSuccessLeavesTheUserFailureCountAlone() {
    ProviderLatch latch = new ProviderLatch(new MovableClock());
    latch.recordFailure("review", "ollama", FailureKind.TRANSIENT, null);
    latch.recordFailure("review", "ollama", FailureKind.TRANSIENT, null);

    new ProviderProbeScheduler(latch, List.of(new LivenessProbe("review", "ollama", null)))
        .runLivenessProbes();
    latch.recordFailure("review", "ollama", FailureKind.TRANSIENT, null);

    // 성공한 생존 핑이 recordSuccess 를 하면 카운터가 0 이 되어 세 번째에서 열리지 않는다.
    assertTrue(latch.isOpen("review", "ollama"));
  }

  @Test
  void livenessSkipsALatchThatIsAlreadyOpen() {
    ProviderLatch latch = new ProviderLatch(new MovableClock());
    latch.recordFailure("review", "ollama", FailureKind.AUTH, null);
    LivenessProbe ollama = new LivenessProbe("review", "ollama", null);

    new ProviderProbeScheduler(latch, List.of(ollama)).runLivenessProbes();

    assertEquals(0, ollama.pings);
  }

  @Test
  void livenessIgnoresProbesThatAreNotLivenessTargets() {
    ProviderLatch latch = new ProviderLatch(new MovableClock());
    StubProbe claude = new StubProbe("review", "claude", unavailable());

    new ProviderProbeScheduler(latch, List.of(claude)).runLivenessProbes();

    assertEquals(0, claude.pings);
    assertFalse(latch.isOpen("review", "claude"));
  }

  @Test
  void theOpenedLivenessLatchIsClosedByTheDueProbeOnceOllamaReturns() {
    MovableClock clock = new MovableClock();
    ProviderLatch latch = new ProviderLatch(clock);
    new ProviderProbeScheduler(latch, List.of(new LivenessProbe("review", "ollama", unavailable())))
        .runLivenessProbes();
    assertTrue(latch.isOpen("review", "ollama"));

    clock.advance(Duration.ofMinutes(2));
    new ProviderProbeScheduler(latch, List.of(new LivenessProbe("review", "ollama", null)))
        .runDueProbes();

    assertFalse(latch.isOpen("review", "ollama"));
  }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.provider.ProviderProbeSchedulerTest'`
Expected: FAIL — `cannot find symbol: method runLivenessProbes()`

- [ ] **Step 3: Write minimal implementation** — `ProviderProbeScheduler` 의 `runDueProbes()` 아래에 추가

```java
  /**
   * 폴백 자리 provider 의 생존 탐색(스펙 2026-10-03 §3.1-5). 래치가 <b>닫힌</b> 대상만 핑한다 —
   * 열린 것은 {@link #runDueProbes} 가 복구를 맡는다. 실패하면 사용자 요청의 「3연속」 게이트 없이
   * 즉시 연다(다음 요청이 죽은 폴백으로 가서 지연을 물지 않게). 성공은 기록하지 않는다 — 사용자
   * 요청 실패 카운터는 실제 호출에 대한 증거라 핑 하나로 지우지 않는다.
   */
  @Scheduled(fixedDelayString = "${devpath.provider.liveness-interval:PT30S}")
  public void runLivenessProbes() {
    for (ProviderProbe probe : probes) {
      if (!probe.livenessTarget() || latch.isOpen(probe.feature(), probe.provider())) continue;
      try {
        probe.ping();
      } catch (RuntimeException e) {
        ProviderFailures.Classified c = ProviderFailures.classify(e);
        boolean open = latch.recordProbeFailure(
            probe.feature(), probe.provider(), c.kind(), c.retryAfter());
        log.warn("provider liveness probe failed: feature={} provider={} kind={} latchOpen={} reason={}",
            probe.feature(), probe.provider(), c.kind(), open, e.toString());
      }
    }
  }
```

`application.yml` 의 `devpath.provider` 절, `probe-interval` 아래에 추가:

```yaml
    # 폴백 자리 Ollama 의 생존 탐색 주기. 래치가 닫혀 있어도 핑해 죽은 폴백을 요청 전에 막는다(스펙 2026-10-03 §3.1-5).
    liveness-interval: ${PROVIDER_LIVENESS_INTERVAL:PT30S}
```

- [ ] **Step 4: Run test to verify it passes**

Run: 같은 명령
Expected: PASS — `failures="0" errors="0"`(기존 + 신규 5)

- [ ] **Step 5: Commit**

```bash
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb add src/main/java/ai/devpath/aigw/provider/ProviderProbeScheduler.java src/main/resources/application.yml src/test/java/ai/devpath/aigw/provider/ProviderProbeSchedulerTest.java
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb commit -m "feat(provider): open the fallback latch from a periodic liveness probe"
```

---

### Task 12: Ollama 탐색 빈 — 폴백 자리에 있을 때만

**Files:**
- Modify: `src/main/java/ai/devpath/aigw/provider/ProviderChain.java`(메서드 추가)
- Create: `src/main/java/ai/devpath/aigw/provider/OllamaProbeConfig.java`
- Test: `src/test/java/ai/devpath/aigw/provider/ProviderChainTest.java` · `src/test/java/ai/devpath/aigw/provider/OllamaProbeConfigTest.java`

**Interfaces:**
- Produces: `static boolean ProviderChain.isFallback(String provider, String fallbackCsv, String name)` — `requestedNames` 규칙(trim·빈 값·중복 제거) 그대로, `name` 의 위치가 1 이상이면 `true`
- Produces: 빈 `reviewOllamaProbe` · `communitySeedOllamaProbe` · `retentionOllamaProbe`(각각 `ProviderProbe`, 조건부)

- [ ] **Step 1: Write the failing tests**

`ProviderChainTest` 끝에 추가:

```java
  @Test
  void ollamaInTheFallbackSlotIsAFallback() {
    assertTrue(ProviderChain.isFallback("claude", "ollama", "ollama"));
  }

  @Test
  void thePrimaryIsNotAFallback() {
    assertFalse(ProviderChain.isFallback("ollama", "claude", "ollama"));
  }

  @Test
  void anAbsentProviderIsNotAFallback() {
    assertFalse(ProviderChain.isFallback("claude", "", "ollama"));
  }

  @Test
  void isFallbackTrimsAndDeduplicates() {
    // Review Focus 1: 체인 순서와 같은 규칙.
    assertTrue(ProviderChain.isFallback(" claude ", " ollama , ollama ,", "ollama"));
    assertFalse(ProviderChain.isFallback("claude", " claude , ", "claude"));
  }
```

(`ProviderChainTest` 에 `assertTrue`·`assertFalse` static import 가 없으면 더한다.)

`OllamaProbeConfigTest.java`:

```java
package ai.devpath.aigw.provider;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

class OllamaProbeConfigTest {

  private final ApplicationContextRunner runner =
      new ApplicationContextRunner().withUserConfiguration(OllamaProbeConfig.class);

  @Test
  void registersALivenessProbeForEachFeatureWhoseFallbackIsOllama() {
    runner
        .withPropertyValues(
            "devpath.review.provider=claude", "devpath.review.fallback=ollama",
            "devpath.community-seed.provider=claude", "devpath.community-seed.fallback=ollama",
            "devpath.retention.provider=claude", "devpath.retention.fallback=ollama",
            "devpath.review.ollama-base-url=http://ollama-gpu.devpath.svc:11434",
            "devpath.review.ollama-model=qwen2.5:7b")
        .run(context -> {
          Map<String, ProviderProbe> probes = context.getBeansOfType(ProviderProbe.class);
          assertThat(probes).hasSize(3);
          assertThat(probes.values()).allMatch(ProviderProbe::livenessTarget);
          assertThat(probes.values()).extracting(ProviderProbe::feature)
              .containsExactlyInAnyOrder("review", "community-seed", "retention");
        });
  }

  @Test
  void registersNothingWithoutAFallback() {
    runner
        .withPropertyValues(
            "devpath.review.provider=claude", "devpath.community-seed.provider=claude",
            "devpath.retention.provider=claude")
        .run(context -> assertThat(context.getBeansOfType(ProviderProbe.class)).isEmpty());
  }

  @Test
  void registersNothingWhenOllamaIsThePrimary() {
    runner
        .withPropertyValues("devpath.review.provider=ollama", "devpath.review.fallback=claude")
        .run(context -> assertThat(context.getBeansOfType(ProviderProbe.class)).isEmpty());
  }

  @Test
  void registersNothingForAMockFeature() {
    // provider=mock 이면 ClientConfig 가 체인을 만들지 않는다 — 탐색할 폴백이 없다.
    runner
        .withPropertyValues("devpath.review.provider=mock", "devpath.review.fallback=ollama")
        .run(context -> assertThat(context.getBeansOfType(ProviderProbe.class)).isEmpty());
  }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.provider.ProviderChainTest' --tests 'ai.devpath.aigw.provider.OllamaProbeConfigTest'`
Expected: FAIL — `cannot find symbol: method isFallback` · `cannot find symbol: class OllamaProbeConfig`

- [ ] **Step 3: Write minimal implementation**

`ProviderChain` 의 `requestedCount` 아래에 추가:

```java
  /**
   * {@code name} 이 체인의 1순위가 아닌 자리(폴백)에 있는가. {@link #ordered} 와 같은 규칙
   * (trim·빈 값·중복 제거)으로 판단한다 — 탐색 빈의 조건과 실제 체인이 어긋나지 않게.
   */
  public static boolean isFallback(String provider, String fallbackCsv, String name) {
    return requestedNames(provider, fallbackCsv).indexOf(name) > 0;
  }
```

`OllamaProbeConfig.java`:

```java
package ai.devpath.aigw.provider;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 세 기능의 Ollama 생존·복구 탐색기(스펙 2026-10-03 §3.1-4). <b>Ollama 가 그 기능의 폴백 자리에
 * 있을 때만</b> 만든다 — fallback 이 비어 있는 환경(체인 길이 1)에서는 탐색 트래픽이 0 이다.
 * 주소·모델은 기능별 ClientConfig 와 같은 키를 읽는다(탐색이 실제 폴백과 같은 곳을 본다).
 */
@Configuration
public class OllamaProbeConfig {

  @Bean
  @ConditionalOnExpression("'${devpath.review.provider:mock}'.trim() != 'mock' and "
      + "T(ai.devpath.aigw.provider.ProviderChain).isFallback("
      + "'${devpath.review.provider:mock}', '${devpath.review.fallback:}', 'ollama')")
  public ProviderProbe reviewOllamaProbe(
      @Value("${devpath.review.ollama-base-url:${devpath.ollama.base-url:http://localhost:11434}}")
      String baseUrl,
      @Value("${devpath.review.ollama-model:qwen2.5-coder:7b}") String model) {
    return new OllamaProviderProbe(ProviderFeatures.REVIEW, baseUrl, model);
  }

  @Bean
  @ConditionalOnExpression("'${devpath.community-seed.provider:mock}'.trim() != 'mock' and "
      + "T(ai.devpath.aigw.provider.ProviderChain).isFallback("
      + "'${devpath.community-seed.provider:mock}', '${devpath.community-seed.fallback:}', 'ollama')")
  public ProviderProbe communitySeedOllamaProbe(
      @Value("${devpath.community-seed.ollama-base-url:${devpath.ollama.base-url:http://localhost:11434}}")
      String baseUrl,
      @Value("${devpath.community-seed.ollama-model:qwen2.5:7b}") String model) {
    return new OllamaProviderProbe(ProviderFeatures.COMMUNITY_SEED, baseUrl, model);
  }

  @Bean
  @ConditionalOnExpression("'${devpath.retention.provider:mock}'.trim() != 'mock' and "
      + "T(ai.devpath.aigw.provider.ProviderChain).isFallback("
      + "'${devpath.retention.provider:mock}', '${devpath.retention.fallback:}', 'ollama')")
  public ProviderProbe retentionOllamaProbe(
      @Value("${devpath.retention.ollama-base-url:${devpath.ollama.base-url:http://localhost:11434}}")
      String baseUrl,
      @Value("${devpath.retention.ollama-model:qwen2.5:7b}") String model) {
    return new OllamaProviderProbe(ProviderFeatures.RETENTION, baseUrl, model);
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: 같은 명령
Expected: PASS — 두 XML `failures="0" errors="0"`

- [ ] **Step 5: Commit**

```bash
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb add src/main/java/ai/devpath/aigw/provider/ProviderChain.java src/main/java/ai/devpath/aigw/provider/OllamaProbeConfig.java src/test/java/ai/devpath/aigw/provider/ProviderChainTest.java src/test/java/ai/devpath/aigw/provider/OllamaProbeConfigTest.java
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb commit -m "feat(provider): register Ollama probes only where Ollama is the fallback"
```

---

### Task 13: 동등성 종단 테스트 · 전체 스위트 · PR

**Files:**
- Test: `src/test/java/ai/devpath/aigw/provider/FallbackParityTest.java`

**Interfaces:**
- Consumes: 위의 모든 Task — 실제 ClientConfig·Claude 빈·`OllamaProbeConfig`·`ProviderProbeScheduler` 를 조립해 검증

- [ ] **Step 1: Write the test**

```java
package ai.devpath.aigw.provider;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.devpath.aigw.community.AiSeedClient;
import ai.devpath.aigw.community.CommunitySeedClaudeConfig;
import ai.devpath.aigw.community.CommunitySeedClientConfig;
import ai.devpath.aigw.community.SeedInput;
import ai.devpath.aigw.community.SeedPromptBuilder;
import ai.devpath.aigw.retention.ReEngagementClientConfig;
import ai.devpath.aigw.retention.ReEngagementInput;
import ai.devpath.aigw.retention.ReEngagementPromptBuilder;
import ai.devpath.aigw.retention.ReEngagementSuggestionClient;
import ai.devpath.aigw.retention.RetentionClaudeClientConfig;
import ai.devpath.aigw.review.AiReviewClient;
import ai.devpath.aigw.review.ClaudeClientConfig;
import ai.devpath.aigw.review.ReviewClientConfig;
import ai.devpath.aigw.review.ReviewInput;
import ai.devpath.aigw.review.ReviewPromptBuilder;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.boot.convert.ApplicationConversionService;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.ApplicationContext;
import tools.jackson.databind.json.JsonMapper;

/**
 * 스펙 2026-10-03 §2 의 성공 기준을 실제 조립으로 증명한다: 폴백(Ollama)이 죽어 있으면 Claude 는 폴백을
 * 끈 상태와 같은 재시도 예산을 받는다. Claude 목이 처음 500, 다음 200 을 주면 요청이 <b>성공</b>해야 하고
 * (재시도 0 이면 실패한다), 생존 탐색이 돌기 전(폴백이 살아 보임)에는 Claude 가 한 번에 실패를 넘긴다.
 */
class FallbackParityTest {

  private static String message(String text) {
    String escaped = text.replace("\\", "\\\\").replace("\"", "\\\"");
    return """
        {"id":"msg_parity","type":"message","role":"assistant","model":"claude-sonnet-4-6",
         "content":[{"type":"text","text":"%s"}],"stop_reason":"end_turn","stop_sequence":null,
         "usage":{"input_tokens":1,"output_tokens":1}}
        """.formatted(escaped);
  }

  private static final ReviewInput REVIEW_INPUT = new ReviewInput("python", "print(1)", "1", "", 0);
  private static final SeedInput SEED_INPUT = new SeedInput("질문 제목", "질문 본문입니다.");
  private static final ReEngagementInput RETENTION_INPUT = new ReEngagementInput(
      7L, Instant.parse("2026-09-20T00:00:00Z"), 3, "Spring Boot 기초 3/12주");

  private MockWebServer claude;
  private String deadOllama;

  @BeforeEach
  void start() throws Exception {
    claude = new MockWebServer();
    claude.start();
    MockWebServer ollama = new MockWebServer();
    ollama.start();
    deadOllama = ollama.url("/").toString();
    ollama.shutdown();   // 포트를 닫아 연결 거부 = 회수된 GPU 노드
  }

  @AfterEach
  void stop() throws Exception {
    claude.shutdown();
  }

  private ApplicationContextRunner runner() {
    String claudeUrl = claude.url("/").toString();
    return new ApplicationContextRunner()
        .withInitializer(context -> context.getBeanFactory()
            .setConversionService(ApplicationConversionService.getSharedInstance()))
        .withBean(Clock.class, Clock::systemUTC)
        .withBean(ProviderLatch.class, () -> new ProviderLatch(Clock.systemUTC()))
        .withBean(JsonMapper.class, JsonMapper::new)
        .withBean(ReviewPromptBuilder.class, ReviewPromptBuilder::new)
        .withBean(SeedPromptBuilder.class, SeedPromptBuilder::new)
        .withBean(ReEngagementPromptBuilder.class, ReEngagementPromptBuilder::new)
        .withUserConfiguration(
            ClaudeClientConfig.class, CommunitySeedClaudeConfig.class, RetentionClaudeClientConfig.class,
            ReviewClientConfig.class, CommunitySeedClientConfig.class, ReEngagementClientConfig.class,
            OllamaProbeConfig.class)
        .withPropertyValues(
            "ANTHROPIC_API_KEY=sk-test",
            "devpath.review.provider=claude", "devpath.review.fallback=ollama",
            "devpath.review.claude-base-url=" + claudeUrl,
            "devpath.review.ollama-base-url=" + deadOllama,
            "devpath.review.claude-timeout=PT5S",
            "devpath.community-seed.provider=claude", "devpath.community-seed.fallback=ollama",
            "devpath.community-seed.claude-base-url=" + claudeUrl,
            "devpath.community-seed.ollama-base-url=" + deadOllama,
            "devpath.community-seed.claude-timeout=PT5S",
            "devpath.retention.provider=claude", "devpath.retention.fallback=ollama",
            "devpath.retention.claude-base-url=" + claudeUrl,
            "devpath.retention.ollama-base-url=" + deadOllama,
            "devpath.retention.claude-timeout=PT5S");
  }

  private static void runLiveness(ApplicationContext context) {
    new ProviderProbeScheduler(context.getBean(ProviderLatch.class),
        List.copyOf(context.getBeansOfType(ProviderProbe.class).values())).runLivenessProbes();
  }

  @Test
  void retentionGetsTheSdkRetryBudgetOnceTheDeadFallbackIsDetected() {
    runner().run(context -> {
      runLiveness(context);
      assertTrue(context.getBean(ProviderLatch.class).isOpen("retention", "ollama"));
      claude.enqueue(new MockResponse().setResponseCode(500));
      claude.enqueue(new MockResponse().setHeader("Content-Type", "application/json")
          .setBody(message("다시 시작해 볼까요?")));

      assertEquals("다시 시작해 볼까요?",
          context.getBean(ReEngagementSuggestionClient.class).suggest(RETENTION_INPUT));
      assertEquals(2, claude.getRequestCount());
    });
  }

  @Test
  void beforeDetectionClaudeFailsFastToTheFallback() {
    // 대조군: 생존 탐색 전에는 폴백이 살아 보이므로 Claude 는 재시도 0 으로 한 번에 넘긴다.
    runner().run(context -> {
      claude.enqueue(new MockResponse().setResponseCode(500));

      assertThrows(RuntimeException.class,
          () -> context.getBean(ReEngagementSuggestionClient.class).suggest(RETENTION_INPUT));
      assertEquals(1, claude.getRequestCount());
    });
  }

  @Test
  void everythingBlockedStillCallsClaude() {
    runner().run(context -> {
      runLiveness(context);
      context.getBean(ProviderLatch.class)
          .recordFailure("retention", "claude", FailureKind.RATE_LIMIT, null);
      claude.enqueue(new MockResponse().setHeader("Content-Type", "application/json")
          .setBody(message("돌아오셨네요")));

      assertEquals("돌아오셨네요",
          context.getBean(ReEngagementSuggestionClient.class).suggest(RETENTION_INPUT));
    });
  }

  @Test
  void reviewGetsTheSdkRetryBudgetOnceTheDeadFallbackIsDetected() {
    runner().run(context -> {
      runLiveness(context);
      claude.enqueue(new MockResponse().setResponseCode(500));
      claude.enqueue(new MockResponse().setHeader("Content-Type", "application/json").setBody(
          message("{\"confidence\":80,\"strengths\":[],\"improvements\":[],\"security\":[]}")));

      assertEquals(80, context.getBean(AiReviewClient.class).review(REVIEW_INPUT).confidence());
      assertEquals(2, claude.getRequestCount());
    });
  }

  @Test
  void communitySeedGetsTheSdkRetryBudgetOnceTheDeadFallbackIsDetected() {
    runner().run(context -> {
      runLiveness(context);
      claude.enqueue(new MockResponse().setResponseCode(500));
      claude.enqueue(new MockResponse().setHeader("Content-Type", "application/json")
          .setBody(message("이렇게 접근해 보세요.")));

      context.getBean(AiSeedClient.class).generate(SEED_INPUT);
      assertEquals(2, claude.getRequestCount());
    });
  }
}
```

- [ ] **Step 2: Run the test**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test --tests 'ai.devpath.aigw.provider.FallbackParityTest'`
Expected: PASS — `tests="5" failures="0" errors="0"`. (이 테스트는 Task 1~12 의 결과를 검증한다 — 실패하면 해당 Task 로 돌아가 원인을 찾는다. 추측으로 테스트를 고치지 않는다.)

음성 확인: `ReviewClientConfig`·`CommunitySeedClientConfig`·`ReEngagementClientConfig` 에서 `new FallbackXxx(chain, lastResort, latch)` 를 일시적으로 `new FallbackXxx(chain, latch)` 로 바꾸면 세 `...GetsTheSdkRetryBudget...` 테스트가 `claude.getRequestCount()` 1 로 실패해야 한다. 확인 뒤 되돌린다(`git -C … diff` 가 비어야 한다).

- [ ] **Step 3: 전체 스위트**

Run: `D:/workspace/dpa/.worktrees/ai-svc-aifb/gradlew -p D:/workspace/dpa/.worktrees/ai-svc-aifb test`
Expected: BUILD SUCCESSFUL · `build/test-results/test/*.xml` 합계 `failures=0 errors=0` · `tests=` 합계가 Task 0 기준선 + 신규 테스트 수와 같다(삭제한 3개를 빼고 계산).

- [ ] **Step 4: Commit · push · PR**

```bash
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb add src/test/java/ai/devpath/aigw/provider/FallbackParityTest.java
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb commit -m "test(provider): prove a dead fallback leaves Claude its retry budget"
git -C D:/workspace/dpa/.worktrees/ai-svc-aifb push -u origin feat/ai-fallback-availability-aware-retries
```

PR 본문은 파일로 만들어 넘긴다(`D:/workspace/dpa/.worktrees/ai-svc-aifb-pr-body.md`, 레포 밖). 아래 틀의 `N`·`M` 은 Step 3 에서 **실측한 XML 합계**로 채운다:

```markdown
## 요약

폴백(Ollama)을 쓸 수 없을 때 세 기능(review·community-seed·retention)의 Claude 성공률·지연이 폴백을 끈 상태와 같아지게 한다(gitops 폴백 publisher 리뷰 M1).

- 스펙: documents `docs/superpowers/specs/2026-10-03-ai-fallback-availability-aware-retries-design.md`
- 계획: documents `docs/superpowers/plans/2026-10-03-ai-fallback-availability-aware-retries.md`

## 변경

- `ProviderAttemptPlan`: 뒤에 쓸 provider 가 없으면 LAST_RESORT, 전부 차단이면 1순위 1회(예전 `LLM_ALL_PROVIDERS_BLOCKED` 경로 제거)
- `ClaudeClients.lastResort`: `withOptions` 로 재시도만 SDK 기본(2)으로 되돌린 사본(빈 아님)
- Ollama 생존 탐색(`OllamaProviderProbe` · `runLivenessProbes` 30초 · 폴백 자리일 때만 빈)
- Ollama 연결 타임아웃 3초 분리 · Ollama 404·모델 부재 → TRANSIENT · review Ollama 404 → 일시 실패

## 검증

- 전체 스위트: tests=N failures=0 errors=0 (기준선 M, 삭제 3 = 전부 차단 테스트 교체)
- `FallbackParityTest`: 폴백 사망 시 Claude 500→200 이 성공(요청 2회), 탐지 전에는 1회로 넘김(대조군)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

```bash
gh pr create -R DevPathAi/devpath-ai-svc --base develop --head feat/ai-fallback-availability-aware-retries --title "feat(provider): 폴백을 쓸 수 없을 때 Claude 재시도 예산 유지" --body-file D:/workspace/dpa/.worktrees/ai-svc-aifb-pr-body.md
```

CI 가 녹색이면 merge commit 으로 develop 에 머지한다. 운영 반영은 다음 릴리스 캠페인이다(스펙 §6).
