# S2c-2 — frontend 릴리스 증거에서 서명 모바일·TalkBack 제거 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** frontend 의 수동 접근성 증거 파이프라인에서 서명 APK 인증과 TalkBack 레인을 제거해 `manual-nvda` 단독으로 만든다. NVDA 증거 JSON 의 모양은 바꾸지 않는다.

**Architecture:** 증거 도구(`mission_spine_manual_at_evidence.mjs`)의 레인 정의가 단일 진실이다 — 카탈로그 검증·candidate 검증·패키지 검증이 모두 `laneDefinitions` 를 순회한다. 레인을 하나로 줄이고 candidate 의 `quality_evidence_inputs` 를 exact-key 로 잠그면 구 모양 candidate 는 fail-closed 로 거부된다. 워크플로는 도구의 CLI 를 그대로 호출하므로 도구 → 워크플로 → 계약 테스트 순으로 바꾼다.

**Tech Stack:** Node.js 20+(`node:test`) · GitHub Actions YAML · Dart/Flutter test(워크플로 계약 테스트) · melos 7

**Spec:** `docs/superpowers/specs/2026-09-19-s2c2-s2a-drop-signed-mobile-and-gitops-mirror-design.md` §3 (documents 레포)

## Global Constraints

- 작업 레포: `DevPathAi/devpath-frontend`. **주 checkout(`D:/workspace/dpa/devpath-frontend`, 브랜치 `feat/evidence-auth-smoke`)은 건드리지 않는다.** 전용 worktree `D:/workspace/dpa/.worktrees/frontend-s2c2` 에서만 작업한다.
- 브랜치: `origin/develop` 에서 `chore/s2c2-drop-signed-mobile-talkback` 분기 → `develop` 으로 PR. `main`·`develop` 직접 push 금지. 머지는 merge commit.
- 모든 git·파일 명령은 절대경로 또는 `git -C <절대경로>` 를 쓴다. `cd` 뒤 상대경로로 후속 명령을 내지 않는다(에이전트 스레드는 bash 호출 사이 cwd 가 리셋된다).
- NVDA 증거 JSON 의 키 집합·순서는 **바꾸지 않는다**: `candidate_spec_sha256, status, producer_run_id, producer_run_attempt, repository, source_sha, case_catalog_sha256, case_count, passed_case_count, failed_case_count, assistive_technology, test_provenance_sha256, approval_environment, approval_environment_id, approval_job_name, approved_by, approved_by_id, approval_effective_at`.
- 바꾸지 않는 식별자: 환경 `mission-spine-manual-at-auth`·`manual-at-nvda` · 승인 잡 이름 `Authenticate manual AT inputs`·`Approve manual NVDA evidence` · 아티팩트 이름 `<release_id>-manual-nvda-run-<run_id>-attempt-<n>`·`<release_id>-unsealable-manual-at-review-run-…`·`<release_id>-unsealable-manual-nvda-approval-run-…`.
- **GitHub 환경 `manual-at-talkback`·`mission-spine-mobile-signing-android` 는 삭제하지 않는다**(환경 시크릿은 재조회 불가).
- ET13 카탈로그(`evidence/et13/**`)·`apps/mobile` 본체·`mobile.yml` 은 건드리지 않는다. 예외: `apps/mobile/test/architecture/` 의 워크플로 계약 테스트 2개(Task 2·Task 4).
- `node --test <디렉터리>` 는 이 PC 에서 모듈 해석 오류가 난다 → 테스트 파일을 직접 지정한다.
- Git Bash 에서 `git show origin/x:path` 를 쓸 때는 `export MSYS_NO_PATHCONV=1`.
- 로컬 검증은 node 테스트·Dart 계약 테스트·analyze 까지. 웹 빌드·Playwright·perf-gate 는 CI 에 맡긴다(perf-gate 약 23분).
- 스펙 대비 추가 1건: 증거 도구 두 개의 node 테스트를 실행하는 CI 가 없다(실측: `ci.yml` 은 `immutable_registry`·`browser_ux`·`perf` 만 실행). Task 5 에서 `ci.yml` 에 한 단계를 추가한다.

## File Structure

| 파일 | 조치 | 책임 |
|---|---|---|
| `tools/mission_spine_manual_at_evidence.mjs` | 수정 | 수동 AT 카탈로그·candidate·증거·패키지 검증과 증거 생성 CLI. 레인은 `manual-nvda` 하나 |
| `tools/mission_spine_manual_at_evidence.test.mjs` | 전체 교체 | 위 도구의 단위 테스트 + 구 모양 거부 음성 테스트 |
| `tools/mission_spine_release_evidence.mjs` · `.test.mjs` | 삭제 | 서명 모바일 provenance 전용 |
| `tools/mission_spine_protected_approval.mjs` | 수정 | 보호 승인 허용 목록에서 서명·TalkBack 바인딩 제거 |
| `tools/mission_spine_protected_approval.test.mjs` | 수정 | 기본 픽스처를 `manual-at-nvda` 바인딩으로 재기준 + 음성 테스트 |
| `.github/workflows/mission-spine-manual-at-evidence.yml` | 수정 | candidate 인증 → NVDA 승인 → NVDA 증거 게시 |
| `.github/workflows/mission-spine-signed-mobile-build.yml` | 삭제 | 서명 Android 빌드 |
| `tool/release-evidence/catalogs/manual-talkback.v1.json` · `provenance/manual-talkback.v1.json` | 삭제 | TalkBack 카탈로그 |
| `apps/mobile/test/architecture/mission_spine_signed_mobile_workflow_contract_test.dart` | 삭제 | 삭제되는 워크플로의 계약 테스트 |
| `apps/mobile/test/architecture/mission_spine_manual_at_workflow_contract_test.dart` | `apps/web/test/app/` 로 이전·수정 | 수동 AT 워크플로 계약 테스트 |
| `.github/workflows/ci.yml` | 수정 | 증거 도구 node 테스트 실행 단계 추가 |

---

### Task 0: 작업 worktree 와 기준선

**Files:** 없음(환경 준비)

**Interfaces:**
- Produces: worktree `D:/workspace/dpa/.worktrees/frontend-s2c2`(브랜치 `chore/s2c2-drop-signed-mobile-talkback`), 이하 `$WT`.

- [ ] **Step 1: worktree 생성**

```bash
git -C D:/workspace/dpa/devpath-frontend fetch origin
git -C D:/workspace/dpa/devpath-frontend worktree add -b chore/s2c2-drop-signed-mobile-talkback \
  D:/workspace/dpa/.worktrees/frontend-s2c2 origin/develop
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 log -1 --format='%h %s'
```

Expected: 마지막 줄이 `db955ea Merge pull request #223 …` 또는 그보다 뒤의 develop 커밋. `db955ea` 보다 뒤라면 `git -C $WT diff db955ea HEAD --stat -- tools .github/workflows/mission-spine-manual-at-evidence.yml tool/release-evidence` 가 비어 있는지 확인한다. 비어 있지 않으면 멈추고 `NEEDS_CONTEXT` 로 보고한다(이 계획의 줄 번호·코드는 `db955ea` 기준이다).

