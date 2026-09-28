# SDD ledger — plan: /d/workspace/dpa/.worktrees/documents-s3p5-plan/docs/superpowers/plans/2026-09-28-s3-p5-baseline-rerecord.md

Spec: `documents:docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` §7 P5 (읽음 — 도달 가능)
실행 범위: 이 SDD 세션은 **PR-1 = Task 1~11**. Task 12~17 은 사용자 결정으로 컨트롤러가 직접(Native) 수행한다.
워크트리: `D:\workspace\dpa\.worktrees\frontend-s3p5-20260928` · 브랜치 `feat/s3-p5-carryover` · base `eaa7f77`

## Task 0 (컨트롤러 직접 수행) — 완료

- 워크트리 생성 · `dart pub get` + `melos bootstrap` (4 packages)
- 기준선 실측 = **계획 예상과 일치**: dp_design **380** pass (+ golden 2건 로컬 실패 = `@Tags(['golden'])`, CI 는 `--exclude-tags golden` 으로 제외 ⇒ 정상) · dp_core **174** · admin **156** · web **1122**
- **Ruling: 로컬 툴체인이 쓰는 설정 파일 4개는 매 도구 실행마다 되돌린다.** `melos bootstrap`·`flutter test` 가 `apps/{admin,web}/analysis_options.yaml`·`packages/dp_design/analysis_options.yaml`(`analyzer: exclude: build/**` 추가)과 `pubspec.lock`(`intl` 0.20.2→0.20.3 · `matcher` 0.12.19→0.12.20)을 다시 쓴다. `pubspec.lock` 변경은 **CI 의 `dart pub get --enforce-lockfile` + lock sha256 동일성 검사를 깨뜨린다**. — 왜: 로컬 Flutter 3.47 ≠ CI 핀 3.44.1. — 틀렸을 때의 비용: 이 판단이 틀릴 여지는 없다(CI 가 lock sha256 을 직접 비교한다). 실행자에게 커밋 직전 되돌림을 의무로 부과한다.
- `packages/dp_design/test/golden/failures/` 는 골든 실패 산출물이며 추적되지 않는다 — 삭제했다.

## 사전 충돌 스캔 (Task 1~11)

### 파일·인터페이스를 공유하는 Task 쌍

| Task 쌍 | 공유 대상 | 한쪽이 만드는 것 ↔ 다른쪽이 쓰는 것 | 발견 |
|---|---|---|---|
| 3 ↔ 4 | `dp_next_action_band.dart` · 같은 테스트 파일 | 3 = `build` 의 `DecoratedBox` 에서 `boxShadow` 제거 / 4 = `_PrimaryAction.build` 의 `semanticLabel` 분기 | **충돌 없음** — 서로 다른 메서드, 서로 다른 단언. 3 의 테스트(`boxShadow isNull`)와 4 의 테스트(시맨틱 라벨)는 모순되지 않는다 |
| 5 ↔ 8 | `apps/web` (5 Step 5 가 `MaterialType.transparency` 중복을 걷어낸다 / 8 이 `mypage_page.dart` 를 고친다) | 5 = `DpPanel` 이 잉크 표면을 소유 / 8 = 마이페이지 머리·사이드 개편 | **순차라 충돌 없음.** 단 5 가 mypage 의 중복 `Material` 을 지웠다면 8 이 같은 영역을 다시 편집한다 → 8 의 dispatch 에 5 의 결과를 알린다 |
| 6 → 7 | 줄 높이 | 6 = 토큰의 `height` 가 merge 에서 이긴다 ⇒ 행 높이 변화 / 7 = 보기 목록 간격을 **측정**한다 | **순서 의존이 실재한다.** 6 이 7 보다 앞이어야 7 의 측정이 최종 렌더를 잰다. 계획 순서가 이미 그렇다 ✔ |
| 6 ↔ 5 | `dp_design` 전 스위트 | 6 = 텍스트 스타일 · 5 = 위젯 트리에 `Material` 한 겹 | **충돌 없음** — 5 의 테스트는 `Container` `.first`(패널 바깥 컨테이너)를 잡고, 6 은 텍스트만 만진다 |
| 2 ↔ 7 | `DpSteps` | 2 = `ValueKey('dp-step-<i>')` + 동일 높이 / 7 = 진단 화면이 `DpSteps` 를 소비 | **충돌 없음** — 7 은 `DpSteps` 를 편집하지 않는다. 2 의 높이 변화가 7 의 간격 측정 대상(보기 목록)과 다른 위치다 |
| 6 → 15(PR-2) | `DpWebDensity` | 6 이 정의 / 15 가 DESIGN.md 에 이름으로 문서화 | PR 경계를 넘는 의존. PR-1 이 먼저 머지되므로 문제 없다 |
| 1 ↔ 나머지 | `dp_cols.dart` | 1 = **주석만** 수정(코드 불변) | **충돌 없음** · 렌더 변화 0 |
| 9 ↔ 나머지 | `placeholder_page.dart` 삭제 | 소비처 0(실측) | **충돌 없음** |
| 10 ↔ 나머지 | `dp_nav_rail.dart` | admin 전용 | **충돌 없음** |

### Task 자체 정합성

| Task | 스스로 모순이 없는가 | 발견 |
|---|---|---|
| 1 | 테스트가 `DpTheme.light()`·`DpCols` 를 쓴다 | **발견 1**: 기존 `dp_cols_test.dart` 가 `DpTheme` 를 import 하고 있지 않을 수 있다 → 실행자가 import 를 더해야 한다. `package:dp_design/dp_design.dart` 가 `DpTheme`·`DpCols`·`DpColors` 를 모두 export 한다(확인) |
| 2 | 파일 경로 | 계획 초안이 `lib/src/widgets/dp_steps.dart` 로 적었으나 실제는 **`lib/src/layout/dp_steps.dart`**, 테스트는 **`test/layout/dp_steps_test.dart`** — 계획 병합 전에 고쳤다 ✔ |
| 3 | `DecoratedBox` `.first` 로 밴드의 바깥 장식을 잡는다 | 일치 ✔ (`build` 의 최상위가 `DecoratedBox` 다) |
| 4 | `disabled` 면 `disabledReason` 이 non-null 임을 가정 | 일치 ✔ — 생성자 assert 가 `state != disabled \|\| (disabledReason != null && disabledReason != '')` 를 보장한다 |
| 5 | `Column` 을 `Material` 로 감싸며 괄호 한 겹 증가 | 일치 ✔ |
| 6 | 테스트 스니펫의 `DpStatusText` 호출 | **발견 2 (실측으로 계획이 틀렸다)**: 실제 시그니처는 `DpStatusText({required String text, required DpStatusTone tone})` 로 **`text:` 가 named** 이고, tone 열거값은 `done`·`idle`·`current` 다 — 계획 스니펫의 `DpStatusText('완료', tone: DpStatusTone.ok)` 는 **컴파일되지 않는다** |
| 7 | 세 건이 서로 다른 파일 | 일치 ✔ (M10a·M9 = `diagnostic_page.dart` / M11 = `dp_check_row_test.dart`) |
| 8 | `DpKeyValues.entries` 의 레코드 타입 | 일치 ✔ — `typedef DpKeyValue = ({String key, Widget value})` 이므로 `(key: '목표 트랙', value: Text(...))` 가 맞다 |
| 9 | 삭제 대상과 소비처 | 일치 ✔ (실측 0곳) |
| 10 | 래퍼 `Semantics(label:)` + 보이는 `Text` | 일치 ✔ (`:245` 와 `:264-267`) |
| 11 | 게이트 Task | 일치 ✔ |

### 스캔 결과에 대한 판정

- **Ruling(발견 2): Task 6 의 테스트 스니펫을 dispatch 에서 교정해 넘긴다.** 올바른 호출은 `DpStatusText(text: '완료', tone: DpStatusTone.done)` 다. — 왜: 계획은 병합됐고 스니펫 한 줄을 고치려 새 PR 을 내는 비용이 교정 전달 비용보다 크다. dispatch 의 「브리프의 모호함에 대한 컨트롤러 해석」 항목이 이 목적의 기제다. — 틀렸을 때의 비용: 없다(실측한 시그니처다). 계획 본문의 그 스니펫은 Task 17 의 원장에 정정으로 기록한다.
- **Ruling(발견 1): import 추가는 실행자의 재량으로 둔다.** — 왜: 계획이 이미 「기존 테스트 파일에 덧붙인다」고 했고 필요한 심볼이 전부 공개 API 에 있다. — 틀렸을 때의 비용: 컴파일 실패 한 번, 실행자가 즉시 본다.
- 리뷰 루브릭이 결함으로 볼 것을 계획이 명령하는 곳: **없다.** Task 1 은 「코드 불변 + 테스트 추가」이고 그 테스트는 네 경계값을 실제로 단언한다(빈 단언이 아니다). Task 9 의 삭제는 실측된 소비처 0 에 근거한다.

## 진행

### 계획 파일 결함 (실행 전 발견·수정)

