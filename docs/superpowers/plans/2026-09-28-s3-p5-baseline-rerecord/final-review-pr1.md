# 전체 브랜치 리뷰 — `feat/s3-p5-carryover` (`eaa7f77..590fa50`, 14커밋)

리뷰 방식: 68KB diff 를 2패스로 읽었다(1패스 = 소스 변경 + 화면, 2패스 = 테스트 + 토큰).
그 뒤 diff 밖의 근거를 직접 확인했다 — `dp_typography.dart`·`dp_spacing.dart`·`dp_semantic_tokens.dart`·
`dp_colors.dart`·`dp_nav_rail.dart`·`mypage_page.dart` 전문, Flutter SDK 의 `Material.build`(잉크 표면의
부작용 확인), 그리고 **시안 정본 Artifact `DWi8kMV6QcAzBEQwbrNPNd` 의 CSS 를 직접 읽었다**(`.next`·`.steps`·
`.form`·`.chk`·`.kv`·`.rowline`·`.list li`·`.tag`·`.st`·`th`·`.opt`·`.prof`·mypage 사이드·`@container (max-width:720px)`).
아래 시안 인용은 전부 그 파일에서 그대로 옮긴 것이다.

### Verdict
Needs fixes before merge

세 건의 Important 는 전부 **「지금 고치지 않으면 PR-2 가 그 상태를 기준선으로 굳히거나, PR-3 의 핸드오프가
사실이 아닌 종결을 적게 된다」**는 성격이다. 코드가 깨지거나 테스트가 거짓인 곳은 없다.
컨트롤러가 I1·I2 를 「PR-2/PR-3 에 명시적 divergence 로 기록」으로 갈음하기로 판정한다면 그것도 유효한 닫기다 —
지금 상태의 문제는 그 divergence 가 **어디에도 적혀 있지 않다**는 것이다.

---

### Plan Alignment

계획 Task 1~10 은 **전부 구현됐다.** Task 11~17 은 손대지 않았다(범위 준수 ✅).
계획 밖으로 새 파일을 만들거나 다른 화면을 건드린 흔적은 없다. `git status` 깨끗, 설정 파일 커밋 0건
(Global Constraints 의 「설정 파일을 커밋하지 않는다」 지켜짐 — 변경 27파일 전부 lib/test).

정당한 이탈(개선으로 판정):

| 이탈 | 계획 | 구현 | 판정 |
|---|---|---|---|
| Task 7 M10a 기대값 | `closeTo(16, 0.5)`(「DpSpacing.lg 하나」) | `closeTo(8, 0.5)`·`closeTo(12, 0.5)` | ✅ 계획이 틀렸다. 실측으로 교정했고 주석에 근거를 남겼다 |
| Task 7 M9 상한 | `lessThan(2532)`(뷰포트 3배) | `lessThan(1500)`(실측 1337) | ✅ 훨씬 판별력이 높다 |
| Task 7 보기 루프 회귀 테스트 | 트랙 루프 1건만 | 트랙·보기 **둘 다** | ✅ M10a 가 지목한 두 루프를 다 덮는다 |
| Task 6 대상 | 7곳 | **11곳**(+`dp_tag`·`dp_web_table` 헤더·`dp_check_row` 설명·`dp_check_row` 패딩) | ⚠️ 방향은 옳다. 다만 렌더 영향 목록이 계획과 달라졌다 → M5 |
| Task 2 `_Step` 키 | 계획대로 | 계획대로 | ✅ |

문제 있는 이탈 하나:

- **Task 6 Step 1 의 「렌더를 고정하는」 단언이 조용히 빠졌다.** 계획은
  `expect(tester.getSize(find.text('완료')).height, closeTo(16, 0.5))` 를 명시했는데 구현 테스트에는
  `style.height` 단언만 있다. Task 6 의 존재 이유가 「바뀐 높이를 테스트로 고정한다」였으므로
  **선언된 스타일이 아니라 그려진 줄 상자**를 재야 계약이 잠긴다. Task 6 보고서에 이유가 없다 → M4.

---

### Strengths

1. **함정을 호출부가 아니라 위젯이 흡수하게 만든 것(Task 5)이 이 브랜치에서 가장 값진 변경이다.**
   `path_plan_view.dart` 에서 우회 두 겹과 그 긴 설명 주석이 사라지고, 지식이 `dp_panel.dart` 한 곳으로
   모였다. `grep MaterialType.transparency` 로 남은 3곳(`notice_banner_bar`·`ads_page`·`bulk_action_bar`)을
   직접 확인했는데 전부 **자기 표면을 가진 색 Material** 이라 건드리지 않은 판단이 옳다.
