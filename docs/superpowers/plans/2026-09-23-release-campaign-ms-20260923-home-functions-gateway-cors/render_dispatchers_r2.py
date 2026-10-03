"""Render the -r2 dispatcher workflows from the r3 precedents by exact, asserted substitution.

Usage: render_dispatchers_r2.py <coords-r2.json> <which: baseline|evidence|validate|promote|landing>
Writes to <out_dir>/dispatchers-r2/<name>.yml (LF). Every replaced literal is asserted to occur the expected number
of times, and no r3 literal may survive.
"""
import io
import json
import pathlib
import sys

coords = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
which = sys.argv[2]
PREC = pathlib.Path("D:/workspace/dpa/.release-artifacts/ms-20260920-community-flat-pages/r3/dispatchers")
OUT = pathlib.Path(coords["out_dir"]) / f"dispatchers-{coords['release_id'].rsplit('-', 1)[1]}"
OUT.mkdir(parents=True, exist_ok=True)
OLD_ID = "ms-20260920-community-flat-pages-r3"
OLD_SPEC = "b5ede99fa46a753202d9a4da1218c6fb9de1e7f0516063211648a4fd4c84cbcd"
OLD_GITOPS = "fcf97cf686df8e8bad56597d4679f9a96fd597fc"
NEW_ID = coords["release_id"]
NL = chr(10)


def render(precedent: str, pairs: list[tuple[str, str, int]], forbid: tuple[str, ...]) -> str:
    text = io.open(PREC / precedent, encoding="utf-8", newline="").read().replace(chr(13), "")
    for old, new, count in pairs:
        assert text.count(old) == count, (precedent, old[:40], text.count(old), count)
        text = text.replace(old, new)
    for literal in (OLD_ID, OLD_SPEC, OLD_GITOPS) + forbid:
        assert literal not in text, (precedent, literal[:40])
    return text


def write(name: str, text: str) -> None:
    path = OUT / name
    io.open(path, "w", encoding="utf-8", newline=NL).write(text)
    print(f"{name}: {len(text.splitlines())} lines")


if which == "baseline":
    raw = coords["raw_review"]
    write("frontend-baseline.yml", render("baseline-dispatch-r3.yml", [
        (OLD_ID, NEW_ID, 2),
        ('"raw_run_id": "35434688375"', f'"raw_run_id": "{raw["run_id"]}"', 1),
        ('"raw_artifact_id": "10581743618"', f'"raw_artifact_id": "{raw["artifact_id"]}"', 1),
        ('"raw_artifact_digest": "sha256:fa25b74322d9b1eabe3470f4197f410e5bf00498433ae17c553167091d7b1bdc"',
         f'"raw_artifact_digest": "{raw["artifact_digest"]}"', 1),
        ('"raw_workflow_sha256": "71ba5845635677793d97d1b30d01a7ad58fed2e8ca2e2e9cc1a437f89b7d323e"',
         f'"raw_workflow_sha256": "{raw["workflow_sha256"]}"', 1),
    ], ("35434688375", "10581743618")))
elif which == "evidence":
    cand, base = coords["candidate"], coords["baseline"]
    write("frontend-evidence.yml", render("r3-devpath-frontend.yml", [
        (OLD_ID, NEW_ID, 3),
        (OLD_SPEC, cand["spec_sha256"], 2),
        ('"candidate_run_id": "35573090295"', f'"candidate_run_id": "{cand["run_id"]}"', 2),
        ('"candidate_artifact_id": "10627021263"', f'"candidate_artifact_id": "{cand["artifact_id"]}"', 2),
        ('"baseline_run_id": "35572702300"', f'"baseline_run_id": "{base["run_id"]}"', 1),
        ('"baseline_artifact_id": "10627065495"', f'"baseline_artifact_id": "{base["artifact_id"]}"', 1),
    ], ("35573090295", "10627021263", "35572702300", "10627065495")))
    write("documents-privacy.yml", render("r3-documents.yml", [
        (OLD_ID, NEW_ID, 2),
        (OLD_SPEC, cand["spec_sha256"], 1),
        # approval_source_sha stays: documents main is still 7f732ac5ba31a91e81ea4e557cb7f67c8ee5ca36 (asserted by caller)
    ], ()))
    write("ai-svc-eval.yml", render("r3-devpath-ai-svc.yml", [
        (OLD_ID, NEW_ID, 2),
        (OLD_SPEC, cand["spec_sha256"], 1),
        (OLD_GITOPS, coords["gitops_base_sha"], 1),
        # ai_source_sha stays: ai-svc main is still 54f634b845befc7085e4b974a8b66120bf6c8856
    ], ()))
elif which == "migration":
    v = coords["validate"]
    write("shared-migration.yml", render("r3-devpath-shared.yml", [
        (OLD_ID, NEW_ID, 2),
        ("fe45981814cae3a95554f857c85319ad08cc22d3", v["sealed_sha"], 1),
        (OLD_GITOPS, coords["gitops_base_sha"], 1),
        ("6db1109cf9bd7e732b5805b1542d765e1a735f1f26d01a0b6326d5bb91f90d81", v["sealed_manifest_sha256"], 1),
        # source_sha stays: shared main is still 9793b8f92f92cca1ef57e28d2db6fb7d911741a3 (asserted by caller)
    ], ("fe45981814", "6db1109cf9")))
elif which in ("validate", "promote", "landing"):
    source = {"validate": "validate-dispatch-r3.yml", "promote": "r3-gitops-promote.yml", "landing": "r3-gitops-landing.yml"}[which]
    write(f"gitops-{which}.yml", render(source, [(OLD_ID, NEW_ID, 2)], ()))
else:
    raise SystemExit(f"unknown target {which}")