- **Ruling: 병합된 계획의 닫히지 않은 코드 펜스를 별도 PR 로 즉시 고쳤다.** Task 1 Step 5 의 ` ```bash ` 블록이 닫히지 않아 펜스 수가 홀수(175)였고, `task-brief` 추출기가 펜스를 세어 Task 경계를 찾으므로 **Task 1 브리프가 1944줄(파일 끝까지)** 이 되고 **Task 2~17 이 `not found`** 가 됐다 — 실행을 시작할 수 없었다. — 왜: 계획 없이는 dispatch 가 불가능하고, 수정은 한 줄이다. — 틀렸을 때의 비용: 없다(펜스 수 176 짝수 · 브리프 11개가 53~192줄로 정상 추출됨을 확인). documents PR **#186** → develop **`2327853`**.
- documents 계획 PR **#185** → develop **`5e05a05`** (머지 완료).

### Dispatch 기록

- **Task 1+2 (배치)** — 같은 `dp_design` 소형 수정 두 건이고 브리프가 완전한 코드를 담고 있어 한 dispatch 로 묶었다. 모델 = haiku(전사 + 테스트). BASE = `eaa7f774490c48e5b1d92a827efad2b012a7363f`. 보고서 = `task-1-2-report.md`.
  - dispatch 에 실어 보낸 컨트롤러 해석 6건: 공개 API export 확인 · `dp_steps.dart` 실제 경로 · 골든 2건 로컬 실패는 정상(`--exclude-tags golden` 사용) · 기준선 380→기대 382 · **설정 파일 4개 커밋 직전 되돌림 의무** · 커밋 메시지 형식.

### 뒤 Task dispatch 를 위해 미리 실측한 이름 (계획 스니펫의 헬퍼 이름이 틀렸다)

계획은 「기존 pump 헬퍼 이름을 읽어 맞추라」고 지시했으나, 스니펫이 든 **가짜 이름이 실행자를 오도할 수 있으므로** 컨트롤러가 미리 실측해 dispatch 에 실어 보낸다.

| 계획 스니펫의 이름 | 실제 | 위치 |
|---|---|---|
| `_pumpDiagnosticStart(tester)` (Task 7) | **`_host(controller, {bool missionSpineEnabled, bool router})`** — `await tester.pumpWidget(_host(controller))` 형태로 쓴다 | `apps/web/test/features/diagnostic/diagnostic_page_test.dart:74` |
| `_pumpMyPage(tester)` (Task 8) | **`_host(MyPageState state, {MentorAccessState mentorAccess})`** — `await tester.pumpWidget(_host(const MyPageLoaded(...)))` 형태 | `apps/web/test/features/mypage/mypage_page_test.dart:36` |

- Task 7 의 진단 시작 CTA = `FilledButton(child: const Text('진단 시작하기'))` — `diagnostic_page.dart:337-343` (계획의 `find.widgetWithText(FilledButton, '진단 시작하기')` 가 맞다).
- Task 8 의 화면 상태 접근: `_Body` 가 `final st = widget.state; final p = st.profile;` 를 쓰고 `final trackLabel = trackLabels[p.targetTrack];` 가 `mypage_page.dart:134-136` 에 있다. 배지 계산은 `st.dashboard` 를 읽는다.
- Task 8 의 테스트 픽스처 `MyPageLoaded` 는 이미 `dashboard: DashboardSummary(streakDays: 3, progressPercent: 40, completedContentCount: 7)` 를 준다 — **`badges` 가 비어 있으므로 배지 태그 테스트는 `badges: ['첫 경로']` 를 더한 픽스처가 필요하다.** `streakDays: 3` 이면 배지 라벨은 `3일 연속` 이 된다(계획의 `7일 연속` 은 시안 예시 값이다 — 테스트는 픽스처 값에 맞춘다).

### Task 1+2 — 구현 보고 수령 · 컨트롤러 직접 검증

구현자 보고: **DONE**, 커밋 2개(`1ce8123`, `37f608d`), 우려 없음.

컨트롤러가 직접 확인한 것(보고를 신뢰하지 않음):

| 확인 | 결과 |
|---|---|
| 커밋 범위 `eaa7f77..HEAD` | **정확히 2개** — 지정한 것보다 더 커밋하지 않았다 ✔ |
| 바뀐 파일 | `dp_cols.dart`·`dp_steps.dart` + 두 테스트 = **4개뿐** (+94/−6) ✔ |
| 설정 파일 커밋 여부 | **커밋 안 됨** ✔ (워킹 트리의 드리프트는 구현자의 마지막 테스트 실행이 다시 쓴 것 — 컨트롤러가 되돌렸다) |
| `packages/dp_design` 전 스위트 (직접 실행) | **382 통과**(기준선 380 + 2) ✔ |
| `apps/web/test/features/diagnostic` (직접 실행) | **88 통과** ✔ |
| 인접 레포 스팟체크(documents) | 낯선 브랜치·커밋 **없음** ✔ (develop = `2327853`) |

- **보고서 정확성 결함 1건(코드 결함 아님)**: 보고서가 diagnostic 회귀를 「3 tests — claim_analytics_receipt, diagnostic_continuation」이라 적었으나 그 디렉터리에는 **6파일 · 88 테스트**가 있다. 구현자가 일부만 돌렸거나 잘못 셌다. 컨트롤러가 전체를 돌려 통과를 확인했으므로 회귀 위험은 닫혔다. — 다음 dispatch 부터 「회귀 확인은 디렉터리 전체를 돌리고 통과 **개수**를 보고하라」를 명시한다.
- review package = `review-eaa7f77..37f608d.diff`(8912 bytes). task reviewer(sonnet) dispatch 완료.

### 절차 결함 1건 (컨트롤러 실수) · 판정

- **Ruling: 앞으로 모든 리뷰어 dispatch 도 보고서를 파일로 받는다.** Task 1+2 의 task reviewer 는 작업을 마쳤지만 **최종 메시지가 유실**됐다(`No new instruction received — ending here.`) — 분석 전체를 잃을 뻔했다. 원인은 컨트롤러가 superpowers 의 task-reviewer 템플릿(「Your final message is the report itself」)을 그대로 따랐기 때문이다. 이 하네스에서는 **긴 최종 메시지가 유실될 수 있다**는 것이 이미 알려진 함정이고(메모리 `feedback-subagent-report-to-file`), 구현자에게는 적용했으면서 리뷰어에게는 적용하지 않았다. — 조치: 살아 있는 리뷰어를 재개해 같은 판정을 `task-1-2-review.md` 로 쓰게 했다(재리뷰가 아니라 기록만). 이후 리뷰어 dispatch 는 **① 보고서 파일 경로를 지정하고 ② 최종 메시지는 3줄(Spec 판정 / Task quality / Critical·Important·Minor 개수)로 제한**한다. — 틀렸을 때의 비용: 없다(파일은 유실되지 않는다). 토큰 비용은 리뷰어당 Write 한 번.

### Task 1+2 — 리뷰 결과 · 판정

리뷰(sonnet) = **Spec ✅ · Critical 0 · Important 1(plan-mandated) · Minor 2 · Task quality: Needs fixes.** 보고서 = `task-1-2-review.md`.

- **Ruling(Important · plan-mandated): 고친다.** 지적 = 새 테스트 두 개가 같은 파일의 `_host(Widget)`·`_size(WidgetTester, Size)` 헬퍼를 쓰지 않고 축자 중복했다. **컨트롤러가 직접 확인: 지적이 옳다** — `dp_cols_test.dart:5-17` 과 `dp_steps_test.dart:5-17` 에 두 헬퍼가 실재하고, `_size()` 에는 이 계획의 전역 제약과 **같은 MediaQuery 함정 주석**이 이미 달려 있다. 원인은 구현자의 일탈이 아니라 **계획(내가 쓴 Step 1 스니펫)이 인라인 형태를 명령**한 것이다. — 왜 고치는가: 스펙은 인라인 설정을 요구하지 않고, 레포의 관례(헬퍼 + 그 함정 주석)가 더 높은 권위다. 중복을 남기면 다음 사람이 함정 주석을 두 곳에서 관리하게 된다. 수정은 기계적이고 거동 변화가 없다. — 틀렸을 때의 비용: 테스트 두 개가 헬퍼 경유로 바뀌는 것뿐. 렌더·프로덕션 코드 영향 0.
- **Ruling(⚠️ 항목): 수용한다.** 지적 = `dp_cols.dart` 의 새 주석이 「근거는 DESIGN.md §5」를 가리키는데 그 근거 문단은 Task 15 가 쓴다(PR-2). **컨트롤러 확인: `DESIGN.md:185` 에 `## 5. 반응형` 절이 실재한다** — 가리키는 대상이 없는 인용이 아니라, 같은 단계(P5) 안의 전방 참조다. — 왜: PR-1 머지 후 PR-2 머지까지의 창에서만 그 절에 구체 문단이 없다. 한 단계 안에서 닫힌다. — 틀렸을 때의 비용: Task 15 가 그 문단을 빠뜨리면 주석이 빈 인용이 된다 → **Task 15 의 검증 항목으로 이월**(Task 15 Step 4 가 이미 `grep` 으로 확인하게 돼 있다).
- Minor 2건(보고서의 diagnostic 「3건」 서술 · `devicePixelRatio` 설정 순서)은 **deferred** 로 기록한다.
  - `Task 1+2: minor (deferred): 구현 보고서가 diagnostic 회귀를 3건으로 적었다(실제 6파일·88 테스트). 코드 결함 아님 — 컨트롤러가 전체 실행으로 이미 확인.`
  - `Task 1+2: minor (deferred): 새 테스트가 devicePixelRatio 를 physicalSize 보다 먼저 설정한다(_size 헬퍼는 반대 순서). 기능상 무관 — Important 수정으로 헬퍼를 쓰면 자동 해소된다.`
- 수정 라운드 1/5: 원 구현자(haiku)를 재개해 findings 를 그대로 전달. FIX_BASE = `37f608d`.

Task 1+2: fix round 1/5 (수정 커밋 `6b29852` — 컨트롤러 직접 확인: 두 테스트 파일만 변경(+12/−22), 인라인 블록이 `_size(...)`+`_host(...)` 호출로 바뀌었고 `expect` 줄은 diff 에 하나도 없다 = 단언 무변경. 직접 실행: 덮는 11건 통과 · `dp_design` 전체 **382** 통과 · 워킹 트리 깨끗). 범위 재리뷰(haiku) dispatch 완료 — 보고서 파일 계약 적용.
Task 1+2: 재리뷰 = Finding 1 **ADDRESSED** · 새 breakage 없음 · out-of-scope 없음 (`task-1-2-rereview.md`). 파일 계약을 적용하자 최종 메시지도 정상 도착했다 — 위 절차 판정이 유효함을 실증.
Task 1+2: minor (deferred): 구현 보고서가 diagnostic 회귀를 3건으로 적었다(실제 6파일·88 테스트). 코드 결함 아님 — 컨트롤러가 전체 실행으로 확인.
Task 1+2: minor (deferred): 새 테스트의 `devicePixelRatio`/`physicalSize` 설정 순서 — Important 수정으로 `_size()` 헬퍼를 쓰게 되어 자동 해소됨.
**Task 1+2: complete (commits eaa7f77..6b29852, review clean)**

### Task 3+4 — dispatch 준비로 실측한 것 (DRY 결함 재발 방지)

`packages/dp_design/test/mission/dp_next_action_band_test.dart` 에는 이미 헬퍼가 둘 있다:

