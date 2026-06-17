# 설계서 — MD1 슬라이스 #1: GitHub OAuth/인증 게이트 (2026-06-17)

> **목적**: MD1의 첫 수직 슬라이스. 비회원/미인증 → GitHub OAuth 로그인 → JWT 발급 → `/users/me`가 web에서 **끝단간 실API로 동작**하는 인증 게이트를 구축한다. 모든 후속 슬라이스(진단·학습경로)의 선행 게이트다.
> **원칙**: 각 레포 CLAUDE.md 절대 조건(추측 금지·테스트 우선·문제 시 코드 분석) + 브랜치 전략(main 보호·develop 경유 2단계 PR) + 서브에이전트 Scope Lock.
> **근거(실측 2026-06-17)**: 17_스케줄 §2(MD1 슬라이스 #1), 02_ERD §1, 03_아키텍처, 04_API_명세 §1, 각 레포 W1 baseline.

---

## 1. 선결 결정 (브레인스토밍 확정)

| # | 결정 | 선택 | 근거 |
|---|------|------|------|
| D-1 | OAuth provider 1차 끝단간 범위 | **GitHub만 먼저 끝단간** (provider 추상화는 N개 대응 설계) | GitHub OAuth는 심사 불필요·즉시. Google(2~6주)·카카오(3~7일) 심사 리드타임 회피. 통합 리스크 최소화 |
| D-2 | 토큰 전략 | **단명 access(JWT 본문) + 회전 refresh(HttpOnly·Secure·SameSite 쿠키)** | 탈취 대응 표준. refresh rotation + 이전 토큰 무효화, 서버측 해시 저장 |
| D-3 | OAuth 종단·JWT 발급 주체 | **platform 발급 / gateway 검증** | 스케줄 §2 SSoT 일치. provider 토큰을 platform-svc github 수집기가 소비(지역성) |
| D-4 | shared 스키마 | **ERD 정합, github_id 이관** | users 확장 + user_oauth_identities + user_profiles. user_learning_prefs는 #2 연기 |
| D-5 | UserRegisteredEvent Outbox | **Producer + 소비처 1개(notification 환영 알림)** | 발행 검증 + consumer 결선 시연. github 수집 범위 회피 |

---

## 2. 끝단간 흐름

```
[web SPA] --GET /oauth2/authorization/github--> [gateway] --route--> [platform-svc]
                                                                          |
[platform-svc] --redirect--> [GitHub authorize] --callback /login/oauth2/code/github--> [gateway->platform]
                                                                          |
[platform-svc]: code 교환 -> GitHub access_token + 사용자 조회
   -> users + user_oauth_identities(provider 토큰 암호화) upsert
   -> user_profiles 빈 행 생성, onboarding_status=PENDING
   -> (최초 가입 시 동일 트랜잭션) UserRegisteredEvent outbox 기록
   -> 앱 access JWT(단명) 발급 + refresh(회전·해시 저장) HttpOnly 쿠키 설정
   -> access_token을 SPA로 전달 (전달 방식 = R1, spec 확정)
                                                                          |
[web SPA] --GET /users/me (Bearer)--> [gateway: JWT 서명·만료 검증] --route--> [platform-svc]
[web SPA] 401 시 --POST /auth/refresh (쿠키 자동)--> [platform: 회전] -> 새 access
                                                                          |
[outbox relay] -> Kafka -> [notification 소비자] -> 환영 알림 생성
```

### 권한·엔드포인트 (04_API_명세 §1 계약)
| Method | Endpoint | 권한 | 비고 |
|--------|----------|------|------|
| GET | `/oauth2/authorization/{provider}` | PUBLIC | provider=github (1차) |
| GET | `/login/oauth2/code/{provider}` | PUBLIC | Spring Security 콜백 처리 |
| POST | `/auth/refresh` | AUTHENTICATED | refresh 쿠키 → 새 access, 토큰 회전 |
| POST | `/auth/logout` | AUTHENTICATED | refresh 무효화 |
| GET | `/users/me` | AUTHENTICATED | 로그인 검증·프로필 |

### 로그인 성공 응답 (04_API_명세 §1.1)
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token_cookie_set": true,
  "user": { "id": 42, "nickname": "지수", "onboarding_status": "PENDING", "plan": "FREE" }
}
```

---

## 3. 레포별 설계 (빌드 순서)

### 3.1 devpath-shared (순서 1 — 스키마·이벤트 SSoT)

**Flyway 마이그레이션** (`src/main/resources/db/migration/`, 규약 `VYYYYMMDDHHMM__*.sql`, W1 baseline `V202606150900~0902` 다음 번호):

- `users` 확장 (W1 골격: id·github_id·status·*_at): `email VARCHAR UNIQUE`(**nullable** — R4), `nickname VARCHAR`, `role VARCHAR DEFAULT 'LEARNER'`(LEARNER/ADMIN), `onboarding_status VARCHAR DEFAULT 'PENDING'`(PENDING/IN_PROGRESS/DONE). **`github_id` 컬럼 제거**(신원은 user_oauth_identities로 이관).
- `user_oauth_identities` 신규: `user_id FK`, `provider VARCHAR`(GITHUB/GOOGLE/KAKAO), `provider_user_id VARCHAR`, `access_token_encrypted`, `refresh_token_encrypted`, `scope`, `linked_at`. **`(provider, provider_user_id)` UNIQUE 인덱스**(02_ERD §인덱스).
- `user_profiles` 신규: `user_id FK`, `avatar`, `bio`, `learning_goal`(JOB/CAREER_CHANGE/UPSKILL/SIDE_PROJECT, nullable — 온보딩 #2 채움), `target_track`(BACKEND_SPRING/FRONTEND_REACT/MOBILE_FLUTTER/DEVOPS/FULLSTACK, nullable), `experience_years`(nullable).
- `outbox` 테이블 신규(Transactional Outbox): `id`, `aggregate_type`, `aggregate_id`, `event_type`, `payload(jsonb)`, `created_at`, `published_at`(nullable), `(published_at)` 부분 인덱스.
- 모든 테이블 공통 규약: snake_case, `created_at`/`updated_at` audit + `set_updated_at` 트리거.

**이벤트** (`ai.devpath.shared.event`): `UserRegisteredEvent` record(`DomainEvent` 구현), `eventType = "user.user.registered"`(규약 `<도메인>.<엔티티>.<동작>`, 기존 `LearningPathGeneratedEvent` 패턴 준수). 필드: userId, provider, registeredAt 등(하위 호환: 새 필드 nullable/기본값).

**테스트(먼저)**: Flyway 마이그레이션 검증(기존 `FlywayMigrationTest` 패턴 — `PGSimpleDataSource`로 로컬 docker-compose PostgreSQL 17/CI service container에 연결, `Flyway.migrate()` 후 JDBC 메타데이터로 테이블·컬럼 검증. Testcontainers 미사용), `UserRegisteredEvent` 직렬화/eventType 테스트.

### 3.2 devpath-platform-svc (순서 2 — 인증 코어)

`build.gradle.kts`: `spring-boot-starter-security`(주석 해제), oauth2-client·data-redis·kafka 활성화. Spring Boot 4.0.7 GA(스케줄 §8 폴백 ADR-001 불필요).

- **OAuth2 로그인**: Spring Security oauth2-client. **provider 추상화** — registration 맵에 github만 등록, google/kakao는 설정(yaml/env) 추가만으로 확장 가능한 구조.
- **사용자 upsert**: 콜백 성공 시 user_oauth_identities `(provider, provider_user_id)`로 조회 → 없으면 users+identity+profile 생성(최초 가입) → UserRegisteredEvent outbox 기록(동일 트랜잭션). provider access/refresh 토큰 **암호화 저장**(well-tested 라이브러리 — Google Tink 또는 Spring Security 암호화; 자체 구현 금지).
- **JWT 발급**: 단명 access(서명키 env 주입). 클레임: subject=userId, role.
- **refresh 회전**: 발급 시 refresh를 **해시로 서버측 저장**, HttpOnly·Secure·SameSite 쿠키 설정. `/auth/refresh`는 쿠키의 refresh 검증 → 새 access+새 refresh 발급 → 이전 refresh 무효화(rotation). `/auth/logout`은 refresh 무효화.
- **outbox relay**: outbox 테이블 미발행 행을 Kafka로 발행(published_at 갱신).
- **notification 소비자(D-5)**: `UserRegisteredEvent` 소비 → 환영 알림 생성(platform-svc notification 도메인, 추가 서비스 의존 없음).

**테스트(먼저)**: oauth2 로그인 흐름(mock provider) 통합, JWT 발급·검증 단위, refresh 회전(이전 토큰 무효화 확인), outbox 트랜잭션 기록(가입 실패 시 미기록), notification 소비자, JPA 매핑 `ddl-auto: validate`.

### 3.3 devpath-gateway (순서 3 — 엣지 검증·라우팅)

- `build.gradle.kts`: **`spring-boot-starter-security-oauth2-client` 의존성 제거 → JWT 검증**(WebFlux resource-server 계열)으로 교체. spring-cloud-gateway(WebFlux) 유지.
- **라우팅**: `/oauth2/**`·`/login/**`·`/auth/**`·`/users/**` → platform-svc. 공개 경로(`/oauth2/authorization/**`, `/login/oauth2/code/**`)는 검증 제외.
- **JWT 검증**: 보호 경로에서 access JWT 서명·만료 검증(platform 발급 키와 정합 — R5). 검증 실패 시 401.
- **CLAUDE.md 정정**: "OAuth2 로그인 + JWT 발급/검증" → "JWT 검증 + 라우팅"(발급은 platform).

**테스트(먼저)**: JWT 검증 라우팅 통합(reactor-test) — 유효/만료/무서명 토큰별 라우팅·401, 공개 경로 통과.

### 3.4 devpath-frontend (순서 4 — web 목→실 전환)

web auth 골격(`auth_controller`·`auth_state`·`login_page`·`gateRedirect`)은 이미 존재 → **목→실API 전환**.

- **refresh 계약 정합화(R2)**: 현재 `AuthInterceptor`는 `/auth/refresh`에 `{refreshToken}` 본문 전송·응답에서 refresh 읽음. → 실계약(HttpOnly 쿠키·`refresh_token_cookie_set`)에 맞게 본문 제거, withCredentials 쿠키 전송, 응답은 access_token만.
- **로그인**: `/oauth2/authorization/github` 리다이렉트 진입, 콜백 후 access_token 수신(R1 방식 확정 후) → InMemoryTokenStore.
- gate_redirect(미인증→/login, 온보딩미완→/onboarding)·golden_path_smoke 유지. `useMock=false` 실API 경로 검증.

**테스트(먼저)**: auth_controller 실API 테스트, auth_interceptor_wire 갱신(쿠키 계약), gate_redirect·golden_path_smoke 유지(flutter_test + ProviderContainer).

---

## 4. 횡단 규칙

- **비밀값**: GitHub client id/secret, JWT 서명키, redirect URI는 env(`--dart-define`/환경변수). **절대 커밋 금지**(각 레포 CLAUDE.md).
- **브랜치**: 각 레포 `develop`에서 `feat/*` 분기 → `develop` PR. CI 녹색 확인 후 merge commit. main 직접 금지.
- **서브에이전트 Scope Lock**: 위임 시 단일 Task 경계 명시, 명세 부족 시 NEEDS_CONTEXT 보고. 컨트롤러가 커밋 로그·파일 구조·테스트 직접 검증.
- **선행 트러블슈팅**: 동일 스택 선행 프로젝트 교훈 `documents/24` 참고.

---

## 5. 미해결 spec 항목 (플랜 수립 전 확정 필요)

| # | 항목 | 권장 기본값(플랜에서 최종 확정) |
|---|------|-----------|
| R1 | OAuth 리다이렉트 후 access_token을 SPA에 전달 | **콜백이 refresh HttpOnly 쿠키 설정 후 SPA로 리다이렉트 → SPA가 즉시 `/auth/refresh`로 첫 access 획득**(새 엔드포인트·URL 토큰 노출 회피, refresh 흐름 재사용). 대안: 일회용 code 교환 |
| R2 | refresh 본문→HttpOnly 쿠키 계약 정합 | 프론트·백 동시 수정(설계 3.2·3.4 반영). 확정 |
| R3 | web 토큰 메모리-only(새로고침 시 세션 소실) | #1 수용(R1 흐름으로 새로고침 시 `/auth/refresh` 재획득 가능). localStorage 영속·silent refresh는 후속 |
| R4 | GitHub email 미반환 케이스 | `users.email` nullable. 미반환 시 email=null로 가입 진행, 후처리는 후속 |
| R5 | gateway↔platform JWT 검증 정합 | **대칭 HMAC(공유 시크릿 env 주입)** — 단일 발급자/검증자라 #1엔 충분·단순. 비대칭(JWKS)은 다중 검증자 필요 시 후속 |
| R6 | SPA↔gateway 교차출처 쿠키 | dev(이종 출처): **SameSite=None; Secure + CORS allow-credentials 출처 allowlist**. prod 동일도메인 시 SameSite=Lax 가능 |

### 5.1 후속 확정 결정 (플랜 단계에서 추가)

| # | 항목 | 결정 |
|---|------|------|
| D-6 | platform-svc의 shared 의존 소비 방식 | **shared main 릴리스 선행**: platform 작업 전 shared develop→main PR → `publish.yml`이 GitHub Packages에 publish. platform CI(Packages: read)가 새 클래스 해소 → PR green 가능 |
| D-7 | refresh 토큰 서버측 저장소 | **Redis**(해시 저장, TTL=refresh 수명). 인프라(6379) 존재, TTL 만료·회전·폐기 자연스러움, shared 스키마 변경 불요. platform에 data-redis 활성화 |
| D-8 | 환영 알림 소비자 산출물 | **최소 notifications 테이블**(shared 추가 마이그레이션) + 소비자 행 INSERT. → outbox 릴레이+Kafka 소비자와 함께 **platform 2b**로 분리 |

### 5.2 platform-svc 작업 분해 (2a / 2b)

platform-svc는 Security 7 OAuth + JWT + Redis refresh + Tink 암호화 + Outbox/Kafka로 범위가 커, 빌드 순서 내에서 두 sub-plan으로 분해한다:
- **2a — 인증 척추**: deps/config, JPA 엔티티(User·UserOauthIdentity·UserProfile·OutboxEntry, `ddl-auto: validate`), JWT 서비스(HMAC mint+decode), GitHub OAuth2 로그인 + 사용자 upsert + provider 토큰 Tink 암호화 + `UserRegisteredEvent` outbox 기록(동일 tx), Redis refresh 회전+HttpOnly 쿠키, `/auth/refresh`·`/auth/logout`·`/users/me`. mock provider로 독립 테스트.
- **2b — 이벤트 전파**: outbox 릴레이→Kafka 발행 + 환영 알림 Kafka 소비자 + notifications 테이블(D-8, shared 추가 마이그레이션). 2a 머지 후 작성.

---

## 6. 범위 외 (슬라이스 #1 제외)

- Google·카카오 **실연동**(provider 추상화로 설정만 추후 추가)
- `user_learning_prefs` 테이블(온보딩 슬라이스 #2)
- 진단 결과 claim(`/onboarding/assessments/claim`, 슬라이스 #2)
- github 프로필 수집 워커(별도 슬라이스)
- 모바일 OAuth 콜백 딥링크(`devpath://callback`, 슬라이스 #10)
- web 토큰 localStorage 영속·silent refresh(후속)

---

## 7. 완료 기준 (슬라이스 #1)

- web에서 GitHub OAuth 로그인 → JWT 발급 → `/users/me` 끝단간 **실API 동작**(목 제거)
- gateway가 JWT 검증으로 보호 경로 게이팅, 미인증 401
- refresh 회전 동작(이전 토큰 무효화 확인)
- `UserRegisteredEvent` outbox 발행 + notification 환영 알림 소비 확인
- 각 레포 테스트 녹색, develop PR 머지
- (게이트 완료 → 슬라이스 #2 진단 착수 가능)
