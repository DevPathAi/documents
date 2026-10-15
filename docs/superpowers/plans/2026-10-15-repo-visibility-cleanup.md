# 공개 저장소 정리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** documents 의 제출 시점 사업 문서 7개를 신규 비공개 저장소로 원문 보존하고 documents 최신 트리에서 빼며, 남는 최상위 문서의 「최초」·「유일한」·구 가격 표현을 정리하고, 구 랜딩 저장소를 비공개 · 보관한다.

**Architecture:** documents · devpath-gitops 는 공개를 유지한다(Free 요금제에서 비공개 전환은 승인 체계를 깨뜨린다). 사본 저장소를 먼저 만들고 바이트 비교로 검증한 뒤에만 documents 에서 지운다. documents 변경은 develop 까지만 넣고, main 반영(공개 화면이 바뀌는 시점)은 다음 캠페인 candidate 생성 전이다.

**Tech Stack:** git · GitHub CLI(`gh`) · Python 3(표준 라이브러리만, `py -I -X utf8`) · Git Bash.

**Spec:** `docs/superpowers/specs/2026-10-15-repo-visibility-cleanup-design.md`

**도구(이 계획 디렉터리, 계획 작성 때 버리는 사본에서 검증함):**

| 파일 | 역할 |
|---|---|
| `2026-10-15-repo-visibility-cleanup/check_cleanup.py` | 스펙 §6 완료 조건 검사기(C1~C9). 멘토 실명은 sha256 으로만 가진다 |
| `2026-10-15-repo-visibility-cleanup/test_check_cleanup.py` | 검사기 단위 테스트 13개 |
| `2026-10-15-repo-visibility-cleanup/apply_edits.py` | documents 편집 적용기 — `--stage links` · `--stage words`. 원문이 정확히 한 번 나와야 쓴다 |
| `2026-10-15-repo-visibility-cleanup/provenance.py` | 사본 출처 표 생성(`table`) · 커밋된 blob 끼리 sha256 비교(`verify`) |

계획 작성 때 실측(origin/develop `f66dcf03`): 적용 전 검사기 = C1·C2·C3·C4·C7·C8·C9 FAIL, C5·C6 PASS · `links` 뒤 = 11 files changed, 16 insertions(+), 4653 deletions(-) · `words` 뒤 = 10 files changed, 13 insertions(+), 7 deletions(-) · 두 단계 뒤 검사기 9개 전부 PASS · 같은 단계 재실행은 `STOP … 원문이 0회` 로 멈춘다.

## Global Constraints

