# S3-P3 공용 위젯 웹화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `dp_design` 에 시안의 웹 문법 프리미티브(패널·표·구분선 목록·링크·상태 텍스트)를 세우고, `DpListRow` 를 카드에서 구분선 행으로 교체하며, 시안에 없는 `DpPageHeader.titleMenu` 와 커뮤니티 FAB 을 제거한다.

**Architecture:** 전부 `packages/dp_design` 안의 순수 표현부 위젯이다 — go_router·Riverpod 비의존, 색·간격·반경은 계약 2.0.0 토큰(`DpColors`·`DpSpacing`·`DpRadius`·`DpDensity`)에서만 가져온다. 화면 레이아웃 재구성(`cols`/`side`/`narrow`, Material `Card(` 25곳 교체)은 **P4** 이며 이 계획의 범위가 아니다. 소비처는 위젯에서 파라미터를 없애 컴파일이 강제하는 3파일만 건드린다.

**Tech Stack:** Flutter 3.44.1(CI 핀) · Dart pub workspaces + melos 7 · `flutter_test` 위젯 테스트 · CI `analyze-test`·`browser-ux`·`perf-gate`·`produce-atomic-pair`

**Spec:** `docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` (§5.3 웹 문법, §7 P3, §8 게이트)

**시안 정본:** Artifact `https://claude.ai/artifact/DWi8kMV6QcAzBEQwbrNPNd` (Version 2). 아래 치수는 그 CSS 에서 직접 옮긴 값이며, 프레임 기본값이 `data-hit="24"`(촘촘) 이므로 **행 세로 여백은 8** 이다.

## Global Constraints

- **로컬 Flutter 가 CI 와 다르면 CI 를 믿는다.** CI 는 `3.44.1` 핀이다. 로컬이 3.47.x 이면 `flutter analyze` 가 `unawaited_return_in_try_block` 같은 신규 린트를 내고, `flutter test`/`analyze` 실행이 `apps/*/analysis_options.yaml` 과 루트 `pubspec.lock` 을 제멋대로 고쳐 놓는다. **그 4개 파일은 절대 커밋하지 않는다** — 커밋 전 `git status --porcelain` 으로 확인하고 `git checkout --` 로 되돌린다.
- **색은 `context.dpColors` 에서만** 가져온다. `Colors.*` 하드코딩 금지(테마 대비 계약이 깨진다).
- **치수는 토큰 상수로만**: `DpSpacing.xs/sm/md/lg/xl` = 4/8/12/16/24, `DpDensity.rowPadding` = 8, `DpDensity.controlHeight` = 30, `DpDensity.minTarget` = 24, `DpRadius.chip/button/card` = 4/6/8. 리터럴 숫자를 새로 쓰지 않는다.
- **모든 새 위젯은 `packages/dp_design/lib/dp_design.dart` 에 export** 한다. 빠뜨리면 소비처가 `src/` 를 직접 import 하게 되어 캡슐화가 깨진다.
- **커밋 메시지는 Conventional Commits**, 본문 끝에 `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.
- **브랜치**: `develop` 에서 `feat/s3-p3-web-widgets` 를 분기하고 `develop` 으로 PR 한다. `main` 직접 금지.
- **테스트 먼저.** 구현 전에 실패를 눈으로 본다. 통과한 채로 시작한 테스트는 무효다.

## Review Focus

스펙이 함의하지만 어느 Task 의 기본 테스트도 건드리지 않는, 사람을 물 가능성이 높은 다섯 가지. 각 줄의 테스트는 해당 코드를 가진 Task 안에 스텝으로 들어가 있다.

1. **긴 제목이 숫자 칼럼을 밀어낸다** — 표 첫 칼럼은 줄바꿈해야 하고 숫자 칼럼은 `nowrap` 으로 폭을 지켜야 한다. (Task 4 Step 6)
2. **행이 0개인 표** — 헤더만 남은 빈 표는 「목록이 비었다」를 전달하지 못한다. `empty` 위젯으로 대체돼야 한다. (Task 4 Step 8)
3. **390px 에서 본문이 가로로 스크롤된다** — 표만 자체 스크롤해야 하고 페이지 본문은 절대 넘치면 안 된다. (Task 4 Step 10)
4. **스크린리더가 행을 한 덩어리로 읽는다** — 표 행이 단일 시맨틱 노드로 병합되면 칼럼 값이 사라진다. 2026-09-26 P2 에서 같은 계열의 결함을 겪었다. (Task 4 Step 12)
5. **다크 테마에서 hover 배경과 구분선이 안 보인다** — 두 색 모두 테마별로 다른 토큰이므로 라이트에서만 확인하면 놓친다. (Task 1 Step 6, Task 4 Step 14)

---

## File Structure

| 파일 | 책임 | Task |
|---|---|---|
| `packages/dp_design/lib/src/layout/dp_panel.dart` | 시안 `.panel` — surface + 1px 테두리 + 반경 8, 선택적 제목행 | 1 |
| `packages/dp_design/lib/src/content/dp_link.dart` | 시안 `.ttl`·`.lk` 두 링크 변형 | 2 |
| `packages/dp_design/lib/src/states/dp_status_text.dart` | 시안 `.st ok/no/now` 상태 텍스트 | 3 |
| `packages/dp_design/lib/src/data/dp_web_table.dart` | 시안 `<table>` — 헤더행 + 구분선 + hover + 숫자 칼럼 + 가로 스크롤 | 4 |
| `packages/dp_design/lib/src/data/dp_list_lines.dart` | 시안 `.list` — 자식 사이 구분선 | 5 |
| `packages/dp_design/lib/src/data/dp_row_line.dart` | 시안 `.rowline` — 좌 라벨/설명 + 우 컨트롤 | 6 |
| `packages/dp_design/lib/src/data/dp_key_values.dart` | 시안 `.kv` — dt/dd 2열 | 7 |
| `packages/dp_design/lib/src/data/dp_list_row.dart` | **수정** — 카드·accent 제거, 구분선 행으로 | 8 |
| `packages/dp_design/lib/src/layout/dp_page_header.dart` | **수정** — `titleMenu`·`titleMenuTooltip` 제거 | 9 |
| `apps/web/lib/src/features/community/presentation/web_community_board_projection.dart` | **수정** — titleMenu·accentColor·`communityRowAccent` 제거, 헤더에 작성 액션 추가 | 9·10 |
| `apps/web/lib/src/features/community/presentation/community_home_page.dart` | **수정** — FAB 제거, accentColor 제거 | 9·10 |
| `DESIGN.md` | **수정** — §3 에 새 프리미티브 등재 | 11 |

---

### Task 1: `DpPanel` — 시안 `.panel`

**Files:**
- Create: `packages/dp_design/lib/src/layout/dp_panel.dart`
- Modify: `packages/dp_design/lib/dp_design.dart` (export 추가)
- Test: `packages/dp_design/test/layout/dp_panel_test.dart`

**Interfaces:**
- Consumes: `context.dpColors`(`surface`·`border`·`textPrimary`), `DpSpacing`, `DpRadius`
- Produces: `DpPanel({Key? key, Widget? title, required Widget child, EdgeInsetsGeometry? padding})` — `title` 이 있으면 제목행(패딩 12×16, 하단 1px 구분선)을 그리고 그 아래 `child`. `padding` 기본 `EdgeInsets.zero`(표·목록이 자체 패딩을 갖기 때문).

- [ ] **Step 1: 실패 테스트를 쓴다**

`packages/dp_design/test/layout/dp_panel_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host(Widget child, {Brightness brightness = Brightness.light}) =>
    MaterialApp(
      theme: brightness == Brightness.light ? DpTheme.light() : DpTheme.dark(),
      home: Scaffold(body: child),
    );

BoxDecoration _decorationOf(WidgetTester tester) {
  final container = tester.widget<Container>(
    find
        .descendant(
          of: find.byType(DpPanel),
          matching: find.byType(Container),
        )
        .first,
  );
  return container.decoration! as BoxDecoration;
}