- `Widget _host(Widget child, {ThemeData? theme, Size size = const Size(840, 700), double textScale = 1, bool disableAnimations = false})` (`:9`) — `MediaQuery` 를 **`MaterialApp` 의 `home` 안쪽**에 두므로 함정에 걸리지 않는 올바른 형태다.
- `DpNextActionBand _band({DpNextActionState state = ready, DpNextActionBandVariant variant = inline, ValueChanged<String>? onPressed, FocusNode? focusNode})` (`:28`) — `label: '이 맥락으로 실습 시작'`, `expectedOutcome: '현재 과제와 starter code가 실습으로 이어집니다.'`, disabled 일 때 `disabledReason: '현재 과제를 먼저 열어야 합니다.'` 를 이미 채운다.

⇒ 계획 Task 3·4 의 테스트 스니펫은 `MaterialApp(...)` 과 `DpNextActionBand(...)` 를 **인라인으로 구성**한다 — Task 1+2 에서 Important 로 잡힌 것과 **같은 축자 중복**이다. **Ruling: dispatch 에서 헬퍼 사용을 명시해 선제 차단한다.** 그러면 Task 4 의 기대 시맨틱 라벨은 `'이 맥락으로 실습 시작, 사용할 수 없음: 현재 과제를 먼저 열어야 합니다.'` 가 된다(계획 스니펫의 「경로 상태 확인 필요…」 문자열이 아니라). — 왜: 같은 결함을 두 번 잡게 두면 라운드 비용이 그대로 반복된다. — 틀렸을 때의 비용: 없다(헬퍼가 주는 문자열을 실측했다).
기존 테스트 9건 중 `:146 'ready/pending/disabled/retry/completed states are explicit'` 가 disabled → `'현재 과제를 먼저 열어야 합니다.'` 를 매핑한다 — Task 4 가 **시맨틱 라벨만** 바꾸므로 보이는 텍스트 단언이면 영향이 없다. 구현자에게 확인·보고를 지시한다.

### Task 5·6 — dispatch 전 실측 (계획 스니펫의 결함 선제 교정)

**Task 5 (`dp_panel_test.dart`)** — 헬퍼 두 개가 이미 있다: `Widget _host(Widget child, {Brightness brightness = Brightness.light})`(`:5`)와 **`BoxDecoration _decorationOf(WidgetTester tester)`**(`:11`, `DpPanel` 아래 첫 `Container` 의 decoration 을 꺼낸다). 기존 테스트 6건 중 `'표면색·1px 테두리·반경 8 의 컨테이너다'`(`:21`)가 이미 `_decorationOf` 로 `color`·`border.width/color`·`borderRadius` 를 단언한다. 색은 `DpTheme.light().extension<DpColors>()!` 가 아니라 **`const c = DpColors.light;`** 로 읽는 것이 이 파일의 관례다.

- **Ruling: 계획 Task 5 의 두 번째 테스트(「패널 표면 색·테두리·무그림자는 그대로다」)를 새로 추가하지 않는다.** 그 테스트의 단언 중 색·테두리는 기존 테스트와 **중복**이고, 새로운 것은 `boxShadow isNull` 하나뿐이다. 그 한 줄을 **기존 테스트에 더한다**(`_decorationOf` 가 바로 그 자리에 있다). 새로 추가하는 것은 **잉크 표면 테스트 하나**뿐이며 `_host(...)` 를 쓴다. — 왜: Task 1+2 에서 같은 축자 중복이 Important 로 잡혔고, 여기서는 테스트 자체가 중복이라 더 나쁘다. — 틀렸을 때의 비용: 없다. `Material` 한 겹을 `Container` 와 `Column` 사이에 넣어도 `_decorationOf` 의 `Container .first` 는 여전히 바깥 컨테이너를 잡으므로 기존 6건은 유효하다(실측으로 확인할 것).

**Task 6 (`dp_status_text_test.dart`)** — 헬퍼 `Widget _host(Widget child)`(`:5`)와 `Text _text(WidgetTester tester)`(`:10`)가 있고, 기존 테스트 4건이 **`DpStatusText(text: '✓ 완료', tone: DpStatusTone.done)`** 형태를 쓴다.

- **Ruling: 계획 Task 6 의 테스트 스니펫을 dispatch 에서 전면 교정한다.** 계획은 `DpStatusText('완료', tone: DpStatusTone.ok)` 라 적었는데 **① `text:` 가 named 이고 ② `ok` 라는 열거값이 없다**(`done`·`idle`·`current`) ⇒ 컴파일 불가. 또 `MaterialApp(...)` 인라인 구성은 `_host` 중복이다. 교정형: `_host(const DpStatusText(text: '✓ 완료', tone: DpStatusTone.done))` + `_text(tester).style!` 로 `fontSize`·`fontWeight`·`height` 를 단언. — 틀렸을 때의 비용: 없다(실측한 시그니처·관례다).

**패턴 판정:** 계획의 테스트 스니펫이 **세 Task 연속**으로 기존 헬퍼를 중복했다(1·2 에서 실제로 Important 가 됐고, 3·4·5·6 은 선제 차단). 원인은 계획 작성 시 소스 파일만 읽고 **테스트 파일의 헬퍼를 읽지 않은 것**이다. — **Ruling: 남은 모든 Task 는 dispatch 전에 그 Task 가 건드릴 테스트 파일의 상단 헬퍼를 컨트롤러가 먼저 읽고, 교정형을 dispatch 에 싣는다.** Task 17 의 원장에 계획 본문 정정으로 기록한다.

### Task 3+4 — 구현 보고 수령 · 컨트롤러 직접 검증

구현자 보고: **DONE**, 커밋 2개(`900492c`, `296b0fa`).

| 확인 | 결과 |
|---|---|
| 커밋 범위 `6b29852..HEAD` | **정확히 2개** ✔ |
| 바뀐 파일 | `dp_next_action_band.dart`(+9/−8) + 그 테스트(+43) = **2개뿐** ✔ |
| 설정 파일 커밋 | **안 됨** ✔ |
| 소스 diff 직접 확인 | Task 3 = `boxShadow` 블록 삭제 + 근거 주석 · Task 4 = `semanticLabel` 만 상태별 분기(보이는 텍스트 무변경) ✔ |
| 테스트가 헬퍼를 썼는가 | **`_host(_band(...))` 로 정확히 재사용** ✔ — 선제 교정이 먹혔다 |
| `packages/dp_design` (직접 실행) | **385 통과**(382 + 3) ✔ |
| `apps/web` (직접 실행) | **1122 통과**(변동 없음) ✔ = 소비처 12곳과 `:161` 기존 테스트 무사 |

- 구현자가 확인한 것: `:161 'ready/pending/disabled/retry/completed states are explicit'` 는 **보이는 텍스트**를 단언한다(`disabled → '현재 과제를 먼저 열어야 합니다.'`) ⇒ 시맨틱 라벨 변경에 영향 없음. `apps/web` 1122 유지가 이를 뒷받침한다.
- review package = `review-6b29852..296b0fa.diff`(6264 bytes). task reviewer(sonnet) dispatch — 파일 계약 적용 · 「`Semantics.hint` 중복 낭독 여부를 판정하라」를 명시적 위험으로 지시.

### Task 7 — dispatch 전 실측

- `packages/dp_design/test/interaction/dp_check_row_test.dart`(기존 6건)에 `Widget _host(Widget child)`(`:8`)와 `void _noop(bool _)`(`:6`)가 있고 **`package:flutter/services.dart` 를 이미 import** 한다 ⇒ 계획이 적은 「`LogicalKeyboardKey` 를 쓰려면 import 를 더한다」는 **불필요하다**. M11 테스트는 `_host(Column(children: [DpCheckRow(..., onChanged: _noop), DpCheckRow(..., onChanged: _noop, last: true)]))` 형태로 쓴다.
- `apps/web/test/features/diagnostic/diagnostic_page_test.dart` 의 pump 헬퍼는 **`_host(controller, {bool missionSpineEnabled, bool router})`**(`:74`)이며 `await tester.pumpWidget(_host(controller))` 로 쓴다 — 계획 스니펫의 `_pumpDiagnosticStart(tester)` 는 실재하지 않는다.

### Task 3+4 — 리뷰 결과 · 판정

리뷰(sonnet) = **Spec ✅ · Critical 0 · Important 1(plan-mandated) · Minor 0 · Needs fixes.** 보고서 = `task-3-4-review.md`.

- **Ruling(Important · plan-mandated): 고친다. disabled 일 때 `hint` 를 `null` 로 둔다.** 지적 = `dp_next_action_band.dart:208-212` 에서 `Semantics.label` 이 이제 `'…, 사용할 수 없음: <이유>'` 를 담는데 같은 노드의 `hint` 도 여전히 `disabledReason` 이라, 스크린리더가 `label` 과 `hint` 를 이어 읽어 **같은 문장을 두 번** 낭독한다. **컨트롤러가 소스로 확인: 지적이 옳다** — `hint:` 는 disabled 일 때 `widget.disabledReason` 그대로다. 원인은 구현자가 아니라 **내가 쓴 계획**이다(Task 4 의 결정문에 「`disabledReason` 은 이미 `Semantics.hint` 로도 실려 있으므로 라벨에서 중복을 피해 `hint` 는 그대로 둔다」고 적었는데, **라벨에 이유를 넣으면서 hint 를 남기는 것이 곧 중복**이라는 것을 보지 못했다). M7 이 고치려던 목표가 「정확한 낭독」이므로 이 회귀는 목표와 정면으로 부딪힌다.
  - **왜 `hint: null` 쪽인가**(리뷰어가 제시한 두 선택지 중): `label` 은 항상 낭독되지만 `hint` 는 스크린리더의 상세도 설정에 따라 **생략될 수 있다**. 이유를 `label` 에 두면 어떤 설정에서도 들린다. 반대 선택(label 에서 이유를 빼고 hint 에 남기기)은 상세도를 낮춘 사용자에게 이유가 사라진다.
  - **라벨 문구는 그대로 둔다**(`'…, 사용할 수 없음: <이유>'`). `enabled: false` 가 이미 「사용 안 함」을 알리므로 「사용할 수 없음」이 다소 중복이라는 지적은 가능하지만, 두 리뷰어 중 누구도 제기하지 않았고 그 문구는 사용자가 승인한 계획의 것이다 — 발견 범위를 넘는 문구 변경은 하지 않는다.
  - **틀렸을 때의 비용**: disabled 밴드의 스크린리더 낭독에서 이유가 한 번만 들린다(현재는 두 번). 시각 렌더 영향 0. 되돌리려면 한 줄이다.
