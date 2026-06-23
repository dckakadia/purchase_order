const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const urls = [
    'http://127.0.0.1:8090/supplier-book',
    'http://127.0.0.1:8090/customer-book',
    'http://127.0.0.1:8090/forwarder-dashboard',
    'http://127.0.0.1:8090/admin/rbac'
  ];

  for (const url of urls) {
    console.log(`\nTesting ${url}`);
    const page = await browser.newPage();
    
    page.on('console', msg => console.log(`[PAGE CONSOLE] ${msg.type()}: ${msg.text()}`));
    page.on('pageerror', err => console.error(`[PAGE ERROR]`, err));
    
    // Set cookie to simulate login
    await page.setCookie({
      name: 'session',
      value: 'eyJ1c2VyX2lkIjoxfQ.Z.mocksession', // Might not work if secret is needed, but we can just use the login page first
      domain: '127.0.0.1'
    });

    try {
      await page.goto(url, { waitUntil: 'networkidle2' });
      // If redirected to login, login
      if (page.url().includes('login')) {
        await page.type('input[name="username"]', 'admin');
        await page.type('input[name="password"]', 'admin');
        await Promise.all([
          page.click('button[type="submit"]'),
          page.waitForNavigation({ waitUntil: 'networkidle2' }),
        ]);
        // After login it redirects. Then we go to the actual URL again
        await page.goto(url, { waitUntil: 'networkidle2' });
      }

      console.log(`Final URL: ${page.url()}`);
      const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 200).replace(/\n/g, ' '));
      console.log(`Body starts with: ${bodyText}`);

    } catch (e) {
      console.error(`Error loading ${url}:`, e);
    }
    await page.close();
  }

  await browser.close();
})();
