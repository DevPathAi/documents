# 정합성 점검 2차 — 보조 자산 사실 수집

> 수집일: 2026-07-02 / 기준: storyboard·prototype·workflow-guide·templates origin/main, workflow-dashboard origin/develop
> 수집: 읽기 전용 조사 에이전트 / 컨트롤러 표본 검증 통과 — workflow-dashboard의 MySQL 언급이 done=true 이관 기록임을 직접 확인, workflow-guide guides.config.json 6개 문서 매핑 직접 확인(Task 2 발견과 일치)

# T7 Facts — DevPathAi 5개 레포 조사 (읽기 전용, 기준 ref)

조사 기준:

| 레포 | ref | commit |
|---|---|---|
| storyboard | origin/main | 94fd94a5 |
| prototype | origin/main | f084364 |
| workflow-guide | origin/main | 87f3999 |
| workflow-dashboard | origin/develop | bb0c0c8 |
| templates | origin/main | 687a178 |

---

## storyboard

파일 구성(node_modules/build/.gstack/*.zip/*.pdf 제외): `.github/workflows/pages.yml`, `CLAUDE.md`, `README.md`, `storyboard.html`

### 1. 구현/진행 상태 주장 문구

| 파일 | 주장 원문 |
|---|---|
| README.md | "`storyboard.html` 파일을 브라우저에서 열면 바로 동작합니다. 빌드나 서버가 필요 없습니다." |
| README.md | "`main` 브랜치에 push하면 GitHub Actions가 `storyboard.html`을 `index.html`로 복사해 GitHub Pages에 배포합니다." 배포 대상: `https://devpathai.github.io/storyboard/` |
| README.md | "핵심 LCS 학습 루프는 인터랙티브로, 나머지 화면은 개발 핸드오프용 정적 목업으로 구성" |
| README.md | 수록 화면 표 — `SCR-W-ONB-*`(온보딩), `SCR-W-PATH-*`(학습경로), `SCR-W-CNT-*`/`SCR-W-SBX-*`(콘텐츠/실습), `SCR-W-REV-*`/`SCR-W-MEN-*`(AI 리뷰/멘토), `SCR-W-COM-*`(커뮤니티), `SCR-W-DASH-*`/`SCR-M-NTF-*`(대시보드/알림), `SCR-A-*`(관리자) |
| CLAUDE.md | "단일 HTML 인터랙티브 화면 스토리보드 (역할별 약 30종)" |

### 2. 기술 스택 언급 중 구식 후보

grep 결과(`mysql|react|vite|claude|vector\(1536\)|pgvector`, *.md/*.json/*.mts/*.mjs): CLAUDE.md 제목 줄의 "CLAUDE.md" 표기 외 매치 없음. MySQL/React/Vite/pgvector 관련 언급 없음.

### 3. (workflow-dashboard 전용 항목 — 해당 없음)

### 4. (workflow-guide 전용 항목 — 해당 없음)

---

## prototype

파일 구성: Flutter 프로젝트. `CLAUDE.md`, `README.md`, `lib/main.dart`, `lib/learning_loop/{fixtures,models,reducer,selectors,view}.dart`, `lib/theme/prototype_theme.dart`, `lib/widgets/prototype_components.dart`, `test/**`, `tool/check_feature_coverage.dart`, `tool/check_web_size.dart`, `web/index.html`, `docs/20260618-lcs-first-ceo-plan.md` 외 docs/*, `pubspec.yaml`, `.github/workflows/pages.yml`

### 1. 구현/진행 상태 주장 문구

| 파일 | 주장 원문 |
|---|---|
| README.md | "이 레포는 심사위원, 멘토, 초기 사용자, 협업자가 DevPath AI의 핵심 경험을 빠르게 이해하도록 돕는 공개 페이지입니다." |
| README.md | "이번 프로토타입은 실제 백엔드 API를 호출하지 않습니다. 공개 페이지에서 안정적으로 보여줄 수 있도록 모든 데이터는 정적 샘플로 구성합니다." |
| README.md | "**구성 검증**: 현재 구조를 순수 MSA가 아니라 폴리레포 서비스 + 중앙 PostgreSQL/Flyway 스키마를 쓰는 `분산형 모듈러 모놀리스`로 설명합니다." |
| README.md | "**AI 검색 페이지**: 검색 의도와 pgvector 포함 여부를 바꾸며 키워드/임베딩 혼합 추천 결과와 추천 근거를 비교합니다." |
| README.md | 배포 대상: `https://devpathai.github.io/prototype/` (`main` push 시 `.github/workflows/pages.yml` 실행) |
| CLAUDE.md | "핵심 플로우(두 Aha Moment) 검증용 공개 Flutter Web 프로토타입" |
| CLAUDE.md | "검증 대상: ① GitHub 활동 + 진단 기반 개인화 학습 경로 ② Sandbox 실습 후 AI 코드 리뷰" |

### 2. 기술 스택 언급 중 구식 후보

grep 결과: MySQL/React/Vite 언급 없음. "claude"는 CLAUDE.md 제목·"Claude API 키" 비밀값 언급뿐(구식 스택 주장 아님). pgvector는 README.md에 "검색 의도와 pgvector 포함 여부를 바꾸며..." — 현재 스택으로서 언급(구식 후보 아님, VECTOR(1536) 명시 없음).

---

## workflow-guide

파일 구성: `.github/workflows/deploy.yml`, `CLAUDE.md`, `README.md`, `docs/.vitepress/config.mts`, `docs/index.md`, `guides.config.json`, `package.json`, `package-lock.json`, `scripts/prepare-docs.mjs`

### 1. 구현/진행 상태 주장 문구

| 파일 | 주장 원문 |
|---|---|
| README.md | "[DevPathAi/documents]의 워크플로우 가이드 문서를 모아 **VitePress** 정적 사이트로 배포하는 레포입니다." Live site: `https://devpathai.github.io/workflow-guide/` |
| README.md | "`main` 푸시 / 평일 자동 스케줄 / 수동 실행 시 GitHub Actions가: 1) 이 레포와 `DevPathAi/documents`를 체크아웃 2) `scripts/prepare-docs.mjs`가 `guides.config.json`의 문서를 `docs/<slug>.md`로 복사 3) `vitepress build docs`로 빌드 4) `docs/.vitepress/dist`를 GitHub Pages로 배포" |
| README.md | "가이드 내용 수정은 `documents` 레포에서 합니다. 이 레포는 빌드 파이프라인만 관리합니다." |
| CLAUDE.md | "가이드 추가: `guides.config.json`에 `{ file, slug, title }` 추가 → `prepare-docs`가 누락 문서를 에러로 보고한다(검증)." |

### 2. 기술 스택 언급 중 구식 후보

grep 결과: MySQL 없음. React는 `package-lock.json`의 transitive dependency(`@docsearch/react`, VitePress 내부용 `@vitejs/plugin-vue` 경유)로만 존재 — 레포 자체 스택 주장이 아님, 실제 사용 프레임워크는 VitePress(Vue 기반)+Vite. "claude"는 CLAUDE.md 제목과 "비밀값(Claude API 키·OAuth·결제 키)은 절대 커밋하지 않는다" 문구뿐.

### 4. workflow-guide 빌드 대상 documents 파일 목록 (`guides.config.json`)

| file (documents 루트 기준) | slug | title |
|---|---|---|
| 09_Git_규칙_정의서.md | git-rules | Git 규칙 정의서 |
| 12_코드_리뷰_규칙.md | code-review | 코드 리뷰 규칙 |
| 11_테스트_전략서.md | test-strategy | 테스트 전략서 |
| 10_환경_설정_템플릿.md | env-setup | 환경 설정 템플릿 |
| 14_배포_가이드.md | deploy-guide | 배포 가이드 |
| 16_운영_메뉴얼.md | ops-manual | 운영 메뉴얼 |

`scripts/prepare-docs.mjs`: documents 경로 우선순위 = 커맨드 인자 > `DOCS_SRC` 환경변수 > `../documents`(기본값). 각 `file`을 읽어 `docs/<slug>.md`로 복사하고 frontmatter(`title`) 주입, 문서 내 상대링크는 등록된 slug면 사이트 내부 경로로, 미등록이면 `https://github.com/DevPathAi/documents/blob/main/<file>`로 재작성. 등록된 file이 documents에 없으면 경고 후 최종적으로 exit 1(빌드 실패).

---

## workflow-dashboard

파일 구성(node_modules 등 제외): React+TypeScript+Vite 프로젝트. `data/config.json`, `data/devpath-*.json`(9개 레포 데이터), `scripts/{parse-prd,parse-workflow,sync,validate-data,generate-sample-data,scaffold}.mjs`, `scripts/parsers/{done-guard,github-markdown,linear,notion,parse-workflow-md,index}.mjs` + fixtures, `skills/project-dashboard/**`, `src/**`(App.tsx, pages, components, hooks 등), `docs/design-audit-2026-06-13.md`, `docs/superpowers/**`(handoff, plans, specs)

### 1. 구현/진행 상태 주장 문구

| 파일 | 주장 원문 |
|---|---|
| README.md | "**DevPath AI** 팀의 워크플로우 진행 현황 대시보드입니다. GitHub Pages로 배포됩니다." |
| README.md | "이 레포는 [project-dashboard 스킬]로 생성·관리됩니다. 데이터 수정/동기화는 `/project-dashboard` 스킬 명령(`status`, `config`, `edit`, `sync`)을 사용하세요." |
| README.md | "프로젝트는 **단계 DONE·MD1~MD4 (모두의 창업 라운드 정렬, 2026-06~12)** 기준이며, 작업 단위는 **수직 슬라이스 #1~12**(repo별 Step)입니다." |
| README.md | 단계표 — DONE(~6.16, W1 인프라+프론트 목 프로토 기준선), MD1 1st Aha(~7.20, OAuth→진단→학습경로(Claude) p50<8분), MD2 2nd Aha+베타(~8.31, 콘텐츠→Sandbox→AI리뷰+결제+베타100명=8주 MVP), MD3 풀 골든패스+멀티플랫폼(~11월), MD4 v1.0 완성도(12월) |
| README.md | "현재 `data/`에는 [17_스케줄] 기반 **DONE 기준선 + MD1~MD4 수직 슬라이스** 작업이 9개 트랙에 시드되어 있습니다. DONE 기준선(W1 인프라·프론트 목 프로토)은 완료(`- [x]`)로 박제, 이후 슬라이스는 계획 상태이며 실제 진척은 각 서비스가 작업하며 `sync`로 갱신합니다." |
| README.md | "각 서비스 레포의 `docs/project-management/workflow/WORKFLOW_*.md`(SSoT)에서 진행 상황을 수집합니다... (과거 `docs/seed/`는 제거됨 — 원본은 각 서비스 레포)." |
| CLAUDE.md | "`project-dashboard` 스킬로 생성·관리." |
| docs/superpowers/plans/2026-06-16-dashboard-schedule-realign.md | "`documents/17_스케줄.md`가 주차(W1~W24)/마일스톤(M1~M6) 기준에서 **단계(MD1~MD4) + 수직 슬라이스 #1~12** 기준으로 전면 재작성됨. 대시보드(React)를 새 일정으로 전면 수정한다." |
| docs/superpowers/plans/2026-06-17-ssot-migration.md | "9개 서비스 레포 docs/project-management/workflow/로 WORKFLOW md 이관 완료에 따라 대시보드 docs/seed 제거. sync 무결성 검증(dry-run 카운트 9개 일치) 통과." |

### 2. 기술 스택 언급 중 구식 후보

- **MySQL**: `data/devpath-shared.json`의 task 항목 텍스트 `"MySQL→PostgreSQL(SSOT 5432 + pgvector 5433)"`, `"done": true`로 표시됨(완료된 마이그레이션 기록, 현재 스택 아님). 동일 문구가 `docs/superpowers/plans/2026-06-16-dashboard-schedule-realign.md:137`, `docs/superpowers/specs/2026-06-16-dashboard-schedule-realign-design.md:62`에도 등장(계획/설계 문서 맥락, "W1 인프라 — MySQL→PostgreSQL(SSOT 5432 + pgvector 5433)").
- **React**: 대시보드 자체의 **현재** 스택으로 명시 — README.md: "React 19 + TypeScript + Vite 8", `package.json`/`package-lock.json`에 `react ^19.2.6`, `vite ^8.0.12` 등. 또한 `data/devpath-frontend.json`의 task 항목 `"React→Flutter 전환, melos 모노레포(dp_core·dp_design + apps/web·admin·mobile)"`, `"done": true` — **devpath-frontend 레포는 React에서 Flutter로 전환 완료됨**(workflow-dashboard 자체와는 별개 레포 기록).
- **Vite**: 현재 스택(README.md, package.json — `vite ^8.0.12`, `@tailwindcss/vite ^4.3.0`). `scripts/parsers/linear.mjs:20` 주석 "The actual GraphQL query is executed by Claude Code."
- **Claude 전용 언급**: `data/devpath-ai-svc.json` — "Claude 경로 생성", "Claude API 클라이언트(Sonnet 4.6)", "Claude 코드 리뷰 프롬프트 + 골든 50 케이스"; `data/devpath-community-svc.json` — "AI 시드 답변 Worker(질문 즉시 Claude→community_ai_answers) + 유사 질문 탐지(pgvector 0.80)"; `data/devpath-gitops.json` — "Chaos(Claude·CDN·Sandbox 풀 고갈) + OWASP ZAP"; README.md 표 — "OAuth → 진단 → 학습경로(Claude) p50 < 8분".
- **pgvector**: `data/devpath-shared.json`(SSOT 5432 + pgvector 5433), `data/devpath-community-svc.json`(유사 질문 탐지 pgvector 0.80). VECTOR(1536) 명시적 언급은 grep 결과에 없음.
- **불일치 발견(스코프 내 관찰, 별도 판단 없이 사실만 기록)**: `scripts/parse-prd.mjs`의 `REPO_FR_PREFIXES` 매핑 키가 `synapse-platform-svc`, `synapse-engagement-svc`, `synapse-knowledge-svc`, `synapse-learning-svc`, `synapse-frontend`, `synapse-gitops`, `synapse-shared`(모두 `synapse-` 접두)이며, `scripts/parse-workflow.mjs`의 `trackAliasMap`/`skills/.../modules/sync.md`·`config.md`의 예시들도 `synapse-*`를 사용. 반면 `data/config.json`의 실제 `repos[].id`는 전부 `devpath-*`(devpath-shared, devpath-gateway, devpath-platform-svc, devpath-learning-svc, devpath-community-svc, devpath-ai-svc, devpath-sandbox-svc, devpath-frontend, devpath-gitops).

### 3. workflow-dashboard가 파싱하는 데이터 소스(원본 문서 경로)

- `data/config.json`의 `repos[].source`: 전부 `"type": "github-markdown"`, `"repo": "DevPathAi/<repo-id>"`, `"path": "docs/project-management"` (9개 레포: devpath-shared, devpath-gateway, devpath-platform-svc, devpath-learning-svc, devpath-community-svc, devpath-ai-svc, devpath-sandbox-svc, devpath-frontend, devpath-gitops).
- `scripts/parse-workflow.mjs`: `<docsDir>/workflow/WORKFLOW_<track>_<Week>.md` 및 `<docsDir>/task/TASK_<track>.md`를 파싱. README.md 기준 실제 SSoT 경로는 각 서비스 레포의 `docs/project-management/workflow/WORKFLOW_*.md`.
- `scripts/parse-prd.mjs`: `<docsDir>/prd/PRD_W<n>.md` 파일들을 파싱, FR-ID 접두사로 레포별 필터링.
- `scripts/sync.mjs` 로컬 실행 시 `DOCS_DIR=<서비스 레포>/docs/project-management npm run sync -- <repo-id>` 형태로 repo별 실행(README.md). 과거 `docs/seed/`는 제거됨(SSOT 이관 완료, ssot-migration 문서 근거).
- `skills/project-dashboard/modules/sync.md`: source type별 라우팅 — `github-markdown`(gh CLI로 tarball 받아 DOCS_DIR 지정), `notion`(notion-fetch MCP), `linear`(GraphQL API), `manual`(스킵, edit 명령으로만 편집).

---

## templates

파일 구성: `CLAUDE.md`, `README.md` 단 2개 파일만 존재(그 외 파일 없음).

### 1. 구현/진행 상태 주장 문구

| 파일 | 주장 원문 |
|---|---|
| README.md | "**DevPath AI** 프로젝트에서 공용으로 사용하는 템플릿 모음 레포지토리입니다." |
| README.md | "## 📂 구성 (예정)" — `docs/`(문서 템플릿), `github/`(Issue/PR/워크플로 템플릿), `config/`(환경 설정 템플릿) 표로 소개되나 **실제로는 해당 디렉터리/파일이 레포에 존재하지 않음**(트리 조회 결과 CLAUDE.md·README.md 외 없음). |
| CLAUDE.md | "DevPath AI 공용 템플릿 모음 (문서 · GitHub · 설정 템플릿)" |

### 2. 기술 스택 언급 중 구식 후보

grep 결과: MySQL/React/Vite/Claude(제목 외)/pgvector 언급 없음. CLAUDE.md 제목 줄의 "CLAUDE.md" 문자열만 매치.

### 3. (workflow-dashboard 전용 항목 — 해당 없음)

### 4. (workflow-guide 전용 항목 — 해당 없음)