- 이력 재작성 · force-push 금지.
- Task 1~4 는 documents main · ai-svc main · 홈 master · gitops main 을 건드리지 않는다(현재 운영 릴리스 `ms-20261003` 의 롤백 창). documents main 은 Task 5 에서만 움직인다.
- 공개 범위를 바꾸는 저장소는 `devpath-landing-page` 하나다. `documents` · `devpath-gitops` 의 공개 범위는 그대로다.
- documents `.github/` · `tools/` · workflow-guide 게시 가이드 6개(`09_Git_규칙_정의서.md` · `10_환경_설정_템플릿.md` · `11_테스트_전략서.md` · `12_코드_리뷰_규칙.md` · `14_배포_가이드.md` · `16_운영_메뉴얼.md`)는 바이트 단위로 바꾸지 않는다.
- 멘토 실명은 커밋 메시지 · PR 본문 · 로그 · 문서 어디에도 쓰지 않는다.
- 비공개 저장소의 7개 파일은 원문 그대로다(sha256 일치). 고치지 않는다.
- 변경은 작업 브랜치 → develop PR(merge commit) → 릴리스 때 develop → main. CI 가 있으면 녹색을 확인한 뒤 머지한다.
- 스테이징은 경로를 명시한다 — `git add -A` 금지.
- 모든 git 명령은 `-C <절대경로>` 로 낸다. Python 은 `py -I -X utf8`(`-I` 는 `PYTHONUTF8` 환경변수를 무시한다).
- 커밋 메시지 끝: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` · PR 본문 끝: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- 사본 저장소 이름: `DevPathAi/leva-business-docs`(private). 링크 대체 문구: `(비공개 저장소로 이동, 2026-10)`. 새 소개 문구: `사수 없는 0~3년차 개발자의 첫 AI 사수`. 가격 머리말: `> 현행 가격: 정식 전환 시 월 9,900원 예정(2026-10 기준). 본문의 월 14,900원은 작성 당시 가설입니다.`

## Review Focus

1. 한글 · 이모지 파일명이 복사 · 커밋 중 다른 이름이 된다 → 사본의 파일명 집합이 원본 7개와 같아야 한다 — Task 1 Step 7 `provenance.py verify`(이름 집합 + blob 해시).
2. Windows 줄바꿈 자동 변환으로 원문 바이트가 바뀐다 → sha256 이 같아야 한다 — Task 1 Step 4(`core.autocrlf false` · `.gitattributes` 의 `* -text`) + Step 7 의 커밋된 blob 비교.
3. 편집이 대상 줄 밖을 건드린다(줄바꿈 변환 포함) → 변경 규모가 계획 실측값과 같아야 한다 — Task 2 Step 5 · Task 3 Step 2 의 `--shortstat` 단언.
4. 공개 범위 변경이 엉뚱한 저장소에 적용된다 → `devpath-landing-page` 한 줄만 바뀌어야 한다 — Task 4 Step 6 저장소 목록 diff.
5. 구 랜딩을 비공개로 돌리면 리드 수집이 끊긴다 → 홈 `/api/stats` 가 전후 모두 200 · `"ok":true` 여야 한다 — Task 4 Step 1 · Step 6.

---

## 공통 변수 (모든 Task 의 셸 첫머리에 둔다)

```bash
DOC=D:/workspace/dpa/documents
WT=D:/workspace/dpa/.worktrees/documents-visibility-cleanup
TOOLS=$WT/docs/superpowers/plans/2026-10-15-repo-visibility-cleanup
PRIV=D:/workspace/dpa/leva-business-docs
SCR=D:/workspace/dpa/.worktrees/visibility-cleanup-state   # Task 5(다음 캠페인, 다른 세션)도 읽으므로 영구 경로
MOVED=("28_장기_전략.md" "29_예비창업패키지_사업계획서.md" "30_발표_QA_스크립트.md" "31_통계_출처_검증.md" "32_영상_대본.md" "35_모두의_창업_프로그램_참고.md" "pitch-deck.html")
```

`SRC`(원본 커밋)는 Task 1 Step 1 에서 정하고 `$SCR/src_sha.txt` 에 적는다. 이후 Task 는 `SRC=$(cat $SCR/src_sha.txt)` 로 읽는다.
파일이 없으면(다른 기기 등) 비공개 저장소 README 「출처」에서 되찾는다:
`gh api repos/DevPathAi/leva-business-docs/contents/README.md --jq .content | base64 -d | grep -oE '[0-9a-f]{40}' | head -1`

---

### Task 1: 비공개 저장소 `leva-business-docs` 에 원문 보존

**Files:**
- Create(신규 저장소 `D:/workspace/dpa/leva-business-docs`): `.gitattributes` · `CLAUDE.md` · `README.md` · 이동 대상 7개(원문)
- Create(documents 워크트리): `D:/workspace/dpa/.worktrees/documents-visibility-cleanup`(브랜치 `docs/visibility-cleanup`)

**Interfaces:**
- Consumes: documents origin/develop(이 계획 PR 이 머지된 상태 — 도구가 들어 있어야 한다)
- Produces: `$SCR/src_sha.txt`(원본 커밋 SHA) · 원격 `DevPathAi/leva-business-docs` 의 main · develop 에 7개 파일 · Task 2 가 쓰는 워크트리 `$WT`

- [ ] **Step 1: 워크트리를 만들고 원본 커밋을 고정한다**

```bash
git -C $DOC fetch -q origin
mkdir -p $SCR
git -C $DOC worktree add -q -b docs/visibility-cleanup --no-track $WT origin/develop
SRC=$(git -C $WT rev-parse HEAD); echo "$SRC" > $SCR/src_sha.txt; echo "SRC=$SRC"
ls $TOOLS
```

Expected: `ls` 가 `apply_edits.py check_cleanup.py provenance.py test_check_cleanup.py` 를 보인다. 없으면 이 계획 PR 이 develop 에 머지되지 않은 것 — STOP.

- [ ] **Step 2: 검사기 단위 테스트를 돌린다**

Run: `py -I -X utf8 $TOOLS/test_check_cleanup.py`
Expected: `Ran 13 tests` · `OK`

- [ ] **Step 3: 저장소가 아직 없는지 확인하고 비공개로 만든다**

```bash
gh repo view DevPathAi/leva-business-docs --json name 2>&1 | head -1
curl -s -o /dev/null -w "anon=%{http_code}\n" https://github.com/DevPathAi/leva-business-docs
gh repo create DevPathAi/leva-business-docs --private --description "Leva 사업·지원사업 제출 문서 보관(비공개)" --disable-wiki --disable-issues
gh repo view DevPathAi/leva-business-docs --json visibility -q .visibility
```

Expected: 첫 줄 `GraphQL: Could not resolve to a Repository …` · `anon=404` · 마지막 줄 `PRIVATE`. 첫 줄이 저장소 정보를 돌려주면 이미 있는 것 — STOP 하고 보고.

- [ ] **Step 4: 로컬 저장소를 초기화한다(줄바꿈 변환 끔)**

```bash
git init -q -b main $PRIV
git -C $PRIV config core.autocrlf false
printf '* -text\n' > $PRIV/.gitattributes
```

`$PRIV/CLAUDE.md` 내용:

```markdown
# CLAUDE.md — leva-business-docs (비공개)

