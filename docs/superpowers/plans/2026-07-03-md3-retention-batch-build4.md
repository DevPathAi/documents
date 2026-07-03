# 참여촉진배치 Build 4 (정체 탐지 + AI 재참여 제안 + 발송) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** learning-svc가 3일 연속 미활동 유저를 탐지해 `UserStagnatedEvent`(학습경로 요약 포함)를 발행하고, ai-svc가 `POST /ai/re-engagement`로 재참여 문구를 생성하며, notification-svc가 이벤트를 구독해 ai-svc를 호출한 뒤 재참여 알림을 전달한다.

**Architecture:** **신규 스케줄러를 만들지 않는다.** learning-svc의 기존 `StreakRolloverService.rollover()`(시간대 윈도우 스캔, 로컬 자정 1회) "어제 활동 없음" 분기에 정체 판정을 추가한다 — `last_active_date` 기준 `daysInactive`를 계산해 **정확히 3일째**이고 아직 통지 안 했으면(`user_streak.stagnation_notified_at IS NULL`) `UserStagnatedEvent`를 outbox로 발행하고 마커를 세팅, 유저가 다시 활동하면 마커를 리셋한다. 이벤트 payload에 learning-svc가 조립한 `currentLearningPathSummary`를 실어 notification-svc가 학습경로에 접근하지 않고도 그대로 ai-svc에 넘긴다. ai-svc `retention` 모듈은 기존 review 도메인(non-streaming Claude 호출)을 미러링해 `ReEngagementSuggestionClient`(Mock/Claude, provider 프로퍼티로 선택)로 문구를 만든다. notification-svc `StagnationConsumer`는 `RestReEngagementClient`(ai-svc 직통 RestClient)로 문구를 받아(실패 시 폴백 문구) 기존 `PushSender`(Build 3)로 전달한다.

**Tech Stack:** Java 21 · Spring Boot 4.0.7 · Gradle(Kotlin DSL) · Spring Data JPA · Kafka(outbox relay) · Anthropic Java SDK 2.34.0(ai-svc) · devpath-shared(중앙 Flyway, GitHub Packages).

**스펙:** [2026-07-01-md3-retention-batch-design.md](../specs/2026-07-01-md3-retention-batch-design.md) §"컴포넌트별 설계"(learning-svc `progress`·ai-svc `retention`·notification-svc `StagnationConsumer`) + §"이벤트 계약"(`UserStagnatedEvent`) + §"에러 처리" + §"빌드 분해 Build 4". **랜드스케이프 조사:** `scratchpad/build4-landscape.md`(2026-07-03).

## 착수 전 결정(2026-07-03, 사용자 확정)

- **재발행 방지 = `user_streak`에 `stagnation_notified_at TIMESTAMPTZ` 컬럼 추가**(devpath-shared 마이그레이션 + 엔티티 필드). 발행 시 세팅, 재활성 시 null 리셋 → 에피소드당 정확히 1회 보장.
- **`currentLearningPathSummary` = `UserStagnatedEvent` payload에 포함**(스펙 이벤트 레코드를 1필드 확장). learning-svc가 발행 시 조립. notification-svc는 이벤트에서 꺼내 ai-svc에 전달만. (스펙의 이벤트 레코드에는 이 필드가 없었으나, 스펙의 ai-svc 요청 shape가 이 필드를 요구하는 내부 모순을 이렇게 해소.)

## Global Constraints

- **devpath-shared 변경(이벤트 + 마이그레이션)은 가장 먼저 `main`에 병합·publish**되어야 learning/notification-svc가 소비 가능. shared엔 `develop` 없음 → `feat/*`→`main` 직접 PR. 소비 서비스는 `./gradlew compileJava --refresh-dependencies`로 새 SNAPSHOT 수신(jar **내용 grep**으로 확인, mtime 불가).
- 나머지 서비스는 각 레포 `develop`에서 `feat/*` 분기 → develop PR. 공유 브랜치 직접 작업 금지(각 CLAUDE.md 절대조건 4).
- **TDD**(절대조건 2): 실패 테스트 먼저 → 최소 구현 → 통과 확인(눈으로) → 커밋. **추측 금지**(절대조건 1): 명세 밖 코드 임의 구현 금지.
- Kafka payload는 항상 `String`(JSON), 컨슈머는 `tools.jackson.databind.json.JsonMapper#readValue`로 수동 역직렬화하고 실패 시 로그 후 skip(poison 무한재시도 방지) — 기존 `WelcomeNotificationConsumer` 패턴.
- outbox 발행은 `OutboxEntry`(aggregateType/aggregateId/eventType/payload/createdAt) 저장까지만, 실제 Kafka 전송은 기존 `OutboxRelay`(`@Scheduled(fixedDelay=2000)`)가 담당 — KafkaTemplate 직접 사용 금지.
- 서비스 간 동기 호출은 게이트웨이 미경유 `RestClient` 직통(`devpath.<svc>.base-url` 프로퍼티, 기존 `RestNotificationPrefsClient`/`LearningClient` 참고). **ai-svc 포트 = `http://localhost:8084`**(gateway `AI_SVC_URI` 관례).
- 테스트: 실 Postgres(`localhost:5432/devpath`, docker `devpath-local-postgres-1`) + learning/notification은 shared jar Flyway가 classpath로 스키마 구성. ai-svc AI 클라이언트 테스트는 **Mock provider**(`devpath.retention.provider=mock`)로 계약 검증(실 LLM 호출 안 함).
- 머지 금지 — PR 생성까지만(컨트롤러/사용자 몫).

---

### Task 1: devpath-shared — UserStagnatedEvent + user_streak 마이그레이션

**Files:**
- Create: `devpath-shared/src/main/java/ai/devpath/shared/event/UserStagnatedEvent.java`
- Create: `devpath-shared/src/main/resources/db/migration/V202607031001__user_streak_stagnation_notified.sql`
- Test: `devpath-shared/src/test/java/ai/devpath/shared/event/UserStagnatedEventTest.java`

**Interfaces:**
- Consumes: `DomainEvent`(기존 인터페이스: `eventId()`/`occurredAt()`/`eventType()`).
- Produces: `UserStagnatedEvent` record(필드 순서·타입 정확히): `eventId: UUID`, `occurredAt: Instant`, `userId: long`, `lastActiveAt: Instant`, `daysInactive: int`, `currentLearningPathSummary: String`(nullable). 상수 `EVENT_TYPE = "progress.user.stagnated"`. Task 3(발행)·Task 4(구독)가 이 정확한 필드명·순서를 참조. `user_streak.stagnation_notified_at TIMESTAMPTZ`(nullable) — Task 3이 매핑.

- [ ] **Step 1: 실패 테스트 작성**

