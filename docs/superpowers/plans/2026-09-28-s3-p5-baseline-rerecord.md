# S3-P5 기준선 재기록 + 이월 판단 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** P2~P4 가 바꾼 렌더를 게이트가 참인 상태로 굳히고(browser-ux 커버리지·perf 기준선·DESIGN.md), P3·P4 가 P5 로 미룬 판단 13건을 닫아 S3 를 릴리스에 태울 수 있게 만든다.

**Architecture:** 렌더를 바꾸는 이월 판단을 **PR-1 에서 전부** 끝내고, **PR-2 가 그 최종 렌더를 기준선으로 기록**한다(기준선을 두 번 기록하지 않기 위한 순서다). PR-2 의 실질은 「기대값 갱신」이 아니라 **게이트 커버리지 확장** — `browser-ux` 가 지금 8 라우트(7화면)만 방문하고 P4 가 바꾼 14화면을 한 번도 보지 않는다. PR-3 은 documents 레포에 핸드오프·원장·스펙 정정을 남긴다.

**Tech Stack:** Flutter 3.44.1(CI 핀) / Dart 3.12.1 · melos 7 워크스페이스 · Playwright `mcr.microsoft.com/playwright:v1.55.0-noble` 핀 컨테이너 · axe-core · Node 테스트 러너

**Spec:** `docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` §7 (P5 행) · §8 (게이트) · §9 (운영 반영)

**입력 계약:** `docs/superpowers/plans/2026-09-27-s3-p4-screen-groups/baseline-impact.md` — 이 계획의 모든 이월 항목은 그 문서의 「P5 이월」·「PR-C 실행이 드러낸 함정」 절에서 나왔다.

**시안 정본:** Artifact `https://claude.ai/artifact/DWi8kMV6QcAzBEQwbrNPNd` (Version 2). 시각 판단은 이 시안의 CSS 를 근거로만 내린다 — 「시안에 없는 화면 요소를 구현 중에 즉흥으로 만들지 않는다」(스펙 §7 원칙).

---

## Global Constraints

- **Flutter/Dart 버전**: CI 핀은 Flutter **3.44.1** / Dart **3.12.1**. 로컬은 3.47 이라 API 가 더 많다 — **로컬에만 있는 API 에 테스트를 묶지 말 것**.
- **`SemanticsFlag` 는 이 Flutter 에 없다.** `containsSemantics` 는 deprecated 이고 `flutter analyze` 가 info 를 치명으로 다뤄 rc=1 이 된다. 시맨틱스 매처는 **`isSemantics`** 를 쓴다. `flagsCollection` + `ui.Tristate` 관례는 로컬 3.47 전용이라 금지.
- **`MaterialApp` 은 뷰에서 자기 MediaQuery 를 만든다.** 바깥에 `MediaQuery` 를 씌워 폭·배율을 주는 테스트는 **조용히 무효**다. `tester.view.physicalSize` + `tester.view.devicePixelRatio` / `tester.platformDispatcher.textScaleFactorTestValue` 를 쓰고 `addTearDown(tester.view.reset)` 으로 되돌린다.
- **`context.appTokens` 는 테마 확장을 요구한다**(`Theme.extension<AppTokens>()!`). 토큰을 읽는 위젯을 테스트로 띄울 때 그 호스트에 **`theme: DpTheme.light()`** 를 반드시 준다 — 없으면 `_TypeError` 로 죽는다.
- **`Row` 의 non-flex 자식은 주축 무한 제약으로 측정된다.** 좁은 폭·큰 배율 테스트는 `expect(tester.takeException(), isNull)` 로 판정하지 말고 **폭을 직접 잰다**(오버플로 예외가 나지 않는 결함이다).
- **위젯 단독 테스트는 화면보다 폭이 넉넉하다.** 390 재현은 뷰포트만 390 으로 두면 안 되고 실제 행 폭(390 − 페이지 패딩 − 패널 테두리 = **340**)으로 좁혀야 판별력이 생긴다.
- **그림자 금지**(DESIGN.md §3 「장식용 그림자 금지(APP UI). 보더 우선, 그림자는 오버레이(드롭다운·다이얼로그·시트)에만」).
- **포인터 타깃 ≥ 24×24**(`DpDensity.minTarget` = 24 · browser-ux `MIN_TARGET` 과 같은 값) · 컨트롤 높이 30(`DpDensity.controlHeight`).
- **레이아웃 토큰**: `contentMaxWidth` 1120 · `readableMaxWidth` 760 · `headerHeight` 56 · `panelRadius` 8. 셸 밖 bare 라우트(`/login`·`/consent`·`/diagnostic`·`/beta-pending`·`/auth/callback`)는 **본문 폭 상한을 스스로** 줘야 한다.
- **`DpWindowClass` 경계는 SSoT**: compact <600 · medium 600–839 · expanded 840–1239 · large ≥1240. 재정의 금지.
- **설정 파일을 커밋하지 않는다**(로컬 Flutter 가 `.vscode`·`analysis_options` 등을 다시 쓸 수 있다 — P3 리뷰 Important 였다). 커밋 전 `git diff --stat` 으로 변경 파일 목록을 눈으로 확인한다.
- **포맷**: `dart run melos run format` 이 `0 changed` 여야 한다.
- **모든 git/파일 명령에 절대경로 또는 `-C <레포 절대경로>` 를 쓴다.** `cd` 후 상대경로 후속 명령 금지 — 에이전트 스레드는 bash 호출 사이 cwd 가 리셋돼 조용히 다른 레포에서 실행될 수 있다.
- **레포 경로**: frontend 워크트리 `D:\workspace\dpa\.worktrees\frontend-s3p5-20260928`(Task 0 에서 만든다) · documents 워크트리 `D:\workspace\dpa\.worktrees\documents-s3p5-plan`.
- **브랜치 전략**: 작업 브랜치는 `develop` 에서 분기하고 `develop` 으로 PR. `main`·`develop` 직접 push 금지. CI 전 잡이 pass/skipping 이고 실패 0 이면 AI 가 머지한다(사용자 결정 2026-09-27).

## Review Focus

이 계획의 작업이 건드리는 입력 중, 어느 Task 의 테스트도 저절로는 건드리지 않는 것 다섯. 각 줄의 테스트는 해당 Task 안에 스텝으로 들어가 있다.

1. **`DpSteps` 의 라벨이 줄바꿈하는 폭** — 단계 높이가 서로 달라지고 테두리 안 배경이 어긋난다. 시안 `.steps` 는 `align-items:stretch` 다. (Task 2 가 640 폭에서 세 단계의 높이 동일을 측정한다 — 그 폭에서 한 칸이 약 213px 이라 긴 라벨이 실제로 줄바꿈한다.)
2. **`DpNextActionBand` 가 `disabled` 인 상태** — 사용자가 실행할 수 없는 「예상 결과」를 스크린리더가 약속으로 읽는다. (Task 4 가 disabled 밴드의 시맨틱 라벨을 단언한다.)
3. **`DpPanel` 안에 잉크를 쓰는 Material 위젯(`ListTile`·`InkWell`)을 넣은 화면** — 잉크가 패널 표면 대신 `Scaffold` 에 그려져 패널이 그 잉크를 덮는다. 프레임워크 단언으로 죽는다. (Task 5 가 패널 안 `ListTile` 을 띄워 단언 없이 통과함을 증명한다.)
4. **탭 정지 개수** — `DpCheckRow` 의 `ExcludeFocus` 를 지워 체크박스가 다시 별도 정지를 가져도 지금 테스트는 전부 통과한다. (Task 7 이 정지 **개수**를 고정한다.)
5. **인증 상태에 따라 라우터가 돌려보내는 라우트** — `MOCK_PROFILE=onboarded` 빌드에서 `/login`·`/consent`·`/diagnostic`·`/beta-pending`·`/auth/callback` 은 **전부 redirect 되어 도달 불가**다. 그 화면을 ROUTES 에 적는 것만으로는 다른 화면을 두 번 재는 테스트가 된다. (Task 12 가 프로필별 도달을 실측으로 증명한 뒤에 라우트를 넣는다.)

---

## 이 계획이 닫는 이월 목록 (입력 계약과의 대조표)

| 출처 | 항목 | Task |
|---|---|---|
| baseline-impact 「P5 이월」 | `DpCols` 주석/코드 모순 | 1 |
| baseline-impact 「P5 이월」 | `dp_design` 리터럴 치수 → 토큰 | 6 |
| baseline-impact 「P5 이월」 | `DpInteractiveCard` ↔ DESIGN.md §3 불일치 | 15 |
| baseline-impact 「P5 이월」 | `DpNavRail` 레일 항목 라벨 중복 | 10 |
| baseline-impact 「PR-A 함정」 | `DpPanel` 잉크 표면 근본 수정 | 5 |
| P4 리뷰 M1 | `DpSteps` 단계 높이 | 2 |
| P4 리뷰 M3 | `PlaceholderPage` 소비처 0 | 9 |
| P4 리뷰 M6c | 마이페이지 `.prof` 태그 ↔ 사이드 kv | 8 |
| P4 리뷰 M7 | 비활성 밴드가 예상 결과를 읽는다 | 4 |
| P4 리뷰 M8 | `DpNextActionBand` 의 `boxShadow` | 3 |
| P4 리뷰 M9 | 진단 시작 CTA 깊이 단언 부재 | 7 |
| P4 리뷰 M10a | 보기 목록 마지막 행 뒤 여분 8px | 7 |
| P4 리뷰 M11 | 탭 정지 개수 고정 테스트 부재 | 7 |
| baseline-impact 「browser-ux 시나리오 수정」 | P4 가 바꾼 14화면이 게이트 밖이다 | 12 |
| 스펙 §7 P5 | browser-ux `expectations.json` | 13 |
| 스펙 §7 P5 | perf baseline | 14 |
| 스펙 §7 P5 | DESIGN.md §3·§5 개정 | 15 |
| 스펙 §7 P5 | ET13 visual/a11y baseline | 17 (판정: 릴리스 단계 — 아래 참조) |

**ET13 에 대한 판정(실측 근거):** `evidence/et13/catalog.schema.json:61` 이 `baseline_status` 를 `"pending_external_review"` **상수**로 고정하므로 커밋된 카탈로그는 `approved` 를 담을 수 없다. `evidence/et13/baselines/` 에는 README 하나뿐이고 승인된 기준선 이미지는 레포에 **없다**. 승인은 `.github/workflows/et13-baseline-approval.yml`(보호 환경 `et13-baseline-approval`, `workflow_dispatch`)가 만드는 외부 산출물이고 입력에 **`release_id`** 를 요구한다 ⇒ **ET13 baseline 승인은 P5(develop 단계)의 작업이 아니라 릴리스 캠페인의 단계다.** P5 의 몫은 카탈로그 정합성(13 fixture 의 `source_widget` 13개 전부 실재 — 확인 완료)과 `produce-atomic-pair` 녹색 유지뿐이고, Task 16 이 그 판정을 핸드오프와 스펙에 적는다.

---

## File Structure

**PR-1 — `feat/s3-p5-carryover` (frontend)**

| 파일 | 책임 |
|---|---|
| `packages/dp_design/lib/src/layout/dp_cols.dart` | 2열 분기. **코드 불변**, 주석만 코드에 맞게 재작성 |
| `packages/dp_design/test/layout/dp_cols_test.dart` | 840 경계를 고정하는 테스트 추가(모순 재발 방지) |
| `packages/dp_design/lib/src/layout/dp_steps.dart` | 단계 표시. 동일 높이 |
| `packages/dp_design/lib/src/mission/dp_next_action_band.dart` | 그림자 제거 · disabled 시맨틱 라벨 |
| `packages/dp_design/lib/src/layout/dp_panel.dart` | 잉크 표면을 스스로 갖는다 |
| `packages/dp_design/lib/src/states/dp_status_text.dart` | 리터럴 12/w600 → `labelMedium` |
| `packages/dp_design/lib/src/data/dp_row_line.dart` | 설명 리터럴 13 → `bodySmall` · 비스케일 패딩 10 을 명명 상수로 |
| `packages/dp_design/lib/src/data/dp_list_lines.dart` | 같은 비스케일 패딩 10 |
| `packages/dp_design/lib/src/data/dp_key_values.dart` | 비스케일 간격 6 |
| `packages/dp_design/lib/src/interaction/dp_option_row.dart` | 설명 리터럴 13 → `bodySmall` |
| `packages/dp_design/lib/src/shell/dp_nav_rail.dart` | 라벨 중복 제거(admin) |
| `apps/web/lib/src/features/diagnostic/presentation/diagnostic_page.dart` | 보기 목록 여분 간격 |
| `apps/web/lib/src/features/mypage/presentation/mypage_page.dart` | `.prof` 배지 태그 + 사이드 프로필 kv |
| `apps/web/lib/src/features/common/presentation/placeholder_page.dart` | **삭제**(소비처 0) |
| `packages/dp_design/test/{layout/dp_steps,mission/dp_next_action_band,layout/dp_panel,states/dp_status_text,interaction/dp_check_row,shell/dp_nav_rail}_test.dart` | 위 변경의 테스트 |
| `apps/web/test/features/{diagnostic/diagnostic_page,mypage/mypage_page}_test.dart` | 화면 변경의 테스트 |

**PR-2 — `feat/s3-p5-gate-baseline` (frontend)**

| 파일 | 책임 |
|---|---|
| `tools/browser_ux/run.mjs` | `--routes=` 옵션 · `ROUTES` 확장 |
| `tools/browser_ux/run.test.mjs` | 새 옵션의 단위 테스트 |
| `tools/browser_ux/expectations.json` | `recorded_from` 갱신 · 새 라우트 기대값 |
| `apps/web/lib/src/data/web_mock_fixtures.dart` | mock 프로필 `consent`·`guest` 신설(온보딩 화면 도달용) |
| `apps/web/test/app/gate_redirect_test.dart` | 프로필별 라우트 도달을 `gateRedirect` 로 고정 |
| `apps/web/test/data/web_mock_fixtures_profile_test.dart` | 새 프로필 픽스처의 단위 테스트 |
| `.github/workflows/ci.yml` | `browser-ux-onboarding` 잡 신설 |
| `perf/baseline.json` | CI 측정 아티팩트로 재기록 |
| `DESIGN.md` | §3 소비 줄 정정 · §5 에 `DpCols` 경계 근거 |

**PR-3 — `docs/s3-p5-complete` (documents)**