2. **실패를 먼저 보고 고친 흔적이 테스트에 남아 있다.** Task 2 의 `IntrinsicHeight` 함정 주석
   (「Row 의 stretch 만으로는 세로 무한 제약이 자식에게 넘어간다」)은 다음 사람이 같은 실수를 반복하지
   않게 하는 종류의 주석이다. Task 7 M11 의 「정지 **개수**」 테스트도 마찬가지 — `ExcludeFocus` 를 지우면
   5회 Tab 에서 서로 다른 노드가 4개가 되어 실제로 RED 가 된다(판별력 확인함).
3. **Task 1 의 새 주석이 시안과 정확히 맞는다.** 시안을 직접 읽어 대조했다 —
   `@container (max-width:720px){ .cols,.login{grid-template-columns:minmax(0,1fr)} }`
   가 실제로 `.cols` 와 `.login` **한 규칙에 묶여** 있다. 주석이 근거로 든 사실이 참이다.
   경계 4값(599/839/840/1240) 고정 테스트도 모순 재발을 실제로 막는다.
4. **Task 10 의 수정이 정확히 최소다.** 래퍼 `Semantics` 가 라벨을 소유하고 보이는 `Text` 만 뺐다.
   `Badge` 의 개수 텍스트는 시맨틱스에 남겨 둔 것도 옳다(읽히지 않으면 안 되는 정보다).
5. **접근성 변경 3건이 전부 실제 개선이다**(퇴행 없음 — 아래 접근성 절 참조).
6. **M10a 가 코드베이스 전체에서 닫혔다.** `for (...) ...[...]` 형태의 스프레드 4곳을 전수 조사했고
   마지막 자식이 `SizedBox`/`Divider` 인 루프는 **0건**이다. 같은 결함이 다른 화면에 남아 있지 않다.

---

### Cross-Task Findings

#### C1. `DpPanel` 의 `Material` 은 잉크만 바꾸지 않는다 — `DefaultTextStyle` 도 리셋한다 *(Minor, M11)*

Flutter SDK `material.dart` 의 `Material.build` 를 직접 읽었다:

```dart
Widget? contents = widget.child;
if (contents != null) {
  contents = AnimatedDefaultTextStyle(
    style: widget.textStyle ?? Theme.of(context).textTheme.bodyMedium!,
    duration: widget.animationDuration,   // 기본 kThemeChangeDuration = 200ms
    child: contents,
  );
}
```

즉 `DpPanel` 안쪽의 모든 텍스트는 이제 **패널 밖에서 내려오던 `DefaultTextStyle` 을 물려받지 않고**
`bodyMedium` 에서 다시 시작한다(그리고 그 스타일 전환이 200ms 애니메이션이며 `DpMotion` 의 reduced-motion
게이트를 타지 않는다). `MaterialType.transparency` 는 배경을 안 그릴 뿐 이 래퍼는 그대로 붙는다.

**오늘 실제 영향은 없다** — 확인했다: `DpPanel` 소비처 21파일 어디에서도 바깥 `DefaultTextStyle.merge` 안에
패널을 두지 않고, `dp_design` 셸(`dp_nav_rail:79`·`dp_chrome_bar:140`·`dp_web_header:180`)의 텍스트 스타일
스코프 안에 `DpPanel` 이 들어가는 경로도 없다(`grep DpPanel( packages/dp_design/lib` = 정의 1줄뿐).
**하지만** `DpPanel` 은 21파일이 쓰는 프리미티브이고, 지금 코드 주석은 「표면 색·테두리는 그대로이고
**잉크만**」이라고 단언한다. 그 단언이 불완전하다. 한 줄 보강을 권한다.

같은 확인의 결론 하나: **`Material` 은 시맨틱스 노드를 만들지 않는다**(`_RenderInkFeatures` 는
`RenderProxyBox`, `ClipPath`/`_ShapeBorderPaint` 도 시맨틱스 설정 없음). 그래서 리뷰 지시가 물은
**「`DpPanel` 의 `Material` 과 `DpNavRail` 의 `ExcludeSemantics` 가 시맨틱스 트리에서 간섭하는가」의 답은
「간섭하지 않는다」**이다. 둘의 경로도 겹치지 않는다(레일 항목 안에 패널이 들어가는 화면이 없다).
`absorbHitTest` 도 transparency 에서는 `false` 라 히트테스트 변화도 없다.

#### C2. 누적 렌더 변화의 충돌 — 그림자 제거가 「배경 색이 틀린」 밴드를 드러냈다 *(→ Important I1)*

