# S2a PR ① — gitops 릴리스 계약에서 서명 모바일·TalkBack 제거 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gitops 의 candidate spec·릴리스 매니페스트 계약과 그 검증기·봉인기에서 서명 Android 빌드 바인딩(`mobile_test_artifacts`)과 `manual-talkback` 레인을 제거한다. 수동 접근성 증거는 `manual-nvda` 하나, 품질 증거 레이블은 6 → 5.

**Architecture:** 계약의 모양은 네 곳에 겹쳐 적혀 있다 — JSON Schema(`schema-v1.json`), 파이썬 검증기의 상수·exact-key 검사(`validate_release_manifest.py`), 아티팩트 검증기(`verify_release_artifacts.py`), 봉인기(`seal_release_manifest.py`). 네 곳과 합성 픽스처 쌍을 한 PR 에서 같은 모양으로 맞춘다. `schema_version` 은 1 그대로(in-place). exact-key 검증이라 구 모양 문서는 버전 없이도 거부된다 — 그 거부를 새 계약 테스트가 고정한다. **ET13 12-fixture 리터럴(`"mobile"` 표면 포함)은 이 PR 에서 건드리지 않는다**(PR ② 의 몫).

**Tech Stack:** Python 3(`unittest`, `jsonschema==4.25.1`, `PyYAML==6.0.2`) · JSON Schema Draft 2020-12

**Spec:** `docs/superpowers/specs/2026-09-19-s2c2-s2a-drop-signed-mobile-and-gitops-mirror-design.md` §4.1 (documents 레포)

## Global Constraints

- 작업 레포: `DevPathAi/devpath-gitops`. 주 checkout(`D:/workspace/dpa/devpath-gitops`)은 건드리지 않는다. 전용 worktree `D:/workspace/dpa/.worktrees/gitops-s2a1`(이하 `$WT`)에서만 작업한다.
- 브랜치: `origin/develop` 에서 `chore/s2a-drop-signed-mobile-talkback` 분기 → `develop` 으로 PR. **`main` 은 이 계획의 범위가 아니다**(main 승격은 PR ② 뒤의 별도 계획). 머지는 merge commit.
- 모든 git·파일 명령은 절대경로 또는 `git -C <절대경로>`. `cd` 뒤 상대경로 후속 명령 금지. 테스트처럼 cwd 가 필요한 명령은 한 번의 Bash 호출 안에서 `cd <절대경로> && …` 로 묶는다.
- `schema_version` 은 **1**, 스키마 파일명은 **`schema-v1.json`** 그대로.
- 이 PR 에서 **건드리지 않는 것**: `FRONTEND_FIXTURE_IDS`·`FRONTEND_PROJECTION_MATRIX`·`FRONTEND_PROJECTION_CONTRACT_SHA256`·`FRONTEND_CATALOG_CONTRACTS` 와 스키마의 ET13 `const`, 표면 집합 `{"web","admin","mobile","dp_design"}`, `_frontend_surface` 의 `mobile-` 분기, `release-manifests/contracts/frontend-et13/**`, `tests/release/test_et13_atomic_evidence.py`, `tests/release/test_release_hardening.py`. 이들의 `mobile` 은 ET13 표면 이름이고 PR ② 가 처리한다.
- 픽스처 `tests/release/fixtures/valid-candidate-spec.json`·`valid-release.json` 은 손으로 포맷된 JSON 이다(`json.dumps` 로 재직렬화하면 바이트가 달라진다 — 실측). **텍스트 블록 단위로만** 고친다.
- candidate 픽스처의 sha256 은 세 곳에 결속돼 있다: `valid-candidate-spec.sha256`(형식 `<sha>␠␠valid-candidate-spec.json\n`) · `valid-release.json` 의 `candidate_spec.sha256` 1곳 · `candidate_spec_sha256` N곳. 픽스처를 고치면 반드시 재결속한다(Task 2 의 스크립트).
- 파이썬 실행은 `py`(이 PC 에서 `python` 은 무동작 스텁).
- CI 와 같은 명령으로 검증한다: `py -m unittest discover -s tests/release -p 'test_*.py'`.
- 워킹 카피가 CRLF 일 수 있다. 파일을 고치는 스크립트는 **바이트 단위**로 읽고 써서 줄 끝을 보존한다.

## File Structure

| 파일 | 조치 | 책임 |
|---|---|---|
| `tests/release/test_mobile_free_release_contract.py` | 신규 | 새 계약의 고정: 구 모양 거부(파이썬 검증기 + JSON Schema) · 계약 테이블이 NVDA 단독 · 제거된 심볼 부재 · 소스 잔존 문자열 부재 · 봉인기의 단일 레인 producer run 탐색 |
| `release-manifests/schema-v1.json` | 수정 | `mobileTestArtifacts` 정의와 그 참조, `manual-talkback`/`manual_talkback` 제거 |
| `scripts/release/validate_release_manifest.py` | 수정 | 상수 테이블·`quality_evidence_inputs` exact-key·서명 아티팩트 구별 검사 |
| `scripts/release/verify_release_artifacts.py` | 수정 | 서명 모바일 함수 7개·상수·TalkBack 분기·`signed-mobile` producer kind 제거 |
| `scripts/release/seal_release_manifest.py` | 수정 | `signed_mobile_context` 배관 제거, `_discover_manual_trio` → `_discover_manual_evidence` |
| `tests/release/fixtures/valid-candidate-spec.json` · `.sha256` · `valid-release.json` | 수정 | 합성 픽스처를 새 모양으로 + sha 재결속 |
| `tests/release/test_signed_mobile_manual_trust.py` | `test_manual_nvda_trust.py` 로 이름 변경·수정 | NVDA 수동 증거 신뢰 테스트만 남김 |
| `tests/release/test_et13_evidence_contract.py` | 수정 | 모바일·TalkBack 의존 부분만 |
| `tests/release/test_release_contract.py` | 수정 | 610–614행의 모바일 아티팩트 이름 갱신 제거 |
| `tests/release/test_et13_final_rebind.py` | 수정 | candidate sha 참조 개수 13 → 12 |
| `release-manifests/README.md` | 수정 | 계약 서술 정정 |

**중간 상태 주의:** 검증기 → 아티팩트 검증기 → 봉인기는 import 로 묶여 있어(`verify` 가 `validate` 의 `SIGNED_MOBILE_*` 를 import) Task 2 와 Task 5 사이에는 전체 스위트가 빨갛다. 각 Task 는 자기 범위의 표적 검사로 확인하고, **전체 스위트 녹색 게이트는 Task 5 끝**이다.

---

### Task 0: worktree · 도구 · 기준선

**Files:** 스크래치패드에 도구 스크립트 2개 생성(레포에 커밋하지 않음)

**Interfaces:**
- Produces: `$WT` · `<스크래치패드>/s2a1/delete_top_level.py`(`py delete_top_level.py <파일> <이름>…`) · `<스크래치패드>/s2a1/baseline-tests.txt`·`baseline-pyflakes.txt`.

- [ ] **Step 1: worktree 생성과 기준 커밋 확인**

```bash
git -C D:/workspace/dpa/devpath-gitops fetch origin
git -C D:/workspace/dpa/devpath-gitops worktree add -b chore/s2a-drop-signed-mobile-talkback \
  D:/workspace/dpa/.worktrees/gitops-s2a1 origin/develop
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 log -1 --format='%h %s'
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 diff 988661b HEAD --stat -- scripts/release release-manifests tests/release
```

Expected: HEAD 가 `988661b`(2026-09-19 의 `origin/develop`)이거나, 그보다 뒤라면 마지막 명령의 출력이 비어 있다. 비어 있지 않으면 멈추고 `NEEDS_CONTEXT` 로 보고한다(이 계획의 줄 번호는 `988661b` 기준이다).

- [ ] **Step 2: 의존성과 기준선**

