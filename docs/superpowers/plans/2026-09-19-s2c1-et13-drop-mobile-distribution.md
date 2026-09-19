# S2c-1 — ET13 에서 모바일 distribution 제거 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `devpath-frontend` 의 ET13 증거 계약에서 모바일 fixture 2종과 `mobile` distribution 을 제거해, 웹·관리자만으로 된 13-fixture 카탈로그와 그 투영 계약 해시를 확정한다.

**Architecture:** ET13 계약은 fixture 목록과 표면별 개수를 여러 곳이 동시에 잠근다(도구 상수 · `catalog.v1.json` · 스키마 5종 · 계약 테스트 · 캡처 도구 · 워크플로). 2026-09-17 N06 이 12 → 15 로 늘릴 때 쓴 변경 지점을 그대로 역방향으로 밟는다. 생성 카탈로그와 투영 계약 해시는 손으로 쓰지 않고 도구(`generate`)가 계산한 값을 옮긴다. 이 계획은 `apps/mobile` 자체는 지우지 않는다 — ET13 이 그것을 **빌드·캡처하지 않게** 만들 뿐이다.

**Tech Stack:** Dart(`tools/et13_evidence.dart`) · JSON Schema · Node(`tools/et13/capture.mjs`) · GitHub Actions(`et13-evidence.yml`) · Flutter 테스트

**Spec:** `docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` §6.3–§6.5. 선례 계획: frontend `docs/superpowers/plans/2026-09-17-et13-community-fixtures.md`.

## Global Constraints

- 브랜치 `chore/et13-drop-mobile-distribution`, frontend `origin/develop` 에서 분기. 새 worktree `D:\workspace\dpa\.worktrees\frontend-et13-drop-mobile` 에서 작업한다. 주 checkout `D:\workspace\dpa\devpath-frontend` 는 건드리지 않는다.
- 남는 fixture 13개의 **id·순서·artifact 경로는 바꾸지 않는다.** 두 모바일 id(`mobile-today-available`, `mobile-content-reading`)만 목록에서 뺀다.
- 제거 후 확정 값(전부 파생 가능해야 한다): fixture 13 · visual `13 × 4 × 2 = 104`(web 72 · admin 16 · dp_design 16) · a11y `13 × 2 = 26`(web 18 · admin 4 · dp_design 4) · owner `web 9 · admin 2 · dp_design 2` · distribution `web 11 · admin 2` · 원시 리뷰 아티팩트 `10 + 104 + 26 + 11 × 4 = 184` 파일.
- `evidence/et13/generated/*.json` 은 손으로 편집하지 않는다. `dart run tools/et13_evidence.dart generate` 로만 만든다.
- `projection_contract_sha256` 은 도구가 출력한 값을 `tools/et13_evidence.dart` 의 `_projectionContractSha256` 과 `catalog.v1.json` 에 **같은 값으로** 옮긴다(`validate` 가 대조한다).
- `baseline_status` 는 `pending_external_review` 그대로 둔다.
- fixture 수를 바꿀 때의 교훈(같은 결함이 세 번 나왔다): 리터럴 grep 을 도구·스키마·테스트뿐 아니라 **`capture.mjs`, 합계 검사, `.github/workflows`** 까지 넓힌다. Task 4 가 이 전수 검사다.
- 로컬에서 `flutter build web`·Playwright 를 돌리지 않는다(메모리 제약). 캡처는 PR 의 `produce-atomic-pair` 잡(diagnostic 모드)이 판정한다.
- 이 PC 에서 `packages/dp_design/test/theme/dp_code_font_test.dart` 1건은 CRLF 때문에 로컬 실패가 정상이다(CI 는 통과). 이 계획에서 고치지 않는다.
- 커밋은 Conventional Commits + `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

---

### Task 1: 계약 테스트를 13-fixture 로 먼저 바꾼다 (red)

**Files:**
- Modify: `apps/web/test/app/et13_evidence_catalog_contract_test.dart` (`_fixtureIds`, 표면별 개수 맵 277–290행 부근, schema `minItems/maxItems` 단언)
- Modify: `apps/web/test/app/et13_evidence_producer_contract_test.dart:130` (`['web', 'admin', 'mobile']`), `:859` (`'mobile': 'apps/mobile/lib/et13_evidence_main.dart'`)

**Interfaces:**
- Produces: 13-fixture 계약을 요구하는 실패 테스트. Task 2·3 이 이것을 녹색으로 만든다.

- [ ] **Step 1: worktree 와 브랜치**

```bash
git -C /d/workspace/dpa/devpath-frontend fetch origin
git -C /d/workspace/dpa/devpath-frontend worktree add -b chore/et13-drop-mobile-distribution /d/workspace/dpa/.worktrees/frontend-et13-drop-mobile origin/develop
cd /d/workspace/dpa/.worktrees/frontend-et13-drop-mobile && dart pub get --enforce-lockfile
```

- [ ] **Step 2: `et13_evidence_catalog_contract_test.dart` 수정**

`_fixtureIds` 목록에서 아래 두 줄을 지운다(나머지 13줄의 순서는 그대로):

```dart
  'mobile-today-available',
  'mobile-content-reading',