- [ ] **Step 2: 변경 전 기준선 — 기존 테스트가 통과함을 확인**

```bash
node --test D:/workspace/dpa/.worktrees/frontend-s2c2/tools/mission_spine_manual_at_evidence.test.mjs \
            D:/workspace/dpa/.worktrees/frontend-s2c2/tools/mission_spine_protected_approval.test.mjs \
            D:/workspace/dpa/.worktrees/frontend-s2c2/tools/mission_spine_release_evidence.test.mjs
```

Expected: `# fail 0`. 실패가 있으면 멈추고 보고한다(이 계획의 변경과 무관한 기존 결함).

---

### Task 1: 증거 도구를 `manual-nvda` 단독으로

**Files:**
- Modify: `tools/mission_spine_manual_at_evidence.mjs`
- Test: `tools/mission_spine_manual_at_evidence.test.mjs` (전체 교체)

**Interfaces:**
- Produces (export, 시그니처):
  - `validateAllManualCatalogs(repositoryRoot: string) → { 'manual-nvda': { catalog_path, catalog_sha256, case_count, case_ids, provenance_path, provenance_sha256 } }`
  - `createManualEvidence({ lane, candidate, candidateSpecSha256, releaseId, sourceSha, producerRunId, producerRunAttempt, approval, repositoryRoot }) → evidence object`
  - `validateManualEvidencePackages({ packageRoot, candidate, candidateSpecSha256, releaseId, sourceSha, producerRunId, producerRunAttempt, repositoryRoot }) → true`
  - `validateManualInputs({ repositoryRoot, candidate, candidateSpecSha256, releaseId, sourceSha }) → { catalogs, candidateSpecSha256 }` — **`signedBundleRoot` 인자 제거**
  - 제거되는 export: `validateSignedMobileArtifactFacts`
- CLI 명령: `validate-manual-inputs`(옵션 `--signed-root` 없음) · `manual-evidence` · `validate-manual-packages`. 제거: `authenticate-signed-artifact`.

- [ ] **Step 1: 실패하는 테스트 작성 — 테스트 파일을 아래 내용으로 전체 교체**

`tools/mission_spine_manual_at_evidence.test.mjs`:

