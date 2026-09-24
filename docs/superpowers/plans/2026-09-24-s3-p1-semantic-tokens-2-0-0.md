# S3-P1 — 시맨틱 토큰 계약 2.0.0 (웹 문법: 반경·밀도·레이아웃 폭, `rail*` → `header*`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `packages/dp_design` 의 시맨틱 토큰 계약을 **2.0.0** 으로 올려 웹 문법의 반경·밀도·레이아웃 폭을 코드 SSoT 에 박고, 다크 레일 전용 색 6종을 `header*` 로 승계한 뒤, 홈 `assets/tokens.css` 미러와 Claude Design 번들을 같은 값으로 재동기화한다(S3 의 P2~P5 는 이 계약 위에서 진행한다).

**Architecture:** 값은 전부 `DpRadius`·`DpDensity`(신설)·`AppTokens.standard`·`DpColors` 에서 나오고 `DpSemanticTokenManifest` 가 CSS 로 투영한다(변경 지점 = 코드 상수 + 투영 이름). 위젯은 토큰을 기호로 소비하므로 `DpTheme` 의 컨트롤 최소 크기·탭 타깃 정책만 함께 바꾸면 전 화면의 반경·밀도가 한 번에 옮겨진다. 셸(`DpAppShell`·`DpNavRail`)과 화면은 이 PR 에서 **바꾸지 않는다** — P2~P4 의 일이다. 홈 미러는 별도 레포 PR(사용자 결정 뒤).

**Tech Stack:** Flutter **3.44.1**(CI 핀, 로컬 `D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin/flutter.bat`) · Dart pub workspace + melos 7(`dart run melos …`) · Node 20(browser-ux 러너, 홈 vitest) · GitHub Actions(`analyze-test`·`browser-ux`·`perf-gate`·`web-image-config-contract`·ET13 `produce-atomic-pair`) · Claude Design `Leva Design Tokens`(DesignSync 도구) · 홈 vitest + Playwright visual evidence(핀 이미지).

**Spec:** documents `docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` §5.3·§5.4·§7(P1)·§8·§10, 시안 https://claude.ai/artifact/DWi8kMV6QcAzBEQwbrNPNd (Version 2 — `--r-card 8px / --r-btn 6px / --r-chip 4px`, `data-hit="24"` → `--hit 30px; --rowpad 8px`, 헤더 56px, `.main` 최대폭 1120px, `.prose` 760px).

## Global Constraints

- 반경(스펙 §5.3 + 시안): 칩 **4** · 버튼 **6** · 카드/패널 **8** · 입력 **6** · 다이얼로그 **12**. `AppTokens.panelRadius == DpRadius.card`.
- 밀도(스펙 §5.4-1): 컨트롤 높이 **30** · 표 행 여백 **8** · 최소 포인터 타깃 **24**(WCAG 2.2 AA 2.5.8; 390 폭에서도 같은 기준, 인접 타깃 간격으로 예외 조건 충족). 44px 기준은 DESIGN.md §6·browser-ux 러너에서 **함께** 바꾼다 — 한쪽만 바꾸면 CI `browser-ux` 가 실패한다.
- 레이아웃 폭(시안): `contentMaxWidth` **1120** · `readableMaxWidth` **760**(유지) · `headerHeight` **56**(신설). `railWidth` 280 · `railCollapsedWidth` 80 은 **유지**(`apps/admin` 의 `DpAppShell`/`DpNavRail` 이 쓴다 — 스펙 §7 P2).
- 색(스펙 §5.4-2): `railBg·railText·railMuted·railFaint·railActive·railBorder` → `headerBg·headerText·headerMuted·headerFaint·headerActive·headerBorder`. **값은 한 글자도 바꾸지 않는다**(라이트 `#11131B·#F5F7FB·#B7BDCA·#959DAD·#272B3F·#2A2F3C`, 다크 `#090B10·#F4F5F8·#B6BCC8·#929AA8·#23263B·#292D38`). CSS 이름은 `_kebabCase` 파생이라 `--dp-color-header-*` 로 자동 변경.
- 계약 버전: `DpSemanticTokenManifest.version` `'1.1.0'` → **`'2.0.0'`**(이름·값이 바뀌므로 major). `schema` `'leva.semantic-tokens'` 유지.
- 색·폰트·상태 매핑(`stateMappings`)·간격(`DpSpacing`)·모션(`DpDurations`)·타이포그래피는 **변경 금지**(스펙 §5.3 "색·폰트·접근성 계약은 유지").
- 이 PR 은 `develop` 대상 한 개(스펙 §7 "단계별 PR"). 셸 교체·위젯 웹화·화면 개편·FAB 제거는 넣지 않는다. 시안에 없는 요소를 즉흥으로 만들지 않는다.
- ET13 시각 기준선은 이 PR 로 전부 달라진다 — **기준선 재승인은 P5(사람 단계)** 이고, develop PR 의 `produce-atomic-pair` 는 증거를 만들기만 한다(스펙 §9). PR 설명에 이 사실을 적는다.
- 로컬 검증은 `analyze`·단위 테스트까지(스펙 §7 원칙; 웹 빌드·Playwright 는 CI). Windows: Flutter 는 위 절대경로의 `flutter.bat` 만(Git Bash PATH 가 `D:/` 접두를 무시해 다른 버전을 잡는다) · `dart format` 은 워크스페이스 루트에서 · `packages/dp_design/test/theme/dp_code_font_test.dart` 1건은 CRLF 체크아웃에서 실패할 수 있다(CI 통과, 무시) · 여러 줄 치환은 Write/Edit 도구 또는 스크래치패드 파이썬(heredoc 은 백슬래시를 먹는다).
- 브랜치 흐름: `origin/develop` 에서 `feat/s3-p1-semantic-tokens-2-0-0` → develop PR → CI 녹색 → merge commit. `main` 직접 push 금지. 커밋 메시지 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- 작업 위치: 워크트리 `D:/workspace/dpa/.worktrees/frontend-s3p1-20260924`(아래 `WT`). 모든 git·파일 명령은 절대경로 또는 `git -C "$WT"`.

## Review Focus

1. **390px 폭 + 30px 컨트롤**: `role=button` 이 24×24 이상이어도 서로 붙으면 2.5.8 위반이다 — Task 5 의 러너는 24 미만만 잡으므로, Task 4 의 위젯 테스트가 인접 버튼 사이 간격(≥ 8px, `DpSpacing.sm`)을 한 번 단언한다.
2. **긴 한국어 라벨이 30px 버튼에서 두 줄로 접힘**: 라벨이 두 줄이 되면 30px 을 넘거나 잘린다 — Task 4 가 `FilledButton` 의 높이는 30 이고 라벨은 한 줄(`softWrap`/`overflow` 기본)임을 단언한다.
3. **`AppTokens.lerp`/`copyWith` 가 새 필드 `headerHeight` 를 빼먹음**: 테마 전환에서 헤더 높이만 튄다 — Task 1 이 `lerp(t=1)`·`copyWith(headerHeight:)` 를 단언한다.
4. **홈 미러 파서의 선택자 형태**: 홈 계약 테스트의 정규식은 `[data-theme="dark"] {` 만 읽는다 — Flutter 덤프의 `[data-theme="dark"], .dp-theme-dark {` 를 그대로 붙이면 다크 블록이 통째로 빠진다. Task 9 는 선택자를 손으로 유지하고 테스트가 다크 값을 실제로 읽는지(`--dp-color-header-bg` 다크 `#090B10`) 단언한다.
5. **어두운 헤더의 대비**: 이름만 바뀌었지만 P2 의 헤더가 `headerActive` 위에 `headerMuted` 텍스트를 놓을 때 4.5:1 이 필요하다 — Task 2 가 기존 레일 대비 테스트를 헤더 이름으로 그대로 유지(값 불변 → 통과)하고 설명 문구를 헤더로 바꾼다.

---

### Task 1: 반경·밀도·레이아웃 폭 토큰 2.0.0 (`DpRadius`·`DpDensity`·`AppTokens`)

**Files:**
- Modify: `packages/dp_design/lib/src/theme/dp_spacing.dart:14-20` (`DpRadius` 값), 같은 파일 끝에 `DpDensity` 추가
- Modify: `packages/dp_design/lib/src/theme/dp_tokens.dart` (`headerHeight` 필드 + `standard` 값)
- Modify: `packages/dp_design/test/theme/dp_tokens_test.dart:21-25,38`
- Create: `packages/dp_design/test/theme/dp_radius_density_test.dart`

**Interfaces:**
- Produces: `DpRadius.chip=4, button=6, card=8, input=6, dialog=12` · `abstract final class DpDensity { static const double controlHeight = 30; static const double rowPadding = 8; static const double minTarget = 24; }` · `AppTokens.headerHeight` (double), `AppTokens.standard = (1120, 760, 280, 80, panelRadius 8, headerHeight 56)`. Task 3·4·9 가 이 이름을 쓴다.

