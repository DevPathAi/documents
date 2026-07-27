# B2 독립 검증 — MD3 슬라이스 #8 (community-svc 이벤트 왕복 + 유사질문)

> 검증일: 2026-06-26 · 검증자: 독립 서브에이전트(읽기·git/gh 조회·테스트 실행만, 코드 수정/커밋/머지 없음) · 대상 레포: devpath-community-svc

## 판정 요약

| 항목 | 판정 | 근거 |
|---|---|---|
| B2 develop 머지 | **OK** | PR #10 MERGED, merge SHA `f60bce4` (보고서와 일치) |
| B2 범위(outbox·seed consumer·embedding·similar, kafka 의존) | **OK** | develop src/main에 전부 실재, build.gradle.kts spring-kafka 추가 |
| ai-svc 미침범 | **OK** | ai-svc develop에 community/·seed 코드 전무 |
| develop CI | **녹색** | PR #10 head(170a22a) build=success, image/deploy=skipped(정상) |
| 테스트 직접 재실행 | **통과 21 / 실패 0** | gradlew test --rerun-tasks BUILD SUCCESSFUL, JUnit XML 합산 21/0/0/0 |

**최종: PASS.** 보고서의 모든 주장이 독립 검증으로 확인됨. 범위 이탈·ai-svc 침범·테스트 허위 없음.

## 1. B2 develop 머지 확인

- `git log origin/develop --oneline`: B2 커밋 4종 + 머지 커밋 develop에 존재.
  - `f60bce4` Merge pull request #10 (머지 커밋)
  - `170a22a` B2-4 EmbeddingClient + SimilarQuestionMatcher + similar 엔드포인트
  - `00bec2d` B2-3 CommunitySeedConsumer 멱등 영속
  - `ad9054a` B2-2 outbox 미러 + question.posted 발행
  - `cbeec81` B2-1 spring-kafka 활성 + Kafka 설정 + ai-svc base-url
- 4개 커밋 SHA 전부 보고서 ③표와 일치.
- `gh pr view 10`: state=MERGED, mergeCommit.oid=`f60bce4bfc9f34b57ddad73775e45d5c115c9324`, baseRefName=develop, headRefName=feat/slice8-community-events, mergedAt=2026-06-26T04:06:13Z. 보고서 ⑤와 일치.

## 2. 범위 확인 (develop src/main 실측)

`git ls-tree -r origin/develop -- src/main` + `git grep origin/develop`:

- **outbox/**: OutboxEntry.java·OutboxRepository.java·OutboxRelay.java·OutboxRelayScheduler.java — 4종 전부 존재.
- **CommunitySeedConsumer**: `seed/CommunitySeedConsumer.java:23` `@KafkaListener(topics = CommunitySeedReadyEvent.EVENT_TYPE, groupId = "devpath-community")` 실재.
- **EmbeddingClient**: `seed/EmbeddingClient.java` — RestClient로 `/ai/embed` POST, `{texts}`→`{embeddings}`, 768차원 검증, 실패 시 EmbeddingUnavailableException(graceful). 보고서 ⑥-6 계약과 일치.
- **SimilarQuestionMatcher**: `seed/SimilarQuestionMatcher.java` — pgvector 코사인거리 `<=>` 네이티브쿼리, MAX_DISTANCE=0.20, toVectorLiteral 768가드.
- **GET /community/questions/similar**: `post/CommunityController.java:60` `@GetMapping("/questions/similar")` 실재.
- **build.gradle.kts**: `spring-kafka`·`spring-boot-kafka`(main) + `spring-kafka-test`·`awaitility`(test) 추가 확인.
- **QuestionService**: `publishQuestionPosted`가 `community.question.posted` Outbox 적재(같은 tx). shared `CommunityQuestionPostedEvent` import.

범위 diff: `git diff --name-only e5f01aa..170a22a` = **24개 파일, 전부 devpath-community-svc/ 내부**. 보고서 ④의 24개 목록과 정확히 일치(신규 main 12 + 수정 main 6 + 신규/수정 test 6).

DB 스키마(devpath_citest, 도커 pgvector/pgvector:pg17):
- community_* 7테이블 존재(ai_answers·answers·post_tags·posts·questions·tags·votes).
- community_questions.question_embedding = USER-DEFINED(pgvector vector 타입).
- flyway_schema_history: `202606251001 community qna success=t`.

## 3. ai-svc 미침범 확인

- `git -C devpath-ai-svc status -sb`: 로컬 develop, 워킹트리에 CLAUDE.md 수정 + .omc/ 만(B2 무관, 기존 상태).
- `git ls-tree -r origin/ai-svc develop -- src/main | grep -iE "community|seed"` → 매치 없음(exit 1).
- `git grep origin/develop "communityseed|community.seed.ready|community.question.posted" -- src/main` → 매치 없음.
- ai-svc 최근 커밋: 슬라이스 #7 mentor(26534cf 등). B2 흔적 없음.
- 결론: B2는 ai-svc를 전혀 건드리지 않음. ai-svc 시드 워커(발행자)는 빌드 C 영역으로 아직 부재 — 정상.

## 4. develop CI 녹색

- `gh pr checks 10`: build=pass(1m23s), image=skipping, deploy=skipping. (develop 대상이라 image/deploy 잡 스킵은 정상.)
- `gh run list`: PR #10 head sha `170a22a` run 28216369039 conclusion=success(event=pull_request).
- check-runs API(170a22a): build=success, image=skipped, deploy=skipped.
- 참고: `gh run list --branch develop`는 push 이벤트 위주라 PR #10 run을 직접 보여주지 않으나, head sha·PR checks·check-runs API 3경로로 build success 교차확인.

## 5. 테스트 직접 재실행 (직접 검증)

- 도커 postgres(devpath-local-postgres-1, pgvector/pgvector:pg17) Up 2h healthy, 5432 포트.
- 실행: `cd devpath-community-svc && DB_URL=jdbc:postgresql://localhost:5432/devpath_citest DB_USER=devpath DB_PASSWORD=localdev ./gradlew.bat test --rerun-tasks`
- 결과: **BUILD SUCCESSFUL in 30s**, GRADLE_EXIT=0.
- JUnit XML(build/test-results/test/) 12개 스위트 합산:

| 스위트 | tests |
|---|---|
| CommunityApplicationTests | 1 |
| CommunityContextTest | 1 |
| DbConnectionTest | 1 |
| outbox.OutboxRelayTest | 1 |
| post.CommunityRepositoryTest | 1 |
| post.QnaMockMvcTest | 4 |
| post.QuestionOutboxTest | 1 |
| post.TagMockMvcTest | 1 |
| post.VoteMockMvcTest | 2 |
| seed.CommunitySeedConsumerIT | 3 |
| seed.SimilarQuestionApiTest | 3 |
| seed.SimilarQuestionMatcherTest | 2 |
| **합계** | **21 tests / 0 skip / 0 fail / 0 err** |

- 보고서 ③·⑤의 "전체 21 테스트 / 0 실패 / 0 에러 / 0 skip"과 정확히 일치.
- B2 신규 테스트(OutboxRelayTest 1·QuestionOutboxTest 1·CommunitySeedConsumerIT 3·SimilarQuestionApiTest 3·SimilarQuestionMatcherTest 2 = 10건) + B1 회귀 11건 전부 통과.

## 발견된 문제

없음. 보고서의 PR번호·머지SHA·커밋SHA·파일목록(24)·테스트수(21)·CI상태가 전부 독립 검증과 일치. 범위 이탈·ai-svc 침범·미푸시 드리프트 없음(로컬 워킹트리 untracked `.omc/`만, 소스 변경 없음).

### 특이사항(무해, 보고서 ⑥와 부합)
- EmbeddedKafka Windows temp 파일락 정리 ERROR 로그가 테스트 로그에 보이나 BUILD SUCCESSFUL·tests 0 fail로 무영향(보고서 ⑥-3 기재대로).
