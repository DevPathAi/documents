// [보존본 2026-10-06] import·DIST 경로는 조사 당시 워크트리(frontend-consent-repro · home-master-1002 · home-fix-flutter-fill) 기준이다.
// 그 워크트리들은 정리됐다 — 다시 쓸 때는 README.md 의 레시피로 빌드하고 경로를 고친다.
// consent-repro.mjs 의 후속 — 연도 fill 이 Flutter 에 반영되는지를 변형별로 잰다. 일회용 조사 스크립트.
// Usage: node consent-repro2.mjs <iterations> <variant>
//   spec        : 스펙 순서 그대로(체크 2 → fill)
//   prewait     : 폼이 뜬 뒤 1500ms 기다렸다가 스펙 순서
//   type        : fill 대신 click + pressSequentially
//   fill-first  : fill 을 체크보다 먼저
//   refill      : fill 뒤 값이 다르면 다시 fill(최대 3회)
import { chromium, expect } from 'file:///D:/workspace/dpa/.worktrees/home-master-1002/node_modules/@playwright/test/index.mjs';
import { activateFlutterSemantics } from 'file:///D:/workspace/dpa/.worktrees/home-master-1002/e2e/release/support/staging-control.js';
import { serve } from 'file:///D:/workspace/dpa/.worktrees/frontend-consent-repro/tools/browser_ux/serve.mjs';

const iterations = Number(process.argv[2] ?? 20);
const variant = process.argv[3] ?? 'spec';

const server = await serve(process.env.DIST ?? 'D:/workspace/dpa/.worktrees/frontend-consent-repro/apps/web/build/web');
const browser = await chromium.launch();
const page = await (await browser.newContext()).newPage();

async function refreshFlutter(pathname) {
  await page.reload({ waitUntil: 'domcontentloaded' });
  await activateFlutterSemantics(page);
  await expect.poll(() => new URL(page.url()).pathname).toBe(pathname);
}

const tally = {};
const samples = [];
await page.goto(`${server.base}/consent`, { waitUntil: 'domcontentloaded' });
for (let index = 0; index < iterations; index += 1) {
  let row;
  try {
    await refreshFlutter('/consent');
    const terms = page.getByRole('checkbox', { name: /서비스 이용약관 동의/ });
    const privacy = page.getByRole('checkbox', { name: /개인정보 수집·이용 동의/ });
    const year = page.getByLabel('출생 연도 (필수)');
    await terms.waitFor({ state: 'visible' });
    const prefilled = await year.inputValue();
    if (variant === 'prewait') await page.waitForTimeout(1500);
    const t0 = Date.now();
    let attempts = 0;
    if (variant === 'fill-first') await year.fill('1995');
    await terms.click();
    await privacy.click();
    if (variant === 'type') {
      await year.click();
      await page.keyboard.press('Control+A');
      await year.pressSequentially('1995');
    } else if (variant === 'stable') {
      await expect(async () => {
        attempts += 1;
        await year.fill('1995');
        await page.waitForTimeout(300);
        expect(await year.inputValue()).toBe('1995');
        await page.waitForTimeout(300);
        expect(await year.inputValue()).toBe('1995');
      }).toPass({ timeout: 15_000 });
    } else if (variant !== 'fill-first') {
      await year.fill('1995');
    }
    let refills = 0;
    if (variant === 'refill') {
      while (refills < 3) {
        await page.waitForTimeout(150);
        if (await year.inputValue() === '1995') break;
        await year.fill('1995');
        refills += 1;
      }
    }
    const immediately = await year.inputValue();
    await page.waitForTimeout(400);
    const settled = await year.inputValue();
    await page.keyboard.press('Tab');
    await page.waitForTimeout(300);
    const blurred = await year.inputValue();
    row = {
      index, prefilled, immediately, settled, blurred, attempts, refills, interactMs: Date.now() - t0 - 400,
      terms: await terms.isChecked(), privacy: await privacy.isChecked(),
    };
  } catch (error) {
    row = { index, error: String(error).split('\n')[0].slice(0, 160) };
  }
  const key = row.error ? `harness-error: ${row.error}` : `settled=${row.settled} blurred=${row.blurred} attempts=${row.attempts} terms=${row.terms} privacy=${row.privacy}`;
  tally[key] = (tally[key] ?? 0) + 1;
  if (samples.length < 4 || (row.settled && row.settled !== '1995' && samples.length < 10)) samples.push(row);
}
for (const sample of samples) console.log(JSON.stringify(sample));
console.log('SUMMARY', JSON.stringify({ variant, iterations, tally }));
await browser.close();
await server.close();
