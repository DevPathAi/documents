# 전체 정합성 점검 2차 + 리팩토링 실행계획 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 워크스페이스 전체(문서+코드)의 2차 정합성 점검을 수행하고 `42_전체_정합성_점검_2차.md`(점검 보고서)와 `43_정합성_리팩토링_실행계획서.md`(문서 수정 실행계획)를 산출한다.

**Architecture:** Phase 0(기준 확정) → Phase 1(38번 회귀 체크) → Phase 2(읽기 전용 에이전트 병렬 사실 수집) → Phase 3(컨트롤러 교차 대조) → Phase 4(42·43번 작성·색인·PR). 모든 점검은 각 레포 `origin/develop` 트리를 기준으로 하며, 어떤 서비스 레포의 파일도 수정하지 않는다. 산출물과 중간 근거는 전부 `documents` 레포 `docs/consistency-check-round2` 브랜치에 커밋한다.

**Tech Stack:** git(`git show`/`git ls-tree`/`git grep`로 origin/develop 트리 읽기), 읽기 전용 탐색 서브에이전트, gh CLI(PR).

**스펙:** [2026-07-02-consistency-refactor-round2-design.md](../specs/2026-07-02-consistency-refactor-round2-design.md)

## Global Constraints

- 워크스페이스 루트: `D:\workspace\dpa` (Git Bash 경로 `/d/workspace/dpa`)
- 점검 기준: 각 레포 `origin/develop` 트리 고정. 워킹트리·체크아웃 브랜치는 기준이 아니며 **절대 체크아웃을 바꾸지 않는다**. 읽기는 `git show origin/develop:<path>`, `git ls-tree -r --name-only origin/develop`, `git grep <pat> origin/develop -- <path>`만 사용
- `origin/develop`이 없는 레포는 `origin/HEAD` 기본 브랜치를 기준으로 쓰고 그 사실을 산출물에 명기
- **코드가 진실**: 문서를 코드에 맞춘다. 코드 수정 항목은 43번에 넣지 않는다. 발견된 코드 문제는 42번 "관찰 사항"에만 기록
- 쓰기 허용 범위: `documents` 레포 `docs/consistency-check-round2` 브랜치의 `42_*.md`, `43_*.md`, `README.md`, `Home.md`, `docs/superpowers/reports/2026-07-02-consistency-round2-*.md` **만**. 다른 레포·다른 파일 쓰기 금지. `documents`의 기존 미추적 파일(`.tier1-baseline.md` 등)은 add 금지
- 제외 대상: `*.zip`, `*.pdf`, `node_modules/`, `build/`, `.gstack/`, 빌드 산출물
- 커밋: Conventional Commits, 예: `docs(consistency): ...`
- 서브에이전트 지시문에는 반드시 아래 Scope Lock 문구를 그대로 포함한다:

```text
[Scope Lock] 이 조사 Task만 수행하라. 끝나면 결과를 보고하고 정지하라. 다른 Task로 진행하지 말라.
어떤 파일도 수정·생성·삭제하지 말라(완전 읽기 전용). git fetch/checkout/switch도 금지한다(이미 완료됨).
명세가 부족하거나 대상이 존재하지 않으면 추측하지 말고 "NEEDS_CONTEXT: <무엇이 부족한지>"로 보고하라.
```

- 서브에이전트가 실패·무응답이면 resume하지 말고 **동일 지시문으로 신규 dispatch**한다 (Windows 불안정 이력)
- 컨트롤러는 각 에이전트 보고에서 핵심 사실 2~3개를 직접 명령으로 재확인(표본 검증)한 뒤에만 결과를 수용한다

---

### Task 1: Phase 0 — 기준 확정(baseline) 보고서

**Files:**
- Create: `docs/superpowers/reports/2026-07-02-consistency-round2-baseline.md` (documents 레포)

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: 레포별 기준 SHA 표 + 미머지 브랜치 표. 이후 모든 태스크는 이 표의 `기준 ref`(레포별 `origin/develop` 또는 대체 브랜치)를 사용한다

- [ ] **Step 1: 전 레포 fetch + 기준 수집 스크립트 실행**

Git Bash에서 실행:

```bash
cd /d/workspace/dpa
for d in */ .github/; do
  [ -d "$d/.git" ] || continue
  name=$(basename "$d")
  git -C "$d" fetch origin --quiet 2>/dev/null
  if git -C "$d" rev-parse --verify origin/develop >/dev/null 2>&1; then
    ref="origin/develop"
  else
    ref=$(git -C "$d" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/||')
  fi
  sha=$(git -C "$d" rev-parse --short "$ref" 2>/dev/null)
  date=$(git -C "$d" log -1 --format=%ad --date=short "$ref" 2>/dev/null)
  echo "| $name | $ref | $sha | $date |"
done
```

기대 출력: 레포당 1행(devpath-* 13개 + documents + 기타 git 레포). `ref`가 `origin/develop`이 아닌 레포는 표시됨.

- [ ] **Step 2: 미머지 브랜치(진행 중 작업) 수집**

```bash
cd /d/workspace/dpa
for d in */ .github/; do
  [ -d "$d/.git" ] || continue
  name=$(basename "$d")
  base=$(git -C "$d" rev-parse --verify origin/develop >/dev/null 2>&1 && echo origin/develop || git -C "$d" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/||')
  git -C "$d" branch -r --no-merged "$base" 2>/dev/null | grep -v 'HEAD' | sed "s|^ *|\| $name \| |; s|\$| \||"
done
```

