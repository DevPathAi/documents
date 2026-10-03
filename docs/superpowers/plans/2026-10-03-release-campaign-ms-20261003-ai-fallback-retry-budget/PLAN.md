# 릴리스 캠페인 `ms-20261003-ai-fallback-retry-budget` — 계획·좌표 (2026-10-03 착수)

## 사용자 결정 (2026-10-03)

1. **지금 시작** — 운영의 M1(폴백 켜짐 = Claude 재시도 0) 위험을 없앤다.
2. **범위** = ai-svc #86·#87 + documents develop→main(프라이버시 도구 #200 포함) + frontend **무해한 최소 변경**
   (매니페스트 `:995` 가 릴리스마다 새 웹 이미지를 강제한다).
3. **승인 = 10/02 방침 그대로** — 인증·staging·운영 off/on/landing·migration 은 AI 가 봇 디스패치로 승인,
   ET13 시각 기준선·NVDA·프라이버시·AI 평가 4개는 **사용자가 누른다**. 운영 변경(10단계) 직전에 다시 확인받는다.

## 착수 전 실측

| 레포 | main | develop | 내용 차이 |
|---|---|---|---|
| devpath-ai-svc | `83cfe79`(squash #85) | `c19ebd1` | 37파일 — #87 M1 수정(36) + #86 멘토 테스트(1). main 고유 내용 0 |
| devpath-frontend | `a08feb6` | `b77efce` | **0** — 열린 PR 0 → `apps/web/README.md`(Flutter 템플릿 문구 그대로)를 실제 README 로 교체 |
| documents | `7f732ac` | `0168f52` | #200 프라이버시 도구 + 문서 다수 |
| devpath-gitops | `a97a1754` | — | develop→main 은 운영 경로가 아니다(publisher 만). base_sha = `a97a1754` |
| 홈 | master | — | 변경 없음, preview 재배포만 |

- 머지 방식: ai-svc main = **squash 만**(룰셋 linear history) · frontend main = merge commit · documents main = merge commit(`7f732ac` 2부모).
- ET13 raw review(diagnostic)는 frontend main push 가 `apps/web/**` 등 경로에 걸릴 때만 자동 생성 → README 가 `apps/web/` 아래라 걸린다.
- 이전 캠페인 `ms-20261002-…` 의 롤백 레인은 gitops publisher(`a97a1754`)로 이미 닫혔다 → main 들을 움직여도 잃는 것이 없다.

## 단계 (10/02 와 같음)

0. 릴리스 머지 — documents·ai-svc(squash)·frontend(README → develop → main). gitops 는 머지하지 않는다.
1. 좌표 수집 — main SHA · 웹 off/on·admin 다이제스트 · ai-svc 이미지 · raw review · 워크플로 sha256.
2. 기준선 비교 — 새 raw review vs 10/02 승인 baseline(run `36922449776`, artifact `11193625116`).
3. ET13 baseline 승인 — 봇 디스패처 → `et13-baseline-approval` **[사용자]**.
4. provenance — 핀 Flutter 3.44.1 절대경로로 web·admin 빌드 → build marker 대조.
5. 홈 preview — master dist → `wrangler pages deploy --branch release-<id>`.
6. candidate spec — 이전 spec 에서 파생. ★`rendered_config_sha256` = `9b7d7031…`(복사 금지)★ · `gitops.base_sha` = `a97a1754` ·
   `base_web_digest` = `902f1ae1…` · `approval_source_sha` = 0단계 뒤 documents main SHA.
7. 증거 5종 — ET13 · Manual AT(**[사용자]** NVDA) · 홈 dist · 프라이버시(**[사용자]**) · AI 평가(**[사용자]**).
8. validate/seal — staging 승인 2건(AI).
9. promote 사전 검증.
10. **[확인 관문] 운영 변경** — migration → promote OFF → ON → canary 900s.
11. **[확인 관문] landing-last**.
12. 기록.

## 이어받은 함정

- release id 재사용 불가 · 성공한 증거는 재디스패치 금지(seal = 적격 producer 정확히 1개).
- 보호 승인은 봇 디스패처 + `approve_gate.py <repo> <run_id> <env> <comment>`(폼 인코딩 `-F environment_ids[]` 는 실패).
- Windows 검증기는 `PYTHONUTF8=1` · `git show <rev>:.github/…` 는 `MSYS_NO_PATHCONV=1` · `cmd | tail; echo $?` 는 tail 의 종료코드.
- PATH 의 flutter 는 3.47.2 — 핀 SDK `D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin/flutter` 를 절대경로로.
- 증거 디스패처 inputs 값 전수검증(허용 집합 밖 값 금지) — 10/02 에 이전 `candidate_spec_sha256` 를 보낸 결함.
- documents main 은 candidate 생성 ~ 프라이버시 증거 사이 동결.
- 운영 반영 판정은 런타임 이미지 다이제스트로.
- 증거 만기 최단 platform-svc 2026-10-15 07:12Z.

## 진행 기록

### 0단계 — 릴리스 머지 (진행)

| 레포 | PR | 비고 |
|---|---|---|
| devpath-frontend | **#245** `docs/web-readme-20261003`→develop | `apps/web/README.md` 템플릿 문구 → 실행·릴리스 안내(서술 전부 코드 대조) |
| devpath-frontend | (다음) develop→main | merge commit · main push 가 web off/on·admin 이미지 + ET13 diagnostic raw review 생성 |
| devpath-ai-svc | **#88** develop→main | squash |
| documents | **#208** develop→main | merge commit · 머지 뒤 main SHA = `approval_source_sha` |
- documents #208 머지 → main **`f52b4a9a385b4eed18ec34f2e37cb35d17f80d78`**(develop 과 트리 동일) = approval_source_sha. 이제부터 프라이버시 증거까지 documents main 동결.
- ai-svc #88 DIRTY(충돌) — main 의 squash(#85)와 #87 이 같은 파일을 다르게 바꿈. sync PR **#89** `chore/sync-main-into-develop-20261003`: 충돌 24파일 develop 쪽 해소, 병합 트리 = develop 트리 `e1c1c42` 바이트 동일.
- (6단계 메모) 10/02 생성기는 `analytics_privacy.approval_source_sha`·`ai_release_eval_config.rendered_config_sha256` 를 건드리지 않는다(그땐 documents main·AI base 가 r3 와 같았다). 이번엔 둘 다 바뀐다 → 변경집합에 추가.
- ai-svc #89 sync 머지(develop `4b283c5`) → #88 head 가 c19ebd1 에 고정돼 DIRTY 유지 → 닫았다 다시 열어 동기화 → CI 녹색 →
  **squash 머지 → ai-svc main `c5614621d0076ced0342353c8dd211a0c0a46cff`**.
- frontend #245 develop 머지(`43e0ecd`) → 릴리스 PR **#246** develop→main(diff = README 1파일).
- (6단계 사전 확인) `ai_release_eval_config`: prompt·tuning·fixture 해시 = ai-svc `src/test/resources/eval`·멘토 자산(83cfe792..c5614621 에서 무변경, 바뀐 리소스는 application.yml 뿐) · `ollama_endpoint_sha256` = 평가 워크플로가 띄우는 평가용 Ollama 엔드포인트(`MissionSpineReleaseEvalEvidence.ollamaEndpointSha256`) → **바뀌는 것은 `rendered_config_sha256` 하나**(`9b7d7031…`). AI 평가 증거는 `ai_source_sha`=candidate ai-svc source_sha · `gitops_source_sha`=base_sha 를 단언(`verify_release_artifacts.py:1724`).
- ai-svc main CI `37111365299` success → 이미지 **`sha256:c3c29ade29d94309ec57cca7c503bce100699db86116a8e0523186118a56919f`**
  (tag = `c5614621…`, registry-evidence `11270077605` 만료 11-02). `mentor-release-inputs` 아티팩트는 1일 만료지만
  AI 평가 워크플로는 입력을 스스로 빌드한다(`mission-spine-release-eval.yml:212`) → 시간 제약 아님.
- frontend #246 머지 → main **`b69e99909bd028682a9c0a3ca11489ac87f90fb9`**(merge commit). **0단계 완료** — documents `f52b4a9a` · ai-svc `c5614621` · frontend `b69e9990`.

### 5단계 결과 — 홈 preview
dist `51e8ef83…` 707,145 B 재계산(createCanonicalHomeArchive) = 이전과 동일 · wrangler 4.146.0 · preview **`3c7d8696-0c29-4d40-901d-10bba3f8a84c`**
(https://3c7d8696.devpath-home-page.pages.dev, branch `release-ms-20261003-ai-fallback-retry-budget`, source abdf57a) · 업로드 0(51 기존) ·
직전 운영 배포 `087c9235-51f3-493c-b56c-d81447e23a54`.

### 1단계(일부) — raw review·빌드 재현
- ET13 Frontend Evidence(push) run **`37112627137`** attempt 1 success · raw review 아티팩트 **`11270965962`**
  `sha256:cd8e266d23c153bc5cd8f29ad8bbbaf5b808351900a8270802c4b71424e12ab9` 만료 10-17.
- build marker web `c8a2c38a…` · admin `2a6d2a1c…` = **로컬 핀 Flutter 빌드와 바이트 일치**(web 1m56s · admin 58s).
- 워크플로 sha256: `et13-evidence.yml` `71ba5845…` · `et13-baseline-approval.yml` `24e959a7…` — 10/02 와 동일.

### 2단계 결과 — 기준선 104/104 **무변경**
10/02 승인 baseline(run `36922449776`, `candidate_set_sha256` `80d6e69a…`) 대비 `compare_baseline.py`:
케이스 104 · 변경 0 · 치수변화 0 · 추가 0 · 삭제 0 (`baseline-diff.json`). README 변경이라 예상대로.

### 3단계 — ET13 baseline 승인 **[사용자 대기]**
디스패처 `automation/dispatch-ms-20261003-ai-fallback-retry-budget` 커밋 `0a2f221`(10/02 `285a83c` 에서 치환 5·유지 4·잔존 0) →
디스패처 런 `37113355753` success → 승인 런 **`37113362836`** waiting · actor/triggering `github-actions[bot]` · attempt 1 · main `b69e9990` ·
env `et13-baseline-approval`(20001533626) · can_approve=true.
URL: https://github.com/DevPathAi/devpath-frontend/actions/runs/37113362836
- 1단계: frontend CI `37112627035` success — web off `16748f26…` · on `e3108c09…` · admin `93b26f9c…`(registry-evidence 11271210969/11270865716/11270881243, 만료 11-02). 직전 운영 웹 `902f1ae1` 과 넷 모두 다름·off≠on → `:979/:993/:995` 충족.

### 3단계 결과 — ET13 baseline 승인 **완료**(사용자 직접 승인)
승인 런 `37113362836` success · 승인 기록 `VelkaressiaBlutkrone` · 승인 baseline 아티팩트 **`11271468059`**
`sha256:7e270bc7…`(로컬 zip sha256 일치) · 만료 11-02 · PNG 104 · `candidate_set_sha256` `80d6e69a…`(10/02 와 동일 = 무변경의 귀결).

### 4단계 결과 — provenance 2건
| 레인 | input_provenance_sha256 | file sha256 | bytes | CR |
|---|---|---|---|---|
| visual | `b9ad3f88…` | `87615a55…` | 1883 | 0 |
| a11y | `f15f7c49…` | `e677c944…` | 1881 | 0 |
★함정 재발 방지: 출력 경로를 `"$OUT\$lane-…"` 로 쓰면 `$lane` 이 펼쳐지지 않아 두 레인이 같은 파일(`candidate-provenance$lane-…`)에 덮어쓴다 → `printf '%s\%s-…' "$OUT" "$lane"` 로 만든다.

### 6단계 결과 — candidate spec **완료**
| 항목 | 값 |
|---|---|
| spec sha256 | **`c23f3b8e1c1dfceb8c87e347a192c94b706d33c968624cd8dce06126ef94a3e1`** |
| 브랜치 / 커밋 | `release/candidate-ms-20261003-ai-fallback-retry-budget` / `0ba21e3`(봇 이름·부모 a97a1754·추가 1파일·blob 해시 일치) |
| candidate 런 | **`37117483543`** attempt 1 success |
| 아티팩트 | **`11272196381`** `sha256:143cb891…` 만료 11-02 |
| 로컬 관문 | 검증기 rc0 · web base rc0 · 홈 하니스 ok · 서비스 이미지 9/9(최단 platform-svc 10-15 07:12Z) |
| 변경 필드 | **34 = 기대 집합 정확** · 잔존 0 · CR 0 |
★10/02 대비 두 필드 추가: `analytics_privacy.approval_source_sha` 7f732ac5→**f52b4a9a** · `ai_release_eval_config.rendered_config_sha256` bfa0126d→**9b7d7031**
(compute_ai_rendered_config.py, 방법 증명 eb413814→bfa0126d 일치 후).

### 7단계 진행 — 증거 디스패치 (2026-10-03 10:49Z)
선례 = 10/02 에 **성공한** 디스패처(frontend `f8ecab4` · documents `db61841` · ai-svc `6fbe6f7`; 결함 버전 8e88e8e·4ad4087 제외).
documents 는 `approval_source_sha` 도 치환(7f732ac5→f52b4a9a). 렌더 단언: frontend 치환 7·입력 15 / documents 4·4 / ai-svc 5·5 전수 통과.
디스패처 커밋: frontend `eb37d31`(baseline 디스패처 위 2번째) · documents `c1ca2e5` · ai-svc `b6bfc3b` — 세 디스패처 런 success.
프라이버시 도구(main, #200 포함) 로컬 종단: `Canonical GitOps candidate authenticated`, 산출 sha = spec sha.

| 증거 | 런 | 상태 |
|---|---|---|
| ③ 홈 dist | `37117678162` | ✅ success(직접 디스패치, 환경 없음) |
| ① ET13 | `37117660640` | 인증 관문 AI 승인(deployment 6826651882) → 진행 중 |
| ② Manual AT | `37117661880` | 인증 관문 AI 승인(6826652084) → ★`manual-at-nvda` 사용자 대기★ |
| ④ 프라이버시 | `37117661578` | ★`mission-spine-privacy-approval` 사용자 대기★ |
| ⑤ AI 평가 | `37117663881` | ★`mission-spine-ai-release-eval` 사용자 대기★ |

판단 재료: `analytics_privacy` 는 `approval_source_sha` 만 바뀌고 6필드 동일 · documents 7f732ac5..f52b4a9a 의 프라이버시 관련 변경은 도구 수정(#200)과 기록 문서뿐 ·
`ai_release_eval_config` 는 `rendered_config_sha256` 만 바뀜 · frontend 변경은 README 1파일(UI·시맨틱스 무변경, ET13 104/104 무변경).
- 사람 관문 3건 **사용자 직접 승인**(NVDA·프라이버시·AI 평가, VelkaressiaBlutkrone). Manual AT `37117661880` ✅ · 프라이버시 `37117661578` ✅ · ET13·AI 평가 실행 중.
- 8단계 준비: gitops validate 디스패처 `390a702`(봇 이름, parent a97a175, 10/02 bfb1972 에서 release id 2곳 치환·잔존 0) — **증거 5/5 뒤 push**.

### 7단계 결과 — 증거 **5/5 success**(사람 관문 3건 사용자 직접 승인)
ET13 `37117660640`(visual 11271814308 · a11y 11272685067) · Manual AT `37117661880`(nvda 11271903958) · 프라이버시 `37117661578`(11272566489) ·
AI 평가 `37117663881`(11271784344) · 홈 dist `37117678162`(11271968032). 워크플로별 오늘 producer 런 정확히 1개.
⚠ `et13-release-auth` 아티팩트 만료 10-04 → 8단계 바로 진행.

### 8단계 — validate/seal **진행 중** (2026-10-03 11:03Z~)
gitops 디스패처 `390a702`(봇 이름 `244265210+devpath-gitops-release[bot]`, parent a97a175, 10/02 bfb1972 에서 release id 2곳 치환) push →
validate 런 **`37118424720`**(bot · main `a97a1754` · attempt 1) · `mission-spine-staging` 1/2 AI 승인(deployment `6826784582`) ·
`Run candidate journeys` 실행 중. 감시·승인 스크립트 `validate_wait.py <since>`(로그 `step8-validate.log`)가 2/2(seal)까지 처리한다.

## 세션 마감 (2026-10-03 11:05Z) — 다음 세션 이관
정지 지점 = 8단계 진행 중. 다음 세션 첫 동작:
1. `gh run view 37118424720 -R DevPathAi/devpath-gitops` — success 면 seal 커밋(candidate 브랜치 head)·매니페스트 수집, 아니면 원인 확인.
   아직 waiting 이면 `PYTHONUTF8=1 py -u validate_wait.py 2026-10-03T11:03:00Z` 재실행(대기 관문을 승인하고 완료까지 기다린다).
2. sealed 매니페스트 → `sealed-release-manifest-budget.json` · coords `validate.*` 채우기 → `py promote.py coords.json preflight`(읽기 전용).
3. **[사용자 확인]** 뒤 `migration --confirmed` → `promote-off` → `promote-on` → `landing`.

### 8단계 1차 결과 — **validate 실패**(seal 단계) · 운영 무변경
validate 런 `37118424720`: staging 2/2 AI 승인(6826784582 · 6826850724) · `Run candidate journeys` **success**
(activation `11272935112` · contextual `11271964766` · home visual-a11y `11272117634`) · `Seal and validate staging` **failure** —
`release seal failed: exactly one frontend producer run is required`(11:10:13Z).
- 사실: ET13 런 `37117660640` 은 11:02:23Z 완료, 두 품질 아티팩트 11:02:20Z 생성(8분 전). **같은 main seal 코드를 실제 API 로 로컬 재현하면
  `SELECTED 37117660640`**(`check_seal_selection.py`). 그 사이 바뀐 입력은 없다 → API 목록(런 `status=success` 필터 또는 `artifacts?name=`) 반영 지연으로
  보이나 **증명은 못 한다**(지나간 시점).
- 재디스패치 안전성: 저니 아티팩트는 매니페스트에 **artifact ID** 로 바인딩(`_require_artifact_identity`·다운로드는 `artifacts/{id}`), 이름 유일성 검색 없음 ·
  「고유 producer 런」 검사는 증거 종류에만·`conclusion=success` 만 · 선례 9/23 r3(validate 1차 실패 → 같은 id 2차 성공).
- ★정정★ `et13-release-auth` 아티팩트(10-04 만료)는 seal·검증기가 쓰지 않는다 — seal 이 확인하는 인증은 승인 baseline `11271468059`(11-02 만료).
- 다음: `check_seal_selection.py` 로 선택 성공 재확인 → gitops 디스패처 브랜치에 봇 이름 **빈 nonce 커밋** push → `validate_wait.py <since>`.