| 파일 | 책임 |
|---|---|
| `docs/superpowers/handoff-2026-09-28-s3-p5-complete.md` | 핸드오프 |
| `docs/superpowers/plans/2026-09-28-s3-p5-baseline-rerecord/execution-ledger.md` | 실행 원장 |
| `docs/superpowers/plans/2026-09-28-s3-p5-baseline-rerecord/baseline-impact-p5.md` | P5 가 만든 렌더 변화(릴리스 캠페인의 입력) |
| `docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` | §7 P5 행 정정(ET13 승인은 릴리스 단계) |

---

### Task 0: 작업 워크트리

**Files:**
- 없음(환경 준비)

**Interfaces:**
- Consumes: frontend `origin/develop` = `eaa7f77`
- Produces: 워크트리 `D:\workspace\dpa\.worktrees\frontend-s3p5-20260928` · 브랜치 `feat/s3-p5-carryover`

- [ ] **Step 1: origin 을 받고 base 를 확인한다**

```bash
git -C /d/workspace/dpa/devpath-frontend fetch origin --quiet
git -C /d/workspace/dpa/devpath-frontend log --oneline -1 origin/develop
```

Expected: `eaa7f77` 로 시작하는 한 줄. 다르면 **멈추고 보고한다**(base 가 움직였다).

- [ ] **Step 2: 워크트리를 만든다**

```bash
git -C /d/workspace/dpa/devpath-frontend worktree add \
  /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 \
  -b feat/s3-p5-carryover origin/develop
```

- [ ] **Step 3: 워크스페이스를 부트스트랩한다**

```bash
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && dart pub get && dart run melos bootstrap
```

- [ ] **Step 4: 기준선 상태를 기록한다(뒤 Task 가 비교할 값)**

```bash
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test -r compact 2>&1 | tail -3
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/web && flutter test -r compact 2>&1 | tail -3
```

Expected: dp_design **380** 통과 · web **1122** 통과. 다르면 base 가 다르다 — 멈추고 보고한다.

---

### Task 1: `DpCols` 의 주석과 코드를 일치시킨다 (모순 해소)

**결정(사용자, 2026-09-28):** **코드가 옳다 — 경계는 840 이다.** 주석을 고친다. 시안 CSS 의 `@container (max-width:720px)` 와 다른 값을 쓰는 이유를 주석과 DESIGN.md 에 남긴다(Task 15). 렌더는 한 픽셀도 바뀌지 않는다.

**Files:**
- Modify: `packages/dp_design/lib/src/layout/dp_cols.dart:5-13` (주석만)
- Test: `packages/dp_design/test/layout/dp_cols_test.dart`

**Interfaces:**
- Consumes: `DpWindowClass`(compact <600 · medium 600–839 · expanded 840–1239 · large ≥1240)
- Produces: 변화 없음 — `DpCols({required Widget main, required Widget side, bool stretch = false})`

- [ ] **Step 1: 경계를 고정하는 실패 테스트를 쓴다**

`packages/dp_design/test/layout/dp_cols_test.dart` 끝에 덧붙인다:

```dart
  // 주석과 코드가 서로 다른 경계를 말하던 모순(P4 독립 리뷰 I6)이 다시 열리지
  // 않게 네 경계값을 직접 고정한다. 839→1열 / 840→2열 이 계약이다.
  testWidgets('2열 경계는 840 이다 — 839 는 1열, 840 은 2열', (tester) async {
    for (final (width, expectTwoColumn) in <(double, bool)>[
      (599, false),
      (839, false),
      (840, true),
      (1240, true),
    ]) {
      tester.view.devicePixelRatio = 1;
      tester.view.physicalSize = Size(width, 900);
      addTearDown(tester.view.reset);

      await tester.pumpWidget(
        MaterialApp(
          theme: DpTheme.light(),
          home: const Scaffold(
            body: DpCols(
              main: SizedBox(key: ValueKey('cols-main'), height: 40),
              side: SizedBox(key: ValueKey('cols-side'), height: 40),
            ),
          ),
        ),
      );

      final mainRect = tester.getRect(find.byKey(const ValueKey('cols-main')));
      final sideRect = tester.getRect(find.byKey(const ValueKey('cols-side')));
      // 2열이면 사이드가 주 내용 오른쪽에 있고, 1열이면 아래에 있다.
      expect(
        sideRect.left > mainRect.left,
        expectTwoColumn,
        reason: 'width=$width 에서 2열 기대=$expectTwoColumn',
      );
      expect(sideRect.top > mainRect.top, !expectTwoColumn, reason: 'width=$width');
    }
  });
```

- [ ] **Step 2: 테스트가 통과하는지 확인한다(코드는 이미 옳다)**

```bash
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test test/layout/dp_cols_test.dart -r compact
```

Expected: PASS. **FAIL 이면 멈춘다** — 코드가 840 이 아니라는 뜻이고 이 Task 의 전제가 깨진다.

- [ ] **Step 3: 주석을 코드에 맞게 재작성한다**

`dp_cols.dart` 의 클래스 주석 중 아래 두 줄을

```dart
/// 경계를 [DpWindowClass.expanded](1240) 에 두는 이유: 셸 본문은 최대 1120 이고
/// 사이드가 1fr 이므로 840~1239 에서 사이드가 약 270px 까지 눌린다. 그 폭에서는
/// 표가 이미 자체 가로 스크롤로 들어가 2열이 읽히지 않는다.
```

다음으로 바꾼다:

```dart
/// 2열 경계는 **840**([DpWindowClass.expanded] 의 시작)이다. 시안의 컨테이너
/// 질의는 720 이지만(`@container (max-width:720px)`) 이 위젯은 840 을 쓴다 —
/// 시안의 그 한 규칙이 `.cols`(2:1 분할)와 `.login`(1.1:0.9 대등 분할)을 함께
/// 묶고 있고, 2:1 에서는 720 에서 사이드가 약 220px 로 눌려 패널 제목조차
/// 줄바꿈한다. 시안 갤러리는 1440·390 두 폭만 보여 주므로 720~839 는 시각
/// 검토된 적이 없다 — 검토되지 않은 구간에서는 더 보수적인 경계를 택했다.
/// (S3-P5 사용자 결정 2026-09-28. 근거는 DESIGN.md §5.)
```

- [ ] **Step 4: 분석·포맷·테스트**

```bash
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter analyze && flutter test -r compact 2>&1 | tail -3
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && dart format --set-exit-if-changed .
```

Expected: analyze 0 issues · dp_design **381** 통과 · format 0 changed.

- [ ] **Step 5: 커밋**

```bash
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && git add packages/dp_design/lib/src/layout/dp_cols.dart packages/dp_design/test/layout/dp_cols_test.dart && git diff --cached --stat && git commit -m "$(cat <<'EOF'
docs(dp_design): DpCols 2열 경계를 840 으로 확정하고 주석 모순을 닫는다

주석은 「경계를 expanded(1240) 에」라 적고 코드는 `expanded || large`(840)로
그려 840~1239 의 6화면 레이아웃이 어느 쪽 의도인지 알 수 없었다(P4 독립 리뷰
I6). 코드를 정본으로 택하고 주석을 다시 썼다 — 시안 CSS 의 720 과 다른 이유를
함께 적었다. 렌더는 바뀌지 않는다. 경계 네 값을 고정하는 테스트를 더해 모순이
다시 열리지 않게 했다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
---

### Task 2: `DpSteps` 의 단계가 같은 높이를 갖는다 (M1)

**근거:** 시안 `.steps{display:flex;gap:0;...}` — flex 기본 `align-items:stretch` 다. 현재 코드는 `Row(children: [...Expanded])` 로 `crossAxisAlignment` 를 지정하지 않아 기본 `center` 가 되고, 라벨이 줄바꿈하는 폭에서 단계마다 높이가 달라져 `accentSoft` 배경이 어긋난다.

**함정:** `Row(crossAxisAlignment: CrossAxisAlignment.stretch)` 만으로는 안 된다 — 세로 제약이 무한인 자리(`Column` 안)에서 `stretch` 는 무한 높이를 자식에게 넘긴다. **`IntrinsicHeight` 로 감싸야** 가장 높은 자식 높이가 먼저 정해진다.

**Files:**
- Modify: `packages/dp_design/lib/src/layout/dp_steps.dart`
- Test: `packages/dp_design/test/layout/dp_steps_test.dart`

**Interfaces:**
- Consumes: `DpWindowClass`(compact 면 세로 스택) · `DpColors`
- Produces: 공개 API 불변 — `DpSteps({required List<String> labels, required int currentIndex})`. 내부 `_Step` 에 `ValueKey('dp-step-<i>')` 가 새로 붙는다(테스트가 잡는다)

- [ ] **Step 1: 실패 테스트를 쓴다**

`packages/dp_design/test/layout/dp_steps_test.dart` 에 덧붙인다:

```dart
  // 시안 `.steps` 는 CSS flex 기본값인 align-items:stretch 다 — 라벨이 줄바꿈
  // 하는 폭에서도 세 단계의 높이가 같아야 배경(accentSoft)이 어긋나지 않는다.
  testWidgets('라벨이 줄바꿈하는 폭에서도 단계 높이가 같다', (tester) async {
    tester.view.devicePixelRatio = 1;
    // 640: compact(<600)를 넘겨 가로 배치로 두면서, 세 단계를 나란히 놓으면
    // 한 칸이 약 213px 이라 긴 라벨이 두 줄이 되는 폭이다.
    tester.view.physicalSize = const Size(640, 400);
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: const Scaffold(
          body: Align(
            alignment: Alignment.topCenter,
            child: DpSteps(
              labels: ['1 트랙 선택', '2 실력 진단을 아주 길게 적은 라벨', '3 학습 경로'],
              currentIndex: 0,
            ),
          ),
        ),
      ),
    );

    final heights = <double>[
      for (var i = 0; i < 3; i++)
        tester.getSize(find.byKey(ValueKey('dp-step-$i'))).height,
    ];
    expect(heights[1], greaterThan(24), reason: '긴 라벨이 실제로 줄바꿈해야 판별력이 생긴다');
    expect(heights[0], heights[1]);
    expect(heights[2], heights[1]);
  });
```

- [ ] **Step 2: 테스트를 돌려 RED 를 확인한다**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test test/layout/dp_steps_test.dart -r compact`

Expected: FAIL. 먼저 `ValueKey('dp-step-0')` 을 못 찾아 실패한다(키가 아직 없다).

- [ ] **Step 3: `_Step` 에 키를 주고 가로 배치를 `IntrinsicHeight` + stretch 로 바꾼다**

`dp_steps.dart` 의 `items` 생성에 키를 더한다:

```dart
    final items = <Widget>[
      for (var i = 0; i < labels.length; i++)
        _Step(
          key: ValueKey('dp-step-$i'),
          label: labels[i],
          current: i == currentIndex,
          // 마지막이 아니면 다음 단계와의 사이에 구분선을 둔다.
          divider: i != labels.length - 1,
          vertical: vertical,
        ),
    ];
```

`_Step` 생성자에 `super.key` 를 받게 한다:

```dart
class _Step extends StatelessWidget {
  const _Step({
    super.key,
    required this.label,
    required this.current,
    required this.divider,
    required this.vertical,
  });
```

가로 분기를 바꾼다:

```dart
          : IntrinsicHeight(
              // 시안 `.steps` 는 flex 기본 align-items:stretch 다. Row 의
              // `stretch` 만으로는 안 된다 — 세로 제약이 무한인 자리에서는
              // 무한 높이가 자식에게 넘어간다. IntrinsicHeight 가 가장 높은
              // 자식의 높이를 먼저 정해 준다.
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [for (final item in items) Expanded(child: item)],
              ),
            ),
```

- [ ] **Step 4: 테스트를 돌려 GREEN 을 확인한다**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test test/layout/dp_steps_test.dart -r compact && flutter analyze`

Expected: PASS · analyze 0 issues.

- [ ] **Step 5: 진단 화면 3곳의 회귀를 확인한다**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/web && flutter test test/features/diagnostic -r compact`

Expected: 전부 통과.

- [ ] **Step 6: 커밋**

커밋 메시지(제목 + 본문):

```
fix(dp_design): DpSteps 의 단계가 같은 높이를 갖는다

시안 `.steps` 는 flex 기본값인 align-items:stretch 인데 Row 가
crossAxisAlignment 를 지정하지 않아 기본 center 로 그려졌다 — 라벨이 줄바꿈
하는 폭에서 단계마다 높이가 달라지고 현재 단계의 accentSoft 배경이 어긋났다.
IntrinsicHeight + stretch 로 고쳤다(Row 의 stretch 만으로는 세로 무한 제약을
자식에게 넘겨 죽는다). 640 폭에서 세 단계의 높이 동일을 측정하는 테스트를 더했다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && git add packages/dp_design && git diff --cached --stat && git commit -F <메시지 파일>`

---

### Task 3: `DpNextActionBand` 의 그림자를 없앤다 (M8)

**근거:** 시안 `.next{...background:var(--soft);border:1px solid var(--line);border-radius:var(--r-card)}` — **그림자가 없다.** DESIGN.md §3 도 「장식용 그림자 금지. 보더 우선, 그림자는 오버레이에만」이다. 현재 밴드는 `blurRadius: 24` 그림자를 갖는다.

**영향 범위:** 소비처 12곳(오늘 2 · 콘텐츠 1 · 경로 1 · 실습 2 · 진단 6). 전부 렌더가 바뀐다 — PR-2 가 기준선을 다시 기록한다.

**Files:**
- Modify: `packages/dp_design/lib/src/mission/dp_next_action_band.dart` (`build` 의 `DecoratedBox`)
- Test: `packages/dp_design/test/mission/dp_next_action_band_test.dart`

**Interfaces:**
- Consumes: `context.dpColors` · `context.appTokens.panelRadius`
- Produces: 공개 API 불변

- [ ] **Step 1: 실패 테스트를 쓴다**

```dart
  // DESIGN.md §3: 장식용 그림자 금지 — 시안 `.next` 도 테두리 한 겹뿐이다.
  testWidgets('밴드는 그림자를 갖지 않는다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: Scaffold(
          body: DpNextActionBand(
            actionId: 'a',
            label: '시작',
            expectedOutcome: '무엇이 일어나는지',
            state: DpNextActionState.ready,
            onPressed: (_) {},
          ),
        ),
      ),
    );

    final box = tester.widget<DecoratedBox>(
      find
          .descendant(
            of: find.byType(DpNextActionBand),
            matching: find.byType(DecoratedBox),
          )
          .first,
    );
    expect((box.decoration as BoxDecoration).boxShadow, isNull);
  });
```

