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

**더하는 것 ①** — 헬퍼 컨텍스트 단언 바로 뒤에, 헬퍼 checkout 에서 `python -m unittest discover -s tests/release -p 'test_s2a_main_publish.py'` 를 돌린다(CI 와 같은 discover 형식 —
gitops 에는 `tests/__init__.py` 가 없어 `tests.release.…` 점 표기는 러너 site-packages 의 `tests` 패키지에 가려질 수 있다).
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

### 4.4 실행 스크립트 `run_s2a_main_publish.py` (gitops 밖 — 계획 문서에 전문 수록하고 같은 바이트를 documents `plans/2026-09-20-gitops-main-promotion-via-publisher/` 에 커밋, 실행 세션의 스크래치패드에 `git show` 로 물질화)

실행 단계 전체를 한 Python 스크립트로 묶는다. 셸 `trap` 을 쓰지 않는 이유: 이 PC 는 메모리 압박으로 백그라운드 대기가 네 번 강제 종료됐다
(핸드오프 §5). `try/finally` 로 복원을 보장한다.

1. 전제 재측정 — main == `MAIN_SHA` · 헬퍼·target 브랜치 head 가 기록한 SHA · gitops 에 진행·대기 중인 실행 0 · 브랜치 정책 원형 스냅샷
   (1건·`main`·id `57524487`) · `prevent_self_review == true`.
2. 헬퍼 브랜치 정책 POST, **돌아온 id 기록**.
3. staged 디스패처 SHA 를 `automation/dispatch-s2a-main-publish` 로 push → 헬퍼 브랜치의 auth-smoke 실행이 `waiting` 이 될 때까지 폴링(상한 5분).
4. `finally`: **이름이 헬퍼 브랜치인 정책만** DELETE(POST 응답을 잃어 id 를 모르는 경우에도 복원된다. `main` 정책은 이름이 달라 절대 지워지지 않는다 —
   목록을 다시 쓰지 않고 추가분만 지운다) → GET 이 스냅샷과 같음을 단언.
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

## 10. 실행 결과 (2026-09-20) — 승격 완료

gitops `main` 은 `4f3ed64` → **`69e7bd15570f5ba0f271c83b5bd46955cb249c8e`**(트리 `7799cc07…`)로 fast-forward 됐다. 봉인은 풀지 않았다.

| 항목 | 값 |
|---|---|
| publisher 실행 | `35491725505` — actor·triggering actor `github-actions[bot]` · attempt 1 · head `00cafba`(헬퍼) · 14개 step 전부 success · 05:27:30Z → 05:28:28Z |
| 디스패처 실행 | `35491720855`(`automation/dispatch-s2a-main-publish` push) |
| 승인 | `VelkaressiaBlutkrone`, 환경 `mission-spine-production-off`, `prevent_self_review` **불변**. 코멘트: "…after restoring the main-only environment policy." |
| 환경 브랜치 정책 | 헬퍼 정책을 임시 추가했다가 승인 **전에** main-only(id `57524487`)로 복원·검증. publisher 의 live 단언(§4.2)도 job 안에서 같은 것을 확인하고 통과 |
| main CI | `35491763390` success(`69e7bd15`) |
| 사후 | 룰셋 2종 active · `enforce_admins` true · 진행·대기 실행 0 · `app.leva.ai.kr`·`leva.ai.kr` 200 · #162 닫음 |

**Q4 의 변경(사용자 결정, 확인 게이트에서)**: "실행은 사람 단계가 가능한 날에" 대신 **"지금 실행 — 사람 단계(N01 토큰 · ET13 시각 승인 · NVDA)는 나중에"**.
따라서 `ms-20260916-community-ia` 의 **자동 롤백 레인은 2026-09-20T05:28Z 부터 다음 릴리스 승격까지 닫혀 있다** — 하루 이내가 아니라 사람 단계가
끝날 때까지다. 그 구간의 비상 수단은 수동 gitops(`handoff-2026-08-22-et10-release-complete-manual-gitops.md`). §8 의 첫 위험이 이 결정으로 길어졌다.

**독립 리뷰**(§6): Critical 0 · Major 2 · Minor 4 — 전부 변이로 재현한 뒤 고쳤다. 상세는 계획 문서 끝 「리뷰 결과」.

