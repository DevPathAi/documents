# 빌드 보고 — MD3 슬라이스 #8 B2 (community-svc 이벤트 왕복 + 유사질문)

> 일자: 2026-06-26 · 레포: devpath-community-svc · 작업: 빌드 B2(이벤트 왕복 + 유사질문) 플랜~구현~develop 머지

## ① B1 교차검증 결과 (PASS)

- `git checkout develop && git pull`: develop이 B1(PR #9, merge `e5f01aa`)까지 fast-forward 반영 확인.
- B1 도메인 존재: `src/main/java/ai/devpath/community/post/`에 엔티티 6종(CommunityPost·Question·Answer·Vote·Tag·PostTag)·서비스 4종(Question·Answer·Vote·Tag)·CommunityController·dto 7종·예외 3종 + `config/`(SecurityConfig·GlobalExceptionHandler) 실측.
- B2 코드 부재 확인: `grep -rEli "kafkalistener|outboxrelay|seedconsumer|embedding" src/main` → **NONE**(B2가 추가할 영역 비어 있음).
- 베이스라인 테스트: `DB_URL=...devpath_citest ./gradlew test` → **BUILD SUCCESSFUL**(B1 12 테스트 녹색).
- shared 마이그레이션 적용 확인: `devpath_citest`에 `community_*` 7테이블 + `flyway_schema_history` `202606251001 community qna success=t`. `community_ai_answers`(PK=question_id) 존재.
- B1 정상 → 진행. `feat/slice8-community-events`를 develop에서 분기.

## ② 작성한 플랜 경로

`documents/docs/superpowers/plans/2026-06-25-md3-slice8-community-events-b2.md`
(B1 플랜과 동일 형식. 태스크 B2-1~B2-5 + PR/머지 + Self-Review. 각 태스크 TDD RED→GREEN→커밋·실제 코드·검증 명령.)

## ③ 태스크별 커밋 SHA · 테스트 결과

| 태스크 | 커밋 | 내용 | 테스트 |
|---|---|---|---|
| B2-1 | `cbeec81` | spring-kafka·spring-boot-kafka 활성 + Kafka producer/consumer 설정 + ai-svc base-url + KafkaConfig(poison-skip ErrorHandler) | CommunityContextTest PASS(kafka 빈 포함 기동) |
| B2-2 | `ad9054a` | outbox/ 4종 미러(learning 복제) + CommunityApplication @EnableScheduling + QuestionService.create()가 같은 tx에서 community.question.posted Outbox 적재 | OutboxRelayTest(1)·QuestionOutboxTest(1)·QnaMockMvcTest(4, B1 회귀) PASS |
| B2-3 | `00bec2d` | CommunityAiAnswer 엔티티+Repository + CommunitySeedService(멱등 영속) + CommunitySeedConsumer(@KafkaListener seed.ready) | CommunitySeedConsumerIT **3/0/0/0**(DONE 영속·멱등 중복 1건·FAILED 경로) |
| B2-4 | `170a22a` | EmbeddingClient(ai-svc /ai/embed) + SimilarQuestionMatcher(pgvector<0.20) + EmbeddingUnavailableException + SimilarQuestionView + GET /community/questions/similar(graceful) | SimilarQuestionMatcherTest(2)·SimilarQuestionApiTest(3) PASS |
| B2-5 | (검증) | 전체 스위트 + 빌드 | `./gradlew build` **BUILD SUCCESSFUL**, 전체 **21 테스트 / 0 실패 / 0 에러 / 0 skip** |

머지 커밋: `f60bce4`(develop).

## ④ 생성/수정 파일 (24개, 전부 community-svc)

**신규 main**:
- `outbox/OutboxEntry.java`·`OutboxRepository.java`·`OutboxRelay.java`·`OutboxRelayScheduler.java`(learning 복제, 패키지만 변경)
- `config/KafkaConfig.java`(DefaultErrorHandler 지수백오프 3회 + poison skip 로깅)
- `seed/CommunityAiAnswer.java`·`CommunityAiAnswerRepository.java`·`CommunitySeedService.java`·`CommunitySeedConsumer.java`·`EmbeddingClient.java`·`EmbeddingUnavailableException.java`·`SimilarQuestionMatcher.java`·`dto/SimilarQuestionView.java`

**수정 main**:
- `CommunityApplication.java`(@EnableScheduling)
- `post/QuestionService.java`(OutboxRepository·JsonMapper 주입 + publishQuestionPosted)
- `post/CommunityController.java`(EmbeddingClient·SimilarQuestionMatcher 주입 + similar 엔드포인트)
- `build.gradle.kts`(kafka 활성 + spring-kafka-test·awaitility)
- `src/main/resources/application.yml`(kafka producer/consumer + devpath.ai-svc)
- `src/test/resources/application-test.yml`(kafka consumer group + ai-svc 닿지않는 base-url)

**신규 test**:
- `outbox/OutboxRelayTest.java`(EmbeddedKafka)
- `post/QuestionOutboxTest.java`
- `seed/CommunitySeedConsumerIT.java`(EmbeddedKafka, 3 시나리오)
- `seed/SimilarQuestionMatcherTest.java`·`seed/SimilarQuestionApiTest.java`

## ⑤ PR 번호 · CI 상태 · 머지 SHA

- PR: **#10** (`DevPathAi/devpath-community-svc`, base=develop, head=feat/slice8-community-events)
- CI: `build` **pass**(1m23s, pgvector/pgvector:pg17 postgres). `image`/`deploy` skipping(develop 대상, main 전용 잡).
- 머지: **MERGED** (merge `--merge --delete-branch`), 머지 SHA `f60bce4`, mergedAt 2026-06-26T04:06:13Z. 브랜치 삭제됨.

## ⑥ 막힌 점 / 특이사항

1. **`@Repository` 예외 변환(B2-4에서 1회 RED 후 수정)**: `SimilarQuestionMatcher`에 `@Repository`를 달면 Spring `PersistenceExceptionTranslationInterceptor`가 `toVectorLiteral`의 768 검증 `IllegalArgumentException`을 `InvalidDataAccessApiUsageException`으로 래핑. 근본 원인 규명(스택트레이스: HibernateExceptionTranslator) 후, 테스트를 "래핑 예외의 cause가 IllegalArgumentException(가드 발동)"으로 단언하도록 정정. learning `ContentEmbeddingMatcher`도 동일 구조지만 그쪽 테스트는 768 위반 케이스를 단언하지 않아 드러나지 않았던 동작. **땜질 아님** — 실제 런타임 동작을 정확히 단언.
2. **코사인거리 테스트 벡터(플랜 단계에서 선반영)**: 상수 양수 벡터끼리는 방향이 같아 코사인거리≈0 → far도 near로 잡힘. far를 교대 부호(alternating, 직교에 근접) 벡터로 설정해 거리≈1.0(>0.20)로 제외되게 구성. 플랜 Self-Review ⑧에 명시하고 구현에 반영.
3. **EmbeddedKafka Windows temp 정리 경고(무해)**: 테스트 종료 후 `FileSystemException ... .index 다른 프로세스가 사용 중` ERROR 로그가 찍히나, 이는 EmbeddedKafka 브로커 셧다운의 Windows 파일락 정리 실패일 뿐 테스트 결과(tests=3 failures=0)에 영향 없음. CI(Linux)에서는 발생하지 않음. 빌드 SUCCESSFUL·CI pass로 확인.
4. **questionId == postId**: B1 실측상 `CommunityQuestion.postId = post.id`(question PK=post id). 이벤트 `CommunityQuestionPostedEvent`는 questionId·postId 둘 다 동봉(설계 §4) → 둘 다 `p.getId()`로 설정.
5. **JsonMapper = `tools.jackson.databind.json.JsonMapper`**(Jackson 3, Boot 4 자동구성 빈). ai-svc와 동일. `com.fasterxml` 아님. `writeValueAsString`은 unchecked(try/catch 불요).
6. **ai-svc embed 계약**: ai-svc `/ai/embed`는 `{texts:List<String>}` → `{embeddings:List<List<Double>>}`(실측 EmbedRequest/EmbedResponse). EmbeddingClient는 단일 text를 `texts:[text]`로 보내고 `embeddings[0]`(768)을 사용.

### Scope Lock 준수
- 변경 파일 전부 `devpath-community-svc/`. ai-svc·gateway·frontend·shared **미수정**(`git diff --name-only origin/develop..` 확인). ai-svc `/ai/embed`는 호출만, 실제 호출은 테스트에서 `@MockitoBean`으로 mock.
- 빌드 C(ai-svc 시드 워커)·D(gateway)·E(frontend)는 미착수(B2 범위 외).
