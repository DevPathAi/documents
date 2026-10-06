# 핸드오프 — 릴리스 캠페인 `ms-20261003-ai-fallback-retry-budget` **운영 반영 완료** (2026-10-06 06:15Z)

> ai-svc M1 근본 수정(폴백을 쓸 수 없을 때 Claude 재시도 예산 유지)이 운영에 올라갔다.
> 직전 문서 = `handoff-2026-10-03-release-campaign-ms-20261003-validating.md`(8단계 재디스패치 대기 시점).
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
- **후속 수정 후보(gitops, 다음 publisher 때)**: 마커가 「같은 dist·다른 release」를 가리키면 전파 중으로 보고 재시도하거나, 마커 경로에 release id 를 넣는다.

### 3-2. validate 활성화 저니 — 동의 단계 간헐 타임아웃 (**원인 미규명**)

- 홈 `e2e/release/mission-spine-onboarding.spec.js` 의 `required-consent-claim-replay` 단계에서
  `TimeoutError: page.waitForRequest … POST …/consents`(런 `37417289045`).
- 같은 후보 바이트·같은 staging 백엔드 파드로 10/03 에는 통과했고 11분 뒤 3차도 통과했다. 9/16~9/30 의 실패 6건 로그에는 없던 증상이다.
- 코드로 확인한 약점(원인 단정 아님): 웹 `consent_page.dart` 의 제출 버튼은 항상 활성이고 검증은 `_submitPressed` 안에서 한다.
  체크박스·연도가 Flutter 상태에 안 들어가면 요청 없이 에러 문구만 뜬다. 스펙의 `toBeEnabled()` 는 폼 유효성을 보장하지 않고, 실패 시 Playwright 컨텍스트를 올리는 단계가 없다.
- 후속 후보(홈 master 동결이 풀린 뒤): 제출 전에 체크박스·연도 값을 단언하고, 실패 시 `error-context.md`·trace 를 아티팩트로 올린다.
- 같은 증상이 **연속 2회**면 재디스패치를 멈추고 staging 에서 직접 추적한다.

### 3-3. validate 1차의 seal 실패(10/03)는 여전히 미증명

3일 뒤 같은 seal 코드가 같은 입력에서 `37117660640` 을 골랐다. API 목록 반영 지연이라는 추정을 뒤집는 증거도 굳히는 증거도 새로 없다.

### 3-4. GPU 노드 디스크

`ip-172-31-52-85` 루트 디스크 63.5/72.5 GiB(88%). kubelet 이 `FreeDiskSpaceFailed` 경고를 계속 낸다 — 이미지는 4.6 GiB 뿐이라 이미지 GC 로는 못 줄인다.
k3s 축출 임계(여유 5%)에는 닿지 않았다. 조치는 하지 않았다.

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
- 홈이 또 안 바뀌면 3-1 이 재현될 수 있다 — landing 첫 런 실패 시 마커를 확인하고 `landing-resume`.
- 서비스 이미지 증거 최단 만료는 여전히 platform-svc **2026-10-15 07:12Z** 다(이번엔 안 바뀐 서비스라 다음 캠페인도 같은 증거를 쓰면 기한이 걸린다).

## 6. 남은 일

1. GPU 스팟 노드는 여전히 회수 위험이 높아진 상태다. 회수되면 학습경로 생성이 멈추고 세 기능의 폴백이 사라진다(이제 Claude 재시도는 유지된다).
   복구 = gitops `docs/runbook-k3s-bootstrap.md` 「스팟 회수 후 복구」(노드 삭제 → 옛 파드 강제 삭제 → PVC 삭제).
2. 3-1·3-2 의 후속 수정.
3. 런북에 적힌 남은 공백(Slack 수신처·미복구 반복 통지)은 이번에 건드리지 않았다.
