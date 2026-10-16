# GPU 스팟 노드 자동 복구 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GPU 스팟 노드가 회수돼도 사람 없이 `ollama-gpu` 와 모델 2종이 10분 안에 돌아오고, 15분 넘게 안 돌아오면 알림이 온다.

**Architecture:** ASG(스팟 1대, 세 AZ)가 대체 인스턴스를 띄우고, cloud-init 의 기동 스크립트가 SSM 에서 조인 토큰과 노드 비밀번호를 읽어 **같은 노드 이름(`devpath-gpu`)** 으로 조인한다. 클러스터는 같은 Node 가 돌아온 것으로 보므로 노드 · 파드 · PVC 를 지울 필요가 없다. 노드가 1분마다 보내는 생존 신호(CloudWatch 지표)를 알람과 반복 통지 Lambda 가 본다.

**Tech Stack:** Python 3.10(노드) / 3.13(CI · Lambda) 표준 라이브러리 · `unittest` · PyYAML 6.0.x(테스트 전용) · cloud-init `#cloud-config` · systemd · k3s `v1.36.2+k3s1` · AWS(EC2 Auto Scaling · SSM Parameter Store · CloudWatch · SNS · Lambda · IAM)

**Spec:** `documents/docs/superpowers/specs/2026-10-07-gpu-node-auto-recovery-design.md` (develop `ac7f1ae4`, 사용자 승인 2026-10-07)

## Global Constraints

- 코드 레포 `D:/workspace/dpa/devpath-gitops`. 작업 워크트리 `D:/workspace/dpa/.worktrees/gitops-gpu-auto-recovery`, 브랜치 `feat/gpu-node-auto-recovery` 를 `origin/develop` 에서 분기한다. PR 은 `develop` 으로만. `main` 은 동결(`9ab0dd79`)이다 — 건드리지 않는다.
- `apps/` · `scripts/release/` · `.github/workflows/` · `argocd/` · `staging/` · `release-manifests/` 를 바꾸지 않는다(스펙 G4).
- 모든 git 명령은 `git -C <절대경로>` 로 쓴다. `cd` 후 상대경로 명령을 이어 쓰지 않는다.
- TDD: 각 Task 는 실패하는 테스트를 먼저 쓰고 실패를 눈으로 본 뒤 구현한다.
- 테스트 실행(Git Bash): `PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 py -m unittest discover -s <WT>/tests/release -t <WT> -p '<파일>'`. 전체 스위트는 로컬에서 돌리지 않고 PR 의 CI 로 본다(로컬 Windows 는 12분을 넘긴다).
- 커밋은 기본 작성자(`Qahnaarin`)로 한다. 커밋 메시지는 영어 Conventional Commits, 끝에 세션이 지정한 `Co-Authored-By` · `Claude-Session` 줄.
- 고정값(스펙 4절 그대로): 노드 이름 `devpath-gpu` · 파라미터 접두 `/devpath/gpu-node/` · 지표 `DevPath/GPU` / `OllamaReady` / 차원 `Node=devpath-gpu` · 리전 `ap-northeast-2` · 서버 `https://172.31.48.82:6443` · 라벨 `devpath.ai/gpu=true` · 테인트 `devpath.ai/gpu=true:NoSchedule` · 모델 `qwen2.5:3b` `qwen2.5:7b` · 기동 재시도 한도 30분 · 알람 300초 × 3 · 반복 통지 창 15분.
- 조인 토큰과 노드 비밀번호의 **값**을 출력하거나 명령줄 · 환경 변수 · git · 이 세션의 도구 인자에 싣지 않는다(스펙 G3).
- 노드의 Python 은 3.10.12 다 — 3.11 이상 문법(`tomllib`, `except*` 등)을 쓰지 않는다.
- AWS 호출은 AWS MCP `run_script`(`call_boto3`)로 한다. 바이트 인자는 넘기지 못한다 — Lambda zip 은 임시 비공개 S3 버킷 + presigned URL 로 올린다(런북 「미복구 반복 통지」의 절차).
- Task 8~10 은 GPU 기능이 멈춘다. **시작 전에 사용자에게 시각을 확인받는다.**

## Review Focus

1. **`model-dir` 가 잘못 들어간 경우**(`/`, `/etc`, 저장소 루트 자체, `..` 를 섞은 경로, 상대 경로) — 기동 스크립트는 그 경로를 0777 로 만든다. 저장소 루트 밖은 거부하고 agent 를 설치하지 않아야 한다. → Task 1 `test_refuses_a_model_directory_outside_the_volume_storage_root`.
2. **파라미터 값의 앞뒤 공백 · 개행**(CLI 출력의 개행, 콘솔에서 붙여 넣은 `\r\n`) — 파일에는 다듬은 값과 개행 하나만 들어가야 한다. 비밀번호가 한 글자라도 다르면 노드가 거부된다. → Task 1 `test_trims_whitespace_around_parameter_values`.
3. **`get.k3s.io` 가 안 열리는데 파이프라인이 0 으로 끝나는 경우**(`curl` 실패 → 빈 입력을 받은 `sh` 가 성공) — 설치 실패로 세고 다시 시도해야 한다. → Task 1 `test_joins_under_the_fixed_name_with_the_gpu_label_and_taint`(`bash -o pipefail`).
4. **ollama 가 200 으로 엉뚱한 본문을 주는 경우**(HTML, 빈 본문, `{"models": null}`, 이름 없는 항목) — 생존 신호를 쓰지 않고, 예외로 죽지도 않아야 한다. → Task 2 `test_stays_silent_on_a_body_that_is_not_a_model_list`.
5. **CloudWatch 가 합이 0 인 데이터포인트나 둘로 쪼개진 데이터포인트를 주는 경우, 또는 조회 자체가 실패하는 경우** — 0 은 「신호 없음」, 쪼개진 것은 합쳐서 판단, 조회 실패는 조용히 넘어가지 않고 Lambda 오류로 드러나야 한다. → Task 4 `test_adds_up_split_datapoints` · `test_a_failed_metric_query_is_an_error_not_silence`.

---

## 파일 구조

| 파일 | 책임 |
|---|---|
| `infra/aws/gpu-node/bootstrap.py` (신규) | 부팅 때 한 번: 파라미터 읽기 → 비밀 파일 · PV 디렉터리 → agent 설치 → 타이머 켜기 |
| `infra/aws/gpu-node/heartbeat.py` (신규) | 1분마다: ollama 가 모델 2종을 내는지 보고 지표 한 점 쓰기 |
| `infra/aws/gpu-node/devpath-gpu-heartbeat.service` · `.timer` (신규) | 생존 신호의 systemd 유닛 |
| `infra/aws/gpu-node/render_user_data.py` (신규) | 위 네 파일로 `#cloud-config` user-data 를 만든다 |
| `infra/aws/gpu-node-absence-watch/handler.py` (수정) | 반복 통지의 기준을 「인스턴스 유무」에서 「생존 신호」로 |
| `tests/release/test_gpu_node_bootstrap.py` · `test_gpu_node_heartbeat.py` · `test_gpu_node_user_data.py` (신규) | 단위 테스트 |
| `tests/release/test_gpu_node_absence_watch.py` (수정) | Lambda 테스트 |
| `.gitattributes` (수정) | `infra/aws/**` 를 LF 로 고정(user-data 해시가 체크아웃에 따라 달라지지 않게) |
| `docs/runbook-k3s-bootstrap.md` (수정) | 「자동 복구」 절, 수동 절차의 위치 조정, 실측 기록 |

`<WT>` = `D:/workspace/dpa/.worktrees/gitops-gpu-auto-recovery`.

---

## Part A — 코드 (gitops develop, 서비스 영향 없음)

### Task 0: 워크트리

- [ ] **Step 1: 분기**

```bash
git -C D:/workspace/dpa/devpath-gitops fetch origin
git -C D:/workspace/dpa/devpath-gitops worktree add -b feat/gpu-node-auto-recovery D:/workspace/dpa/.worktrees/gitops-gpu-auto-recovery origin/develop
git -C D:/workspace/dpa/.worktrees/gitops-gpu-auto-recovery config --get user.name
```

Expected: 마지막 줄 `Qahnaarin`.

### Task 1: 기동 스크립트 `bootstrap.py`

**Files:**
- Create: `infra/aws/gpu-node/bootstrap.py`
- Test: `tests/release/test_gpu_node_bootstrap.py`

**Interfaces:**
- Produces: `main(run=run_command, root=Path("/"), sleep=time.sleep, clock=time.monotonic) -> int` (0 성공 · 1 실패) · 상수 `NODE_NAME = "devpath-gpu"` · `REGION = "ap-northeast-2"` · `PARAMETER_PREFIX = "/devpath/gpu-node/"` · `PASSWORD_FILE = "etc/rancher/node/password"` · `TOKEN_FILE = "etc/rancher/k3s/agent-token"` · `HEARTBEAT_TIMER = "devpath-gpu-heartbeat.timer"` · `INSTALL_RETRY_SECONDS = 30` · `INSTALL_BUDGET_SECONDS = 1800`.
- `run(args: list[str], env: dict | None = None)` 은 `.returncode` `.stdout` `.stderr` 를 가진 객체를 돌려준다.

- [ ] **Step 1: 실패하는 테스트를 쓴다** — `tests/release/test_gpu_node_bootstrap.py`

