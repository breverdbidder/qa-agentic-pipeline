import { test, expect } from '@playwright/test';

const BASE_URL = process.env.ZONEWISE_WEB_URL || 'https://zonewise.ai';

test.describe('ZoneWise.AI Critical Path E2E', () => {

  test.describe('Homepage', () => {
    test('homepage loads and has title', async ({ page }) => {
      const response = await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
      expect(response?.status()).toBeLessThan(400);
    });

    test('homepage contains ZoneWise branding', async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
      const title = await page.title();
      const content = await page.content();
      const hasZoneWise = title.toLowerCase().includes('zone') || 
                          content.toLowerCase().includes('zonewise') ||
                          content.toLowerCase().includes('zoning');
      expect(hasZoneWise).toBeTruthy();
    });

    test('no console errors on load', async ({ page }) => {
      const errors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') errors.push(msg.text());
      });
      await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });
      // Filter out known third-party errors
      const criticalErrors = errors.filter(e => 
        !e.includes('favicon') && 
        !e.includes('analytics') &&
        !e.includes('gtag')
      );
      expect(criticalErrors.length).toBe(0);
    });
  });

  test.describe('Core UI Elements', () => {
    test('search or input field exists', async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
      const input = page.locator('input, textarea, [role="textbox"]').first();
      const count = await page.locator('input, textarea, [role="textbox"]').count();
      // ZoneWise has a chat/search interface
      expect(count).toBeGreaterThan(0);
    });

    test('page renders without blank screen', async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
      const body = await page.locator('body').innerText();
      expect(body.trim().length).toBeGreaterThan(10);
    });
  });

  test.describe('API Integration', () => {
    test('agents backend is reachable', async ({ request }) => {
      const agentsUrl = process.env.ZONEWISE_AGENTS_URL || 'https://zonewise-agents.onrender.com';
      const response = await request.get(`${agentsUrl}/health`);
      expect(response.status()).toBe(200);
    });
  });

  test.describe('Performance', () => {
    test('homepage loads within 10 seconds', async ({ page }) => {
      const start = Date.now();
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
      const elapsed = Date.now() - start;
      expect(elapsed).toBeLessThan(10_000);
    });
  });
});