> Leva(레바) 사업 · 지원사업 제출 시점 문서 보관소. 공개 저장소 `DevPathAi/documents` 에서 2026-10 에 옮겨 왔다.

## 원칙

- 원문을 고치지 않는다. 현행 기준과 다른 수치 · 표현이 있어도 제출 당시 기록이다.
- 파일의 출처와 sha256 은 README 「출처」 표에 있다. 바꿔야 하면 새 파일로 추가하고 원본은 둔다.
- 비밀값은 절대 커밋하지 않는다.

## Git 브랜치 전략

`main` 은 보호 브랜치로 취급한다(이 저장소는 Free 요금제 비공개라 GitHub 보호 규칙을 걸 수 없다 — 규칙으로 지킨다).

1. `develop` 에서 `docs/*` · `chore/*` 브랜치를 분기한다.
2. 작업 브랜치 → `develop` PR → 머지(merge commit).
3. 릴리스 때만 `develop` → `main` PR → 머지.

`main` · `develop` 에 직접 push 하지 않는다.
```

`$PRIV/README.md` 내용:

```markdown
# leva-business-docs (비공개)

Leva(레바) 사업 · 지원사업 제출 시점 문서 보관소다. 공개 저장소 `DevPathAi/documents` 에서 2026-10 에 옮겨 왔다
(설계: documents `docs/superpowers/specs/2026-10-15-repo-visibility-cleanup-design.md`).
원문을 고치지 않고 보존한다 — 현행 기준과 다른 수치 · 표현이 있어도 제출 당시 기록이다.
```

- [ ] **Step 5: 초기화 커밋을 main 에 올리고 develop 을 만든다**

```bash
git -C $PRIV add .gitattributes CLAUDE.md README.md
git -C $PRIV commit -q -F - <<'EOF'
chore: 저장소 초기화 — 비공개 사업 문서 보관소

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $PRIV remote add origin https://github.com/DevPathAi/leva-business-docs.git
git -C $PRIV push -q -u origin main
git -C $PRIV switch -q -c develop && git -C $PRIV push -q -u origin develop
git -C $PRIV ls-remote --heads origin
```

Expected: `refs/heads/develop` · `refs/heads/main` 두 줄. (빈 저장소의 첫 push 다 — 이후 main · develop 직접 push 는 없다.)

- [ ] **Step 6: 작업 브랜치에 원문 7개와 출처 표를 넣는다**

```bash
SRC=$(cat $SCR/src_sha.txt)
git -C $PRIV switch -q -c docs/import-business-docs
for f in "${MOVED[@]}"; do git -C $WT show "$SRC:$f" > "$PRIV/$f"; done
{ printf '\n## 출처\n\n- 원본: `DevPathAi/documents` 커밋 `%s`(develop)\n- 이동일: %s\n\n' "$SRC" "$(date -u +%F)"
  py -I -X utf8 $TOOLS/provenance.py table --src $WT --sha $SRC; } >> $PRIV/README.md
