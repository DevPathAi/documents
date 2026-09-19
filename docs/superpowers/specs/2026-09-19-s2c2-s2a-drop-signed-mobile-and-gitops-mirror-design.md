# S2c-2 + S2a 쌍 설계 — 웹 릴리스 증거에서 서명 모바일·TalkBack 제거 ↔ gitops 미러

> 2026-09-19. 상위 스펙은 `2026-09-19-web-native-redesign-and-mobile-split-design.md`(이하 "상위 스펙") §6.3~§6.6,
> 착수 근거는 `handoff-2026-09-19-web-redesign-spec-and-mobile-split.md` §4 다.
> 이 문서는 상위 스펙이 "쌍으로 설계한다"고 남겨 둔 두 하위 프로젝트의 설계를 확정한다.
> 실측 기준: frontend `origin/develop` `db955ea` · gitops `origin/main` `4f3ed64`(검증기 4개 파일은 `origin/develop` 과 바이트 동일).

## 1. 목표와 범위

웹 릴리스 계약에서 모바일을 뺀다는 결정(상위 스펙 §6.3)을 두 레포의 코드로 옮긴다.

- **S2c-2 (frontend)**: 수동 접근성 증거 파이프라인에서 서명 APK 인증과 TalkBack 레인을 제거한다.
- **S2a (gitops)**: candidate spec·릴리스 매니페스트 계약에서 서명 모바일 바인딩과 `manual-talkback` 을 제거하고,
  ET13 카탈로그 미러를 S2c-1 이 확정한 13-fixture 값으로 바꾸되 손으로 적은 리터럴을 바이트 핀 파일 파생으로 교체한다.

범위 밖: `apps/mobile` 본체 삭제(S2c-3, 별도 bounded 계획) · frontend `develop → main` 재릴리스와 승격 캠페인 ·
모바일 레포의 독립 서명 파이프라인 · frontend GitHub 환경 삭제(§3.5).

## 2. 결정 (2026-09-19 설계 문답)

| # | 질문 | 결정 | 근거 |
|---|---|---|---|
| Q1 | 서명 모바일을 뺀 `authenticate-inputs` 의 모양 | **candidate 인증만 남긴다** | 상위 결정의 귀결. 보호 환경 `mission-spine-manual-at-auth` 와 읽기 전용 App 경계는 유지 |
| Q2 | 수동 접근성 증거 | **`manual-nvda` 단독**, gitops `QUALITY_EVIDENCE` 6 → 5 레이블 | 상위 결정의 귀결 |
| Q3 | gitops `schema_version` | **in-place 변경**(`schema_version` 1 · `schema-v1.json` 유지) | `schema-v1.json` 은 지금까지 18번 in-place 로 바뀌었고(Flyway target·ET11 계약 등 호환을 깨는 변경 포함) 버전 검사는 최초 도입 뒤 바뀐 적이 없다. exact-key 검증이라 구·신 문서는 버전 없이도 양방향 fail-closed. **상위 스펙 §6.3 의 "(스키마 버전 상승)" 문구는 이 결정으로 정정된다** |
| Q4 | ET13 미러 방식 | **바이트 핀 + 파생**, 파생 불가능한 곳은 대조 테스트 | 같은 계열의 낡은 리터럴 결함이 9/17~9/19 에 일곱 번 나왔다(핸드오프 §6). 신뢰 모델(gitops 는 자기가 승인한 바이트만 믿는다)은 유지 |
| Q5 | gitops main 잠금의 사람 단계 | **AI 가 실행하되 해제 직전에 한 번 확인**(§5.2) | 도구로 도달 가능한 작업. 운영 gitops 의 보호를 일시 해제하므로 직전 확인 |
| 구조 | PR 구성 | frontend 1 PR → gitops 2 PR(develop) → **main 승격 squash 1회** | 상위 결정 B("한 번의 gitops 변경")는 main 잠금 해제·baseline 재승인 횟수에 관한 것. develop PR 을 나눠도 지켜진다 |

