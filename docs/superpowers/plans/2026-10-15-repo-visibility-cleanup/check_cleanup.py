#!/usr/bin/env python3
"""공개 저장소 정리(스펙 2026-10-15-repo-visibility-cleanup-design.md §6) 완료 조건 검사기.

documents 트리를 읽기만 한다. 멘토 실명은 이 파일에 쓰지 않고 3음절 sha256 으로만 찾는다.

사용: py -I -X utf8 check_cleanup.py --repo <documents 경로> --base <기준 커밋 SHA>
종료 코드: 모든 검사 통과 0, 하나라도 실패 1.
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys
import unicodedata
import urllib.parse

MOVED = (
    "28_장기_전략.md",
    "29_예비창업패키지_사업계획서.md",
    "30_발표_QA_스크립트.md",
    "31_통계_출처_검증.md",
    "32_영상_대본.md",
    "35_모두의_창업_프로그램_참고.md",
    "pitch-deck.html",
)
GUIDES = (
    "09_Git_규칙_정의서.md",
    "10_환경_설정_템플릿.md",
    "11_테스트_전략서.md",
    "12_코드_리뷰_규칙.md",
    "14_배포_가이드.md",
    "16_운영_메뉴얼.md",
)
NAME_SHA256 = {"937b630c27b8c625f9c22076696abab152567d9a12ecb87247896379002a2715"}
FORBIDDEN = ("최초의 개발자 교육", "유일한 한국")
BANNER = "> 현행 가격: 정식 전환 시 월 9,900원 예정(2026-10 기준). 본문의 월 14,900원은 작성 당시 가설입니다."
BANNER_FILES = ("17_스케줄.md", "27_MVP_설계서.md")
TAGLINE = "사수 없는 0~3년차 개발자의 첫 AI 사수"
TAGLINE_FILES = ("README.md", "Home.md")
BOX_FILE = "06_화면_기능_정의서.md"
BOX_REF_LINE, BOX_LINE = 60, 61  # 1부터 센다. 60행은 같은 상자의 바로 윗줄
UNCHANGED = GUIDES + (".github", "tools")

_SKIP_TARGET = re.compile(r"^(https?:|mailto:|#|/)", re.I)
_WIKI = re.compile(r"\[\[([^\]]+)\]\]")
_HANGUL_RUN = re.compile(r"[가-힣]{3,}")


def md_links(text):
    """[label](target) 의 target 과 [[이름]] 위키 링크를 (행 번호, 대상, 종류) 로 낸다.

    target 안의 괄호는 짝을 맞춰 읽는다(예: `./a-(v5.0).md`). 이미지 `![..](..)` 는 건너뛴다.
    """
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        i = line.find("](")
        while i != -1:
            depth, j = 0, i - 1
            while j >= 0:
                if line[j] == "]":
                    depth += 1
                elif line[j] == "[":
                    if depth == 0:
                        break
                    depth -= 1
                j -= 1
            is_image = j > 0 and line[j - 1] == "!"
            k, depth, buf = i + 2, 1, []
            while k < len(line):
                c = line[k]
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                    if depth == 0:
                        break
                buf.append(c)
                k += 1
            target = "".join(buf).strip().split()[0] if "".join(buf).strip() else ""
            if j >= 0 and not is_image and target:
                out.append((lineno, target, "md"))
            i = line.find("](", k)
        for m in _WIKI.finditer(line):
            name = m.group(1).split("|")[0].split("#")[0].strip()
            if name:
                out.append((lineno, name, "wiki"))
    return out


def link_resolves(exists, target, kind):
    """exists(상대경로) -> bool 로 링크 대상이 있는지 본다. 외부·앵커·절대 링크는 검사하지 않는다."""
    if kind == "wiki":
        return exists(target + ".md") or exists(target)
    if _SKIP_TARGET.match(target):
        return True
    path = urllib.parse.unquote(target.split("#")[0].split("?")[0])
    if not path:
        return True
    return exists(path)


def _norm(rel):
    return os.path.normpath(rel).replace("\\", "/")


def broken_links(read, exists, files):
    """(파일, 대상, 종류) 집합 — 행 번호는 비교에서 뺀다(편집으로 행이 밀린다)."""
    out = set()
    for f in files:
        for _, target, kind in md_links(read(f)):
            if not link_resolves(exists, target, kind):
                out.add((f, target, kind))
    return out


def links_to_moved(read, files):
    out = []
    for f in files:
        for lineno, target, kind in md_links(read(f)):
            name = target + ".md" if kind == "wiki" else os.path.basename(urllib.parse.unquote(target.split("#")[0]))
            if name in MOVED:
                out.append(f"{f}:{lineno}->{target}")
    return out


def hashed_name_hits(text, sha_set):
    """3음절 창의 sha256 이 sha_set 에 있는 횟수."""
    hits = 0
    for m in _HANGUL_RUN.finditer(text):
        run = m.group(0)
        for s in range(len(run) - 2):
            if hashlib.sha256(run[s:s + 3].encode("utf-8")).hexdigest() in sha_set:
                hits += 1
    return hits


def display_width(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def _read(repo, rel):
    with open(os.path.join(repo, rel), encoding="utf-8") as f:
        return f.read()


def _tracked_files(repo):
    raw = subprocess.run(["git", "-C", repo, "ls-files", "-z"], capture_output=True, check=True).stdout
    return [p.decode("utf-8") for p in raw.split(b"\0") if p]


def run_checks(repo, base):
    results = []

    def record(cid, ok, title, detail=""):
        results.append((cid, ok, title, detail))

    present = [m for m in MOVED if os.path.exists(os.path.join(repo, m))]
    record("C1", not present, "이동 대상 7개 없음", ", ".join(present))

    name_files = []
    for rel in _tracked_files(repo):
        p = os.path.join(repo, rel)
        if not os.path.isfile(p):
            continue
        data = open(p, "rb").read()
        if b"\0" in data:
            continue
        if hashed_name_hits(data.decode("utf-8", "replace"), NAME_SHA256):
            name_files.append(rel)
    record("C2", not name_files, "멘토 실명 0건(전체 트리)", f"{len(name_files)}개 파일")

    top_md = sorted(f for f in os.listdir(repo) if f.endswith(".md") and os.path.isfile(os.path.join(repo, f)))
    forbidden = [f"{f}:{phrase}" for f in top_md for phrase in FORBIDDEN if phrase in _read(repo, f)]
    record("C3", not forbidden, "최상위 md 에 「최초의 개발자 교육」·「유일한 한국」 없음", ", ".join(forbidden))

    no_banner = [f for f in BANNER_FILES if BANNER not in _read(repo, f)]
    record("C4", not no_banner, "17·27 현행 가격 머리말", ", ".join(no_banner))

    def read_now(rel):
        return _read(repo, rel)

    def exists_now(rel):
        return os.path.exists(os.path.join(repo, _norm(rel)))

    base_tree = subprocess.run(["git", "-C", repo, "ls-tree", "-r", "-t", "--name-only", "-z", base],
                               capture_output=True, check=True).stdout
    base_paths = {p.decode("utf-8") for p in base_tree.split(b"\0") if p}

    def read_base(rel):
        return subprocess.run(["git", "-C", repo, "show", f"{base}:{rel}"], capture_output=True,
                              check=True).stdout.decode("utf-8", "replace")

    def exists_base(rel):
        return _norm(rel) in base_paths

    base_top_md = sorted(p for p in base_paths if "/" not in p and p.endswith(".md"))
    new_broken = sorted(broken_links(read_now, exists_now, top_md) - broken_links(read_base, exists_base, base_top_md))
    record("C5", not new_broken, "기준 커밋 대비 새로 끊긴 상대 링크 0개(최상위 md)",
           "; ".join(f"{f}->{t}" for f, t, _ in new_broken))
    moved_links = links_to_moved(read_now, top_md)
    record("C9", not moved_links, "이동 대상 7개를 가리키는 링크 0개(최상위 md)", "; ".join(moved_links))

    changed = subprocess.run(["git", "-C", repo, "diff", "--name-only", base, "--", *UNCHANGED],
                             capture_output=True, check=True).stdout.decode("utf-8").split()
    record("C6", not changed, "6개 가이드·.github·tools 변경 없음", ", ".join(changed))

    no_tagline = [f for f in TAGLINE_FILES if TAGLINE not in _read(repo, f)]
    record("C7", not no_tagline, "README·Home 새 소개 문구", ", ".join(no_tagline))

    lines = _read(repo, BOX_FILE).splitlines()
    ref_w, box_w = display_width(lines[BOX_REF_LINE - 1]), display_width(lines[BOX_LINE - 1])
    record("C8", ref_w == box_w and "최초의" not in lines[BOX_LINE - 1],
           "06 상자 줄 폭 유지·「최초의」 없음", f"윗줄 폭 {ref_w}, 대상 줄 폭 {box_w}")
    return results


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--base", required=True)
    args = ap.parse_args(argv)
    results = run_checks(args.repo, args.base)
    for cid, ok, title, detail in results:
        print(f"{'PASS' if ok else 'FAIL'} {cid} {title}" + (f" — {detail}" if detail and not ok else ""))
    return 0 if all(ok for _, ok, _, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
