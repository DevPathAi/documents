# 정합성 3차 — 축④ TDD 갭(프론트)

## 기준

- 대상 레포: `devpath-frontend` (Flutter 모노레포, Melos)
- 기준 SHA: `e6be351fa066ca05a084ff6963d2ce107709a6fe` (origin/develop)
  - 확인: `git -C D:\workspace\dpa\devpath-frontend rev-parse origin/develop` → `e6be351…`
- 기준 문서: `documents` origin/develop `11_테스트_전략서.md` 의 Flutter 단위/위젯 계층 규정
  - `## 3. 프런트엔드 테스트`: **flutter_test(위젯·단위) + flutter_riverpod `ProviderContainer`**, **골든 테스트**(`flutter test`, 시각 회귀), **integration_test E2E**, **SSE 스트리밍 mock(Path 생성 / Mentor)**
  - `## 4. 모바일 테스트(Flutter)` 레벨표: 단위=`flutter test`, 위젯=`flutter test`, 통합=`integration_test`, 실기기 회귀=Android·iOS 각 3종 스모크
  - 피라미드(§1): Unit 75%(JUnit5, Flutter test) / Integration 20% / E2E 5%(Playwright(Web) + **Flutter integration_test**)
  - 커버리지 게이트(§소스 216·231행): Mobile(Flutter) ≥ 65%
  - 골든: `test/golden/` 디렉토리에 입력+기대 쌍 저장 규정
- 요지: 문서는 (a) 위젯·단위 flutter_test, (b) 골든(시각 회귀), (c) integration_test E2E, (d) Path/Mentor SSE mock 스트리밍 회귀를 프론트 테스트 계층으로 명시.

## 방법

- 파일 목록: `git -C D:\workspace\dpa\devpath-frontend ls-tree -r origin/develop --name-only` → 앱(apps/admin·apps/mobile·apps/web)·패키지(packages/dp_core·packages/dp_design)별 `lib/` 기능 디렉토리와 `test/` 파일 대조.
- SSE/ApiClient 회귀: `git -C … grep -lnE 'SseClient|ApiClient' origin/develop` 결과를 `/test/`로 필터.
- realapi 회귀 잔존: `git -C … grep -cE 'realApi|realapi|RealApi' origin/develop -- <파일들>` 및 파일명 존재 확인.
- integration_test 존재: `ls-tree … | grep -iE integration_test` (결과 없음).
- 코드 레포 읽기 전용(ls-tree/grep/show만). 상태 변경 명령 미사용.

## 실측

### (1) 앱/패키지별 기능 → 테스트 유무 표

#### apps/web (주력 앱)
| 기능(화면/서비스) | lib 경로 | 대응 테스트 | 유무 |
|---|---|---|---|
| auth(login/callback/controller) | features/auth | auth_controller_test, login_page_test, providers/auth_interceptor_wire_test | O |
| beta_pending 화면 | features/beta | features/beta/beta_pending_page_test | O |
| community(home/qna/question_create) | features/community | community_controller/community_home_page/qna_detail_controller/qna_detail_page/question_create_page/lcs_source_test | O |
| consent | features/consent | consent_controller_test, consent_page_test | O |
| content(viewer/progress) | features/content | content_controller/content_page/content_progress_tracker_test | O |
| dashboard | features/dashboard | dashboard_controller_test, dashboard_page_test | O |
| diagnostic(온보딩 진단) | features/diagnostic | diagnostic_controller_test (page 테스트 없음) | 부분 |
| mentor(SSE) | features/mentor | mentor_controller/mentor_page/mentor_state/mentor_sse_source/**mentor_sse_realapi**_test | O |
| mypage | features/mypage | mypage_controller_test (page 테스트 없음) | 부분 |
| path(SSE) | features/path | path_controller/path_page/path_plan_view/path_sse_source/**path_sse_realapi**_test | O |
| review | features/review | review_controller_test, review_panel_test | O |
| sandbox(run/monaco/layout) | features/sandbox | run_controller(+session)/run_state/monaco_editor_view/sandbox_layout/sandbox_page/**sandbox_run_sse_realapi**/sandbox_review_smoke_test | O |
| settings | features/settings | settings_controller_test, settings_page_test | O |
| shell(app_shell) | features/shell | app_shell_view_test | O |
| common/placeholder_page | features/common | (없음) | X |
| providers(api/gate/theme) | src/providers | api_providers_test, onboarding_gate_interceptor_test, theme_provider_test, auth_interceptor_wire_test | O |
| golden path(온보딩/스모크/T1) | (앱 전역) | golden_path_onboarding/golden_path_smoke/golden_path_t1_realapi_test | O |