기대 출력: `| 레포 | origin/브랜치명 |` 형식 행들 (없으면 그 레포는 0행).

- [ ] **Step 3: baseline 보고서 작성**

`documents/docs/superpowers/reports/2026-07-02-consistency-round2-baseline.md`에 아래 구조로 저장:

```markdown
# 정합성 점검 2차 — 기준(baseline) 확정

> 작성일: 2026-07-02 / 스펙: ../specs/2026-07-02-consistency-refactor-round2-design.md

## 1. 레포별 점검 기준 ref
| 레포 | 기준 ref | SHA | 마지막 커밋일 |
|---|---|---|---|
(Step 1 출력)

## 2. origin/develop 부재 레포
(해당 레포와 대체 기준 명기. 없으면 "없음")

## 3. 진행 중 작업(미머지 원격 브랜치) — 참고용, 점검 기준 아님
| 레포 | 브랜치 |
|---|---|
(Step 2 출력)

## 4. git 레포가 아닌 최상위 디렉터리
(예: templates 등 — Step 1 루프에서 제외된 디렉터리를 `ls`와 대조해 나열)
```

- [ ] **Step 4: 검증**

- 표 1의 행 수 ≥ 14 (devpath-* 13 + documents)인지 확인. 부족하면 어떤 레포가 빠졌는지 `ls /d/workspace/dpa`와 대조해 원인 규명(레포가 git이 아니면 4절에 기록)
- 표 1의 모든 SHA가 비어있지 않은지 확인

- [ ] **Step 5: 커밋**

```bash
cd /d/workspace/dpa/documents
git add docs/superpowers/reports/2026-07-02-consistency-round2-baseline.md
git commit -m "docs(consistency): 2차 점검 기준(baseline) 확정 보고서"
```

---

### Task 2: Phase 1 — 38번 수정계획 회귀 체크

**Files:**
- Create: `docs/superpowers/reports/2026-07-02-consistency-round2-regression-check.md` (documents 레포)
- 참조: `documents/38_정합성_수정계획서.md` (origin/develop 기준으로 읽기)

**Interfaces:**
- Consumes: Task 1의 레포별 기준 ref
- Produces: 38번 23개 항목(P0-1~P0-5, P1-1~P1-11, P2-1~P2-4, I-1~I-3)의 판정 표. Task 9(42번 작성)가 이 표를 그대로 인용한다

- [ ] **Step 1: 38번 전문을 기준 ref에서 읽기**

```bash
cd /d/workspace/dpa/documents
git show origin/develop:38_정합성_수정계획서.md
```

23개 항목의 대상 파일·수정 내용·완료 기준을 확보한다.

- [ ] **Step 2: 항목별 판정**

각 항목에 대해 대상 파일을 **해당 레포의 기준 ref**에서 읽고 완료 기준 충족 여부를 판정한다. 판정 값: `✅ 이행` / `⚠️ 부분` / `❌ 미이행` / `➖ 대상 소멸`(파일·전제가 사라짐). 판정마다 근거 인용(파일 경로 + 확인한 문구/부재)을 1줄 이상 남긴다.

파일 읽기 예 (레포가 다르면 해당 레포에서):

```bash
git -C /d/workspace/dpa/documents show origin/develop:17_스케줄.md | head -40        # P0-1
git -C /d/workspace/dpa/devpath-ai-svc show origin/develop:README.md | head -60      # P0-2
git -C /d/workspace/dpa/devpath-ai-svc show origin/develop:CLAUDE.md | head -60      # P0-3
git -C /d/workspace/dpa/.github show origin/develop:profile/README.md 2>/dev/null || git -C /d/workspace/dpa/.github show origin/HEAD:profile/README.md   # P0-5
```

P0-4(레포별 MD1 workflow)는 platform/learning/ai/shared 각각에서 `git ls-tree -r --name-only <기준ref> | grep -i workflow`로 파일을 찾아 확인한다.

- [ ] **Step 3: 회귀 체크 보고서 작성**

`docs/superpowers/reports/2026-07-02-consistency-round2-regression-check.md`:

```markdown
# 정합성 점검 2차 — 38번 수정계획 회귀 체크

> 기준: Task 1 baseline의 레포별 ref / 판정일: 2026-07-02

| 항목 | 대상 파일 | 완료 기준(38번) | 판정 | 근거 |
|---|---|---|---|---|
| P0-1 | documents/17_스케줄.md | "OAuth 이후 전부 미착수" 제거, 부분 구현 표기 | | |
| P0-2 | devpath-ai-svc/README.md | /ai/embed, /ai/path/generate 표기 | | |
| P0-3 | devpath-ai-svc/CLAUDE.md | 현재 Ollama, 운영 목표 Claude 분리 | | |
| P0-4 | 레포별 MD1 workflow (platform/learning/ai/shared) | 완료/부분/미구현 구분 | | |
| P0-5 | .github/profile/README.md | community/sandbox 스켈레톤, ai dev Ollama 표기 | | |
| P1-1 | documents/02_ERD_문서.md | 목표/현재 구분 가능 | | |
| P1-2 | documents/02_ERD_문서.md | task_type AR 제거, v2 분리 | | |
| P1-3 | documents/06_화면_기능_정의서.md | 설계/목 구현 구분 배너 | | |
| P1-4 | documents/07_요구사항_정의서.md | 목표 요구사항 배너 | | |
| P1-5 | documents/11_테스트_전략서.md | 목표 전략 배너 | | |
| P1-6 | documents/14_배포_가이드.md | 목표 배포 배너 | | |
| P1-7 | documents/16_운영_메뉴얼.md | 목표 운영 배너 | | |
| P1-8 | documents/20_커뮤니티_기능_설계서.md | 목표 설계 배너 | | |
| P1-9 | documents/26_학습맥락_자동첨부_구현.md | LCS 목표 스펙 배너 | | |
| P1-10 | documents/10_환경_설정_템플릿.md | shared compose·Flutter/melos·Ollama 기준 | | |
| P1-11 | documents/README.md, Home.md | dev Ollama / 운영 provider 목표 표기 | | |
| P2-1 | workflow-guide/docs/env-setup.md | MySQL 잔존 제거 | | |
| P2-2 | workflow-guide/docs/ops-manual.md | MySQL 잔존 제거 | | |
| P2-3 | workflow-guide/docs/test-strategy.md | PostgreSQL/Flutter 정합 | | |
| P2-4 | workflow-guide/docs/git-rules.md | AR v2 참고로 강등 | | |
| I-1 | documents/README.md | 38번 링크, 27번 초안 표기 | | |
| I-2 | documents/Home.md | 38번 링크, 27번 초안 표기 | | |
| I-3 | documents/37_...점검.md | 후속 계획 링크 | | |

## 미이행·부분 항목 요약
(❌/⚠️ 항목만 모아 42번·43번에 넘길 목록)
```

주의: 위 표의 "완료 기준" 열은 38번 원문과 대조해 정확히 옮긴다(위 표는 요약 시드). 판정·근거 열을 전부 채운다 — 빈 칸이 남으면 이 Task는 미완료다.

- [ ] **Step 4: 검증**

- 판정 행 수 = 23 확인: `grep -c '^| [PI]' docs/superpowers/reports/2026-07-02-consistency-round2-regression-check.md` → 23
- ❌/⚠️ 항목이 "미이행·부분 요약" 절에 모두 재등장하는지 확인

- [ ] **Step 5: 커밋**

```bash
cd /d/workspace/dpa/documents
git add docs/superpowers/reports/2026-07-02-consistency-round2-regression-check.md
git commit -m "docs(consistency): 38번 수정계획 회귀 체크 결과"
```

---

### Task 3: Phase 2-① — 백엔드 서비스 7개 사실 수집

**Files:**
- Create: `docs/superpowers/reports/2026-07-02-consistency-round2-facts-backend.md` (documents 레포)

**Interfaces:**
- Consumes: Task 1의 기준 ref (에이전트 지시문에 그대로 기입)
- Produces: 레포별 실제 엔드포인트 표·도메인 모듈 목록·README/CLAUDE 상태 주장 표. Task 8이 소비

- [ ] **Step 1: 읽기 전용 탐색 에이전트 dispatch**

Explore(또는 read-only general-purpose) 에이전트에 아래 지시문을 그대로 전달한다. `<기준ref표>` 자리에는 Task 1 baseline 표에서 해당 7개 레포 행을 붙여넣는다:

```text
[Scope Lock] 이 조사 Task만 수행하라. 끝나면 결과를 보고하고 정지하라. 다른 Task로 진행하지 말라.
어떤 파일도 수정·생성·삭제하지 말라(완전 읽기 전용). git fetch/checkout/switch도 금지한다(이미 완료됨).
명세가 부족하거나 대상이 존재하지 않으면 추측하지 말고 "NEEDS_CONTEXT: <무엇이 부족한지>"로 보고하라.

조사 대상: D:\workspace\dpa 아래 7개 레포 — devpath-platform-svc, devpath-learning-svc,
devpath-ai-svc, devpath-community-svc, devpath-sandbox-svc, devpath-lcs-svc, devpath-notification-svc.
점검 기준은 각 레포의 아래 ref다. 워킹트리 파일을 읽지 말고 반드시 기준 ref 트리만 읽어라:
<기준ref표>

읽기 방법(Git Bash): git -C <레포경로> grep -nE "@(Get|Post|Put|Delete|Patch|Request)Mapping" <기준ref> -- "*.java"
파일 내용: git -C <레포경로> show <기준ref>:<파일경로>
파일 목록: git -C <레포경로> ls-tree -r --name-only <기준ref>

각 레포에 대해 수집하라:
1. 실제 HTTP 엔드포인트 표: | HTTP 메서드 | 경로(클래스 @RequestMapping prefix 결합한 전체 경로) | 컨트롤러 파일 |
2. 주요 도메인 모듈: src/main/java 아래 패키지 1~2단계 디렉터리 목록
3. README.md와 CLAUDE.md에서 구현 상태를 주장하는 문장(완료/미구현/부분/스택 언급) 인용: | 파일 | 주장 원문(1줄) |
4. 테스트 존재 여부: src/test 아래 파일 수

최종 보고는 위 4개 절을 레포별 섹션(## 레포명)으로 묶은 마크다운 원문으로만 반환하라. 요약·평가·제안을 덧붙이지 말라.
```

- [ ] **Step 2: 표본 검증 (컨트롤러 직접)**

에이전트 보고의 엔드포인트 표에서 서로 다른 레포의 3개를 골라 직접 재확인:

```bash
git -C /d/workspace/dpa/<레포> show <기준ref>:<보고된 컨트롤러 경로> | grep -n "Mapping"
```

