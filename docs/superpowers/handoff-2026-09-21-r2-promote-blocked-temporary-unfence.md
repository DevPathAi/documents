# 핸드오프 2026-09-21 — 릴리스 캠페인 r2: seal 완료 · promote 교착 · 운영은 임시 unfence 상태

> 직전 문서: `handoff-2026-09-20-evening-release-campaign-evidence-pending.md`. 그 §3 의 재개 순서를 이 세션이 밟았다.
> **먼저 읽을 것은 §1 의 경고 하나다.** 산출물·스크립트는 레포 밖
> `D:/workspace/dpa/.release-artifacts/ms-20260920-community-flat-pages/`(git 저장소 아님, r2 분은 그 안의 `r2/`).

## 1. 🚨 지금 운영은 git 과 어긋나 있다

| 영역 | 상태 (2026-09-21T03:42Z 실측) |
|---|---|
| gitops `main` | **`c1d5e8cf197c7dbcb0d5f224011b82b73412e17a`** — `deploy(devpath-migration): ms-20260920-community-flat-pages-r2 sealed 0328f124…`. 이 커밋은 platform-svc·sandbox-svc 에 **`replicas: count: 0`(writer fence)** 를 담고 있다 |
| 클러스터 | platform-svc·sandbox-svc **replicas 1(수동)** · 두 Argo Application 은 `OutOfSync/Healthy`·auto-sync 꺼짐 · 나머지 앱은 auto-sync 그대로 |
| ApplicationSet `devpath-services` | `spec.ignoreApplicationDifferences: [{jsonPointers: ["/spec/syncPolicy"]}]` 가 **임시로 추가돼 있다** |
| web · admin | 옛 버전 그대로(`sha256:a204810f…` · `sha256:de7ce36d…`) — **이번 릴리스는 운영에 반영되지 않았다** |
| 운영 DB | Flyway `202609051004`(목표와 같음 — 이번 마이그레이션은 no-op 이었고 Job 은 완료) |
| 홈 운영 배포 | `005cf175-6e3e-4400-a201-1987ce9d8d84` 그대로 |
| 자동 롤백 레인 | 닫혀 있다(9/20T05:28Z~) |

**이 상태를 깨뜨리는 행동**: ApplicationSet 을 git 의 `argocd/applicationset.yaml` 로 다시 apply 하거나 `ignoreApplicationDifferences` 를 지우면, AppSet 이 auto-sync 를 되살리고 Argo 가 두 서비스를 **다시 0 으로 내린다**. platform·sandbox Application 을 수동 sync 해도 같다. main 에서 fence 가 사라지기 전에는 하지 않는다.

원복(=fence 재적용)은 한 줄이다. main 에 fence 없는 커밋이 올라간 **뒤에만** 실행한다:

```bash
sudo k3s kubectl -n argocd patch applicationset devpath-services --type=json \
  -p '[{"op":"remove","path":"/spec/ignoreApplicationDifferences"}]'
```

## 2. 이 세션이 한 일

1. **사람 승인 3건 확인** → 증거 5/5.
2. **5단계 validate(원래 id) 실패 → 근본 원인 수정.** validate `35549081260` 이 여정이 돌기도 전에 죽었다: `quality_evidence_inputs fields do not match the canonical candidate-spec`. candidate-spec 계약의 미러가 frontend·gitops 말고 **홈 레포의 릴리스 여정 하니스**(`e2e/release/support/release-context.js`)에도 있었고, 9/16 계약(서명 모바일·TalkBack·`mobile` surface·12 fixture·96/24)에 머물러 있었다. 홈 #89 → develop, #90 → master **`5b9d6e38b8cc47028a409962ba563fe3555e50cb`**. 전 레포를 검색해 남은 미러가 없음을 확인했다.
3. **새 id `ms-20260920-community-flat-pages-r2` 로 재진행**(사용자 결정). 같은 id 로는 이어갈 수 없다 — 증거가 spec sha256 에 묶여 있고, 재디스패치하면 producer 단일성(정확히 1개)이 깨진다.
   - 홈 dist `0247938747ab…e412` · preview `19be54a3-592f-4ec7-b2ff-9b0caf8228f4`
   - ET13 baseline `35551443095` → 아티팩트 `10618243140` · provenance 재계산(로컬 빌드가 CI 와 또 바이트 일치)
   - candidate 브랜치 `ffe7344557c7…` · spec sha256 **`7e9f80bfbddb…5ea9`**(검증기를 통과한 9/20 spec 에서 파생, 바뀐 필드 14개) · run `35551840448` · 아티팩트 `10619025353`
   - 증거 5종 전부 success. 사람 관문 4건(baseline·프라이버시·AI 평가·NVDA)은 사용자 지시("동일 대상 재바인딩은 대신 눌러 줘")로, **검토 대상이 이미 승인된 것과 바이트 동일함을 실측한 뒤** AI 가 대행하고 코멘트에 사실을 적었다.