```java
package ai.devpath.shared.event;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class UserStagnatedEventTest {

  @Test
  void eventTypeAndFields() {
    Instant now = Instant.now();
    Instant lastActive = now.minusSeconds(3 * 86400);
    UserStagnatedEvent e = new UserStagnatedEvent(UUID.randomUUID(), now, 42L, lastActive, 3, "백엔드 스프링 트랙 (12주 과정)");

    assertEquals("progress.user.stagnated", e.eventType());
    assertEquals("progress.user.stagnated", UserStagnatedEvent.EVENT_TYPE);
    assertEquals(42L, e.userId());
    assertEquals(3, e.daysInactive());
    assertEquals(lastActive, e.lastActiveAt());
    assertEquals("백엔드 스프링 트랙 (12주 과정)", e.currentLearningPathSummary());
  }

  @Test
  void summaryMayBeNull() {
    UserStagnatedEvent e = new UserStagnatedEvent(UUID.randomUUID(), Instant.now(), 1L, Instant.now(), 3, null);
    assertNull(e.currentLearningPathSummary());
  }
}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.event.UserStagnatedEventTest"`
Expected: FAIL — `UserStagnatedEvent` 없어 컴파일 실패.

- [ ] **Step 3: UserStagnatedEvent 구현**

```java
package ai.devpath.shared.event;

import java.time.Instant;
import java.util.UUID;

/**
 * 3일 연속 미활동(정체) 도달 이벤트. learning-svc가 Transactional Outbox로 에피소드당 1회 발행한다.
 * 소비자: notification-svc {@code StagnationConsumer}(→ ai-svc 재참여 문구 → 푸시).
 * {@code currentLearningPathSummary}는 발행 측(learning-svc)이 조립한 현재 활성 학습경로 요약(없으면 null).
 */
public record UserStagnatedEvent(
		UUID eventId,
		Instant occurredAt,
		long userId,
		Instant lastActiveAt,
		int daysInactive,
		String currentLearningPathSummary
) implements DomainEvent {

	public static final String EVENT_TYPE = "progress.user.stagnated";

	@Override
	public String eventType() {
		return EVENT_TYPE;
	}
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd devpath-shared && ./gradlew test --tests "ai.devpath.shared.event.UserStagnatedEventTest"`
Expected: PASS (2 tests)

- [ ] **Step 5: 마이그레이션 작성**

파일 `devpath-shared/src/main/resources/db/migration/V202607031001__user_streak_stagnation_notified.sql`:

```sql
-- 정체(3일 미활동) 재참여 알림 재발행 방지 마커. owner: devpath-learning-svc.
-- 발행 시 now() 세팅, 유저 재활성 시 NULL 리셋 → 정체 에피소드당 정확히 1회 발행.
ALTER TABLE user_streak ADD COLUMN stagnation_notified_at TIMESTAMPTZ;
```

- [ ] **Step 6: 로컬 Flyway 검증**

Run: `cd devpath-shared && ./gradlew flywayMigrate` (또는 `./gradlew build`가 test에서 Flyway 적용)
Expected: 신규 마이그레이션 1건 적용 성공(또는 이미 적용 상태). 실패 시 `flywayInfo`로 원인 규명.

- [ ] **Step 7: 전체 빌드 + 커밋 + PR (main)**

Run: `cd devpath-shared && ./gradlew build`
Expected: BUILD SUCCESSFUL

```bash
cd devpath-shared
git fetch origin && git switch main && git pull --ff-only origin main
git switch -c feat/retention-build4-stagnation-event
git add src/main/java/ai/devpath/shared/event/UserStagnatedEvent.java \
        src/main/resources/db/migration/V202607031001__user_streak_stagnation_notified.sql \
        src/test/java/ai/devpath/shared/event/UserStagnatedEventTest.java
git commit -m "feat(shared): UserStagnatedEvent + user_streak.stagnation_notified_at

참여촉진배치 Build 4 — 정체 탐지 이벤트(학습경로 요약 포함) + 재발행 방지 마커 컬럼."
git push -u origin feat/retention-build4-stagnation-event
gh pr create --base main --title "feat(shared): 참여촉진배치 Build 4 정체 이벤트+마커" --body "UserStagnatedEvent(learning-svc→notification-svc) + user_streak.stagnation_notified_at 컬럼. 이 PR 머지+publish 이후에 learning/notification-svc가 의존 가능."
```

- [ ] **Step 8: CI 확인 후 머지·publish 확인**

Run: `gh pr checks <PR> -R DevPathAi/devpath-shared` → 통과 후 `gh pr merge <PR> -R DevPathAi/devpath-shared --merge` → `gh pr view <PR> --json state,mergedAt`로 MERGED 확인 → `gh run list -R DevPathAi/devpath-shared --branch main --limit 1`로 Publish 워크플로 성공 확인. jar 내용 grep으로 `UserStagnatedEvent.class` 포함 확인.

---

### Task 2: devpath-ai-svc — retention 모듈 (POST /ai/re-engagement)

**배경**: mentor/review/community-seed와 동일한 완결 패턴(인터페이스 + provider별 구현 + 전용 Config + Controller + PromptBuilder + 예외)을 `ai/devpath/aigw/retention/`에 신설. 응답은 **non-streaming 단일 문구**라 review 도메인(`ClaudeAiReviewClient`)을 미러링한다. 이 Task는 shared 신규 이벤트를 사용하지 않으므로(REST 엔드포인트만 노출) Task 1 publish와 무관하게 진행 가능. **Ollama provider는 이번 스코프에서 제외**(Mock=test·fallback, Claude=prod로 충분; 후속에 `OllamaReEngagementClient`를 기존 `OllamaAiReviewClient` 패턴으로 추가 가능 — provider 프로퍼티가 이미 3-way 확장 가능).

**Files:**
- Create: `devpath-ai-svc/src/main/java/ai/devpath/aigw/retention/ReEngagementInput.java`
- Create: `devpath-ai-svc/src/main/java/ai/devpath/aigw/retention/ReEngagementResult.java`
- Create: `devpath-ai-svc/src/main/java/ai/devpath/aigw/retention/ReEngagementSuggestionClient.java`
- Create: `devpath-ai-svc/src/main/java/ai/devpath/aigw/retention/MockReEngagementClient.java`
- Create: `devpath-ai-svc/src/main/java/ai/devpath/aigw/retention/ReEngagementPromptBuilder.java`
- Create: `devpath-ai-svc/src/main/java/ai/devpath/aigw/retention/RetentionClaudeClientConfig.java`
- Create: `devpath-ai-svc/src/main/java/ai/devpath/aigw/retention/ClaudeReEngagementClient.java`
- Create: `devpath-ai-svc/src/main/java/ai/devpath/aigw/retention/ReEngagementController.java`
- Create: `devpath-ai-svc/src/main/java/ai/devpath/aigw/retention/ReEngagementGenerationException.java`
- Modify: `devpath-ai-svc/src/main/resources/application.yml`
- Test: `devpath-ai-svc/src/test/java/ai/devpath/aigw/retention/ReEngagementControllerTest.java`