**실행 중 드러난 결함 1건**: 실행 스크립트의 사이트 확인이 `Python-urllib` 기본 UA 로 나가 Cloudflare 가 `leva.ai.kr` 에 403 을 돌려줬다(가짜 실패 —
승격과 복원·승인은 그 전에 끝나 있었다). 테스트를 먼저 더해 고쳤고 `--post-verify-only` 로 사후 검증 전체를 다시 통과시켰다. 상세는 계획 문서 끝 「실행 결과」.

**다음**: frontend main `31a7785d` 에 대한 ET13 baseline **봇 디스패치** → 사람의 시각 승인 → gitops candidate(`gitops.base_sha` = `69e7bd15…`) →
수동 NVDA 증거 → seal → promote → landing-last(prior deployment 기대값 `005cf175-6e3e-4400-a201-1987ce9d8d84`, N01 토큰 선행).

## 11. 부록 (2026-09-21) — 같은 publisher 로 폐기된 r2 의 writer fence 를 main 에서 걷어낸다 · **실행 완료**(§11.1)

**왜**: 릴리스 `ms-20260920-community-flat-pages-r2` 의 마이그레이션 커밋 M(`c1d5e8cf197c7dbcb0d5f224011b82b73412e17a`)이 platform-svc·sandbox-svc 를
`replicas: 0` 으로 fence 했다. fence 를 푸는 것은 promote 의 additive-services 커밋인데, promote 는 9개 서비스의 immutable-image 증거를 요구하고
community-svc·notification-svc 의 아티팩트가 2026-09-21 에 만료됐다(같은 SHA 로 재생성 불가). 새 릴리스도 시작할 수 없다 — shared 의 마이그레이션 게이트가
replica override 가 있는 base 를 거부한다. 운영은 클러스터 쪽 임시 조치로 살려 두었다(`handoff-2026-09-21-r2-promote-blocked-temporary-unfence.md` §1).
main 대상 PR·직접 push 는 봉인에 막혀 있으므로 §1 의 publisher 가 정식 경로다.

**결정(사용자, 2026-09-21)**: **fence 만 제거한다.** target 은 M 의 단일 자식이고 두 writer kustomization 만 fence 이전 base(`69e7bd15…`)의 블롭으로 되돌린다.
`69e7bd15` 의 트리로 통째 되돌리지 않는 이유 — migration kustomization 의 Job 이름이 9/16 의 것으로 돌아가는데 그 Job 은 이미 prune 됐으므로 ArgoCD 가
다시 만들어 실행한다(init 이 writer replicas=0 을 기다리다 멈추고 일회성 관문 ConfigMap 도 없다 → `devpath-migration` Degraded). M 의 Job 은 Complete 라
그대로 두면 아무것도 재실행되지 않는다. 클러스터의 수동 replicas 1 이 곧 git 상태가 되므로 push 자체는 운영 무변화다.

**§3.1 과의 차이**: 이번 `MAIN_SHA` 는 완료된 릴리스의 종단 커밋이 아니라 **폐기된 체인의 M** 이다. 그래도 다음 candidate 에 영향이 없음을 실제 게이트 코드로
증명했다(`prove_next_base.py`) — `inspect_chain` 은 `base_sha` 에서 walk 를 멈추고 base 에는 inert migration Job(`suspend: true`) · 파싱 가능한 migration
selector · writer fence 부재만 요구한다. target 은 세 검사와 shared 게이트의 두 렌더를 통과하고, 대조군 M 은 두 게이트 모두 거부한다. r2 는 폐기되고 봉인
브랜치는 증거로 남는다.

