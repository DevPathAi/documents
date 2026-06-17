# 런북 — MD1 슬라이스 #1(OAuth/인증 게이트) 끝단간(E2E) 검증 (2026-06-18)

> **목적**: 5개 빌드가 develop 머지된 슬라이스 #1을 **실제 GitHub OAuth로 끝단간 동작**시켜 MD1 첫 게이트(가입(OAuth)→`/users/me`→온보딩 게이트)를 닫는다.
> **대상 독자**: 직접 실행하는 사람(에이전트 대행 불가 항목 포함 — GitHub 앱 등록·비밀값 주입).
> **이 문서의 모든 값은 레포 실제 설정에서 확인한 값이다(추측 없음).** 출처는 각 절 끝 `근거` 참조.

---

## 0. 전제 — 사전 준비물

| 구성요소 | 로컬 | 비고 |
|---|---|---|
| PostgreSQL | `localhost:5432` DB `devpath` / user `devpath` / pw `localdev` | platform `DB_URL/DB_USER/DB_PASSWORD` 기본값 |
| Redis | `localhost:6379` | refresh 토큰 저장 |
| Kafka | `localhost:9092` | 환영알림 전파(2b). **없어도 로그인 자체는 됨**(아웃박스 릴레이만 지연) |
| 스키마 | devpath-shared 중앙 Flyway가 적용한 `devpath` DB | platform은 `ddl-auto: validate`·`flyway.enabled: false`(검증만) |
| Java 21 / Flutter(web) | — | platform·gateway Boot 4.0.7, web Flutter |

> **스키마 주의**: platform은 마이그레이션을 직접 돌리지 않는다(`flyway.enabled: false`, `ddl-auto: validate`). DB에 슬라이스 #1 스키마(users 확장·user_oauth_identities·user_profiles·outbox·notifications)가 **미리 적용**돼 있어야 부팅된다. shared 중앙 Flyway로 프로비저닝한다.
> 근거: `devpath-platform-svc/src/main/resources/application.yml:9-23`.

---

## 1. GitHub OAuth 앱 등록 (사용자 직접 — 에이전트 대행 불가)

GitHub → Settings → Developer settings → **OAuth Apps** → New OAuth App.

| 항목 | 로컬 값 | staging 값(예) |
|---|---|---|
| Application name | `DevPath AI (local)` | `DevPath AI (staging)` |
| Homepage URL | `http://localhost:5173` | `https://<web-도메인>` |
| **Authorization callback URL** | `http://localhost:8080/login/oauth2/code/github` | `https://<gateway-도메인>/login/oauth2/code/github` |

- 콜백 URL은 **게이트웨이**를 가리킨다(gateway가 `/login/**`를 platform으로 라우팅). 포트는 게이트웨이 포트(로컬 8080).
- 발급된 **Client ID / Client secret**을 2절 platform env(`GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`)에 주입한다. **secret은 절대 커밋 금지.**
- scope는 코드에 고정: `read:user,user:email`(별도 설정 불요).

> 근거: 콜백 경로 = Spring Security 기본 `{baseUrl}/login/oauth2/code/{registrationId}`, gateway 라우팅 `Path=/oauth2/**,/login/**,/auth/**,/users/**`(`devpath-gateway/.../application.yml:9-12`). scope `read:user,user:email`(`devpath-platform-svc/.../application.yml:35`).

---

## 2. 환경변수 — 검증된 변수명·기본값

### 2.1 platform (devpath-platform-svc) — `--server.port=8081`로 기동

| 변수 | 기본값(application.yml) | 로컬 E2E 설정 | staging |
|---|---|---|---|
| `GITHUB_CLIENT_ID` | `dummy-client-id` | **1절 발급값** | 발급값 |
| `GITHUB_CLIENT_SECRET` | `dummy-secret` | **1절 발급값**(비밀) | 발급값(비밀) |
| `JWT_SECRET` | `test-secret-...0123456789`(36B) | **gateway와 동일**, ≥32B | 동일·강한 비밀(≥32B) |
| `APP_WEB_URL` | `http://localhost:5173` | `http://localhost:5173` | `https://<web-도메인>` |
| `COOKIE_SAME_SITE` | `Lax` | `Lax`(로컬 동일호스트) | **`None`** |
| `COOKIE_SECURE` | `false` | `false`(로컬 http) | **`true`** |
| `COOKIE_DOMAIN` | (빈값=host-only) | 빈값 | 필요 시 상위 도메인 |
| `TOKEN_ENC_KEYSET` | (미설정→인메모리, local/test만 허용) | 미설정 가능(경고) | **필수**(Tink JSON keyset Base64). 미설정 시 운영 프로파일 **부팅 실패** |
| `KAFKA_BOOTSTRAP` | `localhost:9092` | `localhost:9092` | 브로커 주소 |
| `DB_URL`/`DB_USER`/`DB_PASSWORD` | `jdbc:postgresql://localhost:5432/devpath`/`devpath`/`localdev` | 동일 | 배포 DB |
| `REDIS_HOST`/`REDIS_PORT` | `localhost`/`6379` | 동일 | 배포 Redis |
| `ACCESS_TTL`/`REFRESH_TTL` | `PT15M`/`P14D` | 기본 | 기본 |

