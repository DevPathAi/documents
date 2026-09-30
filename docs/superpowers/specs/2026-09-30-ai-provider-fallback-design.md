# AI provider 폴백 설계 — Claude 를 못 쓸 때 Ollama 가 이어받는다

작성 2026-09-30. 대상 레포 **`devpath-ai-svc` 단독**. 결정은 사용자와 이 문서의 브레인스토밍에서 내렸다.

## 0. 의도 (합의된 이해)

**사용자가 원한 것**: Claude API 토큰이 없어서 문제가 생길 때 그 기능이 멈추지 않고 Ollama 가 이어받는다.

**착수 전 실측이 전제를 바꿨다.** 사용자가 이름 댄 세 기능 중 둘은 Claude 를 쓰지 않고, Claude 전용인 곳은 이름 대지 않은 세 곳이었다. 아래 §1 이 그 표다. 이 문서는 **실측된 Claude 전용 지점**을 대상으로 한다.

**성공 기준**
1. `ANTHROPIC_API_KEY` 가 없어도 review·community-seed·retention 이 **동작한다**(오류가 아니라 Ollama 산출물).
2. 크레딧이 소진돼도 그 상태가 지속되는 동안 **매 요청이 Claude 실패 지연을 물지 않는다**.
3. 저장되는 산출물은 **어느 provider 가 만들었는지 기록**되고, 나중에 Claude 로 다시 만들 수 있다.
4. 운영이 「왜 이 산출물이 Ollama 로 만들어졌는가」를 **사후에 답할 수 있다**.
5. 우리 버그(400)나 출력 검증 실패가 **전체의 Claude 를 끊지 않는다**.

## 1. 실측 — 무엇이 실제로 Claude 전용인가

| 사용자가 말한 기능 | 실측 | 이 스펙의 대상 |
|---|---|---|
| **학습경로 생성** | `devpath-learning-svc` 에 Claude 호출이 **없다**. `PathGenerationConfig`·`PathGenerationJobService` 가 이미 Ollama 전용이고, gitops 는 `OLLAMA_PATH_BASE_URL` 로 GPU 노드에 보낸다 | ❌ 대상 아님 |
| **진단** | learning-svc 에 Claude 호출이 없다. 문항은 오프라인 Ollama 생성 뱅크다 | ❌ 대상 아님 |
| **멘토** | `MENTOR_PROVIDER=ollama` · `MENTOR_FALLBACK=claude` — **이미 Ollama 우선 + Claude 폴백**이다. gitops 주석이 이유를 적어 뒀다: 「Anthropic 크레딧 소진 시 멘토 전체가 멈추는 것을 막는다」 | ⚠️ 결함만 |

**실제 Claude 전용 세 곳**(전부 `devpath-ai-svc`):

| 설정 | 무엇 | 인터페이스 | Claude | Ollama | Mock |
|---|---|---|---|---|---|
| `REVIEW_PROVIDER=claude` | 실습 코드 리뷰 (저장) | `AiReviewClient` | ✓ | **✓ 있다** | ✓ |
| `COMMUNITY_SEED_PROVIDER=claude` | 커뮤니티 시드 답변 (저장·공개) | `AiSeedClient` | ✓ | **✓ 있다** | — |
| `RETENTION_PROVIDER=claude` | 재참여 알림 문구 (일회성) | `ReEngagementSuggestionClient` | ✓ | **✗ 없다** | ✓ |

**따라서 신규 구현은 하나뿐이다** — retention 의 Ollama 클라이언트. 나머지 둘은 구현이 이미 있고 조립만 없다.

### 왜 「설정값 한 줄」이 아닌가

review·seed·retention 은 멘토와 **다른 방식**으로 provider 를 고른다:

```java
@Component
@ConditionalOnProperty(name = "devpath.review.provider", havingValue = "ollama")
public class OllamaAiReviewClient implements AiReviewClient
```

**한 번에 구현체 하나만 빈으로 생성된다.** 다른 구현은 존재조차 하지 않으므로 이 구조로는 체인이 원리적으로 불가능하다. 반면 멘토는 `MentorClientConfig` 가 모든 구현을 `available` 맵에 담고 순서를 조립한다. 이 스펙의 「배선」은 **세 기능을 멘토 방식으로 옮기는 리팩터**다.

