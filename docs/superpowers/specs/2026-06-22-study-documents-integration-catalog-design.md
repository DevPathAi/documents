# DevPath AI ↔ study-documents 상시 통합 카탈로그 — 설계서

- **작성일**: 2026-06-22
- **상태**: 설계 확정 (구현 계획 대기)
- **대상 범위**: DevPathAi 멀티레포 전반 + `VelkaressiaBlutkrone/develop-study-documents`
- **연계 브랜치**: `documents` 레포 `docs/study-documents-integration`

---

## 1. 배경과 목적

`develop-study-documents`(이하 study-documents)는 DevPath AI와 **거의 동일한 스택**을 커버하는 학습·스킬·코드 저장소다. dev-path-ai 개발 중 이 자산을 매번 수동으로 찾아 들어가는 대신, **항상 작동하는 통합 구조**를 만들어 개발 생산성을 높인다.

### 확인된 사실 (추측 아님 — 실측)

| 항목 | dev-path-ai | study-documents |
|------|-------------|-----------------|
| GitHub 소유자 | `DevPathAi` 조직 (멀티레포) | `VelkaressiaBlutkrone` 개인 |
| 백엔드 | Spring Boot **4.0.7 GA** · Java 21 · Gradle 9.5.1 · PostgreSQL · JPA · Redis · Kafka · OAuth2 RS | spring-setup 스킬(Spring Boot 4/Java 21 기준) — **정합** |
| 프론트 | Dart SDK 3.12.1 (Flutter) | flutter-setup · Flutter Sample Codes 47종 |
| 자산 규모 | — | 스킬 31 · Sample Codes 149(Spring 80·Flutter 47·React 15·Python 6) · Dockerfile 8 |
| 현재 연결 상태 | **스킬 활성화 0** (전역 64 스킬 중 Skillbook 출신 0), 루트 비-git 멀티레포 컨테이너 | 플러그인 미패키징, 과거 `~/.claude/skills` 복사 흔적 |

### 핵심 제약

1. **두 저장소는 GitHub 소유자가 다름** → 복사하면 "두 개의 진실 소스 + 출처 혼재 + 동기화 부채". **참조/연결이 구조적으로 우월**.
2. **dev-path-ai 루트는 비-git** → 루트에 둔 산출물은 팀/다중세션 공유 불가(로컬 전용). 영구 산출물은 git 레포 안에 둬야 함.
3. **각 devpath-* 는 독립 GitHub 레포** → 레포별 포인터는 각 레포 git으로 공유됨.

---

## 2. 확정 결정 (사용자 합의)

| # | 결정 항목 | 선택 |
|---|-----------|------|
| D1 | 산출물 범위 | **상시 통합 카탈로그 구축** (영구 인덱스·스킬 연결) |
| D2 | 우선 대상 | **전 영역 균형** (스킬·코드·문서) |
| D3 | 스킬 활성화 방식 | **로컬 플러그인 마켓플레이스** (study-documents가 단일 정본) |
| D4 | 카탈로그 위치 | **documents 레포 마스터 카탈로그 + 각 레포 CLAUDE.md 포인터** |
| D5 | 스킬 선별 | **적합 ~24개만 선별** (LLM/React/Tailwind/MSA 전환 제외) |
| D6 | 이슈 수정 | **dev-path-ai 관련만 선반영** (적용 스킬의 영향 이슈만) |

---

## 3. 아키텍처 — 2개 독립 레이어

```
┌──────────── study-documents (VelkaressiaBlutkrone, 단일 정본) ────────────┐
│  Skillbook/ (31)      Sample Codes/ (149)     Dockerfile/ (8)    가이드 문서  │
└─────┬─────────────────────────────┬──────────────────────────────────────────┘
      │ ① 플러그인 패키징            │ ② 참조 인덱싱 (복사 아님 — 경로 매핑)
      ▼                             ▼
┌─ 레이어1: 실행 도구 ─────────┐  ┌─ 레이어2: 참조 카탈로그 ───────────────────────────┐
│ study-documents/            │  │ DevPathAi/documents/                                │
│   .claude-plugin/           │  │   41_study-documents_연계_카탈로그.md (마스터)       │
│     marketplace.json        │  │     - 스택→자산 매핑표 (스킬/코드/Dockerfile/문서)   │
│   plugin(s) 정의            │  │     - "언제 무엇을 보는가" 인덱스                    │
│ → claude plugins install    │  │ + 각 레포 CLAUDE.md 하단 "study-documents 참조" 블록 │
│ → 적합 24 스킬 자동 트리거  │  │   (해당 스택 발췌 포인터)                            │
└─────────────────────────────┘  └─────────────────────────────────────────────────────┘
```