- ⚠️(커밋 메시지 본문의 `Co-Authored-By` 줄은 diff 로 확인 불가) — **컨트롤러가 직접 확인**한다(아래).
- 수정 라운드 1/5: 원 구현자(haiku) 재개. FIX_BASE = `296b0fa`.
- **Ruling(⚠️ 후속 · 컨트롤러 실측): 커밋 트레일러 불일치를 「파킹」한다 — 이력을 다시 쓰지 않는다.** 실측: `900492c`·`296b0fa` 의 트레일러가 **`Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>`** 이다(앞의 `1ce8123`·`37f608d`·`6b29852` 는 규약대로 `Claude Opus 5 (1M context)`). 구현 에이전트의 하네스가 자기 트레일러를 주입한 것으로 보인다. — 왜 고치지 않는가: 고치려면 `filter-branch` 등으로 **이력을 다시 써야 하고**, 그러면 원장에 기록한 SHA 들이 전부 무효가 된다. 원장의 SHA 는 컨텍스트가 압축돼도 살아남는 **복구 지도**이고(이 스킬의 명시적 설계), 그 안정성이 트레일러 한 줄의 표기 일관성보다 값지다. 트레일러 자체는 **거짓이 아니다**(실제로 haiku 가 작성했다). — 틀렸을 때의 비용: PR 의 5커밋 중 2개가 다른 공저자 줄을 갖는다. 코드·CI 영향 0. 사용자가 원하면 머지 전에 squash 나 재작성으로 정리할 수 있다. **PR 본문과 최종 보고에 명시한다.**
- 조치: 남은 모든 implementer dispatch 에 「커밋 뒤 `git log -1 --format=%B` 로 트레일러가 정확히 `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` 인지 확인하고, 다르면 **그 커밋에 한해** `git commit --amend` 로 고쳐라」를 넣는다(자기 커밋을 직후에 고치는 것은 이력 재작성이 아니다).

Task 3+4: fix round 1/5 (수정 커밋 `79eb4c0` — 컨트롤러 직접 확인: `hint:` 세 줄이 근거 주석으로 대체되고 `Semantics` 의 나머지 인자·`semanticLabel` 계산식은 무변경(+9/−3, 2파일). 더한 단언은 `tester.getSemantics(...).getSemanticsData().hint` 가 **비어 있음**을 재는 형태라 hint 가 돌아오면 실패한다 = 판별력 있음. **트레일러가 규약대로 `Claude Opus 5 (1M context)` 로 들어갔다** — dispatch 에 넣은 확인 지시가 작동했다. 직접 실행: `dp_design` **385** · `apps/web` **1122** 유지). 범위 재리뷰(haiku) dispatch.
Task 3+4: 재리뷰 = Finding 1 **ADDRESSED** · 새 breakage 없음 · out-of-scope 없음 (`task-3-4-rereview.md`).
Task 3+4: parked — 커밋 `900492c`·`296b0fa` 의 `Co-Authored-By` 가 `Claude Haiku 4.5` 다 — Ruling: 이력을 다시 쓰지 않는다(원장 SHA 안정성 > 표기 일관성, 트레일러는 거짓이 아님). PR 본문에 명시한다.
**Task 3+4: complete (commits 6b29852..79eb4c0, review clean, 1 parked)**

### Task 5 — dispatch (이번 PR 에서 가장 위험이 큰 단계)

모델 = sonnet(세 패키지 회귀 + 판단). BASE = `79eb4c0`. 보고서 = `task-5-report.md`.

dispatch 에 실어 보낸 컨트롤러 교정 5건:
1. **브리프의 두 번째 테스트를 추가하지 말라** — 기존 `:21 '표면색·1px 테두리·반경 8 의 컨테이너다'` 와 중복이다. 새로운 단언은 `boxShadow isNull` 하나뿐이므로 **그 한 줄을 기존 테스트에 더한다.**
2. 새 잉크 테스트는 `_host(...)` 를 쓰고 색은 `const c = DpColors.light;` 관례를 따른다.
3. `_decorationOf` 가 `Container .first` 를 잡으므로 `Material` 한 겹 삽입이 그 관계를 깨는지 **기존 6건 통과로 실증**하라. 깨지면 테스트를 느슨하게 고치지 말고 보고하라.
4. 제거할 중복 `Material` 은 **정확히 두 곳**(실측): `apps/web/lib/src/features/path/presentation/path_plan_view.dart:95`(설명 주석 4줄 포함)·`:121`. 둘 다 `DpPanel(child: Material(transparency, child: Column(...)))` 형태다. 다른 `Material` 은 건드리지 말 것.
5. 커밋 직후 트레일러 확인 + 다르면 그 커밋만 `--amend`.

기대값: `dp_design` **386**(385+1) · `apps/web` **1122** 유지 · `apps/admin` **156** 유지.

### Task 5 — 구현 보고 수령 · 컨트롤러 직접 검증

| 확인 | 결과 |
|---|---|
| 커밋 범위 `79eb4c0..HEAD` | **정확히 1개** (`f88edab`) ✔ |
| 트레일러 | `Claude Opus 5 (1M context)` ✔ |
| 바뀐 파일 | `dp_panel.dart` · `dp_panel_test.dart` · `path_plan_view.dart` = **3개** ✔ (설정 파일 없음) |
| `DpPanel` 소스 diff | `Material(type: MaterialType.transparency)` 한 겹 + 근거 주석. `Container` 의 decoration·`clipBehavior`·제목행·`Padding` 무변경 ✔ |
| `path_plan_view` 정리 | 중복 `Material` **두 곳 모두 제거** + 설명 주석 4줄 제거 + 재들여쓰기. 파일 내 `MaterialType.transparency` 잔존 **0** ✔ |
| `packages/dp_design` (직접 실행) | **386 통과**(385 + 1) ✔ — 기존 6건 전부 통과 = `_decorationOf` 가 여전히 바깥 `Container` 를 잡는다 |
| `apps/web` (직접 실행) | **1122 통과**(변동 없음) ✔ |
| `apps/admin` (직접 실행) | **156 통과**(변동 없음) ✔ |
| `flutter analyze`(dp_design) | 0 issues ✔ |

**렌더 중립의 근거**: `MaterialType.transparency` 는 배경을 그리지 않고, 소비처 1278개 테스트(web 1122 + admin 156)가 하나도 바뀌지 않았다.

review package = `review-79eb4c0..f88edab.diff`. task reviewer(sonnet) dispatch — 파일 계약 적용.
Task 5: 리뷰 = **Spec ✅ · Critical 0 · Important 0 · Minor 1 · Approved** (`task-5-review.md`). 리뷰어가 `path_plan_view.dart` 76줄을 라인 단위로 대조해 **실질 변경 0**(전부 재들여쓰기)임을 확인했고, 새 잉크 테스트의 RED 로그가 프레임워크 예외 문구(`ListTile background color or ink splashes may be invisible`)를 실제로 담고 있어 판별력이 있음을 확인했다.
Task 5: minor (deferred): 함정 설명 문구가 `dp_panel.dart` 와 `dp_panel_test.dart` 양쪽에 중복된다(브리프가 지정한 문구를 옮긴 것). 머지를 막지 않는다.
**Task 5: complete (commits 79eb4c0..f88edab, review clean)**

### Task 6 — dispatch 전 실측: 계획의 「리터럴 7곳」이 실제로는 11곳이다

컨트롤러가 `grep -rn "fontSize: [0-9]"` 로 `packages/dp_design/lib` 을 훑은 결과:

| 위치 | 현재 값 | 계획 목록에 있나 | 토큰 대체 시 렌더 |
|---|---|---|---|
| `states/dp_status_text.dart:40` | `fontSize:12, w600` (height 없음) | ✅ | `labelMedium` → **height 16/12 추가 = 행 높이 변화** |
| `data/dp_row_line.dart:59` | `fontSize:13` | ✅ | `bodySmall` → **height 20/13 추가** |
| `interaction/dp_option_row.dart:111` | `fontSize:13` | ✅ | 같음 |
| **`interaction/dp_check_row.dart:94`** | `fontSize:13` | ❌ **누락** | 같음 |
| **`data/dp_tag.dart:33-38`** | `fontSize:12, height:16/12, w600` | ❌ **누락** | `labelMedium` 과 **완전히 동일** ⇒ 렌더 변화 **0** |
| **`data/dp_web_table.dart:207`** | `fontSize:12, w600` (height 없음) | ❌ **누락** | `labelMedium` → **표 헤더 행 높이 변화** |
| `data/dp_row_line.dart:34` · `data/dp_list_lines.dart:44` · `interaction/dp_option_row.dart:66` | `vertical: 10` | ✅(2/3) | `DpWebDensity.rowVerticalPadding` — 값 동일 ⇒ 렌더 0 |
| `data/dp_key_values.dart:34` | `SizedBox(height: 6)` | ✅ | `DpWebDensity.keyValueGap` — 값 동일 ⇒ 렌더 0 |
| `content/dp_markdown.dart:46` | `fontSize:16` | ❌ | **범위 밖** — P3 웹 문법 위젯이 아니라 읽기 본문 마크다운이고 자체 스케일 계약을 갖는다 |

- **Ruling: 누락된 3곳(`dp_check_row:94`·`dp_tag:33`·`dp_web_table:207`)을 Task 6 에 포함한다.** — 왜: 이 Task 의 목적은 「웹 문법 위젯에서 리터럴 치수를 없애 시안과 대조 가능하게」인데, **같은 패턴의 형제 3곳을 남기면 목적을 달성하지 못하고** 리뷰어가 그 비일관성을 발견으로 올릴 것이다. `dp_tag` 는 토큰과 값이 완전히 같아 **렌더 변화 0 의 순이득**이다. 계획이 든 7곳은 P3 리뷰가 그때 지목한 줄 번호를 옮겨 적은 것이고(그 번호는 이미 이동했다), 전수 조사를 하지 않은 결과다. — **틀렸을 때의 비용**: 계획이 예상한 것보다 렌더 변화 면적이 넓어진다(표 헤더·동의 행 설명이 추가). 그러나 PR-2 가 같은 단계에서 기준선을 다시 기록하므로 흡수된다.
- **Ruling: `dp_markdown.dart:46` 과 `SizedBox(height: 2)` 류는 건드리지 않는다.** — 왜: 전자는 읽기 본문의 별도 계약, 후자는 시안이 지정하지 않은 미세 간격이라 이름 붙일 토큰이 없다. 범위 확대를 막는다.

