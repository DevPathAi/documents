> **회수 경위(컨트롤러 기록)**: 리뷰어(새 컨텍스트 general-purpose 서브에이전트, 89 tool_use·약 23분·31만 토큰)의 `REPORT.md` 쓰기가
> 하네스에 거부됐다 — `Subagents should return findings as text, not write report files`. 최종 응답은 스텁만 반복했고,
> 보고 전문은 에이전트 대화 기록(JSONL)의 assistant 텍스트 블록(886행, 10,031자)에서 Python 으로 그 블록만 뽑아 회수했다.
> 아래 본문은 리뷰어가 쓴 그대로다. 맨 끝 「컨트롤러 대조」만 컨트롤러가 덧붙였다.

# 독립 리뷰 보고 — AI fallback probe publisher 준비물 (2026-10-03)

**Ready: No** — 산출물(target `a97a175`·헬퍼 `868afac`·staged `3b424ff`·`rendered/` 5종)은 기계적으로 전부 검증을 통과해 **재작업이 필요 없다**. 그러나 Part B 전에 계획서·사용자 결정에 반영할 Medium 3건이 있다: (M1) 폴백을 켜면 Claude SDK 재시도가 0이 되어 「GPU 상실 = #83 이전 상태(순손실 아님)」 전제가 코드와 다르다 → 사용자 재확인이 필요하다. (M2) target 자체를 되돌리는 경로가 없다. (M3) 다음 candidate 의 `rendered_config_sha256` 를 다시 계산해야 한다.

리뷰 방식: 읽기 전용. gitops 객체는 `git show/diff/ls-tree/archive`로 읽고 scratchpad 에 풀어 실행했다. 커밋 해시 재현은 `hash-object`(`-w` 없음)로 했다. kubectl·ssh·push·POST 는 하지 않았다. GitHub 는 `gh api` GET 만 썼다.

## 질문별 판정

### Q1 target 내용 — Yes
- `a97a175` 부모 = `cea3610ab295…` 단독. 작성자·커미터 = 봇, 시각 = 2026-10-03T03:00:00Z.
- `git diff --name-status cea3610 a97a175` 결과는 M 5행뿐이다.
- 5경로 blob 은 develop `e6730ed` 와 전부 같다(예: ai-svc deployment `0c350561f7`). merge-base `eb41381..cea3610` 동안 그 5경로를 건드린 커밋은 0개다.
- web·ai-svc·migration kustomization 과 migration `job.yaml`·ollama-gpu kustomization 은 target 과 main 이 바이트 동일하다(`464221c1`·`a6ad6835`·`2f7f9812`). develop 쪽은 r3 값이다(`6e0cd7fe`·`95305b4d`·`9249eb6a`).
- 원격 상태(`gh api` GET): `main` = `cea3610` · `develop` = `e6730ed`. publisher 브랜치 4개는 원격에 없다(404).
- 재현성: 스크립트의 상수로 커밋 바이트를 다시 만들어 `git hash-object -t commit --stdin`(쓰기 없음)에 넣었다. 결과 `a97a1754…` 와 `cat-file` 바이트가 일치한다.
- 보충(L3): 릴리스가 관리하는 kustomization 은 3개가 아니라 4개다. admin 도 다르다(main `4c93a285…` 는 `22759fc` 가 승격한 값, develop 은 옛 값 `5847d5e9…`). target 은 5경로 화이트리스트로 만들어지므로 영향은 없다.

### Q2 운영 효과 — 바인딩·Service·Recreate Yes / 운영 효과 서술 Concern(M1)
- **env 9개 바인딩**(`83cfe792:src/main/resources/application.yml`):
  - `REVIEW_FALLBACK`:39 · `REVIEW_OLLAMA_MODEL`:42 · `REVIEW_OLLAMA_BASE_URL`:45
  - `COMMUNITY_SEED_FALLBACK`:73 · `COMMUNITY_SEED_OLLAMA_MODEL`:75 · `COMMUNITY_SEED_OLLAMA_BASE_URL`:77
  - `RETENTION_FALLBACK`:86 · `RETENTION_OLLAMA_MODEL`:87 · `RETENTION_OLLAMA_BASE_URL`:89
  - 소비처: `ReviewClientConfig.java:27-32`·`ReEngagementClientConfig.java:23-28`·`CommunitySeedClientConfig.java:24-29`.
  - 운영 이미지 대조: `gh api` 에서 `sha256:107fd20a…` 의 태그 = `83cfe792201b…`.