Task 3·5·6 이 만나는 화면은 `/diagnostic` 결과와 `/sandbox`·`/content` 다. 셋을 겹쳐 보면:

- Task 3 이 `DpNextActionBand` 의 유일한 깊이 단서(`blurRadius 24`)를 없앴다. 남은 구분은 1px 테두리뿐이다.
- 그런데 밴드의 배경은 `colors.surface`(라이트 `#FFFFFF`)다. `DpPanel`·`.ide .pane` 등 **`surface` 를 쓰는
  컨테이너 위에 얹히면 배경이 같아져** 사실상 테두리만 남는다.
- 시안은 이 문제를 배경 색으로 푼다: `.next{...background:var(--soft);border:1px solid var(--line)...}`.
  두 토큰 모두 레포에 **이미 있고 값도 정확히 일치한다** — `accentSoft = #EEF2FF` = `--soft`,
  `accentLine = #C7D2FE` = `--line`.

즉 Task 3 은 시안 `.next` 규칙을 근거로 들면서 그 규칙의 **세 속성 중 하나(그림자 없음)만** 반영했다.
상세는 I1.

#### C3. Task 6 의 토큰 도입은 Task 2·7 의 치수 단언과 충돌하지 않는다 ✅

명시적으로 물어본 항목이라 하나씩 확인했다.

- Task 2 의 단계 높이 테스트는 **세 단계 서로의 높이를 비교**한다 → 줄 높이 변화에 면역.
- Task 7 M10a 의 두 테스트는 **사각형 사이 간격**을 잰다 → 줄 높이 변화에 면역.
- Task 7 M9 의 CTA 깊이(절대값 1500)만 모든 토큰 변화에 민감하다. **커밋 순서가 옳다** —
  `145bd00`(Task 6) → `9805b46`(Task 7)이라 1337 은 토큰 전환 **뒤**의 실측이다.
  헤드룸 163px ≈ `DpOptionRow` 3행분이라 주석의 「행 두어 개」와 일치한다.
- 진단 화면의 보기 행에는 `description` 이 없어 `bodySmall` 전환이 높이에 닿지 않는다.

충돌 없음. 다만 줄 높이 변화 자체의 **근거**는 아래 M7 처럼 정리가 필요하다.

#### C4. 새 공개 API `DpWebDensity` 는 기존 토큰 체계와 일관되지 않다 *(→ Important I3)*

`dp_spacing.dart` 에 이미 **`DpDensity`** 가 있고 그 안에 `rowPadding = 8`(「표 행 세로 여백 8」)이 있다.
이제 같은 파일 아래쪽에 `DpWebDensity.rowVerticalPadding = 10` 이 생겼다. 상세는 I3.

#### C5. 테스트 관례는 브랜치 안에서 일관된다 ✅ (코드의 이름 관례는 아니다)

- `dp_design` 신규 테스트 6파일 전부 파일 지역 `_host(...)` + `_size(tester, Size)` 헬퍼를 쓴다.
  `dp_steps_test.dart` 의 `_size` 주석이 `dp_cols_test.dart` 를 관례의 출처로 명시까지 한다. 좋다.
- `apps/web` 신규 테스트는 해당 파일의 기존 관례(뷰포트 인라인 지정)를 따른다 — `mypage_page_test.dart`
  는 원래 전부 인라인이고 새 테스트 2건도 인라인, `diagnostic_page_test.dart` 는 원래 `tallView` 헬퍼가
  있고 새 `phoneView` 헬퍼를 같은 모양으로 더했다. **파일별로 다르지만 파일 안에서는 일관**이다. 옳은 선택.
- 반면 **구현 코드의 `textTheme` 접근은 세 가지 이름**이 됐다: `dp_status_text` = `base`,
  `dp_web_table`·`dp_row_line` 등 = 지역 `text`, `dp_tag` = 인라인 `Theme.of(context).textTheme`
  (게다가 포맷터가 `Theme.of(\n  context,\n).textTheme...` 로 접어 읽기 나쁘다 — 컨트롤러의 `a2a9926`
  가 그 줄이다). → M8.

#### C6. 이 브랜치가 닫은 「주석/코드 모순」과 같은 종류를 새로 두 개 들였다 *(M3·M11)*

Task 1 의 주제가 **「주석이 코드와 다른 값을 말한다」**였는데,