tail -12 $PRIV/README.md
```

Expected: 출처 절과 7행 표(`| \`28_장기_전략.md\` | \`<64자 hex>\` |` …).

- [ ] **Step 7: 커밋 전 검증이 실패하는지 보고, 커밋한 뒤 통과하는지 본다**

```bash
py -I -X utf8 $TOOLS/provenance.py verify --src $WT --sha $SRC --dst $PRIV --ref HEAD; echo "exit=$?"
git -C $PRIV add .gitattributes README.md "${MOVED[@]}"
git -C $PRIV commit -q -F - <<'EOF'
docs: documents 제출 시점 사업 문서 7개 원문 보존

공개 저장소 documents 에서 옮겨 온다(원문 그대로, 출처·sha256 은 README).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
py -I -X utf8 $TOOLS/provenance.py verify --src $WT --sha $SRC --dst $PRIV --ref HEAD; echo "exit=$?"
git -C $PRIV ls-files | wc -l
```

Expected: 첫 verify = `FAIL 사본에 없는 파일: [...]` · `exit=1`. 둘째 verify = `PASS` 7줄 · `exit=0`. `ls-files` = `10`(7 + `.gitattributes` · `CLAUDE.md` · `README.md`).

- [ ] **Step 8: develop · main 으로 PR 머지(2단계)**

```bash
git -C $PRIV push -q -u origin docs/import-business-docs
gh pr create -R DevPathAi/leva-business-docs --base develop --head docs/import-business-docs \
  --title "docs: documents 제출 시점 사업 문서 7개 원문 보존" \
  --body "$(printf '공개 저장소 documents 에서 옮겨 온 원문 7개. 출처·sha256 은 README.\n\n`provenance.py verify` 7/7 PASS.\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)')"
gh pr merge -R DevPathAi/leva-business-docs docs/import-business-docs --merge
gh pr create -R DevPathAi/leva-business-docs --base main --head develop --title "release: 사업 문서 보존본" \
  --body "$(printf 'develop → main 릴리스.\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)')"
gh pr merge -R DevPathAi/leva-business-docs develop --merge
```

이 저장소에는 CI 가 없다 — 머지 판단 근거는 Step 7 의 verify 결과다.

- [ ] **Step 9: 원격 main 을 다시 검증한다**

```bash
git -C $PRIV fetch -q origin
py -I -X utf8 $TOOLS/provenance.py verify --src $WT --sha $SRC --dst $PRIV --ref origin/main; echo "exit=$?"
gh repo view DevPathAi/leva-business-docs --json visibility -q .visibility
curl -s -o /dev/null -w "anon=%{http_code}\n" https://github.com/DevPathAi/leva-business-docs
```

Expected: `PASS` 7줄 · `exit=0` · `PRIVATE` · `anon=404`.

---

### Task 2: documents — 이동 대상 7개 삭제 · 링크 정리

**Files:**
- Delete: 이동 대상 7개(documents 최상위)
- Modify: `17_스케줄.md`(2곳) · `45_Tier3_확장_기능_카탈로그.md`(2곳) · `Home.md`(5곳, `[[위키 링크]]`) · `README.md`(7곳 — 표 6행 + 읽기 경로 1행)
- Test: `$TOOLS/check_cleanup.py`

**Interfaces:**
- Consumes: Task 1 의 `$WT` · `$SCR/src_sha.txt` · 원격 `leva-business-docs` main(검증 통과)
- Produces: 브랜치 `docs/visibility-cleanup` 의 커밋 1개(삭제 + 링크)

편집 원문 → 결과(`apply_edits.py` 의 `LINK_EDITS` 와 같다):

