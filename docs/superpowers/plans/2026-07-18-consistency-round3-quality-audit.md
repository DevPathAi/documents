# 전체 정합성 점검 3차 + 품질 감사 + 안전 리팩토링 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 워크스페이스 전 레포의 코드↔문서 불일치·코드 규칙 위반·TDD 갭을 실측 기반으로 식별해 `46_전체_정합성_점검_3차.md`·`47_품질_리팩토링_실행계획서.md`를 산출하고, 47번의 P0/P1 Task를 안전·소형 리팩토링 PR로 실행한다.

**Architecture:** 3단계 순차 — Phase 1(축별 병렬 점검, 읽기 전용 서브에이전트가 reports 원자료 생산) → Phase 2(컨트롤러가 교차 종합해 46·47번 작성, documents PR) → Phase 3(47번 Task별 실행 PR). 점검 기준은 각 레포 `fetch` 후 `origin/develop` 고정 SHA이며 워킹트리는 기준이 아니다.

**Tech Stack:** git(실측: show/ls-tree/grep), PowerShell, 서브에이전트(Task/Agent), 각 svc = Spring Boot(Gradle)·frontend = Flutter, GitHub PR + CI(gh CLI).

**승인 스펙:** `docs/superpowers/specs/2026-07-18-consistency-round3-quality-audit-design.md`

## Global Constraints

- **기준 ref**: 모든 실측은 `git fetch origin` 후 `origin/develop`(부재 시 `origin/main`)의 **Task 1에서 고정한 SHA**로 수행. 워킹트리·로컬 브랜치를 근거로 쓰지 않는다.
- **읽기 명령**: `git -C <레포절대경로> show <ref>:<path>` / `ls-tree -r <ref> --name-only` / `grep -nE '<pattern>' <ref> -- '<glob>'`만 사용(점검 단계).
- **절대경로 강제**: 모든 git/파일 명령에 `D:\workspace\dpa\<repo>` 절대경로 또는 `git -C <절대경로>`를 사용한다. `cd` 후 상대경로 금지(에이전트 스레드는 호출 간 cwd 리셋).
- **SCOPE_LOCK(서브에이전트 프롬프트 공통 전문 — 각 dispatch 프롬프트 맨 앞에 그대로 붙일 것)**:
  ```text
  [SCOPE LOCK] 이 작업(아래 명세)만 수행하라. 끝나면 보고하고 정지하라. 다른 Task로 진행하지 말라.
  명세에 없는 작업을 추측·즉흥 구현하지 말라. 명세가 부족하면 멈추고 NEEDS_CONTEXT로 보고하라.
  이 작업은 읽기 전용 점검이다: 어떤 파일도 생성·수정·삭제하지 말고, git 상태를 바꾸는 명령
  (add/commit/checkout/branch/reset/push 등)을 실행하지 말라. 결과는 최종 텍스트로만 반환하라.
  모든 git/파일 명령에 절대경로 또는 git -C <레포 절대경로>를 사용하라. cd 후 상대경로 금지.
  근거 없는 판정 금지: 모든 불일치 주장에 (a)문서 파일경로+행 인용 (b)코드 근거(실행한 명령과 출력 요지)를 첨부하라.
  ```