| 좌표 | 값 |
|---|---|
| `MAIN_SHA` = `HELPER_BASE_SHA` | `c1d5e8cf197c7dbcb0d5f224011b82b73412e17a` |
| `FENCE_BASE_SHA` | `69e7bd15570f5ba0f271c83b5bd46955cb249c8e` |
| target `fix/r2-writer-fence-removal-main-20260921` | `fcf97cf686df8e8bad56597d4679f9a96fd597fc` · 트리 `a1c43f95c1332611e0f32066b51aa25090e98b5a`(고정 타임스탬프로 결정적 재현 — `make_unfence_target.py`) |
| 헬퍼 `chore/r2-writer-fence-removal-publish-20260921` | `8e42f757c3b73570e94c1ec7309fb406222bb705`(2경로: publisher · `tests/release/test_r2_unfence_main_publish.py`) |
| staged 디스패처 `chore/r2-unfence-publish-dispatcher-staged-20260921` | `00c66257a9c48552bc5b92278f6b04e552b0f982` |
| 방아쇠 | `automation/dispatch-r2-unfence-main-publish` — **아직 없음**(그 이름으로 push 하는 것이 실행) |

**§4.2 대비 바꾼 것**(9/20 에 실행된 헬퍼와의 diff 가 정확히 이것뿐임을 확인): 핀·이름·브랜치명 · target `fetch-depth` 2→3(조부모의 트리가 필요 — 실제 얕은
클론으로 depth 3 통과·depth 2 실패를 확인) · 접두사 allowlist 대신 **`--name-status` 정확히 2행 + 두 블롭 == `$FENCE_BASE_SHA` 의 블롭 + migration 블롭 == M**.
블롭 비교는 대입 뒤 `test -n` 을 거친다(`test "$(a)" = "$(b)"` 는 두 명령이 다 실패하면 통과한다). fence 잔존 검사는 `if grep -q` 분기다(`! grep` 은 `set -e` 를
건드리지 않는다). 실행 스크립트는 (a) preflight 가 post_verify 의 **모든 읽기 경로**(룰셋 · `enforce_admins` · target 트리 · `ci.yml` runs · 사이트 200)를 첫 쓰기
전에 지나가고(§10 의 결함 교정) (b) **리뷰된 헬퍼 SHA 를 핀**한다(`--helper-sha`).

**검증**: 계약 테스트 16(옛 워크플로에 RED 확인 후) · actionlint(헬퍼·디스패처) · target 검증 step 을 실제 target 에서 독립 Git Bash 로 실행 + 변이 3종이 의도한
단언에서 사망(`mutation_check.py`) · target 트리에서 `tests/release` 전체 347 OK · 실행 스크립트 단위 테스트 18 · live `--preflight-only` OK + 음성 대조(틀린 헬퍼
SHA → 쓰기 전 거부). **독립 리뷰**(새 컨텍스트, 읽기 전용): Critical 0 · Medium 1 · Low 2 — 전부 변이로 재현한 뒤 고쳤다(`contract_mutants.py`): step 수준 `env` 가
job 수준 핀을 가릴 수 있었음(9/20 원본에서 물려받은 구멍) · `set -euo pipefail` 미단언(`shell:` 을 명시하지 않은 러너 셸은 `bash -e {0}` 이라 pipefail·nounset 이
없다 — 리뷰어가 든 완화 근거보다 실제로 더 중요했다) · 실행 스크립트가 헬퍼 SHA 를 핀하지 않고 발견하던 비대칭.

**실행 절차**(사용자 확인 1회 뒤): §5.2 와 같다 — `run_r2_unfence_main_publish.py --repo-dir … --staged-sha 00c66257… --helper-sha 8e42f757… --comment …`.
**publisher 밖의 순서 하나가 추가된다**: `main == target` 을 확인한 **뒤에만** 클러스터의 임시 조치를 되돌린다
(`kubectl -n argocd patch applicationset devpath-services --type=json -p '[{"op":"remove","path":"/spec/ignoreApplicationDifferences"}]'`) → 두 앱
Synced/Healthy · replicas 1 · OAuth 시작 경로 302 확인. 순서가 바뀌면 fence 가 다시 걸린다.

**범위 밖**: fence ServiceAccount 의 `imagePullSecrets` 매니페스트 결함(M 렌더 검증에 걸릴 수 있어 분리 — 수동 patch 유지) · r3 전체.

스크립트: `plans/2026-09-21-gitops-main-writer-fence-removal-via-publisher/`.

### 11.1 실행 결과 (2026-09-21T06:02Z~06:09Z)

