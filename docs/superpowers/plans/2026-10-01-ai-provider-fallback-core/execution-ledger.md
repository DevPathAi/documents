# SDD ledger — plan: D:/workspace/dpa/documents/docs/superpowers/plans/2026-10-01-ai-provider-fallback-core.md

Spec: `documents` `origin/develop:docs/superpowers/specs/2026-09-30-ai-provider-fallback-design.md`
(사본: `.superpowers/sdd/2026-10-01-ai-provider-fallback-core/spec.md`) — 2026-10-01 보정 포함.
Worktree: `D:/workspace/dpa/.worktrees/ai-svc-provider-fallback` · branch `feat/ai-provider-fallback-core`
BASE at start: `f8e9b59` (origin/develop) → `55d290d` (chore: ignore the superpowers workspace)
Executor: inline (superpowers:executing-plans), Native 선택 by user 2026-10-01.

## Pre-flight

계획이 근거로 삼은 소스를 develop 기준으로 재확인했다. **Java 9개 파일은 develop 과 동일**
(`MentorClientConfig` · `MentorClaudeClientConfig` · `ClaudeClientConfig` · `ClaudeAiReviewClient` ·
`OllamaAiReviewClient` · `CommunitySeedClaudeConfig` · `OllamaSeedClient` ·
`RetentionClaudeClientConfig` · `ClaudeReEngagementClient`).

Pre-flight: Ruling: 계획을 쓸 때 읽은 체크아웃(`feat/evidence-reader-migration`)이 develop 보다
**59커밋 뒤처져** 있었고 `application.yml`·`build.gradle.kts` 가 달랐다 — develop 기준으로 재실측해
`anthropic-java:2.34.0` · `spring-boot-starter-actuator` · 세 기능 설정 키 구조가 **모두 계획과 일치**함을
확인했다. develop 에는 `review.ollama-model` 이 이미 명시돼 있고 `retention.ollama-model` 은 없다
(Task 8 이 추가한다). — 계획 수정 불필요 — 틀렸다면 Task 8 의 yml 편집이 중복 키를 만든다.

### 공유 인터페이스 (Interfaces 블록 대조)

| 생산 | 소비 | 대조 결과 |
|---|---|---|
| Task 1 `ProviderChain.ordered` / `orderedMap(String,String,Map<String,T>) → LinkedHashMap<String,T>` | Task 5·6·7 | 일치 — 세 설정 모두 `LinkedHashMap<String,X> chain = ProviderChain.orderedMap(provider, fallbackCsv, available)` |
| Task 2 `FailureKind` · `ProviderLatch(Clock)` · `isOpen` · `recordFailure(f,p,kind,Duration)` · `recordSuccess` · `dueProbes()→List<Probe>` | Task 3(enum) · 5·6·7(래치) · 8(dueProbes) | 일치 |
| Task 3 `ProviderFailures.Classified(FailureKind,Duration)` · `classify(Throwable)` | Task 5·6·7·8 | 일치 — 네 곳 모두 `c.kind()` · `c.retryAfter()` |
| Task 4 빈 `anthropicClient`·`communitySeedAnthropicClient`·`retentionAnthropicClient` | Task 5·6·7(`ObjectProvider`) · 10(`ClaudeProbeConfig`) | 일치 — `@Qualifier` 이름 동일 |
| Task 5 `ProviderLatchConfig` 빈 `Clock providerClock` · `ProviderLatch providerLatch` | Task 6·7·8·9 | 일치 |
| Task 8 `ProviderProbe` 인터페이스 · `ProviderProbeScheduler(ProviderLatch, List<ProviderProbe>)` | Task 10(구현 3개) | 일치 |

Pre-flight: Ruling: Task 8 Step 4 의 「`@EnableScheduling` 이 없으면 `ProviderLatchConfig` 에 붙인다」는
**붙이지 않는다** — `AiApplication.java:10` 에 이미 있다(`OutboxRelayScheduler` 가 `@Scheduled` 를 쓴다).
— 중복 선언은 무해하지만 불필요하다 — 틀렸다면 스케줄러가 안 돌아 래치가 기한 만료로만 닫힌다.

