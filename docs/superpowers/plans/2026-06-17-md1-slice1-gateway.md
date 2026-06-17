# MD1 슬라이스 #1 — devpath-gateway JWT 검증·라우팅(빌드 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

> **⚠️ 상류 계약 의존 게이트:** 이 플랜은 platform 2a 구현 전에 작성됐다. **platform 2a가 develop 머지된 직후, 실행 전에** 다음을 재검증하라: (1) JWT 서명 알고리즘·시크릿 공유 방식(platform `JWT_SECRET` HS256과 동일), (2) 공개/보호 경로 목록(`/oauth2/**`·`/login/**`·`/auth/refresh`·`/auth/logout`·`/users/**`), (3) platform 실제 포트·서비스명. 불일치 시 본 플랜의 해당 Task를 먼저 수정.

**Goal:** gateway가 엣지에서 access JWT(HS256)를 검증하고, 보호 경로를 platform-svc로 라우팅한다. OAuth2 로그인·JWT 발급은 platform이 담당(설계서 D-3); gateway는 **검증 + 프록시**만.

**Architecture:** Spring Cloud Gateway(WebFlux, reactive). `SecurityWebFilterChain`(`@EnableWebFluxSecurity`)이 `oauth2ResourceServer().jwt()`로 Bearer 토큰을 `NimbusReactiveJwtDecoder.withSecretKey`(platform과 동일 HMAC 시크릿)로 검증한다. 공개 경로(OAuth 리다이렉트/콜백·`/auth/refresh`)는 검증 제외하고 platform으로 통과. 라우팅은 `spring.cloud.gateway` routes로 platform-svc에 프록시.

**Tech Stack:** Java 21 · Spring Boot 4.0.7 · Spring Cloud Gateway(WebFlux) 2025.1.2 · Spring Security 7(reactive) · reactor-test · WebTestClient.

## Global Constraints

- Java 21. 패키지 루트 `ai.devpath.gateway`. 메인 `GatewayApplication`. 포트 8080(reactive). reactor-test 사용(WebFlux).
- gateway는 **발급하지 않는다**(검증만). `spring-boot-starter-security-oauth2-client` 의존성 제거 → `spring-boot-starter-oauth2-resource-server`(reactive)로 교체.
- JWT 검증 = 대칭 HMAC HS256(설계서 R5). 시크릿은 env `JWT_SECRET`(platform과 **반드시 동일 값**). 절대 커밋 금지.
- 라우팅 대상은 env `PLATFORM_URI`(기본 `http://localhost:8081` 로컬 / `http://devpath-platform-svc:8080` 배포). 로컬은 platform과 포트 충돌 주의(gateway 8080, platform 8080 → 로컬 동시 구동 시 platform을 다른 포트로).
- 공개 경로(인증 제외): `/oauth2/**`, `/login/**`, `/auth/refresh`, `/auth/logout`, `/actuator/health`. 그 외 `/users/**` 등은 JWT 필요.
- CLAUDE.md "도메인" 표를 "JWT 검증 + 라우팅(발급은 platform)"으로 정정.
- 브랜치: develop에서 `feat/jwt-edge` 분기 → develop PR. main 직접 금지.

## Preconditions

- platform 2a develop 머지 + 위 "상류 계약 게이트" 재검증 완료.
- 작업 디렉터리 `D:\workspace\dev-path-ai\devpath-gateway`. 브랜치 `git checkout develop && git pull && git checkout -b feat/jwt-edge`.

## File Structure

- `build.gradle.kts` — oauth2-client 제거, oauth2-resource-server 추가.
- `src/main/resources/application.yml` — routes(platform) + 공개 경로.
- `config/GatewaySecurityConfig.java` — `SecurityWebFilterChain` + `ReactiveJwtDecoder`(HMAC) 빈.
- `CLAUDE.md` — 역할 정정.

---

### Task 1: 의존성 교체 + ReactiveJwtDecoder + SecurityWebFilterChain

**Files:**
- Modify: `build.gradle.kts`
- Create: `config/GatewaySecurityConfig.java`
- Create(test): `src/test/java/ai/devpath/gateway/config/GatewaySecurityConfigTest.java`
- Modify(test): 기존 `GatewayApplicationTests`(필요 시 프로파일)

**Interfaces:**
- Produces:
  - `SecretKey jwtSecretKey()` = `new SecretKeySpec(env JWT_SECRET bytes, "HmacSHA256")`.
  - `ReactiveJwtDecoder jwtDecoder(SecretKey)` = `NimbusReactiveJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build()`.
  - `SecurityWebFilterChain`(`ServerHttpSecurity`): 공개 경로 permitAll, 그 외 authenticated, `oauth2ResourceServer(jwt)`, csrf disable.

