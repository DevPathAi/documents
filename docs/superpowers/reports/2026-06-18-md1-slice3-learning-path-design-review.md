# MD1 Slice 3 학습경로 설계서 검토 리포트

작성일: 2026-06-18  
대상: `documents/docs/superpowers/specs/2026-06-18-md1-slice3-learning-path-design.md`  
원칙: 대상 설계서와 서비스 코드는 수정하지 않고, 보완 의견만 별도 문서로 기록

## 검토 범위

- 대상 설계서: MD1 슬라이스 #3 학습경로(1st Aha)
- 근거 문서: `02_ERD_문서.md`, `04_API_명세서.md`, `07_요구사항_정의서.md`, `17_스케줄.md`, `19_온보딩_와이어프레임_스펙.md`, `26_학습맥락_자동첨부_구현.md`
- 실제 소스: `devpath-shared`, `devpath-learning-svc`, `devpath-platform-svc`, `devpath-gateway`, `devpath-frontend`, `devpath-ai-svc`
- 외부 1차 문서: Ollama 공식 API 문서(`/api/chat`, `/api/embed`, streaming) 및 Ollama model library

## 총평

설계 방향은 좋다. 슬라이스 #2의 교훈을 이어서 service boundary, outbox, shared schema publish, CI에서 AI 실호출 금지, 프론트 목 SSE 제거를 명확히 잡은 점이 특히 강하다. Claude 중심 원천 문서를 로컬 Ollama로 치환한 결정도 "외부 API 키 제거"라는 개발 현실에는 잘 맞는다.

다만 구현자가 문서 그대로 옮기면 바로 깨질 수 있는 계약이 몇 개 있다. 가장 큰 위험은 Ollama `/api/chat`의 기본 streaming 응답과 strict JSON 파싱의 충돌, `/api/v1` prefix 계약 불명확, pgvector 메인 DB 전환 범위 누락, 프론트의 기존 `step/fromStep/weeks` 모델과 새 `stage/milestones` 계약의 대규모 교체다. 아래 P0/P1은 빌드별 구현 플랜 작성 전에 설계서 또는 플랜에 반영하는 것을 권장한다.

## 핵심 수정 필요 사항

| 우선순위 | 영역 | 요약 | 권장 조치 |
| --- | --- | --- | --- |
| P0 | ai-svc Ollama | `/api/chat`은 기본 streaming이라 strict JSON 파싱과 충돌 | path 생성 요청에 `stream:false`를 명시하거나 NDJSON parser를 구현 |
| P0 | gateway/API prefix | API 명세와 프론트 baseUrl은 `/api/v1`, gateway/service route는 prefix 없음 | gateway에서 `/api/v1/**` 매칭과 StripPrefix를 명시하거나 baseUrl 정책을 통일 |
| P0 | pgvector 전환 | 현재 compose/CI는 5432 postgres와 5433 pgvector 분리, 설계는 5432 pgvector 전환 | shared 및 shared migration 소비 repo CI 전체 전환 범위와 로컬 volume/rerun 절차 명시 |
| P1 | frontend contract | 현재 web은 `step`, `fromStep`, resume, `weeks` 모델에 묶여 있음 | `stage`, 재생성, `milestones` 모델로 바꾸는 breaking migration task/test를 구체화 |
| P1 | FR-PATH | "이번 주 3개 과제"와 "완료 시 역량 수준"이 응답 스키마에서 보장되지 않음 | task cardinality와 target/completion level 필드를 API 계약에 추가 |
| P1 | ai-svc skeleton | 설계는 무상태 gateway지만 실제 ai-svc는 DB/JPA 템플릿 상태 | Build B에 JPA/DataSource/DbConnectionTest/CI postgres 제거 또는 유지 사유 명시 |
| P1 | assessment input | "최신 COMPLETED 직접 조회"는 맞지만 현재 repository에는 join query가 없음 | assessment/result join query, 동률 정렬, 409 정책을 플랜에 내려쓰기 |
| P2 | vector/JPA | Hibernate JPA mapping만으로 `VECTOR(768)`과 `<=>` 쿼리가 애매함 | embedding repository는 JdbcTemplate/native query 기준으로 설계 |

## 상세 검토 결과

### P0-1. Ollama `/api/chat` 기본 streaming과 strict JSON 파싱 충돌

근거:

