> ⚠️ **아카이브 — 구버전 참고 설계** · 본 문서의 MySQL·LearnFlow 등 표기는 현행과 다릅니다. 현 SSOT는 **PostgreSQL**, 제품명은 **DevPath AI**입니다. (2026-06-13 정합성 점검 — [25_문서_정합성_점검_보고서](./25_문서_정합성_점검_보고서.md))

> **프로젝트명**: LearnFlow AI — AI 기반 적응형 학습 관리 시스템 + 개인 학습 인프라
> **버전**: v5.0 완전 통합본 (v1.0~v4.0 전체 상세 + v5.0 확장 모두 포함)
> **통합 작업**: 2026-04-22 — v5.0 원본의 축약 섹션에 v4.0 원본 세부 내용 병합
> **작성일**: 2026-04-21
> **기술 스택**: Spring Boot 4 + React 18 + Flutter 3.x + LLM API + pgvector
> **버전 이력**: v1.0(기반) → v2.0(AI 서비스 분리, RAG) → v3.0(Outbox, RAGAS, PII, FinOps) → v4.0(3층 평가, Semantic Chunking, Output PII, OTel) → **v5.0(Flashcard SRS + Obsidian Lite + Cross-module Synergy)**

---

## 📋 v5.0 핵심 확장 요약

v5.0은 v4.0 인프라를 재활용해 **학습 경험의 입력-처리-내재화 사이클을 완결**시키는 버전입니다.

```
v4.0: [강의 수강] → [AI 튜터 질의응답] → [퀴즈/과제 채점] (외부 학습 콘텐츠 소비)
                            ↓
v5.0: + [개인 노트 작성] → [플래시카드 복습] → [장기 기억화]
       (개인 지식 내재화 사이클 완결)

                   [강의 콘텐츠]
                         │
                         ▼
                   [개인 노트 작성] ──┐
                         │           │
                         ▼           │
                   [플래시카드 생성]  │
                         │           │
                         ▼           ▼
                   [SM-2 복습] ← [AI 튜터 참조]
                         │
                         ▼
                   [concept_mastery 갱신]
                         │
                         ▼
                   [적응형 추천 고도화]
```

### v4.0 → v5.0 변경 요약

| 영역 | v4.0 | v5.0 |
|------|------|------|
| 마이크로서비스 | AI Gateway + 4 서브서비스 | **+ Knowledge Service (Flashcard + Note 통합)** |
| 학습 사이클 | 강의 → 튜터 → 퀴즈 | + **노트 작성 → 플래시카드 → 장기 복습** |
| AI 튜터 Long-term Memory | concept_mastery + 오답 이력 | + **개인 노트 RAG 컨텍스트 주입** |
| 플래시카드 | LLM 생성 엔드포인트만 존재 | **SM-2 알고리즘 + 복습 큐 + Bloom 가중치 연동** |
| 개인 지식 관리 | 없음 | **Obsidian Lite (마크다운 + [[wiki-link]] + 그래프 뷰 + pgvector 의미 검색)** |
| 데이터 네트워크 효과 | 없음 | **사용자 노트/카드 축적 → 개인화 품질 향상 플라이휠** |
| Vector DB 스케일링 | 강의 콘텐츠만 | + **개인 노트 임베딩 (RLS 권한 격리)** |
| FinOps | 강의 단위 | + **사용자별 임베딩 한도 + 무료/유료 플랜 분리** |
| 모바일 UX | 강의 수강 + AI 튜터 | + **자투리 시간 플래시카드 복습 + 퀵 노트 캡처** |
| 교차 시너지 | - | **노트 → 카드 자동 생성, 카드 답 → 관련 노트 추천** |

---

## 1. 프로젝트 개요

### 1.1 프로젝트 배경

기존 LMS는 강의 콘텐츠를 일방향으로 제공하는 데 그쳤고, v4.0에서 적응형 학습·AI 튜터·자동 채점까지 고도화했다.
그러나 **학습자가 강의에서 습득한 지식을 자기 것으로 만드는 단계(필기 → 복습 → 장기 기억화)** 는 여전히 외부 도구(Notion, Obsidian, Anki)에 의존해야 했다.

v5.0은 이 공백을 메운다. LearnFlow AI 인프라 위에 **Spaced Repetition 기반 플래시카드**와 **개인 지식 그래프**를 서브 모듈로 통합하여, 학습의 입력부터 장기 기억화까지 하나의 플랫폼에서 처리한다. 특히 AI 튜터가 학습자의 개인 노트를 Long-term Memory로 참조함으로써, **사용자 데이터가 쌓일수록 AI 개인화 품질이 높아지는 데이터 네트워크 효과**를 확보한다.

### 1.2 프로젝트 목표

```
┌─────────────────────────────────────────────────────────────────┐
│                  LearnFlow AI v5.0 핵심 목표                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ① 적응형 학습    : 학습자 수준에 맞는 콘텐츠 자동 조정          │
│  ② AI 튜터       : LLM 기반 실시간 질의응답 + 개인 노트 참조     │
│  ③ 자동 평가     : AI 퀴즈/과제 자동 생성 및 채점                │
│  ④ 학습 분석     : 취약점 분석, 학습 패턴 시각화, 추천           │
│  ⑤ 협업 학습     : 스터디 그룹, 토론, 피어 리뷰                  │
│  ⑥ AI 품질 관리  : 3층 평가, A/B 테스트, 지속 개선               │
│  ⑦ 프로덕션 안정성: Outbox, 분산 추적, Chaos Testing            │
│  ⑧ 컴플라이언스  : PII 양방향 보호, 감사 추적, 신뢰 채점         │
│  ⑨ FinOps       : Unit Economics, 동적 라우팅, Semantic Cache   │
│  ⑩ 장기 기억화   : SM-2 기반 플래시카드 + Bloom 가중 스케줄링    │  ← v5.0
│  ⑪ 개인 지식 그래프: 마크다운 + 위키링크 + 의미 검색 + 그래프 뷰  │  ← v5.0
│  ⑫ 데이터 플라이휠: 노트/카드 축적 → AI 개인화 품질 향상         │  ← v5.0
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 대상 사용자

| 역할 | 설명 | 주요 기능 |
|------|------|-----------|
| **학습자 (Learner)** | 강의 수강 + 개인 학습 자산 관리 | 수강, AI 튜터, 퀴즈, 학습 분석, **노트 작성, 카드 복습** |
| **강사 (Instructor)** | 강의 생성 및 관리 | 강의 관리, 과제 출제, 수강생 분석, Manual Review Queue |
| **관리자 (Admin)** | 시스템 운영 | 사용자 관리, AI 품질, FinOps, 분산 추적, 감사 로그 |

---

## 2. 시스템 아키텍처

### 2.1 전체 아키텍처 (v5.0)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Client Layer                                   │
│                                                                          │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐       │
│   │  React 18    │    │ Flutter 3.x  │    │  Admin Dashboard     │       │
│   │  (Web SPA)   │    │ (Mobile App) │    │  (React)             │       │
│   │              │    │              │    │                      │       │
│   │ 강의/튜터    │    │ 강의/튜터    │    │ AI 품질/FinOps/      │       │
│   │ 노트/그래프  │    │ 카드복습     │    │ Knowledge Stats      │       │
│   │ 카드 편집    │    │ 퀵노트캡처   │    │                      │       │
│   └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘       │
└──────────┼───────────────────┼───────────────────────┼───────────────────┘
           └───────────────────┼───────────────────────┘
                               │
                        ┌──────▼──────┐
                        │  API Gateway │ ← Spring Cloud Gateway
                        │  + Trace ID  │ ← OTel Sampling 10~30%
                        └──────┬──────┘
                               │
  ┌────────────────┬───────────┼──────────────┬─────────────────┐
  │                │           │              │                 │
┌─▼──────┐  ┌─────▼────┐ ┌────▼─────┐ ┌──────▼──────┐ ┌────────▼─────────┐
│ 학습    │  │ 사용자    │ │ AI       │ │ Knowledge    │ │ Analytics        │
│ 서비스  │  │ 서비스    │ │ Gateway  │ │ Service      │ │ Worker           │
│(Course)│  │(Auth)    │ │(Orchstr) │ │(v5.0 신규)   │ │ (concept_mastery)│
└─┬──────┘  └────┬─────┘ └──┬───────┘ └──────┬───────┘ └──────────────────┘
  │              │          │                │
  │              │   ┌──────┴──────┐         │
  │              │   │ PII Masking │         │
  │              │   │ Layer       │         │
  │              │   └──┬──────────┘         │
  │              │      │                    │
  │              │   ┌──┴──────┬─────┬─────┬──────┐
  │              │ ┌─▼──┐ ┌───▼──┐ ┌▼───┐ ┌▼────┐
  │              │ │LLM │ │Embed │ │RAG │ │Eval │
  │              │ │Svc │ │Svc   │ │Svc │ │Svc  │
  │              │ └────┘ └──────┘ └────┘ └─────┘
  │              │
  ▼              ▼
MySQL (Source of Truth)  ─ courses, users, notes, flashcards, reviews
Redis (Session/Cache)    ─ short-term memory, rate limit, card due queue
pgvector                 ─ content_embeddings (ACTIVE), note_embeddings (ACL)
Elasticsearch (BM25)     ─ hybrid search corpus (courses + notes)
Kafka (Event Bus)        ─ Outbox → FlashcardReviewed, NoteCreated, ...
```

**v5.0 아키텍처 핵심 변경점:**

1. **Knowledge Service 신설**: 플래시카드(SM-2)와 개인 노트(Obsidian Lite)를 하나의 마이크로서비스로 묶음. 두 기능이 데이터 모델(노트 → 카드 생성)과 사용자 소유권(user_id 기반 권한) 측면에서 강하게 결합되어 있어 분리보다 통합이 운영에 유리.
2. **pgvector 이중 테이블**: `content_embeddings`(공용 강의 콘텐츠) + `note_embeddings`(개인 소유, RLS 적용)로 분리. 권한 누수 리스크 원천 차단.
3. **RAG Service 재사용**: 동일한 Query Rewrite + Hybrid Search + Re-ranking 파이프라인이 `source_filter` 파라미터(`COURSE` / `NOTE` / `BOTH`)로 검색 범위만 제어하여 두 도메인에 공통 적용.
4. **Long-term Memory 확장**: AI 튜터가 concept_mastery뿐 아니라 사용자의 개인 노트 중 질의와 의미적으로 유사한 조각을 컨텍스트에 주입.

### 2.2 AI 서비스 분리 (v5.0 확장)

