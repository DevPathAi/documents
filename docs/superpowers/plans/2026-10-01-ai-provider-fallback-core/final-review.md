# Code Review — `feat/ai-provider-fallback-core` (`f8e9b59..5f4d3f4`)

Reviewer: senior code reviewer (read-only pass, 2026-10-01).
Repo under review: `D:/workspace/dpa/.worktrees/ai-svc-provider-fallback` (worktree of `devpath-ai-svc`).
Base `f8e9b59594e758955c31b147fdce4a1a821b432d` (origin/develop) → Head `5f4d3f4`.

Scope read: `spec.md` including the **보정 (2026-10-01)** section, the plan
(`2026-10-01-ai-provider-fallback-core.md`), the full `progress.md` ledger (all ten `Ruling:` lines),
all 20 changed/new main sources, all 12 changed/new test sources, the pre-existing callers
(`ReviewService`, `CommunitySeedService`, `ReEngagementController`), `FallbackMentorClient`, and the
stored test results.

Verification cross-check: `build/test-results/test/*.xml` sums to **339 tests / 0 failures / 1 skipped**
(81 result files), and `TEST-ai.devpath.aigw.AiApplicationTests.xml` shows `contextLoads()` passing.
The executor's claim is therefore plausible and reconciled. A useful side-effect of that evidence: the
full application context boots with **zero** `ProviderProbe` beans (no `ANTHROPIC_API_KEY` in
`src/test/resources/application-test.yml`), so `ProviderProbeScheduler`'s `List<ProviderProbe>`
constructor parameter resolving to an empty list is confirmed safe rather than assumed.

---

## Strengths

- **The mentor no-change constraint is genuinely honored, not just claimed.** `ProviderChain.ordered`
  is a verbatim lift of `MentorClientConfig.orderedChain`; the only mentor-side edit is the call site
  plus imports (`src/main/java/ai/devpath/aigw/mentor/MentorClientConfig.java:44`). The five
  table-driven tests moved unchanged — the `MentorClientConfigTest` diff is purely the receiver name —
  `FallbackMentorClient` is untouched, and `MentorClientConfig.java:45-47` preserves the
  `chain.isEmpty() → mock` safety net exactly. `MentorClientWiringIT` / `MentorClientQualifierTest`
  still pass.

- **Task 3's ruling is a real improvement over the plan.** Classifying by
  `AnthropicServiceException.statusCode()` (`src/main/java/ai/devpath/aigw/provider/ProviderFailures.java:47-48`)
  instead of type-by-type `instanceof` applies one rule to both the Anthropic SDK and Spring
  `RestClient`, picks up `NotFoundException` / `UnprocessableEntityException` /
  `UnexpectedStatusCodeException` for free, and — contradicting the plan's own test, correctly — reads
  Claude's `Retry-After` (`ProviderFailures.java:74-81`). `ProviderFailuresTest` exercises the real SDK
  exception builders, not mocks.

- **The cause-chain walk is load-bearing and was spotted.** Every existing client wraps SDK/HTTP
  failures (`src/main/java/ai/devpath/aigw/review/ClaudeAiReviewClient.java:48-58`,
  `src/main/java/ai/devpath/aigw/review/OllamaAiReviewClient.java:64-76`), and all four exception
  constructors pass the cause to `super(message, cause)` (verified in `TransientReviewException`,
  `PermanentReviewException`, `SeedGenerationException`, `ReEngagementGenerationException`). Without
  `ProviderFailures.classify`'s unwrap (`ProviderFailures.java:32-41`) the latch would never see a
  single 429. The `MAX_CAUSE_DEPTH = 16` bound, the self-cause guard (`:38`) and the a→b→a cycle test
  (`src/test/java/ai/devpath/aigw/provider/ProviderFailuresTest.java:139-156`) all came from an
  executor ruling after the plan's self-causation test proved impossible in Java.