- [ ] **Step 2: RED 확인**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test test/mission/dp_next_action_band_test.dart -r compact`

Expected: FAIL — `boxShadow` 가 1건이다.

- [ ] **Step 3: 그림자를 지운다**

`dp_next_action_band.dart` 의 `build` 에서 `boxShadow: [...]` 블록 전체를 삭제하고 주석을 남긴다:

```dart
    final band = DecoratedBox(
      decoration: BoxDecoration(
        color: context.dpColors.surface,
        border: Border.all(color: context.dpColors.border),
        borderRadius: BorderRadius.circular(context.appTokens.panelRadius),
        // 그림자 없음 — DESIGN.md §3(장식용 그림자 금지)이고 시안 `.next` 는
        // 테두리 한 겹뿐이다.
      ),
```

- [ ] **Step 4: GREEN 확인 + 소비처 회귀**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test -r compact
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/web && flutter test -r compact
```

Expected: 양쪽 전부 통과.

- [ ] **Step 5: 커밋**

```
fix(dp_design): DpNextActionBand 의 그림자를 없앤다

시안 `.next` 는 배경 + 테두리 한 겹뿐이고 DESIGN.md §3 도 장식용 그림자를
금지한다. blurRadius 24 그림자가 남아 있었다(P4 독립 리뷰 M8). 소비처 12곳의
렌더가 바뀐다 — P5 의 기준선 재기록이 이 상태를 굳힌다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

### Task 4: 비활성 밴드가 「예상 결과」를 약속하지 않는다 (M7)

**근거:** `_PrimaryAction` 의 `semanticLabel` 이 상태와 무관하게 `'<라벨>, 예상 결과: <expectedOutcome>'` 다. `disabled` 상태(진단 결과의 `saved && pathBranch == unknown` — 라벨 「경로 상태 확인 필요」)에서는 누를 수 없는데도 스크린리더가 예상 결과를 약속으로 읽는다.

**결정:** **시맨틱 라벨만 바꾼다.** 보이는 텍스트는 그대로 둔다 — 눈으로 읽는 사용자에게는 예상 결과 줄과 바로 아래 이유 줄이 함께 「화면이 무엇을 기다리는지」를 설명하고, 그 줄을 지우면 그 설명이 사라진다. `disabledReason` 은 `Semantics.hint` 에도 이미 실려 있다.

**Files:**
- Modify: `packages/dp_design/lib/src/mission/dp_next_action_band.dart` (`_PrimaryAction.build` 의 `semanticLabel` 한 줄)
- Test: `packages/dp_design/test/mission/dp_next_action_band_test.dart`

**Interfaces:**
- Consumes: `DpNextActionState` · `DpNextActionBand.disabledReason`(disabled 면 non-null·non-empty 가 생성자 assert 로 보장된다)
- Produces: 공개 API 불변

- [ ] **Step 1: 실패 테스트를 쓴다**

```dart
  // 누를 수 없는 밴드가 예상 결과를 약속으로 읽으면 안 된다(P4 독립 리뷰 M7).
  testWidgets('disabled 밴드의 라벨은 예상 결과 대신 이유를 읽는다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: const Scaffold(
          body: DpNextActionBand(
            actionId: 'a',
            label: '경로 상태 확인 필요',
            expectedOutcome: '경로 상태를 확인하면 학습 경로로 넘어갈 수 있습니다.',
            state: DpNextActionState.disabled,
            disabledReason: '경로 상태를 아직 확인하지 못했어요.',
          ),
        ),
      ),
    );

    expect(
      find.bySemanticsLabel('경로 상태 확인 필요, 사용할 수 없음: 경로 상태를 아직 확인하지 못했어요.'),
      findsOneWidget,
    );
    expect(find.bySemanticsLabel(RegExp('예상 결과')), findsNothing);
  });

  testWidgets('ready 밴드는 예상 결과를 그대로 읽는다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: Scaffold(
          body: DpNextActionBand(
            actionId: 'a',
            label: '시작',
            expectedOutcome: '무엇이 일어나는지',
            state: DpNextActionState.ready,
            onPressed: (_) {},
          ),
        ),
      ),
    );
    expect(find.bySemanticsLabel('시작, 예상 결과: 무엇이 일어나는지'), findsOneWidget);
  });
```

- [ ] **Step 2: RED 확인**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test test/mission/dp_next_action_band_test.dart -r compact`

Expected: 첫 테스트 FAIL · 두 번째 PASS.

- [ ] **Step 3: 라벨 계산을 상태별로 가른다**

`_PrimaryAction.build` 의 `semanticLabel` 한 줄을 바꾼다:

```dart
    // disabled 는 사용자가 실행할 수 없다 — 그 자리에서 「예상 결과」를 읽으면
    // 지킬 수 없는 약속이 된다(P4 독립 리뷰 M7). 대신 왜 못 누르는지를 읽는다.
    // 보이는 텍스트는 그대로 둔다: 예상 결과 줄과 그 아래 이유 줄이 함께 화면이
    // 무엇을 기다리는지 설명한다.
    final semanticLabel = widget.state == DpNextActionState.disabled
        ? '$displayedLabel, 사용할 수 없음: ${widget.disabledReason}'
        : '$displayedLabel, 예상 결과: ${widget.expectedOutcome}';
```

- [ ] **Step 4: GREEN 확인 + 소비처 회귀**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test -r compact
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/web && flutter test -r compact
```

Expected: 전부 통과. `bySemanticsLabel` 로 CTA 를 찾는 기존 테스트가 깨지면 그 화면이 disabled 밴드를 쓰는 것이다 — **실패 메시지에 찍힌 실제 라벨을 읽어** 기대 문자열을 고친다(추측 금지).

- [ ] **Step 5: 커밋**

```
fix(dp_design): 비활성 밴드가 예상 결과를 약속하지 않는다

disabled 상태의 DpNextActionBand 가 사용자가 누를 수 없는 「예상 결과」를
스크린리더에 약속으로 읽었다(P4 독립 리뷰 M7). 그 상태에서는 「사용할 수 없음:
<이유>」를 읽는다. 보이는 텍스트는 그대로 둔다 — 예상 결과 줄과 이유 줄이 함께
화면이 무엇을 기다리는지 설명한다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

### Task 5: `DpPanel` 이 스스로 잉크 표면을 갖는다 (PR-A 함정의 근본 수정)

**근거:** 패널은 색을 가진 `Container` 이고 Material `ListTile`·`InkWell` 은 **가장 가까운 `Material`**(보통 `Scaffold`)에 배경·잉크를 그린다. 그래서 패널 표면이 그 잉크를 덮고 `ListTile` 은 프레임워크 단언에 걸린다 — P4 Task 3 의 실패 7건이 전부 이 한 원인이었다. 지금 처방은 호출부가 직접 `Material(type: MaterialType.transparency)` 를 한 겹 두는 것이다.

**결정(사용자, 2026-09-28):** **위젯이 함정을 흡수한다.** `MaterialType.transparency` 는 아무 배경도 그리지 않으므로 표면 색·테두리 렌더는 그대로이고, 잉크만 패널의 `clipBehavior: Clip.antiAlias` 안으로 잘린다.

**Files:**
- Modify: `packages/dp_design/lib/src/layout/dp_panel.dart`
- Test: `packages/dp_design/test/layout/dp_panel_test.dart`

**Interfaces:**
- Consumes: `DpColors.surface`·`DpColors.border` · `DpRadius.card`
- Produces: 공개 API 불변 — `DpPanel({Widget? title, required Widget child, EdgeInsetsGeometry? padding})`

- [ ] **Step 1: 실패 테스트를 쓴다**

```dart
  // 패널은 색을 가진 Container 다 — Material ListTile 은 가장 가까운 Material
  // (보통 Scaffold)에 잉크를 그리므로 패널 표면이 그 잉크를 덮고 프레임워크
  // 단언에 걸린다. 패널이 스스로 투명 Material 을 두면 호출부가 그 함정을
  // 몰라도 된다(P4 Task 3 의 실패 7건이 전부 이 원인이었다).
  testWidgets('패널 안의 Material ListTile 이 단언 없이 그려진다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: Scaffold(
          body: DpPanel(
            title: const DpPanelTitle('제목'),
            child: ListTile(title: const Text('행'), onTap: () {}),
          ),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
    expect(
      find.descendant(
        of: find.byType(DpPanel),
        matching: find.byWidgetPredicate(
          (w) => w is Material && w.type == MaterialType.transparency,
        ),
      ),
      findsOneWidget,
    );
  });

  testWidgets('패널 표면 색·테두리·무그림자는 그대로다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: const Scaffold(body: DpPanel(child: SizedBox(height: 20))),
      ),
    );
    final container = tester.widget<Container>(
      find
          .descendant(of: find.byType(DpPanel), matching: find.byType(Container))
          .first,
    );
    final decoration = container.decoration! as BoxDecoration;
    expect(decoration.color, DpTheme.light().extension<DpColors>()!.surface);
    expect(decoration.border, isNotNull);
    expect(decoration.boxShadow, isNull);
  });
```

- [ ] **Step 2: RED 확인**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test test/layout/dp_panel_test.dart -r compact`

Expected: 첫 테스트 FAIL — 투명 `Material` 이 없다.

- [ ] **Step 3: 패널 안쪽에 투명 Material 을 둔다**

`dp_panel.dart` 의 `return Container(...)` 를 바꾼다(`Column` 을 `Material` 로 감싸고 닫는 괄호를 한 겹 늘린다):

```dart
    return Container(
      decoration: BoxDecoration(
        color: c.surface,
        border: Border.all(color: c.border),
        borderRadius: BorderRadius.circular(DpRadius.card),
      ),
      clipBehavior: Clip.antiAlias,
      // 패널이 스스로 잉크 표면을 갖는다. `MaterialType.transparency` 는 아무
      // 배경도 그리지 않으므로 표면 색·테두리는 위 Container 것 그대로이고,
      // 잉크만 이 경계 안에서 일어나 위의 clipBehavior 로 잘린다. 이 한 겹이
      // 없으면 안쪽의 `ListTile`·`InkWell` 이 가장 가까운 Material(보통
      // `Scaffold`)에 그려 패널 표면이 그 잉크를 덮고, `ListTile` 은 프레임워크
      // 단언에 걸린다(P4 Task 3 의 실패 7건이 전부 이 원인이었다).
      child: Material(
        type: MaterialType.transparency,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            // (기존 자식 그대로)
          ],
        ),
      ),
    );
```

- [ ] **Step 4: GREEN 확인 + 세 패키지 전 스위트**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test -r compact
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/web && flutter test -r compact
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/admin && flutter test -r compact
```

Expected: 전부 통과. **하나라도 깨지면 원인을 읽고 보고한다 — 테스트를 느슨하게 고쳐 통과시키지 않는다.**

- [ ] **Step 5: 호출부의 중복 Material 을 걷어낸다**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && grep -rn "MaterialType.transparency" apps/web/lib apps/admin/lib --include=*.dart`

`DpPanel` 바로 안쪽 한 겹이라면 지운다(이제 패널이 갖는다). 패널과 무관한 곳은 건드리지 않는다. 지운 뒤 Step 4 를 다시 돌린다.

- [ ] **Step 6: 커밋**

```
fix(dp_design): DpPanel 이 스스로 잉크 표면을 갖는다

패널은 색을 가진 Container 라 안쪽의 Material ListTile/InkWell 이 가장 가까운
Material(보통 Scaffold)에 잉크를 그렸다 — 패널 표면이 그 잉크를 덮고 ListTile
은 프레임워크 단언에 걸렸다(P4 Task 3 의 실패 7건이 전부 이 한 원인).
`MaterialType.transparency` 한 겹을 패널 안쪽에 둬 함정을 위젯이 흡수한다.
그 타입은 아무 배경도 그리지 않으므로 표면 색·테두리 렌더는 그대로다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

### Task 6: `dp_design` 의 리터럴 치수를 토큰으로 옮긴다

**실측한 현재 값과 목표:**

| 파일 | 현재 | 목표 | 성격 |
|---|---|---|---|
| `states/dp_status_text.dart` | `TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: color)` | 테마의 `labelMedium`(12 · w600)을 읽어 `color` 만 덮는다 | 타이포 |
| `data/dp_row_line.dart` 설명 | `TextStyle(fontSize: 13, color: c.textSecondary)` | `text.bodySmall!.copyWith(color: c.textSecondary)` | 타이포 |
| `interaction/dp_option_row.dart` 설명 | `TextStyle(fontSize: 13, color: c.textSecondary)` | 같음 | 타이포 |
| `data/dp_row_line.dart` 패딩 | `vertical: 10` | `DpWebDensity.rowVerticalPadding` 신설 | 간격 |
| `data/dp_list_lines.dart` 패딩 | `vertical: 10` | 같은 상수 | 간격 |
| `interaction/dp_option_row.dart` 패딩 | `vertical: 10` | 같은 상수 | 간격 |
| `data/dp_key_values.dart` 간격 | `SizedBox(height: 6)` | `DpWebDensity.keyValueGap` | 간격 |

**주의 — 렌더가 바뀐다:** 리터럴 `TextStyle(fontSize: 12)` 는 `Text` 가 `DefaultTextStyle` 에 **merge** 하므로 줄 높이를 주변(보통 `bodyMedium` 의 1.6)에서 물려받는다. 토큰 `labelMedium` 은 `height: 16/12` 를 스스로 갖고 있어 merge 후 그 값이 이긴다 ⇒ **행 높이가 바뀐다.** baseline-impact 가 「렌더가 동일해야 하므로 기준선 재기록과 함께 확인하는 것이 싸다」고 적은 지점이다. 이 Task 는 바뀐 높이를 테스트로 고정하고 PR-2 가 기준선을 다시 기록한다.

간격 10·6 은 **시안 그대로다**(`.chk{padding:10px 16px}` · `.kv{gap:6px 16px}`). 8pt 스케일에 없으므로 `DpSpacing` 에 억지로 넣지 않고 출처를 적은 명명 상수로 옮긴다.

**Files:**
- Modify: `packages/dp_design/lib/src/theme/dp_spacing.dart` (`DpWebDensity` 신설)
- Modify: `packages/dp_design/lib/src/states/dp_status_text.dart` · `data/dp_row_line.dart` · `data/dp_list_lines.dart` · `data/dp_key_values.dart` · `interaction/dp_option_row.dart`
- Test: `packages/dp_design/test/states/dp_status_text_test.dart`

