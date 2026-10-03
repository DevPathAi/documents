# GPU Ollama 폴백 env + Landing 프로브 재시도 publisher — 준비 기록 (2026-10-03)

> **준비(Part A) 완료 — 실행(Part B, gitops main 이동)은 하지 않았다.** Part B 전에 ★리뷰 M1(사용자 결정 전제 정정)★을 다시 묻는다. 디렉터리
> `2026-10-03-gitops-main-ai-fallback-probe-via-publisher/` 가 스크립트·렌더 산출물이다.
> 선례: `2026-09-24-gitops-main-gateway-edge-cors-via-publisher.md`(렌더러 원형) ·
> `2026-09-21-gitops-main-pipeline-defects-via-publisher.md`(publisher 원형, 같은 형태의 target).

**Goal:** 릴리스 `ms-20261002-ai-provider-fallback-gpu7b` 로 운영에 들어간 ai-svc `107fd20a`(#83 폴백 코어 · #84 기능별
Ollama 엔드포인트)의 폴백을 실제로 켠다. 폴백을 켜는 env 는 gitops Deployment 에 있어 릴리스에 실릴 수 없었다 — main PR 정책이
`apps/`·`scripts/release/` 를 막고, promote 는 `kustomization.yaml` 만 쓴다. env 가 없으니 지금 운영의 폴백은 **꺼져 있다**.

## 사용자 결정 (2026-10-03)

1. **준비만 지금** — 실행은 다음 캠페인을 시작할 때(documents main 릴리스와 같은 시점) 한 번 더 확인한 뒤.
   이유: publisher 가 main 을 움직이는 순간 방금 반영한 릴리스의 자동 롤백 레인이 다음 승격까지 닫힌다(선례 9/20·9/23).
2. **범위 = 폴백·프로브만** — develop 의 staging 정비(staging 이미지 3개·route 8080·migration job·gateway CORS·TLS 10년
   스크립트)는 넣지 않는다.

## ★범위 함정 — develop 트리를 그대로 올리면 운영이 되돌아간다★

main↔develop 사이에서 릴리스가 관리하는 kustomization **4개**에 develop 은 **r3 값**을 들고 있다(실측, admin 은 리뷰 L3 가 찾음):
`apps/devpath-web/base/kustomization.yaml`(web `3a6ab8db…`) · `apps/devpath-ai-svc/base/kustomization.yaml`(ai-svc `eb6f3c2b…`) ·
`apps/devpath-admin/base/kustomization.yaml`(admin `5847d5e9…`) · `apps/devpath-migration/base/kustomization.yaml`(manifest `2f41143f…`).
main 쪽 최종 작성자는 전부 promote 봇 커밋이다.
→ target 은 develop 트리가 아니라 **main + 고른 5경로**로 만든다. `prove_next_base.py` 가 위 4개와 마이그레이션 파일들이
main 과 바이트 동일함을 단언한다.

## target

`a97a175466962e33ca1823edbb6656091700db81` · 트리 `fa3bcc60b2e9bb018ae0362c16f28696a028e470` · 부모 `cea3610`(mission-on, landing 완료) ·
봇 신원 · 고정 시각 2026-10-03T03:00:00Z · subject `release: enable the GPU Ollama Claude fallback and retry the Landing probes` · 5경로 M:

| 경로 | 내용 | 운영 영향 |
|---|---|---|
| `apps/devpath-ai-svc/base/deployment.yaml` | env 9개 — retention·community-seed·review 의 `*_FALLBACK=ollama` · `*_OLLAMA_MODEL=qwen2.5:7b` · `*_OLLAMA_BASE_URL=http://ollama-gpu.devpath.svc:11434` | ai-svc 파드 1회 재시작 |
| `apps/devpath-ollama-gpu/base/deployment.yaml` | `strategy: Recreate` · 기동 시 `ollama pull qwen2.5:7b` 추가 | ollama-gpu 파드 1회 재시작(Recreate — spec 이 strategy 와 template 을 한 번에 바꾸므로 새 strategy 로 롤아웃, 단일 GPU 교착 없음) |
| `scripts/release/cloudflare_pages.py` · `tests/release/test_cloudflare_api.py` | Landing 프로브 6회/30초 재시도, 404·연결 실패·308 구분 | 다음 landing-last 부터 |
| `docs/runbook-k3s-bootstrap.md` | GPU 스팟 회수 후 복구 절차·탐지 공백 | 없음 |

