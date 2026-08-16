import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import {
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  artifactName,
  discoverCandidateArtifact,
  listAllGitHubPages,
  createPrivacyEvidence,
  selectUniqueCandidateMatch,
  validateCandidateArtifactFacts,
  validateCandidateBinding,
  validateCandidateSourceFacts,
  validateCandidateWorkflowDispatch,
  validatePrivacyArtifactMetadata,
  validatePrivacyArtifactZip,
  validatePrivacyEvidence,
  validateProtectedApprovalFacts,
} from './mission_spine_privacy_approval.mjs';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const releaseId = 'ms-20990101-privacy-fixture';
const sourceSha = '1234567890abcdef1234567890abcdef12345678';
const candidateHeadSha = '234567890abcdef1234567890abcdef123456789';
const gitopsBaseSha = '34567890abcdef1234567890abcdef1234567890';
const candidateSha = 'abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789';
const workflowBytes = Buffer.from('name: trusted privacy approval workflow\n');
const candidateWorkflowBytes = Buffer.from(
  'name: Candidate\non:\n  workflow_dispatch:\n    inputs:\n' +
  '      release_id:\n        required: true\n        type: string\npermissions:\n  contents: read\n',
);
const privacy = {
  collection_mode: 'explicit-consent',
  approval_source_sha: sourceSha,
  region: 'EU',
  project_identity: 'posthog-eu-mission-spine',
  retention_days: 90,
  access_owner: 'devpathai/privacy-owners',
  deletion_runbook: 'documents/privacy/posthog-deletion-v1',
};

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function candidateBytes(overrides = {}) {
  return Buffer.from(`${JSON.stringify({
    $schema: '../schema-v1.json',
    schema_version: 1,
    document_type: 'candidate-spec',
    release_id: releaseId,
    gitops: {
      repository: 'DevPathAi/devpath-gitops',
      base_sha: gitopsBaseSha,
      base_web_tag: '4567890abcdef1234567890abcdef12345678901',
      base_web_digest: `sha256:${'1'.repeat(64)}`,
      web_kustomization: 'apps/devpath-web/base/kustomization.yaml',
    },
    analytics_privacy: privacy,
    ...overrides,
  }, null, 2)}\n`);
}

function approvalFacts() {
  return {
    repository: 'DevPathAi/documents',
    sourceSha,
    runId: 701,
    runAttempt: 1,
    workflowPath: '.github/workflows/mission-spine-privacy-approval.yml',
    environmentName: 'mission-spine-privacy-approval',
    jobName: 'Approve analytics privacy release',
    repositoryInfo: {
      full_name: 'DevPathAi/documents',
      default_branch: 'main',
      archived: false,
    },
    run: {
      id: 701,
      run_attempt: 1,
      event: 'workflow_dispatch',
      status: 'in_progress',
      conclusion: null,
      head_sha: sourceSha,
      head_branch: 'main',
      path: '.github/workflows/mission-spine-privacy-approval.yml',
      repository: { full_name: 'DevPathAi/documents' },
      head_repository: { full_name: 'DevPathAi/documents' },
      actor: { id: 11, login: 'release-initiator', type: 'User' },
      triggering_actor: { id: 11, login: 'release-initiator', type: 'User' },
      created_at: '2025-08-17T01:00:00Z',
    },
    branch: {
      name: 'main',
      protected: true,
      commit: { sha: sourceSha },
    },
    environment: {
      id: 91,
      name: 'mission-spine-privacy-approval',
      protection_rules: [
        {
          type: 'required_reviewers',
          prevent_self_review: true,
          reviewers: [{
            type: 'Team',
            reviewer: {
              id: 81,
              slug: 'privacy-owners',
              organization: { login: 'DevPathAi' },
            },
          }],
        },
      ],
    },
    teamMemberships: [
      {
        team_id: 81,
        team_slug: 'privacy-owners',
        organization: 'DevPathAi',
        user_login: 'privacy-reviewer',
        state: 'active',
        role: 'member',
      },
    ],
    approvals: [
      {
        state: 'approved',
        user: { id: 21, login: 'privacy-reviewer', type: 'User' },
        environments: [{ id: 91, name: 'mission-spine-privacy-approval' }],
      },
    ],
    jobs: {
      jobs: [
        {
          name: 'Approve analytics privacy release',
          run_id: 701,
          head_sha: sourceSha,
          status: 'in_progress',
          conclusion: null,
          started_at: '2025-08-17T01:02:03Z',
        },
      ],
    },
    workflowBytes: Buffer.from(workflowBytes),
    localWorkflowBytes: Buffer.from(workflowBytes),
  };
}