보고와 불일치하면 해당 레포 부분을 신규 에이전트로 재조사시키고, 일치할 때까지 수용하지 않는다.

- [ ] **Step 3: 보고서 저장**

에이전트 보고 원문 앞에 헤더(기준 ref 표, 수집일, 표본 검증 결과 3건)를 붙여 `docs/superpowers/reports/2026-07-02-consistency-round2-facts-backend.md`로 저장.

- [ ] **Step 4: 커밋**

```bash
cd /d/workspace/dpa/documents
git add docs/superpowers/reports/2026-07-02-consistency-round2-facts-backend.md
git commit -m "docs(consistency): 백엔드 7개 svc 구현 사실 수집(2차)"
```

---

### Task 4: Phase 2-② — 프런트엔드 사실 수집

**Files:**
- Create: `docs/superpowers/reports/2026-07-02-consistency-round2-facts-frontend.md` (documents 레포)

**Interfaces:**
- Consumes: Task 1의 기준 ref
- Produces: frontend 앱별 라우트 표·구현 상태, landing-page 페이지 목록. Task 8이 소비

- [ ] **Step 1: 읽기 전용 탐색 에이전트 dispatch**

지시문 (`<기준ref표>`는 devpath-frontend, devpath-landing-page 행):

```text
[Scope Lock] 이 조사 Task만 수행하라. 끝나면 결과를 보고하고 정지하라. 다른 Task로 진행하지 말라.
어떤 파일도 수정·생성·삭제하지 말라(완전 읽기 전용). git fetch/checkout/switch도 금지한다(이미 완료됨).
명세가 부족하거나 대상이 존재하지 않으면 추측하지 말고 "NEEDS_CONTEXT: <무엇이 부족한지>"로 보고하라.

조사 대상: D:\workspace\dpa 아래 2개 레포 — devpath-frontend, devpath-landing-page.
점검 기준은 아래 ref다. 워킹트리를 읽지 말고 기준 ref 트리만 읽어라:
<기준ref표>

devpath-frontend에서 수집:
1. 앱 목록: git -C <경로> ls-tree --name-only <기준ref> apps
2. 앱별 라우트: git -C <경로> grep -nE "GoRoute|path:" <기준ref> -- "apps/web/lib" "apps/admin/lib" "apps/mobile/lib"
   → | 앱 | 라우트 경로 | 정의 파일 | 표
3. API 연동 방식: git -C <경로> grep -nlE "http|dio|Uri.parse" <기준ref> -- "apps" "packages" 중 대표 파일 3개를 열어
   실 API 호출인지 목(mock) 데이터인지 판정 근거 인용
4. README.md/CLAUDE.md의 구현 상태 주장 인용

devpath-landing-page에서 수집:
1. 페이지/라우트 목록 (기준 ref 트리의 소스 구조 기반)
2. README.md의 상태 주장 인용

최종 보고는 레포별 섹션(## 레포명)의 마크다운 원문으로만 반환하라. 요약·평가·제안 금지.
```

- [ ] **Step 2: 표본 검증** — 보고된 라우트 2개를 `git -C ... show <기준ref>:<파일>`로 직접 확인. 불일치 시 신규 dispatch로 재조사

- [ ] **Step 3: 보고서 저장** — 헤더(기준 ref, 표본 검증 결과) + 원문을 `docs/superpowers/reports/2026-07-02-consistency-round2-facts-frontend.md`로 저장

- [ ] **Step 4: 커밋**

```bash
cd /d/workspace/dpa/documents
git add docs/superpowers/reports/2026-07-02-consistency-round2-facts-frontend.md
git commit -m "docs(consistency): 프런트엔드 구현 사실 수집(2차)"
```

---

### Task 5: Phase 2-③ — 인프라·공통 레포 사실 수집

**Files:**
- Create: `docs/superpowers/reports/2026-07-02-consistency-round2-facts-infra.md` (documents 레포)

**Interfaces:**
- Consumes: Task 1의 기준 ref
- Produces: Flyway 마이그레이션 전체 목록, gateway 라우트 표, gitops 앱 등록 목록, svc-template 표준 요약. Task 8이 소비

- [ ] **Step 1: 읽기 전용 탐색 에이전트 dispatch**

지시문 (`<기준ref표>`는 devpath-shared, devpath-gateway, devpath-gitops, devpath-svc-template 행):

```text
[Scope Lock] 이 조사 Task만 수행하라. 끝나면 결과를 보고하고 정지하라. 다른 Task로 진행하지 말라.
어떤 파일도 수정·생성·삭제하지 말라(완전 읽기 전용). git fetch/checkout/switch도 금지한다(이미 완료됨).
명세가 부족하거나 대상이 존재하지 않으면 추측하지 말고 "NEEDS_CONTEXT: <무엇이 부족한지>"로 보고하라.

조사 대상: D:\workspace\dpa 아래 4개 레포 — devpath-shared, devpath-gateway, devpath-gitops, devpath-svc-template.
점검 기준은 아래 ref다. 워킹트리를 읽지 말고 기준 ref 트리만 읽어라:
<기준ref표>

devpath-shared:
1. Flyway 마이그레이션 전체 목록: git -C <경로> ls-tree -r --name-only <기준ref> -- src/main/resources/db/migration
2. 각 마이그레이션의 CREATE TABLE 대상: git -C <경로> grep -nE "CREATE TABLE|CREATE EXTENSION" <기준ref> -- "*.sql"
   → | 파일 | 테이블/확장 | 표

devpath-gateway:
3. 라우트 설정: git -C <경로> grep -nE "predicates|uri:|Path=" <기준ref> -- "src/main/resources" 및 라우트 정의 Java가 있으면 함께
   → | 라우트 경로 패턴 | 대상 서비스 | 정의 파일 | 표

devpath-gitops:
4. 등록된 앱 목록: git -C <경로> ls-tree -r --name-only <기준ref> 중 Application 매니페스트 경로와 각 매니페스트의 서비스명

devpath-svc-template:
5. 템플릿 구조 1~2단계 디렉터리와 README의 표준 규정(상태 주장 포함) 인용

최종 보고는 레포별 섹션(## 레포명)의 마크다운 원문으로만 반환하라. 요약·평가·제안 금지.
```

