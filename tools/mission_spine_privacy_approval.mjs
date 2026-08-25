import { createHash } from 'node:crypto';
import {
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  realpathSync,
  writeFileSync,
} from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import process from 'node:process';
import { pathToFileURL } from 'node:url';
import { inflateRawSync } from 'node:zlib';

export const documentsRepository = 'DevPathAi/documents';
export const documentsBranch = 'main';
export const privacyWorkflow = '.github/workflows/mission-spine-privacy-approval.yml';
export const privacyEnvironment = 'mission-spine-privacy-approval';
export const privacyJob = 'Approve analytics privacy release';
export const gitopsRepository = 'DevPathAi/devpath-gitops';
export const candidateWorkflow = '.github/workflows/mission-spine-candidate.yml';

const MIB = 1024 * 1024;
const MAX_API_BYTES = MIB;
const MAX_CANDIDATE_BYTES = 256 * 1024;
const MAX_EVIDENCE_BYTES = 64 * 1024;
const MAX_ZIP_BYTES = MIB;
const SHA40 = /^(?!0{40}$)[0-9a-f]{40}$/;
const WEB_BASE_TAG = /^([0-9a-f]{40})(?:-mission-(?:off|on))?$/;
const SHA64 = /^(?!0{64}$)[0-9a-f]{64}$/;
const SAFE_RELEASE_ID = /^ms-[0-9]{8}-[a-z0-9][a-z0-9-]{2,40}$/;
const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9_.:/-]{1,127}$/;
const SAFE_LOGIN = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$/;
const SAFE_ARTIFACT_NAME = /^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$/;
const PRIVACY_KEYS = [
  'collection_mode',
  'approval_source_sha',
  'region',
  'project_identity',
  'retention_days',
  'access_owner',
  'deletion_runbook',
];
const GITOPS_KEYS = [
  'repository',
  'base_sha',
  'base_web_tag',
  'base_web_digest',
  'web_kustomization',
];
const APPROVAL_KEYS = [
  'approval_environment',
  'approval_environment_id',
  'approval_job_name',
  'approved_by',
  'approved_by_id',
  'approval_effective_at',
];
const EVIDENCE_KEYS = [
  'candidate_spec_sha256',
  'status',
  'producer_run_id',
  'producer_run_attempt',
  'approved_at',
  'collection_mode',
  'region',
  'project_identity',
  'retention_days',
  'access_owner',
  'deletion_runbook',
  ...APPROVAL_KEYS,
];

function fail(message) {
  throw new Error(`Mission Spine privacy approval failed: ${message}`);
}

function compareAscii(left, right) {
  return left < right ? -1 : left > right ? 1 : 0;
}

function exact(actual, expected, name) {
  if (actual !== expected) fail(`${name} mismatch`);
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function sha40(value, name) {
  if (typeof value !== 'string' || !SHA40.test(value)) {
    fail(`${name} must be a nonzero lowercase Git SHA`);
  }
  return value;
}

function webBaseTag(value, name) {
  const match = typeof value === 'string' ? WEB_BASE_TAG.exec(value) : null;
  if (match === null || /^0{40}$/.test(match[1])) {
    fail(`${name} must be a nonzero lowercase Git SHA with an optional mission phase`);
  }
  return value;
}

function sha64(value, name) {
  if (typeof value !== 'string' || !SHA64.test(value)) {
    fail(`${name} must be a nonzero lowercase SHA-256 digest`);
  }
  return value;
}

function positiveInteger(value, name) {
  if (!Number.isSafeInteger(value) || value < 1) {
    fail(`${name} must be a positive integer`);
  }
  return value;
}

function safeReleaseId(value) {
  if (typeof value !== 'string' || !SAFE_RELEASE_ID.test(value)) {
    fail('release_id is not a safe identifier');
  }
  return value;
}

function safeId(value, name) {
  if (typeof value !== 'string' || !SAFE_ID.test(value)) {
    fail(`${name} is not a safe identifier`);
  }
  return value;
}

function utc(value, name) {
  if (
    typeof value !== 'string' ||
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(value) ||
    !Number.isFinite(Date.parse(value))
  ) {
    fail(`${name} must be an exact UTC timestamp ending in Z`);
  }
  return Date.parse(value);
}

function exactKeys(value, expected, name, ordered = false) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    fail(`${name} must be an object`);
  }
  const actual = Object.keys(value);
  const matches = ordered
    ? actual.length === expected.length && actual.every((entry, index) => entry === expected[index])
    : actual.length === expected.length &&
      [...actual].sort(compareAscii).every(
        (entry, index) => entry === [...expected].sort(compareAscii)[index],
      );
  if (!matches) fail(`${name} exact${ordered ? ' ordered' : ''} key set mismatch`);
}

function regularFile(path, name, maximumBytes) {
  let info;
  try {
    info = lstatSync(path);
  } catch (error) {
    fail(`${name} is absent: ${error.message}`);
  }
  if (!info.isFile() || info.isSymbolicLink()) {
    fail(`${name} must be one regular non-link file`);
  }
  if (info.size < 1 || info.size > maximumBytes) {
    fail(`${name} byte size is invalid`);
  }
  return info;
}

function regularDirectory(path, name) {
  let info;
  try {
    info = lstatSync(path);
  } catch (error) {
    fail(`${name} is absent: ${error.message}`);
  }
  if (!info.isDirectory() || info.isSymbolicLink() || realpathSync(path) !== resolve(path)) {
    fail(`${name} must be one exact regular non-link directory`);
  }
  return info;
}

function decodeUtf8(bytes, name) {
  if (
    bytes.length >= 3 &&
    bytes[0] === 0xef &&
    bytes[1] === 0xbb &&
    bytes[2] === 0xbf
  ) {
    fail(`${name} must be UTF-8 without BOM`);
  }
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  } catch (error) {
    fail(`${name} must be strict UTF-8: ${error.message}`);
  }
}

export function parseStrictJsonBytes(input, name = 'JSON', maximumBytes = MAX_CANDIDATE_BYTES) {
  const bytes = Buffer.from(input);
  if (bytes.length < 2 || bytes.length > maximumBytes) {
    fail(`${name} byte size is invalid`);
  }
  const text = decodeUtf8(bytes, name);
  let index = 0;

  function whitespace() {
    while (index < text.length && /[\u0020\u000a\u000d\u0009]/.test(text[index])) index += 1;
  }

  function string() {
    if (text[index] !== '"') fail(`${name} contains malformed JSON string`);
    const start = index;
    index += 1;
    while (index < text.length) {
      const code = text.charCodeAt(index);
      if (code === 0x22) {
        index += 1;
        try {
          return JSON.parse(text.slice(start, index));
        } catch (error) {
          fail(`${name} contains invalid JSON string: ${error.message}`);
        }
      }
      if (code < 0x20) fail(`${name} contains a control character in a JSON string`);
      if (code === 0x5c) {
        index += 1;
        if (index >= text.length || !/["\\/bfnrtu]/.test(text[index])) {
          fail(`${name} contains an invalid JSON escape`);
        }
        if (text[index] === 'u') {
          if (!/^[0-9a-fA-F]{4}$/.test(text.slice(index + 1, index + 5))) {
            fail(`${name} contains an invalid Unicode escape`);
          }
          index += 4;
        }
      }
      index += 1;
    }
    fail(`${name} contains an unterminated JSON string`);
  }

  function value() {
    whitespace();
    if (text[index] === '"') return string();
    if (text[index] === '{') return object();
    if (text[index] === '[') return array();
    for (const [literal, result] of [['true', true], ['false', false], ['null', null]]) {
      if (text.startsWith(literal, index)) {
        index += literal.length;
        return result;
      }
    }
    const match = text.slice(index).match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/);
    if (!match) fail(`${name} contains an invalid JSON value`);
    index += match[0].length;
    const result = Number(match[0]);
    if (!Number.isFinite(result)) fail(`${name} contains a non-finite number`);
    return result;
  }

  function array() {
    index += 1;
    whitespace();
    const result = [];
    if (text[index] === ']') {
      index += 1;
      return result;
    }
    while (true) {
      result.push(value());
      whitespace();
      if (text[index] === ']') {
        index += 1;
        return result;
      }
      if (text[index] !== ',') fail(`${name} contains malformed JSON array`);
      index += 1;
    }
  }

  function object() {
    index += 1;
    whitespace();
    const result = {};
    const seen = new Set();
    if (text[index] === '}') {
      index += 1;
      return result;
    }
    while (true) {
      whitespace();
      const key = string();
      if (seen.has(key)) fail(`${name} contains duplicate JSON key ${JSON.stringify(key)}`);
      seen.add(key);
      whitespace();
      if (text[index] !== ':') fail(`${name} contains malformed JSON object`);
      index += 1;
      Object.defineProperty(result, key, {
        value: value(),
        enumerable: true,
        configurable: true,
        writable: true,
      });
      whitespace();
      if (text[index] === '}') {
        index += 1;
        return result;
      }
      if (text[index] !== ',') fail(`${name} contains malformed JSON object`);
      index += 1;
    }
  }

  const result = value();
  whitespace();
  if (index !== text.length) fail(`${name} has trailing non-whitespace bytes`);
  return result;
}

