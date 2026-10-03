# Code review — S3-P1 semantic token contract 2.0.0

Range: `de316b4..e1bef21` (9 commits, devpath-frontend) + `44b8212` (devpath-home-page).
Reviewed in four passes (docs/tokens, theme, tests, home mirror) plus targeted reads of the
non-diff call sites the change reaches. `flutter test --exclude-tags golden` re-run
independently in `packages/dp_design`: 255 passed.

Paths are relative to `D:/workspace/dpa/.worktrees/frontend-s3p1-20260924` (frontend) and
`D:/workspace/dpa/.worktrees/home-s3p1-mirror-20260924` (home) unless absolute.

## Verdict

Yes — safe to merge to develop as-is; the two Important findings are a published external artifact and two false-coverage tests, neither of which blocks the branch.

## Critical

None.

## Important

**1. The design system published as "2.0.0" ships a header that contradicts the tokens beside it**

- File: `.design-sync/conventions.md:15`, `:21`, `:23`, `:43`
- What breaks: `.design-sync/config.json` sets `"readmeHeader": ".design-sync/conventions.md"`, and
  `.design-sync/scripts/build_ds_readme.py:20` prepends that file verbatim to `ds-bundle/README.md` —
  the artifact Task 7 uploaded to `Leva Design Tokens`. Task 7 updated `NOTES.md` but never this file,
  so the live README now states, directly above a generated token table that says the opposite:
  - line 15 still advertises `rail: --dp-color-rail-bg · --dp-color-rail-text · --dp-color-rail-muted ·
    --dp-color-rail-faint · --dp-color-rail-active · --dp-color-rail-border` — six custom properties that
    no longer exist in `tokens/leva-tokens.css`;
  - line 23 states `Accessibility floor (from guidelines/DESIGN.md §6): 44×44px hit targets`, while
    `guidelines/DESIGN.md` **in the same bundle** now reads `≥24×24` (`DESIGN.md:202`) — it cites a section
    this PR changed to say the opposite;
  - line 43, the "one idiomatic snippet", builds `minHeight: 44, padding: '0 var(--dp-space-xl)'` —
    precisely the 44px/24px geometry contract 2.0.0 replaced with 30px/16px;
  - no `--dp-density-*` row, though every other token family is enumerated in that table;
  - (pre-existing, but re-published under a 2.0.0 label) line 21's layout row still says
    `1440px / 880px / 256px / 72px` — contract 1.0.0 numbers, two generations stale against 1120/760/280/80.
- Failure scenario: someone opens `Leva Design Tokens`, follows the header it leads with, writes
  `background: var(--dp-color-rail-bg)` and gets nothing — CSS custom properties fail silently, so the
  element renders transparent with no console error and no build failure. They then size controls at 44px
  against a contract that just moved to 30/24. The token table three screens down disagrees with the
  instructions they read first. This is the only artifact in this change already live outside the repo.
- Fix: rewrite lines 15/21/23/43, add a density row, re-run `build_ds_readme.py`, re-upload. Then add a
  gate: a test asserting every `--dp-*` name mentioned in `conventions.md` exists in
  `DpSemanticTokenManifest.cssCustomProperties`. Nothing currently tests this file, which is why the
  rename passed straight through it.

**2. Review Focus 1's test is a tautology — the adjacency guarantee does not exist**

- File: `packages/dp_design/test/theme/dp_segmented_button_theme_test.dart`, third test
  (`'FilledButton 은 30px 이고 인접 버튼과 8px 이상 떨어지면 2.5.8 간격 예외를 만족한다'`)
- What breaks: the test builds
  `Row(children: [FilledButton(...), const SizedBox(width: DpSpacing.sm), OutlinedButton(...)])`
  and then asserts `expect(outlined.left - filled.right, greaterThanOrEqualTo(DpSpacing.sm))`. It inserts
  the 8px spacer itself and then asserts the spacer it inserted. Strip every spacing rule from `DpTheme`
  and this test stays green. Nothing in the theme or in any widget enforces separation between adjacent
  controls, so the Review Focus item is reported as covered while being unverified.