- **레이어1(스킬)**: study-documents에 마켓플레이스 정의 추가 → deepe 환경 설치 → Claude가 키워드로 자동 트리거. study-documents가 정본이라 복사·동기화 부채 없음.
- **레이어2(카탈로그)**: documents 레포 마스터 인덱스 1본 + 각 레포 CLAUDE.md 짧은 포인터. git 추적·다중세션 공유.

두 레이어는 **독립**이다. 한쪽이 실패해도 다른 쪽은 동작한다(스킬 미설치여도 카탈로그로 수동 참조 가능, 카탈로그 없이도 스킬은 트리거).

---

## 4. 레이어1 — 플러그인 마켓플레이스 (study-documents 측)

### 4.1 산출물

- `develop-study-documents/.claude-plugin/marketplace.json` — 로컬 마켓플레이스 정의
- 플러그인 패키징 구조 (Skillbook의 SKILL.md들을 플러그인 `skills/`로 노출)
- 설치/업데이트 절차 문서

> **구현 시 확인 필요(추측 금지)**: Claude Code 플러그인/마켓플레이스 정확한 스키마는 deepe 환경의 기존 설치본(`~/.claude/plugins/known_marketplaces.json`, `installed_plugins.json`, `oh-my-claudecode` 구조)을 실측해 확정한다. Skillbook이 `Skillbook/<skill>/SKILL.md` 구조이므로 플러그인 `skills/` 매핑 방식(심볼릭/경로지정/재배치)을 검증 후 결정.

### 4.2 포함 스킬 — 적합 후보 (제외 7개를 뺀 나머지)

> Skillbook SKILL.md 31개 기준 제외 7개를 빼면 **약 24개**가 적합 후보다. 카테고리별 잠정 목록은 아래이며, `dart-flutter-lint-check`·`sample-code-builder` 포함 여부와 **정확한 총수는 구현 1단계에서 SKILL.md frontmatter 전수 확인 후 확정**한다(추측 금지).

- **환경 구축**: spring-setup · flutter-setup · dockerfile-builder · docker-compose-infra
- **분석/리뷰**: code-reviewer · complexity-analyzer · error-detective · test-coverage-booster
- **에이전트 엔지니어링**: context-harness · harness-doctor · eval-builder
- **외부도구 통합**: context7-helper · code-review-multiagent · semgrep-scanner · sonatype-checker · brooks-lint-arch · vercel-grep-helper · deepwiki-helper · flutter-pubdev-helper · postgres-mcp-tuner
- **설계/문서**: domain-modeler · readme-generator · deep-interview
- **유틸**: deep-init
- **추가 적합(분류 외)**: dart-flutter-lint-check · sample-code-builder

### 4.3 제외 스킬 (7개) — 사유

| 스킬 | 제외 사유 |
|------|-----------|
| spring-api | LLM 프로젝트 전용 (WebClient/Mono 비동기) — dev-path-ai는 webmvc, 컨벤션 충돌 |
| python-endpoint | LLM 전용 (FastAPI+Ollama+ChromaDB) — dev-path-ai에 Python 서비스 없음 |
| db-migration | MySQL 전용 — dev-path-ai는 PostgreSQL + 중앙 Flyway |
| troubleshoot | LLM 프로젝트(MySQL+Ollama+Python+Spring) 전용 — 범용 진단은 error-detective |
| react-setup | React/Vite — 프론트엔드는 Flutter |
| super-nova | Tailwind 디자인 엔진 — Flutter 프로젝트에 부적합 |
| msa-converter | 모놀리스→MSA 전환 스킬 — dev-path-ai는 이미 MSA 구성 |

제외 스킬은 study-documents 정본에 그대로 둔다(삭제 아님). 단지 dev-path-ai용 마켓플레이스에 등록하지 않는다.

