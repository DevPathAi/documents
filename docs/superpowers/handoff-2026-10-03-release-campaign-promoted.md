# 핸드오프 — 2026-10-03 릴리스 캠페인 `ms-20261002-ai-provider-fallback-gpu7b` 운영 반영 완료

> 앞 문서: `handoff-2026-10-02-release-campaign-privacy-blocked.md`(PR #199, develop `42414bc`).
> 작업 원장(단계별 실측 전부)은 git 밖
> `D:/workspace/dpa/.release-artifacts/ms-20261002-ai-provider-fallback-gpu7b/`
> (`PLAN.md` · `coords.json` · `promote.py` 등 하니스 · `step10-*.log` · 봉인 매니페스트 사본) — **지우지 말 것**.

---

## 0. 한 줄 요약

릴리스 **0~12단계 완주 — 2026-10-03 01:10Z 운영 반영 완료**. 체인 `phase=mission-on` · `writer_fence_active=false`.
운영에서 바뀐 것은 이미지 4개뿐이다 — **ai-svc** `eb6f3c2b→107fd20a` · **admin** `5847d5e9→4c93a285` ·
**web** off `8cdf906e→ed8ce273` / on `3a6ab8db→902f1ae1`. 나머지 7서비스·홈 dist·shared migration 은 r3 와 동일.
⚠ ai-svc 폴백 env 는 들어가지 않았다(§4) → 폴백 코드는 운영에 있지만 **꺼진 상태** = 이전과 같은 동작.

---

## 1. ⬅️ 다음 캠페인 첫 동작 — documents 도구 수정의 main 릴리스 (**candidate 만들기 전에**)

프라이버시 도구 수정(§2)은 **develop 에만** 있다(PR #200 → `9af1090`). main 릴리스는 **일부러 미뤘다**.

- **지금 하면 안 되는 이유 — 롤백 창**: `mission-spine-rollback.yml:100` 이 롤백할 그 릴리스를
  `verify_release_artifacts.py` 로 재검증하고, 이 검증기는 외부 증거마다 **현재** 보호 브랜치 head 가 봉인 당시
  source 와 같기를 요구한다(`:3344-3350`, `:3452-3475`). 실제 GitHub 데이터로 `validate_privacy_approval_trust` 를
  호출해 확인했다 — 지금은 통과, documents main 이 `9af1090` 이면 `privacy-approval: candidate source is not current main`.
- **언제 해야 하는가**: 다음 캠페인을 시작할 때, **candidate 를 만들기 전에**. candidate spec 의
  `analytics_privacy.approval_source_sha` 가 그 시점의 documents main SHA 에 묶이고, 프라이버시 워크플로가
  `GITHUB_SHA = approval_source_sha` 를 단언하기 때문이다(candidate 를 만든 뒤 main 을 움직이면 그 candidate 는
  `candidate approval_source_sha mismatch` 로 거부된다 — 2026-10-03 로컬 실측).
- **여유**: 지금 candidate 런 목록은 79건·1,030,159 B(상한 1,048,576). 다음 candidate 런 1건(약 +13 KB)까지는
  수정 없이도 통과하지만 **그 다음은 반드시 터진다**.

> 같은 원리로 **ai-svc main(`83cfe792`)·홈 master(`abdf57a7`)에 머지하는 것도 이번 릴리스의 롤백 워크플로를 막는다.**
> 롤백 창은 이 세 브랜치가 움직이지 않는 동안만 열려 있다.

---

## 2. 프라이버시 증거 차단 해소 (2026-10-02 정지 지점)

### 근본 원인 — 재현으로 확정

`tools/mission_spine_privacy_approval.mjs` 의 `discoverCandidateArtifact` 가 gitops candidate 워크플로의 완료 런
**전체**를 `per_page=100` 으로 읽는다. 캠페인이 쌓여 81건이 되자 응답이 **1,057,193 B** 로 `MAX_API_BYTES`(1 MiB)를
8,617 B 넘었다. main 버전 도구를 로컬에서 실제 좌표로 돌려 CI 와 **같은 오류**를 재현했다.

### 수정 — documents PR #200 → develop `9af1090`

쿼리에 `branch=release/candidate-<release_id>` 추가(같은 좌표에서 1건·14,463 B). candidate 워크플로가
`GITHUB_REF_NAME = release/candidate-$RELEASE_ID` 를 단언하므로 그 밖에서는 적격 런이 생길 수 없다 — 탐색 범위만 줄고
수용 조건은 그대로다. 실패 테스트 먼저(API 상한을 넘는 목록 모사) → 12/12, 실제 API 종단에서 spec `3423b8be…` 산출 확인.

### ★10/02 에 남긴 경로는 자기모순이었다★

10/02 핸드오프의 「documents 수정 → develop→main 릴리스 → 증거 재디스패치」는 **그대로 하면 안 되는 경로**였다.
candidate 의 `approval_source_sha` 가 documents main `7f732ac5` 에 묶여 있어, main 을 움직이는 순간 이미 봉인된
candidate 가 거부되고 성공한 증거 4건도 함께 무효가 된다(§1 과 같은 바인딩).

### 실제로 푼 방법 — 사용자 결정

도구를 바꿀 수 없으니 응답을 줄였다. gitops candidate 워크플로의 **failure 런 2건**을 삭제했다 —
`35551785909`(9/21 main 오디스패치) · `32639025910`(8/23 prod1), 둘 다 아티팩트 0개·적격 producer 아님.
목록이 예측과 바이트 단위로 같은 **1,030,159 B** 가 됐고, main 버전 도구로 로컬 `fetch-candidate` 통과를 확인한 뒤
재디스패치했다(승인 클릭을 태우기 전에 통과를 미리 확인 — `fetch-candidate` 는 environment 승인 **뒤**에 돈다).

---

## 3. 단계별 결과

| 단계 | 좌표 | 결과 |
|---|---|---|
| 7 프라이버시 | 런 `37075688806` · 디스패처 `db61841` | ✅ 아티팩트 `11256682077` · 승인 = AI 대행(사용자 명시 지시) |
| 8 validate/seal | 런 `37076440861` · 디스패처 `bfb1972`(봇) · staging 2건 AI | ✅ **sealed `25002f162a4115c32191b872cf2e65e85c7bce76`** · 매니페스트 `bc1d7c75…` |
| 9 사전 검증 | `promote.py preflight` | ✅ EXIT 0 · 이미지 9/9 · 체인 `phase=base` · TLS 3608d |
| 10 migration | shared 런 `37082702000` | ✅ 결과 아티팩트 `11259456271` |
| 10 promote-off | 런 `37082838228` | ✅ 게이트 배치→회수 · `→ e18752d → 22759fc → 7cd74ed` |
| 10 promote-on | 런 `37083400762` | ✅ canary 900s · staging rebaseline · `→ cea3610` |
| 10 landing | 런 `37084886615` | ✅ `mode=deploy` · Pages `087c9235-…` · 업로드 0 · 전파 경쟁 재발 없음 |

운영 런타임 최종 실측(SSH): web `902f1ae1` · admin `4c93a285` · ai-svc `107fd20a` · 나머지 7개 불변 · 10/10 1/1.
라이브: `/api/invite-rounds`·`/api/stats`·`/updates`·`/` 전부 200.

---

## 4. 이월 — gitops 변경은 여전히 운영 밖

10/02 의 구조적 발견 그대로다 — main PR 정책이 `apps/`·`scripts/release/` 등을 금지하고 룰셋 bypass 는 App 봇뿐이라
gitops PR #168(GPU 7b 폴백 env · `ollama-gpu` Recreate · landing 프로브 재시도 수정)은 **머지 불가로 열려 있다**.
운영 반영 경로는 App 봇 직접 push 뿐이고, 진행 여부는 사용자 결정 사항이다. 그 전까지 ai-svc 폴백은 꺼진 상태다.

---

## 5. 함정 (이번 세션)

- **Git Bash `MSYS_NO_PATHCONV=1`**: `git show origin/main:path` 에는 필요하지만, 켠 채 `git worktree add /d/…` 나
  `git -C /d/…` 를 하면 `D:/d/…` 로 간다. 경로 인자는 `D:/…` 형식으로 쓴다.
- **Windows 에서 `mission_spine_privacy_approval.test.mjs`**: `core.autocrlf=true` 로 워크플로 YAML 이 CRLF 가 되어
  YAML 정규식 테스트 2건이 수정과 무관하게 실패한다. `tr -d '\r'` 사본에서 돌린다(CI 는 LF).
- **`install_pinned_kustomize.py` 는 linux_amd64 전용** — `verify_release_artifacts.py` 전체를 Windows 에서 돌릴 수 없다.
  필요한 검사 함수만 import 해 실제 API 응답으로 호출하면 된다.
