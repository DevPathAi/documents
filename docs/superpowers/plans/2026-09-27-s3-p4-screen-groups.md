# S3-P4 화면군별 웹 재구성 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `apps/web` 의 20화면을 시안(`Leva 웹 문법 시안`)의 웹 문법 — 패널 한 겹 테두리·2열 `.cols`·760 `.narrow`·표·구분선 목록 — 으로 재구성하면서 **기존 기능을 하나도 잃지 않는다**. 3개 PR(학습 / 커뮤니티 / 계정·온보딩)로 나눠 `develop` 에 넣는다.

**Architecture:** P3 이 만든 `dp_design` 프리미티브 7종(`DpPanel`·`DpWebTable`·`DpListLines`·`DpRowLine`·`DpKeyValues`·`DpLink`·`DpStatusText`)은 현재 `apps/web` 에 **소비처가 0곳**이다. P4 는 그것을 화면에 배선하는 단계다. 셸(`DpWebShell`, P2)이 이미 좌우 패딩(`compact? DpSpacing.lg : DpSpacing.xl`)·`DpMaxWidth(contentMaxWidth=1120)`·브레드크럼을 주므로 **화면은 폭·좌우 패딩·브레드크럼을 다시 만들지 않는다**. 화면은 셸이 넘긴 본문 폭 안에서 `.cols`(2fr/1fr) 또는 `.narrow`(760)만 고른다. 상태 분기(로딩·실패·빈 목록)와 컨트롤러 배선은 그대로 두고 표현부만 바꾼다.

**Tech Stack:** Flutter 3.44.1(CI 핀) · Dart pub workspaces + melos 7 · `flutter_test` 위젯 테스트 · CI `analyze-test`·`browser-ux`·`perf-gate`·`produce-atomic-pair`·`web-image-config-contract`

**Spec:** `docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` (§5.3 웹 문법, §7 P4, §8 게이트, §10 하지 않는 것)

**시안 정본:** Artifact `DWi8kMV6QcAzBEQwbrNPNd` Version 2 (`Leva 웹 문법 시안 · 20화면`). 치수·색은 그 CSS 에서 직접 옮긴다. 프레임 기본은 `data-hit="24"`(촘촘 = `--hit:30px`·`--rowpad:8px`)·`data-head="dark"`·본문 `max-width:1120`·`.prose`/`.narrow` `max-width:760`·compact 경계 `@container (max-width:720px)`.

**앞 단계 산출물:** P3 핸드오프 `handoff-2026-09-27-s3-p3-web-widgets-merged.md` · P3 계획 `plans/2026-09-27-s3-p3-web-widgets.md` · P3 리뷰 `plans/2026-09-27-s3-p3-web-widgets/review-report.md`

---

## Global Constraints

이 절은 모든 Task 의 요구사항에 암묵적으로 포함된다.

### 결정 사항 (2026-09-27 사용자 결정)

- **기능 보존이 시안 충실도보다 앞선다.** 시안에 없는 기존 기능(추세 라인차트·주간 학습량·KPI 카드·Bento 그리드·광고 슬롯·경로 설계 근거·완료한 주차 등)을 **지우지 않는다.** 시안 문법으로 감싸 재배치한다. 화면당 패널이 시안보다 1~3개 많아지는 것은 정상이다.
- **장식은 기능이 아니다.** 순수 장식(로그인 화면의 `_DecorativeOrb`, `_panel()` 의 `boxShadow`)은 시안 문법으로 바꿀 때 사라져도 된다. 단 **무엇을 왜 지웠는지 각 Task 의 Ruling 에 적는다.**
- **시안에만 있는 요소는 전부 구현한다.** 「이번 주 과제」 표 · 「진행」 키-값 · 「왜 이 순서인가요」 · 「막히면」 링크 목록. 네 가지 모두 **이미 내려오는 데이터**로 만든다 — `mission.tasks` · `DashboardSummary` · `PathMilestone.whyThisOrder` · 기존 라우트. **새 API 호출을 추가하지 않는다.**
- **시안 파생 규칙(시안에 없는 5화면).** 시안을 보강하지 않고, 아래 파생 근거를 따른다:
  - 자유글 작성(`post_create_page`) · 글 수정(`post_edit_page`) · 질문 수정(`question_edit_page`) → 시안 `write`(질문 작성) 문법에서 파생. `.narrow` + `.form` + `.fld` + 하단 `.acts`. 수정 화면은 `write` 와 같되 제출 라벨만 바꾼다.
  - 인증 콜백(`auth_callback_page`) · `placeholder_page` → 시안 `beta`(베타 대기) 문법에서 파생. `.narrow.center` 중앙 정렬 한 열.
- **P4 는 3 PR·1계획이다.** PR 경계를 넘는 커밋을 만들지 않는다. 각 PR 은 `develop` 에서 분기해 `develop` 으로 PR 하고, CI 6잡이 **전부 녹색인 것을 확인한 뒤** 기본 merge commit 으로 머지한다.

### 치수·색

- 치수는 토큰 상수로만 쓴다: `DpSpacing`(4·8·12·16·24·32·48) · `DpRadius`(chip 4·button 6·card 8·input 6·dialog 12) · `DpDensity`(controlHeight 30·rowPadding 8·minTarget 24) · `AppTokens`(contentMaxWidth 1120·readableMaxWidth 760·headerHeight 56). **새 리터럴 숫자를 쓰지 않는다.**
- 색은 `DpColors` 토큰으로만 쓴다. **`textFaint` 를 본문·라벨 텍스트에 쓰지 않는다** — 라이트에서 3.52:1 로 WCAG AA 미달이다(P3 실측). 보조 텍스트는 `textSecondary`(5.93:1).
- **대비는 라이트와 다크 둘 다 잰다.** P3 에서 다크만 보고 라이트 미달을 놓쳤다.
- 그림자를 쓰지 않는다 — 시안의 면 구분은 1px 테두리 한 겹뿐이다.

### 셸과의 경계

- 화면은 `DpMaxWidth`·`ConstrainedBox(maxWidth: …)`·좌우 페이지 패딩을 **새로 만들지 않는다.** 셸이 이미 준다. 화면 안에서 더 좁히는 것(`.narrow` 760, `.prose` 760)만 화면의 몫이다.
- 화면은 브레드크럼을 그리지 않는다. `breadcrumbFor(location)`(`app_shell.dart`)이 셸에서 그린다.
- `DpPageHeader` 는 자체 좌우 패딩(`compact? lg : xl`)을 갖고 있어 셸 패딩과 **이중**이 된다. Task 1 에서 `DpPageHeader` 의 좌우 패딩을 0 으로 내리고 상하만 남긴다(시안 `.ph` 에는 패딩이 없다 — `.main` 의 24가 유일하다).

### 로컬 도구 함정 (P3 실측)

- **`git add -A <경로>` 를 쓰지 않는다.** 로컬 Flutter 3.47 이 `analysis_options.yaml` 3개와 `pubspec.lock` 을 명령마다 다시 쓴다(CI 는 3.44.1 핀). 명시 경로만 `git add` 한다.
- 검증은 파일 **개수**가 아니라 `git diff origin/develop HEAD --name-only` **목록**으로 한다.
- **되돌림은 되돌린 직후 다른 명령 없이 커밋한다.** 되돌린 뒤 `flutter test` 를 한 번 돌리면 로컬 툴이 같은 블록을 다시 써 넣는다.
- `dart format` 에 디렉터리를 넘기지 않는다 — 로컬 3.47 과 CI 3.44 포매터가 갈리는 파일이 있다. 내가 만든 파일만 지정한다.
- `python` 은 스텁이다(rc0·무출력). `py` 를 쓴다.

### 테스트 함정 (P3 실측)

- `find.byType` 은 **정확한 런타임 타입**만 잡는다 — `FilledButton.icon` 은 서브클래스라 안 걸린다.
- 같은 `ValueKey` 를 형제로 두면 `Duplicate keys found` 로 죽는다. 항목을 비공개 위젯 한 겹으로 감싼다.
- `testWidgets` 의 `skip` 은 `bool` 이다.
- `GestureDetector` 는 `excludeFromSemantics: true` 가 없으면 자식 셀의 시맨틱스를 흡수한다. `MergeSemantics` 는 라벨에 빈 조각을 붙인다.

### 기준선 영향 (P5 로 넘길 목록을 각 Task 가 갱신한다)

`WebCommunityBoardProjection`(`web_community_board_projection.dart`)과 `WebContentProjection`(`content_page.dart`)은 **ET13 증거용 결정적 투영**이다. 이 둘의 렌더가 바뀌면 ET13 visual/a11y baseline 재승인(사람 단계)이 필요하다. P4 는 baseline 을 **재기록하지 않는다** — 바뀐 화면을 `docs/superpowers/plans/2026-09-27-s3-p4-screen-groups/baseline-impact.md` 에 누적해 P5 에 넘긴다.

---

## Review Focus

이 다섯 가지는 스펙이 요구하지만 어느 Task 의 테스트도 저절로 다루지 않는다. 각 줄마다 그 코드를 가진 Task 에 테스트를 붙였다.

1. **390px 에서 본문이 가로로 넘치지 않는가.** `.cols` 가 1열로 접히고, 표만 자체 가로 스크롤을 갖는다(`DpWebTable.minWidth`). → Task 2·3·10·17 의 390px 폭 테스트.
2. **200% 배율에서 패널이 깨지지 않는가.** 280px 사이드 패널 + 큰 배율에서 `DpKeyValues`·`DpRowLine` 이 RenderFlex 오버플로 없이 접히는지. → Task 2·17 의 `textScaler` 2.0 테스트.
3. **콘텐츠 진행률이 레이아웃 변경 뒤에도 같은 값을 서버로 보내는가.** `_scrollPct` 가 `_headerKey` 로 헤더 높이를 실측해 분자·분모에서 뺀다. 헤더를 패널로 감싸면 그 높이가 바뀐다. → Task 4 의 기존 회귀 테스트 재실행 + 새 경계 테스트.
4. **표·목록 행이 스크린리더에서 칼럼별로 읽히는가.** 행 제스처는 시맨틱스에서 빠지고 접근성 컨트롤은 제목의 `DpLink.title` 이다. → Task 8 의 시맨틱스 트리 테스트.
5. **빈 목록·실패·로딩 상태가 각 화면에서 여전히 도달 가능한가.** 상태 분기를 패널 안으로 옮기는 과정에서 `SliverFillRemaining` 분기가 사라지기 쉽다. → Task 2·8·10 의 상태별 테스트.

---

## 시안 20화면 ↔ 앱 화면 대조표

각 Task 는 이 표의 한 줄 이상을 담당한다. 「골격」은 시안의 최상위 레이아웃 클래스다.

| 시안 | 골격 | 앱 파일 | PR | Task |
|---|---|---|---|---|
| `today` 오늘 | `.next` + `.cols` | `dashboard/presentation/dashboard_page.dart` · `widgets/dashboard_body.dart` · `widgets/today_mission_section.dart` | A | 2 |
| `path` 학습 경로 | `.cols` | `path/presentation/path_page.dart` · `mission_path_plan_view.dart` · `path_plan_view.dart` | A | 3 |
| `ptoday` 경로·이번 주 | `.cols` | `mission_path_plan_view.dart` (`_AvailablePath`) | A | 3 |
| `content` 콘텐츠 읽기 | `.cols` + `.prose` | `content/presentation/content_page.dart` | A | 4 |
| `sandbox` 실습 | `.ide` | `sandbox/presentation/sandbox_page.dart` · `sandbox_layout.dart` | A | 5 |
| `mentor` AI 멘토 | `.cols` + `.chat` | `mentor/presentation/mentor_page.dart` | A | 6 |
| `free` 자유게시판 | `.filters` + `.panel` 표 | `community/presentation/community_home_page.dart` · `web_community_board_projection.dart` | B | 8 |
| `qna` Q/A | `.filters` + `.panel` 표 | 위와 같음 | B | 8 |
| `feedback` 피드백 | `.filters` + `.panel` 표 | 위와 같음 | B | 8 |
| `post` 글 상세 | `.narrow` | `community/presentation/post_detail_page.dart` | B | 10 |
| `detail` 질문 상세 | `.cols` | `community/presentation/qna_detail_page.dart` | B | 10 |
| `write` 질문 작성 | `.narrow` + `.form` | `community/presentation/question_create_page.dart` | B | 11 |
| (파생) 자유글 작성 | `.narrow` + `.form` | `community/presentation/post_create_page.dart` | B | 11 |
| (파생) 글 수정 | `.narrow` + `.form` | `community/presentation/post_edit_page.dart` | B | 11 |
| (파생) 질문 수정 | `.narrow` + `.form` | `community/presentation/question_edit_page.dart` | B | 11 |
| `login` 로그인 | `.login` | `auth/presentation/login_page.dart` | C | 14 |
| (파생) 인증 콜백 | `.narrow.center` | `auth/presentation/auth_callback_page.dart` | C | 14 |
| `consent` 동의 | `.narrow` + `.chk` | `consent/presentation/consent_page.dart` | C | 15 |
| `beta` 베타 대기 | `.narrow.center` | `beta/presentation/beta_pending_page.dart` | C | 15 |
| `dstart` 진단 시작 | `.narrow` + `.steps` + `.opt` | `diagnostic/presentation/diagnostic_page.dart` (`_StartView`) | C | 16 |
| `dq` 진단 문항 | `.narrow` + `.steps` + `.opt` | 위와 같음 (`_QuestionView`) | C | 16 |
| `dresult` 진단 결과 | `.narrow` + `.steps` + `.bars` + `.next` | 위와 같음 | C | 16 |
| `mypage` 마이페이지 | `.cols` | `mypage/presentation/mypage_page.dart` | C | 17 |
| `settings` 설정 | `.narrow` + `.rowline` | `settings/presentation/settings_page.dart` | C | 17 |
| (파생) placeholder | `.narrow.center` | `common/presentation/placeholder_page.dart` | C | 17 |

### 실측 교정

- 핸드오프·메모리가 적은 「Material `Card(` **25곳**」은 실재하지 않는다. `apps/web` 의 `Card(` 는 **7곳**(6파일)이고 `origin/main`·P1·P2·P3 전 시점에서 같다. 그 수치는 P3 계획 본문이 실측 없이 쓴 것이 핸드오프·메모리로 전파된 것이다. 실제 규모는 **신설 위젯 7종 소비처 0곳** + `BoxDecoration` 22 · `ConstrainedBox` 13 · `maxWidth` 17 이다.
- `Card(` 7곳: `community/presentation/lcs_context.dart`(2) · `community/presentation/widgets/content_tombstone.dart` · `question_create_page.dart` · `qna_detail_page.dart` · `post_detail_page.dart` · `ads/presentation/ad_slot_widget.dart`.
- `apps/admin` 의 `Card(` 2곳(`reports_page.dart`·`admin_access_frame.dart`)은 **범위 밖**이다 — 스펙 §10 「관리자 앱을 바꾸지 않는다」.

---

# PR-A — 학습 (오늘·경로·콘텐츠·실습·멘토)

브랜치: `feat/s3-p4-learning-screens` (base: `develop`)

---

## Task 1: dp_design 준비 — 이월 Minor 수정 + `DpCols` 신설 + `DpPageHeader` 패딩 정리

P3 리뷰가 남긴 Minor 중 **화면에 걸리는 것**만 닫고, 6화면이 쓸 2열 레이아웃 프리미티브를 만든다. 이 Task 없이 Task 2 를 시작하면 표의 `empty` 누락·우측 정렬 실종이 화면마다 번진다.

**Files:**
- Modify: `packages/dp_design/lib/src/data/dp_web_table.dart`
- Modify: `packages/dp_design/lib/src/layout/dp_panel.dart`
- Modify: `packages/dp_design/lib/src/layout/dp_page_header.dart`
- Modify: `packages/dp_design/lib/src/content/dp_link.dart`
- Create: `packages/dp_design/lib/src/layout/dp_cols.dart`
- Modify: `packages/dp_design/lib/dp_design.dart`
- Test: `packages/dp_design/test/data/dp_web_table_test.dart`
- Test: `packages/dp_design/test/layout/dp_panel_test.dart`
- Test: `packages/dp_design/test/layout/dp_page_header_test.dart`
- Test: `packages/dp_design/test/content/dp_link_test.dart`
- Test: `packages/dp_design/test/data/dp_list_row_test.dart` (테스트 이름·단언 1건)
- Create: `packages/dp_design/test/layout/dp_cols_test.dart`

**Interfaces:**
- Consumes: 없음 (이 PR 의 첫 Task)
- Produces:
  - `DpCols({Key? key, required Widget main, required Widget side})` — expanded/large 에서 `2fr / 1fr` 2열(간격 `DpSpacing.xl`), 그 미만에서 `main` → `side` 1열.
  - `DpSide({Key? key, required List<Widget> children})` — 사이드 칼럼 세로 스택(간격 `DpSpacing.lg`).
  - `DpPanelTitle(String text, {Key? key})` — 패널 제목 텍스트에만 heading 플래그를 준다.
  - `DpWebTable({Key? key, required List<DpTableColumn> columns, required List<DpTableRowSpec> rows, required Widget empty, double minWidth = 640})` — `empty` 가 **필수**가 된다. `const` 생성자가 아니게 된다.
  - `DpPageHeader` 서명은 그대로. 좌우 패딩만 0 이 된다.

### Minor 처리 판정 — 이 Task 에서 10건 전부 결론낸다

| # | 리뷰 Minor | 판정 |
|---|---|---|
| 1 | `numeric: true` + `width: null` 이면 우측 정렬이 조용히 사라진다 | **수정** (Step 1~4) |
| 2 | 빈 표의 기본값이 곧 실패 상태(`empty` 가 선택 파라미터) | **수정** — `required` 로 올린다 (Step 5~8) |
| 3 | 행 셀 개수 불일치가 `RangeError` 로만 드러난다 | **수정** — `assert` 추가 (Step 9~12) |
| 4 | 새 리터럴 치수 7군데(`fontSize: 12` 등) | **이월(P5)** — 내부 치수라 화면에 걸리지 않는다. 토큰으로 바꾸면 렌더가 같아야 하므로 기준선 재기록 단계에서 함께 확인하는 것이 싸다. |
| 5 | `DpLink.focused` 가 실제 포커스가 아니라 하이라이트 모드에 묶여 있다 | **수정** (Step 13~16) |
| 6 | `DpPanel.title` 이 자유 Widget 이라 heading+button 병합 함정이 열려 있다 | **수정** — P4 가 패널 제목 옆에 액션을 넣는다 (Step 17~20) |
| 7 | 좁은 폭에서 `DpRowLine` 의 컨트롤이 좌측으로 떨어진다 | **기각** — 시안 CSS 와 **같은 거동**이다. `.rowline{display:flex;justify-content:space-between;flex-wrap:wrap}` 에서 컨트롤이 다음 줄로 내려가면 그 줄의 항목이 하나이므로 브라우저도 좌측에 둔다. 시안을 벗어나는 교정은 하지 않는다. |
| 8 | hover 배경이 패널 밖에서는 사실상 보이지 않는다(`bg` 위 1.046:1) | **기각 + 계약 문서화** — 시안 `tbody tr:hover{background:var(--muted)}` 가 정확히 같은 값이다. 대신 `DpWebTable`·`DpListRow` 는 **`DpPanel` 안에서만 쓴다**(= `surface` 위 1.12:1)는 계약을 doc 에 적는다. hover 어포던스는 `DpLink.title` 의 hover 밑줄이 이미 담당한다. |
| 9 | 이름이 더 이상 맞지 않는 테스트 1건 | **수정** (Step 21) |
| 10 | `DpInteractiveCard` 가 소비처를 잃었는데 DESIGN.md 는 여전히 가리킨다 | **이월(P5)** — DESIGN.md §3·§5 개정이 P5 의 명시 범위다. |

- [ ] **Step 1: `numeric` 유연 칼럼의 우측 정렬 실패 테스트를 쓴다**

`packages/dp_design/test/data/dp_web_table_test.dart` 에 추가한다. `_host` 는 그 파일에 이미 있는 헬퍼를 쓴다.

```dart
  testWidgets('DpWebTable: numeric 유연 칼럼도 우측 정렬한다', (tester) async {
    await tester.pumpWidget(
      _host(
        DpWebTable(
          columns: const [
            (label: '제목', width: null, numeric: false),
            (label: '추천', width: null, numeric: true),
          ],
          rows: const [
            (cells: [Text('제목 A'), Text('7')], onTap: null),
          ],
          empty: const Text('비었다'),
        ),
      ),
    );

    final align = tester.widget<Align>(
      find.ancestor(of: find.text('7'), matching: find.byType(Align)).first,
    );
    expect(align.alignment, Alignment.centerRight);
  });
```

- [ ] **Step 2: 테스트를 돌려 red 를 확인한다**

Run: `cd packages/dp_design && flutter test test/data/dp_web_table_test.dart --plain-name "numeric 유연 칼럼도 우측 정렬한다"`

Expected: FAIL — 유연 칼럼은 `Expanded(child: children[i])` 로 끝나 `Align` 이 없다(`Align` 조상을 못 찾아 실패하거나 다른 `Align` 을 잡는다).

- [ ] **Step 3: `_cells` 가 유연 칼럼에도 정렬을 넣게 고친다**

`packages/dp_design/lib/src/data/dp_web_table.dart` 의 최상위 함수 `_cells` 를 아래로 교체한다.

```dart
// `numeric` 은 칼럼 폭과 무관한 약속이다(`DpTableColumn` doc). 고정폭 분기에만
// 정렬을 넣으면 유연 칼럼에서 조용히 좌측 정렬이 된다(P3 리뷰 Minor 1).
List<Widget> _cells(List<DpTableColumn> columns, List<Widget> children) => [
  for (var i = 0; i < columns.length; i++)
    if (columns[i].width == null)
      Expanded(
        child: Align(
          alignment: columns[i].numeric
              ? Alignment.centerRight
              : Alignment.centerLeft,
          child: children[i],
        ),
      )
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
```

- [ ] **Step 4: 테스트를 돌려 green 을 확인한다**

Run: `cd packages/dp_design && flutter test test/data/dp_web_table_test.dart`

Expected: 파일 전체 PASS. `Align` 이 한 겹 더 끼므로 기존 폭 단언이 `Align` 을 잡아 깨지면 `find.ancestor(...).first` 대신 `find.descendant(of: find.byKey(const ValueKey('dp-web-table-row')), matching: …)` 로 좁힌다.

- [ ] **Step 5: 빈 표가 반드시 `empty` 를 그리는 테스트로 바꾼다**

같은 파일의 기존 테스트 `'행이 없고 empty 가 없으면 헤더만 남는다'`(약 118~123행)를 **삭제하고** 아래를 넣는다.

```dart
  testWidgets('DpWebTable: 행이 없으면 empty 를 그리고 헤더를 감춘다', (tester) async {
    await tester.pumpWidget(
      _host(
        DpWebTable(
          columns: const [(label: '제목', width: null, numeric: false)],
          rows: const [],
          empty: const Text('아직 글이 없어요'),
        ),
      ),
    );

    expect(find.text('아직 글이 없어요'), findsOneWidget);
    expect(find.byKey(const ValueKey('dp-web-table-header')), findsNothing);
  });
```

- [ ] **Step 6: 삭제한 계약이 사라진 것을 확인한다**

Run: `cd packages/dp_design && flutter test test/data/dp_web_table_test.dart --plain-name "헤더만 남는다"`

Expected: `No tests match` — 「헤더만 남는다」를 계약으로 고정한 테스트가 없어야 한다. 남아 있으면 Step 7 뒤 실패한다.

- [ ] **Step 7: `empty` 를 필수로 올린다**

`packages/dp_design/lib/src/data/dp_web_table.dart` 의 생성자와 필드:

```dart
  DpWebTable({
    super.key,
    required this.columns,
    required this.rows,
    required this.empty,
    this.minWidth = 640,
  });

  final List<DpTableColumn> columns;
  final List<DpTableRowSpec> rows;

  /// 이 폭보다 좁으면 표만 가로로 스크롤한다(페이지 본문은 넘치지 않는다).
  final double minWidth;

  /// 행이 없을 때 표 대신 보여 줄 것. **필수다** — 헤더만 남은 표는 「목록이
  /// 비었다」를 전달하지 못한다(P3 리뷰 Minor 2: 기본 동작이 곧 실패 상태였다).
  final Widget empty;
```

`_DpWebTableState.build` 의 분기:

```dart
    if (rows.isEmpty) return widget.empty;
```

클래스 doc 에 hover 계약을 덧붙인다(Minor 8 판정):

```dart
/// hover 배경은 `surfaceMuted` 다 — 시안 `tbody tr:hover{background:var(--muted)}`
/// 와 같은 값이다. 그 대비는 `surface` 위에서 1.12:1, `bg` 위에서 1.046:1 이라
/// **이 위젯은 `DpPanel` 안에서만 쓴다.** 행을 클릭할 수 있다는 어포던스는
/// hover 배경이 아니라 제목의 `DpLink.title` hover 밑줄이 담당한다.
```

- [ ] **Step 8: analyze 와 테스트를 돌린다**

Run: `cd packages/dp_design && flutter analyze lib/src/data/dp_web_table.dart && flutter test test/data/dp_web_table_test.dart`

Expected: analyze `No issues found!` · 테스트 PASS. `const DpWebTable(` 를 쓰는 호출부가 있으면 `const` 를 떼라는 에러가 난다 — 현재 소비처는 테스트뿐이다.

- [ ] **Step 9: 셀 개수 불일치 assert 테스트를 쓴다**

```dart
  test('DpWebTable: 셀 개수가 칼럼 수와 다르면 assert 로 막는다', () {
    expect(
      () => DpWebTable(
        columns: const [
          (label: '제목', width: null, numeric: false),
          (label: '추천', width: null, numeric: true),
        ],
        rows: const [
          (cells: [Text('제목만')], onTap: null),
        ],
        empty: const Text('비었다'),
      ),
      throwsA(isA<AssertionError>()),
    );
  });
```

- [ ] **Step 10: 테스트를 돌려 red 를 확인한다**

Run: `cd packages/dp_design && flutter test test/data/dp_web_table_test.dart --plain-name "셀 개수가 칼럼 수와 다르면"`

Expected: FAIL — assert 가 없어 생성자가 조용히 성공한다.

- [ ] **Step 11: 생성자에 assert 를 넣는다**

```dart
  DpWebTable({
    super.key,
    required this.columns,
    required this.rows,
    required this.empty,
    this.minWidth = 640,
  }) : assert(
         // doc 에만 있던 계약을 코드로 올린다. 어기면 배치 중 RangeError 로
         // 터지고, 그 스택에는 원인이 칼럼 정의에 있다는 단서가 남지 않는다.
         // `rows.every` 를 부르므로 이 생성자는 더 이상 const 가 아니다 —
         // 표는 화면당 한두 개라 비용이 무의미하다.
         rows.every((row) => row.cells.length == columns.length),
         'DpTableRowSpec.cells 길이는 columns 길이와 같아야 한다.',
       );
```

- [ ] **Step 12: 테스트를 돌려 green 을 확인한다**

Run: `cd packages/dp_design && flutter test test/data/dp_web_table_test.dart`

Expected: 파일 전체 PASS.

- [ ] **Step 13: `DpLink.focused` 가 실제 포커스를 따르는지 테스트를 쓴다**

`packages/dp_design/test/content/dp_link_test.dart` 에 추가한다. 파일 상단에 `import 'package:flutter/services.dart';` 가 없으면 추가한다.

```dart
  testWidgets('DpLink: 하이라이트 모드가 touch 여도 focused 가 실제 포커스를 따른다', (
    tester,
  ) async {
    FocusManager.instance.highlightStrategy =
        FocusHighlightStrategy.alwaysTouch;
    addTearDown(() {
      FocusManager.instance.highlightStrategy =
          FocusHighlightStrategy.automatic;
    });

    await tester.pumpWidget(_host(DpLink.title(text: '제목 링크', onTap: () {})));

    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();

    final node = tester.getSemantics(find.bySemanticsLabel('제목 링크'));
    expect(node.hasFlag(SemanticsFlag.isFocused), isTrue);
  });
```

- [ ] **Step 14: 테스트를 돌려 red 를 확인한다**

Run: `cd packages/dp_design && flutter test test/content/dp_link_test.dart --plain-name "하이라이트 모드가 touch 여도"`

Expected: FAIL — `onShowFocusHighlight` 는 `FocusManager.highlightMode` 가 `traditional` 일 때만 불리므로 `_focused` 가 false 로 남는다.

- [ ] **Step 15: `onFocusChange` 로 바꾼다**

`packages/dp_design/lib/src/content/dp_link.dart` 의 `FocusableActionDetector` 에서:

```dart
        child: FocusableActionDetector(
          // `onShowFocusHighlight` 는 `FocusManager.highlightMode` 가
          // traditional 일 때만 불린다(터치·테스트 기본값에서는 조용하다).
          // 이 위젯의 `Semantics.focused` 는 자식 subtree 를
          // `excludeSemantics` 로 가린 뒤 **직접 선언하는 유일한 진실**이므로
          // 하이라이트 정책이 아니라 실제 포커스를 따라야 한다(리뷰 Minor 5).
          onFocusChange: (v) => setState(() => _focused = v),
```

- [ ] **Step 16: 테스트를 돌려 green 을 확인한다**

Run: `cd packages/dp_design && flutter test test/content/dp_link_test.dart`

Expected: 파일 전체 PASS. 포커스 링(`dp-link-focus-ring`)을 확인하는 기존 테스트가 `traditional` 을 가정하고 있었다면 이제 touch 에서도 링이 보인다 — 시안 `:focus-visible` 과는 어긋나지만, 링은 `_focused` 하나로 그려지므로 **시맨틱스 정확성을 택한다.** 이 절충을 위젯 doc 에 한 줄로 적는다.

- [ ] **Step 17: `DpPanel.title` 이 노드 둘일 때 라벨을 잃는지 테스트를 쓴다**

`packages/dp_design/test/layout/dp_panel_test.dart` 에 추가:

```dart
  testWidgets('DpPanel: 제목에 액션이 함께 있어도 heading 라벨이 남는다', (tester) async {
    await tester.pumpWidget(
      _host(
        DpPanel(
          title: Row(
            children: [
              const Expanded(child: Text('이번 주 과제')),
              TextButton(onPressed: () {}, child: const Text('전체 보기')),
            ],
          ),
          child: const Text('본문'),
        ),
      ),
    );

    final heading = tester.getSemantics(find.bySemanticsLabel('이번 주 과제'));
    expect(heading.hasFlag(SemanticsFlag.isHeader), isTrue);
  });
```

- [ ] **Step 18: 테스트를 돌려 red 를 확인한다**

Run: `cd packages/dp_design && flutter test test/layout/dp_panel_test.dart --plain-name "제목에 액션이 함께 있어도"`

Expected: FAIL — `Semantics` 는 기본 `container: false` 라 자식 노드가 둘 이상이면 병합되지 않고 **라벨 없는 header 컨테이너**가 생긴다(2026-09-17 함정 1 「heading+button 병합」과 같은 뿌리).

- [ ] **Step 19: `DpPanelTitle` 을 만들고 `DpPanel` 의 heading 래퍼를 없앤다**

`packages/dp_design/lib/src/layout/dp_panel.dart` 파일 끝에 추가:

```dart
/// 패널 제목 텍스트(시안 `.panel>h3`). heading 플래그를 **이 텍스트에만** 준다.
///
/// `DpPanel.title` 에 액션을 함께 넣을 때 제목행 전체를 `Semantics(header: true)`
/// 로 감싸면, 자식 노드가 둘 이상이라 병합되지 않고 라벨 없는 header 컨테이너가
/// 생긴다(P3 리뷰 Minor 6). 제목만 감싸면 그 함정이 닫힌다.
class DpPanelTitle extends StatelessWidget {
  const DpPanelTitle(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) =>
      Semantics(header: true, child: Text(text));
}
```

그리고 `DpPanel.build` 의 제목행에서 `Semantics(header: true, …)` 래퍼를 **없앤다**(남기면 이중이 된다):

```dart
              child: DefaultTextStyle.merge(
                style: text.titleSmall?.copyWith(color: c.textPrimary),
                child: title!,
              ),
```

앞으로의 표준은 `title: const DpPanelTitle('이번 주 과제')` 이고, 액션이 있으면 `title: Row(children: [const Expanded(child: DpPanelTitle('…')), …])` 다.

- [ ] **Step 20: 테스트를 고쳐 green 을 확인한다**

Step 17 의 테스트에서 `const Expanded(child: Text('이번 주 과제'))` 를 `const Expanded(child: DpPanelTitle('이번 주 과제'))` 로 바꾼다. 기존 테스트가 `title: const Text('…')` 로 `isHeader` 를 단언하고 있으면 `DpPanelTitle` 로 바꾼다.

Run: `cd packages/dp_design && flutter test test/layout/dp_panel_test.dart`

Expected: 파일 전체 PASS.

- [ ] **Step 21: 이름이 맞지 않는 테스트 1건을 고친다**

`packages/dp_design/test/data/dp_list_row_test.dart` 의 `'DpListRow: hover/focus 베이스(FocusableActionDetector) 존재'`(약 31~43행) 이름과 단언을 바꾼다. 그 `FocusableActionDetector` 는 이제 행이 아니라 `DpLink` 내부의 것이다(리뷰 Minor 9).

```dart
  testWidgets('DpListRow: 제목 링크가 hover/focus 베이스(FocusableActionDetector)를 갖는다', (
    tester,
  ) async {
```

본문의 `findsWidgets` 단언을 아래로 바꾼다:

```dart
    expect(
      find.descendant(
        of: find.byType(DpLink),
        matching: find.byType(FocusableActionDetector),
      ),
      findsOneWidget,
    );
```

Run: `cd packages/dp_design && flutter test test/data/dp_list_row_test.dart`

Expected: 파일 전체 PASS.

- [ ] **Step 22: `DpPageHeader` 가 좌우 패딩을 주지 않는 테스트를 쓴다**

`packages/dp_design/test/layout/dp_page_header_test.dart` 에 추가:

```dart
  testWidgets('DpPageHeader: 좌우 패딩을 주지 않는다 — 셸이 이미 준다', (tester) async {
    await tester.pumpWidget(_host(const DpPageHeader(title: '오늘')));

    final padding = tester.widget<Padding>(
      find.ancestor(of: find.text('오늘'), matching: find.byType(Padding)).last,
    );
    final resolved = padding.padding.resolve(TextDirection.ltr);
    expect(resolved.left, 0);
    expect(resolved.right, 0);
  });
```

- [ ] **Step 23: 테스트를 돌려 red 를 확인한다**

Run: `cd packages/dp_design && flutter test test/layout/dp_page_header_test.dart --plain-name "좌우 패딩을 주지 않는다"`

Expected: FAIL — 현재 `EdgeInsets.fromLTRB(compact ? DpSpacing.lg : DpSpacing.xl, …)` 로 좌우를 준다. 셸의 좌우 패딩과 합쳐져 시안(`.main` 의 24 한 겹)의 두 배가 된다.

