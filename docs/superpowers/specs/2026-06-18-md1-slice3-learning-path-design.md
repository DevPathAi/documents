# 설계서 — MD1 슬라이스 #3: 학습경로(1st Aha) (2026-06-18)

> **상태**: 설계 확정(브레인스토밍 승인 2026-06-18). 다음 = 빌드별 구현 플랜(writing-plans).
> **위치**: MD1 핵심 — "1st Aha 실연동". 가입(OAuth)→진단→**개인화 학습경로**가 web 끝단간 실API로 동작. 선행=슬라이스 #1(인증)·#2(진단, 완료). 후행=슬라이스 #4(콘텐츠).
> **원칙**: 각 레포 CLAUDE.md 절대조건(추측 금지·테스트 우선·문제 시 코드 분석) + 브랜치 전략(main 보호·develop 경유 2단계 PR) + 서브에이전트 Scope Lock.
> **근거 사양**: `17_스케줄.md §2(슬라이스#3)·§6`, `02_ERD_문서.md §학습경로·콘텐츠`, `04_API_명세서.md §학습경로·§3.1 SSE`, `07_요구사항_정의서.md FR-PATH·NFR-AHA/PERF`, `19_온보딩_와이어프레임_스펙.md O04/O05`, `26_학습맥락`, 슬라이스 #2 설계서. Ollama API는 context7 `/ollama/ollama`로 검증.

---

## 1. 목적·완료 기준·핵심 결정