| 파일 | 원문 | 결과 |
|---|---|---|
| 17 | ` · 정렬 근거 [29_예비창업패키지_사업계획서](./29_….md) · [35_모두의_창업_프로그램_참고](./35_….md).` | ` · 정렬 근거 29_예비창업패키지_사업계획서 · 35_모두의_창업_프로그램_참고 (비공개 저장소로 이동, 2026-10).` |
| 17 | `- [29_…](./29_….md) · [35_…](./35_….md)` | `- 29_예비창업패키지_사업계획서 · 35_모두의_창업_프로그램_참고 (비공개 저장소로 이동, 2026-10)` |
| 45 | `B2B는 별도 수익 축([28_장기_전략](./28_장기_전략.md) 참조).` | `B2B는 별도 수익 축(28_장기_전략 참조 — 비공개 저장소로 이동, 2026-10).` |
| 45 | `- [28_장기_전략](./28_장기_전략.md) — 사업 확장 축(B2B·예창패 등)` | `- 28_장기_전략 — 사업 확장 축(B2B·예창패 등) (비공개 저장소로 이동, 2026-10)` |
| Home | `\| 28 \| [[28_장기_전략]] — 장기 전략 (90일 통합) \|` (29~32 같은 꼴) | `\| 28 \| 28_장기_전략 — 장기 전략 (90일 통합) (비공개 저장소로 이동, 2026-10) \|` |
| README | `\| 28 \| [장기 전략 (90일 통합)](./28_장기_전략.md) \|` (29~32 · 피치덱 같은 꼴) | `\| 28 \| 장기 전략 (90일 통합) (비공개 저장소로 이동, 2026-10) \|` |
| README | `\| 심사 / 투자자 대응 \| 27 → 29 → 30 → 31 → pitch-deck \|` | `\| 심사 / 투자자 대응 \| 27 (29·30·31·피치덱은 비공개 저장소로 이동, 2026-10) \|` |

- [ ] **Step 1: 사본 검증이 통과했는지 다시 확인한다(삭제 전 관문)**

```bash
SRC=$(cat $SCR/src_sha.txt)
git -C $PRIV fetch -q origin
py -I -X utf8 $TOOLS/provenance.py verify --src $WT --sha $SRC --dst $PRIV --ref origin/main; echo "exit=$?"
```

Expected: `exit=0`. 아니면 STOP — documents 에서 지우지 않는다.

- [ ] **Step 2: 검사기가 적용 전 상태에서 실패하는지 본다**

Run: `py -I -X utf8 $TOOLS/check_cleanup.py --repo $WT --base $SRC | sed 's/ —.*//'`
Expected:

```
FAIL C1 이동 대상 7개 없음
FAIL C2 멘토 실명 0건(전체 트리)
FAIL C3 최상위 md 에 「최초의 개발자 교육」·「유일한 한국」 없음
FAIL C4 17·27 현행 가격 머리말
PASS C5 기준 커밋 대비 새로 끊긴 상대 링크 0개(최상위 md)
FAIL C9 이동 대상 7개를 가리키는 링크 0개(최상위 md)
PASS C6 6개 가이드·.github·tools 변경 없음
FAIL C7 README·Home 새 소개 문구
FAIL C8 06 상자 줄 폭 유지·「최초의」 없음
```

- [ ] **Step 3: 링크 단계를 적용한다**

Run: `py -I -X utf8 $TOOLS/apply_edits.py --repo $WT --stage links`
Expected: `applied links: 4 files edited`. `STOP …` 이 나오면 원문이 develop 에서 바뀐 것 — 원문을 다시 읽고 `apply_edits.py` 를 고칠지 사용자에게 보고한다(즉흥 수정 금지).

- [ ] **Step 4: 검사기로 링크 단계 결과를 본다**

Run: `py -I -X utf8 $TOOLS/check_cleanup.py --repo $WT --base $SRC | sed 's/ —.*//'`
Expected: `PASS` = C1 · C2 · C5 · C9 · C6, `FAIL` = C3 · C4 · C7 · C8(Task 3 몫).

- [ ] **Step 5: 변경 규모가 실측과 같은지 본다**

Run: `git -C $WT add 17_스케줄.md 45_Tier3_확장_기능_카탈로그.md Home.md README.md && git -C $WT diff --cached --shortstat`
Expected: ` 11 files changed, 16 insertions(+), 4653 deletions(-)`. 다르면 STOP — `git -C $WT diff --cached` 로 원인을 본다.

- [ ] **Step 6: 커밋한다**

```bash
git -C $WT commit -q -F - <<'EOF'
docs: 제출 시점 사업 문서 7개를 비공개 저장소로 이동 — 링크 정리

28~32·35·pitch-deck.html 을 leva-business-docs(비공개)로 옮기고, 최상위 문서 4개의
링크 16곳을 「(비공개 저장소로 이동, 2026-10)」 텍스트로 바꾼다.
스펙: docs/superpowers/specs/2026-10-15-repo-visibility-cleanup-design.md

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $WT log --oneline -1
```

