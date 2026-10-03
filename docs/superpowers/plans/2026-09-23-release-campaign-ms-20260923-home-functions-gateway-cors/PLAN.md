# 릴리스 캠페인 `ms-20260923-home-functions-gateway-cors` — 계획·좌표 (2026-09-23 저녁 착수)

> **선회(2026-09-23T13:05Z, 사용자 결정)**: 첫 candidate 가 gitops 검증기에서 거부됐다 — `rollback.prior_digest` 는 base 웹(= 운영 `a6466f5d`)과 같아야 하고 동시에 후보 mission-off/on 과 달라야 한다(`validate_release_manifest.py:993-996`). frontend 소스가 r3 와 같으면 모순. → **frontend 를 README 사유 커밋으로 재빌드 릴리스**(새 SHA → 새 web/admin 이미지 → ET13 raw review·baseline·provenance·NVDA 를 새 SHA 로) 하고, **release id 는 `ms-20260923-home-functions-gateway-cors-r2`** 로 재발급한다(첫 id 에는 이미 성공한 baseline 승인 런 `35862514213` 이 있어 같은 id 로 두 번째 승인을 만들면 seal 의 "정확히 1개" 규칙에 걸린다 — r2→r3 선례). gateway 이미지(SHA 기준)·홈 preview(배포 id 기준, r3 가 r2 preview 를 재사용한 선례)는 그대로 쓴다. 첫 id 의 산출물(baseline 승인 `10750996942`, provenance, 디스패처 브랜치)은 고아로 남긴다.

