# -*- coding: utf-8 -*-
"""10/02 선례(285a83c)에서 ET13 baseline 승인 디스패처를 정확한 치환으로 파생한다.

치환 개수를 단언하고, 선례 리터럴이 하나도 남지 않았음을 확인한 뒤에만 파일을 쓴다.
(9/20 캠페인 build_dispatchers.py 의 방식)
"""
import io
import pathlib
import sys

PRECEDENT = pathlib.Path(
    r"D:/workspace/dpa/.release-artifacts/ms-20261003-ai-fallback-retry-budget/precedent-baseline-dispatch.yml"
)  # = frontend 285a83c(10/02 baseline 디스패처) 의 워크플로 파일

OLD_BRANCH = "automation/dispatch-ms-20261002-ai-provider-fallback-gpu7b"
NEW_BRANCH = "automation/dispatch-ms-20261003-ai-fallback-retry-budget"
OLD_ID = "ms-20261002-ai-provider-fallback-gpu7b"
NEW_ID = "ms-20261003-ai-fallback-retry-budget"

# (old, new, 예상 치환 개수)
PAIRS = [
    (f"      - {OLD_BRANCH}", f"      - {NEW_BRANCH}", 1),
    (f'"release_id": "{OLD_ID}"', f'"release_id": "{NEW_ID}"', 1),
    ('"raw_run_id": "36918293674"', '"raw_run_id": "37112627137"', 1),
    ('"raw_artifact_id": "11191407144"', '"raw_artifact_id": "11270965962"', 1),
    (
        '"raw_artifact_digest": "sha256:09b692cce43e1649eaaae07286d6119b420dd5656a20e012d9e0e8a2b3a99355"',
        '"raw_artifact_digest": "sha256:cd8e266d23c153bc5cd8f29ad8bbbaf5b808351900a8270802c4b71424e12ab9"',
        1,
    ),
]

# 치환하지 않지만 이번 릴리스에도 유효해야 하는 값 — 존재를 단언한다.
# et13-evidence.yml 바이트가 10/02(=r3) 와 동일함을 로컬 sha256 으로 확인했다(b69e9990).
MUST_KEEP = (
    '"raw_run_attempt": "1"',
    '"raw_workflow_sha256": "71ba5845635677793d97d1b30d01a7ad58fed2e8ca2e2e9cc1a437f89b7d323e"',
    '"ref": "main"',
    "et13-baseline-approval.yml/dispatches",
)

# 치환 후 하나도 남아 있으면 안 되는 선례 리터럴
FORBIDDEN = (
    OLD_ID, OLD_BRANCH, "36918293674", "11191407144",
    "09b692cce43e1649eaaae07286d6119b420dd5656a20e012d9e0e8a2b3a99355",
    "ms-20261002", "gpu7b",
)


def main() -> int:
    text = io.open(PRECEDENT, encoding="utf-8").read().replace("\r", "")
    for old, new, count in PAIRS:
        found = text.count(old)
        assert found == count, f"치환 대상 개수 불일치: {old!r} found={found} expected={count}"
        text = text.replace(old, new)

    for keep in MUST_KEEP:
        assert keep in text, f"유지해야 할 값이 없다: {keep!r}"

    leftovers = [lit for lit in FORBIDDEN if lit in text]
    assert not leftovers, f"선례 리터럴이 남았다: {leftovers}"

    for need in (NEW_ID, NEW_BRANCH, "37112627137", "11270965962",
                 "cd8e266d23c153bc5cd8f29ad8bbbaf5b808351900a8270802c4b71424e12ab9"):
        assert need in text, f"이번 릴리스 값이 없다: {need!r}"

    target = pathlib.Path(sys.argv[1])
    target.parent.mkdir(parents=True, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="\n").write(text)
    print(f"작성: {target}")
    print(f"  치환 {len(PAIRS)}건 · 유지 단언 {len(MUST_KEEP)}건 · 금지 리터럴 0건 확인")
    return 0


if __name__ == "__main__":
    sys.exit(main())
