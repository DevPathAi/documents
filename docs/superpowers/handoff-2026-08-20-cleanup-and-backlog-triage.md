# 핸드오프 — 작업트리 81→17, 「미푸시 11건」 오판 정정, 릴리스 게이트의 실재하는 구멍

- 작성일: 2026-08-20
- 이전 핸드오프: `handoff-2026-08-19-track-expansion-complete.md`
- **릴리스 통제는 이번에도 한 글자도 바뀌지 않았다.** 재개 순서 1번(사람)은 그대로 유효하다.

## 한 줄 요약

작업트리 81→17 정리에서 브랜치 11개를 "푸시도 PR도 없는 실작업"으로 판정했으나 **그 판정은 틀렸다** —
`origin/develop` 하고만 대조했고 **열린 PR 11건의 head 와는 대조하지 않았다.** 전수 재대조 결과 11건
전부 추월당한 초안이다(§2).

진짜 고유했던 것은 **shared 미커밋 23줄 하나**였고, 그 안에 **보안 강화 둘과 보안 완화 하나가 섞여**
있어 셋으로 분리했다(§2-B). 그 과정에서 **릴리스 통제에 실재하는 구멍**이 드러났다 — 보호 환경
두 곳 모두 `can_admins_bypass=true` 다.

---

## 1. 릴리스 통제 재측정 (2026-08-20)

| 확인 | 값 | 08-19 대비 |
|---|---|---|
| 조직 초대 `qahnaarin` | 목록에 그대로 (08-17 20:18 생성, 미수락) | 변화 없음 |
| 조직 멤버 | `VelkaressiaBlutkrone` 1명 | 변화 없음 |
| shared 저장소 초대 | 미수락 (08-17 11:28) | 변화 없음 |
| 보호 환경 reviewer | 두 환경 모두 `["VelkaressiaBlutkrone"]` | 변화 없음 |
| shared #67 / gitops #59 | 둘 다 `open` / `blocked` | 변화 없음 |
| 게시 버전 | `0.0.1-SNAPSHOT` 뿐 | 변화 없음 |
| 실행 EC2 | `t3.xlarge / devpath-k3s` (2d) 하나 — GPU 노드 없음 | 변화 없음 |

조직은 `DevPathAi`다(`leva-devpath` 아님 — `gh api` 호출 시 주의).

### 왜 초대 수락 없이는 못 푸는가 — 게이트가 둘이고 둘 다 자기 승인을 막는다

08-20에 차단 메커니즘을 직접 조회했다. "사람이 해야 한다"는 절차 문제가 아니라 **구조**다.

**게이트 A — main 브랜치 보호(PR 승인)**. `devpath-shared` main:

```
required_approving_review_count: 1
enforce_admins:                  true      ← 소유자 권한 우회도 닫혀 있다
require_last_push_approval:      true
required_status_checks:          ["build"]
```

#67 작성자 = `VelkaressiaBlutkrone`, 리뷰 `[]`, 결정 `REVIEW_REQUIRED`. **GitHub 는 PR 작성자의
자기 승인을 구조적으로 막는다**(설정이 아니라 규칙). 조직 멤버가 1명이라 승인 가능한 사람이 0명이다.
`devpath-gitops` #59 도 **완전히 같은 구조**다(작성자 동일 · `count: 1` · `enforce_admins: true`).

**게이트 B — 보호 환경 배포 승인(마이그레이션 실행·패키지 게시)**:

```
mission-spine-migration-release      : required_reviewers, prevent_self_review: true, reviewers=[VelkaressiaBlutkrone]
mission-spine-shared-package-publish : required_reviewers, prevent_self_review: true, reviewers=[VelkaressiaBlutkrone]
```

워크플로를 트리거하는 사람이 곧 유일한 reviewer라 `prevent_self_review: true` 가 승인을 막는다.
**게시가 SNAPSHOT 에 멈춰 있고 서비스 8개 PR build 가 전부 실패하는 근본 원인이 여기다.**