- **문서 산출 브랜치**: documents 레포 `docs/consistency-round3-spec` 브랜치에 reports·46·47을 계속 쌓는다(스펙과 같은 브랜치, 최종 PR 1개).
- **커밋**: Conventional Commits. `main`·`develop` 직접 푸시 금지, PR + CI 녹색 후 merge commit.
- **서브에이전트 무신뢰**: 완료 보고를 신뢰하지 않는다. 각 보고서에서 표본 주장 2건을 골라 컨트롤러가 명령을 재실행해 대조하고, 인접 레포에 낯선 브랜치·커밋이 없는지 스팟체크한다. Windows에서 서브에이전트 resume은 신뢰하지 않는다 — resume 실패·응답 이상 시 신규 dispatch로 전환한다.
- **커밋 트레일러**: 컨트롤러가 실행하는 모든 커밋 메시지 말미에 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`를 붙인다(아래 커밋 예시들에는 지면상 생략).
- **보고서 공통 템플릿(모든 reports 파일은 이 5개 섹션 필수)**:
  ```markdown
  # <제목>
  ## 기준     ← 레포별 SHA(Task 1 표 인용)
  ## 방법     ← 실행한 명령 원문
  ## 실측     ← 결과 표/목록
  ## 불일치 후보 ← 각 건: 문서위치(파일:행) | 코드근거 | P0/P1/P2 후보 | 수정방향
  ## 관찰     ← 판정 보류·대형 구조 관찰
  ```
- **레포 목록(코드 축 12)**: devpath-platform-svc, devpath-learning-svc, devpath-community-svc, devpath-sandbox-svc, devpath-ai-svc, devpath-lcs-svc, devpath-notification-svc, devpath-gateway, devpath-frontend, devpath-shared, devpath-svc-template, devpath-gitops
- **fetch 전체 목록(기준표 대상 21)**: 위 12 + documents, prototype, storyboard, templates, workflow-dashboard, workflow-guide, .github, devpath-home-page, devpath-landing-page

---

## Phase 1 — 점검 (Task 1~6)

### Task 1: Baseline 고정 (fetch + SHA 표)

**Files:**
- Create: `D:\workspace\dpa\documents\docs\superpowers\reports\2026-07-18-consistency-round3-baseline.md`

**Interfaces:**
- Produces: 레포별 `기준 ref | SHA | 마지막 커밋일` 표 — Task 2~8 전부가 이 SHA를 인용한다.

- [ ] **Step 1: 전 레포 fetch + SHA 수집 (컨트롤러 직접 실행)**

```powershell
$all = @('devpath-platform-svc','devpath-learning-svc','devpath-community-svc','devpath-sandbox-svc','devpath-ai-svc','devpath-lcs-svc','devpath-notification-svc','devpath-gateway','devpath-frontend','devpath-shared','devpath-svc-template','devpath-gitops','documents','prototype','storyboard','templates','workflow-dashboard','workflow-guide','.github','devpath-home-page','devpath-landing-page')
foreach ($r in $all) {
  $p = "D:\workspace\dpa\$r"
  git -C $p fetch origin --quiet 2>$null
  $ref = 'origin/develop'
  git -C $p rev-parse --verify --quiet origin/develop *> $null
  if ($LASTEXITCODE -ne 0) { $ref = 'origin/main' }
  $sha = git -C $p rev-parse --short $ref
  $d = git -C $p log -1 --format='%ad' --date=short $ref
  Write-Output "$r | $ref | $sha | $d"
}
```

Expected: 21행 출력. `origin/develop` 부재 레포만 `origin/main`.

- [ ] **Step 2: baseline 보고서 작성** — 공통 템플릿 5섹션. `## 실측`에 위 표, `## 방법`에 위 스니펫 원문. 미머지 원격 feature 브랜치 목록(`git -C <p> branch -r`)을 `## 관찰`에 42번 §2.2 형식으로 기록.
- [ ] **Step 3: 검증** — `Select-String -Path D:\workspace\dpa\documents\docs\superpowers\reports\2026-07-18-consistency-round3-baseline.md -Pattern '^## '` → 5개 섹션 확인. 표 행수 21 확인.
- [ ] **Step 4: Commit**

```powershell
git -C D:\workspace\dpa\documents add docs/superpowers/reports/2026-07-18-consistency-round3-baseline.md
git -C D:\workspace\dpa\documents commit -m "docs: 정합성 3차 — baseline SHA 고정"
```

### Task 2: 축① 전체 구조 점검