- [ ] **Step 1: 워크트리·브랜치·부트스트랩**

```bash
cd /d/workspace/dpa/devpath-frontend && git fetch -q origin develop
git -C /d/workspace/dpa/devpath-frontend worktree add "D:/workspace/dpa/.worktrees/frontend-s3p1-20260924" -b feat/s3-p1-semantic-tokens-2-0-0 origin/develop
WT="D:/workspace/dpa/.worktrees/frontend-s3p1-20260924"; FLUTTER="D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin/flutter.bat"; DART="D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin/dart.bat"
cd "$WT" && "$DART" run melos bootstrap --enforce-lockfile
```
Expected: `melos bootstrap` 성공(lockfile 변화 없음). `git -C "$WT" status --porcelain` 이 빈 출력.

- [ ] **Step 2: 실패하는 테스트 작성**

`packages/dp_design/test/theme/dp_radius_density_test.dart`:
```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('DpRadius 2.0.0 — 웹 문법 반경(칩 4·버튼 6·카드 8·입력 6·다이얼로그 12)', () {
    expect(DpRadius.chip, 4);
    expect(DpRadius.button, 6);
    expect(DpRadius.card, 8);
    expect(DpRadius.input, 6);
    expect(DpRadius.dialog, 12);
  });

  test('DpDensity — 포인터 밀도(컨트롤 30·행 여백 8·최소 타깃 24 = WCAG 2.2 AA 2.5.8)', () {
    expect(DpDensity.controlHeight, 30);
    expect(DpDensity.rowPadding, 8);
    expect(DpDensity.minTarget, 24);
    expect(DpDensity.minTarget, lessThan(DpDensity.controlHeight));
  });

  test('AppTokens.standard — 웹 레이아웃 폭·헤더 높이, panelRadius 는 카드 반경과 같다', () {
    expect(AppTokens.standard.contentMaxWidth, 1120);
    expect(AppTokens.standard.readableMaxWidth, 760);
    expect(AppTokens.standard.headerHeight, 56);
    expect(AppTokens.standard.panelRadius, DpRadius.card);
    // apps/admin 의 DpAppShell·DpNavRail 이 아직 쓰는 레일 폭은 P2 까지 그대로 둔다.
    expect(AppTokens.standard.railWidth, 280);
    expect(AppTokens.standard.railCollapsedWidth, 80);
  });

  test('AppTokens.copyWith/lerp 는 headerHeight 를 함께 다룬다', () {
    final taller = AppTokens.standard.copyWith(headerHeight: 64);
    expect(taller.headerHeight, 64);
    expect(taller.contentMaxWidth, AppTokens.standard.contentMaxWidth);
    final lerped = AppTokens.standard.lerp(taller, 1);
    expect(lerped, isA<AppTokens>());
    expect((lerped as AppTokens).headerHeight, 64);
  });
}
```

그리고 `packages/dp_design/test/theme/dp_tokens_test.dart` 의 기대값을 바꾼다(21~25행, 38행):
```dart
    expect(t.contentMaxWidth, 1120);
    expect(t.readableMaxWidth, 760);
    expect(t.railWidth, 280);
    expect(t.railCollapsedWidth, 80);
    expect(t.panelRadius, 8);
    expect(t.headerHeight, 56);
```
(다크 테스트의 `expect(t.railWidth, 280);` 은 그대로.)

- [ ] **Step 3: 실패 확인**

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/theme/dp_radius_density_test.dart test/theme/dp_tokens_test.dart
```
Expected: 컴파일 오류 `Undefined name 'DpDensity'` / `The getter 'headerHeight' isn't defined` → FAIL.

- [ ] **Step 4: 최소 구현**

`packages/dp_design/lib/src/theme/dp_spacing.dart` — `DpRadius` 를 다음으로 바꾸고 파일 끝에 `DpDensity` 를 더한다:
```dart
/// 반경 — 웹 문법(계약 2.0.0, 스펙 §5.3 + 시안 `--r-chip/--r-btn/--r-card`).
/// 칩·태그 4, 버튼·입력 6, 카드·패널·드롭다운 8, 다이얼로그·시트 12.
abstract final class DpRadius {
  static const double chip = 4;
  static const double button = 6;
  static const double card = 8;
  static const double input = 6;
  static const double dialog = 12;
}
```
```dart
/// 포인터 밀도(계약 2.0.0, 스펙 §5.4-1 — 사용자 결정 "촘촘").
/// 컨트롤(버튼·입력·세그먼트·헤더 항목) 높이 30, 표 행 세로 여백 8,
/// 최소 포인터 타깃 24 = WCAG 2.2 AA 2.5.8. 24 미만인 타깃은 인접 타깃과의
/// 간격으로 예외 조건을 만족시켜야 한다(browser-ux 러너 `MIN_TARGET` 과 같은 값).
abstract final class DpDensity {
  static const double controlHeight = 30;
  static const double rowPadding = 8;
  static const double minTarget = 24;
}
```

`packages/dp_design/lib/src/theme/dp_tokens.dart` — 생성자·필드·`standard`·`copyWith`·`lerp` 에 `headerHeight` 를 더한다:
```dart
/// 레이아웃 토큰(폭·반경·헤더 높이). DESIGN.md §3·§5 + 스펙 2026-09-19 §5.3.
/// 색과 달리 밝기 무관 — light/dark 모두 [standard] 단일값을 쓴다.
@immutable
class AppTokens extends ThemeExtension<AppTokens> {
  const AppTokens({
    required this.contentMaxWidth,
    required this.readableMaxWidth,
    required this.railWidth,
    required this.railCollapsedWidth,
    required this.panelRadius,
    required this.headerHeight,
  });

  final double contentMaxWidth;
  final double readableMaxWidth;
  /// admin 의 DpAppShell/DpNavRail 이 쓴다. web 셸은 P2 에서 헤더로 바뀐다.
  final double railWidth;
  final double railCollapsedWidth;
  final double panelRadius;
  /// 상단 헤더 높이(시안 `.hd` 56px). P2 의 DpWebShell 이 소비한다.
  final double headerHeight;

  static const standard = AppTokens(
    contentMaxWidth: 1120,
    readableMaxWidth: 760,
    railWidth: 280,
    railCollapsedWidth: 80,
    panelRadius: 8, // = DpRadius.card
    headerHeight: 56,
  );

  @override
  AppTokens copyWith({
    double? contentMaxWidth,
    double? readableMaxWidth,
    double? railWidth,
    double? railCollapsedWidth,
    double? panelRadius,
    double? headerHeight,
  }) => AppTokens(
    contentMaxWidth: contentMaxWidth ?? this.contentMaxWidth,
    readableMaxWidth: readableMaxWidth ?? this.readableMaxWidth,
    railWidth: railWidth ?? this.railWidth,
    railCollapsedWidth: railCollapsedWidth ?? this.railCollapsedWidth,
    panelRadius: panelRadius ?? this.panelRadius,
    headerHeight: headerHeight ?? this.headerHeight,
  );

  @override
  AppTokens lerp(ThemeExtension<AppTokens>? other, double t) {
    if (other is! AppTokens) return this;
    return AppTokens(
      contentMaxWidth: _lerp(contentMaxWidth, other.contentMaxWidth, t),
      readableMaxWidth: _lerp(readableMaxWidth, other.readableMaxWidth, t),
      railWidth: _lerp(railWidth, other.railWidth, t),
      railCollapsedWidth: _lerp(
        railCollapsedWidth,
        other.railCollapsedWidth,
        t,
      ),
      panelRadius: _lerp(panelRadius, other.panelRadius, t),
      headerHeight: _lerp(headerHeight, other.headerHeight, t),
    );
  }

  static double _lerp(double a, double b, double t) => a + (b - a) * t;
}
```
(`AppTokensX` 확장은 그대로.)

- [ ] **Step 5: 통과 확인 + 패키지 전체 테스트**

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/theme/dp_radius_density_test.dart test/theme/dp_tokens_test.dart && "$FLUTTER" test --exclude-tags golden
```
Expected: 두 파일 PASS. 전체 스위트는 `dp_code_font_test`(CRLF, 알려진 로컬 실패) 외 PASS — 위젯은 `DpRadius`·`AppTokens` 를 기호로 소비하므로 값 변경만으로 깨지는 테스트가 없어야 한다. 다른 실패가 나오면 **그 테스트가 리터럴(18·12·999·1360)을 핀한 것** — 리터럴을 `DpRadius.*`/`AppTokens.standard.*` 기호로 바꾼다(값 되돌리기 금지).

- [ ] **Step 6: 커밋**

```bash
cd "$WT" && "$DART" format packages/dp_design/lib/src/theme packages/dp_design/test/theme && git -C "$WT" add packages/dp_design/lib/src/theme/dp_spacing.dart packages/dp_design/lib/src/theme/dp_tokens.dart packages/dp_design/test/theme/dp_radius_density_test.dart packages/dp_design/test/theme/dp_tokens_test.dart && git -C "$WT" commit -q -F - <<'MSG'
feat(dp_design): web-grammar radii, pointer density and layout widths (tokens 2.0.0, part 1)