- 설계서는 ai-svc가 Ollama `POST /api/chat`을 호출하고 structured JSON을 strict 파싱한다고 한다.
- Ollama 공식 `/api/chat` 문서는 `stream` 기본값이 true라고 명시한다.
- Ollama streaming 문서는 streaming 응답이 `application/x-ndjson` 형식이며, structured output처럼 짧고 파싱이 중요한 응답은 non-streaming이 더 단순하다고 안내한다.

영향:

- `RestClient`로 단일 JSON body를 기대하면 Ollama가 여러 NDJSON chunk를 반환해 파싱 실패가 날 수 있다.
- path 생성 실패가 learning-svc SSE의 `generating` 단계에서 사용자에게 "생성 실패"로 노출된다.

권장 보완:

- ai-svc `POST /ai/path/generate`가 Ollama에 보낼 body에 반드시 `"stream": false`를 포함한다고 설계서와 플랜에 명시한다.
- MockWebServer 테스트에 "요청 body에 `format` JSON schema와 `stream:false`가 포함된다"를 추가한다.
- Ollama 응답은 `message.content` 내부 문자열을 다시 JSON parse해야 하므로, 이 2단계 파싱과 schema validation 실패 시 502/재시도 정책도 함께 명시한다.

### P0-2. `/api/v1` prefix 계약이 gateway, frontend, API 명세 사이에서 갈라져 있음

근거:

- `04_API_명세서.md`의 Base URL은 `https://api.devpath.ai/api/v1`이다.
- web `AppConfig` 기본/예시는 `https://.../api/v1` baseUrl을 사용한다.
- gateway route는 현재 `/oauth2/**`, `/auth/**`, `/users/**`, `/onboarding/assessments/**`만 매칭한다.
- learning-svc controller도 `/onboarding/assessments`처럼 prefix 없는 path를 쓴다.
- 대상 설계서의 gateway 보강도 `/learning-paths/**` 추가만 언급한다.

영향:

- 실 환경에서 프론트가 `/api/v1/learning-paths/me/generate`를 호출하면 gateway route가 매칭되지 않을 수 있다.
- 슬라이스 #2 진단 route도 같은 문제를 이미 안고 있어, #3만 구현해도 온보딩 전체 E2E가 깨질 수 있다.

권장 보완:

- 하나를 확정한다.
  - gateway가 `/api/v1/**`를 받는 공식 edge이고, service로 넘길 때 `/api/v1`을 strip한다.
  - 또는 프론트 실API baseUrl에서 `/api/v1`을 제거하고 API 명세를 수정한다.
- 현재 문서 체계상 API 명세가 `/api/v1`을 공식으로 두고 있으므로 gateway route에 `/api/v1/learning-paths/**`, `/api/v1/onboarding/assessments/**`와 StripPrefix/RewritePath를 명시하는 쪽이 자연스럽다.
- gateway test는 prefix 없는 path뿐 아니라 `/api/v1/...` path까지 추가해야 한다.

### P0-3. pgvector 메인 DB 전환 범위가 실제 repo 상태보다 좁게 적혀 있음

근거:

- 대상 설계서는 메인 devpath DB(5432)를 `pgvector/pgvector:pg17`로 전환한다고 한다.
- 현재 `devpath-shared/docker-compose.yml`은 5432 `postgres:17-alpine`, 5433 `pgvector/pgvector:pg17`의 이중 DB다.
- shared, learning, ai, platform CI는 모두 `postgres:17-alpine` service container를 사용한다.
- shared migration에 `VECTOR(768)`이 들어가면 plain postgres CI에서는 extension/type 생성이 실패한다.

영향:

- Build A가 shared에 merge되는 순간 shared CI와 shared migration을 test profile로 적용하는 downstream 서비스 CI가 깨질 수 있다.
- 로컬 개발자는 기존 5432 volume을 그대로 둔 상태에서 extension이 없어 실패하거나, 5433 vector DB와 5432 app DB 중 어느 쪽을 써야 하는지 혼동할 수 있다.

권장 보완:

- Build A 산출에 다음을 명시한다.
  - `devpath-shared/docker-compose.yml`: 5432 postgres 이미지를 `pgvector/pgvector:pg17`로 교체하고 5433 `postgres-vector`는 제거 또는 deprecated.
  - `devpath-shared`, `devpath-learning-svc`, `devpath-platform-svc`, `devpath-ai-svc` CI의 postgres image를 모두 pgvector로 교체. ai-svc가 DB 제거되면 ai-svc는 제외.
  - 로컬 기존 volume 처리: fresh DB 권장, 필요 시 backup 후 `docker compose down -v` 범위 안내.
