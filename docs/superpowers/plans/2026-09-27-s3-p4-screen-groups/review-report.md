# PR-C 독립 리뷰 보고

대상: `feat/s3-p4-account-screens` · `2c38bac..e8f66d6` (5커밋, 28파일) · Task 13~18
리뷰 방식: 3패스 — ① dp_design 신설 프리미티브 3종 + `DpLink` 변경 ② 9화면 diff 를 `2c38bac` 원본과 갈래별 대조 ③ 테스트 전량 실행 + 모델·라우터·토큰·Flutter SDK 실측
**소스 코드는 한 줄도 수정하지 않았습니다.**

## 요약

findings 개수: **Critical 0 · Important 7 · Minor 11**

판정: **Ready to merge = With fixes**

기능 손실 위험이 가장 컸던 세 지점(진단 `_primaryAction` 9갈래 · 동의 제출 payload · 신설 폼 프리미티브의 시각/상태 일치)은 원본과 직접 대조해 **손실 0** 을 확인했고 테스트도 전량 통과합니다(dp_design 377 · web 1109). 머지 전 닫아야 할 것은 사용자가 바로 겪는 3건(I1·I2·I3), 접근성 후퇴 1건(I4), P5 계약 2건(I5·I6), 그리고 PR-A 유래지만 이 PR 의 화면에서 드러나는 1건(I7)입니다.

---

## Critical

**없음.**

근거: 데이터 손실·보안·크래시·기능 파괴 경로를 찾지 못했습니다. 구체적으로 확인한 것 —

- 진단 결과 화면의 primary action 9갈래를 원본(`git show 2c38bac:apps/web/lib/src/features/diagnostic/presentation/diagnostic_page.dart:731-780`)과 한 갈래씩 대조 → 라벨 9개 전부 동일, 콜백 누락 0건, busy 게이팅 동등. 중복 제출 가능성 없음(§적대적 3 참조).
- 동의 제출 payload 가 UI 구조 변경과 무관(`consent_page.dart:127-130` 이 `_ConsentKind.values` 직접 순회).
- 5화면의 상태 분기 전부 보존 — 설정(Loading/Error/Ready), 마이페이지(Loading/Failed/Loaded + 부분실패 4문구), 동의(prefill loading/ConsentError/ConsentBlocked), 베타(pending/expired), 진단(busy/failure/legacy/`_LegacyPreview`).
- `flutter test` 전량 통과, `flutter analyze` 신규 이슈 0(§실행 기록).

---

## Important

### I1. 로그인 화면이 폭 상한을 잃어 넓은 모니터에서 전폭으로 퍼진다

- **위치**: `apps/web/lib/src/features/auth/presentation/login_page.dart:88-105` (보조 `:54-65`, `:67-86`)
- **실패 시나리오**: 1920px 모니터에서 `/login` 을 엽니다. `gutter = DpSpacing.xl`(좌우 24씩) + 칼럼 간 `SizedBox(DpSpacing.xxxl)`(48) → 로그인 패널 = `(1920 − 48 − 48) × 9/20 = 820.8px`, 스토리 칼럼 = `1003.2px`. 「GitHub로 계속하기」·「Google로 계속하기」 버튼이 **821px 폭으로 늘어나고** 스토리 본문(`bodyLarge`)이 1003px 한 줄로 깔립니다. 2560px 에서는 패널 **1108.8px**. 600~839(medium) 구간에서는 1열이지만 `CrossAxisAlignment.stretch` 라 패널이 **최대 791px** 까지 늘어납니다 — 원본은 이 구간에서 480px 중앙 정렬이었습니다.
- **근거**:
  ```dart
  // login_page.dart:88-99 — ConstrainedBox·DpMaxWidth 가 하나도 없다
  return Scaffold(
    body: SafeArea(
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            brandRow(context, actions: [themeToggle]),
            const SizedBox(height: DpSpacing.xxl),
            Padding(
              padding: EdgeInsets.symmetric(horizontal: gutter),
              child: layout,
  ```
  원본에는 캡이 있었습니다 — `git show 2c38bac:apps/web/lib/src/features/auth/presentation/login_page.dart` → `:92` `constraints: const BoxConstraints(maxWidth: 480)`, `:119` 동일.
  `/login` 이 셸 밖 bare 라우트여서 `contentMaxWidth` 를 줄 셸이 없음 — `apps/web/lib/src/app/router.dart:245` (`ShellRoute` 는 `:258` 부터).
  토큰에는 상한이 있음 — `packages/dp_design/lib/src/theme/dp_tokens.dart:28` `contentMaxWidth: 1120`.
  9화면 중 로그인만 본문에 상한이 없음 —
  ```
  $ grep -rn "ConstrainedBox\|maxWidth:" --include=*.dart \
      apps/web/lib/src/features/{auth,beta,consent,diagnostic,mypage,settings} \
      apps/web/lib/src/features/common/presentation/placeholder_page.dart
  auth/presentation/auth_callback_page.dart:93,96   readableMaxWidth
  auth/presentation/login_page.dart:189,190         readableMaxWidth  ← _LoginSessionCheck 전용
  beta/presentation/beta_pending_page.dart:81,84    readableMaxWidth
  consent/presentation/consent_page.dart:179,184    readableMaxWidth
  consent/presentation/consent_page.dart:331,335    readableMaxWidth
  diagnostic/presentation/diagnostic_page.dart:58,60 readableMaxWidth
  settings/presentation/settings_page.dart:78,81    readableMaxWidth
  common/presentation/placeholder_page.dart:15,17   readableMaxWidth
  ```
  → 로그인 페이지 **본문**에 해당하는 항목이 없습니다.
- **고치는 방법**: `layout` 을 `Center(child: ConstrainedBox(maxWidth: context.appTokens.contentMaxWidth, …))` 로 감싸고, 1열 분기의 `access` 는 `readableMaxWidth`(또는 시안 `.panel.signin` 폭)로 따로 묶습니다.

### I2. `DpCheckRow` 의 `trailing` 이 200% 배율에서 라벨을 몇 글자 폭으로 짜부순다

