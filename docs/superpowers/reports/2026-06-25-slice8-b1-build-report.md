# 빌드 B1 (community-svc 코어) — Q&A CRUD 구현 보고서

- **일자**: 2026-06-26
- **레포**: `devpath-community-svc`
- **브랜치**: `feat/slice8-community-core` (develop에서 분기, 푸시 안 함)
- **플랜**: `documents/docs/superpowers/plans/2026-06-25-md3-slice8-community-core-b1.md` (B1-1 ~ B1-6)
- **결과**: **전 태스크 완료(GREEN)**. 전체 테스트 11개 통과(failures=0, errors=0). `./gradlew build` 성공.

---

## 태스크별 상태

| 태스크 | 내용 | 상태 | 커밋 SHA | 테스트 |
|---|---|---|---|---|
| B1-1 | deps(security/oauth2) 활성 + SecurityConfig + 컨텍스트 기동 | ✅ 완료 | `32ee359` | CommunityContextTest 1 PASS |
| B1-2 | Q&A 엔티티 6종 + 리포지토리 6종 + JPA 매핑 검증 | ✅ 완료 | `2ad7c66` | CommunityRepositoryTest 1 PASS |
| B1-3 | 질문 작성·목록·상세 + 태그 연결 | ✅ 완료 | `1b724ea` | QnaMockMvcTest 3 PASS |
| B1-4 | 답변 작성 + 채택(OWNER 검사) | ✅ 완료 | `171c235` | QnaMockMvcTest 4 PASS(누적) |
| B1-5 | 투표 UPSERT + 카운트 집계 | ✅ 완료 | `0304cc7` | VoteMockMvcTest 2 PASS |
| B1-6 | 태그 자동완성 + B1 코어 전체 검증 | ✅ 완료 | `49fe077` | TagMockMvcTest 1 PASS + 전체 11 PASS |

각 태스크는 TDD(RED→GREEN)로 진행했고, 플랜에 적힌 검증 명령(`DB_URL=jdbc:postgresql://localhost:5432/devpath_citest DB_USER=devpath DB_PASSWORD=localdev ./gradlew.bat test --tests "..."`)을 그대로 사용해 실패→통과를 눈으로 확인했다.

### 전체 테스트 집계 (최종 `./gradlew test`)

```
ai.devpath.community.CommunityApplicationTests    tests=1 failures=0 errors=0  (기존)
ai.devpath.community.CommunityContextTest         tests=1 failures=0 errors=0  (B1-1)
ai.devpath.community.DbConnectionTest             tests=1 failures=0 errors=0  (기존)
ai.devpath.community.post.CommunityRepositoryTest tests=1 failures=0 errors=0  (B1-2)
ai.devpath.community.post.QnaMockMvcTest          tests=4 failures=0 errors=0  (B1-3,B1-4)
ai.devpath.community.post.VoteMockMvcTest         tests=2 failures=0 errors=0  (B1-5)
ai.devpath.community.post.TagMockMvcTest          tests=1 failures=0 errors=0  (B1-6)
=== TOTAL: tests=11 failures=0 errors=0 skipped=0 ===
```

`./gradlew build`(컴파일+테스트+jar 어셈블) 도 BUILD SUCCESSFUL.

---

## 생성·수정한 파일 전체 목록

### 수정 (기존 파일)
- `build.gradle.kts` — security + oauth2-resource-server 활성, test deps 추가(security-test, data-jpa-test, spring-boot-flyway, flyway-core, flyway-database-postgresql). **kafka/redis는 주석 유지(B2 범위)**.
- `src/main/resources/application.yml` — `devpath.auth.jwt-secret` 추가.

### 생성 (main)
- `src/main/java/ai/devpath/community/config/SecurityConfig.java`
- `src/main/java/ai/devpath/community/config/GlobalExceptionHandler.java`
- `src/main/java/ai/devpath/community/post/CommunityPost.java`
- `src/main/java/ai/devpath/community/post/CommunityQuestion.java`
- `src/main/java/ai/devpath/community/post/CommunityAnswer.java`
- `src/main/java/ai/devpath/community/post/CommunityVote.java`
- `src/main/java/ai/devpath/community/post/CommunityTag.java`
- `src/main/java/ai/devpath/community/post/CommunityPostTag.java`
- `src/main/java/ai/devpath/community/post/CommunityPostTagId.java`
- `src/main/java/ai/devpath/community/post/CommunityPostRepository.java`
- `src/main/java/ai/devpath/community/post/CommunityQuestionRepository.java`
- `src/main/java/ai/devpath/community/post/CommunityAnswerRepository.java`
- `src/main/java/ai/devpath/community/post/CommunityVoteRepository.java`
- `src/main/java/ai/devpath/community/post/CommunityTagRepository.java`
- `src/main/java/ai/devpath/community/post/CommunityPostTagRepository.java`
- `src/main/java/ai/devpath/community/post/QuestionService.java`
- `src/main/java/ai/devpath/community/post/AnswerService.java`
- `src/main/java/ai/devpath/community/post/VoteService.java`
- `src/main/java/ai/devpath/community/post/TagService.java`
- `src/main/java/ai/devpath/community/post/CommunityController.java`
- `src/main/java/ai/devpath/community/post/NotFoundException.java`
- `src/main/java/ai/devpath/community/post/ForbiddenException.java`
- `src/main/java/ai/devpath/community/post/InvalidVoteException.java`
- `src/main/java/ai/devpath/community/post/dto/CreateQuestionRequest.java`
- `src/main/java/ai/devpath/community/post/dto/QuestionDetailView.java`
- `src/main/java/ai/devpath/community/post/dto/PostSummaryView.java`
- `src/main/java/ai/devpath/community/post/dto/AnswerView.java`
- `src/main/java/ai/devpath/community/post/dto/CreateAnswerRequest.java`
- `src/main/java/ai/devpath/community/post/dto/VoteRequest.java`
- `src/main/java/ai/devpath/community/post/dto/TagView.java`

