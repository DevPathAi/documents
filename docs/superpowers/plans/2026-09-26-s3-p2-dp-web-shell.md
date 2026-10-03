# S3-P2 — `DpWebShell` 신설(상단 헤더·햄버거·계정 메뉴·푸터) → web `AppShellView` 교체 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `apps/web` 의 셸을 「다크 레일 + 크롬바 + (compact) 하단 내비」에서 **「상단 헤더 + 중앙 본문 + 푸터」** 로 바꾼다. 새 셸 위젯군은 `packages/dp_design` 에 신설하고, `apps/admin` 이 쓰는 `DpAppShell`·`DpNavRail`·`DpChromeBar`·`DpMobileNavigation` 은 **그대로 둔다**.

**Architecture:** dp_design 에 라우팅 비의존 위젯 5종을 새로 만든다 — `DpMenuButton`(웹 시맨틱 focus 함정을 이미 해결한 `MenuAnchor` 패턴의 재사용 가능 판), `DpWebHeader`(브랜드·주 메뉴·커뮤니티 드롭다운·검색 트리거·계정 메뉴, compact 에서는 햄버거 + 인라인 접힘 메뉴), `DpWebFooter`, `DpBreadcrumb`(본문 상단용), `DpWebShell`(셋을 세로로 합치고 본문을 `contentMaxWidth` 로 중앙 정렬). `apps/web` 은 목적지 모델을 index 기반에서 **id(경로) 기반**으로 바꾸고 `AppShellView` 가 `DpAppShell` 대신 `DpWebShell` 을 쓴다. 기존 위치 해석기 `shellDestinationIndexFor` 는 이미 테스트가 두터우므로 **그대로 두고** 얇은 id 매핑만 얹는다.

**Tech Stack:** Flutter **3.44.1**(CI 핀, 로컬 `D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin/flutter.bat`) · Dart pub workspace + melos 7(`dart run melos …`) · Node 20(browser-ux 러너) · GitHub Actions(`analyze-test` · `browser-ux` · `perf-gate` · `web-image-config-contract` · ET13 `produce-atomic-pair`).

**Spec:** documents `docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` §5.3 · §5.4 · §7(P2) · §8 · §10, 시안 https://claude.ai/artifact/DWi8kMV6QcAzBEQwbrNPNd (Version 2). 앞 단계 = `plans/2026-09-24-s3-p1-semantic-tokens-2-0-0.md`(계약 2.0.0, merged `17ce8a2`).

## Global Constraints

- **시안이 시각 계약의 정본이다.** 시안에 없는 화면 요소를 즉흥으로 만들지 않는다(스펙 §7 원칙). 이 계획이 시안에서 그대로 옮긴 값:
  - 헤더 높이 **56**(`AppTokens.headerHeight`, 계약 2.0.0 에 이미 있다) · 어두운 면(`headerBg`/`headerBorder`) · 본문 최대폭 **1120**(`AppTokens.contentMaxWidth`) · 본문 패딩 24(compact 16).
  - 주 메뉴 = **오늘 · 학습 경로 · AI 멘토 · 커뮤니티 ▾**(드롭다운 = 자유게시판 · Q/A · 피드백). 항목 높이 `DpDensity.controlHeight`(30), 반경 `DpRadius.button`(6), 평시 `headerMuted`, hover `headerActive` 배경 + `headerText`, 현재 항목은 `headerText` + 하단 2px `primary` 밑줄(반경 0).
  - compact(≤ **container 720px**, 시안 `@container (max-width:720px)`) 에서 주 메뉴와 도구가 사라지고 **햄버거**가 나온다. 펼치면 헤더 **아래로 인라인 확장**(overlay·drawer·focus trap 금지) — 내용은 시안 `.mnav` 그대로: `오늘 / 학습 경로 / AI 멘토 / [커뮤니티] 자유게시판·Q/A·피드백 / [계정] 마이페이지·설정·로그아웃`.
  - 푸터 = `© 레바 · 사업자등록번호 796-76-00732` + 링크 4종 `이용약관 · 개인정보 처리방침 · 오류 신고·문의 · 업데이트 소식`. 상단 경계선, `surface` 배경, 12px, 안쪽은 1120 중앙 정렬.
  - 브레드크럼은 **본문 상단**(시안 `.crumb`), 크롬바가 아니다. 구분자는 `›`.
- **사용자 결정(2026-09-26, 이 계획 작성 중 확인 관문)**:
  1. **푸터는 셸 하단 고정**이다 — `DpWebShell` 이 `Column[header, Expanded(body), footer]` 로 그린다. 화면 수정 0. 시안의 「내용 끝」 거동과 다르고 compact 에서도 약 45px 이 항상 붙는다는 것을 알고 고른 선택이다(스펙 §5.3 「하단 고정 요소 없음」은 **하단 내비**를 가리키는 문장으로 읽는다). 이 판단은 PR 설명과 실행 원장에 적는다.
  2. **계정 버튼은 아이콘 + ▾ 만**이다. 시안의 아바타 이니셜·이름은 P4(계정 화면군)에서 같은 컨트롤러로 붙인다 — P2 는 셸에 데이터 의존을 새로 만들지 않는다.
- **토큰 밖 수치는 만들지 않는다.** 시안의 `gap:20px`·`gap:2px`·`padding:6px`·아바타 26px 은 `DpSpacing` 에 없다 → 각각 `DpSpacing.xl`(24) · `DpSpacing.xs`(4) · `DpSpacing.sm`(8) 로 반올림하고 아바타는 쓰지 않는다(위 결정 2). DESIGN.md §3 의 「간격은 `DpSpacing` 에서만」이 시안의 임의 픽셀보다 우선한다. 시안의 어두운 검색 배경 `#1B1E29` 도 토큰이 아니다 → **`headerActive`** 를 쓴다(어두운 헤더 위의 표면 토큰). 레이아웃 폭(검색 200px)은 토큰 대상이 아니다(`DpChromeBar` 의 `maxWidth: 300` 전례).
- **최소 타깃은 24**(`DpDensity.minTarget`, 계약 2.0.0 · WCAG 2.2 AA 2.5.8). 44 로 되돌리지 않는다. 헤더·접힘 메뉴·푸터의 모든 누를 수 있는 요소는 **시맨틱 박스**가 24 이상이어야 한다 — `tester.getSize` 가 아니라 `tester.getSemantics(...).rect` 로 잰다(아래 함정 3).
- **Flutter 웹 시맨틱 함정 5건을 먼저 대조한다**(2026-09-17 실측, 단위 테스트는 전부 통과하는데 `browser-ux` 만 잡는다):
  1. `Semantics(header:true, button:true)` 한 노드 → 웹이 `<h2>툴팁\n제목</h2>` 로 낸다(heading 오염 + button 역할 소실).
  2. 헤더와 버튼이 형제여도 헤더 표식이 위로 합쳐지면 `<h2>` 가 아예 안 나온다 → `Semantics(container: true, header: true)`.
  3. `IconButton` 위젯 크기는 48인데 웹 시맨틱 박스는 40 → 필요하면 `IconButton.styleFrom(minimumSize: …)`.
  4. Flutter 웹은 `MenuItemButton` 을 `role=menuitem` 이 아니라 **button** 으로 낸다(러너의 셀렉터가 `getByRole('button')` 인 이유).
  5. `MenuAnchor` 를 Enter 로 연 뒤 웹에서 Escape 가 안 먹고 DOM focus 가 body 로 빠진다. **`childFocusNode` 만으로는 안 된다(CI 실측 FAIL)** → 열 때 `addPostFrameCallback` 으로 첫 `MenuItemButton` 의 `focusNode` 에 `requestFocus` + `childFocusNode` 로 닫을 때 복귀. 검증된 구현이 `packages/dp_design/lib/src/layout/dp_page_header.dart` 의 `_TitleMenuState` 에 있다 — Task 1 은 그것을 **그대로** 일반화한다.
- **`apps/admin` 을 바꾸지 않는다**(스펙 §10). 실측: `admin_shell.dart` 는 `compactDestinations` 를 넘기지 않고 `destinations` 폴백으로 `DpMobileNavigation` 을 쓴다(`apps/admin/test/features/shell/admin_shell_view_test.dart:44` 가 단언). 따라서 **`DpMobileNavigation` 은 남긴다**. web 만 쓰던 `compactDestinations`·`compactSelectedIndex`·`onCompactSelect` 세 파라미터만 제거한다(Task 8).
- **이 PR 이 하지 않는 것**: 공용 위젯 웹화(`DpListRow`·`DpPageHeader.titleMenu` 제거·카드→목록·FAB 제거 = P3) · 화면군 개편(P4) · ET13/perf/골든 기준선 재기록(P5). 화면 파일은 건드리지 않는다.
- **ET13 시각 기준선은 이 PR 로 전부 달라진다** — 재승인은 P5(사람 단계)이고 develop PR 의 `produce-atomic-pair` 는 증거를 만들기만 한다(스펙 §9). PR 설명에 적는다.
- **로컬 검증은 `analyze` · 단위 테스트까지.** 웹 빌드·Playwright(`browser-ux`)·perf 는 CI 가 판정한다(스펙 §7 원칙). `browser-ux` 기대값은 **실측 후에만** 갱신한다(`tools/browser_ux/expectations.json` 의 `notes`, `docs/design/browser-ux-contract.md` §기대값 갱신 규칙).
- **브랜치 흐름**: `origin/develop` 에서 `feat/s3-p2-dp-web-shell` → develop PR → CI 녹색 → merge commit. `main` 직접 push 금지. 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.
- **작업 위치**: 워크트리 `D:/workspace/dpa/.worktrees/frontend-s3p2-20260926`(아래 `WT`). 모든 git·파일 명령은 절대경로 또는 `git -C "$WT"`. Windows: Flutter 는 `D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin/flutter.bat` 절대경로만(Git Bash PATH 가 `D:/` 접두를 무시해 다른 버전을 잡는다) · `dart format` 은 워크스페이스 루트에서 · `packages/dp_design/test/theme/dp_code_font_test.dart` 1건은 CRLF 체크아웃에서 실패할 수 있다(CI 통과, 무시).

## Review Focus

1. **접힌 메뉴를 열어 둔 채 폭이 넓어짐** — 390 에서 햄버거를 펼치고 회전(또는 창 확대)하면 데스크톱 메뉴와 접힘 메뉴가 **둘 다** 보이고 접힘 메뉴를 닫을 버튼이 사라진다. Task 2 가 「compact 가 아니게 되면 접힘 상태가 자동으로 false 로 돌아간다」를 단언한다.
2. **드롭다운이 열린 채 다른 목적지로 이동** — 커뮤니티 ▾ 를 열고 항목을 고르면 라우트가 바뀌는데 메뉴가 닫히지 않으면 새 화면 위에 떠 있는다. Task 1 이 「항목을 누르면 컨트롤러가 닫힌다」를, Task 2 가 「`onSelect` 는 닫힌 뒤에 호출된다」를 단언한다.
3. **목적지에 없는 위치(`/settings`·`/mypage`·`/content/:id`·`/sandbox`)** — 헤더가 엉뚱한 항목에 밑줄을 그으면 셸 안 두 위치 표시(밑줄 ↔ 브레드크럼)가 서로 모순된다. 기존 레일이 겪은 회귀다. Task 6 이 「매칭 실패 시 `selectedId` 는 null 이고 어떤 항목에도 밑줄이 없다」를 단언한다.
4. **200% 텍스트 배율에서 56px 헤더** — 라벨이 커지면 고정 높이 헤더에서 잘리거나 `RenderFlex` 오버플로가 난다(`browser-ux` 의 `overflow-and-targets` 가 4폭 × 100/200% 로 돈다). Task 2 가 「폭 390·`textScaleFactor` 2.0 에서 헤더가 오버플로하지 않는다」를, Task 3 이 푸터 `Wrap` 에 대해 같은 것을 단언한다.
5. **푸터 링크의 시맨틱 박스가 24 미만** — 12px 글자에 패딩이 없으면 높이가 약 19px 이라 2.5.8 을 깬다(위젯 크기가 아니라 시맨틱 박스로 재야 드러난다 — 함정 3). Task 3 이 네 링크 전부 `getSemantics(...).rect.height >= DpDensity.minTarget` 을 단언한다.

---

### Task 1: `DpMenuButton` — 웹에서 실제로 닫히는 메뉴 버튼

`_TitleMenuState`(`dp_page_header.dart`)가 이미 푼 함정 5 의 해법을 재사용 가능한 위젯으로 뽑는다. 헤더의 커뮤니티 드롭다운·계정 메뉴가 같은 것을 쓴다.

**Files:**
- Create: `packages/dp_design/lib/src/shell/dp_menu_button.dart`
- Create: `packages/dp_design/test/shell/dp_menu_button_test.dart`
- Modify: `packages/dp_design/lib/dp_design.dart` (배럴에 `export 'src/shell/dp_menu_button.dart';` 추가 — 기존 `dp_command_palette.dart` 줄 다음)

