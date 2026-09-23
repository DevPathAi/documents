# 독립 리뷰 보고 — gitops 파이프라인 결함 3건 publisher (Task 7, 2026-09-23)

리뷰어: 새 컨텍스트, 읽기 전용. 근거는 입력 패키지 `00`~`11` 과 `git -C D:/workspace/dpa/devpath-gitops show|diff|diff-tree|rev-list|grep` 의 바이트, 그리고 `py -B` 인메모리 실행(파일 쓰기 없음). 저장소·워크트리·원격은 하나도 건드리지 않았다. 패키지 밖에서 읽은 것은 gitops 저장소의 커밋 객체와 documents `origin/develop` 의 `plans/2026-09-21-gitops-main-pipeline-defects-via-publisher/*`(실행 스크립트 원본·`mutation_check.py`·`prove_next_base.py`·단위 테스트 이름)뿐이며, 어디서 읽었는지 각 항목에 적었다.

---

## 1. Strengths

1. **패키지가 저장소 바이트와 정확히 같다.** `03`=`3e67810:.github/workflows/mission-spine-auth-smoke.yml`, `05`=`3e67810:tests/release/test_pipeline_defects_main_publish.py`, `07`=`cbf1538:.github/workflows/mission-spine-release-gate-dispatch.yml`, `01`=`git diff 30c0e9f7 5961922b`, `02`=`git show -s` 메타, `04`/`06`=9/21 실행본(`8e42f757`) 대비 diff, `08`=documents `origin/develop` 의 `run_pipeline_defects_main_publish.py`, `11`=같은 곳의 `contract_mutants.py` — 전부 `cmp`/`diff` 로 바이트 동일 확인.
2. **좌표가 전부 서로 맞고 그래프가 주장과 일치한다.** `5961922b` 는 `30c0e9f7` 의 단일 자식, 트리 `85d71a7f`, 12경로 전부 `100644`(모드 변경 없음), 신규 1건(`A`), `git diff --check` 깨끗함. 헬퍼 `3e67810` 은 `30c0e9f7` 의 단일 자식·정확히 2경로(`M` 워크플로 · `A` 계약 테스트). 디스패처 `cbf1538` 은 `30c0e9f7` 의 단일 자식·1경로 추가. 로컬 `refs/remotes/origin/main` = `30c0e9f7`(마지막 fetch 기준). `08` 의 7개 좌표 + `07` 의 브랜치명 + `03` 의 env + `05` 의 상수가 한 글자도 어긋나지 않는다.
3. **"전체 목록 비교" 블록(`03:148-166`)은 `git diff-tree --name-status -r` 의 실제 바이트와 맞는다.** 실제 출력을 `cat -A` 로 떠 보면 `M^Ipath$` 형태(탭 구분, 트리 순서)이고, 같은 bash 구문(printf + ANSI-C 탭 + `$( )` 의 후행 개행 제거)을 그대로 돌려 `test "$target_listing" = "$expected_listing"` 이 참이 되는 것과 `mapfile` 행 수 12 를 재현했다. `diff-tree` 는 plumbing 이라 `diff.renames` 설정과 무관하게 rename 탐지를 하지 않으므로 `R` 행이 끼어들 수 없고, 13번째 경로·11경로는 문자열이 달라져 반드시 죽는다(`09` 의 A·B 도 그 줄에서 죽었다). 9/21 의 행별 비교+블롭 복원 검사를 버린 이유도 타당하다 — 그때는 "pre-fence 블롭으로 되돌아왔는가"라는 참조가 있었고, 이번엔 참조가 없으니 내용 보증은 트리 핀(`03:139`)이 맡는다(`09` 의 C 가 그 줄에서 죽었다).
4. **모든 `test "$(…)" = "$X"` 가 비어 있을 수 없는 핀 상수와 비교된다.** 치환이 실패해 빈 문자열이 되어도 빈 문자열 = 비어있지 않은 상수 는 거짓이라 fail-closed 다(`03:66-67,77,99-119,137-147,203-209,223,226,232-233`). 할당형 `var="$(cmd)"` 는 `set -e` 아래에서 cmd 의 실패를 전파한다(`03:68,73,148,150`). `mapfile < <(…)` 는 없다(`05:265-267` 이 금지).
5. **push 는 SHA 를 fast-forward 로만 옮긴다.** `03:224` 가 `$TARGET_SHA:refs/heads/main` 을 강제 옵션 없이 push 하고, 직전에 `origin/main == MAIN_SHA`(`03:222-223`), 직후에 `== TARGET_SHA`(`03:225-226`), 별도 step 에서 트리까지 재확인(`03:228-233`). TOCTOU 로 main 이 그 사이 다른 곳으로 움직이면 non-FF 로 거부되고, `TARGET_SHA` 의 조상으로만 움직였다면 결과는 여전히 `TARGET_SHA` 다. `verify_gitops_write_authority.py`(target 트리, `5961922b:scripts/release/verify_gitops_write_authority.py`)가 push 직전 두 번(`03:200-202, 219-221`) integrity 룰셋이 `deletion`+`non_fast_forward`+`required_linear_history` 정확히 3규칙·App 도 bypass 불가(`never`), governance 는 `update` 단일 규칙·App 만 bypass, classic 보호는 `restrictions.apps`=App 단독·`enforce_admins`·`allow_force_pushes=false` 임을 실제 API 로 요구한다. 설치가 gitops 레포 하나만 선택하는지도(`total_count == 1`) 검사하므로 `repositories:` 없는 토큰 민팅(`03:174-180`)의 범위 우려가 상쇄된다.
6. **실행 스크립트는 첫 쓰기 전에 모든 읽기 경로를 지난다.** `08:132-165` 의 preflight 는 리뷰어 계정 → main/target/staged/helper 핀 → 헬퍼 부모 → 방아쇠 브랜치 부재 → 바쁜 런 0 → 룰셋·트리·CI 미실행·사이트 200 → 환경 스냅샷 순이고 첫 쓰기(`08:206` 정책 POST)는 그 뒤다. 복원(`08:185-191`)이 승인(`08:230-245`)보다 먼저이며 검증 실패 시 `RestoreError` 로 승인이 막힌다(`08:218-225`). documents `origin/develop` 의 `test_run_pipeline_defects_main_publish.py` 에 이 경로들(moved main · busy repo · never-waits · failed dispatch push · unverified restore · unapprovable · red CI · interrupt-during-restore)이 18건으로 있다.
7. **target 내용이 §12.1 과 일치한다.** 8개 파일 전부 서비스 이름과 같은 단일 컨테이너의 `readinessProbe` 바로 앞에 같은 7줄이 들어갔고(YAML 파싱으로 확인: `periodSeconds 5 · failureThreshold 60 · timeoutSeconds 3`, liveness 키 = `{httpGet, initialDelaySeconds:20}`, readiness `initialDelaySeconds:10` 그대로), `writer-fence-rbac.yaml` 의 `imagePullSecrets` 는 ServiceAccount 최상위(`01:99-100`, target 파일 6-7행). 값은 `staging/mission-spine/patches/*.yaml` 의 선례와 동일하고 `test_mission_staging_stack.py::test_spring_services_have_staging_startup_budget` 의 "≥300초" 계약을 그대로 옮겼다.
8. **새 테스트가 변경 전 상태에서 실패한다.** `test_production_startup_budget.py` 는 main 트리에서 `startupProbe` 가 `None`(assertIsNotNone) · SA 에 `imagePullSecrets` 키 없음(KeyError) 으로 RED, `LandingApiSmokeTest` 는 main 의 모듈에 `_probe_api` 가 없어 RED — 스펙 §12.5 의 "RED→GREEN" 주장과 코드가 맞는다. `test_steady_state_probes_are_unchanged` 가 두 프로브를 **dict 전체 동등**으로 단언해 키 추가까지 막는다.
9. **`_probe_api` 는 9/21 사고 모양을 실제로 거부한다.** `_NO_REDIRECT_OPENER` 는 `redirect_request` 가 `None` 을 돌려주므로 3xx 는 `HTTPError`, 4xx/5xx 도 `HTTPError`, 연결 오류·타임아웃은 `URLError`/`TimeoutError` — 전부 `OSError` 라 `01:182-183` 의 한 `except` 로 fail-closed. 정적 404 페이지(4xx)·SPA fallback(HTML 200)·빈 204·과대 본문·비-UTF-8 이 각각 다른 줄에서 거부되고, 테스트(`01:235-257`)가 그 조합을 덮는다. 홈 레포 `origin/develop` 에 `functions/api/invite-rounds.js` 가 실재한다.
10. **§12.4 의 주장은 코드와 맞다.** `verify_promotion_chain.py`(`30c0e9f7`, 약 1260행)의 walk 는 알려진 subject 가 아니면 `"current main contains an unrelated promotion commit"` 으로 거부하고, `mission-spine-rollback.yml:138-141` 이 `--current refs/remotes/origin/main` 으로 그것을 돌린다 — main 이 target 으로 옮겨진 순간 r3 자동 롤백 레인이 닫힌다는 서술이 정확하다.

