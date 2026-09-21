# gitops main 파이프라인 결함 3건 publisher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** JVM 서비스 8개의 `startupProbe` · fence ServiceAccount 의 `imagePullSecrets` · landing-last 의 `/api/*` smoke 를 한 target 커밋으로 만들어 one-shot publisher 로 gitops `main` 에 올릴 준비를 끝낸다(Part A). 실행(Part B)은 사용자 확인 1회 뒤.

**Architecture:** 2026-09-21 에 실행된 fence 제거 publisher(`origin/chore/r2-writer-fence-removal-publish-20260921` = `8e42f757`)에서 **정확한 횟수의 치환**으로 헬퍼·계약 테스트·실행 스크립트를 파생한다. target 은 `MAIN_SHA` 의 단일 자식이고 고정 타임스탬프·봇 신원으로 결정적으로 재현된다. 롤아웃 직렬화는 publisher 밖의 클러스터 절차다.

**Tech Stack:** Python 3(`py`, 로컬 3.14 / 러너 3.13) · PyYAML · jsonschema 4.25.1 · kubectl v1.36(kustomize 내장) · GitHub Actions · `gh` CLI · actionlint v1.7.12(`D:/workspace/dpa/.worktrees/_tools/actionlint/`)

**Spec:** `docs/superpowers/specs/2026-09-20-gitops-main-promotion-via-publisher-design.md` §12 (틀은 §4·§5·§11)

## Global Constraints

- `MAIN_SHA` = `30c0e9f717efaad9bd46d47721a61495f4093e96`(r3 mission-on). `origin/main` 이 여기서 움직이면 **핀 전부 무효 — 멈추고 재계획**.
- gitops 로컬 체크아웃(`D:/workspace/dpa/devpath-gitops`)은 다른 작업 브랜치에 있다 — **건드리지 않는다.** 모든 작업은 절대경로 워크트리에서, git 은 `-C <절대경로>` 로.
- `startupProbe` 값은 글자 그대로: `httpGet {path: /actuator/health/liveness, port: 8080}` · `periodSeconds: 5` · `timeoutSeconds: 3` · `failureThreshold: 60`. 기존 `readinessProbe`·`livenessProbe` 는 한 글자도 바꾸지 않는다.
- smoke 경로는 `/api/invite-rounds` 하나(GET, 리다이렉트 없음, 200, 본문 ≤ 65536 바이트, UTF-8 JSON).
- target 의 변경 경로는 정확히 12행(§Task 2 의 목록). 그 밖의 경로가 바뀌면 실패다.
- 봇 신원: `devpath-gitops-release[bot]` / `244265210+devpath-gitops-release[bot]@users.noreply.github.com`. 고정 날짜 `1789995600 +0000`(2026-09-21T13:00:00Z).
- 브랜치명: target `fix/pipeline-defects-main-20260921` · 헬퍼 `chore/pipeline-defects-publish-20260921` · staged 디스패처 `chore/pipeline-defects-publish-dispatcher-staged-20260921` · 방아쇠 `automation/dispatch-pipeline-defects-main-publish`(**Part B 까지 만들지 않는다 — 그 이름으로 push 하는 것이 실행이다**).
- 계약 테스트 파일명 `tests/release/test_pipeline_defects_main_publish.py`. 워크플로 파일은 선례와 같이 `.github/workflows/mission-spine-auth-smoke.yml` 을 덮어쓴다(`workflow_dispatch` 는 기본 브랜치에 같은 이름의 워크플로가 있어야 한다).
- Windows 함정: 스크립트는 Write 도구로 파일에 쓴다(heredoc 은 백슬래시를 망친다) · Git Bash 에서 `rev:.github/…` 인자는 `MSYS_NO_PATHCONV=1` · gitops 검증기 로컬 실행은 `PYTHONUTF8=1` · `py -B`(documents 는 `__pycache__` 를 ignore 하지 않는다) · bare `bash` 는 WSL 로 풀릴 수 있다 → `DRYRUN_BASH="C:/Program Files/Git/bin/bash.exe"`.
- Part A 는 운영에 닿지 않는다: 클러스터에는 읽기만, gitops 에는 `main`·`automation/*` 이 아닌 브랜치 push 만.