gitops `main` 은 `c1d5e8cf` → **`fcf97cf686df8e8bad56597d4679f9a96fd597fc`**(트리 `a1c43f95…`)로 fast-forward 됐다. 봉인은 풀지 않았다.

| 항목 | 값 |
|---|---|
| publisher 실행 | `35566755778` — actor `github-actions[bot]` · attempt 1 · 전 step success |
| 승인 | `VelkaressiaBlutkrone`, 환경 `mission-spine-production-off`, `prevent_self_review` **불변**. 사용자 확인 1회 뒤 AI 가 승인 |
| 환경 브랜치 정책 | 헬퍼 정책(id `60552783`)이 열려 있던 구간 약 20초(06:02:07~06:02:29Z — 스크립트 밖에서 독립 관찰). 승인은 main-only(id `57524487`) 복원·검증 **뒤** |
| main CI | `35566816989` success |
| 사후 | 룰셋 2종 active · `enforce_admins` true · 진행·대기 실행 0 · `app.leva.ai.kr`·`leva.ai.kr` 200 |
| 클러스터 원복 | `main == target` 과 git 선언 `replicas: 1` 을 확인한 뒤 AppSet 의 `ignoreApplicationDifferences` 제거 → 11초 만에 platform·sandbox `Synced/Healthy`·auto-sync 복원, 3분 관찰 내내 1/1·같은 파드(재시작 0). 마이그레이션 Job 재실행 없음 |

이번에는 실행 중 드러난 결함이 없었다 — preflight 가 post_verify 의 읽기 경로를 전부 미리 지나간 덕이다(§10 의 결함과 대비).
**다음**: `gitops.base_sha` = `fcf97cf6…` 로 r3 — `handoff-2026-09-21-afternoon-main-unfenced-r3-next.md` §3.

## 12. 부록 (2026-09-21 밤) — 같은 publisher 로 파이프라인 결함 3건을 main 에 올린다 · **준비 진행 중(독립 리뷰 대기) — 실행 전**(§12.5)

**왜**: 2026-09-21 의 사고 세 건(`handoff-2026-09-21-night-session-close.md` §3) 가운데 둘의 근본 원인과, 그날 드러난 수동 의존 하나가 gitops 통제면에 남아 있다.
전부 main 대상 PR 이 막히는 경로(`apps/**` · `scripts/release/**`)라 §1 의 publisher 가 정식 경로다.

**실측(2026-09-21, `origin/main` = `30c0e9f717efaad9bd46d47721a61495f4093e96` — r3 의 mission-on 커밋)**

| 결함 | main 의 실물 | 운영의 실물 |
|---|---|---|
| 서비스 Deployment 에 `startupProbe` 없음 | JVM 서비스 8개(`devpath-{platform,learning,ai,community,notification,lcs,sandbox}-svc` · `devpath-gateway`)의 `base/deployment.yaml` 에 `readinessProbe`(`initialDelaySeconds: 10`)·`livenessProbe`(`initialDelaySeconds: 20`, 나머지 기본값 = 10초×3회)만 있다 → 기동이 약 50초를 넘기면 liveness 가 죽인다. `devpath-web`·`devpath-admin`(nginx)은 해당 없음 | 8개 전부 `startupProbe` 없음 · `paused` 없음 · 전 파드 `restartCount` 0 · 전략은 기본(25%/25% → replicas 1 에서 surge 1·unavailable 0), **sandbox-svc 만 `maxSurge: 0`·`maxUnavailable: 1`** |
| fence ServiceAccount 에 `imagePullSecrets` 없음 | `apps/devpath-migration/base/writer-fence-rbac.yaml` 의 SA 는 `automountServiceAccountToken: false` 뿐 | 수동 patch `[{"name":"ghcr-pull"}]` 가 살아 있고 Argo 는 `Synced` 로 본다(last-applied 에 없는 필드는 diff 대상이 아니다). `ghcr-pull` 은 `kubernetes.io/dockerconfigjson`, default SA 도 같은 시크릿을 쓴다 |
| landing-last 에 `/api/*` smoke 없음 | `scripts/release/cloudflare_pages.py` 의 `verify-new-production` 은 배포 CAS · dist 마커(`_probe_marker`) · `/` 의 2xx/3xx(`_probe`)만 본다 | 9/21 에 함수 없는 배포가 이 검증을 통과했고 `/api/*` 는 404 였다(2분 30초) |