- Failure scenario: this PR removed the implicit separation. `tapTargetSize: MaterialTapTargetSize.shrinkWrap`
  on every button theme (`packages/dp_design/lib/src/theme/dp_theme.dart`) means an `IconButton` is now
  exactly 30×30 — confirmed by the new `packages/dp_design/test/theme/dp_theme_density_test.dart:38-40`,
  which measures `Size(30,30)` — instead of the 48×48 padded box it used to get.
  `packages/dp_design/lib/src/shell/dp_chrome_bar.dart:212-245` renders
  `for (final a in inline) IconButton(...)` followed immediately by the overflow `IconButton`
  **with no spacer between them**. On a 390px phone those two targets now touch at 0px where they
  previously had ~18px of implicit padding each, and a thumb aimed at "더 보기" lands on the last inline
  action instead.
- Premise correction, since the verdict depends on it: WCAG 2.2 SC 2.5.8 is satisfied outright by any
  target ≥24×24 CSS px; the spacing exception applies only to **undersized** targets. Flush 30×30 controls
  are AA-conformant. This finding stands as false coverage plus a real ergonomic change on phone widths,
  not as an accessibility violation.
- Fix: either assert the property on a real composition (a widget from the app, with no spacer added by
  the test), or drop the assertion and record honestly that adjacency is a P3 screen-level concern.

## Minor

**3. Review Focus 2 is also not covered — but the underlying risk is smaller than stated**

- File: `packages/dp_design/test/theme/dp_segmented_button_theme_test.dart`, second test
  (`'TextButton 은 30px 컨트롤이고 한 줄 라벨을 자르지 않는다'`)
- What breaks: the `TextButton.icon('실습으로 돌아가기')` sits inside a `Center`, i.e. unbounded width, so
  the label cannot wrap. The test proves the non-wrapping case only.
- Failure scenario: traced the wrapping case — `controlText` is `labelLarge` 14/20
  (`packages/dp_design/lib/src/theme/dp_typography.dart:50-54`) and no `maximumSize` is set, so a two-line
  label grows the button to 40px rather than clipping it. No truncation, but the "controls are 30px"
  contract silently breaks for any width-constrained Korean label and no test notices. Add a
  constrained-width case (`SizedBox(width: 120)`) asserting the growth is graceful.

**4. `dp_chrome_bar`'s overflow budget is calibrated to a button size that no longer exists**

- File: `packages/dp_design/lib/src/shell/dp_chrome_bar.dart:181-189` — `const perAction = 48.0;`,
  `const overflowButton = 48.0;`, `final accountReserve = account != null ? 48.0 + DpSpacing.sm : 0.0;`
- What breaks: every one of those 48s was the rendered `IconButton` width; it is now 30. The budget
  over-reserves 18px per action and 18px for the account, so actions fold into the "더 보기" menu earlier
  than they need to.
- Failure scenario: with three chrome actions at 390px, `fits = floor(123/48) = 2` and
  `inline = floor((123-48)/48) = 1`, so one action renders inline and two are buried in a menu — while
  `3 × 30 + 8 + 30 = 128 ≤ 179` would have fit them all. No user hits this today:
  `apps/web/lib/src/features/shell/presentation/app_shell.dart:298` passes exactly one `chromeAction`,
  which is why this is Minor. But both chrome-bar tests only assert `takeException() == null` / "menu
  exists", so the arithmetic is now entirely unverified, and
  `packages/dp_design/test/shell/dp_chrome_bar_account_gap_test.dart`'s 25-line explanatory comment
  (which reasons explicitly from "account 히트 영역=48 (`IconButton`)") now documents a world that no
  longer exists — a trap for whoever touches this in P2.

**5. Stale rationale in `dp_nav_rail`**

