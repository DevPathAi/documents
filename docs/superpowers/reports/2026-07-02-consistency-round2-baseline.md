# 정합성 점검 2차 — 기준(baseline) 확정

> 작성일: 2026-07-02 / 스펙: ../specs/2026-07-02-consistency-refactor-round2-design.md

## 1. 레포별 점검 기준 ref
| 레포 | 기준 ref | SHA | 마지막 커밋일 |
|---|---|---|---|
| devpath-ai-svc | origin/develop | f36cca2 | 2026-06-26 |
| devpath-community-svc | origin/develop | 3f9783a | 2026-07-01 |
| devpath-frontend | origin/develop | 62c161e | 2026-06-27 |
| devpath-gateway | origin/develop | c8a1282 | 2026-07-01 |
| devpath-gitops | origin/develop | 728e5c1 | 2026-06-26 |
| devpath-landing-page | origin/develop | b725ef4 | 2026-06-24 |
| devpath-lcs-svc | origin/develop | 212e588 | 2026-06-26 |
| devpath-learning-svc | origin/develop | caec735 | 2026-06-25 |
| devpath-notification-svc | origin/develop | f76acfb | 2026-07-01 |
| devpath-platform-svc | origin/develop | 56bf8a6 | 2026-07-01 |
| devpath-sandbox-svc | origin/develop | ee212b7 | 2026-06-25 |
| devpath-shared | origin/main | a42f756 | 2026-07-01 |
| devpath-svc-template | origin/develop | b6c33ee | 2026-06-20 |
| documents | origin/develop | 099d333 | 2026-07-01 |
| prototype | origin/main | f084364 | 2026-06-20 |
| storyboard | origin/main | 94fd94a | 2026-06-20 |
| templates | origin/main | 687a178 | 2026-06-20 |
| workflow-dashboard | origin/develop | bb0c0c8 | 2026-06-17 |
| workflow-guide | origin/main | 87f3999 | 2026-06-20 |
| .github | origin/develop | 2a8fc05 | 2026-06-21 |

## 2. origin/develop 부재 레포

다음 레포는 `origin/develop`이 없으며 대체 기준을 사용함:
- **devpath-shared**: 대체 기준 `origin/main` (SHA: a42f756)
- **prototype**: 대체 기준 `origin/main` (SHA: f084364)
- **storyboard**: 대체 기준 `origin/main` (SHA: 94fd94a)
- **templates**: 대체 기준 `origin/main` (SHA: 687a178)
- **workflow-guide**: 대체 기준 `origin/main` (SHA: 87f3999)

## 3. 진행 중 작업(미머지 원격 브랜치) — 참고용, 점검 기준 아님
| 레포 | 브랜치 |
|---|---|
| devpath-ai-svc | origin/main |
| devpath-community-svc | origin/main |
| devpath-frontend | origin/feat/p7-landing-jaspr |
| devpath-frontend | origin/main |
| devpath-gateway | origin/main |
| devpath-gitops | origin/feature/w1-infra |
| devpath-gitops | origin/main |
| devpath-gitops | origin/release/slice9-lcs-app |
| devpath-landing-page | origin/main |
| devpath-lcs-svc | origin/main |
| devpath-learning-svc | origin/main |
| devpath-platform-svc | origin/main |
| devpath-sandbox-svc | origin/main |
| devpath-svc-template | origin/fix/ci-build-job-registry-auth |
| documents | origin/main |
| workflow-dashboard | origin/docs/claude-md-rules |
| workflow-dashboard | origin/main |
| .github | origin/main |

## 4. git 레포가 아닌 최상위 디렉터리

모든 최상위 디렉터리가 git 레포이므로 해당 없음.