---

## 2. Findings

### F1 · Medium — 계약 테스트(`05`)는 push 에 관여하는 step 을 **조각 문자열**로만 고정한다 → App 토큰이 다른 SHA 를 올리는 변이가 살아남는다

- 위치: `05:226-252`(`test_only_the_release_app_fast_forwards_main_exactly_once`), `05:254-263`(`test_token_bearing_steps_have_no_other_write_path`), `05:128-132`(`test_every_action_is_pinned_to_a_full_sha`), `05:106-114`(step env 그림자만 검사).
- 문제: push 관련 보증이 (a) `\bpush\b` 를 포함하는 **줄의 목록**이 정확히 하나인지, (b) mint 이후 `run` 본문에 `gh|curl|wget|git/refs|update-ref` 가 없는지, (c) step **`env` 키**가 핀을 가리지 않는지로 이루어져 있다. `run` 본문 안의 셸 변수 재할당, `uses:` 로 추가된 step, 정규식을 피하는 철자, `python -c` 는 어느 단언에도 걸리지 않는다. 아래 변이를 `05` 의 소스를 인메모리로 exec 하고 `WORKFLOW` 를 변이 텍스트로 바꿔 **16/16 통과(SURVIVED)** 를 확인했다(대조군: step env 그림자·refspec 변경·`GITHUB_ENV` 기록은 killed).
  - **M1** `03:224` 바로 위에 `TARGET_SHA=dddd…(40)` 한 줄 삽입(`export …`, `printf -v TARGET_SHA …` 도 동일). push 줄은 바이트 그대로이므로 `05:236-238` 통과, 같은 step 의 사후 검사(`03:226`)도 재할당된 값과 비교돼 통과, 별도 step 인 재인증(`03:232`)에서야 죽는다 — **그때는 main 이 이미 옮겨진 뒤다.**
  - **M2** mint step(`03:172-180`) 뒤에 `- uses: attacker/x@<40hex>` + `with: token: ${{ steps.app_token.outputs.token }}` step 삽입. `PINNED_ACTION` 은 40-hex 면 아무 owner/repo 나 허용하고, `app_token` 문자열 금지는 mint **이전** step 에만 적용된다(`05:223-224`). `run` 이 아니므로 (b) 도 보지 않는다.
  - **M3** `03:224` 앞에 `git -C gitops-main pu""sh origin dddd…:refs/heads/main` 삽입 — bash 는 `push` 로 이어 붙이지만 `\bpush\b` 는 매치하지 않는다.
  - **M4** push step 의 `git fetch` 앞에 `python -c "…urlopen(Request('https://api.github.com/repos/DevPathAi/devpath-gitops/git/'+'refs/heads/main', method='PATCH', headers={'Authorization':'Bearer '+os.environ['GH_TOKEN']}))"` 삽입 — `git/refs` 리터럴을 쪼개면 (b) 를 지난다.
  - (부수) **M6** `03:185` `repository:` 를 다른 레포로, **M8** push 앞에 `git config url.<attacker>.insteadOf <origin>` 삽입, **M12/M13** mint 에 `repositories:`/`permission-workflows: write` 추가, **M11** `runs-on` 변경 — 전부 SURVIVED. 이들은 main 을 다른 것으로 바꾸지는 못하지만(오히려 push 가 엉뚱한 곳으로 가거나 실패) 워크플로 형태가 고정돼 있지 않다는 같은 증상이다.
