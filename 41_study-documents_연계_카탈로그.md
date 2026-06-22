# 41. study-documents 연계 마스터 카탈로그

> **기준 시점**: 2026-06-22  
> **정본 레포**: `D:\workspace\develop-study-documents` (소유자: VelkaressiaBlutkrone)  
> **활용 대상**: DevPathAi 멀티레포 전 도메인  
> **작성 주체**: documents/41 (docs/study-documents-integration 브랜치)

---

## ① 개요

### 목적

`develop-study-documents`(이하 **study-documents**)의 스킬·코드·문서 자산을 dev-path-ai 개발에 상시 참조·활용하기 위한 **단일 진입점 인덱스**다. 이 카탈로그 하나만 열면 "어떤 작업에 어떤 자산을 쓰는가"를 한눈에 찾을 수 있다.

### 정본 경로 및 소유자

| 항목 | 값 |
|------|-----|
| 정본 경로 | `D:\workspace\develop-study-documents` |
| 소유자 | VelkaressiaBlutkrane |
| 스킬 루트 | `Skillbook/<skill>/SKILL.md` |
| Sample Codes | `Sample Codes/` (총 149개) |
| Dockerfile | `Dockerfile/<Stack>/` |
| 가이드(루트) | `*.md` (루트 직속 가이드 파일) |