**수용한 위험(Q3)**: `mission-spine-promote.yml`·`mission-spine-rollback.yml` 은 대상 릴리스의 candidate 를 main 의 현재
검증기로 `validate_candidate_spec` 한다. S2a 가 main 에 들어간 시점부터 다음 릴리스가 승격될 때까지, 현재 운영 릴리스
`ms-20260916-community-ia`(모바일 필드·12 fixture)의 **자동 롤백 레인은 닫힌다.** 이 릴리스의 landing-last 는 2026-09-16
에 이미 성공했으므로 영향은 롤백 레인뿐이다. 그 기간의 비상 수단은 수동 gitops 다(선례:
`handoff-2026-08-22-et10-release-complete-manual-gitops.md`). 이중 지원(v1+v2 분기)은 서명 모바일 검증 코드와 12-fixture
리터럴을 그대로 남겨 "제거"가 성립하지 않으므로 버렸다.

## 3. S2c-2 — frontend (`chore/s2c2-drop-signed-mobile-talkback` → `develop`)

### 3.1 접합면 실측

수동 NVDA 증거 JSON 에는 원래 서명 필드가 없다(`evidenceKeys('manual-nvda')` 는 공통 키만 반환). 따라서 **증거 JSON 의
모양은 바뀌지 않는다.** 두 레포 사이에서 바뀌는 접합면은 둘뿐이다: (1) candidate spec 의 `quality_evidence_inputs`
(`mobile_test_artifacts` 와 `manual-talkback` 카탈로그 제거), (2) 수동 아티팩트 개수(2 → 1).

### 3.2 워크플로 `mission-spine-manual-at-evidence.yml`

- `authenticate-inputs`: 보호 승인 인증 → 읽기 전용 GitOps 토큰 → App 범위 검증 → candidate 메타데이터 인증 →
  독립 다운로드·해시 → 핀 액션 다운로드 → 바이트·보호 소스 결속까지만 남긴다. 서명 번들 5단계
  (`Authenticate exact signed mobile producer…` · `Independently download and hash signed mobile archive` ·
  `Download exact signed bundle through pinned action` · 검증 단계의 `--signed-root` · 보존 단계의 `stage/signed`)를 삭제한다.
- `approve-talkback` 잡 삭제. 게시 잡의 `needs` 는 `[authenticate-inputs, approve-nvda]`.
- 게시 잡 id·이름을 `publish-manual-nvda` / `Publish manual NVDA evidence` 로 바꾼다("pair"가 거짓이 된다).
  gitops 가 결속하는 것은 승인 잡 이름 `Approve manual NVDA evidence` 와 환경 `manual-at-nvda` 뿐이라 영향이 없다.
  아티팩트 이름 `<release_id>-manual-nvda-run-<run_id>-attempt-1` 은 그대로다.

### 3.3 도구

- `tools/mission_spine_manual_at_evidence.mjs`: `manual-talkback` 레인 정의 · `signedBindingSchema`·`signedBindingKeys` ·
  `validateCandidate` 의 `mobile_test_artifacts` 블록 · `authenticate-signed-artifact` 명령과 서명 producer run 검증 ·
  `evidenceKeys` 의 레인 분기 · 증거 생성·검증의 `mobile` 인자를 제거한다. `validateCandidate` 는
  `quality_evidence_inputs` 의 exact-key 가 `{catalogs, frontend_projection_contract}` 이고 수동 카탈로그가
  `manual-nvda` 하나임을 검증한다 → 구 모양 candidate 는 fail-closed 로 거부된다.
- `tools/mission_spine_release_evidence.mjs` 와 `.test.mjs`: **파일째 삭제.** export 전부가 서명 모바일 전용이다.
  유일한 범용 상수 `frontendRepository` 는 `mission_spine_manual_at_evidence.mjs` 로 옮긴다.
- `tools/mission_spine_protected_approval.mjs`: 허용 목록에서 서명 워크플로·`mission-spine-mobile-signing-android`·
  `manual-at-talkback` 항목 제거. 테스트도 함께.

### 3.4 삭제·이전하는 파일