- 실제 위험도 평가: 이번 실행의 진짜 경계는 계약 테스트가 아니라 **리뷰된 헬퍼 SHA** 다 — `08:137-142` 가 `--helper-sha` 와 부모를 요구하고 `08:178` 이 런의 `head_sha` 를 같은 값으로 요구한다. 따라서 오퍼레이터가 `3e67810…` 를 정확히 넘기는 한 위 변이들은 라이브 경로가 아니다. 그러나 스펙(`00:35` ⑥, `00:68`)은 이 테스트를 "헬퍼를 고정하는 계약"으로 부르고, 실수·재사용(다음 publisher 를 이 템플릿에서 치환해 만들 때)에서 push step 의 변형을 잡지 못한다. 그래서 Medium.
- 권고(헬퍼 커밋만 바뀌고 target·핀은 그대로): ① mint·gitops-main checkout·인증·fast-forward·재인증 다섯 step 의 **dict 전체를 리터럴과 동등 비교**(현재 목록 블록에 쓴 방식과 같은 강도). ② `uses` 집합을 정확히 `{checkout@d23441a…, setup-python@ece7cb0…, setup-kubectl@8293235…, create-github-app-token@bcd2ba4…}` 로, `steps.app_token` 출현을 정확히 3곳(`03:187,194-197,213-216`)으로 고정. ③ mint 이후 step 은 `run` 또는 알려진 `uses` 만 허용하고 `with.token` 을 금지. ④ 금지어에 `|| :`, `||:`, `true ||`, `printf -v`, `read `, `eval`, `source `, `. `, `export `, 그리고 핀 이름 뒤의 `=` 를 추가(F2 참조).