function cloneFacts() {
  const value = structuredClone(approvalFacts());
  value.workflowBytes = Buffer.from(workflowBytes);
  value.localWorkflowBytes = Buffer.from(workflowBytes);
  return value;
}

const CRC32_TABLE = new Uint32Array(256);
for (let index = 0; index < CRC32_TABLE.length; index += 1) {
  let value = index;
  for (let bit = 0; bit < 8; bit += 1) {
    value = (value >>> 1) ^ (0xedb88320 & -(value & 1));
  }
  CRC32_TABLE[index] = value >>> 0;
}

function crc32(bytes) {
  let value = 0xffffffff;
  for (const byte of bytes) {
    value = (value >>> 8) ^ CRC32_TABLE[(value ^ byte) & 0xff];
  }
  return (value ^ 0xffffffff) >>> 0;
}

function storedZip(entries) {
  const locals = [];
  const centrals = [];
  let offset = 0;
  for (const [name, body] of entries) {
    const nameBytes = Buffer.from(name, 'utf8');
    const bytes = Buffer.from(body);
    const checksum = crc32(bytes);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0x0800, 6);
    local.writeUInt16LE(0, 8);
    local.writeUInt32LE(checksum, 14);
    local.writeUInt32LE(bytes.length, 18);
    local.writeUInt32LE(bytes.length, 22);
    local.writeUInt16LE(nameBytes.length, 26);
    locals.push(local, nameBytes, bytes);

    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE((3 << 8) | 20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(0x0800, 8);
    central.writeUInt16LE(0, 10);
    central.writeUInt32LE(checksum, 16);
    central.writeUInt32LE(bytes.length, 20);
    central.writeUInt32LE(bytes.length, 24);
    central.writeUInt16LE(nameBytes.length, 28);
    central.writeUInt32LE((0o100644 << 16) >>> 0, 38);
    central.writeUInt32LE(offset, 42);
    centrals.push(central, nameBytes);
    offset += local.length + nameBytes.length + bytes.length;
  }
  const centralBytes = Buffer.concat(centrals);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(entries.length, 8);
  end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(centralBytes.length, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, centralBytes, end]);
}

function responseHeaders(values = {}) {
  const normalized = new Map(
    Object.entries(values).map(([key, value]) => [key.toLowerCase(), String(value)]),
  );
  return { get: (name) => normalized.get(name.toLowerCase()) ?? null };
}

function jsonResponse(value, status = 200) {
  const text = JSON.stringify(value);
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: responseHeaders({ 'content-length': Buffer.byteLength(text) }),
    async text() { return text; },
  };
}

function bytesResponse(bytes, status = 200, headers = {}) {
  const body = Buffer.from(bytes);
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: responseHeaders(headers),
    async arrayBuffer() {
      return body.buffer.slice(body.byteOffset, body.byteOffset + body.byteLength);
    },
  };
}

