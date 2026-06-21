# 슬라이스 #3 빌드 C — devpath-learning-svc 학습경로 엔진 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `devpath-learning-svc`에 학습경로 엔진을 완성한다. 흐름은 최신 완료 진단 조회 → `devpath-ai-svc` mockable client 호출 → pgvector HNSW 콘텐츠 매칭 → path/milestone/task 영속 → SSE 진행 이벤트 → `LearningPathGeneratedEvent` outbox 기록이다.

**Architecture:** learning-svc가 path 도메인과 SSE를 소유한다. AI 호출과 query embedding 준비는 트랜잭션 밖에서 수행하고, 기존 ACTIVE archive + 신규 ACTIVE path insert + outbox 기록만 짧은 단일 트랜잭션으로 묶는다. `content_embeddings.embedding VECTOR(768)`와 `<=>` 쿼리는 Hibernate entity에 매핑하지 않고 `JdbcTemplate` native repository로만 접근한다. CI에는 Ollama가 없으므로 learning-svc 테스트는 ai-svc client를 `@MockitoBean`/stub으로 대체한다.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · WebMVC/SseEmitter · JPA · JdbcTemplate · PostgreSQL 17 + pgvector · Kafka outbox · JUnit 5/MockMvc/Mockito.

## Global Constraints

- 레포 절대조건: 추측 금지 · **테스트 우선** · 문제 시 코드 분석. (`devpath-learning-svc/CLAUDE.md`)
- 브랜치: `develop` 기준. main 직접 금지.
- **범위:** 빌드 C만 수행한다. platform DONE 소비(D), gateway/frontend(E)는 범위 밖이다.
- **API prefix:** 기존 슬라이스 #1/#2와 동일하게 bare path 유지: `/learning-paths/**`.
- **CI Ollama 실호출 금지:** learning-svc 테스트는 ai-svc client mock/stub만 사용한다.
- **진단 조회:** `assessment_results` 단독 조회 금지. 반드시 `assessment_results r join assessments a`로 user별 최신 `COMPLETED`를 조회한다.
- **트랜잭션 경계:** AI generate/embed 호출은 `@Transactional` 밖. DB archive/insert/outbox만 `@Transactional`.
- **ACTIVE 1개:** DB partial unique `learning_paths(user_id) WHERE status='ACTIVE'`가 최종 방어선이다. 동시 요청 충돌은 409로 매핑한다.
- **임베딩:** vector는 native SQL/JdbcTemplate만 사용. query embedding 길이 768 검증.
- **경로 품질:** milestone별 task는 정확히 3개. 3개 미만은 계약 오류, 초과는 ai-svc B 계약상 없어야 하지만 방어적으로 top 3만 영속한다.
- **shared 이벤트:** 이번 빌드에서는 기존 `LearningPathGeneratedEvent(eventId, occurredAt, userId, learningPathId, targetTrack)`를 그대로 사용한다. `diagnosedLevel` 확장은 D와 shared 호환 테스트가 필요한 별도 PR로 둔다.

---

## File Structure

- Modify: `devpath-learning-svc/.github/workflows/ci.yml` — postgres image를 `pgvector/pgvector:pg17`로 전환.
- Modify: `devpath-learning-svc/src/main/resources/application.yml` — `devpath.ai-svc.base-url`, timeout 설정.
- Create: `src/main/java/ai/devpath/learning/path/**` — controller, service, JPA entities/repositories, DTOs, ai client, native matcher, event publisher.
- Modify: `src/main/java/ai/devpath/learning/config/GlobalExceptionHandler.java` — path-specific 409/502/503/404 매핑.
- Create: `src/test/java/ai/devpath/learning/path/**` — latest diagnosis, generation orchestration, native matching, controller/SSE, outbox tests.
- Create: `src/test/resources/seed/content_seed.sql` or test fixture methods — deterministic content/vector seed.

---

## Task 1: CI/설정 선행 게이트

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `src/main/resources/application.yml`

- [ ] **Step 1: CI postgres image 전환**

