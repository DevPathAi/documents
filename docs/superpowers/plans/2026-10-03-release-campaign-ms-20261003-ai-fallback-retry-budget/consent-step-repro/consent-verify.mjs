// [보존본 2026-10-06] import·DIST 경로는 조사 당시 워크트리(frontend-consent-repro · home-master-1002 · home-fix-flutter-fill) 기준이다.
// 그 워크트리들은 정리됐다 — 다시 쓸 때는 README.md 의 레시피로 빌드하고 경로를 고친다.
// 수정된 홈 워크트리의 실제 헬퍼(fillFlutterTextField)와 바뀐 스펙 순서를 mock consent 빌드에서 반복 검증한다.
// Usage: node consent-verify.mjs <iterations>
import { chromium, expect } from 'file:///D:/workspace/dpa/.worktrees/home-fix-flutter-fill/node_modules/@playwright/test/index.mjs';
import {
  activateFlutterSemantics,
  fillFlutterTextField,
  waitForFlutterSemanticsTarget,
} from 'file:///D:/workspace/dpa/.worktrees/home-fix-flutter-fill/e2e/release/support/staging-control.js';
import { serve } from 'file:///D:/workspace/dpa/.worktrees/frontend-consent-repro/tools/browser_ux/serve.mjs';

const iterations = Number(process.argv[2] ?? 20);
const DELAYS = [0, 30, 120, 400];
const YEAR_ERROR = '출생 연도 4자리를 숫자로 입력해 주세요';
const REQUIRED_ERROR = '필수 항목(이용약관·개인정보)에 모두 동의해 주세요.';

const server = await serve(process.env.DIST ?? 'D:/workspace/dpa/.worktrees/frontend-consent-repro/apps/web/build/web');
const browser = await chromium.launch();
const page = await (await browser.newContext()).newPage();

const texts = () => page.evaluate(() => Array.from(
  new Set(Array.from(document.querySelectorAll('flt-semantics'))
    .map((node) => (node.getAttribute('aria-label') || node.textContent || '').trim())
    .filter(Boolean)),
));

const outcomes = {};
const failures = [];
let fillMs = 0;
await page.goto(`${server.base}/consent`, { waitUntil: 'domcontentloaded' });
for (let index = 0; index < iterations; index += 1) {
  let outcome = 'no-effect';
  try {
    // refreshFlutter(page, '/consent')
    await page.reload({ waitUntil: 'domcontentloaded' });
    await activateFlutterSemantics(page);
    await expect.poll(() => new URL(page.url()).pathname).toBe('/consent');
    // --- 스펙의 required-consent-claim-replay 단계와 같은 순서 ---
    const termsConsent = page.getByRole('checkbox', { name: /서비스 이용약관 동의/ });
    const privacyConsent = page.getByRole('checkbox', { name: /개인정보 수집·이용 동의/ });
    const birthYear = page.getByLabel('출생 연도 (필수)');
    await termsConsent.click();
    await privacyConsent.click();
    const started = Date.now();
    await fillFlutterTextField(page, birthYear, '1995');
    fillMs += Date.now() - started;
    await page.waitForTimeout(DELAYS[index % DELAYS.length]); // control.command('replay-claim') 자리
    const consentButton = page.getByRole('button', { name: '동의하고 계속하기', exact: true });
    await waitForFlutterSemanticsTarget(page, consentButton);
    await expect(consentButton).toBeEnabled();
    await expect(termsConsent).toBeChecked();
    await expect(privacyConsent).toBeChecked();
    await expect(birthYear).toHaveValue('1995');
    const before = new Set(await texts());
    await consentButton.evaluate((element) => element.click());
    const deadline = Date.now() + 6_000;
    while (Date.now() < deadline) {
      const now = await texts().catch(() => []);
      if (now.some((text) => text.includes(REQUIRED_ERROR))) { outcome = 'validation-required'; break; }
      if (now.some((text) => text.includes(YEAR_ERROR))) { outcome = 'validation-year'; break; }
      if (new URL(page.url()).pathname !== '/consent' || now.some((text) => !before.has(text))) {
        outcome = 'submitted';
        break;
      }
      await page.waitForTimeout(100);
    }
  } catch (error) {
    outcome = 'harness-error';
    failures.push({ index, error: String(error).split('\n')[0].slice(0, 200) });
  }
  outcomes[outcome] = (outcomes[outcome] ?? 0) + 1;
}
for (const failure of failures.slice(0, 5)) console.log(JSON.stringify(failure));
console.log('SUMMARY', JSON.stringify({ iterations, outcomes, avgFillMs: Math.round(fillMs / iterations) }));
await browser.close();
await server.close();