- [ ] **Step 2: 표본 검증** — 마이그레이션 1개 파일의 CREATE TABLE과 gateway 라우트 1개를 직접 `git show`로 확인. 불일치 시 신규 dispatch

- [ ] **Step 3: 보고서 저장** — `docs/superpowers/reports/2026-07-02-consistency-round2-facts-infra.md`

- [ ] **Step 4: 커밋**

```bash
cd /d/workspace/dpa/documents
git add docs/superpowers/reports/2026-07-02-consistency-round2-facts-infra.md
git commit -m "docs(consistency): 인프라·공통 레포 구현 사실 수집(2차)"
```

---

### Task 6: Phase 2-④ — documents 41개 문서 주장 추출 (에이전트 2개 분할)

**Files:**
- Create: `docs/superpowers/reports/2026-07-02-consistency-round2-claims-documents.md` (documents 레포)

**Interfaces:**
- Consumes: Task 1의 documents 기준 ref
- Produces: 문서별 "검증 가능한 주장" 표 (문서 | 주장 원문 | 유형 | 검증 대상 레포). Task 8의 좌변 입력

- [ ] **Step 1: 에이전트 2개 병렬 dispatch (04a: 01~20번, 04b: 21~41번 + README/Home)**

공통 지시문 (조사 파일 목록만 다름 — 04a는 `01_*.md`~`20_*.md`, 04b는 `21_*.md`~`41_*.md`와 `README.md`, `Home.md`):

```text
[Scope Lock] 이 조사 Task만 수행하라. 끝나면 결과를 보고하고 정지하라. 다른 Task로 진행하지 말라.
어떤 파일도 수정·생성·삭제하지 말라(완전 읽기 전용). git fetch/checkout/switch도 금지한다(이미 완료됨).
명세가 부족하거나 대상이 존재하지 않으면 추측하지 말고 "NEEDS_CONTEXT: <무엇이 부족한지>"로 보고하라.

조사 대상: D:\workspace\dpa\documents 레포의 <파일 목록> (점검 기준: <documents 기준ref>).
워킹트리가 아닌 기준 ref로 읽어라: git -C /d/workspace/dpa/documents show <기준ref>:<파일명>
파일명 확인: git -C /d/workspace/dpa/documents ls-tree --name-only <기준ref>

각 문서에서 "코드와 대조해 검증 가능한 주장"을 추출하라. 유형:
- STATUS: 구현 완료/부분/미구현/진행 상태 주장
- API: 특정 엔드포인트(메서드+경로) 존재 주장
- SCHEMA: 테이블·컬럼·마이그레이션 존재 주장
- STACK: 기술 스택 주장(예: Ollama/Claude, PostgreSQL, Flutter, 특정 라이브러리)
- LABEL: TARGET/HISTORY/PROTOTYPE 등 상태 배너의 존재 여부(문서 상단 배너가 있으면 그 내용, 없으면 "배너 없음")

출력: 문서별 섹션(## 파일명) 아래 표
| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
주장이 없는 문서는 "검증 가능한 주장 없음" 1줄. 41개 문서 전부 섹션이 있어야 한다(누락 금지).
요약·평가·제안 금지. 마크다운 원문만 반환하라.
```

- [ ] **Step 2: 표본 검증** — 04a·04b 보고에서 각각 문서 1개씩 골라 원문을 `git show`로 열어 주장 인용이 실제 존재하는지 확인. 또한 섹션 수 합계 = 43(문서 41 + README + Home) 확인. 미달이면 누락 문서를 지목해 신규 dispatch

- [ ] **Step 3: 병합 저장** — 04a + 04b 보고를 순서대로 이어붙이고 헤더(기준 ref, 표본 검증 결과)를 달아 `docs/superpowers/reports/2026-07-02-consistency-round2-claims-documents.md`로 저장

- [ ] **Step 4: 커밋**

```bash
cd /d/workspace/dpa/documents
git add docs/superpowers/reports/2026-07-02-consistency-round2-claims-documents.md
git commit -m "docs(consistency): documents 41개 문서 주장 추출(2차)"
```

---

### Task 7: Phase 2-⑤ — 보조 자산 사실 수집

**Files:**
- Create: `docs/superpowers/reports/2026-07-02-consistency-round2-facts-aux.md` (documents 레포)

**Interfaces:**
- Consumes: Task 1의 기준 ref (git 레포가 아닌 디렉터리는 워킹트리 그대로 읽음 — baseline 4절 참조)
- Produces: storyboard/prototype/workflow-guide/workflow-dashboard/templates의 상태 표기·스택 언급·stale 후보 표. Task 8이 소비

- [ ] **Step 1: 읽기 전용 탐색 에이전트 dispatch**