스크립트 디렉터리: `docs/superpowers/plans/2026-09-21-gitops-main-pipeline-defects-via-publisher/`(이하 `PLAN_DIR`). 선례 디렉터리: `docs/superpowers/plans/2026-09-21-gitops-main-writer-fence-removal-via-publisher/`(이하 `PREC_DIR`).

---

### Task 1: target 의 내용을 TDD 로 만든다 (로컬 개발 브랜치, push 안 함)

**Files:**
- Create: `tests/release/test_production_startup_budget.py`
- Modify: `apps/devpath-{platform,learning,ai,community,notification,lcs,sandbox}-svc/base/deployment.yaml` · `apps/devpath-gateway/base/deployment.yaml`
- Modify: `apps/devpath-migration/base/writer-fence-rbac.yaml`
- Modify: `scripts/release/cloudflare_pages.py`(`_probe` 뒤에 `_probe_api`, `verify-new-production` 분기)
- Modify: `tests/release/test_cloudflare_api.py`
- Create: `PLAN_DIR/insert_startup_probe.py`

**Interfaces:**
- Produces: 로컬 브랜치 `dev/pipeline-defects-content`(워크트리 `D:/workspace/dpa/.worktrees/gitops-pipeline-defects-dev`)의 HEAD — Task 2 가 이 커밋의 12개 경로 blob 을 읽는다. `cloudflare_pages._probe_api(origin: str) -> None`(실패 시 `ValueError`).

- [ ] **Step 1: 워크트리** — `git -C D:/workspace/dpa/devpath-gitops worktree add -b dev/pipeline-defects-content D:/workspace/dpa/.worktrees/gitops-pipeline-defects-dev 30c0e9f717efaad9bd46d47721a61495f4093e96`
- [ ] **Step 2: 기준선** — 워크트리에서 `PYTHONUTF8=1 py -B -m unittest discover -s tests/release -p 'test_*.py'` 의 건수와 결과를 기록한다(이후 회귀 판정의 기준).
- [ ] **Step 3: 실패하는 테스트 — 매니페스트**

```python
# tests/release/test_production_startup_budget.py
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPRING_SERVICES = (
    "devpath-ai-svc",
    "devpath-community-svc",
    "devpath-gateway",
    "devpath-lcs-svc",
    "devpath-learning-svc",
    "devpath-notification-svc",
    "devpath-platform-svc",
    "devpath-sandbox-svc",
)
RBAC = ROOT / "apps" / "devpath-migration" / "base" / "writer-fence-rbac.yaml"


def _service_container(service: str) -> dict:
    document = yaml.safe_load(
        (ROOT / "apps" / service / "base" / "deployment.yaml").read_text(encoding="utf-8")
    )
    containers = [
        container
        for container in document["spec"]["template"]["spec"]["containers"]
        if container["name"] == service
    ]
    if len(containers) != 1:
        raise AssertionError(f"{service} must have exactly one container named after the service")
    return containers[0]


class ProductionStartupBudgetTest(unittest.TestCase):
    def test_spring_services_have_a_production_startup_budget(self):
        # Without a startupProbe the liveness probe (20s delay + 3 x 10s) kills a JVM that needs
        # more than ~50s to start - the 2026-09-21 herd: several JVMs starting on one 4-CPU node.
        for service in SPRING_SERVICES:
            probe = _service_container(service).get("startupProbe")
            self.assertIsNotNone(probe, service)
            self.assertEqual(
                probe["httpGet"], {"path": "/actuator/health/liveness", "port": 8080}, service
            )
            self.assertGreaterEqual(probe["periodSeconds"] * probe["failureThreshold"], 300, service)
            self.assertLessEqual(probe["periodSeconds"], 10, service)
            self.assertGreaterEqual(probe["timeoutSeconds"], 3, service)

    def test_steady_state_probes_are_unchanged(self):
        for service in SPRING_SERVICES:
            container = _service_container(service)
            self.assertEqual(
                container["readinessProbe"],
                {
                    "httpGet": {"path": "/actuator/health/readiness", "port": 8080},
                    "initialDelaySeconds": 10,
                },
                service,
            )
            self.assertEqual(
                container["livenessProbe"],
                {
                    "httpGet": {"path": "/actuator/health/liveness", "port": 8080},
                    "initialDelaySeconds": 20,
                },
                service,
            )

    def test_migration_fence_service_account_declares_its_pull_secret(self):
        # The migration Job pulls a private ghcr.io image with this ServiceAccount. Until
        # 2026-09-21 the secret existed only as a manual cluster patch.
        documents = list(yaml.safe_load_all(RBAC.read_text(encoding="utf-8")))
        account = documents[0]
        self.assertEqual(
            (account["kind"], account["metadata"]["name"]),
            ("ServiceAccount", "devpath-migration-fence"),
        )
        self.assertEqual(account["imagePullSecrets"], [{"name": "ghcr-pull"}])
        self.assertIs(account["automountServiceAccountToken"], False)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: RED 확인** — `py -B -m unittest discover -s tests/release -p 'test_production_startup_budget.py'` → 1번·3번 테스트 FAIL(`startupProbe` 없음 / `imagePullSecrets` KeyError), 2번은 PASS.
- [ ] **Step 5: 삽입 스크립트**(손 편집 8회 대신 — 바이트 단위로 같은 변경을 보장)

```python
# PLAN_DIR/insert_startup_probe.py
#!/usr/bin/env python3
"""Insert the staging-proven startupProbe before readinessProbe in the eight Spring Deployments,
and declare the ghcr pull secret on the migration fence ServiceAccount. Exact, counted edits."""

