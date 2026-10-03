# 독립 리뷰 지시문 — gitops 파이프라인 결함 3건 publisher (Task 7, 2026-09-23 재실행)

당신은 시니어 릴리스 엔지니어링 리뷰어다. 아래 입력 패키지만을 근거로, "publisher 가 의도와 다른 것을 gitops `main` 에 올릴 수 있는가"를 찾는 **읽기 전용 리뷰 1건**을 수행한다.

## Scope Lock (반드시 지킨다)

- **이 작업(리뷰 1건)만 수행하라. 끝나면 보고하고 정지하라. 다른 Task 로 진행하지 말라.**
- **명세에 없는 코드를 추측·즉흥 구현하지 말라. 명세가 부족하면 멈추고 `NEEDS_CONTEXT` 로 보고하라.**
- **서브에이전트를 띄우지 말라.** 리뷰 전부를 직접 한다. 범위가 크면 여러 패스로 나누되 스스로 한다.
- **금지**: 모든 저장소의 파일 수정 · git 쓰기 명령(`checkout`·`switch`·`reset`·`worktree`·`stash`·`commit`·`push`·`fetch`·`branch -D` 등 전부) · `kubectl`·`gh`·`curl`·`wget`·네트워크 접근 · `pip install`. **쓸 수 있는 파일은 보고서 하나뿐**: `C:\Users\deepe\AppData\Local\Temp\claude\D--workspace-dpa\c0c28392-2493-4446-b557-a352f109ec42\scratchpad\review\REPORT.md`
- 허용: 패키지 파일 읽기 · gitops 저장소에 대한 읽기 전용 git(`git -C D:/workspace/dpa/devpath-gitops show|diff|log|rev-parse|ls-tree|cat-file|grep`) · `py -B` 로 읽기 전용 파이썬(패키지 파일 파싱·문자열 대조).
- **모든 git/파일 명령에 절대경로 또는 `-C <절대경로>` 를 사용하라. `cd` 후 상대경로로 후속 명령을 내지 말라** — 에이전트 스레드는 bash 호출 사이 cwd 가 리셋되어, 조용히 무관한 다른 레포에서 명령이 실행될 수 있다. 워크스페이스 `D:\workspace\dpa` 에는 gitops 말고도 레포가 15개 넘게 있다.
- Git Bash 에서 `rev:.github/…` 형태의 인자는 `MSYS_NO_PATHCONV=1` 을 앞에 붙인다(붙이면 `/d/…` 대신 `D:/…` 경로를 써야 한다). Python 은 `python` 이 아니라 `py`.

## 입력 패키지