- **`ClaudeProviderProbeTest` is the strongest test in the branch.** Task 10's ruling — a real SDK
  client against `MockWebServer` instead of the plan's Mockito deep stub — pins the actual wire format
  (`POST /v1/messages`, `"max_tokens":1`) at
  `src/test/java/ai/devpath/aigw/provider/ClaudeProviderProbeTest.java:66-79`, *and* that
  429 → `RateLimitException` + `Retry-After: 42` (`:81-94`) and 401 → `UnauthorizedException` (`:96-106`)
  flow into `ProviderFailures` unchanged. A deep stub can show neither fact.

- **Task 9's ruling caught a vacuous test in the plan and proved the fix.** The plan's regression lock
  compared `providerName()` (which returns the chain head before any call) against `"MOCK"` — wrong
  case against lowercase chain keys — so it passed with `mock` injected. The executor measured that,
  switched to `isExactlyInstanceOf` on the assembled bean
  (`src/test/java/ai/devpath/aigw/provider/MockExclusionTest.java:58-59,72-74,85-86`), re-injected the
  violation to observe FAILED, and reverted to observe SUCCESSFUL. Right instinct, right evidence.

- **The safe-default constraint holds.** All three `*_FALLBACK` keys are `${…:}` in
  `src/main/resources/application.yml:40,70,81`; all three chains are length 1; and chain-size-1
  returns the **bare** client (`src/main/java/ai/devpath/aigw/review/ReviewClientConfig.java:54-55`)
  so no wrapper is interposed at all. Nothing outside `devpath-ai-svc` changed — gitops is untouched
  and `ai_release_eval_config.rendered_config_sha256` is unaffected.

- **`mock` exclusion is structural, not filtered.** `mock` is never placed in the `available` map
  (`ReviewClientConfig.java:40-46`, `CommunitySeedClientConfig.java:38-44`,
  `ReEngagementClientConfig.java:37-44`), so no configuration value can route to it; `provider=mock`
  short-circuits before assembly (`ReviewClientConfig.java:36-38`) and still works. Both halves are
  tested (`MockExclusionTest.java:49-107`).

- **Indentation contract met exactly** — verified mechanically: zero tab-indented lines under
  `provider` / `review` / `community` / `mentor`, and zero space-indented code lines under `retention`
  (which uses tabs, e.g. `src/main/java/ai/devpath/aigw/retention/ReEngagementClientConfig.java:21-55`).

- **All five named review-focus input classes have a test that actually pins them**:
  duplicate collapse (`ProviderChainTest.java:32-37`), whitespace/empty-entry handling
  (`ProviderChainTest.java:39-44`), `fallback=claude` with no key and no boot failure
  (`ClaudeBeanConditionTest.java:47-60`), all-latches-open surfacing the feature's own exception
  (`FallbackAiReviewClientTest.java:110-121`), and success resetting the consecutive counter
  (`ProviderLatchTest.java:97-110`).

- **No real-time `sleep` anywhere.** Both clock stubs are movable
  (`ProviderLatchTest.java:18-26`, `ProviderProbeSchedulerTest.java:19-27`).

- **The Claude beans were re-conditioned correctly per 보정 §D-①.** All three configs moved from
  `@ConditionalOnProperty(havingValue="claude")` to `@ConditionalOnExpression("'${ANTHROPIC_API_KEY:}' != ''")`
  (`review/ClaudeClientConfig.java:19`, `community/CommunitySeedClaudeConfig.java:19`,
  `retention/RetentionClaudeClientConfig.java:18`), with `maxRetries(0)` and explicit timeouts per
  보정 §D-②. `ClaudeBeanConditionTest.java:33-45` proves three beans exist from the key alone regardless
  of provider value — which is exactly what makes `ollama` primary + `claude` upgrade possible.

---

## Issues

### Critical (Must Fix)

**C1 — Provider identity recording is broken exactly when fallback happens. Spec success criteria #3
and #4 are not met.**

Three defects in one mechanism.

*(a) The caller reads `providerName()` before the call it describes.*
`src/main/java/ai/devpath/aigw/review/ReviewService.java:91-92` (pre-existing, unchanged on this branch):

```java
provider = aiReviewClient.providerName();
result   = aiReviewClient.review(new ReviewInput(...));
```