Pre-flight: Ruling: Task 5 의 `providerClock` 빈은 기존 `Clock` `@Bean` 과 충돌하지 않는다 —
`src/main/java` 에 `Clock` `@Bean` 선언이 없다. — 충돌하면 Task 5 Step 7 의 컨텍스트 테스트에서 드러난다.

`provider` 패키지는 신규다(기존 패키지: `community` · `config` · `mentor` · `ollama` · `outbox` ·
`retention` · `review`) — 이름 충돌 없음.

## Baseline

1차 `./gradlew test` on `55d290d`: **267 tests, 81 failed, 1 skipped** — 전부 Spring 컨텍스트 로드 실패.
근본 원인 실측: `PSQLException: Connection refused` → Flyway → `BeanCreationException`. **로컬 Postgres 부재.**

Baseline: Ruling: 사용자 승인(2026-10-01)으로 로컬 Postgres 를 띄워 **전체 스위트 녹색 게이트를 유지**한다 —
Task 4·5 가 바꾸는 빈 배선(`AnthropicClient` 조건 · `@ConditionalOnProperty` → 팩토리)이 바로 그 81개
컨텍스트 테스트가 검증하는 영역이라, DB 없이는 회귀를 확인할 수 없다 —
틀렸다면(= DB 없이 진행) 빈 배선 회귀가 CI 까지 숨는다.

로컬 DB 준비 (워크트리 밖 side effect, 사용자 승인):
- Docker Desktop 기동 → daemon server **29.6.2**
- ★`postgres:16-alpine` 로는 안 된다★ — Flyway `V202606181006__learning_path_schema.sql` 가
  `extension "vector"` 를 요구한다(멘토 RAG 임베딩). 2차 실행에서 원인이
  `Connection refused` → `extension "vector" is not available` 로 **전진**했다.
- `pgvector/pgvector:pg16` 로 교체 → `vector` 확장 설치 확인
- 컨테이너 `devpath-test-pg` · 5432 · db/user `devpath` · pw `localdev` ·
  `-c max_connections=300` (`application-test.yml` 주석이 경고한 "too many clients"(53300) 예방;
  테스트는 컨텍스트당 hikari pool 4 로 제한한다)
- ★컨테이너 기동 중 `pg_isready` 가 **초기화용 임시 서버에 먼저 OK** 를 돌려준다 —
  바로 `psql` 하면 `the database system is shutting down`. 준비 판정은 `psql -tAc "select 1;"` 로 한다★

3차 `./gradlew test --rerun-tasks`: **BUILD SUCCESSFUL** — 베이스라인 깨끗. 게이트는 「전체 스위트 녹색」 유지.

