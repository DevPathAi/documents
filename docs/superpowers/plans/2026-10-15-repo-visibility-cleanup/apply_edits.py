#!/usr/bin/env python3
"""공개 저장소 정리 — documents 편집 적용기(계획 Task 2 · Task 3).

각 원문은 대상 파일에 정확히 한 번 나와야 한다. 아니면 아무것도 쓰지 않고 멈춘다.
줄바꿈은 파일의 것을 그대로 둔다(newline="").

사용:
  py -I -X utf8 apply_edits.py --repo <documents 경로> --stage links   # 7개 git rm + 링크 16곳
  py -I -X utf8 apply_edits.py --repo <documents 경로> --stage words   # 문구 7곳 + 머리말 2곳 + 체크리스트 1곳
"""
import argparse
import os
import subprocess
import sys

MOVE = "(비공개 저장소로 이동, 2026-10)"
MOVED = (
    "28_장기_전략.md",
    "29_예비창업패키지_사업계획서.md",
    "30_발표_QA_스크립트.md",
    "31_통계_출처_검증.md",
    "32_영상_대본.md",
    "35_모두의_창업_프로그램_참고.md",
    "pitch-deck.html",
)
LINK_EDITS = (
    ("17_스케줄.md",
     " · 정렬 근거 [29_예비창업패키지_사업계획서](./29_예비창업패키지_사업계획서.md) · [35_모두의_창업_프로그램_참고](./35_모두의_창업_프로그램_참고.md).",
     f" · 정렬 근거 29_예비창업패키지_사업계획서 · 35_모두의_창업_프로그램_참고 {MOVE}."),
    ("17_스케줄.md",
     "- [29_예비창업패키지_사업계획서](./29_예비창업패키지_사업계획서.md) · [35_모두의_창업_프로그램_참고](./35_모두의_창업_프로그램_참고.md)",
     f"- 29_예비창업패키지_사업계획서 · 35_모두의_창업_프로그램_참고 {MOVE}"),
    ("45_Tier3_확장_기능_카탈로그.md",
     "B2B는 별도 수익 축([28_장기_전략](./28_장기_전략.md) 참조).",
     "B2B는 별도 수익 축(28_장기_전략 참조 — 비공개 저장소로 이동, 2026-10)."),
    ("45_Tier3_확장_기능_카탈로그.md",
     "- [28_장기_전략](./28_장기_전략.md) — 사업 확장 축(B2B·예창패 등)",
     f"- 28_장기_전략 — 사업 확장 축(B2B·예창패 등) {MOVE}"),
    ("Home.md", "| 28 | [[28_장기_전략]] — 장기 전략 (90일 통합) |", f"| 28 | 28_장기_전략 — 장기 전략 (90일 통합) {MOVE} |"),
    ("Home.md", "| 29 | [[29_예비창업패키지_사업계획서]] — 예비창업패키지 사업계획서 |",
     f"| 29 | 29_예비창업패키지_사업계획서 — 예비창업패키지 사업계획서 {MOVE} |"),
    ("Home.md", "| 30 | [[30_발표_QA_스크립트]] — 발표 평가 Q&A 스크립트 |", f"| 30 | 30_발표_QA_스크립트 — 발표 평가 Q&A 스크립트 {MOVE} |"),
    ("Home.md", "| 31 | [[31_통계_출처_검증]] — 통계 출처 검증 가이드 |", f"| 31 | 31_통계_출처_검증 — 통계 출처 검증 가이드 {MOVE} |"),
    ("Home.md", "| 32 | [[32_영상_대본]] — 첨부 영상 대본 |", f"| 32 | 32_영상_대본 — 첨부 영상 대본 {MOVE} |"),
    ("README.md", "| 28 | [장기 전략 (90일 통합)](./28_장기_전략.md) |", f"| 28 | 장기 전략 (90일 통합) {MOVE} |"),
    ("README.md", "| 29 | [예비창업패키지 사업계획서](./29_예비창업패키지_사업계획서.md) |", f"| 29 | 예비창업패키지 사업계획서 {MOVE} |"),
    ("README.md", "| 30 | [발표 평가 Q&A 스크립트](./30_발표_QA_스크립트.md) |", f"| 30 | 발표 평가 Q&A 스크립트 {MOVE} |"),
    ("README.md", "| 31 | [통계 출처 검증 가이드](./31_통계_출처_검증.md) |", f"| 31 | 통계 출처 검증 가이드 {MOVE} |"),
    ("README.md", "| 32 | [첨부 영상 대본](./32_영상_대본.md) |", f"| 32 | 첨부 영상 대본 {MOVE} |"),
    ("README.md", "| — | [피치덱 (HTML)](./pitch-deck.html) |", f"| — | 피치덱 (HTML) {MOVE} |"),
    ("README.md", "| 심사 / 투자자 대응 | 27 → 29 → 30 → 31 → pitch-deck |",
     "| 심사 / 투자자 대응 | 27 (29·30·31·피치덱은 비공개 저장소로 이동, 2026-10) |"),
)
BANNER = "> 현행 가격: 정식 전환 시 월 9,900원 예정(2026-10 기준). 본문의 월 14,900원은 작성 당시 가설입니다."
TAGLINE_OLD = '> **"내 수준에 맞는 다음 단계를 AI가 안내하는 최초의 개발자 교육"**'
TAGLINE_NEW = '> **"사수 없는 0~3년차 개발자의 첫 AI 사수"**'
BOX_OLD = '│  "Pod 간 거리를 걸어서 이해하는 최초의 개발자 교육"          │'
BOX_NEW = '│  "Pod 간 거리를 걸어서 이해하는 개발자 교육"' + " " * 17 + "│"  # 표시 폭 64 = 상자 위 테두리(2026-10-15 리뷰 수정 — 처음엔 18칸·폭 65 로 잘못 맞췄다)
CHECKLIST_ANCHOR = "   릴리스 후 **새 documents main SHA** 가 다음 candidate 의 `approval_source_sha` 가 된다.\n"
WORD_EDITS = (
    ("README.md", TAGLINE_OLD, TAGLINE_NEW),
    ("Home.md", TAGLINE_OLD, TAGLINE_NEW),
    ("01_프로젝트_계획서.md", '**"당신의 GitHub과 실력을 아는 유일한 한국 개발자 학습 플랫폼"**',
     '**"당신의 GitHub과 실력을 아는 한국 개발자 학습 플랫폼"**'),
    ("20_커뮤니티_기능_설계서.md", '"학습 맥락을 아는 유일한 한국 개발자 커뮤니티"', '"학습 맥락을 아는 한국 개발자 커뮤니티"'),
    ("21_유료_플랜_참고설계.md", "시니어가 답하는 유일한 한국 플랫폼.", "시니어가 답하는 한국 플랫폼."),
    ("06_화면_기능_정의서.md", BOX_OLD, BOX_NEW),
    ("22_AR_아키텍처_체험_참고설계.md", '- **"Pod 간 거리를 걸어서 이해하는 최초의 개발자 교육"** 슬로건',
     '- **"Pod 간 거리를 걸어서 이해하는 개발자 교육"** 슬로건'),
    ("17_스케줄.md", "# 17. 스케줄\n\n", f"# 17. 스케줄\n\n{BANNER}\n\n"),
    ("27_MVP_설계서.md", "# DevPath AI MVP 설계 및 1천만원 지원금 활용 계획\n\n",
     f"# DevPath AI MVP 설계 및 1천만원 지원금 활용 계획\n\n{BANNER}\n\n"),
    ("docs/superpowers/plans/2026-10-03-next-campaign-prep.md", CHECKLIST_ANCHOR,
     CHECKLIST_ANCHOR
     + "   이 릴리스에는 공개 저장소 정리(`specs/2026-10-15-repo-visibility-cleanup-design.md`)가 함께 들어간다 —\n"
     + "   머지 뒤 `plans/2026-10-15-repo-visibility-cleanup/check_cleanup.py` 를 main 트리에 다시 돌려 전부 PASS 인지 본다(계획 Task 5).\n"),
)