**Interfaces:**
- Consumes: 없음(dp_design 내부 토큰만).
- Produces:
  - `typedef DpMenuEntry = ({String label, VoidCallback? onSelect});`
  - `class DpMenuButton extends StatefulWidget` — 생성자 `const DpMenuButton({super.key, required List<DpMenuEntry> entries, required Widget Function(BuildContext context, FocusNode buttonFocus, VoidCallback toggle, bool isOpen) builder})`.
  - Task 2 가 이 두 이름을 쓴다.

- [ ] **Step 1: 워크트리·브랜치·부트스트랩**

```bash
cd /d/workspace/dpa/devpath-frontend && git fetch -q origin develop
git -C /d/workspace/dpa/devpath-frontend worktree add "D:/workspace/dpa/.worktrees/frontend-s3p2-20260926" -b feat/s3-p2-dp-web-shell origin/develop
WT="D:/workspace/dpa/.worktrees/frontend-s3p2-20260926"
FLUTTER="D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin/flutter.bat"
DART="D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin/dart.bat"
cd "$WT" && "$DART" run melos bootstrap --enforce-lockfile
```

Expected: `melos bootstrap` 성공, lockfile 변화 없음. `git -C "$WT" status --porcelain` 이 빈 출력.

- [ ] **Step 2: 실패하는 테스트 작성**

`packages/dp_design/test/shell/dp_menu_button_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host({required List<DpMenuEntry> entries}) => MaterialApp(
  theme: DpTheme.light(),
  home: Scaffold(
    body: DpMenuButton(
      entries: entries,
      builder: (context, buttonFocus, toggle, isOpen) => TextButton(
        key: const ValueKey('opener'),
        focusNode: buttonFocus,
        onPressed: toggle,
        child: Text(isOpen ? '열림' : '닫힘'),
      ),
    ),
  ),
);

void main() {
  testWidgets('열면 첫 항목으로 focus 가 간다 — 웹에서 Escape 가 닿으려면 필요하다', (tester) async {
    await tester.pumpWidget(
      _host(entries: [(label: '첫째', onSelect: () {}), (label: '둘째', onSelect: () {})]),
    );

    await tester.tap(find.byKey(const ValueKey('opener')));
    await tester.pumpAndSettle();

    expect(find.text('첫째'), findsOneWidget);
    expect(
      FocusManager.instance.primaryFocus?.debugLabel,
      'dp-menu-button-first-item',
      reason: '첫 항목에 focus 가 없으면 웹에서 DOM focus 가 body 로 빠져 Escape 가 안 먹는다',
    );
  });

  testWidgets('항목을 고르면 콜백이 불리고 메뉴가 닫힌다', (tester) async {
    var picked = 0;
    await tester.pumpWidget(
      _host(entries: [(label: '첫째', onSelect: () => picked++)]),
    );

    await tester.tap(find.byKey(const ValueKey('opener')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('첫째'));
    await tester.pumpAndSettle();

    expect(picked, 1);
    expect(find.text('첫째'), findsNothing, reason: '메뉴가 열린 채 남으면 다음 화면 위에 떠 있는다');
  });

  testWidgets('열린 상태는 builder 에 전달된다', (tester) async {
    await tester.pumpWidget(_host(entries: [(label: '첫째', onSelect: () {})]));

    expect(find.text('닫힘'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('opener')));
    await tester.pumpAndSettle();
    expect(find.text('열림'), findsOneWidget);
  });

  testWidgets('한 번 더 누르면 닫힌다', (tester) async {
    await tester.pumpWidget(_host(entries: [(label: '첫째', onSelect: () {})]));

    await tester.tap(find.byKey(const ValueKey('opener')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('opener')));
    await tester.pumpAndSettle();

    expect(find.text('첫째'), findsNothing);
  });
}
```

- [ ] **Step 3: 실패 확인**

```bash
WT="D:/workspace/dpa/.worktrees/frontend-s3p2-20260926"
FLUTTER="D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin/flutter.bat"
cd "$WT/packages/dp_design" && "$FLUTTER" test test/shell/dp_menu_button_test.dart
```

Expected: 컴파일 실패 — `Undefined name 'DpMenuButton'` / `DpMenuEntry`.

- [ ] **Step 4: 구현**

`packages/dp_design/lib/src/shell/dp_menu_button.dart`:

```dart
import 'package:flutter/material.dart';

/// 메뉴 항목. [onSelect] 가 null 이면 비활성.
typedef DpMenuEntry = ({String label, VoidCallback? onSelect});

/// 웹에서 **실제로 닫히는** 메뉴 버튼.
///
/// `MenuAnchor` 를 그냥 쓰면 Flutter 웹(시맨틱스 on)에서 Enter 로 연 뒤 Escape 가
/// 먹지 않고 DOM focus 가 body 로 빠진다. `childFocusNode` 만으로는 해결되지
/// 않는다(2026-09-17 CI 실측 FAIL). 열 때 첫 항목으로 focus 를 옮겨야
/// 한다(WAI-ARIA 메뉴 버튼 관례). 이 위젯은 그 조합을 한 곳에 가둔다 —
/// 새 메뉴를 만들 때 `MenuAnchor` 를 직접 쓰지 말고 이것을 쓴다.
class DpMenuButton extends StatefulWidget {
  const DpMenuButton({super.key, required this.entries, required this.builder});

  final List<DpMenuEntry> entries;

  /// [buttonFocus] 를 여는 위젯의 `focusNode` 로 넘겨야 닫을 때 focus 가 돌아온다.
  final Widget Function(
    BuildContext context,
    FocusNode buttonFocus,
    VoidCallback toggle,
    bool isOpen,
  )
  builder;

  @override
  State<DpMenuButton> createState() => _DpMenuButtonState();
}

class _DpMenuButtonState extends State<DpMenuButton> {
  final _buttonFocus = FocusNode(debugLabel: 'dp-menu-button');
  final _firstItemFocus = FocusNode(debugLabel: 'dp-menu-button-first-item');
  final _controller = MenuController();
  bool _open = false;

  @override
  void dispose() {
    _buttonFocus.dispose();
    _firstItemFocus.dispose();
    super.dispose();
  }

  void _toggle() {
    if (_controller.isOpen) {
      _controller.close();
      return;
    }
    _controller.open();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && _controller.isOpen) _firstItemFocus.requestFocus();
    });
  }

  void _select(DpMenuEntry entry) {
    // 먼저 닫는다 — 라우트가 바뀐 뒤에 닫으면 메뉴가 새 화면 위에 남는다.
    _controller.close();
    entry.onSelect?.call();
  }

  @override
  Widget build(BuildContext context) {
    return MenuAnchor(
      controller: _controller,
      childFocusNode: _buttonFocus,
      onOpen: () => setState(() => _open = true),
      onClose: () => setState(() => _open = false),
      menuChildren: [
        for (final (index, entry) in widget.entries.indexed)
          MenuItemButton(
            focusNode: index == 0 ? _firstItemFocus : null,
            onPressed: entry.onSelect == null ? null : () => _select(entry),
            child: Text(entry.label),
          ),
      ],
      builder: (context, _, _) =>
          widget.builder(context, _buttonFocus, _toggle, _open),
    );
  }
}
```

- [ ] **Step 5: 통과 확인**

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/shell/dp_menu_button_test.dart
```

Expected: 4 tests passed.

- [ ] **Step 6: 배럴 추가 후 전체 dp_design 테스트**

`packages/dp_design/lib/dp_design.dart` 의 `export 'src/shell/dp_command_palette.dart';` 다음 줄에 `export 'src/shell/dp_menu_button.dart';` 를 넣는다.

```bash
cd "$WT" && "$DART" run melos run analyze && cd "$WT/packages/dp_design" && "$FLUTTER" test
```

Expected: analyze 무이슈, dp_design 기존 테스트 전부 + 새 4건 통과.

- [ ] **Step 7: 커밋**

```bash
git -C "$WT" add packages/dp_design/lib/src/shell/dp_menu_button.dart packages/dp_design/lib/dp_design.dart packages/dp_design/test/shell/dp_menu_button_test.dart
git -C "$WT" commit -m "$(cat <<'EOF'
feat(dp_design): DpMenuButton — 웹에서 실제로 닫히는 메뉴 버튼

dp_page_header 의 _TitleMenuState 가 이미 푼 MenuAnchor 웹 focus 함정을
재사용 가능한 위젯으로 뽑는다. 새 헤더의 커뮤니티 드롭다운과 계정 메뉴가 쓴다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `DpWebHeader` — 상단 헤더 + 햄버거 + 인라인 접힘 메뉴

**Files:**
- Create: `packages/dp_design/lib/src/shell/dp_web_nav_item.dart`
- Create: `packages/dp_design/lib/src/shell/dp_web_header.dart`
- Create: `packages/dp_design/test/shell/dp_web_header_test.dart`
- Modify: `packages/dp_design/lib/dp_design.dart` (두 줄 추가)

**Interfaces:**
- Consumes: Task 1 의 `DpMenuButton`·`DpMenuEntry`.
- Produces:
  - `class DpWebNavItem { const DpWebNavItem({required String id, required String label, List<DpWebNavItem> children = const []}); }`
  - `class DpWebHeader extends StatefulWidget` — `const DpWebHeader({super.key, required DpRailBrand brand, required List<DpWebNavItem> items, required String? selectedId, required ValueChanged<String> onSelect, required List<DpMenuEntry> accountEntries, VoidCallback? onSearchTap})`.
  - `DpWebHeader.compactBreakpoint` = `720.0`.
  - Task 4·6 이 이 이름을 쓴다.

- [ ] **Step 1: 실패하는 테스트 작성**

