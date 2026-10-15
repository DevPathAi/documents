# -*- coding: utf-8 -*-
"""7단계 — 증거 디스패처 3종을 10/02 에 **성공한** 선례에서 정확한 치환으로 파생한다.

선례 = frontend `f8ecab4` · documents `db61841`(60dd134 의 수정 포함) · ai-svc `6fbe6f7`.
(documents `8e88e8e`·ai-svc `4ad4087` 은 이전 candidate 해시를 보낸 결함 버전이라 쓰지 않는다.)

각 치환은 개수를 단언하고, 선례 리터럴이 하나도 남지 않았음을 확인한 뒤에만 파일을 쓴다.
★10/02 와 달리 documents 의 approval_source_sha 도 바뀐다★(documents main 7f732ac5 → f52b4a9a, #208).

Usage: render_evidence_dispatchers.py <frontend wt> <documents wt> <ai-svc wt>
"""
import io
import json
import pathlib
import re
import sys

ART = pathlib.Path("D:/workspace/dpa/.release-artifacts/ms-20261003-ai-fallback-retry-budget")
coords = json.loads((ART / "coords.json").read_text(encoding="utf-8"))

NEW_ID = coords["release_id"]
OLD_ID = "ms-20261002-ai-provider-fallback-gpu7b"
OLD_BRANCH = f"automation/dispatch-{OLD_ID}"
NEW_BRANCH = f"automation/dispatch-{NEW_ID}"

C = coords["candidate"]
CAND_RUN = str(C["run_id"])
CAND_ARTIFACT = str(C["artifact_id"])
CAND_SPEC = C["spec_sha256"]
BASE = coords["et13_baseline"]
BASE_RUN = str(BASE["approval_run_id"])
BASE_ARTIFACT = str(BASE["approved_artifact_id"])

AI_SHA = coords["ai_svc"]["main"]
GITOPS_SHA = coords["gitops"]["base_sha"]
DOCS_APPROVAL_SHA = coords["documents"]["main"]

# 10/02 선례의 값 — 치환 전 존재를 단언하고 치환 후 잔존을 금지한다.
OLD_CAND_RUN = "36927122580"
OLD_CAND_ARTIFACT = "11194227794"
OLD_CAND_SPEC = "3423b8be5cde26420ed34f040447ce8db1ef516c7057ab76db7b57e5891a58a2"
OLD_BASE_RUN = "36922449776"
OLD_BASE_ARTIFACT = "11193625116"
OLD_AI_SHA = "83cfe792201b472aa97e0a2ce03aea79c23f483d"
OLD_GITOPS_SHA = "eb413814c9a813d84b8e1b2c7f5d69979b18bb02"
OLD_DOCS_APPROVAL_SHA = "7f732ac5ba31a91e81ea4e557cb7f67c8ee5ca36"