- `diagnostic_page.dart` 두 곳과 새 테스트 두 곳의 주석이 **`시안 .form{gap:14px}`** 를 근거로 들면서
  실제 코드는 `DpSpacing.sm`(**8**)을 쓴다(시안 실측 확인: `.form{display:flex;flex-direction:column;gap:14px}`).
  근거로 든 것은 「행 **사이**에만」이라는 규칙이지 값이 아니지만, 읽는 사람에게는 14 옆에 8 이 놓인다.
- `dp_panel.dart` 의 새 주석이 「잉크만」이라 단언하는데 실제로는 `DefaultTextStyle` 도 바뀐다(C1).

둘 다 한 줄 보강으로 닫힌다.

---

### Issues

#### Critical (Must Fix)

없음.

#### Important (Should Fix)

---

**I1. `DpNextActionBand` 의 배경·테두리가 시안 `.next` 와 다르고, 그림자 제거가 그 차이를 드러낸다.**

- 위치: `packages/dp_design/lib/src/mission/dp_next_action_band.dart:63-77`(이 PR 이 편집한 바로 그 `BoxDecoration`)
- 시안 정본: `.next{display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap;`
  `padding:16px;background:var(--soft);border:1px solid var(--line);border-radius:var(--r-card)}`
- 현재: `color: context.dpColors.surface` · `border: Border.all(color: context.dpColors.border)`
- 토큰은 이미 있다: `DpColors.light.accentSoft = 0xFFEEF2FF` == `--soft`,
  `DpColors.light.accentLine = 0xFFC7D2FE` == `--line`. `accentLine` 은 같은 파일 262줄이 포커스 링으로
  이미 쓰고 있어 import 도 필요 없다.
- 왜 지금인가: ① Task 3 의 커밋 메시지·코드 주석이 **「시안 `.next` 는 테두리 한 겹뿐이다」**라고 그 규칙을
  근거로 들었다 — 같은 규칙의 나머지 두 속성을 그대로 둔 것은 근거 인용의 절반만 따른 것이다.
  ② 그림자를 없앤 뒤 밴드의 유일한 구분은 1px 테두리인데, 밴드가 `surface` 배경 컨테이너
  (`DpPanel`·실습 IDE 페인) 위에 놓이는 소비처가 있다(소비처 12곳 중 `sandbox_page.dart:373`·`:434`,
  `content_page.dart:299`). 그 자리에서 밴드는 **면 구분이 사실상 사라진다.**
  ③ **PR-2 가 이 렌더를 기준선으로 굳힌다.** 지금 고치지 않으면 다음 기회는 다음 기준선 재기록이다.
- 어떤 기존 테스트도 밴드의 바깥 배경을 고정하지 않는다(확인함) — 2줄 변경 + 색 단언 테스트 1건이면 끝난다.
- **대안 판정도 유효하다**: 「P4 가 의도적으로 surface 를 택했다」는 근거가 어딘가에 있다면
  그것을 코드 주석과 PR-3 의 baseline-impact-p5 에 적어라. 지금은 근거도 기록도 없다.

---

**I2. Task 8 은 마이페이지를 시안과 1:1 로 만들지 못했다 — M6c 의 중복은 닫힌 게 아니라 자리를 옮겼다.**

- 위치: `apps/web/lib/src/features/mypage/presentation/mypage_page.dart:215-261`(편집 패널) vs `:295-312`(새 사이드 kv)
- 시안 정본 `mypage` 화면(직접 읽음):
  - 페이지 헤더: `<div class="acts"><a class="btn">프로필 편집</a><a class="btn">설정</a></div>`
  - 본문 칼럼: `.prof`(아바타 + 이름 + 소개 + 배지 2개) **+ 「커뮤니티 활동」 표.** 편집 폼이 **없다.**
  - 사이드: `<div class="panel"><h3>프로필</h3><dl class="kv"><dt>목표 트랙</dt>…<dt>목표</dt>…<dt>경력(년)</dt><dd>0</dd></dl></div>`
- 구현은 사이드 kv 를 **더했지만** 본문의 「프로필 편집」 패널(자기소개·학습 목표·목표 트랙·경력(년) +
  저장 버튼, **항상 보인다**)을 그대로 뒀다. 결과: **목표 트랙·목표·경력 세 값이 한 화면에 두 번 나온다** —
  사이드에 읽기 전용 kv 로, 본문에 이미 그 값이 선택된 드롭다운/입력으로.
  compact(<840)에서는 `DpCols` 가 main → side 로 접으므로 같은 세 값이 **위아래로** 놓인다.
