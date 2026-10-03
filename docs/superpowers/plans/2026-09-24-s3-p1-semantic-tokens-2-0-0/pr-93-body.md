Mirrors the app's semantic token contract **2.0.0** into `assets/tokens.css` (S3-P1; source `devpath-frontend` PR #232).

- radii 4/6/8/6/12 · new `--dp-density-control-height|row-padding|min-target` (30/8/24) · `--dp-layout-content-max` 1360→1120 · new `--dp-layout-header-height` 56
- `--dp-color-rail-*` → `--dp-color-header-*` (values unchanged) in `tokens.css`, `index.html`, `assets/styles.css`, `assets/public.css`
- `tests/design-token-contract.test.js` pins the new key set, the new values and the dark-block selector; `DESIGN.md` names contract 2.0.0

`npm test` 496/496 · `npm run build` clean.

## ⚠️ Draft: visual baselines are not re-recorded

The radii and the 1120px content width change the rendered landing, so the four committed baselines (320/600/840/1240) no longer match and **`visual-a11y` is expected to fail on this PR.**

Re-recording must run inside the exact image in `baseline_policy.platform` (`npm run visual:evidence:docker` → `npm run visual:baseline:update`), and an approved baseline needs human review afterwards (`docs/visual-a11y-evidence.md` §Baseline updates). That step was not run here: the Docker daemon was not available on the build machine, and this repo's standing rule is that heavy Playwright work belongs in the pinned image rather than ad-hoc locally.

**Do not merge until the baselines are re-recorded and approved.**

🤖 Generated with [Claude Code](https://claude.com/claude-code)