### 생성 (test)
- `src/test/resources/application-test.yml`
- `src/test/java/ai/devpath/community/CommunityContextTest.java`
- `src/test/java/ai/devpath/community/post/CommunityRepositoryTest.java`
- `src/test/java/ai/devpath/community/post/QnaMockMvcTest.java`
- `src/test/java/ai/devpath/community/post/VoteMockMvcTest.java`
- `src/test/java/ai/devpath/community/post/TagMockMvcTest.java`

---

## 플랜과 달라진 점 (있음 — 이유 포함)

플랜의 비즈니스/도메인 코드(엔티티·서비스·컨트롤러·DTO·SecurityConfig·SQL 매핑)는 **전부 플랜 그대로** 구현했다. 단, **테스트 클래스의 Spring Boot 4.0.7 패키지 경로**만 플랜과 달라졌다. 플랜의 테스트 import는 Boot 3 경로로 작성돼 있어 Boot 4.0.7에서 컴파일되지 않았다. 같은 Boot 버전을 쓰는 `devpath-learning-svc`의 **실제 동작하는 테스트**에서 정확한 Boot 4 경로를 확인해 정정했다(추측 아님, 실측).

1. **`@DataJpaTest` import** (B1-2, `CommunityRepositoryTest`)
   - 플랜: `org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest` (Boot 3)
   - 정정: `org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest` (Boot 4.0.7, learning-svc `AssessmentJpaTest` 확인)

2. **`@AutoConfigureTestDatabase(replace=NONE)` → `@TestPropertySource`** (B1-2)
   - 플랜: `@AutoConfigureTestDatabase(replace = Replace.NONE)` (import 경로가 Boot 4에서 이동·미존재)
   - 정정: `@TestPropertySource(properties = "spring.test.database.replace=none")` — learning-svc `AssessmentJpaTest`가 쓰는 Boot 4 관용 방식. 효과 동일(테스트 DB 치환 비활성 → 실 `devpath_citest` 사용).

3. **`@AutoConfigureMockMvc` import** (B1-3/4/5/6, `QnaMockMvcTest`·`VoteMockMvcTest`·`TagMockMvcTest`)
   - 플랜: `org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc` (Boot 3)
   - 정정: `org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc` (Boot 4.0.7, learning-svc 확인)

> 이 3건은 모두 **테스트 인프라 import 경로**일 뿐 테스트 로직·단언·구현 코드는 플랜과 동일하다. 도메인 계약(엔드포인트·DTO·상태 전이·권한)은 변경 없음.

### B1-1 RED 신호 관련 메모 (구현엔 영향 없음)
플랜 B1-1 Step3은 SecurityConfig 부재 시 컨텍스트 기동 실패(RED)를 기대했으나, Boot 4 기본 보안 자동구성이 관대해 SecurityConfig 없이도 컨텍스트가 떴다(GREEN). SecurityConfig는 후속 태스크의 JWT 동작(특히 B1-3 `unauthenticatedRejected` 401)에 필수이므로 플랜대로 작성했고, 실제 JWT 401 거부는 `QnaMockMvcTest.unauthenticatedRejected`로 검증됨.

---

## 막힌 점 (NEEDS_CONTEXT)

없음. 모든 태스크를 명세대로 완료했다.

### 작업 중 발생한 환경 이슈 (해결됨, 코드 무관)
B1-2 GREEN 검증 직전 **docker postgres(localhost:5432)가 다운**됐다(B1-1 테스트는 정상 통과했으므로 그 사이 Docker Desktop 중지로 추정). `java.net.ConnectException: Connection to localhost:5432 refused`로 `@DataJpaTest`·`@SpringBootTest` 모두 실패. raw TCP 체크로 5432/5433 닫힘 확인 → Docker Desktop 재기동 → `devpath-shared/docker-compose.yml`로 postgres 기동 → `devpath_citest`에 community_* 7개 테이블(빌드 A) 존재 확인 → 재검증 GREEN. **코드 수정 없음**.

---

## 스코프 준수 (Scope Lock)

- B1-1 ~ B1-6만 구현. **B2(Outbox·Kafka·이벤트 발행/소비·유사질문·pgvector·embedding) 미착수.**
- `build.gradle.kts`에 kafka/redis 추가 안 함(주석 유지). security/oauth2만 활성.
- `find src/main/java`로 outbox/kafka/consumer/embed/similar 파일 0건 확인.
- 푸시 안 함(커밋까지만). `.omc/`만 untracked(기존, 미커밋).

---

## 최종 `git log --oneline` (develop..HEAD)

```
49fe077 feat(community): 태그 자동완성 + B1 코어 전체 검증 (B1-6)
0304cc7 feat(community): 투표 UPSERT + 카운트 집계 (B1-5)
171c235 feat(community): 답변 작성 + 채택(OWNER 검사) (B1-4)
1b724ea feat(community): 질문 작성·목록·상세 + 태그 연결 (B1-3)
2ad7c66 feat(community): Q&A 엔티티 6종 + 리포지토리 + JPA 매핑 검증 (B1-2)
32ee359 feat(community): deps(security/oauth2) 활성 + SecurityConfig + 컨텍스트 기동 (B1-1)
```