test('binds exact raw candidate bytes and the exact analytics privacy object', () => {
  const bytes = candidateBytes();
  const actual = validateCandidateBinding({
    candidateBytes: bytes,
    releaseId,
    candidateSpecSha256: sha256(bytes),
    approvalSourceSha: sourceSha,
  });
  assert.deepEqual(actual, privacy);

  assert.throws(() => validateCandidateBinding({
    candidateBytes: bytes,
    releaseId,
    candidateSpecSha256: '1'.repeat(64),
    approvalSourceSha: sourceSha,
  }), /candidate.*SHA-256/i);

  const duplicate = Buffer.from(
    `{"document_type":"candidate-spec","release_id":"${releaseId}",` +
    `"release_id":"${releaseId}","analytics_privacy":${JSON.stringify(privacy)}}`,
  );
  assert.throws(() => validateCandidateBinding({
    candidateBytes: duplicate,
    releaseId,
    candidateSpecSha256: sha256(duplicate),
    approvalSourceSha: sourceSha,
  }), /duplicate JSON key/i);

  const substituted = structuredClone(privacy);
  substituted.approval_source_sha = '2'.repeat(40);
  const substitutedBytes = candidateBytes({ analytics_privacy: substituted });
  assert.throws(() => validateCandidateBinding({
    candidateBytes: substitutedBytes,
    releaseId,
    candidateSpecSha256: sha256(substitutedBytes),
    approvalSourceSha: sourceSha,
  }), /approval_source_sha/i);
});

test('accepts only the API-current candidate run artifact and protected-main one-file child', () => {
  const raw = candidateBytes();
  const digest = sha256(raw);
  const zip = storedZip([['candidate-spec.json', raw]]);
  const run = {
    id: 501,
    run_attempt: 2,
    event: 'workflow_dispatch',
    status: 'completed',
    conclusion: 'success',
    head_sha: candidateHeadSha,
    head_branch: `release/candidate-${releaseId}`,
    path: '.github/workflows/mission-spine-candidate.yml',
    repository: { full_name: 'DevPathAi/devpath-gitops' },
    head_repository: { full_name: 'DevPathAi/devpath-gitops' },
  };
  const artifact = {
    id: 601,
    name: `${releaseId}-candidate-spec-run-501-attempt-2`,
    expired: false,
    expires_at: '2099-01-01T00:00:00Z',
    size_in_bytes: zip.length,
    digest: `sha256:${sha256(zip)}`,
    workflow_run: { id: 501, head_sha: candidateHeadSha },
  };
  const selected = validateCandidateArtifactFacts({
    releaseId,
    candidateSpecSha256: digest,
    approvalSourceSha: sourceSha,
    run,
    artifact,
    zipBytes: zip,
  });
  assert.equal(selected.runId, 501);
  assert.equal(selected.runAttempt, 2);
  assert.ok(selected.candidateBytes.equals(raw));

  const sourceFacts = {
    releaseId,
    candidateBytes: raw,
    candidateSpecSha256: digest,
    approvalSourceSha: sourceSha,
    headSha: candidateHeadSha,
    repositoryInfo: {
      full_name: 'DevPathAi/devpath-gitops',
      default_branch: 'main',
      archived: false,
    },
    mainBranch: { name: 'main', protected: true, commit: { sha: gitopsBaseSha } },
    headCommit: { sha: candidateHeadSha, parents: [{ sha: gitopsBaseSha }] },
    comparison: {
      status: 'ahead',
      ahead_by: 1,
      behind_by: 0,
      total_commits: 1,
      merge_base_commit: { sha: gitopsBaseSha },
      commits: [{ sha: candidateHeadSha }],
      files: [{
        filename: `release-manifests/candidates/${releaseId}.candidate-spec.json`,
        status: 'added',
      }],
    },
    candidateBlobBytes: raw,
    baseWorkflowBytes: Buffer.from(candidateWorkflowBytes),
    headWorkflowBytes: Buffer.from(candidateWorkflowBytes),
  };
  assert.equal(validateCandidateSourceFacts(sourceFacts), true);

  for (const mutate of [
    (copy) => { copy.mainBranch.protected = false; },
    (copy) => { copy.headCommit.parents[0].sha = candidateHeadSha; },
    (copy) => { copy.comparison.files[0].status = 'modified'; },
    (copy) => { copy.comparison.files.push({ filename: 'extra.txt', status: 'added' }); },
    (copy) => { copy.candidateBlobBytes = Buffer.from('substituted candidate\n'); },
    (copy) => { copy.headWorkflowBytes = Buffer.from('substituted workflow\n'); },
  ]) {
    const copy = structuredClone(sourceFacts);
    copy.candidateBytes = Buffer.from(raw);
    copy.candidateBlobBytes = Buffer.from(raw);
    copy.baseWorkflowBytes = Buffer.from(candidateWorkflowBytes);
    copy.headWorkflowBytes = Buffer.from(candidateWorkflowBytes);
    mutate(copy);
    assert.throws(() => validateCandidateSourceFacts(copy));
  }

  for (const mutate of [
    (copy) => { copy.run.path = '.github/workflows/attacker.yml'; },
    (copy) => { copy.run.path = `${copy.run.path}@${copy.run.head_branch}`; },
    (copy) => { copy.run.head_branch = 'main'; },
    (copy) => { copy.artifact.name = `${releaseId}-candidate-spec-run-501-attempt-1`; },
    (copy) => { copy.artifact.digest = `sha256:${'9'.repeat(64)}`; },
    (copy) => { copy.artifact.workflow_run.head_sha = gitopsBaseSha; },
    (copy) => { copy.artifact.expires_at = '2020-01-01T00:00:00Z'; },
  ]) {
    const copy = { run: structuredClone(run), artifact: structuredClone(artifact) };
    mutate(copy);
    assert.throws(() => validateCandidateArtifactFacts({
      releaseId,
      candidateSpecSha256: digest,
      approvalSourceSha: sourceSha,
      run: copy.run,
      artifact: copy.artifact,
      zipBytes: zip,
    }));
  }

  const unsafeZip = storedZip([
    ['candidate-spec.json', raw],
    ['raw-review.json', Buffer.from('{}\n')],
  ]);
  const unsafeArtifact = {
    ...artifact,
    size_in_bytes: unsafeZip.length,
    digest: `sha256:${sha256(unsafeZip)}`,
  };
  assert.throws(() => validateCandidateArtifactFacts({
    releaseId,
    candidateSpecSha256: digest,
    approvalSourceSha: sourceSha,
    run,
    artifact: unsafeArtifact,
    zipBytes: unsafeZip,
  }), /exactly one/i);

  assert.equal(selectUniqueCandidateMatch([selected]), selected);
  assert.throws(() => selectUniqueCandidateMatch([selected, { ...selected, runId: 502 }]), /exactly one/i);
});

