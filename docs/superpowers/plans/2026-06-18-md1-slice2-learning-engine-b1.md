# 슬라이스 #2 빌드 B-1 — learning-svc 진단 엔진 + 회원 API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** devpath-learning-svc에 진단 도메인(JPA 엔티티/리포지토리), 자체 JWT 검증 시큐리티, 순수 적응형 진단 엔진, 회원용 진단 API(start/next/answer/complete/result)를 구현한다. (guest/Redis·이벤트 발행·claim·시드는 빌드 B-2.)

**Architecture:** 슬라이스 #1 platform-svc 패턴 재사용 — 각 도메인 서비스가 동일 HS256 JWT를 oauth2ResourceServer로 자체 검증하고 `@AuthenticationPrincipal Jwt`의 `subject`에서 userId를 얻는다. 적응형 엔진은 저장소·전송과 무관한 순수 도메인 객체로 분리해 단위 테스트한다(회원=DB, guest=Redis 공유 — guest는 B-2). DB 스키마는 빌드 A(shared) 마이그레이션을 test 프로파일 Flyway로 적용.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Spring Web MVC · Spring Data JPA · Spring Security(oauth2 resource server, HS256) · PostgreSQL 17 · JUnit 5 · `ai.devpath:devpath-shared`(빌드 A 릴리스).

## Global Constraints

- 레포 절대조건: 추측 금지 · **테스트 우선** · 문제 시 코드 분석. (devpath-learning-svc/CLAUDE.md)
- 브랜치 전략: develop 분기 → develop PR, CI 녹색 후 merge commit. main 직접 금지.
- **선행**: 빌드 A가 devpath-shared develop→**main 릴리스(publish)** 완료되어 새 마이그레이션(question_bank 등)과 `AssessmentCompletedEvent`가 GitHub Packages에 있어야 한다. 로컬은 shared 캐시 purge 후 `--refresh-dependencies`.
- **Spring Boot 4 = Jackson 3**(`tools.jackson.databind.json.JsonMapper`, ObjectMapper 빈 미등록). 테스트 슬라이스/Flyway/Kafka autoconfigure **모듈 분리**: `@DataJpaTest`=`org.springframework.boot.data.jpa.test.autoconfigure`, `@AutoConfigureMockMvc`=`org.springframework.boot.webmvc.test.autoconfigure`, TestEntityManager=`org.springframework.boot.jpa.test.autoconfigure`, Flyway autoconfig 모듈=`org.springframework.boot:spring-boot-flyway`. mock 빈 `@MockitoBean`.
- **서비스 테스트 DB 스키마**: test 프로파일 Flyway로 shared jar `classpath:db/migration` 적용(main은 `flyway.enabled:false`로 validate만). 모든 `@SpringBootTest`/JPA 슬라이스에 `@ActiveProfiles("test")`.
- 인증 모델: gateway가 엣지 JWT 검증 + Authorization 헤더 전달, learning-svc도 **동일 JWT_SECRET(HS256)로 자체 검증**(iss/aud 미검증, 서명+만료만). userId=`jwt.getSubject()`.
- track enum: `BACKEND_SPRING, FRONTEND_REACT, MOBILE_FLUTTER, DEVOPS, FULLSTACK`. bloom: `REMEMBER, UNDERSTAND, APPLY, ANALYZE, EVALUATE, CREATE`. level: `JUNIOR, MID, SENIOR`.
- 적응형 엔진 확정값(설계서 §4): 시작 난이도 0.3, 정답 +0.1/오답 −0.05(clamp [0,1]), 고정 15문항, skip=난이도 무변동·점수 제외, θ=정답(non-skip) difficulty 평균(없으면 0) → <0.4 JUNIOR / 0.4–0.7 MID / >0.7 SENIOR.
- 패키지 루트: `ai.devpath.learning`. 진단 도메인은 `ai.devpath.learning.assessment` 하위.

---

## File Structure

- Modify: `build.gradle.kts` — security 의존성 활성화(+test)
- Modify: `src/main/resources/application.yml` — JWT_SECRET 프로퍼티, test 프로파일 Flyway
- Create: `src/test/resources/application-test.yml` — test 프로파일(Flyway enabled, ddl-auto none)
- Create: `src/main/java/ai/devpath/learning/config/SecurityConfig.java` — oauth2 resource server(HS256)
- Create: `src/main/java/ai/devpath/learning/assessment/QuestionBank.java` (+Repository) — 문항 엔티티
- Create: `.../assessment/Assessment.java` (+Repository) — 진단 세션 엔티티
- Create: `.../assessment/AssessmentItem.java` (+Repository) — 출제·응답 항목
- Create: `.../assessment/AssessmentResult.java` (+Repository) — 결과
- Create: `.../assessment/engine/AdaptiveEngine.java` — 순수 적응형 엔진
- Create: `.../assessment/engine/EngineModels.java` — 엔진 입출력 record(또는 개별 파일)
- Create: `.../assessment/AssessmentService.java` — 회원 진단 유스케이스(DB)
- Create: `.../assessment/AssessmentController.java` — 회원 REST 엔드포인트
- Create: `.../assessment/dto/*.java` — 요청/응답 DTO

---

## Task 1: 시큐리티 의존성 활성화 + JWT 리소스 서버

**Files:**
- Modify: `build.gradle.kts`
- Modify: `src/main/resources/application.yml`
- Create: `src/main/java/ai/devpath/learning/config/SecurityConfig.java`
- Create: `src/test/java/ai/devpath/learning/config/SecurityConfigTest.java`

**Interfaces:**
- Produces: `SecurityConfig` 빈(`JwtDecoder` HS256, `SecurityFilterChain`). 공개경로 `/onboarding/assessments/guest/**`(B-2), `/actuator/health`. 그 외 `/onboarding/assessments/**`는 authenticated. 컨트롤러는 `@AuthenticationPrincipal Jwt`에서 `jwt.getSubject()`로 userId 획득.

- [ ] **Step 1: build.gradle.kts에 security 의존성 추가**

`dependencies` 블록에서 주석을 해제/추가:

```kotlin
	implementation("org.springframework.boot:spring-boot-starter-security")
	implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
	testImplementation("org.springframework.boot:spring-boot-starter-security-test")
```

- [ ] **Step 2: application.yml에 JWT 프로퍼티 추가**

`src/main/resources/application.yml`의 최상위(`server:` 위)에 추가:

```yaml
devpath:
  auth:
    jwt-secret: ${JWT_SECRET:test-secret-please-change-min-32-bytes-long-0123456789}
```

