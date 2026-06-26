# 빌드 보고서 — 슬라이스 #10(모바일) Build A·B·C (2026-06-27)

> `apps/mobile`(빈 Flutter 카운터 스캐폴드)에 실제 앱 골격 구축. dp_core 공유 계층 재사용, web 패턴(Riverpod + go_router + feature-first)을 모바일에 적용. **목 우선**(useMock 기본, web과 동일 정책). WSL+Bash 메인 직접 진행.

## 1. 범위·산출물

### Build A — 기반 / 셸 / 인증 / 딥링크 (PR #39 → develop)
- dp_core 재사용 `ApiClient` + 모바일 토큰 기반 `AuthInterceptor`(401 refresh = refresh 토큰 바디 전송), `AppConfig.fromEnvironment`(`--dart-define`, 목 기본).
- `StatefulShellRoute.indexedStack` 하단탭 셸(홈·학습·커뮤니티) + `gateRedirect`(미인증→/login, 인증+/login→/home).
- `SecureStorageTokenStore`(flutter_secure_storage) + `KeyValueStore` 추상화 → 플랫폼 채널을 토큰 저장소에서 분리(단위테스트 가능).
- OAuth 딥링크: `parseAuthCallback`(devpath://callback, query·fragment) + `DeepLinkService`(app_links 콜드/웜 스타트) + `UrlLauncherOAuthLauncher`(url_launcher). 네이티브: Android `intent-filter` / iOS `CFBundleURLTypes`.
- 세션: 부팅 시 저장 access 토큰 있으면 `GET /users/me`(UserSummary)로 복원. 목 로그인은 가짜 토큰 저장 후 동일 경로.

### Build B — 오프라인 캐시 + 홈 대시보드 (PR #39 → develop)
- drift 오프라인 읽기 캐시(`DashboardCacheRows` 단일행 upsert) + `DashboardCache` 추상(Drift/InMemory).
- `connectivity_plus` 재연결(오프라인→온라인 전환) 자동 재동기화(`ref.listen(connectivityProvider)`).
- `DashboardController`: 온라인 로드→캐시 저장; 네트워크 실패→캐시 복원(`fromCache=true`)·캐시 없으면 실패.
- `DashboardPage`: 스트릭·진척률·다음 과제·배지, 오프라인 시 `DpOfflineBanner`.

### Build C — 학습 뷰어 + 퀵 캡처 (PR #40 → core, 스택)
- 학습: `LearnController`(GET /learning-paths/me) + `LearnPage`(주차·과제 목록); `ContentController`(GET /contents/:slug, 완료 진척 보고) + `ContentViewerPage`(`DpMarkdown` + 완료 표시). 라우터 `/learn/content/:slug` 서브라우트(탭 유지).
- 커뮤니티(퀵 캡처): `CommunityController`(GET /community/posts) + `CommunityPage`(목록 + 퀵 캡처 FAB); `questionCreate`(POST /community/questions) + `QuickCapturePage`(제목·본문·태그 → 게시 후 복귀). 라우터 `/community/new` 서브라우트.
- 정리: 미사용 `PlaceholderPage` 제거.

## 2. 검증 (전 워크스페이스 게이트 — 녹색)
- `melos run analyze`: SUCCESS(dp_core·dp_design·web·admin·mobile).
- `melos run format`: 269 files, 0 changed(CI 게이트).
- `melos run test`: **mobile 45 신규**(A+B 32 + C 13) · web 147 · dp_core 48 · dp_design 19 · admin 12 — 전부 통과. 회귀 무변.
- drift 코드젠 `app_database.g.dart` 생성·커밋(libsqlite3 가용 → `NativeDatabase.memory()` 통합 테스트 포함).

## 3. 핵심 결정·제약 (추측 아님 — 백엔드 코드 검증)
- **모바일 실API 인증 = 백엔드 후속**: 현 platform-svc는 **쿠키 기반**(OAuth 성공→HttpOnly refresh 쿠키 + `webUrl+/auth/callback` 리다이렉트, `/auth/refresh`는 쿠키 판독). 모바일용 `devpath://callback` 리다이렉트·토큰-바디 refresh 계약이 **백엔드에 없음** → 앱은 목 우선 구현. 계약 추가는 백엔드 작업.
- **온보딩 게이트 미구현**: 모바일은 post-onboarding 진입 가정(목 사용자 onboardingStatus=DONE). 온보딩 흐름은 후속.
- **FCM(Build D) 결정(사용자 승인)**: 추상화(NotificationService)+네이티브 설정+페이크 테스트로 구현, 실 Firebase(google-services.json/APNs)는 후속.
- 의존성(워크스페이스 단일 해석): flutter_secure_storage 9.2.4 · app_links 6.4.1 · url_launcher 6.3.2 · drift 2.34.0 · sqlite3_flutter_libs 0.5.42 · connectivity_plus 6.1.5 · path_provider 2.1.6. flutter_riverpod 3.3.2 · go_router 14.8.1(web과 정렬).

## 4. 후속 (슬라이스 #10 잔여)
- **Build D — FCM**: NotificationService 추상 + firebase_messaging 배선 + 네이티브 설정 + 페이크 테스트. 실 Firebase 연결 follow-up.
- **모바일 실API 인증 계약**(백엔드): OAuth 성공 시 `devpath://callback?access_token&refresh_token` 리다이렉트 + 토큰-바디 `/auth/refresh`.
- **콘텐츠 스크롤 진척 자동 추적**: 현재는 "완료로 표시" 수동. web의 스크롤·체류 추적은 후속.
- **온보딩**: 모바일 진단/온보딩 흐름(현재 게이트 미적용).

## 5. 관련
- 플랜/핸드오프: `handoff-2026-06-27-slice10-abc-done-d-next.md`.
- 코드: PR #39(A+B → develop), PR #40(C → feat/slice10-mobile-core, 스택).
