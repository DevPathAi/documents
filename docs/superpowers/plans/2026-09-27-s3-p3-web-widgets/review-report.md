# S3-P3 독립 리뷰

리뷰 범위: `feat/s3-p3-web-widgets` `309d0aa..d9e82f3` (13커밋, 27파일).
직접 실행한 검증: `flutter test` (dp_design `test/data test/content test/layout test/states` → 108/108 pass),
`flutter test test/features/community` (apps/web → 189/189 pass), `flutter analyze` (dp_design → 0).
실행 뒤 `git status` 재확인 — 새로 더러워진 파일 없음(`apps/admin/analysis_options.yaml`·
`packages/dp_design/analysis_options.yaml`·`pubspec.lock` 은 착수 시점부터 미커밋 상태 그대로).

## 요약

Critical 0 · Important 4 · Minor 10

## 발견

### [Important] 커밋하지 않기로 못 박은 `apps/web/analysis_options.yaml` 이 커밋됐다

- 위치: `apps/web/analysis_options.yaml:10-13` (커밋 `d002fb7` "refactor(web): 커뮤니티 FAB 을 페이지 헤더 액션으로")
- 무엇: 로컬 Flutter 3.47.2 가 만들어 내는 `analyzer: exclude: [build/**, web/**]` 블록이 P3 커밋에 섞여 들어갔다 — 계획 Global Constraints 가 "그 4개 파일은 절대 커밋하지 않는다"고 명시한 바로 그 파일이다.
- 실패 시나리오: 같은 도구가 만든 동일 변경(index `0d29021..2a2b57e`, 바이트 동일)이 `apps/admin/analysis_options.yaml` 에는 미커밋으로 남아 있다. 결과적으로 develop 에 **web 만 `web/**` 를 analyze 대상에서 뺀 비대칭 설정**이 들어가고, 다음 사람이 admin 쪽 같은 변경을 볼 때 "web 은 커밋됐으니 의도된 것"으로 오해해 함께 커밋하게 된다. 지금은 `apps/web/web/` 에 `.dart` 가 없어 실질 은닉은 없으나(실측), 앞으로 그 밑에 Dart 가 생기면 CI analyze 가 조용히 건너뛴다. Task 11 의 "커밋 전 `git status --porcelain` 확인" 게이트가 Task 10 커밋을 못 잡은 것이기도 하다.
- 제안: `git rebase` 로 `d002fb7` 에서 그 파일만 되돌리거나(푸시 전이면 `git restore --source=309d0aa --staged --worktree apps/web/analysis_options.yaml` 후 amend), 세 파일을 한 번에 커밋할지 전부 뺄지 **하나로 통일**한다. 되돌리는 쪽이 계획과 맞다.

### [Important] `DpKeyValues` 는 키가 조금만 길어도 RenderFlex 오버플로로 깨진다

- 위치: `packages/dp_design/lib/src/data/dp_key_values.dart:35-43`
- 무엇: `Row(children: [Text(key), SizedBox(16), Expanded(value)])` 에서 키 `Text` 가 **유연 자식이 아니라** 주축 제약이 무한대로 들어간다(`RenderFlex._constraintsForNonFlexChild`: horizontal + non-stretch → `BoxConstraints(maxHeight: …)` 뿐, maxWidth 무제한). 줄바꿈도 생략도 못 하고 고유 폭 그대로 깔린다.
- 실패 시나리오: 280px 사이드 패널(가용 폭 = 280 − 좌우 16×2 = 248px)에 `(key: '이번 주 학습 시간', value: Text('3시간 20분'))` 을 넣고 브라우저 텍스트 배율 200%(browser-ux 가 실제로 도는 `390×200%` 시나리오)로 보면 키 한 줄이 248px 를 넘어 `A RenderFlex overflowed by N pixels on the right` 가 뜨고, 릴리스 빌드에서는 경고 없이 값이 잘린다. `Expanded` 는 이미 0 까지 줄어든 뒤라 값도 사라진다. 현재 테스트(`dp_key_values_test.dart`)는 폭 360 에 키 '이번 주'·'전체 경로'만 써서 이 경로를 전혀 밟지 않는다.
- 제안: 키를 `Flexible(child: Text(key))` 로 감싸거나(값 `Expanded` 와 함께 flex 비율 지정), 최소한 `Expanded(flex: …)` 2열로 만든다. 회귀 테스트는 폭 280 + 긴 키 + `MediaQuery(textScaler: TextScaler.linear(2))` 로 `tester.takeException(), isNull` 을 건다.