function parseJsonFile(path, name, maximumBytes) {
  regularFile(path, name, maximumBytes);
  const bytes = readFileSync(path);
  return { bytes, value: parseStrictJsonBytes(bytes, name, maximumBytes) };
}

function validatePrivacy(value, approvalSourceSha) {
  exactKeys(value, PRIVACY_KEYS, 'candidate analytics_privacy');
  if (!['explicit-consent', 'approved-cookieless'].includes(value.collection_mode)) {
    fail('candidate analytics_privacy.collection_mode is not approved');
  }
  exact(value.approval_source_sha, approvalSourceSha, 'candidate approval_source_sha');
  sha40(value.approval_source_sha, 'candidate approval_source_sha');
  exact(value.region, 'EU', 'candidate analytics_privacy.region');
  safeId(value.project_identity, 'candidate analytics_privacy.project_identity');
  if (!Number.isSafeInteger(value.retention_days) || value.retention_days < 1 || value.retention_days > 365) {
    fail('candidate analytics_privacy.retention_days must be an integer from 1 through 365');
  }
  safeId(value.access_owner, 'candidate analytics_privacy.access_owner');
  safeId(value.deletion_runbook, 'candidate analytics_privacy.deletion_runbook');
  return value;
}

function parseCandidateContract({
  candidateBytes,
  releaseId,
  candidateSpecSha256,
  approvalSourceSha,
}) {
  const bytes = Buffer.from(candidateBytes);
  safeReleaseId(releaseId);
  sha64(candidateSpecSha256, 'candidate_spec_sha256');
  sha40(approvalSourceSha, 'approval_source_sha');
  exact(sha256(bytes), candidateSpecSha256, 'raw candidate SHA-256');
  const candidate = parseStrictJsonBytes(bytes, 'candidate-spec.json', MAX_CANDIDATE_BYTES);
  if (candidate === null || typeof candidate !== 'object' || Array.isArray(candidate)) {
    fail('candidate-spec.json root must be an object');
  }
  if (typeof candidate.$schema !== 'string' || candidate.$schema.length < 1 || candidate.$schema.length > 256) {
    fail('candidate $schema is invalid');
  }
  exact(candidate.schema_version, 1, 'candidate schema_version');
  exact(candidate.document_type, 'candidate-spec', 'candidate document_type');
  exact(candidate.release_id, releaseId, 'candidate release_id');
  exactKeys(candidate.gitops, GITOPS_KEYS, 'candidate gitops');
  exact(candidate.gitops.repository, gitopsRepository, 'candidate gitops.repository');
  sha40(candidate.gitops.base_sha, 'candidate gitops.base_sha');
  webBaseTag(candidate.gitops.base_web_tag, 'candidate gitops.base_web_tag');
  if (
    typeof candidate.gitops.base_web_digest !== 'string' ||
    !/^sha256:[0-9a-f]{64}$/.test(candidate.gitops.base_web_digest)
  ) {
    fail('candidate gitops.base_web_digest is invalid');
  }
  safeId(candidate.gitops.web_kustomization, 'candidate gitops.web_kustomization');
  const privacy = validatePrivacy(candidate.analytics_privacy, approvalSourceSha);
  return { candidate, privacy, baseSha: candidate.gitops.base_sha };
}

export function validateCandidateBinding({
  candidateBytes,
  releaseId,
  candidateSpecSha256,
  approvalSourceSha,
}) {
  return parseCandidateContract({
    candidateBytes,
    releaseId,
    candidateSpecSha256,
    approvalSourceSha,
  }).privacy;
}

export function validateCandidateWorkflowDispatch(input) {
  const bytes = Buffer.from(input);
  const text = decodeUtf8(bytes, 'candidate producer workflow');
  if (text.includes('\r') || text.includes('\t')) {
    fail('candidate producer workflow must use canonical LF indentation');
  }
  const lines = text.split('\n');
  const onIndexes = lines
    .map((line, index) => line === 'on:' ? index : -1)
    .filter((index) => index >= 0);
  if (onIndexes.length !== 1) fail('candidate workflow must have exactly one canonical top-level on');
  const onIndex = onIndexes[0];
  const permissionsIndex = lines.indexOf('permissions:', onIndex + 1);
  if (permissionsIndex < 0) fail('candidate workflow permissions boundary is absent');
  const section = lines.slice(onIndex + 1, permissionsIndex);
  while (section.at(-1) === '') section.pop();
  if (section[0] !== '  workflow_dispatch:' || section[1] !== '    inputs:') {
    fail('candidate workflow must directly contain only workflow_dispatch inputs');
  }
  let index = 2;
  const inputs = [];
  while (index < section.length) {
    const input = section[index]?.match(/^      ([A-Za-z_][A-Za-z0-9_-]*):$/)?.[1];
    if (!input) fail('candidate workflow has a noncanonical dispatch child');
    index += 1;
    const properties = new Map();
    while (index < section.length && section[index].startsWith('        ')) {
      const property = section[index].match(/^        ([a-z_]+):(?: (.*))?$/);
      if (!property || properties.has(property[1])) {
        fail('candidate workflow input property is invalid or duplicated');
      }
      if (!['description', 'required', 'type'].includes(property[1])) {
        fail('candidate workflow input property is not allowlisted');
      }
      properties.set(property[1], property[2] ?? '');
      index += 1;
    }
    if (properties.get('required') !== 'true' || properties.get('type') !== 'string') {
      fail('candidate workflow input must be a required string');
    }
    if (properties.has('description') && properties.get('description').length < 1) {
      fail('candidate workflow input description must be nonempty');
    }
    inputs.push(input);
  }
  if (inputs.length !== 1 || inputs[0] !== 'release_id') {
    fail('candidate workflow dispatch input must be exactly release_id');
  }
  return true;
}

function safeBranch(value, releaseId) {
  if (
    typeof value !== 'string' ||
    value.length < 1 ||
    value.length > 255 ||
    !/^[A-Za-z0-9][A-Za-z0-9._/-]*$/.test(value) ||
    value === documentsBranch ||
    value.endsWith('/') ||
    value.endsWith('.') ||
    value.endsWith('.lock') ||
    value.includes('..') ||
    value.includes('//') ||
    value.includes('@{')
  ) {
    fail('candidate run must originate from a safe non-main candidate branch');
  }
  exact(value, `release/candidate-${releaseId}`, 'candidate run head_branch');
  return value;
}

function candidateWorkflowPath(value) {
  exact(value, candidateWorkflow, 'candidate workflow run.path');
}

export function validateCandidateArtifactFacts({
  releaseId,
  candidateSpecSha256,
  approvalSourceSha,
  run,
  artifact,
  zipBytes,
}) {
  safeReleaseId(releaseId);
  sha64(candidateSpecSha256, 'candidate_spec_sha256');
  sha40(approvalSourceSha, 'approval_source_sha');
  const runId = positiveInteger(run?.id, 'candidate run.id');
  const runAttempt = positiveInteger(run?.run_attempt, 'candidate run.run_attempt');
  exact(run.event, 'workflow_dispatch', 'candidate run.event');
  exact(run.status, 'completed', 'candidate run.status');
  exact(run.conclusion, 'success', 'candidate run.conclusion');
  const headSha = sha40(run.head_sha, 'candidate run.head_sha');
  const headBranch = safeBranch(run.head_branch, releaseId);
  candidateWorkflowPath(run.path);
  exact(run.repository?.full_name, gitopsRepository, 'candidate run.repository');
  exact(run.head_repository?.full_name, gitopsRepository, 'candidate run.head_repository');

  positiveInteger(artifact?.id, 'candidate artifact.id');
  exact(
    artifact.name,
    `${releaseId}-candidate-spec-run-${runId}-attempt-${runAttempt}`,
    'candidate artifact.name',
  );
  exact(artifact.expired, false, 'candidate artifact.expired');
  const expiresAt = utc(artifact.expires_at, 'candidate artifact.expires_at');
  if (expiresAt <= Date.now()) fail('candidate artifact has expired');
  positiveInteger(artifact.size_in_bytes, 'candidate artifact.size_in_bytes');
  if (artifact.size_in_bytes > MAX_ZIP_BYTES) fail('candidate artifact ZIP exceeds 1 MiB');
  const digest = normalizedDigest(artifact.digest, 'candidate artifact digest');
  exact(artifact.workflow_run?.id, runId, 'candidate artifact.workflow_run.id');
  exact(artifact.workflow_run?.head_sha, headSha, 'candidate artifact.workflow_run.head_sha');
  const archive = Buffer.from(zipBytes);
  exact(archive.length, artifact.size_in_bytes, 'candidate artifact ZIP size');
  exact(sha256(archive), digest, 'candidate artifact ZIP SHA-256');
  const candidateBytes = singleFileFromZip(
    archive,
    'candidate-spec.json',
    MAX_CANDIDATE_BYTES,
  );
  const parsed = parseCandidateContract({
    candidateBytes,
    releaseId,
    candidateSpecSha256,
    approvalSourceSha,
  });
  return {
    runId,
    runAttempt,
    headSha,
    headBranch,
    artifactId: artifact.id,
    artifactName: artifact.name,
    artifactArchiveSha256: digest,
    candidateBytes,
    baseSha: parsed.baseSha,
    privacy: parsed.privacy,
  };
}