**결정(사용자, 2026-09-21)**: ① **세 건을 한 target 커밋에** 담는다(publisher 1회 = 보호 환경 승인 1회 + r3 자동 롤백 레인 닫힘 1회) ② 아래 설계 승인.

### 12.1 target 커밋 — `MAIN_SHA` 의 단일 자식, 고정 타임스탬프로 결정적 재현

| 경로 | 변경 |
|---|---|
| 8개 서비스의 `apps/<name>/base/deployment.yaml` | 첫 컨테이너의 `readinessProbe` **앞에** `startupProbe` 를 넣는다: `httpGet {path: /actuator/health/liveness, port: 8080}` · `periodSeconds: 5` · `timeoutSeconds: 3` · `failureThreshold: 60`(예산 300초). 기존 readiness·liveness 는 한 글자도 바꾸지 않는다 |
| `apps/devpath-migration/base/writer-fence-rbac.yaml` | ServiceAccount 에 `imagePullSecrets: [{name: ghcr-pull}]` |
| `scripts/release/cloudflare_pages.py` | `_probe_api(origin)` 추가 — `GET {origin}/api/invite-rounds` 를 리다이렉트 없이, 200 · 본문 ≤ 64 KiB · UTF-8 JSON 으로 파싱 가능. `verify-new-production` 에서 `_probe` 뒤에 호출하고 성공 메시지에 반영 |
| `tests/release/test_production_startup_budget.py`(신규) | 8개 운영 Deployment 의 `startupProbe` 가 위 경로·포트이고 `periodSeconds × failureThreshold ≥ 300` · 기존 두 프로브가 그대로 · fence SA 의 `imagePullSecrets` 가 정확히 `ghcr-pull` 하나 |
| `tests/release/test_cloudflare_api.py` | `_probe_api` 의 수락·거부 케이스(비-200 · 리다이렉트 · 비-JSON · 과대 본문 · 네트워크 오류)와 `verify-new-production` 이 그것을 호출함 |

값의 근거는 레포 안의 선례다 — `staging/mission-spine/patches/{gateway,platform,learning,sandbox,ai,lcs}.yaml` 이 같은 `startupProbe` 를 이미 쓰고 `tests/release/test_mission_staging_stack.py::test_spring_services_have_staging_startup_budget` 가 "예산 ≥ 300초"를 단언한다.
smoke 를 `/api/invite-rounds` 하나로 한정하는 이유: 부작용 없는 GET 이고 상류 의존이 없다. `POST /api/lead` 는 실제 리드를 쓰고 `/api/stats` 는 Apps Script 에 의존해 흔들린다.

**검토하고 버린 대안**: liveness `initialDelaySeconds` 를 늘린다(장애 감지가 항상 느려진다) · ApplicationSet progressive sync 로 매니페스트 차원에서 직렬화한다(알파 기능, 범위 과대) · smoke 경로를 candidate-spec 에 싣는다(frontend·gitops·홈 하니스의 계약 미러 3곳을 건드린다).

**다른 게이트와의 관계(코드로 확인, 준비 단계에서 실행으로 증명)**: gitops `tests/release/test_release_contract.py` 는 RBAC 파일에서 세 문서의 kind·이름과 Role 규칙만 본다 · shared `scripts/release/migration_release_gate.py` 의 `validate_base_migration_render`·`validate_migration_render` 는 렌더에서 **Job 문서만** 검사하고 `job.yaml` 은 바꾸지 않는다 → §11 이 SA 를 분리하며 든 우려("M 렌더 검증에 걸릴 수 있어")는 코드상 해당하지 않는다.

### 12.2 준비 단계 (운영 무접촉)

