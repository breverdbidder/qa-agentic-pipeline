import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: 'e2e_zonewise.spec.ts',  // Only our spec — no recursive pickup
  timeout: 60_000,
  retries: 1,
  reporter: [['json', { outputFile: 'playwright-results.json' }], ['list']],
  use: {
    headless: true,
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