test('candidate workflow parser rejects extra dispatch inputs and sibling triggers', () => {
  const raw = candidateWorkflowBytes;
  assert.equal(validateCandidateWorkflowDispatch(raw), true);
  for (const mutation of [
    raw.toString().replace('  workflow_dispatch:', '  push:\n  workflow_dispatch:'),
    raw.toString().replace('        type: string', '        type: string\n        default: unsafe'),
    raw.toString().replace('permissions:', '      digest:\n        required: true\n        type: string\npermissions:'),
    raw.toString().replace('on:', '"on":'),
  ]) {
    assert.throws(() => validateCandidateWorkflowDispatch(Buffer.from(mutation)));
  }
});

test('candidate discovery enumerates every API page before uniqueness is decided', async () => {
  const first = Array.from({ length: 100 }, (_, index) => ({ id: index + 1 }));
  const later = { id: 101 };
  const fetchImpl = async (url) => {
    const page = Number(new URL(url).searchParams.get('page'));
    const value = page === 1 ? first : page === 2 ? [later] : [];
    return {
      ok: true,
      status: 200,
      async text() {
        return JSON.stringify({ total_count: 101, workflow_runs: value });
      },
    };
  };
  const runs = await listAllGitHubPages({
    path: '/repos/DevPathAi/devpath-gitops/actions/workflows/test/runs?event=workflow_dispatch',
    field: 'workflow_runs',
    token: 'test-token',
    fetchImpl,
  });
  assert.equal(runs.length, 101);
  assert.equal(runs.at(-1).id, later.id);
});