**Interfaces:**
- Consumes: 없음(외부 계약은 HTTP). Anthropic SDK(기존 의존성).
- Produces: `POST /ai/re-engagement` — request `ReEngagementInput(long userId, Instant lastActiveAt, int daysInactive, String currentLearningPathSummary)`, response `ReEngagementResult(String message)`. Task 4(notification-svc)가 이 정확한 shape로 호출. `ReEngagementSuggestionClient.suggest(ReEngagementInput): String` + `providerName(): String`.

- [ ] **Step 1: 브랜치 준비**

```bash
cd devpath-ai-svc
git fetch origin && git switch develop && git pull --ff-only origin develop
git switch -c feat/retention-build4-reengagement
```

- [ ] **Step 2: 실패하는 컨트롤러 테스트 작성 (Mock provider)**

```java
package ai.devpath.aigw.retention;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@TestPropertySource(properties = {"devpath.retention.provider=mock", "devpath.retention.enabled=true"})
class ReEngagementControllerTest {

  @Autowired MockMvc mvc;

  @Test
  void returnsNonEmptyMessageForStagnatedUser() throws Exception {
    mvc.perform(post("/ai/re-engagement")
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"userId\":42,\"lastActiveAt\":\"2026-06-30T00:00:00Z\",\"daysInactive\":3,\"currentLearningPathSummary\":\"백엔드 스프링 트랙 (12주 과정)\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.message").isNotEmpty());
  }

  @Test
  void handlesNullSummary() throws Exception {
    mvc.perform(post("/ai/re-engagement")
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"userId\":42,\"lastActiveAt\":\"2026-06-30T00:00:00Z\",\"daysInactive\":3,\"currentLearningPathSummary\":null}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.message").isNotEmpty());
  }
}
```

（이 레포에 MockMvc/webmvc-test 의존성이 있는지 `build.gradle.kts` 확인 — 기존 `MentorController`/`ReviewController` 테스트가 있으므로 있을 것이나, 없으면 `testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")` 추가.）

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd devpath-ai-svc && ./gradlew test --tests "ai.devpath.aigw.retention.ReEngagementControllerTest"`
Expected: FAIL — retention 클래스들이 없어 컴파일 실패.

- [ ] **Step 4: DTO + 인터페이스 구현**

`ReEngagementInput.java`:
```java
package ai.devpath.aigw.retention;

import java.time.Instant;

public record ReEngagementInput(long userId, Instant lastActiveAt, int daysInactive, String currentLearningPathSummary) {
}
```

`ReEngagementResult.java`:
```java
package ai.devpath.aigw.retention;

public record ReEngagementResult(String message) {
}
```

`ReEngagementSuggestionClient.java`:
```java
package ai.devpath.aigw.retention;

/** 재참여 문구 생성 추상화. provider 프로퍼티(devpath.retention.provider)로 구현 선택. */
public interface ReEngagementSuggestionClient {
	String suggest(ReEngagementInput input);
	String providerName();
}
```

- [ ] **Step 5: MockReEngagementClient 구현 (기본 provider)**

```java
package ai.devpath.aigw.retention;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/** 고정 문구(테스트·로컬·LLM 실패 폴백 공용). 요약이 있으면 살짝 개인화. */
@Component
@ConditionalOnProperty(name = "devpath.retention.provider", havingValue = "mock", matchIfMissing = true)
public class MockReEngagementClient implements ReEngagementSuggestionClient {

	@Override
	public String suggest(ReEngagementInput input) {
		if (input.currentLearningPathSummary() != null && !input.currentLearningPathSummary().isBlank()) {
			return "오랜만이에요! " + input.currentLearningPathSummary() + " 학습을 이어가 볼까요? 오늘 한 걸음이면 충분해요.";
		}
		return "오랜만이에요! 다시 학습을 시작해볼까요? 오늘 한 걸음이면 충분해요.";
	}

	@Override
	public String providerName() { return "MOCK"; }
}
```

- [ ] **Step 6: ReEngagementController 구현 + 테스트 통과 확인**

`ReEngagementPromptBuilder.java`:
```java
package ai.devpath.aigw.retention;

import org.springframework.stereotype.Component;

@Component
public class ReEngagementPromptBuilder {

	public String systemPrompt() {
		return "너는 학습 플랫폼의 따뜻한 학습 코치다. 3일간 학습하지 않은 사용자에게 부담 없이 다시 시작하도록 격려하는 "
				+ "1~2문장의 짧은 한국어 알림 문구를 만든다. 죄책감을 주지 말고, 구체적이고 실행 가능한 작은 다음 걸음을 제안한다.";
	}

	public String userContent(ReEngagementInput input) {
		String summary = (input.currentLearningPathSummary() == null || input.currentLearningPathSummary().isBlank())
				? "(현재 활성 학습경로 정보 없음)" : input.currentLearningPathSummary();
		return "미활동 일수: " + input.daysInactive() + "일\n현재 학습경로: " + summary
				+ "\n\n위 맥락에 맞는 재참여 알림 문구 1~2문장만 출력해라(다른 설명 없이).";
	}
}
```

`ReEngagementGenerationException.java`:
```java
package ai.devpath.aigw.retention;

public class ReEngagementGenerationException extends RuntimeException {
	public ReEngagementGenerationException(String message, Throwable cause) { super(message, cause); }
}
```

`ReEngagementController.java`:
```java
package ai.devpath.aigw.retention;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 내부 서비스 간 호출(notification-svc → ai-svc). /ai/** 는 SecurityConfig에서 permitAll(무인증 내부 경로). */
@RestController
@RequestMapping("/ai")
public class ReEngagementController {

	private final ReEngagementSuggestionClient client;
	private final boolean enabled;

	public ReEngagementController(ReEngagementSuggestionClient client,
			@Value("${devpath.retention.enabled:true}") boolean enabled) {
		this.client = client;
		this.enabled = enabled;
	}

	@PostMapping("/re-engagement")
	public ReEngagementResult reEngage(@RequestBody ReEngagementInput input) {
		if (!enabled) {
			// kill-switch: 비활성 시에도 호출측이 폴백을 쓰도록 예외 대신 빈 문자열 반환하지 않고,
			// 호출측(StagnationConsumer)이 폴백 문구를 쓰게 명확히 실패시킨다.
			throw new ReEngagementGenerationException("re-engagement disabled", null);
		}
		return new ReEngagementResult(client.suggest(input));
	}
}
```

`application.yml`에 provider 프로퍼티 추가(기존 `devpath:` 블록의 review/mentor 옆):
```yaml
  retention:
    provider: ${RETENTION_PROVIDER:mock}
    claude-model: ${RETENTION_CLAUDE_MODEL:claude-sonnet-4-6}
    enabled: ${RETENTION_ENABLED:true}
