# 핸드오프 2026-09-21 (오후) — gitops main 의 writer fence 제거 완료 · 운영과 git 다시 일치 · 다음은 r3

> 직전 문서: `handoff-2026-09-21-r2-promote-blocked-temporary-unfence.md`(같은 날 오전). **그 §1 의 경고("운영이 git 과 어긋나 있다")는 이 문서로 해소됐다** —
> 임시 조치는 전부 되돌렸고, 그 문서의 "원복 한 줄"은 이미 실행됐다. 교착의 구조(§3)와 교훈(§5)은 그대로 유효하다.

## 1. 지금 상태 (2026-09-21T06:10Z 실측)

| 영역 | 상태 |
|---|---|
| gitops `main` | **`fcf97cf686df8e8bad56597d4679f9a96fd597fc`**(트리 `a1c43f95c1332611e0f32066b51aa25090e98b5a`) — `release: remove the abandoned ms-20260920-community-flat-pages-r2 writer fence from main`. 부모 = r2 의 M `c1d5e8cf…`. 봉인 불변: 룰셋 2종 active · `enforce_admins` true · 환경 `mission-spine-production-off` 는 `main` 단독(id `57524487`) · `prevent_self_review` 미접촉 |
| 클러스터 | 모든 Argo Application 이 `fcf97cf6` 에서 Synced(`devpath-ollama-gpu` 의 Progressing 은 기존 상태 — GPU 워커 노드 NotReady). platform-svc·sandbox-svc **auto-sync(selfHeal) 복원**, replicas 1/1, 파드 재시작 0(무중단). ApplicationSet 의 임시 `ignoreApplicationDifferences` **제거됨** |
| 마이그레이션 | r2 의 Job `devpath-flyway-migrate-81029e190726-0328f124b50cb9fef34c4532` Complete 그대로(재실행 없음). DB Flyway `202609051004` |
| web · admin | 옛 버전 그대로(`a204810f…` · `de7ce36d…`) — **이번 릴리스는 아직 운영에 반영되지 않았다** |
| 외부 경로 | app 200 · home 200 · OAuth 시작 302 |
| 자동 롤백 레인 | 닫혀 있다(9/20T05:28Z~, 다음 릴리스 승격까지) |
| 클러스터에 남은 수동 변경 | ServiceAccount `devpath-migration-fence` 의 `imagePullSecrets: ghcr-pull` 하나(무해 · gitops 매니페스트 결함의 임시 보완 — §4) |
| 열린 PR · 세션 워크트리 | 0 · `frontend-et13-prov` 하나(r3 에서 재사용) |

r2(`ms-20260920-community-flat-pages-r2`)는 **폐기**됐다. candidate·sealed 브랜치와 증거 실행은 기록으로 남는다.

## 2. 이 구간(오후)이 한 일

1. **설계(bounded, 사용자 승인)** — "fence 만 제거". `69e7bd15` 트리로 통째 되돌리지 않는 이유: migration kustomization 의 Job 이름이 9/16 것으로 돌아가는데 그 Job 은 prune 돼 있어 Argo 가 다시 만들어 실행한다(init 이 writer replicas=0 을 기다리다 멈춤 + 관문 ConfigMap 없음).
2. **전제 증명** — 이 target 이 다음 릴리스의 base 로 받아들여짐을 실제 게이트 코드(gitops `verify_promotion_chain` 의 base 조건 3종 + shared `migration_release_gate` 의 두 렌더)로 확인. 대조군 M 은 두 게이트 모두 거부.
3. **준비** — target `fcf97cf6…` · 헬퍼 `8e42f757…` · staged 디스패처 `00c66257…`. 9/20 에 실행된 publisher 와의 diff 가 의도한 것뿐임을 확인. 계약 테스트 16 · actionlint · target 검증 step 을 실제 target·실제 얕은 클론(depth 3 통과 / 2 실패)에서 독립 Git Bash 로 실행 · 변이 3종이 의도한 단언에서 사망 · target 트리에서 `tests/release` 전체 347 OK · 실행 스크립트 단위 테스트 18 · live `--preflight-only` + 음성 대조.
4. **독립 리뷰**(새 컨텍스트) — Critical 0 · Medium 1 · Low 2, 전부 변이로 재현한 뒤 수정(step 수준 `env` 의 핀 가림 · `set -euo pipefail` 미단언 · 헬퍼 SHA 미핀).
5. **실행(사용자 확인 1회, 승인은 AI)** — publisher run **`35566755778`**(actor `github-actions[bot]` · attempt 1 · success). 환경 정책이 열려 있던 구간은 약 20초(06:02:07~06:02:29Z, 스크립트 밖에서 독립 관찰), **main-only 복원·검증 뒤에** 승인. main CI `35566816989` success. 전체 2분 30초.
6. **클러스터 원복** — `main == target` 확인 → git 선언 replicas 가 1 임을 확인 → AppSet 패치 제거 → 11초 만에 두 앱 Synced/Healthy, 3분 관찰 내내 1/1·같은 파드.

기록: 9/20 publisher 스펙 **부록 §11** + 스크립트 8개(`plans/2026-09-21-gitops-main-writer-fence-removal-via-publisher/`) — documents #158.

## 3. 다음 세션 착수점 — r3

새 id(예: `ms-20260920-community-flat-pages-r3`), `gitops.base_sha` = **`fcf97cf686df8e8bad56597d4679f9a96fd597fc`**. 계획 문서 없음 — 짧은 설계 → 승인부터.

