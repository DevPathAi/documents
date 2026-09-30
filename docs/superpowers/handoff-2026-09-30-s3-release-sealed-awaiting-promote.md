# 핸드오프 — S3 릴리스 sealed, 운영 변경 직전에서 정지 (2026-09-30 밤)

릴리스 캠페인 **`ms-20260930-s3-web-redesign-r3`** 이 **sealed** 상태다. 0~9단계가 끝났고
**10단계(운영 변경)는 사용자 확인 관문이라 착수하지 않았다.**

> 작업 원장(단계별 실측·판단 전부)은 **git 밖**에 있다: `D:/workspace/dpa/.release-artifacts/ms-20260930-s3-web-redesign/PLAN.md` + `coords.json`. **지우지 말 것.**

## 지금 상태 한 줄

**운영은 이 세션에서 한 번도 바뀌지 않았다.** staging 은 validate 가 후보 웹을 올렸다가 매번 fail-safe 로 원복했다.

## 재개 지점 — 10단계 [확인 관문]

| 좌표 | 값 |
|---|---|
| release id | `ms-20260930-s3-web-redesign-r3` |
| **sealed SHA** | **`f80f44da34fa1d84548387b9673154b4ef738645`** |
| candidate 브랜치 | `release/candidate-ms-20260930-s3-web-redesign-r3` (gitops) |
| candidate spec sha256 | `ef51e3ef8f71decfdebfbe5b4dbb1e3b7d7edc989265b9ce7c5595bee0407e0f` |
| gitops base (main) | `5427fe1e6e5729309687c0ddec3fc1a8b16683f1` — 체인 검증기가 `phase=base` 로 수용 |
| frontend main | `9c7efee38a83e250848ee023da46e6fe1fafe438` |
| web mission-off | `sha256:8cdf906e1cbe0f6e844c12cb63f622154f70c66845c81cd888d52412c14b6b6d` |
| web mission-on | `sha256:3a6ab8dbca5d362632c22c5cf2a01afe6430db33802608bb3f5bcf5e606a211a` |
| admin | `sha256:5847d5e93d7a2568616046271b2af2b8375b0c83273e635d5caa24b997875516` |
| rollback prior (현 운영 웹) | `sha256:4fb7acbf90b74d9ea08f2708c00ac34d988a56592485ee093b8f54945ac21a7c` |
| home master | `abdf57a7311115826528e068311c0e6ce997fe7f` · dist `51e8ef83…` · preview `d26a6b96-2a4f-465c-8396-d31f7adfd6ed` |
| home 직전 운영 배포 | `6f7a7e2b-522f-4bf1-b134-2dd2b345f83c` |

**남은 단계**: 10 운영 변경(promote OFF → ON → canary 900s → staging rebaseline) · 11 landing-last · 12 기록.
DB 마이그레이션은 **없다**(전 레포 변경 0).

**절차 대본**은 직전 캠페인의 `promote_r2.py` 를 적응시킨다:
`D:/workspace/dpa/.release-artifacts/ms-20260923-home-functions-gateway-cors/promote_r2.py`
(`preflight | migration | promote-off | promote-on | landing` — migration 단계는 이번엔 불필요).

### ⏰ 만기 시계

| 항목 | 만기 |
|---|---|
| **ai-svc 이미지 증거** | **2026-10-08** ← 가장 이르다 |
| platform-svc 이미지 증거 | 2026-10-15 |
| 나머지 서비스·증거 아티팩트 | 2026-10-21 ~ 10-30 |

10-08 을 넘기면 ai-svc 이미지를 재빌드해야 하고 release id 재발급이 따라온다.

## 9단계 사전 검증 (전부 통과, 재실행 없이 신뢰 가능)

- `preverify_service_images.py` — 서비스 9/9 · failures 0
- `verify_promotion_chain.py --current 5427fe1e` — **rc 0** · `phase=base` · `web_phase=base` · `writer_fence_active=false`
- sandbox-runner TLS(SSH 실측) — 운영 **2036-08-19**(3610일) · staging 3643일