**Files:**
- Create: `D:\workspace\dpa\documents\docs\superpowers\reports\2026-07-18-consistency-round3-structure.md`

**Interfaces:**
- Consumes: baseline SHA 표
- Produces: 구조 불일치 후보 목록(46번 §구조 절 입력)

- [ ] **Step 1: 서브에이전트 1명 dispatch (읽기 전용)** — 프롬프트 = SCOPE_LOCK + 아래:

```text
[명세] 축① 전체 구조 점검. 기준 SHA는 다음 표를 그대로 사용하라: <Task 1 표 붙여넣기>
1. 03_아키텍처: git -C D:\workspace\dpa\documents show origin/develop:03_프로젝트_아키텍처_정의서.md 를 읽고,
   문서가 주장하는 서비스 목록·포트·라우팅·의존 방향을 추출하라.
2. gateway 실측: git -C D:\workspace\dpa\devpath-gateway ls-tree -r origin/develop --name-only 로 파일을 파악하고
   라우팅 설정 파일(application*.yml 등)을 git show로 읽어 실제 라우트(path→svc) 표를 만들어라.
3. svc 표면 실측: 7개 svc 각각 git -C D:\workspace\dpa\devpath-<x>-svc grep -nE '@(Get|Post|Put|Delete|Patch|Request)Mapping' origin/develop -- '*.java' 로 컨트롤러 매핑을 수집해 gateway 라우트와 대조하라.
4. gitops 실측: git -C D:\workspace\dpa\devpath-gitops ls-tree -r origin/develop --name-only 로 매니페스트 구성(앱 목록)을 추출해 svc 목록과 대조하라.
5. 산출: 공통 템플릿 5섹션(기준/방법/실측/불일치 후보/관찰)의 마크다운 본문을 최종 텍스트로 반환하라. 파일 쓰기 금지.
```

- [ ] **Step 2: 컨트롤러 검증** — 보고 내 표본 2건 재실행 대조(예: gateway 라우트 1건 `git show`, svc 매핑 1건 `git grep`). 불일치 시 해당 절 재점검 지시.
- [ ] **Step 3: 보고서 파일로 저장(컨트롤러가 Write)** 후 Commit

```powershell
git -C D:\workspace\dpa\documents add docs/superpowers/reports/2026-07-18-consistency-round3-structure.md
git -C D:\workspace\dpa\documents commit -m "docs: 정합성 3차 — 축1 구조 원자료"
```

### Task 3: 축② 코드/문서 정합성 점검 (중점)

**Files:**
- Create: `D:\workspace\dpa\documents\docs\superpowers\reports\2026-07-18-consistency-round3-api-surface.md`
- Create: `D:\workspace\dpa\documents\docs\superpowers\reports\2026-07-18-consistency-round3-doc-consistency.md`

**Interfaces:**
- Consumes: baseline SHA 표
- Produces: 엔드포인트/스키마 실측 인벤토리 + 문서별 불일치 후보(46번 §불일치 절의 주 입력)

- [ ] **Step 1: 서브에이전트 A — 코드 실측 인벤토리** — 프롬프트 = SCOPE_LOCK + :

```text
[명세] 코드 실측 인벤토리. 기준 SHA 표: <Task 1 표>
1. API 표면: 7개 svc 각각 git -C D:\workspace\dpa\devpath-<x>-svc grep -nE '@(Get|Post|Put|Delete|Patch|Request)Mapping' origin/develop -- '*.java'
   → svc별 메서드·경로 표. 총계를 42번 §1의 52개와 비교해 증감을 기록하라.
2. Flyway: 각 svc git grep 대신 git -C <svc> ls-tree -r origin/develop --name-only | 'db/migration' 필터
   → 파일명 전수 목록(네이밍 판정은 축③ 소관이므로 목록만).
3. 이벤트: 각 svc + devpath-shared에서 git grep -nE 'KafkaListener|topics? *=|TopicNames|EventType' origin/develop 로 토픽·이벤트 명 인벤토리.
4. shared 컨트랙트: git -C D:\workspace\dpa\devpath-shared ls-tree -r origin/main --name-only 로 모듈·패키지 목록(develop 부재 시 main).
5. frontend 화면: git -C D:\workspace\dpa\devpath-frontend ls-tree -r origin/develop --name-only 중 lib/ 하위 페이지·라우트 파일 목록과
   git grep -nE 'GoRoute|routes?:' origin/develop -- '*.dart' 로 라우트 표.
산출: 공통 템플릿 본문 반환(파일 쓰기 금지). 이 보고서의 '불일치 후보' 절은 비워두고 '실측'에 집중하라.
```

