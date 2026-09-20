# 핸드오프 2026-09-20 (오후) — gitops main 승격 완료(publisher) · 다음은 릴리스 캠페인

> 직전 문서: `handoff-2026-09-20-s2a-publisher-prepared.md`(같은 날 오전 — 준비 완료 시점). 그 §3 의 Part B 를 이 세션이 실행했다.
> 설계·결과 = `specs/2026-09-20-gitops-main-promotion-via-publisher-design.md` §10 · 계획 = `plans/2026-09-20-gitops-main-promotion-via-publisher.md`
> (끝의 「리뷰 결과」·「실행 결과」). 이 문서는 **지금 어디까지 왔고 다음에 무엇을 하는지**만 고정한다.

## 1. 지금 상태 (세션 종료 시 실측, 2026-09-20)

| 영역 | 상태 | 식별자 |
|---|---|---|
| 앱·홈 운영 | **변화 없음** — `app.leva.ai.kr` 200 · `leva.ai.kr` 200(트리 변경이 `apps/` 밖이라 ArgoCD 동기화 대상 없음) | |
| gitops `main` | **승격됨** — S2a ①+②(모바일 없는 릴리스 계약 + 핀된 13-fixture ET13 카탈로그) | `69e7bd15570f5ba0f271c83b5bd46955cb249c8e` (트리 `7799cc07…`) |
| 봉인 | **풀지 않았다.** 룰셋 2종 active · `enforce_admins` true · 환경 `mission-spine-production-off` 허용 브랜치 `main` 단독(id `57524487`) · `prevent_self_review` true | 전부 불변 |
| publisher 실행 | `35491725505` success(14 step) · 디스패처 `35491720855` · main CI `35491763390` success | |
| gitops 열린 PR | **0** — #162 는 publisher 결과 링크와 함께 닫았다 | |
| gitops 증거 브랜치 | target · 헬퍼 · staged 디스패처 · `automation/dispatch-s2a-main-publish` — 지우지 않는다(선례도 전부 남아 있다) | |
| frontend `main` | `31a7785d` — **운영 미승격**(gitops 의 ET13 핀 커밋) | |
| **자동 롤백 레인** | **닫혀 있다** — `ms-20260916-community-ia`, 2026-09-20T05:28Z 부터 다음 릴리스 승격까지. 비상 수단은 수동 gitops | §3 |
| 세션 워크트리 | 0 | |

## 2. 이번 세션이 끝낸 것