- **목적**: 진단을 마친 회원에게 Claude급 LLM(이번 슬라이스는 **로컬 Ollama**)이 생성한 개인화 12주 학습경로를, 진행 SSE 스트리밍과 함께 제공하고 pgvector로 실제 콘텐츠를 매칭한다. "오늘의 학습 시작" 단일 CTA로 1st Aha를 완성한다.
- **DoD**: web에서 진단 완료→`POST /learning-paths/me/generate`(SSE 진행)→경로 생성·영속·콘텐츠 매칭→`GET /learning-paths/me` 결과 표시(O05 강·약점·로드맵·이번주 과제)→`onboarding_status` DONE 전이. 가입→진단→경로 **p50<8분(staging)**, 경로 생성 **p95<8s**(NFR-PERF-003). 단위·통합·끝단간 테스트 녹색.
- **확정 결정**:
  1. **범위 Full**: Claude→**Ollama** 경로 생성 + contents 임베딩 + pgvector HNSW 매칭 + 소량 시드 콘텐츠.
  2. **소유**: **learning-svc**가 path 도메인(테이블·SSE 서빙·`LearningPathGeneratedEvent` 발행) 소유. **ai-svc = 로컬 Ollama 게이트웨이**(생성·임베딩 LLM 호출 일원화).
  3. **AI = 로컬 Ollama**(외부 API 키 제거). 임베딩 `nomic-embed-text`(768차원), 생성 `qwen2.5`(structured JSON), 둘 다 env override.
  4. **진단 입력**: learning-svc가 자체 `assessment_results` 직접 조회(assessments·path 동일 서비스 소유 → 이벤트/외부 API 불요).
  5. **DONE 전이**: platform이 `LearningPathGeneratedEvent` 소비 → `onboarding_status` DONE(슬라이스 #2 C 패턴).
- **범위 외**: 실 대량 콘텐츠(슬라이스 #4), GitHub 활동 심층 연동(deferred), AI 멘토 채팅, 비용추적/Semantic Cache/kill-switch 고도화(ai-svc는 게이트웨이 골격만), SSE 서버측 부분재개(resume), 임베딩 운영 품질 튜닝.

## 2. AI 레이어 — 로컬 Ollama (ai-svc 게이트웨이)

- **ai-svc**(스켈레톤→구현): 모든 LLM 호출의 단일 진입점. 대상은 외부 API가 아닌 **로컬 Ollama**(`OLLAMA_BASE_URL`, 기본 `http://localhost:11434`). 2 엔드포인트:
  - `POST /ai/embed` { texts: [String] } → { embeddings: [[float]] } — Ollama `POST /api/embed`(model=`nomic-embed-text`, input=배치) 위임.
  - `POST /ai/path/generate` { track, diagnosedLevel, strengthConcepts, weaknessConcepts, goal? } → { rationale, milestones:[{weekNum,title,goalDescription,targetSkills,estimatedHours,whyThisOrder,tasks:[{orderNum,taskType,title,required}]}] } — Ollama `POST /api/chat`(model=`qwen2.5`, `format`=JSON 스키마 structured output, `options.temperature` 낮게) 위임 + strict JSON 파싱.
- **모델·차원**: 임베딩 nomic-embed-text=**768차원** → `content_embeddings.embedding VECTOR(768)`(ERD의 1536에서 변경, 본 슬라이스 채택값). 생성 qwen2.5. 모델은 `OLLAMA_EMBED_MODEL`/`OLLAMA_GEN_MODEL`로 주입.
- **인프라**: docker-compose에 `ollama` 서비스 추가 + 사용자 1회 `ollama pull nomic-embed-text qwen2.5`(수 GB). **CI엔 Ollama 미배치** → ai-svc 테스트는 Ollama HTTP를 MockWebServer로, learning-svc 테스트는 ai-svc 클라이언트를 mock(슬라이스 #2 CI 교훈: 외부 AI는 CI에서 절대 실호출 안 함).
- ai-svc 스택: Spring Boot 4.0.7 · Java 21 · WebMVC · shared. Ollama 호출은 표준 HTTP 클라이언트(RestClient). Boot4=Jackson3(JsonMapper).

## 3. 데이터 모델 (ERD §학습경로·콘텐츠 채택, 차원만 768로)

- `learning_paths`(id PK · user_id · generated_at · track · total_weeks DEFAULT 12 · gen_prompt_version · source_embedding_version · status ACTIVE/ARCHIVED · ai_rationale TEXT). 사용자당 ACTIVE 1개(앱 레이어 보장: 신규 생성 시 기존 ACTIVE→ARCHIVED).
- `path_milestones`(id · path_id FK · week_num · title · goal_description · target_skills JSONB · estimated_hours · why_this_order TEXT).
- `path_weekly_tasks`(id · milestone_id FK · order_num · content_id FK **nullable**(매칭 실패 허용) · task_type READ/PRACTICE/QUIZ · required BOOL · completed_at). UNIQUE(milestone_id, order_num).
- `contents`(id · slug UK · title · track · content_md TEXT · estimated_minutes · difficulty · bloom_level · concept_tags JSONB · status DRAFT/PUBLISHED · created_at/updated_at).
- `content_embeddings`(id · content_id FK · chunk_index · chunk_text TEXT · **embedding VECTOR(768)** · chunk_hash · status ACTIVE/STALE). HNSW 인덱스 on embedding WHERE status='ACTIVE'; 보조 `(track,status,difficulty)`는 contents.
- `users.current_path_id BIGINT`(nullable, 교차서비스 FK 금지 — 슬라이스 #2 교훈대로 **FK 없이** 논리 참조. platform이 소유하는 users 컬럼이나 learning이 path 생성 후 갱신은 이벤트 기반 또는 미사용; **본 슬라이스는 current_path_id 미사용**, 활성 경로는 learning_paths.status=ACTIVE로 판정).
- enum은 VARCHAR+CHECK, JSON은 JSONB, PK BIGSERIAL, TIMESTAMPTZ, FK는 **learning 도메인 내부만**(learning_paths↔milestones↔tasks↔contents↔embeddings). user_id는 FK 없음(서비스 경계).
- **pgvector**: 메인 devpath DB(5432) 이미지를 `pgvector/pgvector:pg17`로 전환 + shared 마이그레이션 `CREATE EXTENSION IF NOT EXISTS vector;`(단일 DB·단일 Flyway 유지). docker-compose·CI postgres 서비스 이미지 동시 변경(pgvector는 postgres 상위호환).

## 4. 경로 생성 흐름 (learning-svc, SSE)

`POST /learning-paths/me/generate`(LEARNER, `Accept: text/event-stream`):
1. **collecting**: 자체 `assessment_results`(해당 user 최신 COMPLETED)에서 diagnosed_level·strength/weakness·track 조회. 없으면 409(진단 선행 필요).
2. **generating**: ai-svc `POST /ai/path/generate` 호출 → milestones JSON 수신·strict 파싱.
3. **matching**: 각 milestone.target_skills/주차 주제로 ai-svc `/ai/embed`(쿼리 임베딩) → pgvector HNSW로 contents 매칭(track 필터·근접도 top-k) → `path_weekly_tasks.content_id` 채움(매칭 실패 시 null, task는 텍스트 유지).
4. 영속(learning_paths ACTIVE + milestones + tasks, 기존 ACTIVE→ARCHIVED) → `LearningPathGeneratedEvent`(outbox 동일tx) → **done**: `{stage:"done", pathId, progress:1.0}`.
- **SSE 이벤트 표준(단일화, §11-3 해소)**: `data: {"stage":"collecting|generating|matching|done","progress":0.0~1.0,"message":"<사용자 카피>","pathId":<done시>}`. 단계 카피는 와이어 O04 정합. 프론트는 이 스키마로 정합(`step`→`stage`).
- **resume/fromStep**: 서버측 부분재개 미지원. 중단 시 프론트가 재생성 호출(기존 ACTIVE archive 후 신규). `fromStep` 파라미터는 본 슬라이스 미사용(프론트 정리).
- **SLO**: 경로 생성 p95<8s(Ollama 로컬 추론 시간 포함; 모델 크기로 조정). matching은 top-k 제한·배치 임베딩으로 비용 관리.

## 5. API (출처 §4 명세, 응답 스키마 확정)

| Method | Endpoint | 설명 | 권한 | SSE |
|---|---|---|---|---|
| POST | `/learning-paths/me/generate` | 경로 생성(SSE 진행) | LEARNER | ✅ |
| GET | `/learning-paths/me` | 현재 ACTIVE 경로(전체 로드맵) | LEARNER | — |
| GET | `/learning-paths/me/this-week` | 활성 경로의 이번 주(1주차) 과제 | LEARNER | — |
| POST | `/learning-paths/me/regenerate` | 재생성(기존 ACTIVE archive 후 generate와 동일, 이유 옵션) | LEARNER | 동기 200(SSE 아님, 본 슬라이스) |
| GET | `/learning-paths/{id}/rationale` | "왜 이 순서인가"(ai_rationale + milestone.why_this_order) | OWNER | — |

`GET /me` 응답(확정, O05 충족): `{ pathId, track, totalWeeks, rationale, diagnosis:{diagnosedLevel,strengthConcepts,weaknessConcepts}, milestones:[{weekNum,title,goalDescription,targetSkills,estimatedHours,whyThisOrder,locked,tasks:[{orderNum,taskType,title,required,contentId,contentSlug?}]}] }`. (locked = weekNum>1 파생, 1주차만 active.)

## 6. 이벤트·연결

- **`LearningPathGeneratedEvent`**(shared 기존: eventId·occurredAt·userId·learningPathId·targetTrack). 필요 시 diagnosedLevel 추가(하위호환 nullable). learning-svc가 `/generate` 완료 시 outbox→Kafka(`learning.path.generated`) 발행(슬라이스 #1/#2 2b 패턴).
- **DONE 전이(빌드 D)**: platform이 `LearningPathGeneratedEvent` 소비 → `users.onboarding_status`를 IN_PROGRESS→**DONE** 조건부 update(멱등, `where onboarding_status<>'DONE'`). 슬라이스 #2 `AssessmentCompletedConsumer` 패턴.
- **진단 결과 입력(§11-9 해소)**: learning-svc가 자체 DB `assessment_results` 직접 조회(option b). 이벤트/result API 불요.
- **이벤트명(§11-2)**: `learning.path.generated` 유지. LCS `learning.path.assigned`는 슬라이스 #4+ 별건으로 본 슬라이스 범위 외.

## 7. 프론트(web, 빌드 E)

- **dp_core LearningPath 모델 확장**(§11-5 해소): 현 `{rationale, weeks[{week,title,tasks[{title,done}]}]}` → `GET /me` 응답 스키마(§5)로 확장(diagnosis 강·약점·milestone goalDescription/targetSkills/estimatedHours/whyThisOrder/locked·task taskType/required/contentId). 기존 PathPlanView 등 소비처 정합 갱신.
- **PathController/SSE 목→실**: 현 SSE 목 구현(PathPhase·resume·partial)을 §4 단일 스키마(`stage`)로 정합. `apiClient.sse('/learning-paths/me/generate')`. O04 로딩 단계 카피, O05 reveal(강·약점 카드·rationale·로드맵 locked·"오늘의 학습 시작" CTA).
- **라우팅**: 진단 완료(claim/complete)→경로 생성(/path)→결과. 골든 스모크(온보딩→진단→경로 정상 + 중단→재생성). 목 픽스처 실계약 정합.

## 8. 게이트웨이(빌드 E)
- gateway에 `/learning-paths/**` → learning-svc 라우트 추가(슬라이스 #2 `/onboarding/assessments/**` 패턴). JWT 엣지 검증. SSE 경유(WebFlux 게이트웨이 text/event-stream 패스스루 확인).

## 9. 빌드 분해 (슬라이스 #1/#2 동형, A→main릴리스)

| 빌드 | 레포 | 산출 | 비고 |
|---|---|---|---|
| **A 스키마+pgvector** | devpath-shared | learning_paths·path_milestones·path_weekly_tasks·contents·content_embeddings(VECTOR768+HNSW)·`CREATE EXTENSION vector`·(이벤트 필드) + docker-compose/CI postgres→pgvector 이미지 | develop→**main 릴리스(publish)** 선행 |
| **B ai-svc Ollama** | devpath-ai-svc | Ollama 클라이언트(RestClient)·`/ai/embed`·`/ai/path/generate`·프롬프트 v1·structured JSON 파싱·MockWebServer 테스트·docker-compose ollama | redis/kafka 불요, jpa 불요(무상태 게이트웨이) |
| **C learning 경로엔진** | devpath-learning-svc | path JPA·콘텐츠 임베딩 적재·HNSW 매칭·경로생성(진단조회→ai-svc→매칭→영속)·SSE `/generate`·`/me`·`/this-week`·`/rationale`·`LearningPathGeneratedEvent` outbox·시드 콘텐츠 | 핵심·최대 빌드. ai-svc 클라이언트 mock |
| **D platform DONE** | devpath-platform-svc | `LearningPathGeneratedEvent` 소비→onboarding_status DONE(조건부 update·멱등) | 슬라이스 #2 C 패턴 |
| **E gateway+frontend** | devpath-gateway·devpath-frontend | gateway `/learning-paths/**` 라우트 / dp_core 모델 확장·PathController 실 SSE·O04/O05·라우팅 | ⚠️상류 계약 재검증 게이트 |

빌드 순서: A(+릴리스)→B→C→D→E. B·C는 A 릴리스 후. E는 C 계약 확정 후.

## 10. 테스트·CI 전략 (슬라이스 #2 교훈 승계)

- **CI에 Ollama 실호출 금지**: ai-svc는 Ollama HTTP를 MockWebServer로 계약 검증, learning-svc는 ai-svc 클라이언트를 `@MockitoBean`으로 대체.
- **pgvector**: 메인 DB 이미지 pgvector/pgvector:pg17. shared FlywayMigrationTest·서비스 JPA 테스트가 VECTOR·HNSW·`<=>` 연산을 실 PG로 검증. CI postgres 서비스 이미지도 pgvector로 변경(각 레포 ci.yml).
- **Boot4 모듈**: spring-boot-flyway·spring-boot-kafka(이벤트 발행 서비스)·테스트 슬라이스 모듈 분리, 모든 @SpringBootTest @ActiveProfiles("test"). 서비스 테스트 DB 스키마는 test 프로파일 Flyway로 shared jar 적용.
- **fresh DB + CI 일치 검증 필수**(로컬 devpath DB·인프라가 실패를 가린다 — 슬라이스 #2 교훈). guest/Redis·Kafka·pgvector·Ollama 의존을 CI 서비스/mock와 일치시킨다.
- **HNSW 매칭 IT**: 시드 콘텐츠 + 고정(결정적) 쿼리 임베딩으로 근접 매칭 결과 단언(Ollama 실호출 없이 임베딩 stub 주입).
- **SSE IT**: 스트림 단계 순서(collecting→generating→matching→done)·done payload·이벤트 outbox 발행.
- **교차서비스 FK 금지**(슬라이스 #2 교훈): learning_paths.user_id·users.current_path_id에 FK 두지 않음. learning 도메인 내부 FK만.

## 11. 미해결/플랜 확정 대상 (공백·정합성)

1. Ollama 생성 모델 최종 선정·structured output `format` 스키마 정밀(qwen2.5 가정; 모델별 JSON 준수도 차이 → 플랜에서 프롬프트·파싱 견고화·실패 폴백).
2. SSE `progress` 단계별 값·카피 문구 확정(와이어 O04 정합), regenerate가 SSE인지 동기인지(본 설계 동기 200, 플랜 확정).
3. HNSW 매칭 파라미터(top-k·거리함수 cosine `<=>`·ef_search), content_id 매칭 실패 정책(text-only task).
4. 시드 콘텐츠 규모·track 커버리지(끝단간 매칭 가능 최소량) + 시드 임베딩 생성 시점(빌드 시 Ollama vs 사전 계산 고정벡터 — CI는 고정벡터).
5. `LearningPathGeneratedEvent` 필드 확장 여부(diagnosedLevel 추가) — 하위호환 nullable.
6. dp_core 모델 확장에 따른 기존 path 테스트/PlanView 소비처 정합 범위.
7. gateway SSE(text/event-stream) WebFlux 패스스루·타임아웃·버퍼링 확인.
8. pgvector 이미지 전환에 따른 기존 슬라이스 #1/#2 마이그레이션 테스트 영향(무해 예상, 확인).
9. ERD VECTOR(1536)→(768) 변경의 문서 정합 반영(ERD 문서 갱신은 별도 docs PR).

## 12. 관련 문서·메모리
- 슬라이스 #2 설계서: `docs/superpowers/specs/2026-06-18-md1-slice2-diagnostic-design.md`
- 핸드오프·런북: `docs/superpowers/handoff-2026-06-18-md1-slice1-done.md`, `runbook-2026-06-18-md1-slice1-e2e.md`
- Ollama API: context7 `/ollama/ollama`(/api/embed·/api/chat structured output).
