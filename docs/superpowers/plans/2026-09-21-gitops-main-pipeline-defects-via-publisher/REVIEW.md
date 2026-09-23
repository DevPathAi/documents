# 독립 리뷰 레시피 (Task 7) — 2026-09-23 실행 완료

2026-09-22 세션은 리뷰어를 띄웠지만 결과를 받기 전에 종료됐고, **2026-09-23 세션이 아래 레시피로 처음부터 다시 돌려 완료했다.** 기록은 `review-2026-09-23/`(지시문 `INSTRUCTION.md` · 보고 `REPORT.md` · 로그 `logs/`). 레시피는 헬퍼·target 이 바뀌어 리뷰를 다시 해야 할 때를 위해 남긴다. 전부 읽기 전용이다.

## 1. 입력 패키지 만들기

`S` = 세션의 스크래치패드, `PD` = 이 디렉터리(documents 의 **커밋된 바이트**를 `git show` 로 물질화해서 쓴다 — Windows 체크아웃은 CRLF 다), `G` = `D:/workspace/dpa/devpath-gitops`.
`MSYS_NO_PATHCONV=1` 아래에서는 `/d/…` 가 git 에 그대로 넘어가 실패한다 — `D:/…`·`C:/…` 형식만 쓴다.

```bash
export MSYS_NO_PATHCONV=1
MAIN=30c0e9f717efaad9bd46d47721a61495f4093e96
TARGET=5961922b9a309055a75bc7302e5c852c5c51d59c
HELPER=046023061409ba534d3abce5523aaf348ad70dfc      # 2026-09-23 push 본 (9/22 의 3e67810 은 push 전에 교체됨)
PREC=origin/chore/r2-writer-fence-removal-publish-20260921
mkdir -p "$S/prec" "$S/helper" "$S/review"
git -C $G fetch origin && test "$(git -C $G rev-parse origin/main)" = "$MAIN"   # 다르면 핀 전부 무효 — 멈춘다
git -C $G show "$PREC:.github/workflows/mission-spine-auth-smoke.yml" > "$S/prec/helper-0921.yml"
git -C $G show "$PREC:tests/release/test_r2_unfence_main_publish.py" > "$S/prec/test_helper-0921.py"
py -B "$PD/render_helper_workflow.py" "$S/prec/helper-0921.yml" "$S/helper/mission-spine-auth-smoke.yml"
py -B "$PD/render_contract_test.py"  "$S/prec/test_helper-0921.py" "$S/helper/test_pipeline_defects_main_publish.rendered.py"
py -B "$PD/strengthen_contract_test.py" "$S/helper/test_pipeline_defects_main_publish.rendered.py" \
     "$S/helper/mission-spine-auth-smoke.yml" "$S/helper/test_pipeline_defects_main_publish.py"
# 렌더 결과가 헬퍼 커밋의 blob 과 같아야 한다 (워크플로 ef7b4def… · 계약 테스트 dacf1dfd…)
test "$(git hash-object "$S/helper/mission-spine-auth-smoke.yml")" = \
     "$(git -C $G rev-parse $HELPER:.github/workflows/mission-spine-auth-smoke.yml)"
test "$(git hash-object "$S/helper/test_pipeline_defects_main_publish.py")" = \
     "$(git -C $G rev-parse $HELPER:tests/release/test_pipeline_defects_main_publish.py)"

git -C $G diff $MAIN $TARGET                                > "$S/review/01-target.diff"
git -C $G show -s --format='%H%n%an <%ae>%n%cn <%ce>%n%ad%n%n%B' $TARGET > "$S/review/02-target-commit.txt"
cp "$S/helper/mission-spine-auth-smoke.yml"                   "$S/review/03-helper-workflow.yml"
diff "$S/prec/helper-0921.yml" "$S/helper/mission-spine-auth-smoke.yml" > "$S/review/04-helper-vs-0921-executed.diff"
cp "$S/helper/test_pipeline_defects_main_publish.py"          "$S/review/05-contract-test.py"
diff "$S/prec/test_helper-0921.py" "$S/helper/test_pipeline_defects_main_publish.py" > "$S/review/06-contract-test-vs-0921.diff"
git -C $G show "chore/pipeline-defects-publish-dispatcher-staged-20260921:.github/workflows/mission-spine-release-gate-dispatch.yml" > "$S/review/07-dispatcher.yml"
cp "$PD/run_pipeline_defects_main_publish.py" "$S/review/08-run-script.py"
cp "$PD/contract_mutants.py"                  "$S/review/11-contract-mutants.py"
# 00 = 스펙 §12 전문(`## 12.` 부터 끝까지), 09·10 = mutation_check.py · prove_next_base.py 를 다시 돌린 로그
```

`mutation_check.py` 는 `DRYRUN_BASH="C:/Program Files/Git/bin/bash.exe"` 와 detached 워크트리(`…/gitops-pipeline-defects-scratch`)가 필요하다. `prove_next_base.py` 의 인자는 파일 머리의 Usage 를 본다(shared 스크립트와 r3 candidate spec 은 `git show` 로 물질화: shared `origin/main:scripts/release/` 전체, gitops `origin/release/candidate-ms-20260920-community-flat-pages-r3:release-manifests/candidates/ms-20260920-community-flat-pages-r3.candidate-spec.json`). `contract_mutants.py` 에는 `.github/` 와 `tests/` 만 든 최소 디렉터리를 주면 25종이 1분 안에 돈다(워크트리 전체를 주면 변이마다 통째로 복사한다).

패키지의 줄바꿈: `00`~`08`·`11` 은 커밋 바이트(LF), `09`·`10` 로그만 CRLF. 리뷰어 지시문에 이 사실과 "gitops 작업 트리는 CRLF 이므로 저장소와 대조할 때는 `git show` 의 바이트를 쓰라"를 적는다 — 9/22 의 리뷰어가 "전 줄이 다르다"에서 헛걸음한 원인이다.

## 2. 리뷰어 지시문 (새 컨텍스트 서브에이전트 1개, 읽기 전용)

전문은 `review-2026-09-23/INSTRUCTION.md`. 뼈대:

- Scope Lock: "이 작업(리뷰 1건)만 수행하라. 끝나면 보고하고 정지하라. 다른 Task 로 진행하지 말라. 명세에 없는 코드를 추측·즉흥 구현하지 말라. 명세가 부족하면 멈추고 `NEEDS_CONTEXT` 로 보고하라. 서브에이전트를 띄우지 말라."
- 금지: 모든 저장소의 파일 수정 · git 쓰기 명령 · kubectl/gh/curl · 네트워크 · pip install. 쓸 수 있는 파일은 보고서 하나뿐. 모든 git/파일 명령은 절대경로 또는 `-C <절대경로>`(에이전트 스레드는 bash 호출 사이 cwd 가 리셋된다). `rev:.github/…` 인자 앞에 `MSYS_NO_PATHCONV=1`, Python 은 `py`.
- 찾을 것(우선순위순): ① publisher 가 의도와 다른 것을 main 에 올릴 수 있는 경로 — 핀 우회·step env 가림·`set -euo pipefail` 아래에서도 조용히 통과하는 셸 구문, 특히 9/21 실행본에서 **바뀐** "전체 목록 비교" 블록(`expected_listing`) ② 계약 테스트가 ①을 놓치는 구체적 변이 ③ target 내용(`startupProbe` 값·위치, `_probe_api` 의 오류 처리, 새 테스트가 의미 있는 것을 단언하는지, 커밋 메시지의 사실 오류 — sandbox-svc 의 컨테이너는 **1개**다, 113행의 `sandbox-runner-mtls` 는 볼륨) ④ 실행 스크립트의 좌표 8줄이 다른 입력과 일치하는지 ⑤ §12.3 실행 절차가 다루지 않은 운영 위험.
- 보고: 발견마다 심각도(Critical/Medium/Low/Info) · 위치(파일:줄) · 문제 · 재현 방법 또는 구체적 변이 · 권고. 확인했으나 문제없던 항목도 나열. 추측은 추측이라고 표시. **응답은 3줄, 전문은 지정 파일에.**
- Codex 는 계정 한도(2026-10-19 까지)로 쓸 수 없었다 — 그 뒤라면 `codex exec -s read-only` 로 같은 지시문을 줄 수 있다.

## 3. 리뷰 뒤

- 컨트롤러 검증: 리뷰 전후로 gitops · documents · shared · 홈 · frontend 의 브랜치 목록·작업 트리·stash 스냅샷을 `diff` 로 대조한다(9/23: 동일).
- Critical/Medium 은 변이·재현으로 **먼저 확인한 뒤** 고친다(`contract_mutants.py` 에 변이를 추가해 SURVIVED 를 보고, 보강 뒤 killed 를 본다 — 9/23: F1/F2 의 16종 SURVIVED → 25/25 killed). 헬퍼가 바뀌면 로컬 헬퍼 커밋을 새로 만들고(단일 자식·정확히 2경로, 워크플로만 안 바뀌면 그 blob 은 그대로) `HELPER_SHA` 가 바뀐다. target 이 바뀌면 `TARGET_SHA`·`TARGET_TREE` 가 바뀌어 헬퍼·계약 테스트·실행 스크립트의 핀을 전부 다시 렌더한다 — 이미 push 된 target 브랜치는 새 SHA 로 교체해야 하므로 그때 사용자에게 알린다.
- 그다음: 헬퍼·디스패처 push(둘 다 워크플로를 실행시키지 않는다 — 헬퍼는 `workflow_dispatch` 전용, 디스패처는 방아쇠 브랜치 push 에서만) → `run_pipeline_defects_main_publish.py --preflight-only` + 음성 대조(틀린 `--helper-sha` → 첫 쓰기 전 `helper branch moved away from the reviewed commit`) → 스펙 §12.4 의 확인 관문.
