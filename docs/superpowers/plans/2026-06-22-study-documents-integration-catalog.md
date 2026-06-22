# study-documents 상시 통합 카탈로그 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** study-documents의 스킬·코드·문서 자산을 dev-path-ai 개발 중 상시 활용하도록, ①Skillbook을 로컬 플러그인 마켓플레이스로 패키징하고 ②documents 레포에 참조 카탈로그 + 각 레포 CLAUDE.md 포인터를 구축한다.

**Architecture:** 2개 독립 레이어. 레이어1은 study-documents 레포 안에 `devpath-skillpack` 플러그인(적합 26 스킬 복사) + 루트 `.claude-plugin/marketplace.json`을 만들어 `/plugin install`로 활성화. 레이어2는 dev-path-ai의 documents 레포에 마스터 카탈로그 1본 + 각 devpath-* 레포 CLAUDE.md에 짧은 포인터. 정본은 study-documents/Skillbook, 플러그인 skills/는 빌드 산출물(스크립트로 재생성).

**Tech Stack:** Claude Code 플러그인/마켓플레이스(`.claude-plugin/`), Markdown, PowerShell/bash 빌드 스크립트, git(멀티레포).

## Global Constraints

- **추측 금지·검증 필수**: 모든 변경은 실제 파일/명령으로 확인 후 반영. "완료"는 검증 근거가 있을 때만(documents/CLAUDE.md 절대조건 1·5).
- **멀티레포 git-branch-flow**: 각 레포는 `develop`에서 작업 브랜치 분기 → develop PR. `main`·`develop` 직접 커밋 금지. study-documents도 동일.
- **복사 아닌 참조 원칙(코드·문서)**: Sample Codes·Dockerfile·가이드는 dev-path-ai 레포로 복사하지 않고 경로 참조만. (예외: 플러그인 skills/는 study-documents 레포 *내부* 복사 — 정본은 Skillbook, 빌드 산출물임을 명시)
- **적합 26 / 제외 6**: 포함 26 = spring-setup·flutter-setup·dockerfile-builder·docker-compose-infra·code-reviewer·complexity-analyzer·error-detective·test-coverage-booster·dart-flutter-lint-check·context-harness·harness-doctor·eval-builder·context7-helper·code-review-multiagent·semgrep-scanner·sonatype-checker·brooks-lint-arch·vercel-grep-helper·deepwiki-helper·flutter-pubdev-helper·postgres-mcp-tuner·domain-modeler·readme-generator·deep-interview·deep-init·sample-code-builder. 제외 = python-endpoint·db-migration·troubleshoot(llm-project-troubleshoot)·react-setup·msa-converter·super-nova. (skill-routing-eval은 스킬 아님 — 자동 제외)
- **dev-path-ai 실측 스택**: Spring Boot 4.0.7 GA · Java 21 · Gradle 9.5.1 · PostgreSQL · JPA · Redis · Kafka · OAuth2 RS / Flutter(Dart 3.12.1).
- **마켓플레이스 명명**: kebab-case, 예약어 회피. 마켓플레이스명 `devpath-study` · 플러그인명 `devpath-skillpack`.
- **플러그인 자족성**: 설치 시 디렉토리가 캐시로 복사됨 → 각 skills/<skill>는 자기 references/까지 포함해 자족적이어야 함(디렉토리 밖 참조 금지).
- **Scope Lock**: 서브에이전트 위임 시 단일 Task 명세만 구현, 추측·즉흥 금지, 완료 후 정지·보고. 컨트롤러가 직접 검증.

---

## File Structure

**study-documents 레포** (브랜치 `feat/devpath-skillpack-plugin`):
- `develop-study-documents/.claude-plugin/marketplace.json` — 마켓플레이스 카탈로그
- `develop-study-documents/devpath-skillpack/.claude-plugin/plugin.json` — 플러그인 매니페스트
- `develop-study-documents/devpath-skillpack/skills/<26개>/` — 적합 스킬 복사본(빌드 산출물)
- `develop-study-documents/devpath-skillpack/README.md` — 빌드/동기화 설명
- `develop-study-documents/scripts/build-devpath-skillpack.ps1` — 정본 Skillbook → 플러그인 skills/ 복사 스크립트
- `develop-study-documents/Skillbook/<수정 스킬>/...` — dev-path-ai 관련 이슈 선반영(정본)

