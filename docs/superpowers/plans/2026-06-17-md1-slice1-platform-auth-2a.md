# MD1 슬라이스 #1 — devpath-platform-svc 인증 척추(2a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GitHub OAuth2 로그인 → 사용자 upsert(+`UserRegisteredEvent` outbox 기록) → JWT 발급 → Redis refresh 회전 → `/users/me`가 platform-svc에서 실동작하는 인증 코어를 구축한다.

**Architecture:** Spring Boot 4 / Spring Security 7 servlet. 하나의 `SecurityFilterChain`이 (1) `oauth2Login`(GitHub, 세션 기반 로그인 댄스)과 (2) `oauth2ResourceServer().jwt()`(stateless Bearer 검증)를 함께 구성한다. 로그인 성공 핸들러가 사용자를 upsert하고(동일 트랜잭션에 outbox 기록) refresh 토큰을 Redis에 해시 저장 + HttpOnly 쿠키로 내려준 뒤 SPA로 리다이렉트한다(설계서 R1). SPA는 `/auth/refresh`로 첫 access JWT를 받는다. JWT는 대칭 HMAC(HS256, 설계서 R5). provider 토큰은 Google Tink AEAD로 암호화해 `user_oauth_identities`에 저장. 스키마는 devpath-shared가 소유(`ddl-auto: validate`).

**Tech Stack:** Java 21 · Spring Boot 4.0.7 · Spring Security 7 · Gradle(Kotlin DSL) · PostgreSQL 17 · Redis 7 · Google Tink · JUnit 5 · `ai.devpath:devpath-shared`(GitHub Packages).

## Global Constraints

- Java 21. 패키지 루트 `ai.devpath.platform`. 메인 `PlatformApplication`. 실행 포트 8080.
- 빌드 `./gradlew build` / 테스트 `./gradlew test`(JUnit5). DB 연동은 실DB(로컬 docker-compose / CI postgres service container, env `DB_URL`/`DB_USER`/`DB_PASSWORD` 기본 `jdbc:postgresql://localhost:5432/devpath`·`devpath`·`localdev`). Redis는 env `REDIS_HOST`/`REDIS_PORT` 기본 `localhost`/`6379`.
- `spring.jpa.hibernate.ddl-auto: validate` — 스키마는 shared 소유. 엔티티는 **매핑만**, 새 테이블 생성 금지. Flyway는 platform에서 `enabled: false`.
- 마이그레이션은 절대 platform-svc에 두지 않는다(shared 소유). 새 테이블·컬럼이 필요하면 멈추고 보고(이 플랜은 기존 shared 스키마만 사용: `users`·`user_oauth_identities`·`user_profiles`·`outbox`).
- 토큰 전략(설계서 D-2): access=JWT HS256 단명(15분), refresh=불투명 토큰(서버측 Redis 해시 저장, TTL 14일, 회전 시 이전 무효화), HttpOnly·Secure·SameSite 쿠키.
- JWT 비밀키(`JWT_SECRET`, ≥32바이트)·GitHub client id/secret(`GITHUB_CLIENT_ID`/`GITHUB_CLIENT_SECRET`)·Tink keyset(`TOKEN_ENC_KEYSET`)·SPA URL(`APP_WEB_URL`)는 **env 주입, 절대 커밋 금지**. 테스트는 테스트 전용 더미 값을 코드/리소스에 둔다(실제 시크릿 아님).
- provider enum 값은 `GITHUB`(shared CHECK 제약과 일치). eventType 상수는 `UserRegisteredEvent.EVENT_TYPE` 사용(하드코딩 금지).
- **D-9 user 객체 shape(프론트 dp_core `User`와 정합):** `/auth/refresh`·`/users/me`가 반환하는 user 객체는 dp_core `User`(`{id, email, nickname, role, onboardingStatus}`)와 동일 키·타입으로 직렬화한다. `id`는 **문자열**(`String.valueOf(user.getId())`), `role`/`onboardingStatus`는 enum 문자열("LEARNER"/"PENDING" 등). `plan`·`email` 누락 금지. (04_API §1.1의 예시(plan 포함)보다 dp_core `User`가 실제 소비자이므로 이를 따른다.)
- 보안 구현은 well-tested 라이브러리 사용(Spring Security·Nimbus·Tink). 토큰 서명·암호화 자체 구현 금지.
- 브랜치: devpath-platform-svc `develop`에서 `feat/oauth-auth-core` 분기 → `develop` PR(2단계). main 직접 금지.

## Preconditions

- 작업 디렉터리: `D:\workspace\dev-path-ai\devpath-platform-svc`.
- **PostgreSQL + Redis 가동**: devpath-shared에서 `docker compose up -d`(postgres 5432·redis 6379). PG 준비 `docker exec devpath-local-postgres-1 pg_isready -U devpath -d devpath`.
- DB에 shared 마이그레이션 적용돼 있어야 함(`users`·`user_oauth_identities`·`user_profiles`·`outbox`). 미적용이면 shared에서 `./gradlew flywayMigrate` 또는 `FlywayMigrationTest` 1회 실행.
- 브랜치: `git checkout develop && git pull && git checkout -b feat/oauth-auth-core`.

## File Structure

- `build.gradle.kts` — 의존성 활성화(security·oauth2-client·oauth2-resource-server·oauth2-jose·data-redis·Tink).
- `src/main/resources/application.yml` — github client registration(env), jwt/redis/cookie/app-web-url 설정.
- `config/AuthProperties.java` — `@ConfigurationProperties("devpath.auth")` (jwt secret·access TTL·refresh TTL·cookie 속성·web url).
- `config/SecurityConfig.java` — `SecurityFilterChain`, `JwtEncoder`/`JwtDecoder`(HMAC) 빈, `ClientRegistrationRepository`(env github).
- `user/User.java`·`UserOauthIdentity.java`·`UserProfile.java` — JPA 엔티티.
- `user/UserRepository.java`·`UserOauthIdentityRepository.java`·`UserProfileRepository.java`.
- `outbox/OutboxEntry.java`·`OutboxRepository.java`.
- `auth/crypto/TokenCipher.java` — Tink AEAD encrypt/decrypt.
- `auth/jwt/JwtService.java` — access JWT mint.
- `auth/refresh/RefreshTokenStore.java` — Redis 해시 저장/검증/회전/폐기.
- `auth/RefreshCookies.java` — refresh 쿠키 생성/삭제(ResponseCookie).
- `auth/UserRegistrationService.java` — `@Transactional` upsert + outbox 기록.
- `auth/OAuth2LoginSuccessHandler.java` — 성공 시 upsert→refresh 쿠키→SPA 리다이렉트.
- `auth/AuthController.java` — `/auth/refresh`·`/auth/logout`.
- `auth/dto/LoginResponse.java`·`UserSummary.java`.
- `user/UserController.java` — `/users/me`.

---

### Task 0: shared develop→main 릴리스 (Packages 배포) — 선행

platform-svc는 GitHub Packages의 `ai.devpath:devpath-shared:0.0.1-SNAPSHOT`을 의존한다. 새 스키마/이벤트(`UserRegisteredEvent`)가 Packages에 있어야 platform 빌드(로컬·CI)가 해소된다. shared `publish.yml`은 main push에서 publish하므로 develop→main 릴리스가 필요하다(설계서 D-6).

**Files:** 없음(릴리스 PR).

- [ ] **Step 1: shared develop→main 릴리스 PR 생성**

```bash
cd /d/workspace/dev-path-ai/devpath-shared
git checkout develop && git pull
gh pr create --base main --head develop \
  --title "release: 인증 스키마 + UserRegisteredEvent (MD1 슬라이스 #1)" \
  --body "users 확장·user_oauth_identities·user_profiles·outbox + UserRegisteredEvent. develop→main 릴리스로 GitHub Packages publish."
```

- [ ] **Step 2: CI 녹색 확인 후 머지**

Run: `gh pr checks <PR번호> --watch`
Expected: build 통과. 통과 시 `gh pr merge <PR번호> --merge`.

- [ ] **Step 3: publish 워크플로 성공 확인** — main 머지가 `publish.yml`(`./gradlew publish`)을 트리거한다.

Run: `gh run list --workflow publish.yml --branch main --limit 1`
Expected: 최근 run `success`. 실패 시 로그 분석(Packages 권한·중복 버전). 성공해야 platform이 새 클래스를 받는다.

- [ ] **Step 4: platform 의존 해소 확인**

```bash
cd /d/workspace/dev-path-ai/devpath-platform-svc
git checkout develop && git pull && git checkout -b feat/oauth-auth-core
./gradlew dependencies --configuration compileClasspath 2>&1 | grep devpath-shared
```
Expected: `ai.devpath:devpath-shared:0.0.1-SNAPSHOT` 해소(에러 없음). 이후 Task에서 `import ai.devpath.shared.event.UserRegisteredEvent;`가 컴파일된다.

---

### Task 1: 의존성 활성화 + 설정 + AuthProperties

보안/OAuth/JWT/Redis/Tink 의존성을 켜고 설정 골격을 만든다. 보안 활성화 후에도 컨텍스트가 로드됨을 검증한다.

**Files:**
- Modify: `build.gradle.kts`
- Modify: `src/main/resources/application.yml`
- Create: `src/main/java/ai/devpath/platform/config/AuthProperties.java`
- Create(test): `src/test/resources/application-test.yml`
- Modify(test): `src/test/java/ai/devpath/platform/PlatformApplicationTests.java`