**Interfaces:**
- Consumes: `Theme.of(context).textTheme`(= `DpTypography.textTheme`) · `DpColors`
- Produces: `abstract final class DpWebDensity { static const double rowVerticalPadding = 10; static const double keyValueGap = 6; }` — 뒤 Task 는 쓰지 않는다

- [ ] **Step 1: 현재 렌더를 재는 테스트를 쓴다(측정 먼저)**

```dart
  // 리터럴 TextStyle(fontSize:12) 은 DefaultTextStyle 에 merge 되어 줄 높이를
  // 주변에서 물려받는다. 토큰(labelMedium)은 height 16/12 를 스스로 갖고 있어
  // merge 후 그 값이 이긴다 — 이 테스트가 그 전환을 눈에 보이게 고정한다.
  testWidgets('상태 텍스트는 labelMedium(12 · w600 · height 16/12)으로 그려진다', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: const Scaffold(
          body: Align(
            alignment: Alignment.topLeft,
            child: DpStatusText('완료', tone: DpStatusTone.ok),
          ),
        ),
      ),
    );

    final style = tester.widget<Text>(find.text('완료')).style!;
    expect(style.fontSize, 12);
    expect(style.fontWeight, FontWeight.w600);
    expect(style.height, closeTo(16 / 12, 0.001));
    expect(tester.getSize(find.text('완료')).height, closeTo(16, 0.5));
  });
```

`DpStatusText` 의 실제 생성자 시그니처를 먼저 읽고(위치 인자·`tone` 이름) 그대로 맞춘다.

- [ ] **Step 2: RED 확인**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test test/states/dp_status_text_test.dart -r compact`

Expected: FAIL — `style.height` 가 null 이다.

- [ ] **Step 3: `DpWebDensity` 를 신설한다**

`packages/dp_design/lib/src/theme/dp_spacing.dart` 끝에 덧붙인다:

```dart
/// 시안의 웹 문법이 쓰는 비(非)8pt 치수. 8pt 스케일(`DpSpacing`)에 없는 값이라
/// 여기에 이름을 두고 출처를 적는다 — 리터럴로 흩어지면 시안과 대조할 수 없다.
abstract final class DpWebDensity {
  /// 구분선 행의 세로 패딩. 시안 `.chk`·`.rowline`·`.list li` = `padding:10px 16px`.
  static const double rowVerticalPadding = 10;

  /// 키-값 목록의 행 간격. 시안 `.kv{gap:6px 16px}`.
  static const double keyValueGap = 6;
}
```

- [ ] **Step 4: 일곱 소비처를 바꾼다**

`states/dp_status_text.dart`:

```dart
    final base = Theme.of(context).textTheme.labelMedium;
    return Text(
      text,
      softWrap: false,
      overflow: TextOverflow.clip,
      style: base?.copyWith(color: color),
    );
```

`data/dp_row_line.dart` · `data/dp_list_lines.dart` · `interaction/dp_option_row.dart` 의 패딩:

```dart
      padding: const EdgeInsets.symmetric(
        vertical: DpWebDensity.rowVerticalPadding,
        horizontal: DpSpacing.lg, // dp_option_row 는 DpSpacing.md 를 유지한다
      ),
```

`data/dp_row_line.dart` · `interaction/dp_option_row.dart` 의 설명 스타일:

```dart
                  style: text.bodySmall!.copyWith(color: c.textSecondary),
```

`data/dp_key_values.dart`:

```dart
            if (i > 0) const SizedBox(height: DpWebDensity.keyValueGap),
```

`text` 지역 변수가 없는 파일에는 `final text = Theme.of(context).textTheme;` 를 `build` 앞머리에 더한다. 각 파일이 `dp_spacing.dart` 를 이미 import 하는지 확인한다.

- [ ] **Step 5: GREEN 확인 + 세 패키지 전 스위트**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test -r compact && flutter analyze
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/web && flutter test -r compact
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/admin && flutter test -r compact
```

Expected: 전부 통과. 줄 높이가 바뀌어 **행 높이·패널 개수를 세던 테스트가 깨질 수 있다** — 기대값은 실측한 새 값으로 고치고 왜 바뀌었는지(토큰의 `height`)를 그 테스트 주석에 적는다.

- [ ] **Step 6: 390px · 200% 배율 회귀를 확인한다**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test test/data -r compact && flutter test test/interaction -r compact`

Expected: 통과. 이 디렉터리의 200% 테스트가 폭을 직접 재고 있으므로, 줄 높이 변화가 라벨 짜부심으로 번지지 않았음을 여기서 판정한다.

- [ ] **Step 7: 커밋**

```
refactor(dp_design): 리터럴 치수를 타이포·밀도 토큰으로 옮긴다

P3 리뷰가 남긴 리터럴 7군데를 정리했다. 글자 크기 12·13 은 DpTypography 의
labelMedium·bodySmall 로, 8pt 스케일에 없는 시안 값 10·6 은 출처를 적은
DpWebDensity 상수로 옮겼다.

토큰은 리터럴에 없던 height 를 갖고 있어 **줄 높이가 바뀐다**(merge 후 토큰이
이긴다). 바뀐 값을 테스트로 고정했고 P5 의 기준선 재기록이 이 상태를 굳힌다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

### Task 7: 진단·동의 화면의 마감 3건 (M10a · M9 · M11)

**세 건의 실측 근거:**

- **M10a** `diagnostic_page.dart` 의 두 루프가 `SizedBox(height: DpSpacing.sm)` 를 **각 행 뒤**에 놓는다(트랙 루프 · 보기 루프). 마지막 행 뒤에도 8px 이 남아 다음 요소와의 간격이 시안보다 8 넓다. 시안 `.form{gap:14px}` 는 행 **사이**에만 간격을 준다.
- **M9** 진단 시작 화면은 트랙 보기가 **8행**(시안 예시는 3개)이라 폰에서 CTA 가 뷰포트 밖으로 밀린다. 그 깊이를 재는 단언이 없어, 앞으로 행이 더 늘어도 아무도 모른다.
- **M11** `DpCheckRow` 는 체크박스를 `ExcludeFocus` 로 빼서 탭 정지를 **행 하나**로 만든다(`dp_check_row.dart:68`). 그 `ExcludeFocus` 를 지워도 현재 테스트는 전부 통과한다 — 정지 **개수**를 고정하는 테스트가 없다.

**Files:**
- Modify: `apps/web/lib/src/features/diagnostic/presentation/diagnostic_page.dart` (두 루프)
- Test: `apps/web/test/features/diagnostic/diagnostic_page_test.dart`
- Test: `packages/dp_design/test/interaction/dp_check_row_test.dart`

**Interfaces:**
- Consumes: `DpOptionRow`(Task 6 에서 패딩이 `DpWebDensity.rowVerticalPadding` 로 바뀌었다) · `DpCheckRow`
- Produces: 없음(화면·테스트만)

- [ ] **Step 1: M10a 실패 테스트를 쓴다**

`apps/web/test/features/diagnostic/diagnostic_page_test.dart` 에 덧붙인다:

```dart
  // 시안 `.form{gap:14px}` 는 행 **사이**에만 간격을 준다. 루프가 각 행 뒤에
  // 간격을 붙이면 마지막 행 뒤에 여분이 남아 다음 요소가 8px 더 밀린다.
  testWidgets('보기 목록 마지막 행 뒤에 여분 간격이 없다', (tester) async {
    await _pumpDiagnosticStart(tester); // 이 파일의 기존 헬퍼를 쓴다
    await tester.pumpAndSettle();

    final rows = find.byType(DpOptionRow);
    expect(rows, findsWidgets);
    final lastRow = tester.getRect(rows.last);
    final hintOrCta = tester.getRect(
      find.byKey(const ValueKey('diagnostic-track-hint')),
    );
    // 마지막 행과 다음 요소 사이는 DpSpacing.lg(16) 하나뿐이어야 한다.
    expect(hintOrCta.top - lastRow.bottom, closeTo(16, 0.5));
  });
```

이 파일의 기존 pump 헬퍼 이름과 시그니처를 먼저 읽고 그대로 쓴다. `diagnostic-track-hint` 키는 트랙 미선택 상태에서만 있으므로 헬퍼가 트랙을 고르지 않은 상태로 띄우는지 확인한다 — 고르는 헬퍼라면 그 바로 아래 `FilledButton` 을 기준으로 바꾼다.

- [ ] **Step 2: RED 확인**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/web && flutter test test/features/diagnostic/diagnostic_page_test.dart -r compact`

Expected: FAIL — 간격이 24(16 + 여분 8)로 측정된다.

- [ ] **Step 3: 두 루프를 「행 사이에만」으로 고친다**

트랙 루프(현재 `for (final entry in trackLabels.entries) ...[ DpOptionRow(...), const SizedBox(height: DpSpacing.sm) ]`)를 인덱스 기반으로 바꾼다:

```dart
              for (final (index, entry) in trackLabels.entries.indexed) ...[
                // 간격은 행 **사이**에만 둔다 — 뒤에 붙이면 마지막 행 다음에
                // 여분이 남아 다음 요소가 8px 밀린다(시안 `.form{gap:14px}`).
                if (index > 0) const SizedBox(height: DpSpacing.sm),
                DpOptionRow(
                  key: ValueKey('diagnostic-track-${entry.key}'),
                  label: Text(entry.value),
                  selected: selectedTrack == entry.key,
                  onSelect: () => notifier.selectTrack(entry.key),
                ),
              ],
```

보기 루프도 같은 모양으로 바꾼다:

```dart
                for (var index = 0; index < options.length; index++) ...[
                  if (index > 0) const SizedBox(height: DpSpacing.sm),
                  DpOptionRow(
                    key: answerFailed && selectedOptionIndex == index
                        ? ValueKey('diagnostic-option-selected-$index')
                        : ValueKey('diagnostic-option-$index'),
                    role: DpOptionRole.button,
                    label: Text(options[index]),
                    selected: answerFailed && selectedOptionIndex == index,
                    onSelect: busy || answerFailed
                        ? null
                        : () => notifier.submitAnswer(
                            question.id,
                            '{"correct":$index}',
                            timeSpentSec: 5,
                          ),
                  ),
                ],
```

`.indexed` 는 Dart 3 의 `IterableExtensions` 다 — `collection` 패키지 import 가 필요 없다.

- [ ] **Step 4: GREEN 확인**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/web && flutter test test/features/diagnostic -r compact`

Expected: 전부 통과.

- [ ] **Step 5: M9 — 폰에서 CTA 깊이를 재는 테스트를 더한다**

```dart
  // 트랙 보기가 8행이라(시안 예시는 3개) 폰에서 CTA 가 뷰포트 밖으로 밀린다.
  // 스크롤되므로 결함은 아니지만, 행이 더 늘면 사용자가 CTA 를 찾기 어려워진다 —
  // 지금 깊이를 고정해 다음 변경이 조용히 더 밀지 못하게 한다.
  testWidgets('390 폭에서 진단 시작 CTA 는 뷰포트 3배 안에 있다', (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(390, 844);
    addTearDown(tester.view.reset);

    await _pumpDiagnosticStart(tester);
    await tester.pumpAndSettle();

    final cta = find.widgetWithText(FilledButton, '진단 시작하기');
    expect(cta, findsOneWidget);
    // 스크롤 위치 0 기준의 절대 y. 844 × 3 = 2532 를 넘으면 행이 늘어난 것이다.
    expect(tester.getRect(cta).top, lessThan(2532));
  });
```

CTA 의 실제 라벨과 위젯 타입을 화면 코드에서 읽어 맞춘다(스크롤 가능한 화면이므로 `findsOneWidget` 이 실패하면 `tester.scrollUntilVisible` 없이도 트리에 있는지 먼저 확인한다).

- [ ] **Step 6: M11 — 탭 정지 개수를 고정하는 테스트를 더한다**

`packages/dp_design/test/interaction/dp_check_row_test.dart` 에 덧붙인다:

```dart
  // 체크박스는 `ExcludeFocus` 로 포커스에서 빠져 있고 행 래퍼가 정지를 소유한다.
  // 그 `ExcludeFocus` 를 지워도 기존 테스트는 전부 통과했다 — 정지 **개수**를
  // 고정해야 회귀를 잡는다(P4 독립 리뷰 M11).
  testWidgets('행 두 개의 탭 정지는 정확히 두 개다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: Scaffold(
          body: Column(
            children: [
              DpCheckRow(
                label: const Text('첫째'),
                value: false,
                onChanged: (_) {},
              ),
              DpCheckRow(
                label: const Text('둘째'),
                value: false,
                onChanged: (_) {},
                last: true,
              ),
            ],
          ),
        ),
      ),
    );

    final stops = <int>[];
    for (var i = 0; i < 5; i++) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump();
      final node = FocusManager.instance.primaryFocus;
      if (node != null) stops.add(identityHashCode(node));
    }
    // 5번 Tab 을 눌러도 서로 다른 정지는 두 개뿐이어야 한다(그 뒤 순환).
    expect(stops.toSet().length, 2);
  });
```

`LogicalKeyboardKey` 를 쓰려면 `import 'package:flutter/services.dart';` 가 필요하다.

- [ ] **Step 7: 테스트를 돌린다**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test test/interaction/dp_check_row_test.dart -r compact
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/web && flutter test test/features/diagnostic -r compact
```

Expected: 전부 통과. M11 테스트가 `2` 가 아니라 `4` 를 보면 `ExcludeFocus` 가 작동하지 않는 것이다 — **테스트 기대값을 4 로 낮추지 말고** 위젯을 고친다.

- [ ] **Step 8: 커밋**

```
fix(web): 진단·동의 화면의 마감 3건

- 보기·트랙 루프가 각 행 뒤에 간격을 붙여 마지막 행 다음에 여분 8px 이
  남았다(P4 독립 리뷰 M10a). 간격을 행 사이에만 둔다.
- 390 폭에서 진단 시작 CTA 깊이를 고정하는 단언을 더했다(M9) — 트랙 보기가
  8행이라 CTA 가 접히는데 그 깊이를 재는 테스트가 없었다.
- DpCheckRow 의 탭 정지 개수를 고정했다(M11). ExcludeFocus 를 지워도 기존
  테스트가 전부 통과해 회귀를 잡지 못했다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

### Task 8: 마이페이지 `.prof` 를 시안과 1:1 로 맞춘다 (M6c)

**실측한 불일치:** 시안 `mypage` 화면에서

- `.prof` 의 태그는 **배지**다 — `<span class="tag">첫 경로</span> <span class="tag">7일 연속</span>`
- 사이드 `프로필` 패널의 `.kv` 가 **목표 트랙 · 목표 · 경력(년)** 이다