지시문:

```text
[Scope Lock] 이 조사 Task만 수행하라. 끝나면 결과를 보고하고 정지하라. 다른 Task로 진행하지 말라.
어떤 파일도 수정·생성·삭제하지 말라(완전 읽기 전용). git fetch/checkout/switch도 금지한다(이미 완료됨).
명세가 부족하거나 대상이 존재하지 않으면 추측하지 말고 "NEEDS_CONTEXT: <무엇이 부족한지>"로 보고하라.

조사 대상: D:\workspace\dpa 아래 5개 디렉터리 — storyboard, prototype, workflow-guide, workflow-dashboard, templates.
git 레포인 것은 아래 기준 ref 트리로 읽고, git 레포가 아닌 것은 워킹트리를 그대로 읽어라:
<기준ref표 + 비git 목록>
제외: node_modules/, build/, .gstack/, *.zip, *.pdf

각 디렉터리에서 수집:
1. 구현/진행 상태를 주장하는 문구 인용 (README, 문서, 설정): | 파일 | 주장 원문 | 표
2. 기술 스택 언급 중 구식 후보: MySQL, React/Vite(frontend 문맥), Claude 전용, VECTOR(1536) 등
   검색 예: git grep -niE "mysql|react|vite|claude" <기준ref> -- "*.md" (비git이면 rg -niE ... --glob "*.md")
3. workflow-dashboard: 어떤 데이터 소스(문서/일정)를 파싱하는지 — skills/, scripts/parsers/ 아래 설정·파서가 참조하는 원본 문서 경로
4. workflow-guide: guides.config.json이 빌드 대상으로 삼는 documents 파일 목록

최종 보고는 디렉터리별 섹션(## 이름)의 마크다운 원문으로만 반환하라. 요약·평가·제안 금지.
```

- [ ] **Step 2: 표본 검증** — 보고된 구식 스택 언급 2건을 직접 확인. 불일치 시 신규 dispatch

- [ ] **Step 3: 보고서 저장** — `docs/superpowers/reports/2026-07-02-consistency-round2-facts-aux.md`

- [ ] **Step 4: 커밋**

```bash
cd /d/workspace/dpa/documents
git add docs/superpowers/reports/2026-07-02-consistency-round2-facts-aux.md
git commit -m "docs(consistency): 보조 자산 사실 수집(2차)"
```

> **병렬 실행 메모:** Task 3~7은 상호 독립이다. subagent-driven 실행 시 dispatch를 동시에 던져도 되지만, 컨트롤러의 표본 검증·저장·커밋은 태스크별로 순차 수행한다(같은 documents 브랜치에 커밋하므로).

---

### Task 8: Phase 3 — 교차 대조·불일치 목록 (컨트롤러 직접)

**Files:**
- Create: `docs/superpowers/reports/2026-07-02-consistency-round2-mismatch-list.md` (documents 레포)
- 참조: Task 2~7의 reports 5+1개

**Interfaces:**
- Consumes: claims-documents.md(주장 좌변) × facts-backend/frontend/infra/aux.md(사실 우변) + regression-check.md(❌/⚠️ 항목)
- Produces: 불일치 목록 표 — Task 9·10이 이 표를 42번 4절과 43번 항목표의 원천으로 사용

- [ ] **Step 1: 주장 × 사실 대조**

**서브에이전트에 위임하지 않는다.** 컨트롤러가 claims-documents.md의 각 주장(유형 STATUS/API/SCHEMA/STACK/LABEL)을 해당 facts 파일과 대조한다. facts에 없는 사실이 필요하면 직접 `git show`/`git grep`으로 확인하고 그 명령을 근거에 남긴다.

- [ ] **Step 2: 불일치 목록 작성**

`docs/superpowers/reports/2026-07-02-consistency-round2-mismatch-list.md`:

```markdown
# 정합성 점검 2차 — 불일치 목록

| # | 문서 | 문서의 주장 | 코드 사실 | 근거(파일 경로/명령) | 처리 후보 |
|---|---|---|---|---|---|
| M-1 | ... | ... | ... | ... | P0/P1/P2/관찰 |

## 회귀 항목 (38번 미이행·부분 — regression-check에서 승계)
| # | 38번 항목 | 현재 상태 | 처리 후보 |

## 관찰 사항 (코드 문제 — 43번에 넣지 않음)
| # | 레포 | 관찰 내용 | 근거 |
```

처리 후보 기준: P0 = 소비자가 먼저 보는 파일(일정표·README·색인)의 현황 왜곡, P1 = 오해 방지 라벨/배너 필요, P2 = 과거 스택·계획 잔존 정리, 관찰 = 코드 측 문제(43번 제외).

- [ ] **Step 3: 검증**

- 모든 행의 "근거" 열이 채워져 있는지 확인 (빈 근거 = 미완료)
- STATUS/API/SCHEMA 유형 불일치 중 3건을 무작위로 골라 근거 명령을 직접 재실행해 재현되는지 확인

- [ ] **Step 4: 커밋**

```bash
cd /d/workspace/dpa/documents
git add docs/superpowers/reports/2026-07-02-consistency-round2-mismatch-list.md
git commit -m "docs(consistency): 문서-코드 불일치 목록(2차)"
```

---

### Task 9: Phase 4 — 42번 점검 보고서 작성

**Files:**
- Create: `42_전체_정합성_점검_2차.md` (documents 레포 루트)
- 참조: Task 1~8의 reports 전부