- **위치**: `packages/dp_design/lib/src/interaction/dp_check_row.dart:113-155` (특히 `:150-153`)
- **실패 시나리오**: 390px 폭 + 200% 배율로 `/consent` 를 엽니다. 행 내부 폭 ≈ `390 − 24×2(페이지 패딩) − 1×2(패널 테두리) − 16×2(행 패딩) = 308px`. non-flex 자식이 먼저 확정됩니다 — Checkbox(compact) ~36 + 간격 8 + 8 + `DpTag('필수')`(fontSize 12 × 2배 = 24px 글자 2자 + 좌우 8×2 ≈ 64) + `DpLink.inline('전문 보기')`(bodyMedium 14 × 2배, 4자+공백 ≈ 130) ≈ **246px**. 남은 **~54px** 안에서 `Flexible(Text('개인정보 수집·이용 동의'))` 가 줄바꿈해 **줄당 약 2글자, 6줄** 로 쌓입니다. RenderFlex 오버플로 예외는 나지 않으므로 신설 테스트의 `expect(tester.takeException(), isNull)` 이 **통과합니다** — 그 단언이 이 결함을 볼 수 없습니다. 400% 배율이면 non-flex 합이 가용 폭을 넘어 실제 오버플로로 넘어갑니다.
- **근거**:
  ```dart
  // dp_check_row.dart:113-153 — 최외곽이 Wrap 이 아니라 Row, trailing 이 non-flex
  child: Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Expanded(child: MergeSemantics(child: Semantics(... inner ...))),
      if (widget.trailing != null) ...[
        const SizedBox(width: DpSpacing.sm),
        widget.trailing!,          // ← non-flex: 주축 무한 제약으로 측정된다
      ],
    ],
  ),
  ```
  Flutter `RenderFlex` 는 수평 방향 non-flex 자식을 `BoxConstraints(maxHeight: …)` 로만 묶어 **주축(폭)은 무한** 으로 측정합니다. 이 레포가 그 함정을 이미 문서화해 뒀습니다 — `apps/web/lib/src/features/common/presentation/brand_row.dart:21-23`:
  > `// Flexible로 감싼다 — Spacer(Expanded)와 같은 Row의 non-flex 자식은`
  > `// 무한 주축 제약으로 측정되어 ellipsis가 발동하지 않고 오버플로한다.`

  그리고 P3 의 `DpRowLine` 은 **정확히 이 문제** 를 `Wrap` 으로 풀었습니다 — `packages/dp_design/lib/src/data/dp_row_line.dart:8-9`:
  > `/// 좌측 라벨(600) + 선택적 설명(13px 보조색), 우측 컨트롤. 좁은 폭에서는`
  > `/// Wrap 이 컨트롤을 아래 줄로 내린다 — Row 로 두면 390px 에서 넘친다.`

  `DpLink` 는 `maxLines: null` 이라 줄바꿈 자체는 가능하지만(`packages/dp_design/lib/src/content/dp_link.dart:88-93`) 무한 주축 제약 때문에 한 줄로 펴집니다.
  토큰: `dp_spacing.dart:6-12`(`xs=4 sm=8 md=12 lg=16`), `dp_tag.dart:23-37`(`fontSize: 12`, 좌우 `DpSpacing.sm`).
  테스트의 약한 단언: `apps/web/test/features/consent/consent_page_test.dart` 의 `동의: 390px · 200% 배율에서 체크 행이 깨지지 않는다` = `expect(tester.takeException(), isNull)` + `findsNWidgets(5)`.
- **근거의 성격**: 폭 수치는 프레임워크 동작(RenderFlex non-flex 측정)과 토큰값에서 **유도** 했습니다. 워킹트리 변경 금지라 프로브 테스트로 픽셀을 재지 못했습니다 — 구조적 원인은 확정, 수치는 추정입니다.
- **고치는 방법**: `DpRowLine` 처럼 최외곽을 `Wrap` 으로 바꾸거나, compact 에서 `trailing` 을 라벨 아래 줄로 내립니다.

### I3. 설정 화면이 원시 ISO-8601 타임스탬프를 사용자 문구로 그린다

- **위치**: `apps/web/lib/src/features/settings/presentation/settings_page.dart:189`
- **실패 시나리오**: 동의 이력이 있는 사용자가 `/settings` → 「동의 관리」 패널을 봅니다. 「서비스 이용약관」 행 설명에 **`2026-07-01T09:00:00Z 동의`** 가 그대로 표시됩니다. 원본에는 이 자리에 `'필수'`/`'선택'` 만 있었습니다.
- **근거**:
  ```dart
  // settings_page.dart:189
  description: agreedAt == null ? null : Text('$agreedAt 동의'),
  ```
  타입이 포맷을 보장하지 않는 원시 문자열 — `apps/web/lib/src/features/settings/data/settings_models.dart:42` `final String? agreedAt;` · `:49` `agreedAt: json['agreedAt'] as String?`.
  형식은 목 픽스처가 확정 — `apps/web/lib/src/data/web_mock_fixtures.dart:118` `'agreedAt': '2026-07-01T09:00:00Z',` (`:124` 동일, `:130` null).
  레포에 포매터가 없음 —
  ```
  $ grep -rn "formatKoreanDate\|DateFormat\|intl\|formatDate" --include=*.dart \
      apps/web/lib packages/dp_core/lib packages/dp_design/lib
  packages/dp_core/lib/src/models/sandbox.dart:28: '    System.out.println("Hello, Leva!");\n'   ← 무관
  ```
  원본: `git show 2c38bac:apps/web/lib/src/features/settings/presentation/settings_page.dart` → `subtitle: const Text('필수')` / `subtitle: const Text('선택')`.
- **테스트가 못 잡는 이유**: 신설 `apps/web/test/features/settings/settings_rowline_test.dart:17-19` 픽스처가 `agreedAt` 을 넘기지 않아(기본 null) 이 경로가 한 번도 실행되지 않습니다.
- **고치는 방법**: `DateTime.tryParse` → `yyyy.MM.dd` 로 포맷하고 파싱 실패 시 설명을 생략합니다.

### I4. 「누르면 즉시 제출」인 문항 보기가 라디오를 선언하고, radiogroup 이 약속하는 키보드 계약이 비어 있다

- **위치**: `apps/web/lib/src/features/diagnostic/presentation/diagnostic_page.dart:464-491`(문항) · `:297-317`(트랙) · `packages/dp_design/lib/src/interaction/dp_option_row.dart:109-139`
- **실패 시나리오** (둘):
  - *스크린리더*: 진단 문항 화면에서 보기 4개가 「라디오, 선택 안 됨」으로 읽힙니다. Enter 로 활성화하면 `checked` 상태 변화 대신 `submitAnswer` 가 실행돼 문항 전체가 교체됩니다. 정상 흐름에서 `selected` 가 true 가 되는 경우는 **답변 저장 실패 시뿐** 이므로, 「라디오 그룹인데 아무것도 선택되지 않은 상태」가 정상입니다.
  - *키보드*: 진단 시작 화면에서 Tab 을 누릅니다. 트랙이 **8개** 라 「진단 시작하기」 버튼에 닿기까지 **Tab 8번** 이 필요하고, 「진단할 트랙 라디오 그룹」이라고 들은 뒤 ↓/→ 를 눌러도 아무 일도 일어나지 않습니다.