- [ ] **Step 2: 서브에이전트 B — 문서 대조** (A 결과를 프롬프트에 포함해 dispatch) — 프롬프트 = SCOPE_LOCK + :

```text
[명세] 문서 대조. 기준 SHA 표: <Task 1 표>. 코드 실측 인벤토리: <A의 실측 절 전체 붙여넣기>
대조 대상(각각 git -C D:\workspace\dpa\documents show origin/develop:<파일> 로 읽기):
02_ERD_문서.md / 04_API_명세서.md / 06_화면_기능_정의서.md / 17_스케줄.md / 20_커뮤니티_기능_설계서.md /
26_학습맥락_자동첨부_구현.md / 27_MVP_설계서.md / 44_MVP_잔여_로드맵.md / Home.md / README.md
+ 12개 코드 레포 각각의 README.md·CLAUDE.md (git -C <레포> show <기준ref>:README.md 등)
점검 관점:
(a) 문서가 "미구현·스켈레톤·예정"이라 하는데 실측에 존재 → 불일치(42번의 주종 패턴).
(b) 문서가 존재를 주장하는데 실측에 없음 → 불일치.
(c) 42번(7-02) 이후 머지 기능이 문서에 반영됐는지: 에러 envelope 표준화(5 svc)·Tier-2 웹 실API·마이페이지 P1~P4·
    설정/동의·Google OAuth·베타 게이팅(C1/C2a/C2b)·웹 이미지·결제 마스터 spec(구현 미착수가 정확한 표기).
(d) 04_API 명세의 엔드포인트 표 vs 실측 표면의 건별 대조(누락·초과·경로 상이).
산출: 공통 템플릿 본문 반환. 불일치 후보 각 건에 문서위치(파일:행)+코드근거+P후보+수정방향 필수.
```

- [ ] **Step 3: 컨트롤러 검증** — A 표본 2건(임의 svc 1개 매핑 재실행, Flyway 목록 1개), B 표본 2건(불일치 주장 중 2건의 문서 행·코드 근거 재확인).
- [ ] **Step 4: 두 보고서 저장 + Commit**

```powershell
git -C D:\workspace\dpa\documents add docs/superpowers/reports/2026-07-18-consistency-round3-api-surface.md docs/superpowers/reports/2026-07-18-consistency-round3-doc-consistency.md
git -C D:\workspace\dpa\documents commit -m "docs: 정합성 3차 — 축2 실측·문서대조 원자료"
```

### Task 4: 축③ 코드 규칙 점검

**Files:**
- Create: `D:\workspace\dpa\documents\docs\superpowers\reports\2026-07-18-consistency-round3-code-rules.md`

**Interfaces:**
- Consumes: baseline SHA 표, Task 3-A의 Flyway 목록
- Produces: 규칙 위반 목록(47번 chore Task들의 입력)

- [ ] **Step 1: 서브에이전트 1명 dispatch** — 프롬프트 = SCOPE_LOCK + :

