# Notification-svc Build 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `devpath-platform-svc`에 이미 구현되어 있지만 게이트웨이 라우트가 없어 도달 불가능한 디바이스 토큰 등록/인앱 알림 코드를 신규 `devpath-notification-svc`로 이관하고, 게이트웨이에 `/notifications/**` 라우트를 뚫어 모바일의 FCM 토큰 등록이 실제로 동작하게 만든다.

**Architecture:** `devpath-svc-template`을 복제해 `devpath-notification-svc`를 스캐폴딩한다. `platform-svc`의 `ai.devpath.platform.notification` 패키지(`DeviceController`·`DeviceToken`·`DeviceTokenRepository`·`DeviceRegistrationRequest`·`Notification`·`NotificationRepository`·`WelcomeNotificationConsumer`, 총 7개 main 파일 + 테스트 3개)를 그대로 새 서비스로 이관한 뒤 `platform-svc`에서 삭제한다. `device_tokens`/`notifications` 테이블은 이미 `devpath-shared`에 마이그레이션되어 있으므로(`V202606271001__device_tokens.sql`, `V202606171005__notifications.sql`) 신규 스키마 변경은 없다. 코드 이동 과정에서 `platform-svc`의 `EventPropagationIT`(outbox→Kafka→WelcomeNotificationConsumer 끝단간 테스트)를 발행측(`platform-svc`에 잔류)과 소비측(`notification-svc`로 이관)으로 분리한다.

**Tech Stack:** Java 21 · Spring Boot 4.0.7 · Gradle(Kotlin DSL) · Spring Data JPA · Spring Security(OAuth2 Resource Server, JWT/HS256) · Spring Kafka · PostgreSQL(devpath-shared 공유 스키마, 단일 인스턴스) · JUnit 5 · Mockito · Awaitility · EmbeddedKafka

## Global Constraints

- 모든 신규 작업은 각 레포의 `develop`에서 새 브랜치(`feat/*`)를 분기한다. `develop`/`main` 직접 커밋 금지(git-branch-flow). `devpath-notification-svc`는 아직 `develop`이 없으므로 Task 1에서 부트스트랩한다(아래 Task 1 참조).
- 서비스 스키마는 `devpath-shared`가 SSOT(중앙 마이그레이션). 이번 빌드는 기존 마이그레이션(`V202606271001`, `V202606171005`)을 재사용하며 **신규 마이그레이션 파일을 만들지 않는다.**
- 각 서비스 CLAUDE.md 절대조건 적용: 추측 금지(파일 직접 확인 후 행동) · Test-First(실패 테스트 먼저 작성) · 문제 발생 시 코드 분석 우선 · 결과 자화자찬 금지(검증 근거 있을 때만 완료 보고).
- **새 GitHub 레포(`DevPathAi/devpath-notification-svc`) 생성은 되돌리기 어려운 공개 리소스 생성 작업이다 — 반드시 사용자에게 명시적으로 확인받은 뒤에만 실행한다.** 이 플랜을 실행하는 에이전트는 해당 단계에서 자동 진행하지 말고 사용자 확인을 기다린다.
- 코드 이관 시 원본 동작(멱등 upsert, IDOR 방지 삭제, poison-payload skip)을 변경하지 않는다 — 패키지 경로와 그에 종속된 최소 참조만 바꾸는 순수 이동이다.

---

## Task 1: notification-svc 신규 서비스 스캐폴딩

**Files:**
- Create (신규 디렉터리 `D:\workspace\dpa\devpath-notification-svc`, `devpath-svc-template` 복제 기반):
  - `settings.gradle.kts`, `build.gradle.kts`, `.gitignore`, `.gitattributes`, `Dockerfile`, `README.md`, `CLAUDE.md`
  - `.github/workflows/ci.yml`
  - `gradlew`, `gradlew.bat`, `gradle/wrapper/gradle-wrapper.jar`, `gradle/wrapper/gradle-wrapper.properties` (템플릿에서 그대로 복사, 수정 없음)
  - `src/main/java/ai/devpath/notification/NotificationApplication.java`
  - `src/main/java/ai/devpath/notification/config/SecurityConfig.java`
  - `src/main/resources/application.yml`
  - `src/test/resources/application-test.yml`
  - `src/test/java/ai/devpath/notification/NotificationApplicationTests.java`
- Delete: 없음 (신규 레포)

**Interfaces:**
- Produces: `ai.devpath.notification.config.SecurityConfig`(리소스서버 전용 JWT 검증, `devpath.auth.jwt-secret` 프로퍼티 사용) — Task 2/3의 컨트롤러가 이 필터체인 아래에서 동작한다. `spring.kafka.consumer.group-id=devpath-notification` — Task 3의 `WelcomeNotificationConsumer`가 이 그룹으로 구독한다.

- [ ] **Step 1: devpath-svc-template 복제로 로컬 디렉터리 생성**

```bash
cp -r "D:/workspace/dpa/devpath-svc-template" "D:/workspace/dpa/devpath-notification-svc"
rm -rf "D:/workspace/dpa/devpath-notification-svc/.git"
rm -rf "D:/workspace/dpa/devpath-notification-svc/build"
rm -f "D:/workspace/dpa/devpath-notification-svc/HELP.md"
```

- [ ] **Step 2: settings.gradle.kts 작성**

`D:\workspace\dpa\devpath-notification-svc\settings.gradle.kts`:
```kotlin
rootProject.name = "notification-svc"
```

- [ ] **Step 3: build.gradle.kts 작성**

community-svc의 구성(리소스서버+JPA+Kafka+devpath-shared)을 그대로 재사용한다(신원 발급이 아닌 순수 리소스서버이므로 oauth2-client는 불필요).

`D:\workspace\dpa\devpath-notification-svc\build.gradle.kts`:
```kotlin
plugins {
	java
	id("org.springframework.boot") version "4.0.7"
	id("io.spring.dependency-management") version "1.1.7"
}

group = "ai.devpath"
version = "0.0.1-SNAPSHOT"
description = "DevPath AI notification service (device tokens, in-app notifications, retention batch)"

java {
	toolchain {
		languageVersion = JavaLanguageVersion.of(21)
	}
}

repositories {
	mavenCentral()
	maven {
		url = uri("https://maven.pkg.github.com/DevPathAi/devpath-shared")
		credentials {
			username = providers.gradleProperty("gpr.user").orElse(providers.environmentVariable("GITHUB_ACTOR")).orNull
			password = providers.gradleProperty("gpr.token").orElse(providers.environmentVariable("GITHUB_TOKEN")).orNull
		}
	}
}

dependencies {
	implementation("org.springframework.boot:spring-boot-starter-actuator")
	implementation("org.springframework.boot:spring-boot-starter-validation")
	implementation("org.springframework.boot:spring-boot-starter-webmvc")
	implementation("org.springframework.boot:spring-boot-starter-data-jpa")
	implementation("ai.devpath:devpath-shared:0.0.1-SNAPSHOT")
	runtimeOnly("org.postgresql:postgresql")
	implementation("org.springframework.boot:spring-boot-starter-security")
	implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
	implementation("org.springframework.kafka:spring-kafka")
	implementation("org.springframework.boot:spring-boot-kafka")
	compileOnly("org.projectlombok:lombok")
	annotationProcessor("org.projectlombok:lombok")
	testImplementation("org.springframework.boot:spring-boot-starter-actuator-test")
	testImplementation("org.springframework.boot:spring-boot-starter-validation-test")
	testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
	testImplementation("org.springframework.boot:spring-boot-starter-security-test")
	testImplementation("org.springframework.boot:spring-boot-starter-data-jpa-test")
	testImplementation("org.springframework.kafka:spring-kafka-test")
	testImplementation("org.awaitility:awaitility")
	testImplementation("org.springframework.boot:spring-boot-flyway")
	testImplementation("org.flywaydb:flyway-core")
	testImplementation("org.flywaydb:flyway-database-postgresql")
	testCompileOnly("org.projectlombok:lombok")
	testRuntimeOnly("org.junit.platform:junit-platform-launcher")
	testAnnotationProcessor("org.projectlombok:lombok")
}

tasks.withType<Test> {
	useJUnitPlatform()
}
```