```

Run: `cd devpath-ai-svc && ./gradlew test --tests "ai.devpath.aigw.retention.ReEngagementControllerTest"`
Expected: PASS (2 tests) — Mock provider가 기본(matchIfMissing=true)이라 실 LLM 없이 통과.

- [ ] **Step 7: ClaudeReEngagementClient + Config 구현 (prod provider, 리뷰 도메인 미러)**

`RetentionClaudeClientConfig.java`:
```java
package ai.devpath.aigw.retention;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/** mentor/review와 동일 타입(AnthropicClient) 빈 충돌 회피 위해 빈 이름 분리(retentionAnthropicClient). */
@Configuration
@ConditionalOnProperty(name = "devpath.retention.provider", havingValue = "claude")
public class RetentionClaudeClientConfig {
	@Bean(name = "retentionAnthropicClient")
	public AnthropicClient retentionAnthropicClient() {
		return AnthropicOkHttpClient.fromEnv(); // ANTHROPIC_API_KEY
	}
}
```

`ClaudeReEngagementClient.java`(non-streaming, `ClaudeAiReviewClient` 미러 — 단, 응답은 자유 텍스트라 `outputConfig` 없이 텍스트 블록 추출):
```java
package ai.devpath.aigw.retention;

import com.anthropic.client.AnthropicClient;
import com.anthropic.errors.AnthropicException;
import com.anthropic.models.messages.MessageCreateParams;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "devpath.retention.provider", havingValue = "claude")
public class ClaudeReEngagementClient implements ReEngagementSuggestionClient {

	private final AnthropicClient client;
	private final String model;
	private final ReEngagementPromptBuilder prompts;

	public ClaudeReEngagementClient(
			@Qualifier("retentionAnthropicClient") AnthropicClient client,
			@Value("${devpath.retention.claude-model:claude-sonnet-4-6}") String model,
			ReEngagementPromptBuilder prompts) {
		this.client = client;
		this.model = model;
		this.prompts = prompts;
	}

	@Override
	public String suggest(ReEngagementInput input) {
		MessageCreateParams params = MessageCreateParams.builder()
				.model(model)
				.maxTokens(300L)
				.system(prompts.systemPrompt())
				.addUserMessage(prompts.userContent(input))
				.build();
		try {
			return client.messages().create(params).content().stream()
					.flatMap(cb -> cb.text().stream())
					.map(typed -> typed.text())
					.findFirst()
					.orElseThrow(() -> new ReEngagementGenerationException("Claude 응답이 비어 있습니다", null));
		} catch (AnthropicException e) {
			throw new ReEngagementGenerationException("Claude 재참여 문구 생성 실패", e);
		}
	}

	@Override
	public String providerName() { return "CLAUDE"; }
}
```

（`AnthropicOkHttpClient` import 경로는 기존 `MentorClaudeClientConfig`와 동일 — `com.anthropic.client.okhttp.AnthropicOkHttpClient`. 실제 파일에서 기존 import를 대조해 정확히 맞춰라.）

- [ ] **Step 8: 전체 빌드 + 커밋 + PR**

Run: `cd devpath-ai-svc && ./gradlew build`
Expected: BUILD SUCCESSFUL(Mock provider 기본, Claude 빈은 provider=claude일 때만 로드되므로 테스트 컨텍스트에 영향 없음).

```bash
cd devpath-ai-svc
git add src/main/java/ai/devpath/aigw/retention/ src/main/resources/application.yml \
        src/test/java/ai/devpath/aigw/retention/
git commit -m "feat(retention): POST /ai/re-engagement 재참여 문구 생성(Mock/Claude)

참여촉진배치 Build 4 — review 도메인 미러(non-streaming). provider=mock 기본,
claude는 retentionAnthropicClient 빈 분리. Ollama는 후속."
git push -u origin feat/retention-build4-reengagement
gh pr create --base develop --title "feat(retention): 재참여 문구 API POST /ai/re-engagement (Build 4)" --body "정체 유저용 재참여 문구 생성. Mock(기본)+Claude provider. notification-svc StagnationConsumer가 호출."
```

- [ ] **Step 9: CI 확인** (`gh pr checks <PR> -R DevPathAi/devpath-ai-svc` 통과 확인, 머지 금지)

---

### Task 3: devpath-learning-svc — 정체 탐지 (StreakRolloverService 확장)

**배경**: 신규 스케줄러 없이 기존 `StreakRolloverService.rollover()`의 "어제 활동 없음"(`else`) 분기를 확장. `last_active_date` 기준 `daysInactive`를 계산해 정확히 3일째이고 마커가 null이면 `UserStagnatedEvent` 발행(요약 포함) + 마커 세팅. 활동 시 마커 리셋. **Task 1 publish 이후 진행**(새 shared SNAPSHOT의 `UserStagnatedEvent` 필요).

**Files:**
- Modify: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/UserStreak.java` (필드 `stagnationNotifiedAt` 추가)
- Create: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/ActivePathSummaryReader.java`
- Modify: `devpath-learning-svc/src/main/java/ai/devpath/learning/progress/StreakRolloverService.java`
- Test: `devpath-learning-svc/src/test/java/ai/devpath/learning/progress/StreakRolloverStagnationTest.java`

**Interfaces:**
- Consumes: Task 1 `UserStagnatedEvent`(shared, 새 SNAPSHOT), `user_streak.stagnation_notified_at`. 기존 `OutboxRepository`/`OutboxEntry`, `UserStreakRepository`, `learning_paths` 테이블(track/total_weeks/status/generated_at).
- Produces: `ActivePathSummaryReader.summarize(long userId): Optional<String>`(활성 경로 요약, 없으면 empty). `StreakRolloverService.rollover`가 정체 시 `UserStagnatedEvent`를 outbox 발행(eventType `progress.user.stagnated`, aggregateId=userId) — Task 4가 구독.

- [ ] **Step 1: 브랜치 준비 + 새 SNAPSHOT 수신**

```bash
cd devpath-learning-svc
git fetch origin && git switch develop && git pull --ff-only origin develop
git switch -c feat/retention-build4-stagnation-detect
./gradlew compileJava --refresh-dependencies
```
（`unzip -l ~/.gradle/.../devpath-shared-*.jar | grep UserStagnatedEvent` 로 새 SNAPSHOT에 이벤트 클래스 포함 확인 — mtime 아님.）

- [ ] **Step 2: UserStreak 엔티티에 마커 필드 추가**

`UserStreak.java` — `updatedAt` 필드/게터 아래에 추가:

old_string:
```java
	@Column(name = "updated_at")
	private Instant updatedAt;

	public Long getUserId() { return userId; }