**Interfaces:**
- Produces: `AuthProperties`(record-like `@ConfigurationProperties("devpath.auth")`) — `getJwtSecret()`, `getAccessTtl()`(Duration), `getRefreshTtl()`(Duration), `getWebUrl()`, `getCookieDomain()`, `isCookieSecure()`, `getCookieSameSite()`.

- [ ] **Step 1: build.gradle.kts 의존성 활성화** — `dependencies` 블록의 주석 처리된 security/redis를 켜고 oauth2/jose/tink을 추가한다. 기존 블록을 다음으로 교체:

```kotlin
dependencies {
	implementation("org.springframework.boot:spring-boot-starter-actuator")
	implementation("org.springframework.boot:spring-boot-starter-validation")
	implementation("org.springframework.boot:spring-boot-starter-webmvc")
	implementation("org.springframework.boot:spring-boot-starter-data-jpa")
	implementation("org.springframework.boot:spring-boot-starter-security")
	implementation("org.springframework.boot:spring-boot-starter-oauth2-client")
	implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
	implementation("org.springframework.boot:spring-boot-starter-data-redis")
	implementation("com.google.crypto.tink:tink:1.18.0")
	implementation("ai.devpath:devpath-shared:0.0.1-SNAPSHOT")
	runtimeOnly("org.postgresql:postgresql")
	compileOnly("org.projectlombok:lombok")
	annotationProcessor("org.projectlombok:lombok")
	testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
	testImplementation("org.springframework.boot:spring-boot-starter-security-test")
	testCompileOnly("org.projectlombok:lombok")
	testRuntimeOnly("org.junit.platform:junit-platform-launcher")
	testAnnotationProcessor("org.projectlombok:lombok")
}
```

- [ ] **Step 2: application.yml에 OAuth/JWT/Redis/auth 설정 추가** — 기존 내용 끝에 추가:

```yaml
  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: ${REDIS_PORT:6379}
  security:
    oauth2:
      client:
        registration:
          github:
            client-id: ${GITHUB_CLIENT_ID:dummy-client-id}
            client-secret: ${GITHUB_CLIENT_SECRET:dummy-secret}
            scope: read:user,user:email

devpath:
  auth:
    jwt-secret: ${JWT_SECRET:test-secret-please-change-min-32-bytes-long-0123456789}
    access-ttl: ${ACCESS_TTL:PT15M}
    refresh-ttl: ${REFRESH_TTL:P14D}
    web-url: ${APP_WEB_URL:http://localhost:5173}
    cookie-domain: ${COOKIE_DOMAIN:}
    cookie-secure: ${COOKIE_SECURE:false}
    cookie-same-site: ${COOKIE_SAME_SITE:Lax}
```

> 주의: `spring.data.redis`는 기존 `spring:` 블록 하위에 들어가야 한다(들여쓰기 확인). 더미 값은 테스트/로컬 부팅용 — 실제 시크릿은 env로만.

- [ ] **Step 3: AuthProperties 작성** — `config/AuthProperties.java`:

```java
package ai.devpath.platform.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("devpath.auth")
public class AuthProperties {
	private String jwtSecret;
	private Duration accessTtl = Duration.ofMinutes(15);
	private Duration refreshTtl = Duration.ofDays(14);
	private String webUrl;
	private String cookieDomain = "";
	private boolean cookieSecure = false;
	private String cookieSameSite = "Lax";

	public String getJwtSecret() { return jwtSecret; }
	public void setJwtSecret(String v) { this.jwtSecret = v; }
	public Duration getAccessTtl() { return accessTtl; }
	public void setAccessTtl(Duration v) { this.accessTtl = v; }
	public Duration getRefreshTtl() { return refreshTtl; }
	public void setRefreshTtl(Duration v) { this.refreshTtl = v; }
	public String getWebUrl() { return webUrl; }
	public void setWebUrl(String v) { this.webUrl = v; }
	public String getCookieDomain() { return cookieDomain; }
	public void setCookieDomain(String v) { this.cookieDomain = v; }
	public boolean isCookieSecure() { return cookieSecure; }
	public void setCookieSecure(boolean v) { this.cookieSecure = v; }
	public String getCookieSameSite() { return cookieSameSite; }
	public void setCookieSameSite(String v) { this.cookieSameSite = v; }
}
```

`PlatformApplication`에 `@ConfigurationPropertiesScan` 추가(클래스 애너테이션):

```java
@SpringBootApplication
@org.springframework.boot.context.properties.ConfigurationPropertiesScan
public class PlatformApplication {
	public static void main(String[] args) { SpringApplication.run(PlatformApplication.class, args); }
}
```

- [ ] **Step 4: 테스트 설정 + 컨텍스트 로드 테스트** — `src/test/resources/application-test.yml`(테스트용 더미; Redis 미연결 시 컨텍스트 로드만 검증하려면 lettuce는 lazy):

```yaml
devpath:
  auth:
    jwt-secret: test-secret-please-change-min-32-bytes-long-0123456789
spring:
  security:
    oauth2:
      client:
        registration:
          github:
            client-id: test-client
            client-secret: test-secret
            scope: read:user,user:email
```

`PlatformApplicationTests`를 프로파일 지정으로 수정:

```java
package ai.devpath.platform;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class PlatformApplicationTests {

	@Test
	void contextLoads() {
	}
}
```

- [ ] **Step 5: 실패→통과 확인**

Run: `./gradlew test --tests "ai.devpath.platform.PlatformApplicationTests"`
Expected: 의존성 추가/설정 전 RED(컴파일 또는 빈 누락) → 후 PASS. (Redis 빈은 lettuce가 lazy 연결이라 컨텍스트 로드는 실제 연결 없이 통과. 연결이 필요한 테스트는 Task 5에서 실Redis 사용.)

- [ ] **Step 6: 커밋**

```bash
git add build.gradle.kts src/main/resources/application.yml src/main/java/ai/devpath/platform/config/AuthProperties.java src/main/java/ai/devpath/platform/PlatformApplication.java src/test/resources/application-test.yml src/test/java/ai/devpath/platform/PlatformApplicationTests.java
git commit -m "feat(auth): 보안/OAuth/JWT/Redis/Tink 의존성 + auth 설정"
```

---

### Task 2: JPA 엔티티 + 리포지토리 (shared 스키마 매핑)

`ddl-auto: validate`로 shared 스키마에 매핑되는 엔티티를 만든다. 매핑 오류는 컨텍스트 로드 시 검증된다.

**Files:**
- Create: `user/User.java`, `user/UserOauthIdentity.java`, `user/UserProfile.java`, `outbox/OutboxEntry.java`
- Create: `user/UserRepository.java`, `user/UserOauthIdentityRepository.java`, `user/UserProfileRepository.java`, `outbox/OutboxRepository.java`
- Create(test): `src/test/java/ai/devpath/platform/user/UserMappingTest.java`

**Interfaces:**
- Produces:
  - `User`(id Long, email String, nickname String, role String, status String, onboardingStatus String, createdAt/updatedAt/lastActiveAt Instant) — table `users`.
  - `UserOauthIdentity`(id Long, userId Long, provider String, providerUserId String, accessTokenEncrypted String, refreshTokenEncrypted String, scope String, linkedAt Instant) — table `user_oauth_identities`.
  - `UserProfile`(userId Long @Id, avatar, bio, learningGoal, targetTrack, experienceYears Integer) — table `user_profiles`.
  - `OutboxEntry`(id Long, aggregateType String, aggregateId String, eventType String, payload String, createdAt Instant, publishedAt Instant) — table `outbox`, payload는 `@JdbcTypeCode(SqlTypes.JSON)`.
  - `UserOauthIdentityRepository.findByProviderAndProviderUserId(String, String): Optional<UserOauthIdentity>`.
  - `OutboxRepository extends JpaRepository<OutboxEntry, Long>`.

- [ ] **Step 1: 실패 테스트 작성** — `user/UserMappingTest.java` (실DB에 매핑·CRUD 검증):

```java
package ai.devpath.platform.user;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.devpath.platform.outbox.OutboxEntry;
import ai.devpath.platform.outbox.OutboxRepository;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase.Replace;

@DataJpaTest
@AutoConfigureTestDatabase(replace = Replace.NONE)
class UserMappingTest {

	@Autowired UserRepository users;
	@Autowired UserOauthIdentityRepository identities;
	@Autowired UserProfileRepository profiles;
	@Autowired OutboxRepository outbox;

	@Test
	void persistsUserIdentityProfileAndOutbox() {
		User u = new User();
		u.setEmail("t" + System.nanoTime() + "@example.com");
		u.setNickname("지수");
		u.setRole("LEARNER");
		u.setStatus("ACTIVE");
		u.setOnboardingStatus("PENDING");
		User saved = users.save(u);
		assertTrue(saved.getId() != null);

		UserOauthIdentity id = new UserOauthIdentity();
		id.setUserId(saved.getId());
		id.setProvider("GITHUB");
		id.setProviderUserId("gh-" + System.nanoTime());
		id.setLinkedAt(Instant.now());
		identities.save(id);
		assertTrue(identities.findByProviderAndProviderUserId(id.getProvider(), id.getProviderUserId()).isPresent());

		UserProfile p = new UserProfile();
		p.setUserId(saved.getId());
		profiles.save(p);

		OutboxEntry e = new OutboxEntry();
		e.setAggregateType("user");
		e.setAggregateId(String.valueOf(saved.getId()));
		e.setEventType("user.user.registered");
		e.setPayload("{\"userId\":" + saved.getId() + "}");
		e.setCreatedAt(Instant.now());
		OutboxEntry savedE = outbox.save(e);
		assertEquals("user.user.registered", savedE.getEventType());
	}
}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `./gradlew test --tests "ai.devpath.platform.user.UserMappingTest"`
Expected: FAIL — 컴파일 에러(엔티티/리포지토리 없음).

- [ ] **Step 3: 엔티티/리포지토리 작성**

`user/User.java`:
```java
package ai.devpath.platform.user;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "users")
public class User {
	@Id @GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;
	private String email;
	private String nickname;
	@Column(nullable = false) private String role = "LEARNER";
	@Column(nullable = false) private String status = "ACTIVE";
	@Column(name = "onboarding_status", nullable = false) private String onboardingStatus = "PENDING";
	@Column(name = "created_at", insertable = false, updatable = false) private Instant createdAt;
	@Column(name = "updated_at", insertable = false, updatable = false) private Instant updatedAt;
	@Column(name = "last_active_at", insertable = false, updatable = false) private Instant lastActiveAt;