- [ ] **Step 3: 시큐리티 통합 실패 테스트 작성**

`SecurityConfigTest.java`:

```java
package ai.devpath.learning.config;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class SecurityConfigTest {

  @Autowired MockMvc mvc;

  @Test
  void healthIsPublic() throws Exception {
    mvc.perform(get("/actuator/health")).andExpect(status().isOk());
  }

  @Test
  void protectedAssessmentRequiresAuth() throws Exception {
    mvc.perform(get("/onboarding/assessments/1/next")).andExpect(status().isUnauthorized());
  }
}
```

- [ ] **Step 4: 테스트 실패 확인**

```bash
./gradlew test --tests ai.devpath.learning.config.SecurityConfigTest
```
Expected: FAIL(컴파일 또는 시큐리티 미구성 — 401 대신 다른 응답/에러).

- [ ] **Step 5: SecurityConfig 구현**

`SecurityConfig.java` (platform-svc SecurityConfig 패턴, oauth2Login 제외):

```java
package ai.devpath.learning.config;

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
            .requestMatchers("/onboarding/assessments/guest/**", "/actuator/health").permitAll()
            .anyRequest().authenticated())
        .oauth2ResourceServer(rs -> rs.jwt(Customizer.withDefaults()));
    return http.build();
  }
}
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
./gradlew test --tests ai.devpath.learning.config.SecurityConfigTest
```
Expected: PASS (health 200, 보호경로 401).

- [ ] **Step 7: 커밋**

```bash
git add build.gradle.kts src/main/resources/application.yml \
        src/main/java/ai/devpath/learning/config/SecurityConfig.java \
        src/test/java/ai/devpath/learning/config/SecurityConfigTest.java
git commit -m "feat(security): learning-svc JWT 리소스 서버(HS256) + 공개/보호 경로"
```

---

## Task 2: test 프로파일 Flyway + 진단 JPA 엔티티 4개 + 리포지토리

**Files:**
- Create: `src/test/resources/application-test.yml`
- Modify: `build.gradle.kts` (test에 flyway autoconfig)
- Create: `.../assessment/QuestionBank.java`, `QuestionBankRepository.java`
- Create: `.../assessment/Assessment.java`, `AssessmentRepository.java`
- Create: `.../assessment/AssessmentItem.java`, `AssessmentItemRepository.java`
- Create: `.../assessment/AssessmentResult.java`, `AssessmentResultRepository.java`
- Create: `src/test/java/ai/devpath/learning/assessment/AssessmentJpaTest.java`

**Interfaces:**
- Consumes: 빌드 A 마이그레이션(question_bank/assessments/assessment_items/assessment_results), shared jar `classpath:db/migration`.
- Produces: 엔티티 `QuestionBank`(id Long, track/questionType/content/options/answerKey/bloomLevel String, difficulty double, conceptTags String), `Assessment`(id, userId Long nullable, track, status, currentDifficulty double, bloomDistribution String, startedAt/completedAt Instant), `AssessmentItem`(id, assessmentId, questionBankId, orderNum int, answer String, isCorrect Boolean, skipped boolean, timeSpentSec Integer, presentedAt/answeredAt), `AssessmentResult`(assessmentId PK, diagnosedLevel, conceptScores/strength/weakness String, confidenceWeight Double). JSON 컬럼은 `@JdbcTypeCode(SqlTypes.JSON) String`(OutboxEntry 패턴).

- [ ] **Step 1: build.gradle.kts test Flyway autoconfig 추가**

`dependencies`에 추가(테스트에서 shared 마이그레이션 적용):

```kotlin
	testImplementation("org.springframework.boot:spring-boot-starter-data-jpa-test")
	testImplementation("org.flywaydb:flyway-core")
	testImplementation("org.flywaydb:flyway-database-postgresql")
```

> 주: Flyway autoconfigure 활성화는 test 프로파일에서만(application-test.yml). 메인 런타임은 `flyway.enabled:false` 유지.

- [ ] **Step 2: application-test.yml 작성**

`src/test/resources/application-test.yml`:

```yaml
spring:
  datasource:
    url: ${DB_URL:jdbc:postgresql://localhost:5432/devpath}
    username: ${DB_USER:devpath}
    password: ${DB_PASSWORD:localdev}
    driver-class-name: org.postgresql.Driver
  flyway:
    enabled: true
    locations: classpath:db/migration
  jpa:
    hibernate:
      ddl-auto: none
```

- [ ] **Step 3: JPA 매핑 실패 테스트 작성**

`AssessmentJpaTest.java` (실제 PG + shared 마이그레이션, `@DataJpaTest` non-embedded):

```java
package ai.devpath.learning.assessment;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.test.context.ActiveProfiles;

@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@ActiveProfiles("test")
class AssessmentJpaTest {

  @Autowired QuestionBankRepository questions;
  @Autowired AssessmentRepository assessments;

  @Test
  void persistsQuestionAndAssessment() {
    QuestionBank q = new QuestionBank();
    q.setTrack("BACKEND_SPRING");
    q.setQuestionType("MCQ");
    q.setContent("What is a bean?");
    q.setOptions("[\"a\",\"b\"]");
    q.setAnswerKey("{\"correct\":0}");
    q.setBloomLevel("UNDERSTAND");
    q.setDifficulty(0.3);
    q.setConceptTags("[\"spring-core\"]");
    QuestionBank saved = questions.save(q);
    assertThat(saved.getId()).isNotNull();

    Assessment a = new Assessment();
    a.setUserId(null); // guest 허용 확인
    a.setTrack("BACKEND_SPRING");
    a.setStatus("IN_PROGRESS");
    a.setCurrentDifficulty(0.3);
    a.setStartedAt(Instant.now());
    Assessment savedA = assessments.save(a);
    assertThat(savedA.getId()).isNotNull();
  }
}
```

- [ ] **Step 4: 테스트 실패 확인**

```bash
docker compose up -d   # learning-svc에 compose 없으면 devpath-shared의 compose 사용
./gradlew test --tests ai.devpath.learning.assessment.AssessmentJpaTest
```
Expected: FAIL(엔티티/리포지토리 미존재 컴파일 실패).

- [ ] **Step 5: QuestionBank 엔티티 + 리포지토리 작성**

`QuestionBank.java`:

```java
package ai.devpath.learning.assessment;

import jakarta.persistence.*;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "question_bank")
public class QuestionBank {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
  @Column(nullable = false) private String track;
  @Column(name = "question_type", nullable = false) private String questionType;
  @Column(nullable = false) private String content;
  @JdbcTypeCode(SqlTypes.JSON) private String options;
  @JdbcTypeCode(SqlTypes.JSON) @Column(name = "answer_key", nullable = false) private String answerKey;
  @Column(name = "bloom_level", nullable = false) private String bloomLevel;
  @Column(nullable = false) private double difficulty;
  @JdbcTypeCode(SqlTypes.JSON) @Column(name = "concept_tags") private String conceptTags;

  public Long getId() { return id; }
  public String getTrack() { return track; }
  public void setTrack(String v) { this.track = v; }
  public String getQuestionType() { return questionType; }
  public void setQuestionType(String v) { this.questionType = v; }
  public String getContent() { return content; }
  public void setContent(String v) { this.content = v; }
  public String getOptions() { return options; }
  public void setOptions(String v) { this.options = v; }
  public String getAnswerKey() { return answerKey; }
  public void setAnswerKey(String v) { this.answerKey = v; }
  public String getBloomLevel() { return bloomLevel; }
  public void setBloomLevel(String v) { this.bloomLevel = v; }
  public double getDifficulty() { return difficulty; }
  public void setDifficulty(double v) { this.difficulty = v; }
  public String getConceptTags() { return conceptTags; }
  public void setConceptTags(String v) { this.conceptTags = v; }
}
```

`QuestionBankRepository.java`:

```java
package ai.devpath.learning.assessment;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface QuestionBankRepository extends JpaRepository<QuestionBank, Long> {
  List<QuestionBank> findByTrack(String track);
}
```

- [ ] **Step 6: Assessment 엔티티 + 리포지토리 작성**

`Assessment.java`:

```java
package ai.devpath.learning.assessment;

import jakarta.persistence.*;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "assessments")
public class Assessment {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
  @Column(name = "user_id") private Long userId;
  @Column(nullable = false) private String track;
  @Column(nullable = false) private String status;
  @Column(name = "current_difficulty", nullable = false) private double currentDifficulty;
  @JdbcTypeCode(SqlTypes.JSON) @Column(name = "bloom_distribution") private String bloomDistribution;
  @Column(name = "started_at", nullable = false) private Instant startedAt;
  @Column(name = "completed_at") private Instant completedAt;

  public Long getId() { return id; }
  public Long getUserId() { return userId; }
  public void setUserId(Long v) { this.userId = v; }
  public String getTrack() { return track; }
  public void setTrack(String v) { this.track = v; }
  public String getStatus() { return status; }
  public void setStatus(String v) { this.status = v; }
  public double getCurrentDifficulty() { return currentDifficulty; }
  public void setCurrentDifficulty(double v) { this.currentDifficulty = v; }
  public String getBloomDistribution() { return bloomDistribution; }
  public void setBloomDistribution(String v) { this.bloomDistribution = v; }
  public Instant getStartedAt() { return startedAt; }
  public void setStartedAt(Instant v) { this.startedAt = v; }
  public Instant getCompletedAt() { return completedAt; }
  public void setCompletedAt(Instant v) { this.completedAt = v; }
}
```

`AssessmentRepository.java`:

```java
package ai.devpath.learning.assessment;

import org.springframework.data.jpa.repository.JpaRepository;

public interface AssessmentRepository extends JpaRepository<Assessment, Long> {
}
```

- [ ] **Step 7: AssessmentItem 엔티티 + 리포지토리 작성**

`AssessmentItem.java`:

```java
package ai.devpath.learning.assessment;

import jakarta.persistence.*;
import java.time.Instant;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "assessment_items")
public class AssessmentItem {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;
  @Column(name = "assessment_id", nullable = false) private Long assessmentId;
  @Column(name = "question_bank_id", nullable = false) private Long questionBankId;
  @Column(name = "order_num", nullable = false) private int orderNum;
  @Column(name = "presented_at", nullable = false) private Instant presentedAt;
  @Column(name = "answered_at") private Instant answeredAt;
  @JdbcTypeCode(SqlTypes.JSON) private String answer;
  @Column(name = "is_correct") private Boolean isCorrect;
  @Column(nullable = false) private boolean skipped;
  @Column(name = "time_spent_sec") private Integer timeSpentSec;

  public Long getId() { return id; }
  public Long getAssessmentId() { return assessmentId; }
  public void setAssessmentId(Long v) { this.assessmentId = v; }
  public Long getQuestionBankId() { return questionBankId; }
  public void setQuestionBankId(Long v) { this.questionBankId = v; }
  public int getOrderNum() { return orderNum; }
  public void setOrderNum(int v) { this.orderNum = v; }
  public Instant getPresentedAt() { return presentedAt; }
  public void setPresentedAt(Instant v) { this.presentedAt = v; }
  public Instant getAnsweredAt() { return answeredAt; }
  public void setAnsweredAt(Instant v) { this.answeredAt = v; }
  public String getAnswer() { return answer; }
  public void setAnswer(String v) { this.answer = v; }
  public Boolean getIsCorrect() { return isCorrect; }
  public void setIsCorrect(Boolean v) { this.isCorrect = v; }
  public boolean isSkipped() { return skipped; }
  public void setSkipped(boolean v) { this.skipped = v; }
  public Integer getTimeSpentSec() { return timeSpentSec; }
  public void setTimeSpentSec(Integer v) { this.timeSpentSec = v; }
}
```

`AssessmentItemRepository.java`:

```java
package ai.devpath.learning.assessment;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AssessmentItemRepository extends JpaRepository<AssessmentItem, Long> {
  List<AssessmentItem> findByAssessmentIdOrderByOrderNumAsc(Long assessmentId);
}
```

- [ ] **Step 8: AssessmentResult 엔티티 + 리포지토리 작성**

`AssessmentResult.java`:

```java
package ai.devpath.learning.assessment;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "assessment_results")
public class AssessmentResult {
  @Id @Column(name = "assessment_id") private Long assessmentId;
  @Column(name = "diagnosed_level", nullable = false) private String diagnosedLevel;
  @JdbcTypeCode(SqlTypes.JSON) @Column(name = "concept_scores") private String conceptScores;
  @JdbcTypeCode(SqlTypes.JSON) @Column(name = "strength_concepts") private String strengthConcepts;
  @JdbcTypeCode(SqlTypes.JSON) @Column(name = "weakness_concepts") private String weaknessConcepts;
  @Column(name = "confidence_weight") private Double confidenceWeight;

  public Long getAssessmentId() { return assessmentId; }
  public void setAssessmentId(Long v) { this.assessmentId = v; }
  public String getDiagnosedLevel() { return diagnosedLevel; }
  public void setDiagnosedLevel(String v) { this.diagnosedLevel = v; }
  public String getConceptScores() { return conceptScores; }
  public void setConceptScores(String v) { this.conceptScores = v; }
  public String getStrengthConcepts() { return strengthConcepts; }
  public void setStrengthConcepts(String v) { this.strengthConcepts = v; }
  public String getWeaknessConcepts() { return weaknessConcepts; }
  public void setWeaknessConcepts(String v) { this.weaknessConcepts = v; }
  public Double getConfidenceWeight() { return confidenceWeight; }
  public void setConfidenceWeight(Double v) { this.confidenceWeight = v; }
}
```