`.github/workflows/ci.yml`:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg17
```

- [ ] **Step 2: ai-svc client config 추가**

`application.yml`:

```yaml
devpath:
  ai-svc:
    base-url: ${AI_SVC_BASE_URL:http://localhost:8081}
    timeout: ${AI_SVC_TIMEOUT:PT8S}
```

- [ ] **Step 3: 정적 검증**

```powershell
rg -n "pgvector/pgvector:pg17|ai-svc|AI_SVC" .github src/main/resources
```

Expected: learning CI postgres가 pgvector이고 ai-svc 설정이 존재.

---

## Task 2: Path 도메인 JPA/DTO 골격

**Files:**
- Create: `path/LearningPath.java`, `PathMilestone.java`, `PathWeeklyTask.java`, `Content.java`
- Create: `path/LearningPathRepository.java`, `PathMilestoneRepository.java`, `PathWeeklyTaskRepository.java`
- Create: `path/dto/*.java`

**Interfaces:**
- Consumes shared schema `learning_paths`, `path_milestones`, `path_weekly_tasks`, `contents`.
- Does not map `content_embeddings.embedding`.

- [ ] **Step 1: JPA slice 실패 테스트**

`LearningPathJpaTest`: path + milestone + 3 tasks 저장, ACTIVE user lookup, 기존 ACTIVE archive update를 검증한다.

- [ ] **Step 2: 엔티티 구현**

JPA 매핑:
- `LearningPath`: id, userId, generatedAt, track, totalWeeks, genPromptVersion, sourceEmbeddingVersion, status, aiRationale, milestones.
- `PathMilestone`: expectedOutcome 포함.
- `PathWeeklyTask`: nullable contentId 또는 `Content` lazy reference. 단순화를 위해 `contentId` 컬럼 직접 매핑 권장.
- `Content`: id, slug, title, track, estimatedMinutes, difficulty, bloomLevel, conceptTags, status.

- [ ] **Step 3: repository 구현**

필수 method:
- `Optional<LearningPath> findFirstByUserIdAndStatusOrderByGeneratedAtDesc(Long userId, String status)`
- `@Modifying archiveActiveByUserId(userId)`
- milestone/task 조회는 path aggregate cascade 또는 repository query.

---

## Task 3: 최신 완료 진단 조회

**Files:**
- Create: `path/LatestDiagnosisRepository.java`
- Create: `path/LatestDiagnosis.java`
- Create test: `path/LatestDiagnosisRepositoryTest.java`

**Query:**

```sql
select r.assessment_id, a.track, r.diagnosed_level, r.strength_concepts,
       r.weakness_concepts, r.confidence_weight
from assessment_results r
join assessments a on r.assessment_id = a.id
where a.user_id = :userId and a.status = 'COMPLETED'
order by a.completed_at desc nulls last, a.id desc
limit 1
```

- [ ] **Step 1: 실패 테스트**

테스트 케이스:
- 같은 user의 여러 완료 진단 중 `completed_at desc, id desc` 최신 선택.
- 다른 user 결과는 제외.
- `IN_PROGRESS` assessment result는 제외.
- 없으면 empty → service/controller에서 409 `NO_COMPLETED_ASSESSMENT`.

- [ ] **Step 2: JdbcTemplate repository 구현**

JSON 문자열(`strength_concepts`, `weakness_concepts`)은 repository에서 `List<String>`으로 파싱한다. 파싱 실패는 계약 오류가 아니라 빈 목록 fallback으로 둔다(진단 서비스 기존 parseTags 관례와 정합).

---

## Task 4: ai-svc client boundary

**Files:**
- Create: `path/ai/AiPathClient.java`
- Create: `path/ai/RestAiPathClient.java`
- Create: `path/ai/dto/*.java`
- Create test: `path/ai/RestAiPathClientTest.java` 또는 service mock 테스트

**Interfaces:**
- `POST {baseUrl}/ai/path/generate`
- `POST {baseUrl}/ai/embed`

- [ ] **Step 1: client interface 작성**

```java
PathGenerateResult generate(PathGenerateCommand command);
List<List<Double>> embed(List<String> texts);
```

- [ ] **Step 2: RestClient 구현**

Timeout은 config에서 주입. 4xx/5xx/connection/timeout은 path service가 SSE error로 매핑할 수 있게 `AiServiceUnavailableException` 또는 `AiServiceContractException`으로 변환한다.

- [ ] **Step 3: 테스트 원칙**

CI test에서는 실제 ai-svc/Ollama 호출 금지. orchestration tests는 `@MockitoBean AiPathClient`로 대체한다.

---

## Task 5: pgvector native content matching

**Files:**
- Create: `path/ContentEmbeddingMatcher.java`
- Create test: `path/ContentEmbeddingMatcherTest.java`

**Native SQL:**

```sql
select c.id, c.slug, c.title, ce.chunk_text, ce.embedding <=> ?::vector as distance
from content_embeddings ce
join contents c on c.id = ce.content_id
where ce.status = 'ACTIVE'
  and c.status = 'PUBLISHED'
  and c.track = ?
order by ce.embedding <=> ?::vector
limit ?
```

- [ ] **Step 1: deterministic vector seed 테스트**

고정 768차원 vector 2~3개와 query vector를 insert한 뒤 track/status 필터와 nearest ordering을 단언한다.

- [ ] **Step 2: 구현**

`List<Double>` → pgvector literal 문자열(`[0.1,0.2,...]`)로 변환하되 길이 768을 검증한다. SQL parameter는 `?::vector`를 사용한다.

- [ ] **Step 3: fallback 정책**

매칭이 없으면 `contentId=null`로 task를 영속한다. path 생성은 실패시키지 않는다.

---

## Task 6: 경로 생성 orchestration + short transaction persist/outbox

**Files:**
- Create: `path/LearningPathGenerationService.java`
- Create: `path/LearningPathPersistenceService.java`
- Create: `path/LearningPathEventPublisher.java`
- Create tests: `LearningPathGenerationServiceTest`, `LearningPathPersistenceServiceTest`

**Flow:**
1. `collecting`: `LatestDiagnosisRepository.findLatestCompleted(userId)`; 없으면 409.
2. `generating`: `AiPathClient.generate(...)`.
3. `matching`: milestone target skills/title로 query text 생성 → `AiPathClient.embed(...)` → `ContentEmbeddingMatcher.match(...)`.
4. `persist`: `@Transactional` persistence service archives active path, inserts new path/milestones/tasks, writes outbox `learning.path.generated`.

- [ ] **Step 1: orchestration 실패 테스트**

Mock ai-svc client로:
- 진단 없음 → 409, ai-svc 호출 없음.
- generate 호출이 진단 값(track/level/strength/weakness/goal)을 받음.
- embed 호출은 milestone별 query text 수만큼 batch.
- matcher 결과가 task.contentId에 들어감.
- task 3개 미만 milestone → contract exception.

- [ ] **Step 2: persistence 실패 테스트**

실 DB 테스트:
- 기존 ACTIVE path가 ARCHIVED되고 신규 ACTIVE 1개 생성.
- milestone expectedOutcome, whyThisOrder, targetSkills JSON 저장.
- 1주차 task 정확히 3개.
- outbox에 `event_type='learning.path.generated'`, aggregate_type=`learning_path`, aggregate_id=`pathId`, payload에 userId/pathId/targetTrack 포함.

- [ ] **Step 3: 구현**

`LearningPathGenerationService`는 transactional annotation을 붙이지 않는다. `LearningPathPersistenceService.persistGeneratedPath(...)`만 `@Transactional`.

---

## Task 7: REST/SSE API

**Files:**
- Create: `path/LearningPathController.java`
- Create DTOs: `LearningPathView`, `MilestoneView`, `WeeklyTaskView`, `ThisWeekView`, `RationaleView`, `PathProgressEvent`
- Create tests: `LearningPathControllerTest`

**Endpoints:**
- `POST /learning-paths/me/generate` — `text/event-stream`, stages `collecting`, `generating`, `matching`, `done`.
- `GET /learning-paths/me`
- `GET /learning-paths/me/this-week`
- `GET /learning-paths/{id}/rationale`
- `POST /learning-paths/me/regenerate` — 동기 200, optional reason/goal body.

- [ ] **Step 1: SSE 테스트**

MockMvc async/SseEmitter 테스트:
- authenticated jwt subject → userId.
- stream contains collecting → generating → matching → done in order.
- done event JSON has camelCase `pathId`.
- 진단 없음은 409 JSON `{errorCode:"NO_COMPLETED_ASSESSMENT"}`.
- ai-svc unavailable는 503 또는 SSE error event로 고정. 권장: stream 시작 전 collecting 실패는 HTTP 409, generating/matching 중 실패는 SSE `stage:"error"`.

- [ ] **Step 2: GET API 테스트**

Seed persisted path:
- `/me` returns pathId, track, totalWeeks, rationale, diagnosis, milestones, expectedOutcome, task contentSlug.
- `/this-week` returns weekNum=1 and exactly 3 tasks when path has complete seed.
- `/rationale` owner only; 다른 user는 403/404.

- [ ] **Step 3: 구현**

`SseEmitter`는 stage별 event를 즉시 send하고 generation/persist는 executor에서 실행한다. 테스트 안정성을 위해 generation service에서 progress callback을 받는 구조를 사용한다.

---

## Task 8: seed content / embedding fixtures

**Files:**
- Create: `src/main/resources/db/seed/learning_content_seed.sql` or service-local startup seeder disabled by default.
- Create test fixture helper under `src/test/java/.../path/PathTestFixtures.java`

- [ ] **Step 1: 테스트 seed helper**

CI는 Ollama 없이 고정 vector insert로 matching을 검증한다.

- [ ] **Step 2: 운영 seed 방식**

본 빌드에서는 migration이 아닌 별도 seed SQL/runbook으로 둔다. 콘텐츠 대량화는 슬라이스 #4.

---

## Task 9: 전체 검증

- [ ] **Step 1: focused tests**

```powershell
cd devpath-learning-svc
.\gradlew.bat test --tests "ai.devpath.learning.path.*"
```

- [ ] **Step 2: full tests**

```powershell
.\gradlew.bat test
```

- [ ] **Step 3: build**

```powershell
.\gradlew.bat clean build
```

- [ ] **Step 4: no real AI scan**

```powershell
rg -n "localhost:11434|ollama|MockWebServer" src/test src/main
```

Expected: learning-svc tests do not depend on Ollama; ai-svc boundary is mockable.

---

## Acceptance Checklist

- [ ] `POST /learning-paths/me/generate` emits `collecting → generating → matching → done`.
- [ ] 최신 완료 진단 join query uses `assessment_results` + `assessments`, user/status/order 조건이 deterministic하다.
- [ ] No completed assessment returns 409 with `NO_COMPLETED_ASSESSMENT`.
- [ ] learning-svc tests mock `AiPathClient`; CI never calls real Ollama.
- [ ] AI generate/embed happen outside DB transaction.
- [ ] Persist transaction archives previous ACTIVE path and inserts exactly one new ACTIVE path.
- [ ] `LearningPathGeneratedEvent` outbox is written in the same transaction as path persist.
- [ ] pgvector matching uses native `JdbcTemplate` and `<=>`, not Hibernate vector mapping.
- [ ] Matching miss keeps task with `contentId=null`.
- [ ] `/learning-paths/me`, `/this-week`, `/rationale`, `/regenerate` match 설계서 §5.
- [ ] learning-svc CI postgres image is `pgvector/pgvector:pg17`.

---

## Self-Review

- **Spec coverage:** 설계서 §4~§6, §9 Build C, §10 CI mock, R-5 task 3개/expectedOutcome, R-7 latest diagnosis join, R-8 transaction/concurrency, R-9 native vector repository를 커버한다.
- **Current source alignment:** 기존 assessment/outbox/security 패턴을 재사용한다. shared schema A가 이미 `expected_outcome`, active partial unique, VECTOR(768), HNSW를 제공하므로 C는 서비스 구현에 집중한다.
- **CI safety:** ai-svc/Ollama는 mock boundary 뒤에 있다. pgvector는 learning CI image 전환으로 Flyway/JPA 테스트가 plain postgres에서 깨지는 문제를 차단한다.
- **Risk:** `SseEmitter` async 테스트는 타이밍 민감도가 있다. generation service에 progress callback을 두고 MockMvc async result를 명시 대기해 안정화한다.