- [ ] **Step 24: 좌우 패딩을 0 으로 내린다**

`packages/dp_design/lib/src/layout/dp_page_header.dart`:

```dart
    return Padding(
      // 시안 `.ph` 에는 패딩이 없다 — 좌우 여백은 `.main` 의 24 한 겹이고, 앱에서는
      // `DpWebShell`(web)·`DpAppShell`(admin)이 그 값을 준다. 여기서 또 주면 두 겹이다.
      padding: EdgeInsets.fromLTRB(
        0,
        compact ? DpSpacing.xl : DpSpacing.xxl,
        0,
        DpSpacing.lg,
      ),
```

- [ ] **Step 25: admin 회귀를 확인하고, 필요하면 admin 셸에서 고친다**

`DpPageHeader` 는 `apps/admin` 도 쓴다. admin 본문 좌우 패딩이 없으면 화면이 왼쪽 끝에 붙는다.

Run:

```bash
git grep -n "DpPageHeader" -- apps/admin/lib
cd apps/admin && flutter test
```

Expected: admin 156 PASS. 실패하거나 패딩이 없으면 **`DpAppShell` 의 본문에 좌우 패딩을 넣어** 고친다 — 화면마다 되살리지 않는다(셸이 준다는 규칙을 admin 에도 같게 한다). 그 변경은 이 Task 의 커밋에 포함한다.

- [ ] **Step 26: `DpCols` 실패 테스트를 쓴다**

`packages/dp_design/test/layout/dp_cols_test.dart` 를 만든다:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host(Widget child, {required Size size}) => MediaQuery(
  data: MediaQueryData(size: size),
  child: MaterialApp(theme: DpTheme.light(), home: Scaffold(body: child)),
);

void main() {
  testWidgets('DpCols: expanded 이상에서 2:1 두 열로 배치한다', (tester) async {
    await tester.pumpWidget(
      _host(
        const DpCols(
          main: SizedBox(key: ValueKey('cols-main'), height: 10),
          side: SizedBox(key: ValueKey('cols-side'), height: 10),
        ),
        size: const Size(1280, 800),
      ),
    );

    final mainW = tester.getSize(find.byKey(const ValueKey('cols-main'))).width;
    final sideW = tester.getSize(find.byKey(const ValueKey('cols-side'))).width;
    expect(mainW, closeTo(sideW * 2, 1));
  });

  testWidgets('DpCols: compact 에서 main 다음에 side 한 열로 접는다', (tester) async {
    await tester.pumpWidget(
      _host(
        const DpCols(
          main: SizedBox(key: ValueKey('cols-main'), height: 10),
          side: SizedBox(key: ValueKey('cols-side'), height: 10),
        ),
        size: const Size(390, 800),
      ),
    );

    final mainRect = tester.getRect(find.byKey(const ValueKey('cols-main')));
    final sideRect = tester.getRect(find.byKey(const ValueKey('cols-side')));
    expect(mainRect.width, sideRect.width);
    expect(sideRect.top, greaterThan(mainRect.bottom));
  });

  testWidgets('DpSide: 자식 사이에 lg 간격을 넣는다', (tester) async {
    await tester.pumpWidget(
      _host(
        const DpSide(
          children: [
            SizedBox(key: ValueKey('side-a'), height: 10),
            SizedBox(key: ValueKey('side-b'), height: 10),
          ],
        ),
        size: const Size(1280, 800),
      ),
    );

    final a = tester.getRect(find.byKey(const ValueKey('side-a')));
    final b = tester.getRect(find.byKey(const ValueKey('side-b')));
    expect(b.top - a.bottom, DpSpacing.lg);
  });
}
```

- [ ] **Step 27: 테스트를 돌려 red 를 확인한다**

Run: `cd packages/dp_design && flutter test test/layout/dp_cols_test.dart`

Expected: FAIL — `DpCols`·`DpSide` 가 없어 컴파일되지 않는다.

- [ ] **Step 28: `DpCols`·`DpSide` 를 만든다**

`packages/dp_design/lib/src/layout/dp_cols.dart`:

```dart
import 'package:flutter/material.dart';

import '../theme/dp_spacing.dart';
import 'dp_window_class.dart';

/// 본문 2열 배치(시안 `.cols`) — 주 내용 2fr, 사이드 1fr, 간격 24.
///
/// 좁은 폭에서는 `main` → `side` 순서로 한 열이 된다(시안
/// `@container (max-width:720px){.cols{grid-template-columns:minmax(0,1fr)}}`).
/// 경계를 `DpWindowClass.expanded`(1240) 에 두는 이유: 셸 본문은 최대 1120 이고
/// 사이드가 1fr 이므로 840~1239 에서 사이드가 약 270px 까지 눌린다. 그 폭에서는
/// 표가 이미 자체 가로 스크롤로 들어가 2열이 읽히지 않는다.
///
/// 폭·좌우 패딩은 셸(`DpWebShell`)이 준다 — 이 위젯은 그 안에서 나누기만 한다.
class DpCols extends StatelessWidget {
  const DpCols({super.key, required this.main, required this.side});

  final Widget main;
  final Widget side;

  @override
  Widget build(BuildContext context) {
    final twoColumn = switch (context.windowClass) {
      DpWindowClass.expanded || DpWindowClass.large => true,
      DpWindowClass.compact || DpWindowClass.medium => false,
    };

    if (!twoColumn) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [main, const SizedBox(height: DpSpacing.xl), side],
      );
    }

    return Row(
      // 시안 `align-items:start` — 사이드가 주 내용 높이만큼 늘어나지 않는다.
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(flex: 2, child: main),
        const SizedBox(width: DpSpacing.xl),
        Expanded(child: side),
      ],
    );
  }
}

/// 사이드 칼럼의 세로 스택(시안 `.side{display:flex;flex-direction:column;gap:16px}`).
class DpSide extends StatelessWidget {
  const DpSide({super.key, required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    mainAxisSize: MainAxisSize.min,
    children: [
      for (var i = 0; i < children.length; i++) ...[
        if (i > 0) const SizedBox(height: DpSpacing.lg),
        children[i],
      ],
    ],
  );
}
```

- [ ] **Step 29: barrel 에 추가하고 green 을 확인한다**

`packages/dp_design/lib/dp_design.dart` 에 `export 'src/layout/dp_cols.dart';` 를 `export 'src/layout/dp_max_width.dart';` **앞**(알파벳 순서)에 넣는다.

Run: `cd packages/dp_design && flutter test test/layout/dp_cols_test.dart`

Expected: PASS 3/3.

- [ ] **Step 30: dp_design 전체와 admin 을 돌린다**

Run: `cd packages/dp_design && flutter test` 이어서 `cd apps/admin && flutter test`

Expected: dp_design 350+ PASS · admin 156 PASS.

- [ ] **Step 31: 포맷하고 커밋한다**

```bash
dart format packages/dp_design/lib/src/layout/dp_cols.dart packages/dp_design/lib/src/layout/dp_panel.dart packages/dp_design/lib/src/layout/dp_page_header.dart packages/dp_design/lib/src/data/dp_web_table.dart packages/dp_design/lib/src/content/dp_link.dart packages/dp_design/test/layout/dp_cols_test.dart
git add packages/dp_design/lib/src/layout/dp_cols.dart packages/dp_design/lib/src/layout/dp_panel.dart packages/dp_design/lib/src/layout/dp_page_header.dart packages/dp_design/lib/src/data/dp_web_table.dart packages/dp_design/lib/src/content/dp_link.dart packages/dp_design/lib/dp_design.dart packages/dp_design/test/layout packages/dp_design/test/data packages/dp_design/test/content
git commit -F - <<'MSG'
feat(dp_design): P4 준비 — DpCols 신설, 이월 Minor 5건 수정, DpPageHeader 좌우 패딩 제거

- DpWebTable: numeric 유연 칼럼 우측 정렬, empty 필수화, 셀 개수 assert
- DpPanel: DpPanelTitle 신설 — 제목에 액션이 함께 있어도 heading 라벨 유지
- DpLink: focused 를 실제 포커스(onFocusChange)로 — 하이라이트 모드와 무관
- DpPageHeader: 좌우 패딩 0 — 셸이 이미 준다(시안 .ph 에는 패딩이 없다)
- DpCols/DpSide: 시안 .cols 2fr/1fr + .side 스택

리뷰 Minor 7(Wrap 정렬)·8(hover 대비)은 시안 CSS 와 같은 거동이라 기각.
4(리터럴 치수)·10(DESIGN.md)은 P5 이월.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
git diff origin/develop HEAD --name-only
```

Expected: 변경 파일 목록에 `analysis_options.yaml`·`pubspec.lock` 이 **없어야 한다.** 있으면 그 파일만 `git checkout origin/develop -- <경로>` 로 되돌리고 **즉시** `git commit --amend --no-edit` 한다(다른 명령을 끼우면 로컬 툴이 다시 쓴다).

---

## Task 2: 오늘 화면 — `.next` + `.cols` + 「이번 주 과제」 표 신설

**시안 `today`.** 앱의 Bento 4열 그리드를 `.cols` 2열로 바꾸고, 시안에만 있던 네 요소(「이번 주 과제」 표·「진행」 키-값·「왜 이 순서인가요」·「막히면」)를 **이미 내려오는 데이터로** 만든다. 차트·광고는 사이드 패널로 옮겨 **보존**한다.

**Files:**
- Modify: `apps/web/lib/src/features/dashboard/presentation/dashboard_page.dart`
- Modify: `apps/web/lib/src/features/dashboard/presentation/widgets/dashboard_body.dart`
- Create: `apps/web/lib/src/features/dashboard/presentation/widgets/today_panels.dart`
- Modify: `apps/web/lib/src/features/dashboard/presentation/widgets/weekly_activity_card.dart`
- Modify: `apps/web/lib/src/features/dashboard/presentation/widgets/progress_trend_card.dart`
- Test: `apps/web/test/features/dashboard/today_panels_test.dart` (신규)
- Test: 기존 `apps/web/test/features/dashboard/` 아래 전부 (경로는 Step 1 에서 확인)

**Interfaces:**
- Consumes: `DpCols`·`DpSide`·`DpPanelTitle`·`DpWebTable`(`empty` 필수) — Task 1.
- Produces:
  - `TodayTasksPanel({required CurrentMission mission, required ValueChanged<WeeklyTask> onOpenTask, Key? key})`
  - `TodayProgressPanel({required DashboardSummary summary, required CurrentMission? mission, Key? key})`
  - `TodayWhyPanel({required String why, required VoidCallback onOpenPath, Key? key})`
  - `TodayHelpPanel({required VoidCallback onOpenMentor, required VoidCallback onOpenQna, Key? key})`
  - `DashboardBody.supportingContent(BuildContext, DashboardSummary, {Key? key})` — 반환값이 Bento 그리드에서 **`DpSide` 스택**으로 바뀐다. 시그니처는 그대로.

### 판정 (Ruling) — 무엇을 보존하고 무엇을 합쳤는가

| 기존 요소 | 처리 | 근거 |
|---|---|---|
| `WeeklyActivityCard` 「주간 학습량」 | **보존** — 사이드 패널로 이동 | 기능 보존 규칙. 자체 `Container`+제목을 `DpPanel`+`DpPanelTitle` 로 교체하고 `Key('weekly-activity-card')` 를 `DpPanel` 로 옮긴다(테스트가 그 키를 쓴다). |
| `ProgressTrendCard` 「진행률 추이」 | **보존** — 사이드 패널로 이동 | 같음. `Key('progress-trend-card')` 유지. |
| `DpKpiCard` 「연속 학습」·「완료 콘텐츠」 | **표현 통합** — 「진행」 키-값의 행이 된다 | 데이터(`streakDays`·`completedContentCount`)는 **하나도 잃지 않는다.** 시안 `.kv` 가 같은 데이터를 같은 화면에서 더 조밀하게 전달하므로 카드 두 장을 따로 두면 같은 숫자가 두 번 나온다. |
| `_BadgeStrip` 배지 | **표현 통합** — 「진행」 키-값의 `배지` 행 | 같음. `summary.badges` 를 `DpTag` 로 그린다. |
| `_DonutCard` 진행 도넛 | **표현 통합** — 「진행」 키-값의 `전체 진행률` 행 | `progressPercent` 를 잃지 않는다. 도넛은 legacy(flag OFF) 경로에만 있었고 시안에 대응이 없다. |
| `_HeroCta` 「다음 과제」 | **보존(legacy 전용)** — `DpPanel` 로 감싼다 | flag OFF 경로에서만 쓰인다. flag ON 에서는 `TodayMissionSection` 의 `DpNextActionBand` 가 같은 역할이다. |
| `StaggeredGrid`(Bento) | **제거** | `.cols`+`.side` 가 대체한다. `flutter_staggered_grid_view` 의존은 **pubspec 에서 지우지 않는다**(다른 소비처 확인은 P5 정리 범위). |
| `_panel()` 의 `boxShadow` | **제거** | 장식이다. 시안의 면 구분은 1px 테두리 한 겹뿐이다. |
| `AdSlotWidget('DASHBOARD_TOP')` | **보존** — 위치 그대로(본문 맨 아래 sliver) | 사업 요소다. 시안에 대응이 없다는 이유로 지우지 않는다. |
| 시안 `.ex`(과제 설명 한 줄) | **구현하지 않음** | `WeeklyTask` 에 설명 필드가 없다(`taskId`·`orderNum`·`taskType`·`title`·`required`·`contentId`·`contentSlug`·`completed`·`completedAt`). 새 API 를 만들지 않는다는 규칙이 우선한다. |
| 시안 「전체 경로 · 12주 중 1주차」 | **낮춰서 구현** — `N주차` 만 | 오늘 화면은 `LearningPath` 를 읽지 않아 총 주차 수를 모른다. 총 주차를 알려면 새 호출이 필요하다. |
| 시안 유형 라벨 「퀴즈」 | **앱 라벨 유지** — `DpLearningLabels.taskType('QUIZ')` = 「확인」 | 라벨은 제품 문구의 SSoT 가 `DpLearningLabels` 다. 시안 문구를 따르려면 별도 문구 결정이 필요하다(P5 문서 단계로 이월). |

- [ ] **Step 1: 기존 대시보드 테스트의 위치와 개수를 확인한다**

Run:

```bash
git -C . ls-files apps/web/test | grep -i 'dashboard\|today'
cd apps/web && flutter test test/features/dashboard 2>&1 | tail -5
```

Expected: 현재 통과 개수를 기록한다. 이 Task 는 그 테스트들을 **깨뜨린다** — 무엇이 왜 깨지는지 알고 고치기 위해 먼저 녹색 기준선을 확인한다.

- [ ] **Step 2: 「이번 주 과제」 표 실패 테스트를 쓴다**

`apps/web/test/features/dashboard/today_panels_test.dart` 를 만든다:

```dart
import 'package:dp_core/dp_core.dart';
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:web/src/features/dashboard/presentation/widgets/today_panels.dart';

CurrentMission _mission() => CurrentMission.available(
  pathId: 1,
  weekNum: 1,
  tasks: const [
    WeeklyTask(
      taskId: 11,
      orderNum: 1,
      taskType: 'READ',
      title: 'Future/async-await 정리',
      completed: true,
    ),
    WeeklyTask(
      taskId: 12,
      orderNum: 2,
      taskType: 'PRACTICE',
      title: 'Stream 구독 실습',
      contentId: 5,
    ),
    WeeklyTask(
      taskId: 13,
      orderNum: 3,
      taskType: 'QUIZ',
      title: '에러 처리 패턴 적용',
    ),
  ],
);

Widget _host(Widget child, {Size size = const Size(1280, 900)}) => MediaQuery(
  data: MediaQueryData(size: size),
  child: MaterialApp(
    theme: DpTheme.light(),
    home: Scaffold(body: SingleChildScrollView(child: child)),
  ),
);

void main() {
  testWidgets('TodayTasksPanel: 과제 3개를 상태와 함께 표로 그린다', (tester) async {
    await tester.pumpWidget(
      _host(TodayTasksPanel(mission: _mission(), onOpenTask: (_) {})),
    );

    expect(find.text('이번 주 과제'), findsOneWidget);
    expect(find.text('Future/async-await 정리'), findsOneWidget);
    expect(find.text('Stream 구독 실습'), findsOneWidget);
    expect(find.text('에러 처리 패턴 적용'), findsOneWidget);
    expect(find.text('✓ 완료'), findsOneWidget);
    expect(find.text('● 다음'), findsOneWidget);
    expect(find.text('대기'), findsOneWidget);
  });

  testWidgets('TodayTasksPanel: 제목 링크를 누르면 그 과제를 넘긴다', (tester) async {
    WeeklyTask? opened;
    await tester.pumpWidget(
      _host(TodayTasksPanel(mission: _mission(), onOpenTask: (t) => opened = t)),
    );

    await tester.tap(find.text('Stream 구독 실습'));
    await tester.pump();

    expect(opened?.taskId, 12);
  });

  testWidgets('TodayTasksPanel: compact 에서 유형 칼럼을 감춘다', (tester) async {
    await tester.pumpWidget(
      _host(
        TodayTasksPanel(mission: _mission(), onOpenTask: (_) {}),
        size: const Size(390, 900),
      ),
    );

    expect(find.text('유형'), findsNothing);
    expect(find.text('과제'), findsOneWidget);
  });

  testWidgets('TodayTasksPanel: 과제가 없으면 빈 상태를 말한다', (tester) async {
    final empty = CurrentMission.available(
      pathId: 1,
      weekNum: 1,
      tasks: const [],
    );
    await tester.pumpWidget(
      _host(TodayTasksPanel(mission: empty, onOpenTask: (_) {})),
    );

    expect(find.text('이번 주 과제가 아직 없어요'), findsOneWidget);
  });
}
```

`CurrentMission.available(...)` 의 정확한 팩토리 이름과 인자는 `packages/dp_core/lib/src/models/current_mission.dart` 를 열어 맞춘다(비공개 생성자 `CurrentMission._` 이므로 팩토리가 따로 있다). 팩토리가 `fromJson` 뿐이면 테스트는 `CurrentMission.fromJson({...})` 로 만든다 — 그때 위 `_mission()` 을 그 형태로 바꾼다.

- [ ] **Step 3: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/dashboard/today_panels_test.dart`

Expected: FAIL — `today_panels.dart` 가 없다.

- [ ] **Step 4: `today_panels.dart` 를 만든다**

`apps/web/lib/src/features/dashboard/presentation/widgets/today_panels.dart`:

```dart
import 'package:dp_core/dp_core.dart';
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';

/// 시안 `today` 의 `.cols` 좌측 — 「이번 주 과제」 표.
///
/// 데이터는 `CurrentMission.tasks` 뿐이다(오늘 화면은 `LearningPath` 를 읽지
/// 않는다). 시안의 과제 설명(`.ex`)에 해당하는 필드가 `WeeklyTask` 에 없어
/// 그 줄은 그리지 않는다 — 새 API 를 만들지 않는다.
class TodayTasksPanel extends StatelessWidget {
  const TodayTasksPanel({
    super.key,
    required this.mission,
    required this.onOpenTask,
  });

  final CurrentMission mission;
  final ValueChanged<WeeklyTask> onOpenTask;

  @override
  Widget build(BuildContext context) {
    // 시안 `.hide-n` — 720 미만에서 감추는 칼럼. `DpWebTable` 은 칼럼 숨김을
    // 모르므로 칼럼 목록 자체에서 뺀다.
    final compact = context.windowClass == DpWindowClass.compact;
    final nextTaskId = mission.nextTask?.taskId;

    return DpPanel(
      title: const DpPanelTitle('이번 주 과제'),
      child: DpWebTable(
        columns: [
          const (label: '과제', width: null, numeric: false),
          if (!compact) const (label: '유형', width: 72, numeric: false),
          const (label: '상태', width: 72, numeric: false),
          const (label: '', width: 72, numeric: true),
        ],
        empty: const Padding(
          padding: EdgeInsets.symmetric(
            vertical: DpSpacing.xl,
            horizontal: DpSpacing.lg,
          ),
          child: Text('이번 주 과제가 아직 없어요'),
        ),
        rows: [
          for (final task in mission.tasks)
            (
              cells: [
                DpLink.title(
                  text: task.title,
                  onTap: () => onOpenTask(task),
                ),
                if (!compact) DpTag(label: DpLearningLabels.taskType(task.taskType)),
                _status(task, nextTaskId),
                DpLink.inline(
                  text: _actionLabel(task, nextTaskId),
                  onTap: () => onOpenTask(task),
                ),
              ],
              onTap: () => onOpenTask(task),
            ),
        ],
      ),
    );
  }

  /// 시안 `.st.ok/.now/.no` — 색만으로 의미를 전달하지 않도록 기호를 함께 넣는다.
  Widget _status(WeeklyTask task, int? nextTaskId) {
    if (task.completed) {
      return const DpStatusText(text: '✓ 완료', tone: DpStatusTone.done);
    }
    if (task.taskId != null && task.taskId == nextTaskId) {
      return const DpStatusText(text: '● 다음', tone: DpStatusTone.current);
    }
    return const DpStatusText(text: '대기', tone: DpStatusTone.idle);
  }

  String _actionLabel(WeeklyTask task, int? nextTaskId) {
    if (task.completed) return '다시 보기';
    if (task.taskId != null && task.taskId == nextTaskId) return '시작';
    return '열기';
  }
}

/// 시안 `today` 의 `.side` 첫 패널 — 「진행」 키-값.
///
/// 옛 KPI 카드 2장(`연속 학습`·`완료 콘텐츠`)·도넛(`전체 진행률`)·배지 스트립의
/// 데이터가 전부 이 표로 모인다. 같은 숫자를 한 화면에 두 번 그리지 않는다.
class TodayProgressPanel extends StatelessWidget {
  const TodayProgressPanel({
    super.key,
    required this.summary,
    required this.mission,
  });

  final DashboardSummary summary;
  final CurrentMission? mission;

  @override
  Widget build(BuildContext context) {
    final tasks = mission?.tasks ?? const <WeeklyTask>[];
    final done = tasks.where((task) => task.completed).length;
    final weekNum = mission?.weekNum;

    return DpPanel(
      title: const DpPanelTitle('진행'),
      child: DpKeyValues(
        entries: [
          if (tasks.isNotEmpty)
            (key: '이번 주', value: Text('$done / ${tasks.length}')),
          // 시안은 「12주 중 1주차」지만 총 주차 수는 이 화면에 내려오지 않는다
          // (`LearningPath` 를 읽지 않는다). 새 호출을 만들지 않고 낮춰 적는다.
          if (weekNum != null) (key: '현재 주차', value: Text('$weekNum주차')),
          (key: '전체 진행률', value: Text('${summary.progressPercent}%')),
          (key: '연속 학습', value: Text('${summary.streakDays}일')),
          (key: '완료 콘텐츠', value: Text('${summary.completedContentCount}개')),
          if (summary.badges.isNotEmpty)
            (
              key: '배지',
              value: Wrap(
                alignment: WrapAlignment.end,
                spacing: DpSpacing.xs,
                runSpacing: DpSpacing.xs,
                children: [for (final b in summary.badges) DpTag(label: b)],
              ),
            ),
        ],
      ),
    );
  }
}

/// 시안 `today` 의 「왜 이 순서인가요」 패널.
class TodayWhyPanel extends StatelessWidget {
  const TodayWhyPanel({
    super.key,
    required this.why,
    required this.onOpenPath,
  });

  /// `DpMissionHeader.why` 와 같은 문장을 받는다 — 두 곳이 갈라지지 않게.
  final String why;
  final VoidCallback onOpenPath;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    return DpPanel(
      title: const DpPanelTitle('왜 이 순서인가요'),
      padding: const EdgeInsets.symmetric(
        vertical: DpSpacing.md,
        horizontal: DpSpacing.lg,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            why,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: c.textSecondary),
          ),
          const SizedBox(height: DpSpacing.sm),
          DpLink.inline(text: '경로 전체 보기', onTap: onOpenPath),
        ],
      ),
    );
  }
}

/// 시안 `today` 의 「막히면」 패널 — 구분선 목록 안 링크 둘.
class TodayHelpPanel extends StatelessWidget {
  const TodayHelpPanel({
    super.key,
    required this.onOpenMentor,
    required this.onOpenQna,
  });

  final VoidCallback onOpenMentor;
  final VoidCallback onOpenQna;

  @override
  Widget build(BuildContext context) => DpPanel(
    title: const DpPanelTitle('막히면'),
    child: DpListLines(
      children: [
        DpLink.inline(text: 'AI 멘토에게 이 과제 물어보기', onTap: onOpenMentor),
        DpLink.inline(text: 'Q/A 에서 비슷한 질문 찾기', onTap: onOpenQna),
      ],
    ),
  );
}
```

- [ ] **Step 5: 테스트를 돌려 green 을 확인한다**

Run: `cd apps/web && flutter test test/features/dashboard/today_panels_test.dart`

Expected: PASS 4/4. `CurrentMission` 생성 방식이 틀렸으면 그 에러를 따라 `_mission()` 만 고친다.

- [ ] **Step 6: 200% 배율에서 사이드 패널이 깨지지 않는 테스트를 쓴다 (Review Focus 2)**

같은 테스트 파일에 추가:

```dart
  testWidgets('TodayProgressPanel: 280px 패널 + 200% 배율에서 오버플로가 없다', (
    tester,
  ) async {
    await tester.pumpWidget(
      MediaQuery(
        data: const MediaQueryData(
          size: Size(1280, 900),
          textScaler: TextScaler.linear(2),
        ),
        child: MaterialApp(
          theme: DpTheme.light(),
          home: Scaffold(
            body: SingleChildScrollView(
              child: SizedBox(
                width: 280,
                child: TodayProgressPanel(
                  summary: const DashboardSummary(
                    streakDays: 7,
                    progressPercent: 33,
                    completedContentCount: 2,
                    badges: ['첫 경로', '7일 연속'],
                  ),
                  mission: _mission(),
                ),
              ),
            ),
          ),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
  });
```

- [ ] **Step 7: 테스트를 돌려 green 을 확인한다**

Run: `cd apps/web && flutter test test/features/dashboard/today_panels_test.dart --plain-name "200% 배율"`

Expected: PASS — P3 이 `DpKeyValues` 의 키를 `Flexible` 로 고쳤으므로 통과해야 한다. 실패하면 `DpKeyValues` 쪽 회귀이므로 Task 1 로 돌아가 고친다(화면에서 우회하지 않는다).

- [ ] **Step 8: 커밋한다**

```bash
dart format apps/web/lib/src/features/dashboard/presentation/widgets/today_panels.dart apps/web/test/features/dashboard/today_panels_test.dart
git add apps/web/lib/src/features/dashboard/presentation/widgets/today_panels.dart apps/web/test/features/dashboard/today_panels_test.dart
git commit -F - <<'MSG'
feat(web): 오늘 화면의 시안 패널 4종 신설 — 이번 주 과제 표·진행 kv·왜 이 순서·막히면

시안에만 있던 네 요소를 이미 내려오는 데이터로 만든다(새 API 호출 없음).
KPI 카드 2장·도넛·배지 스트립의 데이터는 「진행」 키-값으로 모인다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
```

- [ ] **Step 9: 차트 두 장의 자체 컨테이너를 `DpPanel` 로 바꾼다**

`weekly_activity_card.dart` 의 `build` 를 아래로 바꾼다(키를 `DpPanel` 로 옮기고, 내부 제목·`Container`·`boxShadow` 없는 `BoxDecoration` 을 없앤다):

```dart
  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final text = Theme.of(context).textTheme;
    final hasData = activity.any((a) => a.completedCount > 0);
    return DpPanel(
      key: const Key('weekly-activity-card'),
      title: const DpPanelTitle('주간 학습량'),
      padding: const EdgeInsets.all(DpSpacing.lg),
      child: hasData
          ? SizedBox(height: 140, child: _chart(context))
          : Text(
              '아직 학습 기록이 없어요',
              style: text.bodyMedium?.copyWith(color: c.textSecondary),
            ),
    );
  }
```

`progress_trend_card.dart` 도 같은 모양으로 바꾼다 — `key: const Key('progress-trend-card')`, `title: const DpPanelTitle('진행률 추이')`, 범례(`DpChartLegend`)는 차트 아래 `Column` 에 그대로 둔다.

- [ ] **Step 10: 차트 테스트를 돌린다**

Run: `cd apps/web && flutter test test/features/dashboard`

Expected: 키(`weekly-activity-card`·`progress-trend-card`)를 찾는 테스트는 통과한다. 제목 텍스트를 `Container` 안에서 찾던 테스트가 있으면 `DpPanel` 구조에 맞게 고친다. `boxShadow` 를 단언하는 테스트가 있으면 **테스트를 지운다**(장식 제거는 이 Task 의 결정이다 — Ruling 표 참조).

- [ ] **Step 11: `DashboardBody.supportingContent` 를 `DpSide` 스택으로 바꾸는 실패 테스트를 쓴다**

`apps/web/test/features/dashboard/today_panels_test.dart` 에 추가:

```dart
  testWidgets('DashboardBody.supportingContent: Bento 대신 DpSide 스택을 그린다', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        Builder(
          builder: (context) => DashboardBody.supportingContent(
            context,
            const DashboardSummary(
              streakDays: 7,
              progressPercent: 33,
              completedContentCount: 2,
            ),
          ),
        ),
      ),
    );

    expect(find.byType(DpSide), findsOneWidget);
    expect(find.byType(DpKpiCard), findsNothing);
  });
```

`import 'package:web/src/features/dashboard/presentation/widgets/dashboard_body.dart';` 를 추가한다.

- [ ] **Step 12: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/dashboard/today_panels_test.dart --plain-name "Bento 대신 DpSide"`

Expected: FAIL — 현재는 `StaggeredGrid` + `DpKpiCard` 를 그린다.

- [ ] **Step 13: `dashboard_body.dart` 를 고친다**

`supportingContent` 는 **사이드 칼럼용 스택**을 돌려준다. `_content` 의 Bento 분기에서 `includeLegacyHero == false` 쪽을 아래로 교체한다.

```dart
  /// Today 의 `.side` 칼럼. 폭 판단은 `DpCols` 가 하므로 여기서 열 수를 세지 않는다.
  /// KPI·도넛·배지의 데이터는 `TodayProgressPanel` 이 키-값으로 그리므로 여기서는
  /// 차트만 남긴다(같은 숫자를 두 번 그리지 않는다).
  static Widget supportingContent(
    BuildContext context,
    DashboardSummary summary, {
    Key? key,
  }) => DpSide(
    key: key,
    children: [
      WeeklyActivityCard(activity: summary.weeklyActivity),
      ProgressTrendCard(history: summary.progressHistory),
    ],
  );
```

`_content`·`_trendMinWidth`·`_streakTile`·`_completedContentTile`·`_progressDonutTile`·`_weeklyActivityTile`·`_progressTrendTile`·`_DonutCard`·`_BadgeStrip` 중 **legacy 경로(`DashboardBody.content`)가 쓰는 것만 남기고** 나머지는 지운다. `_panel()` 은 `DpPanel` 로 바꾼다:

```dart
Widget _panel(BuildContext context, Widget child) => DpPanel(
  // 시안의 면 구분은 1px 테두리 한 겹뿐이다 — 그림자를 쓰지 않는다.
  padding: const EdgeInsets.all(DpSpacing.xl),
  child: child,
);
```

`content`(legacy, flag OFF) 는 Bento 를 유지하되 `_panel` 이 `DpPanel` 을 쓰게 되어 그림자만 사라진다. **legacy 경로를 `.cols` 로 옮기지 않는다** — flag OFF 는 운영 경로가 아니고, 바꾸면 그 경로의 테스트 전부를 다시 써야 한다.

- [ ] **Step 14: 테스트를 돌려 green 을 확인한다**

Run: `cd apps/web && flutter test test/features/dashboard`

Expected: PASS. `DpKpiCard`·도넛·배지를 Today 에서 찾던 테스트는 **「진행」 키-값에서 같은 숫자를 찾도록** 고친다(데이터가 사라진 게 아니라 옮겨졌다).

- [ ] **Step 15: `dashboard_page.dart` 를 `.next` + `.cols` 로 조립하는 실패 테스트를 쓴다**

기존 대시보드 페이지 테스트 파일(Step 1 에서 확인한 경로)에 추가한다:

```dart
  testWidgets('오늘: 미션 밴드 다음에 .cols 2열(과제 표 | 사이드)을 그린다', (tester) async {
    // 기존 파일의 provider override 헬퍼를 그대로 쓴다.
    await tester.pumpWidget(_app(size: const Size(1280, 900)));
    await tester.pumpAndSettle();

    expect(find.byType(DpCols), findsOneWidget);
    expect(find.text('이번 주 과제'), findsOneWidget);
    expect(find.text('진행'), findsOneWidget);
    expect(find.text('막히면'), findsOneWidget);
    // 광고 슬롯은 보존한다.
    expect(find.byKey(const ValueKey('today-ad-section')), findsOneWidget);
  });
```

- [ ] **Step 16: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/dashboard --plain-name ".cols 2열"`

Expected: FAIL — 현재는 `Row(flex 3/2)` 를 직접 만든다.

- [ ] **Step 17: `dashboard_page.dart` 의 flag ON 경로를 조립한다**

`build` 의 slivers 를 아래로 바꾼다. `wide`·`Row(flex 3/2)` 수동 분기를 **없애고** `DpCols` 에 맡긴다.

```dart
    final mission = missionState.mission;
    final summary = switch (s) {
      DashLoaded(:final summary) => summary,
      _ => null,
    };

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          const SliverToBoxAdapter(child: DpPageHeader(title: '오늘')),
          // 시안 `.next` — 다음 할 일 밴드. 상태 분기(로딩·실패·빈 경로)는 그대로
          // 이 위젯 안에 있다.
          SliverToBoxAdapter(
            key: const ValueKey('today-mission-section'),
            child: missionSection,
          ),
          if (showSupporting && mission != null)
            SliverToBoxAdapter(
              key: const ValueKey('today-cols'),
              child: Padding(
                padding: const EdgeInsets.only(bottom: DpSpacing.xl),
                child: DpCols(
                  main: TodayTasksPanel(
                    mission: mission,
                    onOpenTask: (task) {
                      final contentId = task.contentId;
                      if (contentId == null || task.taskId == null) {
                        context.go('/path');
                        return;
                      }
                      context.push(
                        MissionWorkspaceKey(
                          taskId: task.taskId!,
                          contentId: contentId,
                        ).contentLocation,
                      );
                    },
                  ),
                  side: DpSide(
                    children: [
                      if (summary != null)
                        TodayProgressPanel(summary: summary, mission: mission),
                      TodayWhyPanel(
                        why: '서버가 정한 이번 주의 첫 미완료 과제예요.',
                        onOpenPath: () => context.go('/path'),
                      ),
                      TodayHelpPanel(
                        onOpenMentor: () => context.go('/mentor'),
                        onOpenQna: () => context.go('/community?board=QNA'),
                      ),
                      // 지표 로딩·실패도 사이드에서 말한다(기존 분기를 잃지 않는다).
                      KeyedSubtree(key: supportingKey, child: supportingSection),
                    ],
                  ),
                ),
              ),
            ),
          if (showSupporting)
            const SliverToBoxAdapter(
              key: ValueKey('today-ad-section'),
              child: Padding(
                padding: EdgeInsets.only(bottom: DpSpacing.xl),
                child: AdSlotWidget(slot: 'DASHBOARD_TOP'),
              ),
            ),
        ],
      ),
    );
```

`import '../../mission/state/mission_workspace_key.dart';` 를 추가한다. 좌우 패딩(`EdgeInsets.fromLTRB(lg, 0, lg, xl)`)은 **없앤다** — 셸이 준다.

- [ ] **Step 18: 테스트를 돌려 green 을 확인하고 상태 분기를 지킨다 (Review Focus 5)**

Run: `cd apps/web && flutter test test/features/dashboard`

Expected: PASS. 아래 세 가지가 여전히 도달 가능한지 각각 테스트가 있는지 확인하고, 없으면 만든다:

```dart
  testWidgets('오늘: 지표 실패 시 사이드에서 다시 시도할 수 있다', (tester) async {
    await tester.pumpWidget(_app(dashboard: const DashFailed('네트워크')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('today-metrics-error')), findsOneWidget);
    expect(find.text('지표 다시 보기'), findsOneWidget);
  });
```

로딩(`today-metrics-loading`)·경로 없음(`CurrentMissionOutcome.noActivePath` → `DpEmpty`)도 같은 모양으로 확인한다.

- [ ] **Step 19: 390px 에서 가로로 넘치지 않는지 확인한다 (Review Focus 1)**

```dart
  testWidgets('오늘: 390px 에서 본문이 가로로 넘치지 않는다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(390, 900)));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    final cols = tester.getSize(find.byType(DpCols));
    expect(cols.width, lessThanOrEqualTo(390));
  });
```

Run: `cd apps/web && flutter test test/features/dashboard --plain-name "390px"`

Expected: PASS. 표가 `minWidth`(640) 보다 좁은 폭에서 자체 가로 스크롤로 들어가므로 본문은 넘치지 않는다.

- [ ] **Step 20: analyze·format 하고 커밋한다**

```bash
cd apps/web && flutter analyze lib/src/features/dashboard
cd ../.. && dart format apps/web/lib/src/features/dashboard/presentation/dashboard_page.dart apps/web/lib/src/features/dashboard/presentation/widgets/dashboard_body.dart apps/web/lib/src/features/dashboard/presentation/widgets/weekly_activity_card.dart apps/web/lib/src/features/dashboard/presentation/widgets/progress_trend_card.dart
git add apps/web/lib/src/features/dashboard apps/web/test/features/dashboard
git commit -F - <<'MSG'
feat(web): 오늘 화면을 시안 .next + .cols 로 재구성

- Bento StaggeredGrid → DpCols(과제 표 | 사이드 스택)
- 차트 두 장의 자체 컨테이너 → DpPanel(그림자 제거)
- KPI·도넛·배지 데이터는 「진행」 키-값으로 통합(데이터 손실 없음)
- 화면의 좌우 패딩 제거 — 셸이 준다
- 광고 슬롯·상태 분기(로딩·실패·경로 없음) 보존

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
git diff origin/develop HEAD --name-only
```

Expected: 목록에 `analysis_options.yaml`·`pubspec.lock` 이 없어야 한다.

- [ ] **Step 21: 기준선 영향을 기록한다**

`docs/superpowers/plans/2026-09-27-s3-p4-screen-groups/baseline-impact.md`(documents 레포)에 한 줄 추가한다. 이 파일은 P4 가 누적하고 P5 가 소비한다.

```markdown
- `/dashboard` 오늘 — Bento 그리드 → `.cols` 2열, KPI 카드·도넛·배지 스트립 사라짐(데이터는 「진행」 kv 로), 차트 패널 그림자 제거. ET13 visual baseline 재기록 대상.
```

---

## Task 3: 학습 경로 화면 — `.cols` + 「12주 계획」 표 신설

**시안 `path`·`ptoday`.** 앱의 수동 `Row(flex 3/2)` 를 `DpCols` 로 바꾸고, 시안에만 있던 「12주 계획」 표를 `plan.milestones` 로 만든다. 접힘 목록(`ExpansionTile`)이 담던 주차 정보는 그 표의 행이 되고, 근거·진단 요약은 사이드 패널이 된다.

**Files:**
- Modify: `apps/web/lib/src/features/path/presentation/path_page.dart`
- Modify: `apps/web/lib/src/features/path/presentation/mission_path_plan_view.dart`
- Modify: `apps/web/lib/src/features/path/presentation/path_plan_view.dart`
- Create: `apps/web/lib/src/features/path/presentation/path_panels.dart`
- Test: `apps/web/test/features/path/path_panels_test.dart` (신규)
- Test: 기존 `apps/web/test/features/path/` 전부

**Interfaces:**
- Consumes: `DpCols`·`DpSide`·`DpPanel`·`DpPanelTitle`·`DpWebTable`·`DpKeyValues`·`DpLink`·`DpStatusText` — Task 1.
- Produces:
  - `PathWeeksPanel({required LearningPath plan, required int? currentWeek, required ValueChanged<PathMilestone> onOpenWeek, Key? key})`
  - `PathDiagnosisPanel({required LearningPath plan, Key? key})`
  - `PathWeekOutcomePanel({required PathMilestone milestone, Key? key})`
  - `PathRationalePanel({required LearningPath plan, Key? key})`

### 판정 (Ruling)

| 기존 요소 | 처리 | 근거 |
|---|---|---|
| `DpMissionHeader` + `DpNextActionBand` | **보존** — `.cols` 좌측 맨 위 | 시안 `.ph` + 다음 행동. 그대로 둔다. |
| `DpProgressSpine`(주차 미션 순서) | **보존** — `.cols` 좌측 | 시안에 대응이 없지만 「이번 주 미션 순서」를 말하는 유일한 수단이다. |
| `_RoadmapDetails` 의 `ExpansionTile` 「완료한 주차」·「앞으로의 주차」 | **표현 교체** — 「12주 계획」 표의 행 | 같은 데이터(`weekNum`·`title`·`goalDescription`·진행)를 시안의 표가 접지 않고 한눈에 보여 준다. 접혀 있던 `goalDescription`·`expectedOutcome` 은 표의 「목표」 칼럼으로 올라오므로 **정보가 줄지 않는다.** |
| `ExpansionTile` 「경로 설계 근거와 진단 요약」 | **분리 보존** — 사이드의 `PathRationalePanel`(근거) + `PathDiagnosisPanel`(진단 요약 kv) | 시안 `.side` 의 「진단 요약」 kv 가 후자에 대응한다. 전자는 시안에 없지만 `plan.rationale` 은 지우지 않는다. |
| `_CurrentWeekDetail` 「이번 주 완료 근거」 | **보존** — `PathWeekOutcomePanel` (`DecoratedBox` → `DpPanel`) | 시안 `.side` 의 「1주차를 끝내면」에 대응한다. |
| `'다음 잠금 해제 · …'` 텍스트 | **보존** — `PathWeekOutcomePanel` 안의 한 줄 | 사이드로 옮긴다. |
| `_CompletedPath` 의 `ListTile` 완료 목록 | **표현 교체** — `DpListLines` | 시안 `.list` 문법. `completedAt` 문구를 유지한다. |
| `PathPlanView`(flag OFF) | **패널만 교체** | `BoxDecoration` 3곳 → `DpPanel`. 레이아웃은 그대로 둔다(운영 경로가 아니다). |
| `MilestoneProgressCard` 「주차별 진행률」 | **보존** — 소비처가 있으면 사이드 패널로, 없으면 건드리지 않는다 | Step 1 에서 `git grep MilestoneProgressCard` 로 실측한 뒤 결정하고, 결과를 이 표에 적는다. |

- [ ] **Step 1: 소비처와 기준선을 실측한다**

Run:

```bash
git grep -n "MilestoneProgressCard" -- apps/web
cd apps/web && flutter test test/features/path 2>&1 | tail -5
```

Expected: 통과 개수를 기록한다. `MilestoneProgressCard` 소비처가 0이면 Ruling 표의 마지막 줄을 「소비처 0 — 손대지 않는다(P5 정리 이월)」로 고쳐 적는다.

- [ ] **Step 2: 「12주 계획」 표 실패 테스트를 쓴다**

`apps/web/test/features/path/path_panels_test.dart`:

```dart
import 'package:dp_core/dp_core.dart';
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:web/src/features/path/presentation/path_panels.dart';

LearningPath _plan() => const LearningPath(
  pathId: 1,
  rationale: '진단에서 비동기 흐름과 테스트 보강이 먼저 필요하다고 나왔어요.',
  milestones: [
    PathMilestone(
      weekNum: 1,
      title: '비동기 기초',
      goalDescription: 'Future와 Stream의 차이를 이해하고 작은 기능에 적용합니다.',
      estimatedHours: 6,
      whyThisOrder: '비동기가 나머지 주차의 전제다.',
      expectedOutcome: '비동기 API 호출과 Stream 구독을 안정적으로 다룰 수 있어요.',
      tasks: [
        WeeklyTask(
          taskId: 11,
          orderNum: 1,
          taskType: 'READ',
          title: '읽기 과제',
          completed: true,
        ),
        WeeklyTask(taskId: 12, orderNum: 2, taskType: 'PRACTICE', title: '실습 과제'),
        WeeklyTask(taskId: 13, orderNum: 3, taskType: 'QUIZ', title: '확인 과제'),
      ],
    ),
    PathMilestone(
      weekNum: 2,
      title: '주차 2 학습',
      goalDescription: '다음 단계 역량을 차근차근 확장합니다.',
      estimatedHours: 6,
      whyThisOrder: '1주차 위에 쌓는다.',
      expectedOutcome: '확장된 역량',
    ),
  ],
);

Widget _host(Widget child, {Size size = const Size(1280, 900)}) => MediaQuery(
  data: MediaQueryData(size: size),
  child: MaterialApp(
    theme: DpTheme.light(),
    home: Scaffold(body: SingleChildScrollView(child: child)),
  ),
);

void main() {
  testWidgets('PathWeeksPanel: 주차를 표로 그리고 현재 주차를 표시한다', (tester) async {
    await tester.pumpWidget(
      _host(
        PathWeeksPanel(plan: _plan(), currentWeek: 1, onOpenWeek: (_) {}),
      ),
    );

    expect(find.text('12주 계획'), findsOneWidget);
    expect(find.text('비동기 기초'), findsOneWidget);
    expect(find.text('주차 2 학습'), findsOneWidget);
    expect(find.text('● 진행 중'), findsOneWidget);
    // 「목표」 칼럼이 접혀 있던 goalDescription 을 올려 보여 준다.
    expect(
      find.text('Future와 Stream의 차이를 이해하고 작은 기능에 적용합니다.'),
      findsOneWidget,
    );
    // 진행 칼럼: 1주차는 3개 중 1개 완료.
    expect(find.text('1 / 3'), findsOneWidget);
  });

  testWidgets('PathWeeksPanel: 주차 제목을 누르면 그 주차를 넘긴다', (tester) async {
    PathMilestone? opened;
    await tester.pumpWidget(
      _host(
        PathWeeksPanel(
          plan: _plan(),
          currentWeek: 1,
          onOpenWeek: (m) => opened = m,
        ),
      ),
    );

    await tester.tap(find.text('주차 2 학습'));
    await tester.pump();

    expect(opened?.weekNum, 2);
  });

  testWidgets('PathWeeksPanel: compact 에서 목표 칼럼을 감춘다', (tester) async {
    await tester.pumpWidget(
      _host(
        PathWeeksPanel(plan: _plan(), currentWeek: 1, onOpenWeek: (_) {}),
        size: const Size(390, 900),
      ),
    );

    expect(find.text('목표'), findsNothing);
    expect(find.text('주제'), findsOneWidget);
  });

  testWidgets('PathDiagnosisPanel: 진단 요약을 키-값으로 그린다', (tester) async {
    await tester.pumpWidget(_host(PathDiagnosisPanel(plan: _plan())));

    expect(find.text('진단 요약'), findsOneWidget);
  });
}
```

`LearningPath`·`PathMilestone` 의 필수 인자는 `packages/dp_core/lib/src/models/learning_path.dart` 를 열어 정확히 맞춘다(`diagnosis` 는 nullable 이므로 생략 가능한지 확인한다).

- [ ] **Step 3: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/path/path_panels_test.dart`

Expected: FAIL — `path_panels.dart` 가 없다.

- [ ] **Step 4: `path_panels.dart` 를 만든다**

```dart
import 'package:dp_core/dp_core.dart';
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';

/// 시안 `path` 의 `.cols` 좌측 — 「12주 계획」 표.
///
/// 옛 `ExpansionTile` 목록(「완료한 주차」·「앞으로의 주차」)을 대체한다. 접혀
/// 있던 `goalDescription` 이 「목표」 칼럼으로 올라오므로 정보가 줄지 않는다.
class PathWeeksPanel extends StatelessWidget {
  const PathWeeksPanel({
    super.key,
    required this.plan,
    required this.currentWeek,
    required this.onOpenWeek,
  });

