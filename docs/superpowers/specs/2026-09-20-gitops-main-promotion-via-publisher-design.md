# gitops main 승격 — 체인 밖 통제면 변경을 one-shot publisher 로 올리는 설계

> 2026-09-20. 착수 근거는 `handoff-2026-09-19-night-s2-done-main-promotion-via-publisher.md` §3(질문 5개)이고,
> 올릴 내용의 원천은 `2026-09-19-s2c2-s2a-drop-signed-mobile-and-gitops-mirror-design.md`(이하 "S2a 스펙")다.
> `plans/2026-09-19-s2a3-gitops-main-promotion.md` 의 Task 2~4(봉인 해제 → admin 머지)는 이 문서로 대체된다.
> 실측 기준(2026-09-20): gitops `origin/main` `4f3ed64` · `origin/develop` `9204c33` · PR #162 OPEN(head `4f0ba69`) ·
> 룰셋 `mission-spine-main-governance`(21194270)·`mission-spine-main-integrity`(21194269) active.

## 1. 목표와 범위

gitops `develop` 에 들어간 S2a ①(#160)·②(#161)를 **봉인을 풀지 않고** `main` 에 올린다. 수단은 9/3~9/12 의 main 통제면 커밋이
전부 거친 publisher 경로다 — 봇 작성자의 단일 target 커밋을, one-shot 헬퍼 브랜치의 워크플로가 보호 환경 승인 뒤 릴리스 App 권한으로
fast-forward push 한다.

범위 밖: publisher 뒤의 릴리스 캠페인(ET13 baseline → candidate → 증거 → seal → promote → landing-last)의 계획 ·
gitops `develop` 과 `main` 의 기존 분기(9개 파일) 해소 · S3(웹 재구성 구현).

**브랜치 규칙과의 관계**: 사용자 전역 규칙은 "main 에는 `develop → main` PR 로만"이다. gitops 의 통제면(`.github/workflows/`·
`.github/actions/`·`scripts/release/`·`tools/release-wrangler/`·`release-manifests/`)은 `scripts/release/verify_main_pr_policy.py`
가 그 경로를 **의도적으로 막는다**(2026-08-17 도입, #162 가 실측으로 확인). publisher 는 이 레포가 그 자리에 둔 정식 경로이고,
이 설계는 새 예외를 만들지 않는다.

## 2. 결정 (2026-09-20 설계 문답)

| # | 질문(핸드오프 §3) | 결정 | 근거 |
|---|---|---|---|
| Q1 | 체인 밖 변경의 publisher 모양 | **체인 재검증 단계를 뺀다. 새 등록 방식은 두지 않는다.** `MAIN_SHA` 핀이 "진행 중 체인 없음"을 대신한다 | §3.1 |
| Q2 | target 경로의 exact 단언 | **트리 해시 핀 + 접두사 allowlist.** 경로 목록·개수 리터럴은 쓰지 않는다 | §3.2 |
| Q3 | 보호 환경 승인 방식·확인 시점 | **봇 디스패치 + 사용자 확인 1회 뒤 AI 가 승인.** `prevent_self_review` 는 건드리지 않는다. 바뀌는 보호 설정은 헬퍼 브랜치 정책의 임시 추가(수십 초)뿐 | §3.3 |
| Q4 | 롤백 레인 폐쇄 구간 | **준비는 지금, 실행은 사람 단계(ET13 시각 승인·NVDA)를 같은 날 할 수 있는 날에.** N01 토큰은 그 전에 | §5 |
| Q5 | 독립 리뷰 수단 | **Claude 새 컨텍스트 서브에이전트 리뷰 + 기계 게이트**(트리 핀·계약 테스트·publisher 내 전체 스위트). Codex 는 2026-10-19 까지 한도 소진(9/20 `-m gpt-5.5` 도 거부, 실측) | §6 |

## 3. 결정의 근거 (실측)

### 3.1 체인 재검증을 넣을 수 없고, 넣을 필요도 없다

`verify_promotion_chain.py` 의 `inspect_chain` 은 candidate 의 `gitops.base_sha` 까지 거슬러 올라가며 커밋 제목을 등록된 것과
대조하고, 모르는 제목을 만나면 `current main contains an unrelated promotion commit` 으로 거부한다. 선례 publisher 들이 before/after
로 체인을 재검증한 것은 그 변경이 **진행 중인 체인의 fix** 였기 때문이다.

이번 변경을 체인에 등록하는 안은 성립하지 않는다. 재검증은 `ms-20260916-community-ia` 의 candidate 를 target 의 새 검증기로
`validate_candidate_spec` 하는데, 새 검증기는 구 모양(모바일 필드·12 fixture)을 거부한다 — S2a 스펙 §2 가 수용한 "자동 롤백 레인
폐쇄"와 같은 사실이다. 통과시키려면 v1+v2 이중 지원이 필요하고 그것은 S2a 스펙에서 버린 안이다. 등록은 target 트리도 바꿔
#162 의 CI 증거(§3.2)를 잃게 한다.

넣을 필요가 없는 이유: `4f3ed64` 는 `release(web): promote ms-20260916-community-ia mission-on` 이고 그 릴리스는 landing-last 까지
끝났다. publisher 가 `MAIN_SHA` 를 이 커밋으로 핀하면 "main 이 완료된 릴리스의 종단 커밋에 있다 = 끼어들 체인이 없다"가 함께 고정된다.
다음 candidate 는 `base_sha` 를 target 커밋으로 잡고, 검증기는 base 에서 walk 를 멈추므로 target 의 제목이 미등록이어도 다음 체인은 영향받지 않는다.

### 3.2 #162 의 head 가 이미 "CI 가 통과시킨 트리"다

`4f0ba69`(PR #162 head)는 부모가 `4f3ed64` 인 단일 커밋이고 작성자·커미터 이름이 `devpath-gitops-release[bot]` 이다.
트리는 `7799cc07f3083a002d0e2064db5437e2cde46f84`, CI 는 main 기준 전체 347건 OK. 부모가 main 이므로 PR 의 머지 ref 트리와 head 트리가 같다.

main 대비 변경은 `--name-status` 로 26행(rename 1건 포함 — `diff-tree` 는 `-M` 없이 D+A 로 풀어 27행; 핸드오프의 "25"는 어느 쪽과도
맞지 않는다). 9/17 이후 같은 계열의 낡은 개수 리터럴 결함이 열한 번 나왔다. 그래서 publisher 는 경로 목록을 적지 않고
**트리 해시**를 핀한다 — 목록 exact 보다 강하고(내용까지 고정) 개수가 등장하지 않는다. 의도는 접두사 allowlist 로 따로 드러낸다:
바뀐 경로는 전부 `release-manifests/`·`scripts/release/`·`tests/release/` 아래다(`.github/` 와 ArgoCD 가 추적하는 `apps/` 는 0건, 실측).

`4f0ba69` 를 그대로 target 으로 쓰지 않는 이유: 이메일이 `devpath-gitops-release[bot]@users.noreply.github.com` 인데 main 의 봇 커밋은
전부 `244265210+devpath-gitops-release[bot]@users.noreply.github.com`(GitHub 가 봇 계정에 귀속시키는 형식)이다. 검증기는 이름만 보지만
main 이력의 일관성을 위해 같은 트리를 선례 이메일로 `git commit-tree` 재작성한다. 트리가 같으므로 CI 증거는 그대로 유효하다.

### 3.3 봇 디스패치면 `prevent_self_review` 를 끌 일이 없다

선례(9/12, run `34686584754`)는 `VelkaressiaBlutkrone` 이 직접 디스패치했고, 같은 계정이 유일한 리뷰어라
`approve_pending_deployment.py` 로 `prevent_self_review` 를 잠시 끄고 승인했다. 그 뒤 9/16~17 에 봇 디스패처가 도입됐다:
`automation/dispatch-*` 브랜치 push → `GITHUB_TOKEN`(`actions: write`)으로 대상 워크플로를 디스패치 → actor·triggering actor 가
`github-actions[bot]`(run `35119923465` 실측)이 되어 리뷰어가 **설정 변경 없이** 승인할 수 있다. 이번 publisher 는 이 방식을 쓴다.

남는 보호 설정 변경은 환경 `mission-spine-production-off` 의 허용 브랜치다. 현재 `main` 단독(정책 id `57524487`)이라 헬퍼 브랜치의
job 은 대기에 들어가지도 못한다. 선례의 승인 코멘트("…after restoring the main-only environment policy")가 순서를 알려 준다 —
**헬퍼 브랜치 정책 임시 추가 → 디스패치 → 대기 진입 확인 → main-only 복원 → 승인.** 브랜치 정책은 job 이 대기에 들어갈 때 평가되므로
복원 뒤에 승인해도 실행된다.

`scripts/release/verify_current_protected_approval.py` 는 `main` 에서의 실행을 하드코딩으로 요구해(`protected workflow must execute
from main`) 헬퍼 브랜치에서 재사용할 수 없다. publisher 는 같은 내용을 인라인으로 단언한다(§4.2).

## 4. 구성 요소

전부 gitops 레포, 전부 `origin/main` `4f3ed64b2a148394eb0b8b3f5311e327f0edd759` 기준. 날짜 접미사는 브랜치를 만든 날(재작성 시 `-v2`).

| 브랜치 | 내용 | 작성자 |
|---|---|---|
| `fix/s2a-mobile-free-contract-main-20260920` | **target** 단일 커밋. 트리 `7799cc07…`, 제목은 #162 와 같은 `release: promote the mobile-free release contract and the pinned ET13 catalog to main` | 봇(선례 이메일) |
| `chore/s2a-mobile-free-contract-publish-20260920` | **헬퍼** 1커밋, 정확히 2개 경로: `.github/workflows/mission-spine-auth-smoke.yml`(publisher 로 교체) · `tests/release/test_s2a_main_publish.py`(계약 테스트) | 봇(선례 이메일) |
| `automation/dispatch-s2a-main-publish` | **디스패처** 1커밋, 정확히 1개 경로 추가: `.github/workflows/mission-spine-release-gate-dispatch.yml`(main 에는 없는 파일 — 선례 `automation/dispatch-ms-20260916-community-ia` 와 같은 구성). 자기 브랜치 push 에 반응해 헬퍼 브랜치의 `mission-spine-auth-smoke.yml` 을 `full: true` 로 디스패치한다. **준비 단계에서는 같은 커밋을 방아쇠가 아닌 이름 `chore/s2a-main-publish-dispatcher-staged-20260920` 으로만 push 한다**(워크플로의 `on.push.branches` 가 디스패처 이름 하나뿐이라 돌지 않는다 — 리뷰 대상이 원격에 남고 세션이 바뀌어도 유지된다). 실행 단계에서 그 SHA 를 디스패처 이름으로 push 한다 — 그 push 가 방아쇠다 | 봇(선례 이메일) |

헬퍼가 새 워크플로 파일을 만들지 않고 `mission-spine-auth-smoke.yml` 을 덮어쓰는 것은 선례와 같다 — `workflow_dispatch` 는 기본 브랜치에
같은 이름의 워크플로가 있어야 API 로 띄울 수 있다. 헬퍼 커밋은 main 에 들어가지 않으므로 main 의 auth-smoke 는 그대로다.

### 4.1 target 커밋

```
git commit-tree 7799cc07f3083a002d0e2064db5437e2cde46f84 -p 4f3ed64b2a148394eb0b8b3f5311e327f0edd759 -m <제목>
  (GIT_AUTHOR_*/GIT_COMMITTER_* = devpath-gitops-release[bot] <244265210+devpath-gitops-release[bot]@users.noreply.github.com>)
```

작성 직후 확인: `git diff 4f0ba69 <target>` 가 비어 있다 · 부모 1개 == main · 작성자·커미터 · `git diff --check main target` 통과.

### 4.2 publisher 워크플로 — 선례(`origin/chore/prod27r4-cloudflare-pagination-publish-20260912`) 대비

**그대로 두는 것**: `workflow_dispatch`(`full` boolean) · job `if`(ref == 헬퍼 브랜치 && `inputs.full`) · `environment:
mission-spine-production-off` · 전용 `concurrency` 그룹 · SHA 로 핀한 액션 · 헬퍼 컨텍스트 단언(event · attempt 1 · ref · `HEAD == GITHUB_SHA` ·
`HEAD^ == HELPER_BASE_SHA` · 헬퍼 커밋의 정확한 2개 경로 · 현재 main == `MAIN_SHA`) · target 에서 `python -m unittest discover -s tests/release`
전체 스위트 · App 토큰 발급(`administration: read`·`contents: write`) · `verify_gitops_write_authority.py` 를 push 전에 두 번 ·
`git push origin "$TARGET_SHA:refs/heads/main"` · push 뒤 `origin/main == TARGET_SHA` 재확인.

**바꾸는 것**

| 항목 | 선례 | 이번 |
|---|---|---|
| actor·triggering actor 단언 | `VelkaressiaBlutkrone` | `github-actions[bot]` |
| job `permissions` | `contents: read`·`deployments: write` | + `actions: read`(승인 기록 조회, landing-last 와 같은 구성) |
| target 경로 단언 | `--name-status` 4행 exact | `git rev-parse HEAD^{tree}` == `TARGET_TREE` + 모든 변경 경로가 3개 접두사 안 |
| 체인 단계 | `SEALED_SHA` 체크아웃 · `verify_migration_result.py` · `verify_promotion_chain.py` before/after | **없음**(§3.1). `RELEASE_EVIDENCE_TOKEN` 도 쓰지 않는다 |

**더하는 것 ①** — 헬퍼 컨텍스트 단언 바로 뒤에, 헬퍼 checkout 에서 `python -m unittest tests.release.test_s2a_main_publish` 를 돌린다.
헬퍼에는 CI 가 없으므로(§5.1) 실제로 실행되는 바로 그 워크플로 파일이 자기 계약을 통과하는지 실행 시점에 확인한다.

**더하는 것 ②** — App 토큰 발급 **앞**에 두는 "live 환경·승인 단언"(`GH_TOKEN: github.token`):

- `environments/mission-spine-production-off`: `can_admins_bypass == false` · required-reviewers 규칙 1개 · `prevent_self_review == true` ·
  리뷰어 1명 == `VelkaressiaBlutkrone`.
- `…/deployment-branch-policies`: 정확히 1건, `name == main`·`type == branch` — **임시로 연 정책이 이미 닫혔음**을 job 안에서 확인한다.
- `actions/runs/$GITHUB_RUN_ID/approvals`: `approved` 1건, 승인자 `VelkaressiaBlutkrone`, 환경 이름 일치.

### 4.3 계약 테스트 `tests/release/test_s2a_main_publish.py`

헬퍼 브랜치에서만 돈다(target 에 넣지 않으므로 main 트리는 #162 그대로). 워크플로 YAML 을 파싱해 단언한다:
핀 값(`MAIN_SHA`·`TARGET_SHA`·`TARGET_TREE`·`HELPER_BASE_SHA`·브랜치명 2개) · `git push` 가 파일 전체에 정확히 하나이고 그 형태 ·
job `if`·`environment`·`permissions`·`concurrency` · 모든 `uses:` 가 40자 SHA 핀 · actor 단언이 `github-actions[bot]` ·
`verify_promotion_chain`·`SEALED_SHA`·`RELEASE_EVIDENCE_TOKEN` 이 파일에 **나오지 않음**(의도된 제거를 고정) ·
계약 테스트 자기 실행 step 과 live 환경·승인 단언 step 이 App 토큰 발급 step 보다 **앞** · `MAIN_SHA == HELPER_BASE_SHA`.

### 4.4 실행 스크립트 `run_s2a_main_publish.py` (레포 밖 — 계획 문서에 전문 수록, 실행 세션의 스크래치패드에 물질화)

실행 단계 전체를 한 Python 스크립트로 묶는다. 셸 `trap` 을 쓰지 않는 이유: 이 PC 는 메모리 압박으로 백그라운드 대기가 네 번 강제 종료됐다
(핸드오프 §5). `try/finally` 로 복원을 보장한다.

1. 전제 재측정 — main == `MAIN_SHA` · 헬퍼·target 브랜치 head 가 기록한 SHA · gitops 에 진행·대기 중인 실행 0 · 브랜치 정책 원형 스냅샷
   (1건·`main`·id `57524487`) · `prevent_self_review == true`.
2. 헬퍼 브랜치 정책 POST, **돌아온 id 기록**.
3. staged 디스패처 SHA 를 `automation/dispatch-s2a-main-publish` 로 push → 헬퍼 브랜치의 auth-smoke 실행이 `waiting` 이 될 때까지 폴링(상한 5분).
4. `finally`: 기록한 id 로 DELETE(`main` 정책은 건드리지 않는다 — 목록을 다시 쓰지 않고 추가분만 지운다) → GET 이 스냅샷과 같음을 단언.
   **여기서 실패하면 승인으로 가지 않고 멈춘다.**
5. `pending_deployments` 에서 `current_user_can_approve == true` 확인 → POST 승인(`environment_ids` 는 `-F` 정수형).
6. `gh run watch <run> --interval 15 --exit-status` 포그라운드.
7. 사후 검증 — §5.3.

## 5. 절차

### 5.1 준비 단계 (운영에 닿지 않는다 — 스펙 승인 뒤 바로)

1. 9/10 부터 같은 보호 환경에서 승인 대기로 방치된 publisher 실행 `34422926318`(`chore/prod27-ai-digest-main-publish-20260910`)을 취소한다.
   승인돼도 `MAIN_SHA` 단언에서 죽지만, 실행일의 "대기 중인 실행 0" 전제를 위해 치운다.
2. target 브랜치 작성·push(§4.1).
3. 헬퍼 브랜치 작성(TDD — 계약 테스트 먼저) · 로컬에서 새 테스트 모듈과, `mission-spine-auth-smoke.yml` 을 참조하는 기존 테스트 모듈(있다면 — 계획
   작성 때 grep 으로 확정)을 돌린다 · push. **헬퍼 브랜치에는 CI 가 돌지 않는다** — `ci.yml` 은 `push: main` 과 `pull_request` 에만 반응하고, 선례도
   헬퍼에 PR·CI 없이 갔다(실측: 헬퍼 브랜치의 실행은 publisher 자신뿐). 헬퍼 트리는 "CI 녹색인 main `4f3ed64` + 2개 파일"이라 새로 검증할 것은
   계약 테스트뿐이고, 그것은 publisher 가 첫 단계에서 스스로 다시 돌린다(§4.2).
4. 리뷰(§6) → 지적 반영 → 계약 테스트 재실행. 헬퍼 커밋이 바뀌면 `GITHUB_SHA` 도 바뀌지만 publisher 가 핀하는 것은 `HELPER_BASE_SHA` 라 자기 참조는 없다.
5. 디스패처 커밋을 만들어 staged 이름으로만 push 한다(§4 — 실행이 생기지 않음을 `gh run list` 로 확인). 실행 스크립트를 쓰고, API 호출부를 주입 가능한 함수로 두어 **가짜 API 로**
   복원 경로를 테스트한다 — 정상 흐름 · 대기 진입 시간 초과 · 디스패치 실패 · DELETE 뒤 스냅샷 불일치(→ 승인 호출이 일어나지 않음).
   준비 단계에서는 live 환경 설정에 쓰기를 하지 않는다.
6. 요약을 보고하고 **멈춘다.**

### 5.2 실행 단계 (사용자가 정한 날, "진행" 1회 뒤 멈추지 않고)

실행일 체크리스트(확인 요청 전에 AI 가 채운다): N01 Cloudflare durable token 준비됨(사람) · 사용자가 같은 날 ET13 시각 승인과 NVDA 증거를
할 수 있음 · main 이 `MAIN_SHA` 에서 움직이지 않음(움직였으면 target·헬퍼를 새 main 위에 다시 만들고 §5.1 의 3~4 를 반복).
"진행"을 받으면 §4.4 의 스크립트를 돌린다.

### 5.3 사후 검증과 마무리

- `origin/main == TARGET_SHA` · `origin/main^{tree} == 7799cc07…` · main push 의 CI(`ci.yml`) 녹색.
- 룰셋 2종 active·규칙 불변 · classic 보호 불변 · 환경 정책 main-only · `prevent_self_review == true`.
- `app.leva.ai.kr`·`leva.ai.kr` 200(트리 변경이 `apps/` 밖이라 ArgoCD 동기화 대상 없음 — 확인만).
- #162 를 "같은 트리가 publisher 로 main 에 들어갔다(run 링크)"는 코멘트와 함께 닫는다. 브랜치 3개와 #162 는 증거로 남긴다(선례도 전부 남아 있다).
- documents 에 핸드오프·S2a 스펙 실행 결과 절 갱신, 메모리 갱신. 이어서 핸드오프 §4 의 캠페인으로 넘어간다.

## 6. 리뷰

대상은 헬퍼 커밋의 2개 파일, 디스패처 워크플로, 실행 스크립트다. target 트리는 #160·#161 로 develop 에서 검증됐고 #162 CI 가 main 기준으로
통과시킨 것과 바이트 동일하다.

- 새 컨텍스트 서브에이전트에게 주는 것: 선례 워크플로와 새 워크플로의 diff · 계약 테스트 · 디스패처(선례 디스패처 대비 diff) ·
  실행 스크립트와 그 테스트 · 이 문서 §4.2 의 단언 목록.
  지시: "이 publisher 가 의도하지 않은 것을 main 에 쓸 수 있는 경로, 단언을 우회해 push 에 도달하는 경로를 찾아라." 범위 고정 문구
  (이 작업만 · 읽기 전용 · 보고 후 정지 · 절대경로)를 포함한다.
- 지난 세션에 이 PC 의 서브에이전트 리뷰가 빈 응답을 두 번 냈다 → 본 리뷰 전에 소형 프로브로 실측하고, 비면 헤드리스 `claude -p`
  별도 프로세스로 형태를 바꿔 재시도한다. 둘 다 실패하면 멈추고 사용자에게 보고한다(리뷰 없이 진행하지 않는다).
- 리뷰 결과는 그대로 믿지 않고 컨트롤러가 지적마다 코드에서 재확인한다.

## 7. 오류 처리

| 죽는 곳 | main | 처리 |
|---|---|---|
| 정책 추가·디스패치·대기 진입 | 불변 | `finally` 복원 확인. 대기에 못 들어간 실행은 취소. 원인 조사 뒤 디스패처에 nonce 커밋을 더해 재디스패치(attempt 는 새 run 이라 1) |
| 승인 뒤, push 전(단언·스위트·권한 검증) | 불변 | 롤백할 것 없음. 워크플로를 고쳐야 하면 `-v2` 헬퍼 브랜치(선례 9/12), 재실행(attempt 2)은 publisher 가 거부 |
| push 직후 재검증 | target | main == target 이면 승격은 성립. 재검증 실패의 원인만 조사 |
| push 뒤 main CI 실패 | target | 트리가 #162 와 같아 가능성은 낮다. 되돌리지 않는다 — integrity 룰셋이 non-fast-forward 를 bypass 없이 막는다. **fix-forward**(같은 publisher 패턴) |
| 복원 검증 실패 | 불변 | 승인으로 가지 않고 멈춘다. 환경 정책을 스냅샷대로 수동 복원(명령은 계획 문서에), 사용자에게 보고 |

## 8. 위험

- **자동 롤백 레인 폐쇄**(S2a 스펙 §2 에서 수용): push 시점부터 다음 릴리스 승격까지. 비상 수단은 수동 gitops
  (`handoff-2026-08-22-et10-release-complete-manual-gitops.md`). §5.2 의 일정 결정이 구간을 하루 이내로 줄인다 — 사람 단계가 밀리면 그만큼 늘어난다.
- **임시 브랜치 정책**: 열려 있는 수십 초 동안 그 브랜치에서 이 환경을 쓰는 다른 job 이 대기에 들어갈 수 있다. 헬퍼 브랜치에서 이 환경을
  참조하는 워크플로는 publisher 하나뿐이고(계약 테스트가 고정), 대기에 들어가도 리뷰어 승인 없이는 돌지 않는다.
- **AI 승인**: 승인 클릭을 AI 가 한다(사용자 결정, S2a 스펙 Q5 와 같은 모양). 통제는 직전 확인 1회 + publisher 안의 단언들이다.
- **준비와 실행 사이의 간격**: 그 사이 main 이 움직이면 핀이 전부 무효다. 현재 main 을 움직일 주체는 릴리스 App 뿐이고 예정된 승격이 없다.
  실행일 전제 재측정이 잡는다.

## 9. 산출 계획 문서

`plans/2026-09-20-gitops-main-promotion-via-publisher.md` 하나 — 준비 단계(§5.1)의 Task 들과, 확인 게이트 뒤 실행 단계(§5.2~§5.3)의 Task 들.