	public Long getId() { return id; }
	public String getEmail() { return email; }
	public void setEmail(String v) { this.email = v; }
	public String getNickname() { return nickname; }
	public void setNickname(String v) { this.nickname = v; }
	public String getRole() { return role; }
	public void setRole(String v) { this.role = v; }
	public String getStatus() { return status; }
	public void setStatus(String v) { this.status = v; }
	public String getOnboardingStatus() { return onboardingStatus; }
	public void setOnboardingStatus(String v) { this.onboardingStatus = v; }
	public Instant getCreatedAt() { return createdAt; }
}
```

`user/UserOauthIdentity.java`:
```java
package ai.devpath.platform.user;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "user_oauth_identities")
public class UserOauthIdentity {
	@Id @GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;
	@Column(name = "user_id", nullable = false) private Long userId;
	@Column(nullable = false) private String provider;
	@Column(name = "provider_user_id", nullable = false) private String providerUserId;
	@Column(name = "access_token_encrypted") private String accessTokenEncrypted;
	@Column(name = "refresh_token_encrypted") private String refreshTokenEncrypted;
	private String scope;
	@Column(name = "linked_at", nullable = false) private Instant linkedAt;

	public Long getId() { return id; }
	public Long getUserId() { return userId; }
	public void setUserId(Long v) { this.userId = v; }
	public String getProvider() { return provider; }
	public void setProvider(String v) { this.provider = v; }
	public String getProviderUserId() { return providerUserId; }
	public void setProviderUserId(String v) { this.providerUserId = v; }
	public String getAccessTokenEncrypted() { return accessTokenEncrypted; }
	public void setAccessTokenEncrypted(String v) { this.accessTokenEncrypted = v; }
	public String getRefreshTokenEncrypted() { return refreshTokenEncrypted; }
	public void setRefreshTokenEncrypted(String v) { this.refreshTokenEncrypted = v; }
	public String getScope() { return scope; }
	public void setScope(String v) { this.scope = v; }
	public Instant getLinkedAt() { return linkedAt; }
	public void setLinkedAt(Instant v) { this.linkedAt = v; }
}
```

`user/UserProfile.java`:
```java
package ai.devpath.platform.user;

import jakarta.persistence.*;

@Entity
@Table(name = "user_profiles")
public class UserProfile {
	@Id @Column(name = "user_id") private Long userId;
	private String avatar;
	private String bio;
	@Column(name = "learning_goal") private String learningGoal;
	@Column(name = "target_track") private String targetTrack;
	@Column(name = "experience_years") private Integer experienceYears;

	public Long getUserId() { return userId; }
	public void setUserId(Long v) { this.userId = v; }
	public String getAvatar() { return avatar; }
	public void setAvatar(String v) { this.avatar = v; }
	public String getBio() { return bio; }
	public void setBio(String v) { this.bio = v; }
	public String getLearningGoal() { return learningGoal; }
	public void setLearningGoal(String v) { this.learningGoal = v; }
	public String getTargetTrack() { return targetTrack; }
	public void setTargetTrack(String v) { this.targetTrack = v; }
	public Integer getExperienceYears() { return experienceYears; }
	public void setExperienceYears(Integer v) { this.experienceYears = v; }
}
```

`outbox/OutboxEntry.java`:
```java
package ai.devpath.platform.outbox;

import jakarta.persistence.*;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "outbox")
public class OutboxEntry {
	@Id @GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;
	@Column(name = "aggregate_type", nullable = false) private String aggregateType;
	@Column(name = "aggregate_id", nullable = false) private String aggregateId;
	@Column(name = "event_type", nullable = false) private String eventType;
	@JdbcTypeCode(SqlTypes.JSON)
	@Column(nullable = false) private String payload;
	@Column(name = "created_at", nullable = false) private Instant createdAt;
	@Column(name = "published_at") private Instant publishedAt;

	public Long getId() { return id; }
	public String getAggregateType() { return aggregateType; }
	public void setAggregateType(String v) { this.aggregateType = v; }
	public String getAggregateId() { return aggregateId; }
	public void setAggregateId(String v) { this.aggregateId = v; }
	public String getEventType() { return eventType; }
	public void setEventType(String v) { this.eventType = v; }
	public String getPayload() { return payload; }
	public void setPayload(String v) { this.payload = v; }
	public Instant getCreatedAt() { return createdAt; }
	public void setCreatedAt(Instant v) { this.createdAt = v; }
	public Instant getPublishedAt() { return publishedAt; }
	public void setPublishedAt(Instant v) { this.publishedAt = v; }
}
```

리포지토리 4개:
```java
// user/UserRepository.java
package ai.devpath.platform.user;
import org.springframework.data.jpa.repository.JpaRepository;
public interface UserRepository extends JpaRepository<User, Long> {}
```
```java
// user/UserOauthIdentityRepository.java
package ai.devpath.platform.user;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
public interface UserOauthIdentityRepository extends JpaRepository<UserOauthIdentity, Long> {
	Optional<UserOauthIdentity> findByProviderAndProviderUserId(String provider, String providerUserId);
}
```
```java
// user/UserProfileRepository.java
package ai.devpath.platform.user;
import org.springframework.data.jpa.repository.JpaRepository;
public interface UserProfileRepository extends JpaRepository<UserProfile, Long> {}
```
```java
// outbox/OutboxRepository.java
package ai.devpath.platform.outbox;
import org.springframework.data.jpa.repository.JpaRepository;
public interface OutboxRepository extends JpaRepository<OutboxEntry, Long> {}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `./gradlew test --tests "ai.devpath.platform.user.UserMappingTest"`
Expected: PASS — `ddl-auto: validate`가 매핑을 검증하고 CRUD 성공. (실패 시 컬럼명/타입 불일치 → shared 스키마 대조.)

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/platform/user src/main/java/ai/devpath/platform/outbox src/test/java/ai/devpath/platform/user/UserMappingTest.java
git commit -m "feat(user): users/oauth/profile/outbox JPA 엔티티 + 리포지토리"
```

---

### Task 3: JwtService (access JWT HMAC mint) + JwtDecoder/JwtEncoder 빈

대칭 HMAC(HS256)로 access JWT를 발급한다(설계서 R5). 발급↔검증 라운드트립을 단위 검증.

**Files:**
- Create: `config/SecurityConfig.java`(빈만 우선 — `JwtEncoder`/`JwtDecoder`/`SecretKey`; FilterChain은 Task 7)
- Create: `auth/jwt/JwtService.java`
- Create(test): `src/test/java/ai/devpath/platform/auth/jwt/JwtServiceTest.java`

**Interfaces:**
- Consumes: `AuthProperties.getJwtSecret()`, `getAccessTtl()`.
- Produces:
  - `SecretKey jwtSecretKey(AuthProperties)` 빈 — `new SecretKeySpec(secret.getBytes(UTF_8), "HmacSHA256")`.
  - `JwtEncoder jwtEncoder(SecretKey)` = `NimbusJwtEncoder.withSecretKey(key).build()`.
  - `JwtDecoder jwtDecoder(SecretKey)` = `NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build()`.
  - `JwtService.mintAccessToken(long userId, String role): String` — subject=userId, claim `role`, issuedAt/expiresAt(now+accessTtl), header HS256.

- [ ] **Step 1: 실패 테스트 작성** — `auth/jwt/JwtServiceTest.java`:

```java
package ai.devpath.platform.auth.jwt;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.devpath.platform.config.AuthProperties;
import ai.devpath.platform.config.SecurityConfig;
import java.time.Instant;
import javax.crypto.SecretKey;
import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;

class JwtServiceTest {

	private JwtService newService() {
		AuthProperties props = new AuthProperties();
		props.setJwtSecret("test-secret-please-change-min-32-bytes-long-0123456789");
		SecurityConfig cfg = new SecurityConfig(props);
		SecretKey key = cfg.jwtSecretKey();
		JwtEncoder encoder = cfg.jwtEncoder(key);
		return new JwtService(encoder, props);
	}

