# 설계서 - MD2 슬라이스 #4: 콘텐츠 대량화 + 콘텐츠 뷰어/진척 (2026-06-20)

> **상태**: 검토 반영본. 슬라이스 #1(인증), #2(진단), #3(학습경로) 이후 MD2 데모/베타100에 필요한 실데이터와 콘텐츠 소비 경험을 완성한다.
> **위치**: MD2 "2nd Aha + 베타100"의 첫 단계. 선행=슬라이스 #1~#3, 후행=슬라이스 #5 Sandbox, #6 AI 코드리뷰.
> **원칙**: 런타임 LLM 통합 금지(오프라인 생성만), CI에서 Ollama 실호출 금지, shared 마이그레이션은 스키마 전용, 대량 데이터는 승인된 seed 산출물로 관리.

---

## 0. 검토 반영 요약

초안의 큰 방향(콘텐츠 대량화 + 뷰어 + 진척)은 유지한다. 다만 실제 저장소와 대조한 결과 아래 항목을 설계에 반영해야 구현 리스크가 줄어든다.

| 우선순위 | 보강/수정 | 이유 |
|---|---|---|
| P0 | MD2 진단 문항은 `MCQ`/`CODE_READING`만 생성하고 `SHORT_ANSWER`는 제외 | 현재 learning-svc 채점은 제출 JSON과 `answer_key`의 정규화 문자열 동일성 비교다. 서술형은 별도 채점기 없이는 오답 처리/품질 리스크가 크다. |
| P0 | `/contents/**` gateway 라우트 추가를 빌드 범위에 포함 | 현재 gateway learning 라우트는 `/onboarding/assessments/**`, `/learning-paths/**`, `/dashboard/**` 중심이며 콘텐츠 API 경로가 빠져 있다. |
| P1 | `Content` 엔티티/API에 `content_md` 노출 추가 | shared에는 `contents.content_md`가 있으나 현재 learning-svc `Content` 엔티티는 본문 필드를 매핑하지 않는다. 뷰어 API 구현 전 보완 필요. |
| P1 | 콘텐츠 조회 응답 필드는 `markdown`으로 확정 | 현재 web `ContentController`가 `/contents/{id}` 응답에서 `markdown`을 읽는다. 백엔드와 목 픽스처를 camelCase 계약으로 맞춘다. |
| P1 | 콘텐츠 식별자는 `idOrSlug` 지원 | 경로 응답은 `contentId`와 `contentSlug`를 둘 다 제공하고, 프론트 라우트는 `/content/:id` 형태다. 숫자 id와 slug 둘 다 조회 가능하게 해 전환 비용을 낮춘다. |
| P1 | 완료 판정은 `scrollPct` 단독이 아니라 `scrollPct + dwellSec`로 확정 | 사용자가 스크롤바만 끝까지 끌어도 완료되는 문제를 줄인다. MVP에서는 클라이언트 신뢰 모델을 허용하되 임계값을 명시한다. |
| P2 | 생성 산출물의 SSoT를 승인 JSON + seed SQL로 분리 | Ollama 출력은 비결정적이다. 승인된 JSON과 그로부터 생성한 seed SQL만 재현 가능한 산출물로 본다. |

## 1. 목적과 완료 기준

### 1.1 목적

현재 저장소 기준으로 진단 문항은 BACKEND_SPRING 17개 수준의 dev/test seed만 있고, `contents`/`content_embeddings`는 스키마와 테스트 fixture 중심이다. 이 상태에서는 슬라이스 #2 진단이 다른 track에서 비어 있고, 슬라이스 #3 경로 엔진도 실제 매칭할 콘텐츠가 부족하다.

슬라이스 #4는 다음 두 가지를 끝단간으로 완성한다.

1. **데이터 대량화**: 5개 track에 대해 진단 문항 500개(각 100개)와 학습 콘텐츠 150편(각 30편)을 생성, 검수, seed로 적재한다.
2. **콘텐츠 소비 경험**: 사용자가 경로 과제의 콘텐츠를 열고, Markdown 본문을 읽고, 진척이 저장되며, 임계 도달 시 해당 경로 task가 완료 처리되게 한다.

### 1.2 완료 기준(DoD)