  final LearningPath plan;
  final int? currentWeek;
  final ValueChanged<PathMilestone> onOpenWeek;

  @override
  Widget build(BuildContext context) {
    final compact = context.windowClass == DpWindowClass.compact;
    final total = plan.milestones.length;

    return DpPanel(
      title: DpPanelTitle('$total주 계획'),
      child: DpWebTable(
        columns: [
          const (label: '주차', width: 56, numeric: true),
          const (label: '주제', width: null, numeric: false),
          if (!compact) const (label: '목표', width: null, numeric: false),
          const (label: '진행', width: 88, numeric: false),
        ],
        empty: const Padding(
          padding: EdgeInsets.symmetric(
            vertical: DpSpacing.xl,
            horizontal: DpSpacing.lg,
          ),
          child: Text('아직 주차 계획이 없어요'),
        ),
        rows: [
          for (final milestone in plan.milestones)
            (
              cells: [
                Text('${milestone.weekNum}'),
                _topic(milestone),
                if (!compact)
                  Text(
                    milestone.goalDescription,
                    style: TextStyle(color: context.dpColors.textSecondary),
                  ),
                _progress(context, milestone),
              ],
              onTap: () => onOpenWeek(milestone),
            ),
        ],
      ),
    );
  }

  Widget _topic(PathMilestone milestone) {
    final isCurrent = milestone.weekNum == currentWeek;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        DpLink.title(text: milestone.title, onTap: () => onOpenWeek(milestone)),
        if (isCurrent) ...[
          const SizedBox(height: DpSpacing.xs),
          const DpStatusText(text: '● 진행 중', tone: DpStatusTone.current),
        ],
      ],
    );
  }

  Widget _progress(BuildContext context, PathMilestone milestone) {
    final tasks = milestone.tasks;
    if (tasks.isEmpty) {
      return const DpStatusText(text: '대기', tone: DpStatusTone.idle);
    }
    final done = tasks.where((task) => task.completed).length;
    return Text('$done / ${tasks.length}');
  }
}

/// 시안 `path` 의 `.side` 「진단 요약」 — 강점·보강·트랙.
class PathDiagnosisPanel extends StatelessWidget {
  const PathDiagnosisPanel({super.key, required this.plan});

  final LearningPath plan;

  @override
  Widget build(BuildContext context) {
    final diagnosis = plan.diagnosis;
    return DpPanel(
      title: const DpPanelTitle('진단 요약'),
      child: DpKeyValues(
        entries: [
          if (diagnosis != null)
            (key: '현재 수준', value: Text('${diagnosis.diagnosedLevel}')),
          (key: '주차 수', value: Text('${plan.milestones.length}주')),
        ],
      ),
    );
  }
}

/// 시안 `path` 의 `.side` 「1주차를 끝내면」 — 이번 주 완료 근거 + 다음 잠금 해제.
class PathWeekOutcomePanel extends StatelessWidget {
  const PathWeekOutcomePanel({
    super.key,
    required this.milestone,
    required this.nextUnlock,
  });

  final PathMilestone milestone;

  /// 다음에 열리는 것. 문장을 계산하는 책임은 호출부(`mission_path_plan_view`)에 둔다.
  final String nextUnlock;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final text = Theme.of(context).textTheme;
    return DpPanel(
      title: DpPanelTitle('${milestone.weekNum}주차를 끝내면'),
      padding: const EdgeInsets.symmetric(
        vertical: DpSpacing.md,
        horizontal: DpSpacing.lg,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(milestone.expectedOutcome, style: text.bodyMedium),
          const SizedBox(height: DpSpacing.sm),
          Text(
            '다음 잠금 해제 · $nextUnlock',
            style: text.bodySmall?.copyWith(color: c.textSecondary),
          ),
        ],
      ),
    );
  }
}

/// 옛 `ExpansionTile` 「경로 설계 근거」. 시안에는 없지만 `plan.rationale` 을
/// 잃지 않기 위해 사이드 패널로 남긴다(기능 보존 규칙).
class PathRationalePanel extends StatelessWidget {
  const PathRationalePanel({super.key, required this.plan});

  final LearningPath plan;

  @override
  Widget build(BuildContext context) => DpPanel(
    title: const DpPanelTitle('경로 설계 근거'),
    padding: const EdgeInsets.symmetric(
      vertical: DpSpacing.md,
      horizontal: DpSpacing.lg,
    ),
    child: Text(
      plan.rationale,
      style: Theme.of(
        context,
      ).textTheme.bodyMedium?.copyWith(color: context.dpColors.textSecondary),
    ),
  );
}
```

- [ ] **Step 5: 테스트를 돌려 green 을 확인한다**

Run: `cd apps/web && flutter test test/features/path/path_panels_test.dart`

Expected: PASS 4/4. `PathDiagnosisPanel` 테스트가 「진단 요약」 문구만 보므로 `diagnosis` 가 null 이어도 통과한다.

- [ ] **Step 6: `mission_path_plan_view.dart` 를 `DpCols` 로 재조립하는 실패 테스트를 쓴다**

기존 `apps/web/test/features/path/` 의 테스트 파일에 추가한다:

```dart
  testWidgets('학습 경로: .cols 2열(미션+표 | 사이드)을 그린다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(1280, 900)));
    await tester.pumpAndSettle();

    expect(find.byType(DpCols), findsOneWidget);
    expect(find.byType(ExpansionTile), findsNothing);
    expect(find.text('진단 요약'), findsOneWidget);
    expect(find.text('경로 설계 근거'), findsOneWidget);
  });
```

- [ ] **Step 7: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/path --plain-name ".cols 2열"`

Expected: FAIL — 현재는 `Row(flex 3/2)` + `ExpansionTile` 이다.

- [ ] **Step 8: `_AvailablePath` 의 `primary`·`supporting` 을 다시 짠다**

`mission_path_plan_view.dart` 의 `_AvailablePath.build` 에서:

```dart
    final primary = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        DpMissionHeader(/* 기존 인자 그대로 */),
        if (!detailMatches && plan != null) ...[
          const SizedBox(height: DpSpacing.sm),
          const DpInlineNotice(
            message: '현재 미션과 경로 상세가 아직 맞지 않아요.',
            tone: DpInlineNoticeTone.warning,
          ),
        ],
        if (missionState.failureMessage != null) ...[
          const SizedBox(height: DpSpacing.sm),
          DpInlineNotice(/* 기존 인자 그대로 */),
        ],
        const SizedBox(height: DpSpacing.lg),
        DpProgressSpine(/* 기존 인자 그대로 */),
        if (matchingPlan != null) ...[
          const SizedBox(height: DpSpacing.xl),
          PathWeeksPanel(
            plan: matchingPlan,
            currentWeek: mission.weekNum,
            onOpenWeek: (_) {},
          ),
        ] else if (isPlanLoading || planFailureMessage != null) ...[
          const SizedBox(height: DpSpacing.xl),
          _PlanEnrichmentStatus(
            isLoading: isPlanLoading,
            failureMessage: planFailureMessage,
            onRetry: onRetryPlan,
          ),
        ],
      ],
    );

    final supporting = DpSide(
      children: [
        if (currentMilestone != null)
          PathWeekOutcomePanel(
            milestone: currentMilestone,
            nextUnlock: nextUnlock,
          ),
        if (matchingPlan != null) PathDiagnosisPanel(plan: matchingPlan),
        if (matchingPlan != null) PathRationalePanel(plan: matchingPlan),
      ],
    );

    // 폭 분기는 `DpCols` 가 한다 — 화면에서 `wide` 를 다시 계산하지 않는다.
    // 좌우 패딩도 주지 않는다(셸이 준다).
    return DpCols(main: primary, side: supporting);
```

`onOpenWeek` 는 지금 갈 곳이 없다(주차 상세 라우트가 없다) — **빈 콜백으로 두지 않고** 표의 제목을 링크가 아닌 텍스트로 두는 편이 정직하다. `PathWeeksPanel` 에 `onOpenWeek` 를 nullable 로 바꾸고, null 이면 `Text` 를 그리게 한다:

```dart
  final ValueChanged<PathMilestone>? onOpenWeek;
```

```dart
        final onOpen = onOpenWeek;
        …
        onOpen == null
            ? Text(milestone.title, style: const TextStyle(fontWeight: FontWeight.w600))
            : DpLink.title(text: milestone.title, onTap: () => onOpen(milestone)),
```

`rows` 의 `onTap` 도 `onOpen == null ? null : () => onOpen(milestone)` 로 바꾼다. Step 2 의 두 번째 테스트는 `onOpenWeek` 를 넘기므로 그대로 통과한다. **호출부(`mission_path_plan_view`)는 `onOpenWeek` 를 넘기지 않는다.**

`wide`·`Padding(EdgeInsets.all(DpSpacing.lg))`·`_RoadmapDetails`·`_MilestoneDisclosure`·`_CurrentWeekDetail` 를 **지운다**.

- [ ] **Step 9: `_CompletedPath` 의 완료 목록을 `DpListLines` 로 바꾼다**

```dart
        DpPanel(
          title: const DpPanelTitle('완료한 미션'),
          child: DpListLines(
            children: [
              for (final task in mission.tasks)
                Row(
                  children: [
                    Icon(DpIcons.stepDone, color: context.dpColors.success),
                    const SizedBox(width: DpSpacing.sm),
                    Expanded(child: Text(task.title)),
                    Text(
                      '완료 · ${task.completedAt!.toLocal()}',
                      style: TextStyle(color: context.dpColors.textSecondary),
                    ),
                  ],
                ),
            ],
          ),
        ),
```

`_RoadmapDetails` 를 쓰던 자리는 `PathWeeksPanel(plan: plan!, currentWeek: mission.weekNum, onOpenWeek: null)` 로 바꾼다.

- [ ] **Step 10: `path_page.dart` 의 좌우 패딩을 없앤다**

`legacyBodySliver` 의 `SliverPadding(padding: const EdgeInsets.all(DpSpacing.lg), …)` 에서 좌우를 뺀다:

```dart
      PathPhase.complete when s.result != null => SliverPadding(
        padding: const EdgeInsets.symmetric(vertical: DpSpacing.lg),
        sliver: SliverList.list(
          children: PathPlanView.children(context, s.result!),
        ),
      ),
```

- [ ] **Step 11: `path_plan_view.dart` 의 `BoxDecoration` 3곳을 `DpPanel` 로 바꾼다**

`PathPlanView.children` 안에서 `Container(decoration: BoxDecoration(color: c.surface, border: …, borderRadius: …))` 로 감싼 블록 셋을 각각 `DpPanel(title: DpPanelTitle('…'), padding: const EdgeInsets.all(DpSpacing.lg), child: …)` 로 바꾼다. 제목 문구는 지금 `Text('진단 요약', style: text.titleMedium)` 등으로 블록 안에 있으므로, 그 `Text` 를 지우고 패널 제목으로 올린다. `_Tag` 의 `BoxDecoration` 은 태그 칩이므로 `DpTag(label: …)` 로 바꾼다.

- [ ] **Step 12: 경로 테스트 전체를 돌린다 (Review Focus 1·5)**

Run: `cd apps/web && flutter test test/features/path`

Expected: PASS. 아래 셋이 살아 있는지 확인하고 없으면 만든다:

```dart
  testWidgets('학습 경로: 390px 에서 가로로 넘치지 않는다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(390, 900)));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(tester.getSize(find.byType(DpCols)).width, lessThanOrEqualTo(390));
  });

  testWidgets('학습 경로: 경로가 없으면 빈 상태에서 다시 확인할 수 있다', (tester) async {
    // CurrentMissionOutcome.noActivePath
    await tester.pumpWidget(_app(outcome: CurrentMissionOutcome.noActivePath));
    await tester.pumpAndSettle();
    expect(find.text('현재 경로 다시 확인'), findsOneWidget);
  });

  testWidgets('학습 경로: SSE 진행 중에는 단계 표시를 남긴다', (tester) async {
    await tester.pumpWidget(_app(phase: PathPhase.streaming));
    await tester.pumpAndSettle();
    expect(find.byType(DpSseStageView), findsOneWidget);
  });
```

- [ ] **Step 13: analyze·format 하고 커밋한다**

```bash
cd apps/web && flutter analyze lib/src/features/path
cd ../.. && dart format apps/web/lib/src/features/path/presentation/path_panels.dart apps/web/lib/src/features/path/presentation/mission_path_plan_view.dart apps/web/lib/src/features/path/presentation/path_page.dart apps/web/lib/src/features/path/presentation/path_plan_view.dart
git add apps/web/lib/src/features/path apps/web/test/features/path
git commit -F - <<'MSG'
feat(web): 학습 경로 화면을 시안 .cols + 12주 계획 표로 재구성

- ExpansionTile 「완료한 주차」·「앞으로의 주차」 → PathWeeksPanel 표
  (접혀 있던 goalDescription 이 「목표」 칼럼으로 올라온다)
- 근거·진단 요약·이번 주 완료 근거 → 사이드 패널 3개
- Row(flex 3/2) 수동 분기 제거 — DpCols 가 폭을 판단한다
- legacy PathPlanView 의 BoxDecoration 3곳 → DpPanel

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
git diff origin/develop HEAD --name-only
```

- [ ] **Step 14: 기준선 영향을 기록한다**

`baseline-impact.md` 에 추가:

```markdown
- `/path` 학습 경로 — 접힘 목록 → 표, 사이드 패널 3개 신설, 2열 분기 기준이 `DpCols`(expanded 1240)로 통일. ET13 visual baseline 재기록 대상.
```

---

## Task 4: 콘텐츠 읽기 화면 — `.cols` + `.prose` 760 + 진행률 보정 유지

**시안 `content`.** 본문을 `.prose`(760)로 좁히고 사이드에 「콘텐츠 학습 진행률」·「현재 학습 미션」 패널을 둔다. **`_scrollPct` 의 헤더 높이 보정이 이 Task 의 유일한 위험이다** — 헤더가 들어가는 박스를 바꾸면 서버로 보내는 진행률이 어긋난다.

**Files:**
- Modify: `apps/web/lib/src/features/content/presentation/content_page.dart`
- Create: `apps/web/lib/src/features/content/presentation/content_panels.dart`
- Test: `apps/web/test/features/content/` 아래 기존 테스트 전부 (`content_progress_smoke_test.dart`·`content_sandbox_smoke_test.dart` 포함)
- Test: `apps/web/test/features/content/content_panels_test.dart` (신규)

**Interfaces:**
- Consumes: `DpCols`·`DpSide`·`DpPanel`·`DpPanelTitle`·`DpListLines`·`DpLink`·`DpStatusText` — Task 1.
- Produces:
  - `ContentProgressPanel({required LearningContent content, Key? key})`
  - `ContentMissionPanel({required CurrentMission? mission, required int? currentTaskId, required ValueChanged<WeeklyTask> onOpenTask, Key? key})`
  - `WebContentProjection` 시그니처는 그대로. 내부 `maxWidth` 가 `840` → `context.appTokens.readableMaxWidth`(760)로 바뀐다.

### 판정 (Ruling)

| 기존 요소 | 처리 | 근거 |
|---|---|---|
| `WebContentProjection` 의 `ConstrainedBox(maxWidth: 840)` | **토큰으로 교체** — `readableMaxWidth`(760) | 시안 `.prose{max-width:760px}`. 840 은 리터럴이고 토큰과 어긋난다. |
| 본문 위 `LinearProgressIndicator` + `'$percent% 진행'` | **사이드로 이동** — `ContentProgressPanel` | 시안은 진행률을 `.side` 패널에 둔다. 위젯·데이터는 그대로다. |
| `Chip(label: Text(tag))` 개념 태그 | **`DpTag` 로 교체** | Material `Chip` 은 P2 에서 폰트 폭주의 원인이었다. `DpTag` 가 시안 `.tag` 다. |
| `AdSlotWidget('CONTENT_PAGE')` | **보존** — 본문 맨 아래 | 사업 요소. |
| `_MissionContentHeader`(`DpMissionHeader`) | **보존** — `_headerKey` 가 감싸는 박스를 **바꾸지 않는다** | `_scrollPct` 가 이 박스 높이를 잰다. 패널로 감싸면 높이가 바뀌어 진행률이 어긋난다. |
| `DpNextActionBand` 「실습 시작」 | **보존** — 본문 아래 | 시안 `.acts` 의 「실습 시작」에 대응. |
| 시안 「현재 학습 미션」 목록 | **신설** — `ContentMissionPanel` | `currentMissionState.mission.tasks` 로 만든다(이미 이 화면이 watch 한다). |

- [ ] **Step 1: 진행률 회귀 테스트가 지금 녹색인지 확인한다**

Run:

```bash
cd apps/web && flutter test test/features/content test/content_progress_smoke_test.dart 2>&1 | tail -5
git grep -n "_scrollPct\|headerHeight\|_headerKey" -- apps/web/test
```

Expected: 통과 개수와 **진행률 보정을 단언하는 테스트 파일명**을 기록한다. 그 테스트가 이 Task 의 안전망이다.

- [ ] **Step 2: 사이드 패널 실패 테스트를 쓴다**

`apps/web/test/features/content/content_panels_test.dart`:

```dart
import 'package:dp_core/dp_core.dart';
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:web/src/features/content/presentation/content_panels.dart';

Widget _host(Widget child) => MediaQuery(
  data: const MediaQueryData(size: Size(1280, 900)),
  child: MaterialApp(
    theme: DpTheme.light(),
    home: Scaffold(body: SingleChildScrollView(child: child)),
  ),
);

void main() {
  testWidgets('ContentProgressPanel: 진행률과 완료 기준을 말한다', (tester) async {
    await tester.pumpWidget(
      _host(
        ContentProgressPanel(
          content: LearningContent.fromJson(const {
            'id': 5,
            'slug': 'async-basics',
            'title': '비동기 기초',
            'markdown': '본문',
            'progress': {'scrollPct': 0.8, 'dwellSec': 60, 'completed': false},
          }),
        ),
      ),
    );

    expect(find.text('콘텐츠 학습 진행률'), findsOneWidget);
    expect(find.textContaining('80%'), findsOneWidget);
  });
}
```

`LearningContent.fromJson` 의 필수 키는 `packages/dp_core/lib/src/models/learning_content.dart` 를 보고 맞춘다.

- [ ] **Step 3: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/content/content_panels_test.dart`

Expected: FAIL — `content_panels.dart` 가 없다.

- [ ] **Step 4: `content_panels.dart` 를 만든다**

```dart
import 'package:dp_core/dp_core.dart';
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';

/// 시안 `content` 의 `.side` 「콘텐츠 학습 진행률」.
///
/// 본문 위에 있던 `LinearProgressIndicator` 와 같은 데이터다 — 위치만 옮긴다.
class ContentProgressPanel extends StatelessWidget {
  const ContentProgressPanel({super.key, required this.content});

  final LearningContent content;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final progress = content.progress;
    final percent = (progress.scrollPct * 100).round().clamp(0, 100);

    return DpPanel(
      title: const DpPanelTitle('콘텐츠 학습 진행률'),
      padding: const EdgeInsets.symmetric(
        vertical: DpSpacing.md,
        horizontal: DpSpacing.lg,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          LinearProgressIndicator(
            value: progress.scrollPct.clamp(0, 1).toDouble(),
          ),
          const SizedBox(height: DpSpacing.sm),
          Text(
            progress.completed
                ? '완료 · 끝까지 읽어 완료로 저장됐어요'
                : '$percent% · 끝까지 읽으면 완료로 저장됩니다',
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: c.textSecondary),
          ),
        ],
      ),
    );
  }
}

/// 시안 `content` 의 `.side` 「현재 학습 미션」 — 이번 주 과제 셋과 현재 위치.
class ContentMissionPanel extends StatelessWidget {
  const ContentMissionPanel({
    super.key,
    required this.mission,
    required this.currentTaskId,
    required this.onOpenTask,
  });

  final CurrentMission? mission;
  final int? currentTaskId;
  final ValueChanged<WeeklyTask> onOpenTask;

  @override
  Widget build(BuildContext context) {
    final tasks = mission?.tasks ?? const <WeeklyTask>[];
    if (tasks.isEmpty) return const SizedBox.shrink();

    return DpPanel(
      title: const DpPanelTitle('현재 학습 미션'),
      child: DpListLines(
        children: [
          for (final task in tasks)
            Row(
              children: [
                _mark(task),
                const SizedBox(width: DpSpacing.sm),
                Expanded(
                  child: task.taskId == currentTaskId || task.completed
                      ? Text(task.title)
                      : DpLink.inline(
                          text: task.title,
                          onTap: () => onOpenTask(task),
                        ),
                ),
              ],
            ),
        ],
      ),
    );
  }

  Widget _mark(WeeklyTask task) {
    if (task.completed) {
      return const DpStatusText(text: '✓', tone: DpStatusTone.done);
    }
    if (task.taskId == currentTaskId) {
      return const DpStatusText(text: '●', tone: DpStatusTone.current);
    }
    return const DpStatusText(text: '·', tone: DpStatusTone.idle);
  }
}
```

- [ ] **Step 5: 테스트를 돌려 green 을 확인한다**

Run: `cd apps/web && flutter test test/features/content/content_panels_test.dart`

Expected: PASS.

- [ ] **Step 6: `WebContentProjection` 의 폭·태그·진행률을 고치는 테스트를 쓴다**

```dart
  testWidgets('WebContentProjection: 본문 폭이 readableMaxWidth(760) 다', (tester) async {
    await tester.pumpWidget(/* 기존 테스트의 호스트로 WebContentProjection 을 띄운다 */);

    final box = tester.widget<ConstrainedBox>(
      find
          .ancestor(
            of: find.byType(DpMarkdown),
            matching: find.byType(ConstrainedBox),
          )
          .first,
    );
    expect(box.constraints.maxWidth, 760);
  });

  testWidgets('WebContentProjection: 개념 태그를 DpTag 로 그린다', (tester) async {
    await tester.pumpWidget(/* conceptTags 가 있는 콘텐츠 */);
    expect(find.byType(DpTag), findsWidgets);
    expect(find.byType(Chip), findsNothing);
  });
```

- [ ] **Step 7: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/content --plain-name "readableMaxWidth"`