```
┌─────────────────────────────────────────────────────────────────┐
│  AI Gateway (Orchestrator)                                      │
│  ├── 요청 라우팅 + 모델 선택 (4분류 + 예산 동적 라우팅)          │
│  ├── PII Masking 전처리/후처리 (Input + Output 양방향)           │
│  ├── Rate Limiting + 토큰 관리                                   │
│  ├── FinOps Kill-switch (Unit Economics 연동)                    │
│  ├── Circuit Breaker + Fallback (Resilience4j)                   │
│  └── Trace ID 전파 (OTel, Sampling 10~30%, 에러 100%)            │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ LLM      │ │ Embedding│ │ RAG      │ │Evaluation│           │
│  │ Service  │ │ Service  │ │ Service  │ │ Service  │           │
│  │          │ │          │ │          │ │          │           │
│  │ • Chat   │ │ • 강의벡터│ │ • 검색   │ │ • 퀴즈생성│           │
│  │ • Tutor  │ │ • 노트벡터│ │ • Re-rank│ │ • 채점   │           │
│  │ • 요약   │ │ • Semantic│ │ • 압축   │ │ • Conf.  │           │
│  │ • 카드생성│ │   Chunk  │ │ • source │ │          │           │
│  │ (v5.0)  │ │  (v5.0)  │ │  filter  │ │          │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Transactional Outbox Pattern (유지)

```
┌─────────────────────────────────────────────────────────────────┐
│  @Transactional (하나의 DB 트랜잭션)                             │
│  ├── ① 비즈니스 데이터 저장 (MySQL)                              │
│  └── ② outbox_events INSERT (같은 트랜잭션)                      │
│                                                                 │
│  Outbox Relay (Debezium CDC or Polling):                        │
│  outbox_events → Kafka (destination_topic별 라우팅)              │
│                                                                 │
│  Consumer 멱등성 (Holy Trinity):                                │
│  ├── dedup_key 체크 (aggregate_id + event_type + version)       │
│  ├── Version OCC (Read Model) / dedup_key (알림/AI)             │
│  └── DLQ: Relay 5회 실패 → DEAD_LETTER, Consumer 3회 → DLQ 토픽 │
│                                                                 │
│  Polling vs CDC:                                                │
│  Phase 1: Polling + ShedLock                                    │
│  Phase 2: Debezium CDC (Scale 시 binlog 기반 실시간 전환)        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 이벤트 목록 (v5.0 확장)

| 이벤트 | Producer | Consumer | 처리 |
|--------|----------|----------|------|
| `ContentCreated` | 학습 서비스 (Outbox) | Embedding Worker | 청킹 + 강의 임베딩 |
| `ContentUpdated` | 학습 서비스 (Outbox) | Embedding Worker | chunk_hash 비교 → 변경분만 |
| `ContentDeleted` | 학습 서비스 (Outbox) | Embedding Worker | INACTIVE 처리 |
| `QuizSubmitted` | 퀴즈 서비스 (Outbox) | AI Grading Worker | 자동 채점 |
| `AssignmentSubmitted` | 과제 서비스 (Outbox) | AI Grading Worker | 과제 AI 채점 |
| `GradingAppeal` | 퀴즈/과제 서비스 | Notification | 강사 Manual Review Queue |
| `LessonCompleted` | 학습 서비스 (Outbox) | Analytics Worker | 진도/취약점 갱신 |
| `CostThresholdReached` | FinOps Monitor | Admin Notification | 비용 경고 |
| **`NoteCreated`** (v5.0) | Knowledge Service (Outbox) | Embedding Worker | 노트 청킹 + 개인 임베딩 |
| **`NoteUpdated`** (v5.0) | Knowledge Service (Outbox) | Embedding Worker | chunk_hash diff → 재임베딩 |
| **`NoteLinked`** (v5.0) | Knowledge Service (Outbox) | Graph Builder | 그래프 캐시 갱신 |
| **`FlashcardGenerated`** (v5.0) | Knowledge Service (Outbox) | Notification | 덱에 새 카드 알림 |
| **`FlashcardReviewed`** (v5.0) | Knowledge Service (Outbox) | Analytics Worker | concept_mastery 실시간 갱신 |
| **`CardBatchDue`** (v5.0) | Scheduler (cron) | Notification/Push | 복습 시간 알림 |

### 2.5 Distributed Tracing (OTel, 유지 + v5.0 추가 Span)

```
┌─────────────────────────────────────────────────────────────────┐
│  Sampling: dev 100% / staging 50% / prod 10~30%                 │
│  예외: 5xx 에러 → 100%, AI API 호출 → 100%                      │
│                                                                 │
│  v5.0 추가 Span Attributes:                                     │
│  knowledge.source_type (COURSE/NOTE), knowledge.note_id,        │
│  flashcard.deck_id, flashcard.sm2.interval, flashcard.quality,  │
│  graph.node_count, graph.edge_count                             │
│                                                                 │
│  Trace 예시 (AI 튜터 with 개인 노트 참조):                       │
│  API Gateway(2ms) → AI Gateway → PII Masking(5ms)              │
│  → RAG Service: Query Rewrite(120ms)                            │
│    + Hybrid Search: course(85ms) || note(70ms) 병렬             │
│    + Re-ranking(200ms) + Compression(30ms)                      │
│  → LLM Service: Prompt(15ms) + LLM API(1800ms)                  │
│  → PII Demasking(3ms)                                           │
│  Total: ~2335ms                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 기술 스택

### 3.1 Backend

| 영역 | 기술 | 버전 | 용도 |
|------|------|------|------|
| Framework | Spring Boot | 4.x | 메인 애플리케이션 |
| Language | Java | 21+ | Virtual Threads |
| ORM | Spring Data JPA + QueryDSL | 5.x | 데이터 접근 |
| Security | Spring Security | 7.x | JWT + **Row-level Security (노트)** |
| API 문서 | SpringDoc OpenAPI | 2.x | Swagger UI |
| Build | Gradle | 8.x | Kotlin DSL |
| DB | MySQL | 8.x | Source of Truth |
| Cache | Redis | 7.x | 세션, 캐시, **Card Due Queue (Sorted Set)** |
| 메시징 | Kafka | - | 이벤트 기반 비동기 |
| CDC | Debezium | 2.x | Outbox → Kafka 릴레이 |
| 검색 | Elasticsearch | 8.x | BM25 Hybrid (courses + notes) |
| 스토리지 | MinIO / AWS S3 | - | 파일 저장 |
| Resilience | Resilience4j | - | Circuit Breaker |
| Tracing | Micrometer + OTel | - | 분산 추적 |
| PII | Presidio + KoNLPy | - | 개인정보 마스킹 |
| DB 마이그레이션 | Flyway | - | 스키마 버전 관리 |
| **Markdown Parser** (v5.0) | **Flexmark-java** | 0.64.x | **[[wiki-link]] 추출, AST 기반 백링크** |
| **Scheduler** (v5.0) | **Quartz + ShedLock** | - | **카드 복습 알림 배치** |

### 3.2 AI / LLM

| 영역 | 기술 | 용도 |
|------|------|------|
| LLM API | Claude API (Anthropic) | 메인 AI 엔진 |
| Fallback | OpenAI GPT API | 보조 LLM |
| Embedding | text-embedding-3-small | 강의 + 노트 임베딩 |
| Vector DB | pgvector (Phase 1) → Qdrant (Phase 2) | `content_embeddings` + `note_embeddings` |
| Re-ranking | CrossEncoder (ms-marco) | 검색 결과 재정렬 |
| RAG 평가 | RAGAS + DeepEval | 자동 품질 평가 |
| Prompt 관리 | 자체 Template Engine | 프롬프트 버전 관리 |

### 3.3 Frontend

| 영역 | 기술 | 용도 |
|------|------|------|
| Web | React 18 + TypeScript | SPA 웹 클라이언트 |
| 상태 | Zustand + TanStack Query | 상태 + API 캐싱 |
| UI | shadcn/ui + Tailwind CSS | 컴포넌트 |
| 차트 | Recharts | 학습 분석 시각화 |
| 에디터 | TipTap | 마크다운/리치텍스트 (강의 노트 + 개인 노트 공용) |
| **그래프 시각화** (v5.0) | **React Flow + D3-force** | **노트 그래프 뷰 (force-directed)** |
| **Markdown 렌더** (v5.0) | **react-markdown + remark-wiki-link** | **위키링크 [[note]] 렌더링** |
| **카드 애니메이션** (v5.0) | **Framer Motion** | **플래시카드 뒤집기 UX** |
| Mobile | Flutter 3.x + Riverpod | 크로스플랫폼 모바일 |
| **모바일 그래프** (v5.0) | **Flutter CustomPainter + force_directed_graph_flutter** | **간소화된 그래프 뷰** |

### 3.4 인프라

| 영역 | 기술 | 용도 |
|------|------|------|
| 컨테이너 | Docker + Docker Compose | 개발/배포 |
| CI/CD | GitHub Actions | 자동 빌드/배포 |
| 모니터링 | Prometheus + Grafana | 시스템 + AI + FinOps + **Knowledge 대시보드** |
| 분산 추적 | Zipkin (OTel) | 서비스 간 추적 |
| CDC | Debezium | Outbox 릴레이 |
| **푸시 알림** (v5.0) | **FCM (Firebase Cloud Messaging)** | **복습 알림 (모바일)** |

---

## 4. ERD 설계 (전체)

### 4.1 사용자 도메인

```
┌──────────────────────┐       ┌──────────────────────┐
│       users           │       │    user_profiles      │
├──────────────────────┤       ├──────────────────────┤
│ PK  id        BIGINT │───┐   │ PK  id        BIGINT │
│     email     VARCHAR│   │   │ FK  user_id   BIGINT │
│     password  VARCHAR│   │   │     nickname  VARCHAR│
│     role      ENUM   │   │   │     avatar    VARCHAR│
│     status    ENUM   │   │   │     bio       TEXT   │
│     created_at DATETIME│  │   │     level     INT    │
│     updated_at DATETIME│  │   │     exp_point INT    │
└──────────────────────┘   │   └──────────────────────┘
                           │
                           │   ┌──────────────────────┐
                           └──→│  user_learning_prefs  │
                               │     preferred_pace ENUM│
                               │     daily_goal_min INT │
                               │     interests   JSON  │
                               │     difficulty  ENUM  │
                               └──────────────────────┘
```

### 4.2 강의 도메인

```
┌──────────────────────┐       ┌──────────────────────┐
│      courses          │       │      sections         │
├──────────────────────┤       ├──────────────────────┤
│ PK  id        BIGINT │───┐   │ PK  id        BIGINT │
│ FK  instructor_id    │   │   │ FK  course_id BIGINT │
│     title     VARCHAR│   │   │     title     VARCHAR│
│     description TEXT  │   │   │     order_num INT    │
│     category  VARCHAR│   │   └──────────┬───────────┘
│     level     ENUM   │   │              │
│     thumbnail VARCHAR│   │   ┌──────────▼───────────┐
│     price     DECIMAL│   │   │      lessons          │
│     status    ENUM   │   │   │ PK  id        BIGINT │
│     avg_rating DECIMAL│  │   │ FK  section_id BIGINT│
│     created_at DATETIME│ │   │     title     VARCHAR│
└──────────────────────┘   │   │     type      ENUM   │
                           │   │     content   TEXT   │
                           │   │     video_url VARCHAR│
                           │   │     duration_min INT │
                           │   │     order_num INT    │
                           │   └──────────────────────┘
                           │
                           │   ┌──────────────────────┐
                           └──→│    enrollments        │
                               │ FK  user_id   BIGINT │
                               │ FK  course_id BIGINT │
                               │     status    ENUM   │
                               │     progress  DECIMAL│
                               │     enrolled_at DATETIME│
                               │     completed_at DATETIME│
                               └──────────────────────┘