현재 구현(`mypage_page.dart:197-200`)은 **둘을 뒤바꿔** 놓았다: 배지 자리에 프로필 3필드(`trackLabel`·`goalLabel`·`경력 N년`)를 넣고, 시안에 있는 사이드 kv 는 만들지 않았다. 그래서 P4 리뷰 M6c 가 「태그 3개가 바로 아래 편집 폼의 같은 3필드를 반복한다」고 지적했다 — 원인은 중복이 아니라 **자리 교환**이었다.

**결정(사용자, 2026-09-28):** **시안 100%.** 그리고 **요청 추가는 필요하지 않다** — `MyPageLoaded` 가 이미 `DashboardSummary? dashboard` 를 들고 있고(`mypage_controller.dart:29` 가 병렬로 읽는다) 그 모델에 `List<String> badges` 와 `int streakDays` 가 있다. 오늘 화면이 같은 값을 `today_panels.dart:112-121` 에서 「연속 학습 N일」 + 배지 태그로 그린다 — 같은 문구를 재사용한다.

**Files:**
- Modify: `apps/web/lib/src/features/mypage/presentation/mypage_page.dart`
- Test: `apps/web/test/features/mypage/mypage_page_test.dart`

**Interfaces:**
- Consumes: `MyPageLoaded.profile`(`ProfileView`: avatar·bio·learningGoal·targetTrack·experienceYears) · `MyPageLoaded.dashboard`(`DashboardSummary`: `badges`·`streakDays`) · `DpKeyValues` · `DpPanel` · `DpTag`
- Produces: 없음

- [ ] **Step 1: 실패 테스트를 쓴다**

```dart
  // 시안 mypage: `.prof` 의 태그는 배지(첫 경로·7일 연속)이고, 프로필 3필드는
  // 사이드 `프로필` 패널의 kv 다. P4 는 둘을 뒤바꿔 넣었다(독립 리뷰 M6c).
  testWidgets('.prof 태그는 배지이고 프로필 3필드는 사이드 kv 다', (tester) async {
    await _pumpMyPage(tester); // 이 파일의 기존 헬퍼. dashboard 를 함께 준다
    await tester.pumpAndSettle();

    // 배지가 머리에 있다.
    expect(find.text('첫 경로'), findsOneWidget);
    expect(find.text('7일 연속'), findsOneWidget);

    // 프로필 필드는 머리의 태그가 아니라 사이드 kv 에 있다.
    final sideKv = find.byKey(const ValueKey('mypage-profile-kv'));
    expect(sideKv, findsOneWidget);
    expect(
      find.descendant(of: sideKv, matching: find.text('백엔드 (Spring)')),
      findsOneWidget,
    );

    // 머리의 Wrap 에는 프로필 필드 태그가 없다.
    final profHeader = find.byKey(const ValueKey('mypage-prof'));
    expect(
      find.descendant(of: profHeader, matching: find.textContaining('경력')),
      findsNothing,
    );
  });
```

헬퍼 `_pumpMyPage` 가 `dashboard` 를 null 로 주고 있으면 `badges: ['첫 경로'], streakDays: 7` 를 가진 `DashboardSummary` 를 주도록 고친다. 트랙 라벨 문자열은 화면의 `trackLabels` 맵에서 실제 값을 읽어 쓴다.

- [ ] **Step 2: RED 확인**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/web && flutter test test/features/mypage -r compact`

Expected: FAIL — `mypage-profile-kv` 가 없고 머리에 「경력 …」 태그가 있다.

- [ ] **Step 3: 머리의 태그를 배지로 바꾼다**

`mypage_page.dart` 의 `if (trackLabel != null || goalLabel != null || p.experienceYears != null) ...[ ... Wrap(... DpTag 3개 ...) ]` 블록을 배지로 교체한다. 바깥 `Row` 에 `key: const ValueKey('mypage-prof')` 를 준다.

```dart
                        // 시안 `.prof` 의 태그는 배지다 — 프로필 3필드는 사이드
                        // `프로필` 패널의 kv 가 맡는다. 두 자리를 바꿔 넣으면
                        // 머리의 태그가 바로 아래 편집 폼을 반복한다(M6c).
                        if (badgeLabels.isNotEmpty) ...[
                          const SizedBox(height: DpSpacing.sm),
                          Wrap(
                            key: const ValueKey('mypage-prof-badges'),
                            spacing: DpSpacing.sm,
                            runSpacing: DpSpacing.sm,
                            children: [
                              for (final b in badgeLabels) DpTag(label: b),
                            ],
                          ),
                        ],
```

`build` 앞머리에서 배지 라벨을 만든다(오늘 화면과 같은 문구):

```dart
    // 오늘 화면(`today_panels.dart`)이 쓰는 것과 같은 값·문구다. 요청은 늘지
    // 않는다 — `MyPageLoaded` 가 이미 `dashboard` 를 들고 있다.
    final summary = state.dashboard;
    final badgeLabels = <String>[
      ...?summary?.badges,
      if (summary != null && summary.streakDays > 0) '${summary.streakDays}일 연속',
    ];
```

`state` 의 실제 변수명(`s`·`loaded` 등)은 그 파일의 것을 그대로 쓴다.

- [ ] **Step 4: 사이드에 `프로필` kv 패널을 만든다**

사이드 칼럼(`DpSide` 의 children)의 **첫 항목**으로 넣는다 — 시안에서 `프로필` 이 `AI 멘토 초대` 위에 있다.

```dart
          DpPanel(
            key: const ValueKey('mypage-profile-kv'),
            title: const DpPanelTitle('프로필'),
            // 시안 사이드 `.kv`: 목표 트랙 · 목표 · 경력(년).
            child: DpKeyValues(
              entries: [
                if (trackLabel != null)
                  (key: '목표 트랙', value: Text(trackLabel)),
                if (goalLabel != null) (key: '목표', value: Text(goalLabel)),
                if (p.experienceYears != null)
                  (key: '경력(년)', value: Text('${p.experienceYears}')),
              ],
            ),
          ),
```

`DpKeyValues` 의 `entries` 실제 레코드 타입을 위젯 소스에서 읽어 맞춘다(`(key: String, value: Widget)` 형태인지 확인).

- [ ] **Step 5: GREEN 확인**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/web && flutter test test/features/mypage -r compact && flutter analyze`

Expected: 통과 · analyze 0.

- [ ] **Step 6: 세 필드가 전부 null 인 경우를 확인한다**

kv 항목이 0개면 빈 패널이 남는다. `entries` 가 비면 패널 자체를 만들지 않도록 감싼다:

```dart
          if (trackLabel != null || goalLabel != null || p.experienceYears != null)
            DpPanel( /* 위와 같음 */ ),
```

그 경우를 덮는 테스트를 더한다:

```dart
  testWidgets('프로필 3필드가 모두 비면 사이드 kv 패널을 만들지 않는다', (tester) async {
    await _pumpMyPage(tester, profile: _emptyProfile); // 헬퍼에 인자를 더한다
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('mypage-profile-kv')), findsNothing);
  });
```

- [ ] **Step 7: 커밋**

```
fix(web): 마이페이지 `.prof` 를 시안과 1:1 로 맞춘다

시안의 `.prof` 태그는 배지(첫 경로·7일 연속)이고 프로필 3필드는 사이드
`프로필` 패널의 kv 다. P4 는 둘을 뒤바꿔 배지 자리에 프로필 필드를 넣고 사이드
kv 를 만들지 않았다 — 독립 리뷰 M6c 가 「태그가 편집 폼을 반복한다」고 지적한
것의 실제 원인이 이 자리 교환이었다.

요청은 늘지 않는다: MyPageLoaded 가 이미 DashboardSummary 를 들고 있고 그
모델에 badges·streakDays 가 있다(오늘 화면이 같은 값을 같은 문구로 그린다).

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

### Task 9: `PlaceholderPage` 를 지운다 (M3)

**실측:** `grep -rn "PlaceholderPage" apps packages --include=*.dart` 가 **정의 파일 자신의 두 줄만** 돌려준다 — 프로덕션 소비처가 0곳이다. P4 계획의 대조표가 실재하지 않는 화면 한 줄을 잡고 있었다.

**Files:**
- Delete: `apps/web/lib/src/features/common/presentation/placeholder_page.dart`
- Delete: 그 파일의 테스트(있으면)

**Interfaces:**
- Consumes: 없음
- Produces: 없음

- [ ] **Step 1: 소비처가 0임을 다시 확인한다(지우기 전 실측)**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && grep -rn "PlaceholderPage" apps packages --include=*.dart | grep -v "/build/"
```

Expected: `placeholder_page.dart` 자신의 줄만. **다른 파일이 하나라도 나오면 이 Task 를 중단하고 보고한다.**

- [ ] **Step 2: 파일과 테스트를 지운다**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && git rm apps/web/lib/src/features/common/presentation/placeholder_page.dart
ls apps/web/test/features/common/ 2>/dev/null | grep -i placeholder
```

테스트 파일이 있으면 그것도 `git rm` 한다.

- [ ] **Step 3: 분석·테스트**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/web && flutter analyze && flutter test -r compact
```

Expected: analyze 0 · 테스트 전부 통과.

- [ ] **Step 4: 커밋**

```
chore(web): 소비처가 없는 PlaceholderPage 를 지운다

프로덕션 소비처가 0곳이었다(정의 파일 자신 외 참조 없음). P4 계획의 화면
대조표가 실재하지 않는 화면 한 줄을 잡고 있었다(독립 리뷰 M3).

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

### Task 10: `DpNavRail` 의 레일 항목 라벨 중복을 없앤다

**실측:** `dp_nav_rail.dart` 의 항목은 펼침 상태에서 `Text(d.label)` 을 보이게 그리고(`:245`), 그 전체를 `Semantics(button: true, label: d.label, selected: selected)` 로 감싼다(`:264-267`). 라벨이 시맨틱스 트리에 **두 번** 올라가 스크린리더가 `'대시보드\n대시보드'` 로 읽는다. `apps/admin` 전용 위젯이다(web 은 P2 부터 헤더를 쓴다).

**Files:**
- Modify: `packages/dp_design/lib/src/shell/dp_nav_rail.dart`
- Test: `packages/dp_design/test/shell/dp_nav_rail_test.dart`

**Interfaces:**
- Consumes: 항목 모델의 `label`
- Produces: 공개 API 불변

- [ ] **Step 1: 실패 테스트를 쓴다**

```dart
  // 펼침 상태에서 보이는 Text 와 래퍼 Semantics.label 이 둘 다 트리에 올라가
  // 스크린리더가 라벨을 두 번 읽었다. 래퍼가 라벨을 소유하고 보이는 Text 는
  // 시맨틱스에서 빠져야 한다.
  testWidgets('펼친 레일 항목의 라벨은 한 번만 읽힌다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: DpTheme.light(),
        home: const Scaffold(
          body: DpNavRail(/* 이 파일의 기존 테스트와 같은 인자 · extended: true */),
        ),
      ),
    );

    expect(find.bySemanticsLabel('대시보드'), findsOneWidget);
    expect(find.bySemanticsLabel(RegExp(r'대시보드[\s\S]*대시보드')), findsNothing);
  });
```

`DpNavRail` 의 실제 필수 인자와 항목 모델은 같은 파일의 기존 테스트를 그대로 복사해 쓴다. 라벨 문자열도 그 픽스처의 것을 쓴다.

- [ ] **Step 2: RED 확인**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test test/shell/dp_nav_rail_test.dart -r compact`

Expected: FAIL — 라벨이 두 번 나온다.

- [ ] **Step 3: 보이는 Text 를 시맨틱스에서 뺀다**

`dp_nav_rail.dart` 의 펼침 분기에서 `Expanded(child: Text(...))` 를 감싼다:

```dart
                if (extended) ...[
                  const SizedBox(width: DpSpacing.md),
                  // 래퍼 `Semantics(label: d.label)` 가 이미 라벨을 소유한다 —
                  // 보이는 Text 까지 트리에 올라가면 스크린리더가 두 번 읽는다.
                  Expanded(
                    child: ExcludeSemantics(
                      child: Text(
                        d.label,
                        overflow: TextOverflow.ellipsis,
                        style: text.bodyMedium?.copyWith(
                          color: selected ? c.headerText : c.headerMuted,
                          fontWeight: selected
                              ? FontWeight.w600
                              : FontWeight.w400,
                        ),
                      ),
                    ),
                  ),
                ],
```

- [ ] **Step 4: GREEN 확인 + admin 회귀**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/packages/dp_design && flutter test -r compact
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/admin && flutter test -r compact
```

Expected: 양쪽 전부 통과.

- [ ] **Step 5: 커밋**

```
fix(dp_design): DpNavRail 항목의 라벨 중복을 없앤다

펼침 상태에서 보이는 Text 와 래퍼 Semantics.label 이 둘 다 트리에 올라가
스크린리더가 `대시보드\n대시보드` 로 읽었다. 래퍼가 라벨을 소유하므로 보이는
Text 를 ExcludeSemantics 로 뺐다. admin 전용 위젯이다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

### Task 11: PR-1 을 올리고 CI 로 판정한 뒤 머지한다

**Files:**
- 없음(게이트)

**Interfaces:**
- Consumes: Task 1~10 의 커밋
- Produces: frontend `develop` 의 새 머지 커밋 — Task 12 의 base

- [ ] **Step 1: 전체 게이트를 로컬에서 돌린다**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && dart run melos run format && dart run melos run analyze && dart run melos run test
```

Expected: format 0 changed · analyze 0(web 의 `current_mission_controller.dart` `unawaited_return_in_try_block` 1건은 `origin/develop` 에도 있는 **로컬 3.47 전용 린트**라 무시한다 — CI 3.44.1 은 녹색) · 테스트 전부 통과.

- [ ] **Step 2: 변경 파일에 설정 파일이 섞이지 않았는지 확인한다**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && git diff --stat origin/develop`

Expected: `packages/dp_design`·`apps/web`·`apps/admin` 아래 소스·테스트만. `.vscode`·`analysis_options.yaml`·`*.iml`·`pubspec.lock` 이 보이면 되돌린다.