export function validateCandidateSourceFacts({
  releaseId,
  candidateBytes,
  candidateSpecSha256,
  approvalSourceSha,
  headSha,
  repositoryInfo,
  mainBranch,
  headCommit,
  comparison,
  candidateBlobBytes,
  baseWorkflowBytes,
  headWorkflowBytes,
}) {
  const parsed = parseCandidateContract({
    candidateBytes,
    releaseId,
    candidateSpecSha256,
    approvalSourceSha,
  });
  sha40(headSha, 'candidate head SHA');
  exact(repositoryInfo?.full_name, gitopsRepository, 'GitOps repository full_name');
  exact(repositoryInfo?.default_branch, 'main', 'GitOps default branch');
  exact(repositoryInfo?.archived, false, 'GitOps repository archived state');
  exact(mainBranch?.name, 'main', 'GitOps protected branch name');
  exact(mainBranch?.protected, true, 'GitOps protected branch policy');
  exact(mainBranch?.commit?.sha, parsed.baseSha, 'GitOps current protected main SHA');
  exact(headCommit?.sha, headSha, 'candidate head commit SHA');
  if (
    !Array.isArray(headCommit?.parents) ||
    headCommit.parents.length !== 1 ||
    headCommit.parents[0]?.sha !== parsed.baseSha
  ) {
    fail('candidate head must have exactly one parent equal to gitops.base_sha');
  }
  exact(comparison?.status, 'ahead', 'candidate comparison status');
  exact(comparison?.ahead_by, 1, 'candidate comparison ahead_by');
  exact(comparison?.behind_by, 0, 'candidate comparison behind_by');
  exact(comparison?.total_commits, 1, 'candidate comparison total_commits');
  exact(comparison?.merge_base_commit?.sha, parsed.baseSha, 'candidate comparison merge base');
  if (
    !Array.isArray(comparison?.commits) ||
    comparison.commits.length !== 1 ||
    comparison.commits[0]?.sha !== headSha
  ) {
    fail('candidate comparison must contain exactly the candidate head commit');
  }
  const expectedPath = `release-manifests/candidates/${releaseId}.candidate-spec.json`;
  if (
    !Array.isArray(comparison?.files) ||
    comparison.files.length !== 1 ||
    comparison.files[0]?.filename !== expectedPath ||
    comparison.files[0]?.status !== 'added' ||
    comparison.files[0]?.previous_filename !== undefined
  ) {
    fail('candidate commit must add only the exact canonical candidate path');
  }
  if (!Buffer.from(candidateBlobBytes).equals(Buffer.from(candidateBytes))) {
    fail('candidate artifact bytes differ from the candidate source blob');
  }
  if (
    !Buffer.isBuffer(baseWorkflowBytes) ||
    baseWorkflowBytes.length < 1 ||
    !Buffer.isBuffer(headWorkflowBytes) ||
    !baseWorkflowBytes.equals(headWorkflowBytes)
  ) {
    fail('candidate producer workflow differs from protected main');
  }
  validateCandidateWorkflowDispatch(headWorkflowBytes);
  return true;
}

export function selectUniqueCandidateMatch(matches) {
  if (!Array.isArray(matches) || matches.length !== 1) {
    fail('candidate discovery must find exactly one eligible current successful run');
  }
  positiveInteger(matches[0]?.runId, 'selected candidate run ID');
  return matches[0];
}

function workflowPath(value) {
  exact(value, privacyWorkflow, 'workflow run path');
}

function actorIdentity(value, name) {
  if (value === null || typeof value !== 'object') fail(`${name} is absent`);
  const id = positiveInteger(value.id, `${name}.id`);
  if (!['User', 'Bot'].includes(value.type)) fail(`${name}.type is invalid`);
  const loginIsValid =
    typeof value.login === 'string' &&
    (value.type === 'User'
      ? SAFE_LOGIN.test(value.login)
      : /^[A-Za-z0-9][A-Za-z0-9-]{0,99}\[bot\]$/.test(value.login));
  if (!loginIsValid) fail(`${name}.login is invalid`);
  return { id, login: value.login };
}