```python
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "infra" / "aws" / "gpu-node" / "bootstrap.py"
SPEC = importlib.util.spec_from_file_location("tested_gpu_node_bootstrap", SOURCE)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

TOKEN = "K10" + "ab" * 32 + "::q1w2e3.0123456789abcdef"
PASSWORD = "0f" * 16
MODEL_DIR = "/var/lib/rancher/k3s/storage/pvc-1234_devpath_ollama-gpu-models"
POSIX = os.name != "nt"


class Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeHost:
    """Answers the commands the bootstrap runs and records them in order."""

    def __init__(self, root, *, parameters=None, install_results=(0,)):
        self.root = root
        self.parameters = {
            "k3s-version": "v1.36.2+k3s1\n",
            "agent-token": TOKEN + "\n",
            "node-password": PASSWORD + "\n",
            "model-dir": MODEL_DIR + "\n",
        }
        self.parameters.update(parameters or {})
        self.install_results = list(install_results)
        self.calls = []
        self.seen_at_install = None
        self.slept = []
        self.now = 0.0

    def run(self, args, env=None):
        self.calls.append((list(args), dict(env) if env is not None else None))
        if args[:3] == ["aws", "ssm", "get-parameter"]:
            name = args[args.index("--name") + 1].removeprefix(module.PARAMETER_PREFIX)
            value = self.parameters.get(name)
            if value is None:
                return Result(254, "", "An error occurred (ParameterNotFound) when calling the GetParameter operation: ")
            return value if isinstance(value, Result) else Result(0, value)
        if args[:1] == ["bash"]:
            self.seen_at_install = {
                "password": (self.root / module.PASSWORD_FILE).read_text(encoding="ascii"),
                "token": (self.root / module.TOKEN_FILE).read_text(encoding="ascii"),
                "model_dir": (self.root / MODEL_DIR.lstrip("/")).is_dir(),
            }
            code = self.install_results.pop(0) if len(self.install_results) > 1 else self.install_results[0]
            return Result(code)
        return Result(0)

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds

    def clock(self):
        return self.now

    def installs(self):
        return [(args, env) for args, env in self.calls if args[:1] == ["bash"]]


class GpuNodeBootstrapTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def bootstrap(self, host):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = module.main(run=host.run, root=self.root, sleep=host.sleep, clock=host.clock)
        return code, stdout.getvalue() + stderr.getvalue()

    def test_writes_the_password_and_the_token_before_the_agent_starts(self):
        # 2026-10-06: a node that starts under an existing name without the saved password is
        # rejected ("Node password rejected, duplicate hostname ..."), and a volume directory that
        # does not exist leaves the pod in FailedMount. All three have to be there first.
        host = FakeHost(self.root)
        code, _ = self.bootstrap(host)
        self.assertEqual(code, 0)
        self.assertEqual(
            host.seen_at_install,
            {"password": PASSWORD + "\n", "token": TOKEN + "\n", "model_dir": True},
        )

    @unittest.skipUnless(POSIX, "POSIX file modes")
    def test_secret_files_are_readable_by_root_only(self):
        host = FakeHost(self.root)
        self.bootstrap(host)
        for name in (module.PASSWORD_FILE, module.TOKEN_FILE):
            self.assertEqual(stat.S_IMODE((self.root / name).stat().st_mode), 0o600, name)
        # local-path creates its volume directories 0777.
        self.assertEqual(stat.S_IMODE((self.root / MODEL_DIR.lstrip("/")).stat().st_mode), 0o777)

    def test_joins_under_the_fixed_name_with_the_gpu_label_and_taint(self):
        host = FakeHost(self.root)
        self.bootstrap(host)
        args, env = host.installs()[0]
        # pipefail: with get.k3s.io unreachable, curl fails and sh, fed nothing, would exit 0.
        self.assertEqual(args[:4], ["bash", "-o", "pipefail", "-c"])
        self.assertIn("curl -sfL https://get.k3s.io | sh -s - agent", args[4])
        self.assertIn("--node-name devpath-gpu", args[4])
        self.assertIn("--node-label devpath.ai/gpu=true", args[4])
        self.assertIn("--node-taint devpath.ai/gpu=true:NoSchedule", args[4])
        self.assertEqual(env["INSTALL_K3S_VERSION"], "v1.36.2+k3s1")
        self.assertEqual(env["K3S_URL"], "https://172.31.48.82:6443")
        self.assertEqual(env["K3S_TOKEN_FILE"], str(self.root / module.TOKEN_FILE))

    def test_no_parameter_value_reaches_a_command_line_or_the_environment(self):
        host = FakeHost(self.root)
        self.bootstrap(host)
        for args, env in host.calls:
            for text in [" ".join(args), *(env or {}).values()]:
                self.assertNotIn(TOKEN, text)
                self.assertNotIn(PASSWORD, text)

    def test_prints_no_parameter_value(self):
        host = FakeHost(self.root)
        code, output = self.bootstrap(host)
        self.assertEqual(code, 0)
        self.assertNotIn(TOKEN, output)
        self.assertNotIn(PASSWORD, output)

    def test_reads_the_secrets_decrypted_and_the_rest_plain(self):
        host = FakeHost(self.root)
        self.bootstrap(host)
        decrypted = {
            args[args.index("--name") + 1]: "--with-decryption" in args
            for args, _ in host.calls
            if args[:3] == ["aws", "ssm", "get-parameter"]
        }
        self.assertEqual(
            decrypted,
            {
                "/devpath/gpu-node/k3s-version": False,
                "/devpath/gpu-node/agent-token": True,
                "/devpath/gpu-node/node-password": True,
                "/devpath/gpu-node/model-dir": False,
            },
        )

    def test_continues_without_a_model_directory_when_the_parameter_does_not_exist(self):
        # At the cutover the volume does not exist yet; the provisioner creates its directory.
        host = FakeHost(self.root, parameters={"model-dir": None})
        code, _ = self.bootstrap(host)
        self.assertEqual(code, 0)
        self.assertFalse(host.seen_at_install["model_dir"])
        self.assertFalse((self.root / "var").exists())

    def test_refuses_a_model_directory_outside_the_volume_storage_root(self):
        # The directory is created 0777. A mistyped parameter must not do that to "/" or "/etc".
        for value in (
            "/",
            "/etc",
            "/var/lib/rancher/k3s/storage",
            "/var/lib/rancher/k3s/storage/",
            "/var/lib/rancher/k3s/storage/../../../../etc",
            "storage/pvc-1234_devpath_ollama-gpu-models",
        ):
            with self.subTest(value=value):
                host = FakeHost(self.root, parameters={"model-dir": value})
                code, output = self.bootstrap(host)
                self.assertEqual(code, 1)
                self.assertIn("model-dir", output)
                self.assertEqual(host.installs(), [])

    def test_trims_whitespace_around_parameter_values(self):
        host = FakeHost(
            self.root,
            parameters={
                "k3s-version": " v1.36.2+k3s1\n",
                "agent-token": "  " + TOKEN + " \n\n",
                "node-password": PASSWORD + "\r\n",
                "model-dir": MODEL_DIR + " \n",
            },
        )
        code, _ = self.bootstrap(host)
        self.assertEqual(code, 0)
        self.assertEqual((self.root / module.TOKEN_FILE).read_bytes(), (TOKEN + "\n").encode())
        self.assertEqual((self.root / module.PASSWORD_FILE).read_bytes(), (PASSWORD + "\n").encode())
        self.assertEqual(host.installs()[0][1]["INSTALL_K3S_VERSION"], "v1.36.2+k3s1")
        self.assertTrue((self.root / MODEL_DIR.lstrip("/")).is_dir())

    def test_retries_a_failed_install_until_it_succeeds(self):
        host = FakeHost(self.root, install_results=(1, 1, 0))
        code, _ = self.bootstrap(host)
        self.assertEqual(code, 0)
        self.assertEqual(len(host.installs()), 3)
        self.assertEqual(host.slept, [module.INSTALL_RETRY_SECONDS] * 2)

    def test_gives_up_when_the_install_budget_runs_out(self):
        host = FakeHost(self.root, install_results=(1,))
        code, output = self.bootstrap(host)
        self.assertEqual(code, 1)
        self.assertIn("k3s agent install failed", output)
        self.assertEqual(sum(host.slept), module.INSTALL_BUDGET_SECONDS)
        self.assertNotIn(TOKEN, output)
        self.assertNotIn(PASSWORD, output)
        self.assertFalse(any(args[:2] == ["systemctl", "enable"] for args, _ in host.calls))

    def test_stops_before_the_install_when_a_required_parameter_cannot_be_read(self):
        denied = Result(
            254, "", "An error occurred (AccessDeniedException) when calling the GetParameter operation: no"
        )
        host = FakeHost(self.root, parameters={"node-password": denied})
        code, output = self.bootstrap(host)
        self.assertEqual(code, 1)
        self.assertIn("/devpath/gpu-node/node-password", output)
        self.assertIn("AccessDeniedException", output)
        self.assertEqual(host.installs(), [])

    def test_a_missing_required_parameter_is_an_error_not_a_skip(self):
        host = FakeHost(self.root, parameters={"agent-token": None})
        code, output = self.bootstrap(host)
        self.assertEqual(code, 1)
        self.assertIn("/devpath/gpu-node/agent-token", output)
        self.assertEqual(host.installs(), [])

    def test_enables_the_heartbeat_timer_after_the_agent_is_installed(self):
        host = FakeHost(self.root)
        self.bootstrap(host)
        order = [args for args, _ in host.calls if args[0] in ("bash", "systemctl")]
        self.assertEqual(order[0][0], "bash")
        self.assertEqual(
            order[1:],
            [["systemctl", "daemon-reload"], ["systemctl", "enable", "--now", "devpath-gpu-heartbeat.timer"]],
        )

    def test_running_twice_leaves_the_same_files(self):
        self.bootstrap(FakeHost(self.root))
        code, _ = self.bootstrap(FakeHost(self.root))
        self.assertEqual(code, 0)
        self.assertEqual((self.root / module.PASSWORD_FILE).read_bytes(), (PASSWORD + "\n").encode())
        self.assertEqual((self.root / module.TOKEN_FILE).read_bytes(), (TOKEN + "\n").encode())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 py -m unittest discover -s <WT>/tests/release -t <WT> -p 'test_gpu_node_bootstrap.py'`
Expected: `FAILED (errors=1)` — `bootstrap.py` 가 없어 모듈 로드에서 `FileNotFoundError`.

- [ ] **Step 3: 구현한다** — `infra/aws/gpu-node/bootstrap.py`

```python
#!/usr/bin/env python3
"""Join this instance to the cluster as the node it replaces.

A spot reclaim used to need three manual deletions because the replacement joined under a new
name while the model volume stayed pinned to the old one. With the same node name and the same
node password the server takes the new machine for the same Node, and nothing has to be deleted
(measured 2026-10-06; documents docs/superpowers/specs/2026-10-07-gpu-node-auto-recovery-design.md).

cloud-init runs this once. Every step can run again with the same result. No value read from
Parameter Store is printed, passed on a command line or put in an environment variable.
"""
import os
import posixpath
import re
import subprocess
import sys
import time
from pathlib import Path

REGION = "ap-northeast-2"
PARAMETER_PREFIX = "/devpath/gpu-node/"
NODE_NAME = "devpath-gpu"
SERVER_URL = "https://172.31.48.82:6443"
NODE_LABEL = "devpath.ai/gpu=true"
NODE_TAINT = "devpath.ai/gpu=true:NoSchedule"
PASSWORD_FILE = "etc/rancher/node/password"
TOKEN_FILE = "etc/rancher/k3s/agent-token"
STORAGE_ROOT = "/var/lib/rancher/k3s/storage/"
INSTALL_PIPELINE = (
    "curl -sfL https://get.k3s.io | sh -s - agent"
    f" --node-name {NODE_NAME} --node-label {NODE_LABEL} --node-taint {NODE_TAINT}"
)
INSTALL_BUDGET_SECONDS = 1800
INSTALL_RETRY_SECONDS = 30
HEARTBEAT_TIMER = "devpath-gpu-heartbeat.timer"


class BootstrapError(Exception):
    """A step failed and the operator has to read why. Never carries a parameter value."""


def run_command(args, env=None):
    return subprocess.run(args, env=env, capture_output=True, text=True, check=False)


def read_parameter(run, name, *, decrypt=False, required=True):
    args = [
        "aws", "ssm", "get-parameter", "--region", REGION, "--name", PARAMETER_PREFIX + name,
        "--query", "Parameter.Value", "--output", "text",
    ]
    if decrypt:
        args.append("--with-decryption")
    result = run(args)
    if result.returncode != 0:
        code = re.search(r"\((\w+)\)", result.stderr)
        reason = code.group(1) if code else f"exit {result.returncode}"
        if reason == "ParameterNotFound" and not required:
            return None
        raise BootstrapError(f"cannot read parameter {PARAMETER_PREFIX}{name} ({reason})")
    value = result.stdout.strip()
    if not value:
        raise BootstrapError(f"parameter {PARAMETER_PREFIX}{name} is empty")
    return value


def write_secret(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="ascii", newline="\n") as handle:
        handle.write(value + "\n")
    os.chmod(path, 0o600)


def ensure_model_directory(root, value):
    # This directory is made world-writable, so a mistyped parameter must not reach "/" or "/etc".
    path = posixpath.normpath(value)
    if not path.startswith(STORAGE_ROOT):
        raise BootstrapError(f"parameter {PARAMETER_PREFIX}model-dir is not a directory under {STORAGE_ROOT}")
    target = root / path.lstrip("/")
    target.mkdir(parents=True, exist_ok=True)
    os.chmod(target, 0o777)
    return path


def install_agent(run, version, token_file, *, sleep, clock):
    env = dict(os.environ, INSTALL_K3S_VERSION=version, K3S_URL=SERVER_URL, K3S_TOKEN_FILE=str(token_file))
    deadline = clock() + INSTALL_BUDGET_SECONDS
    attempts = 0
    while True:
        attempts += 1
        # pipefail: with get.k3s.io unreachable, curl fails and sh, fed nothing, would exit 0.
        if run(["bash", "-o", "pipefail", "-c", INSTALL_PIPELINE], env=env).returncode == 0:
            return attempts
        if clock() >= deadline:
            raise BootstrapError(f"k3s agent install failed {attempts} times in {INSTALL_BUDGET_SECONDS}s")
        sleep(INSTALL_RETRY_SECONDS)


def main(run=run_command, root=Path("/"), sleep=time.sleep, clock=time.monotonic):
    try:
        version = read_parameter(run, "k3s-version")
        token = read_parameter(run, "agent-token", decrypt=True)
        password = read_parameter(run, "node-password", decrypt=True)
        model_dir = read_parameter(run, "model-dir", required=False)
        write_secret(root / PASSWORD_FILE, password)
        write_secret(root / TOKEN_FILE, token)
        print("wrote the node password and the agent token")
        if model_dir is None:
            print("no model-dir parameter: the provisioner will create the volume directory")
        else:
            print(f"volume directory ready: {ensure_model_directory(root, model_dir)}")
        attempts = install_agent(run, version, root / TOKEN_FILE, sleep=sleep, clock=clock)
        print(f"k3s agent {version} installed as {NODE_NAME} (attempt {attempts})")
        for args in (["systemctl", "daemon-reload"], ["systemctl", "enable", "--now", HEARTBEAT_TIMER]):
            if run(args).returncode != 0:
                raise BootstrapError(f"cannot enable {HEARTBEAT_TIMER}")
        print("heartbeat timer enabled")
    except BootstrapError as error:
        print(f"gpu-node bootstrap failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 통과를 확인한다**

Run: Step 2 와 같은 명령.
Expected: `Ran 15 tests` · `OK`(Windows 에서는 `skipped=1` — 파일 모드 테스트는 CI 의 Linux 에서 돈다).

- [ ] **Step 5: 커밋**

```bash
git -C <WT> add infra/aws/gpu-node/bootstrap.py tests/release/test_gpu_node_bootstrap.py
git -C <WT> commit -m "feat(infra): bootstrap the GPU node under the name it replaces"
```

커밋 본문에는 「같은 이름 · 같은 비밀번호면 같은 Node 로 복귀한다(2026-10-06 실측)」와 스펙 경로를 적는다.

### Task 2: 생존 신호 `heartbeat.py`

**Files:**
- Create: `infra/aws/gpu-node/heartbeat.py`
- Test: `tests/release/test_gpu_node_heartbeat.py`

**Interfaces:**
- Produces: `main(run=run_command, fetch=fetch_url) -> int` — `0` 지표를 썼다 · `1` 아직 준비 안 됨(지표 없음) · `2` 준비됐는데 지표 쓰기 실패. 상수 `NODE_NAME = "devpath-gpu"` · `REGION` · `METRIC_NAMESPACE = "DevPath/GPU"` · `METRIC_NAME = "OllamaReady"` · `REQUIRED_MODELS`.
- `run(args: list[str])` 은 `.returncode` `.stdout` `.stderr` · `fetch(url: str) -> bytes`(실패는 예외).

- [ ] **Step 1: 실패하는 테스트를 쓴다** — `tests/release/test_gpu_node_heartbeat.py`

```python
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from urllib.error import URLError


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "infra" / "aws" / "gpu-node" / "heartbeat.py"
SPEC = importlib.util.spec_from_file_location("tested_gpu_node_heartbeat", SOURCE)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