- `question_bank`에 5개 track 각각 100개, 총 500개 승인 문항이 적재된다.
- `contents`에 5개 track 각각 30편, 총 150편 `PUBLISHED` 콘텐츠가 적재된다.
- 각 콘텐츠의 chunk embedding이 `content_embeddings`에 `ACTIVE`로 적재되고, 슬라이스 #3 HNSW 매칭 테스트가 실제 콘텐츠로 통과한다.
- `GET /contents/{idOrSlug}`가 인증 사용자에게 Markdown 본문과 메타데이터, 본인 진척을 반환한다.
- `POST /contents/{idOrSlug}/progress`가 `user_content_progress`를 멱등 upsert하고, 완료 임계값 도달 시 ACTIVE 학습경로의 연결 task를 자동 완료한다.
- web에서 Path의 이번 주 과제 클릭 -> 콘텐츠 뷰어 진입 -> 스크롤/체류 진척 전송 -> Path/Dashboard 완료율 반영 흐름이 실 API로 동작한다.
- shared, learning-svc, gateway, frontend 테스트가 CI에서 녹색이며, CI는 Ollama를 실호출하지 않는다.

### 1.3 범위 외

- admin 콘텐츠 CRUD와 검수 UI. 이번 슬라이스는 파일 기반 검수/승인 산출물로 충분하다.
- 런타임 콘텐츠 생성, 런타임 문제 생성, 사용자별 동적 추천 엔진.
- `SHORT_ANSWER` 자동 채점, LLM 기반 답안 평가.
- 학습 노트, 북마크, 좋아요, 댓글, 콘텐츠 검색.
- Sandbox 실행/코드 제출. 콘텐츠 안의 코드블록은 후속 슬라이스 입력으로만 둔다.

## 2. 현재 상태

### 2.1 이미 있는 것

- shared:
  - `question_bank`, `assessments`, `assessment_items`, `assessment_results`.
  - `learning_paths`, `path_milestones`, `path_weekly_tasks`, `contents`, `content_embeddings`.
  - `content_embeddings.embedding VECTOR(768)` + HNSW 인덱스, `status ACTIVE/INACTIVE`.
- learning-svc:
  - dev profile `QuestionBankSeeder`가 BACKEND_SPRING 샘플 17개만 적재.
  - test seed도 BACKEND_SPRING 17개.
  - `Content` 엔티티는 일부 메타만 매핑되어 있고 `content_md` 본문 매핑은 없음.
  - 학습경로 조회는 task의 `contentId`/`contentSlug`/`completed`를 내려준다.
  - 콘텐츠 뷰어 API와 사용자 콘텐츠 진척 저장은 없음.
- gateway:
  - learning 라우트에 `/onboarding/assessments/**`, `/learning-paths/**`, `/dashboard/**`가 있음.
  - `/contents/**` 라우트는 없음.
- frontend:
  - `/content/:id` 라우트와 `ContentPage`가 있음.
  - `ContentController`는 `GET /contents/{id}` 응답의 `markdown` 필드를 기대한다.
  - 현재는 목 fixture `GET /contents/c1`만 존재하고, 스크롤 진척 전송은 없음.

### 2.2 이번 슬라이스가 추가/수정할 것

- shared: `user_content_progress` 테이블.
- learning-svc:
  - `tools/content-gen/` 오프라인 배치.
  - 승인 JSON/seed SQL 적재 경로.
  - `Content` 엔티티의 `content_md` 매핑.
  - 콘텐츠 조회/진척 API.
  - 진척 완료 시 `path_weekly_tasks.completed_at` 갱신.
- gateway: `/contents/**` learning 라우트와 보호 경로 테스트.
- frontend:
  - Path task 클릭 진입.
  - 콘텐츠 응답 모델 확장.
  - 스크롤/체류 시간 기반 progress POST.
  - 완료 후 Path/Dashboard refresh.

## 3. 확정 결정