test('candidate discovery follows a credential-free redirect and rejects a competing fresh run', async () => {
  const raw = candidateBytes();
  const rawDigest = sha256(raw);
  const zip = storedZip([['candidate-spec.json', raw]]);
  const zipDigest = sha256(zip);
  const branch = `release/candidate-${releaseId}`;

  function run(id) {
    return {
      id,
      run_attempt: 2,
      event: 'workflow_dispatch',
      status: 'completed',
      conclusion: 'success',
      head_sha: candidateHeadSha,
      head_branch: branch,
      path: '.github/workflows/mission-spine-candidate.yml',
      repository: { full_name: 'DevPathAi/devpath-gitops' },
      head_repository: { full_name: 'DevPathAi/devpath-gitops' },
    };
  }

  function artifact(runId) {
    return {
      id: runId + 100,
      name: `${releaseId}-candidate-spec-run-${runId}-attempt-2`,
      expired: false,
      expires_at: '2099-01-01T00:00:00Z',
      size_in_bytes: zip.length,
      digest: `sha256:${zipDigest}`,
      workflow_run: { id: runId, head_sha: candidateHeadSha },
    };
  }

  function fetchFor(runIds) {
    return async (input) => {
      const url = new URL(input);
      const path = url.pathname;
      if (url.hostname === 'artifact.example.invalid') return bytesResponse(zip);
      if (path.includes('/actions/workflows/') && path.endsWith('/runs')) {
        return jsonResponse({ total_count: runIds.length, workflow_runs: runIds.map(run) });
      }
      const attempt = path.match(/\/actions\/runs\/(\d+)\/attempts\/2$/);
      if (attempt) return jsonResponse(run(Number(attempt[1])));
      const current = path.match(/\/actions\/runs\/(\d+)$/);
      if (current) return jsonResponse(run(Number(current[1])));
      const artifacts = path.match(/\/actions\/runs\/(\d+)\/artifacts$/);
      if (artifacts) {
        const value = artifact(Number(artifacts[1]));
        return jsonResponse({ total_count: 1, artifacts: [value] });
      }
      const metadata = path.match(/\/actions\/artifacts\/(\d+)$/);
      if (metadata) return jsonResponse(artifact(Number(metadata[1]) - 100));
      if (/\/actions\/artifacts\/\d+\/zip$/.test(path)) {
        return bytesResponse(Buffer.alloc(0), 302, {
          location: 'https://artifact.example.invalid/candidate.zip',
        });
      }
      if (path === '/repos/DevPathAi/devpath-gitops') {
        return jsonResponse({
          full_name: 'DevPathAi/devpath-gitops',
          default_branch: 'main',
          archived: false,
        });
      }
      if (path.endsWith('/branches/main')) {
        return jsonResponse({ name: 'main', protected: true, commit: { sha: gitopsBaseSha } });
      }
      if (path.endsWith(`/commits/${candidateHeadSha}`)) {
        return jsonResponse({ sha: candidateHeadSha, parents: [{ sha: gitopsBaseSha }] });
      }
      if (path.endsWith(`/compare/${gitopsBaseSha}...${candidateHeadSha}`)) {
        return jsonResponse({
          status: 'ahead',
          ahead_by: 1,
          behind_by: 0,
          total_commits: 1,
          merge_base_commit: { sha: gitopsBaseSha },
          commits: [{ sha: candidateHeadSha }],
          files: [{
            filename: `release-manifests/candidates/${releaseId}.candidate-spec.json`,
            status: 'added',
          }],
        });
      }
      if (path.includes('/contents/release-manifests/candidates/')) {
        return jsonResponse({
          type: 'file',
          path: `release-manifests/candidates/${releaseId}.candidate-spec.json`,
          encoding: 'base64',
          size: raw.length,
          content: raw.toString('base64'),
        });
      }
      if (path.includes('/contents/.github/workflows/mission-spine-candidate.yml')) {
        return jsonResponse({
          type: 'file',
          path: '.github/workflows/mission-spine-candidate.yml',
          encoding: 'base64',
          size: candidateWorkflowBytes.length,
          content: candidateWorkflowBytes.toString('base64'),
        });
      }
      throw new Error(`unexpected test URL: ${url}`);
    };
  }

  const selected = await discoverCandidateArtifact({
    releaseId,
    candidateSpecSha256: rawDigest,
    approvalSourceSha: sourceSha,
    token: 'test-token',
    fetchImpl: fetchFor([501]),
  });
  assert.equal(selected.runId, 501);
  await assert.rejects(
    discoverCandidateArtifact({
      releaseId,
      candidateSpecSha256: rawDigest,
      approvalSourceSha: sourceSha,
      token: 'test-token',
      fetchImpl: fetchFor([501, 502]),
    }),
    /exactly one eligible/i,
  );
});

