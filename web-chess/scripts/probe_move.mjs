import { chromium } from 'playwright';

const browser = await chromium.launch({
  headless: true,
  args: ['--use-gl=angle', '--use-angle=swiftshader'],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

await page.goto('http://127.0.0.1:5173', { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForFunction(() => typeof window.render_game_to_text === 'function', { timeout: 15000 });

const canvas = await page.$('canvas');
const bb = await canvas.boundingBox();

const state = async () => page.evaluate(() => JSON.parse(window.render_game_to_text()));
const start = await state();

let selectPoint = null;
let selectedSquare = null;
for (let y = 180; y <= 620 && !selectPoint; y += 25) {
  for (let x = 220; x <= 1060 && !selectPoint; x += 25) {
    await page.mouse.click(bb.x + x, bb.y + y);
    await page.waitForTimeout(20);
    const s = await state();
    if (s.selected_square && Array.isArray(s.legal_targets) && s.legal_targets.length > 0) {
      selectPoint = { x, y };
      selectedSquare = s.selected_square;
    }
  }
}

let moved = null;
if (selectPoint) {
  for (let y = 180; y <= 620 && !moved; y += 20) {
    for (let x = 220; x <= 1060 && !moved; x += 20) {
      await page.mouse.click(bb.x + selectPoint.x, bb.y + selectPoint.y);
      await page.waitForTimeout(10);
      await page.mouse.click(bb.x + x, bb.y + y);
      await page.waitForTimeout(20);
      const s = await state();
      if (s.turn === 'b' && s.fen !== start.fen) {
        moved = { x, y, fen: s.fen, status: s.status };
      }
    }
  }
}

console.log(JSON.stringify({ selectedSquare, selectPoint, moved }));
await browser.close();