from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1])
SERVICES = (
    "devpath-ai-svc", "devpath-community-svc", "devpath-gateway", "devpath-lcs-svc",
    "devpath-learning-svc", "devpath-notification-svc", "devpath-platform-svc", "devpath-sandbox-svc",
)
ANCHOR = (
    "          readinessProbe:\n"
    "            httpGet:\n"
    "              path: /actuator/health/readiness\n"
)
PROBE = (
    "          startupProbe:\n"
    "            httpGet:\n"
    "              path: /actuator/health/liveness\n"
    "              port: 8080\n"
    "            periodSeconds: 5\n"
    "            timeoutSeconds: 3\n"
    "            failureThreshold: 60\n"
)
SA_OLD = (
    "kind: ServiceAccount\n"
    "metadata:\n"
    "  name: devpath-migration-fence\n"
    "automountServiceAccountToken: false\n"
)
SA_NEW = SA_OLD + "imagePullSecrets:\n  - name: ghcr-pull\n"


def edit(path: Path, old: str, new: str) -> None:
    raw = path.read_bytes()
    assert b"\r" not in raw, path
    text = raw.decode("utf-8")
    assert text.count(old) == 1, (path, text.count(old))
    assert "startupProbe" not in text and "imagePullSecrets" not in text, path
    path.write_bytes(text.replace(old, new).encode("utf-8"))


for service in SERVICES:
    edit(root / "apps" / service / "base" / "deployment.yaml", ANCHOR, PROBE + ANCHOR)
edit(root / "apps" / "devpath-migration" / "base" / "writer-fence-rbac.yaml", SA_OLD, SA_NEW)
print("edited", len(SERVICES) + 1, "files")
```

실행: `py -B PLAN_DIR/insert_startup_probe.py D:/workspace/dpa/.worktrees/gitops-pipeline-defects-dev`
- [ ] **Step 6: GREEN 확인** — 같은 명령 → 3건 PASS. `git diff --stat` 이 정확히 9파일, 서비스마다 `+7`, RBAC `+2`.
- [ ] **Step 7: 커밋** — `git add` 9개 매니페스트 + 새 테스트 → `test+fix: production startup budget and the fence pull secret`
- [ ] **Step 8: 실패하는 테스트 — smoke**(`tests/release/test_cloudflare_api.py` 끝, `if __name__` 앞에 추가. 같은 파일의 `FakeResponse`·`module` 을 쓴다 — 추가 전에 파일을 읽어 `FakeResponse` 의 생성자 시그니처와 모듈 변수명을 확인한다)

```python
class LandingApiSmokeTest(unittest.TestCase):
    ORIGIN = "https://leva.example.test"

    def probe(self, response=None, side_effect=None):
        with mock.patch.object(
            module._NO_REDIRECT_OPENER, "open", return_value=response, side_effect=side_effect
        ) as opened:
            module._probe_api(self.ORIGIN)
        return opened

    def test_requests_the_side_effect_free_functions_route_without_redirects(self):
        opened = self.probe(FakeResponse(b'{"rounds":[]}'))
        request = opened.call_args.args[0]
        self.assertEqual(request.full_url, f"{self.ORIGIN}/api/invite-rounds")
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(opened.call_args.kwargs["timeout"], 10)

    def test_rejects_a_deployment_that_lost_its_functions(self):
        # 2026-09-21: a dist-only deploy dropped functions/ and /api/* served the static 404 page.
        for response in (
            FakeResponse(b"<!doctype html><title>404</title>", status=404),
            FakeResponse(b"", status=308),
            FakeResponse(b"<!doctype html><title>home</title>"),
            FakeResponse(b"\xff\xfe"),
            FakeResponse(b"[1" + b" " * 65536 + b"]"),
        ):
            with self.assertRaisesRegex(ValueError, "Landing API smoke"):
                self.probe(response)

    def test_wraps_network_failures(self):
        with self.assertRaisesRegex(ValueError, "Landing API smoke failed"):
            self.probe(side_effect=OSError("connection reset"))

    def test_production_verification_runs_the_api_smoke_after_the_page_probe(self):
        source = Path(module.__file__).read_text(encoding="utf-8")
        branch = source[source.index('if action == "verify-new-production":'):]
        branch = branch[: branch.index("return")]
        self.assertLess(branch.index("_probe(landing_origin)"), branch.index("_probe_api(landing_origin)"))