### F2 · Low — `set -e` 무력화 철자 `|| :` · `true ||` 가 금지어에 없다 → 게이트 단언을 조각 그대로 남기고 죽인다

- 위치: `05:125`(금지어 `set +e`, `set +u`, `set +o pipefail`, `|| true` 뿐), `05:158-168`·`05:199-212`(assertIn 조각).
- 변이(모두 SURVIVED): **M5** `03:139` 트리 핀에 ` || :` 접미, **M5b** 같은 줄에 `true || ` 접두, **M5c** `03:138` 부모 핀에 ` || :`, **M10** `03:118` 승인자 로그인 검사에 ` || :`. 조각은 여전히 포함돼 있어 assertIn 이 통과한다. 이들은 push 되는 SHA 를 바꾸지는 못하지만(핀은 env 상수) target 검증·승인자 검증이라는 이 워크플로의 존재 이유를 조용히 끈다.
- 권고: F1 ④ 의 금지어 추가 + 조각이 아니라 **줄 단위 정확 일치**(`" ".join(line.split())` 정규화 후 `lines.index(...)`)로 바꾼다 — `05:188-191` 이 이미 그 패턴을 쓰고 있다.

### F3 · Low — §12.3 1단계의 "1~2분 관찰" 은 Argo 의 기본 재조정 주기(180초)보다 짧다 → self-heal 이 한 번도 돌지 않은 채 관문을 통과할 수 있다