DpRadius chip 999->4, button 12->6, card 18->8, input 12->6, dialog 20->12 (spec 2026-09-19 §5.3, mock-up
--r-chip/--r-btn/--r-card). New DpDensity: controlHeight 30, rowPadding 8, minTarget 24 (WCAG 2.2 AA 2.5.8,
user decision §5.4-1). AppTokens.standard: contentMaxWidth 1360->1120, panelRadius 18->8, new headerHeight 56;
rail widths stay for apps/admin until P2.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
MSG
```

---

### Task 2: `rail*` 색 6종을 `header*` 로 승계 (값 불변, 이름·CSS 투영 변경)

**Files:**
- Modify: `packages/dp_design/lib/src/theme/dp_colors.dart` (필드·생성자·`light`·`dark`·`copyWith`·`lerp`)
- Modify: `packages/dp_design/lib/src/theme/dp_semantic_tokens.dart:63-96,108-114,150-156` (`DpSemanticColorRole` 6 값·`resolve`·`allowedUsages`)
- Modify: `packages/dp_design/lib/src/shell/dp_nav_rail.dart` (13 참조), `packages/dp_design/lib/src/shell/dp_rail_brand.dart:8-9` (주석)
- Modify tests: `packages/dp_design/test/theme/dp_colors_integrity_test.dart`, `dp_colors_contrast_test.dart`, `dp_semantic_tokens_test.dart`(역할 이름만 — 값·버전은 Task 3), `packages/dp_design/test/shell/dp_nav_rail_test.dart`, `dp_nav_rail_dark_test.dart`, `dp_rail_brand_test.dart`, `apps/web/test/features/shell/app_shell_view_test.dart:204-270`, `apps/admin/test/features/shell/admin_shell_view_test.dart:84-134`, `apps/web/lib/src/features/shell/presentation/app_shell.dart:345`(주석)

**Interfaces:**
- Consumes: 없음(Task 1 과 독립).
- Produces: `DpColors.headerBg/headerText/headerMuted/headerFaint/headerActive/headerBorder`, `DpSemanticColorRole.headerBg…headerBorder`, CSS `--dp-color-header-bg` … `--dp-color-header-border`. P2 의 `DpWebShell` 과 Task 9 의 홈 미러가 이 이름을 쓴다.

- [ ] **Step 1: 실패하는 테스트 — 무결성 테스트의 필드 목록을 헤더 이름으로**

`packages/dp_design/test/theme/dp_colors_integrity_test.dart` 22~27행을 다음으로 바꾼다:
```dart
  'headerBg': (c) => c.headerBg,
  'headerText': (c) => c.headerText,
  'headerMuted': (c) => c.headerMuted,
  'headerFaint': (c) => c.headerFaint,
  'headerActive': (c) => c.headerActive,
  'headerBorder': (c) => c.headerBorder,
```
같은 파일 62·70·77행:
```dart
    expect(mid.headerFaint, DpColors.light.headerFaint);
```
```dart
    expect(c.headerBg, DpColors.light.headerBg);
```
```dart
    expect(DpColors.light.headerBg, const Color(0xFF11131B));
```
그리고 값 불변 단언을 파일 끝 `main()` 안에 추가한다(마지막 `test` 뒤):
```dart
  test('header* 는 rail* 의 값을 그대로 승계한다(계약 2.0.0 이름 변경, 값 불변)', () {
    expect(DpColors.light.headerBg, const Color(0xFF11131B));
    expect(DpColors.light.headerText, const Color(0xFFF5F7FB));
    expect(DpColors.light.headerMuted, const Color(0xFFB7BDCA));
    expect(DpColors.light.headerFaint, const Color(0xFF959DAD));
    expect(DpColors.light.headerActive, const Color(0xFF272B3F));
    expect(DpColors.light.headerBorder, const Color(0xFF2A2F3C));
    expect(DpColors.dark.headerBg, const Color(0xFF090B10));
    expect(DpColors.dark.headerText, const Color(0xFFF4F5F8));
    expect(DpColors.dark.headerMuted, const Color(0xFFB6BCC8));
    expect(DpColors.dark.headerFaint, const Color(0xFF929AA8));
    expect(DpColors.dark.headerActive, const Color(0xFF23263B));
    expect(DpColors.dark.headerBorder, const Color(0xFF292D38));
  });
```

- [ ] **Step 2: 실패 확인**

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/theme/dp_colors_integrity_test.dart
```
Expected: 컴파일 오류 `The getter 'headerBg' isn't defined for the type 'DpColors'` → FAIL.

- [ ] **Step 3: 이름 일괄 변경(색 이름 6종만 — `railWidth`·`railCollapsedWidth` 는 건드리지 않는다)**

```bash
cd "$WT" && git grep -lE '\brail(Bg|Text|Muted|Faint|Active|Border)\b' -- packages apps | xargs sed -i -E 's/\brail(Bg|Text|Muted|Faint|Active|Border)\b/header\1/g'
git -C "$WT" grep -nE '\brail(Bg|Text|Muted|Faint|Active|Border)\b' -- packages apps; echo "remaining=$?"
git -C "$WT" grep -c 'railWidth' -- packages/dp_design/lib/src/theme/dp_tokens.dart
```
Expected: 두 번째 명령은 매치 0(`remaining=1`). 세 번째는 `railWidth` 가 그대로 남아 있음(3 이상).
변경 파일(전부 12개여야 한다): `dp_colors.dart`(필드·생성자·light·dark·copyWith·lerp), `dp_semantic_tokens.dart`(역할 enum·resolve·allowedUsages), `dp_nav_rail.dart`, `dp_rail_brand.dart`(주석), `dp_colors_integrity_test.dart`, `dp_colors_contrast_test.dart`, `dp_semantic_tokens_test.dart`, `dp_nav_rail_test.dart`, `dp_nav_rail_dark_test.dart`, `dp_rail_brand_test.dart`, `apps/web/test/features/shell/app_shell_view_test.dart`, `apps/admin/test/features/shell/admin_shell_view_test.dart`, `apps/web/lib/src/features/shell/presentation/app_shell.dart`(주석). `git -C "$WT" status --porcelain | wc -l` 로 개수를 확인한다.

- [ ] **Step 4: 사람 말도 헤더로 — 대비 테스트 제목과 `DpColors` 문서 주석**

`packages/dp_design/test/theme/dp_colors_contrast_test.dart` 56·64행의 제목:
```dart
      test('어두운 헤더 대비 — headerBg 위 메뉴 항목·섹션 레이블 4.5:1 (rail* 승계, 스펙 §5.4-2)', () {
```
```dart
      test('어두운 헤더 대비 — headerActive(hover/활성 면) 위 메뉴 라벨 4.5:1', () {
```
`packages/dp_design/lib/src/theme/dp_colors.dart` 의 `headerBg` 필드 선언 바로 위에 문서 주석을 단다(생성자 아래 `final Color headerBg;` 앞):
```dart
  /// 어두운 헤더(계약 2.0.0 — 2026-09-19 §5.4-2 에서 다크 레일 색 `rail*` 을 값 그대로 승계).
  /// P2 까지는 admin 의 DpNavRail 도 같은 토큰을 쓴다.
```

- [ ] **Step 5: 통과 확인(dp_design 전체 + web/admin 셸 테스트)**

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test --exclude-tags golden
cd "$WT/apps/web" && "$FLUTTER" test test/features/shell/app_shell_view_test.dart test/features/shell/app_shell_rail_toggle_test.dart
cd "$WT/apps/admin" && "$FLUTTER" test test/features/shell/admin_shell_view_test.dart
```
Expected: 전부 PASS(`dp_code_font_test` 로컬 실패 제외). `dp_semantic_tokens_test` 도 아직 PASS 여야 한다(역할 이름만 바뀌었고 버전 `1.1.0`·반경 CSS 값은 Task 3 에서 바꾼다 — 단 Task 1 이 `--dp-radius-chip` 을 `4px` 로 바꿨으므로 254~255행 두 단언은 **여기서 이미 실패한다**. 그 두 줄을 `'4px'`·`'8px'` 로 고쳐 두고 Task 3 에서 전체를 다시 쓴다).

- [ ] **Step 6: 커밋**

```bash
cd "$WT" && "$DART" format packages apps && git -C "$WT" add -A packages apps && git -C "$WT" commit -q -F - <<'MSG'
refactor(dp_design): rename the dark rail colour tokens to header* (values unchanged)