export function validateProtectedApprovalFacts(facts) {
  exact(facts.repository, documentsRepository, 'repository');
  exact(facts.workflowPath, privacyWorkflow, 'workflow path');
  exact(facts.environmentName, privacyEnvironment, 'environment binding');
  exact(facts.jobName, privacyJob, 'job binding');
  sha40(facts.sourceSha, 'source SHA');
  positiveInteger(facts.runId, 'run ID');
  if (facts.runAttempt !== 1) {
    fail('protected approvals require attempt 1 and a fresh workflow_dispatch');
  }

  exact(facts.repositoryInfo?.full_name, documentsRepository, 'repository metadata full_name');
  exact(facts.repositoryInfo?.default_branch, documentsBranch, 'repository default branch');
  exact(facts.repositoryInfo?.archived, false, 'repository archived state');
  exact(facts.run?.id, facts.runId, 'run.id');
  exact(facts.run?.run_attempt, 1, 'run.run_attempt');
  exact(facts.run?.event, 'workflow_dispatch', 'run.event');
  exact(facts.run?.status, 'in_progress', 'run.status');
  exact(facts.run?.conclusion, null, 'run.conclusion');
  exact(facts.run?.head_sha, facts.sourceSha, 'run.head_sha');
  exact(facts.run?.head_branch, documentsBranch, 'run.head_branch');
  exact(facts.run?.repository?.full_name, documentsRepository, 'run.repository');
  exact(facts.run?.head_repository?.full_name, documentsRepository, 'run.head_repository');
  workflowPath(facts.run?.path);
  actorIdentity(facts.run?.actor, 'run.actor');
  actorIdentity(facts.run?.triggering_actor, 'run.triggering_actor');

  exact(facts.branch?.name, documentsBranch, 'protected branch name');
  exact(facts.branch?.commit?.sha, facts.sourceSha, 'protected branch current SHA');
  exact(facts.branch?.protected, true, 'protected branch policy');

  exact(facts.environment?.name, privacyEnvironment, 'environment.name');
  const environmentId = positiveInteger(facts.environment?.id, 'environment.id');
  if (!Array.isArray(facts.environment?.protection_rules)) {
    fail('environment protection rules are absent');
  }
  const reviewerRules = facts.environment.protection_rules.filter(
    (rule) => rule?.type === 'required_reviewers',
  );
  if (reviewerRules.length !== 1) fail('required reviewer rule is absent or ambiguous');
  const reviewerRule = reviewerRules[0];
  exact(reviewerRule.prevent_self_review, true, 'environment prevent_self_review');
  if (!Array.isArray(reviewerRule.reviewers) || reviewerRule.reviewers.length < 1) {
    fail('environment has no configured reviewer');
  }
  const configuredUsers = [];
  const configuredTeams = [];
  const reviewerIdentities = new Set();
  for (const entry of reviewerRule.reviewers) {
    if (entry?.type === 'User') {
      const id = positiveInteger(entry.reviewer?.id, 'configured reviewer user id');
      const key = `User:${id}`;
      if (reviewerIdentities.has(key)) fail('configured reviewer identity is duplicated');
      reviewerIdentities.add(key);
      configuredUsers.push(id);
      continue;
    }
    if (entry?.type !== 'Team') fail('configured reviewer type is unsupported');
    const id = positiveInteger(entry.reviewer?.id, 'configured reviewer team id');
    const slug = entry.reviewer?.slug;
    if (typeof slug !== 'string' || !/^[a-z0-9](?:[a-z0-9-]{0,99})$/.test(slug)) {
      fail('configured reviewer team slug is invalid');
    }
    const key = `Team:${id}`;
    if (reviewerIdentities.has(key)) fail('configured reviewer identity is duplicated');
    reviewerIdentities.add(key);
    configuredTeams.push({ id, slug });
  }

  if (!Array.isArray(facts.approvals)) fail('approval history is absent');
  const reviews = facts.approvals.filter(
    (review) =>
      review?.state === 'approved' &&
      Array.isArray(review.environments) &&
      review.environments.filter(
        (entry) => entry?.id === environmentId && entry?.name === privacyEnvironment,
      ).length === 1,
  );
  if (reviews.length !== 1) fail('exact environment approval is absent or ambiguous');
  const reviewer = actorIdentity(reviews[0].user, 'approved reviewer');
  exact(reviews[0].user.type, 'User', 'approved reviewer type');
  const configuredUser = configuredUsers.includes(reviewer.id);
  const memberships = facts.teamMemberships;
  if (!Array.isArray(memberships)) {
    fail('configured team membership facts are absent or ambiguous');
  }
  if (configuredUser && memberships.length !== 0) {
    fail('direct configured user approval must not depend on team membership facts');
  }
  if (!configuredUser && memberships.length !== configuredTeams.length) {
    fail('configured team membership facts are absent or ambiguous');
  }
  const membershipKeys = new Set();
  let activeTeamMemberships = 0;
  for (const membership of memberships) {
    const teamId = positiveInteger(membership?.team_id, 'team membership team_id');
    const team = configuredTeams.find(
      (entry) => entry.id === teamId && entry.slug === membership?.team_slug,
    );
    if (!team) fail('team membership does not bind a configured reviewer team');
    if (membershipKeys.has(teamId)) fail('team membership fact is duplicated');
    membershipKeys.add(teamId);
    exact(membership.organization, 'DevPathAi', 'team membership organization');
    exact(membership.user_login, reviewer.login, 'team membership user');
    if (membership.state === 'active') {
      if (!['member', 'maintainer'].includes(membership.role)) {
        fail('active team membership role is invalid');
      }
      activeTeamMemberships += 1;
    } else if (membership.state !== 'absent' || membership.role !== null) {
      fail('inactive team membership fact is invalid');
    }
  }
  if (!configuredUser && activeTeamMemberships < 1) {
    fail('approved reviewer is not represented by the configured gate');
  }

  if (!facts.jobs || !Array.isArray(facts.jobs.jobs)) fail('attempt job list is absent');
  const jobs = facts.jobs.jobs.filter((job) => job?.name === privacyJob);
  if (jobs.length !== 1) fail('protected approval job identity is absent or ambiguous');
  const job = jobs[0];
  exact(job.run_id, facts.runId, 'approval job run_id');
  exact(job.head_sha, facts.sourceSha, 'approval job head_sha');
  exact(job.status, 'in_progress', 'approval job status');
  exact(job.conclusion, null, 'approval job conclusion');
  const createdAt = utc(facts.run.created_at, 'run.created_at');
  const effectiveAt = utc(job.started_at, 'approval job started_at');
  if (effectiveAt < createdAt || effectiveAt > Date.now()) {
    fail('approval effective time is outside the protected run interval');
  }

  if (!Buffer.isBuffer(facts.workflowBytes) || facts.workflowBytes.length < 1) {
    fail('workflow raw bytes are absent');
  }
  if (
    !Buffer.isBuffer(facts.localWorkflowBytes) ||
    !facts.workflowBytes.equals(facts.localWorkflowBytes)
  ) {
    fail('workflow source differs from exact checked-out bytes');
  }

  return {
    approval_environment: privacyEnvironment,
    approval_environment_id: environmentId,
    approval_job_name: privacyJob,
    approved_by: reviewer.login,
    approved_by_id: reviewer.id,
    approval_effective_at: job.started_at,
  };
}

function validateApprovalClaim(value) {
  exactKeys(value, APPROVAL_KEYS, 'protected approval', true);
  exact(value.approval_environment, privacyEnvironment, 'approval_environment');
  positiveInteger(value.approval_environment_id, 'approval_environment_id');
  exact(value.approval_job_name, privacyJob, 'approval_job_name');
  if (typeof value.approved_by !== 'string' || !SAFE_LOGIN.test(value.approved_by)) {
    fail('approved_by is invalid');
  }
  positiveInteger(value.approved_by_id, 'approved_by_id');
  utc(value.approval_effective_at, 'approval_effective_at');
  return value;
}

export function createPrivacyEvidence({
  candidateSpecSha256,
  producerRunId,
  producerRunAttempt,
  privacy,
  approval,
}) {
  sha64(candidateSpecSha256, 'candidate_spec_sha256');
  positiveInteger(producerRunId, 'producer_run_id');
  if (producerRunAttempt !== 1) {
    fail('protected approvals require attempt 1 and a fresh workflow_dispatch');
  }
  validatePrivacy(privacy, privacy?.approval_source_sha);
  validateApprovalClaim(approval);
  return {
    candidate_spec_sha256: candidateSpecSha256,
    status: 'passed',
    producer_run_id: producerRunId,
    producer_run_attempt: 1,
    approved_at: approval.approval_effective_at,
    collection_mode: privacy.collection_mode,
    region: privacy.region,
    project_identity: privacy.project_identity,
    retention_days: privacy.retention_days,
    access_owner: privacy.access_owner,
    deletion_runbook: privacy.deletion_runbook,
    approval_environment: approval.approval_environment,
    approval_environment_id: approval.approval_environment_id,
    approval_job_name: approval.approval_job_name,
    approved_by: approval.approved_by,
    approved_by_id: approval.approved_by_id,
    approval_effective_at: approval.approval_effective_at,
  };
}

export function validatePrivacyEvidence(value, expected) {
  exactKeys(value, EVIDENCE_KEYS, 'privacy evidence', true);
  const canonical = createPrivacyEvidence(expected);
  for (const key of EVIDENCE_KEYS) exact(value[key], canonical[key], `evidence.${key}`);
  exact(value.approved_at, value.approval_effective_at, 'evidence approved_at');
  return true;
}

function validatePackageRoot(packageRoot) {
  regularDirectory(packageRoot, 'privacy evidence package root');
  const entries = readdirSync(packageRoot, { withFileTypes: true });
  if (
    entries.length !== 1 ||
    entries[0].name !== 'evidence.json' ||
    !entries[0].isFile() ||
    entries[0].isSymbolicLink()
  ) {
    fail('package must contain exactly one regular evidence.json file');
  }
}

function evidenceInputs({
  candidatePath,
  approvalPath,
  releaseId,
  candidateSpecSha256,
  approvalSourceSha,
  producerRunId,
  producerRunAttempt,
}) {
  const candidate = parseJsonFile(candidatePath, 'candidate-spec.json', MAX_CANDIDATE_BYTES);
  const privacy = validateCandidateBinding({
    candidateBytes: candidate.bytes,
    releaseId,
    candidateSpecSha256,
    approvalSourceSha,
  });
  const approval = parseJsonFile(approvalPath, 'protected approval', MAX_EVIDENCE_BYTES).value;
  validateApprovalClaim(approval);
  return {
    candidateSpecSha256,
    producerRunId,
    producerRunAttempt,
    privacy,
    approval,
  };
}

function createEvidencePackage(options) {
  const expected = evidenceInputs(options);
  const parent = dirname(resolve(options.packageRoot));
  regularDirectory(parent, 'privacy evidence package parent');
  try {
    lstatSync(options.packageRoot);
    fail('privacy evidence package output already exists');
  } catch (error) {
    if (!error || error.code !== 'ENOENT') throw error;
  }
  mkdirSync(options.packageRoot, { recursive: false, mode: 0o755 });
  const evidence = createPrivacyEvidence(expected);
  writeFileSync(join(options.packageRoot, 'evidence.json'), `${JSON.stringify(evidence, null, 2)}\n`, {
    encoding: 'utf8',
    flag: 'wx',
    mode: 0o644,
  });
  validateEvidencePackage({ ...options, expected });
  return evidence;
}