- **Service**: `service.yaml` 은 name `ollama-gpu`, port 11434 이고 AppSet namespace 가 `devpath` 이므로(`applicationset.yaml:26-28`) `ollama-gpu.devpath.svc:11434` 와 맞는다. 기존 `OLLAMA_PATH_BASE_URL` 과도 같은 값이다.
- **Recreate 전환**: 컨트롤러는 갱신된 spec 의 strategy 로 롤아웃한다. 옛 RS 를 0 으로 줄이고 종료를 기다린 뒤 새 RS 를 만든다. GPU 1개 교착은 생기지 않는다.
  - AppSet 에 ServerSideApply 가 없으므로 client-side apply 다. apps/v1 `strategy` 는 `retainKeys` 라 기본값 `rollingUpdate` 가 제거된다.
  - 라이브 실측은 하지 못했다 → 4단계에서 `strategy.type`·`rollingUpdate` 부재·RS 1개를 확인할 것.
- kustomize v5.4.3 렌더 대조: ai-svc 는 env 9줄 추가뿐, ollama-gpu 는 `strategy: Recreate` 와 pull 1줄뿐이다.

### Q3 다음 base — Concern(M3, L2)
- 재실행(target 의 `verify_promotion_chain.py`, 10/02 candidate spec):

  | 커밋 | inert migration | migration selector | service base selectors |
  |---|---|---|---|
  | target | ok | ok | ok |
  | main | ok | ok | ok |
  | M `c1d5e8cf` | ok | ok | 거부(`devpath-platform-svc: sealed base must not retain a writer fence`) |

- `inspect_chain` 의 base 분기(`:776-780`)는 검사 4개를 적용한다. `prove_next_base.py` 는 `_require_web(…,"base")` 를 뺐다. web kustomization 이 바이트 동일하므로 안전하다(L2).
- **빠진 base 조건**: `verify_ai_rendered_config` 는 base 를 렌더해 해시를 비교하고 `validate_ai_rendered_runtime` 를 돌린다(`verify_release_artifacts.py:54-60, 2587-2668, 2849-2885, 3342`).
  - target 에서 `validate_ai_rendered_runtime` 는 통과한다.
  - 해시는 바뀐다 → M3.

### Q4 publisher 파생 — Yes / Yes / 순환 위험 없음
- `rendered/` 5종을 9/24 산출물과 `diff` 했다. 차이는 다음뿐이다:
  - 이름
  - SHA 3종
  - 브랜치 4종
  - subject
  - listing 5행
  - `-eq 5`·`assertEqual(5, …)`
  - 디스패처 nonce·ref
  - 러너는 상수 7줄, 단위 테스트는 import 2줄만 다르다.
- 헬퍼·staged blob 은 렌더 산출물과 바이트 동일하다(helper `685584b0` · contract `65f3253d` · dispatcher `12924985`).
- 계약 가드를 완화하지 않은 판단은 맞다. target 에는 `verify_promotion_chain.py`·`verify_migration_result.py` 가 없다. 9/21 선례 `5961922b` 도 `cloudflare_pages.py`·`test_cloudflare_api.py` 를 바꿨다.
- **순환 위험 없음**:
  - target 코드는 App 토큰 발급 **전에** `github.token`(`persist-credentials: false`)으로만 실행된다.
  - 토큰 발급 뒤에는 `verify_gitops_write_authority.py` 하나만 target 에서 실행된다. 이 파일은 main 과 같은 blob `0495d8aa` 이고 stdlib 만 import 한다. `scripts/release/` 에 추가되는 파일이 없으므로 import shadowing 도 없다.
  - 로컬: `test_cloudflare_api.py` target 14 OK / main 7 OK, `test_release_hardening.py` 24 OK / 24 OK.

### Q5 음성 대조·계약 테스트 — 5종 Yes / 놓치는 변조 찾음(L1)
- `negative_controls.py` 를 헬퍼 트리에 실행했다. 원본 rc=0, 변조 5종 모두 rc=1 이다. 각 변조는 유일한 줄 치환과 적용 여부 단언을 거치므로 거짓 거부가 집계될 수 없다.
- 계약 18/18 · 러너 단위 18/18 을 재현했다.

### Q6 실행 시 위험 — Concern(M1, M2, M3)
계획서가 다루지 않은 것: 아래 M1·M2·M3, 그리고 4단계 검증 항목(qwen2.5:7b 보유·strategy)이다.

## 발견 사항

### Medium

**M1. 폴백을 켜면 세 기능의 Claude SDK 재시도가 2→0 이 된다. 「GPU 상실 = #83 이전 상태라 순손실 아님」 전제는 코드와 다르다.**
- 근거:
  - `ClaudeClients.java:53-55`: `requestedCount(provider, fallbackCsv) >= 2 ? 0 : 2`. `requestedCount` 는 가용 여부를 보지 않는다(`ProviderChain.java:45-50`). 지금 운영은 env 가 없어 재시도 2다.
  - 같은 파일 주석 `:32-48` 이 그 순손실을 직접 적고 있다. community-seed 는 「한 번의 503 이 시드 답변을 영구히 잃는다」, retention 은 「재시도가 아예 없다」.
