# 슬라이스 #7 빌드 E — gateway `/ai-mentor/**` 라우트 + SSE 패스스루 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** gateway에 `/ai-mentor/**` → ai-svc 라우트를 추가해, 프론트가 게이트웨이를 통해 AI 멘토 SSE 세션 API(`POST /ai-mentor/sessions`)에 접근하게 한다. JWT 엣지 검증은 기존 `anyExchange().authenticated()`로 자동 적용되고, 멘토 응답은 `text/event-stream` 스트리밍이므로 WebFlux 게이트웨이가 버퍼링 없이 토큰을 흘리는지 확인한다.

**Architecture:** Spring Cloud Gateway(WebFlux, reactive/Netty) 선언적 라우트에 멘토 경로를 추가한다. 멘토 타깃은 코드리뷰와 동일한 ai-svc(`AI_SVC_URI`)이므로 **기존 `ai-review` 라우트의 `Path=` 술어에 `/ai-mentor/**`를 추가**한다(신규 라우트 id 불필요 — 동일 다운스트림). 코드 변경은 라우트 설정(`application.yml` + `application-test.yml`)뿐. 보안은 기존 `GatewaySecurityConfig`(전 경로 JWT) 무변경. 검증은 `MentorRouteTest`(WebTestClient, `ReviewRouteTest` 미러) + `RouteConfigTest` 멘토 경로 단언 + SSE 패스스루 확인 단계.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Spring Cloud Gateway Server WebFlux(`spring-cloud-starter-gateway-server-webflux`, Spring Cloud `2025.1.2`) · WebTestClient · Mockito · `ReactiveJwtDecoder`.

## Global Constraints

- 대상 레포: `devpath-gateway` 단독. 설계서 [2026-06-24-md3-slice7-ai-mentor-design](../specs/2026-06-24-md3-slice7-ai-mentor-design.md) §5(gateway)·§9 빌드 E·M-2(SSE 이벤트 계약).
- **내부 경로 `/internal/**`는 절대 라우트하지 않는다** — learning/sandbox 내부 조회 API(빌드 B/C, M-3)는 게이트웨이 미경유. `/ai-mentor/**`만 추가.
- 멘토 다운스트림은 코드리뷰와 동일한 ai-svc(`${AI_SVC_URI:http://localhost:8084}`, 컨테이너 포트 8080). **기존 `ai-review` 라우트 id를 재사용**하고 그 `Path=` 술어에 `/ai-mentor/**`만 덧붙인다(별도 라우트 id 생성 금지 — 동일 uri 중복 방지).
- 보안: 기존 `GatewaySecurityConfig`의 `anyExchange().authenticated()`가 전 경로 JWT를 강제하므로 `/ai-mentor/**`도 자동 인증. permitAll 목록(`/oauth2/**`, `/login/**`, `/auth/refresh`, `/auth/logout`, `/onboarding/assessments/guest/**`, `/actuator/health`)에 멘토 경로가 없음을 확인 → SecurityConfig 변경 없음(설계 I-6).
- **라우트는 두 파일에 중복 정의됨**: `src/main/resources/application.yml`(런타임)과 `src/test/resources/application-test.yml`(`@ActiveProfiles("test")` 로딩). **두 파일 모두** 동일하게 수정해야 테스트와 런타임이 일치한다.
- SSE: WebFlux 게이트웨이는 Project Reactor 기반 non-blocking I/O로 응답 바디를 **리액티브 스트리밍**한다(서블릿 버퍼링 없음). `text/event-stream` 토큰이 버퍼링 없이 통과하는지 **실증 확인 단계**를 둔다(설계 §10 리스크: "구현 시 검증"). 별도 버퍼링 비활성 설정이 필요 없음을 확인하되, 필요 시 근본 원인 규명 후에만 설정 추가(추측 금지).
- 신규 작업 브랜치는 `develop`에서 분기.

---

## File Structure

- Modify: `src/main/resources/application.yml` — `ai-review` 라우트 `Path=` 술어에 `/ai-mentor/**` 추가(런타임).
- Modify: `src/test/resources/application-test.yml` — 동일 변경(테스트 프로파일).
- Create(test): `src/test/java/ai/devpath/gateway/MentorRouteTest.java` — `ReviewRouteTest` 미러(POST `/ai-mentor/sessions`).
- Modify(test): `src/test/java/ai/devpath/gateway/RouteConfigTest.java` — 멘토 경로가 `ai-review` 라우트에 매칭되는지 단언 추가.

---

## Task 0: 작업 브랜치

