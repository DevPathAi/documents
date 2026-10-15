// [보존본 2026-10-06] import·DIST 경로는 조사 당시 워크트리(frontend-consent-repro · home-master-1002 · home-fix-flutter-fill) 기준이다.
// 그 워크트리들은 정리됐다 — 다시 쓸 때는 README.md 의 레시피로 빌드하고 경로를 고친다.
// 활성화 저니의 `required-consent-claim-replay` 단계를 mock consent 빌드에서 반복해
// 「제출을 눌렀는데 아무 요청도 안 나가는」 경우가 재현되는지 본다. 일회용 조사 스크립트.
// Usage: node consent-repro.mjs <iterations> [mode]
//   mode = spec    : 스펙과 같은 순서(체크 2 → 연도 fill → 지연 → DOM click)
//   mode = guarded : 제출 전에 체크·연도 값을 expect 로 단언(보강안 검증)
import { chromium, expect } from 'file:///D:/workspace/dpa/.worktrees/home-master-1002/node_modules/@playwright/test/index.mjs';
import {
  activateFlutterSemantics,
  waitForFlutterSemanticsTarget,
} from 'file:///D:/workspace/dpa/.worktrees/home-master-1002/e2e/release/support/staging-control.js';
import { serve } from 'file:///D:/workspace/dpa/.worktrees/frontend-consent-repro/tools/browser_ux/serve.mjs';

const iterations = Number(process.argv[2] ?? 20);
const mode = process.argv[3] ?? 'spec';
const DELAYS = [0, 30, 120, 400];
const REQUIRED_ERROR = '필수 항목(이용약관·개인정보)에 모두 동의해 주세요.';
const YEAR_ERROR = '출생 연도 4자리를 숫자로 입력해 주세요';

const server = await serve(process.env.DIST ?? 'D:/workspace/dpa/.worktrees/frontend-consent-repro/apps/web/build/web');
const browser = await chromium.launch();
const page = await (await browser.newContext()).newPage();
const pageErrors = [];
page.on('pageerror', (error) => pageErrors.push(String(error).slice(0, 200)));

async function semanticsTexts() {
  return page.evaluate(() => Array.from(
    new Set(Array.from(document.querySelectorAll('flt-semantics'))
      .map((node) => (node.getAttribute('aria-label') || node.textContent || '').trim())
      .filter(Boolean)),
  ));
}

async function refreshFlutter(pathname) {
  await page.reload({ waitUntil: 'domcontentloaded' });
  await activateFlutterSemantics(page);
  await expect.poll(() => new URL(page.url()).pathname).toBe(pathname);
}

const outcomes = {};
const rows = [];
await page.goto(`${server.base}/consent`, { waitUntil: 'domcontentloaded' });
for (let index = 0; index < iterations; index += 1) {
  const delay = DELAYS[index % DELAYS.length];
  const started = Date.now();
  let outcome = 'unknown';
  let detail = '';
  try {
    await refreshFlutter('/consent');
    const terms = page.getByRole('checkbox', { name: /서비스 이용약관 동의/ });
    const privacy = page.getByRole('checkbox', { name: /개인정보 수집·이용 동의/ });
    const year = page.getByLabel('출생 연도 (필수)');
    await terms.click();
    await privacy.click();
    if (mode === 'stable') {
      await expect(async () => {
        await year.fill('1995');
        await page.waitForTimeout(300);
        expect(await year.inputValue()).toBe('1995');
        await page.waitForTimeout(300);
        expect(await year.inputValue()).toBe('1995');
      }).toPass({ timeout: 15_000 });
    } else {
      await year.fill('1995');
    }
    if (delay > 0) await page.waitForTimeout(delay);
    const consentButton = page.getByRole('button', { name: '동의하고 계속하기', exact: true });
    await waitForFlutterSemanticsTarget(page, consentButton);
    await expect(consentButton).toBeEnabled();
    if (mode === 'guarded') {
      await expect(terms).toBeChecked();
      await expect(privacy).toBeChecked();
      await expect(year).toHaveValue('1995');
    }
    const state = {
      terms: await terms.isChecked(),
      privacy: await privacy.isChecked(),
      year: await year.inputValue(),
    };
    const before = new Set(await semanticsTexts());
    await consentButton.evaluate((element) => element.click());
    const deadline = Date.now() + 6_000;
    outcome = 'no-effect';
    while (Date.now() < deadline) {
      const pathname = new URL(page.url()).pathname;
      if (pathname !== '/consent') { outcome = 'navigated'; detail = pathname; break; }
      const texts = await semanticsTexts().catch(() => []);
      if (texts.some((text) => text.includes(REQUIRED_ERROR))) { outcome = 'validation-required'; break; }
      if (texts.some((text) => text.includes(YEAR_ERROR))) { outcome = 'validation-year'; break; }
      const added = texts.filter((text) => !before.has(text));
      if (added.length > 0) { outcome = 'submitted'; detail = added[0].slice(0, 60); break; }
      await page.waitForTimeout(100);
    }
    detail = `${detail} state=${JSON.stringify(state)}`;
  } catch (error) {
    outcome = 'harness-error';
    detail = String(error).split('\n')[0].slice(0, 160);
  }
  outcomes[outcome] = (outcomes[outcome] ?? 0) + 1;
  rows.push({ index, delay, outcome, ms: Date.now() - started, detail });
  if (outcome !== 'submitted' || index < 3) console.log(JSON.stringify(rows.at(-1)));
}
console.log('SUMMARY', JSON.stringify({ mode, iterations, outcomes, pageErrors: pageErrors.slice(0, 3) }));
await browser.close();
await server.close();
