const { chromium } = require('playwright');
(async () => {
  console.log('Playwright bootet...');
  const browser = await chromium.launch({ 
    headless: false,
    args: ['--no-sandbox']
  });
  const page = await browser.newPage();
  await page.goto('https://www.wikipedia.org');
  await page.screenshot({ path: '/app/openclaw-main/pw_victory.png' });
  await browser.close();
  console.log('SUCCESS: Playwright hat Wikipedia gerendert!');
})();
