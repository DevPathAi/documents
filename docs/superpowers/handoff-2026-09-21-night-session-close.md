# 핸드오프 2026-09-21 (밤, 세션 종료) — r3 앱 승격 완료 · 홈 함수 묶기 PR #91 은 CI 실패로 미머지 · 다음은 "landing 을 실은 다음 릴리스"

> **이 문서 하나만 읽으면 된다.** 같은 날의 세 문서(`…r2-promote-blocked-temporary-unfence` → `…afternoon-main-unfenced-r3-next` → `…evening-r3-promoted-landing-last-next`)는 경과 기록이다. 필요한 절만 아래에서 가리킨다.
> 산출물·스크립트는 레포 밖 `D:/workspace/dpa/.release-artifacts/ms-20260920-community-flat-pages/`(git 저장소 아님) — `r2/` · `r3/` · `unfence-publisher/`.

## 1. 지금 상태 (2026-09-21 세션 종료 시 실측)

| 영역 | 상태 |
|---|---|
| **앱** | 릴리스 **`ms-20260920-community-flat-pages-r3`** 가 운영에 mission-ON. web `sha256:a6466f5d…c4e1`(frontend `31a7785d`) · admin `sha256:53813915…fc91` · 서비스 9개 Synced/Healthy(5개는 오늘 재빌드) · canary·staging rebaseline 통과 |
| gitops `main` | `30c0e9f717efaad9bd46d47721a61495f4093e96`(base `fcf97cf6` → M `7906bdc7` → S `ec54b37c` → OFF `7d973847` → ON `30c0e9f7`). 봉인 불변: 룰셋 2종 active · `enforce_admins` · 보호 환경 전부 `main` 단독 · `prevent_self_review` true |
| **홈(랜딩)** | **직전 배포 `005cf175-6e3e-4400-a201-1987ce9d8d84`(소스 `24c6e748`) 그대로** — landing-last 를 한 번 실행했다가 되돌렸다(§3). 제품 소스는 홈 master `5b9d6e38` 과 같다(차이는 테스트·문서). Pages 이력에 비활성 운영 배포 `9814656f-…` 가 남아 있다 |
| **N01** | **닫힘** — gitops 환경 `mission-spine-production-landing` 의 `CLOUDFLARE_API_TOKEN` 이 정식 `Pages:Edit` 단일 권한 토큰으로 교체됨(`2026-09-21T09:57:53Z`). landing-last 의 preflight·배포를 실제로 통과시켰다 |
| **열린 PR** | **홈 #91 `fix/functions-in-sealed-dist` → develop**(커밋 `3995dfc`, §2) — **CI 실패, 머지하지 않았다**(`MERGEABLE / UNSTABLE`). 그 밖의 레포는 0 |
| 클러스터의 수동 변경 | ServiceAccount `devpath-migration-fence` 의 `imagePullSecrets: ghcr-pull` 하나(무해 — §4 의 매니페스트 결함 보완) |
| 세션 워크트리 | `D:/workspace/dpa/.worktrees/home-functions-in-dist`(홈 #91 의 작업 트리 — 머지 뒤 삭제) |
| 자동 롤백 레인 | r3 기준으로 다시 열렸다(롤백 워크플로를 실제로 돌려 검증한 것은 아니다) |

## 2. 다음 세션 착수점

**① 홈 #91 의 CI 를 녹색으로 만든 뒤 머지한다.** 필수 체크 두 개가 같은 원인으로 실패했다(로컬 `npm test` 495건은 커밋 **전** 작업 트리에서 녹색이었다 — 이 검사는 커밋된 이력을 보기 때문에 커밋 뒤에야 드러난다):
   - `visual-a11y` › "Validate visual and accessibility contracts": `Error: product runtime drifted from rendered commit: build.mjs, scripts/pages-worker.mjs, tests/pages-worker.test.js`(`scripts/visual-evidence.mjs:408` `validateProductRuntimeProvenance`)
   - `test` › `tests/visual-evidence-audit-contract.test.js` › "allows evidence-only and non-rendering descendants while retaining runtime drift detection"
   - **원인(코드로 확인)**: 홈의 시각 증거 계약은 `e2e/visual/candidate-spec.v2.json` 의 `surface.rendered_product_sha`(현재 `16cda0cfb3d1e9a496167873196fa50b4d45eb16`) 이후 HEAD 까지 바뀐 경로가 `EVIDENCE_ONLY_PATHS`·`NON_RENDERING_RELEASE_PATHS`(`scripts/visual-evidence.mjs:27~49`)에 있을 때만 통과시킨다. #91 의 세 파일은 어느 목록에도 없다 — 계약이 의도대로 동작한 것이다. `scripts/mission-spine-home-dist.mjs`·`tests/mission-spine-home-dist.test.js`·`CLAUDE.md`·`AGENTS.md` 는 목록에 있어 걸리지 않았다.
   - **고치는 길(이 레포의 기존 관례)**: 제품 커밋 뒤에 **같은 PR 안에서** 렌더 기준을 그 제품 커밋으로 옮기는 증거 커밋을 잇는다 — 선례 `aec5a6c test(visual): bind token-mirror 1.1.0 candidate`(제품 커밋 `16cda0c` 바로 뒤) · `345818d` · `80a372a`. 절차는 홈 `docs/visual-a11y-evidence.md` 의 "Baseline updates"(`baseline_policy.platform` 의 정확한 이미지 안에서 `npm run visual:baseline:update`, `HOME_VISUAL_BASELINE_*` 환경변수). 허용 목록에 `build.mjs` 를 넣는 식의 우회는 하지 않는다 — `build.mjs` 는 렌더링 입력이다. 이 변경은 화면을 바꾸지 않으므로 PNG 는 그대로이고 핀·tree sha·메타데이터만 움직일 것으로 **예상**하지만(미실측), baseline 의 `approved` 상태가 걸린 사람 검토 관문이 다시 필요한지는 선례 커밋의 diff 로 먼저 확인한다.
   - 확인 명령: `gh pr checks 91 -R DevPathAi/devpath-home-page`. 녹색이 되면 develop 에 merge commit 으로 머지하고 워크트리 `D:/workspace/dpa/.worktrees/home-functions-in-dist` 를 지운다.

   #91 의 내용: `build.mjs` 가 `functions/api/*.js` 를 원천으로 `dist/_worker.js`(Pages advanced mode)를 생성 · 정규 dist 아카이브가 `_worker.js` 없는 dist 의 봉인을 거부. 검증은 끝나 있다 — 단위 495건, 두 번 빌드한 `dist_sha256` 동일, **실제 Pages 에서 landing-last 와 같은 조건(functions/ 없는 디렉터리에서 dist 만 배포)으로 `/api/invite-rounds` 200**, 대조군(함수 없는 배포)은 404, `_routes.json` 이 advanced mode 에서도 `/api/*` 만 워커를 거치게 함을 표시 헤더로 실측.

**② landing 은 다음 릴리스 id 에 실린다.** #91 이 홈 master 에 들어가면 `home.source_sha`·`dist_sha256` 이 바뀌므로 새 candidate 가 필요하다. r3 의 앱 승격은 그대로 유효하고, 홈은 제품 소스가 같아 서두를 이유가 없다 — **다음에 frontend/서비스 릴리스를 할 때 홈을 함께 싣는 것이 자연스럽다.** 그때의 순서는 오늘 r3 가 밟은 그대로다(§5 의 스크립트 재사용). 단 **landing-last 를 다시 돌리기 전에**:
   - 홈 master 의 빌드에 `dist/_worker.js` 가 있는지(#91 이 master 까지 갔는지) 확인한다.
   - Pages 이력의 비활성 운영 배포 `9814656f`(commit_hash `5b9d6e38`)가 mode 판정(`reuse`)·"deploy window / production census" 검사에 걸리지 않는지 `cloudflare_pages.py --action preflight` 를 로컬에서 먼저 돌려 본다(홈 SHA 가 바뀌면 commit_hash 가 달라 무관해질 가능성이 높다 — 추정).
   - **배포 뒤 첫 확인은 200 이 아니라 기능 경로다**: `/api/invite-rounds` 200 JSON · `/api/lead` POST · `/api/stats`.

**③ 남은 파이프라인 결함**(전부 gitops 통제면 → publisher 경로, 오늘의 `unfence-publisher/` 와 9/20 스펙 §11 을 출발점으로):
   - **서비스 Deployment 에 startupProbe 가 없다** — 오늘 herd 사고의 근본 원인. 고치기 전까지는 additive-services 직후 롤아웃을 **먼저** 직렬화한다(옛 파드가 있는 배포를 `rollout pause` + 새 ReplicaSet `scale 0` → writer 가 뜬 뒤 하나씩 `rollout resume`).
   - fence ServiceAccount 의 `imagePullSecrets` 가 매니페스트에 없다(수동 patch 가 사라지면 마이그레이션 Job 이 이미지를 못 받는다).
   - landing-last 에 `/api/*` 라이브 smoke 가 없다.
   - `sandbox-migration-gate` ConfigMap 은 릴리스마다 손으로 만든다(직전 실측값을 상한으로).

**④ 만료 달력** — 서비스 이미지 증거(보존 30일): ai-svc **10/08** · gateway 10/10 · platform 10/15 · admin 10/19 · 오늘 재빌드한 5개 10/21. 다음 캠페인 1단계에서 `gh api repos/<repo>/actions/artifacts` 의 `expires_at` 부터 본다. 재빌드 절차는 §5.

## 3. 오늘 있었던 사고 세 건 (원인과 복구)

| 시각(UTC) | 무엇이 | 원인 | 복구 |
|---|---|---|---|
| 03:19~03:40 (21분) | platform·sandbox 중단 | r2 promote 가 fence 를 풀기 **전** 단계에서 실패 — community·notification 의 immutable-image 아티팩트가 그날 만료(보존 30일). 그 검사는 promote 에만 있었다 | ApplicationSet 에 `ignoreApplicationDifferences` 임시 추가 + 두 앱 auto-sync 끔 + replicas 1 → 오후에 publisher 로 main 의 fence 를 걷어내고 원복 |
| 08:05~08:18 (12분 40초) | platform·sandbox 중단 | r3 additive-services 가 재빌드한 서비스 5개를 한꺼번에 롤링 — 단일 노드(4 CPU)에서 JVM 6개 동시 기동(load 61), startupProbe 부재로 liveness 가 50초에 전부 죽임. 재빌드 범위를 5개로 넓히자는 내 권고의 숨은 비용이었다 | git·Argo 무접촉: 4개 배포 pause + 새 RS 0 → writer 기동 → 하나씩 resume(각 ~23초). 이후 재시작 이력이 남은 두 파드를 하나씩 교체(런타임 검증기가 `restartCount == 0` 요구) |
| 10:17~10:20 (2분 30초) | 홈 `/api/*` 404 | landing-last 는 봉인된 dist 만 올린다 — `functions/` 가 dist 밖이라 Pages Functions 가 빠짐 | Cloudflare Pages 롤백 API 로 직전 배포 복귀 → 홈 #91 로 근본 수정 |

세 건의 공통점: **사전 검증이 "검사가 통과하는가"만 봤다.** 첫째는 뒤 단계의 검사를 읽지 않았고, 둘째는 "이 커밋이 클러스터에서 무엇을 동시에 일으키는가"를, 셋째는 "배포물에서 무엇이 빠지는가"를 묻지 않았다. 둘째·셋째는 어떤 검증기에도 없는 질문이었다.

## 4. 교훈 (다음 캠페인의 점검표)

1. **운영을 바꾸는 단계 앞에서 세 가지를 묻는다**: (a) 그 뒤 워크플로의 `verify_*` 를 전부 읽기 전용으로 미리 돌렸는가 — 오늘 r3 에서는 promote 의 실제 `verify_service_image_evidence.py` 와 landing 의 `cloudflare_pages.py --action preflight` 를 로컬에서 끝까지 돌렸고 둘 다 실전과 같은 결과였다 (b) 이 커밋이 **동시에** 무엇을 재시작시키는가 (c) 배포물에 **빠지는 것**은 없는가(preview 와 CI 배포의 wrangler 출력을 나란히 놓는다).
2. **fence 를 거는 단계와 푸는 단계 사이에는 되돌릴 길이 없다.** 롤백 워크플로·PR·수동 sync 모두 fence-only 상태를 못 푼다(publisher 뿐). 선배치(관문 ConfigMap · SA pull secret)로 마이그레이션 Job 은 20초에 끝난다 — 9/16 의 43분은 이 둘이 빠져서였다.
3. **계약의 미러는 전 레포 grep 으로 센다.** candidate-spec 계약의 미러가 frontend·gitops 말고 홈 여정 하니스에도 있었다(홈 #89). 새 로컬 관문: candidate 를 push 하기 전에 핀된 홈 SHA 의 하니스에 spec 을 먹여 본다.
4. **seal 은 증거 종류마다 적격 producer "정확히 1개"를 요구한다.** 성공한 증거를 같은 id 로 다시 디스패치하면 봉인이 막힌다 — 고치려면 새 id(`-rN`).
5. **재개형 워크플로는 실패를 값싸게 만든다.** promote 는 phase 를 스스로 판정한다 — 원인을 고치고 빈 nonce 커밋으로 잇는다. 같은 step 의 두 실패가 다른 원인일 수 있으니 재개 전에 매번 로그를 읽는다.
6. **통째 되돌림은 안전해 보이지만 부작용을 되살린다**(이미 prune 된 Job 의 재실행). 되돌릴 때는 클러스터가 그 상태를 어떻게 다시 해석하는지를 본다.
7. **커밋된 이력을 보는 검사는 커밋 전의 로컬 테스트로 드러나지 않는다.** 홈 #91 은 작업 트리에서 495건 녹색이었지만, 렌더 기준 커밋 이후의 `git diff` 를 보는 provenance 검사는 커밋 뒤에야 실패했다. 홈에서 `build.mjs`·`scripts/`·`tests/` 를 건드리면 push 전에 **커밋한 상태로** `npm test` 와 `npm run visual:contracts` 를 한 번 더 돌린다.
8. 환경 함정: 워크트리는 **절대경로**로만(`git -C <repo> worktree add` 의 상대경로는 그 레포 기준) · `!` 접두는 **bash** — 사용자에게 줄 명령은 bash 문법 · Python `subprocess` 의 bare `bash` 는 WSL 로 풀릴 수 있다 · gitops 검증기를 로컬에서 돌릴 때 `PYTHONUTF8=1` · 활성 wrangler 설정은 `%USERPROFILE%\.wrangler\config\default.toml` · documents PR 은 생성 직후 `pull_request` 이벤트가 누락될 때가 있다(close/reopen) · 리뷰 서브에이전트에는 처음부터 "보고 전문을 지정 파일에, 응답은 3줄".

## 5. 재사용할 것

| 무엇 | 어디 |
|---|---|
| r3 가 밟은 전체 순서와 좌표 | `handoff-2026-09-21-evening-r3-promoted-landing-last-next.md` §2·§7 |
| provenance 계산 · candidate spec 파생(검증기를 통과한 직전 spec 에서 바뀐 필드만 단언) · 디스패처 렌더링 | `.release-artifacts/…/r3/`(`run_provenance_r3.py` · `build_candidate_spec_r3.py` · `dispatchers/`) |
| promote 사전 검증(9개 이미지 증거를 gitops 실제 코드로) | `r3/preverify_service_images.py` |
| 서비스 main 재빌드(보호 완화→squash 머지→복원, 스냅샷 대조) | `r3/release_merge.py` — 사용자 결정이 매번 필요하다(1인 조직이라 `reviews=1` 을 채울 계정이 없다) |
| 보호 환경 승인 헬퍼 | `approve_gate.py` |
| main 을 publisher 로 움직이기(준비·계약 테스트·변이 검사·실행 트랜잭션) | `unfence-publisher/` + documents `specs/2026-09-20-gitops-main-promotion-via-publisher-design.md` §11 · `plans/2026-09-21-gitops-main-writer-fence-removal-via-publisher/` |
| 운영 k3s 접근 · 일회성 읽기 전용 psql 파드 | 메모리 `devpath-prod-k3s-access.md` |

## 6. 사람 단계

- (없음 — N01 은 닫혔다.) 다음 릴리스에서 사람 관문 4건(baseline·프라이버시·AI 평가·NVDA)이 다시 온다. 소스가 그대로면 "동일 대상 재바인딩"이다.
- 앞에서 넘어온 것: 모바일 서명 시크릿 4종 이전 · YouTube 재업로드 · 로그인 캡처 · AdSense 결정.