```

- [ ] **Step 9: RED 확인** — `py -B -m unittest discover -s tests/release -p 'test_cloudflare_api.py'` → 새 4건이 `AttributeError: … has no attribute '_probe_api'` / `ValueError: substring not found` 로 FAIL, 기존 건은 PASS.
- [ ] **Step 10: 최소 구현**(`scripts/release/cloudflare_pages.py`, `_probe` 바로 뒤)

```python
API_SMOKE_PATH = "/api/invite-rounds"
MAX_API_SMOKE_BYTES = 65536


def _probe_api(origin: str) -> None:
    # The sealed dist must carry the Pages Functions (dist/_worker.js). A dist-only deploy that
    # lost them still serves "/" and the marker, so probe one side-effect-free Functions route.
    request = Request(
        f"{origin.rstrip('/')}{API_SMOKE_PATH}",
        headers={"Accept": "application/json", "User-Agent": "devpath-landing-canary/3"},
    )
    try:
        with _NO_REDIRECT_OPENER.open(request, timeout=10) as response:
            if response.status != 200:
                raise ValueError("Landing API smoke returned a non-200 status")
            raw = response.read(MAX_API_SMOKE_BYTES + 1)
    except OSError as exc:
        raise ValueError("Landing API smoke failed") from exc
    if len(raw) > MAX_API_SMOKE_BYTES:
        raise ValueError("Landing API smoke response is too large")
    try:
        json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Landing API smoke response is not UTF-8 JSON") from exc
