# 정합성 3차 — Baseline SHA 고정

> 정합성 점검 3차(설계서 `docs/superpowers/specs/2026-07-18-consistency-round3-quality-audit-design.md`)의 기준선.
> Task 2~9 전부가 아래 SHA 표를 점검 기준 ref로 인용한다. **워킹트리·로컬 브랜치는 기준이 아니다.**

## 기준

- 각 레포 `git fetch origin` 선행 후 `origin/develop`(부재 시 `origin/main`)의 고정 SHA.
- 고정 시각: 2026-07-18 (본 세션 착수 시점).
- 대상: fetch 전체 21레포(코드 축 12 + documents + 참고 8).

## 방법

전 레포 fetch + SHA/최종커밋일 수집 (컨트롤러 직접 실행, PowerShell):

```powershell
$all = @('devpath-platform-svc','devpath-learning-svc','devpath-community-svc','devpath-sandbox-svc','devpath-ai-svc','devpath-lcs-svc','devpath-notification-svc','devpath-gateway','devpath-frontend','devpath-shared','devpath-svc-template','devpath-gitops','documents','prototype','storyboard','templates','workflow-dashboard','workflow-guide','.github','devpath-home-page','devpath-landing-page')
foreach ($r in $all) {
  $p = "D:\workspace\dpa\$r"
  git -C $p fetch origin --quiet 2>$null
  $ref = 'origin/develop'
  git -C $p rev-parse --verify --quiet origin/develop *> $null
  if ($LASTEXITCODE -ne 0) { $ref = 'origin/main' }
  $sha = git -C $p rev-parse --short $ref
  $d = git -C $p log -1 --format='%ad' --date=short $ref
  Write-Output "$r | $ref | $sha | $d"
}
```

미머지 원격 브랜치 수집:

```powershell
git -C <repo> branch -r --no-merged <기준ref>   # HEAD·develop·main 제외
```

## 실측

### 기준 ref SHA 표 (21레포)

| # | 레포 | 기준 ref | SHA | 마지막 커밋일 |
|---|------|----------|-----|---------------|
| 1 | devpath-platform-svc | origin/develop | `4c1ca4f` | 2026-07-18 |
| 2 | devpath-learning-svc | origin/develop | `0461c4f` | 2026-07-05 |
| 3 | devpath-community-svc | origin/develop | `043b830` | 2026-07-05 |
| 4 | devpath-sandbox-svc | origin/develop | `a6d802e` | 2026-07-04 |
| 5 | devpath-ai-svc | origin/develop | `69d5e0f` | 2026-07-04 |
| 6 | devpath-lcs-svc | origin/develop | `bd64ada` | 2026-07-04 |
| 7 | devpath-notification-svc | origin/develop | `0afddfd` | 2026-07-17 |
| 8 | devpath-gateway | origin/develop | `c8a1282` | 2026-07-01 |
| 9 | devpath-frontend | origin/develop | `e6be351` | 2026-07-18 |
| 10 | devpath-shared | origin/develop | `ff7f5a6` | 2026-07-17 |
| 11 | devpath-svc-template | origin/develop | `b6c33ee` | 2026-06-20 |
| 12 | devpath-gitops | origin/develop | `ece471d` | 2026-07-05 |
| 13 | documents | origin/develop | `12fa43b` | 2026-07-17 |
| 14 | prototype | origin/main | `f084364` | 2026-06-20 |
| 15 | storyboard | origin/main | `94fd94a` | 2026-06-20 |
| 16 | templates | origin/main | `cf43fe5` | 2026-07-02 |
| 17 | workflow-dashboard | origin/develop | `bb0c0c8` | 2026-06-17 |
| 18 | workflow-guide | origin/main | `87f3999` | 2026-06-20 |
| 19 | .github | origin/develop | `072b797` | 2026-07-02 |
| 20 | devpath-home-page | origin/develop | `d31c121` | 2026-07-14 |
| 21 | devpath-landing-page | origin/develop | `b725ef4` | 2026-06-24 |

**참고**: `origin/develop` 부재로 `origin/main`을 기준으로 쓴 레포 = prototype, storyboard, templates, workflow-guide (4개). 나머지 17개는 `origin/develop`.

## 불일치 후보

해당 없음. 본 보고서는 기준선(baseline) 고정 전용이며 불일치 식별은 축①~④(Task 2~6)의 소관이다. 각 축 보고서가 여기 고정한 SHA를 기준 ref로 인용해 불일치를 산출한다.

## 관찰

### 미머지 원격 feature 브랜치 (42번 §2.2 형식)

코드 축 12레포 + documents에 대해 `branch -r --no-merged <기준ref>`로 수집. 기준 ref에 아직 병합되지 않은 원격 브랜치:

| 레포 | 미머지 원격 브랜치 | base | 비고 |
|------|--------------------|------|------|
| devpath-frontend | `origin/feat/p7-landing-jaspr` | origin/develop | Jaspr 랜딩 잔재. PR #55 close됨(홈페이지는 devpath-home-page/CF Pages로 일원화), 브랜치는 보존. |
| devpath-svc-template | `origin/fix/ci-build-job-registry-auth` | origin/develop | CI 빌드 잡 레지스트리 인증 수정 브랜치. 미머지 — 축② 회귀/축③ 규칙에서 상태 확인 대상. |
| documents | `origin/docs/consistency-round3-spec` | origin/develop | **본 점검의 작업 브랜치(자신)** — 정상. reports·46·47을 여기 쌓아 Task 9에서 PR. |

그 외 코드 레포(platform·learning·community·sandbox·ai·lcs·notification·gateway·shared·gitops)는 미머지 원격 브랜치 없음(기준 ref가 최신).

### 워킹트리 dirty (점검 기준 제외, 위생 항목으로 별도 추적 — 설계서 §2.3)

- documents 미커밋 방치 3파일(2026-07-18 착수 시 워킹트리 관찰): `.tier1-baseline.md`, `docs/superpowers/plans/2026-06-24-landing-validation-test-plan.md`, `docs/superpowers/specs/2026-06-24-office-hours-landing-validation-design.md`. → Task 7 §9(위생)에서 처리안, Task 10 Step 4에서 실행.
- 대부분 레포 `.omc/`(oh-my-claudecode 세션 상태) untracked 오염 및 community-svc `.omc/state/*` 추적 여부는 축③(Task 4) 레포 위생 표에서 기준 ref 기준으로 확정한다.

### 판정 보류

- 위 SHA는 점검 시작 시점 고정값. 다른 세션이 점검 중 머지하면 낡을 수 있음 → Task 7 Step 2에서 종료 시 재fetch로 신규 머지 여부 확인 후 46번 §2에 주석(설계서 §5 리스크 완화).