	@Test
	void mintsDecodableAccessTokenWithSubjectAndRole() {
		JwtService svc = newService();
		String token = svc.mintAccessToken(42L, "LEARNER");

		AuthProperties props = new AuthProperties();
		props.setJwtSecret("test-secret-please-change-min-32-bytes-long-0123456789");
		SecurityConfig cfg = new SecurityConfig(props);
		JwtDecoder decoder = cfg.jwtDecoder(cfg.jwtSecretKey());
		Jwt jwt = decoder.decode(token);

		assertEquals("42", jwt.getSubject());
		assertEquals("LEARNER", jwt.getClaimAsString("role"));
		assertTrue(jwt.getExpiresAt().isAfter(Instant.now()));
	}
}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `./gradlew test --tests "ai.devpath.platform.auth.jwt.JwtServiceTest"`
Expected: FAIL — `SecurityConfig`/`JwtService` 없음(컴파일 에러).

- [ ] **Step 3: SecurityConfig 빈 + JwtService 작성**

`config/SecurityConfig.java` (이 Task는 빈 메서드만; FilterChain은 Task 7에서 동일 클래스에 추가):
```java
package ai.devpath.platform.config;

import java.nio.charset.StandardCharsets;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;

@Configuration
public class SecurityConfig {

	private final AuthProperties props;

	public SecurityConfig(AuthProperties props) { this.props = props; }

	@Bean
	public SecretKey jwtSecretKey() {
		return new SecretKeySpec(props.getJwtSecret().getBytes(StandardCharsets.UTF_8), "HmacSHA256");
	}

	@Bean
	public JwtEncoder jwtEncoder(SecretKey key) {
		return new NimbusJwtEncoder(new com.nimbusds.jose.jwk.source.ImmutableSecret<>(key));
	}

	@Bean
	public JwtDecoder jwtDecoder(SecretKey key) {
		return NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
	}
}
```

`auth/jwt/JwtService.java`:
```java
package ai.devpath.platform.auth.jwt;

import ai.devpath.platform.config.AuthProperties;
import java.time.Instant;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.stereotype.Service;

@Service
public class JwtService {

	private final JwtEncoder encoder;
	private final AuthProperties props;

	public JwtService(JwtEncoder encoder, AuthProperties props) {
		this.encoder = encoder;
		this.props = props;
	}

	public String mintAccessToken(long userId, String role) {
		Instant now = Instant.now();
		JwtClaimsSet claims = JwtClaimsSet.builder()
				.subject(String.valueOf(userId))
				.issuedAt(now)
				.expiresAt(now.plus(props.getAccessTtl()))
				.claim("role", role)
				.build();
		JwsHeader header = JwsHeader.with(MacAlgorithm.HS256).build();
		return encoder.encode(JwtEncoderParameters.from(header, claims)).getTokenValue();
	}
}
```

> 구현 주의: `NimbusJwtEncoder`는 HS256 서명을 위해 `ImmutableSecret<>(SecretKey)` JWKSource를 받는다(Security 7). `withSecretKey` 빌더가 있으면 그걸 써도 된다 — 컴파일되는 형태로 확정하라. 자체 서명 구현 금지.

- [ ] **Step 4: 테스트 통과 확인**

Run: `./gradlew test --tests "ai.devpath.platform.auth.jwt.JwtServiceTest"`
Expected: PASS — mint한 토큰이 decode되고 subject="42", role="LEARNER", exp 미래.

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/platform/config/SecurityConfig.java src/main/java/ai/devpath/platform/auth/jwt src/test/java/ai/devpath/platform/auth/jwt/JwtServiceTest.java
git commit -m "feat(auth): HMAC JWT 발급/검증 빈 + JwtService"
```

---

### Task 4: TokenCipher (Tink AEAD provider 토큰 암호화)

GitHub access token을 DB(`access_token_encrypted`)에 저장 전 Tink AEAD로 암호화한다. encrypt→decrypt 라운드트립 검증.

**Files:**
- Create: `auth/crypto/TokenCipher.java`
- Create(test): `src/test/java/ai/devpath/platform/auth/crypto/TokenCipherTest.java`

**Interfaces:**
- Produces: `TokenCipher.encrypt(String plaintext): String`(base64), `TokenCipher.decrypt(String b64): String`. 키셋은 env `TOKEN_ENC_KEYSET`(base64 Tink keyset); 미설정 시(테스트/로컬) 임시 인메모리 keyset 생성 + 경고 로그.

- [ ] **Step 1: 실패 테스트 작성** — `auth/crypto/TokenCipherTest.java`:

```java
package ai.devpath.platform.auth.crypto;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;

import org.junit.jupiter.api.Test;

class TokenCipherTest {

	@Test
	void encryptThenDecryptRoundtrips() throws Exception {
		TokenCipher cipher = new TokenCipher(null); // null env → 임시 keyset
		String plain = "gho_exampletoken123";
		String enc = cipher.encrypt(plain);
		assertNotEquals(plain, enc);
		assertEquals(plain, cipher.decrypt(enc));
	}
}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `./gradlew test --tests "ai.devpath.platform.auth.crypto.TokenCipherTest"`
Expected: FAIL — `TokenCipher` 없음.

- [ ] **Step 3: TokenCipher 작성** — `auth/crypto/TokenCipher.java`:

```java
package ai.devpath.platform.auth.crypto;

import com.google.crypto.tink.Aead;
import com.google.crypto.tink.InsecureSecretKeyAccess;
import com.google.crypto.tink.KeysetHandle;
import com.google.crypto.tink.TinkJsonProtoKeysetFormat;
import com.google.crypto.tink.aead.AeadConfig;
import com.google.crypto.tink.aead.PredefinedAeadParameters;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class TokenCipher {

	private static final Logger log = LoggerFactory.getLogger(TokenCipher.class);
	private final Aead aead;

	public TokenCipher(@Value("${TOKEN_ENC_KEYSET:#{null}}") String keysetB64) throws Exception {
		AeadConfig.register();
		KeysetHandle handle;
		if (keysetB64 == null || keysetB64.isBlank()) {
			log.warn("TOKEN_ENC_KEYSET 미설정 — 임시 인메모리 keyset 사용(개발 전용). 프로덕션은 반드시 env 주입.");
			handle = KeysetHandle.generateNew(PredefinedAeadParameters.AES256_GCM);
		} else {
			String json = new String(Base64.getDecoder().decode(keysetB64), StandardCharsets.UTF_8);
			handle = TinkJsonProtoKeysetFormat.parseKeyset(json, InsecureSecretKeyAccess.get());
		}
		this.aead = handle.getPrimitive(Aead.class);
	}

	public String encrypt(String plaintext) {
		try {
			byte[] ct = aead.encrypt(plaintext.getBytes(StandardCharsets.UTF_8), new byte[0]);
			return Base64.getEncoder().encodeToString(ct);
		} catch (Exception e) {
			throw new IllegalStateException("토큰 암호화 실패", e);
		}
	}

	public String decrypt(String b64) {
		try {
			byte[] pt = aead.decrypt(Base64.getDecoder().decode(b64), new byte[0]);
			return new String(pt, StandardCharsets.UTF_8);
		} catch (Exception e) {
			throw new IllegalStateException("토큰 복호화 실패", e);
		}
	}
}
```

> 주의: Tink API 시그니처(`TinkJsonProtoKeysetFormat`·`PredefinedAeadParameters`)는 Tink 1.18 기준. 컴파일되는 정확한 형태로 확정하라(자체 암호 구현 금지).

- [ ] **Step 4: 테스트 통과 확인**

Run: `./gradlew test --tests "ai.devpath.platform.auth.crypto.TokenCipherTest"`
Expected: PASS — enc≠plain, decrypt(enc)=plain.

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/platform/auth/crypto src/test/java/ai/devpath/platform/auth/crypto/TokenCipherTest.java
git commit -m "feat(auth): Tink AEAD provider 토큰 암호화 TokenCipher"
```

---

### Task 5: RefreshTokenStore (Redis 해시 저장/검증/회전/폐기)

refresh 토큰을 불투명 난수로 발급하고, Redis에 SHA-256 해시 키로 userId를 TTL 저장한다. 회전 시 이전 키 삭제. **실 Redis 연결 필요.**

**Files:**
- Create: `auth/refresh/RefreshTokenStore.java`
- Create(test): `src/test/java/ai/devpath/platform/auth/refresh/RefreshTokenStoreTest.java`

**Interfaces:**
- Consumes: `StringRedisTemplate`, `AuthProperties.getRefreshTtl()`.
- Produces:
  - `RefreshTokenStore.issue(long userId): String` — 난수 토큰 반환, Redis `refresh:{sha256(token)}` → userId, TTL=refreshTtl.
  - `RefreshTokenStore.validate(String token): Optional<Long>` — 유효하면 userId.
  - `RefreshTokenStore.rotate(String oldToken): Optional<Rotated>` — oldToken 검증·삭제 후 새 토큰 발급. `Rotated(long userId, String newToken)`.
  - `RefreshTokenStore.revoke(String token): void`.

- [ ] **Step 1: 실패 테스트 작성** — `auth/refresh/RefreshTokenStoreTest.java` (실 Redis: `@SpringBootTest` + `StringRedisTemplate`):

```java
package ai.devpath.platform.auth.refresh;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.devpath.platform.config.AuthProperties;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class RefreshTokenStoreTest {

	@Autowired StringRedisTemplate redis;

	private RefreshTokenStore store() {
		AuthProperties props = new AuthProperties();
		props.setRefreshTtl(Duration.ofDays(14));
		return new RefreshTokenStore(redis, props);
	}

	@Test
	void issueValidateRotateRevoke() {
		RefreshTokenStore s = store();
		String t = s.issue(42L);
		assertEquals(42L, s.validate(t).orElseThrow());

		var rotated = s.rotate(t).orElseThrow();
		assertEquals(42L, rotated.userId());
		assertFalse(s.validate(t).isPresent(), "회전 후 이전 토큰 무효");
		assertEquals(42L, s.validate(rotated.newToken()).orElseThrow());

		s.revoke(rotated.newToken());
		assertFalse(s.validate(rotated.newToken()).isPresent(), "폐기 후 무효");
	}
}
```

- [ ] **Step 2: 테스트 실패 확인** (Redis 가동 필수)

Run: `./gradlew test --tests "ai.devpath.platform.auth.refresh.RefreshTokenStoreTest"`
Expected: FAIL — `RefreshTokenStore` 없음.

- [ ] **Step 3: RefreshTokenStore 작성** — `auth/refresh/RefreshTokenStore.java`:

```java
package ai.devpath.platform.auth.refresh;