- 즉 P4 독립 리뷰 M6c 의 지적(「태그 3개가 바로 아래 편집 폼의 같은 3필드를 반복한다」)은
  **반복 자체가 사라진 게 아니라 태그 → kv 패널로 바뀐 것**이다. 시안에 중복이 없는 이유는
  시안에는 그 편집 폼이 애초에 없기 때문이다.
- 편집 폼을 별도 라우트로 빼는 것은 이 PR 의 범위가 분명히 아니다. **그래서 요구하는 것은 코드 변경이 아니라
  기록이다**: (a) `mypage_page.dart` 의 사이드 kv 주석에 「본문 편집 폼과 값이 겹친다 — 시안은 편집을
  별도 화면으로 빼서 겹치지 않는다」를 적고, (b) PR-3 핸드오프/원장이 **M6c 를 「닫힘」이 아니라
  「부분 닫힘 + 남은 divergence」**로 적게 하라. 지금 상태로 두면 「시안과 1:1 로 맞췄다」는 커밋 메시지가
  그대로 스펙에 실린다.
- 부수 확인 ✅: 사이드 kv 의 키 문자열 3개(`목표 트랙`·`목표`·`경력(년)`)와 패널 제목(`프로필`),
  배지 2개가 머리에 온다는 배치는 **시안과 정확히 일치한다.** 그 부분의 구현은 옳다.

---

**I3. `DpWebDensity` 는 기존 `DpDensity` 와 개념이 겹치고 2.0.0 토큰 계약 바깥에 있다. `plan-mandated`**

- 위치: `packages/dp_design/lib/src/theme/dp_spacing.dart:54-62`(신설) vs 같은 파일 `:27-31`(기존 `DpDensity`)
- 사실:
  - `DpDensity` 의 doc 이 스스로 **「표 행 세로 여백 8」**을 선언하고 `rowPadding = 8` 을 갖는다
    (`dp_list_row.dart:223`·`dp_web_table.dart:242` 가 쓴다).
  - 새 `DpWebDensity.rowVerticalPadding = 10` 은 `dp_row_line`·`dp_list_lines`·`dp_check_row`·`dp_option_row`
    가 쓴다.
  - 결과: **「행 세로 패딩」이라는 한 이름의 개념이 두 클래스에 8 과 10 으로 나뉘어 있다.**
    다음에 행 위젯을 만드는 사람이 `DpDensity.` 를 먼저 자동완성으로 만나면 8 을 집는다.
  - 더 무거운 쪽: `dp_semantic_tokens.dart:475-486` 이 밀도 토큰을 CSS 로 투영하며
    주석에 **「DpDensity 가 SSoT」**라 못 박고 `--dp-density-*` 커스텀 프로퍼티를 만든다
    (랜딩 `tokens.css` 미러가 이 투영을 쓴다). `DpWebDensity` 는 그 목록에 없다 ⇒
    **디자인 토큰 계약이 모르는 공개 치수 토큰**이 생겼다. DESIGN.md 개정(Task 15)의 범위에도 없다.
  - 이 레포는 과거에 정확히 이 축에서 사고를 냈다(홈 `assets/tokens.css` 미러가 앱 값과 어긋난 채
    버전 없이 바뀐 건).
- 값(10·6)은 **시안과 정확히 맞다** — 확인함: `.chk{padding:10px 16px}` · `.rowline{padding:10px 16px}` ·
  `.list li{padding:10px 16px}` · `.kv{padding:12px 16px;gap:6px 16px}`. doc 주석의 근거 인용은 참이다.
  문제는 값이 아니라 **어디에 두었는가**다.
- 가장 싼 닫기(택1):
  1. `DpDensity` 에 `rowVerticalPaddingWeb`/`keyValueGap` 으로 합치고 `_DensityRole` 에 두 role 을 더해
     CSS 투영까지 넣는다(계약 안으로 들어온다). 또는
  2. `DpWebDensity` 를 유지하되 **양쪽 클래스 doc 에 상호 참조 한 줄**을 넣고
     (`DpDensity.rowPadding` 은 표 행, `DpWebDensity.rowVerticalPadding` 은 구분선 행),
     **「계약 투영 대상이 아님」을 명시**한 뒤 Task 15 의 DESIGN.md 개정에 한 줄 추가한다.
- 계획이 이 형태를 명령했으므로 `plan-mandated` 로 표시한다 — 계획의 저작권이 계획 자신을 채점하지 않는다.

#### Minor (Nice to Have)

- **M1.** `dp_next_action_band.dart:204` — 릴리스 빌드에서 `disabledReason` 이 null 이면 라벨이
  「…, 사용할 수 없음: **null**」로 읽힌다. 생성자 `assert` 는 디버그 전용이고, 바꾸기 전에는
  `hint: null` 이라 조용히 없어졌다. `${widget.disabledReason ?? '지금은 사용할 수 없습니다'}` 한 줄이면 닫힌다.