**documents 레포** (브랜치 `docs/study-documents-integration`, 이미 분기됨 — spec 커밋 존재):
- `documents/41_study-documents_연계_카탈로그.md` — 마스터 카탈로그(신규)

**각 devpath-* 레포** (레포별 브랜치 `docs/study-documents-pointer`):
- `<repo>/CLAUDE.md` — 하단 "study-documents 연계" 포인터 블록 추가

---

## Task 1: dev-path-ai 관련 이슈 선반영 (정본 Skillbook 수정)

**작업 레포/브랜치:** study-documents — `feat/devpath-skillpack-plugin` (develop에서 분기)

**Files:**
- Modify: `develop-study-documents/Skillbook/spring-setup/references/*.md` (버전 표기)
- Modify: `develop-study-documents/Skillbook/flutter-setup/references/*.md` (버전 정합)
- Modify: `develop-study-documents/Skillbook/domain-modeler/references/*.md` (BusinessException arity)
- Modify: `develop-study-documents/Skillbook/readme-generator/references/badges*.md`
- Modify: `develop-study-documents/Skillbook/code-reviewer/SKILL.md` (Flutter 트리거 키워드)

**Interfaces:**
- Produces: 적합 스킬 중 dev-path-ai 영향 이슈가 수정된 정본 Skillbook 디렉토리(Task 2가 이를 복사).

- [ ] **Step 1: 브랜치 분기**

```bash
cd /d/workspace/develop-study-documents
git checkout -b feat/devpath-skillpack-plugin develop
git branch --show-current   # → feat/devpath-skillpack-plugin
```

- [ ] **Step 2: spring-setup 버전 실태 확인(추측 금지)**

```bash
cd /d/workspace/develop-study-documents
grep -rniE "spring boot 4\.0\.3|gradle 9\.4|@CreationTimestamp|@CreatedDate" Skillbook/spring-setup/ | head -30
```
확인: `4.0.3`, `9.4.x` 하드코딩 위치와 `@CreationTimestamp`↔`@CreatedDate` 혼용 위치를 식별.

- [ ] **Step 3: spring-setup 버전 갱신**

식별된 위치에서 다음 치환(파일별 Edit):
- `Spring Boot 4.0.3` → `Spring Boot 4.0.7` (dev-path-ai 실측 GA)
- `Gradle 9.4.0`/`9.4.x` → `Gradle 9.5.1`
- 타임스탬프 어노테이션은 Spring Data Auditing(`@CreatedDate`/`@LastModifiedDate` + `@EnableJpaAuditing`)으로 통일, `@CreationTimestamp`(Hibernate) 혼용 제거.

- [ ] **Step 4: flutter-setup 버전 정합 확인·수정**

```bash
grep -rniE "3\.27\.|3\.41\.|3\.24\.|flutter .*3\." Skillbook/flutter-setup/ | head -30
```
디폴트 버전 표기 불일치(3.27.x/3.41.x/3.24.0 혼재)를 **단일 기준**으로 통일하고, dev-path-ai는 Dart 3.12.1(Flutter) 기준임을 주석으로 명기. (하드코딩된 미래/구버전 정리)

- [ ] **Step 5: domain-modeler · readme-generator · code-reviewer 수정**

- domain-modeler: `BusinessException` 생성자를 spring-setup과 동일 arity(1-arg `BusinessException(String message)`)로 통일.
- readme-generator: `badges*.md`의 하드코딩 버전(Spring Boot/Gradle)을 `[버전]` 플레이스홀더 또는 dev-path-ai 실측값으로.
- code-reviewer: SKILL.md 조건부 트리거에 Flutter 키워드(`DioException`, `SharedPreferences`, `Riverpod`) 보강.

- [ ] **Step 6: 변경 검증(렌더·링크)**

```bash
cd /d/workspace/develop-study-documents
git diff --stat
grep -rniE "4\.0\.3|gradle 9\.4" Skillbook/spring-setup/ || echo "OK: no stale 4.0.3/9.4"
```
Expected: 잔존 `4.0.3`/`9.4` 없음.

- [ ] **Step 7: 커밋**

