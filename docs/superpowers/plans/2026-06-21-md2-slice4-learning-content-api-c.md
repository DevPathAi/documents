# MD2 슬라이스 #4 빌드 C — devpath-learning-svc 콘텐츠 조회/진척 API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `devpath-learning-svc`에 `GET /contents/{idOrSlug}`, `POST /contents/{idOrSlug}/progress`, `GET /contents/me/progress`를 구현한다. 콘텐츠 본문 `content_md`를 `markdown`으로 노출하고, progress 완료 임계 도달 시 ACTIVE learning path의 연결 task를 자동 완료한다.

**Architecture:** 기존 path 도메인의 `Content` entity/repository를 확장하되, runtime API는 `ai.devpath.learning.content` 패키지에 둔다. progress upsert와 task 자동완료는 `JdbcTemplate` native SQL로 구현해 `ON CONFLICT`, `greatest`, `COALESCE` 규칙을 DB에서 보장한다. Dashboard progress는 기존 `path_weekly_tasks.completed_at` 계산을 재사용한다.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · WebMVC · JPA · JdbcTemplate · PostgreSQL 17 · JUnit 5/MockMvc.

## Global Constraints

- 선행: shared 빌드 A가 develop/main에 릴리스되어 `user_content_progress` 테이블이 존재해야 한다.
- B2 seed 없이도 C 테스트는 자체 fixture content/progress insert로 통과해야 한다.
- API prefix는 bare path `/contents/**`.
- 인증은 기존 OAuth2 Resource Server/JWT. `userId = jwt.subject`.
- `user_id`는 users FK가 아니다(Build A). 테스트는 users 행을 seed할 필요가 없고, 기존 `AssessmentControllerTest`처럼 `jwt().jwt(j -> j.subject("42"))`로 인증한다. task 자동완료 테스트는 같은 user_id의 `learning_paths`/`path_milestones`/`path_weekly_tasks`(+`content_id`) fixture만 seed한다.
- progress request는 누적값이다. delta가 아니다.
- 낮은 progress 재전송으로 값이 감소하면 안 된다.

---

## File Structure

- Modify: `src/main/java/ai/devpath/learning/path/Content.java` — `contentMd` 매핑 추가.
- Modify: `src/main/java/ai/devpath/learning/path/ContentRepository.java` — id/status, slug/status 조회 추가.
- Create: `src/main/java/ai/devpath/learning/content/ContentController.java`
- Create: `ContentService.java`, `ContentProgressRepository.java`, `ContentProgressProperties.java`
- Create: `LearningContentView.java`, `ContentProgressView.java`, `UpsertContentProgressRequest.java`, `UpsertContentProgressResponse.java`, `ProgressListView.java`, `ContentProgressItem.java`
- Create: `ContentNotFoundException.java`, `InvalidProgressException.java`, `InvalidContentIdException.java`
- Modify: `src/main/java/ai/devpath/learning/config/GlobalExceptionHandler.java`
- Create: `src/test/java/ai/devpath/learning/content/ContentControllerTest.java`
- Create: `src/test/java/ai/devpath/learning/content/ContentProgressRepositoryTest.java`

---

## Task 0: 브랜치와 shared artifact 확인

- [ ] **Step 1: 브랜치**

```powershell
cd devpath-learning-svc
git switch develop
git pull
git switch -c feat/slice4-content-progress-api
```

- [ ] **Step 2: shared 최신 반영**

```powershell
.\gradlew.bat --refresh-dependencies test --tests ai.devpath.learning.LearningApplicationTests
```

Expected: shared A가 아직 publish 전이면 `user_content_progress` 관련 테스트는 작성 후 실패한다. 구현 시작 전 A publish 상태를 확인한다.

---

## Task 1: Content entity/repository 계약 테스트

**Files:**
- Modify: `Content.java`
- Modify: `ContentRepository.java`
- Create: `ContentRepositoryTest.java` 또는 `ContentControllerTest` 내 fixture

- [ ] **Step 1: 실패 테스트**

테스트:

- `content_md`가 JPA entity의 `contentMd`로 읽힌다.
- `findByIdAndStatus(id, "PUBLISHED")`는 PUBLISHED만 반환한다.
- `findBySlugAndStatus(slug, "PUBLISHED")`는 slug 조회를 지원한다.
- DRAFT는 조회되지 않는다.

- [ ] **Step 2: 구현**

`Content.java`에 추가:

```java
@Column(name = "content_md", nullable = false)
private String contentMd;
```