- platform `server.port`는 yml에서 **8080**이다. 게이트웨이 기본 `PLATFORM_URI=http://localhost:8081`과 맞추려면 platform을 **8081**로 띄운다: `SERVER_PORT=8081` 또는 `./gradlew bootRun --args='--server.port=8081'`.
- `TOKEN_ENC_KEYSET` 미설정 시 local/test 프로파일에서만 임시 인메모리 keyset 허용(재시작 시 기존 암호화 토큰 복호화 불가). 운영 프로파일은 미설정이면 부팅 실패한다.

> 근거: `devpath-platform-svc/.../application.yml:5-54`(env 기본값·port 8080), `auth/crypto/TokenCipher.java:22-37`(`TOKEN_ENC_KEYSET`, local/test 외 부팅 실패), `auth/OAuth2LoginSuccessHandler.java:56-58`(refresh 쿠키 set + `{APP_WEB_URL}/auth/callback` 리다이렉트).

### 2.2 gateway (devpath-gateway) — 포트 8080

| 변수 | 기본값 | 로컬 E2E | staging |
|---|---|---|---|
| `JWT_SECRET` | `test-secret-...0123456789` | **platform과 동일** | platform과 동일 |
| `PLATFORM_URI` | `http://localhost:8081` | `http://localhost:8081` | `http://devpath-platform-svc:8080`(클러스터 내부) |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | `http://localhost:5173`(web 출처) | `https://<web-도메인>` |

- gateway는 JWT를 **서명+만료만** 검증한다(HS256, iss/aud 미검증). 그래서 `JWT_SECRET`이 platform과 **반드시 동일**해야 한다(불일치 시 모든 보호 요청 401). ≥32B 미만이면 부팅 실패.
- CORS는 `allow-credentials`라 쿠키 왕복을 허용하되 origin을 와일드카드(`*`)로 둘 수 없다 — web 출처를 정확히 명시한다.

> 근거: `devpath-gateway/.../config/GatewaySecurityConfig.java:22-25`(`JWT_SECRET` ≥32B 검증), `:51`(`CORS_ALLOWED_ORIGINS` 기본 `http://localhost:5173`), `application.yml:10`(`PLATFORM_URI` 기본 8081).

### 2.3 web (devpath-frontend/apps/web)

`--dart-define`로 주입:

| define | 값(로컬) | 의미 |
|---|---|---|
| `API_BASE_URL` | `http://localhost:8080`(gateway) | 모든 API·OAuth 진입 베이스 |
| `USE_MOCK` | `false` | 목 어댑터 비활성, 실 HTTP |

> 근거: `apps/web/.../auth/application/auth_controller.dart:31`(`'$base/oauth2/authorization/github'`), CLAUDE.md "환경 변수"(`--dart-define`·`AppConfig.fromEnvironment`).

---

## 3. 로컬 끝단간 기동 순서

```bash
# 0) 인프라: PostgreSQL(5432)·Redis(6379)·Kafka(9092) 기동 + shared 중앙 Flyway로 devpath DB 스키마 적용

# 1) platform — 8081로 기동 (env는 셸/파일로 주입, secret 커밋 금지)
cd devpath-platform-svc
GITHUB_CLIENT_ID=<발급값> GITHUB_CLIENT_SECRET=<발급값> \
JWT_SECRET=<공유-32바이트-이상> APP_WEB_URL=http://localhost:5173 \
./gradlew bootRun --args='--server.port=8081'

# 2) gateway — 8080
cd devpath-gateway
JWT_SECRET=<platform과-동일> PLATFORM_URI=http://localhost:8081 \
CORS_ALLOWED_ORIGINS=http://localhost:5173 \
./gradlew bootRun        # 기본 8080

# 3) web — 5173 (Flutter Web)
cd devpath-frontend/apps/web
flutter run -d chrome \
  --web-port=5173 \
  --dart-define=API_BASE_URL=http://localhost:8080 \
  --dart-define=USE_MOCK=false
```