test('authenticates the exact protected job, environment, workflow, and non-self reviewer', () => {
  assert.deepEqual(validateProtectedApprovalFacts(approvalFacts()), {
    approval_environment: 'mission-spine-privacy-approval',
    approval_environment_id: 91,
    approval_job_name: 'Approve analytics privacy release',
    approved_by: 'privacy-reviewer',
    approved_by_id: 21,
    approval_effective_at: '2025-08-17T01:02:03Z',
  });
  const directUser = approvalFacts();
  directUser.environment.protection_rules[0].reviewers = [
    { type: 'User', reviewer: { id: 21, login: 'privacy-reviewer' } },
  ];
  directUser.teamMemberships = [];
  assert.equal(
    validateProtectedApprovalFacts(directUser).approved_by,
    'privacy-reviewer',
  );

  const mutations = [
    (facts) => { facts.runAttempt = 2; facts.run.run_attempt = 2; },
    (facts) => { facts.run.path = '.github/workflows/mission-spine-privacy-approval.yml@main'; },
    (facts) => { facts.run.path = '.github/workflows/mission-spine-privacy-approval.yml@refs/heads/main'; },
    (facts) => { facts.run.head_repository.full_name = 'attacker/fork'; },
    (facts) => { facts.branch.protected = false; },
    (facts) => { facts.environment.protection_rules[0].prevent_self_review = false; },
    (facts) => { facts.teamMemberships[0].state = 'pending'; },
    (facts) => { facts.teamMemberships[0].role = 'unknown'; },
    (facts) => { facts.teamMemberships[0].team_slug = 'lookalike'; },
    (facts) => { facts.approvals[0].user = { id: 11, login: 'release-initiator', type: 'User' }; },
    (facts) => { facts.approvals.push(structuredClone(facts.approvals[0])); },
    (facts) => { facts.jobs.jobs[0].name = 'Lookalike approval'; },
    (facts) => { facts.workflowBytes = Buffer.from('substituted workflow\n'); },
    (facts) => { facts.repositoryInfo.default_branch = 'develop'; },
  ];
  for (const mutate of mutations) {
    const facts = cloneFacts();
    mutate(facts);
    assert.throws(() => validateProtectedApprovalFacts(facts));
  }
});

test('generates and validates the exact ordered one-file privacy evidence payload', () => {
  const approval = validateProtectedApprovalFacts(approvalFacts());
  const evidence = createPrivacyEvidence({
    candidateSpecSha256: candidateSha,
    producerRunId: 701,
    producerRunAttempt: 1,
    privacy,
    approval,
  });
  assert.deepEqual(evidence, {
    candidate_spec_sha256: candidateSha,
    status: 'passed',
    producer_run_id: 701,
    producer_run_attempt: 1,
    approved_at: '2025-08-17T01:02:03Z',
    collection_mode: 'explicit-consent',
    region: 'EU',
    project_identity: 'posthog-eu-mission-spine',
    retention_days: 90,
    access_owner: 'devpathai/privacy-owners',
    deletion_runbook: 'documents/privacy/posthog-deletion-v1',
    approval_environment: 'mission-spine-privacy-approval',
    approval_environment_id: 91,
    approval_job_name: 'Approve analytics privacy release',
    approved_by: 'privacy-reviewer',
    approved_by_id: 21,
    approval_effective_at: '2025-08-17T01:02:03Z',
  });
  assert.equal(validatePrivacyEvidence(evidence, {
    candidateSpecSha256: candidateSha,
    producerRunId: 701,
    producerRunAttempt: 1,
    privacy,
    approval,
  }), true);

  assert.throws(() => createPrivacyEvidence({
    candidateSpecSha256: candidateSha,
    producerRunId: 701,
    producerRunAttempt: 2,
    privacy,
    approval,
  }), /attempt 1|fresh dispatch/i);
  const extra = { ...evidence, raw_review_notes: 'must never be sealable' };
  assert.throws(() => validatePrivacyEvidence(extra, {
    candidateSpecSha256: candidateSha,
    producerRunId: 701,
    producerRunAttempt: 1,
    privacy,
    approval,
  }), /exact ordered key set/i);
  const forged = { ...evidence, approved_at: '2025-08-17T01:01:00Z' };
  assert.throws(() => validatePrivacyEvidence(forged, {
    candidateSpecSha256: candidateSha,
    producerRunId: 701,
    producerRunAttempt: 1,
    privacy,
    approval,
  }), /approved_at/i);
});

