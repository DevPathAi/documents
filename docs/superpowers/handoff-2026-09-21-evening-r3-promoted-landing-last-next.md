# 핸드오프 2026-09-21 (저녁) — 릴리스 r3 운영 승격 완료(mission-ON) · 남은 것은 landing-last

> 🚨 **§4 의 landing-last 를 그대로 다시 실행하지 말 것 — §9(2026-09-21T10:20Z 추가)를 먼저 읽는다.** landing-last 는 홈의 Pages Functions 를 빼고 배포한다. 한 번 실행했다가 2분 30초 만에 롤백했다.
>
> 직전 문서: `handoff-2026-09-21-afternoon-main-unfenced-r3-next.md`(같은 날 오후). 그 §3 의 r3 를 이 구간이 서비스 재빌드부터 promote ON 까지 끝냈다.
> 산출물·스크립트는 레포 밖 `D:/workspace/dpa/.release-artifacts/ms-20260920-community-flat-pages/r3/`(git 저장소 아님).

## 1. 지금 상태 (2026-09-21T09:00Z 실측)

| 영역 | 상태 |
|---|---|
| 릴리스 | **`ms-20260920-community-flat-pages-r3` 가 운영에 mission-ON 으로 올라갔다.** 900초 canary 통과 · staging rebaseline 완료 |
| gitops `main` | **`30c0e9f717efaad9bd46d47721a61495f4093e96`** — 체인: M `7906bdc7` → additive-services `ec54b37c` → mission-off `7d973847` → mission-on `30c0e9f7`(base = fence 제거 커밋 `fcf97cf6`). main CI success. 봉인 불변(룰셋 2종 active · `enforce_admins` · 세 보호 환경 모두 `main` 단독 · `prevent_self_review` true) |
| 운영 web · admin | web `sha256:a6466f5de1714e12b7fcd01766e0fc0e4f61cf4dab4e6155ea0948ee3fb1c4e1`(frontend `31a7785d` mission-on) · admin `sha256:53813915…fc91` · staging web 도 같은 ON 다이제스트 |
| 서비스 | 9개 전부 Synced/Healthy · 파드 clean(재시작 0). community·notification·lcs·sandbox·learning 은 오늘 재빌드한 새 이미지 |
| 외부 경로 | app 200 · home 200 · OAuth 시작 302 |
| **홈(랜딩)** | **아직 옛 배포** `005cf175-6e3e-4400-a201-1987ce9d8d84` — landing-last 미실행. preview `19be54a3-592f-4ec7-b2ff-9b0caf8228f4`(홈 master `5b9d6e38`)가 대기 중 |
| 자동 롤백 레인 | r3 기준으로 다시 열렸다(롤백 워크플로의 체인이 r3 의 M/S/OFF/ON 을 인식) — 실제 디스패치로 검증한 것은 아니다 |
| 클러스터의 수동 변경 | ServiceAccount `devpath-migration-fence` 의 `imagePullSecrets: ghcr-pull` 하나. 일회성 관문 ConfigMap 은 회수했다. `paused` 잔존 없음 |
| 열린 PR · 세션 워크트리 | 11개 레포 전부 0 · 0 |

## 2. 이 구간이 한 일

1. **서비스 5개 재빌드**(사용자 결정: 5개 전부 · 보호된 main 은 "완화→머지→즉시 복원"을 AI 가 실행). main 은 linear history + strict 체크라 먼저 main 을 develop 에 동기화(PR 5개)한 뒤 develop→main 을 **squash** 로 머지. 트리가 같던 lcs·sandbox·learning 은 README 에 재빌드 사유를 기록. community·notification·lcs 는 `reviews=1`·`last_push_approval` 을 수 초 동안만 0·false 로 내렸다가 복원(스크립트 밖에서도 대조). 새 main: community `fca2fa91` · notification `feb330a9` · lcs `3bb4afa9` · sandbox `75684c0a` · learning `4ecfb32a`.
2. **baseline → provenance → candidate r3 → 증거 5종 → validate/seal**. candidate `19dda79c`, spec sha256 `b5ede99f…4cbcd`(r2 spec 에서 파생, 바뀐 필드 19개가 기대 집합과 정확히 일치), sealed **`fe45981814cae3a95554f857c85319ad08cc22d3`**, manifest sha256 `6db1109c…0d81`. 사람 관문 4건은 "검토 대상이 이미 승인한 것과 바이트 동일"을 실측한 뒤 AI 가 재바인딩 대행(코멘트에 사실 기재).
3. **promote 사전 검증(운영을 건드리기 전)** — promote 의 실제 `verify_service_image_evidence.py` 를 로컬에서 끝까지 실행해 `passed`(9 서비스, GHCR OCI 대조 포함) · 봉인 manifest 가 참조하는 아티팩트 10개 미만료 · 체인 검증기가 현재 main 을 r3 의 base 로 수용. 오전에 fence 가 걸린 채 멈췄던 바로 그 관문을 미리 넘겼다.
4. **운영 변경**(사용자 확인: 지금 실행 · 관문 AI 승인 · 유지보수 승인 = 직전 실측값) — fence 08:05:21Z → Job 22초 → additive-services 08:08:17Z → **사고(§3)** → promote 두 번 재개 → mission-off 08:35:38Z → mission-on 08:40:29Z → canary → staging rebaseline 08:58Z.

