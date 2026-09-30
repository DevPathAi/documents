# 핸드오프 2026-09-30 밤 — S3-P5 완결 · 릴리스 캠페인 0단계까지 · 폴백 스펙 검토 대기

> 앞 핸드오프: `handoff-2026-09-30-s3-p5-complete.md`(#188·#189).
> 이 문서는 그 뒤에 한 것 = **릴리스 캠페인 착수(0단계)** 와 **AI provider 폴백 스펙 작성**.

## 1. 좌표 (2026-09-30 밤)

| 레포 | 브랜치 | 커밋 | 비고 |
|---|---|---|---|
| devpath-frontend | `develop` | **`7c80bbd`** | sync #241 머지 완료. `main` 대비 **ahead=102 · behind=0** |
| devpath-frontend | `main` | `ee5a5ad` | **릴리스 PR 미생성** — 여기가 재개 지점 |
| devpath-home-page | `master` | **`134490c7`** | 릴리스 #95 머지 완료(토큰 미러 2.0.0). develop 과 트리 동일 |
| devpath-home-page | `develop` | `9f1f42a` | sync #94 머지 완료 |
| documents | `develop` | (이 PR 머지 후) | 스펙 + 이 핸드오프 |
| devpath-gitops | `main` | `5427fe1e` | 캠페인 `base_sha`. 운영 릴리스 = `ms-20260923-…-r3` |
| 서비스 8곳 | — | — | **main 과 트리 동일 — 릴리스 대상 아님**(§3) |

## 2. 릴리스 캠페인 `ms-20260930-s3-web-redesign` — 0단계까지 끝났다

**작업 디렉터리**(git 밖, 지우지 말 것): `D:\workspace\dpa\.release-artifacts\ms-20260930-s3-web-redesign\`
- `PLAN.md` — 사용자 결정 · 착수 전 실측 표 · 12단계 · 알려진 함정 · 진행 기록
- `coords.json` — 좌표 정본(채워진 것과 `null` 인 것)

### 사용자 결정 (2026-09-30)

| 항목 | 결정 |
|---|---|
| 범위 | **frontend S3(P1~P5) + home 토큰 미러 2.0.0 만.** gitops develop 의 미반영 40파일은 이번에 제외 |
| release id | **`ms-20260930-s3-web-redesign`** |
| ET13 시각 기준선 | **승인 전에 바뀐 PNG 를 먼저 본다** — 재바인딩이 아니라 실제 사람 검토 |

### 끝난 것

- home: sync #94 → **릴리스 #95 머지**(master `134490c7`). 트리 동일 확인.
- frontend: **sync #241 머지**(develop `7c80bbd`, behind=0).

### ★ 재개 지점 — frontend 릴리스 PR

```
gh pr create --repo DevPathAi/devpath-frontend --base main --head develop \
  --title "release: S3 웹 문법 재구성을 main 에 올린다 (ms-20260930-s3-web-redesign)"
```

`main` 보호 = 필수 체크 **`analyze-test`** · `strict` · **승인 0건** · `enforce_admins` · linear off(머지 커밋 허용). `behind=0` 이므로 strict 조건은 이미 충족.

머지하면 `main` 푸시가 **web mission-off/on · admin 이미지 + `leva-*-registry-evidence-*` 아티팩트**와 **`et13-evidence.yml` 의 ET13 raw review** 를 만든다. 그것이 1·2단계의 입력이다.

### 남은 단계 (PLAN.md §단계 가 정본)

1. main 좌표 수집 — main SHA · web off/on·admin 다이제스트 · raw review(run/artifact/digest/build marker) · 워크플로 sha256
2. **기준선 검토 산출물** — 새 raw review PNG 와 현재 승인된 r3 baseline PNG 비교 → before/after Artifact 페이지
3. ET13 baseline 승인 — `automation/dispatch-<id>` 디스패처 → 보호 환경 `et13-baseline-approval` → **사람 승인**
4. provenance ×2 (Flutter 3.44.1 워크트리, `main.dart.js` 해시 = raw build marker 일치 확인)
5. 홈 preview — `wrangler pages deploy --branch release-<id> --commit-hash 134490c7`
6. candidate spec — r3 spec 파생 → 로컬 검증기 4종 → 봇 커밋 → `release/candidate-<id>` → 디스패치
7. 증거 5종 + 승인 4건 (★성공한 증거는 재디스패치 금지 — seal 은 정확히 1개)
8. validate/seal — `mission-spine-staging` 승인 2건
9. promote 사전 검증 — `preverify_service_images.py` · 체인 검증기
10. **[확인 관문]** 운영 변경 — promote OFF → ON → canary → staging rebaseline. **shared 마이그레이션 없음**(변경 0)
11. **[확인 관문]** landing-last — `/api/invite-rounds`·`/api/lead`·`/api/stats`
12. 기록

### 기준선 검토 산출물의 입력 (이미 로컬에 있다)

현재 승인된 기준선 = `.release-artifacts/ms-20260923-home-functions-gateway-cors/baseline-r3/`
`visual/{admin,dp_design,web}/<fixture>--visual--w<폭>--<테마>.png` **104장** + `baseline-approval.v1.json`. 아티팩트 `10783426360`, 만기 **2026-10-24**(여유 있다). 새 raw review 와 파일명이 같은 레이아웃이라 그대로 짝지어 비교하면 된다.

## 3. 착수 전 실측 — 범위가 크게 줄었다

메모리가 사용자 결정으로 남겨 둔 「서비스 develop 백로그 4~42커밋의 릴리스 여부」는 **물을 필요가 없었다.**

| 레포 | ahead | 실제 트리 차이 |
|---|---|---|
| devpath-frontend | 100 | **178파일 +13,383/−3,336** |
| devpath-home-page | 4 | **14파일 +100/−80** |
| gateway · platform · learning · community · ai · lcs · notification · sandbox | 4~42 | **전부 0** |

**`ahead` 커밋 수는 머지·스쿼시 방식의 산물이다** — 서비스 8곳은 내용이 이미 main 에 있다. **DB 마이그레이션 파일도 전 레포 0건**이다(지난 캠페인들이 Flyway `-target` 분할로 고생한 부류가 없다).

그리고:
- **머지 방향 안전**: frontend `git diff origin/develop...origin/main` 과 home `…develop...origin/master` 가 **둘 다 비어 있다** — 릴리스 머지가 아무것도 되돌리지 않는다.
- **브랜치 푸시는 운영을 바꾸지 않는다**: frontend 워크플로 5개에 wrangler·kubectl·argocd·helm 사용 **0건**(이미지 빌드 + ET13 증거만). home 워크플로 2개에도 배포가 없다(wrangler 직접 업로드). 운영은 promote 와 landing 에서만 바뀐다.
- **gitops 는 양방향 격차**(develop 40파일 / main 66파일). publisher 로 전진하는 레포라 설계상 갈라지지만, develop 쪽 40파일은 미반영 작업이고 **이번 범위에서 제외**했다.

## 4. AI provider 폴백 스펙 — 검토 대기

**`docs/superpowers/specs/2026-09-30-ai-provider-fallback-design.md`**(212줄, 이 PR). 사용자 검토를 기다리는 상태이고, 승인되면 다음은 `superpowers:writing-plans`.

### 브레인스토밍이 뒤집은 전제 — 이것이 스펙의 핵심

사용자 요청은 「진단·학습·멘토가 Claude 전용이니 Ollama 폴백」이었으나 실측 결과:

| 말한 기능 | 실측 |
|---|---|
| 학습경로 생성 | learning-svc 에 Claude **없음**. 이미 Ollama 전용(GPU 노드) |
| 진단 | Claude 호출 없음. 문항은 오프라인 Ollama 생성 뱅크 |
| 멘토 | **이미 `MENTOR_PROVIDER=ollama` + `MENTOR_FALLBACK=claude`** — gitops 주석이 이유까지 적어 뒀다 |

**실제 Claude 전용은 말하지 않은 세 곳**(전부 ai-svc): `REVIEW_PROVIDER=claude`(실습 코드 리뷰) · `COMMUNITY_SEED_PROVIDER=claude` · `RETENTION_PROVIDER=claude`.

그중 **신규 구현은 retention 하나**다 — review·seed 는 `OllamaAiReviewClient`·`OllamaSeedClient` 가 **이미 있다**. 다만 세 기능은 `@ConditionalOnProperty` 로 **한 번에 구현체 하나만 빈이 되는** 구조라 체인이 원리적으로 불가능하다. 「배선」의 실제 내용은 **멘토 방식(Config 조립)으로 옮기는 리팩터**다.

### 사용자가 내린 설계 결정

기능별 차등 정책 · 설정 + 런타임 실패 + **래치**(배경 탐색으로 복구) · 접근안 **A**(ProviderChain + ProviderLatch 추출, 제네릭 래퍼 없음) · 재생성은 **백엔드 엔드포인트만**(UI 별도) · retention 모델은 **더 큰 것을 새로 pull**(`qwen2.5:7b` — community-seed 와 같은 모델이라 pull 한 번이 둘을 덮는다).

### ★ 이 스펙이 릴리스에 태워질 때 걸리는 것

`*_FALLBACK` env 추가는 `kustomize build apps/devpath-ai-svc/base` 의 렌더 해시를 바꾸므로 `ai_release_eval_config.rendered_config_sha256` 이 바뀐다. 지난 캠페인이 startupProbe 추가로 **같은 이유로 release id 를 `-r3` 로 재발급**했다. candidate spec 이 새 해시를 실어야 한다.

## 5. ② Ollama 모델 추가 학습 — 미착수, 별도 프로젝트

사용자가 두 항목을 주었고 **①(폴백) 먼저, ②는 별도**로 결정했다. ②는 스펙 §11 에 「이 설계의 **수용 기준을 정한다**」로 적혀 있다 — review·retention 을 Ollama 로 넘길 수 있는지, 멘토를 Claude 우선으로 되돌릴지가 모두 품질에 달려 있다. ①이 승인되면 ②를 별도로 브레인스토밍한다.

참고 실측: 멘토는 `qwen2.5:3b`, review 는 `qwen2.5-coder:7b`(기본값, 운영 미사용), seed 는 `qwen2.5:7b`(기본값, 운영 미사용), 학습경로는 GPU Ollama. 메모리의 「7b 는 루프·오답키」 기록은 *문항 생성 + 정답키*라는 훨씬 어려운 과제였다.

## 6. 지우지 말 것

- `D:\workspace\dpa\.release-artifacts\ms-20260930-s3-web-redesign\` — 진행 중 캠페인의 `PLAN.md`·`coords.json`. **git 밖**이다.
- `D:\workspace\dpa\.release-artifacts\ms-20260923-home-functions-gateway-cors\baseline-r3\` — 현재 승인된 기준선 104장. 2단계의 비교 기준.
- `D:\workspace\dpa\.worktrees\frontend-s3p5pr2-20260930` — 일회용 프로브 3종(`probe-axe.mjs`·`probe-targets.mjs`·`probe-scroll.mjs`).
- `D:\workspace\dpa\.worktrees\home-s3-release-20260930` — 홈 릴리스 작업 워크트리.
- `D:\workspace\dpa\.worktrees\documents-s3p5-plan` — 이 문서의 작업 워크트리.
- `D:\workspace\dpa\.worktrees\frontend-s3p5-20260928` — PR-1 의 SDD 산출물.

## 7. 이 세션이 새로 실증한 함정

1. **★ `ahead` 커밋 수는 릴리스 범위가 아니다.** 트리 diff 로 재야 한다 — 서비스 8곳이 4~42커밋 앞서 보였지만 내용은 이미 main 에 있었다. 이 하나가 캠페인 범위를 크게 줄였다.
2. **★ 기능이 「Claude 전용」인지는 코드로 확인해야 한다.** 사용자가 이름 댄 세 기능 중 둘은 Claude 를 아예 쓰지 않았고, 실제 전용은 다른 세 곳이었다. 요청의 전제를 실측으로 검증하지 않으면 쓸모없는 설계를 만든다.
3. **★ `@ConditionalOnProperty(havingValue=...)` 는 체인을 원리적으로 막는다** — 구현체가 빈으로 생성조차 되지 않는다. 「폴백 설정 한 줄」로 보이는 것이 빈 배선 리팩터였다.
4. **★ 브랜치 머지가 배포인지 실측하라.** 옛 메모리에 「frontend 는 main 푸시에서만 배포된다」가 있었는데, 지금 frontend 워크플로 5개에 배포 도구 사용이 0건이다(gitops promote 가 배포를 소유한다). 오래된 메모리를 그대로 믿으면 운영 변경을 안 해도 될 단계에서 멈춘다.
5. **`gh pr view --json merged` 는 없는 필드다** — `state`·`mergedAt`·`mergeCommit` 을 쓴다. 그리고 `gh pr merge` 는 성공 시 출력이 없어 `tail` 로는 확인이 안 된다 — `state` 를 따로 조회해야 한다.
6. **프로세스 치환 `<(...)` 은 Windows `gh` 에 통하지 않는다**(`open /proc/NN/fd/63` 실패). 실제 파일로 합쳐서 넘긴다.
7. **`sleep N` 뒤에 명령을 잇는 형태는 하네스가 막는다** — `until <조건>; do sleep N; done` 또는 `run_in_background` 를 쓴다.