- File: `packages/dp_design/lib/src/shell/dp_nav_rail.dart:99-106`
- What breaks: the comment justifying the vertical mark/toggle stack argues from
  "mark(22) + IconButton(Material 최소 탭 타깃 48) = 70px이 필요해 19px RenderFlex 오버플로" and
  "44px 최소 탭 타깃(DD7)... 44+8=52가 이론 한계". With a 30px toggle, 22+30 = 52 = the available width,
  so the stated impossibility no longer holds.
- Failure scenario: behaviour is unchanged and correct today, but the emphatic
  "이 분기를 가로 Row로 되돌리지 말 것" warning now rests on arithmetic that stopped being true in this
  very commit; a P2 author who checks the maths will find it wrong and may distrust the whole comment.

**6. `DpTapTarget.minSize` 44 → 24 is inert**

- File: `packages/dp_design/lib/src/a11y/dp_tap_target.dart:13`
- What breaks: nothing today — every call site was checked and the widget is used only by its own test.
- Failure scenario: a wrapper whose stated job is "guarantee a minimum target" now guarantees 24 for
  whatever first adopts it, including a touch surface where 24 is the AA floor rather than a good size.
  One line in its doc comment telling touch-surface callers to pass a larger `minSize` would carry the
  intent forward.

**7. The golden baseline is now stale and nothing will ever notice**

- File: `packages/dp_design/test/golden/goldens/` (recorded against card radius 18 and 52px controls),
  gated by `pubspec.yaml:26`
- What breaks: `pubspec.yaml:26` runs `flutter test --exclude-tags golden`, and so did every local
  verification, so the baseline rots silently — no CI job will ever flag it.
- Failure scenario: whoever re-enables goldens later faces a wall of diffs with no way to tell intended
  2.0.0 changes from real regressions. Add it to the P5 baseline re-record list alongside ET13.

**8. DESIGN.md §3 states "컨트롤 높이 30" more firmly than the code delivers**

- File: `DESIGN.md:163` (density bullet)
- What breaks: it discloses the segment exception (`VisualDensity.compact` → 32px) but not the input one.
- Failure scenario: a themed `TextField` measures ~34px
  (`packages/dp_design/test/theme/dp_theme_density_test.dart:23` accepts `[30, 36]`; `bodyLarge` 16/24 +
  `vertical: 5` ×2 = 34). A P3 author sizing a row to the documented 30px finds inputs overflowing it.
  One clause would keep the contract doc honest about both exceptions rather than one.

**9. `DpDensity.rowPadding` is published with no consumer**

- File: `packages/dp_design/lib/src/theme/dp_spacing.dart` (`DpDensity.rowPadding`)
- What breaks: it is projected to CSS and named in DESIGN.md, but nothing reads it in either repo
  (tables/list rows are P3).
- Failure scenario: none today; the "표 행 여백 8" line of the contract is simply unenforced, unlike
  `controlHeight` and `minTarget`, so a P3 divergence would not be caught by any test.

**10. Uncommitted working-tree change**

- File: `packages/dp_design/analysis_options.yaml` (uncommitted `analyzer: exclude: build/**`, from the
  Task 7 token dump into `build/`)
- What breaks: nothing — it is outside the reviewed range and CI passed without it.
- Failure scenario: it rides along into a later commit unnoticed, quietly narrowing the analyzer's scope
  in CI. Worth reverting or committing deliberately.

## Review Focus