- 위치: `00:41`(1단계), `00:44`(4단계 "Synced 유지"), `00:46`(6단계 Healthy).
- 근거: `30c0e9f7:argocd/applicationset.yaml:29-34` 는 `automated.prune/selfHeal: true` 만 두고, 저장소 어디에도 `timeout.reconciliation`·`argocd-cm` 재정의가 없다(git grep 0건) → 기본 3분. self-heal 은 재조정 시점의 diff 로만 판단하므로 pause 직후 1~2분 관찰은 관측이 비어 있을 수 있다. (추측: 되돌리지 않는다 — `spec.paused` 는 desired 에도 last-applied 에도 없어 3-way diff 의 대상이 아니며, `00:11` 의 "last-applied 에 없는 필드는 diff 대상이 아니다" 와 같은 원리. 하지만 스펙이 이것을 **실측 관문**으로 뒀으니 관측이 실제로 일어나게 해야 한다.)
- 추가로 알아 둘 것: `spec.paused: true` 인 Deployment 의 Argo 내장 health 는 **`Suspended`("Deployment is paused")** 다. 4단계에서 기대할 상태는 `Synced / Suspended` 이며 `Healthy` 는 resume 뒤에야 돌아온다 — 6단계 문구는 맞고 4단계는 health 를 명시하지 않는다. 그 사이 알림·대시보드가 Healthy 를 기대한다면 오탐이 난다.
- 권고: 1단계에 **강제 재조정**(`argocd app get devpath-notification-svc --hard-refresh` 또는 `kubectl -n argocd annotate application devpath-notification-svc argocd.argoproj.io/refresh=hard --overwrite`)을 넣고, 재조정 뒤 `spec.paused == true` 와 `Synced` 를 확인한다. 4단계 기대값에 `Suspended` 를 적는다.

### F4 · Low — 실행 스크립트가 남길 수 있는 "절반 상태" 두 가지에 정리 절차가 없다

- 위치: `08:194-227`(`open_dispatch_restore`), `08:143-149`(preflight 의 거부 조건), `00:37-48`(§12.3 에 정리 절차 없음).
- 시나리오: (a) 방아쇠 브랜치 push(`08:207-209`) 는 성공했으나 `_waiting_run` 이 `head_sha`/actor/attempt 불일치로 raise 하거나 300초 데드라인을 넘긴 경우(`08:211-215`) — 정책은 복원되고 승인은 안 되지만 **`automation/dispatch-pipeline-defects-main-publish` 브랜치와 `waiting` 상태의 런(보류 배포)이 남는다.** (b) 승인 뒤 `gh run watch`(`08:275`) 가 네트워크로 죽으면 post_verify 가 생략된다(이쪽은 `--post-verify-only` 가 있다).
- (a) 에서 다음 시도의 preflight 는 `"dispatcher branch already exists"`(`08:143-146`)와 `"repository has waiting workflow runs"`(`08:147-149`)로 정확히 막힌다 — fail-closed 로는 옳다. 그러나 스크립트도 §12.3 도 그 정리(방아쇠 브랜치 삭제 · 보류 배포 거부/런 취소 — 거부는 리뷰어 계정으로 `POST …/pending_deployments {"state":"rejected"}`)를 적지 않아 사람이 즉흥으로 하게 된다. 남은 `waiting` 런은 정책이 main-only 로 복원된 뒤에도 리뷰어가 UI 에서 실수로 승인할 수 있는 상태다(그 런의 헬퍼 컨텍스트 검사는 통과할 것이다).
- 권고: §12.3 에 (a) 의 정리 명령 2개를 적고, 스크립트 실패 메시지에 "남은 것"을 출력한다(정리 자동화는 범위 밖이어도 된다).

### F5 · Low — §12.3 의 "실패 처리" 는 되돌림이 아니라 **보류**이고, 진짜 되돌림 경로의 소요 시간이 정해져 있지 않다

- 위치: `00:48`, `00:52`.
- 근거: 새 파드가 Ready 가 안 될 때 "다시 pause + 새 RS `scale --replicas=0`" 은 옛 파드가 계속 서비스하게 하는 보류다(Deployment 컨트롤러는 paused 상태에서 `createIfNotExisted=false` 로 sync 만 하므로 새 RS 를 다시 만들지 않는다 — 9/21 실측과 일치). 그러나 템플릿을 실제로 되돌리는 방법은 `kubectl rollout undo` 가 **아니다**(Argo self-heal 이 git 템플릿으로 되돌려 새 RS 를 다시 만든다) — 되돌림은 8개 파일을 되돌리는 **또 한 번의 publisher**(target·헬퍼·리뷰·승인)이고, §12.4 대로 r3 자동 롤백 레인은 닫혀 있다. 보류 상태(Suspended, `updatedReplicas: 0`)는 다음 릴리스 캠페인의 런타임 검증(`verify_kubernetes_release_runtime.py` 의 `restartCount == 0`·Running/Ready·단일 컨테이너 검사)과 충돌하지 않지만, 그 캠페인이 다시 템플릿을 바꾸는 순간 보류가 풀린다.
- 권고: 실행 전에 되돌림 target(`TARGET_SHA` 의 자식으로 8개 deployment.yaml 만 `MAIN_SHA` 블롭으로 되돌린 결정적 커밋)을 미리 만들어 두거나, "보류로 충분하며 되돌림 publisher 는 N시간" 을 §12.3 에 명시해 결정을 남긴다.