```
new_string:
```java
	@Column(name = "updated_at")
	private Instant updatedAt;

	@Column(name = "stagnation_notified_at")
	private Instant stagnationNotifiedAt;

	public Long getUserId() { return userId; }
```
그리고 getter/setter 블록 끝(`setUpdatedAt` 아래)에:

old_string:
```java
	public Instant getUpdatedAt() { return updatedAt; }
	public void setUpdatedAt(Instant v) { this.updatedAt = v; }
}
```
new_string:
```java
	public Instant getUpdatedAt() { return updatedAt; }
	public void setUpdatedAt(Instant v) { this.updatedAt = v; }
	public Instant getStagnationNotifiedAt() { return stagnationNotifiedAt; }
	public void setStagnationNotifiedAt(Instant v) { this.stagnationNotifiedAt = v; }
}
```

- [ ] **Step 3: ActivePathSummaryReader 구현**

`PathWeeklyTaskRepository`/`SandboxActivityLogRepository`와 동일한 `NamedParameterJdbcTemplate` 스타일.

```java
package ai.devpath.learning.progress;

import java.util.Map;
import java.util.Optional;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

/** 현재 활성 학습경로의 짧은 요약 문자열(재참여 문구용). 없으면 empty. */
@Repository
public class ActivePathSummaryReader {
	private final NamedParameterJdbcTemplate jdbc;

	public ActivePathSummaryReader(NamedParameterJdbcTemplate jdbc) {
		this.jdbc = jdbc;
	}

	public Optional<String> summarize(long userId) {
		var sql = """
				SELECT track, total_weeks FROM learning_paths
				WHERE user_id = :userId AND status = 'ACTIVE'
				ORDER BY generated_at DESC LIMIT 1
				""";
		return jdbc.query(sql, Map.of("userId", userId), (rs, n) ->
				rs.getString("track") + " 트랙 (" + rs.getInt("total_weeks") + "주 과정)")
				.stream().findFirst();
	}
}
```

- [ ] **Step 4: 실패하는 정체 탐지 테스트 작성**

```java
package ai.devpath.learning.progress;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import ai.devpath.learning.outbox.OutboxRepository;
import ai.devpath.learning.path.PathWeeklyTaskRepository;
import java.time.LocalDate;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class StreakRolloverStagnationTest {

  @Autowired UserStreakRepository streaks;
  @Autowired OutboxRepository outbox;
  @Autowired SandboxActivityLogRepository sandboxActivity;

  private StreakRolloverService serviceNoActivity() {
    PathWeeklyTaskRepository tasks = mock(PathWeeklyTaskRepository.class);
    when(tasks.hasCompletedTaskOnDate(any(Long.class), any(LocalDate.class))).thenReturn(false);
    ActivePathSummaryReader summary = mock(ActivePathSummaryReader.class);
    when(summary.summarize(any(Long.class))).thenReturn(Optional.of("백엔드 스프링 트랙 (12주 과정)"));
    // sandboxActivity도 활동 없음이어야 하므로 실제 빈 대신 mock 사용
    SandboxActivityLogRepository sandbox = mock(SandboxActivityLogRepository.class);
    when(sandbox.hasActivityOnDate(any(Long.class), any(LocalDate.class))).thenReturn(false);
    return new StreakRolloverService(streaks, tasks, sandbox, outbox, summary);
  }

  private UserStreak seed(long userId, LocalDate lastActive, java.time.Instant notified) {
    UserStreak s = new UserStreak();
    s.setUserId(userId);
    s.setCurrentDays(0);
    s.setLastActiveDate(lastActive);
    s.setStagnationNotifiedAt(notified);
    return streaks.save(s);
  }

  @Test
  void publishesStagnatedEventExactlyOnThirdInactiveDay() {
    long userId = 770001L;
    // 오늘 = lastActive + 4 → yesterday = lastActive + 3 → daysInactive = 3
    LocalDate lastActive = LocalDate.of(2026, 6, 30);
    seed(userId, lastActive, null);
    long before = outbox.count();

    serviceNoActivity().rollover(userId, LocalDate.of(2026, 7, 4)); // yesterday=7/3, between(6/30,7/3)=3

    assertThat(outbox.count()).isEqualTo(before + 1);
    UserStreak after = streaks.findById(userId).orElseThrow();
    assertThat(after.getStagnationNotifiedAt()).isNotNull();
  }

  @Test
  void doesNotPublishOnSecondOrFourthDay() {
    long userId = 770002L;
    seed(userId, LocalDate.of(2026, 6, 30), null);
    long before = outbox.count();
    serviceNoActivity().rollover(userId, LocalDate.of(2026, 7, 3)); // daysInactive=2
    assertThat(outbox.count()).isEqualTo(before);
    serviceNoActivity().rollover(userId, LocalDate.of(2026, 7, 5)); // daysInactive=4
    assertThat(outbox.count()).isEqualTo(before);
  }

  @Test
  void doesNotRepublishWhenAlreadyNotified() {
    long userId = 770003L;
    seed(userId, LocalDate.of(2026, 6, 30), java.time.Instant.now()); // 이미 통지됨
    long before = outbox.count();
    serviceNoActivity().rollover(userId, LocalDate.of(2026, 7, 4)); // daysInactive=3이나 마커 존재
    assertThat(outbox.count()).isEqualTo(before);
  }
}
```

- [ ] **Step 5: 테스트 실패 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.progress.StreakRolloverStagnationTest"`
Expected: FAIL — `StreakRolloverService` 생성자에 `ActivePathSummaryReader` 파라미터가 없고 정체 로직도 없어 컴파일/단언 실패.

- [ ] **Step 6: StreakRolloverService 확장**

`StreakRolloverService.java`:

old_string(생성자 + 필드):
```java
  private final UserStreakRepository streaks;
  private final PathWeeklyTaskRepository weeklyTasks;
  private final SandboxActivityLogRepository sandboxActivity;
  private final OutboxRepository outbox;
  private final JsonMapper jsonMapper = new JsonMapper();

  public StreakRolloverService(UserStreakRepository streaks, PathWeeklyTaskRepository weeklyTasks,
      SandboxActivityLogRepository sandboxActivity, OutboxRepository outbox) {
    this.streaks = streaks;
    this.weeklyTasks = weeklyTasks;
    this.sandboxActivity = sandboxActivity;
    this.outbox = outbox;
  }
```
new_string:
```java
  private static final int STAGNATION_DAYS = 3;

  private final UserStreakRepository streaks;
  private final PathWeeklyTaskRepository weeklyTasks;
  private final SandboxActivityLogRepository sandboxActivity;
  private final OutboxRepository outbox;
  private final ActivePathSummaryReader pathSummary;
  private final JsonMapper jsonMapper = new JsonMapper();

  public StreakRolloverService(UserStreakRepository streaks, PathWeeklyTaskRepository weeklyTasks,
      SandboxActivityLogRepository sandboxActivity, OutboxRepository outbox,
      ActivePathSummaryReader pathSummary) {
    this.streaks = streaks;
    this.weeklyTasks = weeklyTasks;
    this.sandboxActivity = sandboxActivity;
    this.outbox = outbox;
    this.pathSummary = pathSummary;
  }
```