railBg/railText/railMuted/railFaint/railActive/railBorder -> headerBg/headerText/headerMuted/headerFaint/
headerActive/headerBorder in DpColors, DpSemanticColorRole (CSS --dp-color-header-*), DpNavRail and every
test that names them (dp_design, apps/web, apps/admin). Spec 2026-09-19 §5.4-2: the web header inherits the
dark rail palette; admin keeps DpNavRail on the same tokens until P2.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
MSG
```

---

### Task 3: 매니페스트 2.0.0 — 밀도 토큰 종류 추가, 버전, CSS 투영

**Files:**
- Modify: `packages/dp_design/lib/src/theme/dp_semantic_tokens.dart` (`DpSemanticTokenKind`·`DpSemanticTokenUsage`·`_DensityRole`·`DpSemanticTokenManifest.version/density/tokens`)
- Modify: `packages/dp_design/test/theme/dp_semantic_tokens_test.dart`
- Modify: `packages/dp_design/test/theme/dp_semantic_tokens_dump_test.dart:22-31` (layout 맵에 헤더 높이)

**Interfaces:**
- Consumes: Task 1 `DpDensity`, `AppTokens.headerHeight`; Task 2 `DpSemanticColorRole.header*`.
- Produces: `DpSemanticTokenKind.density`, `DpSemanticTokenUsage.interactionDensity`, `DpSemanticTokenManifest.density` (List<DpSemanticDimensionToken>), CSS `--dp-density-control-height: 30px`·`--dp-density-row-padding: 8px`·`--dp-density-min-target: 24px`, `--dp-token-manifest-version: "2.0.0"`, 덤프 `--dp-layout-header-height: 56px`. Task 7(design-sync)·Task 9(홈)이 이 키 집합을 그대로 미러한다.

- [ ] **Step 1: 실패하는 테스트 — 계약 테스트를 2.0.0 으로 고친다**

`packages/dp_design/test/theme/dp_semantic_tokens_test.dart` 에서:
- 6행 `group('DpSemanticTokenManifest v1', () {` → `group('DpSemanticTokenManifest v2 (2.0.0 — web grammar)', () {`
- 9행 `expect(DpSemanticTokenManifest.version, '1.1.0');` → `expect(DpSemanticTokenManifest.version, '2.0.0');`
- 170~200행의 테스트 이름을 `'spacing, radius, density, duration and typography values stay source-mapped'` 로 바꾸고 `radii` 단언 뒤(199행 `DpRadius.card,` `);` 다음)에 추가:
```dart
        expect(
          DpSemanticTokenManifest.radii.map((token) => token.lightValue).toList(),
          [DpRadius.chip, DpRadius.button, DpRadius.card, DpRadius.input, DpRadius.dialog],
        );
        expect(
          DpSemanticTokenManifest.density
              .map((token) => (token.cssCustomProperty, token.lightValue))
              .toList(),
          [
            ('--dp-density-control-height', DpDensity.controlHeight),
            ('--dp-density-row-padding', DpDensity.rowPadding),
            ('--dp-density-min-target', DpDensity.minTarget),
          ],
        );
        for (final token in DpSemanticTokenManifest.density) {
          expect(token.kind, DpSemanticTokenKind.density);
          expect(token.allowedUsages, {DpSemanticTokenUsage.interactionDensity});
          expect(DpSemanticTokenManifest.tokens, contains(token));
        }
```
- 241~258행 `CSS projection …` 테스트의 단언을 다음으로 바꾼다:
```dart
        expect(light['--dp-token-manifest-version'], '"2.0.0"');
        expect(light['--dp-color-primary'], '#5653E7');
        expect(dark['--dp-color-primary'], '#9B99FF');
        expect(light['--dp-color-header-bg'], '#11131B');
        expect(dark['--dp-color-header-bg'], '#090B10');
        expect(light['--dp-color-rail-bg'], isNull);
        expect(light['--dp-space-lg'], '16px');
        expect(light['--dp-radius-chip'], '4px');
        expect(light['--dp-radius-button'], '6px');
        expect(light['--dp-radius-panel'], '8px');
        expect(light['--dp-radius-input'], '6px');
        expect(light['--dp-radius-dialog'], '12px');
        expect(light['--dp-density-control-height'], '30px');
        expect(light['--dp-density-row-padding'], '8px');
        expect(light['--dp-density-min-target'], '24px');
        expect(light['--dp-layout-content-max'], isNull);
        expect(light['--dp-state-focus-ring'], '#4338CA');
        expect(dark['--dp-state-focus-ring'], '#B9B8FF');
        expect(light['--dp-state-focus-ring-width'], '2px');
```

`packages/dp_design/test/theme/dp_semantic_tokens_dump_test.dart` 22~31행의 `layout` 맵을 다음으로 바꾼다:
```dart
    final layout = {
      '--dp-layout-content-max':
          '${AppTokens.standard.contentMaxWidth.toInt()}px',
      '--dp-layout-readable-max':
          '${AppTokens.standard.readableMaxWidth.toInt()}px',
      '--dp-layout-header-height':
          '${AppTokens.standard.headerHeight.toInt()}px',
      '--dp-layout-rail': '${AppTokens.standard.railWidth.toInt()}px',
      '--dp-layout-rail-collapsed':
          '${AppTokens.standard.railCollapsedWidth.toInt()}px',
      for (final entry in breakpoints.entries)
        '--dp-breakpoint-${entry.key}': '${entry.value.toInt()}px',
    };
    expect(layout['--dp-layout-content-max'], '1120px');
    expect(layout['--dp-layout-header-height'], '56px');
    expect(light['--dp-token-manifest-version'], '"2.0.0"');
```

- [ ] **Step 2: 실패 확인**

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/theme/dp_semantic_tokens_test.dart test/theme/dp_semantic_tokens_dump_test.dart
```
Expected: `The getter 'density' isn't defined`, `DpSemanticTokenKind.density` 미정의 → FAIL.

- [ ] **Step 3: 구현**

`packages/dp_design/lib/src/theme/dp_semantic_tokens.dart`:

(a) 8행 `enum DpSemanticTokenKind { color, spacing, radius, duration, typography }` →
```dart
enum DpSemanticTokenKind { color, spacing, radius, density, duration, typography }
```
(b) `DpSemanticTokenUsage` 의 `motion,` 다음에 `interactionDensity,` 를 추가한다(순서: `layoutSpacing, panelShape, interactionDensity, motion, uiTypography, readingTypography`).

(c) `_RadiusRole` 확장 블록 뒤(즉 `final class DpSemanticDimensionToken` 앞)에 추가:
```dart
enum _DensityRole { controlHeight, rowPadding, minTarget }

extension on _DensityRole {
  double get value => switch (this) {
    _DensityRole.controlHeight => DpDensity.controlHeight,
    _DensityRole.rowPadding => DpDensity.rowPadding,
    _DensityRole.minTarget => DpDensity.minTarget,
  };
}
```
(d) `DpSemanticTokenManifest` 에서 `version` 과 `radii` 다음:
```dart
  static const String version = '2.0.0';
```
```dart
  /// 포인터 밀도(2.0.0 신설). 컨트롤 높이·표 행 여백·최소 타깃 — DpDensity 가 SSoT.
  static final List<DpSemanticDimensionToken> density = List.unmodifiable(
    _DensityRole.values.map(
      (role) => DpSemanticDimensionToken(
        kind: DpSemanticTokenKind.density,
        flutterName: 'DpDensity.${role.name}',
        cssCustomProperty: '--dp-density-${_kebabCase(role.name)}',
        value: role.value,
        allowedUsages: const {DpSemanticTokenUsage.interactionDensity},
      ),
    ),
  );
```
(e) `tokens` 목록을 `[...colors, ...spacing, ...radii, ...density, ...durations, ...typography]` 로.
(f) `DpSemanticTokenManifest` 의 문서 주석 `/// v1 manifest. …` → `/// 2.0.0 manifest(웹 문법). 값은 DpColors/DpSpacing/DpRadius/DpDensity/DpTypography 에서 읽으며 Landing mirror 가 사용할 CSS 이름과 상태 mapping 을 함께 고정한다.`

- [ ] **Step 4: 통과 확인**

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/theme/dp_semantic_tokens_test.dart test/theme/dp_semantic_tokens_dump_test.dart && "$FLUTTER" test --exclude-tags golden
```
Expected: PASS(로컬 `dp_code_font_test` 제외).

- [ ] **Step 5: 커밋**

```bash
cd "$WT" && "$DART" format packages/dp_design && git -C "$WT" add packages/dp_design && git -C "$WT" commit -q -F - <<'MSG'
feat(dp_design): semantic token manifest 2.0.0 — density tokens, header colours, web radii projection

Adds DpSemanticTokenKind.density / DpSemanticTokenUsage.interactionDensity with --dp-density-control-height
(30px), --dp-density-row-padding (8px), --dp-density-min-target (24px); bumps the contract to 2.0.0 because
the rail colour names and the radius/layout values changed. The design-sync dump gains
--dp-layout-header-height (56px).

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
MSG
```

---

### Task 4: 테마 밀도 — 30px 컨트롤, 24px 최소 타깃, `DpTapTarget` 기본값

**Files:**
- Modify: `packages/dp_design/lib/src/theme/dp_theme.dart:51-125` (visualDensity 주석·segmented·filled·outlined·text·input) + `iconButtonTheme` 추가
- Modify: `packages/dp_design/lib/src/a11y/dp_tap_target.dart:3-10`
- Modify tests: `packages/dp_design/test/theme/dp_theme_v2_test.dart`, `packages/dp_design/test/theme/dp_segmented_button_theme_test.dart`, `packages/dp_design/test/a11y/dp_tap_target_test.dart`
- Create: `packages/dp_design/test/theme/dp_theme_density_test.dart`

**Interfaces:**
- Consumes: Task 1 `DpDensity`, `DpRadius`, `DpSpacing`.
- Produces: 테마 계약 — `filledButtonTheme/outlinedButtonTheme.minimumSize == Size(64, DpDensity.controlHeight)`, `textButtonTheme.minimumSize == Size(DpDensity.minTarget, DpDensity.controlHeight)`, `iconButtonTheme.minimumSize == Size(DpDensity.controlHeight, DpDensity.controlHeight)`, 모든 버튼 `tapTargetSize == MaterialTapTargetSize.shrinkWrap`, `inputDecorationTheme.isDense == true`, `contentPadding == EdgeInsets.symmetric(horizontal: DpSpacing.md, vertical: 5)`; `DpTapTarget.minSize` 기본 `DpDensity.minTarget`. P2~P4 위젯이 이 위에서 30px 로 렌더된다.

- [ ] **Step 1: 실패하는 테스트**

`packages/dp_design/test/theme/dp_theme_v2_test.dart` 의 첫 테스트를 다음으로 바꾼다:
```dart
  testWidgets('Leva 2.0.0 theme styles primary controls as 30px pointer actions', (
    tester,
  ) async {
    late ThemeData theme;
    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: Builder(
          builder: (context) {
            theme = Theme.of(context);
            return const SizedBox();
          },
        ),
      ),
    );

    final buttonStyle = theme.filledButtonTheme.style!;
    expect(buttonStyle.minimumSize!.resolve({}), Size(64, DpDensity.controlHeight));
    expect(buttonStyle.tapTargetSize, MaterialTapTargetSize.shrinkWrap);
    expect(
      (buttonStyle.shape!.resolve({})! as RoundedRectangleBorder).borderRadius,
      BorderRadius.circular(DpRadius.button),
    );
    expect(
      theme.outlinedButtonTheme.style!.minimumSize!.resolve({}),
      Size(64, DpDensity.controlHeight),
    );
    expect(
      theme.textButtonTheme.style!.minimumSize!.resolve({}),
      Size(DpDensity.minTarget, DpDensity.controlHeight),
    );
    expect(
      theme.iconButtonTheme.style!.minimumSize!.resolve({}),
      Size(DpDensity.controlHeight, DpDensity.controlHeight),
    );
    expect(theme.iconButtonTheme.style!.tapTargetSize, MaterialTapTargetSize.shrinkWrap);
    expect(theme.inputDecorationTheme.filled, isTrue);
    expect(theme.inputDecorationTheme.isDense, isTrue);
    expect(
      theme.inputDecorationTheme.contentPadding,
      const EdgeInsets.symmetric(horizontal: DpSpacing.md, vertical: 5),
    );
    expect(theme.inputDecorationTheme.fillColor, DpColors.light.surfaceMuted);
  });
```

`packages/dp_design/test/theme/dp_segmented_button_theme_test.dart` 전체를 다음으로 바꾼다:
```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets(
    'SegmentedButton 세그먼트는 30px 컨트롤 높이(±4)이며 24px 최소 타깃을 넘는다',
    (tester) async {
      tester.view.physicalSize = const Size(390, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(
        MaterialApp(
          theme: DpTheme.light(),
          home: Scaffold(
            body: SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 0, label: Text('자유게시판')),
                ButtonSegment(value: 1, label: Text('Q/A')),
                ButtonSegment(value: 2, label: Text('피드백')),
              ],
              selected: const {0},
              onSelectionChanged: (_) {},
            ),
          ),
        ),
      );
      final height = tester.getSize(find.byType(SegmentedButton<int>)).height;
      expect(height, greaterThanOrEqualTo(DpDensity.minTarget));
      expect(
        height,
        inInclusiveRange(DpDensity.controlHeight, DpDensity.controlHeight + 4),
      );
      // 계약 2.0.0(스펙 §5.4-1): 포인터 밀도. 44px 터치 기준은 2026-09-19 에 24px(WCAG 2.2 AA 2.5.8)로 옮겼다.
    },
    variant: TargetPlatformVariant.only(TargetPlatform.windows),
  );

  testWidgets('TextButton 은 30px 컨트롤이고 한 줄 라벨을 자르지 않는다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: Scaffold(
          body: Center(
            child: TextButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.code),
              label: const Text('실습으로 돌아가기'),
            ),
          ),
        ),
      ),
    );
    final size = tester.getSize(find.byType(TextButton));
    expect(size.height, DpDensity.controlHeight);
    expect(tester.takeException(), isNull); // 오버플로 없음
  });

  testWidgets('FilledButton 은 30px 이고 인접 버튼과 8px 이상 떨어지면 2.5.8 간격 예외를 만족한다', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: Scaffold(
          body: Row(
            children: [
              FilledButton(onPressed: () {}, child: const Text('실습 시작하기')),
              const SizedBox(width: DpSpacing.sm),
              OutlinedButton(onPressed: () {}, child: const Text('취소')),
            ],
          ),
        ),
      ),
    );
    final filled = tester.getRect(find.byType(FilledButton));
    final outlined = tester.getRect(find.byType(OutlinedButton));
    expect(filled.height, DpDensity.controlHeight);
    expect(outlined.height, DpDensity.controlHeight);
    expect(outlined.left - filled.right, greaterThanOrEqualTo(DpSpacing.sm));
  });
}
```

`packages/dp_design/test/a11y/dp_tap_target_test.dart` 6·22·23행:
```dart
  testWidgets('작은 child도 24x24(DpDensity.minTarget) 이상 탭 영역을 보장한다', (tester) async {
```
```dart
    expect(size.width, greaterThanOrEqualTo(DpDensity.minTarget));
    expect(size.height, greaterThanOrEqualTo(DpDensity.minTarget));
```
(파일 상단 import 에 `import 'package:dp_design/dp_design.dart';` 가 없으면 추가한다.)

`packages/dp_design/test/theme/dp_theme_density_test.dart`(신규):
```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('TextField 는 밀도 토큰으로 30px 근처의 한 줄 컨트롤이 된다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: const Scaffold(
          body: Center(
            child: SizedBox(
              width: 280,
              child: TextField(decoration: InputDecoration(hintText: '검색  Ctrl K')),
            ),
          ),
        ),
      ),
    );
    final height = tester.getSize(find.byType(TextField)).height;
    expect(height, inInclusiveRange(DpDensity.controlHeight, DpDensity.controlHeight + 6));
  });

  testWidgets('IconButton 은 30x30 이며 24px 최소 타깃을 넘는다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: Scaffold(
          body: Center(
            child: IconButton(onPressed: () {}, icon: const Icon(Icons.search), tooltip: '검색'),
          ),
        ),
      ),
    );
    final size = tester.getSize(find.byType(IconButton));
    expect(size.width, DpDensity.controlHeight);
    expect(size.height, DpDensity.controlHeight);
    expect(size.shortestSide, greaterThanOrEqualTo(DpDensity.minTarget));
  });
}
```

- [ ] **Step 2: 실패 확인**

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/theme/dp_theme_v2_test.dart test/theme/dp_segmented_button_theme_test.dart test/a11y/dp_tap_target_test.dart test/theme/dp_theme_density_test.dart
```
Expected: `Size(64, 52) != Size(64, 30)`, 세그먼트 높이 44 이상(범위 밖), `iconButtonTheme.style` null → FAIL.