```text
[명세] 축③ 코드 규칙 점검. 기준 SHA 표: <Task 1 표>. Flyway 파일 목록: <Task 3-A 발췌>
기준 문서(git -C D:\workspace\dpa\documents show origin/develop:<파일>): 09_Git_규칙_정의서.md / 10_환경_설정_템플릿.md / 12_코드_리뷰_규칙.md
1. 커밋 컨벤션: 12개 코드 레포 각각 git -C <레포> log <기준ref> --format='%s' -30 에서 Conventional Commits 위반(merge commit 제외) 건수·예시.
2. Flyway 네이밍: 목록을 규칙 V{date_seq}__{snake}.sql 과 대조, 위반 전수.
3. 에러 envelope: 각 svc git -C <svc> grep -nE 'ErrorResponse|ProblemDetail|error' <기준ref> -- '*Advice*.java' '*Handler*.java' 로
   핸들러 존재·shared 컨트랙트 사용 여부 확인(구현 상세 판정은 보류하고 사용/미사용/독자구현만 분류).
4. 시크릿: 각 레포 git -C <레포> grep -nEi '(password|secret|api[_-]?key|token) *[:=] *["'"'"'][^"'"'"'$\{]' <기준ref> -- '*.yml' '*.yaml' '*.properties' '*.env' 결과에서
   플레이스홀더(${...}·example·changeme)를 제외한 실값 의심 건.
5. 레포 위생: 각 레포 git -C <레포> ls-tree -r <기준ref> --name-only 에서 .omc/ 등 도구 상태·빌드 산출물의 추적 여부와
   git -C <레포> show <기준ref>:.gitignore 의 .omc/ 포함 여부를 표로.
산출: 공통 템플릿 본문 반환. 판정 불가 항목은 '관찰'로 분리.
```

- [ ] **Step 2: 컨트롤러 검증** — 표본 2건(커밋 컨벤션 1레포 재실행, 위생 표 1레포 재확인). 시크릿 의심 건은 **전건** 직접 재확인.
- [ ] **Step 3: 저장 + Commit** (`docs: 정합성 3차 — 축3 코드규칙 원자료`)

### Task 5: 축④ TDD 적합성 점검

**Files:**
- Create: `D:\workspace\dpa\documents\docs\superpowers\reports\2026-07-18-consistency-round3-tdd-gaps.md`

**Interfaces:**
- Consumes: baseline SHA 표
- Produces: 레포별 테스트 갭 표 + 우선순위 후보(47번 test Task들의 입력)

- [ ] **Step 1: 서브에이전트 2명 병렬 dispatch** — 백엔드 담당/프론트 담당. 백엔드 프롬프트 = SCOPE_LOCK + :

```text
[명세] 축④ TDD 갭 점검 — 백엔드(7 svc + shared + svc-template + gateway). 기준 SHA 표: <Task 1 표>
기준: git -C D:\workspace\dpa\documents show origin/develop:11_테스트_전략서.md (피라미드 Unit75/Int20/E2E5, jqwik 속성 기반, 불변식 목록 §2.1)
각 레포에 대해:
1. git -C <레포> ls-tree -r <기준ref> --name-only 로 src/main 클래스와 src/test 클래스 목록을 뽑아
   (a) *Service·도메인 클래스 중 대응 테스트 없는 것 (b) 테스트 총수 대비 @SpringBootTest 비중
   (git -C <레포> grep -ln '@SpringBootTest' <기준ref> -- '*.java' 건수 / 전체 테스트 파일 수) 를 표로.
2. 11번 §2.1 불변식(평판 일일 40점 상한·에스컬레이션 상태 전이·현상금 차감/환불·적응형 난이도·스트릭 TZ 등)별로
   대응 테스트 존재 여부: git -C <레포> grep -lnE '<불변식 키워드>' <기준ref> -- 'src/test' 로 확인.
3. jqwik 사용 여부: git -C <레포> grep -ln 'jqwik' <기준ref> 결과.
산출: 공통 템플릿 본문. '불일치 후보' 대신 '갭 후보'로: 갭 | 근거 | 위험도(P0/P1/P2 후보) | 보강 제안(테스트 클래스 경로 수준).
```