## 2. 구조

새 패키지 `ai.devpath.aigw.provider` — 작은 두 조각만 둔다.

### 2.1 `ProviderChain`

`MentorClientConfig.orderedChain(provider, fallbackCsv, available)` 을 **그대로 올린다.** 이미 `static` 순수 함수라 옮기는 위험이 낮고, 멘토는 계속 이것을 부른다(호출부 한 줄 변경).

계약: 주 provider 를 앞에, `fallback` CSV 를 순서대로 뒤에 두고, `available` 에 없는 이름과 중복을 제거한 리스트를 돌려준다.

### 2.2 `ProviderLatch`

`(feature, provider)` 단위 인메모리 상태. `Clock` 을 주입받는다(테스트 결정성).

- `boolean isOpen(feature, provider)` — 열려 있으면 체인이 그 provider 를 **건너뛴다**
- `void recordFailure(feature, provider, FailureKind, Duration retryAfterOrNull)`
- `void recordSuccess(feature, provider)` — 닫는다
- `Set<Probe> dueProbes()` — 기한이 지난 항목(배경 작업이 소비)

**전제: `replicas: 1`.** gitops `apps/devpath-ai-svc/base/deployment.yaml` 이 `replicas: 1` 이라 공유 저장소가 필요 없다. **스케일아웃하면 파드마다 래치가 갈라져 일관성이 깨진다** — 그때는 공유 저장소(Redis 등)로 옮겨야 한다. 이 사실을 코드 주석과 §11(범위 밖)에 남긴다.

### 2.3 제네릭 `FallbackClient<T>` 는 만들지 않는다

네 인터페이스의 모양이 다르다 — 멘토는 스트리밍(`stream(input, sink, providerSelected)`), review 는 요청/응답(`review(input)`), retention 은 배치. 제네릭으로 감싸면 기능마다 함수형 어댑터가 필요해 코드량이 같아지고, 더 나쁘게는 **멘토의 「토큰 방출 뒤 전환 불가」 규칙이 review 에 잘못 적용될 위험**이 생긴다. 대신 기능별로 20줄짜리 얇은 `Fallback*Client` 를 두어 각자의 실패 의미를 명시한다.

### 2.4 소유 경계

- `ProviderChain` = **순서**만
- `ProviderLatch` = **상태**만
- 각 기능 = 프롬프트 작성, 출력 파싱·검증, 「이 출력을 받아도 되는가」 판정, 자기 예외 타입

## 3. 실패 판정과 래치 의미론

용어: 래치가 **열림(open)** 이면 그 provider 를 **건너뛴다**(차단). **닫힘(closed)** 이면 정상 사용한다.

**가용성 실패만 래치를 연다. 내용 실패는 열지 않는다.** 이것이 이 설계의 핵심 안전장치다.

**키 부재와 잘못된 키는 다른 경로다.** `ANTHROPIC_API_KEY` 가 **없으면** Claude 빈이 생성되지 않아 `available` 에 아예 들어가지 않는다 — 래치가 관여하지 않고 체인이 처음부터 Ollama 로 간다(설정 수준 해결, 멘토가 이미 그렇게 동작한다). 래치가 필요한 것은 **키가 있는데 못 쓰는** 경우다: 회수된 키(401), 소진(429), 장애(5xx).

| 종류 | `FailureKind` | 래치 | 기한 | 이유 |
|---|---|---|---|---|
| 401·403 | `auth` | 즉시 열림 | 30분 | 키가 틀렸거나 회수됐다. 재시도가 의미 없다 |
| 429 | `rate_limit` | 즉시 열림 | `retry-after` 헤더, 없으면 5분 → 연속 시 ×2, 상한 1시간 | 소진과 단기 제한이 같은 코드로 온다. 헤더가 있으면 그것을 믿는다 |
| 5xx·연결·타임아웃 | `transient` | **연속 3회** 후 | 1분 → 연속 시 ×2, 상한 30분 | 일시적일 수 있다. 한 번으로 끊지 않는다. 연속 횟수는 `(feature, provider)` 단위이고 성공 한 번으로 0 이 된다 |
| 400 | `bad_request` | **열지 않음** | — | 우리 버그다. 한 사용자의 잘못된 프롬프트가 전체의 Claude 를 끊으면 안 된다 |
| 파싱·스키마·정답키 모양 실패 | `output_invalid` | **열지 않음** | — | 가용성 문제가 아니다. 그 요청만 다음 provider 로 넘긴다 |

