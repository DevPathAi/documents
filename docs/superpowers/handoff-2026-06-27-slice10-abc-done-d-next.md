# 핸드오프 — 슬라이스 #10(모바일) A·B·C 완료 / 다음 = Build D(FCM) (2026-06-27)

> 다음 세션 이관용. **슬라이스 #10(모바일) Build A+B+C 완료·develop 머지 완료**(PR #39·#40·#46 머지). 빈 카운터 스캐폴드였던 `apps/mobile`이 실제 앱 골격(셸·인증·딥링크·오프라인 대시보드·학습 뷰어·퀵 캡처)으로. 남은 = **Build D(FCM)** + 모바일 실API 인증(백엔드) + 온보딩. **WSL+Bash 메인 직접 진행.**

## 1. 종착점 — 슬라이스 #10 A/B/C ✅
- **A 기반/셸/인증/딥링크**: dp_core 재사용 ApiClient+모바일 토큰 AuthInterceptor, AppConfig(목 기본), StatefulShellRoute 하단탭 셸(홈·학습·커뮤니티)+gateRedirect, SecureStorageTokenStore(+KeyValueStore 추상), OAuth 딥링크(devpath://callback 파서·DeepLinkService(app_links)·url_launcher·네이티브 intent-filter/URL scheme).
- **B 오프라인+대시보드**: drift 읽기 캐시(DashboardCache 추상)+connectivity_plus 재연결 자동 재동기화+홈 대시보드(스트릭·진척·다음과제, 오프라인 DpOfflineBanner).
- **C 학습 뷰어+퀵 캡처**: LearnPage(경로)·ContentViewerPage(DpMarkdown+완료보고), CommunityPage(목록+FAB)·QuickCapturePage(질문 게시). /learn·/community 서브라우트.
- 검증: melos analyze/format 그린, test 그린(**mobile 45** = A+B 32 + C 13 · web 147 · dp_core 48 회귀 무변).
- 보고서 `reports/2026-06-27-slice10-mobile-abc-build-report.md`.

## 2. PR/머지 상태 (머지 완료)
- **머지 완료**: PR #40(C→core)·#39(core→develop)·docs #46 모두 머지. **frontend `develop` HEAD `11b32c1`**에 A+B+C 통합, **documents `develop` `f08276a`**에 리포트·핸드오프 통합. 기능/문서 브랜치 삭제됨.
- 두 코드 PR 원격 CI(`analyze-test`) pass 후 머지. 결합 트리(A+B+C) 로컬 게이트(melos analyze/format/test)도 녹색.
- **`main` 릴리스 미진행**(develop 통합까지만). frontend는 deploy 잡 없음(릴리스만). gitops 주의 [[gitops-deploy-bot-main-drift]] — 모바일 슬라이스엔 무관.
- 다음 세션: develop 최신(`git pull`)에서 새 작업 브랜치(`feat/slice10-mobile-d` 등) 분기.

## 3. 남은 작업 (슬라이스 #10)
- **Build D — FCM 푸시** (다음 진입점): NotificationService 추상 인터페이스 + firebase_messaging 배선 + 네이티브 설정(google-services.json 자리/APNs 권한) + **페이크 테스트**. **실 Firebase 프로젝트 연결(google-services.json/APNs 키)은 후속** — 사용자 승인 결정(추상화+네이티브+페이크로 구현, 실연동 deferred). 토큰 등록 시 백엔드 전달 엔드포인트는 계약 확인 필요.
- **모바일 실API 인증 계약(백엔드 과제)**: 현 백엔드 **쿠키 기반**. 모바일용 `devpath://callback?access_token&refresh_token` 리다이렉트 + 토큰-바디 `/auth/refresh` 필요. 추가 전엔 목(useMock=true)으로 동작. 앱 측 구조(딥링크·토큰스토어·refresh 콜백)는 이미 준비됨.
- **온보딩**: 모바일 온보딩/진단 흐름 미구현(현재 게이트는 온보딩 미검사, 목 사용자 DONE 가정).
- **콘텐츠 스크롤 진척 자동 추적**: 현재 "완료로 표시" 수동. web의 scroll/dwell 추적 미이식.

## 4. 환경/도구 (필수 — [[wsl-build-environment]]·[[slice10-mobile-progress]])
- **PATH**: `export PATH="$HOME/flutter/bin:$HOME/.pub-cache/bin:$PATH"`(비대화 셸에 flutter/melos 미등록). Flutter 3.44.4/Dart 3.12.2.
- **게이트(루트)**: `melos run analyze` · `melos run test` · `melos run format`(CI 게이트, `dart format --set-exit-if-changed .` — 생성 파일 포함). 단일 앱: `cd apps/mobile && flutter analyze/test`.
- **워크스페이스**: Dart pub workspaces — 루트 `flutter pub get`이 전 멤버 해석(apps/mobile 신규 의존성도). pubspec.lock 단일.
- **drift 코드젠**: 테이블 변경 시 `cd apps/mobile && dart run build_runner build`(→ `app_database.g.dart` 커밋). libsqlite3.so 가용 → 테스트 `NativeDatabase.memory()` 동작.
- **riverpod 3.x 테스트 주의**: Notifier가 `ref.listen`한 provider(예: connectivity 재연결)를 테스트할 때 `container.read(provider.notifier)`만으론 리스너 그래프가 유지 안 됨 → `container.listen(provider, (_,_){})`로 활성 구독 유지(화면 ref.watch 모사). AsyncValue엔 `valueOrNull` 없음 → `switch(AsyncData(:final value))`.
- 목 픽스처: `apps/mobile/lib/src/data/mobile_mock_fixtures.dart`(enum 와이어 대문자=web과 정합).

## 다음 세션 진입점
**Build D — FCM 푸시**: NotificationService 추상 + firebase_messaging + 네이티브 설정 + 페이크 테스트(실 Firebase는 후속). 그 전/병행으로 PR #40→#39 머지. 이후 #11 랜딩 → 평판 기초(스케줄 `17_§9`·§3 Tier-2). WSL 메인 직접 진행 가능.