- [ ] **Step 4: 메인 애플리케이션 클래스 작성 + 템플릿 잔재 삭제**

```bash
rm -f "D:/workspace/dpa/devpath-notification-svc/src/main/java/ai/devpath/template/SvcTemplateApplication.java"
rm -f "D:/workspace/dpa/devpath-notification-svc/src/test/java/ai/devpath/template/SvcTemplateApplicationTests.java"
rmdir "D:/workspace/dpa/devpath-notification-svc/src/main/java/ai/devpath/template" 2>/dev/null || true
rmdir "D:/workspace/dpa/devpath-notification-svc/src/test/java/ai/devpath/template" 2>/dev/null || true
```

`D:\workspace\dpa\devpath-notification-svc\src\main\java\ai\devpath\notification\NotificationApplication.java`:
```java
package ai.devpath.notification;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class NotificationApplication {

	public static void main(String[] args) {
		SpringApplication.run(NotificationApplication.class, args);
	}

}
```

`D:\workspace\dpa\devpath-notification-svc\src\test\java\ai\devpath\notification\NotificationApplicationTests.java`:
```java
package ai.devpath.notification;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class NotificationApplicationTests {

	@Test
	void contextLoads() {
	}

}
```

- [ ] **Step 5: application.yml 작성**

`D:\workspace\dpa\devpath-notification-svc\src\main\resources\application.yml`:
```yaml
spring:
  application:
    name: devpath-notification-svc
  datasource:
    url: ${DB_URL:jdbc:postgresql://localhost:5432/devpath}
    username: ${DB_USER:devpath}
    password: ${DB_PASSWORD:localdev}
    driver-class-name: org.postgresql.Driver
  jpa:
    hibernate:
      ddl-auto: validate
    properties:
      hibernate.dialect: org.hibernate.dialect.PostgreSQLDialect
  flyway:
    enabled: false   # 마이그레이션은 devpath-shared(중앙)에서 실행, 서비스는 validate만
  kafka:
    bootstrap-servers: ${KAFKA_BOOTSTRAP:localhost:9092}
    consumer:
      group-id: devpath-notification
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.apache.kafka.common.serialization.StringDeserializer
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.apache.kafka.common.serialization.StringSerializer

devpath:
  auth:
    jwt-secret: ${JWT_SECRET:test-secret-please-change-min-32-bytes-long-0123456789}

server:
  port: 8080

management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics
```

`D:\workspace\dpa\devpath-notification-svc\src\test\resources\application-test.yml`:
```yaml
devpath:
  auth:
    jwt-secret: test-secret-please-change-min-32-bytes-long-0123456789
spring:
  flyway:
    enabled: true
    locations: classpath:db/migration
```

- [ ] **Step 6: SecurityConfig 작성(community-svc 패턴 — 리소스서버 전용)**

`D:\workspace\dpa\devpath-notification-svc\src\main\java\ai\devpath\notification\config\SecurityConfig.java`:
```java
package ai.devpath.notification.config;

import java.nio.charset.StandardCharsets;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

  @Bean
  public SecretKey jwtSecretKey(
      @Value("${devpath.auth.jwt-secret:test-secret-please-change-min-32-bytes-long-0123456789}") String secret) {
    byte[] bytes = secret.getBytes(StandardCharsets.UTF_8);
    if (bytes.length < 32) {
      throw new IllegalStateException("JWT_SECRET must be >= 32 bytes (HS256), got " + bytes.length);
    }
    return new SecretKeySpec(bytes, "HmacSHA256");
  }

  @Bean
  public JwtDecoder jwtDecoder(SecretKey key) {
    return NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
  }

  @Bean
  public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
    http
        .csrf(csrf -> csrf.disable())
        .authorizeHttpRequests(authorize -> authorize
            .requestMatchers("/actuator/health").permitAll()
            .anyRequest().authenticated())
        .oauth2ResourceServer(rs -> rs.jwt(Customizer.withDefaults()));
    return http.build();
  }
}
```

- [ ] **Step 7: Dockerfile — 템플릿 그대로(수정 불필요, 내용 검증만)**

`D:\workspace\dpa\devpath-notification-svc\Dockerfile`는 복제 시 이미 존재한다. 내용이 다음과 동일한지 확인만 한다:
```dockerfile
FROM eclipse-temurin:21-jre-alpine AS runtime
RUN addgroup -S app && adduser -S app -G app
WORKDIR /app
COPY build/libs/*-SNAPSHOT.jar app.jar
USER app
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

- [ ] **Step 8: CI 워크플로 이미지 태그 수정**

`D:\workspace\dpa\devpath-notification-svc\.github\workflows\ci.yml`에서 마지막 `tags:` 블록만 수정(나머지는 템플릿과 동일):
```yaml
      - uses: docker/build-push-action@v7
        with:
          context: .
          push: true
          tags: |
            ghcr.io/devpathai/devpath-notification-svc:${{ github.sha }}
            ghcr.io/devpathai/devpath-notification-svc:main
```

- [ ] **Step 9: README.md 작성**

`D:\workspace\dpa\devpath-notification-svc\README.md`:
```markdown
# devpath-notification-svc

**DevPath AI** 알림 서비스 — FCM 디바이스 토큰 등록, 인앱 알림 인박스, 참여 촉진 배치(스트릭·주간 리포트·정체 탐지·선호 시간대 리마인더).

## 구성

