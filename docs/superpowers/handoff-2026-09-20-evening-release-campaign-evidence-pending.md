# 핸드오프 2026-09-20 (저녁) — 릴리스 캠페인 `ms-20260920-community-flat-pages`: candidate 완료 · 증거 2/5 · 사람 승인 3건 대기

> 직전 문서: `handoff-2026-09-20-gitops-main-promoted.md`(같은 날 오후 — gitops main 승격 완료 시점). 그 §3 의 릴리스 캠페인을 이 세션이 1~4단계까지 진행했다.
> 이 문서는 **지금 어디까지 왔고 다음에 무엇을 하는지**만 고정한다. 산출물·스크립트는 레포 밖
> `D:/workspace/dpa/.release-artifacts/ms-20260920-community-flat-pages/`(git 저장소 아님)에 있다.

## 1. 지금 상태 (세션 종료 시 실측, 2026-09-20)

| 영역 | 상태 | 식별자 |
|---|---|---|
| 앱·홈 운영 | **변화 없음** — `app.leva.ai.kr` 200 · `leva.ai.kr` 200. 홈 운영 배포는 `005cf175-6e3e-4400-a201-1987ce9d8d84` 그대로 | |
| gitops `main` | 승격된 상태 그대로(봉인 불변: 룰셋 2종 active · 환경 `mission-spine-production-off` 는 `main` 단독) | `69e7bd15570f5ba0f271c83b5bd46955cb249c8e` |
| **gitops candidate** | **완료** — `release/candidate-ms-20260920-community-flat-pages`(main + 봇 1커밋·1파일). candidate 워크플로 run `35504481794` success · 아티팩트 `10603192764` | 브랜치 `970a41958cbbd945ece2288d3cae2e02e9a3de9a` · spec sha256 **`e12921324ea5a1e325bb8125631aba7a653375d49ad46c5c91ec7031cf2640a7`** |
| frontend `main` | 운영 미승격(이 캠페인이 올린다) | `31a7785d5f3c73563c8ddb61b69a7a0e07f65f16` |
| **홈 `master`** | **선행 릴리스 완료**(#88 develop→master) — 9/17 핫픽스·토큰 1.1.0 을 따라잡음. preview 배포 `7cc522a3-7d0a-44a3-937a-9a5a91fcb50b` | `17cb9c63079ded36d671e4723b9866af2a16db02` · `dist_sha256` `3eeacb0c5a70f094e127a0518889857510832d9430247160d3712475d57c881d` |
| 서비스 8개 · shared | 9/16 spec 이후 불변 | shared main `9793b8f9` |
| 자동 롤백 레인 | **닫혀 있다**(2026-09-20T05:28Z~, `ms-20260916-community-ia`) — 다음 승격까지. 비상 수단은 수동 gitops | |
| 열린 PR | 5개 레포 전부 0 | |
| 세션 워크트리 | 0(`.worktrees/` 의 `*-release-dispatch-community-ia` 등은 9/16 세션의 잔재) | |

### 증거 5건 (4단계)

| # | 증거 | 실행 | 상태 |
|---|---|---|---|
| ③ | 홈 dist | home `35509794859` | **success** — 아티팩트 `10603864839`. CI 가 로컬 계산 `dist_sha256` 을 재현 |
| ① | 릴리스 ET13 증거 | frontend `35509929188` | **success** — visual `10605435660` · a11y `10605650392` · release-auth `10603979790`. **CI 가 쓴 두 레인의 `provenance.v1.json` 이 candidate 에 미리 묶은 값과 파일 해시·정규 해시 모두 바이트 일치**(내려받아 대조) |
| ② | Manual AT(NVDA) | frontend `35509930022` | 입력 인증 success → **`manual-at-nvda` [사람] 대기** |
| ④ | 프라이버시 승인 | documents `35509922429` | **`mission-spine-privacy-approval` [사용자] 대기** |
| ⑤ | AI 평가 | ai-svc `35509925684` | **`mission-spine-ai-release-eval` [사용자] 대기**(승인 뒤 약 7분) |

대기 3건 모두 actor `github-actions[bot]` · attempt 1 · main · `current_user_can_approve: true`. **승인 대기 실행은 30일 뒤 만료된다**(2026-10-20 무렵). 아티팩트 만료: ET13 baseline·candidate 10/20, raw review 10/03.

## 2. 이번 세션(저녁)이 끝낸 것

1. **ET13 baseline 승인** — 봇 디스패치(`automation/dispatch-ms-20260920-community-flat-pages`, 9/16 선례에서 모바일 서명 step 제거) → 승인 실행 `35495107534` success → 승인된 baseline 아티팩트 `10600418949`. 승인 클릭은 사용자가 "이미 검토했음 — 대신 눌러 줘"를 명시적으로 고른 **이번 건에 한해** AI 가 대행(코멘트에 사실 기재). 기본 규칙(시각 승인은 사람)은 그대로다.
2. **candidate prebinding 절차 확정(spike)** — candidate 는 두 frontend 레인의 **릴리스 모드 input provenance** 해시를 미리 묶어야 하고, 그것은 아티팩트에서 읽는 값이 아니라 `tools/et13_evidence.dart provenance --mode=release_ready` 로 **계산**하는 값이다. 그 명령은 build marker 를 실제 `main.dart.js` 와 대조하므로 로컬 빌드가 필요하다 — Windows 로컬 빌드가 Linux CI 와 **바이트 동일**함을 확인(web `56d5240d…` · admin `80fe8e5d…`).
3. **홈 선행 릴리스** — 홈 `master` 가 9/13 에 머물러 있어, 직전 spec 의 `home` 을 그대로 썼다면 **landing-last 가 9/17 GovTech 핫픽스를 되돌렸을 것**이다. #88 로 master 를 올리고, `dist_sha256` 계산 절차를 9/13 master 로 직전 값(`60020c60…`)을 바이트까지 재현해 증명한 뒤, preview 배포를 만들었다.
4. **candidate 작성** — `build_candidate_spec.py`(모든 값에 출처 단언) → main 의 `validate_release_manifest.py`·`verify_candidate_web_base.py` 로컬 통과 → 봇 커밋 → push → candidate 워크플로 success. **모바일 없는 새 계약(5레이블·13 fixture) 아래 첫 실전 candidate 가 검증기를 통과했다.**
5. **증거 디스패치** — 홈 dist 는 직접, 나머지 넷은 세 레포의 봇 디스패처로(documents `09f6ea0` · ai-svc `0ef3914` · frontend `2b38a0a`). 인증 관문 2개(`mission-spine-et13-release-auth`·`mission-spine-manual-at-auth`)만 AI 가 승인. 8/27 부터 방치된 Manual AT 대기 실행 `33036844359` 는 취소했다.

## 3. 다음 세션 착수점

**먼저 사람 단계 3건**(§5). 그 뒤 재개:

```bash
export MSYS_NO_PATHCONV=1
for r in "devpath-frontend 35509930022" "documents 35509922429" "devpath-ai-svc 35509925684"; do set -- $r
  echo "$1 $2: $(gh api repos/DevPathAi/$1/actions/runs/$2 -q '[.status,(.conclusion // "-")] | @tsv')"; done
gh api repos/DevPathAi/devpath-gitops/branches/main -q .commit.sha                     # 69e7bd15…
gh api repos/DevPathAi/devpath-gitops/branches/release/candidate-ms-20260920-community-flat-pages -q .commit.sha   # 970a4195…
```

세 건이 전부 `completed success` 면 **5단계 — gitops validate/seal** 의 짧은 설계 → 사용자 승인 → 실행. 이 캠페인은 **단계마다 짧은 설계를 승인받고, promote·landing-last 는 각각 직전에 확인**받기로 했다(사용자 결정).

9/16 캠페인이 실제로 밟은 뒤쪽 순서(각 레포의 `origin/automation/dispatch-ms-20260916-community-ia` 가 기록이다):

1. gitops **validate → seal** — `mission-spine-validate.yml`. 봉인 커밋이 candidate 브랜치에 얹힌다(9/16: `975f10c release(manifest): seal … validation attestation`, 작성자 `devpath-release-bot`). gitops README 는 validate 가 staging 에서 후보를 돌리고 되돌린다고 적는다("completed staging reverse duration") — 이 세션이 직접 확인한 것은 아니다.
2. **shared 마이그레이션 릴리스** — `devpath-shared` 의 `mission-spine-migration-release.yml`, 입력 `release_id`·`source_sha`(shared main `9793b8f9…`)·**`sealed_release_sha`**·`gitops_source_sha`. 봇 디스패치.
3. gitops **promote** — additive-services → mission-off → mission-on + canary(9/16 디스패처 커밋 `ea069f8`). **여기서 운영이 바뀐다.**
4. gitops **landing-last** — 홈 dist 를 운영에 올린다. prior deployment 기대값 = `005cf175-6e3e-4400-a201-1987ce9d8d84`. 9/16~17 에는 Cloudflare 자격 문제로 **여섯 번 재시도**했다(`08d0990`…`e0592fa`) → **[사람] N01 durable token 이 먼저다.**

5단계 설계 때 읽을 것: `mission-spine-validate.yml` 의 입력·보호 환경, 9/16 validate 실행의 actor·승인 기록, seal 이 요구하는 아티팩트 목록(이번에는 5레이블).

## 4. 이번 세션(저녁)의 교훈 — 오전·오후분은 앞의 두 핸드오프 §4

- **"복사해서 몇 필드 바꾸면 된다"는 두 번 틀렸다.** candidate spec 은 (a) 로컬 빌드로 계산해야 하는 prebinding 과 (b) 선행 릴리스가 필요한 홈 구간을 품고 있었다. 둘 다 직전 spec 의 **각 값이 어디서 왔는지를 해시 대조로 역추적**하다가 드러났다 — 값의 출처를 모르는 필드는 복사하지 않는다.
- **운영에 직접 배포한 것은 릴리스 브랜치에 빚을 남긴다.** 홈은 9/17 에 develop 에서 wrangler 로 직접 나갔고 master 는 그대로였다. 다음 정식 릴리스가 master 를 집으면 핫픽스가 되돌아간다. 직접 배포 뒤에는 곧바로 릴리스 브랜치를 따라잡게 한다.
- **9/15·9/16 캠페인은 Codex 가 돌렸다** — 절차의 출처는 Claude 세션 기록(`session_search`)이 아니라 `~/.codex/sessions/2026/09/*/rollout-*.jsonl` 이다. 로그 전체를 읽지 말고, 찾는 문자열이 든 **명령 호출만** 골라 뽑는다(§6 의 `scan_codex.py`).
- **frontend ET13 도구는 경로를 문자열로 비교한다**(`startsWith`/`==`). Windows 에서는 `--baseline-root`·`--baseline-approval`·`--build-marker`·`--output` 을 **역슬래시 상대경로**로 줘야 하고, 그 경로는 Python 에서 `chr(92)` 로 조립한다 — Bash 도구는 `"…\\$lane\\…"` 의 이스케이프를 한 겹 더 먹어 두 레인이 같은 파일에 덮어썼다(오늘 같은 계열의 함정 세 번째).
- **결정적 빌드는 줄바꿈에서 깨진다.** 홈 dist·gitops candidate 는 `git -c core.autocrlf=false worktree add` 로 받고, 커밋한 블롭의 CR 바이트를 센다.
- **비교 대상이 실제로 존재하는지 본다.** preview 와 운영 배포의 `/assets/tokens.css` 가 "다르다"고 나왔는데, 그 경로는 dist 에 없어(자산은 해시가 붙는다) 둘 다 폴백 HTML 이었다. 실제 차이는 빌드가 심는 `appVersion` 한 줄뿐이었다.
- **모르는 대기 실행은 정체를 확인한 뒤에만 취소한다.** frontend 의 8/27 Manual AT 실행은 같은 `manual-at-nvda` 환경이라 새 실행과 헷갈릴 수 있어, 새 디스패치 **전에** 취소하고 `completed/cancelled` 를 확인했다.
- 승인 방침을 **환경의 성격으로 나눴다**(사용자 결정): 입력 인증 관문은 AI, 내용 판단(프라이버시·AI 평가)과 시각·NVDA 검토는 사람. "진행"은 맥락마다 다른 말이라, 되돌릴 수 없거나 사람의 판단을 기록하는 지점에서는 선택지로 다시 물었다 — ET13 승인에서 사용자는 "이미 검토했음 — 대신 눌러 줘"를, publisher 에서는 "지금 실행, 사람 단계는 나중에"를 골랐다.

## 5. 사람 단계

1. **프라이버시 승인** — https://github.com/DevPathAi/documents/actions/runs/35509922429 (spec 의 `analytics_privacy` 구간은 9/16 릴리스와 같다)
2. **AI 평가 승인** — https://github.com/DevPathAi/devpath-ai-svc/actions/runs/35509925684 (ai-svc `54f634b8` 불변, gitops 소스 `69e7bd15`)
3. **NVDA 증거** — https://github.com/DevPathAi/devpath-frontend/actions/runs/35509930022 · 물리 Windows + Chromium + NVDA · 후보 소스 `31a7785d` 의 Web release build · 2케이스(frontend `tool/release-evidence/catalogs/manual-nvda.v1.json`): `nvda-web-today-mission-spine`(오늘의 미션의 읽기·포커스 순서) · `nvda-web-next-action-navigation`(다음 행동 Enter → 콘텐츠 → 뒤로 가기 복원). **어느 빌드에서 하는지는 미확인**(staging 에 후보가 올라가는 것은 validate 뒤다) — 필요하면 AI 가 로컬 릴리스 빌드를 띄운다.
   - 1·2 는 검토 후 "대신 눌러 줘"라고 하면 AI 가 클릭만 대행한다(ET13 때와 같은 방식). 3 은 사람만 할 수 있다.
4. **N01 Cloudflare durable token** — landing-last 전. 9/16~17 에 이 자격 문제로 landing 이 여섯 번 재시도됐다.
5. 앞 핸드오프에서 넘어온 것: 모바일 서명 시크릿 4종 이전(그 전까지 frontend 환경 `manual-at-talkback`·`mission-spine-mobile-signing-android` 삭제 금지) · YouTube 재업로드 · 로그인 캡처 · AdSense 결정. Codex 는 2026-10-19 까지 한도 소진.

## 6. 산출물 색인 (`.release-artifacts/ms-20260920-community-flat-pages/`)

| 파일 | 내용 |
|---|---|
| `build_candidate_spec.py` | candidate spec 생성(값마다 출처 단언, 직전 spec 의 직렬화 형식 재현 확인, 낡은 리터럴 스캔) |
| `run_provenance.py` · `candidate-provenance/` | 두 레인의 릴리스 모드 provenance 계산과 결과 |
| `build-marker.v1.json` · `baseline-approval.v1.json` | 계산 입력(raw 아티팩트의 CI build marker · 승인된 baseline 문서) |
| `home-values.json` | `home` 구간·홈 카탈로그에 넣은 값 |
| `build_dispatchers.py` · `approve_gate.py` | 세 레포 디스패처 생성(선례에서 단언 치환) · 단일 대기 승인 헬퍼 |
| `candidate/` · `evidence/` | candidate 아티팩트와 두 레인 증거 패키지의 사본(바이트 대조용) |
| `scan_codex.py` | Codex 세션 로그에서 특정 문자열이 든 명령 호출만 뽑는 스캐너 |