POD_ID = "b67356d746769616a7234a1c50ba4531d3316a6a41da9a5d101a91d209f67f40"
INSPECT = json.dumps({"status": {"network": {"ip": "10.42.7.4"}, "metadata": {"namespace": "devpath"}}})
TAGS = json.dumps({"models": [{"name": "qwen2.5:7b"}, {"name": "qwen2.5:3b"}]}).encode()
PUBLISH = [
    "aws", "cloudwatch", "put-metric-data", "--region", "ap-northeast-2",
    "--namespace", "DevPath/GPU", "--metric-name", "OllamaReady",
    "--dimensions", "Node=devpath-gpu", "--value", "1",
]


class Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeNode:
    def __init__(self, *, pods=POD_ID + "\n", inspect=INSPECT, tags=TAGS, publish=None):
        self.pods = pods
        self.inspect = inspect
        self.tags = tags
        self.publish = publish or Result(0)
        self.commands = []
        self.fetched = []

    def run(self, args):
        self.commands.append(list(args))
        if args[:3] == ["k3s", "crictl", "pods"]:
            return self.pods if isinstance(self.pods, Result) else Result(0, self.pods)
        if args[:3] == ["k3s", "crictl", "inspectp"]:
            return self.inspect if isinstance(self.inspect, Result) else Result(0, self.inspect)
        if args[:3] == ["aws", "cloudwatch", "put-metric-data"]:
            return self.publish
        raise AssertionError(f"unexpected command: {args}")

    def fetch(self, url):
        self.fetched.append(url)
        if isinstance(self.tags, Exception):
            raise self.tags
        return self.tags

    @property
    def published(self):
        return [command for command in self.commands if command[:3] == ["aws", "cloudwatch", "put-metric-data"]]


class GpuNodeHeartbeatTest(unittest.TestCase):
    def beat(self, node):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = module.main(run=node.run, fetch=node.fetch)
        return code, stdout.getvalue() + stderr.getvalue()

    def test_writes_one_datapoint_while_ollama_serves_both_models(self):
        node = FakeNode()
        code, _ = self.beat(node)
        self.assertEqual(code, 0)
        self.assertEqual(node.published, [PUBLISH])
        self.assertEqual(node.fetched, ["http://10.42.7.4:11434/api/tags"])

    def test_looks_for_the_ready_ollama_gpu_pod_of_the_devpath_namespace(self):
        node = FakeNode()
        self.beat(node)
        self.assertEqual(
            node.commands[0],
            [
                "k3s", "crictl", "pods", "--label", "app=ollama-gpu",
                "--label", "io.kubernetes.pod.namespace=devpath", "--state", "Ready", "-q",
            ],
        )
        self.assertEqual(node.commands[1], ["k3s", "crictl", "inspectp", POD_ID])

    def test_other_models_next_to_the_two_do_not_matter(self):
        tags = json.dumps({"models": [{"name": n} for n in ("qwen2.5:14b", "qwen2.5:3b", "qwen2.5:7b")]}).encode()
        code, _ = self.beat(FakeNode(tags=tags))
        self.assertEqual(code, 0)

    def test_stays_silent_while_no_pod_is_ready(self):
        # The state right after a reclaim: the instance is up, the pod is not.
        for pods in ("", "\n", Result(1, "", "runtime is not ready")):
            with self.subTest(pods=pods):
                node = FakeNode(pods=pods)
                code, output = self.beat(node)
                self.assertEqual(code, 1)
                self.assertEqual(node.published, [])
                self.assertIn("not ready", output)

    def test_stays_silent_while_the_pod_has_no_address(self):
        for inspect in (
            "{}",
            json.dumps({"status": {"network": {"ip": ""}}}),
            json.dumps({"status": {"network": None}}),
            "not json",
            Result(1, "", "not found"),
        ):
            with self.subTest(inspect=inspect):
                node = FakeNode(inspect=inspect)
                code, _ = self.beat(node)
                self.assertEqual(code, 1)
                self.assertEqual(node.published, [])

    def test_stays_silent_when_ollama_does_not_answer(self):
        for failure in (URLError("connection refused"), TimeoutError("timed out"), ConnectionResetError()):
            with self.subTest(failure=failure):
                node = FakeNode(tags=failure)
                code, _ = self.beat(node)
                self.assertEqual(code, 1)
                self.assertEqual(node.published, [])

    def test_stays_silent_on_a_body_that_is_not_a_model_list(self):
        # A 200 that is not ollama's answer must neither count as ready nor crash the unit.
        for body in (
            b"<html>bad gateway</html>",
            b"",
            b"{}",
            b'{"models": null}',
            b'{"models": [{"model": "qwen2.5:3b"}]}',
            b'{"models": ["qwen2.5:3b", "qwen2.5:7b"]}',
            b"[1]",
            b"\xff\xfe",
        ):
            with self.subTest(body=body):
                node = FakeNode(tags=body)
                code, _ = self.beat(node)
                self.assertEqual(code, 1)
                self.assertEqual(node.published, [])

    def test_stays_silent_while_a_model_is_still_being_pulled(self):
        # postStart pulls in the background, so a Ready pod can still lack the 7b model.
        node = FakeNode(tags=json.dumps({"models": [{"name": "qwen2.5:3b"}]}).encode())
        code, output = self.beat(node)
        self.assertEqual(code, 1)
        self.assertEqual(node.published, [])
        self.assertIn("qwen2.5:7b", output)

    def test_a_similar_tag_is_not_the_required_model(self):
        tags = json.dumps({"models": [{"name": "qwen2.5:3b"}, {"name": "qwen2.5:7b-instruct"}]}).encode()
        node = FakeNode(tags=tags)
        code, _ = self.beat(node)
        self.assertEqual(code, 1)
        self.assertEqual(node.published, [])

    def test_a_datapoint_that_was_not_written_is_a_failure(self):
        # Silence means "not recovered" to the alarm; a ready node that cannot write must say so.
        node = FakeNode(publish=Result(254, "", "An error occurred (AccessDenied) when calling PutMetricData"))
        code, output = self.beat(node)
        self.assertEqual(code, 2)
        self.assertIn("AccessDenied", output)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 py -m unittest discover -s <WT>/tests/release -t <WT> -p 'test_gpu_node_heartbeat.py'`
Expected: `FAILED (errors=1)` — `heartbeat.py` 가 없다.

- [ ] **Step 3: 구현한다** — `infra/aws/gpu-node/heartbeat.py`

```python
#!/usr/bin/env python3
"""Tell CloudWatch that this node's ollama serves both models.

Auto recovery makes "is there an instance" the wrong question: an instance can run while the join
or the model pull failed. One datapoint a minute says the service itself is up; the alarm and the
reminder Lambda read silence as "not recovered"
(documents docs/superpowers/specs/2026-10-07-gpu-node-auto-recovery-design.md, 3.4).
"""
import http.client
import json
import subprocess
import sys
import urllib.request

REGION = "ap-northeast-2"
NODE_NAME = "devpath-gpu"
METRIC_NAMESPACE = "DevPath/GPU"
METRIC_NAME = "OllamaReady"
POD_NAMESPACE = "devpath"
POD_LABEL = "app=ollama-gpu"
# The two models the ollama-gpu postStart hook pulls (apps/devpath-ollama-gpu/base/deployment.yaml).
REQUIRED_MODELS = frozenset({"qwen2.5:3b", "qwen2.5:7b"})
TAGS_TIMEOUT_SECONDS = 5


class NotReady(Exception):
    """ollama is not serving both models. Expected while a node boots."""


def run_command(args):
    return subprocess.run(args, capture_output=True, text=True, check=False)


def fetch_url(url):
    with urllib.request.urlopen(url, timeout=TAGS_TIMEOUT_SECONDS) as response:
        return response.read()


def ready_pod_address(run):
    listed = run([
        "k3s", "crictl", "pods", "--label", POD_LABEL,
        "--label", f"io.kubernetes.pod.namespace={POD_NAMESPACE}", "--state", "Ready", "-q",
    ])
    pod_ids = listed.stdout.split() if listed.returncode == 0 else []
    if not pod_ids:
        raise NotReady("no Ready ollama-gpu pod on this node")
    inspected = run(["k3s", "crictl", "inspectp", pod_ids[0]])
    try:
        address = json.loads(inspected.stdout)["status"]["network"]["ip"]
    except (ValueError, KeyError, TypeError):
        address = None
    if inspected.returncode != 0 or not isinstance(address, str) or not address:
        raise NotReady("the ollama-gpu pod has no address")
    return address


def served_models(fetch, address):
    try:
        models = json.loads(fetch(f"http://{address}:11434/api/tags"))["models"]
        return {model["name"] for model in models}
    except (OSError, http.client.HTTPException, ValueError, KeyError, TypeError) as error:
        raise NotReady(f"ollama did not list its models ({error.__class__.__name__})") from None