import ai.devpath.platform.config.AuthProperties;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.Optional;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

@Component
public class RefreshTokenStore {

	public record Rotated(long userId, String newToken) {}

	private static final String PREFIX = "refresh:";
	private static final SecureRandom RANDOM = new SecureRandom();

	private final StringRedisTemplate redis;
	private final AuthProperties props;

	public RefreshTokenStore(StringRedisTemplate redis, AuthProperties props) {
		this.redis = redis;
		this.props = props;
	}

	public String issue(long userId) {
		byte[] raw = new byte[32];
		RANDOM.nextBytes(raw);
		String token = Base64.getUrlEncoder().withoutPadding().encodeToString(raw);
		redis.opsForValue().set(PREFIX + hash(token), String.valueOf(userId), props.getRefreshTtl());
		return token;
	}

	public Optional<Long> validate(String token) {
		if (token == null || token.isBlank()) return Optional.empty();
		String v = redis.opsForValue().get(PREFIX + hash(token));
		return v == null ? Optional.empty() : Optional.of(Long.parseLong(v));
	}

	public Optional<Rotated> rotate(String oldToken) {
		Optional<Long> userId = validate(oldToken);
		if (userId.isEmpty()) return Optional.empty();
		redis.delete(PREFIX + hash(oldToken));
		String next = issue(userId.get());
		return Optional.of(new Rotated(userId.get(), next));
	}

	public void revoke(String token) {
		if (token != null && !token.isBlank()) redis.delete(PREFIX + hash(token));
	}