```

### 4.3 AI 채팅 도메인

```
┌──────────────────────┐       ┌──────────────────────────┐
│    ai_chat_sessions   │       │    ai_chat_messages       │
├──────────────────────┤       ├──────────────────────────┤
│ PK  id        BIGINT │───┐   │ PK  id          BIGINT   │
│ FK  user_id   BIGINT │   │   │ FK  session_id  BIGINT   │
│ FK  course_id BIGINT │   │   │     role        ENUM     │
│     title     VARCHAR│   └──▶│     content     TEXT     │
│     context   JSON   │       │     token_used  INT      │
│     created_at DATETIME│     │     feedback    ENUM     │ (GOOD/BAD/null)
└──────────────────────┘       │     model_used  VARCHAR  │
                               │     created_at  DATETIME │
                               └──────────────────────────┘
```

### 4.4 퀴즈/과제 도메인

```
┌──────────────────────┐       ┌──────────────────────┐
│       quizzes         │       │    quiz_questions     │
├──────────────────────┤       ├──────────────────────┤
│ PK  id        BIGINT │──┐    │ PK  id        BIGINT │
│ FK  lesson_id BIGINT │  │    │ FK  quiz_id   BIGINT │
│     title     VARCHAR│  │    │     question   TEXT   │
│     difficulty ENUM  │  └──▶ │     type       ENUM  │
│     ai_generated BOOL│       │     options    JSON   │
│     prompt_ver VARCHAR│      │     answer     TEXT   │
│     created_at DATETIME│     │     explanation TEXT  │
└──────────────────────┘       │     bloom_level ENUM  │
                               └──────────────────────┘

┌──────────────────────────────────┐
│   quiz_attempts                   │
├──────────────────────────────────┤
│ FK  user_id, quiz_id             │
│     score          DECIMAL       │
│     answers        JSON          │
│     ai_feedback    TEXT          │
│     started_at, submitted_at     │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│   assignment_submissions          │
├──────────────────────────────────┤
│ FK  assignment_id, user_id       │
│     content        TEXT          │
│     ai_score       DECIMAL       │
│     ai_confidence  DECIMAL       │  ← Confidence Score
│     ai_feedback    TEXT          │
│     instructor_score DECIMAL     │
│     instructor_feedback TEXT     │
│     status         ENUM         │  SUBMITTED → AI_GRADED
│                                  │  → CONFIRMED / APPEALED / MANUAL_REVIEW
│     appeal_reason  TEXT          │
│     appeal_at      DATETIME     │
│     reviewed_at    DATETIME     │
└──────────────────────────────────┘
```

### 4.5 학습 분석 도메인

```
┌──────────────────────┐       ┌──────────────────────────┐
│  learning_activities  │       │  concept_mastery          │
├──────────────────────┤       ├──────────────────────────┤
│ FK  user_id, lesson_id│       │ FK  user_id, course_id   │
│     activity_type ENUM│       │     concept      VARCHAR │
│     duration_sec INT │       │     mastery_score DECIMAL│
│     completed  BOOL  │       │     confidence   DECIMAL │ ← v4.0
│     created_at DATETIME│     │     source       ENUM    │ (DIAGNOSTIC/QUIZ/MANUAL)
└──────────────────────┘       │     attempt_count INT    │
                               │     last_updated  DATETIME│
┌──────────────────────┐       └──────────────────────────┘
│  weakness_analyses    │
├──────────────────────┤
│ FK  user_id, course_id│
│     topic     VARCHAR│
│     mastery_level DECIMAL│
│     suggestion TEXT  │
│     analyzed_at DATETIME│
└──────────────────────┘
```

### 4.6 임베딩 도메인

```
┌─────────────────────────────────────┐
│  content_embeddings                  │
├─────────────────────────────────────┤
│ PK  id            BIGINT           │
│ FK  course_id     BIGINT           │
│ FK  lesson_id     BIGINT           │
│     chunk_index   INT              │
│     chunk_text    TEXT             │
│     embedding     VECTOR(1536)     │  ← pgvector
│     token_count   INT              │
│     chunk_hash    VARCHAR          │  ← SHA-256 (v4.0: 중복 스킵)
│     metadata      JSONB            │  {section, page, timestamp, type}
│     chunking_strategy VARCHAR      │  (RECURSIVE, SEMANTIC, HYBRID)
│     version       INT              │
│     status        ENUM             │  ACTIVE / INACTIVE
│     last_modified_at DATETIME      │
│     created_at    DATETIME         │
│     updated_at    DATETIME         │
└─────────────────────────────────────┘
INDEX: HNSW on embedding WHERE status = 'ACTIVE'
INDEX: (course_id, lesson_id, status)
INDEX: (chunk_hash)
```

### 4.7 이벤트/운영 도메인

```
┌────────────────────────────────────┐
│  outbox_events                      │
├────────────────────────────────────┤
│ PK  id              BIGINT        │
│     aggregate_type  VARCHAR       │
│     aggregate_id    BIGINT        │
│     event_type      VARCHAR       │
│     dedup_key       VARCHAR UNIQUE│  ← aggregate_id+event_type+version
│     destination_topic VARCHAR     │  ← v4.0: 토픽별 라우팅
│     payload         JSON          │
│     status          ENUM          │  PENDING → PUBLISHED → CONSUMED
│     retry_count     INT           │
│     max_retries     INT DEFAULT 5 │
│     error_message   TEXT          │
│     created_at, published_at, consumed_at │
└────────────────────────────────────┘

┌──────────────────────────────────┐
│  audit_logs                       │
├──────────────────────────────────┤
│ FK  user_id                      │
│     action, entity_type, entity_id│
│     before_value JSON, after_value JSON│
│     ip_address, user_agent       │
│     created_at                   │
└──────────────────────────────────┘
```

### 4.8 AI 품질 관리 도메인

```
┌──────────────────────────┐       ┌──────────────────────────┐
│  ai_feedback_logs         │       │  prompt_versions          │
├──────────────────────────┤       ├──────────────────────────┤
│ FK  user_id, message_id  │       │     name, version         │
│     feedback ENUM (GOOD/BAD)│    │     template TEXT         │
│     comment  TEXT         │       │     is_active BOOL       │
│     created_at            │       │     created_at           │
└──────────────────────────┘       └──────────────────────────┘

┌──────────────────────────┐       ┌──────────────────────────┐
│  ab_tests                 │       │  ab_test_results          │
├──────────────────────────┤       ├──────────────────────────┤
│     name, variant_a/b JSON│      │ FK  test_id, user_id     │
│     target ENUM, status   │       │     variant ENUM (A/B)   │
│     start_date, end_date  │       │     feedback, latency_ms │
│                           │       │     token_used, mastery_delta│ ← v4.0
└──────────────────────────┘       └──────────────────────────┘

┌──────────────────────────┐
│  ragas_evaluations        │
├──────────────────────────┤
│ FK  message_id           │
│     context_precision    DECIMAL│
│     context_recall       DECIMAL│
│     faithfulness         DECIMAL│
│     answer_relevancy     DECIMAL│
│     deepeval_hallucination DECIMAL│ ← v4.0
│     overall_score        DECIMAL│
│     run_number           INT    │  ← v4.0: 3회 평가 중 몇 번째
│     evaluated_at         │
└──────────────────────────┘
```

### 4.9 FinOps 도메인

```
┌──────────────────────────────────┐
│  ai_cost_logs                     │
├──────────────────────────────────┤
│ FK  user_id                      │
│     service (TUTOR, QUIZ_GEN, GRADING, SUMMARY)│
│     model   VARCHAR              │
│     input_tokens, output_tokens INT│
│     cost_usd DECIMAL             │
│     cache_hit BOOL               │  ← v4.0: Semantic Cache 여부
│     created_at                   │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  cost_thresholds                  │
├──────────────────────────────────┤
│     period (DAILY/MONTHLY)       │
│     soft_limit_usd, hard_limit_usd│
│     current_usage_usd            │
│     is_killed BOOL               │
└──────────────────────────────────┘
```

### 4.10 온보딩 도메인

```
┌──────────────────────────────────┐       ┌──────────────────────────────┐
│  diagnostic_tests                 │       │  diagnostic_results           │
├──────────────────────────────────┤       ├──────────────────────────────┤
│ FK  course_id                    │───┐   │ FK  test_id, user_id         │
│     title, questions JSON        │   │   │     answers JSON              │
│     level_ranges JSON            │   └──▶│     diagnosed_level ENUM     │
│     bloom_distribution JSON      │ ←v4.0 │     concept_scores JSON      │
│     created_at                   │       │     confidence_weight DECIMAL│ ←v4.0
└──────────────────────────────────┘       │     taken_at                 │
                                           └──────────────────────────────┘
```

---

**▼ 이하 v5.0 확장 (v4.0 에 없던 하위 섹션)**

### 4.11 플래시카드 도메인 (v5.0 신규)

```
┌────────────────────────────────────┐
│  flashcard_decks                   │
├────────────────────────────────────┤
│ PK  id                BIGINT       │
│ FK  owner_user_id     BIGINT       │
│ FK  course_id         BIGINT NULL  │  ← 강의 연동 덱 (옵셔널)
│ FK  source_note_id    BIGINT NULL  │  ← 노트에서 파생된 덱 (옵셔널)
│     title             VARCHAR      │
│     description       TEXT         │
│     settings          JSONB        │  {sm2_ease_default, daily_limit, ...}
│     card_count        INT          │
│     due_count         INT          │  ← 복습 대기 카드 수 (집계)
│     status            ENUM         │  ACTIVE / ARCHIVED
│     created_at, updated_at         │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│  flashcards                        │
├────────────────────────────────────┤
│ PK  id                  BIGINT     │
│ FK  deck_id             BIGINT     │
│ FK  source_chunk_id     BIGINT NULL│  ← content_embeddings or note_embeddings
│     source_type         ENUM       │  COURSE_CHUNK / NOTE_CHUNK / MANUAL / AI_GEN
│     front               TEXT       │  질문 (Markdown + LaTeX 지원)
│     back                TEXT       │  답 (Markdown + LaTeX + 이미지)
│     front_embedding     VECTOR(1536)│ ← 중복 탐지용
│     bloom_level         ENUM       │  REMEMBER/UNDERSTAND/APPLY/ANALYZE/EVALUATE/CREATE
│     concept_tags        JSONB      │  ["jpa-n+1", "fetch-join"]
│     difficulty_hint     FLOAT      │  0.0~1.0 (LLM 추정)
│     status              ENUM       │  ACTIVE / SUSPENDED / DELETED
│     ai_generation_meta  JSONB      │  {prompt_version, model, confidence}
│     created_at, updated_at         │
└────────────────────────────────────┘
INDEX: (deck_id, status)
INDEX: (source_chunk_id)
INDEX: HNSW on front_embedding (중복 카드 병합용)

