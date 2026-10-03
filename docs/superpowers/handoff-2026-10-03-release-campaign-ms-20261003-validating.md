# 핸드오프 — 릴리스 캠페인 `ms-20261003-ai-fallback-retry-budget` 8단계(validate/seal) 1차 실패 · 재디스패치 대기 (2026-10-03 11:30Z 갱신)

> 이 캠페인은 ai-svc M1 근본 수정(폴백을 쓸 수 없을 때 Claude 재시도 예산 유지)을 운영에 올린다.
> **운영은 아직 바뀌지 않았다.** 정지 지점 = 8단계 validate **1차 실패(seal 단계) → 재디스패치 대기**. 10단계(운영 변경)는 사용자 확인 뒤에만.
> 작업 원장(git 밖, 지우지 말 것) = `D:/workspace/dpa/.release-artifacts/ms-20261003-ai-fallback-retry-budget/`
> (`PLAN.md` · `coords.json` · 생성기·렌더러·`promote.py` · `evidence/` · `candidate-provenance/`). 사본 = 이 문서 옆
> `plans/2026-10-03-release-campaign-ms-20261003-ai-fallback-retry-budget/`.

## 1. 다음 세션 첫 동작

### 1-0. validate 1차 결과 (2026-10-03 11:10Z) — **실패, 재디스패치로 푼다**

validate 런 `37118424720`: `mission-spine-staging` 2/2 AI 승인(`6826784582` · `6826850724`) · `Run candidate journeys` **success**
(activation `11272935112` · contextual `11271964766` · home visual-a11y `11272117634`) · `Seal and validate staging` **failure**:
`release seal failed: exactly one frontend producer run is required`(11:10:13Z).

- ET13 런 `37117660640` 은 11:02:23Z 에 끝났고 두 품질 아티팩트는 11:02:20Z 에 생겼다(seal 8분 전).
  **main 의 seal 코드(`select_frontend_evidence_run`)를 실제 API 로 로컬 재현하면 `SELECTED 37117660640`** — 그 사이 바뀐 입력이 없다.
  → GitHub API 목록(런 `status=success` 필터 또는 `artifacts?name=`) 반영 지연으로 보이나 **증명은 못 했다**(지나간 시점).
- 재디스패치는 안전하다: 저니 아티팩트는 매니페스트에 **artifact ID** 로 바인딩되고(`_require_artifact_identity`, 다운로드는 `artifacts/{id}`)
  이름 유일성 검색이 없다 · 「고유 producer 런」 검사는 증거 종류에만, `conclusion=success` 런에만 적용 · 선례 9/23 r3(1차 실패 → 같은 id 2차 성공).

### 1-1. 재디스패치 절차

1. 선택 재확인(읽기 전용): `(cd D:/workspace/dpa/.worktrees/gitops-candidate-1003/scripts/release && GH_TOKEN=$(gh auth token) PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 py <원장>/check_seal_selection.py)` → `SELECTED 37117660640`.
2. gitops 디스패처 브랜치에 봇 이름 **빈 nonce 커밋** → push(디스패처가 validate 를 다시 띄운다):
   ```
   WT=D:/workspace/dpa/.worktrees/gitops-dispatch-1003
   git -C $WT -c core.autocrlf=false -c user.name='devpath-gitops-release[bot]' -c user.email='244265210+devpath-gitops-release[bot]@users.noreply.github.com' commit -q --allow-empty -m "ci: re-dispatch the GitOps validation for ms-20261003-ai-fallback-retry-budget"
   S=$(date -u +%Y-%m-%dT%H:%M:%SZ); git -C $WT push -q origin automation/dispatch-ms-20261003-ai-fallback-retry-budget
   ```
3. 원장에서 `PYTHONUTF8=1 py -u validate_wait.py $S` — 새 봇 런의 `mission-spine-staging` 2건을 승인하고 완료까지 기다린다.
   또 같은 오류면 원인을 다시 본다(재디스패치 반복 금지 — 같은 증상 2회면 seal 코드의 조회 쿼리를 실측으로 추적).

### 1-2. validate 성공 뒤

1. seal 수집: candidate 브랜치 head(= sealed SHA, 커밋 `release(manifest): seal …`) · `release-manifests/releases/<id>.json`
   sha256 · validation 아티팩트 → 원장 `sealed-release-manifest-budget.json`, `coords.json` 의 `validate.{sealed_sha,sealed_manifest_sha256,…}`.
2. 9단계 `py promote.py coords.json preflight`(읽기 전용) — 이미지 9/9 · 체인 `phase=base` · TLS · 잔존 게이트 · 운영이 받을 것.
3. **[사용자 확인]** 뒤 `py promote.py coords.json migration --confirmed` → `promote-off --confirmed` → `promote-on --confirmed` →
   `landing --confirmed`(10/02 순서·교훈 그대로, `render_dispatchers.py` 는 r3 선례 기반 그대로 쓴다).

## 2. 동결 규칙 — 지금 움직이면 안 되는 것

| 브랜치 | 현재 | 이유 |
|---|---|---|
| documents **main** | `f52b4a9a` | candidate `analytics_privacy.approval_source_sha` — seal·promote·롤백 검증기가 현재 head 일치를 요구 |
| ai-svc **main** | `c5614621` | AI 평가 증거의 source |
| 홈 **master** | `abdf57a7` | 홈 dist 증거의 source |
| gitops **main** | `a97a1754` | candidate `gitops.base_sha` — promote 체인의 시작점 |

develop 머지(이 문서처럼)는 괜찮다. **운영 반영 뒤에도 같은 head 들이 롤백 창을 연다** — 다음 캠페인 candidate 전까지 main 을 움직이지 않는다.