### Task 6 — 구현 보고 수령 · 컨트롤러 직접 검증 · **CI 차단 결함 1건 발견**

| 확인 | 결과 |
|---|---|
| 커밋 | 1개. 트레일러가 **`Claude Sonnet 5`** 로 들어갔다 → **HEAD 라서 `git commit --amend` 로 교정**(`c04409f` → **`7ae309f`**). 기록된 SHA 를 깨지 않았다 |
| 바뀐 파일 | 10개(위젯 8 · `dp_spacing.dart` · 테스트 1). 설정 파일 없음 ✔ |
| 리터럴 잔존 | `grep -rn "fontSize: [0-9]" packages/dp_design/lib` → **`dp_markdown.dart:46`(범위 밖 판정) + `dp_typography.dart`(토큰 정의 자신)** 뿐 ✔ 11곳 전부 교체됨 |
| 계획에 없던 12번째 지점 | 구현자가 `dp_check_row.dart:107` 의 `vertical: 10` 도 `DpWebDensity.rowVerticalPadding` 으로 옮겼다. **수용** — 값이 동일해 렌더 중립이고, 그 상수의 문서가 바로 `.chk` 를 근거로 든다. 컨트롤러 Ruling 의 취지와 일치 |
| `dp_design` / `apps/web` / `apps/admin` (직접 실행) | **387** / **1122** / **156** ✔ · analyze 0 |

**★ CI 차단 결함 — 포맷 게이트.** 컨트롤러가 `dart format --set-exit-if-changed .` 을 직접 돌리자 **5 changed** 가 나왔다. 조사 결과 두 가지가 겹쳐 있었다:

1. **로컬 Dart 3.13.2 ≠ CI 핀 Dart 3.12.1 이라 포매터 출력이 다르다.** 우리가 **건드린 적 없는 파일 4개**(`apps/admin/test/.../reports_async_order_test.dart` 등)를 로컬 포매터가 3.13 의 새 인자 패킹 규칙으로 다시 쓴다. **레포 전체에 `dart format .` 을 돌려 커밋하면 안 된다** — 무관한 파일이 섞이고 CI 에서 되돌려진다.
2. **그러나 우리 파일 하나는 진짜 dirty 였다.** `dp_next_action_band_test.dart` 의 `find.bySemanticsLabel(...)` 호출이 3줄로 나뉘어 있었는데, 한 줄로 접으면 **74자**로 80열에 들어간다. Dart 3.7+ 의 tall-style 포매터는 트레일링 콤마를 무시하고 폭으로 판단하므로 **CI 의 3.12.1 도 같은 결과를 낸다** ⇒ 이대로 PR 을 올렸다면 `melos run format` 게이트가 **실패했을 것이다**.

- **Ruling: 컨트롤러가 직접 고쳤다**(커밋 `c1033bc`). — 왜: 리뷰 발견이 아니라 프로젝트 자신의 포매터를 파일 하나에 돌리는 **판단이 필요 없는 기계적 조치**이고, 서브에이전트 왕복 비용이 이득을 넘는다. 이미 닫힌 Task(3+4)의 산출물이라 그 Task 의 루프로 되돌릴 수도 없다. — 틀렸을 때의 비용: 없다(재검사 19파일 0 changed · 그 테스트 13건 통과).
- **Ruling: 포맷 확인 방법을 바꾼다.** 앞으로 `dart format .`(파괴적·전체)을 쓰지 않고 **`dart format --output=none --set-exit-if-changed $(git diff --name-only <base>..HEAD)`** 로 이 브랜치가 바꾼 파일만 비파괴 검사한다. 남은 dispatch 에 이 명령을 명시한다.
- **구현자 보고의 「format 0 changed」 주장은 세 번 다 부정확했다** — 범위를 좁혀 돌렸거나 파괴적으로 돌린 뒤 결과를 확인하지 않았다. 컨트롤러가 직접 돌리지 않았다면 CI 에서야 드러났을 것이다.

### Task 7·10 — dispatch 전 실측

**Task 7 (`apps/web/test/features/diagnostic/diagnostic_page_test.dart`)**
- 헬퍼: `Widget _host(_FixedDiagnosticController controller, {bool router = false, bool missionSpineEnabled = true, TextScaler? textScaler})`(`:74`). `textScaler` 는 `MaterialApp.builder` 안에서 `MediaQuery` 를 덮으므로 **함정에 걸리지 않는 올바른 형태**다.
- 시작 화면 띄우는 관례: `final controller = _FixedDiagnosticController(const DiagnosticState()); await tester.pumpWidget(_host(controller)); await tester.pump();`
- 뷰포트 헬퍼 **`void tallView(WidgetTester tester)`**(`:141`)가 이미 있다 — 1200×2400 고정이고, 그 주석이 「시작 화면은 스크롤되지만, 탭하는 테스트는 뷰포트를 키워 CTA 를 화면 안에 둔다」고 적는다. **즉 이 파일은 CTA 가 접힌다는 사실을 이미 알고 있고, M9 는 그 깊이를 「재는」 테스트를 더하는 것이다.** 390 폭이 필요하므로 `tallView` 를 쓸 수 없다 — 그 옆에 같은 모양의 `phoneView(tester)` 를 두는 것이 이 파일의 관례에 맞는다.
- 쓸 수 있는 키: `ValueKey('diagnostic-onboarding-surface')` · `ValueKey('brand-row')` · `ValueKey('diagnostic-track-hint')`. CTA = `find.widgetWithText(FilledButton, '진단 시작하기')`.

**Task 10 (`packages/dp_design/test/shell/dp_nav_rail_test.dart`, 기존 13건)**
- 헬퍼 `Widget _host(Widget child)`(`:19`)가 `Scaffold(body: Row(children: [child]))` 로 감싼다(레일은 `Row` 안에 있어야 한다).
- 픽스처 `const _dests = <DpDestination>[...]`(`:7`) — 라벨이 **`'대시보드'`·`'학습 경로'`·`'게시판'`** 이고 셋째에 `badgeCount: 2` 가 있다. 위젯 호출은 `DpNavRail(destinations: _dests, selectedIndex: 0, onSelect: (_) {}, extended: <bool>)` 이며 `extended` 기본값은 true 로 보인다(첫 테스트가 넘기지 않고 섹션 라벨을 기대한다).
- ⇒ M11 계열 테스트의 기대 라벨은 `'대시보드'` 다(계획이 든 예시와 일치).

### Task 6 — 리뷰 결과 · 판정

리뷰(sonnet) = **Spec ✅ · Critical 0 · Important 1 · Minor 4 · Approved** (`task-6-review.md`). 리뷰어가 11곳 전부를 값 단위로 대조했고, `dp_tag` 의 렌더 중립(`-height: 16 / 12` 가 사라진 이유는 토큰이 같은 값을 주기 때문)과 `dp_web_table` 의 WCAG 주석 보존을 diff 로 확인했다.

- **Ruling(Important · 수정 라운드 없이 해소): 리뷰어의 「보고서가 검증 가능하게 거짓」 판정은 컨트롤러의 정보 누락 탓이다.** 리뷰어는 구현자 보고서가 트레일러를 `Claude Sonnet 5` 로 적었는데 실제 커밋은 `Claude Opus 5 (1M context)` 라며 Important 를 올렸다. **사실관계: 보고서는 작성 시점에 정확했고, 그 뒤 컨트롤러가 `git commit --amend` 로 트레일러를 고쳤다**(`c04409f` → `7ae309f`). 보고서가 든 해시 `c04409f` 가 diff 의 해시와 다른 것도 같은 이유다. — 왜 수정 라운드가 없는가: **코드 결함이 아니고**(리뷰어 자신도 "no code fix is needed" 라 적었다) 고칠 산출물이 없다. — **내 잘못**: 리뷰 dispatch 의 「컨트롤러가 이미 실측한 것」 절에 커밋 해시만 적고 **내가 amend 했다는 사실을 적지 않았다.** — 조치: 앞으로 **컨트롤러가 그 Task 의 커밋을 건드린 경우 리뷰 dispatch 에 반드시 명시**한다. — 틀렸을 때의 비용: 없다(git log 로 확인 가능한 사실이다).
- **Ruling(Minor 1 · 명시적 비준): 구현자의 4번째 범위 확장을 승인한다.** `dp_check_row.dart:108` 의 컨테이너 `vertical: 10` → `DpWebDensity.rowVerticalPadding`. 리뷰어가 「컨트롤러가 명시적으로 비준하거나 거부해야 한다」고 요구했다. **비준한다** — 값이 동일해 렌더 중립이고, 그 상수의 문서 주석이 바로 `.chk`(= `DpCheckRow`)를 근거로 들기 때문에 그 위젯만 리터럴로 남기는 것이 오히려 모순이다. 구현자가 숨기지 않고 보고서에 「컨트롤러 확인 필요」로 적은 것도 옳은 처신이다.
- Minor 2~4 는 **deferred**:
  - `Task 6: minor (deferred): 타이포 6곳 중 `dp_status_text` 에만 `style.height` 단언이 있다. 나머지 5곳은 기존 스위트에 의존한다 — 렌더의 진짜 고정은 PR-2 의 기준선 재기록이 한다.`
  - `Task 6: minor (deferred): plan-mandated — 같은 위젯 안에서 라벨은 `text.bodyMedium?.copyWith`, 설명은 `text.bodySmall!.copyWith` 로 `?.`/`!` 가 섞인다(브리프 스니펫이 `!` 를 지정했다). `ThemeData` 가 `TextTheme` 를 항상 채우므로 실무 위험은 낮다.`
  - `Task 6: minor (deferred): `dp_web_table` 은 지역 `text` 변수를, `dp_tag` 는 `Theme.of(context).textTheme` 인라인을 쓴다(순수 미관).`

**Task 6: complete (commits f88edab..c1033bc, review clean — Important 1건은 컨트롤러 정보 누락으로 판정·해소, 4 deferred minors)**

### Task 7 — 구현 보고 수령 · 컨트롤러 직접 검증

