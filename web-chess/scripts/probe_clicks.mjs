import { chromium } from 'playwright';

const browser = await chromium.launch({
  headless: true,
  args: ['--use-gl=angle', '--use-angle=swiftshader'],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

page.on('console', (msg) => {
  if (msg.type() === 'error') {
    console.error('console.error:', msg.text());
  }
});
page.on('pageerror', (err) => {
  console.error('pageerror:', String(err));
});

await page.goto('http://127.0.0.1:5173', { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForFunction(() => typeof window.render_game_to_text === 'function', { timeout: 15000 });

const canvas = await page.$('canvas');
if (!canvas) {
  console.log(JSON.stringify({ error: 'no-canvas' }));
  await browser.close();
  process.exit(1);
}
const bb = await canvas.boundingBox();
if (!bb) {
  console.log(JSON.stringify({ error: 'no-bbox' }));
  await browser.close();
  process.exit(1);
}

let found = null;
for (let y = 180; y <= 620 && !found; y += 30) {
  for (let x = 220; x <= 1060 && !found; x += 30) {
    await page.mouse.click(bb.x + x, bb.y + y);
    await page.waitForTimeout(20);
    const state = await page.evaluate(() => JSON.parse(window.render_game_to_text()));
    if (state.selected_square) {
      found = { x, y, square: state.selected_square, targets: state.legal_targets };
    }
  }
}

console.log(JSON.stringify(found));
await browser.close();