- [ ] **Step 3: 구현**

`packages/dp_design/lib/src/theme/dp_theme.dart` — `visualDensity` 주석부터 `inputDecorationTheme` 까지(51~112행)를 다음으로 바꾼다:
```dart
      // 계약 2.0.0(스펙 §5.4-1 "촘촘"): 컨트롤 30px, 최소 포인터 타깃 24px(WCAG 2.2 AA 2.5.8).
      // 플랫폼 밀도에 기대지 않고 minimumSize 로 고정한다. tapTargetSize 는 shrinkWrap —
      // padded 는 레이아웃 크기를 48px 로 부풀려 30px 컨트롤을 만들 수 없다.
      visualDensity: VisualDensity.standard,
      segmentedButtonTheme: SegmentedButtonThemeData(
        style: ButtonStyle(
          padding: const WidgetStatePropertyAll(
            EdgeInsets.symmetric(horizontal: DpSpacing.md, vertical: 5),
          ),
          minimumSize: const WidgetStatePropertyAll(
            Size(DpDensity.minTarget, DpDensity.controlHeight),
          ),
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          textStyle: controlText,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: ButtonStyle(
          minimumSize: const WidgetStatePropertyAll(
            Size(64, DpDensity.controlHeight),
          ),
          padding: const WidgetStatePropertyAll(
            EdgeInsets.symmetric(horizontal: DpSpacing.lg),
          ),
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          shape: WidgetStatePropertyAll(roundedButton),
          textStyle: controlText,
          elevation: const WidgetStatePropertyAll(0),
          backgroundColor: WidgetStateProperty.resolveWith(
            (states) => states.contains(WidgetState.disabled)
                ? c.surfaceMuted
                : c.primary,
          ),
          foregroundColor: WidgetStateProperty.resolveWith(
            (states) => states.contains(WidgetState.disabled)
                ? c.textFaint
                : c.onPrimary,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: ButtonStyle(
          minimumSize: const WidgetStatePropertyAll(
            Size(64, DpDensity.controlHeight),
          ),
          padding: const WidgetStatePropertyAll(
            EdgeInsets.symmetric(horizontal: DpSpacing.lg),
          ),
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          shape: WidgetStatePropertyAll(roundedButton),
          textStyle: controlText,
          foregroundColor: WidgetStatePropertyAll(c.textPrimary),
          side: WidgetStatePropertyAll(BorderSide(color: c.border)),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: ButtonStyle(
          minimumSize: const WidgetStatePropertyAll(
            Size(DpDensity.minTarget, DpDensity.controlHeight),
          ),
          padding: const WidgetStatePropertyAll(
            EdgeInsets.symmetric(horizontal: DpSpacing.sm),
          ),
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          shape: WidgetStatePropertyAll(roundedButton),
          textStyle: controlText,
          foregroundColor: WidgetStatePropertyAll(c.primaryText),
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: ButtonStyle(
          minimumSize: const WidgetStatePropertyAll(
            Size(DpDensity.controlHeight, DpDensity.controlHeight),
          ),
          fixedSize: const WidgetStatePropertyAll(
            Size(DpDensity.controlHeight, DpDensity.controlHeight),
          ),
          padding: const WidgetStatePropertyAll(EdgeInsets.all(3)),
          iconSize: const WidgetStatePropertyAll(20),
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          shape: WidgetStatePropertyAll(roundedButton),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        isDense: true,
        fillColor: c.surfaceMuted,
        constraints: const BoxConstraints(minHeight: DpDensity.controlHeight),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: DpSpacing.md,
          vertical: 5,
        ),
        border: roundedInput,
        enabledBorder: roundedInput,
        focusedBorder: roundedInput.copyWith(
          borderSide: BorderSide(color: c.primaryText, width: 2),
        ),
        hintStyle: TextStyle(color: c.textFaint),
      ),
```
(`cardTheme` 이하는 그대로 — 반경은 Task 1 의 `DpRadius` 값을 기호로 받는다.)