- [ ] **Step 3: 푸시하고 PR 을 만든다**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && git push -u origin feat/s3-p5-carryover
```

PR 본문에 담을 것: 닫는 이월 항목 표(Task 1~10) · 렌더가 바뀐 위젯 목록(`DpNextActionBand` 그림자 · `DpSteps` 높이 · 리터럴→토큰의 줄 높이 · 마이페이지 머리·사이드) · **「기준선은 PR-2 가 다시 기록한다」** 는 문장. 끝에 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

- [ ] **Step 4: CI 를 끝까지 지켜본다**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && gh pr checks --watch`

기대 잡: `analyze-test` · `browser-ux` · `perf-gate` · `produce-atomic-pair` · `web-image-config-contract`(off/on). `admin-image`·`web-image`·`web-image-release-contract`·ET13 auth 는 skipping.

**`perf-gate` 가 +5% 회귀로 실패하면** 그것은 이 PR 이 만든 실제 변화다 — 실패 로그의 라우트·지표를 읽어 원장에 적고 **Task 15(perf 재기록)로 이월**한다. 게이트를 느슨하게 고치지 않는다.

**`browser-ux` 가 실패하면** 상세는 잡 로그가 아니라 아티팩트에 있다:

```
gh run download <run-id> -n leva-browser-ux-<sha>-run-<run-id>-attempt-<n>
```

받은 `latest.json` 의 실패 시나리오에서 `details.routes` 를 읽으면 규칙 id·impact·노드 수가 나온다.

**`perf-gate` 가 `locator('flt-semantics-placeholder')` 120초 초과로 죽으면** 하네스 flake 일 수 있다. 판정 조건 셋을 먼저 확인한다: ① 같은 라우트의 다른 run 이 같은 잡에서 통과했는가 ② 그 라우트를 이 PR 이 건드렸는가 ③ 바뀐 위젯을 그 라우트가 쓰는가(`grep`). 셋 다 「아니다」면 실패 잡만 재실행한다(`gh run rerun <run-id> --failed`). 판정 근거를 원장에 남긴다.

- [ ] **Step 5: 실패 0 을 확인하고 머지한다**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && gh pr view --json mergeStateStatus,statusCheckRollup
```

전 잡이 pass/skipping 이고 실패가 0 이며 `mergeStateStatus=CLEAN` 이면 머지한다(기본 merge commit):

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && gh pr merge --merge`

머지 커밋 SHA 를 원장에 적는다.

---

### Task 12: `browser-ux` 가 P4 가 바꾼 화면을 보게 한다

**이 Task 가 P5 의 실질이다.** 현재 `tools/browser_ux/run.mjs:22` 의 `ROUTES` 는 8항목 = **7화면**(`/dashboard`·`/path`·`/community` ×3 보드·`/mentor`·`/sandbox`·`/content/:slug`)뿐이고, P4 가 바꾼 나머지 **14화면**은 axe·타깃·오버플로 게이트가 한 번도 방문하지 않는다.

**도달 가능성은 추측하지 않고 `gateRedirect` 로 증명한다.** 그 함수는 순수 함수(`apps/web/lib/src/app/router.dart:50`)라 단위 테스트로 라우트별 도달을 초 단위에 판정할 수 있다. 실측한 결론(먼저 Step 1 이 이것을 테스트로 고정한다):

| mock 프로필 | 상태 | 도달 가능한 라우트 |
|---|---|---|
| `onboarded`(기존) | 인증 · consent DONE · onboarding DONE | `/community/post/10` · `/community/post/10/edit` · `/community/1` · `/community/1/edit` · `/community/new` · `/community/new/post` · `/settings` · `/mypage` |
| `guest`(신설) | 미인증 | `/login` · `/diagnostic` · `/beta-pending` · `/auth/callback` |
| `consent`(신설) | 인증 · consent **PENDING** | `/consent` |

`onboarded` 빌드에서 `/login`→`/dashboard` · `/consent`→`/path` · `/diagnostic`→`/path` · `/beta-pending`→`/dashboard` · `/auth/callback`→`/dashboard` 로 **전부 돌려보낸다** — 그 라우트를 기존 `ROUTES` 에 적는 것은 다른 화면을 두 번 재는 테스트가 된다.

**덮지 못하는 것(기록하고 넘긴다):** 진단 **문항·결과** 화면은 `/diagnostic` 안의 단계이고 URL 로 도달하지 않는다. 클릭을 하는 새 시나리오가 필요하므로 이 Task 의 범위 밖이다 — Task 17 이 `baseline-impact-p5.md` 에 미커버로 적는다.

**Files:**
- Modify: `apps/web/lib/src/data/web_mock_fixtures.dart` (프로필 `guest`·`consent`)
- Test: `apps/web/test/app/gate_redirect_test.dart` (도달 판정)
- Modify: `tools/browser_ux/run.mjs` (`--routes=` 옵션 · `ROUTES` 확장)
- Modify: `tools/browser_ux/run.test.mjs`
- Modify: `.github/workflows/ci.yml` (`browser-ux-onboarding` 잡)

**Interfaces:**
- Consumes: `gateRedirect(AuthState auth, String location, {bool missionSpineEnabled, bool hasDiagnosticContinuation, bool diagnosticPathHandoffRequested})`
- Produces: `run.mjs` 의 `--routes=<쉼표 목록>` 옵션(생략하면 `ROUTES` 기본값) · mock 프로필 문자열 `'guest'`·`'consent'`

- [ ] **Step 1: 도달 가능성을 고정하는 테스트를 쓴다**

`apps/web/test/app/gate_redirect_test.dart` 에 덧붙인다(그 파일의 기존 `AuthState` 생성 헬퍼를 그대로 쓴다):

```dart
  // browser-ux 의 ROUTES 에 라우트를 넣기 전에 그 빌드에서 실제로 도달하는지
  // 증명한다. gateRedirect 는 순수 함수라 초 단위로 판정할 수 있다 — 도달하지
  // 않는 라우트를 ROUTES 에 적으면 다른 화면을 두 번 재는 테스트가 된다.
  group('browser-ux 라우트 도달', () {
    test('onboarded 빌드: 커뮤니티 상세·작성·설정·마이페이지는 통과한다', () {
      for (final location in const [
        '/community/post/10',
        '/community/post/10/edit',
        '/community/1',
        '/community/1/edit',
        '/community/new',
        '/community/new/post',
        '/settings',
        '/mypage',
      ]) {
        expect(
          gateRedirect(_onboarded, location, missionSpineEnabled: true),
          isNull,
          reason: location,
        );
      }
    });

    test('onboarded 빌드: 온보딩 라우트는 전부 돌려보낸다', () {
      expect(gateRedirect(_onboarded, '/login', missionSpineEnabled: true), '/dashboard');
      expect(gateRedirect(_onboarded, '/consent', missionSpineEnabled: true), '/path');
      expect(gateRedirect(_onboarded, '/diagnostic', missionSpineEnabled: true), '/path');
      expect(gateRedirect(_onboarded, '/beta-pending', missionSpineEnabled: true), '/dashboard');
      expect(gateRedirect(_onboarded, '/auth/callback', missionSpineEnabled: true), '/dashboard');
    });

    test('guest 빌드: 로그인·진단·베타 대기·콜백이 통과한다', () {
      for (final location in const [
        '/login',
        '/diagnostic',
        '/beta-pending',
        '/auth/callback',
      ]) {
        expect(
          gateRedirect(_guest, location, missionSpineEnabled: true),
          isNull,
          reason: location,
        );
      }
      expect(gateRedirect(_guest, '/mypage', missionSpineEnabled: true), '/login');
    });

    test('consent 빌드: 동의 화면이 통과한다', () {
      expect(gateRedirect(_consentPending, '/consent', missionSpineEnabled: true), isNull);
      expect(gateRedirect(_consentPending, '/mypage', missionSpineEnabled: true), '/consent');
    });
  });
```

`_onboarded`·`_guest`·`_consentPending` 은 그 파일의 기존 `AuthState` 헬퍼로 만든다(`_guest` = `AuthUnauthenticated`, `_consentPending` = 인증 + `consentStatus: ConsentStatus.pending`).

- [ ] **Step 2: 테스트를 돌린다**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/web && flutter test test/app/gate_redirect_test.dart -r compact`

Expected: 전부 PASS(코드는 이미 그렇게 동작한다). **하나라도 FAIL 이면 위 표가 틀린 것이다** — 실제 반환값을 읽어 표와 이 계획을 고치고 보고한다.

- [ ] **Step 3: mock 프로필 두 개를 신설한다**

`apps/web/lib/src/data/web_mock_fixtures.dart` 의 프로필 주석과 사용자 픽스처를 고친다:

```dart
/// 빌드 시 `--dart-define=MOCK_PROFILE=<pending|onboarded|consent|guest>` 로 고르는
/// mock 유저 프로필.
///
/// 기본 `pending` 은 온보딩 게이트(진단) 시연용이다. 브라우저 UX·성능 자동화처럼
/// 백엔드 없이 `/dashboard` 이후 화면에 도달해야 하는 실행은 `onboarded` 를 쓴다.
/// `consent` 는 동의 화면(`/consent`)에, `guest` 는 미인증 화면(`/login`·
/// `/diagnostic`·`/beta-pending`·`/auth/callback`)에 도달하기 위한 것이다 —
/// 라우터 게이트가 그 화면들을 인증 상태에서 전부 돌려보내기 때문이다.
const String mockProfile = String.fromEnvironment(
  'MOCK_PROFILE',
  defaultValue: 'pending',
);

/// `POST /auth/refresh` 가 돌려주는 mock 유저. 알 수 없는 [profile] 은 `pending`
/// 으로 안전하게 떨어진다. `guest` 는 유저를 돌려주지 않는다 — 아래 참조.
Map<String, dynamic> mockAuthRefreshUser({String profile = mockProfile}) => {
  'id': 'u-mock',
  'email': 'learner@devpath.ai',
  'nickname': '지수',
  'role': 'LEARNER',
  'onboardingStatus': profile == 'onboarded' ? 'DONE' : 'PENDING',
  'consentStatus': profile == 'consent' ? 'PENDING' : 'DONE',
};
```

`guest` 는 **세션 복원이 실패해야** 미인증이 된다. `POST /auth/refresh` 픽스처가 `mockProfile == 'guest'` 일 때 401 을 돌려주게 한다 — 그 픽스처 맵의 실제 키 이름(`'POST /auth/refresh'`)을 읽고 값을 프로필에 따라 가르는 함수로 바꾼다. 픽스처 맵이 `const` 라면 `guest` 분기를 담을 수 있도록 getter 로 바꾼다.

- [ ] **Step 4: 프로필별 픽스처의 단위 테스트를 더한다**

```dart
  test('guest 프로필은 세션 복원을 401 로 거절한다', () {
    final (status, _) = webMockFixturesFor('guest')['POST /auth/refresh']!;
    expect(status, 401);
  });

  test('consent 프로필의 유저는 consentStatus 가 PENDING 이다', () {
    expect(mockAuthRefreshUser(profile: 'consent')['consentStatus'], 'PENDING');
  });
```

실제 접근자 이름(`webMockFixtures` 를 함수로 바꿨는지)에 맞춰 쓴다.

- [ ] **Step 5: `run.mjs` 에 `--routes=` 를 더하고 `ROUTES` 를 넓힌다**

```js
export const ROUTES = [
  '/dashboard',
  '/path',
  '/community',
  '/community?board=QNA',
  '/community?board=FEEDBACK',
  '/mentor',
  '/sandbox',
  '/content/future-async-await',
  // S3-P4 가 바꿨는데 이 러너가 한 번도 방문하지 않던 화면들. mock id 는
  // `web_mock_fixtures.dart` 의 `GET /community/posts/10`·`/questions/1` 이다.
  '/community/post/10',
  '/community/post/10/edit',
  '/community/1',
  '/community/1/edit',
  '/community/new',
  '/community/new/post',
  '/settings',
  '/mypage',
];

/// 실행할 라우트. `--routes=/a,/b` 로 덮을 수 있다 — 온보딩 화면은 라우터
/// 게이트 때문에 다른 mock 프로필로 빌드해야 도달하므로 별도 잡이 그 목록을
/// 넘긴다(`browser-ux-onboarding`).
function routesOf(options) {
  if (!options.routes) return ROUTES;
  const list = options.routes.split(',').map((s) => s.trim()).filter(Boolean);
  if (!list.length) throw new Error('--routes= was empty');
  return list;
}
```

`usage` 문자열에 `[--routes=/a,/b]` 를 더하고, `run()` 안에서 `const routes = routesOf(options);` 를 만들어 **두 소비처**(`overflow-and-targets` 의 `for (const route of ROUTES)` 와 `axe` 의 같은 줄)를 `routes` 로 바꾼다.

- [ ] **Step 6: `run.test.mjs` 에 옵션 테스트를 더한다**

```js
test('routesOf: 기본은 ROUTES, --routes 는 그것을 덮는다', () => {
  assert.deepEqual(routesOf({}), ROUTES);
  assert.deepEqual(routesOf({ routes: '/login, /consent' }), ['/login', '/consent']);
  assert.throws(() => routesOf({ routes: '' }), /empty/);
});
```

`routesOf` 를 `export` 한다.

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && node --test tools/browser_ux/run.test.mjs`

Expected: PASS.

- [ ] **Step 7: 로컬에서 새 라우트를 실제로 재고 결함을 고친다**

Docker 가 켜져 있어야 한다. 빌드(약 100초):

```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/apps/web && flutter build web --release --no-pub --no-web-resources-cdn --dart-define=USE_MOCK=true --dart-define=MISSION_SPINE_ENABLED=true --dart-define=MOCK_PROFILE=onboarded --dart-define=HOME_BASE_URL=http://127.0.0.1:1
```

러너 의존성(한 번, 네트워크 필요):

```
MSYS_NO_PATHCONV=1 docker run --rm --platform linux/amd64 -v "D:/workspace/dpa/.worktrees/frontend-s3p5-20260928:/work" -w /work/tools/browser_ux mcr.microsoft.com/playwright:v1.55.0-noble npm ci --ignore-scripts --no-audit --no-fund
```

axe 만 먼저(약 1~2분):

```
MSYS_NO_PATHCONV=1 docker run --rm --platform linux/amd64 --network none --ipc=host -v "D:/workspace/dpa/.worktrees/frontend-s3p5-20260928:/work" -w /work/tools/browser_ux mcr.microsoft.com/playwright:v1.55.0-noble node run.mjs --dist=/work/apps/web/build/web --out=/work/evidence/browser-ux/local.json --only=axe
```

그 다음 `--only=overflow-and-targets`. 실패가 나오면 `evidence/browser-ux/local.json` 의 해당 시나리오 `details.routes` 에서 규칙 id·impact·노드를 읽는다.

