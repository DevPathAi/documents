# 핸드오프 — 작업트리 정리에서 미푸시 실작업 11건이 나왔다, 백로그 재정돈

- 작성일: 2026-08-20
- 이전 핸드오프: `handoff-2026-08-19-track-expansion-complete.md`
- **릴리스 통제는 이번에도 한 글자도 바뀌지 않았다.** 재개 순서 1번(사람)은 그대로 유효하다.

## 한 줄 요약

정리 작업으로 시작했는데 **정리 대상 안에 푸시도 PR도 없는 실작업 11건이 들어 있었다** — ET2·ET3·ET8
Mission Spine 구현이 이 머신에만 있었다. 원래 설계대로 지웠다면 잃었다. `git bundle`로 오프라인 보존했다.

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

## 2. ★정리 대상 안에 미푸시 실작업 11건이 있었다★

`.worktrees/` 81개를 정리하려고 안전성을 재는 과정에서 드러났다. 세 겹으로 걸러야 보였다.

### 판정 방법 — 세 단계가 각각 다른 것을 잡는다

1. **`merge-base --is-ancestor`** (main/master/develop 포함 여부) → 절반이 `NO`로 나온다
2. **원격 ref 포함 여부**(`branch -r --contains`) → 22건이 남는다
3. **`git cherry`(patch-id)** → 실제 고아는 훨씬 적다. `feat/mission-spine-et11-mobile` 6커밋은 전부
   `-`(반영됨) — **리베이스 머지라 로컬 SHA만 다르다.**

★**1·2단계만 보면 "미머지"로 오판한다**★ — patch-id 비교까지 가야 리베이스 머지를 구분한다.

### 그런데 patch-id `+`도 "필요한 작업"의 증거는 아니다

`+`가 나온 것들이 develop에 **다른 구현으로 이미 들어갔을 수 있다.** 그래서 기능 단위로 직접 쟀다
(대조군 먼저 세운 뒤):

| 측정 | 대조군 | 실험군 |
|---|---|---|
| develop 파일 존재 | `ThisWeekView.java`·`ReviewService.java` **있음** | 고아 커밋 산출 테스트 8/9 **없음** |
| `SandboxClient.java` 토큰 배선 | `/internal/sandbox/...` URI 2건 검출 | `X-DevPath-Internal-Token` **0건** |
| `application-test.yml` flyway | `enabled`·`locations` 절 **있음** | `postgresql.transactional-lock` **없음** |
| community `@Put/@DeleteMapping` | `@PostMapping` `CommunityController` 7건 | **0건** |

결론: **develop에 없다.** 폐기된 초안이 아니라 미완의 실작업이다.

### 목록 — 전부 PR 없음(`gh pr list --state all` 0건), 푸시조차 안 됨

| 레포 / 브랜치 | 고아 커밋 | 내용 |
|---|---|---|
| learning-svc `feat/mission-spine-et2-claim` | 1 | guest 진단 이행 DB 멱등화. **1,110줄 · 테스트 7클래스** |
| learning-svc `feat/mission-spine-et3-current-mission` | 2 | 현재 미션·완료 계약 고정. 872줄 |
| ai-svc `fix/et8-review-idempotency` | 1 | 중복 소비 provider fence. 619줄 |
| ai-svc `fix/et8-internal-token-client-ai` | 1 | `X-DevPath-Internal-Token` + 토큰 없으면 생성자에서 throw(fail-closed) |
| lcs-svc `fix/et8-internal-token-client-lcs` | 1 | 같은 계열 |
| community·lcs·learning·notification·platform `fix/et8-flyway-transactional-lock-*` | 2·1·2·2·2 | `flyway.postgresql.transactional-lock: false` + 계약 테스트 |
| frontend `feat/mission-spine-et13-frontend-repro` | 1 | 재현성 계약. **다른 5커밋은 반영됨**(파일은 develop에 있음) |

### 보존 조치 — `git bundle` (원격 무접촉)

`.artifacts/unpushed-bundles-20260820/` 에 브랜치당 번들 1개 + 미커밋 패치 1개.

- `git bundle create <f> <branch> --not origin/develop` (thin, 1~27KB)
- **verify 11/11 통과**
- **실복구 테스트**: 새 클론에 `git fetch <bundle> 'refs/heads/*:refs/heads/restored/*'` →
  `ClaimConcurrencyTest.java` 7,914바이트 실재 확인
- **선행 커밋 11/11이 원격에 존재** → GitHub 재클론 + 번들 적용만으로 완전 복구된다

HOLD 걸린 Mission Spine 범위라 푸시·PR·머지는 하지 않았다.

★**`git bundle verify` 출력 파싱을 두 번 틀렸다**★ — `requires this ref`(단수)라 `these`를 요구한
정규식이 선행 0개로 읽었고, 그 앞에는 `grep -oE '[0-9a-f]{40}'` 첫 줄이 **브랜치 팁**을 집어 왔다.
확실한 방법 = `bundle list-heads`로 포함 ref를 구해 `comm -23`으로 뺀 나머지가 선행이다.

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
4. **미푸시 11건 처리 방향 결정** — §2. 번들로 보존했을 뿐 아직 살릴지 버릴지는 미정이다.

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