---

### Task 3: documents — 문구 · 가격 머리말 · 캠페인 체크리스트, develop 머지

**Files:**
- Modify: `README.md`:3 · `Home.md`:3 · `01_프로젝트_계획서.md`:16 · `20_커뮤니티_기능_설계서.md`:14 · `21_유료_플랜_참고설계.md`:170 · `06_화면_기능_정의서.md`:61 · `22_AR_아키텍처_체험_참고설계.md`:38 · `17_스케줄.md`(머리) · `27_MVP_설계서.md`(머리) · `docs/superpowers/plans/2026-10-03-next-campaign-prep.md`(§1 항목 1)
- Test: `$TOOLS/check_cleanup.py`

**Interfaces:**
- Consumes: Task 2 의 커밋이 있는 `docs/visibility-cleanup`
- Produces: documents develop 머지 커밋(Task 5 가 main 으로 올린다)

편집 원문 → 결과(`apply_edits.py` 의 `WORD_EDITS` 와 같다):

| 파일 | 원문 | 결과 |
|---|---|---|
| README · Home 3행 | `> **"내 수준에 맞는 다음 단계를 AI가 안내하는 최초의 개발자 교육"**` | `> **"사수 없는 0~3년차 개발자의 첫 AI 사수"**` |
| 01:16 | `**"당신의 GitHub과 실력을 아는 유일한 한국 개발자 학습 플랫폼"**` | `**"당신의 GitHub과 실력을 아는 한국 개발자 학습 플랫폼"**` |
| 20:14 | `"학습 맥락을 아는 유일한 한국 개발자 커뮤니티"` | `"학습 맥락을 아는 한국 개발자 커뮤니티"` |
| 21:170 | `시니어가 답하는 유일한 한국 플랫폼.` | `시니어가 답하는 한국 플랫폼.` |
| 06:61 | `│  "Pod 간 거리를 걸어서 이해하는 최초의 개발자 교육"          │` | `│  "Pod 간 거리를 걸어서 이해하는 개발자 교육"` + 공백 18칸 + `│`(표시 폭 65 = 윗줄) |
| 22:38 | `- **"Pod 간 거리를 걸어서 이해하는 최초의 개발자 교육"** 슬로건` | `- **"Pod 간 거리를 걸어서 이해하는 개발자 교육"** 슬로건` |
| 17 · 27 | 제목 줄 + 빈 줄 | 제목 줄 + 빈 줄 + 가격 머리말 + 빈 줄 |
| next-campaign-prep §1-1 | `   릴리스 후 **새 documents main SHA** 가 … 된다.` 다음 | 두 줄 추가 — 「이 릴리스에는 공개 저장소 정리(…)가 함께 들어간다 — 머지 뒤 `check_cleanup.py` 를 main 트리에 다시 돌려 전부 PASS 인지 본다(계획 Task 5).」 |

- [ ] **Step 1: 문구 단계를 적용한다**

Run: `py -I -X utf8 $TOOLS/apply_edits.py --repo $WT --stage words`
Expected: `applied words: 10 files edited`

- [ ] **Step 2: 검사기 전부 통과 · 변경 규모 확인**

```bash
SRC=$(cat $SCR/src_sha.txt)
py -I -X utf8 $TOOLS/check_cleanup.py --repo $WT --base $SRC; echo "exit=$?"
git -C $WT diff --shortstat
```

Expected: 9줄 모두 `PASS` · `exit=0` · ` 10 files changed, 13 insertions(+), 7 deletions(-)`.

- [ ] **Step 3: 상자 그림을 눈으로 본다**

Run: `sed -n 59,62p "$WT/06_화면_기능_정의서.md"`
Expected: 오른쪽 `│` 가 위아래 줄과 같은 열에 선다(고정폭 글꼴 기준).

- [ ] **Step 4: 커밋한다**