`AssessmentResultRepository.java`:

```java
package ai.devpath.learning.assessment;

import org.springframework.data.jpa.repository.JpaRepository;

public interface AssessmentResultRepository extends JpaRepository<AssessmentResult, Long> {
}
```

- [ ] **Step 9: 테스트 통과 확인 + 커밋**

```bash
./gradlew test --tests ai.devpath.learning.assessment.AssessmentJpaTest
```
Expected: PASS.

```bash
git add build.gradle.kts src/test/resources/application-test.yml \
        src/main/java/ai/devpath/learning/assessment/*.java \
        src/test/java/ai/devpath/learning/assessment/AssessmentJpaTest.java
git commit -m "feat(assessment): 진단 JPA 엔티티 4종 + test Flyway 프로파일"
```

---

## Task 3: 순수 적응형 엔진

**Files:**
- Create: `.../assessment/engine/AdaptiveEngine.java`
- Create: `.../assessment/engine/Difficulty.java` (난이도 전이 헬퍼) — 선택, 엔진 내 static로 둬도 됨
- Create: `src/test/java/ai/devpath/learning/assessment/engine/AdaptiveEngineTest.java`

**Interfaces:**
- Produces:
  - `AdaptiveEngine.START_DIFFICULTY = 0.3`, `TOTAL_QUESTIONS = 15`.
  - `double nextDifficulty(double current, AnswerOutcome outcome)` — outcome=CORRECT→+0.1, WRONG→−0.05, SKIP→무변동, clamp[0,1].
  - `enum AnswerOutcome { CORRECT, WRONG, SKIP }`
  - `boolean isComplete(int answeredCount)` — answeredCount >= 15.
  - `String diagnoseLevel(List<Double> correctDifficulties)` — θ=평균(빈 리스트=0) → JUNIOR/MID/SENIOR.
  - learning 서비스(Task 4)·guest(B-2)가 동일 엔진 사용.

- [ ] **Step 1: 엔진 단위 실패 테스트 작성**

`AdaptiveEngineTest.java`:

```java
package ai.devpath.learning.assessment.engine;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import java.util.List;
import org.junit.jupiter.api.Test;

class AdaptiveEngineTest {

  final AdaptiveEngine engine = new AdaptiveEngine();

  @Test
  void correctRaisesByPointOne() {
    assertThat(engine.nextDifficulty(0.3, AdaptiveEngine.AnswerOutcome.CORRECT)).isCloseTo(0.4, within(1e-9));
  }

  @Test
  void wrongLowersByPointZeroFive() {
    assertThat(engine.nextDifficulty(0.3, AdaptiveEngine.AnswerOutcome.WRONG)).isCloseTo(0.25, within(1e-9));
  }

  @Test
  void skipKeepsDifficulty() {
    assertThat(engine.nextDifficulty(0.3, AdaptiveEngine.AnswerOutcome.SKIP)).isCloseTo(0.3, within(1e-9));
  }

  @Test
  void clampsToBounds() {
    assertThat(engine.nextDifficulty(1.0, AdaptiveEngine.AnswerOutcome.CORRECT)).isEqualTo(1.0);
    assertThat(engine.nextDifficulty(0.0, AdaptiveEngine.AnswerOutcome.WRONG)).isEqualTo(0.0);
  }

  @Test
  void completesAtFifteen() {
    assertThat(engine.isComplete(14)).isFalse();
    assertThat(engine.isComplete(15)).isTrue();
  }

  @Test
  void diagnosesLevelByThreshold() {
    assertThat(engine.diagnoseLevel(List.of())).isEqualTo("JUNIOR");          // θ=0
    assertThat(engine.diagnoseLevel(List.of(0.2, 0.3))).isEqualTo("JUNIOR");  // θ=0.25
    assertThat(engine.diagnoseLevel(List.of(0.5, 0.6))).isEqualTo("MID");     // θ=0.55
    assertThat(engine.diagnoseLevel(List.of(0.8, 0.9))).isEqualTo("SENIOR");  // θ=0.85
  }
}
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
./gradlew test --tests ai.devpath.learning.assessment.engine.AdaptiveEngineTest
```
Expected: FAIL(`AdaptiveEngine` 미존재).

- [ ] **Step 3: AdaptiveEngine 구현**

`AdaptiveEngine.java`:

```java
package ai.devpath.learning.assessment.engine;

import java.util.List;
import org.springframework.stereotype.Component;

/** 순수 적응형 진단 엔진(저장소·전송 무관). 설계서 §4 확정값. */
@Component
public class AdaptiveEngine {

  public static final double START_DIFFICULTY = 0.3;
  public static final int TOTAL_QUESTIONS = 15;
  private static final double STEP_UP = 0.1;
  private static final double STEP_DOWN = 0.05;

  public enum AnswerOutcome { CORRECT, WRONG, SKIP }

  public double nextDifficulty(double current, AnswerOutcome outcome) {
    double next = switch (outcome) {
      case CORRECT -> current + STEP_UP;
      case WRONG -> current - STEP_DOWN;
      case SKIP -> current;
    };
    return Math.max(0.0, Math.min(1.0, next));
  }

  public boolean isComplete(int answeredCount) {
    return answeredCount >= TOTAL_QUESTIONS;
  }

  /** θ = 정답(non-skip) 문항 difficulty 평균(없으면 0). <0.4 JUNIOR, 0.4~0.7 MID, >0.7 SENIOR. */
  public String diagnoseLevel(List<Double> correctDifficulties) {
    double theta = correctDifficulties.isEmpty() ? 0.0
        : correctDifficulties.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);
    if (theta < 0.4) return "JUNIOR";
    if (theta <= 0.7) return "MID";
    return "SENIOR";
  }
}
```

- [ ] **Step 4: 테스트 통과 확인 + 커밋**