def _load(repo, rel):
    with open(os.path.join(repo, rel), encoding="utf-8", newline="") as f:
        return f.read()


def apply(repo, edits):
    """모든 원문이 정확히 한 번 나오는지 먼저 확인하고, 그다음에만 쓴다."""
    pending = {}
    for rel, old, new in edits:
        text = pending.get(rel, _load(repo, rel))
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"STOP {rel}: 원문이 {count}회 나온다 — {old[:70]}")
        pending[rel] = text.replace(old, new)
    for rel, text in pending.items():
        with open(os.path.join(repo, rel), "w", encoding="utf-8", newline="") as f:
            f.write(text)
    return sorted(pending)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--stage", required=True, choices=("links", "words"))
    args = ap.parse_args(argv)
    if args.stage == "links":
        missing = [m for m in MOVED if not os.path.exists(os.path.join(args.repo, m))]
        if missing:
            raise SystemExit(f"STOP 이동 대상이 이미 없다: {missing}")
        changed = apply(args.repo, LINK_EDITS)
        subprocess.run(["git", "-C", args.repo, "rm", "-q", "--", *MOVED], check=True)
    else:
        changed = apply(args.repo, WORD_EDITS)
    print(f"applied {args.stage}: {len(changed)} files edited")
    return 0


if __name__ == "__main__":
    sys.exit(main())