def main(run=run_command, fetch=fetch_url):
    try:
        missing = REQUIRED_MODELS - served_models(fetch, ready_pod_address(run))
        if missing:
            raise NotReady("missing models: " + ", ".join(sorted(missing)))
    except NotReady as reason:
        print(f"not ready: {reason}")
        return 1
    published = run([
        "aws", "cloudwatch", "put-metric-data", "--region", REGION,
        "--namespace", METRIC_NAMESPACE, "--metric-name", METRIC_NAME,
        "--dimensions", f"Node={NODE_NAME}", "--value", "1",
    ])
    if published.returncode != 0:
        print(f"ready, but the datapoint was not written: {published.stderr.strip()[:300]}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 통과를 확인한다**

Run: Step 2 와 같은 명령.
Expected: `Ran 10 tests` · `OK`.

- [ ] **Step 5: 커밋**

```bash
git -C <WT> add infra/aws/gpu-node/heartbeat.py tests/release/test_gpu_node_heartbeat.py
git -C <WT> commit -m "feat(infra): report a heartbeat while ollama-gpu serves both models"
```

### Task 3: systemd 유닛과 user-data 렌더러

**Files:**
- Create: `infra/aws/gpu-node/devpath-gpu-heartbeat.service` · `infra/aws/gpu-node/devpath-gpu-heartbeat.timer` · `infra/aws/gpu-node/render_user_data.py`
- Modify: `.gitattributes` (마지막 줄 뒤에 추가)
- Test: `tests/release/test_gpu_node_user_data.py`

**Interfaces:**
- Consumes: Task 1 `bootstrap.HEARTBEAT_TIMER` · `bootstrap.NODE_NAME` · `bootstrap.REGION`, Task 2 `heartbeat.NODE_NAME` · `heartbeat.REGION`.
- Produces: `render(source_dir=HERE) -> str`(`#cloud-config` 문서) · CLI `py render_user_data.py`(표준 출력으로 바이트) · `py render_user_data.py --sha256`.

- [ ] **Step 1: 실패하는 테스트를 쓴다** — `tests/release/test_gpu_node_user_data.py`

```python
import importlib.util
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "infra" / "aws" / "gpu-node"


def load(name):
    spec = importlib.util.spec_from_file_location(f"tested_gpu_node_{name}", SOURCES / f"{name}.py")
    loaded = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


module = load("render_user_data")
bootstrap = load("bootstrap")
heartbeat = load("heartbeat")

WRITTEN = {
    "/usr/local/lib/devpath-gpu/bootstrap.py": "bootstrap.py",
    "/usr/local/lib/devpath-gpu/heartbeat.py": "heartbeat.py",
    "/etc/systemd/system/devpath-gpu-heartbeat.service": "devpath-gpu-heartbeat.service",
    "/etc/systemd/system/devpath-gpu-heartbeat.timer": "devpath-gpu-heartbeat.timer",
}


class GpuNodeUserDataTest(unittest.TestCase):
    def test_cloud_init_writes_every_source_file_byte_for_byte(self):
        rendered = module.render()
        self.assertTrue(rendered.startswith("#cloud-config\n"))
        document = yaml.safe_load(rendered)
        self.assertEqual([entry["path"] for entry in document["write_files"]], list(WRITTEN))
        for entry in document["write_files"]:
            source = (SOURCES / WRITTEN[entry["path"]]).read_bytes().decode("utf-8")
            self.assertEqual(entry["content"], source, entry["path"])
            self.assertEqual(entry["permissions"], "0644")
            self.assertEqual(entry["owner"], "root:root")

    def test_cloud_init_runs_the_bootstrap_once(self):
        document = yaml.safe_load(module.render())
        self.assertEqual(document["runcmd"], [["/usr/bin/python3", "/usr/local/lib/devpath-gpu/bootstrap.py"]])

    def test_fits_the_ec2_user_data_limit(self):
        self.assertLessEqual(len(module.render().encode("utf-8")), 16384)

    def test_the_same_sources_render_the_same_bytes(self):
        self.assertEqual(module.render(), module.render())
        self.assertNotIn("\r", module.render())

    def test_carries_nothing_that_looks_like_a_secret(self):
        # Everything sensitive is read from Parameter Store at boot. user-data is readable through
        # the console and DescribeInstanceAttribute, so a token or a password must never be here.
        rendered = module.render()
        self.assertIsNone(re.search(r"K10[0-9a-f]{16,}", rendered))
        self.assertIsNone(re.search(r"\b[0-9a-f]{32}\b", rendered))

    def test_refuses_a_source_that_yaml_could_bend(self):
        for name, damage in (
            ("crlf", lambda text: text.replace("\n", "\r\n")),
            ("tab", lambda text: text.replace("    ", "\t", 1)),
            ("no final newline", lambda text: text.rstrip("\n")),
            ("two final newlines", lambda text: text + "\n"),
            ("indented first line", lambda text: "  " + text),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                copy = Path(directory)
                for source in WRITTEN.values():
                    shutil.copy(SOURCES / source, copy / source)
                target = copy / "heartbeat.py"
                target.write_bytes(damage(target.read_bytes().decode("utf-8")).encode("utf-8"))
                with self.assertRaisesRegex(ValueError, "heartbeat.py"):
                    module.render(copy)

    def test_the_units_run_the_heartbeat_that_was_written(self):
        service = (SOURCES / "devpath-gpu-heartbeat.service").read_text(encoding="utf-8")
        timer = (SOURCES / "devpath-gpu-heartbeat.timer").read_text(encoding="utf-8")
        self.assertIn("ExecStart=/usr/bin/python3 /usr/local/lib/devpath-gpu/heartbeat.py\n", service)
        # Exit 1 is "not ready yet", which is normal while a node boots; only exit 2 is a failure.
        self.assertIn("SuccessExitStatus=1\n", service)
        self.assertIn("OnUnitActiveSec=60\n", timer)
        self.assertIn("WantedBy=timers.target\n", timer)
        self.assertEqual(bootstrap.HEARTBEAT_TIMER, "devpath-gpu-heartbeat.timer")

    def test_the_two_scripts_agree_on_who_and_where_they_are(self):
        self.assertEqual(bootstrap.NODE_NAME, heartbeat.NODE_NAME)
        self.assertEqual(bootstrap.REGION, heartbeat.REGION)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 py -m unittest discover -s <WT>/tests/release -t <WT> -p 'test_gpu_node_user_data.py'`
Expected: `FAILED (errors=1)` — `render_user_data.py` 가 없다.

- [ ] **Step 3: 유닛 두 개를 쓴다**

`infra/aws/gpu-node/devpath-gpu-heartbeat.service`:

```ini
[Unit]
Description=Report that ollama-gpu serves both models (devpath GPU node heartbeat)
After=k3s-agent.service

[Service]
Type=oneshot
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/usr/bin/python3 /usr/local/lib/devpath-gpu/heartbeat.py
SuccessExitStatus=1
```

`infra/aws/gpu-node/devpath-gpu-heartbeat.timer`:

```ini
[Unit]
Description=Run the devpath GPU node heartbeat every minute

[Timer]
OnBootSec=60
OnUnitActiveSec=60
AccuracySec=5

[Install]
WantedBy=timers.target
```

- [ ] **Step 4: 렌더러를 구현한다** — `infra/aws/gpu-node/render_user_data.py`

```python
#!/usr/bin/env python3
"""Render the launch template's user-data from the files next to this one.

cloud-init writes the two scripts and the two systemd units, then runs the bootstrap once. The
output holds no secret: everything sensitive is read from Parameter Store at boot.

    py render_user_data.py            # the user-data bytes
    py render_user_data.py --sha256   # their hash, to compare with the launch template
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = (
    ("bootstrap.py", "/usr/local/lib/devpath-gpu/bootstrap.py"),
    ("heartbeat.py", "/usr/local/lib/devpath-gpu/heartbeat.py"),
    ("devpath-gpu-heartbeat.service", "/etc/systemd/system/devpath-gpu-heartbeat.service"),
    ("devpath-gpu-heartbeat.timer", "/etc/systemd/system/devpath-gpu-heartbeat.timer"),
)
RUN = ("/usr/bin/python3", "/usr/local/lib/devpath-gpu/bootstrap.py")
USER_DATA_LIMIT = 16384
INDENT = " " * 6


def render(source_dir=HERE):
    lines = ["#cloud-config", "write_files:"]
    for name, target in FILES:
        text = (Path(source_dir) / name).read_bytes().decode("utf-8")
        # A YAML block scalar keeps these bytes only if the indentation is unambiguous.
        if "\r" in text or "\t" in text or not text.endswith("\n") or text.endswith("\n\n") or text[:1].isspace():
            raise ValueError(
                f"{name}: needs LF line ends, no tabs, an unindented first line and exactly one final newline"
            )
        lines += [f"  - path: {target}", "    owner: root:root", "    permissions: '0644'", "    content: |"]
        lines += [INDENT + line if line else "" for line in text[:-1].split("\n")]
    lines += ["runcmd:", "  - [" + ", ".join(RUN) + "]"]
    rendered = "\n".join(lines) + "\n"
    if len(rendered.encode("utf-8")) > USER_DATA_LIMIT:
        raise ValueError("user-data is over the 16 KB EC2 limit")
    return rendered


def main(argv):
    rendered = render().encode("utf-8")
    if argv[1:] == ["--sha256"]:
        print(hashlib.sha256(rendered).hexdigest())
    else:
        sys.stdout.buffer.write(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 5: `.gitattributes` 에 한 줄을 더한다** (파일 끝)

```
# The launch template's user-data is rendered from these bytes and compared by hash.
infra/aws/** text eol=lf
```

- [ ] **Step 6: 통과를 확인한다**

Run: Step 2 와 같은 명령. 이어서 `py <WT>/infra/aws/gpu-node/render_user_data.py --sha256` 와 `py <WT>/infra/aws/gpu-node/render_user_data.py | wc -c`.
Expected: `Ran 8 tests` · `OK` · 64자 hex 한 줄 · 16384 이하의 바이트 수.

- [ ] **Step 7: 커밋**

```bash
git -C <WT> add .gitattributes infra/aws/gpu-node/devpath-gpu-heartbeat.service infra/aws/gpu-node/devpath-gpu-heartbeat.timer infra/aws/gpu-node/render_user_data.py tests/release/test_gpu_node_user_data.py
git -C <WT> commit -m "feat(infra): render the GPU node user-data from its sources"
```

### Task 4: 반복 통지 Lambda 의 기준을 생존 신호로

**Files:**
- Modify: `infra/aws/gpu-node-absence-watch/handler.py` (전체 교체)
- Modify: `tests/release/test_gpu_node_absence_watch.py` (전체 교체)

**Interfaces:**
- Produces: `handler(event, context, *, ec2=None, sns=None, cloudwatch=None, environ=os.environ, now=None) -> dict`. 신호가 있으면 `{"heartbeats": <합>, "notified": False}`, 없으면 `{"heartbeats": 0, "gpu_instances": [...], "notified": True}`. 환경 변수 `TOPIC_ARN`(필수) · `GPU_ROLE_TAG`(기본 `k3s-agent-gpu`) · `HEARTBEAT_NODE`(기본 `devpath-gpu`).

- [ ] **Step 1: 테스트를 새 기준으로 바꾼다** — `tests/release/test_gpu_node_absence_watch.py` 전체

```python
import datetime
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
HANDLER = ROOT / "infra" / "aws" / "gpu-node-absence-watch" / "handler.py"
SPEC = importlib.util.spec_from_file_location("tested_gpu_node_absence_watch", HANDLER)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

ENVIRON = {
    "TOPIC_ARN": "arn:aws:sns:ap-northeast-2:000000000000:devpath-spot-interruption",
    "GPU_ROLE_TAG": "k3s-agent-gpu",
    "HEARTBEAT_NODE": "devpath-gpu",
}
NOW = datetime.datetime(2026, 10, 7, 3, 0, tzinfo=datetime.timezone.utc)


class FakeCloudWatch:
    def __init__(self, *sums, failure=None):
        self.sums = sums
        self.failure = failure
        self.query = None

    def get_metric_statistics(self, **kwargs):
        self.query = kwargs
        if self.failure:
            raise self.failure
        return {"Datapoints": [{"Sum": value, "Unit": "None"} for value in self.sums]}


class FakeEc2:
    def __init__(self, *pages):
        self.pages = pages
        self.filters = None

    def get_paginator(self, operation):
        assert operation == "describe_instances"
        return self

    def paginate(self, **kwargs):
        self.filters = kwargs["Filters"]
        return iter(self.pages)


class UnusedEc2:
    def get_paginator(self, operation):
        raise AssertionError("EC2 is only asked once the heartbeat is silent")


class FakeSns:
    def __init__(self):
        self.published = []

    def publish(self, **kwargs):
        self.published.append(kwargs)


def page(*instance_ids):
    return {"Reservations": [{"Instances": [{"InstanceId": instance_id}]} for instance_id in instance_ids]}


class GpuNodeAbsenceWatchTest(unittest.TestCase):
    def run_watch(self, cloudwatch, ec2, environ=ENVIRON):
        sns = FakeSns()
        result = module.handler({}, None, ec2=ec2, sns=sns, cloudwatch=cloudwatch, environ=environ, now=NOW)
        return result, sns

    def test_stays_silent_while_the_heartbeat_arrives(self):
        result, sns = self.run_watch(FakeCloudWatch(15.0), UnusedEc2())
        self.assertEqual(sns.published, [])
        self.assertEqual(result, {"heartbeats": 15.0, "notified": False})

    def test_reminds_the_operators_when_no_instance_exists(self):
        # 2026-09-08: the GPU spot node was reclaimed and nobody knew for 23 days.
        result, sns = self.run_watch(FakeCloudWatch(), FakeEc2(page()))
        self.assertEqual(result, {"heartbeats": 0, "gpu_instances": [], "notified": True})
        self.assertEqual(len(sns.published), 1)
        published = sns.published[0]
        self.assertEqual(published["TopicArn"], ENVIRON["TOPIC_ARN"])
        self.assertEqual(published["Subject"], "[DevPath/AWS] GPU node is not serving: no instance")
        self.assertIn("role=k3s-agent-gpu", published["Message"])
        self.assertIn("devpath-gpu-node", published["Message"])
        self.assertIn("runbook-k3s-bootstrap.md", published["Message"])

    def test_says_so_when_an_instance_is_up_but_ollama_is_not(self):
        # The case the instance check could not see: auto recovery launched a node that never
        # came to serve. An instance exists, so "no instance" would send the operator the wrong way.
        result, sns = self.run_watch(FakeCloudWatch(), FakeEc2(page("i-0aaaaaaaaaaaaaaaa")))
        self.assertEqual(result, {"heartbeats": 0, "gpu_instances": ["i-0aaaaaaaaaaaaaaaa"], "notified": True})
        published = sns.published[0]
        self.assertEqual(
            published["Subject"], "[DevPath/AWS] GPU node is not serving: instance up, ollama not ready"
        )
        self.assertIn("i-0aaaaaaaaaaaaaaaa", published["Message"])
        self.assertIn("cloud-init-output.log", published["Message"])
        self.assertIn("FailedMount", published["Message"])

    def test_asks_for_the_last_fifteen_minutes_of_this_node(self):
        cloudwatch = FakeCloudWatch(1.0)
        self.run_watch(cloudwatch, UnusedEc2())
        self.assertEqual(
            cloudwatch.query,
            {
                "Namespace": "DevPath/GPU",
                "MetricName": "OllamaReady",
                "Dimensions": [{"Name": "Node", "Value": "devpath-gpu"}],
                "StartTime": NOW - datetime.timedelta(minutes=15),
                "EndTime": NOW,
                "Period": 900,
                "Statistics": ["Sum"],
            },
        )

    def test_adds_up_split_datapoints(self):
        # A 15-minute window rarely lines up with a period boundary and comes back in two pieces.
        result, sns = self.run_watch(FakeCloudWatch(0.0, 4.0), UnusedEc2())
        self.assertEqual(sns.published, [])
        self.assertEqual(result["heartbeats"], 4.0)

    def test_datapoints_that_sum_to_zero_are_silence(self):
        result, sns = self.run_watch(FakeCloudWatch(0.0, 0.0), FakeEc2(page()))
        self.assertTrue(result["notified"])
        self.assertEqual(len(sns.published), 1)

    def test_a_failed_metric_query_is_an_error_not_silence(self):
        sns = FakeSns()
        with self.assertRaisesRegex(RuntimeError, "throttled"):
            module.handler(
                {}, None, ec2=UnusedEc2(), sns=sns,
                cloudwatch=FakeCloudWatch(failure=RuntimeError("throttled")), environ=ENVIRON, now=NOW,
            )
        self.assertEqual(sns.published, [])

    def test_subjects_fit_what_sns_accepts_for_email(self):
        for subject in (module.SUBJECT_NO_INSTANCE, module.SUBJECT_NOT_READY):
            self.assertTrue(subject.isascii())
            self.assertLess(len(subject), 100)
            self.assertNotIn("\n", subject)

    def test_looks_for_pending_or_running_instances_that_carry_the_role_tag(self):
        ec2 = FakeEc2(page())
        self.run_watch(FakeCloudWatch(), ec2)
        self.assertEqual(
            ec2.filters,
            [
                {"Name": "tag:role", "Values": ["k3s-agent-gpu"]},
                {"Name": "instance-state-name", "Values": ["pending", "running"]},
            ],
        )

    def test_finds_an_instance_on_a_later_page(self):
        result, _ = self.run_watch(FakeCloudWatch(), FakeEc2(page(), page("i-0bbbbbbbbbbbbbbbb")))
        self.assertEqual(result["gpu_instances"], ["i-0bbbbbbbbbbbbbbbb"])

    def test_node_and_role_default_to_the_deployed_names(self):
        cloudwatch, ec2 = FakeCloudWatch(), FakeEc2(page())
        self.run_watch(cloudwatch, ec2, environ={"TOPIC_ARN": ENVIRON["TOPIC_ARN"]})
        self.assertEqual(cloudwatch.query["Dimensions"], [{"Name": "Node", "Value": "devpath-gpu"}])
        self.assertEqual(ec2.filters[0], {"Name": "tag:role", "Values": ["k3s-agent-gpu"]})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 py -m unittest discover -s <WT>/tests/release -t <WT> -p 'test_gpu_node_absence_watch.py'`
Expected: `FAILED` — `handler()` 가 `cloudwatch` · `now` 인자를 받지 않아 `TypeError: handler() got an unexpected keyword argument 'cloudwatch'`.

- [ ] **Step 3: 구현한다** — `infra/aws/gpu-node-absence-watch/handler.py` 전체

```python
"""Keep telling the operators while the GPU node's ollama is not serving.

The EC2 state-change rule reports a reclaim once. If that mail is missed nothing speaks again:
the GPU node was reclaimed on 2026-09-08 and stayed gone, unnoticed, for 23 days. This function
runs on a schedule and publishes to the same SNS topic until the node is back.

"Back" is the node's own heartbeat (infra/aws/gpu-node/heartbeat.py), not the existence of an
instance: with auto recovery an instance can be up while the join or the model pull failed.
"""
import datetime
import os

DEFAULT_ROLE_TAG = "k3s-agent-gpu"
DEFAULT_NODE = "devpath-gpu"
METRIC_NAMESPACE = "DevPath/GPU"
METRIC_NAME = "OllamaReady"
WINDOW = datetime.timedelta(minutes=15)
SUBJECT_NO_INSTANCE = "[DevPath/AWS] GPU node is not serving: no instance"
SUBJECT_NOT_READY = "[DevPath/AWS] GPU node is not serving: instance up, ollama not ready"
MESSAGE_NO_INSTANCE = """\
[DevPath/AWS] GPU node is not serving: no instance
No heartbeat from node {node} for 15 minutes, and no pending or running EC2 instance carries
tag role={role}.

Auto recovery (Auto Scaling group devpath-gpu-node) has not produced an instance. The usual cause
is no spot capacity; the group's activity history says why.
Until the node is back, learning-path generation is down and the Claude fallback of review,
community-seed and retention has nowhere to go.
Runbook: devpath-gitops/docs/runbook-k3s-bootstrap.md 'auto recovery'.

This reminder repeats on a schedule until the heartbeat returns."""
MESSAGE_NOT_READY = """\
[DevPath/AWS] GPU node is not serving: instance up, ollama not ready
No heartbeat from node {node} for 15 minutes, although an instance is up: {instances}.

The instance booted but ollama is not serving both models. Look, in this order, at the node's
/var/log/cloud-init-output.log (the bootstrap), at whether the node joined, and at the ollama-gpu
pod's events (FailedMount means the model-dir parameter no longer matches the volume).
Until it serves, learning-path generation is down and the Claude fallback of review,
community-seed and retention has nowhere to go.
Runbook: devpath-gitops/docs/runbook-k3s-bootstrap.md 'auto recovery'.

This reminder repeats on a schedule until the heartbeat returns."""


def _client(service):
    import boto3  # provided by the Lambda runtime; the tests inject their own clients

    return boto3.client(service)


def heartbeats(cloudwatch, node, now):
    statistics = cloudwatch.get_metric_statistics(
        Namespace=METRIC_NAMESPACE,
        MetricName=METRIC_NAME,
        Dimensions=[{"Name": "Node", "Value": node}],
        StartTime=now - WINDOW,
        EndTime=now,
        Period=int(WINDOW.total_seconds()),
        Statistics=["Sum"],
    )
    return sum(point["Sum"] for point in statistics["Datapoints"])


def gpu_instances(ec2, role):
    pages = ec2.get_paginator("describe_instances").paginate(
        Filters=[
            {"Name": "tag:role", "Values": [role]},
            {"Name": "instance-state-name", "Values": ["pending", "running"]},
        ]
    )
    return [
        instance["InstanceId"]
        for page in pages
        for reservation in page["Reservations"]
        for instance in reservation["Instances"]
    ]


def handler(event, context, *, ec2=None, sns=None, cloudwatch=None, environ=os.environ, now=None):
    node = environ.get("HEARTBEAT_NODE", DEFAULT_NODE)
    role = environ.get("GPU_ROLE_TAG", DEFAULT_ROLE_TAG)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    count = heartbeats(cloudwatch or _client("cloudwatch"), node, now)
    if count > 0:
        return {"heartbeats": count, "notified": False}
    present = gpu_instances(ec2 or _client("ec2"), role)
    subject, message = (
        (SUBJECT_NOT_READY, MESSAGE_NOT_READY) if present else (SUBJECT_NO_INSTANCE, MESSAGE_NO_INSTANCE)
    )
    (sns or _client("sns")).publish(
        TopicArn=environ["TOPIC_ARN"],
        Subject=subject,
        Message=message.format(node=node, role=role, instances=", ".join(present)),
    )
    return {"heartbeats": 0, "gpu_instances": present, "notified": True}
```

- [ ] **Step 4: 통과를 확인한다**

Run: Step 2 와 같은 명령.
Expected: `Ran 11 tests` · `OK`.

- [ ] **Step 5: 커밋**

```bash
git -C <WT> add infra/aws/gpu-node-absence-watch/handler.py tests/release/test_gpu_node_absence_watch.py
git -C <WT> commit -m "feat(infra): remind on a silent heartbeat instead of a missing instance"
```

이 커밋은 **저장소의 소스만** 바꾼다. 운영 Lambda 는 Task 9 에서 바꾼다 — 생존 신호가 없는 지금 배포하면 6시간마다 거짓 통지가 온다.

### Task 5: 런북 「자동 복구」 절과 PR

**Files:**
- Modify: `docs/runbook-k3s-bootstrap.md` — `### 스팟 회수 후 복구 (2026-10-01 실측)` 바로 앞에 새 절을 넣고, 그 절의 첫 문단 앞에 한 줄을 더한다.

- [ ] **Step 1: 새 절을 넣는다** (`### 스팟 회수 후 복구 (2026-10-01 실측)` 줄 바로 위)

````markdown
### 자동 복구 — 같은 이름으로 돌아오는 노드 (2026-10-07 설계, 전환 기록은 아래)

설계 = documents `docs/superpowers/specs/2026-10-07-gpu-node-auto-recovery-design.md`. 회수되면 ASG 가 대체 인스턴스를 띄우고,
기동 스크립트가 **같은 노드 이름(`devpath-gpu`)과 같은 노드 비밀번호**로 조인한다. 서버는 같은 Node 가 돌아온 것으로 보므로
PV 고정이 그대로 맞는다 — 죽은 노드 · 멈춘 파드 · PVC 를 지우지 않는다.

| 리소스 | 이름 |
|---|---|
| ASG | `devpath-gpu-node` — 최소 0 · 최대 1 · 희망 1, 스팟만, 서브넷 2a · 2c · 2d, `AZRebalance` 중지 |
| 기동 템플릿 | `devpath-gpu-node` — AMI · `g6.xlarge` · 120 GiB gp3 · 태그는 「절차」 2 와 같다. 프로파일 `devpath-gpu-node`, IMDSv2 필수(홉 1) |
| 파라미터 | `/devpath/gpu-node/agent-token` · `node-password`(SecureString) · `model-dir` · `k3s-version`(String) |
| 소스 | `infra/aws/gpu-node/` — `bootstrap.py` · `heartbeat.py` · 유닛 2개 · `render_user_data.py` |
| 생존 신호 | `DevPath/GPU` · `OllamaReady` · `Node=devpath-gpu` — 노드가 1분마다, ollama 가 모델 2종을 낼 때만 쓴다 |
| 알람 | `devpath-gpu-ollama-not-ready` — 15분 신호 없음 → 메일, 복귀 → 메일 |

**끄는 법**: `aws autoscaling set-desired-capacity --auto-scaling-group-name devpath-gpu-node --desired-capacity 0`. 인스턴스가 내려가고 과금이 멈춘다. 다시 켜려면 1.

**값을 바꿀 때**

| 무엇이 바뀌면 | 할 일 |
|---|---|
| 서버 k3s 버전 | `/devpath/gpu-node/k3s-version` 을 같은 값으로. 다음 기동부터 적용된다 |
| `ollama-gpu-models` PVC 를 다시 만들었다 | 새 PV 의 `spec.local.path` 를 `/devpath/gpu-node/model-dir` 에 적는다. 지금 노드에는 그 디렉터리가 이미 있다 |
| ollama 가 내려받는 모델 | `infra/aws/gpu-node/heartbeat.py` 의 `REQUIRED_MODELS` — 안 바꾸면 생존 신호가 끊겨 알람이 난다 |
| 기동 스크립트 · 유닛 | `py infra/aws/gpu-node/render_user_data.py` 의 출력으로 기동 템플릿의 새 버전을 만든다. ASG 는 `$Latest` 를 쓴다 |
| 조인 토큰이 샜다 | control-plane 에서 `k3s token delete <id>` → 새 토큰을 만들어 `agent-token` 을 덮어쓴다. 지금 노드는 영향이 없다 |

배포된 user-data 가 저장소와 같은지는 `py infra/aws/gpu-node/render_user_data.py --sha256` 과 기동 템플릿 user-data 의 sha256 을 비교한다.

**증상별**

| 증상 | 원인 | 조치 |
|---|---|---|
| 메일 「no instance」 | ASG 가 인스턴스를 못 얻었다 — 대개 세 AZ 모두 스팟 용량 없음 | `describe-scaling-activities` 로 사유를 본다. 기다리거나, 온디맨드로 띄울지 정한다 |
| 메일 「instance up, ollama not ready」 | 부팅은 됐는데 조인 · 마운트 · 모델 pull 중 하나가 실패 | 노드의 `/var/log/cloud-init-output.log` → `kubectl get node devpath-gpu` → 파드 이벤트 순으로 본다 |
| agent 로그 `Node password rejected` | `node-password` 파라미터가 서버의 `devpath-gpu.node-password.k3s` 와 다르다 | `kubectl delete node devpath-gpu`(시크릿도 함께 사라진다) 뒤 노드에서 `systemctl restart k3s-agent` — 지금 비밀번호로 새로 등록된다 |
| 파드 `FailedMount … path … does not exist` | `model-dir` 가 실제 PV 와 다르다 | 위 표의 「PVC 를 다시 만들었다」 줄 + 노드에서 `mkdir -m 0777 <경로>` |

자동화가 꺼져 있거나 실패했을 때의 수동 절차가 아래 「스팟 회수 후 복구」다.
````

- [ ] **Step 2: 수동 절차의 첫머리에 한 줄을 더한다** (`### 스팟 회수 후 복구 (2026-10-01 실측)` 줄 바로 아래, 빈 줄 하나 뒤)

```markdown
> 2026-10-07 부터 회수는 위 「자동 복구」가 처리한다. 이 절은 자동화를 껐거나 그것이 실패했을 때 쓴다.
```

- [ ] **Step 3: 확인하고 커밋한다**

```bash
git -C <WT> diff --stat
git -C <WT> diff | grep -c $'\r'
git -C <WT> add docs/runbook-k3s-bootstrap.md
git -C <WT> commit -m "docs(runbook): GPU 노드 자동 복구 절 — 구성, 끄는 법, 값 변경, 증상별 조치"
```

Expected: `docs/runbook-k3s-bootstrap.md` 한 파일 · CR 0.

- [ ] **Step 4: 네 테스트 파일을 한 번에 돌린다**

Run: `PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 py -m unittest discover -s <WT>/tests/release -t <WT> -p 'test_gpu_node_*.py'`
Expected: `Ran 44 tests` · `OK (skipped=1)`.

- [ ] **Step 5: PR 을 올리고 CI 뒤 머지한다**

```bash
git -C <WT> push -u origin feat/gpu-node-auto-recovery
gh pr create -R DevPathAi/devpath-gitops --base develop --head feat/gpu-node-auto-recovery --title "feat(infra): GPU 스팟 노드 자동 복구 — 같은 이름으로 돌아오는 노드" --body-file <본문 파일>
gh pr checks <번호> -R DevPathAi/devpath-gitops --watch
gh pr merge <번호> -R DevPathAi/devpath-gitops --merge
```

PR 본문에는 스펙 · 이 계획의 경로, 「운영 리소스는 아직 만들지 않았다 · Lambda 는 전환 뒤에 바꾼다」, 테스트 수를 적는다.
Expected: `mission-spine-release-contract` · `kustomize` 둘 다 pass(기존 383 + 새 38 = 421 tests — Lambda 테스트가 6개에서 11개로 늘고 새 파일이 33개).

---

## Part B — AWS 준비 (서비스 영향 없음 · 컨트롤러 전용)

이 Part 와 Part C 는 AWS MCP 와 SSH 를 쓰므로 서브에이전트에 넘기지 않는다. 계정 `963773969059`, 리전 `ap-northeast-2`.

### Task 6: 파라미터 · 인스턴스 역할 · 읽기 검증

- [ ] **Step 1: `k3s-version` 과 `node-password` 를 만든다** (`run_script` 한 번)

| 호출 | 인자 |
|---|---|
| `ssm:PutParameter` | `Name=/devpath/gpu-node/k3s-version` · `Type=String` · `Value=v1.36.2+k3s1` · `Overwrite=False` · `Description=k3s agent version of the GPU node; must equal the server's` |
| `ssm:PutParameter` | `Name=/devpath/gpu-node/node-password` · `Type=SecureString` · `Value=uuid.uuid4().hex`(스크립트 안에서 만들고 **돌려주지 않는다**) · `Overwrite=False` · `Description=k3s node password of devpath-gpu; a replacement instance rejoins as the same Node with it` |

스크립트가 돌려주는 것은 `{"version": 1, "password_length": 32}` 뿐이다. Expected: 그 값.

- [ ] **Step 2: GPU 노드 전용 조인 토큰을 control-plane 에서 SSM 으로 옮긴다** — 값이 세션을 지나가지 않는다

1. `run_script`: 버킷 `devpath-gpu-token-transfer-963773969059-tmp` 생성(`CreateBucketConfiguration.LocationConstraint=ap-northeast-2`) + `PutPublicAccessBlock` 네 항목 `True`.
2. `get_presigned_url`: `operation=upload` · 그 버킷 · `key=agent-token` · `expires_in=600`.
3. control-plane 에서(SSH):

```bash
sudo k3s token create --ttl 0 --description devpath-gpu-node | curl -sf -o /dev/null -w '%{http_code}\n' -X PUT --data-binary @- '<presigned URL>'
sudo k3s token list
```

Expected: `200` · 목록에 `devpath-gpu-node` 설명의 토큰 한 줄(`TTL` `<forever>`). 목록은 비밀 부분을 보여 주지 않는다.

4. `run_script`: `s3:GetObject` → `Body.strip()` → `re.fullmatch(r"K10[0-9a-f]{64}::[a-z0-9]{6}\.[a-z0-9]{16}", value)` 가 맞으면
   `ssm:PutParameter`(`Name=/devpath/gpu-node/agent-token` · `Type=SecureString` · `Overwrite=False` · `Description=k3s bootstrap token of the GPU node (k3s token list: devpath-gpu-node)`).
   그 뒤 `s3:DeleteObject` · `s3:DeleteBucket`. 돌려주는 것은 `{"format_ok": true, "length": <n>, "version": 1}` 뿐.

Expected: `format_ok: true`. `false` 면 파라미터를 만들지 않고 객체 · 버킷을 지운 뒤 `sudo k3s token delete <id>` 하고 멈춘다(`k3s token create` 의 출력 형식이 예상과 다른 것이다 — 원인을 본 뒤 다시).

- [ ] **Step 3: 인스턴스 역할과 프로파일** (`run_script` 한 번)

`iam:CreateRole` `RoleName=devpath-gpu-node`, 신뢰 정책:

```json
{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]}
```

`iam:PutRolePolicy` `PolicyName=gpu-node`:

```json
{"Version": "2012-10-17", "Statement": [
  {"Sid": "ReadOwnParameters", "Effect": "Allow", "Action": "ssm:GetParameter",
   "Resource": "arn:aws:ssm:ap-northeast-2:963773969059:parameter/devpath/gpu-node/*"},
  {"Sid": "WriteHeartbeat", "Effect": "Allow", "Action": "cloudwatch:PutMetricData", "Resource": "*",
   "Condition": {"StringEquals": {"cloudwatch:namespace": "DevPath/GPU"}}}
]}
```

`iam:CreateInstanceProfile` `InstanceProfileName=devpath-gpu-node` → `iam:AddRoleToInstanceProfile`.

- [ ] **Step 4: 임시 인스턴스로 권한을 실측한다** — 프로파일과 IMDS 설정이 스펙대로 동작하는가

`ec2:RunInstances`: AMI `ami-062cdf7151c071074`(Ubuntu 22.04) · `t3.small` · 키 `devpath-k3s-key` · 서브넷 `subnet-00bb150fb3e236ecb` · SG `sg-0ad7dfa8afe5d1eea` ·
`IamInstanceProfile.Name=devpath-gpu-node` · `MetadataOptions={HttpTokens: required, HttpPutResponseHopLimit: 1, HttpEndpoint: enabled}` · 태그 `Name=devpath-profile-check` `role=profile-check`.
프로파일이 막 만들어져 `Invalid IAM Instance Profile name` 이 나면 10초 뒤 다시.

SSH 로 들어가 `sudo snap install aws-cli --classic` 뒤:

| 명령 | Expected |
|---|---|
| `aws ssm get-parameter --region ap-northeast-2 --name /devpath/gpu-node/node-password --with-decryption --query Parameter.Version --output text` | `1` |
| 같은 명령, `agent-token` | `1` |
| `aws ssm get-parameter --region ap-northeast-2 --name /devpath/gpu-node/k3s-version --query Parameter.Value --output text` | `v1.36.2+k3s1` |
| 같은 명령, `model-dir` | `ParameterNotFound`(아직 없다 — 기동 스크립트가 건너뛰는 경우) |
| `aws ssm get-parameter --region ap-northeast-2 --name /devpath/other` | `AccessDeniedException` (대조군) |
| `aws ec2 describe-instances --region ap-northeast-2` | `UnauthorizedOperation` (대조군) |
| `aws cloudwatch put-metric-data --region ap-northeast-2 --namespace DevPath/GPU --metric-name ProfileCheck --value 1` | 출력 없음 · rc 0 |
| `aws cloudwatch put-metric-data --region ap-northeast-2 --namespace Other/Namespace --metric-name ProfileCheck --value 1` | `AccessDenied` (대조군) |
| `curl -s -o /dev/null -w '%{http_code}\n' http://169.254.169.254/latest/meta-data/` | `401` (IMDSv1 차단) |

`--query Parameter.Version` 으로 읽으므로 값은 화면에 나오지 않는다.
`AccessDeniedException` 이 SecureString 에서만 나면 KMS 권한이 모자란 것이다 — 역할 정책에 `kms:Decrypt`(조건 `kms:ViaService=ssm.ap-northeast-2.amazonaws.com`)를 더하고 다시 잰다.

끝나면 `ec2:TerminateInstances`. Expected: 인스턴스 `shutting-down`.

### Task 7: 기동 템플릿 · ASG(희망 0) · 알람(동작 꺼 둠)

- [ ] **Step 1: user-data 를 만든다** (Task 5 의 PR 이 머지된 `origin/develop` 에서)

```bash
git -C D:/workspace/dpa/devpath-gitops fetch origin
git -C D:/workspace/dpa/devpath-gitops worktree add --detach D:/workspace/dpa/.worktrees/gitops-develop-render origin/develop
py D:/workspace/dpa/.worktrees/gitops-develop-render/infra/aws/gpu-node/render_user_data.py --sha256
py D:/workspace/dpa/.worktrees/gitops-develop-render/infra/aws/gpu-node/render_user_data.py | base64 -w0 > <scratch>/gpu-user-data.b64
```

Expected: sha256 한 줄(런북에 적을 값) · base64 한 줄.

- [ ] **Step 2: 기동 템플릿** — `ec2:CreateLaunchTemplate` `LaunchTemplateName=devpath-gpu-node`, `LaunchTemplateData`:

```json
{
  "ImageId": "ami-09d3bdf0648512f52",
  "InstanceType": "g6.xlarge",
  "KeyName": "devpath-k3s-key",
  "SecurityGroupIds": ["sg-0ad7dfa8afe5d1eea"],
  "IamInstanceProfile": {"Name": "devpath-gpu-node"},
  "BlockDeviceMappings": [{"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 120, "VolumeType": "gp3", "DeleteOnTermination": true}}],
  "MetadataOptions": {"HttpTokens": "required", "HttpPutResponseHopLimit": 1, "HttpEndpoint": "enabled"},
  "TagSpecifications": [
    {"ResourceType": "instance", "Tags": [{"Key": "role", "Value": "k3s-agent-gpu"}, {"Key": "Name", "Value": "devpath-k3s-gpu"}]},
    {"ResourceType": "volume", "Tags": [{"Key": "Name", "Value": "devpath-k3s-gpu"}]}
  ],
  "UserData": "<gpu-user-data.b64 의 한 줄>"
}
```

확인: `ec2:DescribeLaunchTemplateVersions`(`Versions=["$Latest"]`)의 `UserData` 문자열이 `gpu-user-data.b64` 와 **같은 문자열**인가.
이어서 `ec2:RunInstances` 를 `DryRun=True` · `LaunchTemplate={LaunchTemplateName: devpath-gpu-node}` · `MinCount=MaxCount=1` · `SubnetId=subnet-00bb150fb3e236ecb` ·
`InstanceMarketOptions={MarketType: spot}` 로 부른다. Expected: `DryRunOperation`(「Request would have succeeded」).

- [ ] **Step 3: ASG** — `autoscaling:CreateAutoScalingGroup`:

```json
{
  "AutoScalingGroupName": "devpath-gpu-node",
  "MinSize": 0, "MaxSize": 1, "DesiredCapacity": 0,
  "VPCZoneIdentifier": "subnet-08f3b5aa5e95e53b0,subnet-053662e249d717940,subnet-00bb150fb3e236ecb",
  "HealthCheckType": "EC2", "HealthCheckGracePeriod": 300,
  "CapacityRebalance": false,
  "MixedInstancesPolicy": {
    "LaunchTemplate": {
      "LaunchTemplateSpecification": {"LaunchTemplateName": "devpath-gpu-node", "Version": "$Latest"},
      "Overrides": [{"InstanceType": "g6.xlarge"}]
    },
    "InstancesDistribution": {
      "OnDemandBaseCapacity": 0, "OnDemandPercentageAboveBaseCapacity": 0,
      "SpotAllocationStrategy": "price-capacity-optimized"
    }
  }
}
```

그 뒤 `autoscaling:SuspendProcesses`(`ScalingProcesses=["AZRebalance"]`).
확인: `autoscaling:DescribeAutoScalingGroups` — `DesiredCapacity=0` · `Instances=[]` · `SuspendedProcesses` 에 `AZRebalance` 하나.

- [ ] **Step 4: 토픽 정책에 CloudWatch 의 게시를 허용한다**

`sns:GetTopicAttributes` 로 지금 정책(문장 2개: `AllowAccountOwner` · `AllowEventBridgePublish`)을 읽고, 문장 하나를 더해 `sns:SetTopicAttributes`(`AttributeName=Policy`)로 쓴다:

```json
{"Sid": "AllowCloudWatchAlarmPublish", "Effect": "Allow", "Principal": {"Service": "cloudwatch.amazonaws.com"},
 "Action": "SNS:Publish", "Resource": "arn:aws:sns:ap-northeast-2:963773969059:devpath-spot-interruption",
 "Condition": {"ArnLike": {"aws:SourceArn": "arn:aws:cloudwatch:ap-northeast-2:963773969059:alarm:devpath-gpu-ollama-not-ready"}}}
```

확인: 다시 읽은 정책의 문장이 3개이고 앞의 두 개는 그대로다.

- [ ] **Step 5: 알람을 만든다 — 동작은 꺼 둔다** — `cloudwatch:PutMetricAlarm`:

```json
{
  "AlarmName": "devpath-gpu-ollama-not-ready",
  "AlarmDescription": "No OllamaReady heartbeat from node devpath-gpu for 15 minutes: auto recovery did not finish. Start with devpath-gitops/docs/runbook-k3s-bootstrap.md 'auto recovery'. OK means the node serves both models again.",
  "Namespace": "DevPath/GPU", "MetricName": "OllamaReady",
  "Dimensions": [{"Name": "Node", "Value": "devpath-gpu"}],
  "Statistic": "Sum", "Period": 300, "EvaluationPeriods": 3, "DatapointsToAlarm": 3,
  "Threshold": 1, "ComparisonOperator": "LessThanThreshold", "TreatMissingData": "breaching",
  "ActionsEnabled": false,
  "AlarmActions": ["arn:aws:sns:ap-northeast-2:963773969059:devpath-spot-interruption"],
  "OKActions": ["arn:aws:sns:ap-northeast-2:963773969059:devpath-spot-interruption"]
}
```

Expected: 알람이 생기고 곧 `ALARM` 상태가 된다(아직 신호가 없다) — 동작이 꺼져 있어 메일은 오지 않는다. 메일함으로 확인한다.

---

## Part C — 전환 · 확인 · 훈련 (GPU 기능 중단 · 컨트롤러 전용)

**시작 전에 사용자에게 시각을 확인받는다.** Task 8 과 Task 10 은 각각 GPU 기능이 약 10분 멈춘다(Claude 1차 경로는 정상). Task 9 는 서비스에 영향이 없다.

### Task 8: 전환 — 지금 노드를 ASG 노드로

- [ ] **Step 1: 시작 상태를 적는다**

```bash
sudo kubectl get nodes --no-headers
sudo kubectl get pods -n devpath -l app=ollama-gpu -o wide --no-headers
sudo kubectl get pvc -n devpath ollama-gpu-models --no-headers
sudo kubectl get applications -n argocd --no-headers | grep -vc 'Synced *Healthy'
```

Expected: 노드 2대 Ready(`ip-172-31-48-82` · `ip-172-31-60-217`) · 파드 1/1 Running · PVC Bound · 마지막 줄 `0`.

- [ ] **Step 2: 옛 노드를 내린다** (스팟 쿼터 4 vCPU — 두 대를 동시에 띄울 수 없다). 시각 t0 를 적는다.

`ec2:TerminateInstances` `i-09f6b4f41ebd973c7`. 바로 이어서:

```bash
sudo kubectl delete node ip-172-31-60-217
sudo kubectl delete pod -n devpath -l app=ollama-gpu --force --grace-period=0
sudo kubectl delete pvc -n devpath ollama-gpu-models --wait=false
sleep 15; sudo kubectl get pvc -n devpath ollama-gpu-models --no-headers
```

Expected: ArgoCD 가 PVC 를 다시 만들어 `Pending`(소비자를 기다린다). 이 세 삭제를 쓰는 것은 이번이 마지막이다.

- [ ] **Step 3: ASG 를 켠다**

`autoscaling:SetDesiredCapacity`(`AutoScalingGroupName=devpath-gpu-node` · `DesiredCapacity=1`).
`autoscaling:DescribeScalingActivities` 와 `DescribeAutoScalingGroups` 를 20초 간격으로 읽는다.
Expected: 활동 `Successful`, 인스턴스 1대 `InService`. 인스턴스 ID · AZ · 기동 시각을 적는다.
`Failed` 면 `StatusMessage` 를 읽는다 — `MaxSpotInstanceCountExceeded` 는 옛 인스턴스가 아직 `shutting-down` 인 것이다(ASG 가 다시 시도한다).

- [ ] **Step 4: 조인과 파드를 본다**

```bash
sudo kubectl get node devpath-gpu -o jsonpath='{.status.conditions[?(@.type=="Ready")].status} uid={.metadata.uid} gpu={.status.allocatable.nvidia\.com/gpu} taints={.spec.taints}{"\n"}'
sudo kubectl get pods -A -o wide --no-headers --field-selector spec.nodeName=devpath-gpu
sudo kubectl get pvc -n devpath ollama-gpu-models --no-headers
sudo kubectl exec -n devpath deploy/ollama-gpu -- ollama list
```

Expected: `True` · `gpu=1` · 테인트 `devpath.ai/gpu=true:NoSchedule` · 그 노드의 파드는 `ollama-gpu` 와 device plugin 둘 · PVC `Bound` · 모델 2종.
노드 UID 를 적는다(Task 10 에서 같은지 본다). 10분이 지나도 노드가 안 보이면 Step 5 의 로그부터 읽는다.

- [ ] **Step 5: 노드 안을 확인한다** (공인 IP 는 `DescribeInstances` 로)

```bash
sudo tail -8 /var/log/cloud-init-output.log
sudo grep -c 'K10' /var/log/cloud-init-output.log /etc/systemd/system/k3s-agent.service.env
sudo stat -c '%a %U %n' /etc/rancher/node/password /etc/rancher/k3s/agent-token
sudo grep K3S_TOKEN_FILE /etc/systemd/system/k3s-agent.service.env
systemctl is-active devpath-gpu-heartbeat.timer; df -h / | tail -1
curl -s -o /dev/null -w '%{http_code}\n' http://169.254.169.254/latest/meta-data/
```

Expected: 기동 스크립트의 줄 4개(`wrote the node password…` · `no model-dir parameter…` · `k3s agent v1.36.2+k3s1 installed as devpath-gpu…` · `heartbeat timer enabled`) ·
`K10` 개수 두 파일 모두 `0` · 두 파일 `600 root` · `K3S_TOKEN_FILE='/etc/rancher/k3s/agent-token'` · `active` · 117G · `401`.

- [ ] **Step 6: 새 PV 의 경로를 `model-dir` 에 적는다**

```bash
sudo kubectl get pv "$(sudo kubectl get pvc -n devpath ollama-gpu-models -o jsonpath='{.spec.volumeName}')" -o jsonpath='{.spec.local.path} {.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values}{"\n"}'
```

Expected: `/var/lib/rancher/k3s/storage/pvc-<uid>_devpath_ollama-gpu-models ["devpath-gpu"]`.
그 경로로 `ssm:PutParameter`(`Name=/devpath/gpu-node/model-dir` · `Type=String` · `Overwrite=False`). 경로는 비밀이 아니다.

- [ ] **Step 7: 생존 신호와 서비스 경로를 확인한다**

`cloudwatch:GetMetricStatistics`(`DevPath/GPU` · `OllamaReady` · `Node=devpath-gpu` · 지난 10분 · `Period=60` · `Sum`). Expected: 1 인 데이터포인트가 분마다.

```bash
sudo kubectl logs -n devpath deploy/ollama-gpu --since=5m | grep "$(sudo kubectl get pod -n devpath -l app=devpath-ai-svc -o jsonpath='{.items[0].status.podIP}')" | tail -3
sudo kubectl logs -n devpath deploy/devpath-ai-svc --since=40m | grep 'provider latch closed by probe' | tail -3
```

Expected: ai-svc 파드 IP 의 `GET "/api/tags"` 200(노드 간 통신) · 래치가 닫힌 줄 3개(중단 길이에 따라 최대 30분 뒤 — 그때까지 다시 본다).

- [ ] **Step 8: 파드에서는 인스턴스 자격 증명에 닿지 못하는가** (대조군 포함)

```bash
sudo kubectl run imds-check -n devpath --restart=Never --image=curlimages/curl:8.10.1 \
  --overrides='{"spec":{"nodeSelector":{"devpath.ai/gpu":"true"},"tolerations":[{"key":"devpath.ai/gpu","operator":"Equal","value":"true","effect":"NoSchedule"}]}}' \
  --command -- sh -c 'curl -s -m 5 -o /dev/null -w "%{http_code}\n" -X PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 60"; echo "rc=$?"'
sleep 20; sudo kubectl logs -n devpath imds-check; sudo kubectl delete pod -n devpath imds-check
```

Expected: `000` 과 `rc=28`(타임아웃). 노드에서 같은 `curl -X PUT` 은 `200` 이다(대조군).
`--overrides` 가 셸 이스케이프로 깨지면 같은 내용을 매니페스트 파일로 만들어 `kubectl apply -f` 한다.

### Task 9: 감시를 생존 신호로 바꾸고 알람을 확인한다 (서비스 영향 없음)

- [ ] **Step 1: Lambda 를 새 코드로** — 런북 「미복구 반복 통지」의 절차 그대로

`handler.py`(Task 4, `origin/develop`) 하나를 `ZipInfo(date_time=(2026, 10, 7, 0, 0, 0))` · deflate 로 묶는다 → 임시 버킷 + presigned URL 로 올린다 →
`iam:GetRolePolicy`(역할 `devpath-gpu-node-absence-watch` · 정책 `watch`)로 지금 문서(문장 3개: `FindGpuInstances` · `Remind` · `WriteOwnLogs`)를 읽고,
아래 문장을 더한 **네 문장 전체**를 `iam:PutRolePolicy` 로 쓴다(이 호출은 문서를 통째로 바꾼다):

```json
{"Sid": "ReadHeartbeat", "Effect": "Allow", "Action": "cloudwatch:GetMetricStatistics", "Resource": "*"}
```

→ `lambda:UpdateFunctionCode`(`S3Bucket` · `S3Key`) → `CodeSha256` 이 로컬 zip 의 sha256(base64)과 같은지 본다 →
`lambda:UpdateFunctionConfiguration` — `Environment.Variables` 는 통째로 바뀌므로 셋을 다 준다
(`TOPIC_ARN=arn:aws:sns:ap-northeast-2:963773969059:devpath-spot-interruption` · `GPU_ROLE_TAG=k3s-agent-gpu` · `HEARTBEAT_NODE=devpath-gpu`),
`Description=Publishes to devpath-spot-interruption while node devpath-gpu sends no OllamaReady heartbeat` → 버킷 삭제.

- [ ] **Step 2: 호출해 본다** — `lambda:Invoke`

Expected: `{"heartbeats": <0 보다 큰 수>, "notified": false}`. 메일 없음.

- [ ] **Step 3: 알람 동작을 켠다** — `cloudwatch:EnableAlarmActions`(`AlarmNames=["devpath-gpu-ollama-not-ready"]`)

먼저 `DescribeAlarms` 로 상태가 `OK` 인 것을 본다(`ALARM` 인 채로 켜면 그 자체로는 메일이 오지 않지만, 다음 전이에서 `OK` 메일이 온다).
Expected: `StateValue=OK` · `ActionsEnabled=true`.

- [ ] **Step 4: 신호를 일부러 끊어 알람과 반복 통지를 본다** — 서비스는 그대로 돈다

노드에서 `sudo systemctl stop devpath-gpu-heartbeat.timer`. 시각을 적고 20분 기다린다.

| 확인 | Expected |
|---|---|
| `DescribeAlarms` | 15~20분 사이에 `ALARM` |
| 메일함(`from:sns.amazonaws.com "devpath-gpu-ollama-not-ready"`) | `ALARM: "devpath-gpu-ollama-not-ready"` 메일 1통 |
| `lambda:Invoke` | `{"heartbeats": 0, "gpu_instances": ["<지금 인스턴스>"], "notified": true}` + 제목 「…instance up, ollama not ready」 메일 |

그 뒤 `sudo systemctl start devpath-gpu-heartbeat.timer`.

| 확인 | Expected |
|---|---|
| `DescribeAlarms` | 5~10분 안에 `OK` |
| 메일함 | `OK: "devpath-gpu-ollama-not-ready"` 메일 1통 |
| `lambda:Invoke` | `notified: false` |

### Task 10: 훈련 — 일부러 회수시킨다

- [ ] **Step 1: 종료한다.** 시각 t0 · 종료 전 노드 UID · 파드 이름을 적는다.

`autoscaling:TerminateInstanceInAutoScalingGroup`(`InstanceId=<지금 인스턴스>` · `ShouldDecrementDesiredCapacity=False`).

- [ ] **Step 2: 돌아오는 것을 잰다** — 15초 간격으로 한 줄씩 적는다

```bash
sudo kubectl get node devpath-gpu -o jsonpath='{.status.conditions[?(@.type=="Ready")].status} uid={.metadata.uid} ip={.status.addresses[?(@.type=="InternalIP")].address}{"\n"}'
sudo kubectl get pods -n devpath -l app=ollama-gpu --no-headers
sudo kubectl exec -n devpath deploy/ollama-gpu -- ollama list 2>/dev/null | tail -2
```

적을 시각: 대체 인스턴스 기동(ASG 활동) · Node Ready · 파드 Running · 모델 2종 · 생존 신호 재개(`GetMetricStatistics`).

| 기준 | Expected |
|---|---|
| G1 | t0 부터 모델 2종까지 10분 안 |
| 같은 노드인가 | UID 가 종료 전과 같다. InternalIP 는 새 값 |
| 지운 것 | 없다 — `kubectl delete` 를 한 번도 쓰지 않는다 |
| 실패한 파드 | `kubectl get pods -n devpath -l app=ollama-gpu` 에 `Failed` · `UnexpectedAdmissionError` 가 남는가. 남으면 개수와 이유를 적는다(스펙 3.6 의 device plugin 순서) |
| 알람 | 15분 안에 돌아오면 `ALARM` 으로 가지 않는다 |
| 메일 | 종료 통지(규칙 ②)만 온다 |

- [ ] **Step 3: 서비스 경로를 본다** — Task 8 Step 7 과 같은 두 명령

Expected: ai-svc 의 `GET "/api/tags"` 200 이 새 노드로 다시 찍힌다 · 래치가 닫힌다.

- [ ] **Step 4: 10분을 넘겼거나 사람이 손을 댔다면**

훈련은 실패다. 손댄 단계와 이유를 적고, 원인을 고친 뒤(기동 스크립트면 Task 1 로 돌아가 테스트부터) 다시 한다. 급하면 ASG 희망 0 + 런북의 수동 절차로 되돌린다.

### Task 11: 기록

- [ ] **Step 1: 런북에 실측을 적는다** (gitops 브랜치 `docs/gpu-auto-recovery-record`, develop 으로 PR)

「자동 복구」 절 끝에 `**전환과 훈련(실측)**` 단락을 더한다 — 전환 시각과 중단 길이, 훈련의 타임라인(t0 · 기동 · Ready · Running · 모델 · 신호), UID 가 같았는지,
실패한 파드가 남았는지, 알람 확인의 시각(ALARM · OK), user-data sha256, Lambda `CodeSha256`, 기동 템플릿 버전, 현재 인스턴스 ID.
「확정값」 표의 노드 이름 · 「미복구 반복 통지」 절의 판정 문장(「태그 인스턴스가 없으면」 → 「생존 신호가 15분 없으면」)과 Lambda 표를 새 기준으로 고친다.
`### 스팟 회수 후 복구` 의 3~5 단계에 「같은 이름으로 띄웠다면 필요 없다」를 적는다.

- [ ] **Step 2: 핸드오프와 메모리**

documents `docs/superpowers/handoff-2026-10-06-session-close.md` 에 §9 를 더한다 — 점검 대상이 「노드 `devpath-gpu` · ASG `devpath-gpu-node` · 알람 상태」로 바뀐 것, 끄는 법, 남은 것(Slack · publisher · 다음 캠페인).
메모리 `devpath-gpu-spot-node-ops.md` 를 새 구조로 고친다(현재 인스턴스 ID 는 ASG 가 바꾸므로 「ASG 에서 읽는다」로).

- [ ] **Step 3: 정리**

`D:/workspace/dpa/.worktrees/gitops-gpu-auto-recovery` · `gitops-develop-render` 워크트리를 지운다(머지 확인 뒤). 동결 head 4개와 Argo 16 앱 Synced/Healthy 를 다시 본다.

---

## Self-Review 결과

- **스펙 대조**: G1 → Task 10 · G2 → Task 2 · 4 · 7 · 9 · G3 → Task 1(테스트 4개) · Task 6 Step 2 · Task 8 Step 5 · G4 → Global Constraints · G5 → Task 5 런북 · 3.2 구성 요소 → Task 1~7 · 3.4 감시 → Task 4 · 7 · 9 · 3.5 보안 → Task 6 Step 4 · Task 8 Step 8 · 3.6 잔여 위험의 「훈련에서 관찰」 → Task 10 Step 2 · 6절 순서 → Part B → C.
- **스펙에 없던 것**: `model-dir` 경로 검증(Review Focus 1) — 스펙은 「디렉터리를 만든다」만 적었다. 0777 로 만드는 경로이므로 저장소 루트 밖을 거부하게 했다.
- **이름 일치**: `HEARTBEAT_TIMER` · `NODE_NAME` · `REGION` 은 Task 3 의 테스트가 두 스크립트와 유닛 파일 이름을 서로 맞춰 본다. Lambda 의 `METRIC_NAMESPACE` · `METRIC_NAME` · 차원은 Task 2 의 `PUBLISH` 와 Task 4 의 조회 단언이 같은 문자열을 쓴다.