> ⚠️ **경로 의존 주의**: 이 카탈로그의 모든 `Study-docs:` 경로는 `D:\workspace\develop-study-documents\` 를 절대 기준으로 한다. 레포를 다른 위치에 클론한 경우 경로를 재조정한다.

### 동기화 정책

| 자산 유형 | 동기화 방법 | 주기 |
|-----------|-------------|------|
| 스킬 (26개) | `devpath-skillpack` 플러그인 재빌드 → `/plugin marketplace update` | study-documents 스킬 변경 시 |
| Sample Codes / Dockerfile / 가이드 | 작업자가 직접 참조 (읽기 전용) | 필요 시 |
| 이 카탈로그(41번) | 수동 갱신 PR (`docs/*` → develop) | study-documents 주요 변경 시 |

### 플러그인 네임스페이스

스킬은 `devpath-skillpack` 플러그인으로 패키징되어 `/devpath-skillpack:<skill>` 형식으로 호출한다.  
설치·검증은 **별도 Task**에서 수행 예정이며, 이 카탈로그는 **참조 인덱스** 역할만 한다.

---

## ② 레이어1 — 스킬 인덱스 (26개)

### 적합 스킬 전체 표

| # | 스킬명 | 호출 | 대표 트리거 키워드 | 적용 레포 | 정본 경로 |
|---|--------|------|--------------------|-----------|-----------|
| 1 | spring-setup | `/devpath-skillpack:spring-setup` | Spring Boot, build.gradle, JPA, Security, JWT, Flyway, Redis, AOP, 패키지 구조, 도메인 생성, 전체 레이어 생성 | devpath-ai-svc, community-svc, learning-svc, platform-svc, sandbox-svc, devpath-gateway | `Skillbook/spring-setup/SKILL.md` |
| 2 | flutter-setup | `/devpath-skillpack:flutter-setup` | Flutter SDK, flutter doctor, pubspec 의존성, Riverpod 초기 세팅, freezed build_runner, GoRouter 패키지 설정, CI/CD Flutter, 패키지 충돌 | devpath-frontend | `Skillbook/flutter-setup/SKILL.md` |
| 3 | dockerfile-builder | `/devpath-skillpack:dockerfile-builder` | Dockerfile 작성, 멀티스테이지 빌드, COPY 최적화, .dockerignore, 이미지 경량화 | devpath-shared, devpath-gitops | `Skillbook/dockerfile-builder/SKILL.md` |
| 4 | docker-compose-infra | `/devpath-skillpack:docker-compose-infra` | docker-compose, 로컬 인프라, PostgreSQL 컨테이너, Redis 컨테이너, Kafka 로컬, 헬스체크 | devpath-shared, devpath-gitops | `Skillbook/docker-compose-infra/SKILL.md` |
| 5 | code-reviewer | `/devpath-skillpack:code-reviewer` | 코드 리뷰, PR 리뷰, 보안 취약점, N+1 쿼리, XSS, SQL Injection, SOLID, CORS, Java, Dart | 전 레포 | `Skillbook/code-reviewer/SKILL.md` |
| 6 | complexity-analyzer | `/devpath-skillpack:complexity-analyzer` | 복잡도 분석, 리팩토링, 코드 스멜, God Class, SOLID 원칙, 순환 복잡도, 인지 복잡도, SRP, DIP | 전 레포 | `Skillbook/complexity-analyzer/SKILL.md` |
| 7 | error-detective | `/devpath-skillpack:error-detective` | Exception, 스택 트레이스, 빌드 실패, CORS, 502, NullPointerException, FlutterError, OOMKilled, 에러 디버깅 | 전 레포 | `Skillbook/error-detective/SKILL.md` |
| 8 | test-coverage-booster | `/devpath-skillpack:test-coverage-booster` | 테스트 커버리지, JUnit, Mockito, mocktail, 단위 테스트, 통합 테스트, E2E, 테스트 작성, 커버리지 올리기 | 전 레포 | `Skillbook/test-coverage-booster/SKILL.md` |
| 9 | dart-flutter-lint-check | `/devpath-skillpack:dart-flutter-lint-check` | Dart lint, analysis_options, dart analyze, 린트 에러, Effective Dart, flutter_lints, dart fix, 위젯 컨벤션, pubspec 검증 | devpath-frontend | `Skillbook/dart-flutter-lint-check/SKILL.md` |
| 10 | context-harness | `/devpath-skillpack:context-harness` | CLAUDE.md 작성, AGENTS.md 만들어줘, .cursorrules, copilot-instructions, 에이전트 규칙 파일, 컨텍스트 엔지니어링, 하네스 구성 | 전 레포 | `Skillbook/context-harness/SKILL.md` |
| 11 | harness-doctor | `/devpath-skillpack:harness-doctor` | 에이전트가 컨벤션 안 지켜, AI가 같은 실수 반복, 환각, 무한 루프, 에이전트 규칙 무시, 하네스 진단 | 전 레포 | `Skillbook/harness-doctor/SKILL.md` |
| 12 | eval-builder | `/devpath-skillpack:eval-builder` | 평가 만들어줘, eval 작성, LLM 평가, RAG 평가, 에이전트 평가, 루브릭, LM judge, trajectory 평가 | 전 레포 | `Skillbook/eval-builder/SKILL.md` |
| 13 | context7-helper | `/devpath-skillpack:context7-helper` | 버전 확인, 최신 API, 환각 방지, 마이그레이션, Spring Boot 4, Dio 5, Riverpod 3, GoRouter 14, Sample Codes 보강 | 전 레포 | `Skillbook/context7-helper/SKILL.md` |
| 14 | code-review-multiagent | `/devpath-skillpack:code-review-multiagent` | 다중 에이전트 리뷰, 병렬 PR 리뷰, 거짓 양성 필터, 신뢰도 점수, PR 자동 리뷰, 머지 가부, code-review plugin | 전 레포 | `Skillbook/code-review-multiagent/SKILL.md` |
| 15 | semgrep-scanner | `/devpath-skillpack:semgrep-scanner` | 보안 스캔, OWASP, 취약점 탐지, JWT 검증, 암호화 검증, RLS 검증, XSS, SQL Injection, 시크릿 스캔, CWE 매핑 | 전 레포 | `Skillbook/semgrep-scanner/SKILL.md` |
| 16 | sonatype-checker | `/devpath-skillpack:sonatype-checker` | 의존성 검증, CVE 조회, 버전 추천, 공급망 보안, build.gradle, pubspec.yaml, 취약 버전, OSS Index | 전 레포 | `Skillbook/sonatype-checker/SKILL.md` |
| 17 | brooks-lint-arch | `/devpath-skillpack:brooks-lint-arch` | 아키텍처 리뷰, 부패 진단, Hexagonal, CQRS, DDD, Aggregate, Modulith, Clean Architecture, 응집도, 결합도, 도메인 표류 | devpath-ai-svc, community-svc, learning-svc, platform-svc, sandbox-svc, devpath-gateway | `Skillbook/brooks-lint-arch/SKILL.md` |
| 18 | vercel-grep-helper | `/devpath-skillpack:vercel-grep-helper` | Vercel Grep, GitHub 코드 검색, 실전 패턴, OSS 구현, Outbox, Saga, CQRS 비교, 코드 발굴 | 전 레포 | `Skillbook/vercel-grep-helper/SKILL.md` |
| 19 | deepwiki-helper | `/devpath-skillpack:deepwiki-helper` | DeepWiki, OSS 위키, 설계 의도, ADR, RFC, Spring Modulith 배경, Riverpod 설계, 학습 깊이 | 전 레포 | `Skillbook/deepwiki-helper/SKILL.md` |
| 20 | flutter-pubdev-helper | `/devpath-skillpack:flutter-pubdev-helper` | pub.dev, Flutter 패키지 발굴, pubspec 호환성, Dart 3 지원, Likes, Pub 점수, 패키지 비교, 마이그레이션 경로 | devpath-frontend | `Skillbook/flutter-pubdev-helper/SKILL.md` |
| 21 | postgres-mcp-tuner | `/devpath-skillpack:postgres-mcp-tuner` | PostgreSQL 인덱스 튜닝, EXPLAIN ANALYZE, 쿼리 최적화, pgvector, HNSW, IVFFlat, JPA N+1, QueryDSL Projection, DB 성능 | devpath-ai-svc, community-svc, learning-svc, platform-svc, sandbox-svc | `Skillbook/postgres-mcp-tuner/SKILL.md` |
| 22 | domain-modeler | `/devpath-skillpack:domain-modeler` | DDD, 도메인 모델링, Aggregate, 바운디드 컨텍스트, 도메인 이벤트, CQRS, 이벤트 스토밍, Entity, Value Object | devpath-ai-svc, community-svc, learning-svc, platform-svc, sandbox-svc, devpath-gateway | `Skillbook/domain-modeler/SKILL.md` |
| 23 | readme-generator | `/devpath-skillpack:readme-generator` | README, 리드미, 기술 스택 뱃지, 설치 방법, API 명세, 환경변수, 디렉토리 구조, shields.io | 전 레포 | `Skillbook/readme-generator/SKILL.md` |
| 24 | deep-interview | `/devpath-skillpack:deep-interview` | 요구사항 정리, 기능 정의, 문제 분석, PRD 빈약, 뭘 만들어야 할지 모르겠어, 소크라테스 인터뷰 | 전 레포 | `Skillbook/deep-interview/SKILL.md` |
| 25 | deep-init | `/devpath-skillpack:deep-init` | 코드베이스 문서화, AI-CONTEXT.md 생성, AI 가이드 만들어줘, 프로젝트 초기 문서화 | 전 레포 | `Skillbook/deep-init/SKILL.md` |
| 26 | sample-code-builder | `/devpath-skillpack:sample-code-builder` | 샘플 코드 만들어줘, 예제 코드 작성, 코드 예시 보여줘, sample code, code example, 이 기능 어떻게 쓰는지 | 전 레포 | `Skillbook/sample-code-builder/SKILL.md` |

### 스킬→레포 매핑 요약

```
백엔드 svc 5개 + devpath-gateway
  └─ spring-setup · domain-modeler · code-reviewer · complexity-analyzer
     test-coverage-booster · error-detective · postgres-mcp-tuner
     brooks-lint-arch · context7-helper · sonatype-checker
     semgrep-scanner · code-review-multiagent · deepwiki-helper · vercel-grep-helper

devpath-frontend
  └─ flutter-setup · dart-flutter-lint-check · flutter-pubdev-helper
     code-reviewer · complexity-analyzer · test-coverage-booster
     error-detective · context7-helper

devpath-shared · devpath-gitops
  └─ dockerfile-builder · docker-compose-infra

전 레포 공통 (14개)
  └─ context-harness · harness-doctor · eval-builder · readme-generator
     deep-interview · deep-init · sample-code-builder · code-reviewer
     complexity-analyzer · error-detective · test-coverage-booster
     context7-helper · semgrep-scanner · sonatype-checker
     code-review-multiagent · vercel-grep-helper · deepwiki-helper
```

### 부록 A — 제외 스킬 (6개)

| 스킬명 | 제외 사유 |
|--------|-----------|
| `python-endpoint` | LLM 서버(FastAPI + Ollama) 전용. dev-path-ai는 Python 백엔드 없음 |
| `db-migration` | MySQL + Alembic 전용. dev-path-ai는 PostgreSQL + Flyway 사용 |
| `troubleshoot` (llm-project-troubleshoot) | LLM 프로젝트(Ollama·MySQL·Python) 전용 트러블슈팅. 스택 불일치 |
| `react-setup` | React 없음. 프론트는 Flutter(Dart) |
| `msa-converter` | dev-path-ai는 이미 MSA 구조. 모놀리스 → MSA 변환 스킬 불필요 |
| `super-nova` | Tailwind CSS 기반. Flutter에 적용 불가 |

---

## ③ 레이어2 — Sample Codes 매핑 (149개)

> ✅ **리뷰·수정 완료**: `Sample Codes/_audit/` 보고서 기준 Critical 18건·Medium 41건 수정 완료. 현재 전 파일 그대로 참조 가능.

### 스택별 분포

| 스택 | 파일 수 | 주 활용 레포 |
|------|---------|-------------|
| Flutter (🐤 Flutter_*) | 47 | devpath-frontend |
| Spring Boot 4 (🐤 Spring_Boot_4_*) | 80 | devpath-*-svc, devpath-gateway |
| React TypeScript (🐤 React_TS_*) | 15 | 참고용 (dev-path-ai 미사용 스택) |
| Python FastAPI (🐤 Python_*) | 6 | 참고용 (dev-path-ai 미사용 스택) |
| 감사 보고서 (_audit) | 1 | — |
| **합계** | **149** | |

### Flutter 대표 패턴 (devpath-frontend 활용)

실측 패키지: `flutter_riverpod ^3.3.0` · `go_router ^14.6.0` · `dio ^5.0.0` · Dart SDK `^3.12.1`

| 패턴 | 파일명 (Study-docs: `Sample Codes/`) |
|------|--------------------------------------|
| 401 Refresh / Bearer Auth | `🐤 Flutter_Dio_Bearer_Auth_QueuedInterceptor_401_Refresh_샘플코드.md` |
| GoRouter 인증 리다이렉트 | `🐤 Flutter_GoRouter_인증_리다이렉트_라우팅_샘플코드.md` |
| GoRouter 탭 네비게이션 | `🐤 Flutter_GoRouter_StatefulShellRoute_탭_네비게이션_샘플코드.md` |
| RSA/AES 하이브리드 암호화 | `🐤 Flutter_RSA_AES_GCM_하이브리드암호화_샘플코드.md` |
| SSE 실시간 스트림 | `🐤 Flutter_SSE_실시간_스트림_구독_샘플코드.md` |
| Riverpod 비동기 상태관리 | `🐤 Flutter_Riverpod_비동기_상태관리_샘플코드.md` |
| Riverpod 코드생성 + CRUD | `🐤 Flutter_Riverpod_코드생성_NotifierProvider_CRUD_샘플코드.md` |
| Sealed AuthState + KeepAlive | `🐤 Flutter_Sealed_AuthState_Riverpod_KeepAlive_인증_샘플코드.md` |
| ConsumerStatefulWidget CRUD | `🐤 Flutter_ConsumerStatefulWidget_CRUD_화면_샘플코드.md` |
| 페이지네이션 FutureProvider.family | `🐤 Flutter_Repository_FutureProvider_Family_PageResponse_페이지네이션_샘플코드.md` |
| Dart 3 Record 반환 NotifierProvider | `🐤 Flutter_Dart3_Record_반환_NotifierProvider_샘플코드.md` |
| Certificate Pinning / TLS 보안 | `🐤 Flutter_Certificate_Pinning_TLS_보안_샘플코드.md` |
| 지수 백오프 재시도 | `🐤 Flutter_API_Client_지수백오프_재시도_샘플코드.md` |
| 리치텍스트 에디터 | `🐤 Flutter_AppFlowyEditor_리치텍스트_에디터_통합_샘플코드.md` |

### Spring Boot 4 대표 패턴 (devpath-*-svc, devpath-gateway 활용)

| 패턴 | 파일명 (Study-docs: `Sample Codes/`) |
|------|--------------------------------------|
| Redisson 분산락 | `🐤 Spring_Boot_4_Redisson_분산락_샘플코드.md` |
| DistributedLock AOP Annotation | `🐤 Spring_Boot_4_DistributedLock_AOP_Annotation_변형_샘플코드.md` |
| Redis 분산세션 Pub/Sub | `🐤 Spring_Boot_4_Redis_분산세션_Pub_Sub_샘플코드.md` |
| Outbox + Kafka | `🐤 Spring_Boot_4_ApplicationModuleListener_Outbox_Kafka_변형_샘플코드.md` |
| SSE 스트리밍 | `🐤 Spring_Boot_4_FastAPI_SSE_스트리밍_샘플코드.md` |
| JWT RSA 하이브리드 암호화 | `🐤 Spring_Boot_4_JWT_RSA_하이브리드암호화_샘플코드.md` |
| JWT Nimbus JOSE JWE | `🐤 Spring_Boot_4_JWT_RSA_Nimbus_JOSE_JWE_변형_샘플코드.md` |
| PostgreSQL RLS | `🐤 Spring_Boot_4_PostgreSQL_RLS_Row_Level_Security_샘플코드.md` |
| CQRS Command/Query Handler 분리 | `🐤 Spring_Boot_4_CQRS_Command_Query_Handler_분리_샘플코드.md` |
| CQRS QueryDSL Projection | `🐤 Spring_Boot_4_CQRS_Query_Port_QueryDSL_Projection_샘플코드.md` |
| DDD Aggregate 설계패턴 | `🐤 Spring_Boot_4_DDD_Aggregate_설계패턴_샘플코드.md` |
| ArchUnit 계층경계 자동검증 | `🐤 Spring_Boot_4_ArchUnit_계층경계_자동검증_샘플코드.md` |
| Kafka Avro Producer/Consumer | `🐤 Spring_Boot_4_Kafka_Avro_Producer_Consumer_샘플코드.md` |
| Kafka Dead Letter Queue | `🐤 Spring_Boot_4_Kafka_Dead_Letter_Queue_처리_샘플코드.md` |
| Domain Event 발행구독 | `🐤 Spring_Boot_4_Domain_Event_발행구독_샘플코드.md` |
| Audit Trail 필드변경추적 | `🐤 Spring_Boot_4_Audit_Trail_필드변경추적_샘플코드.md` |

### React / Python (참고용)

dev-path-ai는 React·Python 백엔드를 사용하지 않지만, 알고리즘 패턴 참고용으로 보관한다.

- React TS: 15개 (`React_TS_*`) — Axios 인터셉터, JWT 자동갱신, SSE, 암호화, Context/Hook 패턴 등
- Python FastAPI: 6개 (`Python_*`) — OAuth2 JWT, RAG 하이브리드검색, 비동기 엔드포인트 등

---

## ④ 레이어3 — Dockerfile 매핑

Study-docs: `Dockerfile/` 하위 실재 확인된 디렉토리:

| 디렉토리 | 활용 레포 / 용도 |
|----------|-----------------|
| `Dockerfile/Spring/` | devpath-*-svc, devpath-gateway — 백엔드 서비스 이미지 |
| `Dockerfile/Flutter/` | devpath-frontend — Flutter Web/App 빌드 이미지 |
| `Dockerfile/Postgresql/` | devpath-shared, devpath-gitops — 로컬 DB 컨테이너 |
| `Dockerfile/Redis/` | devpath-shared, devpath-gitops — 로컬 캐시 컨테이너 |
| `Dockerfile/Mysql/` | 참고용 (dev-path-ai는 PostgreSQL 사용) |
| `Dockerfile/Ollama/` | 참고용 (LLM 로컬 서버) |
| `Dockerfile/Python/` | 참고용 (Python 서비스) |
| `Dockerfile/React/` | 참고용 (React 프론트엔드) |
| `Dockerfile/base/` | 베이스 이미지 레이어 참조 |
| `Dockerfile/fullstack/` | 풀스택 로컬 개발 환경 참조 |

> 참고: `Dockerfile/hub-overviews/`, `Dockerfile/scripts/`, `Dockerfile/docker-compose.example.yml` 도 동일 디렉토리에 존재함.

---

## ⑤ 레이어4 — 가이드 문서 매핑

Study-docs 루트 직속 가이드 파일(실재 확인):

| 가이드 파일 | 참조 시점 / 적용 레포 |
|------------|----------------------|
| `🎩 Flutter-Riverpod-guide.md` | devpath-frontend Riverpod 상태관리 설계 전반 |
| `🎩 Flutter-Riverpod-3.0-마이그레이션-매뉴얼.md` | flutter_riverpod ^3.x 마이그레이션 시 |
| `🎩 Flutter-go_router-14-17-마이그레이션-매뉴얼.md` | go_router ^14 → 상위 버전 마이그레이션 시 |
| `🎩 Flutter-Async-Future-Stream-Riverpod.md` | Flutter 비동기 패턴 설계 시 |
| `🎩 Flutter-외부패키지-메이저버전-마이그레이션-매뉴얼.md` | Flutter 의존성 메이저 업그레이드 시 |
| `🦄 MSA_디자인_패턴_가이드.md` | devpath-gateway, 백엔드 svc 간 패턴 설계 시 |
| `🐣 CQRS 가이드.md` | devpath-ai-svc, learning-svc CQRS 도입·설계 시 |
| `🐣 Query-port-pattern.md` | QueryDSL Projection + Query Port 구현 시 |
| `🐙 Git-Workflow-Strict 가이드.md` | 전 레포 브랜치 전략·커밋 컨벤션 정비 시 |
| `📝 학습문서 작성 가이드.md` | study-documents Sample Codes 추가·수정 시 |
| `🎼 Kubernetes_배포_전략_가이드.md` | devpath-gitops Kubernetes 배포 전략 설계 시 |
| `🐳 Dockerfile 가이드.md` | Dockerfile 작성 참조 |
| `🐳 Docker 설치 및 운영 가이드.md` | 로컬 Docker 환경 구성 시 |

---

## ⑥ "언제 무엇을" — 시나리오 인덱스

작업 시작 전 이 표를 보고 필요한 자산을 한 번에 찾는다.

| 작업 시나리오 | 스킬 호출 | Sample Codes 참조 | 가이드 참조 |
|--------------|-----------|-------------------|-------------|
| **Flutter 401 Refresh 구현** | `/devpath-skillpack:flutter-setup` | `🐤 Flutter_Dio_Bearer_Auth_QueuedInterceptor_401_Refresh_샘플코드.md` | `🎩 Flutter-Riverpod-guide.md` |
| **GoRouter 인증 가드 설계** | `/devpath-skillpack:flutter-setup` | `🐤 Flutter_GoRouter_인증_리다이렉트_라우팅_샘플코드.md` + `🐤 Flutter_GoRouter_StatefulShellRoute_탭_네비게이션_샘플코드.md` | `🎩 Flutter-go_router-14-17-마이그레이션-매뉴얼.md` |
| **Spring Redisson 분산락 구현** | `/devpath-skillpack:spring-setup` + `/devpath-skillpack:domain-modeler` | `🐤 Spring_Boot_4_Redisson_분산락_샘플코드.md` + `🐤 Spring_Boot_4_DistributedLock_AOP_Annotation_변형_샘플코드.md` | `🦄 MSA_디자인_패턴_가이드.md` |
| **Spring SSE 스트리밍 API 구현** | `/devpath-skillpack:spring-setup` | `🐤 Spring_Boot_4_FastAPI_SSE_스트리밍_샘플코드.md` | — |
| **Spring CQRS 도입** | `/devpath-skillpack:domain-modeler` + `/devpath-skillpack:brooks-lint-arch` | `🐤 Spring_Boot_4_CQRS_Command_Query_Handler_분리_샘플코드.md` + `🐤 Spring_Boot_4_CQRS_Query_Port_QueryDSL_Projection_샘플코드.md` | `🐣 CQRS 가이드.md` + `🐣 Query-port-pattern.md` |
| **Spring Kafka Outbox 패턴** | `/devpath-skillpack:spring-setup` + `/devpath-skillpack:domain-modeler` | `🐤 Spring_Boot_4_ApplicationModuleListener_Outbox_Kafka_변형_샘플코드.md` + `🐤 Spring_Boot_4_Domain_Event_발행구독_샘플코드.md` | `🦄 MSA_디자인_패턴_가이드.md` |
| **Flutter 암호화 (RSA/AES) 구현** | `/devpath-skillpack:flutter-setup` | `🐤 Flutter_RSA_AES_GCM_하이브리드암호화_샘플코드.md` | — |
| **Spring PostgreSQL RLS 설정** | `/devpath-skillpack:postgres-mcp-tuner` | `🐤 Spring_Boot_4_PostgreSQL_RLS_Row_Level_Security_샘플코드.md` | — |
| **Spring 보안 취약점 스캔** | `/devpath-skillpack:semgrep-scanner` + `/devpath-skillpack:sonatype-checker` | `🐤 Spring_Boot_4_JWT_RSA_하이브리드암호화_샘플코드.md` (검증 대상 예시) | — |
| **Flutter Riverpod 3.x 상태관리 설계** | `/devpath-skillpack:flutter-setup` + `/devpath-skillpack:dart-flutter-lint-check` | `🐤 Flutter_Riverpod_비동기_상태관리_샘플코드.md` + `🐤 Flutter_Riverpod_코드생성_NotifierProvider_CRUD_샘플코드.md` | `🎩 Flutter-Riverpod-3.0-마이그레이션-매뉴얼.md` + `🎩 Flutter-Async-Future-Stream-Riverpod.md` |
| **신규 서비스 도메인 모델링** | `/devpath-skillpack:domain-modeler` + `/devpath-skillpack:deep-interview` | `🐤 Spring_Boot_4_DDD_Aggregate_설계패턴_샘플코드.md` | `🦄 MSA_디자인_패턴_가이드.md` |
| **CI Dockerfile / compose 정비** | `/devpath-skillpack:dockerfile-builder` + `/devpath-skillpack:docker-compose-infra` | — | `🐳 Dockerfile 가이드.md` + `Dockerfile/Spring/`, `Dockerfile/Flutter/` |

---

## ⑦ 경로 유효성 검증

### 검증 방법

이 카탈로그가 참조하는 study-documents 경로는 작성 시점(2026-06-22) 실측으로 모두 존재를 확인했다. 향후 카탈로그 갱신 시 아래 명령으로 재검증한다.

```bash
# 스킬 26개 SKILL.md 존재 확인
for skill in spring-setup flutter-setup dockerfile-builder docker-compose-infra \
  code-reviewer complexity-analyzer error-detective test-coverage-booster \
  dart-flutter-lint-check context-harness harness-doctor eval-builder \
  context7-helper code-review-multiagent semgrep-scanner sonatype-checker \
  brooks-lint-arch vercel-grep-helper deepwiki-helper flutter-pubdev-helper \
  postgres-mcp-tuner domain-modeler readme-generator deep-interview \
  deep-init sample-code-builder; do
  f="D:/workspace/develop-study-documents/Skillbook/$skill/SKILL.md"
  [ -f "$f" ] && echo "OK: $skill" || echo "MISSING: $skill"
done

# Sample Codes 총 수 확인 (149 이상이어야 함)
ls "D:/workspace/develop-study-documents/Sample Codes/" | wc -l

# Dockerfile 디렉토리 확인
ls "D:/workspace/develop-study-documents/Dockerfile/"

# 가이드 파일 존재 확인
ls "D:/workspace/develop-study-documents/"*.md | grep -E "Flutter-Riverpod|MSA_디자인|CQRS|Git-Workflow|학습문서"
```

### 작성 시점 검증 결과 요약

| 자산 | 검증 결과 |
|------|-----------|
| 스킬 26개 SKILL.md | 전부 OK (26/26) |
| Sample Codes 파일 수 | 150개 확인 (149 콘텐츠 + 1 `_audit` 디렉토리) |
| Flutter 샘플 | 47개 확인 |
| Spring 샘플 | 80개 확인 |
| React 샘플 | 15개 확인 |
| Python 샘플 | 6개 확인 |
| Dockerfile 디렉토리 | Spring·Flutter·Postgresql·Redis·Mysql·Ollama·Python·React·base·fullstack 확인 |
| 루트 가이드 파일 | Flutter-Riverpod·MSA·CQRS·Git-Workflow·학습문서 가이드 존재 확인 |
| devpath-frontend 실측 패키지 | `flutter_riverpod ^3.3.0`, `go_router ^14.6.0`, `dio ^5.0.0`, Dart SDK `^3.12.1` |

> 📌 **스킬 설치·트리거 검증은 별도 Task에서 수행 예정**이다. 이 카탈로그는 경로 인덱싱 역할만 한다.

---

## 부록 B — deep-init 스킬 참고

`deep-init` 스킬의 SKILL.md 내 `name` 필드가 `deepinit`으로 등록되어 있다. 호출 시 `/devpath-skillpack:deep-init`을 우선 시도하고, 플러그인 빌드 결과에 따라 `/devpath-skillpack:deepinit`으로 대체될 수 있다. 별도 Task 검증 시 확인한다.

---

*이 문서는 `docs/study-documents-integration` 브랜치에서 작성되었으며, develop PR 머지 후 전 팀에 공유된다.*