| # | 항목 | 결정 |
|---|---|---|
| D-1 | 범위 | 콘텐츠/문항 데이터 대량화 + 콘텐츠 뷰어 API + 진척 추적 |
| D-2 | 생성 방식 | 로컬 Ollama 초안 생성 + 자동 검증 + 사람 수검수 |
| D-3 | 런타임 | 런타임 LLM 통합 없음. 생성은 오프라인 배치만 수행 |
| D-4 | 생성 모델 | `qwen2.5:7b`, Ollama `/api/chat`, `stream:false`, structured JSON schema |
| D-5 | 임베딩 모델 | `nomic-embed-text`, 768차원. 응답 길이 768 fail-fast |
| D-6 | 데이터 규모 | 문항 500개(5 track x 100), 콘텐츠 150편(5 track x 30) |
| D-7 | 진단 문항 타입 | MD2는 `MCQ` 70%, `CODE_READING` 30%, `SHORT_ANSWER` 0% |
| D-8 | SSoT | 승인 JSON + 생성 seed SQL. raw AI output은 검수 참고물이지 운영 SSoT가 아님 |
| D-9 | 진척 저장 | 신규 `user_content_progress`, `user_id`는 논리 참조(FK 없음), `content_id`는 learning 내부 FK |
| D-10 | 완료 판정 | `scrollPct >= 0.8` AND `dwellSec >= 45` 기본값. 둘 다 설정으로 override 가능 |
| D-11 | task 자동완료 | 해당 사용자 ACTIVE path의 `content_id` 일치 task만 idempotent 완료 처리 |
| D-12 | API prefix | 기존 컨벤션대로 bare path 사용: `/contents/**` |

track enum은 기존 슬라이스와 동일하다.

`BACKEND_SPRING, FRONTEND_REACT, MOBILE_FLUTTER, DEVOPS, FULLSTACK`

## 4. 데이터 대량화 설계

### 4.1 배치 위치

배치는 learning 도메인 데이터(question_bank/contents)를 소유하는 `devpath-learning-svc`에 둔다.

```text
devpath-learning-svc/
  tools/
    content-gen/
      README.md
      package.json 또는 build.gradle task
      schemas/
        question.schema.json
        content.schema.json
        manifest.schema.json
      prompts/
        question-system.md
        content-system.md
        tracks/
          backend-spring.md
          frontend-react.md
          mobile-flutter.md
          devops.md
          fullstack.md
      generated/
        raw/          # Ollama 원본 출력, 커밋 선택
        approved/     # 사람 검수 완료 JSONL, 커밋 대상
        seeds/        # SQL seed 산출물, 커밋 대상
      src/
        generate-questions.*
        generate-contents.*
        validate.*
        make-seed-sql.*
        embed-contents.*
```

언어는 레포의 기존 개발 편의에 맞춰 선택하되, 조건은 아래와 같다.

- CI에서 schema validation과 seed SQL 검증이 가능해야 한다.
- Ollama 호출부는 mock 가능해야 한다.
- JSON schema validation 실패 시 seed 생성이 중단되어야 한다.
- 생성 스크립트는 같은 승인 JSON으로 같은 seed SQL을 만들 수 있어야 한다.

### 4.2 생성 파이프라인

```text
track별 prompt
  -> Ollama qwen2.5:7b (stream:false, JSON schema)
  -> raw JSONL
  -> 자동 검증(schema, enum, quota, 중복, answer_key)
  -> 사람 수검수
  -> approved JSONL
  -> question/content seed SQL 생성
  -> content chunking
  -> ai-svc /ai/embed 또는 Ollama embed offline 호출
  -> content_embeddings seed SQL 생성
  -> learning-svc test/dev seed 검증
```

운영/데모 데이터 적재는 마이그레이션이 아니라 seed로 한다. shared Flyway는 스키마만 담당한다.

### 4.3 문항 데이터 계약

MD2 승인 문항은 아래 필드를 가진다.

```json
{
  "track": "BACKEND_SPRING",
  "questionType": "MCQ",
  "content": "문항 본문. 코드가 있으면 fenced code block 사용.",
  "options": ["선택지 A", "선택지 B", "선택지 C", "선택지 D"],
  "answerKey": {"correct": 2},
  "bloomLevel": "APPLY",
  "difficulty": 0.6,
  "conceptTags": ["spring-tx", "transaction-boundary"],
  "explanation": "검수용 해설. DB 적재 대상 아님 또는 별도 메타로만 보관."
}
```

적재 시 DB 컬럼은 기존 snake_case를 사용한다.