프론트 프롬프트 = SCOPE_LOCK + :

```text
[명세] 축④ TDD 갭 점검 — 프론트(devpath-frontend 단일 레포). 기준 SHA 표: <Task 1 표>
기준: git -C D:\workspace\dpa\documents show origin/develop:11_테스트_전략서.md (Flutter test 단위/위젯 계층)
1. git -C D:\workspace\dpa\devpath-frontend ls-tree -r origin/develop --name-only 로 lib/ 하위 기능 디렉토리(화면·서비스·클라이언트)와
   test/ 하위 테스트 파일 목록을 뽑아 기능→대응 테스트 유무 표를 만들어라.
2. 위젯/단위 테스트가 전무한 화면(페이지) 목록을 별도로 나열하라.
3. SSE·API 클라이언트 회귀 테스트: git -C D:\workspace\dpa\devpath-frontend grep -lnE 'SseClient|ApiClient' origin/develop -- 'test' 로
   존재를 확인하고, Tier-2 실계약 회귀 테스트(경로 생성·sandbox·mentor SSE)가 남아 있는지 확인하라.
산출: 공통 템플릿 본문. '불일치 후보' 대신 '갭 후보'로: 갭 | 근거 | 위험도(P0/P1/P2 후보) | 보강 제안(테스트 파일 경로 수준).
```

- [ ] **Step 2: 컨트롤러 검증** — 표본 2건(임의 svc 1개의 "테스트 부재" 주장 재확인, @SpringBootTest 비중 1개 재계산).
- [ ] **Step 3: 두 결과 병합 저장 + Commit** (`docs: 정합성 3차 — 축4 TDD 갭 원자료`)

### Task 6: 회귀 체크 (43번 이행 + 잔여 OPEN)

**Files:**
- Create: `D:\workspace\dpa\documents\docs\superpowers\reports\2026-07-18-consistency-round3-regression-check.md`

**Interfaces:**
- Consumes: baseline SHA 표
- Produces: 43번 항목별 ✅/⚠️/❌/➖ 표(46번 §3 입력)

- [ ] **Step 1: 컨트롤러 직접 수행(위임 없음)** — `git -C D:\workspace\dpa\documents show origin/develop:43_정합성_리팩토링_실행계획서.md`로 항목을 추출하고, 각 항목의 대상 파일을 기준 ref로 재확인해 42번 §3 형식 표 작성. 42번 잔여 ⚠️(P0-5 조직 프로필 웹 렌더링)과 OPEN 이력 PR 2건 상태 확인:

```powershell
gh pr view 18 --repo DevPathAi/devpath-sandbox-svc --json state,title
gh pr view 6 --repo DevPathAi/.github --json state,title
```

- [ ] **Step 2: 저장 + Commit** (`docs: 정합성 3차 — 회귀체크 원자료`)

---

## Phase 2 — 종합 문서·PR (Task 7~9)

### Task 7: 46_전체_정합성_점검_3차.md 작성

**Files:**
- Create: `D:\workspace\dpa\documents\46_전체_정합성_점검_3차.md`

**Interfaces:**
- Consumes: Task 1~6의 reports 6종
- Produces: P0/P1/P2 확정 불일치·갭 목록(47번의 유일한 입력)