- 삭제: `.github/workflows/mission-spine-signed-mobile-build.yml` ·
  `tool/release-evidence/catalogs/manual-talkback.v1.json` · `tool/release-evidence/provenance/manual-talkback.v1.json` ·
  `apps/mobile/test/architecture/mission_spine_signed_mobile_workflow_contract_test.dart`.
  서명 워크플로와 서명 provenance 도구는 모바일 레포로 가져가지 않았다. 모바일의 독립 서명 파이프라인을 설계할 때
  frontend `db955eab` 에서 꺼낸다(`git show db955eab:.github/workflows/mission-spine-signed-mobile-build.yml`,
  `…:tools/mission_spine_release_evidence.mjs`).
- 이전: `apps/mobile/test/architecture/mission_spine_manual_at_workflow_contract_test.dart`(152줄)는 S2c-3 에서
  `apps/mobile` 과 함께 사라질 위치에 있다. 새 모양에 맞게 고쳐 `apps/web/test/app/` 으로 옮긴다
  (선례: `et13_baseline_approval_workflow_contract_test.dart`). "서명 단계 없음"·"talkback 잡 없음"을 부정 단언으로 추가한다.

### 3.5 건드리지 않는 것

- GitHub 환경 `manual-at-talkback`·`mission-spine-mobile-signing-android` 는 **삭제하지 않는다.** 환경 시크릿은 다시 읽을
  수 없어, 서명 키 4종이 모바일 레포로 옮겨졌다고 사람이 확인하기 전에 지우면 되돌릴 수 없다. 후속 항목으로만 남긴다.
- ET13 카탈로그(`catalog_sha256` 불변) · `apps/mobile` 본체 · `mobile.yml`.

### 3.6 검증

로컬: node 테스트는 파일을 직접 지정해 실행(`tools/mission_spine_manual_at_evidence.test.mjs`·
`tools/mission_spine_protected_approval.test.mjs`) · 이전한 Dart 계약 테스트 · `melos run analyze` · 워크플로 YAML lint.
무거운 검증(웹 빌드·Playwright·perf-gate)은 CI. PR 전 Codex 리뷰.

## 4. S2a — gitops

### 4.1 PR ① `chore/s2a-drop-signed-mobile-talkback` → `develop` (제거만, ET13 리터럴은 그대로)

| 대상 | 변경 |
|---|---|
| `release-manifests/schema-v1.json` | `$defs/mobileTestArtifacts` 삭제 · `quality_evidence_inputs.required` 에서 `mobile_test_artifacts` · 카탈로그 `required`/`properties` 에서 `manual-talkback` · `quality_evidence.required`/`properties` 에서 `manual_talkback` 제거. `schema_version` 1 유지 |
| `scripts/release/validate_release_manifest.py` | `SIGNED_MOBILE_BINDING_KEYS`·`SIGNED_MOBILE_BINDING_VERSION`·`SIGNED_MOBILE_WORKFLOW`·`SIGNED_MOBILE_FILES` 와 `mobile_test_artifacts` 검증 블록 삭제 · 품질 아티팩트가 서명 아티팩트 id·이름과 달라야 한다는 검사 삭제 · 워크플로 맵·`QUALITY_EVIDENCE`·`QUALITY_EVIDENCE_FILES`·`MANUAL_CATALOG_CONTRACTS` 에서 `manual-talkback` 제거. 수동 증거 공통 필드 일치 루프는 레이블이 하나여도 성립하므로 구조 유지, 메시지의 "trio" 만 정정 |
| `scripts/release/verify_release_artifacts.py` | `validate_signed_mobile_provenance` · `_extract_signed_mobile_archive` · `_download_signed_mobile_archive` · `validate_signed_mobile_bundle` · `_parse_mobile_version` · `verify_signed_mobile_artifact` 삭제 · 수동 증거 검증의 TalkBack 분기(`build_provenance_sha256`·`signed_apk_sha256` 대조) 삭제 · 승인 환경·잡 맵에서 talkback 제거 · `validate_manual_chronology` **삭제** — 함수 전체가 "서명 빌드 완료 뒤에 수동 실행 시작" 한 가지만 검사하고(두 레인 공통), NVDA 고유의 순서 검사는 들어 있지 않다(실측). 웹 빌드에 대한 새 순서 검사는 만들지 않는다(범위 밖, 기존에도 없던 보증) |
| `scripts/release/seal_release_manifest.py` | `signed_mobile_context` 매개변수 · 서명 아티팩트 검증 호출 · `validate_manual_chronology` 호출 삭제. 수동 producer run 단일성 탐색은 레이블 1개로 그대로 동작 — 단위 테스트로 고정 |
| 테스트·픽스처 | `tests/release/test_signed_mobile_manual_trust.py` 의 서명·TalkBack 케이스 삭제, 남는 NVDA 신뢰 케이스는 `test_manual_nvda_trust.py` 로 이름 변경 · `fixtures/valid-candidate-spec.json`·`fixtures/valid-release.json` 에서 해당 필드 제거 · **음성 테스트 추가**: `mobile_test_artifacts`·`manual-talkback`·`manual_talkback` 을 가진 구 모양 문서가 exact-key 로 거부됨 |
| `release-manifests/README.md` | "six distinct quality-evidence" → five · 서명 아티팩트·manual pair 서술 정정 |