⏰ **기한**: 서비스 이미지 증거 최단 **platform-svc 2026-10-15 07:12Z**. (★정정: `et13-release-auth` 아티팩트(10-04 만료)는 seal·검증기가 쓰지 않는다 —
seal 이 확인하는 인증은 승인 baseline `11271468059`(11-02 만료).)

## 3. 좌표

| 항목 | 값 |
|---|---|
| release id | `ms-20261003-ai-fallback-retry-budget` |
| candidate spec | `c23f3b8e1c1dfceb8c87e347a192c94b706d33c968624cd8dce06126ef94a3e1` · 커밋 `0ba21e3` · run `37117483543` · artifact `11272196381` |
| gitops base | `a97a175466962e33ca1823edbb6656091700db81`(폴백 publisher) · base web `902f1ae1…` |
| ai-svc | main `c5614621`(squash #88) · 이미지 `sha256:c3c29ade…`(registry-evidence `11270077605`) · 직전 `107fd20a` |
| frontend | main `b69e9990`(#246) · web off `16748f26…` / on `e3108c09…` · admin `93b26f9c…` |
| documents | main `f52b4a9a`(#208) = `approval_source_sha` |
| 홈 | master `abdf57a7`(무변경) · dist `51e8ef83…` · preview `3c7d8696-0c29-4d40-901d-10bba3f8a84c` · 직전 운영 `087c9235…` |
| AI 렌더 해시 | `9b7d7031…`(a97a1754, 방법 증명 eb413814→bfa0126d 후) |
| ET13 baseline 승인 | run `37113362836` · artifact `11271468059` · 104/104 무변경 |
| provenance | visual `b9ad3f88…` · a11y `f15f7c49…` |
| 증거 5/5 | ET13 `37117660640` · Manual AT `37117661880` · 프라이버시 `37117661578` · AI 평가 `37117663881` · 홈 dist `37117678162` |
| 디스패처 | frontend `0a2f221`→`eb37d31` · documents `c1ca2e5` · ai-svc `b6bfc3b` · gitops `390a702` (모두 `automation/dispatch-<id>`) |
| validate | 1차 run `37118424720` **실패**(seal: frontend producer 런 선택) — 저니는 성공 |

승인 주체: ET13 기준선·NVDA·프라이버시·AI 평가 = **사용자 직접** · 인증 2건·staging = AI(10/02 방침, 2026-10-03 사용자 결정).

## 4. 이번 세션에서 한 것

1. **M1 근본 수정 구현** — 계획 13 Task 를 네이티브로 실행, 최종 리뷰(Critical 0 · Important 3 → 수정 2 · 수용 1) →
   ai-svc PR #87(develop) → 릴리스 #88(main). 스펙·리뷰 기록은 documents #205~#207.
   - 수용한 잔여 위험(스펙 §3.3-3): GPU 가 죽어 있는 동안 Ollama 래치 기한 만료마다 ≤ 30초 창.
   - 보류한 Minor 7건 = `plans/2026-10-03-ai-fallback-availability-aware-retries/review-2026-10-03/RESOLUTION.md`.
2. **캠페인 0~7단계 + 8단계 시작** — 사용자 결정: 지금 시작 · frontend 무해한 최소 변경(`apps/web/README.md` #245) · 승인 10/02 방침.

## 5. 이번 세션의 함정과 교훈

- ★**ai-svc 릴리스 PR 이 DIRTY** — main 이 squash 만 받아 develop 이력이 main 에 없고, 다음 변경이 같은 파일을 바꾸면 3-way 충돌한다.
  → `chore/sync-main-into-develop` PR(#89): 충돌을 develop 쪽으로 해소하고 **병합 트리 = develop 트리**를 단언.
  ★sync 머지 뒤에도 릴리스 PR head 가 옛 SHA 에 고정됐다 → PR 닫았다 다시 열기로 동기화.
- ★**10/02 의 documents·ai-svc 증거 디스패처 첫 커밋(8e88e8e·4ad4087)은 결함 버전**이다 — 선례는 성공한 head(db61841·6fbe6f7)를 쓴다.
- ★10/02 생성기는 `approval_source_sha`·`rendered_config_sha256` 를 다루지 않았다(그땐 안 바뀌었다) — documents main·gitops base 가
  움직이면 두 필드가 변경 집합에 들어간다.
- provenance 출력 경로를 `"$OUT\\$lane-…"` 로 쓰면 `$lane` 이 안 펼쳐져 두 레인이 한 파일에 덮어쓴다 → `printf` 로 만든다.
- **gitops 의 「봇 커밋」은 App 토큰이 아니다** — `git -c user.name='devpath-gitops-release[bot]' -c user.email=…` 로 쓴 커밋을
  내 계정으로 push 한다(candidate 워크플로는 base+1커밋·부모1·추가1파일만 검사). candidate 는 `gh workflow run mission-spine-candidate.yml --ref release/candidate-<id>`.
- 홈 preview 는 npx 캐시의 **wrangler 4.146.0** 으로 버전 고정(`npx --no-install` 는 실패, 최신 해석이 캐시에 없음).
- AI 평가 입력: prompt·tuning·fixture 해시는 ai-svc `src/test/resources/eval`, `ollama_endpoint_sha256` 은 평가 워크플로의 평가용 엔드포인트,
  `mentor-release-inputs` 아티팩트(1일 만료)는 평가가 쓰지 않는다(스스로 빌드).
- 로컬 ai-svc 전체 스위트는 Postgres 필요(Docker + pgvector:pg17 + `DB_URL/DB_USER/DB_PASSWORD`, 없으면 81건 실패).
- 서브에이전트 알림의 `output_file` 이 0바이트일 수 있다 — 전사는 `~/.claude/projects/<proj>/<session>/subagents/agent-<id>.jsonl`.