`packages/dp_design/test/shell/dp_web_header_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const _items = [
  DpWebNavItem(id: '/dashboard', label: '오늘'),
  DpWebNavItem(id: '/path', label: '학습 경로'),
  DpWebNavItem(
    id: '/community',
    label: '커뮤니티',
    children: [
      DpWebNavItem(id: '/community?board=FREE', label: '자유게시판'),
      DpWebNavItem(id: '/community?board=QNA', label: 'Q/A'),
    ],
  ),
];

void _setWidth(WidgetTester tester, double w) {
  tester.view.physicalSize = Size(w, 900);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
}

Widget _host({
  String? selectedId,
  void Function(String)? onSelect,
  double? textScale,
}) => MaterialApp(
  theme: DpTheme.light(),
  builder: (context, child) => textScale == null
      ? child!
      : MediaQuery.withClampedTextScaling(
          minScaleFactor: textScale,
          maxScaleFactor: textScale,
          child: child!,
        ),
  home: Scaffold(
    body: DpWebHeader(
      brand: DpRailBrand(mark: const DpBrandMark(size: 24), wordmark: 'Leva'),
      items: _items,
      selectedId: selectedId,
      onSelect: onSelect ?? (_) {},
      accountEntries: [
        (label: '마이페이지', onSelect: () {}),
        (label: '설정', onSelect: () {}),
        (label: '로그아웃', onSelect: () {}),
      ],
      onSearchTap: () {},
    ),
  ),
);

void main() {
  testWidgets('넓은 폭: 주 메뉴가 보이고 햄버거는 없다', (tester) async {
    _setWidth(tester, 1240);
    await tester.pumpWidget(_host());

    expect(find.text('오늘'), findsOneWidget);
    expect(find.text('학습 경로'), findsOneWidget);
    expect(find.text('커뮤니티'), findsOneWidget);
    expect(find.byKey(const ValueKey('web-header-burger')), findsNothing);
  });

  testWidgets('헤더 높이는 계약의 headerHeight(56)다', (tester) async {
    _setWidth(tester, 1240);
    await tester.pumpWidget(_host());

    final bar = tester.getSize(find.byKey(const ValueKey('web-header-bar')));
    expect(bar.height, AppTokens.standard.headerHeight);
  });

  testWidgets('compact: 주 메뉴·검색은 감추고 햄버거만 남는다', (tester) async {
    _setWidth(tester, 390);
    await tester.pumpWidget(_host());

    expect(find.byKey(const ValueKey('web-header-burger')), findsOneWidget);
    expect(find.byKey(const ValueKey('web-header-search')), findsNothing);
    expect(find.byKey(const ValueKey('web-header-nav')), findsNothing);
  });

  testWidgets('compact: 햄버거를 누르면 접힘 메뉴가 헤더 아래로 펼쳐진다 — 게시판 셋과 계정 항목이 들어 있다', (
    tester,
  ) async {
    _setWidth(tester, 390);
    await tester.pumpWidget(_host());

    await tester.tap(find.byKey(const ValueKey('web-header-burger')));
    await tester.pumpAndSettle();

    final menu = find.byKey(const ValueKey('web-header-collapsed-menu'));
    expect(menu, findsOneWidget);
    for (final label in ['오늘', '학습 경로', '자유게시판', 'Q/A', '마이페이지', '설정', '로그아웃']) {
      expect(
        find.descendant(of: menu, matching: find.text(label)),
        findsOneWidget,
        reason: '$label 이 접힘 메뉴에 없으면 폰에서 도달할 방법이 사라진다',
      );
    }

    final header = tester.getRect(find.byKey(const ValueKey('web-header-bar')));
    expect(
      tester.getRect(menu).top,
      greaterThanOrEqualTo(header.bottom),
      reason: '오버레이가 아니라 헤더 아래 인라인 확장이어야 한다(스펙 §5.3)',
    );
  });

  testWidgets('접힘 메뉴 항목을 고르면 메뉴가 닫히고 onSelect 가 불린다', (tester) async {
    _setWidth(tester, 390);
    String? picked;
    await tester.pumpWidget(_host(onSelect: (id) => picked = id));

    await tester.tap(find.byKey(const ValueKey('web-header-burger')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Q/A'));
    await tester.pumpAndSettle();

    expect(picked, '/community?board=QNA');
    expect(find.byKey(const ValueKey('web-header-collapsed-menu')), findsNothing);
  });

  // Review Focus 1
  testWidgets('접힘 메뉴를 연 채 폭이 넓어지면 접힘 상태가 풀린다', (tester) async {
    _setWidth(tester, 390);
    await tester.pumpWidget(_host());
    await tester.tap(find.byKey(const ValueKey('web-header-burger')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('web-header-collapsed-menu')), findsOneWidget);

    tester.view.physicalSize = const Size(1240, 900);
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey('web-header-collapsed-menu')),
      findsNothing,
      reason: '닫을 버튼이 사라진 채 메뉴만 남으면 빠져나올 수 없다',
    );
  });

  testWidgets('현재 항목에만 밑줄이 있다 — 매칭 실패면 아무 데도 없다', (tester) async {
    _setWidth(tester, 1240);
    await tester.pumpWidget(_host(selectedId: '/path'));
    expect(
      tester.widget<DpWebHeader>(find.byType(DpWebHeader)).selectedId,
      '/path',
    );
    expect(find.byKey(const ValueKey('web-header-current-/path')), findsOneWidget);
    expect(find.byKey(const ValueKey('web-header-current-/dashboard')), findsNothing);

    await tester.pumpWidget(_host());
    expect(find.byKeyValue(startsWith: 'web-header-current-'), findsNothing);
  });

  testWidgets('커뮤니티 자식이 현재면 부모에 밑줄이 간다', (tester) async {
    _setWidth(tester, 1240);
    await tester.pumpWidget(_host(selectedId: '/community?board=QNA'));
    expect(find.byKey(const ValueKey('web-header-current-/community')), findsOneWidget);
  });

  // Review Focus 4
  testWidgets('390 폭 · 텍스트 200% 에서 헤더가 오버플로하지 않는다', (tester) async {
    _setWidth(tester, 390);
    await tester.pumpWidget(_host(textScale: 2.0));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('접힘 메뉴의 모든 항목은 최소 타깃 24 이상이다', (tester) async {
    // getSemantics 는 시맨틱스가 켜져 있어야 한다 — 핸들 없이 부르면 던진다.
    final handle = tester.ensureSemantics();
    addTearDown(handle.dispose);

    _setWidth(tester, 390);
    await tester.pumpWidget(_host());
    await tester.tap(find.byKey(const ValueKey('web-header-burger')));
    await tester.pumpAndSettle();

    for (final label in ['오늘', '자유게시판', '로그아웃']) {
      final rect = tester.getSemantics(find.text(label)).rect;
      expect(
        rect.height,
        greaterThanOrEqualTo(DpDensity.minTarget),
        reason: '$label 의 시맨틱 박스가 ${rect.height} — 위젯 크기가 아니라 이 값이 2.5.8 기준이다',
      );
    }
  });
}

/// `find.byKey` 는 정확한 키만 찾는다 — 접두사로 「어떤 현재 항목도 없음」을 재려면 술어가 필요하다.
extension on CommonFinders {
  Finder byKeyValue({required String startsWith}) => find.byWidgetPredicate((w) {
    final key = w.key;
    return key is ValueKey<String> && key.value.startsWith(startsWith);
  });
}
```

- [ ] **Step 2: 실패 확인**

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/shell/dp_web_header_test.dart
```

Expected: 컴파일 실패 — `Undefined name 'DpWebHeader'` / `DpWebNavItem`.

- [ ] **Step 3: 목적지 모델 구현**

`packages/dp_design/lib/src/shell/dp_web_nav_item.dart`:

```dart
import 'package:flutter/foundation.dart';

/// 상단 헤더의 주 메뉴 항목. [children] 이 비어 있지 않으면 드롭다운이다.
///
/// [id] 는 dp_design 에게 불투명한 문자열이다 — 앱이 경로로 해석한다
/// (`DpDestination` 의 index 방식과 다른 판단: 커뮤니티 자식까지 index 로
/// 세면 앱이 평면·계층 두 벌의 순서를 맞춰야 한다).
@immutable
class DpWebNavItem {
  const DpWebNavItem({
    required this.id,
    required this.label,
    this.children = const [],
  });

  final String id;
  final String label;
  final List<DpWebNavItem> children;

  /// 이 항목이나 그 자식이 [selectedId] 인가.
  bool isCurrent(String? selectedId) =>
      selectedId != null &&
      (id == selectedId || children.any((child) => child.id == selectedId));
}
```

- [ ] **Step 4: 헤더 구현**

`packages/dp_design/lib/src/shell/dp_web_header.dart`:

```dart
import 'package:flutter/material.dart';

import '../icons/dp_icons.dart';
import '../layout/dp_window_class.dart';
import '../theme/dp_colors.dart';
import '../theme/dp_spacing.dart';
import '../theme/dp_tokens.dart';
import 'dp_menu_button.dart';
import 'dp_rail_brand.dart';
import 'dp_web_nav_item.dart';

/// 웹 문법의 상단 헤더(스펙 §5.3, 시안 `.hd`). 라우팅 비의존 — 선택은 id 로 통지.
///
/// 어두운 면(`headerBg`)이고 높이는 계약의 `AppTokens.headerHeight`(56)다.
/// [compactBreakpoint] 미만에서는 주 메뉴·검색·계정을 감추고 햄버거만 남기며,
/// 펼치면 헤더 **아래로 인라인 확장**한다 — overlay·drawer·focus trap 을 쓰지
/// 않는다(스펙 §5.3: 홈 랜딩과 같은 규칙).
class DpWebHeader extends StatefulWidget {
  const DpWebHeader({
    super.key,
    required this.brand,
    required this.items,
    required this.selectedId,
    required this.onSelect,
    required this.accountEntries,
    this.onSearchTap,
  });

  /// 시안 `@container (max-width:720px)`. `DpWindowClass` 경계(600/840)와 다르다 —
  /// 시안이 정한 값이라 그대로 쓴다.
  static const double compactBreakpoint = 720;

  final DpRailBrand brand;
  final List<DpWebNavItem> items;
  final String? selectedId;
  final ValueChanged<String> onSelect;
  final List<DpMenuEntry> accountEntries;
  final VoidCallback? onSearchTap;

  @override
  State<DpWebHeader> createState() => _DpWebHeaderState();
}

class _DpWebHeaderState extends State<DpWebHeader> {
  final _burgerFocus = FocusNode(debugLabel: 'web-header-burger');
  bool _expanded = false;

  @override
  void dispose() {
    _burgerFocus.dispose();
    super.dispose();
  }

  void _pick(String id) {
    // 먼저 접는다 — 라우트가 바뀐 뒤에 접으면 새 화면 위에 메뉴가 남는다.
    if (_expanded) setState(() => _expanded = false);
    widget.onSelect(id);
  }

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final compact =
        MediaQuery.sizeOf(context).width < DpWebHeader.compactBreakpoint;