- `question_type`: `MCQ` 또는 `CODE_READING`.
- `answer_key`: 반드시 `{"correct": <0-based index>}`.
- `options`: 4개 권장, 최소 2개. `correct` index는 options 범위 안이어야 한다.
- `difficulty`: 0.0~1.0, 소수 1자리 권장.
- `concept_tags`: 2~5개, kebab-case 권장.
- `explanation`: 검수용. 현재 `question_bank`에는 컬럼이 없으므로 운영 DB에는 넣지 않는다.

`SHORT_ANSWER`는 schema상 가능하더라도 MD2 seed에는 넣지 않는다. 별도 답안 평가기와 테스트가 생긴 뒤 후속 슬라이스에서 활성화한다.

### 4.4 문항 quota

track당 100개를 아래 비율로 생성한다.

| 구분 | quota/track | 비고 |
|---|---:|---|
| MCQ | 70 | 개념 이해, 적용 판단 |
| CODE_READING | 30 | 짧은 코드/설정/SQL/로그 해석 |
| SHORT_ANSWER | 0 | MD2 제외 |

난이도 분포:

| difficulty band | quota/track |
|---|---:|
| 0.1~0.2 | 10 |
| 0.3~0.4 | 25 |
| 0.5~0.6 | 30 |
| 0.7~0.8 | 25 |
| 0.9 | 10 |

Bloom 분포:

| bloom_level | quota/track | 비고 |
|---|---:|---|
| REMEMBER | 10 | 용어/기본 사실 |
| UNDERSTAND | 25 | 개념 구분 |
| APPLY | 30 | 상황 적용 |
| ANALYZE | 25 | 코드/원인 분석 |
| EVALUATE | 10 | 설계 선택 판단 |
| CREATE | 0 | 자동 채점 부재로 MD2 제외 |

### 4.5 콘텐츠 데이터 계약

승인 콘텐츠는 아래 필드를 가진다.

```json
{
  "slug": "backend-spring-transaction-boundary",
  "title": "스프링 트랜잭션 경계 잡기",
  "track": "BACKEND_SPRING",
  "markdown": "## 문제 상황\n\n...",
  "estimatedMinutes": 8,
  "difficulty": 0.5,
  "bloomLevel": "APPLY",
  "conceptTags": ["spring-tx", "transaction-boundary", "jpa"],
  "status": "PUBLISHED"
}
```

작성 규칙:

- slug는 track prefix를 포함한 lowercase kebab-case로 한다.
- 본문은 Markdown만 허용한다. raw HTML은 금지한다.
- H2/H3 중심 구조, 코드블록은 fenced code block만 사용한다.
- 각 콘텐츠는 하나의 핵심 개념을 다루고, 6~12분 분량을 기본으로 한다.
- `conceptTags`는 진단 문항 tag와 최대한 같은 taxonomy를 사용한다.
- `status`는 승인 seed에서는 `PUBLISHED`만 사용한다. 초안은 승인 JSON에 들어오면 안 된다.

### 4.6 콘텐츠 quota

track당 30편, 총 150편.

| 난이도 | quota/track |
|---|---:|
| 입문(0.1~0.3) | 8 |
| 중급(0.4~0.6) | 14 |
| 심화(0.7~0.9) | 8 |

콘텐츠 유형은 별도 DB 컬럼이 없으므로 title/tag/본문 구조로 표현한다. 단, 후속 Sandbox 연결을 위해 track당 최소 10편은 실행 가능한 코드블록 또는 설정 예시를 포함한다.

### 4.7 임베딩 생성

- chunk 기준: H2 섹션 우선, 너무 긴 섹션은 800~1,200자 단위로 분할, 120자 내외 overlap 허용.
- `chunk_index`: content별 0부터 증가.
- `chunk_hash`: normalized `chunk_text`의 SHA-256 hex.
- embedding은 `nomic-embed-text` 768차원만 허용한다.
- `content_embeddings.status`: 신규 seed는 `ACTIVE`.
- 같은 `content_id + chunk_hash`가 이미 있으면 중복 생성하지 않는다.

임베딩 seed SQL은 커밋 가능한 산출물로 만들되, 파일이 과도하게 커질 경우 `approved/content_embeddings.jsonl` + 적재 스크립트 조합을 허용한다. 이 경우에도 CI는 Ollama 없이 fixture embedding으로 적재/조회 테스트를 통과해야 한다.