- **근거**:
  ```dart
  // diagnostic_page.dart:464-491 — 즉시 제출인데 radiogroup + radio
  Semantics(
    container: true,
    role: SemanticsRole.radioGroup,
    label: '보기',
    child: Column(children: [
      for (var index = 0; index < options.length; index++) ...[
        DpOptionRow(
          selected: answerFailed && selectedOptionIndex == index,   // ← 실패 시에만 true
          onSelect: busy || answerFailed ? null
              : () => notifier.submitAnswer(question.id, '{"correct":$index}', timeSpentSec: 5),
  ```
  원본은 버튼이었고 그것이 정확했습니다 — `git show 2c38bac:…/diagnostic_page.dart` → `OutlinedButton(key: …, onPressed: busy || answerFailed ? null : () => notifier.submitAnswer(...))`.
  `DpOptionRow` 가 역할을 하드코딩 — `dp_option_row.dart:109-114`:
  ```dart
  return MergeSemantics(
    child: Semantics(
      inMutuallyExclusiveGroup: true,
      checked: selected,
      enabled: enabled,
      onTap: onSelect,
  ```
  Flutter 자신의 `RadioGroup` 은 그 역할과 **함께** 화살표 순회와 단일 탭 정지를 줍니다 — 로컬 SDK 실측(`/c/tools/flutter`, Flutter 3.47.2):
  ```dart
  // packages/flutter/lib/src/widgets/radio_group.dart:90-96
  late final Map<ShortcutActivator, Intent> _radioGroupShortcuts = <ShortcutActivator, Intent>{
    const SingleActivator(LogicalKeyboardKey.arrowLeft):  VoidCallbackIntent(_selectPreviousRadio),
    const SingleActivator(LogicalKeyboardKey.arrowRight): VoidCallbackIntent(_selectNextRadio),
    const SingleActivator(LogicalKeyboardKey.arrowDown):  VoidCallbackIntent(_selectNextRadio),
    const SingleActivator(LogicalKeyboardKey.arrowUp):    VoidCallbackIntent(_selectPreviousRadio),
    const SingleActivator(LogicalKeyboardKey.space):      VoidCallbackIntent(_toggleFocusedRadio),
  };
  // :214-220
  return Semantics(container: true, role: SemanticsRole.radioGroup,
    child: Shortcuts.manager(manager: _radioGroupShortcutManager,
      child: FocusTraversalGroup(policy: _SkipUnselectedRadioPolicy<T>(_radios, widget.groupValue),
  ```
  이 구현에는 `Shortcuts` 도 `FocusTraversalGroup` 도 없습니다.
  트랙 8개 — `apps/web/lib/src/features/common/application/track_catalog.dart:13-22` (`BACKEND_SPRING`·`FRONTEND_REACT`·`MOBILE_FLUTTER`·`DEVOPS`·`FULLSTACK`·`PYTHON_BACKEND`·`NODE_TYPESCRIPT`·`DATA_AI`).
- **고치는 방법**: `DpOptionRow` 에 역할 파라미터를 추가해 문항 보기는 `button: true` 로 두고(역할 정직성), 트랙 그룹에는 `FocusTraversalGroup` + 화살표 `Shortcuts` 를 얹거나 `RadioGroup` 을 씁니다.

### I5. `baseline-impact.md` 가 여전히 비어 있다 — Task 18 Step 3 의 합격 기준 미충족

- **위치**: `D:/workspace/dpa/.worktrees/documents-s3p4-plan/docs/superpowers/plans/2026-09-27-s3-p4-screen-groups/baseline-impact.md:7`
- **실패 시나리오**: P5(기준선 재기록) 담당자가 이 파일을 열어 ET13 visual/a11y baseline 재기록 대상을 정하려 합니다. 「렌더가 바뀐 화면」 절이 플레이스홀더 한 줄뿐이라 **20화면 중 무엇이 바뀌었는지 알 수 없습니다.** 실제 내역은 세 워크트리의 git-ignored `progress.md` 안에만 있고, PR-C 가 새로 만든 「구현하지 않은 시안 요소」 4건(`dresult` 의 `.bars` · `mypage` 활동 표 · `mypage` 프로필 사이드 kv · 프로필 표시 이름)도 표에 반영되지 않았습니다.
- **근거**:
  ```markdown
  ## 렌더가 바뀐 화면

  (Task 2·3·4·5·6·8·10·11·14·15·16·17 이 각자 한 줄씩 추가한다)
  ```
  파일 mtime 이 PR-C 착수 전 —
  ```
  $ ls -la .../2026-09-27-s3-p4-screen-groups/
  -rw-r--r-- 3458 Sep 27 16:03 baseline-impact.md
  $ ls -la .superpowers/sdd/2026-09-27-s3-p4-screen-groups/ | grep t1[3-8]
  Sep 28 09:35  t13-steps-red.log   …   Sep 28 11:04 (progress.md)
  ```
  계획의 합격 기준 — `docs/superpowers/plans/2026-09-27-s3-p4-screen-groups.md` Task 18 Step 3: 「**「구현하지 않음」으로 남긴 것이 `baseline-impact.md` 에 근거와 함께 적혀 있는지** 가 판정 기준이다」.
- **고치는 방법**: 세 PR 의 Ruling 기록(각 `progress.md` 의 「기준선 영향」 절)을 이 파일로 옮긴 뒤 머지합니다(documents 레포 PR).

### I6. 원장의 기준선 영향 기록이 틀렸다 — 2열 경계는 1240 이 아니라 840 이다

- **위치**: `.superpowers/sdd/2026-09-27-s3-p4-screen-groups/progress.md` Task 14 「기록: 기준선 영향」 절 — 「`/login`: … **2열 경계 900 → 1240**」 (계획 Task 14 Step 2 의 테스트 제목 「1240 이상에서 …」도 같은 오기)
- **실패 시나리오**: P5 담당자가 이 기록을 받아 1240 근처에서 렌더 변화를 찾습니다. 그런데 1240 에서는 구·신 모두 2열이라 **차이가 없습니다**. 실제로 뒤집히는 구간은 **840~899**(구: 1열 480 중앙 / 신: 2열)이고, ET13 기준선 폭(320/390/1240/1360) 어디에도 걸리지 않아 눈에 보이는 가장 큰 변화가 기준선에서 누락됩니다.
- **근거**:
  ```dart
  // packages/dp_design/lib/src/layout/dp_window_class.dart:6-11
  DpWindowClass dpWindowClassOf(double width) {
    if (width < 600) return DpWindowClass.compact;
    if (width < 840) return DpWindowClass.medium;
    if (width < 1240) return DpWindowClass.expanded;   // ← expanded = 840..1239
    return DpWindowClass.large;
  }
  ```
  ```dart
  // login_page.dart:55-58 — expanded 부터 2열 = 840
  final twoColumn = switch (windowClass) {
    DpWindowClass.expanded || DpWindowClass.large => true,
    DpWindowClass.compact  || DpWindowClass.medium => false,
  };
  ```
  구 경계: `git show 2c38bac:…/login_page.dart:51` → `final compact = constraints.maxWidth < 900;`
  **구현은 계획대로입니다**(계획 Ruling: 「medium 이하에서 1열」). 구현자는 테스트 제목도 바르게 고쳤습니다(`login_page_test.dart` 「로그인: **expanded 이상** 에서 … 2열」) — 틀린 것은 원장 기록과 계획 Step 2 제목입니다.