## 3. 사고 — platform·sandbox 약 12분 40초 중단 (08:05:21Z~08:18:02Z)

- **원인**: additive-services 가 재빌드한 서비스 5개를 **한꺼번에** 롤링시켰고, fence 에서 풀린 platform·sandbox 까지 단일 노드(4 CPU)에서 JVM 6개가 동시에 기동했다. 각 500m, load avg 61, 컨텍스트 초기화만 27초. 이 서비스들에는 **startupProbe 가 없고** liveness 가 `initialDelay 20s + 3×10s` 라 기동 50초 시점에 죽는다 → 전원 crash loop. 옛 파드가 있는 4개는 서비스가 유지됐고, 0 에서 올라오던 platform·sandbox 만 내려가 있었다.
- **복구**(git·Argo 설정 무접촉): 옛 파드가 살아 있는 4개 배포를 `rollout pause` + 새 ReplicaSet `scale --replicas=0` → CPU 가 비자 platform·sandbox Ready → 4개를 **하나씩** `rollout resume`(각 ~23초, 재시작 0). `spec.paused`·RS scale 은 Argo selfHeal 이 되돌리지 않는다.
- **재개 실패 1회**: 런타임 검증기(`verify_kubernetes_release_runtime.py`)는 컨테이너 `restartCount == 0` · 활성 ReplicaSet 1 · 파드 수 == replicas 를 요구한다. crash loop 을 겪은 platform·sandbox 파드는 Ready 여도 탈락 → 두 파드를 하나씩 교체(각 23~24초 끊김, 08:30~08:31Z) 후 통과.
- **내 판단의 비용**: 재빌드 범위를 5개로 넓히자고 권한 것이 동시 재시작 수를 늘렸다. 만료 위험과 맞바꾼 것이지만 이 비용을 미리 말하지 못했다.

## 4. 다음 — landing-last

`mission-spine-landing-last.yml`(gitops main, 입력 `release_id` 하나, 보호 환경 `mission-spine-production-landing`, 시크릿 `CLOUDFLARE_API_TOKEN`·`RELEASE_EVIDENCE_TOKEN`). 홈 dist(`0247938747ab…e412`, 홈 master `5b9d6e38`)를 운영 Pages 에 올린다. prior deployment 기대값 = `005cf175-6e3e-4400-a201-1987ce9d8d84`, candidate deployment = `19be54a3-592f-4ec7-b2ff-9b0caf8228f4`.

1. **[사람] N01 Cloudflare durable token 이 먼저다** — 9/16~17 에 이 자격 문제로 landing 이 여섯 번 재시도됐다. 명령은 frontend `docs/community-information-architecture/task.md` §5 N01.
2. 디스패치 전에 **landing-last 의 검증을 읽기 전용으로 미리 돌린다**(오늘의 방식): 홈 dist 아티팩트 `10626737227` 미만료 · 운영 배포가 아직 `005cf175-…` 인지 · preview `19be54a3-…` 가 살아 있는지 · 홈 master 가 `5b9d6e38` 그대로인지(바뀌면 candidate 의 `home.source_sha` 와 어긋난다 — 홈 master 에 머지 금지).
3. 봇 디스패치(gitops 디스패처 브랜치 `automation/dispatch-ms-20260920-community-flat-pages-r3` 에 워크플로를 landing-last 로 바꾼 커밋 — 9/16 선례 `08d0990`) → 관문 승인 → 라이브 확인. 실행 직전에 사용자 확인.