### 4.4 dev-path-ai 관련 이슈 선반영 (D6)

패키징 전, **적용 스킬 중 dev-path-ai에 영향 주는 이슈만** 수정한다. (study-documents가 정본이므로 study-documents 브랜치에서 수정)

| 스킬 | 이슈 | 조치 |
|------|------|------|
| spring-setup | Spring Boot 4.0.3을 GA로 표기 / Gradle 9.4.0 | dev-path-ai 실측값 **4.0.7 GA · Gradle 9.5.1**로 갱신 |
| spring-setup | `@CreationTimestamp` vs `@CreatedDate` 혼용 | Spring Data Auditing으로 통일 |
| flutter-setup | 버전 예시 3.27.x/3.41.x 혼재, 구버전 하드코딩 | dev-path-ai Dart 3.12.1 기준 정합 확인 |
| domain-modeler | `BusinessException` 생성자 arity 불일치(spring-setup과) | 1-arg로 통일 |
| readme-generator | badges 버전 하드코딩 | dev-path-ai 실제 버전 또는 플레이스홀더 |
| code-reviewer | Flutter 키워드(DioException 등) 조건부 트리거 누락 | 보강 |

> 나머지 리뷰 리포트 이슈(제외 스킬의 Critical, 비-dev-path-ai 항목)는 **이번 범위 밖**. 별도 세션.

### 4.5 설치/활성화

- deepe 환경에서 `claude plugins` 흐름으로 study-documents 마켓플레이스 등록 → 적합 스킬 플러그인 설치.
- 전역 설치이므로 dev-path-ai 외 프로젝트에도 노출됨(단일 개발 환경이므로 수용).

---

## 5. 레이어2 — 참조 카탈로그 (documents 레포 + 레포별)

### 5.1 마스터 카탈로그: `documents/41_study-documents_연계_카탈로그.md`

기존 40개 정본 문서 다음 번호로 신설. 구성:

1. **개요**: study-documents 경로·소유자·동기화 정책·이 카탈로그의 역할
2. **스킬 인덱스**: 적합 24 스킬 — 이름 / 트리거 키워드 / dev-path-ai 적용 레포 / study-documents 경로
3. **Sample Codes 매핑** (149개 → 스택별):
   - Flutter 47 → `devpath-frontend` (Riverpod·GoRouter·Dio·SSE·STOMP·암호화·UI 컴포넌트)
   - Spring 80 → `devpath-*-svc` (JPA·분산락·SSE·Audit·WebClient 등)
   - React 15 / Python 6 → 참고용(직접 적용 대상 아님, 패턴 학습)
   - ⚠️ **이미 리뷰·수정 완료**(Critical 18·Medium 41 수정됨) — 그대로 참조 가능
4. **Dockerfile 매핑** (8종 → 서비스): Spring/Flutter/PostgreSQL/Redis → 각 서비스·shared
5. **가이드 문서 매핑**: Flutter-Riverpod 3.0 마이그레이션 · MSA 패턴 · CQRS · Query-port · Git-Workflow-Strict · 학습문서 작성 가이드 → 어느 작업에서 보는가
6. **"언제 무엇을" 시나리오 인덱스**: "엔티티 추가" / "401 리프레시 구현" / "분산락" / "SSE 브로드캐스트" / "라우팅 가드" 등 작업 → 해당 스킬+Sample Code+가이드 한 줄 매핑

### 5.2 레포별 CLAUDE.md 포인터

각 레포 CLAUDE.md 하단에 표준 블록 1개 추가(해당 스택만 발췌):

```markdown
## 📚 study-documents 연계 (상시 참조)
- 마스터 카탈로그: DevPathAi/documents/41_study-documents_연계_카탈로그.md
- 이 레포 관련 자산:
  - 스킬: <해당 스택 스킬>
  - Sample Codes: <경로 — 핵심 패턴>
  - 가이드: <경로>
```

- `devpath-frontend` → Flutter 스킬/Sample/Riverpod 가이드
- `devpath-*-svc` → Spring 스킬/Sample/도메인모델링/CQRS
- `devpath-shared` → Dockerfile/docker-compose/마이그레이션
- `devpath-gateway` → Spring + 라우팅 패턴
- `devpath-gitops` → Docker/K8s/배포 가이드