## Tasks
Task 1: complete (commits 55d290d..b0e7279, tests: ./gradlew test --tests ai.devpath.aigw.provider.* --tests ai.devpath.aigw.mentor.* --console=plain → BUILD SUCCESSFUL, 8 new + mentor suite)
Task 2: Ruling: 계획의 `dueProbesReportsOnlyEntriesWhoseDeadlinePassed` 가 `List` 순서를 단언했는데
계획 자신의 구현(`ConcurrentHashMap`)은 반복 순서를 보장하지 않는다 — 실측 실패:
expected `[review, community-seed]` / actual `[community-seed, review]` (둘 다 존재, 순서만 다름).
스펙은 `dueProbes()` 순서에 아무 요구가 없고 스케줄러는 각 항목을 개별 ping 하므로, 테스트를
**집합 동등성 + 개수 단언**으로 바꿨다(「due 인 것만, 중복 없이 전부」라는 의미는 보존).
구현에 결정적 순서를 넣는 쪽은 택하지 않았다 — 스펙이 요구하지 않는 의미를 추가하게 된다.
— 틀렸다면 로그에서 탐색 순서를 예측할 수 없다(기능 영향 없음).
Task 2: complete (commits b0e7279..35270ad, tests: ./gradlew test --tests ai.devpath.aigw.provider.* --console=plain → Consider enabling configuration cache to speed up this build: https://docs.gradle.org/9.5.1/userguide/configuration_cache_enabling.html)
Task 3: Ruling: 계획은 SDK 예외를 **타입별 `instanceof`** 로 분류하라고 했다. 실측(javap, jar
`anthropic-java-core-2.34.0`)에서 `AnthropicServiceException` 이 `public abstract int statusCode()` 와
`public abstract Headers headers()` 를 노출하는 **추상 기반**임을 확인해, **상태코드 하나로 일괄 분류**하도록
바꿨다 — Ollama(`RestClientResponseException`)와 같은 규칙을 쓰고, 계획이 다루지 않은
`NotFoundException`·`UnprocessableEntityException`·`UnexpectedStatusCodeException` 까지 자동으로 덮는다.
부수 효과로 **Claude 의 429 에서도 `Retry-After` 를 읽는다**(계획의 테스트는 null 을 단언했는데, 그건
근거 없는 제약이었다). — 틀렸다면 SDK 가 상태코드를 안 싣는 예외를 추가했을 때 `TRANSIENT` 로 떨어진다(안전한 쪽).

Task 3: Ruling: 계획의 `treatsAnUnknownAnthropicFailureAsTransientRatherThanSilentlyIgnoringIt` 가
`UnauthorizedException(String)` 류 생성자를 가정했다. 실측: 이 예외들은 `builder().headers(..).body(..)`
로만 만들고, `InternalServerException` 은 5xx 전반을 덮어 **`statusCode` 가 필수**다
(`Check.checkRequired`). 테스트를 빌더 형태로 맞췄다. — 단언의 의미는 바꾸지 않았다.

Task 3: Ruling: 계획의 `unwrapsACauseChain` 옆에 넣은 자기 참조 순환 테스트가 성립하지 않았다 —
Java 의 `initCause(this)` 는 `IllegalArgumentException: Self-causation not permitted` 를 던진다.
**a → b → a 2단 순환**(구성 가능)으로 바꾸고, 구현에 `MAX_CAUSE_DEPTH = 16` 깊이 상한을 뒀다
(자기 참조 가드만으로는 2단 순환을 못 막는다). 순환 뒤에 분류 가능한 cause 가 있는 경우도 테스트에 추가했다.
— 틀렸다면 아주 깊은(16단 초과) cause 체인의 끝에 있는 429 를 놓친다(실무에서 보기 어렵다).
Task 3: complete (commits 35270ad..a1c2f54, tests: ./gradlew test --tests ai.devpath.aigw.provider.* --console=plain → Consider enabling configuration cache to speed up this build: https://docs.gradle.org/9.5.1/userguide/configuration_cache_enabling.html)
Task 4: Ruling: `ApplicationContextRunner` 는 Boot 앱과 달리 `ApplicationConversionService` 를
등록하지 않아 `@Value("...:PT60S") Duration` 변환이 `UnsatisfiedDependencyException` 으로 깨졌다.
**실제 앱에는 있는 것**이므로(기존 `OllamaAiReviewClient` 가 같은 패턴으로 동작한다) 구현을 바꾸지 않고
테스트에만 `withInitializer(... setConversionService(ApplicationConversionService.getSharedInstance()))`
로 보충했다. — 틀렸다면 운영에서 timeout 프로퍼티가 변환되지 않는다(전체 스위트 녹색이 그렇지 않음을 보였다).
Task 4: complete (commits a1c2f54..d3d3ed8, tests: ./gradlew test --console=plain → Consider enabling configuration cache to speed up this build: https://docs.gradle.org/9.5.1/userguide/configuration_cache_enabling.html)
Task 5: complete (commits d3d3ed8..0863e7f, tests: ./gradlew test --console=plain → Consider enabling configuration cache to speed up this build: https://docs.gradle.org/9.5.1/userguide/configuration_cache_enabling.html)
Task 6: complete (commits 0863e7f..c53fb76, tests: ./gradlew test --console=plain → Consider enabling configuration cache to speed up this build: https://docs.gradle.org/9.5.1/userguide/configuration_cache_enabling.html)
Task 7: complete (commits c53fb76..574adb9, tests: ./gradlew test --console=plain → Consider enabling configuration cache to speed up this build: https://docs.gradle.org/9.5.1/userguide/configuration_cache_enabling.html)
Task 8: complete (commits 574adb9..b7afe88, tests: ./gradlew test --console=plain → Consider enabling configuration cache to speed up this build: https://docs.gradle.org/9.5.1/userguide/configuration_cache_enabling.html)
Task 7: Ruling: `OllamaReEngagementClientTest` 가 입력으로 `null` 을 넘겼는데 이 테스트는 **실제**
`ReEngagementPromptBuilder` 를 쓰므로 `userContent(input)` 에서 NPE 가 났다(스텁을 쓰는 Fallback 테스트와
다르다). 실제 `ReEngagementInput(7L, 2026-09-20T00:00:00Z, 11, "Spring Boot 기초 3/12주")` 로 바꿨다.
— 단언의 의미는 바꾸지 않았다.

Task 9: Ruling: ★계획의 회귀 잠금이 **공허했다**★ — `providerName()` 으로 mock 혼입을 검사했는데,
`Fallback*Client.providerName()` 은 호출 전이면 **체인의 첫 provider** 를 돌려주므로 `[ollama, mock]` 에서
`"ollama"` 가 나와 통과한다(게다가 체인 키는 소문자인데 비교값은 `"MOCK"` 이었다). **실측으로 확인했다**:
`available` 맵에 mock 을 주입해도 테스트가 BUILD SUCCESSFUL 이었다.
단언을 **조립 결과의 구체 타입**(`isExactlyInstanceOf`)으로 바꿨다 — 키가 없으면 Claude 빈이 없으니
mock 이 제외되면 체인 길이 1 이고 결과는 `OllamaAiReviewClient` 자체여야 하고, 섞이면
`FallbackAiReviewClient` 가 된다. **다시 위반을 주입해 FAILED 를, 원복해 SUCCESSFUL 을 확인**했다.
— 틀렸다면 체인 길이가 1이 아닌 다른 조립(예: Claude 키가 있는 CI)에서 이 테스트가 깨진다(키를 주지 않아 고정).
Task 9: complete (commits b7afe88..7955f21, tests: ./gradlew test --tests ai.devpath.aigw.provider.* --console=plain → Consider enabling configuration cache to speed up this build: https://docs.gradle.org/9.5.1/userguide/configuration_cache_enabling.html)
Task 10: Ruling: 계획은 `AnthropicClient` 를 Mockito **딥스텁**으로 감싸 `MessageCreateParams` 를
캡처하라고 했다. 대신 **실제 SDK 클라이언트를 MockWebServer 에 붙였다** — TDD 스킬이 「mock 동작이 아니라
실제 동작을 단언하라」고 하고, 이 테스트의 핵심은 탐색이 보내는 **실제 와이어 형식**(`/v1/messages`,
`"max_tokens":1`)과 실패가 올라오는 **실제 SDK 예외 타입**(스케줄러가 분류할 바로 그것)이다.
덕분에 429 → `RateLimitException` + `Retry-After 42s`, 401 → `UnauthorizedException` 이
`ProviderFailures` 로 그대로 흐르는 것을 한 테스트에서 확인했다 — 딥스텁으로는 알 수 없는 사실이다.
— 틀렸다면 MockWebServer 기동 비용(테스트당 수십 ms)을 더 낸다.
Task 10: complete (commits 7955f21..5f4d3f4, tests: ./gradlew test --console=plain → Consider enabling configuration cache to speed up this build: https://docs.gradle.org/9.5.1/userguide/configuration_cache_enabling.html)

## 최종 리뷰 (2026-10-01) — **With fixes**. 수정 패스는 다음 세션.

리뷰 본문: `final-review.md`(394줄). 리뷰어는 가장 유능한 모델·신선한 컨텍스트·읽기 전용으로 돌았다.
★최종 메시지가 한 줄로 와서 본문이 유실될 뻔했고, 재개해 파일로 받았다 — [[feedback-subagent-report-to-file]] 재확인★

**Critical 1건 (C1) — 컨트롤러가 직접 실측해 확인했다. 제 계획의 결함이다(구현은 계획에 충실했다).**

provider 기록이 **폴백이 일어난 바로 그 경우에 틀린다** → 스펙 성공 기준 #3·#4 미달. 세 결함이 한 메커니즘에:
- (a) `ReviewService.java:91-92` 가 **`providerName()` 을 `review()` 보다 먼저** 읽는다(실측 확인).
  체인 ≥2 에서 첫 요청은 체인 머리를, 이후 요청은 **직전 요청의** provider 를 기록한다.
  테스트가 못 잡은 이유: `FallbackAiReviewClientTest:146-155` 가 **운영과 반대 순서**로 호출하고,
  기존 review Spring 테스트 12개는 `providerName()` 을 상수로 스텁한다.
- (b) `ThreadLocal` 을 **어디서도 `remove()` 하지 않는다**(세 Fallback 클라이언트 모두). 풀 워커에서 값이 살아남고,
  `CommunitySeedService:50` 은 **실패 경로**에서 그 값을 발행한다 → 관여하지 않은 provider 를 실패로 지목.
- (c) 래퍼는 **체인 키(소문자)** 를 저장하는데 구현체는 **대문자**(`CLAUDE`/`OLLAMA`)를 돌려준다(실측 확인).
  `ai_code_reviews.provider` 컬럼에 두 표기가 섞여 집계가 깨진다.

★**멘토의 `FallbackMentorClient` 가 세 가지를 이미 다 해결해 두었는데 계획이 따르지 않았다**★ —
`:27,:34,:38` `SERVED.remove()` · `:48` `d.providerName()`(구현체의 대문자) 저장 · `:62-65` read-once-and-clear ·
`:32-40,:49` `providerSelected` 콜백으로 **thread-local 없이** 호출자에게 제때 알린다.

수정 방향(한 변경, 세 효과): 세 Fallback 클라이언트가 `e.getValue().providerName()` 을 저장하고 entry·`finally`
에서 비운다. 그리고 `ReviewService` 의 순서를 바꾸거나 — **더 낫게, 멘토처럼** — 선택을 콜백/결과로 보고해
thread-local 을 없앤다. 세 `reportsTheProviderThatActuallyServed` 를 대문자 단언으로 바꾸고 I5 의 통합 테스트를 더한다.

**Important 5건**: I1 `ProviderLatch` 가변 상태를 동기화·`volatile` 없이 읽는다 · I2 기한 만료가 차단 해제와
탐색 예약을 동시에 해서 **결국 사용자 요청이 탐색을 문다**(§3.1 의 의도를 약화) · I3 `lastBackoff` 를
`RATE_LIMIT`·`TRANSIENT` 가 공유해 서로의 증가를 오염시킨다 · I4 `maxRetries(0)` 의 비용은 지금 내고 이득은
나중에 걷는다 · I5 **스펙 §9 의 통합 항목이 ruling 없이 계획에서 빠졌고, 그게 바로 C1(a)를 잡을 테스트다**.

**Minor 12건 · Declined to judge 11줄** — 전부 `final-review.md` 에 있다. 다음 세션에서 재채점한다.

Final: 이 세션은 수정 패스를 **수행하지 않았다**(사용자 지시: 큰 작업은 다음 세션 이관, 30분 내 마무리).
다음 세션이 재채점 → Critical/Important 한 번의 수정 패스(각 수정 RED→GREEN + 전체 스위트) → Minor 는 deferred → 머지.


---

## 수정 패스 (2026-10-01, 다음 세션) — 재채점 결과와 ruling

리뷰 수용 전에 **세 Critical 주장과 다섯 Important 를 컨트롤러가 직접 코드에서 확인**했다.
전부 사실이었다. 추가로 두 가지를 실측해 결정의 근거로 삼았다:

- **SDK 기본값**(anthropic-java-core 2.34.0): `maxRetries = 2`(javap `ClientOptions$Builder.<init>` 의
  `iconst_2; putfield maxRetries`), 기본 timeout `connect=PT1M · read/write/request=PT10M`
  (리플렉션으로 `Timeout.default()` 실행). 브랜치는 이걸 `maxRetries(0)` + 전부 60초로 바꿨다.
- **탐색기 적용 범위**: `ClaudeProbeConfig` 가 만드는 `ProviderProbe` 는 **Claude 세 개뿐**이고
  그나마 `ANTHROPIC_API_KEY` 가 있을 때만 생긴다. **Ollama 용 탐색기는 없다.**

### C1 — 수용, 단 「콜백」이 아니라 「멘토의 ThreadLocal 수명 관리」를 택했다

Ruling: 리뷰어는 "reorder, 또는 **더 낫게** 콜백/결과로 보고해 thread-local 제거"를 제안했다.
콜백은 `AiReviewClient`·`AiSeedClient`·`ReEngagementSuggestionClient` 세 인터페이스와 그 구현 7개,
그리고 `providerName()` 을 스텁하는 기존 테스트 12개를 모두 건드린다 — 머지 직전 수정 패스의 범위를
넘는다. 대신 **멘토가 이미 쓰는 수명 관리**를 그대로 가져왔다: 진입 시 `remove()` ·
`delegate.providerName()`(구현체의 대문자)를 **호출 전에** 기록 · `providerName()` 은 read-once-and-clear.
`ReviewService` 는 순서를 뒤집었다. — 틀렸다면 thread-local 이 남아 콜백 리팩터가 언젠가 필요하다.

「호출 **전에**」 기록하는 것은 멘토와 같은 자리다(`FallbackMentorClient:48-49`). 덕분에 전부 실패해도
`providerName()` 이 **마지막으로 시도한** provider 를 말한다 — `CommunitySeedService:50` 의 실패 경로가
정확해진다. 아무도 시도되지 않았으면(전부 차단) 체인 머리의 **구현체 이름**을 돌려준다.

### I5 — 수용, 모양만 바꿨다

Ruling: 리뷰어는 `ApplicationContextRunner`/`@SpringBootTest` 를 제안했지만, 계약의 핵심은
「**서비스**를 실제 `Fallback*Client` 로 관통시킨다」이지 Spring 컨텍스트가 아니다. 실제 체인 +
mock 영속/발행으로 같은 계약을 더 빠르게 못박았다(`*ProviderRecordingTest` 3개, 6 테스트).
— 틀렸다면 빈 조립 단계의 결함은 여전히 `MockExclusionTest` 만 본다(그건 이미 조립을 본다).

### I1 — 수용. 네 필드 전부 `volatile`

가시성 결함은 결정적으로 재현할 수 없어(JMM 은 낡은 값을 **허용**할 뿐 강제하지 않는다)
**컴파일된 필드 수식어**를 리플렉션으로 단언했다. 소스 텍스트 검사가 아니다.
Ruling: 모니터 밖에서 실제로 읽히는 것은 `openUntil` 하나지만 넷 다 붙였다 — 비용이 없고,
앞으로 어떤 필드가 모니터 밖으로 새도 안전하다. — 틀렸다면 불필요한 메모리 배리어 세 개를 낸다.

### I2 — **옵션 (i) 채택**: 탐색 실패는 항상 기한을 해소한다. 「탐색 확인 전까지 계속 차단」은 **기각**

Ruling: 리뷰어의 "better still"(차단과 탐색 예약을 분리해 탐색이 확인할 때까지 `isOpen` 유지)은
**이 코드베이스에서 Ollama 를 영구 차단한다** — 위 실측대로 탐색기가 Claude 에만 있어서,
Ollama 래치가 한 번 열리면 닫아 줄 주체가 없다. 시간 기반 만료가 탐색기 없는 provider 의
**유일한 회복 경로**다(`ClaudeProbeConfig` 의 javadoc 도 이 의존을 이미 적고 있다).

그래서 만료는 그대로 두고, `recordProbeFailure` 를 새로 두어 **탐색 실패는 반드시 항목을 해소**하게 했다:
- TRANSIENT 의 「3연속」 게이트를 **적용하지 않는다** — 그 규칙은 사용자에게 보이는 딸꾹질 한 번으로
  provider 를 끊지 않으려는 것이고 탐색은 사용자 트래픽이 아니다. (리뷰어 지적 ②: 지속 장애 중
  래치가 ~3틱 동안 사실상 닫혀 사용자가 60초 타임아웃을 무는 문제가 사라진다.)
- 내용 실패(BAD_REQUEST·OUTPUT_INVALID)는 **탐색을 포기**하고 `openUntil` 을 지운다. (지적 ③:
  영구 past-due + 1분마다 무의미한 핑 + "stays open" 거짓 로그가 사라진다.) 백오프 사다리와 연속
  카운터는 **보존** — 가용성 이력인데 내용 실패는 그에 대해 아무 말도 하지 않는다.

남는 것(지적 ①): 만료와 다음 틱 사이 ≤1 탐색주기(기본 1분) 동안 사용자 요청이 죽은 provider 로 갈 수
있다. 탐색기 없는 provider 에게는 이게 회복 경로 자체이므로 **의도적으로 남긴다**.
— 틀렸다면 Claude 전용으로 「탐색 적용 범위」를 래치에 알려 주는 한 단계가 더 필요하다.

### I3 — 수용. 사다리를 종류별로 분리

`lastBackoff` 하나 → `rateLimitBackoff` · `transientBackoff`. 양방향 오염을 테스트로 못박았고
(429 뒤 transient 가 1분, transient 뒤 헤더 없는 429 가 5분), 비어 있던 transient 의
1→2분 배증과 30분 상한, 그리고 rate_limit 1시간 상한의 **아래쪽** 단언(M3)을 채웠다.

### I4 — **결정: 재시도 예산은 체인을 따라간다**(끄지 않는 쪽이 기본)

Ruling: `maxRetries(0)` 의 근거(429 를 삼켜 래치 판정을 왜곡)는 **체인이 있을 때만** 성립한다.
보정 §C 가 `*_FALLBACK` 을 빈 값으로 출하하므로 지금 운영은 체인 길이 1 = 래퍼도 래치도 없다 —
그 상태에서 재시도를 끄는 것은 이득 없는 순손실이다. 노출 정도를 확인했다:
**community-seed 는 Kafka 재시도가 없다**(`CommunitySeedService` 가 예외를 잡아 `publishFailed`
로 끝낸다 → 한 번의 503 이 그 질문의 시드 답변을 영구히 잃는다), **retention 도 없다**(동기 HTTP),
review 만 `releaseForRetry` 가 받는다. 그래서 `ClaudeClients.maxRetriesFor` 가
`ProviderChain.requestedCount(provider, fallback) >= 2` 일 때만 0 으로 내린다.
값은 **MockWebServer 가 센 실제 요청 횟수**로 못박았다(체인 없음 3회 / 체인 있음 1회).

타임아웃 60초는 **유지**한다 — SDK 기본 10분은 결정된 값이 아니라 기본값이고, 그동안 Kafka 리스와
동기 HTTP 요청이 10분간 붙들린다. 멘토가 같은 자리에서 이미 50초를 쓴다(`MentorTimeoutPolicy`).
— 틀렸다면 60초를 넘는 정상 리뷰 생성이 실패한다(`devpath.*.claude-timeout` 로 올릴 수 있다).

### Minor — 넷 처리, 여덟 deferred

처리: **M1**(기능 키를 `ProviderFeatures` 공유 상수로 — 래퍼와 탐색기의 오타가 복구 탐색을 조용히
끄는 것을 막는다) · **M2**(소스 텍스트 검사를 지우고 `ClaudeRetryBudgetTest` 의 행동 검증으로 대체) ·
**M6**(`.gitignore` CRLF→LF, diff 75줄 → 3줄) · **M7**(`new` 로 조립되는 세 Claude 클라이언트의 죽은
`@Qualifier`/`@Value` 와 Mock 두 개의 이중 빈 줄 제거).

Deferred: M3 는 I3 에 흡수됐고, M4·M5·M8·M9·M10·M11·M12 는 머지 후 별도. 그중 **M11**(ruling 원장이
gitignore 된 `.superpowers/` 에만 산다)은 이 파일을 `documents` 로 옮겨 닫는다.

### 검증

각 수정 RED→GREEN 을 눈으로 확인했다. C1 은 신규 6 테스트가 먼저 **9건 FAILED**(래퍼 3 + 서비스 6)
→ 수정 후 전부 통과. I1·I2·I3 는 `recordProbeFailure` 부재로 **컴파일 FAILED** → 구현 후 통과.
전체 스위트 **339 → 352 tests, 0 failures, 1 skipped**(신규 13).
