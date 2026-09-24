# 핸드오프 2026-09-24 — 릴리스 `ms-20260923-home-functions-gateway-cors-r3` **운영 반영 완결** · 검증기 fix publisher · CORS env publisher · 다음 candidate 의 base = `5427fe1e`

> 앞 문서 `handoff-2026-09-23-pipeline-defects-published.md` 의 「다음 착수점 = 다음 릴리스 캠페인」이 **끝났다.** 홈 Pages Functions 를 봉인 dist 에 묶은 홈 #91(master `ffaf4b33`) 과 gateway CORS 중복 제거 #44/#46(이미지 `8cf6af8d…`) 이 운영에 있다. 사용자 결정(2026-09-24): "migration + promote 실행, landing 은 직전 재확인" → "publisher 로 검증기 수정 게시 후 재개" → "지금 landing 실행" + 후속 "CORS env 수정 publisher 게시, sandbox-migration-gate ConfigMap 회수".
> 정본: 캠페인 계획·좌표·스크립트 `plans/2026-09-23-release-campaign-ms-20260923-home-functions-gateway-cors/`(`PLAN.md` · `coords-r3.json`), publisher 2벌 `plans/2026-09-24-gitops-main-service-applied-revision-via-publisher/` · `plans/2026-09-24-gitops-main-gateway-edge-cors-via-publisher/`(각 `.md` 가 요약, 디렉터리가 스크립트·렌더 산출물·로그).

## 1. 지금 상태 (2026-09-24 04:30Z 실측)

| 영역 | 상태 |
|---|---|
| gitops `main` | **`5427fe1e6e5729309687c0ddec3fc1a8b16683f1`**(CORS env target, 트리 `0c22b0f3…`). 체인 = `5961922b`(base) → `a2c677a` migration → `8b036dc` services → `8b01c02d` `fix(release): bind service applied revision to the app base` → `1d45b63` mission-off → `eae5c42` mission-on → `5427fe1e` `release: restore the gateway edge CORS dedupe in the production default-filters`. **다음 candidate 의 `gitops.base_sha` = `5427fe1e`**(base 검사 3종 통과를 실제 검증기로 확인) |
| 운영 서비스 | gateway `8cf6af8d…`(새 파드 `devpath-gateway-5649996b78-xc2pf` 04:24:55Z, env `…DEFAULT_FILTERS_0=PreserveHostHeader` + `…_1=DedupeResponseHeader=Access-Control-Allow-Origin Access-Control-Allow-Credentials Vary, RETAIN_UNIQUE`) · admin `ec6fd714…` 신규, 나머지 7개 서비스 이미지 불변. 재시작 0. Argo 16개 앱 `5427fe1e` Synced/Healthy(ollama-gpu Progressing 은 기존 GPU 대기) |
| web | mission-on `4fb7acbf…`(파드 `devpath-web-594c4fcf89-ppxpq` 03:17:10Z). canary 900초 통과, staging rebaseline 완료 |
| 홈 | 운영 배포 **`6f7a7e2b-522f-4bf1-b134-2dd2b345f83c`**(landing-last run `35953575812`, 03:58Z; prior `005cf175…`). dist sha256 `00794a10…`(master `ffaf4b33`). `/`·`/api/invite-rounds`·`/api/stats` 200, `/updates` 308→200. **다음 landing-last 의 prior deployment 기대값 = `6f7a7e2b…`** |
| CORS | `GET api.leva.ai.kr/mentor-access/invite-rounds` + `Origin: https://leva.ai.kr` → 200, **Access-Control-Allow-Origin 1개 · Vary 3개**(publisher 전 2개·6개). 홈 랜딩은 동일 출처 함수 경유라 전후 모두 정상 |
| 마이그레이션 | r3 sealed manifest `c95cc641…` — 적용 마이그레이션 없음(`status=validated`). 손으로 만든 ConfigMap `sandbox-migration-gate` 는 사용자 승인으로 **삭제**(04:0xZ) |
| GitHub 통제 | 환경 `mission-spine-production-off` 브랜치 정책 `main` 단독 복원(publisher 2회 모두) · 진행/대기 런 0 · 열린 PR = 이 문서 PR + gitops `fix/staging-cert-lifetime-20260924`→develop |
| staging | sandbox-runner 인증서 3650일로 재발급(9/24 00:42Z). 스크립트 `scripts/release/provision_mission_staging.sh` 의 `-days 30` 은 gitops develop PR 로 수정(main 은 publisher 전용이라 다음 base-advancing 번들에 얹는다) |
| 증거 만기 | r3 sealed 참조 아티팩트 9개 10/24 · landing 증거 `10789682304` 10/24 · 서비스 이미지 증거 중 가장 이른 만기 ai-svc **10/08**(다음 캠페인이 그 전이면 재사용, 뒤면 재생성) |
| 브랜치·워크트리 | origin 감사 흔적: `fix/service-applied-revision-main-20260924`·`chore/service-applied-revision-publish(-dispatcher-staged)-20260924`·`automation/dispatch-service-applied-revision-main-publish`·`fix/gateway-edge-cors-main-20260924`·`chore/gateway-edge-cors-publish(-dispatcher-staged)-20260924`·`automation/dispatch-gateway-edge-cors-main-publish`·`release/candidate-…-r3`(sealed)·`automation/dispatch-…-r3`(gitops/frontend/documents/ai-svc/shared). r2·첫 후보의 워크트리 6개·로컬 6·원격 5 브랜치는 삭제. 남은 로컬 워크트리 = §5 |

