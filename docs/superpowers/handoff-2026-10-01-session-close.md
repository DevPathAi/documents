# 핸드오프 — 2026-10-01 세션 마무리 (S3 운영 반영 → landing 결함 수정 → AI provider 폴백 구현)

> 앞 문서: `handoff-2026-10-01-s3-release-promoted.md`(PR #192). 이 세션은 그 뒤로 두 가지 후속 과제를
> 순서대로 처리했다. **다음 세션 첫 동작은 §4.**

## 0. 한 줄 요약

| # | 작업 | 상태 |
|---|---|---|
| 1 | S3 릴리스 `ms-20260930-s3-web-redesign-r3` 운영 반영 | **완료** (앞 핸드오프 #192) |
| 2 | gitops landing 프로브 전파 경쟁 결함 수정 | **완료 · develop 머지** `3f5ff8f` (PR #165, 선행 sync PR #164) |
| 3 | AI provider 폴백 — 스펙 보정 + 계획 A | **완료 · develop 머지** `f50da54` (PR #193) |
| 4 | AI provider 폴백 — 계획 A 구현 (Task 1~10) | **구현·푸시 완료, PR #83 열림. ⚠ 최종 리뷰 미처리 → 머지 전 필수** |

---

## 1. gitops landing 프로브 수정 (완료)

`ms-20260930-s3-web-redesign-r3` 의 `landing-last` 가 실패했던 원인을 고쳤다.

**결함**: 배포 성공 `00:33:44.740Z` → marker 프로브 실패 `00:33:45.914Z` = **1.17초**. `cloudflare_pages.py` 의
`_probe_marker` 에 재시도·백오프가 없고, `urllib` 의 `HTTPError ⊂ OSError` 라 **404 가 연결 실패와 같은
메시지로 뭉개졌다**(`:393` 의 non-200 분기에 도달조차 못 한다).

**수정**: `_probe` · `_probe_api` · `_probe_marker` 가 전파성 실패를 **6회 / 합계 30초**(1·2·4·8·15s) 예산 안에서
재시도하고 세 실패를 구분한다 — `not served yet (HTTP 404)` · `could not connect` ·
`unexpected HTTP 308`(종단, 첫 시도에 즉시 실패). 원래 메시지 접두사는 보존했다.

**선행 작업이 필요했다**: gitops `develop` 이 `main` 보다 **39커밋 뒤처져** 있었고 그중 10건이 캠페인 중 main 에
직접 들어간 실제 수정이라, 그대로 릴리스하면 **되돌아갔다**. sync PR #164 로 해소(충돌 2파일은 전부 main 쪽 채택
— `verify_promotion_chain.py` 는 develop 고유 줄 0 = 엄격한 상위집합).

검증: `python -m unittest discover -s tests/release` → **369 OK**(기준선 362 + 신규 7).

★`HTTPError` 는 `addinfourl` → `tempfile._TemporaryFileWrapper` 를 상속한다 — 테스트에서 **닫지 않으면**
`__del__` 이 `ResourceWarning` 을 낸다. `fp=None` 이어도 `io.BytesIO()` 라 tempfile 때문이 아니다★

**아직 develop 에만 있다** — 운영(main) 반영은 다음 릴리스.

---

## 2. AI provider 폴백 — 스펙 §7 선행 실측 (완료)

스펙의 사전 과제 5건을 실측했다. **설계(§2~§5)는 전부 유지. §6.1 모델 계획만 불가능하다.**

| § | 결과 |
|---|---|
| 7-3 SDK 예외 | ✅ 가정보다 좋다 — `anthropic-java:2.34.0`, 타입 계층이 이미 `ClaudeAiReviewClient:52-60` 에 매핑돼 있다 |
| 7-4 메트릭 | ✅ actuator 있음 → Micrometer 가용. 기존 커스텀 메트릭 0개라 맞출 규칙이 없다 |
| 7-5 멘토 테스트 | ✅ `FallbackMentorClientTest` 등 4개 존재 |
| 7-1 모델 | ❌ **차단** — CPU Ollama 에 `qwen2.5:3b`·`nomic-embed-text` 뿐. `qwen2.5-coder:7b`·`qwen2.5:7b` **둘 다 없다** |
| 7-2 여유 | ❌ **차단** — PVC 가 local-path 라 노드 `/dev/root`(49G) 위, **7.8G 여유(84% 사용)** vs 7b 두 개 ≈9.4GB. 파드 메모리 limit **5Gi**, 노드 가용 **3.9Gi** |

**사용자 결정**: 배선만 먼저, **모델은 별도 결정**. `*_FALLBACK` 기본 빈 문자열 = 운영 불변, gitops 미변경.
모델 선택지 — ① 3b 로 낮춘다(`qwen2.5:3b` 기보유 + review 는 `qwen2.5-coder:3b` ~1.9GB) ② 디스크·메모리 확보해 7b 유지 ③ 노드 상향.

### ★스펙이 놓친 구조적 사실 2건★

**① 세 기능의 `AnthropicClient` 빈이 `provider == "claude"` 조건이었다.** 스펙 §2.5 의 「키가 없으면 Claude 빈이
안 생긴다」는 **멘토에만** 해당한다. 그래서 `ollama` 주 + `claude` 상향이 **원리적으로 불가능**했다.
멘토가 답을 갖고 있었다 — `@ConditionalOnExpression("'${ANTHROPIC_API_KEY:}' != ''")`.

**② 세 기능은 `fromEnv()` 라 SDK 기본 재시도를 쓴다.** 멘토만 `maxRetries(0)` 이다. SDK 내부 재시도는
**429 를 삼키고 실패를 느리게 만들어** 래치 판정을 왜곡한다.

---

## 3. AI provider 폴백 — 계획 A 구현 (Task 1~10, PR #83)

브랜치 `feat/ai-provider-fallback-core` · base `f8e9b59`(origin/develop) → head **`5f4d3f4`** · 11커밋 · 42파일 · +2275/-114.

| Task | 커밋 | 내용 |
|---|---|---|
| 1 | `b0e7279` | `ProviderChain.ordered`/`orderedMap` — 멘토의 순서 함수를 제네릭으로 올리고 멘토를 그 위로 |
| 2 | `35270ad` | `ProviderLatch`·`FailureKind` — `Clock` 주입, 기한·지수증가 결정적 검증 |
| 3 | `a1c2f54` | `ProviderFailures` — 상태코드 일괄 분류 |
| 4 | `d3d3ed8` | **Claude 빈을 키 존재 조건으로** + `maxRetries(0)` |
| 5 | `0863e7f` | review 체인 (`FallbackAiReviewClient`·`ReviewClientConfig`) |
| 6 | `c53fb76` | community-seed 체인 |
| 7 | `574adb9` | **retention Ollama 클라이언트**(유일한 신규 구현) + 체인 |
| 8 | `b7afe88` | 배경 복구 탐색 + `application.yml` 폴백 키 |
| 9 | `7955f21` | mock 회귀 잠금 |
| 10 | `5f4d3f4` | Claude 탐색기 3개 (출력 1토큰) |

검증: `./gradlew test` → **339 tests · 0 failures · 1 skipped** (베이스라인 267 → 신규 72).

### ★로컬 테스트에는 pgvector 가 필요하다★

`origin/develop` 베이스라인이 **267중 81 실패**였다 — 전부 Spring 컨텍스트 로드 실패, 근본 원인은 로컬 Postgres 부재.
사용자 승인으로 Docker 를 띄워 세웠고, **두 함정을 실측했다**:

1. **`postgres:16-alpine` 으로는 안 된다** — Flyway `V202606181006__learning_path_schema.sql` 가
   `extension "vector"` 를 요구한다(멘토 RAG 임베딩). 원인이 `Connection refused` → `extension "vector" is not available` 로 전진했다.
2. **컨테이너 초기화 중 `pg_isready` 가 임시 서버에 먼저 OK 를 준다** — 바로 `psql` 하면
   `the database system is shutting down`. 준비 판정은 `psql -tAc "select 1;"` 로 한다.

재현 명령 (다음 세션에서 그대로 쓸 수 있다):

```bash
docker run -d --name devpath-test-pg \
  -e POSTGRES_DB=devpath -e POSTGRES_USER=devpath -e POSTGRES_PASSWORD=localdev \
  -p 5432:5432 pgvector/pgvector:pg16 -c max_connections=300
# 준비 대기: psql -tAc "select 1;" 가 성공할 때까지
```

`max_connections=300` 은 `application-test.yml` 주석이 경고한 "too many clients"(53300) 예방이다
(테스트는 컨텍스트당 hikari pool 4 로 제한한다).

### 실행 중 내린 Ruling (전부 원장에 기록)

작업 원장: **워크트리 안** `.superpowers/sdd/2026-10-01-ai-provider-fallback-core/progress.md` (git-ignored).

1. **계획 작성 시 읽은 체크아웃이 develop 보다 59커밋 뒤처져 있었다** — develop 기준 재실측 결과 근거(SDK 2.34.0·actuator·설정 키)가 전부 일치해 계획 수정은 불필요
2. **Task 8 의 `@EnableScheduling` 추가는 하지 않는다** — `AiApplication.java:10` 에 이미 있다
3. **`dueProbes()` 순서 단언 → 집합 동등성** — 계획의 테스트가 계획 자신의 `ConcurrentHashMap` 이 보장할 수 없는 순서를 단언했다(실측 실패)
4. ★**SDK 분류를 타입별 `instanceof` → 상태코드 일괄로**★ — `AnthropicServiceException` 이 `statusCode()`·`headers()` 를 노출하는 추상 기반임을 javap 로 실측. 계획이 다루지 않은 404·422 까지 덮고 **Claude 의 429 에서 `Retry-After` 를 읽게 됐다**
5. **SDK 예외는 빌더로만 생성되고 `InternalServerException` 은 `statusCode` 필수** · Java 는 자기 참조 cause 를 금지 → 2단 순환 + 깊이 상한 16
6. **`ApplicationContextRunner` 에 `ApplicationConversionService` 를 보충** — Boot 앱에는 있는 것이라 구현을 바꾸지 않았다
7. **retention Ollama 테스트 입력을 실제 `ReEngagementInput` 으로** — 실제 PromptBuilder 를 쓰므로 null 불가
8. ★**계획의 mock 회귀 잠금이 공허했다**★ — `providerName()` 은 호출 전이면 **체인의 첫 provider** 를 돌려주므로 `[ollama, mock]` 에서 `"ollama"` 가 나와 통과한다. **위반을 주입해 통과하는 것을 실측 확인**한 뒤 조립 결과의 구체 타입 단언으로 바꾸고, 다시 위반 주입 → FAILED / 원복 → SUCCESSFUL 을 확인했다
9. **Task 10 을 Mockito 딥스텁 → 실제 SDK + MockWebServer 로** — mock 동작이 아니라 실제 와이어 형식(`/v1/messages`, `"max_tokens":1`)과 실제 SDK 예외 타입을 검증한다. 덕분에 429 → `RateLimitException`+`Retry-After 42s`, 401 → `UnauthorizedException` 이 분류기로 그대로 흐르는 것을 확인했다

---

## 4. ⚠ 다음 세션 첫 동작 — 최종 리뷰 **결과 처리**(리뷰는 끝났다)

**최종 리뷰를 받았다 — 판정 `With fixes`.** 본문은 워크트리 안
`.superpowers/sdd/2026-10-01-ai-provider-fallback-core/final-review.md`(394줄, git-ignored).
★리뷰어 최종 메시지가 한 줄이라 본문이 유실될 뻔했고 재개해 파일로 받았다★

### ★Critical 1건 (C1) — 컨트롤러가 직접 실측해 확인했다. 이것은 **계획의 결함**이다(구현은 계획에 충실했다)★

**provider 기록이 폴백이 일어난 바로 그 경우에 틀린다** → 스펙 성공 기준 #3·#4 미달. 세 결함이 한 메커니즘에:

- **(a) `ReviewService.java:91-92` 가 `providerName()` 을 `review()` 보다 먼저 읽는다**(실측 확인).
  체인 ≥2 에서 첫 요청은 체인 머리를, 이후 요청은 **직전 요청의** provider 를 기록한다.
  테스트가 못 잡은 이유: `FallbackAiReviewClientTest:146-155` 가 **운영과 반대 순서**로 호출하고,
  기존 review Spring 테스트 12개는 `providerName()` 을 상수로 스텁한다.
- **(b) `ThreadLocal` 을 어디서도 `remove()` 하지 않는다**(세 Fallback 클라이언트 모두). 풀 워커에서 값이
  살아남고 `CommunitySeedService:50` 은 **실패 경로**에서 그 값을 발행한다 → 관여하지 않은 provider 를 실패로 지목.
- **(c) 래퍼는 체인 키(소문자)를 저장하는데 구현체는 대문자**(`CLAUDE`/`OLLAMA`)를 돌려준다(실측 확인).
  `ai_code_reviews.provider` 에 두 표기가 섞여 집계가 깨진다.

★**멘토의 `FallbackMentorClient` 가 세 가지를 이미 다 해결해 두었는데 계획이 따르지 않았다**★ —
`:27,:34,:38` `SERVED.remove()` · `:48` `d.providerName()` 저장 · `:62-65` read-once-and-clear ·
`:32-40,:49` `providerSelected` 콜백으로 **thread-local 없이** 호출자에게 제때 알린다.

**수정 방향(한 변경, 세 효과)**: 세 Fallback 클라이언트가 `e.getValue().providerName()` 을 저장하고
entry·`finally` 에서 비운다. 그리고 `ReviewService` 의 순서를 바꾸거나 — **더 낫게, 멘토처럼** — 선택을
콜백/결과로 보고해 thread-local 을 없앤다. 세 `reportsTheProviderThatActuallyServed` 를 대문자 단언으로
바꾸고 I5 의 통합 테스트를 더한다.

### Important 5건

| # | 내용 |
|---|---|
| I1 | `ProviderLatch` 가변 상태를 동기화·`volatile` 없이 읽는다 |
| I2 | 기한 만료가 **차단 해제와 탐색 예약을 동시에** 해서 결국 사용자 요청이 탐색을 문다(§3.1 의도 약화) |
| I3 | `lastBackoff` 를 `RATE_LIMIT`·`TRANSIENT` 가 공유해 서로의 증가를 오염시킨다 |
| I4 | `maxRetries(0)` 의 비용은 지금 내고 이득은 나중에 걷는다 |
| I5 | **스펙 §9 의 통합 항목이 ruling 없이 계획에서 빠졌고, 그게 바로 C1(a)를 잡을 테스트다** |

**Minor 12건 · Declined to judge 11줄** — 전부 `final-review.md` 에.

### 다음 세션이 할 일

1. **재채점** — reviewer 의 severity 는 조언이다. 효과로 다시 매긴다(Declined to judge 11줄도 각각 ruling 한다).
2. **Critical/Important 만 한 번의 수정 패스** — 각 수정은 재현 테스트 **RED→GREEN** + 전체 스위트 녹색.
   Minor 는 원장에 deferred 로 남기고 사용자에게 보고한다. 두 번째 수정 패스는 없다.
3. 그 뒤 `superpowers:finishing-a-development-branch` 로 **PR #83 머지**.

**리뷰 결과를 반영하기 전에 머지하지 말 것.**

### (참고) 이 세션이 수정 패스를 하지 않은 이유

사용자 지시로 30분 내 마무리·큰 작업 이관. 리뷰는 받았고 기록했으나 수정은 다음 세션 몫이다.

### 그다음 (순서대로)

1. **모델 결정** (§2 의 ①②③) — 정해지면 `*_FALLBACK` env 를 gitops 에 넣는다. ★`rendered_config_sha256` 이 바뀌어 release id 재발급을 부른다★
2. **계획 B** — 스펙 §10 관측 메트릭 · §5 review 재생성 엔드포인트
3. **gitops landing 수정의 운영 반영** — 다음 릴리스 캠페인에 실린다

## 5. 환경 상태

- 로컬 Postgres 컨테이너 `devpath-test-pg`(pgvector/pgvector:pg16, 5432) **실행 중**. 다음 세션에 그대로 쓸 수 있고, 불필요하면 `docker rm -f devpath-test-pg`.
- 워크트리 `D:/workspace/dpa/.worktrees/ai-svc-provider-fallback` **유지** — 원장과 리뷰 패키지가 그 안에 있다(git-ignored `.superpowers/`). 다음 세션이 여기서 이어받는다.
- 레포 작업트리에 미커밋 작업 없음.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