**사용자 결정(2026-09-23)**: 범위 = 홈(Pages Functions 를 봉인 dist 에 묶은 #91, master `ffaf4b33`) + gateway CORS 헤더 중복 제거(#44) · 다른 7개 서비스는 r3 이미지 그대로 · 사람 관문 4건은 "검토 대상이 이미 승인한 것과 바이트 동일"을 실측한 경우 AI 가 재바인딩 대행(r3 방침) · 운영 변경 단계(migration/promote/landing)는 직전에 확인.

release id 규칙 `^ms-[0-9]{8}-[a-z0-9][a-z0-9-]{2,40}$` → **`ms-20260923-home-functions-gateway-cors`**.

## 좌표 (알려진 것)

| 항목 | 값 |
|---|---|
| gitops `base_sha` | `5961922b9a309055a75bc7302e5c852c5c51d59c`(2026-09-23 publisher, startupProbe 포함) |
| 운영 웹(base_web) | `31a7785d…-mission-on` = `sha256:a6466f5de1714e12b7fcd01766e0fc0e4f61cf4dab4e6155ea0948ee3fb1c4e1`(gitops main kustomization) |
| frontend | `31a7785d5f3c73563c8ddb61b69a7a0e07f65f16`(r3 와 동일 · mission_off `c140b9a4…` · mission_on `a6466f5d…` · admin `53813915…`) |
| 홈 | master `ffaf4b33ca23d61dfd0304f666192a4e6c6ddfa3` · `dist_sha256` `00794a107b370a28404edbed62ffdd71891491f8953998d54f7b9eeb740cc237` · `prior_production_deployment_id` `005cf175-6e3e-4400-a201-1987ce9d8d84` · 시각 카탈로그 `rendered_product_sha` `3995dfc7…`(홈 `e2e/visual/candidate-spec.v2.json`) |
| gateway | develop `58359bc`(#44) → sync PR → 릴리스 PR(squash) → 새 main SHA · 새 digest · immutable-image 아티팩트(이 단계에서 채움) |
| 직전 릴리스(rollback prior) | `ms-20260920-community-flat-pages-r3` · spec sha256 `b5ede99fa46a753202d9a4da1218c6fb9de1e7f0516063211648a4fd4c84cbcd` · sealed `fe459818…` |
| shared migration | 변경 없음(`9793b8f9` · flyway `202609051004`) — 6단계는 그래도 fence→Job→additive 를 밟는다(platform·sandbox 약 3분 중단, 확인 관문에서 명시) |
| ET13 baseline 원자료 | raw run `35434688375`/attempt 1 · artifact `10581743618`(만료 10/03) · digest `sha256:fa25b743…` · workflow sha256 `71ba5845…` — r3 와 동일 입력 |

## 단계

0. **gateway 릴리스** — sync PR(main→develop) → develop→main squash(`r3/release_merge.py`, gateway 는 reviews=0 이라 완화 불필요) → main push CI 의 immutable-image 아티팩트·GHCR digest 기록(`service-images.json`).
1. **ET13 baseline** — frontend 디스패처 브랜치 `automation/dispatch-<id>` 에 baseline 디스패처 push → `et13-baseline-approval.yml` 실행 → 환경 `et13-baseline-approval` 승인(동일 대상 재바인딩: raw digest 가 r3 승인분과 동일) → 승인 baseline 아티팩트 id·digest·`baseline-approval.v1.json`.
2. **provenance** — frontend `31a7785d` 워크트리에서 web·admin ET13 빌드 → `main.dart.js` 해시 = build marker → `provenance --mode=release_ready` ×2(visual·a11y, 새 baseline run/artifact) → `input_provenance_sha256`·file sha.
3. **홈 preview** — master `ffaf4b33` dist 를 `wrangler pages deploy --branch release-<id> --commit-hash ffaf4b33…` → `candidate_deployment_id`·`landing_origin`.
4. **candidate spec** — r3 spec(검증기 통과본)에서 파생, 바뀐 필드만 단언: release_id·created_at·frontend.app_version·gitops.base_sha/base_web_tag/base_web_digest·frontend.rollback(prior_digest·prior_identity=r3)·services.devpath-gateway·home.*·catalogs(home-visual/home-axe source_sha·rendered_product_sha·tree, frontend-visual baseline_approval_sha256·provenance ×2) → 로컬 `validate_release_manifest.py`·`verify_candidate_web_base.py` → 봇 커밋 → `release/candidate-<id>` push → candidate 워크플로(직접 디스패치).
5. **증거 5종** — 홈 dist(직접) · ET13 + Manual AT(frontend 봇 디스패처) · 프라이버시(documents 봇 디스패처) · AI 평가(ai-svc 봇 디스패처) → 승인 4건(재바인딩 대행 조건 확인 후 `approve_gate.py`). ★성공한 증거는 재디스패치 금지(seal 은 정확히 1개)★
6. **validate/seal** — gitops 봇 디스패처 → 승인 2건(`mission-spine-staging`) → sealed SHA·manifest.
7. **promote 사전 검증** — `preverify_service_images.py`(9 이미지 증거 미만료·GHCR 대조) · 체인 검증기가 현재 main 을 base 로 수용.
8. **[확인 관문] 운영 변경** — migration-release(shared) → promote OFF → promote ON → canary → staging rebaseline. 직렬화: startupProbe 가 있어 herd 는 완화됐지만 additive-services 는 gateway 1개만 바꾼다.
9. **[확인 관문] landing-last** — 배포 뒤 첫 확인은 `/api/invite-rounds`·`/api/lead`·`/api/stats`.
10. 기록(스펙·핸드오프·메모리).

## 세션 2 (2026-09-24 아침) — 재빌드 릴리스의 실제 경로와 스크립트 파이프라인

**함정**: `et13-evidence.yml` 의 main push 트리거는 `paths:` 필터라 README 만 바뀐 main 푸시로는 ET13 raw review 가 돌지 않는다. baseline 승인은 `rawRun.event == push`·`rawRun.head_sha == main HEAD` 를 요구한다. → #197 선례대로 `evidence/et13/release-triggers/<r2 id>.md` 마커를 추가(PR #231). gitops `source-pin.v1.json` 은 evidence/et13 의 8개 파일만 핀하고 `et13_evidence.dart` 의 재귀 리스팅은 `.json` 만 검사한다.

**frontend**: #229(README, develop `0d97229`) → #231(트리거 마커, `734fe42`) → develop → **#230**(develop→main, merge commit, `analyze-test`) → main 푸시 = ci.yml(web off/on·admin 이미지 + `leva-*-registry-evidence-*` 아티팩트) + et13-evidence.yml push(raw review `et13-unsealed-raw-review-run-*`).

**스크립트(순서대로, 모두 `coords-r2.json` 을 읽고 채운다)**:
1. `collect_main_r2.py coords-r2.json` — main SHA·web off/on·admin 다이제스트·raw review(run/artifact/digest/build marker)·워크플로 sha256 수집.
2. `verify_identical_target_r2.py coords-r2.json` — raw review PNG 104장의 candidate_set_sha256 이 r3 승인 baseline(`2db5d572…`)과 바이트 동일함을 증명 → `IDENTICAL_TARGET_OK`(없으면 사람 검토).
3. `baseline_r2.py coords-r2.json dispatch|approve|collect` — frontend `automation/dispatch-<r2>` 브랜치(main 기반)에 렌더된 디스패처 push → 봇 승인 런 대기 → `approve_gate.py`(재바인딩 대행) → 승인 baseline 아티팩트 → `baseline-r2/`.
4. `build_r2.sh coords-r2.json` — Flutter 3.44.1 워크트리(`frontend-et13-prov-r2`, 새 SHA)에서 web/admin ET13 빌드 → main.dart.js 해시가 raw 마커와 일치해야.
5. `run_provenance_r2.py coords-r2.json` — release_ready provenance ×2(visual·a11y).
6. `candidate_r2.py coords-r2.json prepare|push|dispatch` — gitops 워크트리 `gitops-candidate-20260923-r2`(`release/candidate-<r2>`, base `5961922b`) → `build_candidate_spec_r2.py` → 관문 4종(검증기·web base·홈 하니스 `loadReleaseContext`·`preverify_service_images.py`) → 봇 커밋(`devpath-gitops-release[bot]`) → push → `mission-spine-candidate.yml` 직접 디스패치 → candidate run/artifact.
7. `render_dispatchers_r2.py coords-r2.json evidence` → frontend(같은 automation 브랜치 2번째 커밋)·documents·ai-svc `automation/dispatch-<r2>` push + 홈 `mission-spine-home-dist.yml` 직접 디스패치(release_id·candidate_spec_sha256·home_source_sha·dist_sha256) → 인증 관문 승인(재바인딩 대행) → 증거 5종.
8. `render_dispatchers_r2.py coords-r2.json validate` → gitops `automation/dispatch-<r2>`(main 기반, 봇 작성자) → `mission-spine-staging` 승인 2건 → seal.
9. [확인] `promote` → shared migration-release(`r3-devpath-shared.yml` 선례) → promote → canary. 10. [확인] `landing`.

**확인된 불변**: documents main `7f732ac5`·ai-svc main `54f634b8`·shared main `9793b8f9`·gitops main `5961922b`·홈 master `ffaf4b33` 모두 그대로. 워크플로 sha256(raw `71ba5845…`·baseline `24e959a7…`)도 develop 에서 동일.

### r2 → r3 (2026-09-24 00:10Z)

ai-svc 평가가 `candidate does not bind exact ET9 release inputs` 로 실패: `ai_release_eval_config.rendered_config_sha256` 은 gitops `base_sha` 에서 `kustomize build apps/devpath-ai-svc/base`(v5.4.3) 를 렌더한 sha256 이며, 새 base `5961922b` 의 startupProbe 때문에 `bb9f18df…`→`bfa0126d…` 로 바뀌어야 했다. 증거 producer 적격이 아티팩트 이름(release id) 기준이라 같은 id 재사용 불가 → `-r3`. 스크립트는 `coords-r3.json` 으로 같은 순서(baseline → provenance → candidate → evidence → validate)를 다시 밟는다. builder 는 이제 kustomize 렌더 해시를 직접 계산·단언한다.

### r3 상태 (2026-09-24 01:0xZ) — 봉인 완료, 운영 변경 대기

| 단계 | 결과 |
|---|---|
| baseline 승인 | run `35937165203` · artifact `10783426360` (동일 대상 재바인딩 대행) |
| candidate | gitops `release/candidate-<r3>` `687c6167` · spec `06cd05d9…` · run `35937332719` · artifact `10783084611` |
| 증거 5종 | home `35937419487` · ET13 `35937561874` · manual-AT `35937563630` · privacy `35937570293` · AI eval `35937578808` |
| validate 1차 | `35938438966` 실패 — staging sandbox-runner TLS 30일 만기(9/23 12:10Z) → 인증서 재발급(3650일)·파드 재생성으로 복구 |
| validate 2차 / seal | `35939693144` success · seal `4a2ab53a` · manifest sha256 `c95cc641…` |
| preflight | gitops main = base · 9 이미지 ok(가장 빠른 만료 ai-svc 10/08) · 체인 검증기 통과 |
| **다음(사용자 확인 필수)** | `promote_r2.py coords-r3.json migration` → `promote-off` → `promote-on` → `landing` |

### 운영 변경 진행과 검증기 결함 (2026-09-24 01:09Z~)

| 시각(UTC) | 단계 | 결과 |
|---|---|---|
| 01:09 | shared migration-release `35941728847` | success → gitops main `a2c677a` |
| 01:11~01:23 | promote OFF `35941807967` | fence → Job(ConfigMap `sandbox-migration-gate` 부재로 01:15~01:17 지연, 손으로 생성) → additive-services `8b036dc` → **런타임 검증 실패** |
| 01:26~01:35 | promote 재개 `35942936280` | 같은 실패: `Argo Application revision is not exact` |
| 진단 | | 검증기가 `kustomization.yaml` 마지막 커밋을 applied revision 으로 삼는데 9/23 publisher 가 deployment.yaml 만 바꿔 Argo 가 `5961922b` 로 sync → ai·community·lcs·learning·notification 5개 영구 불일치 |
| 사용자 결정 | | publisher 로 검증기 수정 게시 후 재개 |
| 수정 | dev `a70eeb9` → target **`6efa0d00`**(트리 `2761cf64`) | `wait_release_rollouts.py` applied revision = `apps/<svc>/base` 디렉터리 · 문법 슬롯 `fix(release): bind service applied revision to the app base`(services 직후 1회) · 테스트 3건 |
| publisher 준비 | 헬퍼 `chore/service-applied-revision-publish-20260924` **`24767ded`** · staged `…-dispatcher-staged-20260924` **`1d960111`** · target 브랜치 `fix/service-applied-revision-main-20260924` | 계약 테스트 18/18 · run 스크립트 단위 18 · preflight ok · 음성 대조 거부 |
| 발견 | | CORS dedupe 가 운영에서 무효: gitops gateway env `…DEFAULT_FILTERS_0=PreserveHostHeader` 가 application.yml 의 dedupe 필터를 덮어씀 → 별도 publisher 커밋 필요 |
| 운영 현재 | | gateway `8cf6af8d`·admin `ec6fd714` 신규, platform·sandbox 복구(fence 중단 약 6분), web 은 r3 mission-on 그대로, 체인 phase `services` |
| 03:04~03:07 | publisher | 리뷰(서브에이전트) 뒤 범위 확장(canary·evidence 도 kustomization 기준 대조) → target **`8b01c02d`**(10경로) · 헬퍼 `d5a4694c` · 스위트 359 OK → publisher 런 `35949979763` success → **gitops main = `8b01c02d`** |
| 03:08 | promote 재개 | nonce 커밋 → OFF 잡(고친 검증기) 진행 중 |
| 03:08~03:12 | promote 재개 `35950184028` | **success** — 고친 검증기가 services 관문 통과 → mission-OFF → gitops main `1d45b63`(web mission-off `fba587d5`) |
| 03:13~03:35 | promote ON `35950519691` | nonce `28d95b72` → 첫 대기 환경이 production-on(순서 assert 실패 → `wait_bot_run` 무순서 승인 + `promote-on-continue`) → mission-ON 03:16:48Z gitops main **`eae5c42`** → canary 900s → staging rebaseline → **success** |
| 03:40 | 운영 실측 | web `devpath-web-594c4fcf89-ppxpq` 1/1 **`4fb7acbf…`**(mission-on) · Argo Synced/Healthy `eae5c42e` · gateway `8cf6af8d…` · 비정상 파드 0 · 스모크 app/api/landing 200 |
| 03:42 | CORS 라이브 재측정 | `GET /mentor-access/invite-rounds` Origin `https://leva.ai.kr` → 200, **ACAO 2개·Vary 6개 그대로**(gitops env `DEFAULT_FILTERS_0=PreserveHostHeader` 가 dedupe 를 덮음) — #44 는 운영에서 무효, 별도 gitops 수정 필요 |
| 03:57~03:59 | landing-last `35953575812` | 사용자 재확인("지금 landing 실행") → 디스패치 `b21cd9b6` → 환경 `mission-spine-production-landing` 승인 → **success**. 새 운영 배포 **`6f7a7e2b-522f-4bf1-b134-2dd2b345f83c`**(prior `005cf175`), 증거 artifact `10789682304`(만료 10/24). 라이브 `/`·`/api/invite-rounds`·`/api/stats` 200, `/updates` 308→200, index = 후보 `2225c3fb` 와 동일(Cloudflare 주입 2줄 제외). **릴리스 r3 운영 반영 완결.** |
| 04:0x | ConfigMap 회수 | 사용자 승인 → 운영 `sandbox-migration-gate` 삭제(참조는 완료된 flyway Job 파드뿐, Argo 미관리) |

### 잔여 과제 (2026-09-24 03:45Z)

- CORS: gitops `apps/devpath-gateway/base/deployment.yaml` env 를 `_FILTERS_0=DedupeResponseHeader=Access-Control-Allow-Origin Access-Control-Allow-Credentials Vary,RETAIN_UNIQUE` · `_FILTERS_1=PreserveHostHeader` 로(publisher 경로, 이미지 무변경). 라이브 확인 명령은 위 03:42 행.
- ~~ConfigMap 회수~~ 완료(04:0xZ). 다음 캠페인 preflight 에 `sandbox-migration-gate` 선배치·회수 단계 자동화는 남음.
- staging `provision_mission_staging.sh -days 30` → 장기 인증서로 수정.
- r2 고아 브랜치·워크트리 정리, documents 핸드오프·publisher 스크립트 커밋(선례 관례).

### CORS env publisher (2026-09-24 04:0x~04:27Z, 사용자 승인)

| 단계 | 결과 |
|---|---|
| TDD | `tests/release/test_gateway_edge_cors.py` RED → `apps/devpath-gateway/base/deployment.yaml` 에 `…DEFAULT_FILTERS_1=DedupeResponseHeader=Access-Control-Allow-Origin Access-Control-Allow-Credentials Vary, RETAIN_UNIQUE` 추가 → GREEN → 전체 스위트 rc 0 |
| source | `dev/gateway-edge-cors-20260924` `abd75bd8`(워크트리 `gitops-fix-cors-env-20260924`) |
| target | **`5427fe1e6e5729309687c0ddec3fc1a8b16683f1`**(트리 `0c22b0f3…`, 부모 `eae5c42`, 봇 신원, 고정 시각 04:30:00Z, subject `release: restore the gateway edge CORS dedupe in the production default-filters`, 2경로 M/A) — 재현 확인, 다음 base 검사 3종 통과(대조: main 도 통과) |
| publisher | 렌더 `publisher/cors/render_cors_publisher.py`(9/21 선례에서 counted substitution, 가드 완화 없음) → 헬퍼 `25b30686` · staged `60219f13` · 계약 18/18 · run 단위 18/18 · 음성 대조 5종 거부(listing 행 삭제·행 수·force push·tree sha·target 스위트 생략) · preflight ok → **런 `35955319129` success(04:21~04:23Z)** → gitops main **`5427fe1e`** · post-verify ok · 환경 정책 `main` 만 |
| 런타임 | Argo 강제 refresh → gateway 파드 `devpath-gateway-5649996b78-xc2pf`(04:24:55Z, 재시작 0) env 두 줄 확인 → 16 앱 `5427fe1e` Synced(ollama-gpu Progressing 은 기존 GPU 대기) |
| 라이브 | `GET /mentor-access/invite-rounds` Origin `https://leva.ai.kr` → 200, **ACAO 1개 · Vary 3개**(이전 2·6) ×3회 |

**다음 릴리스의 gitops `base_sha` = `5427fe1e`.**