```bash
./gradlew test --tests ai.devpath.learning.assessment.engine.AdaptiveEngineTest
git add src/main/java/ai/devpath/learning/assessment/engine/AdaptiveEngine.java \
        src/test/java/ai/devpath/learning/assessment/engine/AdaptiveEngineTest.java
git commit -m "feat(engine): 적응형 진단 엔진(난이도 전이·종료·레벨매핑)"
```
Expected: PASS.

---

## Task 4: 회원 진단 서비스 + 컨트롤러 + DTO

> 다음 문항 선택(미출제·track·current_difficulty 최근접·결정적), 답안 채점(answer_key 비교), 결과 산출(concept_scores/strength/weakness/θ→level)을 DB 기반으로 구현하고 5개 회원 엔드포인트를 노출한다. 이벤트 발행은 B-2에서 `complete`에 결선한다(이 Task에서는 결과 저장까지).

**Files:**
- Create: `.../assessment/dto/StartAssessmentRequest.java`, `QuestionView.java`, `NextQuestionResponse.java`, `AnswerRequest.java`, `AssessmentResultView.java`
- Create: `.../assessment/NextQuestionSelector.java` (다음 문항 결정적 선택)
- Create: `.../assessment/AssessmentService.java`
- Create: `.../assessment/AssessmentController.java`
- Create: `src/test/java/ai/devpath/learning/assessment/NextQuestionSelectorTest.java`
- Create: `src/test/java/ai/devpath/learning/assessment/AssessmentControllerTest.java`

**Interfaces:**
- Consumes: `AdaptiveEngine`, 리포지토리 4종, `@AuthenticationPrincipal Jwt`(userId=subject).
- Produces:
  - `QuestionView(long id, String type, String content, String options, String bloomLevel, double difficulty)` — answer_key 미포함.
  - `NextQuestionResponse(QuestionView question, int index, int total)` (total=15).
  - `AnswerRequest(long questionId, String answer, boolean skipped, Integer timeSpentSec)`.
  - `AssessmentResultView(String diagnosedLevel, String conceptScores, String strengthConcepts, String weaknessConcepts, Double confidenceWeight)`.
  - `NextQuestionSelector.select(String track, double currentDifficulty, Set<Long> excludedIds, List<QuestionBank> pool)` → `QuestionBank`(최근접 difficulty, 동률 시 id 오름차순; 후보 없으면 null).
  - 엔드포인트: `POST /onboarding/assessments`(body track)→{assessmentId}, `GET /{id}/next`, `POST /{id}/answer`, `POST /{id}/complete`→result, `GET /{id}/result`.

- [ ] **Step 1: NextQuestionSelector 실패 테스트 작성**

`NextQuestionSelectorTest.java`:

```java
package ai.devpath.learning.assessment;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class NextQuestionSelectorTest {

  final NextQuestionSelector selector = new NextQuestionSelector();

  private QuestionBank q(long id, double difficulty) {
    QuestionBank q = new QuestionBank();
    q.setTrack("BACKEND_SPRING");
    q.setDifficulty(difficulty);
    // id는 영속화로만 부여되므로 테스트에선 리플렉션 대신 difficulty/순서로 검증
    return q;
  }

  @Test
  void picksClosestDifficultyNotExcluded() {
    var pool = List.of(q(1, 0.2), q(2, 0.35), q(3, 0.9));
    QuestionBank picked = selector.select("BACKEND_SPRING", 0.3, Set.of(), pool);
    assertThat(picked.getDifficulty()).isEqualTo(0.35);
  }

  @Test
  void returnsNullWhenAllExcluded() {
    var pool = List.<QuestionBank>of();
    assertThat(selector.select("BACKEND_SPRING", 0.3, Set.of(), pool)).isNull();
  }
}
```

> 주: id는 영속 후 부여되므로 selector는 `excludedIds`(이미 출제된 question_bank_id)를 받아 필터링하고, 남은 후보 중 |difficulty − current| 최소(동률 시 getId() 오름차순)를 고른다. 컨트롤러/서비스 레벨에서 영속 엔티티로 검증(Step 6 통합 테스트).

- [ ] **Step 2: 테스트 실패 확인**

```bash
./gradlew test --tests ai.devpath.learning.assessment.NextQuestionSelectorTest
```
Expected: FAIL(`NextQuestionSelector` 미존재).

- [ ] **Step 3: NextQuestionSelector 구현**

`NextQuestionSelector.java`:

```java
package ai.devpath.learning.assessment;

import java.util.Comparator;
import java.util.List;
import java.util.Set;
import org.springframework.stereotype.Component;

/** 다음 문항 결정적 선택: track 일치·미출제 후보 중 |difficulty-current| 최소, 동률 시 id 오름차순. */
@Component
public class NextQuestionSelector {

  public QuestionBank select(String track, double currentDifficulty, Set<Long> excludedIds, List<QuestionBank> pool) {
    return pool.stream()
        .filter(q -> track.equals(q.getTrack()))
        .filter(q -> q.getId() == null || !excludedIds.contains(q.getId()))
        .min(Comparator
            .comparingDouble((QuestionBank q) -> Math.abs(q.getDifficulty() - currentDifficulty))
            .thenComparing(q -> q.getId() == null ? Long.MAX_VALUE : q.getId()))
        .orElse(null);
  }
}
```

- [ ] **Step 4: DTO 작성**

`dto/StartAssessmentRequest.java`:

```java
package ai.devpath.learning.assessment.dto;

public record StartAssessmentRequest(String track) {}
```

`dto/QuestionView.java`:

```java
package ai.devpath.learning.assessment.dto;

public record QuestionView(long id, String type, String content, String options,
                           String bloomLevel, double difficulty) {}
```

`dto/NextQuestionResponse.java`:

```java
package ai.devpath.learning.assessment.dto;

public record NextQuestionResponse(QuestionView question, int index, int total) {}
```

`dto/AnswerRequest.java`:

```java
package ai.devpath.learning.assessment.dto;

public record AnswerRequest(long questionId, String answer, boolean skipped, Integer timeSpentSec) {}
```

`dto/AssessmentResultView.java`:

```java
package ai.devpath.learning.assessment.dto;

public record AssessmentResultView(String diagnosedLevel, String conceptScores,
                                   String strengthConcepts, String weaknessConcepts,
                                   Double confidenceWeight) {}
```

- [ ] **Step 5: AssessmentService 구현**

`AssessmentService.java` (DB 기반 회원 유스케이스; 채점·결과 산출 포함):