`bad_request`·`output_invalid` 는 래치를 건드리지 않고 **그 요청에 한해** 체인의 다음으로 넘어간다.

### 3.1 복구 탐색은 배경 작업으로

기한이 지나면 **사용자 요청을 탐색에 쓰지 않는다.** 배경 스케줄러가 `dueProbes()` 를 읽어 최소 프롬프트(출력 1토큰)로 ping 한다. 성공하면 닫고, 실패하면 기한을 늘린다.

*이유*: 사용자 요청으로 half-open 탐색을 하면 실패할 때 그 사용자가 지연을 물고, 멘토는 스트리밍이라 특히 아프다. 최소 프롬프트의 크레딧 비용은 무시할 수준이고, 크레딧이 소진된 상태라면 즉시 429 로 떨어져 비용이 아예 없다.

### 3.2 스트리밍 — 추가 지연을 사지 않는다

`FallbackMentorClient` 의 계약은 「어떤 delegate 가 토큰을 하나라도 방출한 뒤 실패하면 폴백하지 않고 예외를 전파한다」 — 구조적 제약이다.

**래치가 흔한 경우를 이미 없앤다.** 소진 상태면 래치가 열려 있어 그 provider 를 애초에 시도하지 않으므로 중간 실패가 생기지 않는다. 남는 것은 「래치가 닫혀 있는데 이 요청에서 처음 실패」인 드문 경우뿐이고, 그때만 첫 토큰 전이면 폴백·후면 오류다.

매 요청에 버퍼링이나 사전 ping 을 붙이지 **않는다**. 대신 이 잔여 한계를 알려진 한계로 명시한다.

> 방향 주의: 멘토는 Ollama 우선이므로 이 위험은 *Ollama* 가 중간에 죽고 Claude 로 넘어가려 할 때 생긴다 — 흔히 생각하는 방향의 반대다.

## 4. 기능별 정책

| 기능 | 산출물 | 정책 |
|---|---|---|
| **mentor** | 대화(비저장) | 즉시 이어받음. **이미 Ollama 우선**이라 Claude 는 폴백이 아니라 *상향*이다 |
| **review** | 저장 — `ai_code_review.provider` 컬럼이 **이미 있다** | 이어받고 provider 기록. 나중에 Claude 로 재생성 가능(§5) |
| **community-seed** | 저장 — 공개 커뮤니티 답변 | 같음 |
| **retention** | 알림 문구(일회성) | 즉시 이어받음 |

### 4.1 새로 만드는 체인에는 `mock` 을 넣지 않는다

세 기능 모두 `Mock*Client` 가 존재하지만(`MockAiReviewClient`·`MockSeedClient`·`MockReEngagementClient`) **체인에 넣지 않는다.** 가짜 코드 리뷰가 사용자 기록에 영구히 남거나 가짜 문구가 알림으로 발송되는 것은 **실패보다 나쁘다.** 체인이 비면 기능의 기존 예외를 던진다.

멘토의 `mock` 안전망(`chain.isEmpty() → mock`)은 **유지한다.** 원칙이 달라서가 아니라 **이 스펙이 멘토의 기존 동작을 바꾸지 않기 때문**이다 — 멘토의 mock 을 없애는 것은 별개 판단이다.

**회귀 잠금**: `mock` 이 review·community-seed·retention 체인에 들어가지 않음을 단언하는 테스트를 둔다(설정 실수 방지).

### 4.2 멘토 provider 순서는 바꾸지 않는다

`MENTOR_PROVIDER=ollama` 는 gitops 주석에 이유가 적힌 의도된 선택이다. 순서를 되돌리는 것(품질 좋은 Claude 를 주로)은 **품질 판단**이고, 멘토 Ollama 가 `qwen2.5:3b` 인 현실과 묶여 있다. 별도 과제(§8).

## 5. 재생성

**백엔드 엔드포인트만. UI 는 이 스펙의 범위 밖이다.**