┌────────────────────────────────────┐
│  flashcard_review_states           │  ← SM-2 알고리즘 상태
├────────────────────────────────────┤
│ PK  id                  BIGINT     │
│ FK  card_id             BIGINT     │
│ FK  user_id             BIGINT     │  (카드 공유 덱 대비 per-user 상태)
│     ease_factor         FLOAT      │  SM-2 EF (default 2.5, min 1.3)
│     interval_days       INT        │  다음 복습까지 일수
│     repetitions         INT        │  연속 성공 횟수
│     due_at              DATETIME   │  복습 예정 시각
│     last_reviewed_at    DATETIME   │
│     last_quality        TINYINT    │  0~5 (Anki SM-2 quality)
│     leech_count         INT        │  연속 실패 카운터 (8+ → SUSPENDED 제안)
│     confidence_weight   FLOAT      │  Bloom 가중치 (§5.6 온보딩 연동)
│     created_at, updated_at         │
└────────────────────────────────────┘
UNIQUE: (card_id, user_id)
INDEX: (user_id, due_at) — 복습 큐 조회 핵심 인덱스

┌────────────────────────────────────┐
│  flashcard_reviews                 │  ← 복습 이력 (append-only)
├────────────────────────────────────┤
│ PK  id                  BIGINT     │
│ FK  card_id             BIGINT     │
│ FK  user_id             BIGINT     │
│     quality             TINYINT    │  0~5
│     elapsed_ms          INT        │  카드 앞면 보고 답까지 걸린 시간
│     review_context      ENUM       │  SCHEDULED / CRAM / AD_HOC
│     session_id          VARCHAR    │  (UUID — 세션 집계용)
│     reviewed_at         DATETIME   │
└────────────────────────────────────┘
INDEX: (user_id, reviewed_at)
PARTITION: monthly on reviewed_at
```

**SM-2 상태 전이 요약:**
- Review 시 quality 입력 → `flashcard_review_states` 갱신 → `flashcard_reviews` append
- quality < 3: `repetitions = 0`, `interval_days = 1`, EF 감소
- quality ≥ 3: `repetitions++`, `interval_days = prev * EF` (복잡 공식은 §5.8 참고)
- `leech_count >= 8` → 사용자에게 "이 카드 재작성하세요" 제안


### 4.12 개인 지식 노트 도메인 (v5.0 신규)

```
┌────────────────────────────────────┐
│  notes                             │
├────────────────────────────────────┤
│ PK  id                  BIGINT     │
│ FK  owner_user_id       BIGINT     │
│ FK  course_id           BIGINT NULL│  ← 강의 연동 노트 (옵셔널)
│ FK  lesson_id           BIGINT NULL│
│     title               VARCHAR    │  (unique per user — 위키링크용)
│     slug                VARCHAR    │  (URL-safe 식별자)
│     content_md          TEXT       │  Markdown 원문
│     folder_path         VARCHAR    │  "/dev/spring/jpa"
│     visibility          ENUM       │  PRIVATE / SHARED_TEAM
│     word_count          INT        │
│     status              ENUM       │  DRAFT / PUBLISHED / ARCHIVED
│     created_at, updated_at         │
└────────────────────────────────────┘
UNIQUE: (owner_user_id, title) — 위키링크 해석 키
UNIQUE: (owner_user_id, slug)
INDEX: (owner_user_id, folder_path)
RLS POLICY: owner_user_id = current_user_id OR visibility = 'SHARED_TEAM'

┌────────────────────────────────────┐
│  note_links                        │  ← [[wiki-link]] 해석 결과
├────────────────────────────────────┤
│ PK  id                  BIGINT     │
│ FK  source_note_id      BIGINT     │  (링크를 건 노트)
│ FK  target_note_id      BIGINT NULL│  (NULL = 미해결 링크, 나중에 생성될 수 있음)
│     target_title        VARCHAR    │  (미해결 링크 추적용)
│     link_type           ENUM       │  WIKI / TAG / EXTERNAL_URL
│     anchor_text         VARCHAR    │  "JPA N+1" 같은 표시 텍스트
│     position            INT        │  노트 내 위치 (백링크 하이라이트용)
│     created_at                     │
└────────────────────────────────────┘
INDEX: (source_note_id)
INDEX: (target_note_id) — 백링크 조회
INDEX: (target_title) WHERE target_note_id IS NULL — 미해결 링크 배치 작업용

┌────────────────────────────────────┐
│  note_tags                         │
├────────────────────────────────────┤
│ PK  id                  BIGINT     │
│ FK  note_id             BIGINT     │
│     tag                 VARCHAR    │  "#spring", "#database"
│     created_at                     │
└────────────────────────────────────┘
UNIQUE: (note_id, tag)
INDEX: (tag)

┌────────────────────────────────────┐
│  note_graph_cache                  │  ← 그래프 뷰 성능 최적화
├────────────────────────────────────┤
│ PK  user_id             BIGINT     │
│     node_count          INT        │
│     edge_count          INT        │
│     graph_json          JSONB      │  {nodes: [...], edges: [...]}
│     layout_coords       JSONB      │  force-directed 좌표 캐시
│     generated_at        DATETIME   │
└────────────────────────────────────┘
TTL: 24h (NoteCreated/NoteLinked 이벤트로 무효화)
```

**설계 핵심:**
- `note_links.target_note_id NULL` 허용 → Obsidian과 동일하게 "존재하지 않는 노트로의 링크"를 허용하고, 나중에 해당 제목 노트가 생성되면 배치로 연결
- `note_graph_cache`는 사용자당 1건 캐시. 노트가 많은 사용자(1000+) 대비해 force-directed 좌표를 서버에서 사전 계산
- PII는 본문 전체가 아니라 **Embedding으로 전달되기 전 청크 단위에서만 스캔** (사용자 자신의 노트 내부 PII는 허용, AI 호출 시 마스킹)


---

## 5. AI/LLM 기능 상세 설계

> §5.1~§5.7은 v4.0 설계 그대로 유지 (RAG 파이프라인, 튜터 메모리, 3단계 레벨링, 3층 평가, AI 채점 HITL, 온보딩, LLM 라우팅).
> v5.0 신규: §5.8 SM-2 스케줄러 + Bloom 가중치, §5.9 개인 노트 의미 검색, §5.10 AI 튜터 개인 노트 참조, §5.11 노트 → 카드 자동 생성 파이프라인.

### 5.2 AI 튜터 메모리 구조 (v5.0 확장)

```
┌─────────────────────────────────────────────────────────────────┐
│  Short-term Memory (세션 내, 변경 없음)                          │
│  ├── 현재 대화 히스토리 (최근 10턴)                              │
│  ├── 현재 학습 중인 레슨 컨텍스트                                │
│  └── 저장: Redis (TTL: 세션 종료 후 24시간)                      │
│                                                                 │
│  Long-term Memory (v5.0 확장)                                    │
│  ├── concept_mastery (개념별 숙련도 + confidence)                │
│  ├── 자주 틀리는 패턴 (오답 이력)                                │
│  ├── 선호 학습 스타일 (피드백 데이터 기반)                       │
│  ├── 플래시카드 leech 목록 (반복 실패 개념)             ← v5.0   │
│  └── 개인 노트 벡터 검색 Top-K (의미 유사 조각)        ← v5.0   │
│                                                                 │
│  프롬프트 구성 순서:                                             │
│  System Prompt (역할 + 레벨링)                                   │
│  → Long-term Memory (concept + leech + 개인 노트 Top-3)          │
│  → RAG 컨텍스트 (강의 콘텐츠)                                    │
│  → Short-term Memory → User Message                              │
└─────────────────────────────────────────────────────────────────┘
```

### 5.8 Flashcard SM-2 스케줄러 + Bloom 가중치 (v5.0 신규)

```
┌─────────────────────────────────────────────────────────────────┐
│  SM-2 알고리즘 (Piotr Wozniak, 1985 — Anki 원본 공식)            │
│                                                                 │
│  Input: quality q ∈ {0,1,2,3,4,5}                                │
│   0=완전히 잊음 / 3=어렵게 기억 / 5=즉시 기억                    │
│                                                                 │
│  q < 3 (실패):                                                   │
│    repetitions = 0                                               │
│    interval_days = 1                                             │
│    ease_factor 유지 (단, 감소는 아래 공식)                       │
│    leech_count++                                                 │
│                                                                 │
│  q >= 3 (성공):                                                  │
│    if repetitions == 0: interval = 1                             │
│    if repetitions == 1: interval = 6                             │
│    if repetitions >= 2: interval = prev_interval * EF            │
│    repetitions++                                                 │
│                                                                 │
│  EF 갱신 (매 리뷰):                                              │
│    EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))             │
│    EF' = max(1.3, EF')                                           │
│                                                                 │
│  due_at = last_reviewed_at + interval_days                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  v5.0 확장: Bloom's Taxonomy 가중치 (온보딩 §5.6 연동)           │
│                                                                 │
│  confidence_weight 계산:                                         │
│    base = concept_mastery의 confidence (0.0~1.0)                 │
│    bloom_multiplier:                                             │
│      REMEMBER    → 1.0  (그대로)                                 │
│      UNDERSTAND  → 0.95                                          │
│      APPLY       → 0.85                                          │
│      ANALYZE     → 0.75                                          │
│      EVALUATE    → 0.65                                          │
│      CREATE      → 0.55                                          │
│    weight = base * bloom_multiplier                              │
│                                                                 │
│  적용: 고차원 Bloom 카드일수록 interval을 보수적으로              │
│    effective_interval = interval_days * (0.5 + 0.5 * weight)     │
│                                                                 │
│  의미:                                                           │
│  → "기억" 수준 카드는 SM-2 공식 그대로 사용                      │
│  → "창조" 수준 카드는 같은 quality=5라도 interval이 짧아짐       │
│  → 고차원 사고는 더 자주 복습해야 한다는 학습과학 반영          │
└─────────────────────────────────────────────────────────────────┘
```

**복습 큐 운영 (Redis Sorted Set):**
```
KEY: flashcard:due:{user_id}
SCORE: due_at (epoch millis)
MEMBER: card_id

# 복습할 카드 가져오기 (지금까지 due인 것)
ZRANGEBYSCORE flashcard:due:{user_id} -inf {now_epoch} LIMIT 0 50