기한: 봉인된 아티팩트는 10/21 까지, 서비스 이미지 증거 중 가장 빠른 만료는 ai-svc **10/08**. landing-last 가 이미지 증거를 다시 보는지는 확인하지 않았다 — 2번에서 본다.

## 5. 남은 결함 (고치지 않음 — 다음 publisher 작업의 후보)

- **서비스 Deployment 에 startupProbe 가 없다**(gitops `apps/*/base/deployment.yaml`). 여러 서비스가 함께 재시작되면 herd → crash loop. 고치기 전까지는 **additive-services 직후 롤아웃을 직렬화**한다(§3 의 pause → 하나씩 resume 을 사고 뒤가 아니라 **먼저**).
- **fence ServiceAccount 의 `imagePullSecrets` 가 매니페스트에 없다** — 수동 patch 가 사라지면 마이그레이션 Job 이 이미지를 못 받는다.
- **`sandbox-migration-gate` ConfigMap 은 릴리스마다 손으로 만든다**(운영자 유지보수 승인, 직전 실측값).
- **이미지 증거의 30일 보존이 릴리스 가능 기간을 정한다.** 다음 만료: ai-svc 10/08 · gateway 10/10 · platform 10/15 · admin 10/19 · 오늘 재빌드한 5개 10/21.
- 서비스 main 의 `reviews=1` 은 1인 조직에서 채울 수 없다 — 릴리스마다 "완화→머지→복원"을 사용자 결정으로 반복하고 있다.

## 6. 교훈 (오전·오후분은 앞의 두 핸드오프)

- **사전 검증은 "검사가 통과하는가"만 본다 — "배포가 버티는가"는 보지 못했다.** promote 의 인증 관문은 전부 미리 넘겼지만, additive-services 가 일으키는 동시 재시작은 어떤 검증기에도 없었다. 운영 변경 전에 **"이 커밋이 클러스터에서 무엇을 동시에 일으키는가"**를 따로 묻는다.
- **같은 step 의 두 실패가 다른 원인이었다**(Argo 미수렴 → 재시작 이력). 재개 전에 매번 로그를 읽는다.
- **재개형 워크플로는 실패를 값싸게 만든다.** promote 가 phase 를 스스로 판정하므로, 원인을 고친 뒤 빈 nonce 커밋 하나로 이어 갔다.
- 선배치는 이번에도 통했다 — 마이그레이션 22초.

## 7. 좌표

| 항목 | 값 |
|---|---|
| release id | `ms-20260920-community-flat-pages-r3`(원래 id·r2 는 폐기) |
| candidate / sealed | `19dda79cd23b05ad53b91f95fff449dbe3c206e8` / `fe45981814cae3a95554f857c85319ad08cc22d3` |
| spec / manifest sha256 | `b5ede99fa46a753202d9a4da1218c6fb9de1e7f0516063211648a4fd4c84cbcd` / `6db1109cf9bd7e732b5805b1542d765e1a735f1f26d01a0b6326d5bb91f90d81` |
| 실행 | validate `35574301865` · migration-release `35576029339` · promote OFF `35576130923`(실패)·`35577435349`(실패)·**`35578420751`** · promote ON **`35578880883`** |
| 증거 | 홈 dist `35573198376` · ET13 `35573205914` · Manual AT `35573207617` · 프라이버시 `35573184227` · AI 평가 `35573198282` · baseline `35572702300` |
| 서비스 릴리스 PR | community #41 · notification #18 · lcs #16 · sandbox #35 · learning #68(각 레포의 develop 동기화 PR: #40·#17·#15·#34·#67) |
| 디스패처 브랜치(증거로 유지) | 각 레포 `automation/dispatch-ms-20260920-community-flat-pages-r3` |

## 8. 사람 단계

- **N01 Cloudflare durable token** — landing-last 전.
- 앞에서 넘어온 것: 모바일 서명 시크릿 4종 이전 · YouTube 재업로드 · 로그인 캡처 · AdSense 결정.

## 9. 추가 (2026-09-21T10:20Z) — landing-last 를 실행했고, 되돌렸다