function validateEvidencePackage(options) {
  validatePackageRoot(options.packageRoot);
  const expected = options.expected ?? evidenceInputs(options);
  const evidence = parseJsonFile(
    join(options.packageRoot, 'evidence.json'),
    'evidence.json',
    MAX_EVIDENCE_BYTES,
  );
  validatePrivacyEvidence(evidence.value, expected);
  const canonical = Buffer.from(`${JSON.stringify(evidence.value, null, 2)}\n`);
  if (!evidence.bytes.equals(canonical)) fail('evidence.json bytes are not canonical');
  return evidence.bytes;
}

export function artifactName(releaseId, runId, runAttempt) {
  safeReleaseId(releaseId);
  positiveInteger(runId, 'run ID');
  if (runAttempt !== 1) fail('privacy artifact requires attempt 1');
  const value = `${releaseId}-privacy-approval-run-${runId}-attempt-1`;
  if (!SAFE_ARTIFACT_NAME.test(value)) fail('privacy artifact name is unsafe');
  return value;
}

function normalizedDigest(value, name) {
  if (typeof value !== 'string') fail(`${name} is absent`);
  return sha64(value.startsWith('sha256:') ? value.slice(7) : value, name);
}

export function validatePrivacyArtifactMetadata({
  metadata,
  artifactId,
  artifactName: expectedName,
  artifactDigest,
  runId,
  sourceSha,
}) {
  positiveInteger(artifactId, 'artifact ID');
  positiveInteger(runId, 'run ID');
  sha40(sourceSha, 'source SHA');
  if (typeof expectedName !== 'string' || !SAFE_ARTIFACT_NAME.test(expectedName)) {
    fail('artifact name is unsafe');
  }
  const digest = normalizedDigest(artifactDigest, 'artifact digest');
  exact(metadata?.id, artifactId, 'artifact metadata.id');
  exact(metadata?.name, expectedName, 'artifact metadata.name');
  exact(metadata?.expired, false, 'artifact metadata.expired');
  positiveInteger(metadata?.size_in_bytes, 'artifact metadata.size_in_bytes');
  if (metadata.size_in_bytes > MAX_ZIP_BYTES) fail('artifact ZIP exceeds 1 MiB');
  exact(metadata?.digest, `sha256:${digest}`, 'artifact metadata.digest');
  exact(metadata?.workflow_run?.id, runId, 'artifact metadata.workflow_run.id');
  exact(metadata?.workflow_run?.head_sha, sourceSha, 'artifact metadata.workflow_run.head_sha');
  return true;
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

function zipName(bytes, expectedName) {
  let value;
  try {
    value = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  } catch (error) {
    fail(`ZIP entry name is not UTF-8: ${error.message}`);
  }
  if (
    value !== expectedName ||
    value.includes('/') ||
    value.includes('\\') ||
    value.includes('\0')
  ) {
    fail(`unsafe or non-root artifact ZIP entry: ${JSON.stringify(value)}`);
  }
  return value;
}

function endOfCentralDirectory(bytes) {
  const minimum = Math.max(0, bytes.length - (65_535 + 22));
  for (let offset = bytes.length - 22; offset >= minimum; offset -= 1) {
    if (bytes.readUInt32LE(offset) === 0x06054b50) return offset;
  }
  fail('artifact ZIP end-of-central-directory is absent');
}

function inflate(method, compressed, maximumBytes, name) {
  if (method === 0) return Buffer.from(compressed);
  if (method !== 8) fail('artifact ZIP compression method is unsupported');
  try {
    return inflateRawSync(compressed, { maxOutputLength: maximumBytes });
  } catch (error) {
    fail(`artifact ZIP ${name} cannot be safely inflated: ${error.message}`);
  }
}

function singleFileFromZip(zipBytes, expectedName, maximumBytes) {
  const bytes = Buffer.from(zipBytes);
  if (bytes.length < 100 || bytes.length > MAX_ZIP_BYTES) {
    fail('artifact ZIP byte length is invalid');
  }
  const endOffset = endOfCentralDirectory(bytes);
  if (endOffset + 22 !== bytes.length || bytes.readUInt16LE(endOffset + 20) !== 0) {
    fail('artifact ZIP must have no comment or trailing bytes');
  }
  if (bytes.readUInt16LE(endOffset + 4) !== 0 || bytes.readUInt16LE(endOffset + 6) !== 0) {
    fail('artifact ZIP must be single-disk');
  }
  const diskEntries = bytes.readUInt16LE(endOffset + 8);
  const totalEntries = bytes.readUInt16LE(endOffset + 10);
  if (diskEntries !== 1 || totalEntries !== 1) {
    fail(`artifact ZIP must contain exactly one ${expectedName} entry`);
  }
  const centralSize = bytes.readUInt32LE(endOffset + 12);
  const centralOffset = bytes.readUInt32LE(endOffset + 16);
  if (centralOffset + centralSize !== endOffset) fail('artifact ZIP central bounds mismatch');
  const cursor = centralOffset;
  if (cursor + 46 > endOffset || bytes.readUInt32LE(cursor) !== 0x02014b50) {
    fail('artifact ZIP central entry is malformed');
  }
  const madeBy = bytes.readUInt16LE(cursor + 4);
  const flags = bytes.readUInt16LE(cursor + 8);
  const method = bytes.readUInt16LE(cursor + 10);
  const checksum = bytes.readUInt32LE(cursor + 16);
  const compressedSize = bytes.readUInt32LE(cursor + 20);
  const uncompressedSize = bytes.readUInt32LE(cursor + 24);
  const nameLength = bytes.readUInt16LE(cursor + 28);
  const extraLength = bytes.readUInt16LE(cursor + 30);
  const commentLength = bytes.readUInt16LE(cursor + 32);
  const diskStart = bytes.readUInt16LE(cursor + 34);
  const externalAttributes = bytes.readUInt32LE(cursor + 38);
  const localOffset = bytes.readUInt32LE(cursor + 42);
  const centralEnd = cursor + 46 + nameLength + extraLength + commentLength;
  if (centralEnd !== endOffset) fail('artifact ZIP central entry bounds mismatch');
  const name = zipName(
    bytes.subarray(cursor + 46, cursor + 46 + nameLength),
    expectedName,
  );
  if (
    flags & ~0x0808 ||
    flags & 0x0001 ||
    ![0, 8].includes(method) ||
    diskStart !== 0 ||
    extraLength !== 0 ||
    commentLength !== 0 ||
    [compressedSize, uncompressedSize, localOffset].includes(0xffffffff)
  ) {
    fail('artifact ZIP entry metadata is unsafe or noncanonical');
  }
  const host = madeBy >>> 8;
  const mode = externalAttributes >>> 16;
  const type = mode & 0xf000;
  if (host === 3 && type !== 0 && type !== 0x8000) {
    fail('artifact ZIP entry is a link or special file');
  }
  if (localOffset !== 0 || uncompressedSize < 1 || uncompressedSize > maximumBytes) {
    fail(`artifact ZIP ${expectedName} size or offset is invalid`);
  }
  if (bytes.readUInt32LE(0) !== 0x04034b50) fail('artifact ZIP local header is malformed');
  const localFlags = bytes.readUInt16LE(6);
  const localMethod = bytes.readUInt16LE(8);
  const localChecksum = bytes.readUInt32LE(14);
  const localCompressedSize = bytes.readUInt32LE(18);
  const localUncompressedSize = bytes.readUInt32LE(22);
  const localNameLength = bytes.readUInt16LE(26);
  const localExtraLength = bytes.readUInt16LE(28);
  const localName = zipName(bytes.subarray(30, 30 + localNameLength), expectedName);
  if (
    localName !== name ||
    localFlags !== flags ||
    localMethod !== method ||
    localExtraLength !== 0
  ) {
    fail('artifact ZIP local/central metadata mismatch');
  }
  const dataStart = 30 + localNameLength;
  const dataEnd = dataStart + compressedSize;
  if (dataEnd > centralOffset) fail('artifact ZIP entry exceeds local-data bounds');
  let rangeEnd = dataEnd;
  if (flags & 0x0008) {
    let descriptor = dataEnd;
    if (bytes.readUInt32LE(descriptor) === 0x08074b50) descriptor += 4;
    if (descriptor + 12 > centralOffset) fail('artifact ZIP descriptor is truncated');
    if (
      bytes.readUInt32LE(descriptor) !== checksum ||
      bytes.readUInt32LE(descriptor + 4) !== compressedSize ||
      bytes.readUInt32LE(descriptor + 8) !== uncompressedSize
    ) {
      fail('artifact ZIP descriptor mismatch');
    }
    rangeEnd = descriptor + 12;
  } else if (
    localChecksum !== checksum ||
    localCompressedSize !== compressedSize ||
    localUncompressedSize !== uncompressedSize
  ) {
    fail('artifact ZIP local sizes or CRC mismatch');
  }
  if (rangeEnd !== centralOffset) fail('artifact ZIP local entry has gaps or trailing bytes');
  const body = inflate(method, bytes.subarray(dataStart, dataEnd), maximumBytes, expectedName);
  if (body.length !== uncompressedSize || crc32(body) !== checksum) {
    fail(`artifact ZIP ${expectedName} bytes or CRC mismatch`);
  }
  return body;
}

export function validatePrivacyArtifactZip({
  zipBytes,
  evidenceBytes,
  expectedZipSha256,
}) {
  const bytes = Buffer.from(zipBytes);
  exact(
    sha256(bytes),
    normalizedDigest(expectedZipSha256, 'artifact ZIP SHA-256'),
    'artifact ZIP SHA-256',
  );
  const expected = Buffer.from(evidenceBytes);
  if (expected.length < 1 || expected.length > MAX_EVIDENCE_BYTES) {
    fail('validated evidence byte size is invalid');
  }
  if (!singleFileFromZip(bytes, 'evidence.json', MAX_EVIDENCE_BYTES).equals(expected)) {
    fail('artifact ZIP evidence.json differs from the validated evidence bytes');
  }
  return true;
}

function strictBase64(value, name) {
  if (typeof value !== 'string') fail(`${name} is absent`);
  const normalized = value.replace(/\s/g, '');
  if (
    normalized.length < 4 ||
    normalized.length % 4 !== 0 ||
    !/^[A-Za-z0-9+/]+={0,2}$/.test(normalized)
  ) {
    fail(`${name} is not canonical base64`);
  }
  const bytes = Buffer.from(normalized, 'base64');
  if (bytes.toString('base64') !== normalized) fail(`${name} is not canonical base64`);
  return bytes;
}

function githubUrl(path) {
  if (typeof path !== 'string' || !path.startsWith('/') || path.startsWith('//')) {
    fail('GitHub API path is unsafe');
  }
  return `https://api.github.com${path}`;
}

async function githubResponse(path, token, fetchImpl = fetch) {
  if (typeof token !== 'string' || token.length < 1) fail('GitHub API token is absent');
  return fetchImpl(githubUrl(path), {
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${token}`,
      'X-GitHub-Api-Version': '2022-11-28',
    },
    redirect: 'error',
  });
}

async function responseJson(response, path) {
  const lengthHeader = response.headers?.get?.('content-length');
  if (lengthHeader !== null && lengthHeader !== undefined) {
    if (!/^[0-9]+$/.test(lengthHeader) || Number(lengthHeader) > MAX_API_BYTES) {
      fail(`GitHub API ${path} content length is invalid`);
    }
  }
  const raw = await response.text();
  if (Buffer.byteLength(raw, 'utf8') > MAX_API_BYTES) {
    fail(`GitHub API ${path} response is too large`);
  }
  return parseStrictJsonBytes(Buffer.from(raw), `GitHub API ${path}`, MAX_API_BYTES);
}

async function github(path, token, fetchImpl = fetch) {
  const response = await githubResponse(path, token, fetchImpl);
  if (!response.ok) fail(`GitHub API ${path} returned HTTP ${response.status}`);
  return responseJson(response, path);
}

async function githubOptional404(path, token, fetchImpl = fetch) {
  const response = await githubResponse(path, token, fetchImpl);
  if (response.status === 404) return null;
  if (!response.ok) fail(`GitHub API ${path} returned HTTP ${response.status}`);
  return responseJson(response, path);
}

export async function listAllGitHubPages({ path, field, token, fetchImpl = fetch }) {
  if (typeof field !== 'string' || !/^[a-z_]+$/.test(field)) {
    fail('GitHub pagination field is invalid');
  }
  const base = new URL(githubUrl(path));
  if (base.origin !== 'https://api.github.com') fail('GitHub pagination origin is invalid');
  const results = [];
  const ids = new Set();
  let totalCount = null;
  for (let page = 1; page <= 100; page += 1) {
    base.searchParams.set('per_page', '100');
    base.searchParams.set('page', `${page}`);
    const value = await github(`${base.pathname}${base.search}`, token, fetchImpl);
    if (value === null || typeof value !== 'object' || Array.isArray(value)) {
      fail(`GitHub paginated ${field} response must be an object`);
    }
    if (!Number.isSafeInteger(value.total_count) || value.total_count < 0 || value.total_count > 10_000) {
      fail(`GitHub paginated ${field} total_count is invalid`);
    }
    if (totalCount === null) totalCount = value.total_count;
    exact(value.total_count, totalCount, `GitHub paginated ${field} total_count`);
    const pageValues = value[field];
    if (!Array.isArray(pageValues) || pageValues.length > 100) {
      fail(`GitHub paginated ${field} page is invalid`);
    }
    for (const item of pageValues) {
      const id = positiveInteger(item?.id, `GitHub paginated ${field} item id`);
      if (ids.has(id)) fail(`GitHub paginated ${field} item is duplicated`);
      ids.add(id);
      results.push(item);
    }
    if (results.length > totalCount) fail(`GitHub paginated ${field} exceeds total_count`);
    if (results.length === totalCount) return results;
    if (pageValues.length !== 100) fail(`GitHub paginated ${field} ended before total_count`);
  }
  fail(`GitHub paginated ${field} exceeds the page limit`);
}

async function boundedResponseBytes(response, maximumBytes, name) {
  const lengthHeader = response.headers?.get?.('content-length');
  if (lengthHeader !== null && lengthHeader !== undefined) {
    if (!/^[0-9]+$/.test(lengthHeader) || Number(lengthHeader) > maximumBytes) {
      fail(`${name} content length is invalid`);
    }
  }
  if (response.body?.getReader) {
    const reader = response.body.getReader();
    const chunks = [];
    let total = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.length;
      if (total > maximumBytes) {
        await reader.cancel();
        fail(`${name} exceeds its byte limit`);
      }
      chunks.push(Buffer.from(value));
    }
    return Buffer.concat(chunks, total);
  }
  const bytes = Buffer.from(await response.arrayBuffer());
  if (bytes.length > maximumBytes) fail(`${name} exceeds its byte limit`);
  return bytes;
}

async function downloadArtifactZip(artifactId, token, fetchImpl = fetch) {
  positiveInteger(artifactId, 'candidate artifact download ID');
  const path = `/repos/${gitopsRepository}/actions/artifacts/${artifactId}/zip`;
  let response = await fetchImpl(githubUrl(path), {
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${token}`,
      'X-GitHub-Api-Version': '2022-11-28',
    },
    redirect: 'manual',
  });
  if ([301, 302, 303, 307, 308].includes(response.status)) {
    const location = response.headers?.get?.('location');
    let target;
    try {
      target = new URL(location);
    } catch {
      fail('candidate artifact redirect URL is invalid');
    }
    if (target.protocol !== 'https:' || target.username || target.password) {
      fail('candidate artifact redirect must be credential-free HTTPS');
    }
    response = await fetchImpl(target, {
      headers: { Accept: 'application/zip' },
      redirect: 'error',
    });
  }
  if (!response.ok) fail(`candidate artifact ZIP download returned HTTP ${response.status}`);
  return boundedResponseBytes(response, MAX_ZIP_BYTES, 'candidate artifact ZIP');
}