| 확인 | 결과 |
|---|---|
| 커밋 / 트레일러 | `378c1d4` 1개 · `Claude Opus 5 (1M context)` ✔ (dispatch 의 확인 지시가 작동) |
| 바뀐 파일 | `diagnostic_page.dart` · 그 테스트 · `dp_check_row_test.dart` = **3개** ✔ 설정 파일 없음 |
| M10a 소스 | 두 루프 모두 `if (index > 0)` 를 **행 앞**으로 옮기고 뒤 `SizedBox` 제거. 트랙 루프는 `.indexed` 사용. 보기 행의 `key` 계산식 무변경 ✔ |
| M9 | `phoneView(tester)` 헬퍼를 `tallView` 옆에 신설(인라인 중복 없음) ✔ CTA 실측 **1337px**, 상한 1500 과 그 근거를 테스트 주석에 기록 ✔ |
| M11 | `_host`·`_noop` 재사용 ✔ Tab 5회 후 **서로 다른 정지 2개**를 단언 |
| `dp_design` / `apps/web` (직접 실행) | **388**(387+1) / **1124**(1122+2) ✔ |
| 포맷(비파괴·브랜치 한정 22파일) | **0 changed** ✔ |
| `flutter analyze`(apps/web) | **1 issue = 계획이 예고한 기존 항목** — `current_mission_controller.dart:273 unawaited_return_in_try_block`. 우리 브랜치가 건드린 적 없는 파일이고 **로컬 Dart 3.13.2 전용 린트**다(CI 핀 3.12.1 은 녹색). 무시가 맞다 |

- **실측이 계획을 교정한 것**: 계획의 M10a 스니펫은 마지막 행과 다음 요소 사이 간격을 **16**(`DpSpacing.lg`)으로 추측했으나, 구현자가 실제 인접 요소를 재어 **8**(`DpSpacing.sm`)임을 찾아 `closeTo(8, 0.5)` 로 단언했다. 올바른 처신이다.
- **`flutter analyze` 자신이 `analysis_options.yaml` 을 다시 쓴다** — 출력에 `Upgrading analysis_options.yaml to exclude build and platform directories.` 가 찍힌다. 그 결과 **두 번째 실행에서는 그 1건이 사라진다**(제외 경로로 들어가서가 아니라 설정이 바뀌어서). 즉 analyze 를 두 번 돌려 「0 issues」를 보고하면 **거짓 음성**이다. 확인은 항상 설정을 되돌린 뒤 한 번만 돌린다.

### Task 7 — 리뷰 결과 · 판정

리뷰(sonnet) = **Spec ❌ · Critical 0 · Important 1 · Minor 2 · Needs fixes** (`task-7-review.md`).

- **Ruling(Important): 고친다. 보기(문항) 루프의 회귀 테스트가 없다.** 지적 = M10a 는 **두 루프**(트랙·보기)를 고쳤는데 추가된 테스트는 트랙 루프 것 하나뿐이라, 보기 루프에 트레일링 `SizedBox` 가 다시 붙어도 스위트가 잡지 못한다. **컨트롤러가 소스로 확인: 지적이 옳고 앵커도 실재한다** — 보기 루프 바로 뒤에 `if (!advanceFailed && !answerFailed) ...[ const SizedBox(height: DpSpacing.md), const Divider(), TextButton('잘 모르겠어요') ]` 가 있다(`diagnostic_page.dart:505-512`). 즉 마지막 보기 행과 `Divider` 사이는 **`DpSpacing.md`(12) 하나**여야 한다. 또 그 화면을 띄우는 관례와 템플릿 테스트가 이미 있다(`:663 '진단 문항: 2단계가 현재이고 보기를 DpOptionRow 로 그린다'`, 보기 4행). — 왜 고치는가: 이 레포의 절대 조건 2 가 「테스트 없는 구현 변경을 금지한다」이고, 두 루프는 독립적 수정이라 한쪽만 잠그면 절반만 지켜진다. — 틀렸을 때의 비용: 테스트 하나가 는다. 소스 변경 없음.
- 리뷰어가 정확히 판정한 것 둘(기록): ① 브리프의 `closeTo(16, 0.5)` 는 **옛 구조 기준의 오기**이고 구현자의 `closeTo(8, 0.5)` 가 맞다(루프 트레일링 8 을 없앴으므로 힌트 앞 `SizedBox(sm)` 8 만 남는다). ② M9 상한 1500 은 실측 1337 대비 12% 여유로 「판별력 없는 상한」이 아니다.
- Minor 2건 **deferred**:
  - `Task 7: minor (deferred): M11 이 `identityHashCode(node)` 로 `Set<int>` 를 만든다 — `FocusNode` 는 기본 객체 동일성을 쓰므로 `Set<FocusNode>` 가 더 직접적이다. 현재 방식도 틀리지 않다.`
  - `Task 7: minor (deferred): M9 의 상한이 행 1~2개 증가는 못 잡을 수 있다는 한계를 테스트 주석에도 한 줄 남기면 좋다(보고서에는 우려로 적혀 있다).`
- ⚠️(M11 의 「`ExcludeFocus` 제거 시 4가 된다」 재현은 diff 로 검증 불가) — **수용**. 리뷰어가 설계 논증으로 판별력을 확인했고(2주기 vs 4주기를 Tab 5회가 가른다), 구현자가 실제로 `Actual: <4>` 를 봤다고 보고했다. 재현물을 커밋에 남기는 것은 부적절하므로 이 이상 요구하지 않는다.
- 수정 라운드 1/5: 원 구현자(sonnet) 재개. FIX_BASE = `378c1d4`.

Task 7: fix round 1/5 (수정 커밋 `2ef4766` — 컨트롤러 직접 확인: **테스트 파일 하나만** +33, 소스 변경 섞이지 않음. 트레일러 정상. 구현자가 RED 를 실증해 `Actual: <20.0>`(= 기대 12 + 여분 8)을 보고했고, 일시 수정을 원복해 `diagnostic_page.dart` 가 byte-identical 임을 확인했다 — 컨트롤러도 grep 으로 보기 루프가 `if (index > 0)` 형태임을 재확인. 앵커 `Divider` 가 단일 매치인 근거(파일에 `Divider` 두 곳이나 문항 화면 상태에서는 `:507` 하나만 렌더)를 보고서에 논증. 직접 실행: `apps/web` **1125** · 포맷 22파일 **0 changed** · 워킹 트리 깨끗). 범위 재리뷰(haiku) dispatch.
Task 7: 재리뷰 = Finding 1 **ADDRESSED** · 새 breakage 없음 · out-of-scope 없음 (`task-7-rereview.md`).
Task 7: minor (deferred): M11 이 `identityHashCode(node)` 로 `Set<int>` 를 만든다 — `Set<FocusNode>` 가 더 직접적이다(현재도 틀리지 않다).
Task 7: minor (deferred): M9 상한이 행 1~2개 증가는 못 잡을 수 있다는 한계를 테스트 주석에도 남기면 좋다.
**Task 7: complete (commits c1033bc..2ef4766, review clean, 2 deferred minors)**

### Task 8 — dispatch 전 실측 (마이페이지 구조)

- `mypage_page.dart:143` 에 `DpCols(main: …, side: DpSide(children: […]))`.
- **`main`**: `.prof` 머리(`CircleAvatar` + bio + 사진 유무 문구 + **현재 태그 3개**, `:150-207`) → `DpPanel('프로필 편집')`(`:210`) → `DpPanel('활동')`(`:259`).
- **`side`**(`:288-315`): ① `DpPanel('AI 멘토 초대')` ② `DpPanel(child: DpRowLine('설정' …))`.
- ⇒ 시안의 사이드 순서는 **`프로필` kv → `AI 멘토 초대`** 이므로 새 패널을 `DpSide.children` 의 **첫 항목**으로 넣는다.
- 상태 접근: `final st = widget.state; final p = st.profile;`(`:133-134`), `final trackLabel = trackLabels[p.targetTrack];`(`:136`).
- 테스트(`mypage_page_test.dart`, 기존 8건): 헬퍼 `Widget _host(MyPageState state, {MentorAccessState mentorAccess})`(`:36`). **현재 3개 태그의 텍스트를 단언하는 기존 테스트는 없다**(grep: 픽스처 값만 나온다) ⇒ 태그를 배지로 바꿔도 기존 테스트가 깨질 위험이 낮다.
- 픽스처는 이미 `dashboard: DashboardSummary(streakDays: 3, progressPercent: 40, completedContentCount: 7)` 를 준다 — `badges` 가 비어 있으므로 배지 테스트용 픽스처에 `badges: ['첫 경로']` 를 더해야 하고, 그때 배지 라벨은 **`첫 경로`** 와 **`3일 연속`**(`streakDays: 3`)이 된다(시안 예시의 `7일 연속` 이 아니다).

### Task 8 — 구현 보고 수령 · 컨트롤러 직접 검증

| 확인 | 결과 |
|---|---|
| 커밋 | 1개. 트레일러가 또 **`Claude Sonnet 5`** → HEAD 라서 `--amend` 로 교정(`0dd9c19` → **`675181a`**). **sonnet 구현자에게서 두 번째 재발** — dispatch 의 확인 지시를 넣어도 sonnet 은 따르지 않는다(haiku 는 따랐다) |
| 바뀐 파일 | `mypage_page.dart`(+39/−8) · 그 테스트(+72) = **2개** ✔ 설정 파일 없음 |
| 머리 태그 → 배지 | `badgeLabels = [...?summary?.badges, if (streakDays > 0) '${streakDays}일 연속']` · `Wrap` 에 `ValueKey('mypage-prof-badges')` · 바깥 `Row` 에 `ValueKey('mypage-prof')` · 주석도 「태그」→「배지」로 갱신 ✔ |
| 사이드 kv 신설 | `DpSide.children` 의 **첫 항목** ✔ 시안 순서(프로필 → AI 멘토 초대)와 일치 · 세 필드 전부 null 이면 만들지 않는 가드 있음 ✔ `DpKeyValue` 레코드 형태 정확 |
| `apps/web` (직접 실행) | **1127**(1125 + 2) ✔ |
| 포맷(비파괴·24파일) | **0 changed** ✔ · 워킹 트리 깨끗 |

- **Ruling: 리뷰 dispatch 에 「컨트롤러가 이 Task 의 커밋을 amend 했다」를 명시한다.** Task 6 에서 이것을 빠뜨려 리뷰어가 구현자 보고서를 「검증 가능하게 거짓」으로 오판했다. 같은 실수를 반복하지 않는다.

### Task 8 — 리뷰 결과 · 판정

