# gitops main 승격 — one-shot publisher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gitops `develop` 의 S2a ①(#160)·②(#161)를, 봉인을 풀지 않고 one-shot publisher 로 `main` 에 fast-forward 한다.

**Architecture:** main `4f3ed64` 위에 브랜치 3개를 만든다 — 봇 작성자의 단일 **target** 커밋(#162 와 같은 트리), `mission-spine-auth-smoke.yml` 을
publisher 로 바꾼 **헬퍼** 1커밋, 헬퍼를 `github-actions[bot]` 으로 띄우는 **디스패처** 1커밋. 실행은 한 Python 트랜잭션이 맡는다: 환경 브랜치 정책
임시 추가 → 디스패처 push → 대기 진입 → main-only 복원·검증 → 승인 → 감시 → 사후 검증. `prevent_self_review` 와 룰셋은 건드리지 않는다.

**Tech Stack:** git · GitHub Actions · GitHub REST API(`gh api`) · Python 3(`unittest`, PyYAML) · actionlint v1.7.12

**Spec:** `docs/superpowers/specs/2026-09-20-gitops-main-promotion-via-publisher-design.md` (documents 레포, develop `4169a8b`)

> **이 계획의 코드는 작성 시점(2026-09-20)에 스크래치패드에서 실제로 돌려 확인했다**: 계약 테스트 11건 OK + 워크플로 변이 7종 전부 적발 ·
> 실행 스크립트 테스트 9건 OK + 변이 6종 전부 적발 · 두 워크플로 actionlint v1.7.12 무결 · target 생성 스크립트가 `69e7bd15…` 를 재현
> (#162 head 와 diff 0). 실행자는 같은 결과를 다시 얻어야 한다 — 다르면 멈춘다.
>
> **2026-09-20 리뷰 반영(Task 5)**: 아래 코드 블록은 독립 리뷰 뒤의 최종본이다(헬퍼 head `00cafba`). 계약 테스트 13건 ·
> 실행 트랜잭션 테스트 12건 · 변이 11종(원래 7 + 리뷰 4) 전부 적발. 무엇을 왜 고쳤는지는 문서 끝 「리뷰 결과」 절.

## Global Constraints

- **두 구간으로 나뉜다.** Part A(Task 0~6)는 운영·보호 설정에 쓰지 않는다 — 바로 실행한다. **Part B(Task 7~9)는 사용자가 정한 날, "진행" 확인을
  받은 뒤에만** 실행한다. Part A 끝(Task 6)에서 반드시 멈춘다.
- 고정 좌표(전부 실측, 스펙 §3~§4):
  - `MAIN_SHA` = `4f3ed64b2a148394eb0b8b3f5311e327f0edd759`
  - `TARGET_SHA` = `69e7bd15570f5ba0f271c83b5bd46955cb249c8e` · `TARGET_TREE` = `7799cc07f3083a002d0e2064db5437e2cde46f84`
  - PR #162 head = `4f0ba697c7a9994e1ba263e04cc4bd7e6db8aefe`
  - target 브랜치 `fix/s2a-mobile-free-contract-main-20260920` · 헬퍼 브랜치 `chore/s2a-mobile-free-contract-publish-20260920`
  - staged 디스패처 `chore/s2a-main-publish-dispatcher-staged-20260920` · 방아쇠 브랜치 `automation/dispatch-s2a-main-publish`
  - 환경 `mission-spine-production-off`(main 정책 id `57524487`) · 리뷰어 `VelkaressiaBlutkrone` · 룰셋 `21194269`·`21194270`
- 봇 신원(세 커밋 모두): 이름 `devpath-gitops-release[bot]`, 이메일 `244265210+devpath-gitops-release[bot]@users.noreply.github.com`.
  환경변수는 `export` 로 준다(`env NAME=VAL cmd` 형식은 이 PC 의 uv shim 이 깨뜨린다).
- 레포: gitops `D:/workspace/dpa/devpath-gitops`(이하 `$G`) · documents `D:/workspace/dpa/documents`. **주 checkout 은 건드리지 않는다** — worktree 는
  `D:/workspace/dpa/.worktrees/` 아래에 만들고, 지우기 전에 셸 cwd 를 밖으로 옮긴다.
- 모든 git·파일 명령은 절대경로 또는 `git -C <절대경로>`. Bash 에서는 `export MSYS_NO_PATHCONV=1`. Python 은 `py`(이 PC 의 `python` 은 스텁).
- 파일은 **Write 도구로** 만든다(Bash heredoc 안의 백슬래시 치환은 조용히 빗나간다). 워크플로·테스트·스크립트는 LF.
- `… | tail` 뒤의 `$?` 는 `tail` 의 것이다 — 종료코드는 `${PIPESTATUS[0]}` 로 보거나 파이프 없이 본다. 대기는 `gh run watch <id> --interval N --exit-status` 포그라운드.
- **헬퍼·디스패처 브랜치에는 CI 가 돌지 않는다**(`ci.yml` = `push: main` + `pull_request`). PR 을 열지 않는다 — main 대상 PR 은 정책 게이트가 막는다(의도).
- 어떤 단언이든 어긋나면 **고치려 들지 말고 멈춰서 보고한다.** main 이 `MAIN_SHA` 에서 움직였으면 이 계획의 핀은 전부 무효다.
- 서브에이전트에 위임할 때는 `C:\Users\deepe\.claude\rules\subagent-scope.md` 의 범위 고정 문구와 절대경로 문구를 포함하고, 결과는 컨트롤러가 직접 검증한다.

## File Structure

| 파일 | 레포·브랜치 | 책임 |
|---|---|---|
| (커밋만) | gitops · target 브랜치 | #162 와 같은 트리의 봇 단일 커밋 |
| `.github/workflows/mission-spine-auth-smoke.yml` | gitops · 헬퍼 | one-shot publisher(기존 auth-smoke 를 덮어쓴다 — main 에는 들어가지 않는다) |
| `tests/release/test_s2a_main_publish.py` | gitops · 헬퍼 | publisher 의 계약 테스트. publisher 가 첫 단계에서 스스로 돌린다 |
| `.github/workflows/mission-spine-release-gate-dispatch.yml` | gitops · 디스패처 | 헬퍼의 publisher 를 `github-actions[bot]` 으로 디스패치(신규 파일) |
| `docs/superpowers/plans/2026-09-20-gitops-main-promotion-via-publisher/make_target.py` | documents | target 커밋을 결정적으로 만든다 |
| `…/run_s2a_main_publish.py` · `…/test_run_s2a_main_publish.py` | documents | 실행 트랜잭션과 가짜 API 테스트 |

스펙 §4.4 는 실행 스크립트를 "레포 밖, 계획에 전문 수록"이라 했다. 이 계획은 전문을 수록하되 **같은 바이트를 documents 에도 커밋한다** — 준비와 실행이
다른 세션이고 스크래치패드는 세션마다 새로 생기기 때문이다. documents 는 `autocrlf` 로 checkout 이 CRLF 가 될 수 있으므로 실행 때는
`git show origin/develop:<경로>` 로 블롭을 꺼내 쓴다.

---

# Part A — 준비 (운영·보호 설정에 쓰지 않는다)

### Task 0: 전제 재측정, 방치된 대기 실행 취소

**Files:** 없음(조회와 실행 1건 취소)

**Interfaces:**
- Produces: "gitops 에 진행·대기 중인 실행 0" 상태. Task 4 의 `--preflight-only` 와 Part B 가 이 상태를 요구한다.

- [ ] **Step 1: 좌표가 계획과 같은지 확인**

```bash
export MSYS_NO_PATHCONV=1
G=D:/workspace/dpa/devpath-gitops; R=DevPathAi/devpath-gitops
git -C $G fetch origin --quiet
git -C $G rev-parse origin/main          # 4f3ed64b2a148394eb0b8b3f5311e327f0edd759
git -C $G rev-parse origin/develop       # 9204c33fd0705e192b25efff2258911b649be884
git -C $G rev-parse 'origin/release/s2a-main-promotion^{tree}'   # 7799cc07f3083a002d0e2064db5437e2cde46f84
gh pr view 162 -R $R --json state,headRefOid   # OPEN / 4f0ba697…
gh api repos/$R/rulesets -q '.[] | [.id,.name,.enforcement] | @tsv'   # 두 줄 모두 active
gh api repos/$R/environments/mission-spine-production-off/deployment-branch-policies -q '.branch_policies[] | [.id,.name,.type] | @tsv'   # 57524487 main branch 한 줄
```

Expected: 주석의 값과 전부 일치. 하나라도 다르면 **멈추고 보고**.

- [ ] **Step 2: 방치된 대기 실행이 아직 있는지 확인**

```bash
gh run list -R $R --status waiting --json databaseId,headBranch,createdAt -q '.[] | [.databaseId,.headBranch,.createdAt] | @tsv'
```

Expected: `34422926318  chore/prod27-ai-digest-main-publish-20260910  2026-09-10T00:49:39Z` 한 줄(또는 이미 만료돼 0줄). **다른 실행이 보이면 멈추고 보고** —
이 계획이 모르는 대기 실행은 취소하지 않는다.

- [ ] **Step 3: 그 실행을 취소**

```bash
gh run cancel 34422926318 -R $R
gh run view 34422926318 -R $R --json status,conclusion   # completed / cancelled
```

- [ ] **Step 4: 진행·대기 실행이 0인지 확인**

```bash
for s in in_progress queued waiting requested pending; do
  echo "$s=$(gh api "repos/$R/actions/runs?status=$s&per_page=1" -q .total_count)"
done
```

Expected: 다섯 줄 모두 `=0`.

### Task 1: target 커밋을 만들어 push

**Files:**
- Create: `D:/workspace/dpa/.worktrees/docs-s2a-publish-runner/docs/superpowers/plans/2026-09-20-gitops-main-promotion-via-publisher/make_target.py`

**Interfaces:**
- Produces: 원격 브랜치 `fix/s2a-mobile-free-contract-main-20260920` = `69e7bd15570f5ba0f271c83b5bd46955cb249c8e`. 헬퍼 워크플로(Task 2)와 실행 스크립트(Task 4)가 이 SHA 를 핀한다.

- [ ] **Step 1: documents worktree 를 만든다(Task 1·4 가 함께 쓴다)**

```bash
export MSYS_NO_PATHCONV=1
D=D:/workspace/dpa/documents; DW=D:/workspace/dpa/.worktrees/docs-s2a-publish-runner
git -C $D fetch origin --quiet
git -C $D worktree add -b chore/s2a-main-publish-runner $DW origin/develop
mkdir -p $DW/docs/superpowers/plans/2026-09-20-gitops-main-promotion-via-publisher
```

- [ ] **Step 2: Write 도구로 `make_target.py` 를 만든다**

```python
#!/usr/bin/env python3
"""Create the deterministic S2a target commit (no ref, no push) and print its SHA."""

from __future__ import annotations

import os
import subprocess
import sys

MAIN_SHA = "4f3ed64b2a148394eb0b8b3f5311e327f0edd759"
TARGET_TREE = "7799cc07f3083a002d0e2064db5437e2cde46f84"
PR162_HEAD = "4f0ba697c7a9994e1ba263e04cc4bd7e6db8aefe"
EXPECTED_TARGET_SHA = "69e7bd15570f5ba0f271c83b5bd46955cb249c8e"
BOT_NAME = "devpath-gitops-release[bot]"
BOT_EMAIL = "244265210+devpath-gitops-release[bot]@users.noreply.github.com"
FIXED_DATE = "1789873200 +0000"  # 2026-09-20T03:00:00Z - fixed so the SHA is reproducible

MESSAGE = "\n".join(
    [
        "release: promote the mobile-free release contract and the pinned ET13 catalog to main",
        "",
        "Squash promotion of S2a (1) #160 and (2) #161 from develop:",
        "- drop the candidate-prebound signed Android build and the manual TalkBack lane",
        "  (quality evidence 6 -> 5 labels; schema_version stays 1, in-place)",
        "- rebind the ET13 contract to the 13-fixture frontend catalog at frontend main",
        "  31a7785d5f3c73563c8ddb61b69a7a0e07f65f16 and derive the fixture list, projection matrix,",
        "  counts and surfaces from eight byte-pinned producer files",
        "",
        "main and develop had already diverged in nine files, so this applies the develop diff",
        "(988661b..9204c33) as a patch on top of main instead of copying files.",
        "",
        "Tree 7799cc07f3083a002d0e2064db5437e2cde46f84 is byte-identical to PR #162 head",
        "4f0ba697c7a9994e1ba263e04cc4bd7e6db8aefe, whose CI passed the full release suite on main.",
        "Published by the one-shot publisher, not merged: main PRs may not change the control plane.",
        "",
        "Spec: documents docs/superpowers/specs/2026-09-20-gitops-main-promotion-via-publisher-design.md",
        "",
        "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>",
        "",
    ]
)


def git(repo: str, *args: str, stdin: bytes | None = None, env: dict[str, str] | None = None) -> str:
    done = subprocess.run(
        ["git", "-C", repo, *args], input=stdin, capture_output=True, env=env, check=False
    )
    if done.returncode != 0:
        raise SystemExit(f"git {' '.join(args[:3])} failed: {done.stderr.decode(errors='replace')}")
    return done.stdout.decode().strip()


def main() -> int:
    repo = sys.argv[1]
    if git(repo, "rev-parse", "origin/main") != MAIN_SHA:
        raise SystemExit("origin/main moved away from MAIN_SHA - stop and re-plan")
    if git(repo, "rev-parse", f"{PR162_HEAD}^{{tree}}") != TARGET_TREE:
        raise SystemExit("PR #162 head tree is not TARGET_TREE")
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": BOT_NAME,
        "GIT_AUTHOR_EMAIL": BOT_EMAIL,
        "GIT_AUTHOR_DATE": FIXED_DATE,
        "GIT_COMMITTER_NAME": BOT_NAME,
        "GIT_COMMITTER_EMAIL": BOT_EMAIL,
        "GIT_COMMITTER_DATE": FIXED_DATE,
    }
    target = git(
        repo, "commit-tree", TARGET_TREE, "-p", MAIN_SHA, "-F", "-",
        stdin=MESSAGE.encode("utf-8"), env=env,
    )
    if target != EXPECTED_TARGET_SHA:
        raise SystemExit(f"target SHA {target} != pinned {EXPECTED_TARGET_SHA} - stop")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: 실행 — 핀한 SHA 가 재현되는지 확인**

```bash
G=D:/workspace/dpa/devpath-gitops
py $DW/docs/superpowers/plans/2026-09-20-gitops-main-promotion-via-publisher/make_target.py $G
```

Expected: `69e7bd15570f5ba0f271c83b5bd46955cb249c8e` 한 줄, exit 0. 다른 SHA 면 스크립트가 스스로 멈춘다 — **메시지·날짜를 손보지 말고 보고**
(핀이 헬퍼·실행 스크립트·계약 테스트에 퍼져 있다).

- [ ] **Step 4: 커밋을 검사**

```bash
T=69e7bd15570f5ba0f271c83b5bd46955cb249c8e
git -C $G show -s --format='%P|%an|%ae|%cn|%ce|%T' $T
git -C $G diff --quiet 4f0ba697c7a9994e1ba263e04cc4bd7e6db8aefe $T; echo "diff_rc=$?"
git -C $G diff --check 4f3ed64b2a148394eb0b8b3f5311e327f0edd759 $T; echo "check_rc=$?"
git -C $G diff --name-only 4f3ed64b2a148394eb0b8b3f5311e327f0edd759 $T | grep -vE '^(release-manifests|scripts/release|tests/release)/' ; echo "outside_rc=$?"
```

Expected: 첫 줄 `4f3ed64b…|devpath-gitops-release[bot]|244265210+…|devpath-gitops-release[bot]|244265210+…|7799cc07…` · `diff_rc=0` · `check_rc=0` ·
`outside_rc=1`(접두사 밖 경로 0건이라 grep 이 아무것도 못 찾음).

- [ ] **Step 5: push 하고 원격을 확인**

```bash
git -C $G push origin $T:refs/heads/fix/s2a-mobile-free-contract-main-20260920
gh api repos/DevPathAi/devpath-gitops/branches/fix/s2a-mobile-free-contract-main-20260920 -q .commit.sha
gh run list -R DevPathAi/devpath-gitops --branch fix/s2a-mobile-free-contract-main-20260920 --limit 3
```

Expected: SHA 일치, 실행 0건(이 브랜치 push 에 반응하는 워크플로는 없다).

### Task 2: 헬퍼 브랜치 — 계약 테스트 먼저, 그다음 publisher

**Files:**
- Create: `D:/workspace/dpa/.worktrees/gitops-s2a-publish-helper/tests/release/test_s2a_main_publish.py`
- Modify(전체 교체): `D:/workspace/dpa/.worktrees/gitops-s2a-publish-helper/.github/workflows/mission-spine-auth-smoke.yml`

**Interfaces:**
- Consumes: Task 1 의 target 브랜치·`TARGET_SHA`.
- Produces: 원격 브랜치 `chore/s2a-mobile-free-contract-publish-20260920`(main + 정확히 1커밋·2경로). 워크플로의 step 이름은 계약 테스트가 그대로 참조한다 — 바꾸면 둘 다 바꾼다.

- [ ] **Step 1: worktree 를 main 에서 만든다**

```bash
export MSYS_NO_PATHCONV=1
G=D:/workspace/dpa/devpath-gitops; HW=D:/workspace/dpa/.worktrees/gitops-s2a-publish-helper
git -C $G worktree add -b chore/s2a-mobile-free-contract-publish-20260920 $HW 4f3ed64b2a148394eb0b8b3f5311e327f0edd759
```

- [ ] **Step 2: Write 도구로 실패할 계약 테스트를 만든다**

`$HW/tests/release/test_s2a_main_publish.py`:

```python
import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "mission-spine-auth-smoke.yml"

MAIN_SHA = "4f3ed64b2a148394eb0b8b3f5311e327f0edd759"
TARGET_SHA = "69e7bd15570f5ba0f271c83b5bd46955cb249c8e"
TARGET_TREE = "7799cc07f3083a002d0e2064db5437e2cde46f84"
HELPER_BRANCH = "chore/s2a-mobile-free-contract-publish-20260920"
TARGET_BRANCH = "fix/s2a-mobile-free-contract-main-20260920"
ENVIRONMENT = "mission-spine-production-off"
PINNED_ACTION = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}")
LINE_CONTINUATION = re.compile(r"\\\n[ \t]*")

STEP_CONTRACT_TEST = "Run the publisher contract test on the exact helper bytes"
STEP_LIVE_ENVIRONMENT = "Authenticate the live protected environment and this approval"
STEP_TARGET_TEST = "Test the exact S2a target"
STEP_MINT = "Mint the production-scoped release App token"
STEP_PUSH = "Fast-forward protected main to the exact tested S2a target"


class S2aMainPublishTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.document = yaml.safe_load(cls.text)
        cls.job = cls.document["jobs"]["publish"]
        cls.steps = cls.job["steps"]
        cls.names = [step.get("name") for step in cls.steps]

    def _run(self, name: str) -> str:
        matches = [step for step in self.steps if step.get("name") == name]
        self.assertEqual(1, len(matches), name)
        return matches[0]["run"]

    def test_trigger_is_the_single_boolean_dispatch(self) -> None:
        # PyYAML reads the bare key `on` as the boolean True.
        trigger = self.document.get("on", self.document.get(True))
        self.assertEqual(["workflow_dispatch"], list(trigger))
        self.assertEqual(["full"], list(trigger["workflow_dispatch"]["inputs"]))
        full = trigger["workflow_dispatch"]["inputs"]["full"]
        self.assertEqual("boolean", full["type"])
        self.assertIs(True, full["required"])
        self.assertIs(False, full["default"])

    def test_job_is_the_only_job_and_is_fenced(self) -> None:
        self.assertEqual(["publish"], list(self.document["jobs"]))
        self.assertEqual({"contents": "read"}, self.document["permissions"])
        self.assertEqual(
            {"actions": "read", "contents": "read", "deployments": "write"},
            self.job["permissions"],
        )
        self.assertEqual(ENVIRONMENT, self.job["environment"])
        self.assertEqual(
            {"group": "s2a-mobile-free-contract-main-publish", "cancel-in-progress": False},
            self.document["concurrency"],
        )
        self.assertEqual(
            f"github.ref == 'refs/heads/{HELPER_BRANCH}' && inputs.full",
            " ".join(self.job["if"].split()),
        )

    def test_exact_coordinates_are_pinned(self) -> None:
        env = self.job["env"]
        self.assertEqual(MAIN_SHA, env["MAIN_SHA"])
        self.assertEqual(MAIN_SHA, env["HELPER_BASE_SHA"])
        self.assertEqual(TARGET_SHA, env["TARGET_SHA"])
        self.assertEqual(TARGET_TREE, env["TARGET_TREE"])
        self.assertEqual(HELPER_BRANCH, env["HELPER_BRANCH"])
        self.assertEqual(TARGET_BRANCH, env["TARGET_BRANCH"])
        self.assertEqual(ENVIRONMENT, env["PROTECTED_ENVIRONMENT"])
        self.assertEqual("VelkaressiaBlutkrone", env["APPROVER_LOGIN"])

    def test_every_action_is_pinned_to_a_full_sha(self) -> None:
        used = [step["uses"] for step in self.steps if "uses" in step]
        self.assertTrue(used)
        for reference in used:
            self.assertIsNotNone(PINNED_ACTION.fullmatch(reference), reference)

    def test_helper_context_is_bot_dispatched_attempt_one(self) -> None:
        run = self._run("Prove the exact one-shot helper context")
        for fragment in (
            'test "$GITHUB_ACTOR" = "github-actions[bot]"',
            'test "$GITHUB_TRIGGERING_ACTOR" = "github-actions[bot]"',
            'test "$GITHUB_EVENT_NAME" = "workflow_dispatch"',
            'test "$GITHUB_RUN_ATTEMPT" = "1"',
            'test "$GITHUB_REF" = "refs/heads/$HELPER_BRANCH"',
            'test "$INPUT_FULL" = "true"',
            'test "$MAIN_SHA" = "$HELPER_BASE_SHA"',
            'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
            'test "$(git rev-parse HEAD^)" = "$HELPER_BASE_SHA"',
            'test "${#helper_paths[@]}" -eq 2',
            'test "${helper_paths[0]}" = ".github/workflows/mission-spine-auth-smoke.yml"',
            'test "${helper_paths[1]}" = "tests/release/test_s2a_main_publish.py"',
            'test "$current_main" = "$MAIN_SHA"',
        ):
            self.assertIn(fragment, run)
        self.assertNotIn("VelkaressiaBlutkrone", run)

    def test_target_is_pinned_by_tree_not_by_a_path_list(self) -> None:
        run = self._run(STEP_TARGET_TEST)
        for fragment in (
            'test "$(git rev-parse HEAD)" = "$TARGET_SHA"',
            'test "$(git rev-list --parents -n 1 HEAD)" = "$TARGET_SHA $MAIN_SHA"',
            "test \"$(git rev-parse 'HEAD^{tree}')\" = \"$TARGET_TREE\"",
            "release: promote the mobile-free release contract and the pinned ET13 catalog to main",
            "test \"$(git show -s --format=%an HEAD)\" = 'devpath-gitops-release[bot]'",
            "test \"$(git show -s --format=%cn HEAD)\" = 'devpath-gitops-release[bot]'",
            "release-manifests/*|scripts/release/*|tests/release/*) ;;",
            '*) echo "unexpected target path: $target_path" >&2; exit 1 ;;',
            'git diff --check "$MAIN_SHA" "$TARGET_SHA"',
            "python -m unittest discover -s tests/release -p 'test_*.py'",
        ):
            self.assertIn(fragment, run)
        self.assertEqual(
            2, run.count("244265210+devpath-gitops-release[bot]@users.noreply.github.com")
        )
        self.assertNotIn("--name-status", self.text)

    def test_live_environment_and_approval_are_authenticated(self) -> None:
        run = self._run(STEP_LIVE_ENVIRONMENT)
        for fragment in (
            "\"repos/$GITHUB_REPOSITORY/environments/$PROTECTED_ENVIRONMENT\"",
            "'.can_admins_bypass' <<<\"$environment_json\")\" = \"false\"",
            "| .prevent_self_review' <<<\"$environment_json\")\" = \"true\"",
            "= \"User:$APPROVER_LOGIN\"",
            "deployment-branch-policies?per_page=100",
            "'.total_count' <<<\"$policies_json\")\" = \"1\"",
            "= \"branch:main\"",
            "\"repos/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID/approvals\"",
            "'length' <<<\"$approvals_json\")\" = \"1\"",
            "'.[0].state' <<<\"$approvals_json\")\" = \"approved\"",
            "'.[0].user.login' <<<\"$approvals_json\")\" = \"$APPROVER_LOGIN\"",
        ):
            self.assertIn(fragment, run)

    def test_every_gate_precedes_the_app_token(self) -> None:
        mint = self.names.index(STEP_MINT)
        for gate in (
            "Prove the exact one-shot helper context",
            STEP_CONTRACT_TEST,
            STEP_LIVE_ENVIRONMENT,
            STEP_TARGET_TEST,
        ):
            self.assertLess(self.names.index(gate), mint, gate)
        self.assertLess(mint, self.names.index(STEP_PUSH))
        self.assertIn(
            "python -m unittest discover -s tests/release -p 'test_s2a_main_publish.py'",
            self._run(STEP_CONTRACT_TEST),
        )
        for step in self.steps[:mint]:
            self.assertNotIn("app_token", str(step), step.get("name"))

    def test_only_the_release_app_fast_forwards_main_exactly_once(self) -> None:
        mint = self.steps[self.names.index(STEP_MINT)]
        self.assertEqual("read", mint["with"]["permission-administration"])
        self.assertEqual("write", mint["with"]["permission-contents"])
        self.assertEqual("DevPathAi", mint["with"]["owner"])
        # Fold shell line continuations first: `git ... \` + `push ...` is ONE command.
        shell = "\n".join(
            LINE_CONTINUATION.sub(" ", step["run"]) for step in self.steps if "run" in step
        )
        pushes = [line.strip() for line in shell.splitlines() if re.search(r"\bpush\b", line)]
        self.assertEqual(
            ['git -C gitops-main push origin "$TARGET_SHA:refs/heads/main"'], pushes
        )
        run = self._run(STEP_PUSH)
        push_at = run.index("git -C gitops-main push origin")
        self.assertLess(run.index("verify_gitops_write_authority.py"), push_at)
        self.assertLess(
            run.index('test "$(git -C gitops-main rev-parse origin/main)" = "$MAIN_SHA"'),
            push_at,
        )
        self.assertLess(
            push_at,
            run.index('test "$(git -C gitops-main rev-parse origin/main)" = "$TARGET_SHA"'),
        )
        self.assertEqual(2, self.text.count("verify_gitops_write_authority.py"))
        for forbidden in ("--force", "+$TARGET_SHA", "+refs", "--mirror", "--delete"):
            self.assertNotIn(forbidden, self.text)

    def test_token_bearing_steps_have_no_other_write_path(self) -> None:
        # The App token can write any ref through the API, not only through `git push`.
        mint = self.names.index(STEP_MINT)
        for step in self.steps[mint:]:
            run = LINE_CONTINUATION.sub(" ", step.get("run", ""))
            for pattern in (r"\bgh\b", r"\bcurl\b", r"\bwget\b", r"git/refs", r"update-ref"):
                self.assertIsNone(re.search(pattern, run), (step.get("name"), pattern))
        # Pinned coordinates live in the job `env`; no step may rewrite them mid-job.
        for forbidden in ("GITHUB_ENV", "GITHUB_PATH", "BASH_ENV"):
            self.assertNotIn(forbidden, self.text)

    def test_listings_cannot_fail_silently(self) -> None:
        # `mapfile < <(cmd)` hides cmd's exit status from `set -e`; an assignment does not.
        self.assertNotIn("< <(", self.text)
        self.assertIn(
            'helper_listing="$(git diff-tree --no-commit-id --name-only -r HEAD)"',
            self._run("Prove the exact one-shot helper context"),
        )
        self.assertIn(
            'target_listing="$(git diff-tree --no-commit-id --name-only -r HEAD)"',
            self._run(STEP_TARGET_TEST),
        )

    def test_the_promotion_chain_is_deliberately_absent(self) -> None:
        for forbidden in (
            "verify_promotion_chain",
            "verify_migration_result",
            "SEALED_SHA",
            "sealed-release",
            "RELEASE_EVIDENCE_TOKEN",
            "RELEASE_ID",
        ):
            self.assertNotIn(forbidden, self.text)

    def test_published_main_is_re_authenticated(self) -> None:
        run = self._run("Re-authenticate the published main")
        self.assertIn('test "$(git -C gitops-main rev-parse origin/main)" = "$TARGET_SHA"', run)
        self.assertIn(
            "test \"$(git -C gitops-main rev-parse 'origin/main^{tree}')\" = \"$TARGET_TREE\"",
            run,
        )
        self.assertEqual("Re-authenticate the published main", self.names[-1])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

```bash
cd $HW && py -m unittest discover -s tests/release -p 'test_s2a_main_publish.py' 2>&1 | tail -5; cd /d/workspace/dpa
```

Expected: `ERROR`/`FAILED` — 지금 파일은 main 의 auth-smoke(job 이름이 `publish` 가 아니다)라 `setUpClass` 의 `jobs["publish"]` 에서 `KeyError`.

- [ ] **Step 4: Write 도구로 워크플로를 통째로 교체**

`$HW/.github/workflows/mission-spine-auth-smoke.yml`:

```yaml
name: S2a mobile-free release contract main publisher

on:
  workflow_dispatch:
    inputs:
      full:
        description: Publish the exact tested S2a mobile-free release contract to main
        type: boolean
        required: true
        default: false

permissions:
  contents: read

concurrency:
  group: s2a-mobile-free-contract-main-publish
  cancel-in-progress: false

jobs:
  publish:
    if: >-
      github.ref == 'refs/heads/chore/s2a-mobile-free-contract-publish-20260920' &&
      inputs.full
    runs-on: ubuntu-24.04
    timeout-minutes: 25
    environment: mission-spine-production-off
    permissions:
      actions: read
      contents: read
      deployments: write
    env:
      MAIN_SHA: 4f3ed64b2a148394eb0b8b3f5311e327f0edd759
      TARGET_SHA: 69e7bd15570f5ba0f271c83b5bd46955cb249c8e
      TARGET_TREE: 7799cc07f3083a002d0e2064db5437e2cde46f84
      HELPER_BASE_SHA: 4f3ed64b2a148394eb0b8b3f5311e327f0edd759
      HELPER_BRANCH: chore/s2a-mobile-free-contract-publish-20260920
      TARGET_BRANCH: fix/s2a-mobile-free-contract-main-20260920
      PROTECTED_ENVIRONMENT: mission-spine-production-off
      APPROVER_LOGIN: VelkaressiaBlutkrone
      GITHUB_API_VERSION: "2026-03-10"
      PYTHONDONTWRITEBYTECODE: "1"
    steps:
      - name: Checkout the exact helper branch
        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0
        with:
          ref: ${{ github.sha }}
          fetch-depth: 2
          persist-credentials: false
          path: helper

      - name: Prove the exact one-shot helper context
        working-directory: helper
        env:
          INPUT_FULL: ${{ inputs.full }}
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          test "$GITHUB_ACTOR" = "github-actions[bot]"
          test "$GITHUB_TRIGGERING_ACTOR" = "github-actions[bot]"
          test "$GITHUB_EVENT_NAME" = "workflow_dispatch"
          test "$GITHUB_RUN_ATTEMPT" = "1"
          test "$GITHUB_REF" = "refs/heads/$HELPER_BRANCH"
          test "$GITHUB_REF_NAME" = "$HELPER_BRANCH"
          test "$INPUT_FULL" = "true"
          test "$MAIN_SHA" = "$HELPER_BASE_SHA"
          test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
          test "$(git rev-parse HEAD^)" = "$HELPER_BASE_SHA"
          helper_listing="$(git diff-tree --no-commit-id --name-only -r HEAD)"
          mapfile -t helper_paths <<<"$helper_listing"
          test "${#helper_paths[@]}" -eq 2
          test "${helper_paths[0]}" = ".github/workflows/mission-spine-auth-smoke.yml"
          test "${helper_paths[1]}" = "tests/release/test_s2a_main_publish.py"
          current_main="$(
            gh api -H "X-GitHub-Api-Version: $GITHUB_API_VERSION" \
              "repos/$GITHUB_REPOSITORY/branches/main" --jq '.commit.sha'
          )"
          test "$current_main" = "$MAIN_SHA"

      - uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6.3.0
        with:
          python-version: "3.13"

      - name: Run the publisher contract test on the exact helper bytes
        working-directory: helper
        run: |
          set -euo pipefail
          python -m pip install --disable-pip-version-check PyYAML==6.0.2
          python -m unittest discover -s tests/release -p 'test_s2a_main_publish.py'

      - name: Authenticate the live protected environment and this approval
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          environment_json="$(
            gh api -H "X-GitHub-Api-Version: $GITHUB_API_VERSION" \
              "repos/$GITHUB_REPOSITORY/environments/$PROTECTED_ENVIRONMENT"
          )"
          test "$(jq -r '.name' <<<"$environment_json")" = "$PROTECTED_ENVIRONMENT"
          test "$(jq -r '.can_admins_bypass' <<<"$environment_json")" = "false"
          test "$(jq -r '.deployment_branch_policy.protected_branches' <<<"$environment_json")" = "false"
          test "$(jq -r '.deployment_branch_policy.custom_branch_policies' <<<"$environment_json")" = "true"
          test "$(jq -r '[.protection_rules[] | select(.type == "required_reviewers")] | length' <<<"$environment_json")" = "1"
          test "$(jq -r '.protection_rules[] | select(.type == "required_reviewers") | .prevent_self_review' <<<"$environment_json")" = "true"
          test "$(jq -r '[.protection_rules[] | select(.type == "required_reviewers") | .reviewers[] | "\(.type):\(.reviewer.login)"] | join(",")' <<<"$environment_json")" = "User:$APPROVER_LOGIN"
          policies_json="$(
            gh api -H "X-GitHub-Api-Version: $GITHUB_API_VERSION" \
              "repos/$GITHUB_REPOSITORY/environments/$PROTECTED_ENVIRONMENT/deployment-branch-policies?per_page=100"
          )"
          test "$(jq -r '.total_count' <<<"$policies_json")" = "1"
          test "$(jq -r '[.branch_policies[] | "\(.type):\(.name)"] | join(",")' <<<"$policies_json")" = "branch:main"
          approvals_json="$(
            gh api -H "X-GitHub-Api-Version: $GITHUB_API_VERSION" \
              "repos/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID/approvals"
          )"
          test "$(jq -r 'length' <<<"$approvals_json")" = "1"
          test "$(jq -r '.[0].state' <<<"$approvals_json")" = "approved"
          test "$(jq -r '.[0].user.login' <<<"$approvals_json")" = "$APPROVER_LOGIN"
          test "$(jq -r '[.[0].environments[].name] | join(",")' <<<"$approvals_json")" = "$PROTECTED_ENVIRONMENT"

      - name: Checkout the exact tested S2a target
        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0
        with:
          ref: ${{ env.TARGET_SHA }}
          fetch-depth: 2
          persist-credentials: false
          path: target

      - uses: azure/setup-kubectl@829323503d1be3d00ca8346e5391ca0b07a9ab0d # v5.1.0
        with:
          version: v1.36.2

      - name: Test the exact S2a target
        working-directory: target
        run: |
          set -euo pipefail
          test "$(git rev-parse HEAD)" = "$TARGET_SHA"
          test "$(git rev-list --parents -n 1 HEAD)" = "$TARGET_SHA $MAIN_SHA"
          test "$(git rev-parse 'HEAD^{tree}')" = "$TARGET_TREE"
          test "$(git show -s --format=%s HEAD)" = \
            'release: promote the mobile-free release contract and the pinned ET13 catalog to main'
          test "$(git show -s --format=%an HEAD)" = 'devpath-gitops-release[bot]'
          test "$(git show -s --format=%cn HEAD)" = 'devpath-gitops-release[bot]'
          test "$(git show -s --format=%ae HEAD)" = \
            '244265210+devpath-gitops-release[bot]@users.noreply.github.com'
          test "$(git show -s --format=%ce HEAD)" = \
            '244265210+devpath-gitops-release[bot]@users.noreply.github.com'
          target_listing="$(git diff-tree --no-commit-id --name-only -r HEAD)"
          test -n "$target_listing"
          mapfile -t target_paths <<<"$target_listing"
          test "${#target_paths[@]}" -gt 0
          for target_path in "${target_paths[@]}"; do
            case "$target_path" in
              release-manifests/*|scripts/release/*|tests/release/*) ;;
              *) echo "unexpected target path: $target_path" >&2; exit 1 ;;
            esac
          done
          git diff --check "$MAIN_SHA" "$TARGET_SHA"
          python -m pip install --disable-pip-version-check \
            jsonschema==4.25.1 PyYAML==6.0.2
          python -m unittest discover -s tests/release -p 'test_*.py'

      - name: Mint the production-scoped release App token
        id: app_token
        uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0
        with:
          app-id: ${{ secrets.GITOPS_RELEASE_APP_ID }}
          private-key: ${{ secrets.GITOPS_RELEASE_APP_PRIVATE_KEY }}
          owner: DevPathAi
          permission-administration: read
          permission-contents: write

      - name: Checkout current protected main with release App authority
        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0
        with:
          repository: DevPathAi/devpath-gitops
          ref: main
          token: ${{ steps.app_token.outputs.token }}
          fetch-depth: 0
          persist-credentials: true
          path: gitops-main

      - name: Authenticate authority and the target graph
        env:
          GH_TOKEN: ${{ steps.app_token.outputs.token }}
          APP_ID: ${{ secrets.GITOPS_RELEASE_APP_ID }}
          APP_SLUG: ${{ steps.app_token.outputs.app-slug }}
          INSTALLATION_ID: ${{ steps.app_token.outputs.installation-id }}
        run: |
          set -euo pipefail
          python target/scripts/release/verify_gitops_write_authority.py \
            --expected-app-id "$APP_ID" --app-slug "$APP_SLUG" \
            --installation-id "$INSTALLATION_ID"
          test "$(git -C target rev-parse HEAD)" = "$TARGET_SHA"
          test "$(git -C gitops-main rev-parse HEAD)" = "$MAIN_SHA"
          git -C gitops-main fetch --no-tags origin \
            "$TARGET_BRANCH:refs/remotes/origin/$TARGET_BRANCH"
          test "$(git -C gitops-main rev-parse "refs/remotes/origin/$TARGET_BRANCH")" = "$TARGET_SHA"
          test "$(git -C gitops-main rev-parse "$TARGET_SHA^")" = "$MAIN_SHA"
          test "$(git -C gitops-main rev-parse "$TARGET_SHA^{tree}")" = "$TARGET_TREE"

      - name: Fast-forward protected main to the exact tested S2a target
        env:
          GH_TOKEN: ${{ steps.app_token.outputs.token }}
          APP_ID: ${{ secrets.GITOPS_RELEASE_APP_ID }}
          APP_SLUG: ${{ steps.app_token.outputs.app-slug }}
          INSTALLATION_ID: ${{ steps.app_token.outputs.installation-id }}
        run: |
          set -euo pipefail
          python target/scripts/release/verify_gitops_write_authority.py \
            --expected-app-id "$APP_ID" --app-slug "$APP_SLUG" \
            --installation-id "$INSTALLATION_ID"
          git -C gitops-main fetch --no-tags origin main:refs/remotes/origin/main
          test "$(git -C gitops-main rev-parse origin/main)" = "$MAIN_SHA"
          git -C gitops-main push origin "$TARGET_SHA:refs/heads/main"
          git -C gitops-main fetch --no-tags origin main:refs/remotes/origin/main
          test "$(git -C gitops-main rev-parse origin/main)" = "$TARGET_SHA"

      - name: Re-authenticate the published main
        run: |
          set -euo pipefail
          git -C gitops-main fetch --no-tags origin main:refs/remotes/origin/main
          test "$(git -C gitops-main rev-parse origin/main)" = "$TARGET_SHA"
          test "$(git -C gitops-main rev-parse 'origin/main^{tree}')" = "$TARGET_TREE"
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
cd $HW && py -m unittest discover -s tests/release -p 'test_s2a_main_publish.py' 2>&1 | tail -4; cd /d/workspace/dpa
```

Expected: `Ran 13 tests` · `OK`.

- [ ] **Step 6: actionlint(CI 와 같은 v1.7.12)로 린트**

```bash
A=D:/workspace/dpa/.worktrees/_tools/actionlint; mkdir -p $A && cd $A
gh release download v1.7.12 -R rhysd/actionlint -p 'actionlint_1.7.12_windows_amd64.zip' -p 'actionlint_1.7.12_checksums.txt' --clobber
test "$(grep ' actionlint_1.7.12_windows_amd64.zip$' actionlint_1.7.12_checksums.txt | cut -d' ' -f1)" = "$(sha256sum actionlint_1.7.12_windows_amd64.zip | cut -d' ' -f1)" && echo CHECKSUM_OK
unzip -o -q actionlint_1.7.12_windows_amd64.zip actionlint.exe
./actionlint.exe -no-color -ignore 'unexpected key "queue" for "concurrency" section' $HW/.github/workflows/mission-spine-auth-smoke.yml; echo "lint_rc=$?"
cd /d/workspace/dpa
```

Expected: `CHECKSUM_OK`(체크섬 `6e7241b51e6817ea6a047693d8e6fed13b31819c9a0dd6c5a726e1592d22f6e9`) · 출력 없음 · `lint_rc=0`.

- [ ] **Step 7: 봇 신원으로 커밋하고 모양을 확인**

```bash
export GIT_AUTHOR_NAME='devpath-gitops-release[bot]' GIT_COMMITTER_NAME='devpath-gitops-release[bot]'
export GIT_AUTHOR_EMAIL='244265210+devpath-gitops-release[bot]@users.noreply.github.com'
export GIT_COMMITTER_EMAIL='244265210+devpath-gitops-release[bot]@users.noreply.github.com'
git -C $HW add .github/workflows/mission-spine-auth-smoke.yml tests/release/test_s2a_main_publish.py
git -C $HW commit -q -m "chore(release): publish the S2a mobile-free release contract to main"
git -C $HW rev-parse HEAD^                                  # 4f3ed64b…
git -C $HW diff-tree --no-commit-id --name-only -r HEAD     # 정확히 두 줄, 이 순서
git -C $HW show -s --format='%an|%ae|%cn|%ce' HEAD
git -C $HW status --porcelain | grep -v '^??' ; echo "dirty_rc=$?"
```

Expected: 부모 = `MAIN_SHA` · 경로 `.github/workflows/mission-spine-auth-smoke.yml`, `tests/release/test_s2a_main_publish.py` · 봇 신원 네 칸 · `dirty_rc=1`.
(publisher 가 `helper_paths[0]`·`[1]` 을 이 순서로 단언한다 — `diff-tree` 는 경로를 바이트 순으로 낸다.)

- [ ] **Step 8: push, 실행이 생기지 않았는지 확인**

```bash
git -C $HW push -u origin chore/s2a-mobile-free-contract-publish-20260920
gh run list -R DevPathAi/devpath-gitops --branch chore/s2a-mobile-free-contract-publish-20260920 --limit 3
```

Expected: 실행 0건(`workflow_dispatch` 전용이고 아직 아무도 띄우지 않았다).

### Task 3: 디스패처를 staged 이름으로만 push

**Files:**
- Create: `D:/workspace/dpa/.worktrees/gitops-s2a-publish-dispatcher/.github/workflows/mission-spine-release-gate-dispatch.yml`

**Interfaces:**
- Consumes: Task 2 의 헬퍼 브랜치 이름(디스패치 `ref`).
- Produces: 원격 브랜치 `chore/s2a-main-publish-dispatcher-staged-20260920` 과 그 head SHA(= `STAGED_SHA`). Part B 가 이 SHA 를 `automation/dispatch-s2a-main-publish` 로 push 한다 — **Part A 에서는 그 이름으로 push 하지 않는다.**

- [ ] **Step 1: worktree 를 main 에서 만든다**

```bash
export MSYS_NO_PATHCONV=1
G=D:/workspace/dpa/devpath-gitops; XW=D:/workspace/dpa/.worktrees/gitops-s2a-publish-dispatcher
git -C $G worktree add -b chore/s2a-main-publish-dispatcher-staged-20260920 $XW 4f3ed64b2a148394eb0b8b3f5311e327f0edd759
test ! -e $XW/.github/workflows/mission-spine-release-gate-dispatch.yml && echo "new file, as expected"
```

- [ ] **Step 2: Write 도구로 디스패처를 만든다**

`$XW/.github/workflows/mission-spine-release-gate-dispatch.yml`:

```yaml
---
# Dispatch nonce: S2a main publisher attempt 1.
name: Mission Spine Release Gate Dispatch

'on':
  push:
    branches:
      - automation/dispatch-s2a-main-publish

permissions:
  actions: write
  contents: read

jobs:
  dispatch:
    name: Dispatch protected release gate
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - name: Dispatch the S2a main publisher as GitHub Actions automation
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh api \
            --method POST \
            "repos/${GITHUB_REPOSITORY}/actions/workflows/mission-spine-auth-smoke.yml/dispatches" \
            --input - <<'JSON'
          {
            "ref": "chore/s2a-mobile-free-contract-publish-20260920",
            "inputs": {
              "full": "true"
            }
          }
          JSON
```

- [ ] **Step 3: 선례와의 차이가 의도한 세 곳뿐인지 확인, 린트**

```bash
git -C $G show origin/automation/dispatch-ms-20260916-community-ia:.github/workflows/mission-spine-release-gate-dispatch.yml > D:/workspace/dpa/.worktrees/_tools/dispatch-precedent.yml
diff D:/workspace/dpa/.worktrees/_tools/dispatch-precedent.yml $XW/.github/workflows/mission-spine-release-gate-dispatch.yml
D:/workspace/dpa/.worktrees/_tools/actionlint/actionlint.exe -no-color $XW/.github/workflows/mission-spine-release-gate-dispatch.yml; echo "lint_rc=$?"
```

Expected: diff 는 (1) nonce 주석 (2) `branches:` 값 (3) step 이름·대상 워크플로 파일명·JSON 본문(`ref`·`inputs`)뿐. `permissions`·`runs-on`·`timeout-minutes`·`GH_TOKEN` 은 같다. `lint_rc=0`.

- [ ] **Step 4: 봇 신원으로 커밋, staged 이름으로 push**

```bash
export GIT_AUTHOR_NAME='devpath-gitops-release[bot]' GIT_COMMITTER_NAME='devpath-gitops-release[bot]'
export GIT_AUTHOR_EMAIL='244265210+devpath-gitops-release[bot]@users.noreply.github.com'
export GIT_COMMITTER_EMAIL='244265210+devpath-gitops-release[bot]@users.noreply.github.com'
git -C $XW add .github/workflows/mission-spine-release-gate-dispatch.yml
git -C $XW commit -q -m "ci: dispatch the S2a main publisher as GitHub Actions automation"
git -C $XW diff-tree --no-commit-id --name-status -r HEAD    # A  .github/workflows/mission-spine-release-gate-dispatch.yml 한 줄
git -C $XW push -u origin chore/s2a-main-publish-dispatcher-staged-20260920
git -C $XW rev-parse HEAD    # ← STAGED_SHA. Task 6 보고와 Part B 에 쓴다
```

- [ ] **Step 5: 방아쇠가 당겨지지 않았는지 확인**

```bash
gh run list -R DevPathAi/devpath-gitops --limit 5 --json workflowName,headBranch,createdAt -q '.[] | [.createdAt,.workflowName,.headBranch] | @tsv'
gh api repos/DevPathAi/devpath-gitops/git/matching-refs/heads/automation/dispatch-s2a-main-publish -q length   # 0
```

Expected: 방금 시각의 `Mission Spine Release Gate Dispatch` 실행이 **없다**. `automation/dispatch-s2a-main-publish` ref 는 0개.
push 직후에는 아직 안 보일 수 있으므로 **Task 4 Step 5 의 preflight 가 같은 것을 다시 본다**(진행·대기 실행 0, 방아쇠 ref 0). 실행이 생겼다면 즉시 `gh run cancel` 하고 멈춰 보고(`on.push.branches` 가 staged 이름과 일치할 수 없으므로 일어나서는 안 된다).

### Task 4: 실행 트랜잭션 스크립트 — 가짜 API 테스트 먼저

**Files:**
- Create: `D:/workspace/dpa/.worktrees/docs-s2a-publish-runner/docs/superpowers/plans/2026-09-20-gitops-main-promotion-via-publisher/test_run_s2a_main_publish.py`
- Create: `…/2026-09-20-gitops-main-promotion-via-publisher/run_s2a_main_publish.py`

**Interfaces:**
- Consumes: Task 1~3 의 브랜치, Task 0 의 "실행 0" 상태.
- Produces: `publish(ops, repo_dir, staged_sha, comment) -> {"run_id", "deployment_ids", "main"}` · CLI `--repo-dir --staged-sha --comment [--preflight-only]` ·
  예외 `PublishError`(복원 확인됨) / `RestoreError`(복원 미확인 — 아무것도 승인되지 않음).

- [ ] **Step 1: Write 도구로 실패할 테스트를 만든다**

```python
import unittest
from typing import Any
from unittest import mock

import run_s2a_main_publish as runner
from run_s2a_main_publish import Ops, PublishError, RestoreError

HELPER_SHA = "a" * 40
STAGED_SHA = "b" * 40
ENV_ID = 9001
MAIN_POLICY_ID = 57524487
HELPER_POLICY_ID = 60000001
RUN_ID = 777


class FakeGitHub:
    """A scripted GitHub that records every call in order."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.main = runner.MAIN_SHA
        self.policies = [{"id": MAIN_POLICY_ID, "name": "main", "type": "branch"}]
        self.prevent_self_review = True
        self.runs: list[dict[str, Any]] = []
        self.busy = 0
        self.now = 0.0
        self.dispatch_appears = True
        self.push_fails = False
        self.delete_is_ignored = False
        self.delete_is_interrupted = False
        self.can_approve = True
        self.approval_body: Any = [{"id": 4242}]
        self.ci_conclusion = "success"

    # -- Ops ---------------------------------------------------------------
    def ops(self) -> Ops:
        return Ops(
            api=self.api, run=self.run, sleep=self.sleep, clock=lambda: self.now,
            http_status=lambda url: 200,
        )

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def run(self, command: list[str]) -> str:
        self.calls.append("RUN " + " ".join(command[:5]))
        if command[3:4] == ["push"]:
            if self.push_fails:
                raise PublishError("push failed")
            allowed = any(policy["name"] == runner.HELPER_BRANCH for policy in self.policies)
            if self.dispatch_appears:
                self.runs.append(
                    {
                        "id": RUN_ID,
                        "head_sha": HELPER_SHA,
                        "actor": {"login": runner.BOT},
                        "run_attempt": 1,
                        "status": "waiting" if allowed else "completed",
                    }
                )
        if command[:3] == ["gh", "run", "watch"]:
            self.main = runner.TARGET_SHA
        return ""

    def api(self, method: str, path: str, payload: dict[str, Any] | None) -> Any:
        self.calls.append(f"{method} {path.split('?')[0]}")
        repo = f"repos/{runner.REPO}"
        if path == "user":
            return {"login": runner.REVIEWER}
        if path == f"{repo}/branches/main":
            return {"commit": {"sha": self.main}}
        if path == f"{repo}/branches/{runner.TARGET_BRANCH}":
            return {"commit": {"sha": runner.TARGET_SHA}}
        if path == f"{repo}/branches/{runner.STAGED_BRANCH}":
            return {"commit": {"sha": STAGED_SHA}}
        if path == f"{repo}/branches/{runner.HELPER_BRANCH}":
            return {"commit": {"sha": HELPER_SHA, "parents": [{"sha": runner.MAIN_SHA}]}}
        if path.startswith(f"{repo}/git/matching-refs/"):
            return []
        if path.startswith(f"{repo}/actions/runs?status="):
            return {"total_count": self.busy}
        if path == runner.HELPER_RUNS_PATH:
            return {"workflow_runs": list(self.runs)}
        if path == runner.ENV_PATH:
            return {
                "id": ENV_ID,
                "name": runner.ENVIRONMENT,
                "can_admins_bypass": False,
                "deployment_branch_policy": {
                    "protected_branches": False,
                    "custom_branch_policies": True,
                },
                "protection_rules": [
                    {
                        "type": "required_reviewers",
                        "prevent_self_review": self.prevent_self_review,
                        "reviewers": [{"type": "User", "reviewer": {"login": runner.REVIEWER}}],
                    },
                    {"type": "branch_policy"},
                ],
            }
        if path == f"{runner.POLICIES_PATH}?per_page=100":
            return {"total_count": len(self.policies), "branch_policies": list(self.policies)}
        if method == "POST" and path == runner.POLICIES_PATH:
            assert payload == {"name": runner.HELPER_BRANCH, "type": "branch"}
            self.policies.append({"id": HELPER_POLICY_ID, **payload})
            return {"id": HELPER_POLICY_ID, **payload}
        if method == "DELETE" and path.startswith(runner.POLICIES_PATH + "/"):
            policy_id = int(path.rsplit("/", 1)[1])
            assert policy_id != MAIN_POLICY_ID, "the main policy must never be deleted"
            if self.delete_is_interrupted:
                raise KeyboardInterrupt
            if not self.delete_is_ignored:
                self.policies = [row for row in self.policies if row["id"] != policy_id]
            return None
        if path == f"{repo}/actions/runs/{RUN_ID}/pending_deployments":
            if method == "GET":
                return [
                    {
                        "environment": {"id": ENV_ID, "name": runner.ENVIRONMENT},
                        "current_user_can_approve": self.can_approve,
                    }
                ]
            assert payload == {
                "environment_ids": [ENV_ID],
                "state": "approved",
                "comment": "go",
            }
            return self.approval_body
        if path == f"{repo}/git/commits/{runner.TARGET_SHA}":
            return {"tree": {"sha": runner.TARGET_TREE}}
        if path == f"{repo}/rulesets":
            return [
                {"id": key, "name": name, "enforcement": "active"}
                for key, name in runner.RULESETS.items()
            ]
        if path == f"{repo}/branches/main/protection":
            return {"enforce_admins": {"enabled": True}}
        if path.startswith(f"{repo}/actions/workflows/ci.yml/runs"):
            return {"workflow_runs": [{"status": "completed", "conclusion": self.ci_conclusion}]}
        raise AssertionError(f"unscripted call: {method} {path}")

    # -- helpers -----------------------------------------------------------
    def index(self, needle: str) -> int:
        return next(i for i, call in enumerate(self.calls) if needle in call)

    def approved(self) -> bool:
        return any(call.startswith("POST") and "pending_deployments" in call for call in self.calls)

    def policy_opened(self) -> bool:
        return f"POST {runner.POLICIES_PATH}" in self.calls


class PublishTransactionTest(unittest.TestCase):
    def test_happy_path_restores_before_it_approves(self) -> None:
        github = FakeGitHub()
        result = runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertEqual(
            {"run_id": RUN_ID, "deployment_ids": [4242], "main": runner.TARGET_SHA}, result
        )
        opened = github.index(f"POST {runner.POLICIES_PATH}")
        pushed = github.index("RUN git -C D:/repo push origin")
        deleted = github.index(f"DELETE {runner.POLICIES_PATH}/{HELPER_POLICY_ID}")
        approved = github.index(f"POST repos/{runner.REPO}/actions/runs/{RUN_ID}/pending")
        self.assertLess(opened, pushed)
        self.assertLess(pushed, deleted)
        self.assertLess(deleted, approved)
        self.assertEqual([{"id": MAIN_POLICY_ID, "name": "main", "type": "branch"}], github.policies)

    def test_preflight_refuses_a_moved_main_before_any_write(self) -> None:
        github = FakeGitHub()
        github.main = "c" * 40
        with self.assertRaisesRegex(PublishError, "main moved"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertFalse(github.policy_opened())
        self.assertFalse(github.approved())

    def test_preflight_refuses_a_busy_repository_before_any_write(self) -> None:
        github = FakeGitHub()
        github.busy = 1
        with self.assertRaisesRegex(PublishError, "workflow runs"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertFalse(github.policy_opened())

    def test_preflight_refuses_a_relaxed_self_review_rule(self) -> None:
        github = FakeGitHub()
        github.prevent_self_review = False
        with self.assertRaisesRegex(PublishError, "prevent_self_review"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertFalse(github.policy_opened())

    def test_a_run_that_never_waits_is_restored_and_not_approved(self) -> None:
        github = FakeGitHub()
        github.dispatch_appears = False
        with self.assertRaisesRegex(PublishError, "never reached waiting"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertEqual(["main"], [row["name"] for row in github.policies])
        self.assertFalse(github.approved())
        self.assertGreaterEqual(github.now, 300.0)

    def test_a_failed_dispatch_push_is_restored_and_not_approved(self) -> None:
        github = FakeGitHub()
        github.push_fails = True
        with self.assertRaisesRegex(PublishError, "push failed"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertEqual(["main"], [row["name"] for row in github.policies])
        self.assertFalse(github.approved())

    def test_an_unverified_restore_blocks_the_approval(self) -> None:
        github = FakeGitHub()
        github.delete_is_ignored = True
        with self.assertRaises(RestoreError):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertFalse(github.approved())

    def test_an_unapprovable_deployment_is_not_approved(self) -> None:
        github = FakeGitHub()
        github.can_approve = False
        with self.assertRaisesRegex(PublishError, "cannot approve"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertEqual(["main"], [row["name"] for row in github.policies])
        self.assertFalse(github.approved())

    def test_a_red_main_ci_fails_the_post_verification(self) -> None:
        github = FakeGitHub()
        github.ci_conclusion = "failure"
        with self.assertRaisesRegex(PublishError, "main CI failed"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertTrue(github.approved())

    def test_an_interrupt_during_the_restore_is_a_restore_error(self) -> None:
        github = FakeGitHub()
        github.delete_is_interrupted = True
        with self.assertRaises(RestoreError):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertFalse(github.approved())

    def test_an_empty_approval_response_is_a_publish_error(self) -> None:
        github = FakeGitHub()
        github.approval_body = None
        with self.assertRaisesRegex(PublishError, "approval response is not exact"):
            runner.publish(github.ops(), "D:/repo", STAGED_SHA, "go")
        self.assertEqual(["main"], [row["name"] for row in github.policies])

    def test_post_verify_without_a_snapshot_still_requires_the_sealed_shape(self) -> None:
        github = FakeGitHub()
        github.main = runner.TARGET_SHA
        runner.post_verify(github.ops(), None)
        github.prevent_self_review = False
        with self.assertRaisesRegex(PublishError, "prevent_self_review"):
            runner.post_verify(github.ops(), None)

    def test_site_probe_identifies_itself(self) -> None:
        # Cloudflare answers 403 to the default "Python-urllib" agent on leva.ai.kr (live, 2026-09-20).
        seen: list[Any] = []

        class _Response:
            status = 200

            def __enter__(self) -> "_Response":
                return self

            def __exit__(self, *exc: Any) -> None:
                return None

        def fake_urlopen(request: Any, timeout: float) -> _Response:
            seen.append(request)
            return _Response()

        with mock.patch.object(runner.urllib.request, "urlopen", fake_urlopen):
            self.assertEqual(200, runner._http_status("https://leva.ai.kr"))
        self.assertEqual("https://leva.ai.kr", seen[0].full_url)
        agent = seen[0].get_header("User-agent")
        self.assertTrue(agent and "urllib" not in agent.lower(), agent)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

```bash
P=D:/workspace/dpa/.worktrees/docs-s2a-publish-runner/docs/superpowers/plans/2026-09-20-gitops-main-promotion-via-publisher
cd $P && py -m unittest test_run_s2a_main_publish 2>&1 | tail -3; cd /d/workspace/dpa
```

Expected: `ModuleNotFoundError: No module named 'run_s2a_main_publish'`.

- [ ] **Step 3: Write 도구로 스크립트를 만든다**

```python
#!/usr/bin/env python3
"""Operator transaction for the one-shot S2a main publisher.

Opens the helper branch on the protected environment, bot-dispatches the
publisher, restores the exact main-only branch policy no matter what happened,
and only after the restore is verified approves the pending deployment.
It never touches ``prevent_self_review``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

REPO = "DevPathAi/devpath-gitops"
ENVIRONMENT = "mission-spine-production-off"
REVIEWER = "VelkaressiaBlutkrone"
BOT = "github-actions[bot]"
MAIN_SHA = "4f3ed64b2a148394eb0b8b3f5311e327f0edd759"
TARGET_SHA = "69e7bd15570f5ba0f271c83b5bd46955cb249c8e"
TARGET_TREE = "7799cc07f3083a002d0e2064db5437e2cde46f84"
HELPER_BRANCH = "chore/s2a-mobile-free-contract-publish-20260920"
TARGET_BRANCH = "fix/s2a-mobile-free-contract-main-20260920"
STAGED_BRANCH = "chore/s2a-main-publish-dispatcher-staged-20260920"
DISPATCH_BRANCH = "automation/dispatch-s2a-main-publish"
WORKFLOW_FILE = "mission-spine-auth-smoke.yml"
RULESETS = {
    21194269: "mission-spine-main-integrity",
    21194270: "mission-spine-main-governance",
}
BUSY_STATUSES = ("in_progress", "queued", "waiting", "requested", "pending")
SITES = ("https://app.leva.ai.kr", "https://leva.ai.kr")
ENV_PATH = f"repos/{REPO}/environments/{ENVIRONMENT}"
POLICIES_PATH = f"{ENV_PATH}/deployment-branch-policies"
HELPER_RUNS_PATH = (
    f"repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/runs"
    f"?branch={HELPER_BRANCH}&event=workflow_dispatch&per_page=20"
)


class PublishError(RuntimeError):
    """The transaction stopped; main-only policy was restored and verified."""


class RestoreError(PublishError):
    """The main-only policy could NOT be verified. Nothing was approved."""


@dataclass
class Ops:
    api: Callable[[str, str, dict[str, Any] | None], Any]
    run: Callable[[list[str]], str]
    sleep: Callable[[float], None]
    clock: Callable[[], float]
    http_status: Callable[[str], int]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PublishError(message)


def _branch_sha(ops: Ops, branch: str) -> str:
    return ops.api("GET", f"repos/{REPO}/branches/{branch}", None)["commit"]["sha"]


def _policies(ops: Ops) -> list[tuple[int, str, str]]:
    payload = ops.api("GET", f"{POLICIES_PATH}?per_page=100", None)
    rows = [(row["id"], row["name"], row["type"]) for row in payload["branch_policies"]]
    _require(payload["total_count"] == len(rows), "branch policy listing is truncated")
    return sorted(rows)


def snapshot_environment(ops: Ops) -> dict[str, Any]:
    """Return the sealed shape of the environment, or refuse to continue."""
    environment = ops.api("GET", ENV_PATH, None)
    _require(environment["name"] == ENVIRONMENT, "environment identity mismatch")
    _require(environment["can_admins_bypass"] is False, "administrators may bypass")
    _require(
        environment["deployment_branch_policy"]
        == {"protected_branches": False, "custom_branch_policies": True},
        "environment does not use an exact custom branch policy",
    )
    reviewer_rules = [
        rule for rule in environment["protection_rules"] if rule["type"] == "required_reviewers"
    ]
    _require(len(reviewer_rules) == 1, "exactly one required-reviewers rule is required")
    rule = reviewer_rules[0]
    _require(rule["prevent_self_review"] is True, "prevent_self_review is not true")
    reviewers = [(entry["type"], entry["reviewer"]["login"]) for entry in rule["reviewers"]]
    _require(reviewers == [("User", REVIEWER)], "configured reviewer is not exact")
    policies = _policies(ops)
    _require(
        [(name, kind) for _, name, kind in policies] == [("main", "branch")],
        "environment branch policy is not exactly main",
    )
    return {"environment_id": environment["id"], "policies": policies}


def preflight(ops: Ops, repo_dir: str, staged_sha: str) -> dict[str, Any]:
    _require(ops.api("GET", "user", None)["login"] == REVIEWER, "gh is not the reviewer")
    _require(_branch_sha(ops, "main") == MAIN_SHA, "main moved away from MAIN_SHA")
    _require(_branch_sha(ops, TARGET_BRANCH) == TARGET_SHA, "target branch moved")
    _require(_branch_sha(ops, STAGED_BRANCH) == staged_sha, "staged dispatcher moved")
    helper = ops.api("GET", f"repos/{REPO}/branches/{HELPER_BRANCH}", None)["commit"]
    _require(
        [parent["sha"] for parent in helper["parents"]] == [MAIN_SHA],
        "helper is not exactly one commit on MAIN_SHA",
    )
    _require(
        ops.api("GET", f"repos/{REPO}/git/matching-refs/heads/{DISPATCH_BRANCH}", None) == [],
        "dispatcher branch already exists",
    )
    for status in BUSY_STATUSES:
        busy = ops.api("GET", f"repos/{REPO}/actions/runs?status={status}&per_page=1", None)
        _require(busy["total_count"] == 0, f"repository has {status} workflow runs")
    known_runs = {run["id"] for run in ops.api("GET", HELPER_RUNS_PATH, None)["workflow_runs"]}
    ops.run(["git", "-C", repo_dir, "fetch", "--no-tags", "origin", STAGED_BRANCH])
    ops.run(["git", "-C", repo_dir, "cat-file", "-e", f"{staged_sha}^{{commit}}"])
    return {
        "snapshot": snapshot_environment(ops),
        "helper_sha": helper["sha"],
        "known_runs": known_runs,
    }


def _waiting_run(ops: Ops, helper_sha: str, known_runs: set[int]) -> int | None:
    runs = [
        run
        for run in ops.api("GET", HELPER_RUNS_PATH, None)["workflow_runs"]
        if run["id"] not in known_runs
    ]
    _require(len(runs) <= 1, "more than one publisher run appeared")
    if not runs:
        return None
    run = runs[0]
    _require(run["head_sha"] == helper_sha, "publisher run is not on the helper commit")
    _require(run["actor"]["login"] == BOT, "publisher run was not bot-dispatched")
    _require(run["run_attempt"] == 1, "publisher run is not attempt one")
    _require(run["status"] != "completed", "publisher run finished without waiting")
    return run["id"] if run["status"] == "waiting" else None


def restore(ops: Ops, snapshot: dict[str, Any]) -> None:
    """Delete only the helper policy, then prove the sealed shape is back."""
    for policy_id, name, _ in _policies(ops):
        if name == HELPER_BRANCH:
            ops.api("DELETE", f"{POLICIES_PATH}/{policy_id}", None)
    if snapshot_environment(ops) != snapshot:
        raise PublishError("environment differs from the snapshot")


def open_dispatch_restore(
    ops: Ops,
    repo_dir: str,
    staged_sha: str,
    state: dict[str, Any],
    *,
    wait_seconds: float = 300.0,
    poll_seconds: float = 5.0,
) -> int:
    failure: BaseException | None = None
    run_id: int | None = None
    try:
        ops.api("POST", POLICIES_PATH, {"name": HELPER_BRANCH, "type": "branch"})
        ops.run(
            ["git", "-C", repo_dir, "push", "origin", f"{staged_sha}:refs/heads/{DISPATCH_BRANCH}"]
        )
        deadline = ops.clock() + wait_seconds
        while run_id is None:
            run_id = _waiting_run(ops, state["helper_sha"], state["known_runs"])
            if run_id is None:
                _require(ops.clock() < deadline, "publisher run never reached waiting")
                ops.sleep(poll_seconds)
    except BaseException as exc:  # noqa: BLE001 - the policy must be restored regardless
        failure = exc
    try:
        restore(ops, state["snapshot"])
    except BaseException as exc:  # noqa: BLE001 - an interrupted restore is an unverified restore
        raise RestoreError(
            "main-only policy NOT verified - restore it by hand before anything else"
        ) from (failure or exc)
    if failure is not None:
        raise failure
    assert run_id is not None
    return run_id


def approve(ops: Ops, run_id: int, environment_id: int, comment: str) -> list[int]:
    path = f"repos/{REPO}/actions/runs/{run_id}/pending_deployments"
    pending = ops.api("GET", path, None)
    _require(len(pending) == 1, "exactly one pending deployment is required")
    _require(pending[0]["environment"]["id"] == environment_id, "pending environment mismatch")
    _require(pending[0]["environment"]["name"] == ENVIRONMENT, "pending environment mismatch")
    _require(pending[0]["current_user_can_approve"] is True, "current user cannot approve")
    approved = ops.api(
        "POST",
        path,
        {"environment_ids": [environment_id], "state": "approved", "comment": comment},
    )
    _require(
        isinstance(approved, list) and len(approved) == 1, "approval response is not exact"
    )
    return [item["id"] for item in approved]


def post_verify(
    ops: Ops, snapshot: dict[str, Any] | None, *, ci_wait_seconds: float = 900.0
) -> None:
    """Verify the published state. ``snapshot=None`` (``--post-verify-only``) still requires the
    sealed environment shape, but cannot compare it with a pre-publish snapshot."""
    _require(_branch_sha(ops, "main") == TARGET_SHA, "main is not TARGET_SHA")
    commit = ops.api("GET", f"repos/{REPO}/git/commits/{TARGET_SHA}", None)
    _require(commit["tree"]["sha"] == TARGET_TREE, "published tree is not TARGET_TREE")
    rulesets = {
        row["id"]: (row["name"], row["enforcement"])
        for row in ops.api("GET", f"repos/{REPO}/rulesets", None)
    }
    _require(
        rulesets == {key: (name, "active") for key, name in RULESETS.items()},
        "rulesets changed",
    )
    protection = ops.api("GET", f"repos/{REPO}/branches/main/protection", None)
    _require(protection["enforce_admins"]["enabled"] is True, "enforce_admins is off")
    observed = snapshot_environment(ops)
    _require(snapshot is None or observed == snapshot, "environment differs from the snapshot")
    deadline = ops.clock() + ci_wait_seconds
    ci_path = f"repos/{REPO}/actions/workflows/ci.yml/runs?head_sha={TARGET_SHA}&event=push"
    while True:
        runs = ops.api("GET", ci_path, None)["workflow_runs"]
        if runs and runs[0]["status"] == "completed":
            _require(runs[0]["conclusion"] == "success", "main CI failed on TARGET_SHA")
            break
        _require(ops.clock() < deadline, "main CI did not finish in time")
        ops.sleep(15.0)
    for site in SITES:
        _require(ops.http_status(site) == 200, f"{site} is not 200")


def publish(ops: Ops, repo_dir: str, staged_sha: str, comment: str) -> dict[str, Any]:
    state = preflight(ops, repo_dir, staged_sha)
    run_id = open_dispatch_restore(ops, repo_dir, staged_sha, state)
    deployment_ids = approve(ops, run_id, state["snapshot"]["environment_id"], comment)
    ops.run(["gh", "run", "watch", str(run_id), "-R", REPO, "--interval", "15", "--exit-status"])
    post_verify(ops, state["snapshot"])
    return {"run_id": run_id, "deployment_ids": deployment_ids, "main": TARGET_SHA}


def _gh_api(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    command = ["gh", "api", "-H", "X-GitHub-Api-Version: 2026-03-10", "-X", method, path]
    if payload is not None:
        command += ["--input", "-"]
    done = subprocess.run(
        command,
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    if done.returncode != 0:
        raise PublishError(f"GitHub API {method} {path} failed: {done.stderr.strip()[:300]}")
    return json.loads(done.stdout) if done.stdout.strip() else None


def _run(command: list[str]) -> str:
    done = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
    if done.returncode != 0:
        raise PublishError(f"{' '.join(command[:4])} failed: {done.stderr.strip()[:300]}")
    return done.stdout


def _http_status(url: str) -> int:
    # Cloudflare answers 403 to the default "Python-urllib" agent on leva.ai.kr, so identify ourselves.
    request = urllib.request.Request(url, headers={"User-Agent": "devpath-release-postverify/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 - fixed https URLs
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", required=True, help="absolute path of a devpath-gitops clone")
    parser.add_argument("--staged-sha", required=True, help="head of the staged dispatcher branch")
    parser.add_argument("--comment", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--post-verify-only", action="store_true")
    args = parser.parse_args()
    ops = Ops(api=_gh_api, run=_run, sleep=time.sleep, clock=time.monotonic, http_status=_http_status)
    if args.preflight_only:
        state = preflight(ops, args.repo_dir, args.staged_sha)
        print(json.dumps({"preflight": "ok", "helper_sha": state["helper_sha"]}))
        return 0
    if args.post_verify_only:
        post_verify(ops, None)
        print(json.dumps({"post_verify": "ok", "main": TARGET_SHA}))
        return 0
    print(json.dumps(publish(ops, args.repo_dir, args.staged_sha, args.comment), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

스펙 §4.4 는 "기록한 id 로 DELETE"라 했다. 구현은 **이름이 헬퍼 브랜치인 정책만** 지운다 — POST 응답을 잃어 id 를 모르는 경우에도 복원되고,
`main` 정책은 이름이 달라 절대 지워지지 않는다(테스트의 가짜 GitHub 가 main 정책 DELETE 를 `assert` 로 막는다).

- [ ] **Step 4: 통과 확인**

```bash
cd $P && py -m unittest test_run_s2a_main_publish 2>&1 | tail -4; cd /d/workspace/dpa
```

Expected: `Ran 13 tests` · `OK`.

- [ ] **Step 5: live 읽기 전용 preflight(쓰기 없음)**

```bash
STAGED_SHA=$(gh api repos/DevPathAi/devpath-gitops/branches/chore/s2a-main-publish-dispatcher-staged-20260920 -q .commit.sha)
py $P/run_s2a_main_publish.py --repo-dir D:/workspace/dpa/devpath-gitops --staged-sha $STAGED_SHA --comment unused --preflight-only
```

Expected: `{"preflight": "ok", "helper_sha": "<Task 2 의 헬퍼 head>"}`. `--preflight-only` 는 GET 과 `git fetch`·`cat-file` 만 한다.

- [ ] **Step 6: documents 에 커밋·PR·머지**

```bash
DW=D:/workspace/dpa/.worktrees/docs-s2a-publish-runner
git -C $DW add docs/superpowers/plans/2026-09-20-gitops-main-promotion-via-publisher/
git -C $DW commit -q -m "chore(plan): S2a main publisher 의 target 생성·실행 트랜잭션 스크립트와 테스트"
git -C $DW push -u origin chore/s2a-main-publish-runner
gh pr create -R DevPathAi/documents --base develop --head chore/s2a-main-publish-runner \
  --title "chore(plan): S2a main publisher 실행 스크립트와 테스트" \
  --body "계획 docs/superpowers/plans/2026-09-20-gitops-main-promotion-via-publisher.md Task 1·4 의 산출물. 가짜 API 테스트 9건. 운영에 쓰지 않는다."
```

커밋 메시지 끝에는 세션의 attribution 줄을, PR 본문 끝에는 Generated-with 줄을 붙인다. CI(`privacy-producer-contract`) 녹색을 `gh pr checks` 로 확인한 뒤
`gh pr merge <번호> -R DevPathAi/documents --merge`. **Task 5 의 리뷰가 스크립트를 고치게 하면 같은 방식으로 후속 PR 을 낸다.**

### Task 5: 독립 리뷰 (새 컨텍스트)

**Files:** 없음(읽기 전용). 지적이 코드 수정으로 이어지면 Task 2·3·4 의 해당 Step 을 다시 밟는다.

**Interfaces:**
- Consumes: 헬퍼·디스패처·실행 스크립트(전부 원격에 있다).
- Produces: 지적 목록과, 컨트롤러가 각 지적을 코드에서 재확인한 결과.

- [ ] **Step 1: 리뷰 입력을 파일로 만든다**

```bash
export MSYS_NO_PATHCONV=1
G=D:/workspace/dpa/devpath-gitops; RV=D:/workspace/dpa/.worktrees/_review-s2a-publish; mkdir -p $RV
git -C $G fetch origin --quiet
git -C $G show origin/chore/prod27r4-cloudflare-pagination-publish-20260912:.github/workflows/mission-spine-auth-smoke.yml > $RV/precedent-publisher.yml
git -C $G show origin/chore/s2a-mobile-free-contract-publish-20260920:.github/workflows/mission-spine-auth-smoke.yml > $RV/new-publisher.yml
git -C $G show origin/chore/s2a-mobile-free-contract-publish-20260920:tests/release/test_s2a_main_publish.py > $RV/test_s2a_main_publish.py
git -C $G show origin/chore/s2a-main-publish-dispatcher-staged-20260920:.github/workflows/mission-spine-release-gate-dispatch.yml > $RV/new-dispatcher.yml
git -C $G show origin/automation/dispatch-ms-20260916-community-ia:.github/workflows/mission-spine-release-gate-dispatch.yml > $RV/precedent-dispatcher.yml
git -C $G show origin/main:scripts/release/verify_gitops_write_authority.py > $RV/verify_gitops_write_authority.py
D=D:/workspace/dpa/documents; git -C $D fetch origin --quiet
for f in run_s2a_main_publish.py test_run_s2a_main_publish.py; do
  git -C $D show origin/develop:docs/superpowers/plans/2026-09-20-gitops-main-promotion-via-publisher/$f > $RV/$f
done
git -C $D show origin/develop:docs/superpowers/specs/2026-09-20-gitops-main-promotion-via-publisher-design.md > $RV/spec.md
diff -u $RV/precedent-publisher.yml $RV/new-publisher.yml > $RV/publisher.diff; ls -la $RV
```

- [ ] **Step 2: 프로브 — 이 PC 의 서브에이전트가 응답을 내는지 실측**

Agent 도구(`subagent_type: general-purpose`)에 다음을 준다:

```
이 작업만 수행하라. 끝나면 보고하고 정지하라. 다른 작업으로 진행하지 말라.
D:/workspace/dpa/.worktrees/_review-s2a-publish/new-dispatcher.yml 을 Read 도구로 읽고,
(1) 이 워크플로가 반응하는 브랜치 이름 (2) 디스패치하는 워크플로 파일명 (3) 디스패치 ref 를 세 줄로 답하라.
파일을 수정하지 말라. 모든 경로는 절대경로로 다뤄라.
```

Expected: `automation/dispatch-s2a-main-publish` / `mission-spine-auth-smoke.yml` / `chore/s2a-mobile-free-contract-publish-20260920`.
**빈 응답이면** Step 3 을 Agent 도구 대신 헤드리스 프로세스로 돌린다: 프롬프트를 Write 도구로 `$RV/review-prompt.txt` 에 쓰고
`claude -p "$(cat $RV/review-prompt.txt)" --allowedTools "Read,Grep,Glob" > $RV/review-output.md 2>&1; echo "CLAUDE_EXIT=$?"`.
그것도 비면 **멈추고 사용자에게 보고한다 — 리뷰 없이 Task 6 으로 가지 않는다**(스펙 §6).

- [ ] **Step 3: 본 리뷰를 맡긴다**

Agent 도구(`subagent_type: oh-my-claudecode:security-reviewer` — Write·Edit 없는 읽기 전용 에이전트)에 다음을 준다:

```
이 작업(publisher 적대적 리뷰)만 수행하라. 끝나면 보고하고 정지하라. 다른 작업으로 진행하지 말라.
명세에 없는 코드를 추측·즉흥 구현하지 말라. 파일을 수정·생성하지 말라. git 명령으로 어떤 레포의 상태도 바꾸지 말라.
정보가 부족하면 멈추고 NEEDS_CONTEXT 로 보고하라. 모든 경로는 절대경로로 다뤄라.

배경: GitHub 레포 DevPathAi/devpath-gitops 의 main 은 봉인돼 있다(룰셋 2종 + 보호 환경). 릴리스 GitHub App 만이 main 에 쓸 수 있다.
"one-shot publisher" 는 헬퍼 브랜치의 워크플로가 보호 환경 승인 뒤 App 토큰으로 정확히 하나의 커밋을 main 에 fast-forward 하는 장치다.
읽을 파일은 전부 D:/workspace/dpa/.worktrees/_review-s2a-publish/ 아래에 있다:
  spec.md(설계 — §3, §4.2~§4.4, §7 을 기준으로 삼아라) · precedent-publisher.yml(9/12 에 실제로 쓰인 선례) · new-publisher.yml(리뷰 대상) ·
  publisher.diff(둘의 diff) · test_s2a_main_publish.py(리뷰 대상 계약 테스트) · precedent-dispatcher.yml · new-dispatcher.yml(리뷰 대상) ·
  run_s2a_main_publish.py · test_run_s2a_main_publish.py(리뷰 대상 실행 트랜잭션) · verify_gitops_write_authority.py(참고, 수정 대상 아님)

찾을 것:
 1. new-publisher.yml 이 TARGET_SHA 가 아닌 것을 main 에 쓰거나, main 이 아닌 ref 에 쓰거나, 단언을 하나라도 건너뛰고 `git push` 에 도달하는 경로.
    셸 인용·`set -euo pipefail` 아래에서 `test`/`mapfile`/`case`/명령 치환이 실패를 삼키는 곳을 포함한다.
 2. 선례에서 의도적으로 뺀 것(체인 재검증·SEALED_SHA·RELEASE_EVIDENCE_TOKEN) 말고, **실수로 빠진** 단언.
 3. 새로 더한 "live 환경·승인 단언" step 의 jq 식이 틀린 입력에서 참이 되는 경우(빈 배열·null·여러 규칙·여러 리뷰어·여러 승인).
 4. 계약 테스트가 통과하는데 워크플로는 위험한 변형 — 테스트가 고정하지 못하는 것.
 5. run_s2a_main_publish.py: 환경 브랜치 정책이 main-only 로 복원되지 않은 채 끝나는 경로, 복원이 검증되지 않았는데 승인에 도달하는 경로,
    main 정책(id 57524487)을 지울 수 있는 경로, 예외가 삼켜지는 곳. KeyboardInterrupt 와 부분 실패(POST 는 됐는데 응답 유실)를 포함한다.
 6. 디스패처가 헬퍼 브랜치가 아닌 것을 띄울 수 있는 경우.

보고 형식: 지적마다 [심각도 Critical/Major/Minor] 파일:줄 — 무엇이, 어떤 입력에서, 어떻게 잘못되는가 — 고칠 방향 한 줄.
문제없다고 판단한 항목도 "확인함: 근거 한 줄"로 적어라. 추측은 추측이라고 표시하라.
```

- [ ] **Step 4: 컨트롤러가 직접 검증**

리뷰 보고를 그대로 믿지 않는다. 지적마다 해당 파일·줄을 Read 로 열어 사실인지 확인하고, 사실이면 재현(계약 테스트에 실패하는 케이스를 먼저 더한다 — TDD)한 뒤 고친다.
서브에이전트가 범위를 벗어나지 않았는지도 확인한다:

```bash
for r in devpath-gitops documents devpath-frontend; do
  echo "== $r"; git -C D:/workspace/dpa/$r status --porcelain | grep -v '^??' | head -5
  git -C D:/workspace/dpa/$r for-each-ref --sort=-committerdate --format='%(committerdate:iso) %(refname:short)' refs/heads | head -3
done
git -C D:/workspace/dpa/devpath-gitops worktree list | tail -4
```

Expected: 추적 파일 변경 0 · 이 계획이 만든 것 외의 새 브랜치·worktree 0.

- [ ] **Step 5: 고친 것이 있으면 해당 Task 의 검증 Step 을 다시 밟고 다시 push**

헬퍼를 고쳤다면: 같은 worktree 에서 수정 → Task 2 Step 5·6 → **새 커밋을 쌓지 말고** `git -C $HW commit --amend -q --no-edit`(봇 신원 `export` 상태에서) →
Step 7 의 모양 확인(부모 = `MAIN_SHA`·경로 2개) → `git -C $HW push --force-with-lease origin chore/s2a-mobile-free-contract-publish-20260920`.
publisher 는 헬퍼가 **main + 정확히 1커밋**일 것을 단언하므로 amend 가 맞다(이 브랜치는 이 세션만 쓰고 아직 아무도 띄우지 않았다).
디스패처를 고쳤다면 Task 3 Step 3~5 를 같은 방식으로. 실행 스크립트를 고쳤다면 Task 4 Step 4·6(후속 PR).
Critical·Major 가 남아 있으면 Task 6 으로 가지 않는다.

### Task 6: 준비 완료 보고 — 여기서 멈춘다

**Files:** 없음

- [ ] **Step 1: 최종 상태를 실측해 보고**

```bash
export MSYS_NO_PATHCONV=1
R=DevPathAi/devpath-gitops
for b in main fix/s2a-mobile-free-contract-main-20260920 chore/s2a-mobile-free-contract-publish-20260920 chore/s2a-main-publish-dispatcher-staged-20260920; do
  echo "$b = $(gh api repos/$R/branches/$b -q .commit.sha)"
done
gh api repos/$R/git/matching-refs/heads/automation/dispatch-s2a-main-publish -q length     # 0
gh api repos/$R/environments/mission-spine-production-off/deployment-branch-policies -q '.branch_policies[] | [.id,.name] | @tsv'   # 57524487 main
gh api repos/$R/rulesets -q '.[] | [.id,.enforcement] | @tsv'
```

사용자에게 보고할 것: 위 SHA 들(특히 `STAGED_SHA`) · 리뷰 지적과 처리 · main·봉인·환경이 불변이라는 실측 · Part B 에 필요한 사람 준비물
(N01 Cloudflare durable token, 같은 날 ET13 시각 승인과 NVDA 증거가 가능한 날짜).

- [ ] **Step 2: worktree 정리**

```bash
cd /d/workspace/dpa
git -C D:/workspace/dpa/devpath-gitops worktree remove D:/workspace/dpa/.worktrees/gitops-s2a-publish-helper
git -C D:/workspace/dpa/devpath-gitops worktree remove D:/workspace/dpa/.worktrees/gitops-s2a-publish-dispatcher
git -C D:/workspace/dpa/documents worktree remove D:/workspace/dpa/.worktrees/docs-s2a-publish-runner
rm -rf D:/workspace/dpa/.worktrees/_review-s2a-publish
```

로컬 브랜치는 남긴다(원격과 같다). `_tools/actionlint` 는 Part B 에서 헬퍼를 다시 만들 일이 생기면 쓰므로 남긴다.

- [ ] **Step 3: documents 에 진행 메모(핸드오프)와 메모리 갱신 후 STOP**

핸드오프 `documents/docs/superpowers/handoff-<오늘 날짜>-s2a-publisher-prepared.md` 에 Step 1 의 실측값·리뷰 결과·Part B 재개 명령(Task 7 Step 1)을 적어
`docs/*` 브랜치 → develop PR 로 올린다. 메모리 `MEMORY.md` 의 최상단 착수점을 이 핸드오프로 바꾼다.
**Part B 는 사용자가 날짜를 정하고 "진행"을 줄 때까지 시작하지 않는다.**

---

# Part B — 실행 (사용자가 정한 날, "진행" 확인 뒤)

### Task 7: 실행일 체크리스트와 확인 게이트

**Files:** 없음

- [ ] **Step 1: 전제를 다시 잰다**

```bash
export MSYS_NO_PATHCONV=1
G=D:/workspace/dpa/devpath-gitops; D=D:/workspace/dpa/documents; R=DevPathAi/devpath-gitops
git -C $G fetch origin --quiet; git -C $D fetch origin --quiet
X="<이 세션의 Scratchpad directory>/s2a-main-publish"; mkdir -p "$X"   # 시스템 프롬프트의 Scratchpad directory 절대경로를 넣는다
for f in run_s2a_main_publish.py test_run_s2a_main_publish.py; do
  git -C $D show origin/develop:docs/superpowers/plans/2026-09-20-gitops-main-promotion-via-publisher/$f > "$X/$f"
done
(cd "$X" && py -m unittest test_run_s2a_main_publish 2>&1 | tail -3)
STAGED_SHA=$(gh api repos/$R/branches/chore/s2a-main-publish-dispatcher-staged-20260920 -q .commit.sha)
py "$X/run_s2a_main_publish.py" --repo-dir $G --staged-sha $STAGED_SHA --comment unused --preflight-only
curl -s -o /dev/null -w '%{http_code}\n' https://app.leva.ai.kr; curl -s -o /dev/null -w '%{http_code}\n' https://leva.ai.kr
```

Expected: `Ran 13 tests`·`OK` · `{"preflight": "ok", …}` · `200` 두 줄. preflight 가 "main moved" 로 실패하면 **Part A 를 새 main 위에서 다시 한다**
(target·헬퍼·디스패처를 새 `MAIN_SHA` 로 다시 만들고 핀을 전부 바꾼 뒤 리뷰도 다시) — 이 계획의 SHA 로는 진행하지 않는다.

- [ ] **Step 2: 헬퍼 계약 테스트를 원격 바이트로 한 번 더**

```bash
HW=D:/workspace/dpa/.worktrees/gitops-s2a-publish-helper-verify
git -C $G worktree add --detach $HW origin/chore/s2a-mobile-free-contract-publish-20260920
(cd $HW && py -m unittest discover -s tests/release -p 'test_s2a_main_publish.py' 2>&1 | tail -3)
cd /d/workspace/dpa && git -C $G worktree remove $HW
```

Expected: `Ran 13 tests`·`OK`.

- [ ] **Step 3: 사람 준비물 확인 후 요약을 보여 주고 "진행"을 받는다**

사용자에게 묻는다(AskUserQuestion): N01 Cloudflare durable token 이 준비됐는가 · 오늘 ET13 시각 승인과 NVDA 증거를 할 수 있는가.
둘 다 예이면 다음을 요약해 보여 준다 — 지금부터 일어날 일(환경 브랜치 정책 임시 추가 → 봇 디스패치 → main-only 복원 → AI 승인 → main 이
`4f3ed64` → `69e7bd15` 로 이동) · 그 순간부터 `ms-20260916-community-ia` 의 자동 롤백 레인이 닫힌다는 것 · 비상 수단은 수동 gitops.
**"진행"을 받기 전에는 Task 8 을 시작하지 않는다.** 받은 뒤에는 Task 8~9 를 멈추지 않고 끝낸다.

### Task 8: publisher 실행

**Files:** 없음(Task 7 Step 1 이 `$X` 에 꺼내 둔 스크립트를 쓴다)

- [ ] **Step 1: 트랜잭션을 포그라운드로 실행**

```bash
py "$X/run_s2a_main_publish.py" --repo-dir $G --staged-sha $STAGED_SHA \
  --comment "Approve the exact attempt-one bot-dispatched S2a main publisher after restoring the main-only environment policy." \
  ; echo "PUBLISH_EXIT=$?"
```

Bash 도구의 `timeout` 은 최대값(600000ms)으로 준다. 선례 publisher 는 승인 포함 1분 30초에 끝났다(run `34686584754`). 그래도 도구 타임아웃으로 끊기면
**트랜잭션을 다시 돌리지 않는다** — 그 시점에 정책 복원과 승인은 이미 끝나 있다(복원은 승인보다 앞이다). Step 2 를 확인한 뒤
`gh run watch <run_id> -R $R --interval 15 --exit-status` 로 끝을 보고, `py "$X/run_s2a_main_publish.py" --repo-dir $G --staged-sha $STAGED_SHA --comment unused --post-verify-only` 로 사후 검증만 돌린다.

Expected: `{"deployment_ids": […], "main": "69e7bd15…", "run_id": …}` · `PUBLISH_EXIT=0`.

- [ ] **Step 2: 어떻게 끝났든 환경 정책부터 확인**

```bash
gh api repos/$R/environments/mission-spine-production-off/deployment-branch-policies -q '.branch_policies[] | [.id,.name,.type] | @tsv'
gh api repos/$R/environments/mission-spine-production-off -q '.protection_rules[] | select(.type=="required_reviewers") | .prevent_self_review'
```

Expected: `57524487 main branch` 한 줄 · `true`. **헬퍼 브랜치 정책이 남아 있으면 즉시 지운다**:
`gh api -X DELETE repos/$R/environments/mission-spine-production-off/deployment-branch-policies/<그 id>` — main 정책 `57524487` 은 지우지 않는다. 그리고 사용자에게 보고한다.

- [ ] **Step 3: 실패했을 때(스펙 §7)**

| `PublishError` 메시지 | main | 다음 |
|---|---|---|
| preflight 계열(`main moved`·`workflow runs`·…) | 불변, 쓰기 없음 | 원인 해소 후 Task 7 부터 |
| `never reached waiting` · `push failed` | 불변 | Step 2 확인. 디스패처 실행 로그(`gh run list --branch automation/dispatch-s2a-main-publish`)를 읽는다. 재시도는 디스패처에 nonce 커밋을 하나 더해 새 SHA 로 — `automation/dispatch-s2a-main-publish` 가 이미 있으면 preflight 가 막으므로 원인을 알고 난 뒤 그 ref 를 지운다 |
| `RestoreError` | 불변, **승인 없음** | Step 2 의 수동 복원 → 보고 → 멈춘다 |
| `cannot approve` | 불변 | 대기 실행을 취소(`gh run cancel`)하고 actor 를 확인(`gh api repos/$R/actions/runs/<id> -q .actor.login`) |
| `gh run watch` 실패(publisher 가 빨강) | `gh api repos/$R/branches/main -q .commit.sha` 로 **먼저 확인** | `4f3ed64` 면 push 전에 죽은 것 — 로그를 읽고, 워크플로를 고쳐야 하면 `-v2` 헬퍼 브랜치(재실행은 attempt 2 라 publisher 가 거부). `69e7bd15` 면 승격은 성립 — Task 9 로 |
| `main CI failed` | target | 되돌리지 않는다(integrity 룰셋이 막는다). 로그를 읽고 fix-forward 를 같은 publisher 패턴으로 — 사용자에게 보고 |

### Task 9: 사후 검증과 마무리

**Files:**
- Modify: `documents/docs/superpowers/specs/2026-09-20-gitops-main-promotion-via-publisher-design.md`(실행 결과 절 추가)
- Create: `documents/docs/superpowers/handoff-<실행일>-gitops-main-promoted.md`

- [ ] **Step 1: 스크립트의 사후 검증을 눈으로 다시 확인**

```bash
gh api repos/$R/branches/main -q .commit.sha                         # 69e7bd15…
gh api repos/$R/git/commits/69e7bd15570f5ba0f271c83b5bd46955cb249c8e -q .tree.sha   # 7799cc07…
gh run list -R $R --branch main --event push --limit 1 --json conclusion,headSha -q '.[0] | [.conclusion,.headSha] | @tsv'   # success 69e7bd15…
gh api repos/$R/rulesets -q '.[] | [.id,.name,.enforcement] | @tsv'
gh api repos/$R/branches/main/protection -q '.enforce_admins.enabled'   # true
curl -s -o /dev/null -w '%{http_code}\n' https://app.leva.ai.kr; curl -s -o /dev/null -w '%{http_code}\n' https://leva.ai.kr
```

- [ ] **Step 2: #162 를 닫는다**

```bash
gh pr close 162 -R $R --comment "같은 트리(7799cc07…)가 one-shot publisher 로 main 에 들어갔다: 69e7bd15570f5ba0f271c83b5bd46955cb249c8e (run <run_id>). main 대상 PR 은 통제면을 바꿀 수 없어(mission-spine-main-pr-policy) 이 PR 은 머지하지 않고 CI 증거로만 썼다. 브랜치는 증거로 남긴다."
```

브랜치 4개(target·헬퍼·staged·`automation/dispatch-s2a-main-publish`)는 지우지 않는다(선례도 전부 남아 있다).

- [ ] **Step 3: 문서·메모리**

스펙에 "실행 결과" 절(run id·deployment id·시각·사후 검증 값·리뷰에서 고친 것)을 더하고, 핸드오프를 새로 써서 다음 착수점을
"frontend main `31a7785d` 에 대해 ET13 baseline 봇 디스패치(`automation/dispatch-<release_id>`) → 시각 승인 → candidate(`gitops.base_sha` =
`69e7bd15…`) → NVDA → seal → promote → landing-last(prior deployment `005cf175-6e3e-4400-a201-1987ce9d8d84`)"로 고정한다. `docs/*` → develop PR.
메모리의 "gitops main 수동 머지는 3중 해제" 항목에 "통제면 변경의 정식 경로는 publisher — 봇 디스패치로 `prevent_self_review` 불변" 을 덧붙인다.

- [ ] **Step 4: 곧바로 릴리스 캠페인으로 넘어간다**

롤백 레인이 닫혀 있는 구간이다. 캠페인 계획은 이 문서의 범위 밖이므로, 핸드오프 §4 순서로 brainstorming(bounded) → 실행에 들어간다.

---

# 리뷰 결과 (Task 5, 2026-09-20)

수단: 새 컨텍스트 읽기 전용 서브에이전트(`oh-my-claudecode:security-reviewer`) — 스펙 §6. 판정은 **Critical 0 · Major 2 · Minor 4**,
핵심 결론은 "publisher 가 `TARGET_SHA` 가 아닌 것을 main 에 쓰거나 단언을 건너뛰고 `git push` 에 도달하는 경로는 없다",
"선례 대비 실수로 빠진 단언은 없다", "live 환경·승인 단언의 jq 식은 빈 배열·null·다수 규칙·다수 리뷰어·rejected 뒤 approved 에서 모두 거짓이 된다".

컨트롤러가 지적마다 **변이로 재현한 뒤** 고쳤다(변이 스크립트는 세션 스크래치패드의 `review-repro/mutate.py`·`mutate_original7.py`).

| # | 심각도 | 지적 | 재현 | 조치 |
|---|---|---|---|---|
| 1 | Major | 계약 테스트의 push 탐지가 줄 단위라 `git … \` + 다음 줄 `push …` 로 나눈 **두 번째 push** 를 못 본다 | MISSED 확인 | 모든 `run` 블록의 줄 계속을 접은 뒤 `push` 단어가 든 줄이 정확히 하나일 것을 단언 |
| 2 | Major | App 토큰으로 `gh api …/git/refs/…` 같은 **API ref 쓰기**를 해도 어떤 금지 패턴에도 안 걸린다 | MISSED 확인 | 토큰 발급 이후 step 의 `run` 에 `gh`·`curl`·`wget`·`git/refs`·`update-ref` 금지 |
| 2b | (컨트롤러 추가) | `$GITHUB_ENV` 로 핀한 좌표를 job 도중 덮어쓰는 변형도 통과한다 | MISSED 확인 | 파일 전체에 `GITHUB_ENV`·`GITHUB_PATH`·`BASH_ENV` 금지 |
| 3 | Minor | `mapfile -t x < <(git diff-tree …)` 는 git 의 실패를 `set -e` 로부터 숨긴다(선례에도 있던 모양) | `bash -c` 로 확인: 프로세스 치환은 rc=0 으로 계속, 대입은 rc=128 로 중단 | 두 곳 모두 `listing="$(…)"` 대입 + here-string 으로 교체, 계약 테스트가 `< <(` 부재를 고정 |
| 4 | Minor | 복원 도중의 `KeyboardInterrupt` 가 `except Exception` 을 뚫고 나간다(승인에는 도달하지 않지만 `RestoreError` 가 아니다) | 테스트 실행 자체가 끊김 | 복원 블록을 `except BaseException` 으로 — 중단된 복원은 "검증되지 않은 복원"이다 |
| 5 | Minor | 승인 POST 가 빈 본문이면 `len(None)` 의 `TypeError` | 테스트로 확인 | `isinstance(approved, list)` 를 함께 단언해 `PublishError` 로 |
| 6 | Minor | `--post-verify-only` 가 방금 찍은 스냅샷과 자기 비교를 한다 | 코드로 확인 | `post_verify(ops, None)` — 봉인된 모양(main-only·`prevent_self_review`·리뷰어)은 요구하되, 사전 스냅샷 비교는 하지 않는다고 코드가 정직하게 말한다 |

고친 뒤: 계약 테스트 13건 · 실행 트랜잭션 테스트 12건 · 변이 11종 전부 적발 · actionlint 무결 · live `--preflight-only` 통과(헬퍼 head `00cafba`).
헬퍼는 **amend** 로 고쳤다(publisher 가 "main + 정확히 1커밋"을 단언한다) — `2829db1` → `00cafba`.

**이 세션이 밟은 함정 두 개**(다음 실행자를 위해):

- Major 1 의 첫 재현은 "CAUGHT" 로 나왔는데 **가짜였다.** 변이 스크립트를 Bash heredoc 으로 넘기자 백슬래시+줄바꿈이 글자 그대로의 `\n` 이 되어
  변이가 한 줄짜리 push 가 됐고, 옛 테스트도 그것은 잡는다. 스크립트를 Write 도구로 파일에 쓰고 백슬래시를 `chr(92)` 로 만들자 MISSED 가 나왔다.
  (9/19 핸드오프 §5 의 "heredoc 안의 백슬래시 치환은 조용히 빗나간다" 그대로.) **재현이 기대와 다르면 재현 자체를 먼저 의심한다.**
- 셸 수정의 검증도 한 번 틀렸다: Bash 도구 안의 `( set -e; … )` 서브셸에서는 실패한 대입이 중단을 일으키지 않아 "수정이 안 먹는다"로 보였다.
  도구가 명령을 errexit 이 억제되는 문맥에서 감싸 실행하기 때문이다. GitHub Actions 와 같은 조건은 독립된 `bash -c '…'` 다.
- 리뷰 에이전트는 14분간 일하고 최종 응답으로 "완료." 한 단어만 돌려줬다(지난 세션의 "빈 응답"과 같은 모양). 보고는 에이전트 대화 기록의
  중간 메시지에 있었다 — 기록 파일을 통째로 읽지 않고 assistant 텍스트 블록의 **길이만** 먼저 뽑아 위치를 찾은 뒤 그 블록만 꺼냈다.

---

# 실행 결과 (Part B, 2026-09-20) — 승격 성공

Task 7 의 전제 재측정은 전부 통과했다. 확인 게이트에서 사용자는 **"지금 실행 — 사람 단계는 나중에"**를 골랐다(스펙 Q4 의 변경 — 스펙 §10).
Task 8 의 트랜잭션은 1회 실행으로 승격까지 끝냈고, **사후 검증의 마지막 항목에서 스크립트가 가짜 실패로 멈췄다.**

| 시각(UTC) | 일 |
|---|---|
| 05:27:09 | 트랜잭션 시작 — preflight → 환경에 헬퍼 브랜치 정책 추가 |
| 05:27:23 | 디스패처 실행 `35491720855`(`automation/dispatch-s2a-main-publish` push) success |
| 05:27:30 | publisher 실행 `35491725505` 생성 — actor·triggering actor `github-actions[bot]`, attempt 1, head `00cafba` → 승인 대기 |
| (그 사이) | main-only 복원·검증 → `VelkaressiaBlutkrone` 승인(`prevent_self_review` 불변) |
| 05:28:28 | publisher success — 14개 step 전부 통과, App 이 main 을 `4f3ed64` → `69e7bd15` 로 fast-forward |
| ~05:29 | main push 의 CI `35491763390` success |
| 05:29:22 | 스크립트가 `PublishError: https://leva.ai.kr is not 200` 로 종료(exit 1) |

**가짜 실패의 원인(스크립트 결함)**: `_http_status` 가 `urllib` 의 기본 User-Agent(`Python-urllib/3.x`)로 요청했고, Cloudflare 가 `leva.ai.kr` 에서 그 UA 에
**403** 을 돌려준다(같은 시각 curl 은 200, `app.leva.ai.kr` 은 urllib 로도 200, UA 를 `devpath-release-postverify/1.0` 으로 주면 200 — 실측).
준비 단계에서 사이트를 curl 로만 확인했고 스크립트의 urllib 경로는 live 로 한 번도 돌리지 않았다 — `--preflight-only` 는 사이트를 보지 않는다.
계획 Task 8 Step 2 대로 환경 정책부터 직접 확인(main-only · `prevent_self_review` true)한 뒤, 테스트를 먼저 더해(`test_site_probe_identifies_itself`)
`_http_status` 가 자기 UA 를 밝히도록 고치고 `--post-verify-only` 로 **사후 검증 전체를 같은 코드 경로로 통과**시켰다. 위 코드 블록은 그 최종본이다(테스트 13건).

**교훈**: 가짜 API 로 테스트한 스크립트의 **실제 I/O 가장자리**(`_gh_api`·`_run`·`_http_status`)는 테스트가 덮지 않는다. `_gh_api`·`_run` 은
`--preflight-only` 가 live 로 밟아 줬지만 `_http_status` 는 아무도 밟지 않았다. 다음에는 읽기 전용 live 점검이 **모든** 가장자리를 한 번씩 지나가게 한다.

사후 상태(실측): main `69e7bd15570f5ba0f271c83b5bd46955cb249c8e` · 트리 `7799cc07…` · 룰셋 2종 active · `enforce_admins` true · 환경 정책 `main` 단독 ·
진행·대기 실행 0 · 운영 200/200 · gitops #162 닫음(열린 PR 0) · 브랜치 4개(target·헬퍼·staged·방아쇠)는 증거로 남김.