    // Review Focus 1: compact 가 아니게 되면 접힘 상태를 자동으로 푼다.
    // 안 그러면 닫을 버튼(햄버거)이 사라진 채 메뉴만 남는다.
    if (!compact && _expanded) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) setState(() => _expanded = false);
      });
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _bar(context, c, compact),
        if (compact && _expanded) _collapsedMenu(context, c),
      ],
    );
  }

  Widget _bar(BuildContext context, DpColors c, bool compact) => Container(
    key: const ValueKey('web-header-bar'),
    height: context.appTokens.headerHeight,
    decoration: BoxDecoration(
      color: c.headerBg,
      border: Border(bottom: BorderSide(color: c.headerBorder)),
    ),
    padding: EdgeInsets.symmetric(
      horizontal: compact ? DpSpacing.lg : DpSpacing.xl,
    ),
    child: Row(
      children: [
        _brand(context, c),
        if (compact) ...[
          const Spacer(),
          _burger(context, c),
        ] else ...[
          const SizedBox(width: DpSpacing.xl),
          Expanded(child: _nav(context, c)),
          const SizedBox(width: DpSpacing.xl),
          _search(context, c),
          const SizedBox(width: DpSpacing.sm),
          _account(context, c),
        ],
      ],
    ),
  );

  Widget _brand(BuildContext context, DpColors c) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      SizedBox.square(dimension: 24, child: FittedBox(child: widget.brand.mark)),
      const SizedBox(width: DpSpacing.sm),
      Text(
        widget.brand.wordmark,
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
          color: c.headerText,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
        ),
      ),
    ],
  );

  Widget _nav(BuildContext context, DpColors c) => Row(
    key: const ValueKey('web-header-nav'),
    mainAxisSize: MainAxisSize.min,
    children: [
      for (final item in widget.items)
        Padding(
          padding: const EdgeInsets.only(right: DpSpacing.xs),
          child: item.children.isEmpty
              ? _navLink(context, c, item)
              : _navDropdown(context, c, item),
        ),
    ],
  );

  /// 평시 `headerMuted`, 현재 항목은 `headerText` + 하단 2px primary 밑줄(반경 0).
  Widget _navSurface(
    BuildContext context,
    DpColors c, {
    required DpWebNavItem item,
    required Widget child,
    required VoidCallback onTap,
    FocusNode? focusNode,
  }) {
    final current = item.isCurrent(widget.selectedId);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        key: current ? ValueKey('web-header-current-${item.id}') : null,
        focusNode: focusNode,
        onTap: onTap,
        borderRadius: current
            ? BorderRadius.zero
            : BorderRadius.circular(DpRadius.button),
        hoverColor: c.headerActive,
        child: Container(
          height: DpDensity.controlHeight,
          padding: const EdgeInsets.symmetric(horizontal: DpSpacing.md),
          decoration: current
              ? BoxDecoration(
                  border: Border(
                    bottom: BorderSide(color: c.primary, width: 2),
                  ),
                )
              : null,
          alignment: Alignment.center,
          child: DefaultTextStyle.merge(
            style: TextStyle(
              color: current ? c.headerText : c.headerMuted,
              fontWeight: FontWeight.w500,
            ),
            child: child,
          ),
        ),
      ),
    );
  }

  Widget _navLink(BuildContext context, DpColors c, DpWebNavItem item) =>
      _navSurface(
        context,
        c,
        item: item,
        onTap: () => _pick(item.id),
        child: Text(item.label, overflow: TextOverflow.ellipsis),
      );

  Widget _navDropdown(BuildContext context, DpColors c, DpWebNavItem item) =>
      DpMenuButton(
        entries: [
          for (final child in item.children)
            (label: child.label, onSelect: () => _pick(child.id)),
        ],
        builder: (context, buttonFocus, toggle, isOpen) => _navSurface(
          context,
          c,
          item: item,
          focusNode: buttonFocus,
          onTap: toggle,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Flexible(child: Text(item.label, overflow: TextOverflow.ellipsis)),
              Icon(
                isOpen ? Icons.expand_less : Icons.expand_more,
                size: 18,
                color: item.isCurrent(widget.selectedId)
                    ? c.headerText
                    : c.headerMuted,
              ),
            ],
          ),
        ),
      );

  /// 시안의 입력 상자 모양이지만 실제 입력은 `DpCommandPalette` 가 받는다
  /// (`DpChromeBar` 와 같은 판단 — 입력 상태를 두 곳에서 관리하지 않는다).
  Widget _search(BuildContext context, DpColors c) {
    if (widget.onSearchTap == null) return const SizedBox.shrink();
    return SizedBox(
      width: 200,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          key: const ValueKey('web-header-search'),
          onTap: widget.onSearchTap,
          borderRadius: BorderRadius.circular(DpRadius.input),
          child: Container(
            height: DpDensity.controlHeight,
            padding: const EdgeInsets.symmetric(horizontal: DpSpacing.sm),
            decoration: BoxDecoration(
              // 시안의 #1B1E29 는 토큰이 아니다 — 어두운 헤더 위의 표면 토큰을 쓴다.
              color: c.headerActive,
              border: Border.all(color: c.headerBorder),
              borderRadius: BorderRadius.circular(DpRadius.input),
            ),
            child: Row(
              children: [
                Icon(DpIcons.search, size: 16, color: c.headerMuted),
                const SizedBox(width: DpSpacing.xs),
                Flexible(
                  child: Text(
                    '검색',
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(
                      context,
                    ).textTheme.labelMedium?.copyWith(color: c.headerMuted),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _account(BuildContext context, DpColors c) => DpMenuButton(
    entries: widget.accountEntries,
    builder: (context, buttonFocus, toggle, isOpen) => IconButton(
      key: const ValueKey('web-header-account'),
      focusNode: buttonFocus,
      // 색을 명시하지 않는다 — 어두운 헤더가 공급하는 IconTheme 을 상속한다.
      icon: const Icon(DpIcons.account),
      tooltip: '계정',
      style: IconButton.styleFrom(
        minimumSize: const Size.square(DpDensity.controlHeight),
        foregroundColor: c.headerText,
      ),
      onPressed: toggle,
    ),
  );

  Widget _burger(BuildContext context, DpColors c) => Semantics(
    // 함정 1·2: 헤더 표식과 합쳐지지 않도록 자기 노드로 가둔다.
    container: true,
    child: OutlinedButton.icon(
      key: const ValueKey('web-header-burger'),
      focusNode: _burgerFocus,
      icon: const Icon(DpIcons.menu, size: 18),
      label: const Text('메뉴'),
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(0, DpDensity.controlHeight),
        padding: const EdgeInsets.symmetric(horizontal: DpSpacing.md),
        foregroundColor: c.headerText,
        side: BorderSide(color: c.headerBorder),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(DpRadius.button),
        ),
      ),
      onPressed: () => setState(() => _expanded = !_expanded),
    ),
  );

  Widget _collapsedMenu(BuildContext context, DpColors c) {
    final rows = <Widget>[];
    for (final item in widget.items) {
      if (item.children.isEmpty) {
        rows.add(_menuRow(context, c, item.label, () => _pick(item.id)));
      } else {
        rows.add(_menuSection(context, c, item.label));
        for (final child in item.children) {
          rows.add(
            _menuRow(context, c, child.label, () => _pick(child.id), sub: true),
          );
        }
      }
    }
    rows.add(_menuSection(context, c, '계정'));
    for (final entry in widget.accountEntries) {
      rows.add(
        _menuRow(context, c, entry.label, () {
          setState(() => _expanded = false);
          entry.onSelect?.call();
        }, sub: true),
      );
    }

    return Container(
      key: const ValueKey('web-header-collapsed-menu'),
      decoration: BoxDecoration(
        color: c.headerBg,
        border: Border(bottom: BorderSide(color: c.headerBorder)),
      ),
      padding: const EdgeInsets.fromLTRB(
        DpSpacing.lg,
        DpSpacing.sm,
        DpSpacing.lg,
        DpSpacing.md,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: rows,
      ),
    );
  }

  Widget _menuRow(
    BuildContext context,
    DpColors c,
    String label,
    VoidCallback onTap, {
    bool sub = false,
  }) => Material(
    color: Colors.transparent,
    child: InkWell(
      onTap: onTap,
      child: Container(
        // 최소 타깃 24(계약 2.0.0). 시안의 7px 세로 패딩으로는 시맨틱 박스가
        // 모자랄 수 있어 하한을 명시한다.
        constraints: const BoxConstraints(minHeight: DpDensity.controlHeight),
        padding: EdgeInsets.only(left: sub ? DpSpacing.md : 0),
        alignment: Alignment.centerLeft,
        child: Text(
          label,
          style: TextStyle(
            color: sub ? c.headerMuted : c.headerText,
            fontWeight: sub ? FontWeight.w400 : FontWeight.w500,
          ),
        ),
      ),
    ),
  );

  Widget _menuSection(BuildContext context, DpColors c, String label) =>
      Container(
        margin: const EdgeInsets.only(top: DpSpacing.sm),
        padding: const EdgeInsets.only(top: DpSpacing.sm),
        decoration: BoxDecoration(
          border: Border(top: BorderSide(color: c.headerBorder)),
        ),
        child: Text(
          label,
          style: Theme.of(
            context,
          ).textTheme.labelSmall?.copyWith(color: c.headerMuted),
        ),
      );
}
```

- [ ] **Step 5: 배럴 추가 후 통과 확인**

`packages/dp_design/lib/dp_design.dart` 에 두 줄 추가:

```dart
export 'src/shell/dp_web_nav_item.dart';
export 'src/shell/dp_web_header.dart';
```

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/shell/dp_web_header_test.dart
```

Expected: 10 tests passed. (실패하면 오버플로·시맨틱 박스 높이 순서로 본다 — 증상을 가리는 방향으로 테스트를 낮추지 않는다.)

- [ ] **Step 6: 커밋**

```bash
git -C "$WT" add packages/dp_design/lib/src/shell/dp_web_nav_item.dart packages/dp_design/lib/src/shell/dp_web_header.dart packages/dp_design/lib/dp_design.dart packages/dp_design/test/shell/dp_web_header_test.dart
git -C "$WT" commit -m "$(cat <<'EOF'
feat(dp_design): DpWebHeader — 상단 헤더·커뮤니티 드롭다운·햄버거 인라인 메뉴

시안의 .hd/.mnav 를 그대로 옮긴다. 높이 56·어두운 면·컨트롤 30px·반경 6,
compact 경계는 시안의 container 720px. 접힘 메뉴는 오버레이가 아니라 헤더
아래 인라인 확장이고, 폭이 넓어지면 자동으로 풀린다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `DpWebFooter`

**Files:**
- Create: `packages/dp_design/lib/src/shell/dp_web_footer.dart`
- Create: `packages/dp_design/test/shell/dp_web_footer_test.dart`
- Modify: `packages/dp_design/lib/dp_design.dart`

**Interfaces:**
- Produces: `typedef DpFooterLink = ({String label, VoidCallback onTap});` · `class DpWebFooter extends StatelessWidget` — `const DpWebFooter({super.key, required String notice, required List<DpFooterLink> links})`. Task 4·6 이 쓴다.

- [ ] **Step 1: 실패하는 테스트 작성**

`packages/dp_design/test/shell/dp_web_footer_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void _setWidth(WidgetTester tester, double w) {
  tester.view.physicalSize = Size(w, 900);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
}

Widget _host({void Function(String)? onTap, double? textScale}) => MaterialApp(
  theme: DpTheme.light(),
  builder: (context, child) => textScale == null
      ? child!
      : MediaQuery.withClampedTextScaling(
          minScaleFactor: textScale,
          maxScaleFactor: textScale,
          child: child!,
        ),
  home: Scaffold(
    body: Column(
      children: [
        const Spacer(),
        DpWebFooter(
          notice: '© 레바 · 사업자등록번호 796-76-00732',
          links: [
            for (final label in ['이용약관', '개인정보 처리방침', '오류 신고·문의', '업데이트 소식'])
              (label: label, onTap: () => onTap?.call(label)),
          ],
        ),
      ],
    ),
  ),
);

void main() {
  testWidgets('사업자 표기와 링크 4종을 낸다', (tester) async {
    _setWidth(tester, 1240);
    await tester.pumpWidget(_host());

    expect(find.text('© 레바 · 사업자등록번호 796-76-00732'), findsOneWidget);
    for (final label in ['이용약관', '개인정보 처리방침', '오류 신고·문의', '업데이트 소식']) {
      expect(find.text(label), findsOneWidget);
    }
  });

  testWidgets('링크를 누르면 콜백이 불린다', (tester) async {
    _setWidth(tester, 1240);
    String? tapped;
    await tester.pumpWidget(_host(onTap: (label) => tapped = label));

    await tester.tap(find.text('오류 신고·문의'));
    expect(tapped, '오류 신고·문의');
  });

  // Review Focus 5
  testWidgets('링크의 시맨틱 박스는 최소 타깃 24 이상이다', (tester) async {
    final handle = tester.ensureSemantics();
    addTearDown(handle.dispose);

    _setWidth(tester, 1240);
    await tester.pumpWidget(_host());

    for (final label in ['이용약관', '개인정보 처리방침', '오류 신고·문의', '업데이트 소식']) {
      final rect = tester.getSemantics(find.text(label)).rect;
      expect(
        rect.height,
        greaterThanOrEqualTo(DpDensity.minTarget),
        reason: '$label 의 시맨틱 박스 높이가 ${rect.height} — 12px 글자에 패딩이 없으면 2.5.8 을 깬다',
      );
    }
  });

  // Review Focus 4
  testWidgets('390 폭 · 텍스트 200% 에서 줄바꿈으로 흡수하고 오버플로하지 않는다', (tester) async {
    _setWidth(tester, 390);
    await tester.pumpWidget(_host(textScale: 2.0));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('안쪽 내용은 contentMaxWidth 로 중앙 정렬된다', (tester) async {
    _setWidth(tester, 1600);
    await tester.pumpWidget(_host());

    expect(
      find.descendant(of: find.byType(DpWebFooter), matching: find.byType(DpMaxWidth)),
      findsOneWidget,
    );
  });
}
```

- [ ] **Step 2: 실패 확인**

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/shell/dp_web_footer_test.dart
```

Expected: `Undefined name 'DpWebFooter'`.

- [ ] **Step 3: 구현**

`packages/dp_design/lib/src/shell/dp_web_footer.dart`:

```dart
import 'package:flutter/material.dart';

import '../layout/dp_max_width.dart';
import '../theme/dp_colors.dart';
import '../theme/dp_spacing.dart';

/// 푸터 링크.
typedef DpFooterLink = ({String label, VoidCallback onTap});

/// 웹 문법의 푸터(스펙 §5.3, 시안 `.ft`). 상단 경계선 + `surface` 배경,
/// 안쪽은 `contentMaxWidth` 중앙 정렬.
///
/// 셸 하단에 **고정**된다(사용자 결정 2026-09-26). 시안은 내용 끝에 붙지만,
/// Flutter 는 화면마다 자기 스크롤뷰를 가져서 같은 거동을 얻으려면 모든 화면을
/// 고쳐야 한다 — 그것은 P4 의 일이다.
class DpWebFooter extends StatelessWidget {
  const DpWebFooter({super.key, required this.notice, required this.links});

  final String notice;
  final List<DpFooterLink> links;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final text = Theme.of(context).textTheme;

    return Container(
      key: const ValueKey('web-footer-root'),
      decoration: BoxDecoration(
        color: c.surface,
        border: Border(top: BorderSide(color: c.border)),
      ),
      child: DpMaxWidth(
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: DpSpacing.xl,
            vertical: DpSpacing.sm,
          ),
          child: Wrap(
            spacing: DpSpacing.lg,
            runSpacing: DpSpacing.xs,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              // 최소 타깃은 누를 수 있는 것에만 적용된다 — 이 줄은 텍스트다.
              ConstrainedBox(
                constraints: const BoxConstraints(
                  minHeight: DpDensity.minTarget,
                ),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    notice,
                    style: text.labelSmall?.copyWith(color: c.textFaint),
                  ),
                ),
              ),
              for (final link in links)
                Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: link.onTap,
                    borderRadius: BorderRadius.circular(DpRadius.button),
                    child: Container(
                      constraints: const BoxConstraints(
                        minHeight: DpDensity.minTarget,
                      ),
                      padding: const EdgeInsets.symmetric(
                        horizontal: DpSpacing.xs,
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        link.label,
                        style: text.labelSmall?.copyWith(
                          color: c.textSecondary,
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: 배럴 추가 후 통과 확인**

`packages/dp_design/lib/dp_design.dart` 에 `export 'src/shell/dp_web_footer.dart';` 추가.

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/shell/dp_web_footer_test.dart
```

Expected: 5 tests passed.

- [ ] **Step 5: 커밋**

```bash
git -C "$WT" add packages/dp_design/lib/src/shell/dp_web_footer.dart packages/dp_design/lib/dp_design.dart packages/dp_design/test/shell/dp_web_footer_test.dart
git -C "$WT" commit -m "$(cat <<'EOF'
feat(dp_design): DpWebFooter — 사업자 표기 + 법적·지원 링크 4종

시안 .ft 를 그대로 옮긴다. 안쪽은 contentMaxWidth 중앙 정렬, 링크의
시맨틱 박스는 계약 2.0.0 의 최소 타깃 24 를 지킨다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `DpBreadcrumb` — 본문 상단 브레드크럼

크롬바가 web 에서 사라지므로 브레드크럼이 갈 곳이 필요하다(시안 `.crumb`). `DpChromeBar._crumbs` 는 **건드리지 않는다** — admin 이 쓴다.

**Files:**
- Create: `packages/dp_design/lib/src/shell/dp_breadcrumb.dart`
- Create: `packages/dp_design/test/shell/dp_breadcrumb_test.dart`
- Modify: `packages/dp_design/lib/dp_design.dart`

**Interfaces:**
- Consumes: `DpCrumb`(`dp_chrome_bar.dart` 의 기존 typedef — 재정의하지 않고 import 한다).
- Produces: `class DpBreadcrumb extends StatelessWidget` — `const DpBreadcrumb({super.key, required List<DpCrumb> crumbs, ValueChanged<String>? onCrumbTap})`. Task 5 가 쓴다.

- [ ] **Step 1: 실패하는 테스트 작성**

`packages/dp_design/test/shell/dp_breadcrumb_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host({required List<DpCrumb> crumbs, void Function(String)? onTap}) =>
    MaterialApp(
      theme: DpTheme.light(),
      home: Scaffold(
        body: DpBreadcrumb(crumbs: crumbs, onCrumbTap: onTap),
      ),
    );

void main() {
  testWidgets('세그먼트와 › 구분자를 낸다', (tester) async {
    await tester.pumpWidget(
      _host(
        crumbs: const [
          (label: '커뮤니티', path: '/community'),
          (label: 'Q/A', path: null),
        ],
      ),
    );

    expect(find.text('커뮤니티'), findsOneWidget);
    expect(find.text('Q/A'), findsOneWidget);
    expect(find.text('›'), findsOneWidget);
  });

  testWidgets('마지막 세그먼트는 path 가 있어도 링크가 아니다', (tester) async {
    String? tapped;
    await tester.pumpWidget(
      _host(
        crumbs: const [
          (label: '커뮤니티', path: '/community'),
          (label: '자유게시판', path: '/community?board=FREE'),
        ],
        onTap: (p) => tapped = p,
      ),
    );

    await tester.tap(find.text('자유게시판'));
    await tester.pump();
    expect(tapped, isNull, reason: '자기 자신으로 가는 링크를 두지 않는다(브레드크럼 관례)');

    await tester.tap(find.text('커뮤니티'));
    await tester.pump();
    expect(tapped, '/community');
  });

  testWidgets('빈 목록이면 아무것도 그리지 않는다', (tester) async {
    await tester.pumpWidget(_host(crumbs: const []));
    expect(find.byType(SizedBox), findsWidgets);
    expect(find.text('›'), findsNothing);
  });

  testWidgets('링크 세그먼트의 시맨틱 박스는 최소 타깃 24 이상이다', (tester) async {
    final handle = tester.ensureSemantics();
    addTearDown(handle.dispose);

    await tester.pumpWidget(
      _host(
        crumbs: const [
          (label: '커뮤니티', path: '/community'),
          (label: 'Q/A', path: null),
        ],
      ),
    );

    expect(
      tester.getSemantics(find.text('커뮤니티')).rect.height,
      greaterThanOrEqualTo(DpDensity.minTarget),
    );
  });
}
```

- [ ] **Step 2: 실패 확인**

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/shell/dp_breadcrumb_test.dart
```

Expected: `Undefined name 'DpBreadcrumb'`.

- [ ] **Step 3: 구현**

`packages/dp_design/lib/src/shell/dp_breadcrumb.dart`:

```dart
import 'package:flutter/material.dart';

import '../theme/dp_colors.dart';
import '../theme/dp_spacing.dart';
import 'dp_chrome_bar.dart' show DpCrumb;

/// 본문 상단 브레드크럼(스펙 §5.3, 시안 `.crumb`).
///
/// `DpChromeBar` 안의 브레드크럼과 별개다 — 크롬바는 `apps/admin` 이 계속 쓰고,
/// web 은 크롬바 없이 이것을 본문 맨 위에 둔다.
class DpBreadcrumb extends StatelessWidget {
  const DpBreadcrumb({super.key, required this.crumbs, this.onCrumbTap});

  final List<DpCrumb> crumbs;
  final ValueChanged<String>? onCrumbTap;

  @override
  Widget build(BuildContext context) {
    if (crumbs.isEmpty) return const SizedBox.shrink();
    final c = context.dpColors;
    final style = Theme.of(
      context,
    ).textTheme.labelMedium?.copyWith(color: c.textFaint);

    final children = <Widget>[];
    for (var i = 0; i < crumbs.length; i++) {
      final crumb = crumbs[i];
      final isLast = i == crumbs.length - 1;
      final label = Text(
        crumb.label,
        style: style?.copyWith(color: isLast ? c.textFaint : c.textSecondary),
        overflow: TextOverflow.ellipsis,
      );

      children.add(
        // 마지막 세그먼트는 현재 위치이므로 path 가 있어도 링크하지 않는다.
        (crumb.path == null || isLast)
            ? ConstrainedBox(
                constraints: const BoxConstraints(
                  minHeight: DpDensity.minTarget,
                ),
                child: Align(alignment: Alignment.centerLeft, child: label),
              )
            : Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () => onCrumbTap?.call(crumb.path!),
                  borderRadius: BorderRadius.circular(DpRadius.button),
                  child: Container(
                    constraints: const BoxConstraints(
                      minHeight: DpDensity.minTarget,
                    ),
                    alignment: Alignment.centerLeft,
                    child: label,
                  ),
                ),
              ),
      );

      if (!isLast) {
        children.add(
          ConstrainedBox(
            constraints: const BoxConstraints(minHeight: DpDensity.minTarget),
            child: Align(alignment: Alignment.center, child: Text('›', style: style)),
          ),
        );
      }
    }

    return Semantics(
      container: true,
      label: '현재 위치',
      child: Wrap(
        spacing: DpSpacing.xs,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: children,
      ),
    );
  }
}
```

- [ ] **Step 4: 배럴 추가 후 통과 확인**

`packages/dp_design/lib/dp_design.dart` 에 `export 'src/shell/dp_breadcrumb.dart';` 추가.

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/shell/dp_breadcrumb_test.dart
```

Expected: 4 tests passed.

- [ ] **Step 5: 커밋**

```bash
git -C "$WT" add packages/dp_design/lib/src/shell/dp_breadcrumb.dart packages/dp_design/lib/dp_design.dart packages/dp_design/test/shell/dp_breadcrumb_test.dart
git -C "$WT" commit -m "$(cat <<'EOF'
feat(dp_design): DpBreadcrumb — 본문 상단 브레드크럼

web 셸에서 크롬바가 빠지므로 브레드크럼이 본문 맨 위로 간다(시안 .crumb).
DpChromeBar 의 것은 admin 이 계속 쓰므로 건드리지 않는다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `DpWebShell` — 헤더·본문·푸터 합성

**Files:**
- Create: `packages/dp_design/lib/src/shell/dp_web_shell.dart`
- Create: `packages/dp_design/test/shell/dp_web_shell_test.dart`
- Modify: `packages/dp_design/lib/dp_design.dart`

**Interfaces:**
- Consumes: Task 2 의 `DpWebHeader`·`DpWebNavItem`, Task 3 의 `DpWebFooter`·`DpFooterLink`, Task 4 의 `DpBreadcrumb`, Task 1 의 `DpMenuEntry`.
- Produces: `class DpWebShell extends StatelessWidget` — `const DpWebShell({super.key, required DpRailBrand brand, required List<DpWebNavItem> items, required String? selectedId, required ValueChanged<String> onSelect, required List<DpMenuEntry> accountEntries, required String footerNotice, required List<DpFooterLink> footerLinks, required Widget body, List<DpCrumb> breadcrumb = const [], ValueChanged<String>? onCrumbTap, VoidCallback? onSearchTap})`. Task 6 이 쓴다.

- [ ] **Step 1: 실패하는 테스트 작성**

`packages/dp_design/test/shell/dp_web_shell_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void _setWidth(WidgetTester tester, double w) {
  tester.view.physicalSize = Size(w, 900);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
}

Widget _host({List<DpCrumb> breadcrumb = const []}) => MaterialApp(
  theme: DpTheme.light(),
  home: DpWebShell(
    brand: DpRailBrand(mark: const DpBrandMark(size: 24), wordmark: 'Leva'),
    items: const [DpWebNavItem(id: '/dashboard', label: '오늘')],
    selectedId: '/dashboard',
    onSelect: (_) {},
    accountEntries: [(label: '로그아웃', onSelect: () {})],
    footerNotice: '© 레바',
    footerLinks: [(label: '이용약관', onTap: () {})],
    breadcrumb: breadcrumb,
    body: const Text('본문'),
  ),
);

void main() {
  testWidgets('헤더 · 본문 · 푸터를 세로로 쌓는다 — 레일과 하단 내비는 없다', (tester) async {
    _setWidth(tester, 1240);
    await tester.pumpWidget(_host());

    expect(find.byType(DpWebHeader), findsOneWidget);
    expect(find.text('본문'), findsOneWidget);
    expect(find.byType(DpWebFooter), findsOneWidget);
    expect(find.byType(DpNavRail), findsNothing);
    expect(find.byType(DpMobileNavigation), findsNothing);
    expect(find.byType(DpChromeBar), findsNothing);
  });

  testWidgets('푸터는 헤더보다 아래, 본문보다 아래다', (tester) async {
    _setWidth(tester, 1240);
    await tester.pumpWidget(_host());

    final header = tester.getRect(find.byType(DpWebHeader));
    final footer = tester.getRect(find.byType(DpWebFooter));
    expect(footer.top, greaterThan(header.bottom));
  });

  testWidgets('compact 에서도 푸터는 보인다(사용자 결정: 셸 하단 고정)', (tester) async {
    _setWidth(tester, 390);
    await tester.pumpWidget(_host());
    expect(find.byType(DpWebFooter), findsOneWidget);
  });

  testWidgets('본문은 contentMaxWidth 로 중앙 정렬된다 — large 뿐 아니라 모든 폭에서', (
    tester,
  ) async {
    for (final width in [900.0, 1600.0]) {
      _setWidth(tester, width);
      await tester.pumpWidget(_host());
      expect(
        find.descendant(
          of: find.byKey(const ValueKey('web-shell-main')),
          matching: find.byType(DpMaxWidth),
        ),
        findsOneWidget,
        reason: '폭 $width 에서 본문 최대폭 제약이 없다 — 시안의 .main{max-width:1120px} 은 무조건이다',
      );
    }
  });

  testWidgets('브레드크럼은 본문 위, 헤더 아래에 놓인다', (tester) async {
    _setWidth(tester, 1240);
    await tester.pumpWidget(
      _host(
        breadcrumb: const [
          (label: '커뮤니티', path: '/community'),
          (label: 'Q/A', path: null),
        ],
      ),
    );

    final crumb = tester.getRect(find.byType(DpBreadcrumb));
    final header = tester.getRect(find.byType(DpWebHeader));
    final body = tester.getRect(find.text('본문'));
    expect(crumb.top, greaterThanOrEqualTo(header.bottom));
    expect(crumb.bottom, lessThanOrEqualTo(body.top));
  });

  testWidgets('브레드크럼이 비면 자리를 차지하지 않는다', (tester) async {
    _setWidth(tester, 1240);
    await tester.pumpWidget(_host());
    expect(find.byType(DpBreadcrumb), findsOneWidget);
    expect(tester.getSize(find.byType(DpBreadcrumb)).height, 0);
  });
}
```

- [ ] **Step 2: 실패 확인**

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/shell/dp_web_shell_test.dart
```

Expected: `Undefined name 'DpWebShell'`.

- [ ] **Step 3: 구현**

`packages/dp_design/lib/src/shell/dp_web_shell.dart`:

```dart
import 'package:flutter/material.dart';

import '../layout/dp_max_width.dart';
import '../theme/dp_colors.dart';
import '../theme/dp_spacing.dart';
import 'dp_breadcrumb.dart';
import 'dp_chrome_bar.dart' show DpCrumb;
import 'dp_menu_button.dart';
import 'dp_rail_brand.dart';
import 'dp_web_footer.dart';
import 'dp_web_header.dart';
import 'dp_web_nav_item.dart';

/// 웹 문법 셸(스펙 §5.3·§7 P2, 시안 `.screen`): 상단 헤더 + 중앙 본문 + 푸터.
///
/// `DpAppShell`(레일 + 크롬바 + 하단 내비)을 **대체하지 않는다** — 그쪽은
/// `apps/admin` 이 계속 쓴다. 이것은 `apps/web` 전용이다.
///
/// 본문은 폭과 무관하게 항상 `contentMaxWidth` 로 중앙 정렬한다
/// (`DpAppShell.constrainBodyAtLarge` 와 다른 규칙 — 시안 `.main` 은 무조건이다).
class DpWebShell extends StatelessWidget {
  const DpWebShell({
    super.key,
    required this.brand,
    required this.items,
    required this.selectedId,
    required this.onSelect,
    required this.accountEntries,
    required this.footerNotice,
    required this.footerLinks,
    required this.body,
    this.breadcrumb = const [],
    this.onCrumbTap,
    this.onSearchTap,
  });

  final DpRailBrand brand;
  final List<DpWebNavItem> items;
  final String? selectedId;
  final ValueChanged<String> onSelect;
  final List<DpMenuEntry> accountEntries;
  final String footerNotice;
  final List<DpFooterLink> footerLinks;
  final Widget body;
  final List<DpCrumb> breadcrumb;
  final ValueChanged<String>? onCrumbTap;
  final VoidCallback? onSearchTap;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final compact =
        MediaQuery.sizeOf(context).width < DpWebHeader.compactBreakpoint;

    return Scaffold(
      // 실측: `DpColors` 의 배경 토큰 이름은 `background` 가 아니라 `bg` 다.
      backgroundColor: c.bg,
      body: Column(
        children: [
          DpWebHeader(
            brand: brand,
            items: items,
            selectedId: selectedId,
            onSelect: onSelect,
            accountEntries: accountEntries,
            onSearchTap: onSearchTap,
          ),
          Expanded(
            child: Padding(
              key: const ValueKey('web-shell-main'),
              padding: EdgeInsets.symmetric(
                horizontal: compact ? DpSpacing.lg : DpSpacing.xl,
              ),
              child: DpMaxWidth(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    DpBreadcrumb(crumbs: breadcrumb, onCrumbTap: onCrumbTap),
                    Expanded(child: body),
                  ],
                ),
              ),
            ),
          ),
          DpWebFooter(notice: footerNotice, links: footerLinks),
        ],
      ),
    );
  }
}
```

- [ ] **Step 4: 배럴 추가 후 dp_design 전체 통과 확인**

`packages/dp_design/lib/dp_design.dart` 에 `export 'src/shell/dp_web_shell.dart';` 추가.

```bash
cd "$WT" && "$DART" run melos run analyze
cd "$WT/packages/dp_design" && "$FLUTTER" test
```

Expected: analyze 무이슈. dp_design 전체 통과(기존 + 신규 23건). `dp_code_font_test.dart` 1건 실패는 CRLF 체크아웃 탓이므로 무시한다.

- [ ] **Step 5: 커밋**

```bash
git -C "$WT" add packages/dp_design/lib/src/shell/dp_web_shell.dart packages/dp_design/lib/dp_design.dart packages/dp_design/test/shell/dp_web_shell_test.dart
git -C "$WT" commit -m "$(cat <<'EOF'
feat(dp_design): DpWebShell — 헤더 + 중앙 본문 + 푸터

apps/web 전용 셸. DpAppShell 은 apps/admin 이 계속 쓰므로 그대로 둔다.
본문은 폭과 무관하게 contentMaxWidth 로 중앙 정렬하고(시안 .main),
브레드크럼은 본문 맨 위에 놓는다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `apps/web` 셸 교체

**Files:**
- Modify: `apps/web/lib/src/features/shell/presentation/app_shell.dart` (전면)
- Modify: `apps/web/test/features/shell/app_shell_view_test.dart`
- Modify: `apps/web/test/features/shell/app_shell_breadcrumb_test.dart`
- Delete: `apps/web/test/features/shell/app_shell_rail_toggle_test.dart` (web 에 레일이 없다)
- Modify: `apps/web/test/features/community/community_navigation_hierarchy_test.dart`
- Modify: `apps/web/test/features/support/support_entrypoints_test.dart`

**Interfaces:**
- Consumes: Task 5 의 `DpWebShell`, Task 2 의 `DpWebNavItem`, Task 1 의 `DpMenuEntry`, Task 3 의 `DpFooterLink`. 기존 `externalLinkOpenerProvider`(`open(String url)`) · `showSupportDialog(BuildContext)` · `settingsControllerProvider.notifier.logout()` · `AppConfig.homeBaseUrl`.
- Produces: `const List<DpWebNavItem> kWebNavItems` · `String? webNavSelectedIdFor(String location)` · `AppShellView`(시그니처 유지: `location`·`child`·`onSelect`·`onLogout`) + 새 옵셔널 `onOpenExternal`·`onOpenSupport`. `breadcrumbFor`·`shellDestinationIndexFor` 는 **유지**한다. `kShellDestinations`·`kCompactShellDestinations`·`compactShellDestinationIndexFor` 는 삭제한다.

- [ ] **Step 1: 실패하는 테스트 작성 — 셸 구조**

`apps/web/test/features/shell/app_shell_view_test.dart` 의 위젯 테스트를 새 구조로 바꾼다. 아래 세 개를 **삭제**한다: `좁은 폭(<600)은 Leva 플로팅 하단 내비` · `중간 폭(600–839)은 접힌 NavigationRail(하단 Bar 아님)` · `Large 폭(≥1240)은 펼친 Rail + 본문 최대폭 제약`. `첫 목적지 라벨은 Today다` 는 `kWebNavItems.first.label` 로 고친다. 크롬바를 찾는 두 테스트는 `DpBreadcrumb` 로 고친다. 계정 아이콘 색 테스트 두 개는 아래 하나로 합친다. 그리고 다음을 추가한다:

```dart
  testWidgets('모든 폭에서 상단 헤더 셸이다 — 레일도 하단 내비도 없다', (tester) async {
    for (final width in [390.0, 700.0, 1400.0]) {
      _setWidth(tester, width);
      await tester.pumpWidget(
        _host(const AppShellView(location: '/dashboard', child: Text('본문'))),
      );
      expect(find.byType(DpWebShell), findsOneWidget, reason: '폭 $width');
      expect(find.byType(DpNavRail), findsNothing, reason: '폭 $width');
      expect(find.byType(DpMobileNavigation), findsNothing, reason: '폭 $width');
    }
  });

  test('주 메뉴는 오늘·학습 경로·AI 멘토·커뮤니티(자식 3)다', () {
    expect(kWebNavItems.map((i) => i.label).toList(), [
      '오늘',
      '학습 경로',
      'AI 멘토',
      '커뮤니티',
    ]);
    expect(kWebNavItems.last.children.map((i) => i.label).toList(), [
      '자유게시판',
      'Q/A',
      '피드백',
    ]);
  });

  test('위치 → 헤더 선택 id', () {
    expect(webNavSelectedIdFor('/dashboard'), '/dashboard');
    expect(webNavSelectedIdFor('/path/301/today'), '/dashboard');
    expect(webNavSelectedIdFor('/mission/302/sandbox'), '/dashboard');
    expect(webNavSelectedIdFor('/path'), '/path');
    expect(webNavSelectedIdFor('/mentor'), '/mentor');
    expect(webNavSelectedIdFor('/community'), '/community?board=FREE');
    expect(webNavSelectedIdFor('/community?board=QNA'), '/community?board=QNA');
    expect(
      webNavSelectedIdFor('/community?board=FEEDBACK'),
      '/community?board=FEEDBACK',
    );
  });

  // Review Focus 3
  test('목적지에 없는 위치는 null 이다 — 헤더가 엉뚱한 항목에 밑줄을 긋지 않는다', () {
    for (final location in ['/settings', '/mypage', '/content/77', '/sandbox']) {
      expect(webNavSelectedIdFor(location), isNull, reason: location);
    }
  });

  testWidgets('헤더에서 목적지를 고르면 해당 경로로 콜백', (tester) async {
    _setWidth(tester, 1400);
    String? picked;
    await tester.pumpWidget(
      _host(
        AppShellView(
          location: '/dashboard',
          onSelect: (p) => picked = p,
          child: const Text('본문'),
        ),
      ),
    );

    await tester.tap(find.text('AI 멘토'));
    await tester.pumpAndSettle();
    expect(picked, '/mentor');
  });

  testWidgets('390 폭: 햄버거 메뉴 안에서 게시판으로 이동한다', (tester) async {
    _setWidth(tester, 390);
    String? picked;
    await tester.pumpWidget(
      _host(
        AppShellView(
          location: '/community',
          onSelect: (p) => picked = p,
          child: const Text('본문'),
        ),
      ),
    );

    await tester.tap(find.byKey(const ValueKey('web-header-burger')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('피드백'));
    await tester.pumpAndSettle();
    expect(picked, '/community?board=FEEDBACK');
  });

  testWidgets('계정 메뉴에서 로그아웃을 실행할 수 있다', (tester) async {
    _setWidth(tester, 1400);
    var logoutCalls = 0;
    await tester.pumpWidget(
      _host(
        AppShellView(
          location: '/dashboard',
          onLogout: () async => logoutCalls++,
          child: const Text('본문'),
        ),
      ),
    );

    await tester.tap(find.byKey(const ValueKey('web-header-account')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('로그아웃'));
    await tester.pump();
    expect(logoutCalls, 1);
  });

  testWidgets('푸터 링크: 약관·처리방침은 외부로, 오류 신고는 앱 안에서 연다', (tester) async {
    _setWidth(tester, 1400);
    final opened = <String>[];
    var supportCalls = 0;
    await tester.pumpWidget(
      _host(
        AppShellView(
          location: '/dashboard',
          onOpenExternal: opened.add,
          onOpenSupport: () => supportCalls++,
          child: const Text('본문'),
        ),
      ),
    );

    await tester.tap(find.text('이용약관'));
    await tester.tap(find.text('개인정보 처리방침'));
    await tester.tap(find.text('업데이트 소식'));
    await tester.tap(find.text('오류 신고·문의'));
    await tester.pump();

    expect(opened, [
      'https://leva.ai.kr/terms',
      'https://leva.ai.kr/privacy',
      'https://leva.ai.kr/updates',
    ]);
    expect(supportCalls, 1);
  });

  testWidgets('계정 아이콘은 색을 하드코딩하지 않고 어두운 헤더에서 headerText 로 렌더된다', (
    tester,
  ) async {
    _setWidth(tester, 1400);
    await tester.pumpWidget(
      _host(const AppShellView(location: '/dashboard', child: Text('본문'))),
    );

    final icon = tester.widget<Icon>(find.byIcon(DpIcons.account));
    expect(icon.color, isNull);
  });
```

`app_shell_breadcrumb_test.dart` 와 `community_navigation_hierarchy_test.dart` 의 `DpChromeBar`·`DpMobileNavigation` 단언은 각각 `DpBreadcrumb`·`DpWebHeader` 로 옮긴다. `support_entrypoints_test.dart` 의 `chrome-search` 단언은 `web-header-search` 로 바꾸고, 「크롬바 액션에 오류 신고가 있다」는 「푸터 링크에 오류 신고·문의가 있다」로 바꾼다.

- [ ] **Step 2: 실패 확인**

```bash
cd "$WT/apps/web" && "$FLUTTER" test test/features/shell/ test/features/support/ test/features/community/community_navigation_hierarchy_test.dart
```

Expected: 컴파일 실패 — `Undefined name 'DpWebShell'` / `kWebNavItems` / `webNavSelectedIdFor`.

- [ ] **Step 3: 구현 — 목적지 모델**

`app_shell.dart` 에서 `kShellDestinations`·`kCompactShellDestinations`·`ShellDestination`·`compactShellDestinationIndexFor` 를 지우고 다음으로 바꾼다. `shellDestinationIndexFor` 와 `breadcrumbFor` 는 **손대지 않는다**(테스트가 두텁다).

```dart
/// 상단 헤더의 주 메뉴(스펙 §5.3·시안). 커뮤니티는 드롭다운이고 세 게시판이
/// 그 자식이다 — 게시판 이동 수단은 이 메뉴뿐이다(사용자 결정 2026-09-19 §5.4-3).
const List<DpWebNavItem> kWebNavItems = [
  DpWebNavItem(id: '/dashboard', label: '오늘'),
  DpWebNavItem(id: '/path', label: '학습 경로'),
  DpWebNavItem(id: '/mentor', label: 'AI 멘토'),
  DpWebNavItem(
    id: '/community',
    label: '커뮤니티',
    children: [
      DpWebNavItem(id: '/community?board=FREE', label: '자유게시판'),
      DpWebNavItem(id: '/community?board=QNA', label: 'Q/A'),
      DpWebNavItem(id: '/community?board=FEEDBACK', label: '피드백'),
    ],
  ),
];

/// `shellDestinationIndexFor` 의 index 순서와 1:1 로 맞춘 평면 id 목록.
/// 순서를 바꾸면 두 곳을 함께 바꿔야 한다.
const List<String> _flatNavIds = [
  '/dashboard',
  '/path',
  '/mentor',
  '/community?board=FREE',
  '/community?board=QNA',
  '/community?board=FEEDBACK',
];

/// 위치 → 헤더에서 현재 표시할 id. 매칭되는 목적지가 없으면 null(무강조) —
/// /settings·/mypage·/content/:id·/sandbox 에서 엉뚱한 항목에 밑줄이 가지 않게 한다.
String? webNavSelectedIdFor(String location) {
  final index = shellDestinationIndexFor(location);
  return index == null ? null : _flatNavIds[index];
}
```

- [ ] **Step 4: 구현 — `AppShell` 과 `AppShellView`**

`AppShell.build` 의 `DpCommandPalette.commands` 를 평면 id 로 바꾸고(커뮤니티 부모 `/community` 는 넣지 않는다 — 자식 셋이 이미 있다), `AppShellView` 에 외부 링크·지원 콜백을 넘긴다:

```dart
        return DpCommandPalette(
          commands: [
            for (final id in _flatNavIds)
              (
                id: id,
                label: _commandLabelFor(id),
                icon: _commandIconFor(id),
                onInvoke: () => context.go(id),
              ),
          ],
          child: AppShellView(
            location: location,
            onSelect: (path) => context.go(path),
            onLogout: () =>
                ref.read(settingsControllerProvider.notifier).logout(),
            onOpenExternal: (url) =>
                ref.read(externalLinkOpenerProvider).open(url),
            onOpenSupport: () => showSupportDialog(context),
            child: Column(
              children: [
                const NoticeBannerBar(),
                Expanded(child: child),
              ],
            ),
          ),
        );
```

명령 팔레트 라벨·아이콘은 평면 목록의 부수 정보이므로 같은 파일 위쪽에 둔다:

```dart
String _commandLabelFor(String id) => switch (id) {
  '/dashboard' => '오늘',
  '/path' => '학습 경로',
  '/mentor' => 'AI 멘토',
  '/community?board=FREE' => '자유게시판',
  '/community?board=QNA' => 'Q/A',
  _ => '피드백',
};

IconData _commandIconFor(String id) => switch (id) {
  '/dashboard' => DpIcons.dashboard,
  '/path' => DpIcons.path,
  '/mentor' || '/community?board=QNA' => DpIcons.mentor,
  '/community?board=FREE' => DpIcons.community,
  _ => DpIcons.thumbUp,
};
```

`AppShellView` 는 `StatefulWidget` 일 필요가 없어진다(레일 펼침 상태가 사라진다) — `StatelessWidget` 으로 바꾼다:

```dart
/// 표현부: go_router 비의존 — DpWebShell(상단 헤더 문법)로 위임.
class AppShellView extends StatelessWidget {
  const AppShellView({
    super.key,
    required this.location,
    required this.child,
    this.onSelect,
    this.onLogout,
    this.onOpenExternal,
    this.onOpenSupport,
  });

  final String location;
  final Widget child;
  final void Function(String path)? onSelect;
  final Future<void> Function()? onLogout;
  final void Function(String url)? onOpenExternal;
  final VoidCallback? onOpenSupport;

  /// 법적 문서와 업데이트 소식은 홈(leva.ai.kr)에 있다 — 앱에 라우트가 없다.
  static const _homeBaseUrl = 'https://leva.ai.kr';

  @override
  Widget build(BuildContext context) {
    return DpWebShell(
      brand: DpRailBrand(mark: const DpBrandMark(size: 24), wordmark: 'Leva'),
      items: kWebNavItems,
      selectedId: webNavSelectedIdFor(location),
      onSelect: (id) => onSelect?.call(id),
      accountEntries: [
        (label: '마이페이지', onSelect: () => onSelect?.call('/mypage')),
        (label: '설정', onSelect: () => onSelect?.call('/settings')),
        (
          label: '로그아웃',
          onSelect: onLogout == null ? null : () async => onLogout!.call(),
        ),
      ],
      footerNotice: '© 레바 · 사업자등록번호 796-76-00732',
      footerLinks: [
        (
          label: '이용약관',
          onTap: () => onOpenExternal?.call('$_homeBaseUrl/terms'),
        ),
        (
          label: '개인정보 처리방침',
          onTap: () => onOpenExternal?.call('$_homeBaseUrl/privacy'),
        ),
        (label: '오류 신고·문의', onTap: () => onOpenSupport?.call()),
        (
          label: '업데이트 소식',
          onTap: () => onOpenExternal?.call('$_homeBaseUrl/updates'),
        ),
      ],
      breadcrumb: breadcrumbFor(location),
      onCrumbTap: (p) => onSelect?.call(p),
      onSearchTap: () =>
          Actions.invoke(context, const OpenCommandPaletteIntent()),
      body: child,
    );
  }
}
```

`_AccountMenu` 클래스 전체를 삭제한다 — `DpWebHeader` 의 계정 메뉴가 `DpMenuButton` 으로 같은 일을 하고, 함정 5 도 거기서 해결된다.

- [ ] **Step 5: 통과 확인**

```bash
cd "$WT/apps/web" && "$FLUTTER" test test/features/shell/ test/features/support/ test/features/community/
cd "$WT" && "$DART" run melos run analyze
```

Expected: 전부 통과, analyze 무이슈. 실패하면 **테스트를 낮추지 말고** 원인을 본다.

- [ ] **Step 6: apps/web 전체 테스트**

```bash
cd "$WT/apps/web" && "$FLUTTER" test
```

Expected: 1010건 수준 전부 통과. 화면 테스트가 깨지면 그 화면이 셸 구조에 의존하고 있었다는 뜻이다 — 화면을 고치지 말고(P3/P4 범위) 무엇이 깨졌는지 기록한 뒤 진행을 멈추고 보고한다.

- [ ] **Step 7: 커밋**

```bash
git -C "$WT" add apps/web/lib/src/features/shell/presentation/app_shell.dart apps/web/test/features/shell apps/web/test/features/support apps/web/test/features/community
git -C "$WT" rm apps/web/test/features/shell/app_shell_rail_toggle_test.dart
git -C "$WT" commit -m "$(cat <<'EOF'
feat(web): 셸을 DpWebShell 로 교체 — 상단 헤더·햄버거·푸터

목적지 모델을 index 에서 id(경로) 기반으로 바꾼다. shellDestinationIndexFor
와 breadcrumbFor 는 그대로 두고 얇은 매핑만 얹었다. 브레드크럼은 본문 위로,
오류 신고·문의는 크롬바 액션에서 푸터 링크로 옮겼다. 레일 펼침 상태가
사라져 AppShellView 는 StatelessWidget 이 됐다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: `browser-ux` 시나리오를 새 구조로 다시 쓴다

스펙 §8: 「셸 교체(P2)에서 browser-ux 시나리오(키보드 순회·게시판 이동·메뉴 focus 복귀)를 새 구조에 맞춰 다시 쓴다.」

**Files:**
- Modify: `tools/browser_ux/run.mjs:247-289` (`back-forward-boards`), `:290-313` (`keyboard-traversal` 주석), `:315-342` (`dialog-focus-return` 주석)
- Modify: `tools/browser_ux/expectations.json`
- Modify: `docs/design/browser-ux-contract.md`

**Interfaces:**
- Consumes: Task 2·6 의 접힘 메뉴 — 390 폭에서 `메뉴` 버튼 → 게시판 라벨 버튼.
- Produces: 갱신된 `expectations.json`(`recorded_from` = 이 브랜치의 부모 커밋, `keyboard_traversal.community_desktop` = **CI 실측값**).

- [ ] **Step 1: `back-forward-boards` 를 햄버거 경로로 바꾼다**

`tools/browser_ux/run.mjs` 의 주석과 클릭 두 줄을 바꾼다:

```js
    // 3. board 전환 뒤 back/forward 가 URL 과 H1 을 함께 되돌린다.
    //    390 폭에서 게시판을 옮기는 유일한 수단은 헤더의 접힌 메뉴다(S3-P2).
    //    페이지 안 세그먼트도, 제목 메뉴도 쓰지 않는다.
```

```js
            await page.getByRole('button', { name: '메뉴', exact: true }).first().click();
            // Flutter Web 은 접힘 메뉴 항목을 링크가 아니라 button 으로 낸다(함정 4).
            await page.getByRole('button', { name: label, exact: true }).first().click();
```

- [ ] **Step 2: 기대값을 「미기록」으로 되돌린다**

`keyboard_traversal.community_desktop` 의 값은 지금 순서를 실측한 것이라 새 셸에서는 반드시 틀리다. 추측으로 새 배열을 쓰지 않는다 — 러너가 「아직 기록되지 않았다」로 실패하게 두고 CI 실측값으로 채운다.

`tools/browser_ux/expectations.json`:

```json
{
  "schema_version": "leva.browser-ux.expectations.v1",
  "recorded_from": "PENDING",
  "notes": [
    "community_desktop: /community 1440px 에서 Tab 순서(첫 4 정지).",
    "S3-P2 에서 셸이 상단 헤더로 바뀌어 순서가 달라진다 — CI 의 browser-ux 리포트 아티팩트에서 실측한 뒤 채운다. 추측으로 쓰지 않는다.",
    "갱신은 실측 후 PR 리뷰 승인으로만 한다."
  ],
  "keyboard_traversal": {}
}
```

- [ ] **Step 3: 계약 문서 갱신**

`docs/design/browser-ux-contract.md` 의 시나리오 3 설명에서 「390px 제목 메뉴(`게시판 바꾸기`)」를 「390px 헤더의 접힌 메뉴(`메뉴`)」로, 시나리오 4 설명에 「S3-P2 에서 셸이 상단 헤더가 되어 순회 시작점이 바뀐다 — 기대값은 그 PR 의 CI 실측으로 다시 기록했다」를 한 줄 추가한다.

- [ ] **Step 4: 러너 자체 테스트**

```bash
cd "$WT/tools/browser_ux" && node --test run.test.mjs
```

Expected: 통과(리포트 스키마 테스트라 시나리오 변경과 무관하다 — 깨지면 JSON 문법 오류다).

- [ ] **Step 5: 커밋**

```bash
git -C "$WT" add tools/browser_ux/run.mjs tools/browser_ux/expectations.json docs/design/browser-ux-contract.md
git -C "$WT" commit -m "$(cat <<'EOF'
test(browser-ux): 게시판 이동을 헤더 접힘 메뉴로, 키보드 순회 기대값은 재실측 대기

390 폭의 게시판 이동 수단이 제목 메뉴에서 헤더의 접힌 메뉴로 바뀌었다.
키보드 순회 기대값은 셸 구조가 바뀌어 반드시 달라지므로 비우고, CI
실측값으로 채운다 — 추측으로 쓰지 않는다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: `DpAppShell` 의 web 전용 파라미터 정리 + 문서 갱신

**Files:**
- Modify: `packages/dp_design/lib/src/shell/dp_app_shell.dart` (compact 3파라미터 제거)
- Delete: `packages/dp_design/test/shell/dp_app_shell_adaptive_destinations_test.dart`
- Modify: `packages/dp_design/test/shell/dp_app_shell_compact_test.dart` (compact 파라미터를 쓰는 부분)
- Modify: `DESIGN.md` §5 표의 「web 셸」 열, §9 셸 구조
- Modify: `docs/community-information-architecture/handoff.md` §9.6-5 · §11 (= 핸드오프 2026-09-19 의 **L4 「frontend 큐 문서」**. 실측으로 확인한 대상: §9.6 항목 5 「키보드 순회에 셸 레일 포함」은 레일이 사라져 헤더 이야기로 바뀌어야 하고, §11 의 진단 항목 「모바일 하단 바에 여섯 항목이 보임」은 하단 바 자체가 없어져 폐기 대상이다)
- 과거 계획 문서(`docs/superpowers/plans/2026-08-03-*`·`2026-09-17-*`)는 **건드리지 않는다** — 그 시점의 기록이다.

**Interfaces:**
- Consumes: Task 6 이후 `compactDestinations` 를 넘기는 곳이 0이라는 사실.
- Produces: 파라미터 3개가 빠진 `DpAppShell`(admin 전용). `DpMobileNavigation` 은 **남는다**.

- [ ] **Step 1: 소비처가 정말 0인지 확인**

```bash
cd "$WT" && git grep -n "compactDestinations\|compactSelectedIndex\|onCompactSelect" -- '*.dart'
```

Expected: `dp_app_shell.dart` 자신과 `dp_app_shell_adaptive_destinations_test.dart`·`dp_app_shell_compact_test.dart` 만 남는다. `apps/` 아래에 하나라도 남아 있으면 **여기서 멈추고 보고한다** — 제거 전제가 깨진 것이다.

- [ ] **Step 2: 테스트에서 먼저 지운다(빨간 상태 만들기)**

`packages/dp_design/test/shell/dp_app_shell_adaptive_destinations_test.dart` 를 삭제하고, `dp_app_shell_compact_test.dart` 에서 compact 3파라미터를 쓰는 호출을 `destinations`/`selectedIndex`/`onSelect` 만 쓰도록 고친다. 그리고 admin 이 폴백 경로를 쓴다는 사실을 고정하는 테스트를 `dp_app_shell_compact_test.dart` 에 추가한다:

```dart
  testWidgets('compact 에서 destinations 가 그대로 하단 내비가 된다(admin 경로)', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: DpAppShell(
          destinations: const [
            DpDestination(icon: Icons.home, label: '대시보드'),
            DpDestination(icon: Icons.people, label: '사용자'),
          ],
          selectedIndex: 1,
          onSelect: (_) {},
          body: const Text('본문'),
        ),
      ),
    );

    final nav = tester.widget<DpMobileNavigation>(
      find.byType(DpMobileNavigation),
    );
    expect(nav.destinations.length, 2);
    expect(nav.selectedIndex, 1);
  });
```

- [ ] **Step 3: 실패 확인**

```bash
cd "$WT/packages/dp_design" && "$FLUTTER" test test/shell/dp_app_shell_compact_test.dart
```

Expected: 새 테스트는 통과하고(폴백은 이미 구현돼 있다) 나머지는 그대로 통과. 즉 이 단계는 **초록**이다 — 파라미터 제거는 리팩터링이라 빨간 테스트를 먼저 만들 대상이 아니다. 대신 Step 4 뒤에 컴파일이 깨지지 않는 것으로 안전성을 확인한다.

- [ ] **Step 4: `DpAppShell` 에서 3파라미터 제거**

`dp_app_shell.dart` 에서 `compactDestinations`·`compactSelectedIndex`·`onCompactSelect` 필드와 생성자 인자를 지우고, compact 분기를 다음으로 줄인다:

```dart
    if (compact) {
      return Scaffold(
        body: main,
        bottomNavigationBar: DpMobileNavigation(
          destinations: destinations,
          selectedIndex: selectedIndex,
          onSelect: onSelect,
        ),
      );
    }
```

클래스 문서에서 compact 목적지 관련 문단을 지우고, 대신 한 줄을 넣는다:

```dart
/// `apps/web` 은 S3-P2 부터 이 셸을 쓰지 않는다(`DpWebShell`). 지금 소비처는
/// `apps/admin` 뿐이므로 web 전용이던 compact 목적지 축약은 제거했다.
```

- [ ] **Step 5: 통과 확인**

```bash
cd "$WT" && "$DART" run melos run analyze
cd "$WT/packages/dp_design" && "$FLUTTER" test
cd "$WT/apps/admin" && "$FLUTTER" test
```

Expected: 전부 통과. admin 156건 그대로.

- [ ] **Step 6: DESIGN.md 갱신**

§5 표의 「web 셸」 열 네 줄을 바꾼다:

| 클래스 | 폭 | web 셸 |
|---|---|---|
| Compact | <600 | 상단 헤더(56px) + 햄버거 인라인 메뉴 + 1열 본문 + 푸터 |
| Medium | 600–839 | 720px 미만은 햄버거, 이상은 주 메뉴 노출. 본문 1열 |
| Expanded | 840–1239 | 상단 헤더 주 메뉴 + 중앙 본문(최대 1120) |
| Large | ≥1240 | 같음(본문이 1120 에서 멈추고 좌우 여백이 는다) |

§5 의 마지막 불릿을 바꾼다: 「하단 내비는 `DpMobileNavigation` 이 소유한다」 뒤에 「— **`apps/admin` 전용이다.** `apps/web` 은 S3-P2 부터 폭과 무관하게 하단 내비를 쓰지 않는다」를 잇는다.

§9 「셸 구조」의 3종 표 위에 절을 하나 넣는다:

```markdown
**web 과 admin 은 서로 다른 셸을 쓴다(S3-P2).**

| 앱 | 셸 | 구성 |
|---|---|---|
| `apps/web` | `DpWebShell` | `DpWebHeader`(56px, 어두운 면, 주 메뉴 + 커뮤니티 드롭다운 + 검색 트리거 + 계정 메뉴; 720px 미만은 햄버거 인라인 메뉴) · 본문(`contentMaxWidth` 1120 중앙 정렬, 맨 위에 `DpBreadcrumb`) · `DpWebFooter` |
| `apps/admin` | `DpAppShell` | `DpNavRail` + `DpChromeBar` + (compact) `DpMobileNavigation` — 아래 3종 표 그대로 |

- **새 메뉴는 `MenuAnchor` 를 직접 쓰지 않는다.** `DpMenuButton` 을 쓴다 — 웹에서 Escape 가 먹지 않고 DOM focus 가 body 로 빠지는 함정을 이미 해결한 판이다(2026-09-17 CI 실측).
- **web 의 브레드크럼은 본문 상단이다.** 크롬바 안 브레드크럼은 admin 것이다.
```

- [ ] **Step 7: frontend 큐 문서 갱신(L4)**

`docs/community-information-architecture/handoff.md`:

- §9.6 항목 5 를 바꾼다: 「키보드 순회에 셸 레일 포함(라우트 `FocusScope` 경계 재설계). 스크롤 컨테이너가 Tab 정지로 잡히는 엔진 동작은 미해결.」 → 「키보드 순회에 **셸 헤더** 포함(라우트 `FocusScope` 경계 재설계). S3-P2 에서 레일이 상단 헤더로 바뀌었고 경계 문제는 그대로다 — 순회 기대값은 그 PR 의 CI 실측으로 다시 기록했다. 스크롤 컨테이너가 Tab 정지로 잡히는 엔진 동작은 미해결.」
- §11 의 진단 항목 「모바일 하단 바에 여섯 항목이 보임」 절 전체를 지우고, 그 자리에 한 줄을 남긴다: 「(S3-P2 에서 `apps/web` 의 하단 내비가 없어졌다 — 이 증상은 더 이상 나올 수 없다. `apps/admin` 은 여전히 `DpMobileNavigation` 을 쓴다.)」
- §11 의 「Q/A를 눌렀는데 자유게시판이 선택됨」은 **남긴다** — 헤더 드롭다운에서도 같은 해석기(`shellDestinationIndexFor`)를 쓰므로 여전히 유효하다. 다만 첫 줄의 「레일」을 「헤더」로 바꾼다.

- [ ] **Step 8: 커밋**

```bash
git -C "$WT" add packages/dp_design/lib/src/shell/dp_app_shell.dart packages/dp_design/test/shell/dp_app_shell_compact_test.dart DESIGN.md docs/community-information-architecture/handoff.md
git -C "$WT" rm packages/dp_design/test/shell/dp_app_shell_adaptive_destinations_test.dart
git -C "$WT" commit -m "$(cat <<'EOF'
refactor(dp_design): DpAppShell 의 web 전용 compact 목적지 축약 제거 + 문서 갱신

실측: apps/admin 은 compactDestinations 를 넘기지 않고 destinations 폴백으로
DpMobileNavigation 을 쓴다. 그러므로 DpMobileNavigation 은 남기고 web 만 쓰던
파라미터 3개만 지운다. DESIGN.md §5·§9 에 web/admin 이 다른 셸을 쓴다는 사실을
적고, 커뮤니티 IA 핸드오프의 후속 큐(§9.6-5)와 진단 절(§11)에서 사라진 레일·
하단 바를 정리했다(2026-09-19 핸드오프의 L4).

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: 로컬 전 게이트 → PR → CI 실측으로 `browser-ux` 기대값 확정

**Files:**
- Modify: `tools/browser_ux/expectations.json` (CI 실측값으로 채움)

**Interfaces:**
- Consumes: Task 1~8 의 모든 커밋.
- Produces: develop 에 머지된 셸 교체.

- [ ] **Step 1: 로컬 전 게이트**

```bash
cd "$WT" && "$DART" format --set-exit-if-changed .
cd "$WT" && "$DART" run melos run analyze
cd "$WT" && "$DART" run melos run test
```

Expected: format 무변경 · analyze 4패키지 무이슈 · 전체 테스트 통과(dp_design 은 신규 23건만큼 늘어난다). `dp_code_font_test.dart` 1건 실패는 CRLF 탓이므로 무시한다.

- [ ] **Step 2: PR 생성**

```bash
git -C "$WT" push -u origin feat/s3-p2-dp-web-shell
cd "$WT" && gh pr create --base develop --head feat/s3-p2-dp-web-shell \
  --title "feat(web): S3-P2 — DpWebShell 신설(상단 헤더·햄버거·계정 메뉴·푸터)로 셸 교체" \
  --body-file <(cat <<'EOF'
스펙 §7 의 P2. `apps/web` 의 셸을 「다크 레일 + 크롬바 + 하단 내비」에서 「상단 헤더 + 중앙 본문 + 푸터」로 바꾼다. 시안 https://claude.ai/artifact/DWi8kMV6QcAzBEQwbrNPNd (Version 2) 의 `.hd`/`.mnav`/`.ft`/`.main` 을 그대로 옮겼다.

## 신설 (packages/dp_design)

- `DpMenuButton` — 웹에서 Escape 가 먹지 않고 DOM focus 가 body 로 빠지는 `MenuAnchor` 함정을 이미 해결한 판(`dp_page_header` 의 `_TitleMenuState`)을 재사용 가능한 위젯으로 뽑았다. 핸드오프 2026-09-19 의 **L3(`_AccountMenu` a11y)를 여기서 흡수**한다.
- `DpWebHeader` · `DpWebFooter` · `DpBreadcrumb` · `DpWebShell`.

## 바뀐 것 (apps/web)

- 목적지 모델이 index → **id(경로)** 기반. `shellDestinationIndexFor`·`breadcrumbFor` 는 그대로 두고 얇은 매핑만 얹었다.
- 브레드크럼이 크롬바에서 **본문 상단**으로, 오류 신고·문의가 크롬바 액션에서 **푸터 링크**로.
- 레일 펼침 상태가 사라져 `AppShellView` 가 `StatelessWidget` 이 됐다.

## 바뀌지 않은 것

- `apps/admin` — `DpAppShell`·`DpNavRail`·`DpChromeBar`·`DpMobileNavigation` 그대로. 실측상 admin 은 `compactDestinations` 를 넘기지 않고 `destinations` 폴백을 쓰므로 `DpMobileNavigation` 을 남겼고, web 만 쓰던 파라미터 3개만 지웠다.
- 화면 파일 0개. 공용 위젯 웹화는 P3, 화면군 개편은 P4.

## 알고 고른 것

- **푸터는 셸 하단 고정**이다(사용자 결정 2026-09-26). 시안은 내용 끝에 붙지만 Flutter 는 화면마다 자기 스크롤뷰를 가져서 같은 거동을 얻으려면 모든 화면을 고쳐야 한다 — P4 의 일이다. compact 에서도 약 45px 이 항상 붙는다.
- **계정 버튼은 아이콘 + ▾ 만**이다. 시안의 아바타·이름은 P4 에서 계정 화면군과 같은 컨트롤러로 붙인다.

## 기준선

ET13 시각 기준선은 이 PR 로 전부 달라진다. **재승인은 P5(사람 단계)** 이고 이 PR 의 `produce-atomic-pair` 는 증거를 만들기만 한다(스펙 §9). `browser-ux` 의 `keyboard_traversal` 기대값은 셸 구조가 바뀌어 반드시 달라지므로 비워 두고 **이 PR 의 CI 실측값**으로 채운다.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)
```

- [ ] **Step 3: CI 실측 → `keyboard_traversal` 기대값 기록**

첫 실행에서 `browser-ux` 의 `keyboard-traversal` 이 `expectations.keyboard_traversal.community_desktop is not recorded yet` 으로 실패하는 것이 **정상**이다. 리포트 아티팩트에서 실측 순서를 읽는다:

```bash
cd "$WT" && gh run list --branch feat/s3-p2-dp-web-shell --limit 5
gh run download <run-id> -n browser-ux-report -D /tmp/bux
node -e "const r=require('/tmp/bux/report.json');const s=r.scenarios.find(x=>x.id==='keyboard-traversal');console.log(JSON.stringify(s.detail.sequence.slice(0,6),null,2))"
```

읽은 배열을 `expectations.json` 의 `keyboard_traversal.community_desktop` 에 넣고, `recorded_from` 을 이 브랜치의 부모 커밋(`git -C "$WT" rev-parse HEAD~1`)으로 채우고, `notes` 에 「S3-P2 상단 헤더 셸에서 실측(`<run-id>`)」을 적는다. **아티팩트 이름이 다르면** `gh run view <run-id> --log` 로 실패 단계의 출력에서 `sequence` 를 읽는다.

- [ ] **Step 4: 기대값 커밋 후 재실행**

```bash
git -C "$WT" add tools/browser_ux/expectations.json
git -C "$WT" commit -m "$(cat <<'EOF'
test(browser-ux): 상단 헤더 셸의 키보드 순회 기대값을 CI 실측으로 기록

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git -C "$WT" push
```

- [ ] **Step 5: CI 전 잡 녹색 확인**

```bash
cd "$WT" && gh pr checks --watch
```

Expected: `analyze-test` · `browser-ux` · `perf-gate` · `web-image-config-contract`(on/off) · `produce-atomic-pair` 전부 pass. `perf-gate` 는 약 23분 걸린다. **`browser-ux` 가 `axe` 나 `overflow-and-targets` 에서 실패하면 기대값을 낮추지 말고 헤더·푸터를 고친다** — 그 잡이 이 작업의 진짜 판정자다.

- [ ] **Step 6: 리뷰 → 머지**

`superpowers:requesting-code-review` 로 신선한 컨텍스트 리뷰를 받은 뒤 지적을 반영하고, CI 가 다시 녹색이면 merge commit 으로 develop 에 머지한다. 그 뒤 원격·로컬 브랜치와 워크트리를 정리한다.

```bash
cd "$WT" && gh pr merge --merge
cd /d/workspace/dpa/devpath-frontend
git push origin --delete feat/s3-p2-dp-web-shell
git worktree remove --force "D:/workspace/dpa/.worktrees/frontend-s3p2-20260926" || rm -rf "D:/workspace/dpa/.worktrees/frontend-s3p2-20260926"
git worktree prune && git branch -D feat/s3-p2-dp-web-shell
```