리뷰(sonnet) = **Spec ✅ · Critical 0 · Important 0 · Minor 2 · Approved** (`task-8-review.md`). 리뷰어가 ① 새 요청 0건(`st.dashboard` 만 읽음) ② `streakDays == 0` 가드 ③ 사이드 kv 가 첫 항목 ④ 「머리에 경력 문구가 없다」단언의 판별력 ⑤ 뷰포트 1200(840 경계 초과)을 `tester.view.physicalSize` 로 준 것을 전부 diff 로 확인했다. **amend 사실을 dispatch 에 적은 덕에 Task 6 같은 오판이 없었다.**

- Minor 2건 **deferred**:
  - `Task 8: minor (deferred): `mypage_page.dart` 의 새 주석이 「오늘 화면이 쓰는 것과 같은 값·문구다」라고 적었으나 실측상 오늘 화면에는 `'N일 연속'` 이라는 합성 문구가 없다 — **값(streakDays)만 재사용했고 문구는 시안 `.prof` 의 `7일 연속` 형태로 새로 합성**한 것이다. 동작은 옳다(시안 100% 가 사용자 결정). **이 주석 문구는 컨트롤러가 dispatch 에 그대로 받아 적은 것이라 원인도 컨트롤러에 있다.** 최종 전체 리뷰가 트리아지한다.`
  - `Task 8: minor (deferred): `dashboard == null`(집계 섹션 실패) 일 때 배지 영역이 조용히 사라지는 경로를 검증하는 테스트가 없다 — 코드상 안전하고 브리프 범위 밖이다.`

**Task 8: complete (commits 2ef4766..675181a, review clean, 2 deferred minors)**

### Task 9+10 — dispatch 전 실측

- **Task 9**: `grep -rn "PlaceholderPage" apps packages --include=*.dart` → **정의 파일 자신의 두 줄뿐**(소비처 0). 전용 테스트 파일도 없다(`apps/web/test/features/common/` 에는 `brand_row_test.dart`·`track_catalog_test.dart` 만). 그 파일의 doc 주석이 「P4b~P4d에서 실구현될 화면의 임시 자리」라 적는데 **그 단계는 이미 끝났다** ⇒ 진짜 죽은 코드다.
- **Task 10**: `dp_nav_rail.dart` 의 항목이 펼침 상태에서 `Text(d.label)` 을 보이게 그리고(`:245` 부근) 그 전체를 `Semantics(button: true, label: d.label, selected: selected)` 로 감싼다(`:264-267`) ⇒ 라벨이 두 번 올라간다. 테스트 파일(`test/shell/dp_nav_rail_test.dart`, 기존 13건)에 `Widget _host(Widget child)`(`:19`, `Scaffold(body: Row(children: [child]))`)와 `const _dests`(라벨 `'대시보드'`·`'학습 경로'`·`'게시판'`, 셋째에 `badgeCount: 2`)가 있다.

### Task 9+10 — 구현 보고 수령 · 컨트롤러 직접 검증

| 확인 | 결과 |
|---|---|
| 커밋 | 2개(Task 9 삭제 · Task 10 수정) ✔ |
| Task 9 | `placeholder_page.dart` 삭제(−24). `grep -rn "PlaceholderPage"` 잔존 **0** ✔ |
| Task 10 | 보이는 `Text` 를 `ExcludeSemantics` 로 감쌈 + 근거 주석. `Semantics` 래퍼 인자(`key`·`button`·`label`·`selected`)와 접힘 `Tooltip` 분기 **무변경** ✔ |
| Task 10 테스트 | `tester.getSemantics(find.byKey(ValueKey('rail-item-semantics-0'))).label` 이 **정확히 `'대시보드'`** 임을 단언 — 수정 전이면 `'대시보드\n대시보드'` 라 판별력이 있다 ✔ |
| `dp_design` / `apps/web` / `apps/admin` (직접 실행) | **389**(388+1) / **1127**(유지) / **156**(유지) ✔ |

### ★ 커밋 트레일러 일괄 정리 — 앞선 파킹 판정을 뒤집었다

- **Ruling(앞선 Ruling 을 대체한다): 브랜치 전체의 `Co-Authored-By` 를 규약대로 통일했다.** Task 3+4 시점에는 「이력을 다시 쓰지 않는다(원장 SHA 안정성 > 표기 일관성)」로 파킹했으나, Task 9+10 에서 **또 2건이 어긋나 14커밋 중 4건**이 됐다. 파킹을 유지하면 PR 이 영구히 비일관해지고, 고치는 비용은 시간이 갈수록만 커진다. **푸시 전인 지금이 가장 싼 시점**이라 판단을 뒤집었다.
- 방법: `git filter-branch -f --msg-filter 'sed …' eaa7f77..HEAD` — **메시지만** 바꾼다.
- **내용 무변경을 세 지표로 검증**: 최종 트리 해시 `b62cf43b8084fcc489a4b2fb9071611abde8f2a1` **동일** · 커밋 수 **14 동일** · `git diff eaa7f77..HEAD` 의 sha256 `5eef64b6face69e07ea9c03a388ffb7eddf0b200dd2b616bce72124767e6a396` **동일**.
- 결과: 14커밋 전부 `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` ✔
- **틀렸을 때의 비용**: 아래 매핑 이전의 SHA 를 인용한 원장 기록이 stale 이 된다(내용은 그대로라 `git log` 로 추적 가능). 푸시 전이라 외부 영향 0.

**SHA 매핑 (옛 → 새). 이 줄 위의 모든 원장 기록은 옛 SHA 를 쓴다.**

| 옛 | 새 | 무엇 |
|---|---|---|
| `1ce8123` | `1ce8123`(불변) | Task 1 DpCols 주석 |
| `37f608d` | `37f608d`(불변) | Task 2 DpSteps 높이 |
| `6b29852` | `6b29852`(불변) | Task 1+2 수정(헬퍼 재사용) |
| `900492c` | **`38dbae1`** | Task 3 그림자 제거 |
| `296b0fa` | **`113b616`** | Task 4 비활성 라벨 |
| `79eb4c0` | **`3d5d2e3`** | Task 3+4 수정(hint 제거) |
| `f88edab` | **`64f071c`** | Task 5 DpPanel 잉크 |
| `7ae309f` | **`145bd00`** | Task 6 리터럴→토큰 |
| `c1033bc` | **`a2a9926`** | 포맷 게이트 수정(컨트롤러) |
| `378c1d4` | **`9805b46`** | Task 7 마감 3건 |
| `2ef4766` | **`acb1be1`** | Task 7 수정(보기 루프 테스트) |
| `675181a` | **`b11219f`** | Task 8 마이페이지 |
| `db920bd` | **`2cec270`** | Task 9 PlaceholderPage 삭제 |
| `9efb947` | **`590fa50`** | Task 10 DpNavRail 라벨 |

- `git filter-branch` 가 `refs/original/refs/heads/feat/s3-p5-carryover` 를 남겼다(되돌림용 백업 ref). 푸시 대상이 아니며 Task 11 뒤 정리한다.

Task 9+10: 리뷰 = **Spec ✅ · Critical 0 · Important 0 · Minor 0 · Approved** (`task-9-10-review.md`). 이 브랜치에서 유일하게 완전히 깨끗한 리뷰다.
**Task 9+10: complete (commits b11219f..590fa50, review clean)**

### PR-1 구현 완료 — 게이트 사전 확인 (컨트롤러 직접 실행)