- GPU 노드가 없거나 엔드포인트가 0 이면(9/08~10/01 에 23일 방치된 선례):
  - Claude 일시 장애 1회 → 재시도 없이 죽은 Ollama 로 넘어가 → 실패한다.
  - Claude 429 → 래치가 claude 를 5분 이상 연다(`ProviderLatch.java:24, 87-90`). 그동안 세 기능 요청 전부가 죽은 Ollama 로만 간다.
  - 노드가 갑자기 사라지면 connect timeout 60초를 물 수 있다.
- **7b 가 없으면 더 나쁘다**:
  - postStart 는 3b 를 먼저, 7b 를 나중에 백그라운드로 받는다(`ollama-gpu deployment.yaml:76`). readiness 는 pull 을 기다리지 않는다. 스팟 복구 런북은 PVC 를 삭제한다.
  - 그 구간에 Ollama 404 → `PermanentReviewException("PARSE_FAILED")`(`OllamaAiReviewClient.java:64-72`) → `ReviewService.java:102-104` `finishFailed` 로 이어진다. 원래 Kafka 로 재시도되던 리뷰가 **영구 실패**가 된다. 404 는 OUTPUT_INVALID 로 분류돼 래치도 열리지 않는다(`ProviderFailures.java:65-66`).
- target 주석(`ai-svc deployment.yaml:98-103`, `ollama-gpu deployment.yaml:29-32`)과 10/02 사용자 결정의 근거가 이 전제다. 계획서 운영 영향은 「파드 1회 재시작」뿐이다.
- 권고:
  - (a) 사용자에게 정정된 조건으로 재확인받는다.
  - (b) 4단계에 `/api/tags` 의 `qwen2.5:7b` 존재 확인과 strategy 확인을 추가하고, 스팟 복구 런북에도 넣는다.
  - (c) 후속 ai-svc 과제로 재시도 예산을 실제 가용성에 연동하거나 Ollama 탐색기를 두는 방안을 검토한다.

**M2. target 자체를 되돌리는 경로가 없다.**
- main 은 App 봇만 움직인다. 롤백 레인이 닫히는 것은 계획서가 인정했다.
- 그러나 이 target 의 효과(폴백 env·Recreate)를 끌 준비된 수단이 없다. Argo selfHeal(`applicationset.yaml:29-32`)이 kubectl 수정을 되돌린다. 역방향 publisher 는 렌더·리뷰부터 다시 해야 한다.
- Part B 3~4단계에는 중단·되돌림 기준이 없다.
- 권고: 긴급 차단 절차를 명시한다(예: devpath-ai-svc 자동 동기화 해제 → `*_FALLBACK` 비우기). 사람 승인이 필요하다고 표시하거나 역방향 target 을 미리 준비할지 결정한다.

**M3. 다음 candidate 의 `ai_release_eval_config.rendered_config_sha256` 를 target 기준으로 다시 계산해야 한다.**
- 로컬 kustomize v5.4.3 렌더 해시:

  | base | 해시 |
  |---|---|
  | `eb41381` | `bfa0126d…` — 10/02 spec 값과 일치, 즉 렌더러가 CI 와 같은 바이트를 낸다 |
  | `cea3610` | `7626f312981121dff9c8b3d9a2d7d95e0ee9e7ee975f7ae7a1a8e0045129850a` |
  | **target** | **`9b7d7031fafe5104ec51200e5c1b90ddd9bc38cd305683c672ee95f5238f4f4f`** |

- 10/02 builder 는 이 필드를 다시 계산하지 않는다(9/23 builder `build_candidate_spec_r2.py:76-98` 는 했다).
- 그대로 복사하면 ai-release-eval 또는 promote/landing `verify_artifacts`(`:3342`)에서 늦게 fail-closed 된다. candidate spec 은 커밋 후 바꿀 수 없으므로 release id 를 버리게 된다.
- 권고: Part B 5단계에 「candidate 해시 = 고정 kustomize 로 target 을 렌더한 값(CI 바이너리로 재확인)」을 추가한다.

### Low

**L1. 계약 테스트가 토큰 발급 전 게이트 step 의 실행·실패 전파를 고정하지 않는다.**
- 다음 변조가 scratch 실측에서 전부 rc=0 으로 **수용**됐다:
  - ① target test step 에 `if: false`
  - ② live env/approval step 에 `continue-on-error: true`
  - ③ helper context step 에 `continue-on-error: true`
  - ④ 최상위 `defaults.run.shell`
  - ⑤ target checkout `persist-credentials: true`