### F6 · Info — `_probe_api` 의 예외 경계와 수락 조건 두 가지

- 위치: `01:177-189`.
- `http.client.IncompleteRead`·`HTTPException` 은 `OSError` 가 아니라 `except OSError` 를 지나 원시 예외로 터진다 — 여전히 실패(fail-closed)지만 메시지가 "Landing API smoke failed" 가 아니다. `json.loads` 는 `null`·`"x"`·`1` 도 수락한다 — 스펙 문구("JSON 으로 파싱 가능")와는 일치하나, 함수가 "라운드 목록" 을 주는 라우트이므로 객체/배열을 요구하면 더 조인다. `Content-Encoding` 검사는 없지만 urllib 이 `Accept-Encoding` 을 보내지 않으므로 identity 가 기대된다. 라이브 검증(`00:68`)이 통과했으니 이번 범위에선 변경 불필요.

### F7 · Info — 지시문의 전제 "sandbox-svc 는 컨테이너가 2개" 는 사실이 아니다

- `5961922b:apps/devpath-sandbox-svc/base/deployment.yaml` 을 YAML 로 파싱하면 `containers=['devpath-sandbox-svc']`, `initContainers=[]`, `volumes=['sandbox-runner-mtls']` — 113행의 `- name: sandbox-runner-mtls` 는 **볼륨**이다(runner 는 별도 Deployment `apps/devpath-sandbox-runner`). 따라서 "어느 컨테이너에 들어갔는가" 는 문제가 되지 않고, 새 테스트의 "서비스 이름 컨테이너 정확히 1개" 단언과도 맞다. 전제가 문서로 번지지 않게 적어 둔다.

### F8 · Info — 런 안의 계약 테스트는 자기 바이트에 대한 자가 점검이지 독립 경계가 아니다

- `03:83-88` 은 헬퍼 커밋 안의 테스트 파일로 같은 커밋의 워크플로를 검사한다. 헬퍼가 바뀌면 테스트도 같이 바뀔 수 있으므로 경계는 `08:137-142`·`08:178` 의 리뷰된 SHA 다. `--helper-sha` 는 인자로 받는다(다른 7개 좌표는 상수). 리뷰가 끝나 SHA 가 확정되면 다른 좌표처럼 상수로 박아 오퍼레이터 오타 경로를 없애는 것을 권한다(그러면 스크립트 단위 테스트 1건 조정).

### F9 · Info — `require_sealed_controls`(`08:109-119`) 는 룰셋을 (id, name, enforcement) 로만 본다

- 규칙 내용·bypass 배우는 보지 않는다. 그러나 런 안에서 `verify_gitops_write_authority.py` 가 push 직전 두 번 규칙 내용까지 검사하므로(Strengths 5) 스크립트 쪽은 사전 "형태 변화 감지" 로 충분하다. 변경 불필요.

---

## 3. Checked, no issue