§11 의 틀을 그대로 쓴다. ① target 을 `make_pipeline_defects_target.py` 로 결정적으로 만들고 트리 해시를 핀 ② 새 테스트는 RED(현재 main 트리) → GREEN(target 트리) 확인, target 트리에서 `tests/release` 전체 ③ 9개 앱(서비스 8 + migration)의 `kubectl kustomize` 렌더를 main/target 에서 떠서 diff 가 의도한 줄뿐임을 확인 ④ `prove_next_base.py` — 다음 candidate 의 `gitops.base_sha` 로 target 이 gitops `inspect_chain` 의 base 요건과 shared 게이트의 렌더 검증을 통과함을 실제 코드로 증명 ⑤ 헬퍼 워크플로는 9/21 헬퍼에서 핀·이름·브랜치명과 target 검증 step(부모 == `MAIN_SHA` · `--name-status` 정확한 행 집합 · 트리 해시)만 바꾼다 — diff 가 그것뿐임을 확인 ⑥ 계약 테스트 · 변이 검사 · actionlint · 실행 스크립트 단위 테스트 ⑦ 새 컨텍스트 독립 리뷰(읽기 전용) ⑧ live `--preflight-only`(post_verify 의 모든 읽기 경로를 첫 쓰기 전에 지나간다).

### 12.3 실행 단계 (준비 완료 보고 → 사용자 확인 1회 뒤)

**이 커밋은 그대로 sync 되면 9/21 의 herd 를 재현한다** — 파드 템플릿 8개가 한 번에 바뀌어 단일 노드(4 CPU)에서 JVM 8개가 동시에 롤링된다. 새 파드는 `startupProbe` 덕에 죽지 않지만 옛 파드의 liveness(timeout 1초)가 CPU 기아로 실패할 수 있다. 그래서 publisher **밖에** 직렬화 절차를 둔다.

1. `kubectl -n devpath rollout pause deployment/devpath-notification-svc` 하나만 먼저 → 1~2분 관찰: Argo 가 `Synced` 를 유지하고 `spec.paused` 를 되돌리지 않는지(9/21 의 복구는 sync **뒤** pause 였다 — 순서가 다른 이번 경우는 미실측). 되돌린다면 멈추고 재설계한다.
2. 나머지 7개 pause.
3. publisher: §5.2 와 같다(환경 브랜치 정책 임시 추가 → 봇 디스패치 → waiting 확인 → main-only 복원·검증 → 승인). `prevent_self_review` 불변.
4. `main == target` · main CI 성공 확인 → Argo sync 뒤 8개 Deployment 의 템플릿에 `startupProbe` 가 있고 **새 ReplicaSet 이 없고 파드가 그대로**임을 확인. fence SA 는 `imagePullSecrets` 유지 + last-applied 에 반영.
5. 하나씩 `rollout resume` → `rollout status` 대기 → 새 파드 `restartCount == 0` 확인, 순서는 notification → ai → lcs → community → learning → sandbox → platform → gateway(덜 중요한 것에서 프로브를 먼저 검증하고 관문은 마지막). sandbox 는 `maxSurge: 0` 이라 교체 동안 끊긴다(9/21 실측 기동 ~23초 — 모든 릴리스에서 같은 일이 일어난다).
6. 사후: 8개 앱 `Synced/Healthy` · `paused` 없음 · 전 파드 재시작 0(다음 릴리스의 런타임 검증기가 `restartCount == 0` 을 요구한다) · `app.leva.ai.kr`·`leva.ai.kr` 200 · OAuth 시작 경로 302.

**실패 처리**: 새 파드가 Ready 가 안 되면 그 Deployment 를 다시 pause 하고 새 ReplicaSet 을 `scale --replicas=0`(9/21 에 Argo 와 충돌 없이 동작) — 기본 전략에서는 옛 파드가 계속 서비스한다. publisher 가 승인 전에 실패하면 main 은 그대로이므로 8개를 `resume` 하면 원상이다(템플릿 무변화 → 롤아웃 없음).

### 12.4 되돌릴 수 없는 지점과 확인 관문

main 이 r3 의 mission-on 커밋에서 벗어나는 순간부터 다음 릴리스 승격까지 **r3 의 자동 롤백 레인이 닫힌다** — `mission-spine-rollback.yml` 이 `verify_promotion_chain.py --current refs/remotes/origin/main` 을 돌리고 그 검증기는 체인 위의 미등록 커밋을 거부한다(§3.1). 비상 수단은 수동 gitops 다. "지금 실행" 과 "다음 릴리스 캠페인의 0단계로 실행" 은 준비물이 같으므로 준비 완료 보고 때 선택지로 묻는다. main 이 그 전에 움직이면 핀이 전부 무효다.

