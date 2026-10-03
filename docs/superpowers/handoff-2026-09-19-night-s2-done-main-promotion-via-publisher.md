# 핸드오프 2026-09-19 밤 — S2(모바일 분리) frontend·gitops develop 완료 · main 승격은 publisher 경로로

> 직전 문서: `handoff-2026-09-19-web-redesign-spec-and-mobile-split.md`. 이 문서는 그 §4(S2c-2 + S2a 쌍 설계)에서 시작한 세션의 재개 문서다.
> 설계의 원천은 `specs/2026-09-19-s2c2-s2a-drop-signed-mobile-and-gitops-mirror-design.md`(§8~§10 에 실행 결과)이고, 이 문서는 **지금 어디까지 왔고
> 다음에 무엇을 하는지**만 고정한다.

## 1. 지금 상태 (세션 종료 시 실측)

| 영역 | 상태 | 식별자 |
|---|---|---|
| 앱·홈 운영 | **변화 없음** — `app.leva.ai.kr` 200 · `leva.ai.kr` 200 | 9/16 승격분 그대로 |
| frontend `main` | 두 번 릴리스(#226 → #228). 모바일 없는 웹 릴리스 계약 + ET13 스키마 수정. **운영 미승격** | `31a7785d5f3c73563c8ddb61b69a7a0e07f65f16` (= gitops 의 ET13 핀 커밋) |
| frontend `develop` | main 과 내용 동일(main 이 릴리스 머지 커밋 5개 앞) | `4636fba` |
| gitops `develop` | S2a ①(#160) + ②(#161) 머지 | `9204c33fd0705e192b25efff2258911b649be884` |
| gitops `main` | **손대지 않음** — 봉인 그대로(룰셋 2종 active · `enforce_admins` true) | `4f3ed64` |
| gitops 열린 PR | **#162** `release/s2a-main-promotion`(head `4f0ba69`) — 정책 게이트에 막혀 머지 불가, **증거로 열어 둠**(§3) | CI: main 기준 전체 347건 OK |
| documents `develop` | 스펙·계획 4건·이 문서 | #143~#148 + 이 PR |
| 세션 워크트리 | 0 (각 레포 주 checkout 은 건드리지 않았다) | |
| 진행 중인 gitops 실행 | 0 | |

## 2. 이번 세션이 끝낸 것

| 단계 | PR | 요지 |
|---|---|---|
| 쌍 설계 | documents #143 | 핸드오프 §4 의 질문 5개를 닫음 — gitops 스키마 in-place · ET13 바이트 핀+파생 · gitops 2 PR + main 승격 1회 |
| S2c-2 | frontend #224 | 웹 릴리스 증거에서 서명 모바일·TalkBack 제거. NVDA 증거 JSON 은 불변, candidate `quality_evidence_inputs` exact-key |
| S2a ① | gitops #160 | 계약에서 `mobile_test_artifacts`·`manual-talkback` 제거(6 → 5 레이블, `schema_version` 1 유지). 검증기에서 약 600줄 삭제 |
| S2c-3 | frontend #225 | `apps/mobile`·`mobile.yml`·`mobile_source_guard.dart` 제거(−24,895줄). lock 은 모바일 전용 43개 제거뿐 |
| frontend 릴리스 | #226 · #227 · #228 | gitops 가 결속할 main 커밋을 만들기 위해 먼저 릴리스(사용자 결정). 중간에 frontend 스키마 결함을 고쳐 한 번 더 |
| S2a ② | gitops #161 | ET13 계약을 13-fixture 카탈로그·frontend main `31a7785d` 에 재결속, 8파일 바이트 핀 + `frontend_et13_contract.py` 파생 + 대조 테스트 + 진단 스냅샷 재생성 |

**S2b · S2c(1·2·3) · S2a(①·②)는 develop 기준으로 전부 끝났다.** 남은 것은 gitops main 승격과 그 뒤의 릴리스 캠페인이다.

## 3. 다음 세션 착수점 — gitops main 승격을 **publisher 경로**로 설계

**왜 PR 머지가 아닌가(실측)**: 승격 PR #162 에서 `mission-spine-main-pr-policy` 가 실패했다 —
`main PR may not change the base-owned policy implementation: release-manifests/…, scripts/release/…`. `scripts/release/verify_main_pr_policy.py`
(2026-08-17 도입)는 main 대상 PR 이 `.github/workflows/`·`.github/actions/`·`scripts/release/`·`tools/release-wrangler/`·`release-manifests/`
아래를 **일절 바꾸지 못하게** 한다. 이번 세션이 세웠던 "봉인 해제 + admin squash 머지"는 그 게이트를 넘어가는 방식이라 **쓰지 않는다**
(`plans/2026-09-19-s2a3-gitops-main-promotion.md` 상단의 정정 배너). 9/9~9/10 의 #146·#148·`db36521` 만 그 방식으로 들어갔고, 이후로는 쓰이지 않았다.

**정식 경로 = publisher**(9/3~9/12 의 main 통제면 커밋 전부, 참고 구현 `origin/chore/prod27r4-cloudflare-pagination-publish-20260912` 의
`.github/workflows/mission-spine-auth-smoke.yml`):

1. 현재 main 바로 위에 **작성자·커미터 `devpath-gitops-release[bot]` 의 단일 target 커밋**을 만들어 `fix/…-main-<날짜>` 브랜치로 올린다.
   내용은 #162 와 같은 트리여야 한다 — ①+② 의 diff(`988661b..9204c33`)를 main 에 `git apply --3way --index`(이번 세션에서 exit 0 · 충돌 0,
   ①+② 가 건드린 26개 경로 중 develop 과 다른 것은 원래 갈라져 있던 `tests/release/test_release_contract.py`·`test_release_hardening.py` 둘뿐).
2. main + 1커밋짜리 **헬퍼 브랜치** `chore/…-publish-<날짜>` 가 `mission-spine-auth-smoke.yml` 을 one-shot publisher 로 바꾸고 계약 테스트 1개를
   더한다. 선례의 publisher 는 actor·attempt 1·헬퍼 커밋의 정확한 2개 경로·`MAIN_SHA`·`TARGET_SHA`·target 커밋의 제목/작성자/경로 목록을 모두 단언한 뒤,
   target 에서 전체 스위트를 돌리고 → App 토큰 발급 → `verify_gitops_write_authority.py` → **`git push origin "$TARGET_SHA:refs/heads/main"`**(fast-forward)
   → push 뒤 재검증한다. **봉인은 풀지 않는다** — App 이 governance 룰셋의 유일한 bypass 주체다.
3. 보호 환경 `mission-spine-production-off`: 리뷰어 `VelkaressiaBlutkrone` · `prevent_self_review: true` · **허용 브랜치는 현재 `main` 뿐**(헬퍼 브랜치
   정책을 추가해야 한다) · `can_admins_bypass: false`. 선례는 디스패치 actor 와 승인자가 같은 계정이라 README 의 "AI-operated approval transaction"
   (`scripts/release/approve_pending_deployment.py` — `prevent_self_review` 만 잠시 끄고 승인한 뒤 `finally` 로 복원·검증)을 썼다.

**설계에서 닫을 질문**
1. 선례의 publisher 는 **진행 중인 승격 체인의 fix** 였다(`verify_promotion_chain.py` 에 제목·경로를 등록하고, 봉인된 릴리스를 데이터로 받아 체인을
   before/after 로 재검증). 이번 변경은 **체인 밖**이다(`ms-20260916-community-ia` 는 landing-last 까지 완료, 다음 candidate 의 `base_sha` 가 이 커밋
   이후). publisher 에서 체인 재검증 단계를 빼는가, "체인 밖 통제면 변경"의 등록 방식을 새로 두는가.
2. target 커밋이 25개 경로를 바꾼다(선례는 2~4개). publisher 가 경로 목록을 exact 로 단언하는 방식 그대로 갈 것인가.
3. 환경 브랜치 정책 추가·`prevent_self_review` 일시 해제는 운영 보호 설정 변경이다 — 어느 시점에 사용자 확인을 받고, 승인 클릭은 사람이 하는가
   승인 트랜잭션 스크립트를 쓰는가.
4. 머지 시점부터 다음 릴리스 승격까지 `ms-20260916-community-ia` 의 **자동 롤백 레인이 닫힌다**(사용자가 수용한 위험, 스펙 §2). 그 구간을 짧게 하려면
   publisher 직후 곧바로 릴리스 캠페인(ET13 baseline 승인 → candidate → …)으로 이어 가는 일정이어야 한다.
5. 독립 리뷰 수단: Codex CLI 는 **2026-10-19 까지 한도 소진**(무료 ChatGPT 계정 — 기본 모델 `gpt-5.6-sol` 도 거부, `-m gpt-5.5` 는 동작했었다).
   이 PC 의 서브에이전트 리뷰는 빈 응답이다(2회). publisher 는 이 캠페인에서 가장 민감한 단계다 — 리뷰 방식을 먼저 정한다.

**재개 명령**

```bash
export MSYS_NO_PATHCONV=1
G=D:/workspace/dpa/devpath-gitops; git -C $G fetch origin
git -C $G rev-parse --short origin/main origin/develop            # 4f3ed64 / 9204c33 이어야 한다
gh pr view 162 -R DevPathAi/devpath-gitops --json state,headRefOid  # OPEN / 4f0ba69…
gh api repos/DevPathAi/devpath-gitops/rulesets -q '.[] | [.id,.name,.enforcement] | @tsv'
gh api repos/DevPathAi/devpath-gitops/environments/mission-spine-production-off/deployment-branch-policies -q '.branch_policies[].name'
git -C $G show origin/chore/prod27r4-cloudflare-pagination-publish-20260912:.github/workflows/mission-spine-auth-smoke.yml | head -120
git -C $G show origin/main:scripts/release/approve_pending_deployment.py | head -60
```

## 4. 그 뒤의 순서

gitops main 승격(publisher) → frontend main `31a7785d` 에 대해 ET13 baseline **봇 디스패치**(`automation/dispatch-<release_id>` 의 디스패처, `gh workflow run`
직접 금지, `current_user_can_approve` 확인, 취소한 대기 실행은 재확인) → 사람의 시각 승인 → gitops candidate(`base_sha` ≥ 승격 커밋) → 수동 NVDA 증거
(이제 레인 1개)·나머지 증거 → seal → promote → landing-last(prior deployment 기대값 `005cf175-6e3e-4400-a201-1987ce9d8d84`). S3(웹 재구성 구현)는 여전히
S2 와 독립이고 계획 미작성이다.

## 5. 이번 세션의 교훈

- **같은 계열의 낡은 리터럴이 네 번 더 나왔다**(9/17 부터 세면 열한 번): gitops 테스트의 `len(quality) == 6`·sha 참조 13 · 검증기 오류 메시지의
  "all six"(Codex 적발, 단언하는 테스트도 없었다) · frontend `catalog.schema.json` 의 projection const(12-fixture 시절 값 — 카탈로그가 자기 스키마를
  통과하지 못했다, ET13 스키마는 기계 검증되지 않는다) · gitops `test_release_hardening.py` a11y 페이로드의 `case_count: 24`(무거워서 로컬에서 안 돌린
  모듈을 CI 가 잡았다). **개수는 메시지에서도 빼고, 한 파일 안에서도 레인마다 따로 있다.** 이제 gitops 는 fixture 목록·매트릭스·개수·표면을 핀 파일에서
  파생하고, frontend 는 스키마 최상위 const·배열 제약을 카탈로그와 대조하는 테스트를 갖는다.
- **잔존 grep 이 상류의 결함을 잡았다.** gitops 가 frontend 파일을 바이트 핀하자, 옛 해시를 찾는 점검이 frontend 스키마의 낡은 const 를 찾아냈다.
  그때 고치지 않았다면 나중에 gitops 재결속과 main 승격이 한 번 더 들었다.
- **계획의 전제는 실행 직전에 다시 잰다.** main 승격 계획은 "사람이 봉인을 풀고 머지한다"를 전제했지만(9/9 의 선례와 메모리의 "3중 해제" 기록),
  그 뒤에 정식 경로가 publisher 로 바뀌어 있었다. 봉인에 손대기 전에 PR 의 정책 체크가 알려 줬다 — **의도된 게이트의 실패는 우회할 대상이 아니라
  경로가 틀렸다는 신호다.**
- ET13 진단 실행은 PR 과 main push 에서만 돈다(`workflow_dispatch` 는 릴리스 입력 7개 필수). PR 실행의 증거 `source_sha` 는 임시 머지 ref 이고
  main push 실행의 `source_sha` 는 실제 커밋이다 → gitops 의 핀은 frontend **main 커밋**에 둔다.
- main 과 develop 이 갈라진 레포(gitops)에서 "develop 의 파일을 옮긴다"는 성립하지 않는다 — diff 를 패치로 적용하고, 경로별 블롭 일치로 확인한다.
- 도구: Codex 로그의 판정은 마지막 `^codex$` 마커 뒤 ~ `tokens used` 전이고, 중간에 죽으면 그 자리가 판정이 아니라 작업 메모다(`CODEX_EXIT` 와 함께 본다) ·
  `… | tail` 뒤의 `$?` 는 `tail` 의 것(이번에도 `git apply --check` 에서 걸릴 뻔했다) · Bash heredoc 안의 백슬래시 치환은 조용히 빗나간다(두 번) →
  스크립트는 Write 도구로 파일에 쓴다 · `git stash` 스택은 worktree 간 공유 · worktree 는 셸 cwd 를 밖으로 옮긴 뒤 지운다 · unittest 출력을 `tail -N` 으로
  자르면 `Ran/OK` 줄이 밀려 사라진다.
- 환경: 사용자의 게임(약 19GB)으로 메모리 압박이 심해 백그라운드 `until … sleep` 대기가 네 번 강제 종료됐다 → `gh run watch <run> --interval N --exit-status`
  를 포그라운드로 쓴다. gitops 전체 스위트는 CI 에서 1분 미만, 이 PC 에서 11~15분 — 로컬은 관련 모듈만, 전체는 CI 게이트로(단 무거운 모듈을 빼면 위의
  `case_count: 24` 같은 누락이 CI 에서야 드러난다).

## 6. 사람 단계

1. **Codex 리뷰 수단** — ChatGPT 플랜 업그레이드(결제) 또는 다른 외부 리뷰어. 2026-10-19 전에는 Codex 를 쓸 수 없다.
2. **publisher 의 보호 환경 승인** — `mission-spine-production-off`(설계에서 방식을 정한다, §3 질문 3).
3. **ET13 baseline 재승인**(시각 검토) — gitops main 승격 뒤, 봇이 띄운 실행에서.
4. **수동 NVDA 증거** — 물리 Windows 호스트 · NVDA 2케이스 · `manual-at-nvda` 승인.
5. **N01 Cloudflare durable token** — landing-last 전.
6. **모바일 서명 시크릿 4종 이전** — 모바일 독립 서명 파이프라인 설계 때. 그 전까지 frontend 의 GitHub 환경 `manual-at-talkback`·
   `mission-spine-mobile-signing-android` 는 **삭제하지 않는다**(환경 시크릿은 재조회 불가). 서명 워크플로·provenance 도구의 복구 지점은 frontend `db955eab`.
7. 이전 핸드오프에서 넘어온 것: YouTube 재업로드, 로그인 캡처, AdSense 결정.