```bash
git add Skillbook/spring-setup Skillbook/flutter-setup Skillbook/domain-modeler Skillbook/readme-generator Skillbook/code-reviewer
git commit -m "fix(skillbook): dev-path-ai 적용 스킬 버전·일관성 이슈 선반영

- spring-setup: Spring Boot 4.0.3→4.0.7 GA, Gradle 9.4→9.5.1, 타임스탬프 Spring Data Auditing 통일
- flutter-setup: 버전 표기 정합(Dart 3.12.1 기준 명기)
- domain-modeler: BusinessException 1-arg 통일
- readme-generator: badges 버전 하드코딩 제거
- code-reviewer: Flutter 트리거 키워드 보강"
```

---

## Task 2: 플러그인 마켓플레이스 패키징 (study-documents)

**작업 레포/브랜치:** study-documents — `feat/devpath-skillpack-plugin` (Task 1 연속)

**Files:**
- Create: `develop-study-documents/scripts/build-devpath-skillpack.ps1`
- Create: `develop-study-documents/devpath-skillpack/.claude-plugin/plugin.json`
- Create: `develop-study-documents/devpath-skillpack/README.md`
- Create: `develop-study-documents/.claude-plugin/marketplace.json`
- Generate: `develop-study-documents/devpath-skillpack/skills/<26개>/` (스크립트 산출)

**Interfaces:**
- Consumes: Task 1의 수정된 정본 Skillbook 26개 디렉토리.
- Produces: 설치 가능한 마켓플레이스 `devpath-study` + 플러그인 `devpath-skillpack`(26 스킬). Task 3이 설치·검증.

- [ ] **Step 1: 빌드 스크립트 작성 (정본 → 플러그인 복사)**

`develop-study-documents/scripts/build-devpath-skillpack.ps1`:

```powershell
# 정본 Skillbook/<skill> → devpath-skillpack/skills/<skill> 복사 (적합 26만)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$src  = Join-Path $root "Skillbook"
$dst  = Join-Path $root "devpath-skillpack\skills"

$include = @(
  "spring-setup","flutter-setup","dockerfile-builder","docker-compose-infra",
  "code-reviewer","complexity-analyzer","error-detective","test-coverage-booster",
  "dart-flutter-lint-check","context-harness","harness-doctor","eval-builder",
  "context7-helper","code-review-multiagent","semgrep-scanner","sonatype-checker",
  "brooks-lint-arch","vercel-grep-helper","deepwiki-helper","flutter-pubdev-helper",
  "postgres-mcp-tuner","domain-modeler","readme-generator","deep-interview",
  "deep-init","sample-code-builder"
)

if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
New-Item -ItemType Directory -Force -Path $dst | Out-Null

$missing = @()
foreach ($s in $include) {
  $from = Join-Path $src $s
  if (-not (Test-Path (Join-Path $from "SKILL.md"))) { $missing += $s; continue }
  Copy-Item $from (Join-Path $dst $s) -Recurse -Force
  # evals/ 는 플러그인 배포 불필요 — 제거(용량 절감)
  $ev = Join-Path $dst "$s\evals"
  if (Test-Path $ev) { Remove-Item $ev -Recurse -Force }
}
if ($missing.Count -gt 0) { throw "Missing SKILL.md for: $($missing -join ', ')" }
Write-Host "Built $($include.Count) skills into devpath-skillpack/skills/"
```

- [ ] **Step 2: 스크립트 실행 → skills/ 생성**

```bash
cd /d/workspace/develop-study-documents
pwsh -File scripts/build-devpath-skillpack.ps1
```
Expected: `Built 26 skills into devpath-skillpack/skills/` (missing 0).

- [ ] **Step 3: 생성 검증 (26개 · SKILL.md 존재 · 제외 미포함)**

```bash
ls devpath-skillpack/skills/ | wc -l            # → 26
find devpath-skillpack/skills -maxdepth 2 -name SKILL.md | wc -l   # → 26
ls devpath-skillpack/skills/ | grep -E "react-setup|super-nova|msa-converter|python-endpoint|db-migration|troubleshoot" || echo "OK: excluded skills absent"
```
Expected: 26 / 26 / "OK: excluded skills absent".

- [ ] **Step 4: plugin.json 작성**

`develop-study-documents/devpath-skillpack/.claude-plugin/plugin.json`:

