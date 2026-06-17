# MD1 슬라이스 #1 — devpath-frontend web 인증 목→실 전환(빌드 4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

> **⚠️ 상류 계약 의존 게이트(실행 전 필수 재검증):** 이 플랜은 platform 2a·gateway 구현 전에 작성됐다. platform 2a + gateway develop 머지 직후, **실행 전에** 실제 응답을 curl/통합으로 확인하고 본 플랜의 계약 가정을 정정하라:
> - **D-9 user 객체 shape 불일치(반드시 해결):** dp_core `User`는 `{id:String, email, nickname, role(enum), onboardingStatus(enum)}`. platform 2a `UserSummary`는 `{id:long, nickname, onboardingStatus, plan}`(email·role 없음, id 숫자). **둘 중 하나를 맞춰야 한다.** 권장: platform `/auth/refresh`·`/users/me`가 `{id, email, nickname, role, onboardingStatus}`를 반환하도록 2a `UserSummary` 확장(또는 별도 `MeResponse`), id는 문자열 직렬화 또는 dp_core `User.id`를 int로. 본 플랜은 "platform이 dp_core `User`와 동일 shape 반환"을 전제로 작성됨 — 2a 실행 시 이 shape를 산출하도록 조정.
> - **R2 refresh 계약:** 실 `/auth/refresh`는 HttpOnly 쿠키 기반(요청 본문에 refresh 없음, 응답 `{access_token, refresh_token_cookie_set, user}`). 현 dp_core `AuthInterceptor`/목은 본문 `{refreshToken}`+응답 `{accessToken, refreshToken}` 가정 → 교체.
> - **R1 로그인:** 실 로그인은 `POST /auth/login`이 아니라 브라우저 리다이렉트 `GET {baseUrl}/oauth2/authorization/github` → 콜백 후 SPA가 `/auth/refresh`로 첫 access 획득.
> - **R6 CORS/쿠키:** dio `withCredentials=true` + gateway CORS allow-credentials·출처 allowlist 필요.

**Goal:** web 앱이 목(`POST /auth/login` + 본문 refresh)에서 실 OAuth 흐름(GitHub 리다이렉트 → 콜백 → 쿠키 기반 `/auth/refresh`)으로 전환되어, gateway 실API로 로그인→`/users/me`→게이트(온보딩)가 동작한다.

**Architecture:** 로그인은 `window.location`으로 gateway `/oauth2/authorization/github`로 이동(브라우저 리다이렉트). platform이 refresh HttpOnly 쿠키 설정 후 `{APP_WEB_URL}/auth/callback`으로 리다이렉트. SPA의 `/auth/callback` 라우트가 `POST /auth/refresh`(withCredentials, 본문 없음)를 호출해 access JWT + user를 받고 `AuthAuthenticated`로 전환 → 게이트가 온보딩/대시보드로 분기. access는 메모리(`InMemoryTokenStore`), refresh는 JS 비가독 HttpOnly 쿠키(브라우저가 자동 전송). 401 시 `AuthInterceptor`가 쿠키 기반 `/auth/refresh`로 회전 재시도.

**Tech Stack:** Flutter Web · Dart · Riverpod · go_router · dio · melos. 빌드/테스트: `melos run analyze` / `melos run test`(flutter_test + ProviderContainer).

## Global Constraints

- 모노레포 루트에서 melos로 실행. 테스트는 Flutter 테스트 스택(`flutter_test`+`flutter_riverpod` `ProviderContainer`/위젯). 실패 테스트 먼저, `melos run test`로 통과 확인. 포맷 `melos run format`(CI 게이트).
- 런타임 설정은 `--dart-define`(`API_BASE_URL`=gateway, `USE_MOCK=false`). 비밀값·토큰 커밋 금지.
- dp_core(순수 Dart)·dp_design(Flutter)는 공용 — web 전용 변경은 `apps/web`에, 공용 계약 변경(AuthInterceptor·TokenStore·User)은 `packages/dp_core`에. freezed/json 모델 변경 시 `dart run build_runner build` 재생성.
- 브랜치: devpath-frontend `develop`에서 `feat/web-auth-realapi` 분기 → develop PR(2단계, main 직접 금지). CI(`melos run analyze`·`melos run test`) green 필수.
- 기존 게이트 순수함수 `gateRedirect`(미인증→/login, 온보딩미완→/onboarding)·`golden_path_smoke`·`gate_redirect` 테스트는 유지(회귀 금지).