```java
package ai.devpath.learning.assessment;

import ai.devpath.learning.assessment.dto.*;
import ai.devpath.learning.assessment.engine.AdaptiveEngine;
import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AssessmentService {

  private final AssessmentRepository assessments;
  private final AssessmentItemRepository items;
  private final AssessmentResultRepository results;
  private final QuestionBankRepository questions;
  private final AdaptiveEngine engine;
  private final NextQuestionSelector selector;

  public AssessmentService(AssessmentRepository assessments, AssessmentItemRepository items,
      AssessmentResultRepository results, QuestionBankRepository questions,
      AdaptiveEngine engine, NextQuestionSelector selector) {
    this.assessments = assessments;
    this.items = items;
    this.results = results;
    this.questions = questions;
    this.engine = engine;
    this.selector = selector;
  }

  @Transactional
  public long start(long userId, String track) {
    Assessment a = new Assessment();
    a.setUserId(userId);
    a.setTrack(track);
    a.setStatus("IN_PROGRESS");
    a.setCurrentDifficulty(AdaptiveEngine.START_DIFFICULTY);
    a.setStartedAt(Instant.now());
    return assessments.save(a).getId();
  }

  @Transactional
  public Optional<NextQuestionResponse> next(long userId, long assessmentId) {
    Assessment a = ownedInProgress(userId, assessmentId);
    List<AssessmentItem> answered = items.findByAssessmentIdOrderByOrderNumAsc(assessmentId);
    if (engine.isComplete(answered.size())) return Optional.empty();
    Set<Long> excluded = answered.stream().map(AssessmentItem::getQuestionBankId).collect(Collectors.toSet());
    QuestionBank q = selector.select(a.getTrack(), a.getCurrentDifficulty(), excluded,
        questions.findByTrack(a.getTrack()));
    if (q == null) return Optional.empty();
    AssessmentItem item = new AssessmentItem();
    item.setAssessmentId(assessmentId);
    item.setQuestionBankId(q.getId());
    item.setOrderNum(answered.size() + 1);
    item.setPresentedAt(Instant.now());
    item.setSkipped(false);
    items.save(item);
    var view = new QuestionView(q.getId(), q.getQuestionType(), q.getContent(), q.getOptions(),
        q.getBloomLevel(), q.getDifficulty());
    return Optional.of(new NextQuestionResponse(view, answered.size() + 1, AdaptiveEngine.TOTAL_QUESTIONS));
  }

  @Transactional
  public void answer(long userId, long assessmentId, AnswerRequest req) {
    Assessment a = ownedInProgress(userId, assessmentId);
    AssessmentItem item = items.findByAssessmentIdOrderByOrderNumAsc(assessmentId).stream()
        .filter(i -> i.getQuestionBankId().equals(req.questionId()) && i.getAnsweredAt() == null)
        .findFirst().orElseThrow(() -> new IllegalArgumentException("출제되지 않았거나 이미 응답한 문항"));
    QuestionBank q = questions.findById(req.questionId()).orElseThrow();
    item.setAnsweredAt(Instant.now());
    item.setTimeSpentSec(req.timeSpentSec());
    AdaptiveEngine.AnswerOutcome outcome;
    if (req.skipped()) {
      item.setSkipped(true);
      item.setAnswer(null);
      item.setIsCorrect(null);
      outcome = AdaptiveEngine.AnswerOutcome.SKIP;
    } else {
      item.setAnswer(req.answer());
      boolean correct = Objects.equals(normalize(req.answer()), normalize(q.getAnswerKey()));
      item.setIsCorrect(correct);
      outcome = correct ? AdaptiveEngine.AnswerOutcome.CORRECT : AdaptiveEngine.AnswerOutcome.WRONG;
    }
    items.save(item);
    a.setCurrentDifficulty(engine.nextDifficulty(a.getCurrentDifficulty(), outcome));
    assessments.save(a);
  }

  @Transactional
  public AssessmentResultView complete(long userId, long assessmentId) {
    Assessment a = ownedInProgress(userId, assessmentId);
    List<AssessmentItem> all = items.findByAssessmentIdOrderByOrderNumAsc(assessmentId);
    Map<Long, QuestionBank> byId = questions.findAllById(
        all.stream().map(AssessmentItem::getQuestionBankId).collect(Collectors.toSet()))
        .stream().collect(Collectors.toMap(QuestionBank::getId, x -> x));
    List<Double> correctDifficulties = all.stream()
        .filter(i -> Boolean.TRUE.equals(i.getIsCorrect()))
        .map(i -> byId.get(i.getQuestionBankId()).getDifficulty())
        .collect(Collectors.toList());
    String level = engine.diagnoseLevel(correctDifficulties);
    long scored = all.stream().filter(i -> !i.isSkipped()).count();
    double confidence = all.isEmpty() ? 0.0 : (double) scored / all.size();

    a.setStatus("COMPLETED");
    a.setCompletedAt(Instant.now());
    assessments.save(a);

    AssessmentResult r = new AssessmentResult();
    r.setAssessmentId(assessmentId);
    r.setDiagnosedLevel(level);
    r.setConfidenceWeight(confidence);
    // concept_scores/strength/weakness 집계는 B-2 시드 데이터 기반으로 보강. 최소 결과 저장.
    results.save(r);
    return new AssessmentResultView(level, r.getConceptScores(), r.getStrengthConcepts(),
        r.getWeaknessConcepts(), confidence);
  }

  @Transactional(readOnly = true)
  public Optional<AssessmentResultView> result(long userId, long assessmentId) {
    owned(userId, assessmentId);
    return results.findById(assessmentId).map(r -> new AssessmentResultView(
        r.getDiagnosedLevel(), r.getConceptScores(), r.getStrengthConcepts(),
        r.getWeaknessConcepts(), r.getConfidenceWeight()));
  }

  private Assessment owned(long userId, long assessmentId) {
    Assessment a = assessments.findById(assessmentId)
        .orElseThrow(() -> new java.util.NoSuchElementException("assessment 없음"));
    if (a.getUserId() == null || a.getUserId() != userId) {
      throw new org.springframework.security.access.AccessDeniedException("소유자 아님");
    }
    return a;
  }

  private Assessment ownedInProgress(long userId, long assessmentId) {
    Assessment a = owned(userId, assessmentId);
    if (!"IN_PROGRESS".equals(a.getStatus())) {
      throw new IllegalStateException("진행 중 세션 아님");
    }
    return a;
  }

  private static String normalize(String json) {
    return json == null ? null : json.replaceAll("\\s+", "");
  }
}
```