- [ ] **Step 1: build.gradle.kts 의존성 교체** — `implementation("org.springframework.boot:spring-boot-starter-security-oauth2-client")` 줄을 제거하고 추가:
```kotlin
	implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
```
테스트 의존성의 `spring-boot-starter-security-oauth2-client-test`도 제거(또는 `spring-security-test`로 교체):
```kotlin
	testImplementation("org.springframework.security:spring-security-test")
```

- [ ] **Step 2: 실패 테스트** — `config/GatewaySecurityConfigTest.java`(WebTestClient, 보안 동작):
```java
package ai.devpath.gateway.config;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.reactive.server.WebTestClient;

@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class GatewaySecurityConfigTest {

	@Autowired WebTestClient web;

	@Test
	void protectedRouteWithoutTokenIs401() {
		web.get().uri("/users/me").exchange().expectStatus().isUnauthorized();
	}

	@Test
	void publicAuthRefreshIsNot401() {
		// 다운스트림 미가동 시 라우팅 실패(5xx/404)일 수 있으나 보안 401은 아니어야 한다.
		web.post().uri("/auth/refresh").exchange()
			.expectStatus().value(s -> org.junit.jupiter.api.Assertions.assertTrue(s != 401));
	}
}
```
> 테스트는 `test` 프로파일에 `JWT_SECRET` 더미와 routes(존재하지 않는 다운스트림이라도 보안 레이어만 검증)를 둔다. `src/test/resources/application-test.yml`에 `devpath`/`spring.cloud.gateway` 최소 설정.

- [ ] **Step 3: 실패 확인** — `./gradlew test --tests "ai.devpath.gateway.config.GatewaySecurityConfigTest"` → FAIL(보안 빈 없음 → 기본 동작 불일치 또는 컴파일).

- [ ] **Step 4: GatewaySecurityConfig 작성** — `config/GatewaySecurityConfig.java`:
```java
package ai.devpath.gateway.config;

import java.nio.charset.StandardCharsets;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.reactive.EnableWebFluxSecurity;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.NimbusReactiveJwtDecoder;
import org.springframework.security.oauth2.jwt.ReactiveJwtDecoder;
import org.springframework.security.web.server.SecurityWebFilterChain;

@Configuration
@EnableWebFluxSecurity
public class GatewaySecurityConfig {

	@Bean
	public SecretKey jwtSecretKey(@Value("${JWT_SECRET:test-secret-please-change-min-32-bytes-long-0123456789}") String secret) {
		byte[] bytes = secret.getBytes(StandardCharsets.UTF_8);
		if (bytes.length < 32) { // P1-3: HS256 최소 256비트. platform과 동일 검증.
			throw new IllegalStateException("JWT_SECRET must be >= 32 bytes (HS256), got " + bytes.length);
		}
		return new SecretKeySpec(bytes, "HmacSHA256");
	}

	@Bean
	public ReactiveJwtDecoder jwtDecoder(SecretKey key) {
		return NimbusReactiveJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
	}

	@Bean
	public SecurityWebFilterChain securityWebFilterChain(ServerHttpSecurity http) {
		http
			.csrf(ServerHttpSecurity.CsrfSpec::disable)
			.cors(org.springframework.security.config.Customizer.withDefaults()) // P1-6/R6
			.authorizeExchange(ex -> ex
				.pathMatchers("/oauth2/**", "/login/**", "/auth/refresh", "/auth/logout", "/actuator/health").permitAll()
				.anyExchange().authenticated())
			.oauth2ResourceServer(rs -> rs.jwt(Customizer.withDefaults()));
		return http.build();
	}

	// P1-6/R6: SPA(이종 출처)의 쿠키 동반 요청 허용. allowCredentials=true는 와일드카드 origin과 양립 불가 →
	// 반드시 명시 allowlist(env)로 주입. 브라우저가 Set-Cookie 처리.
	@Bean
	public org.springframework.web.cors.reactive.CorsConfigurationSource corsConfigurationSource(
			@Value("${CORS_ALLOWED_ORIGINS:http://localhost:5173}") String origins) {
		var cfg = new org.springframework.web.cors.CorsConfiguration();
		cfg.setAllowCredentials(true);
		cfg.setAllowedOrigins(java.util.Arrays.asList(origins.split(",")));
		cfg.setAllowedMethods(java.util.List.of("GET", "POST", "PUT", "DELETE", "OPTIONS"));
		cfg.setAllowedHeaders(java.util.List.of("Authorization", "Content-Type"));
		var source = new org.springframework.web.cors.reactive.UrlBasedCorsConfigurationSource();
		source.registerCorsConfiguration("/**", cfg);
		return source;
	}
}
```
> `allowCredentials=true`에는 와일드카드(`*`) origin을 쓸 수 없다 — `CORS_ALLOWED_ORIGINS` env allowlist 필수(프론트 출처). `Cookie`는 단순요청에서 자동 동반이라 allowedHeaders에 명시 불필요하나, preflight 동작은 통합 테스트로 확인.