- **패키지 ↔ 저장소 바이트**: `03`·`05`·`07`·`01`·`02`·`04`·`06`·`08`·`11` 전부 `cmp`/`diff` 동일(위 Strengths 1).
- **그래프·핀**: target 부모/트리, 헬퍼 부모/2경로, 디스패처 부모/1경로, `origin/fix/pipeline-defects-main-20260921` = `5961922b`, 로컬 헬퍼·디스패처 브랜치 = 각 SHA, `refs/remotes/origin/main` = `30c0e9f7`, 방아쇠 브랜치는 로컬·원격 어디에도 없음. 9/21 target `fcf97cf6` 은 `30c0e9f7` 의 조상(선례가 실제로 main 을 옮겼음).
- **목록 비교 블록**: 실제 `diff-tree` 바이트(`cat -A`)와 bash 재현으로 동등 확인, 행 수 12, 트리 순서 = 파이썬 정렬 순서(`05:177`), `diff.renames` 미설정이며 plumbing 이라 무관.
- **`git diff --check 30c0e9f7 5961922b`**: 깨끗함.
- **`03` 의 셸 구문**: 파이프 안 `grep` 없음, `$( )` 실패는 비어있지 않은 상수와의 비교로 fail-closed, `test -n` 이 두 목록 모두에 있음(`03:149,163`), here-string 만 사용, `${{ }}` 는 `run:` 본문에 없음(env·with 로만 전달, 값은 상수/`github.sha`/secrets).
- **step env 그림자**: `03` 의 step env 키는 `INPUT_FULL`·`GH_TOKEN`·`APP_ID`·`APP_SLUG`·`INSTALLATION_ID` 뿐 — 핀과 겹치지 않음. 워크플로 최상위 `env` 없음.
- **권한·동시성**: 최상위 `contents: read`, job `actions: read · contents: read · deployments: write`(GITHUB_TOKEN 으로 push 불가), App 토큰은 mint 이후에만, `concurrency.cancel-in-progress: false`, `GITHUB_RUN_ATTEMPT = 1`, preflight 의 바쁜 런 0 요구. 디스패처(`07`)는 `actions: write` 로 `workflow_dispatch` 만 호출하며 GITHUB_TOKEN 발 `workflow_dispatch` 는 새 런을 만든다(9/21 선례 `automation/dispatch-r2-unfence-main-publish` = `00c66257` 존재). `07` 은 9/21 실행본과 이름·브랜치·ref 4줄만 다름.
- **환경·승인 인증**(`03:90-119`): `can_admins_bypass=false`, custom branch policy 정확히 `branch:main`(= 헬퍼 정책이 복원된 뒤에만 통과), required_reviewers 1규칙·`prevent_self_review=true`·리뷰어 정확히 1명, 이 런의 승인 정확히 1건·approved·그 리뷰어·그 환경.
- **target 검사 step 순서**: SHA → 부모 → 트리 → subject/author/committer/email(2회) → 목록 → `diff --check` → 전체 테스트(`05:195` 가 순서 강제). `fetch-depth: 2` 로 부모가 있으므로 `rev-list --parents`·`diff --check MAIN TARGET`·`diff-tree HEAD` 모두 동작.
- **실행 스크립트 좌표 8줄**: 9/21 `run_r2_unfence_main_publish.py` 대비 docstring 1줄 + 좌표 7줄만 다름(documents `origin/develop` 로 diff). `CI_RUNS_PATH` 의 `ci.yml` 은 main 에 존재하고 `push: branches: [main]` 로 트리거된다.
- **preflight 순서**: 첫 쓰기(`08:206`) 전에 `08:133-160` 의 모든 읽기 + 스냅샷. 로컬 clone 으로의 `git fetch`(`08:151`)만 있고 원격 쓰기는 없다.
- **8개 Deployment**: 컨테이너 1개(서비스 이름), `startupProbe` 가 `readinessProbe` 직전, 값 5/60/3, 두 프로브 dict 불변, `progressDeadlineSeconds` 미설정(기본 600초 — resume 뒤부터 계산되며 pause 중엔 진행되지 않음), sandbox 만 `maxSurge 0 / maxUnavailable 1`. staging 은 별도 kustomization(`staging/mission-spine/kustomization.yaml`)에서 같은 base deployment 에 같은 `startupProbe` 를 strategic-merge 로 덧씌우므로 중복 없이 대체된다.
- **fence SA**: `imagePullSecrets` 최상위, `automountServiceAccountToken: false` 유지, Job(`job.yaml`) 은 바이트 불변(`prove_next_base.py:86` 이 단언). `10` 로그는 target 이 chain base 요건·shared 렌더 게이트를 통과하고 대조군 3건이 거부됨을 보여 준다.
- **커밋 메시지(`02`)**: liveness 산식(20+3×10≈50초)·5s×300s·"Readiness and liveness are unchanged"·12분40초·2분30초·"eight Deployments' pod templates change"·스펙 경로(documents `origin/develop` 에 실재, 부록 12) 전부 코드/기록과 일치. 사실 오류 없음. 날짜 `Mon Sep 21 2026` 은 실제 월요일.
- **`09`·`10` 로그의 의미**: `mutation_check.py` 는 워크플로 파일에서 target 검사 step 의 `run` 을 잘라 실제 bash 로 돌리고 xtrace 마지막 줄로 죽은 자리를 확인한다(A·B 는 목록 비교, C 는 트리 핀). `prove_next_base.py` 는 target 체크아웃의 실제 `verify_promotion_chain.py` 와 shared 의 `migration_release_gate.py` 를 import 해 돌린다. 로그의 주장과 스크립트 내용이 맞는다.
- **`11` 의 9종 변이**: 정의가 모두 실제 워크플로 텍스트에 1회 존재함(assert count==1)을 확인. `05` 가 각각을 죽이는 단언을 갖고 있음을 코드로 대조(step env 그림자 → `05:106-114`, strict mode → `05:116-126`, 행 삭제/빈 목록/비교 삭제/재할당/접두 비교 → `05:173-195`).
- **비밀 위치**: 실제 `mission-spine-auth-smoke.yml`(main) 의 두 잡과 promote/rollback 이 모두 `environment: mission-spine-production-off` 안에서 `secrets.GITOPS_RELEASE_APP_*` 를 쓰고, `docs/mission-spine-release-handoff-2026-08-17.md:118` 이 "환경 비밀" 로 적고 있다(라이브는 미확인 — 아래).
- **`.gitattributes`**: `.github/workflows/*.yml`·`scripts/release/*.py`·`tests/release/*.py` 는 `eol=lf` 이므로 ubuntu 러너에서 계약 테스트가 읽는 바이트 = 커밋 바이트.