- Flyway test에는 `CREATE EXTENSION vector`, `content_embeddings.embedding VECTOR(768)`, HNSW index 존재, `<=>` smoke query를 넣는다.

### P1-1. 프론트 path contract migration이 현재 설계보다 큰 작업임

근거:

- 현재 `PathController`는 `step` 값을 읽고 `DONE`이면 `/learning-paths/me`를 조회한다.
- 현재 `path_sse_source.dart`는 `ANALYZE/MAP/BUILD/DONE`, `fromStep`, body `{'fromStep': fromStep}`를 사용한다.
- 현재 `LearningPath` 모델은 `{rationale, weeks[{week,title,tasks[{title,done}]}]}` 형태다.
- 대상 설계서는 `stage`, no server resume, 중단 시 재생성, `milestones`, `diagnosis`, `targetSkills`, `whyThisOrder`, `contentId` 등을 확정한다.

영향:

- `GET /learning-paths/me`가 설계 스키마대로 나오면 기존 `LearningPath.fromJson()`은 필요한 필드를 모두 버리거나 역직렬화에 실패한다.
- `stage` 기반 SSE가 오면 현재 controller는 이벤트를 무시하고 timeout 후 partial로 빠질 수 있다.
- 화면에는 여전히 "이어서 생성"이 남아 설계의 "재생성" 정책과 사용자 경험이 어긋난다.

권장 보완:

- Build E에 다음 task를 명시한다.
  - `PathSseEvent` DTO 추가: `stage`, `progress`, `message`, `pathId`.
  - `fromStep` 제거, partial CTA를 "다시 생성" 또는 "처음부터 생성"으로 교체.
  - dp_core `LearningPath`를 `pathId/track/totalWeeks/diagnosis/milestones/tasks` 구조로 재생성하고 generated files 갱신.
  - 기존 `PathPlanView`가 `weeks`가 아니라 `milestones`를 렌더하도록 교체.
- golden smoke에는 정상 완료와 중단 후 재생성 모두 포함한다.

### P1-2. FR-PATH-005/006이 API 스키마에서 보장되지 않음

근거:

- `07_요구사항_정의서.md`는 "이번 주 3개 과제 노출"과 "예상 소요, 완료 시 역량 수준 표시"를 Must로 둔다.
- 대상 설계서의 `GET /me` 응답은 `estimatedHours`는 있지만, 완료 시 기대 역량 수준을 담는 필드가 없다.
- path 생성 프롬프트의 `tasks` 배열에도 주차별 task 개수 제한이 없다.

영향:

- LLM이 1주차에 1개 또는 5개 task를 반환해도 서버 계약상 실패가 아니다.
- O05에서 "완료 후 어느 수준까지 가는지"를 표시하려면 프론트가 임의 문구를 만들어야 한다.

권장 보완:

- path 생성 schema에 milestone별 `tasks` length를 3으로 제한하거나, 서버가 top 3만 persist한다고 명시한다.
- `GET /learning-paths/me/this-week`는 항상 최대 3개가 아니라 "정확히 3개 또는 seed 부족 시 명시 fallback" 중 하나로 고정한다.
- `GET /me` 또는 milestone에 `targetLevelAfterCompletion`, `expectedCompetency`, `completionOutcome` 같은 필드를 추가한다.
- 테스트에 1주차 task 3개와 completion level 표시 필드 존재를 추가한다.

### P1-3. ai-svc "무상태 gateway" 설계와 현재 템플릿 코드가 충돌

근거:

- 대상 설계서는 ai-svc를 JPA 불요, Redis/Kafka 불요의 Ollama gateway로 둔다.
- 현재 `devpath-ai-svc`는 `spring-boot-starter-data-jpa`, PostgreSQL runtime, datasource 설정, `DbConnectionTest`를 갖고 있다.
- ai-svc CI도 postgres service container를 띄운다.

영향:

- Build B를 "무상태 gateway"로 구현해도 DB 설정이 남아 있으면 로컬/CI에서 불필요한 DB 의존 때문에 context load가 실패할 수 있다.
- pgvector 전환 범위에도 ai-svc가 불필요하게 끌려 들어간다.

권장 보완:

- Build B task에 JPA/datasource/flyway/DbConnectionTest/CI postgres 제거를 명시한다.
- ai-svc가 앞으로 비용추적, cache, audit 때문에 DB를 가질 계획이라면 본 슬라이스에서는 "DB 사용 안 함, 관련 starter 제거 보류" 같은 중간 상태를 명시하고 context load 전략을 확정한다.

