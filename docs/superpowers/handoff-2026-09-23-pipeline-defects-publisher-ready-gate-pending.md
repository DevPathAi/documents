# 핸드오프 2026-09-23 — gitops 결함 3건 publisher **준비 완료** · 확인 관문 대기 · 운영 무접촉

> 앞 문서 `handoff-2026-09-22-pipeline-defects-publisher-prepared-review-pending.md` 의 §2 ①②(리뷰 재실행 · 발견 처리 · push · preflight)가 **끝났다.** 이 문서는 §2 ③(확인 관문) 직전의 이관이다. 앞 문서의 §3(확인한 사실)·§4(교훈)와 그 앞 문서(`handoff-2026-09-21-night-session-close.md`)의 §2 ②④·§3~§6 은 그대로 유효하다.
> 정본: 스펙 `specs/2026-09-20-gitops-main-promotion-via-publisher-design.md` **§12**(§12.3 실행 절차 — 이번에 F3·F4·F5 반영, §12.5 좌표·검증), 계획 `plans/2026-09-21-gitops-main-pipeline-defects-via-publisher.md`(「실행 기록」 Task 7 · 편차 7~9), 리뷰 기록 `plans/2026-09-21-gitops-main-pipeline-defects-via-publisher/review-2026-09-23/`.

## 1. 지금 상태 (2026-09-23 세션 종료 시 실측)

| 영역 | 상태 |
|---|---|
| 운영(앱·홈·클러스터) | **이 세션이 바꾼 것 없음.** 앱 r3 mission-ON(gitops `main` = `30c0e9f717efaad9bd46d47721a61495f4093e96`) · 홈 배포 `005cf175-…` · 클러스터는 건드리지 않았다(조회도 안 함) |
| gitops target | `fix/pipeline-defects-main-20260921` = `5961922b9a309055a75bc7302e5c852c5c51d59c`(트리 `85d71a7f…`) — 9/22 push 본 그대로, 리뷰에서 변경 없음 |
| gitops 헬퍼 | `chore/pipeline-defects-publish-20260921` = **`046023061409ba534d3abce5523aaf348ad70dfc`** — **push 됨**(2026-09-23). 9/22 의 `3e67810…` 은 push 전에 교체(계약 테스트만 보강, 워크플로 blob `ef7b4def…` 불변, 부모 `MAIN_SHA`, 2경로) |
| gitops staged 디스패처 | `chore/pipeline-defects-publish-dispatcher-staged-20260921` = `cbf153840adfba33c3460de0ae653cf54a02b4e2` — **push 됨**(2026-09-23). 두 push 모두 워크플로 실행 0건 확인 |
| 방아쇠 | `automation/dispatch-pipeline-defects-main-publish` **없음**(그 이름으로 push = 실행) |
| 독립 리뷰 | **완료.** Ready to publish = **Yes**(바이트 그대로, `--helper-sha` 정확 전달 조건). Medium 1 · Low 4 · Info 4 — 전문 `review-2026-09-23/REPORT.md`. Medium(F1)·Low(F2)는 변이 16종으로 재현(전부 SURVIVED) → 계약 테스트 보강 → 25/25 killed. F3·F4·F5 는 스펙 §12.3 에 반영. 리뷰 전후 5개 레포 스냅샷 동일 |
| live preflight | **OK** — `{"preflight": "ok", "helper_sha": "0460230…"}`. 음성 대조(폐기된 `3e67810`)는 첫 쓰기 전 `helper branch moved away from the reviewed commit` 로 거부. 환경 정책 `branch:main` 단독 유지 |
| 열린 PR | 이 문서가 실린 documents PR 머지 뒤 전 레포 0 |
| 남은 워크트리(전부 `D:/workspace/dpa/.worktrees/`) | `gitops-pipeline-defects-dev`(`dev/pipeline-defects-content` `b1da15b`, 로컬 전용) · `-target`·`-scratch`(detached `5961922`) · `-helper`(`0460230`) · `-dispatcher`(`cbf1538`) — **Part B 가 쓴다, 지우지 말 것.** `documents-pipeline-defects-review-20260923` 는 PR 머지 뒤 삭제 |

## 2. 다음 세션 착수점 = 확인 관문 (스펙 §12.4 · 계획 Task 8 Step 4)

**되돌릴 수 없는 지점을 요약해 두 가지를 묻는다. "진행"을 main 이동의 승인으로 읽지 않는다.**

1. **실행 시점** — "지금 실행" 대 "다음 릴리스 캠페인의 0단계로". 준비물은 같다. main 이 r3 의 mission-on 커밋에서 벗어나면 **다음 승격까지 r3 자동 롤백 레인이 닫힌다**(`mission-spine-rollback.yml` → `verify_promotion_chain.py --current origin/main` 이 미등록 커밋을 거부). 8개 서비스 순차 롤아웃, sandbox 는 `maxSurge: 0` 이라 약 25초 끊긴다.
2. **되돌림 방식(리뷰 F5)** — (a) 보류로 충분(다시 pause + 새 RS `scale 0`, 옛 파드가 계속 서비스; 템플릿 되돌림은 또 한 번의 publisher) / (b) 실행 전에 되돌림 target(`TARGET_SHA` 의 자식, 8개 파일만 `MAIN_SHA` blob)과 헬퍼를 미리 만들어 둔다(준비 1세션 추가).

