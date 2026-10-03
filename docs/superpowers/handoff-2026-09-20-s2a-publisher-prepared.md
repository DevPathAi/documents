# 핸드오프 2026-09-20 — gitops main 승격 publisher **준비 완료**, 실행은 사용자가 정한 날에

> 직전 문서: `handoff-2026-09-19-night-s2-done-main-promotion-via-publisher.md`(그 §3 의 질문 5개를 이 세션이 닫았다).
> 설계 = `specs/2026-09-20-gitops-main-promotion-via-publisher-design.md` · 계획 = `plans/2026-09-20-gitops-main-promotion-via-publisher.md`
> (끝의 「리뷰 결과」 절 포함). 이 문서는 **지금 어디까지 왔고 다음에 무엇을 하는지**만 고정한다.

## 1. 지금 상태 (세션 종료 시 실측, 2026-09-20)

| 영역 | 상태 | 식별자 |
|---|---|---|
| 앱·홈 운영 | **변화 없음** — `app.leva.ai.kr` 200 · `leva.ai.kr` 200 | |
| gitops `main` | **손대지 않음** | `4f3ed64b2a148394eb0b8b3f5311e327f0edd759` |
| 봉인 | 룰셋 2종 active · `enforce_admins` true · 환경 `mission-spine-production-off` 허용 브랜치 `main` 단독(id `57524487`) · `prevent_self_review` true | 전부 불변 |
| gitops target 브랜치 | `fix/s2a-mobile-free-contract-main-20260920` — 봇 단일 커밋, 트리 `7799cc07…`(= #162 CI 347 OK 의 트리) | `69e7bd15570f5ba0f271c83b5bd46955cb249c8e` |
| gitops 헬퍼 브랜치 | `chore/s2a-mobile-free-contract-publish-20260920` — main + 1커밋·2경로(publisher + 계약 테스트 13건) | `00cafba86398ce6d644e619199b9e8a92d916710` |
| gitops staged 디스패처 | `chore/s2a-main-publish-dispatcher-staged-20260920` — **방아쇠 이름으로는 아직 push 하지 않았다** | `0c0c9cc8f82c3a6ede03ec7b0b075c5d158d44bc` (= `STAGED_SHA`) |
| 방아쇠 ref | `automation/dispatch-s2a-main-publish` — **없음**(0개) | |
| gitops 진행·대기 실행 | 0 (9/10 부터 방치됐던 publisher 대기 실행 `34422926318` 은 취소했다) | |
| gitops 열린 PR | #162 — 증거로 유지. publisher 뒤에 닫는다(계획 Task 9) | head `4f0ba69` |
| documents `develop` | 스펙 #150 · 계획 #151 · 실행 스크립트 #152 · 리뷰 반영 #153 · 이 문서 | `69faf55` + 이 PR |
| 세션 워크트리 | 0 | |

## 2. 이번 세션이 끝낸 것

- **설계 문답**(핸드오프 §3 의 5문): 체인 재검증 제거(`MAIN_SHA` 핀이 대신) · 트리 해시 핀 + 접두사 allowlist · **봇 디스패치 + 확인 1회 뒤 AI 승인**
  (`prevent_self_review` 불변) · 준비는 지금/실행은 사람 단계가 가능한 날 · Claude 새 컨텍스트 리뷰 + 기계 게이트.
- **계획 Part A(Task 0~6) 전부**: 방치 실행 취소 → target → 헬퍼 → staged 디스패처 → 실행 트랜잭션 스크립트 → 독립 리뷰 → 반영.
- **독립 리뷰**: Critical 0 · Major 2 · Minor 4, 전부 변이로 재현한 뒤 고쳤다(계획 문서 끝 「리뷰 결과」). 핵심 결론 — publisher 가 `TARGET_SHA` 가 아닌
  것을 main 에 쓰거나 단언을 건너뛰고 push 에 도달하는 경로는 없다.

## 3. 다음 세션 착수점 — **계획 Part B (Task 7~9)**, 사용자가 날짜를 정한 뒤

**전제(사람)**: ① N01 Cloudflare durable token 준비 ② 같은 날 ET13 baseline 시각 승인과 수동 NVDA 증거(물리 Windows 호스트)를 할 수 있을 것.
publisher 가 main 을 옮기는 순간부터 다음 릴리스 승격까지 `ms-20260916-community-ia` 의 **자동 롤백 레인이 닫힌다**(S2a 스펙 §2 에서 수용) —
그래서 같은 날 캠페인까지 이어 간다. 그 구간의 비상 수단은 수동 gitops.

**재개 명령**(계획 Task 7 Step 1 — 읽기 전용):

```bash
export MSYS_NO_PATHCONV=1
G=D:/workspace/dpa/devpath-gitops; D=D:/workspace/dpa/documents; R=DevPathAi/devpath-gitops
git -C $G fetch origin --quiet; git -C $D fetch origin --quiet
X="<이 세션의 Scratchpad directory>/s2a-main-publish"; mkdir -p "$X"
for f in run_s2a_main_publish.py test_run_s2a_main_publish.py; do
  git -C $D show origin/develop:docs/superpowers/plans/2026-09-20-gitops-main-promotion-via-publisher/$f > "$X/$f"
done
(cd "$X" && py -B -m unittest test_run_s2a_main_publish 2>&1 | tail -3)          # Ran 12 tests / OK
STAGED_SHA=$(gh api repos/$R/branches/chore/s2a-main-publish-dispatcher-staged-20260920 -q .commit.sha)   # 0c0c9cc8…
py -B "$X/run_s2a_main_publish.py" --repo-dir $G --staged-sha $STAGED_SHA --comment unused --preflight-only   # {"preflight": "ok", "helper_sha": "00cafba8…"}
```

preflight 가 `main moved` 로 실패하면 **이 핀들은 전부 무효다** — Part A 를 새 main 위에서 다시 한다(리뷰 포함).
통과하면 계획 Task 7 Step 2~3 → 사용자 "진행" → Task 8(트랜잭션 1회, 포그라운드) → Task 9(사후 검증 · #162 닫기 · 문서) → 곧바로 릴리스 캠페인
(9/19 핸드오프 §4: ET13 baseline **봇 디스패치** → 시각 승인 → candidate `gitops.base_sha` = `69e7bd15…` → NVDA → seal → promote →
landing-last, prior deployment 기대값 `005cf175-6e3e-4400-a201-1987ce9d8d84`).

## 4. 이번 세션의 교훈

- **재현이 기대와 다르면 재현부터 의심한다.** 리뷰의 Major(줄 계속으로 나눈 두 번째 push)를 변이로 재현하자 "CAUGHT" 가 나왔는데 가짜였다 —
  변이 스크립트를 Bash heredoc 으로 넘겨 백슬래시+줄바꿈이 글자 `\n` 이 됐고, 한 줄짜리 push 는 옛 테스트도 잡는다. Write 도구로 파일에 쓰고
  백슬래시를 `chr(92)` 로 만들자 MISSED 가 나왔다. 9/19 핸드오프 §5 의 같은 함정을 같은 주에 또 밟았다.
- **Bash 도구 안의 `( set -e; … )` 는 GitHub Actions 와 다르다.** 도구가 명령을 errexit 이 억제되는 문맥에서 감싸 실행해, 실패한 대입이 중단을
  일으키지 않는 것처럼 보인다. 셸 동작은 독립된 `bash -c '…'` 로 확인한다.
- **`mapfile -t x < <(cmd)` 는 cmd 의 실패를 `set -e` 로부터 숨긴다**(9/3~9/12 선례 publisher 전부에 있는 모양). `x="$(cmd)"` 대입은 숨기지 않는다.
- **서브에이전트의 "빈 응답"은 보고가 없다는 뜻이 아닐 수 있다.** 리뷰 에이전트는 14분 일하고 "완료." 만 돌려줬지만 보고 전문은 대화 기록의 중간
  메시지에 있었다. 기록 파일을 통째로 읽지 말고, assistant 텍스트 블록의 **길이만** 먼저 뽑아 위치를 찾은 뒤 그 블록만 꺼낸다.
  (소형 프로브는 정상 응답했다 — 긴 작업에서만 최종 응답이 빈다.)
- **헬퍼·디스패처 브랜치에는 CI 가 없다**(`ci.yml` = `push: main` + `pull_request`, 선례도 PR·CI 없이 갔다). 그래서 계약 테스트를 publisher 가 첫
  단계에서 스스로 돌리고, 린트는 CI 와 같은 actionlint v1.7.12 를 체크섬 검증해 로컬에서 돌렸다(`D:/workspace/dpa/.worktrees/_tools/actionlint/`).
- gitops 에는 `tests/__init__.py` 가 없다 — `python -m unittest tests.release.x` 점 표기는 러너 site-packages 의 `tests` 에 가려질 수 있다. CI 와 같은
  `discover -s tests/release -p '<파일>'` 형식을 쓴다.
- documents 는 `__pycache__` 를 ignore 하지 않는다. 그 안에서 테스트를 돌릴 때는 `py -B`, 스테이징은 **파일을 하나씩 명시**한다(이번 세션에 pyc 2개가
  디렉터리 단위 `git add` 로 PR 에 들어갔다가 머지 전에 걷어냈다).
- 핸드오프의 숫자·명령도 실측 대상이다: 9/19 핸드오프의 "25개 경로"는 26행(`-M` 없이 27행)이었고, `rev-parse --short A B` 는 이 git 에서 동작하지 않으며,
  "진행 중인 실행 0"은 9/10 의 방치된 대기 실행을 놓친 값이었다.

## 5. 사람 단계 (9/19 핸드오프 §6 에서 달라진 것만)

1. ~~Codex 리뷰 수단~~ — 이번 publisher 는 Claude 새 컨텍스트 리뷰로 끝냈다. Codex 는 여전히 2026-10-19 까지 한도 소진(9/20 재실측).
2. **publisher 실행일 정하기** — N01 토큰을 먼저 받고, ET13 시각 승인과 NVDA 를 같은 날 할 수 있는 날.
3. 나머지(ET13 baseline 재승인 · 수동 NVDA 증거 · N01 · 모바일 서명 시크릿 이전 · YouTube 재업로드 등)는 9/19 핸드오프 §6 그대로.
