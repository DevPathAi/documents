# MD2 슬라이스 #4 빌드 D — devpath-gateway /contents/** 라우트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **✅ 구현 완료(2026-06-21):** 본 플랜은 `devpath-gateway`에서 실행 완료됐다 — 커밋 `fe8e0ea` "feat: route content APIs through gateway" (PR #10 → develop 머지, merge commit `5bddd06`). 변경 4파일은 본 플랜 File Structure와 동일(main/test `application*.yml` + `RouteConfigTest`·`ContentRouteTest`), CI `build` 녹색, 스코프 클린. `RouteConfigTest`는 `learningRouteIsConfigured` 추가, `ContentRouteTest`는 미인증 401·인증 라우팅 + **선택 항목인 dashboard 드리프트 회귀 잠금(`authenticatedDashboardPathMatchesLearningRoute`)까지 포함**. 따라서 아래 "Global Constraints/현재 상태/Self-Review"의 *실행 전* 기술(특히 "test yml에 `/dashboard/**`가 빠져 있다")은 **이미 해소됨** — 두 yml 모두 `/onboarding/assessments/**,/learning-paths/**,/dashboard/**,/contents/**`이고 gateway 보안은 `.anyExchange().authenticated()`로 `/contents/**`를 자동 보호한다.

**Goal:** `devpath-gateway`가 `/contents/**` 요청을 `devpath-learning-svc`로 프록시하도록 main/test route config를 정합화하고, 인증 보호 경로 테스트를 추가한다.

**Architecture:** 기존 learning route(`Path=/onboarding/assessments/**,/learning-paths/**,/dashboard/**`)에 `/contents/**`를 추가한다. `/contents/**`는 private learning resource로 취급해 JWT 인증이 필요하다. public 콘텐츠 공개는 후속 결정이다.

**Tech Stack:** Spring Boot 4.0.7 · Spring Cloud Gateway WebFlux · Spring Security OAuth2 Resource Server · WebTestClient · JUnit 5.

## Global Constraints

- 범위는 gateway route/security only. learning-svc API 구현은 C, frontend는 E다.
- API prefix는 bare `/contents/**`.
- main `application.yml`과 test `application-test.yml` route predicate가 서로 어긋나면 안 된다.
- 현재 test yml은 `/dashboard/**`도 빠져 있으므로, D에서 learning route 목록을 main/test 동일하게 맞춘다.

---

## File Structure

- Modify: `src/main/resources/application.yml`
- Modify: `src/test/resources/application-test.yml`
- Modify or Create: `src/test/java/ai/devpath/gateway/ContentRouteTest.java`
- Modify: `src/test/java/ai/devpath/gateway/RouteConfigTest.java`

---

## Task 0: 브랜치 준비

```powershell
cd devpath-gateway
git switch develop
git pull
git switch -c feat/slice4-content-route
```

---

## Task 1: route config 실패 테스트

**Files:**
- Modify: `RouteConfigTest.java`
- Create: `ContentRouteTest.java`

- [ ] **Step 1: RouteConfigTest 강화 (route id 존재만 단언)**

> **검수 반영(중요):** 현재 `RouteConfigTest`는 `RouteLocator`로 route **id**만 검사한다(`platformAuthRouteIsConfigured`가 `r.getId()`로 `platform-auth` 확인). Spring Cloud Gateway의 `Route.getPredicate()`는 불투명한 `AsyncPredicate<ServerWebExchange>`라 원본 `Path=` 패턴 문자열을 되꺼낼 수 없다. 따라서 "predicate 문자열에 `/contents/**` 포함" 류의 단언은 RouteLocator로 **불가능**하다. 경로 매칭 자체는 Step 2의 행위 기반 테스트(WebTestClient)로 검증한다.

`RouteConfigTest`에는 `learning` route가 구성됐는지만 추가한다(기존 `platformAuthRouteIsConfigured` 패턴 복사):

```java
@Test
void learningRouteIsConfigured() {
  StepVerifier.create(routes.getRoutes().map(r -> r.getId()).filter(id -> id.equals("learning")))
      .expectNext("learning").verifyComplete();
}
```

