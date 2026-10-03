# S2a ③ — gitops main 승격 (①+② 를 main 에, 봉인 해제 → squash 머지 → 재봉인) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> ## ⛔ 2026-09-19 정정 — 이 계획의 Task 2~4(봉인 해제 → admin squash 머지)는 **실행하지 않는다**
>
> Task 0·1 을 실행해 PR DevPathAi/devpath-gitops#162 를 열자 `mission-spine-main-pr-policy` 가 실패했다:
> `main PR may not change the base-owned policy implementation: release-manifests/…, scripts/release/…`.
> 이것은 의도된 게이트다 — `scripts/release/verify_main_pr_policy.py` 는 main 대상 PR 이 `.github/workflows/`·`.github/actions/`·
> `scripts/release/`·`tools/release-wrangler/`·`release-manifests/` 아래를 **일절 바꾸지 못하게** 한다(2026-08-17 도입).
>
> **통제면 변경의 정식 경로는 PR 이 아니라 "publisher" 다**(실측, 2026-09-03~09-12 의 main 통제면 커밋 전부):
> 1. 현재 main 바로 위에 `devpath-gitops-release[bot]` 작성자·커미터의 **단일 target 커밋**을 만들어 `fix/…-main-<날짜>` 브랜치로 올린다.
> 2. main + 1커밋짜리 **헬퍼 브랜치**(`chore/…-publish-<날짜>`)가 `.github/workflows/mission-spine-auth-smoke.yml` 을 one-shot publisher 로 바꾸고
>    그 계약 테스트 1개를 더한다. `workflow_dispatch`(`full: true`, attempt 1, actor 고정)로 띄운다.
> 3. 보호 환경 `mission-spine-production-off`(리뷰어 `VelkaressiaBlutkrone`, `prevent_self_review: true`, 허용 브랜치는 현재 `main` 뿐) 승인 뒤,
>    target 에서 전체 스위트를 돌리고 → 릴리스 App 토큰을 발급해 `verify_gitops_write_authority.py` 로 쓰기 권한을 검증하고 →
>    **App 이 `TARGET_SHA:refs/heads/main` 을 fast-forward push** 한다. **봉인은 풀지 않는다**(App 이 governance 룰셋의 유일한 bypass 주체다).
> 참고 구현: `origin/chore/prod27r4-cloudflare-pagination-publish-20260912` 의 `mission-spine-auth-smoke.yml`.
>
> 9/9~9/10 의 #146·#148·`db36521` 은 사람이 봉인을 풀고 정책 체크 실패를 넘겨 머지한 것이다 — 그 뒤로는 쓰이지 않았다. 이 계획이 택했던 방식이 그것이고,
> **의도된 게이트를 넘어가는 방식이라 쓰지 않는다.** Task 0(패치 적용)의 결과와 #162 의 CI(main 기준 전체 **347건 OK**, head `4f0ba69`)는 그대로 유효한
> 증거다 — publisher 의 target 커밋은 같은 트리를 봇 작성자로 다시 만든 것이어야 한다. publisher 경로의 설계·계획은 사용자 결정 뒤 별도 문서로 쓴다.
> 봉인에는 손대지 않았다(룰셋 2종 active · classic 그대로, 2026-09-19 확인).