async function collectTeamMemberships(environment, approvals, token, fetchImpl = fetch) {
  if (!Array.isArray(environment?.protection_rules) || !Array.isArray(approvals)) {
    fail('team membership prerequisites are absent');
  }
  const rules = environment.protection_rules.filter(
    (rule) => rule?.type === 'required_reviewers',
  );
  if (rules.length !== 1 || !Array.isArray(rules[0].reviewers)) {
    fail('team membership reviewer rule is absent or ambiguous');
  }
  const reviews = approvals.filter(
    (review) =>
      review?.state === 'approved' &&
      Array.isArray(review.environments) &&
      review.environments.filter(
        (entry) => entry?.id === environment.id && entry?.name === privacyEnvironment,
      ).length === 1,
  );
  if (reviews.length !== 1) fail('team membership approval is absent or ambiguous');
  const login = reviews[0].user?.login;
  if (typeof login !== 'string' || !SAFE_LOGIN.test(login)) {
    fail('team membership approved reviewer login is invalid');
  }
  const reviewerId = positiveInteger(reviews[0].user?.id, 'team membership reviewer id');
  const directUser = rules[0].reviewers.some(
    (entry) => entry?.type === 'User' && entry.reviewer?.id === reviewerId,
  );
  if (directUser) return [];
  const teams = rules[0].reviewers.filter((entry) => entry?.type === 'Team');
  const result = [];
  for (const entry of teams) {
    const teamId = positiveInteger(entry.reviewer?.id, 'configured reviewer team id');
    const slug = entry.reviewer?.slug;
    if (typeof slug !== 'string' || !/^[a-z0-9](?:[a-z0-9-]{0,99})$/.test(slug)) {
      fail('configured reviewer team slug is invalid');
    }
    const path = `/orgs/DevPathAi/teams/${encodeURIComponent(slug)}/memberships/${encodeURIComponent(login)}`;
    const membership = await githubOptional404(path, token, fetchImpl);
    result.push({
      team_id: teamId,
      team_slug: slug,
      organization: 'DevPathAi',
      user_login: login,
      state: membership === null ? 'absent' : membership.state,
      role: membership === null ? null : membership.role,
    });
  }
  return result;
}