- 원인: `GATE_BODIES` 는 `run` 텍스트만 비교한다(`:461-466`). dict 동등 비교는 mint 이후 step 뿐이다(`:468-475`). 최상위 키 검사는 `env` 만 본다(`:272`).
- 현재 위험은 없다. 헬퍼 바이트가 리뷰된 바이트와 같고, `--helper-sha` 가 고정되며, push 는 고정된 TARGET_SHA·tree 로만 일어난다. 9/24 실행본에도 같은 틈이 있었다.
- 권고(선택): 다음부터 mint 이전 step 도 dict 전체를 비교하고 `defaults`·`if`·`continue-on-error` 를 금지한다. 지금 고치면 헬퍼 SHA 가 바뀌어 재렌더·재리뷰가 필요하다.

**L2. `prove_next_base.py` 의 서술이 실제와 다르다.**
- 「three base checks」라고 쓰지만 실제는 4개다(+AI 렌더 바인딩 별도). 생략이 안전한 이유를 주석으로 남길 것.
- 대조 M 은 service selector 검사로만 거부되므로, writer-fence 가지만 증명한다.

**L3. 계획서 범위 경고가 release-managed kustomization 을 3개로 센다.** admin 을 경고문과 `UNCHANGED` 목록에 추가할 것.

**L4. 계약 테스트 메서드명 `…_twelve_pinned_paths` 가 낡았다(실제 5행).** 동작 영향은 없다.

### Info
- I1. Landing 프로브 최악 예산: 프로브당 90초, `verify-new-production` 은 약 270초로 landing job 30분 안이다. 308 은 즉시 실패, 404·연결 실패는 재시도한다. rollback 도 `_probe` 를 쓰므로 최대 90초 길어진다.
- I2. ci.yml 은 `push: [main]` 만 트리거한다. 비-main 브랜치를 push 해도 러너 preflight CI 검사(`:106,157-158`)에 걸리지 않는다.
- I3. 미완 항목 「target 전체 `tests/release` 로컬 대조」는 대신하지 않았다(kubectl 호출 테스트가 다수). 헬퍼 CI 에서 실패하면 main 은 안전하지만 1회분 실행이 소모된다. Part B 전에 마칠 것.
- I4. `rendered/.omc/` 는 `.gitignore:15` 로 무시된다.
- I5. `NEEDS_CONTEXT`: 라이브 ollama-gpu PVC 의 모델 목록(7b·디스크)과 현재 strategy·RS 수는 kubectl 금지로 확인하지 못했다.

---

## 컨트롤러 대조 (2026-10-03, 보고를 그대로 믿지 않고 재현)

| 지적 | 판정 | 근거 |
|---|---|---|
| M1 재시도 2→0 | **사실** | `83cfe792:src/main/java/ai/devpath/aigw/provider/ClaudeClients.java` `maxRetriesFor` = `requestedCount(provider, fallback) >= 2 ? 0 : SDK_DEFAULT_MAX_RETRIES`, `ProviderChain.requestedCount` 는 가용 여부를 보지 않는다(주석 그대로). 같은 파일 주석이 community-seed 영구 상실·retention 무재시도를 적고 있다 |
| M1 7b 부재 → 리뷰 영구 실패 | **사실** | `OllamaAiReviewClient` 4xx(429 제외) → `PermanentReviewException("PARSE_FAILED")` · `ProviderFailures.fromStatus` 404 → `OUTPUT_INVALID`(래치 안 열림) |
| M2 되돌림 경로 없음 | **사실** | `argocd/applicationset.yaml` `syncPolicy.automated.selfHeal: true` — kubectl 수정은 되돌려진다 |
| M3 rendered_config_sha256 | **사실(범위는 더 넓다)** | `verify_release_artifacts.py:54` `AI_RENDER_PATH = "apps/devpath-ai-svc/base"` 를 렌더해 비교. spec 값 `bfa0126d…`. ★publish 하지 않아도 main `cea3610` 에서 이미 ai-svc 다이제스트가 바뀌어 다음 candidate 는 어차피 재계산이 필요하다(리뷰어 측정 `7626f312…`) — 10/02 생성기의 복사 방식은 **다음 캠페인 전체의 함정**이다 |
| L2 | 반영 | `prove_next_base.py` docstring 을 4검사 구조로 정정, `_require_web(base)` 생략 이유 명시. 실측: 현 spec 으로 target 은 `web-base-digest` 거부, `eb41381` 은 수용 |
| L3 | 반영 | `apps/devpath-admin/base/kustomization.yaml` 을 `UNCHANGED` 에 추가 → 재실행 rc 0 |
| L1 | 미반영(후속) | 헬퍼 SHA 가 바뀌어 재렌더·재리뷰가 필요하다. 9/24 실행본에도 같은 틈. Part B 전에 고칠지는 사용자 결정 |
| L4 | 미반영 | 동작 영향 없음 |
