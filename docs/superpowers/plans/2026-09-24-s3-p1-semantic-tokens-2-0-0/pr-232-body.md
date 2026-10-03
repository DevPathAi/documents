## S3-P1 (spec documents `specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` §5.3·§5.4·§7 P1)

- `DpRadius` 4/6/8/6/12 · new `DpDensity` 30/8/24 · `AppTokens.standard` 1120/760/280/80/8 + `headerHeight` 56
- `rail*` → `header*` colour tokens (values unchanged) · manifest **2.0.0** with `--dp-density-*`, `--dp-color-header-*`, `--dp-layout-header-height`
- `DpTheme`: 30px controls, `shrinkWrap` tap targets, dense inputs; `DpTapTarget` default 24 · browser-ux `MIN_TARGET` 24 · DESIGN.md §1/§3/§5/§6
- Claude Design `Leva Design Tokens` re-synced to 2.0.0; homepage mirror follows in devpath-home-page (separate PR)

Two implementation notes beyond the plan: `SegmentedButton` computes its own height floor (`textButtonMinHeight` 40 + `visualDensity.baseSizeAdjustment.dy`), so its theme carries `VisualDensity.compact` (→ 32px); `IconButton` takes `minimumSize` only, because a `fixedSize` box clipped the composite `flutter_quill` toolbar icons (42 overflow assertions in three web tests).

## Local gates
`dart format --set-exit-if-changed .` clean · `melos run analyze` no issues (4 packages) · `melos run test` 1595 passing (dp_design 255 · web 1010 · admin 156 · dp_core 174).

## Expected CI
analyze-test · browser-ux (24px targets) · perf-gate (no transfer change) · web-image-config-contract · ET13 produce-atomic-pair — **all ET13 visual fixtures change** (radii/density); baseline re-approval is the P5 human step before the release, not this PR.

## Not in this PR
Shell replacement (P2), widget web grammar / FAB removal (P3), screen groups (P4), baselines (P5). Admin keeps `DpAppShell`/`DpNavRail` on the renamed tokens. Widgets that hard-code 44px stay for P3/P4.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