#### apps/admin
| 기능 | lib 경로 | 대응 테스트 | 유무 |
|---|---|---|---|
| auth(login/callback/oauth) | features/auth | auth_controller_test, bootstrap_callback_test, oauth_login_test | O |
| dashboard | features/dashboard | dashboard_page_test (controller 단독 테스트 없음, page에 포함) | 부분 |
| reports | features/reports | reports_page_test (controller 단독 없음) | 부분 |
| users(approve/beta) | features/users | users_controller_test, users_page_test, users_page_beta_test, approve_test | O |
| shell(admin_shell) | features/shell | (전용 없음; admin_smoke_test/app/admin_guard_test에서 간접) | 부분 |
| providers | src/providers | providers/auth_interceptor_wire_test | O |
| 전역 스모크/가드 | — | admin_smoke_test, app/admin_guard_test | O |

#### apps/mobile
| 기능 | lib 경로 | 대응 테스트 | 유무 |
|---|---|---|---|
| auth(controller/callback/pkce/deep_link/oauth) | features/auth | auth_controller_test, auth/auth_callback_test, pkce_test (deep_link/oauth_launcher 단독 없음) | 부분 |
| community(home/qna/quick_capture) | features/community | community_page/community/qna_detail_controller/qna_detail_page/quick_capture_page_test | O |
| dashboard(+drift cache) | features/dashboard | dashboard_controller_test, dashboard_page_test (drift_dashboard_cache 단독 없음) | 부분 |
| learning(learn/content/progress) | features/learning | learn_controller/learn_page/content_controller/content_progress_tracker/content_viewer_page_test | O |
| notifications(+device_registrar) | features/notifications | notification_controller/notifications_page/device_registrar_test | O |
| onboarding | features/onboarding | onboarding_controller_test, onboarding_page_test | O |
| shell(mobile_shell) | features/shell | mobile_shell_test | O |
| auth secure store | src/auth | auth/secure_storage_token_store_test | O |
| data(app_database/key_value) | src/data | data/app_database_test (key_value_store/secure_key_value_store 단독 없음) | 부분 |
| services(connectivity/push) | src/services | services/push_service_test (connectivity_service 단독 없음) | 부분 |
| providers(theme) | src/providers | providers/theme_provider_test (api_providers 단독 없음) | 부분 |

#### packages/dp_core
| 기능 | lib 경로 | 대응 테스트 | 유무 |
|---|---|---|---|
| ApiClient/config | src/api/api_client, api_config | api/api_client_test, api/api_client_sse_test | O |
| assessment_api / page | src/api | assessment_api_test, page_test | O |
| auth interceptor/token_store | src/auth | auth/auth_interceptor_test (token_store 단독 없음) | 부분 |
| error(code/exception) | src/error | error/api_exception_test, api_exception_contract_test | O |
| mock(http adapter/sse) | src/mock | mock/mock_test, mock_query_test | O |
| SseClient/sse_event | src/sse | sse/sse_client_test, sse_client_error_test | O |
| models(assessment/code_review/community/dashboard/lcs/learning_content/learning_path/my_activity/path_sse_event/profile_view/user/beta_status/enums) | src/models | assessment/beta_status/code_review/dashboard_community/learning_content/learning_path/path_sse_event/user_test (**profile_view·lcs_snapshot·my_activity·enums 모델 단독 테스트 없음**) | 부분 |

#### packages/dp_design
| 기능 | lib 경로 | 대응 테스트 | 유무 |
|---|---|---|---|
| a11y/dp_tap_target | src/a11y | a11y/dp_tap_target_test | O |
| content/dp_markdown | src/content | content/dp_markdown_test | O |
| icons/dp_icons | src/icons | icons/dp_icons_test | O |
| states(9종: empty/error/kill_switch/loading/offline_banner/quota/sandbox_unavailable/sse_stage/state_scaffold) | src/states | states/backend_states_test, base_states_test + golden/state_golden_test | O(묶음) |
| theme(colors/spacing/typography/theme) | src/theme | theme/dp_colors_test, dp_typography_test (spacing·dp_theme 단독 없음) | 부분 |

### (2) 위젯/단위 테스트가 전무한 화면(페이지) 목록

페이지(presentation) 파일 중 **직접 대응 위젯 테스트가 전무**하거나 controller 테스트만 있고 page 테스트가 없는 화면:

- apps/web `features/common/presentation/placeholder_page.dart` — 대응 테스트 전무(X)
- apps/web `features/diagnostic/presentation/diagnostic_page.dart` — page 위젯 테스트 없음(controller만 존재)
- apps/web `features/mypage/presentation/mypage_page.dart` — page 위젯 테스트 없음(controller만 존재)
- apps/admin `features/dashboard/presentation/dashboard_page.dart` — page_test 존재하므로 해당 없음(참고: controller 단독 없음)
- apps/mobile `features/auth/presentation/login_page.dart` — login_page 위젯 테스트 없음(controller/callback만)

주: apps/web·mobile의 나머지 모든 page는 `*_page_test.dart`가 존재. admin은 dashboard/reports/users page 모두 page_test 보유.

### (3) SSE / ApiClient 회귀 테스트 존재 목록

