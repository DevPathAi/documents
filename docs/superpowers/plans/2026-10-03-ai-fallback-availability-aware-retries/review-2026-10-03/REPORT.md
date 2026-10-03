All evidence is in. Here is the complete review.

---

# Final branch review — `feat/ai-fallback-availability-aware-retries` (c26bb6d..509bd60, 13 commits)

Scope: spec (documents `origin/develop` …/2026-10-03-ai-fallback-availability-aware-retries-design.md), plan (documents-aifb-plan-1003), ledger (`.superpowers/sdd/…/progress.md`), full diff (36 files, +1355/−90). Reviewed in three passes: main sources, feature-package tests, provider-package tests + surrounding context (ProviderLatch, ProviderFailures, ProviderProbeScheduler, ClaudeClients, ProviderChain, ClaudeProbeConfig, OutboxRelayScheduler, the three Claude/Ollama clients, CommunitySeedService, ReEngagementController, community-svc seed consumer). I also inspected `anthropic-java-core-2.34.0` bytecode and re-ran the new unit tests (ProviderAttemptPlan 8, ProviderProbeScheduler 11, OllamaProviderProbe 7, FallbackParity 5, ClaudeRetryBudget 4, OllamaProbeConfig 4, Fallback{Review,Seed,ReEngagement}Client 13/10/9 — all 0 failures, 0 errors). Nothing in any repo was modified.

### Strengths

- **Plan fidelity is high.** The main-source diff matches the plan's code blocks essentially verbatim; 13 commits map 1:1 to Tasks 1–13; every task in the ledger carries a per-class JUnit XML count, and the final 414 = 359 + 58 − 3 reconciles with my own count of added/removed tests.
- **`ProviderAttemptPlan` is a clean pure function** with the latch read exactly once per provider (RF4 `consultsTheLatchOncePerProvider`), and it genuinely removed the three copied loops.
- **`ClaudeClients.lastResort` via `withOptions` is sound.** `ClientOptions` keeps `originalHttpClient`, and `Builder.from$anthropic_java_core` does `putfield httpClient ← access$getOriginalHttpClient$p` (verified with `javap -c`), so the copy wraps the *same* OkHttp client in a fresh `RetryingHttpClient(2)` — no second pool/thread, no second bean, `ClaudeBeanConditionTest` untouched. `ClaudeRetryBudgetTest` proves 3 vs 1 requests against a real MockWebServer.
- **`FallbackParityTest` is a real end-to-end proof**, not a mock test: real `ClaudeClientConfig`/`*ClientConfig`/`OllamaProbeConfig`, real SDK retry, a closed port for Ollama, Claude mock 500→200. The ledger records the negative control (dropping `lastResort` fails exactly the three parity tests).
- **Review Focus 1–5 each has a targeted test and the implementation holds**: `isFallback` reuses `requestedNames` (same trim/dedupe), exact model-name match, 500 ms read-timeout probe finishes in <2.5 s and classifies TRANSIENT, liveness opens immediately via `recordProbeFailure`, served name is the delegate's `providerName()` so both Claude variants record `CLAUDE`.
- **Production chain-length-1 path (Claude primary, empty fallback) is byte-for-byte unchanged**: no wrapper, no probe beans (`registersNothingWithoutAFallback`), `anthropicClient` bean and `maxRetriesFor` untouched.
- **Mentor untouched** — no mentor file in the diff; `ProviderFailures`/`ProviderLatch` usages are only the three wrappers and the scheduler (grep-verified).
- Claude 404 stays `OUTPUT_INVALID` (control test kept); Ollama 404 is found through the cause chain, so review's `TransientReviewException("LLM_MODEL_UNAVAILABLE", …, e)` still opens the latch correctly.
- All four new config keys have defaults and a rationale comment in `application.yml`; no gitops env change is needed, as spec §4 promises.

### Issues

#### Critical (Must Fix)

None.

#### Important (Should Fix)