**범위 밖**: liveness `timeoutSeconds` 조정 · landing smoke 실패 시 자동 롤백(`--action rollback-prior` 는 이미 있다) · `sandbox-migration-gate` ConfigMap 자동화 · 홈 develop → master 릴리스.

스크립트: `plans/2026-09-21-gitops-main-pipeline-defects-via-publisher/`.

### 12.5 준비 현황 (2026-09-22 새벽, 세션 종료 시점)

| 좌표 | 값 | 상태 |
|---|---|---|
| `MAIN_SHA` = `HELPER_BASE_SHA` | `30c0e9f717efaad9bd46d47721a61495f4093e96` | 세션 종료 시 `origin/main` 과 일치 |
| target `fix/pipeline-defects-main-20260921` | `5961922b9a309055a75bc7302e5c852c5c51d59c` · 트리 `85d71a7f6734d781df3ea0f287ae8569a1b801e4`(`make_pipeline_defects_target.py`, 두 번 실행해 같은 SHA) | **push 됨** |
| 헬퍼 `chore/pipeline-defects-publish-20260921` | `3e67810471eaf90499e26134f2e76c942c25d711`(2경로: publisher · `tests/release/test_pipeline_defects_main_publish.py`) | **로컬 커밋만 — 리뷰 뒤 push** |
| staged 디스패처 `chore/pipeline-defects-publish-dispatcher-staged-20260921` | `cbf153840adfba33c3460de0ae653cf54a02b4e2`(1경로 추가) | **로컬 커밋만 — 리뷰 뒤 push** |
| 방아쇠 `automation/dispatch-pipeline-defects-main-publish` | — | **없음**(그 이름으로 push 하는 것이 실행) |

**끝난 검증**: 기준선 `tests/release` 347 OK(skipped 3) → target 트리 **354 OK**(새 테스트 7건은 RED 확인 뒤 GREEN) · 9개 앱 kustomize 렌더 diff = 서비스마다 `startupProbe` 7줄, migration 은 `imagePullSecrets` 2줄, 삭제 0 · `_probe_api` 실물: `https://leva.ai.kr` 수락, **9/21 사고의 함수 없는 배포 `9814656f.devpath-home-page.pages.dev` 는 `HTTPError 404` 로 거부** · `prove_next_base.py` 7/7(target 은 gitops chain base 요건과 shared 의 실제 렌더 경로 `set-migration-release` → build → `validate-migration-render` 를 통과, 대조군 3건은 거부) · 헬퍼는 9/21 실행본 대비 치환표의 항목만 다름(diff 70줄) · 계약 테스트 16건: 9/21 워크플로에 RED(8건) → 새 워크플로에 GREEN · actionlint(헬퍼·디스패처) · 계약 변이 9종 전부 killed · step 변이: 실제 target 통과 / 11경로·13경로는 전체 목록 비교에서, 같은 12경로의 내용 변조는 트리 핀에서 사망 · 실행 스크립트는 9/21 실행본 대비 좌표 8줄만 다름, 단위 테스트 18 OK.

**남은 준비**: ① 독립 리뷰(새 컨텍스트, 읽기 전용) — 세션 종료 시점에 **진행 중이었고 결과를 받지 못했다.** 입력 패키지를 다시 만드는 명령과 지시문의 뼈대는 `plans/2026-09-21-gitops-main-pipeline-defects-via-publisher/REVIEW.md` 에 있다. 다음 세션은 리뷰를 **처음부터 다시** 돌린다 ② 발견 사항을 변이·재현으로 확인한 뒤 수정(헬퍼·target 이 바뀌면 핀을 다시 굴린다) ③ 헬퍼·디스패처 push ④ live `--preflight-only` + 음성 대조(틀린 `--helper-sha`) ⑤ §12.4 의 확인 관문.

§11 이 SA 를 분리하며 든 우려("M 렌더 검증에 걸릴 수 있어")는 실제 게이트 코드로 **해당 없음**을 확인했다 — shared 의 렌더 검증은 Job 문서만 본다.