## Preconditions

- platform 2a + gateway develop 머지 + 위 "상류 계약 게이트" 재검증·정정 완료.
- 로컬 실API 검증을 위해 gateway+platform+PG+Redis 구동(또는 staging). 외부 GitHub OAuth 앱(client id/secret·redirect URI `{gateway}/login/oauth2/code/github`) 등록 완료(사용자 선행).
- 브랜치: `git checkout develop && git pull && git checkout -b feat/web-auth-realapi`. `melos bootstrap`.

## File Structure

- (dp_core) `auth/token_store.dart` — web용 access-only 동작 허용(refresh 쿠키). `auth/auth_interceptor.dart` — 쿠키 기반 refresh(본문/인자 없는 refresh) 지원.
- (dp_core) `models/user.dart` — D-9 정렬에 따라 필드/직렬화 조정(필요 시).
- (web) `providers/api_providers.dart` — dio `withCredentials`, AuthInterceptor refresh 콜백(쿠키 기반), useMock 분기.
- (web) `features/auth/application/auth_controller.dart` — `login()`=OAuth 리다이렉트, `bootstrapFromCallback()`=`/auth/refresh`로 세션 복원.
- (web) `features/auth/presentation/login_page.dart` — "GitHub로 로그인" → 리다이렉트.
- (web) `app/router.dart` — `/auth/callback` 라우트 추가(게이트 예외).
- (web) `data/web_mock_fixtures.dart` — 목 계약을 실계약(snake_case·user 포함 refresh)과 정합화(목 유지하되 실 shape 반영).
- (web) `app/app_config.dart` — 기본 baseUrl/useMock(실API용 dart-define 문서화).

---

### Task 1: (dp_core) AuthInterceptor·TokenStore 쿠키 기반 refresh 지원 (R2)

웹은 refresh가 HttpOnly 쿠키라 JS가 읽을 수 없다. `readRefresh()`가 null이어도 쿠키 기반 refresh를 시도하도록 인터셉터를 일반화한다.

**Files:**
- Modify: `packages/dp_core/lib/src/auth/auth_interceptor.dart`
- Modify(test): `packages/dp_core/test/auth/auth_interceptor_test.dart`(있으면) 또는 신규

**Interfaces:**
- Produces: `AuthInterceptor`의 `refresh` 콜백 시그니처를 `Future<TokenPair?> Function(String? refreshToken)`로 일반화(웹은 인자 무시·쿠키 사용). `readRefresh()==null`이어도 `refresh(null)`을 시도하고, 성공 시 `store.save(access, refresh?? '')`. refresh가 쿠키 전용이면 `TokenPair.refresh`는 빈 문자열 허용.

- [ ] **Step 1: 실패 테스트** — 401 → refresh(null 허용) → 재시도 성공 케이스. (MockAdapter로 401→200, refresh 콜백이 새 access 반환.)
- [ ] **Step 2~4:** 실패 확인 → 인터셉터 수정(아래) → 통과.

`auth_interceptor.dart` 변경 핵심:
```dart
  final Future<TokenPair?> Function(String? refreshToken) refresh;
  ...
  // onError 내 refresh 분기:
  final refreshToken = await store.readRefresh(); // 웹은 null 가능
  try {
    final pair = await refresh(refreshToken); // 쿠키 기반이면 인자 무시
    if (pair == null) { await store.clear(); handler.next(err); return; }
    await store.save(access: pair.access, refresh: pair.refresh);
    final req = err.requestOptions..headers['Authorization'] = 'Bearer ${pair.access}';
    handler.resolve(await retry(req));
  } catch (_) {
    await store.clear();
    handler.next(err);
  }
```
> 기존 rotation-guard(다중 동시요청 직렬화) 로직은 유지. `refreshToken==null` 시 즉시 포기하던 분기를 제거(쿠키 기반 시도 허용).

- [ ] **Step 5: 커밋** — `feat(dp_core): AuthInterceptor 쿠키 기반 refresh 지원(R2)`.

---