> **검수 반영:** `Content`는 이미 `slug,title,track,estimatedMinutes,difficulty,bloomLevel,conceptTags,status`를 매핑하고 있다. 핸드오프의 "`difficulty` 미매핑"은 오인이며 실제 `Content.java:16`에 `private Double difficulty;`가 있다. **누락은 `content_md` 하나뿐**이므로 `contentMd` 필드 + getter만 추가한다. `application.yml`이 `spring.jpa.hibernate.ddl-auto: validate`라 컬럼명은 shared `V202606181006`의 `content_md`(TEXT NOT NULL)와 정확히 일치해야 하고, 누락 시 부팅 검증이 실패한다.
>
> 주의: `conceptTags`는 `@JdbcTypeCode(SqlTypes.JSON) private String conceptTags;`로 **JSON 문자열**이다. 응답에서 `conceptTags: ["spring-tx"]` 배열로 노출하려면 이 String을 `List<String>`으로 역직렬화해야 한다(Task 3 Step 3 참조). entity 타입 자체는 바꾸지 않는다(매칭/seed가 String JSON에 의존).

`ContentRepository`:

```java
Optional<Content> findByIdAndStatus(Long id, String status);
Optional<Content> findBySlugAndStatus(String slug, String status);
```

---

## Task 2: progress repository native upsert

**Files:**
- Create: `ContentProgressRepository.java`
- Create: `ContentProgressRepositoryTest.java`

- [ ] **Step 1: 실패 테스트**

테스트 케이스:

- 첫 progress request는 insert.
- 낮은 `scrollPct`/`dwellSec` 재전송은 기존 값을 낮추지 않음.
- 임계 미달이면 `completedAt` null.
- `scrollPct >= 0.8` AND `dwellSec >= 45`면 `completedAt` set.
- 이미 완료된 row는 `completedAt`을 변경하지 않음.
- 경로 밖 content면 taskCompletedCount 0.
- ACTIVE path 연결 task만 완료.
- ARCHIVED path task는 변경되지 않음.
- 같은 content_id가 ACTIVE path 여러 task에 있으면 실제 갱신 수를 반환.

- [ ] **Step 2: upsert SQL 구현**

핵심 규칙:

```sql
INSERT INTO user_content_progress(user_id, content_id, scroll_pct, dwell_sec, completed_at)
VALUES (:userId, :contentId, :scrollPct, :dwellSec, :completedAtIfThreshold)
ON CONFLICT (user_id, content_id) DO UPDATE SET
  scroll_pct = GREATEST(user_content_progress.scroll_pct, EXCLUDED.scroll_pct),
  dwell_sec = GREATEST(user_content_progress.dwell_sec, EXCLUDED.dwell_sec),
  completed_at = CASE
    WHEN GREATEST(user_content_progress.scroll_pct, EXCLUDED.scroll_pct) >= :scrollThreshold
     AND GREATEST(user_content_progress.dwell_sec, EXCLUDED.dwell_sec) >= :minDwellSec
    THEN COALESCE(user_content_progress.completed_at, now())
    ELSE user_content_progress.completed_at
  END,
  updated_at = now()
RETURNING content_id, scroll_pct, dwell_sec, completed_at;
```

- [ ] **Step 3: task 자동완료 SQL**

```sql
UPDATE path_weekly_tasks t
SET completed_at = COALESCE(t.completed_at, now())
FROM path_milestones m
JOIN learning_paths p ON p.id = m.path_id
WHERE t.milestone_id = m.id
  AND p.user_id = :userId
  AND p.status = 'ACTIVE'
  AND t.content_id = :contentId
  AND t.completed_at IS NULL
```

완료 임계에 도달한 경우에만 실행한다.

`taskCompletedCount`(응답 필드)는 이 UPDATE의 영향 행 수 = `JdbcTemplate.update(sql, params)`의 반환값이다. 완료 임계 미도달이면 UPDATE를 실행하지 않고 0을 반환한다. `WHERE ... AND t.completed_at IS NULL`이 이미 완료된 task를 제외하므로 재호출에도 멱등(경로 밖 콘텐츠는 매칭 0건 → 0). 대상 컬럼 `path_weekly_tasks.content_id`는 shared `V202606181006`에 존재함을 확인했다. upsert와 task 자동완료는 같은 트랜잭션(`@Transactional`)에서 실행한다.

---

## Task 3: service/properties/DTO

**Files:**
- Create: `ContentProgressProperties.java`
- Create: DTO records
- Create: `ContentService.java`

- [ ] **Step 1: properties**