```js
import assert from 'node:assert/strict';
import {
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import test from 'node:test';

import {
  createManualEvidence,
  validateAllManualCatalogs,
  validateManualEvidencePackages,
  validateManualInputs,
} from './mission_spine_manual_at_evidence.mjs';

const root = resolve(import.meta.dirname, '..');
const sourceSha = '1234567890abcdef1234567890abcdef12345678';
const candidateSha256 = '1'.repeat(64);
const releaseId = 'release-2026-08-17';

const expectedCases = {
  'manual-nvda': [
    'nvda-web-today-mission-spine',
    'nvda-web-next-action-navigation',
  ],
};

const evidenceKeyOrder = [
  'candidate_spec_sha256',
  'status',
  'producer_run_id',
  'producer_run_attempt',
  'repository',
  'source_sha',
  'case_catalog_sha256',
  'case_count',
  'passed_case_count',
  'failed_case_count',
  'assistive_technology',
  'test_provenance_sha256',
  'approval_environment',
  'approval_environment_id',
  'approval_job_name',
  'approved_by',
  'approved_by_id',
  'approval_effective_at',
];

const legacySignedBinding = {
  schema_version: 'leva.mission-spine.signed-android-build-binding.v2',
  repository: 'DevPathAi/devpath-frontend',
  source_sha: sourceSha,
  event: 'workflow_dispatch',
  workflow_path: '.github/workflows/mission-spine-signed-mobile-build.yml',
  workflow_sha256: '3'.repeat(64),
  workflow_run_id: 701,
  run_attempt: 1,
  artifact_id: 801,
  artifact_name: 'release-2026-08-17-signed-android-build-run-701-attempt-1',
  artifact_archive_sha256: '4'.repeat(64),
  build_provenance_file: 'build-provenance.v2.json',
  build_provenance_sha256: '5'.repeat(64),
  signed_apk_file: 'mobile/android/leva-release.apk',
  signed_apk_sha256: '6'.repeat(64),
};

function approval() {
  return {
    approval_environment: 'manual-at-nvda',
    approval_environment_id: 100,
    approval_job_name: 'Approve manual NVDA evidence',
    approved_by: 'independent-reviewer',
    approved_by_id: 501,
    approval_effective_at: '2025-08-17T01:02:03Z',
    workflow_sha256: '2'.repeat(64),
  };
}

function candidateFromCatalogs(catalogs) {
  const bindings = {
    'frontend-visual': {},
    'home-visual': {},
    'frontend-automated-a11y': {},
    'home-axe-browser-a11y': {},
  };
  for (const [lane, value] of Object.entries(catalogs)) {
    bindings[lane] = {
      repository: 'DevPathAi/devpath-frontend',
      source_sha: sourceSha,
      path: value.catalog_path,
      sha256: value.catalog_sha256,
      case_count: value.case_count,
      provenance_sha256: value.provenance_sha256,
    };
  }
  return {
    $schema: 'https://example.invalid/candidate.schema.json',
    schema_version: 'mission-spine.candidate-spec.v1',
    document_type: 'candidate-spec',
    release_id: releaseId,
    created_at: '2025-08-17T00:00:00Z',
    gitops: {},
    services: {},
    shared_migration: {},
    frontend: {
      repository: 'DevPathAi/devpath-frontend',
      source_sha: sourceSha,
    },
    home: {},
    analytics_privacy: {},
    ai_release_eval_config: {},
    environments: {},
    journey_harness: {},
    quality_evidence_inputs: {
      catalogs: bindings,
      frontend_projection_contract: {},
    },
    rollout: {},
  };
}

function evidenceArguments(candidate, overrides = {}) {
  return {
    lane: 'manual-nvda',
    candidate,
    candidateSpecSha256: candidateSha256,
    releaseId,
    sourceSha,
    producerRunId: 901,
    producerRunAttempt: 1,
    approval: approval(),
    repositoryRoot: root,
    ...overrides,
  };
}

test('manual catalogs and static provenance have exact reviewed order and bytes', () => {
  const catalogs = validateAllManualCatalogs(root);
  assert.deepEqual(Object.keys(catalogs), ['manual-nvda']);
  for (const [lane, expected] of Object.entries(expectedCases)) {
    assert.deepEqual(catalogs[lane].case_ids, expected);
    assert.equal(catalogs[lane].case_count, expected.length);
    assert.match(catalogs[lane].catalog_sha256, /^[0-9a-f]{64}$/);
    assert.match(catalogs[lane].provenance_sha256, /^[0-9a-f]{64}$/);
  }
});

test('manual NVDA evidence keeps its exact key order and approval identity', () => {
  const candidate = candidateFromCatalogs(validateAllManualCatalogs(root));
  const evidence = createManualEvidence(evidenceArguments(candidate));
  assert.equal(evidence.status, 'passed');
  assert.equal(evidence.case_count, 2);
  assert.equal(evidence.passed_case_count, 2);
  assert.equal(evidence.failed_case_count, 0);
  assert.equal(evidence.assistive_technology, 'NVDA+Chromium');
  assert.equal(evidence.approval_environment, 'manual-at-nvda');
  assert.deepEqual(Object.keys(evidence), evidenceKeyOrder);
});

test('manual evidence rejects attempt reuse, catalog drift, and unsafe review data', () => {
  const candidate = candidateFromCatalogs(validateAllManualCatalogs(root));
  assert.throws(
    () => createManualEvidence(evidenceArguments(candidate, { producerRunAttempt: 2 })),
    /attempt 1/,
  );

  const drift = structuredClone(candidate);
  drift.quality_evidence_inputs.catalogs['manual-nvda'].case_count = 3;
  assert.throws(
    () => createManualEvidence(evidenceArguments(drift)),
    /case_count/,
  );

  const unsafe = approval();
  unsafe.approved_by = 'data:text/plain,reviewer';
  assert.throws(
    () => createManualEvidence(evidenceArguments(candidate, { approval: unsafe })),
    /approved_by/,
  );

  const legacyVoiceOver = structuredClone(candidate);
  legacyVoiceOver.quality_evidence_inputs.catalogs['manual-voiceover'] = {
    repository: 'DevPathAi/devpath-frontend',
  };
  assert.throws(
    () => createManualEvidence(evidenceArguments(legacyVoiceOver)),
    /candidate catalog bindings/,
  );
});

test('legacy signed-mobile and TalkBack candidate shapes fail closed', () => {
  const candidate = candidateFromCatalogs(validateAllManualCatalogs(root));

  const legacySigned = structuredClone(candidate);
  legacySigned.quality_evidence_inputs.mobile_test_artifacts = legacySignedBinding;
  assert.throws(
    () => createManualEvidence(evidenceArguments(legacySigned)),
    /candidate\.quality_evidence_inputs exact ordered key set mismatch/,
  );

  const legacyTalkBack = structuredClone(candidate);
  legacyTalkBack.quality_evidence_inputs.catalogs['manual-talkback'] = {
    repository: 'DevPathAi/devpath-frontend',
    source_sha: sourceSha,
    path: 'tool/release-evidence/catalogs/manual-talkback.v1.json',
    sha256: '7'.repeat(64),
    case_count: 4,
    provenance_sha256: '8'.repeat(64),
  };
  assert.throws(
    () => createManualEvidence(evidenceArguments(legacyTalkBack)),
    /candidate catalog bindings/,
  );

  assert.throws(
    () => createManualEvidence(evidenceArguments(candidate, { lane: 'manual-talkback' })),
    /unknown manual lane/,
  );
});

test('manual inputs validate without any signed bundle', () => {
  const catalogs = validateAllManualCatalogs(root);
  const candidate = candidateFromCatalogs(catalogs);
  const result = validateManualInputs({
    repositoryRoot: root,
    candidate,
    candidateSpecSha256: candidateSha256,
    releaseId,
    sourceSha,
  });
  assert.deepEqual(Object.keys(result), ['catalogs', 'candidateSpecSha256']);
  assert.deepEqual(Object.keys(result.catalogs), ['manual-nvda']);
  assert.equal(result.candidateSpecSha256, candidateSha256);
});

test('the single manual package is exact and rejects extras', () => {
  const candidate = candidateFromCatalogs(validateAllManualCatalogs(root));
  const packageRoot = mkdtempSync(join(tmpdir(), 'manual-at-packages-'));
  const packageArguments = {
    packageRoot,
    candidate,
    candidateSpecSha256: candidateSha256,
    releaseId,
    sourceSha,
    producerRunId: 901,
    producerRunAttempt: 1,
    repositoryRoot: root,
  };
  try {
    mkdirSync(join(packageRoot, 'manual-nvda'));
    writeFileSync(
      join(packageRoot, 'manual-nvda', 'evidence.json'),
      `${JSON.stringify(createManualEvidence(evidenceArguments(candidate)), null, 2)}\n`,
    );
    assert.doesNotThrow(() => validateManualEvidencePackages(packageArguments));

    mkdirSync(join(packageRoot, 'manual-talkback'));
    assert.throws(
      () => validateManualEvidencePackages(packageArguments),
      /exactly the manual lane directories/,
    );
    rmSync(join(packageRoot, 'manual-talkback'), { recursive: true });

    writeFileSync(join(packageRoot, 'manual-nvda', 'raw-notes.txt'), 'forbidden');
    assert.throws(
      () => validateManualEvidencePackages(packageArguments),
      /exactly evidence.json/,
    );
  } finally {
    rmSync(packageRoot, { recursive: true, force: true });
  }
});

test('the tool source carries no signed-mobile or TalkBack residue', () => {
  const source = readFileSync(
    new URL('./mission_spine_manual_at_evidence.mjs', import.meta.url),
    'utf8',
  );
  assert.doesNotMatch(source, /talkback|signed|mobile_test_artifacts|\.apk/i);
  assert.doesNotMatch(source, /mission_spine_release_evidence/);
});
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인**

Run: `node --test D:/workspace/dpa/.worktrees/frontend-s2c2/tools/mission_spine_manual_at_evidence.test.mjs`

Expected: FAIL. 최소한 첫 테스트가 `Object.keys(catalogs)` 에 `'manual-talkback'` 이 있어 `deepEqual` 에서 실패하고, 마지막 테스트가 `talkback|signed` 매치로 실패한다.

- [ ] **Step 3: 도구 수정 — import 와 상수**

`tools/mission_spine_manual_at_evidence.mjs` 13–26행을 다음으로 바꾼다(서명 모바일 모듈 import 와 `signedBindingSchema` 제거, `frontendRepository` 를 이 파일이 소유).

```js
const frontendRepository = 'DevPathAi/devpath-frontend';

export const manualWorkflow =
  '.github/workflows/mission-spine-manual-at-evidence.yml';

const catalogSchema = 'leva.mission-spine.manual-at-catalog.v1';
const provenanceSchema =
  'leva.mission-spine.manual-at-test-provenance.v1';