- **M2.** `dp_steps.dart` `_Step` 이 시안과 다르다 — 시안 `.steps li{flex:1;padding:6px 12px;font-size:13px}`,
  구현은 `vertical: DpSpacing.xs`(**4**)·`horizontal: DpSpacing.md`(12)에 `fontSize` 미지정(=bodyMedium **14**).
  Task 2 가 이 위젯을 열었고 Task 6 이 「리터럴 치수 → 토큰」을 했는데 둘 다 지나쳤다. `bodySmall`(13/20) +
  세로 6 이 시안이다. PR-2 가 굳히기 전이 마지막 기회다.
- **M3.** `diagnostic_page.dart:317`·`:481` 과 새 테스트 2건의 주석이 `시안 .form{gap:14px}` 를 근거로
  드는데 코드는 `DpSpacing.sm`(8)이다. 시안 값 14 → 8pt 스케일로 내린 판단이 **어디에도 적혀 있지 않다**.
  주석에 「8pt 스케일에 맞춰 8 로 내렸다」 한 마디를 더하면 Task 1 이 닫은 종류의 모순이 다시 안 열린다.
- **M4.** `dp_status_text_test.dart` 가 계획의 **렌더 단언**(`tester.getSize(...).height ≈ 16`)을 빠뜨리고
  `style.height` 만 잰다. Task 6 의 목적이 「바뀐 높이를 고정」이므로 그려진 줄 상자를 재야 한다.
  (deferred minor #4 보다 이쪽이 날카로운 지적이다.)
- **M5.** Task 6 이 계획의 7곳 → **11곳**으로 늘면서 계획이 예고하지 않은 렌더 변화가 하나 늘었다:
  `dp_web_table` 헤더 셀의 줄 높이 `14×1.6=19.2` → `labelMedium` 의 16(헤더 행이 약 3.2px 낮아진다).
  `dp_tag` 는 옛 리터럴이 이미 `height: 16/12` 였으므로 **렌더 불변**(확인함). PR-3 의
  `baseline-impact-p5.md` 는 계획의 예상이 아니라 **실제 11곳 기준**으로 적어야 한다.
- **M6.** 시안 `.tag{…font-size:12px;font-weight:500}` 인데 `labelMedium` 은 **w600** 이다
  (옛 리터럴도 600 이었으므로 이 PR 이 만든 차이는 아니다). `DpTypography` 에 12/500 role 이 없다 —
  `labelMedium.copyWith(fontWeight: FontWeight.w500)` 또는 새 role 이 필요하다. 판단만 기록해도 된다.
- **M7.** Task 6 의 줄 높이 근거가 시안과 반대 방향이다. 시안에서 `.st`·`th`·`.tag` 는 `line-height` 를
  **재정의하지 않아 body 의 1.6 을 물려받는다**(=12px 글자에 19.2px 줄). 토큰 `labelMedium` 은 16/12 를
  스스로 갖는다. 즉 이 전환은 「시안에 맞춘 것」이 아니라 **토큰 체계에 맞춘 것**이고, 시안 대비로는
  `.st`·`th` 가 약 3.2px 낮아진다. 새 테스트 주석이 `16/12` 를 계약처럼 서술하므로 한 줄로 정정하는 게 좋다
  (「촘촘 밀도 결정에 따라 시안의 상속 행간 대신 토큰 행간을 쓴다」).
- **M8.** `textTheme` 접근 이름이 셋이다(`base`/`text`/인라인). 특히 `dp_tag.dart` 의 인라인은
  포맷터가 `Theme.of(\n  context,\n).textTheme…` 로 접어 읽기 나쁘다(컨트롤러의 `a2a9926` 가 그 줄).
  `final text = Theme.of(context).textTheme;` 로 통일하면 포맷 문제도 함께 사라진다. = deferred #6.
- **M9.** `dp_check_row_test.dart` 의 `Set<int>` + `identityHashCode(node)` 는 `Set<FocusNode>` 로
  바로 쓸 수 있다(해시 충돌 여지도 없어진다). = deferred #7.
- **M10.** `dp_next_action_band_test.dart` 의 새 테스트 `'ready 밴드는 예상 결과를 그대로 읽는다'` 가
  같은 파일 기존 테스트 `'ready action relates its label to the expected outcome and returns ID'` 의
  단언 문자열과 **완전히 같다.** 한쪽은 지워도 커버리지가 줄지 않는다.
- **M11.** `dp_panel.dart:34-39` 의 주석이 「표면 색·테두리는 그대로이고 **잉크만**」이라 단언하지만
  `Material` 은 `AnimatedDefaultTextStyle(bodyMedium, 200ms)` 도 씌운다(C1 에 SDK 인용). 오늘 영향은
  없으나(21 소비처 전수 확인) 프리미티브의 불변식이므로 한 줄 적어 두는 게 맞다.
- **M12.** 마이페이지 배지는 `dashboard` 가 null 이면 **조용히 사라진다.** 바로 아래 「활동」 패널은
  같은 실패를 「학습 활동을 불러오지 못했습니다」로 **명시**한다 — 한 화면에서 같은 실패를 두 방식으로
  다룬다. 배지는 장식에 가까우니 현 동작도 방어 가능하지만, 그 판단이 코드에 없다. = deferred #10.
- **M13.** `mypage_page.dart:138-139` 주석의 「오늘 화면이 쓰는 것과 같은 값·**문구**다」가 사실이 아니다.
  실측: `today_panels.dart:112` 는 `(key: '연속 학습', value: Text('${summary.streakDays}일'))` 이고
  `'N일 연속'` 이라는 문구는 **이 화면이 새로 합성한 것**이다(배지 `summary.badges` 만 같은 값 재사용).
  = deferred #9. **이 한 건은 머지 전에 고치라고 본다**(아래 트리아지 참조).

---

### Deferred Minors — 트리아지

1. **Task 1+2 보고서가 회귀 범위를 작게 적었다** — 머지 전 수정 **불필요**. 코드가 아니라 보고서의 기록이고
   컨트롤러가 전체 실행으로 이미 덮었다. PR-3 원장에 한 줄로 남기면 족하다.
2. **`devicePixelRatio`/`physicalSize` 설정 순서** — **불필요**. `_size` 헬퍼로 실제 해소됐음을 코드에서 확인했다.
3. **함정 설명이 `dp_panel.dart` 와 `dp_panel_test.dart` 양쪽에 있다** — **불필요**. 테스트 쪽 주석은
   「왜 이 테스트가 존재하는가」이고 구현 쪽은 「왜 이 한 겹이 있는가」다. 목적이 달라 중복이 아니다.
4. **타이포 6곳 중 `dp_status_text` 에만 `style.height` 단언** — 머지 전 수정 **불필요하지만**, 진짜 문제는
   커버리지 범위가 아니라 **그 하나마저 렌더가 아닌 선언 스타일만 잰다**는 것이다(M4). M4 를 함께 다루면
   좋고, 미루더라도 PR-2 의 기준선이 실제 계약 역할을 한다.
5. **`?.` / `!` 혼용** — **불필요**. `DpTheme` 아래에서 `bodySmall` 은 항상 non-null 이라 `!` 가 틀린 것은
   아니다. 다만 `dp_status_text` 만 `?.` 라 실패 양상이 다르다(그쪽은 null 이면 **색까지 통째로 사라진다**).
   통일한다면 `!` 쪽으로.
6. **지역 `text` vs 인라인 `Theme.of`** — **불필요**(M8 로 승계). 다만 포맷터가 만든 `dp_tag.dart` 의
   3줄 접힘까지 함께 사라지므로 값싼 개선이다.
7. **`identityHashCode` → `Set<FocusNode>`** — **불필요**(M9). 테스트 판별력은 지금도 충분하다(확인함).
8. **M9 CTA 상한의 한계를 주석에** — **불필요**. 지금 주석이 이미 「행 두어 개가 늘어도 통과하도록 1500」을
   적고 있어 한계가 드러나 있다.
9. **`mypage_page.dart` 주석이 출처를 과장한다** — **머지 전에 고쳐라.** ⭐
   실측으로 확인했다: 오늘 화면에 `'N일 연속'` 문구는 없다. 이 레포의 최상위 규칙이
   「추측·예상 금지 / 확인한 사실만 적는다」이고, 이 주석은 **다음 사람이 today 화면을 고칠 때 잘못된
   커플링 가정을 하게 만든다**(「문구를 공유하니 한쪽만 바꾸면 안 되겠군」). 한 줄 교정이다:
   「값은 오늘 화면과 같은 `DashboardSummary` 를 쓴다. 배지 문구는 그 화면의 `'연속 학습: N일'` 과 달리
   시안 `.prof` 의 `7일 연속` 형태로 여기서 합성한다.」
10. **`dashboard == null` 경로 테스트 부재** — **불필요**(M12). 다만 위 9번을 고칠 때 같은 블록이므로
    테스트 3줄을 함께 더하면 싸게 닫힌다.

**머지 전에 고쳐야 할 deferred minor: 1건(9번).**

---

### Declined to Judge

아래는 이 PR 의 범위(계획 Task 1~10) 바깥이라고 보고 판정하지 않은 것들이다. 각 줄에 이유를 붙인다.
컨트롤러가 판정한다.

1. **`DpNextActionBand` 의 구조가 시안 `.next` 와 다르다** — 시안은 `display:flex;justify-content:space-between`
   에 오른쪽 `.btn.p` 인 가로 배치인데 구현은 세로 `Column` 에 전폭 `InkWell` 이다. P4 가 이미 배선한
   구조 변경이라 이 PR 의 이월 목록에 없다. (I1 의 색 두 개와 달리 이건 2줄로 안 끝난다.)
2. **시안 `.prof` 는 사용자 **이름**을 굵게 보여 준다**(`<b style="font-size:18px">지수</b>`) — 구현은
   이름 없이 소개(bio)를 `titleMedium` 으로 첫 줄에 둔다. Task 8 의 명세는 「태그 ↔ kv 자리 교환」뿐이었고
   이름 필드 배선은 새 작업이다.
3. **시안 마이페이지 본문의 「커뮤니티 활동」 **표**** vs 구현의 「활동」 2줄 집계 — P4 가 주석으로
   「시안의 활동 표를 만들 목록 데이터가 없다」고 이미 기록한 알려진 divergence다.
4. **시안 마이페이지 페이지 헤더의 `프로필 편집`·`설정` 버튼** — 구현에는 없다(편집이 인라인이라서).
   I2 와 같은 뿌리지만 라우트 신설이 필요해 이 PR 범위 밖이다.
5. **`.opt{padding:10px 14px}` 의 가로 14 vs 구현 `DpSpacing.md`(12)**, **`.tag{padding:1px 7px}` vs
   구현 8/4** — P3·P4 가 8pt 스케일로 내린 기존 판단이고 이 PR 이 건드리지 않았다.
6. **`apps/web` 에 리터럴 `TextStyle(fontSize:)` 가 아직 10곳 남아 있다**
   (`lcs_context.dart` 3 · `post_detail_page.dart` 2 · `web_community_board_projection.dart:210` ·
   `path_panels.dart:107` · `support_dialog.dart` 3). `dp_design/lib` 은 이제 **0곳**이다(확인함).
   Task 6 의 명시 범위가 `dp_design` 이라 판정하지 않았다. 다만 결과적으로 **같은 화면 안에서
   12px 글자의 줄 높이가 두 가지**(토큰 16 vs 리터럴 19.2)가 된다 — PR-2 가 이 상태를 굳힌다.
7. **`flutter analyze` 의 `current_mission_controller.dart:273 unawaited_return_in_try_block`** —
   컨트롤러가 이미 실측으로 「로컬 Dart 3.13.2 전용, CI 핀 3.12.1 에는 없음, 파일은 develop 과 byte-identical」
   로 판정했다. 재판정하지 않는다.
8. **컨트롤러가 작업 브랜치에 직접 포맷 커밋(`a2a9926`)을 넣은 것** — 프로세스이지 코드가 아니다.
   (그 줄 자체는 M8 로 다룬다.)
9. **`DpNavRail._item` 은 `Material(color: Colors.transparent)`(= canvas 타입, `absorbHitTest: true`)를,
   `DpPanel` 은 `MaterialType.transparency`(`absorbHitTest: false`)를 쓴다** — 잉크 표면을 다는 관용구가
   레포에 둘이다. 동작 결함은 아니고(둘 다 의도대로 작동) 통일은 별도 작업이다.
10. **`IntrinsicHeight` 의 레이아웃 비용**(자식 수만큼 추가 패스) — `DpSteps` 는 단계 3~4개라 무시할
    수준이고, perf 기준선은 PR-2(Task 14)가 CI 측정값으로 다시 기록한다.
11. **`DpPanel` 이 이제 `Container` clip + `Material` 의 `ClipPath` 로 클립 레이어를 두 겹 갖는다**
    (`Material.clipBehavior` 기본값이 `Clip.none` 이라 실제 클리핑은 한 번) — 측정 가능한 영향이 없다.
12. **`_Step` 의 `Semantics(selected:)` 에 `role` 이 없다**(시안은 `<ol>/<li aria-current="step">`) —
    P4 가 정한 현재 모양이고 이월 목록에 없다.