`application.yml`:

```yaml
devpath:
  content:
    completion:
      scroll-threshold: ${CONTENT_COMPLETION_SCROLL_THRESHOLD:0.8}
      min-dwell-sec: ${CONTENT_COMPLETION_MIN_DWELL_SEC:45}
```

- [ ] **Step 2: request validation**

`UpsertContentProgressRequest`:

```java
Double scrollPct;
Integer dwellSec;
```

Validation:

- null -> 400 `INVALID_PROGRESS`.
- `scrollPct < 0 || scrollPct > 1` -> 400.
- `dwellSec < 0` -> 400.

- [ ] **Step 3: idOrSlug 해석 + userId + conceptTags**

- **idOrSlug**: `^\d+$`면 `findByIdAndStatus(Long.parseLong(s), "PUBLISHED")`, 아니면 `findBySlugAndStatus(s, "PUBLISHED")`. 둘 다 miss면 `ContentNotFoundException` → 404 `CONTENT_NOT_FOUND`.
- **overflow**: 숫자처럼 보이지만 `long` 범위를 넘어 `NumberFormatException`이면 `InvalidContentIdException` → 400 `INVALID_CONTENT_ID`. 기존 `IllegalArgumentException` 핸들러는 `errorCode` 없이 400을 내므로 재사용하지 않고 전용 예외를 만든다.
- **userId**: 기존 컨트롤러와 **동일 패턴**으로 JWT subject에서 얻는다 — `@AuthenticationPrincipal Jwt jwt` + `Long.parseLong(jwt.getSubject())`. 참고 구현: `AssessmentController.uid(Jwt)`, `LearningPathController`(L81). 새 인증 방식을 만들지 않는다.
- **conceptTags**: 응답의 `conceptTags`(배열)는 `Content.conceptTags`(JSON 문자열)를 **Jackson 3 `JsonMapper`**로 파싱해 내린다 — `com.fasterxml.jackson...ObjectMapper`가 **아니다**. 기존 `AssessmentService`(L195)가 동일 패턴을 쓴다: `jsonMapper.readValue(json, new tools.jackson.core.type.TypeReference<List<String>>() {})`. 주입받은 `JsonMapper` 빈을 그대로 재사용한다. null/빈 문자열이면 `[]`. (`me/progress` 목록 항목에는 tags가 없으므로 GET 단건에만 적용.)

---

## Task 4: REST controller와 에러 매핑

**Files:**
- Create: `ContentController.java`
- Modify: `GlobalExceptionHandler.java`

- [ ] **Step 1: endpoints**

```java
@GetMapping("/contents/{idOrSlug}")
LearningContentView get(...)

@PostMapping("/contents/{idOrSlug}/progress")
UpsertContentProgressResponse progress(...)

@GetMapping("/contents/me/progress")
ProgressListView myProgress(...)
```

- [ ] **Step 2: response contract**

`GET /contents/{idOrSlug}`:

```json
{
  "id": 1,
  "slug": "backend-spring-transaction-boundary",
  "title": "...",
  "track": "BACKEND_SPRING",
  "markdown": "## ...",
  "estimatedMinutes": 8,
  "difficulty": 0.5,
  "bloomLevel": "APPLY",
  "conceptTags": ["spring-tx"],
  "progress": {
    "scrollPct": 0.42,
    "dwellSec": 73,
    "completed": false,
    "completedAt": null
  }
}
```

- [ ] **Step 3: error codes**

Add handler responses:

- `CONTENT_NOT_FOUND` -> 404.
- `INVALID_PROGRESS` -> 400.
- `INVALID_CONTENT_ID` -> 400.

Use existing map style but include `errorCode`.

---

## Task 5: MockMvc tests

**Files:**
- Create: `ContentControllerTest.java`

> **검수 반영(테스트 패턴):** 기존 `AssessmentControllerTest`를 그대로 따른다 — `@SpringBootTest @AutoConfigureMockMvc @ActiveProfiles("test")` (import는 Boot 4 경로 `org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc`), `@Autowired MockMvc mvc`. 인증은 `import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;` + `var auth = jwt().jwt(j -> j.subject("42"));` 후 모든 요청에 `.with(auth)`. **실 DB**를 쓰므로(@WebMvcTest 슬라이스 아님) fixture는 `ContentRepository.save()` 또는 `JdbcTemplate` insert로 만들고, task 자동완료 검증용 `learning_paths`/`path_milestones`/`path_weekly_tasks`(content_id 포함)도 직접 insert한다. JSON 단언은 `com.jayway.jsonpath.JsonPath` 또는 `jsonPath(...)`.

