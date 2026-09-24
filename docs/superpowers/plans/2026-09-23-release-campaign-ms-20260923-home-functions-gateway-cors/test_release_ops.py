"""Unit tests for release_ops (campaign preflight helpers): pure parsing/arithmetic and the remote script contracts."""
import datetime as dt
import unittest

import release_ops as ops


class NotAfterTest(unittest.TestCase):
    def test_parses_the_openssl_enddate_form(self):
        parsed = ops.parse_not_after("notAfter=Sep 21 00:41:53 2036 GMT")
        self.assertEqual(dt.datetime(2036, 9, 21, 0, 41, 53, tzinfo=dt.timezone.utc), parsed)

    def test_parses_a_bare_value_and_single_digit_days(self):
        parsed = ops.parse_not_after("Aug  9 10:00:20 2036 GMT")
        self.assertEqual(dt.datetime(2036, 8, 9, 10, 0, 20, tzinfo=dt.timezone.utc), parsed)

    def test_days_left_is_floored_and_can_be_negative(self):
        now = dt.datetime(2026, 9, 24, 5, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(29, ops.days_left(dt.datetime(2026, 10, 23, 23, 0, tzinfo=dt.timezone.utc), now))
        self.assertEqual(-1, ops.days_left(dt.datetime(2026, 9, 23, 12, 10, tzinfo=dt.timezone.utc), now))

    def test_tls_report_parses_remote_lines_and_flags_short_lifetimes(self):
        text = (
            "devpath-staging/sandbox-runner-server-tls/ca.pem: notAfter=Sep 21 00:41:53 2036 GMT | subject=CN = x\n"
            "devpath/sandbox-runner-mtls/cert.pem: notAfter=Oct  1 10:00:21 2026 GMT | subject=CN = y\n"
            "devpath/sandbox-runner-ca: (absent)\n"
        )
        now = dt.datetime(2026, 9, 24, 5, 0, tzinfo=dt.timezone.utc)
        rows = ops.tls_rows(text, now)
        self.assertEqual(
            [("devpath-staging", "sandbox-runner-server-tls", "ca.pem", 3649), ("devpath", "sandbox-runner-mtls", "cert.pem", 7)],
            [(r.namespace, r.secret, r.key, r.days_left) for r in rows if r.days_left is not None],
        )
        absent = [r for r in rows if r.days_left is None]
        self.assertEqual([("devpath", "sandbox-runner-ca")], [(r.namespace, r.secret) for r in absent])
        ok, failures = ops.tls_verdict(rows, min_days=30)
        self.assertFalse(ok)
        self.assertEqual({"devpath/sandbox-runner-mtls/cert.pem", "devpath/sandbox-runner-ca"}, set(failures))
        ok, failures = ops.tls_verdict([r for r in rows if r.secret == "sandbox-runner-server-tls"], min_days=30)
        self.assertTrue(ok)
        self.assertEqual([], failures)


class GateTest(unittest.TestCase):
    def test_measurements_are_parsed_from_the_labelled_psql_output(self):
        text = "sandbox_sessions_bytes=1048576\nsupport_requests_rows=42\nsupport_requests_bytes=81920\nduplicate_active_users=0\n"
        self.assertEqual(
            {"sandbox_sessions_bytes": 1048576, "support_requests_rows": 42, "support_requests_bytes": 81920, "duplicate_active_users": 0},
            ops.parse_measurements(text),
        )

    def test_measurement_parsing_refuses_missing_or_non_integer_values(self):
        with self.assertRaises(ValueError):
            ops.parse_measurements("sandbox_sessions_bytes=1\nsupport_requests_rows=2\n")
        with self.assertRaises(ValueError):
            ops.parse_measurements("sandbox_sessions_bytes=1\nsupport_requests_rows=x\nsupport_requests_bytes=3\nduplicate_active_users=0\n")

    def test_bounds_add_headroom_and_round_bytes_up_to_whole_mebibytes(self):
        measured = {"sandbox_sessions_bytes": 1048576, "support_requests_rows": 42, "support_requests_bytes": 81920, "duplicate_active_users": 0}
        bounds = ops.gate_bounds(measured)
        # bytes: x1.25 then rounded up to the next MiB; rows: x1.25 + 100, integer
        self.assertEqual(2 * 1048576, bounds["max-sandbox-sessions-bytes"])
        self.assertEqual(1048576, bounds["max-support-requests-bytes"])
        self.assertEqual(152, bounds["max-support-requests-rows"])
        self.assertEqual("true", bounds["maintenance-approved"])
        self.assertEqual({"maintenance-approved", "max-sandbox-sessions-bytes", "max-support-requests-rows", "max-support-requests-bytes"}, set(bounds))

    def test_bounds_never_fall_below_the_measurement(self):
        measured = {"sandbox_sessions_bytes": 3, "support_requests_rows": 0, "support_requests_bytes": 0, "duplicate_active_users": 0}
        bounds = ops.gate_bounds(measured)
        self.assertGreaterEqual(bounds["max-sandbox-sessions-bytes"], 3)
        self.assertGreaterEqual(bounds["max-support-requests-rows"], 0)
        self.assertGreaterEqual(bounds["max-support-requests-bytes"], 0)
        self.assertEqual(1048576, bounds["max-sandbox-sessions-bytes"])

    def test_bounds_refuse_duplicate_active_users(self):
        measured = {"sandbox_sessions_bytes": 1, "support_requests_rows": 1, "support_requests_bytes": 1, "duplicate_active_users": 2}
        with self.assertRaisesRegex(ValueError, "duplicate_active_users"):
            ops.gate_bounds(measured)


class SshTransportTest(unittest.TestCase):
    def test_scripts_reach_the_node_as_bytes_without_carriage_returns(self):
        # Windows text-mode pipes rewrite "\n" as "\r\n"; bash then sees `name="x\r"` and kubectl rejects the pod name.
        from unittest import mock
        import subprocess

        captured = {}

        def fake_run(cmd, **kwargs):
            captured.update(kwargs)
            captured["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout=b"ok\n", stderr=b"")

        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            done = ops.ssh("set -eu\necho ok\n")
        self.assertIsInstance(captured["input"], bytes)
        self.assertNotIn(b"\r", captured["input"])
        self.assertFalse(captured.get("text", False))
        self.assertEqual("ok\n", done.stdout)
        self.assertEqual("", done.stderr)
        self.assertEqual(0, done.returncode)
        self.assertEqual(["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15", "-i", ops.SSH_KEY, ops.SSH_HOST, "bash -s"], captured["cmd"])


class RemoteScriptContractTest(unittest.TestCase):
    def test_measurement_pod_takes_credentials_from_the_secret_not_the_command_line(self):
        script = ops.MEASURE_SCRIPT
        self.assertIn('"secretKeyRef"', script)
        self.assertIn('"platform-db"', script)
        for key in ("db-url", "db-user", "db-password"):
            self.assertIn(f'"key": "{key}"', script)
        self.assertNotIn("PGPASSWORD=", script.split("secretKeyRef")[0])
        # one-shot pod: never restarted, read back through `kubectl logs` after it succeeded (attach loses the first
        # line), always deleted on exit even when the wait fails
        self.assertIn("--restart=Never", script)
        self.assertNotIn(" -i ", script)
        self.assertIn("--for=jsonpath='{.status.phase}'=Succeeded", script)
        self.assertLess(script.index("trap '"), script.index("kubectl -n devpath run"))
        self.assertIn('delete pod "$name" --ignore-not-found', script)
        self.assertIn('logs "$name"\n', script)
        self.assertIn("ON_ERROR_STOP=1", script)
        self.assertIn("pg_total_relation_size('sandbox_sessions')", script)
        self.assertIn("pg_total_relation_size('support_requests')", script)
        self.assertIn("count(*) FROM support_requests", script)
        self.assertIn("status IN ('ALLOCATING', 'RUNNING')", script)
        self.assertIn("postgres:16-alpine", script)

    def test_measurement_script_is_read_only(self):
        # the SQL the pod runs only reads; the kubectl wrapper only creates/waits/reads logs/deletes its own pod
        sql = ops._MEASURE_COMMAND.lower()
        for forbidden in ("insert ", "update ", "delete ", "drop ", "alter ", "lock table", "truncate", "create "):
            self.assertNotIn(forbidden, sql)
        wrapper = ops.MEASURE_SCRIPT.lower()
        for forbidden in ("kubectl apply", "kubectl patch", "kubectl edit", "kubectl exec", "kubectl scale", "delete configmap", "delete deploy"):
            self.assertNotIn(forbidden, wrapper)
        self.assertEqual(1, wrapper.count("delete pod"))

    def test_gate_scripts_name_the_exact_configmap_and_keys(self):
        self.assertEqual("sandbox-migration-gate", ops.GATE_NAME)
        place = ops.gate_place_script({"maintenance-approved": "true", "max-sandbox-sessions-bytes": 1, "max-support-requests-rows": 2, "max-support-requests-bytes": 3})
        self.assertIn("create configmap sandbox-migration-gate", place)
        for literal in ("--from-literal=maintenance-approved=true", "--from-literal=max-sandbox-sessions-bytes=1",
                        "--from-literal=max-support-requests-rows=2", "--from-literal=max-support-requests-bytes=3"):
            self.assertIn(literal, place)
        self.assertIn("-n devpath ", place)
        recall = ops.gate_recall_script()
        self.assertIn("delete configmap sandbox-migration-gate", recall)
        self.assertIn("-n devpath ", recall)

    def test_argo_refresh_touches_every_application_with_the_refresh_annotation(self):
        script = ops.ARGO_REFRESH_SCRIPT
        self.assertIn("get applications -o name", script)
        self.assertIn("argocd.argoproj.io/refresh=normal", script)
        self.assertIn("--overwrite", script)


if __name__ == "__main__":
    unittest.main()