**나올 가능성이 높은 것(PR-A 에서 같은 원인으로 이미 한 번 잡혔다):** 가로로 잘리는 표의 axe `scrollable-region-focusable`(serious). 마이페이지 커뮤니티 활동 표가 `DpWebTable` 이고 링크가 있는 표라면 통과하지만, 좁은 폭에서 링크 없는 칼럼만 보이면 걸린다. 수정은 `DpWebTable` 에 있고 **포커스 노드를 스크롤 뷰 *안*에** 둬야 한다(밖에 두면 웹 시맨틱스가 tabindex 를 overflow 요소가 아니라 그 부모에 붙여 axe 가 계속 잡는다). 이미 그렇게 돼 있으므로, 새로 걸리는 노드가 있으면 그 노드가 `DpWebTable` 밖인지부터 확인한다.

결함을 하나 고칠 때마다 이 Step 의 axe 실행을 다시 돌려 **닫힘을 실측으로 확인**하고, 고친 내용마다 커밋을 나눈다.

- [ ] **Step 8: `browser-ux-onboarding` 잡을 만든다**

`.github/workflows/ci.yml` 에 기존 `browser-ux` 잡을 본으로 새 잡을 더한다. 차이는 세 가지다: 프로필 3종을 각각 빌드하고, 각 빌드에 맞는 `--routes` 를 넘기고, `--only` 로 라우트 순회 시나리오만 돌린다.

```yaml
  # 온보딩·미인증 화면은 라우터 게이트가 onboarded 빌드에서 전부 돌려보낸다
  # (apps/web/test/app/gate_redirect_test.dart 가 그 표를 고정한다). 그래서 프로필별로
  # 따로 빌드해 라우트 순회 시나리오(axe · overflow-and-targets)만 돌린다.
  browser-ux-onboarding:
    runs-on: ubuntu-24.04
    env:
      RENDERER_IMAGE: mcr.microsoft.com/playwright:v1.55.0-noble@sha256:ffc33305f7b4b04057ae4a0caa70aad4fde87454fb403a1a22e7f931707dfcf9
    strategy:
      fail-fast: false
      matrix:
        include:
          - profile: guest
            routes: /login,/diagnostic,/beta-pending,/auth/callback
          - profile: consent
            routes: /consent
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0
      - uses: subosito/flutter-action@1a449444c387b1966244ae4d4f8c696479add0b2 # v2.23.0
        with:
          flutter-version: '3.44.1'
          channel: stable
          cache: true
      - name: Resolve and bootstrap locked workspace
        shell: bash
        run: |
          set -euo pipefail
          lock_sha256_before="$(sha256sum pubspec.lock | awk '{print $1}')"
          dart pub get --enforce-lockfile
          dart run melos bootstrap --enforce-lockfile
          test "$(sha256sum pubspec.lock | awk '{print $1}')" = "${lock_sha256_before}"
      - name: Build mock web release for ${{ matrix.profile }}
        shell: bash
        working-directory: apps/web
        run: |
          set -euo pipefail
          flutter build web --release --no-pub --no-web-resources-cdn \
            --dart-define=USE_MOCK=true \
            --dart-define=MISSION_SPINE_ENABLED=true \
            --dart-define=MOCK_PROFILE=${{ matrix.profile }} \
            --dart-define=HOME_BASE_URL=http://127.0.0.1:1
      - name: Install pinned runner dependencies
        shell: bash
        run: |
          set -euo pipefail
          docker pull --platform linux/amd64 "${RENDERER_IMAGE}"
          docker run --rm --platform linux/amd64 \
            -v "${GITHUB_WORKSPACE}:/work" \
            -w /work/tools/browser_ux \
            "${RENDERER_IMAGE}" \
            npm ci --ignore-scripts --no-audit --no-fund
      - name: Run route sweep without network
        shell: bash
        run: |
          set -euo pipefail
          docker run --rm --platform linux/amd64 --network none --ipc=host \
            -v "${GITHUB_WORKSPACE}:/work" \
            -w /work/tools/browser_ux \
            "${RENDERER_IMAGE}" \
            node run.mjs \
              --dist=/work/apps/web/build/web \
              --out=/work/evidence/browser-ux/${{ matrix.profile }}.json \
              --routes=${{ matrix.routes }} \
              --only=axe,overflow-and-targets \
              --built-from="${GITHUB_SHA}"
      - name: Preserve report
        if: always()
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2
        with:
          name: leva-browser-ux-${{ matrix.profile }}-${{ github.sha }}-run-${{ github.run_id }}-attempt-${{ github.run_attempt }}
          path: evidence/browser-ux/
          if-no-files-found: warn
          retention-days: 30
```

`--only` 가 쉼표 목록을 받는지 `run.mjs` 의 `wants()` 구현을 읽어 확인한다 — 하나만 받는다면 쉼표를 지원하게 고치고 `run.test.mjs` 에 그 테스트를 더한다.

- [ ] **Step 9: 로컬에서 두 프로필을 재고 결함을 고친다**

`guest`·`consent` 로 각각 빌드해 Step 7 과 같은 명령으로 `--routes` 를 넘겨 돌린다. **`/login` 은 P4 리뷰 I1 이 「bare 라우트라 셸이 폭 상한을 못 준다」로 고친 화면이라 처음 재는 화면 중 가장 위험하다** — 1920px 넘침과 타깃 크기를 특히 본다.

결함마다 고치고 다시 재 닫힘을 확인한 뒤 커밋한다.

- [ ] **Step 10: 커밋**

```
test(browser-ux): P4 가 바꾼 14화면을 게이트가 보게 한다

러너가 8항목(7화면)만 방문해 P4 가 바꾼 커뮤니티 상세·작성·수정·설정·
마이페이지·로그인·동의·진단·베타 대기가 axe·타깃·오버플로 게이트를 한 번도
지나지 않았다.

- gateRedirect(순수 함수)로 라우트별 도달을 테스트로 고정했다. onboarded
  빌드는 온보딩 라우트 5개를 전부 돌려보낸다 — 그 라우트를 ROUTES 에 적으면
  다른 화면을 두 번 재는 테스트가 된다.
- onboarded 로 도달하는 8라우트를 ROUTES 에 더했다.
- 미인증·동의 화면을 위해 mock 프로필 guest·consent 를 신설하고, 프로필별
  빌드로 라우트 순회만 돌리는 browser-ux-onboarding 잡을 더했다.
- run.mjs 에 --routes= 옵션을 더했다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

### Task 13: `expectations.json` 을 실측 근거와 함께 갱신한다

**실측:** 이 파일은 시나리오 17개의 기대값이 아니라 **`community_desktop` 키보드 순회 8정지 하나**만 고정한다(나머지 시나리오는 자기검증형이다). `recorded_from` 이 아직 **`ff4a886`**(S3-P2 커밋)인데 notes 는 「S3-P4b … CI 36319166732(PR #237) 실측」을 말한다 — PR-B 가 값과 notes 는 갱신하고 이 필드를 옮기지 않았다.

**Files:**
- Modify: `tools/browser_ux/expectations.json`

**Interfaces:**
- Consumes: Task 12 의 CI 실행 결과(순회가 바뀌었는지)
- Produces: 없음

- [ ] **Step 1: 현재 순회를 CI 실측으로 읽는다**

Task 12 의 PR CI 에서 `browser-ux` 잡의 아티팩트를 받아 `keyboard-traversal` 시나리오의 실제 정지 목록을 읽는다.

```
gh run download <run-id> -n leva-browser-ux-<sha>-run-<run-id>-attempt-<n>
```

- [ ] **Step 2: 값과 provenance 를 갱신한다**

정지 목록이 바뀌었으면 새 값으로 갱신한다. 바뀌지 않았어도 `recorded_from` 과 notes 는 고친다:

```json
  "recorded_from": "<이 PR 의 head SHA>",
  "notes": [
    "community_desktop: /community 1440px 에서 Tab 순서(첫 8 정지). CI 36212413896(S3-P2 상단 헤더 셸) 실측.",
    "S3-P2 로 바뀐 것: 푸터 링크 4개가 순회에 새로 들어왔다. 화면 안 순서(검색·최신순·글 작성·행)는 DpWebShell 이 DpAppShell 의 WidgetOrderTraversalPolicy 를 승계해 develop 과 같다.",
    "헤더는 순회에 들어오지 않는다 — 레일이 빠져 있던 것과 같은 라우트 FocusScope 경계 문제이고 docs/community-information-architecture/handoff.md §9.6-5 에 있다.",
    "러너는 14번 Tab 을 눌러 앞 N 개만 비교한다. 마지막 정지가 반복되는 꼬리는 develop 실측(35932928056)에도 똑같이 있다 — 이 셸이 만든 것이 아니다.",
    "S3-P4b 로 바뀐 것: 목록 행의 탭 정지가 「제목 + 집계 한 덩어리」에서 **제목 링크 하나**로 줄었다. 카드 나열(DpListRow)이 표(DpWebTable)가 되면서 답변·추천이 각자 숫자 칼럼이 됐고, 그 셀들은 포커스 대상이 아니다 — 접근성 컨트롤은 제목의 DpLink.title 하나다. CI 36319166732(PR #237) 실측.",
    "S3-P5 로 바뀐 것: <바뀐 내용, 또는 「순회는 그대로다」> — CI <run-id> 실측. 앞선 갱신이 recorded_from 을 P2 커밋(ff4a886)에 남겨 둔 것도 함께 고쳤다.",
    "갱신은 실측 후 PR 리뷰 승인으로만 한다."
  ]
```

- [ ] **Step 3: 커밋**

```
test(browser-ux): 순회 기대값의 provenance 를 실측 SHA 로 맞춘다

recorded_from 이 S3-P2 커밋(ff4a886)에 남아 있는데 notes 는 S3-P4b 실측을
말하고 있었다 — PR #237 이 값과 notes 만 옮겼다. 이 PR 의 CI 실측으로 둘을
맞췄다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

### Task 14: `perf/baseline.json` 을 CI 측정값으로 재기록한다

**실측:** `built_from` 이 **`a4753024`**(마지막 커밋은 「font diet」 재기준선)이고 P2·P3·P4 의 렌더 변화가 반영돼 있지 않다. 20행(5라우트 × mobile/desktop × cold/warm)이며 `samples: 3` 이다(CI 는 `--runs=5` 로 돈다).

**재기록 방법 — 로컬에서 재지 않는다.** CI `perf-gate` 잡이 핀 컨테이너·고정 조건에서 측정한 `evidence/perf/latest.json` 을 아티팩트로 올린다. 그 파일을 그대로 `perf/baseline.json` 으로 커밋하면 `built_from` 이 자동으로 그 SHA 가 되고 측정 환경이 CI 와 같다. 로컬 측정값을 커밋하면 머신 편차가 기준선에 들어간다.

**Files:**
- Modify: `perf/baseline.json`

**Interfaces:**
- Consumes: Task 12 PR 의 `perf-gate` 아티팩트 `leva-perf-<sha>-run-<run-id>-attempt-<n>`
- Produces: 없음

- [ ] **Step 1: 현재 기준선의 provenance 를 기록한다**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && PYTHONUTF8=1 py -c "import json;d=json.load(open('perf/baseline.json',encoding='utf-8'));print(d['built_from'], len(d['routes']), d['routes'][0]['samples'])"`

기록: 옛 `built_from`·행 수·샘플 수. 원장에 적는다.

- [ ] **Step 2: CI 아티팩트를 받는다**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && gh run download <run-id> -n leva-perf-<sha>-run-<run-id>-attempt-<n> --dir /c/Users/deepe/AppData/Local/Temp/claude/perf-p5
```