## 2. 타임라인 (2026-09-23 23:24Z ~ 2026-09-24 04:27Z, UTC)

| 시각 | 단계 | 결과 |
|---|---|---|
| 9/23 23:24 | frontend #230 develop→main(README 재빌드 #229 + ET13 트리거 마커 #231) | main `ee5a5add` · CI `35933420253` · raw review `35933420238`(push 이벤트) — ★`et13-evidence.yml` 은 `paths:` 필터라 README 만 바뀐 push 로는 안 돈다 → `evidence/et13/release-triggers/<id>.md` 마커★ |
| 9/24 00:00 | r2 좌표 수집 · 동일 대상 확인 · baseline 승인 대행 · provenance · candidate · 증거 4/5 | AI eval 실패 `candidate does not bind exact ET9 release inputs` — `ai_release_eval_config.rendered_config_sha256` 은 base 에서 `kustomize build apps/devpath-ai-svc/base` 렌더 해시(startupProbe 로 `bb9f18df…`→`bfa0126d…`). seal 은 `<release_id>-…` 아티팩트 '정확히 1개' 규칙이라 같은 id 재사용 불가 → **r3 재발급** |
| 00:10~00:25 | r3: baseline `35937165203` · candidate `687c6167`(spec `06cd05d9…`) · 증거 5종 성공 | 홈 dist `35937419487` · ET13 `35937561874` · manual-AT `35937563630` · privacy `35937570293` · AI eval `35937578808` |
| 00:26 | validate 1차 `35938438966` 실패 | staging sandbox-runner mTLS **30일 만기**(9/23 12:10Z) → sandbox-svc readiness 503. 3650일 재발급·파드 재생성 후 재디스패치 |
| 00:5x | validate `35939693144` success → **seal `4a2ab53a`**, manifest `c95cc641…` | preflight(체인 phase base, 9 이미지 ok) |
| 01:09 | [확인] shared migration-release `35941728847` | success → gitops `a2c677a` |
| 01:11~01:23 | promote OFF `35941807967` | fence → Job init `CreateContainerConfigError`(ConfigMap `sandbox-migration-gate` 부재, 손으로 생성 01:17:53Z) → additive-services `8b036dc` → fence 해제(**중단 약 6분**, 01:15~01:21Z) → 런타임 검증 **실패** `Argo Application revision is not exact` |
| 01:26~01:35 | 재개 `35942936280` | 같은 실패 → **검증기 결함**: applied revision 을 `apps/<svc>/base/kustomization.yaml` 마지막 커밋으로 계산하는데 9/23 publisher 가 `deployment.yaml` 만 바꿔 Argo 는 `5961922b` 로 sync → ai·community·lcs·learning·notification 5개 영구 불일치 |
| 01:4x~03:07 | [확인] **검증기 fix publisher** | TDD → target `8b01c02d`(10경로: canary·evidence 도 같은 대조를 하므로 2라운드 확장) · 계약 18/18 · 스위트 359 OK · 런 `35949979763` success(2분 15초) → main `8b01c02d` |
| 03:08~03:12 | promote 재개 `35950184028` | success → mission-off `1d45b63`(web `fba587d5`) |
| 03:13~03:35 | promote ON `35950519691` | 첫 대기 환경이 production-on(순서 assert → 무순서 승인으로 패치) → mission-on `eae5c42` → canary 900s → staging rebaseline → success |
| 03:57~03:59 | [확인] landing-last `35953575812` | 새 홈 배포 `6f7a7e2b…` · 라이브 검증 통과 · **릴리스 완결** |
| 04:0x | ConfigMap 회수 | `sandbox-migration-gate` 삭제(참조는 완료된 Job 파드뿐, Argo 미관리) |
| 04:1x~04:27 | [승인] **CORS env publisher** | TDD(`test_gateway_edge_cors.py`) → target `5427fe1e`(2경로) · 계약 18/18 · run 단위 18/18 · 음성 대조 5종 거부 · 런 `35955319129` success(2분 31초) → main `5427fe1e` → Argo refresh → gateway 파드 교체 → 라이브 ACAO 1개 |