```bash
git -C $WT add README.md Home.md 01_프로젝트_계획서.md 20_커뮤니티_기능_설계서.md 21_유료_플랜_참고설계.md \
  06_화면_기능_정의서.md 22_AR_아키텍처_체험_참고설계.md 17_스케줄.md 27_MVP_설계서.md \
  docs/superpowers/plans/2026-10-03-next-campaign-prep.md
git -C $WT commit -q -F - <<'EOF'
docs: 최상위 문서의 「최초」·「유일한」 문구 정리, 17·27 현행 가격 머리말

README·Home 소개 문구를 랜딩과 같은 「사수 없는 0~3년차 개발자의 첫 AI 사수」로 바꾸고,
01·20·21 의 「유일한」, 06·22 의 「최초의」를 뺀다. 17·27 은 본문을 두고 머리말만 단다.
다음 캠페인 체크리스트 §1 에 main 반영 뒤 재검사를 적는다.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $WT status --short | wc -l
```

Expected: `0`(남은 변경 없음).

- [ ] **Step 5: develop 으로 PR · CI · 머지**

```bash
git -C $WT push -q -u origin docs/visibility-cleanup
gh pr create -R DevPathAi/documents --base develop --head docs/visibility-cleanup \
  --title "docs: 공개 저장소 정리 — 사업 문서 7개 비공개 이동·최상위 문구 정리" \
  --body "$(printf '스펙 docs/superpowers/specs/2026-10-15-repo-visibility-cleanup-design.md · 계획 Task 2·3.\n\n- 7개 → leva-business-docs(비공개, sha256 7/7 일치)\n- 링크 16곳 텍스트화, 문구 7곳, 17·27 가격 머리말, 캠페인 체크리스트 1곳\n- check_cleanup.py 9/9 PASS\n\nmain 반영은 다음 캠페인 candidate 생성 전(계획 Task 5).\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)')"
gh pr checks docs/visibility-cleanup -R DevPathAi/documents --watch
gh pr merge docs/visibility-cleanup -R DevPathAi/documents --merge
```

Expected: `privacy-producer-contract` `pass` 뒤 머지. 실패하면 머지하지 않고 로그를 읽는다.

- [ ] **Step 6: 머지된 develop 을 새로 받아 다시 검사한다**

```bash
git -C $DOC fetch -q origin
T=D:/workspace/dpa/.worktrees/documents-visibility-verify
git -C $DOC worktree add -q --detach $T origin/develop
py -I -X utf8 $TOOLS/check_cleanup.py --repo $T --base $(cat $SCR/src_sha.txt); echo "exit=$?"
git -C $DOC worktree remove $T
```

Expected: 9줄 `PASS` · `exit=0`.

---

### Task 4: 구 랜딩 저장소 비공개 → 보관

**Files:** 없음(저장소 설정만)

**Interfaces:**
- Consumes: 없음(Task 1~3 과 독립. Task 1 뒤에 하면 목록에 `leva-business-docs` 가 전후 모두 있다)
- Produces: `devpath-landing-page` = PRIVATE · archived

- [ ] **Step 1: 전 상태를 기록한다**

```bash
gh repo list DevPathAi --limit 100 --json name,visibility,isArchived -q 'sort_by(.name)[] | "\(.name) \(.visibility) \(.isArchived)"' > $SCR/repos-before.txt
grep devpath-landing-page $SCR/repos-before.txt
curl -s -w "\nstats=%{http_code}\n" https://leva.ai.kr/api/stats
```

Expected: `devpath-landing-page PUBLIC false` · 본문에 `"ok":true` · `stats=200`.

- [ ] **Step 2: 열린 PR · 이슈를 기록한다(보관하면 읽기 전용이 된다)**

```bash
gh pr list -R DevPathAi/devpath-landing-page --state open --json number,title
gh issue list -R DevPathAi/devpath-landing-page --state open --json number,title
```

Expected: 결과를 보고에 그대로 남긴다(있으면 번호 · 제목). 열린 PR 이 있으면 STOP 하고 사용자에게 처리 방침을 묻는다.

- [ ] **Step 3: 비공개로 돌린다**

Run: `gh repo edit DevPathAi/devpath-landing-page --visibility private --accept-visibility-change-consequences`

- [ ] **Step 4: 보관한다**

Run: `gh repo archive DevPathAi/devpath-landing-page --yes`

- [ ] **Step 5: 후 상태를 기록한다**

```bash
gh repo list DevPathAi --limit 100 --json name,visibility,isArchived -q 'sort_by(.name)[] | "\(.name) \(.visibility) \(.isArchived)"' > $SCR/repos-after.txt
```

