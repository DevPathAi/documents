# AI provider 폴백 — 핵심 배선 구현 계획 (계획 A)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `devpath-ai-svc` 의 review·community-seed·retention 이 Claude 를 못 쓸 때 Ollama 가 이어받게 하고, 못 쓰는 상태가 지속되는 동안 매 요청이 Claude 실패 지연을 물지 않게 한다.

**Architecture:** 세 기능이 쓰는 `@ConditionalOnProperty(havingValue=...)` 는 **구현체를 하나만 빈으로 만들기 때문에 체인이 원리적으로 불가능**하다. 멘토가 이미 쓰는 방식(`@Configuration` 팩토리가 모든 구현을 `available` 맵에 담고 순서를 조립)으로 세 기능을 옮긴다. 순서는 제네릭 `ProviderChain`, 차단 상태는 `(feature, provider)` 단위 인메모리 `ProviderLatch` 가 갖는다. **가용성 실패만 래치를 연다 — 내용 실패는 열지 않는다.**

**Tech Stack:** Java 21 · Spring Boot 4 · `com.anthropic:anthropic-java:2.34.0` · Spring `RestClient`(Ollama) · JUnit 5 · Gradle Kotlin DSL (`./gradlew test`)

**Spec:** `docs/superpowers/specs/2026-09-30-ai-provider-fallback-design.md` (2026-10-01 보정 포함 — §7 실측 결과와 §D 의 구조적 보정 2건을 반드시 읽어라)

## Global Constraints

- 대상 레포는 **`devpath-ai-svc` 단독**. 다른 레포를 건드리지 않는다. **gitops 를 건드리지 않는다** — `*_FALLBACK` env 추가는 `ai_release_eval_config.rendered_config_sha256` 을 바꿔 release id 재발급을 부른다(스펙 §8).
- `application.yml` 의 새 키는 전부 **`${*_FALLBACK:}` 기본 빈 문자열**. 설정하지 않으면 **현재 운영 동작과 완전히 동일**해야 한다.
- **`mock` 을 review·community-seed·retention 체인에 넣지 않는다**(스펙 §4.1). 가짜 리뷰가 사용자 기록에 영구히 남거나 가짜 문구가 알림으로 발송되는 것은 실패보다 나쁘다. 체인이 비면 그 기능의 **기존 예외**를 던진다.
- **멘토의 기존 동작을 바꾸지 않는다**(스펙 §4.2) — `MENTOR_PROVIDER=ollama`·`MENTOR_FALLBACK=claude` 순서 유지, 멘토의 `chain.isEmpty() → mock` 안전망 유지.
- `ProviderLatch` 는 **`replicas: 1` 전제**다(gitops `apps/devpath-ai-svc/base/deployment.yaml`). 클래스 Javadoc 에 이 전제와 「스케일아웃하면 파드마다 래치가 갈라진다」를 적는다.
- 테스트에 **실시간 `sleep` 금지**. `ProviderLatch` 는 `java.time.Clock` 을 주입받아 결정적으로 검증한다.
- 기존 들여쓰기 관례를 따른다: `review`·`community`·`mentor` 패키지는 **스페이스 2칸**, `retention` 패키지는 **탭**.

## Review Focus

스펙이 함축하지만 어떤 task 의 테스트도 건드리지 않아, 사람이 쓸 때 물릴 가능성이 높은 입력·상태 다섯 가지. 각 줄의 테스트는 그 코드를 소유한 task 에 넣었다.

1. **`REVIEW_FALLBACK=claude` 처럼 주 provider 와 같은 이름이 fallback 에 또 들어온다** — 중복은 제거돼 체인 길이가 1이어야 하고, 예외가 아니어야 한다. → Task 1
2. **`REVIEW_FALLBACK=" ollama , , claude "` 처럼 공백·빈 항목이 섞인다** — trim 되고 빈 항목은 버려져야 한다. → Task 1
3. **`REVIEW_FALLBACK=ollama` 인데 `ANTHROPIC_API_KEY` 가 없다** — Claude 빈이 없어 체인이 `[ollama]` 하나가 되고, 부팅이 실패하지 않아야 한다. → Task 4
4. **래치가 열린 뒤 모든 provider 가 차단된다** — 체인이 전부 건너뛰어져 비면, 그 기능의 **기존 예외**가 나와야 한다(널 반환이나 `IndexOutOfBounds` 가 아니라). → Task 5
5. **같은 `(feature, provider)` 에 `transient` 실패와 성공이 섞여 온다** — 성공 한 번이 연속 카운터를 0 으로 되돌려, 2회 실패 + 성공 + 2회 실패로는 래치가 열리지 않아야 한다. → Task 2

---

## File Structure

| 파일 | 책임 |
|---|---|
| `src/main/java/ai/devpath/aigw/provider/ProviderChain.java` (신규) | **순서만.** `provider` + `fallback` CSV 를 `available` 로 필터링한 리스트 |
| `src/main/java/ai/devpath/aigw/provider/FailureKind.java` (신규) | 실패 종류 enum |
| `src/main/java/ai/devpath/aigw/provider/ProviderLatch.java` (신규) | **상태만.** `(feature, provider)` 차단 상태·기한·연속 카운터·`dueProbes()` |
| `src/main/java/ai/devpath/aigw/provider/ProviderFailures.java` (신규) | SDK·HTTP 예외 → `FailureKind` + `retryAfter` 분류 |
| `src/main/java/ai/devpath/aigw/provider/ProviderLatchConfig.java` (신규) | `Clock`·`ProviderLatch` 빈 등록 (프로세스 전역 1개) |
| `src/main/java/ai/devpath/aigw/provider/ProviderProbe.java` (신규) | 한 `(feature, provider)` 의 복구 확인 호출 — 인터페이스 |
| `src/main/java/ai/devpath/aigw/provider/ProviderProbeScheduler.java` (신규) | 기한이 지난 항목을 배경에서 ping 해 래치를 닫는다 |
| `src/main/java/ai/devpath/aigw/provider/ClaudeProviderProbe.java` · `ClaudeProbeConfig.java` (신규) | 세 기능의 Claude 탐색기(출력 1토큰) — 스케줄러가 `List<ProviderProbe>` 로 받는다 |
| `src/test/java/ai/devpath/aigw/provider/MockExclusionTest.java` (신규) | 스펙 §4.1 회귀 잠금 — `mock` 이 세 체인에 들어가지 않음 |
| `review/FallbackAiReviewClient.java` (신규) · `ReviewClientConfig.java` (신규) | review 체인 |
| `community/FallbackAiSeedClient.java` (신규) · `CommunitySeedClientConfig.java` (신규) | community-seed 체인 |
| `retention/OllamaReEngagementClient.java` (신규) · `FallbackReEngagementClient.java` (신규) · `ReEngagementClientConfig.java` (신규) | retention 체인 + **유일한 신규 구현** |
| `mentor/MentorClientConfig.java` (수정) | `orderedChain` 을 `ProviderChain` 호출로 교체 |
| `review/ClaudeClientConfig.java` · `community/CommunitySeedClaudeConfig.java` · `retention/RetentionClaudeClientConfig.java` (수정) | 빈 조건을 **키 존재**로 바꾸고 `maxRetries(0)` 적용 |
| `review/{Claude,Ollama,Mock}AiReviewClient.java` · `community/{Claude,Ollama,Mock}SeedClient.java` · `retention/{Claude,Mock}ReEngagementClient.java` (수정) | `@Component`·`@ConditionalOnProperty` 제거 (팩토리가 생성) |
| `src/main/resources/application.yml` (수정) | `fallback:` 키 3개 추가 |

---

## Task 1: `ProviderChain` — 순서를 제네릭으로 올린다

**Files:**
- Create: `src/main/java/ai/devpath/aigw/provider/ProviderChain.java`
- Create: `src/test/java/ai/devpath/aigw/provider/ProviderChainTest.java`
- Modify: `src/main/java/ai/devpath/aigw/mentor/MentorClientConfig.java` (`orderedChain` 삭제, `ProviderChain.ordered` 호출)
- Modify: `src/test/java/ai/devpath/aigw/mentor/MentorClientConfigTest.java` (`orderedChain` 을 부르는 테스트가 있으면 호출만 바꾼다)

