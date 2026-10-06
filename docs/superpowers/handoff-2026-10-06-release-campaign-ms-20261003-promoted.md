# 핸드오프 — 릴리스 캠페인 `ms-20261003-ai-fallback-retry-budget` **운영 반영 완료** (2026-10-06 06:15Z)

> ai-svc M1 근본 수정(폴백을 쓸 수 없을 때 Claude 재시도 예산 유지)이 운영에 올라갔다.
> 직전 문서 = `handoff-2026-10-03-release-campaign-ms-20261003-validating.md`(8단계 재디스패치 대기 시점).
> **갱신(2026-10-06 07:20Z)**: 3-1·3-2 의 후속 수정(gitops #169 · 홈 #100, 둘 다 develop)과 3-4 디스크 실측을 반영했다. 운영 상태는 1절 그대로다.
> **갱신(2026-10-06 07:45Z)**: 사용자 결정 두 건(publisher 는 리뷰 대기 · GPU 루트 볼륨은 다음 기동부터)을 반영했다.
> 작업 원장(git 밖, 지우지 말 것) = `D:/workspace/dpa/.release-artifacts/ms-20261003-ai-fallback-retry-budget/`
> (`PLAN.md` · `coords.json` · `step8-validate-retry*.log` · `step9-preflight.log` · `step10-*.log` · `chain-final-budget.txt`).
> 사본 = `plans/2026-10-03-release-campaign-ms-20261003-ai-fallback-retry-budget/`(`PLAN.md`·`coords.json` 갱신).

## 1. 운영 상태 (2026-10-06 06:15Z 실측)

| 항목 | 값 |
|---|---|
| gitops main | `9ab0dd790d2e1cdad6a3d7716ad44abee0f6643f` · 체인 `phase=mission-on` |
| ai-svc | `sha256:c3c29ade…`(source `c5614621`) — 파드 1/1·재시작 0·기동 뒤 ERROR 0·폴백 env 9개 유지 |
| web / admin | `sha256:e3108c09…`(mission-on) / `sha256:93b26f9c…` |
| gateway | `sha256:8cf6af8d…`(불변) |
| Argo | 16 앱 Synced/Healthy, rev `9ab0dd79` |
| staging web | `sha256:e3108c09…`(rebaseline 완료) |
| 홈(Pages) | deployment `1c4ea148-e030-424e-a041-2f54f5a93b7b` · 마커가 이번 릴리스에 바인딩 · `/`·`/updates`·`/api/invite-rounds`·`/api/stats` 200 |
| GPU 노드 | `ip-172-31-52-85` Ready · `ollama-gpu` 1/1 · `qwen2.5:7b`·`3b` 보유 |

## 2. 실행 기록

계기는 2026-10-06 04:34Z 의 GPU 스팟 노드(`i-0956cd8d637f6dafd`) **Rebalance Recommendation** 통지였다. 회수는 아니었고 노드는 계속
정상이었지만, 회수되면 운영이 M1 의 나쁜 상태(폴백 불가 + Claude 재시도 0)가 되므로 멈춰 있던 캠페인을 끝내는 것을 완화책으로 삼았다.

| 단계 | 런 | 결과 |
|---|---|---|
| validate 1차 (10/03) | gitops `37118424720` | seal 실패 — `exactly one frontend producer run is required` |
| validate 2차 | gitops `37417289045` | 활성화 저니 실패 — 동의 제출 뒤 `POST /consents` 30초 미발생 |
| validate 3차 | gitops `37418150783` | **success** · sealed `c8ee341d395539544ec62abad21efb406555c1d9` · 매니페스트 `dd8e9626…` |
| preflight | (읽기 전용) | 이미지 9/9 · 체인 `phase=base` · TLS 3600일+ · 잔존 게이트 없음 |
| migration | shared `37419589050` | success · gitops `3cbba3d` |
| promote-off | gitops `37419716583` | success · `600cdc5`(services) → `924d252`(mission-off) |
| promote-on | gitops `37420243377` | success · `9ab0dd7`(mission-on) · canary 900s · staging rebaseline |
| landing | gitops `37422048024` | **failure**(게이트 프로브) — 배포 자체는 성공 |
| landing-resume | gitops `37422475962` | success · `mode=reuse`(재배포 없음) |

승인: staging 관문과 운영 관문 4종(`migration-release`·`production-off`·`production-on`·`production-landing`)은 사용자 「진행」 확인 뒤 AI 가 승인했다(10/02 방침).

## 3. 이번에 드러난 것

### 3-1. landing 게이트 — 홈 dist 가 안 바뀐 릴리스는 첫 런이 실패할 수 있다 (원인 확인)

- 마커 경로는 `.well-known/devpath-release/<dist_sha256>.json` 이고 내용은 `{release_id, candidate_spec_sha256, dist_sha256}` 다.
- 이번 릴리스의 홈 dist(`51e8ef83…`, 소스 `abdf57a7`)는 10/02 릴리스와 **같다** → 경로가 같고 내용만 다르다.
- `wrangler pages deploy` 완료 1.35초 뒤 프로브가 전파 전 엣지에서 **이전 배포의 마커를 HTTP 200 으로** 받았다.
- `scripts/release/cloudflare_pages.py::_probe_marker` 는 비-200·연결 실패만 재시도한다. 내용 불일치(`validate_public_marker`)는 즉시 종료다.
  10/03 에 넣은 프로브 재시도는 404 전파만 덮는다.
- 로그의 `Uploaded 1 files (51 already uploaded)` 가 「새로 올라간 것은 마커 하나」임을 보여 준다.
- 대응: 라이브 마커가 이번 릴리스에 바인딩된 것을 3회 확인한 뒤 `promote.py … landing-resume --confirmed` — 새 런이 preflight 의 `reuse` 분기를 타 재배포하지 않는다.
- 직접 확인(같은 날): 직전 배포 `087c9235` 의 같은 경로가 `release_id=ms-20261002-ai-provider-fallback-gpu7b` 마커를 HTTP 200 으로 돌려준다.
- **수정(2026-10-06, gitops PR #169 → develop `4e804446`)**: 형식이 정상인 「같은 dist·다른 release」 마커는 기존 프로브 예산(최대 30초) 안에서
  재시도한다. 끝까지 안 바뀌면 실패하고, 다른 dist·키가 다른 마커는 그대로 즉시 실패한다. 통과 조건(정확히 일치)은 그대로다.
  #165 가 「다른 release 마커 = 즉시 실패」로 고정했던 테스트 하나를 이 판정으로 바꿨다. CI 372 tests 통과.
- ★**운영 게이트(gitops main)에는 아직 없다.** `scripts/release/` 는 릴리스 PR 로 못 들어가므로 다음 publisher 때 올린다.
  Codex 리뷰는 2026-10-19 까지 한도 소진(10/06 재실측)이라 독립 리뷰 없이 develop 에만 머지했다.
  **사용자 결정(2026-10-06): publisher 로 올리되 리뷰를 기다린다** — 독립 리뷰가 끝나기 전에는 publisher 를 실행하지 않는다.★

### 3-2. validate 활성화 저니 — 동의 단계 타임아웃 (원인 재현·수정)

- 홈 `e2e/release/mission-spine-onboarding.spec.js` 의 `required-consent-claim-replay` 단계에서
  `TimeoutError: page.waitForRequest … POST …/consents`(런 `37417289045`).
- 같은 후보 바이트·같은 staging 백엔드 파드로 10/03 에는 통과했고 11분 뒤 3차도 통과했다. 9/16~9/30 의 실패 6건 로그에는 없던 증상이다.
- **원인**: Flutter 웹은 텍스트 필드가 포커스를 받은 뒤 한두 프레임이 지나야 텍스트 편집을 붙인다. 그 전에 들어간 Playwright `fill` 은
  프레임워크에 닿지 않고, 프레임워크가 자기 값을 DOM 에 되쓴다. 신규 사용자는 그 값이 빈 값이다.
  웹 `consent_page.dart` 의 제출 버튼은 항상 활성이고 `_submitPressed` 안에서 검증하므로 요청 없이 에러 문구만 뜬다.
- **재현**(후보와 같은 Flutter 3.44.1 · frontend main `b69e9990` · `USE_MOCK=true MOCK_PROFILE=consent`, 신규 사용자 조건은 mock 의 `birthYear` 만 `null`):

  | 방식 | 신규 사용자 조건 | 재동의 조건(prefill 1998) |
  |---|---|---|
  | 기존 `fill('1995')` | 32회 중 29회 연도 검증 실패(요청 없음) | 30회 중 17회 입력 유실 |
  | 수정한 순서(헬퍼 + 단언) | 60/60 제출 | 30/30 제출 |

  유실은 prefill 시점과 무관하고(1.5초 기다려도 30회 중 22회), 체크박스는 모든 실행에서 정상이었다.
- **수정(홈 PR #100 → develop `7779e0a3`)**: `support/staging-control.js::fillFlutterTextField` — 값이 300ms 안정 구간을 두 번 버틸 때까지 다시 채운다.
  누르기 전에 필수 동의 2개(`toBeChecked`)와 연도(`toHaveValue`)를 단언한다. 홈 `npm test` 501/501.
- **한계**: 실패했던 런은 Playwright 컨텍스트를 남기지 않았다 — 그 런이 정확히 이 경로였다는 직접 증거는 없고, 같은 서명의 재현이 근거다.
  실제 저니(staging 제어 토큰 필요)는 로컬에서 못 돌렸다. **다음 validate 가 수정본의 첫 종단 실행이다.**
- ★**홈 master 는 롤백 창 동안 동결이라 수정은 다음 candidate 직전에 올라간다.** 그 전에 validate 를 돌리면 옛 스펙이다.★
- 같은 증상이 **연속 2회**면 재디스패치를 멈추고 staging 에서 직접 추적한다.

### 3-3. validate 1차의 seal 실패(10/03)는 여전히 미증명

3일 뒤 같은 seal 코드가 같은 입력에서 `37117660640` 을 골랐다. API 목록 반영 지연이라는 추정을 뒤집는 증거도 굳히는 증거도 새로 없다.

### 3-4. GPU 노드 디스크

`ip-172-31-52-85` 루트 디스크 63.5/72.5 GiB(88%). kubelet 이 `FreeDiskSpaceFailed` 경고를 계속 낸다 — 이미지는 4.6 GiB 뿐이라 이미지 GC 로는 못 줄인다.
k3s 축출 임계(여유 5%)에는 닿지 않았다. 조치는 하지 않았다.

사용처 실측(`du`, 06:26Z): `/usr/local` 41G = AMI 에 들어 있는 CUDA 툴킷 4벌(`cuda-12.8` 11G · `12.9` 12G · `13.0` 9G · `13.2` 9G) ·
`/var/lib/rancher/k3s` 15G(agent 8G + 모델 PV 7G) · `/var/lib/kubelet` 7G. 즉 디스크의 과반이 AMI 기본 탑재물이고 워크로드는 22G 안팎이다.
노드는 회수 때마다 AMI 에서 다시 만들어지므로, 손볼 곳은 살아 있는 노드가 아니라 기동 절차다.
**사용자 결정(2026-10-06): 다음 노드 기동부터 볼륨업** — gitops 런북에 120 GiB gp3 를 명시했다(PR #170 → develop `f36dbd54`, `RunInstances` DryRun 으로 수락 확인). 120 은 제안값이고 실제 기동은 아직 없다.
GPU 노드 SSH 는 공인 IP 로 직접 붙었다. control-plane 경유(ProxyCommand)는 타임아웃이었다 — 런북의 노드 간 SG 규칙에 22 가 없다.

## 4. 동결 규칙 — 롤백 창

운영 반영 뒤에도 아래 head 들이 이 릴리스의 롤백 워크플로를 연다. **다음 캠페인 candidate 직전까지 움직이지 않는다.**

| 브랜치 | head |
|---|---|
| documents **main** | `f52b4a9a` |
| ai-svc **main** | `c5614621` |
| 홈 **master** | `abdf57a7` |
| gitops **main** | `9ab0dd79` |

develop 머지는 괜찮다.

## 5. 다음 캠페인 입력

- `gitops.base_sha` = `9ab0dd790d2e1cdad6a3d7716ad44abee0f6643f` · base web = `sha256:e3108c09…`
- `ai_release_eval_config.rendered_config_sha256` 는 **재계산**한다(main 의 ai-svc 다이제스트가 `c3c29ade` 로 바뀌었다, 고정 kustomize v5.4.3).
- 홈 `prior_production_deployment_id` = `1c4ea148-e030-424e-a041-2f54f5a93b7b`
- 홈 develop `7779e0a3`(저니 스펙 수정, 3-2)을 master 로 올리면 홈 `source_sha` 가 바뀐다. 바뀐 것은 `e2e/`·`tests/` 뿐이라 dist 해시가 그대로일 수 있다 — 빌드해서 확인한다.
- 3-1 의 게이트 수정이 main 에 올라가기 전에 홈 dist 가 직전과 같은 릴리스를 내면 3-1 이 재현될 수 있다 — landing 첫 런 실패 시 마커를 확인하고 `landing-resume`.
- 서비스 이미지 증거 최단 만료는 여전히 platform-svc **2026-10-15 07:12Z** 다(이번엔 안 바뀐 서비스라 다음 캠페인도 같은 증거를 쓰면 기한이 걸린다).

## 6. 남은 일

1. GPU 스팟 노드는 여전히 회수 위험이 높아진 상태다. 회수되면 학습경로 생성이 멈추고 세 기능의 폴백이 사라진다(이제 Claude 재시도는 유지된다).
   복구 = gitops `docs/runbook-k3s-bootstrap.md` 「스팟 회수 후 복구」(노드 삭제 → 옛 파드 강제 삭제 → PVC 삭제).
2. 3-1 의 게이트 수정을 gitops main 에 올리는 publisher — **리뷰 대기**(Codex 는 2026-10-19 이후). 리뷰가 끝나면 publisher 준비·실행은 사용자 확인 뒤에 한다.
3. 3-2 의 저니 스펙 수정을 다음 candidate 직전에 홈 master 로 올리고, 첫 validate 에서 종단 통과를 확인한다.
4. GPU 노드 루트 볼륨 — 런북 반영 완료. 다음 기동 때 120 GiB 로 띄우고 `df -h /` 로 확인한다.
5. 런북에 적힌 남은 공백(Slack 수신처·미복구 반복 통지)은 이번에 건드리지 않았다.