test('authenticates run-scoped artifact metadata and exact one-file ZIP bytes', () => {
  const approval = validateProtectedApprovalFacts(approvalFacts());
  const evidence = Buffer.from(`${JSON.stringify(createPrivacyEvidence({
    candidateSpecSha256: candidateSha,
    producerRunId: 701,
    producerRunAttempt: 1,
    privacy,
    approval,
  }), null, 2)}\n`);
  const zip = storedZip([['evidence.json', evidence]]);
  const digest = sha256(zip);
  const name = artifactName(releaseId, 701, 1);
  assert.equal(name, `${releaseId}-privacy-approval-run-701-attempt-1`);
  assert.equal(validatePrivacyArtifactMetadata({
    metadata: {
      id: 801,
      name,
      expired: false,
      size_in_bytes: zip.length,
      digest: `sha256:${digest}`,
      workflow_run: { id: 701, head_sha: sourceSha },
    },
    artifactId: 801,
    artifactName: name,
    artifactDigest: digest,
    runId: 701,
    sourceSha,
  }), true);
  assert.equal(validatePrivacyArtifactZip({
    zipBytes: zip,
    evidenceBytes: evidence,
    expectedZipSha256: digest,
  }), true);

  const traversal = storedZip([['../evidence.json', evidence]]);
  assert.throws(() => validatePrivacyArtifactZip({
    zipBytes: traversal,
    evidenceBytes: evidence,
    expectedZipSha256: sha256(traversal),
  }), /unsafe|root/i);
  const extra = storedZip([
    ['evidence.json', evidence],
    ['review-notes.txt', Buffer.from('not sealable\n')],
  ]);
  assert.throws(() => validatePrivacyArtifactZip({
    zipBytes: extra,
    evidenceBytes: evidence,
    expectedZipSha256: sha256(extra),
  }), /exactly one|evidence\.json/i);
  const substituted = storedZip([['evidence.json', Buffer.from('{}\n')]]);
  assert.throws(() => validatePrivacyArtifactZip({
    zipBytes: substituted,
    evidenceBytes: evidence,
    expectedZipSha256: sha256(substituted),
  }), /differs from the validated evidence bytes/i);
});