Expected: FAIL — 현재 840 이고 `Chip` 을 쓴다.

- [ ] **Step 8: `WebContentProjection` 을 고친다**

`content_page.dart` 의 `WebContentProjection.build`:

```dart
    return Center(
      child: ConstrainedBox(
        // 시안 `.prose{max-width:760px}` = `readableMaxWidth`. 840 은 토큰과
        // 어긋난 리터럴이었다.
        constraints: BoxConstraints(maxWidth: context.appTokens.readableMaxWidth),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(content.title, style: text.headlineSmall),
            const SizedBox(height: DpSpacing.sm),
            if (meta.isNotEmpty)
              Text(
                meta.join(' · '),
                style: text.bodySmall?.copyWith(color: colors.textSecondary),
              ),
            if (content.conceptTags.isNotEmpty) ...[
              const SizedBox(height: DpSpacing.md),
              Wrap(
                spacing: DpSpacing.xs,
                runSpacing: DpSpacing.xs,
                children: [
                  // Material `Chip` 은 P2 에서 폰트 폭주의 원인이었다
                  // (`ChipThemeData.labelStyle` 이 앱 폰트를 대체한다).
                  for (final tag in content.conceptTags) DpTag(label: tag),
                ],
              ),
            ],
            const SizedBox(height: DpSpacing.xl),
            DpMarkdown(data: content.markdown),
            const SizedBox(height: DpSpacing.lg),
            adSlot,
          ],
        ),
      ),
    );
```

진행률 `Row`(`LinearProgressIndicator` + `'$percent% 진행'`)와 `percent`·`progress` 지역 변수를 **지운다** — `ContentProgressPanel` 이 맡는다.

- [ ] **Step 9: 본문을 `.cols` 로 감싸고 헤더 박스를 건드리지 않는다**

`_ContentPageState.build` 의 콘텐츠 sliver 를 아래로 바꾼다. **`_headerKey` 가 붙은 sliver 는 손대지 않는다.**

```dart
          else if (content != null)
            SliverPadding(
              // 좌우 패딩은 셸이 준다. 상하만 남긴다.
              padding: const EdgeInsets.symmetric(vertical: DpSpacing.lg),
              sliver: SliverToBoxAdapter(
                child: DpCols(
                  main: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      if (inlineLoadFailure != null) ...[
                        _InlineContentError(
                          message: inlineLoadFailure,
                          actionLabel: '콘텐츠 다시 불러오기',
                          onRetry: _posting ? null : _loadContent,
                        ),
                        const SizedBox(height: DpSpacing.md),
                      ],
                      if (progressFailure != null) ...[
                        _InlineContentError(
                          message: progressFailure,
                          actionLabel: '진행률 저장 다시 시도',
                          onRetry:
                              _posting ||
                                  (missionState?.progressSubmitting ?? false)
                              ? null
                              : _retryFailedProgress,
                        ),
                        const SizedBox(height: DpSpacing.md),
                      ],
                      WebContentProjection(content: content),
                      if (workspaceKey != null) ...[
                        const SizedBox(height: DpSpacing.xl),
                        DpNextActionBand(
                          actionId: 'open-contextual-sandbox',
                          label: '실습 시작',
                          expectedOutcome: '현재 미션 맥락으로 코드 실습을 시작합니다',
                          state: DpNextActionState.ready,
                          onPressed: (_) {
                            _maybeFlushProgress(force: true);
                            context.push(workspaceKey.sandboxLocation);
                          },
                        ),
                      ],
                    ],
                  ),
                  side: DpSide(
                    children: [
                      ContentProgressPanel(content: content),
                      ContentMissionPanel(
                        mission: currentMissionState?.mission,
                        currentTaskId: workspaceKey?.taskId,
                        onOpenTask: (task) {
                          final contentId = task.contentId;
                          if (contentId == null || task.taskId == null) return;
                          context.push(
                            MissionWorkspaceKey(
                              taskId: task.taskId!,
                              contentId: contentId,
                            ).contentLocation,
                          );
                        },
                      ),
                    ],
                  ),
                ),
              ),
            ),
```

`import 'content_panels.dart';` 를 추가한다.

- [ ] **Step 10: 진행률 보정 회귀를 실측한다 (Review Focus 3)**

Run: `cd apps/web && flutter test test/features/content test/content_progress_smoke_test.dart`

Expected: **Step 1 에서 기록한 진행률 테스트가 전부 통과해야 한다.** 깨지면 원인은 둘 중 하나다:

1. `_headerKey` 가 붙은 위젯이 바뀌었다 → 되돌린다. 이 Task 는 헤더 박스를 바꾸지 않는다.
2. 본문 높이가 달라져 `maxScrollExtent` 가 바뀌었다 → 이것은 **정상**이다. 그 테스트가 특정 픽셀을 단언한다면 비율을 단언하도록 고친다. 고칠 때 doc 주석의 계산 예시(헤더 80·본문 1000)도 함께 갱신한다.

새 경계 테스트를 더한다:

```dart
  testWidgets('콘텐츠: 사이드 패널이 생겨도 진행률은 본문 기준으로 보낸다', (tester) async {
    // 1280 폭(2열)과 390 폭(1열)에서 같은 스크롤 위치가 같은 scrollPct 를 보내는지.
    // 두 폭 모두 헤더 높이를 빼고 나눈 비율이므로 값이 같아야 한다.
  });
```

- [ ] **Step 11: analyze·format 하고 커밋한다**

```bash
cd apps/web && flutter analyze lib/src/features/content
cd ../.. && dart format apps/web/lib/src/features/content/presentation/content_panels.dart apps/web/lib/src/features/content/presentation/content_page.dart
git add apps/web/lib/src/features/content apps/web/test/features/content
git commit -F - <<'MSG'
feat(web): 콘텐츠 화면을 시안 .cols + .prose 760 으로 재구성

- 본문 폭 840 리터럴 → readableMaxWidth(760)
- 진행률을 본문 위에서 사이드 패널로, 「현재 학습 미션」 패널 신설
- Material Chip → DpTag (P2 폰트 폭주 원인 회피)
- _headerKey 가 감싸는 박스는 건드리지 않았다 — _scrollPct 보정 유지

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
git diff origin/develop HEAD --name-only
```

- [ ] **Step 12: 기준선 영향을 기록한다**

```markdown
- `/content` 콘텐츠 — 본문 폭 840 → 760, 진행률 바가 본문 위에서 사이드로, 개념 태그가 `Chip` → `DpTag`(글꼴이 Pretendard 로 바뀐다). ET13 visual baseline 재기록 대상 + `WebContentProjection` 은 ET13 결정적 투영이다.
```

---

## Task 5: 실습 화면 — 시안 `.ide` 문법으로 페인 재도장

**시안 `sandbox`.** 앱은 3페인 반응형(≥1240 3페인 / 1024–1239 2페인+로그 접이 / <1024 세그먼트 탭)이고 시안은 2페인 그리드다. **반응형 거동을 바꾸지 않고** 페인의 테두리 문법만 시안에 맞춘다 — 현재는 페인마다 `Border.all` 을 둘러 페인 사이에 테두리가 **두 겹**이다.

**Files:**
- Modify: `apps/web/lib/src/features/sandbox/presentation/sandbox_layout.dart`
- Modify: `apps/web/lib/src/features/sandbox/presentation/sandbox_page.dart` (좌우 패딩만)
- Test: `apps/web/test/features/sandbox/` 아래 기존 테스트 전부
- Test: `apps/web/test/features/sandbox/sandbox_layout_chrome_test.dart` (신규)

**Interfaces:**
- Consumes: `DpRadius.card`·`DpColors.border`·`DpColors.surface` — 기존 토큰.
- Produces: `SandboxLayout` 의 공개 시그니처(`editor`·`log`·`review`·`onEditorVisible`·`onReviewVisibilityChanged`)와 `SandboxLayoutState` 의 `showEditor()`·`showLog()`·`showReview()`·`isReviewVisible` 는 **바뀌지 않는다.**

### 판정 (Ruling)

| 기존 요소 | 처리 | 근거 |
|---|---|---|
| 3페인/2페인/세그먼트 탭 반응형 | **보존** | 시안은 2페인이지만 앱의 3페인은 로그와 리뷰를 동시에 보게 하는 기능이다. 기능 보존 규칙. 시안 `.ide` 의 1열 접힘(`@container (max-width:720px)`)은 앱의 `<1024` 세그먼트 탭이 이미 더 강하게 담당한다. |
| 페인마다 `Border.all` | **교체** — 바깥 테두리 한 겹 + 페인 사이 구분선 | 시안 `.ide{border:1px solid;border-radius:8px;overflow:hidden}` + `.ide .pane+.pane{border-left:1px solid}`. 현재는 페인 사이가 2px 로 보인다. |
| `IndexedStack`(에디터 State 보존) | **보존** | 탭 전환 시 코드가 소실되지 않게 하는 기존 결함 수정(F5-b)이다. |
| 로그 접이 버튼 | **보존** | 1024–1239 전용 기능. |
| `SegmentedButton` 의 좌측 정렬 패딩(`horizontal: w < 600 ? lg : xl`) | **제거** | 그 패딩은 「페이지 헤더의 좌측선과 맞추기」 위한 것이었고, 이제 셸이 좌우 패딩을 주므로 여기서 또 주면 어긋난다. |
| `SafeArea` | **보존** | 모바일 브라우저 노치 대응. |

- [ ] **Step 1: 기준선을 확인한다**

Run: `cd apps/web && flutter test test/features/sandbox 2>&1 | tail -5`

Expected: 통과 개수를 기록한다.

- [ ] **Step 2: 페인 테두리 실패 테스트를 쓴다**

`apps/web/test/features/sandbox/sandbox_layout_chrome_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:web/src/features/sandbox/presentation/sandbox_layout.dart';

Widget _host(Size size) => MediaQuery(
  data: MediaQueryData(size: size),
  child: MaterialApp(
    theme: DpTheme.light(),
    home: const Scaffold(
      body: SandboxLayout(
        editor: Text('에디터'),
        log: Text('로그'),
        review: Text('리뷰'),
      ),
    ),
  ),
);

void main() {
  testWidgets('SandboxLayout: 바깥 테두리는 한 겹이고 페인마다 두르지 않는다', (tester) async {
    await tester.pumpWidget(_host(const Size(1280, 900)));

    // 시안 `.ide` — 바깥 컨테이너 하나가 테두리와 반경 8을 갖는다.
    final frame = tester.widget<Container>(
      find.byKey(const ValueKey('sandbox-ide-frame')),
    );
    final decoration = frame.decoration! as BoxDecoration;
    expect(decoration.borderRadius, BorderRadius.circular(DpRadius.card));
    expect(decoration.border, isNotNull);

    // 페인 자체는 테두리를 갖지 않는다 — 사이 구분선만 있다.
    expect(find.byKey(const ValueKey('sandbox-pane-border')), findsNothing);
  });

  testWidgets('SandboxLayout: 1280 에서 3페인을 그린다', (tester) async {
    await tester.pumpWidget(_host(const Size(1280, 900)));
    expect(find.text('에디터'), findsOneWidget);
    expect(find.text('로그'), findsOneWidget);
    expect(find.text('리뷰'), findsOneWidget);
  });

  testWidgets('SandboxLayout: 390 에서 세그먼트 탭으로 한 페인만 보인다', (tester) async {
    await tester.pumpWidget(_host(const Size(390, 900)));
    expect(find.byType(SegmentedButton<int>), findsOneWidget);
    // IndexedStack 이라 셋 다 트리에 있고 하나만 보인다.
    expect(find.byType(IndexedStack), findsOneWidget);
  });
}
```

- [ ] **Step 3: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/sandbox/sandbox_layout_chrome_test.dart`

Expected: FAIL — `sandbox-ide-frame` 키가 없다.

- [ ] **Step 4: `sandbox_layout.dart` 의 페인 문법을 바꾼다**

`SandboxLayoutState.build` 를 아래로 바꾼다. `pane()` 헬퍼를 **없애고** 바깥 프레임 하나 + 페인 사이 구분선으로 간다.

```dart
  @override
  Widget build(BuildContext context) {
    final w = MediaQuery.sizeOf(context).width;
    final c = context.dpColors;
    _reportReviewVisibility(w >= 1024 || _tab == 2);

    // 시안 `.ide{border:1px solid var(--border);border-radius:8px;overflow:hidden}`.
    // 페인마다 `Border.all` 을 두르면 페인 사이가 2px 로 보인다(옛 코드).
    Widget frame(Widget child) => Container(
      key: const ValueKey('sandbox-ide-frame'),
      decoration: BoxDecoration(
        color: c.surface,
        border: Border.all(color: c.border),
        borderRadius: BorderRadius.circular(DpRadius.card),
      ),
      clipBehavior: Clip.antiAlias,
      child: child,
    );

    // 시안 `.ide .pane+.pane{border-left:1px solid var(--border)}`.
    Widget vDivider() => Container(width: 1, color: c.border);
    Widget hDivider() => Container(height: 1, color: c.border);

    if (w >= 1240) {
      return frame(
        Row(
          children: [
            Expanded(flex: 5, child: widget.editor),
            vDivider(),
            Expanded(flex: 3, child: widget.log),
            vDivider(),
            Expanded(flex: 4, child: widget.review),
          ],
        ),
      );
    }

    if (w >= 1024) {
      return Column(
        children: [
          Expanded(
            child: frame(
              Row(
                children: [
                  Expanded(flex: 6, child: widget.editor),
                  vDivider(),
                  Expanded(flex: 5, child: widget.review),
                ],
              ),
            ),
          ),
          // 로그 접이 — 1024–1239 전용 기능이므로 유지한다.
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: () => setState(() => _logOpen = !_logOpen),
              icon: Icon(_logOpen ? DpIcons.expandMore : DpIcons.expandLess),
              label: Text(_logOpen ? '실행 로그 접기' : '실행 로그 펼치기'),
            ),
          ),
          if (_logOpen) SizedBox(height: 160, child: frame(widget.log)),
        ],
      );
    }

    // <1024: 세그먼트 탭 1페인.
    // `panes[_tab]` 로 현재 탭만 트리에 넣으면 탭 전환 시 에디터 State(입력)가
    // 폐기되어 코드가 소실된다(F5-b) → IndexedStack 으로 전 페인을 유지한다.
    return Column(
      children: [
        // 좌우 패딩을 주지 않는다 — 셸이 준다(옛 코드는 페이지 헤더의 좌측선과
        // 맞추려고 여기서 직접 줬다).
        Padding(
          padding: const EdgeInsets.symmetric(vertical: DpSpacing.sm),
          child: Align(
            alignment: Alignment.centerLeft,
            child: SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 0, label: Text('에디터')),
                ButtonSegment(value: 1, label: Text('실행')),
                ButtonSegment(value: 2, label: Text('리뷰')),
              ],
              selected: {_tab},
              onSelectionChanged: (s) => setState(() {
                _tab = s.first;
                if (_tab == 0) widget.onEditorVisible?.call();
              }),
            ),
          ),
        ),
        Expanded(
          child: frame(
            IndexedStack(
              index: _tab,
              children: [widget.editor, widget.log, widget.review],
            ),
          ),
        ),
      ],
    );
  }
```

`hDivider()` 를 쓰지 않으면 지운다(`analyze` 가 경고한다).

- [ ] **Step 5: 테스트를 돌려 green 을 확인한다**

Run: `cd apps/web && flutter test test/features/sandbox/sandbox_layout_chrome_test.dart`

Expected: PASS 3/3.

- [ ] **Step 6: `sandbox_page.dart` 의 좌우 패딩을 없앤다**

`_buildCanonical` 의 맥락 스크롤 영역:

```dart
              child: SingleChildScrollView(
                key: const ValueKey('sandbox-context-scroll'),
                // 좌우 패딩은 셸이 준다.
                padding: const EdgeInsets.symmetric(vertical: DpSpacing.lg),
```

`_buildLegacy` 는 `DpPageHeader` 다음에 바로 `Expanded(child: _workspaceLayout(...))` 이므로 손댈 패딩이 없다. `_missionRecovery` 안에 좌우 패딩이 있으면 같이 없앤다.

- [ ] **Step 7: 실습 테스트 전체를 돌린다**

Run: `cd apps/web && flutter test test/features/sandbox`

Expected: Step 1 의 개수와 같게 PASS. 페인 테두리를 단언하던 테스트가 있으면 새 구조(`sandbox-ide-frame`)로 고친다.

- [ ] **Step 8: analyze·format 하고 커밋한다**

```bash
cd apps/web && flutter analyze lib/src/features/sandbox
cd ../.. && dart format apps/web/lib/src/features/sandbox/presentation/sandbox_layout.dart apps/web/lib/src/features/sandbox/presentation/sandbox_page.dart
git add apps/web/lib/src/features/sandbox apps/web/test/features/sandbox
git commit -F - <<'MSG'
feat(web): 실습 화면 페인을 시안 .ide 문법으로 — 테두리 한 겹 + 사이 구분선

- 페인마다 Border.all → 바깥 프레임 하나(반경 8) + 페인 사이 1px 구분선
- 세그먼트의 좌우 패딩 제거 — 셸이 준다
- 3페인/2페인+로그 접이/세그먼트 탭 반응형과 IndexedStack 은 그대로

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
git diff origin/develop HEAD --name-only
```

- [ ] **Step 9: 기준선 영향을 기록한다**

```markdown
- `/sandbox` 실습 — 페인 사이 테두리가 2px → 1px, 바깥 반경 8 적용, 세그먼트 좌측 위치가 셸 패딩 기준으로 이동. ET13 visual baseline 재기록 대상.
```

---

## Task 6: 멘토 화면 — `.cols` + 맥락을 사이드로

**시안 `mentor`.** 대화와 작성칸을 `.cols` 좌측에, 「선택한 학습 맥락」·「맥락 미리보기」를 `.side` 로 옮긴다. 현재는 맥락 캡슐이 대화 **위**에 있어 좁은 화면에서 대화가 밀린다.

대화는 자체 스크롤(`ListView` + `_scroll`)을 유지해야 한다(스트리밍 중 자동 하단 이동이 그 컨트롤러에 달려 있다). 그래서 이 Task 는 `DpCols` 에 높이를 채우는 `stretch` 모드를 더한다.

**Files:**
- Modify: `packages/dp_design/lib/src/layout/dp_cols.dart`
- Modify: `packages/dp_design/test/layout/dp_cols_test.dart`
- Modify: `apps/web/lib/src/features/mentor/presentation/mentor_page.dart`
- Test: `apps/web/test/features/mentor/` 아래 기존 테스트 전부

**Interfaces:**
- Consumes: `DpCols`·`DpSide` — Task 1.
- Produces: `DpCols({..., bool stretch = false})` — `true` 면 2열에서 `CrossAxisAlignment.stretch`, 1열에서 `main` 을 `Expanded` 로 감싼다. 높이가 유한한 부모 안에서 내부 스크롤 위젯을 쓰는 화면(멘토)이 소비한다.

### 판정 (Ruling)

| 기존 요소 | 처리 | 근거 |
|---|---|---|
| `WebMentorContextProjection`(맥락 캡슐) | **위치 이동** — 대화 위 → `.side` 첫 패널 | 시안 `.side` 의 「선택한 학습 맥락」·「맥락 미리보기」에 정확히 대응한다. 위젯·상태·콜백은 그대로다. |
| `_ReferencePanel`(참고 자료) | **위치 이동** — 작성칸 위 → `.side` | 시안에 대응이 없지만 맥락과 같은 성질이라 사이드가 맞다. 지우지 않는다. |
| `_conversation`(`ListView` + `_scroll`) | **보존** — 자체 스크롤 유지 | 스트리밍 중 자동 하단 이동이 이 컨트롤러에 달려 있다. 페이지 스크롤로 바꾸면 그 기능을 잃는다. |
| `_LegacyComposer`·`_ContextualComposer` | **보존** — `.cols` 좌측 맨 아래 | 시안 `.fld` 작성칸. |
| `_PartialNotice`·`_PartialText`·`_InlineError`·`DpKillSwitch` | **보존** — 위치 그대로 | 상태 분기를 잃지 않는다. |
| `_Bubble` 의 `maxWidth: width * 0.86` | **토큰으로 교체** — `readableMaxWidth`(760) | 시안 `.msg{max-width:760px}`. 화면 폭 비율은 2열에서 말풍선이 사이드 위로 넘치게 만든다. |

- [ ] **Step 1: `DpCols.stretch` 실패 테스트를 쓴다**

`packages/dp_design/test/layout/dp_cols_test.dart` 에 추가:

```dart
  testWidgets('DpCols(stretch): 2열에서 두 칼럼이 부모 높이를 채운다', (tester) async {
    await tester.pumpWidget(
      _host(
        const SizedBox(
          height: 400,
          child: DpCols(
            stretch: true,
            main: ColoredBox(color: Color(0xFF000000), key: ValueKey('cols-main')),
            side: ColoredBox(color: Color(0xFF000000), key: ValueKey('cols-side')),
          ),
        ),
        size: const Size(1280, 800),
      ),
    );

    expect(tester.getSize(find.byKey(const ValueKey('cols-main'))).height, 400);
    expect(tester.getSize(find.byKey(const ValueKey('cols-side'))).height, 400);
  });
```

- [ ] **Step 2: 테스트를 돌려 red 를 확인한다**

Run: `cd packages/dp_design && flutter test test/layout/dp_cols_test.dart --plain-name "stretch"`

Expected: FAIL — `stretch` 파라미터가 없어 컴파일되지 않는다.

- [ ] **Step 3: `DpCols` 에 `stretch` 를 더한다**

`packages/dp_design/lib/src/layout/dp_cols.dart`:

```dart
  const DpCols({
    super.key,
    required this.main,
    required this.side,
    this.stretch = false,
  });

  final Widget main;
  final Widget side;

  /// 부모 높이를 채운다. 내부에 자체 스크롤 위젯(`ListView` 등)을 둔 화면이
  /// 쓴다 — 기본값(false)은 시안 `align-items:start` 그대로다.
  final bool stretch;
```

```dart
    if (!twoColumn) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: stretch ? MainAxisSize.max : MainAxisSize.min,
        children: [
          stretch ? Expanded(child: main) : main,
          const SizedBox(height: DpSpacing.xl),
          side,
        ],
      );
    }

    return Row(
      crossAxisAlignment: stretch
          ? CrossAxisAlignment.stretch
          : CrossAxisAlignment.start,
      children: [
        Expanded(flex: 2, child: main),
        const SizedBox(width: DpSpacing.xl),
        Expanded(child: side),
      ],
    );
```

- [ ] **Step 4: 테스트를 돌려 green 을 확인한다**

Run: `cd packages/dp_design && flutter test test/layout/dp_cols_test.dart`

Expected: PASS 4/4. 1열 `stretch` 는 `side` 가 고정 높이를 갖게 되므로, 멘토의 compact 에서 사이드가 길면 스크롤이 필요하다 — Step 8 에서 확인한다.

- [ ] **Step 5: 멘토 화면의 `.cols` 실패 테스트를 쓴다**

`apps/web/test/features/mentor/` 의 기존 테스트 파일에 추가:

```dart
  testWidgets('멘토: 맥락 캡슐이 사이드에 있고 대화가 좌측에 있다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(1280, 900)));
    await tester.pumpAndSettle();

    expect(find.byType(DpCols), findsOneWidget);

    final capsule = tester.getRect(find.byType(WebMentorContextProjection));
    final chat = tester.getRect(find.byType(ListView).first);
    // 사이드는 오른쪽 칼럼이다.
    expect(capsule.left, greaterThan(chat.left));
  });
```

- [ ] **Step 6: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/mentor --plain-name "맥락 캡슐이 사이드에"`

Expected: FAIL — 현재 캡슐은 대화 위에 있다.

- [ ] **Step 7: `_buildContextual` 을 `.cols` 로 다시 짠다**

```dart
    return Scaffold(
      body: SafeArea(
        child: DpCols(
          stretch: true,
          main: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: state.status == MentorStatus.killSwitch
                    ? const DpKillSwitch()
                    : _conversation(state),
              ),
              if (state.status == MentorStatus.partial)
                _PartialText(message: state.error),
              if (state.status == MentorStatus.busy)
                _PartialText(message: state.error),
              if (state.status == MentorStatus.failed && state.error != null)
                _InlineError(
                  message: state.error!,
                  color: context.dpColors.danger,
                ),
              if (state.status != MentorStatus.killSwitch)
                _ContextualComposer(
                  controller: _input,
                  enabled: !_contextBusy(state),
                  pending: _contextBusy(state),
                  actionLabel: _contextualActionLabel(state),
                  onPressed: () => _handleContextualPrimary(state),
                ),
            ],
          ),
          // 시안 `.side` — 「선택한 학습 맥락」·「맥락 미리보기」가 여기다.
          side: SingleChildScrollView(
            child: DpSide(
              children: [
                WebMentorContextProjection(
                  mission: mission,
                  task: task,
                  fields: _contextFields(state, previewMatches),
                  capsuleMode: capsuleMode,
                  capsuleStatus: _capsuleStatus(state),
                  statusMessage: state.contextError,
                  disclosureFocusNode: _capsuleDisclosureFocus,
                  onDisclosurePressed: () =>
                      setState(() => _capsuleExpandedOverride = !capsuleExpanded),
                  onFieldEditRequested: (_) => _showContextEditor(),
                  onRetry: () =>
                      _controller().preparePreview(_input.text.trim()),
                ),
                if (state.references.isNotEmpty)
                  _ReferencePanel(references: state.references),
              ],
            ),
          ),
        ),
      ),
    );
```

`compactOrMedium` 을 쓰는 `capsuleExpanded` 기본값은 그대로 둔다 — 사이드가 좁을 때 접힌 채 시작하는 것이 맞다.

- [ ] **Step 8: `_buildLegacy` 도 같은 배치로 맞춘다**

```dart
  Widget _buildLegacy(BuildContext context, MentorState state) {
    final colors = context.dpColors;
    return Scaffold(
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const DpPageHeader(
            title: 'AI 멘토',
            description: '막히는 부분을 물어보면 학습 맥락을 반영해 답합니다',
          ),
          Expanded(
            child: DpCols(
              stretch: true,
              main: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (state.status == MentorStatus.killSwitch)
                    const DpKillSwitch()
                  else
                    Expanded(child: _conversation(state)),
                  if (state.status == MentorStatus.partial)
                    _PartialNotice(
                      message: state.error,
                      onRetry: _controller().retry,
                    ),
                  if (state.status == MentorStatus.busy)
                    _PartialNotice(
                      message: state.error,
                      onRetry: _controller().retry,
                    ),
                  if (state.status == MentorStatus.failed &&
                      state.error != null)
                    _InlineError(message: state.error!, color: colors.danger),
                  if (state.status != MentorStatus.killSwitch)
                    _LegacyComposer(controller: _input, onSend: _sendLegacy),
                ],
              ),
              side: SingleChildScrollView(
                child: DpSide(
                  children: [
                    if (state.references.isNotEmpty)
                      _ReferencePanel(references: state.references),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
```

참고 자료가 없으면 `DpSide(children: [])` 가 빈 `Column` 이 되어 사이드가 빈칸이 된다. 그때는 1열로 두는 편이 낫다 — 아래처럼 분기한다:

```dart
            child: state.references.isEmpty
                ? mainColumn
                : DpCols(stretch: true, main: mainColumn, side: sideColumn),
```

`mainColumn`·`sideColumn` 을 지역 변수로 뽑아 두 분기가 같은 것을 쓰게 한다.

- [ ] **Step 9: 말풍선 최대 폭을 토큰으로 바꾼다**

`_Bubble.build` 의 `maxWidth: MediaQuery.sizeOf(context).width * 0.86` 를 아래로 바꾼다:

```dart
        // 시안 `.msg{max-width:760px}`. 화면 폭 비율로 두면 2열에서 말풍선이
        // 사이드 칼럼 폭까지 밀고 들어간다.
        maxWidth: context.appTokens.readableMaxWidth,
```

- [ ] **Step 10: 멘토 테스트 전체를 돌린다 (Review Focus 1·5)**

Run: `cd apps/web && flutter test test/features/mentor`

Expected: PASS. 아래를 확인하고 없으면 만든다:

```dart
  testWidgets('멘토: 390px 에서 대화 → 맥락 순서로 한 열이 된다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(390, 900)));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    final chat = tester.getRect(find.byType(ListView).first);
    final capsule = tester.getRect(find.byType(WebMentorContextProjection));
    expect(capsule.top, greaterThan(chat.top));
  });

  testWidgets('멘토: killSwitch 에서 작성칸을 감춘다', (tester) async {
    await tester.pumpWidget(_app(status: MentorStatus.killSwitch));
    await tester.pumpAndSettle();
    expect(find.byType(DpKillSwitch), findsOneWidget);
  });
```

- [ ] **Step 11: analyze·format 하고 커밋한다**

```bash
cd packages/dp_design && flutter test && cd ../../apps/web && flutter analyze lib/src/features/mentor
cd ../.. && dart format packages/dp_design/lib/src/layout/dp_cols.dart apps/web/lib/src/features/mentor/presentation/mentor_page.dart
git add packages/dp_design/lib/src/layout/dp_cols.dart packages/dp_design/test/layout/dp_cols_test.dart apps/web/lib/src/features/mentor apps/web/test/features/mentor
git commit -F - <<'MSG'
feat(web): 멘토 화면을 시안 .cols 로 — 맥락 캡슐을 사이드로

- WebMentorContextProjection·_ReferencePanel 을 .side 로 이동
- 대화는 자체 스크롤 유지(스트리밍 자동 하단 이동이 그 컨트롤러에 달렸다)
- DpCols 에 stretch 모드 추가 — 내부 스크롤 위젯을 둔 화면용
- 말풍선 최대 폭 width*0.86 → readableMaxWidth(760)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
git diff origin/develop HEAD --name-only
```

- [ ] **Step 12: 기준선 영향을 기록한다**

```markdown
- `/mentor` AI 멘토 — 맥락 캡슐이 대화 위 → 사이드 칼럼, 말풍선 최대 폭이 화면 비율 → 760. ET13 visual baseline 재기록 대상 + `WebMentorContextProjection` 은 ET13 결정적 투영이다.
```

---

## Task 7: PR-A 마무리 — 전 패키지 검증과 PR

**Files:** 코드 변경 없음. 검증과 PR 만 한다.

- [ ] **Step 1: 변경 파일 목록을 확인한다**

Run: `git diff origin/develop HEAD --name-only`

Expected: `packages/dp_design/**`·`apps/web/lib/src/features/{dashboard,path,content,sandbox,mentor}/**`·`apps/web/test/**` 만. `analysis_options.yaml`·`pubspec.lock`·`apps/admin` 밖의 것이 있으면 **그 파일만** 되돌리고 즉시 `git commit --amend --no-edit` 한다.

- [ ] **Step 2: analyze 를 전 패키지에서 돌린다**

Run: `melos run analyze` (없으면 `cd packages/dp_design && flutter analyze` · `cd apps/web && flutter analyze` · `cd apps/admin && flutter analyze`)

Expected: `No issues found!` — 0 issues.

- [ ] **Step 3: 포맷이 깨끗한지 확인한다**

Run: `dart format --output=none --set-exit-if-changed $(git diff origin/develop HEAD --name-only -- '*.dart')`

Expected: exit 0. **디렉터리를 넘기지 않는다** — 로컬 3.47 과 CI 3.44 포매터가 갈리는 무관한 파일까지 바꾼다.

- [ ] **Step 4: 전 패키지 테스트를 돌린다**

Run: `cd packages/dp_core && flutter test` · `cd packages/dp_design && flutter test` · `cd apps/web && flutter test` · `cd apps/admin && flutter test`

Expected: dp_core 174 · dp_design 350+ · web 1010+ · admin 156 PASS. 실패는 전부 이 PR 의 책임이다 — skip 으로 덮지 않는다.

- [ ] **Step 5: PR 을 올린다**

```bash
git push -u origin feat/s3-p4-learning-screens
gh pr create --base develop --title "feat(web): S3-P4a 학습 화면군을 시안 웹 문법으로 재구성" --body-file - <<'BODY'
## 무엇

S3-P4 의 첫 PR. 학습 화면군 5개(오늘·경로·콘텐츠·실습·멘토)를 시안(`Leva 웹 문법 시안`)의 웹 문법으로 재구성한다. **기존 기능을 하나도 지우지 않았다** — 차트·KPI·광고·상태 분기는 전부 남아 있고 배치만 바뀌었다.

## 어떻게

- `dp_design`: `DpCols`/`DpSide` 신설, P3 리뷰 이월 Minor 5건 수정, `DpPageHeader` 좌우 패딩 제거(셸이 준다)
- 오늘: Bento 4열 → `.cols` 2열. 시안에만 있던 「이번 주 과제」 표·「진행」 kv·「왜 이 순서인가요」·「막히면」을 **이미 내려오는 데이터로** 신설. KPI 카드·도넛·배지의 숫자는 「진행」 kv 로 모였다(데이터 손실 없음)
- 경로: `ExpansionTile` 접힘 목록 → 「12주 계획」 표(접혀 있던 목표가 칼럼으로 올라왔다). 근거·진단 요약은 사이드 패널
- 콘텐츠: 본문 폭 840 리터럴 → `readableMaxWidth`(760), 진행률을 사이드로, `Chip` → `DpTag`
- 실습: 페인마다 두르던 테두리 → 바깥 한 겹 + 사이 구분선. 반응형 3페인 거동은 그대로
- 멘토: 맥락 캡슐을 대화 위 → 사이드. 대화의 자체 스크롤은 유지

## 검증

- analyze 0 · format 0 changed
- dp_core / dp_design / web / admin 전 패키지 테스트 통과
- 390px 가로 넘침 없음 · 200% 배율 오버플로 없음 · 콘텐츠 진행률 보정 회귀 없음

## P5 로 넘기는 것

`docs/superpowers/plans/2026-09-27-s3-p4-screen-groups/baseline-impact.md`(documents) 에 기준선 재기록 대상 5화면을 적었다.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
BODY
```

- [ ] **Step 6: CI 6잡이 전부 녹색인지 확인한다**

Run: `gh pr checks --watch`

Expected: `analyze-test`·`browser-ux`·`perf-gate`·`produce-atomic-pair`·`web-image-config-contract` ×2 전부 pass. `perf-gate` 는 약 23분, `browser-ux` 는 약 5분 걸린다.

- **`browser-ux` 가 깨지면**: 시나리오가 옛 구조(행이 클릭 대상·KPI 카드 존재 등)를 기대한다. **시나리오를 고친다** — 화면을 옛 구조로 되돌리지 않는다. 로컬 재현은 P2 에서 확립한 레시피를 쓴다(mock 릴리스 웹 빌드 + 핀 Playwright `v1.55.0-noble` + `--network none` + `--only=<시나리오>`, 약 2분).
- **`perf-gate` 가 깨지면**: 전송량 +5% 초과다. `flutter_staggered_grid_view` 가 이제 쓰이지 않으면 그 의존을 지우는 것이 가장 큰 절감이다 — 소비처 0을 `git grep` 으로 확인한 뒤 `pubspec.yaml` 에서 지운다.

