#!/usr/bin/env python3
"""Render the service-applied-revision publisher artifacts from the executed 2026-09-21 pipeline-defects publisher by
exact, counted substitution: helper workflow, contract test, staged dispatcher, operator transaction and its unit test.

Usage: render_r3fix_publisher.py <publisher dir>
Reads  <dir>/prec-0921-live/{helper.yml,contract_test.py,dispatcher.yml} (git show of the executed branches),
       <dir>/prec-0921/{run_pipeline_defects_main_publish.py,test_run_pipeline_defects_main_publish.py} and
       <dir>/target.txt (TARGET_SHA / TARGET_TREE).
Writes <dir>/rendered/{helper.yml,test_service_applied_revision_main_publish.py,dispatcher.yml,
       run_service_applied_revision_main_publish.py,test_run_service_applied_revision_main_publish.py}.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

D = Path(sys.argv[1])
OUT = D / "rendered"
OUT.mkdir(exist_ok=True)
target = dict(line.split("=", 1) for line in (D / "target.txt").read_text(encoding="utf-8").split())
TARGET_SHA, TARGET_TREE = target["TARGET_SHA"], target["TARGET_TREE"]
assert re.fullmatch(r"[0-9a-f]{40}", TARGET_SHA) and re.fullmatch(r"[0-9a-f]{40}", TARGET_TREE)

OLD_MAIN = "30c0e9f717efaad9bd46d47721a61495f4093e96"
OLD_TARGET = "5961922b9a309055a75bc7302e5c852c5c51d59c"
OLD_TREE = "85d71a7f6734d781df3ea0f287ae8569a1b801e4"
NEW_MAIN = "8b036dce5c410191c99b6334b288cccd104a0b34"
OLD_SUBJECT = "release: add the production startup budget, the fence pull secret, and the landing API smoke to main"
NEW_SUBJECT = "fix(release): bind service applied revision to the app base"
BS = chr(92)
TAB = BS + "t"
CONT = " " + BS
NL = BS + "n"
NEW_ROWS = (
    ("M", "scripts/release/build_production_canary.py"),
    ("M", "scripts/release/promote_service_digests.py"),
    ("M", "scripts/release/verify_promotion_chain.py"),
    ("M", "scripts/release/verify_promotion_evidence.py"),
    ("M", "scripts/release/wait_release_rollouts.py"),
    ("M", "tests/release/test_kubernetes_release_runtime.py"),
    ("M", "tests/release/test_production_canary.py"),
    ("M", "tests/release/test_promotion_chain.py"),
    ("M", "tests/release/test_promotion_evidence.py"),
    ("M", "tests/release/test_service_promotion.py"),
)
STALE = (OLD_MAIN, OLD_TARGET, OLD_TREE, OLD_SUBJECT, "pipeline", "Pipeline", "20260921", "startup budget",
         "writer-fence-rbac", "cloudflare_pages", "test_production_startup_budget")


class Doc:
    def __init__(self, path: Path):
        self.text = io.open(path, encoding="utf-8", newline="").read()
        assert "\r" not in self.text, path

    def replace(self, old: str, new: str, count: int = 1) -> None:
        assert self.text.count(old) == count, (old[:70], self.text.count(old), count)
        self.text = self.text.replace(old, new)

    def replace_span(self, start: str, end: str, new: str) -> None:
        assert self.text.count(start) == 1 and self.text.count(end) == 1, (start[:40], end[:40])
        begin, finish = self.text.index(start), self.text.index(end)
        assert begin < finish
        self.text = self.text[:begin] + new + self.text[finish:]

    def write(self, path: Path, *, stale: tuple[str, ...] = STALE) -> None:
        for fragment in stale:
            assert fragment not in self.text, (path.name, fragment[:40])
        io.open(path, "w", encoding="utf-8", newline="\n").write(self.text)
        print("rendered", path.name, len(self.text.splitlines()), "lines")


def common(doc: Doc, *, sha_lines: bool) -> None:
    doc.text = doc.text.replace("pipeline defects main publisher", "service applied revision main publisher")
    doc.text = doc.text.replace("pipeline defect fixes", "service applied revision fix")
    doc.text = doc.text.replace("pipeline-defects", "service-applied-revision")
    doc.text = doc.text.replace("pipeline_defects", "service_applied_revision")
    doc.text = doc.text.replace("PipelineDefects", "ServiceAppliedRevision")
    doc.text = doc.text.replace("20260921", "20260924")
    if sha_lines:
        doc.text = doc.text.replace(OLD_MAIN, NEW_MAIN)
        doc.text = doc.text.replace(OLD_TARGET, TARGET_SHA)
        doc.text = doc.text.replace(OLD_TREE, TARGET_TREE)


# ---- helper workflow ---------------------------------------------------------------------------------------
helper = Doc(D / "prec-0921-live" / "helper.yml")
common(helper, sha_lines=True)
helper.replace(f"            '{OLD_SUBJECT}'\n", f"            '{NEW_SUBJECT}'\n")
rows = "".join(
    f"            $'{status}{TAB}{path}'" + (CONT if index < len(NEW_ROWS) - 1 else ')"') + "\n"
    for index, (status, path) in enumerate(NEW_ROWS)
)
helper.replace_span(
    "            $'M" + TAB + "apps/devpath-ai-svc/base/deployment.yaml'" + CONT + "\n",
    '          test -n "$expected_listing"\n',
    rows,
)
helper.replace('          test "${#target_rows[@]}" -eq 12\n', f'          test "${{#target_rows[@]}}" -eq {len(NEW_ROWS)}\n')
helper.write(OUT / "helper.yml")

# ---- contract test -------------------------------------------------------------------------------------------
contract = Doc(D / "prec-0921-live" / "contract_test.py")
common(contract, sha_lines=True)
contract.replace_span(
    "TARGET_ROWS = (\n",
    "SUBJECT = (\n",
    "TARGET_ROWS = (\n" + "".join(f'    ("{s}", "{p}"),\n' for s, p in NEW_ROWS) + ")\n",
)
contract.replace(
    'SUBJECT = (\n    "release: add the production startup budget, the fence pull secret, "\n    "and the landing API smoke to main"\n)\n',
    f'SUBJECT = "{NEW_SUBJECT}"\n',
)
contract.replace(
    "        'test \"$(git show -s --format=%s HEAD)\" = " + BS + "'" + OLD_SUBJECT + BS + "'',\n",
    "        'test \"$(git show -s --format=%s HEAD)\" = " + BS + "'" + NEW_SUBJECT + BS + "'',\n",
)
old_listing_line = [line for line in contract.text.splitlines() if line.startswith("        'expected_listing=")]
assert len(old_listing_line) == 1, old_listing_line
# inside the python single-quoted literal: printf '%s\n' becomes printf \'%s\\n\' and $'M\tpath' becomes $\'M\\tpath\'
new_listing = (
    "        'expected_listing=\"$(printf " + BS + "'%s" + BS + BS + "n" + BS + "' "
    + " ".join("$" + BS + "'" + s + BS + BS + "t" + p + BS + "'" for s, p in NEW_ROWS)
    + ")\"',"
)
contract.replace(old_listing_line[0], new_listing)
contract.replace("        'test \"${#target_rows[@]}\" -eq 12',\n", f"        'test \"${{#target_rows[@]}}\" -eq {len(NEW_ROWS)}',\n", 2)
contract.replace("        self.assertEqual(12, len(TARGET_ROWS))\n", f"        self.assertEqual({len(NEW_ROWS)}, len(TARGET_ROWS))\n")
# the publisher must never RUN the chain or migration verifiers; the target listing merely NAMES verify_promotion_chain.py
contract.replace(
    "    def test_the_promotion_chain_is_deliberately_absent(self) -> None:\n"
    "        # This commit sits outside every release chain; the chain verifiers would refuse its unregistered subject.\n"
    "        for forbidden in (\n",
    "    def test_the_promotion_chain_is_deliberately_absent(self) -> None:\n"
    "        # The publisher never runs the chain or migration verifiers. The target itself edits\n"
    "        # verify_promotion_chain.py, so that path may appear only in the expected target listing rows.\n"
    "        guarded = \"" + NL + "\".join(\n"
    "            line for line in self.text.splitlines()\n"
    "            if not line.lstrip().startswith(\"$'M" + BS + BS + "t\")\n"
    "            and not line.lstrip().startswith(\"$'A" + BS + BS + "t\")\n"
    "        )\n"
    "        self.assertNotIn(\"verify_promotion_chain.py --\", self.text)\n"
    "        for forbidden in (\n",
)
contract.replace(
    '            "RELEASE_ID",\n        ):\n            self.assertNotIn(forbidden, self.text)\n',
    '            "RELEASE_ID",\n        ):\n            self.assertNotIn(forbidden, guarded)\n',
)
compile(contract.text, "contract", "exec")
contract.write(OUT / "test_service_applied_revision_main_publish.py")

# ---- staged dispatcher -----------------------------------------------------------------------------------------
dispatcher = Doc(D / "prec-0921-live" / "dispatcher.yml")
common(dispatcher, sha_lines=False)
dispatcher.write(OUT / "dispatcher.yml")

# ---- operator transaction + its unit test ----------------------------------------------------------------------
runner = Doc(D / "prec-0921" / "run_pipeline_defects_main_publish.py")
common(runner, sha_lines=True)
compile(runner.text, "run", "exec")
runner.write(OUT / "run_service_applied_revision_main_publish.py")
unit = Doc(D / "prec-0921" / "test_run_pipeline_defects_main_publish.py")
common(unit, sha_lines=True)
compile(unit.text, "unit", "exec")
unit.write(OUT / "test_run_service_applied_revision_main_publish.py")
print("TARGET_SHA", TARGET_SHA, "TARGET_TREE", TARGET_TREE)
