# 핸드오프 2026-09-22 (새벽, 세션 종료) — 홈 #91 머지 완료 · gitops 결함 3건 publisher 준비 중(독립 리뷰 대기) · 운영 무접촉

> 앞 문서 `handoff-2026-09-21-night-session-close.md` 의 §2 ① 은 **끝났다**(아래 §1). 이 문서는 그 §2 ③(gitops 파이프라인 결함)을 publisher 로 올리는 작업의 중간 이관이다. §2 ②·④ 와 §3~§6 은 앞 문서가 그대로 유효하다.
> 설계·좌표·검증의 정본은 스펙 `specs/2026-09-20-gitops-main-promotion-via-publisher-design.md` **§12**(특히 §12.5), 절차는 계획 `plans/2026-09-21-gitops-main-pipeline-defects-via-publisher.md`(끝의 「실행 기록」), 스크립트는 같은 이름의 디렉터리다.

## 1. 지금 상태 (2026-09-22 세션 종료 시 실측)

| 영역 | 상태 |
|---|---|
| 운영(앱·홈·클러스터) | **이 세션이 바꾼 것 없음.** 앱 r3 mission-ON(gitops `main` = `30c0e9f717efaad9bd46d47721a61495f4093e96`) · 홈 배포 `005cf175-…` · 클러스터에는 읽기 전용 조회만 했다(8개 Deployment `paused` 없음 · 전 파드 재시작 0 · Argo 전부 Synced, `ollama-gpu` 만 Progressing · fence SA 의 수동 `imagePullSecrets` 생존) |
| **홈 #91** | **develop 머지 완료 `17be1b8a`**(2026-09-21T11:29Z). PR CI 4건 + develop push CI 녹색. 증거 커밋 3건(`772e8f6` candidate 바인딩 → `6fe017b` review-metadata 재바인딩 → `5d30e32` 테스트 핀). 핀된 컨테이너에서 다시 렌더한 **PNG 4장이 바이트 동일**해서 `approved` 를 사람 검토 없이 다시 묶을 수 있었다. 워크트리·로컬/원격 브랜치 삭제 |
| gitops target | `fix/pipeline-defects-main-20260921` = **`5961922b9a309055a75bc7302e5c852c5c51d59c`**(트리 `85d71a7f…`) — **push 됨**. `main` 의 단일 자식, 12경로 |
| gitops 헬퍼·디스패처 | 헬퍼 `3e67810471eaf90499e26134f2e76c942c25d711` · staged 디스패처 `cbf153840adfba33c3460de0ae653cf54a02b4e2` — **로컬 커밋만, push 안 함**(리뷰 뒤에). 방아쇠 브랜치 `automation/dispatch-pipeline-defects-main-publish` 는 **없다** |
| 독립 리뷰 | 세션 종료 시점에 **진행 중 — 결과를 받지 못했다.** 다음 세션이 처음부터 다시 돌린다(`…/REVIEW.md`) |
| 열린 PR | documents #163(이 문서가 실린 PR) 머지 뒤 전 레포 0 |
| 남은 워크트리(전부 `D:/workspace/dpa/.worktrees/`) | `gitops-pipeline-defects-dev`(`dev/pipeline-defects-content` `b1da15b`, 로컬 전용) · `-target`·`-scratch`(detached `5961922`) · `-helper` · `-dispatcher` — **다음 세션이 쓴다, 지우지 말 것.** `documents-pipeline-defects-publisher` 는 #163 머지 뒤 삭제 |

## 2. 다음 세션 착수점

**① 독립 리뷰를 다시 돌린다.** `plans/2026-09-21-gitops-main-pipeline-defects-via-publisher/REVIEW.md` — 입력 패키지를 git 에서 다시 만드는 명령과 지시문의 뼈대가 있다(이 세션의 패키지는 세션 전용 스크래치패드에 있었다). 시작 전에 `origin/main == 30c0e9f7…` 을 확인한다. **다르면 핀 전부 무효 — Part A 를 새 main 위에서 다시.**

**② 발견 사항 처리 → push → preflight.** Critical/Medium 은 변이·재현으로 먼저 확인한 뒤 고친다. 헬퍼가 바뀌면 로컬 헬퍼 커밋을 새로(단일 자식·정확히 2경로), target 이 바뀌면 `TARGET_SHA`·`TARGET_TREE` 와 모든 핀을 다시 렌더한다(이미 push 된 target 브랜치를 교체해야 하므로 사용자에게 알린다). 그 뒤 헬퍼·디스패처 push → `run_pipeline_defects_main_publish.py --preflight-only` + 음성 대조(틀린 `--helper-sha` → 첫 쓰기 전 거부).

**③ 확인 관문(스펙 §12.4) — "진행"을 main 이동의 승인으로 읽지 않는다.** 되돌릴 수 없는 지점을 요약해 선택지로 묻는다: main 이 r3 의 mission-on 에서 벗어나면 **다음 승격까지 r3 자동 롤백 레인이 닫힌다**(`mission-spine-rollback.yml` 이 `verify_promotion_chain.py --current origin/main` 을 돌리고 미등록 커밋을 거부) · 8개 서비스 순차 롤아웃 · sandbox 는 `maxSurge: 0` 이라 약 25초 끊긴다. 선택지는 "지금 실행" 대 "다음 릴리스 캠페인의 0단계로" — 준비물은 같다.