**Goal:** gitops `develop` 에 들어간 S2a ①(서명 모바일·TalkBack 제거, #160)과 ②(ET13 final rebind, #161)를 **한 번의 squash PR 로 `main` 에 올린다.** main 의 봉인(룰셋 2종 + classic 보호)은 머지에 필요한 최소한만, 머지에 필요한 시간만 풀고 원래 형상으로 되돌린다.

**Architecture:** main 과 develop 은 9개 파일에서 이미 갈라져 있다(main 에만 있는 릴리스 수정이 있다 — 실측). 그래서 develop 의 파일을 복사하지 않고 **①+② 의 diff 를 main 위에 패치로 적용**한다. 봉인은 "해제 전 GET 스냅샷 → 최소 해제 → 머지 → 스냅샷대로 복원 → 복원 결과 == 스냅샷 확인 + `validate_authority_state`" 의 순서로 다루고, 해제 뒤의 모든 단계는 한 스크립트가 `trap` 으로 재봉인을 보장한다.

**Tech Stack:** git · GitHub REST API(`gh api`) · Python 3(`unittest`)

**Spec:** `docs/superpowers/specs/2026-09-19-s2c2-s2a-drop-signed-mobile-and-gitops-mirror-design.md` §4.3·§5.2·§9 (documents 레포)

## Global Constraints

- 작업 레포: `DevPathAi/devpath-gitops`. 주 checkout 은 건드리지 않는다. worktree `D:/workspace/dpa/.worktrees/gitops-s2a3`(이하 `$WT`), 브랜치 `release/s2a-main-promotion` ← **`origin/main`**.
- 모든 git·파일 명령은 절대경로 또는 `git -C <절대경로>`. worktree 를 지우기 전에 셸 cwd 를 밖으로 옮긴다.
- **운영 접점이다.** main 의 스크립트는 promote·rollback·landing 워크플로가 그대로 실행한다. 머지 시점부터 다음 릴리스 승격까지 현재 운영 릴리스 `ms-20260916-community-ia` 의 **자동 롤백 레인이 닫힌다**(구 모양 candidate 를 새 검증기가 거부 — 사용자가 수용한 위험, 스펙 §2). 그 기간의 비상 수단은 수동 gitops 다.
- **사용자 확인 게이트**(사용자 결정, 스펙 §2 Q5): 전제조건을 AI 가 모두 채운 뒤 요약을 보여 주고 "진행"을 받는다. 그 전에는 봉인에 손대지 않는다. 받은 뒤에는 해제 → 머지 → 재봉인 → 검증을 멈추지 않고 끝낸다.
- **진행 중인 승격 체인이 없어야 한다.** `verify_promotion_chain.py` 는 승격 체인 사이에 끼어든 main 커밋을 등록된 fix 만 허용한다. 다음 candidate 의 `gitops.base_sha` 는 이 승격 커밋 이후여야 한다.
- 봉인 형상(2026-09-19 실측): governance `21194270`(active · `update` · bypass = App `4679079` always) · integrity `21194269`(active · `deletion`·`non_fast_forward`·`required_linear_history` · bypass 없음) · classic(`enforce_admins` true · reviews 1 + `dismiss_stale` + `require_last_push_approval` · push 제한 = `devpath-gitops-release` 단독 · linear · conversation resolution). `gh` 계정 `VelkaressiaBlutkrone` 은 레포 admin.
- **최소 해제**: governance 비활성(사람 계정의 ref 갱신을 막는다) + classic 의 `enforce_admins` 해제(admin 이 리뷰 1·push 제한을 우회해 머지). **integrity 는 풀지 않는다** — squash 머지는 linear 다. 머지가 integrity 에 막히면 그때만 풀고, 같은 `trap` 이 되돌린다.
- 권한 분류기가 보호 설정 변경이나 머지를 거부하면 같은 호출을 기계적으로 반복하지 않는다. 거부 메시지와 함께 Task 4 의 명령 묶음을 `!` 접두 형식으로 사용자에게 건넨다.
- 파이썬은 `py`. 이 PC 에서 gitops 전체 스위트는 11~15분 걸린다 → 로컬은 관련 모듈만, 전체 게이트는 PR 의 CI.

---

### Task 0: 승격 브랜치 — ①+② 를 main 위에 패치로

- [ ] **Step 1: 범위 확정과 worktree**

```bash
G=D:/workspace/dpa/devpath-gitops; git -C $G fetch origin
git -C $G log --oneline 988661b..origin/develop          # ①(#160)+②(#161) 의 커밋만 있어야 한다
git -C $G log -1 --format='%h %s' origin/main             # 4f3ed64 … mission-on
git -C $G worktree add -b release/s2a-main-promotion D:/workspace/dpa/.worktrees/gitops-s2a3 origin/main
```

Expected: 첫 명령의 비-머지 커밋이 전부 `s2a`/`release`/`test(release)`/`docs(release)` 계열이고 그 밖의 작업이 섞여 있지 않다. `origin/main` 이 `4f3ed64` 가 아니면(새 릴리스 봇 커밋 등) 멈추고, 진행 중인 승격 체인이 있는지 먼저 확인한다.

- [ ] **Step 2: 패치 생성과 적용**

```bash
S="<스크래치패드>/s2a3"; mkdir -p "$S"
git -C $G diff --binary 988661b origin/develop > "$S/s2a.patch"
git -C D:/workspace/dpa/.worktrees/gitops-s2a3 apply --3way --index "$S/s2a.patch" > "$S/apply.log" 2>&1; echo "APPLY_EXIT=$?"
grep -ciE "conflict|error|does not apply|failed" "$S/apply.log"
git -C D:/workspace/dpa/.worktrees/gitops-s2a3 status --short | awk '{print $1}' | sort | uniq -c
```

Expected: `APPLY_EXIT=0` · 충돌 문구 0(2026-09-19 드라이런에서 `--check` exit 0 확인) · 상태가 추가 8 / 수정 17 / 이름 변경 1 안팎. **`APPLY_EXIT` 는 파이프 없이 직접 찍는다**(파이프 뒤의 `$?` 는 마지막 명령의 것이다).

- [ ] **Step 3: develop 과의 일치 확인 — ①+② 가 건드린 경로만**

```bash
cd D:/workspace/dpa/.worktrees/gitops-s2a3
for p in $(git -C $G diff --name-only 988661b origin/develop); do
  a=$(git rev-parse -q --verify ":$p" 2>/dev/null || echo ABSENT); b=$(git -C $G rev-parse -q --verify "origin/develop:$p" 2>/dev/null || echo ABSENT)
  [ "$a" = "$b" ] || echo "DIFF $p"
done
```

Expected: `tests/release/test_release_contract.py` 와 `tests/release/test_release_hardening.py` **두 줄만** `DIFF` 로 나온다 — 이 둘은 변경 전부터 main 과 develop 이 달랐고(실측), 패치는 main 쪽 내용 위에 ①+② 의 hunk 만 얹는다. 그 밖의 파일이 `DIFF` 면 멈추고 원인을 규명한다.

- [ ] **Step 4: 관련 모듈 로컬 실행과 커밋**

```bash
cd D:/workspace/dpa/.worktrees/gitops-s2a3 && py -m unittest tests.release.test_frontend_et13_pinned_contract tests.release.test_mobile_free_release_contract tests.release.test_et13_final_rebind tests.release.test_et13_evidence_contract tests.release.test_et13_atomic_evidence tests.release.test_manual_nvda_trust tests.release.test_release_contract 2>&1 | grep -E "^(ERROR|FAIL|OK|FAILED|Ran)"
py -m pyflakes scripts/release/frontend_et13_contract.py scripts/release/validate_release_manifest.py scripts/release/verify_release_artifacts.py scripts/release/seal_release_manifest.py
git -C D:/workspace/dpa/.worktrees/gitops-s2a3 commit -q -m "release: promote the mobile-free release contract and the pinned ET13 catalog to main"
```

Expected: `OK` · pyflakes 출력 없음. 커밋 메시지 본문에는 #160·#161 과 스펙 경로를 적고 `Co-Authored-By` 줄로 끝낸다.

---

### Task 1: PR 과 CI

- [ ] **Step 1**: push → `gh pr create --base main --head release/s2a-main-promotion`. 본문: ①+② 요약 · 패치 적용 방식과 Task 0 Step 3 의 결과 · **수용한 위험(롤백 레인)** · 진행 중인 승격 체인 없음 · 머지는 squash · 마지막 줄 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 2**: CI(`mission-spine-release-contract` = 전체 스위트, `kustomize`) 통과를 로그의 `Ran N tests … OK` 로 확인한다. main 대상 PR 에서도 `pull_request` 로 돈다(실측).
- [ ] **Step 3**: 독립 리뷰를 다시 시도한다 — Codex 가 여전히 한도 소진이면 시도한 사실과 오류를 PR 에 적는다(이 PR 의 내용은 develop 에서 이미 CI 를 통과한 ①+② 그대로이고, Task 0 Step 3 이 그 동일성을 보인다).

---

### Task 2: 전제조건 점검 → 사용자 확인

- [ ] **Step 1: 점검**

```bash
gh pr checks <PR> -R DevPathAi/devpath-gitops
gh pr view <PR> -R DevPathAi/devpath-gitops --json mergeable,mergeStateStatus,headRefOid
gh run list -R DevPathAi/devpath-gitops --limit 15 --json workflowName,status,createdAt -q '.[] | select(.status!="completed") | [.workflowName,.status,.createdAt] | @tsv'
git -C D:/workspace/dpa/devpath-gitops fetch origin && git -C D:/workspace/dpa/devpath-gitops rev-parse --short origin/main
gh api repos/DevPathAi/devpath-gitops/rulesets -q '.[] | [.id,.name,.enforcement] | @tsv'
```

Expected: CI 전부 pass · `MERGEABLE` · 진행 중인 promote/landing/rollback 실행 0 · `origin/main` 이 PR 의 base(`4f3ed64`) 그대로 · 룰셋 2종 active. (`mergeStateStatus` 는 봉인 때문에 `BLOCKED` 일 수 있다 — 그것이 풀려는 대상이다.)

- [ ] **Step 2: 사용자에게 요약을 보여 주고 "진행"을 받는다.** 요약에 넣을 것: PR 번호와 head · CI 결과(테스트 수) · 풀 것(governance 비활성 + `enforce_admins` 해제)과 풀지 않을 것(integrity) · 예상 소요(1~2분) · 머지 뒤 닫히는 롤백 레인 · 분류기가 거부하면 명령 묶음을 건넨다는 점. **답을 받기 전에는 Task 3 으로 가지 않는다.**

---

### Task 3: 해제 → squash 머지 → 재봉인 (한 번에, `trap` 으로 재봉인 보장)

- [ ] **Step 1: 스냅샷**

```bash
S="<스크래치패드>/s2a3"; R=DevPathAi/devpath-gitops
gh api repos/$R/rulesets/21194270 > "$S/governance.before.json"
gh api repos/$R/rulesets/21194269 > "$S/integrity.before.json"
gh api repos/$R/branches/main/protection > "$S/classic.before.json"
py -c "import json,sys; [json.load(open(p,encoding='utf-8')) for p in sys.argv[1:]]; print('snapshots parse')" "$S/governance.before.json" "$S/integrity.before.json" "$S/classic.before.json"
```

- [ ] **Step 2: 스크립트**(Write 도구로 `<스크래치패드>/s2a3/promote.sh` 에 쓴다 — heredoc 금지)

```bash
#!/usr/bin/env bash
set -uo pipefail
R=DevPathAi/devpath-gitops; PR="$1"; S="$2"
reseal() {
  echo "== reseal"
  gh api -X POST "repos/$R/branches/main/protection/enforce_admins" -q '.enabled' || echo "RESEAL_FAILED enforce_admins"
  gh api -X PUT "repos/$R/rulesets/21194270" -f enforcement=active -q '.enforcement' || echo "RESEAL_FAILED governance"
  if [ -f "$S/integrity.relaxed" ]; then
    gh api -X PUT "repos/$R/rulesets/21194269" -f enforcement=active -q '.enforcement' || echo "RESEAL_FAILED integrity"
  fi
}
trap reseal EXIT
echo "== unlock"
gh api -X PUT "repos/$R/rulesets/21194270" -f enforcement=disabled -q '.enforcement' || exit 10
gh api -X DELETE "repos/$R/branches/main/protection/enforce_admins" || exit 11
echo "== merge"
if ! gh pr merge "$PR" -R "$R" --squash --admin; then
  echo "merge refused with integrity active; relaxing integrity once"
  touch "$S/integrity.relaxed"
  gh api -X PUT "repos/$R/rulesets/21194269" -f enforcement=disabled -q '.enforcement' || exit 12
  gh pr merge "$PR" -R "$R" --squash --admin || exit 13
fi
echo "== merged"
```

```bash
bash "<스크래치패드>/s2a3/promote.sh" <PR> "<스크래치패드>/s2a3"; echo "PROMOTE_EXIT=$?"
```

Expected: `disabled` → (DELETE 는 출력 없음) → 머지 메시지 → `== merged` → `== reseal` → `true` → `active` · `PROMOTE_EXIT=0` · `RESEAL_FAILED` 0건. **`RESEAL_FAILED` 가 하나라도 있으면 즉시 같은 복원 명령을 다시 실행하고, 그래도 실패하면 사용자에게 바로 알린다**(봉인이 풀린 채로 두지 않는다).

- [ ] **Step 3: 복원 확인 — 스냅샷과 같은가**

```bash
S="<스크래치패드>/s2a3"; R=DevPathAi/devpath-gitops
gh api repos/$R/rulesets/21194270 > "$S/governance.after.json"; gh api repos/$R/rulesets/21194269 > "$S/integrity.after.json"; gh api repos/$R/branches/main/protection > "$S/classic.after.json"
py - "$S" <<'PY'
import json, sys
from pathlib import Path
s = Path(sys.argv[1])
def normalized(name):
    doc = json.loads((s / name).read_text(encoding="utf-8")); doc.pop("updated_at", None); return doc
for kind in ("governance", "integrity", "classic"):
    same = normalized(f"{kind}.before.json") == normalized(f"{kind}.after.json")
    print(kind, "restored" if same else "DRIFTED")
PY
```

Expected: 세 줄 모두 `restored`. `DRIFTED` 면 두 파일을 diff 해 어긋난 필드를 그 값으로 되돌린다.

- [ ] **Step 4: 봉인 형상 검증기**

`validate_authority_state` 를 실데이터로 돌린다. App 설치 목록(`/installation/repositories`)은 App 토큰 전용이라 목표 상태를 대입한다(2026-08-22 의 기법 — CI 의 write-authority 스모크가 그 부분을 실측한다).

```bash
cd D:/workspace/dpa/devpath-gitops && git fetch origin && py - <<'PY'
import importlib.util, json, subprocess, sys
src = subprocess.run(["git", "show", "origin/main:scripts/release/verify_gitops_write_authority.py"], check=True, capture_output=True).stdout
spec = importlib.util.spec_from_loader("authority", loader=None); module = importlib.util.module_from_spec(spec); exec(compile(src, "verify_gitops_write_authority.py", "exec"), module.__dict__)
def api(path): return json.loads(subprocess.run(["gh", "api", path], check=True, capture_output=True).stdout)
repo = "DevPathAi/devpath-gitops"
rulesets = api(f"repos/{repo}/rulesets?includes_parents=true&per_page=100")
details = {r["id"]: api(f"repos/{repo}/rulesets/{r['id']}") for r in rulesets}
repo_id = api(f"repos/{repo}")["id"]
print(module.validate_authority_state(
    app_slug="devpath-gitops-release", installation_id=155611619,
    repositories={"total_count": 1, "repositories": [{"full_name": repo, "archived": False, "id": repo_id}]},
    classic_protection_status=200, classic_protection=api(f"repos/{repo}/branches/main/protection"),
    rulesets=rulesets, rule_details=details, expected_app_id=4679079,
))
PY
```

Expected: `{'app_slug': 'devpath-gitops-release', 'app_id': 4679079, 'installation_id': 155611619, 'ruleset_ids': [21194269, 21194270]}`. `ValueError` 면 메시지가 가리키는 형상을 Step 3 의 스냅샷과 대조해 복원한다.

---

### Task 4: 분류기가 거부했을 때 사용자에게 건넬 명령 묶음

Task 3 을 AI 가 실행할 수 없으면(권한 분류기의 거부 메시지가 증거), 아래를 그대로 건넨다. 실행 뒤 AI 가 Task 3 Step 3·4 와 Task 5 를 이어받는다.

```
! gh api -X PUT repos/DevPathAi/devpath-gitops/rulesets/21194270 -f enforcement=disabled -q .enforcement
! gh api -X DELETE repos/DevPathAi/devpath-gitops/branches/main/protection/enforce_admins
! gh pr merge <PR> -R DevPathAi/devpath-gitops --squash --admin
! gh api -X POST repos/DevPathAi/devpath-gitops/branches/main/protection/enforce_admins -q .enabled
! gh api -X PUT repos/DevPathAi/devpath-gitops/rulesets/21194270 -f enforcement=active -q .enforcement
```

반복해서 거부되는 종류면 settings 의 허용 규칙 추가를 제안한다(허용 규칙 추가 자체는 사용자 몫).

---

### Task 5: 머지 뒤 검증과 정리

- [ ] main 의 새 커밋이 squash 1건인지(`git log origin/main --oneline -3`), 그 트리에서 Task 0 Step 3 의 일치가 그대로인지 확인한다.
- [ ] main push 가 띄운 CI(`mission-spine-release-contract`) 통과를 로그로 확인한다.
- [ ] 주 checkout 불변 · 인접 레포에 낯선 브랜치 없음 · worktree 와 브랜치 정리.
- [ ] documents 에 결과 기록(승격 커밋 SHA · 롤백 레인이 닫힌 시각 · 다음 단계), 메모리 갱신.

## 다음 (범위 밖)

frontend main `31a7785d…` 에 대해 ET13 baseline **봇 디스패치**(`automation/dispatch-<release_id>` 브랜치의 디스패처 — `gh workflow run` 으로 직접 띄우지 않는다, `current_user_can_approve` 확인) → 사람의 시각 승인 → gitops candidate(`base_sha` ≥ 승격 커밋) → 수동 NVDA 증거·나머지 증거 → seal → promote → landing-last(prior deployment 기대값 `005cf175-6e3e-4400-a201-1987ce9d8d84`, N01 Cloudflare 토큰은 사람 단계).