### 4.8 자동 검증

승인 전 자동 검증에서 하나라도 실패하면 seed SQL을 만들지 않는다.

- JSON schema 필수 필드 검증.
- track/questionType/bloom/status enum 검증.
- difficulty 범위 검증.
- `answerKey.correct` 범위 검증.
- MD2 금지 타입(`SHORT_ANSWER`, `CREATE`) 검출.
- slug uniqueness 검증.
- normalized content/question hash 기반 완전 중복 검출.
- track별 quota 검증.
- concept tag 공백/대문자/한글 혼용 정책 검증. 기본은 kebab-case 영문.
- Markdown code fence 닫힘 검증.
- embedding 차원 768 검증.

### 4.9 사람 수검수

문항은 정답 정확성이 제품 신뢰를 직접 훼손하므로 더 엄격하게 본다.

- 문항: track별 100개 전수 검토. 특히 `answerKey.correct`와 해설을 확인한다.
- 콘텐츠: track별 최소 30% 샘플 검토 + 제목/slug/개념 tag 전수 확인.
- 검수자는 승인 JSONL에만 반영한다. raw 출력은 직접 seed로 변환하지 않는다.
- 검수 완료 기준: track별 quota 충족, 중복 없음, 정답 오류 0개, 명백한 환각/구버전 API 설명 제거.

## 5. 데이터 모델

### 5.1 기존 스키마 사용

기존 shared 스키마를 그대로 사용한다.

- `question_bank`
- `contents`
- `content_embeddings`
- `learning_paths`
- `path_milestones`
- `path_weekly_tasks`

단, learning-svc 구현에서는 `contents.content_md`를 JPA 엔티티 또는 전용 projection에 반드시 매핑한다.

### 5.2 신규 `user_content_progress`

shared 마이그레이션으로 추가한다.