- **`review` 에 대해서만** 「Claude 로 다시 만들기」 엔드포인트를 둔다.
- **community-seed 는 제외한다.** 시드 답변은 공개 커뮤니티 콘텐츠이고, 이미 읽히고 추천·댓글이 붙었을 수 있는 글을 다시 쓰는 것은 모더레이션 판단이 필요하다 — 기술 문제가 아니다. `provider` 기록만 남기고 재생성은 범위 밖으로 둔다.
- 호출 시 래치를 확인한다 — Claude 래치가 **열려 있으면**(= 차단 상태) **즉시 거절**하고 이유를 돌려준다. 폴백으로 또 Ollama 를 만들어 주지 않는다 — 재생성의 목적이 상향이므로 Ollama 재생성은 무의미하다.
- 성공하면 `provider` 를 갱신한다. 실패해도 **기존 산출물을 지우지 않는다.**
- 자동 재생성(Claude 복구 시 배치)은 **하지 않는다** — 사용자가 이미 읽은 내용을 예고 없이 바꾸고 비용이 예측 불가하다.

## 6. 배선 표면

| 기능 | 현재 env | 추가 env | 제안 값 |
|---|---|---|---|
| mentor | `MENTOR_PROVIDER=ollama` · `MENTOR_FALLBACK=claude` | — | **변경 없음** |
| review | `REVIEW_PROVIDER=claude` | `REVIEW_FALLBACK` | `ollama` |
| community-seed | `COMMUNITY_SEED_PROVIDER=claude` | `COMMUNITY_SEED_FALLBACK` | `ollama` |
| retention | `RETENTION_PROVIDER=claude` | `RETENTION_FALLBACK` | `ollama` |

`application.yml` 에 `${*_FALLBACK:}` 기본 빈 문자열로 두어 **설정하지 않으면 현재 동작과 같다**(안전한 기본값).

### 6.1 모델

| 기능 | Ollama 모델 | 상태 |
|---|---|---|
| review | `qwen2.5-coder:7b` (`devpath.review.ollama-model` 기본값) | **코드 특화 모델.** 운영에서 Ollama 로 돌아 본 적이 없으니 클러스터에 pull 됐는지 **확인이 선행 조건**이다(§7) |
| community-seed | **`qwen2.5:7b`** (`devpath.community-seed.ollama-model` 기본값 — 실측) | 운영에서 Ollama 로 돌아 본 적이 없으니 pull 확인이 선행 조건(§7) |
| retention | **`qwen2.5:7b`** — 새로 pull | 사용자 결정: 「더 큰 모델을 새로 pull」. 3b 보다 한 단계 위이고 **community-seed 와 같은 모델이라 pull 한 번이 두 기능을 덮는다.** 메모리의 7b 실패 기록은 *문항 생성 + 정답키*라는 훨씬 어려운 구조화 과제였고, 재참여 문구는 짧은 한국어 텍스트다. 품질이 부족하면 14b 로 올린다 |
| mentor | `qwen2.5:3b` | 변경 없음(§4.2) |

## 7. 사전 과제 (구현 착수 전에 실측)

1. **클러스터 CPU Ollama 의 모델 목록** — 필요한 것은 **둘**이다: `qwen2.5-coder:7b`(review)와 `qwen2.5:7b`(community-seed + retention). 없으면 그 폴백이 런타임 실패가 된다. 이미 있는 것은 `qwen2.5:3b`(멘토·생성). 접근은 노드 SSH + `sudo kubectl`(로컬 kubeconfig 는 인증서에 EIP 가 없어 TLS 실패).
2. **pull + 리소스 여유** — CPU Ollama 에 모델 둘을 더할 때의 디스크·메모리 여유. GPU Ollama(`ollama-gpu`)는 스팟이고 학습경로 전용이므로 **여기에 얹지 않는다**.
3. **Anthropic SDK 의 예외 표면** — 429 에서 `retry-after` 를 어떤 타입으로 노출하는지, 401/400 을 어떤 예외로 던지는지. §3 의 분류 표가 이것에 의존한다.
4. **ai-svc 메트릭 스택** — Micrometer/actuator 가 이미 있는지, 메트릭 이름 규칙이 있는지.
5. **멘토의 기존 테스트** — 「방출 후 실패는 전파」 계약에 테스트가 이미 있는지(있으면 재사용, 없으면 보강).