- [ ] **Step 7: 녹색을 확인한 뒤 머지한다**

Run: `gh pr merge --merge`

Expected: merge commit 으로 `develop` 에 들어간다. **CI 가 pending 인 채로 머지하지 않는다**(P3 에서 순서를 어긴 적이 있다).

---

# PR-B — 커뮤니티 (목록 3종·상세 2종·작성·수정 4종)

브랜치: `feat/s3-p4-community-screens` (base: `develop`, PR-A 머지 뒤 분기)

---

## Task 8: 커뮤니티 목록 3종 — 카드 나열 → 칼럼 있는 표

**시안 `free`·`qna`·`feedback`.** `DpListRow` 나열을 `DpWebTable` 로 바꾸고, 게시판별로 칼럼을 다르게 준다. 빈 상태의 「같은 라벨 액션 2개」(P3 이월)도 여기서 닫는다.

**Files:**
- Modify: `apps/web/lib/src/features/community/presentation/community_home_page.dart`
- Modify: `apps/web/lib/src/features/community/presentation/web_community_board_projection.dart`
- Test: `apps/web/test/features/community/community_home_page_test.dart`
- Test: `apps/web/test/features/community/community_header_test.dart`
- Test: `apps/web/test/features/community/community_search_test.dart`
- Test: `apps/web/test/evidence/et13_web_evidence_app_test.dart`
- Test: `apps/web/test/features/community/community_board_table_test.dart` (신규)

**Interfaces:**
- Consumes: `DpWebTable`(`empty` 필수)·`DpPanel`·`DpLink`·`DpStatusText` — Task 1.
- Produces:
  - `communityBoardColumns(CommunityBoard board, {required bool compact}) → List<DpTableColumn>` — 게시판별 칼럼. 최상위 함수로 내보내 표와 테스트가 같은 정의를 쓴다.
  - `communityPostRow({required CommunityPostSummary post, required VoidCallback onTap, required CommunityBoard board, required bool compact, required BuildContext context}) → DpTableRowSpec`
  - `communitySearchRow({required CommunitySearchItem item, required VoidCallback onTap, required CommunityBoard board, required bool compact, required BuildContext context}) → DpTableRowSpec`
  - `CommunityBoardEmpty` 는 `onCompose` 를 **더 이상 받지 않는다**(`CommunityBoardEmpty({required CommunityBoard board, Key? key})`).
  - `CommunityPostRow` 위젯은 **삭제된다** — 행이 표의 셀 목록이 되므로 위젯일 필요가 없다.

### 실측: 시안의 두 칼럼은 데이터가 없다

시안 목록 표는 「작성」(3시간 전)과 작성자 이름을 보여 준다. **둘 다 지금 구현할 수 없다.**

- 프론트 모델 `CommunityPostSummary` 필드: `id`·`title`·`boardType`·`authorId`·`solved`·`upvoteCount`·`replyCount`·`excerpt`.
- 백엔드 `devpath-community-svc` 의 `PostSummaryView` (`src/main/java/ai/devpath/community/post/dto/PostSummaryView.java`): `long id, String boardType, String title, Long authorId, boolean solved, int upvoteCount, int replyCount, String excerpt`.
- 즉 **서버가 작성 시각도, 작성자 표시 이름도 보내지 않는다.** `authorId` 는 숫자이고 닉네임 조회 API 를 이 목록에서 부르는 것은 N+1 이다.

→ 「작성」 칼럼과 작성자 이름은 **구현하지 않는다.** Global Constraints 의 「새 API 호출을 추가하지 않는다」가 우선한다. 이것은 P4 가 시안과 1:1 이 되지 못하는 **유일한 항목**이므로 `baseline-impact.md` 와 핸드오프에 「후속: `PostSummaryView` 에 `createdAt`·작성자 표시 이름 추가(백엔드 계약 변경)」로 남긴다.

### 판정 (Ruling)

| 기존 요소 | 처리 | 근거 |
|---|---|---|
| `CommunityPostRow`(`DpListRow` 나열) | **표로 교체** | 시안 `.panel > table`. P3 이 `DpWebTable` 을 만든 목적이다. |
| `excerpt`(미리보기 한 줄) | **보존** — 제목 칼럼 아래 `.ex` 줄 | 시안 표의 `.ex` 에 대응한다. 데이터가 있다. |
| `CommunityBadgeChip('✓ 해결됨')` | **`DpStatusText` 로 교체** — Q/A 의 「상태」 칼럼 | 시안 `.st.ok`. 자체 `Container`+`BoxDecoration` 을 없앤다. |
| `trailing`(「답변 2 · 추천 5」 한 줄) | **칼럼으로 분리** | 시안은 답변·추천을 각각 숫자 칼럼으로 둔다. 좁은 폭에서는 답변만 감춘다(`.hide-n`). |
| 피드 광고(`COMMUNITY_FEED`, 5번째 뒤) | **표 아래로 이동** | 표 중간에 광고 행을 끼우면 칼럼 정렬이 깨진다. 표 다음 sliver 로 옮기고 `semanticChildCount` 계산은 그대로 둔다(콘텐츠 수만 센다). |
| 검색의 「더 보기」 버튼 | **표 아래로 이동** | 같은 이유. |
| `SearchHighlightText`(매칭 근거) | **보존** — 제목 칼럼 아래 | 검색 결과 표에서 `excerpt` 자리를 하이라이트가 대신한다. |
| `CommunityBoardEmpty` 의 `actionLabel: board.composeLabel` | **제거** | 헤더 액션과 **접근명이 같아** 스크린리더로 구분할 수 없다(P3 이월). 헤더의 작성 버튼이 상시 보이므로 빈 상태는 안내만 한다. |
| `PinnedHeaderSliver` 검색·정렬 줄 | **보존** — 좌우 패딩만 제거 | 시안 `.filters`. 고정 헤더 거동은 기능이다. |
| `CommunitySortMenu` 의 `MenuAnchor` focus 복귀 | **보존** | 2026-09-17 함정 5 의 수정이다. |

- [ ] **Step 1: 기준선을 확인한다**

Run: `cd apps/web && flutter test test/features/community 2>&1 | tail -5`

Expected: 통과 개수를 기록한다. 커뮤니티는 테스트가 26개 파일로 가장 많다 — 이 Task 가 가장 많이 깨뜨린다.

- [ ] **Step 2: 게시판별 칼럼 실패 테스트를 쓴다**

`apps/web/test/features/community/community_board_table_test.dart`:

```dart
import 'package:dp_core/dp_core.dart';
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:web/src/features/community/presentation/web_community_board_projection.dart';
import 'package:web/src/features/community/state/community_state.dart';

const _qnaPost = CommunityPostSummary(
  id: 1,
  boardType: 'QNA',
  title: 'async/await가 헷갈려요',
  solved: true,
  upvoteCount: 5,
  replyCount: 2,
  excerpt: 'async/await에서 예외는 어디서 잡나요?',
);

const _freePost = CommunityPostSummary(
  id: 10,
  boardType: 'FREE',
  title: '오늘 배운 것 공유',
  upvoteCount: 4,
  replyCount: 1,
  excerpt: '오늘은 Riverpod 을 배웠어요.',
);

Widget _host(Widget child, {Size size = const Size(1280, 900)}) => MediaQuery(
  data: MediaQueryData(size: size),
  child: MaterialApp(
    theme: DpTheme.light(),
    home: Scaffold(body: SingleChildScrollView(child: child)),
  ),
);

void main() {
  test('communityBoardColumns: Q/A 는 상태 칼럼을 갖고 자유게시판은 갖지 않는다', () {
    final qna = communityBoardColumns(CommunityBoard.qna, compact: false);
    final free = communityBoardColumns(CommunityBoard.free, compact: false);

    expect(qna.map((c) => c.label), containsAllInOrder(['질문', '상태']));
    expect(free.map((c) => c.label), containsAllInOrder(['제목']));
    expect(free.map((c) => c.label), isNot(contains('상태')));
  });

  test('communityBoardColumns: 작성 시각 칼럼은 없다 — 서버가 보내지 않는다', () {
    for (final board in kCommunityBoards) {
      final labels = communityBoardColumns(board, compact: false)
          .map((c) => c.label)
          .toList();
      expect(labels, isNot(contains('작성')));
    }
  });

  test('communityBoardColumns: compact 는 답변/댓글 칼럼을 감춘다', () {
    final wide = communityBoardColumns(CommunityBoard.qna, compact: false);
    final narrow = communityBoardColumns(CommunityBoard.qna, compact: true);
    expect(wide.map((c) => c.label), contains('답변'));
    expect(narrow.map((c) => c.label), isNot(contains('답변')));
  });

  testWidgets('WebCommunityBoardProjection: Q/A 를 표로 그리고 해결 상태를 말한다', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        SizedBox(
          height: 900,
          child: WebCommunityBoardProjection(
            board: CommunityBoard.qna,
            posts: const [_qnaPost],
            onOpenPost: (_) {},
            onCompose: () {},
          ),
        ),
      ),
    );

    expect(find.text('질문'), findsOneWidget);
    expect(find.text('async/await가 헷갈려요'), findsOneWidget);
    expect(find.text('✓ 해결됨'), findsOneWidget);
    expect(find.text('async/await에서 예외는 어디서 잡나요?'), findsOneWidget);
    expect(find.text('2'), findsOneWidget); // 답변
    expect(find.text('5'), findsOneWidget); // 추천
  });

  testWidgets('WebCommunityBoardProjection: 자유게시판은 상태 칼럼 없이 그린다', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        SizedBox(
          height: 900,
          child: WebCommunityBoardProjection(
            board: CommunityBoard.free,
            posts: const [_freePost],
            onOpenPost: (_) {},
            onCompose: () {},
          ),
        ),
      ),
    );

    expect(find.text('상태'), findsNothing);
    expect(find.text('오늘 배운 것 공유'), findsOneWidget);
  });

  testWidgets('WebCommunityBoardProjection: 빈 목록은 안내만 하고 중복 액션을 두지 않는다', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        SizedBox(
          height: 900,
          child: WebCommunityBoardProjection(
            board: CommunityBoard.free,
            posts: const [],
            onOpenPost: (_) {},
            onCompose: () {},
          ),
        ),
      ),
    );

    expect(find.text('아직 글이 없어요'), findsOneWidget);
    // 헤더의 작성 버튼 하나만 있어야 한다 — 같은 접근명이 둘이면
    // 스크린리더로 구분할 수 없다(P3 이월).
    expect(find.text('글 작성'), findsOneWidget);
  });

  testWidgets('표 행이 스크린리더에서 칼럼별로 읽힌다', (tester) async {
    final handle = tester.ensureSemantics();
    await tester.pumpWidget(
      _host(
        SizedBox(
          height: 900,
          child: WebCommunityBoardProjection(
            board: CommunityBoard.qna,
            posts: const [_qnaPost],
            onOpenPost: (_) {},
            onCompose: () {},
          ),
        ),
      ),
    );

    // 제목은 링크로, 숫자는 별도 라벨로 남는다 — 행 제스처가 셀을 삼키지 않는다.
    expect(find.bySemanticsLabel('async/await가 헷갈려요'), findsOneWidget);
    expect(find.bySemanticsLabel('2'), findsOneWidget);
    handle.dispose();
  });
}
```

- [ ] **Step 3: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/community/community_board_table_test.dart`

Expected: FAIL — `communityBoardColumns` 가 없다.

- [ ] **Step 4: `web_community_board_projection.dart` 를 표 기반으로 다시 짠다**

`CommunityBoardCopy` 확장은 그대로 두고, `CommunityPostRow` 를 지우고 아래를 넣는다.

```dart
/// 게시판별 표 칼럼(시안 `free`/`qna`/`feedback` 의 `<thead>`).
///
/// **「작성」 칼럼이 없다.** 서버 `PostSummaryView` 가 작성 시각도 작성자 표시
/// 이름도 보내지 않는다(`id·boardType·title·authorId·solved·upvoteCount·
/// replyCount·excerpt`). 시안의 그 칼럼은 백엔드 계약 변경이 있어야 한다.
///
/// [compact] 는 시안 `.hide-n` — 좁은 폭에서 감추는 칼럼을 목록에서 뺀다.
List<DpTableColumn> communityBoardColumns(
  CommunityBoard board, {
  required bool compact,
}) {
  final isQna = board == CommunityBoard.qna;
  return [
    (label: isQna ? '질문' : '제목', width: null, numeric: false),
    if (isQna) (label: '상태', width: 80, numeric: false),
    if (!compact)
      (label: isQna ? '답변' : '댓글', width: 56, numeric: true),
    (label: '추천', width: 56, numeric: true),
  ];
}

/// 목록 한 행. 셀 개수는 [communityBoardColumns] 와 반드시 같아야 한다
/// (`DpWebTable` 의 assert 가 어긋남을 배치 전에 잡는다).
DpTableRowSpec communityPostRow({
  required BuildContext context,
  required CommunityPostSummary post,
  required CommunityBoard board,
  required bool compact,
  required VoidCallback onTap,
}) {
  final isQna = board == CommunityBoard.qna;
  return (
    cells: [
      _titleCell(
        context: context,
        title: post.title,
        preview: post.excerpt.isEmpty ? null : Text(post.excerpt),
        onTap: onTap,
      ),
      if (isQna)
        post.solved
            ? const DpStatusText(text: '✓ 해결됨', tone: DpStatusTone.done)
            : DpStatusText(
                text: post.replyCount == 0 ? '답변 대기' : '답변 ${post.replyCount}',
                tone: DpStatusTone.idle,
              ),
      if (!compact) Text('${post.replyCount}'),
      Text('${post.upvoteCount}'),
    ],
    onTap: onTap,
  );
}

/// 검색 결과 한 행. 미리보기 자리에 매칭 근거(하이라이트)를 always 보여 준다.
DpTableRowSpec communitySearchRow({
  required BuildContext context,
  required CommunitySearchItem item,
  required CommunityBoard board,
  required bool compact,
  required VoidCallback onTap,
}) {
  final isQna = item.boardType == 'QNA';
  // 본문 매칭이 없으면 highlight 가 비어 오므로 excerpt 로 폴백한다.
  final body = item.highlight.isNotEmpty ? item.highlight : item.excerpt;
  return (
    cells: [
      _titleCell(
        context: context,
        title: item.title,
        preview: body.isEmpty ? null : SearchHighlightText(body),
        onTap: onTap,
      ),
      if (board == CommunityBoard.qna)
        isQna && item.solved
            ? const DpStatusText(text: '✓ 해결됨', tone: DpStatusTone.done)
            : const DpStatusText(text: '답변 대기', tone: DpStatusTone.idle),
      if (!compact) Text('${item.replyCount}'),
      Text('${item.upvoteCount}'),
    ],
    onTap: onTap,
  );
}

/// 제목 셀 — 시안 `a.ttl` + `.ex`. 접근성 컨트롤은 이 링크 하나다
/// (행 제스처는 `DpWebTable` 이 시맨틱스에서 뺀다).
Widget _titleCell({
  required BuildContext context,
  required String title,
  required Widget? preview,
  required VoidCallback onTap,
}) {
  final c = context.dpColors;
  return Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    mainAxisSize: MainAxisSize.min,
    children: [
      DpLink.title(text: title, onTap: onTap),
      if (preview != null) ...[
        const SizedBox(height: DpSpacing.xs),
        DefaultTextStyle.merge(
          style: TextStyle(fontSize: 13, color: c.textSecondary),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          child: preview,
        ),
      ],
    ],
  );
}
```

`import 'widgets/search_highlight.dart';` 를 추가한다. `CommunityBadgeChip` 은 소비처가 없어지면 **지운다**(`git grep CommunityBadgeChip` 으로 확인 — 상세 화면이 쓰면 남긴다).

`WebCommunityBoardProjection.build` 를 표로 바꾼다:

```dart
  @override
  Widget build(BuildContext context) {
    final compact = context.windowClass == DpWindowClass.compact;
    return CustomScrollView(
      semanticChildCount: posts.length,
      slivers: [
        SliverToBoxAdapter(
          child: CommunityBoardHeader(board: board, onCompose: onCompose),
        ),
        SliverToBoxAdapter(
          child: DpPanel(
            child: DpWebTable(
              columns: communityBoardColumns(board, compact: compact),
              empty: CommunityBoardEmpty(board: board),
              rows: [
                for (final post in posts)
                  communityPostRow(
                    context: context,
                    post: post,
                    board: board,
                    compact: compact,
                    onTap: () => onOpenPost(post),
                  ),
              ],
            ),
          ),
        ),
      ],
    );
  }
```

`CommunityBoardEmpty` 에서 액션을 뺀다:

```dart
/// 게시판별 빈 상태.
///
/// **작성 액션을 갖지 않는다.** 페이지 헤더의 작성 버튼이 빈 목록에서도 보이고,
/// 같은 라벨의 버튼이 둘이면 스크린리더가 둘을 구분할 수 없다(P3 이월 과제).
class CommunityBoardEmpty extends StatelessWidget {
  const CommunityBoardEmpty({super.key, required this.board});

  final CommunityBoard board;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: DpSpacing.xl),
    child: DpEmpty(
      icon: DpIcons.community,
      title: board.emptyTitle,
      message: board.emptyMessage,
    ),
  );
}
```

- [ ] **Step 5: 테스트를 돌려 green 을 확인한다**

Run: `cd apps/web && flutter test test/features/community/community_board_table_test.dart`

Expected: PASS 7/7. `DpEmpty` 가 `actionLabel` 없이도 그려지는지 확인한다(선택 파라미터여야 한다 — 아니면 `DpEmpty` 를 고친다).

- [ ] **Step 6: `community_home_page.dart` 를 표로 바꾼다**

`_bodySlivers` 를 아래로 바꾼다:

```dart
      case CommunityPhase.loaded:
        final compact = context.windowClass == DpWindowClass.compact;
        const feedAdAt = 5; // 5번째 게시글 뒤 — 이제 표 아래에 둔다
        return [
          SliverToBoxAdapter(
            child: DpPanel(
              child: DpWebTable(
                columns: communityBoardColumns(board, compact: compact),
                empty: CommunityBoardEmpty(board: board),
                rows: [
                  for (final post in posts)
                    communityPostRow(
                      context: context,
                      post: post,
                      board: board,
                      compact: compact,
                      onTap: () => context.go(
                        post.boardType == 'QNA'
                            ? '/community/${post.id}'
                            : '/community/post/${post.id}?board=${post.boardType}',
                      ),
                    ),
                ],
              ),
            ),
          ),
          if (posts.length >= feedAdAt)
            const SliverToBoxAdapter(
              child: Padding(
                padding: EdgeInsets.only(top: DpSpacing.lg),
                child: AdSlotWidget(slot: 'COMMUNITY_FEED'),
              ),
            ),
        ];
```

`_searchSlivers` 의 `loaded` 분기도 같은 모양으로 바꾼다:

```dart
      case CommunitySearchPhase.loaded:
        final compact = context.windowClass == DpWindowClass.compact;
        return [
          SliverToBoxAdapter(
            child: DpPanel(
              child: DpWebTable(
                columns: communityBoardColumns(board, compact: compact),
                empty: Padding(
                  padding: const EdgeInsets.symmetric(vertical: DpSpacing.xl),
                  child: DpEmpty(
                    icon: DpIcons.search,
                    title: '검색 결과가 없어요',
                    message: '"${search.query}"와 맞는 글을 찾지 못했어요. 다른 낱말로 찾아보세요.',
                  ),
                ),
                rows: [
                  for (final item in search.items)
                    communitySearchRow(
                      context: context,
                      item: item,
                      board: board,
                      compact: compact,
                      onTap: () => context.go(
                        item.boardType == 'QNA'
                            ? '/community/${item.id}'
                            : '/community/post/${item.id}?board=${item.boardType}',
                      ),
                    ),
                ],
              ),
            ),
          ),
          if (search.hasMore)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.only(top: DpSpacing.md),
                child: OutlinedButton(
                  key: const ValueKey('search-more'),
                  onPressed: search.loadingMore
                      ? null
                      : () => ref
                            .read(communitySearchControllerProvider.notifier)
                            .loadMore(board: board.value),
                  child: Text(
                    search.loadingMore
                        ? '불러오는 중…'
                        : '더 보기 (${search.items.length}/${search.total})',
                  ),
                ),
              ),
            ),
        ];
```

빈 검색 결과를 `SliverFillRemaining` 으로 따로 내보내던 분기(`search-empty` 키)는 **표의 `empty` 로 옮겨졌다** — 그 키를 찾는 테스트가 있으면 `DpEmpty` 안의 문구를 찾도록 고친다. `_searchRow` 메서드와 `CommunityPostRow` import 를 지운다.

`PinnedHeaderSliver` 의 좌우 패딩을 없앤다:

```dart
              child: Padding(
                padding: const EdgeInsets.only(
                  top: DpSpacing.md,
                  bottom: DpSpacing.sm,
                ),
```

`SliverPadding(padding: EdgeInsets.all(DpSpacing.lg))` 래퍼들은 전부 없앤다(셸이 좌우를, 표가 자기 행 패딩을 준다).

- [ ] **Step 7: 커뮤니티 테스트 전체를 돌리고 하나씩 고친다**

Run: `cd apps/web && flutter test test/features/community`

Expected: 실패가 많이 난다. 고치는 규칙:

- `DpListRow` 를 찾는 단언 → `DpWebTable` 의 행(`ValueKey('dp-web-table-row')`) 또는 제목 텍스트로 바꾼다.
- 「답변 2 · 추천 5」 한 줄을 찾는 단언 → 칼럼별 숫자(`find.text('2')`)로 바꾼다.
- 빈 상태에서 작성 버튼 **둘**을 기대하는 단언 → 하나로 바꾼다(이번 Task 의 결정이다).
- 행을 탭해 이동하는 테스트 → 그대로 통과해야 한다(`DpTableRowSpec.onTap` 이 남아 있다).
- **행이 클릭 대상임을 시맨틱스로 단언하는 테스트** → 제목 링크를 단언하도록 바꾼다. 행 제스처는 `excludeFromSemantics` 다.

- [ ] **Step 8: ET13 증거 테스트를 돌린다**

Run: `cd apps/web && flutter test test/evidence/et13_web_evidence_app_test.dart test/app/et13_evidence_producer_contract_test.dart`

Expected: PASS. `WebCommunityBoardProjection` 은 ET13 결정적 투영이라 렌더가 바뀐다 — **계약 테스트가 구조를 단언한다면** 그 단언을 새 구조로 고치고, **baseline 이미지를 여기서 재기록하지 않는다**(P5 사람 승인 단계다).

- [ ] **Step 9: 390px 가로 넘침을 확인한다 (Review Focus 1)**

```dart
  testWidgets('커뮤니티 목록: 390px 에서 본문이 가로로 넘치지 않고 표만 스크롤한다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(390, 900)));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(tester.getSize(find.byType(DpWebTable)).width, lessThanOrEqualTo(390));
    expect(
      find.byKey(const ValueKey('dp-web-table-scroll')),
      findsOneWidget,
    );
  });
```

Run: `cd apps/web && flutter test test/features/community --plain-name "390px"`

Expected: PASS — 칼럼 폭 합(제목 유연 + 80 + 56 + 56)이 `minWidth`(640) 보다 좁은 화면에서 표가 자체 가로 스크롤로 들어간다.

- [ ] **Step 10: analyze·format 하고 커밋한다**

```bash
cd apps/web && flutter analyze lib/src/features/community
cd ../.. && dart format apps/web/lib/src/features/community/presentation/community_home_page.dart apps/web/lib/src/features/community/presentation/web_community_board_projection.dart
git add apps/web/lib/src/features/community apps/web/test/features/community apps/web/test/evidence
git commit -F - <<'MSG'
feat(web): 커뮤니티 목록 3종을 카드 나열 → 칼럼 있는 표로

- DpListRow 나열 → DpWebTable(게시판별 칼럼: Q/A 는 상태 칼럼을 갖는다)
- 해결 배지 CommunityBadgeChip → DpStatusText
- 「답변 N · 추천 M」 한 줄 → 숫자 칼럼 둘(compact 는 답변을 감춘다)
- 빈 상태의 작성 액션 제거 — 헤더 버튼과 접근명이 같아 구분 불가였다(P3 이월)
- 피드 광고·「더 보기」를 표 아래로(표 중간 행은 칼럼 정렬을 깬다)
- 화면의 좌우 패딩 제거 — 셸이 준다

시안의 「작성」 칼럼과 작성자 이름은 구현하지 않았다 — 서버 PostSummaryView 가
작성 시각도 작성자 표시 이름도 보내지 않는다(백엔드 계약 변경 필요).

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
git diff origin/develop HEAD --name-only
```

- [ ] **Step 11: 기준선 영향과 후속 과제를 기록한다**

`baseline-impact.md` 에 추가:

```markdown
- `/community` 목록 3종 — 카드 나열 → 표(칼럼·구분선). **P3 핸드오프가 예고한 렌더 변화**이고 ET13 커뮤니티 fixture 3종의 visual/a11y baseline 재기록 대상이다.
- browser-ux 시나리오 중 「행이 클릭 대상」을 기대하는 것이 있으면 제목 링크로 고친다(행 제스처는 시맨틱스에서 빠졌다).
- **후속(P4 범위 밖)**: `PostSummaryView` 에 `createdAt`·작성자 표시 이름 추가 — 시안의 「작성」 칼럼과 작성자 이름이 그것 없이는 불가능하다.
```

---

## Task 9: 검색 중 게시판을 바꿔도 검색어를 유지한다

P3 가 `DpPageHeader.titleMenu` 를 없애면서 `onSelectBoard` 가 죽은 코드가 됐고, 셸 이동은 원래도 `q` 를 떨궜다. 복원 지점은 **셸의 `onSelect`** 다 — 커뮤니티 하위 목적지로 이동할 때 현재 `q` 를 들고 간다.

skip 상태로 계약을 들고 있는 테스트가 `apps/web/test/features/community/community_home_page_test.dart:394`(`skip: true`, 본문에 `fail('S3-P4 에서 구현한다')`)에 있다.

**Files:**
- Modify: `apps/web/lib/src/features/shell/presentation/app_shell.dart`
- Modify: `apps/web/test/features/community/community_home_page_test.dart`
- Test: `apps/web/test/features/shell/app_shell_view_test.dart`
- Test: `apps/web/test/features/shell/community_query_carry_test.dart` (신규)

**Interfaces:**
- Produces: `String carryCommunityQuery({required String location, required String targetId})` — 최상위 순수 함수. `location` 과 `targetId` 가 **둘 다** 커뮤니티 게시판 경로이고 `location` 에 `q` 가 있으면 `targetId` 에 그 `q` 를 붙여 돌려준다. 그 밖에는 `targetId` 를 그대로 돌려준다.

- [ ] **Step 1: 순수 함수 실패 테스트를 쓴다**

`apps/web/test/features/shell/community_query_carry_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:web/src/features/shell/presentation/app_shell.dart';

void main() {
  test('게시판 사이 이동은 q 를 들고 간다', () {
    expect(
      carryCommunityQuery(
        location: '/community?board=FREE&q=stream',
        targetId: '/community?board=QNA',
      ),
      '/community?board=QNA&q=stream',
    );
  });

  test('q 가 없으면 목적지를 그대로 쓴다', () {
    expect(
      carryCommunityQuery(
        location: '/community?board=FREE',
        targetId: '/community?board=QNA',
      ),
      '/community?board=QNA',
    );
  });

  test('커뮤니티 밖으로 나가면 q 를 버린다', () {
    expect(
      carryCommunityQuery(
        location: '/community?board=FREE&q=stream',
        targetId: '/path',
      ),
      '/path',
    );
  });

  test('커뮤니티 밖에서 들어올 때는 q 가 없다', () {
    expect(
      carryCommunityQuery(
        location: '/path',
        targetId: '/community?board=QNA',
      ),
      '/community?board=QNA',
    );
  });

  test('상세 화면에서 목록으로 갈 때도 q 를 들고 가지 않는다', () {
    // 상세(`/community/1`)에는 q 가 없으므로 붙일 것이 없다.
    expect(
      carryCommunityQuery(
        location: '/community/1',
        targetId: '/community?board=QNA',
      ),
      '/community?board=QNA',
    );
  });

  test('목적지에 이미 q 가 있으면 덮어쓰지 않는다', () {
    expect(
      carryCommunityQuery(
        location: '/community?board=FREE&q=stream',
        targetId: '/community?board=QNA&q=future',
      ),
      '/community?board=QNA&q=future',
    );
  });
}
```

- [ ] **Step 2: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/shell/community_query_carry_test.dart`

Expected: FAIL — `carryCommunityQuery` 가 없다.

- [ ] **Step 3: 함수를 만든다**

`apps/web/lib/src/features/shell/presentation/app_shell.dart` 의 최상위에 추가한다(`breadcrumbFor` 근처):

```dart
/// 셸 목적지로 이동할 때 커뮤니티 검색어를 이어 간다.
///
/// 게시판 이동은 셸의 몫이고(S3-P2), 셸의 목적지 id 는 `/community?board=QNA`
/// 처럼 **정적**이라 현재 검색어가 떨어진다. 검색 중에 게시판만 바꾸는 것은
/// 「이 낱말을 저 게시판에서 찾아 달라」는 뜻이므로 `q` 를 들고 간다.
///
/// 게시판 목록 경로끼리의 이동에서만 이어 간다 — 상세(`/community/1`)나 작성
/// 화면에는 `q` 가 없고, 커뮤니티 밖으로 나가면 검색 맥락이 끝난다.
String carryCommunityQuery({
  required String location,
  required String targetId,
}) {
  final from = Uri.parse(location);
  final to = Uri.parse(targetId);
  if (from.path != '/community' || to.path != '/community') return targetId;
  if (to.queryParameters.containsKey('q')) return targetId;
  final q = from.queryParameters['q'];
  if (q == null || q.isEmpty) return targetId;
  return Uri(
    path: to.path,
    queryParameters: {...to.queryParameters, 'q': q},
  ).toString();
}
```

- [ ] **Step 4: 테스트를 돌려 green 을 확인한다**

Run: `cd apps/web && flutter test test/features/shell/community_query_carry_test.dart`

Expected: PASS 6/6.

- [ ] **Step 5: 셸 배선에 끼운다**

`AppShellView.build` 의 `DpWebShell(onSelect: …)` 를 바꾼다:

```dart
      onSelect: (id) =>
          onSelect?.call(carryCommunityQuery(location: location, targetId: id)),
```

`AppShell` 의 `DpCommandPalette` 명령(`onInvoke: () => context.go(destination.id)`)도 같게 한다:

```dart
              onInvoke: () => context.go(
                carryCommunityQuery(
                  location: location,
                  targetId: destination.id,
                ),
              ),
```

- [ ] **Step 6: skip 테스트를 켠다**

`apps/web/test/features/community/community_home_page_test.dart:388~394` 의 테스트에서 `fail('S3-P4 에서 구현한다')` 줄과 그 위 주석을 지우고, `skip: true` 를 **없앤다.** 본문은 그 테스트가 원래 단언하려던 것(게시판을 바꿔도 검색어가 남는다)을 셸 경유로 확인하게 쓴다:

```dart
  testWidgets('게시판을 바꿔도 검색어가 유지된다', (tester) async {
    await tester.pumpWidget(_appAt('/community?board=FREE&q=stream'));
    await tester.pumpAndSettle();

    // 셸 헤더의 커뮤니티 하위 목적지로 이동한다.
    await tester.tap(find.text('커뮤니티'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Q/A'));
    await tester.pumpAndSettle();

    expect(find.text('stream'), findsOneWidget); // 검색 입력에 남아 있다
  });
```

`_appAt` 은 그 파일의 기존 라우터 헬퍼를 쓴다. 헬퍼가 셸을 띄우지 않으면 **셸을 포함하는 헬퍼로 바꾼다** — 이 계약은 셸이 이행하므로 셸 없이 검증할 수 없다.

- [ ] **Step 7: 테스트를 돌린다**

Run: `cd apps/web && flutter test test/features/community/community_home_page_test.dart test/features/shell`

Expected: PASS. 켠 테스트가 실패하면 원인을 좁힌다 — ① 셸 헤더 메뉴 탭이 안 열리는가 ② `q` 가 URL 에 실렸는데 `CommunityHomePage.initialQuery` 로 전달되지 않는가(라우터 배선). ②면 `app_router` 의 `/community` 라우트가 `q` 를 읽는지 확인한다.

- [ ] **Step 8: 커밋한다**

```bash
dart format apps/web/lib/src/features/shell/presentation/app_shell.dart
git add apps/web/lib/src/features/shell apps/web/test/features/shell apps/web/test/features/community/community_home_page_test.dart
git commit -F - <<'MSG'
fix(web): 검색 중 게시판을 바꿔도 검색어를 유지한다

셸의 목적지 id 가 정적(`/community?board=QNA`)이라 이동할 때 q 가 떨어졌다.
carryCommunityQuery 로 게시판 목록끼리의 이동에서만 q 를 이어 간다.

P3 가 skip 으로 남겨 둔 계약 테스트를 켰다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
```

---

## Task 10: 글 상세·질문 상세 — `.narrow` / `.cols` + `Card(` 제거

**시안 `post`·`detail`.** 글 상세는 `.narrow`(760) 한 열, 질문 상세는 `.cols`(본문 | 「관련 질문」 사이드)다. 두 화면의 `Card(` 를 `DpPanel` 로 바꾼다.

**Files:**
- Modify: `apps/web/lib/src/features/community/presentation/post_detail_page.dart`
- Modify: `apps/web/lib/src/features/community/presentation/qna_detail_page.dart`
- Modify: `apps/web/lib/src/features/community/presentation/lcs_context.dart`
- Modify: `apps/web/lib/src/features/community/presentation/widgets/content_tombstone.dart`
- Test: `apps/web/test/features/community/post_detail_page_test.dart`
- Test: `apps/web/test/features/community/qna_detail_page_test.dart`
- Test: `apps/web/test/features/community/inline_edit_test.dart` · `inline_edit_stale_body_test.dart` · `edit_delete_golden_path_test.dart`
- Test: `apps/web/test/features/community/qna_related_questions_test.dart` (신규)

**Interfaces:**
- Consumes: `DpPanel`·`DpPanelTitle`·`DpCols`·`DpSide`·`DpListLines`·`DpLink`·`DpMaxWidth` — Task 1.
- Produces: `QnaRelatedPanel({required int questionId, required String title, Key? key})` — `similarQuestionsProvider` 로 관련 질문을 조회해 `DpListLines` 로 그린다. 자기 자신(`questionId`)은 목록에서 뺀다.

### 판정 (Ruling)

