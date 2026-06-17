# MD1 Slice 1 Plan Review Report

작성일: 2026-06-17  
대상:
- `documents/docs/superpowers/plans/2026-06-17-md1-slice1-shared-schema.md`
- `documents/docs/superpowers/plans/2026-06-17-md1-slice1-platform-auth-2a.md`
- `documents/docs/superpowers/plans/2026-06-17-md1-slice1-platform-events-2b.md`
- `documents/docs/superpowers/plans/2026-06-17-md1-slice1-gateway.md`
- `documents/docs/superpowers/plans/2026-06-17-md1-slice1-frontend-web.md`

## 1. 검토 요약

원본 계획문서는 직접 수정하지 않았다. 이 리포트는 OAuth 설계서 D-1~D-9/R1~R6, 현재 레포 상태, 그리고 5개 계획문서 간 계약 정합성을 기준으로 한 별도 보완 보고서다.

빌드1(shared schema)은 이미 구현/머지 완료 상태로 간주한다. 따라서 빌드1 관련 항목은 기존 마이그레이션 수정이 아니라 후속 마이그레이션, 운영 전제 명시, 또는 데이터 보정 방안으로만 다룬다.

가장 큰 리스크는 인증 계약의 의미 혼재, provider token 저장 목표와 구현 계획의 불일치, outbox relay의 발행 성공 판정, CORS/쿠키 누락, 프론트 세션 복원 누락이다. 빌드2a/2b/3/4 실행 전에 아래 P0/P1 항목을 먼저 정리하는 것이 좋다.

## 2. P0 차단 항목

### P0-1. `/auth/refresh`와 `/auth/logout`의 인증 의미 혼재

문제:
- OAuth 설계서의 엔드포인트 표는 `/auth/refresh`, `/auth/logout`을 `AUTHENTICATED`로 둔다.
- platform 2a 계획은 `/auth/refresh`를 permitAll로 두고, Task 9에서는 `/auth/logout`도 테스트 단순화를 위해 permitAll에 추가하라고 한다.
- gateway 계획도 `/auth/refresh`, `/auth/logout`을 공개 경로로 둔다.
- 여기서 `AUTHENTICATED`가 Bearer JWT 인증을 뜻하는지, refresh-cookie 소유를 뜻하는지 문서마다 다르게 읽힌다.

영향:
- gateway/platform/frontend 테스트가 서로 다른 status를 기대할 수 있다.
- `/auth/logout`을 Bearer 인증 필요로 둘 경우 프론트가 access 만료 상태에서 로그아웃을 실패할 수 있고, permitAll로 둘 경우 refresh cookie만으로 폐기하는 엔드포인트라는 보안 의미를 명시해야 한다.

권고:
- 계약을 다음처럼 명확히 나눈다.
  - `/auth/refresh`: Bearer 불필요, `refresh_token` HttpOnly cookie 필요. 쿠키 없거나 무효면 401.
  - `/auth/logout`: Bearer 불필요, cookie가 있으면 revoke 후 clear, cookie가 없어도 clear cookie + 204 허용.
  - `/users/me`: Bearer access JWT 필요.
- platform 2a, gateway, frontend 테스트 fixture를 같은 기준으로 맞춘다.
- 문서 표현은 `PUBLIC` 대신 `NO_BEARER_REQUIRED`, `REFRESH_COOKIE_REQUIRED`처럼 의미를 분리하는 것이 안전하다.

### P0-2. provider access token 저장 목표와 실제 계획 불일치

문제:
- 설계서 3.2와 platform 2a 목표는 provider access/refresh token을 Tink로 암호화해 `user_oauth_identities`에 저장한다고 한다.
- 하지만 platform 2a Task 8 `OAuth2LoginSuccessHandler`는 provider access token을 `null`로 넘긴다.
- platform 2a는 "2b에서 보강"이라고 적지만, 2b Self-Review는 provider token 캡처를 범위 밖으로 둔다.

영향:
- GitHub collector가 provider token을 소비한다는 D-3 지역성 근거가 깨진다.
- `TokenCipher`와 `access_token_encrypted` 컬럼이 결선된 것처럼 보이지만 실제 OAuth 성공 경로에서는 비어 있게 된다.

권고:
- 2a에 `OAuth2AuthorizedClientService` 또는 `OAuth2AuthorizedClientRepository`를 주입해 로그인 성공 시 GitHub access token, refresh token, scope를 캡처하도록 보강한다.
- 구현 난도가 높아 2a에서 제외한다면, 2b가 아니라 별도 명시 후속 플랜을 만들고 현재 슬라이스 완료 기준에서 provider token 저장을 제외한다고 분명히 적는다.
- 테스트는 OAuth2 성공 핸들러 통합 테스트에서 `access_token_encrypted`가 null이 아닌지까지 검증한다.

