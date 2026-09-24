"""Campaign preflight and operations helpers that touch the production cluster over SSH (read-only unless named `place`/`recall`).

- TLS: expiry of the static sandbox-runner secrets in `devpath-staging` and `devpath` (2026-09-23: a 30-day staging
  certificate expired and the validate journey died in its sandbox step).
- Migration maintenance gate: the shared migration Job's init container `sandbox-low-lock-preflight` reads the
  ConfigMap `sandbox-migration-gate` (maintenance-approved + three bounds) and refuses when the live tables exceed
  the approved bounds. The operator measures the tables with the very same queries right before promote, places the
  gate with a little headroom, and recalls it after the OFF phase (2026-09-24: the missing gate cost ~6 minutes of
  fence downtime; 9/21 handoffs: "release-by-release, by hand, from the latest measurement").
- Argo: `argocd.argoproj.io/refresh=normal` on every Application so a new gitops main commit converges before the
  runtime verifier's wait ends (Argo polls every 3 minutes); `MainWatcher` does that whenever origin/main moves.

Windows: run scripts through `ssh ... 'bash -s'` / `'python3 -'` with the script on stdin so quoting never leaks.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass

SSH_HOST = "ubuntu@13.124.153.105"
SSH_KEY = os.path.expanduser("~/.ssh/devpath-k3s-key-lf.pem")
NS_PROD = "devpath"
NS_STAGING = "devpath-staging"
GATE_NAME = "sandbox-migration-gate"
GATE_KEYS = ("maintenance-approved", "max-sandbox-sessions-bytes", "max-support-requests-rows", "max-support-requests-bytes")
TLS_SECRETS = ("sandbox-runner-server-tls", "sandbox-runner-mtls", "sandbox-runner-ca")
MEASURE_IMAGE = "docker.io/library/postgres:16-alpine"
MIB = 1048576
_MONTHS = {m: i for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
_NOT_AFTER = re.compile(r"(?:notAfter=)?\s*([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})\s+(\d{4})\s+GMT")


def ssh(script: str, *, interpreter: str = "bash -s", timeout: int = 300) -> subprocess.CompletedProcess:
    """Run `script` on the production node through the named interpreter reading stdin; stdout/stderr stay separate.

    The script travels as UTF-8 bytes: a Windows text-mode pipe would rewrite "\\n" as "\\r\\n" and bash would then
    carry a trailing "\\r" into every value (kubectl refused `gate-measure-<ts>\\r` as a pod name, 2026-09-24).
    """
    done = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15", "-i", SSH_KEY, SSH_HOST, interpreter],
        input=script.replace("\r\n", "\n").encode("utf-8"), capture_output=True, timeout=timeout,
    )
    return subprocess.CompletedProcess(
        done.args, done.returncode,
        stdout=(done.stdout or b"").decode("utf-8", errors="replace"),
        stderr=(done.stderr or b"").decode("utf-8", errors="replace"),
    )


def _ok(done: subprocess.CompletedProcess, label: str) -> str:
    if done.returncode != 0:
        raise RuntimeError(f"{label} failed ({done.returncode}): {(done.stderr or '')[-600:]}")
    return done.stdout


# ---------------------------------------------------------------- TLS -----------------------------------------------
TLS_SCRIPT = f"""
import base64, json, subprocess
def kget(ns, kind, name):
    p = subprocess.run(["sudo", "kubectl", "-n", ns, "get", kind, name, "-o", "json"], capture_output=True, text=True)
    return json.loads(p.stdout) if p.returncode == 0 else None
for ns in ({NS_STAGING!r}, {NS_PROD!r}):
    for s in {TLS_SECRETS!r}:
        sec = kget(ns, "secret", s)
        if not sec:
            print(f"{{ns}}/{{s}}: (absent)")
            continue
        for k, v in sorted(sec["data"].items()):
            raw = base64.b64decode(v)
            if b"BEGIN CERTIFICATE" in raw:
                o = subprocess.run(["openssl", "x509", "-enddate", "-subject", "-noout"], input=raw, capture_output=True)
                print(f"{{ns}}/{{s}}/{{k}}: " + o.stdout.decode().strip().replace("\\n", " | "))