```bash
py -m pip install --user --disable-pip-version-check jsonschema==4.25.1 PyYAML==6.0.2 pyflakes
cd D:/workspace/dpa/.worktrees/gitops-s2a1 && py -m unittest discover -s tests/release -p 'test_*.py' 2>&1 | tail -5 > "<스크래치패드>/s2a1/baseline-tests.txt"; cat "<스크래치패드>/s2a1/baseline-tests.txt"
cd D:/workspace/dpa/.worktrees/gitops-s2a1 && py -m pyflakes scripts/release/validate_release_manifest.py scripts/release/verify_release_artifacts.py scripts/release/seal_release_manifest.py > "<스크래치패드>/s2a1/baseline-pyflakes.txt"; wc -l "<스크래치패드>/s2a1/baseline-pyflakes.txt"
```

Expected: `baseline-tests.txt` 의 마지막 줄이 `OK`(또는 `OK (skipped=N)`). `FAILED` 면 멈추고 실패 목록을 보고한다 — 이 계획과 무관한 기존 결함이다(Windows 전용 실패 여부는 같은 커밋의 gitops CI 결과와 대조).

- [ ] **Step 3: 최상위 정의 삭제 도구를 스크래치패드에 작성**

`<스크래치패드>/s2a1/delete_top_level.py`:

```python
"""Delete named top-level functions/assignments from a Python file, preserving line endings."""
import ast
import sys
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1])
    names = sys.argv[2:]
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    spans = []
    for name in names:
        matches = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                matches.append(node)
            elif (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == name
            ):
                matches.append(node)
        if len(matches) != 1:
            raise SystemExit(f"{name}: expected exactly one top-level definition, found {len(matches)}")
        node = matches[0]
        start = node.lineno - 1
        if isinstance(node, ast.FunctionDef) and node.decorator_list:
            start = node.decorator_list[0].lineno - 1
        end = node.end_lineno
        while end < len(lines) and lines[end].strip() == "":
            end += 1
        spans.append((start, end))
    for start, end in sorted(spans, reverse=True):
        del lines[start:end]
    result = "".join(lines)
    ast.parse(result)
    path.write_bytes(result.encode("utf-8"))
    print(f"{path.name}: deleted {len(names)} definitions, {len(text.splitlines()) - len(result.splitlines())} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

### Task 1: 새 계약 테스트(빨강)

**Files:**
- Create: `tests/release/test_mobile_free_release_contract.py`

**Interfaces:**
- Consumes: `validate_release_manifest.validate_candidate_spec(data, source)` · `validate_release_manifest(release, candidate, candidate_hash, source)` · 봉인기의 `_discover_manual_evidence(env, release_id, candidate_hash, candidate)`(Task 4 가 만든다).
- Produces: 이후 모든 Task 의 완료 기준.

- [ ] **Step 1: 테스트 파일 작성**

`tests/release/test_mobile_free_release_contract.py`:

```python
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest
from unittest import mock

import jsonschema


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "release"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SCHEMA = ROOT / "release-manifests" / "schema-v1.json"
README = ROOT / "release-manifests" / "README.md"
CANDIDATE_FIXTURE = ROOT / "tests" / "release" / "fixtures" / "valid-candidate-spec.json"
RELEASE_FIXTURE = ROOT / "tests" / "release" / "fixtures" / "valid-release.json"