### P0-3. outbox relay가 Kafka 발행 성공 전에 `published_at`을 찍음

문제:
- platform 2b `OutboxRelay.relayOnce()`는 `kafka.send(...)` 호출 직후 `publishedAt=now`를 저장한다.
- `KafkaTemplate.send()`는 비동기다. broker 전송 실패, timeout, serialization 실패가 나중에 발생해도 이미 발행 완료로 표시될 수 있다.

영향:
- 이벤트 유실 가능성이 생긴다.
- Transactional Outbox의 핵심 보장인 "성공 발행 행만 published 처리"가 깨진다.

권고:
- 발행 future 완료를 확인한 뒤에만 `published_at`을 설정한다.
- 실패 시 예외를 던지고 row는 미발행 상태로 유지한다.
- Spring Kafka 4 API 기준으로 `CompletableFuture<SendResult<K,V>>` 또는 실제 반환 타입에 맞춰 `get(timeout)`/callback 처리를 확정한다.
- 테스트는 Kafka 발행 실패 mock을 두고 `published_at IS NULL` 유지까지 검증한다.

## 3. P1 실행 전 보완 항목

### P1-1. Task 실행 순서: platform 2a Task 7과 Task 8 순환 의존

문제:
- Task 7 `SecurityFilterChain`은 `OAuth2LoginSuccessHandler` 빈을 주입받는다.
- `OAuth2LoginSuccessHandler`는 Task 8에서 생성된다.
- 문서 하단에 Task 8을 먼저 진행해도 된다는 주의는 있으나, 실제 체크리스트 순서는 Task 7 -> Task 8이다.

권고:
- 실행 순서를 Task 8 -> Task 7로 바꾸는 것이 가장 단순하다.
- 또는 Task 7에 임시 test stub 빈 전략을 명시하고, Task 8에서 본 구현으로 교체한다.

### P1-2. `TOKEN_ENC_KEYSET` 미설정 시 인메모리 keyset 생성 위험

문제:
- platform 2a `TokenCipher`는 `TOKEN_ENC_KEYSET` 미설정 시 임시 인메모리 keyset을 생성한다.

영향:
- 운영에서 env 누락 시 서버 재시작 후 기존 provider token 복호화가 불가능하다.
- 장애가 조용히 데이터 손상처럼 보일 수 있다.

권고:
- `local`/`test` profile에서만 임시 keyset을 허용한다.
- 운영 profile에서는 `TOKEN_ENC_KEYSET`이 없거나 형식이 틀리면 애플리케이션 부팅을 실패시킨다.
- 보안 테스트에 "prod-like profile에서 keyset 누락 시 context load 실패"를 추가한다.

### P1-3. refresh/JWT secret 길이 검증 부족

문제:
- platform/gateway 모두 HS256 공유 시크릿을 사용하지만, 계획은 실제 길이 검증을 명확히 요구하지 않는다.

영향:
- 짧은 `JWT_SECRET`이 운영에 들어가도 토큰 발급/검증이 가능할 수 있다.

권고:
- platform과 gateway 모두 `JWT_SECRET` UTF-8 bytes 길이가 최소 32바이트 이상인지 부팅 시 검증한다.
- 짧은 secret 거부 테스트를 양쪽에 추가한다.

### P1-4. 2b 알림 멱등성이 레이스에 취약

문제:
- `WelcomeNotificationConsumer`는 `existsByUserIdAndType(userId, "WELCOME")` 확인 후 insert한다.
- 같은 이벤트가 동시에 소비되면 두 트랜잭션 모두 exists=false를 보고 중복 insert할 수 있다.

권고:
- shared notifications 마이그레이션에 WELCOME 멱등을 보장하는 DB 제약을 추가한다.
  - 예: `CREATE UNIQUE INDEX uq_notifications_welcome_user ON notifications(user_id, type) WHERE type = 'WELCOME';`
- 또는 repository upsert/native query로 충돌 무시를 구현한다.
- 테스트는 같은 payload를 병렬 호출하거나 동일 이벤트 2회 발행 후 row 1개를 검증한다.

### P1-5. 2b NotificationRepositoryTest의 `user_id=1` 가정

문제:
- 2b 계획의 테스트 코드 예시는 `n.setUserId(1L)`를 사용한다.
- 바로 아래 주의에서 고정 id 사용 금지를 말하지만, 코드 블록 자체는 실패하거나 환경 의존적이다.