# Review 후 갱신
ZADD flashcard:due:{user_id} {new_due_at} {card_id}
```

매일 자정 Quartz 배치가 `CardBatchDue` 이벤트를 발행하여 모바일 푸시 알림 트리거.

### 5.9 개인 노트 의미 검색 (v5.0 신규)

기존 RAG 파이프라인(§5.1)을 **`source_filter` 파라미터**로 재사용한다. 코드 한 줄 안 고치고 두 도메인 지원.

```
┌─────────────────────────────────────────────────────────────────┐
│  노트 검색 API: GET /api/v1/notes/search?q=...&scope=PERSONAL    │
│                                                                 │
│  RAG Service.search(query, source_filter=NOTE, user_id=...)     │
│   ├── Query Rewrite                                             │
│   ├── Hybrid Search (note_embeddings + ES BM25 on notes 인덱스) │
│   │   └── WHERE owner_user_id = :user_id (RLS 강제)            │
│   ├── Re-ranking (CrossEncoder)                                 │
│   └── Top 5 chunks + 노트 메타데이터 반환                        │
│                                                                 │
│  반환:                                                           │
│  [{                                                              │
│    note_id, title, chunk_text, score,                            │
│    highlighted_snippet, path                                     │
│  }, ...]                                                         │
└─────────────────────────────────────────────────────────────────┘
```

**BM25 인덱스 분리 전략:**
- Elasticsearch 인덱스: `courses_v1`, `notes_v1_{user_id}` (사용자별 인덱스 분리) OR `notes_v1` 단일 인덱스 + user_id 필터
- **단일 인덱스 권장**: 노트 양이 적어 샤드 오버헤드 큼. `routing` + `user_id` 필터로 격리
- 권한 체크는 애플리케이션 레이어에서 이중 검증 (ES 필터 + DB RLS)

### 5.10 AI 튜터가 개인 노트를 Long-term Memory로 참조 (v5.0 신규)

가장 강력한 교차 시너지. 튜터 프롬프트에 사용자 노트 조각을 자동 주입한다.

```
┌─────────────────────────────────────────────────────────────────┐
│  튜터 요청 처리 파이프라인 (v5.0)                                │
│                                                                 │
│  사용자 질의: "JPA fetch join 언제 써?"                          │
│                                                                 │
│  1. 질의 임베딩                                                  │
│  2. 병렬 검색:                                                   │
│     ├── content_embeddings (수강 강의 범위)                      │
│     └── note_embeddings (사용자 개인 노트)                       │
│  3. Re-ranking 통합 (둘을 같은 스코어로 비교, source type 태깅)  │
│  4. 프롬프트 빌드:                                               │
│                                                                 │
│  [System]                                                        │
│  당신은 학습자의 튜터입니다. 학습자의 개인 노트가 있으면          │
│  반드시 참조하고, 학습자가 이전에 정리한 내용과 연결해 답하세요.  │
│                                                                 │
│  [Long-term Memory]                                              │
│  - 학습자 수준: 중급 (mastery 0.6)                               │
│  - 취약 개념: N+1 문제 (leech 3회)                                │
│  - 학습자의 관련 노트:                                            │
│    ● "JPA 페치 전략" (2주 전 작성)                               │
│      "Lazy는 프록시로 감싸서 접근 시점에 쿼리..."                │
│    ● "성능 튜닝 체크리스트" (어제 작성)                           │
│      "N+1이 의심되면 JPQL fetch join 먼저 시도..."               │
│                                                                 │
│  [RAG 강의 컨텍스트]                                              │
│  (수강 중인 강의 관련 청크 3개)                                  │
│                                                                 │
│  [User] JPA fetch join 언제 써?                                  │
└─────────────────────────────────────────────────────────────────┘
```

**개인정보 취급 주의:**
- 사용자 본인의 노트는 자기 질의에 주입되므로 **PII 마스킹 대상이 아님** (자기 데이터 접근)
- 그러나 LLM 제공자(Anthropic/OpenAI)로 전송되므로 **제3자 PII는 여전히 마스킹** (친구 이름, 사내 민감 정보 등)
- 설정으로 사용자가 "AI 튜터에 노트 참조 허용" 토글 가능 (Off-by-default in v5.0 MVP, privacy by design)

### 5.11 노트 → 플래시카드 자동 생성 파이프라인 (v5.0 신규)

```
┌─────────────────────────────────────────────────────────────────┐
│  사용자 액션:                                                     │
│  노트에서 텍스트 블록 선택 → "카드로 만들기" 버튼                │
│        OR                                                        │
│  노트 저장 시 #flashcard 태그가 있으면 자동 제안                 │
│                                                                 │
│  1. 선택 블록 → LLM Service                                      │
│     Prompt: "다음 노트에서 플래시카드 N장 생성. Bloom 레벨 다양화,│
│              각 카드는 front(질문)/back(답)/bloom_level 포함"    │
│                                                                 │
│  2. LLM 응답 파싱 (JSON strict)                                  │
│     [{front, back, bloom_level, concept_tags}, ...]              │
│                                                                 │
│  3. 중복 탐지:                                                    │
│     front_embedding 계산 → 사용자 기존 카드와 cosine sim          │
│     sim > 0.9 → 기존 카드에 태그 추가 제안 (중복 생성 안 함)     │
│                                                                 │
│  4. 미리보기 UI → 사용자 승인 → flashcards INSERT + Outbox       │
│                                                                 │
│  5. source_note_id, source_chunk_id 기록 → 카드 뒤면에           │
│     "원본 노트 보기" 링크 자동 생성 (학습 맥락 연결)            │
└─────────────────────────────────────────────────────────────────┘
```

**FinOps 고려:**
- 카드 1장 = LLM 호출 1회가 아님. 한 번의 LLM 호출로 N장 일괄 생성
- Semantic Cache 적극 활용: 유사 청크에서 이미 생성된 카드가 있으면 재사용 제안
- 사용자별 월간 AI 카드 생성 한도 (무료 50장 / 유료 500장)

---

## 6. PII Masking Pipeline (v4.0 유지 + v5.0 주의점)

```
┌─────────────────────────────────────────────────────────────────┐
│  ── 입력 마스킹 (전처리) ──                                     │
│  Step 1: Regex (한국 특화 — 이메일, 전화, 주민번호, 카드번호,    │
│          계좌번호(은행별), 여권, 운전면허, 사업자등록번호)        │
│  Step 2: NER (Presidio + KoNLPy — 인명, 주소, 기관명)           │
│  Step 3: 토큰 치환 ("김철수" → <NAME_1> 또는 "학습자A")         │
│          매핑: Redis session-scoped, 세션 종료 시 자동 삭제      │
│                                                                 │
│  Anonymization 옵션: 완전 마스킹(기본) / Pseudonymization(가명화)│
│                                                                 │
│  ── 출력 스캔 (후처리, v4.0) ──                                 │
│  Step 1: Demasking (<NAME_1> → 원본 복원)                       │
│  Step 2: Output PII 스캔 (LLM이 새로 생성한 PII 감지)           │
│          → 탐지 시 마스킹 + 감사 로그 "OUTPUT_PII_DETECTED"     │
│                                                                 │
│  ── 컴플라이언스 ──                                             │
│  한국 PIPA: 처리 목적 명시, 위탁 고지, PII 전송 유형 기록       │
│  EU AI Act: 교육 AI → 투명성, AI 생성 결과 명시, 감사 추적      │
└─────────────────────────────────────────────────────────────────┘
```

---

**▼ 이하 v5.0 확장 (v4.0 에 없던 하위 섹션)**


v4.0의 Input/Output 양방향 PII Masking Pipeline(Presidio + KoNLPy + Pseudonymization)을 그대로 사용한다. v5.0에서 추가 고려할 점:

**개인 노트 처리 원칙:**
- **자기 데이터 저장 시**: 마스킹하지 않음 (사용자 본인 자료)
- **LLM 호출 시(튜터/요약/카드 생성)**: 제3자 PII만 마스킹 (본인 정보는 통과)
- **사용자 간 공유 노트(SHARED_TEAM)**: 공유 전 강제 Output PII 스캔 → 발견 시 사용자에게 경고

**플래시카드 특이사항:**
- 카드 앞면에 PII가 있으면 안 됨 (학습 자료 성격상 제3자 정보 포함 시 사생활 침해)
- 카드 생성 LLM 응답 → Output 스캔 통과 후 저장
- 이상 탐지: 특정 사용자가 PII 포함 카드를 반복 생성 시도 → 감사 로그 + Rate Limit

---

## 7. FinOps Kill-switch (v5.0 확장)

v4.0의 Unit Economics 모델을 확장하여 **노트/카드 모듈의 비용 효율**을 별도 추적한다.

### 7.1 v5.0 추가 단가 지표

| 지표 | 정의 | 목표값 |
|------|------|--------|
| **cost_per_note_embedding** | 노트 1편 임베딩 비용 | < $0.002 |
| **cost_per_ai_card** | AI 생성 카드 1장 비용 | < $0.005 |
| **cost_per_active_learner** | MAU당 총 AI 비용 | < $0.50 |
| **note_embedding_cache_hit_rate** | 동일 chunk_hash 재사용 비율 | > 70% |
| **semantic_cache_card_gen_hit** | 카드 생성 시 유사 카드 재사용 | > 40% |

### 7.2 사용자별 한도 (플랜 기반)

```
┌─────────────────────────────────────────────────────────────────┐
│  Free Plan (v5.0 MVP):                                           │
│  ├── 노트 개수: 200편                                            │
│  ├── 노트 임베딩: 월 100편 (초과 시 검색은 키워드로만)           │
│  ├── AI 카드 생성: 월 50장                                       │
│  ├── AI 튜터 노트 참조: Off (수동 켜기)                          │
│  └── 그래프 뷰: 최대 300 노드까지 렌더                           │
│                                                                 │
│  Pro Plan (향후):                                                │
│  ├── 무제한 노트/임베딩                                          │
│  ├── AI 카드 월 500장                                            │
│  ├── AI 튜터 노트 참조 기본 On                                   │
│  ├── SHARED_TEAM 기능                                            │
│  └── 고급 그래프 (필터/클러스터링/타임라인)                      │
└─────────────────────────────────────────────────────────────────┘
```

Kill-switch는 **사용자별/플랜별/전사**의 3계층으로 작동:
- 사용자가 월 한도 초과 → 해당 사용자만 AI 호출 차단 (학습은 계속 가능)
- 플랜 총 한도 초과 → 관리자 알림 (플랜 가격 재산정 시그널)
- 전사 한도 초과 → v4.0 기존 로직 (전면 Kill)

---

## 8. 보안 설계 (7 Layer + PII + FinOps + v5.0 Knowledge)

v4.0의 7 Layer 방어 체계를 유지하고, v5.0에서 **노트 권한 분리 층**을 추가한다.

### 8.1 v5.0 추가 방어 — Row-Level Security (RLS)

```
PostgreSQL 설정:
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
CREATE POLICY notes_owner_read ON notes FOR SELECT
  USING (owner_user_id = current_setting('app.current_user_id')::bigint
         OR visibility = 'SHARED_TEAM');
