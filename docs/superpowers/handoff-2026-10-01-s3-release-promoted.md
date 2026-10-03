# 핸드오프 — S3 웹 재구성 릴리스 `ms-20260930-s3-web-redesign-r3` 운영 반영 완료 (2026-10-01)

> 앞 문서: `handoff-2026-09-30-s3-release-sealed-awaiting-promote.md`(PR #191, develop `580584c1`).
> 그 문서가 「10단계 운영 변경 앞에서 정지」로 남긴 것을 이 세션이 **완주**했다.
> 작업 원장(단계별 실측 전부)은 git 밖 `D:/workspace/dpa/.release-artifacts/ms-20260930-s3-web-redesign/`
> (`PLAN.md` 688줄 · `coords.json` · **`promote.py` 하니스**) — 지우지 말 것.

## 1. 결론

**릴리스가 운영에 반영됐다.** 승격 체인 최종 = `phase=mission-on` · `writer_fence_active=false`.

```
base       5427fe1e  (직전 릴리스 ms-20260923-…-r3 의 상태)
migration  5b895232  deploy(devpath-migration): …-r3 sealed 2f41143f…
services   691ff88d  release(services): …-r3 additive-services   (9곳)
off        14ec0688  release(web): …-r3 mission-off   (웹 8cdf906e…)
on         eb413814  release(web): …-r3 mission-on    (웹 3a6ab8db…)   ← 현재 운영
```

| 단계 | 런 | 결과 |
|---|---|---|
| `migration` (shared) | 36794105669 | success |
| `promote-off` | 36794246230 | success |
| `promote-on` (ON + canary 900s + staging rebaseline) | 36794773595 | success |
| `landing-last` 1차 | 36796663491 | **failure** — §4 의 게이트 결함 |
| `landing-last` 재개 | 36797098042 | success (`mode=reuse`, 재배포 없음) |

보호 환경 승인 5건을 봇 디스패처로 처리했다: `mission-spine-migration-release` ·
`-production-off` · `-production-on` · `-staging` · `-production-landing`.

## 2. 운영 반영 실측

**런타임 이미지 다이제스트(SSH, k3s `devpath` 네임스페이스)**

| 워크로드 | 런타임 | spec 대조 |
|---|---|---|
| `devpath-web` | `sha256:3a6ab8dbca5d362632c22c5cf2a01afe6430db33802608bb3f5bcf5e606a211a` | **mission_on** ✓ |
| `devpath-admin` | `sha256:5847d5e93d7a2568616046271b2af2b8375b0c83273e635d5caa24b997875516` | ✓ |
| `devpath-gateway` | `sha256:8cf6af8d91d96d4cd7e66ea0d1175d11758b5f12dd3e6f528fd542219fd59095` | ✓ |

릴리스 9서비스 전부 `1/1` ready·updated·available.
`ollama-gpu` 만 미준비 — GPU 쿼터로 이번 릴리스 **이전부터** 그 상태이고 릴리스 대상이 아니다.

**홈(Cloudflare Pages)**: 배포 `d09631a6` · `dist_sha256 51e8ef83…` · source `abdf57a7`(master).
공개 marker `/.well-known/devpath-release/51e8ef83….json` 가 `release_id ms-20260930-s3-web-redesign-r3` ·
`candidate_spec_sha256 ef51e3ef…` 를 그대로 서비스한다.

**라이브**: `app.leva.ai.kr/` 200 · `leva.ai.kr/` 200 · `/updates` 200 ·
`/api/invite-rounds` 200 `[]` · `/api/stats` 200 (`signups 11`).

DB 추가 적용분 **0건**(`flyway_target 202609051004` 는 직전 릴리스와 동일).

## 3. ★`migration` 단계는 새 SQL 이 0건이어도 건너뛸 수 없다★

앞 세션 PLAN 의 10단계가 *"shared 마이그레이션은 **없다**(변경 0)"* 라고 적었다. **내용 이야기로만 맞다.**

- 후보 spec 의 `rollout.production_order[0]` = `shared-migration`, `shared_migration` 블록이 살아 있다.
- `mission-spine-promote.yml:209` 이 promote-OFF 잡 안에서 `verify_migration_result.py` 를 돌린다.
- 그 검증기(`:255-259`, `:283-309`)는 **아티팩트 이름에 그 릴리스 id 를 요구**한다 —
  `mission-spine-migration-result-<release id>-<run id>-attempt-1`, 미만기, `workflow_dispatch`,
  `head_branch=main`, `head_sha == shared_migration.source_sha`, **적격 런 정확히 1개**.
  → **직전 릴리스의 결과를 재사용할 수 없다.**
- **순서 함정**: OFF 게이트 승인(`:123`)이 이 검증(`:209`)**보다 먼저** 일어난다.
  건너뛰었다면 **OFF 승인을 태운 뒤** 그 스텝에서 실패했다.
- `sandbox-migration-gate` ConfigMap 배치/회수도 그대로 필요하다(마이그레이션 Job 의 init 컨테이너가 없으면 거부).
- 그리고 **이 단계가 gitops main 을 움직인다**(`5427fe1e` → `5b895232`) — 체인 phase 가 `base` → `migration`.

실제 순서 = `migration`(shared) → `promote-off` → `promote-on` → `landing`.

## 4. ★landing-last 게이트의 전파 경쟁(propagation race) — 운영 반영은 성공, 게이트만 실패★

1차 런 로그 실측:

```
00:33:44.740Z  ✨ Deployment complete! … https://d09631a6.devpath-home-page.pages.dev
00:33:45.914Z  Cloudflare release gate failed: public dist marker probe failed
```

**1.17초** 간격이다. `scripts/release/cloudflare_pages.py` 의 `_probe_marker` 가 배포 직후
`<origin>/.well-known/devpath-release/<dist_sha256>.json` 을 찌르는데 **재시도·백오프가 없다**.
게다가 `urllib` 의 `HTTPError` 가 `OSError` 하위라 **404 도 `except OSError` 에 걸려** 연결 실패와 똑같이
`"public dist marker probe failed"` 로 뭉개진다 — `:393` 의 non-200 메시지에 도달하지 못한다.

사후 실측: 세 오리진(`leva.ai.kr` · `d09631a6….pages.dev` · `devpath-home-page.pages.dev`) **전부 HTTP 200**,
payload 가 기대값과 정확히 일치. 즉 **배포는 처음부터 성공했고 운영은 정상이었다.**

**복구 = 재디스패치로 충분하다.** `cloudflare_pages.py:444-471` 의 `preflight` 는
`current_id == prior_id` 일 때만 `mode=deploy` 다. 운영이 이미 새 배포이므로 `else` 분기로 가서
`source_sha` 바인딩 확인 → marker 프로브(이제 200) → 드리프트 확인 → **`mode=reuse`**.
재개 런 로그가 `verified Landing candidate and exact production CAS mode=reuse` 를 찍었고
`Deployment complete!` 가 없다 — **재배포하지 않았다.**

### 후속 과제 (gitops)

1. `_probe_marker` · `_probe` · `_probe_api` 에 **짧은 재시도 + 백오프**를 넣는다. 1.2초는 Cloudflare Pages
   전파에 구조적으로 부족하다.
2. **404 를 연결 실패와 분리**한다. `except OSError` 를 `except HTTPError` / `except URLError` 로 쪼개
   "marker not yet served (404)" 와 "probe could not connect" 를 다른 메시지로 낸다.

★`--branch develop` 가 홈 Pages 프로젝트의 **production 브랜치**다(그래서 `leva.ai.kr` 로 떴다).
 이름만 보고 preview 로 오판하지 말 것★

## 5. 이식한 promote 하니스 (재사용 가능)

`.release-artifacts/ms-20260930-s3-web-redesign/` 에 2026-09-23 캠페인의 `promote_r2.py` 를 이식했다.

| 파일 | 내용 |
|---|---|
| `promote.py` | `preflight`(read-only) · `migration` · `promote-off` · `promote-resume` · `promote-on` · `promote-on-continue` · `landing` · **`landing-resume`** · 클러스터 헬퍼 |
| `render_dispatchers.py` | `migration`·`promote`·`landing` 3종. 선례 리터럴 잔존 금지 + 이 릴리스 값 존재를 단언 |
| `release_ops.py`·`approve_gate.py`·`test_release_ops.py` | 9/23 에서 복사 · 단위 테스트 14 passed |

**운영 변경 단계는 `--confirmed` 없이는 거부한다.** 이번 세션에 승인 표시가 사람의 실제 입력이 아닌 경로로
도착한 일이 있었고, 그때 운영을 건드리지 않았다. 다음 세션도 사람의 확인 없이는 기계적으로 막힌다.

★릴리스 매니페스트 sha256 = **파일 원본 바이트의 sha256**(디스패처의 `release_manifest_sha256`).
 r3 값 `2f41143ffe7a46e95e180e26711f067c6718f21f0d1de3cc22b2bf3a21a9a87a`. 산출법은 9/23 값(`c95cc641…`)을
 그 매니페스트로 재계산해 실증했다★

★sealed 릴리스 매니페스트에는 `*expir*` 키가 하나도 없다 — expiry walk 가 `None` 을 내도 정상이다.
 만기 판정은 `preverify_service_images.py` 가 담당한다★

## 6. 내가 잘못 설계한 검증 2건 (반복하지 말 것)

1. **`main.dart.js` 해시를 `coords.frontend.build_marker` 와 비교했다.** 그 값(`c34e28b1…`)은
   **ET13 증거 빌드**의 해시다(dart-define 이 다르다). 운영 웹은 별도 이미지라 해시가 당연히 다르다
   (운영 실측 `c4271fa4…`). **운영 반영 판정은 런타임 이미지 다이제스트로 한다.**
2. **`/api/lead` 에 POST 를 보냈다.** 쓰기 엔드포인트를 운영에 찔렀다. 빈 바디 `{}` 는 길이 검사를 통과해
   **Apps Script 까지 포워딩된다**(`functions/api/lead.js` 는 `!body` 만 막는다).
   `/api/stats` 의 `signups` 가 11 → 11 로 불변이라 레코드는 생기지 않았지만, 해선 안 되는 확인이었다.
   ★`/api/lead` 는 GET 에 **404**(405 아님)를 준다 — 함수 주석의 「POST 외는 CF 가 405」는 현재 플랫폼 동작과
    다르다. GET 404 를 존재 확인에 쓰면 「없다」고 오판한다★

## 7. 다음 세션 착수점

1. **gitops 후속 과제**(§4) — landing 프로브 재시도·백오프 + 404 분리. `develop` 에서 분기해 PR.
2. **AI provider 폴백 스펙 검토 대기** — `docs/superpowers/specs/2026-09-30-ai-provider-fallback-design.md`(PR #190).
   승인되면 다음은 `writing-plans`.
3. 만기 소멸: ai-svc 이미지 증거(10-08)·마이그레이션 결과 아티팩트(10-08) 모두 **이 릴리스가 소비했으므로
   더 이상 마감이 아니다.**

🤖 Generated with [Claude Code](https://claude.com/claude-code)
