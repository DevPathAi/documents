#!/usr/bin/env python3
"""비공개 저장소 사본의 출처 표 만들기 · 원본과 바이트 비교(계획 Task 1).

비교는 작업 트리 파일이 아니라 **커밋된 blob** 끼리 한다(줄바꿈 변환에 속지 않는다).

사용:
  py -I -X utf8 provenance.py table  --src <documents 경로> --sha <원본 커밋>
  py -I -X utf8 provenance.py verify --src <documents 경로> --sha <원본 커밋> --dst <사본 저장소 경로> [--ref HEAD]
"""
import argparse
import hashlib
import subprocess
import sys

MOVED = (
    "28_장기_전략.md",
    "29_예비창업패키지_사업계획서.md",
    "30_발표_QA_스크립트.md",
    "31_통계_출처_검증.md",
    "32_영상_대본.md",
    "35_모두의_창업_프로그램_참고.md",
    "pitch-deck.html",
)


def blob(repo, ref, path):
    return subprocess.run(["git", "-C", repo, "show", f"{ref}:{path}"], capture_output=True, check=True).stdout


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def table(src, sha):
    rows = ["| 파일 | sha256 |", "|---|---|"]
    rows += [f"| `{p}` | `{sha256(blob(src, sha, p))}` |" for p in MOVED]
    return "\n".join(rows)


def verify(src, sha, dst, ref):
    raw = subprocess.run(["git", "-C", dst, "ls-tree", "-r", "--name-only", "-z", ref],
                         capture_output=True, check=True).stdout
    names = {p.decode("utf-8") for p in raw.split(b"\0") if p}
    ok = True
    missing = [p for p in MOVED if p not in names]
    if missing:
        print(f"FAIL 사본에 없는 파일: {missing}")
        ok = False
    for p in MOVED:
        if p in missing:
            continue
        a, b = sha256(blob(src, sha, p)), sha256(blob(dst, ref, p))
        print(f"{'PASS' if a == b else 'FAIL'} {p} {a[:12]}" + ("" if a == b else f" != {b[:12]}"))
        ok = ok and a == b
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("table", "verify"))
    ap.add_argument("--src", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--dst")
    ap.add_argument("--ref", default="HEAD")
    args = ap.parse_args(argv)
    if args.cmd == "table":
        print(table(args.src, args.sha))
        return 0
    return 0 if verify(args.src, args.sha, args.dst, args.ref) else 1


if __name__ == "__main__":
    sys.exit(main())