- **참고(이 diff 밖)**: 같은 오해의 진원지가 `packages/dp_design/lib/src/layout/dp_cols.dart:10-12` 주석입니다 — 「경계를 `DpWindowClass.expanded`(**1240**) 에 두는 이유: … 840~1239 에서 사이드가 약 270px 까지 눌린다」. 코드는 그 840~1239 를 2열로 만들므로 주석이 자기모순입니다. PR-A 산출물이라 수정 대상은 아니나 함께 바로잡는 것이 좋습니다.
- **고치는 방법**: `baseline-impact.md` 로 옮길 때 「900 → 840(`DpWindowClass.expanded`)」로 정정하고, 실제 변화 구간 840~899 를 명시합니다.

### I7. `/consent`·`/diagnostic` 의 페이지 헤더가 좌측 여백 0 으로 화면 끝에 붙는다 (PR-A 유래, PR-C 의 화면)

- **위치**: `apps/web/lib/src/features/consent/presentation/consent_page.dart:190-198` · `apps/web/lib/src/features/diagnostic/presentation/diagnostic_page.dart:66-79` · `packages/dp_design/lib/src/layout/dp_page_header.dart:45-52`
- **실패 시나리오**: 390px 폭으로 `/consent` 를 엽니다. 한 화면에 좌측 정렬선이 **셋** 생깁니다 — Leva 로고 x=16 · 「가입 전 동의」 제목·설명 **x=0(화면 끝에 붙음)** · 동의 패널 x=24. `/diagnostic` 의 「실력 진단」도 같습니다. PR-C 의 390px 테스트는 `second.right <= viewport.right` 만 보므로 이것을 보지 못합니다.
- **근거**:
  ```dart
  // dp_page_header.dart:45-52 — gutter:false(기본값) 면 좌우 0
  return Padding(
    padding: EdgeInsets.fromLTRB(
      gutter ? (compact ? DpSpacing.lg : DpSpacing.xl) : 0,
      compact ? DpSpacing.xl : DpSpacing.xxl,
      gutter ? (compact ? DpSpacing.lg : DpSpacing.xl) : 0,
      DpSpacing.lg,
    ),
  ```
  호출부가 `gutter` 를 넘기지 않음 — `consent_page.dart:191-196`, `diagnostic_page.dart:67-72`.
  형제들은 각자 다른 패딩 — `brandRow`: `apps/web/lib/src/features/common/presentation/brand_row.dart:11-16` `EdgeInsets.fromLTRB(DpSpacing.lg, DpSpacing.lg, DpSpacing.lg, 0)` = 좌 16 / 본문: `consent_page.dart:198` `EdgeInsets.symmetric(horizontal: DpSpacing.xl)` = 24, `diagnostic_page.dart:74-79` `fromLTRB(DpSpacing.xl, 0, DpSpacing.xl, DpSpacing.xl)` = 24.
  두 화면이 셸 밖 — `apps/web/lib/src/app/router.dart:250-251`(`ShellRoute` 는 `:258` 부터).
- **이 브랜치 유래가 아닙니다**: `git diff 2c38bac..e8f66d6 -- packages/dp_design/lib/src/layout/dp_page_header.dart` → 변경 없음. base 원본도 같은 모양(`git show 2c38bac:…/consent_page.dart:178-186`). PR-A Task 1 이 `gutter` 기본값을 뒤집으면서 bare 라우트 호출부를 갱신하지 않은 결과입니다. 다만 PR-C 가 이 두 화면의 「재구성」 담당이고 Review Focus 1(390px)의 소유자이므로 여기서 닫는 것이 맞습니다.
- **고치는 방법**: 두 호출부에 `gutter: true` 를 주거나, 헤더를 본문과 같은 `Padding` 안으로 넣습니다.

---

## Minor

### M1. `DpSteps` 의 단계가 서로 다른 높이를 가질 수 있다 (시안 CSS 와 불일치)

- **위치**: `packages/dp_design/lib/src/layout/dp_steps.dart:48`
- **실패 시나리오**: 배율이나 폭 때문에 세 라벨 중 하나만 줄바꿈하면(예: '1 트랙 선택' 2줄, '3 학습 경로' 1줄) 짧은 단계의 오른쪽 세로 구분선이 띠 높이를 못 채우고, 현재 단계의 `accentSoft` 배경이 위아래로 잘려 보입니다.
- **근거**: `Row(children: [for (final item in items) Expanded(child: item)])` — `crossAxisAlignment` 미지정이라 Flutter 기본값 `center`. 시안 `.steps{display:flex}` 는 CSS 기본 `align-items: stretch` 라 모든 단계가 같은 높이입니다. `_Step` 의 배경·구분선은 자기 `Container` 높이에만 그려집니다(`:69-84`). `CrossAxisAlignment.stretch` 또는 `IntrinsicHeight` 로 닫힙니다.

### M2. 보이는 필드 라벨 '진단할 트랙' 이 사라졌다

- **위치**: `apps/web/lib/src/features/diagnostic/presentation/diagnostic_page.dart:300-304`
- **실패 시나리오**: 시각 사용자가 진단 시작 화면을 봅니다. 8개 보기 행 위에 그룹 제목이 없고 설명 문장('선택한 트랙이 문항과 이후 학습 경로의 기준이 됩니다.')만 있습니다.
- **근거**: 원본은 `DropdownButtonFormField(decoration: const InputDecoration(labelText: '진단할 트랙', hintText: '트랙을 선택하세요'))` 로 **보이는** 라벨(`git show 2c38bac:…:300-307`). 새 코드는 `Semantics(key: ValueKey('diagnostic-track'), container: true, role: SemanticsRole.radioGroup, label: '진단할 트랙')` — 시맨틱스 전용입니다.

### M3. `PlaceholderPage` 는 레포 전체에 소비처가 0곳 — 죽은 코드를 고쳤다

- **위치**: `apps/web/lib/src/features/common/presentation/placeholder_page.dart:12-23`
- **실패 시나리오**: 없음(렌더되지 않음). 다만 Task 17 Step 9 의 변경이 검증 불가이고, 계획 대조표가 실재하지 않는 화면 한 줄을 잡고 있었다는 뜻입니다.
- **근거**:
  ```
  $ grep -rn "PlaceholderPage\|placeholder_page" --include=*.dart .
  ./apps/web/lib/src/features/common/presentation/placeholder_page.dart:8:class PlaceholderPage extends StatelessWidget {
  ./apps/web/lib/src/features/common/presentation/placeholder_page.dart:9:  const PlaceholderPage({super.key, required this.title, required this.icon});
  ```
  선언 2줄뿐 — 라우터·테스트 어디서도 호출하지 않습니다.

### M4. 테스트 헬퍼가 `textScaler` 인자를 무시한다

- **위치**: `apps/web/test/features/settings/settings_rowline_test.dart:37-45`
- **실패 시나리오**: 다음 작업자가 `textScaler: const TextScaler.linear(3)` 을 넘겨 300% 를 검증했다고 믿지만 실제로는 2 가 적용됩니다.
- **근거**:
  ```dart
  Widget _app(WidgetTester tester, {Size size = const Size(1280, 2400), TextScaler? textScaler}) {
    …
    if (textScaler != null) {
      tester.platformDispatcher.textScaleFactorTestValue = 2;   // ← 인자 값을 쓰지 않는다
  ```