`src/main/java/ai/devpath/aigw/review/FallbackAiReviewClient.java:54-57` only knows the answer *after*
`review()` returns:

```java
public String providerName() {
  String s = served.get();
  return s != null ? s : delegates.keySet().iterator().next();
}
```

So with a chain of ≥2: the **first** review on a worker thread records the **chain head** (`claude`)
regardless of who actually served; **every later** review on that thread records the **previous
request's** provider. It is reliably wrong precisely when a fallback occurred — the only reason this
feature exists. The value reaches `ai_code_reviews.provider` via
`src/main/java/ai/devpath/aigw/review/ReviewPersistenceService.java:131-136` (`finishDone`).

Why no test catches it: `src/test/java/ai/devpath/aigw/review/FallbackAiReviewClientTest.java:146-155`
calls `review()` **then** `providerName()` — the opposite order from production — and all twelve
existing review Spring tests stub `when(aiReviewClient.providerName()).thenReturn("MOCK")`
(e.g. `ReviewConsumerIT.java:55,73,95,118`, `ReviewServiceIdempotencyTest.java:67,125`,
`ReviewRetryIT.java:39`, `ReviewServicePersistenceBoundaryTest.java:36`), so a constant is always
returned and the ordering is never exercised.

*(b) The `ThreadLocal` is never cleared.*
`src/main/java/ai/devpath/aigw/review/FallbackAiReviewClient.java:20,39-40`,
`src/main/java/ai/devpath/aigw/community/FallbackAiSeedClient.java:20,39-40`,
`src/main/java/ai/devpath/aigw/retention/FallbackReEngagementClient.java:20,39-40` — each calls
`served.set(name)` with no `remove()` on any path. On a pooled worker thread the value outlives the
request indefinitely. Concretely: `src/main/java/ai/devpath/aigw/community/CommunitySeedService.java:50`
publishes `seedClient.providerName()` on the **failure** path, where `served` holds the *previous*
request's provider (or the chain head) — a `seed.ready FAILED` event attributing the failure to a
provider that was never involved.

*(c) The stored name is the lowercase chain key, not the provider's own name.*
Every concrete client returns UPPERCASE — `ClaudeAiReviewClient.java:62-64` (`"CLAUDE"`),
`OllamaAiReviewClient.java:45-48` (`"OLLAMA"`), `MockAiReviewClient.java:26` (`"MOCK"`),
`community/ClaudeSeedClient.java:52`, `community/OllamaSeedClient.java:60`,
`retention/ClaudeReEngagementClient.java:44`, `retention/OllamaReEngagementClient.java:55` — and the
column already holds those values (existing ITs assert `"MOCK"`). The three wrappers return
`"claude"` / `"ollama"`, so switching on `*_FALLBACK` starts writing a second casing into the same
column; operations can no longer group by provider without normalizing, which directly undercuts spec
criterion #4.

**The pre-existing `FallbackMentorClient` already solves all three and was not followed:**
`src/main/java/ai/devpath/aigw/mentor/FallbackMentorClient.java:27` (`remove()` on entry), `:34,:38`
(`remove()` on entry and in `finally`), `:62-65` (read-once-and-clear in `providerName()`), and `:48`
stores `d.providerName()` — the delegate's own uppercase name — plus a `providerSelected` callback
(`:32-40,:49`) so the caller is told at the right moment with no thread-local at all.

**This is a defect in the PLAN, not an executor deviation.** The plan specifies this exact
`ThreadLocal` (plan lines 1308, 1342, 1615, 1649, 2068, 2101) and this exact assertion
`assertEquals("ollama", client.providerName())` (plan lines 1274, 1581, 2036). The implementation is
faithful to it.

*Fix (one change, three effects):* in each `Fallback*Client`, store `e.getValue().providerName()`
instead of the chain key, and clear the thread-local on method entry and in a `finally`; then either
reorder `ReviewService.java:91-92` to read `providerName()` after `review()`, or — better, and matching
mentor — have the chain report the selection through a callback or on the result so no thread-local is
needed. Update the three `reportsTheProviderThatActuallyServed` tests to assert the uppercase name, and
add the integration test in **I5** so the ordering bug cannot return.