## 3. 결함과 교훈 (이 세션에서 실측한 것)

1. **gitops 검증기 `wait_release_rollouts.py`(+canary·evidence)의 applied revision 은 kustomization.yaml 이 아니라 `apps/<svc>/base` 디렉터리 기준이어야 한다** — Argo 는 base 아래 어떤 렌더 변화에도 sync 한다. 9/23 publisher 가 이 base 위의 모든 릴리스를 막고 있었다. 수정은 `promote_service_digests.SERVICE_BASE_PATHS` 공유 + 체인 문법 슬롯 `fix(release): bind service applied revision to the app base`(services 직후 1회). ★리뷰어가 '경미'로 분류한 `build_production_canary.py:177`·`verify_promotion_evidence.py:223` 도 같은 결함이었다 — 대조 코드를 직접 읽고 판정★
2. **Spring Boot 는 상위 소스(env)의 리스트가 yml 리스트를 통째로 대체한다.** gitops gateway env `…DEFAULT_FILTERS_0=PreserveHostHeader` 하나가 이미지 application.yml 의 `default-filters`(DedupeResponseHeader)를 지웠다. 앱 테스트는 그 env 가 없어 통과. → 이미지 설정을 바꾸는 릴리스는 **gitops env 가 같은 키를 덮는지** 먼저 본다(staging 패치 `staging/mission-spine/patches/gateway.yaml` 은 `_FILTERS_1` 에 dedupe 를 이미 두고 있었다 — 운영 base 와 달랐다).
3. **`sandbox-migration-gate` ConfigMap 은 릴리스마다 손으로 만들고 회수한다**(9/21 핸드오프에 있었지만 preflight 에 없었다). 다음 캠페인 preflight = 선배치(`maintenance-approved=true` + 상한 3종) → promote → 회수.
4. **정적 TLS 시크릿 만기를 preflight 에 넣는다**(`openssl x509 -enddate`). staging runner 인증서가 30일이라 validate 가 sandbox 명령에서만 죽었다.
5. **`ai_release_eval_config.rendered_config_sha256` 은 상수가 아니다** — base 가 ai-svc 렌더를 바꾸면 값이 바뀐다. candidate builder 가 kustomize 로 재계산·단언한다(`build_candidate_spec_r2.py`).
6. **Argo 3분 폴링** — services 커밋 직후 9개 앱에 `argocd.argoproj.io/refresh=normal` 을 걸면 런타임 검증기의 대기 종료 전에 수렴한다.
7. **promote ON 의 첫 대기 환경은 `mission-spine-production-on` 일 수 있다** — 승인 순서를 가정하지 말고 대기 중인 환경을 그때그때 승인(`wait_bot_run` 무순서).
8. Windows 함정: Bash 도구가 `\` 한 겹을 먹는다(긴 패치·변조는 파일로 쓰거나 '유일한 줄 찾기' 로) · `PYTHONUTF8=1` · `MSYS_NO_PATHCONV=1` 아래에서는 `D:/…` 만 · `| tail` 이 종료 코드를 가린다 · Git Bash PATH 가 `D:/` 접두를 무시해 다른 Flutter 를 잡는다(절대경로 `flutter.bat`).

## 4. 다음 착수점

1. **다음 릴리스 캠페인**: gitops `base_sha` = `5427fe1e` · 홈 prior deployment = `6f7a7e2b…` · 서비스 develop 백로그의 릴리스 여부는 사용자에게 · ai-svc 이미지 증거 만기 10/08. §3 의 3·4·6 은 **`promote_r2.py` + `release_ops.py` 에 구현됨**(2026-09-24 05:0xZ, 같은 계획 디렉터리): `preflight` 가 sandbox-runner TLS 시크릿 잔여일(≥30일, staging·운영 5+5)과 stale 게이트 부재를 단언하고 게이트 측정값을 찍는다 · `promote-off`/`promote-resume` 가 `sandbox-migration-gate` 를 직전 실측(+25% 여유, MiB 올림, 행 +100)으로 선배치하고 성공 뒤 회수한다 · promote 단계마다 main 감시 스레드가 새 main 커밋에 Argo 16 앱 refresh 를 건다 · 수동 단계 `tls-check|gate-measure|gate-place|gate-recall|argo-refresh`. 측정은 `postgres:16-alpine` 일회용 파드가 `platform-db` 시크릿을 env 로 받아 preflight.sh 와 같은 쿼리를 읽기 전용으로 실행(5초). 단위 테스트 `test_release_ops.py` 14건. ★Windows 함정 2건: 텍스트 모드 stdin 은 CRLF 로 나가므로 ssh 원격 스크립트는 바이트로 · `kubectl run -i` 는 첫 출력 줄을 잃으므로 wait+logs★
2. **staging 인증서 스크립트** — gitops `fix/staging-cert-lifetime-20260924`(`-days 30`→`3650` ×3) develop PR. main 반영은 다음 base-advancing publisher 번들에 포함(단독 publisher 는 과함).
3. governance 룰셋 설계 충돌(et11) · S3 웹 재구성 계획 — 변동 없음.
4. 정리: §5 의 r3 워크트리는 이 문서 머지 뒤 삭제해도 된다(origin 에 전부 있음).

## 5. 좌표

- 릴리스 id `ms-20260923-home-functions-gateway-cors-r3` · frontend main `ee5a5add39c98bfb0db0db15f4b2388f2b9915c6` · web off `sha256:fba587d5…` / on `sha256:4fb7acbf90b74d9ea08f2708c00ac34d988a56592485ee093b8f54945ac21a7c` / admin `sha256:ec6fd714…` · candidate spec `06cd05d95d2b380863f7aa8ec023e0eb2831b5344412223037d161a69d763bd2` · seal `4a2ab53a91f049d13799932a35c48c1c8fe17734` · manifest `c95cc64184eb6f25cd5712b41df593aaf8b4f379ebd7227f7350836286481375`.
- 런: baseline `35937165203` · candidate `35937332719` · validate `35939693144` · migration `35941728847` · promote OFF `35941807967`→`35942936280`→`35950184028` · promote ON `35950519691` · landing `35953575812` · publisher(검증기) `35949979763` · publisher(CORS) `35955319129`.
- 로컬 워크트리(`D:/workspace/dpa/.worktrees/`): `gitops-main-20260924`(detached) · `gitops-candidate-20260923-r3` · `gitops-dispatch-r3-20260924` · `gitops-fix-applied-revision-20260924` · `gitops-target-20260924` · `gitops-helper-20260924` · `gitops-staged-20260924` · `gitops-fix-cors-env-20260924` · `gitops-helper-cors-20260924` · `gitops-staged-cors-20260924` · `frontend-et13-prov-r2`(r3 빌드도 여기) · `frontend-dispatch-r3-20260924` · `documents-dispatch-r3-20260924` · `ai-svc-dispatch-r3-20260924` · `shared-dispatch-r3-20260924` · `home-candidate-20260923` · `documents-handoff-20260924`(이 문서).
- 로컬 산출물 원본 `D:/workspace/dpa/.release-artifacts/ms-20260923-home-functions-gateway-cors/`(zip·PNG 세트 포함, 약 33MB — 문서 레포에는 스크립트·좌표·로그만 복사).