---

## 4. Not checked

- **라이브 GitHub 상태**(룰셋 내용·환경 보호·비밀이 실제로 환경 스코프인지·App 설치 레포 목록): `gh`·네트워크 금지. 런 안의 `verify_gitops_write_authority.py` 와 스크립트 preflight 가 실행 시점에 다시 검사하므로 실행 전 `--preflight-only`(§12.5 ④)가 이것을 대신한다.
- **target 트리에서 `tests/release` 전체 354건 실행·`kubectl kustomize` 렌더 diff·actionlint**: checkout/worktree·kubectl 금지. §12.5 의 기록(354 OK·렌더 diff 7줄/2줄)을 코드 대조로만 확인했다.
- **`_probe_api` 라이브 호출**: 네트워크 금지. 홈 레포 `origin/develop` 에 라우트 파일이 있는 것까지만.
- **Argo CD 의 실제 버전과 `Suspended` health·self-heal 동작의 실측**: 클러스터 접근 금지. F3 의 권고는 Argo 기본 동작(3-way diff, Deployment health) 에 근거한 추론이다(추측: 표시).
- **`prove_next_base.py`·`mutation_check.py` 의 재실행**: 로그(`09`·`10`)는 오늘 것이지만 재실행은 worktree·kubectl 이 필요해 하지 않았다.

---

## 5. Assessment

**Ready to publish? = Yes** (지금 바이트 그대로 — `--helper-sha 3e67810471eaf90499e26134f2e76c942c25d711` 를 정확히 넘기는 조건).

근거: publisher 가 `TARGET_SHA` 이외의 것을 main 에 올릴 수 있는 경로를 찾지 못했다 — 핀은 job env 상수이고 push 는 그 SHA 의 FF 이며 룰셋·classic 보호가 push 직전 두 번 실증되고, 목록 비교 블록은 실제 `diff-tree` 바이트와 재현으로 맞았다. 발견은 Medium 1(계약 테스트가 push step 을 조각으로만 고정 — 리뷰된 헬퍼 SHA 핀이 상쇄) · Low 4(금지어 누락, §12.3 의 self-heal 관찰 창·정리 절차·되돌림 경로) · Info 4 이며, F3·F4 는 실행 절차 문구에 반영하고 F1·F2 는 헬퍼 커밋만 바꾸는 선택 사항이다(적용하면 `--helper-sha` 만 새 값이 되고 target·핀은 불변).