	private static String hash(String token) {
		try {
			byte[] d = MessageDigest.getInstance("SHA-256").digest(token.getBytes(StandardCharsets.UTF_8));
			return Base64.getUrlEncoder().withoutPadding().encodeToString(d);
		} catch (Exception e) {
			throw new IllegalStateException(e);
		}
	}
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `./gradlew test --tests "ai.devpath.platform.auth.refresh.RefreshTokenStoreTest"`
Expected: PASS — issue/validate/rotate(이전 무효)/revoke 동작.

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/platform/auth/refresh src/test/java/ai/devpath/platform/auth/refresh/RefreshTokenStoreTest.java
git commit -m "feat(auth): Redis refresh 토큰 저장/회전/폐기 RefreshTokenStore"
```

---

### Task 6: UserRegistrationService (@Transactional upsert + outbox 기록)

OAuth 신원으로 사용자를 찾거나(없으면) users+identity+profile 생성 + `UserRegisteredEvent`를 동일 트랜잭션으로 outbox 기록. provider access token은 암호화 저장.

**Files:**
- Create: `auth/UserRegistrationService.java`
- Create(test): `src/test/java/ai/devpath/platform/auth/UserRegistrationServiceTest.java`

**Interfaces:**
- Consumes: `UserRepository`, `UserOauthIdentityRepository`, `UserProfileRepository`, `OutboxRepository`, `TokenCipher`, `ObjectMapper`, `UserRegisteredEvent`.
- Produces:
  - `record OauthUser(String provider, String providerUserId, String email, String nickname, String accessToken)`.
  - `UserRegistrationService.registerOrFind(OauthUser): User` — `@Transactional`. 신규면 user(email·nickname·role=LEARNER·status=ACTIVE·onboarding=PENDING)+identity(암호화 토큰)+빈 profile 생성 + outbox 1행(eventType=`UserRegisteredEvent.EVENT_TYPE`, payload=직렬화). 기존이면 해당 user 반환(중복 생성·이벤트 없음).

- [ ] **Step 1: 실패 테스트 작성** — `auth/UserRegistrationServiceTest.java`:

```java
package ai.devpath.platform.auth;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.devpath.platform.auth.UserRegistrationService.OauthUser;
import ai.devpath.platform.outbox.OutboxRepository;
import ai.devpath.platform.user.User;
import ai.devpath.platform.user.UserOauthIdentityRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class UserRegistrationServiceTest {

	@Autowired UserRegistrationService service;
	@Autowired UserOauthIdentityRepository identities;
	@Autowired OutboxRepository outbox;

	@Test
	void newIdentityCreatesUserProfileIdentityAndOutboxEvent() {
		String providerUserId = "gh-" + System.nanoTime();
		long outboxBefore = outbox.count();
		OauthUser oauth = new OauthUser("GITHUB", providerUserId, "u@example.com", "지수", "gho_token");

		User created = service.registerOrFind(oauth);

		assertTrue(created.getId() != null);
		assertEquals("PENDING", created.getOnboardingStatus());
		assertTrue(identities.findByProviderAndProviderUserId("GITHUB", providerUserId).isPresent());
		assertEquals(outboxBefore + 1, outbox.count(), "신규 가입 시 outbox 1행");
	}

	@Test
	void existingIdentityReturnsSameUserWithoutDuplicateEvent() {
		String providerUserId = "gh-" + System.nanoTime();
		OauthUser oauth = new OauthUser("GITHUB", providerUserId, "u@example.com", "지수", "gho_token");
		User first = service.registerOrFind(oauth);
		long outboxAfterFirst = outbox.count();

		User second = service.registerOrFind(oauth);

		assertEquals(first.getId(), second.getId());
		assertEquals(outboxAfterFirst, outbox.count(), "기존 사용자는 이벤트 미발생");
	}
}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `./gradlew test --tests "ai.devpath.platform.auth.UserRegistrationServiceTest"`
Expected: FAIL — `UserRegistrationService` 없음.

- [ ] **Step 3: UserRegistrationService 작성** — `auth/UserRegistrationService.java`:

```java
package ai.devpath.platform.auth;

import ai.devpath.platform.auth.crypto.TokenCipher;
import ai.devpath.platform.outbox.OutboxEntry;
import ai.devpath.platform.outbox.OutboxRepository;
import ai.devpath.platform.user.*;
import ai.devpath.shared.event.UserRegisteredEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class UserRegistrationService {

	public record OauthUser(String provider, String providerUserId, String email, String nickname, String accessToken) {}

	private final UserRepository users;
	private final UserOauthIdentityRepository identities;
	private final UserProfileRepository profiles;
	private final OutboxRepository outbox;
	private final TokenCipher cipher;
	private final ObjectMapper objectMapper;

	public UserRegistrationService(UserRepository users, UserOauthIdentityRepository identities,
			UserProfileRepository profiles, OutboxRepository outbox, TokenCipher cipher, ObjectMapper objectMapper) {
		this.users = users;
		this.identities = identities;
		this.profiles = profiles;
		this.outbox = outbox;
		this.cipher = cipher;
		this.objectMapper = objectMapper;
	}

	@Transactional
	public User registerOrFind(OauthUser oauth) {
		var existing = identities.findByProviderAndProviderUserId(oauth.provider(), oauth.providerUserId());
		if (existing.isPresent()) {
			return users.findById(existing.get().getUserId()).orElseThrow();
		}

		User user = new User();
		user.setEmail(oauth.email());
		user.setNickname(oauth.nickname());
		user.setRole("LEARNER");
		user.setStatus("ACTIVE");
		user.setOnboardingStatus("PENDING");
		user = users.save(user);

		UserOauthIdentity identity = new UserOauthIdentity();
		identity.setUserId(user.getId());
		identity.setProvider(oauth.provider());
		identity.setProviderUserId(oauth.providerUserId());
		if (oauth.accessToken() != null) identity.setAccessTokenEncrypted(cipher.encrypt(oauth.accessToken()));
		identity.setScope("read:user,user:email");
		identity.setLinkedAt(Instant.now());
		identities.save(identity);

		UserProfile profile = new UserProfile();
		profile.setUserId(user.getId());
		profiles.save(profile);

		writeOutbox(user, oauth.provider());
		return user;
	}

	private void writeOutbox(User user, String provider) {
		UserRegisteredEvent event = new UserRegisteredEvent(
				UUID.randomUUID(), Instant.now(), user.getId(), provider, user.getEmail());
		OutboxEntry entry = new OutboxEntry();
		entry.setAggregateType("user");
		entry.setAggregateId(String.valueOf(user.getId()));
		entry.setEventType(UserRegisteredEvent.EVENT_TYPE);
		entry.setPayload(serialize(event));
		entry.setCreatedAt(Instant.now());
		outbox.save(entry);
	}

	private String serialize(UserRegisteredEvent event) {
		try {
			return objectMapper.writeValueAsString(event);
		} catch (Exception e) {
			throw new IllegalStateException("UserRegisteredEvent 직렬화 실패", e);
		}
	}
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `./gradlew test --tests "ai.devpath.platform.auth.UserRegistrationServiceTest"`
Expected: PASS — 신규 가입 시 user+identity+profile+outbox(1행), 재호출 시 동일 user·이벤트 미발생.

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/platform/auth/UserRegistrationService.java src/test/java/ai/devpath/platform/auth/UserRegistrationServiceTest.java
git commit -m "feat(auth): 사용자 upsert + UserRegisteredEvent outbox 기록(@Transactional)"
```

---

### Task 7: RefreshCookies + SecurityConfig FilterChain (oauth2Login + resource server)

refresh 쿠키 유틸과, OAuth2 로그인 + JWT 리소스서버를 함께 구성하는 `SecurityFilterChain`. 보호 경로 미인증 401·공개 경로 통과를 통합 검증.

**Files:**
- Create: `auth/RefreshCookies.java`
- Modify: `config/SecurityConfig.java`(FilterChain + 성공핸들러 주입 빈)
- Create(test): `src/test/java/ai/devpath/platform/config/SecurityFilterChainTest.java`

**Interfaces:**
- Consumes: `JwtDecoder`(Task 3), `OAuth2LoginSuccessHandler`(Task 8), `AuthProperties`.
- Produces:
  - `RefreshCookies.create(String token): ResponseCookie` — name `refresh_token`, HttpOnly, Secure=props, SameSite=props, Path `/`, MaxAge=refreshTtl, Domain(있으면).
  - `RefreshCookies.clear(): ResponseCookie` — 동일 name, MaxAge 0.
  - `RefreshCookies.COOKIE_NAME = "refresh_token"`.
  - `SecurityConfig.securityFilterChain(HttpSecurity, OAuth2LoginSuccessHandler)` — 공개: `/oauth2/**`,`/login/**`,`/auth/refresh`,`/actuator/health`; 그 외 authenticated. `oauth2Login`(successHandler 지정), `oauth2ResourceServer(o->o.jwt(...))`, csrf disable(API+쿠키 stateless), session은 oauth2Login 위해 기본 유지.

- [ ] **Step 1: 실패 테스트 작성** — `config/SecurityFilterChainTest.java`:

```java
package ai.devpath.platform.config;

import ai.devpath.platform.auth.jwt.JwtService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class SecurityFilterChainTest {

	@Autowired MockMvc mvc;
	@Autowired JwtService jwt;

	@Test
	void protectedEndpointWithoutTokenIs401() throws Exception {
		mvc.perform(get("/users/me")).andExpect(status().isUnauthorized());
	}

	@Test
	void protectedEndpointWithValidJwtIsNot401() throws Exception {
		String token = jwt.mintAccessToken(1L, "LEARNER");
		mvc.perform(get("/users/me").header("Authorization", "Bearer " + token))
				.andExpect(status().is(org.hamcrest.Matchers.not(401)));
	}

	@Test
	void oauthAuthorizationEndpointRedirects() throws Exception {
		mvc.perform(get("/oauth2/authorization/github")).andExpect(status().is3xxRedirection());
	}
}
```

> 참고: `/users/me` 핸들러는 Task 10에서 추가. 이 Task에서는 보안 통과 후 404가 아닌 401 여부만 핵심이므로 두 번째 테스트는 "401이 아님"으로 검증한다(핸들러 추가 후엔 200).

- [ ] **Step 2: 테스트 실패 확인**

Run: `./gradlew test --tests "ai.devpath.platform.config.SecurityFilterChainTest"`
Expected: FAIL — FilterChain/`RefreshCookies`/성공핸들러 빈 없음(컴파일 또는 보안 기본동작 불일치).

- [ ] **Step 3: RefreshCookies + FilterChain 작성**

`auth/RefreshCookies.java`:
```java
package ai.devpath.platform.auth;

import ai.devpath.platform.config.AuthProperties;
import org.springframework.http.ResponseCookie;
import org.springframework.stereotype.Component;

@Component
public class RefreshCookies {

	public static final String COOKIE_NAME = "refresh_token";
	private final AuthProperties props;

	public RefreshCookies(AuthProperties props) { this.props = props; }

	public ResponseCookie create(String token) {
		ResponseCookie.ResponseCookieBuilder b = ResponseCookie.from(COOKIE_NAME, token)
				.httpOnly(true).secure(props.isCookieSecure()).path("/")
				.maxAge(props.getRefreshTtl()).sameSite(props.getCookieSameSite());
		if (props.getCookieDomain() != null && !props.getCookieDomain().isBlank()) b.domain(props.getCookieDomain());
		return b.build();
	}

	public ResponseCookie clear() {
		ResponseCookie.ResponseCookieBuilder b = ResponseCookie.from(COOKIE_NAME, "")
				.httpOnly(true).secure(props.isCookieSecure()).path("/").maxAge(0).sameSite(props.getCookieSameSite());
		if (props.getCookieDomain() != null && !props.getCookieDomain().isBlank()) b.domain(props.getCookieDomain());
		return b.build();
	}
}
```

`config/SecurityConfig.java`에 FilterChain 추가(기존 빈 메서드 유지, 아래 메서드 추가 + import):
```java
	@org.springframework.context.annotation.Bean
	public org.springframework.security.web.SecurityFilterChain securityFilterChain(
			org.springframework.security.config.annotation.web.builders.HttpSecurity http,
			ai.devpath.platform.auth.OAuth2LoginSuccessHandler successHandler) throws Exception {
		http
			.csrf(csrf -> csrf.disable())
			.authorizeHttpRequests(authorize -> authorize
				.requestMatchers("/oauth2/**", "/login/**", "/auth/refresh", "/actuator/health").permitAll()
				.anyRequest().authenticated())
			.oauth2Login(oauth -> oauth.successHandler(successHandler))
			.oauth2ResourceServer(rs -> rs.jwt(org.springframework.security.config.Customizer.withDefaults()));
		return http.build();
	}
```

> `@EnableWebSecurity`를 `SecurityConfig`에 추가. `JwtDecoder` 빈(Task 3)이 resource server에 자동 사용된다. GitHub `ClientRegistration`은 Spring Boot가 `spring.security.oauth2.client.registration.github`(application.yml, env)로 자동 구성하므로 별도 repository 빈 불필요.

- [ ] **Step 4: 테스트 통과 확인** (Redis·PG 가동, OAuth2LoginSuccessHandler는 Task 8 — 이 Task에서 함께 생성하거나 임시 스텁 후 Task 8에서 본구현)

> 의존: 이 FilterChain은 `OAuth2LoginSuccessHandler` 빈을 주입받는다. Task 8과 함께 구현하거나, Task 8을 먼저 수행하라. 순서상 **Task 8을 Task 7보다 먼저** 진행해도 무방(상호 의존). 권장: Task 8 → Task 7 순. 

Run: `./gradlew test --tests "ai.devpath.platform.config.SecurityFilterChainTest"`
Expected: PASS — `/users/me` 무토큰 401, 유효 JWT는 비401, `/oauth2/authorization/github` 3xx.

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/platform/auth/RefreshCookies.java src/main/java/ai/devpath/platform/config/SecurityConfig.java src/test/java/ai/devpath/platform/config/SecurityFilterChainTest.java
git commit -m "feat(auth): SecurityFilterChain(oauth2Login + JWT 리소스서버) + refresh 쿠키"
```

---

### Task 8: OAuth2LoginSuccessHandler (upsert → refresh 쿠키 → SPA 리다이렉트)

OAuth2 로그인 성공 시 GitHub 사용자 속성에서 신원을 추출해 upsert하고, refresh 토큰을 발급·쿠키 설정 후 SPA로 리다이렉트한다(설계서 R1).

**Files:**
- Create: `auth/OAuth2LoginSuccessHandler.java`
- Create(test): `src/test/java/ai/devpath/platform/auth/OAuth2LoginSuccessHandlerTest.java`

**Interfaces:**
- Consumes: `UserRegistrationService`, `RefreshTokenStore`, `RefreshCookies`, `AuthProperties`.
- Produces: `OAuth2LoginSuccessHandler implements AuthenticationSuccessHandler`. `onAuthenticationSuccess`: `OAuth2AuthenticationToken`에서 `getPrincipal().getAttributes()` (`id`→providerUserId, `login`/`name`→nickname, `email`→email) 추출 → `registerOrFind` → `refreshStore.issue(userId)` → `response.addHeader(SET_COOKIE, cookie)` → redirect `${webUrl}/auth/callback`.

- [ ] **Step 1: 실패 테스트 작성** — `auth/OAuth2LoginSuccessHandlerTest.java` (핸들러 단위, mock token/response):

```java
package ai.devpath.platform.auth;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.devpath.platform.user.User;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.oauth2.client.authentication.OAuth2AuthenticationToken;
import org.springframework.security.oauth2.core.user.DefaultOAuth2User;
import org.springframework.security.core.authority.AuthorityUtils;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class OAuth2LoginSuccessHandlerTest {

	@Autowired OAuth2LoginSuccessHandler handler;

	@Test
	void onSuccessUpsertsUserSetsRefreshCookieAndRedirects() throws Exception {
		Map<String, Object> attrs = Map.of(
				"id", 99001 + (int) (System.nanoTime() % 100000),
				"login", "octocat", "name", "Octo Cat", "email", "octo@example.com");
		var principal = new DefaultOAuth2User(AuthorityUtils.createAuthorityList("ROLE_USER"), attrs, "id");
		var auth = new OAuth2AuthenticationToken(principal, principal.getAuthorities(), "github");

		HttpServletRequest req = new MockHttpServletRequest();
		MockHttpServletResponse res = new MockHttpServletResponse();

		handler.onAuthenticationSuccess(req, res, auth);

		assertEquals(302, res.getStatus());
		assertNotNull(res.getRedirectedUrl());
		String setCookie = res.getHeader("Set-Cookie");
		assertNotNull(setCookie, "refresh 쿠키 설정");
		assertTrue(setCookie.contains("refresh_token="));
		assertTrue(setCookie.contains("HttpOnly"));
	}
}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `./gradlew test --tests "ai.devpath.platform.auth.OAuth2LoginSuccessHandlerTest"`
Expected: FAIL — `OAuth2LoginSuccessHandler` 없음.

- [ ] **Step 3: 작성** — `auth/OAuth2LoginSuccessHandler.java`:

```java
package ai.devpath.platform.auth;

import ai.devpath.platform.config.AuthProperties;
import ai.devpath.platform.auth.refresh.RefreshTokenStore;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Map;
import org.springframework.http.HttpHeaders;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.client.authentication.OAuth2AuthenticationToken;
import org.springframework.security.web.authentication.AuthenticationSuccessHandler;
import org.springframework.stereotype.Component;

@Component
public class OAuth2LoginSuccessHandler implements AuthenticationSuccessHandler {

	private final UserRegistrationService registration;
	private final RefreshTokenStore refreshStore;
	private final RefreshCookies cookies;
	private final AuthProperties props;

	public OAuth2LoginSuccessHandler(UserRegistrationService registration, RefreshTokenStore refreshStore,
			RefreshCookies cookies, AuthProperties props) {
		this.registration = registration;
		this.refreshStore = refreshStore;
		this.cookies = cookies;
		this.props = props;
	}

	@Override
	public void onAuthenticationSuccess(HttpServletRequest request, HttpServletResponse response,
			Authentication authentication) throws IOException {
		OAuth2AuthenticationToken token = (OAuth2AuthenticationToken) authentication;
		String provider = token.getAuthorizedClientRegistrationId().toUpperCase();
		Map<String, Object> attrs = token.getPrincipal().getAttributes();
		String providerUserId = String.valueOf(attrs.get("id"));
		String nickname = attrs.get("name") != null ? String.valueOf(attrs.get("name")) : String.valueOf(attrs.get("login"));
		String email = attrs.get("email") != null ? String.valueOf(attrs.get("email")) : null;
		String accessToken = null; // provider access token 캡처는 OAuth2AuthorizedClient 경유(2b에서 보강); 현재 null 허용.

		var user = registration.registerOrFind(
				new UserRegistrationService.OauthUser(provider, providerUserId, email, nickname, accessToken));

		String refresh = refreshStore.issue(user.getId());
		response.addHeader(HttpHeaders.SET_COOKIE, cookies.create(refresh).toString());
		response.sendRedirect(props.getWebUrl() + "/auth/callback");
	}
}
```

> provider access token 캡처(`access_token_encrypted` 채우기)는 `OAuth2AuthorizedClientService`/`@RegisteredOAuth2AuthorizedClient` 경유가 필요해 2b에서 보강한다. 현재는 신원·암호화 경로(TokenCipher)만 결선하고 token=null 허용(컬럼 nullable).

- [ ] **Step 4: 테스트 통과 확인**

Run: `./gradlew test --tests "ai.devpath.platform.auth.OAuth2LoginSuccessHandlerTest"`
Expected: PASS — 302 리다이렉트 + `refresh_token` HttpOnly 쿠키.

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/platform/auth/OAuth2LoginSuccessHandler.java src/test/java/ai/devpath/platform/auth/OAuth2LoginSuccessHandlerTest.java
git commit -m "feat(auth): OAuth2 로그인 성공 핸들러(upsert+refresh 쿠키+SPA 리다이렉트)"
```

---

### Task 9: AuthController (/auth/refresh, /auth/logout)

`/auth/refresh`: 쿠키의 refresh를 회전하고 새 access JWT + 사용자 요약을 반환(설계서 §1.1, R1). `/auth/logout`: refresh 폐기 + 쿠키 삭제.

**Files:**
- Create: `auth/dto/LoginResponse.java`, `auth/dto/UserSummary.java`
- Create: `auth/AuthController.java`
- Create(test): `src/test/java/ai/devpath/platform/auth/AuthControllerTest.java`

**Interfaces:**
- Consumes: `RefreshTokenStore`, `JwtService`, `RefreshCookies`, `UserRepository`.
- Produces:
  - `record UserSummary(String id, String email, String nickname, String role, String onboardingStatus)` + `static of(User)`(D-9: dp_core `User` 정합).
  - `record LoginResponse(String accessToken, boolean refreshTokenCookieSet, UserSummary user)` — JSON 필드 `access_token`,`refresh_token_cookie_set`,`user`(snake_case는 `@JsonProperty`).
  - `POST /auth/refresh` → 쿠키 refresh 회전 → 새 쿠키 Set-Cookie + body `LoginResponse`(access mint). 쿠키 없거나 무효면 401.
  - `POST /auth/logout` → revoke + clear 쿠키 → 204.

- [ ] **Step 1: 실패 테스트 작성** — `auth/AuthControllerTest.java`:

```java
package ai.devpath.platform.auth;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import ai.devpath.platform.auth.refresh.RefreshTokenStore;
import ai.devpath.platform.user.User;
import ai.devpath.platform.user.UserRepository;
import jakarta.servlet.http.Cookie;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class AuthControllerTest {

	@Autowired MockMvc mvc;
	@Autowired RefreshTokenStore refreshStore;
	@Autowired UserRepository users;

	@Test
	void refreshWithValidCookieReturnsAccessTokenAndRotates() throws Exception {
		User u = new User();
		u.setEmail("r" + System.nanoTime() + "@example.com");
		u.setNickname("지수"); u.setRole("LEARNER"); u.setStatus("ACTIVE"); u.setOnboardingStatus("PENDING");
		u = users.save(u);
		String refresh = refreshStore.issue(u.getId());

		mvc.perform(post("/auth/refresh").cookie(new Cookie("refresh_token", refresh)))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.access_token").isNotEmpty())
				.andExpect(jsonPath("$.refresh_token_cookie_set").value(true))
				.andExpect(jsonPath("$.user.id").value(String.valueOf(u.getId())))
				.andExpect(jsonPath("$.user.email").value(u.getEmail()))
				.andExpect(header().exists("Set-Cookie"));
	}

	@Test
	void refreshWithoutCookieIs401() throws Exception {
		mvc.perform(post("/auth/refresh")).andExpect(status().isUnauthorized());
	}

	@Test
	void logoutClearsCookieAnd204() throws Exception {
		String refresh = refreshStore.issue(1L);
		mvc.perform(post("/auth/logout").cookie(new Cookie("refresh_token", refresh)))
				.andExpect(status().isNoContent())
				.andExpect(header().exists("Set-Cookie"));
	}
}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `./gradlew test --tests "ai.devpath.platform.auth.AuthControllerTest"`
Expected: FAIL — DTO/컨트롤러 없음.

- [ ] **Step 3: DTO + 컨트롤러 작성**

`auth/dto/UserSummary.java` (D-9: dp_core `User`와 정합 — id 문자열, email·role 포함, plan 제거):
```java
package ai.devpath.platform.auth.dto;
public record UserSummary(String id, String email, String nickname, String role, String onboardingStatus) {
	public static UserSummary of(ai.devpath.platform.user.User u) {
		return new UserSummary(String.valueOf(u.getId()), u.getEmail(), u.getNickname(), u.getRole(), u.getOnboardingStatus());
	}
}
```
`auth/dto/LoginResponse.java`:
```java
package ai.devpath.platform.auth.dto;
import com.fasterxml.jackson.annotation.JsonProperty;
public record LoginResponse(
		@JsonProperty("access_token") String accessToken,
		@JsonProperty("refresh_token_cookie_set") boolean refreshTokenCookieSet,
		UserSummary user) {}
```
`auth/AuthController.java`:
```java
package ai.devpath.platform.auth;

import ai.devpath.platform.auth.dto.LoginResponse;
import ai.devpath.platform.auth.dto.UserSummary;
import ai.devpath.platform.auth.jwt.JwtService;
import ai.devpath.platform.auth.refresh.RefreshTokenStore;
import ai.devpath.platform.user.User;
import ai.devpath.platform.user.UserRepository;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CookieValue;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/auth")
public class AuthController {

	private final RefreshTokenStore refreshStore;
	private final JwtService jwt;
	private final RefreshCookies cookies;
	private final UserRepository users;

	public AuthController(RefreshTokenStore refreshStore, JwtService jwt, RefreshCookies cookies, UserRepository users) {
		this.refreshStore = refreshStore;
		this.jwt = jwt;
		this.cookies = cookies;
		this.users = users;
	}

	@PostMapping("/refresh")
	public ResponseEntity<?> refresh(
			@CookieValue(value = RefreshCookies.COOKIE_NAME, required = false) String refreshToken,
			HttpServletResponse response) {
		var rotated = refreshToken == null ? java.util.Optional.<RefreshTokenStore.Rotated>empty() : refreshStore.rotate(refreshToken);
		if (rotated.isEmpty()) return ResponseEntity.status(401).build();

		User user = users.findById(rotated.get().userId()).orElse(null);
		if (user == null) return ResponseEntity.status(401).build();

		String access = jwt.mintAccessToken(user.getId(), user.getRole());
		response.addHeader(HttpHeaders.SET_COOKIE, cookies.create(rotated.get().newToken()).toString());
		return ResponseEntity.ok(new LoginResponse(access, true, UserSummary.of(user)));
	}

	@PostMapping("/logout")
	public ResponseEntity<Void> logout(
			@CookieValue(value = RefreshCookies.COOKIE_NAME, required = false) String refreshToken,
			HttpServletResponse response) {
		if (refreshToken != null) refreshStore.revoke(refreshToken);
		response.addHeader(HttpHeaders.SET_COOKIE, cookies.clear().toString());
		return ResponseEntity.noContent().build();
	}
}
```

> `/auth/logout`은 SecurityConfig에서 인증 필요(AUTHENTICATED)지만 쿠키 기반이라 stateless. 테스트 단순화를 위해 `/auth/logout`도 permitAll로 둘지(쿠키만으로 동작) 여부는 구현 시 SecurityConfig requestMatchers와 맞춰라 — 본 플랜은 `/auth/refresh`만 permitAll, `/auth/logout`은 인증 필요로 두되 테스트는 JWT 없이 쿠키만으로 204를 기대하므로 **`/auth/logout`도 permitAll에 추가**한다(Task 7 requestMatchers에 `/auth/logout` 포함). Task 7 수정 필요 시 함께 반영.

- [ ] **Step 4: 테스트 통과 확인**

Run: `./gradlew test --tests "ai.devpath.platform.auth.AuthControllerTest"`
Expected: PASS — refresh 200+access+회전 쿠키, 무쿠키 401, logout 204+쿠키삭제.

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/platform/auth/dto src/main/java/ai/devpath/platform/auth/AuthController.java src/main/java/ai/devpath/platform/config/SecurityConfig.java src/test/java/ai/devpath/platform/auth/AuthControllerTest.java
git commit -m "feat(auth): /auth/refresh(회전) + /auth/logout"
```

---

### Task 10: UserController (/users/me)

인증된 JWT 주체로 본인 프로필을 반환한다.

**Files:**
- Create: `user/UserController.java`
- Create(test): `src/test/java/ai/devpath/platform/user/UserControllerTest.java`

**Interfaces:**
- Consumes: `UserRepository`, JWT 인증(`@AuthenticationPrincipal Jwt` subject=userId).
- Produces: `GET /users/me` → `UserSummary`(id·email·nickname·role·onboardingStatus, D-9). 사용자 없음 시 404.

- [ ] **Step 1: 실패 테스트 작성** — `user/UserControllerTest.java`:

```java
package ai.devpath.platform.user;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import ai.devpath.platform.auth.jwt.JwtService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class UserControllerTest {

	@Autowired MockMvc mvc;
	@Autowired JwtService jwt;
	@Autowired UserRepository users;

	@Test
	void meReturnsProfileForAuthenticatedUser() throws Exception {
		User u = new User();
		u.setEmail("m" + System.nanoTime() + "@example.com");
		u.setNickname("지수"); u.setRole("LEARNER"); u.setStatus("ACTIVE"); u.setOnboardingStatus("PENDING");
		u = users.save(u);
		String token = jwt.mintAccessToken(u.getId(), "LEARNER");

		mvc.perform(get("/users/me").header("Authorization", "Bearer " + token))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.id").value(String.valueOf(u.getId())))
				.andExpect(jsonPath("$.email").value(u.getEmail()))
				.andExpect(jsonPath("$.nickname").value("지수"))
				.andExpect(jsonPath("$.role").value("LEARNER"))
				.andExpect(jsonPath("$.onboardingStatus").value("PENDING"));
	}
}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `./gradlew test --tests "ai.devpath.platform.user.UserControllerTest"`
Expected: FAIL — 컨트롤러 없음(현재 401이 아닌 404 또는 매핑 없음).

- [ ] **Step 3: 작성** — `user/UserController.java`:

```java
package ai.devpath.platform.user;

import ai.devpath.platform.auth.dto.UserSummary;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/users")
public class UserController {

	private final UserRepository users;

	public UserController(UserRepository users) { this.users = users; }

	@GetMapping("/me")
	public ResponseEntity<UserSummary> me(@AuthenticationPrincipal Jwt jwt) {
		long userId = Long.parseLong(jwt.getSubject());
		return users.findById(userId)
				.map(u -> ResponseEntity.ok(UserSummary.of(u)))
				.orElseGet(() -> ResponseEntity.notFound().build());
	}
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `./gradlew test --tests "ai.devpath.platform.user.UserControllerTest"`
Expected: PASS — JWT 인증 후 본인 프로필 200.

- [ ] **Step 5: 커밋**

```bash
git add src/main/java/ai/devpath/platform/user/UserController.java src/test/java/ai/devpath/platform/user/UserControllerTest.java
git commit -m "feat(user): GET /users/me"
```

---

### Task 11: 전체 검증 + develop PR

**Files:** 없음.

- [ ] **Step 1: 전체 빌드·테스트** (PG + Redis 가동)

Run: `cd /d/workspace/dev-path-ai/devpath-shared && docker compose up -d` (이미 가동이면 생략)
그다음: `cd /d/workspace/dev-path-ai/devpath-platform-svc && ./gradlew clean build`
Expected: BUILD SUCCESSFUL — 모든 테스트 통과(매핑·JWT·암호화·refresh·upsert·security·핸들러·auth·users).

- [ ] **Step 2: 푸시 + develop PR**

```bash
git push -u origin feat/oauth-auth-core
gh pr create --base develop --head feat/oauth-auth-core \
  --title "feat: platform-svc 인증 척추(2a) — GitHub OAuth+JWT+refresh" \
  --body "GitHub OAuth2 로그인→사용자 upsert(+UserRegisteredEvent outbox)→JWT 발급→Redis refresh 회전→/users/me. 설계서/플랜: documents/docs/superpowers/{specs,plans}/2026-06-17-md1-slice1-*. 2b(outbox 릴레이+Kafka 소비자+notifications)는 후속."
```

- [ ] **Step 3: CI 녹색 확인 후 머지(merge commit)**

Run: `gh pr checks --watch`
Expected: build 통과. (CI는 PG service container 사용. Redis는 platform CI에 service로 없을 수 있음 — 확인 필요: 없으면 ci.yml에 redis service 추가가 이 PR에 포함되어야 한다. Task 11 Step 0 참조.)

- [ ] **Step 0(선행 확인): platform CI에 Redis service** — `.github/workflows/ci.yml` build job에 postgres만 있고 redis가 없으면, Redis 의존 테스트(Task 5·6·8·9·10의 `@SpringBootTest`)가 CI에서 실패한다. ci.yml `services`에 redis 추가:

```yaml
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
```
그리고 build step env에 `REDIS_HOST: localhost` / `REDIS_PORT: 6379` 추가. 이 변경을 Task 1 또는 본 Task에 포함해 커밋.

---

## Self-Review

**1. Spec coverage (설계서 §3.2 + §5.1/5.2 대조):**
- security/oauth2-client/resource-server/redis/tink 활성화 → Task 1 ✓
- provider 추상화(github reg, google/kakao 설정 추가형) → application.yml registration(github), Boot 자동구성 ✓ (추가 provider는 yaml만)
- JPA 엔티티 매핑(ddl-auto validate) → Task 2 ✓
- JWT 발급(HMAC, R5) → Task 3 ✓
- provider 토큰 Tink 암호화 → Task 4 ✓ (캡처는 2b 보강 명시)
- Redis refresh 회전·무효화(D-2, D-7) → Task 5 ✓
- 사용자 upsert + UserRegisteredEvent outbox 동일 tx(D-5 producer 기록부) → Task 6 ✓
- SecurityFilterChain(oauth2Login + JWT 검증) → Task 7 ✓
- 성공 핸들러 upsert→쿠키→SPA 리다이렉트(R1) → Task 8 ✓
- /auth/refresh(회전)·/auth/logout → Task 9 ✓
- /users/me → Task 10 ✓
- shared main 릴리스 선행(D-6) → Task 0 ✓
- 범위 외(outbox 릴레이·Kafka·notification 소비자·notifications 테이블=2b, provider 토큰 캡처=2b) → 명시 제외 ✓

**2. Placeholder scan:** 모든 Task에 실제 코드·테스트·명령 포함. "구현 주의"는 Security 7/Tink 정확 시그니처 확정 지시(플랜 코드는 grounded 최선형) — 구현자가 컴파일 확정. TBD/추상 지시 없음.

**3. Type consistency:** `UserRegistrationService.OauthUser`(record, 5필드), `RefreshTokenStore.Rotated(long userId,String newToken)`, `LoginResponse(access_token/refresh_token_cookie_set/user)`, `UserSummary(id,nickname,onboardingStatus,plan)`, `RefreshCookies.COOKIE_NAME="refresh_token"`, `JwtService.mintAccessToken(long,String)` — 정의처와 사용처 일치. provider="GITHUB" 일관(shared CHECK).

**상호 의존 주의:** Task 7(FilterChain)은 Task 8(성공핸들러) 빈을 주입 → **Task 8을 7보다 먼저** 구현 권장. `/auth/logout` permitAll 여부는 Task 7 requestMatchers와 Task 9 테스트를 일치시킬 것(플랜은 `/auth/refresh`·`/auth/logout` 둘 다 permitAll).

## Execution Handoff

Plan complete and saved to `documents/docs/superpowers/plans/2026-06-17-md1-slice1-platform-auth-2a.md`.