```

표면별 개수 기대 맵 두 개에서 `'mobile': 16,` 과 `'mobile': 4,` 줄을 지운다. 지운 뒤 두 맵은 정확히 다음이어야 한다:

```dart
      'web': 72,
      'admin': 16,
      'dp_design': 16,
```

```dart
      'web': 18,
      'admin': 4,
      'dp_design': 4,
```

같은 파일에서 개수를 숫자로 단언하는 곳은 기준 커밋(`7634b63`)에서 정확히 다음 줄들이다. `120` → `104`, `30` → `26`, `15` → `13` 으로 바꾼다:

| 행 | 현재 | 바꾼 뒤 |
|---|---|---|
| 71 | `'case_count': 120,` | `'case_count': 104,` |
| 127 | `'case_count': 30,` | `'case_count': 26,` |
| 231 | `test('approved fixture order and exact 120/30 expansions are immutable', () {` | `… exact 104/26 expansions …` |
| 252 | `expect(fixtures.length * 4 * 2, 120);` | `expect(fixtures.length * 4 * 2, 104);` |
| 253 | `expect(fixtures.length * a11y.length, 30);` | `expect(fixtures.length * a11y.length, 26);` |
| 275 | `expect(visual['case_count'], 120);` | `expect(visual['case_count'], 104);` |
| 276 | `expect(a11y['case_count'], 30);` | `expect(a11y['case_count'], 26);` |
| 318 | `expect(projectionMatrix, hasLength(15));` | `expect(projectionMatrix, hasLength(13));` |
| 472–473 | `expect(visualCases['minItems'], 120);` / `['maxItems'], 120);` | 둘 다 `104` |
| 474–475 | `expect(a11yCases['minItems'], 30);` / `['maxItems'], 30);` | 둘 다 `26` |
| 647 | `test('visual result set reconciles all 120 ordered files exactly', () {` | `… all 104 ordered files …` |

행 번호가 어긋나면(기준 커밋이 달라졌으면) `grep -nE "\b(15|120|30)\b" apps/web/test/app/et13_evidence_catalog_contract_test.dart` 로 다시 찾는다. 647행 테스트 본문이 120개짜리 목록을 직접 만든다면 그 생성 로직도 fixture 목록에서 파생되는지 확인한다.

- [ ] **Step 3: `et13_evidence_producer_contract_test.dart` 수정**

130행:

```dart
    for (final app in ['web', 'admin', 'mobile']) {
```

→

```dart
    for (final app in ['web', 'admin']) {
```

859행 부근 entrypoint 기대 맵에서 아래 줄을 지운다:

```dart
      'mobile': 'apps/mobile/lib/et13_evidence_main.dart',
```

- [ ] **Step 4: red 확인**

```bash
cd apps/web && flutter test test/app/et13_evidence_catalog_contract_test.dart test/app/et13_evidence_producer_contract_test.dart 2>&1 | tail -15
```

Expected: FAIL. 실패 메시지가 "fixture 목록/개수가 카탈로그·도구·워크플로와 다르다"는 종류여야 한다(컴파일 오류나 파일 없음이면 Step 2·3 을 다시 본다).

- [ ] **Step 5: 커밋**

```bash
git add apps/web/test/app/et13_evidence_catalog_contract_test.dart apps/web/test/app/et13_evidence_producer_contract_test.dart
git commit -m "test(et13): expect a 13-fixture catalog without the mobile distribution

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: 카탈로그·스키마·도구에서 모바일 제거, 생성 카탈로그 재계산

**Files:**
- Modify: `tools/et13_evidence.dart` — `_fixtureIds`(26–42행), `_visualSurfaceCounts`·`_a11ySurfaceCounts`(46–57행), `fixtures.length != 15`(416행), `expectedOwners`·`expectedDistributions`(477–488행), build marker 검증(1105–1112행), `writeBuildMarker`(1180–1196행), CLI `build-marker`(3643–3650행), `_projectionContractSha256`(10행)
- Modify: `evidence/et13/catalog.v1.json` — `fixtures` 2항목, `projection_matrix` 2행, `projection_contract_sha256`
- Modify: `evidence/et13/catalog.schema.json:81-82`, `evidence/et13/generated-cases.schema.json:82-83,141-142,183,203,212-227`, `evidence/et13/evidence.schema.json:162-163,175-190`, `evidence/et13/manifest.schema.json:159-160,172-187,203,233`, `evidence/et13/baseline-approval.schema.json:103-104`
- Regenerate: `evidence/et13/generated/visual-cases.v1.json`, `evidence/et13/generated/a11y-cases.v1.json`

**Interfaces:**
- Consumes: Task 1 의 실패 테스트.
- Produces: `dart run tools/et13_evidence.dart validate` 가 OK 인 13-fixture 카탈로그. **새 `projection_contract_sha256`** 과 **새 `catalog_sha256`** — S2a(gitops) 계획의 입력값이다. `build-marker` 서브커맨드는 `--mobile-root` 를 더 받지 않는다(Task 3 이 호출부를 맞춘다).

- [ ] **Step 1: `tools/et13_evidence.dart` 상수**

`_fixtureIds` 에서 두 줄 삭제:

```dart
  'mobile-today-available',
  'mobile-content-reading',
```

표면별 개수 — 바꾼 뒤:

```dart
const _visualSurfaceCounts = <String, int>{
  'web': 72,
  'admin': 16,
  'dp_design': 16,
};
const _a11ySurfaceCounts = <String, int>{
  'web': 18,
  'admin': 4,
  'dp_design': 4,
};
```

416행:

```dart
  if (fixtures.length != 15) _fail('catalog must contain exactly 15 fixtures');
```

→ 리터럴을 없애고 목록에서 파생한다:

```dart
  if (fixtures.length != _fixtureIds.length) {
    _fail('catalog must contain exactly ${_fixtureIds.length} fixtures');
  }
```

477–488행 — 바꾼 뒤:

```dart
  const expectedOwners = <String, int>{
    'web': 9,
    'admin': 2,
    'dp_design': 2,
  };
  const expectedDistributions = <String, int>{
    'web': 11,
    'admin': 2,
  };
```

- [ ] **Step 2: `tools/et13_evidence.dart` build marker**

1105–1112행 — 바꾼 뒤:

```dart
  if (distributions.length != 2) {
    _fail('build marker must bind exactly two Flutter Web distributions');
  }
  const expected = <String, String>{
    'web': 'apps/web/lib/et13_evidence_main.dart',
    'admin': 'apps/admin/lib/et13_evidence_main.dart',
  };
```

`writeBuildMarker` — `required String mobileRoot,` 파라미터, `roots` 의 `'mobile': mobileRoot,`, `entrypoints` 의 `'mobile': 'apps/mobile/lib/et13_evidence_main.dart',` 세 줄을 지운다. CLI `build-marker` 분기에서 다음 줄을 지운다:

```dart
          mobileRoot: _requiredOption(options, 'mobile-root'),
```

이어서 같은 파일에 남은 모바일 참조가 없는지 확인한다:

```bash
grep -nE "mobile" tools/et13_evidence.dart
```

Expected: 출력 없음. 남아 있으면 그 줄의 문맥을 읽고 같은 원칙(모바일 distribution·owner 제거)으로 고친다.

- [ ] **Step 3: `catalog.v1.json`**

`fixtures` 배열에서 `"id": "mobile-today-available"` 객체와 `"id": "mobile-content-reading"` 객체를 통째로 지운다. `projection_matrix` 배열에서 `"fixture_id": "mobile-today-available"` 행과 `"fixture_id": "mobile-content-reading"` 행을 지운다. `projection_contract_sha256` 은 Step 5 에서 바꾼다.

- [ ] **Step 4: 스키마 5종**

각 파일에서:
- fixture id `prefixItems` 의 두 항목 삭제 — `{"const": "mobile-today-available"},` 와 `{"const": "mobile-content-reading"},`. 그 배열의 `minItems`/`maxItems` 가 `15` 면 `13` 으로.
- `"owner": {"enum": ["web", "admin", "mobile", "dp_design"]}` → `["web", "admin", "dp_design"]`
- `"distribution": {"enum": ["web", "admin", "mobile"]}` → `["web", "admin"]`
- `surface_case_counts` 블록: `"required": ["web", "admin", "mobile", "dp_design"]` → `["web", "admin", "dp_design"]`, 그리고 `"mobile": {"const": 16},` / `"mobile": {"const": 4},` 줄 삭제.
- artifact 경로 패턴: `^visual/(?:web|admin|mobile|dp_design)/` → `^visual/(?:web|admin|dp_design)/`, `^a11y/(?:web|admin|mobile|dp_design)/` → `^a11y/(?:web|admin|dp_design)/`
- case 배열의 `minItems`/`maxItems`: `120` → `104`, `30` → `26`. 총합 `case_count` 의 `const` 가 있으면 같은 값으로.

끝나면:

```bash
grep -nE "mobile|\b(15|120|30)\b" evidence/et13/*.schema.json
```

Expected: `mobile` 0건. 숫자는 남은 각 줄을 읽어 fixture/case 수와 무관한지(예: 폭, 버전) 확인한다.

- [ ] **Step 5: 생성·해시 반영·검증**

```bash
dart run tools/et13_evidence.dart generate
```

도구가 출력하는 canonical projection sha(64자 hex)를 복사해 두 곳에 같은 값으로 넣는다: `tools/et13_evidence.dart` 의 `const _projectionContractSha256 = '…';` 와 `evidence/et13/catalog.v1.json` 의 `"projection_contract_sha256"`. 다시:

```bash
dart run tools/et13_evidence.dart generate && dart run tools/et13_evidence.dart validate
```

Expected: `ET13 generated catalogs: visual=104 a11y=26` 그리고 validate OK. 이어서 값을 기록한다(S2a 의 입력):

```bash
py -c "import json;d=json.load(open('evidence/et13/generated/visual-cases.v1.json',encoding='utf-8'));print('projection',d['projection_contract_sha256']);print('catalog',d['catalog_sha256']);print(d['case_count'],d['surface_case_counts'],len(d['fixture_ids']))"
```

Expected: `104 {'web': 72, 'admin': 16, 'dp_design': 16} 13`.

- [ ] **Step 6: green 확인**

```bash
cd apps/web && flutter test test/app/et13_evidence_catalog_contract_test.dart 2>&1 | tail -3
```

Expected: PASS. (`et13_evidence_producer_contract_test.dart` 는 워크플로를 읽으므로 Task 3 뒤에 녹색이 된다.)

- [ ] **Step 7: 커밋**

```bash
git add tools/et13_evidence.dart evidence/et13
git commit -m "feat(et13): drop the mobile distribution from the evidence catalog

13 fixtures (web 9, admin 2, dp_design 2), visual 104, a11y 26. The catalog
length check now derives from the fixture list instead of a literal.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: 캡처 도구와 워크플로에서 모바일 빌드·루트 제거

**Files:**
- Modify: `tools/et13/capture.mjs:165` (`mobile: required(parsed, 'mobile-root'),`), `:180` (`const ports = { web: 4173, admin: 4174, mobile: 4175 };`)
- Modify: `.github/workflows/et13-evidence.yml` — 트리거 경로 45·64행(`'apps/mobile/**'`), 874행(`dart run tools/mobile_source_guard.dart`), 897–898행(`apps/mobile/lib/src/evidence`·`apps/mobile/test/evidence` 포맷 대상), 907행(`(cd apps/mobile && flutter analyze --no-pub)`), 924–926행(모바일 evidence 테스트), 946–953행(`Build mobile evidence distribution` 스텝 전체), 973·1086행(`--mobile-root=…`)
- Test: `tools/et13/*.test.mjs`, `apps/web/test/app/et13_evidence_producer_contract_test.dart`

**Interfaces:**
- Consumes: Task 2 의 `build-marker`(이제 `--web-root`·`--admin-root` 만 받는다).
- Produces: 모바일을 빌드·서빙하지 않는 ET13 파이프라인.

- [ ] **Step 1: `capture.mjs`**

165행 줄 삭제. 180행:

```js
  const ports = { web: 4173, admin: 4174, mobile: 4175 };
```

→

```js
  const ports = { web: 4173, admin: 4174 };
```

```bash
grep -nE "mobile" tools/et13/*.mjs
```

Expected: 출력 없음(테스트 파일 포함). 테스트 파일에 남아 있으면 같은 방식으로 `mobile` 루트·포트를 뺀다.

- [ ] **Step 2: `et13-evidence.yml`**

위 **Files** 에 적은 줄을 지운다. `Build mobile evidence distribution` 은 `- name:` 부터 다음 `- name:` 직전까지 스텝 전체를 지운다. 두 `build-marker`/capture 호출에서 `--mobile-root="${ET13_ROOT}/build/mobile"` 인자 줄을 지우되, 그 줄이 백슬래시 연속의 **마지막 줄**이었다면 바로 윗줄 끝의 `\` 도 지운다(안 그러면 셸이 다음 명령을 인자로 삼킨다).

```bash
grep -nE "mobile" .github/workflows/et13-evidence.yml
```

Expected: 출력 없음.

- [ ] **Step 3: 테스트**

```bash
node --test tools/et13/ 2>&1 | grep -E "^ℹ (pass|fail)"
cd apps/web && flutter test test/app/et13_evidence_producer_contract_test.dart test/app/et13_baseline_approval_workflow_contract_test.dart 2>&1 | tail -3
```

Expected: node `fail 0`, Flutter `All tests passed!`. producer 계약 테스트가 워크플로의 특정 문자열(예: 세 distribution 빌드 스텝 이름)을 단언해 실패하면, 실패 메시지가 가리키는 단언을 두-distribution 계약으로 바꾼다 — 단언을 지우지 말고 새 기대값으로 **바꾼다.**

- [ ] **Step 4: 커밋**

```bash
git add tools/et13 .github/workflows/et13-evidence.yml apps/web/test/app/et13_evidence_producer_contract_test.dart
git commit -m "ci(et13): stop building and serving the mobile evidence distribution

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: 리터럴 전수 검사와 전체 게이트

**Files:**
- Modify(발견 시에만): 검사에서 나온 파일
- Modify: `docs/design/et13-community-fixtures.md` (카탈로그 크기 서술)

**Interfaces:**
- Produces: "옛 개수 리터럴이 레포 어디에도 남지 않았다"는 확인.

- [ ] **Step 1: 옛 값 전수 grep**

```bash
git grep -nE "mobile-today-available|mobile-content-reading|MobileTodayProjection|MobileContentProjection" -- . ':!apps/mobile' ':!docs/superpowers'
git grep -nE "\b(visual=120|a11y=30|case_count\D{0,4}(120|30)|exactly 15 fixtures|three Flutter Web distributions)\b" -- . ':!docs/superpowers'
git grep -nE "et13|ET13" -- .github/workflows | grep -nE "\b(15|120|30|150|204)\b"
```

Expected: 세 명령 모두 출력 없음. 출력이 있으면 그 줄이 (a) 이번에 바꿔야 할 계약인지 (b) 지난 기록(문서의 이력 서술)인지 판단한다. (a) 는 고치고, (b) 는 둔다.

`et13-baseline-approval.yml` 은 2026-09-19 PR #222 로 개수를 case catalog 에서 파생하므로 바꿀 것이 없다 — 위 grep 이 그것을 확인한다.

- [ ] **Step 2: 문서 한 곳 갱신**

`docs/design/et13-community-fixtures.md` 에서 카탈로그 크기를 말하는 문장(15 fixture · visual 120 · a11y 30 · browser smoke 22)에 다음 한 줄을 덧붙인다:

```markdown
> 2026-09-19: 모바일 앱이 `DevPathAi/devpath-mobile` 로 분리되면서 `mobile` distribution 과 fixture 2종을 제거했다 — 13 fixture · visual 104 · a11y 26. browser smoke 는 웹 호스팅 fixture 11개라 22 그대로다.
```

- [ ] **Step 3: 전체 게이트**

```bash
cd /d/workspace/dpa/.worktrees/frontend-et13-drop-mobile
dart run melos run format
dart run melos run analyze
dart run melos run test
dart run tools/et13_evidence.dart validate
node --test tools/ 2>&1 | grep -E "^ℹ (pass|fail)"
```

Expected: format `0 changed`(한 번 고치고 exit 1 이면 다시 돌려 0 을 확인) · analyze 무결점 · test 전부 통과(Global Constraints 의 CRLF 1건 제외 — `dp_code_font_test.dart` 의 "lazy asset" 하나뿐이어야 한다) · validate OK · node `fail 0`.

`apps/mobile` 의 ET13 테스트(`test/evidence/et13_mobile_evidence_app_test.dart`, `test/features/evidence/mobile_evidence_projection_test.dart`)는 앱 내부 위젯만 검사하므로 그대로 통과해야 한다. 실패하면 멈추고 원인을 읽는다.

- [ ] **Step 4: 커밋**

```bash
git add -A
git commit -m "docs(et13): record the 13-fixture catalog after the mobile split

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: PR · CI · 머지 · 산출값 기록

**Interfaces:**
- Produces: develop 머지 커밋, 그리고 S2a 가 gitops 에 미러할 값 — fixture id 13개 목록 · `projection_contract_sha256` · `catalog_sha256` · 표면별 개수.

- [ ] **Step 1: push 와 PR**

```bash
git push -u origin chore/et13-drop-mobile-distribution
cd /d/workspace/dpa && gh pr create -R DevPathAi/devpath-frontend --base develop --head chore/et13-drop-mobile-distribution \
  --title "feat(et13): drop the mobile distribution from the evidence contract" \
  --body "Removes the two mobile fixtures and the \`mobile\` distribution from the ET13 evidence contract now that the native app lives in DevPathAi/devpath-mobile. 13 fixtures, visual 104, a11y 26. \`apps/mobile\` itself is untouched; it is removed in a later PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

- [ ] **Step 2: CI 판정**

```bash
timeout 570 gh pr checks <PR번호> -R DevPathAi/devpath-frontend --watch --interval 30
```

Expected: analyze-test · browser-ux · perf-gate(약 23분) · web-image-config-contract(off/on) · **produce-atomic-pair** · contract-test-android · ios-no-codesign 전부 pass. `produce-atomic-pair` 가 핵심이다 — 모바일 없이 build marker·캡처·원시 아티팩트가 만들어지는지 본다. 실패하면 `gh run view <id> --log-failed` 로 메시지를 읽는다. N06 때 이 잡에서만 드러난 결함이 둘 있었다(`capture.mjs` 의 웹 fixture 수 하드코딩, 캡처 요약 총합 하드코딩) — 개수 불일치 메시지가 나오면 그 계열을 먼저 의심한다.

- [ ] **Step 3: 원시 아티팩트 파일 수 실측**

```bash
RUN=$(gh run list -R DevPathAi/devpath-frontend --workflow et13-evidence.yml --branch chore/et13-drop-mobile-distribution --limit 1 --json databaseId -q '.[0].databaseId')
gh api repos/DevPathAi/devpath-frontend/actions/runs/$RUN/artifacts -q '.artifacts[] | "\(.name) \(.size_in_bytes)"'
```

원시 리뷰 아티팩트를 내려받아 파일 수가 184 인지 확인한다(`gh run download $RUN -n <이름> -D <스크래치>` 후 `find … -type f | wc -l`).

- [ ] **Step 4: 머지와 정리**

```bash
gh pr merge <PR번호> -R DevPathAi/devpath-frontend --merge
cd /d/workspace/dpa && git -C /d/workspace/dpa/devpath-frontend worktree remove /d/workspace/dpa/.worktrees/frontend-et13-drop-mobile
```

(worktree 제거는 셸 cwd 가 그 안에 있으면 Permission denied 다 — 반드시 밖에서 실행한다.)

- [ ] **Step 5: 산출값을 스펙에 기록**

documents `develop` 에서 브랜치를 만들어 스펙 §6.5 끝에 표를 추가한다: fixture id 13개(순서대로) · `projection_contract_sha256` · `catalog_sha256` · visual/a11y `surface_case_counts` · frontend develop 머지 커밋. 값은 Task 2 Step 5 의 출력과 머지된 파일에서 복사한다. PR → CI → 머지.

---

## 범위 밖 (의도적)

- 릴리스 증거에서 서명 모바일·TalkBack 제거(`tools/mission_spine_manual_at_evidence.mjs`, `mission-spine-manual-at-evidence.yml`, `mission-spine-signed-mobile-build.yml`, `tool/release-evidence/catalogs/manual-talkback.v1.json`) → **S2c-2.** 증거 JSON 의 `signed_apk_sha256` 같은 필드를 gitops `verify_release_artifacts.py` 가 검증하므로 gitops S2a 와 쌍으로 설계한다.
- `apps/mobile`·`mobile.yml`·`tools/mobile_source_guard.dart`·루트 workspace 항목 삭제 → **S2c-3.**
- gitops 미러 갱신 → **S2a**(이 계획의 Task 5 산출값이 입력).
