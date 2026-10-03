# AI provider 폴백 — 가용성을 보는 체인 설계 (2026-10-03)

> 대상: `devpath-ai-svc` 세 기능(review · community-seed · retention). 선행 설계: `2026-09-30-ai-provider-fallback-design.md`(#83).
> 계기: gitops 폴백 publisher 독립 리뷰 M1(`plans/2026-10-03-gitops-main-ai-fallback-probe-via-publisher/review-2026-10-03/REPORT.md`).
> 사용자 결정(2026-10-03): 성공 기준 = 「성공률 + 지연 모두」, 접근 = A(가용성 인지 체인). 설계 1~3절 각각 승인.

## 1. 문제

2026-10-03 부터 운영에서 세 기능의 폴백이 켜져 있다(gitops `a97a1754`: `*_FALLBACK=ollama`, GPU Ollama `qwen2.5:7b`).
폴백을 켜면 Claude SDK 재시도가 **2 → 0** 이 된다 — `ClaudeClients.maxRetriesFor`(`ClaudeClients.java:53`)가
`ProviderChain.requestedCount(provider, fallback) >= 2 ? 0 : 2` 이고, `requestedCount` 는 가용성을 보지 않는다.
재시도를 끈 이유는 #83 보정 ②(SDK 재시도가 429 를 삼켜 래치 판정을 왜곡)로 정당하지만, **폴백이 실제로 쓸 수 없을 때도** 끈다.

GPU 는 스팟이다(2026-09-08 회수 뒤 23일 방치 선례). GPU 가 없거나 7b 가 없을 때:

- Claude 일시 장애 1회 → 재시도 없이 죽은 Ollama 로 넘어가 → 실패. community-seed 는 그 질문의 시드 답변을 영구히 잃고,
  retention 은 동기 HTTP 라 그대로 실패한다(코드 주석 `ClaudeClients.java` 자체가 이 순손실을 적고 있다).
- Ollama 404(모델 없음)는 `ProviderFailures` 가 `OUTPUT_INVALID`(`:66`)로 분류해 래치를 열지 않고, review 는
  `PermanentReviewException("PARSE_FAILED")`(`OllamaAiReviewClient.java:72`)로 **영구 실패**한다(원래는 Kafka 재시도).
- Claude 429 로 래치가 열리고 Ollama 도 죽어 있으면, 세 래퍼는 Claude 도 부르지 않고 「전부 차단」으로 실패한다
  (`FallbackAiReviewClient.java:57` · `FallbackAiSeedClient.java:57` · `FallbackReEngagementClient.java:57`).
  폴백을 끈 상태(체인 길이 1)에는 래치가 없어 매번 Claude 를 부른다.
- Ollama 클라이언트의 연결 타임아웃이 읽기와 같은 60초다(`OllamaAiReviewClient.java:32` · `OllamaSeedClient.java:28` ·
  `OllamaReEngagementClient.java:26`). 노드가 갑자기 사라져 엔드포인트가 아직 남아 있는 동안 요청마다 최대 60초를 기다린다.
- Ollama 용 `ProviderProbe` 가 없다 — Ollama 래치가 열리면 닫아 줄 탐색기가 없어 기한 뒤 첫 사용자 요청이 탐색을 떠안는다.

## 2. 목표 · 성공 기준

**GPU 또는 7b 가 쓸 수 없을 때, 세 기능의 성공률과 지연이 폴백을 끈 상태(체인 길이 1)와 같다.**
**폴백이 쓸 수 있을 때는 #83 의 동작(Claude 재시도 0 → 빠른 폴백, 래치 정확성)을 유지한다.**

비목표: 멘토(Ollama 1차 · Claude 폴백, 이미 재시도 0 을 명시한 다른 계약) · 폴백 품질 · 7b 콜드 지연(측정 44.8초).

## 3. 설계

### 3.1 구성 요소

1. **`ProviderAttemptPlan`**(provider 패키지, 신규, 순수 함수). 입력 = 체인 순서(provider 이름 목록)와 래치 조회 함수.
   출력 = 이번 요청의 시도 목록 `List<Attempt(name, mode)>`, `mode ∈ {FAST, LAST_RESORT}`.
   - 래치가 열린 provider 는 건너뛴다.
   - 각 시도에 대해 **그 뒤에 래치가 닫힌 provider 가 하나라도 남았으면 `FAST`, 없으면 `LAST_RESORT`.**
   - **래치가 닫힌 provider 가 하나도 없으면 1순위 provider 를 `LAST_RESORT` 로 1회 시도**한다(래치 무시).
   세 래퍼에 복제된 루프를 이 함수로 모은다.
2. **Claude 클라이언트 2벌.** `ClaudeClients.build` 가 재시도 횟수를 명시 인자로 받는다. 요청 체인 길이가 2 이상인 기능은
   `FAST`(maxRetries 0)와 `LAST_RESORT`(maxRetries 2 = SDK 기본) 두 `AnthropicClient` 를 만든다. 체인 길이 1 이면 지금처럼
   하나(2)만 만든다. 기존 빈 이름(`anthropicClient` · `communitySeedAnthropicClient` · `retentionAnthropicClient`)은 `FAST` 로
   남겨 `ClaudeProbeConfig` 를 바꾸지 않는다.
3. **세 래퍼**(`FallbackAiReviewClient` · `FallbackAiSeedClient` · `FallbackReEngagementClient`)는 `ProviderAttemptPlan` 을 따른다.
   provider 마다 `FAST` 구현체와 선택적 `LAST_RESORT` 구현체를 받는다(Claude 만 둘이 다르고, Ollama 는 같은 인스턴스).
   기능별 클라이언트 인터페이스(`AiReviewClient` 등)는 바꾸지 않는다. 실패·성공 기록은 지금처럼 래치에 남긴다.
   단, 전부 막혀 래치를 무시하고 부른 1순위 시도(규칙 ③)의 **실패는 기록하지 않는다** — 이미 열린 래치에 다시 기록하면
   사다리가 요청마다 자라(5→10→…60분) Ollama 가 돌아온 뒤에도 회복된 Claude 를 그만큼 건너뛴다. 성공은 기록한다
   (최종 리뷰 I-1, 2026-10-03).
4. **`OllamaProviderProbe`**(신규, `ProviderProbe` 구현). `GET {baseUrl}/api/tags` 를 연결 3초·읽기 5초로 호출하고, 응답 모델 목록에
   설정 모델(`devpath.<feature>.ollama-model`)이 없으면 실패로 던진다. 예외는 `ProviderFailures` 가 분류할 수 있는 형태 그대로 둔다.
   세 기능 각각, **그 기능의 fallback CSV 에 `ollama` 가 있고 1순위가 아닐 때만** 빈을 만든다.
5. **생존 탐색.** `ProviderProbe` 에 `default boolean livenessTarget() { return false; }` 를 두고 `OllamaProviderProbe` 만 `true`.
   `ProviderProbeScheduler` 에 `runLivenessProbes()`(`devpath.provider.liveness-interval`, 기본 `PT30S`, 기동 즉시 1회)를 더해
   **래치가 닫힌** 생존 대상만 핑한다. 실패 → `latch.recordProbeFailure(...)`(즉시 열림). 성공 → 기록하지 않는다(사용자 요청
   실패 카운터 보존). 열린 래치의 회복은 기존 `runDueProbes()` 가 같은 `OllamaProviderProbe` 로 닫는다.
6. **연결 타임아웃 분리.** 세 기능의 Ollama 클라이언트에 `devpath.<feature>.ollama-connect-timeout`(기본 `PT3S`)을 두고
   읽기 타임아웃(`…-ollama-timeout`, 기본 60초)과 분리한다.
7. **분류 보정.** Ollama 404 를 가용성 실패(`TRANSIENT`)로 분류한다(Claude 404 는 그대로 `OUTPUT_INVALID`).
   review 의 Ollama 404 는 `TransientReviewException` 으로 바꿔 Kafka 재시도를 받게 한다.

### 3.2 요청 흐름

| 상황 | 시도 | 폴백을 끈 상태와의 관계 |
|---|---|---|
| GPU 정상 | Claude `FAST` → 실패 시 Ollama | #83 과 같다 |
| GPU 회수 감지(생존 탐색이 Ollama 래치를 엶) | Claude `LAST_RESORT` | **같다** |
| 7b 없음 | 생존 탐색이 모델 부재로 래치를 엶 → Claude `LAST_RESORT` | **같다** · 모델 복귀 시 `runDueProbes` 가 닫는다 |
| 전부 차단(Claude 429 + Ollama 사망) | Claude `LAST_RESORT` 1회(래치 무시) | **같다**(지금은 Claude 도 부르지 않고 실패) |
| Claude 만 차단, Ollama 정상 | Ollama | 폴백이 제 역할을 한다 |
| GPU 가 막 죽고 감지 전(≤ 30초) | Claude `FAST` → Ollama | Claude 성공이면 무영향 · Claude 도 실패면 Ollama 가 즉시 거부되거나 ≤ 3초 뒤 실패 |

생존 탐색이 한 번 잘못 실패하면 Ollama 래치가 1분(`TRANSIENT_BASE`) 열린다 — 그동안 Claude 가 재시도 2를 받으니 잃는 것은
「폴백을 잠시 안 씀」뿐이다(안전한 쪽).

### 3.3 잔여 위험 (수용)

1. 감지 전 ≤ 30초 구간에 Claude 와 GPU 가 **동시에** 실패한 요청은 재시도 없이 실패한다.
2. Claude 가 429 로 차단되고 Ollama 가 살아 있다가 그 요청에서 실패하면, 폴백을 끈 상태처럼 Claude 를 다시 부르지 않는다
   (429 중인 Claude 는 다시 불러도 거의 실패하고 대기 지연만 커진다).
3. GPU 가 죽어 있는 동안 Ollama 래치의 기한(1·2·4…30분 사다리)이 끝날 때마다, 다음 생존 탐색(≤ 30초)까지 죽은 Ollama 가
   쓸 수 있어 보인다. 그 창에서 Claude 가 실패한 요청은 재시도 없이 죽은 Ollama 로 넘어가 실패한다. 「기한 만료 = 다음
   탐색 전까지 닫힘」은 모든 provider 래치의 기존 계약이고, 창을 없애려면 생존 탐색이 열린 래치도 핑해 다시 열어야 해
   §3.1-5(닫힌 대상만 핑)를 바꿔야 한다. 크기 ≈ GPU 장애 시간의 1~3% × Claude 일시 실패율(최종 리뷰 I-2, 2026-10-03).

## 4. 설정

| 키 | 기본 | 비고 |
|---|---|---|
| `devpath.provider.liveness-interval` | `PT30S` | 기동 즉시 1회 |
| `devpath.review.ollama-connect-timeout` | `PT3S` | 읽기는 `devpath.review.ollama-timeout`(60초) 유지 |
| `devpath.community-seed.ollama-connect-timeout` | `PT3S` | 〃 |
| `devpath.retention.ollama-connect-timeout` | `PT3S` | 〃 |

모두 기본값이 있어 gitops env 변경이 필요 없다. fallback 이 비어 있는 환경(체인 길이 1)에서는 Ollama 탐색 빈이 생기지 않아
트래픽·동작 변화가 0 이다.

## 5. 테스트 (TDD — 실패 테스트 먼저)

- `ProviderAttemptPlan`: 3.2 표의 모든 행 + 1순위가 Ollama 인 체인 · 3개 provider 체인 · 빈 체인.
- `ClaudeClients`: 재시도 명시 인자. Spring 컨텍스트로 체인 ≥ 2 면 두 빈, 1 이면 한 빈.
- 세 래퍼: 뒤에 쓸 수 있는 provider 가 없을 때 `LAST_RESORT` 구현체 사용 · 전부 차단 시 1순위 `LAST_RESORT` 1회 · 래치 기록 유지.
- `OllamaProviderProbe`(HTTP 목): 정상 · 모델 없음 · 연결 실패 · 5xx.
- 생존 루프(가짜 시계·래치): 닫힌 대상만 핑 · 실패 시 즉시 열림 · 성공 시 무기록 · 열린 대상은 건너뜀.
- 분류: Ollama 404 → `TRANSIENT` · Claude 404 → `OUTPUT_INVALID` 유지 · review Ollama 404 → `TransientReviewException`.
- **동등성 종단 테스트**: 폴백 켬 + Ollama 사망(연결 거부)에서 Claude 목이 첫 호출 529 · 다음 200 이면 요청이 **성공**해야 한다
  (재시도 0 이면 실패 — 「폴백을 끈 상태와 같다」의 직접 증명). SDK 의 재시도 대상 상태코드는 구현 때 문서로 확인한다.
- 기존 스위트(359) 전부 통과.

## 6. 배포

ai-svc `develop` 으로 PR → CI 녹색 → 머지. 운영 반영은 **다음 릴리스 캠페인**(새 ai-svc 이미지 → candidate 의
`services.devpath-ai-svc` · AI 평가 재실행). 그때까지 운영에는 M1 위험이 남는다 — 긴급 차단 절차
(`plans/2026-10-03-gitops-main-ai-fallback-probe-via-publisher.md` 「긴급 차단」)로 대비한다.
