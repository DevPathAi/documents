# S2a PR ② — gitops ET13 계약의 final rebind + 리터럴 → 핀 파일 파생 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gitops 의 ET13 계약(검증기 상수 · JSON Schema `const` · 합성 픽스처 · 골든 파일 · 진단 스냅샷 · 테스트)을 frontend 의 13-fixture 카탈로그와 그 main 커밋에 다시 결속하고, 손으로 적던 fixture 목록·projection matrix·개수·표면 집합을 **바이트 핀 파일에서 파생**하도록 바꾼다.

**Architecture:** `release-manifests/contracts/frontend-et13/` 는 이미 frontend 산출물의 바이트 핀 디렉터리다(골든 5파일, `.gitattributes` 가 `text eol=lf` 로 고정). 여기에 frontend 의 `catalog.v1.json` 과 생성 카탈로그 2개를 더 핀하고, 새 모듈 `frontend_et13_contract.py` 가 import 시점에 세 파일을 sha256 리터럴과 대조한 뒤 값을 파생한다. 검증기의 상수 이름은 유지해 사용처를 고치지 않는다. 파생이 불가능한 JSON Schema `const` 와 합성 픽스처는 값만 갱신하고, 새 대조 테스트가 "핀 파일 == 스키마 const == 픽스처 == 검증기의 독립 재구성"을 잠근다. 런타임의 case 식별자 재구성(`_frontend_expected_case_identity`)은 카탈로그를 믿지 않는 독립 불변식이라 그대로 둔다.

**Tech Stack:** Python 3(`unittest`, `jsonschema==4.25.1`, `PyYAML==6.0.2`) · JSON Schema Draft 2020-12

**Spec:** `docs/superpowers/specs/2026-09-19-s2c2-s2a-drop-signed-mobile-and-gitops-mirror-design.md` §4.2·§8 (documents 레포)

## Global Constraints