CREATE POLICY notes_owner_write ON notes FOR ALL
  USING (owner_user_id = current_setting('app.current_user_id')::bigint);

ALTER TABLE note_embeddings ENABLE ROW LEVEL SECURITY;
CREATE POLICY note_emb_owner ON note_embeddings FOR ALL
  USING (owner_user_id = current_setting('app.current_user_id')::bigint);
```

애플리케이션(JPA) 레이어에서 `current_setting('app.current_user_id', ...)` 을 요청당 주입하여 DB가 자동으로 필터링. ORM 버그로 권한 필터를 빠뜨려도 DB가 방어.

### 8.2 공유 노트 방어

- `visibility=SHARED_TEAM` 전환 시 **Output PII 스캔 필수 통과**
- 공유 링크는 서명 토큰 (JWT + 만료시간)
- 팀 외부 공유는 명시적 확인 2단계

---

## 9. 핵심 API 설계

### 9.1 사용자 / 인증

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| POST | `/api/v1/auth/signup` | 회원가입 | PUBLIC |
| POST | `/api/v1/auth/login` | 로그인 (JWT) | PUBLIC |
| POST | `/api/v1/auth/refresh` | 토큰 갱신 | AUTHENTICATED |
| GET | `/api/v1/users/me` | 내 프로필 | AUTHENTICATED |
| PUT | `/api/v1/users/me` | 프로필 수정 | AUTHENTICATED |
| PUT | `/api/v1/users/me/learning-prefs` | 학습 선호 | LEARNER |

### 9.2 강의

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/api/v1/courses` | 강의 목록 | PUBLIC |
| GET | `/api/v1/courses/{id}` | 강의 상세 | PUBLIC |
| POST | `/api/v1/courses` | 강의 생성 | INSTRUCTOR |
| PUT | `/api/v1/courses/{id}` | 강의 수정 | INSTRUCTOR |
| POST | `/api/v1/courses/{id}/sections` | 섹션 추가 | INSTRUCTOR |
| POST | `/api/v1/sections/{id}/lessons` | 레슨 추가 → Event | INSTRUCTOR |
| POST | `/api/v1/courses/{id}/enroll` | 수강 신청 | LEARNER |
| GET | `/api/v1/courses/{id}/progress` | 진도율 | LEARNER |
| PUT | `/api/v1/lessons/{id}/complete` | 레슨 완료 → Event | LEARNER |

### 9.3 AI 튜터

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| POST | `/api/v1/ai/chat/sessions` | 채팅 세션 생성 | LEARNER |
| POST | `/api/v1/ai/chat/sessions/{id}/messages` | 메시지 (SSE 스트리밍) | LEARNER |
| GET | `/api/v1/ai/chat/sessions` | 세션 목록 | LEARNER |
| GET | `/api/v1/ai/chat/sessions/{id}/messages` | 대화 히스토리 | LEARNER |
| POST | `/api/v1/ai/chat/messages/{id}/feedback` | 피드백 (👍👎) | LEARNER |
| GET | `/api/v1/ai/chat/sessions/{id}/suggestions` | 추천 질문 | LEARNER |

### 9.4 퀴즈 / 과제

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| POST | `/api/v1/ai/quizzes/generate` | AI 퀴즈 생성 | INSTRUCTOR |
| GET | `/api/v1/lessons/{id}/quizzes` | 레슨별 퀴즈 | LEARNER |
| POST | `/api/v1/quizzes/{id}/submit` | 퀴즈 제출 → Event | LEARNER |
| GET | `/api/v1/quizzes/{id}/results` | 결과 + AI 피드백 | LEARNER |
| POST | `/api/v1/assignments/{id}/submit` | 과제 제출 → Event | LEARNER |
| POST | `/api/v1/quizzes/attempts/{id}/appeal` | 채점 이의 제기 | LEARNER |
| POST | `/api/v1/assignments/submissions/{id}/appeal` | 과제 이의 제기 | LEARNER |
| GET | `/api/v1/instructor/review-queue` | 수동 검토 대기 | INSTRUCTOR |
| PUT | `/api/v1/instructor/review-queue/{id}/resolve` | 검토 완료 | INSTRUCTOR |

### 9.5 학습 분석

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/api/v1/analytics/me/dashboard` | 학습 대시보드 | LEARNER |
| GET | `/api/v1/analytics/me/weaknesses` | 취약점 분석 | LEARNER |
| GET | `/api/v1/analytics/me/concept-mastery` | 개념별 숙련도 | LEARNER |
| GET | `/api/v1/analytics/me/recommendations` | AI 추천 | LEARNER |
| GET | `/api/v1/analytics/me/study-time` | 학습 시간 | LEARNER |
| GET | `/api/v1/analytics/courses/{id}/overview` | 강의 분석 | INSTRUCTOR |

### 9.6 온보딩

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/api/v1/onboarding/diagnostic/{courseId}` | 진단 문제 | LEARNER |
| POST | `/api/v1/onboarding/diagnostic/{courseId}/submit` | 진단 결과 제출 | LEARNER |
| POST | `/api/v1/onboarding/self-assess` | 자가 진단 | LEARNER |

### 9.7 콘텐츠 요약

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| POST | `/api/v1/ai/summarize/lesson/{id}` | 레슨 요약 | LEARNER |
| POST | `/api/v1/ai/flashcards/generate/{lessonId}` | 플래시카드 생성 | LEARNER |

### 9.8 AI 품질 관리 (Admin)

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/api/v1/admin/ai/quality/dashboard` | AI 품질 대시보드 | ADMIN |
| GET | `/api/v1/admin/ai/quality/ragas/summary` | RAGAS 주간 요약 | ADMIN |
| GET | `/api/v1/admin/ai/quality/ragas/trends` | 지표 트렌드 | ADMIN |
| POST | `/api/v1/admin/ai/ab-tests` | A/B 테스트 생성 | ADMIN |
| GET | `/api/v1/admin/ai/ab-tests/{id}/results` | A/B 결과 | ADMIN |
| GET | `/api/v1/admin/ai/prompts` | 프롬프트 버전 | ADMIN |
| POST | `/api/v1/admin/ai/prompts` | 새 버전 등록 | ADMIN |
| PUT | `/api/v1/admin/ai/prompts/{id}/rollback` | 롤백 | ADMIN |

### 9.9 FinOps (Admin)

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/api/v1/admin/finops/dashboard` | FinOps 대시보드 | ADMIN |
| GET | `/api/v1/admin/finops/unit-economics` | 서비스별 단가 | ADMIN |
| PUT | `/api/v1/admin/finops/kill-switch` | Kill-switch ON/OFF | ADMIN |
| PUT | `/api/v1/admin/finops/thresholds` | Limit 조정 | ADMIN |

---

**▼ 이하 v5.0 확장 (v4.0 에 없던 하위 섹션)**


§9.1~§9.9는 v4.0 그대로 유지. v5.0 신규: §9.10 Flashcard, §9.11 Note + Graph.


### 9.10 Flashcard (v5.0 신규)

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/api/v1/flashcards/decks` | 내 덱 목록 | LEARNER |
| POST | `/api/v1/flashcards/decks` | 덱 생성 | LEARNER |
| PUT | `/api/v1/flashcards/decks/{id}` | 덱 수정 | OWNER |
| DELETE | `/api/v1/flashcards/decks/{id}` | 덱 삭제 | OWNER |
| GET | `/api/v1/flashcards/decks/{id}/cards` | 덱 내 카드 목록 | OWNER |
| POST | `/api/v1/flashcards/decks/{id}/cards` | 카드 수동 추가 | OWNER |
| PUT | `/api/v1/flashcards/cards/{id}` | 카드 수정 | OWNER |
| DELETE | `/api/v1/flashcards/cards/{id}` | 카드 삭제(soft) | OWNER |
| POST | `/api/v1/flashcards/cards/{id}/suspend` | 카드 보류 | OWNER |
| **GET** | **`/api/v1/flashcards/review/queue`** | **복습 대기 큐 조회 (Redis ZSET)** | **LEARNER** |
| **POST** | **`/api/v1/flashcards/review`** | **복습 결과 제출 (SM-2 갱신)** | **LEARNER** |
| POST | `/api/v1/flashcards/generate/from-lesson/{lessonId}` | 강의에서 생성 (v4.0 기존) | LEARNER |
| **POST** | **`/api/v1/flashcards/generate/from-note/{noteId}`** | **노트에서 생성 (v5.0)** | **OWNER** |
| POST | `/api/v1/flashcards/generate/from-selection` | 선택 텍스트에서 생성 | LEARNER |
| GET | `/api/v1/flashcards/stats/retention` | 기억 유지율 통계 | LEARNER |
| GET | `/api/v1/flashcards/stats/heatmap` | 복습 히트맵 (GitHub 스타일) | LEARNER |

**복습 결과 제출 요청 예시:**
```json
POST /api/v1/flashcards/review
{
  "card_id": 12345,
  "quality": 4,
  "elapsed_ms": 3200,
  "session_id": "s_2026042101"
}

Response:
{
  "next_due_at": "2026-04-26T09:00:00Z",
  "new_interval_days": 5,
  "new_ease_factor": 2.62,
  "concept_mastery_delta": +0.03,
  "message": "좋아요! 5일 후 다시 만나요."
}
```


### 9.11 Knowledge Notes + Graph (v5.0 신규)

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/api/v1/notes` | 내 노트 목록 (folder_path 필터) | LEARNER |
| POST | `/api/v1/notes` | 노트 생성 | LEARNER |
| GET | `/api/v1/notes/{id}` | 노트 상세 (Markdown 원문 + 렌더) | OWNER/SHARED |
| PUT | `/api/v1/notes/{id}` | 노트 수정 | OWNER |
| DELETE | `/api/v1/notes/{id}` | 노트 삭제(soft) | OWNER |
| **GET** | **`/api/v1/notes/search`** | **의미 검색 (RAG Service 재사용)** | **OWNER** |
| GET | `/api/v1/notes/{id}/backlinks` | 이 노트를 참조하는 노트들 | OWNER |
| GET | `/api/v1/notes/{id}/outlinks` | 이 노트가 참조하는 노트들 | OWNER |
| **GET** | **`/api/v1/notes/graph`** | **전체 지식 그래프 (노드+엣지)** | **LEARNER** |
| GET | `/api/v1/notes/graph/subgraph/{id}` | 특정 노트 중심 부분 그래프 (depth=2) | OWNER |
| POST | `/api/v1/notes/quick-capture` | 모바일 퀵 캡처 (제목 자동 생성) | LEARNER |
| GET | `/api/v1/notes/unresolved-links` | 미해결 위키링크 목록 | LEARNER |
| GET | `/api/v1/notes/tags` | 내 태그 목록 (빈도순) | LEARNER |
| GET | `/api/v1/notes/tags/{tag}` | 태그로 묶인 노트들 | LEARNER |