`packages/dp_design/lib/src/a11y/dp_tap_target.dart` 3~10행:
```dart
import '../theme/dp_spacing.dart';

/// 최소 포인터 타깃(기본 24 = DpDensity.minTarget, WCAG 2.2 AA 2.5.8) + 시맨틱 라벨 보장(DESIGN §6).
/// 24 미만이 될 수 없고, 더 큰 값이 필요하면 minSize 로 올린다.
class DpTapTarget extends StatelessWidget {
  const DpTapTarget({
    super.key,
    required this.child,
    required this.onTap,
    required this.semanticLabel,
    this.minSize = DpDensity.minTarget,
  });
```

- [ ] **Step 4: 통과 확인 + 전체**

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/theme/dp_theme_v2_test.dart test/theme/dp_segmented_button_theme_test.dart test/a11y/dp_tap_target_test.dart test/theme/dp_theme_density_test.dart && "$FLUTTER" test --exclude-tags golden
cd "$WT/apps/web" && "$FLUTTER" test
cd "$WT/apps/admin" && "$FLUTTER" test
```
Expected: dp_design 전체 PASS(로컬 CRLF 1건 제외). web/admin 에서 **높이 44/52 리터럴을 핀한 테스트**가 실패할 수 있다(예: 컨트롤 크기를 `greaterThanOrEqualTo(44)` 로 단언). 그런 테스트는 기대값을 `DpDensity.minTarget`(24) 기준으로 바꾼다 — 대상 파일과 줄을 커밋 메시지에 적는다. 위젯 자체의 `BoxConstraints(minHeight: 44)`(dp_context_capsule·dp_next_action_band·dp_progress_spine·dp_chrome_bar·dp_nav_rail·dp_page_header:239·mentor_page·review_panel·sandbox_page)는 **이 PR 에서 바꾸지 않는다**(P3·P4).

- [ ] **Step 5: 커밋**

```bash
cd "$WT" && "$DART" format packages apps && git -C "$WT" add -A packages apps && git -C "$WT" commit -q -F - <<'MSG'
feat(dp_design): 30px pointer controls and a 24px minimum target in DpTheme (tokens 2.0.0)

Filled/outlined/text/icon buttons, segmented buttons and inputs take their minimum size from DpDensity
(controlHeight 30, minTarget 24) with tapTargetSize shrinkWrap; DpTapTarget defaults to DpDensity.minTarget.
Spec 2026-09-19 §5.4-1 (user decision: dense pointer density, WCAG 2.2 AA 2.5.8). Widgets that hard-code
44px stay for P3/P4.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
MSG
```

---

### Task 5: browser-ux 러너의 최소 타깃 기준 44 → 24 (계약 문서 동반)

**Files:**
- Modify: `tools/browser_ux/run.mjs:5,33`
- Modify: `docs/design/browser-ux-contract.md:23,42`

**Interfaces:**
- Consumes: Task 4 의 30px 컨트롤(러너가 CI 에서 실제 웹 빌드로 검증).
- Produces: `MIN_TARGET = 24` — CI `browser-ux` 의 `overflow-and-targets` 시나리오가 2.5.8 기준으로 판정한다.

- [ ] **Step 1: 러너 상수와 주석**

`tools/browser_ux/run.mjs` 5행 주석의 `44px 타깃` → `24px 타깃(WCAG 2.2 AA 2.5.8, 계약 2.0.0)`; 33행:
```js
const MIN_TARGET = 24; // = DpDensity.minTarget (packages/dp_design/lib/src/theme/dp_spacing.dart)
```

- [ ] **Step 2: 계약 문서**

`docs/design/browser-ux-contract.md` 23행의 `390·100% 에서 모든 \`role=button\` 이 44×44 이상` → `390·100% 에서 모든 \`role=button\` 이 24×24 이상(WCAG 2.2 AA 2.5.8; 계약 2.0.0 의 DpDensity.minTarget)`; 42행의 `러너 기준(overflow·44px·axe critical/serious)은 낮추지 않는다` → `러너 기준(overflow·24px 최소 타깃·axe critical/serious)은 낮추지 않는다. 24px 은 2026-09-19 스펙 §5.4-1 의 사용자 결정으로 44px 에서 옮긴 값이며, 그 아래로는 내리지 않는다`.

- [ ] **Step 3: 러너 단위 테스트 실행**

```bash
cd "$WT" && node --test tools/browser_ux/run.test.mjs
```
Expected: PASS(러너 테스트는 `MIN_TARGET` 을 핀하지 않는다 — 판정은 CI `browser-ux` 잡).

- [ ] **Step 4: 커밋**

```bash
git -C "$WT" add tools/browser_ux/run.mjs docs/design/browser-ux-contract.md && git -C "$WT" commit -q -F - <<'MSG'
test(browser-ux): minimum pointer target 44px -> 24px (WCAG 2.2 AA 2.5.8, tokens 2.0.0)

Follows DpDensity.minTarget; the contract document records the 2026-09-19 decision.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
MSG
```

---

### Task 6: DESIGN.md §3·§5·§6 을 계약 2.0.0 으로

**Files:**
- Modify: `DESIGN.md` §3(간격·라운드·고도 + 레이아웃 토큰 표), §5(하단 내비 문장의 44), §6(터치 타깃)

- [ ] **Step 1: §3 라운드 줄과 표를 바꾼다**

`- **라운드**: 칩 \`999\` · 버튼 \`12\` · 카드/패널 \`18\` · 입력 \`12\` · 다이얼로그 \`20\`.` →
```markdown
- **라운드(계약 2.0.0, 웹 문법)**: 칩 `4` · 버튼 `6` · 카드/패널/드롭다운 `8` · 입력 `6` · 다이얼로그/시트 `12`. (2026-09-19 스펙 §5.3 — 999/12/18/12/20 의 모바일 문법에서 옮김.)
- **밀도(계약 2.0.0)**: 컨트롤 높이 `30` · 표 행 세로 여백 `8` · 최소 포인터 타깃 `24`(`DpDensity`). 버튼·입력·세그먼트·아이콘 버튼은 `DpTheme` 이 이 값을 강제한다.
```
레이아웃 토큰 표를 다음으로:
```markdown
| 토큰 | 값 | 용도 |
|---|---|---|
| `contentMaxWidth` | 1120 | 본문 최대 폭(항상 중앙 정렬) |
| `readableMaxWidth` | 760 | 문서·상세 읽기 폭 |
| `headerHeight` | 56 | 상단 헤더 높이(P2 `DpWebShell`) |
| `railWidth` | 280 | admin 레일 폭(web 은 P2 에서 헤더로) |
| `railCollapsedWidth` | 80 | admin 접힘 레일 폭 |
| `panelRadius` | 8 | 패널 반경(=카드) |
```

