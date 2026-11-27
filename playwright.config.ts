import { defineConfig, devices } from '@playwright/test';

/**
 * Smoke tests run against the production build in dist/ (run `pnpm build:all` first),
 * so drafts are excluded and /cv.pdf exists exactly as it will be deployed.
 */
export default defineConfig({
  testDir: 'tests',
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: { baseURL: 'http://localhost:4322' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'pnpm preview --port 4322',
    url: 'http://localhost:4322',
    reuseExistingServer: !process.env.CI,
  },
});