### M5. 대비 테스트가 실재하지 않는 색 조합을 잰다

- **위치**: `packages/dp_design/test/theme/dp_colors_contrast_test.dart` (신설 테스트의 두 번째 단언) · 구현 `packages/dp_design/lib/src/layout/dp_steps.dart:75`
- **실패 시나리오**: 없음(해는 없음). 다만 토큰을 바꿀 때 실제 계약을 지키지 못합니다.
- **근거**: 테스트는 `contrast(p.textSecondary, p.accentSoft)` 를 재지만, 구현에서 비현재 단계 배경은 `color: current ? c.accentSoft : null` → null 이므로 바깥 컨테이너의 `c.surface`(`:37`)입니다. 실제 계약은 `textSecondary`/`surface` 입니다. (현재 단계 조합 `primaryTextStrong`/`accentSoft` 는 올바릅니다.)

### M6. 마이페이지 `.prof` 의 정보 처리 3건

- **위치**: `apps/web/lib/src/features/mypage/presentation/mypage_page.dart:152-190`
- **(a) 아바타 설명 문구 삭제** — 실패 시나리오: 아바타 유무를 알 방법이 없습니다(`CircleAvatar` 는 시맨틱스 라벨도 없음). 근거: 원본 `Text(p.avatar == null ? '프로필 사진 없음' : '프로필 사진')`(`git show 2c38bac:…:152-160`)이 삭제됐습니다.
- **(b) 500자 소개가 제목 자리에 무제한 렌더** — 실패 시나리오: 소개를 길게 쓴 사용자의 마이페이지 머리에 500자가 `titleMedium` 6~8줄 단락으로 깔려 아래 폼을 밀어냅니다. 근거: `:168` `(p.bio?.isNotEmpty ?? false) ? p.bio! : '소개가 아직 없어요'` 에 `maxLines` 가 없고, 편집 폼은 `maxLength: 500` 입니다.
- **(c) 태그가 아래 폼과 중복 + Ruling 논리 불일치** — 근거: `:179-185` 의 `DpTag`(트랙·목표·경력) 3개가 바로 아래 편집 폼의 같은 3필드를 반복합니다. 원장 Ruling 은 「프로필 kv 사이드 패널은 같은 값을 두 번 보이니 만들지 않았다」고 적었는데, 같은 중복을 태그로 만든 셈입니다.

### M7. 비활성 밴드가 사용자가 실행할 수 없는 결과를 약속한다

- **위치**: `apps/web/lib/src/features/diagnostic/presentation/diagnostic_page.dart:704-711`
- **실패 시나리오**: `saved && pathBranch == unknown` 상태의 결과 화면에서 스크린리더가 「경로 상태 확인 필요, 예상 결과: **경로 상태를 확인하면 학습 경로로 넘어갈 수 있습니다.**」를 읽습니다. 그런데 `state: disabled` 이고 `onPressed` 가 없어 누를 수 없습니다.
- **근거**: `state: busy ? DpNextActionState.pending : DpNextActionState.disabled` + `onPressed` 미전달. 접근성 이름 조립: `packages/dp_design/lib/src/mission/dp_next_action_band.dart:204` `'$displayedLabel, 예상 결과: ${widget.expectedOutcome}'`. 원본은 비활성 버튼 문구 하나였습니다(`git show 2c38bac:…:744-748`).

### M8. `DpNextActionBand` 가 `boxShadow` 를 갖는다 — Global Constraints 위반 (계획 지시 결과)

- **위치**: `packages/dp_design/lib/src/mission/dp_next_action_band.dart:86-92`
- **실패 시나리오**: 진단 결과 화면에만 그림자가 있는 면이 생겨 시안(테두리 한 겹)과 어긋납니다.
- **근거**: `boxShadow: [BoxShadow(color: context.dpColors.textPrimary.withValues(alpha: 0.04), blurRadius: 24, offset: const Offset(0, 8))]`. Global Constraints: 「그림자를 쓰지 않는다 — 시안의 면 구분은 1px 테두리 한 겹뿐이다」. 계획 Task 16 Ruling 이 이 위젯을 쓰라고 지시했으므로 구현 잘못은 아니고 **P5 이월 항목** 입니다(PR-A 의 `.next` 도 같은 위젯).

### M9. 진단 시작 화면이 폰에서 CTA 를 화면 1.5장 아래로 밀고, 테스트가 그 깊이를 재지 않는다

- **위치**: `apps/web/test/features/diagnostic/diagnostic_page_test.dart`(`tallView` = `Size(1200, 2400)`, 390px 테스트 = `Size(390, 2400)`) · `apps/web/test/golden_path_onboarding_test.dart`(`ensureVisible` 5곳)
- **실패 시나리오**: 390×844 폰에서 `/diagnostic` 을 엽니다. brandRow(~56) + 페이지 헤더(~80) + `DpSteps` compact 세로 3행(~108) + 개요 + `DpKeyValues` 패널 + 보기 행 8개(~416) 를 지나야 「진단 시작하기」 에 닿습니다 — 약 1.5화면 스크롤. 원본은 드롭다운 1개였습니다.
- **판정/근거**: 키운 뷰포트·`ensureVisible` 자체는 **정당** 합니다 — 화면이 `SingleChildScrollView`(`diagnostic_page.dart:56-57`) 안이라 실제 사용자도 스크롤로 도달하고 `ensureVisible` 은 그 스크롤을 충실히 재현합니다. 결함 은폐가 아닙니다. 다만 실제 폰 높이(844)에서의 스크롤 깊이를 재는 단언이 없어 회귀가 조용히 커질 수 있습니다. 트랙 8개: `track_catalog.dart:13-22`.

### M10. 잔여 잡티 3건

- **옵션 목록 마지막 뒤 여분 간격** — `diagnostic_page.dart:486`, `:314`: `for (…) ...[DpOptionRow(…), const SizedBox(height: DpSpacing.sm)]` 이라 마지막 행 뒤에도 8px 이 붙습니다.
- **베타 화면이 세로 중앙 정렬을 잃음** — `apps/web/lib/src/features/beta/presentation/beta_pending_page.dart:68-70`: 원본 `Center(child: SingleChildScrollView(…))`(`git show 2c38bac:…:68-69`) → 신 `SafeArea(child: SingleChildScrollView(child: Column(…)))`. 가로 중앙 정렬만 남고 내용이 상단에 붙습니다.
- **'저장 후' 조건 문구 소실** — `diagnostic_page.dart:640-645`: 원본 「**저장 후** 이 결과를 기준으로 첫 주 경로와 오늘의 미션을 구성합니다.」 → 신 `(key: '다음 단계', value: Text('첫 주 경로와 오늘의 미션 구성'))`. 미저장 게스트에게 저장이 선행 조건임을 알리던 문구입니다(헤더의 '로그인 전에 결과를 먼저 확인하세요.' 가 일부 대체).

### M11. 탭 정지 개수를 고정하는 테스트가 없다