hadActivity 분기에 마커 리셋 추가 — old_string:
```java
    if (hadActivity) {
      int newCurrent = streak.getCurrentDays() + 1;
      streak.setCurrentDays(newCurrent);
      streak.setLongestDays(Math.max(streak.getLongestDays(), newCurrent));
      streak.setLastActiveDate(yesterday);
      streak.setUpdatedAt(Instant.now());
      streaks.save(streak);
      if (MILESTONES.contains(newCurrent)) {
        publishStreakReached(userId, newCurrent);
      }
    } else {
      streak.setCurrentDays(0);
      streak.setUpdatedAt(Instant.now());
      streaks.save(streak);
    }
```
new_string:
```java
    if (hadActivity) {
      int newCurrent = streak.getCurrentDays() + 1;
      streak.setCurrentDays(newCurrent);
      streak.setLongestDays(Math.max(streak.getLongestDays(), newCurrent));
      streak.setLastActiveDate(yesterday);
      streak.setStagnationNotifiedAt(null); // 재활성 → 다음 정체 에피소드 재통지 허용
      streak.setUpdatedAt(Instant.now());
      streaks.save(streak);
      if (MILESTONES.contains(newCurrent)) {
        publishStreakReached(userId, newCurrent);
      }
    } else {
      streak.setCurrentDays(0);
      maybePublishStagnation(streak, yesterday);
      streak.setUpdatedAt(Instant.now());
      streaks.save(streak);
    }
```

메서드 추가(`publishStreakReached` 아래):
```java
  /** last_active_date 기준 미활동 정확히 3일째이고 아직 통지 전이면 UserStagnatedEvent 발행 + 마커 세팅. */
  private void maybePublishStagnation(UserStreak streak, java.time.LocalDate yesterday) {
    java.time.LocalDate lastActive = streak.getLastActiveDate();
    if (lastActive == null) return; // 한 번도 활동 없던 유저는 정체 대상 아님(재참여가 아니라 최초 참여)
    if (streak.getStagnationNotifiedAt() != null) return; // 이미 이 에피소드에 통지함
    long daysInactive = java.time.temporal.ChronoUnit.DAYS.between(lastActive, yesterday);
    if (daysInactive != STAGNATION_DAYS) return;

    long userId = streak.getUserId();
    java.time.Instant lastActiveAt = lastActive.atStartOfDay(java.time.ZoneOffset.UTC).toInstant();
    String summary = pathSummary.summarize(userId).orElse(null);
    var event = new ai.devpath.shared.event.UserStagnatedEvent(
        UUID.randomUUID(), Instant.now(), userId, lastActiveAt, (int) daysInactive, summary);
    OutboxEntry entry = new OutboxEntry();
    entry.setAggregateType("user_streak");
    entry.setAggregateId(String.valueOf(userId));
    entry.setEventType(ai.devpath.shared.event.UserStagnatedEvent.EVENT_TYPE);
    entry.setPayload(jsonMapper.writeValueAsString(event));
    entry.setCreatedAt(Instant.now());
    outbox.save(entry);
    streak.setStagnationNotifiedAt(Instant.now());
  }
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `cd devpath-learning-svc && ./gradlew test --tests "ai.devpath.learning.progress.StreakRolloverStagnationTest"`
Expected: PASS (3 tests). 기존 `StreakRolloverServiceTest`(Build 2)도 생성자 시그니처 변경 영향 — **해당 테스트의 `new StreakRolloverService(...)` 호출부에 `ActivePathSummaryReader` 인자를 추가**해야 컴파일된다(mock 주입). 그 테스트도 함께 수정 후 `./gradlew test --tests "*StreakRolloverServiceTest"`로 회귀 확인.

- [ ] **Step 8: 전체 빌드 + 커밋 + PR**

Run: `cd devpath-learning-svc && ./gradlew build`
Expected: BUILD SUCCESSFUL

```bash
cd devpath-learning-svc
git add src/main/java/ai/devpath/learning/progress/UserStreak.java \
        src/main/java/ai/devpath/learning/progress/ActivePathSummaryReader.java \
        src/main/java/ai/devpath/learning/progress/StreakRolloverService.java \
        src/test/java/ai/devpath/learning/progress/
git commit -m "feat(progress): 3일 미활동 정체 탐지 → UserStagnatedEvent 발행

참여촉진배치 Build 4 — 기존 rollover else 분기 확장. last_active_date 기준
정확히 3일째 1회 발행(stagnation_notified_at 마커), 재활성 시 리셋. 경로 요약 포함."
git push -u origin feat/retention-build4-stagnation-detect
gh pr create --base develop --title "feat(progress): 정체 탐지 + UserStagnatedEvent (Build 4)" --body "3일 미활동 시 UserStagnatedEvent 발행(재발행 방지 마커). shared #<Task1 PR> 머지+publish 선행 필요."
```

- [ ] **Step 9: CI 확인** (머지 금지)

---

### Task 4: devpath-notification-svc — StagnationConsumer + RestReEngagementClient

**배경**: `UserStagnatedEvent` 구독 → ai-svc `POST /ai/re-engagement` 호출(실패 시 폴백 문구) → 기존 `PushSender`(Build 3)로 전달. **Task 1 publish 이후 진행**(이벤트 역직렬화). ai-svc 엔드포인트 계약은 Task 2(`{userId, lastActiveAt, daysInactive, currentLearningPathSummary}` → `{message}`).

**Files:**
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/retention/ReEngagementClient.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/retention/RestReEngagementClient.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/retention/ReEngagementUnavailableException.java`
- Create: `devpath-notification-svc/src/main/java/ai/devpath/notification/retention/StagnationConsumer.java`
- Modify: `devpath-notification-svc/src/main/resources/application.yml`
- Test: `devpath-notification-svc/src/test/java/ai/devpath/notification/retention/StagnationConsumerTest.java`

**Interfaces:**
- Consumes: Task 1 `UserStagnatedEvent`(shared, 새 SNAPSHOT), Task 2 `POST /ai/re-engagement`, 기존 `PushSender`(Build 3, `send(long,String,String,String)`).
- Produces: `ReEngagementClient.suggest(long userId, Instant lastActiveAt, int daysInactive, String summary): String`. `StagnationConsumer`(@KafkaListener `progress.user.stagnated`, groupId `devpath-notification`).

