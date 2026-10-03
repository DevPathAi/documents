# 핸드오프 — 2026-10-02 릴리스 캠페인 `ms-20261002-ai-provider-fallback-gpu7b` (7단계에서 정지)

> 앞 문서: `handoff-2026-10-02-gpu-7b-fallback-and-spot-detection.md`(PR #198, develop `f38f1b9`).
> 작업 원장(단계별 실측 전부)은 git 밖
> `D:/workspace/dpa/.release-artifacts/ms-20261002-ai-provider-fallback-gpu7b/`
> (`PLAN.md` · `coords.json` · `baseline-diff.json` · 생성기 3종 · `evidence/`) — **지우지 말 것**.

---

## 0. 한 줄 요약

릴리스 **0~6단계 완주**, 7단계 증거 **4/5 success**(ET13 · Manual AT · 홈 dist · AI 평가).
★**남은 하나 — 프라이버시 증거가 릴리스 범위 밖의 도구 결함으로 막혔다**★ = **다음 세션 첫 동작**.
★**운영은 전혀 바뀌지 않았다**★(실측: `devpath-web` `3a6ab8db…` · `devpath-ai-svc` `eb6f3c2b…` 모두 옛 이미지).

증거 최종 상태(전부 attempt 1):

| 증거 | 런 | 결과 | 아티팩트 |
|---|---|---|---|
| ① frontend ET13 | `36928203046` | ✅ success | 4 |
| ② Manual AT (NVDA) | `36928206524` | ✅ success | 3 |
| ③ 홈 dist | `36928318123` | ✅ success | 1 |
| ⑤ AI 평가 | `36933014805` | ✅ success | 1 |
| ④ 프라이버시 | `36933008100` | ❌ **failure** | 0 |

★AI 평가는 **재디스패치로 성공**했다★ — §4-A 의 `candidate_spec_sha256` 수정이 효과를 본
증거다. 프라이버시만 그 수정과 **무관한 별개 도구 결함**(§1)이다.

---

## 1. ⬅️ 다음 세션 첫 동작 — 프라이버시 도구 결함 수정

### 증상

증거 ④ 프라이버시(documents `mission-spine-privacy-approval.yml`)가 **두 번 실패**했다.
1차는 내 디스패처 결함(§4-A), **2차는 입력이 올바른데도 실패**:

```
GitHub API /repos/DevPathAi/devpath-gitops/actions/workflows/mission-spine-candidate.yml/runs
  ?event=workflow_dispatch&status=completed&exclude_pull_requests=true&per_page=100&page=1
  response is too large
```

(2차 런 `36933008100` — env 로 `CANDIDATE_SPEC_SHA256: 3423b8be…` 가 **정확히** 전달된 것을 로그로 확인했다.)

### 원인

`documents/tools/mission_spine_privacy_approval.mjs`

| 줄 | 내용 |
|---|---|
| `:24` | `const MAX_API_BYTES = MIB;` — API 응답 1 MiB 한도 |
| `:1182` | `if (Buffer.byteLength(raw,'utf8') > MAX_API_BYTES) fail('… response is too large')` |
| `:1211` | `base.searchParams.set('per_page', '100')` |
| `:1483` | `path: /repos/${gitopsRepository}/actions/workflows/${workflowId}/runs?event=workflow_dispatch&status=completed&exclude_pull_requests=true` |

gitops 의 candidate 워크플로 런이 누적돼 `per_page=100` 응답이 1 MiB 를 넘었다.
★**캠페인이 쌓일수록 반드시 터지는 종류**★이고 이번 릴리스와 무관한 선재 결함이다.

### 수정안 (설계까지 끝냈다)

`:1483` 쿼리에 **`&branch=release/candidate-<release_id>`** 를 더한다.

근거: `gitops/.github/workflows/mission-spine-candidate.yml:42` 가
`test "$GITHUB_REF_NAME" = "release/candidate-$RELEASE_ID"` 를 단언하므로 **그 브랜치 밖에서는
적격 런이 생길 수 없다**. 따라서 이 필터는 의미상 정확하고 「적격 producer 정확히 1개」 제약을
약화시키지 않고 **오히려 강화**한다. 응답은 1~2개로 줄어든다.

`per_page` 축소는 **열등하다** — 페이지네이션이 필요해지고 적격 런이 뒤 페이지에 숨으면 못 찾는다.

### 경로

documents 코드 수정 → develop PR → **develop→main 릴리스 PR** → 머지 →
프라이버시 증거 **재디스패치**(디스패처 브랜치에 커밋 하나 더) → 재승인[사용자].
★워크플로가 `main` 에서 실행되므로 main 반영이 필수다★.
documents 에는 gitops 같은 main PR 정책이 **없다**(확인 필요하지만 r3 때 #133 이 develop→main 머지로 들어갔다).

**실패한 런은 적격 producer 가 아니다**(`completed/failure`) — 재디스패치해도 「정확히 1개」 규칙에
걸리지 않는다. 실측으로 확인했다.

---

## 2. ★★구조적 발견 — gitops 변경은 릴리스 PR 로 운영에 들어가지 않는다★★

앞 세션들이 gitops env 변경(#166 retention 폴백 · #167 GPU 7b 폴백)을 develop 에 머지하며
「운영 반영은 다음 릴리스」로 남겼다. **그 가정이 틀렸다.** PR #168 이 `BLOCKED` 되어 추적했다.

| 확인 | 실측 |
|---|---|
| 실패 메시지 | `main PR may not change the base-owned policy implementation: scripts/release/cloudflare_pages.py, scripts/release/provision_mission_staging.sh` |
| `verify_main_pr_policy.py` 금지 범위 | `.github/workflows/`·`.github/actions/`·`scripts/release/`·`tools/release-wrangler/`·`release-manifests/` · 서비스·web·migration `kustomization.yaml` · ★`apps/`·`argocd/`·`staging/` **전체**★ (예외 = `apps/devpath-migration/base/job.yaml` 의 일회성 inert suspend 하나) |
| 룰셋 | `mission-spine-main-governance`(rule `update`, **bypass = Integration id 4679079 뿐**, mode always) · `mission-spine-main-integrity`(deletion·non_fast_forward·**required_linear_history**) |
| 브랜치 보호 | `required_PR=true` · `enforce_admins=true` |
| main 에 push 하는 워크플로 | `mission-spine-promote.yml` · `mission-spine-rollback.yml` **둘뿐** |
| promote 가 main 에 쓰는 것 | `promote_service_digests.py`(서비스 9곳 `kustomization.yaml`) · `set_web_digest.py`(web `kustomization.yaml`) — `promote.yml:293-316` 의 **명시적 화이트리스트**. `deployment.yaml` 은 **절대 건드리지 않는다** |
| 선례 `5961922`·`5427fe1`·`8b01c02` | author·committer 모두 `devpath-gitops-release[bot]`, **단일 부모 = 직접 push**, 9/21·9/24 로 **정책 도입(8/17) 이후** |

**→ gitops 의 운영 매니페스트·정책 코드 변경은 App 봇(Integration 4679079) 직접 push 가 유일한 경로다.**
릴리스 파이프라인은 **이미지 다이제스트만** 운영에 반영한다. 설계 의도로 보인다 — 운영 매니페스트를
바꾸면서 그 변경을 심사하는 자기참조를 막는다.

**사용자 결정(2026-10-02)**: env 없이 릴리스 완주. `*_FALLBACK` 이 미설정이라 **폴백은 꺼진 상태 =
현재와 동일(무해)**이고, 나중에 env 가 들어가는 순간 ArgoCD 가 돌리며 활성된다.
⚠ landing 전파 경쟁 수정(#165)도 못 들어가므로 **11단계 게이트가 9/30 처럼 1차 실패할 수 있다**
(복구 = 재디스패치, `mode=reuse` 로 재배포하지 않는다).

**gitops PR #168 은 열어 둔 상태다** — 머지 불가이고, App 봇 경로가 정해지면 그 내용을 쓴다.

---

## 3. 릴리스 진행 기록 (0~6단계 완주)

릴리스 id **`ms-20261002-ai-provider-fallback-gpu7b`** · 범위 = 대기 5건 전부(사용자 결정) ·
승인 방침 = 9/20 방식(인증·staging·운영 관문은 AI, 시각·NVDA·프라이버시·AI 평가는 사용자).

| 단계 | 결과 |
|---|---|
| 0 머지 | ai-svc main **`83cfe792`**(squash) · frontend main **`a08feb6f`**(merge) · gitops **차단**(§2) |
| 1 좌표 | ai-svc 이미지 `sha256:107fd20a…` · web off `ed8ce273…`/on `902f1ae1…` · admin `4c93a285…` · raw review run `36918293674`/artifact `11191407144`/digest `09b692cc…` |
| 2 기준선 비교 | ★**104/104 무변경**(diff 0.000%)★ · 치수변화 0 · 추가·삭제 0 |
| 3 baseline 승인 | 승인 run `36922449776` · 아티팩트 **`11193625116`** digest `939e3a48…` |
| 4 provenance | visual `9d6674b2…`(file `d7fdac8b…`) · a11y `592a9174…`(file `5dc1badf…`) |
| 5 홈 preview | **`f563bd8d-1ec5-4898-badb-952119a54817`**(Preview) · `dist_sha256` `51e8ef83…` |
| 6 candidate | spec **`3423b8be5cde26420ed34f040447ce8db1ef516c7057ab76db7b57e5891a58a2`** · run **`36927122580`** · 아티팩트 **`11194227794`** |
| 7 증거 | **4/5 success** — ① ET13 ✅ · ② Manual AT ✅ · ③ 홈 dist ✅ · ⑤ AI 평가 ✅(재디스패치) · ④ 프라이버시 ❌(§1) |

### ★로컬이 CI 를 바이트 재현한다★ (세 가지로 실증)

| 대상 | 로컬 | CI | |
|---|---|---|---|
| web `main.dart.js` | `43bb86b90b2e1098…` | build marker 동일 | ★일치★ |
| admin `main.dart.js` | `920e390b6615dc0c…` | build marker 동일 | ★일치★ |
| 홈 `dist_sha256` | `51e8ef83…` 707,145B | r3 값과 동일 | ★재현★ |

홈은 업로드 로그가 `Uploaded 0 files (51 already uploaded)` 로 한 번 더 확인해 줬다.
`catalog_sha256`(`a3c338c6…`)도 재계산해 r3 와 일치했다 — **master 가 같은 커밋이면 홈 파생 좌표가
전부 같다**는 논증을 실증한 것이다.

### 2단계의 의미 — 왜 104/104 가 무변경인가

웹 헤더 좌우 정렬(#243)은 ET13 시각 기준선에 **전혀 나타나지 않는다**. fixture 104개가
`flutter_web_release_projection` 으로 **셸(헤더) 없이 본문만** 캡처하기 때문이다. 소스 SHA 가 바뀌어
웹 이미지 다이제스트는 새로 생겼지만 PNG 는 바이트 동일하다 — 모순이 아니다.

9/30 과 **정반대**다(그때는 104/104 가 *변경*이라 PNG 를 하나하나 봐야 했다). 이번 승인은 사용자가
「바뀐 것이 없음」을 확인하는 형식적 관문이었고, 그래도 새 release_id 의 승인 아티팩트 발급을 위해
반드시 필요했다(`validate_release_manifest.py:779` `baseline_status == "approved"`).

⚠ 부수 발견: **이 헤더 수정의 시각 효과는 ET13 이 포착하지 못한다**. 검증은
`dp_web_header_test.dart` 단위 테스트가 담당한다. 헤더가 보이는 fixture 추가는 별도 과제다.

### 6단계 — 생성기의 단언이 내 설계 오류를 잡았다

`baseline_set_sha256` 을 바뀔 것으로 기대했는데 **바뀌지 않았다**. 기준선 104/104 가 무변경이라
승인된 PNG 세트가 바이트 동일하고 그 세트 해시도 같다. 2단계 실측의 당연한 귀결이며
`baseline_approval_sha256`(승인 문서의 run_id·시각)만 바뀐다.

이번 변경 집합은 r3 보다 **좁고 한 군데 넓다**:
- 좁다 — 홈이 **완전 무변경**(source_sha·dist·렌더 좌표가 변경 집합에서 빠진다).
- 넓다 — ★`services.devpath-ai-svc`★ `54f634b8…`/`eb6f3c2b…` → `83cfe792…`/`107fd20a…`.
  **이번 릴리스의 주 목적**이고 r3 에서는 서비스가 하나도 바뀌지 않았다.

최종 변경 필드 **32개 = 정확히 기대 집합** · stale 스캔 0건 · CR 0.
로컬 관문 `validate_release_manifest.py` rc=0 · `verify_candidate_web_base.py` rc=0.

---

## 4. 내가 만든 결함 2건 (반복하지 말 것)

### A. ★증거 디스패처가 옛 `candidate_spec_sha256` 를 보냈다★

documents·ai-svc 디스패처가 r3 의 `ef51e3ef…` 를 그대로 보내 두 증거가 실패했다
(privacy: `response is too large` / ai-eval: `candidate discovery must find exactly one eligible
current successful run`).

**근원**: 선례를 훑을 때 쓴 grep 패턴 `"[a-z_]+":` 가 ★**숫자가 든 키
`candidate_spec_sha256` 을 매치하지 못해**★ 그 입력의 존재 자체를 놓쳤다.
`forbid` 목록에도 옛 spec sha 를 넣지 않아 잔존 스캔이 못 잡았다.

**수정**: 치환 추가(documents 2→3건·ai-svc 4→5건) + 렌더러에 ★**inputs 값 전수검증**★ 신설 —
렌더 결과의 모든 `"key": "value"` 를 파싱해 **이번 릴리스의 허용 집합에 없는 값이 있으면 실패**한다
(frontend 15개·documents 4개·ai-svc 5개 통과). 같은 누락이 구조적으로 불가능해졌다.

★**frontend 디스패처는 다시 push 하지 않았다**★ — ET13·Manual AT 가 이미 success 이고
재디스패치하면 **성공한 증거가 2개**가 되어 seal 이 막힌다. 임시 경로에만 렌더해 검증했다.

### B. 승인 CLI 명령을 틀리게 안내했다

`gh api -X POST … -F "environment_ids[]=<id>"` 로 안내했는데 **세 건 모두 처리되지 않았다**.
GitHub API 는 `environment_ids` 를 **정수 배열**로 요구하는데 `-F` 는 폼 인코딩으로 문자열을 보낸다.
★정답은 `approve_gate.py`★ — JSON body 를 `--input -`(stdin)로 보내고, 환경명·봇 actor·attempt 1 을
단언한 뒤에만 승인한다. 사용법: `approve_gate.py <repo> <run_id> <env> <comment>`.

---

## 5. 재사용할 함정 (이번 세션 실측)

- ★**`PATH` 의 `flutter` 는 3.47.2 라 `pub get --enforce-lockfile` 이 실패한다**★
  (`Unable to satisfy pubspec.yaml using pubspec.lock`). 핀 3.44.1 을 **절대경로**로 부른다:
  `D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin/flutter`
  (revision `924134a44c189315be2148659913dda1671cbe99` · dart 3.12.1 = ci.yml 핀).
  **`export PATH=...` 는 이 도구의 셸에서 유지되지 않는다.**
- ★**Windows 에서 슬래시 포함 상대경로를 Dart 도구에 주면 `startsWith` root 검사가 조용히 깨진다**★
  — 메모리 [[windows-dart-path-prefix-trap]]. `baseline-root` 는 **백슬래시 절대경로 +
  `MSYS_NO_PATHCONV=1`**. 그리고 `baseline-root` 는 `visual/` 만이 아니라 **아티팩트 루트 전체**다.
- ★**`MSYS_NO_PATHCONV=1` 없이 `git show <rev>:.github/...` 는 콜론이 `;` 로, 슬래시가 `\` 로
  변환돼 `ambiguous argument` 로 죽는다**★(점으로 시작하는 경로에서 발동).
- ★**`ai-svc` main 은 merge commit 이 금지돼 있다**(룰셋) — `--merge` 가 거부되고 **squash** 만 된다.
  frontend main 은 merge commit 을 허용한다★ → 레포마다 다르므로 머지 전에 확인한다.
  squash 때문에 develop 커밋이 main 에 남지 않아 다음 릴리스의 `develop..main` 비교가 과장된다
  (이번에 ai-svc 가 57커밋으로 보였던 이유).
- **`pkill -f <pattern>` 이 자기 SSH 명령줄에도 매치해 세션을 끊는다**(exit 255) →
  `pkill -f "ben[c]h\.py"` 처럼 패턴이 자기 자신과 겹치지 않게.
- `PYTHONUTF8=1` 없이 한국어를 `print` 하면 cp949 오류로 죽는다 — **파일 쓰기는 이미 끝난 뒤**라
  출력만 실패할 수 있으니 상태를 다시 확인한다.
- Node 스크립트의 상대 `import` 는 **스크립트 위치 기준**이다 — `/tmp` 에 두면 깨진다.
  절대 `file://` URL 을 쓴다.

### 멘토 테스트의 CI 환경 의존 실패 (PR #86 으로 수정)

`MentorExecutionCoordinatorTest > blockedSelfEmitter…` 가 `:231` 에서 **2회 연속** 실패했다.
`providerTimeout` 20ms 가 러너의 `workExecutor`(코어 1·최대 1·큐 1) 기동 지연보다 짧아, 작업이
`sendToken` 에 진입하기 **전에** 타임아웃이 발동해 `tokenSendEntered` 가 끝내 내려가지 않는다.

★**간헐 flake 가 아니라 환경 의존**이다★ — 같은 merge 트리를 로컬에서 5회 반복해 **5/5 통과**했고
CI 에서는 재실행해도 같은 줄에서 실패했다. **그래서 로컬 통과는 수정의 증거가 못 된다** —
검증은 같은 러너에서 build pass 로만 된다(#86 3m15s · #85 재실행 3m8s).
계약은 「차단된 self emitter 가 durable 타임아웃 취소와 admission 해제를 지연시키지 못한다」이고
절대 밀리초와 무관하므로 정책·대기를 5배로 뒀다(운영 코드 무변경).

---

## 6. 머지·산출물 목록

| 레포 | 커밋/PR | 내용 |
|---|---|---|
| devpath-ai-svc | **#86** → develop `c26bb6d` | 멘토 타이밍 테스트 CI 민감도 수정 |
| devpath-ai-svc | **#85** → main **`83cfe792`**(squash) | 릴리스(#83 폴백 코어 + #84 기능별 엔드포인트) |
| devpath-frontend | **#244** → main **`a08feb6f`**(merge) | 릴리스(#243 웹 헤더 좌우 정렬) |
| devpath-gitops | **#168** (열림·머지 불가) | env 폴백 활성 + landing 수정 — §2 |
| devpath-gitops | `release/candidate-…` `62863d7` | candidate spec |
| devpath-frontend | `automation/dispatch-…` `285a83c`→`f8ecab4` | baseline 승인 → 증거 디스패처 |
| documents | `automation/dispatch-…` `8e88e8e`→`60dd134` | 프라이버시 디스패처(+ spec sha 수정) |
| devpath-ai-svc | `automation/dispatch-…` `4ad4087`→`6fbe6f7` | AI 평가 디스패처(+ spec sha 수정) |

작업 원장의 생성기 3종(재사용 가능):
`build_candidate_spec.py`(변경집합 단언) · `render_baseline_dispatcher.py` ·
`render_evidence_dispatchers.py`(**inputs 값 전수검증 포함**) · `compare_baseline.py`(PIL 픽셀 비교).

---

## 7. 그다음 (프라이버시 수정 뒤)

1. 증거 ④⑤ success 확인 → **5/5**.
2. **8단계 validate/seal** — gitops 에 봇 디스패처를 올려 `mission-spine-validate.yml`(입력
   `release_id` 하나)을 띄우고 **`mission-spine-staging` 보호 관문 2건을 AI 가 승인**.
   ref 는 **`release/candidate-<id>`**(워크플로가 `:76`·`:341` 에서 그 브랜치를 체크아웃).
   성공하면 candidate 브랜치가 sealed 커밋으로 CAS-push 되고 sealed SHA 가 나온다(`:400-422`).
3. **9단계 promote 사전 검증** — `verify_service_image_evidence.py`(이름이 `preverify_service_images.py`
   가 아니다) · 체인 검증기가 현재 main `eb413814` 를 `phase=base` 로 수용하는지.
   ★validate 통과 ≠ promote 통과★.
4. **10단계 [확인 관문] 운영 변경** — `migration`(★새 SQL 0건이어도 필수★) → promote OFF →
   promote ON → canary 900s → staging rebaseline. 하니스는 `--confirmed` 없이 거부한다.
5. **11단계 [확인 관문] landing-last** — #165 가 못 들어갔으므로 1차 실패 가능(§2).
6. 12단계 기록.

**이월**: gitops env 반영(App 봇 경로) · Slack 회수 통지 수신처 · ET13 헤더 fixture 추가 ·
deferred Minor 8건.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