**I-1. Rule-③ ("all blocked → primary once") failures inflate the primary's latch backoff — new regression in the dual-outage recovery path.**
Files: `src/main/java/ai/devpath/aigw/review/FallbackAiReviewClient.java:69-70`, `community/FallbackAiSeedClient.java:69-70`, `retention/FallbackReEngagementClient.java:68-69`, together with `provider/ProviderLatch.java` `recordFailure` (RATE_LIMIT → `nextRateLimit`, TRANSIENT → `nextTransient`).
Before this branch an *open* latch was never called, so `recordFailure` on an open latch was unreachable. Now every request in the all-blocked state calls Claude LAST_RESORT and, on failure, `recordFailure(…)` again: without a `Retry-After` header each failing request doubles the rate-limit ladder 5→10→20→40→60 min (TRANSIENT: 1→…→30 min). Effect: when Ollama comes back (due probe closes its latch), Claude is skipped in favour of 7b for up to 60 min after Claude itself recovered, because the Claude due probe only fires at `openUntil`. With fallback disabled there is no latch at all, so "same as fallback-disabled" fails in the recovery dimension. Spec §3.1-3 ("실패·성공 기록은 지금처럼") did not anticipate this interaction.
Fix (either): (a) extend `Attempt` with a `forced` flag set only by the `usable.isEmpty()` branch and skip `latch.recordFailure` for forced attempts (keep `recordSuccess` so success closes the latch) — explicit and local; or (b) make `ProviderLatch.recordFailure` a no-op while `isOpen(feature, provider)` is true — one line, backward-compatible because that state was unreachable before, but it changes a shared primitive.
Failing test (any wrapper test, MovableClock): open claude RATE_LIMIT + ollama AUTH; `patient` stub throws `status(429)`; call once → throws; `clock.advance(5m+1s)`; `assertFalse(latch.isOpen("review","claude"))` — currently **true** (backoff grew to 10 min).

**I-2. The detected-dead fallback becomes "usable" again for up to one tick at every backoff expiry.**
Files: `provider/ProviderLatch.java` `isOpen` (`now.isBefore(openUntil)`), `provider/ProviderProbeScheduler.java:64-78` (`runLivenessProbes`) and `:29-56` (`runDueProbes`).
`isOpen` is false the instant `openUntil` passes; nothing re-opens it until the next liveness (≤30 s) or due (≤60 s) tick. In that window `ProviderAttemptPlan` plans `[claude FAST, ollama LAST_RESORT]`, so a single Claude 529 falls to dead Ollama (3 s connect fail) and the request fails — seed loses the answer permanently, retention fails synchronously. This recurs at 1, 2, 4, 8, 16, 30, 30… min while Ollama stays dead (≈2–3 % of the first hour, ≈1 % steady state, only harmful when Claude also fails inside the window). Spec §3.3 lists only the *initial* ≤30 s detection window; this recurring one is not listed and contradicts §2's "같다".
Resolution: either document it in spec §3.3 as accepted residual risk, or close it: for liveness targets, ping on every liveness tick regardless of state; on failure `open(now + 2×livenessInterval)` (no ladder — the 30 s cadence already bounds probe cost); on success `recordSuccess` only if `openUntil != null`. That also removes the liveness→due hand-off.
Failing test (`ProviderProbeSchedulerTest`, MovableClock): liveness fails at T0 → `assertTrue(isOpen)`; `clock.advance(61s)`; `assertTrue(latch.isOpen("review","ollama"))` — currently **false**.

**I-3. Both probe loops and `OutboxRelayScheduler` share the single default scheduler thread.**
Files: `src/main/resources/application.yml` (no `spring.task.scheduling.pool.size`), `outbox/OutboxRelayScheduler.java:18` (`fixedDelay = 2000`, `!test`), `provider/ProviderProbeScheduler.java:29,64`.
`runLivenessProbes` pings three features sequentially; worst case 3 × (3 s connect + 5 s read) = 24 s when Ollama accepts but hangs, 9 s when the endpoint black-holes (node gone but endpoint not yet withdrawn — up to ~5 min with default taint-based eviction). During that time the outbox relay and `runDueProbes` stall. It is bounded (latch opens → later ticks skip; recurs only at backoff expiries) and the pre-existing Claude due probe (60 s timeout) already had the same exposure, so this is the low end of Important — but the fix is a one-liner: `spring.task.scheduling.pool.size: 2` (or a dedicated `TaskScheduler` for the probe component). Optional: dedupe the three `/api/tags` pings per base URL.

#### Minor (Nice to Have)

**M-1.** `provider/OllamaProbeConfig.java:17-19, 28-30, 39-41` — the condition looks only at properties. With `provider=claude, fallback=ollama` but no `ANTHROPIC_API_KEY`, the ClientConfig degenerates to a bare Ollama client (chain length 1) yet a probe bean is still registered and pings every 30 s, flipping a latch nobody reads. Harmless traffic; the plan's "체인 길이 1 → 탐색 빈 0" claim holds only for an *empty* fallback. Add `and '${ANTHROPIC_API_KEY:}' != ''` when the primary is claude, or accept.

**M-2.** `provider/OllamaProviderProbe.java:50-57` — exact match vs Ollama's implicit `:latest`. `OLLAMA_MODEL=qwen2.5` works for `/api/chat` but `/api/tags` lists `qwen2.5:latest` → probe reports missing → fallback silently off forever with one WARN per ≤30 min. Current values all carry tags. Normalise `name.contains(":") ? name : name + ":latest"` before the (still exact) comparison — RF2 is preserved.