```json
{
  "name": "devpath-skillpack",
  "description": "DevPath AI 스택(Spring Boot 4·Java 21·PostgreSQL·Flutter) 개발용 스킬 26종 — 환경구축·코드생성·리뷰·테스트·도메인모델링·에이전트엔지니어링·외부도구 통합. 정본: VelkaressiaBlutkrone/develop-study-documents Skillbook.",
  "version": "1.0.0",
  "author": { "name": "VelkaressiaBlutkrone" }
}
```

- [ ] **Step 5: marketplace.json 작성**

`develop-study-documents/.claude-plugin/marketplace.json`:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "devpath-study",
  "description": "DevPath AI 개발에 쓰는 study-documents 스킬 마켓플레이스",
  "owner": { "name": "VelkaressiaBlutkrone" },
  "plugins": [
    {
      "name": "devpath-skillpack",
      "source": "./devpath-skillpack",
      "description": "DevPath AI 스택 개발용 스킬 26종"
    }
  ]
}
```

- [ ] **Step 6: 매니페스트 유효성 검증**

```bash
cd /d/workspace/develop-study-documents
claude plugin validate . 2>&1 | tail -20
```
Expected: validation 통과(에러 0). 실패 시 메시지의 경로/필드 오류를 근본 수정(추측 금지).

- [ ] **Step 7: README 작성 (빌드/동기화 규칙 명시)**

`develop-study-documents/devpath-skillpack/README.md`:

```markdown
# devpath-skillpack (빌드 산출물)

DevPath AI 개발용 스킬 플러그인. **정본은 `../Skillbook/<skill>`**, 이 디렉토리의 `skills/`는
`scripts/build-devpath-skillpack.ps1`이 생성한 복사본이다.

## 동기화
정본 Skillbook 수정 후:
```
pwsh -File ../scripts/build-devpath-skillpack.ps1
```
## 설치 (dev-path-ai 작업 환경)
```
/plugin marketplace add D:/workspace/develop-study-documents
/plugin install devpath-skillpack@devpath-study
```
포함 26 스킬 / 제외 6(LLM·React·Tailwind·MSA). 호출 네임스페이스: `/devpath-skillpack:<skill>`.
```

- [ ] **Step 8: 커밋**

```bash
git add scripts/build-devpath-skillpack.ps1 devpath-skillpack .claude-plugin/marketplace.json
git commit -m "feat(plugin): devpath-skillpack 마켓플레이스 패키징(적합 26 스킬)

