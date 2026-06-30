# 핸드오프 — 슬라이스 #10(모바일) Build D(FCM) 완료 / 다음 = #11 랜딩(P7) (2026-06-30)

> 다음 세션 이관용. **직전 핸드오프(`handoff-2026-06-27-slice10-abc-done-d-next.md`)는 stale**다 — 그 문서는 frontend `develop` `11b32c1` 시점에 "D 다음"으로 적혔으나, **같은 날(06-27) PR #41~#54가 이어 머지되며 Build D(FCM)와 그 외 잔여 항목까지 끝났다.** 본 문서는 2026-06-30 실측 기준이며, frontend `develop` HEAD = `62c161e`.

## 1. 종착점 — 슬라이스 #10 모바일 = 코드 레벨 사실상 완료 ✅

A·B·C(직전 핸드오프)에 더해 **D + 핸드오프가 "남음"으로 적었던 항목들까지 develop 머지 완료**.

| 항목 | 산출물 | 근거(커밋/PR) |
|---|---|---|
| **Build D — FCM 추상화 + 알림센터** | `PushService`(추상)·`StubPushService`(페이크)·알림센터 화면/컨트롤러/상태 | `2b3610b` / PR #41 |
| **Build D — 실 FcmPushService 골격 + 의존성** | `FcmPushService`(토큰·`onMessage`), `firebase_core ^4.11.0`·`firebase_messaging ^16.4.1` | `95003a2` / PR #42 |
| **Build D — 실 결선 준비** | `main` 초기화 게이팅(`USE_MOCK=false`만 `Firebase.initializeApp`) + 백그라운드 핸들러 + 네이티브 설정(Android 권한/google-services 조건부 플러그인, iOS 백그라운드/entitlements) | `8f2481f` / PR #48 |
| **디바이스 토큰 등록** | 로그인 후 `POST /notifications/devices` 등록 / 로그아웃 시 DELETE — `device_registrar.dart` | `a71ca7b` / PR #51 |
| 콘텐츠 진척 자동 추적 | (직전 핸드오프 §3 "남음" → 처리됨) | PR #43 |
| 온보딩 게이트 | (직전 핸드오프 §3 "남음" → 처리됨) | PR #44 |
| 모바일 실API 인증(PKCE·OAuth client type) | (직전 핸드오프 §3 "백엔드 과제" → frontend측 처리됨) | PR #49·#50 |
| 부가: QnA 상세·콘텐츠 메타·테마 토글 | | PR #45·#46·#47 |

- 모바일 FCM 소스: [push_service.dart](../../apps/mobile/lib/src/services/push_service.dart) · `lib/src/features/notifications/{application,presentation,state}/*`
- 페이크 테스트 4종: `test/services/push_service_test.dart` · `test/features/notifications/{device_registrar,notification_controller,notifications_page}_test.dart`
- 실 FCM 결선 가이드: [apps/mobile/docs/FCM_SETUP.md](../../apps/mobile/docs/FCM_SETUP.md) — "클라이언트 결선 완료, 남은 건 외부 설정뿐".

## 2. 검증 (2026-06-30, frontend `develop` 62c161e)

루트에서 `dart pub global run melos run <cmd>`(PATH 미설정 Windows 셸 — `melos` 직접 호출 불가, `dart pub global run melos` 사용):
- `analyze` ✅ 전 멤버 No issues
- `format` ✅ 294 파일 0 changed (CI 게이트 `dart format --set-exit-if-changed .`)
- `test` ✅ **web 147 · mobile 100 · dp_core 48 · dp_design 19 · admin 12** 전부 PASS

## 3. 남은 deferred (슬라이스 #10) — 코드 변경 불필요, 외부/콘솔 작업

- **실 Firebase 외부 설정**(사용자 승인된 후속, 에이전트 대행 불가): Firebase 프로젝트 생성 → `apps/mobile/android/app/google-services.json`(현재 `.example`만) 배치 + iOS `GoogleService-Info.plist` + APNs 키. 절차는 `FCM_SETUP.md` §1~. 마치면 `--dart-define=USE_MOCK=false`로 실 FCM 동작.
- **모바일 실기기 끝단간 검증**: OAuth 딥링크(`devpath://callback`) 토큰 왕복 + FCM 수신 + 디바이스 토큰 등록을 실 백엔드(staging) 대상으로 1회 확인.

## 4. 다음 진입점 — #11 랜딩(P7)

스케줄(`17_스케줄.md` §2 MD3 슬라이스 #11): **landing(Jaspr SSG, standalone) 마케팅 페이지 + 전용 CI job + `<html lang="ko">` 주입.** 이후 평판 기초(`17_스케줄.md` §2 MD3 평판 기초 · §3 Tier-2).

- **선행 자산(미커밋, 활용)**: `documents`에 06-24 작성된 랜딩 검증 문서 2건이 **untracked로 남아있다** — `docs/superpowers/specs/2026-06-24-office-hours-landing-validation-design.md`, `docs/superpowers/plans/2026-06-24-landing-validation-test-plan.md`. (+ `.tier1-baseline.md`도 untracked.) #11 착수 시 이 spec/plan을 정식 커밋·반영 검토.
- P7 원 플랜: `docs/superpowers/plans/`의 P7 landing(Jaspr SSG) 항목(HANDOFF.md "미작성 플랜 없음" 참조).

## 5. 레포 위생 (착수 전 정리 권장)

서비스 레포 일부가 **이미 머지된 feature 브랜치에 체크아웃만 남아있음** — 작업 재개 전 각 레포 `develop` 전환 + `git pull`:
- `ai-svc` → `feat/slice8-community-seed`, `lcs-svc` → `feat/slice9-lcs-by-question`, `sandbox-svc` → `feat/slice7-sandbox-recent-sessions`, **`shared` → `main`**.
- 미커밋 변경은 전부 `.omc/`(툴링 상태)·platform-svc untracked `ai/`뿐 — **실작업 손실 없음**.

## 6. 환경/규칙 (필수)

- **Windows/PowerShell + Git Bash** 환경(직전 핸드오프의 WSL과 다름). Flutter 3.44.1 / Dart 3.12.1 / melos 7.8.2. flutter PATH: `export PATH="$HOME/flutter/bin:$PATH"`, melos는 `dart pub global run melos <cmd>`.
- **백엔드는 Java/Spring Boot 4**(Kotlin 아님). 디바이스 토큰 계약: `DeviceController` `@RequestMapping("/notifications/devices")`, body `{token, platform}`, Bearer 필요, 멱등 upsert.
- 브랜치 전략: `develop` 분기 → develop PR → 머지. main 직접 금지(릴리스 PR 제외). 커밋 전 `dart format`. 서브에이전트 Scope Lock + 컨트롤러 직접 검증.

## 7. 관련 메모리

- [[slice10-mobile-progress]] · [[wsl-build-environment]] · [[gitops-deploy-bot-main-drift]]
- 대시보드: https://devpathai.github.io/workflow-dashboard/