**M-3.** `provider/OllamaProviderProbe.java:55` and `OllamaModelUnavailableException` javadoc — "is not loaded" is misleading: `/api/tags` lists *pulled/available* models; `/api/ps` lists loaded ones. Say "is not available on this Ollama".

**M-4.** `provider/ProviderFailures.java:43-48` — the 404→TRANSIENT rule is keyed on `RestClientResponseException`, not on the provider; the comment "RestClient 를 쓰는 provider 는 Ollama 뿐" is true today (verified) but unguarded. Consider a pinning test or a dedicated exception type so a future RestClient-based provider's 404 doesn't silently become an availability failure.

**M-5.** Dev-mode behaviour change not called out: with `provider=ollama` and empty fallback (chain 1) the Ollama connect timeout drops 60 s→3 s. Spec §3.1-6 intends this for all three clients, but spec §4's "체인 길이 1 → 동작 변화 0" is slightly overstated. Doc nit only.

**M-6.** No ai-svc doc enumerates the provider keys (`PROVIDER_PROBE_INTERVAL` wasn't documented either), so nothing is inconsistent, but a one-line mention of `PROVIDER_LIVENESS_INTERVAL` and `*_OLLAMA_CONNECT_TIMEOUT` in the PR body / gitops runbook would help operators.

**M-7.** Worktree has an untracked `.omc/` directory (tool artefact, not in the diff). Make sure it is not `git add`-ed with the PR.

### Declined to judge

- SDK `maxRetries=2` on non-idempotent `POST /v1/messages` (possible duplicate billing when a response is lost) — identical to the pre-fallback state that the spec defines as the parity baseline.
- SpEL in `@ConditionalOnExpression` embedding property values in string literals (a `'` inside `*_FALLBACK` would break startup) — unrealistic input; pattern pre-exists in `ClaudeProbeConfig`.
- `ProviderProbeScheduler` active in the `test` profile / `List<ProviderProbe>` injection with zero probes — pre-existing.
- In-process latch (replicas=1 assumption) — pre-existing and documented in `ProviderLatch`.
- Removal of `LLM_ALL_PROVIDERS_BLOCKED` as an externally visible code: community-svc only persists `error_code` (`CommunityAiAnswer.setErrorCode`) and never branches on it; retention has no `@ExceptionHandler` for `ReEngagementGenerationException` (500 before and after); `ReviewService` catches `TransientReviewException` the same way. Net external change = a stored string value, and it is spec-intended (§3.1-1 ③).
- Vestigial `@Value` annotations on the retained 5-arg Ollama constructors (not beans) — pre-existing.
- A slow-dripping `/api/tags` body exceeding 5 s total despite `HttpURLConnection`'s per-read timeout — theoretical.
- `OllamaProviderProbe` relying on Jackson 3's default tolerance of unknown JSON properties — covered by the mock test, whose payload includes extra fields.

### Rulings I disagree with (from the ledger)

None outright.
- Pre-flight ruling 1 (`withOptions` copy instead of a second bean): **agree** — bytecode confirms `Builder.from` restores `originalHttpClient`; same observable contract, fewer resources.
- Pre-flight ruling 2 (500 instead of 529 in the parity test): **agree** — both ≥500 are SDK-retried.
- Task 8 / Task 9 rulings (expected code `LLM_FAILED`; catch `RestClientResponseException`): **agree** — I verified no consumer branches on the old code; the Task 9 catch type is an artefact of the raw-throwing stub, which the ledger already notes (production Claude wraps into `ReEngagementGenerationException`).
- Task 13 ruling (defer push/PR until after this review): fine.

### Recommendations

1. Fix **I-1** (skip `recordFailure` for the forced primary attempt, or no-op while open) and **I-3** (`spring.task.scheduling.pool.size: 2`) before merge; add the two tests sketched above.
2. Decide **I-2** explicitly — either add it to spec §3.3 as residual risk #3 (with the ~1–3 % window estimate) or implement the liveness-keeps-it-open variant. Do not leave it undocumented.
3. Fold **M-2/M-3** into the same fix pass if cheap; the rest can be follow-ups.
4. Re-run the full suite with the Postgres env after fixes and re-record the XML sum (baseline 414/0/0/skipped 1) before `gh pr create`.

### Assessment — Ready to merge? **With fixes.**

The design and the parity proof are solid and the implementation follows the plan faithfully; the two Important behavioural gaps are spec-level omissions (backoff inflation under all-blocked, recurring expiry window) rather than coding errors, but their effect contradicts the stated success criterion, and together with the one-line scheduler-pool fix they are small enough to land before the PR.