### 4.2 PR ② `feat/s2a-et13-pinned-catalog` → `develop` (13-fixture 전환 + 리터럴 → 파생)

- **핀 파일**: frontend 의 고정 커밋에서 세 파일을 바이트 그대로 `release-manifests/contracts/frontend-et13/` 에 복사한다 —
  `catalog.v1.json` · `generated/visual-cases.v1.json` · `generated/a11y-cases.v1.json`. 같은 디렉터리의
  `source-pin.v1.json` 에 출처 레포·커밋 SHA·세 파일의 sha256 을 기록한다. 핀 출처 커밋은 **S2c-2 가 머지된 뒤의**
  frontend `origin/develop` 이다.
- **파생 모듈** `scripts/release/frontend_et13_contract.py`: import 시점에 세 파일을 읽어 아래를 확인하고 하나라도
  어긋나면 예외로 fail-closed 한다.
  1. 코드에 남는 유일한 리터럴인 **파일 sha256 3개**와 바이트 대조
  2. `sha256(catalog.v1.json)` == 두 생성 파일의 `catalog_sha256`
  3. 두 생성 파일의 `fixture_ids`·`projection_matrix`·`projection_contract_sha256` 이 서로 같고 catalog 와도 일치
  4. `case_count == len(cases)`, `surface_case_counts` == cases 에서 재집계한 값
- `validate_release_manifest.py` 의 `FRONTEND_FIXTURE_IDS`·`FRONTEND_PROJECTION_MATRIX`·`FRONTEND_PROJECTION_CONTRACT_SHA256`·
  `FRONTEND_CATALOG_CONTRACTS` 의 `case_count`·`surface_case_counts` 를 이 모듈에서 파생한다. **상수 이름은 유지**해
  validate·verify·seal 의 사용처를 고치지 않는다. 레포 파일을 `Path(__file__)` 기준으로 읽는 선례는
  `verify_promotion_chain.py` 의 `SCRIPT_DIR` 이고, 스크립트만 sparse checkout 하는 워크플로는 없다(실측).
- **case 식별자 재구성은 런타임에 남긴다**(계획 작성 중 정정): `verify_release_artifacts.py` 의
  `_frontend_expected_case_identity` 는 fixture 목록에 프로필(visual = 폭 320·600·840·1240 × light/dark, a11y = 320 light·
  1240 dark)을 곱해 `(fixture_id, case_id, 경로)` 를 재구성하고, `validate_frontend_evidence_bundle` 이 아티팩트의 case 를
  그것과 한 줄씩 대조한다. 이것은 개수 리터럴이 아니라 **카탈로그를 믿지 않는 독립 불변식**이라 핀 파일 읽기로 바꾸면
  방어선이 하나 준다. 런타임은 그대로 두고(입력인 `FRONTEND_FIXTURE_IDS` 만 파생), 대조 테스트가 "재구성 결과 == 핀 파일의
  `cases[*].{fixture_id, case_id, artifact_path}`" 를 잠근다. `_frontend_surface` 의 죽은 `mobile-` 분기는 지운다.
- **표면 집합 리터럴 2곳**: `{"web", "admin", "mobile", "dp_design"}` 가 `validate_release_manifest.py`(921행)와
  `verify_release_artifacts.py` `_validate_surface_counts`(273행)에 있다 → 파생한 `surface_case_counts` 의 키 집합으로 바꾼다.