```

`node:fs` import 목록(2–8행)은 그대로 둔다 — `lstatSync, readFileSync, readdirSync, realpathSync, writeFileSync` 모두 남는 코드가 쓴다.

- [ ] **Step 4: 도구 수정 — 레인 정의에서 `manual-talkback` 제거**

`laneDefinitions` 를 다음으로 바꾼다.

```js
const laneDefinitions = Object.freeze({
  'manual-nvda': Object.freeze({
    artifactLane: 'nvda',
    assistiveTechnology: 'NVDA+Chromium',
    surface: 'web',
    environment: 'manual-at-nvda',
    jobName: 'Approve manual NVDA evidence',
    requiredPlatform: 'windows_physical_host',
    requiredClient: 'chromium',
    requiredArtifact: 'exact_source_web_release_build',
    cases: Object.freeze([
      Object.freeze({ id: 'nvda-web-today-mission-spine', entry: 'today' }),
      Object.freeze({
        id: 'nvda-web-next-action-navigation',
        entry: 'next_action',
      }),
    ]),
  }),
});
```

- [ ] **Step 5: 도구 수정 — candidate 검증**

`const signedBindingKeys = [ … ];` 블록 전체를 삭제하고, 그 자리에 다음 상수를 둔다.

```js
const qualityInputKeys = ['catalogs', 'frontend_projection_contract'];
```

`validateCandidate` 함수 전체를 다음으로 바꾼다.

```js
function validateCandidate(candidate, {
  catalogs,
  releaseId,
  sourceSha,
}) {
  exactKeys(candidate, candidateTopKeys, 'canonical candidate');
  if (!releaseIdPattern.test(releaseId)) fail('release_id is not a safe identifier');
  exact(candidate.release_id, releaseId, 'candidate.release_id');
  const frontend = object(candidate.frontend, 'candidate.frontend');
  exact(frontend.repository, frontendRepository, 'candidate.frontend.repository');
  exact(sha1(frontend.source_sha, 'candidate.frontend.source_sha'), sourceSha, 'candidate.frontend.source_sha');
  const quality = object(candidate.quality_evidence_inputs, 'candidate.quality_evidence_inputs');
  exactKeys(quality, qualityInputKeys, 'candidate.quality_evidence_inputs');
  const bindings = object(quality.catalogs, 'candidate catalog bindings');
  exactKeys(bindings, candidateCatalogKeys, 'candidate catalog bindings');
  for (const [lane, local] of Object.entries(catalogs)) {
    const binding = object(bindings[lane], `${lane} candidate binding`);
    exactKeys(binding, manualBindingKeys, `${lane} candidate binding`);
    exact(binding.repository, frontendRepository, `${lane}.repository`);
    exact(binding.source_sha, sourceSha, `${lane}.source_sha`);
    exact(binding.path, local.catalog_path, `${lane}.path`);
    exact(sha256(binding.sha256, `${lane}.sha256`), local.catalog_sha256, `${lane}.sha256`);
    exact(binding.case_count, local.case_count, `${lane}.case_count`);
    exact(
      sha256(binding.provenance_sha256, `${lane}.provenance_sha256`),
      local.provenance_sha256,
      `${lane}.provenance_sha256`,
    );
  }
}
```

- [ ] **Step 6: 도구 수정 — 증거 키·생성·검증**

`const commonEvidenceKeys = [` 의 이름을 `const evidenceKeys = [` 로 바꾸고(배열 내용은 그대로), `function evidenceKeys(lane) { … }` 함수 전체를 삭제한다.

`createManualEvidence` 에서 다음 세 곳을 고친다.

```js
  const catalogs = validateAllManualCatalogs(repositoryRoot);
  validateCandidate(candidate, { catalogs, releaseId, sourceSha });
```

`if (lane !== 'manual-nvda') { evidence.build_provenance_sha256 = …; evidence.signed_apk_sha256 = …; }` 블록을 삭제한다.

```js
  validateEvidence(evidence, lane, {
    candidateSpecSha256,
    sourceSha,
    producerRunId,
    producerRunAttempt,
    catalogs,
  });
  return evidence;
```

`validateEvidence` 에서 `exactKeys(value, evidenceKeys(lane), …)` 를 `exactKeys(value, evidenceKeys, `${lane} evidence`);` 로 바꾸고, 함수 끝의 `if (lane !== 'manual-nvda') { … }` 블록을 삭제한다.

- [ ] **Step 7: 도구 수정 — 패키지·입력 검증**

`validateManualEvidencePackages` 에서 오류 메시지와 `mobile` 을 고친다.

```js
    fail('manual package root must contain exactly the manual lane directories');
  }
  const catalogs = validateAllManualCatalogs(repositoryRoot);
  validateCandidate(candidate, { catalogs, releaseId, sourceSha });
  for (const lane of lanes) {
    const evidenceFile = parseJsonFile(
      exactPackageDirectory(packageRoot, lane),
      `${lane} evidence`,
    );
    validateEvidence(evidenceFile.value, lane, {
      candidateSpecSha256,
      sourceSha,
      producerRunId,
      producerRunAttempt,
      catalogs,
    });
  }
  return true;
```

`validateManualInputs` 함수 전체를 다음으로 바꾼다.

```js
export function validateManualInputs({
  repositoryRoot,
  candidate,
  candidateSpecSha256,
  releaseId,
  sourceSha,
}) {
  const catalogs = validateAllManualCatalogs(repositoryRoot);
  validateCandidate(candidate, { catalogs, releaseId, sourceSha });
  return {
    catalogs,
    candidateSpecSha256: sha256(candidateSpecSha256, 'candidateSpecSha256'),
  };
}
```

`validateRunPath` · `validateSignedMobileArtifactFacts` · `github` · `authenticateSignedArtifact` 네 함수를 전부 삭제한다.

- [ ] **Step 8: 도구 수정 — CLI**

`cli()` 에서 `authenticate-signed-artifact` 분기를 삭제하고, `validate-manual-inputs` 분기와 마지막 `fail` 을 다음으로 바꾼다.

```js
  if (command === 'validate-manual-inputs') {
    validateManualInputs(common);
    process.stdout.write('Manual AT source inputs valid\n');
    return;
  }
```

```js
  fail('command must be validate-manual-inputs, manual-evidence, or validate-manual-packages');
```

- [ ] **Step 9: 테스트를 돌려 통과를 확인**

Run: `node --test D:/workspace/dpa/.worktrees/frontend-s2c2/tools/mission_spine_manual_at_evidence.test.mjs`

Expected: `# pass 7` · `# fail 0`.

Run: `node --check D:/workspace/dpa/.worktrees/frontend-s2c2/tools/mission_spine_manual_at_evidence.mjs`

Expected: 출력 없음(exit 0).

- [ ] **Step 10: 커밋**

```bash
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 add tools/mission_spine_manual_at_evidence.mjs tools/mission_spine_manual_at_evidence.test.mjs
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 commit -m "refactor(evidence): make manual AT evidence NVDA-only and lock candidate quality inputs"
```

---

### Task 2: 서명 모바일·TalkBack 전용 파일 삭제

**Files:**
- Delete: `tools/mission_spine_release_evidence.mjs`
- Delete: `tools/mission_spine_release_evidence.test.mjs`
- Delete: `.github/workflows/mission-spine-signed-mobile-build.yml`
- Delete: `tool/release-evidence/catalogs/manual-talkback.v1.json`
- Delete: `tool/release-evidence/provenance/manual-talkback.v1.json`
- Delete: `apps/mobile/test/architecture/mission_spine_signed_mobile_workflow_contract_test.dart`

**Interfaces:**
- Consumes: Task 1 이 `mission_spine_release_evidence.mjs` import 를 제거했어야 한다.

- [ ] **Step 1: 삭제 전 — 남은 참조가 없음을 확인**

```bash
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 grep -nE "mission_spine_release_evidence|mission-spine-signed-mobile-build|manual-talkback\.v1" -- . \
  ':!tools/mission_spine_release_evidence.mjs' ':!tools/mission_spine_release_evidence.test.mjs' \
  ':!.github/workflows/mission-spine-signed-mobile-build.yml' \
  ':!apps/mobile/test/architecture/mission_spine_signed_mobile_workflow_contract_test.dart' \
  ':!docs'
```

Expected: `tools/mission_spine_protected_approval.mjs`(32행)와 `tools/mission_spine_protected_approval.test.mjs`(31·41행), `.github/workflows/mission-spine-manual-at-evidence.yml` 의 서명 단계만 나온다 — 각각 Task 3·Task 4 가 처리한다. 그 밖의 파일이 나오면 멈추고 `NEEDS_CONTEXT` 로 보고한다.

- [ ] **Step 2: 삭제**

```bash
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 rm -q \
  tools/mission_spine_release_evidence.mjs \
  tools/mission_spine_release_evidence.test.mjs \
  .github/workflows/mission-spine-signed-mobile-build.yml \
  tool/release-evidence/catalogs/manual-talkback.v1.json \
  tool/release-evidence/provenance/manual-talkback.v1.json \
  apps/mobile/test/architecture/mission_spine_signed_mobile_workflow_contract_test.dart
```

- [ ] **Step 3: Task 1 의 테스트가 여전히 통과함을 확인**

Run: `node --test D:/workspace/dpa/.worktrees/frontend-s2c2/tools/mission_spine_manual_at_evidence.test.mjs`

Expected: `# fail 0` (카탈로그 디렉터리에 `manual-nvda.v1.json` 만 남아도 통과).

- [ ] **Step 4: 커밋**

```bash
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 commit -q -m "chore(evidence): delete signed-mobile build workflow, provenance tool, and TalkBack catalogs

The signed build workflow and provenance tool were not carried to devpath-mobile.
Recover them from db955eab when designing the mobile signing pipeline."
```

---

### Task 3: 보호 승인 허용 목록에서 서명·TalkBack 바인딩 제거

**Files:**
- Modify: `tools/mission_spine_protected_approval.mjs:21-54`
- Test: `tools/mission_spine_protected_approval.test.mjs`

**Interfaces:**
- Consumes: 없음.
- Produces: `validateProtectedApprovalFacts(facts)` 가 허용하는 (워크플로, 환경, 잡) 조합 = `et13-evidence.yml`/`mission-spine-et13-release-auth`/`Authenticate ET13 release inputs` · `mission-spine-manual-at-evidence.yml`/`mission-spine-manual-at-auth`/`Authenticate manual AT inputs` · 같은 워크플로/`manual-at-nvda`/`Approve manual NVDA evidence`. 그 밖은 `workflow/environment/job binding is not allowlisted` 로 거부.

- [ ] **Step 1: 실패하는 테스트 작성 — 기본 픽스처 재기준 + 음성 테스트**

`tools/mission_spine_protected_approval.test.mjs` 의 기본 픽스처 `approvalFacts` 는 지금 삭제될 서명 바인딩을 쓴다. 다음 문자열을 파일 전체에서 치환한다(9곳: 29·30·31·41·55·89·96·109·111행).

| 찾기 | 바꾸기 |
|---|---|
| `'mission-spine-mobile-signing-android'` | `'manual-at-nvda'` |
| `'Sign Android release'` | `'Approve manual NVDA evidence'` |
| `'.github/workflows/mission-spine-signed-mobile-build.yml'` | `'.github/workflows/mission-spine-manual-at-evidence.yml'` |

그리고 `test('ET13 release authentication environment is an exact protected binding', …)` 바로 아래에 다음 테스트를 추가한다.

```js
test('removed signed-mobile and TalkBack bindings are no longer allowlisted', () => {
  for (const [workflowPath, environmentName, jobName] of [
    [
      '.github/workflows/mission-spine-signed-mobile-build.yml',
      'mission-spine-mobile-signing-android',
      'Sign Android release',
    ],
    [
      '.github/workflows/mission-spine-manual-at-evidence.yml',
      'manual-at-talkback',
      'Approve manual TalkBack evidence',
    ],
  ]) {
    const removed = structuredClone(approvalFacts);
    removed.workflowBytes = Buffer.from(approvalFacts.workflowBytes);
    removed.workflowPath = workflowPath;
    removed.environmentName = environmentName;
    removed.jobName = jobName;
    removed.run.path = workflowPath;
    removed.environment.name = environmentName;
    removed.approvals[0].environments = [
      { id: removed.environment.id, name: environmentName },
    ];
    removed.jobs.jobs[0].name = jobName;
    assert.throws(
      () => validateProtectedApprovalFacts(removed),
      /binding is not allowlisted/,
    );
  }
  assert.doesNotMatch(verifierSource, /talkback|signed-mobile|mobile-signing/i);
});
```

(`verifierSource` 는 이 테스트 파일 16–19행이 이미 읽어 둔 도구 소스 문자열이다.)

- [ ] **Step 2: 테스트를 돌려 실패를 확인**

Run: `node --test D:/workspace/dpa/.worktrees/frontend-s2c2/tools/mission_spine_protected_approval.test.mjs`

Expected: 새 테스트가 FAIL(`Missing expected exception` — 두 바인딩이 아직 허용 목록에 있다). 나머지는 PASS(치환한 `manual-at-nvda` 바인딩은 이미 허용 목록에 있다).

- [ ] **Step 3: 허용 목록 수정**

`tools/mission_spine_protected_approval.mjs` 의 `allowedBindings` 를 다음으로 바꾼다.

```js
const allowedBindings = new Map([
  [
    '.github/workflows/et13-evidence.yml',
    new Map([
      [
        'mission-spine-et13-release-auth',
        protectedBinding('Authenticate ET13 release inputs'),
      ],
    ]),
  ],
  [
    '.github/workflows/mission-spine-manual-at-evidence.yml',
    new Map([
      [
        'mission-spine-manual-at-auth',
        protectedBinding('Authenticate manual AT inputs'),
      ],
      ['manual-at-nvda', protectedBinding('Approve manual NVDA evidence')],
    ]),
  ],
]);
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인**

Run: `node --test D:/workspace/dpa/.worktrees/frontend-s2c2/tools/mission_spine_protected_approval.test.mjs`

Expected: `# fail 0`.

- [ ] **Step 5: 커밋**

```bash
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 add tools/mission_spine_protected_approval.mjs tools/mission_spine_protected_approval.test.mjs
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 commit -q -m "refactor(evidence): drop signed-mobile and TalkBack protected approval bindings"
```

---

### Task 4: 워크플로와 계약 테스트

**Files:**
- Create: `apps/web/test/app/mission_spine_manual_at_workflow_contract_test.dart` (`apps/mobile/test/architecture/` 에서 `git mv`)
- Modify: `.github/workflows/mission-spine-manual-at-evidence.yml:256-557`

**Interfaces:**
- Consumes: Task 1 의 CLI — `validate-manual-inputs` 는 `--signed-root` 없이 호출한다.
- Produces: 잡 id `authenticate-inputs` · `approve-nvda` · `publish-manual-nvda`.

- [ ] **Step 1: 계약 테스트를 옮긴다**

```bash
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 mv \
  apps/mobile/test/architecture/mission_spine_manual_at_workflow_contract_test.dart \
  apps/web/test/app/mission_spine_manual_at_workflow_contract_test.dart
```

워크플로 경로 `'../../.github/workflows/mission-spine-manual-at-evidence.yml'` 는 `apps/web` 에서도 같은 깊이라 그대로 맞는다(선례: `apps/web/test/app/et13_baseline_approval_workflow_contract_test.dart` 가 같은 표기).

- [ ] **Step 2: 실패하는 테스트 작성 — 두 번째 테스트를 교체**

옮긴 파일에서 `test('manual AT lanes are protected and jointly publish sanitized artifacts', …)` 전체(28–58행)를 다음으로 바꾼다.

```dart
  test('manual NVDA lane is protected and publishes one sanitized artifact', () {
    expect(workflow.existsSync(), isTrue);
    final source = workflow.readAsStringSync().replaceAll('\r\n', '\n');
    expect(source, contains('name: manual-at-nvda'));
    expect(source, contains('name: Approve manual NVDA evidence'));
    expect(source, contains('\n  publish-manual-nvda:\n'));
    expect(source, contains('needs: [authenticate-inputs, approve-nvda]'));
    expect(source, contains('protected approvals require attempt 1'));
    expect(source, contains('tools/et13/verify_external_artifact.mjs'));
    expect(source, contains('candidate-source'));
    expect(source, contains('validate-manual-inputs'));
    expect(source, contains('validate-manual-packages'));
    expect(source, contains('unsealable-manual-at-review'));
    const releaseInput = r'${{ inputs.release_id }}';
    expect(source, contains('$releaseInput-manual-nvda-run-'));
    expect(source, contains('overwrite: false'));
    expect(source, contains('if-no-files-found: error'));
  });

  test('signed-mobile and TalkBack are absent from the web release evidence', () {
    final source = workflow
        .readAsStringSync()
        .replaceAll('\r\n', '\n')
        .toLowerCase();
    for (final forbidden in [
      'talkback',
      'signed',
      '.apk',
      'build-provenance',
      'mobile/',
      'voiceover',
      'signed_ipa',
      'publish-atomic-pair',
    ]) {
      expect(source, isNot(contains(forbidden)), reason: forbidden);
    }
    expect(
      File(
        '../../.github/workflows/mission-spine-signed-mobile-build.yml',
      ).existsSync(),
      isFalse,
    );
    expect(
      File(
        '../../tool/release-evidence/catalogs/manual-talkback.v1.json',
      ).existsSync(),
      isFalse,
    );
  });
```

첫 번째 테스트의 `expect(source, isNot(contains('signed_artifact_id:')));` 는 그대로 둔다.

- [ ] **Step 3: 테스트를 돌려 실패를 확인**

```bash
cd D:/workspace/dpa/.worktrees/frontend-s2c2 && dart pub get --enforce-lockfile
cd D:/workspace/dpa/.worktrees/frontend-s2c2/apps/web && flutter test test/app/mission_spine_manual_at_workflow_contract_test.dart
```

(이 두 줄은 각각 한 번의 Bash 호출 안에서 `cd` 와 명령을 `&&` 로 묶어 실행한다 — 호출 사이에 cwd 가 유지된다고 가정하지 않는다.)

Expected: 새 두 테스트가 FAIL(`publish-manual-nvda` 없음 · `talkback` 존재).

- [ ] **Step 4: 워크플로 수정 — `authenticate-inputs` 에서 서명 단계 제거**

`.github/workflows/mission-spine-manual-at-evidence.yml` 에서 다음 네 단계를 통째로 삭제한다(256–386행).

- `- name: Authenticate exact signed mobile producer and artifact metadata` (`id: signed`)
- `- name: Independently download and hash signed mobile archive`
- `- name: Download exact signed bundle through pinned action`
- `- name: Validate exact signed bytes and immutable manual catalogs`

삭제한 자리(`Bind canonical candidate bytes and protected GitOps source` 단계 뒤, `Preserve authenticated unsealable manual review inputs` 단계 앞)에 다음 단계를 넣는다.

```yaml
      - name: Validate immutable manual catalogs and stage review inputs
        shell: bash
        env:
          RELEASE_ID: ${{ inputs.release_id }}
          CANDIDATE_SPEC_SHA256: ${{ inputs.candidate_spec_sha256 }}
        run: |
          set -euo pipefail
          root=build/mission-spine/manual-at/external
          node tools/mission_spine_manual_at_evidence.mjs validate-manual-inputs \
            --repository-root=. \
            --candidate="${root}/candidate-action/candidate-spec.json" \
            --candidate-sha256="${CANDIDATE_SPEC_SHA256}" \
            --release-id="${RELEASE_ID}" \
            --source-sha="${GITHUB_SHA}"
          stage=build/mission-spine/manual-at/authenticated
          test ! -e "${stage}"
          mkdir -p "${stage}/candidate"
          cp "${root}/candidate-action/candidate-spec.json" "${stage}/candidate/candidate-spec.json"
          cp -R tool/release-evidence/catalogs "${stage}/catalogs"
          cp -R tool/release-evidence/provenance "${stage}/provenance"
```

- [ ] **Step 5: 워크플로 수정 — TalkBack 승인 잡 삭제, 게시 잡을 NVDA 단독으로**

`approve-talkback:` 잡 전체를 삭제한다. `publish-atomic-pair:` 잡을 아래로 교체한다(`Reject rerun approval reuse and verify exact checkout` 단계의 내용은 그대로 유지).

```yaml
  publish-manual-nvda:
    name: Publish manual NVDA evidence
    needs: [authenticate-inputs, approve-nvda]
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0

      - name: Reject rerun approval reuse and verify exact checkout
        shell: bash
        run: |
          set -euo pipefail
          test "${GITHUB_RUN_ATTEMPT}" = 1 || {
            echo 'protected approvals require attempt 1 and a fresh workflow_dispatch' >&2
            exit 1
          }
          test "${GITHUB_REPOSITORY}" = DevPathAi/devpath-frontend
          test "${GITHUB_REF}" = refs/heads/main
          test "$(git rev-parse HEAD)" = "${GITHUB_SHA}"
          test -z "$(git status --porcelain=v1 --untracked-files=all)"

      - name: Download authenticated manual review inputs
        uses: actions/download-artifact@018cc2cf5baa6db3ef3c5f8a56943fffe632ef53 # v6.0.0
        with:
          name: ${{ inputs.release_id }}-unsealable-manual-at-review-run-${{ github.run_id }}-attempt-${{ github.run_attempt }}
          path: build/mission-spine/manual-at/authenticated

      - name: Download protected NVDA approval
        uses: actions/download-artifact@018cc2cf5baa6db3ef3c5f8a56943fffe632ef53 # v6.0.0
        with:
          name: ${{ inputs.release_id }}-unsealable-manual-nvda-approval-run-${{ github.run_id }}-attempt-${{ github.run_attempt }}
          path: build/mission-spine/manual-at/approvals/nvda

      - name: Generate and validate the sanitized NVDA package
        shell: bash
        env:
          RELEASE_ID: ${{ inputs.release_id }}
          CANDIDATE_SPEC_SHA256: ${{ inputs.candidate_spec_sha256 }}
        run: |
          set -euo pipefail
          authenticated=build/mission-spine/manual-at/authenticated
          candidate="${authenticated}/candidate/candidate-spec.json"
          test -f "${candidate}"
          node tools/mission_spine_manual_at_evidence.mjs validate-manual-inputs \
            --repository-root=. \
            --candidate="${candidate}" \
            --candidate-sha256="${CANDIDATE_SPEC_SHA256}" \
            --release-id="${RELEASE_ID}" \
            --source-sha="${GITHUB_SHA}"
          package_root=build/mission-spine/manual-at/packages
          test ! -e "${package_root}"
          mkdir -p "${package_root}/manual-nvda"
          approval=build/mission-spine/manual-at/approvals/nvda/approval.json
          test -f "${approval}"
          test ! -L "${approval}"
          test "$(find "$(dirname "${approval}")" -type f | wc -l)" = 1
          node tools/mission_spine_manual_at_evidence.mjs manual-evidence \
            --repository-root=. \
            --candidate="${candidate}" \
            --candidate-sha256="${CANDIDATE_SPEC_SHA256}" \
            --release-id="${RELEASE_ID}" \
            --source-sha="${GITHUB_SHA}" \
            --producer-run-id="${GITHUB_RUN_ID}" \
            --producer-run-attempt="${GITHUB_RUN_ATTEMPT}" \
            --lane=manual-nvda \
            --approval="${approval}" \
            --output="${package_root}/manual-nvda/evidence.json"
          node tools/mission_spine_manual_at_evidence.mjs validate-manual-packages \
            --repository-root=. \
            --candidate="${candidate}" \
            --candidate-sha256="${CANDIDATE_SPEC_SHA256}" \
            --release-id="${RELEASE_ID}" \
            --source-sha="${GITHUB_SHA}" \
            --producer-run-id="${GITHUB_RUN_ID}" \
            --producer-run-attempt="${GITHUB_RUN_ATTEMPT}" \
            --package-root="${package_root}"

      - name: Publish exact NVDA sanitized evidence
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2
        with:
          name: ${{ inputs.release_id }}-manual-nvda-run-${{ github.run_id }}-attempt-${{ github.run_attempt }}
          path: build/mission-spine/manual-at/packages/manual-nvda
          if-no-files-found: error
          overwrite: false
          retention-days: 30
```

- [ ] **Step 6: YAML 이 파싱되고 잡 구성이 맞는지 확인**

```bash
py -c "
import yaml
d = yaml.safe_load(open(r'D:/workspace/dpa/.worktrees/frontend-s2c2/.github/workflows/mission-spine-manual-at-evidence.yml', encoding='utf-8'))
jobs = d['jobs']
assert list(jobs) == ['authenticate-inputs', 'approve-nvda', 'publish-manual-nvda'], list(jobs)
assert jobs['publish-manual-nvda']['needs'] == ['authenticate-inputs', 'approve-nvda']
names = [s.get('name') for s in jobs['authenticate-inputs']['steps']]
assert 'Validate immutable manual catalogs and stage review inputs' in names, names
assert not [n for n in names if n and 'signed' in n.lower()], names
print('ok', len(names), 'auth steps')
"
```

Expected: `ok 12 auth steps` (변경 전 15단계 − 서명 4단계 + 신규 1단계. PyYAML 이 없으면 `py -m pip install --user pyyaml` 뒤 재실행).

- [ ] **Step 7: 계약 테스트를 돌려 통과를 확인**

```bash
cd D:/workspace/dpa/.worktrees/frontend-s2c2/apps/web && flutter test test/app/mission_spine_manual_at_workflow_contract_test.dart
```

Expected: `All tests passed!` (5 tests).

- [ ] **Step 8: 포맷 확인 후 커밋**

```bash
dart format --output=none --set-exit-if-changed D:/workspace/dpa/.worktrees/frontend-s2c2/apps/web/test/app/mission_spine_manual_at_workflow_contract_test.dart
```

Expected: `0 changed`. 바뀐다고 나오면 `--output=none --set-exit-if-changed` 를 빼고 한 번 실행해 포맷을 적용한다.

```bash
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 add .github/workflows/mission-spine-manual-at-evidence.yml apps/web/test/app/mission_spine_manual_at_workflow_contract_test.dart apps/mobile/test/architecture
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 commit -q -m "ci(evidence): authenticate the candidate only and publish NVDA evidence alone

Move the manual AT workflow contract test to apps/web so it survives the apps/mobile removal."
```

---

### Task 5: CI 에 증거 도구 테스트 추가 · 잔존 리터럴 점검

**Files:**
- Modify: `.github/workflows/ci.yml:41-42`

- [ ] **Step 1: `ci.yml` 에 단계 추가**

`- name: Validate immutable registry client` 단계 바로 아래에 넣는다.

```yaml
      - name: Validate Mission Spine evidence tools
        run: >-
          node --test
          tools/mission_spine_manual_at_evidence.test.mjs
          tools/mission_spine_protected_approval.test.mjs
```

- [ ] **Step 2: 잔존 리터럴 점검**

```bash
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 grep -niE "talkback|mobile_test_artifacts|mission_spine_release_evidence|signed[-_ ]?(mobile|apk|android)|mission-spine-mobile-signing" -- . ':!apps/mobile' ':!docs'
```

Expected: 출력이 다음 세 종류뿐이다 — (a) `tools/mission_spine_manual_at_evidence.test.mjs` 의 음성 테스트 픽스처, (b) `tools/mission_spine_protected_approval.test.mjs` 의 음성 테스트, (c) `apps/web/test/app/mission_spine_manual_at_workflow_contract_test.dart` 의 금지어 목록. 그 밖의 파일이 나오면 그 파일을 열어 원인을 확인하고, 이 계획의 범위(릴리스 증거)에 속하면 제거하며 범위 밖이면 PR 본문에 기록한다.

- [ ] **Step 3: 전체 로컬 검증**

```bash
node --test D:/workspace/dpa/.worktrees/frontend-s2c2/tools/mission_spine_manual_at_evidence.test.mjs D:/workspace/dpa/.worktrees/frontend-s2c2/tools/mission_spine_protected_approval.test.mjs
```

Expected: `# fail 0`.

```bash
cd D:/workspace/dpa/.worktrees/frontend-s2c2 && dart run melos bootstrap --enforce-lockfile && dart run melos run analyze
```

Expected: `No issues found!` (패키지별). `packages/dp_design/test/theme/dp_code_font_test.dart` 의 CRLF 1건은 테스트이지 analyze 가 아니므로 여기서는 나오지 않는다.

- [ ] **Step 4: 커밋**

```bash
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 add .github/workflows/ci.yml
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 commit -q -m "ci: run the Mission Spine evidence tool tests"
```

---

### Task 6: Codex 리뷰 · PR · 머지

**Files:** 없음

- [ ] **Step 1: Codex 리뷰(직렬 1건)**

리뷰 지시문을 스크래치패드에 `s2c2-review-prompt.txt` 로 저장한다.

```
You are reviewing a supply-chain hardening change in the repository at the current directory.
Review ONLY the diff `git diff origin/develop...HEAD`. Do not modify any file.

Context: the web release contract drops the signed Android build and the TalkBack manual lane.
Manual accessibility evidence becomes NVDA-only. The NVDA evidence JSON key set and order must NOT change.

Check specifically:
1. tools/mission_spine_manual_at_evidence.mjs: does any path still accept a candidate that carries
   quality_evidence_inputs.mobile_test_artifacts or a manual-talkback catalog binding? It must fail closed.
2. Is any authentication step of the candidate (protected approval, read-only GitOps token, App scope check,
   metadata authentication, independent archive hash, pinned-action download, byte/source binding)
   weakened or reordered in .github/workflows/mission-spine-manual-at-evidence.yml?
3. Does the publish job still refuse reruns (attempt 1 only) and still validate the package before upload?
4. Dead code, dangling imports, or CLI options left behind by the removal.
5. Do the tests actually prove the negative cases, or do they pass for the wrong reason?

Output format: a list of findings, each with file:line, severity (blocker/major/minor), and a concrete fix.
End with a line `VERDICT: approve` or `VERDICT: changes-requested`.
```

```bash
"/c/Users/deepe/AppData/Local/Programs/OpenAI/Codex/bin/codex" exec -s read-only \
  -C D:/workspace/dpa/.worktrees/frontend-s2c2 - \
  < "<스크래치패드>/s2c2-review-prompt.txt" > "<스크래치패드>/s2c2-review.log" 2>&1; echo "CODEX_EXIT=$?"
```

Expected: `CODEX_EXIT=0`. **로그 크기와 끝부분을 반드시 확인한다**(`wc -c`, 마지막 40줄). 프롬프트가 에코된 `VERDICT:` 줄과 Codex 가 낸 줄을 구분한다 — 프롬프트 길이 이후 구간만 센다. 사용 한도 오류(`You've hit your usage limit`)면 리뷰 없이 진행하지 말고 사용자에게 보고한다.

- [ ] **Step 2: 지적 재확인과 반영**

지적마다 해당 파일·줄을 직접 열어 사실인지 확인한다. 사실이면 테스트를 먼저 추가하고 고친 뒤 커밋한다. 사실이 아니면 근거와 함께 PR 본문에 "기각" 으로 기록한다.

- [ ] **Step 3: push · PR**

```bash
git -C D:/workspace/dpa/.worktrees/frontend-s2c2 push -u origin chore/s2c2-drop-signed-mobile-talkback
gh pr create -R DevPathAi/devpath-frontend --base develop --head chore/s2c2-drop-signed-mobile-talkback \
  --title "chore(evidence): 웹 릴리스 증거에서 서명 모바일·TalkBack 제거 (S2c-2)" \
  --body-file "<스크래치패드>/s2c2-pr-body.md"
```

PR 본문(`s2c2-pr-body.md`)에 넣을 것: 스펙 경로 · 접합면 요약(NVDA 증거 JSON 불변, candidate `quality_evidence_inputs` exact-key) · 삭제 파일 목록과 복구 지점 `db955eab` · Task 5 Step 2 의 grep 결과 · Codex 리뷰 지적과 처리 · "gitops S2a 가 main 에 들어가기 전에는 이 워크플로를 실제 릴리스에 쓰지 않는다(candidate 모양이 어긋난다)" · 마지막 줄 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

- [ ] **Step 4: CI 녹색 확인 후 머지**

```bash
gh pr checks <PR번호> -R DevPathAi/devpath-frontend
```

`gh pr checks --watch` 는 504 가 나므로 쓰지 않는다. perf-gate 가 약 23분 걸린다 — 그동안 gitops S2a 계획의 Task 를 진행한다. 전부 `pass` 면:

```bash
gh pr merge <PR번호> -R DevPathAi/devpath-frontend --merge
git -C D:/workspace/dpa/devpath-frontend fetch origin
git -C D:/workspace/dpa/devpath-frontend log -1 --format='%H %s' origin/develop
```

머지된 develop 커밋의 **전체 SHA 를 기록**한다 — gitops S2a 계획 PR ② 의 핀 출처 커밋이다.

- [ ] **Step 5: 컨트롤러 검증**

```bash
git -C D:/workspace/dpa/devpath-frontend log origin/develop --oneline -8
git -C D:/workspace/dpa/devpath-frontend status --short --branch | head -3
git -C D:/workspace/dpa/devpath-gitops branch --list 'chore/s2c2*'
git -C D:/workspace/dpa/devpath-mobile branch --list 'chore/s2c2*'
```

Expected: develop 에 이 PR 의 커밋만 추가됨 · frontend 주 checkout 은 여전히 `feat/evidence-auth-smoke` 이고 변경 없음 · 인접 레포에 낯선 브랜치 없음.

---

## 실행 기록 (2026-09-19) — 계획과 달랐던 점

- Node 24 의 `node --test` 요약 접두어는 `#` 가 아니라 `ℹ` 다(`ℹ pass 27`). 기준선 27 pass → 변경 뒤 26 pass(`release_evidence` 테스트 4건 삭제, 새 테스트 추가).
- **Task 4**: 의존성 해석(`dart pub get`)을 기다리는 사이 워크플로를 먼저 고쳐, 백그라운드로 돌린 "빨강 확인"이 녹색으로 나왔다. 워크플로만 되돌린 상태에서 새 2건이 실패함을 따로 실증한 뒤 복원했다. 이때 `git stash push -- <경로>` / `pop` 을 썼는데, **stash 스택은 모든 worktree 가 공유**한다(이 레포에는 다른 세션의 `gstack-gitignore` stash 가 있었다) — 다음부터는 임시 WIP 커밋이나 `git stash push -m <고유태그>` + `apply <sha>` 를 쓴다.
- **Task 4 Step 8**: 옮긴 Dart 테스트가 `dart format` 에서 1건 바뀌었다(계획의 코드 블록 줄바꿈이 포매터 결과와 달랐다). 포맷 적용 뒤 테스트 재통과 확인.
- **Task 5 Step 2**: 잔존 grep 에 `.github/workflows/mobile.yml` 의 "**un**signed Android evidence" 2건이 걸렸다 — 모바일 CI 의 무서명 빌드 단계로 정규식 오탐. S2c-3 에서 파일째 삭제.
- **Task 6**: Codex 기본 모델 `gpt-5.6-sol` 이 400 으로 거부돼 `-m gpt-5.5 -c model_reasoning_effort=high` 로 실행. 결과 No findings · approve(Codex 샌드박스에 node 가 없어 테스트는 로컬 결과가 근거).