> 포인터는 **짧게**(링크 + 1줄). 상세는 마스터 카탈로그가 보유. 중복 최소화.

---

## 6. 데이터 흐름

1. **스킬 트리거**: 개발자가 "엔티티 만들어줘" / "이 에러 해결" / "테스트 보강" 발화 → 플러그인 스킬 자동 발동(어느 레포에서든).
2. **자산 참조**: 작업 중 Claude가 레포 CLAUDE.md 포인터 → 마스터 카탈로그 → study-documents의 해당 Sample Code/Dockerfile/가이드 경로를 읽어 검증된 패턴 적용.

---

## 7. 동기화·유지보수

- study-documents 갱신 → `claude plugins update`로 스킬 반영(경로 참조라 재패키징 불필요, 스키마에 따라 확인).
- 마스터 카탈로그는 study-documents **주요 구조 변경 시에만** 갱신(저빈도). 카탈로그 상단에 "기준 시점" 명기.
- 경로 의존: study-documents가 `D:\workspace\develop-study-documents`에 있다고 가정. 이동 시 마켓플레이스 경로 갱신 필요 — 카탈로그에 명기.

---

## 8. 검증·테스트 (이 작업의 "테스트")

산출물이 코드가 아니므로 **정합성·동작 검증**으로 적용(documents/CLAUDE.md 절대조건 2 준수):

- **스킬 활성화 검증**: 설치 후 대표 키워드 스모크 테스트 — "spring entity" → spring-setup, "flutter doctor 에러" → flutter-setup, "이 코드 리뷰" → code-reviewer 발동 확인. 제외 스킬(react-setup 등) 미노출 확인.
- **카탈로그 링크 검증**: 마스터 카탈로그·레포 포인터의 모든 경로/링크가 실재하는지 점검. mermaid·표 렌더 확인.
- **오트리거 회귀**: study-documents의 `skill-routing-eval` 하네스 참조 — 적합 24 스킬 간 충돌·과트리거 없는지(가능 시 재실행).

---

## 9. 범위 밖 (YAGNI)

- 제외 7 스킬의 이슈 수정, 비-dev-path-ai Sample Codes 추가 리뷰 → 별도 세션.
- study-documents를 DevPathAi 조직으로 이관/미러링 → 하지 않음(소유자 분리 유지).
- Sample Codes를 dev-path-ai 레포로 복사 → 하지 않음(참조만, 동기화 부채 회피).
- 제외 스킬 삭제 → 하지 않음(study-documents 정본 보존).

---

## 10. 리스크·미해결

| 리스크 | 대응 |
|--------|------|
| Claude Code 플러그인/마켓플레이스 스키마 미확정 | 구현 1단계에서 deepe 기존 설치본 실측 후 확정(추측 금지) |
| Skillbook 스킬 디렉토리 구조 ↔ 플러그인 `skills/` 매핑 | 실측 검증 후 심볼릭/경로지정/재배치 중 택1 |
| 경로 하드코딩(D:\workspace) 이동 취약성 | 카탈로그·마켓플레이스에 경로 명기, 이동 시 갱신 절차 문서화 |
| 전역 설치로 타 프로젝트 노출 | 단일 개발 환경이므로 수용(D3 합의) |

---

## 11. 구현 단계 개요 (writing-plans로 상세화)

1. **사실 확정**: 플러그인 스키마 실측 · 31 스킬 SKILL.md 전수 확인 → 적합 24 최종 목록 · frontend Riverpod/router 버전 확정.
2. **레이어1**: study-documents 브랜치 → dev-path-ai 관련 이슈 선반영 → `.claude-plugin/marketplace.json` 작성 → 설치 → 스모크 테스트.
3. **레이어2-A**: documents 레포 마스터 카탈로그 작성.
4. **레이어2-B**: 각 레포 CLAUDE.md 포인터 추가(레포별 브랜치, git-branch-flow 준수).
5. **검증**: 스킬 트리거·링크·오트리거 회귀 → 각 레포 develop PR.

> 멀티레포 작업이므로 각 레포는 `develop`에서 작업 브랜치 분기 → develop PR. study-documents도 동일 흐름. 서브에이전트 위임 시 Scope Lock 준수.