- [ ] **Step 1: 브랜치 분기**

```powershell
cd devpath-gateway
git switch develop
git pull
git switch -c feat/slice7-gateway-mentor-route
```

- [ ] **Step 2: 베이스라인**

```powershell
.\gradlew.bat test --tests "ai.devpath.gateway.ReviewRouteTest" --tests "ai.devpath.gateway.RouteConfigTest"
```

Expected: 기존 코드리뷰 라우트 테스트·라우트 설정 테스트 모두 PASS(슬라이스 #6 빌드 D 산출물). 멘토 변경 전 그린 베이스라인 확인.

---

## Task 1: `/ai-mentor/**` 라우트 추가 + MentorRouteTest

설계 §5 gateway = `- Path=/ai-mentor/**` → ai-svc(`AI_SVC_URI`) + JWT 엣지 + SSE 패스스루. 멘토 다운스트림은 코드리뷰와 동일 ai-svc → 기존 `ai-review` 라우트의 `Path=` 술어에 멘토 경로를 덧붙인다.

**Files:**
- Modify: `src/main/resources/application.yml`
- Modify: `src/test/resources/application-test.yml`
- Test: `src/test/java/ai/devpath/gateway/MentorRouteTest.java`

**Interfaces:**
- Produces: `ai-review` 라우트가 `Path=/reviews/**,/ai-mentor/**`를 매칭 → `${AI_SVC_URI}`로 포워드. `POST /ai-mentor/sessions`은 미인증 401, 인증 시 라우트 매칭(404/401/403 아님).

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/gateway/MentorRouteTest.java`(`ReviewRouteTest` 미러 — POST + 멘토 세션 경로):

```java
package ai.devpath.gateway;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import java.time.Instant;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.ReactiveJwtDecoder;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.reactive.server.WebTestClient;
import reactor.core.publisher.Mono;

@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class MentorRouteTest {

  @LocalServerPort int port;

  @MockitoBean ReactiveJwtDecoder jwtDecoder;

  WebTestClient web;

  @BeforeEach
  void setUp() {
    web = WebTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    when(jwtDecoder.decode("test-token")).thenReturn(Mono.just(jwt()));
  }

  @Test
  void mentorSessionsRequireJwt() {
    web.post().uri("/ai-mentor/sessions").exchange()
        .expectStatus().isUnauthorized();
  }

  @Test
  void authenticatedMentorSessionMatchesRoute() {
    web.post().uri("/ai-mentor/sessions")
        .header(HttpHeaders.AUTHORIZATION, "Bearer test-token")
        .exchange()
        .expectStatus().value(MentorRouteTest::assertGatewayMatchedRoute);
  }

  private static void assertGatewayMatchedRoute(int status) {
    assertThat(status)
        .isNotEqualTo(HttpStatus.UNAUTHORIZED.value())
        .isNotEqualTo(HttpStatus.FORBIDDEN.value())
        .isNotEqualTo(HttpStatus.NOT_FOUND.value());
  }

  private static Jwt jwt() {
    Instant now = Instant.now();
    return Jwt.withTokenValue("test-token")
        .header("alg", "HS256")
        .subject("42")
        .issuedAt(now)
        .expiresAt(now.plusSeconds(600))
        .claim("scope", "ROLE_LEARNER")
        .build();
  }
}
```

- [ ] **Step 2: 실패 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.gateway.MentorRouteTest"
```

Expected: `authenticatedMentorSessionMatchesRoute` FAIL — `/ai-mentor/**` 라우트 부재로 인증 후 404. (`mentorSessionsRequireJwt`는 보안이 전 경로 차단이라 이미 PASS — `anyExchange().authenticated()`.)

- [ ] **Step 3: 라우트 경로 추가(런타임 + 테스트 두 파일)**

`src/main/resources/application.yml`의 `ai-review` 라우트 `Path=` 술어에 `/ai-mentor/**`를 추가(라우트 id·uri 변경 없음):

```yaml
            - id: ai-review
              uri: ${AI_SVC_URI:http://localhost:8084}
              predicates:
                - Path=/reviews/**,/ai-mentor/**
```

`src/test/resources/application-test.yml`도 **동일하게** 수정(같은 `ai-review` 블록):

```yaml
            - id: ai-review
              uri: ${AI_SVC_URI:http://localhost:8084}
              predicates:
                - Path=/reviews/**,/ai-mentor/**
```

> ⚠️ `/internal/**`은 추가하지 않는다(learning/sandbox 내부 API는 게이트웨이 미경유 — 설계 M-3).
> ⚠️ 두 파일을 모두 바꾼다 — `MentorRouteTest`/`RouteConfigTest`는 `@ActiveProfiles("test")`로 `application-test.yml`을 로딩하므로 테스트 파일만 바꾸면 런타임이, 런타임 파일만 바꾸면 테스트가 어긋난다.

- [ ] **Step 4: 통과 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.gateway.MentorRouteTest"
```

Expected: 두 케이스 PASS. (인증 후 `POST /ai-mentor/sessions`는 ai-svc로 포워드 시도 → ai-svc 미기동 시 연결 거부 5xx이지만 401/403/404가 아니므로 라우트 매칭 성립.)

- [ ] **Step 5: 커밋**

```powershell
git add src/main/resources/application.yml src/test/resources/application-test.yml src/test/java/ai/devpath/gateway/MentorRouteTest.java
git commit -m "feat(gateway): route /ai-mentor/** to ai-svc (slice7 E)"
```

---

## Task 2: RouteConfigTest 멘토 경로 단언

`/ai-mentor/**`는 별도 라우트 id가 아니라 기존 `ai-review` 라우트 술어에 추가되므로, 라우트 id 단언(`aiReviewRouteIsConfigured`)은 그대로다. 대신 **멘토 경로가 `ai-review` 라우트에 매칭되는지**를 단언해 path 추가를 잠근다(id 단언만으로는 `/ai-mentor/**` 누락을 잡지 못함).

**Files:**
- Modify: `src/test/java/ai/devpath/gateway/RouteConfigTest.java`

**Interfaces:**
- Asserts: `RouteLocator`의 `ai-review` 라우트 predicate가 `POST /ai-mentor/sessions` ServerWebExchange를 매칭(`true`).

- [ ] **Step 1: 실패 테스트 추가**

`RouteConfigTest.java`에 import와 테스트 메서드를 추가한다. 기존 import 블록 아래에 다음을 더한다:

```java
import org.springframework.cloud.gateway.route.Route;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.web.server.ServerWebExchange;
```

그리고 `aiReviewRouteIsConfigured` 테스트 다음에 메서드를 추가한다:

```java
	@Test
	void aiMentorPathMatchesAiReviewRoute() {
		ServerWebExchange exchange =
			MockServerWebExchange.from(MockServerHttpRequest.post("/ai-mentor/sessions").build());
		Route aiReview = routes.getRoutes()
			.filter(r -> r.getId().equals("ai-review"))
			.blockFirst();
		assertThat(aiReview).isNotNull();
		StepVerifier.create(aiReview.getPredicate().apply(exchange))
			.expectNext(true).verifyComplete();
	}
```

`assertThat`(AssertJ) static import가 없다면 클래스 상단 import에 추가:

```java
import static org.assertj.core.api.Assertions.assertThat;
```

- [ ] **Step 2: 실패→통과 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.gateway.RouteConfigTest"
```

Expected:
- Task 1 Step 3(라우트 경로 추가)을 **이미 적용한 상태**라면 PASS(멘토 경로가 `ai-review` predicate에 매칭).
- 만약 Task 1 Step 3을 적용하기 전 시점에 이 단언만 먼저 추가했다면 `aiMentorPathMatchesAiReviewRoute` FAIL(predicate가 `/ai-mentor/sessions`를 매칭하지 못해 `false` → `expectNext(true)` 불일치). 이 경우 Task 1 Step 3 적용 후 재실행하여 PASS 확인.

> 참고: 본 플랜은 Task 1에서 경로 추가를 먼저 커밋하므로 Task 2 시점엔 PASS가 기대값이다. TDD 순서를 엄격히 보려면 Task 2 Step 1을 Task 1 Step 1과 함께 작성해 동반 FAIL → 동반 PASS로 묶어도 된다(선택).

- [ ] **Step 3: 커밋**

```powershell
git add src/test/java/ai/devpath/gateway/RouteConfigTest.java
git commit -m "test(gateway): assert /ai-mentor/** matches ai-review route (slice7 E)"
```

---

## Task 3: SSE 패스스루 검증 (설계 §10 리스크 해소)

멘토 응답은 `text/event-stream`(M-2: `event:token` 반복 + `event:references`). 코드리뷰(`/reviews`)는 일반 REST였으므로 **SSE 스트리밍이 게이트웨이를 버퍼링 없이 통과하는지**는 신규 검증 사항이다. WebFlux 게이트웨이는 Project Reactor 기반 non-blocking I/O로 응답 바디를 리액티브 스트리밍하므로(서블릿 버퍼링 부재) 기본 통과가 기대값이다. 단, **추측 금지** — 실증으로 확인하고, 누설(버퍼링)이 관측되면 근본 원인 규명 후에만 설정을 추가한다.

**Files:** 신규/수정 없음(검증 전용 Task). 결과에 따라 필요 시 `application.yml`에 설정 추가가 발생할 수 있으나, **확인 전 선제 설정 추가 금지**.

- [ ] **Step 1: ai-svc 멘토 엔드포인트 기동 여부 확인(전제)**

빌드 D(ai-svc `mentor/`)가 develop에 머지되어 `POST /ai-mentor/sessions`가 SSE를 방출하는 상태여야 끝단간 실증이 가능하다. 미머지면 본 Task의 실증(Step 2)은 **빌드 D 머지 후 슬라이스 통합 검증으로 이연**하고, Step 3(이론 근거 기록)만 수행한다.

```powershell
# ai-svc develop에 mentor 컨트롤러가 있는지(원격) 확인 — 로컬 빌드는 GitHub Packages 인증 필요(핸드오프 §4)
gh api repos/DevPathAi/devpath-ai-svc/contents/src/main/java/ai/devpath/aigw/mentor?ref=develop --jq ".[].name" 2>$null
```

Expected: 빌드 D 머지 시 `MentorController.java` 등 파일명 출력. 빈 결과/404면 미머지 → Step 2 이연.

- [ ] **Step 2: (ai-svc 멘토 가용 시) 끝단간 SSE 패스스루 실증**

게이트웨이와 ai-svc를 함께 띄우고 `curl`로 SSE를 받아 **토큰이 점진적으로(버퍼링 없이) 도착**하는지 확인한다. (mock provider면 외부 LLM 불요.)

```powershell
# 1) ai-svc를 mock provider로 기동(별 터미널) — 예: AI_SVC 8084, devpath.mentor.provider=mock
#    (ai-svc 기동 방식은 ai-svc CLAUDE.md/README 확인. 로컬 불가 시 본 Step 이연.)
# 2) gateway 기동(별 터미널): .\gradlew.bat bootRun   (포트 8080)
# 3) 유효 JWT로 SSE 요청(--no-buffer로 클라이언트측 버퍼링 배제):
curl --no-buffer -N -H "Authorization: Bearer <VALID_JWT>" -H "Accept: text/event-stream" `
  -H "Content-Type: application/json" -d '{\"message\":\"테스트 질문\"}' `
  http://localhost:8080/ai-mentor/sessions
```

Expected:
- 응답 헤더 `Content-Type: text/event-stream`이 게이트웨이를 통해 보존된다.
- `event:token data:...` 라인이 **한꺼번에가 아니라 점진적으로** 흘러나오고, 이어 `event:references data:[...]`가 도착한 뒤 스트림이 정상 close된다(M-2 계약).
- 게이트웨이 경유(8080)와 ai-svc 직결(8084)의 스트리밍 거동이 동일(버퍼링으로 인한 일괄 도착 없음).

> 버퍼링(전체 응답이 한 번에 도착)이 관측되면: WebFlux 게이트웨이 기본 거동에 반하므로 **근본 원인 규명**(다운스트림 ai-svc가 flush를 안 하는지 / `Accept` 협상 / 클라이언트 버퍼)부터 한다. 게이트웨이 설정(예: 응답 버퍼링 관련) 변경은 원인을 설명할 수 있을 때만 추가하고, 추가 시 `RouteTest`로 회귀를 건다.

- [ ] **Step 3: 검증 결과 기록(근거 남김)**

본 Task의 실증/이연 여부와 결과를 빌드 E PR 본문 또는 슬라이스 핸드오프에 1~2줄로 남긴다(예: "SSE 패스스루 = WebFlux 리액티브 스트리밍 기본 통과, mock provider 끝단간 curl로 점진 도착 확인" 또는 "ai-svc 멘토 미머지로 통합 검증 시 실증 예정 — 이론상 WebFlux non-blocking 스트리밍으로 버퍼링 없음"). 코드/설정 변경이 없으면 커밋 없음.

---

## Task 4: 전체 회귀 + develop PR

- [ ] **Step 1: 전체 테스트**

```powershell
.\gradlew.bat clean test
```

Expected: 기존 라우트/보안 테스트(`AssessmentRouteTest`·`LearningPathRouteTest`·`ContentRouteTest`·`SandboxRouteTest`·`ReviewRouteTest`·`GatewaySecurityConfigTest`·`GatewaySecurityConfigShortSecretTest`·`RouteConfigTest`) + 신규 `MentorRouteTest` 전부 PASS.

- [ ] **Step 2: format/lint(있으면)**

```powershell
.\gradlew.bat build -x test
```

Expected: 컴파일·정적검사 통과(설정 변경 + 테스트 추가만이라 빌드 그린).

- [ ] **Step 3: PR 생성·CI·머지**

```powershell
git push -u origin feat/slice7-gateway-mentor-route
gh pr create --base develop --title "feat(gateway): /ai-mentor/** → ai-svc 라우트 + SSE 패스스루 (슬라이스 #7 빌드 E)" --body "AI 멘토 SSE 세션 API 게이트웨이 라우트. 기존 ai-review 라우트(ai-svc)에 /ai-mentor/** 경로 추가. JWT 엣지 자동(anyExchange().authenticated()). /internal/**는 미라우트(내부 전용). SSE는 WebFlux 리액티브 스트리밍으로 버퍼링 없이 통과(Task 3 검증). 설계서 docs/superpowers/specs/2026-06-24-md3-slice7-ai-mentor-design.md §5·빌드 E·M-2"
gh pr checks --watch
gh pr merge --merge
```

Expected: gateway CI 녹색. 앱이라 main 릴리스는 슬라이스 통합 릴리스에서.

---

## Self-Review 메모(작성자)

- **Spec 커버리지**(설계 §5 gateway / §9 빌드 E / M-2):
  - `- Path=/ai-mentor/**` → ai-svc(`AI_SVC_URI`) = Task 1 Step 3(기존 `ai-review` 라우트 술어에 추가).
  - `anyExchange().authenticated()` JWT 엣지로 `/ai-mentor/**` 인증 강제 = Task 1(`mentorSessionsRequireJwt` 401) + SecurityConfig 무변경 확인(Global Constraints).
  - SSE 패스스루 검증(설계 §10 리스크 "구현 시 검증") = Task 3.
  - `MentorRouteTest`(ReviewRouteTest 패턴 미러, `/ai-mentor/**` 라우팅 + JWT 401) = Task 1.
  - 전부 매핑.
- **실측 기반(추측 금지)**:
  - 기존 `ai-review` 라우트가 이미 `${AI_SVC_URI:http://localhost:8084}`로 ai-svc를 타깃 → 멘토는 path만 추가(설계 "있으면 같은 ai-svc로 path만 추가"). 신규 라우트 id 생성 안 함(동일 uri 중복 회피).
  - 라우트가 `application.yml`(런타임)·`application-test.yml`(테스트) **두 파일에 중복** → 둘 다 수정(테스트는 `@ActiveProfiles("test")`).
  - `GatewaySecurityConfig` permitAll 목록에 멘토 경로 없음 확인 → `anyExchange().authenticated()`로 자동 JWT(SecurityConfig 무변경, 설계 I-6).
  - 스택 = `spring-cloud-starter-gateway-server-webflux`(reactive/Netty, Spring Cloud `2025.1.2`, Boot 4.0.7) → SSE는 리액티브 non-blocking 스트리밍으로 기본 통과(공식 레퍼런스 확인). 버퍼링 비활성 설정은 **선제 추가 금지**, 누설 관측 시 근본 원인 규명 후에만.
- **placeholder 없음**: 라우트 YAML·`MentorRouteTest`·`RouteConfigTest` 메서드 모두 실값. `<VALID_JWT>`/ai-svc 기동만 환경 의존(실증 단계, 미가용 시 통합 검증 이연 명시).
- **타입/계약 일관성**: 프론트(빌드 F)가 `POST /ai-mentor/sessions {message, contentId?}`로 호출(설계 §5 frontend) → 라우트 prefix `/ai-mentor/**`와 일치. 내부 `/internal/**` 미라우트(설계 M-3). 라우트 id `ai-review`(코드리뷰와 공유)·`AI_SVC_URI`가 설계·빌드 D와 정합.
- **TDD**: 실패테스트(Step 1) → 실패확인(Step 2) → 구현(Step 3) → 통과확인(Step 4) → 커밋(Step 5). Task별 bite-sized.
- **경계**: 빌드 E(gateway)만. ai-svc 멘토 구현(빌드 D)·프론트(빌드 F)·learning/sandbox 내부 API(빌드 B/C)는 본 플랜 범위 밖. Task 3 끝단간 실증은 빌드 D 머지에 의존 → 미머지 시 통합 검증으로 이연(이론 근거는 기록).