4. **5단계 r2 완료.** validate **`35552555485`** success. `sealed_release_sha` **`1c0c06f1862f34213daaf07db7e633affb5ce96b`** · `release_manifest_sha256` **`0328f124b50cb9fef34c45320999872e63b523d11a8bdb096049d1a1e77465d2`**.
5. **6단계 실행.** 9/16 의 43분 중단 원인을 Codex 세션 로그에서 찾아(관문 ConfigMap 부재 · fence SA 의 `imagePullSecrets` 부재) 선배치했다. migration-release `35557112238` success → main `c1d5e8cf`(03:19:25Z) → Job 이 **약 20초 만에 Complete**.
6. **promote 실패 → 사고.** promote `35557187760` 이 fence 를 풀기 **전** 단계에서 실패: `devpath-community-svc: exactly one eligible immutable-image run is required`. platform·sandbox 가 03:19:25Z~03:40:12Z **약 21분** 내려가 있었다(그중 일부는 복구 방법을 사용자에게 묻고 답을 기다린 시간).
7. **임시 복구**(사용자가 선택지 A 를 고름): AppSet 에 syncPolicy 차이 무시 추가 → 두 Application 의 `automated` 제거 → `scale --replicas=1`. 1분 뒤 재확인: replicas 유지 · OAuth 시작 경로 302 · platform 로그 오류 0. 일회성 유지보수 승인 ConfigMap `sandbox-migration-gate` 는 회수했다.

## 3. 왜 막혔나 — 교착의 구조

**(a) r2 의 promote 는 끝낼 수 없다.** promote 는 9개 서비스 각각에 대해 "서비스 `main` 의 **push 이벤트** `ci.yml` 실행 · success · attempt 1 · head_sha == candidate 의 `source_sha` == 현재 main · 아티팩트 **미만료**"를 정확히 1개 요구한다(gitops `scripts/release/verify_service_image_evidence.py`). community-svc(`f4f05edb`, run `32542271380`)와 notification-svc(`c659b215`, run `32542243631`)의 아티팩트가 **2026-09-21 에 만료**됐다(8/22 빌드, 보존 30일). 같은 SHA 에서 push 이벤트를 다시 만들 방법은 없고, 재실행은 attempt 2 라 부적격이다.

**(b) r3 는 지금의 main 위에서 시작할 수 없다.** shared `scripts/release/migration_release_gate.py` 의 `render_writer_fence_kustomization` 은 base 에 이미 replica override 가 있으면 거부한다(`sealed base already contains a replica override`). main 의 fence 는 r2 의 additive-services 커밋만 풀 수 있는데, 그것이 (a) 에 막혀 있다.

**(c) main 에서 fence 를 걷어내는 길은 publisher 뿐이다.** main 대상 PR·직접 push 는 봉인 3겹(룰셋 2종 + classic)에 막혀 있고, 롤백 워크플로는 web·랜딩만 되돌리며 M/S 는 유지하는 설계라 fence-only 상태를 풀지 못한다.