study-documents 루트 마켓플레이스 devpath-study + 플러그인 devpath-skillpack.
빌드 스크립트로 정본 Skillbook→skills/ 복사. LLM/React/Tailwind/MSA 6종 제외."
```

---

## Task 3: 플러그인 설치 + 트리거 스모크 테스트 (study-documents)

**작업 레포/브랜치:** study-documents — `feat/devpath-skillpack-plugin` (검증 단계, 파일 변경 없음)

**Interfaces:**
- Consumes: Task 2의 마켓플레이스/플러그인.
- Produces: 설치 동작·자동 트리거·제외 미노출이 검증된 상태. Task 4 카탈로그가 검증 결과를 반영.

- [ ] **Step 1: 마켓플레이스 등록 + 설치**

Claude Code 세션에서:
```
/plugin marketplace add D:/workspace/develop-study-documents
/plugin install devpath-skillpack@devpath-study
/reload-plugins
```
Expected: 설치 성공, 에러 없음.

- [ ] **Step 2: 스킬 노출 확인**

```
/help
```
Expected: `/devpath-skillpack:spring-setup`, `:flutter-setup`, `:code-reviewer` 등 26개가 네임스페이스로 표시. `react-setup`·`super-nova` 등 제외 6은 **부재**.

- [ ] **Step 3: 자동 트리거 스모크 테스트 (대표 3종)**

신규 임시 대화에서 각 발화 → 해당 스킬이 트리거되는지 관찰(실제 트리거 로그/동작):
- "Spring Boot 엔티티 만들어줘" → `devpath-skillpack:spring-setup` 발동 기대
- "flutter doctor 에러 고쳐줘" → `:flutter-setup`
- "이 PostgreSQL 쿼리 EXPLAIN 측정" → `:postgres-mcp-tuner`

각 결과(발동/미발동)를 기록. 미발동 시 description 키워드 점검(정본 수정→재빌드→재설치).

- [ ] **Step 4: 검증 결과 기록**

검증 결과(설치 OK / 노출 26·제외 0 / 트리거 3종 결과)를 Task 4 카탈로그 "검증" 절에 인용할 수 있도록 메모.

> 이 Task는 코드 산출이 아닌 **동작 검증**이다(documents/CLAUDE.md 절대조건 5). 커밋 없음.

---

## Task 4: 마스터 카탈로그 작성 (documents 레포)

**작업 레포/브랜치:** documents — `docs/study-documents-integration` (이미 분기됨)

**Files:**
- Create: `documents/41_study-documents_연계_카탈로그.md`

**Interfaces:**
- Consumes: Task 2 스킬 목록(26), Task 3 검증 결과, study-documents Sample Codes/Dockerfile/가이드 인벤토리.
- Produces: 마스터 카탈로그. Task 5 레포 포인터가 이 문서를 가리킴.

- [ ] **Step 1: frontend 스택 실측(추측 금지)**

```bash
grep -niE "riverpod|go_router|dio|freezed|hooks_riverpod" /d/workspace/dev-path-ai/devpath-frontend/pubspec.yaml | head
```
Sample Codes Flutter 매핑의 정확도를 위해 실제 패키지/버전 확인.

- [ ] **Step 2: 카탈로그 문서 작성**

`documents/41_study-documents_연계_카탈로그.md` — 다음 구조로 작성:

1. **개요**: 정본 경로(`D:\workspace\develop-study-documents`, 소유자 VelkaressiaBlutkrone), 기준 시점(2026-06-22), 동기화 정책(스킬=플러그인 재빌드/`/plugin marketplace update`, 카탈로그=주요 변경 시), 경로 의존 주의.
2. **레이어1 스킬 인덱스(26)**: 표 — 스킬명 / 호출 네임스페이스 `/devpath-skillpack:<skill>` / 대표 트리거 키워드 / 적용 레포 / 정본 경로 `Skillbook/<skill>`. 제외 6 + 사유도 부록 표.
3. **Sample Codes 매핑(149)**:
   - Flutter 47 → `devpath-frontend` (Riverpod 상태/GoRouter 가드/Dio 401 Refresh/SSE·STOMP/하이브리드 암호화/UI 컴포넌트) — 경로 `Sample Codes/🐤 Flutter_*`
   - Spring 80 → `devpath-*-svc` (JPA Entity/분산락/SSE 브로드캐스트/Audit/WebClient) — `Sample Codes/*Spring*`
   - React 15·Python 6 → 참고용(직접 적용 대상 아님, 패턴 학습)
   - ⚠️ 이미 리뷰·수정 완료(Critical 18·Medium 41) — 그대로 참조 가능 명기.
4. **Dockerfile 매핑(8)**: Spring/Flutter/PostgreSQL/Redis → 각 서비스·`devpath-shared`. 경로 `Dockerfile/<stack>`.
5. **가이드 문서 매핑**: Flutter-Riverpod 3.0 마이그레이션 · MSA 패턴 · CQRS · Query-port · Git-Workflow-Strict · 학습문서 작성 가이드 → "어느 작업에서 보는가".
6. **"언제 무엇을" 시나리오 인덱스**: 작업→자산 한 줄 매핑(예: "401 리프레시 구현"→`:flutter-setup` + `Sample Codes/🐤 Flutter_Dio_Bearer_Auth_QueuedInterceptor_401_Refresh` + Riverpod 가이드; "분산락"→`Sample Codes/Spring_Boot_4_Redisson_분산락`; "도메인 모델 설계"→`:domain-modeler`).
7. **검증**: Task 3 결과(설치/노출/트리거) 요약 + 링크 유효성 점검 절차.

> 모든 경로는 실재 확인 후 기입(Step 3에서 일괄 검증). 추측 경로 금지.

- [ ] **Step 3: 카탈로그 내 경로·링크 유효성 검증**

```bash
cd /d/workspace/develop-study-documents
# 카탈로그가 참조한 대표 경로 존재 확인
ls "Sample Codes/🐤 Flutter_Dio_Bearer_Auth_QueuedInterceptor_401_Refresh_샘플코드.md"
ls Dockerfile/Spring Dockerfile/Postgresql Dockerfile/Flutter Dockerfile/Redis
for s in spring-setup flutter-setup postgres-mcp-tuner domain-modeler; do ls "Skillbook/$s/SKILL.md"; done
```
Expected: 모든 경로 존재(에러 0). 누락 시 카탈로그 경로 수정.

- [ ] **Step 4: 커밋**

```bash
cd /d/workspace/dev-path-ai/documents
git add 41_study-documents_연계_카탈로그.md
git commit -m "docs(catalog): study-documents 연계 마스터 카탈로그 추가

스킬 26·Sample Codes 149·Dockerfile 8·가이드 매핑 + 시나리오 인덱스.
플러그인 devpath-skillpack 설치/트리거 검증 결과 반영."
```

---

## Task 5: 각 레포 CLAUDE.md 포인터 추가

**작업 레포/브랜치:** 각 devpath-* 레포 — 레포별 `docs/study-documents-pointer` (각 develop에서 분기)

**Files:**
- Modify: `devpath-frontend/CLAUDE.md`, `devpath-learning-svc/CLAUDE.md`, `devpath-ai-svc/CLAUDE.md`, `devpath-community-svc/CLAUDE.md`, `devpath-platform-svc/CLAUDE.md`, `devpath-sandbox-svc/CLAUDE.md`, `devpath-gateway/CLAUDE.md`, `devpath-shared/CLAUDE.md`, `devpath-gitops/CLAUDE.md`

**Interfaces:**
- Consumes: Task 4 마스터 카탈로그(링크 대상).
- Produces: 각 레포 작업 맥락에서 카탈로그·관련 자산으로 가는 포인터.

- [ ] **Step 1: 표준 포인터 블록 정의**

각 CLAUDE.md 하단에 추가할 블록(해당 스택만 발췌). 백엔드 svc 예(`devpath-learning-svc`):

```markdown
## 📚 study-documents 연계 (상시 참조)
- 마스터 카탈로그: [documents/41_study-documents_연계_카탈로그.md](https://github.com/DevPathAi/documents/blob/main/41_study-documents_연계_카탈로그.md)
- 이 레포 관련 자산:
  - 스킬: `/devpath-skillpack:spring-setup` · `:domain-modeler` · `:code-reviewer` · `:test-coverage-booster` · `:error-detective` · `:postgres-mcp-tuner`
  - Sample Codes: Spring Boot 4 JPA·분산락·SSE·Audit (study-documents `Sample Codes/*Spring*`)
  - 가이드: CQRS·Query-port·MSA 패턴
```

frontend 예(`devpath-frontend`):

```markdown
## 📚 study-documents 연계 (상시 참조)
- 마스터 카탈로그: [documents/41_study-documents_연계_카탈로그.md](https://github.com/DevPathAi/documents/blob/main/41_study-documents_연계_카탈로그.md)
- 이 레포 관련 자산:
  - 스킬: `/devpath-skillpack:flutter-setup` · `:dart-flutter-lint-check` · `:flutter-pubdev-helper` · `:code-reviewer` · `:test-coverage-booster`
  - Sample Codes: Riverpod·GoRouter·Dio 401 Refresh·SSE/STOMP·암호화·UI (study-documents `Sample Codes/🐤 Flutter_*`)
  - 가이드: Flutter-Riverpod 3.0 마이그레이션
```

shared 예(`devpath-shared`):

```markdown
## 📚 study-documents 연계 (상시 참조)
- 마스터 카탈로그: [documents/41_study-documents_연계_카탈로그.md](https://github.com/DevPathAi/documents/blob/main/41_study-documents_연계_카탈로그.md)
- 이 레포 관련 자산:
  - 스킬: `/devpath-skillpack:dockerfile-builder` · `:docker-compose-infra`
  - Dockerfile: Spring·PostgreSQL·Redis (study-documents `Dockerfile/`)
```

gitops 예(`devpath-gitops`):

```markdown
## 📚 study-documents 연계 (상시 참조)
- 마스터 카탈로그: [documents/41_study-documents_연계_카탈로그.md](https://github.com/DevPathAi/documents/blob/main/41_study-documents_연계_카탈로그.md)
- 이 레포 관련 자산:
  - 스킬: `/devpath-skillpack:dockerfile-builder` · `:docker-compose-infra`
  - 가이드: Kubernetes 배포 전략·Docker 운영
```

gateway는 백엔드 svc 블록과 동일(spring-setup 계열). ai/community/platform/sandbox-svc도 백엔드 svc 블록 사용.

- [ ] **Step 2: 레포별 분기·추가·커밋 (각 레포 반복)**

각 레포에서 (예시는 frontend):
```bash
cd /d/workspace/dev-path-ai/devpath-frontend
git checkout -b docs/study-documents-pointer develop
# CLAUDE.md 하단에 해당 블록 Edit 추가
git add CLAUDE.md
git commit -m "docs(claude): study-documents 연계 포인터 추가"
```
9개 레포(frontend·learning/ai/community/platform/sandbox-svc·gateway·shared·gitops) 각각 수행. **각 레포 독립 브랜치·커밋.**

- [ ] **Step 3: 추가 검증 (블록 1개 = 1 레포, 누락/오배치 없음)**

```bash
cd /d/workspace/dev-path-ai
for r in devpath-frontend devpath-learning-svc devpath-ai-svc devpath-community-svc devpath-platform-svc devpath-sandbox-svc devpath-gateway devpath-shared devpath-gitops; do
  n=$(grep -c "study-documents 연계" "$r/CLAUDE.md" 2>/dev/null)
  echo "$r: $n"
done
```
Expected: 각 레포 `1`. (0=누락, 2+=중복)

---

## Task 6: 최종 통합 검증

**작업 레포/브랜치:** 검증 전용(파일 변경 없음)

**Interfaces:**
- Consumes: Task 2~5 산출물 전체.
- Produces: 통합 동작 확인 — PR 가능 상태.

- [ ] **Step 1: 스킬 레이어 재확인**

```
/plugin marketplace update devpath-study
/reload-plugins
/help
```
Expected: 26 스킬 네임스페이스 노출 유지, 제외 6 부재.

- [ ] **Step 2: 카탈로그→자산 경로 전수 점검**

```bash
cd /d/workspace/develop-study-documents
# 카탈로그가 참조하는 모든 study-documents 경로를 스크립트로 추출해 존재 확인
# (카탈로그에서 `Sample Codes/`, `Dockerfile/`, `Skillbook/` 참조 라인 대상)
grep -oE "(Sample Codes|Dockerfile|Skillbook)/[^ )\`]+" /d/workspace/dev-path-ai/documents/41_study-documents_연계_카탈로그.md | sort -u | while read p; do
  [ -e "$p" ] && echo "OK  $p" || echo "MISSING  $p"
done | grep MISSING || echo "ALL PATHS OK"
```
Expected: `ALL PATHS OK`.

- [ ] **Step 3: 레포 포인터 링크 일관성**

각 레포 CLAUDE.md 포인터의 마스터 카탈로그 링크가 동일 URL을 가리키는지 확인:
```bash
cd /d/workspace/dev-path-ai
grep -rh "41_study-documents_연계_카탈로그" */CLAUDE.md | sort -u
```
Expected: 단일 URL 1줄(불일치 없음).

- [ ] **Step 4: PR 준비 보고**

각 레포 변경 요약 + 검증 결과(스킬 노출/트리거/경로/링크)를 사용자에게 보고. develop PR 생성은 사용자 승인 후(또는 finishing-a-development-branch 스킬로).

---

## Self-Review (작성자 점검 결과)

**1. Spec coverage:** spec §4(레이어1)→Task 1·2·3, §5(레이어2)→Task 4·5, §8(검증)→Task 3·6, §4.4(이슈 선반영)→Task 1, §4.3(제외)→Global Constraints+Task 2 Step 3. 모든 spec 섹션이 task로 매핑됨.

**2. Placeholder scan:** 카탈로그 본문(Task 4 Step 2)은 구조 명세 + 실재 경로 예시로 기술하되, 모든 경로는 Step 3/Task 6에서 존재 검증을 강제 — "TBD" 없음. 빌드 스크립트·JSON·명령은 전량 실코드.

**3. Type consistency:** 마켓플레이스명 `devpath-study`, 플러그인명 `devpath-skillpack`, 호출 네임스페이스 `/devpath-skillpack:<skill>`, 적합 26 목록 — 전 task 동일 표기 확인. 제외 6(react-setup·super-nova·msa-converter·python-endpoint·db-migration·troubleshoot) 일관.

**남은 불확정(구현 중 확정):** frontend Riverpod/go_router 실제 버전(Task 4 Step 1에서 실측), 트리거 스모크 결과(Task 3) — plan에 검증 단계로 내장됨.