**먼저 서비스 재빌드**(promote 의 9개 이미지 증거: 서비스 `main` 의 push 이벤트 `ci.yml` · attempt 1 · head == candidate `source_sha` == 현재 main · 아티팩트 미만료 · 보존 30일):

| 서비스 | 아티팩트 만료 | develop 이 main 보다 앞선 것 | 재빌드 방법 |
|---|---|---|---|
| community-svc | **9/21 만료** | `AGENTS.md`·`CODEX.md` 2파일(문서) | develop→main 릴리스 PR 만으로 새 main 커밋이 생긴다 |
| notification-svc | **9/21 만료** | 같은 2파일 | 같음 |
| lcs-svc | 9/23 | 트리 동일(0파일) | no-op 커밋을 develop 에 먼저(작업 브랜치 → develop PR → main PR) |
| sandbox-svc | 9/25 | 트리 동일 | 같음 |
| learning-svc | 9/26 | 트리 동일 | 같음 |
| ai-svc 10/08 · gateway 10/10 · platform 10/15 · admin 10/19 | — | — | 이번엔 불필요 |

필수는 위 둘. 아래 셋을 함께 할지는 **사용자 결정** — r3 가 9/23 을 넘기면 lcs 가 같은 식으로 막는다. 함께 하면 additive-services 에서 재시작되는 서비스가 늘어난다(기능 변화 없음).
★재빌드하면 **서비스 main 이 움직인다** — ai-svc 는 AI 평가 증거의 head 와 묶여 있으므로(`54f634b8`) 건드리지 않는다.

그 뒤: 새 다이제스트로 candidate r3 → baseline 재승인·provenance(빌드 워크트리 `frontend-et13-prov` 재사용 — release id 만 바뀌면 provenance 만 다시) → 증거 5종(사람 관문 4건: frontend `31a7785d`·documents `7f732ac5`·ai-svc `54f634b8` 가 그대로면 또 "동일 대상 재바인딩") → validate/seal → **운영을 바꾸기 전에 promote 의 `verify_service_image_evidence.py` 와 나머지 `verify_*` 를 읽기 전용으로 미리 돌린다** → 선배치(관문 ConfigMap 은 직전 실측값으로 새로 · SA patch 는 남아 있음) → migration-release → promote OFF → promote ON → landing-last([사람] N01 Cloudflare 토큰 선행).

재사용: `.release-artifacts/ms-20260920-community-flat-pages/r2/` 의 스크립트(`run_provenance_r2.py`·`build_candidate_spec_r2.py`·디스패처 렌더링) · 홈 preview `19be54a3-592f-4ec7-b2ff-9b0caf8228f4`(홈 master `5b9d6e38` 그대로면) · `approve_gate.py`.

## 4. 남은 결함(이번에 고치지 않음)

- **fence ServiceAccount 의 `imagePullSecrets` 가 gitops 매니페스트에 없다**(`apps/devpath-migration/base/writer-fence-rbac.yaml`). 수동 patch 가 사라지면 마이그레이션 Job 이 이미지를 못 받는다(9/16 의 43분 원인 중 하나). 고치려면 shared 의 M 렌더 검증이 그 변경을 받아들이는지부터 조사 — publisher 경로.
- **`sandbox-migration-gate` ConfigMap 은 릴리스마다 손으로 만들어야 한다**(운영자 유지보수 승인). 절차에 넣을 것.
- **이미지 증거의 30일 보존이 릴리스 가능 기간을 정한다** — 캠페인 1단계에서 9개 서비스의 `expires_at` 을 먼저 본다.

## 5. 이 구간의 교훈

- **통째 되돌림은 안전해 보이지만 부작용을 되살린다.** "이전 트리와 동일"이 가장 단언하기 쉬운 목표였지만, 되돌아가는 Job 이름이 이미 prune 된 자원을 다시 실행시켰을 것이다. 되돌릴 때는 **클러스터가 그 상태를 어떻게 다시 해석하는지**를 본다.
- **설계의 전제는 실제 게이트 코드로 증명한다**, 그리고 대조군을 둔다 — 통과만 보면 검사가 아무것도 가르지 않아도 모른다.
- **검증은 러너와 같은 조건에서** — 전체 클론에서 통과한 step 이 `fetch-depth: 2` 에서는 실패했다(3 으로 고정).
- **리뷰어의 완화 근거도 잰다.** "기본 셸이 pipefail 이라 영향이 작다"는 틀렸다 — `shell:` 미지정 러너 셸은 `bash -e {0}` 이다(오늘 로그).
- Windows 서브에이전트의 최종 응답 유실은 여전하다(`R1 DONE` 한 줄·기록 0바이트). **"보고 전문을 지정 파일에 써라, 응답은 3줄"** 을 SendMessage 로 1회 요청해 회수했다 — 처음부터 그렇게 지시할 것.
- documents PR 을 만든 직후 `pull_request` 워크플로가 뜨지 않고 mergeable 이 `unknown` 에 머물렀다 — close/reopen 으로 이벤트를 다시 냈다.
- Python `subprocess` 의 bare `bash` 는 Windows 에서 WSL 로 풀릴 수 있다 — Git Bash 절대경로를 넘긴다.

## 6. 사람 단계

- **N01 Cloudflare durable token** — landing-last 전.
- r3 의 사람 관문 4건(baseline·프라이버시·AI 평가·NVDA).
- r3 재빌드 범위 결정(§3 표).
- 앞에서 넘어온 것: 모바일 서명 시크릿 4종 이전 · YouTube 재업로드 · 로그인 캡처 · AdSense 결정.