## 이 세션이 남긴 영구 산출물

1. **frontend S3 전체가 main 에 들어갔다** — `ee5a5ad` → `9c7efee3`(102커밋 · 178파일 +13,383/−3,336), CI 8/8.
2. **ET13 시각 기준선을 사람이 검토·승인했다** — 104/104 케이스 변경, 검토 산출물 Artifact `https://claude.ai/artifact/GfqcdgyvHD4b14fqSnsjr8`
   (나란히/겹쳐보기/차이 3모드 · 208 PNG). 승인된 세트 `candidate_set_sha256 = 80d6e69a…`.
3. **릴리스 저니 하니스를 S3 UI 에 맞췄다** — home PR **#96**(4건) + **#98**(1건). 이번 릴리스뿐 아니라 앞으로 계속 쓰인다.
4. **로컬 Windows + 핀 Flutter 3.44.1 빌드가 CI(ubuntu) build marker 와 바이트 일치**함을 확인했다
   (web `c34e28b1…` · admin `8def9685…`).

## ★다음 세션이 알아야 할 것 — 이번에 비싸게 배운 것★

### 1. 원리를 발견하면 **그 자리에서 전수 대조**한다

`DpNextActionBand` 는 접근성 이름에 `, 예상 결과: …` 를 덧붙인다. S3 가 진단 화면 버튼 6개를 그 밴드로 옮기면서
`exact: true` / `$` 앵커 셀렉터가 깨졌다. **원리를 #96 에 적어 두고도 sweep 을 하지 않아 한 건만 고쳤고, r2 한 사이클을 통째로 날렸다.**
접두 정규식(`/^미션 열기/`)은 원래 안전했다.

### 2. release id 재발급의 실제 비용

home 소스가 바뀌면 → `dist_sha256` → candidate spec → **증거 5종 전부 무효** → id 재발급.
그리고 **baseline 승인도 재사용할 수 없다** — `verify_release_artifacts.py:307·2905` 가 아티팩트 이름을
`{release_id}-frontend-visual-approved-baseline-run-{run_id}-attempt-1` 로 기대한다(그냥 썼으면 seal 에서 터졌다).
**사람이 다시 해야 하는 것은 `manual-at-nvda` 승인 한 번뿐**이고 나머지는 AI 가 다 돌린다.

### 3. 검증된 사실들 (재조사 불필요)

- **ET13 카탈로그·픽스처는 S3 릴리스 범위에서 diff 0** — 104 케이스가 1:1 대응한다.
- **서비스 8곳은 main 과 트리 동일** — `ahead` 커밋 수는 머지 방식의 산물이다.
- **`NON_RENDERING_RELEASE_PATHS`** (`scripts/visual-evidence.mjs`)가 `e2e/release/` 와
  `tests/release-harness-contract.test.js` 를 담는다 → 하니스만 고치면 홈 렌더 좌표(`rendered_product_sha` `44b82121…` ·
  tree `4e4ec2bd…`)를 **재베이스라인 없이 유지**할 수 있다. 저장소가 이 경우를 미리 허용해 둔 설계다.
- 홈 `provenance_sha256` 은 `e2e/visual/candidate-spec.v2.json` 의 **`runtime` 블록 canonical sha256** 이다
  (`verify_release_artifacts.py:1481`). runtime 이 안 바뀌면 `d04f74b3…` 불변.
- 동일 타깃 판정: **privacy(documents main `7f732ac5` 불변)와 ai eval(ai-svc main `54f634b8` 불변 + gitops
  `apps/devpath-ai-svc` diff 0)은 성립**한다. **NVDA 는 성립하지 않는다** — 그 2개 케이스가 걷는 화면을 S3-P4 가 다시 썼다.

### 4. 접근성: 회귀가 아니라 개선이었다