`grep -lnE 'SseClient|ApiClient' origin/develop` → `/test/` 필터 결과 중 핵심:
- packages/dp_core: `api/api_client_test.dart`, `api/api_client_sse_test.dart`, `sse/sse_client_test.dart`, `sse/sse_client_error_test.dart` (ApiClient·SseClient 단위/에러 회귀 O)
- apps/web: `features/path/path_sse_realapi_test.dart`, `features/mentor/mentor_sse_realapi_test.dart`, `features/sandbox/sandbox_run_sse_realapi_test.dart` (Tier-2 실계약 SSE 회귀 3종 전부 잔존 O)
- 추가 SSE source 단위: `path_sse_source_test`, `mentor_sse_source_test`

Tier-2 실계약 회귀 3종 확인(파일명):
- 경로 생성 SSE → `apps/web/test/features/path/path_sse_realapi_test.dart` (O)
- sandbox SSE → `apps/web/test/features/sandbox/sandbox_run_sse_realapi_test.dart` (O)
- mentor SSE → `apps/web/test/features/mentor/mentor_sse_realapi_test.dart` (O)
- 골든 T1 실계약 → `apps/web/test/golden_path_t1_realapi_test.dart` (O, `realApi` 참조 1건)

integration_test: `ls-tree | grep -i integration_test` → **결과 없음**(레포 내 integration_test 디렉토리/파일 부재).

## 갭 후보

| 갭 | 근거 | 등급 | 보강 제안(테스트 경로) |
|---|---|---|---|
| integration_test E2E 전무 | 문서 §1/§3/§4가 Flutter integration_test E2E를 명시하나 ls-tree에 integration_test 디렉토리·파일 0건 | P1 | `apps/web/integration_test/golden_path_test.dart`(온보딩→path SSE→sandbox 골든패스). 실기기 통합은 별도 |
| diagnostic 화면 위젯 테스트 없음 | features/diagnostic/presentation/diagnostic_page.dart 대응 page_test 부재(controller만) | P1 | `apps/web/test/features/diagnostic/diagnostic_page_test.dart` |
| mypage 화면 위젯 테스트 없음 | features/mypage/presentation/mypage_page.dart 대응 page_test 부재(controller만) | P1 | `apps/web/test/features/mypage/mypage_page_test.dart` |
| mobile login_page 위젯 테스트 없음 | apps/mobile login_page.dart 위젯 테스트 부재 | P2 | `apps/mobile/test/features/auth/login_page_test.dart` |
| dp_core 모델 단독 테스트 결손 | profile_view·lcs_snapshot·my_activity·enums 모델에 단독 (de)serialize 테스트 없음 | P2 | `packages/dp_core/test/models/{profile_view,lcs_snapshot,my_activity}_test.dart` |
| mobile 오프라인/커넥티비티 서비스 테스트 없음 | connectivity_service.dart·drift_dashboard_cache.dart 단독 테스트 부재 | P2 | `apps/mobile/test/services/connectivity_service_test.dart`, `.../dashboard/drift_dashboard_cache_test.dart` |
| placeholder_page 테스트 전무 | common/placeholder_page.dart 무테스트 | P2 | 저위험(정적 위젯). 스모크 1건 또는 판정보류 |
| admin controller 단독 테스트 결손 | dashboard/reports controller가 page_test에 간접 커버(단독 없음) | P2 | `apps/admin/test/features/{dashboard,reports}/*_controller_test.dart` |
| dp_design spacing/theme 단독 테스트 결손 | dp_spacing·dp_theme 단독 테스트 없음(states/colors/typography는 존재) | P2 | `packages/dp_design/test/theme/dp_theme_test.dart` |
| dp_core token_store 단독 테스트 없음 | auth_interceptor_test에서 간접, token_store 단독 부재 | P2 | `packages/dp_core/test/auth/token_store_test.dart` |

## 관찰

- Tier-2 실계약 SSE 회귀(path·sandbox·mentor) 3종과 골든 T1 realapi가 모두 잔존 확인됨 — MEMORY의 Tier-2 완결 기록과 정합. ApiClient·SseClient 단위/에러 회귀도 dp_core에 존재.
- 가장 명확한 문서-실측 격차는 **integration_test E2E 부재**(문서는 명시, 레포는 0건). 다만 앱별 golden_path_smoke/onboarding/t1_realapi 위젯 테스트가 E2E 시나리오를 상당 부분 대체 중이라 P0가 아닌 P1로 제안. 최종 등급·우선순위 판정은 축⑦(정합성 3차 종합 보고서) 및 리팩토링 실행계획서에서 컨트롤러가 확정.
- diagnostic/mypage page 무테스트는 controller 테스트가 로직을 커버하므로 위젯 렌더 회귀에 한정된 갭. P1/P2 경계는 컨트롤러 판정 보류.
- 커버리지 게이트(Mobile ≥65%) 실측치는 이 점검(정적 파일 대조)으로는 산출 불가 — 실행 커버리지 측정은 별도 CI 산출물 필요(판정 보류).
