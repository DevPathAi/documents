# 핸드오프 2026-09-23 — gitops 결함 3건 **운영 반영 완료**(publisher · 직렬 롤아웃, 무중단) · 다음 candidate 의 base = `5961922b`

> 앞 문서 `handoff-2026-09-23-pipeline-defects-publisher-ready-gate-pending.md` 의 §2(확인 관문 → Part B)가 **끝났다.** 사용자 결정(2026-09-23): "지금 실행" + 되돌림은 "(a) 보류". 이 문서가 앞 문서를 대체한다. 앞 문서 §3·§4 와 9/22 핸드오프 §3·§4 는 사실·교훈으로 유효.
> 정본: 스펙 `specs/2026-09-20-gitops-main-promotion-via-publisher-design.md` **§12.6**(실행 결과), 계획 `plans/2026-09-21-gitops-main-pipeline-defects-via-publisher.md`(「실행 기록 — Part B」), 로그 `plans/…/review-2026-09-23/logs/16~25` 와 스크립트 `part-b-*.sh`.

## 1. 지금 상태 (2026-09-23 10:17Z 실측)

| 영역 | 상태 |
|---|---|
| gitops `main` | **`5961922b9a309055a75bc7302e5c852c5c51d59c`**(target, 트리 `85d71a7f…`) — publisher 런 `35847142542`(봇 디스패치 · 리뷰어 승인 · App fast-forward 10:10:12~15Z) · main CI `35847233195` success · 배포 id `6611409255` · 스크립트 사후 검증 통과. **다음 candidate 의 `gitops.base_sha` = 이 값** |
| 운영 8개 JVM 서비스 | 전부 새 파드(10:13:41~10:16:44Z 기동), **재시작 0**, 템플릿에 `startupProbe`(`/actuator/health/liveness` 5초×60) · `paused` 없음 · Deployment 마다 활성 RS 1개 · Argo 16개 앱 `5961922b` 에서 Synced/Healthy(ollama-gpu Progressing 은 기존) |
| 무중단 여부 | 각 서비스 resume → Ready 12~27초, 기본 전략(surge 1)이라 옛 파드가 새 파드 Ready 뒤 종료. sandbox 만 `maxSurge 0` 이라 약 27초 교체(readiness 503 1회, 설계대로). 부하 최대 2.3/4 CPU. herd 없음 |
| 홈·랜딩 | 배포 `005cf175-…` 그대로. `leva.ai.kr` 200 · `/api/invite-rounds` 200 JSON(다음 landing-last 부터 `_probe_api` 가 직접 확인) |
| GitHub 통제 | 룰셋 2종 active · `enforce_admins` true · 환경 정책 `branch:main` 단독 복원 · 진행/대기 런 0 |
| fence SA | live `imagePullSecrets: [ghcr-pull]` 유지(관리자는 아직 9/21 의 `kubectl-patch` — git 이 이제 같은 값을 선언하므로 Argo 는 diff 없음으로 보고 재적용하지 않았다. 필드가 사라지면 selfHeal 이 되돌린다) |
| r3 자동 롤백 레인 | **닫힘**(다음 승격까지). 비상 수단 = 수동 gitops / 되돌림 publisher(§12.3 F5) |
| 남은 브랜치·워크트리 | origin 에 감사 흔적으로 `fix/pipeline-defects-main-20260921`·`chore/pipeline-defects-publish-20260921`·`…-dispatcher-staged-20260921`·`automation/dispatch-pipeline-defects-main-publish`(9/21 선례와 같음). 로컬 워크트리 `gitops-pipeline-defects-*` 5개와 `dev/pipeline-defects-content` 는 삭제. `documents-pipeline-defects-published-20260923` 는 이 PR 머지 뒤 삭제 |
| 열린 PR | 이 문서가 실린 documents PR 머지 뒤 전 레포 0 |

## 2. 실행 타임라인 (2026-09-23 UTC)

| 시각 | 단계 | 결과 |
|---|---|---|
| 10:05:28 | B1 preflight 재실행 + 클러스터 읽기 | OK — 8개 `paused` 없음 · 재시작 0 · Argo 전부 `30c0e9f7` Synced · 부하 2.8 |
| 10:06:03 | B2 notification pause + Argo 강제 재조정 | 재조정 즉시(`reconciledAt` 갱신) · `Synced / Suspended` · `paused=true` 100초 유지 · 새 sync 없음 → **Argo 는 sync 전 pause 도 되돌리지 않는다**(실측) |
| 10:08:04~06 | B3 나머지 7개 pause(+재조정) | 8/8 paused · 8개 앱 Suspended · 파드 그대로 |
| 10:08:57~10:11:20 | B4 publisher | 정책 추가 → 방아쇠 push → 런 `waiting`(10:09:21) → 정책 복원 → 승인 → 헬퍼 14 step success(target 전체 테스트 27초) → fast-forward → main CI success → 사후 검증 |
| 10:11:45 | B5 1차 | 6/16 앱이 target(Argo 기본 3분 폴링 중) · ai·lcs 템플릿에 startupProbe, paused 라 새 RS 없음 |
| 10:12:27~10:13:08 | B5 강제 재조정 16개 → 2차 | **16/16 target Synced** · 8개 템플릿 startupProbe · 새 RS 0 · 파드 그대로 · `updatedReplicas 0` |
| 10:13:40~10:16:55 | B6 순차 resume | notification 17s → ai 21s → lcs 17s → community 21s → learning 21s → sandbox 27s → platform 22s → gateway 12s, 전부 재시작 0 · Synced/Healthy |
| 10:17:18~31 | B7 사후 | 위 §1 전부 통과. 경고 이벤트 = 기동 중 startupProbe 의 `connection refused`(예산 안에서 정상 통과) |