```sql
CREATE TABLE user_content_progress (
  id           BIGSERIAL PRIMARY KEY,
  user_id      BIGINT NOT NULL,
  content_id   BIGINT NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
  scroll_pct   DOUBLE PRECISION NOT NULL DEFAULT 0,
  dwell_sec    INT NOT NULL DEFAULT 0,
  completed_at TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_ucp_user_content UNIQUE (user_id, content_id),
  CONSTRAINT chk_ucp_scroll CHECK (scroll_pct >= 0 AND scroll_pct <= 1),
  CONSTRAINT chk_ucp_dwell CHECK (dwell_sec >= 0)
);

CREATE INDEX idx_ucp_user_updated ON user_content_progress(user_id, updated_at DESC);
CREATE INDEX idx_ucp_content ON user_content_progress(content_id);
CREATE TRIGGER user_content_progress_set_updated_at BEFORE UPDATE ON user_content_progress
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

서비스 경계 원칙:

- `user_id`는 platform `users`의 논리 참조다. 교차서비스 FK를 두지 않는다.
- `content_id`는 learning 도메인 내부 FK다.

## 6. 콘텐츠 API 계약

인증은 슬라이스 #1~#3과 동일하게 HS256 JWT를 `oauth2ResourceServer`로 검증한다. `userId = jwt.subject`다.

### 6.1 `GET /contents/{idOrSlug}`

숫자면 `contents.id`, 숫자가 아니면 `contents.slug`로 조회한다. `PUBLISHED`만 반환한다.

응답:

```json
{
  "id": 1,
  "slug": "backend-spring-transaction-boundary",
  "title": "스프링 트랜잭션 경계 잡기",
  "track": "BACKEND_SPRING",
  "markdown": "## 문제 상황\n\n...",
  "estimatedMinutes": 8,
  "difficulty": 0.5,
  "bloomLevel": "APPLY",
  "conceptTags": ["spring-tx", "transaction-boundary"],
  "progress": {
    "scrollPct": 0.42,
    "dwellSec": 73,
    "completed": false,
    "completedAt": null
  }
}
```

주의:

- 응답 필드는 camelCase.
- 본문 필드는 DB의 `content_md`를 `markdown`으로 노출한다.
- 콘텐츠는 공용 리소스이므로 owner 검증은 하지 않는다. 다만 progress는 요청 사용자 기준으로만 조회한다.

### 6.2 `POST /contents/{idOrSlug}/progress`

요청은 현재 콘텐츠 뷰 세션의 **누적** 값을 보낸다. delta가 아니다.

```json
{
  "scrollPct": 0.86,
  "dwellSec": 91
}
```

서버 upsert 규칙:

- `scroll_pct = greatest(existing.scroll_pct, request.scrollPct)`
- `dwell_sec = greatest(existing.dwell_sec, request.dwellSec)`
- 완료 임계 도달 전이면 `completed_at`은 그대로 둔다.
- 완료 임계 도달 시 `completed_at = coalesce(existing.completed_at, now())`.
- 이미 완료된 progress는 이후 낮은 값으로 되돌릴 수 없다.

응답:

```json
{
  "contentId": 1,
  "scrollPct": 0.86,
  "dwellSec": 91,
  "completed": true,
  "completedAt": "2026-06-20T12:34:56Z",
  "taskCompletedCount": 1
}
```

완료 판정 기본값:

- `devpath.content.completion.scroll-threshold=0.8`
- `devpath.content.completion.min-dwell-sec=45`

### 6.3 `GET /contents/me/progress`

사용자의 콘텐츠 진척 목록을 최신순으로 반환한다.

Query:

- `completed=true|false` 선택.
- `track=BACKEND_SPRING` 선택.
- `limit` 기본 50, 최대 100.

응답:

```json
{
  "items": [
    {
      "contentId": 1,
      "slug": "backend-spring-transaction-boundary",
      "title": "스프링 트랜잭션 경계 잡기",
      "track": "BACKEND_SPRING",
      "scrollPct": 0.86,
      "dwellSec": 91,
      "completed": true,
      "completedAt": "2026-06-20T12:34:56Z",
      "updatedAt": "2026-06-20T12:34:56Z"
    }
  ]
}
```

### 6.4 에러 정책

| 상황 | HTTP | code |
|---|---:|---|
| 인증 없음/토큰 오류 | 401 | `UNAUTHORIZED` |
| 콘텐츠 없음 또는 unpublished | 404 | `CONTENT_NOT_FOUND` |
| progress 값 범위 오류 | 400 | `INVALID_PROGRESS` |
| idOrSlug 형식은 맞지만 내부 변환 실패 | 400 | `INVALID_CONTENT_ID` |

## 7. 진척 -> task 자동완료

progress 완료 시 learning-svc는 같은 트랜잭션에서 ACTIVE path의 연결 task를 완료한다.

```sql
UPDATE path_weekly_tasks t
SET completed_at = COALESCE(t.completed_at, now())
FROM path_milestones m
JOIN learning_paths p ON p.id = m.path_id
WHERE t.milestone_id = m.id
  AND p.user_id = :userId
  AND p.status = 'ACTIVE'
  AND t.content_id = :contentId
  AND t.completed_at IS NULL;
```

정책:

- ACTIVE path만 갱신한다. ARCHIVED path는 건드리지 않는다.
- 같은 ACTIVE path 안에 같은 콘텐츠가 여러 task에 연결되어 있으면 모두 완료한다.
- 이미 완료된 task는 그대로 둔다.
- 경로 밖 콘텐츠를 읽은 경우 progress만 저장되고 task 완료 수는 0이다.
- 완료 후 Dashboard의 `progressPercent`는 기존 `path_weekly_tasks.completed_at` 기반 계산을 재사용한다.

## 8. 아키텍처 흐름

### 8.1 오프라인 생성/적재

```text
Ollama qwen2.5:7b
  -> raw questions/contents
  -> schema + quota validation
  -> human review
  -> approved JSONL
  -> seed SQL
  -> learning DB(question_bank, contents, content_embeddings)
```

### 8.2 런타임 콘텐츠 소비

```text
Path task(contentId/contentSlug)
  -> web /content/:id
  -> GET /contents/{idOrSlug}
  -> Markdown render
  -> throttled POST /contents/{idOrSlug}/progress
  -> user_content_progress upsert
  -> threshold reached
  -> ACTIVE path_weekly_tasks.completed_at update
  -> Path/Dashboard refresh