- **위치**: `packages/dp_design/test/interaction/dp_check_row_test.dart:242-248` · `dp_option_row_test.dart:91-97`
- **실패 시나리오**: 누군가 `ExcludeFocus` 를 제거해 Checkbox 가 다시 별도 탭 정지를 갖게 되어도(같은 항목에 두 번 멈춤) 테스트가 통과합니다.
- **근거**: 두 테스트 모두 `expect(FocusManager.instance.primaryFocus?.context?.widget, isNot(isA<FocusScope>()))` 즉 「포커스가 들어왔다」만 단언합니다. Tab 을 두 번 눌러 포커스가 행을 떠나는지 단언하면 원장 Ruling 의 계약이 고정됩니다.

---

## Declined to judge

확인하지 못한 것과 그 이유입니다. 하나도 묵살하지 않았습니다.

1. **Flutter Web 의 실제 ARIA 매핑과 axe 결과** — `inMutuallyExclusiveGroup` → `role="radio"`, `SemanticsRole.radioGroup` → `role="radiogroup"`, `isSelected` → `aria-selected` 가 axe `aria-required-parent`·`aria-allowed-attr`·`aria-input-field-name` 을 통과하는지. **이유**: 웹 엔진 소스가 로컬 SDK 에 없습니다(`grep -rn radioGroup bin/cache/pkg/sky_engine/lib/ui/semantics.dart` → enum 선언 `:500` 만). CI `browser-ux` 만이 답입니다(원장도 같은 결론). 참고: `DpSteps` 의 `Semantics(selected:)` 노드 모양은 원본 `_JourneyStep` 과 같고 그때 browser-ux 가 17/17 이었으므로 위험은 낮습니다.
2. **CI 핀 Flutter 3.44.1 에 `SemanticsRole.radioGroup` 이 존재하는지** — **이유**: 로컬은 3.47.2(`flutter --version` → `Flutter 3.47.2 • revision d3b14c8769`). `dp_loading.dart:1` 이 `SemanticsRole.status` 를 쓰므로 enum 과 `Semantics.role` 파라미터는 CI 에도 있으나, `radioGroup` 값 자체는 3.44.1 을 실행하지 않고는 단정할 수 없습니다. 컴파일 실패면 CI 가 즉시 드러냅니다.
3. **I2 의 픽셀 수치** — **이유**: 워킹트리 변경 금지 지시와 `code-reviewer.md` 의 read-only 규칙 때문에 프로브 테스트 파일을 만들 수 없었고, 레포 밖 경로에서는 `package:flutter_test` 가 해석되지 않아 외부 실행도 불가했습니다. 구조적 원인(RenderFlex non-flex 무한 주축 측정)은 SDK·레포 주석으로 확정, 수치는 토큰값 기반 유도입니다.
4. **`dp_cols.dart:10-12` 주석의 자기모순** — **이유**: PR-A 산출물이고 이 diff(`git diff 2c38bac..e8f66d6 --name-only`)에 없습니다. I6 에 참고로만 기록했습니다.
5. **CI 4잡 결과**(`browser-ux`·`perf-gate`·`produce-atomic-pair`·`web-image-config-contract`) — **이유**: 로컬에서 웹 빌드·Playwright 를 돌리지 않았습니다(리뷰 범위를 코드·테스트로 한정).
6. **시안 `.steps li` 가 `flex:1` 인지**(등폭 여부) — **이유**: Artifact `DWi8kMV6QcAzBEQwbrNPNd` 를 열지 않았습니다. 계획 본문 발췌(`display:flex;border;border-radius;overflow:hidden`)에 `flex` 선언이 없습니다. M1 은 `align-items` 기본값만 근거로 삼았습니다.
7. **`apps/admin` 156 · `packages/dp_core` 174 테스트** — **이유**: 이 diff 가 admin·dp_core 파일을 전혀 건드리지 않음을 파일 목록으로 확인했고(§실행 기록), 영향받는 두 패키지(`dp_design`·`apps/web`)는 직접 실행했습니다.
8. **`test/golden/state_golden_test.dart` 의 `DpKillSwitch` 골든 2건** — **이유**: 원장이 「이 PC 에서 100% 픽셀 차로 실패하고 내 변경과 무관함을 배럴 되돌림으로 실측했다」고 적었습니다. 저는 CI 와 같게 `--exclude-tags golden` 으로 돌려 재현하지 않았습니다.
9. **`/consent` 「전문 보기」가 실제로 새 탭을 여는지** — **이유**: `externalLinkOpenerProvider` 를 실행하지 않았습니다. 기존 테스트가 `consent-privacy-doc` 키로 통과하므로 배선 보존만 확인했습니다.
10. **`p.bio` 가 저장 후 즉시 갱신되는지**(M6b 인접) — **이유**: `myPageControllerProvider.saveProfile` 이후의 상태 재적재 경로를 따라가지 않았습니다. 표시가 서버값(`p.bio`), 편집이 로컬 컨트롤러(`_bio`)로 갈라져 있는 것은 의도로 보입니다.

---

## 적대적 검증 8개 지점별 결론

**1. `DpOptionRow`·`DpCheckRow` 키보드·시맨틱스 설계 → 부분 문제 (I4 · M11)**
라벨 오염 **없음** — `MergeSemantics` 가 라벨+설명을 한 노드로 묶고 빈 조각을 만들지 않습니다(테스트가 `isSemantics(isInMutuallyExclusiveGroup: true, hasCheckedState: true, isChecked: true)` 로 고정). 잠금 상태 **정확** — `FocusableActionDetector(enabled: false)` 로 포커스 순회에서 빠지고 `isSemantics(hasEnabledState: true, isEnabled: false)` 가 고정됩니다(`dp_option_row_test.dart:104-137`). `FocusableActionDetector` 로 옮긴 판정은 옳습니다(브리프의 `MouseRegion`+`GestureDetector` 로는 Tab 이 건너뜁니다 — P3 `DpLink` 실측과 같은 결함). 탭 정지는 행당 1개로 올바르나 **트랙 그룹 8개 = 탭 정지 8개 + 화살표 순회 부재 → I4**, 개수를 고정하는 테스트 부재 → M11.

**2. `DpCheckRow` 의 Checkbox 래핑(`IgnorePointer`+`ExcludeFocus`+`ExcludeSemantics`) → 문제 없음**
시각과 상태가 어긋날 경로가 **구조적으로 없습니다** — Checkbox 의 `value`(`dp_check_row.dart:68`)와 행 시맨틱스의 `checked`(`:121`)가 **둘 다 `widget.value` 하나** 를 읽습니다. `onChanged: enabled ? (_) {} : null`(`:69`)은 비활성 회색 렌더를 피하려는 의도가 맞고 `IgnorePointer` 로 호출 경로가 차단됩니다. 탭은 조상 `GestureDetector`(`:139-143`)가 받습니다 — `IgnorePointer` 가 자식 히트테스트를 막아 이벤트가 조상으로 떨어지므로 체크박스 영역 탭도 행 토글로 동작합니다. 브리프대로 `ExcludeSemantics` 만 걸었을 때의 이중 탭 정지 문제를 정확히 막았습니다.