- [ ] **Step 3: 새 기준선이 옛 것보다 나쁘지 않은지 눈으로 본다**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && PYTHONUTF8=1 py -c "
import json
old=json.load(open('perf/baseline.json',encoding='utf-8'))
new=json.load(open(r'C:/Users/deepe/AppData/Local/Temp/claude/perf-p5/latest.json',encoding='utf-8'))
k=lambda r:(r['route'],r['profile'],r['phase'])
o={k(r):r for r in old['routes']}
print('old built_from',old['built_from'],'-> new',new['built_from'])
for r in new['routes']:
    b=o.get(k(r))
    if not b: print('NEW ROW',k(r)); continue
    ot,nt=b['transfer_bytes']['total'],r['transfer_bytes']['total']
    print(f\"{k(r)} transfer {ot} -> {nt} ({(nt-ot)/ot*100:+.2f}%)\")
"
```

전송량이 **+5% 를 넘는 행**이 있으면 그것은 회귀다 — 기준선으로 굳히기 전에 원인을 찾아 보고한다(번들에 무엇이 늘었는지). 행 집합이 달라졌으면(라우트 추가·삭제) 왜인지 원장에 적는다.

- [ ] **Step 4: 기준선을 교체한다**

Run:
```
cp /c/Users/deepe/AppData/Local/Temp/claude/perf-p5/latest.json /d/workspace/dpa/.worktrees/frontend-s3p5-20260928/perf/baseline.json
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && node tools/perf/gate.mjs --report=perf/baseline.json --baseline=perf/baseline.json --budget=perf/budget.json
```

Expected: 자기 자신과 비교하므로 회귀 0. **절대 예산(`perf/budget.json`) 위반이 나오면** 기준선이 예산을 넘은 것이다 — 그 값을 보고한다(예산을 올리지 않는다).

- [ ] **Step 5: 커밋**

```
perf: S3(P2~P4) 이후 전송량·CWV 기준선을 다시 기록한다

built_from 이 a4753024(「font diet」 재기준선)에 머물러 P2 셸 교체·P3 공용
위젯 웹화·P4 25화면 개편의 렌더가 기준선에 없었다. CI perf-gate 가 핀
컨테이너·고정 조건에서 측정한 아티팩트를 그대로 기준선으로 옮겼다 — 로컬
측정값은 머신 편차가 섞이므로 쓰지 않았다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

### Task 15: DESIGN.md §3·§5 를 개정한다

**실측한 현재 상태:** §5(반응형)는 이미 720 경계 주석을 갖고 있고 §6 의 포인터 타깃도 이미 24px 로 옮겨져 있다 — 스펙이 P1·P5 로 나눠 적은 것 중 P1 몫이 끝나 있다. 남은 것은 두 가지다.

1. **§3 의 소비 줄(`DESIGN.md:177`)이 `DpInteractiveCard` 를 「클릭 카드 베이스」로 가리키는데 그 위젯은 프로덕션 소비처를 잃었다**(P3 가 카드를 구분선 행·패널로 바꿨다).
2. **§5 에 `DpCols` 의 2열 경계(840)와 그것이 시안의 720 과 다른 이유**가 없다(Task 1 의 결정).

**Files:**
- Modify: `DESIGN.md` (§3 의 소비 줄 · §5 끝)

**Interfaces:**
- Consumes: Task 1 의 결정 · Task 5·6 이 만든 새 사실(`DpPanel` 의 잉크 표면 · `DpWebDensity`)
- Produces: 없음

- [ ] **Step 1: `DpInteractiveCard` 의 소비처를 실측한다**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && grep -rn "DpInteractiveCard" apps packages --include=*.dart | grep -v "/build/"`

소비처가 0곳이면 §3 에서 지운다. admin 에만 남았으면 「admin 전용」으로 적는다. 결과에 따라 Step 2 의 문장을 고른다.

- [ ] **Step 2: §3 의 소비 줄을 고친다**

`DESIGN.md` 의 다음 줄을

```
> 소비: `context.appTokens`. 최대폭 제약은 `DpMaxWidth`, 상태 스타일은 `DpStateStyle`, 클릭 카드 베이스는 `DpInteractiveCard`, 텍스트 선택은 `DpSelectable`, 스크롤바는 `DpScrollbar`. (UI/UX 고도화 로드맵 Phase 0 산출.)
```

다음으로 바꾼다(Step 1 의 실측에 맞게 `DpInteractiveCard` 절을 넣거나 뺀다):

```
> 소비: `context.appTokens`. 최대폭 제약은 `DpMaxWidth`, 상태 스타일은 `DpStateStyle`, 텍스트 선택은 `DpSelectable`, 스크롤바는 `DpScrollbar`. (UI/UX 고도화 로드맵 Phase 0 산출.)
>
> **웹 문법(S3)**: 면은 `DpPanel`(표면 + 1px 테두리 + 반경 8)이 담당하고 클릭 카드
> 베이스는 쓰지 않는다 — S3-P3 가 카드 나열을 구분선 행(`DpListRow`·`DpRowLine`·
> `DpListLines`)과 표(`DpWebTable`)로 바꿨다. `DpPanel` 은 안쪽에
> `Material(type: transparency)` 를 스스로 둬 `ListTile`·`InkWell` 의 잉크가
> 패널 경계 안에서 일어나게 한다(S3-P5). 8pt 스케일에 없는 시안 치수는
> `DpWebDensity`(행 세로 패딩 10 · 키-값 간격 6)에 이름으로 둔다.
```

- [ ] **Step 3: §5 끝에 `DpCols` 경계 근거를 적는다**

§5 의 마지막 불릿 다음에 덧붙인다:

```
- **본문 2열(`DpCols`)의 경계는 840**(= Expanded 의 시작)이다. 시안의 컨테이너
  질의는 720(`@container (max-width:720px)`)이지만 그 한 규칙이 `.cols`(2:1
  분할)와 `.login`(1.1:0.9 대등 분할)을 함께 묶고 있고, 2:1 에서는 720 에서
  사이드가 약 220px 로 눌려 패널 제목조차 줄바꿈한다. 시안 갤러리는 1440·390 두
  폭만 보여 720~839 는 시각 검토된 적이 없으므로 검토되지 않은 구간에서 더
  보수적인 경계를 택했다. 셸의 720(햄버거 ↔ 주 메뉴)과는 성격이 다른 경계다.
  (S3-P5 사용자 결정 2026-09-28. 코드: `packages/dp_design/lib/src/layout/dp_cols.dart`.)
```

- [ ] **Step 4: 문서와 코드가 어긋나지 않는지 확인한다**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && grep -n "DpInteractiveCard\|DpWebDensity\|840" DESIGN.md | head -20
grep -rn "class DpWebDensity" packages/dp_design/lib
```

Expected: DESIGN.md 가 말하는 이름이 전부 코드에 있다.

- [ ] **Step 5: 커밋**

```
docs(design): DESIGN.md §3·§5 를 S3 의 웹 문법으로 개정한다

- §3 의 소비 줄이 프로덕션 소비처를 잃은 `DpInteractiveCard` 를 「클릭 카드
  베이스」로 가리키고 있었다(P3 리뷰 이월). 면은 DpPanel 이 담당한다는 사실과
  DpPanel 의 잉크 표면·DpWebDensity 를 적었다.
- §5 에 DpCols 의 2열 경계 840 과 그것이 시안의 720 과 다른 이유를 적었다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

### Task 16: PR-2 를 올리고 CI 로 판정한 뒤 머지한다

**Files:**
- 없음(게이트)

**Interfaces:**
- Consumes: Task 12~15 의 커밋
- Produces: frontend `develop` 의 머지 커밋 — 릴리스 캠페인의 base

- [ ] **Step 1: 브랜치를 분리한다**

Task 12~15 를 PR-1 머지 뒤의 `develop` 에서 새 브랜치로 진행했는지 확인한다. 아니라면:

```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && git fetch origin && git log --oneline -1 origin/develop
```

- [ ] **Step 2: 전체 게이트를 로컬에서 돌린다**

Run:
```
cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && dart run melos run format && dart run melos run analyze && dart run melos run test && node --test tools/browser_ux/run.test.mjs tools/perf/gate.mjs 2>/dev/null; node --test tools/browser_ux/run.test.mjs && node --test tools/perf/measure.test.mjs tools/perf/gate.test.mjs
```

Expected: 전부 통과.

- [ ] **Step 3: 푸시하고 PR 을 만든다**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && git push -u origin feat/s3-p5-gate-baseline`

PR 본문: 새로 게이트에 들어온 라우트 목록 · 그 과정에서 드러나 고친 결함 목록(각 건의 axe 규칙 id·impact) · perf 기준선의 옛→새 `built_from` 과 전송량 델타 표 · DESIGN.md 개정 요약 · **덮지 못한 것(진단 문항·결과)** 을 명시.

- [ ] **Step 4: CI 를 끝까지 지켜본다**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && gh pr checks --watch`

새 잡 `browser-ux-onboarding (guest)`·`(consent)` 가 함께 돌아야 한다. 안 보이면 워크플로 문법을 확인한다.

- [ ] **Step 5: 실패 0 을 확인하고 머지한다**

Run: `cd /d/workspace/dpa/.worktrees/frontend-s3p5-20260928 && gh pr view --json mergeStateStatus,statusCheckRollup`

전 잡 pass/skipping · 실패 0 · `mergeStateStatus=CLEAN` 이면 `gh pr merge --merge`. 머지 커밋 SHA 를 원장에 적는다.

---

### Task 17: documents 에 핸드오프·원장·기준선 영향·스펙 정정을 남긴다

**Files:**
- Create: `docs/superpowers/handoff-2026-09-28-s3-p5-complete.md`
- Create: `docs/superpowers/plans/2026-09-28-s3-p5-baseline-rerecord/execution-ledger.md`
- Create: `docs/superpowers/plans/2026-09-28-s3-p5-baseline-rerecord/baseline-impact-p5.md`
- Modify: `docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` (§7 의 P5 행)

**Interfaces:**
- Consumes: Task 11·16 의 머지 커밋 SHA · 전 Task 의 판정
- Produces: 릴리스 캠페인의 입력

- [ ] **Step 1: 워크트리를 확인한다**

이 계획 파일이 있는 워크트리(`D:\workspace\dpa\.worktrees\documents-s3p5-plan`, 브랜치 `docs/s3-p5-plan`)를 그대로 쓴다.

- [ ] **Step 2: 실행 원장을 쓴다**

`execution-ledger.md` 에 Task 별로 적는다: 무엇을 했는가 · **계획과 달라진 판정(`Ruling:`)** · 실측값 · 실패했다가 통과한 것. P4 의 원장(`plans/2026-09-27-s3-p4-screen-groups/execution-ledger.md`)을 형식의 본으로 삼는다.

- [ ] **Step 3: `baseline-impact-p5.md` 를 쓴다 — 릴리스 캠페인의 입력**

담을 것:

- PR-1 이 바꾼 렌더 목록(`DpNextActionBand` 그림자 · `DpSteps` 높이 · 리터럴→토큰의 줄 높이 · 마이페이지 머리·사이드 · 진단 간격)
- PR-2 가 새로 게이트에 넣은 라우트와 거기서 고친 결함
- 새 perf 기준선의 `built_from` 과 전송량 델타
- **ET13 판정**: 승인된 기준선은 레포에 없고(`baseline_status` 가 스키마 상수) 승인 워크플로가 `release_id` 를 요구하므로 **릴리스 캠페인 단계**다. 캠페인이 할 일 = `produce-atomic-pair` 산출물로 `et13-baseline-approval` 을 디스패치(보호 환경 승인은 사람) — `gh` CLI 가 리뷰어 계정이라 **직접 `gh workflow run` 하지 말고** `automation/dispatch-<release_id>` 디스패처를 쓴다
- **덮지 못한 것**: 진단 **문항·결과** 화면은 `/diagnostic` 안의 단계라 URL 로 도달하지 않아 axe·타깃 게이트가 보지 못한다. 클릭하는 새 시나리오가 필요하다(S3 이후 과제)
- 시안과 1:1 이 되지 못한 항목의 **갱신된 표** — Task 8 이 마이페이지 표시 이름·프로필 kv 중 kv 를 닫았으므로 P4 의 8건에서 줄어든다. 남은 항목과 각각 필요한 백엔드 계약 변경

- [ ] **Step 4: 스펙 §7 의 P5 행을 고친다**

```
| P5 | 기준선 재기록: browser-ux 게이트 커버리지 확장(+14화면)·`expectations.json`·perf baseline·DESIGN.md §3·§5 개정. P3·P4 이월 판단 13건 | **ET13 baseline 승인은 P5 가 아니라 릴리스 캠페인 단계다** — 커밋된 카탈로그는 `baseline_status` 를 스키마 상수로 `pending_external_review` 에 고정하고, 승인 워크플로가 `release_id` 를 요구한다(S3-P5 실측) |
```

- [ ] **Step 5: 핸드오프를 쓴다**

`handoff-2026-09-28-s3-p5-complete.md` — 앞 핸드오프(`handoff-2026-09-28-s3-p4-complete.md`)를 형식의 본으로. 좌표 표(레포·브랜치·커밋) · P5 가 끝낸 것 · **다음 착수점 = 릴리스 캠페인**(develop→main + gitops 승격 + ET13 baseline 승인) · 다음 세션이 알아야 할 함정 · 지우지 말 워크트리.

- [ ] **Step 6: 커밋하고 PR 을 올린다**

Run:
```
cd /d/workspace/dpa/.worktrees/documents-s3p5-plan && dart format --version >/dev/null 2>&1; git add docs && git diff --cached --stat && git commit -F <메시지 파일> && git push -u origin docs/s3-p5-plan
```

커밋 메시지:

```
docs: S3-P5 계획·원장·기준선 영향·핸드오프

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

- [ ] **Step 7: CI 를 확인하고 머지한다**

documents 레포는 CI 가 가볍다. 녹색이면 `gh pr merge --merge`.

- [ ] **Step 8: 메모리를 갱신한다**

`C:\Users\deepe\.claude\projects\D--workspace-dpa\memory\MEMORY.md` 의 최신 항목을 S3-P5 완결로 바꾼다. 인덱스 줄은 **200자 안**으로 하고 상세는 토픽 파일(`devpath-web-native-redesign-2026-09-19.md`)에 넣는다 — MEMORY.md 가 이미 크기 한계를 넘어 잘린 상태다.

---

## Self-Review

**1. 스펙 커버리지.** 스펙 §7 의 P5 행이 말하는 네 항목 중 — browser-ux `expectations.json` = Task 13 · perf baseline = Task 14 · DESIGN.md §3·§5 = Task 15 · ET13 visual/a11y baseline = **범위 밖으로 판정**하고 근거와 함께 Task 17 이 스펙에 적는다. 스펙 §8(게이트)의 「PR 마다 analyze-test · browser-ux · perf-gate · web-image-config-contract · produce-atomic-pair」는 Task 11·16 이 지킨다. 스펙 §9(운영 반영)는 P5 다음 단계이고 Task 17 의 핸드오프가 그 착수점을 넘긴다. 스펙 §7 원칙의 「시안이 부족하면 시안을 먼저 보강한다」는 Task 1 에서 720~839 가 시각 검토되지 않았다는 사실을 문서화하는 것으로 대신했다(그 구간 시안을 새로 만드는 것은 P5 범위를 넘는다 — 사용자 판단이 필요하면 Task 1 에서 멈추고 묻는다).

**2. 플레이스홀더.** 없다. 다만 다음 세 곳은 **실행자가 레포에서 이름을 읽어 맞춰야** 하는 자리이고 그 사실을 각 스텝에 적었다: 기존 pump 헬퍼 이름(Task 7·8), `DpNavRail`·`DpStatusText`·`DpKeyValues` 의 실제 생성자 시그니처(Task 6·8·10), `web_mock_fixtures` 픽스처 맵의 접근자 형태(Task 12). 추측으로 쓰지 말고 읽고 맞추라고 명시했다.

**3. 타입 일관성.** `DpWebDensity.rowVerticalPadding`·`DpWebDensity.keyValueGap`(Task 6 정의 → Task 15 문서), `routesOf(options)`·`--routes=`(Task 12 정의 → Task 12 Step 8 사용), `ValueKey('dp-step-<i>')`(Task 2), `ValueKey('mypage-profile-kv')`·`ValueKey('mypage-prof')`·`ValueKey('mypage-prof-badges')`(Task 8), mock 프로필 문자열 `'guest'`·`'consent'`(Task 12 전체) — 이름이 정의된 Task 와 쓰는 Task 가 일치한다.

**4. Review Focus 커버리지.** 다섯 줄 각각의 테스트가 Task 2·4·5·7·12 에 스텝으로 들어가 있다.

**5. 순서 의존.** Task 1~10 → 11(머지) → 12~15 → 16(머지) → 17. Task 6 이 줄 높이를 바꾸므로 **Task 7 의 간격 측정은 Task 6 뒤에** 와야 한다(그래서 6 다음이 7 이다). Task 14 는 Task 12 PR 의 CI 아티팩트를 입력으로 쓰므로 그 PR 이 한 번은 돌아야 한다 — 12·13·14·15 를 한 PR 에 담고 CI 를 두 번 돌리는 순서다(1차: 12·13·15 로 측정 → 아티팩트로 14 → 2차: 전 잡 녹색).
