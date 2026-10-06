# 핸드오프 — 2026-10-06 세션 마무리 (M1 운영 반영 → 드러난 결함 2건 수정 → 결정 2건)

> 앞 문서: `handoff-2026-10-06-release-campaign-ms-20261003-promoted.md`(PR #211~#213) — 캠페인 실행 기록과 결함 분석의 상세.
> 이 문서는 세션 전체를 다음 세션에 넘기는 요약이다. **다음 세션 첫 동작은 §1.**
> 원장(git 밖, 지우지 말 것) = `D:/workspace/dpa/.release-artifacts/ms-20261003-ai-fallback-retry-budget/` ·
> 사본 = `plans/2026-10-03-release-campaign-ms-20261003-ai-fallback-retry-budget/`.

## 0. 한 줄 요약

GPU 스팟 노드의 회수 위험 통지를 계기로 멈춰 있던 캠페인 `ms-20261003-ai-fallback-retry-budget` 를 끝내 **M1 수정이 운영에 올라갔다**.
그 과정에서 드러난 결함 2건을 develop 까지 고쳤고, 운영 게이트 반영과 GPU 볼륨은 사용자 결정대로 대기·예약 상태다. **지금 바로 해야 할 일은 없다.**

## 1. 다음 세션 첫 동작

### 1-0. 세션 시작 점검 (읽기 전용)

1. GPU 노드가 살아 있는가 — `i-0956cd8d637f6dafd` 상태, 노드 `ip-172-31-52-85` Ready, `ollama-gpu` 1/1.
   2026-10-06 04:34Z 에 Rebalance Recommendation 이 왔고 07:38Z 까지 회수되지 않았다. 회수 완료 메일(SNS 규칙 ②)이 왔는지 확인한다.
2. 동결 head 4개가 §3 표와 같은가.
3. 운영: Argo 16 앱 Synced/Healthy · ai-svc `sha256:c3c29ade…`.

### 1-1. 조건이 되면 하는 일

| 조건 | 할 일 |
|---|---|
| GPU 노드가 회수됐다 | gitops `docs/runbook-k3s-bootstrap.md` 「스팟 회수 후 복구」. **루트 볼륨 120 GiB** 로 띄운다(「절차」 2). 인스턴스 기동은 비용이 드니 사용자 확인 뒤에. 첫 기동이므로 `df -h /` 가 약 116G 인지 확인하고 런북의 「아직 띄운 적 없다」 문구를 고친다 |
| 2026-10-19 15:13 이후 (Codex 한도 해제) | gitops #169(landing 마커 재시도)의 독립 리뷰 → 지적 처리 → publisher 준비 → **사용자 확인** → 실행. 아래 주의 참고 |
| 다음 캠페인을 시작한다 | §4 의 입력값과 체크리스트 |
| 2026-10-15 07:12Z 가 지났다 | platform-svc 이미지 증거 아티팩트(`10384972238`)가 만료된다. 다음 캠페인 preflight 의 이미지 사전 검증이 그 서비스에서 실패하므로 증거를 새로 만들어야 한다 |

**publisher 주의** — 사용자 결정(2026-10-06, 원문 「publisher/리뷰대기」)은 「publisher 로 올리되 독립 리뷰가 끝나기 전에는 준비·실행하지 않는다」로 해석해 기록했다.
publisher 는 gitops main 을 움직인다. main 이 움직이면 이 릴리스의 자동 롤백 레인이 닫히고 다음 candidate 의 `gitops.base_sha` 가 그 결과가 된다.
그래서 실행 시점은 다음 candidate 직전과 묶는 것이 맞다. 선례 = `plans/2026-10-03-gitops-main-ai-fallback-probe-via-publisher.md`(L1 보강 렌더러에서 파생할 것).

## 2. 이 세션에서 한 것

| 레포 | PR | 내용 | 머지 |
|---|---|---|---|
| gitops | #169 | landing 게이트 — 같은 dist·다른 release 마커를 프로브 예산 안에서 재시도 | develop `4e804446` |
| gitops | #170 | 런북 — GPU 노드 루트 볼륨 120 GiB gp3, 디스크 실측 | develop `f36dbd54` |
| 홈 | #100 | 릴리스 저니 — `fillFlutterTextField` + 제출 전 단언 | develop `7779e0a3` |
| documents | #211 · #212 · #213 | 캠페인 핸드오프와 그 갱신 | develop `5fc4c7c4` |

PR 을 거치지 않은 것(캠페인 절차):

- gitops 디스패처 브랜치 `automation/dispatch-ms-20261003-ai-fallback-retry-budget` 에 봇 이름 커밋 6개
  (validate 재디스패치 `57c3dd3`·`40ba8b6` · promote `cb3ac260`·`4f733dae` · landing `251ee7ff`·`6984f75a`), shared 같은 이름 브랜치에 1개.
- 릴리스 봇이 gitops main 에 올린 승격 커밋 4개(`3cbba3d` → `600cdc5` → `924d252` → `9ab0dd7`)와 candidate 브랜치의 seal 커밋 `c8ee341d`.
- 운영 관문 승인 5회(migration-release · production-off · production-on · production-landing ×2) — 사용자 「진행」 확인 뒤 AI 가 승인.
  staging 관문 4회(validate 2차 1 · 3차 2 · promote-on 의 rebaseline 1)는 10/02 방침대로 AI 가 승인.

사용자 결정(이 세션): ① preflight 뒤 「진행」(운영 관문 AI 승인) ② 후속 3건 「진행」 ③ 「publisher/리뷰대기/다음 노드 기동부터 볼륨업」.

## 3. 현재 상태 (2026-10-06 07:38Z 실측)

| 항목 | 값 |
|---|---|
| 운영 | Argo 16 앱 Synced/Healthy rev `9ab0dd79` · ai-svc `c3c29ade`(1/1·재시작 0·ERROR 0) · web `e3108c09` · admin `93b26f9c` · `leva.ai.kr`·`app`·`api` 200 |
| 노드 | `ip-172-31-48-82`(control-plane) Ready · `ip-172-31-52-85`(GPU 스팟, 루트 75 GiB 88%) Ready · `ollama-gpu` 1/1 |
| 홈 Pages | deployment `1c4ea148-e030-424e-a041-2f54f5a93b7b` · Git 연동 없음(직접 업로드만, develop 머지는 배포를 유발하지 않는다) |

| 브랜치 | head | 비고 |
|---|---|---|
| gitops **main** | `9ab0dd79` | **동결**(롤백 창) |
| 홈 **master** | `abdf57a7` | **동결** |
| documents **main** | `f52b4a9a` | **동결** |
| ai-svc **main** | `c5614621` | **동결** |
| gitops develop | `f36dbd54` | #169·#170 이 main 보다 앞서 있다 |
| 홈 develop | `7779e0a3` | #100 이 master 보다 앞서 있다 |
| documents develop | 이 문서의 PR 머지 커밋 | |

동결은 다음 캠페인 candidate 직전까지다. develop 머지는 괜찮다.

## 4. 다음 캠페인 입력과 체크리스트

- `gitops.base_sha` = `9ab0dd790d2e1cdad6a3d7716ad44abee0f6643f`(그 전에 publisher 를 돌렸으면 그 결과) · base web = `sha256:e3108c09…`
- `ai_release_eval_config.rendered_config_sha256` **재계산**(main 의 ai-svc 다이제스트가 `c3c29ade` 로 바뀌었다, 고정 kustomize v5.4.3)
- 홈 `prior_production_deployment_id` = `1c4ea148-e030-424e-a041-2f54f5a93b7b`
- 홈 develop → master(저니 수정 #100). 홈 `source_sha` 가 바뀐다. 바뀐 파일은 `e2e/`·`tests/` 뿐이라 dist 해시는 그대로일 수 있다 — 빌드해서 확인한다.
- ★**그 캠페인의 validate 가 저니 수정본의 첫 종단 실행이다.** 로컬 검증은 mock 빌드의 동의 화면까지만 했다.
  동의 단계에서 또 실패하면 재디스패치하지 말고 로그의 단언 메시지부터 읽는다(이제 `toBeChecked`·`toHaveValue`·`Flutter text field did not keep the filled value` 중 하나로 드러난다).★
- 게이트 수정이 main 에 없는 상태에서 홈 dist 가 직전과 같으면 landing 첫 런이 `public dist marker does not bind the exact release artifact` 로 실패할 수 있다.
  라이브 마커가 이번 `release_id` 를 가리키는지 확인한 뒤 `py promote.py coords.json landing-resume --confirmed "<reason>"`.

## 5. 이번 세션의 함정과 교훈

- ★**Rebalance Recommendation 은 회수가 아니다.** 인스턴스·스팟 요청·노드·파드를 실측한 뒤 판단한다. 이번 통지의 실제 위험은 노드가 아니라
  운영에 남아 있던 M1(폴백 켜짐 = Claude 재시도 0)이었다.★
- ★**Playwright `fill` 은 Flutter 웹 텍스트 필드에서 유실된다**(포커스 직후 편집 미부착). 느린 CI 에서는 대체로 통과해 간헐로만 보인다.
  값이 유지되는지 확인하고 다시 채운다(홈 `fillFlutterTextField`). 재현 스크립트 = 사본 `consent-step-repro/`.★
- ★**「항상 활성」 버튼 앞의 `toBeEnabled()` 는 아무것도 보장하지 않는다.** 누를 때 검증하는 폼은 누르기 전에 폼 상태를 단언한다.★
- ★**마커처럼 「경로는 같고 내용만 릴리스별로 다른」 공개 파일은 전파 중에 200 으로 옛 내용이 온다.** 404 재시도만으로는 못 덮는다.★
- validate 가 실패하면 실패 지점부터 가른다. 같은 릴리스에서 1차는 seal, 2차는 저니였고 원인도 조치도 달랐다. 재디스패치는 「간헐인지 가르는 실험」으로 1회만 썼다.
- gitops 전체 테스트는 로컬 Windows 에서 12분을 넘겨도 끝나지 않았다(CI 는 372개 19초). 로컬은 관련 파일만 돌리고(4개 파일 103개 760초) 전체는 PR 의 CI 로 확인한다.
- Git Bash 에서 `git show origin/main:<path>` 는 경로가 변환돼 실패한다 → `MSYS_NO_PATHCONV=1` 을 주고, 그때는 `-C` 에 `D:/…` 형식을 쓴다.
- `promote.py` 의 `save()` 는 Windows 에서 `coords.json` 을 CRLF 로 쓴다. documents 사본으로 복사할 때 LF 로 맞춘다(안 맞추면 전체 줄이 diff 로 잡힌다).
- 세션의 작업 디렉터리가 워크트리 안이면 `git worktree remove` 가 등록만 풀고 폴더를 남긴다(이번에도 재현). 밖으로 나온 뒤 폴더를 지운다.
- GPU 노드 SSH 는 공인 IP 로 직접 붙는다. control-plane 경유는 타임아웃이다(노드 간 SG 규칙에 22 가 없다).
- Codex CLI 는 2026-10-06 에 다시 호출해 봤고 여전히 한도 소진이다.

## 6. 환경과 자산

- **원장**: `PLAN.md`(세션 마감 절까지) · `coords.json`(`validate`·`production` 채움) · `sealed-release-manifest-budget.json` ·
  `step8-validate-retry*.log` · `step9-preflight.log` · `step10-*.log` · `chain-final-budget.txt` · `collect_seal.py` · `consent-step-repro/`.
- **남겨 둔 워크트리**(`D:/workspace/dpa/.worktrees/`, 전부 원격과 동기·미커밋 없음): `gitops-dispatch-1003` · `gitops-candidate-1003`(sealed) ·
  `gitops-main-1003`(main `9ab0dd79` detached) · `shared-dispatch-1003` · `fe-dispatch-1003` · `fe-main-1003` · `docs-dispatch-1003` · `home-master-1002`.
  롤백 워크플로를 띄우게 되면 이 디스패처 브랜치들을 쓴다. 이 세션이 만든 작업용 워크트리(documents 4 · gitops 2 · 홈 1 · frontend 1)는 남기지 않았다.
- **이 세션이 건드리지 않은 것**: 각 레포 본 클론의 작업 브랜치(gitops `fix/bypass-observable-contract` ahead 2 · shared `fix/question-811-option-collision` ahead 1 등)는 세션 시작 때 그대로다.
- **핀 Flutter**: `D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin`(PATH 의 flutter 는 3.47.2).
- **운영 접근**: `ssh -i ~/.ssh/devpath-k3s-key-lf.pem ubuntu@13.124.153.105` 후 `sudo kubectl …`. AWS 는 MCP `run_script`.