**N01 은 닫혔다.** 사용자가 대시보드에서 `Account → Cloudflare Pages → Edit` 단일 권한 토큰을 만들었고, gitops 환경 `mission-spine-production-landing` 의 `CLOUDFLARE_API_TOKEN` 이 갱신됐다(`2026-09-21T09:57:53Z`). 새 토큰은 landing-last 의 Cloudflare preflight 와 배포를 실제로 통과시켰다 — 더는 로컬 OAuth 세션에 의존하지 않는다.

**실행**: landing-last `35587817335`(봇 디스패치 · attempt 1 · 관문은 사용자 확인 뒤 AI 승인). 사전에 읽기 전용으로 돌려 본 preflight(`cloudflare_pages.py --action preflight`)와 같은 결과로 통과(mode=deploy) → wrangler 가 새 운영 배포 `9814656f-8e6c-4a48-9403-f16e553fb634`(소스 `5b9d6e38`)를 만들었다 → 직후 `capture-new-production` 이 `public dist marker probe failed` 로 실패(9/16 에도 있던 전파 지연 계열).

**회귀**: 새 운영에서 `/api/invite-rounds` 가 **404**(직전 운영 배포·preview 는 200 JSON), `/api/lead` POST 는 405. **landing-last 는 봉인된 `dist` 만 올린다 — CI 의 작업 디렉터리에 `functions/` 가 없어 Pages Functions 와 `_routes.json` 이 빠진다.** CI 의 wrangler 출력에는 `Uploading Functions bundle`·`_routes.json` 줄이 없다(레포 루트에서 올린 preview 에는 있다). 영향: `/updates` 의 초대 회차 목록(9/17 GovTech 핫픽스 기능) · 리드 폼 · 통계 위젯.

**복구**: Cloudflare Pages 롤백 API(`POST …/deployments/005cf175-6e3e-4400-a201-1987ce9d8d84/rollback`)로 직전 운영 배포를 되살렸다 — 10:20:12Z 성공, 10:20:23Z `/api/invite-rounds` 200. 회귀 구간 약 2분 30초. **현재 운영 홈 = `005cf175-…`(소스 `24c6e748`) 그대로**이고 `9814656f` 는 비활성 운영 배포로 이력에 남아 있다. 앱과 gitops main(`30c0e9f7`)은 무변화.

**그래서 §4 는 이렇게 바뀐다**: landing-last 는 파이프라인을 고치기 전에는 올바르게 끝낼 수 없다. 제품 소스는 운영 홈과 같으므로(차이는 테스트·문서 3파일) 미뤄도 방문자가 잃는 것은 없다. 고칠 곳 — 설계부터:

1. **함수를 배포물에 묶는다.** (a) 홈 빌드가 함수를 `dist/_worker.js`(Pages advanced mode)로 컴파일해 봉인 dist 에 넣는다 — 함수가 `dist_sha256` 에 묶이고 landing-last 는 그대로 둘 수 있다. 또는 (b) landing-last 가 `home.source_sha` 의 `functions/`·`_routes.json` 을 체크아웃해 그 자리에서 배포한다 — gitops 통제면 변경이라 publisher 경로. (a)가 봉인의 의미("올라가는 바이트 전부가 해시에 묶인다")에 맞는다.
2. **`/api/*` 라이브 smoke 를 landing-last(배포 직후)와 홈 CI 에 넣는다.** 지금의 smoke 는 페이지 200 만 본다.
3. 다음 landing 때 확인할 것: Pages 이력에 같은 `commit_hash`(`5b9d6e38`)의 운영 배포 `9814656f` 가 남아 있다 — mode 판정(`reuse`)과 "deploy window / production census" 검사가 이것을 어떻게 보는지. 홈 소스가 바뀌면(1번) `home.source_sha` 가 달라져 새 candidate 가 필요하다 — 즉 **landing 은 다음 릴리스(id 새로)에 실린다.** r3 의 앱 승격은 그대로 유효하다.

**교훈**: 사전 검증이 "검사가 통과하는가"와 "제품 파일이 같은가"만 봤고 **"배포물에서 무엇이 빠지는가"**는 보지 않았다. preview 배포와 CI 배포의 wrangler 출력을 나란히 놓았다면 미리 보였다. 배포 뒤 첫 확인은 200 이 아니라 **기능 경로**여야 한다 — 이번에 빨리 잡은 것은 실패한 실행의 로그에서 빠진 줄을 봤기 때문이지, 검사가 잡아서가 아니다.
