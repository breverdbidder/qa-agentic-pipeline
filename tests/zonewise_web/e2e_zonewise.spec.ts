import { test, expect } from '@playwright/test';

const BASE_URL = process.env.ZONEWISE_WEB_URL || 'https://zonewise.ai';
const AGENTS_URL = process.env.ZONEWISE_AGENTS_URL || 'https://zonewise-agents.onrender.com';

test.describe('ZoneWise.AI Critical Path E2E', () => {

  test.describe('Homepage', () => {
    test('homepage loads with 2xx status', async ({ page }) => {
      const response = await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30_000 });
      expect(response?.status()).toBeGreaterThanOrEqual(200);
      expect(response?.status()).toBeLessThan(400);
    });

    test('homepage contains ZoneWise branding', async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30_000 });
      const content = await page.content();
      const hasZoneWise = content.toLowerCase().includes('zonewise') ||
                          content.toLowerCase().includes('zoning') ||
                          (await page.title()).toLowerCase().includes('zone');
      expect(hasZoneWise).toBeTruthy();
    });

    test('page body has meaningful content (not blank)', async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30_000 });
      const bodyText = await page.locator('body').innerText();
      expect(bodyText.trim().length).toBeGreaterThan(20);
    });

    test('no critical app errors (unhandled rejections)', async ({ page }) => {
      const criticalErrors: string[] = [];
      // Only capture unhandled promise rejections — not third-party console.error
      page.on('pageerror', err => criticalErrors.push(err.message));
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30_000 });
      // Filter React hydration noise and browser extension errors
      const appErrors = criticalErrors.filter(e =>
        !e.includes('extension') &&
        !e.includes('chrome-extension') &&
        !e.includes('ResizeObserver')
      );
      expect(appErrors.length).toBe(0);
    });
  });

  test.describe('Core UI Elements', () => {
    test('input or chat interface exists', async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30_000 });
      const count = await page.locator('input, textarea, [role="textbox"], [contenteditable="true"]').count();
      expect(count).toBeGreaterThan(0);
    });

    test('page renders within 10 seconds', async ({ page }) => {
      const start = Date.now();
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30_000 });
      expect(Date.now() - start).toBeLessThan(10_000);
    });
  });

  test.describe('API Health', () => {
    test('agents backend /health returns 200', async ({ request }) => {
      const response = await request.get(`${AGENTS_URL}/health`, { timeout: 30_000 });
      expect(response.status()).toBe(200);
    });
  });
});