옛 버전은 개념 태그를 Material `Chip` 으로 그렸고 Flutter 웹이 그걸 **`role=checkbox`** 로 노출했다 —
누를 수 없는 장식 태그가 스크린리더에 토글 컨트롤처럼 보였다. S3 의 `DpTag`(`Container`+`Text`)가 그 유령 역할을 없앴다.
릴리스 저니가 **그 가짜 role 을 「본문이 그려졌다」 신호로 쓰고 있었을 뿐**이다.

### 5. 도구 함정 (실증)

| 함정 | 내용 |
|---|---|
| 리터럴 grep | **렌더를 증명하지 않는다** — `% 진행` 이 새 트리에 1건 있었는데 **주석**이었다. 렌더 위치를 봐야 한다 |
| Python `write_text` | LF 파일을 **CRLF 로 뒤집는다** — 4줄 수정이 674줄 diff 가 됐다. `newline=""` 로 읽고 쓴다 |
| bash heredoc + 한글 | 파이썬에 heredoc 으로 넘긴 한글 리터럴이 매치에 실패한다. 패치 스크립트는 **파일로 써서** 실행한다 |
| `kubectl -o jsonpath` | 키 이름에 점이 있으면(`ca.pem`) 필드 구분자로 읽어 **항상 빈 값**. `-o go-template='{{index .data "ca.pem"}}'` |
| bash `PATH` | `D:/…` 형식은 해석되지 않는다 — MSYS 형식 `/d/…`. 안 그러면 핀 Flutter 대신 기본 SDK 가 잡힌다 |
| `pending_deployments` 응답 | `environment` 가 **문자열**이다. `.environment.name` 으로 파싱하면 승인은 성공해도 `--jq` 가 죽는다 |
| 로컬 체크아웃 | 레포 루트가 릴리스 브랜치라고 가정하지 말 것 — `git show <ref>:<path>` 로 읽는다 |
| 메모리 | 로컬 Flutter dart2js 빌드는 다른 작업과 **병렬 실행 불가**(둘 다 OOM 종료됨) |

### 6. mock 빌드로 UI 를 실측하는 레시피 (재사용 가치 높음)

```
flutter build web --release --no-pub --no-web-resources-cdn \
  --dart-define=USE_MOCK=true --dart-define=MISSION_SPINE_ENABLED=true \
  --dart-define=MOCK_PROFILE=<guest|consent|onboarded|pending> \
  --dart-define=HOME_BASE_URL=http://127.0.0.1:1 --output <dir>
```
정적 서버(SPA 폴백 + `application/wasm` MIME)로 띄우고 Playwright 로 `flt-semantics` 의 role 을 덤프한다.
★`MOCK_PROFILE=onboarded` 는 `/diagnostic` 을 라우터가 돌려보낸다 — 진단 화면은 `guest` 빌드가 필요하다★
★mock 은 데이터가 다르다(문항 2개 · 로그인 버튼에 `(목)` 접미사) — 데이터 차이와 구조적 파손을 구분해야 한다★
★저니 뷰포트는 `devices['Desktop Chrome']` = **1280×720**. 390px 결과로 판단하면 틀린다★

## 지우면 안 되는 것

- `D:/workspace/dpa/.release-artifacts/ms-20260930-s3-web-redesign/` — 원장·좌표·spec·baseline·provenance (git 밖)
- 워크트리: `gitops-candidate-r3`(sealed) · `gitops-main-ms20260930` · `frontend-main-ms20260930`(ET13 빌드가 build marker 와 일치) ·
  `home-master-r3` · `frontend-dispatch-ms20260930` · `gitops-dispatch-ms20260930`
- `D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1/` — 핀 SDK

## 미결 백로그 (이번 캠페인과 별개)

1. **AI provider 폴백 스펙 검토 대기** — `docs/superpowers/specs/2026-09-30-ai-provider-fallback-design.md`(PR #190). 승인되면 `writing-plans`.
2. Ollama 추가 학습 계획 — 별도 프로젝트, 미착수.
3. governance 룰셋 설계 충돌(et11) — 차단급 유일 미해결.