| 기존 요소 | 처리 | 근거 |
|---|---|---|
| `_CommentCard`·`_AnswerCard` 의 `Card(` | **`DpPanel` 로 교체** | 시안 `.ans` 는 카드가 아니라 **상단 구분선을 가진 블록**이다. 다만 카드 안에 인라인 수정(`TextField`)이 들어 있어 면 구분이 필요하므로 `DpPanel` 로 간다 — 구분선만 두면 수정 중인 답변의 경계가 사라진다. |
| `lcs_context.dart` 의 `Card(` 2곳 | **`DpPanel` 로 교체** | 같은 이유. |
| `content_tombstone.dart` 의 `Card(` | **`DpPanel` 로 교체** | 삭제된 글의 비석이다. |
| `_VoteBar` | **보존** — 위치 그대로 | 시안 `.ph` 우측의 「▲ 추천 5」 버튼에 대응한다. |
| `ContentMenuButton`(⋯) | **보존** | 시안 `.ph` 의 `⋯` 에 대응한다. |
| `LcsAnswererPanel` | **보존** | 시안에 없지만 LCS 기능이다. 지우지 않는다. |
| `DpMarkdown` 본문 | **폭 제약 추가** — `.prose` 760 | 시안 `.prose{max-width:760px}`. 글 상세는 화면 전체가 `.narrow` 라 자동으로 760 이다. |
| `Divider(height: DpSpacing.xl)` + 「답변 N」 제목 | **`DpPanel` 제목으로 올림** | 시안 `.sec>h3`. |
| 시안 「관련 질문」 (`detail` 사이드) | **구현** — `QnaRelatedPanel` | `similarQuestionsProvider`(`GET /community/questions/similar?q=`)가 **이미 있고** 작성 화면이 쓰고 있다. 새 엔드포인트가 아니다. ★대가: 질문 상세를 열 때 요청이 하나 늘어난다. 시안이 명시한 요소이고 사용자 결정이 「전부 구현」이라 받아들인다.★ |
| 시안 「이 주제 학습하기」 (`detail` 사이드) | **구현하지 않음** | 질문의 태그를 학습 콘텐츠에 잇는 데이터·엔드포인트가 없다. 만들려면 백엔드 계약 변경이다. `baseline-impact.md` 에 후속으로 적는다. |

- [ ] **Step 1: 기준선과 `Card(` 위치를 확인한다**

Run:

```bash
git grep -n "Card(" -- apps/web/lib/src/features/community
cd apps/web && flutter test test/features/community/post_detail_page_test.dart test/features/community/qna_detail_page_test.dart 2>&1 | tail -5
```

Expected: `Card(` 가 `lcs_context.dart`(2) · `content_tombstone.dart`(1) · `question_create_page.dart`(1) · `qna_detail_page.dart`(1) · `post_detail_page.dart`(1) 에 있다. `question_create_page.dart` 는 Task 11 에서 다룬다.

- [ ] **Step 2: 글 상세를 `.narrow` 로 좁히는 실패 테스트를 쓴다**

`apps/web/test/features/community/post_detail_page_test.dart` 에 추가:

```dart
  testWidgets('글 상세: 본문이 readableMaxWidth(760) 를 넘지 않는다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(1280, 900)));
    await tester.pumpAndSettle();

    final body = tester.getSize(find.byType(DpMarkdown));
    expect(body.width, lessThanOrEqualTo(760));
  });

  testWidgets('글 상세: Material Card 를 쓰지 않는다', (tester) async {
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();
    expect(find.byType(Card), findsNothing);
  });
```

- [ ] **Step 3: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/community/post_detail_page_test.dart --plain-name "760"`

Expected: FAIL — 본문이 셸 폭(1120)까지 퍼진다.

- [ ] **Step 4: 글 상세를 `.narrow` 로 감싸고 `Card(` 를 없앤다**

`post_detail_page.dart` 의 `_Loaded.build` 에서 `SliverPadding(padding: const EdgeInsets.all(DpSpacing.lg), sliver: SliverList.list(children: [...]))` 를 아래로 바꾼다:

```dart
    // 시안 `post` 는 `.narrow{max-width:760px}` 한 열이다. 좌우 패딩은 셸이 준다.
    return SliverPadding(
      padding: const EdgeInsets.symmetric(vertical: DpSpacing.lg),
      sliver: SliverToBoxAdapter(
        child: DpMaxWidth(
          maxWidth: context.appTokens.readableMaxWidth,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              /* 기존 children 을 그대로 옮긴다 */
            ],
          ),
        ),
      ),
    );
```

`DpMaxWidth` 는 `Align(topCenter)` 로 중앙 정렬한다 — 시안 `post` 의 `.narrow{margin-inline:0}`(좌측 정렬)과 다르다. 시안을 따르려면 `DpMaxWidth` 대신 `ConstrainedBox` + `Align(centerLeft)` 이 맞다:

```dart
        child: Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            constraints: BoxConstraints(
              maxWidth: context.appTokens.readableMaxWidth,
            ),
            child: Column(/* … */),
          ),
        ),
```

`_CommentCard.build` 의 `Card(` 를 바꾼다:

```dart
    return DpPanel(
      padding: const EdgeInsets.all(DpSpacing.lg),
      child: /* 기존 Card 의 child (Padding 한 겹은 없앤다) */,
    );
```

「댓글 N」 제목과 그 아래 목록은 `DpPanel(title: DpPanelTitle('댓글 ${detail.comments.length}'), child: DpListLines(children: [...]))` 로 묶는다 — 단 **인라인 수정이 열리는 댓글은 면이 필요하므로** 댓글 하나하나를 `DpPanel` 로 두는 현재 모양을 유지하고, 제목만 `Text` 로 남긴다. 둘 중 하나를 골라 그 근거를 커밋 메시지에 적는다.

- [ ] **Step 5: 테스트를 돌려 green 을 확인한다**

Run: `cd apps/web && flutter test test/features/community/post_detail_page_test.dart test/features/community/inline_edit_test.dart test/features/community/inline_edit_stale_body_test.dart`

Expected: PASS. `Card` 를 찾던 단언은 `DpPanel` 로 바꾼다.

- [ ] **Step 6: 「관련 질문」 패널 실패 테스트를 쓴다**

`apps/web/test/features/community/qna_related_questions_test.dart`:

```dart
import 'package:dp_core/dp_core.dart';
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:web/src/features/community/data/community_source.dart';
import 'package:web/src/features/community/presentation/qna_related_panel.dart';

void main() {
  testWidgets('QnaRelatedPanel: 관련 질문을 목록으로 그리고 자기 자신은 뺀다', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          similarQuestionsProvider.overrideWithValue(
            (q) async => const [
              SimilarQuestion(id: 1, title: '자기 자신'),
              SimilarQuestion(id: 2, title: 'Stream 구독 해제는?'),
            ],
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: QnaRelatedPanel(questionId: 1, title: 'async/await가 헷갈려요'),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('관련 질문'), findsOneWidget);
    expect(find.text('Stream 구독 해제는?'), findsOneWidget);
    expect(find.text('자기 자신'), findsNothing);
  });

  testWidgets('QnaRelatedPanel: 조회가 실패하면 조용히 사라진다', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          similarQuestionsProvider.overrideWithValue(
            (q) async => throw Exception('boom'),
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: QnaRelatedPanel(questionId: 1, title: '제목'),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // 보조 정보다 — 실패가 본문 읽기를 막지 않는다.
    expect(find.text('관련 질문'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
```

`SimilarQuestion` 의 실제 필드는 `packages/dp_core` 또는 `community_source.dart` 에서 확인해 맞춘다. `similarQuestionsProvider` 가 `Provider<SimilarQuestionsFetch>` 이므로 `overrideWithValue` 가 맞다.

- [ ] **Step 7: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/community/qna_related_questions_test.dart`

Expected: FAIL — `qna_related_panel.dart` 가 없다.

- [ ] **Step 8: `QnaRelatedPanel` 을 만든다**

`apps/web/lib/src/features/community/presentation/qna_related_panel.dart`:

```dart
import 'package:dp_core/dp_core.dart';
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../data/community_source.dart';

/// 시안 `detail` 의 `.side` 「관련 질문」.
///
/// 작성 화면이 이미 쓰는 `similarQuestionsProvider`(`GET
/// /community/questions/similar?q=`)를 질문 제목으로 부른다 — 새 엔드포인트가
/// 아니다. 대가는 질문 상세를 열 때 요청이 하나 늘어나는 것이고, 보조 정보이므로
/// **실패하면 조용히 사라진다**(본문 읽기를 막지 않는다).
class QnaRelatedPanel extends ConsumerStatefulWidget {
  const QnaRelatedPanel({
    super.key,
    required this.questionId,
    required this.title,
  });

  final int questionId;
  final String title;

  @override
  ConsumerState<QnaRelatedPanel> createState() => _QnaRelatedPanelState();
}

class _QnaRelatedPanelState extends ConsumerState<QnaRelatedPanel> {
  List<SimilarQuestion> _items = const [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  @override
  void didUpdateWidget(covariant QnaRelatedPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.questionId != widget.questionId) {
      setState(() => _items = const []);
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final results = await ref.read(similarQuestionsProvider)(widget.title);
      if (!mounted) return;
      setState(() {
        _items = results
            .where((item) => item.id != widget.questionId)
            .toList(growable: false);
      });
    } catch (_) {
      if (mounted) setState(() => _items = const []);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_items.isEmpty) return const SizedBox.shrink();
    return DpPanel(
      title: const DpPanelTitle('관련 질문'),
      child: DpListLines(
        children: [
          for (final item in _items)
            DpLink.inline(
              text: item.title,
              onTap: () => context.go('/community/${item.id}'),
            ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 9: 테스트를 돌려 green 을 확인한다**

Run: `cd apps/web && flutter test test/features/community/qna_related_questions_test.dart`

Expected: PASS 2/2.

- [ ] **Step 10: 질문 상세를 `.cols` 로 바꾸는 실패 테스트를 쓴다**

```dart
  testWidgets('질문 상세: .cols 2열(본문 | 관련 질문)을 그린다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(1280, 900)));
    await tester.pumpAndSettle();

    expect(find.byType(DpCols), findsOneWidget);
    expect(find.byType(Card), findsNothing);
  });
```

- [ ] **Step 11: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/community/qna_detail_page_test.dart --plain-name ".cols 2열"`

Expected: FAIL.

- [ ] **Step 12: 질문 상세를 `.cols` 로 다시 짠다**

`qna_detail_page.dart` 의 `_Loaded.build` 에서 반환을 아래로 바꾼다. 기존 `children` 은 `article` 로 옮긴다.

```dart
    return SliverPadding(
      padding: const EdgeInsets.symmetric(vertical: DpSpacing.lg),
      sliver: SliverToBoxAdapter(
        child: DpCols(
          main: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              /* 기존 children 전부 — 제목 Row·_VoteBar·DpMarkdown·
                 LcsAnswererPanel·태그·답변 목록·_AnswerComposer */
            ],
          ),
          side: DpSide(
            children: [
              QnaRelatedPanel(questionId: detail.id, title: detail.title),
            ],
          ),
        ),
      ),
    );
```

`_AnswerCard.build` 의 `Card(` 를 `DpPanel(padding: const EdgeInsets.all(DpSpacing.lg), child: …)` 로 바꾼다. `Divider(height: DpSpacing.xl)` + 「답변 N」 `Text` 는 그대로 두거나 `DpPanel` 제목으로 올린다 — 선택과 근거를 커밋 메시지에 적는다.

`QnaRelatedPanel` 이 `_items.isEmpty` 면 `SizedBox.shrink()` 라 사이드가 빈칸이 될 수 있다. 2열에서 빈 사이드는 본문을 2/3 로 좁히기만 한다 — 시안도 사이드가 비는 경우를 다루지 않는다. **관련 질문이 없으면 1열로 두는 편이 낫다**: `DpCols` 를 쓰기 전에 `QnaRelatedPanel` 이 내용을 가졌는지 알 수 없으므로, 패널이 스스로 「관련 질문 없음」을 말하지 않는 대신 **사이드에 「이 질문의 태그」 패널을 함께 둔다** — 태그는 항상 있다:

```dart
          side: DpSide(
            children: [
              QnaRelatedPanel(questionId: detail.id, title: detail.title),
              if (detail.tags.isNotEmpty)
                DpPanel(
                  title: const DpPanelTitle('태그'),
                  padding: const EdgeInsets.all(DpSpacing.lg),
                  child: Wrap(
                    spacing: DpSpacing.xs,
                    runSpacing: DpSpacing.xs,
                    children: [for (final t in detail.tags) DpTag(label: '#$t')],
                  ),
                ),
            ],
          ),
```

그러면 본문의 태그 `Wrap` 은 **사이드로 옮겨진 것**이므로 본문에서 지운다(같은 태그를 두 번 그리지 않는다).

- [ ] **Step 13: `lcs_context.dart`·`content_tombstone.dart` 의 `Card(` 를 바꾼다**

각 `Card(child: Padding(padding: …, child: X))` 를 `DpPanel(padding: …, child: X)` 로 바꾼다. `Card` 의 `margin` 이 있었으면 바깥 `Padding` 으로 옮긴다(`DpPanel` 은 margin 을 갖지 않는다).

- [ ] **Step 14: 커뮤니티 테스트 전체를 돌린다**

Run: `cd apps/web && flutter test test/features/community`

Expected: PASS. `Card` 를 찾던 단언을 전부 `DpPanel` 로 바꾼다.

- [ ] **Step 15: 390px 와 상태 분기를 확인한다 (Review Focus 1·5)**

```dart
  testWidgets('질문 상세: 390px 에서 본문 → 사이드 한 열이 된다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(390, 900)));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('질문 상세: 조회 실패 시 다시 시도할 수 있다', (tester) async {
    await tester.pumpWidget(_app(phase: /* 실패 상태 */));
    await tester.pumpAndSettle();
    expect(find.byType(SupportableError), findsOneWidget);
  });
```

- [ ] **Step 16: analyze·format 하고 커밋한다**

```bash
cd apps/web && flutter analyze lib/src/features/community
cd ../.. && dart format apps/web/lib/src/features/community/presentation/post_detail_page.dart apps/web/lib/src/features/community/presentation/qna_detail_page.dart apps/web/lib/src/features/community/presentation/qna_related_panel.dart apps/web/lib/src/features/community/presentation/lcs_context.dart apps/web/lib/src/features/community/presentation/widgets/content_tombstone.dart
git add apps/web/lib/src/features/community apps/web/test/features/community
git commit -F - <<'MSG'
feat(web): 글 상세를 .narrow 760, 질문 상세를 .cols 로 — Card 5곳 제거

- 글 상세: 본문 폭을 readableMaxWidth(760) 로 좁혔다(시안 .narrow)
- 질문 상세: .cols(본문 | 관련 질문·태그 사이드), 태그를 사이드로 옮겼다
- 「관련 질문」 신설 — 기존 similarQuestionsProvider 를 제목으로 부른다
  (요청이 하나 늘어난다. 보조 정보라 실패하면 조용히 사라진다)
- Card( → DpPanel: 댓글·답변·lcs_context 2곳·content_tombstone

시안 「이 주제 학습하기」는 구현하지 않았다 — 질문 태그를 학습 콘텐츠에 잇는
데이터가 없다(백엔드 계약 변경 필요).

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
git diff origin/develop HEAD --name-only
```

- [ ] **Step 17: 기준선 영향을 기록한다**

```markdown
- `/community/post/:id` 글 상세 — 본문 폭 1120 → 760, 댓글 `Card` → `DpPanel`(그림자 제거).
- `/community/:id` 질문 상세 — `.cols` 2열, 태그가 본문 → 사이드, 「관련 질문」 패널 신설.
- **후속(P4 범위 밖)**: 시안 「이 주제 학습하기」 — 질문 태그 ↔ 학습 콘텐츠 매핑 엔드포인트가 없다.
```

---

## Task 11: 작성·수정 4화면 — `.narrow` + `.form` 문법

**시안 `write`(질문 작성)** 과 그 파생 3화면(자유글 작성·글 수정·질문 수정). 네 화면 모두 `.narrow`(760) 한 열 + `.form` 문법이다.

**Files:**
- Modify: `apps/web/lib/src/features/community/presentation/question_create_page.dart`
- Modify: `apps/web/lib/src/features/community/presentation/post_create_page.dart`
- Modify: `apps/web/lib/src/features/community/presentation/post_edit_page.dart`
- Modify: `apps/web/lib/src/features/community/presentation/question_edit_page.dart`
- Test: `apps/web/test/features/community/question_create_page_test.dart`
- Test: `apps/web/test/features/community/post_create_page_test.dart`
- Test: `apps/web/test/features/community/post_edit_test.dart`
- Test: `apps/web/test/features/community/question_edit_test.dart`

**Interfaces:**
- Consumes: `DpPanel`·`DpPanelTitle` — Task 1. `AppTokens.readableMaxWidth` — 기존.
- Produces: 새 공개 API 없음. 네 화면의 `Scaffold`/`CustomScrollView` 구조는 그대로다.

### 시안 파생 근거 (Global Constraints 의 파생 규칙)

| 화면 | 시안 근거 | 파생 규칙 |
|---|---|---|
| 질문 작성 | 시안 `write` 그대로 | `.narrow` + `.fld`(제목·태그·본문) + 하단 `.acts`(질문 등록·취소·임시 저장 안내) |
| 자유글 작성 | 시안 `write` 파생 | 같은 문법. **태그 `.fld` 가 없다**(자유글에 태그 입력이 없다 — 실측으로 확인해 이 표를 갱신한다). 제출 라벨은 「글 등록」. |
| 글 수정 | 시안 `write` 파생 | 같은 문법. 제출 라벨 「수정 저장」. 헤더 제목 「글 수정」. |
| 질문 수정 | 시안 `write` 파생 | 같은 문법. 제출 라벨 「수정 저장」. 헤더 제목 「질문 수정」. |

- [ ] **Step 1: 네 화면의 현재 구조와 기준선을 확인한다**

Run:

```bash
git grep -n "SliverPadding\|EdgeInsets.all(DpSpacing" -- apps/web/lib/src/features/community/presentation/question_create_page.dart apps/web/lib/src/features/community/presentation/post_create_page.dart apps/web/lib/src/features/community/presentation/post_edit_page.dart apps/web/lib/src/features/community/presentation/question_edit_page.dart
cd apps/web && flutter test test/features/community/question_create_page_test.dart test/features/community/post_create_page_test.dart test/features/community/post_edit_test.dart test/features/community/question_edit_test.dart 2>&1 | tail -5
```

Expected: 각 화면의 `SliverPadding` 위치와 현재 통과 개수를 기록한다. 수정 화면 둘(`post_edit_page`·`question_edit_page`)이 작성 화면의 폼을 재사용하는지도 확인한다 — 재사용하면 그 한 곳만 고치면 넷이 함께 바뀐다.

- [ ] **Step 2: 폼 폭 실패 테스트를 쓴다 (네 화면 각각)**

각 테스트 파일에 같은 모양으로 추가한다. 질문 작성:

```dart
  testWidgets('질문 작성: 폼 폭이 readableMaxWidth(760) 를 넘지 않는다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(1280, 900)));
    await tester.pumpAndSettle();

    final title = tester.getSize(find.byKey(const ValueKey('question-title-field')));
    expect(title.width, lessThanOrEqualTo(760));
  });

  testWidgets('질문 작성: Material Card 를 쓰지 않는다', (tester) async {
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();
    expect(find.byType(Card), findsNothing);
  });
```

키 이름은 그 화면의 실제 `ValueKey` 로 맞춘다(없으면 `find.byType(TextField).first` 로 잡는다).

자유글 작성·글 수정·질문 수정도 같은 두 테스트를 각각 쓴다(문구의 화면 이름만 바꾼다).

- [ ] **Step 3: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/community/question_create_page_test.dart --plain-name "760"`

Expected: FAIL — 폼이 셸 폭(1120)까지 퍼진다.

- [ ] **Step 4: 질문 작성 화면을 `.narrow` 로 감싼다**

`question_create_page.dart` 의 `build` 에서 각 `SliverPadding(padding: const EdgeInsets.all(DpSpacing.lg), …)` 의 좌우를 없애고, sliver 들을 감싸는 공통 폭 제약을 넣는다. sliver 는 `ConstrainedBox` 로 감쌀 수 없으므로 `SliverCrossAxisGroup` 대신 **각 sliver 를 `SliverConstrainedCrossAxis` 로 감싼다**:

```dart
    // 시안 `write` 는 `.narrow{max-width:760px;margin-inline:0}` 한 열이다.
    // 좌우 패딩은 셸이 준다. sliver 목록이라 폭 제약을 sliver 로 준다.
    Widget narrow(Widget sliver) => SliverConstrainedCrossAxis(
      maxExtent: context.appTokens.readableMaxWidth,
      sliver: sliver,
    );
```

그리고 각 sliver 를 `narrow(...)` 로 감싼다:

```dart
        slivers: [
          narrow(
            const SliverToBoxAdapter(
              child: DpPageHeader(
                title: '질문하기',
                description: '무엇을 시도했고 어디서 막혔는지 적으면 답변이 빨라져요',
              ),
            ),
          ),
          narrow(
            SliverPadding(
              padding: const EdgeInsets.symmetric(vertical: DpSpacing.md),
              sliver: SliverList.list(children: [/* 제목·태그 필드 */]),
            ),
          ),
          narrow(
            SliverPadding(
              padding: const EdgeInsets.only(top: DpSpacing.md),
              sliver: SliverPersistentHeader(
                pinned: true,
                delegate: DpRichEditorToolbarHeader(controller: _bodyController),
              ),
            ),
          ),
          narrow(
            SliverToBoxAdapter(
              child: DpRichEditorBody(controller: _bodyController),
            ),
          ),
          narrow(
            SliverPadding(
              padding: const EdgeInsets.symmetric(vertical: DpSpacing.md),
              sliver: SliverList.list(children: [/* 유사질문·LCS·제출 */]),
            ),
          ),
        ],
```

`SliverConstrainedCrossAxis` 는 **좌측 정렬**로 폭을 자른다 — 시안 `.narrow{margin-inline:0}` 과 같다.

`Card(` 한 곳(유사질문 안내)을 `DpPanel` 로 바꾼다:

```dart
                  DpPanel(
                    padding: const EdgeInsets.all(DpSpacing.md),
                    child: /* 기존 Card > Padding 의 child */,
                  ),
```

- [ ] **Step 5: 테스트를 돌려 green 을 확인한다**

Run: `cd apps/web && flutter test test/features/community/question_create_page_test.dart`

Expected: PASS. `SliverConstrainedCrossAxis` 가 없는 Flutter 버전이면(3.44 에는 있다) `SliverCrossAxisGroup` + `SliverConstrainedCrossAxis` 조합을 확인한다.

- [ ] **Step 6: 자유글 작성 화면도 같게 한다**

`post_create_page.dart` 의 `build` 에 같은 `narrow` 헬퍼를 넣고 sliver 다섯을 감싼다. 이 화면은 태그 필드가 없으므로 sliver 가 하나 적다. 좌우 패딩(`EdgeInsets.all(DpSpacing.lg)`)을 `EdgeInsets.symmetric(vertical: …)` 로 바꾼다.

Run: `cd apps/web && flutter test test/features/community/post_create_page_test.dart`

Expected: PASS.

- [ ] **Step 7: 수정 화면 둘을 같게 한다**

`post_edit_page.dart`·`question_edit_page.dart` 는 상태별 `Scaffold` 를 돌려주고 로드된 뒤 폼을 그린다. Step 1 의 실측에 따라:

- **작성 화면의 폼을 재사용한다면**: Step 4·6 의 변경이 이미 반영됐다. 로딩·실패 `Scaffold` 의 `Center(child: CircularProgressIndicator())` 를 `DpLoading()` 으로 바꾸고(레포의 표준 로딩), 실패는 `SupportableError` 를 쓰는지 확인한다.
- **자체 폼을 갖는다면**: Step 4 와 같은 `narrow` 헬퍼를 각 파일에 넣고 sliver 를 감싼다.

Run: `cd apps/web && flutter test test/features/community/post_edit_test.dart test/features/community/question_edit_test.dart`

Expected: PASS.

- [ ] **Step 8: 390px 를 확인한다 (Review Focus 1)**

```dart
  testWidgets('질문 작성: 390px 에서 폼이 가로로 넘치지 않는다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(390, 900)));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
```

네 화면에 각각 쓴다.

- [ ] **Step 9: analyze·format 하고 커밋한다**

```bash
cd apps/web && flutter analyze lib/src/features/community
cd ../.. && dart format apps/web/lib/src/features/community/presentation/question_create_page.dart apps/web/lib/src/features/community/presentation/post_create_page.dart apps/web/lib/src/features/community/presentation/post_edit_page.dart apps/web/lib/src/features/community/presentation/question_edit_page.dart
git add apps/web/lib/src/features/community apps/web/test/features/community
git commit -F - <<'MSG'
feat(web): 작성·수정 4화면을 시안 .narrow 760 + .form 으로

시안에 없는 3화면(자유글 작성·글 수정·질문 수정)은 시안 write 에서 파생했다
— 같은 .narrow + .fld 문법, 제출 라벨만 다르다.

- SliverConstrainedCrossAxis 로 폼 폭을 760 좌측 정렬
- 화면의 좌우 패딩 제거 — 셸이 준다
- 유사질문 안내 Card( → DpPanel

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
git diff origin/develop HEAD --name-only
```

- [ ] **Step 10: 기준선 영향을 기록한다**

```markdown
- 커뮤니티 작성·수정 4화면 — 폼 폭 1120 → 760(좌측 정렬), 유사질문 `Card` → `DpPanel`.
```

---

## Task 12: PR-B 마무리 — 전 패키지 검증과 PR

**Files:** 코드 변경 없음.

- [ ] **Step 1: 변경 파일 목록을 확인한다**

Run: `git diff origin/develop HEAD --name-only`

Expected: `apps/web/lib/src/features/{community,shell}/**` · `apps/web/test/**` 만. `analysis_options.yaml`·`pubspec.lock` 이 있으면 그 파일만 되돌리고 즉시 amend.

- [ ] **Step 2: analyze·format·전 패키지 테스트**

Run:

```bash
cd apps/web && flutter analyze
cd ../.. && dart format --output=none --set-exit-if-changed $(git diff origin/develop HEAD --name-only -- '*.dart')
cd packages/dp_core && flutter test
cd ../dp_design && flutter test
cd ../../apps/web && flutter test
cd ../admin && flutter test
```

Expected: analyze 0 · format exit 0 · 전 패키지 PASS.

- [ ] **Step 3: PR 을 올린다**

```bash
git push -u origin feat/s3-p4-community-screens
gh pr create --base develop --title "feat(web): S3-P4b 커뮤니티 화면군을 시안 웹 문법으로 재구성" --body-file - <<'BODY'
## 무엇

S3-P4 의 두 번째 PR. 커뮤니티 9화면(목록 3·상세 2·작성·수정 4)을 시안의 웹 문법으로 재구성하고, P3 가 이월한 행동 결함 2건을 닫는다.

## 어떻게

- 목록 3종: `DpListRow` 카드 나열 → `DpWebTable`. 게시판별 칼럼(Q/A 는 「상태」 칼럼), compact 는 답변 칼럼을 감춘다. 해결 배지 → `DpStatusText`
- **검색어 유지 복원**: 셸의 목적지 id 가 정적이라 게시판을 바꾸면 `q` 가 떨어졌다. `carryCommunityQuery` 로 게시판 목록끼리의 이동에서만 이어 간다. P3 가 `skip` 으로 남긴 계약 테스트를 켰다
- **빈 상태의 중복 액션 제거**: 헤더 작성 버튼과 접근명이 같아 스크린리더로 구분할 수 없었다
- 글 상세 `.narrow` 760 · 질문 상세 `.cols`(본문 | 관련 질문·태그) · 작성·수정 4화면 `.narrow` 760
- `Card(` 6곳 → `DpPanel`(커뮤니티의 `Card` 를 전부 없앴다)
- 「관련 질문」 신설 — 기존 `similarQuestionsProvider` 사용(새 엔드포인트 아님)

## 구현하지 않은 시안 요소와 근거

- **목록의 「작성」 칼럼·작성자 이름**: 서버 `PostSummaryView` 가 작성 시각도 작성자 표시 이름도 보내지 않는다(`id·boardType·title·authorId·solved·upvoteCount·replyCount·excerpt`). 백엔드 계약 변경이 필요하다
- **질문 상세의 「이 주제 학습하기」**: 질문 태그를 학습 콘텐츠에 잇는 엔드포인트가 없다

## 검증

- analyze 0 · format 0 changed · 전 패키지 테스트 통과
- 390px 가로 넘침 없음(표만 자체 스크롤) · 표 행이 시맨틱스에서 칼럼별로 읽힘

🤖 Generated with [Claude Code](https://claude.com/claude-code)
BODY
```

- [ ] **Step 4: CI 6잡 녹색을 확인한다**

Run: `gh pr checks --watch`

Expected: 전부 pass.

- **`browser-ux` 가 깨지면**: 커뮤니티 시나리오가 「행이 클릭 대상」·「카드 나열」을 기대한다. 시나리오를 제목 링크·표 행 기준으로 고친다. 로컬 재현은 `--only=<시나리오>` 로 약 2분.
- **ET13 `produce-atomic-pair` 가 깨지면**: `WebCommunityBoardProjection` 의 렌더가 바뀌어 카탈로그 계약이 어긋난 것이다. **baseline 을 여기서 재기록하지 않는다** — 계약 테스트가 구조를 단언한다면 그 단언을 고치고, 이미지 baseline 은 P5 사람 승인으로 넘긴다.

- [ ] **Step 5: 녹색을 확인한 뒤 머지한다**

Run: `gh pr merge --merge`

---

# PR-C — 계정·온보딩 (로그인·콜백·동의·베타·진단 3·마이페이지·설정·placeholder)

브랜치: `feat/s3-p4-account-screens` (base: `develop`, PR-B 머지 뒤 분기)

---

## Task 13: dp_design 에 시안 온보딩 프리미티브 3종 신설

시안의 `.steps`(단계 표시)·`.opt`(선택 옵션 행)·`.chk`(체크 행)는 dp_design 에 대응이 없다. `.steps` 는 진단 3화면, `.opt` 는 진단 2화면, `.chk` 는 동의 화면이 쓴다 — 두 화면 이상이 쓰므로 화면 안이 아니라 `dp_design` 에 둔다.

**Files:**
- Create: `packages/dp_design/lib/src/layout/dp_steps.dart`
- Create: `packages/dp_design/lib/src/interaction/dp_option_row.dart`
- Create: `packages/dp_design/lib/src/interaction/dp_check_row.dart`
- Modify: `packages/dp_design/lib/dp_design.dart`
- Create: `packages/dp_design/test/layout/dp_steps_test.dart`
- Create: `packages/dp_design/test/interaction/dp_option_row_test.dart`
- Create: `packages/dp_design/test/interaction/dp_check_row_test.dart`

**Interfaces:**
- Produces:
  - `DpSteps({required List<String> labels, required int currentIndex, Key? key})` — 시안 `.steps{display:flex;border:1px solid;border-radius:6px;overflow:hidden}` + `li[aria-current]{background:var(--soft);color:var(--pstrong);font-weight:600}`. compact 에서 세로로 쌓인다(시안 `@container(max-width:720px){.steps{flex-direction:column}}`).
  - `DpOptionRow({required Widget label, required bool selected, required VoidCallback onSelect, Widget? description, Key? key})` — 시안 `.opt{display:flex;border:1px solid;border-radius:6px}` + `.opt.sel{border-color:var(--primary);background:var(--soft)}`. 라디오 시맨틱스(`inMutuallyExclusiveGroup`)를 갖는다.
  - `DpCheckRow({required Widget label, required bool value, required ValueChanged<bool>? onChanged, Widget? description, Widget? trailing, bool last = false, Key? key})` — 시안 `.chk{display:grid;grid-template-columns:18px 1fr auto;padding:10px 16px;border-bottom:1px solid}`.

- [ ] **Step 1: `DpSteps` 실패 테스트를 쓴다**

`packages/dp_design/test/layout/dp_steps_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host(Widget child, {Size size = const Size(1280, 800)}) => MediaQuery(
  data: MediaQueryData(size: size),
  child: MaterialApp(theme: DpTheme.light(), home: Scaffold(body: child)),
);

void main() {
  testWidgets('DpSteps: 현재 단계를 시맨틱스로 알린다', (tester) async {
    final handle = tester.ensureSemantics();
    await tester.pumpWidget(
      _host(
        const DpSteps(
          labels: ['1 트랙 선택', '2 실력 진단', '3 학습 경로'],
          currentIndex: 1,
        ),
      ),
    );

    expect(find.text('1 트랙 선택'), findsOneWidget);
    expect(find.text('2 실력 진단'), findsOneWidget);
    final node = tester.getSemantics(find.text('2 실력 진단'));
    expect(node.hasFlag(SemanticsFlag.isSelected), isTrue);
    handle.dispose();
  });

  testWidgets('DpSteps: compact 에서 세로로 쌓인다', (tester) async {
    await tester.pumpWidget(
      _host(
        const DpSteps(
          labels: ['1 트랙 선택', '2 실력 진단', '3 학습 경로'],
          currentIndex: 0,
        ),
        size: const Size(390, 800),
      ),
    );

    final first = tester.getRect(find.text('1 트랙 선택'));
    final second = tester.getRect(find.text('2 실력 진단'));
    expect(second.top, greaterThan(first.bottom - 1));
  });
}
```

- [ ] **Step 2: 테스트를 돌려 red 를 확인한다**

Run: `cd packages/dp_design && flutter test test/layout/dp_steps_test.dart`

Expected: FAIL — `DpSteps` 가 없다.

- [ ] **Step 3: `DpSteps` 를 만든다**

`packages/dp_design/lib/src/layout/dp_steps.dart`:

```dart
import 'package:flutter/material.dart';

import '../theme/dp_colors.dart';
import '../theme/dp_spacing.dart';
import 'dp_window_class.dart';

/// 진행 단계 표시(시안 `.steps`) — 테두리 한 겹 안에 단계가 나란히 놓인다.
///
/// 현재 단계는 `soft` 배경 + `primaryTextStrong` + 600 이고, 스크린리더에는
/// `selected` 로 알린다(시안 `li[aria-current="step"]`). compact 에서는 세로로
/// 쌓인다 — 세 단계를 390px 에 나란히 두면 글자가 잘린다.
class DpSteps extends StatelessWidget {
  const DpSteps({
    super.key,
    required this.labels,
    required this.currentIndex,
  });

  final List<String> labels;
  final int currentIndex;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final vertical = context.windowClass == DpWindowClass.compact;

    final items = <Widget>[
      for (var i = 0; i < labels.length; i++)
        _Step(
          label: labels[i],
          current: i == currentIndex,
          // 마지막이 아니면 다음 단계와의 사이에 구분선을 둔다.
          divider: i != labels.length - 1,
          vertical: vertical,
        ),
    ];

    return Container(
      key: const ValueKey('dp-steps'),
      decoration: BoxDecoration(
        color: c.surface,
        border: Border.all(color: c.border),
        borderRadius: BorderRadius.circular(DpRadius.button),
      ),
      clipBehavior: Clip.antiAlias,
      child: vertical
          ? Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: items,
            )
          : Row(
              children: [for (final item in items) Expanded(child: item)],
            ),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({
    required this.label,
    required this.current,
    required this.divider,
    required this.vertical,
  });

  final String label;
  final bool current;
  final bool divider;
  final bool vertical;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    return Container(
      padding: const EdgeInsets.symmetric(
        vertical: DpSpacing.xs,
        horizontal: DpSpacing.md,
      ),
      decoration: BoxDecoration(
        color: current ? c.accentSoft : null,
        border: divider
            ? Border(
                right: vertical
                    ? BorderSide.none
                    : BorderSide(color: c.border),
                bottom: vertical
                    ? BorderSide(color: c.border)
                    : BorderSide.none,
              )
            : null,
      ),
      child: Semantics(
        selected: current,
        child: Text(
          label,
          style: TextStyle(
            color: current ? c.primaryTextStrong : c.textSecondary,
            fontWeight: current ? FontWeight.w600 : FontWeight.w400,
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: 테스트를 돌려 green 을 확인한다**

Run: `cd packages/dp_design && flutter test test/layout/dp_steps_test.dart`

Expected: PASS 2/2.

- [ ] **Step 5: `DpOptionRow` 실패 테스트를 쓴다**

`packages/dp_design/test/interaction/dp_option_row_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host(Widget child) => MaterialApp(
  theme: DpTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  testWidgets('DpOptionRow: 선택 상태를 라디오 시맨틱스로 알린다', (tester) async {
    final handle = tester.ensureSemantics();
    await tester.pumpWidget(
      _host(
        DpOptionRow(
          label: const Text('백엔드 (Spring)'),
          description: const Text('Java · Spring Boot · JPA · 테스트'),
          selected: true,
          onSelect: () {},
        ),
      ),
    );

    final node = tester.getSemantics(find.text('백엔드 (Spring)'));
    expect(node.hasFlag(SemanticsFlag.isInMutuallyExclusiveGroup), isTrue);
    expect(node.hasFlag(SemanticsFlag.isChecked), isTrue);
    handle.dispose();
  });

  testWidgets('DpOptionRow: 행 어디를 눌러도 선택된다', (tester) async {
    var selected = 0;
    await tester.pumpWidget(
      _host(
        DpOptionRow(
          label: const Text('백엔드 (Python)'),
          selected: false,
          onSelect: () => selected++,
        ),
      ),
    );

    await tester.tap(find.text('백엔드 (Python)'));
    await tester.pump();
    expect(selected, 1);
  });
}
```

- [ ] **Step 6: 테스트를 돌려 red 를 확인한다**

Run: `cd packages/dp_design && flutter test test/interaction/dp_option_row_test.dart`

Expected: FAIL — `DpOptionRow` 가 없다.

- [ ] **Step 7: `DpOptionRow` 를 만든다**

`packages/dp_design/lib/src/interaction/dp_option_row.dart`:

```dart
import 'package:flutter/material.dart';

import '../theme/dp_colors.dart';
import '../theme/dp_spacing.dart';

/// 하나만 고르는 선택 행(시안 `.opt` / `.opt.sel`).
///
/// 라디오 버튼만 타깃으로 두지 않고 **행 전체가 타깃**이다(시안도 `label` 이
/// 감싼다). 시맨틱스는 라디오 그룹(`inMutuallyExclusiveGroup` + `checked`)으로
/// 알린다 — `Radio` 를 직접 쓰면 라벨과 노드가 갈라진다.
class DpOptionRow extends StatelessWidget {
  const DpOptionRow({
    super.key,
    required this.label,
    required this.selected,
    required this.onSelect,
    this.description,
  });

  final Widget label;
  final Widget? description;
  final bool selected;
  final VoidCallback onSelect;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final text = Theme.of(context).textTheme;

    return Semantics(
      inMutuallyExclusiveGroup: true,
      checked: selected,
      button: true,
      onTap: onSelect,
      excludeSemantics: true,
      child: InkWell(
        onTap: onSelect,
        borderRadius: BorderRadius.circular(DpRadius.button),
        child: Container(
          padding: const EdgeInsets.symmetric(
            vertical: 10,
            horizontal: DpSpacing.md,
          ),
          decoration: BoxDecoration(
            color: selected ? c.accentSoft : c.surface,
            border: Border.all(color: selected ? c.primary : c.border),
            borderRadius: BorderRadius.circular(DpRadius.button),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                selected
                    ? Icons.radio_button_checked
                    : Icons.radio_button_unchecked,
                size: 18,
                color: selected ? c.primary : c.textSecondary,
              ),
              const SizedBox(width: DpSpacing.sm),
              Expanded(
                child: Column(
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
                    if (description != null) ...[
                      const SizedBox(height: 2),
                      DefaultTextStyle.merge(
                        style: TextStyle(fontSize: 13, color: c.textSecondary),
                        child: description!,
                      ),
                    ],
                  ],
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

`Semantics(excludeSemantics: true)` 로 자식을 가리므로 `find.text(...)` 로 시맨틱스를 잡을 수 없다 — Step 5 의 테스트는 `find.bySemanticsLabel('백엔드 (Spring)')` 로 바꾼다. 라벨이 `Widget` 이라 자동 라벨이 없으므로 `Semantics(label: …)` 에 문자열을 줄 수 없다. **그래서 `excludeSemantics` 를 쓰지 않고** `Semantics(container: true, inMutuallyExclusiveGroup: true, checked: selected, button: true, onTap: onSelect, child: …)` 로 두고, 안쪽 `InkWell` 의 제스처는 `excludeFromSemantics` 로 뺀다:

```dart
    return Semantics(
      container: true,
      inMutuallyExclusiveGroup: true,
      checked: selected,
      button: true,
      onTap: onSelect,
      child: GestureDetector(
        onTap: onSelect,
        // 이 제스처의 노드가 라벨 조각을 흡수하지 않게 뺀다(P3 실측).
        excludeFromSemantics: true,
        child: /* 위 Container 그대로 */,
      ),
    );
```

`InkWell` 을 포기하면 hover·splash 를 잃는다 — 그래서 `MouseRegion(cursor: SystemMouseCursors.click)` 을 함께 둔다.

- [ ] **Step 8: 테스트를 고쳐 green 을 확인한다**

Step 5 의 두 테스트에서 `tester.getSemantics(find.text(...))` 를 그대로 쓸 수 있다(`container: true` 라 라벨이 자식에서 올라온다). 실패하면 `find.byType(DpOptionRow)` 의 시맨틱스를 잡는다.

Run: `cd packages/dp_design && flutter test test/interaction/dp_option_row_test.dart`

Expected: PASS 2/2.

- [ ] **Step 9: `DpCheckRow` 실패 테스트를 쓴다**

`packages/dp_design/test/interaction/dp_check_row_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _host(Widget child) => MaterialApp(
  theme: DpTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  testWidgets('DpCheckRow: 체크 상태를 시맨틱스로 알리고 라벨을 함께 읽는다', (tester) async {
    final handle = tester.ensureSemantics();
    await tester.pumpWidget(
      _host(
        DpCheckRow(
          label: const Text('서비스 이용약관 동의'),
          description: const Text('서비스 이용에 필요한 기본 약관입니다.'),
          value: true,
          onChanged: (_) {},
        ),
      ),
    );

    final node = tester.getSemantics(find.text('서비스 이용약관 동의'));
    expect(node.hasFlag(SemanticsFlag.hasCheckedState), isTrue);
    expect(node.hasFlag(SemanticsFlag.isChecked), isTrue);
    handle.dispose();
  });

  testWidgets('DpCheckRow: 마지막 행은 하단 구분선을 그리지 않는다', (tester) async {
    await tester.pumpWidget(
      _host(
        DpCheckRow(
          label: const Text('마케팅 정보 수신'),
          value: false,
          onChanged: (_) {},
          last: true,
        ),
      ),
    );

    final box = tester.widget<Container>(
      find.byKey(const ValueKey('dp-check-row')),
    );
    final decoration = box.decoration! as BoxDecoration;
    expect(decoration.border, isNull);
  });

  testWidgets('DpCheckRow: onChanged 가 null 이면 눌러도 바뀌지 않는다', (tester) async {
    await tester.pumpWidget(
      _host(
        const DpCheckRow(
          label: Text('필수 항목'),
          value: true,
          onChanged: null,
        ),
      ),
    );

    await tester.tap(find.text('필수 항목'));
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
```

- [ ] **Step 10: 테스트를 돌려 red 를 확인한다**

Run: `cd packages/dp_design && flutter test test/interaction/dp_check_row_test.dart`

Expected: FAIL — `DpCheckRow` 가 없다.

- [ ] **Step 11: `DpCheckRow` 를 만든다**

`packages/dp_design/lib/src/interaction/dp_check_row.dart`:

```dart
import 'package:flutter/material.dart';

import '../theme/dp_colors.dart';
import '../theme/dp_spacing.dart';

/// 동의 체크 행(시안 `.chk`) — 체크박스 + 라벨·설명 + 우측 보조 링크.
///
/// `CheckboxListTile` 을 쓰지 않는 이유: 시안의 행은 우측에 「전문 보기」 링크를
/// 두는데 `CheckboxListTile` 의 `secondary`·`trailing` 은 체크박스와 자리를
/// 다투고, 라벨·설명·링크 셋이 한 노드로 병합돼 스크린리더가 링크를 놓친다.
class DpCheckRow extends StatelessWidget {
  const DpCheckRow({
    super.key,
    required this.label,
    required this.value,
    required this.onChanged,
    this.description,
    this.trailing,
    this.last = false,
  });

  final Widget label;
  final Widget? description;
  final bool value;

  /// null 이면 읽기 전용이다(필수 동의 등).
  final ValueChanged<bool>? onChanged;

  /// 우측 보조 요소(「전문 보기」 링크 등). 체크 상태와 별개의 노드로 남는다.
  final Widget? trailing;

  final bool last;

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final text = Theme.of(context).textTheme;
    final onChanged = this.onChanged;

    return Container(
      key: const ValueKey('dp-check-row'),
      padding: const EdgeInsets.symmetric(
        vertical: 10,
        horizontal: DpSpacing.lg,
      ),
      decoration: BoxDecoration(
        border: last ? null : Border(bottom: BorderSide(color: c.border)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 체크 상태와 라벨을 한 노드로 묶는다 — 체크박스만 읽히면 무엇에
          // 동의하는지 알 수 없다. 우측 `trailing` 은 이 노드 밖에 남는다.
          Expanded(
            child: Semantics(
              container: true,
              checked: value,
              enabled: onChanged != null,
              onTap: onChanged == null ? null : () => onChanged(!value),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ExcludeSemantics(
                    child: Checkbox(
                      value: value,
                      onChanged: onChanged == null
                          ? null
                          : (next) => onChanged(next ?? false),
                      visualDensity: VisualDensity.compact,
                    ),
                  ),
                  const SizedBox(width: DpSpacing.sm),
                  Expanded(
                    child: Column(
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
                        if (description != null) ...[
                          const SizedBox(height: 2),
                          DefaultTextStyle.merge(
                            style: TextStyle(
                              fontSize: 13,
                              color: c.textSecondary,
                            ),
                            child: description!,
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (trailing != null) ...[
            const SizedBox(width: DpSpacing.sm),
            trailing!,
          ],
        ],
      ),
    );
  }
}
```

- [ ] **Step 12: 테스트를 돌려 green 을 확인한다**

Run: `cd packages/dp_design && flutter test test/interaction/dp_check_row_test.dart`

Expected: PASS 3/3.

- [ ] **Step 13: barrel 에 셋을 추가하고 전체를 돌린다**

`packages/dp_design/lib/dp_design.dart` 에 알파벳 순서로 넣는다:

```dart
export 'src/interaction/dp_check_row.dart';
export 'src/interaction/dp_option_row.dart';
export 'src/layout/dp_steps.dart';
```

Run: `cd packages/dp_design && flutter test` 이어서 `cd apps/admin && flutter test`

Expected: dp_design 360+ PASS · admin 156 PASS.

- [ ] **Step 14: 대비를 라이트·다크 둘 다 잰다**

`accentSoft` 위의 `primaryTextStrong`(`DpSteps` 현재 단계)과 `textSecondary`(비현재 단계) 대비를 두 테마에서 계산한다. P3 의 `textFaint` 사고처럼 **한쪽만 보면 놓친다.**

```bash
cd packages/dp_design && flutter test test/theme --plain-name "대비"
```

기존 대비 테스트가 있으면 새 조합을 추가한다. 없으면 이 Task 에서 만든다:

```dart
  test('DpSteps 현재 단계: accentSoft 위 primaryTextStrong 가 라이트·다크 모두 AA', () {
    for (final colors in [DpColors.light, DpColors.dark]) {
      expect(
        contrastRatio(colors.primaryTextStrong, colors.accentSoft),
        greaterThanOrEqualTo(4.5),
      );
    }
  });
```

`contrastRatio`·`DpColors.light`/`dark` 의 실제 이름은 기존 대비 테스트에서 가져온다.

- [ ] **Step 15: format 하고 커밋한다**

```bash
dart format packages/dp_design/lib/src/layout/dp_steps.dart packages/dp_design/lib/src/interaction/dp_option_row.dart packages/dp_design/lib/src/interaction/dp_check_row.dart packages/dp_design/test/layout/dp_steps_test.dart packages/dp_design/test/interaction/dp_option_row_test.dart packages/dp_design/test/interaction/dp_check_row_test.dart
git add packages/dp_design/lib/src/layout/dp_steps.dart packages/dp_design/lib/src/interaction/dp_option_row.dart packages/dp_design/lib/src/interaction/dp_check_row.dart packages/dp_design/lib/dp_design.dart packages/dp_design/test
git commit -F - <<'MSG'
feat(dp_design): 시안 온보딩 프리미티브 3종 — DpSteps·DpOptionRow·DpCheckRow

시안 .steps(진단 3화면)·.opt(진단 2화면)·.chk(동의 화면)에 대응한다.
두 화면 이상이 쓰므로 화면 안이 아니라 dp_design 에 둔다.

- DpSteps: compact 에서 세로로 쌓인다(390px 에 세 단계를 나란히 두면 잘린다)
- DpOptionRow: 행 전체가 타깃이고 라디오 시맨틱스를 갖는다
- DpCheckRow: 체크+라벨을 한 노드로, 우측 「전문 보기」는 별개 노드로
  (CheckboxListTile 은 셋을 병합해 링크를 놓친다)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
```

---

## Task 14: 로그인 + 인증 콜백 — `.login` 2열 / `.narrow.center`

**시안 `login`** 과 파생 화면(인증 콜백). 시안 `.login{grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);gap:48px}` 이고 좌측은 `.flow` 목록 3항목, 우측은 `.panel.signin` 이다.

**Files:**
- Modify: `apps/web/lib/src/features/auth/presentation/login_page.dart`
- Modify: `apps/web/lib/src/features/auth/presentation/auth_callback_page.dart`
- Test: `apps/web/test/features/auth/login_page_test.dart`
- Test: `apps/web/test/features/auth/login_header_test.dart`
- Test: `apps/web/test/features/auth/auth_callback_page_test.dart`

**Interfaces:** 새 공개 API 없음.

### 판정 (Ruling)

| 기존 요소 | 처리 | 근거 |
|---|---|---|
| `_LoginStoryPanel` 의 `BoxDecoration` 그라디언트·`_DecorativeOrb` | **제거** | 순수 장식이다. 시안 `.login` 좌측은 배경 없이 글자와 `.flow` 목록만 있다. Global Constraints 의 「장식은 기능이 아니다」. |
| `_StoryChip` | **`DpTag` 로 교체** | 자체 `BoxDecoration` 을 없앤다. |
| `_LoginAccessPanel` 의 `ConstrainedBox(maxWidth: 480)` | **제거** — `.login` 그리드가 폭을 정한다 | 시안은 우측 칼럼이 `.9fr` 이다. 480 고정은 큰 화면에서 어색하게 좁다. |
| `LayoutBuilder(compact = maxWidth < 900)` | **`DpWindowClass` 로 교체** | 폭 경계의 SSoT 는 `DpWindowClass`(600/840/1240)다. 900 은 리터럴이고 어느 토큰과도 맞지 않는다. `.login` 은 시안의 `@container(max-width:720px)` 에 해당하므로 medium 이하에서 1열로 간다 — `DpCols` 와 같은 판정이다. |
| `_LoginSessionCheck` | **보존** — `.narrow.center` 로 | 세션 확인 중 화면. 시안 `beta` 문법에서 파생. |
| 스토리 문구·`.flow` 3항목 | **시안 문구로 신설** | 시안 `.flow` 의 「맞춤 학습 경로」·「실시간 AI 멘토」·「성장 기록」 세 항목. 현재 화면에 대응 문구가 있으면 그것을 쓰고, 없으면 시안 문구를 그대로 옮긴다(시안이 정본인 신설 요소다). |
| `DpPageHeader` (`_LoginAccessPanel` 안) | **제거** | 시안 `.panel.signin` 은 `h3`「다시 만나서 반가워요」+ 설명 + 버튼 둘이다. 페이지 헤더가 아니라 패널 제목이다. `login_header_test.dart` 가 이 구조를 단언하므로 함께 고친다. |

- [ ] **Step 1: 기준선을 확인한다**

Run: `cd apps/web && flutter test test/features/auth 2>&1 | tail -5`

Expected: 통과 개수를 기록한다. `login_header_test.dart` 가 무엇을 단언하는지 읽어 둔다 — 이 Task 가 그 구조를 바꾼다.

- [ ] **Step 2: `.login` 2열 실패 테스트를 쓴다**

```dart
  testWidgets('로그인: 1240 이상에서 스토리 | 로그인 패널 2열로 배치한다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(1280, 900)));
    await tester.pumpAndSettle();

    final story = tester.getRect(find.text('맞춤 학습 경로'));
    final panel = tester.getRect(find.text('GitHub로 계속하기'));
    expect(panel.left, greaterThan(story.left));
  });

  testWidgets('로그인: 장식 원과 그라디언트를 쓰지 않는다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(1280, 900)));
    await tester.pumpAndSettle();

    // 장식 컨테이너가 남아 있으면 시안과 어긋난다.
    final gradients = tester
        .widgetList<Container>(find.byType(Container))
        .where((c) => (c.decoration as BoxDecoration?)?.gradient != null);
    expect(gradients, isEmpty);
  });

  testWidgets('로그인: medium 이하에서 한 열이 된다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(800, 900)));
    await tester.pumpAndSettle();

    final story = tester.getRect(find.text('맞춤 학습 경로'));
    final panel = tester.getRect(find.text('GitHub로 계속하기'));
    expect(panel.top, greaterThan(story.top));
  });
```

- [ ] **Step 3: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/auth/login_page_test.dart --plain-name "2열로 배치"`

Expected: FAIL — 현재 문구가 시안과 다르고 장식이 있다.

- [ ] **Step 4: 로그인 화면을 다시 짠다**

`login_page.dart` 의 `build` 를 아래로 바꾼다. `_LoginStoryPanel`·`_StoryChip`·`_DecorativeOrb` 를 지우고 `_LoginStory` 를 새로 둔다.

```dart
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    /* 기존 상태 읽기 그대로 */

    // 시안 `.login{grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);gap:48px}`.
    // 폭 경계는 `DpWindowClass` 가 SSoT 다 — 옛 리터럴 900 은 어느 토큰과도 맞지 않았다.
    final twoColumn = switch (context.windowClass) {
      DpWindowClass.expanded || DpWindowClass.large => true,
      DpWindowClass.compact || DpWindowClass.medium => false,
    };

    final story = _LoginStory();
    final panel = _LoginAccessPanel(/* 기존 인자 그대로 */);

    return Scaffold(
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(vertical: DpSpacing.xxl),
        child: twoColumn
            ? Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Expanded(flex: 11, child: story),
                  const SizedBox(width: DpSpacing.xxxl),
                  Expanded(flex: 9, child: panel),
                ],
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  story,
                  const SizedBox(height: DpSpacing.xl),
                  panel,
                ],
              ),
      ),
    );
  }
```

`_LoginStory`:

```dart
/// 시안 `.login` 좌측 — eyebrow + 큰 제목 + 설명 + `.flow` 목록 3항목.
/// 장식(그라디언트·원)을 쓰지 않는다.
class _LoginStory extends StatelessWidget {
  static const _flow = <({String title, String body})>[
    (title: '맞춤 학습 경로', body: '15문항 진단과 GitHub 분석으로 12주 계획을 만듭니다.'),
    (title: '실시간 AI 멘토', body: '지금 보고 있는 과제의 맥락으로 답합니다.'),
    (title: '성장 기록', body: '완료한 과제와 연속 학습이 쌓입니다.'),
  ];

  @override
  Widget build(BuildContext context) {
    final c = context.dpColors;
    final text = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'LEARN · BUILD · GROW',
          style: text.labelMedium?.copyWith(
            color: c.primaryTextStrong,
            letterSpacing: 1.2,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: DpSpacing.sm),
        Text(
          '오늘 할 일을 선명하게, 성장은 매일 이어지게.',
          style: text.headlineMedium?.copyWith(color: c.textPrimary),
        ),
        const SizedBox(height: DpSpacing.md),
        Text(
          '진단부터 실습, AI 멘토 피드백까지 하나의 흐름으로 연결합니다.',
          style: text.bodyLarge?.copyWith(color: c.textSecondary),
        ),
        const SizedBox(height: DpSpacing.xl),
        // 시안 `.flow` — 구분선으로 나뉜 3항목.
        DpListLines(
          children: [
            for (final item in _flow)
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 120,
                    child: Text(
                      item.title,
                      style: text.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: c.textPrimary,
                      ),
                    ),
                  ),
                  const SizedBox(width: DpSpacing.md),
                  Expanded(
                    child: Text(
                      item.body,
                      style: text.bodyMedium?.copyWith(color: c.textSecondary),
                    ),
                  ),
                ],
              ),
          ],
        ),
      ],
    );
  }
}
```

`_flow` 의 120px 고정폭은 시안 `.flow li{grid-template-columns:120px 1fr}` 그대로다 — 리터럴이지만 시안의 값이므로 **주석으로 출처를 남긴다.** compact 에서 시안은 `grid-template-columns:1fr` 로 쌓으므로 `context.windowClass == DpWindowClass.compact` 면 `Column` 으로 바꾼다.

`_LoginAccessPanel` 은 `ConstrainedBox(maxWidth: 480)` 과 `DpPageHeader` 를 없애고 `DpPanel` 로 바꾼다:

```dart
    return DpPanel(
      padding: const EdgeInsets.all(DpSpacing.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('다시 만나서 반가워요', style: text.titleLarge),
          const SizedBox(height: DpSpacing.sm),
          Text(
            '계정을 연결하고 오늘의 학습 흐름을 이어가세요.',
            style: text.bodyMedium?.copyWith(color: c.textSecondary),
          ),
          const SizedBox(height: DpSpacing.lg),
          /* 기존 GitHub·Google 버튼과 약관 문구 그대로 */
        ],
      ),
    );
```

- [ ] **Step 5: 테스트를 돌려 green 을 확인한다**

Run: `cd apps/web && flutter test test/features/auth/login_page_test.dart test/features/auth/login_header_test.dart`

Expected: PASS. `login_header_test.dart` 가 `DpPageHeader` 를 단언하면 패널 제목(`'다시 만나서 반가워요'`)을 단언하도록 고치고, **그 변경 근거를 테스트 이름에 남긴다**(「로그인은 페이지 헤더가 아니라 패널 제목을 쓴다 — 시안 `.panel.signin`」).

- [ ] **Step 6: 인증 콜백을 `.narrow.center` 로 바꾼다**

`auth_callback_page.dart` 의 본문을 아래 모양으로 바꾼다(시안 `beta` 파생):

```dart
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxWidth: context.appTokens.readableMaxWidth,
          ),
          child: Padding(
            padding: const EdgeInsets.all(DpSpacing.xl),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                /* 기존 상태별 내용(진행·실패·재시도) 그대로 */
              ],
            ),
          ),
        ),
      ),
    );