---

### Important (Should Fix)

**I1 — `ProviderLatch`'s mutable state is read without synchronization or `volatile`.**
`src/main/java/ai/devpath/aigw/provider/ProviderLatch.java:30-34` declares `State.openUntil`,
`State.lastBackoff` and `State.transientRun` as plain fields. Writes happen inside `synchronized (s)`
(`:54`, `:64`), but `isOpen()` (`:47-50`) and `dueProbes()` (`:88-98`) read them with no
synchronization. `states` being a `ConcurrentHashMap` (`:37`) safely publishes the `State`
*reference*, not its fields. Under the JMM there is no happens-before edge between the writer's monitor
exit and an unsynchronized reader, so a request thread may observe a stale `openUntil` indefinitely —
continuing to hammer a provider the scheduler just blocked, or continuing to skip one it just closed.
That is the latch's entire purpose, and the state is shared across request threads and the scheduler
thread by design (`ProviderProbeScheduler.java:30-45`).
*Fix:* mark the three fields `volatile`, or read them inside `synchronized (s)`. Cost is negligible.

**I2 — Deadline expiry both unblocks the provider and schedules the probe, so user requests end up
doing the probing — the thing spec §3.1 forbids.**
`ProviderLatch.isOpen()` (`:47-50`) returns false the instant `openUntil` passes, and `dueProbes()`
(`:88-98`) reports the same entry only from that moment. Three consequences, worsening:

1. Between expiry and the next scheduler tick (`devpath.provider.probe-interval`, default `PT1M` —
   `ProviderProbeScheduler.java:29`, `application.yml:84-85`) user requests go to the dead provider and
   pay the full `claude-timeout` (60 s each — `ClaudeClientConfig.java:26`).
2. For `TRANSIENT`, a probe failure only re-opens the latch on the **third consecutive** one
   (`ProviderLatch.java:77-82`). During a sustained Claude 5xx outage the latch is therefore
   effectively *closed* for ~3 scheduler ticks (~3 minutes) after every expiry, with user traffic
   absorbing 60 s timeouts throughout. Spec success criterion #2 ("매 요청이 Claude 실패 지연을 물지
   않는다") is only partly achieved.
3. If a probe failure classifies as `BAD_REQUEST` or `OUTPUT_INVALID`, `recordFailure` does nothing
   (`ProviderLatch.java:66-68`) — the entry stays past-due **forever**: the scheduler pings Claude once
   a minute indefinitely while `ProviderProbeScheduler.java:42-43` logs
   `"provider latch stays open"`, which is false. The realistic trigger is a 404 from a bad model name:
   `src/main/java/ai/devpath/aigw/provider/ClaudeProbeConfig.java:25,32,39` re-reads
   `devpath.*.claude-model` independently of the clients, so a stale default there produces exactly
   this; and `ProviderFailures.fromStatus` (`:60-67`) maps 404 to `OUTPUT_INVALID`.
   `src/test/java/ai/devpath/aigw/provider/ProviderProbeSchedulerTest.java:108-124`
   (`oneFailingProbeDoesNotStopTheOthers`) creates this state with an `IllegalStateException` probe
   failure and asserts nothing about that latch.

*Fix:* probes are not user traffic, so the "3 consecutive" rule — which exists so one user-visible blip
does not cut a provider off — should not gate them: extend the deadline on *any* probe failure. Better
still, separate "blocked" from "probe me": keep `isOpen` true until a probe confirms recovery and have
expiry only set a `probePending` flag. Then no user request ever probes, which is what §3.1 asks for.