### [Important] 390px 에서 표가 가로로 잘리는데 스크롤 어포던스가 없다 — 레포에 이미 `DpScrollbar` 가 있다

- 위치: `packages/dp_design/lib/src/data/dp_web_table.dart:57-61`
- 무엇: 좁은 폭에서 맨 `SingleChildScrollView(scrollDirection: horizontal)` 로만 감싼다. `packages/dp_design/lib/src/layout/dp_scrollbar.dart` 의 `DpScrollbar` 는 doc 에 "웹/데스크톱 스크롤바를 항상 표시(**특히 가로 스크롤 탐색성**)"라고 적힌, 정확히 이 경우를 위한 레포 자체 프리미티브인데 쓰이지 않았다.
- 실패 시나리오: 390px 뷰포트에서 `minWidth: 640` 인 표는 오른쪽 250px(= 숫자 칼럼 두 개 전부)가 잘린 채 그려지고, 잘렸다는 표시가 한 픽셀도 없다. 데스크톱 브라우저 창을 좁힌 사용자는 휠이 세로로만 먹어(Flutter 는 shift+휠에만 가로 스크롤) 숨은 칼럼에 도달할 방법을 찾지 못한다. 현재 테스트는 "스크롤 위젯이 존재한다"까지만 본다.
- 제안: `_RowState` 바깥에 `ScrollController` 를 두고 `DpScrollbar(controller: …, child: SingleChildScrollView(controller: …, …))` 로 감싼다. `DpWebTable` 을 `StatefulWidget` 으로 바꿔야 하는 비용이 있으나, 이 위젯은 P4 의 표 25곳이 전부 지나갈 지점이라 여기서 한 번 치르는 편이 싸다.

### [Important] 표 헤더 라벨이 `textFaint` — 토큰 자신이 "본문 텍스트로 쓰지 않는다"고 금지한 용도다

