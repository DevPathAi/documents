# Final fresh-context review — S3-P5 PR-2 (`feat/s3-p5-gate-baseline`, c8edb82..378109c)

Reviewer: fresh-context critic, read-only. Nothing was edited, committed, or pushed.
The worktree was clean before and after this review (`git status --porcelain` empty at both ends).

## Verdict

**REVISE.** The engineering is strong and CI run 2 (`36652115886`) is green on the final tip,
including `perf-gate` 22m54s and both new onboarding legs. But this PR's subject *is* gate
correctness, and the new gate code contains nine concrete defects of exactly the class it was
written to eliminate — caps that scale the wrong way, a waiver that can hide a regression, a sweep
that still goes blind after the first failure, a check name that silently stops being required, and
a frozen provenance SHA that does not exist. Four are one-to-three-line fixes and should land
before merge (F1, F2, F4, F7). No Critical.

Counts: **Critical 0 · Important 9 · Minor 11.**

## Commands I ran (read-only)

- `git log/diff/show/cat-file/merge-base` in both worktrees
- `node --test tools/browser_ux/run.test.mjs` -> **14 pass / 0 fail** (node_modules absent, same condition as the CI step)
- `dart format --output=none --set-exit-if-changed $(git diff --name-only c8edb82..378109c -- '*.dart')` -> **21 files, 0 changed** (`--output=none` writes nothing)
- Python scans of the emoji ranges over `apps/*/lib`, `packages/*/lib`, `apps/web/web`
- **I did NOT run `flutter test`** — so `analysis_options.yaml` / `pubspec.lock` were not touched by me. No restore needed.

---

## F1 — Important — the new job's check name embeds the route list, so the gate silently stops being required

`.github/workflows/ci.yml:850-863` (`browser-ux-onboarding`, `strategy.matrix.include` carrying both `profile` and `routes`).

GitHub derives the check name from *every* matrix key. Evidence from the author's own log
(`.superpowers/sdd/2026-09-28-s3-p5-baseline-rerecord/ci2.log`):

```
browser-ux-onboarding (guest, /login,/diagnostic,/beta-pending,/auth/callback)   pass  3m6s
browser-ux-onboarding (consent, /consent)                                        pass  2m12s
```

**What breaks:** a required-status-check entry must match that whole string. The moment anyone edits
the route list — the one thing this PR exists to make editable — the check name changes, the ruleset
entry stops matching, and a red onboarding job no longer blocks merge. Nothing is emitted; the job
just becomes decorative. Same rot mode as the stale axe waiver the author (correctly) made fail.

**Trigger:** add `/signup` to the guest row -> new check name -> ruleset match lost.

**Fix:** pin the display name to the stable key only:

```yaml
  browser-ux-onboarding:
    name: browser-ux-onboarding (${{ matrix.profile }})
```

`NEEDS_CONTEXT`: whether `browser-ux-onboarding` is (or will be) in the `develop` ruleset's required
checks. That config is not in this repo and I did not query GitHub
(`gh api repos/DevPathAi/devpath-frontend/rulesets` would settle it). If it is never required, the
whole Task 12 expansion is advisory — and that gap is then the finding instead.

---

## F2 — Important — the sweep still goes blind after the first failing route; the author diagnosed this and fixed only half of it

`tools/browser_ux/run.mjs:412` (`did not settle` -> `break`) and `tools/browser_ux/run.mjs:443`
(budget failure -> `break`). The `axe` loop (`run.mjs:506-513`) has no per-route guard at all, so a
`goto` throw there aborts the remaining routes through `scenario()`'s catch.

The ledger names this exact defect as half of Step 7's problem:

> `러너가 그 자리에서 break 해 /settings·/mypage 를 아예 재지 못했다`

Only the cap was changed. The `break` survived — **and it fired again inside this same PR.** CI run 1
failed with `/community/1 did not settle` (route index 10 of 16), so `/community/1/edit`,
`/community/new`, `/community/new/post`, `/settings`, `/mypage` were never measured in that run at
any width. That is 5 of the 8 newly-gated screens, unmeasured, in the run whose artifact became the
frozen `expectations.json` provenance.