### P1-4. 최신 COMPLETED 진단 조회 query가 플랜 수준까지 내려가야 함

근거:

- 대상 설계서는 learning-svc가 `assessment_results`에서 최신 COMPLETED를 직접 조회한다고 한다.
- 현재 `AssessmentRepository`와 `AssessmentResultRepository`는 기본 `JpaRepository`뿐이다.
- `assessment_results`에는 user_id와 track이 없으므로 `assessments` join이 필요하다.

영향:

- 구현자가 result table만 조회하면 user별 최신 결과나 track을 얻을 수 없다.
- 같은 user가 여러 진단을 완료한 경우 어떤 결과를 path input으로 쓸지 구현마다 달라질 수 있다.

권장 보완:

- repository query를 문서화한다.
  - `assessment_results r join assessments a on r.assessment_id=a.id`
  - `a.user_id=:userId and a.status='COMPLETED'`
  - `order by a.completed_at desc, a.id desc limit 1`
- 조회 결과 DTO는 `assessmentId`, `track`, `diagnosedLevel`, `strengthConcepts`, `weaknessConcepts`, `confidenceWeight`를 포함한다.
- 결과가 없으면 409와 error code를 명시한다.

### P1-5. LLM 호출과 DB transaction 경계가 모호함

근거:

- 대상 설계서는 collect -> generate -> matching -> persist/outbox를 한 흐름으로 둔다.
- `영속(..., outbox 동일tx)`는 맞지만, service method 전체를 `@Transactional`로 감싸면 Ollama 호출 중 DB transaction이 오래 열린다.

영향:

- Ollama 모델 cold start나 timeout 시 DB connection/transaction을 오래 점유한다.
- 기존 ACTIVE archive와 신규 ACTIVE 생성이 동시 요청에서 레이스를 만들 수 있다.

권장 보완:

- AI 호출과 embedding query 준비는 transaction 밖에서 수행하고, archive + insert + outbox만 짧은 transaction으로 묶는다고 명시한다.
- 같은 user의 generate/regenerate 동시 요청 정책을 정한다.
  - user별 lock, DB advisory lock, 또는 active path update 조건부 처리 중 하나.
- RestClient timeout, retry 횟수, Ollama 5xx/timeout mapping, user-facing SSE error stage를 문서화한다.

## 문서별 보완 제안

### 설계서 섹션 2: AI 레이어

- `POST /api/chat` body 예시에 `stream:false`, `format:{...json schema...}`, `options:{temperature:0.2}`, `keep_alive` 기본값을 포함한다.
- `qwen2.5`는 tag가 넓다. 기본값을 `qwen2.5:7b`처럼 pin하거나, `OLLAMA_GEN_MODEL` 기본값과 최소 RAM/VRAM 전제를 적는다.
- `/ai/embed`는 Ollama 공식 `/api/embed` 기준으로 `input`이 string 또는 string array임을 명시한다.
- embedding 응답 길이가 768인지 runtime validation하고, 다르면 502 또는 config error로 fail-fast한다.

### 설계서 섹션 3: 데이터 모델

- `content_embeddings.status`는 ERD의 `ACTIVE/INACTIVE`와 설계서의 `ACTIVE/STALE`가 다르다. 본 슬라이스 채택값이 `STALE`이면 CHECK와 후속 문서 정합 계획을 명시한다.
- `path_weekly_tasks.task_type`에서 ERD의 `AR`를 제외하고 `READ/PRACTICE/QUIZ`로 줄인 것은 슬라이스 범위상 타당하다. 다만 후속 AR 추가 시 enum migration 방식이 필요하다.
- `learning_paths.user_id`는 FK 없음이 맞다. 대신 `(user_id,status)` partial unique index로 ACTIVE 1개를 DB가 보장할지, 앱 레이어만 보장할지 더 명확히 정한다.
- Hibernate mapping은 vector column을 entity 필드로 직접 다루기보다 native SQL/JdbcTemplate 전용 repository로 두는 편이 안전하다.

### 설계서 섹션 4~5: API/SSE