"""


@dataclass(frozen=True)
class TlsRow:
    namespace: str
    secret: str
    key: str | None
    not_after: dt.datetime | None
    days_left: int | None

    @property
    def label(self) -> str:
        return f"{self.namespace}/{self.secret}" + (f"/{self.key}" if self.key else "")


def parse_not_after(text: str) -> dt.datetime:
    match = _NOT_AFTER.search(text)
    if match is None:
        raise ValueError(f"not an openssl notAfter value: {text!r}")
    mon, day, hh, mm, ss, year = match.groups()
    return dt.datetime(int(year), _MONTHS[mon], int(day), int(hh), int(mm), int(ss), tzinfo=dt.timezone.utc)


def days_left(not_after: dt.datetime, now: dt.datetime) -> int:
    return math.floor((not_after - now).total_seconds() / 86400)


def tls_rows(text: str, now: dt.datetime) -> list[TlsRow]:
    rows: list[TlsRow] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        head, rest = line.split(":", 1)
        parts = head.split("/")
        if rest.strip() == "(absent)":
            rows.append(TlsRow(parts[0], parts[1], None, None, None))
            continue
        not_after = parse_not_after(rest)
        rows.append(TlsRow(parts[0], parts[1], parts[2], not_after, days_left(not_after, now)))
    return rows


def tls_verdict(rows: list[TlsRow], *, min_days: int) -> tuple[bool, list[str]]:
    failures = [r.label for r in rows if r.days_left is None or r.days_left < min_days]
    return (not failures, failures)


def tls_check(*, min_days: int = 30, now: dt.datetime | None = None) -> tuple[bool, list[str], list[TlsRow]]:
    now = now or dt.datetime.now(dt.timezone.utc)
    rows = tls_rows(_ok(ssh(TLS_SCRIPT, interpreter="python3 -"), "tls check"), now)
    if not rows:
        raise RuntimeError("tls check returned no secrets")
    ok, failures = tls_verdict(rows, min_days=min_days)
    return ok, failures, rows


# ---------------------------------------------------------------- migration maintenance gate -------------------------
_MEASURE_COMMAND = (
    "export PGCONNECT_TIMEOUT=5; url=\"${FLYWAY_URL#jdbc:}\"; "
    "q(){ psql \"$url\" -v ON_ERROR_STOP=1 -Atc \"$1\"; }; "
    "echo sandbox_sessions_bytes=$(q \"SELECT pg_total_relation_size('sandbox_sessions')\"); "
    "echo support_requests_rows=$(q \"SELECT count(*) FROM support_requests\"); "
    "echo support_requests_bytes=$(q \"SELECT pg_total_relation_size('support_requests')\"); "
    "echo duplicate_active_users=$(q \"SELECT count(*) FROM (SELECT user_id FROM sandbox_sessions "
    "WHERE status IN ('ALLOCATING', 'RUNNING') GROUP BY user_id HAVING count(*) > 1) d\"); "
    "echo active_client_sessions=$(q \"SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
    "AND pid <> pg_backend_pid() AND backend_type = 'client backend' AND state <> 'idle'\")"
)
_MEASURE_OVERRIDES = json.dumps({
    "spec": {
        "restartPolicy": "Never",
        "containers": [{
            "name": "measure",
            "image": MEASURE_IMAGE,
            "imagePullPolicy": "IfNotPresent",
            "command": ["sh", "-c", _MEASURE_COMMAND],
            "env": [
                {"name": "FLYWAY_URL", "valueFrom": {"secretKeyRef": {"name": "platform-db", "key": "db-url"}}},
                {"name": "PGUSER", "valueFrom": {"secretKeyRef": {"name": "platform-db", "key": "db-user"}}},
                {"name": "PGPASSWORD", "valueFrom": {"secretKeyRef": {"name": "platform-db", "key": "db-password"}}},
            ],
        }],
    }
}, indent=1)
# Same queries as gitops apps/devpath-migration/base/sandbox-preflight.yaml; credentials come from the platform-db
# secret through env (never the command line); the pod is one-shot and read-only. The output is read back with
# `kubectl logs` after the pod succeeded: `kubectl run -i` attaches late and loses the first line (2026-09-24).
MEASURE_SCRIPT = f"""set -eu
name="gate-measure-$(date +%s)"
overrides=$(cat <<'JSON'
{_MEASURE_OVERRIDES}
JSON
)
trap 'sudo kubectl -n {NS_PROD} delete pod "$name" --ignore-not-found >/dev/null 2>&1 || true' EXIT
sudo kubectl -n {NS_PROD} run "$name" --restart=Never --image={MEASURE_IMAGE} --image-pull-policy=IfNotPresent --overrides="$overrides" >/dev/null
if ! sudo kubectl -n {NS_PROD} wait pod/"$name" --for=jsonpath='{{.status.phase}}'=Succeeded --timeout=120s >/dev/null 2>&1; then
  echo "measurement pod did not succeed: phase=$(sudo kubectl -n {NS_PROD} get pod "$name" -o jsonpath='{{.status.phase}}')" >&2
  sudo kubectl -n {NS_PROD} logs "$name" >&2 || true
  exit 5