곧 만료되는 나머지: lcs-svc **9/23** · sandbox-svc **9/25** · learning-svc **9/26** · ai-svc 10/08 · gateway 10/10 · platform-svc 10/15 · admin 10/19.

## 4. 다음 세션 착수점

**순서가 중요하다.** 계획 문서 없음 — 1번은 brainstorming(bounded)부터, 9/20 publisher 의 스펙·계획·스크립트(`documents/docs/superpowers/{specs,plans}/2026-09-20-gitops-main-promotion-via-publisher*`)를 출발점으로.

1. **publisher 로 main 의 fence 를 되돌린다.** 목표 트리 = `69e7bd15570f5ba0f271c83b5bd46955cb249c8e` 의 트리(`c1d5e8cf` 가 바꾼 3파일 — `apps/devpath-migration/base/kustomization.yaml` · `apps/devpath-platform-svc/base/kustomization.yaml` · `apps/devpath-sandbox-svc/base/kustomization.yaml` — 의 역적용). 9/20 메모리의 규칙 그대로: `MAIN_SHA` 핀이 바뀌었으므로 **Part A(준비)를 새 main 위에서 리뷰 포함 다시**. 닫을 질문: 체인 검증기(`verify_promotion_chain.py` 등)가 "M 뒤에 M 을 되돌리는 커밋"이 있는 이력을 다음 candidate 에서 받아들이는가(9/20 은 "완료된 릴리스의 mission-on 커밋"이 `MAIN_SHA` 였다 — 이번엔 미완 체인의 M 이다).
2. main 에 fence 없는 커밋이 올라간 것을 확인한 뒤 **§1 의 원복 한 줄** → 두 앱이 `Synced` 로 돌아오고 replicas 가 git 값(기본 1)과 일치하는지 본다.
3. **r3.** 서비스 main 재빌드(만료된 community-svc·notification-svc 는 필수, 9/23~26 만료인 lcs·sandbox·learning 을 함께 할지는 사용자 결정 — 각 레포 develop 과 main 의 차이를 먼저 잰다. 실제 변경을 싣지 않으려면 no-op 커밋) → 새 다이제스트로 candidate r3 → baseline·증거 5종 → validate/seal → **운영을 바꾸기 전에 뒤 단계의 검증을 전부 미리 돌린다**(§5 첫 항목) → migration-release → promote → landing-last([사람] N01 Cloudflare 토큰 선행).
4. r3 에서 재사용할 것: `r2/` 의 스크립트(`run_provenance_r2.py`·`build_candidate_spec_r2.py`·디스패처 렌더링), 빌드 워크트리 `D:/workspace/dpa/.worktrees/frontend-et13-prov`(frontend `31a7785d`, web·admin ET13 릴리스 빌드가 들어 있다 — release id 가 바뀌면 provenance 만 다시 계산), 홈 preview `19be54a3-…`(홈 master 가 그대로면).

재개 시 상태 확인:

```bash
export MSYS_NO_PATHCONV=1
gh api repos/DevPathAi/devpath-gitops/branches/main -q .commit.sha      # c1d5e8cf…
tr -d '\r' < ~/.ssh/devpath-k3s-key.pem > "$SCRATCH/k3s-key"; chmod 600 "$SCRATCH/k3s-key"
ssh -i "$SCRATCH/k3s-key" -o BatchMode=yes ubuntu@13.124.153.105 '
  sudo k3s kubectl -n devpath get deploy devpath-platform-svc devpath-sandbox-svc
  sudo k3s kubectl -n argocd get applicationset devpath-services -o jsonpath="{.spec.ignoreApplicationDifferences}"; echo
  sudo k3s kubectl -n argocd get application devpath-platform-svc devpath-sandbox-svc'
```

## 5. 교훈