답을 받으면 **Part B**(계획 문서 끝): B1 preflight 재실행(`origin/main == MAIN_SHA` — 움직였으면 핀 전부 무효, Part A 를 새 main 위에서) + 클러스터 읽기 점검 → B2 notification 하나 pause + **강제 재조정**(`argocd.argoproj.io/refresh=hard`) 뒤 `spec.paused`·`Synced` 확인(기대 health 는 `Suspended`) → B3 나머지 7개 pause → B4 `run_pipeline_defects_main_publish.py --repo-dir D:/workspace/dpa/devpath-gitops --staged-sha cbf153840adfba33c3460de0ae653cf54a02b4e2 --helper-sha 046023061409ba534d3abce5523aaf348ad70dfc --comment <…>` → B5 `main == TARGET` · 템플릿만 바뀌고 새 RS 없음 → B6 notification → ai → lcs → community → learning → sandbox → platform → gateway 하나씩 resume + `restartCount == 0` → B7 사후 → B8 기록. 방아쇠 push 뒤 멈추면 §12.3 의 정리 절차(보류 배포 거부 + 방아쇠 브랜치 삭제).

**앞에서 넘어온 것**: landing 은 다음 릴리스 id 에(홈 develop → master 릴리스 선행 — master 빌드에 `dist/_worker.js`; 이번 target 이 올라가면 landing-last 가 `/api/invite-rounds` 를 직접 확인한다) · 증거 만료 ai-svc **10/08** · gateway 10/10 · platform 10/15 · admin 10/19 · 나머지 5개 10/21.

## 3. 이 세션이 확인한 사실

- **계약 테스트의 "조각 문자열" 단언은 push step 의 변형을 못 잡는다.** 리뷰어의 변이(핀 재할당 · `pu""sh` · API PATCH · 토큰 받는 추가 `uses` · `|| :`/`true ||`)가 16종 전부 살아남았다. 보강 = mint 이후 step 을 리뷰된 문서와 dict 전체 동등으로, 게이트 4 step 본문을 줄 단위 정확 일치로, `set -e` 우회 철자·핀 재할당을 금지어로. 라이브 경계는 여전히 실행 스크립트의 `--helper-sha` 핀(리뷰어 F8) — 오퍼레이터가 `0460230…` 을 정확히 넘겨야 한다.
- **헬퍼·디스패처 push 는 아무것도 실행시키지 않는다** — 헬퍼 워크플로는 `workflow_dispatch` 전용, 디스패처는 방아쇠 브랜치 push 에서만, CI 는 main push 와 PR 에서만(그래서 target 브랜치 push 도 CI 를 안 돌려 preflight 의 "main CI 미실행" 조건이 성립한다).
- **Argo 의 기본 재조정 주기는 3분**(ApplicationSet 에 `selfHeal: true` 만, `timeout.reconciliation` 재정의 없음) — pause 뒤 "1~2분 관찰"은 관측이 비어 있을 수 있어 강제 재조정을 넣었다. pause 된 Deployment 의 Argo health 는 `Suspended` 다.
- **sandbox-svc 의 컨테이너는 1개** — 9/22 지시문의 "2개" 전제는 틀렸다(`sandbox-runner-mtls` 는 볼륨, runner 는 별도 Deployment).
- `steps.app_token` 문자열 출현은 7회(step 3개) — 보강 스크립트는 워크플로에서 세어 박는다.

## 4. 교훈

1. **리뷰어에게 줄바꿈 사실을 먼저 적어 주면 헛걸음이 사라진다.** 9/22 의 리뷰어는 "전 줄이 다르다"(CRLF/LF)에서 멈췄고, 9/23 지시문은 패키지 LF · 작업 트리 CRLF · `git show` 로 대조를 명시했다 → 리뷰어가 처음부터 `cmp` 로 바이트 동일을 확인하고 들어갔다.
2. **Medium 은 "재현 → 보강 → killed" 로만 닫는다.** 리뷰어의 변이를 그대로 하네스에 옮기니 SURVIVED 16 이 나왔고, 보강 뒤 25/25 killed 가 나왔다 — 보고서의 주장을 믿지 않고 두 번 잰 것이 판정의 근거다.
3. **리터럴은 손으로 치지 말고 리뷰된 바이트에서 뽑는다.** `strengthen_contract_test.py` 가 워크플로에서 step 문서·게이트 본문을 추출해 테스트에 박으므로 (렌더, 워크플로) 쌍에 대해 결정적이고, REVIEW.md 의 "렌더 = blob" 단언이 계속 성립한다.
4. `MSYS_NO_PATHCONV=1` 아래에서는 `/d/…` 경로가 git 에 그대로 넘어가 `cannot change to '/d/…'` 로 죽는다 — 그 셸에서는 `D:/…` 만.
5. 서브에이전트 리뷰 1건 = 약 32만 토큰·34분(44 tool uses). 세션 마무리 30분 규칙 안에서 리뷰를 돌리려면 세션 초반에 띄운다.

## 5. 사람 단계

- §2 의 확인 관문 답 2개(실행 시점 · 되돌림 방식). 그 밖에 없음.
- 앞에서 넘어온 것: 모바일 서명 시크릿 4종 이전 · YouTube 재업로드 · 로그인 캡처 · AdSense 결정.