5경로 blob 은 gitops develop `e6730ed` 과 **바이트 동일**(리뷰된 PR #165·#166·#167). merge-base `eb41381` 이후 main 쪽에서 이 5경로를
바꾼 커밋은 0개 — develop blob 이 main 쪽 변경을 되돌리지 않는다.
라이브(2026-10-03 실측): `ollama-gpu` RollingUpdate·Synced/Healthy, ai-svc 에 폴백 env 없음 — 수동 적용분 없음.

## Tasks

- [x] 소스 — gitops `dev/ai-fallback-probe-20261003` `913757e`(main + develop 5 blob, autocrlf=false)
- [x] target — `make_ai_fallback_probe_target.py <clone> <source> [expected]` → `target.txt`, 재실행 동일 SHA
- [x] 다음 base — `prove_next_base.py`: target **수용** · 대조 main `cea3610` 수용 · 대조 fenced M `c1d5e8cf` **거부**
- [x] 선례 입력 재현 — 9/21 실행본 5종(헬퍼·계약 테스트·디스패처 = gitops 브랜치 `git show`, 운영 트랜잭션·단위 테스트 = documents)으로
      9/24 렌더러를 다시 돌려 9/24 `rendered/` 5종과 **바이트 일치**, 헬퍼는 라이브 9/24 헬퍼 브랜치와도 일치
- [x] 렌더 — `render_ai_fallback_probe_publisher.py <scratch with prec-0921-live/ prec-0921/> <this dir>` → `rendered/`
      (9/24 대비 차이 = 이름·SHA·브랜치·경로 5행·`-eq 5` 뿐. 계약 가드 완화 없음 — 체인·마이그레이션 검증기를 건드리지 않는다)
- [x] 헬퍼 `868afac`(`chore/ai-fallback-probe-publish-20261003`, 부모 `cea3610`, 2경로) · 계약 **18/18**
- [x] staged `3b424ff`(`chore/ai-fallback-probe-publish-dispatcher-staged-20261003`, 부모 `cea3610`, 1경로)
- [x] 운영 트랜잭션 단위 테스트 **18/18**
- [x] 음성 대조 `negative_controls.py` — 원본 수용 + 변조 5종 거부(listing 행 삭제 · `-eq 5→4` · `push --force` · TARGET_TREE · target 스위트 축소)
- [x] target 전체 `tests/release` 로컬 대조 — 소스 **368 OK**(skip 3, 867초) vs main 기준선 361 OK(skip 3) · 양쪽 실패 0 ·
      +7 = Landing 프로브 재시도 테스트. 헬퍼는 실행 시 러너에서 같은 스위트를 다시 돈다
- [x] 운영 효과 실측 — ai-svc `83cfe792`(운영 이미지 `107fd20a` 의 소스) `application.yml` 에 env 9개 전부 바인딩(`:39·42·45·73·75·77·86·87·89`)
- [x] origin 에 비-main 브랜치 3개 push — `fix/ai-fallback-probe-main-20261003` = target · 헬퍼 · staged(`helper.txt`·`staged.txt`).
      방아쇠 `automation/dispatch-ai-fallback-probe-main-publish` 는 **만들지 않았다**. gitops 에서 push 로 도는 워크플로는 `ci.yml`(main 전용)뿐이라
      아무 런도 뜨지 않았다(실측) — preflight 의 「target 에 CI 미실행」 조건도 보존된다
- [x] `--preflight-only` → `{"preflight": "ok"}` rc 0 · 뒤에 환경 정책 `branch:main` 그대로 · 방아쇠 브랜치 없음(쓰기 흔적 0)
- [x] 독립 리뷰 → `review-2026-10-03/REPORT.md`(아래 절)

## 독립 리뷰 (2026-10-03) — `review-2026-10-03/REPORT.md`

**Ready: No — 산출물 재작업은 불필요, Part B 전에 반영할 Medium 3건.** 컨트롤러가 셋 다 코드로 재현했다(REPORT 끝 「컨트롤러 대조」).

- **★M1 — 10/02 사용자 결정의 전제가 코드와 다르다★.** 「GPU 를 잃으면 #83 이전 상태로 돌아갈 뿐 순손실이 아니다」가 틀렸다.
  폴백을 켜면(`*_FALLBACK=ollama`) `ClaudeClients.maxRetriesFor` 가 Claude SDK 재시도를 **2 → 0** 으로 내린다(가용 여부와 무관).
  그래서 GPU 가 없거나 7b 가 아직 안 받아졌을 때는 Claude 일시 장애 1회가 곧바로 죽은 Ollama 로 넘어가 실패한다 —
  community-seed 는 그 질문의 시드 답변을 영구히 잃고, review 는 Ollama 404 가 `PARSE_FAILED` 영구 실패가 된다(원래는 Kafka 재시도).
  429 면 래치가 Claude 를 닫는다(`ProviderLatch` — Retry-After 가 있으면 그만큼, 없으면 5분부터 최대 1시간까지 증가) — 그동안 전부 죽은 Ollama 로 간다. **Part B 전에 이 정정된 조건으로 사용자에게 다시 묻는다.**
  후속 후보: ai-svc 의 재시도 예산을 실제 가용성에 연동.
- **M2 — target 효과를 끌 준비된 수단이 없다.** Argo `selfHeal: true` 라 kubectl 수정은 되돌려진다. 긴급 차단 절차를 아래에 둔다.
- **M3 — 다음 candidate 의 `ai_release_eval_config.rendered_config_sha256` 재계산 필수.** 검증기가 `apps/devpath-ai-svc/base` 를
  렌더해 비교하는데, 10/02 생성기는 이 값을 이전 것 그대로 복사한다. ★publish 와 무관하게 main `cea3610` 에서 이미 ai-svc 다이제스트가
  바뀌었으므로 **다음 캠페인은 어느 쪽이든 재계산해야 한다**★(고정 kustomize v5.4.3 로 렌더, CI 바이너리로 재확인).
- Low: L1 계약 테스트가 토큰 발급 전 step 의 `if`·`continue-on-error`·`defaults` 변조를 못 잡는다(9/24 에도 같은 틈, 현재 바이트는 안전) —
  고치면 헬퍼 SHA 가 바뀌어 재렌더·재리뷰. L2·L3 은 반영했다(증명 docstring 정정, admin 추가). L4 는 이름만의 문제.

## Part B — 실행 (하지 않았다 · 다음 캠페인 시작 시 사용자 확인 후)

0. **M1 재확인** — 정정된 조건(재시도 2→0, GPU·7b 부재 시 이전보다 나빠짐)으로 폴백을 켤지 사용자에게 다시 묻는다.
1. `git fetch` 후 `origin/main == cea3610` 확인 — 움직였으면 target·헬퍼·staged 핀이 전부 무효, Part A 를 새 main 위에서 다시.
2. `run_ai_fallback_probe_main_publish.py --repo-dir <clone> --staged-sha 3b424ff… --helper-sha 868afac… --comment "…" --preflight-only`
3. 사용자 확인 → 같은 명령에서 `--preflight-only` 제거(환경 `mission-spine-production-off` 브랜치 정책 임시 추가 → 방아쇠 push →
   waiting 확인 → main 단독 복원·검증 → 승인 → 성공 → post-verify).
4. Argo 16 앱 refresh → 확인: `devpath-ai-svc` 새 파드 env 9개·재시작 0 · `ollama-gpu` `strategy.type=Recreate`·`rollingUpdate` 부재·RS 1개 ·
   **`ollama-gpu` `/api/tags` 에 `qwen2.5:7b` 존재**(postStart 의 백그라운드 pull 이 끝날 때까지 폴백은 404 영구 실패 경로다 — M1).
5. 다음 candidate: `gitops.base_sha` = target · `rendered_config_sha256` = target 렌더 해시(M3).

### 긴급 차단 (M2) — 폴백이 해를 끼칠 때 (사람 승인 필요)

Argo 가 되돌리므로 순서가 중요하다: ① ApplicationSet 이 생성한 `devpath-ai-svc` Application 의 자동 동기화를 끈다
(ApplicationSet 이 Application 을 다시 쓰므로 실행 시점에 방법을 실측해 정한다) → ② `kubectl -n devpath set env deploy/devpath-ai-svc
RETENTION_FALLBACK- COMMUNITY_SEED_FALLBACK- REVIEW_FALLBACK-` → ③ 원인 해소 후 역방향 target 을 publisher 로 올리거나 자동 동기화를 되돌린다.
GPU 스팟 회수 통지(런북 「스팟 회수 후 복구」)를 받으면 이 절차를 함께 검토한다.