async function authenticateApproval({ repositoryRoot, sourceSha, runId, runAttempt, output }) {
  const token = process.env.GITHUB_TOKEN;
  if (!token) fail('GITHUB_TOKEN is absent');
  const orgToken = process.env.ORG_TOKEN;
  if (!orgToken) fail('ORG_TOKEN is absent');
  exact(process.env.GITHUB_REPOSITORY, documentsRepository, 'GITHUB_REPOSITORY');
  exact(process.env.GITHUB_REF, `refs/heads/${documentsBranch}`, 'GITHUB_REF');
  exact(process.env.GITHUB_SHA, sourceSha, 'GITHUB_SHA');
  if (runAttempt !== 1) fail('protected approvals require attempt 1');
  const repositoryInfo = await github(`/repos/${documentsRepository}`, token);
  const run = await github(
    `/repos/${documentsRepository}/actions/runs/${runId}/attempts/${runAttempt}`,
    token,
  );
  const branch = await github(`/repos/${documentsRepository}/branches/${documentsBranch}`, token);
  const environment = await github(
    `/repos/${documentsRepository}/environments/${encodeURIComponent(privacyEnvironment)}`,
    token,
  );
  const encodedWorkflow = privacyWorkflow
    .split('/')
    .map((part) => encodeURIComponent(part))
    .join('/');
  const workflow = await github(
    `/repos/${documentsRepository}/contents/${encodedWorkflow}?ref=${sourceSha}`,
    token,
  );
  exact(workflow.type, 'file', 'workflow source type');
  exact(workflow.path, privacyWorkflow, 'workflow source path');
  exact(workflow.encoding, 'base64', 'workflow source encoding');
  const workflowBytes = strictBase64(workflow.content, 'workflow source content');
  const localPath = join(repositoryRoot, privacyWorkflow);
  regularFile(localPath, 'local privacy workflow', MAX_API_BYTES);

  let approvals = [];
  let jobs = null;
  for (let attempt = 0; attempt < 10; attempt += 1) {
    approvals = await github(
      `/repos/${documentsRepository}/actions/runs/${runId}/approvals`,
      token,
    );
    jobs = await github(
      `/repos/${documentsRepository}/actions/runs/${runId}/attempts/${runAttempt}/jobs?per_page=100`,
      token,
    );
    const visibleApproval = Array.isArray(approvals) && approvals.some(
      (review) =>
        review?.state === 'approved' &&
        review.environments?.some(
          (entry) => entry?.id === environment.id && entry?.name === privacyEnvironment,
        ),
    );
    const visibleJob = jobs?.jobs?.some(
      (job) => job?.name === privacyJob && job?.started_at && job?.status === 'in_progress',
    );
    if (visibleApproval && visibleJob) break;
    await new Promise((done) => setTimeout(done, 2000));
  }
  const teamMemberships = await collectTeamMemberships(
    environment,
    approvals,
    orgToken,
  );
  const approval = validateProtectedApprovalFacts({
    repository: documentsRepository,
    sourceSha,
    runId,
    runAttempt,
    workflowPath: privacyWorkflow,
    environmentName: privacyEnvironment,
    jobName: privacyJob,
    repositoryInfo,
    run,
    branch,
    environment,
    approvals,
    jobs,
    teamMemberships,
    workflowBytes,
    localWorkflowBytes: readFileSync(localPath),
  });
  writeFileSync(output, `${JSON.stringify(approval, null, 2)}\n`, {
    encoding: 'utf8',
    flag: 'wx',
    mode: 0o600,
  });
  return approval;
}

function contentFileBytes(content, expectedPath, maximumBytes, name) {
  exact(content?.type, 'file', `${name} type`);
  exact(content?.path, expectedPath, `${name} path`);
  exact(content?.encoding, 'base64', `${name} encoding`);
  if (!Number.isSafeInteger(content?.size) || content.size < 1 || content.size > maximumBytes) {
    fail(`${name} size is invalid`);
  }
  const bytes = strictBase64(content.content, `${name} content`);
  exact(bytes.length, content.size, `${name} decoded size`);
  return bytes;
}

function exactRunView(left, right, name) {
  for (const field of [
    'id',
    'run_attempt',
    'event',
    'status',
    'conclusion',
    'head_sha',
    'head_branch',
    'path',
  ]) {
    exact(left?.[field], right?.[field], `${name}.${field}`);
  }
  exact(left?.repository?.full_name, right?.repository?.full_name, `${name}.repository`);
  exact(
    left?.head_repository?.full_name,
    right?.head_repository?.full_name,
    `${name}.head_repository`,
  );
}

export async function discoverCandidateArtifact({
  releaseId,
  candidateSpecSha256,
  approvalSourceSha,
  token,
  fetchImpl = fetch,
}) {
  safeReleaseId(releaseId);
  sha64(candidateSpecSha256, 'candidate_spec_sha256');
  sha40(approvalSourceSha, 'approval_source_sha');
  if (typeof token !== 'string' || token.length < 1) fail('GITOPS_TOKEN is absent');
  const workflowId = encodeURIComponent(candidateWorkflow);
  const runs = await listAllGitHubPages({
    path: `/repos/${gitopsRepository}/actions/workflows/${workflowId}/runs?event=workflow_dispatch&status=completed&exclude_pull_requests=true`,
    field: 'workflow_runs',
    token,
    fetchImpl,
  });
  const expectedBranch = `release/candidate-${releaseId}`;
  const matches = [];
  for (const listed of runs) {
    if (listed?.head_branch !== expectedBranch) continue;
    if (
      listed.event !== 'workflow_dispatch' ||
      listed.status !== 'completed' ||
      listed.conclusion !== 'success' ||
      listed.path !== candidateWorkflow ||
      listed.repository?.full_name !== gitopsRepository ||
      listed.head_repository?.full_name !== gitopsRepository
    ) {
      continue;
    }
    const runId = positiveInteger(listed.id, 'candidate listed run.id');
    const listedAttempt = positiveInteger(
      listed.run_attempt,
      'candidate listed run.run_attempt',
    );
    const current = await github(
      `/repos/${gitopsRepository}/actions/runs/${runId}`,
      token,
      fetchImpl,
    );
    exactRunView(listed, current, 'candidate listed/current run');
    exact(current.run_attempt, listedAttempt, 'candidate current highest run_attempt');
    const attempt = await github(
      `/repos/${gitopsRepository}/actions/runs/${runId}/attempts/${listedAttempt}`,
      token,
      fetchImpl,
    );
    exactRunView(current, attempt, 'candidate current/attempt run');
    const expectedName =
      `${releaseId}-candidate-spec-run-${runId}-attempt-${listedAttempt}`;
    const artifacts = await listAllGitHubPages({
      path: `/repos/${gitopsRepository}/actions/runs/${runId}/artifacts`,
      field: 'artifacts',
      token,
      fetchImpl,
    });
    const named = artifacts.filter((artifact) => artifact?.name === expectedName);
    if (named.length === 0) continue;
    if (named.length !== 1) fail('candidate run has ambiguous exact-named artifacts');
    if (named[0].expired === true) continue;
    const metadata = await github(
      `/repos/${gitopsRepository}/actions/artifacts/${positiveInteger(
        named[0].id,
        'candidate listed artifact.id',
      )}`,
      token,
      fetchImpl,
    );
    for (const field of ['id', 'name', 'expired', 'size_in_bytes', 'digest', 'expires_at']) {
      exact(named[0][field], metadata[field], `candidate listed/metadata artifact.${field}`);
    }
    exact(
      named[0].workflow_run?.id,
      metadata.workflow_run?.id,
      'candidate listed/metadata artifact.workflow_run.id',
    );
    exact(
      named[0].workflow_run?.head_sha,
      metadata.workflow_run?.head_sha,
      'candidate listed/metadata artifact.workflow_run.head_sha',
    );
    const zipBytes = await downloadArtifactZip(metadata.id, token, fetchImpl);
    if (zipBytes.length !== metadata.size_in_bytes) {
      fail('candidate artifact ZIP differs from metadata size');
    }
    exact(
      sha256(zipBytes),
      normalizedDigest(metadata.digest, 'candidate artifact digest'),
      'candidate artifact ZIP SHA-256',
    );
    const rawCandidate = singleFileFromZip(
      zipBytes,
      'candidate-spec.json',
      MAX_CANDIDATE_BYTES,
    );
    if (sha256(rawCandidate) !== candidateSpecSha256) continue;
    matches.push(validateCandidateArtifactFacts({
      releaseId,
      candidateSpecSha256,
      approvalSourceSha,
      run: attempt,
      artifact: metadata,
      zipBytes,
    }));
  }
  const selected = selectUniqueCandidateMatch(matches);
  const repositoryInfo = await github(`/repos/${gitopsRepository}`, token, fetchImpl);
  const mainBranch = await github(
    `/repos/${gitopsRepository}/branches/main`,
    token,
    fetchImpl,
  );
  const headCommit = await github(
    `/repos/${gitopsRepository}/commits/${selected.headSha}`,
    token,
    fetchImpl,
  );
  const comparison = await github(
    `/repos/${gitopsRepository}/compare/${selected.baseSha}...${selected.headSha}`,
    token,
    fetchImpl,
  );
  const candidatePath = `release-manifests/candidates/${releaseId}.candidate-spec.json`;
  const encodedCandidatePath = candidatePath
    .split('/')
    .map((part) => encodeURIComponent(part))
    .join('/');
  const candidateContent = await github(
    `/repos/${gitopsRepository}/contents/${encodedCandidatePath}?ref=${selected.headSha}`,
    token,
    fetchImpl,
  );
  const candidateBlobBytes = contentFileBytes(
    candidateContent,
    candidatePath,
    MAX_CANDIDATE_BYTES,
    'candidate source blob',
  );
  const encodedWorkflow = candidateWorkflow
    .split('/')
    .map((part) => encodeURIComponent(part))
    .join('/');
  const baseWorkflowContent = await github(
    `/repos/${gitopsRepository}/contents/${encodedWorkflow}?ref=${selected.baseSha}`,
    token,
    fetchImpl,
  );
  const headWorkflowContent = await github(
    `/repos/${gitopsRepository}/contents/${encodedWorkflow}?ref=${selected.headSha}`,
    token,
    fetchImpl,
  );
  const baseWorkflowBytes = contentFileBytes(
    baseWorkflowContent,
    candidateWorkflow,
    MAX_API_BYTES,
    'protected candidate workflow',
  );
  const headWorkflowBytes = contentFileBytes(
    headWorkflowContent,
    candidateWorkflow,
    MAX_API_BYTES,
    'candidate head workflow',
  );
  validateCandidateSourceFacts({
    releaseId,
    candidateBytes: selected.candidateBytes,
    candidateSpecSha256,
    approvalSourceSha,
    headSha: selected.headSha,
    repositoryInfo,
    mainBranch,
    headCommit,
    comparison,
    candidateBlobBytes,
    baseWorkflowBytes,
    headWorkflowBytes,
  });
  return selected;
}