- 작업 레포: `DevPathAi/devpath-gitops`. 주 checkout 은 건드리지 않는다. worktree `D:/workspace/dpa/.worktrees/gitops-s2a2`(이하 `$WT`), 브랜치 `feat/s2a-et13-pinned-catalog` ← `origin/develop` → PR 은 `develop`. **`main` 은 이 계획의 범위가 아니다.**
- 모든 git·파일 명령은 절대경로 또는 `git -C <절대경로>`. 테스트는 한 번의 Bash 호출 안에서 `cd <절대경로> && …`.
- **핀 출처(`$PIN`)** = frontend `origin/main` 의 릴리스 머지 커밋(PR DevPathAi/devpath-frontend#226 의 머지 커밋). 사용자 결정(2026-09-19): frontend 를 먼저 main 에 릴리스하고 그 커밋에 결속한다 — 기존 픽스처의 `dbc1cc9…` 도 main 커밋이었고, `et13-evidence.yml` 은 PR 과 main push 에서만 진단 모드로 돌며(`workflow_dispatch` 는 릴리스 입력 7개 필수) PR 실행의 `source_sha` 는 임시 머지 ref 다.
- 핀 3파일의 기대 sha256(2026-09-19 frontend develop `5a47d883` 실측 — Task 0 에서 `$PIN` 에 대해 다시 확인): `catalog.v1.json` `c5acc346a770f5890c6dd06ce616ffc1105eba12b7605e8ad985897e91b00c96` · `generated/visual-cases.v1.json` `acd368d92e9850cb51d67dc2d3cc9a6ae7c96e48f58da28f0e353ca0edc741ce` · `generated/a11y-cases.v1.json` `cf664d46f5e0b0ea9ab789dbf4afca4dbc71778eff0db05779c3a48392622929`. projection `158fdc882238c9459995c0572536a3cec3704e92bd1b28fa2d80907fc0435b78`(= Python `_canonical_sha256(matrix)`, 실측 일치) · 13 fixture · visual 104 `{web 72, admin 16, dp_design 16}` · a11y 26 `{web 18, admin 4, dp_design 4}`.
- **진단 스냅샷의 값은 지어내지 않는다.** `$PIN` 에서 돈 frontend `et13-evidence` 의 `push` 실행 아티팩트 `et13-unsealed-raw-review-run-<id>-attempt-<n>` 에서만 읽는다(필드 대응은 Task 5).
- 픽스처는 손 포맷 JSON 이다 → 텍스트 블록 단위로만 고치고, candidate sha 는 sidecar + release 의 12곳에 재결속한다.
- 이 PC 에서 전체 스위트는 11~15분 걸린다(CI 는 1분 미만). 로컬은 관련 모듈만 돌리고 **전체 스위트 게이트는 PR 의 CI** 다. 무거운 작업을 동시에 돌리지 않는다(사용자가 같은 PC 에서 게임 중, 메모리 압박 실측).
- 파이썬은 `py`. Bash heredoc 안의 백슬래시는 조용히 깨진다 → 스크립트는 Write 도구로 스크래치패드 파일에 쓰고 `py <파일>` 로 실행한다.
- 외부 리뷰: Codex CLI 는 2026-10-19 까지 한도 소진이다. 이 PR 은 공급망 계약 변경이므로 **PR 을 연 뒤 머지 전에 사용자에게 리뷰 방식을 묻는다**(Task 8).

## File Structure

| 파일 | 조치 | 책임 |
|---|---|---|
| `release-manifests/contracts/frontend-et13/catalog.v1.json` · `visual-cases.v1.json` · `a11y-cases.v1.json` | 신규(바이트 복사) | frontend `$PIN` 의 카탈로그와 생성 카탈로그 |
| `release-manifests/contracts/frontend-et13/{catalog,evidence,generated-cases,manifest}.schema.json` | 교체(바이트 복사) | S2c-1 이후 frontend 와 어긋난 골든 스키마 4개 |
| `release-manifests/contracts/frontend-et13/source-pin.v1.json` | 신규 | 핀 출처 레포·커밋과 8파일의 sha256 |
| `release-manifests/contracts/frontend-et13/diagnostic-producer-snapshot.v1.json` | 재생성 | `$PIN` 의 진단 producer 관측값 |
| `scripts/release/frontend_et13_contract.py` | 신규 | 핀 파일 검증 + 파생값(`FIXTURE_IDS`·`PROJECTION_MATRIX`·`PROJECTION_CONTRACT_SHA256`·`CATALOG_SHA256`·`CASES`·`CASE_COUNTS`·`SURFACE_CASE_COUNTS`·`SURFACES`·`GENERATED_SHA256`) |
| `scripts/release/validate_release_manifest.py` | 수정 | `FRONTEND_*` 상수를 파생으로 · 표면 집합 · "12-row" 메시지 |
| `scripts/release/verify_release_artifacts.py` | 수정 | `_validate_surface_counts` 의 표면 집합 · `_frontend_surface` 의 `mobile-` 분기 |
| `release-manifests/schema-v1.json` | 수정 | projection matrix·fixture_ids·case_count·surface_case_counts·projection sha 의 `const` |
| `tests/release/fixtures/*` | 수정 | frontend 결속(소스 SHA·카탈로그 해시·fixture·matrix·개수) + sha 재결속 |
| `tests/release/test_frontend_et13_pinned_contract.py` | 신규 | 대조 테스트 |
| `tests/release/test_et13_final_rebind.py` · `test_et13_evidence_contract.py` · `test_et13_atomic_evidence.py` · `test_release_hardening.py` | 수정 | 리터럴을 파생 모듈에서 읽고, 옛 frontend SHA 를 stale pin 으로 금지 |
| `release-manifests/README.md` | 수정 | 개수·frontend SHA 서술 |

---

### Task 0: worktree · 핀 커밋 · ET13 아티팩트

**Interfaces:**
- Produces: `$WT` · `$PIN`(40자 SHA) · `<스크래치패드>/s2a2/art/`(ET13 아티팩트의 `producer/**` 와 `build-marker.v1.json`) · `<스크래치패드>/s2a2/pin.env`.

- [ ] **Step 1: worktree**

```bash
git -C D:/workspace/dpa/devpath-gitops fetch origin
git -C D:/workspace/dpa/devpath-gitops worktree add -b feat/s2a-et13-pinned-catalog D:/workspace/dpa/.worktrees/gitops-s2a2 origin/develop
git -C D:/workspace/dpa/.worktrees/gitops-s2a2 log -1 --format='%h %s'
```

Expected: `3823ac1 Merge pull request #160 …` 또는 그 뒤. 뒤라면 `git -C $WT diff 3823ac1 HEAD --stat -- scripts/release release-manifests tests/release` 가 비어 있어야 한다. 아니면 멈추고 `NEEDS_CONTEXT`.

- [ ] **Step 2: `$PIN` 확정과 핀 파일 해시 확인**

```bash
export MSYS_NO_PATHCONV=1
F=D:/workspace/dpa/devpath-frontend; git -C $F fetch origin
PIN=$(git -C $F rev-parse origin/main); echo "PIN=$PIN"; git -C $F log -1 --format='%s' $PIN
for p in evidence/et13/catalog.v1.json evidence/et13/generated/visual-cases.v1.json evidence/et13/generated/a11y-cases.v1.json; do echo "$(git -C $F show $PIN:$p | sha256sum | cut -c1-64)  $p"; done
git -C $F ls-tree --name-only $PIN apps/ | tr '\n' ' '
```

Expected: 커밋 제목이 `Merge pull request #226 from DevPathAi/develop` · 세 해시가 Global Constraints 의 값과 같다 · `apps/` 에 `admin`·`web` 만 있다. 해시가 다르면 멈추고 frontend 에서 무엇이 카탈로그를 바꿨는지 규명한다(이 계획의 기대 개수가 틀려진다).

- [ ] **Step 3: `$PIN` 의 ET13 push 실행과 아티팩트**

```bash
gh run list -R DevPathAi/devpath-frontend --workflow et13-evidence.yml --branch main --event push --limit 3 --json databaseId,headSha,conclusion,status -q '.[] | [.databaseId,.headSha,.status,.conclusion] | @tsv'
```

Expected: 첫 줄의 `headSha` 가 `$PIN`, `completed success`. 아직 진행 중이면 끝날 때까지 기다린다(약 10분). 그 실행 id 를 `RUN` 으로 두고:

```bash
S="<스크래치패드>/s2a2"; mkdir -p "$S/art"
gh api repos/DevPathAi/devpath-frontend/actions/runs/$RUN/artifacts -q '.artifacts[] | [.name,.id,.expires_at] | @tsv'
gh run download $RUN -R DevPathAi/devpath-frontend -n et13-unsealed-raw-review-run-$RUN-attempt-1 -D "$S/art"
py -c "import json; [print(k, json.load(open(r'$S/art/producer/%s/evidence.json' % k, encoding='utf-8'))['source_sha']) for k in ('visual','a11y')]"
printf 'PIN=%s\nRUN=%s\n' "$PIN" "$RUN" > "$S/pin.env"
```

Expected: 두 레인의 `source_sha` 가 모두 `$PIN`. 다르면(예: 임시 머지 ref) 이 실행은 스냅샷 출처로 쓸 수 없다 — 멈추고 보고한다.

---

### Task 1: 핀 파일 · 파생 모듈 · 대조 테스트(빨강 → 녹색)

**Files:**
- Create: `release-manifests/contracts/frontend-et13/{catalog.v1.json,visual-cases.v1.json,a11y-cases.v1.json,source-pin.v1.json}`
- Replace: `release-manifests/contracts/frontend-et13/{catalog,evidence,generated-cases,manifest}.schema.json`
- Create: `scripts/release/frontend_et13_contract.py`
- Create: `tests/release/test_frontend_et13_pinned_contract.py`

**Interfaces:**
- Produces(모듈 전역, import 시점에 검증됨):
  - `SOURCE_REPOSITORY: str` · `SOURCE_SHA: str`
  - `FIXTURE_IDS: tuple[str, ...]` · `PROJECTION_MATRIX: list[dict]` · `PROJECTION_CONTRACT_SHA256: str` · `CATALOG_SHA256: str`
  - `GENERATED_SHA256: dict[str, str]`(`"frontend-visual"`·`"frontend-automated-a11y"` → 생성 카탈로그 파일 sha256)
  - `CASES: dict[str, list[dict]]` · `CASE_COUNTS: dict[str, int]` · `SURFACE_CASE_COUNTS: dict[str, dict[str, int]]` · `SURFACES: frozenset[str]`
  - `GOLDEN_SHA256: dict[str, str]`(골든 5파일)

- [ ] **Step 1: 대조 테스트 작성(빨강)**

`tests/release/test_frontend_et13_pinned_contract.py`:

```python
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "release"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
CONTRACT = ROOT / "release-manifests" / "contracts" / "frontend-et13"
SCHEMA = ROOT / "release-manifests" / "schema-v1.json"
CANDIDATE_FIXTURE = ROOT / "tests" / "release" / "fixtures" / "valid-candidate-spec.json"
RELEASE_FIXTURE = ROOT / "tests" / "release" / "fixtures" / "valid-release.json"
LABELS = {
    "frontend-visual": ("visual", "visual-cases.v1.json", "frontendVisualCatalog"),
    "frontend-automated-a11y": ("a11y", "a11y-cases.v1.json", "frontendAutomatedA11yCatalog"),
}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def canonical_sha256(value) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def find_const(node, key):
    """Yield every `{key: {"const": ...}}` value found anywhere under node."""
    if isinstance(node, dict):
        holder = node.get(key)
        if isinstance(holder, dict) and "const" in holder:
            yield holder["const"]
        for value in node.values():
            yield from find_const(value, key)
    elif isinstance(node, list):
        for value in node:
            yield from find_const(value, key)


class FrontendEt13PinnedContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_module(
            SCRIPTS / "frontend_et13_contract.py", "pinned_frontend_et13_contract"
        )
        cls.validator = load_module(
            SCRIPTS / "validate_release_manifest.py", "pinned_contract_validator"
        )
        cls.verifier = load_module(
            SCRIPTS / "verify_release_artifacts.py", "pinned_contract_verifier"
        )
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        cls.candidate = json.loads(CANDIDATE_FIXTURE.read_text(encoding="utf-8"))
        cls.release = json.loads(RELEASE_FIXTURE.read_text(encoding="utf-8"))
        cls.source_pin = json.loads(
            (CONTRACT / "source-pin.v1.json").read_text(encoding="utf-8")
        )

    def test_every_pinned_file_matches_the_recorded_source_pin(self):
        self.assertEqual(self.source_pin["schema_version"], "leva.et13.source-pin.v1")
        self.assertEqual(self.source_pin["repository"], "DevPathAi/devpath-frontend")
        self.assertRegex(self.source_pin["source_sha"], r"^[0-9a-f]{40}$")
        self.assertEqual(self.source_pin["source_sha"], self.contract.SOURCE_SHA)
        self.assertEqual(
            set(self.source_pin["files"]),
            {
                "catalog.v1.json",
                "visual-cases.v1.json",
                "a11y-cases.v1.json",
                "catalog.schema.json",
                "evidence.schema.json",
                "generated-cases.schema.json",
                "manifest.schema.json",
                "release-bundle.v1.json",
            },
        )
        for name, entry in self.source_pin["files"].items():
            with self.subTest(name=name):
                self.assertEqual(set(entry), {"source_path", "sha256"})
                self.assertTrue(entry["source_path"].startswith("evidence/et13/"))
                raw = (CONTRACT / name).read_bytes()
                self.assertNotIn(b"\r", raw)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), entry["sha256"])

    def test_pinned_catalog_and_generated_cases_agree(self):
        contract = self.contract
        catalog = json.loads((CONTRACT / "catalog.v1.json").read_text(encoding="utf-8"))
        self.assertEqual(
            hashlib.sha256((CONTRACT / "catalog.v1.json").read_bytes()).hexdigest(),
            contract.CATALOG_SHA256,
        )
        self.assertEqual(catalog["projection_matrix"], contract.PROJECTION_MATRIX)
        self.assertEqual(
            canonical_sha256(contract.PROJECTION_MATRIX),
            contract.PROJECTION_CONTRACT_SHA256,
        )
        self.assertEqual(
            [row["fixture_id"] for row in contract.PROJECTION_MATRIX],
            list(contract.FIXTURE_IDS),
        )
        self.assertNotIn("mobile", contract.SURFACES)
        self.assertFalse([f for f in contract.FIXTURE_IDS if f.startswith("mobile-")])
        for label, (_, filename, _) in LABELS.items():
            with self.subTest(label=label):
                generated = json.loads((CONTRACT / filename).read_text(encoding="utf-8"))
                self.assertEqual(generated["catalog_sha256"], contract.CATALOG_SHA256)
                self.assertEqual(generated["fixture_ids"], list(contract.FIXTURE_IDS))
                self.assertEqual(generated["cases"], contract.CASES[label])
                self.assertEqual(len(generated["cases"]), contract.CASE_COUNTS[label])
                self.assertEqual(
                    sum(contract.SURFACE_CASE_COUNTS[label].values()),
                    contract.CASE_COUNTS[label],
                )
                self.assertEqual(
                    set(contract.SURFACE_CASE_COUNTS[label]), set(contract.SURFACES)
                )

    def test_validator_constants_are_derived_from_the_pinned_files(self):
        contract, validator = self.contract, self.validator
        self.assertEqual(tuple(validator.FRONTEND_FIXTURE_IDS), contract.FIXTURE_IDS)
        self.assertEqual(validator.FRONTEND_PROJECTION_MATRIX, contract.PROJECTION_MATRIX)
        self.assertEqual(
            validator.FRONTEND_PROJECTION_CONTRACT_SHA256,
            contract.PROJECTION_CONTRACT_SHA256,
        )
        for label in LABELS:
            with self.subTest(label=label):
                lane = validator.FRONTEND_CATALOG_CONTRACTS[label]
                self.assertEqual(lane["case_count"], contract.CASE_COUNTS[label])
                self.assertEqual(
                    lane["surface_case_counts"], contract.SURFACE_CASE_COUNTS[label]
                )
                self.assertEqual(
                    lane["projection_contract_sha256"],
                    contract.PROJECTION_CONTRACT_SHA256,
                )

    def test_verifier_reconstructs_the_pinned_case_identities_independently(self):
        for label in LABELS:
            with self.subTest(label=label):
                pinned = [
                    (case["fixture_id"], case["case_id"], case["artifact_path"])
                    for case in self.contract.CASES[label]
                ]
                self.assertEqual(
                    self.verifier._frontend_expected_case_identity(label), pinned
                )
                owners = {
                    self.verifier._frontend_surface(case["fixture_id"])
                    for case in self.contract.CASES[label]
                }
                self.assertEqual(owners, set(self.contract.SURFACES))

    def test_json_schema_consts_equal_the_pinned_values(self):
        defs = self.schema["$defs"]
        self.assertEqual(
            list(find_const(self.schema, "projection_matrix")),
            [self.contract.PROJECTION_MATRIX],
        )
        shas = list(find_const(self.schema, "projection_contract_sha256"))
        self.assertGreaterEqual(len(shas), 3)
        self.assertEqual(set(shas), {self.contract.PROJECTION_CONTRACT_SHA256})
        for label, (_, _, definition) in LABELS.items():
            with self.subTest(label=label):
                lane = defs[definition]
                self.assertEqual(
                    list(find_const(lane, "fixture_ids")), [list(self.contract.FIXTURE_IDS)]
                )
                self.assertEqual(
                    list(find_const(lane, "case_count")), [self.contract.CASE_COUNTS[label]]
                )
                self.assertEqual(
                    list(find_const(lane, "surface_case_counts")),
                    [self.contract.SURFACE_CASE_COUNTS[label]],
                )

    def test_synthetic_fixtures_bind_the_pinned_source_and_catalogs(self):
        contract = self.contract
        self.assertEqual(self.candidate["frontend"]["source_sha"], contract.SOURCE_SHA)
        inputs = self.candidate["quality_evidence_inputs"]
        projection = inputs["frontend_projection_contract"]
        self.assertEqual(projection["projection_matrix"], contract.PROJECTION_MATRIX)
        self.assertEqual(
            projection["projection_contract_sha256"], contract.PROJECTION_CONTRACT_SHA256
        )
        for label in LABELS:
            with self.subTest(label=label):
                catalog = inputs["catalogs"][label]
                self.assertEqual(catalog["source_sha"], contract.SOURCE_SHA)
                self.assertEqual(catalog["sha256"], contract.GENERATED_SHA256[label])
                self.assertEqual(catalog["fixture_ids"], list(contract.FIXTURE_IDS))
                self.assertEqual(catalog["case_count"], contract.CASE_COUNTS[label])
                self.assertEqual(
                    catalog["surface_case_counts"], contract.SURFACE_CASE_COUNTS[label]
                )
        for key, artifact in self.release["quality_evidence"].items():
            if key.startswith(("frontend_", "manual_")):
                self.assertEqual(artifact["head_sha"], contract.SOURCE_SHA, key)

    def test_a_tampered_pinned_file_fails_closed_on_import(self):
        source = (SCRIPTS / "frontend_et13_contract.py").read_text(encoding="utf-8")
        self.assertIn("hashlib.sha256", source)
        tampered = dict(self.contract.PINNED_SHA256)
        tampered["catalog.v1.json"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "catalog.v1.json"):
            self.contract.load_contract(CONTRACT, tampered)


if __name__ == "__main__":
    unittest.main()
```

```bash
cd D:/workspace/dpa/.worktrees/gitops-s2a2 && py -m unittest tests.release.test_frontend_et13_pinned_contract 2>&1 | grep -E "^(ERROR|FAIL|OK|FAILED|Ran)|Error:" | head
```

Expected: setUpClass ERROR(`frontend_et13_contract.py` 없음). 커밋: `test(release): pin the frontend ET13 contract against byte-pinned files`.

- [ ] **Step 2: 핀 파일 복사와 `source-pin.v1.json`**

`<스크래치패드>/s2a2/copy_pins.py`:

```python
"""Byte-copy the frontend ET13 contract files at PIN into the gitops contract directory."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

frontend, pin, worktree = sys.argv[1], sys.argv[2], Path(sys.argv[3])
contract = worktree / "release-manifests" / "contracts" / "frontend-et13"
files = {
    "catalog.v1.json": "evidence/et13/catalog.v1.json",
    "visual-cases.v1.json": "evidence/et13/generated/visual-cases.v1.json",
    "a11y-cases.v1.json": "evidence/et13/generated/a11y-cases.v1.json",
    "catalog.schema.json": "evidence/et13/catalog.schema.json",
    "evidence.schema.json": "evidence/et13/evidence.schema.json",
    "generated-cases.schema.json": "evidence/et13/generated-cases.schema.json",
    "manifest.schema.json": "evidence/et13/manifest.schema.json",
    "release-bundle.v1.json": "evidence/et13/release-bundle.v1.json",
}
if len(pin) != 40:
    raise SystemExit("PIN must be a full 40-character commit SHA")
entries = {}
for name, source_path in files.items():
    raw = subprocess.run(
        ["git", "-C", frontend, "cat-file", "blob", f"{pin}:{source_path}"],
        check=True, capture_output=True,
    ).stdout
    if b"\r" in raw or not raw:
        raise SystemExit(f"{source_path}: blob is empty or carries CR bytes")
    (contract / name).write_bytes(raw)
    entries[name] = {"source_path": source_path, "sha256": hashlib.sha256(raw).hexdigest()}
pin_document = {
    "schema_version": "leva.et13.source-pin.v1",
    "repository": "DevPathAi/devpath-frontend",
    "source_sha": pin,
    "files": entries,
}
(contract / "source-pin.v1.json").write_bytes(
    (json.dumps(pin_document, indent=2) + "\n").encode("utf-8")
)
for name, entry in entries.items():
    print(entry["sha256"], name)
```

```bash
. "<스크래치패드>/s2a2/pin.env"
py "<스크래치패드>/s2a2/copy_pins.py" D:/workspace/dpa/devpath-frontend $PIN D:/workspace/dpa/.worktrees/gitops-s2a2
git -C D:/workspace/dpa/.worktrees/gitops-s2a2 status --short -- release-manifests/contracts
```

Expected: 8줄의 해시(핀 3파일은 Global Constraints 의 값) · status 에 신규 4개(`catalog.v1.json`·두 생성 카탈로그·`source-pin.v1.json`)와 수정 4개(스키마). `release-bundle.v1.json` 은 바이트가 같아 status 에 나오지 않는다.

- [ ] **Step 3: 파생 모듈**

`scripts/release/frontend_et13_contract.py` — `PINNED_SHA256` 의 8개 값(이 모듈에 남는 **유일한 리터럴**)은 2026-09-19 frontend develop `5a47d883` 에서 계산한 것이다 — Step 2 의 출력과 한 글자도 다르지 않아야 하고, 다르면 Step 2 의 출력이 정답이다(그 경우 무엇이 바뀌었는지 먼저 규명한다).

```python
"""Frontend ET13 contract values derived from byte-pinned producer files.

GitOps trusts only the bytes it has approved. The files under
release-manifests/contracts/frontend-et13/ are byte copies of the frontend producer's
catalog at one source commit; every value the release validators need is derived from
them after their SHA-256 has been checked against the literals below. Rebinding to a new
frontend catalog means copying the files and updating these hashes — nothing else here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CONTRACT_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "release-manifests"
    / "contracts"
    / "frontend-et13"
)
PINNED_SHA256 = {
    "catalog.v1.json": "c5acc346a770f5890c6dd06ce616ffc1105eba12b7605e8ad985897e91b00c96",
    "visual-cases.v1.json": "acd368d92e9850cb51d67dc2d3cc9a6ae7c96e48f58da28f0e353ca0edc741ce",
    "a11y-cases.v1.json": "cf664d46f5e0b0ea9ab789dbf4afca4dbc71778eff0db05779c3a48392622929",
    "catalog.schema.json": "8e0bee6a1f99f2293c7fed5a4b19d89f855cc51da47793c9f88336daf7013726",
    "evidence.schema.json": "acf5b914d1a45838772bac5f9e912534343931e36be51f742cdf6bc3172032c1",
    "generated-cases.schema.json": "86d26364027e1e3a2bf178754ede042096f738c203220b83e6fc0d9c4ff1e8a7",
    "manifest.schema.json": "e201fd195299ed7eddea7ceeaa2ee15eadfab634a49a284b4c23d13defdff5eb",
    "release-bundle.v1.json": "b46cbc3903924267dfa9d44ea66d138ecceee22195c96c0f4fc29b0db6cfd411",
}
GENERATED_FILES = {
    "frontend-visual": "visual-cases.v1.json",
    "frontend-automated-a11y": "a11y-cases.v1.json",
}
_SURFACE_BY_OWNER = {"web": "web", "admin": "admin", "dp_design": "dp_design"}


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_pinned(directory: Path, name: str, expected_sha256: str) -> tuple[bytes, Any]:
    raw = (directory / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(f"pinned frontend ET13 contract file {name} SHA-256 mismatch")
    return raw, json.loads(raw.decode("utf-8"))


def load_contract(directory: Path, pinned_sha256: dict[str, str]) -> dict[str, Any]:
    """Verify every pinned file and derive the contract; any inconsistency fails closed."""
    documents = {
        name: _read_pinned(directory, name, expected)
        for name, expected in pinned_sha256.items()
    }
    source_pin = json.loads((directory / "source-pin.v1.json").read_text(encoding="utf-8"))
    recorded = {name: entry["sha256"] for name, entry in source_pin["files"].items()}
    if recorded != pinned_sha256:
        raise ValueError("source-pin.v1.json does not record the pinned file hashes")

    catalog_raw, catalog = documents["catalog.v1.json"]
    catalog_sha256 = hashlib.sha256(catalog_raw).hexdigest()
    matrix = catalog["projection_matrix"]
    projection_sha256 = catalog["projection_contract_sha256"]
    if _canonical_sha256(matrix) != projection_sha256:
        raise ValueError("pinned projection matrix does not hash to its contract SHA-256")
    fixture_ids = tuple(row["fixture_id"] for row in matrix)
    if len(set(fixture_ids)) != len(fixture_ids):
        raise ValueError("pinned projection matrix repeats a fixture")

    cases: dict[str, list[dict[str, Any]]] = {}
    case_counts: dict[str, int] = {}
    surface_case_counts: dict[str, dict[str, int]] = {}
    generated_sha256: dict[str, str] = {}
    for label, name in GENERATED_FILES.items():
        raw, generated = documents[name]
        if (
            generated["catalog_sha256"] != catalog_sha256
            or generated["projection_contract_sha256"] != projection_sha256
            or generated["projection_matrix"] != matrix
            or tuple(generated["fixture_ids"]) != fixture_ids
        ):
            raise ValueError(f"pinned {name} disagrees with the pinned catalog")
        lane_cases = generated["cases"]
        counted: dict[str, int] = {}
        for case in lane_cases:
            surface = _SURFACE_BY_OWNER[case["owner"]]
            counted[surface] = counted.get(surface, 0) + 1
        if (
            generated["case_count"] != len(lane_cases)
            or generated["surface_case_counts"] != counted
        ):
            raise ValueError(f"pinned {name} case counts are not self-consistent")
        cases[label] = lane_cases
        case_counts[label] = len(lane_cases)
        surface_case_counts[label] = dict(generated["surface_case_counts"])
        generated_sha256[label] = hashlib.sha256(raw).hexdigest()

    surfaces = frozenset().union(*(set(counts) for counts in surface_case_counts.values()))
    return {
        "source_repository": source_pin["repository"],
        "source_sha": source_pin["source_sha"],
        "fixture_ids": fixture_ids,
        "projection_matrix": matrix,
        "projection_contract_sha256": projection_sha256,
        "catalog_sha256": catalog_sha256,
        "generated_sha256": generated_sha256,
        "cases": cases,
        "case_counts": case_counts,
        "surface_case_counts": surface_case_counts,
        "surfaces": surfaces,
    }


_CONTRACT = load_contract(CONTRACT_DIRECTORY, PINNED_SHA256)
SOURCE_REPOSITORY: str = _CONTRACT["source_repository"]
SOURCE_SHA: str = _CONTRACT["source_sha"]
FIXTURE_IDS: tuple[str, ...] = _CONTRACT["fixture_ids"]
PROJECTION_MATRIX: list[dict[str, Any]] = _CONTRACT["projection_matrix"]
PROJECTION_CONTRACT_SHA256: str = _CONTRACT["projection_contract_sha256"]
CATALOG_SHA256: str = _CONTRACT["catalog_sha256"]
GENERATED_SHA256: dict[str, str] = _CONTRACT["generated_sha256"]
CASES: dict[str, list[dict[str, Any]]] = _CONTRACT["cases"]
CASE_COUNTS: dict[str, int] = _CONTRACT["case_counts"]
SURFACE_CASE_COUNTS: dict[str, dict[str, int]] = _CONTRACT["surface_case_counts"]
SURFACES: frozenset[str] = _CONTRACT["surfaces"]
GOLDEN_SHA256: dict[str, str] = {
    name: PINNED_SHA256[name]
    for name in (
        "catalog.schema.json",
        "evidence.schema.json",
        "generated-cases.schema.json",
        "manifest.schema.json",
        "release-bundle.v1.json",
    )
}
```

작성 전에 `owner` 값의 집합이 `{web, admin, dp_design}` 이고 `surface_case_counts` 의 키와 같은 이름인지 핀 파일에서 확인한다.

```bash
py -c "import json; d=json.load(open(r'D:/workspace/dpa/.worktrees/gitops-s2a2/release-manifests/contracts/frontend-et13/visual-cases.v1.json',encoding='utf-8')); print(sorted({c['owner'] for c in d['cases']}), sorted(d['surface_case_counts']))"
```

Expected: `['admin', 'dp_design', 'web'] ['admin', 'dp_design', 'web']`. 다르면 `_SURFACE_BY_OWNER` 대신 `artifact_path` 의 두 번째 경로 요소(`visual/<surface>/…`)에서 표면을 읽도록 그 한 곳을 고친다.

```bash
cd D:/workspace/dpa/.worktrees/gitops-s2a2 && py -c "import sys; sys.path.insert(0,'scripts/release'); import frontend_et13_contract as c; print(len(c.FIXTURE_IDS), c.CASE_COUNTS, c.SURFACE_CASE_COUNTS, sorted(c.SURFACES), c.PROJECTION_CONTRACT_SHA256[:12])"
```

Expected: `13 {'frontend-visual': 104, 'frontend-automated-a11y': 26} {… web 72/18 …} ['admin', 'dp_design', 'web'] 158fdc882238`. 커밋: `feat(release): derive the frontend ET13 contract from byte-pinned producer files`.

이 시점의 대조 테스트: `test_every_pinned_file…`·`test_pinned_catalog…`·`test_a_tampered…` 3건 PASS, 나머지 4건 FAIL(Task 2~4 가 처리).

---

### Task 2: 검증기와 아티팩트 검증기 — 리터럴을 파생으로

**Files:**
- Modify: `scripts/release/validate_release_manifest.py:98-239,780,878`
- Modify: `scripts/release/verify_release_artifacts.py:243-244,1119-1126`

- [ ] **Step 1: 검증기 상수**

import 블록 끝에 `import frontend_et13_contract` 를 추가한다(같은 디렉터리의 형제 모듈 — `verify_release_artifacts.py` 가 `from validate_release_manifest import …` 하는 방식과 같다). `FRONTEND_FIXTURE_IDS = ( … )`(98–111행) · `FRONTEND_PROJECTION_CONTRACT_SHA256 = ( … )`(114–116행) · `FRONTEND_PROJECTION_MATRIX = [ … ]`(117–214행)를 다음 세 줄로 바꾼다.

```python
FRONTEND_FIXTURE_IDS = frontend_et13_contract.FIXTURE_IDS
FRONTEND_PROJECTION_CONTRACT_SHA256 = frontend_et13_contract.PROJECTION_CONTRACT_SHA256
FRONTEND_PROJECTION_MATRIX = frontend_et13_contract.PROJECTION_MATRIX
```

(`FRONTEND_PROJECTION_CONTRACT_VERSION` 은 그대로 둔다.) `FRONTEND_CATALOG_CONTRACTS` 의 두 레인에서 개수 두 줄씩을 바꾼다.

```python
        "case_count": frontend_et13_contract.CASE_COUNTS["frontend-visual"],
        "surface_case_counts": frontend_et13_contract.SURFACE_CASE_COUNTS["frontend-visual"],
```
```python
        "case_count": frontend_et13_contract.CASE_COUNTS["frontend-automated-a11y"],
        "surface_case_counts": frontend_et13_contract.SURFACE_CASE_COUNTS["frontend-automated-a11y"],
```

- [ ] **Step 2: 메시지와 표면 집합**

```python
        _fail(projection_path, "projection contract must contain the exact ordered approved matrix")
```

`_exact_keys(surface_counts, {"web", "admin", "mobile", "dp_design"}, …)` 의 집합 리터럴을 `frontend_et13_contract.SURFACES` 로 바꾼다.

- [ ] **Step 3: 아티팩트 검증기**

`_validate_surface_counts` 의 `{"web", "admin", "mobile", "dp_design"}` → `set(FRONTEND_CATALOG_CONTRACTS["frontend-visual"]["surface_case_counts"])`(이 모듈이 이미 import 하는 이름에서 읽는다 — 두 레인의 키 집합이 같음은 파생 모듈이 보장한다). `_frontend_surface` 에서 다음 두 줄을 삭제한다.

```python
    if fixture_id.startswith("mobile-"):
        return "mobile"
```

`_frontend_expected_case_identity` 와 `validate_frontend_evidence_bundle` 의 프로필 재구성은 **바꾸지 않는다.**

- [ ] **Step 4: 확인**

```bash
cd D:/workspace/dpa/.worktrees/gitops-s2a2 && py -m py_compile scripts/release/validate_release_manifest.py scripts/release/verify_release_artifacts.py && py -m pyflakes scripts/release/validate_release_manifest.py scripts/release/verify_release_artifacts.py scripts/release/frontend_et13_contract.py
git -C D:/workspace/dpa/.worktrees/gitops-s2a2 grep -nE "mobile|12-row" -- scripts/release/validate_release_manifest.py scripts/release/verify_release_artifacts.py
cd D:/workspace/dpa/.worktrees/gitops-s2a2 && py -m unittest tests.release.test_frontend_et13_pinned_contract 2>&1 | grep -E "^(ERROR|FAIL|OK|FAILED|Ran)"
```

Expected: pyflakes 출력 없음 · grep 출력 없음 · 대조 테스트는 `validator_constants`·`verifier_reconstructs` 가 추가로 PASS(5 PASS / 2 FAIL). 커밋: `refactor(release): read the frontend ET13 literals from the pinned contract`.

---

### Task 3: JSON Schema `const`

**Files:**
- Modify: `release-manifests/schema-v1.json:303-359`

- [ ] **Step 1: 스크립트로 갱신**

`<스크래치패드>/s2a2/update_schema.py`:

```python
"""Rewrite the ET13 consts in schema-v1.json from the pinned contract (format preserving)."""
import json
import sys
from pathlib import Path

worktree = Path(sys.argv[1])
sys.path.insert(0, str(worktree / "scripts" / "release"))
import frontend_et13_contract as contract  # noqa: E402

path = worktree / "release-manifests" / "schema-v1.json"
raw = path.read_bytes()
eol = "\r\n" if b"\r\n" in raw else "\n"
text = raw.decode("utf-8").replace("\r\n", "\n")
OLD_SHA = "c66d08b6425628a06b27d07e08d648cfb3568d9db7c8d8aca2371172ccf4bde3"


def once(old: str, new: str, count: int = 1) -> None:
    global text
    if text.count(old) != count:
        raise SystemExit(f"expected {count} occurrence(s), found {text.count(old)}: {old[:70]!r}")
    text = text.replace(old, new)


once(OLD_SHA, contract.PROJECTION_CONTRACT_SHA256, 3)

marker = '          {"fixture_id": "web-today-available"'
start = text.index(marker)
end = text.index("\n        ]", start)
rows = ",\n".join("          " + json.dumps(row, ensure_ascii=False) for row in contract.PROJECTION_MATRIX)
text = text[:start] + rows + text[end:]

old_ids = '"fixture_ids": {"const": ["web-today-available", "web-path-current-week", "web-content-reading", "web-workspace-idle", "web-review-loaded", "web-mentor-context-preview", "admin-kpi-dashboard", "admin-support-long-wire", "mobile-today-available", "mobile-content-reading", "dp-design-mission-ledger", "dp-design-context-payload-preview"]}'
once(old_ids, '"fixture_ids": {"const": ' + json.dumps(list(contract.FIXTURE_IDS)) + "}", 2)

for label, old_count, old_surfaces in (
    ("frontend-visual", 96, '{"web": 48, "admin": 16, "mobile": 16, "dp_design": 16}'),
    ("frontend-automated-a11y", 24, '{"web": 12, "admin": 4, "mobile": 4, "dp_design": 4}'),
):
    once(f'"case_count": {{"const": {old_count}}}', f'"case_count": {{"const": {contract.CASE_COUNTS[label]}}}')
    once(
        '"surface_case_counts": {"const": ' + old_surfaces + "}",
        '"surface_case_counts": {"const": ' + json.dumps(contract.SURFACE_CASE_COUNTS[label]) + "}",
    )

json.loads(text)
path.write_bytes(text.replace("\n", eol).encode("utf-8"))
print("schema consts updated")
```

```bash
py "<스크래치패드>/s2a2/update_schema.py" D:/workspace/dpa/.worktrees/gitops-s2a2
git -C D:/workspace/dpa/.worktrees/gitops-s2a2 diff --stat -- release-manifests/schema-v1.json
git -C D:/workspace/dpa/.worktrees/gitops-s2a2 grep -nE "mobile|c66d08b6" -- release-manifests/schema-v1.json
py -c "import json,jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open(r'D:/workspace/dpa/.worktrees/gitops-s2a2/release-manifests/schema-v1.json',encoding='utf-8'))); print('schema ok')"
```

Expected: `schema consts updated` · diff 는 매트릭스 12 → 13행과 const 7곳 · grep 출력 없음 · `schema ok`. `git diff` 를 직접 읽어 매트릭스 행의 서식(키 순서 `fixture_id, capture_scope, source_widget, substitutions`, 한 행 한 줄)이 기존과 같은지 확인한다. 대조 테스트의 `json_schema_consts` 가 PASS. 커밋: `feat(release): bind the JSON Schema ET13 consts to the 13-fixture catalog`.

---

### Task 4: 합성 픽스처의 frontend 재결속

**Files:**
- Modify: `tests/release/fixtures/valid-candidate-spec.json` · `valid-candidate-spec.sha256` · `valid-release.json`

- [ ] **Step 1: 스크립트**

`<스크래치패드>/s2a2/rebind_fixtures.py`:

```python
"""Rebind the synthetic fixtures to the pinned frontend source and 13-fixture catalog."""
import hashlib
import json
import sys
from pathlib import Path

worktree = Path(sys.argv[1])
sys.path.insert(0, str(worktree / "scripts" / "release"))
import frontend_et13_contract as contract  # noqa: E402

fixtures = worktree / "tests" / "release" / "fixtures"
candidate_path = fixtures / "valid-candidate-spec.json"
release_path = fixtures / "valid-release.json"
sidecar_path = fixtures / "valid-candidate-spec.sha256"
OLD_FRONTEND = "dbc1cc9010dea56471e8eec462a0c52cee946d15"
OLD_PROJECTION = "c66d08b6425628a06b27d07e08d648cfb3568d9db7c8d8aca2371172ccf4bde3"
OLD_CASE_SHA = {
    "frontend-visual": "1f21427cec099ba1d5465d0207fd3f8261084d1e69d94827f02fa44341272e1b",
    "frontend-automated-a11y": "2a76815be997178a6eeb9d54eb609a998fec33538803fd94e44127bdf390897c",
}


def replace_json_value(text: str, key_line: str, value, occurrence_count: int) -> str:
    """Replace the JSON array/object that follows `key_line` (bracket matched), re-indented."""
    if text.count(key_line) != occurrence_count:
        raise SystemExit(f"{key_line!r}: expected {occurrence_count}, found {text.count(key_line)}")
    position = 0
    for _ in range(occurrence_count):
        start = text.index(key_line, position)
        indent = len(key_line) - len(key_line.lstrip(" "))
        opener_at = start + len(key_line) - 1
        opener = text[opener_at]
        closer = {"[": "]", "{": "}"}[opener]
        depth, cursor, in_string = 0, opener_at, False
        while True:
            char = text[cursor]
            if in_string:
                if char == "\\":
                    cursor += 1
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    break
            cursor += 1
        rendered = json.dumps(value, indent=2, ensure_ascii=False).replace("\n", "\n" + " " * indent)
        text = text[:opener_at] + rendered + text[cursor + 1:]
        position = opener_at + len(rendered)
    return text


raw = candidate_path.read_bytes()
eol = "\r\n" if b"\r\n" in raw else "\n"
old_sha = hashlib.sha256(raw).hexdigest()
text = raw.decode("utf-8").replace("\r\n", "\n")

if text.count(OLD_FRONTEND) != 7:
    raise SystemExit(f"frontend SHA occurrences: {text.count(OLD_FRONTEND)}")
text = text.replace(OLD_FRONTEND, contract.SOURCE_SHA)
if text.count(OLD_PROJECTION) != 3:
    raise SystemExit(f"projection SHA occurrences: {text.count(OLD_PROJECTION)}")
text = text.replace(OLD_PROJECTION, contract.PROJECTION_CONTRACT_SHA256)
for label, old in OLD_CASE_SHA.items():
    if text.count(old) != 1:
        raise SystemExit(f"{label} generated-cases SHA occurrences: {text.count(old)}")
    text = text.replace(old, contract.GENERATED_SHA256[label])

text = replace_json_value(text, '      "projection_matrix": [', contract.PROJECTION_MATRIX, 1)
text = replace_json_value(text, '        "fixture_ids": [', list(contract.FIXTURE_IDS), 2)

parsed = json.loads(text)
catalogs = parsed["quality_evidence_inputs"]["catalogs"]
for label in ("frontend-visual", "frontend-automated-a11y"):
    lane = catalogs[label]
    old_count = f'"case_count": {lane["case_count"]},'
    old_surfaces = json.dumps(lane["surface_case_counts"], indent=2).replace("\n", "\n        ")
    block_start = text.index(f'      "{label}": {{')
    block_end = text.index("\n      }", block_start)
    block = text[block_start:block_end]
    if block.count(old_count) != 1 or block.count('"surface_case_counts": ' + old_surfaces) != 1:
        raise SystemExit(f"{label}: count/surface block not found exactly once")
    block = block.replace(old_count, f'"case_count": {contract.CASE_COUNTS[label]},')
    new_surfaces = json.dumps(contract.SURFACE_CASE_COUNTS[label], indent=2).replace("\n", "\n        ")
    block = block.replace('"surface_case_counts": ' + old_surfaces, '"surface_case_counts": ' + new_surfaces)
    text = text[:block_start] + block + text[block_end:]

parsed = json.loads(text)
inputs = parsed["quality_evidence_inputs"]
assert inputs["frontend_projection_contract"]["projection_matrix"] == contract.PROJECTION_MATRIX
for label in ("frontend-visual", "frontend-automated-a11y"):
    lane = inputs["catalogs"][label]
    assert lane["fixture_ids"] == list(contract.FIXTURE_IDS)
    assert lane["case_count"] == contract.CASE_COUNTS[label]
    assert lane["surface_case_counts"] == contract.SURFACE_CASE_COUNTS[label]
    assert lane["sha256"] == contract.GENERATED_SHA256[label]
candidate = text.replace("\n", eol).encode("utf-8")
candidate_path.write_bytes(candidate)
new_sha = hashlib.sha256(candidate).hexdigest()

release = release_path.read_bytes()
if release.count(OLD_FRONTEND.encode()) != 3 or release.count(old_sha.encode()) != 12:
    raise SystemExit("release fixture occurrence counts are not the expected 3 / 12")
release = release.replace(OLD_FRONTEND.encode(), contract.SOURCE_SHA.encode()).replace(old_sha.encode(), new_sha.encode())
json.loads(release)
release_path.write_bytes(release)

sidecar = sidecar_path.read_bytes()
assert sidecar.count(old_sha.encode()) == 1
sidecar_path.write_bytes(sidecar.replace(old_sha.encode(), new_sha.encode()))
print("old", old_sha)
print("new", new_sha)
```

```bash
py "<스크래치패드>/s2a2/rebind_fixtures.py" D:/workspace/dpa/.worktrees/gitops-s2a2
git -C D:/workspace/dpa/.worktrees/gitops-s2a2 diff --stat -- tests/release/fixtures
git -C D:/workspace/dpa/.worktrees/gitops-s2a2 grep -nE "mobile|dbc1cc9|c66d08b6" -- tests/release/fixtures
```

Expected: `old 552507ff…` 와 새 sha · grep 출력 없음. **`git diff` 로 candidate 의 변경이 frontend SHA 7곳 · projection SHA 3곳 · case sha 2곳 · 매트릭스 · fixture_ids 2곳 · 개수 4곳뿐인지 직접 읽는다.** 표면 개수 블록의 서식이 기존 다른 객체와 다르게 나오면(`old_surfaces` 가 안 맞아 스크립트가 멈추면) 그 블록의 실제 텍스트를 읽어 `old_surfaces` 조립을 그 서식에 맞춘다.

- [ ] **Step 2: 확인과 커밋**

```bash
cd D:/workspace/dpa/.worktrees/gitops-s2a2 && py -m unittest tests.release.test_frontend_et13_pinned_contract tests.release.test_mobile_free_release_contract 2>&1 | grep -E "^(ERROR|FAIL|OK|FAILED|Ran)"
```

Expected: `OK`(대조 테스트 7건 전부 + ① 의 계약 테스트 8건). 커밋: `test(release): rebind the synthetic fixtures to the pinned frontend release`.

---

### Task 5: 진단 스냅샷 · final rebind 테스트

**Files:**
- Regenerate: `release-manifests/contracts/frontend-et13/diagnostic-producer-snapshot.v1.json`
- Modify: `tests/release/test_et13_final_rebind.py:18-61`

- [ ] **Step 1: 스냅샷 재생성**

필드 대응(2026-09-19 아티팩트 실측): `generated_cases_sha256` = `evidence.case_catalog_sha256`(= 생성 카탈로그 파일의 sha256) · `input_provenance_sha256` = `evidence.input_provenance_sha256` · `input_provenance_file_sha256` = sha256(`provenance.v1.json`) · `result_manifest_sha256` = sha256(`<lane>-manifest.v1.json`) · `evidence_file_sha256` = sha256(`evidence.json`) · `candidate_spec_sha256` = sha256(`review-candidate.v1.json`) · `assets_lock_sha256`/`renderer_lock_sha256` = frontend `$PIN` 의 `evidence/et13/{assets,renderer}.lock.json` sha256.

`<스크래치패드>/s2a2/make_snapshot.py`:

```python
"""Regenerate diagnostic-producer-snapshot.v1.json from one frontend ET13 diagnostic run."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

frontend, pin, artifact, worktree = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
sys.path.insert(0, str(worktree / "scripts" / "release"))
import frontend_et13_contract as contract  # noqa: E402

if contract.SOURCE_SHA != pin:
    raise SystemExit("PIN differs from the pinned contract source")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob(path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", frontend, "cat-file", "blob", f"{pin}:{path}"], check=True, capture_output=True
    ).stdout


lanes = {}
for kind, label, manifest in (
    ("visual", "frontend-visual", "visual-manifest.v1.json"),
    ("a11y", "frontend-automated-a11y", "a11y-manifest.v1.json"),
):
    base = artifact / "producer" / kind
    evidence_raw = (base / "evidence.json").read_bytes()
    evidence = json.loads(evidence_raw)
    provenance_raw = (base / "provenance.v1.json").read_bytes()
    manifest_raw = (base / manifest).read_bytes()
    candidate_raw = (base / "review-candidate.v1.json").read_bytes()
    checks = {
        "source_sha": evidence["source_sha"] == pin,
        "mode": evidence["evidence_mode"] == "diagnostic" and evidence["status"] == "passed",
        "cases": evidence["case_catalog_sha256"] == contract.GENERATED_SHA256[label],
        "projection": evidence["projection_contract_sha256"] == contract.PROJECTION_CONTRACT_SHA256,
        "provenance_file": evidence["input_provenance_file_sha256"] == sha256(provenance_raw),
        "manifest": evidence["result_manifest_sha256"] == sha256(manifest_raw),
        "candidate": evidence["candidate_spec_sha256"] == sha256(candidate_raw),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise SystemExit(f"{kind}: artifact is not a coherent diagnostic run of PIN: {failed}")
    lane = {
        "generated_cases_path": f"evidence/et13/generated/{kind}-cases.v1.json",
        "generated_cases_sha256": evidence["case_catalog_sha256"],
        "input_provenance_sha256": evidence["input_provenance_sha256"],
        "input_provenance_file_sha256": sha256(provenance_raw),
        "result_manifest_path": f"artifacts/et13/{manifest}",
        "result_manifest_sha256": sha256(manifest_raw),
        "evidence_file_path": "evidence.json",
        "evidence_file_sha256": sha256(evidence_raw),
        "candidate_spec_sha256": sha256(candidate_raw),
        "status": "passed",
        "evidence_mode": "diagnostic",
    }
    if kind == "visual":
        if evidence["baseline_status"] != "pending_external_review":
            raise SystemExit("visual diagnostic run must be pending_external_review")
        lane.update({"baseline_status": "pending_external_review", "baseline_set_sha256": None, "baseline_approval_sha256": None})
    lanes[kind] = lane

path = worktree / "release-manifests" / "contracts" / "frontend-et13" / "diagnostic-producer-snapshot.v1.json"
previous = json.loads(path.read_text(encoding="utf-8"))
snapshot = {
    "schema_version": "leva.et13.diagnostic-snapshot.v1",
    "contract_use": "diagnostic_observation_only",
    "sealable": False,
    "repository": "DevPathAi/devpath-frontend",
    "source_sha": pin,
    "capture_surface": "flutter_web_release_projection",
    "device_evidence": False,
    "catalog_sha256": contract.CATALOG_SHA256,
    "projection_contract_sha256": contract.PROJECTION_CONTRACT_SHA256,
    "assets_lock_sha256": sha256(blob("evidence/et13/assets.lock.json")),
    "renderer_lock_sha256": sha256(blob("evidence/et13/renderer.lock.json")),
    "lanes": lanes,
    "release_blockers": ["protected_baseline_approval", "canonical_candidate_rerun"],
}
if list(snapshot) != list(previous) or list(snapshot["lanes"]["visual"]) != list(previous["lanes"]["visual"]):
    raise SystemExit("snapshot key order drifted from the committed document")
path.write_bytes((json.dumps(snapshot, indent=2) + "\n").encode("utf-8"))
for kind, lane in lanes.items():
    print(kind, json.dumps({k: v for k, v in lane.items() if k.endswith("sha256")}, indent=1))
print("assets", snapshot["assets_lock_sha256"], "renderer", snapshot["renderer_lock_sha256"])
```

```bash
. "<스크래치패드>/s2a2/pin.env"
py "<스크래치패드>/s2a2/make_snapshot.py" D:/workspace/dpa/devpath-frontend $PIN "<스크래치패드>/s2a2/art" D:/workspace/dpa/.worktrees/gitops-s2a2
git -C D:/workspace/dpa/.worktrees/gitops-s2a2 diff --stat -- release-manifests/contracts/frontend-et13/diagnostic-producer-snapshot.v1.json
```

Expected: 두 레인의 해시와 `assets eb6f4dfd… renderer af71b829…`(2026-09-19 develop 실측값 — `$PIN` 에서 다르면 스크립트 출력이 정답이다). 기존 문서의 들여쓰기·줄 끝과 다르게 써졌으면(`git diff` 가 값 이외의 줄을 바꾸면) 기존 파일의 서식을 읽어 `json.dumps` 인자를 맞춘다.

- [ ] **Step 2: `test_et13_final_rebind.py` 의 상수를 파생으로**

18–61행의 리터럴 블록에서 frontend 관련 상수를 다음으로 바꾼다(AI·documents 상수 `AI_*`·`DOCUMENTS_*` 는 그대로).

```python
import frontend_et13_contract  # noqa: E402  (SCRIPTS is already on sys.path above)

SNAPSHOT = json.loads(
    (CONTRACT / "diagnostic-producer-snapshot.v1.json").read_text(encoding="utf-8")
)
FRONTEND_SHA = frontend_et13_contract.SOURCE_SHA
DIAGNOSTIC_FRONTEND_SHA = frontend_et13_contract.SOURCE_SHA
CATALOG_SHA = frontend_et13_contract.CATALOG_SHA256
PROJECTION_SHA = frontend_et13_contract.PROJECTION_CONTRACT_SHA256
ASSETS_LOCK_SHA = "eb6f4dfdd108781ebf4e2a44f9f5489ca1b8db6f611a0b907f41fe8c24051378"  # make_snapshot.py 출력과 대조
RENDERER_LOCK_SHA = "af71b829ec7ba56a5a89ca2e11ea940136b70153cbd4f995c725d047d98cf20b"  # make_snapshot.py 출력과 대조
```

`LANES` 의 두 레인은 `case_sha` 를 `frontend_et13_contract.GENERATED_SHA256[<label>]` 로, 나머지 다섯 값(`canonical_provenance_sha`·`raw_provenance_sha`·`manifest_sha`·`evidence_sha`·`local_candidate_sha`)을 `make_snapshot.py` 가 출력한 해시로 적는다 — 이 다섯은 **관측값의 독립 고정**이라 스냅샷 파일에서 읽지 않고 리터럴로 둔다(스냅샷이 몰래 바뀌면 테스트가 잡아야 한다). `GOLDEN_HASHES = dict(frontend_et13_contract.GOLDEN_SHA256)`.

`import frontend_et13_contract` 는 파일 상단의 `sys.path.insert` 뒤에 둔다. `SNAPSHOT` 은 쓰지 않으면 넣지 않는다.

- [ ] **Step 3: 확인과 커밋**

```bash
cd D:/workspace/dpa/.worktrees/gitops-s2a2 && py -m unittest tests.release.test_et13_final_rebind 2>&1 | grep -E "^(ERROR|FAIL|OK|FAILED|Ran)"
```

Expected: `OK`. 커밋: `test(release): rebind the ET13 final-rebind contract and diagnostic snapshot`.

---

### Task 6: 나머지 테스트의 리터럴

**Files:**
- Modify: `tests/release/test_et13_evidence_contract.py:21,24,30-69,543,549`
- Modify: `tests/release/test_et13_atomic_evidence.py:22-36,38-136,144-145,153-154,185-192`
- Modify: `tests/release/test_release_hardening.py:820-823,905,1522,1550`

- [ ] **Step 1: `test_et13_evidence_contract.py`**

```python
import frontend_et13_contract  # noqa: E402

FINAL_FRONTEND_SHA = frontend_et13_contract.SOURCE_SHA
STALE_FRONTEND_SHAS = (
    "a18aee3d31e61dcd3935" "17ef68125224eeb76c7a",
    "dbc1cc9010dea56471e8" "eec462a0c52cee946d15",
)
FRONTEND_FIXTURE_IDS = list(frontend_et13_contract.FIXTURE_IDS)
FRONTEND_PROJECTION_SHA256 = frontend_et13_contract.PROJECTION_CONTRACT_SHA256
```

`FRONTEND_CATALOG_CONTRACTS` 의 `case_count`·`surface_case_counts` 네 줄을 `frontend_et13_contract.CASE_COUNTS[…]`·`SURFACE_CASE_COUNTS[…]` 로. 기존 `STALE_FRONTEND_SHA` 단일 상수는 `STALE_FRONTEND_SHAS` 튜플로 바꾸고, `test_final_source_rebind_is_exact_and_removes_every_stale_pin` 의 stale 루프가 튜플의 두 값을 모두 금지하게 한다(옛 SHA 는 문자열을 둘로 쪼개 적는다 — 이 테스트 파일 자신이 잔존 검사에 걸리지 않게 하는 기존 관례). 543·549행의 "표면 개수 1 어긋남" 돌연변이는 리터럴 대신 파생값에서 만든다.

```python
        def drifted(counts):
            mutated = dict(counts)
            first, second = sorted(mutated)[:2]
            mutated[first] -= 1
            mutated[second] += 1
            return mutated
```

을 그 테스트 메서드 안에 두고, `{"web": 47, "admin": 17, "mobile": 16, "dp_design": 16}` → `drifted(frontend_et13_contract.SURFACE_CASE_COUNTS["frontend-visual"])`, a11y 도 같은 방식으로.

- [ ] **Step 2: `test_et13_atomic_evidence.py`**

`FIXTURE_IDS`·`PROJECTION_MATRIX`·`PROJECTION_SHA256` 를 파생 모듈에서 읽고(`sys.path.insert` 가 파일에 없으면 `test_et13_final_rebind.py` 와 같은 세 줄을 상단에 추가), `LANES` 의 `count`·`surfaces` 를 `CASE_COUNTS`·`SURFACE_CASE_COUNTS` 로, `surface_for` 의 `mobile-` 분기 두 줄을 삭제한다. 이 파일의 `generated_cases()` 가 프로필을 곱해 합성 카탈로그를 만드는 방식은 그대로 둔다 — fixture 수가 13 이 되면 개수가 104·26 으로 맞는지가 곧 검증이다.

- [ ] **Step 3: `test_release_hardening.py`**

820–823행과 905행의 개수·표면 리터럴을 같은 메서드가 이미 읽고 있는 candidate 픽스처에서 읽는다.

```python
            "case_count": self.candidate["quality_evidence_inputs"]["catalogs"]["frontend-visual"]["case_count"],
            "passed_case_count": self.candidate["quality_evidence_inputs"]["catalogs"]["frontend-visual"]["case_count"],
            "surface_case_counts": dict(self.candidate["quality_evidence_inputs"]["catalogs"]["frontend-visual"]["surface_case_counts"]),
```

(a11y 쪽도 같은 방식으로 `frontend-automated-a11y` 에서.) 1522·1550행의 `"dbc1cc9…"` 는 `self.candidate["frontend"]["source_sha"]` 가 아니라 **파생 모듈의 `SOURCE_SHA`** 로 바꾼다 — 이 테스트는 "픽스처가 정식 소스 핀에 묶였는가"를 보므로 기대값이 픽스처 자신이면 동어반복이 된다. 파일 상단에 `sys.path` 보정과 `import frontend_et13_contract` 를 추가한다.

- [ ] **Step 4: 관련 모듈 실행 · 잔존 점검 · 커밋**

```bash
cd D:/workspace/dpa/.worktrees/gitops-s2a2 && py -m unittest tests.release.test_frontend_et13_pinned_contract tests.release.test_et13_final_rebind tests.release.test_et13_evidence_contract tests.release.test_et13_atomic_evidence tests.release.test_mobile_free_release_contract tests.release.test_manual_nvda_trust tests.release.test_release_contract 2>&1 | grep -E "^(ERROR|FAIL|OK|FAILED|Ran)"
git -C D:/workspace/dpa/.worktrees/gitops-s2a2 grep -nE "\"mobile\"|mobile-today|mobile-content|c66d08b6|fa9067a4|1f21427c|2a76815b|dbc1cc9010dea56471e8eec462a0c52cee946d15" -- scripts tests release-manifests
```

Expected: `OK` · grep 출력 없음(`test_release_hardening.py` 는 무거워 CI 에서 확인한다 — `py -m py_compile` 과 `pyflakes` 는 로컬에서 통과시킨다). 커밋: `test(release): read the ET13 literals from the pinned contract`.

---

### Task 7: README

**Files:**
- Modify: `release-manifests/README.md:28,92`

- [ ] **Step 1**: 28행의 `the visual catalog is exactly 96 cases (`Web` 48, `Admin` 16, `Mobile` 16, `dp_design` 16), and automated accessibility is exactly 24 (`Web` 12, `Admin` 4, `Mobile` 4, `dp_design` 4);` 를 다음으로 바꾼다.

```
the visual catalog is exactly 104 cases (`Web` 72, `Admin` 16, `dp_design` 16), and automated accessibility is exactly 26 (`Web` 18, `Admin` 4, `dp_design` 4) — these counts, the fixture list, and the projection matrix are derived from the byte-pinned producer files under `release-manifests/contracts/frontend-et13/`, never retyped;
```

같은 행의 `and their `Mobile` cases are Flutter-web projections, never native-device evidence;` 는 `and every case is a Flutter-web projection, never native-device evidence;` 로. 92행의 `including frontend `dbc1cc9010dea56471e8eec462a0c52cee946d15`` 는 `$PIN` 으로, `The five producer-owned golden files are byte-pinned` 는 `The eight producer-owned files (five schemas/bundle plus the catalog and both generated case catalogs) are byte-pinned, with their source commit and hashes recorded in `source-pin.v1.json`` 로 바꾼다. 각 "찾기" 문자열은 정확히 한 번 나와야 한다.

- [ ] **Step 2**: `git grep -nE "96 cases|exactly 24|Mobile|dbc1cc9" -- release-manifests/README.md` 출력 없음 확인. 커밋: `docs(release): describe the pinned 13-fixture ET13 contract`.

---

### Task 8: PR · CI · 리뷰 · 머지

- [ ] **Step 1: push · PR**(`--base develop`). 본문: 스펙 경로 · `$PIN`·ET13 실행 id · 핀 8파일 해시 · 파생으로 바뀐 상수와 **런타임에 남긴 독립 재구성** · 진단 스냅샷의 필드 대응과 출처 · 잔존 점검 결과 · "main 은 건드리지 않았다" · 마지막 줄 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 2: CI**(`mission-spine-release-contract` 가 전체 스위트) 통과를 로그의 `Ran N tests … OK` 로 확인한다. `--watch` 는 쓰지 않는다.
- [ ] **Step 3: 리뷰 방식을 사용자에게 묻는다.** Codex 는 2026-10-19 까지 불가, 서브에이전트 리뷰는 이 PC 에서 빈 응답이다(2026-09-19 실측 2회). 선택지: (a) 직접 검증 + CI 로 develop 머지(main 승격 전에 독립 리뷰를 다시 시도), (b) 사용자가 Codex 플랜을 올린 뒤 리뷰, (c) 사용자가 직접 diff 확인. 답을 받기 전에는 머지하지 않는다.
- [ ] **Step 4: 머지 뒤 컨트롤러 검증** — develop 에 이 PR 의 커밋만 추가 · **`origin/main` 불변** · 주 checkout 불변 · 인접 레포에 낯선 브랜치 없음 · worktree 와 머지된 브랜치 정리(worktree 제거 전에 셸 cwd 를 밖으로 옮긴다).

---

## 범위 밖 (다음 계획)

gitops `release/s2a-main-promotion`: main 에서 분기해 ①+② 의 경로만 옮기고(`git diff origin/develop -- <경로>` 0 확인) squash PR → 전제조건 충족 뒤 **해제 직전 1회 사용자 확인** → 최소 해제 → 머지 → 스냅샷대로 재봉인 → `validate_authority_state` 로 봉인 형상 검증. 그 뒤 ET13 baseline 봇 디스패치·사람 승인 → candidate → 증거 → seal → promote → landing-last.