- [ ] **Step 5: 통과 확인** — `./gradlew test --tests "ai.devpath.gateway.config.GatewaySecurityConfigTest"` → PASS.

- [ ] **Step 5b: 추가 테스트(P1-3·P1-6)** — 같은 TDD로 두 케이스를 추가한다:
  - **P1-3 짧은 secret 거부:** `JWT_SECRET`이 32바이트 미만이면 컨텍스트 로드(또는 `jwtSecretKey` 빈 생성)가 `IllegalStateException`으로 실패함을 검증(`@SpringBootTest`에 짧은 secret 프로퍼티 주입 → `ApplicationContextException`/`assertThrows`).
  - **P1-6 CORS preflight:** 허용 origin의 OPTIONS preflight가 `Access-Control-Allow-Credentials: true` + 해당 origin 헤더를 반환하고, 비허용 origin은 거부됨을 `WebTestClient`로 검증.
- [ ] **Step 6: 커밋** — `git commit -m "feat(gateway): JWT(HMAC) 엣지 검증 + CORS(allow-credentials) + oauth2-client 의존성 제거"`.

---

### Task 2: platform 라우팅 설정

**Files:**
- Modify: `src/main/resources/application.yml`
- Create(test): `src/test/java/ai/devpath/gateway/RouteConfigTest.java`

**Interfaces:**
- Produces: `/oauth2/**`,`/login/**`,`/auth/**`,`/users/**` → `${PLATFORM_URI}` 라우트.

- [ ] **Step 1: application.yml routes** — `spring.cloud.gateway.server.webflux.routes`(현재 `[]`)를 채운다:
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
```
- [ ] **Step 2: 실패 테스트** — `RouteConfigTest.java`: `RouteLocator` 빈에서 `platform-auth` 라우트 존재 검증(reactor-test `StepVerifier`로 `routeLocator.getRoutes()`에 id 포함).
```java
package ai.devpath.gateway;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.test.context.ActiveProfiles;
import reactor.test.StepVerifier;

@SpringBootTest
@ActiveProfiles("test")
class RouteConfigTest {
	@Autowired RouteLocator routes;

	@Test
	void platformAuthRouteIsConfigured() {
		StepVerifier.create(routes.getRoutes().map(r -> r.getId()).filter(id -> id.equals("platform-auth")))
			.expectNext("platform-auth").verifyComplete();
	}
}
```
> test 프로파일 application-test.yml에도 동일 routes를 두어야 한다(또는 메인 yml을 테스트가 로드).
- [ ] **Step 3~5**: 실패 확인 → yml 작성 → 통과 → 커밋(`feat(gateway): platform-svc 라우팅`).

---

### Task 3: CLAUDE.md 역할 정정 + 전체 빌드 + PR

**Files:**
- Modify: `CLAUDE.md`(도메인 표 "인증" 행: "OAuth2 로그인 + JWT 발급/검증" → "JWT 검증 + 라우팅(발급·OAuth 로그인은 platform-svc)")
- 없음(빌드/PR)

- [ ] **Step 1: CLAUDE.md 정정** — `## 도메인` 표의 `인증` 행을 다음으로 교체:
```
| 인증 | JWT 검증(엣지) — 발급·OAuth2 로그인은 devpath-platform-svc |
```
- [ ] **Step 2: 전체 빌드** — `./gradlew clean build` → BUILD SUCCESSFUL(reactor-test).
- [ ] **Step 3: develop PR + CI green + 머지**
```bash
git push -u origin feat/jwt-edge
gh pr create --base develop --head feat/jwt-edge --title "feat: gateway JWT 엣지 검증 + platform 라우팅" --body "oauth2-client→resource-server(HMAC HS256, platform과 동일 JWT_SECRET). 공개경로 통과 + /users/me 등 JWT 필요. 설계서 D-3. CLAUDE.md 정정."
```

---

## Self-Review

**1. Spec coverage(설계서 §3.3):** oauth2-client→JWT 검증 교체 Task 1 ✓; 공개/보호 경로 Task 1 ✓; platform 라우팅 Task 2 ✓; CLAUDE.md 정정 Task 3 ✓.
**2. Placeholder scan:** 코드·테스트·명령 포함.
**3. Type consistency:** `NimbusReactiveJwtDecoder.withSecretKey`·HS256·공개경로 목록이 platform(2a SecurityConfig)과 일치(JWT_SECRET 공유).

**⚠️ 상류 의존:** 실행 전 "상류 계약 게이트"(헤더) 재검증 필수 — platform 2a의 실제 경로/시크릿/포트 확인 후 Task 1·2 조정.

## Execution Handoff
Plan complete and saved to `documents/docs/superpowers/plans/2026-06-17-md1-slice1-gateway.md`.