> 주: concept_scores/strength/weakness 정밀 집계는 B-2(시드 데이터·concept_tags 존재 후) 보강 항목. 이 Task는 diagnosed_level·confidence·결과행 저장까지 책임진다(설계서 §11.3 정합).

- [ ] **Step 6: AssessmentController 구현**

`AssessmentController.java`:

```java
package ai.devpath.learning.assessment;

import ai.devpath.learning.assessment.dto.*;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/onboarding/assessments")
public class AssessmentController {

  private final AssessmentService service;

  public AssessmentController(AssessmentService service) { this.service = service; }

  private static long uid(Jwt jwt) { return Long.parseLong(jwt.getSubject()); }

  @PostMapping
  public ResponseEntity<Map<String, Long>> start(@AuthenticationPrincipal Jwt jwt,
      @RequestBody StartAssessmentRequest req) {
    long id = service.start(uid(jwt), req.track());
    return ResponseEntity.ok(Map.of("assessmentId", id));
  }

  @GetMapping("/{id}/next")
  public ResponseEntity<NextQuestionResponse> next(@AuthenticationPrincipal Jwt jwt, @PathVariable long id) {
    return service.next(uid(jwt), id).map(ResponseEntity::ok)
        .orElseGet(() -> ResponseEntity.noContent().build());
  }

  @PostMapping("/{id}/answer")
  public ResponseEntity<Void> answer(@AuthenticationPrincipal Jwt jwt, @PathVariable long id,
      @RequestBody AnswerRequest req) {
    service.answer(uid(jwt), id, req);
    return ResponseEntity.ok().build();
  }

  @PostMapping("/{id}/complete")
  public ResponseEntity<AssessmentResultView> complete(@AuthenticationPrincipal Jwt jwt, @PathVariable long id) {
    return ResponseEntity.ok(service.complete(uid(jwt), id));
  }

  @GetMapping("/{id}/result")
  public ResponseEntity<AssessmentResultView> result(@AuthenticationPrincipal Jwt jwt, @PathVariable long id) {
    return service.result(uid(jwt), id).map(ResponseEntity::ok)
        .orElseGet(() -> ResponseEntity.notFound().build());
  }
}
```

- [ ] **Step 7: 회원 끝단간 통합 테스트 작성(실패→통과)**

`AssessmentControllerTest.java` — 실 PG + shared 마이그레이션 + JWT mock. 문항 픽스처를 리포지토리로 적재 후 start→next→answer 루프→complete→result 검증:

```java
package ai.devpath.learning.assessment;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class AssessmentControllerTest {

  @Autowired MockMvc mvc;
  @Autowired QuestionBankRepository questions;

  private void seed() {
    for (int i = 0; i < 20; i++) {
      QuestionBank q = new QuestionBank();
      q.setTrack("BACKEND_SPRING");
      q.setQuestionType("MCQ");
      q.setContent("Q" + i);
      q.setOptions("[\"a\",\"b\"]");
      q.setAnswerKey("{\"correct\":0}");
      q.setBloomLevel("UNDERSTAND");
      q.setDifficulty(0.1 * (i % 10));
      q.setConceptTags("[\"c" + (i % 3) + "\"]");
      questions.save(q);
    }
  }

  @Test
  void memberFlowStartToResult() throws Exception {
    seed();
    var post = jwt().jwt(j -> j.subject("42"));
    String body = mvc.perform(post("/onboarding/assessments").with(post)
            .contentType(MediaType.APPLICATION_JSON).content("{\"track\":\"BACKEND_SPRING\"}"))
        .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
    long id = com.jayway.jsonpath.JsonPath.parse(body).read("$.assessmentId", Long.class);

    for (int i = 0; i < 15; i++) {
      String next = mvc.perform(get("/onboarding/assessments/" + id + "/next").with(post))
          .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
      long qid = com.jayway.jsonpath.JsonPath.parse(next).read("$.question.id", Long.class);
      mvc.perform(post("/onboarding/assessments/" + id + "/answer").with(post)
              .contentType(MediaType.APPLICATION_JSON)
              .content("{\"questionId\":" + qid + ",\"answer\":\"{\\\"correct\\\":0}\",\"skipped\":false,\"timeSpentSec\":5}"))
          .andExpect(status().isOk());
    }
    mvc.perform(get("/onboarding/assessments/" + id + "/next").with(post))
        .andExpect(status().isNoContent());
    mvc.perform(post("/onboarding/assessments/" + id + "/complete").with(post))
        .andExpect(status().isOk()).andExpect(jsonPath("$.diagnosedLevel").exists());
    mvc.perform(get("/onboarding/assessments/" + id + "/result").with(post))
        .andExpect(status().isOk()).andExpect(jsonPath("$.diagnosedLevel").exists());
  }
}
```

> `com.jayway.jsonpath`는 spring-boot-starter-test에 포함(JsonPath). 미포함 시 `testImplementation("com.jayway.jsonpath:json-path")` 추가.

- [ ] **Step 8: 테스트 통과 확인**

```bash
docker compose up -d
./gradlew test --tests ai.devpath.learning.assessment.AssessmentControllerTest --tests ai.devpath.learning.assessment.NextQuestionSelectorTest
```
Expected: PASS.

- [ ] **Step 9: 커밋**

```bash
git add src/main/java/ai/devpath/learning/assessment/ \
        src/test/java/ai/devpath/learning/assessment/NextQuestionSelectorTest.java \
        src/test/java/ai/devpath/learning/assessment/AssessmentControllerTest.java
git commit -m "feat(assessment): 회원 진단 API(start/next/answer/complete/result) + 다음문항 선택"
```

---

## Task 5: 전체 빌드 검증 + develop PR

- [ ] **Step 1: 전체 빌드·테스트**

```bash
docker compose up -d
./gradlew clean build
```
Expected: BUILD SUCCESSFUL, 전 테스트 PASS.

- [ ] **Step 2: develop PR**

작업 브랜치(`feat/slice2-learning-engine`, develop 분기) push → `gh pr create --base develop ...` → CI 녹색 후 merge commit.

> B-2(outbox/Kafka 이벤트 발행 + guest Redis 세션 + claim + 시드/concept 집계)는 별도 플랜에서 이어간다. B-1 머지 후 진행.

---

## 검토 반영 보완 (2026-06-18 리뷰 P1 — 구현 시 우선 적용)

### R-B1-1 (P1-3): `next()`는 outstanding(미응답) 문항을 재발급 — 반복 호출 안전
원안은 `next()` 호출마다 `AssessmentItem`을 생성해, 클라이언트가 `GET /next`를 반복하면 미응답 문항이 누적되고 진행률·종료 판정이 깨진다. → **미응답 문항이 있으면 새로 만들지 않고 그대로 반환**, 종료 판정은 "응답완료 수" 기준.