void main() {
  testWidgets('표면색·1px 테두리·반경 8 의 컨테이너다', (tester) async {
    await tester.pumpWidget(_host(const DpPanel(child: Text('본문'))));

    final d = _decorationOf(tester);
    final c = DpColors.light;
    expect(d.color, c.surface);
    expect((d.border! as Border).top.width, 1);
    expect((d.border! as Border).top.color, c.border);
    expect(d.borderRadius, BorderRadius.circular(DpRadius.card));
  });

  testWidgets('title 이 없으면 제목행을 그리지 않는다', (tester) async {
    await tester.pumpWidget(_host(const DpPanel(child: Text('본문'))));

    expect(find.byKey(const ValueKey('dp-panel-title')), findsNothing);
    expect(find.text('본문'), findsOneWidget);
  });

  testWidgets('title 이 있으면 제목행과 하단 구분선을 그린다', (tester) async {
    await tester.pumpWidget(
      _host(const DpPanel(title: Text('이번 주 과제'), child: Text('본문'))),
    );

    final header = tester.widget<Container>(
      find.byKey(const ValueKey('dp-panel-title')),
    );
    final d = header.decoration! as BoxDecoration;
    expect(d.border!.bottom.width, 1);
    expect(d.border!.bottom.color, DpColors.light.border);
    expect(header.padding, const EdgeInsets.symmetric(
      vertical: DpSpacing.md,
      horizontal: DpSpacing.lg,
    ));
    expect(find.text('이번 주 과제'), findsOneWidget);
  });

  testWidgets('제목은 시맨틱스에서 헤더로 노출된다', (tester) async {
    final handle = tester.ensureSemantics();
    await tester.pumpWidget(
      _host(const DpPanel(title: Text('진행'), child: Text('본문'))),
    );

    expect(
      tester.getSemantics(find.text('진행')),
      matchesSemantics(label: '진행', isHeader: true),
    );
    handle.dispose();
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd packages/dp_design && flutter test test/layout/dp_panel_test.dart
```

기대: 4건 전부 FAIL — `Undefined name 'DpPanel'` 컴파일 오류.

- [ ] **Step 3: 최소 구현을 쓴다**

`packages/dp_design/lib/src/layout/dp_panel.dart`:

```dart
import 'package:flutter/material.dart';

import '../theme/dp_colors.dart';
import '../theme/dp_spacing.dart';

/// 웹 문법 패널(시안 `.panel`) — 표면 + 1px 테두리 + 반경 8 컨테이너.
///
/// 웹 화면에서 Material `Card` 를 대신한다. 그림자를 쓰지 않는다 —
/// 시안의 면 구분은 테두리 한 겹뿐이다.
///
/// [padding] 기본값이 0 인 이유: 이 패널의 주 내용물인 표·목록은 행마다
/// 자기 패딩을 갖고 구분선이 패널 폭 전체를 가로질러야 한다. 바깥에서
/// 패딩을 주면 구분선이 안쪽으로 밀려 시안과 달라진다.
class DpPanel extends StatelessWidget {
  const DpPanel({super.key, this.title, required this.child, this.padding});

  /// 있으면 하단 구분선을 가진 제목행을 그린다.
  final Widget? title;
  final Widget child;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final text = Theme.of(context).textTheme;

    return Container(
      decoration: BoxDecoration(
        color: c.surface,
        border: Border.all(color: c.border),
        borderRadius: BorderRadius.circular(DpRadius.card),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (title != null)
            Container(
              key: const ValueKey('dp-panel-title'),
              padding: const EdgeInsets.symmetric(
                vertical: DpSpacing.md,
                horizontal: DpSpacing.lg,
              ),
              decoration: BoxDecoration(
                border: Border(bottom: BorderSide(color: c.border)),
              ),
              child: Semantics(
                header: true,
                child: DefaultTextStyle.merge(
                  style: text.titleSmall?.copyWith(color: c.textPrimary),
                  child: title!,
                ),
              ),
            ),
          Padding(padding: padding ?? EdgeInsets.zero, child: child),
        ],
      ),
    );
  }
}
```

`packages/dp_design/lib/dp_design.dart` 의 `export 'src/layout/dp_page_header.dart';` 바로 아래에 추가:

```dart
export 'src/layout/dp_panel.dart';
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd packages/dp_design && flutter test test/layout/dp_panel_test.dart
```

기대: `+4: All tests passed!`

- [ ] **Step 5: 다크 테마 대비 테스트를 추가한다 (Review Focus 5)**

같은 파일 끝에 추가:

```dart
  testWidgets('다크 테마에서도 표면·테두리가 각 테마 토큰을 쓴다', (tester) async {
    await tester.pumpWidget(
      _host(const DpPanel(child: Text('본문')), brightness: Brightness.dark),
    );

    final d = _decorationOf(tester);
    expect(d.color, DpColors.dark.surface);
    expect((d.border! as Border).top.color, DpColors.dark.border);
    // 라이트 값이 새어 들어오지 않았는지 못 박는다.
    expect(d.color, isNot(DpColors.light.surface));
  });
```

- [ ] **Step 6: 실패 → 통과를 확인한다**

```bash
cd packages/dp_design && flutter test test/layout/dp_panel_test.dart
```

`DpColors.dark` 가 이미 있으므로 이 테스트는 **바로 통과해야 한다**. 통과하면 다크 경로가 구현돼 있다는 뜻이므로 그대로 둔다. 만약 FAIL 이면 `DpTheme.dark()` 가 `DpColors.dark` 를 주입하지 않는 것이므로 그 원인을 먼저 규명한다(테스트를 고치지 않는다).

- [ ] **Step 7: 커밋**

```bash
git add packages/dp_design/lib/src/layout/dp_panel.dart \
        packages/dp_design/lib/dp_design.dart \
        packages/dp_design/test/layout/dp_panel_test.dart
git commit -m "$(cat <<'EOF'
feat(dp_design): 웹 문법 패널 DpPanel 신설

시안 `.panel` — 표면 + 1px 테두리 + 반경 8, 선택적 제목행(12×16 + 하단
구분선). 웹 화면의 Material Card 를 대신한다. 그림자 없음.

padding 기본값을 0 으로 둔다 — 표·목록의 구분선이 패널 폭 전체를
가로질러야 하기 때문이다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `DpLink` — 시안 `.ttl` / `.lk`

**Files:**
- Create: `packages/dp_design/lib/src/content/dp_link.dart`
- Modify: `packages/dp_design/lib/dp_design.dart`
- Test: `packages/dp_design/test/content/dp_link_test.dart`

**Interfaces:**
- Consumes: `context.dpColors`(`textPrimary`·`primaryText`)
- Produces:
  - `DpLink.title({Key? key, required String text, VoidCallback? onTap, int? maxLines})` — 시안 `.ttl`: 기본 `textPrimary` + `FontWeight.w600` + 밑줄 없음, hover 시 `primaryText` + 밑줄.
  - `DpLink.inline({Key? key, required String text, VoidCallback? onTap})` — 시안 `.lk`: 항상 `primaryText`, 밑줄 오프셋 3.
  - 두 생성자 모두 같은 `DpLink` 클래스이며 내부 `_DpLinkVariant { title, inline }` 로 갈린다.

- [ ] **Step 1: 실패 테스트를 쓴다**

`packages/dp_design/test/content/dp_link_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host(Widget child) =>
    MaterialApp(theme: DpTheme.light(), home: Scaffold(body: child));

TextStyle _styleOf(WidgetTester tester) =>
    tester.widget<Text>(find.byType(Text)).style!;

Future<void> _hover(WidgetTester tester, Finder target) async {
  final gesture = await tester.createGesture(kind: PointerDeviceKind.mouse);
  await gesture.addPointer(location: Offset.zero);
  addTearDown(gesture.removePointer);
  await gesture.moveTo(tester.getCenter(target));
  await tester.pump();
}

void main() {
  testWidgets('title 변형은 기본 상태에서 본문색·600·밑줄 없음', (tester) async {
    await tester.pumpWidget(
      _host(DpLink.title(text: '오늘 배운 것 공유', onTap: () {})),
    );

    final s = _styleOf(tester);
    expect(s.color, DpColors.light.textPrimary);
    expect(s.fontWeight, FontWeight.w600);
    expect(s.decoration, TextDecoration.none);
  });

  testWidgets('title 변형은 hover 하면 강조색 + 밑줄이 된다', (tester) async {
    await tester.pumpWidget(
      _host(DpLink.title(text: '오늘 배운 것 공유', onTap: () {})),
    );

    await _hover(tester, find.byType(DpLink));

    final s = _styleOf(tester);
    expect(s.color, DpColors.light.primaryText);
    expect(s.decoration, TextDecoration.underline);
  });

  testWidgets('inline 변형은 기본부터 강조색·밑줄·오프셋 3', (tester) async {
    await tester.pumpWidget(
      _host(DpLink.inline(text: '경로 전체 보기', onTap: () {})),
    );

    final s = _styleOf(tester);
    expect(s.color, DpColors.light.primaryText);
    expect(s.decoration, TextDecoration.underline);
    expect(s.decorationStyle, isNull);
    expect(s.height, isNull);
  });

  testWidgets('누르면 onTap 이 불리고 시맨틱스는 link 다', (tester) async {
    var taps = 0;
    final handle = tester.ensureSemantics();
    await tester.pumpWidget(
      _host(DpLink.inline(text: '이용약관', onTap: () => taps++)),
    );

    await tester.tap(find.byType(DpLink));
    expect(taps, 1);
    expect(tester.getSemantics(find.byType(DpLink)), matchesSemantics(
      label: '이용약관',
      isLink: true,
      hasTapAction: true,
    ));
    handle.dispose();
  });

  testWidgets('onTap 이 null 이면 링크가 아니라 그냥 글이다', (tester) async {
    final handle = tester.ensureSemantics();
    await tester.pumpWidget(_host(DpLink.title(text: '삭제된 글')));

    expect(tester.getSemantics(find.byType(DpLink)), matchesSemantics(
      label: '삭제된 글',
    ));
    handle.dispose();
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd packages/dp_design && flutter test test/content/dp_link_test.dart
```

기대: `Undefined name 'DpLink'` 컴파일 오류로 전건 FAIL.

- [ ] **Step 3: 최소 구현을 쓴다**

`packages/dp_design/lib/src/content/dp_link.dart`:

```dart
import 'package:flutter/material.dart';

import '../theme/dp_colors.dart';

enum _DpLinkVariant { title, inline }

/// 웹 문법 링크(시안 `.ttl`·`.lk`).
///
/// - [DpLink.title] = `.ttl`: 목록·표의 제목. 평소엔 본문색 600 에 밑줄이 없고,
///   hover 에서만 강조색 + 밑줄이 된다(표 한 화면에 제목이 수십 개라 항상
///   밑줄이면 지면이 시끄럽다).
/// - [DpLink.inline] = `.lk`: 문장 안 링크. 밑줄이 항상 있어야 색만으로
///   링크를 구분하지 않게 된다(WCAG 1.4.1).
class DpLink extends StatefulWidget {
  const DpLink._({
    super.key,
    required this.text,
    required this.variant,
    this.onTap,
    this.maxLines,
  });

  const DpLink.title({Key? key, required String text, VoidCallback? onTap,
    int? maxLines})
      : this._(
          key: key,
          text: text,
          variant: _DpLinkVariant.title,
          onTap: onTap,
          maxLines: maxLines,
        );

  const DpLink.inline({Key? key, required String text, VoidCallback? onTap})
      : this._(key: key, text: text, variant: _DpLinkVariant.inline,
          onTap: onTap);

  final String text;
  final _DpLinkVariant variant;
  final VoidCallback? onTap;
  final int? maxLines;

  @override
  State<DpLink> createState() => _DpLinkState();
}

class _DpLinkState extends State<DpLink> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final base = Theme.of(context).textTheme.bodyMedium;
    final inline = widget.variant == _DpLinkVariant.inline;
    final emphasised = inline || _hovered;

    final style = (base ?? const TextStyle()).copyWith(
      color: emphasised ? c.primaryText : c.textPrimary,
      fontWeight: inline ? null : FontWeight.w600,
      decoration: emphasised ? TextDecoration.underline : TextDecoration.none,
      decorationColor: emphasised ? c.primaryText : null,
    );

    final label = Text(
      widget.text,
      style: style,
      maxLines: widget.maxLines,
      overflow: widget.maxLines == null ? null : TextOverflow.ellipsis,
    );

    if (widget.onTap == null) {
      return Semantics(label: widget.text, child: ExcludeSemantics(child: label));
    }

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: Semantics(
        link: true,
        label: widget.text,
        onTap: widget.onTap,
        child: GestureDetector(
          onTap: widget.onTap,
          child: ExcludeSemantics(child: label),
        ),
      ),
    );
  }
}
```

`dp_design.dart` 에 추가(기존 `export 'src/content/dp_markdown.dart';` 옆):

```dart
export 'src/content/dp_link.dart';
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd packages/dp_design && flutter test test/content/dp_link_test.dart
```

기대: `+5: All tests passed!`

- [ ] **Step 5: 커밋**

```bash
git add packages/dp_design/lib/src/content/dp_link.dart \
        packages/dp_design/lib/dp_design.dart \
        packages/dp_design/test/content/dp_link_test.dart
git commit -m "$(cat <<'EOF'
feat(dp_design): 웹 문법 링크 DpLink 신설(title·inline)

시안 `.ttl`(제목 링크 — 평소 본문색 600·밑줄 없음, hover 에서 강조색+밑줄)과
`.lk`(문장 안 링크 — 항상 강조색+밑줄) 두 변형.

inline 에 밑줄을 상시로 두는 이유는 색만으로 링크를 구분하지 않기
위해서다(WCAG 1.4.1). title 을 hover 로만 두는 이유는 표 한 화면에 제목이
수십 개라 상시 밑줄이면 지면이 시끄럽기 때문이다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `DpStatusText` — 시안 `.st`

**Files:**
- Create: `packages/dp_design/lib/src/states/dp_status_text.dart`
- Modify: `packages/dp_design/lib/dp_design.dart`
- Test: `packages/dp_design/test/states/dp_status_text_test.dart`

**Interfaces:**
- Consumes: `context.dpColors`(`success`·`textSecondary`·`primaryTextStrong`)
- Produces: `DpStatusText({Key? key, required String text, required DpStatusTone tone})` 과 `enum DpStatusTone { done, idle, current }`. 12px·`FontWeight.w600`·`softWrap: false`.

- [ ] **Step 1: 실패 테스트를 쓴다**

`packages/dp_design/test/states/dp_status_text_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host(Widget child) =>
    MaterialApp(theme: DpTheme.light(), home: Scaffold(body: child));

Text _text(WidgetTester tester) => tester.widget<Text>(find.byType(Text));

void main() {
  testWidgets('done 은 success 색', (tester) async {
    await tester.pumpWidget(
      _host(const DpStatusText(text: '✓ 완료', tone: DpStatusTone.done)),
    );
    expect(_text(tester).style!.color, DpColors.light.success);
  });

  testWidgets('idle 은 보조 텍스트색', (tester) async {
    await tester.pumpWidget(
      _host(const DpStatusText(text: '대기', tone: DpStatusTone.idle)),
    );
    expect(_text(tester).style!.color, DpColors.light.textSecondary);
  });

  testWidgets('current 는 강조 진한색', (tester) async {
    await tester.pumpWidget(
      _host(const DpStatusText(text: '● 다음', tone: DpStatusTone.current)),
    );
    expect(_text(tester).style!.color, DpColors.light.primaryTextStrong);
  });

  testWidgets('12px·600 이고 줄바꿈하지 않는다', (tester) async {
    await tester.pumpWidget(
      _host(const DpStatusText(text: '✓ 해결됨', tone: DpStatusTone.done)),
    );
    final t = _text(tester);
    expect(t.style!.fontSize, 12);
    expect(t.style!.fontWeight, FontWeight.w600);
    expect(t.softWrap, isFalse);
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd packages/dp_design && flutter test test/states/dp_status_text_test.dart
```

기대: `Undefined name 'DpStatusText'` 로 4건 FAIL.

- [ ] **Step 3: 최소 구현을 쓴다**

`packages/dp_design/lib/src/states/dp_status_text.dart`:

```dart
import 'package:flutter/material.dart';

import '../theme/dp_colors.dart';

/// 상태 문구의 의미 축(시안 `.st ok/no/now`).
enum DpStatusTone {
  /// 끝난 것 — `.st.ok`
  done,

  /// 아직인 것 — `.st.no`
  idle,

  /// 지금 할 것 — `.st.now`
  current,
}

/// 표·목록의 상태 칼럼(시안 `.st`). 12px·600·줄바꿈 없음.
///
/// 색만으로 의미를 전달하지 않도록 호출부가 기호를 함께 넣는다
/// (`'✓ 완료'`·`'● 다음'`) — 이 위젯은 기호를 만들지 않는다.
class DpStatusText extends StatelessWidget {
  const DpStatusText({super.key, required this.text, required this.tone});

  final String text;
  final DpStatusTone tone;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final color = switch (tone) {
      DpStatusTone.done => c.success,
      DpStatusTone.idle => c.textSecondary,
      DpStatusTone.current => c.primaryTextStrong,
    };

    return Text(
      text,
      softWrap: false,
      overflow: TextOverflow.clip,
      style: TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        color: color,
      ),
    );
  }
}
```

`dp_design.dart` 의 states 묶음에 추가:

```dart
export 'src/states/dp_status_text.dart';
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd packages/dp_design && flutter test test/states/dp_status_text_test.dart
```

기대: `+4: All tests passed!`

- [ ] **Step 5: 커밋**

```bash
git add packages/dp_design/lib/src/states/dp_status_text.dart \
        packages/dp_design/lib/dp_design.dart \
        packages/dp_design/test/states/dp_status_text_test.dart
git commit -m "$(cat <<'EOF'
feat(dp_design): 상태 텍스트 DpStatusText 신설

시안 `.st ok/no/now` — 12px·600·줄바꿈 없음, 색은 success·textSecondary·
primaryTextStrong 세 축.

기호(✓·●)는 호출부가 문자열에 넣는다. 색만으로 의미를 전달하지 않기
위한 것이고, 이 위젯이 기호를 만들면 문구를 바꿀 수 없어진다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `DpWebTable` — 시안 `<table>`

이 계획에서 가장 큰 Task 다. Review Focus 다섯 줄 중 네 줄이 여기 있다.

**Files:**
- Create: `packages/dp_design/lib/src/data/dp_web_table.dart`
- Modify: `packages/dp_design/lib/dp_design.dart`
- Test: `packages/dp_design/test/data/dp_web_table_test.dart`

**Interfaces:**
- Consumes: `context.dpColors`(`border`·`surfaceMuted`·`textFaint`·`textSecondary`), `DpSpacing`, `DpDensity`
- Produces:
  - `typedef DpTableColumn = ({String label, double? width, bool numeric});` — `width: null` 이면 남는 폭을 나눠 갖고(`Expanded`), 숫자면 우측 정렬 + tabular 숫자 + `textSecondary`.
  - `typedef DpTableRowSpec = ({List<Widget> cells, VoidCallback? onTap});`
  - `DpWebTable({Key? key, required List<DpTableColumn> columns, required List<DpTableRowSpec> rows, double minWidth = 640, Widget? empty})`

**`DpDataTable` 을 쓰지 않는 이유**(이 판단을 뒤집지 말 것): 그쪽은 `data_table_2` 래퍼이고 `TableBorder.all` 로 **세로 테두리**를 그린다. 시안의 표는 가로 구분선만 있고 세로선이 없다. admin 4화면이 `DpDataTable` 을 쓰고 있으므로 그 위젯은 그대로 둔다.

- [ ] **Step 1: 기본 구조 실패 테스트를 쓴다**

`packages/dp_design/test/data/dp_web_table_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host(Widget child, {double width = 1120,
    Brightness brightness = Brightness.light}) =>
    MaterialApp(
      theme: brightness == Brightness.light ? DpTheme.light() : DpTheme.dark(),
      home: Scaffold(
        body: Center(child: SizedBox(width: width, child: child)),
      ),
    );

const _columns = <DpTableColumn>[
  (label: '제목', width: null, numeric: false),
  (label: '댓글', width: 72, numeric: true),
  (label: '작성', width: 96, numeric: true),
];

DpWebTable _table({
  List<DpTableRowSpec>? rows,
  Widget? empty,
  double minWidth = 640,
}) => DpWebTable(
  columns: _columns,
  minWidth: minWidth,
  empty: empty,
  rows: rows ??
      const [
        (cells: [Text('오늘 배운 것 공유'), Text('1'), Text('3시간 전')], onTap: null),
        (cells: [Text('배포 자동화 팁'), Text('3'), Text('어제')], onTap: null),
      ],
);

void main() {
  testWidgets('헤더 라벨과 각 행의 셀을 모두 그린다', (tester) async {
    await tester.pumpWidget(_host(_table()));

    expect(find.text('제목'), findsOneWidget);
    expect(find.text('댓글'), findsOneWidget);
    expect(find.text('오늘 배운 것 공유'), findsOneWidget);
    expect(find.text('배포 자동화 팁'), findsOneWidget);
  });

  testWidgets('행마다 하단 구분선이 있고 마지막 행에는 없다', (tester) async {
    await tester.pumpWidget(_host(_table()));

    final rows = tester
        .widgetList<Container>(find.byKey(const ValueKey('dp-web-table-row')))
        .toList();
    expect(rows.length, 2);
    final first = rows.first.decoration! as BoxDecoration;
    final last = rows.last.decoration! as BoxDecoration;
    expect(first.border!.bottom.width, 1);
    expect(first.border!.bottom.color, DpColors.light.border);
    expect(last.border, isNull);
  });

  testWidgets('행 세로 여백은 DpDensity.rowPadding, 가로는 DpSpacing.lg', (tester) async {
    await tester.pumpWidget(_host(_table()));

    final row = tester.widget<Container>(
      find.byKey(const ValueKey('dp-web-table-row')).first,
    );
    expect(row.padding, const EdgeInsets.symmetric(
      vertical: DpDensity.rowPadding,
      horizontal: DpSpacing.lg,
    ));
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd packages/dp_design && flutter test test/data/dp_web_table_test.dart
```

기대: `Undefined name 'DpWebTable'` 로 3건 FAIL.

- [ ] **Step 3: 최소 구현을 쓴다**

`packages/dp_design/lib/src/data/dp_web_table.dart`:

```dart
import 'dart:ui' show FontFeature;

import 'package:flutter/material.dart';

import '../theme/dp_colors.dart';
import '../theme/dp_spacing.dart';

/// 표의 칼럼 정의.
///
/// [width] 가 null 이면 남는 폭을 다른 유연 칼럼과 나눠 갖는다.
/// [numeric] 이면 우측 정렬 + 등폭 숫자 + 보조 텍스트색이고 줄바꿈하지 않는다.
typedef DpTableColumn = ({String label, double? width, bool numeric});

/// 표의 한 행. [cells] 길이는 칼럼 수와 같아야 한다.
typedef DpTableRowSpec = ({List<Widget> cells, VoidCallback? onTap});

/// 웹 문법 표(시안 `<table>`) — 헤더행 + 가로 구분선 + hover 배경.
///
/// `DpDataTable`(admin 이 쓰는 `data_table_2` 래퍼)과 **다른 위젯**이다.
/// 그쪽은 `TableBorder.all` 로 세로 테두리를 그리지만 시안의 표에는
/// 세로선이 없다.
class DpWebTable extends StatelessWidget {
  const DpWebTable({
    super.key,
    required this.columns,
    required this.rows,
    this.minWidth = 640,
    this.empty,
  });

  final List<DpTableColumn> columns;
  final List<DpTableRowSpec> rows;

  /// 이 폭보다 좁으면 표만 가로로 스크롤한다(페이지 본문은 넘치지 않는다).
  final double minWidth;

  /// 행이 없을 때 표 대신 보여 줄 것. null 이면 헤더만 남는다.
  final Widget? empty;

  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty && empty != null) return empty!;

    final table = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        _Header(columns: columns),
        for (var i = 0; i < rows.length; i++)
          _Row(
            columns: columns,
            spec: rows[i],
            last: i == rows.length - 1,
          ),
      ],
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        if (!constraints.hasBoundedWidth || constraints.maxWidth >= minWidth) {
          return table;
        }
        return SingleChildScrollView(
          key: const ValueKey('dp-web-table-scroll'),
          scrollDirection: Axis.horizontal,
          child: SizedBox(width: minWidth, child: table),
        );
      },
    );
  }
}

List<Widget> _cells(
  List<DpTableColumn> columns,
  List<Widget> children,
) => [
  for (var i = 0; i < columns.length; i++)
    if (columns[i].width == null)
      Expanded(child: children[i])
    else
      SizedBox(
        width: columns[i].width,
        child: Align(
          alignment: columns[i].numeric
              ? Alignment.centerRight
              : Alignment.centerLeft,
          child: children[i],
        ),
      ),
];

class _Header extends StatelessWidget {
  const _Header({required this.columns});

  final List<DpTableColumn> columns;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    return Container(
      key: const ValueKey('dp-web-table-header'),
      padding: const EdgeInsets.symmetric(
        vertical: DpSpacing.sm,
        horizontal: DpSpacing.lg,
      ),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: c.border)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: _cells(columns, [
          for (final col in columns)
            Text(
              col.label,
              softWrap: false,
              overflow: TextOverflow.clip,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: c.textFaint,
              ),
            ),
        ]),
      ),
    );
  }
}

class _Row extends StatefulWidget {
  const _Row({required this.columns, required this.spec, required this.last});

  final List<DpTableColumn> columns;
  final DpTableRowSpec spec;
  final bool last;

  @override
  State<_Row> createState() => _RowState();
}

class _RowState extends State<_Row> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final body = Container(
      key: const ValueKey('dp-web-table-row'),
      padding: const EdgeInsets.symmetric(
        vertical: DpDensity.rowPadding,
        horizontal: DpSpacing.lg,
      ),
      decoration: BoxDecoration(
        color: _hovered ? c.surfaceMuted : null,
        border: widget.last
            ? null
            : Border(bottom: BorderSide(color: c.border)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: _cells(widget.columns, [
          for (var i = 0; i < widget.columns.length; i++)
            widget.columns[i].numeric
                ? DefaultTextStyle.merge(
                    style: TextStyle(
                      color: c.textSecondary,
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                    softWrap: false,
                    overflow: TextOverflow.clip,
                    child: widget.spec.cells[i],
                  )
                : widget.spec.cells[i],
        ]),
      ),
    );

    if (widget.spec.onTap == null) {
      return MouseRegion(
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: body,
      );
    }

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(onTap: widget.spec.onTap, child: body),
    );
  }
}
```

`dp_design.dart` 의 data 묶음에 추가:

```dart
export 'src/data/dp_web_table.dart';
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd packages/dp_design && flutter test test/data/dp_web_table_test.dart
```

기대: `+3: All tests passed!`

- [ ] **Step 5: 긴 제목 테스트를 쓴다 (Review Focus 1)**

같은 테스트 파일의 `main()` 안에 추가:

```dart
  testWidgets('긴 제목은 줄바꿈하고 숫자 칼럼 폭은 그대로다', (tester) async {
    const long = '비전공자 백엔드 전향 6개월 회고 — 퇴근 후 하루 한 시간씩 무엇이 '
        '남았고 무엇을 버렸는지 적어 봅니다';
    await tester.pumpWidget(
      _host(
        _table(
          rows: const [
            (cells: [Text(long), Text('12'), Text('3일 전')], onTap: null),
          ],
        ),
      ),
    );

    // 제목이 두 줄 이상으로 흘러도
    expect(tester.getSize(find.text(long)).height,
        greaterThan(tester.getSize(find.text('12')).height));
    // 숫자 칼럼은 선언한 폭을 지킨다.
    final commentCell = find.ancestor(
      of: find.text('12'),
      matching: find.byType(SizedBox),
    );
    expect(tester.widget<SizedBox>(commentCell.first).width, 72);
  });
```

- [ ] **Step 6: 실패 → 통과를 확인한다**

```bash
cd packages/dp_design && flutter test test/data/dp_web_table_test.dart --plain-name "긴 제목"
```

Step 3 구현이 이미 `Expanded` + 고정 `SizedBox` 를 쓰므로 **통과해야 한다**. FAIL 이면 `_cells` 의 폭 배분이 잘못된 것이므로 구현을 고친다.

- [ ] **Step 7: 빈 목록 테스트를 쓴다 (Review Focus 2)**

```dart
  testWidgets('행이 없고 empty 가 있으면 표 대신 empty 를 그린다', (tester) async {
    await tester.pumpWidget(
      _host(_table(rows: const [], empty: const Text('아직 글이 없어요'))),
    );

    expect(find.text('아직 글이 없어요'), findsOneWidget);
    expect(find.byKey(const ValueKey('dp-web-table-header')), findsNothing);
  });

  testWidgets('행이 없고 empty 가 없으면 헤더만 남는다', (tester) async {
    await tester.pumpWidget(_host(_table(rows: const [])));

    expect(find.byKey(const ValueKey('dp-web-table-header')), findsOneWidget);
    expect(find.byKey(const ValueKey('dp-web-table-row')), findsNothing);
  });
```

- [ ] **Step 8: 실패 → 통과를 확인한다**

```bash
cd packages/dp_design && flutter test test/data/dp_web_table_test.dart
```

기대: 전건 통과. FAIL 이면 `rows.isEmpty && empty != null` 분기를 고친다.

- [ ] **Step 9: 좁은 폭 테스트를 쓴다 (Review Focus 3)**

```dart
  testWidgets('390px 에서는 표만 가로 스크롤하고 본문은 넘치지 않는다', (tester) async {
    await tester.pumpWidget(_host(_table(), width: 390));
    await tester.pumpAndSettle();

    // 표가 자체 가로 스크롤을 갖는다.
    expect(find.byKey(const ValueKey('dp-web-table-scroll')), findsOneWidget);
    // 바깥 폭은 390 을 넘지 않는다.
    expect(tester.getSize(find.byType(DpWebTable)).width, lessThanOrEqualTo(390));
    // 오버플로 예외가 나지 않았다.
    expect(tester.takeException(), isNull);
  });

  testWidgets('minWidth 이상 폭에서는 스크롤을 감싸지 않는다', (tester) async {
    await tester.pumpWidget(_host(_table(), width: 1120));

    expect(find.byKey(const ValueKey('dp-web-table-scroll')), findsNothing);
  });
```

- [ ] **Step 10: 실패 → 통과를 확인한다**

```bash
cd packages/dp_design && flutter test test/data/dp_web_table_test.dart
```

기대: 전건 통과.

- [ ] **Step 11: 시맨틱스 테스트를 쓴다 (Review Focus 4)**

```dart
  testWidgets('행의 각 셀이 시맨틱스에서 따로 읽힌다', (tester) async {
    final handle = tester.ensureSemantics();
    await tester.pumpWidget(
      _host(
        _table(
          rows: [
            (
              cells: const [Text('제목 A'), Text('7'), Text('어제')],
              onTap: () {},
            ),
          ],
        ),
      ),
    );

    // 세 셀이 한 노드로 병합되면 '제목 A\n7\n어제' 하나만 남는다.
    expect(find.bySemanticsLabel('제목 A'), findsOneWidget);
    expect(find.bySemanticsLabel('7'), findsOneWidget);
    expect(find.bySemanticsLabel('어제'), findsOneWidget);
    handle.dispose();
  });
```

- [ ] **Step 12: 실패를 확인하고, 실패하면 고친다**

```bash
cd packages/dp_design && flutter test test/data/dp_web_table_test.dart --plain-name "따로 읽힌다"
```

`GestureDetector` 는 시맨틱스를 병합하지 않으므로 통과할 가능성이 높다. **FAIL 이면**(라벨이 `'제목 A\n7\n어제'` 로 합쳐졌다면) `_Row.body` 를 `Semantics(explicitChildNodes: true, child: …)` 로 감싸 고친다 — 테스트를 고치지 않는다. 2026-09-26 P2 에서 배운 것처럼, 시맨틱스 문제는 실제 트리를 덤프해 확인한다.

- [ ] **Step 13: hover·다크 테스트를 쓴다 (Review Focus 5)**

```dart
  testWidgets('hover 하면 행 배경이 surfaceMuted 가 된다', (tester) async {
    await tester.pumpWidget(_host(_table()));

    final gesture = await tester.createGesture(kind: PointerDeviceKind.mouse);
    await gesture.addPointer(location: Offset.zero);
    addTearDown(gesture.removePointer);
    await gesture.moveTo(
      tester.getCenter(find.text('오늘 배운 것 공유')),
    );
    await tester.pump();

    final row = tester.widget<Container>(
      find.byKey(const ValueKey('dp-web-table-row')).first,
    );
    expect((row.decoration! as BoxDecoration).color,
        DpColors.light.surfaceMuted);
  });

  testWidgets('다크 테마의 구분선은 dark 토큰을 쓴다', (tester) async {
    await tester.pumpWidget(_host(_table(), brightness: Brightness.dark));

    final row = tester.widget<Container>(
      find.byKey(const ValueKey('dp-web-table-row')).first,
    );
    final d = row.decoration! as BoxDecoration;
    expect(d.border!.bottom.color, DpColors.dark.border);
    expect(d.border!.bottom.color, isNot(DpColors.light.border));
  });
```

파일 상단 import 에 추가:

```dart
import 'package:flutter/gestures.dart';
```

- [ ] **Step 14: 실패 → 통과를 확인한다**

```bash
cd packages/dp_design && flutter test test/data/dp_web_table_test.dart
```

기대: 전건(10건) 통과.

- [ ] **Step 15: 커밋**

```bash
git add packages/dp_design/lib/src/data/dp_web_table.dart \
        packages/dp_design/lib/dp_design.dart \
        packages/dp_design/test/data/dp_web_table_test.dart
git commit -m "$(cat <<'EOF'
feat(dp_design): 웹 문법 표 DpWebTable 신설

시안 `<table>` — 헤더행(12/600 faint) + 행 하단 구분선 + hover 배경 +
숫자 칼럼(우측·등폭·nowrap) + minWidth 미만에서 표만 가로 스크롤.

DpDataTable 을 재사용하지 않는다: 그쪽은 data_table_2 래퍼라
TableBorder.all 로 세로 테두리를 그리는데 시안의 표에는 세로선이 없다.
admin 4화면이 쓰고 있으므로 그 위젯은 그대로 둔다.

긴 제목 줄바꿈·빈 목록·390px 가로 스크롤·행 셀의 개별 시맨틱스·다크
구분선까지 테스트로 못 박았다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `DpListLines` — 시안 `.list`

**Files:**
- Create: `packages/dp_design/lib/src/data/dp_list_lines.dart`
- Modify: `packages/dp_design/lib/dp_design.dart`
- Test: `packages/dp_design/test/data/dp_list_lines_test.dart`

**Interfaces:**
- Consumes: `context.dpColors`(`border`), `DpSpacing`
- Produces: `DpListLines({Key? key, required List<Widget> children})` — 각 자식을 패딩 10×16 으로 감싸고 마지막을 뺀 자식에 하단 1px 구분선.

- [ ] **Step 1: 실패 테스트를 쓴다**

`packages/dp_design/test/data/dp_list_lines_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host(Widget child) =>
    MaterialApp(theme: DpTheme.light(), home: Scaffold(body: child));

void main() {
  testWidgets('자식을 모두 그리고 마지막만 구분선이 없다', (tester) async {
    await tester.pumpWidget(
      _host(const DpListLines(children: [Text('첫째'), Text('둘째'), Text('셋째')])),
    );

    final items = tester
        .widgetList<Container>(find.byKey(const ValueKey('dp-list-line')))
        .toList();
    expect(items.length, 3);
    expect((items[0].decoration! as BoxDecoration).border!.bottom.color,
        DpColors.light.border);
    expect((items[1].decoration! as BoxDecoration).border!.bottom.width, 1);
    expect((items[2].decoration! as BoxDecoration).border, isNull);
    expect(find.text('셋째'), findsOneWidget);
  });

  testWidgets('항목 패딩은 세로 10 가로 16', (tester) async {
    await tester.pumpWidget(
      _host(const DpListLines(children: [Text('하나')])),
    );

    final item = tester.widget<Container>(
      find.byKey(const ValueKey('dp-list-line')),
    );
    expect(item.padding,
        const EdgeInsets.symmetric(vertical: 10, horizontal: DpSpacing.lg));
  });

  testWidgets('자식이 없으면 아무것도 그리지 않는다', (tester) async {
    await tester.pumpWidget(_host(const DpListLines(children: [])));

    expect(find.byKey(const ValueKey('dp-list-line')), findsNothing);
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd packages/dp_design && flutter test test/data/dp_list_lines_test.dart
```

기대: `Undefined name 'DpListLines'` 로 3건 FAIL.

- [ ] **Step 3: 최소 구현을 쓴다**

`packages/dp_design/lib/src/data/dp_list_lines.dart`:

```dart
import 'package:flutter/material.dart';

import '../theme/dp_colors.dart';
import '../theme/dp_spacing.dart';

/// 구분선 목록(시안 `.list`) — 사이드 패널의 짧은 목록.
///
/// 세로 여백 10 은 시안 `.list li` 값 그대로이며 표 행(8)보다 조금 넓다.
/// 표는 칼럼 정렬로 행을 가르지만 이 목록은 구분선과 여백만으로 가르기 때문에
/// 같은 값을 쓰면 답답해진다. 토큰 상수가 없는 유일한 치수다.
class DpListLines extends StatelessWidget {
  const DpListLines({super.key, required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var i = 0; i < children.length; i++)
          Container(
            key: const ValueKey('dp-list-line'),
            padding: const EdgeInsets.symmetric(
              vertical: 10,
              horizontal: DpSpacing.lg,
            ),
            decoration: BoxDecoration(
              border: i == children.length - 1
                  ? null
                  : Border(bottom: BorderSide(color: c.border)),
            ),
            child: children[i],
          ),
      ],
    );
  }
}
```

`dp_design.dart` 에 `export 'src/data/dp_list_lines.dart';` 추가.

- [ ] **Step 4: 통과를 확인한다**

```bash
cd packages/dp_design && flutter test test/data/dp_list_lines_test.dart
```

기대: `+3: All tests passed!`

- [ ] **Step 5: 커밋**

```bash
git add packages/dp_design/lib/src/data/dp_list_lines.dart \
        packages/dp_design/lib/dp_design.dart \
        packages/dp_design/test/data/dp_list_lines_test.dart
git commit -m "$(cat <<'EOF'
feat(dp_design): 구분선 목록 DpListLines 신설

시안 `.list` — 자식마다 10×16 패딩, 마지막을 뺀 자식에 하단 1px 구분선.
사이드 패널의 짧은 목록용이다.

세로 10 은 표 행(8)보다 넓다. 표는 칼럼 정렬로도 행을 가르지만 이 목록은
구분선과 여백만으로 가르기 때문이다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `DpRowLine` — 시안 `.rowline`

**Files:**
- Create: `packages/dp_design/lib/src/data/dp_row_line.dart`
- Modify: `packages/dp_design/lib/dp_design.dart`
- Test: `packages/dp_design/test/data/dp_row_line_test.dart`

**Interfaces:**
- Consumes: `context.dpColors`(`border`·`textPrimary`·`textSecondary`), `DpSpacing`
- Produces: `DpRowLine({Key? key, required Widget label, Widget? description, Widget? trailing, bool last = false})` — 좌측에 라벨(600)과 설명(13px·보조색), 우측에 컨트롤. 좁으면 `Wrap` 으로 줄바꿈. `last` 가 아니면 하단 구분선.

- [ ] **Step 1: 실패 테스트를 쓴다**

`packages/dp_design/test/data/dp_row_line_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host(Widget child, {double width = 720}) => MaterialApp(
  theme: DpTheme.light(),
  home: Scaffold(body: Center(child: SizedBox(width: width, child: child))),
);

void main() {
  testWidgets('라벨·설명·우측 컨트롤을 모두 그린다', (tester) async {
    await tester.pumpWidget(
      _host(DpRowLine(
        label: const Text('학습 알림'),
        description: const Text('선호 시간대에 학습 알림을 받아요.'),
        trailing: Switch(value: true, onChanged: (_) {}),
      )),
    );

    expect(find.text('학습 알림'), findsOneWidget);
    expect(find.text('선호 시간대에 학습 알림을 받아요.'), findsOneWidget);
    expect(find.byType(Switch), findsOneWidget);
  });

  testWidgets('last 가 아니면 하단 구분선이 있다', (tester) async {
    await tester.pumpWidget(_host(const DpRowLine(label: Text('로그아웃'))));

    final box = tester.widget<Container>(
      find.byKey(const ValueKey('dp-row-line')),
    );
    final d = box.decoration! as BoxDecoration;
    expect(d.border!.bottom.color, DpColors.light.border);
  });

  testWidgets('last 면 구분선이 없다', (tester) async {
    await tester.pumpWidget(
      _host(const DpRowLine(label: Text('계정 삭제'), last: true)),
    );

    final box = tester.widget<Container>(
      find.byKey(const ValueKey('dp-row-line')),
    );
    expect((box.decoration! as BoxDecoration).border, isNull);
  });

  testWidgets('설명은 13px 보조색이다', (tester) async {
    await tester.pumpWidget(
      _host(const DpRowLine(
        label: Text('주간 리포트'),
        description: Text('월요일에 보내 드려요.'),
      )),
    );

    final style = DefaultTextStyle.of(
      tester.element(find.text('월요일에 보내 드려요.')),
    ).style;
    expect(style.fontSize, 13);
    expect(style.color, DpColors.light.textSecondary);
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd packages/dp_design && flutter test test/data/dp_row_line_test.dart
```

기대: `Undefined name 'DpRowLine'` 로 4건 FAIL.

- [ ] **Step 3: 최소 구현을 쓴다**

`packages/dp_design/lib/src/data/dp_row_line.dart`:

```dart
import 'package:flutter/material.dart';

import '../theme/dp_colors.dart';
import '../theme/dp_spacing.dart';

/// 설정·동의 관리의 한 행(시안 `.rowline`).
///
/// 좌측 라벨(600) + 선택적 설명(13px 보조색), 우측 컨트롤. 좁은 폭에서는
/// `Wrap` 이 컨트롤을 아래 줄로 내린다 — `Row` 로 두면 390px 에서 넘친다.
class DpRowLine extends StatelessWidget {
  const DpRowLine({
    super.key,
    required this.label,
    this.description,
    this.trailing,
    this.last = false,
  });

  final Widget label;
  final Widget? description;
  final Widget? trailing;

  /// 목록의 마지막 행이면 하단 구분선을 그리지 않는다.
  final bool last;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final text = Theme.of(context).textTheme;

    return Container(
      key: const ValueKey('dp-row-line'),
      padding: const EdgeInsets.symmetric(
        vertical: 10,
        horizontal: DpSpacing.lg,
      ),
      decoration: BoxDecoration(
        border: last ? null : Border(bottom: BorderSide(color: c.border)),
      ),
      child: Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: DpSpacing.lg,
        runSpacing: DpSpacing.sm,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              DefaultTextStyle.merge(
                style: text.bodyMedium?.copyWith(
                  color: c.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
                child: label,
              ),
              if (description != null)
                DefaultTextStyle.merge(
                  style: TextStyle(fontSize: 13, color: c.textSecondary),
                  child: description!,
                ),
            ],
          ),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}
```

`dp_design.dart` 에 `export 'src/data/dp_row_line.dart';` 추가.

- [ ] **Step 4: 통과를 확인한다**

```bash
cd packages/dp_design && flutter test test/data/dp_row_line_test.dart
```

기대: `+4: All tests passed!`

- [ ] **Step 5: 커밋**

```bash
git add packages/dp_design/lib/src/data/dp_row_line.dart \
        packages/dp_design/lib/dp_design.dart \
        packages/dp_design/test/data/dp_row_line_test.dart
git commit -m "$(cat <<'EOF'
feat(dp_design): 설정 행 DpRowLine 신설

시안 `.rowline` — 좌측 라벨(600)+설명(13 보조색), 우측 컨트롤, 하단 구분선.

Row 가 아니라 Wrap 을 쓴다. 390px 에서 라벨과 컨트롤이 한 줄에 못 들어가면
Row 는 오버플로를 내지만 Wrap 은 컨트롤을 아랫줄로 내린다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: `DpKeyValues` — 시안 `.kv`

**Files:**
- Create: `packages/dp_design/lib/src/data/dp_key_values.dart`
- Modify: `packages/dp_design/lib/dp_design.dart`
- Test: `packages/dp_design/test/data/dp_key_values_test.dart`

**Interfaces:**
- Consumes: `context.dpColors`(`textSecondary`·`textPrimary`), `DpSpacing`
- Produces: `typedef DpKeyValue = ({String key, Widget value});` 와 `DpKeyValues({Key? widgetKey, required List<DpKeyValue> entries})` — 2열 격자, 좌측 키(보조색), 우측 값(우측 정렬·600·등폭 숫자). 패딩 12×16, 행 간격 6, 열 간격 16.

- [ ] **Step 1: 실패 테스트를 쓴다**

`packages/dp_design/test/data/dp_key_values_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host(Widget child, {double width = 360}) => MaterialApp(
  theme: DpTheme.light(),
  home: Scaffold(body: Center(child: SizedBox(width: width, child: child))),
);

const _entries = <DpKeyValue>[
  (key: '이번 주', value: Text('1 / 3')),
  (key: '전체 경로', value: Text('12주 중 1주차')),
];

void main() {
  testWidgets('키와 값을 모두 그린다', (tester) async {
    await tester.pumpWidget(_host(const DpKeyValues(entries: _entries)));

    expect(find.text('이번 주'), findsOneWidget);
    expect(find.text('1 / 3'), findsOneWidget);
    expect(find.text('전체 경로'), findsOneWidget);
  });

  testWidgets('키는 보조색이다', (tester) async {
    await tester.pumpWidget(_host(const DpKeyValues(entries: _entries)));

    final style = tester.widget<Text>(find.text('이번 주')).style!;
    expect(style.color, DpColors.light.textSecondary);
  });

  testWidgets('값은 우측 정렬 600 이다', (tester) async {
    await tester.pumpWidget(_host(const DpKeyValues(entries: _entries)));

    final valueStyle = DefaultTextStyle.of(
      tester.element(find.text('1 / 3')),
    );
    expect(valueStyle.style.fontWeight, FontWeight.w600);
    expect(valueStyle.textAlign, TextAlign.right);
  });

  testWidgets('바깥 패딩은 12×16', (tester) async {
    await tester.pumpWidget(_host(const DpKeyValues(entries: _entries)));

    final pad = tester.widget<Padding>(
      find.byKey(const ValueKey('dp-key-values')),
    );
    expect(pad.padding, const EdgeInsets.symmetric(
      vertical: DpSpacing.md,
      horizontal: DpSpacing.lg,
    ));
  });
}
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd packages/dp_design && flutter test test/data/dp_key_values_test.dart
```

기대: `Undefined name 'DpKeyValues'` 로 4건 FAIL.

- [ ] **Step 3: 최소 구현을 쓴다**

`packages/dp_design/lib/src/data/dp_key_values.dart`:

```dart
import 'dart:ui' show FontFeature;

import 'package:flutter/material.dart';

import '../theme/dp_colors.dart';
import '../theme/dp_spacing.dart';

/// 키-값 한 쌍. 값은 태그나 진행 바가 올 수 있어 Widget 이다.
typedef DpKeyValue = ({String key, Widget value});

/// 요약 키-값 목록(시안 `.kv`) — 좌측 키, 우측 값.
///
/// 값을 우측 정렬 + 등폭 숫자로 두는 이유는 여러 줄이 세로로 쌓였을 때
/// 자릿수가 맞아야 읽히기 때문이다(시안 `.kv dd`).
class DpKeyValues extends StatelessWidget {
  const DpKeyValues({super.key, required this.entries});

  final List<DpKeyValue> entries;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final text = Theme.of(context).textTheme;

    return Padding(
      key: const ValueKey('dp-key-values'),
      padding: const EdgeInsets.symmetric(
        vertical: DpSpacing.md,
        horizontal: DpSpacing.lg,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          for (var i = 0; i < entries.length; i++) ...[
            if (i > 0) const SizedBox(height: 6),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  entries[i].key,
                  style: text.bodyMedium?.copyWith(color: c.textSecondary),
                ),
                const SizedBox(width: DpSpacing.lg),
                Expanded(
                  child: DefaultTextStyle.merge(
                    textAlign: TextAlign.right,
                    style: text.bodyMedium?.copyWith(
                      color: c.textPrimary,
                      fontWeight: FontWeight.w600,
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                    child: Align(
                      alignment: Alignment.centerRight,
                      child: entries[i].value,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
```

`dp_design.dart` 에 `export 'src/data/dp_key_values.dart';` 추가.

- [ ] **Step 4: 통과를 확인한다**

```bash
cd packages/dp_design && flutter test test/data/dp_key_values_test.dart
```

기대: `+4: All tests passed!`

- [ ] **Step 5: 커밋**

```bash
git add packages/dp_design/lib/src/data/dp_key_values.dart \
        packages/dp_design/lib/dp_design.dart \
        packages/dp_design/test/data/dp_key_values_test.dart
git commit -m "$(cat <<'EOF'
feat(dp_design): 요약 키-값 DpKeyValues 신설

시안 `.kv` — 좌측 키(보조색), 우측 값(우측 정렬·600·등폭 숫자), 패딩 12×16.

값을 등폭 숫자로 두는 이유는 여러 줄이 세로로 쌓였을 때 자릿수가 맞아야
읽히기 때문이다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: `DpListRow` 를 웹 문법 구분선 행으로 교체

**Files:**
- Modify: `packages/dp_design/lib/src/data/dp_list_row.dart`
- Test: `packages/dp_design/test/data/dp_list_row_test.dart` (기존 파일 — 카드 전제 테스트를 구분선 전제로 고친다)

**Interfaces:**
- Consumes: Task 2 의 `DpLink.title`, `context.dpColors`, `DpSpacing`, `DpDensity`
- Produces: `DpListRow({Key? key, required String title, List<Widget> badges = const [], Widget? trailing, VoidCallback? onTap, String? preview, Widget? subtitle, bool last = false})`
  - **`accentColor` 파라미터가 사라진다** — 시안의 목록에는 좌측 상태 표시선이 없다.
  - **`last` 가 새로 생긴다** — 마지막 행의 구분선을 지우기 위해서다.
  - `DpInteractiveCard` 를 더 이상 쓰지 않는다. hover 는 배경색 변화뿐이다.

- [ ] **Step 1: 기존 테스트가 무엇을 주장하는지 읽는다**

```bash
cd packages/dp_design && cat test/data/dp_list_row_test.dart
```

`accentColor`·`DpInteractiveCard` 를 전제한 단언이 있으면 **그 테스트가 지금 계약이다.** 다음 스텝에서 계약을 바꾸는 것이므로, 무엇을 바꾸는지 눈으로 확인하고 진행한다.

- [ ] **Step 2: 새 계약의 실패 테스트를 쓴다**

`packages/dp_design/test/data/dp_list_row_test.dart` 의 `main()` 안에 추가(기존 테스트는 아직 지우지 않는다):

```dart
  testWidgets('카드가 아니라 하단 구분선을 가진 행이다', (tester) async {
    await tester.pumpWidget(
      _host(const DpListRow(title: '오늘 배운 것 공유')),
    );

    expect(find.byType(DpInteractiveCard), findsNothing);
    final row = tester.widget<Container>(
      find.byKey(const ValueKey('dp-list-row')),
    );
    final d = row.decoration! as BoxDecoration;
    expect(d.border!.bottom.color, DpColors.light.border);
    expect(d.borderRadius, isNull);
  });

  testWidgets('last 면 구분선이 없다', (tester) async {
    await tester.pumpWidget(
      _host(const DpListRow(title: '마지막 글', last: true)),
    );

    final row = tester.widget<Container>(
      find.byKey(const ValueKey('dp-list-row')),
    );
    expect((row.decoration! as BoxDecoration).border, isNull);
  });

  testWidgets('행 여백은 표와 같은 8×16 이다', (tester) async {
    await tester.pumpWidget(const _HostedRow());

    final row = tester.widget<Container>(
      find.byKey(const ValueKey('dp-list-row')),
    );
    expect(row.padding, const EdgeInsets.symmetric(
      vertical: DpDensity.rowPadding,
      horizontal: DpSpacing.lg,
    ));
  });

  testWidgets('제목은 DpLink.title 로 그려진다', (tester) async {
    await tester.pumpWidget(
      _host(DpListRow(title: '제목', onTap: () {})),
    );

    expect(find.byType(DpLink), findsOneWidget);
  });
```

`_HostedRow` 가 기존 파일에 없으면 다음을 파일 하단에 추가한다:

```dart
class _HostedRow extends StatelessWidget {
  const _HostedRow();

  @override
  Widget build(BuildContext context) => MaterialApp(
    theme: DpTheme.light(),
    home: const Scaffold(body: DpListRow(title: '여백 확인')),
  );
}
```

- [ ] **Step 3: 실패를 확인한다**

```bash
cd packages/dp_design && flutter test test/data/dp_list_row_test.dart
```

기대: 새 테스트 4건 FAIL(`dp-list-row` 키 없음 / `DpInteractiveCard` 가 발견됨 / `last` 파라미터 없음), 기존 테스트는 아직 통과.

- [ ] **Step 4: 구현을 교체한다**

`packages/dp_design/lib/src/data/dp_list_row.dart` 에서:

1. `accentColor` 필드와 생성자 인자, `_accent()` 메서드를 **삭제**한다.
2. `last` 필드를 추가한다(`this.last = false`).
3. `import '../interaction/dp_interactive_card.dart';` 를 삭제하고 `import 'dp_link.dart';` 대신 `import '../content/dp_link.dart';` 를 추가한다.
4. `build` 를 다음으로 바꾼다(`_HoverPreview`·`_PreviewCard` 는 그대로 둔다 — 시안의 제목 hover 미리보기는 유지 대상이다):

```dart
  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    return _HoverRow(
      onTap: onTap,
      last: last,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(child: _content(context, Theme.of(context).textTheme)),
          if (trailing != null) ...[
            const SizedBox(width: DpSpacing.lg),
            DefaultTextStyle.merge(
              style: TextStyle(color: c.textSecondary),
              child: trailing!,
            ),
          ],
        ],
      ),
    );
  }
```

5. `_content` 안에서 제목을 `DpLink.title` 로 바꾼다:

```dart
      (preview != null && preview!.trim().isNotEmpty)
          ? _HoverPreview(
              preview: preview!,
              child: DpLink.title(text: title, onTap: onTap),
            )
          : DpLink.title(text: title, onTap: onTap),
```

6. 파일 하단에 hover 행을 추가한다:

```dart
/// 구분선 행의 hover 배경. 표(`DpWebTable`)의 행과 같은 규칙이다 —
/// 카드 테두리·그림자를 쓰지 않고 배경색만 바꾼다.
class _HoverRow extends StatefulWidget {
  const _HoverRow({required this.child, required this.last, this.onTap});

  final Widget child;
  final bool last;
  final VoidCallback? onTap;

  @override
  State<_HoverRow> createState() => _HoverRowState();
}

class _HoverRowState extends State<_HoverRow> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final body = Container(
      key: const ValueKey('dp-list-row'),
      padding: const EdgeInsets.symmetric(
        vertical: DpDensity.rowPadding,
        horizontal: DpSpacing.lg,
      ),
      decoration: BoxDecoration(
        color: _hovered ? c.surfaceMuted : null,
        border: widget.last
            ? null
            : Border(bottom: BorderSide(color: c.border)),
      ),
      child: widget.child,
    );

    return MouseRegion(
      cursor: widget.onTap == null
          ? MouseCursor.defer
          : SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: widget.onTap == null
          ? body
          : GestureDetector(onTap: widget.onTap, child: body),
    );
  }
}
```

- [ ] **Step 5: 기존 테스트의 카드 전제를 고친다**

Step 1 에서 읽은 기존 테스트 중 `accentColor`·`DpInteractiveCard`·반경을 단언하는 것을 삭제한다. **제목·뱃지·trailing·preview·subtitle 의 거동을 단언하는 테스트는 남긴다** — 그것들은 여전히 계약이다.

- [ ] **Step 6: 통과를 확인한다**

```bash
cd packages/dp_design && flutter test test/data/dp_list_row_test.dart
```

기대: 전건 통과.

- [ ] **Step 7: dp_design 전체가 여전히 녹색인지 확인한다**

```bash
cd packages/dp_design && flutter test --exclude-tags golden
```

기대: `All tests passed!`. `DpListRow` 를 쓰는 다른 테스트가 깨지면 그것도 계약 변경의 일부이므로 같은 원칙으로 고친다(카드 전제만 삭제, 내용 단언은 유지).

- [ ] **Step 8: 커밋**

```bash
git add packages/dp_design/lib/src/data/dp_list_row.dart \
        packages/dp_design/test/data/dp_list_row_test.dart
git commit -m "$(cat <<'EOF'
refactor(dp_design)!: DpListRow 를 카드에서 구분선 행으로

시안의 목록에는 카드도 좌측 상태 표시선도 없다. DpInteractiveCard 를 벗고
8×16 여백 + 하단 1px 구분선 + hover 배경(surfaceMuted)만 남긴다. 제목은
DpLink.title 로 그려 hover 밑줄 규칙을 표와 공유한다.

BREAKING CHANGE: accentColor 파라미터를 제거하고 last 를 추가했다.
상태는 색 막대가 아니라 DpStatusText 로 드러낸다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: `DpPageHeader.titleMenu` 제거와 소비처 정리

**Files:**
- Modify: `packages/dp_design/lib/src/layout/dp_page_header.dart`
- Delete: `packages/dp_design/test/layout/dp_page_header_title_menu_test.dart`
- Modify: `apps/web/lib/src/features/community/presentation/web_community_board_projection.dart`
- Modify: `apps/web/lib/src/features/community/presentation/community_home_page.dart`
- Modify: `apps/web/test/features/community/community_home_page_test.dart`

**Interfaces:**
- Consumes: Task 8 의 `DpListRow`(더 이상 `accentColor` 를 받지 않음)
- Produces: `DpPageHeader({Key? key, required String title, String? description, List<Widget> actions = const [], List<Widget> filters = const []})` — `titleMenu`·`titleMenuTooltip` 없음.

**왜 지금 제거하는가:** 1회차 결정 「게시판 이동은 헤더 메뉴만」이다. `titleMenu` 는 `compact` 에서만 채워졌는데, P2 의 `DpWebShell` 헤더가 햄버거 메뉴로 커뮤니티 하위 게시판을 이미 제공한다 — 같은 이동 수단이 둘이다.

- [ ] **Step 1: 소비처의 현재 모습을 확인한다**

```bash
cd apps/web && grep -n "titleMenu\|accentColor\|communityRowAccent" -r lib/src/features/community
```

기대 출력(4곳):
- `web_community_board_projection.dart` 의 `titleMenuTooltip`·`titleMenu`
- `web_community_board_projection.dart` 의 `accentColor:` 와 `Color? communityRowAccent(`
- `community_home_page.dart` 의 `accentColor:`

- [ ] **Step 2: 제거를 요구하는 실패 테스트를 쓴다**

`packages/dp_design/test/layout/dp_page_header_test.dart` 에 추가(없으면 파일을 만들고 위 Task 들과 같은 `_host` 헬퍼를 둔다):

```dart
  testWidgets('제목은 언제나 헤더이며 메뉴 버튼이 되지 않는다', (tester) async {
    final handle = tester.ensureSemantics();
    await tester.pumpWidget(
      _host(const DpPageHeader(title: 'Q/A', description: '막힌 곳을 질문하세요.')),
    );

    expect(find.byKey(const ValueKey('page-header-title-menu')), findsNothing);
    expect(
      tester.getSemantics(find.text('Q/A')),
      matchesSemantics(label: 'Q/A', isHeader: true),
    );
    handle.dispose();
  });
```

- [ ] **Step 3: 실패를 확인한다**

```bash
cd packages/dp_design && flutter test test/layout/dp_page_header_test.dart --plain-name "메뉴 버튼이 되지 않는다"
```

`titleMenu` 를 넘기지 않으면 지금도 메뉴가 안 생기므로 이 테스트는 **통과할 수 있다.** 통과하면 그대로 두고 다음 스텝의 삭제로 계약을 못 박는다 — 이 테스트의 값은 삭제 후 회귀를 막는 데 있다.

- [ ] **Step 4: `DpPageHeader` 에서 제거한다**

`packages/dp_design/lib/src/layout/dp_page_header.dart` 에서:
1. `typedef DpPageHeaderMenuItem` 를 삭제한다.
2. 생성자에서 `this.titleMenu = const []`·`this.titleMenuTooltip` 를 삭제한다.
3. 필드 `titleMenu`·`titleMenuTooltip` 와 그 문서 주석을 삭제한다.
4. `build` 의 `if (titleMenu.isEmpty) … else _TitleMenu(…)` 조건을 없애고 `Semantics(header: true, child: Text(…))` 만 남긴다.
5. 파일 안의 `_TitleMenu` 위젯 클래스 전체를 삭제한다.

- [ ] **Step 5: 제목 메뉴 테스트 파일을 삭제한다**

```bash
git rm packages/dp_design/test/layout/dp_page_header_title_menu_test.dart
```

- [ ] **Step 6: 커뮤니티 소비처를 고친다**

`apps/web/lib/src/features/community/presentation/web_community_board_projection.dart`:

- `CommunityBoardHeader.build` 의 `titleMenuTooltip:` 줄과 `titleMenu: [...]` 블록 전체를 삭제한다. `compact` 지역 변수가 더 쓰이지 않으면 그 줄도 삭제한다.
- `Color? communityRowAccent(...)` 함수 전체를 삭제한다.
- `DpListRow(` 호출에서 `accentColor: communityRowAccent(c, boardType: ..., solved: ...),` 를 삭제한다. `c` 가 다른 곳에서 안 쓰이면 `final c = context.dpColors;` 도 삭제한다.

`apps/web/lib/src/features/community/presentation/community_home_page.dart`:

- `_searchRow` 의 `DpListRow(` 호출에서 같은 `accentColor:` 블록을 삭제한다.

`apps/web/test/features/community/community_home_page_test.dart`:

- `const _titleMenu = ValueKey('page-header-title-menu');` 와 그것을 쓰는 테스트(`find.byKey(_titleMenu)` 가 나오는 것)를 삭제한다. 게시판 전환을 검증하던 테스트라면, 전환 자체는 셸 헤더가 담당하므로 여기서 지우는 것이 맞다.

- [ ] **Step 7: 통과를 확인한다**

```bash
cd packages/dp_design && flutter test --exclude-tags golden
cd ../../apps/web && flutter test
```

기대: 양쪽 `All tests passed!`. `apps/web` 이 `DpPageHeaderMenuItem` 를 다른 데서 참조하고 있으면 컴파일이 실패하므로, 그 참조도 같은 원칙으로 제거한다.

- [ ] **Step 8: 커밋**

```bash
git add -A packages/dp_design apps/web
git status --porcelain   # analysis_options.yaml·pubspec.lock 이 섞이지 않았는지 확인
git commit -m "$(cat <<'EOF'
refactor(dp_design)!: DpPageHeader.titleMenu 제거

시안에 제목 메뉴가 없다. 1회차 결정 「게시판 이동은 헤더 메뉴만」이고,
P2 의 DpWebShell 헤더가 햄버거 메뉴로 커뮤니티 하위 게시판을 이미
제공한다 — 같은 이동 수단이 둘이었다.

커뮤니티 소비처에서 titleMenu·accentColor·communityRowAccent 를 함께
걷어낸다(위젯에서 파라미터를 없애 컴파일이 강제한 범위).

BREAKING CHANGE: DpPageHeader 의 titleMenu·titleMenuTooltip 과
DpPageHeaderMenuItem 타입을 제거했다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: 커뮤니티 FAB 을 페이지 헤더 액션으로

**Files:**
- Modify: `apps/web/lib/src/features/community/presentation/community_home_page.dart:115-120`
- Modify: `apps/web/lib/src/features/community/presentation/web_community_board_projection.dart` (`CommunityBoardHeader`)
- Test: `apps/web/test/features/community/community_home_page_test.dart`

**Interfaces:**
- Consumes: Task 9 의 `DpPageHeader(actions:)`
- Produces: `CommunityBoardHeader({Key? key, required CommunityBoard board, required ValueChanged<CommunityBoard> onSelectBoard, VoidCallback? onCompose})` — `onCompose` 가 있으면 헤더 우측에 `FilledButton.icon` 으로 작성 액션을 놓는다. 라벨은 `board.composeLabel`.

- [ ] **Step 1: 실패 테스트를 쓴다**

`apps/web/test/features/community/community_home_page_test.dart` 의 `main()` 안에 추가:

```dart
  testWidgets('작성 버튼은 FAB 이 아니라 페이지 헤더 안에 있다', (tester) async {
    await _pumpCommunityHome(tester);
    await tester.pumpAndSettle();

    expect(find.byType(FloatingActionButton), findsNothing);
    final compose = find.widgetWithText(FilledButton, '글쓰기');
    expect(compose, findsOneWidget);
    expect(
      find.ancestor(of: compose, matching: find.byType(DpPageHeader)),
      findsOneWidget,
    );
  });
```

`_pumpCommunityHome` 는 이 파일에 이미 있는 펌프 헬퍼를 쓴다. 이름이 다르면 파일 상단에서 확인해 맞춘다 — **새 헬퍼를 만들지 않는다.** 자유게시판의 `composeLabel` 이 `'글쓰기'` 가 아니면 실제 값으로 바꾼다:

```bash
cd apps/web && grep -rn "composeLabel" lib/src/features/community
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd apps/web && flutter test test/features/community/community_home_page_test.dart --plain-name "페이지 헤더 안에 있다"
```

기대: FAIL — `FloatingActionButton` 이 1개 발견됨.

- [ ] **Step 3: 헤더가 작성 액션을 받게 한다**

`web_community_board_projection.dart` 의 `CommunityBoardHeader`:

```dart
class CommunityBoardHeader extends StatelessWidget {
  const CommunityBoardHeader({
    super.key,
    required this.board,
    required this.onSelectBoard,
    this.onCompose,
  });

  final CommunityBoard board;
  final ValueChanged<CommunityBoard> onSelectBoard;

  /// 이 게시판의 작성 화면으로 가는 액션. 시안은 주요 액션을 페이지 헤더
  /// 우측에 두고 FAB 을 쓰지 않는다.
  final VoidCallback? onCompose;

  @override
  Widget build(BuildContext context) {
    return DpPageHeader(
      title: board.label,
      description: board.description,
      actions: [
        if (onCompose != null)
          FilledButton.icon(
            onPressed: onCompose,
            icon: const Icon(DpIcons.edit),
            label: Text(board.composeLabel),
          ),
      ],
    );
  }
}
```

`DpIcons` import 가 없으면 추가한다(`package:dp_design/dp_design.dart` 에 이미 들어 있다).

- [ ] **Step 4: FAB 을 없애고 헤더에 연결한다**

`community_home_page.dart`:

```dart
    return Scaffold(
      body: CustomScrollView(
```

(`floatingActionButton:` 인자 4줄을 삭제) 그리고 `CommunityBoardHeader(` 호출에 추가:

```dart
            child: CommunityBoardHeader(
              board: activeBoard,
              onCompose: compose,
```

- [ ] **Step 5: 통과를 확인한다**

```bash
cd apps/web && flutter test test/features/community/community_home_page_test.dart
```

기대: 전건 통과. 기존 테스트가 FAB 을 눌러 작성 화면 이동을 검증하고 있었다면 그 테스트도 새 버튼을 누르도록 고친다(이동 단언은 유지).

- [ ] **Step 6: 커밋**

```bash
git add apps/web
git status --porcelain
git commit -m "$(cat <<'EOF'
refactor(web): 커뮤니티 FAB 을 페이지 헤더 액션으로

시안에 FAB 이 없다. 주요 액션은 페이지 헤더 우측 버튼이다
(자유게시판 「글쓰기」·Q/A 「질문하기」·피드백 「리뷰 요청하기」).

CommunityBoardHeader 에 onCompose 를 받아 DpPageHeader.actions 로 넘긴다.
DpPageHeader.actions 는 이미 있던 API 라 새로 만든 것이 없다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: 전 게이트 확인과 문서 갱신

**Files:**
- Modify: `DESIGN.md` (§3 프리미티브 목록)
- Possibly modify: `tools/browser_ux/expectations.json`

- [ ] **Step 1: 모노레포 전체 테스트를 돌린다**

```bash
dart run melos run test
```

기대: `devpath_admin`·`devpath_web`·`dp_design`·`dp_core` 전부 `All tests passed!`. 한 번 실패하고 두 번째에 통과하면 flake 일 수 있으니 **세 번째까지 돌려** 재현 여부를 확인하고, 재현되면 원인을 규명한다(덮지 않는다).

- [ ] **Step 2: analyze 를 돌린다**

```bash
dart run melos run analyze
```

로컬 Flutter 가 3.47.x 이면 `apps/web` 의 `unawaited_return_in_try_block` 경고가 뜰 수 있다 — 이것은 **CI(3.44.1)에 없는 신규 린트**이고 내 변경과 무관하다. 내가 만든 파일에서 나온 지적만 고친다.

- [ ] **Step 3: 포맷을 확인한다**

```bash
dart format --output=none --set-exit-if-changed packages/dp_design apps/web
```

내가 만든/고친 파일이 목록에 없어야 한다. 다른 파일이 나오면 로컬 포매터 버전 차이이므로 **건드리지 않는다**.

- [ ] **Step 4: 커밋에 섞인 것이 없는지 확인한다**

```bash
git status --porcelain
git diff origin/develop --stat
```

`analysis_options.yaml`(3개)·`pubspec.lock` 이 diff 에 있으면 되돌린다:

```bash
git checkout -- apps/admin/analysis_options.yaml apps/web/analysis_options.yaml \
                packages/dp_design/analysis_options.yaml pubspec.lock
```

- [ ] **Step 5: `DESIGN.md` §3 에 새 프리미티브를 등재한다**

`DESIGN.md` 에서 Layer 2 위젯을 나열한 절을 찾아, 다음을 추가한다:

```markdown
- `DpPanel` — 웹 문법 면(surface + 1px + r8, 선택적 제목행). 웹 화면에서 Material `Card` 를 대신한다.
- `DpWebTable` — 웹 문법 표(헤더행 + 가로 구분선 + hover + 숫자 칼럼). admin 의 `DpDataTable`(data_table_2, 세로 테두리)과 다른 위젯이다.
- `DpListLines` — 구분선 목록(사이드 패널의 짧은 목록).
- `DpRowLine` — 설정·동의 행(좌 라벨/설명 + 우 컨트롤).
- `DpKeyValues` — 요약 키-값(우측 정렬·등폭 숫자).
- `DpLink` — `title`(hover 밑줄)·`inline`(상시 밑줄) 두 링크 변형.
- `DpStatusText` — 상태 문구 3색(done·idle·current).
```

`DpListRow` 설명이 「카드」로 돼 있으면 「구분선 행」으로 고치고, `DpPageHeader` 설명에 제목 메뉴가 적혀 있으면 지운다.

- [ ] **Step 6: 커밋하고 PR 을 올린다**

```bash
git add DESIGN.md
git commit -m "$(cat <<'EOF'
docs(design): S3-P3 웹 문법 프리미티브 7종 등재

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git push -u origin feat/s3-p3-web-widgets
gh pr create --base develop --title "feat(dp_design): S3-P3 공용 위젯 웹화" --body-file <(cat <<'EOF'
스펙 §7 P3. 시안의 웹 문법 프리미티브를 세우고 DpListRow 를 구분선 행으로
교체하며, 시안에 없는 DpPageHeader.titleMenu 와 커뮤니티 FAB 을 제거한다.

화면 레이아웃 재구성(cols/side/narrow, Card 25곳 교체)은 P4 다.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)
```

- [ ] **Step 7: CI 를 확인한다**

```bash
gh pr checks --watch --interval 60
```

`browser-ux` 가 실패하면 **기대값을 먼저 고치지 말고** 무엇이 달라졌는지 본다. 커뮤니티 목록이 카드에서 구분선 행으로 바뀌었으므로 높이·좌표 기대가 흔들리는 것이 정상일 수 있다. 로컬 재현 레시피(CI 6분 → 2분):

```bash
cd apps/web && flutter build web --release --dart-define=USE_MOCK=true
cd ../../tools/browser_ux && node run.mjs --only=<시나리오>
```

핀 이미지는 `mcr.microsoft.com/playwright:v1.55.0-noble`, `--network none` 으로 돌린다. 시맨틱스 DOM 은 `flt-semantics` 덤프로 본다(shadow DOM 아님).

- [ ] **Step 8: 기준선 이월 항목을 기록한다**

CI 가 녹색이 되면, P5 재기록 대상에 **커뮤니티 목록 렌더 변화**를 추가한다(칩 폰트 변화에 이은 두 번째). 기록 위치는 `documents/docs/superpowers/` 의 P3 핸드오프 문서 §기준선.

---

## Self-Review

**1. 스펙 커버리지** — §7 P3 의 다섯 항목: `DpListRow`(Task 8) · `DpPageHeader` titleMenu 제거(Task 9) · 카드→목록(Task 1 `DpPanel` + Task 4 `DpWebTable`; 화면의 Card 25곳 교체는 명시적으로 P4) · 링크 문법(Task 2) · FAB 제거(Task 10). 게이트 `dp_design` 단위 테스트 + browser-ux 는 Task 11. 빠진 항목 없음.

**2. 플레이스홀더** — 모든 코드 스텝에 실제 Dart/셸이 들어 있다. "적절히 처리"·"TODO"·"Task N 과 비슷하게" 없음. Task 8·9 는 기존 파일 수정이라 「삭제할 것」을 파일·식별자 단위로 지목했다.

**3. 타입 일관성** — `DpTableColumn`·`DpTableRowSpec`(Task 4), `DpKeyValue`(Task 7), `DpStatusTone`(Task 3), `DpLink.title`/`DpLink.inline`(Task 2)이 뒤 Task 에서 같은 이름·같은 필드로 쓰인다. Task 8 이 쓰는 `DpLink.title(text:, onTap:)` 는 Task 2 의 서명과 일치한다. Task 10 이 쓰는 `DpPageHeader(actions:)` 는 Task 9 가 남긴 서명과 일치한다.

**4. Review Focus** — 다섯 줄 전부 담당 Task 에 스텝으로 들어갔다(1→Task 4 Step 5-6, 2→Task 4 Step 7-8, 3→Task 4 Step 9-10, 4→Task 4 Step 11-12, 5→Task 1 Step 5-6 · Task 4 Step 13-14).