QUALITY_LABELS = (
    "frontend-visual",
    "home-visual",
    "frontend-automated-a11y",
    "home-axe-browser-a11y",
    "manual-nvda",
)
QUALITY_KEYS = (
    "frontend_visual",
    "home_visual",
    "frontend_automated_a11y",
    "home_axe_browser_a11y",
    "manual_nvda",
)
RESIDUE = re.compile(
    r"talkback|signed[-_ ]?(?:mobile|android|apk)|mobile_test_artifacts|SIGNED_MOBILE|\.apk|build-provenance",
    re.IGNORECASE,
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MobileFreeReleaseContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_module(
            SCRIPTS / "validate_release_manifest.py", "mobile_free_validator"
        )
        cls.verifier = load_module(
            SCRIPTS / "verify_release_artifacts.py", "mobile_free_verifier"
        )
        cls.sealer = load_module(
            SCRIPTS / "seal_release_manifest.py", "mobile_free_sealer"
        )
        cls.candidate = json.loads(CANDIDATE_FIXTURE.read_text(encoding="utf-8"))
        cls.release = json.loads(RELEASE_FIXTURE.read_text(encoding="utf-8"))
        cls.candidate_sha = hashlib.sha256(CANDIDATE_FIXTURE.read_bytes()).hexdigest()
        cls.schema = jsonschema.Draft202012Validator(
            json.loads(SCHEMA.read_text(encoding="utf-8"))
        )

    def _legacy_signed_binding(self) -> dict:
        release_id = self.candidate["release_id"]
        return {
            "schema_version": "leva.mission-spine.signed-android-build-binding.v2",
            "repository": "DevPathAi/devpath-frontend",
            "source_sha": self.candidate["frontend"]["source_sha"],
            "event": "workflow_dispatch",
            "workflow_path": ".github/workflows/mission-spine-signed-mobile-build.yml",
            "workflow_sha256": "3" * 64,
            "workflow_run_id": 701,
            "run_attempt": 1,
            "artifact_id": 801,
            "artifact_name": f"{release_id}-signed-android-build-run-701-attempt-1",
            "artifact_archive_sha256": "4" * 64,
            "build_provenance_file": "build-provenance.v2.json",
            "build_provenance_sha256": "5" * 64,
            "signed_apk_file": "mobile/android/leva-release.apk",
            "signed_apk_sha256": "6" * 64,
        }

    def test_fixtures_have_the_mobile_free_shape_and_validate(self):
        inputs = self.candidate["quality_evidence_inputs"]
        self.assertEqual(set(inputs), {"catalogs", "frontend_projection_contract"})
        self.assertEqual(tuple(inputs["catalogs"]), QUALITY_LABELS)
        self.assertEqual(tuple(self.release["quality_evidence"]), QUALITY_KEYS)
        self.schema.validate(self.candidate)
        self.schema.validate(self.release)
        self.validator.validate_candidate_spec(
            copy.deepcopy(self.candidate), CANDIDATE_FIXTURE
        )
        self.validator.validate_release_manifest(
            copy.deepcopy(self.release),
            copy.deepcopy(self.candidate),
            self.candidate_sha,
            RELEASE_FIXTURE,
        )

    def test_legacy_signed_mobile_binding_fails_closed(self):
        legacy = copy.deepcopy(self.candidate)
        legacy["quality_evidence_inputs"]["mobile_test_artifacts"] = (
            self._legacy_signed_binding()
        )
        with self.assertRaisesRegex(ValueError, "unknown fields: mobile_test_artifacts"):
            self.validator.validate_candidate_spec(legacy, CANDIDATE_FIXTURE)
        with self.assertRaises(jsonschema.ValidationError):
            self.schema.validate(legacy)

    def test_legacy_talkback_catalog_and_artifact_fail_closed(self):
        legacy = copy.deepcopy(self.candidate)
        catalogs = legacy["quality_evidence_inputs"]["catalogs"]
        talkback = copy.deepcopy(catalogs["manual-nvda"])
        talkback["path"] = "tool/release-evidence/catalogs/manual-talkback.v1.json"
        talkback["sha256"] = "7" * 64
        talkback["case_count"] = 4
        talkback["provenance_sha256"] = "8" * 64
        catalogs["manual-talkback"] = talkback
        with self.assertRaisesRegex(ValueError, "unknown fields: manual-talkback"):
            self.validator.validate_candidate_spec(legacy, CANDIDATE_FIXTURE)
        with self.assertRaises(jsonschema.ValidationError):
            self.schema.validate(legacy)

        release = copy.deepcopy(self.release)
        artifact = copy.deepcopy(release["quality_evidence"]["manual_nvda"])
        artifact["artifact_id"] += 1000
        artifact["artifact_name"] = artifact["artifact_name"].replace(
            "manual-nvda", "manual-talkback"
        )
        release["quality_evidence"]["manual_talkback"] = artifact
        with self.assertRaisesRegex(ValueError, "unknown fields: manual_talkback"):
            self.validator.validate_release_manifest(
                release,
                copy.deepcopy(self.candidate),
                self.candidate_sha,
                RELEASE_FIXTURE,
            )
        with self.assertRaises(jsonschema.ValidationError):
            self.schema.validate(release)

    def test_contract_tables_are_nvda_only(self):
        self.assertEqual(tuple(self.validator.QUALITY_EVIDENCE), QUALITY_LABELS)
        self.assertEqual(tuple(self.validator.QUALITY_EVIDENCE.values()), QUALITY_KEYS)
        self.assertEqual(tuple(self.validator.QUALITY_EVIDENCE_FILES), QUALITY_LABELS)
        self.assertEqual(tuple(self.validator.MANUAL_CATALOG_CONTRACTS), ("manual-nvda",))
        self.assertNotIn("manual-talkback", self.validator.PRODUCER_WORKFLOWS)
        self.assertEqual(
            set(self.verifier.PROTECTED_APPROVAL_CONTRACTS),
            {
                "frontend-baseline",
                "ai-release-eval",
                "privacy-approval",
                "shared-migration-result",
                "manual-nvda",
            },
        )
        for module, removed in (
            (
                self.validator,
                (
                    "SIGNED_MOBILE_BINDING_KEYS",
                    "SIGNED_MOBILE_BINDING_VERSION",
                    "SIGNED_MOBILE_WORKFLOW",
                    "SIGNED_MOBILE_FILES",
                ),
            ),
            (
                self.verifier,
                (
                    "MAX_SIGNED_MOBILE_BINARY_BYTES",
                    "MAX_SIGNED_MOBILE_ARCHIVE_BYTES",
                    "SIGNED_MOBILE_PROVENANCE_KEYS",
                    "validate_signed_mobile_provenance",
                    "_extract_signed_mobile_archive",
                    "_download_signed_mobile_archive",
                    "validate_signed_mobile_bundle",
                    "validate_manual_chronology",
                    "_parse_mobile_version",
                    "verify_signed_mobile_artifact",
                ),
            ),
            (self.sealer, ("_discover_manual_trio",)),
        ):
            for name in removed:
                self.assertFalse(hasattr(module, name), f"{module.__name__}.{name}")

    def test_unknown_protected_producer_kind_is_rejected(self):
        with mock.patch.object(self.verifier, "_list_protected_runs", return_value=[]):
            with self.assertRaisesRegex(ValueError, "exactly one"):
                self.verifier.select_unique_protected_producer_run(
                    {}, "DevPathAi/devpath-frontend", "a" * 40,
                    self.validator.PRODUCER_WORKFLOWS["manual-nvda"],
                    self.candidate["release_id"], "manual",
                )
        run = {
            "id": 111, "status": "completed", "conclusion": "success",
            "event": "workflow_dispatch", "head_sha": "a" * 40, "head_branch": "main",
            "path": self.validator.PRODUCER_WORKFLOWS["manual-nvda"], "run_attempt": 1,
        }
        with mock.patch.object(
            self.verifier, "_list_protected_runs", return_value=[run]
        ), mock.patch.object(self.verifier, "_list_named_artifacts", return_value=[]):
            with self.assertRaisesRegex(ValueError, "unknown protected producer kind"):
                self.verifier.select_unique_protected_producer_run(
                    {}, "DevPathAi/devpath-frontend", "a" * 40,
                    self.validator.PRODUCER_WORKFLOWS["manual-nvda"],
                    self.candidate["release_id"], "signed-mobile",
                )

    def test_sealer_discovers_the_single_manual_lane_from_one_run(self):
        release_id = self.candidate["release_id"]
        head = self.candidate["frontend"]["source_sha"]
        workflow = self.validator.PRODUCER_WORKFLOWS["manual-nvda"]

        def run(run_id):
            return {
                "id": run_id, "status": "completed", "conclusion": "success",
                "event": "workflow_dispatch", "head_sha": head, "head_branch": "main",
                "path": workflow, "run_attempt": 1,
            }

        published = {f"{release_id}-manual-nvda-run-412-attempt-1": 412}

        def artifacts(_env, _repository, name):
            if name not in published:
                return []
            return [{"name": name, "expired": False, "workflow_run": {"id": published[name]}}]

        with mock.patch.object(
            self.sealer, "list_manual_evidence_runs", return_value=[run(411), run(412)]
        ), mock.patch.object(
            self.sealer, "_list_named_artifacts", side_effect=artifacts
        ), mock.patch.object(
            self.sealer, "_discover_external_artifact", return_value={"artifact_id": 9}
        ) as discover:
            discovered = self.sealer._discover_manual_evidence(
                {}, release_id, self.candidate_sha, self.candidate
            )
        self.assertEqual(discovered, {"manual_nvda": {"artifact_id": 9}})
        discover.assert_called_once()
        args, kwargs = discover.call_args
        self.assertEqual(args[1], "manual-nvda")
        self.assertEqual(args[3], f"{release_id}-manual-nvda-run-412-attempt-1")
        self.assertEqual(kwargs["expected_run_id"], 412)
        self.assertNotIn("signed_mobile_context", kwargs)

        published[f"{release_id}-manual-nvda-run-411-attempt-1"] = 411
        with mock.patch.object(
            self.sealer, "list_manual_evidence_runs", return_value=[run(411), run(412)]
        ), mock.patch.object(
            self.sealer, "_list_named_artifacts", side_effect=artifacts
        ):
            with self.assertRaisesRegex(ValueError, "exactly one"):
                self.sealer._discover_manual_evidence(
                    {}, release_id, self.candidate_sha, self.candidate
                )

    def test_release_contract_sources_carry_no_residue(self):
        for path in (
            SCRIPTS / "validate_release_manifest.py",
            SCRIPTS / "verify_release_artifacts.py",
            SCRIPTS / "seal_release_manifest.py",
            SCHEMA,
            README,
            CANDIDATE_FIXTURE,
            RELEASE_FIXTURE,
        ):
            with self.subTest(path=path.name):
                hits = sorted(set(RESIDUE.findall(path.read_text(encoding="utf-8"))))
                self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인**

```bash
cd D:/workspace/dpa/.worktrees/gitops-s2a1 && py -m unittest tests.release.test_mobile_free_release_contract 2>&1 | tail -15
```

Expected: FAIL/ERROR 7건 전부(예: `AttributeError: … has no attribute '_discover_manual_evidence'`, `AssertionError: … mobile_test_artifacts`). (검증기의 오류 형식은 `<경로>: unknown fields: <키>`, producer run 선택의 오류는 `<kind>: exactly one eligible protected producer run is required` / `unknown protected producer kind: <kind>` — `988661b` 실측.)

- [ ] **Step 3: 커밋**

```bash
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 add tests/release/test_mobile_free_release_contract.py
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 commit -q -m "test(release): pin the mobile-free release contract"
```

---

### Task 2: 스키마 · 검증기 · 픽스처

**Files:**
- Modify: `release-manifests/schema-v1.json:384-428,585-597`
- Modify: `scripts/release/validate_release_manifest.py`
- Modify: `tests/release/fixtures/valid-candidate-spec.json` · `valid-candidate-spec.sha256` · `valid-release.json`

**Interfaces:**
- Produces: `validate_release_manifest` 모듈에서 `SIGNED_MOBILE_BINDING_KEYS`·`SIGNED_MOBILE_BINDING_VERSION`·`SIGNED_MOBILE_WORKFLOW`·`SIGNED_MOBILE_FILES` 가 사라진다(Task 3 이 import 를 정리). `QUALITY_EVIDENCE`·`QUALITY_EVIDENCE_FILES`·`PRODUCER_WORKFLOWS`·`MANUAL_CATALOG_CONTRACTS` 는 이름 유지, `manual-talkback` 항목만 없다.

- [ ] **Step 1: `schema-v1.json` — `qualityCatalogs`**

`"required"` 배열에서 `, "manual-talkback"` 를 지우고, `"manual-nvda": {…}` 줄 끝의 쉼표를 지운 뒤 `"manual-talkback": {…}` 줄을 삭제한다. 결과:

```json
      "required": ["frontend-visual", "home-visual", "frontend-automated-a11y", "home-axe-browser-a11y", "manual-nvda"],
```

```json
        "manual-nvda": {"allOf": [{"$ref": "#/$defs/qualityCatalog"}, {"properties": {"repository": {"const": "DevPathAi/devpath-frontend"}, "path": {"const": "tool/release-evidence/catalogs/manual-nvda.v1.json"}, "case_count": {"const": 2}}}]}
      },
```

- [ ] **Step 2: `schema-v1.json` — `mobileTestArtifacts` 와 `qualityEvidenceInputs`**

`"mobileTestArtifacts": { … },` 정의 전체(397–419행, 닫는 `},` 포함)를 삭제한다. `qualityEvidenceInputs` 를 다음으로 만든다.

```json
    "qualityEvidenceInputs": {
      "type": "object",
      "required": ["catalogs", "frontend_projection_contract"],
      "properties": {
        "catalogs": {"$ref": "#/$defs/qualityCatalogs"},
        "frontend_projection_contract": {"$ref": "#/$defs/frontendProjectionContract"}
      },
      "additionalProperties": false
    },
```

- [ ] **Step 3: `schema-v1.json` — `qualityEvidence`**

```json
    "qualityEvidence": {
      "type": "object",
      "required": ["frontend_visual", "home_visual", "frontend_automated_a11y", "home_axe_browser_a11y", "manual_nvda"],
      "properties": {
        "frontend_visual": {"$ref": "#/$defs/artifact"},
        "home_visual": {"$ref": "#/$defs/homeVisualArtifact"},
        "frontend_automated_a11y": {"$ref": "#/$defs/artifact"},
        "home_axe_browser_a11y": {"$ref": "#/$defs/homeA11yArtifact"},
        "manual_nvda": {"$ref": "#/$defs/manualArtifact"}
      },
      "additionalProperties": false
    },
```

확인:

```bash
py -c "import json,jsonschema; s=json.load(open(r'D:/workspace/dpa/.worktrees/gitops-s2a1/release-manifests/schema-v1.json',encoding='utf-8')); jsonschema.Draft202012Validator.check_schema(s); d=s['\$defs']; assert 'mobileTestArtifacts' not in d; print('schema ok')"
```

Expected: `schema ok`.

- [ ] **Step 4: 검증기 — 상수 테이블**

`scripts/release/validate_release_manifest.py` 에서 다음 세 줄을 삭제한다.

```python
    "manual-talkback": ".github/workflows/mission-spine-manual-at-evidence.yml",
```
```python
    "manual-talkback": "manual_talkback",
```
```python
    "manual-talkback": "evidence.json",
```

`MANUAL_CATALOG_CONTRACTS` 에서 `"manual-talkback": { … },` 항목 전체(283–297행)를 삭제한다. 서명 상수 네 개는 도구로 지운다.

```bash
py "<스크래치패드>/s2a1/delete_top_level.py" D:/workspace/dpa/.worktrees/gitops-s2a1/scripts/release/validate_release_manifest.py \
  SIGNED_MOBILE_BINDING_KEYS SIGNED_MOBILE_BINDING_VERSION SIGNED_MOBILE_WORKFLOW SIGNED_MOBILE_FILES
```

Expected: `validate_release_manifest.py: deleted 4 definitions, 24 lines`(빈 줄 포함이라 ±1 은 허용).

- [ ] **Step 5: 검증기 — `_validate_quality_evidence_inputs`**

exact-key 를 바꾼다.

```python
    _exact_keys(
        obj,
        {"catalogs", "frontend_projection_contract"},
        path,
    )
```

같은 함수의 끝에서 `mobile_path = f"{path}.mobile_test_artifacts"` 로 시작해 `_fail(mobile_path, "build provenance and signed APK hashes must be distinct")` 로 끝나는 블록 전체(1024–1065행)를 삭제한다. 삭제 뒤 이 함수의 마지막 문장은 Home 카탈로그 결속 검사의 `_fail(f"{path}.catalogs", "Home visual and axe/browser evidence must bind the same combined catalog and render provenance", )` 이다.

- [ ] **Step 6: 검증기 — `validate_release_manifest`**

메시지를 고친다(레인이 하나여도 루프는 성립하므로 구조는 그대로).

```python
                f"atomic manual evidence set {field} must match",
```

`signed_mobile = candidate["quality_evidence_inputs"]["mobile_test_artifacts"]` 로 시작해 `"must be distinct from the prebound signed-mobile artifact name", )` 로 끝나는 `for label, artifact in artifacts.items():` 루프까지(1647–1663행)를 삭제한다. 바로 위의 `physical_ids` 구별 검사는 남긴다.

```bash
py -m py_compile D:/workspace/dpa/.worktrees/gitops-s2a1/scripts/release/validate_release_manifest.py && echo compiled
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 grep -nE "SIGNED_MOBILE|mobile_test_artifacts|talkback|signed" -- scripts/release/validate_release_manifest.py
```

Expected: `compiled`, 그리고 grep 출력 없음.

- [ ] **Step 7: 픽스처 수술 + sha 재결속 스크립트**

`<스크래치패드>/s2a1/rebind_fixtures.py`:

```python
"""Remove the legacy blocks from the synthetic fixtures and rebind the candidate sha256."""
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]) / "tests" / "release" / "fixtures"
candidate_path = root / "valid-candidate-spec.json"
release_path = root / "valid-release.json"
sidecar_path = root / "valid-candidate-spec.sha256"


def remove_block(raw: bytes, opener: bytes, closer: bytes) -> bytes:
    """Drop `,<eol><indent>"key": {` … through the first `<eol><indent>}` after it."""
    if raw.count(opener) != 1:
        raise SystemExit(f"{opener!r}: expected exactly one occurrence, found {raw.count(opener)}")
    start = raw.index(opener)
    end = raw.index(closer, start + len(opener)) + len(closer)
    return raw[:start] + raw[end:]


for eol in (b"\r\n", b"\n"):
    if eol in candidate_path.read_bytes():
        break

candidate = candidate_path.read_bytes()
old_sha = hashlib.sha256(candidate).hexdigest()
candidate = remove_block(
    candidate, b"," + eol + b'      "manual-talkback": {', eol + b"      }"
)
candidate = remove_block(
    candidate, b"," + eol + b'    "mobile_test_artifacts": {', eol + b"    }"
)
parsed = json.loads(candidate)
inputs = parsed["quality_evidence_inputs"]
assert set(inputs) == {"catalogs", "frontend_projection_contract"}, set(inputs)
assert "manual-talkback" not in inputs["catalogs"]
candidate_path.write_bytes(candidate)
new_sha = hashlib.sha256(candidate).hexdigest()

release = release_path.read_bytes()
release = remove_block(release, b"," + eol + b'    "manual_talkback": {', eol + b"    }")
assert release.count(old_sha.encode()) == 12, release.count(old_sha.encode())
release = release.replace(old_sha.encode(), new_sha.encode())
assert "manual_talkback" not in json.loads(release)["quality_evidence"]
release_path.write_bytes(release)

sidecar = sidecar_path.read_bytes()
assert sidecar.count(old_sha.encode()) == 1
sidecar_path.write_bytes(sidecar.replace(old_sha.encode(), new_sha.encode()))
print("old", old_sha)
print("new", new_sha)
```

```bash
py "<스크래치패드>/s2a1/rebind_fixtures.py" D:/workspace/dpa/.worktrees/gitops-s2a1
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 diff --stat -- tests/release/fixtures
```

Expected: `old 887a7c38…d60c` 와 새 sha 가 출력된다. diff stat 은 candidate 약 −25줄, release 약 −15줄 · 12줄 치환, sidecar 1줄. **candidate 의 변경이 두 블록 삭제뿐인지 `git diff` 로 직접 읽어 확인한다**(포맷이 통째로 바뀌었으면 스크립트가 잘못 돈 것이다 — `git checkout -- tests/release/fixtures` 로 되돌리고 원인을 분석한다).

- [ ] **Step 8: 표적 검사 — 검증기만 쓰는 새 계약 테스트 3건**

```bash
cd D:/workspace/dpa/.worktrees/gitops-s2a1 && py - <<'PY'
import copy, hashlib, importlib.util, json, sys
from pathlib import Path
import jsonschema
root = Path.cwd(); sys.path.insert(0, str(root / "scripts" / "release"))
spec = importlib.util.spec_from_file_location("v", root / "scripts/release/validate_release_manifest.py")
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
cp = root / "tests/release/fixtures/valid-candidate-spec.json"; rp = root / "tests/release/fixtures/valid-release.json"
c = json.loads(cp.read_text(encoding="utf-8")); r = json.loads(rp.read_text(encoding="utf-8"))
sha = hashlib.sha256(cp.read_bytes()).hexdigest()
s = jsonschema.Draft202012Validator(json.loads((root / "release-manifests/schema-v1.json").read_text(encoding="utf-8")))
s.validate(c); s.validate(r)
v.validate_candidate_spec(copy.deepcopy(c), cp)
v.validate_release_manifest(copy.deepcopy(r), copy.deepcopy(c), sha, rp)
print("validator + schema accept the mobile-free fixtures; labels:", tuple(v.QUALITY_EVIDENCE))
PY
```

Expected: 마지막 줄에 5개 레이블. 예외가 나면 메시지의 경로(`$.…`)를 따라 픽스처·스키마·검증기 중 어긋난 곳을 찾는다.

- [ ] **Step 9: 커밋**

```bash
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 add release-manifests/schema-v1.json scripts/release/validate_release_manifest.py tests/release/fixtures
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 commit -q -m "feat(release)!: drop the signed-mobile binding and TalkBack lane from the release contract

schema_version stays 1 (in-place, as with every prior contract change). Exact-key validation
rejects documents that still carry mobile_test_artifacts or manual-talkback."
```

---

### Task 3: 아티팩트 검증기

**Files:**
- Modify: `scripts/release/verify_release_artifacts.py`

**Interfaces:**
- Consumes: Task 2 가 `validate_release_manifest` 에서 `SIGNED_MOBILE_*` 를 제거했다.
- Produces: 제거되는 공개 이름 — `validate_signed_mobile_provenance` · `validate_signed_mobile_bundle` · `validate_manual_chronology` · `verify_signed_mobile_artifact`(Task 4 가 봉인기의 import 를 정리). `select_unique_protected_producer_run(…, kind)` 의 `kind` 는 `home-dist`·`ai-release-eval`·`privacy-approval`·`frontend-baseline`·`manual` 만 받는다.

- [ ] **Step 1: import 와 상수**

`from validate_release_manifest import (…)` 에서 다음 세 줄을 삭제한다.

```python
    SIGNED_MOBILE_BINDING_VERSION,
    SIGNED_MOBILE_FILES,
    SIGNED_MOBILE_WORKFLOW,
```

`PROTECTED_APPROVAL_CONTRACTS` 에서 두 항목을 삭제한다.

```python
    "signed-mobile-android": (
        "mission-spine-mobile-signing-android",
        "Sign Android release",
    ),
```
```python
    "manual-talkback": (
        "manual-at-talkback",
        "Approve manual TalkBack evidence",
    ),
```

- [ ] **Step 2: 서명 모바일 전용 정의 10개 삭제**

```bash
py "<스크래치패드>/s2a1/delete_top_level.py" D:/workspace/dpa/.worktrees/gitops-s2a1/scripts/release/verify_release_artifacts.py \
  MAX_SIGNED_MOBILE_BINARY_BYTES MAX_SIGNED_MOBILE_ARCHIVE_BYTES SIGNED_MOBILE_PROVENANCE_KEYS \
  validate_signed_mobile_provenance _extract_signed_mobile_archive _download_signed_mobile_archive \
  validate_signed_mobile_bundle validate_manual_chronology _parse_mobile_version verify_signed_mobile_artifact
```

Expected: `deleted 10 definitions`, 약 460줄 감소. (`988661b` 기준 위치: 55·56 · 166–181 · 406–520 · 1128–1216 · 1219–1254 · 1257–1299 · 1439–1453 · 3566–3574 · 3577–3697.)

- [ ] **Step 3: `validate_evidence_payload` 의 TalkBack 분기 두 곳**

extras 분기에서 다음을 삭제한다(`elif label == "manual-nvda":` 와 `else:  # Home labels return above.` 사이).

```python
        elif label == "manual-talkback":
            extras = {
                "assistive_technology", "test_provenance_sha256",
                "build_provenance_sha256", "signed_apk_sha256",
                *PROTECTED_APPROVAL_KEYS,
            }
```

함수 끝 `return` 직전의 다음 블록을 삭제한다.

```python
        if label == "manual-talkback":
            mobile = candidate["quality_evidence_inputs"]["mobile_test_artifacts"]
            for field in ("build_provenance_sha256",):
                if value[field] != mobile[field]:
                    raise ValueError(f"{label} {field} mismatch")
            if value["signed_apk_sha256"] != mobile["signed_apk_sha256"]:
                raise ValueError(f"{label} signed_apk_sha256 mismatch")
```

- [ ] **Step 4: `select_unique_protected_producer_run` 의 `signed-mobile` kind**

```python
        if kind == "signed-mobile":
            return (f"{release_id}-signed-android-build-run-{run_id}-attempt-1",)
```

위 두 줄을 삭제한다. 마지막의 `raise ValueError(f"unknown protected producer kind: {kind}")` 가 이제 `signed-mobile` 을 거부한다.

- [ ] **Step 5: 릴리스 검증 본문의 호출 두 곳**

`verify_manual_catalog_inputs(command_env, candidate)` 바로 아래의 다음 문장을 삭제한다.

```python
        signed_mobile_provenance, signed_mobile_run = verify_signed_mobile_artifact(
            command_env,
            candidate,
            temp / "signed-mobile",
        )
```

`if label in MANUAL_CATALOG_CONTRACTS:` 블록에서 `validate_manual_chronology(…)` 호출만 삭제한다. 결과:

```python
            if label in MANUAL_CATALOG_CONTRACTS:
                claim = {field: payload[field] for field in PROTECTED_APPROVAL_KEYS}
                verify_live_protected_approval(
                    command_env,
                    repository,
                    run_id,
                    artifact["run_attempt"],
                    run,
                    label,
                    claim,
                    expected_head[label],
                )
```

- [ ] **Step 6: 컴파일 · 잔존 · 새로 생긴 미사용 이름**

```bash
py -m py_compile D:/workspace/dpa/.worktrees/gitops-s2a1/scripts/release/verify_release_artifacts.py && echo compiled
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 grep -nE "SIGNED_MOBILE|mobile_test_artifacts|talkback|signed|\.apk|chronology" -- scripts/release/verify_release_artifacts.py
cd D:/workspace/dpa/.worktrees/gitops-s2a1 && py -m pyflakes scripts/release/verify_release_artifacts.py | diff - <(grep verify_release_artifacts "<스크래치패드>/s2a1/baseline-pyflakes.txt") || true
```

Expected: `compiled` · grep 출력 없음 · diff 에 `<` 로 시작하는 줄(=이번 변경으로 새로 생긴 경고)이 있으면 그것이 가리키는 미사용 import(예: `zipfile`·`stat` 가 다른 곳에서 안 쓰이게 된 경우)를 삭제하고 다시 컴파일한다. 기준선에 이미 있던 경고는 건드리지 않는다.

- [ ] **Step 7: 커밋**

```bash
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 add scripts/release/verify_release_artifacts.py
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 commit -q -m "feat(release)!: remove signed-mobile verification and the TalkBack evidence branch

validate_manual_chronology only ordered the manual run after the signed Android build;
it carried no NVDA-specific check, so it is removed with the build."
```

---

### Task 4: 봉인기

**Files:**
- Modify: `scripts/release/seal_release_manifest.py`

**Interfaces:**
- Produces: `_discover_manual_evidence(env, release_id, candidate_hash, candidate) → {"manual_nvda": {...}}` · `_discover_external_artifact(…)` 에서 키워드 인자 `signed_mobile_context` 제거.

- [ ] **Step 1: import**

`from verify_release_artifacts import (…)` 에서 두 줄을 삭제한다.

```python
    validate_manual_chronology,
```
```python
    verify_signed_mobile_artifact,
```

- [ ] **Step 2: `_discover_external_artifact`**

시그니처에서 다음 줄을 삭제한다.

```python
    signed_mobile_context: tuple[dict[str, Any], dict[str, Any]] | None = None,
```

본문의 `if label in MANUAL_CATALOG_CONTRACTS:` 블록에서 서명 문맥 확인과 chronology 호출을 삭제한다. 결과는 다음과 같이 시작한다(`verify_live_protected_approval(` 의 인자는 그대로 둔다).

```python
        if label in MANUAL_CATALOG_CONTRACTS:
            verify_live_protected_approval(
                env,
                repository,
```

- [ ] **Step 3: `_discover_manual_trio` → `_discover_manual_evidence`**

함수 이름을 바꾸고, 매개변수 `signed_mobile_context: tuple[dict[str, Any], dict[str, Any]],` 와 호출 인자 `signed_mobile_context=signed_mobile_context,` 를 삭제한다. 시그니처 결과:

```python
def _discover_manual_evidence(
    env: dict[str, str],
    release_id: str,
    candidate_hash: str,
    candidate: dict[str, Any],
) -> dict[str, dict[str, Any]]:
```

본문의 run 필터·아티팩트 매칭·`"exactly one atomic manual producer run is required"` 는 바꾸지 않는다 — `MANUAL_CATALOG_CONTRACTS` 를 순회하므로 레인 1개로 그대로 동작한다.

- [ ] **Step 4: 봉인 본문**

`verify_manual_catalog_inputs(gh_env, candidate)` 아래의 다음 블록을 삭제한다.

```python
    with tempfile.TemporaryDirectory(prefix="mission-spine-signed-mobile-") as temp_dir:
        signed_mobile_context = verify_signed_mobile_artifact(
            gh_env,
            candidate,
            Path(temp_dir) / "signed-mobile",
        )
```

호출부를 다음으로 바꾼다.

```python
    discovered.update(
        _discover_manual_evidence(
            gh_env,
            args.release_id,
            candidate_hash,
            candidate,
        )
    )
```

- [ ] **Step 5: 컴파일 · 잔존 · 미사용**

```bash
py -m py_compile D:/workspace/dpa/.worktrees/gitops-s2a1/scripts/release/seal_release_manifest.py && echo compiled
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 grep -nE "signed|mobile|talkback|chronology|_trio" -- scripts/release/seal_release_manifest.py
cd D:/workspace/dpa/.worktrees/gitops-s2a1 && py -m pyflakes scripts/release/seal_release_manifest.py | diff - <(grep seal_release_manifest "<스크래치패드>/s2a1/baseline-pyflakes.txt") || true
```

Expected: `compiled` · grep 출력 없음 · 새 경고가 `tempfile imported but unused` 면 `import tempfile` 을 삭제한다(파일의 다른 곳에서 쓰면 경고가 나오지 않는다).

- [ ] **Step 6: 새 계약 테스트 중 검증기·봉인기 부분이 통과하는지 확인**

```bash
cd D:/workspace/dpa/.worktrees/gitops-s2a1 && py -m unittest tests.release.test_mobile_free_release_contract 2>&1 | tail -12
```

Expected: `test_release_contract_sources_carry_no_residue` 의 `README.md` subTest 만 FAIL(Task 6 이 처리), 나머지 6건 PASS.

- [ ] **Step 7: 커밋**

```bash
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 add scripts/release/seal_release_manifest.py
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 commit -q -m "feat(release)!: seal without the signed-mobile context"
```

---

### Task 5: 기존 테스트를 새 계약에 맞춘다 — 전체 스위트 녹색 게이트

**Files:**
- Rename + Modify: `tests/release/test_signed_mobile_manual_trust.py` → `tests/release/test_manual_nvda_trust.py`
- Modify: `tests/release/test_et13_evidence_contract.py`
- Modify: `tests/release/test_release_contract.py:610-614`
- Modify: `tests/release/test_et13_final_rebind.py:328`

- [ ] **Step 1: 이름 변경과 클래스·모듈 이름**

```bash
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 mv tests/release/test_signed_mobile_manual_trust.py tests/release/test_manual_nvda_trust.py
```

파일 안에서 `class SignedMobileManualTrustTest` → `class ManualNvdaTrustTest`, `"signed_mobile_release_validator"` → `"manual_nvda_release_validator"`, `"signed_mobile_artifact_verifier"` → `"manual_nvda_artifact_verifier"`. 더 이상 쓰지 않게 되는 `import tempfile`·`import zipfile` 은 Step 3 뒤에 pyflakes 로 확인해 지운다.

- [ ] **Step 2: 헬퍼**

`_manual_payload` 를 다음으로 바꾼다.

```python
    def _manual_payload(self, label: str) -> dict:
        catalog = self.candidate["quality_evidence_inputs"]["catalogs"][label]
        return {
            "candidate_spec_sha256": self.candidate_sha,
            "status": "passed",
            "producer_run_id": 109,
            "producer_run_attempt": 1,
            "repository": "DevPathAi/devpath-frontend",
            "source_sha": self.candidate["frontend"]["source_sha"],
            "case_catalog_sha256": catalog["sha256"],
            "case_count": catalog["case_count"],
            "passed_case_count": catalog["case_count"],
            "failed_case_count": 0,
            "assistive_technology": "NVDA+Chromium",
            "test_provenance_sha256": catalog["provenance_sha256"],
            **self._approval(label),
        }
```

`_build_provenance` 메서드 전체를 삭제한다. `_manual_catalog_bundle` 의 `entry_points` 는 `content`·`offline_status` 분기가 죽은 코드가 되므로 다음으로 줄인다.

```python
        entry_points = {
            case_id: (
                "today" if case_id.endswith("today-mission-spine") else "next_action"
            )
            for case_id in contract["case_ids"]
        }
```

- [ ] **Step 3: 테스트별 처리**

삭제(메서드 전체): `test_candidate_exactly_binds_one_signed_android_artifact` · `test_signed_mobile_maps_candidate_source_to_producer_head` · `test_signed_mobile_hashes_and_ids_fail_closed` · `test_build_provenance_exactly_binds_toolchain_config_signatures_and_approvals` · `test_signed_bundle_rejects_missing_extra_link_and_hash_drift` · `test_signed_zip_extraction_rejects_traversal_links_and_extras` · `test_signed_android_must_complete_before_manual_approval`.

교체 — `test_protected_attempt_two_is_rejected_but_fresh_attempt_one_is_valid`:

```python
    def test_protected_attempt_two_is_rejected(self):
        payload = self._manual_payload("manual-nvda")
        payload["producer_run_attempt"] = 2
        with self.assertRaisesRegex(ValueError, "attempt must be 1"):
            self.verifier.validate_evidence_payload(
                "manual-nvda", payload, self.candidate_sha, self.candidate, 109, 2
            )
```

교체 — `test_schema_rejects_protected_attempt_two`:

```python
    def test_schema_rejects_protected_attempt_two(self):
        schema = json.loads(
            (ROOT / "release-manifests" / "schema-v1.json").read_text(encoding="utf-8")
        )
        validator = jsonschema.Draft202012Validator(schema)
        release = self._release_bound_to_current_candidate()
        release["quality_evidence"]["manual_nvda"]["run_attempt"] = 2
        with self.assertRaises(jsonschema.ValidationError):
            validator.validate(release)
```

수정 — `test_manual_catalogs_and_static_provenance_are_exact`: 돌연변이 루프의 `"manual-talkback"` 두 곳을 `"manual-nvda"` 로 바꾼다(`entry-point` 돌연변이는 NVDA 첫 케이스 `today` → `content` 라 그대로 실패한다).

교체 — `test_dispatch_workflow_inputs_are_exact`: 변수 `signed` 를 `single` 로, 레이블 `"signed-mobile"` 을 `"single-input"` 으로 바꾼다(레이블은 오류 메시지 접두어일 뿐이다 — `validate_workflow_dispatch_inputs` 실측). 바이트 리터럴의 `name: signed` 도 `name: single` 로.

교체 — `test_manual_names_are_run_attempt_scoped_and_atomic`:

```python
    def test_manual_names_are_run_attempt_scoped(self):
        release_id = self.candidate["release_id"]
        release = self._release_bound_to_current_candidate()
        artifact = release["quality_evidence"]["manual_nvda"]
        self.assertEqual(
            artifact["artifact_name"],
            self.validator.quality_artifact_name(
                "manual-nvda",
                release_id,
                artifact["run_attempt"],
                artifact["workflow_run_id"],
            ),
        )
        self.validator.validate_release_manifest(
            release,
            copy.deepcopy(self.candidate),
            self.candidate_sha,
            RELEASE_FIXTURE,
        )

        retry = self._release_bound_to_current_candidate()
        artifact = retry["quality_evidence"]["manual_nvda"]
        artifact["run_attempt"] = 2
        artifact["artifact_name"] = self.validator.quality_artifact_name(
            "manual-nvda", retry["release_id"], 2, artifact["workflow_run_id"]
        )
        with self.assertRaisesRegex(ValueError, "attempt 1"):
            self.validator.validate_release_manifest(
                retry,
                copy.deepcopy(self.candidate),
                self.candidate_sha,
                RELEASE_FIXTURE,
            )
```

(레인 사이 원자성 하위 루프와 서명 아티팩트 ID 충돌 검사는 비교 대상이 사라져 삭제한다.)

수정 — `test_manual_evidence_requires_exact_protected_approval_claim`: `for label in ("manual-nvda", "manual-talkback"):` → `for label in ("manual-nvda",):`.

교체 — `test_manual_catalog_and_provenance_hashes_cannot_collide`:

```python
    def test_manual_catalog_and_provenance_hashes_cannot_collide(self):
        invalid = copy.deepcopy(self.candidate)
        nvda = invalid["quality_evidence_inputs"]["catalogs"]["manual-nvda"]
        nvda["provenance_sha256"] = nvda["sha256"]
        with self.assertRaisesRegex(ValueError, "hashes must be distinct"):
            self.validator.validate_candidate_spec(invalid, CANDIDATE_FIXTURE)
```

수정 — `test_unique_protected_run_ignores_attempt_two_and_rejects_competing_fresh_run`: `workflow = self.verifier.SIGNED_MOBILE_WORKFLOW` → `workflow = self.validator.PRODUCER_WORKFLOWS["manual-nvda"]`, 두 호출의 `"signed-mobile"` → `"manual"`. (`kind == "manual"` 의 아티팩트 이름은 `<release>-manual-nvda-run-<id>-attempt-1` 이라 헬퍼 `artifacts()` 의 `-run-` 파싱이 그대로 맞는다.)

- [ ] **Step 4: `test_et13_evidence_contract.py`**

`test_candidate_prebinds_exact_catalogs_and_signed_mobile_builds` → 이름을 `test_candidate_prebinds_exact_catalogs` 로 바꾸고: exact-key 집합을 `{"catalogs", "frontend_projection_contract"}` 로, `inputs["mobile_test_artifacts"]` 를 읽는 단언 두 묶음(124–128행)과 함수 끝의 `mobile[...]` 구별 검사 블록(138–142행)을 삭제한다.

182행 `self.assertEqual(inputs["mobile_test_artifacts"]["source_sha"], FINAL_FRONTEND_SHA)` 삭제.

`test_manual_artifact_names_and_workflow_path_are_exact` 의 `("manual_talkback", "artifact_name", "talkback-evidence-copy"),` 줄 삭제.

`_base_payload` 의 수동 분기: `"assistive_technology": {…}[label]` → `"assistive_technology": "NVDA+Chromium"`, 그 아래 `if label == "manual-talkback":` 블록(440–443행) 삭제.

646–654행의 `"invalid key set"` 검사: `"manual-talkback"` → `"manual-nvda"`(a11y 페이로드를 수동 레이블에 넣으면 키 집합 불일치로 거부되는 검사 — 레이블만 바뀐다).

`test_mobile_manual_evidence_binds_exact_signed_artifact_and_build` 메서드 전체 삭제.

`test_producer_workflow_allowlist_is_exact_per_artifact` 의 `expected` 에서 `"manual-talkback": …` 줄 삭제.

**건드리지 않는다:** 이 파일의 `FRONTEND_FIXTURE_IDS`·`FRONTEND_CATALOG_CONTRACTS`(39–40·54·65행)와 543·549행의 표면 개수, 576·635행의 `native_mobile_device` — ET13 리터럴이고 PR ② 의 몫이다.

- [ ] **Step 5: 나머지 두 파일**

`tests/release/test_release_contract.py` — `candidate_data["release_id"] = "ms-20990101-other"` 아래의 다음 다섯 줄을 삭제한다.

```python
            mobile = candidate_data["quality_evidence_inputs"]["mobile_test_artifacts"]
            mobile["artifact_name"] = (
                f'{candidate_data["release_id"]}-signed-android-build-run-'
                f'{mobile["workflow_run_id"]}-attempt-{mobile["run_attempt"]}'
            )
```

`tests/release/test_et13_final_rebind.py` — `self.assertEqual(len(references), 13)` → `self.assertEqual(len(references), 12)`.

- [ ] **Step 6: 전체 스위트 — 녹색 게이트**

```bash
cd D:/workspace/dpa/.worktrees/gitops-s2a1 && py -m unittest discover -s tests/release -p 'test_*.py' 2>&1 | tail -25
```

Expected: 실패는 `test_release_contract_sources_carry_no_residue (path='README.md')` **한 건뿐**. 그 밖의 실패가 있으면 트레이스백을 읽고 원인을 규명한다 — 테스트가 구 모양을 가정한 것이면 이 Task 의 목록에 빠진 것이므로 같은 원칙(서명·TalkBack 의존만 제거, ET13 리터럴은 보존)으로 고치고 PR 본문에 기록하며, 검증기의 동작이 의도와 다르게 바뀐 것이면 Task 2–4 로 돌아가 고친다. 테스트 수가 기준선(`baseline-tests.txt`)에서 줄어든 것은 삭제한 8개 메서드와 새 7개의 차이로 설명돼야 한다.

```bash
cd D:/workspace/dpa/.worktrees/gitops-s2a1 && py -m pyflakes tests/release/test_manual_nvda_trust.py
```

Expected: `tempfile`·`zipfile` 등 미사용 import 경고가 나오면 그 import 를 삭제하고 Step 6 의 첫 명령을 다시 돌린다.

- [ ] **Step 7: 커밋**

```bash
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 add tests/release
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 commit -q -m "test(release): rebase the manual evidence trust tests onto the NVDA-only contract"
```

---

### Task 6: README · 잔존 점검

**Files:**
- Modify: `release-manifests/README.md:10,28,30,31,42,44,93`

- [ ] **Step 1: 문장 단위 수정**

| 행 | 찾기 | 바꾸기 |
|---|---|---|
| 10 | `and six distinct quality-evidence manifests: frontend visual, Home visual, frontend automated accessibility, Home axe/browser accessibility, manual NVDA, and manual TalkBack.` | `and five distinct quality-evidence manifests: frontend visual, Home visual, frontend automated accessibility, Home axe/browser accessibility, and manual NVDA.` |
| 28 | `for all six quality lanes` | `for all five quality lanes` |
| 30 | `- one protected, candidate-prebound signed-Android build …; TalkBack repeats the APK/build pair;` 로 시작·끝나는 항목 한 줄 전체 | (삭제) |
| 31 | `- two frontend-owned authoritative manual-AT catalogs and their raw-byte-bound static test-provenance documents: NVDA has the two approved physical Windows/Chromium Web cases, while TalkBack has the four approved physical-device Today, next-action, content-reading, and stale/offline cases; the catalog/provenance path, lane, AT/client/platform/artifact, ordered case IDs, all-pass policy, and all four distinct input hashes are fail-closed;` | `- one frontend-owned authoritative manual-AT catalog and its raw-byte-bound static test-provenance document: NVDA has the two approved physical Windows/Chromium Web cases; the catalog/provenance path, lane, AT/client/platform/artifact, ordered case IDs, all-pass policy, and both distinct input hashes are fail-closed;` |
| 42 | `Protected baseline approval, Android signing, manual-AT,` | `Protected baseline approval, manual-AT,` |
| 42 | ``The signed artifact is `<release_id>-signed-android-build-run-<run_id>-attempt-1`; the atomic manual pair is `<release_id>-manual-{nvda|talkback}-run-<run_id>-attempt-1`.`` | ``The manual artifact is `<release_id>-manual-nvda-run-<run_id>-attempt-1`.`` |
| 44 | ``The signed-Android GitHub ZIP digest is independently rehashed before a bounded safe extractor rejects traversal, links, special files, duplicates, missing/extra entries, hash drift, and size drift; its only files are `build-provenance.v2.json` and `mobile/android/leva-release.apk`. Signing must finish before any manual run starts. `` | (삭제 — 두 문장과 뒤따르는 공백 하나) |
| 93 | `approved-baseline hashes, signed Android-build hashes, and evidence IDs` | `approved-baseline hashes and evidence IDs` |
| 93 | `all six source-pinned quality results` | `all five source-pinned quality results` |

각 "찾기" 문자열은 파일에 정확히 한 번 나와야 한다. 한 번이 아니면 멈추고 그 줄을 읽어 원인을 확인한다.

- [ ] **Step 2: 전체 스위트와 잔존 점검**

```bash
cd D:/workspace/dpa/.worktrees/gitops-s2a1 && py -m unittest discover -s tests/release -p 'test_*.py' 2>&1 | tail -4
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 grep -niE "talkback|signed[-_ ]?(mobile|android|apk)|mobile_test_artifacts|SIGNED_MOBILE|build-provenance" -- . ':!docs' ':!tests/release/test_mobile_free_release_contract.py'
```

Expected: 첫 명령 `OK`. 둘째 명령은 출력 없음. (`docs/mission-spine/supporting-artifacts/2026-08-15/**` 는 그 날짜의 설계 기록이라 고치지 않는다.)

- [ ] **Step 3: 커밋**

```bash
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 add release-manifests/README.md
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 commit -q -m "docs(release): describe the five-lane, NVDA-only release contract"
```

---

### Task 7: Codex 리뷰 · PR · 머지

**Files:** 없음

- [ ] **Step 1: Codex 리뷰(직렬 1건, frontend 리뷰와 동시에 돌리지 않는다)**

`<스크래치패드>/s2a1/review-prompt.txt`:

```
You are reviewing a supply-chain contract change in the repository at the current directory.
Review ONLY the diff `git diff origin/develop...HEAD`. Do not modify any file.

Context: the web release contract drops the candidate-prebound signed Android build
(quality_evidence_inputs.mobile_test_artifacts) and the manual TalkBack lane. Manual accessibility
evidence becomes NVDA-only; quality evidence goes from six labels to five. schema_version stays 1
on purpose. ET13 frontend fixture literals that mention a "mobile" surface are intentionally left
for a follow-up PR and are out of scope.

Check specifically:
1. Can a candidate spec or release manifest that still carries mobile_test_artifacts, a manual-talkback
   catalog binding, or a manual_talkback artifact pass the Python validator or the JSON Schema?
2. Was any NVDA-side check weakened while removing the TalkBack branches (approval claim, attempt-1 rule,
   live protected approval, catalog/provenance binding, unique protected producer run)?
3. validate_manual_chronology was deleted because it only ordered the manual run after the signed build.
   Confirm from the pre-change code that no NVDA-relevant ordering guarantee was lost.
4. Does seal_release_manifest still require exactly one manual producer run and exactly one active
   artifact per lane?
5. Dangling imports, dead branches, unreachable kinds, or fixtures whose sha256 bindings are inconsistent.
6. Do the new tests prove the negative cases, or do they pass for the wrong reason?

Output: findings with file:line, severity (blocker/major/minor), concrete fix.
End with `VERDICT: approve` or `VERDICT: changes-requested`.
```

```bash
"/c/Users/deepe/AppData/Local/Programs/OpenAI/Codex/bin/codex" exec -s read-only \
  -C D:/workspace/dpa/.worktrees/gitops-s2a1 - \
  < "<스크래치패드>/s2a1/review-prompt.txt" > "<스크래치패드>/s2a1/review.log" 2>&1; echo "CODEX_EXIT=$?"
```

Expected: `CODEX_EXIT=0`. 로그 크기와 끝 40줄을 확인하고, 프롬프트가 에코된 `VERDICT:` 와 Codex 의 판정을 구분한다. 사용 한도 오류면 리뷰 없이 진행하지 말고 사용자에게 보고한다.

- [ ] **Step 2: 지적 재확인과 반영**

지적마다 파일·줄을 직접 열어 사실인지 확인한다. 사실이면 테스트를 먼저 추가하고 고친 뒤 커밋한다. 사실이 아니면 근거와 함께 PR 본문에 "기각" 으로 적는다.

- [ ] **Step 3: push · PR**

```bash
git -C D:/workspace/dpa/.worktrees/gitops-s2a1 push -u origin chore/s2a-drop-signed-mobile-talkback
gh pr create -R DevPathAi/devpath-gitops --base develop --head chore/s2a-drop-signed-mobile-talkback \
  --title "feat(release)!: 릴리스 계약에서 서명 모바일·TalkBack 제거 (S2a ①)" \
  --body-file "<스크래치패드>/s2a1/pr-body.md"
```

PR 본문에 넣을 것: 스펙 경로 · 계약 변화 요약(6 → 5 레이블, `quality_evidence_inputs` 2키, in-place) · **수용한 위험**(main 승격 시점부터 다음 릴리스 승격까지 `ms-20260916-community-ia` 자동 롤백 레인 폐쇄 — 이 PR 은 develop 이라 아직 발효되지 않는다) · 삭제한 함수 목록 · `validate_manual_chronology` 삭제 근거 · Task 6 Step 2 의 grep 결과 · Codex 지적과 처리 · 범위 밖으로 남긴 ET13 리터럴(PR ②) · 마지막 줄 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

- [ ] **Step 4: CI 녹색 확인 후 머지**

```bash
gh pr checks <PR번호> -R DevPathAi/devpath-gitops
gh pr merge <PR번호> -R DevPathAi/devpath-gitops --merge
```

`--watch` 는 쓰지 않는다(504). 전부 `pass` 일 때만 머지한다.

- [ ] **Step 5: 컨트롤러 검증**

```bash
git -C D:/workspace/dpa/devpath-gitops fetch origin
git -C D:/workspace/dpa/devpath-gitops log origin/develop --oneline -10
git -C D:/workspace/dpa/devpath-gitops rev-parse origin/main
git -C D:/workspace/dpa/devpath-gitops status --short --branch | head -3
git -C D:/workspace/dpa/devpath-frontend branch --list 'chore/s2a*'
```

Expected: develop 에 이 PR 의 커밋만 추가됨 · **`origin/main` 은 `4f3ed64…` 그대로**(이 계획은 main 을 건드리지 않는다) · gitops 주 checkout 변경 없음 · 인접 레포에 낯선 브랜치 없음.