fi
sudo kubectl -n {NS_PROD} logs "$name"
"""
REQUIRED_MEASUREMENTS = ("sandbox_sessions_bytes", "support_requests_rows", "support_requests_bytes", "duplicate_active_users")


def parse_measurements(text: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in text.splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().split()[-1]  # tolerate a stderr prompt glued in front of the first key
        if key in REQUIRED_MEASUREMENTS or key == "active_client_sessions":
            if not re.fullmatch(r"\d+", value.strip()):
                raise ValueError(f"measurement {key} is not an integer: {value!r}")
            values[key] = int(value.strip())
    missing = [k for k in REQUIRED_MEASUREMENTS if k not in values]
    if missing:
        raise ValueError(f"measurements missing: {missing}")
    return values


def gate_bounds(measured: dict[str, int], *, headroom: float = 0.25, extra_rows: int = 100) -> dict[str, object]:
    if measured["duplicate_active_users"] != 0:
        raise ValueError(f"duplicate_active_users={measured['duplicate_active_users']}; the migration preflight will refuse")

    def bytes_bound(value: int) -> int:
        return max(MIB, math.ceil(value * (1 + headroom) / MIB) * MIB)

    return {
        "maintenance-approved": "true",
        "max-sandbox-sessions-bytes": bytes_bound(measured["sandbox_sessions_bytes"]),
        "max-support-requests-rows": int(measured["support_requests_rows"] * (1 + headroom)) + extra_rows,
        "max-support-requests-bytes": bytes_bound(measured["support_requests_bytes"]),
    }


def gate_place_script(bounds: dict[str, object]) -> str:
    literals = " ".join(f"--from-literal={key}={bounds[key]}" for key in GATE_KEYS)
    return (
        "set -eu\n"
        f"if sudo kubectl -n {NS_PROD} get configmap {GATE_NAME} >/dev/null 2>&1; then echo 'gate already exists' >&2; exit 3; fi\n"
        f"sudo kubectl -n {NS_PROD} create configmap {GATE_NAME} {literals}\n"
        f"sudo kubectl -n {NS_PROD} get configmap {GATE_NAME} -o jsonpath='{{.data}}'\n"
    )


def gate_recall_script() -> str:
    return (
        "set -eu\n"
        f"busy=$(sudo kubectl -n {NS_PROD} get pods --field-selector=status.phase!=Succeeded,status.phase!=Failed -o json "
        f"| python3 -c \"import json,sys; d=json.load(sys.stdin); print(sum('{GATE_NAME}' in json.dumps(p['spec']) for p in d['items']))\")\n"
        "[ \"$busy\" = 0 ] || { echo \"a live pod still references the gate ($busy)\" >&2; exit 4; }\n"
        f"sudo kubectl -n {NS_PROD} delete configmap {GATE_NAME}\n"
    )


def gate_exists() -> bool:
    return ssh(f"sudo kubectl -n {NS_PROD} get configmap {GATE_NAME} -o name").returncode == 0


def measure_gate() -> dict[str, int]:
    return parse_measurements(_ok(ssh(MEASURE_SCRIPT, timeout=240), "gate measurement"))


def gate_place(bounds: dict[str, object]) -> str:
    return _ok(ssh(gate_place_script(bounds)), "gate place").strip()


def gate_recall() -> str:
    return _ok(ssh(gate_recall_script()), "gate recall").strip()


# ---------------------------------------------------------------- Argo ----------------------------------------------
ARGO_REFRESH_SCRIPT = (
    "set -eu\n"
    "for a in $(sudo kubectl -n argocd get applications -o name); do "
    "sudo kubectl -n argocd annotate \"$a\" argocd.argoproj.io/refresh=normal --overwrite >/dev/null; done\n"
    "echo refreshed $(sudo kubectl -n argocd get applications -o name | wc -l) applications\n"
)


def argo_refresh_all() -> str:
    return _ok(ssh(ARGO_REFRESH_SCRIPT), "argo refresh").strip()


class MainWatcher(threading.Thread):
    """Poll origin/main of a gitops clone; on every new head, force an Argo refresh of all Applications."""

    def __init__(self, repo_dir: str, *, interval: int = 20, log=print):
        super().__init__(daemon=True, name="gitops-main-watcher")
        self.repo_dir, self.interval, self.log = repo_dir, interval, log
        self._stop = threading.Event()
        self.seen: str | None = None
        self.refreshed: list[str] = []

    def head(self) -> str | None:
        done = subprocess.run(["git", "-C", self.repo_dir, "ls-remote", "origin", "refs/heads/main"],
                              capture_output=True, text=True, encoding="utf-8")
        return done.stdout.split()[0] if done.returncode == 0 and done.stdout.strip() else None

    def run(self) -> None:
        self.seen = self.head()
        while not self._stop.wait(self.interval):
            current = self.head()
            if current and current != self.seen:
                self.seen = current
                try:
                    self.log(f"[{time.strftime('%H:%M:%SZ', time.gmtime())}] main -> {current[:8]}: {argo_refresh_all()}")
                    self.refreshed.append(current)
                except Exception as exc:  # noqa: BLE001 - the watcher must never kill the operator step
                    self.log(f"argo refresh failed for {current[:8]}: {exc}")

    def stop(self) -> None:
        self._stop.set()