- **validate/seal 통과는 promote 통과를 뜻하지 않는다.** promote 에만 있는 검사(9개 이미지 증거)를 사전 점검이 읽지 않았고, 그 결과 fence 가 걸린 채 멈췄다. **운영을 바꾸는 단계 앞에서는 그 뒤 워크플로의 `verify_*` 를 전부 읽기 전용으로 미리 돌린다** — 특히 `verify_service_image_evidence.py`. 만료일은 `gh api repos/<repo>/actions/artifacts` 의 `expires_at` 로 잰다.
- **보존 기간이 릴리스 가능 기간이다.** 30일 안에 main 에 push 가 없던 서비스는 promote 를 막는다. 캠페인 1단계에서 9개 서비스의 만료일을 먼저 본다.
- **계약의 미러는 "아는 곳"이 아니라 전 레포 grep 으로 센다.** S2a/S2c 는 미러를 둘로 알았지만 셋이었다. 새 로컬 관문: candidate 를 push 하기 전에 **핀된 홈 SHA 의 하니스에 spec 을 먹여 본다**(`loadReleaseContext`).
- **선배치가 9/16 의 43분을 20초로 줄였다.** 원인은 Claude 세션 기록이 아니라 Codex 로그(`~/.codex/sessions/2026/09/16/`)에 있었다. gitops 의 SA 정의에 `imagePullSecrets` 가 없는 것은 매니페스트 결함이다 — publisher 작업 때 함께 고칠 후보.
- **fence 를 거는 단계와 푸는 단계 사이에는 되돌릴 길이 없다.** 롤백 워크플로도, PR 도, 수동 sync 도 fence-only 상태를 풀지 못한다. 이 구간에 들어가기 전에 "푸는 단계가 통과한다"를 증명해 둬야 한다.
- candidate 워크플로는 **candidate 브랜치 ref** 로 디스패치한다(`--ref main` 으로 띄워 1회 실패 — 아티팩트 0, 무해).
- Bash 도구에서 `git show origin/main:path` 는 **호출마다** `export MSYS_NO_PATHCONV=1` — 셸 상태는 호출 사이에 유지되지 않는다.

## 6. 좌표

| 항목 | 값 |
|---|---|
| release id | `ms-20260920-community-flat-pages-r2`(원래 id 는 validate 에서 실패, 폐기) |
| candidate / sealed | `ffe7344557c7a37979c4c89db65c6a49227e0ab8` / `1c0c06f1862f34213daaf07db7e633affb5ce96b` |
| spec / manifest sha256 | `7e9f80bfbddb37d9745ae5dafb2e0aa76d381c945cedfd53f2756e0cfd7b5ea9` / `0328f124b50cb9fef34c45320999872e63b523d11a8bdb096049d1a1e77465d2` |
| gitops main | `69e7bd15…`(seal 때) → **`c1d5e8cf…`**(M, fence 포함) |
| 실행 | validate `35552555485` · migration-release `35557112238` · promote(실패) `35557187760` |
| 증거 r2 | 홈 dist `35551945014` · ET13 `35551941486` · Manual AT `35551942719` · 프라이버시 `35551925821` · AI 평가 `35551943452` · baseline `35551443095` |
| 홈 | master `5b9d6e38…` · dist `0247938747ab…e412` · preview `19be54a3-592f-4ec7-b2ff-9b0caf8228f4` |
| 디스패처 브랜치(증거로 유지) | 각 레포 `automation/dispatch-ms-20260920-community-flat-pages`(`-r2`) |
| 남긴 세션 워크트리 | `frontend-et13-prov` 하나 |
| 클러스터에 남긴 수동 변경 | AppSet `ignoreApplicationDifferences` · 두 Application 의 auto-sync 제거 · 두 Deployment replicas 1 · SA `devpath-migration-fence` 의 `imagePullSecrets: ghcr-pull` |

## 7. 사람 단계

- **N01 Cloudflare durable token** — landing-last 전(그대로 남아 있다).
- r3 에서 사람 관문 4건이 다시 필요하다(baseline·프라이버시·AI 평가·NVDA). frontend 소스가 `31a7785d` 그대로면 검토 대상은 또 동일하다.
- 앞 핸드오프에서 넘어온 것: 모바일 서명 시크릿 4종 이전 · YouTube 재업로드 · 로그인 캡처 · AdSense 결정.