> Kafka가 없으면 로그인·`/users/me`는 정상 동작하고, 환영알림(2b)만 아웃박스에 남아 릴레이가 지연된다(브로커 복구 시 전파). 끝단간 "가입→`/users/me`" 게이트 판정에는 Kafka 불필수.

---

## 4. 수동 검증 체크리스트

브라우저(시크릿 창 권장)에서 web(`http://localhost:5173`) 접속 후:

1. **로그인 진입**: 로그인 버튼 → 브라우저가 `http://localhost:8080/oauth2/authorization/github`로 이동(gateway→platform 라우팅) → GitHub 인가 화면.
2. **GitHub 인가**: 승인 → GitHub이 `http://localhost:8080/login/oauth2/code/github`(콜백)로 리다이렉트 → gateway→platform.
3. **세션 수립**: platform이 사용자 upsert + refresh 쿠키 set 후 `http://localhost:5173/auth/callback`로 리다이렉트.
4. **첫 access 발급**: web `/auth/callback`이 `http://localhost:8080/auth/refresh`를 **withCredentials**로 호출 → access 토큰 수신.
5. **`/users/me`**: web이 access로 `/users/me` 호출 성공 → 사용자 정보 표시.
6. **온보딩 게이트**: `onboardingStatus`가 `PENDING`이면 온보딩으로, `DONE`이면 대시보드로 1회 분기.
7. **email 비공개 사용자(R4 검증)**: GitHub 이메일을 비공개로 둔 계정으로도 4~6단계가 통과한다(`User.email` null 허용, devpath-frontend PR #16).

### 확인 포인트(DevTools)
- 2→3 리다이렉트 응답에 `Set-Cookie`(refresh). 로컬은 `SameSite=Lax`(동일호스트 localhost라 Secure 불요).
- 4단계 `/auth/refresh` 요청에 쿠키 동봉(`withCredentials`), 응답 200 + access.
- staging(교차출처)에서는 쿠키가 `SameSite=None; Secure`여야 왕복된다 — `COOKIE_SAME_SITE=None`+`COOKIE_SECURE=true`+gateway CORS allow-credentials 확인.

---

## 5. 트러블슈팅 (증상 → 원인)

| 증상 | 가능 원인 | 확인 |
|---|---|---|
| 보호 요청 전부 401 | gateway·platform `JWT_SECRET` 불일치 | 두 env 동일 여부, 둘 다 ≥32B |
| 부팅 실패(JWT) | `JWT_SECRET` < 32바이트 | 로그 `JWT_SECRET must be >= 32 bytes` |
| 부팅 실패(keyset) | 운영 프로파일 `TOKEN_ENC_KEYSET` 미설정 | 로그 `TOKEN_ENC_KEYSET 미설정 — 운영 프로파일에서는 필수` |
| 콜백 404/route 오류 | GitHub 콜백 URL이 platform(8081)을 직접 가리킴 | 콜백 URL은 **gateway**(8080) `/login/oauth2/code/github` |
| `/auth/refresh` 쿠키 미동봉 | 교차출처인데 `SameSite=Lax`/`Secure=false` | staging은 `None`+`Secure`, gateway CORS allow-credentials·정확한 origin |
| CORS 차단 | `CORS_ALLOWED_ORIGINS`에 web 출처 누락 | web 출처 정확히(와일드카드 불가) |
| 로그인 후 미인증 폴백 | (해결됨) email 미반환 + `User.email` required | PR #16로 nullable화 완료 |
| 부팅 실패(스키마 validate) | DB에 슬라이스 #1 스키마 미적용 | shared 중앙 Flyway로 `devpath` DB 프로비저닝 |

---

## 6. 관련 문서
- 핸드오프: `docs/superpowers/handoff-2026-06-18-md1-slice1-done.md`
- 설계서·플랜: `docs/superpowers/{specs,plans}/2026-06-17-md1-slice1-*`
- 대시보드: https://devpathai.github.io/workflow-dashboard/
