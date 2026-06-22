# 슬라이스 #5 빌드 C — gateway `/sandbox/**` 라우트 + JWT 엣지 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** devpath-gateway에 `/sandbox/**` → sandbox-svc(SANDBOX_URI) 라우트를 추가하고 JWT 엣지 검증이 적용됨을 테스트로 확인한다. 슬라이스 #3(`/learning-paths/**`)·#4(`/contents/**`) 추가 패턴과 완전히 동일한 메커니즘을 따른다.

**Architecture:** gateway는 YAML 라우트 선언(application.yml + application-test.yml) + `GatewaySecurityConfig`의 `anyExchange().authenticated()` 규칙으로 JWT 엣지 검증을 수행한다. 별도 Java 라우트 설정 클래스 없음 — YAML에 라우트 ID와 `uri`·`predicates` 추가만으로 완성. 테스트는 `ContentRouteTest`/`LearningPathRouteTest` 패턴(`@SpringBootTest + @MockitoBean ReactiveJwtDecoder + WebTestClient`) 그대로 복사 후 `/sandbox/**` 경로로 변경. `RouteConfigTest`에 `sandboxRouteIsConfigured` 케이스 1개 추가.

**Tech Stack:** Spring Boot 4.0.7 · Spring Cloud Gateway (WebFlux) · Java 21 · Gradle (Kotlin DSL) · JUnit 5 · WebTestClient.

## Global Constraints

- 대상 레포: **devpath-gateway 단독**.
- `/sandbox/**` 경로는 `GatewaySecurityConfig`의 `anyExchange().authenticated()` 규칙에 의해 자동으로 JWT 필수 경로가 된다. **SecurityConfig 코드 변경 없음**(현재 `permitAll` 목록: `/oauth2/**,/login/**,/auth/refresh,/auth/logout,/onboarding/assessments/guest/**,/actuator/health` — `/sandbox/**`는 여기 없으므로 인증 필수).
- 환경변수: `SANDBOX_URI`(운영) / 로컬 기본 포트 `http://localhost:8085`(기존 LEARNING_URI 기본값 `http://localhost:8082` 패턴 동일, sandbox-svc 포트는 빌드 B에서 확정될 값이나 미리 8085로 지정 — 빌드 B 실행 시 불일치하면 값만 조정).
- 테스트: `@ActiveProfiles("test")` + `@MockitoBean ReactiveJwtDecoder` 패턴 그대로. 업스트림(sandbox-svc) 미가동 상태여도 미인증 401·라우트 매칭(비4xx 응답) 검증 가능.
- 신규 작업 브랜치는 `develop`에서 분기(레포 CLAUDE.md 규칙 4).
- 모든 변경은 실패 테스트 우선(레포 CLAUDE.md 절대조건 2).

---

## File Structure

- Modify: `src/main/resources/application.yml` — `sandbox` 라우트 블록 추가.
- Modify: `src/test/resources/application-test.yml` — `sandbox` 라우트 블록 추가.
- Create(test): `src/test/java/ai/devpath/gateway/SandboxRouteTest.java` — 미인증 401·인증 시 라우트 매칭 검증.
- Modify(test): `src/test/java/ai/devpath/gateway/RouteConfigTest.java` — `sandboxRouteIsConfigured` 케이스 추가.

> 본보기: `ContentRouteTest.java`(테스트 패턴), `LearningPathRouteTest.java`(단일 경로 패턴), `RouteConfigTest.java`(라우트 ID 존재 검증), `application.yml`(YAML 라우트 블록), `application-test.yml`(테스트 오버라이드).

---

## Task 0: 작업 브랜치

- [ ] **Step 1: 브랜치 분기**

```powershell
cd D:\workspace\dev-path-ai\devpath-gateway
git switch develop
git pull
git switch -c feat/sandbox-gateway-route
```

---

## Task 1: SandboxRouteTest 실패 테스트 작성

**Files:**
- Create(test): `src/test/java/ai/devpath/gateway/SandboxRouteTest.java`
- Modify(test): `src/test/java/ai/devpath/gateway/RouteConfigTest.java`

**Interfaces:**
- Verifies: `/sandbox/**` 미인증 → 401(JWT 엣지 검증). 인증 토큰 → 401·403·404 아님(라우트 매칭). `sandbox` 라우트 ID 존재.

- [ ] **Step 1: 실패 테스트 작성** — `src/test/java/ai/devpath/gateway/SandboxRouteTest.java` 생성:

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
class SandboxRouteTest {

  @LocalServerPort int port;

  @MockitoBean ReactiveJwtDecoder jwtDecoder;