권고:
- 테스트 예시를 완성된 코드로 교체해야 한다.
- `@SpringBootTest`에서 `UserRepository`로 user를 저장한 뒤 그 id를 사용하거나, `TestEntityManager`/native insert로 FK를 만족시킨다.

### P1-6. Gateway CORS/쿠키 설정 누락

문제:
- OAuth 설계서 R6은 dev 교차 출처에서 `SameSite=None; Secure`와 CORS allow-credentials origin allowlist를 요구한다.
- gateway 계획에는 JWT 검증과 route만 있고 CORS 설정이 없다.
- frontend 계획은 `withCredentials=true`를 요구하지만, gateway가 credentials CORS를 허용하지 않으면 브라우저 요청이 차단된다.

권고:
- gateway 계획에 CORS 설정 Task를 추가한다.
  - `allowCredentials=true`
  - `allowedOrigins` 또는 `allowedOriginPatterns`를 env allowlist로 주입
  - `Authorization`, `Content-Type`, `Cookie` 요청 헤더 허용
  - `Set-Cookie` 응답 처리 흐름 확인
- 프론트 실API 검증 전에 gateway CORS 테스트를 추가한다.

### P1-7. Frontend app-start session restore 누락

문제:
- frontend 계획은 `/auth/callback` 라우트 진입 시 `/auth/refresh`로 첫 access를 받는 흐름을 다룬다.
- 하지만 새로고침/재방문 때 HttpOnly refresh cookie가 남아 있어도 `AuthController.build()`가 즉시 unauthenticated로 시작하면 라우터가 `/login`으로 보낼 수 있다.

권고:
- 앱 부팅 시 한 번 `POST /auth/refresh`를 시도하는 `bootstrapSession()` 또는 `AuthLoading` 상태를 추가한다.
- `gateRedirect`는 `AuthLoading` 동안 redirect를 보류해야 한다.
- 테스트는 "refresh cookie 기반 bootstrap 성공 시 `/dashboard` 또는 `/onboarding`으로 이동"과 "bootstrap 실패 시 `/login`"을 분리한다.

## 4. P2 정합성/명확성 보완 항목

### P2-1. Frontend D-9 경고 문구가 오래된 2a shape를 언급

문제:
- frontend 계획 헤더는 platform 2a `UserSummary`가 `{id:long, nickname, onboardingStatus, plan}`이라고 경고한다.
- 현재 platform 2a 계획 본문은 이미 `{id, email, nickname, role, onboardingStatus}`와 `id` 문자열로 정렬되어 있다.
- 다만 platform 2a Self-Review에는 여전히 `UserSummary(id,nickname,onboardingStatus,plan)`이라고 오래된 문구가 남아 있다.

권고:
- 리포트 기준으로는 D-9 shape 자체는 2a 본문에서 해결된 것으로 본다.
- 실행 전 혼선을 줄이려면 2a Self-Review와 frontend 헤더 경고를 최신 상태로 맞추는 별도 문서 정리가 필요하다.

### P2-2. User JSON naming: `onboardingStatus` vs `onboarding_status`

문제:
- D-9는 dp_core `User`와 같은 key를 따른다고 하며 `onboardingStatus` camelCase를 전제로 한다.
- OAuth 설계서 04_API 예시는 `onboarding_status` snake_case를 사용한다.
- frontend mock 정합화 Task 4에는 "snake_case" 표현이 남아 있다.

권고:
- 슬라이스 #1에서는 D-9를 우선해 user object는 `onboardingStatus` camelCase로 고정한다.
- `LoginResponse` 최상위 필드만 `access_token`, `refresh_token_cookie_set` snake_case로 둔다.
- mock fixture와 generated `User.fromJson` 테스트를 이 기준으로 맞춘다.

### P2-3. Shared build1 `github_id 이관` 표현과 실제 backfill 부재

문제:
- shared 계획은 `github_id 이관`이라고 표현하지만, 실제 마이그레이션은 `users.github_id`를 backfill 없이 drop한다.
- W1 데이터가 비어 있는 개발/CI DB라면 문제 없지만, 데이터가 있는 환경에서는 기존 GitHub identity가 유실된다.

권고:
- 이미 빌드1이 완료되었으므로 기존 migration 수정은 금지한다.
- 운영/스테이징에 의미 있는 W1 user 데이터가 없다는 전제를 릴리스 노트에 명시한다.
- 데이터가 있을 수 있다면 후속 보정 마이그레이션 또는 수동 backfill runbook을 별도로 작성한다.

### P2-4. Outbox JSON 매핑 타입 확인 필요