**Why it matters:** every first failure costs a full extra CI round (`browser-ux` is 8-11 min) and
hides how many other routes are broken. For a PR that doubles the sweep, this turns a one-round fix
into N rounds.

**Fix:** `continue` instead of `break` in the budget and settle branches (the failure is already
recorded in `failures[]`, and each route re-`goto`s from scratch so no state is carried), and wrap
the axe loop's `goto` in the same try/catch + continue. Add a unit test that a mid-list failure still
produces entries for the later routes.

---

## F3 — Important — the per-route external cap of 40 is 20x the measured norm, so a smaller storm passes

`tools/browser_ux/routes.mjs:51` (`MAX_EXTERNAL_PER_ROUTE = 40`) and `:58`
(`MAX_EXTERNAL_PER_ROUTE_AVERAGE = 8`).

Review Focus #5, answered:

- **Would it catch the 2026-09-26 storm?** Yes. `delta 230 > 40` fires, and `run.test.mjs:93-99` pins it.
- **Can a creep evade it?** Yes, and not only a slow uniform one. With 16 routes the measured norm is
  +2/route (total ~44 including `/sandbox`'s +12 font chunks) against a total budget of 128. So
  **one route can emit +40 — twenty times its norm — and both checks pass** (44 + 38 = 82 < 128). Two
  such routes also pass (120 < 128); only the third trips it.

This is not hypothetical. The ledger records that the `/community/1` emoji storm **reproduced locally
at +5, not +230**, and that the small form was set aside:

> `로컬에서 그 라우트는 +5 로 정착했다. 같은 결함의 작은 모습이고 ...`

A +3..+40 font-fallback storm is therefore a measured shape of this defect, and it is precisely the
band the new cap ignores. Worse, the app-level second layer (F9) has the same blind spot, so the two
layers do not cover for each other.

**Fix:** make the per-route cap relative — e.g. fail on `delta > Math.max(8, 4 * median(deltas))` —
or simply lower `MAX_EXTERNAL_PER_ROUTE` to 16, which still clears `/sandbox`'s measured 12, and keep
the scaled total as the second net.

---

## F4 — Important — on a single-route job the delta cap is dead code and the effective cap is 8, which a font-chunk route trips

`tools/browser_ux/routes.mjs:65-68`, reached from `run.mjs:434-439` with `routeCount: sweepRoutes.length`.

For `browser-ux-onboarding (consent)` `routeCount === 1`, so `budget = 8 * 1 = 8`. The per-route cap
of 40 can never be reached before the total check fires: **the real cap on a one-route job is 8**,
four times stricter than the author's own measured norm for a route fetching its first font chunk
(`/sandbox` +12).

**Trigger:** `/consent` gains any glyph that pulls a first font chunk — a code sample (D2Coding), a
new icon subset, an unloaded weight — and the job fails with
`"/consent external requests total 12 > 8 (1 routes x 8)"`: a storm message for a non-storm.
Structurally the same mistake as the fixed context total of 40 that this PR just removed — a cap that
scales the wrong way with route count.

**Fix:** floor the total, `const budget = Math.max(32, MAX_EXTERNAL_PER_ROUTE_AVERAGE * routeCount);`
and unit-test `routeCount: 1, total: 12` -> `null`.

---

## F5 — Important — the axe waiver can hide a real regression, and its stale check is evaluated per width

`tools/browser_ux/routes.mjs:81-133`, called from `run.mjs:512` once per (route, axe scenario).

Review Focus #4, answered — **yes, it can hide a regression**, two ways:

1. **Route-wide, not node-scoped.** `waiverFor(route)` drops *every* occurrence of
   `aria-command-name` / `aria-prohibited-attr` on those 4 routes (`routes.mjs:119-123`). The measured
   cause is 8 nodes of quill toolbar. If a later change adds a 9th unnamed `role="button"` elsewhere
   on `/community/new` — our own code — the rule still fires, so the waiver is not stale, and the new
   violation is discarded. The runner already carries `nodes` (`run.mjs:188`), so the fix is cheap:
   waive only while the count matches (`{'aria-command-name': 8, 'aria-prohibited-attr': 8}`) and fail
   on `v.nodes !== expected` with a message naming both numbers.

2. **Stale detection is per (route, width).** `axe` runs two scenarios, 390 light and 1240 dark
   (`run.mjs:500`), and `axeFailures` is called independently for each. A waived rule that fires at
   1240 but not at 390 produces **8 hard `stale axe waiver` failures** at 390 for something that is
   not stale. Both rules fire at both widths today (CI run 2 green), but the toolbar is the most
   likely thing here to become responsive — and the waiver's own `followUp` is a toolbar reshape
   (`.bar2`, 12 buttons -> 5). Fix: accumulate `seen` across the whole sweep and evaluate staleness
   once at the end, or key waivers by width.

   Smaller hole in the same function: `seen.add(v.id)` sits *after* the `BLOCKING_IMPACTS` filter
   (`routes.mjs:120-121`), so an axe-core bump that downgrades one of these rules to `moderate` makes
   a still-firing rule report as a **stale waiver**. Move `seen.add(v.id)` above the impact filter.

**Judgment on the ruling itself:** waiving instead of rebuilding the toolbar is the right call.
Reshaping a 12->5 button rich-text toolbar (whose 42px height is pinned by a test) days before
freezing a visual baseline is a worse risk than two unenforced rules on four routes, and the waiver
carries `why`/`followUp` with a test that requires them; the rejected alternative (flutter_quill
11.6.0) is recorded. No objection to the decision — only to the waiver's shape.

---

## F6 — Important — `smallTargets` re-measures through an index locator across a scroll that rebuilds the semantics DOM

`tools/browser_ux/run.mjs:138-167`.

Review Focus #6, answered in three parts:

- **Can the scroll corrupt the overflow measurement that ran just before?** No. `overflow(page)` is
  taken at `run.mjs:414`, before `smallTargets` at `:415`.
- **Can it leak into the next route?** No. Each route enters through `goto()` -> `page.goto` -> a new
  document, so the scroll offset resets. `external_so_far` is read after the scroll (`:422`), which is
  if anything more accurate.
- **Can it corrupt its own measurement?** Yes. `count` is captured once (`:140`) but
  `buttons.nth(index)` is re-resolved on every use (`:144`, `:153`, `:160`). Flutter Web emits
  semantics nodes only for rendered widgets, so `page.mouse.wheel` **adds and removes
  `flt-semantics` nodes**. After the wheel, `buttons.nth(index)` can resolve to a different element
  than the one whose box was measured at `:145`, and the label at `:160` is read after the
  *scroll-back*, i.e. from a third tree state. Net effect: a reported offender's label/size may belong
  to another control, and a genuinely small target can be skipped because the index shifted.

  Secondary: the wheel is aimed at the viewport centre (`:150`). If a nested vertical scrollable sits
  under that point it consumes the wheel, the outer view never moves, the fold-clipping false positive
  survives, and the `-viewportHeight * 20` scroll-back leaves the inner view pinned for the next
  candidate. There is also no assertion that the node actually moved, and each candidate costs 500 ms.

**Fix:** resolve the candidate to a stable handle before scrolling (`const h = await button.elementHandle()`),
capture its label *before* the wheel, re-measure via `h.boundingBox()`, and assert `box.y` changed
before trusting the second reading; otherwise report the original measurement with a `clipped: true`
marker.

---

## F7 — Important — `perf/baseline.json`'s `built_from` is a SHA that does not exist, and it was measured one commit before the tip

`perf/baseline.json:3` — `"built_from": "10f8a5b059d2323999cb878a0788014f37f0e700"`.

```
$ git cat-file -t 10f8a5b059d2323999cb878a0788014f37f0e700
fatal: bad object 10f8a5b059d2323999cb878a0788014f37f0e700
```

`.github/workflows/ci.yml:3-6` is `on: {push: {branches: [main]}, pull_request:}`, so `GITHUB_SHA`
for this run was the ephemeral `refs/pull/240/merge` commit. It is not in the repo, will not exist
once the PR closes, and cannot be checked out. By contrast the *old* value
`a4753024fb84fad2206e6eeb8d961684530f8055` resolves (`chore(et13): re-pin subset fonts`, 2026-09-17,
ancestor of `c8edb82`), so this re-record is a **regression in provenance quality**.

The same PR states the correct convention for the sibling artifact, in `expectations.json`:

> `recorded_from 은 그 측정이 이뤄진 **브랜치 커밋**이다`

and uses a real branch commit there (`13d81c94…` = `13d81c9`). Two conventions in one PR, with the
weaker one applied to the artifact that *is* the frozen performance contract.

**Second half:** CI run 1 (`36649266533`) ran at tip `13d81c9`, i.e. **before** `f08ccdf`
(pictographic emoji removal). So the frozen baseline was measured from a build that is not the merge
candidate. The practical delta is nil — perf `ROUTES` is `/login,/dashboard,/path,/mentor,/community`,
none of which held the emoji, and CI run 2 independently re-measured the final tip against this
baseline and passed at 22m54s — but neither `baseline-impact-p5.md` §5 nor the ledger says so, and
both cite run 1 as the provenance.

The plan is partly at fault (Task 14: `그 파일을 그대로 perf/baseline.json 으로 커밋하면 built_from 이 자동으로 그 SHA 가 되고`),
but Task 13's entire subject was provenance, so this was the one PR where it should have been caught.

**Fix:** set `built_from` to the branch commit whose build was actually copied (`f08ccdf` if run 2's
artifact, `13d81c9` if run 1's), and add a line to `baseline-impact-p5.md` §5 naming the run *and*
the branch commit. Consider a contract assertion that `perf/baseline.json.built_from` resolves
(`git cat-file -e`).

---

## F8 — Important — the boot splash gave every row an LCP, which silently disabled the `ready_ms` absolute check

`tools/perf/gate.mjs:27-31`:

```js
if (p75.lcp_ms !== null && p75.lcp_ms !== undefined) {
  if (p75.lcp_ms > budget.lcp_ms_max) absolute.push(...);
} else if (p75.ready_ms !== null && ... && p75.ready_ms > budget.ready_ms_max) {
  absolute.push(...);
}
```

Measured, old baseline (`git show c8edb82:perf/baseline.json`) vs new:

| | old | new |
|---|---|---|
| `lcp_ms`, all 20 rows | `null` | 44-76 (desktop) · 132-228 (mobile) |
| `ready_ms` cold | 3.80 s desktop · 21.5 s mobile | 3.85 s desktop · 21.5 s mobile |

`perf/budget.json` has `lcp_ms_max: 2500` and `ready_ms_max: 2500`. With `lcp_ms` null the gate
compared `ready_ms`, so 21.5 s was flagged. Now `lcp_ms` is non-null and trivially under 2500, the
`else` branch **never runs**, and a 21.5-second time-to-interactive is invisible to the absolute
budget. The splash is an LCP candidate, not a render; `budget.json`'s own note
(`CanvasKit 은 <canvas> 에 그리므로 브라우저 LCP 후보가 없을 수 있다`) is now false and the fallback it
describes is dead code.

The ledger gets the cause exactly right and stops one step short:

> `같은 c482b54 가 lcp_ms 를 null 에서 48~52 ms 로 바꿨다 ... 렌더가 빨라진 것이 아니라 브라우저에 LCP 후보가 생긴 것이다.`

**Mitigated by:** `budget.enforce_absolute: false`, so today this only changes which *warnings* print —
no gate flips state. That is why this is Important rather than Critical. The harm is deferred to
whoever sets `enforce_absolute: true` believing the absolute thresholds work. Root cause is `c482b54`
on develop, not this PR — but this PR is the approval gate for the baseline and its author was looking
straight at the number.

**Fix (cheap, in this PR):** record it in `baseline-impact-p5.md` §5 as a gate defect with a follow-up.
Real fix (follow-up): compare `ready_ms` against `ready_ms_max` unconditionally, or exclude splash
paints from the LCP candidate set.

---

## F9 — Important — the emoji guard misses most of the family it guards against, can false-positive on comments, and can pass while scanning nothing

`apps/web/test/app/no_pictographic_emoji_test.dart:24-27, 39, 50`.

Review Focus #8, answered — **false negatives yes, false positives yes.**

The regex is `[\u{1F300}-\u{1FAFF}\u{FE0F}]`. I scanned `apps/*/lib`, `packages/*/lib`, `apps/web/web`
for every `Emoji_Presentation=Yes` code point **outside** that range and found **0 current hits**, so
there is no live escape today. As a forward guard it omits, among others:

- `U+1F1E6..U+1F1FF` regional indicators — **flags**, e.g. `KR`, the single most likely emoji for a Korean product to add
- `U+2705` white heavy check mark, `U+274C` cross mark, `U+2B50` star, `U+2728` sparkles, `U+26A1` high voltage, `U+2753` question mark, `U+2795` plus, `U+2B1B` black large square — all default-emoji-presentation, none in Pretendard, all pull Noto Color Emoji
- `U+1F004`, `U+1F0CF`, `U+1F232..U+1F23A`, `U+1FB00..U+1FBFF`

Any one of those reproduces the exact 2651-request storm and walks past the guard. The test's doc
comment justifies the narrow set on the grounds that check/star/circle are in Pretendard — true, but
those are *text*-presentation symbols; it does not follow that the emoji block below `U+1F300` is safe.

Two more defects in the same test:

- **False positives.** `line.trimLeft().startsWith('//')` (`:50`) skips only *full-line* comments. A
  trailing comment (`foo(); // party-popper`) or anything inside `/* ... */` is flagged as a rendered
  string. The repo's own style — comments that explain emoji traps — makes this likely.
- **Vacuous pass.** `if (!dir.existsSync()) continue;` (`:39`) with relative roots (`lib`,
  `../../packages/dp_design/lib`, `../admin/lib`). Run from any cwd other than `apps/web` and all three
  roots miss, `offenders` is empty, and the test **passes while scanning zero files.** Nothing asserts
  that anything was scanned.
- **Scope gap.** `packages/dp_core/lib` is not scanned, and it holds `src/error/` — user-facing message strings.

**Fix:** widen to the Unicode `Extended_Pictographic` ranges (at minimum add `U+1F000-U+1F2FF`,
`U+2600-U+27BF`, `U+2B00-U+2BFF`, `U+1FB00-U+1FBFF`); strip comments properly (everything from `//` to
EOL outside string literals, plus `/* */`); add `packages/dp_core/lib`; and assert `filesScanned > 0`
so the guard cannot go quiet.

---

## Minor findings

- **M1 — `DESIGN.md` §2 now contradicts itself about 메타.** `DESIGN.md:158` still reads
  `메타는 bodySmall 13px`, while the new block at `:160-170` says `.meta` is `context.dpMeta` (12 / 1.6).
  Two adjacent normative statements with no precedence. §2 was Task 15's own subject; amend or
  explicitly supersede the old sentence.
- **M2 — `baseline-impact-p5.md:90` understates the LCP range.** It says `lcp_ms 를 null → 48~52 ms`.
  Measured from the committed file: desktop 44-76, **mobile 132-228**; the mobile half is not mentioned.
  `fcp_ms 5916 → 48` is correct, but only for the `/dashboard` desktop cold row.
- **M3 — `gate.sh`'s exit codes are meaningless, and both scripts it reported as 0 actually failed.**
  `.superpowers/sdd/.../gate.sh:5,19` do `cmd 2>&1 | tail; echo "EXIT=$?"` — `$?` is `tail`'s. `gate.log`
  shows `analyze → ScriptException ... ANALYZE_EXIT=0` and
  `format → Formatted 679 files (4 changed) ... FORMAT_EXIT=0`. Both real failures were reported as
  success by the harness and caught only because the author read the output. Use `set -o pipefail` or
  `${PIPESTATUS[0]}`. (Repo memory already records this exact pitfall.) Both underlying failures are
  correctly explained as local-toolchain-only in the documents ledger, and I independently confirmed the
  changed files are clean: `dart format --output=none --set-exit-if-changed` over the 21 changed Dart
  files -> **0 changed**.
- **M4 — the ledger's stated reason for keeping `/login` in perf `ROUTES` is contradicted by this very
  re-record.** Pre-flight row 9 argues that renaming it
  `would discard comparability with the whole baseline history` — but the re-record already discarded
  that comparability: `samples` 3 -> 5, `fcp_ms` 5864-6132 -> 44-76, `lcp_ms` null -> non-null. The
  **decision** (do not touch perf `ROUTES` in PR-2) is right on scope grounds and the mislabel is
  documented in `baseline-impact-p5.md` §5; only the justification is wrong. Note also that the 4
  `/login` rows are now identical to the `/dashboard` rows except `inp_ms`, so perf covers 4 routes, not 5.
- **M5 — the 24px target check never runs at 200% text scale.** `run.mjs:415` gates on
  `width === 390 && textScale === 100`; 200% is where targets are most likely to shrink. Pre-existing.
- **M6 — `smallTargets(page, HEIGHT)`** (`run.mjs:415`) passes the module constant rather than the live
  viewport height. Correct today because `openPage` always uses `HEIGHT`; fragile if that changes.
- **M7 — `dp_steps_test.dart:130-135`'s padding arithmetic is self-referential** (it uses
  `DpWebDensity.stepVerticalPadding` on both sides), so it would hold for any value of the constant. It
  is saved by the separate `expect(DpWebDensity.stepVerticalPadding, 6)` at `:124`. Prefer the literal
  `12` in the arithmetic.
- **M8 — `settings_page_test.dart:94` cannot distinguish the two semantics nodes.**
  `tester.getSemantics(finder)` walks up to the nearest ancestor with a node, so with
  `Semantics(label:) > Switch` it can read the **wrapper's** label while the `role="switch"` DOM node
  stays nameless — which is exactly what axe checks. The fix is nevertheless proven by measurement
  (`sweep2.log`: `[PASS] axe w=390` and `w=1240` after the change, where the first sweep failed on
  `aria-toggle-field-name`), so this is a weak test, not a wrong fix. Strengthen by asserting the node
  that carries the toggled state holds the label.
- **M9 — the new CI job's `run:` bodies are single ~400-character lines** with runs of spaces where every
  other job uses `\` continuations (verified with `cat -A`: no backslashes, one `$` per logical line).
  Valid shell, but unreviewable in a diff and inconsistent with `browser-ux` and `perf-gate` immediately
  above and below it.
- **M10 — `no_pictographic_emoji_test.dart` lives in `apps/web` but scans `apps/admin` and
  `packages/dp_design`.** Running only the admin or dp_design suites leaves those packages unguarded.
- **M11 — Task 16/17 are still in flight.** `documents-s3p5-plan` has `M execution-ledger.md`,
  `M docs/superpowers/specs/2026-09-19-...-design.md`, `?? baseline-impact-p5.md` — all uncommitted.
  Expected mid-PR, but the spec §7 edit in particular is a cross-repo claim about a merged state.

---

## Review Focus items — answers

| # | Focus | Verdict |
|---|---|---|
| 1 | `DpSteps` wrap guard after 14->13 | **Sound, not a tautology.** `dp_steps_test.dart:70-105` now measures a single-line step at the same 640px width and asserts `heights[1] > singleLine`. If the long label stops wrapping the two become equal and the test fails. Equal-height assertions at `:102-103` unchanged. Only nit = M7. |
| 2 | Tab stops / focus order on `/community` | **Unchanged, verified.** Nothing in the diff touches focusables there: the three emoji were on `/community/1` and `/community/new`; `_titleCell`'s change is a `DefaultTextStyle.merge` (no node); the `Semantics` wrappers are on `/settings`; `DpSteps` is diagnostic-only. `keyboard-traversal` also visits a hard-coded `/community` at 1440 and never reads `ROUTES` (`run.mjs:336-339`). CI run 1 recorded a matching first 8 stops. |
| 3 | `guest` 401 path and the `_baseFixtures` refactor | **Correct.** `auth_controller.dart:83-88`: `ApiException` -> `AuthUnauthenticated(error: includeApiError ? ... : null)`, and `bootstrapSession()` passes `includeApiError: false` (`:48`), so `/login` shows no error banner. `/auth/callback` goes through `bootstrapFromCallback` with `includeApiError: true` (`:152`) and *does* render the message — intentional, and why the 401 body carries a human sentence. The 401 is on `/auth/refresh` itself, so `auth_interceptor.dart`'s 401 retry cannot recurse into a second refresh of the same request (`api_providers.dart:136` documents that hazard explicitly). Refactor consumers: all three (`mockCommunityPosts:33`, `createWebMockHttpAdapter:806`, `_WebMockHttpAdapter.fetch:828`) read the ambient `webMockFixtures`, still a `final Map` with identical keys by construction, pinned by `web_mock_fixtures_profile_test.dart:71-81`. Both new CI legs passed, and `step9.log` shows 10/10 locally for each profile. |
| 4 | Axe waiver | **Can hide a regression — F5.** Route-wide rather than node-count-scoped; stale check evaluated per width, so a rule firing at 1240 but not 390 is a hard false failure; `seen` populated after the impact filter. |
| 5 | External-request budget | **Catches the real storm, misses a smaller one — F3, F4.** |
| 6 | `smallTargets` scrolling | **No cross-route or overflow contamination; a real within-route locator hazard — F6.** |
| 7 | `dpMeta` / `dpBody` render impact | **Claim verified.** `dp_typography.dart:48` `bodyMedium = 14 / 1.6`, so `dpBody(12)` = 12 / 19.2 and `dpBody(13)` = 13 / 20.8. `Material` resets `DefaultTextStyle` to `bodyMedium`, and `ListTile`/`ExpansionTile` subtitles derive from `bodyMedium` too, so all 12 flowing-caption sites render identically to the old bare literals. The one `DefaultTextStyle.merge` site (`web_community_board_projection.dart:210`) is safe because `bodyMedium` sets only `fontFamily`/`fontSize`/`height` — no `fontWeight`, `letterSpacing` or `color` — and the ambient height is already 1.6. The two `qna_detail_page` badges are the only movers: `labelMedium` is `12 / 16` **with `fontWeight: w600`** (`dp_typography.dart:56-61`), matching the literals' `w600`, so **only** the leading moves 19.2 -> 16. Exactly as claimed. |
| 8 | Emoji guard | **False negatives and false positives — F9.** Zero live escapes today (I scanned). |

---

## Judgments requested

- **`/login` kept in perf `ROUTES` while measuring `/dashboard`** — decision correct on scope;
  justification wrong (M4).
- **Waiving the quill toolbar rules instead of rebuilding the toolbar** — correct call, right risk
  trade, alternative recorded. The waiver's *shape* needs F5's node-count pin.
- **The inverted line-height premise** — **the author is right and the handoff was wrong.**
  Independently confirmed: `bodyMedium` is `14 / 1.6` (`dp_typography.dart:48`), so a bare
  `TextStyle(fontSize: 12)` merged over the Material default already rendered 12 / 19.2 — the 시안's
  `.meta` inheriting `body{line-height:1.6}`; `labelMedium` is `12 / 16` (`:56-61`) and is therefore the
  divergent side. Swapping those 12 sites to `labelMedium` would have moved 6 screens *away* from the
  시안 while looking like a token cleanup. Deriving instead of touching contract 2.0.0 is the right call.
  Related: the CSS-projection dump (`dp_semantic_tokens_dump_test.dart`) reads only
  `DpSemanticTokenManifest` + `AppTokens` + breakpoints and does **not** read `DpWebDensity`, so
  `baseline-impact-p5.md` §9-2's claim that the home `tokens.css` mirror needs no resync is also correct,
  including for the new `stepVerticalPadding`.
- **Is `perf/baseline.json` safe to freeze?** **Yes on the only axis the gate uses.** `gate.mjs` compares
  *nothing* but `transfer_bytes.total` and `js + canvaskit_or_wasm` against the baseline;
  `ready_ms`/`fcp_ms`/`lcp_ms`/`inp_ms`/`cls` are never compared to it (they are checked only against
  absolute budgets, from the *current* report, and those are warnings while `enforce_absolute: false`).
  So freezing `inp_ms 608` costs nothing, and the +10.98% warm row is a genuine non-regression: +1431 B
  of `index.html` from `c482b54` (verified: `feat(web): paint a boot splash until the first Flutter
  frame`, 2026-09-17 15:36, i.e. after the old baseline commit `6fff940` at 13:45), identical in cold and
  warm, under the 4096 B floor whose comment describes exactly this case. Strongest evidence: **CI run 2
  independently re-measured the final tip against this new baseline and `perf-gate` passed** (22m54s).
  The caveats are F7 (provenance) and F8 (the LCP branch), not the numbers.
- **Are the documents-side artifacts accurate against the code?** Largely yes — `baseline-impact-p5.md`
  is the most careful artifact in the set. I verified its §4 ET13 claims (`catalog.schema.json:61`
  constant, `release_id` input), §5 transfer arithmetic, §3 route table (16+4+1 = 21), the
  `DpInteractiveCard` zero-consumer claim (only `dp_list_row.dart:11`'s comment and
  `dp_list_row_test.dart:154`'s negative assertion remain), and that the DESIGN.md symbols exist. Two
  defects: M2 (LCP range) and F7's second half (the baseline was measured one commit before the tip, and
  no artifact says so).

---

## Declined to judge

- **Whether `browser-ux-onboarding` is or will be a required status check.** Branch-protection / ruleset
  configuration is not in this repo and I did not query GitHub. Needed: the `develop` ruleset's
  required-checks list (`gh api repos/DevPathAi/devpath-frontend/rulesets`). This decides whether F1 is a
  live gate-rot risk or whether the whole Task 12 expansion is currently advisory.
- **Whether the two waived rules fire on all 4 editor routes at both widths structurally or by
  coincidence.** I read the waiver and the pass/fail logs but did not run the pinned container. Needed:
  the per-route `violations` arrays from `evidence/browser-ux/latest.json` of CI run 2 (the ledger keeps
  only the verdict), to confirm node counts are 8/8 on each of the 8 (route, width) pairs before pinning
  counts per F5.
- **The real-world magnitude of F6.** Confirming that Flutter Web adds/removes `flt-semantics` nodes on
  scroll for these specific routes needs one probe: dump
  `document.querySelectorAll('flt-semantics[role=button]').length` before and after a wheel on
  `/settings` and `/mypage` at 390. `probe-scroll.mjs` / `probe-targets.mjs` are already in the SDD
  folder; it is a two-minute run.
- **Whether `unawaited_return_in_try_block` is genuinely absent from the CI-pinned analyzer.** The
  documents ledger asserts the file is byte-identical to `origin/develop` and that CI `analyze-test`
  passed (run 2 confirms: `analyze-test pass 4m54s`), which is enough for merge. I did not verify the
  lint's availability in Dart 3.12.1 vs 3.13.2. Needed: `dart --version` on both, or the lint's
  introduction release.

---

## What is genuinely good (one pass, no padding)

The pre-flight conflict scan called five of the eight interface risks correctly *before* execution,
including the one that mattered most — that the `keyboard-traversal` expectation is immune to `ROUTES`.
Four plan defects were caught and corrected rather than executed; in particular that
`require('playwright')` at module top level would have killed the pre-`npm ci` unit-test step, which is
why `routes.mjs` exists at all. That is the right refactor for the right reason, and I confirmed its 14
unit tests run with `node_modules` absent. Both latent runner flaws were correctly identified as
predating S3-P5. And the Extra-B investigation reversed a handed-down premise by reading the source of
truth instead of the handoff — the expensive, correct move.