  WebTestClient web;

  @BeforeEach
  void setUp() {
    web = WebTestClient.bindToServer()
        .baseUrl("http://localhost:" + port)
        .build();
    when(jwtDecoder.decode("test-token")).thenReturn(Mono.just(jwt()));
  }

  @Test
  void sandboxRunRequiresJwt() {
    web.post().uri("/sandbox/run").exchange()
        .expectStatus().isUnauthorized();
  }

  @Test
  void sandboxRootRequiresJwt() {
    web.get().uri("/sandbox/sessions").exchange()
        .expectStatus().isUnauthorized();
  }

  @Test
  void authenticatedSandboxRunMatchesSandboxRoute() {
    web.post().uri("/sandbox/run")
        .header(HttpHeaders.AUTHORIZATION, "Bearer test-token")
        .exchange()
        .expectStatus().value(SandboxRouteTest::assertGatewayMatchedRoute);
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

- [ ] **Step 2: RouteConfigTest에 케이스 추가** — `src/test/java/ai/devpath/gateway/RouteConfigTest.java` 파일 끝의 마지막 `}` **앞에** 다음 메서드를 삽입한다:

```java
	@Test
	void sandboxRouteIsConfigured() {
		StepVerifier.create(routes.getRoutes().map(r -> r.getId()).filter(id -> id.equals("sandbox")))
			.expectNext("sandbox").verifyComplete();
	}
```

- [ ] **Step 3: 실패 확인**

```powershell
cd D:\workspace\dev-path-ai\devpath-gateway
.\gradlew.bat test --tests "ai.devpath.gateway.SandboxRouteTest" --tests "ai.devpath.gateway.RouteConfigTest"
```

Expected: `SandboxRouteTest` 전 케이스 FAIL(라우트 없어 404 응답 → assertGatewayMatchedRoute 실패) 또는 컴파일 실패. `RouteConfigTest.sandboxRouteIsConfigured` FAIL(`sandbox` 라우트 ID 없음).

---

## Task 2: YAML 라우트 선언 추가 (main + test)

**Files:**
- Modify: `src/main/resources/application.yml`
- Modify: `src/test/resources/application-test.yml`

**Interfaces:**
- Produces: `sandbox` 라우트 ID. `SANDBOX_URI` 환경변수로 sandbox-svc URI 주입(기본 `http://localhost:8085`). `/sandbox/**` path predicate.

- [ ] **Step 1: application.yml 수정** — `src/main/resources/application.yml`의 `routes:` 리스트 끝(현재 `learning` 블록 다음)에 `sandbox` 라우트 블록을 추가한다.

현재 파일 전체 내용을 다음으로 교체한다:

```yaml
spring:
  application:
    name: devpath-gateway
  cloud:
    gateway:
      server:
        webflux:
          routes:
            - id: platform-auth
              uri: ${PLATFORM_URI:http://localhost:8081}
              predicates:
                - Path=/oauth2/**,/login/**,/auth/**,/users/**
            - id: learning
              uri: ${LEARNING_URI:http://localhost:8082}
              predicates:
                - Path=/onboarding/assessments/**,/learning-paths/**,/dashboard/**,/contents/**
            - id: sandbox
              uri: ${SANDBOX_URI:http://localhost:8085}
              predicates:
                - Path=/sandbox/**

server:
  port: 8080

management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics, gateway
```

- [ ] **Step 2: application-test.yml 수정** — `src/test/resources/application-test.yml`의 `routes:` 리스트 끝(현재 `learning` 블록 다음)에 동일한 `sandbox` 라우트 블록을 추가한다.

현재 파일 전체 내용을 다음으로 교체한다:

```yaml
spring:
  cloud:
    gateway:
      server:
        webflux:
          routes:
            - id: platform-auth
              uri: ${PLATFORM_URI:http://localhost:8081}
              predicates:
                - Path=/oauth2/**,/login/**,/auth/**,/users/**
            - id: learning
              uri: ${LEARNING_URI:http://localhost:8082}
              predicates:
                - Path=/onboarding/assessments/**,/learning-paths/**,/dashboard/**,/contents/**
            - id: sandbox
              uri: ${SANDBOX_URI:http://localhost:8085}
              predicates:
                - Path=/sandbox/**

JWT_SECRET: "test-secret-please-change-min-32-bytes-long-0123456789"
CORS_ALLOWED_ORIGINS: "http://localhost:5173"

management:
  endpoints:
    web:
      exposure:
        include: health
```

- [ ] **Step 3: 통과 확인**

```powershell
cd D:\workspace\dev-path-ai\devpath-gateway
.\gradlew.bat test --tests "ai.devpath.gateway.SandboxRouteTest" --tests "ai.devpath.gateway.RouteConfigTest"
```

Expected:
- `SandboxRouteTest.sandboxRunRequiresJwt` PASS (미인증 → 401).
- `SandboxRouteTest.sandboxRootRequiresJwt` PASS (미인증 → 401).
- `SandboxRouteTest.authenticatedSandboxRunMatchesSandboxRoute` PASS (인증 → sandbox-svc로 라우팅, 업스트림 미가동이라 연결거부 5xx이지만 401/403/404는 아님).
- `RouteConfigTest.sandboxRouteIsConfigured` PASS (`sandbox` 라우트 ID 발견).
- `RouteConfigTest.platformAuthRouteIsConfigured` · `learningRouteIsConfigured` 회귀 없음.

---

## Task 3: 전체 회귀 + 커밋

- [ ] **Step 1: 전체 테스트**

```powershell
cd D:\workspace\dev-path-ai\devpath-gateway
.\gradlew.bat test
```

Expected: BUILD SUCCESSFUL. 기존 `AssessmentRouteTest`·`ContentRouteTest`·`LearningPathRouteTest`·`GatewaySecurityConfigTest`·`GatewaySecurityConfigShortSecretTest` 포함 전 케이스 PASS. 신규 `SandboxRouteTest`(3개)·`RouteConfigTest.sandboxRouteIsConfigured`(1개) 포함.

- [ ] **Step 2: 커밋**

```powershell
git add src/main/resources/application.yml src/test/resources/application-test.yml src/test/java/ai/devpath/gateway/SandboxRouteTest.java src/test/java/ai/devpath/gateway/RouteConfigTest.java
git commit -m "feat(gateway): add /sandbox/** route to sandbox-svc (MD2 slice5 build C)"
```

---

## Task 4: develop PR + CI 녹색 확인

- [ ] **Step 1: develop PR 생성**

```powershell
git push -u origin feat/sandbox-gateway-route
gh pr create --base develop --title "feat(gateway): /sandbox/** route to sandbox-svc (slice5 C)" --body "MD2 슬라이스 #5 빌드 C. /sandbox/** → SANDBOX_URI(기본 http://localhost:8085) 라우트 추가. GatewaySecurityConfig 변경 없음(anyExchange().authenticated()로 JWT 엣지 검증 자동 적용). SandboxRouteTest(미인증 401·인증 시 라우트 매칭)·RouteConfigTest(sandboxRouteIsConfigured) 추가. 설계서 docs/superpowers/specs/2026-06-22-md2-slice5-sandbox-design.md §5."
```

- [ ] **Step 2: CI 녹색 확인**

```powershell
gh pr checks --watch
```

Expected: CI `build` job 녹색. 녹색 확인 후에만 머지(컨트롤러 직접 검증). gateway는 DB 의존 없으므로 fresh DB 불필요.

---

## Self-Review 메모(작성자)

- **Spec 커버리지**: 설계서 §5 "gateway: `/sandbox/**` → sandbox-svc 라우트(SANDBOX_URI), JWT 엣지 검증. 슬라이스 #3/#4 패턴 동일" — Task 1~2에서 완전 구현.
- **SecurityConfig 무변경 근거**: `GatewaySecurityConfig.java` 실측 확인 — `anyExchange().authenticated()`가 모든 비공개 경로를 JWT 필수로 만들며 `/sandbox/**`는 `permitAll` 목록에 없으므로 추가 설정 불필요.
- **SANDBOX_URI 기본 포트(8085)**: sandbox-svc 포트는 빌드 B에서 확정됨. LEARNING_URI 기본 8082 패턴에 따라 8085 임시 지정. 빌드 B 완료 후 실제 포트와 다를 경우 이 파일과 yml만 수정하면 됨.
- **No placeholder**: YAML 라우트 블록·테스트 클래스·PR 명령 전량 실코드.
- **타입 일관성**: 라우트 ID `sandbox`·predicate `Path=/sandbox/**`·환경변수 `SANDBOX_URI`·테스트 경로 `/sandbox/run`,`/sandbox/sessions`이 본문·YAML·테스트 파일에서 일관.
- **교훈 반영**: `@MockitoBean ReactiveJwtDecoder`(Boot4 bean override 패턴), `@ActiveProfiles("test")`, `WebEnvironment.RANDOM_PORT`, `assertGatewayMatchedRoute` helper(404 제외 → 업스트림 미가동 상태에서도 라우트 매칭 검증 가능) — ContentRouteTest/LearningPathRouteTest에서 검증된 패턴 그대로.
