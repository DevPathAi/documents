# -*- coding: utf-8 -*-
"""승인된 10/02 baseline PNG 와 이번 릴리스의 raw review PNG 를 픽셀 비교한다.

산출물 = baseline-diff.json (케이스별 diff·치수 변화·추가/삭제) + 표준출력 요약.
3단계(ET13 기준선 승인)는 사람 관문이고, 사용자는 이 결과와 Artifact 비교 페이지를 보고 결정한다.
"""
import json
import pathlib
import sys
from collections import defaultdict

from PIL import Image, ImageChops

ROOT = pathlib.Path(r"D:/workspace/dpa/.release-artifacts/ms-20261003-ai-fallback-retry-budget")
# 10/02 승인 baseline(run 36922449776, artifact 11193625116) — fe-main-1002 에 풀어 둔 것
BASE = pathlib.Path(r"D:/workspace/dpa/.worktrees/fe-main-1002/build/et13/external/baseline/visual")
HEAD = ROOT / "evidence" / "raw-review" / "capture" / "visual"


def rel_set(root: pathlib.Path) -> dict[str, pathlib.Path]:
    return {str(p.relative_to(root)).replace("\\", "/"): p for p in root.rglob("*.png")}


def parse_case(rel: str) -> tuple[str, str, str, str]:
    """'admin/admin-kpi-dashboard--visual--w1240--dark.png' -> surface, fixture, width, theme"""
    surface, name = rel.split("/", 1)
    stem = name[:-4] if name.endswith(".png") else name
    parts = stem.split("--")
    fixture = parts[0]
    width = next((p for p in parts if p.startswith("w") and p[1:].isdigit()), "?")
    theme = parts[-1]
    return surface, fixture, width, theme


def diff_percent(a: pathlib.Path, b: pathlib.Path) -> tuple[float, bool, tuple, tuple]:
    """다른 픽셀 비율(%), 치수 변화 여부, 두 치수."""
    ia = Image.open(a).convert("RGBA")
    ib = Image.open(b).convert("RGBA")
    if ia.size != ib.size:
        return 100.0, True, ia.size, ib.size
    delta = ImageChops.difference(ia, ib)
    # 알파까지 합쳐 채널 최대값으로 픽셀 단위 변화 판정
    bands = delta.split()
    changed = 0
    total = ia.size[0] * ia.size[1]
    # 채널별 getdata 를 한 번에 돌며 픽셀 단위 OR
    data = list(zip(*(band.getdata() for band in bands)))
    for px in data:
        if any(px):
            changed += 1
    return (changed / total) * 100.0, False, ia.size, ib.size


def main() -> int:
    if not BASE.exists() or not HEAD.exists():
        print(f"경로 없음: {BASE if not BASE.exists() else HEAD}")
        return 2
    base = rel_set(BASE)
    head = rel_set(HEAD)

    added = sorted(set(head) - set(base))
    removed = sorted(set(base) - set(head))
    common = sorted(set(base) & set(head))

    cases = []
    for rel in common:
        pct, resized, sa, sb = diff_percent(base[rel], head[rel])
        surface, fixture, width, theme = parse_case(rel)
        cases.append({
            "case": rel, "surface": surface, "fixture": fixture,
            "width": width, "theme": theme,
            "diff_percent": round(pct, 4),
            "changed": pct > 0.0,
            "resized": resized,
            "baseline_size": list(sa), "candidate_size": list(sb),
        })

    by_fixture = defaultdict(list)
    for c in cases:
        by_fixture[f"{c['surface']}/{c['fixture']}"].append(c["diff_percent"])

    summary = []
    for key, vals in by_fixture.items():
        nz = [v for v in vals if v > 0]
        summary.append({
            "fixture": key, "cases": len(vals), "changed_cases": len(nz),
            "min": round(min(vals), 4), "avg": round(sum(vals) / len(vals), 4),
            "max": round(max(vals), 4),
        })
    summary.sort(key=lambda s: -s["avg"])

    out = {
        "release_id": "ms-20261002-ai-provider-fallback-gpu7b",
        "baseline": {
            "run_id": 36704221183,
            "artifact_id": 11090504413,
            "release_id": "ms-20260930-s3-web-redesign-r3",
            "source_sha": "9c7efee38a83e250848ee023da46e6fe1fafe438",
        },
        "candidate": {
            "run_id": 36918293674,
            "artifact_id": 11191407144,
            "source_sha": "a08feb6f0e28fdb3da45e601dc06ebb15e91e9f2",
        },
        "totals": {
            "cases": len(cases),
            "changed": sum(1 for c in cases if c["changed"]),
            "unchanged": sum(1 for c in cases if not c["changed"]),
            "resized": sum(1 for c in cases if c["resized"]),
            "added": added, "removed": removed,
        },
        "by_fixture": summary,
        "cases": cases,
    }
    (ROOT / "baseline-diff.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    t = out["totals"]
    print(f"케이스 {t['cases']}  변경 {t['changed']}  무변경 {t['unchanged']}  "
          f"치수변화 {t['resized']}  추가 {len(added)}  삭제 {len(removed)}")
    print()
    print(f"{'fixture':52s} {'cases':>5s} {'chg':>4s} {'min%':>8s} {'avg%':>8s} {'max%':>8s}")
    for s in summary:
        print(f"{s['fixture']:52s} {s['cases']:5d} {s['changed_cases']:4d} "
              f"{s['min']:8.3f} {s['avg']:8.3f} {s['max']:8.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
