const fs = require('fs');
const { chromium } = require('playwright');

async function main() {
  const [inputPath, outputPath, selectedFlow = 'all'] = process.argv.slice(2);
  if (!inputPath || !outputPath) throw new Error('input and output paths are required');

  const fragment = fs.readFileSync(inputPath, 'utf8');
  const base = `
    <style>
      :root {
        --background:#f7f8f6; --foreground:#17211b; --card:#ffffff;
        --card-foreground:#17211b; --primary:#155c3b; --primary-foreground:#ffffff;
        --secondary:#e8eee9; --secondary-foreground:#17211b; --muted:#e8ece8;
        --muted-foreground:#526158; --accent:#e2eee6; --accent-foreground:#173b2a;
        --border:#cbd5cd; --ring:#155c3b; --viz-series-1:#2e7d52;
        --viz-series-2:#4a79a8; --viz-series-3:#9a6c2f;
        font-family: Arial, 'Malgun Gothic', sans-serif; font-size:16px;
      }
      * { box-sizing:border-box; }
      body { margin:0; padding:32px; background:var(--background); color:var(--foreground); }
      .viz-controls { display:flex; flex-wrap:wrap; gap:8px; }
      .btn { border:1px solid var(--border); border-radius:8px; background:var(--card); color:var(--foreground); padding:8px 12px; font:inherit; }
      .btn-primary { background:var(--primary); color:var(--primary-foreground); border-color:var(--primary); }
      .viz-badge { background:var(--secondary); color:var(--secondary-foreground); border-radius:999px; padding:4px 8px; font-size:13px; }
      .text-small { font-size:13px; }
      i[data-lucide] { display:none; }
    </style>`;

  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  });
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 }, deviceScaleFactor: 2 });
  await page.setContent(base + fragment, { waitUntil: 'load' });
  if (selectedFlow !== 'all') {
    const flowButton = page.locator(`[data-flow="${selectedFlow}"]`);
    if (await flowButton.count() !== 1) throw new Error(`unknown flow: ${selectedFlow}`);
    await flowButton.click();
  }
  await page.locator('#eminai-system-map').screenshot({ path: outputPath, type: 'png' });
  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