- `dart run melos run test` (CI 와 같은 명령): **전 패키지 SUCCESS** — dp_design 389 · dp_core 174 · admin 156 · web 1127.
- `dart run melos run analyze` (CI 와 같은 명령): dp_design·admin **No issues**, web **1 issue** = `current_mission_controller.dart:273 unawaited_return_in_try_block`.
  - **CI 에서 실패하지 않는다는 근거 3중 확인**: ① 그 파일은 `origin/develop` 과 **byte-identical**(우리가 건드린 적 없다) ② 그 린트는 어떤 `analysis_options.yaml` 에도 **명시적으로 켜져 있지 않다**(`package:flutter_lints/flutter.yaml` 경유) ③ **`origin/develop` 의 CI 가 녹색이다**(PR #238 전 잡 pass) — CI 핀 Dart 3.12.1 에 이 린트가 있었다면 develop 이 이미 빨갰을 것이다. 로컬 Dart **3.13.2** 전용이다.
- 포맷(비파괴·브랜치 한정 26파일): **0 changed** · 워킹 트리 깨끗.
- 최종 전체 브랜치 리뷰 패키지 = `review-eaa7f77..590fa50.diff`(14커밋 · 68581 bytes). 가장 유능한 모델(opus)로 dispatch.

## 최종 전체 브랜치 리뷰 (opus) — 판정

`final-review.md` = **Needs fixes · Critical 0 · Important 3 · Minor 13 · deferred minor 중 머지 전 수정 1건.**
리뷰어가 68KB diff 를 2패스로 읽고 **시안 정본 Artifact 를 직접 열어** CSS 를 대조했다. 교차 Task 검증 6건(C1~C6) 중 「`DpPanel` 의 `Material` 과 `DpNavRail` 의 `ExcludeSemantics` 가 시맨틱스에서 간섭하는가」의 답은 **간섭하지 않는다**(`Material` 은 시맨틱스 노드를 만들지 않는다 — SDK 를 직접 읽어 확인).

- **Ruling(I1): 고친다.** `DpNextActionBand` 의 배경·테두리를 시안 `.next` 대로 `accentSoft`·`accentLine` 로. — 근거: **Task 3 의 커밋 메시지와 코드 주석이 시안 `.next` 규칙을 근거로 인용**했는데 그 규칙의 세 속성(`background:var(--soft)`·`border:1px solid var(--line)`·그림자 없음) 중 **하나만** 반영했다. 인용한 근거의 절반만 따른 것은 새 범위가 아니라 **그 Task 의 미완**이다. 게다가 그림자를 없앤 뒤 밴드가 `surface` 배경 위(실습 2곳·콘텐츠 1곳)에 놓이면 면 구분이 사실상 사라진다. 토큰은 이미 있고 값이 시안과 **정확히 일치**한다(실측: `accentSoft=0xFFEEF2FF`=`--soft`, `accentLine=0xFFC7D2FE`=`--line`).
  - **대비 검증(컨트롤러 직접 계산)**: 이 변경은 비활성 이유 문구(`textSecondary`)를 `accentSoft` 위에 올린다. 기존 대비 테스트는 그 조합을 **재지 않는다** — P4 의 M5 수정이 「실재하지 않는 조합」이라며 제거했기 때문이다(`dp_colors_contrast_test.dart:46-57` 의 주석이 그 논리를 적는다). WCAG 상대휘도로 직접 계산: **라이트 5.30:1 · 다크 7.72:1 — 둘 다 AA(4.5) 통과.** ⇒ 채택 가능하고, **이제 실재하는 조합이 되므로 그 단언을 테스트에 되돌려 놓아야 한다**(P4 M5 의 논리를 그대로 적용하면 그렇다).
  - 틀렸을 때의 비용: 밴드 배경이 12 소비처에서 연보라가 된다 — 그것이 시안이다. PR-2 가 그 상태를 기록한다.
- **Ruling(M1 을 Important 로 승격 · 고친다): 릴리스 빌드에서 「사용할 수 없음: null」이 읽힌다.** `dp_next_action_band.dart:204` 의 `'…: ${widget.disabledReason}'` 는 생성자 `assert` 에 의존하는데 **assert 는 릴리스에서 제거된다.** 바꾸기 전에는 `hint: null` 이라 조용히 없어졌으므로 **이것은 내 Task 4 변경이 들인 회귀다.** 스크린리더가 "null" 을 읽는 것은 합리적인 사용자가 기대할 수 없는 거동이다. `?? '지금은 사용할 수 없습니다'` 한 줄.
- **Ruling(I2): 레이아웃이 아니라 기록을 고친다.** 지적 = 마이페이지의 중복은 닫힌 게 아니라 태그 → 사이드 kv 로 **자리를 옮겼다**. 시안에 중복이 없는 이유는 **시안의 마이페이지에 편집 폼이 아예 없기 때문**이다(헤더의 `프로필 편집` 버튼으로 빠진다). 컨트롤러 확인: 리뷰어가 시안을 직접 읽고 인용한 것이 맞다. — 편집 폼을 별도 라우트로 빼는 것은 **명백히 이 PR 범위 밖**이므로 코드가 아니라 ① `mypage_page.dart` 사이드 kv 주석에 divergence 를 적고 ② **Task 17 의 핸드오프가 M6c 를 「닫힘」이 아니라 「부분 닫힘 + 남은 divergence」로 적게** 한다. — 틀렸을 때의 비용: 없다. 오히려 「시안과 1:1 로 맞췄다」는 커밋 메시지가 정정 없이 스펙에 실리는 것을 막는다.
- **Ruling(I3): 리뷰어의 선택지 2 를 택한다 — `DpWebDensity` 를 유지하고 상호 참조·비투영을 명시한다.** 지적 = `DpDensity.rowPadding = 8`(「표 행 세로 여백」)과 `DpWebDensity.rowVerticalPadding = 10`(구분선 행)이 같은 이름의 개념을 둘로 갈랐고, **`dp_semantic_tokens.dart:475` 가 「DpDensity 가 SSoT」라 못박고 `--dp-density-*` 로 CSS 투영**하는데 새 클래스는 그 목록에 없다(컨트롤러 실측 확인). — **왜 선택지 1(DpDensity 로 합치기)이 아닌가**: `DpDensity` 는 **시맨틱 토큰 계약 2.0.0 의 투영 대상**이고 그 투영이 홈 `tokens.css` 미러로 나간다. 거기에 role 을 더하는 것은 **토큰 계약 변경**이라 버전 범프와 미러 재동기화를 동반해야 한다 — 이월 정리 PR 이 할 일이 아니다. 이 레포는 정확히 그 축에서 사고를 낸 적이 있다(홈 미러가 버전 없이 어긋난 건). — 틀렸을 때의 비용: 두 클래스가 당분간 공존한다. 상호 참조 주석이 오용을 막고, Task 15 의 DESIGN.md 개정이 문서로 닫는다.
- **Ruling(deferred minor 9 = M13): 고친다.** 마이페이지 주석의 「오늘 화면이 쓰는 것과 같은 값·문구다」가 사실이 아니다(오늘 화면에 `'N일 연속'` 합성 문구가 없다). **이 문구는 컨트롤러가 dispatch 에 그대로 받아 적은 것이라 원인도 컨트롤러에 있다.** 이 레포의 최상위 규칙이 「추측 금지 / 확인한 사실만」이고, 이 주석은 다음 사람에게 잘못된 커플링 가정을 심는다.
- **Ruling(M4): 고친다.** 계획 Task 6 Step 1 이 명시한 **렌더 단언**(`tester.getSize(...).height ≈ 16`)이 구현 테스트에서 조용히 빠졌다. Task 6 의 존재 이유가 「바뀐 높이를 테스트로 고정한다」이므로 선언 스타일(`style.height`)만으로는 계약이 잠기지 않는다. 한 줄.
- **Ruling(M2): 고치지 않는다 — Task 17 에 기록한다.** 지적 = `DpSteps._Step` 의 패딩·글자 크기가 시안 `.steps li{padding:6px 12px;font-size:13px}` 와 다르다(구현 4/12 + bodyMedium 14). — **왜 I1 과 다르게 판정하는가**: I1 은 **Task 3 이 스스로 인용한 규칙의 미완**이라 그 Task 의 범위 안이다. M2 는 이 PR 의 **어떤 Task 도 인용하지 않은** 시안 divergence 이고 이월 목록에도 없다 — 고치면 계획 밖 범위 확대다. 이 레포의 규칙이 「명세에 없는 것을 즉흥 구현하지 말라」이다. — 틀렸을 때의 비용: PR-2 가 현재 모양을 기준선으로 굳히고, 나중에 고치면 재기록이 한 번 더 필요하다. **Task 17 의 `baseline-impact-p5.md` 에 「새로 발견한 시안 divergence」로 적어 다음 단계가 판단하게 한다.**
- **Ruling(Declined-to-judge 6): Task 17 에 기록한다.** `apps/web` 에 리터럴 `TextStyle(fontSize:)` 가 **10곳** 남아 있어(`dp_design/lib` 은 이제 0곳) 같은 화면에서 12px 글자의 줄 높이가 둘(토큰 16 vs 리터럴 19.2)이 된다. Task 6 의 명시 범위가 `dp_design` 이라 이 PR 은 건드리지 않는다. **후속 과제로 기록한다.**
- 나머지 Declined 11건과 Minor 9건은 **deferred** — Task 17 의 원장에 옮긴다.

### 최종 리뷰 수정 물결 — 컨트롤러 직접 검증

단일 dispatch 로 다섯 항목(I1 · 승격된 M1 · I2 주석 · I3 문서 · M4)을 한 번에 고쳤다. 커밋 2개.

| 확인 | 결과 |
|---|---|
| 바뀐 파일 | 6개(`dp_next_action_band.dart`·`dp_spacing.dart`·`mypage_page.dart` + 테스트 3) ✔ 설정 파일 없음 |
| I1 | `color: accentSoft` · `border: accentLine` + 시안 인용 주석. 그림자 주석도 「배경 + 테두리 한 겹」으로 갱신 ✔ |
| M1 | `${widget.disabledReason ?? '지금은 사용할 수 없습니다'}` + 「assert 는 릴리스에서 제거된다」 주석 ✔ |
| I2·M13 | 배지 출처 주석을 「값은 같고 **문구는 다르다**」로 교정 · 사이드 kv 에 「남은 divergence」 문단 추가 ✔ 레이아웃 무변경 |
| I3 | `DpDensity`↔`DpWebDensity` 상호 참조 + **「CSS 투영 대상이 아니다」** 명시 ✔ 값 무변경 |
| M4 | `tester.getSize(find.text('✓ 완료')).height` 를 `closeTo(16, 0.5)` 로 고정. **실측 정확히 16.0** — `labelMedium` 의 `height 16/12 × fontSize 12` 와 일치 ✔ |
| 대비 테스트 | `textSecondary` on `accentSoft` 단언을 두 테마 루프 안에 추가 ✔ P4 M5 가 「실재하지 않는다」며 뺐던 것이 이제 실재하므로 같은 원칙으로 되돌린 것 |
| 세 스위트 (직접 실행) | **392**(389+3) / **1127**(유지) / **156**(유지) ✔ |
| 포맷(비파괴·27파일) | **0 changed** ✔ |

- 트레일러가 또 `Claude Sonnet 5` 로 2건 들어와 `filter-branch` 로 정리(`945fea7`→**`e2b602c`**, `3508210`→**`91c9964`**). **내용 무변경 검증**: 트리 `bba423f7…` 동일 · 브랜치 diff sha256 `31a39506…` 동일. 이제 **16커밋 전부** 규약 트레일러다.
- **sonnet 구현자는 트레일러 확인 지시를 세 번 연속 따르지 않았다**(haiku 는 따랐다). 하네스가 주입하는 것으로 보이며, 컨트롤러가 커밋 직후 확인하는 것으로 처리한다.
수정 물결 재리뷰 = **5/5 ADDRESSED · 새 breakage 없음 · out-of-scope 없음** (`final-fix-rereview.md`).
**PR-1 구현 완결 — 16커밋 `eaa7f77..91c9964`. Task 11(푸시·PR·CI 판정) 착수.**

## Task 11 — PR-1 머지 완료

frontend PR **#239** `feat/s3-p5-carryover` → develop **`c8edb82`**. 16커밋.

CI **전 잡 pass/skipping · 실패 0 · `mergeStateStatus=CLEAN`**:

| 잡 | 결과 | 시간 |
|---|---|---|
| `analyze-test` | pass | 4m57s |
| `browser-ux` | pass | 5m17s |
| `perf-gate` | pass | 21m46s |
| `produce-atomic-pair` | pass | 9m16s |
| `web-image-config-contract` (off/on) | pass | 11m34s · 8m43s |
| ET13 auth · admin-image · web-image · web-image-release-contract | skipping | 0 |

실측으로 확인된 세 가지:
1. **`analyze-test` 통과가 컨트롤러의 판정을 확증했다** — 로컬 1건은 CI 핀 Dart 3.12.1 에 없는 린트다.
2. **`perf-gate` 통과** — 그림자 제거·줄 높이 변화·밴드 배경 변경에도 전송량·CWV 가 옛 기준선 대비 +5% 안이다. (기준선 자체는 P2 이전 것이라 Task 14 가 다시 기록한다.)
3. **`browser-ux` 통과** — 시맨틱스 변경 셋(`ExcludeSemantics`·밴드 라벨 분기·패널 `Material`)이 axe 를 깨지 않았다.

**다음: PR-2 (Task 12~17) — 컨트롤러가 직접(Native) 수행한다.**