### Task 2: (web) api_providers — withCredentials + 쿠키 기반 refresh 콜백

**Files:**
- Modify: `apps/web/lib/src/providers/api_providers.dart`
- Modify(test): `apps/web/test/providers/auth_interceptor_wire_test.dart`

**Interfaces:**
- Produces: `apiClientProvider`의 dio에 `withCredentials` 설정(쿠키 전송) + AuthInterceptor `refresh` 콜백이 `POST /auth/refresh`(본문 없음)을 호출해 `{access_token}`을 `TokenPair(access, refresh:'')`로 매핑.

- [ ] **Step 1: 실패 테스트 수정** — `auth_interceptor_wire_test`는 현재 결선만 검증(유지). refresh 콜백이 본문 없이 호출되고 응답 `access_token`을 읽음을 추가 검증(MockAdapter).
- [ ] **Step 2~4:** 수정 → 통과.

`api_providers.dart` refresh 콜백 핵심(현 body `{refreshToken}` 제거):
```dart
    refresh: (refreshToken) async {
      final data = await client.post<Map<String, dynamic>>('/auth/refresh'); // 본문 없음, 쿠키 자동
      return TokenPair(access: data['access_token'] as String, refresh: '');
    },
```
dio withCredentials(웹 쿠키): `ApiClient.create` 또는 dio 옵션에 `extra`/`BrowserHttpClientAdapter().withCredentials = true` 설정. (dp_core `ApiClient`가 어댑터를 만들면 web에서 `withCredentials=true`로 구성 — ApiClient 수정 필요 시 dp_core Task로 분리.)

- [ ] **Step 5: 커밋** — `feat(web): /auth/refresh 쿠키 계약 + withCredentials`.

---

### Task 3: (web) AuthController 실 OAuth 흐름 (R1)

`login()`을 OAuth 리다이렉트로, `bootstrapFromCallback()`을 `/auth/refresh` 세션 복원으로 구현.

**Files:**
- Modify: `apps/web/lib/src/features/auth/application/auth_controller.dart`
- Modify: `apps/web/lib/src/features/auth/presentation/login_page.dart`
- Modify: `apps/web/lib/src/app/router.dart`(`/auth/callback` 라우트 + 게이트 예외)
- Modify(test): `apps/web/test/features/auth/...`(있으면) / `apps/web/test/app/gate_redirect_test.dart`(유지)

**Interfaces:**
- Produces:
  - `AuthController.login()` — `web.window.location.href = '${baseUrl}/oauth2/authorization/github'`(브라우저 리다이렉트; 테스트 위해 리다이렉트 실행을 주입 가능한 `Launcher` 추상화).
  - `AuthController.bootstrapFromCallback()` — `POST /auth/refresh` → access 저장 + `User.fromJson(data['user'])` → `AuthAuthenticated`. 실패 시 `AuthUnauthenticated(error)`.
  - router: `/auth/callback` 라우트(게이트 통과 허용), 진입 시 `bootstrapFromCallback()` 호출 후 결과에 따라 게이트가 분기.

- [ ] **Step 1: 실패 테스트** — `bootstrapFromCallback()`이 목/Mock `/auth/refresh`(user 포함) 응답으로 `AuthAuthenticated(user)`로 전이하고, 실패 응답 시 `AuthUnauthenticated`임을 `ProviderContainer`로 검증. `login()`은 주입된 `Launcher`가 올바른 URL로 호출됨을 검증.
- [ ] **Step 2~4:** 실패 → 구현 → 통과.

`auth_controller.dart` 핵심:
```dart
  Future<void> login() async {
    final base = ref.read(appConfigProvider).baseUrl;
    ref.read(oauthLauncherProvider).launch('$base/oauth2/authorization/github');
  }

  Future<void> bootstrapFromCallback() async {
    try {
      final data = await _client.post<Map<String, dynamic>>('/auth/refresh');
      await _store.save(access: data['access_token'] as String, refresh: '');
      state = AuthAuthenticated(User.fromJson((data['user'] as Map).cast<String, dynamic>()));
    } on ApiException catch (e) {
      state = AuthUnauthenticated(error: e.message);
    }
  }
```
> `oauthLauncherProvider`는 web에서 `window.location` 이동, 테스트에서 Fake로 대체. `User.fromJson`은 D-9 정렬된 user shape를 받는다(상류 게이트 참조).