**Interfaces:**
- Consumes: 없음
- Produces:
  - `static <T> List<T> ProviderChain.ordered(String provider, String fallbackCsv, Map<String, T> available)`
  - `static <T> LinkedHashMap<String, T> ProviderChain.orderedMap(String provider, String fallbackCsv, Map<String, T> available)` — 같은 순서를 **provider 이름까지 유지해서** 돌려준다. Task 5~7 의 `Fallback*Client` 가 래치를 조회하려면 이름이 필요하다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/aigw/provider/ProviderChainTest.java`:

```java
package ai.devpath.aigw.provider;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ProviderChainTest {

  private Map<String, String> available() {
    Map<String, String> available = new LinkedHashMap<>();
    available.put("ollama", "OLLAMA");
    available.put("claude", "CLAUDE");
    available.put("mock", "MOCK");
    return available;
  }

  @Test
  void putsThePrimaryFirstThenTheFallbacksInOrder() {
    assertEquals(List.of("CLAUDE", "OLLAMA"),
        ProviderChain.ordered("claude", "ollama", available()));
  }

  @Test
  void dropsNamesThatAreNotAvailable() {
    assertEquals(List.of("CLAUDE"),
        ProviderChain.ordered("claude", "gemini", available()));
  }

  @Test
  void dropsADuplicateOfThePrimary() {
    // Review Focus 1: REVIEW_FALLBACK=claude with REVIEW_PROVIDER=claude must not duplicate.
    assertEquals(List.of("CLAUDE"),
        ProviderChain.ordered("claude", "claude", available()));
  }

  @Test
  void trimsWhitespaceAndDropsEmptyEntries() {
    // Review Focus 2: " ollama , , claude " must parse to two entries.
    assertEquals(List.of("CLAUDE", "OLLAMA"),
        ProviderChain.ordered(" claude ", " ollama , , ", available()));
  }

  @Test
  void returnsAnEmptyListWhenNothingMatches() {
    assertEquals(List.of(), ProviderChain.ordered("gemini", null, available()));
  }

  @Test
  void toleratesANullPrimary() {
    assertEquals(List.of("OLLAMA"), ProviderChain.ordered(null, "ollama", available()));
  }

  @Test
  void orderedMapKeepsTheProviderNamesInChainOrder() {
    // Fallback*Client 가 래치를 조회하려면 값이 아니라 이름이 필요하다.
    assertEquals(List.of("claude", "ollama"),
        List.copyOf(ProviderChain.orderedMap("claude", "ollama", available()).keySet()));
    assertEquals(List.of("CLAUDE", "OLLAMA"),
        List.copyOf(ProviderChain.orderedMap("claude", "ollama", available()).values()));
  }

  @Test
  void orderedMapIsEmptyWhenNothingMatches() {
    assertEquals(Map.of(), ProviderChain.orderedMap("gemini", null, available()));
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd D:/workspace/dpa/devpath-ai-svc && ./gradlew test --tests 'ai.devpath.aigw.provider.ProviderChainTest'`
Expected: 컴파일 실패 — `package ai.devpath.aigw.provider does not exist`

- [ ] **Step 3: 최소 구현을 쓴다**

`src/main/java/ai/devpath/aigw/provider/ProviderChain.java`:

```java
package ai.devpath.aigw.provider;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * provider 체인의 <b>순서만</b> 결정한다. 상태(차단 여부)는 {@link ProviderLatch} 가 갖는다.
 *
 * <p>원래 {@code MentorClientConfig.orderedChain} 이었다. 순수 static 함수라 그대로 올렸고,
 * 멘토는 계속 이것을 부른다.
 */
public final class ProviderChain {

  private ProviderChain() {}

  /** provider + fallback CSV 순서로, available 에 존재하는 것만, 중복 제거해 반환한다. */
  public static <T> List<T> ordered(String provider, String fallbackCsv, Map<String, T> available) {
    List<String> order = new ArrayList<>();
    order.add(provider == null ? "" : provider.trim());
    if (fallbackCsv != null) {
      for (String f : fallbackCsv.split(",")) {
        String t = f.trim();
        if (!t.isEmpty()) order.add(t);
      }
    }
    List<T> chain = new ArrayList<>();
    Set<String> seen = new LinkedHashSet<>();
    for (String name : order) {
      if (name.isEmpty() || !seen.add(name)) continue;
      T c = available.get(name);
      if (c != null) chain.add(c);
    }
    return chain;
  }

  /**
   * {@link #ordered} 와 같은 순서를 <b>provider 이름까지 유지해서</b> 돌려준다.
   * 래치는 {@code (feature, provider)} 로 조회하므로 체인이 이름을 알아야 한다.
   */
  public static <T> LinkedHashMap<String, T> orderedMap(
      String provider, String fallbackCsv, Map<String, T> available) {
    LinkedHashMap<String, String> identity = new LinkedHashMap<>();
    for (String name : available.keySet()) identity.put(name, name);
    LinkedHashMap<String, T> chain = new LinkedHashMap<>();
    for (String name : ordered(provider, fallbackCsv, identity)) {
      chain.put(name, available.get(name));
    }
    return chain;
  }
}
```

`import java.util.LinkedHashMap;` 를 추가한다.

- [ ] **Step 4: 통과를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.provider.ProviderChainTest'`
Expected: PASS (8 tests)

- [ ] **Step 5: 멘토를 새 함수로 돌린다**

`mentor/MentorClientConfig.java` 에서 `orderedChain` 메서드 **전체를 삭제**하고, 호출부를 바꾼다:

```java
    List<AiMentorClient> chain = ProviderChain.ordered(provider, fallbackCsv, available);
```

import 를 추가한다: `import ai.devpath.aigw.provider.ProviderChain;`
그리고 더 이상 쓰이지 않는 import 를 지운다: `java.util.ArrayList` · `java.util.LinkedHashSet` · `java.util.Set`.

- [ ] **Step 6: 멘토 테스트가 깨지지 않는지 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.mentor.*'`
Expected: PASS. `MentorClientConfigTest` 가 `MentorClientConfig.orderedChain(...)` 을 직접 부르면 `ProviderChain.ordered(...)` 로만 바꾼다 — **단언은 바꾸지 않는다.**

- [ ] **Step 7: 커밋**

```bash
git add src/main/java/ai/devpath/aigw/provider/ProviderChain.java \
        src/test/java/ai/devpath/aigw/provider/ProviderChainTest.java \
        src/main/java/ai/devpath/aigw/mentor/MentorClientConfig.java \
        src/test/java/ai/devpath/aigw/mentor/MentorClientConfigTest.java
git commit -m "refactor(provider): lift the mentor provider chain to a generic ProviderChain"
```

---

## Task 2: `ProviderLatch` — 차단 상태와 기한

**Files:**
- Create: `src/main/java/ai/devpath/aigw/provider/FailureKind.java`
- Create: `src/main/java/ai/devpath/aigw/provider/ProviderLatch.java`
- Create: `src/test/java/ai/devpath/aigw/provider/ProviderLatchTest.java`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `enum FailureKind { AUTH, RATE_LIMIT, TRANSIENT, BAD_REQUEST, OUTPUT_INVALID }`
  - `ProviderLatch(Clock clock)`
  - `boolean isOpen(String feature, String provider)`
  - `void recordFailure(String feature, String provider, FailureKind kind, Duration retryAfter)` — `retryAfter` 는 null 가능
  - `void recordSuccess(String feature, String provider)`
  - `List<ProviderLatch.Probe> dueProbes()` — `record Probe(String feature, String provider)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/aigw/provider/ProviderLatchTest.java`:

```java
package ai.devpath.aigw.provider;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.Test;

class ProviderLatchTest {

  /** 테스트가 시간을 직접 밀어 준다 — 실시간 sleep 금지. */
  private static final class MovableClock extends Clock {
    private Instant now = Instant.parse("2026-10-01T00:00:00Z");

    void advance(Duration d) { now = now.plus(d); }

    @Override public ZoneOffset getZone() { return ZoneOffset.UTC; }
    @Override public Clock withZone(java.time.ZoneId zone) { return this; }
    @Override public Instant instant() { return now; }
  }

  @Test
  void startsClosed() {
    assertFalse(new ProviderLatch(new MovableClock()).isOpen("review", "claude"));
  }

  @Test
  void authOpensImmediatelyForThirtyMinutes() {
    MovableClock clock = new MovableClock();
    ProviderLatch latch = new ProviderLatch(clock);

    latch.recordFailure("review", "claude", FailureKind.AUTH, null);

    assertTrue(latch.isOpen("review", "claude"));
    clock.advance(Duration.ofMinutes(29));
    assertTrue(latch.isOpen("review", "claude"));
    clock.advance(Duration.ofMinutes(2));
    assertFalse(latch.isOpen("review", "claude"));
  }

  @Test
  void rateLimitTrustsTheRetryAfterHeader() {
    MovableClock clock = new MovableClock();
    ProviderLatch latch = new ProviderLatch(clock);

    latch.recordFailure("review", "claude", FailureKind.RATE_LIMIT, Duration.ofSeconds(90));

    clock.advance(Duration.ofSeconds(89));
    assertTrue(latch.isOpen("review", "claude"));
    clock.advance(Duration.ofSeconds(2));
    assertFalse(latch.isOpen("review", "claude"));
  }

  @Test
  void rateLimitWithoutAHeaderStartsAtFiveMinutesAndDoublesToAnHourCap() {
    MovableClock clock = new MovableClock();
    ProviderLatch latch = new ProviderLatch(clock);

    latch.recordFailure("review", "claude", FailureKind.RATE_LIMIT, null);
    clock.advance(Duration.ofMinutes(5).plusSeconds(1));
    assertFalse(latch.isOpen("review", "claude"));

    latch.recordFailure("review", "claude", FailureKind.RATE_LIMIT, null);
    clock.advance(Duration.ofMinutes(9));
    assertTrue(latch.isOpen("review", "claude"));   // 10분으로 늘었다
    clock.advance(Duration.ofMinutes(2));
    assertFalse(latch.isOpen("review", "claude"));

    for (int i = 0; i < 10; i++) {
      latch.recordFailure("review", "claude", FailureKind.RATE_LIMIT, null);
      clock.advance(Duration.ofHours(2));
    }
    latch.recordFailure("review", "claude", FailureKind.RATE_LIMIT, null);
    clock.advance(Duration.ofMinutes(61));
    assertFalse(latch.isOpen("review", "claude"));  // 상한 1시간
  }

  @Test
  void transientOpensOnlyOnTheThirdConsecutiveFailure() {
    MovableClock clock = new MovableClock();
    ProviderLatch latch = new ProviderLatch(clock);

    latch.recordFailure("review", "claude", FailureKind.TRANSIENT, null);
    assertFalse(latch.isOpen("review", "claude"));
    latch.recordFailure("review", "claude", FailureKind.TRANSIENT, null);
    assertFalse(latch.isOpen("review", "claude"));
    latch.recordFailure("review", "claude", FailureKind.TRANSIENT, null);
    assertTrue(latch.isOpen("review", "claude"));
  }

  @Test
  void oneSuccessResetsTheTransientRun() {
    // Review Focus 5: 2 fail + success + 2 fail must not open.
    MovableClock clock = new MovableClock();
    ProviderLatch latch = new ProviderLatch(clock);

    latch.recordFailure("review", "claude", FailureKind.TRANSIENT, null);
    latch.recordFailure("review", "claude", FailureKind.TRANSIENT, null);
    latch.recordSuccess("review", "claude");
    latch.recordFailure("review", "claude", FailureKind.TRANSIENT, null);
    latch.recordFailure("review", "claude", FailureKind.TRANSIENT, null);

    assertFalse(latch.isOpen("review", "claude"));
  }

  @Test
  void badRequestAndOutputInvalidNeverOpen() {
    ProviderLatch latch = new ProviderLatch(new MovableClock());

    for (int i = 0; i < 10; i++) {
      latch.recordFailure("review", "claude", FailureKind.BAD_REQUEST, null);
      latch.recordFailure("review", "claude", FailureKind.OUTPUT_INVALID, null);
    }

    assertFalse(latch.isOpen("review", "claude"));
  }

  @Test
  void successClosesAnOpenLatch() {
    ProviderLatch latch = new ProviderLatch(new MovableClock());

    latch.recordFailure("review", "claude", FailureKind.AUTH, null);
    latch.recordSuccess("review", "claude");

    assertFalse(latch.isOpen("review", "claude"));
  }

  @Test
  void keepsFeaturesAndProvidersIndependent() {
    ProviderLatch latch = new ProviderLatch(new MovableClock());

    latch.recordFailure("review", "claude", FailureKind.AUTH, null);

    assertTrue(latch.isOpen("review", "claude"));
    assertFalse(latch.isOpen("community-seed", "claude"));
    assertFalse(latch.isOpen("review", "ollama"));
  }

  @Test
  void dueProbesReportsOnlyEntriesWhoseDeadlinePassed() {
    MovableClock clock = new MovableClock();
    ProviderLatch latch = new ProviderLatch(clock);

    latch.recordFailure("review", "claude", FailureKind.AUTH, null);              // 30분
    latch.recordFailure("community-seed", "claude", FailureKind.RATE_LIMIT,
        Duration.ofMinutes(1));                                                   // 1분

    assertEquals(List.of(), latch.dueProbes());

    clock.advance(Duration.ofMinutes(2));
    assertEquals(List.of(new ProviderLatch.Probe("community-seed", "claude")), latch.dueProbes());

    clock.advance(Duration.ofMinutes(29));
    assertEquals(
        List.of(new ProviderLatch.Probe("review", "claude"),
                new ProviderLatch.Probe("community-seed", "claude")),
        latch.dueProbes());
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.provider.ProviderLatchTest'`
Expected: 컴파일 실패 — `cannot find symbol: class ProviderLatch`

- [ ] **Step 3: `FailureKind` 를 쓴다**

`src/main/java/ai/devpath/aigw/provider/FailureKind.java`:

```java
package ai.devpath.aigw.provider;

/**
 * provider 실패의 종류. <b>가용성 실패만 래치를 연다</b> — 내용 실패({@link #BAD_REQUEST},
 * {@link #OUTPUT_INVALID})는 그 요청만 다음 provider 로 넘기고 래치를 건드리지 않는다.
 * 한 사용자의 잘못된 프롬프트가 전체의 Claude 를 끊으면 안 된다.
 */
public enum FailureKind {
  /** 401·403. 키가 틀렸거나 회수됐다 — 재시도가 의미 없다. */
  AUTH,
  /** 429. 소진과 단기 제한이 같은 코드로 온다. */
  RATE_LIMIT,
  /** 5xx·연결·타임아웃. 일시적일 수 있다 — 한 번으로 끊지 않는다. */
  TRANSIENT,
  /** 400. 우리 버그다. 래치를 열지 않는다. */
  BAD_REQUEST,
  /** 파싱·스키마 실패. 가용성 문제가 아니다. 래치를 열지 않는다. */
  OUTPUT_INVALID
}
```

- [ ] **Step 4: `ProviderLatch` 를 쓴다**

`src/main/java/ai/devpath/aigw/provider/ProviderLatch.java`:

```java
package ai.devpath.aigw.provider;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * {@code (feature, provider)} 단위 차단 상태. <b>열림(open)</b> 이면 체인이 그 provider 를 건너뛴다.
 *
 * <p><b>전제: replicas = 1.</b> gitops {@code apps/devpath-ai-svc/base/deployment.yaml} 이
 * {@code replicas: 1} 이라 공유 저장소가 필요 없다. <b>스케일아웃하면 파드마다 래치가 갈라져
 * 일관성이 깨진다</b> — 그때는 공유 저장소(Redis 등)로 옮겨야 한다.
 */
public class ProviderLatch {

  /** 배경 복구 탐색이 소비하는 항목. */
  public record Probe(String feature, String provider) {}

  private static final Duration AUTH_DEADLINE = Duration.ofMinutes(30);
  private static final Duration RATE_LIMIT_BASE = Duration.ofMinutes(5);
  private static final Duration RATE_LIMIT_CAP = Duration.ofHours(1);
  private static final Duration TRANSIENT_BASE = Duration.ofMinutes(1);
  private static final Duration TRANSIENT_CAP = Duration.ofMinutes(30);
  private static final int TRANSIENT_THRESHOLD = 3;

  private static final class State {
    Instant openUntil;          // null = 닫힘
    Duration lastBackoff;       // 연속 증가용
    int transientRun;
  }

  private final Clock clock;
  private final Map<String, State> states = new ConcurrentHashMap<>();

  public ProviderLatch(Clock clock) {
    this.clock = clock;
  }

  private static String key(String feature, String provider) {
    return feature + "/" + provider;
  }

  public boolean isOpen(String feature, String provider) {
    State s = states.get(key(feature, provider));
    return s != null && s.openUntil != null && clock.instant().isBefore(s.openUntil);
  }

  public void recordSuccess(String feature, String provider) {
    State s = states.computeIfAbsent(key(feature, provider), k -> new State());
    synchronized (s) {
      s.openUntil = null;
      s.lastBackoff = null;
      s.transientRun = 0;
    }
  }

  public void recordFailure(
      String feature, String provider, FailureKind kind, Duration retryAfter) {
    State s = states.computeIfAbsent(key(feature, provider), k -> new State());
    synchronized (s) {
      switch (kind) {
        case BAD_REQUEST, OUTPUT_INVALID -> {
          // 내용 실패는 래치를 건드리지 않는다.
        }
        case AUTH -> {
          s.transientRun = 0;
          open(s, AUTH_DEADLINE);
        }
        case RATE_LIMIT -> {
          s.transientRun = 0;
          open(s, retryAfter != null ? retryAfter : next(s, RATE_LIMIT_BASE, RATE_LIMIT_CAP));
        }
        case TRANSIENT -> {
          s.transientRun++;
          if (s.transientRun >= TRANSIENT_THRESHOLD) {
            open(s, next(s, TRANSIENT_BASE, TRANSIENT_CAP));
          }
        }
      }
    }
  }

  /** 기한이 지난 항목. 열린 적 있고 기한이 지났으면 탐색 대상이다. */
  public List<Probe> dueProbes() {
    Instant now = clock.instant();
    List<Probe> due = new ArrayList<>();
    for (Map.Entry<String, State> e : states.entrySet()) {
      State s = e.getValue();
      if (s.openUntil == null || now.isBefore(s.openUntil)) continue;
      int slash = e.getKey().indexOf('/');
      due.add(new Probe(e.getKey().substring(0, slash), e.getKey().substring(slash + 1)));
    }
    return due;
  }

  private void open(State s, Duration deadline) {
    s.openUntil = clock.instant().plus(deadline);
  }

  /** 직전 기한의 두 배, 상한까지. 처음이면 base. */
  private static Duration next(State s, Duration base, Duration cap) {
    Duration d = s.lastBackoff == null ? base : s.lastBackoff.multipliedBy(2);
    if (d.compareTo(cap) > 0) d = cap;
    s.lastBackoff = d;
    return d;
  }
}
```

- [ ] **Step 5: 통과를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.provider.ProviderLatchTest'`
Expected: PASS (10 tests)

- [ ] **Step 6: 커밋**

```bash
git add src/main/java/ai/devpath/aigw/provider/FailureKind.java \
        src/main/java/ai/devpath/aigw/provider/ProviderLatch.java \
        src/test/java/ai/devpath/aigw/provider/ProviderLatchTest.java
git commit -m "feat(provider): add the per-feature provider latch with deterministic deadlines"
```

---

## Task 3: `ProviderFailures` — 예외를 `FailureKind` 로 분류한다

**Files:**
- Create: `src/main/java/ai/devpath/aigw/provider/ProviderFailures.java`
- Create: `src/test/java/ai/devpath/aigw/provider/ProviderFailuresTest.java`

**Interfaces:**
- Consumes: `FailureKind` (Task 2)
- Produces:
  - `record Classified(FailureKind kind, Duration retryAfter)` — `retryAfter` null 가능
  - `static Classified classify(Throwable t)`

**실측 근거:** Anthropic SDK 예외는 `ClaudeAiReviewClient:52-60` 이 이미 쓰는 타입들이다 — `RateLimitException` · `InternalServerException` · `AnthropicIoException` · `AnthropicRetryableException` · `AnthropicException`. Ollama 쪽은 `OllamaAiReviewClient` 가 `RestClientResponseException` · `ResourceAccessException` · `RestClientException` 를 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/aigw/provider/ProviderFailuresTest.java`:

```java
package ai.devpath.aigw.provider;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import com.anthropic.errors.AnthropicException;
import com.anthropic.errors.AnthropicIoException;
import com.anthropic.errors.BadRequestException;
import com.anthropic.errors.InternalServerException;
import com.anthropic.errors.PermissionDeniedException;
import com.anthropic.errors.RateLimitException;
import com.anthropic.errors.UnauthorizedException;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientResponseException;

class ProviderFailuresTest {

  private static RestClientResponseException http(HttpStatus status, String retryAfter) {
    HttpHeaders headers = new HttpHeaders();
    if (retryAfter != null) headers.add(HttpHeaders.RETRY_AFTER, retryAfter);
    return new RestClientResponseException(
        "boom", status.value(), status.getReasonPhrase(), headers, null, null);
  }

  @Test
  void mapsHttpStatusesToTheSpecTable() {
    assertEquals(FailureKind.AUTH, ProviderFailures.classify(http(HttpStatus.UNAUTHORIZED, null)).kind());
    assertEquals(FailureKind.AUTH, ProviderFailures.classify(http(HttpStatus.FORBIDDEN, null)).kind());
    assertEquals(FailureKind.RATE_LIMIT,
        ProviderFailures.classify(http(HttpStatus.TOO_MANY_REQUESTS, null)).kind());
    assertEquals(FailureKind.TRANSIENT,
        ProviderFailures.classify(http(HttpStatus.BAD_GATEWAY, null)).kind());
    assertEquals(FailureKind.BAD_REQUEST,
        ProviderFailures.classify(http(HttpStatus.BAD_REQUEST, null)).kind());
  }

  @Test
  void readsRetryAfterSecondsWhenPresent() {
    assertEquals(Duration.ofSeconds(90),
        ProviderFailures.classify(http(HttpStatus.TOO_MANY_REQUESTS, "90")).retryAfter());
  }

  @Test
  void leavesRetryAfterNullWhenTheHeaderIsAbsentOrUnparseable() {
    assertNull(ProviderFailures.classify(http(HttpStatus.TOO_MANY_REQUESTS, null)).retryAfter());
    assertNull(ProviderFailures.classify(
        http(HttpStatus.TOO_MANY_REQUESTS, "Wed, 01 Oct 2026 00:00:00 GMT")).retryAfter());
  }

  @Test
  void mapsConnectionAndTimeoutFailuresToTransient() {
    assertEquals(FailureKind.TRANSIENT,
        ProviderFailures.classify(new ResourceAccessException("timeout")).kind());
    assertEquals(FailureKind.TRANSIENT,
        ProviderFailures.classify(new java.net.SocketTimeoutException("read timed out")).kind());
  }

  @Test
  void mapsTheAnthropicSdkHierarchy() {
    assertEquals(FailureKind.RATE_LIMIT,
        ProviderFailures.classify(sdk(RateLimitException.class)).kind());
    assertEquals(FailureKind.AUTH, ProviderFailures.classify(sdk(UnauthorizedException.class)).kind());
    assertEquals(FailureKind.AUTH,
        ProviderFailures.classify(sdk(PermissionDeniedException.class)).kind());
    assertEquals(FailureKind.BAD_REQUEST,
        ProviderFailures.classify(sdk(BadRequestException.class)).kind());
    assertEquals(FailureKind.TRANSIENT,
        ProviderFailures.classify(sdk(InternalServerException.class)).kind());
    assertEquals(FailureKind.TRANSIENT,
        ProviderFailures.classify(new AnthropicIoException("io", new java.io.IOException())).kind());
  }

  @Test
  void treatsAnUnknownAnthropicFailureAsTransientRatherThanSilentlyIgnoringIt() {
    assertEquals(FailureKind.TRANSIENT,
        ProviderFailures.classify(new AnthropicException("unknown")).kind());
  }

  @Test
  void treatsAnUnrecognisedThrowableAsOutputInvalidSoItNeverOpensTheLatch() {
    assertEquals(FailureKind.OUTPUT_INVALID,
        ProviderFailures.classify(new IllegalStateException("schema mismatch")).kind());
  }

  @Test
  void unwrapsACauseChain() {
    assertEquals(FailureKind.RATE_LIMIT,
        ProviderFailures.classify(
            new RuntimeException("wrapped", http(HttpStatus.TOO_MANY_REQUESTS, null))).kind());
  }

  /**
   * SDK 예외는 상태코드 기반 팩토리로만 만들어지는 경우가 있다. 생성자 시그니처가 버전마다 달라
   * 테스트가 깨지는 것을 막기 위해, 구현자는 Step 2 에서 실제 시그니처를 확인하고 이 헬퍼를
   * 그에 맞춘다. 2.34.0 에서 확인되는 형태를 먼저 시도한다.
   */
  private static AnthropicException sdk(Class<? extends AnthropicException> type) {
    try {
      return type.getConstructor(String.class).newInstance("boom");
    } catch (ReflectiveOperationException e) {
      throw new AssertionError(
          "SDK 예외 생성자 시그니처를 확인하고 이 헬퍼를 고쳐라: " + type.getName(), e);
    }
  }
}
```

- [ ] **Step 2: 실패를 확인하고, SDK 예외 생성자 시그니처를 실측한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.provider.ProviderFailuresTest'`
Expected: 컴파일 실패 — `cannot find symbol: class ProviderFailures`

이 때 **SDK 타입 이름과 생성자를 실측한다**:

```bash
cd D:/workspace/dpa/devpath-ai-svc
./gradlew -q dependencies --configuration runtimeClasspath | grep anthropic
# jar 안의 예외 클래스 목록
find ~/.gradle/caches -name "anthropic-java-2.34.0.jar" | head -1 | \
  xargs -I{} unzip -l {} | grep "com/anthropic/errors/" | sed 's#.*errors/##'
```

`UnauthorizedException` · `PermissionDeniedException` · `BadRequestException` 중 없는 이름이 있으면, 그 자리를 **실제 있는 타입**으로 바꾸고 테스트의 import 도 함께 고친다. 없으면 `AnthropicException` 의 상태코드 접근자(`statusCode()` 등)로 분류하도록 Step 3 의 구현을 맞춘다. **추측하지 말고 jar 목록을 보고 결정한다.**

- [ ] **Step 3: 구현을 쓴다**

`src/main/java/ai/devpath/aigw/provider/ProviderFailures.java`:

```java
package ai.devpath.aigw.provider;

import com.anthropic.errors.AnthropicException;
import com.anthropic.errors.AnthropicIoException;
import com.anthropic.errors.InternalServerException;
import com.anthropic.errors.RateLimitException;
import java.net.SocketTimeoutException;
import java.time.Duration;
import org.springframework.http.HttpHeaders;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientResponseException;

/**
 * 예외를 {@link FailureKind} 로 분류한다. 스펙 §3 의 표가 정본이다.
 *
 * <p>알 수 없는 예외는 {@link FailureKind#OUTPUT_INVALID} 로 떨어진다 — <b>래치를 열지 않는</b>
 * 쪽이 안전한 기본값이다. 분류하지 못한 예외로 provider 를 끊는 것이 더 나쁘다.
 */
public final class ProviderFailures {

  /** retryAfter 는 429 에 Retry-After(초)가 있을 때만 채워진다. */
  public record Classified(FailureKind kind, Duration retryAfter) {}

  private ProviderFailures() {}

  public static Classified classify(Throwable t) {
    for (Throwable c = t; c != null; c = c.getCause() == c ? null : c.getCause()) {
      Classified hit = classifyOne(c);
      if (hit != null) return hit;
    }
    return new Classified(FailureKind.OUTPUT_INVALID, null);
  }

  private static Classified classifyOne(Throwable t) {
    if (t instanceof RestClientResponseException http) {
      return fromStatus(http.getStatusCode().value(), retryAfter(http.getResponseHeaders()));
    }
    if (t instanceof RateLimitException) return new Classified(FailureKind.RATE_LIMIT, null);
    if (t instanceof InternalServerException) return new Classified(FailureKind.TRANSIENT, null);
    if (t instanceof AnthropicIoException) return new Classified(FailureKind.TRANSIENT, null);
    if (t instanceof AnthropicException) {
      // Step 2 에서 실측한 상태코드 접근자가 있으면 fromStatus 로 넘긴다. 없으면 보수적으로 transient.
      return new Classified(FailureKind.TRANSIENT, null);
    }
    if (t instanceof ResourceAccessException || t instanceof SocketTimeoutException) {
      return new Classified(FailureKind.TRANSIENT, null);
    }
    return null;
  }

  private static Classified fromStatus(int status, Duration retryAfter) {
    if (status == 401 || status == 403) return new Classified(FailureKind.AUTH, null);
    if (status == 429) return new Classified(FailureKind.RATE_LIMIT, retryAfter);
    if (status == 400) return new Classified(FailureKind.BAD_REQUEST, null);
    if (status >= 500) return new Classified(FailureKind.TRANSIENT, null);
    return new Classified(FailureKind.OUTPUT_INVALID, null);
  }

  /** Retry-After 는 초(delta-seconds) 형태만 신뢰한다. HTTP-date 는 null 로 둔다. */
  private static Duration retryAfter(HttpHeaders headers) {
    if (headers == null) return null;
    String raw = headers.getFirst(HttpHeaders.RETRY_AFTER);
    if (raw == null) return null;
    try {
      long seconds = Long.parseLong(raw.trim());
      return seconds > 0 ? Duration.ofSeconds(seconds) : null;
    } catch (NumberFormatException e) {
      return null;
    }
  }
}
```

**Step 2 에서 `UnauthorizedException`·`PermissionDeniedException`·`BadRequestException` 이 jar 에 있다면** `classifyOne` 에 `RateLimitException` 앞쪽으로 세 줄을 추가한다:

```java
    if (t instanceof UnauthorizedException) return new Classified(FailureKind.AUTH, null);
    if (t instanceof PermissionDeniedException) return new Classified(FailureKind.AUTH, null);
    if (t instanceof BadRequestException) return new Classified(FailureKind.BAD_REQUEST, null);
```

- [ ] **Step 4: 통과를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.provider.ProviderFailuresTest'`
Expected: PASS. 실패하면 Step 2 의 실측으로 돌아가 타입 이름을 맞춘다 — **단언(분류 결과)은 바꾸지 않는다.**

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/aigw/provider/ProviderFailures.java \
        src/test/java/ai/devpath/aigw/provider/ProviderFailuresTest.java
git commit -m "feat(provider): classify SDK and HTTP failures into latch kinds"
```

---

## Task 4: Claude 빈을 **키 존재** 조건으로 바꾼다

**Files:**
- Modify: `src/main/java/ai/devpath/aigw/review/ClaudeClientConfig.java`
- Modify: `src/main/java/ai/devpath/aigw/community/CommunitySeedClaudeConfig.java`
- Modify: `src/main/java/ai/devpath/aigw/retention/RetentionClaudeClientConfig.java`
- Create: `src/test/java/ai/devpath/aigw/provider/ClaudeBeanConditionTest.java`

**Interfaces:**
- Consumes: 없음
- Produces: 빈 `anthropicClient` · `communitySeedAnthropicClient` · `retentionAnthropicClient` 가 **`ANTHROPIC_API_KEY` 가 비어 있지 않을 때** 존재한다(provider 값과 무관).

**왜:** 스펙 보정 §D-①. 현재는 `provider == "claude"` 일 때만 빈이 생기므로 `ollama` 주 + `claude` 상향이 **원리적으로 불가능**하다. 멘토가 이미 `@ConditionalOnExpression("'${ANTHROPIC_API_KEY:}' != ''")` 를 쓴다. §D-② 에 따라 `maxRetries(0)` 도 함께 맞춘다 — SDK 내부 재시도가 429 를 삼키면 래치 판정이 왜곡된다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/aigw/provider/ClaudeBeanConditionTest.java`:

```java
package ai.devpath.aigw.provider;

import static org.assertj.core.api.Assertions.assertThat;

import ai.devpath.aigw.community.CommunitySeedClaudeConfig;
import ai.devpath.aigw.retention.RetentionClaudeClientConfig;
import ai.devpath.aigw.review.ClaudeClientConfig;
import com.anthropic.client.AnthropicClient;
import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

class ClaudeBeanConditionTest {

  private final ApplicationContextRunner runner = new ApplicationContextRunner()
      .withConfiguration(AutoConfigurations.of())
      .withUserConfiguration(
          ClaudeClientConfig.class, CommunitySeedClaudeConfig.class,
          RetentionClaudeClientConfig.class);

  @Test
  void createsTheClaudeBeansFromTheKeyAloneRegardlessOfProvider() {
    runner
        .withPropertyValues(
            "ANTHROPIC_API_KEY=sk-test",
            "devpath.review.provider=ollama",
            "devpath.community-seed.provider=ollama",
            "devpath.retention.provider=ollama")
        .run(context -> assertThat(context.getBeansOfType(AnthropicClient.class)).hasSize(3));
  }

  @Test
  void createsNoClaudeBeanWithoutTheKeySoBootStaysSafe() {
    // Review Focus 3: fallback names claude but the key is absent -> no bean, no boot failure.
    runner
        .withPropertyValues(
            "devpath.review.provider=ollama",
            "devpath.review.fallback=claude",
            "devpath.community-seed.provider=ollama",
            "devpath.retention.provider=ollama")
        .run(context -> {
          assertThat(context).hasNotFailed();
          assertThat(context.getBeansOfType(AnthropicClient.class)).isEmpty();
        });
  }

  @Test
  void disablesSdkInternalRetriesSoTheLatchSeesTheRealFailure() {
    // SDK 기본 재시도는 429 를 삼켜 ProviderLatch 의 rate_limit 판정을 왜곡한다.
    String reviewSource = sourceOf("review/ClaudeClientConfig.java");
    String seedSource = sourceOf("community/CommunitySeedClaudeConfig.java");
    String retentionSource = sourceOf("retention/RetentionClaudeClientConfig.java");

    for (String source : new String[] {reviewSource, seedSource, retentionSource}) {
      assertThat(source).contains("maxRetries(0)");
      assertThat(source).doesNotContain("fromEnv()");
    }
  }

  private static String sourceOf(String relative) throws Exception {
    return java.nio.file.Files.readString(
        java.nio.file.Path.of("src/main/java/ai/devpath/aigw", relative));
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.provider.ClaudeBeanConditionTest'`
Expected: FAIL — 첫 테스트는 빈 0개(provider 가 `ollama` 라 조건 불충족), 세 번째는 `fromEnv()` 가 남아 있어 실패

- [ ] **Step 3: 세 설정을 바꾼다**

`review/ClaudeClientConfig.java` 전체를 다음으로 바꾼다:

```java
package ai.devpath.aigw.review;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * review 용 AnthropicClient 빈. 키는 ANTHROPIC_API_KEY 환경변수(커밋 금지).
 *
 * <p><b>조건은 provider 값이 아니라 키 존재다</b> — provider=ollama + fallback=claude 처럼
 * Claude 가 주가 아닌 배치에서도 빈이 필요하다(멘토와 동일한 방식).
 * SDK 내부 재시도는 끈다: 429 를 삼키면 ProviderLatch 의 rate_limit 판정이 왜곡된다.
 */
@Configuration
@ConditionalOnExpression("'${ANTHROPIC_API_KEY:}' != ''")
public class ClaudeClientConfig {

  @Bean
  public AnthropicClient anthropicClient(
      @Value("${ANTHROPIC_API_KEY}") String apiKey,
      @Value("${devpath.review.claude-base-url:https://api.anthropic.com}") String baseUrl,
      @Value("${devpath.review.claude-timeout:PT60S}") Duration timeout) {
    return AnthropicOkHttpClient.builder()
        .apiKey(apiKey)
        .baseUrl(baseUrl)
        .timeout(timeout)
        .maxRetries(0)
        .build();
  }
}
```

`community/CommunitySeedClaudeConfig.java` — 같은 모양으로, 빈 이름 `communitySeedAnthropicClient`, 프로퍼티 접두사 `devpath.community-seed.`:

```java
package ai.devpath.aigw.community;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * community-seed 용 AnthropicClient 빈. 조건은 provider 값이 아니라 키 존재다.
 * 빈 이름은 review(anthropicClient)·mentor(mentorAnthropicClient)와 분리한다.
 */
@Configuration
@ConditionalOnExpression("'${ANTHROPIC_API_KEY:}' != ''")
public class CommunitySeedClaudeConfig {

  @Bean(name = "communitySeedAnthropicClient")
  public AnthropicClient communitySeedAnthropicClient(
      @Value("${ANTHROPIC_API_KEY}") String apiKey,
      @Value("${devpath.community-seed.claude-base-url:https://api.anthropic.com}") String baseUrl,
      @Value("${devpath.community-seed.claude-timeout:PT60S}") Duration timeout) {
    return AnthropicOkHttpClient.builder()
        .apiKey(apiKey)
        .baseUrl(baseUrl)
        .timeout(timeout)
        .maxRetries(0)
        .build();
  }
}
```

`retention/RetentionClaudeClientConfig.java` — **이 패키지는 탭 들여쓰기다**:

```java
package ai.devpath.aigw.retention;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/** retention 용 AnthropicClient 빈. 조건은 provider 값이 아니라 키 존재다. */
@Configuration
@ConditionalOnExpression("'${ANTHROPIC_API_KEY:}' != ''")
public class RetentionClaudeClientConfig {

	@Bean(name = "retentionAnthropicClient")
	public AnthropicClient retentionAnthropicClient(
			@Value("${ANTHROPIC_API_KEY}") String apiKey,
			@Value("${devpath.retention.claude-base-url:https://api.anthropic.com}") String baseUrl,
			@Value("${devpath.retention.claude-timeout:PT60S}") Duration timeout) {
		return AnthropicOkHttpClient.builder()
				.apiKey(apiKey)
				.baseUrl(baseUrl)
				.timeout(timeout)
				.maxRetries(0)
				.build();
	}
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.provider.ClaudeBeanConditionTest'`
Expected: PASS (3 tests)

- [ ] **Step 5: 전체 스위트로 회귀를 확인한다**

Run: `./gradlew test`
Expected: PASS. **빈이 이제 키만으로 생기므로**, `provider=mock` 인데 키가 설정된 테스트 컨텍스트에서 `AnthropicClient` 빈이 새로 등장할 수 있다. 실패하면 그 테스트가 빈 **개수**를 단언하는지 확인하고, 단언을 바꾸지 말고 그 테스트의 `ANTHROPIC_API_KEY` 를 비운다.

- [ ] **Step 6: 커밋**

```bash
git add src/main/java/ai/devpath/aigw/review/ClaudeClientConfig.java \
        src/main/java/ai/devpath/aigw/community/CommunitySeedClaudeConfig.java \
        src/main/java/ai/devpath/aigw/retention/RetentionClaudeClientConfig.java \
        src/test/java/ai/devpath/aigw/provider/ClaudeBeanConditionTest.java
git commit -m "fix(provider): gate the Claude beans on the API key, not the provider value"
```

---

## Task 5: review 배선 — `@ConditionalOnProperty` 를 팩토리로 바꾼다

**Files:**
- Create: `src/main/java/ai/devpath/aigw/provider/ProviderLatchConfig.java`
- Create: `src/main/java/ai/devpath/aigw/review/FallbackAiReviewClient.java`
- Create: `src/main/java/ai/devpath/aigw/review/ReviewClientConfig.java`
- Create: `src/test/java/ai/devpath/aigw/review/FallbackAiReviewClientTest.java`
- Modify: `src/main/java/ai/devpath/aigw/review/ClaudeAiReviewClient.java` · `OllamaAiReviewClient.java` · `MockAiReviewClient.java` (`@Component`·`@ConditionalOnProperty` 와 그 import 제거)

**Interfaces:**
- Consumes: `ProviderChain.orderedMap` (Task 1) · `ProviderLatch` (Task 2) · `ProviderFailures.classify` (Task 3) · 빈 `anthropicClient` (Task 4)
- Produces:
  - 빈 `Clock providerClock()` · 빈 `ProviderLatch providerLatch(Clock)` — Task 6·7 이 주입받는다
  - `FallbackAiReviewClient(LinkedHashMap<String, AiReviewClient> delegates, ProviderLatch latch)`
  - 빈 `AiReviewClient reviewClient(...)` — 체인 길이 1이면 그 클라이언트, 2 이상이면 `FallbackAiReviewClient`

- [ ] **Step 1: 래치 빈을 등록한다**

`src/main/java/ai/devpath/aigw/provider/ProviderLatchConfig.java`:

```java
package ai.devpath.aigw.provider;

import java.time.Clock;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/** 래치는 프로세스 전역 단일 인스턴스다(replicas: 1 전제 — ProviderLatch Javadoc 참조). */
@Configuration
public class ProviderLatchConfig {

  @Bean
  public Clock providerClock() {
    return Clock.systemUTC();
  }

  @Bean
  public ProviderLatch providerLatch(Clock providerClock) {
    return new ProviderLatch(providerClock);
  }
}
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

먼저 `src/main/java/ai/devpath/aigw/review/ReviewResult.java` 를 읽어 생성자와 접근자 이름을 확인한다. 아래 테스트의 `result(...)` 헬퍼와 `.summary()` 단언을 그 실제 모양에 맞춘다 — **단언의 의미는 바꾸지 않는다.**

`src/test/java/ai/devpath/aigw/review/FallbackAiReviewClientTest.java`:

```java
package ai.devpath.aigw.review;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.devpath.aigw.provider.FailureKind;
import ai.devpath.aigw.provider.ProviderLatch;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.web.client.RestClientResponseException;

class FallbackAiReviewClientTest {

  private static final ReviewInput INPUT = null; // 스텁은 입력을 보지 않는다

  private static ReviewResult result(String summary) {
    return new ReviewResult(summary, List.of());
  }

  private static final class Stub implements AiReviewClient {
    private final String name;
    private final RuntimeException failure;
    private final ReviewResult success;
    int calls;

    Stub(String name, RuntimeException failure, ReviewResult success) {
      this.name = name;
      this.failure = failure;
      this.success = success;
    }

    @Override public ReviewResult review(ReviewInput input) {
      calls++;
      if (failure != null) throw failure;
      return success;
    }

    @Override public String providerName() { return name; }
  }

  private static RestClientResponseException status(int code, String reason) {
    return new RestClientResponseException(reason, code, reason, new HttpHeaders(), null, null);
  }

  private ProviderLatch latch() {
    return new ProviderLatch(
        Clock.fixed(Instant.parse("2026-10-01T00:00:00Z"), ZoneOffset.UTC));
  }

  private FallbackAiReviewClient chain(ProviderLatch latch, Stub... stubs) {
    LinkedHashMap<String, AiReviewClient> delegates = new LinkedHashMap<>();
    for (Stub s : stubs) delegates.put(s.providerName().toLowerCase(Locale.ROOT), s);
    return new FallbackAiReviewClient(delegates, latch);
  }

  @Test
  void movesToTheNextProviderWhenThePrimaryFails() {
    ProviderLatch latch = latch();
    Stub claude = new Stub("claude", status(429, "Too Many Requests"), null);
    Stub ollama = new Stub("ollama", null, result("from ollama"));

    assertEquals("from ollama", chain(latch, claude, ollama).review(INPUT).summary());
    assertEquals(1, claude.calls);
    assertEquals(1, ollama.calls);
  }

  @Test
  void opensTheLatchOnAnAvailabilityFailure() {
    ProviderLatch latch = latch();
    chain(latch, new Stub("claude", status(429, "Too Many Requests"), null),
                 new Stub("ollama", null, result("ok"))).review(INPUT);

    assertTrue(latch.isOpen("review", "claude"));
  }

  @Test
  void skipsAProviderWhoseLatchIsOpenWithoutCallingIt() {
    ProviderLatch latch = latch();
    latch.recordFailure("review", "claude", FailureKind.AUTH, null);
    Stub claude = new Stub("claude", null, result("never"));

    assertEquals("from ollama",
        chain(latch, claude, new Stub("ollama", null, result("from ollama"))).review(INPUT)
            .summary());
    assertEquals(0, claude.calls);
  }

  @Test
  void doesNotOpenTheLatchOnAnOutputFailure() {
    ProviderLatch latch = latch();

    assertThrows(RuntimeException.class,
        () -> chain(latch, new Stub("claude", new IllegalStateException("schema mismatch"), null),
                           new Stub("ollama", new IllegalStateException("also bad"), null))
            .review(INPUT));

    assertFalse(latch.isOpen("review", "claude"));
    assertFalse(latch.isOpen("review", "ollama"));
  }

  @Test
  void throwsTheExistingReviewExceptionWhenEveryProviderIsBlocked() {
    // Review Focus 4: an all-open chain must surface review's own exception, not an index error.
    ProviderLatch latch = latch();
    latch.recordFailure("review", "claude", FailureKind.AUTH, null);
    latch.recordFailure("review", "ollama", FailureKind.AUTH, null);

    TransientReviewException thrown = assertThrows(TransientReviewException.class,
        () -> chain(latch, new Stub("claude", null, result("x")),
                           new Stub("ollama", null, result("y"))).review(INPUT));
    assertEquals("LLM_ALL_PROVIDERS_BLOCKED", thrown.errorCode());
  }

  @Test
  void propagatesTheLastFailureWhenEveryAttemptFailed() {
    ProviderLatch latch = latch();
    RuntimeException ollamaFailure = status(503, "Service Unavailable");

    RuntimeException thrown = assertThrows(RuntimeException.class,
        () -> chain(latch, new Stub("claude", status(429, "Too Many Requests"), null),
                           new Stub("ollama", ollamaFailure, null)).review(INPUT));
    assertSame(ollamaFailure, thrown);
  }

  @Test
  void closesTheLatchOnSuccess() {
    ProviderLatch latch = latch();
    latch.recordFailure("review", "ollama", FailureKind.TRANSIENT, null);
    latch.recordFailure("review", "ollama", FailureKind.TRANSIENT, null);

    chain(latch, new Stub("ollama", null, result("ok"))).review(INPUT);

    assertFalse(latch.isOpen("review", "ollama"));
  }

  @Test
  void reportsTheProviderThatActuallyServed() {
    ProviderLatch latch = latch();
    FallbackAiReviewClient client = chain(latch,
        new Stub("claude", status(429, "Too Many Requests"), null),
        new Stub("ollama", null, result("ok")));

    client.review(INPUT);

    assertEquals("ollama", client.providerName());
  }
}
```

- [ ] **Step 3: 실패를 확인한다**

Run: `cd D:/workspace/dpa/devpath-ai-svc && ./gradlew test --tests 'ai.devpath.aigw.review.FallbackAiReviewClientTest'`
Expected: 컴파일 실패 — `cannot find symbol: class FallbackAiReviewClient`

- [ ] **Step 4: `FallbackAiReviewClient` 를 쓴다**

`src/main/java/ai/devpath/aigw/review/FallbackAiReviewClient.java`:

```java
package ai.devpath.aigw.review;

import ai.devpath.aigw.provider.ProviderFailures;
import ai.devpath.aigw.provider.ProviderLatch;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 순서형 폴백 코드리뷰 클라이언트. 래치가 열린 provider 는 <b>호출하지 않고</b> 건너뛴다.
 *
 * <p>리뷰는 요청/응답이라 멘토의 「토큰 방출 뒤 전환 불가」 제약이 없다 — 실패하면 항상 다음으로 간다.
 * 체인이 전부 차단됐으면 review 의 기존 예외를 던진다(스펙 §4.1: mock 으로 떨어지지 않는다).
 */
public class FallbackAiReviewClient implements AiReviewClient {

  private static final String FEATURE = "review";

  private final LinkedHashMap<String, AiReviewClient> delegates;
  private final ProviderLatch latch;
  private final ThreadLocal<String> served = new ThreadLocal<>();

  public FallbackAiReviewClient(
      LinkedHashMap<String, AiReviewClient> delegates, ProviderLatch latch) {
    if (delegates == null || delegates.isEmpty()) {
      throw new IllegalArgumentException("delegates must not be empty");
    }
    this.delegates = new LinkedHashMap<>(delegates);
    this.latch = latch;
  }

  @Override
  public ReviewResult review(ReviewInput input) {
    RuntimeException last = null;
    for (Map.Entry<String, AiReviewClient> e : delegates.entrySet()) {
      String name = e.getKey();
      if (latch.isOpen(FEATURE, name)) continue;
      try {
        ReviewResult result = e.getValue().review(input);
        latch.recordSuccess(FEATURE, name);
        served.set(name);
        return result;
      } catch (RuntimeException ex) {
        ProviderFailures.Classified c = ProviderFailures.classify(ex);
        latch.recordFailure(FEATURE, name, c.kind(), c.retryAfter());
        last = ex;
      }
    }
    if (last != null) throw last;
    throw new TransientReviewException("LLM_ALL_PROVIDERS_BLOCKED",
        "모든 리뷰 provider 가 차단 상태입니다", null);
  }

  @Override
  public String providerName() {
    String s = served.get();
    return s != null ? s : delegates.keySet().iterator().next();
  }
}
```

- [ ] **Step 5: 통과를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.review.FallbackAiReviewClientTest'`
Expected: PASS (8 tests)

- [ ] **Step 6: `ReviewClientConfig` 를 쓰고 세 클라이언트의 애노테이션을 뗀다**

`src/main/java/ai/devpath/aigw/review/ReviewClientConfig.java`:

```java
package ai.devpath.aigw.review;

import ai.devpath.aigw.provider.ProviderChain;
import ai.devpath.aigw.provider.ProviderLatch;
import com.anthropic.client.AnthropicClient;
import java.time.Duration;
import java.util.LinkedHashMap;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import tools.jackson.databind.json.JsonMapper;

/**
 * 코드리뷰 클라이언트 단일 진입점 조립(멘토와 같은 방식). provider + devpath.review.fallback 을
 * 가용 provider 로 필터링해 체인을 만든다.
 *
 * <p><b>mock 은 체인에 넣지 않는다</b>(스펙 §4.1) — 가짜 리뷰가 사용자 기록에 영구히 남는 것은
 * 실패보다 나쁘다. provider=mock 일 때만 단독으로 쓴다(개발·CI).
 */
@Configuration
public class ReviewClientConfig {

  @Bean
  public AiReviewClient reviewClient(
      @Value("${devpath.review.provider:mock}") String provider,
      @Value("${devpath.review.fallback:}") String fallbackCsv,
      @Value("${devpath.ollama.base-url:http://localhost:11434}") String ollamaBaseUrl,
      @Value("${devpath.review.ollama-model:qwen2.5-coder:7b}") String ollamaModel,
      @Value("${devpath.review.ollama-timeout:PT60S}") Duration ollamaTimeout,
      @Value("${devpath.review.claude-model:claude-sonnet-4-6}") String claudeModel,
      ReviewPromptBuilder prompts, JsonMapper jsonMapper, ProviderLatch latch,
      @Qualifier("anthropicClient") ObjectProvider<AnthropicClient> anthropicClientProvider) {

    if ("mock".equals(provider == null ? null : provider.trim())) {
      return new MockAiReviewClient();
    }

    LinkedHashMap<String, AiReviewClient> available = new LinkedHashMap<>();
    available.put("ollama",
        new OllamaAiReviewClient(ollamaBaseUrl, ollamaModel, ollamaTimeout, prompts, jsonMapper));
    AnthropicClient anthropic = anthropicClientProvider.getIfAvailable();
    if (anthropic != null) {
      available.put("claude", new ClaudeAiReviewClient(anthropic, claudeModel, prompts));
    }

    LinkedHashMap<String, AiReviewClient> chain =
        ProviderChain.orderedMap(provider, fallbackCsv, available);
    if (chain.isEmpty()) {
      throw new IllegalStateException(
          "devpath.review.provider=" + provider + " 에 해당하는 가용 provider 가 없다");
    }
    return chain.size() == 1
        ? chain.values().iterator().next()
        : new FallbackAiReviewClient(chain, latch);
  }
}
```

`ClaudeAiReviewClient` · `OllamaAiReviewClient` · `MockAiReviewClient` 에서 다음을 삭제한다:
- `@Component` 애노테이션
- `@ConditionalOnProperty(name = "devpath.review.provider", havingValue = "...")` 애노테이션
- `import org.springframework.stereotype.Component;`
- `import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;`

`@Qualifier`·`@Value` 는 **남긴다** — 팩토리가 생성자를 직접 부르므로 무해하고 기본값이 문서 역할을 한다.

- [ ] **Step 7: 전체 스위트로 회귀를 확인한다**

Run: `./gradlew test`
Expected: PASS. 기존 테스트가 `@ConditionalOnProperty` 로 특정 구현만 올라오는 것에 의존하면 `devpath.review.provider` 를 명시해 같은 구현이 선택되게만 고친다 — **단언은 바꾸지 않는다.** `provider=mock` 인데 `ANTHROPIC_API_KEY` 가 설정된 컨텍스트에서 `AnthropicClient` 빈이 새로 등장할 수 있다(Task 4); 빈 개수를 단언하는 테스트가 깨지면 그 테스트의 키를 비운다.

- [ ] **Step 8: 커밋**

```bash
git add src/main/java/ai/devpath/aigw/provider/ProviderLatchConfig.java \
        src/main/java/ai/devpath/aigw/review/ \
        src/test/java/ai/devpath/aigw/review/
git commit -m "feat(review): assemble the review provider chain with latch-aware fallback"
```

---

## Task 6: community-seed 배선

**Files:**
- Create: `src/main/java/ai/devpath/aigw/community/FallbackAiSeedClient.java`
- Create: `src/main/java/ai/devpath/aigw/community/CommunitySeedClientConfig.java`
- Create: `src/test/java/ai/devpath/aigw/community/FallbackAiSeedClientTest.java`
- Modify: `src/main/java/ai/devpath/aigw/community/ClaudeSeedClient.java` · `OllamaSeedClient.java` · `MockSeedClient.java` (애노테이션·import 제거)

**Interfaces:**
- Consumes: `ProviderChain.orderedMap` · `ProviderLatch` 빈 (Task 5) · `ProviderFailures.classify` · 빈 `communitySeedAnthropicClient`
- Produces: `FallbackAiSeedClient(LinkedHashMap<String, AiSeedClient>, ProviderLatch)` · 빈 `AiSeedClient seedClient(...)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

먼저 `src/main/java/ai/devpath/aigw/community/SeedAnswer.java` 를 읽어 생성자와 접근자 이름을 확인하고, 아래의 `new SeedAnswer(answer)` · `.text()` 를 실제 모양에 맞춘다.

`src/test/java/ai/devpath/aigw/community/FallbackAiSeedClientTest.java`:

```java
package ai.devpath.aigw.community;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.devpath.aigw.provider.FailureKind;
import ai.devpath.aigw.provider.ProviderLatch;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.Locale;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.web.client.RestClientResponseException;

class FallbackAiSeedClientTest {

  private static final SeedInput INPUT = null;

  private static final class Stub implements AiSeedClient {
    private final String name;
    private final RuntimeException failure;
    private final String answer;
    int calls;

    Stub(String name, RuntimeException failure, String answer) {
      this.name = name;
      this.failure = failure;
      this.answer = answer;
    }

    @Override public SeedAnswer generate(SeedInput input) {
      calls++;
      if (failure != null) throw failure;
      return new SeedAnswer(answer);
    }

    @Override public String providerName() { return name; }
  }

  private static RestClientResponseException status(int code, String reason) {
    return new RestClientResponseException(reason, code, reason, new HttpHeaders(), null, null);
  }

  private ProviderLatch latch() {
    return new ProviderLatch(
        Clock.fixed(Instant.parse("2026-10-01T00:00:00Z"), ZoneOffset.UTC));
  }

  private FallbackAiSeedClient chain(ProviderLatch latch, Stub... stubs) {
    LinkedHashMap<String, AiSeedClient> delegates = new LinkedHashMap<>();
    for (Stub s : stubs) delegates.put(s.providerName().toLowerCase(Locale.ROOT), s);
    return new FallbackAiSeedClient(delegates, latch);
  }

  @Test
  void movesToTheNextProviderWhenThePrimaryFails() {
    ProviderLatch latch = latch();
    Stub claude = new Stub("claude", status(401, "Unauthorized"), null);

    assertEquals("from ollama",
        chain(latch, claude, new Stub("ollama", null, "from ollama")).generate(INPUT).text());
    assertEquals(1, claude.calls);
  }

  @Test
  void opensTheLatchOnAnAuthFailure() {
    ProviderLatch latch = latch();
    chain(latch, new Stub("claude", status(401, "Unauthorized"), null),
                 new Stub("ollama", null, "ok")).generate(INPUT);

    assertTrue(latch.isOpen("community-seed", "claude"));
  }

  @Test
  void skipsAProviderWhoseLatchIsOpenWithoutCallingIt() {
    ProviderLatch latch = latch();
    latch.recordFailure("community-seed", "claude", FailureKind.AUTH, null);
    Stub claude = new Stub("claude", null, "never");

    assertEquals("from ollama",
        chain(latch, claude, new Stub("ollama", null, "from ollama")).generate(INPUT).text());
    assertEquals(0, claude.calls);
  }

  @Test
  void doesNotOpenTheLatchOnAnOutputFailure() {
    ProviderLatch latch = latch();

    assertThrows(RuntimeException.class,
        () -> chain(latch, new Stub("claude", new IllegalStateException("blank"), null))
            .generate(INPUT));

    assertFalse(latch.isOpen("community-seed", "claude"));
  }

  @Test
  void throwsTheExistingSeedExceptionWhenEveryProviderIsBlocked() {
    ProviderLatch latch = latch();
    latch.recordFailure("community-seed", "claude", FailureKind.AUTH, null);
    latch.recordFailure("community-seed", "ollama", FailureKind.AUTH, null);

    SeedGenerationException thrown = assertThrows(SeedGenerationException.class,
        () -> chain(latch, new Stub("claude", null, "x"), new Stub("ollama", null, "y"))
            .generate(INPUT));
    assertEquals("LLM_ALL_PROVIDERS_BLOCKED", thrown.errorCode());
  }

  @Test
  void reportsTheProviderThatActuallyServed() {
    ProviderLatch latch = latch();
    FallbackAiSeedClient client = chain(latch,
        new Stub("claude", status(401, "Unauthorized"), null), new Stub("ollama", null, "ok"));

    client.generate(INPUT);

    assertEquals("ollama", client.providerName());
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.community.FallbackAiSeedClientTest'`
Expected: 컴파일 실패 — `cannot find symbol: class FallbackAiSeedClient`

- [ ] **Step 3: `FallbackAiSeedClient` 를 쓴다**

`src/main/java/ai/devpath/aigw/community/FallbackAiSeedClient.java`:

```java
package ai.devpath.aigw.community;

import ai.devpath.aigw.provider.ProviderFailures;
import ai.devpath.aigw.provider.ProviderLatch;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 순서형 폴백 커뮤니티 시드 클라이언트. 래치가 열린 provider 는 호출하지 않고 건너뛴다.
 *
 * <p>시드 답변은 저장되고 공개되므로 어느 provider 가 만들었는지 {@link #providerName()} 으로
 * 기록된다. 체인이 전부 차단됐으면 mock 으로 떨어지지 않고 기존 예외를 던진다(스펙 §4.1).
 */
public class FallbackAiSeedClient implements AiSeedClient {

  private static final String FEATURE = "community-seed";

  private final LinkedHashMap<String, AiSeedClient> delegates;
  private final ProviderLatch latch;
  private final ThreadLocal<String> served = new ThreadLocal<>();

  public FallbackAiSeedClient(
      LinkedHashMap<String, AiSeedClient> delegates, ProviderLatch latch) {
    if (delegates == null || delegates.isEmpty()) {
      throw new IllegalArgumentException("delegates must not be empty");
    }
    this.delegates = new LinkedHashMap<>(delegates);
    this.latch = latch;
  }

  @Override
  public SeedAnswer generate(SeedInput input) {
    RuntimeException last = null;
    for (Map.Entry<String, AiSeedClient> e : delegates.entrySet()) {
      String name = e.getKey();
      if (latch.isOpen(FEATURE, name)) continue;
      try {
        SeedAnswer answer = e.getValue().generate(input);
        latch.recordSuccess(FEATURE, name);
        served.set(name);
        return answer;
      } catch (RuntimeException ex) {
        ProviderFailures.Classified c = ProviderFailures.classify(ex);
        latch.recordFailure(FEATURE, name, c.kind(), c.retryAfter());
        last = ex;
      }
    }
    if (last != null) throw last;
    throw new SeedGenerationException("LLM_ALL_PROVIDERS_BLOCKED",
        "모든 시드 provider 가 차단 상태입니다", null);
  }

  @Override
  public String providerName() {
    String s = served.get();
    return s != null ? s : delegates.keySet().iterator().next();
  }
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.community.FallbackAiSeedClientTest'`
Expected: PASS (6 tests)

- [ ] **Step 5: `CommunitySeedClientConfig` 를 쓰고 세 클라이언트의 애노테이션을 뗀다**

`src/main/java/ai/devpath/aigw/community/CommunitySeedClientConfig.java`:

```java
package ai.devpath.aigw.community;

import ai.devpath.aigw.provider.ProviderChain;
import ai.devpath.aigw.provider.ProviderLatch;
import com.anthropic.client.AnthropicClient;
import java.time.Duration;
import java.util.LinkedHashMap;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import tools.jackson.databind.json.JsonMapper;

/**
 * 커뮤니티 시드 클라이언트 단일 진입점 조립. <b>mock 은 체인에 넣지 않는다</b>(스펙 §4.1) —
 * 가짜 답변이 공개 커뮤니티에 남는 것은 실패보다 나쁘다.
 */
@Configuration
public class CommunitySeedClientConfig {

  @Bean
  public AiSeedClient seedClient(
      @Value("${devpath.community-seed.provider:mock}") String provider,
      @Value("${devpath.community-seed.fallback:}") String fallbackCsv,
      @Value("${devpath.ollama.base-url:http://localhost:11434}") String ollamaBaseUrl,
      @Value("${devpath.community-seed.ollama-model:qwen2.5:7b}") String ollamaModel,
      @Value("${devpath.community-seed.ollama-timeout:PT60S}") Duration ollamaTimeout,
      @Value("${devpath.community-seed.claude-model:claude-haiku-4-5}") String claudeModel,
      SeedPromptBuilder prompts, JsonMapper jsonMapper, ProviderLatch latch,
      @Qualifier("communitySeedAnthropicClient")
      ObjectProvider<AnthropicClient> anthropicClientProvider) {

    if ("mock".equals(provider == null ? null : provider.trim())) {
      return new MockSeedClient();
    }

    LinkedHashMap<String, AiSeedClient> available = new LinkedHashMap<>();
    available.put("ollama",
        new OllamaSeedClient(ollamaBaseUrl, ollamaModel, ollamaTimeout, prompts, jsonMapper));
    AnthropicClient anthropic = anthropicClientProvider.getIfAvailable();
    if (anthropic != null) {
      available.put("claude", new ClaudeSeedClient(anthropic, claudeModel, prompts));
    }

    LinkedHashMap<String, AiSeedClient> chain =
        ProviderChain.orderedMap(provider, fallbackCsv, available);
    if (chain.isEmpty()) {
      throw new IllegalStateException(
          "devpath.community-seed.provider=" + provider + " 에 해당하는 가용 provider 가 없다");
    }
    return chain.size() == 1
        ? chain.values().iterator().next()
        : new FallbackAiSeedClient(chain, latch);
  }
}
```

`ClaudeSeedClient` · `OllamaSeedClient` · `MockSeedClient` 에서 `@Component` · `@ConditionalOnProperty` 애노테이션과 그 두 import 를 삭제한다.

- [ ] **Step 6: 전체 스위트**

Run: `./gradlew test`
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add src/main/java/ai/devpath/aigw/community/ src/test/java/ai/devpath/aigw/community/
git commit -m "feat(community-seed): assemble the seed provider chain with latch-aware fallback"
```

---

## Task 7: retention — **유일한 신규 구현**(Ollama 클라이언트) + 배선

**Files:**
- Create: `src/main/java/ai/devpath/aigw/retention/OllamaReEngagementClient.java`
- Create: `src/main/java/ai/devpath/aigw/retention/FallbackReEngagementClient.java`
- Create: `src/main/java/ai/devpath/aigw/retention/ReEngagementClientConfig.java`
- Create: `src/test/java/ai/devpath/aigw/retention/OllamaReEngagementClientTest.java`
- Create: `src/test/java/ai/devpath/aigw/retention/FallbackReEngagementClientTest.java`
- Modify: `src/main/java/ai/devpath/aigw/retention/ClaudeReEngagementClient.java` · `MockReEngagementClient.java` (애노테이션·import 제거)

**★이 패키지는 탭 들여쓰기다.** 아래 코드 블록의 들여쓰기를 그대로 쓴다.

**Interfaces:**
- Consumes: `ProviderChain.orderedMap` · `ProviderLatch` 빈 · `ProviderFailures.classify` · 빈 `retentionAnthropicClient` · 기존 `ReEngagementPromptBuilder`
- Produces:
  - `OllamaReEngagementClient(String baseUrl, String model, Duration timeout, ReEngagementPromptBuilder prompts)` — `suggest(ReEngagementInput)` 가 문구 문자열을 돌려준다
  - `FallbackReEngagementClient(LinkedHashMap<String, ReEngagementSuggestionClient>, ProviderLatch)`
  - 빈 `ReEngagementSuggestionClient reEngagementClient(...)`

**실측 근거:** `ReEngagementSuggestionClient.suggest(ReEngagementInput)` 는 `String` 을 돌려준다. `ReEngagementGenerationException` 의 생성자는 **`(String message, Throwable cause)` 로 errorCode 가 없다**(review·seed 와 다르다). Ollama 호출 패턴은 `OllamaSeedClient.generate` 를 본보기로 한다(`/api/chat` · `stream:false` · `message.content`).

- [ ] **Step 1: 실패하는 테스트를 쓴다 (Ollama 클라이언트)**

먼저 `src/main/java/ai/devpath/aigw/retention/ReEngagementPromptBuilder.java` 를 읽어 메서드 이름을 확인한다(`systemPrompt()` · `userContent(input)` 가 아니면 아래를 그 이름으로 맞춘다).

`src/test/java/ai/devpath/aigw/retention/OllamaReEngagementClientTest.java`:

```java
package ai.devpath.aigw.retention;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Duration;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import okhttp3.mockwebserver.RecordedRequest;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class OllamaReEngagementClientTest {

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

	private OllamaReEngagementClient client() {
		return new OllamaReEngagementClient(
				server.url("/").toString(), "qwen2.5:7b", Duration.ofSeconds(5),
				new ReEngagementPromptBuilder());
	}

	@Test
	void postsToTheChatRouteWithStreamingOff() throws Exception {
		server.enqueue(new MockResponse()
				.setHeader("Content-Type", "application/json")
				.setBody("{\"message\":{\"content\":\"다시 시작해 볼까요?\"}}"));

		String out = client().suggest(null);

		RecordedRequest request = server.takeRequest();
		assertEquals("POST", request.getMethod());
		assertEquals("/api/chat", request.getPath());
		String body = request.getBody().readUtf8();
		assertTrue(body.contains("\"stream\":false"), body);
		assertTrue(body.contains("qwen2.5:7b"), body);
		assertEquals("다시 시작해 볼까요?", out);
	}

	@Test
	void reportsAnEmptyAnswerAsAGenerationFailure() {
		server.enqueue(new MockResponse()
				.setHeader("Content-Type", "application/json")
				.setBody("{\"message\":{\"content\":\"   \"}}"));

		assertThrows(ReEngagementGenerationException.class, () -> client().suggest(null));
	}

	@Test
	void letsAnHttpStatusFailureThroughSoTheLatchCanClassifyIt() {
		// 상태코드를 ReEngagementGenerationException 으로 감싸면 ProviderFailures 가 429 를 못 본다.
		server.enqueue(new MockResponse().setResponseCode(429));

		assertThrows(org.springframework.web.client.RestClientResponseException.class,
				() -> client().suggest(null));
	}

	@Test
	void namesItselfOllama() {
		assertEquals("OLLAMA", client().providerName());
	}
}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.retention.OllamaReEngagementClientTest'`
Expected: 컴파일 실패 — `cannot find symbol: class OllamaReEngagementClient`

- [ ] **Step 3: `OllamaReEngagementClient` 를 쓴다**

`src/main/java/ai/devpath/aigw/retention/OllamaReEngagementClient.java`:

```java
package ai.devpath.aigw.retention;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/**
 * 재참여 문구 생성(Ollama, /api/chat stream:false 자유 텍스트). 스펙 §1 이 지적한 <b>유일한 신규 구현</b>.
 *
 * <p>HTTP 상태 실패는 <b>감싸지 않고 그대로 올린다</b> — {@code ProviderFailures} 가 429·401 을 보고
 * 래치를 판정해야 한다. 응답이 비었을 때만 {@link ReEngagementGenerationException} 을 던진다.
 */
public class OllamaReEngagementClient implements ReEngagementSuggestionClient {

	private final RestClient restClient;
	private final String model;
	private final ReEngagementPromptBuilder prompts;

	public OllamaReEngagementClient(
			String baseUrl, String model, Duration timeout, ReEngagementPromptBuilder prompts) {
		var factory = new SimpleClientHttpRequestFactory();
		factory.setConnectTimeout(timeout);
		factory.setReadTimeout(timeout);
		this.restClient = RestClient.builder().baseUrl(baseUrl).requestFactory(factory).build();
		this.model = model;
		this.prompts = prompts;
	}

	@Override
	public String suggest(ReEngagementInput input) {
		Map<String, Object> body = new LinkedHashMap<>();
		body.put("model", model);
		body.put("messages", List.of(
				Map.of("role", "system", "content", prompts.systemPrompt()),
				Map.of("role", "user", "content", prompts.userContent(input))));
		body.put("stream", false);
		body.put("options", Map.of("temperature", 0.6));

		OllamaChatResponse response = restClient.post().uri("/api/chat").body(body)
				.retrieve().body(OllamaChatResponse.class);

		if (response == null || response.message() == null
				|| response.message().content() == null
				|| response.message().content().isBlank()) {
			throw new ReEngagementGenerationException("Ollama 재참여 문구 응답이 비어 있습니다", null);
		}
		return response.message().content().trim();
	}

	@Override
	public String providerName() { return "OLLAMA"; }

	private record OllamaChatResponse(OllamaMessage message) {}

	private record OllamaMessage(String content) {}
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.retention.OllamaReEngagementClientTest'`
Expected: PASS (4 tests). `prompts.systemPrompt()`·`userContent(input)` 이름이 다르면 Step 1 의 실측대로 고친다.

- [ ] **Step 5: 폴백 테스트를 쓰고 실패를 확인한다**

`src/test/java/ai/devpath/aigw/retention/FallbackReEngagementClientTest.java`:

```java
package ai.devpath.aigw.retention;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.devpath.aigw.provider.FailureKind;
import ai.devpath.aigw.provider.ProviderLatch;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.Locale;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.web.client.RestClientResponseException;

class FallbackReEngagementClientTest {

	private static final class Stub implements ReEngagementSuggestionClient {
		private final String name;
		private final RuntimeException failure;
		private final String text;
		int calls;

		Stub(String name, RuntimeException failure, String text) {
			this.name = name;
			this.failure = failure;
			this.text = text;
		}

		@Override public String suggest(ReEngagementInput input) {
			calls++;
			if (failure != null) throw failure;
			return text;
		}

		@Override public String providerName() { return name; }
	}

	private static RestClientResponseException status(int code, String reason) {
		return new RestClientResponseException(reason, code, reason, new HttpHeaders(), null, null);
	}

	private ProviderLatch latch() {
		return new ProviderLatch(
				Clock.fixed(Instant.parse("2026-10-01T00:00:00Z"), ZoneOffset.UTC));
	}

	private FallbackReEngagementClient chain(ProviderLatch latch, Stub... stubs) {
		LinkedHashMap<String, ReEngagementSuggestionClient> delegates = new LinkedHashMap<>();
		for (Stub s : stubs) delegates.put(s.providerName().toLowerCase(Locale.ROOT), s);
		return new FallbackReEngagementClient(delegates, latch);
	}

	@Test
	void movesToTheNextProviderWhenThePrimaryFails() {
		ProviderLatch latch = latch();
		Stub claude = new Stub("claude", status(429, "Too Many Requests"), null);

		assertEquals("from ollama",
				chain(latch, claude, new Stub("ollama", null, "from ollama")).suggest(null));
		assertEquals(1, claude.calls);
		assertTrue(latch.isOpen("retention", "claude"));
	}

	@Test
	void skipsAProviderWhoseLatchIsOpenWithoutCallingIt() {
		ProviderLatch latch = latch();
		latch.recordFailure("retention", "claude", FailureKind.AUTH, null);
		Stub claude = new Stub("claude", null, "never");

		assertEquals("from ollama",
				chain(latch, claude, new Stub("ollama", null, "from ollama")).suggest(null));
		assertEquals(0, claude.calls);
	}

	@Test
	void doesNotOpenTheLatchOnAnOutputFailure() {
		ProviderLatch latch = latch();

		assertThrows(RuntimeException.class,
				() -> chain(latch,
						new Stub("claude", new ReEngagementGenerationException("blank", null), null))
						.suggest(null));

		assertFalse(latch.isOpen("retention", "claude"));
	}

	@Test
	void throwsTheExistingRetentionExceptionWhenEveryProviderIsBlocked() {
		ProviderLatch latch = latch();
		latch.recordFailure("retention", "claude", FailureKind.AUTH, null);
		latch.recordFailure("retention", "ollama", FailureKind.AUTH, null);

		assertThrows(ReEngagementGenerationException.class,
				() -> chain(latch, new Stub("claude", null, "x"), new Stub("ollama", null, "y"))
						.suggest(null));
	}

	@Test
	void reportsTheProviderThatActuallyServed() {
		ProviderLatch latch = latch();
		FallbackReEngagementClient client = chain(latch,
				new Stub("claude", status(429, "Too Many Requests"), null),
				new Stub("ollama", null, "ok"));

		client.suggest(null);

		assertEquals("ollama", client.providerName());
	}
}
```

Run: `./gradlew test --tests 'ai.devpath.aigw.retention.FallbackReEngagementClientTest'`
Expected: 컴파일 실패 — `cannot find symbol: class FallbackReEngagementClient`

- [ ] **Step 6: `FallbackReEngagementClient` 를 쓴다**

`src/main/java/ai/devpath/aigw/retention/FallbackReEngagementClient.java`:

```java
package ai.devpath.aigw.retention;

import ai.devpath.aigw.provider.ProviderFailures;
import ai.devpath.aigw.provider.ProviderLatch;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 순서형 폴백 재참여 문구 클라이언트. 래치가 열린 provider 는 호출하지 않고 건너뛴다.
 *
 * <p>문구는 일회성이라 즉시 이어받는다. 체인이 전부 차단됐으면 mock 으로 떨어지지 않고
 * 기존 예외를 던진다(스펙 §4.1 — 가짜 문구가 알림으로 발송되는 것은 실패보다 나쁘다).
 */
public class FallbackReEngagementClient implements ReEngagementSuggestionClient {

	private static final String FEATURE = "retention";

	private final LinkedHashMap<String, ReEngagementSuggestionClient> delegates;
	private final ProviderLatch latch;
	private final ThreadLocal<String> served = new ThreadLocal<>();

	public FallbackReEngagementClient(
			LinkedHashMap<String, ReEngagementSuggestionClient> delegates, ProviderLatch latch) {
		if (delegates == null || delegates.isEmpty()) {
			throw new IllegalArgumentException("delegates must not be empty");
		}
		this.delegates = new LinkedHashMap<>(delegates);
		this.latch = latch;
	}

	@Override
	public String suggest(ReEngagementInput input) {
		RuntimeException last = null;
		for (Map.Entry<String, ReEngagementSuggestionClient> e : delegates.entrySet()) {
			String name = e.getKey();
			if (latch.isOpen(FEATURE, name)) continue;
			try {
				String text = e.getValue().suggest(input);
				latch.recordSuccess(FEATURE, name);
				served.set(name);
				return text;
			} catch (RuntimeException ex) {
				ProviderFailures.Classified c = ProviderFailures.classify(ex);
				latch.recordFailure(FEATURE, name, c.kind(), c.retryAfter());
				last = ex;
			}
		}
		if (last != null) throw last;
		throw new ReEngagementGenerationException("모든 재참여 provider 가 차단 상태입니다", null);
	}

	@Override
	public String providerName() {
		String s = served.get();
		return s != null ? s : delegates.keySet().iterator().next();
	}
}
```

- [ ] **Step 7: 통과를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.retention.FallbackReEngagementClientTest'`
Expected: PASS (5 tests)

- [ ] **Step 8: `ReEngagementClientConfig` 를 쓰고 두 클라이언트의 애노테이션을 뗀다**

`src/main/java/ai/devpath/aigw/retention/ReEngagementClientConfig.java`:

```java
package ai.devpath.aigw.retention;

import ai.devpath.aigw.provider.ProviderChain;
import ai.devpath.aigw.provider.ProviderLatch;
import com.anthropic.client.AnthropicClient;
import java.time.Duration;
import java.util.LinkedHashMap;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 재참여 문구 클라이언트 단일 진입점 조립. <b>mock 은 체인에 넣지 않는다</b>(스펙 §4.1) —
 * 가짜 문구가 알림으로 발송되는 것은 실패보다 나쁘다.
 */
@Configuration
public class ReEngagementClientConfig {

	@Bean
	public ReEngagementSuggestionClient reEngagementClient(
			@Value("${devpath.retention.provider:mock}") String provider,
			@Value("${devpath.retention.fallback:}") String fallbackCsv,
			@Value("${devpath.ollama.base-url:http://localhost:11434}") String ollamaBaseUrl,
			@Value("${devpath.retention.ollama-model:qwen2.5:7b}") String ollamaModel,
			@Value("${devpath.retention.ollama-timeout:PT60S}") Duration ollamaTimeout,
			@Value("${devpath.retention.claude-model:claude-sonnet-4-6}") String claudeModel,
			ReEngagementPromptBuilder prompts, ProviderLatch latch,
			@Qualifier("retentionAnthropicClient")
			ObjectProvider<AnthropicClient> anthropicClientProvider) {

		if ("mock".equals(provider == null ? null : provider.trim())) {
			return new MockReEngagementClient();
		}

		LinkedHashMap<String, ReEngagementSuggestionClient> available = new LinkedHashMap<>();
		available.put("ollama",
				new OllamaReEngagementClient(ollamaBaseUrl, ollamaModel, ollamaTimeout, prompts));
		AnthropicClient anthropic = anthropicClientProvider.getIfAvailable();
		if (anthropic != null) {
			available.put("claude",
					new ClaudeReEngagementClient(anthropic, claudeModel, prompts));
		}

		LinkedHashMap<String, ReEngagementSuggestionClient> chain =
				ProviderChain.orderedMap(provider, fallbackCsv, available);
		if (chain.isEmpty()) {
			throw new IllegalStateException(
					"devpath.retention.provider=" + provider + " 에 해당하는 가용 provider 가 없다");
		}
		return chain.size() == 1
				? chain.values().iterator().next()
				: new FallbackReEngagementClient(chain, latch);
	}
}
```

`ClaudeReEngagementClient` · `MockReEngagementClient` 에서 `@Component` · `@ConditionalOnProperty` 애노테이션과 그 두 import 를 삭제한다.

- [ ] **Step 9: 전체 스위트**

Run: `./gradlew test`
Expected: PASS

- [ ] **Step 10: 커밋**

```bash
git add src/main/java/ai/devpath/aigw/retention/ src/test/java/ai/devpath/aigw/retention/
git commit -m "feat(retention): add the Ollama suggestion client and assemble its provider chain"
```

---

## Task 8: 복구 탐색 배경 작업 + `application.yml` 폴백 키

**Files:**
- Create: `src/main/java/ai/devpath/aigw/provider/ProviderProbe.java`
- Create: `src/main/java/ai/devpath/aigw/provider/ProviderProbeScheduler.java`
- Create: `src/test/java/ai/devpath/aigw/provider/ProviderProbeSchedulerTest.java`
- Modify: `src/main/resources/application.yml` (`fallback:` 키 3개 + `probe` 설정)

**Interfaces:**
- Consumes: `ProviderLatch.dueProbes()` · `ProviderLatch.recordSuccess/recordFailure` (Task 2) · `ProviderFailures.classify` (Task 3)
- Produces:
  - `interface ProviderProbe { String feature(); String provider(); void ping(); }`
  - `ProviderProbeScheduler(ProviderLatch latch, List<ProviderProbe> probes)` · `void runDueProbes()`

**왜 배경인가(스펙 §3.1):** 사용자 요청으로 half-open 탐색을 하면 실패할 때 그 사용자가 지연을 문다. 최소 프롬프트의 크레딧 비용은 무시할 수준이고, 크레딧이 소진된 상태라면 즉시 429 로 떨어져 비용이 아예 없다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/aigw/provider/ProviderProbeSchedulerTest.java`:

```java
package ai.devpath.aigw.provider;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.web.client.RestClientResponseException;

class ProviderProbeSchedulerTest {

  private static final class MovableClock extends Clock {
    private Instant now = Instant.parse("2026-10-01T00:00:00Z");

    void advance(Duration d) { now = now.plus(d); }

    @Override public ZoneOffset getZone() { return ZoneOffset.UTC; }
    @Override public Clock withZone(ZoneId zone) { return this; }
    @Override public Instant instant() { return now; }
  }

  private static final class StubProbe implements ProviderProbe {
    private final String feature;
    private final String provider;
    private RuntimeException failure;
    int pings;

    StubProbe(String feature, String provider, RuntimeException failure) {
      this.feature = feature;
      this.provider = provider;
      this.failure = failure;
    }

    @Override public String feature() { return feature; }
    @Override public String provider() { return provider; }
    @Override public void ping() {
      pings++;
      if (failure != null) throw failure;
    }
  }

  @Test
  void doesNotPingWhileTheDeadlineHasNotPassed() {
    MovableClock clock = new MovableClock();
    ProviderLatch latch = new ProviderLatch(clock);
    latch.recordFailure("review", "claude", FailureKind.AUTH, null);
    StubProbe probe = new StubProbe("review", "claude", null);

    new ProviderProbeScheduler(latch, List.of(probe)).runDueProbes();

    assertEquals(0, probe.pings);
    assertTrue(latch.isOpen("review", "claude"));
  }

  @Test
  void closesTheLatchWhenTheProbeSucceeds() {
    MovableClock clock = new MovableClock();
    ProviderLatch latch = new ProviderLatch(clock);
    latch.recordFailure("review", "claude", FailureKind.AUTH, null);
    StubProbe probe = new StubProbe("review", "claude", null);
    clock.advance(Duration.ofMinutes(31));

    new ProviderProbeScheduler(latch, List.of(probe)).runDueProbes();

    assertEquals(1, probe.pings);
    assertFalse(latch.isOpen("review", "claude"));
  }

  @Test
  void extendsTheDeadlineWhenTheProbeStillFails() {
    MovableClock clock = new MovableClock();
    ProviderLatch latch = new ProviderLatch(clock);
    latch.recordFailure("review", "claude", FailureKind.RATE_LIMIT, null); // 5분
    clock.advance(Duration.ofMinutes(6));
    StubProbe probe = new StubProbe("review", "claude",
        new RestClientResponseException("429", 429, "Too Many Requests",
            new HttpHeaders(), null, null));

    new ProviderProbeScheduler(latch, List.of(probe)).runDueProbes();

    assertEquals(1, probe.pings);
    assertTrue(latch.isOpen("review", "claude"));   // 10분으로 늘었다
    clock.advance(Duration.ofMinutes(11));
    assertFalse(latch.isOpen("review", "claude"));
  }

  @Test
  void ignoresADueEntryThatHasNoRegisteredProbe() {
    MovableClock clock = new MovableClock();
    ProviderLatch latch = new ProviderLatch(clock);
    latch.recordFailure("community-seed", "claude", FailureKind.AUTH, null);
    clock.advance(Duration.ofMinutes(31));

    // review 용 probe 만 등록돼 있다 — 예외 없이 그냥 건너뛴다.
    new ProviderProbeScheduler(latch, List.of(new StubProbe("review", "claude", null)))
        .runDueProbes();

    assertFalse(latch.isOpen("community-seed", "claude")); // 기한이 지나 이미 닫힌 상태
  }

  @Test
  void oneFailingProbeDoesNotStopTheOthers() {
    MovableClock clock = new MovableClock();
    ProviderLatch latch = new ProviderLatch(clock);
    latch.recordFailure("review", "claude", FailureKind.AUTH, null);
    latch.recordFailure("retention", "claude", FailureKind.AUTH, null);
    clock.advance(Duration.ofMinutes(31));

    StubProbe failing = new StubProbe("review", "claude", new IllegalStateException("boom"));
    StubProbe healthy = new StubProbe("retention", "claude", null);

    new ProviderProbeScheduler(latch, List.of(failing, healthy)).runDueProbes();

    assertEquals(1, failing.pings);
    assertEquals(1, healthy.pings);
    assertFalse(latch.isOpen("retention", "claude"));
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.provider.ProviderProbeSchedulerTest'`
Expected: 컴파일 실패 — `cannot find symbol: class ProviderProbe`

- [ ] **Step 3: `ProviderProbe` 를 쓴다**

`src/main/java/ai/devpath/aigw/provider/ProviderProbe.java`:

```java
package ai.devpath.aigw.provider;

/**
 * 한 {@code (feature, provider)} 의 복구 여부를 확인하는 최소 호출. 출력 1토큰 수준의
 * 최소 프롬프트를 쓴다 — 크레딧이 소진된 상태라면 즉시 429 로 떨어져 비용이 아예 없다.
 */
public interface ProviderProbe {

  String feature();

  String provider();

  /** 성공하면 조용히 반환하고, 실패하면 그 provider 의 예외를 그대로 던진다. */
  void ping();
}
```

- [ ] **Step 4: `ProviderProbeScheduler` 를 쓴다**

`src/main/java/ai/devpath/aigw/provider/ProviderProbeScheduler.java`:

```java
package ai.devpath.aigw.provider;

import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 기한이 지난 래치를 배경에서 탐색해 닫는다. <b>사용자 요청을 탐색에 쓰지 않는다</b>(스펙 §3.1) —
 * half-open 탐색을 사용자 요청으로 하면 실패할 때 그 사용자가 지연을 문다.
 */
@Component
public class ProviderProbeScheduler {

  private static final Logger log = LoggerFactory.getLogger(ProviderProbeScheduler.class);

  private final ProviderLatch latch;
  private final List<ProviderProbe> probes;

  public ProviderProbeScheduler(ProviderLatch latch, List<ProviderProbe> probes) {
    this.latch = latch;
    this.probes = List.copyOf(probes);
  }

  @Scheduled(fixedDelayString = "${devpath.provider.probe-interval:PT1M}")
  public void runDueProbes() {
    for (ProviderLatch.Probe due : latch.dueProbes()) {
      ProviderProbe probe = find(due);
      if (probe == null) continue;
      try {
        probe.ping();
        latch.recordSuccess(due.feature(), due.provider());
        log.info("provider latch closed by probe: feature={} provider={}",
            due.feature(), due.provider());
      } catch (RuntimeException e) {
        ProviderFailures.Classified c = ProviderFailures.classify(e);
        latch.recordFailure(due.feature(), due.provider(), c.kind(), c.retryAfter());
        log.info("provider latch stays open: feature={} provider={} kind={} reason={}",
            due.feature(), due.provider(), c.kind(), e.toString());
      }
    }
  }

  private ProviderProbe find(ProviderLatch.Probe due) {
    for (ProviderProbe p : probes) {
      if (p.feature().equals(due.feature()) && p.provider().equals(due.provider())) return p;
    }
    return null;
  }
}
```

**주의:** `@Scheduled` 가 동작하려면 `@EnableScheduling` 이 필요하다. `src/main/java/ai/devpath/aigw/AiApplication.java` 또는 기존 설정에 이미 있는지 확인하고, 없으면 `ProviderLatchConfig` 에 `@EnableScheduling` 을 붙인다. **이미 있으면 중복으로 붙이지 않는다.**

- [ ] **Step 5: 통과를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.provider.ProviderProbeSchedulerTest'`
Expected: PASS (5 tests)

- [ ] **Step 6: `application.yml` 에 폴백 키를 추가한다**

`src/main/resources/application.yml` 에서 각 블록에 한 줄씩 넣는다. **기본값은 빈 문자열 — 설정하지 않으면 현재 동작과 완전히 같다.**

`devpath.review:` 블록의 `provider:` 바로 아래:
```yaml
    fallback: ${REVIEW_FALLBACK:}
```

`devpath.community-seed:` 블록의 `provider:` 바로 아래:
```yaml
    fallback: ${COMMUNITY_SEED_FALLBACK:}
```

`devpath.retention:` 블록의 `provider:` 바로 아래:
```yaml
    fallback: ${RETENTION_FALLBACK:}
    ollama-model: ${RETENTION_OLLAMA_MODEL:qwen2.5:7b}
```

`devpath:` 아래에 새 블록을 추가한다:
```yaml
  provider:
    # 기한이 지난 래치를 배경에서 탐색하는 주기. 사용자 요청은 탐색에 쓰지 않는다(스펙 §3.1).
    probe-interval: ${PROVIDER_PROBE_INTERVAL:PT1M}
```

**gitops 를 건드리지 않는다** — `*_FALLBACK` env 를 gitops 에 넣으면 `ai_release_eval_config.rendered_config_sha256` 이 바뀌어 release id 재발급을 부른다(스펙 §8). 모델이 확보된 뒤 별도 작업으로 넣는다.

- [ ] **Step 7: 기본값이 현재 동작을 바꾸지 않음을 확인한다**

Run: `./gradlew test`
Expected: PASS — 전체 스위트가 녹색이어야 한다. `*_FALLBACK` 을 주지 않았으므로 모든 체인 길이는 1이고, 각 기능은 `Fallback*Client` 로 감싸이지 않은 단일 클라이언트를 받는다.

- [ ] **Step 8: 커밋**

```bash
git add src/main/java/ai/devpath/aigw/provider/ src/test/java/ai/devpath/aigw/provider/ \
        src/main/resources/application.yml
git commit -m "feat(provider): probe blocked providers in the background and expose the fallback keys"
```

---

---

## Task 9: 회귀 잠금 — `mock` 은 세 체인에 들어가지 않는다

**Files:**
- Create: `src/test/java/ai/devpath/aigw/provider/MockExclusionTest.java`

**Interfaces:**
- Consumes: 빈 `AiReviewClient` (Task 5) · `AiSeedClient` (Task 6) · `ReEngagementSuggestionClient` (Task 7)
- Produces: 없음 (테스트 전용)

**왜:** 스펙 §4.1 이 명시적으로 요구한다. 가짜 코드 리뷰가 사용자 기록에 **영구히** 남거나 가짜 문구가 알림으로 **발송**되는 것은 실패보다 나쁘다. 설정 실수(`REVIEW_FALLBACK=mock`)로 그 일이 벌어지지 않도록 못박는다. 소스 텍스트가 아니라 **조립 결과**를 단언한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/aigw/provider/MockExclusionTest.java`:

```java
package ai.devpath.aigw.provider;

import static org.assertj.core.api.Assertions.assertThat;

import ai.devpath.aigw.community.AiSeedClient;
import ai.devpath.aigw.community.CommunitySeedClientConfig;
import ai.devpath.aigw.community.SeedPromptBuilder;
import ai.devpath.aigw.retention.ReEngagementClientConfig;
import ai.devpath.aigw.retention.ReEngagementPromptBuilder;
import ai.devpath.aigw.retention.ReEngagementSuggestionClient;
import ai.devpath.aigw.review.AiReviewClient;
import ai.devpath.aigw.review.ReviewClientConfig;
import ai.devpath.aigw.review.ReviewPromptBuilder;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import tools.jackson.databind.json.JsonMapper;

/**
 * 스펙 §4.1 회귀 잠금. {@code *_FALLBACK=mock} 을 설정해도 mock 이 체인에 들어가지 않아야 한다 —
 * 가짜 산출물이 저장·발송되는 것은 실패보다 나쁘다.
 */
class MockExclusionTest {

  /** ANTHROPIC_API_KEY 를 주지 않으므로 Claude 빈은 없고, 체인은 ollama 하나가 된다. */
  private ApplicationContextRunner runner() {
    return new ApplicationContextRunner()
        .withBean(ProviderLatch.class, () -> new ProviderLatch(java.time.Clock.systemUTC()))
        .withBean(JsonMapper.class, JsonMapper::new)
        .withBean(ReviewPromptBuilder.class, ReviewPromptBuilder::new)
        .withBean(SeedPromptBuilder.class, SeedPromptBuilder::new)
        .withBean(ReEngagementPromptBuilder.class, ReEngagementPromptBuilder::new)
        .withUserConfiguration(
            ReviewClientConfig.class, CommunitySeedClientConfig.class,
            ReEngagementClientConfig.class);
  }

  @Test
  void reviewIgnoresAMockFallback() {
    runner()
        .withPropertyValues("devpath.review.provider=ollama", "devpath.review.fallback=mock")
        .run(context -> assertThat(context.getBean(AiReviewClient.class).providerName())
            .isNotEqualTo("MOCK"));
  }

  @Test
  void communitySeedIgnoresAMockFallback() {
    runner()
        .withPropertyValues(
            "devpath.community-seed.provider=ollama", "devpath.community-seed.fallback=mock")
        .run(context -> assertThat(context.getBean(AiSeedClient.class).providerName())
            .isNotEqualTo("MOCK"));
  }

  @Test
  void retentionIgnoresAMockFallback() {
    runner()
        .withPropertyValues("devpath.retention.provider=ollama", "devpath.retention.fallback=mock")
        .run(context -> assertThat(
            context.getBean(ReEngagementSuggestionClient.class).providerName())
            .isNotEqualTo("MOCK"));
  }

  @Test
  void providerMockStillGivesTheMockClientOnItsOwn() {
    // mock 자체를 금지하는 것이 아니다 — 체인에 섞이는 것만 막는다. 개발·CI 는 provider=mock 을 쓴다.
    runner()
        .withPropertyValues(
            "devpath.review.provider=mock",
            "devpath.community-seed.provider=mock",
            "devpath.retention.provider=mock")
        .run(context -> {
          assertThat(context.getBean(AiReviewClient.class).providerName()).isEqualTo("MOCK");
          assertThat(context.getBean(AiSeedClient.class).providerName()).isEqualTo("MOCK");
          assertThat(context.getBean(ReEngagementSuggestionClient.class).providerName())
              .isEqualTo("MOCK");
        });
  }
}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd D:/workspace/dpa/devpath-ai-svc && ./gradlew test --tests 'ai.devpath.aigw.provider.MockExclusionTest'`
Expected: Task 5~7 이 끝난 상태라면 **PASS 해야 한다** — 이 테스트는 이미 구현된 계약을 못박는 회귀 잠금이다. **FAIL 하면 Task 5~7 의 `available` 맵에 `mock` 이 섞여 있다는 뜻이므로 그 설정을 고친다.**

`ReviewPromptBuilder`·`SeedPromptBuilder`·`ReEngagementPromptBuilder` 가 무인자 생성자가 아니면, 각 클래스를 읽어 `withBean(...)` 의 생성 람다를 실제 생성자에 맞춘다.

- [ ] **Step 3: 커밋**

```bash
git add src/test/java/ai/devpath/aigw/provider/MockExclusionTest.java
git commit -m "test(provider): lock mock out of the review, seed, and retention chains"
```

---

## Task 10: Claude 복구 탐색 구현체 3개

**Files:**
- Create: `src/main/java/ai/devpath/aigw/provider/ClaudeProviderProbe.java`
- Create: `src/main/java/ai/devpath/aigw/provider/ClaudeProbeConfig.java`
- Create: `src/test/java/ai/devpath/aigw/provider/ClaudeProviderProbeTest.java`

**Interfaces:**
- Consumes: `ProviderProbe` (Task 8) · 빈 `anthropicClient`·`communitySeedAnthropicClient`·`retentionAnthropicClient` (Task 4)
- Produces: `ProviderProbe` 빈 3개 (`review`/`community-seed`/`retention` × `claude`) — Task 8 의 `ProviderProbeScheduler` 가 `List<ProviderProbe>` 로 받는다

**왜 필수인가:** Task 8 은 인터페이스와 스케줄러만 만든다. 구현체가 없으면 `List<ProviderProbe>` 가 비어 스케줄러가 아무 래치도 닫지 못하고, **기한이 지난 뒤 첫 사용자 요청이 탐색을 대신 물게 된다** — 스펙 §3.1 이 금지한 바로 그 동작이다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`src/test/java/ai/devpath/aigw/provider/ClaudeProviderProbeTest.java`:

```java
package ai.devpath.aigw.provider;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.anthropic.client.AnthropicClient;
import com.anthropic.models.messages.MessageCreateParams;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

class ClaudeProviderProbeTest {

  @Test
  void reportsTheFeatureAndProviderItGuards() {
    ClaudeProviderProbe probe = new ClaudeProviderProbe(
        "review", Mockito.mock(AnthropicClient.class), "claude-sonnet-4-6");

    assertEquals("review", probe.feature());
    assertEquals("claude", probe.provider());
  }

  @Test
  void sendsTheSmallestPossibleRequest() {
    AnthropicClient client = Mockito.mock(AnthropicClient.class, Mockito.RETURNS_DEEP_STUBS);
    new ClaudeProviderProbe("review", client, "claude-sonnet-4-6").ping();

    org.mockito.ArgumentCaptor<MessageCreateParams> params =
        org.mockito.ArgumentCaptor.forClass(MessageCreateParams.class);
    Mockito.verify(client.messages()).create(params.capture());

    // 출력 1토큰 — 크레딧이 소진된 상태라면 즉시 429 로 떨어져 비용이 아예 없다.
    assertEquals(1L, params.getValue().maxTokens());
  }

  @Test
  void letsTheProviderFailureThroughSoTheSchedulerCanClassifyIt() {
    AnthropicClient client = Mockito.mock(AnthropicClient.class, Mockito.RETURNS_DEEP_STUBS);
    RuntimeException failure = new IllegalStateException("429");
    Mockito.when(client.messages().create(Mockito.any(MessageCreateParams.class)))
        .thenThrow(failure);

    RuntimeException thrown = assertThrows(RuntimeException.class,
        () -> new ClaudeProviderProbe("review", client, "claude-sonnet-4-6").ping());

    assertSame(failure, thrown);
  }
}
```

`MessageCreateParams` 의 `maxTokens()` 접근자 이름·타입이 다르면 Step 2 에서 실측해 단언을 맞춘다 — **「1토큰만 요청한다」는 의미는 바꾸지 않는다.** 깊은 스텁(`RETURNS_DEEP_STUBS`)으로 검증이 어려우면 `AnthropicClient` 를 감싼 작은 테스트용 구현으로 바꿔도 된다. `mockito` 가 테스트 의존성에 없으면 `build.gradle.kts` 의 `testImplementation` 에 `spring-boot-starter-test` 가 포함하는지 확인하고, 없으면 테스트용 수동 스텁으로 바꾼다(의존성을 새로 추가하지 않는다).

- [ ] **Step 2: 실패를 확인하고 SDK 접근자를 실측한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.provider.ClaudeProviderProbeTest'`
Expected: 컴파일 실패 — `cannot find symbol: class ClaudeProviderProbe`

이 때 `ClaudeReEngagementClient.suggest` 의 `MessageCreateParams.builder()` 사용부를 읽어 **실제 빌더 메서드 이름**(`maxTokens` · `model` · `addUserMessage` 등)을 확인하고 Step 3 의 코드를 맞춘다. **추측하지 않는다.**

- [ ] **Step 3: `ClaudeProviderProbe` 를 쓴다**

`src/main/java/ai/devpath/aigw/provider/ClaudeProviderProbe.java`:

```java
package ai.devpath.aigw.provider;

import com.anthropic.client.AnthropicClient;
import com.anthropic.models.messages.MessageCreateParams;

/**
 * Claude 가 다시 쓸 수 있는지 확인하는 최소 호출. 출력 1토큰만 요청한다 — 크레딧이 소진된 상태라면
 * 즉시 429 로 떨어져 비용이 아예 없고, 회수된 키라면 401 로 떨어진다.
 *
 * <p>예외를 <b>감싸지 않는다</b>: {@link ProviderProbeScheduler} 가 {@link ProviderFailures} 로
 * 분류해 래치 기한을 늘려야 한다.
 */
public class ClaudeProviderProbe implements ProviderProbe {

  private final String feature;
  private final AnthropicClient client;
  private final String model;

  public ClaudeProviderProbe(String feature, AnthropicClient client, String model) {
    this.feature = feature;
    this.client = client;
    this.model = model;
  }

  @Override
  public String feature() { return feature; }

  @Override
  public String provider() { return "claude"; }

  @Override
  public void ping() {
    client.messages().create(MessageCreateParams.builder()
        .model(model)
        .maxTokens(1L)
        .addUserMessage("ping")
        .build());
  }
}
```

- [ ] **Step 4: 세 빈을 등록한다**

`src/main/java/ai/devpath/aigw/provider/ClaudeProbeConfig.java`:

```java
package ai.devpath.aigw.provider;

import com.anthropic.client.AnthropicClient;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 세 기능의 Claude 복구 탐색기. 키가 없으면 AnthropicClient 빈이 없으므로 탐색기도 만들지 않는다
 * (그 경우 Claude 는 애초에 체인에 없어 래치가 열릴 일도 없다).
 */
@Configuration
@ConditionalOnExpression("'${ANTHROPIC_API_KEY:}' != ''")
public class ClaudeProbeConfig {

  @Bean
  public ProviderProbe reviewClaudeProbe(
      @Qualifier("anthropicClient") ObjectProvider<AnthropicClient> client,
      @Value("${devpath.review.claude-model:claude-sonnet-4-6}") String model) {
    return new ClaudeProviderProbe("review", client.getObject(), model);
  }

  @Bean
  public ProviderProbe communitySeedClaudeProbe(
      @Qualifier("communitySeedAnthropicClient") ObjectProvider<AnthropicClient> client,
      @Value("${devpath.community-seed.claude-model:claude-haiku-4-5}") String model) {
    return new ClaudeProviderProbe("community-seed", client.getObject(), model);
  }

  @Bean
  public ProviderProbe retentionClaudeProbe(
      @Qualifier("retentionAnthropicClient") ObjectProvider<AnthropicClient> client,
      @Value("${devpath.retention.claude-model:claude-sonnet-4-6}") String model) {
    return new ClaudeProviderProbe("retention", client.getObject(), model);
  }
}
```

- [ ] **Step 5: 통과를 확인한다**

Run: `./gradlew test --tests 'ai.devpath.aigw.provider.*'`
Expected: PASS

- [ ] **Step 6: 전체 스위트**

Run: `./gradlew test`
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add src/main/java/ai/devpath/aigw/provider/ClaudeProviderProbe.java \
        src/main/java/ai/devpath/aigw/provider/ClaudeProbeConfig.java \
        src/test/java/ai/devpath/aigw/provider/ClaudeProviderProbeTest.java
git commit -m "feat(provider): probe Claude recovery with a one-token request"
```

## 완료 조건

- [ ] `./gradlew test` 전체 녹색
- [ ] `*_FALLBACK` 미설정 시 모든 체인 길이 1 — **운영 동작 불변**
- [ ] `REVIEW_FALLBACK=ollama` 를 주면 `FallbackAiReviewClient` 가 조립되고, 429 한 번으로 래치가 열려 다음 요청이 Claude 를 건너뛴다
- [ ] `mock` 이 review·community-seed·retention 체인에 **들어가지 않는다**(Task 9 가 못박는다)
- [ ] `ProviderProbeScheduler` 가 **빈 리스트가 아닌** 탐색기 3개를 받는다(Task 10) — 기한이 지난 래치를 사용자 요청이 아니라 배경이 닫는다
- [ ] 멘토 동작·테스트 불변
- [ ] gitops **미변경**

## 알려진 한계 (의도한 것)

- **래치는 인메모리다.** 재시작하면 모든 래치가 닫힌다 — 첫 요청이 실패를 한 번 물고 다시 열린다. `replicas: 1` 전제와 같은 이유로 수용한다(스펙 §2.2·§11).
- **Ollama 쪽에는 탐색기가 없다.** Task 10 은 Claude 만 탐색한다. Ollama 가 차단되면 기한 만료로 닫히고 다음 요청이 탐색을 대신 문다. Ollama 는 클러스터 내부 호출이라 지연 비용이 작아 수용한다 — 필요해지면 같은 인터페이스로 추가한다.
- **멘토는 래치를 쓰지 않는다.** 이 계획은 멘토의 기존 동작을 바꾸지 않는다(스펙 §4.2). 멘토에 래치를 들이는 것은 스트리밍 계약과 얽혀 별도 판단이 필요하다.

## 계획 B (후속, 이 계획 밖)

- 스펙 §10 관측 메트릭(`..._provider_served_total` · `..._provider_latch_open` · `..._provider_failure_total`) — actuator 는 이미 있고 기존 커스텀 메트릭이 0개라 이름을 자유롭게 정한다.
- 스펙 §5 review 재생성 엔드포인트(Claude 래치가 열려 있으면 즉시 거절, 실패해도 기존 산출물 보존).
- 모델 결정과 `gitops` env 반영 — 스펙 보정 §B·§C.