## 8. 릴리스 파이프라인에 걸리는 것

**★ `*_FALLBACK` env 추가는 `ai_release_eval_config.rendered_config_sha256` 을 바꾼다.**

그 값은 gitops `base_sha` 에서 `kustomize build apps/devpath-ai-svc/base` 를 렌더한 sha256 이다. 지난 캠페인(`ms-20260923-…`)에서 startupProbe 추가가 이 해시를 바꿨고, candidate 가 `candidate does not bind exact ET9 release inputs` 로 **실패해 release id 를 `-r3` 로 재발급**했다.

따라서 이 변경을 릴리스에 태울 때:
- candidate spec 의 `ai_release_eval_config.rendered_config_sha256` 을 **새로 렌더한 값으로** 실어야 한다.
- 증거 producer 적격이 아티팩트 이름(release id) 기준이므로, 이 실수를 하면 **같은 id 를 재사용할 수 없다.**

## 9. 테스트 전략

- **`ProviderChain.ordered`** — 순수 함수. 멘토의 기존 표 기반 테스트를 그대로 옮겨 재사용.
- **`ProviderLatch`** — `Clock` 주입으로 기한·지수 증가·탐색 기한을 결정적으로 검증. **실시간 `sleep` 금지.**
- **실패 분류** — §3 의 표를 그대로 단언: 401→`auth`(열림) · 429+`retry-after`→`rate_limit`(기한=헤더) · 429 무헤더→5분 · 5xx 2회→닫힘 유지 · 5xx 3회→열림 · 400→**열지 않음** · 출력 검증 실패→**열지 않음**.
- **기능별 `Fallback*Client`** — 주 실패 시 다음으로 넘어가고 결과가 같은 계약을 만족하는지. 체인이 전부 실패하면 기능의 기존 예외를 던지는지.
- **멘토 스트리밍** — 토큰 방출 **전** 실패는 폴백, **후** 실패는 전파.
- **회귀 잠금** — `mock` 이 새 체인 셋에 들어가지 않음(§4.1).
- **재생성** — Claude 래치가 열려 있으면 거절하고, 실패해도 기존 산출물을 지우지 않음.
- **통합** — Ollama·Claude 를 둘 다 스텁으로 두고 네 기능의 체인을 한 번씩.

## 10. 관측

`ai_code_review.provider` 컬럼은 **결과**만 알려주고 **이유**를 알려주지 않는다. 「왜 이 리뷰가 Ollama 로 만들어졌나」를 사후에 답할 수 있어야 한다.

- `..._provider_served_total{feature, provider}` — 카운터
- `..._provider_latch_open{feature, provider}` — 게이지 0/1
- `..._provider_failure_total{feature, provider, kind}` — kind = `auth`·`rate_limit`·`transient`·`bad_request`·`output_invalid`
- 래치가 열리고 닫힐 때 **이유와 기한을 담은 구조화 로그 한 줄**

정확한 이름은 §7-4 의 기존 규칙에 맞춘다.

## 11. 범위 밖

- **진단·학습경로** — Claude 를 쓰지 않는다(§1). 학습경로의 실제 위험은 GPU 스팟 회수이고, 그때 멈추는 것은 비동기 작업뿐이라는 것이 gitops 주석의 판단이다.
- **멘토 provider 순서 변경** — 품질 판단이고 Ollama 모델 개선 과제에 묶인다(§4.2).
- **재생성 UI** — frontend 별도 작업(§5).
- **community-seed 재생성** — 공개 콘텐츠를 다시 쓰는 것은 모더레이션 판단이다(§5).
- **래치 공유 저장소** — `replicas: 1` 전제(§2.2). 스케일아웃이 이 전제를 깬다.
- **Ollama 모델 추가 학습** — 별도 프로젝트. 이 설계의 **수용 기준을 정한다**: review·retention 을 Ollama 로 넘길 수 있는지는 품질이 결정하고, 멘토를 Claude 우선으로 되돌릴지도 그렇다.
- **ET9 평가 증거 계약 변경** — §8 은 해시를 새로 싣는 것까지다. 증거 계약 자체를 바꾸지 않는다.