```

## 9. 빌드 분해

| 빌드 | 레포 | 산출 | 비고 |
|---|---|---|---|
| A | devpath-shared | `user_content_progress` 마이그레이션 + FlywayMigrationTest | schema only, develop -> main 릴리스 선행 |
| B1 | devpath-learning-svc | `tools/content-gen` 문항 생성/검증 + 승인 문항 500 seed | CI는 Ollama mock/fixture만 |
| B2 | devpath-learning-svc | 콘텐츠 생성/검증 + 승인 콘텐츠 150 seed + embedding seed/loader | `contents`, `content_embeddings` 적재 |
| C | devpath-learning-svc | 콘텐츠 조회/진척 API, `Content.contentMd` 매핑, task 자동완료 | 핵심 런타임 빌드 |
| D | devpath-gateway | `/contents/**` -> learning 라우트 + 보호 경로 테스트 | bare path 유지 |
| E | devpath-frontend | Path task 클릭, Content 모델/화면, progress tracking POST, refresh | 목 fixture와 실계약 정합 |

권장 순서:

```text
A -> C contract skeleton -> D -> E
         \
          B1/B2 데이터 배치와 seed는 병렬 진행 가능
```

데모 완성은 B1/B2 seed 적재 후 C/D/E 통합 검증까지 포함한다.

## 10. 구현 메모

### 10.1 learning-svc

- `Content` 엔티티에 `@Column(name = "content_md") private String contentMd;`를 추가하거나 뷰어 전용 projection을 만든다.
- `ContentRepository`에 `findByIdAndStatus`, `findBySlugAndStatus` 또는 idOrSlug 전용 query를 추가한다.
- progress upsert는 JPA save보다 native SQL `INSERT ... ON CONFLICT ... DO UPDATE`가 단순하다.
- task 자동완료도 native update가 적합하다.
- 완료 임계값은 `@ConfigurationProperties`로 둔다.
- Controller 응답 DTO는 camelCase record로 고정한다.

### 10.2 gateway

`application.yml`과 `application-test.yml`의 learning route Path predicate에 `/contents/**`를 추가한다.

```yaml
- Path=/onboarding/assessments/**,/learning-paths/**,/dashboard/**,/contents/**
```

보호 정책:

- `/contents/**`는 인증 필요.
- guest/public 콘텐츠 공개는 후속 결정으로 미룬다.

### 10.3 frontend

- `ContentState`는 단순 markdown 문자열이 아니라 `LearningContent` 모델을 들고 있어야 한다.
- `ContentController.load(idOrSlug)`는 GET 응답 전체를 파싱한다.
- `ContentPage`는 `ScrollController`와 타이머로 누적 dwellSec을 계산한다.
- progress POST는 다음 조건에서 throttle한다.
  - 최초 렌더 후 5초 이상 경과.
  - scrollPct가 마지막 전송 대비 0.1 이상 증가.
  - 화면 dispose/visibility hidden.
  - 완료 임계값 도달.
- `PathPlanView`의 task는 `contentSlug ?? contentId`가 있으면 `/content/{target}`으로 이동한다.
- progress 완료 응답을 받으면 현재 Path/Dashboard provider를 invalidate 또는 refresh한다.

## 11. 테스트 전략

### 11.1 shared

- `user_content_progress` 테이블 존재.
- unique `(user_id, content_id)` 존재.
- scroll/dwell check constraint 검증.
- `updated_at` trigger 검증.
- `content_id` cascade delete 검증.

### 11.2 배치(B1/B2)

- JSON schema validation 단위 테스트.
- track별 quota 테스트.
- `SHORT_ANSWER`/`CREATE` 금지 테스트.
- answerKey index 범위 테스트.
- Markdown fence 검증 테스트.
- seed SQL 생성 결정성 테스트(같은 approved JSON -> 같은 SQL).
- Ollama 호출부는 MockWebServer/fixture. CI에서 실제 Ollama 호출 금지.
- embedding loader는 768차원 fixture로만 CI 검증.

### 11.3 learning-svc

- `GET /contents/{numericId}` 성공.
- `GET /contents/{slug}` 성공.
- `DRAFT` 또는 없는 slug는 404.
- 응답에 `markdown`, `conceptTags`, `progress` 포함.
- `POST /progress` 첫 요청 insert.
- 낮은 scrollPct/dwellSec 재전송 시 값이 감소하지 않음.
- 임계 미달이면 `completedAt` null.
- 임계 도달이면 `completedAt` set.
- ACTIVE path의 연결 task만 완료.
- ARCHIVED path task는 변경되지 않음.
- 같은 content_id가 여러 task에 있으면 `taskCompletedCount`가 실제 갱신 수와 일치.
- Dashboard progressPercent가 완료 task 기준으로 증가.

### 11.4 gateway

- 인증 없이 `/contents/{id}` 요청 시 401.
- 인증 토큰 포함 시 learning route로 프록시.
- `/contents/**` route가 main/test yml 모두에 존재.

### 11.5 frontend

- mock `GET /contents/c1`로 Markdown 렌더.
- path task 클릭 시 `/content/{contentSlug}` 이동.
- scroll/dwell 조건 충족 시 progress POST.
- progress 완료 응답 후 task completed UI 또는 refresh flow 확인.
- API 에러 시 retry UI.

## 12. 운영/데모 적재 절차

1. Ollama 모델 준비: `qwen2.5:7b`, `nomic-embed-text`.
2. `tools/content-gen`으로 track별 raw JSON 생성.
3. 자동 검증 실행.
4. 사람 수검수 후 `generated/approved/*.jsonl` 갱신.
5. seed SQL 생성.
6. fresh DB에 shared migration 적용.
7. seed SQL 적재.
8. count/coverage 검증:
   - `question_bank`: 500, track별 100.
   - `contents`: 150, track별 30, all PUBLISHED.
   - `content_embeddings`: content별 1개 이상 ACTIVE chunk.
9. learning-svc 통합 테스트와 web smoke:
   - 진단 -> 경로 생성 -> task 클릭 -> 콘텐츠 읽기 -> task 완료 -> dashboard 완료율 반영.

## 13. 리스크와 대응

| 리스크 | 대응 |
|---|---|
| AI 생성 문항 정답 오류 | 문항 전수 검수, answerKey 자동 범위 검증, 해설 필드로 검수 보조 |
| 현 채점기와 문항 타입 불일치 | MD2는 `MCQ`/`CODE_READING`만 허용 |
| seed SQL 과대화 | approved JSON + loader 허용. CI는 fixture embedding으로 검증 |
| 사용자가 progress를 조작 가능 | MD2에서는 저위험 신호로 취급. 결제/인증서/성취 배지와 연결 전 서버 신뢰 모델 재설계 |
| scroll 이벤트/visibility 이벤트 누락 | throttle + dispose flush + 수동 재진입 시 monotonic upsert |
| 콘텐츠 tag taxonomy 분산 | track별 prompt에 canonical tag 목록 제공, 검증기로 kebab-case/중복 검사 |
| embedding 모델 변경 | `source_embedding_version`/manifest에 모델 기록, 변경 시 재임베딩 |

## 14. 플랜 확정 대상

아래는 구현 플랜에서 파일 단위로 확정한다.

1. `tools/content-gen`의 구현 언어와 실행 명령.
2. approved JSON/seed SQL의 최종 커밋 경로.
3. content embedding seed를 SQL로 커밋할지 JSONL+loader로 둘지.
4. track별 canonical concept tag 목록.
5. frontend progress flush의 정확한 throttle 값.
6. `GET /contents/me/progress`를 MD2 화면에서 노출할지, API만 먼저 둘지.

## 15. 관련 문서

- 슬라이스 #2 진단 설계: `documents/docs/superpowers/specs/2026-06-18-md1-slice2-diagnostic-design.md`
- 슬라이스 #3 학습경로 설계: `documents/docs/superpowers/specs/2026-06-18-md1-slice3-learning-path-design.md`
- 스케줄 재정렬 설계: `documents/docs/superpowers/specs/2026-06-16-schedule-rework-design.md`
- shared schema: `devpath-shared/src/main/resources/db/migration/V202606181001__question_bank.sql`, `V202606181006__learning_path_schema.sql`
- learning-svc 현재 seed: `devpath-learning-svc/src/main/java/ai/devpath/learning/seed/QuestionBankSeeder.java`