- [ ] **Step 2: §5 의 하단 내비 문장**

`선택 상태를 억지로 표시하지 않으며, 안전영역과 44px 이상 터치 타깃을 유지한다.` → `선택 상태를 억지로 표시하지 않으며, 안전영역과 §6 의 최소 타깃을 유지한다. (§5 표의 web 셸 열은 S3-P2 에서 상단 헤더 문법으로 다시 쓴다.)`

- [ ] **Step 3: §6 터치 타깃**

`- **터치 타깃**: ≥44×44 (하단탭·아이콘 버튼·칩).` →
```markdown
- **포인터 타깃(계약 2.0.0)**: ≥24×24 — WCAG 2.2 AA 2.5.8. 24 미만인 타깃은 인접 타깃과의 간격(≥8px)으로 예외 조건을 만족시킨다. 컨트롤 표준 높이는 30(`DpDensity.controlHeight`). 2026-09-19 스펙 §5.4-1 의 사용자 결정으로 44×44 터치 기준에서 옮겼다; browser-ux 러너 `MIN_TARGET` 과 같은 값이다.
```

- [ ] **Step 4: 커밋**

```bash
git -C "$WT" add DESIGN.md && git -C "$WT" commit -q -F - <<'MSG'
docs(design): DESIGN.md §3/§5/§6 for token contract 2.0.0 (web radii, density, 24px targets)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
MSG
```

---

### Task 7: design-sync 재빌드 → Claude Design `Leva Design Tokens` 재업로드, NOTES 갱신

**Files:**
- Modify: `.design-sync/NOTES.md:7` (divergence 항목 뒤에 2.0.0 기록)
- 생성물(커밋하지 않음): `packages/dp_design/build/dp-tokens.css`, `ds-bundle/`

**Interfaces:**
- Consumes: Task 3 의 덤프(`--dp-token-manifest-version "2.0.0"`, `--dp-density-*`, `--dp-layout-header-height`, `--dp-color-header-*`).
- Produces: Claude Design 프로젝트 `Leva Design Tokens`(id `19a7b5ca-6f2b-4d14-b291-ac9e47a31855`)이 2.0.0 을 보여준다.

- [ ] **Step 1: 덤프와 번들**

```bash
cd "$WT/packages/dp_design" && DP_TOKEN_DUMP=build/dp-tokens.css "$FLUTTER" test test/theme/dp_semantic_tokens_dump_test.dart
grep -cE 'dp-color-header-|dp-density-|dp-layout-header-height|"2.0.0"' "$WT/packages/dp_design/build/dp-tokens.css"
cd "$WT" && py .design-sync/scripts/build_ds_bundle.py && py .design-sync/scripts/build_ds_readme.py
grep -n '2.0.0' "$WT/ds-bundle/README.md"
```
Expected: 덤프에 헤더 색 12줄(light 6 + dark 6)·밀도 3·헤더 높이 1·버전 1 → grep 개수 ≥ 17. README 가 `leva.semantic-tokens 2.0.0` 을 표기.

- [ ] **Step 2: 검증기와 업로드**

NOTES.md「Rebuild」4 단계대로: 홈 워크트리의 `.ds-sync/package-validate.mjs ./ds-bundle` 로 검증(경고는 `_ds_sync.json` 하나만) → `DesignSync` 도구로 업로드(sentinel → files → sentinel). 업로드 결과의 파일 수와 `README.md` 의 버전 문구를 기록한다.

- [ ] **Step 3: NOTES 갱신**

`.design-sync/NOTES.md` 7행(Divergence found) 뒤에 한 줄 추가:
```markdown
- **Contract 2.0.0 (2026-09-24, S3-P1)**: radii 4/6/8/6/12, density tokens (`--dp-density-control-height 30px`, `--dp-density-row-padding 8px`, `--dp-density-min-target 24px`), `--dp-layout-content-max 1120px`, `--dp-layout-header-height 56px`, `rail*` → `header*`. The homepage mirror (`assets/tokens.css`) follows in its own PR; until it lands, the landing is on 1.1.0 by design and its contract test pins that.
```

- [ ] **Step 4: 커밋(생성물 제외)**

```bash
git -C "$WT" status --porcelain | grep -E 'ds-bundle|build/dp-tokens' && echo "generated files must not be committed" || true
git -C "$WT" add .design-sync/NOTES.md && git -C "$WT" commit -q -F - <<'MSG'
docs(design-sync): record token contract 2.0.0 and the Leva Design Tokens re-sync

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
MSG
```
(`ds-bundle/`·`build/` 가 `git status` 에 보이면 `.gitignore` 에 있지 않다는 뜻 — 커밋하지 말고 그대로 둔다.)

---

### Task 8: develop PR — CI 게이트 5종, 머지

- [ ] **Step 1: 로컬 최종 검증(CI 와 같은 명령)**

```bash
cd "$WT" && "$DART" format --set-exit-if-changed . && "$DART" run melos run analyze && "$DART" run melos run test
```
Expected: format 변경 0 · analyze 경고 0 · test PASS(로컬 CRLF 1건은 CI 에서 통과).

- [ ] **Step 2: push + PR**

```bash
git -C "$WT" push -u origin feat/s3-p1-semantic-tokens-2-0-0
gh pr create -R DevPathAi/devpath-frontend --base develop --head feat/s3-p1-semantic-tokens-2-0-0 --title "feat(dp_design): semantic token contract 2.0.0 — web radii, pointer density, header tokens (S3-P1)" --body-file <(cat <<'BODY'
## S3-P1 (spec documents `specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` §5.3·§5.4·§7 P1)
- `DpRadius` 4/6/8/6/12 · new `DpDensity` 30/8/24 · `AppTokens.standard` 1120/760/280/80/8 + `headerHeight` 56
- `rail*` → `header*` colour tokens (values unchanged) · manifest **2.0.0** with `--dp-density-*`, `--dp-color-header-*`, `--dp-layout-header-height`
- `DpTheme`: 30px controls, `shrinkWrap` tap targets, dense inputs; `DpTapTarget` default 24 · browser-ux `MIN_TARGET` 24 · DESIGN.md §3/§5/§6
- Claude Design `Leva Design Tokens` re-synced to 2.0.0; homepage mirror follows in devpath-home-page (separate PR, user decision on landing visuals)

## Expected CI
analyze-test · browser-ux (24px targets) · perf-gate (no transfer change) · web-image-config-contract · ET13 produce-atomic-pair — **all ET13 visual fixtures change** (radii/density); baseline re-approval is the P5 human step before the release, not this PR.

## Not in this PR
Shell replacement (P2), widget web grammar / FAB removal (P3), screen groups (P4), baselines (P5). Admin keeps `DpAppShell`/`DpNavRail` on the renamed tokens.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
BODY
)
```

- [ ] **Step 3: CI 대기와 판정**

```bash
gh pr checks --watch --fail-fast -R DevPathAi/devpath-frontend "$(gh pr view --json number -q .number -R DevPathAi/devpath-frontend feat/s3-p1-semantic-tokens-2-0-0)"
```
Expected: analyze-test·browser-ux·perf-gate·web-image-config-contract·ET13 잡 전부 success(약 25분). `browser-ux` 가 `small targets` 로 실패하면 Task 4 의 위젯이 24 미만으로 렌더된 것 — 실패 보고서(아티팩트 `leva-browser-ux-*`)의 `small_targets` 라벨을 보고 **그 위젯의 최소 크기**를 `DpDensity.minTarget` 으로 올린다(러너 기준을 낮추지 않는다).

- [ ] **Step 4: 머지(merge commit) + 정리**

```bash
gh pr merge -R DevPathAi/devpath-frontend --merge --delete-branch "$(gh pr view --json number -q .number -R DevPathAi/devpath-frontend feat/s3-p1-semantic-tokens-2-0-0)"
git -C /d/workspace/dpa/devpath-frontend fetch -q origin develop && git -C /d/workspace/dpa/devpath-frontend log -1 --format='%h %s' origin/develop
git -C /d/workspace/dpa/devpath-frontend worktree remove --force "D:/workspace/dpa/.worktrees/frontend-s3p1-20260924"
```

---

### Task 9: 홈 미러 — `assets/tokens.css` 를 2.0.0 으로 (별도 레포 PR, **사용자 결정 뒤**)