문제:
- platform 2a `OutboxEntry.payload`는 `String` + `@JdbcTypeCode(SqlTypes.JSON)`로 계획되어 있다.
- Hibernate/PostgreSQL 조합에 따라 String JSON 매핑이 컴파일은 되어도 저장 시 타입 변환 이슈가 날 수 있다.

권고:
- `UserMappingTest`와 `UserRegistrationServiceTest`에서 outbox insert가 실제 PostgreSQL JSONB에 성공하는지 반드시 확인한다.
- 실패 시 `@JdbcTypeCode(SqlTypes.JSON)` 유지 여부, `String` vs `JsonNode`/`Map` 타입을 실제 Hibernate 7 동작에 맞춰 확정한다.

### P2-5. `created_at`/`updated_at` 매핑의 insertable 전략 점검

문제:
- shared schema는 audit 컬럼 default를 제공한다.
- platform 2a 일부 엔티티는 `createdAt`을 직접 set하고, 일부는 insertable=false/updatable=false로 둔다.

권고:
- DB default를 쓰는 컬럼은 가능하면 insertable=false로 통일한다.
- 직접 set이 필요한 outbox/notification은 명시적 set 또는 DB default 중 하나로 일관되게 정한다.

## 5. 권장 반영 순서

1. 공통 API 계약 표 정리: refresh/logout/users/me의 인증 의미와 응답 shape를 확정한다.
2. platform 2a 보완: provider token 캡처, Task 8 -> Task 7 순서, keyset/JWT secret fail-fast, logout permitAll 기준 반영.
3. gateway 보완: CORS credentials 설정과 platform route/security 테스트를 추가한다.
4. platform 2b 보완: Kafka send 성공 확인 후 published 처리, WELCOME 멱등 DB 제약, user FK 테스트 완성.
5. frontend 보완: app-start session restore, callback bootstrap, cookie refresh interceptor, mock fixture camelCase 정합.
6. shared build1 보강: github_id drop 전제와 데이터 보정 필요 여부를 릴리스 메모로 남긴다.

## 6. 통합 테스트 권장안

계약 테스트:
- `/auth/refresh`: cookie 없음 401, 유효 refresh cookie 200 + `access_token` + `refresh_token_cookie_set=true` + D-9 user object.
- `/auth/logout`: cookie 없음/있음 모두 clear cookie + 204, 유효 cookie가 있으면 Redis revoke.
- `/users/me`: Bearer 없음 401, 유효 Bearer 200 + D-9 user object.

보안 테스트:
- platform에서 발급한 HS256 JWT를 gateway가 검증한다.
- 짧은 `JWT_SECRET`은 platform/gateway 모두 부팅 실패한다.
- CORS credentials 요청에서 허용 origin만 성공한다.
- refresh rotation 후 이전 refresh token은 재사용 불가하다.

이벤트 테스트:
- outbox relay는 Kafka send 성공 후에만 `published_at`을 갱신한다.
- Kafka send 실패 시 `published_at`은 null로 남는다.
- 동일 `UserRegisteredEvent` 중복 소비 후 WELCOME 알림은 1개만 존재한다.

프론트 테스트:
- `/auth/callback` 진입 시 `/auth/refresh` 성공이면 `AuthAuthenticated`.
- 앱 시작 시 refresh cookie 기반 session restore 성공이면 로그인 화면으로 튕기지 않는다.
- 401 응답 후 refresh token 값 없이 cookie 기반 refresh를 시도하고 원 요청을 재시도한다.
- 기존 `gateRedirect`, `golden_path_smoke`, `auth_interceptor_wire` 회귀를 유지한다.

## 7. 최종 판단

빌드1은 현재 계획과 실제 산출물이 대체로 일치하며, 남은 리스크는 데이터 이관 전제 명시 수준이다.

빌드2a는 인증 척추의 핵심이므로 실행 전에 provider token 캡처, refresh/logout 계약, keyset/JWT secret 검증, Task 순서를 정리해야 한다.

빌드2b는 outbox의 신뢰성 보장이 핵심이다. 현재 relay 방식은 이벤트 유실 가능성이 있으므로 Kafka send 성공 확인 후 published 처리로 반드시 보완해야 한다.

빌드3 gateway는 JWT 검증/라우팅 방향은 맞지만, 브라우저 쿠키 흐름을 완성하려면 R6 CORS 설정이 빠지면 안 된다.

빌드4 frontend는 실 OAuth 전환 방향은 맞다. 다만 callback-only bootstrap으로는 새로고침/재방문 UX가 깨질 수 있으므로 app-start session restore를 계획에 포함해야 한다.