- Spring Boot 4.0.x · Java 21 · Gradle (Kotlin DSL)
- 스타터: WebMVC, Actuator, Validation, JPA, Security(OAuth2 Resource Server), Kafka
- `docs/project-management/` — [workflow-dashboard](https://github.com/DevPathAi/workflow-dashboard) 동기화 대상 디렉터리

## 빌드 / 실행

```bash
./gradlew build        # 빌드 + 테스트
./gradlew bootRun      # 로컬 실행 (기본 포트 8080)
```

로컬 인프라(PostgreSQL, Kafka 등)는 [devpath-shared](https://github.com/DevPathAi/devpath-shared)의 docker-compose를 사용한다.

## 개발 규칙

- Git 규칙: [documents/09_Git_규칙_정의서](https://github.com/DevPathAi/documents/blob/main/09_Git_규칙_정의서.md)
- 코드 리뷰: [documents/12_코드_리뷰_규칙](https://github.com/DevPathAi/documents/blob/main/12_코드_리뷰_규칙.md)
- 테스트 전략: [documents/11_테스트_전략서](https://github.com/DevPathAi/documents/blob/main/11_테스트_전략서.md)
```

- [ ] **Step 10: CLAUDE.md 작성(기존 레포 표준 템플릿)**

`D:\workspace\dpa\devpath-notification-svc\CLAUDE.md`:
```markdown
# CLAUDE.md — devpath-notification-svc

> 알림 서비스 — FCM 디바이스 토큰, 인앱 알림, 참여 촉진 배치(리텐션)

## 🚫 절대 조건 — 모든 작업에 예외 없이 적용

아래 세 가지는 이 레포의 **어떤 작업에도 우선하는 최상위 규칙**이다. 개별 지시가 이를 명시적으로 면제하지 않는 한 항상 따른다.

### 1. 추측·예상 금지
- 코드·설정·동작·의존성을 **추측하지 않는다.** 모르면 파일을 읽고 명령을 실행해 사실을 확인한 뒤 행동한다.
- "아마 ~일 것이다", "보통 ~하다" 같은 가정에 기반한 변경·답변·커밋을 금지한다.
- 확인이 불가능하면 진행을 멈추고 묻는다. 모르는 것을 아는 척하지 않는다.

### 2. 테스트 코드 우선 (Test-First)
- 모든 기능 추가·수정은 **실패하는 테스트를 먼저 작성**하고, 그 테스트를 통과시키는 최소 구현을 작성한다.
- 테스트 없는 구현 변경을 금지한다. 변경 후에는 반드시 테스트를 실행해 통과를 **눈으로 확인**한다.
- 구체적 테스트·검증 명령은 아래 "빌드·테스트" 절을 따른다.

### 3. 문제 발생 시 코드 분석 우선
- 버그·테스트 실패·예상 밖 동작이 생기면 **추측으로 고치지 않는다.** 먼저 관련 코드·로그·스택트레이스를 읽어 근본 원인을 규명한다.
- 증상만 덮는 임시방편(땜질)을 금지한다. 원인을 설명할 수 있을 때만 수정한다.

### 4. 신규 작업은 무조건 신규 브랜치
- 모든 신규 작업은 시작 전 `develop`에서 **새 작업 브랜치**(`feat/*`·`fix/*`·`chore/*`·`docs/*`)를 분기해 그 위에서 진행한다. `develop`·`main` 등 공유/통합 브랜치에서 **직접 작업하지 않는다**.
- 이유: **여러 세션이 동시에 작업할 때 파일 관리 충돌을 예방**한다. 미커밋 변경을 공유 브랜치 working tree에 방치하지 않는다.

### 5. 결과를 자화자찬하지 않는다 — 항상 검증·테스트로 확인
- 작업 결과를 스스로 칭찬·과신하지 않는다. "완료했다", "문제없다"는 **검증·테스트로 확인한 근거가 있을 때만** 말한다.
- 당장 문제가 없어 보여도 **모든 작업은 항상 엄격하게 검증·테스트**해 결과를 확인한다. 검증되지 않은 성공·완료를 보고하지 않는다.

## 빌드·테스트

- 빌드: `./gradlew build`
- 테스트: `./gradlew test` (JUnit 5)
- 실행: `./gradlew bootRun` (포트 8080)
- 스택: Spring Boot 4.0.7 · Java 21 · Gradle (Kotlin DSL)
- 패키지: `ai.devpath.notification` / 메인: `NotificationApplication`

> 이 레포는 [devpath-svc-template](https://github.com/DevPathAi/devpath-svc-template)에서 파생되었다. `device`/`inbox` 모듈은 원래 `devpath-platform-svc`의 `notification` 패키지에 있던 코드를 이관한 것이다(2026-07-01).

## 도메인

| 모듈 | 역할 |
|------|------|
| device | FCM 디바이스 토큰 등록/해제 |
| inbox | 인앱 알림(웰컴 등) 저장·조회, `UserRegisteredEvent` 등 구독 |
## 공통 규칙

- Git: Conventional Commits — [documents/09_Git_규칙_정의서](https://github.com/DevPathAi/documents/blob/main/09_Git_규칙_정의서.md)
- 코드 리뷰: [documents/12_코드_리뷰_규칙](https://github.com/DevPathAi/documents/blob/main/12_코드_리뷰_규칙.md)
- 테스트 전략: [documents/11_테스트_전략서](https://github.com/DevPathAi/documents/blob/main/11_테스트_전략서.md)
- 비밀값(Claude API 키·OAuth·결제 키)은 절대 커밋하지 않는다.
- 진행 현황은 `docs/project-management/`에 기록 → [workflow-dashboard](https://devpathai.github.io/workflow-dashboard/)가 동기화.


## 🚫 서브에이전트 작업 범위 강제 (Scope Lock) — 모든 작업 공통

- 서브에이전트(Task/Agent)에 위임 시 **작업 경계를 명시적으로 못박는다**: "이 작업만 수행하고 끝나면 보고 후 정지. 다른 Task로 진행하거나 명세에 없는 코드를 임의 구현 금지. 명세 부족 시 멈추고 NEEDS_CONTEXT 보고."
- 서브에이전트는 **부여된 단일 Task의 명세만** 구현한다. 추측·즉흥(improvise) 금지.
- 위임 결과는 **컨트롤러가 직접 검증**한다(커밋 로그·파일 구조·테스트 실행). 완료 보고를 그대로 신뢰하지 않는다.
- 범위 이탈 산출물은 수용하지 말고, 미푸시면 정상 지점으로 reset 후 플랜대로 재구현한다.

## 📚 study-documents 연계 (상시 참조)

- 마스터 카탈로그: [documents/41_study-documents_연계_카탈로그.md](https://github.com/DevPathAi/documents/blob/main/41_study-documents_연계_카탈로그.md)
- 이 레포 관련 자산:
  - 스킬: `/devpath-skillpack:spring-setup` · `:domain-modeler` · `:code-reviewer` · `:complexity-analyzer` · `:test-coverage-booster` · `:error-detective` · `:postgres-mcp-tuner` · `:brooks-lint-arch`
  - Sample Codes: Spring Boot 4 JPA·분산락·SSE·Audit·WebClient (study-documents `Sample Codes/🐤 Spring_Boot_4_*`)
  - 가이드: CQRS·Query-port·MSA 디자인 패턴
```

- [ ] **Step 11: 빌드 검증**

사전 준비: `spring.flyway.enabled: true`(테스트 프로파일)와 JPA DataSource가 실제 Postgres 연결을 필요로 하므로, 먼저 로컬 인프라를 띄운다:
```bash
cd "D:/workspace/dpa/devpath-shared" && docker compose up -d
```
그 다음 빌드 실행:
```bash
cd "D:/workspace/dpa/devpath-notification-svc" && ./gradlew build
```
Expected: BUILD SUCCESSFUL, `NotificationApplicationTests.contextLoads` PASS(Flyway가 `devpath-shared`의 전체 마이그레이션을 테스트 DB에 적용한 뒤 컨텍스트가 정상 로드됨을 확인).

- [ ] **Step 12: 로컬 git 저장소 초기화 + 최초 커밋**

```bash
cd "D:/workspace/dpa/devpath-notification-svc" && git init && git add -A && git commit -m "$(cat <<'EOF'
chore: devpath-svc-template 기반 notification-svc 스캐폴딩

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 13: (사용자 확인 필요) GitHub 신규 레포 생성 + 푸시**

**이 단계는 조직 계정에 새 공개/비공개 리소스를 생성하는 되돌리기 어려운 작업이다. 실행 전 반드시 사용자에게 진행 여부를 확인받는다.** 확인 후:

```bash
gh repo create DevPathAi/devpath-notification-svc --private --description "DevPath AI notification service (device tokens, in-app notifications, retention batch)"
cd "D:/workspace/dpa/devpath-notification-svc"
git remote add origin https://github.com/DevPathAi/devpath-notification-svc.git
git branch -M main
git push -u origin main
```

- [ ] **Step 14: develop 브랜치 생성(git-branch-flow 부트스트랩)**

```bash
cd "D:/workspace/dpa/devpath-notification-svc"
git checkout -b develop
git push -u origin develop
```

이후 Task 2/3에서 `devpath-notification-svc`에 대한 작업은 전부 이 `develop`에서 `feat/*` 브랜치를 분기해 진행한다.

---

## Task 2: 디바이스 토큰 모듈 이관 (DeviceController 등)

**Files:**
- Create (notification-svc, `feat/migrate-device-tokens` 브랜치, `develop`에서 분기):
  - `src/main/java/ai/devpath/notification/device/DeviceController.java`
  - `src/main/java/ai/devpath/notification/device/DeviceToken.java`
  - `src/main/java/ai/devpath/notification/device/DeviceTokenRepository.java`
  - `src/main/java/ai/devpath/notification/device/DeviceRegistrationRequest.java`
  - `src/test/java/ai/devpath/notification/device/DeviceControllerUnitTest.java`
- Delete (platform-svc, `chore/remove-device-token-module` 브랜치, `develop`에서 분기):
  - `src/main/java/ai/devpath/platform/notification/DeviceController.java`
  - `src/main/java/ai/devpath/platform/notification/DeviceToken.java`
  - `src/main/java/ai/devpath/platform/notification/DeviceTokenRepository.java`
  - `src/main/java/ai/devpath/platform/notification/DeviceRegistrationRequest.java`
  - `src/test/java/ai/devpath/platform/notification/DeviceControllerUnitTest.java`

**Interfaces:**
- Consumes: 없음(독립 모듈, DB 테이블 `device_tokens`은 devpath-shared에 이미 존재)
- Produces: `POST /notifications/devices`(등록, AUTHENTICATED), `DELETE /notifications/devices`(본인 소유 토큰만 삭제) — Task 4의 게이트웨이 라우트가 이 엔드포인트를 가리킨다.

이 코드는 이미 platform-svc에서 검증된 채로 동작 중이므로(순수 이동), TDD의 "실패하는 테스트 먼저"는 **이관 절차의 각 단계에서 테스트가 계속 통과하는지 확인하는 것**으로 대체한다(코드 자체는 새로 설계하지 않는다).

**notification-svc 쪽 작업:**

- [ ] **Step 1: notification-svc에서 새 브랜치 생성**

```bash
cd "D:/workspace/dpa/devpath-notification-svc" && git checkout develop && git pull --ff-only && git checkout -b feat/migrate-device-tokens
```

- [ ] **Step 2: 디바이스 토큰 파일 4개 작성(패키지만 변경, 로직 동일)**

`D:\workspace\dpa\devpath-notification-svc\src\main\java\ai\devpath\notification\device\DeviceToken.java`:
```java
package ai.devpath.notification.device;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

/**
 * 사용자별 FCM 디바이스 토큰(타깃 푸시 발송용). 하드닝 트랙 C.
 * 스키마: devpath-shared {@code V202606271001__device_tokens.sql}.
 */
@Entity
@Table(name = "device_tokens")
public class DeviceToken {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@Column(name = "user_id", nullable = false)
	private Long userId;

	@Column(nullable = false)
	private String token;

	@Column(nullable = false)
	private String platform;

	@Column(name = "created_at", insertable = false, updatable = false)
	private Instant createdAt;

	// 서비스가 매 upsert마다 갱신(insert/update 모두 코드에서 설정).
	@Column(name = "updated_at", nullable = false)
	private Instant updatedAt;

	public Long getId() { return id; }
	public Long getUserId() { return userId; }
	public void setUserId(Long v) { this.userId = v; }
	public String getToken() { return token; }
	public void setToken(String v) { this.token = v; }
	public String getPlatform() { return platform; }
	public void setPlatform(String v) { this.platform = v; }
	public Instant getCreatedAt() { return createdAt; }
	public Instant getUpdatedAt() { return updatedAt; }
	public void setUpdatedAt(Instant v) { this.updatedAt = v; }
}
```

`D:\workspace\dpa\devpath-notification-svc\src\main\java\ai\devpath\notification\device\DeviceTokenRepository.java`:
```java
package ai.devpath.notification.device;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DeviceTokenRepository extends JpaRepository<DeviceToken, Long> {
	Optional<DeviceToken> findByToken(String token);
}
```

`D:\workspace\dpa\devpath-notification-svc\src\main\java\ai\devpath\notification\device\DeviceRegistrationRequest.java`:
```java
package ai.devpath.notification.device;

import com.fasterxml.jackson.annotation.JsonProperty;

/** 디바이스 토큰 등록/해제 요청 바디. */
public record DeviceRegistrationRequest(
		@JsonProperty("token") String token,
		@JsonProperty("platform") String platform) {}
```

`D:\workspace\dpa\devpath-notification-svc\src\main\java\ai\devpath\notification\device\DeviceController.java`:
```java
package ai.devpath.notification.device;

import java.time.Instant;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * FCM 디바이스 토큰 등록/해제(하드닝 트랙 C). Bearer 액세스 토큰 필요(SecurityConfig의
 * anyRequest().authenticated()). 모바일은 로그인 후 getToken() 결과를 여기에 등록한다.
 */
@RestController
@RequestMapping("/notifications/devices")
public class DeviceController {

	private final DeviceTokenRepository devices;

	public DeviceController(DeviceTokenRepository devices) {
		this.devices = devices;
	}

	/** 토큰 등록(멱등 upsert: 같은 token이면 user/platform/updated_at 갱신). */
	@PostMapping
	public ResponseEntity<Void> register(@AuthenticationPrincipal Jwt jwt,
			@RequestBody(required = false) DeviceRegistrationRequest body) {
		if (body == null || isBlank(body.token()) || isBlank(body.platform())) {
			return ResponseEntity.badRequest().build();
		}
		long userId = Long.parseLong(jwt.getSubject());
		DeviceToken dt = devices.findByToken(body.token()).orElseGet(DeviceToken::new);
		dt.setUserId(userId);
		dt.setToken(body.token());
		dt.setPlatform(body.platform());
		dt.setUpdatedAt(Instant.now());
		devices.save(dt);
		return ResponseEntity.noContent().build();
	}

	/** 토큰 해제(로그아웃/기기 해지). 없으면 무시(멱등). 본인 소유 토큰만 삭제(IDOR 방지). */
	@DeleteMapping
	public ResponseEntity<Void> unregister(@AuthenticationPrincipal Jwt jwt,
			@RequestBody(required = false) DeviceRegistrationRequest body) {
		if (body != null && !isBlank(body.token())) {
			long userId = Long.parseLong(jwt.getSubject());
			devices.findByToken(body.token())
					.filter(t -> t.getUserId() != null && t.getUserId() == userId)
					.ifPresent(devices::delete);
		}
		return ResponseEntity.noContent().build();
	}

	private static boolean isBlank(String s) {
		return s == null || s.isBlank();
	}
}
```

- [ ] **Step 3: 테스트 이관(패키지만 변경, 순수 단위테스트라 DB 불요)**

`D:\workspace\dpa\devpath-notification-svc\src\test\java\ai\devpath\notification\device\DeviceControllerUnitTest.java`:
```java
package ai.devpath.notification.device;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.oauth2.jwt.Jwt;

/** 순수 단위테스트(Spring 컨텍스트·DB 불요). 디바이스 토큰 등록/해제 upsert 로직. */
class DeviceControllerUnitTest {

	private DeviceTokenRepository repo;
	private DeviceController controller;
	private final Jwt jwt = Jwt.withTokenValue("t").header("alg", "none").subject("7").build();

	@BeforeEach
	void setUp() {
		repo = mock(DeviceTokenRepository.class);
		controller = new DeviceController(repo);
	}

	@Test
	void registerNewTokenSavesWithUserAndReturns204() {
		when(repo.findByToken("tok")).thenReturn(Optional.empty());

		ResponseEntity<Void> r = controller.register(jwt, new DeviceRegistrationRequest("tok", "ANDROID"));

		assertEquals(204, r.getStatusCode().value());
		ArgumentCaptor<DeviceToken> cap = ArgumentCaptor.forClass(DeviceToken.class);
		verify(repo).save(cap.capture());
		assertEquals(7L, cap.getValue().getUserId());
		assertEquals("tok", cap.getValue().getToken());
		assertEquals("ANDROID", cap.getValue().getPlatform());
		assertNotNull(cap.getValue().getUpdatedAt());
	}

	@Test
	void registerExistingTokenUpsertsSameRow() {
		DeviceToken existing = new DeviceToken();
		existing.setUserId(1L);
		existing.setToken("tok");
		existing.setPlatform("IOS");
		when(repo.findByToken("tok")).thenReturn(Optional.of(existing));

		controller.register(jwt, new DeviceRegistrationRequest("tok", "ANDROID"));

		verify(repo).save(existing); // 동일 행 재사용(새 행 생성 안 함)
		assertEquals(7L, existing.getUserId());
		assertEquals("ANDROID", existing.getPlatform());
	}

	@Test
	void missingFieldsBadRequest() {
		assertEquals(400, controller.register(jwt, null).getStatusCode().value());
		assertEquals(400, controller.register(jwt, new DeviceRegistrationRequest(null, "ANDROID")).getStatusCode().value());
		assertEquals(400, controller.register(jwt, new DeviceRegistrationRequest("tok", " ")).getStatusCode().value());
		verify(repo, never()).save(any());
	}

	@Test
	void unregisterDeletesOwnTokenIfPresent() {
		DeviceToken existing = new DeviceToken();
		existing.setUserId(7L); // 호출자(jwt sub=7) 소유
		when(repo.findByToken("tok")).thenReturn(Optional.of(existing));

		ResponseEntity<Void> r = controller.unregister(jwt, new DeviceRegistrationRequest("tok", null));

		assertEquals(204, r.getStatusCode().value());
		verify(repo).delete(existing);
	}

	@Test
	void unregisterDoesNotDeleteOthersToken() {
		DeviceToken othersToken = new DeviceToken();
		othersToken.setUserId(99L); // 다른 사용자 소유 → 삭제 금지(IDOR 방지)
		when(repo.findByToken("tok")).thenReturn(Optional.of(othersToken));

		ResponseEntity<Void> r = controller.unregister(jwt, new DeviceRegistrationRequest("tok", null));

		assertEquals(204, r.getStatusCode().value());
		verify(repo, never()).delete(any());
	}

	@Test
	void unregisterMissingTokenIsNoOp204() {
		ResponseEntity<Void> r = controller.unregister(jwt, null);
		assertEquals(204, r.getStatusCode().value());
		verify(repo, never()).delete(any());
	}
}
```

- [ ] **Step 4: notification-svc 테스트 실행**

```bash
cd "D:/workspace/dpa/devpath-notification-svc" && ./gradlew test --tests "ai.devpath.notification.device.*"
```
Expected: 6개 테스트 전부 PASS.

- [ ] **Step 5: notification-svc 커밋 + PR**

```bash
cd "D:/workspace/dpa/devpath-notification-svc"
git add src/main/java/ai/devpath/notification/device src/test/java/ai/devpath/notification/device
git commit -m "$(cat <<'EOF'
feat(device): platform-svc에서 디바이스 토큰 모듈 이관

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
git push -u origin feat/migrate-device-tokens
gh pr create --base develop --title "feat(device): 디바이스 토큰 모듈 이관" --body "platform-svc의 DeviceController/DeviceToken 등을 notification-svc로 이관. 로직 변경 없음(패키지 경로만 변경)."
```

**platform-svc 쪽 작업(notification-svc PR 머지 확인 후 진행):**

- [ ] **Step 6: platform-svc에서 새 브랜치 생성**

```bash
cd "D:/workspace/dpa/devpath-platform-svc" && git checkout develop && git pull --ff-only && git checkout -b chore/remove-device-token-module
```

- [ ] **Step 7: platform-svc에서 디바이스 토큰 관련 파일 삭제**

```bash
cd "D:/workspace/dpa/devpath-platform-svc"
rm src/main/java/ai/devpath/platform/notification/DeviceController.java
rm src/main/java/ai/devpath/platform/notification/DeviceToken.java
rm src/main/java/ai/devpath/platform/notification/DeviceTokenRepository.java
rm src/main/java/ai/devpath/platform/notification/DeviceRegistrationRequest.java
rm src/test/java/ai/devpath/platform/notification/DeviceControllerUnitTest.java
```

- [ ] **Step 8: platform-svc 빌드 검증(참조 누락 확인)**

```bash
cd "D:/workspace/dpa/devpath-platform-svc" && ./gradlew build
```
Expected: BUILD SUCCESSFUL. (사전 조사에서 `ai.devpath.platform.notification` 패키지를 참조하는 외부 클래스가 없음을 확인했으므로 컴파일 에러가 없어야 한다. 만약 실패하면 어떤 클래스가 삭제된 클래스를 참조하는지 에러 메시지로 근본 원인을 확인한다 — 추측으로 고치지 않는다.)

- [ ] **Step 9: platform-svc 커밋 + PR**

```bash
cd "D:/workspace/dpa/devpath-platform-svc"
git add -A
git commit -m "$(cat <<'EOF'
chore(notification): 디바이스 토큰 모듈을 notification-svc로 이관하며 제거

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
git push -u origin chore/remove-device-token-module
gh pr create --base develop --title "chore(notification): 디바이스 토큰 모듈 제거(notification-svc로 이관)" --body "devpath-notification-svc PR #<N>에서 이관 완료. 이 레포에서는 더 이상 사용하지 않음."
```

---

## Task 3: 알림 인박스 모듈 이관 (Notification/WelcomeNotificationConsumer) + 통합테스트 분리

**Files:**
- Create (notification-svc, `feat/migrate-notification-inbox` 브랜치, `develop`에서 분기):
  - `src/main/java/ai/devpath/notification/inbox/Notification.java`
  - `src/main/java/ai/devpath/notification/inbox/NotificationRepository.java`
  - `src/main/java/ai/devpath/notification/inbox/WelcomeNotificationConsumer.java`
  - `src/test/java/ai/devpath/notification/inbox/NotificationRepositoryTest.java`
  - `src/test/java/ai/devpath/notification/inbox/WelcomeNotificationConsumerTest.java`
  - `src/test/java/ai/devpath/notification/inbox/WelcomeNotificationConsumerIT.java` (신규 — embedded Kafka 끝단간 테스트, EventPropagationIT의 소비측 커버리지 대체)
- Modify (platform-svc, `chore/remove-notification-inbox-module` 브랜치, `develop`에서 분기):
  - `src/test/java/ai/devpath/platform/EventPropagationIT.java` — 소비측 검증 제거, 발행측(outbox→Kafka)만 검증하도록 축소
- Delete (platform-svc, 동일 브랜치):
  - `src/main/java/ai/devpath/platform/notification/Notification.java`
  - `src/main/java/ai/devpath/platform/notification/NotificationRepository.java`
  - `src/main/java/ai/devpath/platform/notification/WelcomeNotificationConsumer.java`
  - `src/test/java/ai/devpath/platform/notification/NotificationRepositoryTest.java`
  - `src/test/java/ai/devpath/platform/notification/WelcomeNotificationConsumerTest.java`

**Interfaces:**
- Consumes: `ai.devpath.shared.event.UserRegisteredEvent`(devpath-shared, 이미 존재) — Kafka 토픽 `user.user.registered`, platform-svc가 발행.
- Produces: `notifications` 테이블에 `WELCOME` 타입 행(1인당 1개, DB 유니크 인덱스로 멱등 보장) — 후속 빌드의 `GET /notifications/me` 조회 API가 이 데이터를 사용한다(이번 빌드 범위 아님).

**주의 — 기존 `users`/`user_id` FK 문제:** `device_tokens`/`notifications` 둘 다 `user_id BIGINT NOT NULL REFERENCES users(id)` 실물 FK가 있다. 기존 platform-svc 테스트는 FK 만족을 위해 `ai.devpath.platform.user.User`/`UserRepository`를 사용했는데, 이 클래스들은 platform-svc 소유라 notification-svc로 가져올 수 없다. 이관된 테스트에서는 `JdbcTemplate`로 최소 컬럼만 채운 raw insert로 대체한다(`users` 테이블은 `status` 외 전 컬럼이 nullable이거나 DEFAULT가 있어 `INSERT INTO users (status) VALUES ('ACTIVE')`로 충분하다 — devpath-shared `V202606150901__users_skeleton.sql` + `V202606171001__users_auth_extension.sql` 확인 완료).

**notification-svc 쪽 작업:**

- [ ] **Step 1: notification-svc에서 새 브랜치 생성(Task 2 PR 머지 후)**

```bash
cd "D:/workspace/dpa/devpath-notification-svc" && git checkout develop && git pull --ff-only && git checkout -b feat/migrate-notification-inbox
```

- [ ] **Step 2: Notification 엔티티/리포지토리 작성**

`D:\workspace\dpa\devpath-notification-svc\src\main\java\ai\devpath\notification\inbox\Notification.java`:
```java
package ai.devpath.notification.inbox;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "notifications")
public class Notification {
	@Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
	@Column(name = "user_id", nullable = false) private Long userId;
	@Column(nullable = false) private String type;
	@Column(nullable = false) private String title;
	private String body;
	@Column(name = "read_at") private Instant readAt;
	@Column(name = "created_at", nullable = false) private Instant createdAt;

	public Long getId() { return id; }
	public Long getUserId() { return userId; }
	public void setUserId(Long v) { this.userId = v; }
	public String getType() { return type; }
	public void setType(String v) { this.type = v; }
	public String getTitle() { return title; }
	public void setTitle(String v) { this.title = v; }
	public String getBody() { return body; }
	public void setBody(String v) { this.body = v; }
	public Instant getReadAt() { return readAt; }
	public void setReadAt(Instant v) { this.readAt = v; }
	public Instant getCreatedAt() { return createdAt; }
	public void setCreatedAt(Instant v) { this.createdAt = v; }
}
```

`D:\workspace\dpa\devpath-notification-svc\src\main\java\ai\devpath\notification\inbox\NotificationRepository.java`:
```java
package ai.devpath.notification.inbox;
import org.springframework.data.jpa.repository.JpaRepository;
public interface NotificationRepository extends JpaRepository<Notification, Long> {
	boolean existsByUserIdAndType(Long userId, String type);
	long countByUserId(Long userId);
}
```

- [ ] **Step 3: WelcomeNotificationConsumer 작성(consumer group을 devpath-notification으로 변경)**

`D:\workspace\dpa\devpath-notification-svc\src\main\java\ai\devpath\notification\inbox\WelcomeNotificationConsumer.java`:
```java
package ai.devpath.notification.inbox;

import ai.devpath.shared.event.UserRegisteredEvent;
import tools.jackson.databind.json.JsonMapper; // Boot 4 = Jackson 3
import java.time.Instant;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class WelcomeNotificationConsumer {

	private static final Logger log = LoggerFactory.getLogger(WelcomeNotificationConsumer.class);
	private static final String TYPE = "WELCOME";
	private final NotificationRepository notifications;
	private final JsonMapper jsonMapper;

	public WelcomeNotificationConsumer(NotificationRepository notifications, JsonMapper jsonMapper) {
		this.notifications = notifications;
		this.jsonMapper = jsonMapper;
	}

	@KafkaListener(topics = UserRegisteredEvent.EVENT_TYPE, groupId = "devpath-notification")
	public void onUserRegistered(String payload) {
		UserRegisteredEvent event;
		try {
			event = jsonMapper.readValue(payload, UserRegisteredEvent.class);
		} catch (Exception e) {
			log.warn("UserRegisteredEvent 역직렬화 실패 — 메시지 skip: {}", payload, e);
			return; // poison 무한재시도 방지(다른 소비자와 동일 skip 전략)
		}
		if (notifications.existsByUserIdAndType(event.userId(), TYPE)) return; // 베스트에포트 멱등
		Notification n = new Notification();
		n.setUserId(event.userId());
		n.setType(TYPE);
		n.setTitle("환영합니다!");
		n.setBody("DevPath AI에 가입하신 것을 환영합니다. 진단을 시작해 보세요.");
		n.setCreatedAt(Instant.now());
		try {
			notifications.save(n);
		} catch (org.springframework.dao.DataIntegrityViolationException dup) {
			// P1-4: 동시 소비 레이스 — uq_notifications_welcome_user 위반 = 이미 생성됨. 무시(멱등).
		}
	}
}
```

- [ ] **Step 4: NotificationRepositoryTest 이관(User/UserRepository 의존 → JdbcTemplate raw insert로 교체)**

`D:\workspace\dpa\devpath-notification-svc\src\test\java\ai\devpath\notification\inbox\NotificationRepositoryTest.java`:
```java
package ai.devpath.notification.inbox;

import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class NotificationRepositoryTest {

	@Autowired NotificationRepository repo;
	@Autowired JdbcTemplate jdbc;

	@Test
	void savesAndChecksExistenceByType() {
		Long userId = jdbc.queryForObject("INSERT INTO users (status) VALUES ('ACTIVE') RETURNING id", Long.class);

		Notification n = new Notification();
		n.setUserId(userId);
		n.setType("WELCOME");
		n.setTitle("환영합니다");
		n.setCreatedAt(Instant.now());
		repo.save(n);

		assertTrue(repo.existsByUserIdAndType(userId, "WELCOME"));
	}
}
```

- [ ] **Step 5: WelcomeNotificationConsumerTest 이관(동일하게 JdbcTemplate로 교체)**

`D:\workspace\dpa\devpath-notification-svc\src\test\java\ai\devpath\notification\inbox\WelcomeNotificationConsumerTest.java`:
```java
package ai.devpath.notification.inbox;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;

import tools.jackson.databind.json.JsonMapper;
import ai.devpath.shared.event.UserRegisteredEvent;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class WelcomeNotificationConsumerTest {

	@Autowired WelcomeNotificationConsumer consumer;
	@Autowired NotificationRepository notifications;
	@Autowired JdbcTemplate jdbc;
	@Autowired JsonMapper om;

	@Test
	void createsWelcomeNotificationOnceIdempotently() throws Exception {
		Long userId = jdbc.queryForObject("INSERT INTO users (status) VALUES ('ACTIVE') RETURNING id", Long.class);
		String payload = om.writeValueAsString(
				new UserRegisteredEvent(UUID.randomUUID(), Instant.now(), userId, "GITHUB", "w" + System.nanoTime() + "@example.com"));

		consumer.onUserRegistered(payload);
		consumer.onUserRegistered(payload); // 중복

		assertEquals(1, notifications.findAll().stream()
				.filter(n -> n.getUserId().equals(userId) && n.getType().equals("WELCOME")).count());
	}

	@Test
	void poisonPayloadIsSkippedWithoutThrowing() {
		// 역직렬화 불가 payload는 예외 없이 skip(다른 소비자와 동일, Kafka 무한재시도 방지).
		assertDoesNotThrow(() -> consumer.onUserRegistered("{ not-json"));
	}
}
```

- [ ] **Step 6: 신규 WelcomeNotificationConsumerIT 작성(실제 Kafka를 통한 끝단간 검증 — EventPropagationIT의 소비측 커버리지 대체)**

`D:\workspace\dpa\devpath-notification-svc\src\test\java\ai\devpath\notification\inbox\WelcomeNotificationConsumerIT.java`:
```java
package ai.devpath.notification.inbox;

import static org.awaitility.Awaitility.await;
import static org.junit.jupiter.api.Assertions.assertEquals;

import ai.devpath.shared.event.UserRegisteredEvent;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.test.context.ActiveProfiles;
import tools.jackson.databind.json.JsonMapper;

/**
 * 끝단간 통합 테스트: 실제 Kafka(embedded) 토픽에 UserRegisteredEvent를 직접 발행하면
 * WelcomeNotificationConsumer(@KafkaListener)가 실제로 구독해 notifications에 WELCOME 행을
 * 쓰는지 검증한다. platform-svc의 outbox→Kafka 발행측 검증은 platform-svc의
 * EventPropagationIT가 담당하므로(이 서비스는 소비측만 책임), 이 테스트는 발행 과정을
 * KafkaTemplate로 직접 흉내낸다.
 */
@SpringBootTest
@ActiveProfiles("test")
@EmbeddedKafka(
        partitions = 1,
        topics = {UserRegisteredEvent.EVENT_TYPE},
        bootstrapServersProperty = "spring.kafka.bootstrap-servers"
)
class WelcomeNotificationConsumerIT {

    @Autowired JdbcTemplate jdbc;
    @Autowired NotificationRepository notifications;
    @Autowired JsonMapper jsonMapper;
    @Autowired KafkaTemplate<String, String> kafka;

    @Test
    void realKafkaMessage_isConsumedIntoWelcomeNotification() throws Exception {
        Long userId = jdbc.queryForObject("INSERT INTO users (status) VALUES ('ACTIVE') RETURNING id", Long.class);

        UserRegisteredEvent event = new UserRegisteredEvent(
                UUID.randomUUID(), Instant.now(), userId, "GITHUB", "it-" + System.nanoTime() + "@example.com");
        String payload = jsonMapper.writeValueAsString(event);

        kafka.send(UserRegisteredEvent.EVENT_TYPE, String.valueOf(userId), payload).get();

        await()
                .atMost(Duration.ofSeconds(10))
                .pollInterval(Duration.ofMillis(200))
                .untilAsserted(() -> {
                    long count = notifications.findAll().stream()
                            .filter(n -> n.getUserId().equals(userId) && "WELCOME".equals(n.getType()))
                            .count();
                    assertEquals(1L, count,
                            "notifications 테이블에 userId=" + userId + " WELCOME 행이 정확히 1개여야 한다");
                });
    }
}
```

- [ ] **Step 7: notification-svc 테스트 실행**

`@SpringBootTest` 컨텍스트가 실제 Postgres 연결을 필요로 하므로, 먼저 로컬 인프라를 띄운다(이미 떠 있으면 생략):
```bash
cd "D:/workspace/dpa/devpath-shared" && docker compose up -d
```
그 다음 테스트 실행:
```bash
cd "D:/workspace/dpa/devpath-notification-svc" && ./gradlew test --tests "ai.devpath.notification.inbox.*"
```
Expected: 3개 테스트 클래스(`NotificationRepositoryTest` 1건, `WelcomeNotificationConsumerTest` 2건, `WelcomeNotificationConsumerIT` 1건 — 총 4개 `@Test` 메서드) 전부 PASS. `WelcomeNotificationConsumerIT`는 `@EmbeddedKafka`가 자체 브로커를 띄우므로 별도 Kafka 실행은 불필요하다.

- [ ] **Step 8: notification-svc 커밋 + PR**

```bash
cd "D:/workspace/dpa/devpath-notification-svc"
git add src/main/java/ai/devpath/notification/inbox src/test/java/ai/devpath/notification/inbox
git commit -m "$(cat <<'EOF'
feat(inbox): platform-svc에서 알림 인박스 모듈 이관 + 끝단간 소비 테스트 추가

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
git push -u origin feat/migrate-notification-inbox
gh pr create --base develop --title "feat(inbox): 알림 인박스 모듈 이관" --body "platform-svc의 Notification/NotificationRepository/WelcomeNotificationConsumer를 이관. EmbeddedKafka 끝단간 테스트(WelcomeNotificationConsumerIT) 신규 추가로 platform-svc EventPropagationIT의 소비측 커버리지를 대체."
```

**platform-svc 쪽 작업(notification-svc PR 머지 확인 후 진행):**

- [ ] **Step 9: platform-svc에서 새 브랜치 생성**

```bash
cd "D:/workspace/dpa/devpath-platform-svc" && git checkout develop && git pull --ff-only && git checkout -b chore/remove-notification-inbox-module
```

- [ ] **Step 10: platform-svc에서 인박스 관련 파일 삭제**

```bash
cd "D:/workspace/dpa/devpath-platform-svc"
rm src/main/java/ai/devpath/platform/notification/Notification.java
rm src/main/java/ai/devpath/platform/notification/NotificationRepository.java
rm src/main/java/ai/devpath/platform/notification/WelcomeNotificationConsumer.java
rm src/test/java/ai/devpath/platform/notification/NotificationRepositoryTest.java
rm src/test/java/ai/devpath/platform/notification/WelcomeNotificationConsumerTest.java
rmdir src/main/java/ai/devpath/platform/notification 2>/dev/null || true
rmdir src/test/java/ai/devpath/platform/notification 2>/dev/null || true
```

- [ ] **Step 11: EventPropagationIT를 발행측 검증으로 축소**

`D:\workspace\dpa\devpath-platform-svc\src\test\java\ai\devpath\platform\EventPropagationIT.java`의 전체 내용을 다음으로 교체:
```java
package ai.devpath.platform;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import ai.devpath.platform.outbox.OutboxEntry;
import ai.devpath.platform.outbox.OutboxRepository;
import ai.devpath.platform.outbox.OutboxRelay;
import ai.devpath.platform.user.User;
import ai.devpath.platform.user.UserRepository;
import ai.devpath.shared.event.UserRegisteredEvent;
import tools.jackson.databind.json.JsonMapper;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.test.context.ActiveProfiles;

/**
 * 통합 테스트: outbox 1행 → relayOnce() → Kafka 발행까지 검증한다(발행측만).
 *
 * 이전에는 WelcomeNotificationConsumer까지 끝단간으로 검증했으나, 해당 컨슈머는
 * devpath-notification-svc로 이관되었다(2026-07-01). 소비측 커버리지는 그 레포의
 * WelcomeNotificationConsumerIT가 담당한다 — 이 테스트는 발행측(outbox→Kafka)만 책임진다.
 *
 * EmbeddedKafka가 실제 브로커 역할을 하며 bootstrapServersProperty로
 * spring.kafka.bootstrap-servers를 오버라이드한다. relay가 실제로 이 브로커에
 * publish하므로 브로커 자체는 여전히 필요하다.
 */
@SpringBootTest
@ActiveProfiles("test")
@EmbeddedKafka(
        partitions = 1,
        topics = {"user.user.registered"},
        bootstrapServersProperty = "spring.kafka.bootstrap-servers"
)
class EventPropagationIT {

    @Autowired UserRepository users;
    @Autowired OutboxRepository outbox;
    @Autowired OutboxRelay relay;
    @Autowired JsonMapper jsonMapper;

    @Test
    void outboxRelay_publishesUserRegisteredEvent() throws Exception {
        // 1. FK 만족용 실제 user 저장
        User user = new User();
        user.setEmail("it-" + System.nanoTime() + "@example.com");
        user.setNickname("통합테스트유저");
        user.setRole("LEARNER");
        user.setStatus("ACTIVE");
        user.setOnboardingStatus("PENDING");
        user = users.save(user);
        final Long userId = user.getId();

        // 2. UserRegisteredEvent payload를 직렬화해 outbox에 저장
        UserRegisteredEvent event = new UserRegisteredEvent(
                UUID.randomUUID(), Instant.now(), userId, "GITHUB", user.getEmail());
        String payload = jsonMapper.writeValueAsString(event);

        OutboxEntry entry = new OutboxEntry();
        entry.setAggregateType("user");
        entry.setAggregateId(String.valueOf(userId));
        entry.setEventType(UserRegisteredEvent.EVENT_TYPE);
        entry.setPayload(payload);
        entry.setCreatedAt(Instant.now());
        outbox.save(entry);

        // 3. relay가 outbox 행을 Kafka에 발행
        int published = relay.relayOnce();
        assertEquals(1, published, "relay는 1행을 발행해야 한다");

        // 4. 발행 성공 여부는 outbox 행의 published_at으로 검증(소비측은 더 이상 이 레포 책임 아님)
        OutboxEntry saved = outbox.findById(entry.getId()).orElseThrow();
        assertNotNull(saved.getPublishedAt(), "발행 성공 시 published_at이 채워져야 한다");
    }
}
```

- [ ] **Step 12: platform-svc 빌드 + 테스트 검증**

```bash
cd "D:/workspace/dpa/devpath-platform-svc" && ./gradlew build
```
Expected: BUILD SUCCESSFUL. `EventPropagationIT.outboxRelay_publishesUserRegisteredEvent` PASS. 삭제된 클래스를 참조하는 컴파일 에러가 없어야 한다(사전 조사에서 외부 참조 없음을 확인했음).

- [ ] **Step 13: platform-svc 커밋 + PR**

```bash
cd "D:/workspace/dpa/devpath-platform-svc"
git add -A
git commit -m "$(cat <<'EOF'
chore(notification): 알림 인박스 모듈을 notification-svc로 이관하며 제거

EventPropagationIT를 발행측(outbox→Kafka) 검증으로 축소. 소비측 커버리지는
devpath-notification-svc의 WelcomeNotificationConsumerIT로 이동.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
git push -u origin chore/remove-notification-inbox-module
gh pr create --base develop --title "chore(notification): 알림 인박스 모듈 제거(notification-svc로 이관)" --body "devpath-notification-svc PR #<N>에서 이관 완료. EventPropagationIT는 발행측만 검증하도록 축소."
```

---

## Task 4: 게이트웨이 /notifications/** 라우트 추가

**Files:**
- Modify: `devpath-gateway/src/main/resources/application.yml`
- Modify: `devpath-gateway/src/test/resources/application-test.yml`
- Modify: `devpath-gateway/src/test/java/ai/devpath/gateway/RouteConfigTest.java`
- Create: `devpath-gateway/src/test/java/ai/devpath/gateway/NotificationRouteTest.java`

**Interfaces:**
- Consumes: Task 2에서 만든 notification-svc의 `POST /notifications/devices`
- Produces: 게이트웨이 라우트 id `notification`, 환경변수 `NOTIFICATION_URI`(기본값 `http://localhost:8088`)

(devpath-gateway는 이미 `develop`이 있으므로 정상 플로우로 진행)

- [ ] **Step 1: 새 브랜치 생성**

```bash
cd "D:/workspace/dpa/devpath-gateway" && git checkout develop && git pull --ff-only && git checkout -b feat/notification-route
```

- [ ] **Step 2: 실패하는 테스트 먼저 작성 — RouteConfigTest에 라우트 존재 검증 추가**

`D:\workspace\dpa\devpath-gateway\src\test\java\ai\devpath\gateway\RouteConfigTest.java`의 기존 마지막 테스트(`aiMentorPathMatchesAiReviewRoute`) 뒤에 다음 2개 테스트를 추가:
```java
	@Test
	void notificationRouteIsConfigured() {
		StepVerifier.create(routes.getRoutes().map(r -> r.getId()).filter(id -> id.equals("notification")))
			.expectNext("notification").verifyComplete();
	}

	@Test
	void notificationDevicesPathMatchesRoute() {
		ServerWebExchange exchange =
			MockServerWebExchange.from(MockServerHttpRequest.post("/notifications/devices").build());
		Route notification = routes.getRoutes()
			.filter(r -> r.getId().equals("notification"))
			.blockFirst();
		assertThat(notification).isNotNull();
		StepVerifier.create(notification.getPredicate().apply(exchange))
			.expectNext(true).verifyComplete();
	}
```
(닫는 `}`는 클래스 마지막에 이미 있으므로 그 앞에 삽입한다.)

- [ ] **Step 3: 테스트 실행 → 실패 확인**

```bash
cd "D:/workspace/dpa/devpath-gateway" && ./gradlew test --tests "ai.devpath.gateway.RouteConfigTest"
```
Expected: FAIL — `notificationRouteIsConfigured`, `notificationDevicesPathMatchesRoute` 둘 다 라우트가 없어 실패(`verifyComplete()` 전에 `expectNext` 불만족 또는 timeout).

- [ ] **Step 4: application.yml에 라우트 추가**

`D:\workspace\dpa\devpath-gateway\src\main\resources\application.yml`의 `routes:` 리스트에 `community` 라우트 다음, `lcs` 라우트 앞에 삽입:
```yaml
            - id: notification
              uri: ${NOTIFICATION_URI:http://localhost:8088}
              predicates:
                - Path=/notifications/**
```
전체 routes 블록은 다음과 같이 된다:
```yaml
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
            - id: ai-review
              uri: ${AI_SVC_URI:http://localhost:8084}
              predicates:
                - Path=/reviews/**,/ai-mentor/**
            - id: community
              uri: ${COMMUNITY_SVC_URI:http://localhost:8086}
              predicates:
                - Path=/community/**
            - id: notification
              uri: ${NOTIFICATION_URI:http://localhost:8088}
              predicates:
                - Path=/notifications/**
            - id: lcs
              uri: ${LCS_SVC_URI:http://localhost:8087}
              predicates:
                - Path=/lcs/**
```

- [ ] **Step 5: application-test.yml에도 동일 라우트 추가**

`D:\workspace\dpa\devpath-gateway\src\test\resources\application-test.yml`의 `routes:` 리스트도 동일하게 `community`와 `lcs` 사이에 추가:
```yaml
            - id: notification
              uri: ${NOTIFICATION_URI:http://localhost:8088}
              predicates:
                - Path=/notifications/**
```

- [ ] **Step 6: 테스트 재실행 → 통과 확인**

```bash
cd "D:/workspace/dpa/devpath-gateway" && ./gradlew test --tests "ai.devpath.gateway.RouteConfigTest"
```
Expected: PASS (전체 9개 테스트).

- [ ] **Step 7: NotificationRouteTest 작성(CommunityRouteTest와 동일 패턴)**

`D:\workspace\dpa\devpath-gateway\src\test\java\ai\devpath\gateway\NotificationRouteTest.java`:
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
class NotificationRouteTest {

  @LocalServerPort int port;

  @MockitoBean ReactiveJwtDecoder jwtDecoder;

  WebTestClient web;

  @BeforeEach
  void setUp() {
    web = WebTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    when(jwtDecoder.decode("test-token")).thenReturn(Mono.just(jwt()));
  }

  @Test
  void notificationDevicesRequireJwt() {
    web.post().uri("/notifications/devices").exchange()
        .expectStatus().isUnauthorized();
  }

  @Test
  void authenticatedNotificationRequestMatchesRoute() {
    web.post().uri("/notifications/devices")
        .header(HttpHeaders.AUTHORIZATION, "Bearer test-token")
        .exchange()
        .expectStatus().value(NotificationRouteTest::assertGatewayMatchedRoute);
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

- [ ] **Step 8: 전체 게이트웨이 테스트 실행**

```bash
cd "D:/workspace/dpa/devpath-gateway" && ./gradlew test
```
Expected: BUILD SUCCESSFUL, 전체 테스트 PASS(`NotificationRouteTest` 2건 포함).

- [ ] **Step 9: 커밋 + PR**

```bash
cd "D:/workspace/dpa/devpath-gateway"
git add src/main/resources/application.yml src/test/resources/application-test.yml src/test/java/ai/devpath/gateway/RouteConfigTest.java src/test/java/ai/devpath/gateway/NotificationRouteTest.java
git commit -m "$(cat <<'EOF'
feat(gateway): notification-svc /notifications/** 라우트 추가

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
git push -u origin feat/notification-route
gh pr create --base develop --title "feat(gateway): notification-svc 라우트 추가" --body "notification-svc(devpath-notification-svc)로 향하는 /notifications/** 라우트 추가. 모바일 DeviceRegistrar가 이제 실제로 게이트웨이를 통해 도달 가능."
```

---

## 완료 후 확인

Task 1~4가 모두 머지되면:
- 모바일 앱의 `DeviceRegistrar.register()` → 게이트웨이 `/notifications/devices` → notification-svc `DeviceController` 경로가 실제로 동작한다(수동 curl 또는 모바일 앱으로 확인 권장).
- platform-svc는 `user`/`github`/`outbox` 모듈만 남고 `notification` 모듈은 완전히 제거된 상태가 된다.
- 다음 빌드(Build 2 이후, [2026-07-01-md3-retention-batch-design.md](../specs/2026-07-01-md3-retention-batch-design.md) 참조)에서 notification-svc에 `user_notification_prefs`/`weekly_report` 테이블(신규 Flyway 마이그레이션 필요)과 스트릭/정체탐지 컨슈머를 추가한다.