`/contents/**`·`/dashboard/**`가 실제 learning 서비스로 매칭되는지는 ContentRouteTest(Step 2)와 config scan(Task 3)으로 검증한다. 현재 `RouteConfigTest`에는 `platform-auth`만 단언돼 있고 learning route 단언이 없으므로 이 추가만으로도 의미가 있다.

- [ ] **Step 2: ContentRouteTest 작성**

`LearningPathRouteTest`의 셋업을 그대로 복사한다(검증된 패턴): `@SpringBootTest(webEnvironment = RANDOM_PORT)` + `@ActiveProfiles("test")` + `@MockitoBean ReactiveJwtDecoder jwtDecoder` + `WebTestClient`. `@BeforeEach`에서 `when(jwtDecoder.decode("test-token")).thenReturn(Mono.just(jwt()))`, `jwt()`는 `subject("42")`·HS256 헤더로 만든다.

`/contents/c1`에 대해:

- 인증 없음 -> 401.
- `Bearer test-token` -> 401/403/404가 아니어야 함.
- `POST /contents/c1/progress` 인증 없음 -> 401.
- `POST /contents/c1/progress` 인증 있음 -> 401/403/404가 아니어야 함.

백엔드가 떠 있지 않으면 connection 실패로 5xx일 수 있으나(`LearningPathRouteTest`의 authenticated 케이스와 동일), gateway security/route 매칭만 검증하므로 401/403/404가 아니면 통과다.

선택(권장): 같은 방식으로 `/dashboard/c1`(또는 임의 `/dashboard/**` 하위 경로) 인증 시 비-401/403/404도 1건 추가하면 **test yml의 `/dashboard/**` 누락(드리프트)이 회귀로 잠긴다**. config scan(Task 3)만으로도 잡히지만 행위 테스트가 더 강하다.

---

## Task 2: application.yml route 추가

**Files:**
- Modify: `src/main/resources/application.yml`
- Modify: `src/test/resources/application-test.yml`

- [ ] **Step 1: main yml**

```yaml
- Path=/onboarding/assessments/**,/learning-paths/**,/dashboard/**,/contents/**
```

- [ ] **Step 2: test yml**

test yml도 main과 동일한 learning predicate를 사용한다.

```yaml
- Path=/onboarding/assessments/**,/learning-paths/**,/dashboard/**,/contents/**
```

---

## Task 3: 검증

- [ ] **Step 1: focused tests**

```powershell
.\gradlew.bat test --tests ai.devpath.gateway.RouteConfigTest
.\gradlew.bat test --tests ai.devpath.gateway.ContentRouteTest
.\gradlew.bat test --tests ai.devpath.gateway.LearningPathRouteTest
```

- [ ] **Step 2: full build**

```powershell
.\gradlew.bat test
.\gradlew.bat clean build
```

- [ ] **Step 3: config scan**

```powershell
rg -n "/contents/\\*\\*|/dashboard/\\*\\*" src/main/resources src/test/resources src/test/java
```

Expected: main/test route 둘 다 `/contents/**`와 `/dashboard/**` 포함.

---

## Task 4: develop PR

```powershell
git push -u origin feat/slice4-content-route
gh pr create --base develop --title "feat: route content APIs through gateway" --body "Adds /contents/** to learning route and covers protected content routes."
```

## Acceptance Checklist

- [ ] main yml learning route has `/contents/**`.
- [ ] test yml learning route has `/contents/**`.
- [ ] `/dashboard/**` route remains in both main/test yml.
- [ ] unauthenticated `/contents/{id}` and `/contents/{id}/progress` return 401.
- [ ] authenticated content routes are matched by gateway and not rejected as unauthorized/forbidden/not found by gateway.
- [ ] `.\gradlew.bat clean build` passes.

## Self-Review

- **Spec coverage:** 설계서 P0 `/contents/**` gateway route and §11.4 gateway tests를 커버한다.
- **Current source alignment:** main yml has `/dashboard/**`; test yml currently does not. D fixes that drift while adding `/contents/**`.
- **Boundary safety:** No learning/frontend code changes.