SPECS = {
    "frontend": {
        "precedent": "frontend-evidence.yml",
        "pairs": [
            (f"      - {OLD_BRANCH}", f"      - {NEW_BRANCH}", 1),
            (f'"release_id": "{OLD_ID}"', f'"release_id": "{NEW_ID}"', 2),
            (f'"candidate_run_id": "{OLD_CAND_RUN}"', f'"candidate_run_id": "{CAND_RUN}"', 2),
            (f'"candidate_artifact_id": "{OLD_CAND_ARTIFACT}"',
             f'"candidate_artifact_id": "{CAND_ARTIFACT}"', 2),
            (f'"candidate_spec_sha256": "{OLD_CAND_SPEC}"',
             f'"candidate_spec_sha256": "{CAND_SPEC}"', 2),
            (f'"baseline_run_id": "{OLD_BASE_RUN}"', f'"baseline_run_id": "{BASE_RUN}"', 1),
            (f'"baseline_artifact_id": "{OLD_BASE_ARTIFACT}"',
             f'"baseline_artifact_id": "{BASE_ARTIFACT}"', 1),
        ],
        "keep": ('"candidate_run_attempt": "1"', '"baseline_run_attempt": "1"', '"ref": "main"',
                 "et13-evidence.yml/dispatches", "mission-spine-manual-at-evidence.yml/dispatches"),
        "forbid": (OLD_ID, OLD_BRANCH, OLD_CAND_RUN, OLD_CAND_ARTIFACT, OLD_CAND_SPEC,
                   OLD_BASE_RUN, OLD_BASE_ARTIFACT, "ms-20261002", "gpu7b"),
    },
    "documents": {
        "precedent": "documents-privacy.yml",
        "pairs": [
            (f"      - {OLD_BRANCH}", f"      - {NEW_BRANCH}", 1),
            (f'"release_id": "{OLD_ID}"', f'"release_id": "{NEW_ID}"', 1),
            (f'"candidate_spec_sha256": "{OLD_CAND_SPEC}"',
             f'"candidate_spec_sha256": "{CAND_SPEC}"', 1),
            (f'"approval_source_sha": "{OLD_DOCS_APPROVAL_SHA}"',
             f'"approval_source_sha": "{DOCS_APPROVAL_SHA}"', 1),
        ],
        "keep": ('"ref": "main"', "mission-spine-privacy-approval.yml/dispatches"),
        "forbid": (OLD_ID, OLD_BRANCH, OLD_CAND_SPEC, OLD_DOCS_APPROVAL_SHA, "ms-20261002", "gpu7b"),
    },
    "ai-svc": {
        "precedent": "ai-svc-eval.yml",
        "pairs": [
            (f"      - {OLD_BRANCH}", f"      - {NEW_BRANCH}", 1),
            (f'"release_id": "{OLD_ID}"', f'"release_id": "{NEW_ID}"', 1),
            (f'"candidate_spec_sha256": "{OLD_CAND_SPEC}"',
             f'"candidate_spec_sha256": "{CAND_SPEC}"', 1),
            (f'"ai_source_sha": "{OLD_AI_SHA}"', f'"ai_source_sha": "{AI_SHA}"', 1),
            (f'"gitops_source_sha": "{OLD_GITOPS_SHA}"', f'"gitops_source_sha": "{GITOPS_SHA}"', 1),
        ],
        "keep": ('"ref": "main"', "mission-spine-release-eval.yml/dispatches"),
        "forbid": (OLD_ID, OLD_BRANCH, OLD_CAND_SPEC, OLD_AI_SHA, OLD_GITOPS_SHA,
                   "ms-20261002", "gpu7b"),
    },
}

# ★구조적 안전장치★ — 렌더 결과의 inputs 블록을 파싱해 **모든 값이 이번 릴리스의 허용 집합에 있는지** 단언한다.
# (2026-10-02 에 이것이 없어서 documents·ai-svc 가 이전 candidate_spec_sha256 을 보냈다.)
ALLOWED_INPUT_VALUES = {
    NEW_ID, CAND_RUN, CAND_ARTIFACT, CAND_SPEC, BASE_RUN, BASE_ARTIFACT,
    AI_SHA, GITOPS_SHA, DOCS_APPROVAL_SHA, "1", "main",
}


def assert_inputs_are_current(name: str, text: str) -> int:
    bad = []
    count = 0
    for key, value in re.findall(r'"([a-z0-9_]+)":\s*"([^"]+)"', text):
        count += 1
        if value not in ALLOWED_INPUT_VALUES:
            bad.append(f"{key}={value}")
    assert not bad, (name, "stale/unknown input values", bad)
    return count


TARGETS = dict(zip(("frontend", "documents", "ai-svc"), sys.argv[1:4]))
assert len(TARGETS) == 3, "세 워크트리 경로가 필요하다"

for name, spec in SPECS.items():
    text = io.open(ART / "precedents" / spec["precedent"], encoding="utf-8").read().replace("\r", "")
    for old, new, count in spec["pairs"]:
        found = text.count(old)
        assert found == count, (name, old[:60], f"found={found} expected={count}")
        text = text.replace(old, new)
    for keep in spec["keep"]:
        assert keep in text, (name, "missing keep", keep[:60])
    leftovers = [lit for lit in spec["forbid"] if lit in text]
    assert not leftovers, (name, "stale literals", leftovers)
    assert NEW_ID in text and NEW_BRANCH in text, (name, "new values absent")
    checked = assert_inputs_are_current(name, text)

    target = pathlib.Path(TARGETS[name]) / ".github/workflows/mission-spine-release-gate-dispatch.yml"
    target.parent.mkdir(parents=True, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="\n").write(text)
    print(f"{name:10s} 작성 · 치환 {len(spec['pairs'])}건 · 유지 {len(spec['keep'])}건 · "
          f"잔존 0건 · 값 전수검증 {checked}개 통과")

print()
print("candidate:", CAND_RUN, "/", CAND_ARTIFACT, "/", CAND_SPEC[:16] + "...")
print("baseline :", BASE_RUN, "/", BASE_ARTIFACT)
print("ai_source_sha:", AI_SHA[:12], "· gitops_source_sha:", GITOPS_SHA[:12], "· approval_source_sha:", DOCS_APPROVAL_SHA[:12])
