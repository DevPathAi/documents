# 설계서 — MD3 슬라이스 #8 커뮤니티 Q&A (2026-06-25)

> **상태**: 신규. MD3 슬라이스 #8(커뮤니티 Q&A) = Tier-2 두 번째 슬라이스([17_스케줄](../../17_스케줄.md) §2 MD3·§3 Tier-2). 의존성상 #7 AI 멘토(완료·릴리스) 다음, **#8 커뮤니티 → #9 LCS**(스케줄 §2 의존 그래프). 풀 골든패스(멘토·커뮤니티·LCS) 중 커뮤니티.
> **위치**: MD3. 선행 = 슬라이스 #4 콘텐츠(`contents`·`content_embeddings`)·#6 AI리뷰(ai-svc 상태화·provider 추상화·Kafka 컨슈머·인젝션 방어)·#7 멘토(ai-svc `/ai/embed` 임베딩·LearningClient 패턴). 모두 완료·릴리스됨.
> **원칙**: 추측 금지(현재 상태는 실측). 모든 변경은 실패 테스트 우선. CI는 외부 LLM 실호출 금지(mock). 신규 작업은 `develop`에서 분기. 교차서비스 FK 금지.
> **선행 brainstorming 결정(2026-06-25, 사용자 승인)**: ①**범위 = Q&A 골든패스 집중**(자유/프로젝트 게시판·ES 전문검색·평판 엔진/레벨/배지·learning_context 자동첨부는 컷/후속) ②**AI 시드 = 이벤트 왕복**(community→ai-svc→community, #6 비동기 패턴 승계) ③**투표 집계만**(평판 점수/레벨/배지는 후속 WORKFLOW Step3) ④**이벤트 본문 동봉**(question.posted에 title+bodyMd, ai-svc 역조회 불필요) ⑤**빌드 B 분할**(B1 코어 CRUD / B2 이벤트·유사질문).

---

## 0. 배경

슬라이스 #6에서 ai-svc가 **상태 서비스**로 전환됐다(JPA·Kafka·Security·provider 추상화 `AiReviewClient`(Claude/Ollama/Mock)·인젝션 방어 `ReviewPromptBuilder`·멱등 `@KafkaListener` `ReviewConsumer`·`SecurityConfig`). 슬라이스 #7은 ai-svc `/ai/embed`(nomic-embed-text 768)·`LearningClient`·learning `ContentEmbeddingMatcher`(pgvector 네이티브 쿼리)를 추가했다. 슬라이스 #8은 이 자산 위에 **커뮤니티 Q&A**를 올린다.

`devpath-community-svc`는 현재 **W1 백엔드 기준선만** 존재한다(PG 드라이버 + `devpath-shared` 의존 + DB 연결 테스트 + postgres CI). 도메인 코드는 0이다. 본 슬라이스가 community-svc의 첫 도메인 구현이다.

로드맵([17_스케줄](../../17_스케줄.md) §2 MD3)이 명시한 슬라이스 #8 범위:
- community-svc: Q&A CRUD(목록/상세/작성/답변/채택) + 태그 자동완성 + ES 검색 인덱스 + **AI 시드 답변 Worker**(질문 즉시 Claude→`community_ai_answers`) + 유사 질문 탐지(pgvector 0.80)
- 프론트: 커뮤니티 실API 전환(질문 작성 FAB·답변 스레드·투표 활성)
- 자유게시판 + 프로젝트 공유 게시판(커뮤니티 확장)

**brainstorming 범위 결정(Q&A 골든패스 집중)**으로 위 중 **ES 전문검색·자유/프로젝트 게시판은 후속 슬라이스로 컷**한다(아래 §1.3). 슬라이스 #8 핵심 루프 = **질문 작성 → AI 시드 답변 자동 생성 → 인간 답변 → 채택 + 투표**.

커뮤니티는 멘토(#7)와 **전달 축이 다르다**: 멘토는 사용자가 기다리는 동기 SSE이지만, AI 시드 답변은 **질문 게시를 블로킹하지 않는 비동기**다(설계서 20_§11 Graceful Degradation: "질문만 게시, AI 답변 준비 중 표시 후 비동기"). 따라서 코드리뷰(#6)의 **이벤트 구동 + 폴링** 패턴을 따른다.

| 축 | 슬라이스 #6 코드리뷰 | 슬라이스 #7 멘토 | 슬라이스 #8 커뮤니티 Q&A |
|---|---|---|---|
| 전달 | 비동기 이벤트(Kafka)→폴링 | 동기 SSE 토큰 스트리밍 | 비동기 이벤트(Kafka)→재조회 |
| 트리거 | `sandbox.run` 자동 | 사용자 질문 입력 | 질문 작성 자동 |
| AI 위치 | ai-svc 자체 영속 | ai-svc 자체 영속 | **ai-svc 생성 → community-svc 영속(이벤트 왕복)** |
| 출력 | 구조화(ReviewResult) | 자유 텍스트 | 자유 텍스트(마크다운 답변) |

## 1. 목적과 완료 기준

### 1.1 목적
회원이 커뮤니티에서 **Q&A 질문을 작성**하면, ① 즉시 게시되고(블로킹 없음) ② **AI 시드 답변이 비동기로 자동 생성**되어 답변 스레드에 달리며 ③ 다른 회원이 **인간 답변**을 달고 ④ 질문자가 **답변을 채택**하고 ⑤ 게시글·답변에 **투표**할 수 있다. 질문 작성 시 **유사한 기존 질문**을 안내해 중복을 줄인다. dev/CI는 Anthropic 의존 없이 동작하고(Ollama/Mock), 운영은 Claude로 시드 답변 품질을 확보한다.

### 1.2 완료 기준(DoD)
- 프론트 `POST /community/questions {title, bodyMd, tags[]}` → 질문이 즉시 게시(200)되고 `community.question.posted` 이벤트가 Transactional Outbox로 발행된다.
- ai-svc가 이벤트를 멱등 소비 → AI 시드 답변(+질문 임베딩)을 생성 → `community.seed.ready` 발행 → community-svc가 멱등 소비 → `community_answers`(is_ai_generated=TRUE) + `community_ai_answers` + `community_questions.question_embedding`을 영속한다. 재전달 이벤트에도 AI 답변은 **정확히 1건**(`UNIQUE(question_id)`).
- 프론트가 `GET /community/questions/{id}`로 질문 상세(인간/AI 답변 스레드)를 받아 표시한다. AI 답변은 "🤖 AI 초안" 뱃지로 구분된다.
- 인간 답변 작성(`POST /community/questions/{id}/answers`), 답변 채택(`POST /community/answers/{id}/accept`, 질문자 OWNER), 게시글/답변 투표(`POST /community/posts/{id}/vote`·`/community/answers/{id}/vote`, upvote/downvote 카운트 집계, `UNIQUE(user_id,target_type,target_id)`)가 동작한다.
- 태그 자동완성 `GET /community/tags?q=` (prefix 매칭), Q&A 목록/필터 `GET /community/posts?board=QNA&tag=&sort=newest|unanswered`가 동작한다.
- 유사질문 안내 `GET /community/questions/similar?q={text}`: community-svc가 ai-svc `/ai/embed`로 임베딩 → pgvector 코사인 검색(**거리 < 0.20 = 유사도 ≥ 0.80**) → top-K `{questionId, title}` 반환.
- AI 시드 제공자는 `AiSeedClient` 인터페이스로 **Claude(운영)/Ollama(dev)/Mock(CI)** 교체 가능.
- 인젝션 방어: 질문 제목·본문 내 메타지시("이전 지시 무시…")가 AI 시드 답변/동작을 오염시키지 못한다(델리미터 격리 + 강건 system prompt). 무력화 골든 케이스로 회귀 검증.
- CI는 **mock provider**로 녹색(외부 LLM 실호출 없음)·EmbeddedKafka·fresh DB/CI 서비스 일치로 검증.

### 1.3 범위 외 (컷 / 후속 슬라이스)
- **자유게시판·프로젝트 공유 게시판**: `board_type` 컬럼은 두되 MVP는 QNA만 생성·노출. FREE/PROJECT 전용 필드(프로젝트 GitHub URL·스타 등)와 UI는 후속.
- **ES 전문검색**: 목록/필터/태그 자동완성은 PostgreSQL 쿼리로 충분. Elasticsearch 인덱싱은 후속(데이터 규모 도달 시).
- **평판 엔진**: 투표는 카운트 집계만. `user_reputation_events` 점수 산정·레벨 권한 게이팅(15/125/500/1000)·배지(Bronze 9종)·태그별 평판·일일 상한·sockpuppet 탐지는 후속(WORKFLOW Step3 "평판 기초").
- **learning_context 자동첨부**: `community_questions.learning_context` 컬럼은 두되 비운다. 학습 맥락 수집·sanitize·답변자 맥락 패널은 **슬라이스 #9 LCS**.
- **현상금(bounty)·북마크·팔로우·알림·신고/모더레이션·수료자 라운지**: 후속.
- **RAG 시드 품질 강화**(유사 답변을 AI 시드 프롬프트에 주입)·**AI 모더레이션 워커**(ai-mod/ai-quality, 설계서 20_§11 fan-out): 후속(MD4 모더레이션 영역).
- **전면 quota 강제·AI 비용 로깅**(MD4 FinOps). 본 설계는 kill-switch를 **시드 워커 선체크 + FAILED 표면**으로만 다룬다.

## 2. 현재 상태 (실측)

### 2.1 community-svc — W1 기준선 (실측)
- `build.gradle.kts` deps: `actuator`·`validation`·`webmvc`·`data-jpa`·`ai.devpath:devpath-shared:0.0.1-SNAPSHOT`·`runtimeOnly postgresql`·`lombok`. **`spring-kafka`·`security`·`data-redis`는 주석 처리**(템플릿 기본). → 본 슬라이스에서 `spring-kafka`·`security`(oauth2-resource-server) 활성화 필요.
- 패키지 `ai.devpath.community`, 메인 `CommunityApplication`. 소스 = `CommunityApplication.java`·`application.yml`·테스트 2종(`CommunityApplicationTests`·`DbConnectionTest`)뿐. 도메인 코드 0.
- `CLAUDE.md` 도메인표: post(5게시판)·reputation·badge·moderation — **목표 모듈**(미구현). 본 슬라이스는 **post(Q&A) + 투표 집계**만.
- Outbox 인프라 **부재**(다른 서비스는 보유) → community-svc에 신규 복제 필요.

### 2.2 shared — 이벤트/Outbox/마이그레이션 (실측)
- `DomainEvent` 인터페이스: `UUID eventId()`·`Instant occurredAt()`·`String eventType()`. 이벤트는 `ai.devpath.shared.event`에 **record**로 정의, `eventType`은 `<도메인>.<엔티티>.<동작>` 점 표기(예: `sandbox.run.submitted`·`learning.path.generated`). 하위호환: 새 필드는 nullable/기본값, 스키마 변경 시 직렬화 호환 테스트 선작성(shared CLAUDE.md).
- 최신 마이그레이션 `V202606241001__ai_mentor_sessions.sql`. Outbox 테이블 `V202606171004__outbox.sql`. `set_updated_at` 트리거·JSONB·CHECK·`(user_id, created_at DESC)` 인덱스 규약 확립.
- 커뮤니티 마이그레이션은 **`V202606251001`부터**(직전 최댓값+1, 작성 시점 재실측).

### 2.3 Outbox 패턴 (실측 — 각 서비스 복제, community-svc에 미러)
- `OutboxEntry`(@Entity `outbox`): `aggregate_type`·`aggregate_id`·`event_type`·`payload`(`@JdbcTypeCode(JSON)`)·`created_at`·`published_at`.
- `OutboxRelay.relayOnce()`: `findTop100ByPublishedAtIsNullOrderByCreatedAtAsc()` → `kafka.send(eventType, aggregateId, payload).get(5s)` → 성공 시 `publishedAt` 설정. **실패 시 break(미발행 유지, 다음 주기 재시도)** + `log.warn`. → **토픽 = eventType, 파티션 키 = aggregateId**.
- `OutboxRelayScheduler`(주기 호출)·`OutboxRepository`. 발행 측은 도메인 `@Transactional` 안에서 `OutboxEntry` 저장(payload = 직렬화된 이벤트 JSON).

### 2.4 ai-svc — 상태 서비스 (실측, 슬라이스 #6/#7 후)
- 패키지 `ai.devpath.aigw`. `review/`(AiReviewClient·Claude/Ollama/Mock·ReviewConsumer `@KafkaListener`·ReviewService·ReviewPromptBuilder·SandboxClient·ReviewKafkaConfig·ClaudeClientConfig), `mentor/`(AiMentorClient 스트리밍·LearningClient·MentorReferenceService), `ollama/`(OllamaController `/ai/embed`·`/ai/path/generate`·OllamaClient), `config/`(SecurityConfig·GlobalExceptionHandler).
- `OllamaClient.embed(text)` → `/api/embed`(nomic-embed-text, **768**). 멘토 참고자료가 사용 중.
- `SecurityConfig`: `/actuator/health` permitAll + **`/ai/**` permitAll**(내부 호출) + `anyRequest().authenticated()` + `oauth2ResourceServer.jwt`(HS256). Kafka consumer 멱등 패턴(`ReviewConsumer`: `UNIQUE` insert-if-absent).
- provider 분기: `@ConditionalOnProperty(devpath.review.provider=…)`. Claude 빈은 `ClaudeClientConfig`(anthropic-java 2.34.0).

### 2.5 learning — pgvector 패턴 (실측, 승계 대상)
- `ContentEmbeddingMatcher`(`@Repository`, `JdbcTemplate`): `embedding <=> cast(? as vector) as distance` + `order by distance, c.id desc limit ?`. `toVectorLiteral(List<Double>)`는 **768 차원 검증** + `[v1,v2,…]` 리터럴. → 커뮤니티 유사질문이 동일 패턴 승계(`community_questions.question_embedding <=> cast(? as vector)`).

### 2.6 프론트 — 커뮤니티 mock 기구현 (실측)
- `apps/web/lib/src/features/community/`: `data/community_source.dart`·`application/community_controller.dart`·`application/qna_detail_controller.dart`·`state/community_state.dart`·`state/qna_detail_state.dart`·`presentation/community_home_page.dart`·`presentation/qna_detail_page.dart`. mock 기반 → **실API 전환 대상**(멘토 #7 F 패턴 승계). 정확한 mock 계약·위젯 구조는 빌드 E에서 실측.

### 2.7 ERD/API 명세 (기정의 — 본 설계의 상위 계약)
- ERD `02_§8 커뮤니티 도메인`: `community_posts`·`community_questions`·`community_answers`·`community_votes`·`community_tags`·`community_post_tags`·`community_ai_answers`(+pgvector 임베딩 ALTER)·`user_reputation_events`·`community_reports` 등 + 인덱스 정의.
- API `04_§8 커뮤니티`: `/community/posts`(목록·상세·작성·투표)·`/community/questions`(작성·AI답변·답변·채택)·`/community/tags?q=`(자동완성) 등. 본 설계는 **§8 중 골든패스 부분집합만** MVP로 구현(권한은 LEARNER/OWNER; 평판 게이팅은 컷).

### 2.8 인프라 (실측)
- `devpath-shared/docker-compose.yml`: pgvector(5432·5433)·**Elasticsearch 8.19.4(9200)**·Kafka(9092)·Redis. 본 슬라이스는 pgvector·Kafka만 사용(ES는 컷).

## 3. 설계 결정 (D-번호)

### D-1. 비동기 이벤트구동 AI 시드 — 이벤트 왕복 (채택, 사용자 결정)
질문 작성은 즉시 게시(블로킹 없음). AI 시드는 **이벤트 왕복**으로 비동기 생성한다:
```
community-svc: POST /community/questions → 영속(즉시 200) + Outbox community.question.posted
   ↓ Kafka (토픽 community.question.posted, key=questionId)
ai-svc CommunitySeedConsumer(@KafkaListener, 멱등) → AiSeedClient 답변 + OllamaClient.embed(질문)
   → Outbox community.seed.ready (answer, provider, questionEmbedding)
   ↓ Kafka (토픽 community.seed.ready, key=questionId)
community-svc CommunitySeedConsumer(@KafkaListener, 멱등 UNIQUE(question_id))
   → community_answers(is_ai_generated=TRUE) + community_ai_answers + questions.question_embedding
```
- **ai-svc는 LLM 생성만**(LLM 일원화 원칙, #7 M-9), **community-svc가 도메인 테이블 영속**(경계 유지). community 테이블은 community-svc만 JPA 매핑.
- ai-svc도 Outbox로 `community.seed.ready` 발행(트랜잭션 아웃박스 일관). **실측: ai-svc는 produce 인프라 부재**(`ReviewConsumer`가 `@KafkaListener`로 consume만, `KafkaTemplate`·`OutboxRelay`·`OutboxEntry` 없음) → 빌드 C에서 learning/sandbox `OutboxRelay`/`OutboxEntry`/`OutboxRelayScheduler`/`OutboxRepository` **미러 신규 추가**. outbox 테이블은 shared 마이그레이션(`V202606171004`)에 이미 존재하며 ai-svc가 shared 중앙 Flyway를 적용하므로(슬라이스 #7 실측) **테이블 신규 불요, 코드만 추가**(빌드 C에서 재확인).
- 대안(ai-svc 자체 테이블 영속 + 프론트가 ai-svc 폴링)은 ERD의 `community_answers` 통합 구조(AI 답변도 답변 스레드의 일원)와 어긋나 미채택(사용자 결정).

### D-2. 이벤트 본문 동봉 (채택, 사용자 결정)
`CommunityQuestionPostedEvent`에 `title`·`bodyMd`를 동봉한다. ai-svc가 역방향 community 조회 없이 즉시 시드 답변을 생성한다(#6의 경량 이벤트+조회와 대비 — 질문 본문은 작아 Kafka/Outbox payload 부담 없음). community→ai-svc 단방향만 유지(역방향 `CommunityClient` 불필요).

### D-3. AI 시드 제공자 추상화 (채택, #6 승계)
`AiSeedClient` 인터페이스 + 구현 3종(`@ConditionalOnProperty(devpath.community-seed.provider=…)`):
- **ClaudeSeedClient**(claude): 시드 답변은 "방향 제시" 수준(설계서 20_§10 리스크2 — AI 시드가 너무 완벽하면 인간 답변 동기 소멸 → 의도적 제한). 모델 `${devpath.community-seed.claude-model:claude-haiku-…}`(설계서 §11 Haiku, 비용·속도) — 정확 모델 ID는 [claude-api] 스킬로 빌드 C에서 확정.
- **OllamaSeedClient**(ollama): `/api/chat`(범용 대화 모델, dev).
- **MockSeedClient**(mock): 고정 답변(CI·테스트 기본).
- 자유 텍스트(마크다운). `AiReviewClient`(블로킹 구조화)·`AiMentorClient`(스트리밍)와 **별개 인터페이스**(시드는 블로킹 자유텍스트).

### D-4. 질문 임베딩 = 시드 워커가 함께 생성 (채택)
ai-svc 시드 워커가 답변 생성 시 **질문 임베딩(`OllamaClient.embed`, 768)도 함께** 만들어 `community.seed.ready`에 동봉한다. community-svc가 `community_questions.question_embedding`에 저장. 임베딩과 답변은 한 왕복으로 처리(별도 동기 호출 회피). 임베딩 ~768 double(JSON 수~십 KB)은 Kafka 1MB 한도 내. **답변 생성(LLM)과 임베딩(embed)은 독립** — LLM 실패해도 임베딩은 best-effort 동봉(유사질문 검색 보존), 답변은 FAILED 표면(아래 D-6).

### D-5. 유사질문 = 별도 비블로킹 엔드포인트 (채택, 중복 방지 용도)
유사질문 안내는 질문 작성 흐름과 분리한다: `GET /community/questions/similar?q={text}`. community-svc → ai-svc `/ai/embed` → `community_questions.question_embedding` pgvector 검색(`<=> cast(? as vector)`, **거리 < 0.20 = 코사인 유사도 ≥ 0.80**, top-K) → `{questionId, title}` 반환. learning `ContentEmbeddingMatcher` 네이티브 쿼리 패턴 승계(`JdbcTemplate` + `toVectorLiteral` 768 검증). 프론트 작성 폼에서 디바운스 호출. RAG(시드 품질에 유사답변 주입)는 컷(§1.3).

### D-6. 멱등 컨슈머 + AI 답변 상태 표면 (채택, #6 D-9 승계)
- ai-svc `CommunitySeedConsumer`: `community.question.posted` 멱등 소비(ai-svc는 무상태 생성이라 중복 생성 가능하나, community 측 `UNIQUE(question_id)`가 최종 멱등 보장).
- community-svc `CommunitySeedConsumer`: `community.seed.ready` 소비 → `community_ai_answers` `UNIQUE(question_id)` insert-if-absent(재전달 no-op). AI 답변은 `community_answers`에 1건(is_ai_generated=TRUE) + `community_ai_answers` 메타.
- AI 시드 실패(LLM_FAILED/KILL_SWITCH): seed.ready에 `status=FAILED`+`error_code` 동봉 → community가 `community_ai_answers` FAILED로 기록(답변 본문 없음). 프론트는 "AI 답변 생성 실패/없음" 표시. kill-switch는 ai-svc 시드 워커가 선체크.

### D-7. 데이터 모델 = shared 중앙 Flyway, 도메인 내 FK 허용·교차서비스 FK 금지 (채택)
커뮤니티 테이블은 shared 중앙 마이그레이션(다른 서비스 일관). **커뮤니티 도메인 내부 FK는 허용**(`community_questions.post_id → community_posts.id` 등 — 같은 서비스·같은 DB). **교차서비스 참조(`author_id`→platform users, `content_id`→learning)는 논리 참조(FK 없음)**(#6/#7 규약). `user_reputation_events` 등 평판 테이블은 본 슬라이스 미생성(후속).

### D-8. community-svc 보안/인가 (채택, learning-svc 미러)
`security`(oauth2-resource-server) 활성화. `SecurityConfig`: `/actuator/health` permitAll + `anyRequest().authenticated()` + `oauth2ResourceServer.jwt`(HS256, gateway 엣지 + 동일 시크릿). `userId = jwt.getSubject()`. 채택·삭제는 OWNER(작성자) 검사. 평판 기반 권한 게이팅(upvote 15+/downvote 125+)은 **MVP 무제한**(설계서 20_§3.2 "MVP 무제한", 평판 엔진 컷).

## 4. 데이터 모델 — `V202606251001__community_qna.sql` (shared)

> ERD `02_§8` 부분집합. 모든 테이블 `set_updated_at` 트리거(기존 공통 함수 재사용)·`created_at/updated_at TIMESTAMPTZ`. 교차서비스 FK 없음(author_id·content_id 논리참조).

**`community_posts`** — 게시글(MVP=QNA만 생성)
| 컬럼 | 타입 | 비고 |
|---|---|---|
| `id` | BIGSERIAL PK | |
| `author_id` | BIGINT NOT NULL | 논리참조(platform) |
| `board_type` | VARCHAR NOT NULL | CHECK ∈ {QNA,FREE,PROJECT,STUDY,ALUMNI}; MVP는 QNA |
| `title` | VARCHAR(120) NOT NULL | 제목(설계서 80자 제한은 app validation) |
| `body_md` | TEXT NOT NULL | 마크다운 본문 |
| `body_html` | TEXT NULL | 렌더링(MVP 선택; 미사용 시 null) |
| `status` | VARCHAR NOT NULL DEFAULT 'PUBLISHED' | CHECK ∈ {DRAFT,PUBLISHED,HIDDEN,DELETED} |
| `view_count`·`upvote_count`·`downvote_count` | INT NOT NULL DEFAULT 0 | |
| `created_at`,`updated_at` | TIMESTAMPTZ NOT NULL | |

**`community_questions`** — Q&A 확장(post 1:1)
| 컬럼 | 타입 | 비고 |
|---|---|---|
| `post_id` | BIGINT PK | FK→`community_posts(id)`(도메인 내) |
| `is_solved` | BOOLEAN NOT NULL DEFAULT false | |
| `accepted_answer_id` | BIGINT NULL | FK→`community_answers(id)`(채택) |
| `question_embedding` | vector(768) NULL | 유사질문(시드 워커가 채움) |
| `learning_context` | JSONB NOT NULL DEFAULT '{}' | #9 LCS용(MVP 비움) |

**`community_answers`** — 답변(인간/AI)
| 컬럼 | 타입 | 비고 |
|---|---|---|
| `id` | BIGSERIAL PK | |
| `question_id` | BIGINT NOT NULL | FK→`community_questions(post_id)` |
| `author_id` | BIGINT NULL | 인간=작성자; AI=NULL |
| `body_md` | TEXT NOT NULL | |
| `body_html` | TEXT NULL | |
| `is_ai_generated` | BOOLEAN NOT NULL DEFAULT false | AI 시드 |
| `is_accepted` | BOOLEAN NOT NULL DEFAULT false | |
| `upvote_count` | INT NOT NULL DEFAULT 0 | |
| `created_at`,`updated_at` | TIMESTAMPTZ NOT NULL | |

**`community_votes`** — 투표
| 컬럼 | 타입 | 비고 |
|---|---|---|
| `id` | BIGSERIAL PK | |
| `user_id` | BIGINT NOT NULL | 논리참조 |
| `target_type` | VARCHAR NOT NULL | CHECK ∈ {POST,ANSWER} |
| `target_id` | BIGINT NOT NULL | |
| `value` | SMALLINT NOT NULL | CHECK ∈ {-1,1} |
| `created_at` | TIMESTAMPTZ NOT NULL | |
| | | **UNIQUE(user_id,target_type,target_id)** |

**`community_tags`**(`id`·`name` VARCHAR UNIQUE·`post_count` INT DEFAULT 0·`created_at`) / **`community_post_tags`**(`post_id`·`tag_id`, **PK(post_id,tag_id)**, 각 FK 도메인 내)

**`community_ai_answers`** — AI 시드 메타(question 1:1, 멱등)
| 컬럼 | 타입 | 비고 |
|---|---|---|
| `question_id` | BIGINT PK | FK→`community_questions(post_id)`; **UNIQUE(멱등)** |
| `answer_id` | BIGINT NULL | FK→`community_answers(id)`(생성된 AI 답변) |
| `model_used` | VARCHAR NULL | 관측용 |
| `prompt_version` | VARCHAR NULL | |
| `content` | TEXT NULL | 원본 AI 답변(FAILED 시 null) |
| `reference_links` | JSONB NOT NULL DEFAULT '[]' | MVP 빈 배열(역링크 추천은 후속 §1.3); ERD 정합 위해 컬럼만 유지. `references`는 SQL 예약어 회피(#7 규약) |
| `status` | VARCHAR NOT NULL | CHECK ∈ {DONE,FAILED} |
| `error_code` | VARCHAR NULL | FAILED 시(LLM_FAILED/KILL_SWITCH/TIMEOUT) |
| `generated_at` | TIMESTAMPTZ NOT NULL | |

**인덱스**: `community_posts(board_type,status,created_at DESC)`·`(author_id,created_at DESC)`; `community_questions(is_solved)`(미답변 큐); `community_votes(target_type,target_id)` + UNIQUE; `community_tags(name)` UNIQUE + prefix(`text_pattern_ops`) 자동완성; `community_answers(question_id)`. `question_embedding` HNSW/IVFFlat 인덱스는 **후속**(MVP 데이터 소량, 시퀀셜 스캔 허용 — `log` 명시).

**이벤트(shared `event/`)** — record, `DomainEvent` 구현:
- `CommunityQuestionPostedEvent(UUID eventId, Instant occurredAt, long userId, long questionId, long postId, String title, String bodyMd)`, `EVENT_TYPE="community.question.posted"`.
- `CommunitySeedReadyEvent(UUID eventId, Instant occurredAt, long questionId, String status, String content, String provider, List<Double> questionEmbedding, String errorCode)`, `EVENT_TYPE="community.seed.ready"`. (역링크 references는 MVP 미포함 §1.3. 정확 필드는 빌드 A에서 직렬화 호환 테스트와 함께 확정; nullable 규약 준수.)

## 5. 컴포넌트 / 변경 대상 (레포별)

- **shared**: `V202606251001__community_qna.sql` + 이벤트 2종 + `FlywayMigrationTest` 단언(CHECK·UNIQUE·vector·트리거·인덱스) + 이벤트 직렬화 호환 테스트. **develop→main 릴리스(publish) 선행**(서비스가 jar 의존).
- **community-svc** *(핵심 신규 — 도메인 전체)*:
  - **B1 코어**: deps 활성화(`spring-kafka`·`security`/oauth2-resource-server) + `post/`(엔티티 `CommunityPost`·`CommunityQuestion`·`CommunityAnswer`·`CommunityVote`·`CommunityTag`·`CommunityPostTag` + 리포지토리 + `QuestionService`·`AnswerService`·`VoteService`·`TagService` + `CommunityController`(질문 작성·목록·상세·답변·채택·투표·태그 자동완성)) + `SecurityConfig`(D-8) + `GlobalExceptionHandler`.
  - **B2 이벤트/유사질문**: `outbox/`(OutboxEntry·Relay·Scheduler·Repository 미러) + 질문 작성 tx에서 `community.question.posted` Outbox 발행 + `CommunitySeedConsumer`(`@KafkaListener community.seed.ready`, 멱등 `UNIQUE(question_id)`, AI 답변/메타/임베딩 영속) + `EmbeddingClient`(ai-svc `/ai/embed`) + `SimilarQuestionMatcher`(pgvector, learning 패턴) + `GET /community/questions/similar` + Kafka config.
- **ai-svc** *(핵심·직접작업 — 인젝션/콘텐츠필터 위험)*:
  - `community/` 패키지: `CommunitySeedConsumer`(`@KafkaListener community.question.posted`, 멱등) + `AiSeedClient`(인터페이스)+`ClaudeSeedClient`/`OllamaSeedClient`/`MockSeedClient` + `SeedPromptBuilder`(인젝션 격리 `<user_question>` + 강건 system prompt) + 질문 임베딩(`OllamaClient.embed` 재사용) + kill-switch 선체크.
  - `outbox/` 패키지 **신규**(실측: ai-svc는 produce 인프라 부재 — consume만): `OutboxRelay`·`OutboxEntry`·`OutboxRelayScheduler`·`OutboxRepository` 미러(learning/sandbox 패턴) + `KafkaTemplate` 빈/config. `community.seed.ready`를 시드 처리 tx 안에서 OutboxEntry 저장 → relay. outbox 테이블은 shared 마이그레이션 기존(코드만 추가).
  - `build.gradle` 변경 최소(JPA·Kafka·Security 이미 활성). 시드 골든 eval(`@Tag eval`, CI 제외, `golden-community-seed-injection.jsonl`).
  - `SecurityConfig` 변경 불요(`/ai/**` 외 신규 HTTP 엔드포인트 없음 — 시드는 Kafka 소비).
- **gateway**: `application.yml` `- Path=/community/**` → community-svc(`COMMUNITY_SVC_URI`) 라우트 + `anyExchange().authenticated()` JWT 엣지 + `CommunityRouteTest`(ReviewRouteTest/MentorRouteTest 미러).
- **frontend**: `features/community/` mock → 실API(`community_source` wire 교체 + 질문 작성 FAB·답변 스레드·채택·투표·AI 초안 뱃지·유사질문 안내). 위젯/컨트롤러 테스트 갱신. `melos run analyze/test/format` 녹색(format CI 게이트).
- **documents**: community-svc `CLAUDE.md` 도메인표 갱신(post=Q&A MVP 구현 명기), 진행 기록.

## 6. 데이터 흐름 (끝단간)

1. 프론트 → gateway → community-svc `POST /community/questions {title, bodyMd, tags[]}`(JWT). `community_posts`+`community_questions`+태그 영속(즉시 200) + 같은 tx에서 `community.question.posted` Outbox 저장.
2. community OutboxRelay → Kafka `community.question.posted`(key=questionId).
3. ai-svc `CommunitySeedConsumer` 소비(멱등) → `SeedPromptBuilder`(인젝션 격리) → `AiSeedClient`(Claude/Ollama/Mock) 답변 + `OllamaClient.embed(title+bodyMd)` 임베딩 → `community.seed.ready` Outbox 발행(DONE; LLM 실패 시 FAILED+error_code, 임베딩 best-effort).
4. ai-svc OutboxRelay → Kafka `community.seed.ready`(key=questionId).
5. community-svc `CommunitySeedConsumer` 소비(멱등 `UNIQUE(question_id)`) → `community_answers`(is_ai_generated=TRUE, FAILED면 생략) + `community_ai_answers`(메타/status) + `community_questions.question_embedding` UPDATE.
6. 프론트 `GET /community/questions/{id}` 재조회 → 질문 + 답변 스레드(인간/AI 뱃지) 표시.
7. 인간 답변 `POST /community/questions/{id}/answers` → 스레드 추가. 채택 `POST /community/answers/{id}/accept`(질문자 OWNER) → `is_accepted`+`questions.is_solved`+`accepted_answer_id`. 투표 `POST /community/posts|answers/{id}/vote {value}` → `community_votes` UPSERT + 카운트 집계.
8. (작성 폼) `GET /community/questions/similar?q=` → ai-svc embed → pgvector 검색 → 유사질문 안내.

## 7. 에러 처리

| 상황 | 처리 |
|---|---|
| AI 시드 LLM 실패/타임아웃 | seed.ready `status=FAILED`+`error_code`(LLM_FAILED/TIMEOUT) → community `community_ai_answers` FAILED(답변 미생성). 프론트 "AI 답변 없음" |
| kill-switch(AI 비활성) | ai-svc 시드 워커 선체크 → seed.ready FAILED(`KILL_SWITCH`). 질문 게시 자체는 영향 없음 |
| 인젝션 시도(제목/본문) | 델리미터 격리 + 강건 system prompt 무력화(D-3). 골든 회귀 |
| 재전달 이벤트 | community `UNIQUE(question_id)` insert-if-absent no-op(D-6) |
| 임베딩/유사검색 실패 | 유사질문 빈 배열 반환(작성 흐름 무영향). 시드 임베딩 실패 시 question_embedding null(유사검색서 제외) |
| 비소유자 채택/삭제 | 403(OWNER=post.author_id==jwt.subject) |
| 중복 투표 | `UNIQUE(user_id,target_type,target_id)` — 같은 타깃 재투표는 UPSERT(값 변경/취소), 카운트 정합 |
| ai-svc/embed 다운(유사질문) | 유사질문 503 graceful(빈 결과) — 질문 작성·조회는 정상 |

## 8. 테스트 설계 (#6/#7 승계)

- **shared**: `FlywayMigrationTest`(테이블·CHECK·UNIQUE·vector 컬럼·인덱스·트리거 단언), 이벤트 2종 직렬화 호환 테스트.
- **community-svc 단위**: `QuestionService`·`AnswerService`(채택 OWNER·is_solved 전이)·`VoteService`(UPSERT·카운트·UNIQUE)·`TagService`(prefix 자동완성)·`SimilarQuestionMatcher`(pgvector mock/실DB·0.80 임계·768 검증)·`CommunitySeedConsumer`(멱등 1건·FAILED 기록).
- **community-svc IT**: EmbeddedKafka — `community.seed.ready` 소비 → 답변/메타/임베딩 영속(멱등 중복 1건). MockMvc(질문 작성→Outbox 적재, 목록/필터, 상세, 답변, 채택 403/200, 투표). fresh DB(`devpath_citest`). `@ActiveProfiles("test")`.
- **ai-svc 단위/IT**: `AiSeedClient`(MockWebServer Claude/Ollama·malformed→실패), `SeedPromptBuilder`(델리미터·system prompt 단언), `CommunitySeedConsumer`(question.posted→seed.ready 발행, Mock provider·embed mock), kill-switch FAILED. **인젝션 무력화 골든 eval**(`@Tag eval`, CI 제외).
- **CI**: 외부 LLM 0(Mock provider 고정)·postgres(pgvector)·EmbeddedKafka. 모든 `@SpringBootTest` `@ActiveProfiles("test")`.
- **gateway**: `/community/**` 라우트 + JWT 엣지 RouteTest.
- **frontend**: 컨트롤러(질문 작성·목록·상세·답변·채택·투표·유사질문·AI 뱃지 분기), 위젯, mock fixture→실API. `melos run analyze/test/format` 녹색.

## 9. 빌드 분해 (권장 순서 A→B1→B2→C→D→E)

- **A · shared**: `community_qna` 마이그레이션 + 이벤트 2종 + FlywayMigrationTest + 직렬화 호환 테스트. **develop→main 릴리스(publish) 선행**.
- **B1 · community-svc 코어**: deps 활성화 + post/ 도메인(엔티티·리포·서비스·컨트롤러: 질문 CRUD·답변·채택·투표·태그 자동완성·목록/필터) + SecurityConfig + GlobalExceptionHandler + 단위/IT(MockMvc). (서브에이전트 위임 가능 — 인젝션 표현 없음)
- **B2 · community-svc 이벤트/유사질문**: outbox 미러 + question.posted 발행 + `CommunitySeedConsumer`(seed.ready 멱등 영속) + EmbeddingClient + SimilarQuestionMatcher + similar 엔드포인트 + EmbeddedKafka IT.
- **C · ai-svc 시드 워커** *(직접 작업 — 인젝션/탈옥 표현 콘텐츠필터 위험, #5 B2·#6 C 교훈)*: community/ 패키지(CommunitySeedConsumer·AiSeedClient 3종·SeedPromptBuilder 인젝션·질문 임베딩·seed.ready 발행·kill-switch 선체크) + 골든 eval.
- **D · gateway**: `/community/**` 라우트 + JWT 엣지 + RouteTest.
- **E · frontend**: community mock→실API(질문 작성 FAB·답변 스레드·채택·투표·AI 뱃지·유사질문) + 테스트 + documents 갱신.

각 빌드 = 백엔드 API/변경 + (E는) 프론트 실API 전환 + 통합테스트. 각 레포 fresh DB/CI 녹색 develop 머지, A는 main 릴리스 선행. 슬라이스 #1~#7 교훈 승계(로컬 인프라가 CI 가림→fresh DB·CI 서비스 일치, 교차서비스 FK 금지, Boot4 모듈 분리, CI LLM mock, 서브에이전트 Scope Lock, ai-svc 로컬빌드는 `gradle.properties` GitHub Packages 토큰으로 가능). 슬라이스 끝 **통합 릴리스**(shared·community·ai-svc·gateway·frontend develop→main + image/deploy).

### 9.1 컷라인 (여유 부족 시)
일정 압박 시 **Q&A 코어 루프(질문→AI시드→인간답변→채택)** 를 사수하고 아래를 후행 분리(의식적 컷, `log`/핸드오프 명시):
- **유사질문(B2 일부)**: similar 엔드포인트·SimilarQuestionMatcher·임베딩 동봉을 2차로. 시드 답변은 임베딩 없이 성립.
- **Ollama 시드**: dev 편의용. 1차는 Claude(운영)+Mock(CI)만, Ollama 후행.
- **투표**: 채택은 사수, upvote/downvote는 후행 가능(프론트 "투표 활성" 일부 지연).
> 단, **현재 사용자 결정은 §1.2 전부 포함**. 컷라인은 비상 옵션.

## 10. 리스크와 대응

| 리스크 | 대응 |
|---|---|
| ai-svc Outbox produce 인프라 부재(seed.ready) | **실측 확정**: ai-svc는 `@KafkaListener` consume만(produce·Outbox 없음). 빌드 C에서 `OutboxRelay`/`OutboxEntry`/`Scheduler`/`Repository` + KafkaTemplate 미러 신규(outbox 테이블은 shared 기존). 트랜잭션 아웃박스로 발행 보장 |
| 이벤트 왕복 2-hop 지연 | 비동기 수용(질문 게시 블로킹 없음, "AI 답변 준비 중"). 프론트 재조회/폴링 |
| AI 시드가 너무 완벽 → 인간 답변 동기 소멸 | 시드 "방향 제시" 수준 제한 + "🤖 AI 초안" 뱃지(설계서 20_§10 리스크2). 측정·임계는 MD4 |
| 임베딩 이벤트 동봉 무게 | 768 double JSON 수~십 KB ≪ Kafka 1MB. 문제 시 별도 임베딩 이벤트 분리(후속) |
| 인젝션 우회(자유 텍스트, 구조화 출력 없음) | 델리미터+강건 system prompt 1차 방어 + 골든 회귀. 2차 분류기/출력 모더레이션 MD4 |
| community-svc 첫 도메인(대형) | B1/B2 분할 + TDD + 컨트롤러 직접 검증(커밋/구조/테스트). Scope Lock 위임 |
| pgvector 유사질문 정확도 | 거리<0.20(유사도 0.80) 임계 + 768 검증. 데이터 소량 시 시퀀셜 스캔(인덱스 후속) |
| 교차서비스 author_id 정합 | 논리참조(FK 없음), JWT subject로 소유 검사. 사용자 표시명은 후속(platform 조회 or 비정규화) |
| 프론트 mock 계약 불일치 | 빌드 E에서 mock 실측 후 전환(#7 F 패턴: 실제 라우트·아이콘 실측) |

## 11. 참고
- 로드맵: [17_스케줄](../../17_스케줄.md) §2(MD3 슬라이스 #8)·§3(Tier-2). 커뮤니티 전체 설계: [20_커뮤니티_기능_설계서](../../20_커뮤니티_기능_설계서.md)(v1 비전 — 본 슬라이스는 Q&A 골든패스 부분집합). ERD: [02_ERD_문서](../../02_ERD_문서.md) §8. API: [04_API_명세서](../../04_API_명세서.md) §8. 테스트 전략 §16(골든): [11_테스트_전략서](../../11_테스트_전략서.md).
- 패턴 승계: [2026-06-23-md2-slice6-ai-code-review-design](./2026-06-23-md2-slice6-ai-code-review-design.md)(이벤트구동·provider·인젝션·멱등), [2026-06-24-md3-slice7-ai-mentor-design](./2026-06-24-md3-slice7-ai-mentor-design.md)(embed·LearningClient·pgvector).
- 실측: community-svc `build.gradle.kts`·`CommunityApplication`; shared `event/DomainEvent`·`SandboxRunSubmittedEvent`·`V202606171004__outbox`·`V202606241001`; learning `outbox/OutboxRelay`·`outbox/OutboxEntry`·`path/ContentEmbeddingMatcher`; ai-svc `review/`·`mentor/`·`ollama/OllamaClient`·`config/SecurityConfig`; 프론트 `features/community/`; `docker-compose.yml`(pgvector·ES·Kafka).
- 핸드오프: [handoff-2026-06-23-tier1-closed-tier2-next](../handoff-2026-06-23-tier1-closed-tier2-next.md). 멘토 진행: 메모리 `md3-slice7-mentor-progress`.
- study-documents(community-svc CLAUDE.md): `/devpath-skillpack:spring-setup`·`:domain-modeler`·`:code-reviewer`·`:test-coverage-booster`·`:postgres-mcp-tuner`·`:error-detective`. Sample Codes: Spring Boot 4 JPA·WebClient·Audit.