> **결정이 필요하다(계획 검토 때 질문).** 랜딩은 미러의 `--dp-radius-*`(39곳)·`--dp-color-rail-*`(22곳)·`--dp-layout-content-max`(4곳)를 실제로 쓴다. 미러를 2.0.0 값으로 맞추면 **랜딩의 카드·버튼 반경과 본문 폭이 바뀌고**(스펙 §3 은 랜딩 디자인을 범위 밖으로 둔다) 홈 시각 기준선(320/600/840/1240)을 다시 찍어 사람이 재승인해야 한다. 아래는 **A안(미러가 계약을 따른다 — 스펙 §7 P1·`.design-sync/NOTES.md` 의 "divergence = 결함" 관점)** 이다. **B안**은 미러를 1.1.0 에 동결하고 홈 `DESIGN.md` 4행에 "2026-09-24: 앱 계약은 2.0.0, 랜딩 미러는 랜딩 재설계 결정까지 1.1.0 동결" 을 적는 것(코드 변경 없음, 이 Task 는 건너뜀).

**Files (A안):**
- Modify: `devpath-home-page` `assets/tokens.css`, `index.html`(15곳), `assets/styles.css`(5곳), `assets/public.css`(2곳), `tests/design-token-contract.test.js`, `DESIGN.md:4`
- 워크트리: `D:/workspace/dpa/.worktrees/home-s3p1-mirror-20260924`(`origin/develop` 에서 `feat/tokens-mirror-2-0-0`)

**Interfaces:**
- Consumes: Task 3·7 의 덤프 `packages/dp_design/build/dp-tokens.css`(값의 원천 — 손으로 옮기되 값은 여기서 복사).
- Produces: 랜딩 `:root`/`[data-theme="dark"]` 가 2.0.0 키 집합(색 33 + 간격 7 + 반경 5 + 밀도 3 + 모션 5 + 타이포 12 + 상태 24 + 레이아웃 8 + 브레이크포인트 3 + 버전 1)을 갖는다.

- [ ] **Step 1: 실패하는 테스트 — 계약 테스트를 2.0.0 으로**

`tests/design-token-contract.test.js`:
- `colors` 맵의 `--dp-color-rail-*` 6 키를 `--dp-color-header-*` 로 (값은 그대로).
- `describe('Landing/App semantic token contract 1.1.0'` → `2.0.0`.
- 두 번째 `it` 의 기대 객체를 다음 값으로: `'--dp-token-manifest-version': '"2.0.0"'`, `'--dp-radius-chip': '4px'`, `'--dp-radius-button': '6px'`, `'--dp-radius-panel': '8px'`, `'--dp-radius-input': '6px'`, `'--dp-radius-dialog': '12px'`, `'--dp-density-control-height': '30px'`, `'--dp-density-row-padding': '8px'`, `'--dp-density-min-target': '24px'`, `'--dp-layout-content-max': '1120px'`, `'--dp-layout-header-height': '56px'`(나머지 간격·모션·레일 폭·브레이크포인트는 그대로).
- 마지막 `it` 의 `dimensions` 에 `...['control-height', 'row-padding', 'min-target'].map((name) => \`--dp-density-${name}\`)` 를, `layout` 에 `'--dp-layout-header-height'` 를 추가.
- 새 `it` 추가(Review Focus 4):
```js
  it('reads the dark block through the exact selector the app dump does not emit', () => {
    const darkOnly = declarations('[data-theme="dark"]');
    expect(darkOnly['--dp-color-header-bg']).toBe('#090B10');
    expect(darkOnly['--dp-color-header-text']).toBe('#F4F5F8');
    expect(css).not.toMatch(/--dp-color-rail-/);
  });
```

- [ ] **Step 2: 실패 확인**

```bash
cd "D:/workspace/dpa/.worktrees/home-s3p1-mirror-20260924" && npm ci --ignore-scripts --no-audit --no-fund && npx vitest run tests/design-token-contract.test.js
```
Expected: FAIL(rail 키·1.1.0·옛 반경).

- [ ] **Step 3: 미러와 소비자 갱신**

`assets/tokens.css`: 3행 `Contract: DpSemanticTokenManifest 1.1.0` → `2.0.0`; `--dp-token-manifest-version: "2.0.0";`; 라이트·다크 블록의 `--dp-color-rail-(bg|text|muted|faint|active|border)` → `--dp-color-header-…`(값 유지); `--dp-radius-chip: 4px; --dp-radius-button: 6px; --dp-radius-panel: 8px; --dp-radius-input: 6px; --dp-radius-dialog: 12px;`; 반경 블록 뒤에
```css
  /* Density — DpDensity (contract 2.0.0): pointer controls 30px, table row padding 8px, minimum target 24px (WCAG 2.2 AA 2.5.8). */
  --dp-density-control-height: 30px;
  --dp-density-row-padding: 8px;
  --dp-density-min-target: 24px;
```
레이아웃 블록: `--dp-layout-content-max: 1120px;` 와 `--dp-layout-header-height: 56px;`(readable 760, rail 280/80, 브레이크포인트 유지). **선택자는 `:root {` 와 `[data-theme="dark"] {` 를 그대로 둔다**(덤프의 `, .dp-theme-dark` 를 붙이지 않는다).

소비자 이름 변경:
```bash
cd "D:/workspace/dpa/.worktrees/home-s3p1-mirror-20260924" && sed -i -E 's/--dp-color-rail-(bg|text|muted|faint|active|border)/--dp-color-header-\1/g' index.html assets/styles.css assets/public.css && git grep -c 'dp-color-rail' -- . ; echo "remaining rc=$?"
```
Expected: `remaining rc=1`(매치 0).

`DESIGN.md` 4행 `DpSemanticTokenManifest 1.1.0` → `DpSemanticTokenManifest 2.0.0`.

- [ ] **Step 4: 통과 확인 + 빌드**

```bash
cd "D:/workspace/dpa/.worktrees/home-s3p1-mirror-20260924" && npm test && npm run build
```
Expected: vitest 전부 PASS, 빌드 성공(`dist/`).

- [ ] **Step 5: 시각 기준선 재기록(핀 이미지) — 사람 재승인 대상**

`docs/visual-a11y-evidence.md`「Baseline updates」대로 `baseline_policy.platform` 의 정확한 이미지 안에서:
```bash
cd "D:/workspace/dpa/.worktrees/home-s3p1-mirror-20260924" && npm run visual:evidence:docker && npm run visual:baseline:update && npm run visual:contracts && npm run visual:evidence:validate:diagnostic
```
Expected: 4 폭 × 라이트의 PNG 가 바뀌고(반경·폭), 상태는 `diagnostic_pending_review`(승인 전 정상). 커밋한 상태로 `npm test`·`visual:contracts` 를 한 번 더 돈다(홈 규칙).

- [ ] **Step 6: 커밋·PR(develop)**

```bash
cd "D:/workspace/dpa/.worktrees/home-s3p1-mirror-20260924" && git add -A && git commit -q -F - <<'MSG'
feat(tokens): mirror the app's semantic token contract 2.0.0

Radii 4/6/8/6/12, density tokens, content max 1120, header height 56, rail-* -> header-* (values unchanged).
Landing visuals change with the radii and width; visual baselines re-recorded in the pinned image and await
human approval. Source: devpath-frontend packages/dp_design (S3-P1).

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
MSG
git push -u origin feat/tokens-mirror-2-0-0 && gh pr create -R DevPathAi/devpath-home-page --base develop --head feat/tokens-mirror-2-0-0 --fill
```
Expected: 홈 CI 녹색 → 머지 후 `develop→master` 릴리스와 gitops landing-last 는 다음 릴리스 캠페인에서(홈 배포 prior = `6f7a7e2b…`).

---

## Self-Review

- **Spec coverage**: §5.3 반경(T1·T4)·밀도(T1·T4·T5·T6)·본문 폭(T1)·푸터/헤더 구조(P2 — 범위 밖, `headerHeight` 만 선행)·색·폰트 유지(제약) · §5.4-1 24px 기준 이동 + DESIGN §6 + browser-ux(T4·T5·T6) · §5.4-2 `rail*→header*` 값 유지(T2) · §7 P1 "토큰 2.0.0 + 홈 미러 + Claude Design"(T3·T7·T9) · §8 게이트 5종(T8) · §10 admin 회귀는 P1 PR 에서(T2·T4 admin 테스트, T8 CI).
- **Placeholder scan**: 모든 코드 단계에 실제 코드·명령·기대값이 있다. "다른 실패가 나오면" 절은 판정 규칙(기호로 바꾸기, 러너 기준 불변)을 명시한다.
- **Type consistency**: `DpDensity.controlHeight/rowPadding/minTarget`, `AppTokens.headerHeight`, `DpSemanticTokenKind.density`, `DpSemanticTokenUsage.interactionDensity`, `DpSemanticTokenManifest.density`, `header{Bg,Text,Muted,Faint,Active,Border}` — T1~T4·T7·T9 에서 같은 이름.
- **Review Focus**: 1→T4 세 번째 테스트(간격 8) · 2→T4 TextButton 한 줄 테스트 · 3→T1 copyWith/lerp 테스트 · 4→T9 Step 1 새 `it` · 5→T2 대비 테스트 유지.
