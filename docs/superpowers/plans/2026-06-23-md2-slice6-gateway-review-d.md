# 슬라이스 #6 빌드 D — gateway `/reviews/**` 라우트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** gateway에 `/reviews/**` → ai-svc 라우트를 추가해, 프론트가 게이트웨이를 통해 리뷰 폴링/피드백 API에 접근하게 한다. JWT 엣지 검증은 기존 `anyExchange().authenticated()`로 자동 적용된다.

**Architecture:** Spring Cloud Gateway(WebFlux) 선언적 라우트 1개를 `application.yml`에 추가한다. 코드 변경은 라우트 설정뿐. 보안은 기존 `GatewaySecurityConfig`(전 경로 JWT) 무변경. 검증은 `ReviewRouteTest`(WebTestClient, `SandboxRouteTest` 미러).

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Spring Cloud Gateway(WebFlux) · WebTestClient · Mockito · `ReactiveJwtDecoder`.

## Global Constraints

- 대상 레포: `devpath-gateway` 단독. 설계서 [2026-06-23-md2-slice6-ai-code-review-design](../specs/2026-06-23-md2-slice6-ai-code-review-design.md) §5(gateway).
- **내부 경로 `/internal/**`(빌드 B 읽기 API)는 절대 라우트하지 않는다** — `/reviews/**`만 추가.
- ai-svc 컨테이너 포트 8080. 로컬 실행 포트는 다른 서비스(platform 8081·learning 8082·sandbox 8085)와 겹치지 않게 `AI_SVC_URI` 기본값을 둔다(예: `localhost:8084`; ai-svc 로컬 기동 포트에 맞춤 — 구현 시 ai-svc 실행 방식 확인).
- 보안: 기존 `GatewaySecurityConfig`가 전 경로 JWT를 강제하므로 `/reviews/**`도 자동 인증.
- 신규 작업 브랜치는 `develop`에서 분기.

---

## File Structure

- Modify: `src/main/resources/application.yml` — `ai-review` 라우트(`Path=/reviews/**` → `AI_SVC_URI`) 추가.
- Create(test): `src/test/java/ai/devpath/gateway/ReviewRouteTest.java` — `SandboxRouteTest` 미러.

---

## Task 0: 작업 브랜치

- [ ] **Step 1: 브랜치 분기**

```powershell
cd devpath-gateway
git switch develop
git pull
git switch -c feat/slice6-gateway-review-route
```

- [ ] **Step 2: 베이스라인**

```powershell
.\gradlew.bat test --tests "ai.devpath.gateway.SandboxRouteTest"
```

Expected: 기존 라우트 테스트 PASS.

---

## Task 1: `/reviews/**` 라우트 + ReviewRouteTest

**Files:**
- Modify: `src/main/resources/application.yml`
- Test: `src/test/java/ai/devpath/gateway/ReviewRouteTest.java`

**Interfaces:**
- Produces: `Path=/reviews/**` → `${AI_SVC_URI}` 라우트(id `ai-review`). 미인증 401, 인증 시 라우트 매칭(404 아님).

- [ ] **Step 1: 실패 테스트 작성**

`src/test/java/ai/devpath/gateway/ReviewRouteTest.java` (`SandboxRouteTest` 미러):

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
class ReviewRouteTest {

  @LocalServerPort int port;

  @MockitoBean ReactiveJwtDecoder jwtDecoder;

  WebTestClient web;

  @BeforeEach
  void setUp() {
    web = WebTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    when(jwtDecoder.decode("test-token")).thenReturn(Mono.just(jwt()));
  }

  @Test
  void reviewsRequireJwt() {
    web.get().uri("/reviews?sandboxSessionId=1").exchange()
        .expectStatus().isUnauthorized();
  }

  @Test
  void authenticatedReviewMatchesRoute() {
    web.get().uri("/reviews?sandboxSessionId=1")
        .header(HttpHeaders.AUTHORIZATION, "Bearer test-token")
        .exchange()
        .expectStatus().value(ReviewRouteTest::assertGatewayMatchedRoute);
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
.\gradlew.bat test --tests "ai.devpath.gateway.ReviewRouteTest"
```

Expected: `authenticatedReviewMatchesRoute` FAIL — `/reviews` 라우트 부재로 인증 후 404. (`reviewsRequireJwt`는 보안이 전 경로 차단이라 이미 PASS.)

- [ ] **Step 3: 라우트 추가**

`src/main/resources/application.yml`의 `routes:` 리스트에 `sandbox` 다음으로 추가:

```yaml
            - id: ai-review
              uri: ${AI_SVC_URI:http://localhost:8084}
              predicates:
                - Path=/reviews/**
```

> ⚠️ `/internal/**`은 추가하지 않는다(sandbox-svc 내부 API는 게이트웨이 미경유, 빌드 B/설계 D-7).

- [ ] **Step 4: 통과 확인**

```powershell
.\gradlew.bat test --tests "ai.devpath.gateway.ReviewRouteTest"
```

Expected: 두 케이스 PASS. (인증 후 `/reviews`는 ai-svc로 포워드 시도 → 연결 거부 5xx이지만 401/403/404가 아니므로 매칭 성립.)

- [ ] **Step 5: (있으면) RouteConfigTest 라우트 id 단언 추가**

`RouteConfigTest`가 라우트 id 집합을 단언한다면 `ai-review`를 추가한다(파일 확인 후, 없으면 생략). 그 후:

```powershell
.\gradlew.bat test --tests "ai.devpath.gateway.RouteConfigTest"
```

- [ ] **Step 6: 커밋**

```powershell
git add src/main/resources/application.yml src/test/java/ai/devpath/gateway/ReviewRouteTest.java
git commit -m "feat(gateway): route /reviews/** to ai-svc (slice6 D)"
```

---

## Task 2: 전체 회귀 + develop PR

- [ ] **Step 1: 전체 테스트**

```powershell
.\gradlew.bat clean test
```

Expected: 기존 라우트/보안 테스트 + 신규 ReviewRouteTest 전부 PASS.

- [ ] **Step 2: PR 생성·CI·머지**

```powershell
git push -u origin feat/slice6-gateway-review-route
gh pr create --base develop --title "feat(gateway): /reviews/** → ai-svc 라우트 (슬라이스 #6 빌드 D)" --body "리뷰 폴링/피드백 API 게이트웨이 라우트. JWT 엣지 자동. /internal/**는 미라우트(내부 전용). 설계서 docs/superpowers/specs/2026-06-23-md2-slice6-ai-code-review-design.md"
gh pr checks --watch
gh pr merge --merge
```

Expected: gateway CI 녹색. 앱이라 main 릴리스는 슬라이스 통합 릴리스에서.

---

## Self-Review 메모(작성자)

- **Spec 커버리지**: §5 gateway `/reviews/**`→ai-svc + JWT 엣지 = Task1. 전부 매핑.
- **placeholder 없음**: 라우트 YAML·테스트 실값. `AI_SVC_URI` 기본 포트는 ai-svc 로컬 기동 포트 확인 지시(추측 금지).
- **타입 일관성**: 라우트 id `ai-review`·`Path=/reviews/**`·`AI_SVC_URI`가 설계·프론트(빌드 E `/reviews` 호출)와 일치. 내부 `/internal/**` 미라우트(설계 D-7).
- **보안**: 기존 `anyExchange().authenticated()` 재사용 → `/reviews/**` 자동 JWT(SandboxRouteTest와 동일 거동).