★**두 게이트는 독립이고 해소 주체가 다르다**★ — A 는 사람(qahnaarin 이 #67 승인), B 는 에이전트
(환경 reviewer 목록에 qahnaarin 추가). 그런데 **B 는 A 의 선행 조건인 조직 멤버십이 있어야 먹는다**
(멤버가 아니면 PUT 이 200 을 반환하고도 조용히 버려진다 — 08-17 핸드오프 §5). 그래서 순서가 고정이다.

**완화 경로도 있다**(선택지로만 적어 둔다, 이번엔 쓰지 않았다): `prevent_self_review` 를 `false` 로,
`required_approving_review_count` 를 0 으로, 또는 `enforce_admins` 를 끄는 것. 릴리스 통제를 스스로
해체하는 셈이라 기본값은 아니다. 다만 **게이트 B 만 완화하고 A 는 유지**하는 부분 완화도 가능하다.

---

## 2. ★「미푸시 실작업 11건」은 내 오판이었다 — 열린 PR 11건에 이미 다 있다★

**2026-08-20 정정.** 이 절의 초판은 작업트리 11개가 "푸시도 PR도 없는 실작업"이라고 단정했다.
**틀렸다.** 나는 `origin/develop` 하고만 대조했고, **열려 있는 PR 11건의 head 와는 대조하지 않았다.**
작업은 푸시돼 있었다 — **다른 브랜치 이름으로.**

`gh pr list --head <branch>` 가 11건 모두 0을 반환한 것도 오판을 굳혔다. 그 브랜치 이름으로 PR 이 없는
것은 사실이지만, **같은 내용이 다른 브랜치 이름의 PR 로 이미 올라가 있었다.** 브랜치 이름으로 PR 을
찾는 것은 "작업이 푸시됐는가"의 측정이 아니다.

### 전수 대조 결과 — 11건 전부 추월당한 초안

| 검증 | 결과 |
|---|---|
| 11개 브랜치가 건드린 **모든** 파일이 대응 PR head 에 존재하는가 | **PR에없음 = 0** (전 브랜치) |
| 내용 일치 | **75파일 동일** |
| 내용 상이 | **21파일 — 전부 PR 쪽이 앞섬** |

대응 관계: `*-et8-flyway-*` 5건·`et2`·`et3` → 서비스별 `feat/mission-spine-immutable-image` PR
(platform #52 · community #35 · lcs #10 · learning #51 · notification #14) /
`fix/et8-internal-token-client-ai`·`fix/et8-review-idempotency` → ai-svc #35 `fix/et9-ai-release-gates` /
`fix/et8-internal-token-client-lcs` → lcs #10 / `feat/mission-spine-et13-frontend-repro` → frontend #133.

"앞섬"은 **로컬 blob 해시를 PR 히스토리에서 되짚어** 확정했다(로컬 버전이 PR 의 과거 커밋에 그대로
존재 = 명백히 추월됨). 되짚기가 안 된 4건은 diff 를 직접 읽었고 전부 **의도적 개선**이었다:

- `lcs SandboxClient`: 실패 시 빈 리스트 → **명시적 source failure 구분** + strict `JsonMapper`
- `ai-svc ReviewPersistenceService`: `isProcessing` → **리스 기반**
- `ai-svc application.yml`: `MENTOR_TIMEOUT` 하나 → `provider`/`request`/`sse` 3분할
- `frontend`: 고정 SHA 갱신

**→ 11개 브랜치 전부 「버린다」.** 살릴 것이 없다. 번들(`.artifacts/unpushed-bundles-20260820/`)은
남겨 두지만 복구용이 아니라 감사 흔적이다.

### 유지되는 교훈 — 판정 3단계는 여전히 필요하다

1. **`merge-base --is-ancestor`**(main/master/develop 포함) → 절반이 `NO`
2. **원격 ref 포함**(`branch -r --contains`) → 22건 잔존
3. **`git cherry`(patch-id)** → `feat/mission-spine-et11-mobile` 6커밋 전부 `-`(반영됨).
   **리베이스 머지라 로컬 SHA만 다르다**

★1·2단계만 보면 리베이스 머지를 "미머지"로 오판한다★ — 이건 맞았다.

★그런데 **3단계까지 통과해도 부족하다**★. patch-id `+` 는 "develop 에 없다"만 말한다.
**"어디에도 없다"를 주장하려면 열린 PR head 까지 대조해야 한다.** 이번 오판의 정체가 이것이다.
`origin/develop` 은 후보 집합의 일부일 뿐이다.

### 원래 절이 인용한 "기능 단위 측정"은 유효하지만 결론이 달랐다

대조군을 세운 그 측정들(`X-DevPath-Internal-Token` 0건 · `flyway.postgresql` 절 없음 등)은 **측정 자체는
옳았다** — develop 에 없는 것이 사실이다. 틀린 것은 **"develop 에 없다 ⇒ 어디에도 없다"** 라는 추론이다.

---

## 2-B. 유일하게 살아 있던 고유 작업 — shared 미커밋 23줄

작업트리 `shared-migration-result-evidence` 의 스테이징 변경 4파일 23줄만이 진짜 고유했다.
대조군을 세워 확정했다: `repositories: devpath-gitops` 가 develop 80행에 그대로 · `can_admins_bypass`
0건 · `admin-bypass-enabled` 0건 (대조군 `owner: DevPathAi`·`prevent_self_review`·`self-review-enabled`
는 모두 검출). 브랜치 `fix/migration-result-evidence` 자체는 PR #69 로 이미 머지됐고(`ca87a07` →
`a8ab541`), 이 23줄은 **그 뒤에 커밋되지 않은 채 남은 작업**이다.

### ★한 덩어리에 보안 강화 둘과 보안 완화 하나가 섞여 있었다★

셋으로 분리해 커밋했다(로컬 브랜치 `fix/migration-gate-split`, `origin/develop` 위):

| 커밋 | 내용 | 성격 |
|---|---|---|
| `041a2c3` | `validate_protected_approval` 이 `can_admins_bypass` 가 명시적 `false` 가 아니면 `GateError`. 속성 부재도 거부 | 보안 **강화** |
| `0ec0c2f` | 승인 게이트가 `GITHUB_RUN_ATTEMPT` 를 정확히 `"1"` 로 강제함을 고정(프로덕션 변경 0) | 테스트 **추가** |
| `3c196a0` | GitOps App 토큰의 `repositories: devpath-gitops` 고정 제거 | 토큰 범위 **완화** |

### ★릴리스 통제에 실재하는 구멍 — 환경 쪽 관리자 우회가 열려 있다★

```
브랜치 보호  main enforce_admins  = true    ← 잠김
보호 환경    can_admins_bypass    = true    ← 열림 (두 환경 모두)
```

Mission Spine 문서가 "관리자 우회는 대체 수단이 아니다"라고 적어 둔 원칙이 **코드로 강제되지 않고
있었다.** `041a2c3` 이 그것을 강제한다.

★**채택 순서가 있다**★ — 게이트를 먼저 넣으면 `can_admins_bypass=true` 인 현 상태에서 **릴리스가 즉시
실패**한다. **환경 설정을 `false` 로 먼저 바꾼 뒤** 게이트를 반영해야 한다.

### `3c196a0` 은 채택 전 판단이 필요하다

`repositories: devpath-gitops` 를 없애면 토큰이 `devpath-gitops` 한 곳이 아니라 **App 이 설치된 전
저장소**를 덮는다(권한은 `contents: write` 그대로). 워크플로가 런타임에
`/installation/repositories?per_page=100` 로 설치 범위를 검증하는 스텝을 이미 갖고 있어 정적 고정을
그것으로 대체하려던 것일 수는 있으나, **코드만으로는 의도를 단정할 수 없다.** 작성자 확인 필요.

### 검증

- 세 커밋 각각 커밋 직후 `python3 -m unittest discover -s tests/release -p 'test_*.py'` **44건 통과**
  (CI `ci.yml:42` 와 동일 명령)
- ★**판별력을 세 번 다 실측했다**★ — 가드를 임시로 지워 red 가 나는지 직접 돌렸다:
  `041a2c3` 제거 → `admin-bypass-enabled`·`admin-bypass-unknown` **2건** `GateError not raised` /
  `0ec0c2f` 의 대상(`expected_context` 의 `GITHUB_RUN_ATTEMPT`) 제거 → 값 5개 **5건** /
  `3c196a0` 되돌림 → `WorkflowContractTest` **1건**
- **분리 정확성**: 세 커밋 합의 파일 blob 해시 4개가 원본 스테이징 인덱스와 **전부 일치**
  (`21ab99a`·`d32948e`·`ba6c1de`·`4c43a72`) = 바이트 단위 동일, 잃거나 더한 것 없음
- **원격 무접촉**: 푸시 0건, `origin/develop` 은 `a8ab541` 그대로.
  **브랜치 upstream 을 끊어 뒀다** — shared `develop` 은 릴리스 PR #67 의 head 라 무심한 `git push`
  하나로 candidate 계약 밖의 변경이 릴리스에 실린다
- 패치: `.artifacts/shared-gate-split-20260820/` (`format-patch` 3개 + 슬라이스별 원본 패치)

### 이번에 새로 밟은 측정 함정 3개

- ★**`MSYS_NO_PATHCONV=1` 을 켜면 같은 셸의 `/d/...` 절대경로가 깨진다**★ — 변환이 꺼져 리터럴
  `/d/workspace/...` 가 전달되고 Windows 에 그런 경로는 없다. `gh api` 용으로 켠 변수가 뒤이은
  `git -C /d/...` 를 죽였다. **켜는 범위를 명령 단위로 좁힐 것.**
- ★**`git rev-parse '<rev>:<path>'` 의 인자가 MSYS 에 의해 변환돼 조용히 실패한다**★ —
  `origin/develop:.github/workflows/...` → `origin\develop;.github\workflows\...`. 실패한 명령의 빈
  출력을 `||` 분기가 **"0건 = 이미 반영됨"** 으로 읽어 **두 번** 틀린 결론을 냈다. 그 오탐이
  learning-svc `.gitignore` 를 "다름 1건" 으로도 만들었다(실제 차이 0).
- ★**Windows Python 의 `write_text` 가 `\n` 을 `\r\n` 으로 바꿔 `git apply` 가 거부한다**★ —
  `patch does not apply`. 원본은 LF 였다. `open(..., newline="")` 로 써야 한다.

---

## 3. 작업트리 81 → 17

**브랜치는 하나도 지우지 않았다.** `git worktree remove`는 브랜치를 삭제하지 않으므로, 커밋이 로컬
브랜치 ref로 도달 가능하면 작업트리 제거는 무손실이다. 보존 대상 12건 전부 도달 가능함을 먼저 확인했다.

- 제거 64개 / 보존 17개(Codex 재개용 5 + 고유 내용 12)
- 검증: 13개 레포 로컬 브랜치 수가 삭제 전 백업과 **전부 일치**
- 백업: 스크래치패드 `worktree-backup-20260820.txt`(경로 + 전 레포 브랜치 SHA 397줄)

### 함정

- ★**`git worktree remove`가 Windows에서 `Filename too long`으로 실패한다**★ —
  `frontend-et11-mobile`의 Gradle 산출물 경로가 243자
  (`firebase_messaging/.../FlutterFirebasePermissionManager$RequestPermissionsSuccessCallback.class`).
  해법 = PowerShell `Remove-Item -LiteralPath '\\?\D:\...' -Recurse -Force` 후 `git worktree prune`.
- `.omc/`(도구 산출물) 하나 때문에 remove가 막힌다 — 추적 파일 변경이 0인지 확인 후 `--force`.
- ★**작업트리 5개가 WSL 경로(`/mnt/d/...`)로 등록돼 있다**★ — Windows에서 `git -C <path>`가 전부
  실패하고 `worktree list`에는 나온다. **이 5개가 전부 고아 커밋 보유자였다.** 레지스트리 HEAD를
  `<repo>/.git/worktrees/<name>/HEAD`에서 직접 읽어야 판정된다. `worktree prune`을 돌리면 등록이
  사라지므로 **이 5개 레포에는 prune을 돌리지 않았다**(community·lcs·learning·notification·platform).
- 작업트리 2개가 `.worktrees/`가 아니라 **레포 안쪽 `devpath-*/.worktrees/`**에 중첩돼 있다
  (`ai-et8-review`·`shared-et8-review`). 상위 디렉터리만 세면 81이 아니라 79로 잘못 센다.

---

## 4. 백로그 재정돈 (실측 기반)

### 지금 가능 — 릴리스 통제와 무관

1. **`track_catalog.dart`에 2트랙 노출.** 현재 노출 6개(`BACKEND_SPRING`·`DEVOPS`·`FRONTEND_REACT`·
   `FULLSTACK`·`MOBILE_FLUTTER`·`PYTHON_BACKEND`) — `NODE_TYPESCRIPT`·`DATA_AI` 없음. DB CHECK와
   문항 800개는 이미 8트랙을 갖췄다.
   파일: `apps/web/lib/src/features/common/application/track_catalog.dart` + 같은 이름 테스트.
2. **글 수정·삭제 구현.** community-svc develop에 `@Put/@DeleteMapping` **0건** 확정.
3. **문항 사실 정확성 검수** 800문항. 구조·분포만 검증됐다.
4. ~~미푸시 11건 처리 방향 결정~~ — **완료. 11건 전부 「버린다」**(§2). 대신 **shared 게이트 3커밋의
   채택 판단**이 남았다(§2-B) — `041a2c3`·`0ec0c2f` 는 릴리스 후 PR, `3c196a0` 은 의도 확인 필요.
   그리고 **보호 환경 `can_admins_bypass` 를 `false` 로 바꾸는 것은 지금 가능하고 지금 하는 게 맞다**
   — 구멍이 열려 있는 상태이므로.

### 사람 대기

- **`qahnaarin` 초대 수락** → 재개 순서 1~4번 전부가 여기 막혀 있다
- GSC 등록 · 08-14 이월 육안 확인 3건

### 8/21 06:59 이후

- Codex 외부 리뷰 5건, **직렬로 작은 것부터**. 자산 온전 확인:
  작업트리 5개(`{ai-svc,shared,gitops,frontend,learning-svc}-codexreview`, HEAD
  `f39c54b`·`a8ab541`·`cfe5e3d`·`0c35edb`·`e9671e0`) · `codexreview-base`(learning-svc `a4da1c4` ·
  ai-svc `47031c0`) 전부 살아 있다. 지시문만 재작성하면 된다.

**왜 위임했고 왜 첫 시도가 죽었는지 — 재개 전에 반드시 읽을 것**(원문은 08-19 핸드오프 §4):

- **위임 근거**: 사용자 지시. 1인 조직이라 부계정 승인엔 독립 검토의 실질이 없다 →
  **실질 리뷰 = Codex / 형식 승인 = 별도 계정**으로 분리한다. 즉 `qahnaarin` 은 §1 게이트를
  형식적으로 충족시키는 쪽이고, 내용 검토를 대신하지 않는다.
- ★**첫 시도가 전량 실패한 원인 = 5건을 동시에, reasoning `max` 로 돌려 계정 한도를 소진한 것**★
  (측정된 4건만 986K 토큰 → `try again at Aug 21st, 2026 6:59 AM`). **「직렬로, 작은 것부터」는
  취향이 아니라 이 사고의 재발 방지책이다.** 재개할 때 같은 방식으로 다시 돌리면 또 날아간다.
- ★**산출 0건을 「산출됨」으로 오판했다**★ — `grep -c "## 판정"` 이 5건 모두 `1` 을 반환했는데,
  그 1건은 **내가 준 프롬프트의 출력 형식 예시가 에코된 것**이었다. 프롬프트 길이 이후 구간만
  다시 세니 전부 0. 재개 후 결과 판정은 **프롬프트 에코를 제외하고** 세야 한다.
- **대체재 없음**(실측): `gemini 0.42.0` + 무료 Code Assist OAuth =
  `IneligibleTierError: ... migrate to the Antigravity suite`, `GEMINI_API_KEY` 미설정이라 우회 불가.
- 그 밖의 Codex 함정은 08-19 핸드오프 §7 — `codex exec review --base` 는 커스텀 프롬프트와 병용
  불가 · `... | codex ... | tail` 의 `$?` 는 `tail` 것이라 즉사한 5건이 `EXIT=0` 으로 보였다.

### 릴리스 후

- GPU 노드 기동(쿼터 `L-3819A6DF`=4.0 승인) → gitops #59

### ★새로 나온 것 — frontend 라이브가 147커밋 뒤처져 있다★

`main...develop` 실측:

| 레포 | main만 | develop만 | 해석 |
|---|---|---|---|
| frontend | 0 | **147** | main 푸시에서만 배포된다 → **라이브가 147커밋 뒤** |
| gitops | 0 | 39 | 막힌 #59 |
| shared | 0 | 7 | 막힌 #67 |
| ai-svc | 9 | 15 | 미릴리스 15 |
| learning-svc | 10 | 8 | 미릴리스 8 |
| gateway·platform·sandbox·community·lcs·notification | 10·7·7·6·3·1 | 0 | 릴리스 머지 커밋(정상) |

★**main만 있는 커밋 수는 릴리스 머지 커밋 수다** — 이상이 아니다. 반대로 **`0 / N` 은 릴리스가 한 번도
안 됐거나 fast-forward라는 뜻**이고, frontend의 `0 / 147`이 실제 문제다.★

**track_catalog를 고쳐도 릴리스 없이는 이용자에게 안 보인다** — 두 작업이 묶여 있다.

---

## 5. 이번 세션에 확인된 사실 정정

- 로컬 컨테이너 `devpath-pg`·`devpath-redis` 정리는 **불필요했다** — Docker Desktop 데몬 자체가 꺼져
  있다(`dockerDesktopLinuxEngine` 파이프 없음). 리소스를 쓰지 않는다.
- 작업트리는 5개가 아니라 **81개**였다(상위 79 + 중첩 2). `*-codexreview` 5개는 그중 일부다.
- `2328af8`(두 HTML 색 팔레트) — **사용자 결정 = 유지.** revert 하지 않는다.
- ★**이 문서 초판의 §2 결론이 틀렸다**★ — 「미푸시 실작업 11건」은 열린 PR 11건에 이미 있는 초안이었다.
  `origin/develop` 만을 후보 집합으로 삼은 것이 원인이다. §2 를 정정판으로 교체했다.

---

## 6. 재개 순서

1. **[사람] `qahnaarin` 으로 조직 초대 + devpath-shared 저장소 초대 수락**
2. **[에이전트] 보호 환경 reviewer 에 `qahnaarin` 추가 후 재조회로 확인**(PUT 이 200 을 반환하고도
   조용히 버려진다 — 08-17 핸드오프 §5)
3. **[사람] `qahnaarin` 으로 shared #67 승인**
4. **[에이전트] #67 merge commit 병합 → 게시 승인·검증 → 서비스 8개 PR fresh rerun**
5. **[에이전트] GPU 노드 기동 → gitops #59 게이트 확인 → 릴리스**
6. **[8/21 06:59 이후] Codex 리뷰 재개**

1번이 막혀 있는 동안 릴리스 통제와 무관하게 진행 가능한 것은 §4 「지금 가능」 4건이다.

## 7. 참고

- 릴리스 통제: `devpath-gitops/docs/mission-spine-release-handoff-2026-08-17.md`
- GPU 노드 절차: `devpath-gitops/docs/runbook-k3s-bootstrap.md` 「GPU 노드 추가」
- 번들: `.artifacts/unpushed-bundles-20260820/` (git 추적 밖)
- 메모리: `devpath-track-expansion-python-backend` · `devpath-external-review-via-codex` ·
  `devpath-mission-spine-release` · `devpath-path-generation-async`