Task 4 `AssessmentService.next()`를 교체:

```java
  @Transactional
  public Optional<NextQuestionResponse> next(long userId, long assessmentId) {
    Assessment a = ownedInProgress(userId, assessmentId);
    List<AssessmentItem> all = items.findByAssessmentIdOrderByOrderNumAsc(assessmentId);
    long answeredCount = all.stream().filter(i -> i.getAnsweredAt() != null).count();
    if (engine.isComplete((int) answeredCount)) return Optional.empty();
    // outstanding(미응답) 문항이 있으면 재발급(반복 next 안전)
    Optional<AssessmentItem> outstanding = all.stream()
        .filter(i -> i.getAnsweredAt() == null).findFirst();
    if (outstanding.isPresent()) {
      QuestionBank q = questions.findById(outstanding.get().getQuestionBankId()).orElseThrow();
      return Optional.of(toResponse(q, outstanding.get().getOrderNum()));
    }
    Set<Long> excluded = all.stream().map(AssessmentItem::getQuestionBankId).collect(Collectors.toSet());
    QuestionBank q = selector.select(a.getTrack(), a.getCurrentDifficulty(), excluded,
        questions.findByTrack(a.getTrack()));
    if (q == null) return Optional.empty();
    int order = all.size() + 1;
    AssessmentItem item = new AssessmentItem();
    item.setAssessmentId(assessmentId);
    item.setQuestionBankId(q.getId());
    item.setOrderNum(order);
    item.setPresentedAt(Instant.now());
    item.setSkipped(false);
    items.save(item);
    return Optional.of(toResponse(q, order));
  }

  private NextQuestionResponse toResponse(QuestionBank q, int orderNum) {
    var view = new QuestionView(q.getId(), q.getQuestionType(), q.getContent(), q.getOptions(),
        q.getBloomLevel(), q.getDifficulty());
    return new NextQuestionResponse(view, orderNum, AdaptiveEngine.TOTAL_QUESTIONS);
  }
```

### R-B1-2 (P1-3): `answer()`는 **outstanding 문항만** 수락 — 임의/중복 answer 차단
원안은 questionId가 일치하는 미응답 항목을 찾았으나, "현재 outstanding"이 아닌 임의 questionId 수락 여지가 있다. → outstanding 항목과 `questionId`가 일치할 때만 수락한다.

Task 4 `AssessmentService.answer()`의 item 탐색을 교체:

```java
    List<AssessmentItem> all = items.findByAssessmentIdOrderByOrderNumAsc(assessmentId);
    AssessmentItem item = all.stream().filter(i -> i.getAnsweredAt() == null).findFirst()
        .orElseThrow(() -> new IllegalStateException("응답할 outstanding 문항이 없음(먼저 next 호출)"));
    if (!item.getQuestionBankId().equals(req.questionId())) {
      throw new IllegalArgumentException("현재 출제된 문항이 아님");
    }
```
(이후 채점·난이도 전이 로직은 원안 유지.)

### R-B1-3 (P1 B-1): `complete()` 조기 종료 정책
미응답 문항이 남았거나 15문항 미만이면 complete를 거부(또는 의도된 조기 종료 허용 정책 명시). 기본: **outstanding 존재 또는 answeredCount<15면 거부**.

`complete()` 진입부에 추가:

```java
    List<AssessmentItem> all = items.findByAssessmentIdOrderByOrderNumAsc(assessmentId);
    boolean hasOutstanding = all.stream().anyMatch(i -> i.getAnsweredAt() == null);
    long answered = all.stream().filter(i -> i.getAnsweredAt() != null).count();
    if (hasOutstanding || answered < AdaptiveEngine.TOTAL_QUESTIONS) {
      throw new IllegalStateException("15문항 응답 완료 후에만 complete 가능");
    }
```

### R-B1-4 (P1 B-1): 회귀 테스트 + 시드 격리
`AssessmentControllerTest`에 추가: ①같은 문항에 `GET /next` 2회 → 동일 questionId 반환(누적 없음) ②미응답 상태에서 임의 questionId `answer` → 400 ③15문항 미만 `complete` → 4xx. 시드는 테스트 간 잔존 영향을 줄이도록 `@Transactional`(롤백) 또는 고유 track 사용. (실 PG·non-embedded이므로 `@Sql` 시드 + `@Sql`(executionPhase=AFTER) cleanup 또는 테스트별 트랜잭션 롤백 명시.)

### R-B1-5 (B-1 채점): answer_key 비교는 시드 형식 확정 후 구조 비교
원안은 공백 제거 문자열 비교(시드 JSON 형식 단순 가정). B-2 시드 형식(`{"correct":N}`) 확정 후 `JsonMapper`로 파싱해 `correct` 값 비교로 정교화 권장(키 순서·공백 무관).

---

## Self-Review (작성자 점검 결과)

- **Spec coverage**: 설계서 §2 빌드B(엔진+회원 API), §3 데이터모델(엔티티 4종), §4 엔진 확정값(전이·종료·레벨), §5 회원 엔드포인트 5종, §10 Boot4 주의(test 슬라이스 모듈·flyway·@ActiveProfiles), 인증모델(§7 자체 JWT 검증) — 커버. guest/claim/이벤트/시드는 B-2로 명시 분리.
- **Placeholder scan**: 모든 코드 완전 기재. concept_scores 정밀 집계는 "B-2 보강"으로 명시(설계서 §11.3 위임 — 플레이스홀더 아님, 범위 분리). PR 본문 `...`는 자유서술.
- **Type consistency**: `AdaptiveEngine.AnswerOutcome`(CORRECT/WRONG/SKIP)·`START_DIFFICULTY`·`TOTAL_QUESTIONS`·`diagnoseLevel(List<Double>)`가 Task3 정의와 Task4 사용 일치. DTO 필드명(assessmentId/question.id/diagnosedLevel)이 컨트롤러·테스트 JSONPath와 일치. 엔티티 getter(`getQuestionBankId`,`isSkipped`,`getIsCorrect`)가 서비스 사용과 일치.
- **주의**: JPA/통합 테스트는 실 Postgres 필요(로컬 compose/CI service). `@DataJpaTest`는 Boot4 모듈 `org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest`. answer_key 비교는 공백 정규화 단순 비교(JSON 정답 형식 단순 가정) — 시드/실문항 형식 확정 시 B-2에서 정교화.