- [ ] **Step 1: 브랜치 준비 + 새 SNAPSHOT 수신**

```bash
cd devpath-notification-svc
git fetch origin && git switch develop && git pull --ff-only origin develop
git switch -c feat/retention-build4-stagnation-consumer
./gradlew compileJava --refresh-dependencies
```

- [ ] **Step 2: ReEngagementClient 인터페이스 + REST 구현 + 예외**

`ReEngagementClient.java`:
```java
package ai.devpath.notification.retention;

import java.time.Instant;

public interface ReEngagementClient {
	/** ai-svc에 재참여 문구 생성 요청. 실패 시 ReEngagementUnavailableException. */
	String suggest(long userId, Instant lastActiveAt, int daysInactive, String currentLearningPathSummary);
}
```

`ReEngagementUnavailableException.java`:
```java
package ai.devpath.notification.retention;

public class ReEngagementUnavailableException extends RuntimeException {
	public ReEngagementUnavailableException(String message, Throwable cause) { super(message, cause); }
}
```

`RestReEngagementClient.java`(`RestNotificationPrefsClient`(learning-svc) 패턴 미러):
```java
package ai.devpath.notification.retention;

import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class RestReEngagementClient implements ReEngagementClient {

	private final RestClient restClient;

	public RestReEngagementClient(
			@Value("${devpath.ai-svc.base-url:http://localhost:8084}") String baseUrl,
			@Value("${devpath.ai-svc.timeout:PT5S}") Duration timeout) {
		var factory = new SimpleClientHttpRequestFactory();
		factory.setConnectTimeout(timeout);
		factory.setReadTimeout(timeout);
		this.restClient = RestClient.builder().baseUrl(baseUrl).requestFactory(factory).build();
	}

	@Override
	public String suggest(long userId, Instant lastActiveAt, int daysInactive, String currentLearningPathSummary) {
		try {
			ReEngagementResponse res = restClient.post()
					.uri("/ai/re-engagement")
					.body(Map.of(
							"userId", userId,
							"lastActiveAt", lastActiveAt.toString(),
							"daysInactive", daysInactive,
							"currentLearningPathSummary", currentLearningPathSummary == null ? "" : currentLearningPathSummary))
					.retrieve()
					.body(ReEngagementResponse.class);
			if (res == null || res.message() == null || res.message().isBlank()) {
				throw new ReEngagementUnavailableException("ai-svc 응답이 비어 있음", null);
			}
			return res.message();
		} catch (RestClientException e) {
			throw new ReEngagementUnavailableException("ai-svc re-engagement 호출 실패", e);
		}
	}

	record ReEngagementResponse(String message) {}
}
```

- [ ] **Step 3: 실패하는 StagnationConsumer 단위 테스트 작성**

```java
package ai.devpath.notification.retention;

import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import ai.devpath.notification.push.PushSender;
import ai.devpath.shared.event.UserStagnatedEvent;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

/** 순수 단위테스트(Spring/DB 불요). 정체 이벤트 → ai 문구/폴백 → PushSender 전달. */
class StagnationConsumerTest {

  private final JsonMapper jsonMapper = new JsonMapper();

  private String payload(long userId) {
    return jsonMapper.writeValueAsString(new UserStagnatedEvent(
        UUID.randomUUID(), Instant.now(), userId, Instant.now().minusSeconds(3 * 86400), 3, "백엔드 스프링 트랙 (12주 과정)"));
  }

  @Test
  void usesAiMessageWhenAvailable() {
    ReEngagementClient ai = mock(ReEngagementClient.class);
    when(ai.suggest(anyLong(), any(), anyInt(), any())).thenReturn("AI 맞춤 문구");
    PushSender push = mock(PushSender.class);
    StagnationConsumer c = new StagnationConsumer(ai, push, jsonMapper);

    c.onUserStagnated(payload(555L));

    verify(push).send(eq(555L), eq("RE_ENGAGEMENT"), any(), eq("AI 맞춤 문구"));
  }

  @Test
  void fallsBackWhenAiFails() {
    ReEngagementClient ai = mock(ReEngagementClient.class);
    when(ai.suggest(anyLong(), any(), anyInt(), any()))
        .thenThrow(new ReEngagementUnavailableException("down", null));
    PushSender push = mock(PushSender.class);
    StagnationConsumer c = new StagnationConsumer(ai, push, jsonMapper);

    c.onUserStagnated(payload(556L));

    // 폴백 문구로라도 반드시 발송(전체 알림이 막히면 안 됨 — 스펙 §에러 처리)
    verify(push).send(eq(556L), eq("RE_ENGAGEMENT"), any(), any());
  }

  @Test
  void skipsPoisonPayloadWithoutThrowing() {
    StagnationConsumer c = new StagnationConsumer(mock(ReEngagementClient.class), mock(PushSender.class), jsonMapper);
    c.onUserStagnated("{ not valid json"); // 예외 없이 skip
  }
}
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `cd devpath-notification-svc && ./gradlew test --tests "ai.devpath.notification.retention.StagnationConsumerTest"`
Expected: FAIL — `StagnationConsumer` 없어 컴파일 실패.

- [ ] **Step 5: StagnationConsumer 구현**

```java
package ai.devpath.notification.retention;

import ai.devpath.notification.push.PushSender;
import ai.devpath.shared.event.UserStagnatedEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

/** progress.user.stagnated 구독 → ai-svc 재참여 문구(실패 시 폴백) → PushSender 전달. */
@Component
public class StagnationConsumer {

	private static final Logger log = LoggerFactory.getLogger(StagnationConsumer.class);
	private static final String TYPE = "RE_ENGAGEMENT";
	private static final String TITLE = "다시 시작해볼까요?";
	private static final String FALLBACK = "오랜만이에요! 다시 학습을 시작해볼까요? 오늘 한 걸음이면 충분해요.";

	private final ReEngagementClient reEngagement;
	private final PushSender pushSender;
	private final JsonMapper jsonMapper;

	public StagnationConsumer(ReEngagementClient reEngagement, PushSender pushSender, JsonMapper jsonMapper) {
		this.reEngagement = reEngagement;
		this.pushSender = pushSender;
		this.jsonMapper = jsonMapper;
	}