**그래프 조회 응답 예시:**
```json
GET /api/v1/notes/graph?max_nodes=300

{
  "nodes": [
    {"id": 101, "title": "JPA 페치 전략", "tags": ["#spring"], "word_count": 820,
     "card_count": 5, "last_updated": "2026-04-15"},
    ...
  ],
  "edges": [
    {"source": 101, "target": 204, "type": "WIKI"},
    {"source": 101, "target": 302, "type": "TAG", "via": "#spring"}
  ],
  "layout": {"algorithm": "force-directed", "coords": {...}},
  "generated_at": "2026-04-21T10:00:00Z",
  "from_cache": true
}
```

---

## 10. 화면 구성 (v5.0 신규 화면)

§10.1 강의 수강, §10.2 학습 분석 대시보드, §10.3 관리자 대시보드는 v4.0 그대로 유지.

### 10.4 학습자 — 플래시카드 복습 화면 (v5.0 신규)

```
┌────────────────────────────────────────────────────────────────┐
│  [오늘의 복습]  ⏰ 23장 대기    ✨ 연속 7일                     │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                                                          │  │
│  │       JPA에서 fetch join은 언제 써야 하나요?              │  │
│  │                                                          │  │
│  │                 (탭하여 답 확인)                          │  │
│  │                                                          │  │
│  │  📎 원본 노트: "JPA 페치 전략" (2주 전 작성)             │  │
│  │  🏷 #spring #database                                     │  │
│  │  🎯 Bloom: APPLY                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  [다시(0)] [어려움(3)] [보통(4)] [쉬움(5)]                    │
│                                                                │
│  ─────────────────────────────────────────────                 │
│  오늘 복습 진도: ████████░░░░░░ 17/23                          │
│  이번 카드 이전 기록: 3회 성공, EF 2.62, 5일 간격              │
│  관련 약한 개념: N+1 문제 (mastery 0.55 ↑)                     │
└────────────────────────────────────────────────────────────────┘
```

**모바일 UX 특화:**
- 스와이프 제스처: 좌(다시) / 우(쉬움) / 위(답 보기) / 아래(건너뛰기)
- 오프라인 모드: 큐에 담긴 카드는 로컬 저장, 복습 결과 버퍼링 후 동기화
- 복습 전 백그라운드에서 관련 노트 프리패치 (LTE 절약)

### 10.5 학습자 — 개인 지식 그래프 뷰 (v5.0 신규)

```
┌────────────────────────────────────────────────────────────────┐
│  [🔍 의미 검색] "JPA 성능 튜닝"                         [필터▼] │
│                                                                │
│  ┌──────────────────────────┬───────────────────────────────┐  │
│  │                          │   선택 노드 미리보기           │  │
│  │    [force-directed       │   ┌───────────────────────┐   │  │
│  │     graph canvas]        │   │ JPA 페치 전략         │   │  │
│  │                          │   │ 2주 전 작성           │   │  │
│  │     ○ JPA 페치 전략      │   │ 5개 카드 파생         │   │  │
│  │    / |  \                │   │ 3개 백링크            │   │  │
│  │   ○  ○   ○              │   │                       │   │  │
│  │  N+1 Lazy Fetch          │   │ [노트 열기] [카드보기] │   │  │
│  │      관련              │   │                       │   │  │
│  │                          │   │ 📄 미리보기:          │   │  │
│  │  [크기 = 연결 수]        │   │ Lazy는 프록시로 감싸서 │   │  │
│  │  [색 = 태그 클러스터]    │   │ 접근 시점에 쿼리...   │   │  │
│  │  [드래그 / 줌 / 팬]      │   └───────────────────────┘   │  │
│  └──────────────────────────┴───────────────────────────────┘  │
│                                                                │
│  📊 그래프 통계: 132 노드 · 287 엣지 · 8 클러스터              │
│  ⚠️ 고립 노드 3개 (연결되지 않은 노트) — [링크 추천 받기]       │
└────────────────────────────────────────────────────────────────┘
```

**기술적 구현 포인트:**
- Web: React Flow + D3-force. 300 노드 초과 시 클러스터 축약(aggregation) 적용
- Flutter: CustomPainter + isolate로 force simulation 오프로딩 (메인 스레드 블록 방지)
- 좌표 캐싱: `note_graph_cache` 테이블에 매일 자정 배치로 사전 계산
- 의미 검색 통합: 검색어 입력 → 관련 노트 하이라이트 + 그래프 zoom-in

---

## 11. 프로젝트 구조

```
learnflow/
├── learnflow-api/                    # 메인 모놀리식 (MSA 준비 단계)
│   ├── user/                         # 사용자/인증
│   ├── course/                       # 강의/콘텐츠
│   ├── learning/                     # 수강/진도
│   ├── assessment/                   # 퀴즈/과제/채점
│   ├── analytics/                    # 학습 분석
│   ├── onboarding/                   # 진단 테스트
│   ├── knowledge/                    # v5.0 신규: 노트 + 플래시카드
│   │   ├── note/
│   │   │   ├── domain/              # Note, NoteLink, NoteTag
│   │   │   ├── wikilink/            # [[link]] 파서 (Flexmark)
│   │   │   ├── graph/               # 그래프 빌더, 캐시
│   │   │   └── search/              # RAG Service 연동
│   │   └── flashcard/
│   │       ├── domain/              # Deck, Card, ReviewState
│   │       ├── sm2/                 # SM-2 알고리즘 + Bloom 가중
│   │       ├── scheduler/           # Quartz + ShedLock
│   │       └── generator/           # 노트/강의 → 카드 LLM 파이프라인
│   └── common/                       # 공통 (JWT, AOP, 예외 등)
│
├── learnflow-ai-gateway/             # AI 오케스트레이터
├── learnflow-llm-service/            # LLM 호출 + 튜터 + 카드 생성
├── learnflow-embedding-service/      # 강의 + 노트 임베딩 (v5.0 확장)
├── learnflow-rag-service/            # RAG (source_filter로 강의/노트 공용)
├── learnflow-evaluation-service/     # 퀴즈 생성 + 채점
│
├── learnflow-worker/                 # Kafka Consumer 모음
│   ├── embedding-worker/             # ContentCreated + NoteCreated 통합
│   ├── grading-worker/
│   ├── analytics-worker/             # FlashcardReviewed → mastery 갱신 추가
│   └── graph-builder-worker/         # v5.0 신규: NoteLinked → graph_cache
│
├── learnflow-web/                    # React 18
│   ├── features/
│   │   ├── course/
│   │   ├── tutor/
│   │   ├── note/                     # v5.0: 에디터 + 그래프
│   │   └── flashcard/                # v5.0: 덱 관리 + 복습
│   └── shared/
│
├── learnflow-mobile/                 # Flutter
│   ├── features/
│   │   ├── course/
│   │   ├── tutor/
│   │   ├── quick_note/               # v5.0: 퀵캡처
│   │   └── flashcard_review/         # v5.0: 자투리 복습
│   └── core/
│
├── learnflow-admin/                  # React 관리자 콘솔
└── infra/
    ├── docker/                       # docker-compose.yml
    ├── grafana/                      # 대시보드 JSON
    └── k6/                           # 부하 테스트
```

---

## 12. 개발 일정

v5.0은 v4.0 24주 + v5.0 12주 = **총 36주 플랜**. Phase 7(Flashcard), Phase 8(Knowledge Notes + Graph), Phase 9(교차 시너지 + 릴리즈)를 추가한다.

```
─── v4.0 범위 (Week 1-24) ───
Phase 1-6: v4.0 24주 (기존 그대로)
└── M6: 릴리즈 (Week 24) — LMS 코어 완성

─── v5.0 확장 (Week 25-36) ───

Phase 7: Flashcard SRS (Week 25-28)
├── Week 25 : flashcard_decks/cards/review_states 스키마 + API CRUD
├── Week 26 : SM-2 알고리즘 + Bloom 가중치 + Redis 복습 큐
├── Week 27 : 강의/수동 카드 생성 + 중복 탐지(cosine)
├── Week 28 : Web 복습 UI + Flutter 모바일 복습 (오프라인 버퍼)
└── M7: SRS MVP (덱 만들고 복습 가능)

Phase 8: Knowledge Notes + Graph (Week 29-33)
├── Week 29 : notes/note_links/note_tags 스키마 + TipTap 에디터 통합
├── Week 30 : [[wiki-link]] 파서(Flexmark) + 백링크/미해결링크 배치
├── Week 31 : note_embeddings + RAG source_filter 확장 + RLS 적용
├── Week 32 : 그래프 뷰 (React Flow + D3-force) + note_graph_cache 배치
├── Week 33 : 모바일 퀵캡처 + 태그/폴더 관리 + 검색 UX
└── M8: Notes MVP (Obsidian 대체 수준)

Phase 9: 교차 시너지 + 릴리즈 (Week 34-36)
├── Week 34 : 노트 → 카드 자동 생성 파이프라인 + AI 튜터 개인 노트 참조
├── Week 35 : FinOps 플랜별 한도 + 모니터링 대시보드 + Chaos Test
└── Week 36 : 통합 QA + 문서 + 배포
└── M9: v5.0 정식 릴리즈
```

### 마일스톤

| 마일스톤 | 시점 | 완료 기준 |
|----------|------|-----------|
| M1-M6 | Week 4~24 | v4.0 기존 마일스톤 |
| **M7: SRS** | Week 28 | SM-2 + 덱/카드 CRUD + 모바일 복습 |
| **M8: Knowledge** | Week 33 | 노트 + 위키링크 + 그래프 뷰 + 의미검색 |
| **M9: v5.0 릴리즈** | Week 36 | 교차 시너지 + 한도 관리 + Chaos Test |

**리스크 최소화 전략:**
- Phase 7, 8은 각각 독립 배포 가능 (feature flag 사용)
- Phase 9는 Phase 7, 8이 실전에서 2~4주 안정화된 후 진행 권장
- 일정 부족 시 Phase 9를 v5.1로 분리하여 릴리즈 지연 방지

---

## 13. Docker Compose (v5.0 확장 부분만)