```

`verify-new-production` 분기에서 `_probe(landing_origin)` 다음 줄에 `_probe_api(landing_origin)` 을 넣고, 성공 메시지를 `"verified exact new Landing deployment, public dist marker, page smoke, and API smoke"` 로 바꾼다. (`_NoRedirectHandler` 가 3xx 를 어떻게 돌려주는지 — 예외인지 응답인지 — 구현 전에 읽고, 308 케이스의 기대를 그에 맞춘다.)
- [ ] **Step 11: GREEN + 회귀** — smoke 테스트 PASS → `tests/release` 전체가 Step 2 의 기준선 + 새 테스트 수와 일치, 실패 0. 기존 테스트가 성공 메시지 문자열을 단언하면 그 단언을 새 문자열로 옮긴다(grep 으로 확인).
- [ ] **Step 12: 커밋** — `test+feat(release): smoke one Pages Functions route in landing verification`
- [ ] **Step 13: 렌더 diff** — 9개 앱(서비스 8 + `devpath-migration`)에 대해 `kubectl kustomize apps/<app>/base` 를 `MAIN_SHA` 워크트리와 dev 워크트리에서 떠서 `diff`. 기대: 서비스마다 `startupProbe` 7줄 추가뿐, migration 은 SA 의 `imagePullSecrets` 2줄 추가뿐. diff 전문은 스크래치패드에 두고 요약만 스펙 §12.5 에 적는다. (overlay 가 있으면 ApplicationSet 이 실제로 가리키는 경로를 `argocd/` 에서 확인해 그 경로로 뜬다.)

### Task 2: 결정적 target 커밋을 만들고 target 브랜치를 push 한다

**Files:**
- Create: `PLAN_DIR/make_pipeline_defects_target.py`(선례 `PREC_DIR/make_unfence_target.py` 의 구조)

**Interfaces:**
- Consumes: Task 1 의 dev 커밋 SHA(`--source`).
- Produces: `TARGET_SHA` · `TARGET_TREE`(stdout) · 원격 브랜치 `fix/pipeline-defects-main-20260921`.

`TARGET_PATHS`(정렬된 12행 — `git diff-tree --name-status` 의 출력 순서):

```
M	apps/devpath-ai-svc/base/deployment.yaml
M	apps/devpath-community-svc/base/deployment.yaml
M	apps/devpath-gateway/base/deployment.yaml
M	apps/devpath-lcs-svc/base/deployment.yaml
M	apps/devpath-learning-svc/base/deployment.yaml
M	apps/devpath-migration/base/writer-fence-rbac.yaml
M	apps/devpath-notification-svc/base/deployment.yaml
M	apps/devpath-platform-svc/base/deployment.yaml
M	apps/devpath-sandbox-svc/base/deployment.yaml
M	scripts/release/cloudflare_pages.py
M	tests/release/test_cloudflare_api.py
A	tests/release/test_production_startup_budget.py
```

- [ ] **Step 1: 스크립트** — 선례와 같은 뼈대: `origin/main == MAIN_SHA` 단언 → 임시 `GIT_INDEX_FILE` 에 `read-tree MAIN_SHA` → 12개 경로마다 `--source` 커밋의 blob 을 `update-index --add --cacheinfo 100644,<blob>,<path>`(blob 에 `\r` 없음 단언) → `write-tree` → 봇 신원·고정 날짜로 `commit-tree -p MAIN_SHA` → 사후 단언: `diff --name-status MAIN_SHA target` == 위 12행 · `diff --check` · `--source` 트리와 target 트리가 **같다**(dev 브랜치에 12경로 밖의 변경이 없다는 증명) · 선택 인자 `expected` 와 SHA 일치. 커밋 메시지 subject: `release: add the production startup budget, the fence pull secret, and the landing API smoke to main`, 본문은 세 결함의 이유와 스펙 §12 참조, 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- [ ] **Step 2: 두 번 실행해 같은 SHA** 임을 확인(결정성) → `TARGET_SHA`·`TARGET_TREE` 기록.
- [ ] **Step 3: target 트리에서 전체 테스트** — `git worktree add --detach D:/workspace/dpa/.worktrees/gitops-pipeline-defects-target <TARGET_SHA>` → `tests/release` 전체 OK(건수 기록).
- [ ] **Step 4: push** — `git -C <dev worktree> push origin <TARGET_SHA>:refs/heads/fix/pipeline-defects-main-20260921` → `ls-remote` 로 확인. (main 이 아니고 PR 도 아니다 — CI 는 돌지 않는다. 선례와 같다.)

### Task 3: target 이 다음 릴리스의 base 로 받아들여짐을 실제 게이트 코드로 증명한다

**Files:**
- Create: `PLAN_DIR/prove_next_base.py`(선례에서 파생)

- [ ] **Step 1:** 선례 스크립트에서 바꾸는 것 — 대조군 `M`(fence 가 있는 커밋 `c1d5e8cf…`)은 그대로 둔다(여전히 "거부되어야 하는" 대조군으로 유효) · docstring. 호출 인자: gitops 스크립트 디렉터리 = **target 워크트리**의 `scripts/release`, shared 스크립트 = `git -C D:/workspace/dpa/devpath-shared show origin/main:scripts/release/migration_release_gate.py` 를 스크래치패드에 물질화한 것(+ 같은 디렉터리의 import 의존 파일), candidate spec = `.release-artifacts/ms-20260920-community-flat-pages/r3/` 의 r3 spec.
- [ ] **Step 2: 실행** — 기대: target 3건 `accepted`(PASS), 대조군 2건 `refused`(PASS), exit 0. 출력 전문을 스크래치패드에 저장.

### Task 4: 헬퍼(publisher) 워크플로와 계약 테스트

**Files:**
- Create: `PLAN_DIR/render_helper_workflow.py` · `PLAN_DIR/render_contract_test.py`
- Output(헬퍼 브랜치에): `.github/workflows/mission-spine-auth-smoke.yml` · `tests/release/test_pipeline_defects_main_publish.py`

**Interfaces:**
- Consumes: `TARGET_SHA`·`TARGET_TREE`(Task 2).
- Produces: 헬퍼 커밋 SHA(`HELPER_SHA`) — `MAIN_SHA` 의 단일 자식, 정확히 2경로.

치환표(원본 = `git show origin/chore/r2-writer-fence-removal-publish-20260921:<path>`, 전부 `assert text.count(old) == n`):

| old | new |
|---|---|
| `r2 writer fence removal main publisher` | `pipeline defects main publisher` |
| `Publish the exact tested r2 writer fence removal to main` | `Publish the exact tested pipeline defect fixes to main` |
| `r2-writer-fence-removal-main-publish` | `pipeline-defects-main-publish` |
| `chore/r2-writer-fence-removal-publish-20260921` (×2) | `chore/pipeline-defects-publish-20260921` |
| `fix/r2-writer-fence-removal-main-20260921` | `fix/pipeline-defects-main-20260921` |
| env 블록의 `MAIN_SHA`·`FENCE_BASE_SHA`·`TARGET_SHA`·`TARGET_TREE`·`HELPER_BASE_SHA` 5줄 | `MAIN_SHA`·`TARGET_SHA`·`TARGET_TREE`·`HELPER_BASE_SHA` 4줄(`FENCE_BASE_SHA` 삭제) |
| `test_r2_unfence_main_publish.py` (×3: 경로·`-p`·helper_paths) | `test_pipeline_defects_main_publish.py` |
| step 이름의 `fence-removal target` (×3) | `pipeline-defects target` |
| target checkout `fetch-depth: 3` | `fetch-depth: 2`(조부모가 필요 없다) |
| `test "$(git rev-list --parents -n 1 HEAD^)" = "$MAIN_SHA $FENCE_BASE_SHA"` | (삭제) |
| subject 문자열 | Task 2 의 subject |
| `target_listing` 부터 `test "$migration_target" = "$migration_main"` 까지의 블록 | 아래 블록 |

새 target 목록 블록(빈 목록·부분 일치가 통과할 수 없게 — 전체 문자열 비교 + `test -n`):

```bash
          target_listing="$(git diff-tree --no-commit-id --name-status -r HEAD)"
          test -n "$target_listing"
          expected_listing="$(printf '%s\n' \
            $'M\tapps/devpath-ai-svc/base/deployment.yaml' \
            $'M\tapps/devpath-community-svc/base/deployment.yaml' \
            $'M\tapps/devpath-gateway/base/deployment.yaml' \
            $'M\tapps/devpath-lcs-svc/base/deployment.yaml' \
            $'M\tapps/devpath-learning-svc/base/deployment.yaml' \
            $'M\tapps/devpath-migration/base/writer-fence-rbac.yaml' \
            $'M\tapps/devpath-notification-svc/base/deployment.yaml' \
            $'M\tapps/devpath-platform-svc/base/deployment.yaml' \
            $'M\tapps/devpath-sandbox-svc/base/deployment.yaml' \
            $'M\tscripts/release/cloudflare_pages.py' \
            $'M\ttests/release/test_cloudflare_api.py' \
            $'A\ttests/release/test_production_startup_budget.py')"
          test -n "$expected_listing"
          test "$target_listing" = "$expected_listing"
          mapfile -t target_rows <<<"$target_listing"
          test "${#target_rows[@]}" -eq 12