1. 390px + 30px controls, adjacent target spacing ≥8px (`DpSpacing.sm`): the test asserts the `SizedBox` it inserted itself, no production adjacency guarantee exists, and `dp_chrome_bar.dart:212-245` now renders flush 30×30 targets (conformance note: ≥24×24 satisfies 2.5.8 outright, so this is usability, not an AA failure) — **not covered**.
2. Long Korean label wrapping in a 30px button: the test's `Center` gives unbounded width so wrapping is impossible, though the real behaviour is benign — no `maximumSize`, so the button grows to 40px and nothing clips — **not covered**.
3. `AppTokens.lerp`/`copyWith` missing the new `headerHeight` field: wired in ctor, `standard`, `copyWith` and `lerp`, and `dp_radius_density_test.dart:31-37` fails on any single omission — **covered**.
4. Home mirror parser selector: `assets/tokens.css:123` keeps the bare `[data-theme="dark"] {` (the dump's `, .dp-theme-dark` was not pasted in), and the new `it()` reads that block in isolation with a regex guard forbidding any surviving `--dp-color-rail-` — **covered**.
5. Dark header contrast, `headerMuted` on `headerActive` ≥ 4.5:1: recomputed independently as 7.41:1 light (`#B7BDCA` on `#272B3F`) and 7.80:1 dark (`#B6BCC8` on `#23263B`) — **covered**.

## Rulings

- Pre-flight conflict, T1 pre-edits the two `'999px'`/`'18px'` assertions that T3 rewrites: **agree** — cost-if-wrong "none" is accurate because T3 restates the whole block.
- Setup, PATH-pinned Flutter 3.44.1 before `melos bootstrap` after plain PATH resolved 3.47.2 and refused the lockfile: **agree** — correctly diagnosed rather than worked around by relaxing the lockfile.
- T2, `sed \b` missed 15 prose mentions followed by Hangul, completed with a Python regex: **agree** — exactly the word-boundary trap this repo has been bitten by before, and catching it in-task beats catching it in review.
- T4, dropped `iconButtonTheme.fixedSize` and kept `minimumSize 30×30`: **agree** — best-evidenced ruling in the file (42 failing assertions across three `apps/web` community tests from the flutter_quill toolbar's composite icon children), and the stated residual cost (a wide child can exceed 30px in width, height stays 30) is accurate.
- T4, added `visualDensity: VisualDensity.compact` to `segmentedButtonTheme`: **agree** — `SegmentedButton` genuinely ignores `minimumSize` and floors at `textButtonMinHeight 40 + baseSizeAdjustment.dy`, so compact is the only lever, and the 32-vs-30 cost is disclosed in `DESIGN.md:163` where it belongs.
- T5, amended the 2026-09-17 findings-table remedy row instead of rewriting it: **agree** — the appended-note form is the right shape, since a reader following the historical row would otherwise undo Task 4, while rewriting it would falsify the record.
- T6, also rewrote `DESIGN.md` §1 as addendum commit `681d102` though the plan named §3/§5/§6 only: **agree** — leaving §1 at "v1.1.0 … 랜딩 mirror는 이 버전을 따라 맞춘다" would have left the SSoT section contradicting the manifest this plan bumps; the extension was minimal, disclosed, and separately committed.
- T7, uploaded the 8 text files only and not the 5 woff2 binaries: **agree** — `fonts.json` is unchanged and the builder sha256-verifies, so the bytes are identical, and incremental sync matches the tool's guidance.
- T8, fixed three analyzer lints in plan-supplied verbatim test code: **agree and necessary** — CI runs `melos run analyze` as a gate so the literal code could not have merged, and `unnecessary_cast` on `lerp` is a genuine plan defect since `AppTokens.lerp` already returns `AppTokens`.
- T9, did not run the visual baseline update (no Docker daemon, pinned-image rule) and opened the home PR as DRAFT: **agree** — both the tool constraint and the standing rule are real, and parking in DRAFT means nothing can merge by accident; this is the correct place to stop.
- T9, left the landing's own 44×44 a11y rule untouched: **agree** — option A was a decision about mirroring token values, spec §3 puts landing design out of scope, and a stricter landing target is never a violation.
- Extension I would add to the ledger: Task 7's rulings stopped at `NOTES.md`, but the task's actual deliverable — the uploaded `ds-bundle/README.md` — carries `.design-sync/conventions.md` verbatim as its header, and that file was never brought to 2.0.0. That omission is Important finding 1 above and is the only gap in an otherwise well-reasoned ledger.