**Interfaces:**
- Consumes: baseline, regression-check, facts-*, claims-documents, mismatch-list
- Produces: `42_전체_정합성_점검_2차.md` — Task 10이 3·4절(회귀·불일치)을 참조하고, Task 11이 색인에 링크한다

- [ ] **Step 1: 42번 작성**

37번 형식을 계승해 아래 구조로 작성한다. 각 절의 내용은 해당 report 파일에서 옮기되, 요약 표 + report 파일로의 상대 링크(`./docs/superpowers/reports/...`)를 남긴다:

```markdown
# 42. 전체 정합성 점검 2차

> **작성일**: 2026-07-02
> **범위**: D:\workspace\dpa 전체 (37번과 동일 범위, origin/develop 기준)
> **선행**: [37_전체_문서_전체_레포_정합성_점검](./37_전체_문서_전체_레포_정합성_점검.md), [38_정합성_수정계획서](./38_정합성_수정계획서.md)
> **후속 실행 계획**: [43_정합성_리팩토링_실행계획서](./43_정합성_리팩토링_실행계획서.md)

## 1. 결론
(37번 1절 스타일: 전체 판정 + 큰 그림 5~7줄. mismatch-list 작성 후에만 쓸 수 있다)

## 2. 점검 기준과 범위
(baseline 요약: 레포별 기준 ref/SHA 표, 진행 중 브랜치 표, 제외 대상)

## 3. 38번 수정계획 이행 현황 (회귀 체크)
(regression-check의 23항목 판정 표 전체 + 미이행 요약)

## 4. 현재 구현 사실
### 4.1 백엔드 API 표면 (facts-backend 요약: 레포별 엔드포인트 수 + 대표 경로, 상세는 링크)
### 4.2 스키마·게이트웨이·GitOps (facts-infra 요약)
### 4.3 프런트엔드 (facts-frontend 요약)
### 4.4 보조 자산 (facts-aux 요약)

## 5. 문서-코드 불일치 목록
(mismatch-list의 본표 전체 전재)

## 6. 관찰 사항 (코드 측 — 수정계획 제외)
(mismatch-list의 관찰 표 전재)

## 7. 점검 방법 기록
(사용한 명령 패턴, 에이전트 분할, 표본 검증 방식 — 재현 가능하게)
```

- [ ] **Step 2: 정합성 검증 (이 레포의 "테스트")**

- 상대 링크 전수 확인: 42번 안의 모든 `](./` 링크 대상 파일이 존재하는지 확인
  ```bash
  cd /d/workspace/dpa/documents
  grep -oE '\]\(\./[^)]+\)' 42_전체_정합성_점검_2차.md | sed 's/](\.\///;s/)//' | while read f; do [ -e "$f" ] || echo "BROKEN: $f"; done
  ```
  기대: BROKEN 출력 없음 (43번은 Task 10에서 생기므로 이 시점엔 BROKEN 1건 — Task 10 후 재확인)
- 5절 불일치 행 수 = mismatch-list 본표 행 수와 일치 확인

- [ ] **Step 3: 커밋**

```bash
cd /d/workspace/dpa/documents
git add 42_전체_정합성_점검_2차.md
git commit -m "docs(consistency): 42번 전체 정합성 점검 2차 보고서"
```

---

### Task 10: Phase 4 — 43번 리팩토링 실행계획서 작성

**Files:**
- Create: `43_정합성_리팩토링_실행계획서.md` (documents 레포 루트)
- 참조: `42_전체_정합성_점검_2차.md`, mismatch-list

**Interfaces:**
- Consumes: 42번 3절(회귀 미이행)·5절(불일치 목록)
- Produces: `43_정합성_리팩토링_실행계획서.md` — 이후 별도 세션들이 이 계획의 P0/P1/P2를 실행한다

- [ ] **Step 1: 43번 작성**

38번 형식 계승:

```markdown
# 43. 정합성 리팩토링 실행계획서

> **작성일**: 2026-07-02
> **기준 문서**: [42_전체_정합성_점검_2차](./42_전체_정합성_점검_2차.md)
> **목적**: 42번 점검 결과를 우선순위별 실행 계획으로 재구성한다. 코드가 진실이며, 이 계획은 문서 수정 항목만 담는다.

## 1. 수정 원칙
(38번 3원칙 유지: ① 현재 구현/목표 설계 분리(TARGET·HISTORY·PROTOTYPE 라벨) ② 완료 과장 금지 ③ 소비자가 먼저 보는 파일부터)

## 2. P0 — 즉시 수정
| 항목 | 파일 | 수정 내용 | 완료 기준 |
(42번 5절에서 처리 후보 P0인 항목 + 3절 미이행 중 P0 성격)

## 3. P1 — 오해 방지 라벨 수정
(동일 형식)

## 4. P2 — 과거 정리
(동일 형식)

## 5. 색인 업데이트
| 항목 | 파일 | 수정 내용 |
(README.md·Home.md에 42·43 링크 — Task 11이 즉시 수행하는 항목도 명기)

## 6. 제외 항목 (조치 불필요 판정)
| 42번 불일치 # | 사유 |
(불일치지만 수정하지 않기로 판정한 항목과 근거)

## 7. 실행 규칙
- 각 항목은 documents(또는 해당 레포)의 docs/* 브랜치에서 수행, develop 대상 PR
- 완료 기준은 항목별 열에 명시된 검증으로 판정
```