- [ ] **Step 6: 바뀐 것이 구 랜딩 한 줄뿐인지 · 리드 수집이 그대로인지 본다**

```bash
diff $SCR/repos-before.txt $SCR/repos-after.txt
curl -s -o /dev/null -w "anon=%{http_code}\n" https://github.com/DevPathAi/devpath-landing-page
curl -s -w "\nstats=%{http_code}\n" https://leva.ai.kr/api/stats
```

Expected:

```
< devpath-landing-page PUBLIC false
---
> devpath-landing-page PRIVATE true
```

(diff 출력의 줄 번호 표기 `NcN` 은 목록 위치에 따른다) · `anon=404` · 본문 `"ok":true` · `stats=200`. diff 에 다른 줄이 있으면 STOP — 되돌리기(스펙 §7) 전에 사용자에게 보고한다.

---

### Task 5: (다음 캠페인 — candidate 생성 전) documents main 반영 · 재검사

이 Task 는 지금 실행하지 않는다. 다음 캠페인 체크리스트(`docs/superpowers/plans/2026-10-03-next-campaign-prep.md` §1 항목 1 — Task 3 에서 두 줄을 더했다)의 documents develop → main 릴리스와 같은 동작이다.

**Interfaces:**
- Consumes: Task 3 의 develop 머지 커밋
- Produces: documents main 에 정리 반영(공개 화면이 바뀌는 시점) — 그 main SHA 가 다음 candidate 의 `approval_source_sha` 가 된다

- [ ] **Step 1: candidate 를 아직 만들지 않았는지 확인한다**

다음 캠페인의 candidate 런이 없어야 한다. 이미 있으면 STOP — main 을 움직이면 그 candidate 가 `candidate approval_source_sha mismatch` 로 거부된다.

- [ ] **Step 2: develop → main PR 을 올리고 CI 녹색 뒤 머지한다**

```bash
gh pr create -R DevPathAi/documents --base main --head develop --title "release: documents develop → main" \
  --body "$(printf '다음 캠페인 candidate 전 릴리스. 공개 저장소 정리(2026-10-15) 포함.\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)')"
gh pr checks develop -R DevPathAi/documents --watch
gh pr merge develop -R DevPathAi/documents --merge
```

- [ ] **Step 3: main 트리를 다시 검사한다**

```bash
git -C $DOC fetch -q origin
T=D:/workspace/dpa/.worktrees/documents-main-verify
git -C $DOC worktree add -q --detach $T origin/main
py -I -X utf8 $T/docs/superpowers/plans/2026-10-15-repo-visibility-cleanup/check_cleanup.py --repo $T --base $(cat $SCR/src_sha.txt)
git -C $DOC worktree remove $T
curl -s -o /dev/null -w "anon blob 29=%{http_code}\n" "https://github.com/DevPathAi/documents/blob/main/29_%EC%98%88%EB%B9%84%EC%B0%BD%EC%97%85%ED%8C%A8%ED%82%A4%EC%A7%80_%EC%82%AC%EC%97%85%EA%B3%84%ED%9A%8D%EC%84%9C.md"
```

Expected: C1 · C2 · C3 · C4 · C7 · C8 · C9 `PASS` · `anon blob 29=404`. C5 · C6 은 Task 3 이후 develop 에 들어온 다른 PR 때문에 기준(`SRC`)과 달라질 수 있다 — FAIL 이면 `git -C $DOC log --oneline "$(cat $SCR/src_sha.txt)"..origin/main -- .github tools 09_Git_규칙_정의서.md 10_환경_설정_템플릿.md 11_테스트_전략서.md 12_코드_리뷰_규칙.md 14_배포_가이드.md 16_운영_메뉴얼.md` 로 그 변경이 이 정리와 무관한 PR 에서 왔는지 확인하고 기록한다.

- [ ] **Step 4: 로그아웃 상태 화면을 확인한다**

`https://github.com/DevPathAi/documents` 를 로그아웃 상태로 열어 README 3행이 「사수 없는 0~3년차 개발자의 첫 AI 사수」이고 문서 표의 28~32 · 피치덱이 「(비공개 저장소로 이동, 2026-10)」 텍스트인지 본다.