**I3 — `lastBackoff` is shared between `RATE_LIMIT` and `TRANSIENT`, so their escalations contaminate
each other.** `ProviderLatch.java:105-110` keeps one `lastBackoff` per `(feature, provider)` while spec
§3 gives each kind its own base and cap (5 m / 1 h versus 1 m / 30 m — `ProviderLatch.java:24-27`).
Both directions are wrong: a 429 opening at 5 m followed by three transients yields **10 m instead of
1 m** (a provider blocked longer than designed); a transient opening at 1 m followed by a header-less
429 yields **2 m instead of 5 m** (more retry pressure on an exhausted account than designed). Not
covered by any test. *Fix:* keep `lastBackoff` per kind (two fields, or a small `EnumMap`), and add the
missing transient doubling/cap assertions.

**I4 — Production pays for `maxRetries(0)` today and only collects the benefit later.**
보정 §D-② justified disabling SDK retries because they distort latch judgment — correct *when a chain
exists*. But 보정 §C deliberately ships with `*_FALLBACK` empty, so all three chains are length 1 and
`ReviewClientConfig.java:54-55` returns the **bare** `ClaudeAiReviewClient`: no `FallbackAiReviewClient`,
no latch, no fallback. Net effect on the configuration production will actually run: `fromEnv()`'s
default retry budget and default request timeout become `maxRetries(0)` + `PT60S`
(`ClaudeClientConfig.java:26-32`, `CommunitySeedClaudeConfig.java:26-32`,
`RetentionClaudeClientConfig.java:25-31`), so a single 429/503 the SDK used to absorb now surfaces, and
a slow-but-successful call over 60 s becomes a failure. Review has an outer safety net
(`TransientReviewException` → `ReviewService.java:95-97` `releaseForRetry` → Kafka retry / lease
recovery), but **retention does not** —
`src/main/java/ai/devpath/aigw/retention/ReEngagementController.java:30` is a synchronous HTTP endpoint
with no retry at all. *Fix:* either keep a small SDK retry budget (5xx only) until a chain is
configured, or accept the trade explicitly and record it — it should be a decision, not a side effect.

**I5 — Spec §9's integration item was dropped from the plan without a ruling, and it is the exact test
that would have caught C1.** §9 asks for "통합 — Ollama·Claude 를 둘 다 스텁으로 두고 네 기능의 체인을
한 번씩". No plan task covers it (the plan contains no occurrence of "통합"; its ten task headings are
at plan lines 58, 248, 601, 849, 1071, 1443, 1740, 2192, 2478, 2590), and no test drives `ReviewService`
or `CommunitySeedService` through a real `Fallback*Client`. `MockExclusionTest` assembles the chains but
never calls through them. *Fix:* one `ApplicationContextRunner` / `@SpringBootTest` test per feature
that places a failing Claude stub and a succeeding Ollama stub in the chain, invokes the **service**
(not the client), and asserts the persisted/published provider is `"OLLAMA"`.

---

### Minor (Nice to Have)

**M1 — The feature key is a magic string in four places with nothing tying them together.**
`FallbackAiReviewClient.java:16` (`"review"`), `FallbackAiSeedClient.java:16` (`"community-seed"`),
`FallbackReEngagementClient.java:16` (`"retention"`) and `ClaudeProbeConfig.java:26,33,40`. They match
today (checked), but a typo on either side silently disables recovery probing for that feature with no
test failure. Extract a shared constant or enum and have both sides reference it.

**M2 — `ClaudeBeanConditionTest.java:63-75` asserts on source text, not behavior.**
`Files.readString(...)` + `assertThat(source).contains("maxRetries(0)")` would pass if the string
appeared only in a comment, and `Path.of("src/main/java/ai/devpath/aigw", relative)` (`:79`) depends on
the Gradle working directory. `MockWebServer` is already a test dependency
(`build.gradle.kts:63`) and Task 10 proved the pattern: enqueue a 500 and assert exactly one recorded
request.

**M3 — Cap assertions are one-sided.** `ProviderLatchTest.java:75-81` proves the rate-limit deadline is
≤ 61 min, not that the cap *is* 1 h (a 30-min cap would also pass); add an `assertTrue` just under the
cap. The transient 30-min cap (`ProviderLatch.java:27`) and the 1 m→2 m doubling are untested entirely.