```

- [ ] **Step 7: 테스트를 돌린다**

Run: `cd apps/web && flutter test test/features/auth`

Expected: PASS. `mentor_invite_callback_test.dart`·`auth_controller_test.dart` 는 표현부와 무관하므로 그대로 통과해야 한다.

- [ ] **Step 8: analyze·format 하고 커밋한다**

```bash
cd apps/web && flutter analyze lib/src/features/auth
cd ../.. && dart format apps/web/lib/src/features/auth/presentation/login_page.dart apps/web/lib/src/features/auth/presentation/auth_callback_page.dart
git add apps/web/lib/src/features/auth apps/web/test/features/auth
git commit -F - <<'MSG'
feat(web): 로그인을 시안 .login 2열로, 인증 콜백을 .narrow.center 로

- 장식(그라디언트 배경·_DecorativeOrb) 제거 — 시안 좌측은 글자와 .flow 목록뿐
- 폭 경계 리터럴 900 → DpWindowClass(expanded 이상에서 2열)
- 로그인 패널의 maxWidth 480 고정 제거 — .login 그리드가 폭을 정한다
- DpPageHeader → DpPanel 제목(시안 .panel.signin 은 h3 다)
- 인증 콜백은 시안 beta 문법에서 파생(중앙 narrow)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
```

- [ ] **Step 9: 기준선 영향을 기록한다**

```markdown
- `/login` 로그인 — 장식 배경·원 제거, 2열 경계 900 → 1240, 로그인 패널 폭 제약 제거, 페이지 헤더 → 패널 제목. **랜딩과 함께 첫인상이 바뀌는 화면**이라 ET13 visual baseline 재기록 대상 중 눈에 가장 크게 띈다.
- `/auth/callback` — 중앙 narrow 정렬.
```

---

## Task 15: 동의 + 베타 대기 — `.narrow` 760 + `.chk` 패널

**시안 `consent`·`beta`.** 동의 화면은 `.narrow`(760) + 출생 연도 입력 + `.chk` 4행 패널이고, 베타 대기는 `.narrow.center` 다. 현재는 각각 440 폭 고정이다.

**Files:**
- Modify: `apps/web/lib/src/features/consent/presentation/consent_page.dart`
- Modify: `apps/web/lib/src/features/beta/presentation/beta_pending_page.dart`
- Test: `apps/web/test/features/beta/beta_pending_page_test.dart`
- Test: `apps/web/test/features/consent/` 아래 기존 테스트 (경로는 Step 1 에서 확인)

**Interfaces:** 새 공개 API 없음. `DpCheckRow`(Task 13) 를 소비한다.

### 판정 (Ruling)

| 기존 요소 | 처리 | 근거 |
|---|---|---|
| `ConstrainedBox(maxWidth: 440)`(동의) | **`readableMaxWidth`(760) 로 교체** | 시안 `.narrow{max-width:760px}`. 440 은 리터럴이고 `.chk` 행의 라벨+설명+「전문 보기」 셋을 한 줄에 담기 좁다. |
| `ConstrainedBox(maxWidth: 440)`(베타) | **`readableMaxWidth`(760) 로 교체** | 같음. 시안 `beta` 는 `.narrow.center` 이고 문단은 `max-width:52ch` 로 따로 좁힌다. |
| `ConstrainedBox(maxWidth: 360)`(`_BlockedView`) | **`readableMaxWidth` 로 교체** | 같음. 14세 미만 차단 화면이다. |
| `CheckboxListTile` 4개 | **`DpCheckRow` 로 교체** | 시안 `.chk` 는 체크박스 + 라벨·설명 + 우측 「전문 보기」 링크 3열이다. `CheckboxListTile` 은 셋을 한 노드로 병합해 링크를 놓친다(Task 13 의 근거). |
| 「전문 보기」 링크 | **신설/유지** — `DpLink.inline` | 시안 `.chk` 의 우측 `a.lk`. 현재 화면에 그 링크가 없으면 **신설하지 않는다** — 약관 전문 라우트가 없으면 링크할 곳이 없다. Step 1 에서 `git grep '이용약관'` 으로 실측해 이 표를 갱신한다. |
| `CircularProgressIndicator`(로딩) | **`DpLoading` 으로 교체** | 레포 표준 로딩이다. |
| 출생 연도 입력 | **보존** — `.fld` 문법 | 시안 `consent` 의 첫 필드. |

- [ ] **Step 1: 기준선과 약관 전문 라우트를 확인한다**

Run:

```bash
git ls-files apps/web/test | grep -i consent
git grep -n "이용약관\|/terms\|privacy" -- apps/web/lib/src/features/consent apps/web/lib/src/app
cd apps/web && flutter test test/features/beta 2>&1 | tail -3
```

Expected: 동의 화면 테스트 경로와 「전문 보기」가 갈 곳이 있는지 기록한다. 앱에 라우트가 없고 홈(`leva.ai.kr`)에만 있으면 셸 푸터와 같은 방식(`onOpenExternal`)으로 연다 — 그 배선이 동의 화면에 없으면 **링크를 넣지 않고** Ruling 표를 갱신한다.

- [ ] **Step 2: 동의 화면 폭·`.chk` 실패 테스트를 쓴다**

```dart
  testWidgets('동의: 본문 폭이 readableMaxWidth(760) 다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(1280, 900)));
    await tester.pumpAndSettle();

    final box = tester.widget<ConstrainedBox>(
      find
          .ancestor(
            of: find.byType(DpCheckRow).first,
            matching: find.byType(ConstrainedBox),
          )
          .last,
    );
    expect(box.constraints.maxWidth, 760);
  });

  testWidgets('동의: 체크 행을 DpCheckRow 로 그린다', (tester) async {
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    expect(find.byType(DpCheckRow), findsNWidgets(4));
    expect(find.byType(CheckboxListTile), findsNothing);
  });

  testWidgets('동의: 필수 항목을 모두 켜야 계속할 수 있다', (tester) async {
    // 기존 테스트에 같은 계약이 있으면 그것을 그대로 쓴다 — 없으면 만든다.
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();
    expect(find.text('동의하고 계속하기'), findsOneWidget);
  });
```

- [ ] **Step 3: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/consent --plain-name "DpCheckRow"`

Expected: FAIL — 현재 `CheckboxListTile` 이다.

- [ ] **Step 4: 동의 화면을 고친다**

`consent_page.dart` 의 `build` 에서 `ConstrainedBox(maxWidth: 440)` 을 바꾸고, 체크 목록을 `DpPanel` 안의 `DpCheckRow` 로 바꾼다:

```dart
          child: ConstrainedBox(
            // 시안 `.narrow{max-width:760px}`. 440 은 `.chk` 3열을 담기 좁았다.
            constraints: BoxConstraints(
              maxWidth: context.appTokens.readableMaxWidth,
            ),
```

`_consentTile` 을 바꾼다:

```dart
  Widget _consentTile(_ConsentKind k) {
    final meta = _meta[k]!; // 기존 메타 접근을 그대로 쓴다
    return DpCheckRow(
      label: Row(
        children: [
          Text(meta.label),
          const SizedBox(width: DpSpacing.xs),
          DpTag(label: meta.required ? '필수' : '선택'),
        ],
      ),
      description: meta.description == null ? null : Text(meta.description!),
      value: _checked[k] ?? false,
      onChanged: (next) => setState(() => _checked[k] = next),
      last: k == _ConsentKind.values.last,
    );
  }
```

체크 목록을 감싼다:

```dart
                DpPanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      for (final k in _ConsentKind.values) _consentTile(k),
                    ],
                  ),
                ),
```

`_BlockedView` 의 `ConstrainedBox(maxWidth: 360)` 도 `readableMaxWidth` 로 바꾸고, 로딩의 `CircularProgressIndicator` 를 `DpLoading()` 으로 바꾼다.

- [ ] **Step 5: 테스트를 돌려 green 을 확인한다**

Run: `cd apps/web && flutter test test/features/consent`

Expected: PASS. `CheckboxListTile` 을 탭하던 테스트는 `DpCheckRow` 의 라벨을 탭하게 고친다.

- [ ] **Step 6: 베타 대기 화면을 `.narrow.center` 로 바꾼다**

`beta_pending_page.dart`:

```dart
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxWidth: context.appTokens.readableMaxWidth,
          ),
          child: Padding(
            padding: const EdgeInsets.all(DpSpacing.xl),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                const DpTag(label: '베타 대기'),
                const SizedBox(height: DpSpacing.md),
                Text(
                  '승인되면 알려드립니다',
                  style: Theme.of(context).textTheme.headlineSmall,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: DpSpacing.sm),
                Text(
                  '베타 대기자 명단에 등록되었어요. 승인되면 이메일로 알려드리고, 이 화면에서 바로 시작할 수 있어요.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: context.dpColors.textSecondary,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: DpSpacing.lg),
                /* 기존 액션(게스트 진단·로그아웃) 그대로 */
              ],
            ),
          ),
        ),
      ),
    );
```

`DpPageHeader(title: '베타 대기', description: '승인되면 알려드립니다')` 는 **없앤다** — 시안 `beta` 는 중앙 정렬이라 좌측 정렬 페이지 헤더와 맞지 않는다. 제목을 `headlineSmall` 로 직접 그린다.

- [ ] **Step 7: 테스트를 돌린다**

Run: `cd apps/web && flutter test test/features/beta test/features/consent`

Expected: PASS. `beta_pending_page_test.dart` 가 `DpPageHeader` 를 단언하면 제목 텍스트를 단언하게 고친다.

- [ ] **Step 8: 200% 배율을 확인한다 (Review Focus 2)**

```dart
  testWidgets('동의: 200% 배율에서 체크 행이 깨지지 않는다', (tester) async {
    await tester.pumpWidget(_app(
      size: const Size(390, 900),
      textScaler: const TextScaler.linear(2),
    ));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
```

`_app` 헬퍼가 `textScaler` 를 받지 않으면 받게 고친다.

- [ ] **Step 9: analyze·format 하고 커밋한다**

```bash
cd apps/web && flutter analyze lib/src/features/consent lib/src/features/beta
cd ../.. && dart format apps/web/lib/src/features/consent/presentation/consent_page.dart apps/web/lib/src/features/beta/presentation/beta_pending_page.dart
git add apps/web/lib/src/features/consent apps/web/lib/src/features/beta apps/web/test/features/consent apps/web/test/features/beta
git commit -F - <<'MSG'
feat(web): 동의를 .narrow 760 + .chk 패널로, 베타 대기를 .narrow.center 로

- 폭 리터럴 440·360 → readableMaxWidth(760)
- CheckboxListTile 4개 → DpCheckRow (라벨과 우측 링크가 갈라지지 않는다)
- 베타 대기는 좌측 정렬 페이지 헤더를 버리고 중앙 정렬(시안 beta)
- CircularProgressIndicator → DpLoading

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
```

- [ ] **Step 10: 기준선 영향을 기록한다**

```markdown
- `/consent` 동의 — 폭 440 → 760, 체크 행 문법 교체.
- `/beta` 베타 대기 — 좌측 정렬 페이지 헤더 → 중앙 정렬, 폭 440 → 760.
```

---

## Task 16: 진단 3단계 — `.steps` + `.opt` + `.bars` + `.next`

**시안 `dstart`·`dq`·`dresult`.** 세 화면이 한 파일(`diagnostic_page.dart`)에 `_StartView`·`_QuestionView`·결과로 들어 있다. 이미 `readableMaxWidth` 를 쓰므로 폭은 맞고, 단계 표시·선택 옵션·개념별 결과 바를 시안 문법으로 바꾼다.