- **이 작업의 실체는 "final rebind" 다**(계획 작성 중 실측): gitops 계약 픽스처는 frontend 커밋 `dbc1cc90…` 에 결속돼 있다.
  `release-manifests/contracts/frontend-et13/` 의 골든 5파일은 그 커밋의 `evidence/et13/{catalog,evidence,generated-cases,
  manifest}.schema.json`·`release-bundle.v1.json` 과 바이트 동일하고, **그중 스키마 4개가 S2c-1(#223) 이후의 frontend 와
  다르다**(개수 리터럴 변경). `tests/release/test_et13_final_rebind.py` 가 frontend SHA · catalog/projection 해시 · 레인별
  생성 카탈로그 해시 · 골든 해시 · `diagnostic-producer-snapshot.v1.json`(그 커밋의 진단 producer 실행 관측값: provenance·
  manifest·evidence·로컬 candidate 해시, assets/renderer lock 해시)을 고정한다. 따라서 PR ② 는 골든 5파일 재복사 + 핀 3파일
  추가 + candidate 픽스처의 frontend 결속(소스 SHA·카탈로그 해시·fixture 목록·매트릭스·개수) 갱신 + 진단 스냅샷 재생성 +
  픽스처 sha 재결속을 함께 한다. 진단 스냅샷은 값을 지어내지 않고 **핀 커밋에서 돈 frontend `et13-evidence` 실행의
  `et13-unsealed-raw-review-run-<id>-attempt-<n>` 아티팩트**에서 읽는다.
- **파생 불가능한 곳**: `schema-v1.json` 의 `const`(fixture_ids 2곳 · projection matrix · `surface_case_counts` 2곳)는 값을
  13-fixture 로 고치고, 신규 `tests/release/test_frontend_et13_pinned_contract.py` 가 "스키마 const == 핀 파일 파생값"을
  잠근다. `test_et13_evidence_contract.py`·`test_et13_final_rebind.py` 의 리터럴도 같은 모듈에서 읽는다.
- 기대 값(상위 스펙 §6.6, 착수 시 frontend 에서 다시 읽어 대조): 13 fixture ·
  `projection_contract_sha256` `158fdc882238c9459995c0572536a3cec3704e92bd1b28fa2d80907fc0435b78` ·
  `catalog_sha256` `c5acc346a770f5890c6dd06ce616ffc1105eba12b7605e8ad985897e91b00c96` ·
  visual 104 `{web: 72, admin: 16, dp_design: 16}` · a11y 26 `{web: 18, admin: 4, dp_design: 4}`.
- 다음에 fixture 가 바뀔 때 고칠 곳 = **파일 3개 복사 + 해시 3개 + 스키마 const**. 하나라도 빠지면 테스트가 위치를 알려 준다.

### 4.3 main 승격 `release/s2a-main-promotion` → `main` (squash 1건)

- gitops 는 작업 PR 을 `develop` 에, main 에는 `release/*-main-promotion` 브랜치의 squash PR 로 넣는다(main 은 linear 강제).
  `develop` 에는 main 에 없는 55커밋이 있다 → 승격 브랜치는 main 에서 분기해 **①+② 의 경로만** 옮기고, 경로별로
  `git diff origin/develop -- <경로>` 가 0 임을 확인한다.
- **제약**: `verify_promotion_chain.py` 는 진행 중인 승격 체인 사이에 끼어든 main 커밋을 등록된 fix 만 허용한다. 지금은
  진행 중인 릴리스가 없다. 이 승격은 **다음 candidate 를 자르기 전에** 들어가야 하고, 새 candidate 의
  `gitops.base_sha` 는 이 커밋 이후여야 한다.

### 4.4 검증

각 PR 에서 `tests/release` 전체 · gitops CI 의 jsonschema 검증 녹색 · 각 PR 과 승격 PR 에 Codex 리뷰.

## 5. 반영 순서와 사람 단계

### 5.1 순서

```
frontend S2c-2 → develop ─┐
gitops ① → develop        │  (서로 독립, 병행)
                          ▼
gitops ② → develop        핀 출처 = S2c-2 머지 뒤의 frontend develop
                          ▼
frontend S2c-3 → develop  (별도 bounded 계획)
                          ▼
[게이트] 핀 3파일 sha256 == frontend origin/develop 현재 바이트
         + 교차 확인: S2c-2 의 validateCandidate 를 gitops 새 valid-candidate-spec.json 에 실행해 통과
                          ▼
gitops release/s2a-main-promotion: 해제 → squash 머지 → 재봉인 → 봉인 형상 검증
                          ▼
(범위 밖) frontend develop→main → ET13 봇 디스패치·사람 승인 → candidate → 증거 → seal → promote → landing-last
```

핸드오프 §3 의 표와 다른 점: **gitops main 승격을 S2c-3 뒤에 둔다.** S2c-3 은 `pubspec.lock`·`_workspaceLockSha` 를
바꾼다. 핀 3파일의 바이트는 바뀌지 않을 것으로 보지만, 바뀌면 재핀을 위해 main 잠금 해제가 한 번 더 든다. develop
PR 은 잠금과 무관하므로 순서만 바꿔 그 위험을 0 으로 만든다. 교차 확인은 일회성이다 — gitops 픽스처는 자주 바뀌고
frontend 는 PR 마다 perf-gate 약 23분이 돌아, frontend 에 상시 핀하지 않는다.

### 5.2 gitops main 잠금 (실측 2026-09-19)

룰셋 `mission-spine-main-governance`(21194270, active, App 단독 bypass·update 제한) ·
`mission-spine-main-integrity`(21194269, active, bypass 없음·deletion/non-fast-forward/linear) · classic
(`enforce_admins`·push 제한 App 전용·리뷰 1·linear). 봉인 뒤 선례: #148 을 `VelkaressiaBlutkrone` 이 squash 머지.

절차 — **AI 가 실행하고, 해제 직전에 한 번 사용자 확인을 받는다**:

1. 전제조건을 AI 가 모두 채운다: ①② develop 머지·CI 녹색 · 승격 PR CI 녹색 · Codex 리뷰 반영 · §5.1 게이트 통과.
2. 룰셋 2종과 classic 보호의 GET 결과를 스크래치패드에 스냅샷으로 저장한다.
3. 전제조건 요약을 보여 주고 "진행"을 받는다. 그 뒤로는 멈추지 않는다.
4. 최소 해제: governance 비활성 + classic 완화. integrity 는 squash 가 linear 이므로 해제 없이 먼저 시도하고, 머지가
   막힐 때만 해제한다.
5. squash 머지 → 스냅샷대로 복원(스크립트의 `trap` 으로 재봉인 보장) →
   `verify_gitops_write_authority.py` 의 `validate_authority_state` 로 봉인 형상 검증. 실패 시 즉시 보고.
6. 권한 분류기가 거부하면 그 거부 메시지와 함께 복사-실행 가능한 `!` 명령 묶음(해제·머지·재봉인·검증)을 건넨다.

### 5.3 구조적으로 사람 전용인 단계

| 단계 | 시점 |
|---|---|
| ET13 baseline 재승인(시각 검토) — 봇 디스패처로 띄우고 `current_user_can_approve` 확인 뒤 링크 전달, 취소한 대기 실행은 재확인 | frontend 재릴리스 뒤 |
| 수동 NVDA 증거(물리 Windows 호스트 · NVDA 2케이스 · `manual-at-nvda` 승인) | 승격 캠페인 |
| N01 Cloudflare durable token | landing-last 전 |
| 모바일 서명 시크릿 4종 이전 | 모바일 독립 서명 파이프라인 설계 때 |

## 6. 위험

1. **재봉인 누락** — §5.2 의 `trap` + 봉인 형상 검증.
2. **롤백 레인 폐쇄** — §2 에서 수용. 기간 = S2a main 승격 ~ 다음 릴리스 승격.
3. **라이브 첫 실행에서만 드러나는 차이**(2026-08-22 교훈) — 이번 변경은 필드 제거 방향이라 새 라이브 서식 의존이
   생기지 않는다. seal 의 수동 producer run 탐색이 레이블 1개로 동작함은 단위 테스트로 고정한다.
4. **develop ↔ main 표류** — §4.3 의 경로 단위 이관과 diff 0 확인.
5. **리터럴 잔존** — 양 레포에서 `talkback|signed|mobile_test|"mobile"` 과 개수 리터럴(`96`·`24`·`48`·`12`)을
   도구·스키마·테스트·워크플로·README 까지 grep 하고, 결과를 PR 본문에 첨부한다.

## 7. 산출 계획 문서

이 스펙에서 구현 계획 세 개가 나온다.

1. `plans/2026-09-19-s2c2-frontend-drop-signed-mobile-talkback.md` — frontend S2c-2.
2. `plans/2026-09-19-s2a1-gitops-drop-signed-mobile-talkback.md` — gitops PR ①. 1번과 독립이라 병행한다.
3. gitops PR ② + main 승격 계획 — **1·2번이 머지된 뒤에 쓴다.** 입력(핀 출처 커밋, 그 커밋의 ET13 실행 아티팩트)이
   S2c-2 머지 전에는 존재하지 않고, PR ① 이 검증기에서 수백 줄을 지운 뒤의 코드를 기준으로 써야 줄 번호와 코드가 맞는다.
   상위 스펙 §6.5 의 "S2a 계획은 S2c 산출값이 입력이므로 S2c 실행 뒤에 쓴다"와 같은 이유다.

S2c-3 은 별도 bounded 작업이다.

## 8. 실행 결과 (2026-09-19) — 계획 1·2번 완료, 3번의 입력값

| 계획 | PR | 결과 |
|---|---|---|
| 1. frontend S2c-2 | DevPathAi/devpath-frontend#224 | develop `c251b40dceed6c8b7ed69bcbec4c28149e0f0a52` · CI 8개 통과(perf-gate 22m55s) · Codex approve |
| 2. gitops PR ① | DevPathAi/devpath-gitops#160 | develop `3823ac1` · CI 전체 스위트 337건 OK · Codex 지적 1건(minor, 낡은 "all six" 메시지) 반영 · **main 은 `4f3ed64` 그대로** |

실행 중 계획과 달랐던 점은 각 계획 문서 끝의 "실행 기록"에 있다.

**3번 계획(gitops PR ② + main 승격)의 입력값 — 작성 시 frontend `origin/develop` 에서 다시 읽어 대조한다.**

| 항목 | 값 (frontend `c251b40d` 기준) |
|---|---|
| `evidence/et13/catalog.v1.json` sha256 | `c5acc346a770f5890c6dd06ce616ffc1105eba12b7605e8ad985897e91b00c96` (S2c-1 산출값과 동일 — S2c-2 는 카탈로그를 건드리지 않았다) |
| `evidence/et13/generated/visual-cases.v1.json` sha256 | `acd368d92e9850cb51d67dc2d3cc9a6ae7c96e48f58da28f0e353ca0edc741ce` |
| `evidence/et13/generated/a11y-cases.v1.json` sha256 | `cf664d46f5e0b0ea9ab789dbf4afca4dbc71778eff0db05779c3a48392622929` |
| `projection_contract_sha256` · fixture · case | `158fdc88…435b78` · 13 · visual 104 / a11y 26 |
| 진단 스냅샷 출처 후보 | frontend `et13-evidence` run `35426558168`(pull_request, head `75d239e0`), 아티팩트 `et13-unsealed-raw-review-run-35426558168-attempt-1`(id `10579396586`, 만료 2026-10-03) |

주의: 핀 출처 커밋은 **S2c-3 이 머지된 뒤의 develop** 으로 잡는 편이 안전하다(§5.1 의 게이트). S2c-3 이 위 세 파일의 바이트를 바꾸지 않으면
해시는 그대로지만, 진단 스냅샷의 `source_sha` 와 ET13 실행은 그 커밋의 것으로 다시 고른다. 위 아티팩트는 만료 전까지의 예비 출처다.

## 9. 실행 결과 2 (2026-09-19 밤) — S2c-3 · 핀 출처 결정 · frontend 스키마 결함

| 항목 | 결과 |
|---|---|
| S2c-3 | DevPathAi/devpath-frontend#225 → develop `5a47d8837f81ab1ce1809ec05093626d5ba7f931`. 219 파일 · −24,895줄. `pubspec.lock` 은 모바일 전용 43개 제거뿐(남은 153개 전 필드 동일) · `_workspaceLockSha` `30d70407…` · **핀 3파일 sha256 불변** |
| frontend 릴리스 | DevPathAi/devpath-frontend#226(develop→main, #222~#225) → main `9607627616fdd1f369ff58d3fd86440ef6c171f3`. 운영 무영향(승격은 gitops 게이트) |
| PR ② 계획 | `plans/2026-09-19-s2a2-gitops-et13-final-rebind.md`(documents #146) |

**S2c-3 에서 계획에 없던 결합**: `apps/web` 의 테스트 두 개가 `../mobile` 을 읽고 있었다 — 재현성 계약 테스트의 Gradle wrapper 체크섬
검사(같은 `distributionSha256Sum` 을 devpath-mobile 의 `mobile_release_contract_test.dart` 가 고정함을 확인한 뒤 제거)와 브랜드 일관성
검사의 모바일 경로. `mobile.yml` 삭제로 `contract-test-android`·`ios-no-codesign` 체크가 사라졌지만 main 의 필수 체크는
`analyze-test` 하나라 무해하다.

**핀 출처 결정(사용자)**: gitops PR ② 는 **frontend main 릴리스 커밋**에 결속한다. 근거(실측): `et13-evidence.yml` 의
`workflow_dispatch` 는 릴리스 입력 7개가 필수라 develop 에서 진단 모드로 띄울 수 없고, PR 실행의 증거 `source_sha` 는 PR 의 임시
머지 ref 커밋이다. main push 실행의 `source_sha` 는 실제 main 커밋임을 run `35432137657` 로 확인했다. 기존 픽스처의 `dbc1cc9…` 도
main 커밋이었다. 그래서 §5.1 의 순서에서 **frontend 재릴리스가 gitops PR ② 앞으로** 온다(재릴리스는 gitops 에 의존하지 않는다).

**frontend 스키마 결함(같은 계열 아홉 번째)**: main `96076276` 에서 복사한 골든 파일의 잔존 점검이
`evidence/et13/catalog.schema.json` 의 `projection_contract_sha256` `const` 가 12-fixture 시절 해시 `c66d08b6…` 임을 적발했다.
같은 스키마의 `minItems/maxItems` 는 13 인데 이 한 줄만 N06(12→15)·S2c-1(15→13)을 모두 비껴가, `catalog.v1.json` 이 자기 스키마를
통과하지 못하는 상태였다(ET13 스키마는 기계 검증되지 않는다). gitops 가 이 파일을 바이트 핀하므로 **frontend 를 먼저 고친다** —
DevPathAi/devpath-frontend#227(const 수정 + 스키마 최상위 `const`·배열 제약 전부를 카탈로그와 대조하는 계약 테스트). 나머지 스키마
4개는 전수 점검해 이상 없음. 이로 인해 frontend 를 한 번 더 main 에 릴리스하고, PR ② 의 핀은 그 커밋으로 옮긴다(gitops 브랜치는
미푸시 상태라 `repin` 한 번으로 끝난다). 지금 고치지 않으면 나중에 gitops 재결속과 main 잠금 해제가 한 번 더 든다.

**리뷰 수단**: Codex CLI 는 사용 한도 소진(무료 계정, 2026-10-19 까지)이고 대체 서브에이전트 리뷰는 이 PC 에서 빈 응답이다(2회).
S2c-3 은 직접 검증 6항목 + CI 로 머지하고 PR 코멘트에 사실대로 남겼다. PR ② 는 머지 전에 사용자에게 리뷰 방식을 묻는다.

**gitops main 봉인 형상(2026-09-19 실측, main 승격 계획의 입력)**: governance `21194270` active · `update` 규칙 · bypass = App
`4679079` always / integrity `21194269` active · `deletion`·`non_fast_forward`·`required_linear_history` · bypass 없음 / classic:
`enforce_admins` true · checks 없음 · reviews 1(`dismiss_stale`·`require_last_push_approval`, PR bypass = `devpath-gitops-release`) ·
push 제한 = App 단독 · linear · conversation resolution. `gh` 계정 `VelkaressiaBlutkrone` 은 레포 admin.