- [ ] **Step 1: 컨트롤러가 직접 작성** — 42번 형식 계승: §1 결론 → §2 기준·범위(SHA 표 인용) → §3 43번 회귀체크 → §4 축① 구조 → §5 축② 불일치 목록(P0/P1/P2 확정) → §6 축③ 규칙 위반 → §7 축④ TDD 갭 → §8 코드 관찰(대형 구조 기록만) → §9 위생(.omc·documents 방치 3파일: `.tier1-baseline.md`은 내용 요약 후 처리안 제시). 모든 항목에 reports 원자료 링크.
- [ ] **Step 2: 교차 검증** — 46번의 P0 전건에 대해 원자료 근거 링크가 실재하는지 확인. 42번 대비 총계 문장(엔드포인트 수 등)이 Task 3-A 실측과 일치하는지 대조. **기준 SHA 신선도 재확인**(스펙 §5): 전 레포 `git fetch` 후 `git -C <레포> rev-parse --short <기준ref>`가 Task 1 표와 다르면 신규 머지분을 46번 §2에 주석으로 명기(점검 범위 밖임을 표시).
- [ ] **Step 3: Commit** (`docs: 46_전체_정합성_점검_3차 작성`)

### Task 8: 47_품질_리팩토링_실행계획서.md 작성

**Files:**
- Create: `D:\workspace\dpa\documents\47_품질_리팩토링_실행계획서.md`

**Interfaces:**
- Consumes: 46번 확정 목록
- Produces: Phase 3의 태스크 명세(레포·브랜치·파일 경로·수정 내용·검증 명령·완료 기준을 Task별 완전 명세 — 본 계획서의 태스크 형식과 동일 수준)

- [ ] **Step 1: 컨트롤러가 직접 작성** — 46번 각 항목을 Task로 변환. 필수 규칙:
  - Task마다: 대상 레포 / 분기 브랜치명(`docs|chore|refactor|test/*`) / 수정 파일 절대경로 / 변경 내용(문서면 교체 문안, 코드면 변경 코드) / 검증 명령(테스트·빌드) / PR 제목.
  - 코드 변경 Task는 **테스트 선행 단계 포함**(기존 테스트 없으면 현재 동작 고정 테스트부터). 대형 구조 변경은 Task화 금지(46번 §8에만).
  - P2는 "이월 가능" 표시. 43번처럼 P0→P1→P2 순 배열.
- [ ] **Step 2: 셀프 리뷰** — 46번 P0/P1 전 항목이 47번 Task로 존재하는지 1:1 대조표 작성(누락=계획 실패). placeholder 패턴(TBD·"적절히"·코드 없는 코드단계) 스캔.
- [ ] **Step 3: Commit** (`docs: 47_품질_리팩토링_실행계획서 작성`)

### Task 9: documents PR (스펙+플랜+reports+46+47)

- [ ] **Step 1: Home/색인 갱신** — `D:\workspace\dpa\documents\Home.md`(및 README의 문서 색인이 있으면 함께)에 46·47 링크 추가. 04·07 등 배너가 "현재 기준"으로 42번을 가리키면 46번으로 교체(42번 §1 말미 패턴). Commit(`docs: 색인·기준 배너 46번으로 갱신`).
- [ ] **Step 2: 푸시 + PR 생성**

```powershell
git -C D:\workspace\dpa\documents push -u origin docs/consistency-round3-spec
gh pr create --repo DevPathAi/documents --base develop --head docs/consistency-round3-spec --title "docs: 전체 정합성 점검 3차 + 품질 리팩토링 계획" --body "46/47 + 원자료 reports + 설계서/플랜. 스펙: docs/superpowers/specs/2026-07-18-consistency-round3-quality-audit-design.md"
```

- [ ] **Step 3: CI 녹색 확인 후 머지** — `gh pr checks <n> --repo DevPathAi/documents --watch` 성공 확인 → merge commit 머지 → `git -C D:\workspace\dpa\documents checkout develop && git -C D:\workspace\dpa\documents pull`. **사용자 리뷰 게이트**: 머지 전 46·47 요약을 사용자에게 보고하고 승인받는다(Phase 3 실행 범위 확정 게이트).

---

## Phase 3 — 실행 (Task 10 + 47번 Task들)

### Task 10: 레포 위생 — .omc 오염 정리 (사전 확정분, 47번과 독립)

