# gateway 엣지 CORS dedupe 운영 env publisher — 실행 기록 (2026-09-24)

> 실행 완료. 디렉터리 `2026-09-24-gitops-main-gateway-edge-cors-via-publisher/` 가 스크립트·렌더 산출물·실행 로그. 선례: `2026-09-21-gitops-main-pipeline-defects-via-publisher.md`(mission-on 커밋 위의 `release:` 커밋 = 다음 base).

**Goal:** 릴리스 r3 로 운영에 올라간 gateway `8cf6af8d…`(#44/#46 `DedupeResponseHeader`)가 운영에서 효과가 없던 원인을 gitops 만으로 고친다(이미지 무변경).

**결함(01:22Z·03:42Z 운영 실측):** `GET api.leva.ai.kr/mentor-access/invite-rounds` + `Origin: https://leva.ai.kr` → `Access-Control-Allow-Origin` 2개·`Vary` 6개. 원인 = gitops `apps/devpath-gateway/base/deployment.yaml` 의 env `SPRING_CLOUD_GATEWAY_SERVER_WEBFLUX_DEFAULT_FILTERS_0=PreserveHostHeader`. Spring Boot 는 상위 소스(env)의 리스트가 yml 리스트를 **통째로 대체**하므로 이미지 application.yml 의 `default-filters[0]`(dedupe)이 사라졌다. 앱 테스트 `PublicCorsDedupeTest` 는 그 env 가 없어 통과. staging 패치 `staging/mission-spine/patches/gateway.yaml` 은 이미 `_FILTERS_1` 에 dedupe 를 둔다(운영 base 와 달랐음).

**수정(target `5427fe1e6e5729309687c0ddec3fc1a8b16683f1`, 트리 `0c22b0f3db052ab5a99fa7bfa11a7c01fb37091f`, 부모 `eae5c42`(r3 mission-on, landing 완료 후), 봇 신원, 고정 시각 2026-09-24T04:30:00Z, subject `release: restore the gateway edge CORS dedupe in the production default-filters`, 2경로):**
- `M apps/devpath-gateway/base/deployment.yaml` — env `SPRING_CLOUD_GATEWAY_SERVER_WEBFLUX_DEFAULT_FILTERS_1="DedupeResponseHeader=Access-Control-Allow-Origin Access-Control-Allow-Credentials Vary, RETAIN_UNIQUE"` 추가(`_0=PreserveHostHeader` 유지, 이미지 application.yml 과 글자 그대로 같은 값)
- `A tests/release/test_gateway_edge_cors.py` — 운영 gateway 의 `…DEFAULT_FILTERS_*` 가 정확히 {0: PreserveHostHeader, 1: dedupe} 인지 · dedupe 가 세 헤더·`RETAIN_UNIQUE` 를 덮는지

**Tasks (전부 완료):**
- [x] TDD — RED(`_FILTERS_1` 부재) → GREEN → 전체 스위트 rc 0(361) — dev `dev/gateway-edge-cors-20260924` `abd75bd8`
- [x] target — `make_gateway_edge_cors_target.py` → `target.txt`, 재실행 동일 SHA · 다음 base 검사 3종(`_require_inert_migration_base`·`_require_migration_base_selector`·`_require_service_base_selectors`) 통과(대조: main `eae5c42` 도 통과) · 변경 경로 = 위 2개뿐
- [x] 렌더 — `render_cors_publisher.py <publisher dir> <out dir>`(9/21 선례 counted substitution, **계약 가드 완화 없음** — target 이 검증기를 건드리지 않음) → `rendered/`
- [x] 검증 — 헬퍼 `25b30686`(`chore/gateway-edge-cors-publish-20260924`, 부모 `eae5c42`, 2경로) 계약 18/18 · staged `60219f13` · run 단위 18/18 · **음성 대조 5종 거부**(listing 행 삭제 · `-eq 2`→1 · `push --force` · TARGET_TREE 변조 · target 스위트 생략; 원본 수용) · preflight ok
- [x] 실행 — 사용자 승인("CORS env 수정 publisher 게시") → `run_gateway_edge_cors_main_publish.py --repo-dir … --staged-sha 60219f13… --helper-sha 25b30686…` → 런 `35955319129` success(04:21:24~04:23:55Z, deployment 6630129895) → **main `5427fe1e`** · post-verify ok · 환경 정책 `main` 만 복원(`publish-run.log`)
- [x] 런타임 — Argo 16 앱 refresh → gateway 파드 `devpath-gateway-5649996b78-xc2pf`(04:24:55Z, 재시작 0) env 두 줄 확인 → 라이브 **ACAO 1개 · Vary 3개** ×3회

**교훈:** 이미지 설정을 바꾸는 릴리스는 gitops env 가 같은 키(특히 리스트 인덱스 env)를 덮는지 먼저 본다. 음성 대조 변조는 sed 패턴이 아니라 '유일한 줄 찾기' 로 적용하고 **적용 여부를 단언**한다(Bash 도구의 `\` 소거로 첫 시도 2건이 헛돌았다).