```yaml
version: '3.8'
services:
  api:
    build: ./learnflow-api
    ports: ["8080:8080"]
    depends_on: [mysql, redis, kafka, elasticsearch]
    environment:
      SPRING_PROFILES_ACTIVE: dev
      CLAUDE_API_KEY: ${CLAUDE_API_KEY}

  web:
    build: ./learnflow-web
    ports: ["3000:3000"]

  mysql:
    image: mysql:8.0
    ports: ["3306:3306"]
    volumes: [mysql-data:/var/lib/mysql]
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
      MYSQL_DATABASE: learnflow

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: [redis-data:/data]

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    ports: ["9092:9092"]
    depends_on: [zookeeper]

  debezium:
    image: debezium/connect:2.5
    ports: ["8083:8083"]
    depends_on: [mysql, kafka]

  pgvector:
    image: pgvector/pgvector:pg16
    ports: ["5433:5432"]
    volumes: [pgvector-data:/var/lib/postgresql/data]

  elasticsearch:
    image: elasticsearch:8.12.0
    ports: ["9200:9200"]
    environment:
      discovery.type: single-node
      xpack.security.enabled: "false"
    volumes: [es-data:/usr/share/elasticsearch/data]

  minio:
    image: minio/minio
    ports: ["9000:9000", "9001:9001"]
    command: server /data --console-address ":9001"
    volumes: [minio-data:/data]

  zipkin:
    image: openzipkin/zipkin
    ports: ["9411:9411"]

  prometheus:
    image: prom/prometheus
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana
    ports: ["3001:3000"]

volumes:
  mysql-data:
  redis-data:
  pgvector-data:
  es-data:
  minio-data:
```

---

**▼ 이하 v5.0 확장 (v4.0 에 없던 하위 섹션)**


v4.0 docker-compose.yml에 다음 서비스/볼륨을 추가한다. (v4.0 전체 구성은 기존 유지)

```yaml
services:
  # 기존 v4.0 서비스들 유지...

  # v5.0 신규: 플래시카드 복습 스케줄러 전용
  scheduler:
    build: ./learnflow-api
    command: ["--spring.profiles.active=scheduler"]
    environment:
      SHEDLOCK_DATASOURCE_URL: jdbc:mysql://mysql:3306/learnflow
      QUARTZ_ENABLED: "true"
    depends_on:
      - mysql
      - redis
      - kafka

  # v5.0 신규: 그래프 빌더 워커
  graph-builder-worker:
    build: ./learnflow-worker/graph-builder-worker
    environment:
      KAFKA_BOOTSTRAP: kafka:9092
      DATABASE_URL: jdbc:postgresql://postgres:5432/learnflow
    depends_on:
      - kafka
      - postgres

  # v5.0 신규: FCM 푸시 알림 서비스 (필요시)
  notification-service:
    build: ./learnflow-notification
    environment:
      FCM_CREDENTIALS: /run/secrets/fcm_credentials
    secrets:
      - fcm_credentials

secrets:
  fcm_credentials:
    file: ./infra/secrets/fcm.json

volumes:
  # 기존 유지...
  note_embeddings_data:  # pgvector 데이터 분리 고려
```

---

## 14. Grafana 대시보드 (v5.0 추가)

### 14.1 Knowledge Dashboard (v5.0 신규)

```
┌─────────────────────────────────────────────────────────────────┐
│  Flashcard Operations                                            │
│  ├── 일간 복습 카드 수 (전체 / 사용자별 분포)                     │
│  ├── SM-2 quality 분포 (0~5 히스토그램)                         │
│  ├── 평균 EF 추이 / leech 카드 비율                              │
│  ├── 카드 생성 비용 (Unit Economics)                             │
│  └── 복습 완료율 (due 대비 실제 복습)                            │
│                                                                 │
│  Knowledge Notes                                                 │
│  ├── 사용자당 노트 수 분포 (p50/p95/p99)                         │
│  ├── 노트 임베딩 비용 (일간/월간)                                │
│  ├── note_embeddings 캐시 히트율 (chunk_hash)                    │
│  ├── 위키링크 해결률 (resolved / unresolved)                     │
│  ├── 그래프 캐시 생성 지연 (p95)                                 │
│  └── 평균 그래프 크기 (nodes, edges)                             │
│                                                                 │
│  Cross-Module Synergy                                           │
│  ├── 튜터 응답 중 개인 노트 참조 비율                            │
│  ├── 노트 기반 카드 생성 건수 / 수동 생성 대비 비율              │
│  ├── 노트 보유 사용자 vs 미보유 사용자의 mastery 향상 속도       │
│  └── 복습 후 관련 노트 열람 전환율                               │
│                                                                 │
│  알람:                                                           │
│  - 그래프 캐시 생성 실패율 > 5%                                  │
│  - 카드 생성 LLM 비용 일일 한도 도달                             │
│  - note_embeddings cosine 중복률 > 80% (중복 노트 의심)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 15. 기술적 차별화 포인트 (v5.0)

```
🧪 AI 품질 관리 (v4.0 유지)
├── 3층 평가: 사용자 피드백 + 자동(RAGAS+DeepEval) + 인간
├── Importance Sampling + Ground Truth + 학습 성과 A/B 테스트
└── AI-Specific Grafana

🧠 RAG 고도화 (v5.0 확장)
├── Semantic Chunking 하이브리드 (의미 경계 보존)
├── chunk_hash 중복 스킵 + Soft Delete 90일
├── Hybrid Search + Re-ranking + Context Compression
├── source_filter로 강의/노트 이중 도메인 지원                 ← v5.0
└── Vector DB 전환 로드맵 (pgvector → Qdrant)

🔒 컴플라이언스 (v5.0 확장)
├── PII: Input + Output 양방향 + Presidio/KoNLPy
├── 한국 PIPA + EU AI Act 대응
├── AI 채점 투명성 (rubric_coverage + Confidence + Appeal)
├── 감사 로그 (AOP 기반 before/after)
└── 개인 노트 RLS (PostgreSQL 레벨 권한 방어)               ← v5.0

💰 FinOps (v5.0 확장)
├── Unit Economics (세션당·채점당·학습성과당 비용)
├── 예산 기반 동적 모델 라우팅 + Semantic Cache 40~60% 절감
├── 이상 패턴 자동 rate limit
└── 사용자별/플랜별/전사 3계층 Kill-switch                  ← v5.0

🏗️ 아키텍처 (v5.0 확장)
├── AI Gateway + 5 서브서비스 (Knowledge 추가)             ← v5.0
├── Transactional Outbox + Debezium (Holy Trinity)
├── Consumer 멱등성 (dedup_key + Version OCC + DLQ)
├── OTel Distributed Tracing
└── Short-term + Long-term Memory + 개인 노트 컨텍스트      ← v5.0

🧑‍🎓 학습 엔진 (v5.0 완결)
├── 온보딩 Bloom's 배분 + confidence weight
├── concept_mastery 기반 적응형 추천
├── Human-in-the-Loop (rubric_coverage 포함 Confidence)
├── Cold Start 해결 (진단 테스트 + 자가 진단)
├── SM-2 + Bloom 가중 Spaced Repetition                    ← v5.0
└── 개인 지식 그래프 (Obsidian Lite + 의미 검색)           ← v5.0

💫 데이터 네트워크 효과 (v5.0 신규)
├── 사용자 노트 축적 → AI 튜터 개인화 품질 향상
├── 카드 복습 데이터 → concept_mastery 실시간 정밀화
├── 노트-카드-강의 삼중 연결 → 장기 기억 플라이휠
└── 플랫폼 이탈 비용 상승 (개인 자산 락인)
```

---

## 16. 리스크 및 대응 (v5.0 추가)

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|-----------|
| v4.0 기존 리스크 | - | v4.0 문서 참고 (14개 항목) |
| **노트 권한 누수** | 매우 높음 | PostgreSQL RLS + 애플리케이션 이중 필터 + 통합 테스트 강제 |
| **note_embeddings 스케일링** | 높음 | 사용자별 한도 + pgvector 파티션 + Qdrant 전환 대비 |
| **SM-2 예외 케이스 (오입력)** | 중간 | Quality 입력 시 elapsed_ms와 괴리 검증 + 재확인 UX |
| **그래프 뷰 성능 (1000+ 노드)** | 중간 | 서버 좌표 사전 계산 + 클러스터 축약 + 뷰포트 가상화 |
| **위키링크 파서 엣지 케이스** | 낮음 | Flexmark AST 기반 + 골든 테스트 케이스 50+ |
| **카드 생성 LLM 비용 폭주** | 높음 | 사용자 한도 + Semantic Cache + 일괄 생성 강제 |
| **모바일 오프라인 싱크 충돌** | 중간 | LWW(Last Write Wins) + 서버 버전 필드 + 충돌 UI |
| **공유 노트 PII 누수** | 높음 | 공유 전 Output 스캔 강제 통과 + 사용자 확인 2단계 |
| **AI 튜터 노트 참조 프라이버시 우려** | 중간 | Opt-in 기본값 + 설정 토글 + 참조된 노트 로그 가시화 |
| **Phase 7~9 일정 지연** | 중간 | Phase 7/8 독립 배포 + Phase 9를 v5.1로 분리 가능 |
| **Obsidian 대비 기능 부족 비판** | 낮음 | 차별점(AI 튜터 연동)에 집중. 플러그인 생태계는 장기 과제 |

---

## 17. v5.0 교차 시너지 요약 (핵심 내러티브)

v5.0이 단순히 Anki + Obsidian을 베낀 것이 아님을 증명하는 4가지 고유 기능:

```
┌─────────────────────────────────────────────────────────────────┐
│  1. 노트 → 플래시카드 자동 생성                                   │
│     "2주 전 정리한 JPA 노트에서 카드 8장 생성됨"                 │
│     → 학습 자료 작성과 복습 자료 생성을 한 동작으로 통합         │
│                                                                 │
│  2. AI 튜터의 개인 노트 인용                                      │
│     "2주 전 당신이 정리한 '페치 전략' 노트에도 비슷한 내용이..."  │
│     → AI가 학습자의 과거 자기 자신을 인용하는 개인화 극한        │
│                                                                 │
│  3. 복습 카드 → 관련 노트/강의 역추적                             │
│     "이 카드를 틀렸네요. 3주 전 강의 12강 13분 지점을..."         │
│     → 실패가 단순 반복이 아니라 원천 맥락 재탐색 기회             │
│                                                                 │
│  4. concept_mastery 삼중 시그널                                  │
│     퀴즈 결과 + 카드 quality + 노트 작성 빈도 → 정밀 숙련도      │
│     → 학습자가 어느 개념을 진짜로 아는지 다각 측정               │
└─────────────────────────────────────────────────────────────────┘
```

이 네 가지는 **같은 벡터 DB + 같은 Outbox + 같은 AI Gateway**를 공유하기 때문에 가능한 것이며, 별도 Anki + 별도 Obsidian + 별도 LMS를 쓰는 사용자는 절대 얻을 수 없는 경험이다. 이것이 v5.0의 존재 이유.

---

> **문서 끝**
> v5.0 통합 완결본 — v4.0 전체 범위 + Flashcard SRS (SM-2 + Bloom) + Knowledge Notes (Obsidian Lite + pgvector 의미검색 + 그래프뷰) + 교차 시너지 4종.
> 이 문서 하나로 v5.0 전체 설계를 파악할 수 있습니다.
> 다음 문서: 모듈별 상세 설계 (1) Flashcard SRS 상세, (2) Knowledge Notes 상세.
