# 핸드오프 — 2026-10-02 (Ollama 7b 가능 검토 → 세 기능 폴백 활성 → 스팟 회수 탐지 구축)

- 지시: 「올라마 모델 7b 진행 가능 검토후 가능하면 진행」 + 「사용자 중지·사용자 작업 필요 지점까지 전 작업 승인 기반 진행」
- 앞 핸드오프: `handoff-2026-10-01-evening-review-fixes-gpu-restore.md`(PR #197, develop `437d25e`)

---

## 0. 한 줄 요약

**7b 는 GPU 노드에서 가능했고, 어제의 모델 판정이 세 기능 전부로 뒤집혔다.** 실측 후 적용까지 끝냈다
(ai-svc **#84** `9045042` · gitops **#167** `e6730ed`). 어제 「사용자 결정 1건 대기」로 남겼던
**스팟 회수 탐지도 구축·검증 완료**(EventBridge → SNS → 이메일, 구독 확인과 실제 수신까지).
**남은 사용자 작업은 Slack 수신처 하나**이고, 운영 반영은 다음 릴리스다.

---

## 1. 7b 가능 여부 — 전제가 바뀌어 있었다

어제 7b 를 기각한 근거는 ★「t3.xlarge 가용 메모리 3.7GB vs q4 7b 약 5GB」★ 였다.
**그 사실은 CPU 노드의 것이고, 어제 저녁 복구한 GPU 노드에는 해당하지 않는다.**

| | CPU 노드(어제 판정의 근거) | GPU 노드(현재) |
|---|---|---|
| 모델 디스크 여유 | 7.8G | 14G → (작업 후) 9.4G |
| 파드 메모리 limit | 5Gi | **8Gi** |
| 가속기 | 없음 | **NVIDIA L4, 여유 20,278 MiB** |
| 생성 속도 | 4.9 tok/s | **약 52 tok/s** |

### Ollama 가 둘이라는 것이 관문이었다

- `ollama`(CPU 노드) ← `OLLAMA_BASE_URL`. 임베딩·멘토·**그리고 폴백**.
- `ollama-gpu`(GPU 노드) ← `OLLAMA_PATH_BASE_URL`. 학습경로 생성 전용.

★**코드의 Ollama 엔드포인트 변수는 `OLLAMA_BASE_URL` 하나뿐이고 `OLLAMA_PATH_BASE_URL` 만
분리돼 있었다**★ → 「폴백만 GPU 로」가 **원리적으로 불가능**했다. 이것이 1번 작업이 된 이유다.

(참고: GPU 파드의 `AGE 23d / RESTARTS 0` 은 23일간 Pending 이었다가 어제 복구로 Running 이 된 것과 일치한다.)

---

## 2. 실측 — 어제 판정이 세 기능 전부로 뒤집혔다

각 기능의 **실제 system/user 프롬프트·options·format 을 코드에서 그대로 재구성**해
`/api/chat` 으로 측정했다(어제와 같은 방법, 모델과 노드만 다름).

| 기능 | 3b @ CPU (10-01) | **7b @ GPU (10-02)** | |
|---|---|---|---|
| retention | 콜드 30.4s · 웜 16.6s | 콜드 **24.8s** · 웜 **0.8s** | ✅ |
| community-seed | 29.5s, **질문에 되물었다** | **7.3s, 정답 제시** | ❌→✅ |
| review | 콜드 70.6s(타임아웃 초과) · 웜 40.8s · **영어** | 웜 **5.6s** · **한국어** · SQL 인젝션 정확 탐지 | ❌→✅ |

- community-seed 는 `@Transactional` 롤백 질문에 「try-catch 로 예외를 삼키면 롤백되지 않으니
  다시 던져라」는 정답을 냈다.
- review 는 structured output 스키마를 지키며 SQL 인젝션(line 5)과 테이블 부재를 짚었다.
  다만 같은 지적을 3번 중복한 흠이 있다(치명적이지 않음).
- 최악 경로(콜드 24.8s + 최장 생성 ~10s)도 타임아웃 60s 안이다.

### ★내가 중간에 내린 오진과 그 정정★

측정 중 파드가 멈춰 「`limits.memory: 8Gi` 가 7b 의 블로커」라고 판단했는데 **틀렸다.**
8Gi 를 채운 것은 **벤치마크를 위해 모델을 3종(3b+7b+coder:7b) 올린 내 과정**이었다.
운영 구성인 **2종(3b+7b)에서는 `memory.current` 4.79GB = 56%, 압박 0회**다. limit 상향은 불필요하다.
→ 그래서 review 도 코드 기본값 `qwen2.5-coder:7b` 가 아니라 **일반 7b** 를 쓴다(3종이 되는 대가가 크다.
coder 쪽 review 가 조금 더 간결했지만 그 차이로 디스크·메모리 여유를 바꿀 가치는 없다).

---

## 3. 적용 (둘 다 develop 머지)

### ai-svc PR #84 — `9045042` (코드만으로는 운영 불변)

`devpath.<feature>.ollama-base-url` 신설. 미지정이면 공용 `devpath.ollama.base-url` 로 폴스루한다.
`devpath.ollama.path-base-url` 패턴의 일반화다.

- 신규 `FeatureScopedOllamaBaseUrlTest` **7건**. ★프로퍼티 값이 아니라 **MockWebServer 두 대에
  도달한 실제 요청 수**로 단언한다★ — 조립에서 오버라이드가 누락되면 요청은 조용히 공용 주소로
  가고, 그것이 `OLLAMA_PATH_*` 를 `application.yml` 에 등록하지 않아 무시됐던 2026-08-17 실패와 같은 양식이다.
- **red 를 먼저 확인했다**: 구현 전 오버라이드를 준 4건이 SocketTimeout 으로 실패(= 요청이 공용으로 갔다),
  폴스루 3건은 통과. 구현 후 7/7.
- 전체 스위트 **359 tests · 0 failures**(베이스라인 352 + 신규 7). `MockExclusionTest` 4/4 유지.

### gitops PR #167 — `e6730ed`

- 세 기능 `*_FALLBACK=ollama` · `*_OLLAMA_MODEL=qwen2.5:7b` · `*_OLLAMA_BASE_URL=ollama-gpu`.
  임베딩·멘토는 공용(CPU)에 남는다 — **임베딩에는 폴백이 아예 없어** 스팟에 노출시킬 수 없고,
  멘토는 `MENTOR_FALLBACK=claude` 가 받는다.
- `ollama-gpu` 에 **`strategy: Recreate`** (§4) + postStart 가 `qwen2.5:7b` 도 pull.
- 런북: 회수 탐지 구축 결과 · 복구 검증 7번(모델 2종) · 함정 2건.

### ★GPU 는 스팟이다 — 사용자 결정으로 수용한 교환★

어제 매니페스트 주석은 폴백을 GPU 로 보내는 것을 **명시적으로 금지**했다(회수 시 멈추는 것은
비동기 학습경로뿐이어야 한다). **2026-10-02 사용자 결정으로 뒤집었다.**
근거: 폴백은 Claude 가 **이미 실패한** 2차 경로다. GPU 상실 = 「Claude 실패 시 대체 없음」 =
폴백 도입 이전 상태로 돌아갈 뿐 **순손실이 아니다**. 반대쪽 이득은 CPU 3b 로 retention 하나가
겨우 되던 것이 세 기능 전부가 되는 것이다. 회수 자체는 §5 로 보완했다.

---

## 4. 재사용할 함정 2건 (둘 다 이번 실측)

### ★GPU 1개 노드에서 `rollout restart` 는 영구 교착된다★

새 파드는 `Insufficient nvidia.com/gpu` 로 Unschedulable, 롤아웃은 그 파드를 기다리므로
옛 파드를 끝내지 않는다. GPU 는 옛 파드가 놓을 때까지 안 비고, 옛 파드는 새 파드가 Ready 될 때까지
안 죽는다. `rollout status` 는 타임아웃만 낸다.

- 해법: **`strategy: Recreate`**(반영함). 단일 레플리카라 잃는 무중단도 없다.
- 이미 교착됐으면 **`kubectl rollout undo`** 로 푼다(서비스는 옛 파드로 계속 살아 있다).
- 파드만 새로 띄우려면 `rollout restart` 가 아니라 **`kubectl delete pod`** — 순차라 교착하지 않는다.

### ★Ollama 모델 3종부터 page cache 가 limit 을 채워 조용히 느려진다★

Ollama 는 GPU offload 시 `mmap = false` 로 읽고, 그 page cache 가 파드 cgroup 에 집계된다.

| 모델 수 | `memory.current` | 결과 |
|---|---|---|
| 2종(3b+7b) | 4.79GB (56%) | 압박 0회 · 7b 콜드 24.8s |
| 3종(+coder) | **8.586GB = limit 의 99.95%** | 로드 **105s** · 일부 무응답 |

★**OOM 이 아니다**★ `memory.events` = `max 94449 / oom_kill 0`. 죽는 대신 회수 압박으로 느려진다.
로그는 `offloaded 29/29 layers to GPU` 까지 찍히고 응답만 안 온다. `ollama ps` 가 「로드됨」이라
보고하는데 실제 `llama-server` 는 없는 **상태 불일치**도 생긴다.

- **모델을 지워도 캐시는 안 빠진다**: `ollama rm` + 전체 언로드 후에도 6.65GB. 그 상태에서
  3b 로드가 180s 타임아웃으로 실패했다. `/sys/fs/cgroup/memory.reclaim` 쓰기는 컨테이너 안에서 불가.
- 멈춘 런너는 `STAT=Dl`(uninterruptible I/O)로 남아 **파드 종료까지 막는다**.
- 해법: **파드 재생성**(직후 44MB·`events max 0`) + 모델 수를 limit 에 맞춰 묶기.

### 그 밖에

- `pkill -f bench.py` 가 **자기 SSH 명령줄에도 매치해 세션을 끊었다**(exit 255).
  `pkill -f "ben[c]h\.py"` 처럼 패턴이 자기 자신과 겹치지 않게 쓴다.
- Ollama 컨테이너에 `curl`·`python3` 이 **없다**. 측정은 control-plane 노드에서 ClusterIP 로 한다.
- GPU 노드로의 **직접 SSH 는 차단**(배너 교환 타임아웃). 모든 조작은 control-plane 경유 `kubectl`.
- 디스크는 AMI·드라이버가 대부분을 차지한다(이미지 3.3GB·모델 6.6GB vs 사용 64G).
  `ImageGCFailed` 가 반복되면 **모델 정리가 유일한 회수 수단**이다.

---

## 5. 스팟 회수 탐지 — 구축·검증 완료 (어제 §5 의 대기 항목)

| 리소스 | 값 |
|---|---|
| SNS 토픽 | `arn:aws:sns:ap-northeast-2:963773969059:devpath-spot-interruption` |
| 규칙 ① | `devpath-spot-interruption-warning` — 회수 2분 전 경고 + 재균형 권고 |
| 규칙 ② | `devpath-instance-stopped-or-terminated` — `terminated`·`stopped`·`shutting-down` |
| 구독 | email `deepestdark@gmail.com` — **확인 완료** |

★**규칙을 둘로 나눈 이유**★ — 2분 경고만으로는 23일 방치가 재발한다. 그 2분에 사람이 없으면
아무 일도 안 생기기 때문이다. ②가 「회수가 끝났다 = **복구가 필요하다**」를 알린다.
②는 인스턴스를 가리지 않는데(이벤트에 태그가 없어 태그 필터 불가) 계정에 인스턴스가 2대뿐이라
노이즈가 아니라 이득이다 — control-plane 정지도 알아야 한다.
타깃은 `InputTransformer` 로 읽을 수 있는 문장을 만들고 본문에 복구 절차와
★새 노드만 띄우면 Pending 그대로★ 경고를 넣었다.

### ★이메일 구독 확인까지 AI 가 끝냈다★

사람의 링크 클릭이 필요하다고 보고 넘기려 했지만, Gmail MCP 로 확인 메일을 찾아 Token 을 뽑아
`sns:ConfirmSubscription` 을 호출하면 된다 — 실제로 그렇게 했다(`PendingConfirmation` → 정상 ARN).
**소유권 규칙 2(「실행 가능 여부는 시도 후에만 판정한다」)의 실례다.**

### 검증

- `TestEventPattern` 매칭 행렬: 규칙①은 경고·재균형에 `true`/`terminated` 에 `false`, ②는 그 반대.
  **음성 대조군 `state=running` 은 두 규칙 모두 `false`**(정상 가동을 알리지 않는다).
- `sns:Publish` → **받은편지함 실제 수신 확인**(`[DevPath/AWS] spot detection is live (test)`).

### ⚠ 남은 사용자 작업 — Slack 수신처

사용자 결정은 「이메일·Slack 둘 다」였고 **이메일만 완료**다. Slack 은 워크스페이스 인증이
선행이라 구조적으로 사람만 할 수 있다(실측: `chatbot` API 는 **us-east-1 만 엔드포인트 연결
실패**이고 us-east-2·us-west-2 는 동작한다 — 재시도해 확인했다. 결과 `SlackWorkspaces: []` =
워크스페이스 미연결).

**방법 A — AWS Chatbot(권장, Lambda 불필요)**
1. AWS 콘솔 → Amazon Q Developer in chat applications(구 AWS Chatbot) → *Configure new client* → Slack
   → Slack 로그인·권한 승인 → 워크스페이스 연결.
2. 이후는 AI 가 잇는다: `CreateSlackChannelConfiguration` 으로 채널을 위 SNS 토픽에 연결.
   필요한 값은 **채널 ID**(Slack 채널 우클릭 → 링크 복사의 끝부분, `C…`)뿐이다.

**방법 B — Incoming Webhook**
1. Slack → Apps → Incoming Webhooks → 채널 선택 → **Webhook URL 발급**.
2. 이후는 AI 가 잇는다: SNS → Lambda(포맷 변환) → Webhook 구성. SNS 는 Slack 이 기대하는
   `{"text": …}` 형식을 보내지 않아 Lambda 변환이 반드시 필요하다.

---

## 6. 상태 복구 — 내가 건드린 것

벤치마크로 바꾼 운영 상태를 되돌렸다.

- `qwen2.5-coder:7b` 삭제(디스크 94% → **88%**, 9.4G 회수). 필요하면 약 6분 재pull.
- 포화된 cgroup 을 파드 재생성으로 초기화(`memory.current` 8.15GB → 44MB).
- `qwen2.5:3b` 재워밍(`keep_alive=24h`) — path 생성이 콜드를 떠안지 않게. 콜드 로드 61.4s 실측.
- `rollout restart` 교착은 `rollout undo` 로 해소. **서비스 중단 없음**(옛 파드가 계속 Ready).
- 최종: 엔드포인트 ready · 모델 2종 · VRAM 여유 · 압박 0회.

---

## 7. 머지 목록

| 레포 | PR | 커밋 | develop |
|---|---|---|---|
| devpath-ai-svc | **#84** | `492746c` | `9045042` |
| devpath-gitops | **#167** | `826b33e` | `e6730ed` |
| documents | (이 문서) | — | — |

AWS 리소스(SNS 토픽 1 · EventBridge 규칙 2 · 구독 1)는 **운영에 직접 반영됨**(IaC 대상 아님,
런북에 기록). 그 외 코드·매니페스트는 **develop 에만** 있다.

---

## 8. ⬅️ 다음

1. **Slack 수신처** — §5 의 방법 A/B 중 하나. 사용자 1단계 뒤 AI 가 잇는다.
2. **운영 반영 대기 5건을 릴리스 한 번으로** — ★ai-svc 와 gitops 는 **같은 릴리스**여야 한다.
   코드(#84)가 없으면 gitops 의 `*_OLLAMA_BASE_URL`·`*_FALLBACK` 이 **조용히 무시된다**★
   - ai-svc `4e26eae`(#83 폴백 코어) + **`9045042`(#84 기능별 엔드포인트)**
   - gitops `628a39a`(#166) + **`e6730ed`(#167 7b 폴백)** + `3f5ff8f`(landing 전파 경쟁)
   - frontend `b77efce`(웹 헤더 정렬)
   - 반영 후 **운영에서 폴백 한 번을 실제로 태워 확인**할 것(7b 콜드 24.8s 가 첫 호출에 든다).
3. **계획 B** — 스펙 §10 메트릭(Micrometer) · §5 review 재생성 엔드포인트와 래치-열림 거부.
4. **deferred Minor 8건** — `plans/2026-10-01-ai-provider-fallback-core/final-review.md`.
5. (선택) 미복구 상태를 **반복** 알리는 층 — EventBridge Scheduler + Lambda 로 GPU 태그
   인스턴스 수 0 감시. ②가 1회 알리므로 급하지는 않다.