**완전성 규칙**: 42번 5절의 모든 불일치 항목(M-*)과 3절의 모든 ❌/⚠️ 항목은 43번의 P0/P1/P2 항목 **또는** 6절 제외 표 중 정확히 한 곳에 나타나야 한다.

- [ ] **Step 2: 정합성 검증**

- 완전성 확인: 42번 5절의 M-# 목록과 43번(2~4절 + 6절)의 M-# 참조를 대조해 누락·중복 없음 확인
- 각 항목의 "완료 기준"이 검증 가능한 서술(파일에서 확인할 문구/구조)인지 훑기 — "적절히 수정" 같은 모호 서술 금지
- Task 9 Step 2에서 남았던 43번 링크 BROKEN 재확인:
  ```bash
  cd /d/workspace/dpa/documents
  grep -oE '\]\(\./[^)]+\)' 42_전체_정합성_점검_2차.md 43_정합성_리팩토링_실행계획서.md | sed 's/^[^(]*(\.\///;s/)//' | sort -u | while read f; do [ -e "$f" ] || echo "BROKEN: $f"; done
  ```
  기대: BROKEN 출력 없음

- [ ] **Step 3: 커밋**

```bash
cd /d/workspace/dpa/documents
git add 43_정합성_리팩토링_실행계획서.md
git commit -m "docs(consistency): 43번 정합성 리팩토링 실행계획서"
```

---

### Task 11: 색인 갱신 (README.md, Home.md)

**Files:**
- Modify: `README.md`, `Home.md` (documents 레포 루트)

**Interfaces:**
- Consumes: 42·43번 파일명
- Produces: 색인에서 42·43 접근 가능 — PR 리뷰어·workflow-guide 빌드가 소비

- [ ] **Step 1: 두 파일의 문서 목록 절에 42·43 항목 추가**

기존 37·38·39~41 항목이 나열된 위치와 형식을 그대로 따라 두 줄 추가한다 (기존 형식 먼저 확인: `grep -n "41_" README.md Home.md`):

```markdown
- [42. 전체 정합성 점검 2차](./42_전체_정합성_점검_2차.md) — 2026-07-02 기준 origin/develop 대비 전수 점검
- [43. 정합성 리팩토링 실행계획서](./43_정합성_리팩토링_실행계획서.md) — 42번 결과의 P0/P1/P2 실행 계획
```

(Home.md의 링크 형식이 `[[...]]` 위키링크면 그 형식을 따른다 — 기존 41번 줄과 동일하게.)

- [ ] **Step 2: 검증**

```bash
cd /d/workspace/dpa/documents
grep -n "42_전체_정합성_점검_2차\|43_정합성_리팩토링_실행계획서" README.md Home.md
```

기대: 파일당 2건씩 총 4건. workflow-guide 영향 확인: Task 7 결과의 guides.config.json 대상 목록에 README/Home이 포함되면 42번에 그 사실 기록(파일명 변경이 아니므로 빌드 깨짐 없음 예상 — 확인만).

- [ ] **Step 3: 커밋**

```bash
cd /d/workspace/dpa/documents
git add README.md Home.md
git commit -m "docs(consistency): 색인에 42·43번 문서 등록"
```

---

### Task 12: 푸시·PR 생성·CI 확인

**Files:**
- 없음 (git/GitHub 작업)

**Interfaces:**
- Consumes: Task 1~11의 커밋들 (`docs/consistency-check-round2` 브랜치)
- Produces: develop 대상 PR (CI 녹색 확인 후 머지)

- [ ] **Step 1: 푸시**

```bash
cd /d/workspace/dpa/documents
git push -u origin docs/consistency-check-round2
```

- [ ] **Step 2: PR 생성 (base: develop)**

```bash
cd /d/workspace/dpa/documents
gh pr create --base develop --title "docs: 전체 정합성 점검 2차(42) + 리팩토링 실행계획(43)" --body "## 개요
2026-06-19 37·38번 이후 2주 변경분(슬라이스 7~9, 알림 이관, 평판/남용방지)을 반영한 2차 전수 정합성 점검과 후속 실행계획.

## 산출물
- 42_전체_정합성_점검_2차.md — origin/develop 기준 전수 점검, 38번 회귀 체크 포함
- 43_정합성_리팩토링_실행계획서.md — P0/P1/P2 문서 수정 계획 (코드가 진실, 코드 수정 없음)
- docs/superpowers/ — 설계서·구현계획·수집 근거 reports
- README/Home 색인 갱신

## 검증
- 38번 23항목 회귀 판정 완료, 모든 불일치 항목에 근거 명령/경로 첨부
- 42↔43 완전성 대조(불일치 항목 전건이 계획 또는 제외 표에 매핑)
- 상대 링크 전수 확인

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

- [ ] **Step 3: CI 확인 후 머지**

```bash
cd /d/workspace/dpa/documents
gh pr checks --watch
```

기대: 전부 pass. **녹색이 아니면 머지하지 않고** 실패 원인을 조사해 수정 커밋 후 재확인. 녹색이면:

```bash
gh pr merge --merge
gh pr view --json state,mergedAt   # 머지 상태 직접 재확인 (완료 보고 신뢰 금지)
```

- [ ] **Step 4: 최종 보고**

PR URL, 머지 여부, 42번의 결론 요약(불일치 건수, P0/P1/P2 건수)을 사용자에게 보고하고 종료. 43번 계획의 실행(실제 문서 수정)은 **이 계획의 범위 밖** — 별도 세션에서 착수한다.