async function fetchCandidate({
  releaseId,
  candidateSpecSha256,
  approvalSourceSha,
  output,
}) {
  const token = process.env.GITOPS_TOKEN;
  const selected = await discoverCandidateArtifact({
    releaseId,
    candidateSpecSha256,
    approvalSourceSha,
    token,
  });
  writeFileSync(output, selected.candidateBytes, { flag: 'wx', mode: 0o600 });
  return selected.candidateBytes;
}

function parseOptions(arguments_) {
  const result = new Map();
  for (const argument of arguments_) {
    if (!argument.startsWith('--') || !argument.includes('=')) fail(`invalid option ${argument}`);
    const split = argument.indexOf('=');
    const key = argument.slice(2, split);
    if (!key || result.has(key)) fail(`duplicate or empty option --${key}`);
    result.set(key, argument.slice(split + 1));
  }
  return result;
}

function required(options, key) {
  const value = options.get(key);
  if (!value) fail(`missing --${key}`);
  return value;
}

function integerOption(options, key) {
  const value = required(options, key);
  if (!/^[1-9][0-9]*$/.test(value)) fail(`--${key} must be a positive integer`);
  return positiveInteger(Number(value), key);
}

function exactOptions(options, expected) {
  const actual = [...options.keys()].sort(compareAscii);
  const wanted = [...expected].sort(compareAscii);
  if (actual.length !== wanted.length || actual.some((value, index) => value !== wanted[index])) {
    fail(`options must be exactly ${wanted.join(', ')}`);
  }
}

function commonEvidenceOptions(options) {
  safeReleaseId(required(options, 'release-id'));
  return {
    candidatePath: required(options, 'candidate'),
    approvalPath: required(options, 'approval'),
    packageRoot: required(options, 'package-root'),
    releaseId: required(options, 'release-id'),
    candidateSpecSha256: required(options, 'candidate-spec-sha256'),
    approvalSourceSha: required(options, 'approval-source-sha'),
    producerRunId: integerOption(options, 'producer-run-id'),
    producerRunAttempt: integerOption(options, 'producer-run-attempt'),
  };
}

async function cli() {
  const [command, ...arguments_] = process.argv.slice(2);
  const options = parseOptions(arguments_);
  if (command === 'authenticate-approval') {
    exactOptions(options, ['repository-root', 'source-sha', 'run-id', 'run-attempt', 'output']);
    await authenticateApproval({
      repositoryRoot: resolve(required(options, 'repository-root')),
      sourceSha: required(options, 'source-sha'),
      runId: integerOption(options, 'run-id'),
      runAttempt: integerOption(options, 'run-attempt'),
      output: required(options, 'output'),
    });
    process.stdout.write('Protected privacy approval authenticated\n');
    return;
  }
  if (command === 'fetch-candidate') {
    exactOptions(options, [
      'release-id',
      'candidate-spec-sha256',
      'approval-source-sha',
      'output',
    ]);
    await fetchCandidate({
      releaseId: required(options, 'release-id'),
      candidateSpecSha256: required(options, 'candidate-spec-sha256'),
      approvalSourceSha: required(options, 'approval-source-sha'),
      output: required(options, 'output'),
    });
    process.stdout.write('Canonical GitOps candidate authenticated\n');
    return;
  }
  if (command === 'create-evidence' || command === 'validate-evidence') {
    exactOptions(options, [
      'candidate',
      'approval',
      'package-root',
      'release-id',
      'candidate-spec-sha256',
      'approval-source-sha',
      'producer-run-id',
      'producer-run-attempt',
    ]);
    const common = commonEvidenceOptions(options);
    if (command === 'create-evidence') {
      createEvidencePackage(common);
      process.stdout.write('Canonical privacy evidence created\n');
    } else {
      validateEvidencePackage(common);
      process.stdout.write('Canonical privacy evidence valid\n');
    }
    return;
  }
  if (command === 'validate-artifact-metadata') {
    exactOptions(options, [
      'metadata',
      'artifact-id',
      'artifact-name',
      'artifact-digest',
      'run-id',
      'source-sha',
    ]);
    const metadata = parseJsonFile(
      required(options, 'metadata'),
      'artifact metadata',
      MAX_API_BYTES,
    ).value;
    validatePrivacyArtifactMetadata({
      metadata,
      artifactId: integerOption(options, 'artifact-id'),
      artifactName: required(options, 'artifact-name'),
      artifactDigest: required(options, 'artifact-digest'),
      runId: integerOption(options, 'run-id'),
      sourceSha: required(options, 'source-sha'),
    });
    process.stdout.write('Uploaded privacy artifact metadata valid\n');
    return;
  }
  if (command === 'validate-artifact-zip') {
    exactOptions(options, ['zip', 'evidence', 'expected-zip-sha256']);
    const zipPath = required(options, 'zip');
    const evidencePath = required(options, 'evidence');
    regularFile(zipPath, 'artifact ZIP', MAX_ZIP_BYTES);
    regularFile(evidencePath, 'validated evidence.json', MAX_EVIDENCE_BYTES);
    validatePrivacyArtifactZip({
      zipBytes: readFileSync(zipPath),
      evidenceBytes: readFileSync(evidencePath),
      expectedZipSha256: required(options, 'expected-zip-sha256'),
    });
    process.stdout.write('Uploaded privacy artifact ZIP valid\n');
    return;
  }
  fail('unknown command');
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(resolve(process.argv[1])).href
) {
  cli().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