**④ 실행(Part B, 계획 문서 끝).** 핵심은 직렬화다: notification 하나를 먼저 `rollout pause` 하고 90초 관찰(Argo self-heal 이 `spec.paused` 를 되돌리지 않는지 — sync **전** pause 는 미실측) → 나머지 7개 pause → publisher → `main == target`·main CI → 템플릿은 바뀌었고 새 ReplicaSet 은 없음을 확인 → notification → ai → lcs → community → learning → sandbox → platform → gateway 순으로 하나씩 `resume` + `rollout status` + `restartCount == 0`. 실패하면 그 Deployment 를 다시 pause + 새 RS `scale 0`.

**앞 문서에서 넘어온 것**: landing 은 다음 릴리스 id 에(홈 develop → master 릴리스가 선행 — master 빌드에 `dist/_worker.js` 가 있어야 한다. 이번 target 이 올라가면 landing-last 가 `/api/invite-rounds` 를 직접 확인한다) · 증거 만료 ai-svc **10/08** · gateway 10/10 · platform 10/15 · admin 10/19 · 나머지 5개 10/21.

## 3. 이 세션이 확인한 사실 (다음 세션이 다시 재지 않아도 되는 것)

- JVM 서비스 8개 전부 `startupProbe` 없음, liveness `initialDelaySeconds: 20` + 기본값 → 약 50초에 kill. 프로브 블록은 8개가 바이트 단위로 같은 모양이다. staging 패치에는 같은 `startupProbe` 가 이미 있고 테스트가 "예산 ≥ 300초"를 단언한다 — 값은 거기서 가져왔다.
- **startupProbe 를 넣는 커밋은 그대로 sync 되면 herd 를 재현한다**(파드 템플릿 8개 동시 변경). 직렬화는 publisher 밖의 절차다.
- shared 마이그레이션 게이트는 렌더에서 **Job 문서만** 검사한다 → SA 에 `imagePullSecrets` 를 선언해도 걸리지 않는다. §11 의 우려는 해당 없음(실제 경로 `set-migration-release` → build → `validate-migration-render` 로 증명).
- landing smoke 의 실물: 운영 홈은 수락, 9/21 사고의 함수 없는 배포 `9814656f.devpath-home-page.pages.dev` 는 `HTTPError 404` 로 거부. `_NoRedirectHandler` 는 3xx/4xx 를 응답이 아니라 `HTTPError` 로 올린다.
- 홈 시각 증거 재바인딩 레시피(홈 #91): 바인딩 커밋 → 핀된 컨테이너에서 `visual:baseline:update`(직접 `docker run`, `run-visual-evidence-docker.mjs` 와 같은 마운트·`GIT_*`) → 테스트 핀 8줄 → **커밋한 상태로** `npm test`·`visual:contracts`·`visual:evidence:docker`. PNG 해시가 같으면 재승인 가능, 다르면 멈춘다.

## 4. 교훈

1. **증명 스크립트의 FAIL 은 먼저 "내가 맞는 검사를 골랐는가"를 묻는다.** `validate_base_migration_render` 가 target 을 거부했지만 main 의 렌더도 똑같이 거부됐다 — 그 함수는 릴리스 워크플로에 쓰이지 않는다. 호출부(워크플로)를 읽고 실제 경로로 바꿨다. 대조군(변경 전 상태)을 같이 돌리면 이런 오진이 바로 드러난다.
2. **Windows 체크아웃의 CRLF 물질화는 "정확 치환" 스크립트를 조용히 깨뜨린다.** gitops `apps/**` 와 documents 의 스크립트는 인덱스 LF · 작업 트리 CRLF 다. 원본은 `git show` 의 커밋된 바이트로 읽고, 작업 트리를 고칠 때는 LF 로 정규화 → 원래 양식으로 되돌려 쓴다. blob 의 LF 는 바이트로 단언한다.
3. **heredoc 안의 백슬래시는 또 깨졌다**(계획에 적어 두고도 한 번 밟았다 — `\\n` 이 실제 줄바꿈이 됨). 백슬래시가 든 코드는 Write/Edit 도구로만.
4. **xtrace 의 기대 문자열은 실제 trace 를 본 뒤에 확정한다.** `$'M\t…'` 는 실제 탭으로 찍힌다. 변이가 "FAIL" 로 나와도 rc 와 죽은 자리를 먼저 읽는다 — 살아남은 것이 아니라 기대 문자열이 틀린 것이었다.
5. **단일 자식이어야 하는 커밋은 리뷰 뒤에 push 한다.** 리뷰 뒤 수정이 커밋 교체를 뜻하면 push 를 미루는 것이 force-push 를 피하는 길이다.
6. 환경: `git worktree remove` 는 셸 cwd 가 그 안이면 내용만 지우고 빈 디렉터리에서 `Permission denied` → cwd 를 옮긴 뒤 `rmdir` + `worktree prune` · Git Bash 에서 `rev:.github/…` 인자는 `MSYS_NO_PATHCONV=1` · MSYS `grep $'\r'` 은 빈 패턴이 되어 전체 줄 수를 센다(CR 검사는 Python 바이트로) · gitops `tests/release` 전체는 이 PC 에서 약 10분(백그라운드로) · Docker Desktop 은 꺼져 있다 — exe 직접 기동 뒤 `docker desktop stop`.

## 5. 사람 단계

- (없음.) §2 ③ 의 확인 관문에서 실행 시점을 고르는 결정이 하나 온다.
- 앞에서 넘어온 것: 모바일 서명 시크릿 4종 이전 · YouTube 재업로드 · 로그인 캡처 · AdSense 결정.