- 위치: `packages/dp_design/lib/src/data/dp_web_table.dart:104-111`
- 무엇: 칼럼 라벨을 12px/600 `c.textFaint` 로 그린다. `dp_colors.dart:75-76` 의 doc 은 "메타·캡션. **UI 컴포넌트 기준(3:1)이라 본문 텍스트로 쓰지 않는다**", `test/theme/dp_colors_contrast_test.dart` 의 'faint·태그' 테스트도 3:1 만 요구한다. 같은 레포의 `dp_chrome_bar.dart:330` 에는 "textFaint는 대비 3.21:1 — **텍스트가 아닌 구분자 글리프에만 쓴다**"라는 주석까지 있다.
- 실패 시나리오: 라이트 테마에서 `textFaint`(#818998) 대 `surface`(#FFFFFF) = **3.52:1** (직접 계산, 레포 테스트와 같은 WCAG 공식). 12px 는 large text 예외(18pt / 14pt bold)에 들지 않으므로 WCAG 2.1 AA 1.4.3(4.5:1) **미달**이다. 다크는 5.18:1 로 통과하므로, 다크만 확인하면 놓친다(Review Focus 5 가 경고한 바로 그 함정의 대칭형). 칼럼 라벨은 "이 열이 댓글 수인지 작성일인지"를 전달하는 유일한 수단이라 장식 글리프가 아니다. DESIGN.md:277 이 이 선택을 문서로 고정해 둔 상태라 P4 의 표 전체로 번진다.
- 제안: `c.textSecondary`(라이트 5.93:1)로 바꾼다. 시안의 옅은 회색 느낌을 유지해야 한다면 라이트 `textFaint` 값 자체를 4.5:1 까지 어둡게 올리고(계약 2.0.0 의 값 변경 → P5 기준선 재기록 대상에 추가) 대비 테스트의 faint 단언을 4.5 로 올린다. 현 상태로 두려면 최소한 DESIGN.md 에 "헤더 라벨은 WCAG AA 미달을 감수한 결정"이라고 근거를 남겨야 한다.

---

### [Minor] `numeric: true` 인데 `width: null` 이면 우측 정렬이 조용히 사라진다

- 위치: `packages/dp_design/lib/src/data/dp_web_table.dart:67-81`
- 무엇: `_cells` 가 우측 정렬(`Align(centerRight)`)을 **고정폭 분기에만** 넣는다. 유연 칼럼은 `Expanded(child: …)` 로 끝이라 정렬 지시가 없다. `DpTableColumn` doc(:9)은 "`numeric` 이면 우측 정렬"이라고 무조건 약속한다.
- 실패 시나리오: `(label: '점수', width: null, numeric: true)` 로 선언하면 헤더 라벨과 셀 값이 **좌측**에 붙고, 옆의 고정폭 숫자 칼럼은 우측에 붙어 한 표 안에서 숫자 정렬이 엇갈린다. 컴파일도 테스트도 통과한다.
- 제안: `_cells` 의 `Expanded` 분기에도 `Align(alignment: numeric ? centerRight : centerLeft)` 를 넣거나, 아예 `numeric == true` 면 `width` 를 필수로 만드는 `assert` 를 둔다.

### [Minor] 빈 표의 기본값이 곧 Review Focus 2 가 지목한 실패 상태다

- 위치: `packages/dp_design/lib/src/data/dp_web_table.dart:36,40` · 테스트 `test/data/dp_web_table_test.dart:118-123`
- 무엇: `empty` 가 선택 파라미터라 넘기지 않으면 "헤더만 남는다". 계획 Review Focus 2 는 "헤더만 남은 빈 표는 「목록이 비었다」를 전달하지 못한다"를 막으라고 적었는데, 구현의 **기본 동작이 그 상태**이고 테스트('행이 없고 empty 가 없으면 헤더만 남는다')가 그것을 계약으로 고정했다.
- 실패 시나리오: P4 에서 표 25곳을 옮기며 한 곳이라도 `empty:` 를 빠뜨리면 검색 결과 0건 화면이 "제목 / 댓글 / 작성" 헤더 한 줄만 떠 있는 상태가 되고, 스크린리더는 "비었다"에 해당하는 어떤 문구도 읽지 않는다.
- 제안: `empty` 를 `required` 로 올리거나(가장 싸고 확실하다), null 일 때 `DpEmpty` 기본 문구로 폴백한다. 부수적으로, `empty` 를 그릴 때는 `LayoutBuilder`·가로 패딩을 통째로 건너뛰므로 `DpPanel`(기본 padding 0) 안에서 빈 문구가 테두리에 붙는다 — 행들의 `DpSpacing.lg` 가로 여백과 맞춰 주는 편이 낫다.

### [Minor] 행 셀 개수 불일치가 `RangeError` 로만 드러난다

- 위치: `packages/dp_design/lib/src/data/dp_web_table.dart:12-13,67-70`
- 무엇: `DpTableRowSpec.cells` 길이가 칼럼 수와 같아야 한다고 doc 에만 적혀 있고 `assert` 가 없다.
- 실패 시나리오: 칼럼 3개 표에 셀 2개짜리 행을 넣으면 `_cells` 안 `children[i]` 에서 `RangeError (index): Invalid value: Not in inclusive range 0..1: 2` 가 나고, 스택이 비공개 헬퍼를 가리켜 호출부를 찾기 어렵다. P4 에서 행을 데이터로 생성할 때 흔한 실수다.
- 제안: `_Row.build` 또는 `DpWebTable.build` 맨 앞에 `assert(rows.every((r) => r.cells.length == columns.length), 'DpWebTable: cells 길이는 columns 길이와 같아야 한다')`.

### [Minor] 새 리터럴 치수 — 타입 스케일에 이미 같은 값이 있다

- 위치: `dp_status_text.dart:40`(`fontSize: 12`) · `dp_web_table.dart:108`(`fontSize: 12`) · `dp_row_line.dart:59`(`fontSize: 13`) · `dp_row_line.dart:34`·`dp_list_lines.dart:44`(`vertical: 10`) · `dp_key_values.dart:34`(`SizedBox(height: 6)`) · `dp_web_table.dart:25`(`minWidth = 640`)
- 무엇: 계획 Global Constraints 는 "치수는 토큰 상수로만 … 리터럴 숫자를 새로 쓰지 않는다"인데 7군데에 새 리터럴이 들어갔다(계획 본문의 코드 샘플 자체가 그렇게 적혀 있어 구현이 충실히 따른 결과다). `DpTypography` 에는 이미 `labelMedium` = 12px/height 16/12/w600, `bodySmall` = 13px/height 20/13 이 있다.
- 실패 시나리오: `DpStatusText` 의 맨 `TextStyle(fontSize: 12, w600)` 은 `height` 가 없어 상속된 `bodyMedium`(height 1.6)을 쓴다. 같은 표 행에서 숫자 셀(상속 1.6 → 줄 높이 22.4)과 상태 셀(1.6 → 19.2)의 줄 상자가 달라져 세로 중심이 어긋나고, `labelMedium` 을 쓴 다른 화면의 12px 문구(height 16/12 = 1.333)와도 다른 행 높이가 나온다. 나중에 타입 스케일을 조정해도 이 세 곳만 따라오지 않는다.
- 제안: `text.labelMedium?.copyWith(color: …)` / `text.bodySmall?.copyWith(color: …)` 로 바꾼다. `10`·`6`·`640` 은 진짜 토큰이 없으므로 `DpDensity.listRowPadding = 10` 같은 상수를 하나 추가하는 편이 낫다. 덧붙여 `dp_list_lines.dart:8-10` 의 "토큰 상수가 없는 **유일한** 치수다"라는 주석은 사실이 아니다(같은 값이 `dp_row_line.dart:34` 에도 있다) — 주석을 고치거나 상수를 뽑아 실제로 유일하게 만든다.

### [Minor] `DpLink` 의 시맨틱스 `focused` 가 실제 포커스가 아니라 "포커스 하이라이트"에 묶여 있다

- 위치: `packages/dp_design/lib/src/content/dp_link.dart:118-130`
- 무엇: `focused: _focused` 인데 `_focused` 를 채우는 것은 `onShowFocusHighlight` 다. 이 콜백은 `FocusManager.instance.highlightMode` 가 `traditional` 일 때만 불린다(구현 주석도 `onShowHoverHighlight` 에 대해 같은 사실을 적고 있다 — 두 콜백이 같은 `_canShowHighlight` 게이트를 공유한다). 그리고 바깥 `Semantics(excludeSemantics: true)` 가 `FocusableActionDetector` 내부 `Focus` 의 올바른 `isFocusable`/`isFocused` 노드를 지워 버려, 손으로 선언한 이 플래그가 유일한 진실이 된다.
- 실패 시나리오: 하이라이트 모드가 `touch` 인 상태(터치 기기 + 스크린리더, 또는 키 입력 없이 `requestFocus()` 로 포커스를 옮긴 직후)에서 위젯은 포커스를 갖는데 시맨틱스 노드는 `isFocused: false` 를 보고한다. Flutter 웹 엔진은 이 플래그로 DOM 포커스를 맞추므로 AT 의 포커스가 프레임워크 포커스를 따라가지 못한다. 또 `Semantics` 에 `onFocus` 가 없어 스크린리더가 DOM 쪽에서 포커스를 옮겼을 때 프레임워크 포커스가 따라오지도 않는다. (Tab 키를 쓰는 데스크톱 경로는 키 입력이 모드를 `traditional` 로 바꾸므로 정상이고, `dp_link_test.dart:115-124` 가 그 경로만 덮고 있다.)
- 제안: 링 표시는 지금대로 `onShowFocusHighlight` 로 두되, 시맨틱스 `focused` 는 `FocusableActionDetector(onFocusChange:)` 가 주는 **실제 포커스**로 갈아끼운다(상태 두 개). 여력이 되면 `Semantics(onFocus: () => _node.requestFocus())` 도 함께.

### [Minor] `DpPanel.title` 이 자유 Widget 이라 "heading + button 병합" 함정을 다시 열어 둔다

- 위치: `packages/dp_design/lib/src/layout/dp_panel.dart:18,48-54`
- 무엇: `title` 이 `Widget?` 인데 통째로 `Semantics(header: true)` 아래 놓인다. `Semantics` 는 기본 `container: false` 라 자식 노드가 하나면 거기에 병합되지만(그래서 `Text` 단독인 현재 테스트는 `matchesSemantics(label: …, isHeader: true)` 로 통과한다), 자식 노드가 둘 이상이면 **라벨 없는 header 컨테이너**가 생긴다.
- 실패 시나리오: P4 에서 `DpPanel(title: Row(children: [Text('이번 주 과제'), TextButton(…'전체 보기')]))` 같은 흔한 패널 제목행을 만들면, 스크린리더가 빈 제목(heading level, 텍스트 없음) → '이번 주 과제' → '전체 보기 버튼' 순으로 읽는다. 스펙 §7 이 "먼저 대조하라"고 지목한 2026-09-17 웹 시맨틱 함정 5건 중 1번(heading+button 병합)과 같은 계열이다.
- 제안: `DpPageHeader` 처럼 `title` 을 `String` 으로 받고 액션은 별도 슬롯(`titleTrailing`)으로 분리하거나, 헤더 플래그를 텍스트만 감싸도록 좁힌다. 최소한 doc 에 "title 에는 단일 텍스트만"이라고 못 박고 `assert` 대신 테스트로 고정한다.

### [Minor] 좁은 폭에서 `DpRowLine` 의 컨트롤이 우측이 아니라 좌측으로 떨어진다

- 위치: `packages/dp_design/lib/src/data/dp_row_line.dart:40-41`
- 무엇: `Wrap(alignment: WrapAlignment.spaceBetween)` 은 한 run 에 자식이 하나뿐이면 `childLeadingSpace = 0` 이라 **선두 정렬**이 된다.
- 실패 시나리오: 390px 에서 라벨+설명 블록과 스위치가 두 run 으로 갈리는 순간, doc(:8)과 DESIGN.md:280 이 약속한 "우 컨트롤"이 아니라 스위치가 라벨 왼쪽 아래에 붙는다. 설정 목록에서 여러 행이 섞이면 어떤 행은 오른쪽, 어떤 행은 왼쪽에 컨트롤이 있어 스캔이 어긋난다. 현재 390px 테스트는 예외 없음·폭 ≤ 390 만 보므로 잡지 못한다.
- 제안: `trailing` 을 `Align(alignment: Alignment.centerRight, widthFactor: 1, …)` 로 감싸거나(★`widthFactor: 1` 없이는 P2 에서 겪은 "Wrap 안의 Align 이 최대 폭까지 늘어난다" 함정에 다시 걸린다★), 두 run 이 되는 폭에서는 `alignment: WrapAlignment.end` 로 전환한다. 테스트는 `tester.getTopRight(find.byType(Switch)).dx` 를 행 우측 경계와 비교한다.

### [Minor] hover 배경이 패널 밖에서는 사실상 보이지 않는다

- 위치: `dp_web_table.dart:143` · `dp_list_row.dart:227`
- 무엇: hover 색이 `c.surfaceMuted` 고정이다. 배경 대비는 `surface` 위에서 1.12:1, `bg` 위에서 **1.046:1**(직접 계산).
- 실패 시나리오: 표·목록을 `DpPanel`(=`surface`) 없이 페이지 배경(`bg` #F6F7FB) 위에 바로 올리면 hover 가 사실상 보이지 않아 "이 행이 클릭 가능하다"는 유일한 시각 신호가 사라진다(제목 링크의 hover 밑줄만 남는다). P4 의 화면 재구성에서 표를 패널에 넣지 않는 선택이 언제든 가능하다.
- 제안: 문서/doc 주석에 "`DpWebTable`·`DpListRow` 는 `surface` 면 위에 놓는다"를 명시하거나, hover 를 배경색 대신 `surfaceMuted` 와 `border` 조합(좌측 1px 표시선 등)으로 바꾼다.

### [Minor] 이름이 더 이상 맞지 않는 테스트 1건

- 위치: `packages/dp_design/test/data/dp_list_row_test.dart:31-43`
- 무엇: `'DpListRow: hover/focus 베이스(FocusableActionDetector) 존재'` 가 `findsWidgets` 로 여전히 통과하는데, 그 `FocusableActionDetector` 는 이제 행이 아니라 **`DpLink` 내부**의 것이다. 원장 Task 8 Ruling 이 이 테스트를 단서로 DpLink 결함을 찾아낸 것은 좋았으나, 테스트 자체는 갱신되지 않았다.
- 실패 시나리오: 나중에 `DpLink` 를 `InkWell` 등으로 바꾸면 이 테스트가 "행의 hover/focus 베이스가 사라졌다"고 오독되는 신호를 낸다. 반대로 행에서 포커스 기반이 정말 사라져도 이 테스트는 알려 주지 않는다.
- 제안: 이름을 `'제목 링크가 키보드 포커스 기반을 갖는다'` 로 바꾸고 `find.descendant(of: find.byType(DpLink), matching: find.byType(FocusableActionDetector))` 로 대상을 좁힌다.

### [Minor] 구현을 그대로 되읽는 단언 2건

- 위치: `test/states/dp_status_text_test.dart:34-42` · `test/data/dp_web_table_test.dart:102-106`
- 무엇: 전자는 `fontSize == 12`·`fontWeight == w600` 을 구현 리터럴과 1:1로 되읽는다(색 3건은 토큰 매핑이라 의미가 있다). 후자는 Review Focus 1 의 핵심 단언인데 `tester.widget<SizedBox>(…).width` 로 **선언값**을 읽는다 — 실제로 배치된 폭이 아니다.
- 실패 시나리오: 후자는 `_cells` 가 `SizedBox` 를 `Expanded` 안에 넣는 식으로 망가져 실제 렌더 폭이 72 가 아니게 되어도 그대로 통과한다. "숫자 칼럼 폭을 지킨다"는 계약을 지키지 못한다.
- 제안: 후자를 `tester.getSize(commentCell.first).width` 로 바꾼다(같은 값이 나오되 이번엔 레이아웃 결과다). 전자는 `labelMedium` 채택(위 리터럴 항목)과 함께 `expect(style.fontSize, text.labelMedium!.fontSize)` 식으로 스케일에 묶는다.

### [Minor] `DpInteractiveCard` 가 프로덕션 소비처를 잃었는데 DESIGN.md 는 여전히 "클릭 카드 베이스"로 가리킨다

- 위치: `packages/dp_design/lib/src/interaction/dp_interactive_card.dart` · `DESIGN.md:177`
- 무엇: 실측 grep 결과 `DpInteractiveCard` 를 참조하는 곳은 자기 파일, 자기 테스트, `dp_list_row.dart:11` 의 주석, 그리고 "없어야 한다"를 단언하는 새 테스트뿐이다. `apps/web`·`apps/admin` 에는 0건.
- 실패 시나리오: DESIGN.md §(레이어 0) 을 읽은 다음 사람이 P4 에서 "클릭 카드 베이스는 `DpInteractiveCard`"라는 안내를 따라, 카드를 쓰지 않기로 한 웹 문법에 카드를 다시 들인다.
- 제안: P3 범위를 넘지 않는 선에서 DESIGN.md:177 에 "웹 화면에서는 쓰지 않는다(S3-P3) — 카드가 곧 인터랙션인 경우에만" 한 줄을 덧붙인다. 위젯 삭제 자체는 P4/P5 정리 대상으로 남겨도 된다.

## Review Focus 판정

1. **긴 제목이 숫자 칼럼을 밀어내지 않는가 — OK (단서 하나)**
   구조상 보장된다: 고정폭 칼럼은 `SizedBox(width:)`, 유연 칼럼은 `Expanded`(= tight, 남은 폭 그대로)라 제목이 아무리 길어도 숫자 칼럼을 밀 수 없고, 남는 폭이 부족하면 줄어드는 쪽은 언제나 제목이다. `minWidth` 미만에서도 `SizedBox(width: minWidth)` 가 공간을 보장한다. 단서 = `numeric: true` + `width: null` 조합에서 우측 정렬이 빠진다(Minor 참조). 테스트는 줄바꿈은 실측하지만 칼럼 폭은 선언값을 되읽는다(Minor 참조).

2. **행 0개인 표가 「비었다」를 전달하는가 — 조건부. `empty` 를 넘긴 호출부만.**
   `empty` 가 선택 파라미터라 기본 동작이 "헤더만 남기기"이고, 테스트가 그 동작을 계약으로 고정했다. 위젯 스스로는 전달하지 않는다. `required` 로 올리기를 권한다(Minor 참조).

3. **390px 에서 본문이 가로로 넘치지 않는가 — 넘치지 않는 것은 OK. 다만 잘렸다는 표시가 없다.**
   `LayoutBuilder` + `SingleChildScrollView` 로 표만 자체 스크롤하고 `DpWebTable` 자신의 폭은 390 이하임을 테스트가 실측한다(내가 직접 재실행해 확인). `DpRowLine` 도 `Wrap` 으로 390 에서 예외 없이 접힌다(실측). 문제는 어포던스 — 레포 자체 `DpScrollbar` 미사용(Important 참조)과 좁은 폭에서 컨트롤이 왼쪽으로 떨어지는 `Wrap` 정렬(Minor 참조).

4. **표·목록 행이 스크린리더에서 한 덩어리로 읽히지 않는가 — OK.**
   `GestureDetector(excludeFromSemantics: true)` 로 행 제스처 노드를 없애 셀 조각이 흡수되지 않는다. `dp_web_table_test.dart:143-160` 이 `onTap` 이 있는 행에서 셀 3개가 각각 별도 라벨로 남는지를 실제 시맨틱스 트리로 확인한다(구현 되읽기가 아닌 진짜 거동 테스트). `DpListRow` 도 같은 처리이고 접근성 컨트롤은 `DpLink.title` 이 맡는다. `DpListLines`·`DpKeyValues`·`DpRowLine` 에는 `MergeSemantics` 가 없어 병합 위험이 없다. 원장 Task 4 Ruling 의 판단에 동의한다.

5. **다크 테마에서 구분선·hover 배경이 각 테마 토큰을 쓰는가 — OK.**
   새 위젯 전부가 색을 `context.dpColors` 에서만 가져오고 `Colors.*`·리터럴 색이 0건이다(grep 실측). `dp_panel_test`·`dp_web_table_test` 가 다크에서 `DpColors.dark.border`/`surface` 를 단언하고 "라이트 값이 새어 들어오지 않았는지"까지 못 박는다. 다만 **라이트 쪽에 대비 미달이 하나 있다**(표 헤더 `textFaint` 3.52:1, Important 참조) — 다크는 5.18:1 로 통과하므로 이 결함은 라이트에서만 드러난다.

## 원장 Ruling 에 대한 이견

대부분 동의한다. 아래 3건만 보탠다.

- **Task 10(같은 라벨 액션 2개) — 부분 이견.** "제품 결정이라 P3 범위 밖"이라는 판단 자체는 받아들이지만, 같은 커밋의 테스트가 `web_community_board_projection_test.dart` 에서 빈 상태 CTA 탭 → `composed == 1`, 헤더 버튼 탭 → `composed == 2` 로 **둘이 있다는 것을 계약으로 고정**했다. P4 에서 하나를 지우려면 이 테스트를 되돌려야 하므로, 보류가 아니라 굳히기가 됐다. 최소한 이 단언에 `// P4 에서 하나로 줄인다` 주석을 달거나, 빈 상태 CTA 의 라벨을 헤더와 다르게(예: '첫 글 쓰기') 두는 편이 낫다 — 한 화면에 접근명이 완전히 같은 버튼 둘은 스크린리더 사용자가 구분할 방법이 없다.
- **Task 9(검색어 유실) — 동의하되 보완 필요.** 사용자가 P4 로 넘긴 결정에 이견은 없다. 다만 이번 커밋이 `'검색 중 제목 메뉴로 게시판을 바꾸면 같은 검색어를 새 게시판에서 다시 조회한다'` 테스트를 **삭제**해, "게시판을 바꿔도 q 가 살아남는다"에 대한 커버리지가 레포에서 0 이 됐다. P4 에서 셸 헤더가 q 를 들고 가게 만들 때 실패로 이끌어 줄 테스트가 없다. 원장의 P4 이월 목록에 문장으로는 남아 있으나, `skip: 'S3-P4'` 로 테스트를 남겨 두는 편이 안전하다.
- **Task 4(행 제스처 시맨틱스 제외) — 동의, 관측 한 줄 추가.** 판단과 근거 모두 옳다. 다만 부수효과로 **행 클릭이 접근성 트리에서 완전히 사라지므로 browser-ux 러너가 행 단위 컨트롤을 더 이상 볼 수 없다.** P5 기준선 재기록 때 "행이 클릭 대상"을 기대하는 시나리오가 있으면 함께 고쳐야 한다 — P5 이월 목록에 한 줄 추가를 권한다.

## NEEDS_CONTEXT

- **시안 정본(Artifact `DWi8kMV6QcAzBEQwbrNPNd`)을 직접 읽지 못했다.** 따라서 "시안과 1:1인가"류 판정(`.panel` 제목행에 액션이 있는지, `.kv` 의 키 길이 상한, `.st` 의 12px·600, 표 헤더의 회색 톤)은 전부 **계획 문서에 옮겨 적힌 값**을 근거로 했다. 위 Important 4번(표 헤더 대비)은 시안이 실제로 그 톤을 지정했다면 "시안 대 접근성 계약"의 충돌로 승격되며, 그 판단에는 시안 확인이 필요하다.