- API 명세 예시는 done payload에 `path_id`와 `first_week_tasks`를 쓰고, 설계서는 `pathId`만 쓴다. camelCase를 택한다면 API 명세와 fixture 정리 범위를 명시한다.
- SSE event name을 생략할지 `event: progress`를 둘지 정한다. 현재 dp_core `SseClient`는 event field도 파싱하므로 둘 다 가능하지만, 테스트 fixture와 문서를 맞춰야 한다.
- `POST /learning-paths/me/regenerate`는 동기 200이라고 되어 있다. 재생성이 AI를 호출한다면 p95<8s 내라도 HTTP timeout/UX 리스크가 있으므로 SSE로 통일할지, 동기는 "기존 path archive + 새 generate trigger"인지 더 구체화가 필요하다.

### 설계서 섹션 6: 이벤트/연결

- `LearningPathGeneratedEvent`에 `diagnosedLevel`을 추가할지는 nullable로 남겨도 되지만, shared event test에는 JSON 직렬화/역직렬화 호환성까지 추가해야 한다.
- platform DONE 전이는 `where onboarding_status <> 'DONE'`보다 `where onboarding_status in ('PENDING','IN_PROGRESS')`가 의도가 더 분명하다.
- 이벤트 소비 실패 정책이 슬라이스 #2와 같다면 poison payload skip/DLQ 기준도 같이 반복해 적는 편이 좋다.

### 설계서 섹션 8: gateway

- `/learning-paths/**` route만 추가하면 `/api/v1` 환경에서 매칭되지 않을 수 있다.
- SSE pass-through test는 status/header만 보지 말고 chunk가 buffering 없이 순차 도착하는지 검증해야 한다.
- gateway security permitAll 목록과 `/learning-paths/**` 인증 요구를 `/api/v1` prefix 기준으로도 테스트한다.

### 설계서 섹션 10: 테스트/CI

- pgvector CI 전환 대상 repo 목록을 구체화한다.
- ai-svc가 DB 제거 후에는 CI postgres가 없어야 하며, Ollama는 MockWebServer로만 검증한다.
- learning-svc HNSW IT는 "고정 embedding seed vector + query vector"로 deterministic하게 만든다.
- E2E smoke는 `diagnostic complete -> generate SSE -> GET /me -> platform DONE`까지 한 번에 확인한다. Kafka consumer까지 포함하기 어렵다면 event outbox와 platform consumer는 별도 IT로 쪼갠다.

## 권장 보완 순서

1. Ollama `/api/chat` non-streaming structured output 계약을 먼저 고정한다.
2. `/api/v1` gateway prefix 정책을 확정하고 슬라이스 #2 route까지 함께 정리한다.
3. Build A의 pgvector 전환 범위와 로컬 fresh DB 절차를 확정한다.
4. `GET /me`, SSE, regenerate, `/this-week` 응답 스키마를 FR-PATH 기준으로 보강한다.
5. 프론트 `step/fromStep/weeks` 제거 task를 Build E에 세분화한다.
6. ai-svc DB/JPA 제거 여부를 Build B에 명시한다.
7. assessment latest query와 transaction boundary를 Build C에 명시한다.

## 최종 체크리스트

- [ ] ai-svc Ollama chat 요청에 `stream:false`가 포함된다.
- [ ] `/api/v1/learning-paths/me/generate`가 gateway를 통과해 learning-svc로 도달한다.
- [ ] shared/learning/platform CI가 pgvector image에서 migration test를 통과한다.
- [ ] frontend가 `stage` SSE를 읽고 `fromStep`을 보내지 않는다.
- [ ] `GET /learning-paths/me`는 `milestones` 기반 새 dp_core 모델로 역직렬화된다.
- [ ] `/this-week`는 3개 과제를 보장하거나 seed 부족 fallback을 명시한다.
- [ ] O05는 완료 시 기대 역량 수준을 표시할 수 있다.
- [ ] ai-svc가 무상태라면 DB/JPA/DbConnectionTest/CI postgres가 제거된다.
- [ ] learning-svc가 최신 completed assessment를 user 기준으로 deterministic하게 조회한다.
- [ ] path persist와 outbox 기록은 짧은 transaction 하나로 묶이고, Ollama 호출은 transaction 밖에서 수행된다.

## 참고한 공식 문서

- Ollama API introduction: https://docs.ollama.com/api/introduction
- Ollama chat API: https://docs.ollama.com/api/chat
- Ollama embed API: https://docs.ollama.com/api/embed
- Ollama streaming: https://docs.ollama.com/api/streaming
- Ollama `nomic-embed-text`: https://ollama.com/library/nomic-embed-text
- Ollama `qwen2.5`: https://ollama.com/library/qwen2.5