```

계약 테스트는 선례 테스트에서 같은 방식으로 파생한다: 좌표 상수 교체(`FENCE_BASE_SHA` 제거, `len({MAIN_SHA, TARGET_SHA}) == 2`) · `test_target_changes_exactly_the_two_writer_kustomizations` → `test_target_changes_exactly_the_twelve_pinned_paths`(`fetch-depth == 2`, 위 12행 전부와 `test "$target_listing" = "$expected_listing"`·`test -n "$expected_listing"`·`-eq 12` 가 run 에 있음) · `test_writer_blobs_return_…` 삭제 · `test_no_step_shadows_a_pinned_coordinate` 의 필수 핀 집합에서 `FENCE_BASE_SHA` 제거 · 클래스명 `PipelineDefectsMainPublishTest`.

- [ ] **Step 1:** 두 render 스크립트 작성(끝에 stale 문자열 단언: `r2`, `unfence`, `fence-removal`, `FENCE_BASE`, `c1d5e8cf`, `69e7bd15`, `fcf97cf6`, `a1c43f95`).
- [ ] **Step 2: RED** — 새 계약 테스트를 **선례 워크플로**(9/21 헬퍼 바이트)에 돌려 실패함을 확인(테스트가 실제로 무언가를 단언한다는 증명).
- [ ] **Step 3: GREEN** — 렌더한 워크플로에 돌려 전부 PASS. `actionlint` 통과.
- [ ] **Step 4: 파생 diff 검토** — `diff <9/21 헬퍼> <새 헬퍼>` 가 치환표의 항목뿐임을 눈으로 확인하고 diff 를 스크래치패드에 저장(리뷰 입력).
- [ ] **Step 5: target step 드라이런** — `PLAN_DIR/dryrun_target_step.py`(선례에서 step 이름만 교체)로 실제 target 워크트리에서 step 본문을 독립 Git Bash 로 실행 → `STEP-ASSERTIONS-PASSED`. 대조: `TARGET_TREE` 를 틀린 값으로 → rc≠0 · dev 브랜치에 13번째 경로를 더한 가짜 커밋 → 목록 비교에서 rc≠0.
- [ ] **Step 6: 변이 검사** — `PLAN_DIR/mutation_check.py`·`contract_mutants.py`(선례에서 파생): 워크플로를 한 줄씩 망가뜨린 변이(예: 12행 중 한 행 삭제, `test -n "$expected_listing"` 삭제, step 수준 `env: TARGET_SHA`, `set -euo pipefail` 삭제, push step 복제)가 **각각 의도한 계약 테스트에서** 죽는지 확인. 살아남는 변이가 있으면 테스트를 보강한다.
- [ ] **Step 7: 헬퍼 커밋** — `git worktree add -b chore/pipeline-defects-publish-20260921 D:/workspace/dpa/.worktrees/gitops-pipeline-defects-helper 30c0e9f7…` → 두 파일 배치 → 워크트리 안에서 계약 테스트 + `tests/release` 전체 → 커밋 `ci: add the one-shot pipeline defects main publisher` → `diff-tree --name-only` 가 정확히 2행임을 확인 → push → `HELPER_SHA` 기록.

### Task 5: staged 디스패처

- [ ] **Step 1:** 선례 디스패처 브랜치(`origin/chore/r2-unfence-publish-dispatcher-staged-20260921` = `00c66257`)가 부모 대비 무엇을 바꿨는지 `git diff --stat`·전문으로 읽는다(선례 렌더러: `.release-artifacts/ms-20260920-community-flat-pages/unfence-publisher/dispatcher/`).
- [ ] **Step 2:** 같은 치환(헬퍼 브랜치명 · 방아쇠 브랜치명 `automation/dispatch-pipeline-defects-main-publish` · 워크플로 name/concurrency)으로 렌더 → actionlint → 선례와의 diff 가 이름뿐임을 확인 → `chore/pipeline-defects-publish-dispatcher-staged-20260921` 로 push → `STAGED_SHA` 기록. **방아쇠 브랜치는 만들지 않는다.**

### Task 6: 실행 스크립트와 단위 테스트

**Files:**
- Create: `PLAN_DIR/run_pipeline_defects_main_publish.py` · `PLAN_DIR/test_run_pipeline_defects_main_publish.py` · `PLAN_DIR/render_run_script.py`

- [ ] **Step 1:** 선례 `run_r2_unfence_main_publish.py` 에서 상수 7개(`MAIN_SHA`·`TARGET_SHA`·`TARGET_TREE`·`HELPER_BRANCH`·`TARGET_BRANCH`·`STAGED_BRANCH`·`DISPATCH_BRANCH`)와 docstring 만 치환. 테스트 파일도 같은 치환 + import 모듈명.
- [ ] **Step 2:** `py -B -m unittest PLAN_DIR/test_run_pipeline_defects_main_publish.py` → 선례와 같은 건수 PASS.
- [ ] **Step 3: live `--preflight-only`** — `--repo-dir <target 워크트리가 속한 클론> --staged-sha <STAGED_SHA> --helper-sha <HELPER_SHA> --comment preflight` → OK(룰셋 2종 · `enforce_admins` · 환경 정책 main 단독 · target 트리 · 진행 중 실행 0 · 사이트 200 — 읽기만).
- [ ] **Step 4: 음성 대조** — 틀린 `--helper-sha` → 첫 쓰기 전에 거부.

### Task 7: 독립 리뷰(새 컨텍스트, 읽기 전용) → 발견 사항을 변이로 재현한 뒤 수정

- [ ] **Step 1:** 서브에이전트 1개에 리뷰만 위임. 입력: 스펙 §12 · target diff · 헬퍼 워크플로와 9/21 헬퍼 대비 diff · 계약 테스트 · 실행 스크립트 diff. 지시문에 Scope Lock 문구(이 작업만 / 끝나면 보고 후 정지 / 파일 수정·git 쓰기·push 금지 / 절대경로) + "보고 전문은 `<스크래치패드>/review-pipeline-defects.md` 에, 응답은 3줄".
- [ ] **Step 2:** 컨트롤러 검증 — 리뷰 후 gitops·documents·인접 레포에 낯선 브랜치·커밋이 없는지 `git branch`/`git log` 스팟체크.
- [ ] **Step 3:** Critical/Medium 은 변이·재현으로 확인한 뒤 고친다. 헬퍼나 target 이 바뀌면 SHA 핀이 움직이므로 Task 2/4/5/6 의 해당 단계를 다시 돈다.

### Task 8: 문서화와 확인 관문

- [ ] **Step 1:** 스펙 §12 에 좌표표(`MAIN_SHA`·target·헬퍼·staged·방아쇠 "아직 없음")와 **§12.5 준비 결과**(테스트 건수 · 렌더 diff 요약 · next-base 증명 · 변이 · 리뷰 결과 · preflight)를 적고 §12 제목의 상태를 "준비 완료, 실행 전" 으로.
- [ ] **Step 2:** `PLAN_DIR` 의 스크립트를 파일 단위 `git add`(`__pycache__` 금지) → documents PR → CI 녹색 → develop 머지(merge commit).
- [ ] **Step 3:** 메모리 갱신(착수점 = Part B 확인 관문).
- [ ] **Step 4: 확인 관문** — 되돌릴 수 없는 지점(main 이동 → r3 자동 롤백 레인이 다음 승격까지 닫힘 · 8개 서비스 순차 롤아웃 · sandbox 약 25초 중단)을 요약해 "지금 실행 / 다음 릴리스 캠페인의 0단계로" 를 선택지로 묻는다. **"진행"을 main 이동의 승인으로 읽지 않는다.**

---

## Part B — 실행 (사용자 확인 뒤, 스펙 §12.3)

- [ ] **B1:** `--preflight-only` 재실행(`main moved` 면 중단) + 클러스터 읽기 점검(8개 Deployment `paused` 없음 · 재시작 0 · Argo 전부 Synced/Healthy · 노드 load).
- [ ] **B2:** `kubectl -n devpath rollout pause deployment/devpath-notification-svc` → 90초 동안 15초 간격으로 `spec.paused` 와 Argo `sync.status` 관찰. Argo 가 되돌리면 **중단**(resume 후 재설계).
- [ ] **B3:** 나머지 7개 pause → 8개 전부 `paused: true` 확인.
- [ ] **B4:** `run_pipeline_defects_main_publish.py --repo-dir … --staged-sha … --helper-sha … --comment …` — 환경 정책 임시 추가 → 방아쇠 push → waiting 확인 → main-only 복원·검증 → 승인 → 전 step success → post_verify. `RestoreError` 면 승인하지 않는다.
- [ ] **B5:** `main == TARGET_SHA` · main CI success → Argo sync 뒤: 8개 Deployment 템플릿에 `startupProbe` · ReplicaSet 수와 파드가 그대로 · fence SA `imagePullSecrets` 유지.
- [ ] **B6:** notification → ai → lcs → community → learning → sandbox → platform → gateway 순으로 하나씩 `rollout resume` → `rollout status --timeout=6m` → 새 파드 `restartCount == 0` · `startupProbe` 존재 확인 → 다음. 실패 시 그 Deployment 를 다시 pause + 새 ReplicaSet `scale --replicas=0`, 중단하고 보고.
- [ ] **B7:** 사후 — 8개 앱 Synced/Healthy · `paused` 없음 · 전 파드 재시작 0 · `app.leva.ai.kr`·`leva.ai.kr` 200 · OAuth 시작 경로 302 · 룰셋·`enforce_admins`·환경 정책 불변.
- [ ] **B8:** 스펙 §12.6 실행 결과 · 핸드오프 · 메모리. 다음 candidate 의 `gitops.base_sha` = `TARGET_SHA`.