- [ ] **Step 1: GET tests**

테스트:

- numeric id success.
- slug success.
- DRAFT or missing slug -> 404 `CONTENT_NOT_FOUND`.
- response has `markdown`, `conceptTags`, `progress`.
- unauthenticated request -> 401 by existing security.

- [ ] **Step 2: POST progress tests**

테스트:

- insert returns monotonic progress.
- invalid body values -> 400 `INVALID_PROGRESS`.
- threshold reached returns `completed=true`, `completedAt`, `taskCompletedCount`.
- after completion, `GET /learning-paths/me` task completed is true.
- `/dashboard` progressPercent increases because task completed_at is set.

- [ ] **Step 3: progress list tests**

`GET /contents/me/progress` supports:

- default latest order (`updated_at DESC` — `idx_ucp_user_updated` 사용).
- `completed=true|false`.
- `track=BACKEND_SPRING`.
- `limit` 기본 50, 최대 100(초과 요청은 100으로 clamp). 설계서 §6.3.

항목 형태는 설계서 §6.3과 동일하게 `ProgressListView { items: [ContentProgressItem...] }`이고, `ContentProgressItem`은 `contentId, slug, title, track, scrollPct, dwellSec, completed, completedAt, updatedAt`이다. `slug/title/track`은 `user_content_progress`에 없으므로 `contents` JOIN으로 채운다(`completed = completed_at IS NOT NULL`).

---

## Task 6: 검증과 PR

- [ ] **Step 1: focused tests**

```powershell
.\gradlew.bat test --tests "ai.devpath.learning.content.*"
.\gradlew.bat test --tests "ai.devpath.learning.path.LearningPathEngineTest"
```

- [ ] **Step 2: full build**

```powershell
.\gradlew.bat test
.\gradlew.bat clean build
```

- [ ] **Step 3: develop PR**

```powershell
git push -u origin feat/slice4-content-progress-api
gh pr create --base develop --title "feat: MD2 slice4 content viewer progress API" --body "Adds content read/progress APIs and task completion on progress threshold."
```

## Acceptance Checklist

- [ ] `Content.contentMd` maps `contents.content_md`.
- [ ] `GET /contents/{numericId}` and `GET /contents/{slug}` return PUBLISHED content.
- [ ] response field is `markdown`, not `contentMd`.
- [ ] progress upsert is monotonic.
- [ ] threshold requires both scroll and dwell.
- [ ] ACTIVE path tasks are completed idempotently.
- [ ] ARCHIVED path is not changed.
- [ ] dashboard/path completion reflects progress completion.
- [ ] tests pass without B2 real seed or Ollama.

## Self-Review

- **Spec coverage:** 설계서 §6 API, §7 task 자동완료, §10.1 learning-svc, §11.3 tests를 커버한다.
- **Current source alignment:** 현재 `Content` entity에 `content_md`가 없고 `ContentRepository`는 bare JpaRepository다. 본 빌드는 그 최소 누락부터 보완한다.
- **검수 정정(실코드 대조):** 핸드오프의 "`Content.difficulty` 미매핑"은 오인 — `difficulty`는 이미 매핑됨(`Content.java:16`), 미매핑은 `content_md`뿐. `GlobalExceptionHandler`는 `@RestControllerAdvice`로 `Map<String,String>`(+ 일부 `errorCode`)을 내므로 신규 핸들러도 같은 스타일로 추가. `path_weekly_tasks.content_id`·`application.yml`의 `devpath.*` 트리·JWT subject→userId 패턴 모두 실재 확인. `idOrSlug`/`userId`/`conceptTags` 처리는 위 Task들에 명시했다.
- **검수 확인(추가, 실코드 대조):** `SecurityConfig`가 `.requestMatchers("/onboarding/assessments/guest/**","/actuator/health").permitAll()` + `.anyRequest().authenticated()`라 **`/contents/**`는 보안설정 변경 없이 자동 보호**된다(미인증 401) → 본 빌드는 `SecurityConfig`를 건드리지 않는다. `DashboardService.summary`는 `tasks.filter(WeeklyTaskView::completed)` 비율로 `progressPercent`를 계산하므로 task 자동완료(`completed_at` set)가 곧 dashboard 진척 증가다(§7 재사용 확인). MockMvc 인증/실DB 패턴은 `AssessmentControllerTest`와 동일.
- **Boundary safety:** gateway/frontend는 건드리지 않는다.