**3. 진단 `_primaryAction` 9갈래 매핑 → 문제 없음 (핵심 확인)**
9갈래를 원본과 한 갈래씩 대조했습니다 — 라벨 9개 전부 동일, 콜백 누락 0, busy 게이팅 동등.
결정적 근거: `_actionable = (ready‖retry) && onPressed != null`(`dp_next_action_band.dart:68-71`)이고 `_activate()` 가 그것을 재검사(`:75-77`)하므로, `InkWell.onTap` 이 `actionable ‖ keepsFocus`(`:245`)로 pending 에도 배선돼 있어도 **탭이 아무 일도 하지 않습니다** = 옛 `onPressed: null` 과 동등, **중복 제출 불가**. Semantics 쪽은 `onTap: actionable ? onActivate : null`(`:217`)로 pending 에 탭 동작이 없습니다.
`assert` 3개 모두 만족 — ready/retry 4갈래 전부 `onPressed` 있음, disabled 3갈래 전부 `disabledReason` 있음.
`retry` 는 `retryLabel` 을 표시하고(`:181`) 두 retry 갈래의 `retryLabel` 이 원본 문구와 동일('경로 상태 다시 확인' · '저장 다시 시도').
갈래별 대조 결과: ① pathGeneration → retry/pending(busy 시 문구만 '경로 상태 확인 중' 으로 바뀜, 개선) ② guestExpired‖ownership → ready(원본도 busy 무시) ③ saved+unknown → disabled/pending, 라벨 '경로 상태 확인 필요'/'경로 확인 중' 원본과 동일 ④ saved+existing → '기존 경로로 계속' ⑤ saved+new → '학습 경로로 계속' ⑥ consent phase → '필수 동의 확인' ⑦ busy 저장 → '결과 저장 중' ⑧ claim‖resultMismatch → '저장 다시 시도' ⑨ 기본 → '저장하고 계속'. 잔여는 M7(비활성 밴드의 도달 불가 약속)·M10(인접 패널 문구)뿐.

**4. 즉시 제출 + 라디오 시맨틱스 / `radioGroup` 래퍼 → 문제 있음 (I4)**
즉시 제출 컨트롤에 라디오는 부적절합니다 — 원본 `OutlinedButton`(`role=button`)이 정확했고, 새 구현은 정상 흐름에서 아무것도 `checked` 가 되지 않는 라디오 그룹을 만듭니다. `radioGroup` 래퍼 자체는 axe `aria-required-parent` 대비로 방향이 맞고 Flutter 프레임워크 검증(`_semanticsRadioGroup`, `packages/flutter/lib/src/semantics/semantics.dart:343-370` 「Radio groups must not have multiple checked children」)도 통과합니다(어느 그룹도 checked 가 2개 이상 되지 않음). 그러나 Flutter `RadioGroup` 이 그 역할과 함께 주는 **화살표 shortcut + 단일 탭 정지 `FocusTraversalGroup`** 이 없어 계약이 반쪽입니다. 트랙 선택(선택이 상태로 남음)에 라디오는 적절하고, 문항 보기만 역할을 되돌리는 것이 맞습니다.

**5. 로그인 `showStory` 와 2열 경계 900→1240 → 문제 있음 (I1 · I6)**
분기 자체에 사각(dead zone)은 **없습니다** — compact(<600) 스토리 없음 / medium(600~839) 스토리+1열 / 840+ 2열, 세 상태가 연속이고 기존 테스트 「mobile login removes the story panel」(390)과 신설 「medium 에서 스토리 위·패널 아래」(800), 「expanded 이상에서 2열」(1280)이 셋을 각각 고정합니다. 그러나 ① **480 캡 제거로 600~839 에서 로그인 패널이 최대 791px 로 늘어나고 840+ 에서는 상한 없이 커집니다(I1)** ② **경계는 1240 이 아니라 840 입니다(I6)** — `dpWindowClassOf` 의 `expanded` 가 840~1239 이므로 원장 기록이 틀렸습니다. 구현은 계획 Ruling 대로이고 틀린 것은 기록입니다.

**6. 동의 두 패널과 제출 payload → 문제 없음**
`_submitPressed` 가 `for (final k in _ConsentKind.values)` 로 **5개 전부** 순회합니다(`consent_page.dart:127-130`) — UI 패널 구조와 완전히 무관합니다. `_required`(`:92-94`, `where((k) => k.required)`) + `_optional`(`:95-97`, `where((k) => !k.required)`)이 집합을 정확히 분할하고, 렌더 개수 5 를 테스트가 고정합니다(`findsNWidgets(5)` + 필수 태그 2 · 선택 태그 3). 필수 항목도 `onChanged` non-null 이라 여전히 토글 가능 — 원본 동작 유지. prefill 도 원본과 같게 선택 항목만 반영합니다(`:153-156`). 필수·선택 두 패널로 나눈 판정이 기존 정보 구조(필수 2행 → 출생 연도 → 선택 3행)를 보존한 점은 브리프의 단일 패널보다 낫습니다.

**7. `tallView`·`ensureVisible` 가 실제 결함을 덮는지 → 부분 문제 (M9 · I2 의 원인)**
키운 뷰포트와 `ensureVisible` 자체는 **정당** 합니다 — 화면이 `SingleChildScrollView` 안이라 실제 사용자도 스크롤로 도달하며 `ensureVisible` 은 그 스크롤을 충실히 재현합니다(결함 은폐 아님). 덮이는 것은 둘입니다: ① 폰 높이(844)에서의 스크롤 깊이를 재는 단언이 없다(M9) ② **200% 배율 테스트 3건이 모두 `takeException() == null` 만 단언** 해, 예외 없이 레이아웃이 망가지는 I2 를 구조적으로 볼 수 없다. 즉 뷰포트를 키운 것이 아니라 **단언이 약한 것** 이 실제 문제입니다.

**8. 마이페이지 활동 표·프로필 kv 미구현 판정의 데이터 부재 근거 → 문제 없음, 판정이 맞습니다**
모델을 직접 열어 확인했습니다 —
- `packages/dp_core/lib/src/models/my_activity.dart:9-12` = `MyActivity({@Default(0) int questionCount, @Default(0) int answerCount})` → **목록 자체가 없습니다.** 원장의 「브리프가 「작성」 칼럼만 없다고 본 것보다 한 단계 더 없다」가 정확합니다.
- `packages/dp_core/lib/src/models/profile_view.dart:9-15` = `ProfileView({String? avatar, String? bio, String? learningGoal, String? targetTrack, int? experienceYears})` → **표시 이름 필드 없음.**
- `apps/web/lib/src/features/mypage/state/mypage_state.dart` `MyPageLoaded{profile, dashboard, activity, saving}` → 다른 목록 소스도 없음.
- 겸사로 확인한 `.bars` 미구현 근거도 맞습니다: `packages/dp_core/lib/src/models/assessment.dart:38-41` = `AssessmentResult({required String diagnosedLevel, double? confidenceWeight})` → 개념별 점수 없음.
잔여는 kv 대신 넣은 태그가 아래 편집 폼과 중복된다는 논리 불일치(M6c)뿐입니다.