- [ ] **Step 5: 커밋** — `feat(web): OAuth 리다이렉트 로그인 + 콜백 세션 복원`.

---

### Task 4: (web) 목 픽스처 실계약 정합화 + AppConfig 문서화

목을 유지하되 실계약 shape(snake_case·`/auth/refresh`에 user 포함·OAuth 흐름)와 정합화해 `useMock` 경로도 실흐름을 반영.

**Files:**
- Modify: `apps/web/lib/src/data/web_mock_fixtures.dart`
- Modify: `apps/web/lib/src/app/app_config.dart`(주석/기본값 — 실API dart-define 안내)

**Interfaces:**
- Produces: 목 `POST /auth/refresh` → `{access_token, refresh_token_cookie_set:true, user:{...정렬된 shape}}`. 목에서 `POST /auth/login` 제거(실흐름엔 없음) 또는 콜백 부트스트랩 흐름에 맞게 대체. golden_path_smoke가 깨지지 않도록 시나리오 조정.

- [ ] **Step 1: 실패 테스트** — `golden_path_smoke_test`를 실흐름(콜백 부트스트랩→온보딩→…)으로 갱신, 목 픽스처 정합. (기존 흐름 유지가 목표면 최소 변경.)
- [ ] **Step 2~4:** 픽스처/콜백 정합 → 통과.
- [ ] **Step 5: 커밋** — `feat(web): 목 픽스처 실계약 정합 + AppConfig 실API 안내`.

---

### Task 5: 실API 검증 + analyze/test + develop PR

**Files:** 없음(통합·검증).

- [ ] **Step 1: 정적 분석·테스트** — 루트에서 `melos run analyze` && `melos run format` && `melos run test` → 모두 green(특히 `gate_redirect`·`golden_path_smoke`·`auth_interceptor_wire` 유지).
- [ ] **Step 2: 실API 수동 검증(권장)** — gateway+platform 구동 + GitHub OAuth 앱 설정 후 `cd apps/web && flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8080 --dart-define=USE_MOCK=false`로 GitHub 로그인→콜백→/users/me→온보딩 게이트 끝단간 확인. (외부 OAuth 앱 등록 선행 필요.)
- [ ] **Step 3: develop PR + CI green + 머지**
```bash
git push -u origin feat/web-auth-realapi
gh pr create --base develop --head feat/web-auth-realapi --title "feat: web 인증 목→실API 전환(OAuth+JWT+쿠키 refresh)" --body "OAuth 리다이렉트 로그인→콜백 /auth/refresh 부트스트랩→/users/me. R1/R2/R6 반영, D-9 user shape 정렬. 설계서 §3.4."
```

---

## Self-Review

**1. Spec coverage(설계서 §3.4 + R1/R2/R3/R6):** OAuth 리다이렉트 로그인(R1) Task 3 ✓; refresh 쿠키 계약(R2) Task 1·2 ✓; 메모리 토큰·콜백 재획득(R3) Task 3 ✓; withCredentials/CORS(R6) Task 2 ✓; gate_redirect·golden_path 유지 ✓.
**2. Placeholder scan:** 핵심 코드·테스트·명령 포함. 일부는 상류 계약 확정 후 정정 전제로 명시(P4~P5 게이트).
**3. Type consistency:** `User`(dp_core), `TokenPair(access, refresh)`, `/auth/refresh` 응답 키(`access_token`/`user`)가 platform 2a와 일치하도록 **D-9 정렬 필요** — 헤더 게이트에 명시.

**⚠️ 최상위 주의:** 본 플랜은 4개 플랜 중 상류 의존이 가장 크다. **platform 2a·gateway 머지 후 실제 응답으로 D-9/R2/R6를 재검증**한 뒤에만 실행하라. 특히 D-9(user shape)는 platform 2a 실행 시 `UserSummary`를 dp_core `User`와 일치시키는 방향으로 함께 처리하는 것이 옳다(이 발견을 2a 실행 전에 2a 플랜에 반영 권장).

## Execution Handoff
Plan complete and saved to `documents/docs/superpowers/plans/2026-06-17-md1-slice1-frontend-web.md`.