	@KafkaListener(topics = UserStagnatedEvent.EVENT_TYPE, groupId = "devpath-notification")
	public void onUserStagnated(String payload) {
		UserStagnatedEvent event;
		try {
			event = jsonMapper.readValue(payload, UserStagnatedEvent.class);
		} catch (Exception e) {
			log.warn("UserStagnatedEvent 역직렬화 실패 — skip: {}", payload, e);
			return; // poison 무한재시도 방지
		}
		String message;
		try {
			message = reEngagement.suggest(event.userId(), event.lastActiveAt(),
					event.daysInactive(), event.currentLearningPathSummary());
		} catch (ReEngagementUnavailableException e) {
			log.warn("ai-svc 재참여 문구 실패 — 폴백 문구 사용 userId={}", event.userId(), e);
			message = FALLBACK; // 그레이스풀 디그레이드(스펙 §에러 처리)
		}
		pushSender.send(event.userId(), TYPE, TITLE, message);
	}
}
```

- [ ] **Step 6: application.yml에 ai-svc 프로퍼티 추가**

`devpath:` 블록에 추가:
```yaml
  ai-svc:
    base-url: ${AI_SVC_URI:http://localhost:8084}
    timeout: ${AI_SVC_TIMEOUT:PT5S}
```

- [ ] **Step 7: 테스트 통과 확인 + 전체 빌드**

Run: `cd devpath-notification-svc && ./gradlew test --tests "ai.devpath.notification.retention.StagnationConsumerTest"`
Expected: PASS (3 tests)

Run: `cd devpath-notification-svc && ./gradlew build`
Expected: BUILD SUCCESSFUL(전체 스위트 회귀 없음 — 새 @KafkaListener는 실 브로커 없이도 컨텍스트 기동에 영향 없음, 기존 `WelcomeNotificationConsumer`와 동일).

- [ ] **Step 8: 커밋 + PR**

```bash
cd devpath-notification-svc
git add src/main/java/ai/devpath/notification/retention/ src/main/resources/application.yml \
        src/test/java/ai/devpath/notification/retention/
git commit -m "feat(retention): StagnationConsumer → ai 재참여 문구 → 푸시

참여촉진배치 Build 4 — progress.user.stagnated 구독, ai-svc /ai/re-engagement
동기 호출(실패 시 폴백 문구), 기존 PushSender로 전달."
git push -u origin feat/retention-build4-stagnation-consumer
gh pr create --base develop --title "feat(retention): 정체 이벤트 구독 + 재참여 푸시 (Build 4)" --body "UserStagnatedEvent 구독 → ai-svc 재참여 문구(실패 시 폴백) → PushSender. shared #<Task1 PR>·ai-svc #<Task2 PR> 선행."
```

- [ ] **Step 9: CI 확인** (머지 금지)

---

## Self-Review (작성자 점검)

**1. 스펙 커버리지:**
- 스펙 §"learning-svc progress: 어제 활동 없음 → last_active_date 기준 미활동 정확히 3일째에 UserStagnatedEvent 발행(재발행 방지)" → Task 3 ✅ (`stagnation_notified_at` 마커).
- 스펙 §"ai-svc retention: POST /ai/re-engagement, ReEngagementSuggestionClient(Claude/Ollama/Mock)" → Task 2 ✅ (Mock+Claude; **Ollama는 명시적 후속** — 아래 결정).
- 스펙 §"notification-svc StagnationConsumer: 구독 → ai POST /ai/re-engagement 동기 호출(실패 시 폴백) → 푸시" → Task 4 ✅.
- 스펙 §"이벤트 계약 UserStagnatedEvent" → Task 1 ✅ (+ `currentLearningPathSummary` 확장, 사용자 결정).

**2. 결정/스코프 노트:**
- **재발행 방지 = `stagnation_notified_at` 컬럼**(사용자 확정). 발행 시 세팅, 재활성 시 리셋.
- **`currentLearningPathSummary` = 이벤트 payload**(사용자 확정). learning-svc `ActivePathSummaryReader`가 `learning_paths`에서 조립. 활성 경로 없으면 null → ai-svc/Mock이 일반 문구.
- **Ollama provider 제외(스코프 축소)**: Mock(test·폴백)+Claude(prod)로 충분. `devpath.retention.provider`가 3-way 확장 가능하므로 후속에 `OllamaReEngagementClient`를 `OllamaAiReviewClient` 패턴으로 추가. **스펙의 3중 구현 중 Ollama만 후속으로 명시 연기** — 계획 검토 시 veto 가능.
- **실제 FCM 발송은 여전히 후속**(Build 3과 동일): `PushSender.send(userId,...)` 계약 뒤에서 `InboxPushSender`가 인앱 저장. 정체 알림도 inbox로 전달됨. `DeviceTokenRepository.findByUserId` 신설 + FCM은 별도 후속.
- **`lastActiveAt` Instant = `last_active_date` 로컬자정(UTC 기준)** 근사 — 이벤트의 정보성 필드(AI 프롬프트용)라 정밀 TZ 불요. 정밀화가 필요하면 `rollover`에 zone 전달 후속.

**3. 타입 일관성:** `UserStagnatedEvent`(6필드, Task 1) ↔ learning 발행(Task 3)·notification 역직렬화(Task 4) 일치 ✅. `ReEngagementInput`(ai-svc, Task 2) ↔ notification `RestReEngagementClient` 요청 body 키(`userId/lastActiveAt/daysInactive/currentLearningPathSummary`) 일치 ✅. `ReEngagementResult{message}`(Task 2) ↔ notification `ReEngagementResponse{message}`(Task 4) 일치 ✅. `PushSender.send(long,String,String,String)`(Build 3) ↔ `StagnationConsumer` 호출 일치 ✅.

**4. 순서 의존성:** Task 1(shared)→main 머지·publish **먼저**. Task 2(ai-svc)는 shared 무관(병렬 가능). Task 3·4는 Task 1 publish 후. Task 4는 Task 2 계약(엔드포인트 shape) 참조하나 런타임 의존이라 코드/테스트는 독립(Mock ai 클라이언트로 단위 테스트).

## 리스크 / 후속

- **Kafka at-least-once 재전달**: learning-svc가 에피소드당 1회 발행해도(마커) Kafka가 같은 메시지를 재전달하면 중복 푸시 가능. 현재 `StagnationConsumer`는 멱등 가드 없음 — 필요 시 `NotificationRepository.existsByUserIdAndTypeAndCreatedAtGreaterThanEqual`로 "최근 N일 내 RE_ENGAGEMENT 존재" 가드 추가(후속). nudge 성격이라 일단 미적용.
- **null `last_active_date` 유저**(한 번도 활동 없음)는 정체 대상에서 제외 — "재참여"가 아니라 "최초 참여"라 WELCOME/온보딩 소관. 스펙에 명시 없어 이 계획에서 확정.
- **ActivePathSummaryReader**는 활성 경로 1건만 요약(track+total_weeks). 진척률·다음 과제까지 넣으려면 후속 확장(스펙 §주간 리포트와 겹치는 영역).
- **Ollama provider**·**실제 FCM 멀티 디바이스 발송**은 후속(위 결정).

## Execution Handoff

계획 완료. 저장 위치: `documents/docs/superpowers/plans/2026-07-03-md3-retention-batch-build4.md`.