**Files (레포별 반복):**
- Modify: `D:\workspace\dpa\<repo>\.gitignore` (`.omc/` 라인 추가 — 이미 있으면 skip)
- devpath-community-svc 한정: 추적 중인 `.omc/` 제거

**Interfaces:**
- Consumes: Task 4 위생 표(= 어느 레포가 .gitignore 누락/추적 중인지 확정 목록)
- Produces: 각 레포 chore PR

- [ ] **Step 1: 대상 확정** — Task 4 위생 표에서 (a) `.gitignore`에 `.omc/` 없는 레포 (b) `.omc/` 추적 중 레포 목록을 뽑는다(2026-07-18 워킹트리 관찰로는 (b)=devpath-community-svc, (a)는 Task 4가 확정).
- [ ] **Step 2: 레포별 실행(각각 독립 브랜치·PR)** — community-svc 예시(타 레포는 3번째 줄 생략):

```powershell
git -C D:\workspace\dpa\devpath-community-svc checkout develop
git -C D:\workspace\dpa\devpath-community-svc pull origin develop
git -C D:\workspace\dpa\devpath-community-svc checkout -b chore/omc-hygiene
git -C D:\workspace\dpa\devpath-community-svc rm -r --cached .omc
Add-Content -Path D:\workspace\dpa\devpath-community-svc\.gitignore -Value "`n.omc/"
git -C D:\workspace\dpa\devpath-community-svc add .gitignore
git -C D:\workspace\dpa\devpath-community-svc commit -m "chore: .omc 도구 상태 추적 제거 및 gitignore 등록"
git -C D:\workspace\dpa\devpath-community-svc push -u origin chore/omc-hygiene
gh pr create --repo DevPathAi/devpath-community-svc --base develop --head chore/omc-hygiene --title "chore: .omc 위생 정리" --body "정합성 3차(46번 §9) 위생 항목"
```

- [ ] **Step 3: 검증** — 각 PR diff에 `.omc` 외 변경이 없는지 `gh pr diff` 확인, CI 녹색 후 머지. 해당 레포 테스트가 CI에 없으면 로컬 `./gradlew test` 1회.
- [ ] **Step 4: documents 방치 3파일 처리** — 46번 §9의 처리안대로(기본: superpowers 산출물 2건은 documents에 `docs/*` 브랜치로 커밋·PR, `.tier1-baseline.md`은 46번 판단 따름).

### Task 11+: 47번 실행계획 Task별 실행

- [ ] **Step 1: 사용자 승인된 47번의 Task를 P0부터 순서대로 실행** — 각 Task는 47번 명세(레포·브랜치·파일·내용·검증)를 그대로 서브에이전트에 전달(SCOPE_LOCK + 쓰기 허용 변형: "명세된 파일 외 수정 금지, 명세된 커밋 1개만, push·PR 생성까지 수행 후 정지"). 코드 Task는 테스트 선행 단계부터.
- [ ] **Step 2: Task마다 컨트롤러 검증** — `git -C <레포> log` 커밋 범위 / `gh pr diff` 파일 목록 = 명세와 일치 / 테스트 로컬 재실행 / CI 녹색 → 머지. 인접 레포 스팟체크.
- [ ] **Step 3: 종결** — P0·P1 전부 머지 후 46번 §1에 "실행 완료(P2 이월 목록)" 추록 커밋·PR, 메모리 갱신.

---

## 완료 기준 (스펙 §1 성공 기준과 1:1)

- [ ] 46번이 42번 형식으로 작성·머지됨 (Task 7·9)
- [ ] 47번 P0·P1 Task 전부 PR 실행·머지, P2는 명시 이월 (Task 11+)
- [ ] 모든 코드 PR: 로컬 테스트 통과 + CI 녹색 후 머지 (Task 10·11+ Step)
- [ ] 리팩토링 동작 불변: 테스트 선행 확보 원칙 준수 (47번 Task 명세 규칙)
