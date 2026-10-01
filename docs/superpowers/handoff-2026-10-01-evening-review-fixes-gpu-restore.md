# 핸드오프 — 2026-10-01 저녁 (웹 헤더 정렬 → PR #83 리뷰 반영 → 모델 결정 → GPU 노드 복구)

> 앞 문서: `handoff-2026-10-01-session-close.md`(PR #194·#195). 그 문서가 **「다음 세션 첫 동작 = PR #83
> 리뷰 결과 처리」** 로 지정한 것을 이 세션이 처리했고, 뒤이어 모델 결정과 GPU 노드 복구까지 갔다.
> **다음 세션 첫 동작은 §5.**

## 0. 한 줄 요약

| # | 작업 | 상태 | 머지 |
|---|---|---|---|
| 1 | 웹 헤더 좌우 정렬 결함 | **완료** | frontend PR #243 → develop `b77efce` |
| 2 | ai-svc PR #83 최종 리뷰 반영(Critical 1·Important 5·Minor 5) | **완료** | ai-svc PR #83 → develop `4e26eae` |
| 3 | 리뷰 전문·ruling 원장 보존(M11) | **완료** | documents PR #196 → develop `e0fd3c6` |
| 4 | 폴백 모델 결정 + GPU 스팟 노드 복구 | **완료**(GPU 는 운영 반영됨) | gitops PR #166 → develop `628a39a` |
| 5 | 스팟 회수 탐지 | **미해결 — 사용자 결정 1건 대기** | — |

운영(main)에 들어간 것은 **GPU 노드 복구뿐**이다(클러스터 직접 조작). 나머지 넷은 전부 develop 에만 있다.

---

## 1. 웹 헤더 좌우 정렬 (완료 · develop)

사용자가 1920 폭 스크린샷으로 지적: 주 메뉴가 헤더 전체로 흩어지고 검색·계정이 오른쪽 끝에 붙지 않았다.
**겹쳐 있던 독립된 두 개의 flex 결함**이었다 — `packages/dp_design/lib/src/shell/dp_web_header.dart`.

1. **항목이 균등 몫만큼 확장된다** — `_navSurface` 의 `Container(alignment: Alignment.center)`.
   Container 의 `alignment` 가 만드는 `Align` 에는 `widthFactor` 가 없어
   (`shrinkWrapWidth = _widthFactor != null || !constraints.hasBoundedWidth`) **제약의 최대 폭까지 확장**한다.
   항목이 `Flexible` 이라 각자 균등 몫을 통째로 차지하고 라벨이 그 한가운데로 밀렸다.
   → `Center(widthFactor: 1)`. **레포의 기존 관용구**다(`dp_web_footer.dart`·`dp_chrome_bar.dart:274`).
2. **우측 그룹이 끝에 붙지 않는다** — `Expanded(nav)` 와 `Flexible(search)` 가 남는 폭을 반씩 나눠 가졌는데,
   loose fit 인 검색은 제 몫 중 `maxWidth:200` 만 쓰고 **잔여가 재분배되지 않은 채 Row 끝에 남았다**.
   → 검색을 non-flex 로. **남는 폭을 흡수하는 flex 자식은 하나(tight)여야 한다.**

★두 함정 모두 이 레포가 이미 발견해 주석으로 남겨 둔 것이다 — `DpWebFooter` 가 1번을, `DpChromeBar:97-105`
가 2번을. **헤더만 두 교훈을 못 받았다.**★

**실측 (1920 폭 · 항목 4개)**

| 측정 | 전 | 후 | 기대(토큰) |
|---|---|---|---|
| 브랜드 → 첫 항목 | 113.5 | **36.0** | xl+md |
| 항목 라벨 사이 | 161.7 | **28.0** | md+xs+md |
| 현재 항목 밑줄 폭 | 207.6 (라벨 28.5) | **52.5** | 라벨+md×2 |
| 계정 → 바 우측 | **670.4** | **24.0** | xl |

1440·720 에서도 수정 후 값이 전부 동일하다(폭에 따라 변하면 아직 어딘가가 늘어나고 있다는 뜻).
검색이 non-flex 가 되면서 주 메뉴 가용폭은 720 에서 **249 → 298px** 로 오히려 넓어졌다.

검증: 실패 테스트 선작성 → red 실측 → green. 좌우 정렬 계약 1건 + `720`·`720@200%` 오버플로 부재 2건 추가.
전체 **1870 tests 통과**(dp_design 399 · web 1141 · admin 156 · dp_core 174).
**실브라우저 육안 확인** — mock 릴리스 빌드를 `tools/browser_ux/serve.mjs` 로 서빙, Chromium
1920/1440/1024/768/720 에서 `/dashboard` 캡처.

남는 것: 720 폭에서 라벨 말줄임(`학습 경…`). 네 항목 자연폭 합 ≈365px 이 가용폭을 넘어서다. 기존에도
그랬고 완화됐다. 더 줄이려면 좁은 폭에서 검색을 아이콘으로 접는 **별도 결정**이 필요하다.

---

## 2. ai-svc PR #83 리뷰 반영 (완료 · develop `4e26eae`, 수정 커밋 `609cd18`, 29파일 +843/−184)

리뷰 판정 **With fixes**. 리뷰어 보고를 그대로 믿지 않고 **세 Critical 주장과 다섯 Important 를 코드에서
직접 확인**한 뒤 반영했다. 전부 사실이었다.

### 추가로 확보한 실측 2건 (결정의 근거)

- **SDK 기본값**(anthropic-java-core 2.34.0): `maxRetries = 2`(javap `ClientOptions$Builder.<init>` 의
  `iconst_2; putfield maxRetries`), 기본 timeout `connect=PT1M · read/write/request=PT10M`
  (리플렉션으로 `Timeout.default()` 실행).
- **탐색기 적용 범위**: `ClaudeProbeConfig` 가 만드는 `ProviderProbe` 는 **Claude 세 개뿐**이고 그나마
  `ANTHROPIC_API_KEY` 가 있을 때만 생긴다. **Ollama 용 탐색기는 없다.**

### C1 — provider 기록이 폴백이 일어난 바로 그 경우에 틀렸다

★**내 계획의 결함이었다. 구현은 계획에 충실했다.**★ 세 결함이 한 메커니즘에:
(a) `ReviewService` 가 `providerName()` 을 `review()` **보다 먼저** 읽어 체인 머리 또는 직전 요청의
provider 를 기록 (b) `ThreadLocal` 미정리 → 풀 워커에 값이 남고 `CommunitySeedService:50` 이 **실패 경로**
에서 그것을 발행 (c) 래퍼는 소문자 체인 키, 구현체는 대문자 → 같은 컬럼에 두 표기.

★**멘토 `FallbackMentorClient` 가 셋 다 이미 해결해 뒀는데 계획이 따르지 않았다**★ — 그 수명 관리를
이식했다: 진입 시 `remove()` · `delegate.providerName()` 을 **호출 전에** 기록 · read-once-and-clear.

Ruling: 리뷰어가 "더 낫게" 제안한 콜백 방식은 인터페이스 3개와 구현 7개, `providerName()` 을 스텁하는
기존 테스트 12개를 모두 건드려 머지 직전 범위를 넘는다. 멘토 선례를 택했다.

★**잠금·기록 테스트는 운영의 호출 순서를 흉내내야 한다**★ — C1(a)를 테스트가 못 잡은 이유는 래퍼
테스트가 `review()` → `providerName()` 순이었는데 운영은 반대였고, review Spring 테스트 12개가
`providerName()` 을 상수로 스텁했기 때문이다. **스펙 §9 의 통합 테스트가 계획에서 ruling 없이 빠진 것이
직접 원인이다**(I5).

### I2 — 리뷰어의 "better still" 을 **기각**했다

"탐색이 확인할 때까지 계속 차단"은 이 코드베이스에서 **Ollama 를 영구 차단한다** — 탐색기가 Claude 에만
있어 Ollama 래치는 닫아 줄 주체가 없고, 시간 기반 만료가 탐색기 없는 provider 의 **유일한 회복 경로**다
(`ClaudeProbeConfig` javadoc 도 이 의존을 이미 적고 있다). 대신 `recordProbeFailure` 를 신설해 **탐색 실패가
항상 항목을 해소**하게 했다 — TRANSIENT 의 3연속 게이트 미적용(탐색은 사용자 트래픽이 아니다),
내용 실패는 탐색 포기(past-due 영구 잔류 + "stays open" 거짓 로그 제거).

### I4 — `maxRetries(0)` 을 **되돌렸다**(체인이 있을 때만 끈다)

근거(429 를 삼켜 래치 왜곡)는 **체인이 있을 때만** 성립하는데 `*_FALLBACK` 은 빈 값으로 출하한다.
노출 정도를 확인했다: ★**community-seed 는 Kafka 재시도가 없다**(예외를 잡아 `publishFailed` → 한 번의
503 이 그 질문의 시드 답변을 영구히 잃는다) · **retention 도 없다**(동기 HTTP) · review 만
`releaseForRetry` 가 받는다★ → `ClaudeClients.maxRetriesFor` 가
`ProviderChain.requestedCount >= 2` 일 때만 0. 값은 **MockWebServer 가 센 실제 요청 횟수**로 못박았다
(체인 없음 3회 / 있음 1회). 타임아웃 60초는 유지(멘토가 같은 자리에서 50초를 쓴다).

### 나머지

I1 `State` 네 필드 `volatile`(가시성은 결정적 재현 불가 → **컴파일된 필드 수식어**를 리플렉션으로 단언) ·
I3 백오프 사다리를 종류별로 분리 + 비어 있던 transient 배증·상한과 rate_limit 상한의 아래쪽 단언 ·
I5 세 기능 모두 **서비스**를 실제 `Fallback*Client` 로 관통하는 테스트 ·
Minor M1(기능 키 공유 상수)·M2(소스 텍스트 검사 → 행동 검증)·M3·M6(`.gitignore` CRLF→LF, diff 75줄→3줄)·M7.

**Deferred Minor 8건**(M4·M5·M8·M9·M10·M12 등) — `final-review.md` 에 있다.

검증: 각 수정 RED→GREEN 을 눈으로 확인(C1 은 신규 테스트가 먼저 9건 FAILED, I1~I3 은 컴파일 FAILED) ·
전체 **339 → 352 tests, 0 failures** · `./gradlew clean build prepareMentorReleaseArtifacts` 통과 ·
**멘토 디렉터리 무변경**(스펙 §4 제약) 확인 · CI build pass.

리뷰 전문과 ruling 원장은 `docs/superpowers/plans/2026-10-01-ai-provider-fallback-core/`
(`final-review.md` · `execution-ledger.md`, PR #196)에 보존했다 — ai-svc 의 `.superpowers/` 는 gitignore 라
워크트리와 함께 사라졌을 것이다(리뷰 지적 M11).

---

## 3. 폴백 모델 결정 — **retention 만 켠다** (gitops PR #166 → develop)

보정 §C 가 사용자 결정으로 남긴 「① 3b 로 낮춤 / ② 디스크·메모리 확보해 7b / ③ 노드 상향」을
**추측이 아니라 운영 CPU Ollama 에 실제 프롬프트를 보내** 판정했다(각 기능의 실제 system/user 프롬프트와
스키마를 그대로 재구성해 `/api/chat` 호출).

| 기능 | 실측 (qwen2.5:3b, 4.9 tok/s) | 판정 |
|---|---|---|
| **retention** | 콜드 **30.4s**(load 16.0 + eval 6.4/34tok) · 웜 16.6s, 한국어 문구 정상 | ✅ 켠다 |
| community-seed | 29.5s 인데 **질문에 답하지 않고 되물었다**("…seed answer을 작성해 주세요") | ❌ 공개 게시물 |
| review | 콜드 **70.6s**(타임아웃 60s 초과) · 웜 40.8s(10줄 샘플) · 한국어 지시에 **영어** 출력 | ❌ |

뒤의 둘은 저장·공개되는 산출물이라 스펙 §4.1 의 「가짜 산출물이 사용자 기록에 영구히 남는 것은 실패보다
나쁘다」에 걸린다. review 는 Ollama **structured output**(`format: <schema>`)이라 JSON 유효성은 디코딩이
보장한다 — 막은 것은 **지연과 내용**이다.

★**7b 를 막는 것은 디스크가 아니라 메모리다**★ — t3.xlarge 가용 3.7GB(3b 로드만으로 1.68GB 로 하락),
q4 7b 는 약 5GB 필요. 디스크는 7.8GB 여유라 7b **하나**는 들어간다.
★`RETENTION_OLLAMA_MODEL` 을 반드시 명시★ — 코드 기본값이 `qwen2.5:7b` 라 생략하면 폴백이 404.
★**멘토는 이미 운영에서 3b 가 주 provider**★(`MENTOR_PROVIDER=ollama`) — 3b 수용의 선례였다.

**발효 시점**: ai-svc develop(PR #83)이 main 으로 릴리스돼 `:main` 이미지가 갱신된 뒤부터. 그 전까지 이
env 는 읽히지 않는다(현 이미지의 `application.yml` 에 해당 키가 없다).
**릴리스 계약**: `ai_release_eval_config.rendered_config_sha256` 은 생산자가 같은 `base_sha` 에서
`kustomize build apps/devpath-ai-svc/base` 를 다시 돌려 기록하는 자기정합 검증이라 수동 갱신이 필요 없다
(PR #166 의 `mission-spine-release-contract` 통과로 확인).

---

## 4. GPU 스팟 노드 복구 (**운영 반영됨** — 클러스터 직접 조작)

### 발견

모델 결정을 위해 노드 용량을 재다가 발견했다: **GPU 노드가 2026-09-08 스팟 회수된 뒤 복구되지 않았다.**
EC2 에 인스턴스가 `devpath-k3s`(t3.xlarge) **1대뿐**이었고, `ollama-gpu` 서비스는 **23일째 엔드포인트 0개**,
`ollama-gpu` 파드는 23일째 Pending(`FailedScheduling` ×6692). 학습경로 생성이 그리로만 라우팅되므로
(`OLLAMA_PATH_BASE_URL`) **잠복 고장**이었다 — ai-svc 로그가 7일간 121줄로 거의 무트래픽이라 사용자
영향은 없었다.

### ★새 노드만 띄우면 파드는 Pending 그대로다★

`ollama-gpu-models` 의 PV 가 local-path 라
`nodeAffinity: kubernetes.io/hostname In [ip-172-31-52-213]` 로 **죽은 노드에 고정**돼 있었고,
`Terminating` 으로 멈춘 옛 파드가 PVC 의 `kubernetes.io/pvc-protection` finalizer 를 붙들고 있었다.
필요한 순서: **노드 오브젝트 삭제 → 옛 파드 강제 삭제(`--force --grace-period=0`) → PVC 삭제**.
모델 캐시는 노드와 함께 이미 사라졌으므로 버려도 된다(reclaim policy = Delete). 지우면 매니페스트로
재생성되고 새 노드에 새 PV 가 붙는다.

### 실행·검증

런북 `devpath-gitops/docs/runbook-k3s-bootstrap.md` 「GPU 노드 추가」를 그대로 따랐다.

| 검증 | 결과 |
|---|---|
| 새 노드 | `ip-172-31-52-85` · `i-0956cd8d637f6dafd` · g6.xlarge **spot** · NVIDIA L4 23034MiB · 드라이버 595.91.07 |
| 조인 | k3s v1.36.2+k3s1 고정 · 라벨 `devpath.ai/gpu=true` · 테인트 NoSchedule · 토큰 scp 후 `shred` |
| GPU | `nvidia.com/gpu` allocatable = **1**, 파드 내 `nvidia-smi` 확인 |
| 서비스 | `ollama-gpu` 엔드포인트 **ready=true**, 모델 `qwen2.5:3b` 보유 |
| 성능 | **58.8 tok/s**(CPU Ollama 4.9 tok/s 대비 **12배**, 런북 실측 66 t/s 와 동급) |
| 배선 | **ai-svc 파드에서 `ollama-gpu.devpath.svc:11434` 도달 확인**(`/api/tags` 응답) |

### 선결 조건 정정 (2026-10-01 실측)

- ★**스팟 쿼터 `L-3819A6DF` 는 「기본 0·PENDING」이 아니라 4 vCPU 로 승인돼 있다**★
  (`devpath-path-generation-async` 메모리가 또 한 번 「대기」로 잘못 이월했다 — 그 파일이 스스로 적어 둔
  교훈 「이월 블로커는 착수 전 재측정하라」를 같은 파일의 다른 항목이 어긴 사례).
- **스팟 시세가 올랐다**: `$0.2824/h`(2026-08-17) → **`$0.4587/h`**(온디맨드 `$0.9896/h` 대비 46%).
  상시 가동 시 월 약 **$330**.
- SG self-referencing 3규칙 유지 · AMI `ami-09d3bdf0648512f52` 유효 · 서브넷 퍼블릭(IGW).

복구 절차와 탐지 공백은 런북에 기록했다(PR #166, `5cc6f02`).

---

## 5. ⬅️ 다음 세션 첫 동작 — 스팟 회수 탐지 (**사용자 결정 1건 대기**)

★**스팟 회수를 알려 주는 경로가 하나도 없다**★ — 클러스터에 모니터링·알림 스택이 없다
(`kubectl get ns` 에 monitoring 없음, CronJob 0개). **23일 무인지의 직접 원인**이고, 지금 그대로 두면
재발한다. 런북에 선택지를 표로 남겼다:

| 방안 | 범위 | 막는 것 |
|---|---|---|
| EventBridge `EC2 Spot Instance Interruption Warning` → SNS | AWS 리소스 3개, 클러스터 무변경. 회수 2분 전 통지 | **알림 수신처 결정**(이메일/Slack/기타) — 사람 결정 |
| `ollama-gpu` 엔드포인트 0 감시 | 원인 불문 모든 중단을 잡는다 | 위와 같은 결정이 선행 |
| 스팟 ASG(capacity 1) 자동 재기동 | 토큰을 SSM SecureString + 인스턴스 프로파일로 | 런북 3번(「user-data 에 토큰을 넣지 않는다」) 재설계 |

**수신처만 정해지면 EventBridge→SNS 는 바로 붙일 수 있다.**

### 그다음

1. **계획 B** — 스펙 §10 메트릭(Micrometer) · §5 review 재생성 엔드포인트와 래치-열림 거부.
2. **운영 반영 대기 4건** → 릴리스 캠페인 한 번으로 묶는다:
   - ai-svc PR #83 (provider 폴백 + 리뷰 반영) — `4e26eae`
   - frontend 웹 헤더 정렬 — `b77efce`
   - gitops landing 프로브 전파 경쟁 결함 수정 — `3f5ff8f`(앞 핸드오프 §1)
   - gitops retention 폴백 활성 — `628a39a` (★ai-svc 이미지 갱신과 **같은 릴리스**여야 의미가 있다★)
3. **deferred Minor 8건** — `plans/2026-10-01-ai-provider-fallback-core/final-review.md`.
4. (선택) 720 폭 헤더 라벨 말줄임 — 좁은 폭에서 검색을 아이콘으로 접을지 결정.

---

## 6. 이 세션의 머지 목록

| 레포 | PR | 커밋 | develop |
|---|---|---|---|
| devpath-frontend | #243 | `aa6eb7a` | `b77efce` |
| devpath-ai-svc | #83 | `609cd18`(이번 수정) | `4e26eae` |
| documents | #196 | `6ef92be` | `e0fd3c6` |
| devpath-gitops | #166 | `ebf3619`·`5cc6f02` | `628a39a` |

임시 워크트리 4개 생성·전부 제거. 4개 레포 추적파일 미커밋 0건.

## 7. 재사용할 함정

- **`Container.alignment` 은 Flexible 자식을 균등 몫만큼 확장시킨다** — 밑줄·테두리가 글자보다 길면 이것.
  `Center(widthFactor: 1)` 로 푼다.
- **Row 에서 남는 폭을 흡수하는 flex 자식은 정확히 하나, tight 여야 한다** — loose 쪽의 잔여는
  재분배되지 않고 Row 끝에 남는다. `Spacer` 를 더해도 해결되지 않는다(Spacer 도 제 몫만 받는다).
- **로컬 Flutter(3.47.2)가 CI 핀(3.44.1)과 달라 `melos bootstrap` 이 `pubspec.lock`·`analysis_options.yaml`
  3개를 다시 쓴다** — 커밋 전 되돌린다(`git add -A` 금지).
- **로컬 ai-svc 테스트에는 `pgvector/pgvector:pg16` 이 필요하다**(`postgres:16-alpine` 은 Flyway 가
  `extension "vector"` 를 요구해 실패).
- **`python` 은 스텁 — `py` 를 쓴다.** 한글 포함 스크립트는 `PYTHONUTF8=1`.
- **운영 k3s 접근**: SSH 키가 CRLF 라 `tr -d '\r'` 로 LF 사본을 만들어 쓴다. 노드에서 `sudo kubectl`.