**M4 — `ClaudeProbeConfig` gains nothing from `ObjectProvider` and fails hard.**
`ClaudeProbeConfig.java:26,33,40` call `client.getObject()`, which throws if the bean is absent —
identical to direct injection, except the failure now takes down the whole application context.
`getIfAvailable()` plus skipping that probe would degrade gracefully if any of the three Claude configs
is ever re-conditioned. The same file also re-reads `devpath.*.claude-model` independently of the
clients (`:25,32,39`), creating two places to keep in sync and feeding I2's third face.

**M5 — No structured log on the user path when a latch opens or closes.**
`ProviderProbeScheduler.java:37,42` logs, but `ProviderLatch.recordFailure` / `open`
(`ProviderLatch.java:61-85,100-102`) do not — and the user path is where latches normally open. Spec
§10's "래치가 열리고 닫힐 때 이유와 기한을 담은 구조화 로그 한 줄" is part of success criterion #4; §10
is plan B so the *metrics* are rightly deferred, but the asymmetry means criterion #4 currently has
neither a correct `provider` value (C1) nor a log. Separately, the scheduler prints
`"provider latch stays open"` even for kinds that did not open it.

**M6 — `.gitignore` line endings flipped.** `git show f8e9b59:.gitignore` is plain ASCII (LF); at HEAD
the file reports "with CRLF, LF line terminators". The first 37 lines became CRLF, so the file now has
mixed terminators and the diff shows **75 changed lines for a 2-line intent** (`+.superpowers/`). This
is the known local-tool-rewrites-config-files hazard.

**M7 — Dead annotations and stray blank lines from the de-componentization.**
`ClaudeAiReviewClient.java:25-26` still carries `@Qualifier("anthropicClient")` and
`@Value("${devpath.review.claude-model:…}")` on constructor parameters Spring no longer processes (the
class is now built with `new` in `ReviewClientConfig.java:45`); same in `community/ClaudeSeedClient` and
`retention/ClaudeReEngagementClient`. The three `Mock*Client`s (`review/MockAiReviewClient.java`,
`community/MockSeedClient.java`, `retention/MockReEngagementClient.java`) have a leftover double blank
line where the removed imports were.

**M8 — `provider=mock` plus a non-empty fallback silently ignores the fallback.**
`ReviewClientConfig.java:36-38` (and the equivalent in `CommunitySeedClientConfig.java:34-36`,
`ReEngagementClientConfig.java:33-35`) short-circuits before assembly. Intentional and tested
(`MockExclusionTest.java:90-107`), but a misconfiguration produces no warning. One `log.warn` when
`fallbackCsv` is non-empty on the mock path would close it.

**M9 — Ollama 404 ("model not found") classifies as `OUTPUT_INVALID`.**
`ProviderFailures.java:60-67` leaves 404 outside the latch, so the latch never opens and both providers
are attempted on every request with no backoff. That is the single most likely Ollama failure in this
cluster right now, since 보정 §B measured that neither `qwen2.5-coder:7b` nor `qwen2.5:7b` is pulled.
Cost per request is one fast 404, so the behavior is defensible — but it should be a recorded decision
rather than a side effect of the status table, because the operator who flips `REVIEW_FALLBACK=ollama`
a day early gets no backoff signal at all. (Related: `OllamaAiReviewClient.java:72` maps that 404 to
`PermanentReviewException`, so the review fails permanently rather than retrying.)

**M10 — Three `AnthropicOkHttpClient`s are now built whenever `ANTHROPIC_API_KEY` is present**,
regardless of provider values (`ClaudeClientConfig.java:19`, `CommunitySeedClaudeConfig.java:19`,
`RetentionClaudeClientConfig.java:18`), each with its own OkHttp connection pool and dispatcher. No
change in production (all three features are `claude` per spec §1), but dev/CI with a key set now pays
for three idle clients where it previously paid for zero or one.

**M11 — `.superpowers/` is now gitignored** (`.gitignore`, final two lines), so the `Ruling:` ledger —
the record of ten reasoned deviations — lives only in this worktree. Past campaigns preserved that
record in `documents/docs/superpowers/`.

