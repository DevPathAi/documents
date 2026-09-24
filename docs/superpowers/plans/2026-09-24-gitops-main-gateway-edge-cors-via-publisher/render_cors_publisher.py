#!/usr/bin/env python3
"""Render the gateway-edge-CORS publisher artifacts from the executed 2026-09-21 pipeline-defects publisher by exact,
counted substitution: helper workflow, contract test, staged dispatcher, operator transaction and its unit test.

Usage: render_cors_publisher.py <publisher dir holding prec-0921-live/ and prec-0921/> <out dir holding target.txt>
Writes <out dir>/rendered/{helper.yml,test_gateway_edge_cors_main_publish.py,dispatcher.yml,
       run_gateway_edge_cors_main_publish.py,test_run_gateway_edge_cors_main_publish.py}.
Derived from render_r3fix_publisher.py (2026-09-24) without its contract-guard relaxation: this target does not touch
any release verifier, so the original "the promotion chain is deliberately absent" guard applies unchanged.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

D = Path(sys.argv[1])
O = Path(sys.argv[2])
OUT = O / "rendered"
OUT.mkdir(parents=True, exist_ok=True)
target = dict(line.split("=", 1) for line in (O / "target.txt").read_text(encoding="utf-8").split())
TARGET_SHA, TARGET_TREE = target["TARGET_SHA"], target["TARGET_TREE"]
assert re.fullmatch(r"[0-9a-f]{40}", TARGET_SHA) and re.fullmatch(r"[0-9a-f]{40}", TARGET_TREE)

OLD_MAIN = "30c0e9f717efaad9bd46d47721a61495f4093e96"
OLD_TARGET = "5961922b9a309055a75bc7302e5c852c5c51d59c"
OLD_TREE = "85d71a7f6734d781df3ea0f287ae8569a1b801e4"
NEW_MAIN = "eae5c42ef33b1a633a632766410e63d655b409fb"
OLD_SUBJECT = "release: add the production startup budget, the fence pull secret, and the landing API smoke to main"
NEW_SUBJECT = "release: restore the gateway edge CORS dedupe in the production default-filters"
BS = chr(92)
TAB = BS + "t"
CONT = " " + BS
NEW_ROWS = (
    ("M", "apps/devpath-gateway/base/deployment.yaml"),
    ("A", "tests/release/test_gateway_edge_cors.py"),
)
STALE = (OLD_MAIN, OLD_TARGET, OLD_TREE, OLD_SUBJECT, "pipeline", "Pipeline", "20260921", "startup budget",
         "writer-fence-rbac", "cloudflare_pages", "test_production_startup_budget", "service applied revision",
         "service-applied-revision", "service_applied_revision")


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
    doc.text = doc.text.replace("pipeline defects main publisher", "gateway edge CORS main publisher")
    doc.text = doc.text.replace("pipeline defect fixes", "gateway edge CORS fix")
    doc.text = doc.text.replace("pipeline-defects", "gateway-edge-cors")
    doc.text = doc.text.replace("pipeline_defects", "gateway_edge_cors")
    doc.text = doc.text.replace("PipelineDefects", "GatewayEdgeCors")
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
# inside the python single-quoted literal: printf '%s\n' becomes printf \'%s\n\' and $'M\tpath' becomes $\'M\tpath\'
new_listing = (
    "        'expected_listing=\"$(printf " + BS + "'%s" + BS + BS + "n" + BS + "' "
    + " ".join("$" + BS + "'" + s + BS + BS + "t" + p + BS + "'" for s, p in NEW_ROWS)
    + ")\"',"
)
contract.replace(old_listing_line[0], new_listing)
contract.replace("        'test \"${#target_rows[@]}\" -eq 12',\n", f"        'test \"${{#target_rows[@]}}\" -eq {len(NEW_ROWS)}',\n", 2)
contract.replace("        self.assertEqual(12, len(TARGET_ROWS))\n", f"        self.assertEqual({len(NEW_ROWS)}, len(TARGET_ROWS))\n")
compile(contract.text, "contract", "exec")
contract.write(OUT / "test_gateway_edge_cors_main_publish.py")

# ---- staged dispatcher -----------------------------------------------------------------------------------------
dispatcher = Doc(D / "prec-0921-live" / "dispatcher.yml")
common(dispatcher, sha_lines=False)
dispatcher.write(OUT / "dispatcher.yml")

# ---- operator transaction + its unit test ----------------------------------------------------------------------
runner = Doc(D / "prec-0921" / "run_pipeline_defects_main_publish.py")
common(runner, sha_lines=True)
compile(runner.text, "run", "exec")
runner.write(OUT / "run_gateway_edge_cors_main_publish.py")
unit = Doc(D / "prec-0921" / "test_run_pipeline_defects_main_publish.py")
common(unit, sha_lines=True)
compile(unit.text, "unit", "exec")
unit.write(OUT / "test_run_gateway_edge_cors_main_publish.py")
print("TARGET_SHA", TARGET_SHA, "TARGET_TREE", TARGET_TREE)
