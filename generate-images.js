const puppeteer = require('puppeteer');
const path = require('path');

async function generate() {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const templates = [
    {
      file: 'landing/og-image.html',
      output: 'landing/og.jpg',
      width: 1200,
      height: 630,
    },
    {
      file: 'landing/fb-post.html',
      output: 'landing/fb-post.jpg',
      width: 1080,
      height: 1080,
    },
  ];

  for (const t of templates) {
    const page = await browser.newPage();
    await page.setViewport({ width: t.width, height: t.height, deviceScaleFactor: 2 });

    const filePath = path.resolve(__dirname, t.file);
    await page.goto(`file://${filePath}`, { waitUntil: 'networkidle0', timeout: 30000 });

    // Wait for fonts to load
    await page.evaluate(() => document.fonts.ready);
    await new Promise(r => setTimeout(r, 1500));

    const outputPath = path.resolve(__dirname, t.output);
    await page.screenshot({
      path: outputPath,
      type: 'jpeg',
      quality: 92,
      clip: { x: 0, y: 0, width: t.width, height: t.height },
    });

    console.log(`✓ ${t.output} (${t.width}x${t.height})`);
    await page.close();
  }

  await browser.close();
  console.log('\nDone! Images saved to landing/');
}

generate().catch(err => { console.error(err); process.exit(1); });