**Files:**
- Modify: `apps/web/lib/src/features/diagnostic/presentation/diagnostic_page.dart`
- Test: `apps/web/test/features/diagnostic/` 아래 기존 테스트 전부
- Test: `apps/web/test/app/router_diagnostic_handoff_test.dart`

**Interfaces:** 새 공개 API 없음. `DpSteps`·`DpOptionRow`(Task 13) 를 소비한다.

### 판정 (Ruling)

| 기존 요소 | 처리 | 근거 |
|---|---|---|
| `_DiagnosticJourney`·`_JourneyStep`(`BoxDecoration`) | **`DpSteps` 로 교체** | 시안 `.steps`. 세 화면이 같은 단계 표시를 쓰므로 프리미티브로 올렸다(Task 13). |
| `_DiagnosticTrackForm` 의 트랙 선택 | **`DpOptionRow` 로 교체** | 시안 `dstart` 의 `.opt` 3개. 현재 무엇으로 그리는지 Step 1 에서 확인해 이 표를 갱신한다. |
| `_QuestionView` 의 보기 선택 | **`DpOptionRow` 로 교체** | 시안 `dq` 의 `.opt` 4개. |
| `LinearProgressIndicator`(문항 진행) | **보존** | 시안 `dq` 의 `.prog` 에 대응한다. |
| `_DiagnosticOutcomes`(`BoxDecoration`) | **`DpPanel` 로 교체** | 시안 `dstart` 의 「결과 형태 미리보기」 패널 = `DpKeyValues`. |
| `_StartView` 의 `BoxDecoration` | **`DpPanel` 로 교체** | 같음. |
| 진단 결과의 개념별 점수 | **시안 `.bars` 로** — `DpPanel` + 라벨/바/퍼센트 3열 | 현재 무엇으로 그리는지 Step 1 에서 확인한다. 데이터가 있으면 시안 모양으로, 없으면 현재 모양을 `DpPanel` 로만 감싼다. |
| 진단 결과의 「경로 만들기」 | **`DpNextActionBand` 로** | 시안 `dresult` 의 `.next` 밴드. `DpNextActionBand` 가 그 역할의 레포 표준이다. |
| `_LegacyPreview` | **보존** | 미인증 사용자용 미리보기다. |

- [ ] **Step 1: 현재 구조와 기준선을 실측한다**

Run:

```bash
git grep -n "BoxDecoration\|RadioListTile\|Radio(\|SegmentedButton\|_JourneyStep\|bars" -- apps/web/lib/src/features/diagnostic/presentation/diagnostic_page.dart
cd apps/web && flutter test test/features/diagnostic 2>&1 | tail -5
```

Expected: `BoxDecoration` 5곳(`_StartView`·`_JourneyStep`·`_DiagnosticOutcomes` 등)의 정확한 위치와 트랙·보기 선택을 무엇으로 그리는지 기록하고, Ruling 표의 해당 줄을 갱신한다.

- [ ] **Step 2: `.steps` 실패 테스트를 쓴다**

```dart
  testWidgets('진단 시작: 3단계 표시에서 1단계가 현재다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(1280, 900)));
    await tester.pumpAndSettle();

    expect(find.byType(DpSteps), findsOneWidget);
    final steps = tester.widget<DpSteps>(find.byType(DpSteps));
    expect(steps.currentIndex, 0);
    expect(steps.labels, ['1 트랙 선택', '2 실력 진단', '3 학습 경로']);
  });

  testWidgets('진단 문항: 2단계가 현재다', (tester) async {
    await tester.pumpWidget(_app(/* 문항 단계로 진입 */));
    await tester.pumpAndSettle();

    final steps = tester.widget<DpSteps>(find.byType(DpSteps));
    expect(steps.currentIndex, 1);
  });

  testWidgets('진단 결과: 3단계가 현재이고 다음 행동 밴드가 있다', (tester) async {
    await tester.pumpWidget(_app(/* 결과 단계로 진입 */));
    await tester.pumpAndSettle();

    final steps = tester.widget<DpSteps>(find.byType(DpSteps));
    expect(steps.currentIndex, 2);
    expect(find.byType(DpNextActionBand), findsOneWidget);
    expect(find.text('경로 만들기'), findsOneWidget);
  });
```

- [ ] **Step 3: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/diagnostic --plain-name "3단계 표시"`

Expected: FAIL — `DpSteps` 가 없고 `_DiagnosticJourney` 가 그린다.

- [ ] **Step 4: `DpSteps` 로 바꾼다**

`diagnostic_page.dart` 의 `_DiagnosticJourney`·`_JourneyStep` 을 지우고, 세 화면이 각자 `DpSteps` 를 그리게 한다. 라벨은 한 곳에 둔다:

```dart
/// 시안 `.steps` 라벨 — 세 화면이 같은 배열을 쓴다.
const _diagnosticSteps = ['1 트랙 선택', '2 실력 진단', '3 학습 경로'];
```

각 뷰의 최상단에 넣는다:

```dart
        const DpSteps(labels: _diagnosticSteps, currentIndex: 0), // dstart
        const DpSteps(labels: _diagnosticSteps, currentIndex: 1), // dq
        const DpSteps(labels: _diagnosticSteps, currentIndex: 2), // dresult
```

- [ ] **Step 5: 선택 옵션을 `DpOptionRow` 로 바꾼다**

트랙 선택(`_DiagnosticTrackForm`)과 문항 보기(`_QuestionView`)를 바꾼다:

```dart
            for (final track in tracks)
              Padding(
                padding: const EdgeInsets.only(bottom: DpSpacing.sm),
                child: DpOptionRow(
                  label: Text(trackLabels[track] ?? track),
                  description: Text(trackDescriptions[track] ?? ''),
                  selected: selected == track,
                  onSelect: () => onSelect(track),
                ),
              ),
```

```dart
            for (final option in question.options)
              Padding(
                padding: const EdgeInsets.only(bottom: DpSpacing.sm),
                child: DpOptionRow(
                  label: Text(option.text),
                  selected: chosen == option.id,
                  onSelect: () => onChoose(option.id),
                ),
              ),
```

필드 이름(`question.options`·`option.text`·`option.id`·`trackLabels`·`trackDescriptions`)은 Step 1 의 실측으로 맞춘다.

- [ ] **Step 6: `BoxDecoration` 을 `DpPanel` 로 바꾸고 결과를 `.bars`·`.next` 로 만든다**

`_StartView`·`_DiagnosticOutcomes` 의 `Container(decoration: BoxDecoration(...))` 를 `DpPanel(title: DpPanelTitle('결과 형태 미리보기'), child: DpKeyValues(entries: [...]))` 로 바꾼다. 시안 `dstart` 의 그 패널은 키-값 3행이다:

```dart
        DpPanel(
          title: const DpPanelTitle('결과 형태 미리보기'),
          child: const DpKeyValues(
            entries: [
              (key: '현재 레벨', value: Text('1~5 단계와 신뢰도')),
              (key: '강점·보강 개념', value: Text('개념 태그 목록')),
              (key: '다음 단계', value: Text('12주 맞춤 학습 경로')),
            ],
          ),
        ),
```

결과 화면의 개념별 점수는 시안 `.bars{grid-template-columns:90px 1fr 40px}` 모양으로 `DpPanel` 안에 그린다:

```dart
        DpPanel(
          title: const DpPanelTitle('개념별 결과'),
          padding: const EdgeInsets.symmetric(
            vertical: DpSpacing.md,
            horizontal: DpSpacing.lg,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final entry in concepts.entries) ...[
                Row(
                  children: [
                    // 시안 `.bars div{grid-template-columns:90px 1fr 40px}`.
                    SizedBox(width: 90, child: Text(entry.key)),
                    const SizedBox(width: DpSpacing.sm),
                    Expanded(
                      child: LinearProgressIndicator(value: entry.value),
                    ),
                    const SizedBox(width: DpSpacing.sm),
                    SizedBox(
                      width: 40,
                      child: Text(
                        '${(entry.value * 100).round()}%',
                        textAlign: TextAlign.right,
                        style: TextStyle(
                          color: context.dpColors.textSecondary,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DpSpacing.sm),
              ],
            ],
          ),
        ),
```

`concepts` 의 실제 출처(결과 모델의 개념별 점수 맵)는 Step 1 의 실측으로 맞춘다. **데이터가 없으면 이 패널을 만들지 않고** Ruling 표에 「결과 모델에 개념별 점수가 없다」로 적는다.

「경로 만들기」 버튼을 `DpNextActionBand` 로 바꾼다:

```dart
        DpNextActionBand(
          actionId: 'create_path_from_diagnosis',
          label: '경로 만들기',
          expectedOutcome: '비동기·트랜잭션 보강부터 시작하는 12주 경로를 구성합니다.',
          state: creating ? DpNextActionState.pending : DpNextActionState.ready,
          pendingLabel: '경로를 만드는 중',
          onPressed: (_) => onCreatePath(),
        ),
```

- [ ] **Step 7: 진단 테스트 전체를 돌린다**

Run: `cd apps/web && flutter test test/features/diagnostic test/app/router_diagnostic_handoff_test.dart`

Expected: PASS. 단계 표시를 `_JourneyStep` 으로 찾던 테스트는 `DpSteps` 로, 라디오를 찾던 테스트는 `DpOptionRow` 로 바꾼다.

- [ ] **Step 8: 390px 와 상태 분기를 확인한다 (Review Focus 1·5)**

```dart
  testWidgets('진단: 390px 에서 단계 표시가 세로로 쌓이고 넘치지 않는다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(390, 900)));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('진단: 제출 실패 시 다시 시도할 수 있다', (tester) async {
    await tester.pumpWidget(_app(/* 제출 실패 상태 */));
    await tester.pumpAndSettle();
    expect(find.byType(_AdvanceRetry), findsOneWidget);
  });
```

`_AdvanceRetry` 는 비공개 클래스라 테스트에서 타입으로 찾을 수 없다 — 버튼 문구로 찾는다.

- [ ] **Step 9: analyze·format 하고 커밋한다**

```bash
cd apps/web && flutter analyze lib/src/features/diagnostic
cd ../.. && dart format apps/web/lib/src/features/diagnostic/presentation/diagnostic_page.dart
git add apps/web/lib/src/features/diagnostic apps/web/test/features/diagnostic
git commit -F - <<'MSG'
feat(web): 진단 3단계를 시안 .steps + .opt + .bars + .next 로

- _DiagnosticJourney/_JourneyStep → DpSteps (세 화면이 같은 라벨 배열을 쓴다)
- 트랙·보기 선택 → DpOptionRow (행 전체가 타깃, 라디오 시맨틱스)
- BoxDecoration 패널 → DpPanel, 결과 형태 미리보기 → DpKeyValues
- 「경로 만들기」 → DpNextActionBand (시안 .next 밴드)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
```

- [ ] **Step 10: 기준선 영향을 기록한다**

```markdown
- `/diagnostic` 진단 3단계 — 단계 표시·선택 옵션·결과 패널 문법 교체. ET13 visual baseline 재기록 대상.
```

---

## Task 17: 마이페이지 + 설정 + placeholder

**시안 `mypage`·`settings`** 와 파생(placeholder). 마이페이지는 `.cols`(프로필 + 활동 표 | 프로필 kv·AI 멘토), 설정은 `.narrow` + `.rowline` 패널 3개다.

**Files:**
- Modify: `apps/web/lib/src/features/mypage/presentation/mypage_page.dart`
- Modify: `apps/web/lib/src/features/settings/presentation/settings_page.dart`
- Modify: `apps/web/lib/src/features/common/presentation/placeholder_page.dart`
- Test: `apps/web/test/features/mypage/` · `test/features/settings/` 아래 기존 테스트
- Test: `apps/web/test/features/settings/settings_rowline_test.dart` (신규)

**Interfaces:** 새 공개 API 없음. `DpRowLine`·`DpKeyValues`·`DpWebTable`·`DpCols`·`DpSide`(Task 1) 를 소비한다.

### 판정 (Ruling)

| 기존 요소 | 처리 | 근거 |
|---|---|---|
| 설정의 `_header` + `Divider` | **`DpPanel` 제목으로 교체** | 시안 `settings` 는 `.panel>h3` 세 개(알림·동의 관리·계정)다. |
| `SwitchListTile` 4개 | **`DpRowLine` 으로 교체** | 시안 `.rowline` — 좌측 라벨·설명, 우측 컨트롤. |
| `ListTile`(로그아웃·계정 삭제) | **`DpRowLine` 으로 교체** | 같음. 시안도 우측에 버튼을 둔다. |
| 설정 절 순서(동의 → 알림 → 계정) | **시안 순서로(알림 → 동의 관리 → 계정)** | 순수 표현 순서이고 시안이 정본이다. |
| `CircularProgressIndicator`(설정 로딩) | **`DpLoading` 으로 교체** | 레포 표준. |
| `_errorView` | **`SupportableError` 로 교체** | 다른 화면과 같은 실패 표현을 쓴다. 문의 경로가 붙는다. |
| 마이페이지 `_Body` 의 `BoxDecoration` 프로필 | **`.prof` 문법으로** — 테두리 없는 아바타 + 이름·소개·태그 | 시안 `.prof` 는 패널이 아니다(배경 없음). |
| 마이페이지의 `ListTile` 활동 목록 | **`DpWebTable` 로 교체** | 시안 `mypage` 의 「커뮤니티 활동」 표(제목·게시판·작성). **「작성」 칼럼은 데이터가 없다**(Task 8 의 `PostSummaryView` 실측과 같은 이유) → 제목·게시판 두 칼럼으로 만든다. |
| 시안 「프로필」 kv(목표 트랙·목표·경력) | **구현** — `DpKeyValues` | 프로필 모델에 그 필드가 있으면 쓴다. Step 1 에서 실측해 없는 항목은 뺀다. |
| 시안 「AI 멘토 초대」 패널 | **구현/유지** | 현재 화면에 멘토 접근 상태 표시가 있으면 사이드 패널로 옮긴다. 없으면 만들지 않는다(Step 1 실측). |
| `placeholder_page` | **`.narrow.center` 로** | 시안 `beta` 파생. |

- [ ] **Step 1: 현재 구조와 프로필 모델을 실측한다**

Run:

```bash
git grep -n "BoxDecoration\|ListTile\|SwitchListTile" -- apps/web/lib/src/features/mypage apps/web/lib/src/features/settings
git grep -n "class UserProfile\|targetTrack\|goal\|yearsOfExperience" -- packages/dp_core/lib/src/models
cd apps/web && flutter test test/features/mypage test/features/settings 2>&1 | tail -5
```

Expected: 프로필 모델의 실제 필드와 현재 통과 개수를 기록하고, Ruling 표의 「프로필 kv」·「AI 멘토 초대」 줄을 갱신한다.

- [ ] **Step 2: 설정 `.rowline` 실패 테스트를 쓴다**

`apps/web/test/features/settings/settings_rowline_test.dart`:

```dart
import 'package:dp_design/dp_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('설정: 알림·동의 관리·계정 세 패널을 시안 순서로 그린다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(1280, 900)));
    await tester.pumpAndSettle();

    final alarm = tester.getRect(find.text('알림'));
    final consent = tester.getRect(find.text('동의 관리'));
    final account = tester.getRect(find.text('계정'));
    expect(consent.top, greaterThan(alarm.top));
    expect(account.top, greaterThan(consent.top));
  });

  testWidgets('설정: 행을 DpRowLine 으로 그리고 ListTile 을 쓰지 않는다', (tester) async {
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    expect(find.byType(DpRowLine), findsWidgets);
    expect(find.byType(SwitchListTile), findsNothing);
    expect(find.byType(ListTile), findsNothing);
  });

  testWidgets('설정: 본문 폭이 readableMaxWidth(760) 를 넘지 않는다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(1280, 900)));
    await tester.pumpAndSettle();

    expect(
      tester.getSize(find.byType(DpRowLine).first).width,
      lessThanOrEqualTo(760),
    );
  });
}
```

`_app` 헬퍼는 기존 설정 테스트에서 가져온다.

- [ ] **Step 3: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/settings/settings_rowline_test.dart`

Expected: FAIL — 현재 `SwitchListTile`·`ListTile` 이고 순서가 동의 → 알림이다.

- [ ] **Step 4: 설정 화면을 다시 짠다**

`settings_page.dart` 의 `_readyView` 를 아래로 바꾼다:

```dart
  Widget _readyView(ConsentsView consents, NotificationPrefs prefs) {
    final notifier = ref.read(settingsControllerProvider.notifier);
    final c = context.dpColors;

    return SliverPadding(
      // 좌우 패딩은 셸이 준다.
      padding: const EdgeInsets.symmetric(vertical: DpSpacing.md),
      sliver: SliverToBoxAdapter(
        child: Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            // 시안 `settings` 는 `.narrow{max-width:760px;margin-inline:0}` 이다.
            constraints: BoxConstraints(
              maxWidth: context.appTokens.readableMaxWidth,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // 시안 순서: 알림 → 동의 관리 → 계정.
                DpPanel(
                  title: const DpPanelTitle('알림'),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      DpRowLine(
                        label: const Text('학습 리마인더'),
                        description: const Text('선호 시간대에 학습 알림을 받아요.'),
                        trailing: Switch(
                          value: prefs.reminderEnabled,
                          onChanged: notifier.setReminder,
                        ),
                      ),
                      DpRowLine(
                        label: const Text('주간 리포트 이메일'),
                        description: const Text('한 주 학습 요약을 이메일로 받아요.'),
                        trailing: Switch(
                          value: prefs.weeklyReportEmailEnabled,
                          onChanged: notifier.setWeeklyEmail,
                        ),
                        last: true,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: DpSpacing.lg),
                DpPanel(
                  title: const DpPanelTitle('동의 관리'),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      for (final type in _consentMeta.keys)
                        _consentRow(
                          type,
                          consents.itemOf(type),
                          notifier,
                          last: type == _consentMeta.keys.last,
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: DpSpacing.lg),
                DpPanel(
                  title: const DpPanelTitle('계정'),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      DpRowLine(
                        label: const Text('로그아웃'),
                        description: const Text('이 브라우저에서 로그아웃합니다.'),
                        trailing: OutlinedButton(
                          onPressed: () => notifier.logout(),
                          child: const Text('로그아웃'),
                        ),
                      ),
                      DpRowLine(
                        label: Text(
                          '계정 삭제',
                          style: TextStyle(color: c.danger),
                        ),
                        description: const Text('계정과 학습 데이터가 삭제됩니다(30일 유예).'),
                        trailing: OutlinedButton(
                          onPressed: _confirmDelete,
                          style: OutlinedButton.styleFrom(
                            foregroundColor: c.danger,
                            side: BorderSide(color: c.danger),
                          ),
                          child: const Text('계정 삭제'),
                        ),
                        last: true,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _consentRow(
    String type,
    ConsentItemView? item,
    SettingsController notifier, {
    required bool last,
  }) {
    final meta = _consentMeta[type]!;
    final agreed = item?.agreed ?? false;
    return DpRowLine(
      label: Row(
        children: [
          Text(meta.label),
          const SizedBox(width: DpSpacing.xs),
          DpTag(label: meta.required ? '필수' : '선택'),
        ],
      ),
      description: item?.agreedAt == null
          ? null
          : Text('${item!.agreedAt} 동의'),
      trailing: meta.required
          ? Icon(DpIcons.stepDone, color: context.dpColors.success)
          // 선택 동의: 현재 동의된 항목만 철회 가능(재동의는 후속).
          : Switch(
              value: agreed,
              onChanged: agreed ? (v) => notifier.setConsent(type, v) : null,
            ),
      last: last,
    );
  }
```

`item.agreedAt`·`notifier.setConsent` 의 정확한 이름은 기존 코드에서 가져온다. 로딩·실패를 바꾼다:

```dart
            SettingsLoading() => const SliverFillRemaining(
              hasScrollBody: false,
              child: DpLoading(label: '설정을 불러오는 중'),
            ),
            SettingsError(:final message) => SliverFillRemaining(
              hasScrollBody: false,
              child: SupportableError(
                message: message,
                onRetry: () =>
                    ref.read(settingsControllerProvider.notifier).load(),
              ),
            ),
```

`_errorView` 와 `_header` 를 지운다.

- [ ] **Step 5: 테스트를 돌려 green 을 확인한다**

Run: `cd apps/web && flutter test test/features/settings`

Expected: PASS. `SwitchListTile` 을 탭하던 테스트는 `Switch` 를 탭하게 고친다(`find.byType(Switch).at(n)`).

- [ ] **Step 6: 마이페이지 `.cols` 실패 테스트를 쓴다**

```dart
  testWidgets('마이페이지: .cols 2열(프로필+활동 표 | 사이드)을 그린다', (tester) async {
    await tester.pumpWidget(_app(size: const Size(1280, 900)));
    await tester.pumpAndSettle();

    expect(find.byType(DpCols), findsOneWidget);
    expect(find.text('커뮤니티 활동'), findsOneWidget);
    expect(find.byType(ListTile), findsNothing);
  });
```

- [ ] **Step 7: 테스트를 돌려 red 를 확인한다**

Run: `cd apps/web && flutter test test/features/mypage --plain-name ".cols 2열"`

Expected: FAIL.

- [ ] **Step 8: 마이페이지를 다시 짠다**

`_Body.build` 를 `DpCols` 로 감싼다. 좌측은 `.prof`(아바타 + 이름·소개·태그) + 「커뮤니티 활동」 `DpWebTable`, 우측은 `DpSide([프로필 kv, (있으면) AI 멘토 패널])` 다.

```dart
    return DpCols(
      main: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 시안 `.prof` — 배경 없는 아바타 + 이름·소개·태그.
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              /* 기존 아바타 위젯(BoxDecoration 의 배경·테두리는 남긴다 —
                 아바타는 원형 면이 필요하다) */
              const SizedBox(width: DpSpacing.lg),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [/* 이름·소개·배지 태그 */],
                ),
              ),
            ],
          ),
          const SizedBox(height: DpSpacing.xl),
          DpPanel(
            title: const DpPanelTitle('커뮤니티 활동'),
            child: DpWebTable(
              columns: [
                const (label: '제목', width: null, numeric: false),
                if (context.windowClass != DpWindowClass.compact)
                  const (label: '게시판', width: 96, numeric: false),
              ],
              empty: const Padding(
                padding: EdgeInsets.symmetric(
                  vertical: DpSpacing.xl,
                  horizontal: DpSpacing.lg,
                ),
                child: Text('아직 활동이 없어요'),
              ),
              rows: [
                for (final item in activities)
                  (
                    cells: [
                      DpLink.title(
                        text: item.title,
                        onTap: () => context.go(item.location),
                      ),
                      if (context.windowClass != DpWindowClass.compact)
                        Text(item.boardLabel),
                    ],
                    onTap: () => context.go(item.location),
                  ),
              ],
            ),
          ),
        ],
      ),
      side: DpSide(
        children: [
          DpPanel(
            title: const DpPanelTitle('프로필'),
            child: DpKeyValues(entries: [/* Step 1 실측으로 채운다 */]),
          ),
        ],
      ),
    );
```

`activities`·`item.title`·`item.boardLabel`·`item.location` 의 실제 출처는 Step 1 의 실측으로 맞춘다. **「작성」 칼럼은 넣지 않는다** — `PostSummaryView` 에 작성 시각이 없다(Task 8 실측).

- [ ] **Step 9: placeholder 를 `.narrow.center` 로 바꾼다**

`placeholder_page.dart` 의 본문을 Task 14 Step 6 과 같은 모양(중앙 정렬 + `readableMaxWidth`)으로 바꾼다.

- [ ] **Step 10: 테스트를 돌리고 200% 배율을 확인한다 (Review Focus 1·2)**

```dart
  testWidgets('설정: 200% 배율에서 행이 접히고 오버플로가 없다', (tester) async {
    await tester.pumpWidget(_app(
      size: const Size(390, 900),
      textScaler: const TextScaler.linear(2),
    ));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
```

Run: `cd apps/web && flutter test test/features/settings test/features/mypage`

Expected: PASS.

- [ ] **Step 11: analyze·format 하고 커밋한다**

```bash
cd apps/web && flutter analyze lib/src/features/settings lib/src/features/mypage lib/src/features/common
cd ../.. && dart format apps/web/lib/src/features/settings/presentation/settings_page.dart apps/web/lib/src/features/mypage/presentation/mypage_page.dart apps/web/lib/src/features/common/presentation/placeholder_page.dart
git add apps/web/lib/src/features/settings apps/web/lib/src/features/mypage apps/web/lib/src/features/common apps/web/test/features/settings apps/web/test/features/mypage
git commit -F - <<'MSG'
feat(web): 설정을 .narrow + .rowline 패널 3개로, 마이페이지를 .cols 로

- SwitchListTile·ListTile → DpRowLine, _header+Divider → DpPanel 제목
- 절 순서를 시안대로(알림 → 동의 관리 → 계정)
- 마이페이지: 활동 목록 ListTile → DpWebTable, 프로필 kv 사이드 패널
- CircularProgressIndicator → DpLoading, _errorView → SupportableError
- placeholder 는 시안 beta 문법에서 파생(중앙 narrow)

마이페이지 활동 표에 「작성」 칼럼을 넣지 않았다 — PostSummaryView 에 작성
시각이 없다(Task 8 실측과 같은 이유).

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
```

- [ ] **Step 12: 기준선 영향을 기록한다**

```markdown
- `/settings` 설정 — 절 순서 변경(알림이 맨 위로), 행 문법 교체, 폭 760.
- `/mypage` 마이페이지 — `.cols` 2열, 활동 목록 → 표, 프로필 kv 사이드 패널.
- `/placeholder` — 중앙 narrow.
```

---

## Task 18: PR-C 마무리 — 전 패키지 검증과 PR

**Files:** 코드 변경 없음.

- [ ] **Step 1: 변경 파일 목록을 확인한다**

Run: `git diff origin/develop HEAD --name-only`

Expected: `packages/dp_design/**`(Task 13) · `apps/web/lib/src/features/{auth,consent,beta,diagnostic,mypage,settings,common}/**` · `apps/web/test/**` 만.

- [ ] **Step 2: analyze·format·전 패키지 테스트**

Run:

```bash
cd packages/dp_design && flutter analyze && flutter test
cd ../../apps/web && flutter analyze && flutter test
cd ../admin && flutter analyze && flutter test
cd ../../packages/dp_core && flutter test
cd ../.. && dart format --output=none --set-exit-if-changed $(git diff origin/develop HEAD --name-only -- '*.dart')
```

Expected: analyze 0 · 전 패키지 PASS · format exit 0.

- [ ] **Step 3: 20화면 대조표를 한 번 훑는다**

계획 앞머리의 대조표 25줄(시안 20 + 파생 5)을 하나씩 열어 확인한다. **「구현하지 않음」으로 남긴 것이 `baseline-impact.md` 에 근거와 함께 적혀 있는지**가 판정 기준이다. 현재까지 남은 것:

- 오늘 화면의 과제 설명(`.ex`) — `WeeklyTask` 에 필드가 없다
- 오늘 화면의 「12주 중 N주차」 — 총 주차 수가 그 화면에 없다
- 커뮤니티 목록의 「작성」 칼럼·작성자 이름 — `PostSummaryView` 에 없다
- 질문 상세의 「이 주제 학습하기」 — 태그↔콘텐츠 매핑이 없다
- 마이페이지 활동 표의 「작성」 칼럼 — 위와 같은 이유

- [ ] **Step 4: PR 을 올린다**

```bash
git push -u origin feat/s3-p4-account-screens
gh pr create --base develop --title "feat(web): S3-P4c 계정·온보딩 화면군을 시안 웹 문법으로 재구성" --body-file - <<'BODY'
## 무엇

S3-P4 의 마지막 PR. 계정·온보딩 9화면(로그인·콜백·동의·베타·진단 3·마이페이지·설정·placeholder)을 시안의 웹 문법으로 재구성한다. 이것으로 **S3-P4 의 20화면 + 파생 5화면이 모두 끝난다.**

## 어떻게

- `dp_design`: 시안 온보딩 프리미티브 3종 신설 — `DpSteps`(진단 3화면)·`DpOptionRow`(진단 2화면)·`DpCheckRow`(동의)
- 로그인: 장식(그라디언트·원) 제거, 2열 경계 리터럴 900 → `DpWindowClass`, 페이지 헤더 → 패널 제목
- 동의: 폭 440 → 760, `CheckboxListTile` → `DpCheckRow`(라벨과 우측 링크가 갈라지지 않는다)
- 진단: 단계 표시 → `DpSteps`, 선택 → `DpOptionRow`, 「경로 만들기」 → `DpNextActionBand`
- 설정: `SwitchListTile`/`ListTile` → `DpRowLine` 패널 3개, 절 순서를 시안대로
- 마이페이지: `.cols` 2열, 활동 목록 → 표
- 콜백·베타·placeholder: 시안 `beta` 문법에서 파생한 중앙 `.narrow`

## 구현하지 않은 시안 요소 (전체 목록은 baseline-impact.md)

데이터가 없어 새 API/백엔드 계약이 필요한 것들이다: 오늘의 과제 설명·총 주차 수, 커뮤니티·마이페이지의 「작성」 칼럼과 작성자 이름, 질문 상세의 「이 주제 학습하기」.

## 검증

- analyze 0 · format 0 changed · 전 패키지 테스트 통과
- 390px 가로 넘침 없음 · 200% 배율 오버플로 없음
- `DpSteps` 현재 단계 대비를 라이트·다크 둘 다 측정

## 다음

P5(기준선 재기록) — `baseline-impact.md` 에 20화면의 렌더 변화를 누적했다. ET13 visual/a11y baseline 재승인은 사람 단계다.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
BODY
```

- [ ] **Step 5: CI 6잡 녹색을 확인한 뒤 머지한다**

Run: `gh pr checks --watch` 이어서 녹색이면 `gh pr merge --merge`

Expected: 전부 pass. `browser-ux` 가 깨지면 시나리오를 새 구조로 고친다(화면을 되돌리지 않는다).

- [ ] **Step 6: 핸드오프를 쓴다**

`documents` 레포에 `docs/superpowers/handoff-2026-XX-XX-s3-p4-screen-groups-merged.md` 를 쓴다. 담을 것:

- 세 PR 의 머지 커밋과 CI 시간
- 구현하지 않은 시안 요소 5건과 각각의 근거(데이터 없음 → 백엔드 계약 변경 필요)
- `baseline-impact.md` 전문(P5 의 입력이다)
- 실측이 계획을 뒤집은 것들(계획 본문의 Ruling 표를 갱신한 내역)
- **다음 착수점 = S3-P5(기준선 재기록)**

`documents` 레포는 CI 가 가벼우므로 교차 레포 핸드오프는 여기에 쓴다(사용자 지시 2026-09-17).

---

## Self-Review

**1. 스펙 커버리지** — 스펙 §7 P4 는 「화면군별 개편 3 PR: 학습(오늘·경로·콘텐츠·실습·멘토) / 커뮤니티 / 계정·온보딩(로그인·동의·진단·마이페이지·설정)」과 비고 「시안과 1:1 대조」다. 세 PR 이 그 셋이고(PR-A Task 2~6, PR-B Task 8~11, PR-C Task 14~17), 대조표가 시안 20화면 + 파생 5화면을 Task 에 배정했다. 스펙 §8 의 게이트(analyze-test·browser-ux·perf-gate·web-image-config-contract·produce-atomic-pair)는 각 PR 의 마무리 Task(7·12·18)가 확인한다. 스펙 §7 원칙 「시안에 없는 화면 요소를 즉흥으로 만들지 않는다」는 Global Constraints 의 파생 규칙이 각 파생 화면의 근거를 시안 화면에 묶어 이행한다. 빠진 항목 없음.

**2. 플레이스홀더** — 모든 코드 스텝에 실제 Dart 가 있다. 「적절히 처리」·「TODO」는 없다. 다만 **의도적으로 실측에 넘긴 곳이 6군데** 있고 모두 그 Task 의 Step 1 이 실측 명령과 「이 표를 갱신한다」는 지시를 함께 갖는다: Task 3 의 `MilestoneProgressCard` 소비처 · Task 11 의 자유글 태그 필드 유무와 수정 화면의 폼 재사용 여부 · Task 15 의 「전문 보기」 라우트 · Task 16 의 트랙·보기 선택 위젯과 개념별 점수 데이터 · Task 17 의 프로필 모델 필드와 활동 목록 출처. 이것들은 플레이스홀더가 아니라 **실측 지시**다 — 계획 단계에서 파일을 열어 확인할 수 있었으나, 그 값이 코드 모양을 바꾸지 않고 이름만 바꾸므로 실행자가 한 번의 grep 으로 정확히 맞추는 것이 싸다.

**3. 타입 일관성** — `DpCols({main, side, stretch})`·`DpSide({children})`·`DpPanelTitle(String)`·`DpWebTable({columns, rows, empty, minWidth})`·`DpSteps({labels, currentIndex})`·`DpOptionRow({label, selected, onSelect, description})`·`DpCheckRow({label, value, onChanged, description, trailing, last})` 가 정의된 Task(1·6·13)와 소비 Task(2~6·10·14~17) 에서 같은 이름·같은 필드로 쓰인다. `DpTableColumn`(`{label, width, numeric}`)·`DpTableRowSpec`(`{cells, onTap}`)·`DpKeyValue`(`{key, value}`)·`DpStatusTone`(`done`/`idle`/`current`)는 P3 이 정한 그대로다. `communityBoardColumns`/`communityPostRow`/`communitySearchRow`(Task 8)의 시그니처가 Task 8 안의 두 소비처에서 일치한다. `carryCommunityQuery({location, targetId})`(Task 9)는 셸 두 곳에서 같게 불린다.

**4. Review Focus** — 다섯 줄 각각에 소유 Task 의 테스트를 붙였다: ① 390px 가로 넘침 = Task 2 Step 19 · Task 3 Step 12 · Task 8 Step 9 · Task 10 Step 15 · Task 11 Step 8 · Task 16 Step 8 ② 200% 배율 = Task 2 Step 6 · Task 15 Step 8 · Task 17 Step 10 ③ 콘텐츠 진행률 보정 = Task 4 Step 1·10 ④ 표 행 시맨틱스 = Task 8 Step 2 의 마지막 테스트 ⑤ 상태 분기 도달 = Task 2 Step 18 · Task 3 Step 12 · Task 10 Step 15 · Task 16 Step 8.

**5. 실측이 계획을 만들며 이미 뒤집은 것 3건** (모두 본문에 반영됨)

- 「Material `Card(` 25곳」은 실재하지 않는다 — 7곳이고 모든 시점에서 같았다.
- 커뮤니티·마이페이지 목록의 「작성 시각」·작성자 이름은 **백엔드가 보내지 않는다**(`PostSummaryView` 8필드 확인). 시안과 1:1 이 될 수 없는 유일한 항목이다.
- `DpPageHeader` 의 좌우 패딩이 셸 패딩과 이중이었다 — 화면을 고치기 전에 프리미티브를 고쳐야 한다(Task 1).

---