test('CLI creates and revalidates only canonical evidence.json bytes', () => {
  const temporary = mkdtempSync(join(tmpdir(), 'privacy-approval-cli-'));
  const candidatePath = join(temporary, 'candidate-spec.json');
  const approvalPath = join(temporary, 'approval.json');
  const packageRoot = join(temporary, 'package');
  const bytes = candidateBytes();
  const approval = validateProtectedApprovalFacts(approvalFacts());
  writeFileSync(candidatePath, bytes);
  writeFileSync(approvalPath, `${JSON.stringify(approval, null, 2)}\n`);
  const common = [
    `--candidate=${candidatePath}`,
    `--approval=${approvalPath}`,
    `--package-root=${packageRoot}`,
    `--release-id=${releaseId}`,
    `--candidate-spec-sha256=${sha256(bytes)}`,
    `--approval-source-sha=${sourceSha}`,
    '--producer-run-id=701',
    '--producer-run-attempt=1',
  ];
  try {
    for (const command of ['create-evidence', 'validate-evidence']) {
      const result = spawnSync(
        process.execPath,
        [join(root, 'tools', 'mission_spine_privacy_approval.mjs'), command, ...common],
        { cwd: root, encoding: 'utf8', windowsHide: true },
      );
      assert.equal(result.status, 0, result.stderr);
    }
    assert.deepEqual(readdirSync(packageRoot), ['evidence.json']);
    const evidence = readFileSync(join(packageRoot, 'evidence.json'));
    assert.equal(evidence.at(-1), 0x0a);
    assert.equal(JSON.stringify(JSON.parse(evidence), null, 2) + '\n', evidence.toString());
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
});

test('workflow is dispatch-only, pinned, protected, and has no deploy or write authority', () => {
  const workflow = readFileSync(
    join(root, '.github', 'workflows', 'mission-spine-privacy-approval.yml'),
    'utf8',
  );
  const dispatch = workflow.match(/\non:\n([\s\S]*?)\npermissions:/)?.[1];
  assert.ok(dispatch);
  assert.deepEqual(dispatch.match(/^  [A-Za-z_][A-Za-z0-9_-]*:/gm), [
    '  workflow_dispatch:',
  ]);
  for (const input of ['release_id', 'candidate_spec_sha256', 'approval_source_sha']) {
    assert.match(dispatch, new RegExp(
      `      ${input}:\\n        description: [^\\n]+\\n        required: true\\n        type: string(?:\\n|$)`,
    ));
  }
  assert.equal(dispatch.match(/^      [A-Za-z_][A-Za-z0-9_-]*:/gm)?.length, 3);
  assert.doesNotMatch(dispatch, /\n\s+(?:default|options):/);
  assert.match(workflow, /name: Approve analytics privacy release/);
  assert.match(workflow, /environment: mission-spine-privacy-approval/);
  assert.match(workflow, /test "\$\{GITHUB_RUN_ATTEMPT\}" = 1/);
  assert.match(workflow, /test "\$\{GITHUB_REF\}" = refs\/heads\/main/);
  assert.match(workflow, /node-version: '24\.12\.0'/);
  assert.match(workflow, /\$\{\{ inputs\.release_id \}\}-privacy-approval-run-\$\{\{ github\.run_id \}\}-attempt-\$\{\{ github\.run_attempt \}\}/);
  assert.match(workflow, /path: \$\{\{ runner\.temp \}\}\/mission-spine-privacy-approval\/package\/evidence\.json/);
  assert.match(workflow, /overwrite: false/);
  assert.match(workflow, /actions\/checkout@d23441a48e516b6c34aea4fa41551a30e30af803\s+# v6\.1\.0/);
  assert.match(workflow, /actions\/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020\s+# v4\.4\.0/);
  assert.match(workflow, /actions\/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1\s+# v3\.2\.0/);
  assert.match(workflow, /actions\/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02\s+# v4\.6\.2/);
  assert.deepEqual(
    [...workflow.matchAll(/secrets\.([A-Z0-9_]+)/g)].map((match) => match[1]).sort(),
    ['GITOPS_APP_ID', 'GITOPS_APP_PRIVATE_KEY'],
  );
  assert.match(workflow, /permission-actions: read/);
  assert.match(workflow, /permission-contents: read/);
  assert.match(workflow, /permission-members: read/);
  assert.match(workflow, /repositories: \|\n            documents\n            devpath-gitops/);
  assert.doesNotMatch(workflow, /(?:git\s+push|kubectl|wrangler|deploy\b)/i);
  assert.match(workflow, /permissions:\n  actions: read\n  contents: read/);

  const uses = [...workflow.matchAll(/^\s*(?:-\s+)?uses: ([^@\s]+)@([^\s#]+)(?:\s+#\s*(\S+))?\s*$/gm)];
  assert.ok(uses.length > 0);
  for (const use of uses) {
    assert.match(use[2], /^[0-9a-f]{40}$/);
    assert.match(use[3], /^v\d+(?:\.\d+){0,2}$/);
  }
});