---

## 실행 기록

### 테스트·정적 분석

```
$ cd packages/dp_design && flutter test --exclude-tags golden
00:14 +377: All tests passed!

$ cd apps/web && flutter test
00:43 +1109: All tests passed!

$ cd apps/web && flutter analyze
warning - Returning a 'Future' without 'await' inside a try block. Try adding an 'await'
        - lib\src\features\dashboard\application\current_mission_controller.dart:273:7
        - unawaited_return_in_try_block
1 issue found. (ran in 5.4s)
  → 기존 결함(로컬 3.47 전용 린트). CI 3.44.1 은 녹색. 신규 이슈 0.

$ flutter --version
Flutter 3.47.2 • channel [user-branch]
Framework • revision d3b14c8769 (5 weeks ago) • 2026-08-26
  → CI 핀은 3.44.1 이므로 버전 의존 API 는 CI 가 최종 판정(Declined 2).
```

### 범위·충돌 검증

```
$ git log --oneline 2c38bac..e8f66d6
e8f66d6 feat(web): 설정을 .narrow + .rowline 패널 3개로, 마이페이지를 .cols 로
f03d629 feat(web): 진단 3단계를 시안 .steps + .opt + .next 로
ddd4218 feat(web): 동의를 .narrow 760 + .chk 패널로, 베타 대기를 .narrow.center 로
7e0522d feat(web): 로그인을 시안 .login 2열로, 인증 콜백을 .narrow.center 로
611a6da feat(dp_design): 시안 온보딩 프리미티브 3종 — DpSteps·DpOptionRow·DpCheckRow
  → 5커밋, Task 13~17 과 1:1. 범위 초과 커밋 없음.

$ git diff --stat 2c38bac..e8f66d6 | tail -1
 28 files changed, 2109 insertions(+), 760 deletions(-)

$ git diff origin/develop HEAD --name-only
  apps/web/lib/src/features/{auth(2), beta(1), common(1), consent(1),
                             diagnostic(1), mypage(1), settings(1)}   = 8
  apps/web/test/{features/auth(3), beta(1), consent(1), diagnostic(1),
                 mypage(1), settings(2)}, golden_path_onboarding_test  = 10
  packages/dp_design/lib/{dp_design.dart, content/dp_link.dart,
                          interaction/dp_check_row.dart,
                          interaction/dp_option_row.dart,
                          layout/dp_steps.dart}                       = 5
  packages/dp_design/test/{content, interaction×2, layout, theme}     = 5
  → 28파일, 전부 계획 Task 18 Step 1 이 선언한 경로.
    apps/admin · packages/dp_core 파일 0건(스펙 §10 준수) → Declined 7 의 근거.
    dp_link.dart 는 Task 15 Ruling 이 문서화한 계획 외 추가 1건.

$ git rev-parse origin/develop
2c38bacf2b6f5fe1168a04706f47c308be792559
$ git rev-list --left-right --count origin/develop...HEAD
0	5
  → base == 현재 develop, behind 0.

$ comm -12 <(git diff origin/develop...origin/feat/s3-p4-community-screens --name-only | sort) \
           <(git diff origin/develop...HEAD --name-only | sort)
(출력 없음)
  → 미머지 PR-B(931206c)와 겹치는 파일 0건. dp_design 배럴 충돌 없음
    (PR-B 는 dp_design 파일을 건드리지 않음).
```

### 잔여 장식·리터럴 확인

```
$ grep -rn "BoxDecoration\|Card(" --include=*.dart \
    apps/web/lib/src/features/{auth,beta,consent,diagnostic,mypage,settings} \
    apps/web/lib/src/features/common/presentation/placeholder_page.dart
(출력 없음)
  → 9화면에서 raw BoxDecoration·Material Card 전부 제거됨.

$ grep -rn "maxWidth:" (같은 경로)
  → 전부 context.appTokens.readableMaxWidth. 리터럴 0건.
    단 로그인 페이지 본문에는 상한 자체가 없음(I1).
```

### 워킹트리 상태

```
$ git -C D:/workspace/dpa/.worktrees/frontend-s3p4a-20260927 status --short
 M apps/web/analysis_options.yaml
 M packages/dp_design/analysis_options.yaml
 M pubspec.lock

$ git -C ... rev-parse --abbrev-ref HEAD
feat/s3-p4-account-screens
$ git -C ... log --oneline -1
e8f66d6 feat(web): 설정을 .narrow + .rowline 패널 3개로, 마이페이지를 .cols 로
```

**리뷰 시작 시점에는 `status --short` 가 완전히 깨끗했습니다.** 위 3파일은 제가 `flutter test`(dp_design·apps/web)와 `flutter analyze`(apps/web)를 돌린 뒤 **로컬 Flutter 3.47.2 가 다시 쓴 것** 입니다 — 메모리에 등록된 알려진 함정(`feedback-local-tool-rewrites-config-files` 「로컬 Flutter 가 설정 파일을 다시 쓴다」). **제가 편집한 파일은 하나도 없습니다.**

```
$ git diff --stat -- apps/web/analysis_options.yaml \
                     packages/dp_design/analysis_options.yaml pubspec.lock
 apps/web/analysis_options.yaml           |  4 ++++
 packages/dp_design/analysis_options.yaml |  3 +++
 pubspec.lock                             | 28 ++++++++++++++--------------

$ git diff -- apps/web/analysis_options.yaml
+analyzer:
+  exclude:
+    - build/**
+    - web/**
```
(`pubspec.lock` 은 해시 재기록 28줄)

**지시대로 되돌리지 않았습니다** — 컨트롤러가 처리하십시오. 이 3파일은 커밋 `e8f66d6` 에 포함되어 있지 않습니다(위 `git diff origin/develop HEAD --name-only` 28파일 목록에 없음).

---

## 머지 전 체크리스트 (권고 순서)

1. **I3** — `settings_page.dart:189` 날짜 포맷(한 줄). 가장 싸고 사용자 눈에 바로 보입니다.
2. **I1** — `login_page.dart` 에 `contentMaxWidth` 캡 한 겹.
3. **I2** — `dp_check_row.dart` 의 `Row` → `Wrap`(`DpRowLine` 과 동형).
4. **I4** — `DpOptionRow` 역할 파라미터화(문항 보기는 button). 화살표 순회는 후속으로 미뤄도 되지만 역할 정직성은 이 PR 에서 닫는 편이 좋습니다.
5. **I7** — `consent_page.dart`·`diagnostic_page.dart` 의 `DpPageHeader(gutter: true)`.
6. **I5 · I6** — `baseline-impact.md` 채우기 + 「900 → 840」 정정(documents 레포 PR). P5 의 입력 계약입니다.
7. Minor 는 P5 이월 가능. 단 **M4**(무시되는 테스트 인자)와 **M5**(틀린 대비 조합)는 지금 고치는 편이 다음 사람을 속이지 않습니다.