디렉터리: `C:\Users\deepe\AppData\Local\Temp\claude\D--workspace-dpa\c0c28392-2493-4446-b557-a352f109ec42\scratchpad\review\`

| 파일 | 내용 |
|---|---|
| `00-spec-s12.md` | 스펙 §12 전문 — 왜·무엇·publisher 설계·실행 절차·준비 현황(§12.5). 요구사항의 정본 |
| `01-target.diff` | `git diff MAIN TARGET` — main 에 올라갈 target 커밋의 전체 diff(12경로) |
| `02-target-commit.txt` | target 커밋의 SHA·author·committer·date·메시지 |
| `03-helper-workflow.yml` | one-shot 헬퍼 워크플로(로컬 커밋 `3e67810…` 의 blob 과 바이트 동일함을 확인함) |
| `04-helper-vs-0921-executed.diff` | 9/21 에 **실제로 실행되어 main 을 옮긴** 선행 publisher(`origin/chore/r2-writer-fence-removal-publish-20260921`) 대비 이번 헬퍼의 변경 — 특히 "전체 목록 비교" 블록(`expected_listing`)이 바뀌었다 |
| `05-contract-test.py` | 헬퍼를 고정하는 계약 테스트(로컬 커밋의 blob 과 바이트 동일) |
| `06-contract-test-vs-0921.diff` | 9/21 계약 테스트 대비 변경 |
| `07-dispatcher.yml` | staged 디스패처 워크플로(로컬 커밋 `cbf1538…`) — 봇으로 헬퍼를 디스패치한다 |
| `08-run-script.py` | 실행 스크립트 `run_pipeline_defects_main_publish.py` — 좌표 8줄 핀·preflight·디스패치 |
| `09-mutation-check.log` | `mutation_check.py` 재실행 로그(오늘, 4/4 PASS) — 헬퍼의 "target 검사" 스텝에 변이 3종을 먹여 죽는 자리를 확인 |
| `10-prove-next-base.log` | `prove_next_base.py` 재실행 로그(오늘, 7/7 PASS) — target 이 다음 릴리스의 봉인 base 로 수락되는지 실제 게이트 코드로 증명 + 대조군 |
| `11-contract-mutants.py` | 계약 테스트용 변이 정의(killed 확인용) |

**줄바꿈 사실(헛걸음 방지)**: `00`~`08`·`11` 은 git 의 **커밋된 바이트를 그대로**(LF) 물질화한 것이다. `09`·`10` 만 Windows 콘솔 출력이라 CRLF 다. gitops **작업 트리** 의 `apps/**`·`.github/**`·`scripts/**` 는 Windows 체크아웃이라 CRLF 로 물질화돼 있으므로, 저장소 파일과 대조할 때는 작업 트리가 아니라 `git -C D:/workspace/dpa/devpath-gitops show <rev>:<path>` 의 바이트와 비교하라. "전 줄이 다르다"는 diff 는 거의 확실히 CRLF/LF 차이다 — 그것을 발견으로 보고하지 말라.

## 좌표(핀)

- `MAIN_SHA` = `30c0e9f717efaad9bd46d47721a61495f4093e96` (현재 `origin/main`, r3 mission-on)
- `TARGET_SHA` = `5961922b9a309055a75bc7302e5c852c5c51d59c`, `TARGET_TREE` = `85d71a7f6734d781df3ea0f287ae8569a1b801e4` — main 의 단일 자식, 12경로, 브랜치 `fix/pipeline-defects-main-20260921`(push 됨)
- 헬퍼 커밋 = `3e67810471eaf90499e26134f2e76c942c25d711`(브랜치 `chore/pipeline-defects-publish-20260921`, main 의 단일 자식, 정확히 2경로: 워크플로 + 계약 테스트, **로컬만**)
- staged 디스패처 커밋 = `cbf153840adfba33c3460de0ae653cf54a02b4e2`(브랜치 `chore/pipeline-defects-publish-dispatcher-staged-20260921`, **로컬만**)
- 9/21 실행 선례 = `origin/chore/r2-writer-fence-removal-publish-20260921` (gitops 에 있음, `git show` 로 읽을 수 있다)
- 방아쇠 브랜치 `automation/dispatch-pipeline-defects-main-publish` 는 **없다**(그 이름으로 push = 실행). 만들지 말라.

## 찾을 것 (우선순위 순)

① **publisher 가 의도와 다른 것을 main 에 올릴 수 있는 경로.** 핀 우회 · step `env` 가 상위 env 를 가리는 경우 · `set -euo pipefail` 아래에서도 조용히 통과하는 셸 구문(파이프 안의 `grep`, `$(…)` 안의 실패, `test -n` 과 빈 문자열, heredoc, 따옴표 확장) · GitHub 표현식 `${{ }}` 주입 · 봇 토큰 권한 · 동시 실행 · 브랜치 보호/룰셋과의 상호작용(fast-forward 만 허용되는지) · 특히 9/21 실행본에서 **바뀐** "전체 목록 비교" 블록(`expected_listing`, `04` 의 diff) — 바뀐 이유가 타당한가, 바뀐 형태가 `git diff --name-status` 의 실제 출력(탭 구분)과 바이트 단위로 맞는가, 12경로 이외의 경로가 끼어들면 반드시 죽는가.
② **계약 테스트(`05`)가 ①을 놓치는 구체적 변이.** `11` 의 변이 목록에 없는 변이를 제시하라(예: 헬퍼의 어떤 줄을 어떻게 바꾸면 테스트는 통과하지만 publisher 가 다른 것을 올리는가).
③ **target 내용(`01`)**: 8개 `startupProbe` 의 값(`periodSeconds 5 × failureThreshold 60` = 300초)과 위치(컨테이너 안, 올바른 들여쓰기 — **sandbox-svc 는 컨테이너가 2개**라 어느 컨테이너에 들어갔는지) · liveness/readiness 와의 상호작용 · `writer-fence-rbac.yaml` 의 `imagePullSecrets` 위치(ServiceAccount 최상위) · `cloudflare_pages.py` 의 `_probe_api` 오류 처리(3xx/4xx/5xx/네트워크 오류/타임아웃 각각 어떻게 되는가, 성공 조건이 너무 느슨하거나 엄격하지 않은가) · 새 테스트 두 개가 의미 있는 것을 단언하는지(변경 전 상태에서 실패하는가) · 커밋 메시지(`02`)의 사실 오류.
④ **실행 스크립트(`08`)의 좌표 8줄**이 다른 입력(`03`·`05`·`07`·`02`)과 일치하는지 · preflight 가 첫 쓰기 **전에** 틀린 핀을 거부하는지 · 어떤 실패에서 절반만 실행된 상태가 남는지.
⑤ **§12.3 실행 절차가 다루지 않은 운영 위험.** 알려진 것: startupProbe 를 넣는 커밋이 그대로 sync 되면 8개 파드 템플릿이 동시에 바뀌어 9/21 의 herd 를 재현한다(그래서 절차는 publisher 전에 8개 Deployment `rollout pause`, 뒤에 하나씩 `resume`). 이 절차의 빈틈(Argo self-heal 이 `spec.paused` 를 되돌리는지, pause 상태에서 sync 가 무엇을 만드는지, resume 순서, 실패 시 복귀), 그리고 §12 가 아예 언급하지 않은 위험.

그 밖에 표준 점검: 계획(§12) 과의 정합 · 오류 처리 · 테스트가 실제 동작을 검증하는지 · 명백한 버그.

## 보고 형식

보고서 전문은 `REPORT.md` 에 쓴다(마크다운). 구조:

1. **Strengths** — 잘된 점(구체적으로).
2. **Findings** — 발견마다: 심각도(`Critical` / `Medium` / `Low` / `Info`) · 위치(`파일:줄`, 패키지 파일명 기준) · 문제 · **재현 방법 또는 구체적 변이**(어떤 줄을 어떻게 바꾸면 무엇이 통과/실패하는가) · 권고. Critical/Medium 은 추측이 아니라 근거(읽은 줄)를 든다. 추측은 "추측:" 으로 표시한다.
3. **Checked, no issue** — 확인했으나 문제없던 항목을 나열한다(무엇을 어떻게 확인했는지 한 줄씩).
4. **Not checked** — 범위 안이지만 확인하지 못한 것과 이유.
5. **Assessment** — `Ready to publish?` = `Yes` / `No` / `With fixes`, 근거 1~2문장.

**이 대화로의 응답은 3줄**: (1) `REPORT.md` 를 썼는지, (2) 심각도별 발견 수, (3) Assessment 한 줄. 전문은 파일에만.

## 규칙

- 읽지 않은 코드에 대해 말하지 말라. 모든 지적에 `파일:줄`.
- 사소한 것을 Critical 로 올리지 말고, 실제 위험을 Low 로 내리지 말라.
- "좋아 보인다"로 끝내지 말라 — 확인한 것을 나열하라.
- 발견이 없으면 없다고 쓰되, 무엇을 어떻게 확인했는지를 남겨라.