**M12 — `.omc/` is untracked and not ignored** (visible in `git status --porcelain` as `?? .omc/`), and
`src/test/java/ai/devpath/aigw/mentor/MentorClientConfigTest.java:3` places a non-static import above
the static import block.

---

## Declined to judge

Everything I considered and set aside, one line each, with the reason. Nothing here is dropped
silently — the executor rules on each line.

1. Micrometer counters and gauges (spec §10) — 보정 §E assigns them to plan B.
2. `review` regeneration endpoint and its latch-open rejection (spec §5) — plan B.
3. Ollama model availability, pull, and node disk/memory capacity (spec §6.1, 보정 §B) — 보정 §C defers
   to a separate decision; `*_FALLBACK` stays empty until then.
4. Mentor provider order (`MENTOR_PROVIDER=ollama` first) — spec §4.2 places it out of scope; verified
   unchanged.
5. Mentor's `chain.isEmpty() → mock` safety net — spec §4.1 keeps it deliberately; verified unchanged
   at `MentorClientConfig.java:45-47`.
6. `ProviderLatch` sharing across replicas / shared store — spec §11 out of scope under `replicas: 1`;
   the required warning is present at `ProviderLatch.java:14-16`.
7. gitops `*_FALLBACK` env and the `rendered_config_sha256` re-render (spec §8) — out of scope by
   보정 §C; verified nothing outside this repo changed.
8. The Kafka retry/DLQ policy that now receives an *instant* `LLM_ALL_PROVIDERS_BLOCKED` instead of a
   timeout-delayed failure — no `DefaultErrorHandler`/backoff configuration exists under
   `src/main/java/ai/devpath/aigw/config/`, and the consumer's retry policy predates this change; I note
   only that the retry window shortens, and leave the policy itself alone.
9. Prompt construction, parsing and injection defenses in `ClaudeSeedClient` / `OllamaSeedClient` /
   `ReviewPromptBuilder` / `SeedPromptBuilder` — untouched by this branch.
10. `ReviewService`'s claim / lease / disposition mechanics — untouched; read only to establish how
    `provider` reaches the database.
11. Whether `@Value("${ANTHROPIC_API_KEY}")` should also reject a whitespace-only key — a pre-existing
    pattern copied verbatim from `MentorClaudeClientConfig`.

---

## Recommendations

1. Fix **C1** as one change: store the delegate's `providerName()`, manage the thread-local lifecycle
   the way `FallbackMentorClient` does (or drop the thread-local for a callback), and read it after the
   call in `ReviewService.java:91-92`. Update the three `reportsTheProviderThatActuallyServed`
   assertions to the uppercase name.
2. Add **I5**'s three service-level integration tests in the same change — they are what keeps C1 fixed.
3. Make the three `ProviderLatch.State` fields `volatile` (**I1**).
4. Decide **I2**: either extend the deadline on any probe failure, or split "blocked" from "probe me"
   with a `probePending` flag. The third face (past-due forever plus a log line that says the opposite)
   should be fixed either way.
5. Split `lastBackoff` per `FailureKind` and add the missing transient doubling/cap tests (**I3**).
6. Rule on **I4** explicitly — a recorded "we accept losing SDK retries now" is fine; an unnoticed one
   is not. Retention's synchronous endpoint is the exposed case.
7. Cheap cleanups worth doing while in here: shared feature constant (**M1**), a behavioral
   `maxRetries(0)` test (**M2**), `.gitignore` line endings (**M6**), dead annotations (**M7**).

---

## Assessment

**Ready to merge?** **With fixes**

**Reasoning:** The wiring refactor itself is sound, well-tested, and keeps the two hard constraints
(mentor unchanged, `mock` never in the three chains) with evidence — and three of the executor's ten
rulings materially improved on the plan. But C1 means the feature's own success criteria #3 and #4 are
broken the moment anyone sets `*_FALLBACK`, with wrong *and* wrongly-cased values written to a
persisted column that already holds the old format; the fix is small and the integration test that
locks it is the one spec §9 asked for and the plan dropped. I1 and I2 should land before the flag is
ever turned on.