## 3. 이 세션이 확인한 사실

- **sync 전 `rollout pause` 를 Argo selfHeal 은 건드리지 않는다**(9/21 은 sync 뒤였다). 강제 재조정 직후에도 `Synced / Suspended` 로 유지되고, 새 커밋이 sync 되면 템플릿만 바뀌고(`generation` 증가) 새 RS 는 만들지 않는다 — 9/21 herd 의 직렬화 절차가 실측으로 닫혔다.
- **startupProbe 아래의 JVM 기동은 12~27초** — 예산 300초의 10% 미만. 부하 2 안팎에서는 liveness 만으로도 살았겠지만 herd(부하 61)에서는 이 예산이 생명선이다.
- **Argo 기본 폴링(3분) 때문에 publisher 직후 16개 앱이 순차로 target 에 도달한다** — 강제 재조정으로 40초 안에 전부 맞췄다. 다음 캠페인의 "Argo sync 뒤" 단계도 같은 방식으로 앞당길 수 있다.
- fence SA 의 `imagePullSecrets` 는 live 가 이미 같은 값이라 Argo 가 재적용하지 않는다(managedFields 는 `kubectl-patch`). 수동 의존은 "git 이 선언하지 않음"이었고, 그 결함은 닫혔다.
- publisher 1회 = 2분 23초(첫 정책 쓰기부터 사후 검증까지). 헬퍼 런 55초.

## 4. 교훈

1. **되돌릴 수 없는 지점은 관문에서 두 가지를 같이 묻는다** — 실행 시점과 실패 시 대응. "1" 같은 짧은 답은 첫 질문만 답한 것일 수 있으니 두 질문을 선택지로 다시 묻고 진행했다.
2. **직렬화의 관측은 "관측이 실제로 일어났는가"까지 확인한다** — 리뷰 F3 대로 강제 재조정을 넣었기에 pause 직후 `reconciledAt` 이 갱신된 것을 보고 통과시켰다.
3. **한 Deployment 를 먼저 풀어 본 뒤 나머지를 루프로** — 첫 resume 이 startupProbe 동작을 검증했고, 나머지 7개는 실패 시 자동 pause+RS 0 으로 멈추는 루프로 돌렸다(7개 3분 15초).
4. `kubectl get -o json` 은 managedFields 를 숨긴다 — `--show-managed-fields` 없이는 "관리자 없음"으로 오독한다.

## 5. 다음 세션 착수점

- 이 작업은 **완결**. 다음 candidate 의 `gitops.base_sha` = `5961922b9a309055a75bc7302e5c852c5c51d59c`.
- **홈 develop→master 릴리스 완료(2026-09-23T12:13Z, 홈 PR #92, merge commit `ffaf4b33ca23d61dfd0304f666192a4e6c6ddfa3`, master 트리 = develop `17be1b8a` 트리 `c487e2a5…`, master push CI `test`·`visual-a11y` 성공, Direct Upload 라 운영 무변화 — 홈 운영은 `005cf175-…` 그대로)**. 다음 candidate 의 `home.source_sha` = `ffaf4b33…`, **`dist_sha256` = `00794a107b370a28404edbed62ffdd71891491f8953998d54f7b9eeb740cc237`**(autocrlf=false 워크트리 → `npm ci` → `npm run build` → `createCanonicalHomeArchive('dist')` 의 sha256, 두 번 빌드 동일, 706633 바이트, `_worker.js` 6554 바이트·`_routes.json` 포함), `prior_production_deployment_id` = `005cf175-6e3e-4400-a201-1987ce9d8d84` 그대로. ★빌드가 소스 SHA 를 `appVersion` 으로 심으므로 dist 해시는 **master 커밋으로 빌드해야** 나온다(develop `17be1b8a` 빌드는 `1211d1bc…`)★ `candidate_deployment_id`(preview 배포)와 홈 시각 카탈로그(`rendered_product_sha` `3995dfc7…`)는 캠페인 때 새로 얻는다. landing-last 전: Pages 이력의 비활성 운영 배포 `9814656f`(commit_hash `5b9d6e38`)가 preflight mode 판정에 걸리는지 로컬 `cloudflare_pages.py --action preflight` 로 먼저 확인 · 배포 뒤 첫 확인은 `/api/invite-rounds`·`/api/lead`·`/api/stats`.
- **다음 캠페인 범위는 사용자 결정**: 서비스 develop 의 미릴리스 백로그(2026-09-23 실측, main 대비 gateway +16 · platform +23 · learning +21 · ai +42 · community +4 · notification +4 · lcs +7 · sandbox +10 커밋, frontend·shared 0)를 main 에 올릴지 · 이미지 증거 만료(ai-svc 10/08 · gateway 10/10 · platform 10/15 · 9/21 재빌드 5개 10/21).
- 앞에서 넘어온 것: landing 은 다음 릴리스 id 에(홈 master 선행 릴리스는 위와 같이 완료) · 증거 만료 ai-svc **10/08** · gateway 10/10 · platform 10/15 · admin 10/19 · 나머지 5개 10/21 · governance 룰셋 설계 충돌(et11) · S3 웹 재구성 계획 미작성.
- 사람 단계: 모바일 서명 시크릿 4종 이전 · YouTube 재업로드 · 로그인 캡처 · AdSense 결정.