핸드오프 §3 의 질문 5개를 닫는 설계(#150) → 계획(#151) → 준비 Part A(#152·#153·#154) → **실행 Part B**(이 PR). 하루 안에 설계부터 main 이동까지 갔다.
publisher 는 1회 실행으로 끝났다(재시도·`-v2` 없음). 독립 리뷰(Critical 0 · Major 2 · Minor 4)는 전부 변이로 재현한 뒤 반영했다.

## 3. 다음 세션 착수점 — **릴리스 캠페인** (롤백 레인이 닫혀 있는 구간이다)

사용자는 확인 게이트에서 **"지금 실행 — 사람 단계는 나중에"**를 골랐다(스펙 Q4 의 변경, 스펙 §10). 그래서 닫힌 구간의 길이는 **사람 단계의 일정**이 정한다.

순서(9/19 핸드오프 §4 그대로, `base_sha` 만 확정):

1. **[사람] N01 Cloudflare durable token** — landing-last 전까지. 명령은 frontend `docs/community-information-architecture/task.md` §5 N01.
2. frontend main `31a7785d` 에 대한 **ET13 baseline 봇 디스패치** — `automation/dispatch-<release_id>` 의 디스패처로(`gh workflow run` 직접 금지 —
   gh CLI 가 리뷰어 계정이라 self-review 가 된다), `current_user_can_approve` 확인, 취소한 대기 실행은 재확인.
3. **[사람] ET13 시각 승인**.
4. gitops candidate — **`gitops.base_sha` = `69e7bd15570f5ba0f271c83b5bd46955cb249c8e`**. 체인 검증기는 base 에서 walk 를 멈추므로 이 커밋의 제목이 미등록이어도 된다(스펙 §3.1).
5. **[사람] 수동 NVDA 증거** — 물리 Windows 호스트, 이제 레인 1개(`manual-nvda`).
6. 나머지 증거 → seal → promote → landing-last(prior deployment 기대값 `005cf175-6e3e-4400-a201-1987ce9d8d84`).

캠페인은 계획 문서가 없다 — brainstorming(bounded)부터. S3(웹 재구성 구현)는 여전히 S2 와 독립이고 계획 미작성이다.

**재개 명령**

```bash
export MSYS_NO_PATHCONV=1
G=D:/workspace/dpa/devpath-gitops; R=DevPathAi/devpath-gitops; git -C $G fetch origin
git -C $G rev-parse origin/main                       # 69e7bd15570f5ba0f271c83b5bd46955cb249c8e
gh api repos/$R/rulesets -q '.[] | [.id,.name,.enforcement] | @tsv'
gh api repos/$R/environments/mission-spine-production-off/deployment-branch-policies -q '.branch_policies[] | [.id,.name] | @tsv'   # 57524487 main
for s in in_progress queued waiting requested pending; do echo "$s=$(gh api "repos/$R/actions/runs?status=$s&per_page=1" -q .total_count)"; done
git -C D:/workspace/dpa/devpath-frontend fetch origin && git -C D:/workspace/dpa/devpath-frontend rev-parse origin/main   # 31a7785d…
```

## 4. 이번 세션(오후)의 교훈 — 오전분은 직전 핸드오프 §4

- **가짜 API 로 테스트한 스크립트의 실제 I/O 가장자리는 아무도 밟지 않는다.** 실행 트랜잭션은 승격·복원·승인을 다 끝내 놓고 사후 검증의 마지막 줄에서
  `leva.ai.kr is not 200` 으로 죽었다 — `urllib` 기본 UA(`Python-urllib`)에 Cloudflare 가 403 을 준다(curl·식별 가능한 UA 는 200). `_gh_api`·`_run` 은
  `--preflight-only` 가 live 로 지나갔지만 `_http_status` 는 한 번도 live 로 돌지 않았다. **읽기 전용 live 점검은 모든 가장자리를 한 번씩 지나가게 짠다.**
- **스크립트가 빨갛게 죽어도 순서를 지킨다**: 환경 정책부터 직접 확인(계획 Task 8 Step 2) → main → 실행 결과. 그리고 "사실상 성공"을 눈대중으로 선언하지 않고,
  결함을 고친 뒤 `--post-verify-only` 로 같은 코드 경로를 끝까지 통과시켰다.
- **"진행"은 맥락마다 다른 말이다.** 준비 완료 보고 뒤의 "진행"을 main 이동의 최종 승인으로 읽지 않고, 전제 재측정 → 되돌릴 수 없는 지점의 요약 → 선택지 질문을
  거쳤다. 그 질문에서 사용자는 설계 때의 결정(Q4)을 바꿨다 — 묻지 않았다면 드러나지 않았을 변경이다.
- 봇 디스패치 publisher 는 `prevent_self_review` 를 끄지 않고도 끝난다 — 9/12 선례의 승인 트랜잭션(`approve_pending_deployment.py`)은 이 경로에서는 필요 없다.
  환경 브랜치 정책이 열려 있던 시간은 디스패치~대기 진입의 수십 초였다.

## 5. 사람 단계

1. **N01 Cloudflare durable token** — landing-last 전. 롤백 레인이 닫혀 있으므로 일정이 곧 위험의 길이다.
2. **ET13 baseline 시각 승인** — 봇이 띄운 실행에서.
3. **수동 NVDA 증거** — 물리 Windows 호스트 · NVDA 2케이스 · `manual-at-nvda` 승인.
4. 9/19 핸드오프 §6 의 나머지: 모바일 서명 시크릿 4종 이전(그 전까지 frontend 환경 `manual-at-talkback`·`mission-spine-mobile-signing-android` 삭제 금지) ·
   YouTube 재업로드 · 로그인 캡처 · AdSense 결정. Codex 는 2026-10-19 까지 한도 소진.
